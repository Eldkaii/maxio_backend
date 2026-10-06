// Real browser, synthetic API only. Does not start Maxio or connect to its DB.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { execFile } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'tools/ui-review/admin-log');
fs.mkdirSync(output, { recursive: true });
const bootstrap = `<script>
sessionStorage.setItem('maxio_token','test-only');
window.fixtureMode='full';window.logCalls=0;window.uiErrors=[];
addEventListener('error',e=>uiErrors.push(e.message));
addEventListener('unhandledrejection',e=>uiErrors.push(String(e.reason)));
const realTimer=window.setTimeout;
window.setTimeout=(fn,ms,...args)=>realTimer(fn,ms===15000?100:ms,...args);
window.fetch=async(url,options)=>{
  if(url==='/maxio/users/me')return new Response(JSON.stringify({is_admin:true}));
  if(url==='/maxio/users/admin/summary')return new Response(JSON.stringify({real_players:28,bots:10,leagues:3,league_memberships:50,matches:18,upcoming_matches:2}));
  if(url.startsWith('/maxio/users/admin/simulator/log')){
    window.logCalls++;window.lastLogUrl=url;
    if(options.headers.Authorization!=='Bearer test-only')throw Error('Missing auth');
    if(fixtureMode==='error')return new Response(JSON.stringify({detail:'No disponible'}),{status:503});
    const lines=fixtureMode==='empty'?[]:Array.from({length:25},(_,i)=>'2026-10-06 14:20:'+String(i).padStart(2,'0')+' | '+(i===4?'WARNING':'INFO')+' | Crea partido: nicolás.pereira, partido='+i);
    if(lines.length)lines.push('<img src=x onerror="window.injected=true">', 'Jugador: '+ 'x'.repeat(1000));
    return new Response(JSON.stringify({available:true,lines,truncated:true}));
  }
  throw Error('Unexpected request '+url);
};
</script>`;
const audit = `<script>
addEventListener('load',async()=>{
 const errors=[],check=(v,m)=>{if(!v)errors.push(m)},wait=()=>new Promise(r=>realTimer(r,60));
 const ready=async()=>{for(let i=0;i<80;i++){if(!document.querySelector('#simulator-refresh').disabled && document.querySelector('#simulator-panel').dataset.initialized)return;await wait()}throw Error('UI timeout')};
 const refresh=async()=>{document.querySelector('#simulator-refresh').click();await wait();await ready()};
 try{
  await ready();await wait();await wait();await wait();
  check(logCalls>=2,'Auto refresh did not run');
  const auto=document.querySelector('#simulator-auto');auto.checked=false;auto.dispatchEvent(new Event('change'));
  const box=document.querySelector('#simulator-log');
  check(!document.querySelector('#simulator-panel').hidden,'Panel hidden');
  check(box.querySelectorAll('.simulator-line').length===27,'Missing records');
  check(!window.injected&&!box.querySelector('img'),'Log interpreted as HTML');
  check(box.querySelector('.warning'),'Missing warning style');
  box.scrollTop=0;await refresh();check(box.scrollTop===0,'Refresh moved reading position');
  const limit=document.querySelector('#simulator-limit');limit.value='500';limit.dispatchEvent(new Event('change'));await wait();await ready();
  check(lastLogUrl.endsWith('limit=500'),'Limit ignored');
  fixtureMode='error';await refresh();check(document.querySelector('#simulator-status').dataset.error==='true','Missing error');check(box.querySelectorAll('.simulator-line').length===27,'Lost previous records on error');
  fixtureMode='empty';await refresh();check(box.textContent.includes('Todavía no hay'),'Missing empty state');
  fixtureMode='full';await refresh();box.scrollTop=0;
  check(document.documentElement.scrollWidth<=innerWidth+1,'Horizontal overflow');
  document.querySelector('#simulator-panel').scrollIntoView();
 }catch(e){errors.push(e.stack||e.message)}
 parent.postMessage({width:innerWidth,errors:[...errors,...uiErrors]},location.origin);
});</script>`;
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  if (url.pathname === '/preview') return res.end(`<body style="margin:0;background:#09111f"><iframe style="display:block;margin:auto;width:${Number(url.searchParams.get('width'))}px;height:100vh;border:0" src="/web/admin.html"></iframe><script>addEventListener('message',e=>{if(e.origin!==location.origin)return;const p=document.createElement('pre');p.id='qa-report';p.hidden=true;p.textContent=JSON.stringify(e.data);document.body.append(p)})</script></body>`);
  if (url.pathname === '/web/admin.html') return res.end(fs.readFileSync(path.join(root, 'src/web/admin.html'),'utf8').replace('<head>','<head>'+bootstrap).replace('</body>',audit+'</body>'));
  const file = path.resolve(root, 'src', '.' + url.pathname);
  if (!file.startsWith(path.join(root,'src/web')+path.sep) || !fs.existsSync(file)) {res.statusCode=404;return res.end();}
  res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':'text/css');res.end(fs.readFileSync(file));
});
server.listen(0,'127.0.0.1',async()=>{
 try{
  for(const width of [320,1060]){
   const args=['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--hide-scrollbars','--force-device-scale-factor=1','--user-data-dir='+path.join(output,'profile-'+width+'-'+Date.now()),'--window-size='+Math.max(550,width+20)+',1000','--virtual-time-budget=12000','--screenshot='+path.join(output,width+'.png'),'--dump-dom','http://127.0.0.1:'+server.address().port+'/preview?width='+width];
   await new Promise((resolve,reject)=>execFile('C:/Program Files/Google/Chrome/Application/chrome.exe',args,{timeout:30000,maxBuffer:4e6},(err,stdout)=>{
    if(err)return reject(err);
    const match=stdout.match(/<pre id="qa-report" hidden="">([\s\S]*?)<\/pre>/);
    if(!match)return reject(Error('No browser report'));
    const report=JSON.parse(match[1].replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&'));
    console.log(JSON.stringify(report));if(report.errors.length)process.exitCode=1;resolve();
   }));
  }
 }catch(e){console.error(e);process.exitCode=1}finally{server.close()}
});
