(function(){
  const store={get:k=>{try{return localStorage.getItem(k)}catch(e){return null}},set:(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}}};
  const today=new Date().toISOString().slice(0,10);
  let lang=store.get('lang')||'en', asof=store.get('asof')||today;
  const dateInput=document.getElementById('asof'); dateInput.value=asof;
  function render(){
    document.body.className=document.body.className.replace(/\bl-\S+/g,'').trim()+' l-'+lang;
    document.querySelectorAll('.langs button').forEach(b=>b.classList.toggle('on',b.dataset.lang===lang));
    const secs=[...document.querySelectorAll('section.text')];
    if(!secs.length)return;
    let best=null;
    for(const s of secs){ if(s.dataset.lang===lang && s.dataset.from<=asof && (!best||s.dataset.from>best.dataset.from)) best=s; }
    secs.forEach(s=>s.hidden=(s!==best));
    const miss=document.getElementById('missing'); if(miss) miss.hidden=!!best;
    document.querySelectorAll('li.ver').forEach(v=>v.classList.toggle('on',v.dataset.from<=asof&&(!v.dataset.to||asof<=v.dataset.to)));
  }
  document.querySelectorAll('.langs button').forEach(b=>b.onclick=()=>{lang=b.dataset.lang;store.set('lang',lang);render();});
  document.querySelectorAll('li.ver button[data-asof]').forEach(b=>b.onclick=()=>{
    asof=b.dataset.asof; dateInput.value=asof; store.set('asof',asof); render();
    const h=document.querySelector('main h1'); if(h)h.scrollIntoView({behavior:'smooth'});
  });
  dateInput.onchange=()=>{asof=dateInput.value||today;store.set('asof',asof);render();};
  // Connection lists are stored once per page (#conns) and copied into a toggle when opened.
  const conns=document.getElementById('conns');
  document.querySelectorAll('details.conn').forEach(d=>d.addEventListener('toggle',()=>{
    if(d.open&&conns&&!d.querySelector('ul')){const ul=conns.querySelector('ul[data-c="'+d.dataset.c+'"]');if(ul)d.appendChild(ul.cloneNode(true));}
  }));
  // Comments (Giscus): loaded only when the Comments tab is first opened.
  function loadComments(){
    const host=document.querySelector('.giscus-host'); if(!host||host.dataset.loaded)return;
    host.dataset.loaded='1';
    const d=host.dataset, s=document.createElement('script'), gl={'pl-official':'pl'}[lang]||lang;
    const cfg={'repo':d.repo,'repo-id':d.repoId,'category':d.category,'category-id':d.categoryId,
      'mapping':'specific','term':d.term,'strict':'1','reactions-enabled':'1','emit-metadata':'0',
      'input-position':'top','theme':'preferred_color_scheme','lang':gl,'loading':'lazy'};
    s.src='https://giscus.app/client.js'; s.async=true; s.crossOrigin='anonymous';
    for(const k in cfg)s.setAttribute('data-'+k,cfg[k]);
    host.appendChild(s);
  }
  document.querySelectorAll('.tabs').forEach(t=>{
    const heads=t.querySelectorAll('.tabheads button'), panes=t.querySelectorAll('.pane');
    heads.forEach(h=>h.onclick=()=>{const on=!h.classList.contains('on');heads.forEach(x=>x.classList.remove('on'));panes.forEach(p=>p.hidden=true);if(on){h.classList.add('on');const p=t.querySelector('.pane[data-tab="'+h.dataset.tab+'"]');p.hidden=false;if(p.querySelector('.giscus-host'))loadComments();}});
  });
  const root=document.body.dataset.root, box=document.getElementById('search'), res=document.getElementById('results');
  let index=null;
  box.addEventListener('input',async()=>{
    if(!index){index=await (await fetch(root+'search.json')).json();}
    const q=box.value.trim().toLowerCase(); if(q.length<2){res.hidden=true;return;}
    const all=e=>(e.w+' '+Object.values(e.t).join(' ')).toLowerCase();
    const hits=index.filter(e=>all(e).includes(q)).slice(0,40);
    res.innerHTML=hits.map(h=>'<a href="'+root+h.u+'">'+(h.t[lang]||h.t.en).replace(/</g,'&lt;')+' <small>'+h.w+'</small></a>').join('')||'<em>–</em>';
    res.hidden=false;
  });
  document.addEventListener('click',e=>{if(!res.contains(e.target)&&e.target!==box)res.hidden=true;});
  // Table of contents: a column that can be hidden on wide screens (remembered), a drawer
  // that is closed by default on phones and tablets.
  const menu=document.getElementById('menu'), toc=document.getElementById('toc');
  if(toc&&window.TOC){
    toc.innerHTML=window.TOC;
    const page=decodeURIComponent(location.pathname.split('/').pop());
    toc.querySelectorAll('li > a').forEach(a=>{if(a.getAttribute('href')===page){a.parentElement.classList.add('current');const ch=a.closest('li.chap');if(ch)ch.classList.add('open');}});
  }
  if(menu&&toc){
    const narrow=matchMedia('(max-width:800px)');
    const top=document.querySelector('.top');
    const setTop=()=>document.documentElement.style.setProperty('--top',top.offsetHeight+'px');
    function apply(){
      setTop();
      const open=narrow.matches?document.body.classList.contains('toc-open'):store.get('toc')!=='hidden';
      document.body.classList.toggle('toc-closed',!narrow.matches&&!open);
      if(!narrow.matches)document.body.classList.remove('toc-open');
      menu.setAttribute('aria-expanded',String(open));
    }
    function scrollCurrent(){const cur=toc.querySelector('li.current');if(cur)toc.scrollTop=cur.offsetTop-toc.clientHeight/2;}
    menu.onclick=()=>{
      if(narrow.matches){document.body.classList.toggle('toc-open');}
      else{store.set('toc',store.get('toc')==='hidden'?'shown':'hidden');}
      apply(); if(menu.getAttribute('aria-expanded')==='true')scrollCurrent();
    };
    document.addEventListener('click',e=>{if(narrow.matches&&document.body.classList.contains('toc-open')&&!toc.contains(e.target)&&!menu.contains(e.target)){document.body.classList.remove('toc-open');apply();}});
    narrow.addEventListener('change',apply); addEventListener('resize',setTop);
    apply(); addEventListener('load',()=>{if(!narrow.matches)scrollCurrent();});
  }
  // Escape closes the drawer.
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&document.body.classList.contains('toc-open')){document.body.classList.remove('toc-open');if(menu)menu.setAttribute('aria-expanded','false');}
  });
  render();
  // Every language/date version of the text repeats the anchors: go to the one that is shown.
  function toHash(){
    const id=decodeURIComponent(location.hash.slice(1)); if(!id)return;
    const el=document.querySelector('section.text:not([hidden]) [id="'+CSS.escape(id)+'"]');
    if(el){el.scrollIntoView();el.classList.remove('target');void el.offsetWidth;el.classList.add('target');return;}
    // Guidelines Chapter page: sections now have pages of their own; follow older links there
    const moved=document.querySelector('nav.contents a[data-a="'+CSS.escape(id)+'"]');
    if(moved)location.replace(moved.href);
  }
  addEventListener('hashchange',toHash); toHash();
})();
