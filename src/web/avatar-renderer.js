/* Deterministic paper-doll illustration. Identity and equipment share fixed anchors. */
(() => {
  const skins = { porcelain: "#e9c2a9", sand: "#dcb08c", olive: "#bd8d65", copper: "#aa704d", brown: "#815237", deep: "#583b30" };
  const hairColors = { dark: "#262629", brown: "#594136", blond: "#b69862", red: "#8f4d36", grey: "#9faaa9" };
  const defaults = () => ({ version: 1, build: "regular", skin: "olive", hair: "short", hair_color: "dark", beard: "none", equipment: { jersey: "training", shorts: "basic", boots: "classic", cap: "none", tattoo: "none" } });
  const clone = value => JSON.parse(JSON.stringify(value));
  let current = { config: defaults(), face_url: null }, faceData = "", generation = 0;
  const faces = new Map();

  function svg(config = defaults(), face = "") {
    const c = { ...defaults(), ...config, equipment: { ...defaults().equipment, ...config.equipment } };
    const skin = skins[c.skin] || skins.olive, hair = hairColors[c.hair_color] || hairColors.dark;
    const width = { slim: .87, regular: 1, broad: 1.14 }[c.build] || 1;
    const e = c.equipment, bolso = e.jersey === "bolso", manya = e.jersey === "manya";
    const shirt = bolso ? "#e4e5dd" : manya ? "#cbab35" : "#34495b";
    const trim = bolso ? "#a84843" : manya ? "#272c30" : "#a5b1b1";
    const shorts = e.shorts === "winner" ? "#d2d4c9" : "#283740";
    const boot = e.boots === "lime" ? "#c0cb70" : "#30383b";
    const tattoo = e.tattoo === "lightning" ? '<path d="M102 279l-10 21 8-2-5 21 16-27-8 3 6-16z" fill="#354048" opacity=".8"/>'
      : e.tattoo === "bands" ? '<path d="M193 448l30-3m-30 12l30-3" stroke="#354048" stroke-width="6" opacity=".8"/>' : "";
    const safeFace = /^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(face) ? face : "";
    const head = 'M146 78Q145 43 180 42Q216 42 216 79L210 116Q198 139 181 140Q161 137 151 117Z';
    const hairShape = c.hair === "shaved" ? '<path d="M147 74q-1-32 33-32t35 32q-11-22-34-21t-34 21" opacity=".45"/>'
      : c.hair === "tied" ? '<ellipse cx="220" cy="49" rx="15" ry="16"/><path d="M145 88q-8-51 34-52 46-2 38 52l-10-19q-17-1-27-18-10 19-27 22z"/>'
      : c.hair === "curls" ? '<path d="M145 86q-16-13-5-26-6-18 10-21 6-15 20-8 11-11 23 0 18-6 21 9 19 5 10 23 7 13-10 24l-6-19q-12 5-17-7-15 10-25-1l-13 12z"/>'
      : '<path d="M146 88q-10-43 18-48 17-14 46-3l-5 10q20 7 11 40l-9-18-4-12q-23 14-49 6z"/>';
    const beard = c.beard === "short" ? `<path d="M153 104q5 12 14 11l13 5 15-5q9 1 16-13l-5 24q-11 16-25 16t-26-18z" fill="${hair}" opacity=".74"/>` : "";
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 640" role="img" aria-label="Jugador ilustrado" data-build="${['slim','regular','broad'].includes(c.build)?c.build:'regular'}">
      <defs>
        <linearGradient id="skin" x2="1" y2=".4"><stop stop-color="${skin}"/><stop offset=".6" stop-color="${skin}"/><stop offset="1" stop-color="#654836"/></linearGradient>
        <linearGradient id="cloth" x2=".9" y2="1"><stop stop-color="${shirt}"/><stop offset=".6" stop-color="${shirt}"/><stop offset="1" stop-color="${bolso?'#a5b4b8':manya?'#89732e':'#24343f'}"/></linearGradient>
        <clipPath id="head"><path d="${head}"/></clipPath>
        <clipPath id="shirt"><path d="M151 150q29 16 57 0l34 17 19 56-32 13-9-24 13 114q-55 12-107-1l10-113-11 26-31-16 19-55z"/></clipPath>
      </defs>
      <g stroke="#253038" stroke-width="2" stroke-linejoin="round" stroke-linecap="round">
        <g transform="translate(${180*(1-width)} 0) scale(${width} 1)">
          <!-- Skin, then tattoos, then fabric: sleeves always cover the skin beneath. -->
          <g fill="url(#skin)">
            <path d="M134 368l39 4-5 86-6 90-29 0-6-90z"/>
            <path d="M187 372l39-5 5 92-7 90-28 0-8-91z"/>
            <path d="M114 196l24 9-15 69-15 69-17 13-11-6 3-20 13-62z"/>
            <path d="M224 204l24-9 17 78 10 58 4 17-10 9-18-15-11-67z"/>
            <path d="M165 125v27q16 20 31 0v-27"/>
          </g>
          <path d="M88 331l8 6m-10 3l8 6m169-14l-7 7m9 1l-6 7" fill="none" stroke="#795641" stroke-width="1.5"/>
          ${tattoo}
          <path d="M128 312q53 10 102 0l6 83-45 5-12-45-10 45-44-5z" fill="${shorts}"/>
          <path d="M130 325q46 8 96 0m-49 5l-5 13m11-13l5 13m-7 16v-13" fill="none" stroke="#899291" stroke-width="1.5"/>
          ${e.shorts==='winner'?'<path d="M128 338l-1 45m103-45l4 45" stroke="#a3ac5b" stroke-width="6"/>':''}
          <path d="M151 150q29 16 57 0l34 17 19 56-32 13-9-24 13 114q-55 12-107-1l10-113-11 26-31-16 19-55z" fill="url(#cloth)"/>
          ${manya?'<g clip-path="url(#shirt)" fill="#272e31"><path d="M127 146h18v188h-18zm39 0h24v188h-24zm44 0h22v188h-22zm37 0h22v188h-22z"/></g>':''}
          <path d="M152 153q28 27 55 0m-110 65l27 14m109-3l24-10" fill="none" stroke="${trim}" stroke-width="5"/>
          <path d="M142 184l-5 39m78-39l5 39m-83 80l13-5m53 4l19 7m-85 8q43 7 86 0" fill="none" stroke="${bolso?'#9daeb0':'#182b35'}" stroke-width="1.5" opacity=".5"/>
          ${bolso||manya?`<path d="M194 183h17v17l-8 8-9-8z" fill="${bolso?'#304858':'#292d2a'}" stroke="${bolso?'#d0d0c7':'#d0b348'}"/><text x="202.5" y="198" fill="${bolso?'#f0eee6':'#d0b348'}" stroke="none" text-anchor="middle" font-size="10" font-family="sans-serif" font-weight="700">${bolso?'N':'P'}</text>`:'<path d="M197 187l4 6 5-9" fill="none" stroke="#b0ba8f" stroke-width="2"/>'}
          <path d="M129 489l36 1-4 62-29 3zM192 491l36-2-4 66-29-3z" fill="#d6d8cd"/>
          <path d="M133 500l27 1m-27 6l27 1m38-7l25-1m-25 7l25-1" fill="none" stroke="#8b9999" stroke-width="2"/>
          <g fill="${boot}"><path d="M132 545q14 8 29 1l3 27-7 16-43 5q-10-8 0-16l15-15z"/><path d="M195 546q15 7 29-1l6 20 18 14q8 9-2 14l-43-5-10-15z"/></g>
          <path d="M115 589l44-4m43 0l43 5" fill="none" stroke="#929b8a" stroke-width="4"/>
          <path d="M132 562l19 4m-23 3l21 4m59-7l18-4m-17 12l21-5" fill="none" stroke="${e.boots==='lime'?'#47503d':'#a8b0a3'}" stroke-width="2"/>
          <path d="M121 594v4m15-5v4m15-5v4m57-5v4m14-2v4m14-2v4" stroke="#27352f" stroke-width="4"/>
        </g>
        <ellipse cx="146" cy="94" rx="6" ry="11" fill="${skin}"/><ellipse cx="215" cy="94" rx="6" ry="11" fill="${skin}"/>
        <path d="${head}" fill="url(#skin)"/>
        ${safeFace ? `<image href="${safeFace}" x="142" y="42" width="76" height="98" preserveAspectRatio="xMidYMid slice" clip-path="url(#head)"/>` : `
          <path d="M157 86l12-2m24 0l11 2" stroke="${hair}" stroke-width="3"/>
          <path d="M161 94h4m30 0h4" stroke="#34332f" stroke-width="3"/>
          <path d="M180 96l-3 12 5 1m-11 12q10 5 20-1" stroke="#714e3d" fill="none" stroke-width="1.5"/>
          ${beard}<g fill="${hair}" stroke="${hair}">${hairShape}</g>`}
        ${e.cap==='street'?'<path d="M143 72q0-35 38-35t38 35l-20-4q-23-6-56 4z" fill="#354b58"/><path d="M151 67q24-9 50 1l25 12q-36 5-68-1l-15-7z" fill="#283c46"/><path d="M181 38v19" stroke="#72827f"/><path d="M176 51l5-4 5 4-5 5z" fill="#b3bf78" stroke="none"/>':''}
      </g>
    </svg>`;
  }

  const source = (config, face) => `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg(config, face))}`;
  function paint() {
    const src = source(current.config, faceData);
    document.querySelectorAll("[data-player-avatar]").forEach(image => {
      image.src = src;
      image.dataset.avatarJersey = current.config?.equipment?.jersey || "training";
      image.dataset.avatarFace = faceData ? "own" : "neutral";
    });
  }
  async function setState(state = {}) {
    const id = ++generation;
    current = { config: clone(state.config || defaults()), face_url: state.face_url || null };
    faceData = faces.get(current.face_url) || "";
    paint();
    if (!current.face_url || faceData) return;
    // Only this app's face endpoint can be embedded in the SVG.
    let url;
    try { url = new URL(current.face_url, location.origin); } catch { return; }
    if (url.origin !== location.origin || !/^\/player\/[^/]+\/avatar\/face$/.test(url.pathname)) return;
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok || !response.headers.get("content-type")?.startsWith("image/png")) return;
      const blob = await response.blob();
      if (blob.size > 1024 * 1024) return;
      const data = await new Promise((resolve, reject) => {
        const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(blob);
      });
      if (id !== generation) return;
      faces.clear(); faces.set(current.face_url, data); faceData = data; paint();
      document.dispatchEvent(new Event("maxio:face-loaded"));
    } catch { /* A missing image leaves a neutral illustrated face. */ }
  }
  window.MaxioAvatar = Object.freeze({ defaults, svg, source, setState, paint, face: () => faceData });
})();
