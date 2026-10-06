/* Career rules come from the API. This module only presents earned history. */
(() => {
  const escape = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const progress = (value, target, label) => `<progress max="${target}" value="${Math.min(value, target)}" aria-label="${escape(label)}"></progress>`;
  const peerLink = name => `<a href="/web/player.html?username=${encodeURIComponent(name)}">${escape(name)} ↗</a>`;
  const metricLabel = item => item.target === 1 ? ({ partidos: "partido", victorias: "victoria" }[item.metric] || item.metric) : item.metric;

  function mount(player, root, { publicView = false } = {}) {
    if (!root) return;
    root.classList.add("career-mode");
    // Keep the barrio mural as the ambient identity layer behind the room.
    if (window.MaxioBarrio) {
      window.MaxioBarrio.mount(root, { name: player.name, avatar: player.avatar });
    } else {
      // Public profiles load only the career bundle; preserve the mural there too.
      root.classList.add("has-barrio");
      let scene = root.querySelector("#barrio-background");
      if (!scene) {
        scene = document.createElement("div");
        scene.id = "barrio-background";
        scene.className = "barrio-background";
        scene.setAttribute("aria-hidden", "true");
        scene.innerHTML = '<div class="barrio-world"><picture class="barrio-art"><source media="(max-width: 720px)" srcset="/images/barrio-courtyard-mobile-v1.png"><img src="/images/barrio-courtyard-v1.png" alt=""></picture></div><div class="barrio-light"></div>';
        root.prepend(scene);
      }
    }
    const shell = publicView ? root.querySelector(".public-card") : root.querySelector("#player-performance-profile");
    const hero = shell?.querySelector(".hero");
    if (!hero) return;
    hero.querySelector(".eyebrow").textContent = publicView ? "PERFIL DEL JUGADOR" : "TU PERFIL";
    const edit = hero.querySelector("#edit-avatar");
    if (edit) { edit.setAttribute("aria-label", "Editar perfil"); edit.querySelector("span").textContent = "Perfil"; }
    hero.querySelector(".barrio-avatar-actions")?.setAttribute("hidden", "");
    hero.querySelector(".barrio-avatar-space")?.setAttribute("hidden", "");
    shell.querySelector("#avatar-journey")?.remove();
    shell.querySelector(".cromo-vivo-hud")?.remove();
    let hub = shell.querySelector(".career-hub");
    let collection = shell.querySelector(".career-collection");
    if (!hub) { hub = document.createElement("section"); hub.className = "career-hub"; hero.after(hub); }
    if (!collection) { collection = document.createElement("section"); collection.className = "career-collection"; hub.after(collection); }
    // Keep the original identity nodes (and their handlers) inside one room card.
    let profileRoom = shell.querySelector('.locker-profile');
    if (!profileRoom) {
      profileRoom = document.createElement('section');
      profileRoom.className = 'locker-profile';
      profileRoom.setAttribute('aria-label', publicView ? 'Perfil y vestuario del jugador' : 'Tu perfil y vestuario');
      hero.before(profileRoom);
    }
    // The legacy profile renderer can reparent the header on refresh.
    if (hero.parentElement !== profileRoom) profileRoom.prepend(hero);
    if (hub.parentElement !== profileRoom) profileRoom.append(hub);
    const career = player.career;
    if (!career) {
      hero.querySelector(".career-title")?.remove();
      hub.innerHTML = `<p class="career-unavailable">${player.is_bot ? "Los bots completan equipos. La carrera de barrio es para jugadores humanos." : "La carrera no está disponible en este momento. Volvé a cargar el perfil para consultar tus logros."}</p>`;
      collection.replaceChildren();
      return;
    }
    const stage = Math.max(0, Math.min(6, Number(career.stage) || 0));
    root.dataset.careerStage = stage;
    let title = hero.querySelector(".career-title");
    if (!title) { title = document.createElement("div"); title.className = "career-title"; hero.querySelector(".hero-title").after(title); }
    title.innerHTML = `<span>RECORRIDO</span><strong>${escape(career.title)}</strong><small>${career.played} partidos · ${career.earned_count} logros</small>`;
    const rewardsOpen = hub.querySelector(".locker-rewards")?.open || false;
    window.MaxioLockerRoom?.mount(player, hub, { publicView });
    hub.querySelector('.locker-room')?.append(hero);
    hero.classList.add('locker-whiteboard');
    if (!hero.querySelector('.locker-tactics')) {
      const tactics = document.createElement('div');
      tactics.className = 'locker-tactics';
      tactics.setAttribute('aria-hidden', 'true');
      tactics.innerHTML = '<svg viewBox="0 0 280 85" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path opacity=".28" d="M8 8h263v68H9ZM140 9v67M9 25h25v33H9m262-33h-25v33h25"/><circle cx="140" cy="42" r="15" opacity=".28"/><path d="m48 51 12 13m-12 0 12-13m45-31 12 13m-12 0 12-13m77 22 12 13m-12 0 12-13"/><circle cx="84" cy="59" r="5"/><circle cx="154" cy="23" r="5"/><circle cx="224" cy="35" r="5"/><path d="M64 49q17-27 35-24m-7-5 8 5-7 6M119 28q31 30 56 24m-7-4 8 4-6 7M196 44l19-7m-7-4 9 3-5 7"/></svg>';
      hero.append(tactics);
    }
    const rewards = hub.querySelector(".locker-rewards");
    if (rewards) rewards.open = rewardsOpen;

    const earned = career.milestones.filter(item => item.earned);
    const pending = career.milestones.filter(item => !item.earned);
    const stamp = item => `<li class="career-stamp ${item.earned ? "earned" : "locked"}"><span class="career-stamp-mark" aria-hidden="true">${item.target}</span><div><span class="career-kicker">${item.earned ? "CONSEGUIDO" : "POR CONSEGUIR"}</span><strong>${escape(item.name)}</strong><p>${item.peer ? peerLink(item.peer) + " · " : ""}${item.target} ${escape(metricLabel(item))}</p><small>${escape(item.reward)}</small>${item.earned ? "" : progress(item.progress, item.target, item.name) + `<small>${item.progress} / ${item.target}</small>`}</div></li>`;
    const previouslyOpen = collection.querySelector("details")?.open || false;
    collection.innerHTML = `
      <div class="career-section-heading"><div><span class="career-kicker">LA HISTORIA SE JUEGA EN EQUIPO</span><h2>Socios y clásicos</h2></div></div>
      <div class="career-connections">${career.connections.map(connection => {
        const together = connection.kind === "duo";
        const label = together ? "TU DUPLA" : "TU RIVALIDAD";
        return `<article class="career-connection"><span class="career-kicker">${label}</span><h3>${escape(connection.title)}</h3>
          <p>${connection.peer ? peerLink(connection.peer) : together ? "Compartí equipo con otro jugador." : "Volvé a cruzarte con un rival."}</p>
          <p><b>${connection.count}</b> partidos ${together ? "en el mismo equipo" : "enfrentados"}</p>
          ${progress(connection.count, connection.target, connection.next_name)}
          <small>${connection.complete ? "Todos los sellos de esta relación conseguidos" : `${Math.min(connection.count, connection.target)} / ${connection.target} · ${escape(connection.next_name)}`}</small></article>`;
      }).join("")}</div>
      <div class="career-section-heading"><div><span class="career-kicker">LO QUE TE GANASTE JUGANDO</span><h2>Historial de logros</h2></div><span>${earned.length} logros</span></div>
      ${earned.length ? `<ul class="career-stamps">${earned.slice(-6).reverse().map(stamp).join("")}</ul>` : '<p class="career-empty">El primer sello llega con tu debut. Ganar, empatar o perder: salir a la cancha ya cuenta.</p>'}
      <details class="career-all" ${previouslyOpen ? "open" : ""}><summary>Ver recorrido completo · ${career.milestones.length} hitos</summary>
        <p>Los títulos reconocen partidos jugados; el ELO mide tu rendimiento. Cada sello se calcula con el historial registrado.</p>
        <ul class="career-stamps">${[...earned, ...pending].map(stamp).join("")}</ul>
      </details>`;
  }
  window.MaxioCareer = Object.freeze({ mount });
})();
