(function(){
  const form = document.getElementById('t-filter');
  const grid = document.getElementById('t-grid');
  if (!form || !grid) return;

  function computeProgress(container){
    container.querySelectorAll('.progress').forEach(p => {
      const total = +p.getAttribute('data-slots-total') || 0;
      const taken = +p.getAttribute('data-slots-taken') || 0;
      const bar = p.querySelector('.progress__bar');
      if (!bar || !total) return;
      const pct = Math.max(0, Math.min(100, Math.round((taken / total) * 100)));
      bar.style.width = pct + '%';
    });
  }

  function buildQuery(){
    const fd = new FormData(form);
    const params = new URLSearchParams();
    for (const [k, v] of fd.entries()) {
      if (String(v).trim() !== '') params.set(k, String(v));
    }
    return params;
  }

  async function fetchGrid(){
    const params = buildQuery();
    params.set('partial', 'grid');
    const url = `${window.location.pathname}?${params.toString()}`;
    try {
      const res = await fetch(url, {headers: {'X-Requested-With':'fetch'}});
      if (!res.ok) return;
      const html = await res.text();
      // Replace grid
      const tmp = document.createElement('div');
      tmp.innerHTML = html;
      const newGrid = tmp.querySelector('#t-grid');
      if (newGrid) {
        grid.replaceWith(newGrid);
        // Recompute progress on new content
        computeProgress(newGrid);
        // Update reference
        const qs = buildQuery(); qs.delete('partial');
        const newUrl = `${window.location.pathname}${qs.toString() ? '?' + qs.toString() : ''}`;
        window.history.replaceState({}, '', newUrl);
      }
    } catch (_) {}
  }

  // Auto-apply on change and debounce search input
  let t;
  form.addEventListener('change', (e) => {
    if (e.target.matches('select') || e.target.matches('input[type=radio]')) {
      fetchGrid();
    }
  });
  const search = form.querySelector('input[name="q"]');
  search?.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(fetchGrid, 250);
  });

  // First paint: compute progress
  computeProgress(document);
})();
