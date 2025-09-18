(function(){
  // Debounced submit for search forms
  const forms = [document.getElementById('hub-search-form'), document.getElementById('game-search-form')].filter(Boolean);
  forms.forEach(form => {
    const input = form.querySelector('input[type="search"]');
    if (!input) return;
    let t;
    input.addEventListener('input', () => {
      clearTimeout(t);
      t = setTimeout(() => form.submit(), 400);
    });
  });

  // Filter chips on Hub
  const chipWrap = document.getElementById('dc-filter-chips');
  if (chipWrap) {
    chipWrap.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-filter]');
      if (!btn) return;
      const base = chipWrap.dataset.baseUrl || window.location.pathname;
      const [k, v] = String(btn.dataset.filter).split('=');
      const url = new URL(base, window.location.origin);
      const q = new URLSearchParams(window.location.search);
      // preserve existing q (search) if any
      if (q.get('q')) url.searchParams.set('q', q.get('q'));
      url.searchParams.set(k, v);
      window.location = url.toString();
    });
  }
})();
