const playerToken=()=>sessionStorage.getItem("maxio_token");
const escapePlayer=value=>String(value??"").replace(/[&<>"']/g,character=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[character]));

async function playerApi(path){
  const response=await fetch(path,{headers:{Authorization:`Bearer ${playerToken()}`}});
  const body=await response.json().catch(()=>({}));
  if(!response.ok)throw Error(body.detail||"No pudimos cargar tu perfil.");
  return body;
}

function renderProfile(profile){
  const statLabels={tiro:"Tiro",ritmo:"Ritmo",fisico:"Físico",defensa:"Defensa",aura:"Aura"};
  const stats=Object.entries(statLabels).map(([key,label])=>`<article class="player-stat"><b>${Math.round(profile.stats[key])}</b><span>${label}</span></article>`).join("");
  const matches=profile.recent_matches.length?profile.recent_matches.map(match=>`<article><b>Partido #${match.match_id}</b><span>${new Date(match.date).toLocaleDateString("es-UY")} · ${match.result==="win"?"Ganado":match.result==="loss"?"Perdido":"Pendiente"}</span></article>`).join(""):'<p class="empty-player">Todavía no tenés partidos registrados.</p>';
  const allies=profile.relations.top_allies.length?profile.relations.top_allies.map(player=>`<article><b>${escapePlayer(player.name)}</b><span>${player.games_together} partidos juntos</span></article>`).join(""):'<p class="empty-player">Todavía no hay relaciones de juego.</p>';
  document.querySelector("#content").innerHTML=`<article class="player-hero"><p class="eyebrow">MI PERFIL</p><h1>${escapePlayer(profile.name)}</h1><p>ELO ${Math.round(profile.stats.elo)}</p><div class="player-summary"><article><b>${profile.matches_summary.played}</b><span>partidos</span></article><article><b>${profile.matches_summary.won}</b><span>ganados</span></article><article><b>${profile.matches_summary.winrate}%</b><span>victorias</span></article></div></article><section><div class="heading"><h2>Tu rendimiento</h2><span>ESTADÍSTICAS</span></div><div class="player-stats">${stats}</div></section><section><div class="heading"><h2>Últimos partidos</h2></div><div class="player-list">${matches}</div></section><section><div class="heading"><h2>Mejores aliados</h2></div><div class="player-list">${allies}</div></section>`;
}

async function bootPlayerDashboard(){
  try{
    const user=await playerApi("/maxio/users/me");
    if(user.is_admin){window.location.replace("/web/admin");return}
    const profile=await playerApi(`/player/${encodeURIComponent(user.username)}/profile`);
    renderProfile(profile);
  }catch(error){
    sessionStorage.removeItem("maxio_token");
    document.querySelector("#content").innerHTML=`<p class="empty-player">${escapePlayer(error.message)}. <a href="/web/">Volver a ingresar</a></p>`;
  }
}

document.querySelector("#logout").addEventListener("click",()=>{sessionStorage.removeItem("maxio_token");window.location.replace("/web/")});
bootPlayerDashboard();
