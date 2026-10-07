// Standalone browser checks with synthetic data. Never starts the application or DB.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { execFile, execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const output = path.join(root, 'tools', 'ui-review', 'club');
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
const cases = [[390,24,'vitrina'],[320,24,'vitrina'],[390,24,'vestuario'],[390,24,'cantina'],[390,0,'empty'],[320,24,'long'],[390,24,'injection'],[1440,24,'vitrina']];
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
  if(url.pathname === '/player/me/matches'){
    const offset=Number(url.searchParams.get('offset')||0),limit=Number(url.searchParams.get('limit')||20);
    const all=mode==='empty'?[]:Array.from({length:23},(_,i)=>({match_id:100-i,date:'2026-09-20T18:00:00',team:'team1',result:i%3===0?'win':i%3===1?'draw':'loss',my_response:'win',teammates:[{name:'Nico'}],opponents:[{name:'Fede'}]}));
    return json({items:all.slice(offset,offset+limit),has_more:offset+limit<all.length,next_offset:Math.min(all.length,offset+limit)});
  }
  if(url.pathname === '/player/me/connections'){
    return json({items:mode==='empty'?[]:[{name:'Nico',games_together:8,games_apart:3,total_games:11},{name:'Fede',games_together:2,games_apart:5,total_games:7}],has_more:false,next_offset:2});
  }
  if (url.pathname === '/player/me/avatar') return json(avatar);
  if (url.pathname === '/leagues/mine') return json([{id:1,name:'Liga Nacional',is_system_managed:true,role:'member',member_count:12,is_public:true,rankings:[{ranking_type:'general',position:3,points:120},{ranking_type:'solo_duo',position:4,points:110},{ranking_type:'grupo',position:5,points:100}]}]);
  if (url.pathname === '/leagues/1') return json({id:1,name:'Liga Nacional',members:Array.from({length:18},(_,i)=>({username:i===0?fixture.name:'Jugador '+i,rankings:[{ranking_type:'general',position:i+1,points:120-i,matches_played:20-i,wins:12-i,losses:5,draws:3},{ranking_type:'solo_duo',position:i+1,points:110-i},{ranking_type:'grupo',position:i+1,points:100-i}]}))});
  if (url.pathname.startsWith('/leagues') || url.pathname.endsWith('/top_teammates') || url.pathname === '/player/directory') return json([]);
  if (url.pathname.endsWith('/photo')) { res.setHeader('Content-Type','image/png');return res.end(fs.readFileSync(path.join(root,'src/images/player-avatar-base-black.png'))); }
  if (url.pathname === '/web/' || url.pathname === '/web/player.html') {
    let html = fs.readFileSync(path.join(root, 'src/web', mode==='public'?'player.html':'index.html'),'utf8');
    html = html.replace(/<script src="https:\/\/telegram.org[^>]+><\/script>/,'');
    const bootstrap = `<script>sessionStorage.setItem('maxio_token','synthetic-only');window.__errors=[];addEventListener('error',e=>__errors.push(e.message));addEventListener('unhandledrejection',e=>__errors.push(String(e.reason)));</script>`;
    const audit = `<script>addEventListener('load',()=>setTimeout(async()=>{
      const mode=${JSON.stringify(mode)};const data=${JSON.stringify(fixture).replace(/</g,'\\u003c')};
      const fail=m=>__errors.push(m);
      const visible=e=>!!e?.getClientRects().length&&getComputedStyle(e).display!=='none';
      const wait=()=>new Promise(r=>setTimeout(r,400));
      try{
        const root=document.querySelector('#club-app');
        if(!visible(root))fail('Club not visible');
        if(document.querySelectorAll('.club-bottom-nav button').length!==4)fail('Missing rooms');
        const roomOrder=[...document.querySelectorAll('.club-bottom-nav button')].map(button=>button.dataset.room).join(',');
        if(roomOrder!=='cantina,barrio,vitrina,vestuario')fail('Wrong room order');
        if(!getComputedStyle(document.querySelector('#dashboard')).getPropertyValue('--club-view'))fail('Missing panorama view');
        if(document.querySelector('.club-bottom-nav [aria-current]')?.dataset.room!=='vitrina')fail('Wrong initial room');
        if(!document.querySelector('.club-identity h2')?.textContent.includes(data.name))fail('Identity missing');
        if(document.querySelectorAll('.club-skill').length!==6||!document.querySelector('.club-skill[data-skill="ovr"]'))fail('Skills missing');
        if(document.querySelectorAll('.club-award').length!==data.career.earned_count)fail('Incorrect awards');
        const go=key=>root.querySelector('.club-bottom-nav [data-room="'+key+'"]').click();
        root.querySelector('#club-vitrina .club-form')?.click();await wait();
        if(root.querySelector('.club-bottom-nav [aria-current]')?.dataset.room!=='vestuario')fail('Recent form did not open Vestuario');
        go('vitrina');await wait();
        go('vestuario');await wait();
        if(visible(document.querySelector('#club-vitrina')))fail('Screens overlap');
        if(mode!=='empty'){
          if(document.querySelectorAll('.club-match').length!==20)fail('First history page missing');
          root.querySelector('[data-more="matches"]').click();await wait();
          if(document.querySelectorAll('.club-match').length!==23)fail('Full history not reachable');
          if(!root.querySelector('[data-more="matches"]').hidden)fail('End of history not handled');
          root.querySelector('.club-match summary').click();
          if(!visible(root.querySelector('.club-match-detail')))fail('Match detail hidden');
        }
        root.querySelector('[data-club-action="create"]').click();await wait();
        if(!document.querySelector('#match-dialog[open]'))fail('Creator did not open');
        document.querySelector('#match-dialog')?.close();
        go('cantina');await wait();
        if(mode!=='empty'&&document.querySelectorAll('.club-peer').length!==2)fail('Connections missing');
        go('barrio');await wait();
        if(!root.querySelector('#club-barrio #club-leagues-slot'))fail('League room missing');
        root.querySelector('[data-league-expand]')?.click();await wait();
        const memberList=root.querySelector('.club-league-member-list');
        if(!memberList)fail('Expanded league table missing');
        if(memberList.scrollWidth>memberList.clientWidth+1||document.documentElement.scrollWidth>innerWidth+2)fail('Expanded league table overflows');
        go('vitrina');
        profile(data);await wait();
        if(document.querySelectorAll('#club-app').length!==1||document.querySelectorAll('.club-bottom-nav').length!==1)fail('Duplicate app on refresh');
        if(mode==='injection'&&window.__injected)fail('Unescaped name');
        if(mode==='empty'&&document.querySelectorAll('.club-award').length)fail('Invented award');
        go(mode==='vestuario'?'vestuario':mode==='cantina'?'cantina':'vitrina');await wait();
      }catch(error){fail(error.stack||error.message);}
      window.scrollTo(0,0);
      const overflow=[...document.querySelectorAll('#club-app *')].filter(e=>visible(e)&&!e.closest('[hidden]')).filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.right>innerWidth+2||r.left< -2)}).map(e=>e.className||e.tagName);
      if(document.documentElement.scrollWidth>innerWidth+2)fail('Page overflows');
      parent.postMessage({mode,width:innerWidth,overflow:[...new Set(overflow)],errors:__errors},location.origin);
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
      const args=['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--hide-scrollbars','--force-device-scale-factor=1','--user-data-dir='+path.join(output,'browser-profile-'+width+'-'+played+'-'+mode+'-'+Date.now()),'--window-size='+Math.max(516,width+16)+',1300','--virtual-time-budget=12000','--screenshot='+path.join(output,width+'-'+played+'-'+mode+'.png'),'--dump-dom','http://127.0.0.1:'+server.address().port+'/preview?width='+width];
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
