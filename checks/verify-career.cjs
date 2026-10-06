// Standalone browser checks with synthetic data. Never starts the application or DB.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { execFile, execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'tools', 'ui-review', 'career');
fs.mkdirSync(output, { recursive: true });
const python = fs.existsSync(path.join(root,'.venv/Scripts/python.exe')) ? path.join(root,'.venv/Scripts/python.exe') : 'python';
const { careers, rooms } = JSON.parse(execFileSync(python, ['-c',
  'import json; from types import SimpleNamespace; from src.services.career_service import build_career; from src.services.avatar_service import wardrobe_catalog; from src.services.locker_room_service import build_locker_room; steps=(0,1,5,10,24,25,50,100); print(json.dumps(dict(careers={str(n):build_career(n,min(n,16),[dict(id=2,name="Nico",games_together=min(n,8),games_apart=min(n,3))] if n else []) for n in steps},rooms={str(n):build_locker_room(wardrobe_catalog(SimpleNamespace(cant_partidos=n,cant_partidos_ganados=min(n,16),is_bot=False,club_affinity="bolso"))) for n in steps})))'
], { cwd: root, encoding: 'utf8' }));
const base = {
  id: 1, name: 'santi.10', first_name: 'Santiago', last_name: 'Pereira', nationality: 'UY', is_bot: false,
  cant_partidos: 24, stats: { tiro: 82, ritmo: 76, fisico: 68, defensa: 71, aura: 89, elo: 1248 },
  matches_summary: { played: 24, won: 16, drawn: 3, winrate: 66.7, recent_results: ['win','draw','loss','win'] },
  recent_matches: [], relations: { most_played_with: [], top_allies: [], top_opponents: [] },
  evaluation: { can_evaluate: [], evaluations_by_player: [], total_received: 0 },
  achievements: { badges: [], club_choice_available: false, club_affinity: null },
  career: careers['24']
};
const avatar = { config: { version: 1, build: 'regular', skin: 'olive', hair: 'short', hair_color: 'dark', beard: 'none', equipment: { jersey: 'training', shorts: 'basic', boots: 'classic', cap: 'none', tattoo: 'none' } }, face_url: null, catalog: [] };
const cases = [[1440,24,'home'], [768,24,'home'], [390,24,'home'], [320,24,'home'], [390,0,'home'], [390,1,'home'], [390,5,'home'], [390,10,'home'], [390,25,'home'], [390,50,'home'], [390,100,'home'], [320,24,'long'], [390,24,'interactions'], [390,24,'public'], [1440,100,'public'], [390,24,'missing'], [390,24,'injection'], [390,24,'trophies']];
let fixture = base;
let mode = 'home';
const server = http.createServer((req,res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  res.setHeader('Cache-Control','no-store');
  const json = value => { res.setHeader('Content-Type','application/json'); res.end(JSON.stringify(value)); };
  if (url.pathname === '/preview') {
    res.setHeader('Content-Type','text/html; charset=utf-8');
    return res.end(`<html><body style="margin:0;background:#060817"><iframe style="display:block;margin:auto;border:0;width:${Number(url.searchParams.get('width'))}px;height:100vh" src="/web/${mode==='public'?'player.html?username=santi.10':''}"></iframe><script>addEventListener('message',e=>{if(e.origin!==location.origin)return;const p=document.createElement('pre');p.id='qa-report';p.hidden=true;p.textContent=JSON.stringify(e.data);document.body.append(p)})</script></body></html>`);
  }
  if (url.pathname === '/maxio/users/me') return json({ username: fixture.name, is_admin: false });
  if (url.pathname.endsWith('/profile')) return json(fixture);
  if (url.pathname === '/player/me/avatar') return json(avatar);
  if (url.pathname.startsWith('/leagues') || url.pathname.endsWith('/top_teammates') || url.pathname === '/player/directory') return json([]);
  if (url.pathname.endsWith('/photo')) { res.setHeader('Content-Type','image/png');return res.end(fs.readFileSync(path.join(root,'src/images/player-avatar-base-black.png'))); }
  if (url.pathname === '/web/' || url.pathname === '/web/player.html') {
    let html = fs.readFileSync(path.join(root, 'src/web', mode==='public'?'player.html':'index.html'),'utf8');
    html = html.replace(/<script src="https:\/\/telegram.org[^>]+><\/script>/,'');
    const bootstrap = `<script>sessionStorage.setItem('maxio_token','synthetic-only');window.__errors=[];addEventListener('error',e=>__errors.push(e.message));addEventListener('unhandledrejection',e=>__errors.push(String(e.reason)));</script>`;
    const audit = `<script>addEventListener('load',()=>setTimeout(()=>{
      const mode=${JSON.stringify(mode)};const data=${JSON.stringify(fixture).replace(/</g,'\\u003c')};
      const fail=m=>__errors.push(m);const visible=e=>!!e?.getClientRects().length&&getComputedStyle(e).display!=='none';
      if(!visible(document.querySelector('.career-hub')))fail('Career not visible');
      if(mode==='missing'){if(!document.querySelector('.career-unavailable'))fail('Missing data state');}
      else {
        if(innerWidth<=760){
          const mobile=document.querySelector('.mobile-club-profile');
          if(!visible(mobile))fail('Mobile player card hidden');
          if(mobile?.querySelector('h1')?.textContent!==data.name)fail('Mobile username missing');
          if(mobile?.querySelectorAll('.mobile-club-skill').length!==5)fail('Mobile skills missing');
          document.querySelector('.mobile-club-room-toggle')?.click();
        }
        if(!visible(document.querySelector('.locker-room')))fail('Locker room not visible');
        if(!document.querySelector('.locker-room > .hero')||!document.querySelector('.locker-profile > .career-hub'))fail('Profile not integrated');
        if(!document.querySelector('[data-equipment="jersey:training"] image')?.getAttribute('href').endsWith('/camiseta.png'))fail('Wrong initial shirt');
        if(document.querySelector('.career-title strong')?.textContent!==data.career.title)fail('Wrong title');
        const clothes=document.querySelectorAll('.locker-object');
        const unlocked=data.locker_room.equipment.filter(item=>item.unlocked);
        if(clothes.length!==unlocked.length+1)fail('Unowned or missing gear');
        if(innerWidth>760&&[...clothes].some(e=>!visible(e)))fail('Equipment hidden');
        if(innerWidth<=760&&!visible(document.querySelector('[data-equipment="jersey:training"]')))fail('Initial jersey hidden');
        if(document.querySelector('[data-equipment="jersey:manya"]'))fail('Wrong affinity displayed');
        const bg=document.querySelector('.locker-background');
        if(!bg.complete||!bg.naturalWidth)fail('Background not loaded');
        const rect=document.querySelector('.locker-room').getBoundingClientRect();
        if(Math.abs(rect.width/rect.height-1.5)>.01)fail('Distorted coordinate plane');
        if(unlocked.some(i=>i.slot==='shorts')&&!document.querySelector('.surface-bench'))fail('Missing folded gear');
        document.querySelector('.locker-viewport').scrollIntoView({behavior:'instant',block:'center'});
        if(document.querySelector('.locker-player') && visible(document.querySelector('.locker-player')))fail('Avatar still visible');
        if(!document.querySelector('.barrio-background'))fail('Barrio mural missing');
        const rewards=document.querySelector('.locker-rewards');rewards.open=true;
        if(rewards.querySelectorAll('.locker-reward').length!==data.locker_room.equipment.length)fail('Incomplete equipment catalog');
        rewards.open=false;
      }
      if(visible(document.querySelector('.barrio-avatar')))fail('Avatar still dominates');
      if(mode==='public'&&document.querySelector('.career-play'))fail('Owner action on public profile');
      if(mode==='interactions'){
        profile(data);profile(data);
        if(!document.querySelector('.locker-room > .hero'))fail('Profile separated on refresh');
        if(document.querySelectorAll('.career-hub').length!==1)fail('Duplicate career on refresh');
        const details=document.querySelector('.career-all');details.open=true;document.querySelector('.locker-rewards').open=true;profile(data);if(!document.querySelector('.career-all').open||!document.querySelector('.locker-rewards').open)fail('Lost expanded state');
        document.querySelector('[data-profile-view="avatar"]')?.click();
        if(visible(document.querySelector('#player-wardrobe'))||visible(document.querySelector('[data-player-avatar]')))fail('Avatar customization still visible');
        document.querySelector('[data-profile-view="cards"]')?.click();
        document.querySelector('.career-play')?.click();
        if(!document.querySelector('#match-dialog[open]'))fail('Match action did not open builder');
        document.querySelector('#match-dialog')?.close();
      }
      if(mode==='injection'&&window.__injected)fail('Unescaped identity');
      if(mode==='trophies'){
        const list=document.querySelector('.career-collection > .career-stamps');
        if(list?.children.length!==Math.min(6,data.career.earned_count))fail('Wrong earned trophy count');
        const details=document.querySelector('.career-all');details.open=true;
        if(details.querySelectorAll('.career-stamp').length!==data.career.milestones.length)fail('Incomplete milestone gallery');
        list.scrollIntoView({behavior:'instant'});
      }
      setTimeout(()=>{
        if(innerWidth<=760&&mode!=='missing'&&mode!=='trophies'){
          const toggle=document.querySelector('.mobile-club-room-toggle');
          if(toggle?.getAttribute('aria-expanded')==='true')toggle.click();
          document.querySelector('.mobile-club-profile')?.scrollIntoView({behavior:'instant',block:'start'});
        }
        const overflow=[...document.querySelectorAll('body *')].filter(e=>visible(e)&&!e.closest('.barrio-background,[hidden],.locker-room')).filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.right>innerWidth+2||r.left< -2)}).map(e=>e.className||e.id||e.tagName);
        if(document.documentElement.scrollWidth>innerWidth+2)fail('Page overflows');
        const scene=document.querySelector('.locker-room');const earned=document.querySelectorAll('.career-stamp.earned').length;
        parent.postMessage({mode,width:innerWidth,stage:scene?.dataset.stage,earned,overflow:[...new Set(overflow)],errors:__errors},location.origin);
      },500);
    },1000));</script>`;
    res.setHeader('Content-Type','text/html; charset=utf-8');return res.end(html.replace('<head>','<head>'+bootstrap).replace('</body>',audit+'</body>'));
  }
  const location = path.resolve(root, 'src', '.'+decodeURIComponent(url.pathname));
  if(!location.startsWith(path.join(root,'src')+path.sep)||!fs.existsSync(location)||!fs.statSync(location).isFile()){res.statusCode=404;return res.end('Not found');}
  res.setHeader('Content-Type', {'.js':'text/javascript','.css':'text/css','.png':'image/png'}[path.extname(location)]||'application/octet-stream');
  res.end(fs.readFileSync(location));
});
server.listen(0,'127.0.0.1', async()=>{
  try {
    for(const [width,played,variant] of cases){
      if(process.argv[2]&&!process.argv[2].split(',').includes(variant))continue;
      if(process.argv[3]&&width!==Number(process.argv[3]))continue;
      mode=variant;fixture=structuredClone(base);fixture.career=careers[String(played)];fixture.locker_room=rooms[String(played)];fixture.cant_partidos=played;fixture.matches_summary.played=played;fixture.matches_summary.won=Math.min(played,16);fixture.avatar=avatar;
      if(mode==='long')fixture.name='jugador_con_un_nombre_muy_largo_123456789';
      if(mode==='injection')fixture.name='<img src=x onerror="window.__injected=true">';
      if(mode==='missing')delete fixture.career;
      const args=['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--hide-scrollbars','--force-device-scale-factor=1','--user-data-dir='+path.join(output,'browser-profile-'+width+'-'+played+'-'+mode+'-'+Date.now()),'--window-size='+Math.max(516,width+16)+',1300','--virtual-time-budget=4000','--screenshot='+path.join(output,width+'-'+played+'-'+mode+'.png'),'--dump-dom','http://127.0.0.1:'+server.address().port+'/preview?width='+width];
      await new Promise((resolve,reject)=>execFile('C:/Program Files/Google/Chrome/Application/chrome.exe',args,{maxBuffer:12e6,timeout:25000},(error,stdout)=>{
        if(error)return reject(error);
        const match=stdout.match(/<pre id="qa-report" hidden="">([\s\S]*?)<\/pre>/);
        if(!match){fs.writeFileSync(path.join(output,'no-audit.html'),stdout);return reject(Error('No audit: '+mode));}
        const report=JSON.parse(match[1].replace(/&quot;/g,'"').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&'));
        console.log(JSON.stringify(report));if(report.errors.length||report.overflow.length)process.exitCode=1;resolve();
      }));
    }
  }catch(error){console.error(error);process.exitCode=1;}finally{server.close();}
});
