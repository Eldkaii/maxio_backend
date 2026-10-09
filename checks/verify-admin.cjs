// Isolated browser fixtures: no application startup, database, or real API calls.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const {execFile}=require('node:child_process');
const root=path.resolve(__dirname,'..'),output=path.join(root,'tools/ui-review/admin');
fs.mkdirSync(output,{recursive:true});
function fixture(){
  window.__errors=[];window.__writes=[];window.__requests=[];
  addEventListener('error',e=>__errors.push(e.message));addEventListener('unhandledrejection',e=>__errors.push(String(e.reason)));
  sessionStorage.setItem('maxio_token','synthetic-admin');
  const match={id:5,name:'Partido #5',date:'2026-10-08T20:00:00Z',status:'Finalizado',capacity:10,league_id:3,winner:'Equipo 1',players:[{id:1,name:'Santiago',team:'team1'}],votes:{'Equipo 1':4,'Equipo 2':1,Empate:0}};
  const league={id:3,name:'Liga del jueves',type:'Pública',status:'Activa',start:'2026-10-01',end:'2027-01-01',members:[{id:1,name:'Santiago',role:'member',rankings:[{type:'general',points:40}]}],matches:[match],match_count:1};
  const player={id:1,name:'Santiago <img src=x onerror="window.injected=true">',type:'Humano',elo:1250,played:20,wins:12,draws:2,stats:{tiro:71,ritmo:60},matches:[match],leagues:[league],awards:[{name:'Debutante',earned_at:'2026-10-01'}]};
  const award={id:7,key:'debut',name:'Debutante',description:'Primer partido',reward_type:'achievement',active:true,conditions:{played:1},award_count:1,recipients:[{id:1,name:'Santiago',earned_at:'2026-10-01'}]};
  const items={players:player,matches:match,leagues:league,awards:award};
  window.fetch=async(path,options={})=>{
    const url=new URL(path,location.origin);__requests.push(url.pathname+url.search);
    const result=(body,status=200)=>({ok:status<400,status,json:async()=>body});
    if(options.method==='POST'||options.method==='PUT'){__writes.push({path:url.pathname,body:JSON.parse(options.body),method:options.method});if(window.rejectWrite)return result({detail:'Error de prueba: datos inválidos'},400);return result({id:10});}
    if(url.pathname==='/maxio/users/me')return result({is_admin:true});
    if(url.pathname.endsWith('/dashboard')){
      if(window.rejectMetrics)return result({detail:'Métricas temporalmente no disponibles'},503);
      const days=Number(url.searchParams.get('days'));
      return result({generated_at:'2026-10-08T22:00:00Z',totals:{real_players:248,bots:32,matches:186,completed_matches:160,upcoming_matches:12,leagues:14,league_memberships:392,awards:24,awarded:682,active_players:138},dates:Array.from({length:days},(_,i)=>new Date(Date.UTC(2026,9,8-days+1+i)).toISOString().slice(0,10)),charts:Object.keys(items).map((key,j)=>({key,title:['Jugadores','Partidos','Ligas','Premios'][j],note:['Humanos: primer partido finalizado y jugadores únicos por día. No representa altas de cuentas.','Por fecha del encuentro (UTC), no por fecha de creación. Excluye fechas futuras.','Inicio de temporadas y ligas con encuentros finalizados por día; no son altas de ligas.','Definiciones creadas y entregas registradas de logros y trofeos (UTC).'][j],series:[{name:['Debutantes','Programados','Temporadas iniciadas','Nuevos premios'][j],values:Array.from({length:days},(_,i)=>window.zeroMetrics?0:Math.floor(i/5)+i%3+j)},{name:['Activos','Finalizados','Con actividad','Entregas'][j],values:Array.from({length:days},(_,i)=>window.zeroMetrics?0:Math.floor(i/3)+i%4+j)}]}))});
    }
    if(url.pathname.includes('/entities/')){const parts=url.pathname.split('/'),kind=parts[5],id=parts[6];if(id)return result(items[kind]);const search=url.searchParams.get('search');if(search==='error')return result({detail:'Listado temporalmente no disponible'},503);return result({items:search==='vacío'?[]:[items[kind]],total:search==='vacío'?0:21,page:Number(url.searchParams.get('page')),size:20});}
    if(url.pathname.endsWith('/achievements'))return result({items:[award],trophies:[]});
    if(url.pathname.endsWith('/simulator/log'))return result({available:true,lines:['2026-10-08 | INFO | Partido creado','2026-10-08 | ERROR | <script>texto seguro<'+ '/script>'],truncated:false});
    return result({detail:'Unknown fixture '+path},404);
  };
}
async function audit(){
  const wait=()=>new Promise(r=>setTimeout(r,70)),fail=m=>{throw Error(m);},q=s=>document.querySelector(s);
  try{
    await wait();if(document.querySelectorAll('.chart-card').length!==4)fail('Missing charts');
    if(document.documentElement.scrollWidth>innerWidth+1)fail('Overview overflow');
    q('#period').value='7';q('#period').dispatchEvent(new Event('change'));await wait();if(!__requests.some(p=>p.includes('days=7')))fail('Period ignored');
    window.zeroMetrics=true;q('#refresh').click();await wait();if(!q('#charts').textContent.includes('Sin actividad'))fail('Empty chart');window.zeroMetrics=false;
    window.rejectMetrics=true;q('#refresh').click();await wait();if(q('#notice').dataset.error!=='true')fail('Metrics failure hidden');window.rejectMetrics=false;
    for(const kind of ['players','matches','leagues','awards']){
      q(`nav [data-view="${kind}"]`).click();await wait();if(!q('#entity-table [data-detail]'))fail('Missing list '+kind);
      q('#entity-table [data-detail]').click();await wait();if(!q('#detail').open||q('#detail-content').textContent.includes('Cargando'))fail('Missing detail '+kind);
      if(q('#detail').scrollWidth>q('#detail').clientWidth+1)fail('Detail overflow '+kind);
      if(kind==='awards'){q('#edit-award').click();await wait();if(q('#achievement-form').elements.id.value!=='7')fail('Edit not populated');q('#achievement-form').requestSubmit();await wait();if(!__writes.some(w=>w.method==='PUT'))fail('Edit not saved');}
      else q('#detail [data-close]').click();
      if(document.documentElement.scrollWidth>innerWidth+1)fail('List overflow '+kind);
    }
    q('nav [data-view="players"]').click();await wait();q('#next').click();await wait();if(!q('#page-number').textContent.includes('2 de 2'))fail('Pagination');q('#previous').click();await wait();
    q('#search').value='vacío';q('#search').dispatchEvent(new Event('input'));await new Promise(r=>setTimeout(r,300));if(!q('#entity-table').textContent.includes('No hay registros'))fail('Empty list');
    q('#search').value='error';q('#search').dispatchEvent(new Event('input'));await new Promise(r=>setTimeout(r,300));if(!q('#entity-table').textContent.includes('No se pudo cargar'))fail('Error state');
    q('nav [data-view="overview"]').click();
    for(const [id,values] of [['player',{username:'test.player',email:'test@example.invalid',password:'fixture123'}],['league',{name:'Nueva liga',start_date:'2026-10-08',end_date:'2027-01-08'}],['match',{date:'2026-10-10T20:00',league_id:'3'}]]){
      q(`[data-dialog="${id}"]`).click();const form=q(`#${id} form`);Object.entries(values).forEach(([k,v])=>form.elements[k].value=v);
      if(id==='player'){window.rejectWrite=true;form.requestSubmit();await wait();if(!q('#player').open||!form.querySelector('small').textContent)fail('Write failure hidden');window.rejectWrite=false;}
      form.requestSubmit();await wait();if(q(`#${id}`).open)fail('Creation failed '+id);
    }
    const leagueWrite=__writes.find(w=>w.path==='/leagues');if(leagueWrite.body.start_date!=='2026-10-08'||leagueWrite.body.end_date!=='2027-01-08')fail('Dates missing');
    q('[data-new-award]').click();await wait();const f=q('#achievement-form');f.elements.key.value='new-award';f.elements.name.value='Premio nuevo';f.elements.played.value='5';f.requestSubmit();await wait();if(q('#achievement').open)fail('Award creation');
    q('nav [data-view="simulator"]').click();await wait();if(!q('#simulator-log').textContent.includes('Partido creado')||!q('.simulator-line.error'))fail('Log absent');if(q('#simulator-log script'))fail('Log injection');
    q('#simulator-limit').value='500';q('#simulator-limit').dispatchEvent(new Event('change'));await wait();if(!__requests.some(p=>p.includes('limit=500')))fail('Log limit ignored');
    if(window.injected)fail('Player injection');
    q('nav [data-view="overview"]').click();q('#period').value='30';q('#period').dispatchEvent(new Event('change'));await wait();window.scrollTo(0,0);
  }catch(e){__errors.push(e.stack||e.message);}
  parent.postMessage({width:innerWidth,errors:__errors,writes:__writes.length},location.origin);
}
const server=http.createServer((req,res)=>{
  const url=new URL(req.url,'http://localhost');
  if(url.pathname==='/preview'){res.setHeader('Content-Type','text/html; charset=utf-8');return res.end(`<html><body style="margin:0"><iframe style="border:0;width:${Number(url.searchParams.get('width'))}px;height:1200px" src="/web/admin.html"></iframe><script>addEventListener('message',e=>{if(e.origin!==location.origin)return;const p=document.createElement('pre');p.id='qa-report';p.hidden=true;p.textContent=JSON.stringify(e.data);document.body.append(p)})</script></body></html>`);}
  if(url.pathname==='/web/admin.html'){res.setHeader('Content-Type','text/html; charset=utf-8');const html=fs.readFileSync(path.join(root,'src/web/admin.html'),'utf8');return res.end(html.replace('<head>',`<head><script>(${fixture.toString()})()</script>`).replace('</body>',`<script>addEventListener('load',()=>setTimeout(${audit.toString()},200))</script></body>`));}
  const file=path.resolve(root,'src','.'+decodeURIComponent(url.pathname));if(!file.startsWith(path.join(root,'src')+path.sep)||!fs.existsSync(file)){res.statusCode=404;return res.end();}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'image/png');res.end(fs.readFileSync(file));
});
server.listen(0,'127.0.0.1',async()=>{try{for(const width of [1440,390,320]){
  const args=['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--hide-scrollbars','--force-device-scale-factor=1','--user-data-dir='+path.join(output,'profile-'+width+'-'+Date.now()),'--window-size='+Math.max(516,width+16)+',1250','--virtual-time-budget=18000','--screenshot='+path.join(output,width+'.png'),'--dump-dom',`http://127.0.0.1:${server.address().port}/preview?width=${width}`];
  await new Promise((resolve,reject)=>execFile('C:/Program Files/Google/Chrome/Application/chrome.exe',args,{maxBuffer:15e6,timeout:30000},(error,stdout)=>{if(error)return reject(error);const match=stdout.match(/<pre id="qa-report" hidden="">([\s\S]*?)<\/pre>/);if(!match)return reject(Error('No browser audit'));const report=JSON.parse(match[1].replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&'));console.log(JSON.stringify(report));if(report.errors.length)process.exitCode=1;resolve();}));
}}catch(error){console.error(error);process.exitCode=1;}finally{server.close();}});
