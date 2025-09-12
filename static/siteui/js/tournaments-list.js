// static/siteui/js/tournaments-list.js
// Modern, framework-free enhancements for the Tournaments hub/list pages.
// - Debounced search
// - Auto-submit on sort/filter changes
// - Shareable URLs (keeps querystring in sync)
// - PJAX-style content swap for the grid & pagination (fallbacks to full load)
// - Accessible live updates + lightweight skeletons
//
// Safe to include on any page; all selectors are defensive.

(function () {
  const W = window;
  const D = document;

  // ------- Utilities -------
  const qs = (sel, root = D) => root.querySelector(sel);
  const qsa = (sel, root = D) => Array.from(root.querySelectorAll(sel));
  const on = (el, ev, cb, opts) => el && el.addEventListener(ev, cb, opts);
  const sameOrigin = (url) => {
    try {
      const u = new URL(url, location.href);
      return u.origin === location.origin;
    } catch { return false; }
  };

  const debounce = (fn, ms = 300) => {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(null, args), ms);
    };
  };

  const serializeForm = (form) => {
    const data = new FormData(form);
    // include unchecked checkboxes as off? Not needed; server defaults handle absence.
    const params = new URLSearchParams();
    for (const [k, v] of data.entries()) {
      if (v !== null && v !== undefined && String(v).length) params.append(k, v);
    }
    return params;
  };

  const currentParams = () => new URLSearchParams(location.search);

  const mergeParams = (baseParams, incomingParams, { resetPage = true } = {}) => {
    const p = new URLSearchParams(baseParams.toString());
    // Replace & add incoming keys; remove keys set to empty
    for (const [k, v] of incomingParams.entries()) {
      if (v === "" || v == null) p.delete(k);
      else {
        p.delete(k);
        p.append(k, v);
      }
    }
    if (resetPage) p.delete("page");
    return p;
  };

  const setParam = (key, val, { resetPage = true } = {}) => {
    const p = currentParams();
    if (val == null || val === "") p.delete(key);
    else p.set(key, val);
    if (resetPage) p.delete("page");
    return p;
  };

  const buildURL = (params) => {
    const u = new URL(location.href);
    u.search = params.toString();
    return u.toString();
  };

  // ------- Live region (accessibility) -------
  const live = (() => {
    let el = qs('#live-region');
    if (!el) {
      el = D.createElement('div');
      el.id = 'live-region';
      el.setAttribute('aria-live', 'polite');
      el.setAttribute('aria-atomic', 'true');
      el.className = 'sr-only';
      el.style.position = 'absolute';
      el.style.width = '1px';
      el.style.height = '1px';
      el.style.overflow = 'hidden';
      el.style.clip = 'rect(1px, 1px, 1px, 1px)';
      el.style.clipPath = 'inset(50%)';
      el.style.whiteSpace = 'nowrap';
      D.body.appendChild(el);
    }
    return (msg) => { el.textContent = msg; };
  })();

  // ------- PJAX fetch & swap -------
  const grid = () => qs('#grid') || qs('[data-grid="tournaments"]');
  const gridContainer = () => grid() && grid().parentElement;

  const showSkeletons = (count = 6) => {
    const g = grid();
    if (!g) return;
    g.setAttribute('aria-busy', 'true');
    g.innerHTML = '';
    for (let i = 0; i < count; i++) {
      const card = D.createElement('div');
      card.className = 'rounded-2xl border border-black/5 dark:border-white/10 bg-white/60 dark:bg-slate-900/50 overflow-hidden';
      card.innerHTML = `
        <div style="height:8rem;" class="bg-slate-200/70 dark:bg-slate-800/70"></div>
        <div class="p-4">
          <div class="h-4 w-2/3 bg-slate-200 dark:bg-slate-800 rounded mb-2"></div>
          <div class="h-3 w-full bg-slate-200 dark:bg-slate-800 rounded mb-1"></div>
          <div class="h-3 w-5/6 bg-slate-200 dark:bg-slate-800 rounded mb-3"></div>
          <div class="grid grid-cols-4 gap-2">
            <div class="h-5 bg-slate-200 dark:bg-slate-800 rounded"></div>
            <div class="h-5 bg-slate-200 dark:bg-slate-800 rounded"></div>
            <div class="h-5 bg-slate-200 dark:bg-slate-800 rounded"></div>
            <div class="h-5 bg-slate-200 dark:bg-slate-800 rounded"></div>
          </div>
        </div>`;
      g.appendChild(card);
    }
  };

  const swapFromHTML = (html) => {
    const doc = new DOMParser().parseFromString(html, 'text/html');

    // Replace grid
    const newGrid = doc.querySelector('#grid, [data-grid="tournaments"]');
    const g = grid();
    if (g && newGrid) {
      g.replaceWith(newGrid);
    }

    // Replace pagination block (if any)
    // We’ll try to find the block following the grid container.
    const currentCont = gridContainer();
    const newCont = newGrid && newGrid.parentElement;
    if (currentCont && newCont) {
      // Copy any sibling after newGrid that looks like pagination (anchors with page=)
      const newPag = Array.from(newCont.children).find(
        el => el !== newGrid && el.querySelector && el.querySelector('a[href*="page="]')
      );
      const curPag = Array.from(currentCont.children).find(
        el => el !== g && el.querySelector && el.querySelector('a[href*="page="]')
      );
      if (newPag && curPag) curPag.replaceWith(newPag);
      else if (newPag && !curPag) currentCont.appendChild(newPag);
      else if (curPag && !newPag) curPag.remove();
    }
  };

  const fetchAndSwap = async (url) => {
    const g = grid();
    if (g) showSkeletons(Math.min(9, Math.max(3, g.children.length)));

    try {
      const res = await fetch(url, { headers: { 'X-Requested-With': 'fetch' } });
      if (!res.ok) throw new Error('Network error');
      const html = await res.text();
      swapFromHTML(html);
      live('Updated tournaments.');
      // re-attach pagination interception
    } catch (e) {
      // Hard navigate on failure
      location.href = url;
      return;
    } finally {
      const gg = grid();
      gg && gg.removeAttribute('aria-busy');
    }
  };

  const navigate = (params) => {
    const url = buildURL(params);
    history.pushState({ url }, '', url);
    fetchAndSwap(url);
  };

  // ------- Event wiring -------
  const searchInput = qs('input[type="search"][name="q"]');
  const sortSelect = qs('select[name="sort"]');

  // Filters form (sidebar)
  // Pick the first GET form that contains any known filter inputs
  const filtersForm = qsa('form[method="get"]').find(form =>
    form.querySelector('[name="fee_min"],[name="fee_max"],[name="prize_min"],[name="prize_max"],[name="checkin"],[name="online"]')
  );

  // Search: debounce, update URL, PJAX
  if (searchInput) {
    on(searchInput, 'input', debounce(() => {
      const p = setParam('q', searchInput.value || '');
      // Reset page on new search
      p.delete('page');
      navigate(p);
    }, 400));
    // Submit on Enter still works naturally
  }

  // Sort: change → update URL immediately
  if (sortSelect) {
    on(sortSelect, 'change', () => {
      const p = setParam('sort', sortSelect.value || 'powersort');
      p.delete('page');
      navigate(p);
    });
  }

  // Filters form: submit & change auto-apply
  if (filtersForm) {
    on(filtersForm, 'submit', (e) => {
      e.preventDefault();
      const params = mergeParams(currentParams(), serializeForm(filtersForm), { resetPage: true });
      navigate(params);
    });
    // Auto-apply on change with debounce (except text inputs which we treat like search)
    on(filtersForm, 'change', debounce((e) => {
      const target = e.target;
      if (!target || target.matches('input[type="text"], input[type="search"]')) return;
      const params = mergeParams(currentParams(), serializeForm(filtersForm), { resetPage: true });
      navigate(params);
    }, 200));

    // Intercept chip links inside filter form (Status/Game chips) for PJAX
    on(filtersForm, 'click', (e) => {
      const a = e.target.closest('a[href]');
      if (!a || !sameOrigin(a.href)) return;
      // Only intercept if link changes only querystring (same path)
      const url = new URL(a.href);
      if (url.pathname !== location.pathname) return;
      e.preventDefault();
      history.pushState({ url: url.toString() }, '', url.toString());
      fetchAndSwap(url.toString());
    });
  }

  // Pagination links: delegate click -> PJAX
  on(D, 'click', (e) => {
    const a = e.target.closest('a[href]');
    if (!a || !sameOrigin(a.href)) return;
    if (!/[\?&]page=\d+/.test(a.search)) return; // only intercept paginator links
    // Keep path the same; PJAX update
    e.preventDefault();
    const url = a.href;
    history.pushState({ url }, '', url);
    fetchAndSwap(url);
  });

  // Support back/forward
  on(W, 'popstate', (ev) => {
    const url = (ev.state && ev.state.url) || location.href;
    fetchAndSwap(url);
  });

  // Optional: mobile filters drawer (if present)
  // Expect elements with [data-filters-toggle] and [data-filters-panel]
  const drawerBtn = qs('[data-filters-toggle]');
  const drawerPanel = qs('[data-filters-panel]');
  const drawerClose = qs('[data-filters-close]');

  const openDrawer = () => drawerPanel && drawerPanel.classList.remove('hidden');
  const closeDrawer = () => drawerPanel && drawerPanel.classList.add('hidden');

  on(drawerBtn, 'click', (e) => { e.preventDefault(); openDrawer(); });
  on(drawerClose, 'click', (e) => { e.preventDefault(); closeDrawer(); });
  on(D, 'keydown', (e) => { if (e.key === 'Escape') closeDrawer(); });

  // Initial announcement
  live('Tournaments page ready. Use filters and search to refine results.');
})();
