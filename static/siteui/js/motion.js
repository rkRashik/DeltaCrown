(function(){
  var prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---------- Reveal on scroll ----------
  function initReveal(){
    var els = document.querySelectorAll('[data-reveal]');
    if (!els.length) return;
    if (prefersReduced) {
      els.forEach(function(el){ el.removeAttribute('data-reveal'); });
      return;
    }
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){
        if (e.isIntersecting){
          e.target.classList.add('dc-revealed');
          io.unobserve(e.target);
        }
      });
    }, {threshold: 0.12});
    els.forEach(function(el){ io.observe(el); });
  }

  // ---------- Count-up ----------
  function initCountUp(){
    if (prefersReduced) return;
    var els = document.querySelectorAll('[data-count-to]');
    els.forEach(function(el){
      var to = parseInt(el.getAttribute('data-count-to'), 10);
      if (isNaN(to)) return;

      var from = parseInt(el.getAttribute('data-count-from') || '0', 10);
      var dur = parseInt(el.getAttribute('data-count-duration') || '1200', 10);
      var start = null;

      function step(ts){
        if (!start) start = ts;
        var t = Math.min(1, (ts - start) / dur);
        var val = Math.floor(from + (to - from) * t);
        el.textContent = toLocaleInt(val);
        if (t < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }

  function toLocaleInt(n){
    try { return n.toLocaleString(); } catch (_) { return String(n); }
  }

  // ---------- Countdown ----------
  function initCountdown(){
    var el = document.querySelector('[data-countdown-to]');
    if (!el) return;
    var iso = el.getAttribute('data-countdown-to');
    if (!iso) return;
    var end = new Date(iso);
    if (isNaN(end.getTime())) return;

    function tick(){
      var now = new Date();
      var diff = end - now;
      if (diff <= 0){
        el.textContent = 'Starting soon';
        return;
      }
      // compute parts
      var sec = Math.floor(diff / 1000);
      var days = Math.floor(sec / 86400); sec -= days * 86400;
      var hrs = Math.floor(sec / 3600); sec -= hrs * 3600;
      var mins = Math.floor(sec / 60); sec -= mins * 60;
      el.textContent = days + 'd ' + pad(hrs) + 'h ' + pad(mins) + 'm ' + pad(sec) + 's';
      setTimeout(tick, 1000);
    }
    function pad(n){ return (n < 10 ? '0' : '') + n; }
    tick();
  }

  // ---------- Shine effect (subtle) ----------
  function initShine(){
    if (prefersReduced) return;
    document.querySelectorAll('[data-shine]').forEach(function(card){
      card.addEventListener('pointermove', function(e){
        var rect = card.getBoundingClientRect();
        var x = e.clientX - rect.left;
        var y = e.clientY - rect.top;
        card.style.setProperty('--mx', x + 'px');
        card.style.setProperty('--my', y + 'px');
      });
      card.addEventListener('pointerleave', function(){
        card.style.removeProperty('--mx'); card.style.removeProperty('--my');
      });
    });
  }

  // ---------- Toasts ----------
  function initToasts(){
    window.DCToast = function(msg, kind){
      var root = document.getElementById('dc-toasts');
      if (!root) return alert(msg);
      var item = document.createElement('div');
      item.className = 'dc-toast';
      item.setAttribute('role','status');
      item.textContent = msg;
      if (kind) item.dataset.kind = kind;
      root.appendChild(item);
      setTimeout(function(){ item.classList.add('show'); }, 10);
      setTimeout(function(){
        item.classList.remove('show');
        setTimeout(function(){ item.remove(); }, 300);
      }, 3800);
    };
  }

  function init(){
    initReveal();
    initCountUp();
    initCountdown();
    initShine();
    initToasts();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
