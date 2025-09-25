(function () {
  'use strict';

  const READY_STATES = ['interactive', 'complete'];
  const DEFAULT_SORT_ORDER = {
    powerrank: 'desc',
    recent: 'desc',
    members: 'desc',
    points: 'desc',
    az: 'asc',
    game: 'asc',
    newest: 'desc'
  };

  const supportsAsyncNav = Boolean(
    window.history && typeof window.history.pushState === 'function' &&
    typeof window.fetch === 'function' && typeof window.DOMParser === 'function'
  );

  const escapeAttr = (value) => {
    if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
      return CSS.escape(value);
    }
    return String(value).replace(/[\"\]/g, '\$&');
  };

  const state = {
    searchTimer: null,
    isFetching: false,
    listContainer: null,
    loader: null,
    form: null,
    gameSelect: null,
    sortSelect: null,
    orderInput: null,
    desktopSearch: null,
    mobileSearch: null,
    overlays: {},
    activeOverlay: null,
    activeOverlayButton: null,
    backdrop: null,
    sidebar: null,
    sidebarOverlay: null,
    sidebarToggle: null,
    sidebarClose: null,
    body: null,
    scrollLockCount: 0,
    storedOverflow: ''
  };

  function init() {
    const doc = document;
    const form = doc.getElementById('teams-search-form');

    if (!form) {
      return;
    }

    state.form = form;
    state.body = doc.body;
    state.listContainer = doc.querySelector('.teams-list-container');
    state.loader = doc.getElementById('teams-loading');
    state.gameSelect = doc.getElementById('game');
    state.sortSelect = doc.getElementById('sort');
    state.orderInput = doc.getElementById('order-input');
    state.desktopSearch = doc.getElementById('q');
    state.mobileSearch = doc.getElementById('mobile-search');
    state.backdrop = doc.getElementById('mobile-backdrop');
    state.overlays = {
      game: doc.getElementById('game-overlay'),
      sort: doc.getElementById('sort-overlay'),
      actions: doc.getElementById('actions-overlay')
    };
    state.sidebar = doc.getElementById('teams-sidebar');
    state.sidebarOverlay = doc.getElementById('sidebar-overlay');
    state.sidebarToggle = doc.getElementById('toggle-sidebar');
    state.sidebarClose = doc.getElementById('sidebar-close');

    bindFormControls(doc);
    bindOverlayControls(doc);
    bindSidebarControls(doc);
    bindGlobalKeyHandler(doc);

    if (supportsAsyncNav) {
      bindAsyncNavigation(doc);
      if (!window.history.state || typeof window.history.state.url === 'undefined') {
        window.history.replaceState({ url: window.location.href }, '', window.location.href);
      }
    }
  }

  function bindFormControls(doc) {
    if (state.sortSelect && state.orderInput && !state.orderInput.value) {
      setOrderValue(state.sortSelect.value);
    }

    if (state.desktopSearch) {
      state.desktopSearch.addEventListener('input', (event) => {
        queueSearchSubmit(event.target.value);
      });
    }

    if (state.mobileSearch) {
      state.mobileSearch.addEventListener('input', (event) => {
        queueSearchSubmit(event.target.value);
      });
    }

    const mobileSearchBtn = doc.querySelector('.mobile-search-btn');
    if (mobileSearchBtn) {
      mobileSearchBtn.addEventListener('click', (event) => {
        event.preventDefault();
        clearTimeout(state.searchTimer);
        submitForm();
      });
    }

    if (state.gameSelect) {
      state.gameSelect.addEventListener('change', () => {
        submitForm();
      });
    }

    if (state.sortSelect) {
      state.sortSelect.addEventListener('change', () => {
        setOrderValue(state.sortSelect.value);
        submitForm();
      });
    }
  }

  function bindOverlayControls(doc) {
    hideBackdrop();

    doc.querySelectorAll('.mobile-overlay-close').forEach((button) => {
      button.addEventListener('click', closeOverlay);
    });

    if (state.backdrop) {
      state.backdrop.addEventListener('click', closeOverlay);
    }

    doc.querySelectorAll('.mobile-filter-btn[data-filter]').forEach((button) => {
      button.addEventListener('click', () => {
        const key = button.getAttribute('data-filter');
        openOverlay(state.overlays[key], button);
      });
    });

    if (state.overlays.game) {
      state.overlays.game.querySelectorAll('.mobile-filter-option').forEach((option) => {
        option.addEventListener('click', () => {
          const value = option.getAttribute('data-value') || '';
          updateOverlayActiveState(state.overlays.game, value);
          submitSelectValue(state.gameSelect, value);
          closeOverlay();
        });
      });
      updateOverlayActiveState(state.overlays.game, state.gameSelect?.value || '');
    }

    if (state.overlays.sort) {
      state.overlays.sort.querySelectorAll('.mobile-filter-option').forEach((option) => {
        option.addEventListener('click', () => {
          const value = option.getAttribute('data-value') || '';
          updateOverlayActiveState(state.overlays.sort, value);
          submitSelectValue(state.sortSelect, value);
          closeOverlay();
        });
      });
      updateOverlayActiveState(state.overlays.sort, state.sortSelect?.value || '');
    }
  }

  function bindSidebarControls() {
    if (state.sidebarToggle) {
      state.sidebarToggle.addEventListener('click', () => {
        if (!state.sidebar) {
          return;
        }
        if (state.sidebar.classList.contains('active')) {
          closeSidebar();
        } else {
          openSidebar();
        }
      });
    }

    if (state.sidebarClose) {
      state.sidebarClose.addEventListener('click', closeSidebar);
    }

    if (state.sidebarOverlay) {
      state.sidebarOverlay.addEventListener('click', closeSidebar);
    }
  }

  function bindGlobalKeyHandler(doc) {
    doc.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape') {
        return;
      }
      if (state.activeOverlay) {
        closeOverlay();
        return;
      }
      if (state.sidebar && state.sidebar.classList.contains('active')) {
        closeSidebar();
      }
    });
  }

  function bindAsyncNavigation(doc) {
    state.form.addEventListener('submit', (event) => {
      event.preventDefault();
      handleNavigate(buildUrlFromForm());
    });

    doc.addEventListener('click', (event) => {
      const anchor = event.target.closest('a[data-async="true"]');
      if (!anchor) {
        return;
      }
      const href = anchor.getAttribute('href');
      if (!href || anchor.getAttribute('target') === '_blank' || href.startsWith('#') || href.startsWith('javascript:')) {
        return;
      }
      event.preventDefault();
      const absoluteUrl = new URL(href, window.location.origin).toString();
      handleNavigate(absoluteUrl);
    });

    window.addEventListener('popstate', (event) => {
      const url = event.state?.url || window.location.href;
      handleNavigate(url, { push: false, scroll: false });
    });
  }

  function queueSearchSubmit(value) {
    syncSearchInputs(value);
    clearTimeout(state.searchTimer);
    state.searchTimer = window.setTimeout(() => submitForm(), 400);
  }

  function syncSearchInputs(value) {
    if (state.desktopSearch && state.desktopSearch.value !== value) {
      state.desktopSearch.value = value;
    }
    if (state.mobileSearch && state.mobileSearch.value !== value) {
      state.mobileSearch.value = value;
    }
  }

  function submitForm() {
    if (supportsAsyncNav) {
      handleNavigate(buildUrlFromForm());
      return;
    }

    if (typeof state.form.requestSubmit === 'function') {
      state.form.requestSubmit();
    } else {
      state.form.submit();
    }
  }

  function buildUrlFromForm() {
    if (!state.form) {
      return window.location.pathname;
    }

    const action = state.form.getAttribute('action') || window.location.pathname;
    const params = new URLSearchParams();
    const formData = new FormData(state.form);

    for (const [key, rawValue] of formData.entries()) {
      if (rawValue === null || rawValue === undefined) {
        continue;
      }
      const value = typeof rawValue === 'string' ? rawValue.trim() : rawValue;
      if (value === '') {
        continue;
      }
      params.append(key, value);
    }

    const queryString = params.toString();
    return queryString ? `${action}?${queryString}` : action;
  }

  function submitSelectValue(select, value) {
    if (!select) {
      return;
    }
    if (select.value !== value) {
      select.value = value;
    }
    if (select === state.sortSelect) {
      setOrderValue(value);
    }
    submitForm();
  }

  function setOrderValue(sortValue) {
    if (!state.orderInput) {
      return;
    }
    const defaultOrder = DEFAULT_SORT_ORDER[sortValue];
    state.orderInput.value = defaultOrder || 'asc';
  }

  function lockScroll() {
    if (!state.body) {
      return;
    }
    if (state.scrollLockCount === 0) {
      state.storedOverflow = state.body.style.overflow;
      state.body.style.overflow = 'hidden';
    }
    state.scrollLockCount += 1;
  }

  function releaseScroll() {
    if (!state.body || state.scrollLockCount === 0) {
      return;
    }
    state.scrollLockCount -= 1;
    if (state.scrollLockCount === 0) {
      state.body.style.overflow = state.storedOverflow;
    }
  }

  function showBackdrop() {
    if (!state.backdrop) {
      return;
    }
    state.backdrop.style.display = 'block';
    state.backdrop.classList.add('active');
  }

  function hideBackdrop() {
    if (!state.backdrop) {
      return;
    }
    state.backdrop.classList.remove('active');
    state.backdrop.style.display = 'none';
  }

  function openOverlay(overlay, button) {
    if (!overlay) {
      return;
    }
    if (state.activeOverlay === overlay) {
      closeOverlay();
      return;
    }
    closeOverlay();
    state.activeOverlay = overlay;
    state.activeOverlayButton = button || null;
    overlay.classList.add('active');
    if (state.activeOverlayButton) {
      state.activeOverlayButton.classList.add('active');
    }
    overlay.addEventListener('click', handleOverlayBackdropClick);
    document.addEventListener('keydown', handleOverlayEscape);
    showBackdrop();
    lockScroll();
  }

  function closeOverlay() {
    if (!state.activeOverlay) {
      return;
    }
    state.activeOverlay.classList.remove('active');
    state.activeOverlay.removeEventListener('click', handleOverlayBackdropClick);
    state.activeOverlay = null;
    if (state.activeOverlayButton) {
      state.activeOverlayButton.classList.remove('active');
      state.activeOverlayButton = null;
    }
    hideBackdrop();
    document.removeEventListener('keydown', handleOverlayEscape);
    releaseScroll();
  }

  function handleOverlayBackdropClick(event) {
    if (event.target === state.activeOverlay) {
      closeOverlay();
    }
  }

  function handleOverlayEscape(event) {
    if (event.key === 'Escape') {
      closeOverlay();
    }
  }

  function openSidebar() {
    if (!state.sidebar) {
      return;
    }
    state.sidebar.classList.add('active');
    state.sidebarOverlay?.classList.add('active');
    lockScroll();
  }

  function closeSidebar() {
    if (!state.sidebar) {
      return;
    }
    state.sidebar.classList.remove('active');
    state.sidebarOverlay?.classList.remove('active');
    releaseScroll();
  }

  function updateOverlayActiveState(overlay, value) {
    if (!overlay) {
      return;
    }
    overlay.querySelectorAll('.mobile-filter-option').forEach((option) => {
      const optionValue = option.getAttribute('data-value') || '';
      option.classList.toggle('active', optionValue === value);
    });
  }

  function handleNavigate(url, options = {}) {
    if (!supportsAsyncNav || !url) {
      window.location.href = url;
      return;
    }

    if (state.isFetching) {
      return;
    }

    state.isFetching = true;
    clearTimeout(state.searchTimer);
    closeOverlay();
    closeSidebar();
    showLoading();

    fetch(url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }
        return response.text();
      })
      .then((html) => {
        if (!applyPageUpdate(html)) {
          window.location.href = url;
          return;
        }

        if (options.push !== false) {
          window.history.pushState({ url }, '', url);
        } else if (options.replace) {
          window.history.replaceState({ url }, '', url);
        }

        if (options.scroll !== false && state.listContainer) {
          const topOffset = Math.max(state.listContainer.offsetTop - 80, 0);
          window.scrollTo({ top: topOffset, behavior: 'smooth' });
        }
      })
      .catch((error) => {
        console.error('[teams-list] navigation failed', error);
        window.location.href = url;
      })
      .finally(() => {
        state.isFetching = false;
        hideLoading();
      });
  }

  function applyPageUpdate(html) {
    const parser = new DOMParser();
    const nextDoc = parser.parseFromString(html, 'text/html');
    const newList = nextDoc.querySelector('.teams-list-container');

    if (!newList || !state.listContainer) {
      return false;
    }

    state.listContainer.innerHTML = newList.innerHTML;
    state.listContainer = document.querySelector('.teams-list-container');

    const nextOrderInput = nextDoc.getElementById('order-input');
    if (state.orderInput && nextOrderInput) {
      state.orderInput.value = nextOrderInput.value || '';
    }

    const nextSortSelect = nextDoc.getElementById('sort');
    if (state.sortSelect && nextSortSelect) {
      state.sortSelect.value = nextSortSelect.value;
      Array.from(state.sortSelect.options).forEach((option) => {
        option.selected = option.value === nextSortSelect.value;
      });
      setOrderValue(nextSortSelect.value);
    }

    const nextGameSelect = nextDoc.getElementById('game');
    if (state.gameSelect && nextGameSelect) {
      state.gameSelect.value = nextGameSelect.value;
      Array.from(state.gameSelect.options).forEach((option) => {
        option.selected = option.value === nextGameSelect.value;
      });
    }

    const nextQuery = nextDoc.getElementById('q');
    const queryValue = nextQuery ? nextQuery.value : '';
    if (state.desktopSearch) {
      state.desktopSearch.value = queryValue || '';
    }
    if (state.mobileSearch) {
      state.mobileSearch.value = queryValue || '';
    }

    updateSidebarLinks(nextDoc);
    updateOverlayActiveState(state.overlays.game, state.gameSelect?.value || '');
    updateOverlayActiveState(state.overlays.sort, state.sortSelect?.value || '');

    const newTitle = nextDoc.querySelector('title');
    if (newTitle) {
      document.title = newTitle.textContent.trim();
    }

    return true;
  }

  function updateSidebarLinks(nextDoc) {
    if (!state.sidebar) {
      return;
    }

    const currentLinks = state.sidebar.querySelectorAll('.filter-option[data-game]');
    if (!currentLinks.length) {
      return;
    }

    const nextSidebar = nextDoc.getElementById('teams-sidebar');
    if (!nextSidebar) {
      return;
    }

    currentLinks.forEach((link) => {
      const gameCode = link.getAttribute('data-game') || '';
      const replacement = nextSidebar.querySelector(`.filter-option[data-game="${escapeAttr(gameCode)}"]`);
      if (replacement) {
        link.className = replacement.className;
        link.setAttribute('href', replacement.getAttribute('href'));
        link.setAttribute('data-async', replacement.getAttribute('data-async') || 'true');
      }
    });

    const currentStats = state.sidebar.querySelector('.sidebar-stats');
    const nextStats = nextSidebar.querySelector('.sidebar-stats');
    if (currentStats && nextStats) {
      currentStats.innerHTML = nextStats.innerHTML;
    }
  }

  function showLoading() {
    state.loader?.classList.add('active');
    state.listContainer?.classList.add('is-loading');
  }

  function hideLoading() {
    state.loader?.classList.remove('active');
    state.listContainer?.classList.remove('is-loading');
  }

  if (READY_STATES.includes(document.readyState)) {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  }
})();
