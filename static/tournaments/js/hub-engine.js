/**
 * ═══════════════════════════════════════════════════════════
 * THE HUB — SPA State Engine
 * DeltaCrown Sprint 12
 *
 * Responsibilities:
 *  • Tab switching (zero full-page reloads)
 *  • API polling (state / announcements every N seconds)
 *  • Countdown timer (phase events)
 *  • Check-in action (POST)
 *  • Mobile sidebar toggle
 *  • Dynamic DOM updates from poll data
 * ═══════════════════════════════════════════════════════════
 */

const HubEngine = (() => {
  // ── Config ──────────────────────────────────────────────
  const POLL_STATE_INTERVAL   = 20_000;   // 20s
  const POLL_ANN_INTERVAL     = 45_000;   // 45s
  const COUNTDOWN_TICK        = 1_000;    // 1s
  const HUB_TABS = new Set([
    'overview', 'matches', 'squad', 'schedule',
    'bracket', 'standings', 'prizes', 'resources',
    'participants', 'rulebook', 'support',
  ]);
  const TAB_ALIASES = {
    disputes: 'support',
    'support-disputes': 'support',
    'hub-tab-support': 'support',
  };
  const LOCKED_TABS_WHEN_UNVERIFIED = new Set([
    'matches',
    'squad',
    'schedule',
    'bracket',
    'standings',
    'prizes',
    'participants',
  ]);

  // ── State ───────────────────────────────────────────────
  let _shell       = null;
  let _currentTab  = null;
  let _pollStateId = null;
  let _pollAnnId   = null;
  let _countdownId = null;
  let _csrfToken   = '';

  // Lazy-load caches (fetched once per session)
  let _prizesCache       = null;
  let _resourcesCache    = null;
  let _bracketCache      = null;
  let _standingsCache    = null;
  let _matchesCache      = null;
  let _participantsCache = null;
  let _participantsAll   = [];  // for search filtering
  let _supportTicketsLoaded = false;
  let _participantsPage = 1;
  let _participantsHasMore = false;
  const _participantsPageSize = 40;
  let _supportTicketsPage = 1;
  let _supportTicketsHasMore = false;
  const _supportTicketsPageSize = 20;
  let _openModalId = null;
  let _modalReturnFocusEl = null;
  let _mobileSidebarReturnFocusEl = null;

  // S27: WebSocket connection for real-time sync
  let _ws = null;
  let _wsReconnectTimer = null;
  let _wsReconnectAttempts = 0;
  let _wsPingId = null;
  let _resizeTimer = null;
  let _onKeyDown = null;
  let _onWindowResize = null;
  let _onHashChange = null;
  let _onPopState = null;
  let _onVisibilityChange = null;
  const WS_RECONNECT_MAX = 3;
  const WS_RECONNECT_BASE = 3000;  // 3s, doubles each retry

  // ── Init ────────────────────────────────────────────────
  function init() {
    _shell = document.getElementById('hub-shell');
    if (!_shell) return;

    _csrfToken = _getCookie('csrftoken');

    // Start countdown
    _startCountdown();

    // Start polling (auto-pauses in background tab)
    _startPolling();

    // S27: Connect WebSocket for real-time updates
    _connectWebSocket();

    // Keyboard: Escape closes mobile sidebar + modals
    _onKeyDown = (e) => {
      if (e.key === 'Escape') {
        closeMobileSidebar();
        closeContactModal();
        closeStatusModal();
        dismissGuide();
      }
    };
    document.addEventListener('keydown', _onKeyDown);

    // Retry actions for async error states.
    document.removeEventListener('click', _handleRetryButtonClick);
    document.addEventListener('click', _handleRetryButtonClick);

    // First-visit welcome guide
    setTimeout(_checkWelcomeGuide, 500);

    // Redraw bracket connector lines on window resize
    _onWindowResize = () => {
      clearTimeout(_resizeTimer);
      _resizeTimer = setTimeout(_redrawBracketLines, 150);
    };
    window.addEventListener('resize', _onWindowResize);

    // Resolve and hydrate initial tab state from URL without causing extra history entries.
    const initialTab = _resolveInitialTab() || 'overview';
    switchTab(initialTab, {
      historyMode: 'replace',
      smoothScroll: false,
      announceLock: false,
    });

    _onHashChange = () => {
      const hashTab = _resolveInitialTab();
      if (hashTab && hashTab !== _currentTab) {
        switchTab(hashTab, {
          syncUrl: false,
          smoothScroll: false,
          announceLock: false,
        });
      }
    };
    window.addEventListener('hashchange', _onHashChange);

    _onPopState = () => {
      const tab = _resolveInitialTab() || 'overview';
      if (tab !== _currentTab) {
        switchTab(tab, {
          syncUrl: false,
          smoothScroll: false,
          announceLock: false,
        });
      }
    };
    window.addEventListener('popstate', _onPopState);

    _onVisibilityChange = () => {
      if (document.hidden) {
        _stopPolling();
        return;
      }
      _startPolling();
      _pollState();
      _pollAnnouncements();
    };
    document.addEventListener('visibilitychange', _onVisibilityChange);

    // Keep WS alive with periodic pings.
    if (_wsPingId) clearInterval(_wsPingId);
    _wsPingId = setInterval(() => {
      if (_ws && _ws.readyState === WebSocket.OPEN) {
        _ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  }

  function _resolveInitialTab() {
    const hashTab = (window.location.hash || '').replace('#', '').trim().toLowerCase();
    const normalizedHash = _normalizeTab(hashTab);
    if (normalizedHash) return normalizedHash;

    try {
      const params = new URLSearchParams(window.location.search || '');
      const queryTab = (params.get('tab') || '').trim().toLowerCase();
      const normalizedQuery = _normalizeTab(queryTab);
      if (normalizedQuery) return normalizedQuery;
    } catch (e) {
      // ignore malformed query strings
    }

    return null;
  }

  function _normalizeTab(rawTab) {
    if (!rawTab) return null;
    if (HUB_TABS.has(rawTab)) return rawTab;
    return TAB_ALIASES[rawTab] || null;
  }

  function _syncUrlForTab(tabId, mode = 'push') {
    if (!window?.history || !window?.location) return;

    const url = new URL(window.location.href);
    const currentHash = (url.hash || '').replace('#', '').toLowerCase();
    if (currentHash === tabId) {
      return;
    }

    // Canonical URL source is hash only; keep query clean.
    url.searchParams.delete('tab');
    url.hash = tabId;

    const state = { ...(window.history.state || {}), hubTab: tabId };
    if (mode === 'replace') {
      window.history.replaceState(state, '', url.toString());
    } else {
      window.history.pushState(state, '', url.toString());
    }
  }

  // ──────────────────────────────────────────────────────────
  // Tab Switching
  // ──────────────────────────────────────────────────────────
  function switchTab(tabId, options = {}) {
    const {
      syncUrl = true,
      historyMode = 'push',
      smoothScroll = true,
      announceLock = true,
    } = options;

    const normalizedTab = _normalizeTab(tabId) || 'overview';

    const shouldLockTab = _isTabLocked(normalizedTab);

    if (normalizedTab === _currentTab) {
      _applyTabLockState(normalizedTab, { announce: false });
      if (syncUrl) _syncUrlForTab(normalizedTab, historyMode);
      return;
    }

    const target = document.getElementById('hub-tab-' + normalizedTab);
    if (!target) return;

    // Hide all tab contents
    document.querySelectorAll('.hub-tab-content').forEach(el => {
      el.classList.remove('active');
    });

    // Show target
    target.classList.add('active');

    // Update sidebar nav buttons (both desktop + mobile copies)
    document.querySelectorAll('.hub-nav-btn').forEach(btn => {
      const btnTab = btn.getAttribute('data-hub-tab');
      if (btnTab === normalizedTab) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    _currentTab = normalizedTab;
    _applyTabLockState(normalizedTab, {
      announce: shouldLockTab && announceLock,
    });

    if (syncUrl) {
      _syncUrlForTab(normalizedTab, historyMode);
    }

    // Scroll content to top
    const viewport = document.getElementById('hub-viewport');
    if (viewport) {
      const prefersReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      viewport.scrollTo({ top: 0, behavior: (smoothScroll && !prefersReducedMotion) ? 'smooth' : 'auto' });
    }

    // Close mobile sidebar if open
    closeMobileSidebar();

    // Async data fetch for lazy tabs
    if (normalizedTab === 'prizes' && !_prizesCache) {
      _fetchPrizes();
    }
    if (normalizedTab === 'resources' && !_resourcesCache) {
      _fetchResources();
    }
    if (normalizedTab === 'bracket' && !_bracketCache) {
      _fetchBracket();
    }
    if (normalizedTab === 'standings' && !_standingsCache) {
      _fetchStandings();
    }
    if (normalizedTab === 'matches' && !_matchesCache) {
      _fetchMatches();
    }
    if (normalizedTab === 'participants' && !_participantsCache) {
      _fetchParticipants({ reset: true });
    }
    if (normalizedTab === 'support') {
      _initSupportForm();
      if (!_supportTicketsLoaded) {
        _fetchSupportTickets({ reset: true });
      }
    }
    // S27: Lazy-load match schedule for schedule tab
    if (normalizedTab === 'schedule') {
      _fetchScheduleMatches();
    }

    // Re-init lucide icons for dynamic content
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ──────────────────────────────────────────────────────────
  // Mobile Sidebar
  // ──────────────────────────────────────────────────────────
  function openMobileSidebar() {
    const overlay = document.getElementById('hub-mobile-overlay');
    const sidebar = document.getElementById('hub-mobile-sidebar');
    _mobileSidebarReturnFocusEl = document.activeElement;
    if (overlay) overlay.classList.add('open');
    if (sidebar) sidebar.classList.add('open');
    if (sidebar) sidebar.setAttribute('aria-hidden', 'false');
    document.body.classList.add('hub-mobile-nav-open');

    if (sidebar) {
      _attachModalFocusTrap(sidebar);
      const focusables = _getFocusableElements(sidebar);
      if (focusables.length) {
        focusables[0].focus();
      }
    }
  }

  function _getFocusableElements(container) {
    if (!container) return [];
    return Array.from(container.querySelectorAll(
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter(el => {
      if (!el) return false;
      if (el.offsetParent === null && el !== document.activeElement) return false;
      return !el.hasAttribute('hidden');
    });
  }

  function _attachModalFocusTrap(modal) {
    if (!modal || modal._focusTrapBound) return;

    const handler = (e) => {
      if (e.key !== 'Tab') return;

      const focusables = _getFocusableElements(modal);
      if (!focusables.length) {
        e.preventDefault();
        modal.focus();
        return;
      }

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    modal._focusTrapHandler = handler;
    modal.addEventListener('keydown', handler);
    modal._focusTrapBound = true;
  }

  function _detachModalFocusTrap(modal) {
    if (!modal || !modal._focusTrapBound || !modal._focusTrapHandler) return;
    modal.removeEventListener('keydown', modal._focusTrapHandler);
    delete modal._focusTrapHandler;
    modal._focusTrapBound = false;
  }

  function _openModal(modalId, labelId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    if (_openModalId && _openModalId !== modalId) {
      _closeModal(_openModalId, false);
    }

    _openModalId = modalId;
    _modalReturnFocusEl = document.activeElement;

    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    if (labelId) {
      modal.setAttribute('aria-labelledby', labelId);
    } else {
      modal.removeAttribute('aria-labelledby');
    }
    modal.classList.remove('hidden');

    _attachModalFocusTrap(modal);

    const focusables = _getFocusableElements(modal);
    if (focusables.length) {
      focusables[0].focus();
    } else {
      modal.setAttribute('tabindex', '-1');
      modal.focus();
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function _closeModal(modalId, restoreFocus = true) {
    const modal = document.getElementById(modalId);
    if (!modal) return;

    modal.classList.add('hidden');
    _detachModalFocusTrap(modal);

    if (_openModalId === modalId) {
      _openModalId = null;
    }

    if (restoreFocus && _modalReturnFocusEl && document.contains(_modalReturnFocusEl)) {
      _modalReturnFocusEl.focus();
    }
    if (restoreFocus) {
      _modalReturnFocusEl = null;
    }
  }

  function closeMobileSidebar() {
    const overlay = document.getElementById('hub-mobile-overlay');
    const sidebar = document.getElementById('hub-mobile-sidebar');
    if (overlay) overlay.classList.remove('open');
    if (sidebar) sidebar.classList.remove('open');
    if (sidebar) sidebar.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('hub-mobile-nav-open');

    if (sidebar) _detachModalFocusTrap(sidebar);
    if (_mobileSidebarReturnFocusEl && document.contains(_mobileSidebarReturnFocusEl)) {
      _mobileSidebarReturnFocusEl.focus();
    }
    _mobileSidebarReturnFocusEl = null;
  }

  // ──────────────────────────────────────────────────────────
  // Countdown Timer
  // ──────────────────────────────────────────────────────────
  function _startCountdown() {
    const el = document.getElementById('hub-countdown');
    if (!el) return;

    const targetISO = el.getAttribute('data-target');
    if (!targetISO) return;

    const targetDate = new Date(targetISO);

    function tick() {
      const now  = new Date();
      const diff = targetDate - now;

      if (diff <= 0) {
        _setCountdown('00', '00', '00');
        clearInterval(_countdownId);
        // Trigger state refresh
        _pollState();
        return;
      }

      const totalSec = Math.floor(diff / 1000);
      const h = String(Math.floor(totalSec / 3600)).padStart(2, '0');
      const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0');
      const s = String(totalSec % 60).padStart(2, '0');
      _setCountdown(h, m, s);
    }

    tick(); // immediate first tick
    _countdownId = setInterval(tick, COUNTDOWN_TICK);
  }

  function _setCountdown(h, m, s) {
    const hEl = document.getElementById('hub-cd-hours');
    const mEl = document.getElementById('hub-cd-minutes');
    const sEl = document.getElementById('hub-cd-seconds');
    if (hEl) hEl.textContent = h;
    if (mEl) mEl.textContent = m;
    if (sEl) sEl.textContent = s;
  }

  // ──────────────────────────────────────────────────────────
  // Check-In Action
  // ──────────────────────────────────────────────────────────
  async function performCheckIn() {
    if (_isCriticalLocked()) {
      _showLockToast();
      return;
    }

    const url = _shell?.dataset.apiCheckin;
    if (!url) return;

    // Disable buttons
    document.querySelectorAll('#hub-checkin-btn, #hub-checkin-btn-lobby').forEach(btn => {
      btn.disabled = true;
      btn.textContent = 'Checking in...';
    });

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': _csrfToken,
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
      });

      const data = await resp.json();

      if (data.success) {
        // Update buttons to "done" state
        document.querySelectorAll('#hub-checkin-btn, #hub-checkin-btn-lobby').forEach(btn => {
          btn.className = 'hub-checkin-btn done clip-slant w-full lg:w-auto flex items-center justify-center gap-3';
          btn.innerHTML = '<i data-lucide="check" class="w-5 h-5"></i> Checked In';
          btn.disabled = true;
          btn.onclick = null;
        });

        // Update shell data attribute
        if (_shell) _shell.dataset.isCheckedIn = 'true';

        // Show toast if available
        if (window.showToast) {
          window.showToast({ type: 'success', message: 'Successfully checked in!' });
        }

        // Re-init icons
        if (typeof lucide !== 'undefined') lucide.createIcons();

        // Refresh state
        _pollState();
      } else {
        const errMsg = data.error || 'Check-in failed. Please try again.';
        if (window.showToast) {
          window.showToast({ type: 'error', message: errMsg });
        }
        // Re-enable buttons
        document.querySelectorAll('#hub-checkin-btn, #hub-checkin-btn-lobby').forEach(btn => {
          btn.disabled = false;
          btn.innerHTML = '<i data-lucide="check-circle" class="w-5 h-5"></i> Check In Now';
        });
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    } catch (err) {
      console.error('[HubEngine] Check-in error:', err);
      if (window.showToast) {
        window.showToast({ type: 'error', message: 'Network error. Please try again.' });
      }
      document.querySelectorAll('#hub-checkin-btn, #hub-checkin-btn-lobby').forEach(btn => {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="check-circle" class="w-5 h-5"></i> Check In Now';
      });
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }
  }

  // ──────────────────────────────────────────────────────────
  // State Polling
  // ──────────────────────────────────────────────────────────
  function _startPolling() {
    if (!_pollStateId) {
      _pollStateId = setInterval(_pollState, POLL_STATE_INTERVAL);
    }
    if (!_pollAnnId) {
      _pollAnnId = setInterval(_pollAnnouncements, POLL_ANN_INTERVAL);
    }
  }

  function _stopPolling() {
    if (_pollStateId) {
      clearInterval(_pollStateId);
      _pollStateId = null;
    }
    if (_pollAnnId) {
      clearInterval(_pollAnnId);
      _pollAnnId = null;
    }
  }

  async function _pollState() {
    const url = _shell?.dataset.apiState;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) return;
      const data = await resp.json();

      // Update reg count
      const regEl = document.getElementById('hub-reg-count');
      if (regEl && data.reg_count !== undefined) {
        regEl.textContent = data.reg_count;
      }

      // Update user status label
      const statusEl = document.getElementById('hub-status-label');
      if (statusEl && data.user_status) {
        statusEl.textContent = data.user_status;
      }

      // Update check-in state if it changed
      if (data.check_in) {
        const shellChecked = _shell?.dataset.isCheckedIn === 'true';
        if (data.check_in.is_checked_in && !shellChecked) {
          _shell.dataset.isCheckedIn = 'true';
          // Could trigger UI update here
        }
      }

      // Update countdown target if phase changed
      if (data.phase_event && data.phase_event.target) {
        const cdEl = document.getElementById('hub-countdown');
        if (cdEl) {
          const current = cdEl.getAttribute('data-target');
          if (current !== data.phase_event.target) {
            cdEl.setAttribute('data-target', data.phase_event.target);
            // Restart countdown
            if (_countdownId) clearInterval(_countdownId);
            _startCountdown();
          }
        }
      }

    } catch (err) {
      console.warn('[HubEngine] State poll failed:', err.message);
    }
  }

  // ──────────────────────────────────────────────────────────
  // Announcements Polling
  // ──────────────────────────────────────────────────────────
  async function _pollAnnouncements() {
    const url = _shell?.dataset.apiAnnouncements;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) return;
      const data = await resp.json();

      if (!data.announcements || !data.announcements.length) return;

      const feed = document.getElementById('hub-announcements-feed');
      if (!feed) return;

      // Rebuild feed
      const html = data.announcements.map((ann, i) => {
        const dotClass = ann.type === 'urgent' ? 'ann-dot-urgent'
                       : ann.type === 'warning' ? 'ann-dot-warning'
                       : ann.type === 'success' ? 'ann-dot-success'
                       : 'ann-dot-info';

        const typeClass = ann.type === 'urgent' ? 'bg-[#FF2A55]/20 text-[#FF2A55]'
                        : ann.type === 'warning' ? 'bg-[#FFB800]/20 text-[#FFB800]'
                        : ann.type === 'success' ? 'bg-[#00FF66]/20 text-[#00FF66]'
                        : 'bg-white/10 text-gray-300';

        const isLast = i === data.announcements.length - 1;

        return `
          <div class="relative pl-6 border-l border-white/5 ${isLast ? '' : 'pb-6'}">
            <div class="absolute left-0 top-1.5 w-2 h-2 rounded-full -ml-[5px] ${dotClass}"></div>
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              ${ann.is_pinned ? '<span class="px-1.5 py-0.5 rounded bg-[#FFB800]/20 text-[#FFB800] text-[8px] font-black uppercase">Pinned</span>' : ''}
              <span class="px-1.5 py-0.5 rounded ${typeClass} text-[8px] font-black uppercase">${_esc(ann.type || 'Info')}</span>
              <span class="text-[10px] text-gray-500" style="font-family:'Space Grotesk',monospace;">${_esc(ann.time_ago)}</span>
            </div>
            ${ann.title ? `<p class="font-bold text-white text-sm mb-1">${_esc(ann.title)}</p>` : ''}
            <p class="text-xs text-gray-400 leading-relaxed">${_esc(ann.message)}</p>
          </div>`;
      }).join('');

      feed.innerHTML = html;

      // Update count
      const countEl = document.getElementById('hub-ann-count');
      if (countEl) {
        const n = data.announcements.length;
        countEl.textContent = `${n} update${n !== 1 ? 's' : ''}`;
      }

    } catch (err) {
      console.warn('[HubEngine] Announcements poll failed:', err.message);
    }
  }

  // ──────────────────────────────────────────────────────────
  // Squad Management — Roster Slot Swaps
  // ──────────────────────────────────────────────────────────
  async function swapToSub(membershipId) {
    await _swapSlot(membershipId, 'SUBSTITUTE');
  }

  async function swapToStarter(membershipId) {
    await _swapSlot(membershipId, 'STARTER');
  }

  async function _swapSlot(membershipId, newSlot) {
    if (_isCriticalLocked()) {
      _showLockToast();
      return;
    }

    const url = _shell?.dataset.apiSquad;
    if (!url) return;

    // Find and disable the button
    const card = document.querySelector(`[data-member-id="${membershipId}"]`);
    const btn = card?.querySelector('.squad-swap-btn');
    if (btn) {
      btn.classList.add('loading');
      btn.disabled = true;
    }

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': _csrfToken,
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          membership_id: membershipId,
          new_slot: newSlot,
        }),
      });

      const data = await resp.json();

      if (data.success) {
        _showSquadToast(`${data.display_name} moved to ${newSlot.toLowerCase()}`);
        _refreshSquadTab();
      } else {
        _showSquadToast(data.error || 'Swap failed', true);
        if (btn) {
          btn.classList.remove('loading');
          btn.disabled = false;
        }
      }
    } catch (err) {
      console.error('[HubEngine] Squad swap error:', err);
      _showSquadToast('Network error. Please try again.', true);
      if (btn) {
        btn.classList.remove('loading');
        btn.disabled = false;
      }
    }
  }

  async function _refreshSquadTab() {
    const squadTab = document.getElementById('hub-tab-squad');
    if (!squadTab) return;
    try {
      const url = new URL(window.location.href);
      url.hash = 'squad';
      const resp = await fetch(url.toString(), { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const html = await resp.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const freshSquadTab = doc.getElementById('hub-tab-squad');
      if (!freshSquadTab) return;
      squadTab.innerHTML = freshSquadTab.innerHTML;
      if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (err) {
      console.warn('[HubEngine] Squad tab refresh failed:', err.message);
      _showSquadToast('Roster updated. Refresh the page if you do not see changes.', true);
    }
  }

  function _showSquadToast(message, isError = false) {
    const toast = document.getElementById('squad-toast');
    const msgEl = document.getElementById('squad-toast-msg');
    if (!toast || !msgEl) {
      // Fallback to global toast
      if (window.showToast) {
        window.showToast({ type: isError ? 'error' : 'success', message });
      }
      return;
    }

    msgEl.textContent = message;
    const inner = toast.querySelector('div');
    if (inner) {
      if (isError) {
        inner.className = 'px-6 py-3 rounded-xl bg-[#FF2A55]/10 border border-[#FF2A55]/20 backdrop-blur-xl shadow-2xl flex items-center gap-3';
      } else {
        inner.className = 'px-6 py-3 rounded-xl bg-[#00FF66]/10 border border-[#00FF66]/20 backdrop-blur-xl shadow-2xl flex items-center gap-3';
      }
    }

    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3000);
    _announceLiveMessage(message, isError ? 'assertive' : 'polite');
  }

  // ──────────────────────────────────────────────────────────
  // Bracket Zoom Controls
  // ──────────────────────────────────────────────────────────
  let _bracketScale = 1;

  function _redrawBracketLines() {
    const tree = document.getElementById('hub-bracket-tree');
    if (!tree) return;
    requestAnimationFrame(() => {
      tree.querySelectorAll('.bk-section').forEach(sec => _drawBracketConnectors(sec));
    });
  }

  function bracketZoom(dir) {
    const tree = document.getElementById('hub-bracket-tree');
    if (!tree) return;
    _bracketScale = Math.max(0.3, Math.min(2, _bracketScale + dir * 0.2));
    tree.style.transform = `scale(${_bracketScale})`;
    _redrawBracketLines();
  }

  function bracketReset() {
    const tree = document.getElementById('hub-bracket-tree');
    if (!tree) return;
    _bracketScale = 1;
    tree.style.transform = 'scale(1)';
    _redrawBracketLines();
  }

  // ──────────────────────────────────────────────────────────
  // Prizes Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchPrizes() {
    const url = _shell?.dataset.apiPrizeClaim;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _prizesCache = data;
      _renderPrizes(data);
    } catch (err) {
      console.warn('[HubEngine] Prizes fetch failed:', err.message);
      // Show empty state
      _hide('prize-pool-skeleton');
      _hide('prize-dist-skeleton');
      _show('prize-empty-state');
    }
  }

  function _renderPrizes(data) {
    // ── Prize Pool ──
    _hide('prize-pool-skeleton');
    const poolContent = document.getElementById('prize-pool-content');
    if (poolContent) {
      const amt = parseFloat(data.prize_pool?.total || 0);
      document.getElementById('prize-pool-amount').textContent = amt > 0 ? _formatNumber(amt) : '—';
      document.getElementById('prize-pool-currency').textContent = data.prize_pool?.currency || 'BDT';
      document.getElementById('prize-deltacoin').textContent = _formatNumber(data.prize_pool?.deltacoin || 0);
      poolContent.classList.remove('hidden');
    }

    // Tournament status badge
    const statusEl = document.getElementById('prize-tournament-status');
    if (statusEl && data.tournament_status) {
      const s = data.tournament_status;
      const cls = s === 'live' ? 'live' : s === 'completed' ? 'neutral' : 'info';
      statusEl.className = `hub-badge hub-badge-${cls}`;
      statusEl.textContent = s.charAt(0).toUpperCase() + s.slice(1);
    }

    // ── Distribution Breakdown ──
    _hide('prize-dist-skeleton');
    const distContent = document.getElementById('prize-dist-content');
    if (distContent) {
      const dist = data.prize_pool?.distribution || {};
      const entries = Object.entries(dist);

      if (entries.length > 0) {
        let html = '';
        entries.forEach(([place, share]) => {
          const cardClass = place === '1' ? 'gold' : place === '2' ? 'silver' : place === '3' ? 'bronze' : '';
          const emoji = place === '1' ? '🥇' : place === '2' ? '🥈' : place === '3' ? '🥉' : '🏅';
          const label = _ordinal(place) + ' Place';
          html += `
            <div class="prize-placement-card ${cardClass}">
              <div class="text-lg mb-1">${emoji}</div>
              <p class="text-xs font-bold text-white">${_esc(label)}</p>
              <p class="text-lg font-black text-[#FFB800]" style="font-family:Outfit,sans-serif;">${_esc(String(share))}</p>
            </div>`;
        });
        distContent.innerHTML = html;
        distContent.classList.remove('hidden');
      }

      // Also render from overview aggregates if available
      if (data.overview && data.overview.length > 0 && entries.length === 0) {
        let html = '';
        data.overview.forEach(row => {
          html += `
            <div class="prize-placement-card">
              <p class="text-xs font-bold text-white">${_esc(row.placement)}</p>
              <p class="text-lg font-black text-[#FFB800]" style="font-family:Outfit,sans-serif;">${_formatNumber(parseFloat(row.total))}</p>
              <p class="text-[10px] text-gray-500">${row.count} recipient${row.count !== 1 ? 's' : ''}</p>
            </div>`;
        });
        distContent.innerHTML = html;
        distContent.classList.remove('hidden');
      }
    }

    // ── Your Prizes ──
    if (data.your_prizes && data.your_prizes.length > 0) {
      const section = document.getElementById('your-prizes-section');
      const list = document.getElementById('your-prizes-list');
      if (section && list) {
        let html = '';
        data.your_prizes.forEach(p => {
          const claimedBadge = p.claimed
            ? `<span class="hub-badge hub-badge-${p.claim_status === 'paid' ? 'live' : p.claim_status === 'rejected' ? 'danger' : 'warning'}">${_esc(p.claim_status)}</span>`
            : '';
          const claimBtn = !p.claimed
            ? `<button class="prize-claim-btn" onclick="HubEngine.openPrizeModal(${p.id}, '${_esc(p.amount)}', '${_esc(p.placement_display)}')">Claim Prize</button>`
            : '';

          html += `
            <div class="prize-your-card">
              <div>
                <p class="text-sm font-bold text-white">${_esc(p.placement_display)}</p>
                <p class="text-xs text-gray-400 mt-0.5">Amount: <span class="text-[#FFB800] font-bold">${_formatNumber(parseFloat(p.amount))}</span></p>
              </div>
              <div class="flex items-center gap-3">
                ${claimedBadge}
                ${claimBtn}
              </div>
            </div>`;
        });
        list.innerHTML = html;
        section.classList.remove('hidden');
      }
    }

    // ── Empty check ──
    const hasPool = parseFloat(data.prize_pool?.total || 0) > 0 || (data.prize_pool?.deltacoin || 0) > 0;
    const hasPrizes = data.your_prizes && data.your_prizes.length > 0;
    const hasOverview = data.overview && data.overview.length > 0;
    if (!hasPool && !hasPrizes && !hasOverview) {
      _show('prize-empty-state');
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ── Prize Claim Modal ──
  function openPrizeModal(txId, amount, placement) {
    if (_isCriticalLocked()) {
      _showLockToast();
      return;
    }

    document.getElementById('claim-transaction-id').value = txId;
    document.getElementById('claim-modal-amount').textContent = amount;
    document.getElementById('claim-modal-placement').textContent = placement;
    document.getElementById('claim-error').classList.add('hidden');
    document.getElementById('claim-success').classList.add('hidden');
    document.getElementById('claim-submit-btn').disabled = false;

    // Show/hide destination field based on method
    _onPayoutMethodChange();
    const select = document.getElementById('claim-payout-method');
    if (select) {
      select.removeEventListener('change', _onPayoutMethodChange);
      select.addEventListener('change', _onPayoutMethodChange);
    }

    _openModal('prize-claim-modal');
  }

  function closePrizeModal() {
    _closeModal('prize-claim-modal');
  }

  function _onPayoutMethodChange() {
    const method = document.getElementById('claim-payout-method')?.value;
    const wrap = document.getElementById('claim-destination-wrap');
    if (wrap) {
      wrap.classList.toggle('hidden', method === 'deltacoin');
    }
  }

  async function submitPrizeClaim() {
    if (_isCriticalLocked()) {
      _showLockToast();
      return;
    }

    const url = _shell?.dataset.apiPrizeClaim;
    if (!url) return;

    const txId = document.getElementById('claim-transaction-id').value;
    const method = document.getElementById('claim-payout-method').value;
    const dest = document.getElementById('claim-payout-destination')?.value || '';
    const btn = document.getElementById('claim-submit-btn');
    const errEl = document.getElementById('claim-error');
    const okEl = document.getElementById('claim-success');

    btn.disabled = true;
    btn.textContent = 'Submitting...';
    errEl.classList.add('hidden');
    okEl.classList.add('hidden');

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': _csrfToken,
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          transaction_id: parseInt(txId),
          payout_method: method,
          payout_destination: dest,
        }),
      });

      const data = await resp.json();

      if (data.success) {
        okEl.textContent = 'Prize claimed successfully! Your payout is being processed.';
        okEl.classList.remove('hidden');
        btn.textContent = 'Claimed';
        // Refresh cache
        _prizesCache = null;
        setTimeout(() => {
          closePrizeModal();
          _fetchPrizes();
        }, 1500);
      } else {
        errEl.textContent = data.error || 'Failed to claim prize.';
        errEl.classList.remove('hidden');
        btn.disabled = false;
        btn.textContent = 'Submit Claim';
      }
    } catch (err) {
      console.error('[HubEngine] Prize claim error:', err);
      errEl.textContent = 'Network error. Please try again.';
      errEl.classList.remove('hidden');
      btn.disabled = false;
      btn.textContent = 'Submit Claim';
    }
  }

  // ──────────────────────────────────────────────────────────
  // Resources Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchResources() {
    const url = _shell?.dataset.apiResources;
    if (!url) return;

    const rulesContent = document.getElementById('rules-content');
    const socialSection = document.getElementById('resources-social-section');
    const sponsorsSection = document.getElementById('resources-sponsors-section');
    const emptyState = document.getElementById('resources-empty-state');
    if (rulesContent) rulesContent.classList.add('hidden');
    if (socialSection) socialSection.classList.add('hidden');
    if (sponsorsSection) sponsorsSection.classList.add('hidden');
    if (emptyState) emptyState.classList.add('hidden');
    _show('rules-skeleton');

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _resourcesCache = data;
      _renderResources(data);
    } catch (err) {
      console.warn('[HubEngine] Resources fetch failed:', err.message);
      _hide('rules-skeleton');
      _setResourcesEmptyState('Could not load resources right now.', 'Please check your network and try again.', true);
    }
  }

  function _setResourcesEmptyState(title, subtitle, canRetry) {
    const titleEl = document.getElementById('resources-empty-title');
    const subtitleEl = document.getElementById('resources-empty-subtitle');
    const retryBtn = document.getElementById('resources-empty-retry');

    if (titleEl) titleEl.textContent = title || 'No resources available yet';
    if (subtitleEl) subtitleEl.textContent = subtitle || 'The organizer has not published any resources yet.';
    if (retryBtn) {
      retryBtn.classList.toggle('hidden', !canRetry);
      retryBtn.onclick = canRetry ? _fetchResources : null;
    }

    _show('resources-empty-state');
  }

  function _renderResources(data) {
    _hide('rules-skeleton');

    const hasRules = data.rules?.text || data.rules?.pdf_url;
    const hasSocial = data.social_links && data.social_links.length > 0;
    const hasSponsors = data.sponsors && data.sponsors.length > 0;
    const hasContact = !!(data.contact_email || data.contact_phone);
    const hasSupportInfo = !!data.support_info;

    if (!hasRules && !hasSocial && !hasSponsors && !hasContact && !hasSupportInfo) {
      _setResourcesEmptyState(
        'No resources available yet',
        'The organizer has not published any resources for this tournament yet.',
        false,
      );
      return;
    }

    // ── Rules ──
    if (hasRules) {
      const rulesContent = document.getElementById('rules-content');
      if (rulesContent) rulesContent.classList.remove('hidden');

      // PDF link
      if (data.rules.pdf_url) {
        const pdfLink = document.getElementById('rules-pdf-link');
        if (pdfLink) pdfLink.classList.remove('hidden');
        const pdfUrl = document.getElementById('rules-pdf-url');
        if (pdfUrl) pdfUrl.href = data.rules.pdf_url;
      }

      // Rules text
      if (data.rules.text) {
        const textEl = document.getElementById('rules-text-content');
        if (textEl) {
          textEl.innerHTML = _renderSimpleMarkdown(data.rules.text);
        }
      }

      // Terms
      if (data.rules.terms) {
        const termsSec = document.getElementById('terms-section');
        const termsText = document.getElementById('terms-text-content');
        if (termsSec) termsSec.classList.remove('hidden');
        if (termsText) termsText.textContent = data.rules.terms;
      }
    } else {
      _show('rules-empty');
    }

    // ── Social Links ──
    if (hasSocial || hasContact || hasSupportInfo) {
      const socialSection = document.getElementById('resources-social-section');
      if (socialSection) {
        socialSection.classList.remove('hidden');
        socialSection.classList.add('hub-fade-in-up');
      }

      const emailRow = document.getElementById('contact-email-row');
      const phoneRow = document.getElementById('contact-phone-row');
      const supportRow = document.getElementById('resources-support-row');
      if (emailRow) emailRow.classList.add('hidden');
      if (phoneRow) phoneRow.classList.add('hidden');
      if (supportRow) supportRow.classList.add('hidden');

      const grid = document.getElementById('social-links-grid');
      if (grid && hasSocial) {
        const iconMap = {
          discord: 'message-circle', twitter: 'twitter', instagram: 'instagram',
          youtube: 'youtube', facebook: 'facebook', tiktok: 'music',
          website: 'globe', twitch: 'tv', youtube_stream: 'play-circle',
        };
        const subtitleMap = {
          discord: 'Community',
          twitter: 'News',
          instagram: 'Media',
          youtube: 'Videos',
          facebook: 'Page',
          tiktok: 'Clips',
          website: 'Official',
          twitch: 'Live',
          youtube_stream: 'Live',
        };
        let html = '';
        data.social_links.forEach((link, idx) => {
          const icon = iconMap[link.key] || 'link';
          const sub = subtitleMap[link.key] || 'Channel';
          html += `
            <a href="${_esc(link.url)}" target="_blank" rel="noopener" class="social-link-card" style="animation: fadeIn 220ms ease ${idx * 35}ms both;">
              <div class="social-icon ${_esc(link.key)}">
                <i data-lucide="${icon}" class="w-4 h-4"></i>
              </div>
              <span>
                <span class="social-link-label">${_esc(link.label)}</span>
                <span class="social-link-sub">${_esc(sub)}</span>
              </span>
            </a>`;
        });
        grid.innerHTML = html;
      } else if (grid) {
        grid.innerHTML = '';
      }

      if (hasContact) {
        const emailLink = document.getElementById('contact-email-link');
        const emailText = document.getElementById('contact-email-text');
        if (data.contact_email) {
          if (emailRow) emailRow.classList.remove('hidden');
          if (emailLink) emailLink.href = 'mailto:' + data.contact_email;
          if (emailText) emailText.textContent = data.contact_email;
        }

        const phoneLink = document.getElementById('contact-phone-link');
        const phoneText = document.getElementById('contact-phone-text');
        if (data.contact_phone) {
          const phoneDigits = String(data.contact_phone).replace(/[^\d+]/g, '').replace('+', '');
          if (phoneRow) phoneRow.classList.remove('hidden');
          if (phoneLink) phoneLink.href = 'https://wa.me/' + phoneDigits;
          if (phoneText) phoneText.textContent = data.contact_phone;
        }
      }

      if (hasSupportInfo) {
        const supportText = document.getElementById('resources-support-text');
        if (supportRow) supportRow.classList.remove('hidden');
        if (supportText) supportText.innerHTML = `<span class="hub-support-title">Support & Disputes</span>${_esc(data.support_info).replace(/\n/g, '<br>')}`;
      }
    }

    // ── Sponsors ──
    if (hasSponsors) {
      const sponsorsSection = document.getElementById('resources-sponsors-section');
      if (sponsorsSection) {
        sponsorsSection.classList.remove('hidden');
        sponsorsSection.classList.add('hub-fade-in-up');
      }

      const tierMap = { title: 'sponsors-title', gold: 'sponsors-gold', silver: 'sponsors-silver', bronze: 'sponsors-bronze', partner: 'sponsors-partner' };
      const tierGridMap = { title: 'sponsors-title', gold: 'sponsors-gold-grid', silver: 'sponsors-silver-grid', bronze: 'sponsors-bronze-grid', partner: 'sponsors-partner-grid' };

      // Group sponsors by tier
      const grouped = {};
      data.sponsors.forEach(s => {
        if (!grouped[s.tier]) grouped[s.tier] = [];
        grouped[s.tier].push(s);
      });

      Object.entries(grouped).forEach(([tier, sponsors]) => {
        const wrapper = document.getElementById(tierMap[tier]);
        const grid = document.getElementById(tierGridMap[tier]);
        if (!wrapper) return;
        wrapper.classList.remove('hidden');

        const target = grid || wrapper;
        let html = '';

        sponsors.forEach(s => {
          const isTitle = tier === 'title';
          const cardClass = isTitle ? 'sponsor-card title-sponsor' : 'sponsor-card';
          const img = s.banner_url || s.logo_url;
          const imgTag = img
            ? `<img src="${_esc(img)}" alt="${_esc(s.name)}" class="${isTitle ? 'h-16 p-4' : 'h-10 p-2'} object-contain mx-auto">`
            : `<div class="h-10 flex items-center justify-center text-sm font-bold text-gray-400">${_esc(s.name)}</div>`;

          const link = s.website_url ? `href="${_esc(s.website_url)}" target="_blank" rel="noopener"` : '';
          html += `
            <a ${link} class="${cardClass}">
              ${imgTag}
              <div class="sponsor-info">
                <p class="sponsor-name">${_esc(s.name)}</p>
                ${s.description ? `<p class="text-[10px] text-gray-500 mt-0.5 line-clamp-2">${_esc(s.description)}</p>` : ''}
              </div>
            </a>`;
        });
        target.innerHTML = html;
      });
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // Smart content renderer: detects HTML vs plain/markdown
  function _renderSimpleMarkdown(text) {
    if (!text) return '';

    // Detect if content is already HTML (starts with a tag or contains common block tags)
    const trimmed = text.trim();
    if (/^<[a-z][\s\S]*>/i.test(trimmed) || /<(p|div|h[1-6]|ul|ol|li|br|table|blockquote)\b/i.test(trimmed)) {
      // Content is HTML — render directly (trusted content from admin)
      return trimmed;
    }

    // Plain text / markdown — escape then transform
    let html = _esc(text);
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h4 class="text-sm font-bold text-white mt-4 mb-1">$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3 class="text-base font-bold text-white mt-5 mb-2">$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2 class="text-lg font-bold text-white mt-6 mb-2">$1</h2>');
    // Bold / italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Lists
    html = html.replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>');
    html = html.replace(/^(\d+)\. (.+)$/gm, '<li class="ml-4 list-decimal">$2</li>');
    // Line breaks → paragraphs
    html = html.replace(/\n\n/g, '</p><p class="mb-2">');
    html = html.replace(/\n/g, '<br>');
    html = '<p class="mb-2">' + html + '</p>';
    return html;
  }

  // ── DOM helpers ──
  function _show(id) { const el = document.getElementById(id); if (el) el.classList.remove('hidden'); }
  function _hide(id) { const el = document.getElementById(id); if (el) el.classList.add('hidden'); }
  function _formatNumber(n) { return n.toLocaleString('en-US', { maximumFractionDigits: 2 }); }
  function _ordinal(n) {
    const num = parseInt(n);
    if (isNaN(num)) return n;
    const s = ['th', 'st', 'nd', 'rd'];
    const v = num % 100;
    return num + (s[(v - 20) % 10] || s[v] || s[0]);
  }

  // ──────────────────────────────────────────────────────────
  // Utilities
  // ──────────────────────────────────────────────────────────
  function _getCookie(name) {
    const cookies = document.cookie.split(';');
    for (const c of cookies) {
      const [k, v] = c.trim().split('=');
      if (k === name) return decodeURIComponent(v);
    }
    return '';
  }

  function _esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ──────────────────────────────────────────────────────────
  // Loading & Error State Helpers
  // ──────────────────────────────────────────────────────────
  /**
   * Show a loading spinner inside a container element.
   * @param {string} containerId  DOM id of the container
   * @param {string} [message]    Optional loading text
   */
  function _showLoading(containerId, message) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const msg = message || 'Loading…';
    el.innerHTML = `
      <div class="flex flex-col items-center justify-center py-16 gap-4 text-gray-400">
        <svg class="animate-spin w-8 h-8 text-[#00F0FF]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <span class="text-sm">${_esc(msg)}</span>
      </div>`;
    el.classList.remove('hidden');
  }

  /**
   * Show an error message inside a container element.
   * @param {string} containerId  DOM id of the container
   * @param {string} message      Error text
   * @param {string} [retryAction] Optional retry action key
   */
  function _showError(containerId, message, retryAction) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const retryBtn = retryAction
      ? `<button type="button" data-hub-retry="${_esc(retryAction)}" class="mt-3 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-bold text-white transition-all">Retry</button>`
      : '';
    el.innerHTML = `
      <div class="flex flex-col items-center justify-center py-16 gap-3 text-center">
        <div class="w-12 h-12 rounded-xl bg-[#FF2A55]/10 flex items-center justify-center">
          <svg class="w-6 h-6 text-[#FF2A55]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <p class="text-sm text-gray-400 max-w-sm">${_esc(message)}</p>
        ${retryBtn}
      </div>`;
    el.classList.remove('hidden');
    _announceLiveMessage(message, 'assertive');
  }

  function _announceLiveMessage(message, mode = 'polite') {
    const safeMessage = (message || '').trim();
    if (!safeMessage) return;
    const targetId = mode === 'assertive' ? 'hub-live-region-assertive' : 'hub-live-region';
    const region = document.getElementById(targetId);
    if (!region) return;
    region.textContent = '';
    setTimeout(() => {
      region.textContent = safeMessage;
    }, 10);
  }

  function _handleRetryButtonClick(event) {
    const btn = event.target.closest('[data-hub-retry]');
    if (!btn) return;
    const action = btn.getAttribute('data-hub-retry');
    if (!action) return;
    _runRetryAction(action);
  }

  function _runRetryAction(action) {
    switch (action) {
      case 'bracket':
        _fetchBracket();
        break;
      case 'standings':
        _fetchStandings();
        break;
      case 'matches':
        _fetchMatches();
        break;
      default:
        console.warn('[HubEngine] Unknown retry action:', action);
        break;
    }
  }

  // ──────────────────────────────────────────────────────────
  // Map Viewer — Match Game Scores Detail Modal
  // ──────────────────────────────────────────────────────────
  let _mapViewerMatch = null;

  function openMapViewer(matchData) {
    _mapViewerMatch = matchData;
    let modal = document.getElementById('hub-map-viewer-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'hub-map-viewer-modal';
      modal.className = 'fixed inset-0 z-[100] flex items-center justify-center hidden';
      modal.onclick = (e) => { if (e.target === modal) closeMapViewer(); };
      document.body.appendChild(modal);
    }

    const m = matchData;
    const gs = Array.isArray(m.game_scores) ? m.game_scores : [];
    const bo = m.best_of || (gs.length > 0 ? gs.length : 1);

    let mapsHtml = '';
    if (gs.length > 0) {
      gs.forEach((g, i) => {
        const mapName = g.map_name || `Map ${i + 1}`;
        const p1r = g.p1_score ?? g.team1_rounds ?? 0;
        const p2r = g.p2_score ?? g.team2_rounds ?? 0;
        const p1Win = p1r > p2r;
        mapsHtml += `
          <div class="flex items-center justify-between px-5 py-3 ${i % 2 === 0 ? 'bg-white/[0.02]' : ''}">
            <div class="flex items-center gap-3">
              <span class="text-xs font-bold text-gray-500 w-14">MAP ${i + 1}</span>
              <span class="text-sm text-white font-medium">${_esc(mapName)}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-lg font-black ${p1Win ? 'text-[#00FF66]' : 'text-[#FF2A55]'}" style="font-family:Outfit,sans-serif;">${p1r}</span>
              <span class="text-gray-600 text-xs">:</span>
              <span class="text-lg font-black ${p1Win ? 'text-[#FF2A55]' : 'text-[#00FF66]'}" style="font-family:Outfit,sans-serif;">${p2r}</span>
            </div>
          </div>`;
      });
    } else {
      mapsHtml = `<div class="px-5 py-8 text-center text-sm text-gray-500">No map details available for this match.</div>`;
    }

    modal.innerHTML = `
      <div class="absolute inset-0 bg-black/70 backdrop-blur-sm"></div>
      <div class="relative w-full max-w-md mx-4 hub-glass rounded-2xl border border-white/10 overflow-hidden">
        <div class="p-5 flex items-center justify-between border-b border-white/5">
          <div>
            <h3 class="text-base font-bold text-white" style="font-family:Outfit,sans-serif;">
              ${_esc(m.p1_name || 'Team 1')} vs ${_esc(m.p2_name || 'Team 2')}
            </h3>
            <p class="text-[10px] text-gray-500 uppercase tracking-widest mt-0.5">
              ${_esc(m.round_name || '')} · Match ${m.match_number || ''} · BO${bo}
            </p>
          </div>
          <button onclick="HubEngine.closeMapViewer()" class="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="flex items-center justify-between px-5 py-3 bg-white/[0.03]">
          <span class="text-sm font-bold text-white">${_esc(m.p1_name || 'Team 1')}</span>
          <span class="text-2xl font-black text-white" style="font-family:Outfit,sans-serif;">
            ${m.p1_score ?? 0} — ${m.p2_score ?? 0}
          </span>
          <span class="text-sm font-bold text-white">${_esc(m.p2_name || 'Team 2')}</span>
        </div>
        ${mapsHtml}
      </div>`;
    modal.classList.remove('hidden');
  }

  function closeMapViewer() {
    const modal = document.getElementById('hub-map-viewer-modal');
    if (modal) modal.classList.add('hidden');
    _mapViewerMatch = null;
  }

  // ──────────────────────────────────────────────────────────
  // Bracket Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchBracket() {
    const url = _shell?.dataset.apiBracket;
    if (!url) return;

    _show('bracket-skeleton');
    _hide('bracket-not-generated');
    _hide('bracket-zoom-controls');

    const tree = document.getElementById('hub-bracket-tree');
    if (tree) {
      tree.classList.remove('hidden');
      tree.innerHTML = '';
    }

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _bracketCache = data;
      _hide('bracket-skeleton');
      _renderBracket(data);
    } catch (err) {
      console.warn('[HubEngine] Bracket fetch failed:', err.message);
      _hide('bracket-skeleton');
      _showError('hub-bracket-tree', 'Failed to load bracket. Please try again.', 'bracket');
    }
  }

  function _renderBracket(data) {
    _hide('bracket-skeleton');

    const tree = document.getElementById('hub-bracket-tree');
    if (!tree) return;

    if (!data.generated || !data.rounds || data.rounds.length === 0) {
      tree.innerHTML = '';
      tree.classList.add('hidden');
      _show('bracket-not-generated');
      _hide('bracket-zoom-controls');
      return;
    }

    tree.classList.remove('hidden');
    _hide('bracket-not-generated');
    _show('bracket-zoom-controls');
    const fmtEl = document.getElementById('bracket-format-label');
    if (fmtEl && data.format_display) fmtEl.textContent = data.format_display;

    const fmt = (data.format || '').toLowerCase();
    const isDE = fmt.includes('double');

    // Split rounds into UB, LB, GF sections for double elimination
    let sections = [];
    if (isDE) {
      let ub = [], lb = [], gf = [];
      data.rounds.forEach(r => {
        const rn = (r.round_name || '').toLowerCase();
        if (rn.includes('grand') || rn.includes('gf')) gf.push(r);
        else if (rn.includes('lb') || rn.includes('lower')) lb.push(r);
        else ub.push(r);
      });
      if (ub.length) sections.push({ label: 'UPPER BRACKET', cls: 'bk-ub', icon: '🟢', rounds: ub });
      if (lb.length) sections.push({ label: 'LOWER BRACKET', cls: 'bk-lb', icon: '🔴', rounds: lb });
      if (gf.length) sections.push({ label: 'GRAND FINAL',   cls: 'bk-gf', icon: '👑', rounds: gf });
    } else {
      sections.push({ label: '', cls: '', icon: '', rounds: data.rounds });
    }

    // ── Match card renderer ──
    function matchHTML(m) {
      const p1 = m.participant1 || { name: 'TBD', score: null, is_winner: false };
      const p2 = m.participant2 || { name: 'TBD', score: null, is_winner: false };
      const st = m.state === 'live' ? 'bk-live' : (m.state === 'completed' || m.state === 'forfeit') ? 'bk-done' : '';
      const matchNum = m.match_number ? `<span class="bk-mnum">M${m.match_number}</span>` : '';
      const liveBadge = m.state === 'live'
        ? '<span class="bk-badge-live"><span class="bk-dot"></span>LIVE</span>' : '';
      return `<div class="bk-match ${st}" data-mid="${m.id || ''}">
        <div class="bk-match-head">${matchNum}${liveBadge}</div>
        <div class="bk-team${p1.is_winner ? ' bk-w' : ''}">
          <span class="bk-name">${_esc(p1.name)}</span>
          <span class="bk-sc">${p1.score != null ? p1.score : '-'}</span>
        </div>
        <div class="bk-team${p2.is_winner ? ' bk-w' : ''}">
          <span class="bk-name">${_esc(p2.name)}</span>
          <span class="bk-sc">${p2.score != null ? p2.score : '-'}</span>
        </div>
      </div>`;
    }

    // ── Build HTML for all sections ──
    let html = '';
    sections.forEach(sec => {
      const maxMatches = Math.max(...sec.rounds.map(r => (r.matches || []).length), 1);
      const secH = Math.max(maxMatches * 92, 200);

      if (sec.label) {
        html += `<div class="bk-label ${sec.cls}">${sec.icon} ${sec.label}</div>`;
      }
      html += `<div class="bk-section" data-sec="${sec.cls}">`;
      sec.rounds.forEach((round, ri) => {
        html += `<div class="bk-col">`;
        html += `<div class="bk-col-title">${_esc(round.round_name || 'Round')}</div>`;
        html += `<div class="bk-col-body" style="height:${secH}px">`;
        (round.matches || []).forEach(m => { html += matchHTML(m); });
        html += `</div></div>`;
      });
      html += `</div>`;
    });

    tree.innerHTML = html;

    // Draw SVG connector lines after layout renders
    requestAnimationFrame(() => {
      tree.querySelectorAll('.bk-section').forEach(sec => _drawBracketConnectors(sec));
    });
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ── SVG bracket connector lines ──
  function _drawBracketConnectors(section) {
    const cols = section.querySelectorAll('.bk-col');
    if (cols.length < 2) return;

    section.querySelectorAll('.bk-svg').forEach(s => s.remove());

    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('bk-svg');
    svg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:1;overflow:visible;';
    section.appendChild(svg);

    const base = section.getBoundingClientRect();

    for (let ci = 0; ci < cols.length - 1; ci++) {
      const curCards = cols[ci].querySelectorAll('.bk-match');
      const nxtCards = cols[ci + 1].querySelectorAll('.bk-match');
      if (!curCards.length || !nxtCards.length) continue;

      const ratio = Math.max(1, Math.ceil(curCards.length / nxtCards.length));

      nxtCards.forEach((nc, ni) => {
        const nr = nc.getBoundingClientRect();
        const ny = nr.top + nr.height / 2 - base.top;
        const nx = nr.left - base.left;

        for (let j = 0; j < ratio; j++) {
          const idx = ni * ratio + j;
          if (idx >= curCards.length) break;
          const cc = curCards[idx];
          const cr = cc.getBoundingClientRect();
          const cy = cr.top + cr.height / 2 - base.top;
          const cx = cr.right - base.left;
          const mx = (cx + nx) / 2;

          const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
          path.setAttribute('d', `M${cx},${cy} H${mx} V${ny} H${nx}`);
          path.classList.add('bk-line');
          svg.appendChild(path);
        }
      });
    }
  }

  // ──────────────────────────────────────────────────────────
  // Standings Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchStandings() {
    const url = _shell?.dataset.apiStandings;
    if (!url) return;

    const container = document.getElementById('hub-standings-data');
    if (container) _showLoading('hub-standings-data', 'Loading standings…');
    _hide('standings-empty');

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _standingsCache = data;
      _hide('standings-skeleton');
      _renderStandings(data);
    } catch (err) {
      console.warn('[HubEngine] Standings fetch failed:', err.message);
      _hide('standings-skeleton');
      const target = container ? 'hub-standings-data' : 'standings-empty';
      _showError(target, 'Failed to load standings. Please try again.', 'standings');
    }
  }

  function _renderStandings(data) {
    _hide('standings-skeleton');

    if (!data.has_standings) {
      _show('standings-empty');
      return;
    }

    _show('standings-format-badge');
    const container = document.getElementById('hub-standings-container');
    if (!container) return;

    let html = '';

    // ── Esports placement tier helpers ──
    function placementLabel(rank, total) {
      if (rank === 1) return '1st';
      if (rank === 2) return '2nd';
      if (rank === 3) return '3rd';
      if (rank <= 4) return '3rd–4th';
      if (rank <= 6) return '5th–6th';
      if (rank <= 8) return '5th–8th';
      if (rank <= 12) return '9th–12th';
      if (rank <= 16) return '13th–16th';
      return `${rank}th`;
    }
    function tierColor(rank) {
      if (rank === 1) return '#FFB800';
      if (rank === 2) return '#C0C0C0';
      if (rank <= 4) return '#CD7F32';
      if (rank <= 8) return '#00F0FF';
      return '#4B5563';
    }
    function tierBg(rank) {
      if (rank === 1) return 'rgba(255,184,0,0.08)';
      if (rank === 2) return 'rgba(192,192,192,0.06)';
      if (rank <= 4) return 'rgba(205,127,50,0.05)';
      return 'transparent';
    }
    function tierIcon(rank) {
      if (rank === 1) return '👑';
      if (rank === 2) return '🥈';
      if (rank === 3) return '🥉';
      return '';
    }

    // ── Bracket-derived standings (no groups) ──
    if (data.standings_type === 'bracket' && Array.isArray(data.rows)) {

      // ── Champion banner ──
      const champ = data.rows.find(r => r.rank === 1);
      if (champ) {
        html += `<div class="stnd-champion-banner">
          <div class="stnd-champ-icon">👑</div>
          <div class="stnd-champ-info">
            <div class="stnd-champ-label">TOURNAMENT CHAMPION</div>
            <div class="stnd-champ-name">${_esc(champ.name)}</div>
            <div class="stnd-champ-stat">${champ.wins}W – ${champ.losses}L &nbsp;·&nbsp; Maps ${champ.map_wins || 0}–${champ.map_losses || 0} &nbsp;·&nbsp; RD ${champ.round_diff > 0 ? '+' : ''}${champ.round_diff}</div>
          </div>
        </div>`;
      }

      // ── Final placements table (esports-style) ──
      html += `<div class="stnd-table-wrap">`;
      html += `<table class="stnd-table">`;
      html += `<thead><tr>`;
      html += `<th class="stnd-th stnd-th-rank">PLACE</th>`;
      html += `<th class="stnd-th stnd-th-team">TEAM</th>`;
      html += `<th class="stnd-th">SERIES</th>`;
      html += `<th class="stnd-th">MAPS</th>`;
      html += `<th class="stnd-th">RND DIFF</th>`;
      html += `<th class="stnd-th">WIN%</th>`;
      html += `</tr></thead><tbody>`;

      data.rows.forEach(row => {
        const tc = tierColor(row.rank);
        const bg = tierBg(row.rank);
        const icon = tierIcon(row.rank);
        const youTag = row.is_you ? ` <span class="stnd-you">YOU</span>` : '';
        const youCls = row.is_you ? ' stnd-row-you' : '';
        const totalGames = row.wins + row.losses;
        const winPct = totalGames > 0 ? Math.round((row.wins / totalGames) * 100) : 0;
        const mapW = row.map_wins || 0;
        const mapL = row.map_losses || 0;
        const rdSign = row.round_diff > 0 ? '+' : '';

        html += `<tr class="stnd-row${youCls}" style="background:${bg}">`;
        // Placement
        html += `<td class="stnd-td stnd-td-rank"><span class="stnd-rank-badge" style="color:${tc};border-color:${tc}40">${icon ? icon + ' ' : ''}${placementLabel(row.rank, data.rows.length)}</span></td>`;
        // Team
        html += `<td class="stnd-td stnd-td-team">`;
        html += `<div class="stnd-team-cell">`;
        html += `<div class="stnd-team-avatar" style="border-color:${tc}30"><span class="stnd-team-initial">${_esc((row.name || '?').charAt(0))}</span></div>`;
        html += `<div class="stnd-team-info"><span class="stnd-team-name">${_esc(row.name)}${youTag}</span></div>`;
        html += `</div></td>`;
        // Series record (W-L)
        html += `<td class="stnd-td"><span class="stnd-series"><span class="stnd-w">${row.wins}</span><span class="stnd-sep">–</span><span class="stnd-l">${row.losses}</span></span></td>`;
        // Maps record
        html += `<td class="stnd-td"><span class="stnd-maps">${mapW}–${mapL}</span></td>`;
        // Round diff
        html += `<td class="stnd-td"><span class="stnd-rd ${row.round_diff > 0 ? 'stnd-pos' : row.round_diff < 0 ? 'stnd-neg' : ''}">${rdSign}${row.round_diff}</span></td>`;
        // Win %
        html += `<td class="stnd-td"><div class="stnd-winpct-bar"><div class="stnd-winpct-fill" style="width:${winPct}%;background:${tc}"></div><span class="stnd-winpct-txt">${winPct}%</span></div></td>`;
        html += `</tr>`;
      });

      html += `</tbody></table></div>`;
    }

    // ── Group-based standings ──
    else if (Array.isArray(data.groups) && data.groups.length > 0) {
      data.groups.forEach(group => {
        html += `<div class="stnd-group">`;
        html += `<h3 class="stnd-group-title"><i data-lucide="flag" class="w-4 h-4 text-[#00F0FF]"></i> ${_esc(group.name)}</h3>`;

        html += `<div class="stnd-table-wrap">`;
        html += `<table class="stnd-table">`;
        html += `<thead><tr>`;
        html += `<th class="stnd-th stnd-th-rank">#</th>`;
        html += `<th class="stnd-th stnd-th-team">TEAM</th>`;
        html += `<th class="stnd-th">P</th>`;
        html += `<th class="stnd-th">W</th>`;
        html += `<th class="stnd-th">D</th>`;
        html += `<th class="stnd-th">L</th>`;
        html += `<th class="stnd-th">GD</th>`;
        html += `<th class="stnd-th">PTS</th>`;
        html += `</tr></thead><tbody>`;

        (group.standings || []).forEach(row => {
          const youCls = row.is_you ? ' stnd-row-you' : '';
          const youTag = row.is_you ? ` <span class="stnd-you">YOU</span>` : '';
          const qualCls = row.rank <= 2 ? 'stnd-qualified' : row.rank <= 4 ? 'stnd-playoff' : '';
          html += `<tr class="stnd-row${youCls}">`;
          html += `<td class="stnd-td stnd-td-rank ${qualCls}">${row.rank}</td>`;
          html += `<td class="stnd-td stnd-td-team"><span class="stnd-team-name">${_esc(row.name)}${youTag}</span></td>`;
          html += `<td class="stnd-td">${row.matches_played}</td>`;
          html += `<td class="stnd-td stnd-w">${row.won}</td>`;
          html += `<td class="stnd-td">${row.drawn}</td>`;
          html += `<td class="stnd-td stnd-l">${row.lost}</td>`;
          html += `<td class="stnd-td">${row.goal_difference > 0 ? '+' : ''}${row.goal_difference}</td>`;
          html += `<td class="stnd-td font-bold text-white">${row.points}</td>`;
          html += `</tr>`;
        });

        html += `</tbody></table></div></div>`;
      });
    } else {
      _show('standings-empty');
      return;
    }

    container.innerHTML = html;
    container.classList.remove('hidden');
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ──────────────────────────────────────────────────────────
  // Matches Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchMatches() {
    const url = _shell?.dataset.apiMatches;
    if (!url) return;

    _show('matches-skeleton');
    _showLoading('hub-match-cards', 'Loading matches…');
    _hide('matches-empty');

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _matchesCache = data;
      _hide('matches-skeleton');
      _renderMatches(data);
    } catch (err) {
      console.warn('[HubEngine] Matches fetch failed:', err.message);
      _hide('matches-skeleton');
      _showError('hub-match-cards', 'Failed to load matches. Please try again.', 'matches');
    }
  }

  function _renderMatches(data) {
    _hide('matches-skeleton');

    const isStaff = data.active_matches?.some(m => m.is_staff_view) || data.match_history?.some(m => m.is_staff_view);

    // Active matches
    const cardsEl = document.getElementById('hub-match-cards');
    if (cardsEl) {
      if (data.active_matches && data.active_matches.length > 0) {
        _hide('matches-empty');
        let html = '';
        data.active_matches.forEach(m => {
          const stateColor = m.state === 'live' ? '#FF2A55' : m.state === 'ready' ? '#00FF66' : '#00F0FF';
          const lobbyCode = m.lobby_info?.lobby_code || '';
          const matchLabel = isStaff
            ? `${_esc(m.p1_name)} vs ${_esc(m.p2_name)}`
            : `vs ${_esc(m.opponent_name)}`;
          html += `
            <div class="hub-glass rounded-xl p-5 border-l-4 match-card-active" style="border-left-color: ${stateColor}">
              <div class="flex items-center justify-between mb-3">
                <span class="text-[10px] font-bold text-gray-500 uppercase tracking-widest">${_esc(m.round_name)} &middot; Match ${m.match_number}</span>
                <span class="hub-badge" style="background:${stateColor}20;color:${stateColor}">
                  ${m.state === 'live' ? '<span class="w-1.5 h-1.5 rounded-full animate-pulse inline-block" style="background:' + stateColor + '"></span> ' : ''}
                  ${_esc(m.state_display)}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-bold text-white">${matchLabel}</p>
                  ${m.state === 'live' ? `<p class="text-lg font-black text-white mt-1" style="font-family:Outfit,sans-serif;">${m.p1_score ?? 0} — ${m.p2_score ?? 0}</p>` : ''}
                </div>
                ${lobbyCode ? `<div class="text-right"><p class="text-[10px] text-gray-500">Lobby Code</p><p class="text-sm font-bold text-[#00F0FF]" style="font-family:'Space Grotesk',monospace;">${_esc(lobbyCode)}</p></div>` : ''}
              </div>
              ${m.scheduled_at ? `<p class="text-[10px] text-gray-600 mt-2">Scheduled: ${new Date(m.scheduled_at).toLocaleString()}</p>` : ''}
            </div>`;
        });
        cardsEl.innerHTML = html;
        cardsEl.classList.remove('hidden');
      } else {
        cardsEl.innerHTML = '';
        cardsEl.classList.add('hidden');
        _renderMatchLobbyEmptyState();
        _show('matches-empty');
      }
    }

    // Match history
    const historyEl = document.getElementById('hub-match-history');
    if (historyEl) {
      if (data.match_history && data.match_history.length > 0) {
        // Store match data for map viewer access
        window._hubMatchHistory = data.match_history;
        let html = '';
        data.match_history.forEach((m, mi) => {
          const resultClass = m.is_winner === true ? 'text-[#00FF66]' : m.is_winner === false ? 'text-[#FF2A55]' : 'text-gray-400';
          const resultLabel = isStaff ? (m.winner_name ? _esc(m.winner_name) + ' won' : '—') : (m.is_winner === true ? 'WIN' : m.is_winner === false ? 'LOSS' : 'DRAW');
          const matchLabel = isStaff
            ? `${_esc(m.p1_name)} vs ${_esc(m.p2_name)}`
            : `vs ${_esc(m.opponent_name)}`;

          // Map-level scores (game_scores) — inline pills
          let mapsHtml = '';
          const gs = Array.isArray(m.game_scores) ? m.game_scores : [];
          if (gs.length > 0) {
            mapsHtml = '<div class="flex items-center gap-2 mt-2">';
            gs.forEach((g, i) => {
              const mapName = g.map_name || `Map ${i + 1}`;
              const p1r = g.p1_score ?? 0;
              const p2r = g.p2_score ?? 0;
              const p1Win = p1r > p2r;
              const p1Class = p1Win ? 'text-[#00FF66]' : 'text-[#FF2A55]';
              const p2Class = p1Win ? 'text-[#FF2A55]' : 'text-[#00FF66]';
              mapsHtml += `
                <div class="hub-glass rounded-lg px-2.5 py-1.5 text-center" style="min-width:3.5rem">
                  <p class="text-[9px] text-gray-500 truncate" style="max-width:4rem">${_esc(mapName)}</p>
                  <p class="text-xs font-black" style="font-family:'Space Grotesk',monospace;">
                    <span class="${p1Class}">${p1r}</span><span class="text-gray-600">-</span><span class="${p2Class}">${p2r}</span>
                  </p>
                </div>`;
            });
            mapsHtml += '</div>';
          }

          const hasDetail = gs.length > 0;
          const cursorCls = hasDetail ? 'cursor-pointer hover:border-white/15' : '';
          const clickAttr = hasDetail ? `onclick="HubEngine.openMapViewer(window._hubMatchHistory[${mi}])"` : '';

          html += `
            <div class="hub-glass rounded-xl p-4 match-history-card ${cursorCls} transition-colors" ${clickAttr}>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                  <span class="text-xs font-black ${resultClass} w-14">${resultLabel}</span>
                  <div>
                    <p class="text-sm font-medium text-white">${matchLabel}</p>
                    <p class="text-[10px] text-gray-500">${_esc(m.round_name)}</p>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <p class="text-lg font-black text-white" style="font-family:Outfit,sans-serif;">${m.p1_score ?? 0} — ${m.p2_score ?? 0}</p>
                  ${hasDetail ? '<svg class="w-4 h-4 text-gray-600" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 18l6-6-6-6"/></svg>' : ''}
                </div>
              </div>
              ${mapsHtml}
            </div>`;
        });
        historyEl.innerHTML = html;
      } else {
        _show('match-history-empty');
      }
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function _renderMatchLobbyEmptyState() {
    const emptyEl = document.getElementById('matches-empty');
    if (!emptyEl) return;

    const status = _shell?.dataset.tournamentStatus || '';
    let title = 'No Active Matches';
    let message = 'When the tournament goes live and matches are scheduled, your matchups will appear here with live lobby controls and result submission.';

    if (status === 'registration' || status === 'registration_open' || status === 'registration_closed') {
      title = 'Matches Will Unlock After Bracket Generation';
      message = 'Registration is still in progress. After check-in closes and the organizer generates the bracket, your match lobby will activate automatically.';
    } else if (status === 'check_in') {
      title = 'Waiting for Check-In to Close';
      message = 'Check-in is active now. Matchups will appear as soon as the organizer finalizes the bracket and publishes schedules.';
    }

    emptyEl.innerHTML = `
      <div class="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
        <i data-lucide="crosshair" class="w-8 h-8 text-gray-600"></i>
      </div>
      <h3 class="text-lg font-bold text-white mb-2" style="font-family:Outfit,sans-serif;">${_esc(title)}</h3>
      <p class="text-sm text-gray-500 max-w-xl">${_esc(message)}</p>
      <div class="mt-4 flex flex-wrap items-center justify-center gap-2">
        <button class="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-bold text-gray-300 hover:text-white transition-colors" onclick="HubEngine.switchTab('schedule')">
          View Schedule
        </button>
        <button class="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-bold text-gray-300 hover:text-white transition-colors" onclick="HubEngine.switchTab('bracket')">
          Check Bracket Status
        </button>
      </div>
    `;

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ──────────────────────────────────────────────────────────
  // S27: Schedule Tab — Match-Level Schedule
  // ──────────────────────────────────────────────────────────
  let _scheduleMatchesCache = null;

  async function _fetchScheduleMatches() {
    // Reuse the matches API — it returns all match data with scheduled_at
    const url = _shell?.dataset.apiMatches;
    if (!url) return;

    const skeleton = document.getElementById('schedule-match-skeleton');
    const empty    = document.getElementById('schedule-match-empty');
    const list     = document.getElementById('schedule-match-list');
    if (!skeleton && !empty && !list) return; // no schedule match section

    if (skeleton) skeleton.classList.remove('hidden');
    if (empty) empty.classList.add('hidden');
    if (list) list.classList.add('hidden');

    try {
      // Use matches cache if available, otherwise fetch
      let data = _matchesCache;
      if (!data) {
        const resp = await fetch(url, { credentials: 'same-origin' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        data = await resp.json();
        _matchesCache = data;
      }
      _renderScheduleMatches(data);
    } catch (err) {
      console.warn('[Hub] Schedule matches fetch failed:', err.message);
      if (skeleton) skeleton.classList.add('hidden');
      if (empty) { empty.classList.remove('hidden'); }
    }
  }

  function _renderScheduleMatches(data) {
    const skeleton = document.getElementById('schedule-match-skeleton');
    const empty    = document.getElementById('schedule-match-empty');
    const list     = document.getElementById('schedule-match-list');

    if (skeleton) skeleton.classList.add('hidden');

    // Combine active + history matches
    const allMatches = [
      ...(data.active_matches || []),
      ...(data.match_history || [])
    ];

    if (allMatches.length === 0) {
      if (empty) empty.classList.remove('hidden');
      if (list) list.classList.add('hidden');
      return;
    }

    // Sort by scheduled_at (earliest first), unscheduled at end
    const sorted = allMatches.sort((a, b) => {
      if (!a.scheduled_at && !b.scheduled_at) return 0;
      if (!a.scheduled_at) return 1;
      if (!b.scheduled_at) return -1;
      return new Date(a.scheduled_at) - new Date(b.scheduled_at);
    });

    // Group by day
    const groups = {};
    sorted.forEach(m => {
      const day = m.scheduled_at
        ? new Date(m.scheduled_at).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })
        : 'Unscheduled';
      if (!groups[day]) groups[day] = [];
      groups[day].push(m);
    });

    let html = '';
    for (const [day, matches] of Object.entries(groups)) {
      const isToday = day !== 'Unscheduled' && new Date(matches[0].scheduled_at).toDateString() === new Date().toDateString();
      html += `
        <div class="mb-6">
          <div class="flex items-center gap-2 mb-3">
            <span class="text-[10px] font-bold ${isToday ? 'text-[#00FF66]' : 'text-gray-500'} uppercase tracking-widest" style="font-family:'Space Grotesk',monospace;">
              ${isToday ? '● Today — ' : ''}${_esc(day)}
            </span>
            <div class="flex-1 h-px bg-white/5"></div>
          </div>`;

      matches.forEach(m => {
        const stateColors = {
          live: '#FF2A55', ready: '#00FF66', check_in: '#00F0FF',
          scheduled: '#FFB800', completed: '#6b7280', cancelled: '#4b5563',
          forfeit: '#4b5563', disputed: '#f97316'
        };
        const color = stateColors[m.state] || '#6b7280';
        const time = m.scheduled_at
          ? new Date(m.scheduled_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
          : '—';
        const isLive = m.state === 'live';
        const isCompleted = m.state === 'completed';
        const resultTag = isCompleted
          ? (m.is_winner === true ? '<span class="text-[10px] font-bold text-[#00FF66]">WIN</span>'
            : m.is_winner === false ? '<span class="text-[10px] font-bold text-[#FF2A55]">LOSS</span>'
            : '<span class="text-[10px] font-bold text-gray-400">DRAW</span>')
          : '';

        html += `
          <div class="hub-glass rounded-xl p-4 flex items-center gap-4 border-l-3 transition-all hover:border-l-4" style="border-left-color:${color}">
            <div class="w-14 text-center shrink-0">
              <p class="text-sm font-bold ${isLive ? 'text-[#FF2A55]' : 'text-white'}" style="font-family:'Space Grotesk',monospace;">
                ${isLive ? '<span class="w-1.5 h-1.5 rounded-full bg-[#FF2A55] animate-pulse inline-block mr-1"></span>LIVE' : time}
              </p>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-xs font-bold text-gray-500 uppercase tracking-wider">${_esc(m.round_name || 'Round')} · Match ${m.match_number || ''}</p>
              <p class="text-sm font-medium text-white mt-0.5">${m.is_staff_view ? _esc(m.p1_name || 'TBD') + ' vs ' + _esc(m.p2_name || 'TBD') : 'vs ' + _esc(m.opponent_name || 'TBD')}</p>
            </div>
            <div class="text-right shrink-0">
              ${isLive || isCompleted ? `<p class="text-lg font-black text-white" style="font-family:Outfit,sans-serif;">${m.p1_score ?? m.your_score ?? 0} — ${m.p2_score ?? m.opponent_score ?? 0}</p>` : ''}
              ${resultTag}
              ${!isLive && !isCompleted ? `<span class="text-[10px] font-bold uppercase tracking-wider" style="color:${color}">${_esc(m.state_display || m.state)}</span>` : ''}
            </div>
          </div>`;
      });

      html += '</div>';
    }

    if (list) {
      list.innerHTML = html;
      list.classList.remove('hidden');
    }
    if (empty) empty.classList.add('hidden');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // Public helper for refresh button
  function refreshScheduleMatches() {
    _matchesCache = null;
    _fetchScheduleMatches();
  }

  // ──────────────────────────────────────────────────────────
  // Participants Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchParticipants({ reset = false } = {}) {
    const url = _shell?.dataset.apiParticipants;
    if (!url) return;

    if (reset) {
      _participantsPage = 1;
      _participantsHasMore = false;
      _participantsAll = [];
      _participantsCache = null;
      const grid = document.getElementById('participants-grid');
      if (grid) {
        grid.classList.add('hidden');
        grid.innerHTML = '';
      }
      _show('participants-skeleton');
      _hide('participants-no-results');
      _hide('participants-empty');
    }

    try {
      const requestUrl = new URL(url, window.location.origin);
      requestUrl.searchParams.set('page', String(_participantsPage));
      requestUrl.searchParams.set('page_size', String(_participantsPageSize));

      const resp = await fetch(requestUrl.toString(), { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _participantsCache = data;
      const incoming = data.participants || [];
      const existingIds = new Set(_participantsAll.map((p) => p.id));
      incoming.forEach((p) => {
        if (!existingIds.has(p.id)) _participantsAll.push(p);
      });
      _participantsHasMore = Boolean(data.has_more);
      _participantsPage = Number(data.page || _participantsPage);
      _renderParticipants(_participantsAll);
      _updateParticipantsLoadMoreVisibility();
    } catch (err) {
      console.warn('[HubEngine] Participants fetch failed:', err.message);
      _hide('participants-skeleton');
      _show('participants-empty');
      _updateParticipantsLoadMoreVisibility();
    }
  }

  function loadMoreParticipants() {
    const query = document.getElementById('participants-search')?.value?.trim();
    if (query) return;
    if (!_participantsHasMore) return;

    const btn = document.getElementById('participants-load-more-btn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Loading...';
    }

    _participantsPage += 1;
    _fetchParticipants()
      .finally(() => {
        if (btn) {
          btn.disabled = false;
          btn.textContent = 'Load More';
        }
      });
  }

  function _updateParticipantsLoadMoreVisibility() {
    const wrap = document.getElementById('participants-load-more-wrap');
    if (!wrap) return;
    const query = document.getElementById('participants-search')?.value?.trim();
    const shouldShow = _participantsHasMore && !query;
    wrap.classList.toggle('hidden', !shouldShow);
    wrap.classList.toggle('flex', shouldShow);
  }

  function _renderParticipants(list) {
    _hide('participants-skeleton');
    _hide('participants-empty');
    _hide('participants-no-results');

    const grid = document.getElementById('participants-grid');
    if (!grid) return;

    if (!list || list.length === 0) {
      grid.classList.add('hidden');
      _show('participants-empty');
      return;
    }

    // Update count
    const countEl = document.getElementById('participants-count');
    if (countEl && _participantsCache) countEl.textContent = _participantsCache.total;

    const isTeam = _participantsCache?.is_team;
    let html = '';
    list.forEach((p, i) => {
      const youBorder = p.is_you ? ' border-[#00F0FF]/30' : ' border-white/5';
      const youBadge = p.is_you ? `<span class="px-1.5 py-0.5 rounded bg-[#00F0FF]/20 text-[#00F0FF] text-[8px] font-black uppercase ml-1">You</span>` : '';
      const checkedIn = p.checked_in ? '<span class="w-2 h-2 rounded-full bg-[#00FF66] shadow-[0_0_5px_#00FF66] ml-auto shrink-0"></span>' : '';
      const seedBadge = p.seed ? `<span class="text-[10px] text-gray-600 ml-auto">#${p.seed}</span>` : '';
      const memberCount = (isTeam && p.member_count) ? `<p class="text-[10px] text-gray-500 uppercase tracking-widest" style="font-family:'Space Grotesk',monospace;">${p.member_count} Member${p.member_count !== 1 ? 's' : ''}</p>` : '';
      const statusBadge = (!p.verified && p.status_label)
        ? `<span class="px-1.5 py-0.5 rounded bg-[#FFB800]/15 text-[#FFB800] text-[8px] font-black uppercase border border-[#FFB800]/20 ml-1">${_esc(p.status_label)}</span>`
        : '';
      const verifiedBadge = p.verified === true && !p.is_you
        ? '<span class="w-2 h-2 rounded-full bg-[#00F0FF]/40 shrink-0" title="Verified"></span>'
        : '';

      // Stacked member avatars (team mode)
      let avatarStack = '';
      if (isTeam && p.member_avatars && p.member_avatars.length > 0) {
        avatarStack = '<div class="flex -space-x-2 overflow-hidden mt-3">';
        p.member_avatars.forEach(ma => {
          if (ma.avatar_url) {
            avatarStack += `<img class="inline-block h-8 w-8 rounded-full ring-2 ring-[#08080C] object-cover" src="${_esc(ma.avatar_url)}" alt="${_esc(ma.initial)}">`;
          } else {
            avatarStack += `<div class="inline-flex h-8 w-8 rounded-full ring-2 ring-[#08080C] bg-gray-800 items-center justify-center text-[10px] font-bold text-white">${_esc(ma.initial)}</div>`;
          }
        });
        avatarStack += '</div>';
      }

      // Logo / avatar
      const logo = p.logo_url
        ? `<img src="${_esc(p.logo_url)}" class="w-full h-full object-cover" alt="${_esc(p.name)}">`
        : `<span class="font-black text-xl" style="font-family:Outfit,sans-serif;">${_esc(p.tag)}</span>`;
      const logoColorClass = p.is_you ? 'bg-[#00F0FF]/20 text-[#00F0FF]' : 'bg-white/5 text-gray-400';

      // Wrap in link if detail_url exists
      const href = p.detail_url ? ` href="${_esc(p.detail_url)}"` : '';
      const tag = p.detail_url ? 'a' : 'div';
      const unverifiedClass = (p.verified === false) ? ' opacity-80 border-dashed' : '';

      html += `
        <${tag}${href} class="hub-glass p-5 rounded-xl border${youBorder}${unverifiedClass} hover:border-white/20 transition-all group cursor-pointer block" data-participant-name="${_esc(p.name.toLowerCase())}">
          <div class="flex items-center gap-4 mb-1">
            <div class="w-12 h-12 rounded-lg ${logoColorClass} flex items-center justify-center overflow-hidden border border-white/10 shrink-0 group-hover:scale-110 transition-transform">
              ${logo}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-start gap-1 flex-wrap">
                <h3 class="font-bold text-white text-lg group-hover:text-[#00F0FF] transition-colors break-words whitespace-normal leading-tight" style="font-family:Outfit,sans-serif;">${_esc(p.name)}</h3>
                ${youBadge}
                ${statusBadge}
                ${checkedIn}
              </div>
              ${memberCount}
            </div>
          </div>
          ${avatarStack}
        </${tag}>`;
    });

    grid.innerHTML = html;
    grid.classList.remove('hidden');
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function filterParticipants(query) {
    if (!_participantsAll || _participantsAll.length === 0) return;
    const q = (query || '').toLowerCase().trim();

    if (!q) {
      _renderParticipants(_participantsAll);
      _updateParticipantsLoadMoreVisibility();
      return;
    }

    const filtered = _participantsAll.filter(p =>
      p.name.toLowerCase().includes(q) || (p.tag || '').toLowerCase().includes(q)
    );

    if (filtered.length === 0) {
      const grid = document.getElementById('participants-grid');
      if (grid) grid.classList.add('hidden');
      _show('participants-no-results');
    } else {
      _hide('participants-no-results');
      _renderParticipants(filtered);
    }
    _updateParticipantsLoadMoreVisibility();
  }

  // ──────────────────────────────────────────────────────────
  // S27: WebSocket — Real-Time Sync
  // ──────────────────────────────────────────────────────────
  function _connectWebSocket() {
    if (!_shell) return;
    const tid = _shell.dataset.tournamentId;
    if (!tid) { console.warn('[Hub] No tournament ID for WS'); return; }

    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${location.host}/ws/tournament/${tid}/`;

    try {
      _ws = new WebSocket(url);
    } catch (e) {
      console.warn('[Hub] WS failed:', e);
      return;
    }

    _ws.onopen = () => {
      console.info('[Hub] WS connected');
      _wsReconnectAttempts = 0;
      // Add a visual connection indicator
      const ind = document.getElementById('hub-ws-indicator');
      if (ind) { ind.classList.remove('disconnected'); ind.classList.add('connected'); }
    };

    _ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        _handleWsMessage(msg);
      } catch (e) {
        console.warn('[Hub] WS parse error:', e);
      }
    };

    _ws.onclose = (evt) => {
      _ws = null;
      const ind = document.getElementById('hub-ws-indicator');
      if (ind) { ind.classList.remove('connected'); ind.classList.add('disconnected'); }
      // Auto-reconnect with exponential backoff (skip if clean close)
      if (evt.code !== 1000 && _wsReconnectAttempts < WS_RECONNECT_MAX) {
        const delay = WS_RECONNECT_BASE * Math.pow(2, _wsReconnectAttempts);
        _wsReconnectAttempts++;
        if (_wsReconnectAttempts <= 1) {
          console.info(`[Hub] WS closed (${evt.code}), reconnecting in ${delay}ms`);
        }
        _wsReconnectTimer = setTimeout(_connectWebSocket, delay);
      } else if (_wsReconnectAttempts >= WS_RECONNECT_MAX) {
        console.info('[Hub] WS unavailable — live updates disabled (requires ASGI server)');
      }
    };

    _ws.onerror = () => { /* onclose will fire */ };
  }

  function _handleWsMessage(msg) {
    const type = msg.type;
    console.info('[Hub] WS event:', type);

    switch (type) {
      case 'bracket_state':
        // Initial state on connect — prime bracket cache
        if (msg.bracket) {
          _bracketCache = msg.bracket;
        }
        break;

      case 'bracket_update':
        // Invalidate bracket + standings + matches caches
        _bracketCache = null;
        _standingsCache = null;
        _matchesCache = null;
        _refreshActiveTab(['bracket', 'standings', 'matches', 'schedule']);
        break;

      case 'match_completed':
        // Invalidate matches + standings
        _matchesCache = null;
        _standingsCache = null;
        _bracketCache = null;
        _refreshActiveTab(['bracket', 'standings', 'matches', 'schedule']);
        // Show a toast notification
        _showWsToast('Match completed', 'info');
        break;

      case 'match_update':
        _matchesCache = null;
        _refreshActiveTab(['matches', 'schedule']);
        break;

      case 'pong':
        break;

      default:
        // Unknown event — do a general poll refresh
        _pollState();
        break;
    }
  }

  /**
   * If the currently active tab is one of the affected tabs,
   * trigger a re-fetch by calling switchTab logic for that tab.
   */
  function _refreshActiveTab(affectedTabs) {
    if (!_currentTab) return;
    if (affectedTabs.includes(_currentTab)) {
      // Force re-render by clearing the tab and reloading
      const oldTab = _currentTab;
      _currentTab = null;  // allow switchTab to proceed
      switchTab(oldTab);
    }
  }

  /**
   * Lightweight toast notification for WS events.
   */
  function _showWsToast(message, level) {
    let container = document.getElementById('hub-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'hub-toast-container';
      container.style.cssText = 'position:fixed;top:1rem;right:1rem;z-index:9999;display:flex;flex-direction:column;gap:0.5rem;pointer-events:none;';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    const bg = level === 'info' ? '#3b82f6' : level === 'success' ? '#10b981' : '#ef4444';
    toast.style.cssText = `background:${bg};color:#fff;padding:0.75rem 1.25rem;border-radius:0.5rem;font-size:0.875rem;box-shadow:0 4px 12px rgba(0,0,0,0.3);pointer-events:auto;opacity:0;transform:translateX(100%);transition:all 0.3s ease;`;
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => { toast.style.opacity = '1'; toast.style.transform = 'translateX(0)'; });
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      setTimeout(() => toast.remove(), 350);
    }, 4000);
    _announceLiveMessage(message, level === 'error' ? 'assertive' : 'polite');
  }

  // ──────────────────────────────────────────────────────────
  // Cleanup (if SPA navigates away)
  // ──────────────────────────────────────────────────────────
  function destroy() {
    _stopPolling();
    if (_countdownId) clearInterval(_countdownId);
    if (_wsPingId) clearInterval(_wsPingId);
    if (_resizeTimer) clearTimeout(_resizeTimer);

    if (_onKeyDown) document.removeEventListener('keydown', _onKeyDown);
    if (_onWindowResize) window.removeEventListener('resize', _onWindowResize);
    if (_onHashChange) window.removeEventListener('hashchange', _onHashChange);
    if (_onPopState) window.removeEventListener('popstate', _onPopState);
    if (_onVisibilityChange) document.removeEventListener('visibilitychange', _onVisibilityChange);
    document.removeEventListener('click', _handleRetryButtonClick);

    _onKeyDown = null;
    _onWindowResize = null;
    _onHashChange = null;
    _onPopState = null;
    _onVisibilityChange = null;
    _wsPingId = null;
    _resizeTimer = null;

    // S27: Close WebSocket
    if (_wsReconnectTimer) clearTimeout(_wsReconnectTimer);
    if (_ws) { _ws.close(1000); _ws = null; }
  }

  // ──────────────────────────────────────────────────────────
  // Registration Status Modal
  // ──────────────────────────────────────────────────────────
  function showStatusModal() {
    _openModal('hub-status-modal', 'hub-status-modal-title');
  }

  function closeStatusModal() {
    _closeModal('hub-status-modal');
  }

  // ──────────────────────────────────────────────────────────
  // Contact Admin Modal
  // ──────────────────────────────────────────────────────────
  function showContactModal() {
    _openModal('hub-contact-modal', 'hub-contact-modal-title');
  }

  function closeContactModal() {
    _closeModal('hub-contact-modal');
  }

  // ──────────────────────────────────────────────────────────
  // Welcome Guide (first-visit)
  // ──────────────────────────────────────────────────────────
  function _checkWelcomeGuide() {
    const slug = _shell?.dataset.slug || 'default';
    const key = `hub_guide_seen_${slug}`;
    if (!localStorage.getItem(key)) {
      _openModal('hub-welcome-guide', 'hub-welcome-modal-title');
    }
  }

  function dismissGuide() {
    const slug = _shell?.dataset.slug || 'default';
    const key = `hub_guide_seen_${slug}`;
    localStorage.setItem(key, '1');
    _closeModal('hub-welcome-guide');
  }

  // ──────────────────────────────────────────────────────────
  // Support Tab — Category Selection & Form Submission
  // ──────────────────────────────────────────────────────────
  let _supportCategory = 'general';

  function _isCriticalLocked() {
    return _shell?.dataset?.criticalLocked === 'true';
  }

  function _isTabLocked(tabId) {
    const normalizedTab = _normalizeTab(tabId);
    return Boolean(normalizedTab && _isCriticalLocked() && LOCKED_TABS_WHEN_UNVERIFIED.has(normalizedTab));
  }

  function _tabLabel(tabId) {
    const navLabel = document.querySelector(`.hub-nav-btn[data-hub-tab="${tabId}"] > div span:last-child`);
    if (navLabel?.textContent?.trim()) return navLabel.textContent.trim();
    return String(tabId || 'Locked tab')
      .replace(/[-_]+/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function _getLockReason() {
    return (_shell?.dataset?.lockReason || '').trim() || 'Action is locked until payment verification is complete.';
  }

  function _showLockToast() {
    if (window.showToast) {
      window.showToast({ type: 'warning', message: _getLockReason() });
    }
    _announceLiveMessage(_getLockReason(), 'assertive');
  }

  function _applyTabLockState(tabId, { announce = false } = {}) {
    const viewport = document.getElementById('hub-viewport');
    const overlay = document.getElementById('hub-tab-lock-overlay');
    const overlayPanel = document.querySelector('#hub-tab-lock-overlay .hub-tab-lock-overlay-panel');
    const titleEl = document.getElementById('hub-lock-overlay-title');
    const messageEl = document.getElementById('hub-lock-overlay-message');
    const chipEl = document.getElementById('hub-lock-tab-chip');
    const activeTab = document.getElementById('hub-tab-' + tabId);

    document.querySelectorAll('.hub-tab-content').forEach((el) => {
      el.classList.remove('is-lock-blurred');
      if (el.hasAttribute('inert')) el.removeAttribute('inert');
      el.setAttribute('aria-hidden', 'false');
    });

    const isLockedTab = _isTabLocked(tabId);

    if (viewport) {
      viewport.classList.toggle('hub-tab-locked-state', isLockedTab);
    }

    if (overlay) {
      overlay.classList.toggle('active', isLockedTab);
      overlay.setAttribute('aria-hidden', isLockedTab ? 'false' : 'true');
      if (!isLockedTab) {
        _detachModalFocusTrap(overlay);
      }
    }

    if (!isLockedTab) return;

    if (activeTab) {
      activeTab.classList.add('is-lock-blurred');
      activeTab.setAttribute('inert', '');
      activeTab.setAttribute('aria-hidden', 'true');
    }

    const tabLabel = _tabLabel(tabId);
    if (chipEl) chipEl.textContent = tabLabel;
    if (titleEl) titleEl.textContent = `${tabLabel} unlocks after verification`;
    if (messageEl) messageEl.textContent = _getLockReason();

    if (overlay) {
      _attachModalFocusTrap(overlay);
    }
    if (overlayPanel) {
      const focusables = _getFocusableElements(overlayPanel);
      if (focusables.length) {
        focusables[0].focus();
      } else {
        overlayPanel.setAttribute('tabindex', '-1');
        overlayPanel.focus();
      }
    }

    if (announce) {
      _showLockToast();
    }
  }

  async function _fetchSupportTickets({ reset = false } = {}) {
    const url = _shell?.dataset.apiSupport;
    if (!url) return;

    if (reset) {
      _supportTicketsPage = 1;
      _supportTicketsHasMore = false;
    }

    try {
      const requestUrl = new URL(url, window.location.origin);
      requestUrl.searchParams.set('page', String(_supportTicketsPage));
      requestUrl.searchParams.set('page_size', String(_supportTicketsPageSize));

      const resp = await fetch(requestUrl.toString(), { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _supportTicketsHasMore = Boolean(data.has_more);
      _supportTicketsPage = Number(data.page || _supportTicketsPage);
      _renderSupportTickets(data.tickets || [], { append: !reset, hasMore: _supportTicketsHasMore });
      _supportTicketsLoaded = true;
    } catch (err) {
      console.warn('[HubEngine] Support tickets fetch failed:', err.message);
      const list = document.getElementById('support-tickets-list');
      if (list) {
        list.innerHTML = `
          <div class="text-center py-8">
            <i data-lucide="triangle-alert" class="w-8 h-8 text-[#FFB800] mx-auto mb-2"></i>
            <p class="text-xs text-gray-400">Could not load ticket history</p>
            <p class="text-[10px] text-gray-600 mt-1">New submissions will still be sent successfully.</p>
          </div>`;
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
      _toggleSupportLoadMore(false);
    }
  }

  function _renderSupportTickets(tickets, { append = false, hasMore = false } = {}) {
    const list = document.getElementById('support-tickets-list');
    if (!list) return;

    if (!tickets.length) {
      if (!append) {
        list.innerHTML = `
        <div class="text-center py-8">
          <i data-lucide="inbox" class="w-8 h-8 text-gray-700 mx-auto mb-2"></i>
          <p class="text-xs text-gray-500">No support tickets yet</p>
          <p class="text-[10px] text-gray-600 mt-1">Tickets you submit will appear here</p>
        </div>`;
      }
      _toggleSupportLoadMore(false);
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    const statusClassMap = {
      open: 'bg-[#FFB800]/12 border-[#FFB800]/20 text-[#FFB800]',
      in_review: 'bg-[#00F0FF]/12 border-[#00F0FF]/20 text-[#00F0FF]',
      resolved: 'bg-[#00FF66]/12 border-[#00FF66]/20 text-[#00FF66]',
      closed: 'bg-white/10 border-white/15 text-gray-300',
    };

    const html = tickets.map((ticket) => {
      const badgeClass = statusClassMap[ticket.status] || statusClassMap.open;
      return `
        <div class="p-4 rounded-xl border border-white/8 bg-white/[0.02] mb-3">
          <div class="flex items-center justify-between gap-2 mb-2">
            <span class="text-[10px] font-black uppercase tracking-widest text-[var(--game-primary)]">${_esc(ticket.category_display || 'Support')}</span>
            <span class="text-[10px] text-gray-600">${_esc(ticket.time_ago || '')}</span>
          </div>
          <p class="text-sm font-bold text-white">${_esc(ticket.subject || '')}</p>
          ${ticket.match_ref ? `<p class="text-[10px] text-[#FFB800] mt-1">Match: ${_esc(ticket.match_ref)}</p>` : ''}
          <p class="text-xs text-gray-400 mt-2 leading-relaxed">${_esc(ticket.message || '')}</p>
          <div class="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wide ${badgeClass}">${_esc(ticket.status_display || 'Open')}</div>
        </div>`;
    }).join('');

    if (append) {
      list.insertAdjacentHTML('beforeend', html);
    } else {
      list.innerHTML = html;
    }
    _toggleSupportLoadMore(hasMore);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function _toggleSupportLoadMore(show) {
    const wrap = document.getElementById('support-load-more-wrap');
    if (!wrap) return;
    wrap.classList.toggle('hidden', !show);
    wrap.classList.toggle('flex', show);
  }

  function loadMoreSupportTickets() {
    if (!_supportTicketsHasMore) return;
    const btn = document.getElementById('support-load-more-btn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Loading...';
    }
    _supportTicketsPage += 1;
    _fetchSupportTickets()
      .finally(() => {
        if (btn) {
          btn.disabled = false;
          btn.textContent = 'Load More Tickets';
        }
      });
  }

  function selectSupportCategory(category) {
    _supportCategory = category;

    // Update active state
    document.querySelectorAll('.support-category-btn').forEach(btn => {
      if (btn.dataset.category === category) {
        btn.classList.add('active');
        btn.setAttribute('aria-pressed', 'true');
      } else {
        btn.classList.remove('active');
        btn.setAttribute('aria-pressed', 'false');
      }
    });

    // Show/hide dispute-specific fields
    const disputeFields = document.getElementById('support-dispute-fields');
    if (disputeFields) {
      disputeFields.classList.toggle('hidden', category !== 'dispute');
    }
  }

  function _updateCharCount() {
    const msg = document.getElementById('support-message');
    const counter = document.getElementById('support-char-count');
    if (msg && counter) {
      counter.textContent = `${msg.value.length} / 2000`;
    }
  }

  // Attach char count listener on first support tab visit
  function _initSupportForm() {
    const msg = document.getElementById('support-message');
    if (msg && !msg._charCountBound) {
      msg.addEventListener('input', _updateCharCount);
      msg._charCountBound = true;
    }
    _updateCharCount();
    if (!_supportCategory) _supportCategory = 'general';
    selectSupportCategory(_supportCategory);
  }

  function _appendSupportTicketPreview(ticket) {
    if (!ticket) return;
    _fetchSupportTickets({ reset: true });
  }

  async function submitSupportRequest() {
    const url = _shell?.dataset.apiSupport;
    const subject = document.getElementById('support-subject')?.value?.trim();
    const message = document.getElementById('support-message')?.value?.trim();
    const matchRef = document.getElementById('support-match-ref')?.value?.trim() || '';
    const errEl = document.getElementById('support-error');
    const okEl = document.getElementById('support-success');
    const btn = document.getElementById('support-submit-btn');

    // Reset states
    if (errEl) errEl.classList.add('hidden');
    if (okEl) okEl.classList.add('hidden');

    // Validate
    if (!subject) {
      if (errEl) { errEl.textContent = 'Please enter a subject.'; errEl.classList.remove('hidden'); }
      _announceLiveMessage('Please enter a subject.', 'assertive');
      return;
    }
    if (!message || message.length < 10) {
      if (errEl) { errEl.textContent = 'Please write a more detailed message (at least 10 characters).'; errEl.classList.remove('hidden'); }
      _announceLiveMessage('Please write a more detailed message.', 'assertive');
      return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Sending...'; }

    try {
      if (!url) throw new Error('Support endpoint not available');

      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': _csrfToken,
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          category: _supportCategory,
          subject: subject,
          message: message,
          match_ref: matchRef,
        }),
      });

      const data = await resp.json();

      if (data.success) {
        if (okEl) { okEl.textContent = data.message || 'Your message has been sent to the organizer.'; okEl.classList.remove('hidden'); }
        _announceLiveMessage(data.message || 'Support request sent successfully.', 'polite');
        if (data.ticket) {
          _appendSupportTicketPreview(data.ticket);
        } else {
          _fetchSupportTickets({ reset: true });
        }
        // Clear form
        const subj = document.getElementById('support-subject');
        const msg = document.getElementById('support-message');
        const ref = document.getElementById('support-match-ref');
        if (subj) subj.value = '';
        if (msg) msg.value = '';
        if (ref) ref.value = '';
        _updateCharCount();
      } else {
        if (errEl) { errEl.textContent = data.error || 'Failed to send message.'; errEl.classList.remove('hidden'); }
        _announceLiveMessage(data.error || 'Failed to send support message.', 'assertive');
      }
    } catch (err) {
      console.error('[HubEngine] Support submit error:', err);
      if (errEl) { errEl.textContent = 'Network error. Please try again or contact the organizer directly.'; errEl.classList.remove('hidden'); }
      _announceLiveMessage('Network error. Please try again later.', 'assertive');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="send" class="w-4 h-4"></i> Send Message';
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    }
  }

  // ── Public API ──────────────────────────────────────────
  return {
    init,
    destroy,
    switchTab,
    performCheckIn,
    openMobileSidebar,
    closeMobileSidebar,
    swapToSub,
    swapToStarter,
    bracketZoom,
    bracketReset,
    // Module 5: Bounty Board
    openPrizeModal,
    closePrizeModal,
    submitPrizeClaim,
    // Module 9: Participants
    filterParticipants,
    loadMoreParticipants,
    // Module 10: Contact & Guide
    showContactModal,
    closeContactModal,
    // Module 11: Status Detail
    showStatusModal,
    closeStatusModal,
    dismissGuide,
    // Module 12: Support & Disputes
    selectSupportCategory,
    submitSupportRequest,
    loadMoreSupportTickets,
    // S27: WebSocket status
    isWsConnected: () => _ws && _ws.readyState === WebSocket.OPEN,
    refreshScheduleMatches,
    // Map viewer
    openMapViewer,
    closeMapViewer,
    retryAction: _runRetryAction,
  };
})();
