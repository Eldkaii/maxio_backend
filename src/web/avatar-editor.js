/* Owner-only wardrobe. Unlock decisions and persisted identity come from the API. */
(() => {
  const copy = value => JSON.parse(JSON.stringify(value));
  const esc = value => String(value).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const slotLabels = { jersey: "Remeras", shorts: "Shorts", boots: "Botines", cap: "Gorras", tattoo: "Tatuajes" };
  let root, owner, saved, draft, faceUrl = null, catalog = [], loaded = false, busy = false, activeSlot = "jersey", requestId = 0;
  let cropDialog, cropImage = null, objectUrl = null, fileInput;

  async function api(path, options = {}) {
    const session = sessionStorage.getItem("maxio_token");
    const response = await fetch(path, { ...options, headers: { ...options.headers, ...(session ? { Authorization: `Bearer ${session}` } : {}) } });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw Error(typeof body.detail === "string" ? body.detail : "No pudimos guardar el avatar. Revisá tu sesión e intentá otra vez.");
    return body;
  }
  const dirty = () => JSON.stringify(saved) !== JSON.stringify(draft);
  const blocked = () => catalog.some(item => draft.equipment[item.slot] === item.id && !item.unlocked);
  function status(text, error = false) {
    const label = root?.querySelector(".wardrobe-status");
    if (label) { label.textContent = text; label.classList.toggle("is-error", error); }
  }
  function updateActions() {
    if (!root) return;
    root.querySelector("[data-save-avatar]").disabled = busy || !loaded || !dirty() || blocked();
    root.querySelector("[data-reset-avatar]").disabled = busy || !dirty();
    root.querySelector("[data-remove-face]").disabled = busy || !faceUrl;
    root.querySelector("[data-upload-face]").disabled = busy;
    root.querySelectorAll("select, [data-slot], [data-item]").forEach(input => { input.disabled = busy; });
    root.querySelector(".wardrobe-save-hint").textContent = blocked()
      ? "Estás probando una pieza bloqueada. Elegí prendas disponibles para guardar."
      : dirty() ? "Vista previa: guardá para mostrar este avatar en tu perfil." : "Tu avatar guardado también se ve en tu perfil público.";
    const label = document.querySelector(".avatar-appearance-label");
    if (label) label.textContent = dirty() ? "Vista previa · sin guardar" : "Tu avatar · guardado";
  }
  function preview() {
    window.MaxioAvatar.setState({ config: draft, face_url: faceUrl });
    updateActions();
  }
  function fillControls() {
    root.querySelectorAll("[data-avatar-field]").forEach(input => { input.value = draft[input.dataset.avatarField]; });
    root.querySelector(".avatar-face-help").textContent = faceUrl
      ? "Tu cara está cargada. Podés reemplazarla o volver al rostro ilustrado."
      : "Subí una foto de tu cara y ajustá el recorte. Hasta entonces usamos un rostro ilustrado.";
    root.querySelector(".avatar-hair-options").hidden = Boolean(faceUrl);
  }
  function renderItems() {
    if (!root) return;
    root.querySelectorAll("[data-slot]").forEach(button => {
      const selected = button.dataset.slot === activeSlot;
      button.classList.toggle("is-selected", selected); button.setAttribute("aria-pressed", selected);
    });
    const grid = root.querySelector(".wardrobe-items");
    if (!loaded) { grid.innerHTML = '<p class="empty">Cargando tus prendas…</p>'; return; }
    grid.innerHTML = catalog.filter(item => item.slot === activeSlot).map(item => {
      const look = copy(draft); look.equipment[item.slot] = item.id;
      const selected = draft.equipment[item.slot] === item.id;
      const image = window.MaxioAvatar.source(look, window.MaxioAvatar.face());
      return `<button type="button" class="wardrobe-item ${selected ? "is-selected" : ""} ${item.unlocked ? "" : "is-locked"}" data-item="${esc(item.id)}" aria-pressed="${selected}">
        <span class="wardrobe-item-art"><img src="${image}" alt="" loading="lazy"></span>
        <span class="wardrobe-item-state">${item.unlocked ? (selected ? "ELEGIDO" : "DISPONIBLE") : "POR DESBLOQUEAR"}</span>
        <strong>${esc(item.name)}</strong><span>${esc(item.requirement)}</span>
        ${item.target ? `<progress value="${item.progress}" max="${item.target}" aria-label="Progreso para ${esc(item.name)}"></progress><small>${item.progress} / ${item.target}${!item.unlocked && item.progress === item.target ? " · falta la afinidad" : ""}</small>` : ""}
      </button>`;
    }).join("");
    updateActions();
  }
  async function loadWardrobe() {
    const id = ++requestId, currentOwner = owner;
    try {
      const state = await api("/player/me/avatar");
      if (id !== requestId || currentOwner !== owner) return;
      const preserveDraft = loaded && dirty();
      saved = copy(state.config); if (!preserveDraft) draft = copy(saved);
      faceUrl = state.face_url; catalog = state.catalog; loaded = true;
      fillControls(); preview(); renderItems(); status("");
    } catch (error) {
      if (id === requestId) { status(error.message, true); root.querySelector("[data-retry-wardrobe]").hidden = false; }
    }
  }
  async function save() {
    if (busy || !loaded || blocked() || !dirty()) return;
    busy = true; updateActions(); status("Guardando tu avatar…");
    try {
      const state = await api("/player/me/avatar", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(draft) });
      saved = copy(state.config); draft = copy(saved); faceUrl = state.face_url; catalog = state.catalog;
      fillControls(); preview(); renderItems(); status("Avatar guardado.");
    } catch (error) { status(error.message, true); }
    finally { busy = false; updateActions(); }
  }
  async function removeFace() {
    if (busy || !faceUrl) return;
    busy = true; updateActions(); status("Quitando la cara…");
    try {
      const state = await api("/player/me/avatar/face", { method: "DELETE" });
      faceUrl = state.face_url; fillControls(); preview(); renderItems(); status("Volviste al rostro ilustrado.");
    } catch (error) { status(error.message, true); }
    finally { busy = false; updateActions(); }
  }
  function disposeCrop() {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = null; cropImage = null; if (fileInput) fileInput.value = "";
  }
  function drawCrop() {
    if (!cropImage) return;
    const canvas = cropDialog.querySelector("canvas"), ctx = canvas.getContext("2d");
    const zoom = Number(cropDialog.querySelector('[name="zoom"]').value);
    const x = Number(cropDialog.querySelector('[name="x"]').value) / 100;
    const y = Number(cropDialog.querySelector('[name="y"]').value) / 100;
    const scale = Math.max(canvas.width / cropImage.naturalWidth, canvas.height / cropImage.naturalHeight) * zoom;
    const width = cropImage.naturalWidth * scale, height = cropImage.naturalHeight * scale;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(cropImage, (canvas.width - width) / 2 + x * (width - canvas.width) / 2,
      (canvas.height - height) / 2 + y * (height - canvas.height) / 2, width, height);
  }
  function setupCrop() {
    if (cropDialog) return;
    cropDialog = document.createElement("dialog"); cropDialog.className = "avatar-crop-dialog";
    cropDialog.setAttribute("aria-labelledby", "face-crop-title");
    cropDialog.innerHTML = `<h2 id="face-crop-title">Esta cara es tuya</h2><p>Ubicá tu cara dentro del óvalo, desde el pelo hasta el mentón. La foto debe ser tuya.</p>
      <div class="face-crop-frame"><canvas width="304" height="384" aria-label="Vista previa del recorte de tu cara"></canvas><i aria-hidden="true"></i></div>
      <label>Acercar<input name="zoom" type="range" min="1" max="3" step=".01" value="1"></label>
      <label>Horizontal<input name="x" type="range" min="-100" max="100" value="0"></label>
      <label>Vertical<input name="y" type="range" min="-100" max="100" value="0"></label>
      <p class="face-crop-note">Solo se guarda este recorte, con un acabado suavizado. Será visible como parte de tu avatar.</p>
      <p class="face-crop-status" role="status" aria-live="polite"></p>
      <div class="wardrobe-actions"><button type="button" data-crop-cancel>Cancelar</button><button type="button" data-crop-save>Guardar mi cara</button></div>`;
    document.body.append(cropDialog);
    cropDialog.addEventListener("input", drawCrop);
    cropDialog.querySelector("[data-crop-cancel]").addEventListener("click", () => cropDialog.close());
    cropDialog.addEventListener("close", () => { disposeCrop(); root?.querySelector("[data-upload-face]").focus(); });
    cropDialog.addEventListener("cancel", event => { if (busy) event.preventDefault(); });
    cropDialog.querySelector("[data-crop-save]").addEventListener("click", async () => {
      if (busy || !cropImage) return;
      busy = true; updateActions(); cropDialog.querySelectorAll("button,input").forEach(e => { e.disabled = true; });
      const message = cropDialog.querySelector(".face-crop-status"); message.textContent = "Guardando tu cara…";
      try {
        const blob = await new Promise(resolve => cropDialog.querySelector("canvas").toBlob(resolve, "image/png"));
        if (!blob) throw Error("No se pudo preparar la foto.");
        const form = new FormData(); form.append("file", blob, "face.png");
        const state = await api("/player/me/avatar/face", { method: "POST", body: form });
        faceUrl = state.face_url; fillControls(); preview(); renderItems();
        cropDialog.close(); status("Tu cara quedó guardada.");
      } catch (error) { message.textContent = error.message; }
      finally { busy = false; updateActions(); cropDialog.querySelectorAll("button,input").forEach(e => { e.disabled = false; }); }
    });
  }
  async function chooseFile(event) {
    const file = event.target.files[0]; if (!file) return;
    if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      status("Elegí una foto JPG, PNG o WebP de hasta 5 MB.", true); fileInput.value = ""; return;
    }
    setupCrop(); disposeCrop(); objectUrl = URL.createObjectURL(file);
    const url = objectUrl;
    try {
      const image = new Image(); image.src = url; await image.decode();
      if (url !== objectUrl) return;
      if (image.naturalWidth * image.naturalHeight > 16_000_000 || Math.min(image.naturalWidth, image.naturalHeight) < 64) throw Error("Usá una foto de al menos 64 píxeles y hasta 16 megapíxeles.");
      cropImage = image;
      cropDialog.querySelector('[name="zoom"]').value = "1";
      cropDialog.querySelector('[name="x"]').value = cropDialog.querySelector('[name="y"]').value = "0";
      cropDialog.querySelector(".face-crop-status").textContent = "";
      drawCrop(); cropDialog.showModal();
    } catch (error) { disposeCrop(); status(error.message || "No se pudo abrir esa foto.", true); }
  }
  function select(label, field, values) {
    return `<label>${label}<select data-avatar-field="${field}">${values.map(([value, text]) => `<option value="${value}">${text}</option>`).join("")}</select></label>`;
  }
  function createRoot(stage) {
    root = document.createElement("section"); root.id = "player-wardrobe";
    root.setAttribute("aria-label", "Personalizar tu jugador");
    root.innerHTML = `<div class="wardrobe-intro"><p class="eyebrow">TU CARA. TU ESTILO. TU HISTORIA.</p><h3>Un jugador que se parezca a vos.</h3><p class="avatar-face-help"></p>
      <div class="wardrobe-actions"><button type="button" data-upload-face>Subir mi cara</button><button type="button" data-remove-face>Quitar cara</button></div>
      <input type="file" accept="image/jpeg,image/png,image/webp" data-face-file hidden></div>
      <div class="avatar-body-options">
        ${select("Complexión", "build", [["slim","Delgada"],["regular","Media"],["broad","Ancha"]])}
        ${select("Tono de piel", "skin", [["porcelain","Claro"],["sand","Arena"],["olive","Oliva"],["copper","Cobre"],["brown","Marrón"],["deep","Oscuro"]])}
      </div><div class="avatar-hair-options">
        ${select("Pelo", "hair", [["short","Corto"],["curls","Rulos"],["tied","Recogido"],["shaved","Rapado"]])}
        ${select("Color de pelo", "hair_color", [["dark","Negro"],["brown","Castaño"],["blond","Rubio"],["red","Colorado"],["grey","Canoso"]])}
        ${select("Barba", "beard", [["none","Sin barba"],["short","Corta"]])}
      </div>
      <div class="wardrobe-tabs" role="group" aria-label="Categorías de prendas">${Object.entries(slotLabels).map(([slot,label])=>`<button type="button" data-slot="${slot}" aria-pressed="${slot==='jersey'}">${label}</button>`).join("")}</div>
      <div class="wardrobe-items"></div><p class="wardrobe-save-hint"></p>
      <div class="wardrobe-actions"><button type="button" data-save-avatar>Guardar avatar</button><button type="button" data-reset-avatar>Descartar cambios</button><button type="button" data-retry-wardrobe hidden>Reintentar</button></div>
      <p class="wardrobe-status" role="status" aria-live="polite"></p>`;
    stage.append(root);
    fileInput = root.querySelector("[data-face-file]"); fileInput.addEventListener("change", chooseFile);
    root.querySelector("[data-upload-face]").addEventListener("click", () => fileInput.click());
    root.querySelector("[data-remove-face]").addEventListener("click", removeFace);
    root.querySelector("[data-save-avatar]").addEventListener("click", save);
    root.querySelector("[data-reset-avatar]").addEventListener("click", () => { draft = copy(saved); fillControls(); preview(); renderItems(); status("Cambios descartados."); });
    root.querySelector("[data-retry-wardrobe]").addEventListener("click", event => { event.target.hidden = true; loadWardrobe(); });
    root.addEventListener("change", event => {
      if (!event.target.matches("[data-avatar-field]")) return;
      draft[event.target.dataset.avatarField] = event.target.value; preview(); renderItems(); status("");
    });
    root.addEventListener("click", event => {
      const tab = event.target.closest("[data-slot]");
      if (tab) { activeSlot = tab.dataset.slot; renderItems(); return; }
      const button = event.target.closest("[data-item]");
      if (button && !busy) { draft.equipment[activeSlot] = button.dataset.item; preview(); renderItems(); status(""); }
    });
    document.addEventListener("maxio:face-loaded", renderItems);
  }
  function mount(player, stage) {
    if (!stage) return;
    if (!root?.isConnected) createRoot(stage);
    if (owner !== player.name) {
      owner = player.name; loaded = false; catalog = []; faceUrl = player.avatar?.face_url || null;
      saved = copy(player.avatar?.config || window.MaxioAvatar.defaults()); draft = copy(saved);
      fillControls(); renderItems(); preview();
    } else { preview(); }
    loadWardrobe();
  }
  window.MaxioWardrobe = Object.freeze({ mount });
})();
