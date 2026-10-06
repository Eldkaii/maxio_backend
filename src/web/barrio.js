/* Courtyard art and wall slots. The player's identity is rendered by MaxioAvatar. */
(() => {
  // Coordinates are percentages in the corresponding background artwork.
  // Each preset has its own framing; zones remain attached to the actual walls.
  const zones = Object.freeze([
    { id: "back-graffiti-left", wall: "back", kind: "graffiti", desktop: [16, 23, 23, 27], mobile: [22, 24, 26, 22] },
    { id: "back-graffiti-right", wall: "back", kind: "graffiti", desktop: [61, 22, 22, 27], mobile: [53, 25, 25, 22] },
    { id: "back-free-text", wall: "back", kind: "text", desktop: [37, 54, 24, 10], mobile: [29, 52, 42, 9] },
    { id: "left-free-text", wall: "left", kind: "text", desktop: [1, 35, 7, 23], mobile: [2, 32, 13, 26] },
    { id: "right-graffiti", wall: "right", kind: "graffiti", desktop: [94, 30, 5, 28], mobile: [87, 32, 11, 24] },
  ].map(zone => Object.freeze({ ...zone, desktop: Object.freeze(zone.desktop), mobile: Object.freeze(zone.mobile) })));

  function mount(root, { name, avatar } = {}) {
    if (!root) return;
    let scene = root.querySelector("#barrio-background");
    if (!scene) {
      scene = document.createElement("div");
      scene.id = "barrio-background";
      scene.className = "barrio-background";
      scene.setAttribute("aria-hidden", "true");
      scene.innerHTML = `
        <div class="barrio-world">
          <picture class="barrio-art"><source media="(max-width: 720px)" srcset="/images/barrio-courtyard-mobile-v1.png"><img src="/images/barrio-courtyard-v1.png" alt="" fetchpriority="high"></picture>
          <div class="barrio-zones"></div>
        </div>
        <div class="barrio-contact-shadow"></div>
        <img class="identity-character barrio-avatar" data-player-avatar alt="" decoding="async">
        <div class="barrio-light"></div>`;
      const slots = scene.querySelector(".barrio-zones");
      zones.forEach(zone => {
        const slot = document.createElement("div");
        slot.className = "barrio-zone";
        slot.dataset.zoneId = zone.id;
        slot.dataset.wall = zone.wall;
        slot.dataset.kind = zone.kind;
        ["desktop", "mobile"].forEach(preset => {
          ["x", "y", "width", "height"].forEach((key, i) => slot.style.setProperty(`--${preset}-${key}`, `${zone[preset][i]}%`));
        });
        slots.append(slot);
      });
      root.prepend(scene);
    }
    root.classList.add("has-barrio");
    scene.dataset.player = name || "";
    if (avatar) window.MaxioAvatar.setState(avatar);
    else window.MaxioAvatar.paint();
  }

  window.MaxioBarrio = Object.freeze({ mount, zones });
})();
