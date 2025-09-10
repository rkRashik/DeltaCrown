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
  function bindToggle(btnSelector, menuSelector){
    const btn = document.querySelector(btnSelector); const menu = document.querySelector(menuSelector);
    if(!btn || !menu) return;
    function close(){ menu.hidden = true; btn.setAttribute('aria-expanded','false'); }
    btn.addEventListener('click', (e)=>{ e.preventDefault(); const open=menu.hidden===false; document.querySelectorAll('[data-menu],[data-avatar-menu]').forEach(m=>m.hidden=true); if(!open){ menu.hidden=false; btn.setAttribute('aria-expanded','true'); } else { close(); } });
    document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') close(); });
    document.addEventListener('click', (e)=>{ if(!menu.contains(e.target) && !btn.contains(e.target)) close(); });
  }
  bindToggle('[data-menu-toggle]', '[data-menu]');
  bindToggle('[data-avatar-toggle]', '[data-avatar-menu]');
})();
