/* DeltaCrown — tournament detail (tabs, countdown, lazy embeds, small motion) */
(function () {
  const d = document;
  const mqReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)');

  function $(sel, root) { return (root || d).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || d).querySelectorAll(sel)); }

  function initTabs() {
    const tabs = $all('.tabs .tab');
    const panes = $all('.pane');
    if (!tabs.length || !panes.length) return;

    const byName = Object.fromEntries(panes.map(p => [p.getAttribute('data-pane'), p]));
    const setActive = (name, push) => {
      if (!byName[name]) return;
      tabs.forEach(t => {
        const is = t.getAttribute('data-tab') === name;
        t.classList.toggle('is-active', is);
        t.setAttribute('aria-selected', is ? 'true' : 'false');
      });
      panes.forEach(p => p.classList.toggle('is-active', p.getAttribute('data-pane') === name));

      // Lazy-load iframes inside the activated pane (one-time)
      const pane = byName[name];
      if (pane) {
        $all('iframe[data-src]', pane).forEach(ifr => {
          if (!ifr.src) ifr.src = ifr.getAttribute('data-src');
        });
        // enable prev/next buttons in pdf toolbar once visible
        $all('.pdfjs-toolbar', pane).forEach(tb => {
          const prev = tb.querySelector('[data-pdf-prev]'); const next = tb.querySelector('[data-pdf-next]');
          prev && prev.removeAttribute('disabled'); next && next.removeAttribute('disabled');
        });
      }

      if (push) {
        try { history.replaceState(null, '', '#' + name); } catch (_) {}
        // Smooth scroll to tabs (helps on mobile)
        const tablist = $('.tabs');
        if (tablist && !mqReduced?.matches) {
          tablist.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
    };

    // Start from hash if present
    const initial = (location.hash || '').replace('#', '');
    if (initial && byName[initial]) setActive(initial, false);

    tabs.forEach((btn, i) => {
      btn.addEventListener('click', () => {
        const name = btn.getAttribute('data-tab');
        setActive(name, true);
        // Small pulse on the active tab (respect reduced motion)
        if (!mqReduced?.matches) {
          btn.classList.add('pulse');
          setTimeout(() => btn.classList.remove('pulse'), 220);
        }
      });
      btn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); btn.click(); }
        // Arrow navigation across tabs
        if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
          e.preventDefault();
          const dir = e.key === 'ArrowRight' ? 1 : -1;
          const next = tabs[(i + dir + tabs.length) % tabs.length];
          next.focus();
        }
      });
    });

    // If no hash matched, ensure the one with .is-active is reflected in the URL
    const current = $('.tabs .tab.is-active');
    if (current) setActive(current.getAttribute('data-tab'), true);

    // Respond to back/forward hash changes
    window.addEventListener('hashchange', () => {
      const name = (location.hash || '').replace('#', '');
      if (byName[name]) setActive(name, false);
    });
  }

  function initCountdowns() {
    const nodes = $all('[data-countdown]');
    if (!nodes.length) return;

    function pad(n) { return (n < 10 ? '0' : '') + n; }

    nodes.forEach(el => {
      const iso = el.getAttribute('data-countdown');
      let target = iso ? new Date(iso) : null;
      if (!target || isNaN(target.getTime())) return;

      const dSpan = el.querySelector('[data-d]');
      const hSpan = el.querySelector('[data-h]');
      const mSpan = el.querySelector('[data-m]');
      const sSpan = el.querySelector('[data-s]');

      const tick = () => {
        const now = new Date();
        let diff = Math.max(0, target - now);
        const d = Math.floor(diff / (24 * 3600e3)); diff -= d * 24 * 3600e3;
        const h = Math.floor(diff / 3600e3); diff -= h * 3600e3;
        const m = Math.floor(diff / 60e3); diff -= m * 60e3;
        const s = Math.floor(diff / 1e3);

        if (dSpan) dSpan.textContent = String(d);
        if (hSpan) hSpan.textContent = pad(h);
        if (mSpan) mSpan.textContent = pad(m);
        if (sSpan) sSpan.textContent = pad(s);

        if (target - now <= 0) {
          clearInterval(timer);
          el.classList.add('done');
        }
      };
      tick();
      const timer = setInterval(tick, 1000);
    });
  }

  function initShare() {
    $all('[data-share]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const url = location.href;
        const title = d.title || 'Tournament';
        try {
          if (navigator.share) await navigator.share({ title, url });
          else {
            await navigator.clipboard.writeText(url);
            btn.textContent = 'Link copied!';
            setTimeout(() => (btn.textContent = 'Share'), 1200);
          }
        } catch (_) {}
      });
    });
  }

  // micro “spark” hover for .btn-neo
  function initButtonSparks() {
    $all('.btn-neo').forEach(btn => {
      btn.addEventListener('mousemove', (e) => {
        const r = btn.getBoundingClientRect();
        const x = ((e.clientX - r.left) / r.width) * 100;
        const y = ((e.clientY - r.top) / r.height) * 100;
        btn.style.setProperty('--mx', x + '%');
        btn.style.setProperty('--my', y + '%');
      });
    });
  }

  function init() {
    initTabs();
    initCountdowns();
    initShare();
    initButtonSparks();
  }

  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', init);
  else init();
})();
