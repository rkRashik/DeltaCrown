(function(){
  // Lightweight micro-interactions beyond motion.js if needed
  // Example: add hover shine effect re-trigger
  document.querySelectorAll('.spotlight-card').forEach(card => {
    card.addEventListener('mousemove', () => {
      const s = card.querySelector('.shine'); if (!s) return;
      s.style.animation = 'none'; s.offsetHeight; s.style.animation = '';
    });
  });
})();

(function(){
  // Toast helper: DC.toast({image, title, message, time, timeout})
  window.DC = window.DC || {};
  DC.toast = function(opts){
    const o = opts||{};
    const host = document.getElementById('dc-toasts'); if(!host) return;
    const card = document.createElement('div');
    card.className = 'toast-card';
    card.setAttribute('role','status');
    card.setAttribute('aria-live','polite');

    const closeBtn = document.createElement('button');
    closeBtn.className = 'toast-close';
    closeBtn.setAttribute('aria-label','Dismiss');
    closeBtn.textContent = '×';
    card.appendChild(closeBtn);

    if (o.image){
      const imgWrap = document.createElement('div'); imgWrap.className = 'toast-img';
      const img = document.createElement('img'); img.src = o.image; img.alt = '';
      imgWrap.appendChild(img); card.appendChild(imgWrap);
    }

    const body = document.createElement('div'); body.className = 'toast-body';
    if (o.title){ const t = document.createElement('div'); t.className='toast-title'; t.textContent = o.title; body.appendChild(t); }
    const row = document.createElement('div'); row.className = 'flex items-end gap-2';
    const msg = document.createElement('div'); msg.className='toast-msg'; msg.textContent = o.message || '';
    row.appendChild(msg);
    if (o.time){ const meta = document.createElement('span'); meta.className='toast-meta'; meta.textContent = o.time; row.appendChild(meta); }
    body.appendChild(row);
    card.appendChild(body);

    host.appendChild(card);
    requestAnimationFrame(()=> card.setAttribute('data-show','true'));
    const close = ()=>{ card.removeAttribute('data-show'); setTimeout(()=>card.remove(), 180); };
    closeBtn.addEventListener('click', close);
    const t = Math.max(2000, Number(o.timeout||5000));
    setTimeout(close, t);
  };
})();
