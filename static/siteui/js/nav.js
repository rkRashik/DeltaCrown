// Notifications badge (auto-update + ARIA label)
(function(){
  const badge = document.getElementById('notif-badge');
  const notifBtn = document.querySelector('.notif-btn');
  if (!badge || !notifBtn) return;

  function setCount(n){
    badge.textContent = n > 0 ? String(n) : '';
    const label = n > 0 ? `Notifications (${n} unread)` : 'Notifications';
    notifBtn.setAttribute('aria-label', label);
  }

  async function update(){
    try{
      const r = await fetch('/notifications/unread_count/', { credentials:'same-origin' });
      if (!r.ok) return;
      const d = await r.json();
      if (typeof d.count === 'number') setCount(d.count);
    } catch(_){}
  }

  update();
  setInterval(update, 60_000);
})();

// Generic dropdowns (multiple instances, keyboard & focus handling)
(function(){
  // Utility
  function getItems(menu){
    return Array.from(menu.querySelectorAll('[role="menuitem"], a[href], button:not([disabled])'))
      .filter(el => !el.closest('[hidden]'));
  }
  function closeAll(){
    document.querySelectorAll('[data-menu],[data-avatar-menu]').forEach(m=>{
      m.hidden = true;
      m.removeAttribute('data-open');
    });
    document.querySelectorAll('[data-menu-toggle],[data-avatar-toggle]').forEach(b=>{
      b.setAttribute('aria-expanded', 'false');
    });
  }

  function setupPair(btn, menu){
    if (!btn || !menu) return;

    function open(){
      closeAll();
      menu.hidden = false;
      menu.setAttribute('data-open', 'true');
      btn.setAttribute('aria-expanded', 'true');
      const first = getItems(menu)[0];
      if (first) first.focus({ preventScroll: true });
    }
    function close(){
      menu.hidden = true;
      menu.removeAttribute('data-open');
      btn.setAttribute('aria-expanded', 'false');
    }
    function toggle(e){
      e.preventDefault();
      (menu.hidden ? open : close)();
    }

    // Click / keyboard on button
    btn.addEventListener('click', toggle);
    btn.addEventListener('keydown', (e)=>{
      if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault(); open();
      }
    });

    // Keyboard navigation inside menu
    menu.addEventListener('keydown', (e)=>{
      const items = getItems(menu);
      const idx = items.indexOf(document.activeElement);
      if (e.key === 'Escape'){ e.preventDefault(); close(); btn.focus(); }
      if (e.key === 'ArrowDown'){ e.preventDefault(); (items[idx+1] || items[0])?.focus(); }
      if (e.key === 'ArrowUp'){ e.preventDefault(); (items[idx-1] || items[items.length-1])?.focus(); }
      if (e.key === 'Home'){ e.preventDefault(); items[0]?.focus(); }
      if (e.key === 'End'){ e.preventDefault(); items[items.length-1]?.focus(); }
      if (e.key === 'Tab'){
        // If tabbing out and focus leaves menu, close it
        setTimeout(()=>{ if (!menu.contains(document.activeElement)) close(); }, 0);
      }
    });

    // Click outside to close
    document.addEventListener('click', (e)=>{
      if (!menu.contains(e.target) && !btn.contains(e.target)) close();
    });

    // Close on resize/scroll to avoid misplaced panels
    window.addEventListener('resize', close, { passive: true });
    window.addEventListener('scroll', close, { passive: true });
  }

  // Setup all standard dropdowns (Games, Create, etc.)
  document.querySelectorAll('[data-menu-toggle]').forEach(btn=>{
    // Find the paired [data-menu] near the button (sibling or within same .relative)
    const root = btn.closest('.relative') || btn.parentElement || document;
    const menuId = btn.getAttribute('aria-controls');
    const menu = menuId ? document.getElementById(menuId) : root.querySelector('[data-menu]');
    setupPair(btn, menu);
  });

  // Setup avatar dropdown(s)
  document.querySelectorAll('[data-avatar-toggle]').forEach(btn=>{
    const root = btn.closest('.relative') || btn.parentElement || document;
    const menuId = btn.getAttribute('aria-controls');
    const menu = menuId ? document.getElementById(menuId) : root.querySelector('[data-avatar-menu]');
    setupPair(btn, menu);
  });
})();
