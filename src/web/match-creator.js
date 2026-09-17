(() => {
  const dialog = document.querySelector("#match-dialog");
  if (!dialog) return;
  const $ = selector => document.querySelector(selector);
  const state = { size: 5, players: new Map(), groups: [], catalog: new Map(), positions: new Map(), dragName: null };
  const esc = value => String(value).replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));
  const capacity = () => state.size * 2;
  const fail = message => { $("#match-error").textContent = message || ""; };
  const grouped = name => state.groups.findIndex(group => group.includes(name));
  const zoom = image => {
    const overlay = document.createElement("div");
    overlay.className = "card-zoom";
    overlay.innerHTML = `<img src="${image.src}" alt="Resumen ampliado del partido"><div class="zoom-controls"><button type="button" data-zoom-out aria-label="Alejar">−</button><button type="button" data-zoom-reset aria-label="Restablecer zoom">100%</button><button type="button" data-zoom-in aria-label="Acercar">+</button></div><button type="button" data-zoom-close aria-label="Cerrar">×</button>`;
    document.body.append(overlay);
    const target = overlay.querySelector("img"); let scale = 1, offsetX = 0, offsetY = 0, dragStart = null, pinchStart = null;
    const applyScale = () => { target.style.transform = `translate(${offsetX}px,${offsetY}px) scale(${scale})`; overlay.querySelector("[data-zoom-reset]").textContent = `${Math.round(scale * 100)}%`; };
    overlay.querySelector("[data-zoom-in]").addEventListener("click", event => { event.stopPropagation(); scale = Math.min(4, scale + .25); applyScale(); });
    overlay.querySelector("[data-zoom-out]").addEventListener("click", event => { event.stopPropagation(); scale = Math.max(.5, scale - .25); applyScale(); });
    overlay.querySelector("[data-zoom-reset]").addEventListener("click", event => { event.stopPropagation(); scale = 1; offsetX = 0; offsetY = 0; applyScale(); });
    overlay.addEventListener("wheel", event => { event.preventDefault(); scale = Math.max(.5, Math.min(4, scale + (event.deltaY < 0 ? .2 : -.2))); applyScale(); }, {passive:false});
    const pointers = new Map();
    const distance = () => { const points = [...pointers.values()]; return Math.hypot(points[0].clientX - points[1].clientX, points[0].clientY - points[1].clientY); };
    target.addEventListener("pointerdown", event => { target.setPointerCapture(event.pointerId); pointers.set(event.pointerId, event); if (pointers.size === 1) dragStart = {x:event.clientX - offsetX, y:event.clientY - offsetY}; else if (pointers.size === 2) pinchStart = {distance:distance(), scale}; event.preventDefault(); });
    target.addEventListener("pointermove", event => { if (!pointers.has(event.pointerId)) return; pointers.set(event.pointerId, event); if (pointers.size === 2 && pinchStart) scale = Math.max(.5, Math.min(4, pinchStart.scale * distance() / pinchStart.distance)); else if (pointers.size === 1 && dragStart) { offsetX = event.clientX - dragStart.x; offsetY = event.clientY - dragStart.y; } applyScale(); event.preventDefault(); });
    const endPointer = event => {
      pointers.delete(event.pointerId);
      if (pointers.size < 2) pinchStart = null;
      if (pointers.size === 1) {
        const point = [...pointers.values()][0];
        dragStart = {x: point.clientX - offsetX, y: point.clientY - offsetY};
      } else if (pointers.size === 0) dragStart = null;
    };
    target.addEventListener("pointerup", endPointer); target.addEventListener("pointercancel", endPointer);
    const close = () => overlay.remove();
    overlay.addEventListener("click", event => { if (event.target === overlay || event.target.closest("[data-zoom-close]")) close(); });
    document.addEventListener("keydown", function escape(event) { if (event.key === "Escape") { close(); document.removeEventListener("keydown", escape); } });
  };

  const style = document.createElement("style");
  style.textContent = `#match-dialog{width:min(94vw,720px);max-height:94dvh}.pitch-builder{padding:22px;display:grid;gap:14px}.pitch-builder h2{margin:0}.pitch-builder h3{margin:0;font-size:14px}.pitch-builder h3 span{font-size:10px;color:var(--muted);font-weight:normal}.pitch-builder section{display:grid;gap:8px}.pitch-builder .player-picks{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;max-height:140px;overflow:auto}.pitch-builder .player-pick{border:1px solid var(--line);border-radius:10px;background:#172740;color:var(--ink);padding:7px;display:flex;align-items:center;gap:7px;text-align:left}.pitch-builder .player-pick.picked{opacity:.42;filter:saturate(.45)}.pitch-builder .player-pick img,.pitch-player img,.selected-player img{width:30px;height:30px;object-fit:cover;border-radius:8px;margin:0;border:0;background:#203551}.pitch-builder .player-pick span{display:grid;min-width:0}.pitch-builder .player-pick b{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pitch-builder .player-pick small{font-size:9px;color:var(--muted);min-height:0}.pitch-builder .player-pick i{margin-left:auto;color:var(--lime)}.football-pitch{position:relative;aspect-ratio:1.5;border:1px solid #4c6e9e;border-radius:12px;overflow:hidden;background:#1d3d6c url('/images/template_match_card_relations.png') center/cover no-repeat}.pitch-hint{position:absolute;inset:0;display:grid;place-items:center;color:#dcecff;font-size:13px;text-shadow:0 1px 5px #000}.pitch-player{position:absolute;transform:translate(-50%,-50%);z-index:2;border:0;background:transparent;color:#fff;display:grid;justify-items:center;gap:2px;padding:0;cursor:grab}.pitch-player img{width:44px;height:44px;border:2px solid var(--lime);border-radius:13px}.pitch-player span{font-size:9px;font-weight:bold;max-width:72px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:0 1px 3px #000}.pitch-player em{font-size:8px;font-style:normal;background:#0b1728dd;padding:1px 4px;border-radius:4px}.pitch-player.team-group img{border-color:#ffce63;box-shadow:0 0 0 3px #ffce6344}.selected-players{display:flex;flex-wrap:wrap;gap:6px}.selected-player{display:flex;gap:5px;align-items:center;background:#1a2b45;border-radius:9px;padding:4px 6px 4px 4px;font-size:11px}.selected-player em{font-size:9px;font-style:normal;color:var(--lime)}.selected-player button{border:0;background:transparent;color:#ff9b82;font-size:18px}.match-capacity{padding:10px;border-radius:10px;background:#0c192b;color:var(--muted);font-size:12px}.match-capacity b{font-size:18px;color:var(--lime)}.pitch-builder input[type="datetime-local"]{width:100%;padding:11px;border-radius:10px;background:#122038;color:var(--ink);border:1px solid var(--line)}.pitch-builder select{width:100%;padding:11px;border-radius:10px;background:#122038;color:var(--ink);border:1px solid var(--line)}.pitch-builder>#match-result img{width:100%;border-radius:10px}.teams-result{display:grid;grid-template-columns:1fr 1fr;gap:8px}.teams-result>div{padding:9px;background:#0c192b;border-radius:9px;font-size:12px}.teams-result b{color:var(--lime)}.teams-result ul{list-style:none;margin:8px 0 0;padding:0}.result-player{position:relative;display:flex;align-items:center;justify-content:center;min-height:28px}.result-player-name{min-width:0;max-width:calc(100% - 44px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;text-align:center}.result-player-icons{position:absolute;right:0;top:50%;transform:translateY(-50%);display:flex;width:42px;justify-content:flex-start;gap:3px}.result-player-icons img{width:18px;height:18px;object-fit:contain;border-radius:4px}.result-player-icons img[title]{cursor:help}@media(min-width:600px){.pitch-builder .player-picks{grid-template-columns:repeat(3,minmax(0,1fr))}}`;
  document.head.append(style);
  const resultLayoutStyle = document.createElement("style");
  resultLayoutStyle.textContent = `.teams-result>div{overflow:hidden}.teams-result ul.result-team-list{width:min(100%,180px);margin-inline:auto}.result-team-list .result-player{display:grid;align-items:center;min-height:29px;width:180px;max-width:100%;padding:0}.result-team-list .result-player.left{grid-template-columns:140px 40px}.result-team-list .result-player.right{grid-template-columns:40px 140px}.result-team-list .result-player.left .result-player-name{text-align:right;padding-right:8px}.result-team-list .result-player.right .result-player-name{grid-column:2;text-align:left;padding-left:8px}.result-team-list .result-player.right .result-player-icons{grid-column:1;grid-row:1;justify-content:flex-end;padding-right:4px}.result-team-list .result-player-icons{position:static;display:flex;align-items:center;width:40px;height:29px;gap:3px}.result-team-list .result-player-icons img{border:0!important;background:transparent!important;box-shadow:none!important;outline:0;width:18px;height:18px}`;
  document.head.append(resultLayoutStyle);
  const zoomStyle = document.createElement("style");
  zoomStyle.textContent = `.summary-image-button{position:relative;border:0;padding:0;background:transparent;cursor:zoom-in;width:100%}.summary-image-button img{display:block;width:100%;border-radius:10px}.summary-image-button span{position:absolute;right:8px;bottom:8px;background:#071222dd;color:#fff;border-radius:7px;padding:5px 8px;font-size:10px}.card-zoom{position:fixed;inset:0;z-index:1000;background:#020711ee;display:grid;place-items:center;padding:14px;cursor:zoom-out}.card-zoom img{max-width:100%;max-height:100%;object-fit:contain;border-radius:10px;box-shadow:0 12px 50px #000}.card-zoom button{position:absolute;top:12px;right:14px;width:38px;height:38px;border:1px solid #ffffff55;border-radius:50%;background:#12233ddd;color:#fff;font-size:25px;cursor:pointer}`;
  document.head.append(zoomStyle);
  const zoomControlsStyle = document.createElement("style");
  zoomControlsStyle.textContent = `.card-zoom{overflow:auto;display:flex;align-items:center;justify-content:center}.card-zoom>img{flex:none;max-width:100%;max-height:100%;transform-origin:center center}.card-zoom>[data-zoom-close]{z-index:2}.zoom-controls{position:fixed;z-index:3;left:50%;bottom:18px;transform:translateX(-50%);display:flex;gap:6px;padding:6px;border-radius:12px;background:#12233ddd;border:1px solid #ffffff33}.zoom-controls button{position:static;width:40px;height:34px;border:1px solid #ffffff55;border-radius:8px;background:#1d3556;color:#fff;font-size:18px;cursor:pointer}.zoom-controls [data-zoom-reset]{width:58px;font-size:12px}`;
  document.head.append(zoomControlsStyle);
  const interactionStyle = document.createElement("style");
  interactionStyle.textContent = `.card-zoom,.card-zoom>img{touch-action:none}.card-zoom>img{cursor:grab}.card-zoom>img:active{cursor:grabbing}.teams-result>div{min-width:0;overflow:hidden}.teams-result ul.result-team-list{width:100%;max-width:100%;margin:8px 0 0;padding:0;list-style:none}.result-team-list .result-player{display:flex!important;align-items:center;justify-content:center;width:100%;min-height:29px;padding:2px 4px!important}.result-team-list .result-player-name,.result-team-list .result-player.left .result-player-name,.result-team-list .result-player.right .result-player-name{display:block;grid-column:auto!important;max-width:100%;padding:0!important;overflow-wrap:anywhere;white-space:normal;overflow:visible;text-overflow:clip;text-align:center!important}.result-player-icons{display:none!important}`;
  document.head.append(interactionStyle);
  dialog.innerHTML = `<section class="match-builder pitch-builder"><button id="close-match" class="close" type="button">×</button><p class="eyebrow">NUEVO PARTIDO</p><h2>Armá la cancha</h2><p class="match-help">Arrastrá jugadores a la cancha. Soltá un avatar sobre otro para crear un grupo que el balanceo mantendrá junto.</p><label>Elegir fecha y hora<input id="match-date" type="datetime-local" required></label><label>Tamaño de equipo<select id="team-size"></select></label><div class="match-capacity"><b id="real-count">0</b> reales <span id="bot-count"></span></div><div id="football-pitch" class="football-pitch"><span class="pitch-hint">Arrastrá jugadores hasta acá</span></div><section><h3>Sugeridos</h3><div id="match-suggestions" class="player-picks"></div></section><section><input id="player-search" type="search" placeholder="Buscar jugador"><div id="player-results" class="player-picks"></div></section><section><h3>Convocados <span id="selection-status"></span></h3><div id="selected-players" class="selected-players"></div></section><small id="match-error"></small><button id="create-match" class="save" type="button">Balancear y crear partido</button><div id="match-result" hidden></div></section>`;

  function remember(players) { players.forEach(player => state.catalog.set(player.name, player)); return players; }
  function playerCard(player) {
    const added = state.players.has(player.name);
    return `<button type="button" draggable="true" class="player-pick ${added ? "picked" : ""}" data-player-source data-name="${esc(player.name)}" ${added ? "disabled" : ""}><img src="/player/${encodeURIComponent(player.name)}/photo" alt=""><span><b>${esc(player.name)}</b><small>${player.cant_partidos || 0} partidos</small></span><i>↗</i></button>`;
  }
  function defaultPosition(index) { return [[20,24],[45,18],[70,26],[28,52],[56,50],[78,57],[18,76],[47,80],[74,76]][index % 9]; }
  function refreshPitch() {
    const pitch = $("#football-pitch"), names = [...state.players.keys()];
    pitch.querySelectorAll(".pitch-player").forEach(node => node.remove());
    pitch.querySelector(".pitch-hint").hidden = names.length > 0;
    names.forEach((name, index) => {
      const player = state.players.get(name), [left, top] = state.positions.get(name) || defaultPosition(index), group = grouped(name);
      const node = document.createElement("button");
      node.type = "button"; node.draggable = true; node.dataset.pitchPlayer = ""; node.dataset.name = name;
      node.className = `pitch-player ${group >= 0 ? `team-group group-${group % 4}` : ""}`;
      node.style.left = `${left}%`; node.style.top = `${top}%`;
      node.innerHTML = `<img src="/player/${encodeURIComponent(name)}/photo" alt="${esc(name)}"><span>${esc(name)}</span>${group >= 0 ? `<em>Equipo ${group + 1}</em>` : ""}`;
      pitch.append(node);
    });
  }
  function refresh() {
    const people = [...state.players.values()];
    $("#selected-players").innerHTML = people.length ? people.map(player => {
      const group = grouped(player.name);
      return `<span class="selected-player"><img src="/player/${encodeURIComponent(player.name)}/photo" alt="">${esc(player.name)}${group >= 0 ? `<em>Equipo ${group + 1}</em>` : ""}<button type="button" data-remove="${esc(player.name)}">×</button></span>`;
    }).join("") : "<span class=empty>Arrastrá jugadores a la cancha.</span>";
    const count = people.length, bots = capacity() - count;
    $("#real-count").textContent = count; $("#bot-count").textContent = bots >= 0 ? `· ${bots} bot${bots === 1 ? "" : "s"} para completar` : "· excede la capacidad";
    $("#selection-status").textContent = `${count}/${capacity()} reales`; $("#create-match").disabled = count < 2 || count > capacity(); refreshPitch();
  }
  function add(name, position) {
    const player = state.catalog.get(name); if (!player) return;
    if (!state.players.has(name) && state.players.size >= capacity()) return fail(`El tamaño elegido admite ${capacity()} jugadores reales.`);
    state.players.set(name, player); if (position) state.positions.set(name, position); refresh();
  }
  function remove(name) { state.players.delete(name); state.positions.delete(name); state.groups = state.groups.map(group => group.filter(member => member !== name)).filter(group => group.length > 1); refresh(); }
  function joinTeam(first, second) {
    if (first === second) return; if (!state.players.has(first)) add(first); if (!state.players.has(second)) add(second);
    const a = grouped(first), b = grouped(second); if (a >= 0 && a === b) return;
    const merged = new Set([first, second]); if (a >= 0) state.groups[a].forEach(name => merged.add(name)); if (b >= 0) state.groups[b].forEach(name => merged.add(name));
    state.groups = state.groups.filter((_, index) => index !== a && index !== b); state.groups.push([...merged]); fail(""); refresh();
  }
  async function directory(query = "") {
    if (!query.trim()) { $("#player-results").innerHTML = ""; return; }
    const players = remember(await api(`/player/directory?query=${encodeURIComponent(query)}&limit=30`));
    $("#player-results").innerHTML = players.length ? players.map(playerCard).join("") : "<span class=empty>No hay coincidencias.</span>";
  }
  async function suggestions() {
    const me = await api("/maxio/users/me"), [owner, teammates] = await Promise.all([api(`/player/${encodeURIComponent(me.username)}`), api(`/player/${encodeURIComponent(me.username)}/top_teammates?limit=5&exclude_bots=true`)]);
    const players = remember([owner, ...teammates].filter((player, index, all) => all.findIndex(other => other.name === player.name) === index)); $("#match-suggestions").innerHTML = players.map(playerCard).join("");
  }
  function relativePosition(event) { const box = $("#football-pitch").getBoundingClientRect(); return [Math.max(6, Math.min(94, (event.clientX - box.left) / box.width * 100)), Math.max(8, Math.min(92, (event.clientY - box.top) / box.height * 100))]; }
  async function open() {
    state.players.clear(); state.groups = []; state.positions.clear(); fail(""); $("#match-result").hidden = true; $("#match-result").innerHTML = "";
    const now = new Date(), pad = value => String(value).padStart(2, "0");
    $("#match-date").value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
    $("#player-search").value = ""; $("#player-results").innerHTML = "";
    dialog.classList.remove("match-finished");
    dialog.querySelectorAll(".pitch-builder > *").forEach(element => { element.hidden = false; }); $("#match-result").hidden = true;
    $("#team-size").innerHTML = Array.from({length:9}, (_, index) => `<option value="${index + 2}" ${index + 2 === state.size ? "selected" : ""}>${index + 2} por equipo</option>`).join(""); dialog.showModal(); refresh();
    try { await suggestions(); } catch (error) { fail(error.message); }
  }
  async function create() {
    if (state.players.size < 2) return fail("Agregá al menos dos jugadores reales."); const button = $("#create-match"); button.disabled = true; button.textContent = "Balanceando…"; fail("");
    try {
      const matchDate = $("#match-date").value;
      if (!matchDate) { button.disabled = false; button.textContent = "Balancear y crear partido"; return fail("Elegí la fecha y hora del partido."); }
      const match = await api("/match/matches", {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({date:matchDate,max_players:capacity()})});
      for (const player of state.players.values()) await api(`/match/matches/${match.id}/players/${player.id}`, {method:"POST"});
      if (state.groups.length) await api(`/match/matches/${match.id}/pre-set-groups`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({groups:state.groups})});
      const result = await api(`/match/matches/${match.id}/generate-teams`, {method:"POST"}), image = await fetch(`/match/matches/${match.id}/match-card`, {method:"POST",headers:{Authorization:`Bearer ${token()}`}}), imageUrl = image.ok ? URL.createObjectURL(await image.blob()) : "";
      const team = value => (value?.players || []).map(player => `<li class="result-player"><span class="result-player-name">${esc(player.username || player.name)}</span></li>`).join("");
      $("#match-result").innerHTML = `<h3>Partido #${match.id} creado</h3><div class="teams-result"><div><b>Equipo 1</b><ul class="result-team-list">${team(result.team1)}</ul></div><div><b>Equipo 2</b><ul class="result-team-list">${team(result.team2)}</ul></div></div>${imageUrl ? `<button class="summary-image-button" type="button" aria-label="Ampliar resumen"><img src="${imageUrl}" alt="Resumen del partido"><span>Tocar para ampliar</span></button>` : ""}`;
      $("#match-result").hidden = false;
      dialog.classList.add("match-finished");
      dialog.querySelectorAll(".pitch-builder > *:not(#close-match):not(#match-result)").forEach(element => { element.hidden = true; });
      $("#match-result img")?.addEventListener("click", event => { event.preventDefault(); zoom(event.currentTarget); });
      button.textContent = "Partido creado";
    } catch (error) { fail(error.message); button.disabled = false; button.textContent = "Balancear y crear partido"; }
  }
  $("#new-match")?.addEventListener("click", open); $("#close-match").addEventListener("click", () => dialog.close()); $("#team-size").addEventListener("change", event => { state.size = Number(event.target.value); refresh(); });
  $("#player-search").addEventListener("input", event => directory(event.target.value).catch(error => fail(error.message))); $("#create-match").addEventListener("click", create);
  dialog.addEventListener("dragstart", event => { const source = event.target.closest("[data-player-source],[data-pitch-player]"); if (source) { state.dragName = source.dataset.name; event.dataTransfer.effectAllowed = "move"; } });
  dialog.addEventListener("click", event => { const source = event.target.closest("[data-player-source]"); if (source && !source.disabled) add(source.dataset.name); const removeButton = event.target.closest("[data-remove]"); if (removeButton) remove(removeButton.dataset.remove); });
  const pitch = $("#football-pitch"); pitch.addEventListener("dragover", event => event.preventDefault()); pitch.addEventListener("drop", event => { event.preventDefault(); const name = state.dragName; if (!name) return; const target = event.target.closest("[data-pitch-player]"); if (target && target.dataset.name !== name) joinTeam(name, target.dataset.name); else add(name, relativePosition(event)); state.dragName = null; });
  let touchDrag = null;
  dialog.addEventListener("pointerdown", event => { const source = event.target.closest("[data-player-source],[data-pitch-player]"); if (source && !source.disabled) touchDrag = { name: source.dataset.name, x: event.clientX, y: event.clientY }; });
  dialog.addEventListener("pointerup", event => {
    if (!touchDrag) return;
    const moved = Math.hypot(event.clientX - touchDrag.x, event.clientY - touchDrag.y) > 8;
    const box = pitch.getBoundingClientRect();
    const onPitch = event.clientX >= box.left && event.clientX <= box.right && event.clientY >= box.top && event.clientY <= box.bottom;
    if (moved && onPitch) {
      const target = document.elementFromPoint(event.clientX, event.clientY)?.closest("[data-pitch-player]");
      if (target && target.dataset.name !== touchDrag.name) joinTeam(touchDrag.name, target.dataset.name);
      else add(touchDrag.name, [(event.clientX - box.left) / box.width * 100, (event.clientY - box.top) / box.height * 100]);
    }
    touchDrag = null;
  });
})();
