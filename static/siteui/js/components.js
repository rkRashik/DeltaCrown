// Mobile drawer functionality is handled by nav.js - removed to prevent conflicts

// Overlay + drawer open with [data-overlay="#id"], close with [data-close-overlay]
(function(){
  document.addEventListener('click', (e)=>{
    const trig = e.target.closest('[data-overlay]');
    if (trig){
      const sel = trig.getAttribute('data-overlay');
      if(!sel) return;
      const ov = document.querySelector(sel);
      if(!ov) return;
      const open = ov.getAttribute('data-open') === 'true';
      if (!open){ ov.setAttribute('data-open','true'); trig.setAttribute('aria-expanded','true'); ov.querySelector('a,button')?.focus({preventScroll:true}); }
      else { ov.removeAttribute('data-open'); trig.setAttribute('aria-expanded','false'); }
      e.preventDefault();
      return;
    }
    const close = e.target.closest('[data-close-overlay]');
    if (close){ const ov = close.closest('.overlay'); if(ov){ ov.removeAttribute('data-open'); } }
  });
})();

// Collapse toggles: [data-collapse="#id"] toggles hidden/height
(function(){
  function toggle(el){
    const id = el.getAttribute('data-collapse'); if(!id) return;
    const target = document.querySelector(id); if(!target) return;
    const open = !target.classList.contains('hidden') && target.style.height !== '0px';
    if (open){
      target.style.height = target.scrollHeight + 'px';
      requestAnimationFrame(()=>{ target.style.height = '0px'; });
      target.classList.add('hidden');
      el.classList.remove('collapse-open');
    } else {
      target.classList.remove('hidden');
      target.style.height = 'auto';
      const h = target.scrollHeight; target.style.height = '0px';
      requestAnimationFrame(()=>{ target.style.height = h + 'px'; });
      el.classList.add('collapse-open');
    }
  }
  document.addEventListener('click', (e)=>{
    const t = e.target.closest('[data-collapse]'); if(t){ e.preventDefault(); toggle(t); }
  });
})();

// Django messages -> toasts
(function(){
  document.addEventListener('DOMContentLoaded', function(){
    try{
      const el = document.getElementById('dj-messages');
      if(!el) return;
      const data = JSON.parse(el.textContent || '[]');
      if (!Array.isArray(data)) return;
      data.forEach(m=>{
        if (window.DC && DC.toast){
          const title = (m.level||'info').replace(/\b\w/g, c=>c.toUpperCase());
          DC.toast({ title: title, message: m.text||'', timeout: 5000 });
        }
      });
    }catch(e){ /* no-op */ }
  });
})();

