(function () {
  // Tabs
  const tabsRoot = document.querySelector('[data-tabs]');
  if (tabsRoot) {
    const tabs = tabsRoot.querySelectorAll('button[data-tab]');
    const panels = {
      overview: document.getElementById('tab-overview'),
      participants: document.getElementById('tab-participants'),
      bracket: document.getElementById('tab-bracket'),
      standings: document.getElementById('tab-standings'),
      watch: document.getElementById('tab-watch'),
    };
    function show(id) {
      tabs.forEach(b => b.classList.toggle('bg-slate-200', b.dataset.tab === id));
      Object.entries(panels).forEach(([k, el]) => el && el.classList.toggle('hidden', k !== id));
    }
    tabs.forEach(b => b.addEventListener('click', () => show(b.dataset.tab)));
    show('overview');
  }

  // Rules drawer
  const toggle = document.querySelector('[data-rules-toggle]');
  const panel = document.getElementById('rules-panel');
  if (toggle && panel) {
    toggle.addEventListener('click', () => panel.classList.toggle('hidden'));
  }

  // Copy share link
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-copy]');
    if (!btn) return;
    const val = btn.getAttribute('data-copy');
    navigator.clipboard.writeText(val).then(() => {
      const prev = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => (btn.textContent = prev), 1200);
    });
  });

  // Countdown
  const cd = document.getElementById('countdown');
  if (cd) {
    const deadline = new Date(cd.dataset.deadline);
    function tick() {
      const now = new Date();
      let diff = Math.max(0, deadline - now);
      const s = Math.floor(diff / 1000);
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      const sec = s % 60;
      cd.textContent = `Starts in ${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
      if (diff > 0) requestAnimationFrame(() => setTimeout(tick, 250));
      else cd.textContent = 'Starting soon';
    }
    tick();
  }
})();
