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
  const searchClose = $('#dc-search-close');
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
     SEARCH MODAL — Cmd+K
     ════════════════════════════════════ */
  function openSearch() {
    if (!searchOvr) return;
    searchOvr.classList.remove('hidden');
    searchOvr.classList.add('open');
    requestAnimationFrame(() => searchInput?.focus());
    document.body.style.overflow = 'hidden';
  }

  function closeSearch() {
    if (!searchOvr) return;
    searchOvr.classList.remove('open');
    setTimeout(() => {
      searchOvr.classList.add('hidden');
    }, 300);
    if (searchInput) searchInput.value = '';
    document.body.style.overflow = '';
  }

  searchBtn?.addEventListener('click', openSearch);
  searchClose?.addEventListener('click', closeSearch);

  searchOvr?.addEventListener('click', (e) => {
    if (e.target === searchOvr) closeSearch();
  });

  /* ════════════════════════════════════
     KEYBOARD SHORTCUTS
     ════════════════════════════════════ */
  document.addEventListener('keydown', (e) => {
    /* ESC — close anything open */
    if (e.key === 'Escape') {
      if (menuOpen) { closeMenu(); return; }
      if (searchOvr?.classList.contains('open')) { closeSearch(); return; }
      /* Close any open dropdown */
      document.querySelectorAll('.dc-dropdown.show').forEach(d => d.classList.remove('show'));
    }
    /* Cmd/Ctrl + K — search */
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      searchOvr?.classList.contains('open') ? closeSearch() : openSearch();
    }
  });

  /* ════════════════════════════════════
     DESKTOP DROPDOWNS — Notifications & Profile
     ════════════════════════════════════ */
  function toggleDropdown(btn, menu, chevron) {
    if (!btn || !menu) return;
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = menu.classList.contains('show');
      /* Close all dropdowns first */
      document.querySelectorAll('.dc-dropdown.show').forEach(d => d.classList.remove('show'));
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
  toggleDropdown(profileBtn, profileMenu, $('#dc-profile-chevron'));

  /* Close dropdowns on outside click */
  document.addEventListener('click', () => {
    document.querySelectorAll('.dc-dropdown.show').forEach(d => d.classList.remove('show'));
    profileBtn?.setAttribute('aria-expanded', 'false');
    notifBtn?.setAttribute('aria-expanded', 'false');
    const chev = $('#dc-profile-chevron');
    if (chev) chev.style.transform = '';
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
