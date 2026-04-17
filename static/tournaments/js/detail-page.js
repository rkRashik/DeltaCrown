/**
 * Tournament Detail Page — Extracted JavaScript
 * Shared JS for _base_detail.html and all phase templates.
 * Toast notifications, countdown timer, lucide init.
 */

(function () {
  'use strict';

  /* ==========================================================
     TOAST NOTIFICATION
     Uses the #dc-toast / #dc-toast-msg elements in the template.
     ========================================================== */
  window.showToast = function (msg, duration) {
    duration = duration || 2500;
    var el = document.getElementById('dc-toast');
    var msgEl = document.getElementById('dc-toast-msg');
    if (!el || !msgEl) return;
    msgEl.textContent = msg;
    el.classList.add('show');
    setTimeout(function () { el.classList.remove('show'); }, duration);
  };

  /* ==========================================================
     COUNTDOWN TIMER
     ========================================================== */
  window.initCountdown = function (targetISO, containerId) {
    if (!targetISO) return;
    var target = new Date(targetISO).getTime();
    var container = document.getElementById(containerId);
    if (!container) return;

    function update() {
      var now = Date.now();
      var diff = target - now;
      if (diff <= 0) {
        container.innerHTML = '<span class="text-lg font-bold text-game-accent uppercase tracking-wider">Time\'s Up!</span>';
        return;
      }
      var d = Math.floor(diff / 86400000);
      var h = Math.floor((diff % 86400000) / 3600000);
      var m = Math.floor((diff % 3600000) / 60000);
      var s = Math.floor((diff % 60000) / 1000);

      container.innerHTML =
        '<div class="flex items-center gap-3 sm:gap-4">'
        + '<div class="text-center"><div class="countdown-digit">' + String(d).padStart(2, '0') + '</div><div class="countdown-label">Days</div></div>'
        + '<span class="text-2xl text-white/20 font-bold -mt-5">:</span>'
        + '<div class="text-center"><div class="countdown-digit">' + String(h).padStart(2, '0') + '</div><div class="countdown-label">Hours</div></div>'
        + '<span class="text-2xl text-white/20 font-bold -mt-5">:</span>'
        + '<div class="text-center"><div class="countdown-digit">' + String(m).padStart(2, '0') + '</div><div class="countdown-label">Mins</div></div>'
        + '<span class="text-2xl text-white/20 font-bold -mt-5">:</span>'
        + '<div class="text-center"><div class="countdown-digit">' + String(s).padStart(2, '0') + '</div><div class="countdown-label">Secs</div></div>'
        + '</div>';
    }
    update();
    setInterval(update, 1000);
  };

  function _statusClassFromKey(statusKey) {
    var key = String(statusKey || '').toLowerCase();
    if (key === 'live') return 'dc-mobile-status-live';
    if (key === 'registration_open') return 'dc-mobile-status-open';
    if (key === 'completed' || key === 'archived') return 'dc-mobile-status-completed';
    if (key === 'cancelled') return 'dc-mobile-status-cancelled';
    return 'dc-mobile-status-upcoming';
  }

  function _matchStatusClass(statusKey) {
    var key = String(statusKey || '').toLowerCase();
    if (key === 'live') return 'dc-mobile-match-status-live';
    if (key === 'completed') return 'dc-mobile-match-status-completed';
    return 'dc-mobile-match-status-upcoming';
  }

  function _matchStatusLabel(statusKey) {
    var key = String(statusKey || '').toLowerCase();
    if (key === 'live') return 'Live';
    if (key === 'completed') return 'Completed';
    return 'Upcoming';
  }

  function _renderMobileSkeleton(panel) {
    if (!panel) return;
    panel.innerHTML = (
      '<div class="dc-mobile-skeleton-wrap" aria-hidden="true">'
      + '<div class="dc-mobile-skeleton-row"></div>'
      + '<div class="dc-mobile-skeleton-row"></div>'
      + '<div class="dc-mobile-skeleton-row"></div>'
      + '</div>'
    );
  }

  function _hydrateLucide(rootEl) {
    if (!rootEl || typeof window === 'undefined' || !window.lucide || !window.lucide.icons) return;

    var iconNodes = rootEl.querySelectorAll('[data-lucide]');
    Array.prototype.forEach.call(iconNodes, function (node) {
      var iconName = node.getAttribute('data-lucide');
      if (!iconName) return;

      var iconDef = window.lucide.icons[iconName];
      if (!iconDef || typeof iconDef.toSvg !== 'function') return;

      var cssClass = node.getAttribute('class') || '';
      var svgMarkup = iconDef.toSvg({ class: cssClass });
      if (!svgMarkup) return;

      var wrapper = document.createElement('span');
      wrapper.innerHTML = svgMarkup;
      var svgEl = wrapper.firstElementChild;
      if (!svgEl) return;

      node.replaceWith(svgEl);
    });
  }

  function _initLucideIcons() {
    if (typeof window === 'undefined' || typeof window.lucide === 'undefined') return;

    var isMobileViewport = window.matchMedia && window.matchMedia('(max-width: 1023px)').matches;
    var mobileRoot = document.getElementById('dc-mobile-detail');

    if (isMobileViewport && mobileRoot) {
      _hydrateLucide(mobileRoot);
      return;
    }

    if (typeof lucide.createIcons === 'function') {
      lucide.createIcons();
    }
  }

  function _initMobileDetail() {
    var root = document.getElementById('dc-mobile-detail');
    if (!root) return;
    if (root.getAttribute('data-detail-init') === '1') return;
    root.setAttribute('data-detail-init', '1');

    var hero = document.getElementById('dc-mobile-hero');
    var mobileHeader = document.getElementById('dc-mobile-header');
    var mobileViewportQuery = window.matchMedia ? window.matchMedia('(max-width: 1023px)') : null;
    var tabButtons = Array.prototype.slice.call(root.querySelectorAll('[data-mobile-tab]'));
    var panelEls = Array.prototype.slice.call(root.querySelectorAll('[data-mobile-panel]'));
    var panelMap = {};
    panelEls.forEach(function (panel) {
      panelMap[panel.getAttribute('data-mobile-panel')] = panel;
    });

    var loadedTabs = new Set();
    var loadingTabs = new Set();
    var tabLoadCallbacks = {};
    var tabScrollPositions = {};
    var tabOrder = [];
    tabButtons.forEach(function (btn) {
      tabOrder.push(btn.getAttribute('data-mobile-tab'));
    });
    var activeTab = tabOrder[0] || 'overview';
    var sheetOpenCount = 0;
    var pollInFlight = false;
    var pollTimerId = null;
    var stickyOffsetRafId = null;

    function setTextById(id, value) {
      var el = document.getElementById(id);
      if (!el) return;
      el.textContent = value == null ? '' : String(value);
    }

    function toggleSlotsFast(showFast) {
      var indicator = document.getElementById('dc-mobile-slots-fast');
      if (!indicator) return;
      indicator.classList.toggle('hidden', !Boolean(showFast));
    }

    function applyStatusBadge(statusKey, statusLabel) {
      var badge = document.getElementById('dc-mobile-status-badge');
      if (!badge) return;

      badge.classList.remove(
        'dc-mobile-status-live',
        'dc-mobile-status-open',
        'dc-mobile-status-completed',
        'dc-mobile-status-cancelled',
        'dc-mobile-status-upcoming'
      );
      badge.classList.add(_statusClassFromKey(statusKey));
      badge.textContent = statusLabel || _matchStatusLabel(statusKey);
    }

    function applyCta(cta) {
      var ctaBtn = document.getElementById('dc-mobile-cta-button');
      if (!ctaBtn || !cta) return;

      var label = cta.label || ctaBtn.textContent;
      var kind = cta.kind || ctaBtn.getAttribute('data-cta-kind') || 'disabled';
      var disabled = Boolean(cta.disabled);

      ctaBtn.textContent = label;
      ctaBtn.setAttribute('data-cta-kind', kind);
      ctaBtn.classList.toggle('is-disabled', disabled);

      if (ctaBtn.tagName === 'A') {
        if (cta.url) {
          ctaBtn.setAttribute('href', cta.url);
        } else {
          ctaBtn.removeAttribute('href');
        }
      }

      if (disabled) {
        ctaBtn.setAttribute('aria-disabled', 'true');
      } else {
        ctaBtn.removeAttribute('aria-disabled');
      }
    }

    function applyMatchState(rows) {
      if (!Array.isArray(rows)) return;
      rows.forEach(function (row) {
        if (!row || row.id == null) return;
        var id = String(row.id);
        var statusKey = String(row.status || '').toLowerCase();

        var statusEl = document.getElementById('dc-mobile-match-status-' + id);
        if (statusEl) {
          statusEl.classList.remove(
            'dc-mobile-match-status-live',
            'dc-mobile-match-status-completed',
            'dc-mobile-match-status-upcoming'
          );
          statusEl.classList.add(_matchStatusClass(statusKey));
          statusEl.textContent = row.status_label || _matchStatusLabel(statusKey);
        }

        var scoreEl = document.getElementById('dc-mobile-match-score-' + id);
        if (scoreEl) {
          scoreEl.textContent = row.score_text || scoreEl.textContent;
        }

        var timeEl = document.getElementById('dc-mobile-match-time-' + id);
        if (timeEl && row.starts_at_relative) {
          timeEl.textContent = row.starts_at_relative;
        }

        var card = root.querySelector('[data-mobile-match-id="' + id + '"]');
        if (card) {
          if (row.status) card.setAttribute('data-mobile-match-status', row.status);
          if (row.score_text) card.setAttribute('data-mobile-match-score', row.score_text);
          if (row.starts_at_display) card.setAttribute('data-mobile-match-time', row.starts_at_display);
        }
      });
    }

    function applyStatePayload(payload) {
      if (!payload) return;

      setTextById('dc-mobile-status-primary', payload.status_label || 'Upcoming');
      setTextById('dc-mobile-status-context', payload.status_context || 'Awaiting schedule');
      applyStatusBadge(payload.status_key, payload.status_label);

      if (payload.slots_filled != null && payload.slots_total != null) {
        var slotsLabel = String(payload.slots_filled) + '/' + String(payload.slots_total);
        setTextById('dc-mobile-chip-slots-value', slotsLabel);
        setTextById('dc-mobile-sheet-slots-filled', payload.slots_filled);
        setTextById('dc-mobile-sheet-slots-total', payload.slots_total);

        var slotsBar = document.getElementById('dc-mobile-sheet-slots-bar');
        if (slotsBar) {
          slotsBar.style.width = String(payload.slots_percentage || 0) + '%';
        }
      }

      if (payload.start_display) {
        setTextById('dc-mobile-chip-start-value', payload.start_display);
      }

      toggleSlotsFast(Boolean(payload.slots_filling_fast));
      applyCta(payload.cta || null);
      applyMatchState(payload.matches || []);
    }

    function syncTabStickyOffset() {
      if (!mobileHeader) {
        root.style.removeProperty('--dc-mobile-tab-top');
        return;
      }

      var headerRect = mobileHeader.getBoundingClientRect();
      var topOffset = Math.max(0, Math.round(headerRect.bottom));
      root.style.setProperty('--dc-mobile-tab-top', String(topOffset) + 'px');
    }

    function scheduleTabStickyOffsetSync() {
      if (stickyOffsetRafId !== null) return;
      stickyOffsetRafId = window.requestAnimationFrame(function () {
        stickyOffsetRafId = null;
        syncTabStickyOffset();
      });
    }

    function getScrollY() {
      return window.scrollY || window.pageYOffset || document.documentElement.scrollTop || 0;
    }

    function queueTabLoadCallback(tabName, callback) {
      if (typeof callback !== 'function') return;
      if (!tabLoadCallbacks[tabName]) {
        tabLoadCallbacks[tabName] = [];
      }
      tabLoadCallbacks[tabName].push(callback);
    }

    function flushTabLoadCallbacks(tabName) {
      var callbacks = tabLoadCallbacks[tabName] || [];
      delete tabLoadCallbacks[tabName];
      callbacks.forEach(function (callback) {
        try {
          callback();
        } catch (error) {
          // Ignore callback errors to keep tab activation resilient.
        }
      });
    }

    function ensureTabLoaded(tabName, callback) {
      queueTabLoadCallback(tabName, callback);

      var panel = panelMap[tabName];
      if (!panel) return;

      if (loadedTabs.has(tabName)) {
        flushTabLoadCallbacks(tabName);
        return;
      }

      if (loadingTabs.has(tabName)) return;

      loadingTabs.add(tabName);
      panel.classList.add('is-loading');
      panel.setAttribute('aria-busy', 'true');

      _renderMobileSkeleton(panel);

      window.requestAnimationFrame(function () {
        var template = document.getElementById('dc-mobile-template-' + tabName);
        panel.innerHTML = '';
        if (template && template.content) {
          panel.appendChild(template.content.cloneNode(true));
        }

        _hydrateLucide(panel);

        panel.classList.remove('is-loading');
        panel.removeAttribute('aria-busy');
        panel.setAttribute('data-mobile-loaded', 'true');
        loadingTabs.delete(tabName);
        loadedTabs.add(tabName);
        flushTabLoadCallbacks(tabName);
      });
    }

    function activateTab(tabName) {
      if (!panelMap[tabName]) return;
      if (tabName === activeTab && loadedTabs.has(tabName)) return;

      var previousTab = activeTab;
      if (panelMap[previousTab]) {
        tabScrollPositions[previousTab] = getScrollY();
      }

      activeTab = tabName;

      tabButtons.forEach(function (button) {
        var isActive = button.getAttribute('data-mobile-tab') === tabName;
        button.classList.toggle('active', isActive);
        button.setAttribute('aria-selected', isActive ? 'true' : 'false');
      });

      panelEls.forEach(function (panel) {
        var isTarget = panel.getAttribute('data-mobile-panel') === tabName;
        panel.classList.toggle('active', isTarget);
        panel.setAttribute('aria-hidden', isTarget ? 'false' : 'true');
      });

      ensureTabLoaded(tabName, function () {
        var targetY = Object.prototype.hasOwnProperty.call(tabScrollPositions, tabName)
          ? tabScrollPositions[tabName]
          : 0;
        window.requestAnimationFrame(function () {
          window.scrollTo(0, targetY);
        });
      });
    }

    tabButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        activateTab(button.getAttribute('data-mobile-tab'));
      });
    });

    var touchStartX = 0;
    var touchStartY = 0;
    var panelsWrap = document.getElementById('dc-mobile-panels');
    if (panelsWrap) {
      panelsWrap.addEventListener('touchstart', function (event) {
        var first = event.changedTouches && event.changedTouches[0];
        if (!first) return;
        touchStartX = first.clientX;
        touchStartY = first.clientY;
      }, { passive: true });

      panelsWrap.addEventListener('touchend', function (event) {
        var first = event.changedTouches && event.changedTouches[0];
        if (!first) return;
        var dx = first.clientX - touchStartX;
        var dy = first.clientY - touchStartY;
        if (Math.abs(dx) < 56 || Math.abs(dx) < Math.abs(dy)) return;

        var currentIndex = tabOrder.indexOf(activeTab);
        if (dx < 0 && currentIndex < tabOrder.length - 1) {
          activateTab(tabOrder[currentIndex + 1]);
        } else if (dx > 0 && currentIndex > 0) {
          activateTab(tabOrder[currentIndex - 1]);
        }
      }, { passive: true });
    }

    function openSheet(sheetId) {
      if (!sheetId) return;
      var sheet = document.getElementById(sheetId);
      if (!sheet) return;
      if (!sheet.classList.contains('is-open')) {
        sheet.classList.add('is-open');
        sheet.setAttribute('aria-hidden', 'false');
        sheetOpenCount += 1;
      }
      document.body.style.overflow = 'hidden';
    }

    function closeSheet(sheet) {
      if (!sheet || !sheet.classList.contains('is-open')) return;
      sheet.classList.remove('is-open');
      sheet.setAttribute('aria-hidden', 'true');
      sheetOpenCount = Math.max(0, sheetOpenCount - 1);
      if (sheetOpenCount === 0) {
        document.body.style.overflow = '';
      }
    }

    function closeAllSheets() {
      var openSheets = root.querySelectorAll('.dc-mobile-sheet.is-open');
      openSheets.forEach(function (sheet) {
        closeSheet(sheet);
      });
    }

    function populateMatchSheet(trigger) {
      if (!trigger) return;
      setTextById('dc-mobile-match-sheet-title', trigger.getAttribute('data-mobile-match-title') || 'Match Detail');
      setTextById('dc-mobile-match-sheet-stage', trigger.getAttribute('data-mobile-match-stage') || '-');
      setTextById('dc-mobile-match-sheet-status', _matchStatusLabel(trigger.getAttribute('data-mobile-match-status')));
      setTextById('dc-mobile-match-sheet-score', trigger.getAttribute('data-mobile-match-score') || '-');
      setTextById('dc-mobile-match-sheet-time', trigger.getAttribute('data-mobile-match-time') || '-');

      var link = document.getElementById('dc-mobile-match-sheet-link');
      if (link) {
        var href = trigger.getAttribute('data-mobile-match-link') || '#';
        link.setAttribute('href', href);
      }
    }

    root.addEventListener('click', function (event) {
      var closeTrigger = event.target.closest('[data-mobile-sheet-close]');
      if (closeTrigger) {
        var sheet = closeTrigger.closest('.dc-mobile-sheet');
        closeSheet(sheet);
        return;
      }

      var matchTrigger = event.target.closest('[data-mobile-match-open]');
      if (matchTrigger) {
        populateMatchSheet(matchTrigger);
        openSheet('dc-mobile-sheet-match');
        return;
      }

      var openTrigger = event.target.closest('[data-mobile-sheet-open]');
      if (openTrigger) {
        var targetSheet = openTrigger.getAttribute('data-mobile-sheet-open');
        openSheet(targetSheet);
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        closeAllSheets();
      }
    });

    if (hero) {
      hero.classList.remove('is-collapsed');
    }

    window.addEventListener('scroll', scheduleTabStickyOffsetSync, { passive: true });
    window.addEventListener('resize', scheduleTabStickyOffsetSync, { passive: true });
    window.addEventListener('orientationchange', scheduleTabStickyOffsetSync);

    if (mobileHeader) {
      mobileHeader.addEventListener('transitionend', scheduleTabStickyOffsetSync);
    }

    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', scheduleTabStickyOffsetSync);
      window.visualViewport.addEventListener('scroll', scheduleTabStickyOffsetSync);
    }

    scheduleTabStickyOffsetSync();

    function isPollingEligible() {
      if (document.hidden) return false;
      if (!root.isConnected) return false;
      if (window.getComputedStyle(root).display === 'none') return false;
      if (mobileViewportQuery && !mobileViewportQuery.matches) return false;
      return true;
    }

    function stopPolling() {
      if (!pollTimerId) return;
      clearInterval(pollTimerId);
      pollTimerId = null;
    }

    function startPolling() {
      if (pollTimerId || !isPollingEligible()) return;
      pollState();
      pollTimerId = setInterval(function () {
        if (!isPollingEligible()) {
          stopPolling();
          return;
        }
        pollState();
      }, 20000);
    }

    function handleVisibilityChange() {
      if (document.hidden) {
        stopPolling();
      } else {
        startPolling();
      }
    }

    function handleViewportChange() {
      if (isPollingEligible()) {
        startPolling();
      } else {
        stopPolling();
      }
      scheduleTabStickyOffsetSync();
    }

    async function pollState() {
      var stateUrl = root.getAttribute('data-state-url');
      if (!stateUrl || pollInFlight) return;
      pollInFlight = true;
      try {
        var response = await fetch(stateUrl, {
          credentials: 'same-origin',
          headers: {
            'Accept': 'application/json',
          },
        });
        if (!response.ok) return;
        var payload = await response.json();
        applyStatePayload(payload);
      } catch (error) {
        // Fail silently to keep the detail page usable on unstable networks.
      } finally {
        pollInFlight = false;
      }
    }

    activateTab(activeTab);
    startPolling();

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('pagehide', stopPolling);
    window.addEventListener('beforeunload', stopPolling);

    if (mobileViewportQuery) {
      if (typeof mobileViewportQuery.addEventListener === 'function') {
        mobileViewportQuery.addEventListener('change', handleViewportChange);
      } else if (typeof mobileViewportQuery.addListener === 'function') {
        mobileViewportQuery.addListener(handleViewportChange);
      }
    }
  }

  /* ==========================================================
     DETAIL PAGE BRACKET RENDERER
     Renders window.__detailBracketData into #detail-bracket-tree
     ========================================================== */
  var _bracketScale = 1;
  var _BRACKET_SCALE_STEP = 0.15;
  var _BRACKET_SCALE_MIN = 0.5;
  var _BRACKET_SCALE_MAX = 1.8;

  window.detailBracketZoom = function (dir) {
    var tree = document.getElementById('detail-bracket-tree');
    if (!tree) return;
    if (dir === 0) {
      _bracketScale = 1;
    } else {
      _bracketScale = Math.min(_BRACKET_SCALE_MAX, Math.max(_BRACKET_SCALE_MIN, _bracketScale + dir * _BRACKET_SCALE_STEP));
    }
    tree.style.transform = 'scale(' + _bracketScale + ')';
  };

  function _esc(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function _avatarHTML(name, logoUrl) {
    var initial = (name || '?').charAt(0).toUpperCase();
    if (logoUrl) {
      return '<img src="' + _esc(logoUrl) + '" class="db-avatar" alt="" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'\'">'
           + '<div class="db-avatar db-avatar-fb" style="display:none">' + initial + '</div>';
    }
    return '<div class="db-avatar db-avatar-fb">' + initial + '</div>';
  }

  function _renderDetailBracket() {
    var data = window.__detailBracketData;
    if (!data || !data.matches || !data.matches.length) return;
    var tree = document.getElementById('detail-bracket-tree');
    if (!tree) return;

    // Group by round
    var rounds = {};
    var roundOrder = [];
    data.matches.forEach(function (m) {
      var rn = m.round_number || 0;
      if (!rounds[rn]) {
        rounds[rn] = { label: m.round_label || ('Round ' + rn), matches: [] };
        roundOrder.push(rn);
      }
      rounds[rn].matches.push(m);
    });
    roundOrder.sort(function (a, b) { return a - b; });

    // Determine friendly round names for single-elimination
    var totalRounds = roundOrder.length;
    roundOrder.forEach(function (rn, idx) {
      var r = rounds[rn];
      var fromEnd = totalRounds - 1 - idx;
      if (!r.label || r.label === 'Round ' + rn) {
        if (fromEnd === 0) r.label = r.matches.length === 1 ? 'Grand Final' : 'Finals';
        else if (fromEnd === 1 && r.matches.length <= 2) r.label = 'Semifinals';
        else if (fromEnd === 2 && r.matches.length <= 4) r.label = 'Quarterfinals';
      }
    });

    var html = '';
    roundOrder.forEach(function (rn) {
      var r = rounds[rn];
      html += '<div class="db-col">';
      html += '<div class="db-col-title">' + _esc(r.label) + '</div>';
      html += '<div class="db-col-body">';
      r.matches.forEach(function (m) {
        var isLive = m.is_live;
        var isDone = m.state === 'completed' || m.state === 'forfeit';
        var isPending = !isLive && !isDone;
        var isTBD = isPending && (!m.p1_name || m.p1_name === 'TBD') && (!m.p2_name || m.p2_name === 'TBD');
        var stateCls = isLive ? ' db-live' : isDone ? ' db-done' : isTBD ? ' db-tbd' : ' db-sched';
        var matchNum = m.match_number ? 'M' + m.match_number : '';

        // State badge
        var badge = '';
        if (isLive) badge = '<span class="db-badge-live"><span class="db-dot"></span> LIVE</span>';
        else if (isDone) badge = '<span class="db-badge-ft">FT</span>';
        else if (m.state === 'check_in') badge = '<span class="db-badge-up">CHECK IN</span>';
        else if (isTBD) badge = '<span class="db-badge-up db-badge-tbd">TBD</span>';
        else badge = '<span class="db-badge-up">UPCOMING</span>';

        // Player rows
        var p1cls = m.p1_winner ? ' db-w' : (isDone && !m.p1_winner ? ' db-loser' : '');
        var p2cls = m.p2_winner ? ' db-w' : (isDone && !m.p2_winner ? ' db-loser' : '');
        var s1 = m.p1_score != null ? m.p1_score : (isPending ? '–' : '-');
        var s2 = m.p2_score != null ? m.p2_score : (isPending ? '–' : '-');

        html += '<div class="db-match' + stateCls + '">';
        html += '<div class="db-match-head"><span class="db-mnum">' + matchNum + '</span>' + badge + '</div>';
        html += '<div class="db-team' + p1cls + '"><div class="db-team-meta">' + _avatarHTML(m.p1_name, m.p1_logo)
              + '<span class="db-name">' + _esc(m.p1_name || 'TBD') + '</span></div><span class="db-sc">' + s1 + '</span></div>';
        html += '<div class="db-vs">VS</div>';
        html += '<div class="db-team' + p2cls + '"><div class="db-team-meta">' + _avatarHTML(m.p2_name, m.p2_logo)
              + '<span class="db-name">' + _esc(m.p2_name || 'TBD') + '</span></div><span class="db-sc">' + s2 + '</span></div>';
        html += '</div>';
      });
      html += '</div></div>';
    });

    tree.innerHTML = html;
  }

  /* ==========================================================
     DOMContentLoaded INIT
     ========================================================== */
  document.addEventListener('DOMContentLoaded', function () {
    _initMobileDetail();
    _initLucideIcons();
    _renderDetailBracket();
  });
})();
