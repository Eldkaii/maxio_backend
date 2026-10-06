/* Photographic layers use the background's 1536 x 1024 coordinates. */
(() => {
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const atlas='/images/locker-equipment-atlas-v1.png';
 const art={
 training:{src:'/images/camiseta.png',size:[1312,1332],crop:[180,-55,980,1320],anchor:[495,5]},
 bolso:{crop:[565,0,440,550],anchor:[209,17]},
 manya:{src:'/images/locker-shirt-manya-hanger-v1.png',size:[1199,1312],crop:[70,0,1060,1312],anchor:[520,25]},
 folded:{crop:[1050,200,470,300],anchor:[235,275]},
 winner:{crop:[10,590,500,390],anchor:[250,365]},
 lime:{crop:[520,600,520,360],anchor:[260,318]},
 street:{crop:[1040,610,480,350],anchor:[240,334]}
 };
 // Contact point (hook or base), width and surface. Add future gear here.
 const placements={
 'jersey:training':{art:'training',x:745,y:333,width:205,surface:'rail'},
 'jersey:bolso':{art:'bolso',x:1000,y:333,width:210,surface:'rail'},
 'jersey:manya':{art:'manya',x:1000,y:333,width:220,surface:'rail'},
 'shorts:winner':{art:'winner',x:1235,y:662,width:110,surface:'bench'},
 'boots:lime':{art:'lime',x:1000,y:745,width:165,surface:'shelf'},
 'cap:street':{art:'street',x:750,y:662,width:105,surface:'bench'}
 };
 let printSequence=0;
 function photo(key, username=''){
 const a=art[key], [iw,ih]=a.size||[1536,1024];
 // Uppercase is presentation only: account names and accessible labels stay intact.
 const shirtName=String(username).toLocaleUpperCase('es');
 const letters=Array.from(shirtName).length;
 const printId=`shirt-print-${++printSequence}`;
 // A shallow shoulder arc and tall condensed lettering, like a real kit transfer.
 // Unique fragment IDs keep repeated renders and catalog SVGs independent.
 const print=key==='training'&&shirtName?`<defs>
 <path id="${printId}-arc" d="M350 405 Q660 330 970 405"/>
 <filter id="${printId}-ink" x="-5%" y="-15%" width="110%" height="130%" color-interpolation-filters="sRGB">
 <feTurbulence type="fractalNoise" baseFrequency=".035 .11" numOctaves="2" seed="8" result="weave"/>
 <feDisplacementMap in="SourceGraphic" in2="weave" scale="1.3" xChannelSelector="R" yChannelSelector="G"/>
 </filter><mask id="${printId}-wear" maskUnits="userSpaceOnUse" x="490" y="420" width="340" height="420">
 <rect x="490" y="420" width="340" height="420" fill="white"/>
 <g fill="none" stroke="black" stroke-linecap="round">
 <path d="m558 521 19 5 8-3 15 4m81-38-6 21 4 12-5 18m-91 59 28-4 9 3 26-5m37 90 14-3 21 4m-142 63 18-5 8 3 15-4m62-18-5 17 3 11" stroke-width="3"/>
 <path d="m566 555 9 2m118 16 13-4m-112 95 11 3m65 73 12-2m-92 24 14 2" stroke-width="5"/>
 </g><g fill="black"><ellipse cx="578" cy="542" rx="3" ry="5"/><ellipse cx="705" cy="620" rx="4" ry="2"/><ellipse cx="615" cy="730" rx="3" ry="4"/><circle cx="680" cy="759" r="2.5"/></g>
 </mask></defs><g transform="rotate(-1 660 375)"><text class="locker-shirt-print" text-anchor="middle" font-size="${Math.min(132,2000/Math.max(1,letters))}" filter="url(#${printId}-ink)"><textPath href="#${printId}-arc" startOffset="50%" textLength="${Math.min(570,letters*57)}" lengthAdjust="spacingAndGlyphs">${esc(shirtName)}</textPath></text><text class="locker-shirt-print locker-shirt-number" mask="url(#${printId}-wear)" x="660" y="790" text-anchor="middle" font-size="440" textLength="215" lengthAdjust="spacingAndGlyphs" filter="url(#${printId}-ink)">9</text></g>`:'';
 return `<svg class="locker-photo" viewBox="${a.crop.join(' ')}" aria-hidden="true">${key==='training'?'<path d="M655 -30 C655 -60 695 -60 695 -34 C695 -17 675 -18 675 3" fill="none" stroke="#b4aea1" stroke-width="7"/>':''}<image href="${a.src||atlas}" width="${iw}" height="${ih}"/>${print}</svg>`;
 }
 function layer(item){
 const p=placements[item.slot+':'+item.id]; if(!p)return '';
 const a=art[p.art],s=p.width/a.crop[2];
 return `<div class="locker-object surface-${p.surface}" data-equipment="${esc(item.slot+':'+item.id)}" role="img" aria-label="${esc(item.name)}${item.username?' · '+esc(item.username):''}" style="left:${(p.x-a.anchor[0]*s)/1536*100}%;top:${(p.y-a.anchor[1]*s)/1024*100}%;width:${p.width/1536*100}%;height:${a.crop[3]*s/1024*100}%">${photo(p.art,item.username)}</div>`;
 }
 function mount(player,hub,{publicView=false}={}){
 const room=player.locker_room,equipment=room?.equipment||[],earned=equipment.filter(i=>i.unlocked);
 const initial={slot:'jersey',id:'training',name:'Camiseta de entrenamiento inicial, dorsal 9',username:player.name||''};
 const stats=player.matches_summary||{};
 const number=value=>Number.isFinite(Number(value))?Number(value):0;
 const fullName=[player.first_name,player.last_name].map(v=>String(v||'').trim()).filter(Boolean).join(' ')||player.name||'Jugador';
 const countryCode=String(player.nationality||'').trim().toUpperCase();
 let nationality=countryCode||'Nacionalidad sin indicar';
 if (/^[A-Z]{2}$/.test(countryCode)) {
   try { nationality=new Intl.DisplayNames(['es'],{type:'region'}).of(countryCode)||countryCode; } catch { /* Preserve the supplied country if Intl is unavailable. */ }
 }
 const fit=(text,width,size)=>Array.from(String(text)).length*size*.63>width?` textLength="${width}" lengthAdjust="spacingAndGlyphs"`:'';
 // Fixed small variations emulate chalk strokes without jumping on refresh.
 const hand=text=>` rotate="${Array.from(String(text),(_,i)=>[-2,1,-1,2,0,-1,1][i%7]).join(' ')}"`;
 const board=`<svg class="locker-chalkboard" viewBox="0 0 480 320" role="img" aria-label="Ficha de ${esc(fullName)} escrita en tiza"><title>${esc(fullName)} · ${esc(nationality)} · ${esc(player.career?.title||'')} · ELO ${number(player.stats?.elo)} · ${number(stats.played)} partidos · ${number(stats.won)} ganados · ${number(stats.drawn)} empates · ${number(stats.winrate)}% victorias</title>
 <g fill="currentColor">
 <text x="18" y="41" transform="rotate(-1.4 18 41)" class="chalk-player-name"${fit(fullName,435,36)}${hand(fullName)}>${esc(fullName)}</text>
 <text x="27" y="72" transform="rotate(.8 27 72)" class="chalk-nationality"${fit(nationality,421,19)}${hand(nationality)}>${esc(nationality)}</text>
 <text x="20" y="102" transform="rotate(-.7 20 102)" class="chalk-rank"${fit(player.career?.title||'Recién llegado',425,21)}>${esc(player.career?.title||'Recién llegado')}</text>
 ${[[32,160,-2,number(player.stats?.elo),'ELO'],[205,156,1.5,number(stats.played),'partidos'],[355,163,-1,number(stats.won),'ganados']].map(([x,y,angle,value,label])=>`<g transform="rotate(${angle} ${x} ${y})"><text x="${x}" y="${y}" class="chalk-stat-value"${fit(value,105,42)}${hand(value)}>${value}</text><text x="${x+4}" y="${y+23}" class="chalk-stat-label"${hand(label)}>${label}</text></g>`).join('')}
 <text x="20" y="220" transform="rotate(-.9 20 220)" class="chalk-detail">${number(stats.drawn)} empates · ${number(stats.winrate)}% victorias</text>
 <text x="25" y="247" transform="rotate(.6 25 247)" class="chalk-detail">${number(player.career?.earned_count)} logros conseguidos</text>
 <text x="17" y="281" transform="rotate(-1.2 17 281)" class="chalk-caption">Forma reciente</text>
 ${(stats.recent_results||[]).slice(-5).map((r,i)=>`<text x="${185+i*29}" y="${278+[0,-2,1,-1,2][i]}" transform="rotate(${[-3,2,-1,3,-2][i]} ${185+i*29} 278)" class="chalk-form">${({win:'V',draw:'E',loss:'D'})[r]||'–'}</text>`).join('')}
 </g>
 <g fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity=".48"><path d="M18 114q94 3 183-1t239 0M25 199q97-4 180 0t243-1"/>
 <path d="m366 230 10 11m-10 0 10-11m55 24 10 11m-10 0 10-11M378 227q28-22 58-3m-8-7 9 7-10 3M388 277q23 6 37-10m-9 2 10-3-2 9"/>
 <circle cx="369" cy="279" r="6"/><circle cx="447" cy="236" r="5"/></g></svg>`;
 hub.setAttribute('aria-label',publicView?'Vestuario del jugador':'Tu vestuario');
 const skills=[['tiro','Tiro'],['ritmo','Ritmo'],['fisico','Físico'],['defensa','Defensa'],['aura','Aura']];
 const mobile=`<section class="mobile-club-profile" aria-label="Ficha del jugador">
 <div class="mobile-club-identity"><span class="mobile-club-kicker">FÚTBOL DE BARRIO</span><h1>${esc(player.name||'Jugador')}</h1><p>${esc(fullName)} <span>· ${esc(nationality)}</span></p><span class="mobile-club-rank">${esc(player.career?.title||'Recién llegado')}</span></div>
 <div class="mobile-club-numbers" aria-label="Resumen de partidos"><div><strong>${number(player.stats?.elo)}</strong><span>ELO</span></div><div><strong>${number(stats.played)}</strong><span>partidos jugados</span></div><div><strong>${number(stats.won)}</strong><span>ganados</span></div></div>
 <div class="mobile-club-form"><span>${number(stats.winrate)}% victorias · ${number(stats.drawn)} empates</span><div aria-label="Últimos resultados">${(stats.recent_results||[]).slice(-5).map(r=>`<b class="result-${esc(r)}" title="${({win:'Victoria',draw:'Empate',loss:'Derrota'})[r]||'Sin resultado'}">${({win:'V',draw:'E',loss:'D'})[r]||'–'}</b>`).join('')}</div></div>
 <section class="mobile-club-skills" aria-label="Habilidades"><div class="mobile-club-section-title"><h2>Tu juego</h2><span>ATRIBUTOS / 100</span></div>${skills.map(([key,label])=>{const value=Math.min(100,Math.max(0,number(player.stats?.[key])));return `<div class="mobile-club-skill"><span>${label}</span><meter min="0" max="100" value="${value}" aria-label="${label}">${value}</meter><b>${value}</b></div>`}).join('')}</section>
 ${publicView?'':'<button type="button" class="mobile-club-play">Armá un partido <span aria-hidden="true">↗</span></button>'}
 <button type="button" class="mobile-club-room-toggle" aria-expanded="false"><span>Tu vestuario <small>${earned.length} prendas desbloqueadas · ${number(player.career?.earned_count)} logros</small></span><b aria-hidden="true">⌄</b></button>
 </section>`;
 hub.innerHTML=`<header class="locker-heading"><div><span class="career-kicker">CADA PARTIDO DEJA ALGO</span><h2>${publicView?'El vestuario':'Tu vestuario'}</h2></div><span class="locker-count">${room?earned.length+' desbloqueadas':'Sin datos'}</span></header>
 <div class="locker-viewport" tabindex="0" aria-label="Perfil y vestuario del jugador"><div class="locker-room"><picture><source media="(max-width: 760px)" srcset="/images/locker-mobile-landscape-v2.png"><img class="locker-background" src="/images/locker-chalkboard-reference-v8.jpg" alt="Vestuario de barrio con pizarrón de tiza, indumentaria y una persona encapuchada de espaldas" width="1536" height="1024"></picture><svg class="locker-clean-slate" viewBox="55 242 480 338" preserveAspectRatio="none" aria-hidden="true"><image href="/images/locker-chalkboard-v8.png" width="1536" height="1024"/></svg>${board}${room?[initial,...earned].map(layer).join(''):''}</div></div>
 <nav class="locker-navigation" aria-label="Recorrer el vestuario"><button type="button" data-room-direction="-1" aria-label="Ver casilleros anteriores">←</button><span>Recorré tu vestuario</span><button type="button" data-room-direction="1" aria-label="Ver casilleros siguientes">→</button></nav>
 <div class="locker-inventory"><p class="locker-intro">${!room?'No pudimos cargar la indumentaria. Volvé a cargar el perfil.':earned.length?'Las prendas que ganaste ya tienen su lugar. Todavía queda espacio para lo que viene.':'Tu primera camiseta ya está colgada. Jugá partidos y llená el vestuario con indumentaria.'}</p>
 ${room?`<details class="locker-rewards"><summary>Indumentaria · ${earned.length} / ${equipment.length} desbloqueada</summary><ul>${equipment.map(item=>{const p=placements[item.slot+':'+item.id];return `<li class="locker-reward ${item.unlocked?'earned':'locked'}">${p?photo(p.art):''}<div><strong>${esc(item.name)}</strong><small>${item.unlocked?'Desbloqueada':esc(item.requirement)}</small>${item.unlocked?'':`<progress value="${Number(item.progress)||0}" max="${Number(item.target)||1}" aria-label="Progreso para ${esc(item.name)}"></progress><small>${Number(item.progress)||0} / ${Number(item.target)||1}</small>`}</div></li>`}).join('')}</ul></details>`:''}
 <div class="locker-showcase-note"><span aria-hidden="true">◇</span><p><strong>Un lugar para lo que viene</strong>La vitrina espera tus logros, medallas, trofeos y copas. Próximamente.</p></div>${publicView?'':'<button type="button" class="career-play">Armá el próximo partido <span aria-hidden="true">↗</span></button>'}</div>`;
 const viewport=hub.querySelector('.locker-viewport');
 hub.insertAdjacentHTML('afterbegin',mobile);
 hub.classList.remove('mobile-room-expanded');
 hub.querySelector('.mobile-club-play')?.addEventListener('click',()=>document.querySelector('#new-match')?.click());
 hub.querySelector('.mobile-club-room-toggle')?.addEventListener('click',event=>{
   const expanded=hub.classList.toggle('mobile-room-expanded');
   event.currentTarget.setAttribute('aria-expanded',String(expanded));
 });
 const update=()=>hub.querySelectorAll('[data-room-direction]').forEach(b=>{b.disabled=Number(b.dataset.roomDirection)<0?viewport.scrollLeft<2:viewport.scrollLeft+viewport.clientWidth>=viewport.scrollWidth-2;});
 hub.querySelectorAll('[data-room-direction]').forEach(b=>b.addEventListener('click',()=>viewport.scrollBy({left:Number(b.dataset.roomDirection)*viewport.clientWidth*.8,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})));
 viewport.addEventListener('scroll',update,{passive:true});requestAnimationFrame(update);
 hub.querySelector('.career-play')?.addEventListener('click',()=>document.querySelector('#new-match')?.click());
 }
 window.MaxioLockerRoom=Object.freeze({mount});
})();
