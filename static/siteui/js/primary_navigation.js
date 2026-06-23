/* ============================================
   DELTACROWN PRIMARY NAVIGATION — JS Controller v3
   Single source of truth for all nav interactions.
   Loaded once via base.html at the bottom of <body>.
   ============================================ */

(function () {
  'use strict';

  /* === DOM REFS === */
  const $ = (sel) => document.querySelector(sel);
  const navbar      = $('#dc-navbar');
  const mobileHdr   = $('#dc-mobile-header');
  const bottomNav   = $('#dc-bottom-nav');
  const drawer      = $('#dc-mobile-drawer');
  const backdrop    = $('#dc-backdrop');
  const hamburger   = $('#dc-hamburger');
  const toggleBtn   = $('#dc-mobile-menu-toggle');
  const closeBtn    = $('#dc-drawer-close');
  const searchBtn   = $('#dc-search-btn');
  const searchOvr   = $('#dc-search-overlay');
  const searchInput = $('#dc-cmd-input');
  const notifBtn    = $('#dc-notif-btn');
  const notifMenu   = $('#dc-notif-menu');
  const profileBtn  = $('#dc-profile-btn');
  const profileMenu = $('#dc-profile-menu');

  let menuOpen = false;

  /* ════════════════════════════════════
     MOBILE DRAWER — Open / Close
     ════════════════════════════════════ */
  function openMenu() {
    if (menuOpen) return;
    menuOpen = true;
    drawer.style.transform = 'translateX(0)';
    drawer.style.boxShadow = '-8px 0 32px rgba(0,0,0,.5)';
    backdrop.style.display = 'block';
    requestAnimationFrame(() => {
      backdrop.style.opacity = '1';
      backdrop.style.pointerEvents = 'auto';
    });
    hamburger?.classList.add('is-open');
    toggleBtn?.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  }

  function closeMenu() {
    if (!menuOpen) return;
    menuOpen = false;
    drawer.style.transform = 'translateX(100%)';
    drawer.style.boxShadow = 'none';
    backdrop.style.opacity = '0';
    backdrop.style.pointerEvents = 'none';
    setTimeout(() => { backdrop.style.display = 'none'; }, 300);
    hamburger?.classList.remove('is-open');
    toggleBtn?.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }

  /* Bind hamburger toggle */
  toggleBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    menuOpen ? closeMenu() : openMenu();
  });

  /* Bind close button inside drawer */
  closeBtn?.addEventListener('click', closeMenu);

  /* Bind backdrop click */
  backdrop?.addEventListener('click', closeMenu);

  /* ════════════════════════════════════
     SWIPE GESTURES — Drawer
     ════════════════════════════════════ */
  let touchStartX = 0;
  let touchStartY = 0;
  let isSwiping = false;

  document.addEventListener('touchstart', (e) => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    isSwiping = false;
  }, { passive: true });

  document.addEventListener('touchmove', (e) => {
    if (!isSwiping) {
      const dx = Math.abs(e.touches[0].clientX - touchStartX);
      const dy = Math.abs(e.touches[0].clientY - touchStartY);
      if (dx > dy && dx > 10) isSwiping = true;
    }
  }, { passive: true });

  document.addEventListener('touchend', (e) => {
    if (!isSwiping) return;
    const dx = e.changedTouches[0].clientX - touchStartX;
    const threshold = 60;
    /* Swipe left from right edge → open drawer */
    if (dx < -threshold && touchStartX > window.innerWidth - 40 && !menuOpen) {
      openMenu();
    }
    /* Swipe right → close drawer */
    if (dx > threshold && menuOpen) {
      closeMenu();
    }
  }, { passive: true });

  /* ════════════════════════════════════
     SCROLL EFFECTS — Hide header + bottom nav on scroll down
     ════════════════════════════════════ */
  let lastScroll = 0;
  let scrollTicking = false;
  const scrollThreshold = 10;

  function handleScroll() {
    const currentScroll = window.scrollY;

    /* Desktop: add .scrolled class for compact look */
    if (navbar) {
      if (currentScroll > 30) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    }

    /* Mobile: hide header and bottom nav on scroll down, show on scroll up */
    if (window.innerWidth < 768) {
      const delta = currentScroll - lastScroll;
      if (delta > scrollThreshold && currentScroll > 80) {
        /* Scrolling DOWN — hide both bars so user can read */
        mobileHdr?.classList.add('nav-hidden');
        bottomNav?.classList.add('nav-hidden');
      } else if (delta < -scrollThreshold || currentScroll < 30) {
        /* Scrolling UP or near top — show both bars */
        mobileHdr?.classList.remove('nav-hidden');
        bottomNav?.classList.remove('nav-hidden');
      }
    }

    lastScroll = Math.max(0, currentScroll);
    scrollTicking = false;
  }

  window.addEventListener('scroll', () => {
    if (!scrollTicking) {
      requestAnimationFrame(handleScroll);
      scrollTicking = true;
    }
  }, { passive: true });

  /* ════════════════════════════════════
     SEARCH MODAL — Full AJAX Search
     ════════════════════════════════════ */
  const mobileSearchBtn = $('#dc-mobile-search-btn');
  const searchDefault   = $('#dc-search-default');
  const searchResults   = $('#dc-search-results');
  const searchLoading   = $('#dc-search-loading');
  const searchEmpty     = $('#dc-search-empty');
  const recentWrap      = $('#dc-search-recent-wrap');
  const recentList      = $('#dc-search-recent-list');
  const clearRecentBtn  = $('#dc-search-clear-recent');

  let searchTimer = null;
  let searchAbort = null;
  let focusIdx = -1;
  const RECENT_KEY = 'dc_recent_searches';

  function openSearch() {
    if (!searchOvr) return;
    searchOvr.classList.add('open');
    renderRecent();
    searchInput?.focus();
    document.body.style.overflow = 'hidden';
  }

  function closeSearch() {
    if (!searchOvr) return;
    searchOvr.classList.remove('open');
    if (searchInput) searchInput.value = '';
    showPanel('default');
    focusIdx = -1;
    document.body.style.overflow = '';
  }

  function showPanel(which) {
    if (searchDefault) searchDefault.style.display = which === 'default' ? '' : 'none';
    if (searchResults) searchResults.style.display = which === 'results' ? '' : 'none';
    if (searchLoading) searchLoading.style.display = which === 'loading' ? '' : 'none';
    if (searchEmpty)   searchEmpty.style.display   = which === 'empty' ? '' : 'none';
  }

  function getRecent() {
    try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]').slice(0, 5); } catch(e) { return []; }
  }
  function saveRecent(item) {
    try {
      let arr = getRecent().filter(r => r.url !== item.url);
      arr.unshift({ name: item.name, url: item.url, type: item.type });
      localStorage.setItem(RECENT_KEY, JSON.stringify(arr.slice(0, 5)));
    } catch(e) {}
  }
  function clearRecent() {
    try { localStorage.removeItem(RECENT_KEY); } catch(e) {}
    renderRecent();
  }

  function renderRecent() {
    if (!recentWrap || !recentList) return;
    const items = getRecent();
    if (!items.length) { recentWrap.style.display = 'none'; return; }
    recentWrap.style.display = '';
    const ICONS = { tournament: 'fa-trophy', team: 'fa-users', player: 'fa-user' };
    recentList.innerHTML = items.map(r =>
      '<a href="' + escHtml(r.url) + '" class="dc-search-item" data-search-nav>'
      + '<div style="width:36px;height:36px;border-radius:10px;background:#2C2C2E;display:flex;align-items:center;justify-content:center;flex:none;">'
      + '<i class="fa-solid ' + (ICONS[r.type] || 'fa-clock-rotate-left') + '" style="font-size:13px;color:#636366;"></i></div>'
      + '<div style="flex:1;min-width:0;"><div style="font-size:14px;font-weight:600;color:#F4F6FA;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escHtml(r.name) + '</div></div>'
      + '<i class="fa-solid fa-chevron-right" style="font-size:11px;color:#3A3A3C;flex:none;"></i></a>'
    ).join('');
  }

  function escHtml(s) {
    if (!s) return '';
    const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
  }

  const TYPE_LABELS = { tournament: 'Tournaments', team: 'Teams', match: 'Matches', player: 'Players' };
  const TYPE_ICONS  = { tournament: 'fa-trophy', team: 'fa-users', match: 'fa-crosshairs', player: 'fa-user' };

  function renderResults(results) {
    if (!searchResults) return;
    if (!results.length) { showPanel('empty'); return; }
    const grouped = {};
    results.forEach(r => { (grouped[r.type] = grouped[r.type] || []).push(r); });
    let html = '';
    for (const type of ['tournament', 'team', 'match', 'player']) {
      const items = grouped[type];
      if (!items) continue;
      html += '<div style="padding:12px 16px 6px;"><span style="font-size:11px;font-weight:700;color:#636366;letter-spacing:0.06em;text-transform:uppercase;">' + (TYPE_LABELS[type] || type) + '</span></div>';
      items.forEach(r => {
        const hasImg = r.icon && !r.icon.includes('default-avatar') && type !== 'player' || (type === 'player' && r.icon);
        const imgStyle = type === 'player' ? 'border-radius:50%;' : 'border-radius:8px;';
        const iconInner = hasImg
          ? '<img src="' + escHtml(r.icon) + '" alt="" style="width:100%;height:100%;object-fit:cover;' + imgStyle + '" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'"><div style="display:none;width:100%;height:100%;align-items:center;justify-content:center;"><i class="fa-solid ' + (TYPE_ICONS[type] || 'fa-circle') + '" style="font-size:13px;color:#636366;"></i></div>'
          : '<i class="fa-solid ' + (TYPE_ICONS[type] || 'fa-circle') + '" style="font-size:13px;color:#8E8E93;"></i>';
        const statusBadge = (type === 'tournament' && r.status === 'live')
          ? '<span style="font-size:9px;font-weight:700;color:#FF453A;background:rgba(255,69,58,0.14);padding:1px 6px;border-radius:999px;margin-left:6px;">LIVE</span>'
          : (type === 'tournament' && r.status === 'registration_open')
          ? '<span style="font-size:9px;font-weight:700;color:#30D158;background:rgba(48,209,88,0.14);padding:1px 6px;border-radius:999px;margin-left:6px;">OPEN</span>'
          : '';
        html += '<a href="' + escHtml(r.url) + '" class="dc-search-item" data-search-nav data-sr-type="' + escHtml(r.type) + '" data-sr-name="' + escHtml(r.name) + '">'
          + '<div style="width:36px;height:36px;border-radius:' + (type === 'player' ? '50%' : '10px') + ';background:#2C2C2E;display:flex;align-items:center;justify-content:center;flex:none;overflow:hidden;">' + iconInner + '</div>'
          + '<div style="flex:1;min-width:0;">'
          + '<div style="font-size:14px;font-weight:600;color:#F4F6FA;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:flex;align-items:center;">' + escHtml(r.name) + statusBadge + '</div>'
          + (r.meta ? '<div style="font-size:12px;color:#636366;margin-top:1px;">' + escHtml(r.meta) + '</div>' : '')
          + '</div>'
          + '<i class="fa-solid fa-chevron-right" style="font-size:11px;color:#3A3A3C;flex:none;"></i></a>';
      });
    }
    searchResults.innerHTML = html;
    showPanel('results');
  }

  async function doSearch(query) {
    if (searchAbort) { searchAbort.abort(); searchAbort = null; }
    if (query.length < 2) { showPanel('default'); renderRecent(); return; }
    showPanel('loading');
    try {
      searchAbort = new AbortController();
      const resp = await fetch('/search/suggest/?q=' + encodeURIComponent(query), {
        signal: searchAbort.signal,
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' }
      });
      const data = await resp.json();
      renderResults(data.results || []);
      focusIdx = -1;
    } catch(e) {
      if (e.name !== 'AbortError') showPanel('empty');
    }
  }

  searchInput?.addEventListener('input', () => {
    clearTimeout(searchTimer);
    const q = (searchInput.value || '').trim();
    searchTimer = setTimeout(() => doSearch(q), 280);
  });

  function getFocusableItems() {
    const panel = searchResults?.style.display !== 'none' ? searchResults : searchDefault;
    return panel ? Array.from(panel.querySelectorAll('[data-search-nav]')) : [];
  }

  function updateFocus() {
    document.querySelectorAll('.dc-search-focused').forEach(el => el.classList.remove('dc-search-focused'));
    const items = getFocusableItems();
    if (focusIdx >= 0 && focusIdx < items.length) {
      items[focusIdx].classList.add('dc-search-focused');
      items[focusIdx].scrollIntoView({ block: 'nearest' });
    }
  }

  searchBtn?.addEventListener('click', openSearch);
  mobileSearchBtn?.addEventListener('click', openSearch);

  searchOvr?.addEventListener('click', (e) => {
    if (e.target === searchOvr || e.target.closest('#dc-search-modal') === null) closeSearch();
  });

  // Save to recent when clicking a result
  searchOvr?.addEventListener('click', (e) => {
    const item = e.target.closest('[data-sr-name]');
    if (item) saveRecent({ name: item.dataset.srName, url: item.getAttribute('href'), type: item.dataset.srType });
  });

  clearRecentBtn?.addEventListener('click', clearRecent);

  /* ════════════════════════════════════
     KEYBOARD SHORTCUTS
     ════════════════════════════════════ */
  document.addEventListener('keydown', (e) => {
    const searchOpen = searchOvr?.classList.contains('open');
    if (e.key === 'Escape') {
      if (menuOpen) { closeMenu(); return; }
      if (searchOpen) { closeSearch(); return; }
      document.querySelectorAll('.dc-dropdown.show').forEach(d => d.classList.remove('show'));
      document.querySelectorAll('.dcv4-menu.dcv4-open').forEach(m => m.classList.remove('dcv4-open'));
      const chevEsc = $('#dc-profile-chevron'); if (chevEsc) chevEsc.style.transform = '';
    }
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      searchOpen ? closeSearch() : openSearch();
    }
    if (!searchOpen) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const items = getFocusableItems();
      if (items.length) { focusIdx = Math.min(focusIdx + 1, items.length - 1); updateFocus(); }
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (focusIdx > 0) { focusIdx--; updateFocus(); }
      else { focusIdx = -1; updateFocus(); searchInput?.focus(); }
    }
    if (e.key === 'Enter') {
      const items = getFocusableItems();
      if (focusIdx >= 0 && focusIdx < items.length) {
        e.preventDefault();
        const a = items[focusIdx];
        if (a.dataset.srName) saveRecent({ name: a.dataset.srName, url: a.getAttribute('href'), type: a.dataset.srType });
        window.location.href = a.getAttribute('href');
      }
    }
  });

  /* ════════════════════════════════════
     DESKTOP DROPDOWNS — Notifications (.dc-dropdown)
     ════════════════════════════════════ */
  function toggleDropdown(btn, menu, chevron) {
    if (!btn || !menu) return;
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = menu.classList.contains('show');
      document.querySelectorAll('.dc-dropdown.show').forEach(d => d.classList.remove('show'));
      closeV4Menus();
      if (!isOpen) {
        menu.classList.add('show');
        btn.setAttribute('aria-expanded', 'true');
        if (chevron) chevron.style.transform = 'rotate(180deg)';
      } else {
        btn.setAttribute('aria-expanded', 'false');
        if (chevron) chevron.style.transform = '';
      }
    });
  }

  toggleDropdown(notifBtn, notifMenu, null);

  /* ════════════════════════════════════
     v4 NAV MENUS — Tournaments / Teams (hover+click) · Profile (click)
     ════════════════════════════════════ */
  const profileChevron = $('#dc-profile-chevron');

  function closeV4Menus(except) {
    document.querySelectorAll('.dcv4-menu.dcv4-open').forEach(m => {
      if (m !== except) m.classList.remove('dcv4-open');
    });
    if (profileChevron && (!except || except.id !== 'dc-profile-menu')) {
      profileChevron.style.transform = '';
    }
  }
  function closeNotifMenu() {
    document.querySelectorAll('.dc-dropdown.show').forEach(d => d.classList.remove('show'));
    notifBtn?.setAttribute('aria-expanded', 'false');
  }

  ['dc-teams'].forEach((key) => {
    const btn = $('#' + key + '-btn');
    const menu = $('#' + key + '-menu');
    if (!btn || !menu) return;
    const wrap = btn.closest('.dcv4-menuwrap');
    let hideTimer;
    const open = () => {
      clearTimeout(hideTimer);
      closeV4Menus(menu);
      closeNotifMenu();
      menu.classList.add('dcv4-open');
      btn.setAttribute('aria-expanded', 'true');
    };
    const close = () => {
      menu.classList.remove('dcv4-open');
      btn.setAttribute('aria-expanded', 'false');
    };
    if (wrap) {
      wrap.addEventListener('mouseenter', open);
      wrap.addEventListener('mouseleave', () => { hideTimer = setTimeout(close, 160); });
    }
  });

  if (profileBtn && profileMenu) {
    profileBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = profileMenu.classList.contains('dcv4-open');
      closeV4Menus();
      closeNotifMenu();
      if (!isOpen) {
        profileMenu.classList.add('dcv4-open');
        profileBtn.setAttribute('aria-expanded', 'true');
        if (profileChevron) profileChevron.style.transform = 'rotate(180deg)';
      } else {
        profileBtn.setAttribute('aria-expanded', 'false');
        if (profileChevron) profileChevron.style.transform = '';
      }
    });
  }

  /* Close all dropdowns on outside click */
  document.addEventListener('click', () => {
    document.querySelectorAll('.dc-dropdown.show').forEach(d => d.classList.remove('show'));
    closeV4Menus();
    profileBtn?.setAttribute('aria-expanded', 'false');
    notifBtn?.setAttribute('aria-expanded', 'false');
  });

  /* ════════════════════════════════════
     PUBLIC API
     ════════════════════════════════════ */
  window.dcNav = {
    openMenu,
    closeMenu,
    isMenuOpen: () => menuOpen,
    toggleSearch: () => searchOvr?.classList.contains('open') ? closeSearch() : openSearch(),
  };

})();
