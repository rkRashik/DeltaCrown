// static/siteui/js/teams-detail.js
(function () {
  // Tabs
  const root = document.querySelector('[data-tabs]');
  if (root) {
    const tabs = root.querySelectorAll('.tab');
    const panels = document.querySelectorAll('.tab-panel');
    function show(id) {
      tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === id));
      panels.forEach(p => p.id === `tab-${id}` ? p.classList.remove('hidden') : p.classList.add('hidden'));
    }
    tabs.forEach(t => t.addEventListener('click', () => show(t.dataset.tab)));
    // Default visible
    show('roster');
  }

  // Copy link from share menu (vanilla)
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-copy]');
    if (!btn) return;
    const val = btn.getAttribute('data-copy');
    navigator.clipboard.writeText(val).then(() => {
      btn.textContent = 'Copied!';
      setTimeout(() => (btn.textContent = 'Copy link'), 1200);
    });
  });

  // Share menu toggle (no Alpine)
  const shareRoot = document.querySelector('[data-share-menu]');
  if (shareRoot) {
    const toggle = shareRoot.querySelector('[data-share-toggle]');
    const panel = shareRoot.querySelector('[data-share-panel]');
    function close() {
      panel.classList.add('hidden');
      toggle.setAttribute('aria-expanded', 'false');
    }
    function open() {
      panel.classList.remove('hidden');
      toggle.setAttribute('aria-expanded', 'true');
    }
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      if (panel.classList.contains('hidden')) open(); else close();
    });
    document.addEventListener('click', (e) => {
      if (!shareRoot.contains(e.target)) close();
    });
  }
})();
