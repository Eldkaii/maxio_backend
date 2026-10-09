"use strict";
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const num = value => Number(value || 0).toLocaleString("es-UY");
const date = value => value ? new Date(value.length === 10 ? value + "T12:00:00" : value).toLocaleDateString("es-UY") : "—";
const labels = {overview:"Resumen",players:"Jugadores",matches:"Partidos",leagues:"Ligas",awards:"Premios",simulator:"Simulador"};
const dialogs = {players:"player",matches:"match",leagues:"league",awards:"achievement"};
const base = "/maxio/users/admin";
let view = "overview", page = 1, listVersion = 0, metricsVersion = 0, detailVersion = 0, searchTimer;
const adminToken = () => sessionStorage.getItem("maxio_token");
async function adminApi(path, options = {}) {
  const response = await fetch(path, {...options, cache:"no-store", headers:{...options.headers, Authorization:`Bearer ${adminToken() || ""}`}});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Array.isArray(body.detail) ? body.detail.map(item => `${item.loc?.at(-1) || "Campo"}: ${item.msg}`).join(" · ") : body.detail;
    const error = Error(typeof message === "string" ? message : "No se pudo completar la solicitud.");
    error.status = response.status;
    if (response.status === 401) { sessionStorage.removeItem("maxio_token"); location.replace("/web/"); }
    throw error;
  }
  return body;
}
function notice(message, error = false) { $("#notice").hidden = !message; $("#notice").textContent = message; $("#notice").dataset.error = String(error); }
function table(headers, rows) {
  return rows.length ? `<div class="table-scroll"><table><thead><tr>${headers.map(h => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : '<p class="empty">No hay registros para mostrar.</p>';
}
const link = (kind, item) => `<button class="link-button" data-detail="${kind}" data-id="${Number(item.id)}">${esc(item.name)}</button>`;
const inspect = (kind, id) => `<button data-detail="${kind}" data-id="${Number(id)}">Ver detalle →</button>`;
function chart(item, dates) {
  const max = Math.max(1, ...item.series.flatMap(s => s.values));
  const x = i => 34 + i * 470 / Math.max(1, dates.length - 1), y = v => 158 - v * 128 / max;
  const grid = [0,.5,1].map(f => `<line x1="34" x2="504" y1="${y(max*f)}" y2="${y(max*f)}" stroke="#edf0f5"/><text x="26" y="${y(max*f)+4}" text-anchor="end" fill="#7a8799" font-size="10">${Number((max*f).toFixed(1))}</text>`).join("");
  const lines = item.series.map((s, index) => `<polyline points="${s.values.map((v,i) => `${x(i)},${y(v)}`).join(" ")}" fill="none" stroke="${index ? '#149b88' : '#2866e8'}" stroke-width="2.5" stroke-linejoin="round"/>${s.values.map((v,i) => `<circle cx="${x(i)}" cy="${y(v)}" r="${dates.length > 90 ? 1 : 2.5}" fill="${index ? '#149b88' : '#2866e8'}"><title>${esc(date(dates[i]))} · ${esc(s.name)}: ${v}</title></circle>`).join("")}`).join("");
  const indices = [...new Set([0, Math.floor((dates.length-1)/2), dates.length-1])];
  return `<article class="chart-card"><header><h2>${esc(item.title)}</h2><button data-view="${item.key}">Explorar ↗</button></header><div class="legend">${item.series.map(s => `<span>${esc(s.name)}</span>`).join("")}</div><svg viewBox="0 0 530 188" role="img" aria-label="${esc(item.title)}: evolución diaria. Datos completos disponibles debajo.">${grid}${lines}${indices.map(i => `<text x="${x(i)}" y="181" text-anchor="${i===0?'start':i===dates.length-1?'end':'middle'}" fill="#7a8799" font-size="10">${esc(date(dates[i]))}</text>`).join("")}</svg><p class="chart-note">${esc(item.note)}</p><details><summary>Ver datos diarios${item.series.every(s=>s.values.every(v=>!v))?' · Sin actividad en este período':''}</summary>${table(['Fecha',...item.series.map(s=>s.name)],dates.map((d,i)=>[esc(date(d)),...item.series.map(s=>num(s.values[i]))]))}</details></article>`;
}
async function loadMetrics() {
  const version = ++metricsVersion;
  $("#updated").textContent = "Actualizando…";
  try {
    const data = await adminApi(`${base}/dashboard?days=${$("#period").value}`);
    if (version !== metricsVersion) return;
    const t = data.totals;
    const cards = [['players',t.real_players,'Jugadores humanos',`${num(t.active_players)} activos en el período · ${num(t.bots)} bots`],['matches',t.matches,'Partidos',`${num(t.completed_matches)} finalizados · ${num(t.upcoming_matches)} próximos`],['leagues',t.leagues,'Ligas',`${num(t.league_memberships)} inscripciones actuales`],['awards',t.awards,'Premios definidos',`${num(t.awarded)} entregas registradas`]];
    $("#metrics").innerHTML = cards.map(([kind,value,title,note]) => `<button class="metric" data-view="${kind}"><span class="metric-label">${title}<span class="metric-icon">↗</span></span><strong>${num(value)}</strong><small>${note}</small></button>`).join("");
    $("#charts").innerHTML = data.charts.map(c => chart(c,data.dates)).join("");
    $("#updated").textContent = `Actualizado ${new Date(data.generated_at).toLocaleTimeString('es-UY')}`;
  } catch (error) { if(version===metricsVersion) { $("#updated").textContent="No se pudo actualizar"; notice(error.message,true); } }
}
function navigate(next) {
  if (!labels[next]) return;
  view = next; page = 1; $("#search").value = ""; notice("");
  document.querySelectorAll('nav [data-view]').forEach(b => {b.classList.toggle('selected',b.dataset.view===view);b.setAttribute('aria-current',b.dataset.view===view?'page':'false');});
  $("#breadcrumb").textContent = labels[view]; $("#page-title").textContent = view==='overview'?'Pulso de la plataforma':labels[view];
  $("#page-description").textContent = view==='overview'?'Crecimiento, participación y actividad en un solo lugar.':view==='simulator'?'Seguimiento de las acciones y errores del simulador.':'Buscá, revisá y gestioná los registros de la plataforma.';
  $("#overview").hidden = view!=='overview'; $("#explorer").hidden = !dialogs[view]; $("#simulator").hidden = view!=='simulator';
  if (dialogs[view]) { $("#list-title").textContent = labels[view]; $("#search").placeholder = view==='matches'?'Buscar por ID de partido':'Buscar por nombre o ID'; void loadList(); }
  if(view==='simulator') window.initSimulatorLog();
}
async function loadList() {
  if(!dialogs[view]) return;
  const version = ++listVersion, kind = view;
  $("#entity-table").innerHTML = '<p class="empty">Cargando registros…</p>';
  $("#previous").disabled = $("#next").disabled = true;
  try {
    const data = await adminApi(`${base}/entities/${kind}?page=${page}&search=${encodeURIComponent($("#search").value.trim())}`);
    if(version!==listVersion || kind!==view) return;
    let headers, rows;
    if(kind==='players') {headers=['Jugador','Tipo','ELO','Partidos','Victorias',''];rows=data.items.map(i=>[esc(i.name),esc(i.type),num(i.elo),num(i.played),num(i.wins),inspect(kind,i.id)]);}
    if(kind==='matches') {headers=['Partido','Fecha','Estado','Liga','Capacidad',''];rows=data.items.map(i=>[esc(i.name),date(i.date),`<span class="pill">${esc(i.status)}</span>`,i.league_id?`#${i.league_id}`:'Amistoso',num(i.capacity),inspect(kind,i.id)]);}
    if(kind==='leagues') {headers=['Liga','Visibilidad','Estado','Inicio','Fin',''];rows=data.items.map(i=>[esc(i.name),esc(i.type),`<span class="pill">${esc(i.status)}</span>`,date(i.start),date(i.end),inspect(kind,i.id)]);}
    if(kind==='awards') {headers=['Premio','Tipo','Estado',''];rows=data.items.map(i=>[esc(i.name),i.reward_type==='trophy'?'Trofeo':'Logro',i.active?'Activo':'Inactivo',inspect(kind,i.id)]);}
    $("#entity-table").innerHTML = table(headers,rows); $("#list-count").textContent = `${num(data.total)} registros`;
    $("#page-number").textContent = `Página ${page} de ${Math.max(1,Math.ceil(data.total/data.size))}`;
    $("#previous").disabled=page<=1; $("#next").disabled=page*data.size>=data.total;
  } catch(error) {if(version===listVersion && kind===view) {$("#entity-table").innerHTML='<p class="empty">No se pudo cargar. Usá Actualizar para reintentar.</p>';$("#list-count").textContent='';$("#page-number").textContent='';notice(error.message,true);}}
}
const facts = pairs => `<div class="detail-grid">${pairs.map(([key,value])=>`<div><small>${esc(key)}</small><b>${esc(value ?? '—')}</b></div>`).join('')}</div>`;
const matchTable = items => table(['Partido','Fecha','Estado'],items.map(i=>[link('matches',i),date(i.date),esc(i.status)]));
async function showDetail(kind,id) {
  const version=++detailVersion, dialog=$("#detail");
  if(!dialog.open) dialog.showModal();
  $("#detail-content").textContent='Cargando detalle…';
  try {
    const i=await adminApi(`${base}/entities/${kind}/${id}`);
    if(version!==detailVersion) return;
    let content=`<p class="eyebrow">${esc(labels[kind])} / #${Number(i.id)}</p><h2>${esc(i.name)}</h2><br>`;
    if(kind==='players') content+=facts([['Tipo',i.type],['ELO',i.elo],['Partidos',i.played],['Victorias',i.wins],['Empates',i.draws],...Object.entries(i.stats)])+`<h3>Ligas</h3>${table(['Liga','Estado'],i.leagues.map(l=>[link('leagues',l),esc(l.status)]))}<h3>Últimos partidos (hasta 100)</h3>${matchTable(i.matches)}<h3>Premios obtenidos</h3>${table(['Premio','Fecha'],i.awards.map(a=>[esc(a.name),date(a.earned_at)]))}`;
    if(kind==='matches') content+=facts([['Fecha',new Date(i.date).toLocaleString('es-UY')],['Estado',i.status],['Capacidad',i.capacity],['Ganador',i.winner],['Liga',i.league_id?`#${i.league_id}`:'Amistoso'],['Convocados',i.players.length]])+(i.league_id?`<p>${link('leagues',{id:i.league_id,name:'Ver liga →'})}</p>`:'')+`<h3>Convocados y equipos</h3>${table(['Jugador','Equipo'],i.players.map(p=>[link('players',p),esc(p.team==='team1'?'Equipo 1':p.team==='team2'?'Equipo 2':p.team)]))}<h3>Votos</h3>${facts(Object.entries(i.votes))}`;
    if(kind==='leagues') content+=facts([['Estado',i.status],['Visibilidad',i.type],['Integrantes',i.members.length],['Inicio',date(i.start)],['Fin',date(i.end)],['Partidos',i.match_count]])+`<h3>Integrantes y rankings</h3>${table(['Jugador','Rol','General','Solo / Dúo','Grupo'],i.members.map(m=>[link('players',m),esc(m.role),...['general','solo_duo','grupo'].map(k=>num(m.rankings.find(r=>r.type===k)?.points))]))}<h3>Últimos partidos (hasta 100)</h3>${matchTable(i.matches)}`;
    if(kind==='awards') content+=facts([['Tipo',i.reward_type==='trophy'?'Trofeo':'Logro'],['Estado',i.active?'Activo':'Inactivo'],['Entregas',i.award_count]])+`<p>${esc(i.description)}</p><h3>Condiciones</h3>${facts(Object.entries(i.conditions).map(([k,v])=>[conditionLabels[k]||k,v]))}<p><button id="edit-award">Editar premio</button></p><h3>Últimas entregas (hasta 100)</h3>${table(['Jugador','Fecha'],i.recipients.map(p=>[link('players',p),date(p.earned_at)]))}`;
    $("#detail-content").innerHTML=content;
    $("#edit-award")?.addEventListener('click',()=>{dialog.close();void openAward(i);});
  } catch(error) {if(version===detailVersion) $("#detail-content").textContent=error.message;}
}
function openDialog(id) {
  const dialog=$(`#${id}`);dialog.querySelector('small[role=alert]').textContent='';
  if(id==='league') {const f=dialog.querySelector('form');const today=new Date();f.elements.start_date.value ||= localDate(today);today.setDate(today.getDate()+90);f.elements.end_date.value ||= localDate(today);}
  dialog.showModal();
}
function localDate(d) {return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function bindForm(id,endpoint,transform) {
  const dialog=$(`#${id}`),form=dialog.querySelector('form');
  form.addEventListener('submit',async event=>{
    event.preventDefault();const button=form.querySelector('[type=submit]'),error=form.querySelector('small[role=alert]');error.textContent='';button.disabled=true;
    try {const payload=transform(Object.fromEntries(new FormData(form)));await adminApi(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});form.reset();dialog.close();notice('Registro creado correctamente.');await Promise.all([loadMetrics(),loadList()]);}
    catch(reason){error.textContent=reason.message;}finally{button.disabled=false;}
  });
}
const conditionLabels={played:'Partidos jugados',wins:'Victorias',winrate:'% de victorias',with_games:'Partidos con un compañero',with_wins:'Victorias con un compañero',skill_tiro:'Tiro',skill_ritmo:'Ritmo',skill_fisico:'Físico',skill_defensa:'Defensa',skill_aura:'Aura'};
$("#achievement-conditions").innerHTML=Object.entries(conditionLabels).map(([key,label])=>`<label>${label}<input name="${key}" type="number" min="0" ${key==='winrate'||key.startsWith('skill_')?'max="100" step="0.1"':''}></label>`).join('');
function previewTrophy() {const value=$("#achievement-trophy").value,img=$("#trophy-preview");img.hidden=!value;if(value)img.src=`/images/trofeos/${encodeURIComponent(value)}`;else img.removeAttribute('src');}
async function openAward(item) {
  const form=$("#achievement-form"); form.reset();form.elements.id.value=item?.id||'';$("#award-form-title").textContent=item?'Editar premio':'Crear premio';openDialog('achievement');
  if(item) {['key','name','description','reward_type'].forEach(k=>form.elements[k].value=item[k]||'');form.elements.active.checked=item.active;Object.entries(item.conditions).forEach(([k,v])=>{if(form.elements[k])form.elements[k].value=v;});}
  const submit=form.querySelector('[type=submit]');submit.disabled=true;
  try {const data=await adminApi(`${base}/achievements`);$("#achievement-trophy").innerHTML='<option value="">Sin imagen</option>'+data.trophies.map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join('');form.elements.trophy_image.value=item?.trophy_image||'';previewTrophy();}
  catch(error){form.querySelector('small').textContent=error.message;}finally{submit.disabled=false;}
}
$("#achievement-trophy").addEventListener('change',previewTrophy);
$("#achievement-form").addEventListener('submit',async event=>{
  event.preventDefault();const form=event.currentTarget,button=form.querySelector('[type=submit]'),error=form.querySelector('small');button.disabled=true;error.textContent='';
  const v=Object.fromEntries(new FormData(form)),conditions={};Object.keys(conditionLabels).forEach(k=>{if(v[k]!=='')conditions[k]=Number(v[k]);});
  try {await adminApi(`${base}/achievements${v.id?'/'+v.id:''}`,{method:v.id?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:v.key.trim(),name:v.name.trim(),description:v.description,conditions,reward_type:v.reward_type,trophy_image:v.trophy_image||null,active:form.elements.active.checked})});$("#achievement").close();notice('Premio guardado correctamente.');await Promise.all([loadMetrics(),loadList()]);}
  catch(reason){error.textContent=reason.message;}finally{button.disabled=false;}
});
document.addEventListener('click',event=>{
  const nav=event.target.closest('[data-view]'),create=event.target.closest('[data-dialog]'),close=event.target.closest('[data-close]'),detail=event.target.closest('[data-detail]');
  if(nav)navigate(nav.dataset.view);if(create)openDialog(create.dataset.dialog);if(close)close.closest('dialog').close();if(detail)void showDetail(detail.dataset.detail,detail.dataset.id);if(event.target.closest('[data-new-award]'))void openAward();
});
$("#create-entity").onclick=()=>view==='awards'?void openAward():openDialog(dialogs[view]);
$("#search").addEventListener('input',()=>{clearTimeout(searchTimer);++listVersion;searchTimer=setTimeout(()=>{page=1;void loadList();},250);});
$("#previous").onclick=()=>{page--;void loadList();};$("#next").onclick=()=>{page++;void loadList();};
$("#period").onchange=()=>void loadMetrics();
$("#refresh").onclick=()=>{notice('');if(view==='simulator')$("#simulator-refresh").click();else if(view==='overview')void loadMetrics();else void loadList();};
$("#logout").onclick=()=>{if(confirm('¿Cerrar sesión?')){sessionStorage.removeItem('maxio_token');location.replace('/web/');}};
bindForm('player',`${base}/players`,v=>{['tiro','ritmo','fisico','defensa','aura'].forEach(k=>v[k]=Number(v[k]));v.nationality=v.nationality.trim().toUpperCase();return v;});
bindForm('league','/leagues',v=>{if(v.end_date<=v.start_date)throw Error('La finalización debe ser posterior al inicio.');return {name:v.name,start_date:v.start_date,end_date:v.end_date,is_public:v.is_public==='on',is_special:v.is_special==='on',max_group_size:v.max_group_size?Number(v.max_group_size):null};});
bindForm('match','/match/matches',v=>({date:new Date(v.date).toISOString(),max_players:Number(v.max_players),league_id:v.league_id?Number(v.league_id):null}));
async function boot() {try {const me=await adminApi('/maxio/users/me');if(!me.is_admin){location.replace('/web/');return;}navigate('overview');await loadMetrics();}catch(error){notice(error.message,true);}}
void boot();
