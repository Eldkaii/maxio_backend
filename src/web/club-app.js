/* Three club rooms, backed by the existing profile and authenticated histories. */
(() => {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const num = value => Number.isFinite(Number(value)) ? Number(value) : 0;
  const labels = {win:'Victoria',draw:'Empate',loss:'Derrota',pending:'Pendiente'};
  const skills = {tiro:'Tiro',ritmo:'Ritmo',fisico:'Físico',defensa:'Defensa',aura:'Aura'};
  // Orden físico de la panorámica y de la barra: Cantina, Barrio, Vitrina y Vestuario.
  const rooms = {cantina:['La mesa de los de siempre','Cantina'],barrio:['Donde competimos','Barrio'],vitrina:['Tu historia, a la vista','Vitrina'],vestuario:['Nos vemos en la cancha','Vestuario']};
  let root, player, active='vitrina', generation=0;
  let histories;
  document.addEventListener('submit',event=>{
    if(event.target.matches('#login-form,#register-form')){active='vitrina';generation++;}
  },true);
  const icon = kind => {
    const paths = {
      cup:'M8 4h16v7c0 7-4 10-8 10S8 18 8 11V4Zm0 3H3v4c0 5 3 7 8 7m13-11h5v4c0 5-3 7-8 7M16 21v6m-6 2h12',
      medal:'m9 2 7 9 7-9M11 2l5 6 5-6M16 12a8 8 0 1 0 0 16 8 8 0 0 0 0-16Zm0 4 1.5 3 3.5.5-2.5 2.5.5 3.5-3-1.5-3 1.5.5-3.5-2.5-2.5 3.5-.5Z',
      trophy:'M10 29h12l-2-5h-8l-2 5Zm6-5V14m0-12 4 7 8 1-6 6 1 8-7-4-7 4 1-8-6-6 8-1Z',
      shirt:'m11 5-8 5 4 7 4-2v14h10V15l4 2 4-7-8-5c-1 5-9 5-10 0Z',
      table:'M3 15h26M7 15v14m18-14v14M5 10h8V3H5v7Zm14 0h8V3h-8v7Z',
    };
    return `<svg viewBox="0 0 32 32" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[kind]||paths.cup}"/></svg>`;
  };
  const peer = name => `<a href="/web/player.html?username=${encodeURIComponent(name)}">${esc(name)}</a>`;
  const date = value => {const d=new Date(value); return Number.isNaN(d.getTime())?'Fecha por confirmar':new Intl.DateTimeFormat('es-UY',{day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'}).format(d);};
  async function request(path, options={}) {
    const response=await fetch(path,{...options,headers:{Authorization:`Bearer ${sessionStorage.getItem('maxio_token')||''}`,...options.headers}});
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'No pudimos cargar la información. Intentá de nuevo.');
    return data;
  }
  function country(code) { try{return new Intl.DisplayNames(['es'],{type:'region'}).of(String(code||'UY').toUpperCase());}catch{return code||'Nacionalidad sin indicar';} }
  const empty = text => `<p class="club-empty">${text}</p>`;
  const dots = results => (results||[]).slice(-5).map(r=>`<span class="club-result ${esc(r)}" title="${labels[r]||'Pendiente'}">${({win:'✓',draw:'—',loss:'X'})[r]||'—'}</span>`).join('');
  function awards() {
    const milestones=player.career?.milestones||[], earned=milestones.filter(m=>m.earned), pending=milestones.filter(m=>!m.earned);
    const award = m => {
      const kind=m.key?.startsWith('wins-')?'cup':m.key?.startsWith('matches-')?'medal':'trophy';
      const metric=num(m.target)===1?({partidos:'partido',victorias:'victoria'}[m.metric]||m.metric):m.metric;
      return `<li class="club-award"><div class="club-award-metal ${kind}">${icon(kind)}</div><strong>${esc(m.name)}</strong><small>${num(m.target)} ${esc(metric)}${m.peer?' · '+esc(m.peer):''}</small></li>`;
    };
    return `<section class="club-awards"><div class="club-section-title"><h2>Lo que te ganaste</h2><span>${earned.length} logros</span></div>${!player.career?empty('No pudimos cargar tus logros. Volvé a cargar el perfil.') : earned.length?`<ul class="club-trophy-shelf">${earned.map(award).join('')}</ul>`:empty('La vitrina empieza vacía. Tu primer partido ya deja una medalla.')}
    ${pending.length?`<details class="club-next"><summary>Lo que viene · ${pending.length} por conseguir</summary>${pending.map(m=>`<div><strong>${esc(m.name)}</strong><span>${num(m.progress)} / ${num(m.target)} ${esc(m.metric)}</span><progress value="${num(m.progress)}" max="${Math.max(1,num(m.target))}" aria-label="${esc(m.name)}"></progress></div>`).join('')}</details>`:''}</section>`;
  }
  function summaryMatch(m) {return `<li><span class="club-result ${esc(m.result)}">${({win:'V',draw:'E',loss:'D',pending:'–'})[m.result]||'–'}</span><div><strong>Partido #${num(m.match_id)}</strong><small>${esc(date(m.date))}</small></div><span>${labels[m.result]||'Pendiente'}</span></li>`;}
  function addVitrinaExtras() {
    const grid=root?.querySelector('#club-vitrina .club-skill-grid');
    if(grid&&!grid.querySelector('[data-skill="ovr"]')){
      const stats=player.stats||{}, keys=['tiro','ritmo','fisico','defensa','aura'];
      const value=Math.round(keys.reduce((sum,key)=>sum+num(stats[key]),0)/keys.length);
      grid.insertAdjacentHTML('afterbegin',`<div class="club-skill" data-skill="ovr"><span class="club-skill-index" aria-hidden="true">01</span><label for="club-stat-ovr">OVR</label><b>${value}</b><meter id="club-stat-ovr" min="0" max="100" value="${value}">${value}</meter></div>`);
      [...grid.querySelectorAll('.club-skill:not([data-skill="ovr"]) .club-skill-index')].forEach((index,position)=>index.textContent=String(position+2).padStart(2,'0'));
    }
    const form=root?.querySelector('#club-vitrina .club-form');
    if(form&&!root.querySelector('.club-league-summary'))form.insertAdjacentHTML('afterend',leagueSummary());
  }
  function leagueSummary() {
    const leagues=Array.isArray(player.leagues)?player.leagues:[], code=String(player.nationality||'UY').toUpperCase();
    const national=leagues.find(league=>league.is_system_managed||String(league.country||'').toUpperCase()===code||new RegExp(`liga\\s*(${code}|uruguay|argentina|brasil)`,`i`).test(league.name||''));
    const ranking=(national?.rankings||[]).find(row=>row.ranking_type==='general')||(national?.rankings||[])[0];
    const position=ranking?.position?`#${num(ranking.position)}`:'—';
    const range=ranking?.division||ranking?.tier||ranking?.range||'Sin rango';
    return `<div class="club-league-summary" aria-label="Resumen de Liga ${esc(code)}"><div><strong>${esc(position)}</strong><span>RANKING LIGA ${esc(code)}</span></div><div><strong>${esc(range)}</strong><span>RANGO</span></div><div><strong>${leagues.length}</strong><span>LIGAS</span></div><button type="button" data-club-action="leagues">VER ↗</button></div>`;
  }
  async function loadLeagueSummary() {
    const version=generation;
    try { const leagues=await request('/leagues/mine'); if(version!==generation||!Array.isArray(leagues))return; player.leagues=leagues; const summary=root?.querySelector('.club-league-summary'); if(summary)summary.outerHTML=leagueSummary(); } catch { /* Mantener la vista aunque las ligas no estén disponibles. */ }
  }
  const rankingTypes=[['general','GENERAL'],['solo_duo','SOLO / DUO'],['grupo','GRUPOS']];
  function rankingCell(league,type) { const row=(league.rankings||[]).find(item=>item.ranking_type===type); return row?`<div class="club-league-rank-cell"><strong>#${num(row.position)}</strong><span>${num(row.points)} PTS</span><small>${esc(row.division||'RANKING')}</small></div>`:'<div class="club-league-rank-cell is-empty"><strong>—</strong><span>SIN DATOS</span></div>'; }
  function renderMyLeagues(leagues) {
    const holder=root?.querySelector('#club-leagues-slot'); if(!holder)return;
    const ordered=(Array.isArray(leagues)?[...leagues]:[]).sort((a,b)=>Number(Boolean(b.is_system_managed))-Number(Boolean(a.is_system_managed))||Number(b.role==='admin')-Number(a.role==='admin')||String(a.name||'').localeCompare(String(b.name||''),'es'));
    holder.innerHTML=ordered.length?ordered.map(league=>{const kind=league.is_system_managed?'national':league.role==='admin'?'admin':'member';const eyebrow=kind==='national'?'LIGA NACIONAL':kind==='admin'?'ADMINISTRÁS ESTA LIGA':'LIGA ACTIVA';return `<article class="club-league-card club-league-${kind}"><header><div><span class="club-eyebrow">${eyebrow}</span><h3>${esc(league.name)}</h3></div><button type="button" data-league-expand="${num(league.id)}">TABLA COMPLETA</button></header><p>${num(league.member_count)} participantes · ${league.is_public?'PÚBLICA':'PRIVADA'}</p><div class="club-league-three-rankings">${rankingTypes.map(([type,label])=>`<div><span>${label}</span>${rankingCell(league,type)}</div>`).join('')}</div></article>`;}).join(''):'<p class="club-empty">Todavía no participás en ligas. Creá o sumate a una para empezar a competir.</p>';
  }
  async function openLeagueDetail(id) {
    const card=root?.querySelector(`[data-league-expand="${num(id)}"]`)?.closest('.club-league-card'); if(!card)return;
    const current=card.querySelector('.club-league-inline-detail'); if(current){current.remove();return;}
    card.insertAdjacentHTML('beforeend','<div class="club-league-inline-detail"><p class="club-eyebrow">TABLA COMPLETA</p><p>Cargando posiciones…</p></div>');
    const detail=card.querySelector('.club-league-inline-detail');
    try {
      const league=await request(`/leagues/${num(id)}`), currentName=String(player.name||'');
      const members=[...(league.members||[])].sort((a,b)=>num((a.rankings||[]).find(row=>row.ranking_type==='general')?.position)-num((b.rankings||[]).find(row=>row.ranking_type==='general')?.position));
      detail.innerHTML=`<div class="club-league-inline-head"><p class="club-eyebrow">PARTICIPANTES · ${members.length} JUGADORES · ORDEN GENERAL</p><button type="button" data-close-league-inline>CERRAR</button></div><div class="club-league-member-list"><div class="club-league-member-head"><span>JUGADOR</span><span title="Partidos">P</span><span title="Victorias">V</span><span title="Derrotas">D</span><span title="Empates">E</span><span>GENERAL</span><span>SOLO/DUO</span><span>GRUPOS</span></div>${members.length?members.map(member=>{const byType=Object.fromEntries((member.rankings||[]).map(row=>[row.ranking_type,row]));const general=byType.general||{},solo=byType.solo_duo||{},grupo=byType.grupo||{};return `<div class="club-league-member-row ${member.username===currentName?'is-current':''}"><strong title="${esc(member.username)}">${esc(member.username)}</strong><span>${num(general.matches_played)}</span><span>${num(general.wins)}</span><span>${num(general.losses)}</span><span>${num(general.draws)}</span><span>${num(general.points)}p</span><span>${num(solo.points)}p</span><span>${num(grupo.points)}p</span></div>`;}).join(''):'<p>Sin jugadores en esta liga.</p>'}</div>`;
    } catch(error) { detail.innerHTML=`<p class="club-empty">${esc(error.message)}</p>`; }
  }
  async function loadMyLeagueCards() { try { const leagues=await request('/leagues/mine'); player.leagues=leagues; renderMyLeagues(leagues); const summary=root?.querySelector('.club-league-summary'); if(summary)summary.outerHTML=leagueSummary(); } catch { renderMyLeagues([]); } }
  function renderPopularLeagues(leagues) {
    const holder=root?.querySelector('#club-popular-leagues'); if(!holder)return;
    const friends=new Set((['most_played_with','top_allies','top_opponents'].flatMap(key=>player.relations?.[key]||[])).map(item=>String(item.name||'')));
    const joined=new Set((player.leagues||[]).map(league=>num(league.id)));
    const popular=(Array.isArray(leagues)?leagues:[]).filter(league=>league.is_public&&!joined.has(num(league.id))).map(league=>({...league,friendCount:(league.members||[]).filter(member=>friends.has(member.username)).length})).sort((a,b)=>b.friendCount-a.friendCount||Number(b.members?.length||0)-Number(a.members?.length||0)).slice(0,3);
    holder.innerHTML=popular.length?popular.map(league=>`<article class="club-popular-league"><div><span class="club-eyebrow">${league.friendCount?`${league.friendCount} AMIGOS JUEGAN ACÁ`:'LIGA POPULAR'}</span><h3>${esc(league.name)}</h3><p>${num(league.members?.length)} participantes · ${league.max_group_size===2?'SOLO / DUO':'GRUPOS'}</p></div><button type="button" data-club-action="leagues">VER</button></article>`).join(''):'<p class="club-empty">Todavía no hay ligas públicas para recomendar.</p>';
  }
  async function loadPopularLeagues() { try { renderPopularLeagues(await request('/leagues')); } catch { renderPopularLeagues([]); } }
  function renderVitrina() {
    const s=player.matches_summary||{}, full=[player.first_name,player.last_name].filter(Boolean).join(' ');
    return `<div class="club-identity"><div class="club-member-mark" aria-hidden="true">${icon('shirt')}<span>SOCIO DE CANCHA</span></div><div><span class="club-eyebrow">${esc(player.career?.title||'Tu lugar en el club')}</span><h2>${esc(player.name)}</h2><p>${esc(full||player.name)} · ${esc(country(player.nationality))}</p></div></div>
    <div class="club-numbers"><div><b>${num(s.played)}</b><span>partidos</span></div><div><b>${num(s.won)}</b><span>victorias</span></div></div>
    <div class="club-form"><span>ÚLTIMOS PARTIDOS</span><div>${dots(s.recent_results)}</div></div>
    <section class="club-skills"><div class="club-section-title"><h2>Habilidades</h2><span>ATRIBUTOS / 100</span></div><div class="club-skill-grid">${Object.entries(skills).map(([key,label],index)=>{const value=Math.round(Math.min(100,Math.max(0,num(player.stats?.[key]))));return `<div class="club-skill" data-skill="${key}"><span class="club-skill-index" aria-hidden="true">0${index+1}</span><label for="club-stat-${key}">${label}</label><b>${value}</b><meter id="club-stat-${key}" min="0" max="100" value="${value}">${value}</meter></div>`;}).join('')}</div></section>
    ${awards()}`;
  }
  function renderVestuario() {return `<div class="club-room-banner"><span class="club-eyebrow">LA PREVIA EMPIEZA ACÁ</span><h2>Armamos equipo.<br>Después, a la cancha.</h2><p>Convocá a los tuyos y organizá el próximo encuentro.</p><button type="button" class="club-primary" data-club-action="create">Crear partido <span>↗</span></button></div>
    <div class="club-section-title"><h2>Historial de partidos</h2><button type="button" class="club-text-button" data-club-action="refresh-matches">Actualizar</button></div><p class="club-hint">Todos tus partidos, del más reciente al más antiguo.</p><div data-history="matches"></div><div data-history-status="matches" role="status"></div><button type="button" class="club-more" data-more="matches">Cargar partidos</button>
    `;}
  function renderBarrio() {return `<div class="club-room-banner club-barrio-banner"><span class="club-eyebrow">EL CLUB SE ENCUENTRA ACÁ</span><h2>Ligas, grupos<br>y competencia.</h2><p>Encontrá tu lugar en la tabla, seguí tus ligas y organizá la próxima fecha.</p><button type="button" class="club-primary" data-club-action="leagues">Ver ligas y rankings <span>↗</span></button></div>
    <div class="club-section-title"><h2>Mis ligas</h2><button type="button" class="club-text-button" data-club-action="leagues">Gestionar</button></div><p class="club-hint">Tus competencias, posiciones y grupos de jugadores.</p><div id="club-leagues-slot"></div><section class="club-popular-section"><div class="club-section-title"><h2>Ligas donde juegan los tuyos</h2><span>RECOMENDADAS</span></div><div id="club-popular-leagues"><p class="club-empty">Buscando ligas cercanas…</p></div></section>`;}
  function renderCantina() {return `<div class="club-cantina-note"><span class="club-eyebrow">SIEMPRE HAY LUGAR EN LA MESA</span><h2>El fútbol también<br>es con quién jugás.</h2><p>Compañeros de siempre, aliados y rivales que ya son un clásico.</p></div>
    <button type="button" class="club-secondary" data-club-action="search">Buscar un jugador ↗</button>
    <div class="club-connections-highlight">${(player.career?.connections||[]).map(c=>`<article><span class="club-eyebrow">${c.kind==='duo'?'TU DUPLA':'TU CLÁSICO'}</span><h3>${esc(c.title)}</h3><p>${c.peer?peer(c.peer):'Se construye partido a partido.'}</p><small>${num(c.count)} partidos ${c.kind==='duo'?'juntos':'enfrentados'}</small></article>`).join('')}</div>
    <div class="club-section-title"><h2>Historial de conexiones</h2></div><p class="club-hint">Ordenado por encuentros compartidos.</p><div data-history="connections"></div><div data-history-status="connections" role="status"></div><button type="button" class="club-more" data-more="connections">Cargar conexiones</button>`;}
  function matchCard(m) {
    const players=items=>items?.length?items.map(p=>peer(p.name)).join(' '):'<span>Sin jugadores</span>';
    const canVote=m.result==='pending'&&m.my_response==='pending'&&new Date(m.date)<=new Date();
    return `<details class="club-match" data-match-id="${num(m.match_id)}"><summary><span class="club-result ${esc(m.result)}">${({win:'V',draw:'E',loss:'D'})[m.result]||'–'}</span><div><strong>Partido #${num(m.match_id)}</strong><small>${esc(date(m.date))}</small></div><span>${labels[m.result]||'Pendiente'}</span></summary><div class="club-match-detail"><h3>Tu equipo</h3><div class="club-roster">${players(m.teammates)}</div><h3>Rivales</h3><div class="club-roster">${players(m.opponents)}</div>${canVote?`<p>¿Cómo terminó el partido?</p><div class="club-vote">${['win','draw','loss'].map(result=>`<button type="button" data-vote="${result}" data-match="${num(m.match_id)}">${({win:'Ganamos',draw:'Empatamos',loss:'Perdimos'})[result]}</button>`).join('')}</div>`:m.result==='pending'?`<p>${m.my_response&&m.my_response!=='pending'?'Tu resultado ya fue enviado.':'El resultado estará disponible después del partido.'}</p>`:''}<p class="club-vote-status" role="status"></p></div></details>`;
  }
  function drawHistory(kind) {
    const state=histories[kind], holder=root.querySelector(`[data-history="${kind}"]`);
    holder.innerHTML=state.items.length?state.items.map(kind==='matches'?matchCard:c=>`<article class="club-peer"><span class="club-peer-initial" aria-hidden="true">${esc(Array.from(c.name||'?')[0].toUpperCase())}</span><div>${peer(c.name)}<small>${num(c.games_together)} juntos · ${num(c.games_apart)} enfrentados</small></div><b>${num(c.total_games)}<small>partidos</small></b></article>`).join(''):state.loaded?empty(kind==='matches'?'Tu primer partido empieza con una convocatoria.':'Tus conexiones aparecerán después de compartir partidos.') : '';
    const button=root.querySelector(`[data-more="${kind}"]`);
    button.hidden=state.loaded&&!state.hasMore;
    button.disabled=state.loading;
    button.textContent=state.loading?'Cargando…':state.loaded?'Ver más':'Volver a intentar';
  }
  async function loadHistory(kind, reset=false) {
    const state=histories[kind], version=generation;
    if(state.loading)return;
    if(reset){state.items=[];state.offset=0;state.loaded=false;state.hasMore=true;}
    if(!state.hasMore)return;
    state.loading=true;drawHistory(kind);
    const status=root.querySelector(`[data-history-status="${kind}"]`);status.textContent='Cargando…';
    try {
      const data=await request(`/player/me/${kind}?offset=${state.offset}&limit=20`);
      if(version!==generation)return;
      if(!Array.isArray(data.items))throw Error('No pudimos leer el historial. Intentá de nuevo.');
      const key=kind==='matches'?'match_id':'name';
      const known=new Set(state.items.map(i=>i[key]));state.items.push(...data.items.filter(i=>!known.has(i[key])));
      state.offset=data.next_offset;state.hasMore=Boolean(data.has_more);state.loaded=true;status.textContent='';
    }catch(error){if(version===generation)status.textContent=error.message;}
    finally{state.loading=false;if(version===generation)drawHistory(kind);}
  }
  function navigate(room, focus=true) {
    if(!rooms[room])return;
    active=room;
    document.querySelector('#dashboard').dataset.clubRoom=room;
    root.querySelectorAll('[data-club-panel]').forEach(panel=>panel.hidden=panel.dataset.clubPanel!==room);
    root.querySelectorAll('.club-bottom-nav [data-room]').forEach(button=>{if(button.dataset.room===room)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');});
    if(focus){window.scrollTo({top:0,behavior:'instant'});root.querySelector(`[data-club-panel="${room}"] h1`)?.focus({preventScroll:true});}
    const kind=room==='vestuario'?'matches':room==='cantina'?'connections':null;
    if(kind&&!histories[kind].loaded)void loadHistory(kind);
  }
  async function onClick(event) {
    if(event.target.closest('#club-vitrina .club-form')){navigate('vestuario');return;}
    const room=event.target.closest('[data-room]');if(room){navigate(room.dataset.room);return;}
    const expand=event.target.closest('[data-league-expand]');if(expand){void openLeagueDetail(expand.dataset.leagueExpand);return;}
    if(event.target.closest('[data-close-league-inline]')){event.target.closest('.club-league-inline-detail')?.remove();return;}
    if(event.target.closest('[data-close-league]')){event.target.closest('.club-league-expanded')?.remove();return;}
    const more=event.target.closest('[data-more]');if(more){void loadHistory(more.dataset.more);return;}
    const action=event.target.closest('[data-club-action]')?.dataset.clubAction;
    if(action==='create')document.querySelector('#new-match')?.click();
    if(action==='leagues')document.querySelector('#league-hub')?.click();
    if(action==='search')document.querySelector('#global-player-search-button')?.click();
    if(action==='refresh-matches')void loadHistory('matches',true);
    const vote=event.target.closest('[data-vote]');
    if(vote){
      const detail=vote.closest('.club-match-detail'),status=detail.querySelector('.club-vote-status');
      detail.querySelectorAll('button').forEach(b=>b.disabled=true);status.textContent='Enviando resultado…';
      try{await request(`/match/matches/${vote.dataset.match}/result`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:vote.dataset.vote})});status.textContent='Resultado enviado.';await dashboard();}
      catch(error){status.textContent=error.message;detail.querySelectorAll('button').forEach(b=>b.disabled=false);}
    }
  }
  function mount(data) {
    const content=document.querySelector('#content');if(!content)return;
    if(player?.id!==data.id)active='vitrina';player=data;generation++;
    histories=Object.fromEntries(['matches','connections'].map(k=>[k,{items:[],offset:0,hasMore:true,loading:false,loaded:false}]));
    document.body.classList.add('club-app');
    root=document.querySelector('#club-app');
    if(!root){root=document.createElement('div');root.id='club-app';content.append(root);root.addEventListener('click',onClick);}
    // Preserve existing league nodes and event handlers when a profile refreshes.
    const rankings=document.querySelector('#rankings-section');if(rankings&&root.contains(rankings))content.append(rankings);
    root.innerHTML=Object.entries(rooms).map(([key,[kicker,title]])=>`<section class="club-screen" id="club-${key}" data-club-panel="${key}" ${key===active?'':'hidden'}><div class="club-page-heading"><span>${kicker}</span><h1 tabindex="-1">${title}<i aria-hidden="true">.</i></h1></div>${key==='vitrina'?renderVitrina():key==='vestuario'?renderVestuario():key==='cantina'?renderCantina():renderBarrio()}</section>`).join('')+`<nav class="club-bottom-nav" aria-label="Secciones del club">${Object.entries(rooms).map(([key,[,title]])=>`<button type="button" data-room="${key}" aria-controls="club-${key}" ${key===active?'aria-current="page"':''}>${icon(({vitrina:'cup',vestuario:'shirt',cantina:'table',barrio:'trophy'})[key])}<span>${title}</span></button>`).join('')}</nav>`;
    if(rankings)rankings.hidden=true;
    addVitrinaExtras();
    navigate(active,false);
    void loadLeagueSummary();
    void loadMyLeagueCards().then(()=>loadPopularLeagues());
    window.Telegram?.WebApp?.setHeaderColor?.('#29271f');
    window.Telegram?.WebApp?.setBackgroundColor?.('#eee7d7');
  }
  window.MaxioClub=Object.freeze({mount});
})();
