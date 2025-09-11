(function(){
  const badge = document.getElementById('notif-badge');
  if (!badge) return;
  function update(){
    fetch('/notifications/unread_count/', {credentials:'same-origin'})
      .then(r => r.ok ? r.json() : {count:0})
      .then(d => { if (typeof d.count === 'number') badge.textContent = d.count > 0 ? d.count : ''; });
  }
  update();
  setInterval(update, 60000);
})();

// Simple dropdowns for Create and Avatar
(function(){
  function setupDropdown(btn, menu){
    const items = () => Array.from(menu.querySelectorAll('[role="menuitem"],.dd-item, a, button'))
      .filter(el=>!el.hasAttribute('disabled'));
    function open(){
      document.querySelectorAll('[data-menu],[data-avatar-menu]').forEach(m=>{ m.hidden=true; m.removeAttribute('data-open'); });
      menu.hidden = false; menu.setAttribute('data-open','true');
      btn.setAttribute('aria-expanded','true');
      const first = items()[0]; if(first) first.focus({preventScroll:true});
    }
    function close(){ menu.hidden = true; menu.removeAttribute('data-open'); btn.setAttribute('aria-expanded','false'); }
    btn.addEventListener('click', (e)=>{ e.preventDefault(); (menu.hidden?open:close)(); });
    btn.addEventListener('keydown', (e)=>{ if(e.key==='ArrowDown'){ e.preventDefault(); open(); }});
    menu.addEventListener('keydown', (e)=>{
      const it = items(); const idx = it.indexOf(document.activeElement);
      if(e.key==='Escape'){ e.preventDefault(); close(); btn.focus(); }
      if(e.key==='ArrowDown'){ e.preventDefault(); const n = it[Math.min(it.length-1, (idx<0?0:idx+1))]; if(n) n.focus(); }
      if(e.key==='ArrowUp'){ e.preventDefault(); const p = it[Math.max(0, (idx<0?0:idx-1))]; if(p) p.focus(); }
      if(e.key==='Home'){ e.preventDefault(); if(it[0]) it[0].focus(); }
      if(e.key==='End'){ e.preventDefault(); if(it[it.length-1]) it[it.length-1].focus(); }
    });
    document.addEventListener('click', (e)=>{ if(!menu.contains(e.target) && !btn.contains(e.target)) close(); });
  }
  const pairs = [
    ['[data-menu-toggle]','[data-menu]'],
    ['[data-avatar-toggle]','[data-avatar-menu]']
  ];
  pairs.forEach(([bs,ms])=>{ const b=document.querySelector(bs), m=document.querySelector(ms); if(b&&m) setupDropdown(b,m); });
})();
