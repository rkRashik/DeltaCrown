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
  const POLL_ANN_INTERVAL     = 15_000;   // 15s
  const POLL_STATE_INTERVAL_WS = 45_000;  // 45s when WS is healthy
  const POLL_ANN_INTERVAL_WS   = 60_000;  // 60s safety poll when WS is healthy
  const POLL_STATE_MIN_GAP    = 3_500;    // Burst guard for manual/WS-triggered polls
  const POLL_ANN_MIN_GAP      = 5_000;    // Burst guard for announcements
  const COUNTDOWN_TICK        = 1_000;    // 1s
  const BROKEN_AVATAR_CACHE_KEY = 'hub_broken_avatar_urls';
  const HUB_TABS = new Set([
    'overview', 'announcements', 'matches', 'squad', 'schedule',
    'bracket', 'standings', 'prizes', 'resources',
    'participants', 'rulebook', 'support', 'lobby',
  ]);
  const TAB_ALIASES = {
    disputes: 'support',
    'support-disputes': 'support',
    'hub-tab-support': 'support',
  };
  const LOCKED_TABS_WHEN_UNVERIFIED = new Set([
    'matches',
    'lobby',
    'squad',
    'schedule',
    'bracket',
    'standings',
    'prizes',
    'resources',
  ]);
  const PRE_MATCH_LOBBY_WINDOW_MINUTES = 30;
  const SIDEBAR_COLLAPSE_KEY = 'hub_sidebar_collapsed';
  const PARTICIPANTS_SORT_KEY = 'hub_participants_sort';
  const OUTCOME_DISMISS_KEY = 'hub_outcome_dismissed_v1';
  const GAME_LOGO_BASE_PATH = '/static/img/game_logos/svg/';
  const HUB_GAME_LOGO_MAP = {
    codm: 'call-of-duty-logo.svg',
    callofdutymobile: 'call-of-duty-logo.svg',
    callofduty: 'call-of-duty-logo.svg',
    codmobile: 'call-of-duty-logo.svg',
    mlbb: 'mobile-legends-bang-bang.svg',
    mobilelegends: 'mobile-legends-bang-bang.svg',
    mobilelegendsbangbang: 'mobile-legends-bang-bang.svg',
    fc26: 'fifa.svg',
    fifa: 'fifa.svg',
    eafc: 'fifa.svg',
    easportsfc: 'fifa.svg',
    easportsfc26: 'fifa.svg',
    efootball: 'Efootball.svg',
    pes: 'Efootball.svg',
    proevolutionsoccer: 'Efootball.svg',
    cs2: 'cs2.svg',
    csgo: 'cs2.svg',
    freefire: 'freefire.svg',
    ff: 'freefire.svg',
    pubg: 'pubg.svg',
    pubgm: 'pubg.svg',
    pubgmobile: 'pubg.svg',
    valorant: 'valorant.svg',
    dota2: 'dota2.svg',
    rocketleague: 'rocket-league.svg',
  };
  const DEFAULT_TIMEZONE = 'Asia/Dhaka';
  const DEFAULT_TIME_FORMAT = '12h';
  const OVERVIEW_PHASE_STYLES = {
    danger: {
      wrap: 'hub-overview-phase-pill danger',
      label: 'hub-overview-phase-label',
      dot: 'hub-overview-phase-dot',
    },
    success: {
      wrap: 'hub-overview-phase-pill success',
      label: 'hub-overview-phase-label',
      dot: 'hub-overview-phase-dot',
    },
    info: {
      wrap: 'hub-overview-phase-pill info',
      label: 'hub-overview-phase-label',
      dot: 'hub-overview-phase-dot',
    },
  };
  const OVERVIEW_BADGE_BASE_CLASS = 'hub-overview-action-badge';
  const OVERVIEW_BADGE_TONE_CLASS = {
    danger: 'danger',
    success: 'success',
    warning: 'warning',
    info: 'info',
  };
  const OVERVIEW_PRIMARY_BTN_BASE_CLASS = 'hub-overview-btn primary';
  const OVERVIEW_SECONDARY_BTN_CLASS = 'hub-overview-btn secondary';
  const OVERVIEW_TERTIARY_BTN_CLASS = 'hub-overview-btn tertiary';
  const OVERVIEW_PIPELINE_NODE_CLASS = {
    active: 'hub-overview-pipeline-node is-active is-pulsing',
    completed: 'hub-overview-pipeline-node is-completed',
    upcoming: 'hub-overview-pipeline-node is-upcoming',
  };
  const OVERVIEW_PIPELINE_LABEL_CLASS = {
    active: 'hub-overview-pipeline-label active',
    completed: 'hub-overview-pipeline-label completed',
    upcoming: 'hub-overview-pipeline-label upcoming',
  };
  const OVERVIEW_FORM_PILL_CLASS = {
    win: 'hub-overview-form-pill win',
    loss: 'hub-overview-form-pill loss',
    draw: 'hub-overview-form-pill draw',
    muted: 'hub-overview-form-pill muted',
  };
  const OVERVIEW_ANN_ITEM_CLASS = 'hub-overview-ann-item grid grid-cols-[auto,1fr] gap-3 rounded-xl border border-white/10 px-3 py-3';
  const OVERVIEW_ANN_ITEM_LATEST_CLASS = 'ring-1 ring-cyan-300/35 bg-zinc-900/78';
  const OVERVIEW_ANN_ITEM_DEFAULT_CLASS = 'bg-zinc-950/55';
  const OVERVIEW_ANN_ICON_CLASS = {
    urgent: 'border-rose-300/50 bg-rose-500/15 text-rose-100',
    warning: 'border-amber-300/50 bg-amber-500/15 text-amber-100',
    success: 'border-emerald-300/50 bg-emerald-500/15 text-emerald-100',
    info: 'border-cyan-300/45 bg-cyan-500/12 text-cyan-100',
  };

  // ── State ───────────────────────────────────────────────
  let _shell       = null;
  let _currentTab  = null;
  let _pollStateId = null;
  let _latestOutcomeContext = null;
  let _pollAnnId   = null;
  let _countdownId = null;
  let _timePrefs = { timezone: DEFAULT_TIMEZONE, timeFormat: DEFAULT_TIME_FORMAT };
  let _timePrefsPromise = null;

  // Lazy-load caches (fetched once per session)
  let _prizesCache       = null;
  let _resourcesCache    = null;
  let _bracketCache      = null;
  let _standingsCache    = null;
  let _matchesCache      = null;
  let _matchesCacheFetchedAt = 0;
  let _participantsCache = null;
  let _participantsAll   = [];  // for search filtering
  let _participantsSort = 'joined_desc';
  let _supportTicketsLoaded = false;
  let _participantsPage = 1;
  let _participantsHasMore = false;
  const _participantsPageSize = 24;
  let _supportTicketsPage = 1;
  let _supportTicketsHasMore = false;
  const _supportTicketsPageSize = 20;
  let _openModalId = null;
  let _modalReturnFocusEl = null;
  let _mobileSidebarReturnFocusEl = null;
  let _announcementItems = [];
  let _announcementFilter = 'all';
  let _announcementSearch = '';
  let _announcementSearchTimer = null;
  let _announcementHasMore = false;
  let _announcementLastUpdatedAt = null;
  let _announcementLoading = false;
  let _announcementScrollTimer = null;
  let _statePollInFlight = false;
  let _statePollQueued = false;
  let _statePollFailCount = 0;
  let _lastStatePollStartedAt = 0;
  let _lastAnnouncementPollStartedAt = 0;
  let _lastPolledState = null;
  let _scheduleFilter = 'all';
  let _overviewMatchRefreshInFlight = false;
  let _overviewIntelViewMode = 'auto';
  let _rescheduleModalState = null;
  let _rescheduleModalBusy = false;

  // S27: WebSocket connection for real-time sync
  let _ws = null;
  let _wsReconnectTimer = null;
  let _wsReconnectAttempts = 0;
  let _wsPingId = null;
  let _wsConnected = false;
  let _resizeTimer = null;
  let _onKeyDown = null;
  let _onWindowResize = null;
  let _onHashChange = null;
  let _onPopState = null;
  let _onVisibilityChange = null;
  let _mobileLobbyAutoFocused = false;
  let _onViewportScroll = null;
  let _onViewportTouchStart = null;
  let _onViewportPointerDown = null;
  let _mobileChromeIdleTimer = null;
  let _lastViewportScrollTop = 0;
  const WS_RECONNECT_MAX = 3;
  const WS_RECONNECT_BASE = 3000;  // 3s, doubles each retry
  const _brokenAvatarUrls = new Set();
  const _dismissedOutcomeKeys = new Set();
  let _latestOutcomeCommand = null;
  let _outcomeSharePayload = null;
  let _overviewGameBranding = null;
  let _heroFxAnimId = null;
  let _heroFxParticles = [];
  let _outcomeFxAnimId = null;
  let _outcomeFxParticles = [];

  function _isMobileViewport() {
    return window.matchMedia && window.matchMedia('(max-width: 1023px)').matches;
  }

  function _showMobileChrome({ keepDockVisible = false, immediate = false } = {}) {
    if (!_shell) return;
    if (immediate) {
      _shell.classList.add('hub-mobile-dock-snap');
      setTimeout(() => {
        if (_shell) _shell.classList.remove('hub-mobile-dock-snap');
      }, 110);
    }
    _shell.classList.remove('hub-mobile-chrome-hidden');
    if (keepDockVisible) {
      _shell.classList.remove('hub-mobile-dock-idle');
    }
  }

  function _scheduleMobileDockIdle() {
    if (!_shell || !_isMobileViewport()) return;
    if (_mobileChromeIdleTimer) clearTimeout(_mobileChromeIdleTimer);
    _mobileChromeIdleTimer = setTimeout(() => {
      _shell.classList.add('hub-mobile-dock-idle');
    }, 3000);
  }

  function _initMobileChromeGestures() {
    const viewport = document.getElementById('hub-viewport');
    if (!viewport || !_shell) return;

    _lastViewportScrollTop = viewport.scrollTop || 0;

    _onViewportScroll = () => {
      if (!_isMobileViewport()) return;

      const current = viewport.scrollTop || 0;
      const delta = current - _lastViewportScrollTop;

      if (delta > 6 && current > 16) {
        _shell.classList.add('hub-mobile-chrome-hidden');
        _shell.classList.remove('hub-mobile-dock-idle');
      } else if (delta < -4 || current <= 8) {
        _showMobileChrome({ keepDockVisible: true });
      }

      _lastViewportScrollTop = Math.max(0, current);
      _scheduleMobileDockIdle();
    };

    _onViewportTouchStart = () => {
      if (!_isMobileViewport()) return;
      _showMobileChrome({ keepDockVisible: true, immediate: true });
      _scheduleMobileDockIdle();
    };

    _onViewportPointerDown = () => {
      if (!_isMobileViewport()) return;
      _showMobileChrome({ keepDockVisible: true, immediate: true });
      _scheduleMobileDockIdle();
    };

    viewport.addEventListener('scroll', _onViewportScroll, { passive: true });
    viewport.addEventListener('touchstart', _onViewportTouchStart, { passive: true });
    viewport.addEventListener('pointerdown', _onViewportPointerDown, { passive: true });

    if (!_isMobileViewport()) {
      _shell.classList.remove('hub-mobile-chrome-hidden', 'hub-mobile-dock-idle');
      return;
    }

    _showMobileChrome({ keepDockVisible: true });
    _scheduleMobileDockIdle();
  }

  function _emitToast(type, message) {
    const safeType = String(type || 'info').toLowerCase();
    const safeMessage = (message == null) ? '' : String(message);
    if (!safeMessage) return;

    if (window.Toast && typeof window.Toast[safeType] === 'function') {
      window.Toast[safeType](safeMessage);
      return;
    }

    if (typeof window.showToast === 'function') {
      try {
        window.showToast(safeMessage, safeType);
      } catch (err) {
        window.showToast(safeMessage);
      }
      return;
    }

    if (safeType === 'error' || safeType === 'warning') {
      console.warn(`[Hub] ${safeType}:`, safeMessage);
    }
  }

  function _buildHubApiPath(pathSuffix) {
    const slug = _shell?.dataset.slug;
    if (!slug || !pathSuffix) return '';
    return `/tournaments/${slug}/hub/api/${pathSuffix}`;
  }

  function _proposalEndpoint(matchId) {
    const id = String(matchId || '').trim();
    if (!id) return '';
    return _buildHubApiPath(`matches/${encodeURIComponent(id)}/reschedule/propose/`);
  }

  function _respondEndpoint(matchId) {
    const id = String(matchId || '').trim();
    if (!id) return '';
    return _buildHubApiPath(`matches/${encodeURIComponent(id)}/reschedule/respond/`);
  }

  function _normalizeTimeFormat(value) {
    const token = String(value || '').trim().toLowerCase();
    if (token === '24' || token === '24h') return '24h';
    return '12h';
  }

  function _normalizeTimezone(value) {
    const tz = String(value || '').trim();
    return tz || DEFAULT_TIMEZONE;
  }

  function _timeFormatOptions(options, includeTime = true) {
    const next = (options && typeof options === 'object') ? { ...options } : {};
    if (!next.timeZone) {
      next.timeZone = _timePrefs.timezone;
    }
    if (includeTime && next.hour12 === undefined && next.hourCycle === undefined) {
      next.hour12 = _timePrefs.timeFormat !== '24h';
    }
    return next;
  }

  function _formatDateTime(value, options) {
    const dt = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(dt.getTime())) return '';
    return dt.toLocaleString([], _timeFormatOptions(options, true));
  }

  function _formatTime(value, options) {
    const dt = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(dt.getTime())) return '';
    return dt.toLocaleTimeString([], _timeFormatOptions(options, true));
  }

  function _formatDate(value, options) {
    const dt = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(dt.getTime())) return '';
    return dt.toLocaleDateString([], _timeFormatOptions(options, false));
  }

  function _loadTimePreferences() {
    if (_timePrefsPromise) return _timePrefsPromise;

    _timePrefsPromise = fetch('/me/settings/platform-global/', {
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then(async (resp) => {
        if (!resp.ok) throw new Error(`settings_http_${resp.status}`);
        const payload = await resp.json().catch(() => ({}));
        const preferences = (payload && typeof payload === 'object' && payload.preferences)
          ? payload.preferences
          : {};
        _timePrefs = {
          timezone: _normalizeTimezone(preferences.timezone || preferences.timezone_pref),
          timeFormat: _normalizeTimeFormat(preferences.time_format),
        };
        return _timePrefs;
      })
      .catch(() => _timePrefs)
      .then((prefs) => {
        _updateAnnouncementSyncLabel();
        _rerenderMatchSurfacesFromCache();
        return prefs;
      });

    return _timePrefsPromise;
  }

  function _maybeDefaultToParticipantViewOnMobile() {
    if (!_shell || !_isMobileViewport()) return false;
    if (_shell.dataset.canToggleViewMode !== 'true') return false;
    if (_shell.dataset.isStaffView !== 'true') return false;

    const targetRaw = String(_shell.dataset.viewAsParticipantUrl || '').trim();
    if (!targetRaw) return false;

    try {
      const currentUrl = new URL(window.location.href);
      const targetUrl = new URL(targetRaw, window.location.origin);
      if (!targetUrl.hash && currentUrl.hash) {
        targetUrl.hash = currentUrl.hash;
      }
      if (targetUrl.href !== currentUrl.href) {
        window.location.replace(targetUrl.href);
        return true;
      }
    } catch (_err) {
      return false;
    }

    return false;
  }

  function _toDatetimeLocalValue(dateInput) {
    const dt = dateInput instanceof Date ? dateInput : new Date(dateInput);
    if (Number.isNaN(dt.getTime())) return '';
    const local = new Date(dt.getTime() - (dt.getTimezoneOffset() * 60000));
    return local.toISOString().slice(0, 16);
  }

  function _parseLocalDatetime(raw) {
    const value = String(raw || '').trim();
    if (!value) return null;
    const normalized = value.includes('T') ? value : value.replace(' ', 'T');
    const dt = new Date(normalized);
    if (Number.isNaN(dt.getTime())) return null;
    return dt;
  }

  function _formatRescheduleDatetimeLabel(raw) {
    const dt = raw ? new Date(raw) : null;
    if (!dt || Number.isNaN(dt.getTime())) {
      return 'a proposed time';
    }
    return _formatDateTime(dt, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function _rescheduleErrorMessage(payload) {
    const code = String(payload?.error || '').trim();
    if (!code) return 'Unable to process the reschedule request right now.';

    if (code === 'participant_rescheduling_disabled') return 'Participant rescheduling is disabled for this tournament.';
    if (code === 'proposal_deadline_passed') return 'The proposal deadline for this match has already passed.';
    if (code === 'pending_request_exists') return 'A pending proposal already exists for this match.';
    if (code === 'pending_request_not_found') return 'No pending proposal was found for this match.';
    if (code === 'pending_request_expired') return 'This proposal expired before a response was submitted.';
    if (code === 'not_match_participant') return 'Only participants in this match can perform this action.';
    if (code === 'proposer_cannot_respond') return 'The proposing side cannot accept or reject its own request.';
    if (code === 'match_not_scheduled') return 'This match must be scheduled before a proposal can be sent.';
    if (code === 'invalid_datetime_format') return 'Use a valid date/time format (YYYY-MM-DDTHH:MM).';
    if (code === 'new_time_must_be_future') return 'Choose a future date/time for the new schedule.';
    if (code === 'new_time_must_differ') return 'Choose a different time from the current schedule.';
    if (code === 'reason_too_long') return 'Reason is too long. Keep it under 500 characters.';
    if (code === 'response_note_too_long') return 'Response note is too long. Keep it under 500 characters.';
    if (code.startsWith('cannot_reschedule_state:')) {
      return 'This match state no longer allows participant reschedule proposals.';
    }

    return code.replace(/_/g, ' ');
  }

  function _collectKnownMatches() {
    const fromMatches = [
      ...((_matchesCache && _matchesCache.active_matches) || []),
      ...((_matchesCache && _matchesCache.match_history) || []),
    ];
    const fromSchedule = [
      ...((_scheduleMatchesCache && _scheduleMatchesCache.active_matches) || []),
      ...((_scheduleMatchesCache && _scheduleMatchesCache.match_history) || []),
    ];
    return [...fromMatches, ...fromSchedule];
  }

  function _findMatchById(matchId) {
    const id = String(matchId || '').trim();
    if (!id) return null;
    const all = _collectKnownMatches();
    return all.find((m) => String(m?.id || '') === id) || null;
  }

  function _openMatchRoom(url) {
    const targetUrl = String(url || '').trim();
    if (!targetUrl) {
      _emitToast('warning', 'Lobby link is not available for this match yet.');
      return;
    }
    window.location.href = targetUrl;
  }

  function _invalidateMatchCaches() {
    _matchesCache = null;
    _scheduleMatchesCache = null;
    _matchesCacheFetchedAt = 0;
  }

  async function _refreshMatchSurfaces() {
    _invalidateMatchCaches();

    try {
      await _fetchMatches();
    } catch (err) {
      console.warn('[HubEngine] Failed to refresh matches:', err?.message || err);
    }

    try {
      await _fetchScheduleMatches();
    } catch (err) {
      console.warn('[HubEngine] Failed to refresh schedule matches:', err?.message || err);
    }

    _refreshOverviewActionCard({ forceFetch: true, stateData: _lastPolledState });
  }

  function _mutateCachedMatch(matchId, mutator) {
    const normalizedId = String(matchId || '').trim();
    if (!normalizedId || typeof mutator !== 'function') return;

    const mutateCollection = (collection) => {
      if (!Array.isArray(collection)) return;
      collection.forEach((item) => {
        if (String(item?.id || '') === normalizedId) {
          mutator(item);
        }
      });
    };

    [_matchesCache, _scheduleMatchesCache].forEach((cache) => {
      if (!cache || typeof cache !== 'object') return;
      mutateCollection(cache.active_matches);
      mutateCollection(cache.match_history);
    });
  }

  function _rerenderMatchSurfacesFromCache() {
    if (_matchesCache) {
      _renderMatches(_matchesCache);
    } else {
      _renderOverviewActionCard(_scheduleMatchesCache || null, _lastPolledState);
    }

    if (_scheduleMatchesCache) {
      _renderScheduleMatches(_scheduleMatchesCache);
    }
  }

  // ── Init ────────────────────────────────────────────────
  function init() {
    _shell = document.getElementById('hub-shell');
    if (!_shell) return;

    _loadBrokenAvatarUrlCache();
    _loadOutcomeDismissState();
    _mountOutcomeSpotlightToBody();
    _applyOverviewGameBranding();
    _startOverviewHeroFx();
    _hydrateOverviewAnnouncementTimesFromDom();
    _hydrateAnnouncementTimesFromDom('#hub-announcements-lifecycle-strip');
    _hydrateAnnouncementTimesFromDom('#hub-announcements-feed');

    const outcomeDismissBtn = document.getElementById('hub-overview-outcome-spotlight-dismiss');
    if (outcomeDismissBtn) {
      outcomeDismissBtn.addEventListener('click', _dismissOutcomeSpotlight);
    }
    const outcomeOverlay = document.getElementById('hub-overview-outcome-spotlight');
    if (outcomeOverlay) {
      outcomeOverlay.addEventListener('click', (event) => {
        if (event.target === outcomeOverlay) {
          _dismissOutcomeSpotlight();
        }
      });
    }

    const shareDismissBtn = document.getElementById('hub-overview-share-dismiss');
    const shareCopyBtn = document.getElementById('hub-overview-share-copy');
    const sharePostBtn = document.getElementById('hub-overview-share-post');
    const shareTriggerBtn = document.getElementById('hub-overview-outcome-spotlight-share-trigger');

    if (shareTriggerBtn) {
      shareTriggerBtn.setAttribute('aria-expanded', 'false');
      shareTriggerBtn.addEventListener('click', _openOutcomeShareModal);
    }

    if (shareDismissBtn) {
      shareDismissBtn.addEventListener('click', _dismissOutcomeShareModal);
    }
    if (shareCopyBtn) {
      shareCopyBtn.addEventListener('click', _copyOutcomeShareCaption);
    }
    if (sharePostBtn) {
      sharePostBtn.addEventListener('click', _submitOutcomeShare);
    }

    if (_maybeDefaultToParticipantViewOnMobile()) {
      return;
    }

    _loadTimePreferences();

    // Start countdown
    _startCountdown();
    _bindFeedControls();
    _bindParticipantsControls();
    _bindScheduleControls();
    _bindResourcesQuickNav();
    _initDesktopSidebar();
    _initMobileChromeGestures();

    _scheduleFilter = _shell?.dataset.isStaffView === 'true' ? 'all' : 'my';
    _setScheduleFilter(_scheduleFilter, { rerender: false });
    _syncTournamentStatusUi(_shell?.dataset.tournamentStatus || '');
    _pollState()
      .finally(() => {
        _refreshOverviewActionCard({ forceFetch: true, stateData: _lastPolledState });
      });

    // Start polling (auto-pauses in background tab)
    _startPolling();

    // S27: Connect WebSocket for real-time updates
    _connectWebSocket();

    // Keyboard: Escape closes mobile sidebar + modals
    _onKeyDown = (e) => {
      if (e.key === 'Escape') {
        _dismissOutcomeShareModal();
        closeMobileSidebar();
        closeRescheduleModal();
        closeAlertConfirmModal();
        closeAlertModal();
        closeContactModal();
        closeStatusModal();
        closeTicketModal();
        _dismissOutcomeSpotlight();
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
      _startOverviewHeroFx();

      if (!_shell) return;

      if (_isMobileViewport()) {
        _showMobileChrome({ keepDockVisible: true });
        _scheduleMobileDockIdle();
        return;
      }

      _shell.classList.remove('hub-mobile-chrome-hidden', 'hub-mobile-dock-idle');
      if (_mobileChromeIdleTimer) {
        clearTimeout(_mobileChromeIdleTimer);
        _mobileChromeIdleTimer = null;
      }
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
      _pollState({ force: true });
      _pollAnnouncements({ force: true });
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

    if (normalizedTab !== 'overview') {
      _dismissOutcomeSpotlight({ persist: false });
      _dismissOutcomeShareModal();
    } else if (_latestOutcomeCommand) {
      _renderOutcomeExperience(_latestOutcomeCommand, _latestOutcomeContext || {});
    }

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
    if (normalizedTab === 'matches') {
      const _matchStale = !_matchesCache || (Date.now() - _matchesCacheFetchedAt) > 15000;
      if (_matchStale) _fetchMatches();
    }
    if (normalizedTab === 'participants' && !_participantsCache) {
      _fetchParticipants({ reset: true });
    }
    if (normalizedTab === 'lobby') {
      const _lobbyStale = !_matchesCache || (Date.now() - _matchesCacheFetchedAt) > 15000;
      if (_lobbyStale) {
        _fetchMatches();
      } else {
        _renderMobileLobby(_matchesCache);
      }
    }
    if (normalizedTab === 'matches') {
      _fetchScheduleMatches();
    }
    if (normalizedTab === 'standings' && !_participantsCache) {
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

    const checkInButtons = document.querySelectorAll(
      '#hub-checkin-btn, #hub-checkin-btn-lobby, #hub-overview-action-btn[data-hub-action="check_in"]'
    );

    // Disable buttons
    checkInButtons.forEach(btn => {
      btn.disabled = true;
      if (btn.id === 'hub-overview-action-btn') {
        btn.textContent = 'Checking in...';
      } else {
        btn.textContent = 'Checking in...';
      }
    });

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: _csrfHeaders({
          'Content-Type': 'application/json',
        }),
        credentials: 'same-origin',
      });

      const data = await resp.json();

      if (data.success) {
        // Update buttons to "done" state
        checkInButtons.forEach(btn => {
          if (btn.id === 'hub-overview-action-btn') {
            btn.dataset.hubAction = 'checked_in';
            btn.textContent = 'Checked In';
          } else {
            btn.className = 'hub-checkin-btn done clip-slant w-full lg:w-auto flex items-center justify-center gap-3';
            btn.innerHTML = '<i data-lucide="check" class="w-5 h-5"></i> Checked In';
          }
          btn.disabled = true;
          btn.onclick = null;
        });

        // Update shell data attribute
        if (_shell) _shell.dataset.isCheckedIn = 'true';

        // Show toast if available
        _emitToast('success', 'Successfully checked in!');

        // Re-init icons
        if (typeof lucide !== 'undefined') lucide.createIcons();

        // Refresh state
        _pollState();
      } else {
        const errMsg = data.error || 'Check-in failed. Please try again.';
        _emitToast('error', errMsg);
        // Re-enable buttons
        checkInButtons.forEach(btn => {
          btn.disabled = false;
          if (btn.id === 'hub-overview-action-btn') {
            btn.dataset.hubAction = 'check_in';
            btn.textContent = 'Check In Now';
          } else {
            btn.innerHTML = '<i data-lucide="check-circle" class="w-5 h-5"></i> Check In Now';
          }
        });
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    } catch (err) {
      console.error('[HubEngine] Check-in error:', err);
      _emitToast('error', 'Network error. Please try again.');
      checkInButtons.forEach(btn => {
        btn.disabled = false;
        if (btn.id === 'hub-overview-action-btn') {
          btn.dataset.hubAction = 'check_in';
          btn.textContent = 'Check In Now';
        } else {
          btn.innerHTML = '<i data-lucide="check-circle" class="w-5 h-5"></i> Check In Now';
        }
      });
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }
  }

  // ──────────────────────────────────────────────────────────
  // State Polling
  // ──────────────────────────────────────────────────────────
  function _startPolling() {
    // T3-3: Skip polling for terminal tournament states
    const initStatus = String(_shell?.dataset.tournamentStatus || '').toLowerCase();
    if (['completed', 'archived', 'cancelled'].includes(initStatus)) return;

    const stateInterval = _wsConnected ? POLL_STATE_INTERVAL_WS : POLL_STATE_INTERVAL;
    const annInterval = _wsConnected ? POLL_ANN_INTERVAL_WS : POLL_ANN_INTERVAL;

    if (!_pollStateId) {
      _pollStateId = setInterval(_pollState, stateInterval);
    }
    if (!_pollAnnId) {
      _pollAnnId = setInterval(_pollAnnouncements, annInterval);
    }
  }

  function _restartPolling() {
    _stopPolling();
    _startPolling();
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

  async function _pollState(options = {}) {
    const url = _shell?.dataset.apiState;
    if (!url) return;

    const force = Boolean(options && options.force);

    if (_statePollInFlight) {
      if (force) {
        _statePollQueued = true;
      }
      return;
    }

    const now = Date.now();
    if (!force && (now - _lastStatePollStartedAt) < POLL_STATE_MIN_GAP) {
      return;
    }

    _statePollInFlight = true;
    _lastStatePollStartedAt = now;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) return;
      const data = await resp.json();
      _lastPolledState = data;
      _statePollFailCount = 0;

      if (data.tournament_status) {
        _syncTournamentStatusUi(data.tournament_status);
      }

      if (data.phase_event) {
        _updateOverviewPhaseEvent(data.phase_event);
      }

      if (data.lifecycle_pipeline) {
        _renderLifecyclePipeline(data.lifecycle_pipeline);
      }

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
      const overviewStatusEl = document.getElementById('hub-overview-status-label');
      if (overviewStatusEl && data.user_status) {
        overviewStatusEl.textContent = data.user_status;
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
      const cdEl = document.getElementById('hub-countdown');
      if (cdEl) {
        if (data.phase_event && data.phase_event.target) {
          const current = cdEl.getAttribute('data-target');
          cdEl.classList.remove('hidden');
          if (current !== data.phase_event.target) {
            cdEl.setAttribute('data-target', data.phase_event.target);
            // Restart countdown
            if (_countdownId) clearInterval(_countdownId);
            _startCountdown();
          }
        } else {
          cdEl.setAttribute('data-target', '');
          cdEl.classList.add('hidden');
          _setCountdown('--', '--', '--');
          if (_countdownId) {
            clearInterval(_countdownId);
            _countdownId = null;
          }
        }
      }

      _renderOverviewActionCard(_matchesCache, data);

      const status = String(data.tournament_status || '').toLowerCase();
      const hasBackendCommand = Boolean(data.command_center && Object.prototype.hasOwnProperty.call(data.command_center, 'show'));
      const shouldRefreshOverviewMatch = ['live', 'check_in', 'registration_closed', 'registration_open'].includes(status)
        || !_matchesCache
        || hasBackendCommand;
      const isStale = !_matchesCache || (Date.now() - _matchesCacheFetchedAt) > 60000;
      if (shouldRefreshOverviewMatch && isStale) {
        _refreshOverviewActionCard({ forceFetch: true, stateData: data });
      }

    } catch (err) {
      _statePollFailCount++;
      console.warn('[HubEngine] State poll failed:', err.message);
      if (_statePollFailCount === 3 && typeof window.showToast === 'function') {
        window.showToast('Failed to sync hub data. Check your connection.', 'warning');
      }
    } finally {
      _statePollInFlight = false;
      if (_statePollQueued) {
        _statePollQueued = false;
        _pollState({ force: true });
      }
    }
  }

  // ──────────────────────────────────────────────────────────
  // Announcements Polling
  // ──────────────────────────────────────────────────────────
  async function _pollAnnouncements({ append = false, forceLimit = null, force = false } = {}) {
    const url = _shell?.dataset.apiAnnouncements;
    if (!url) return;
    if (_announcementLoading) return;

    if (!append && !force && (Date.now() - _lastAnnouncementPollStartedAt) < POLL_ANN_MIN_GAP) {
      return;
    }

    const currentCount = Array.isArray(_announcementItems) ? _announcementItems.length : 0;
    const offset = append ? currentCount : 0;
    const pageLimit = Number(forceLimit) > 0
      ? Number(forceLimit)
      : (_currentTab === 'announcements' ? 60 : 20);

    _announcementLoading = true;
    _lastAnnouncementPollStartedAt = Date.now();
    _toggleAnnouncementLoadMoreLoading(append, true);

    try {
      const requestUrl = new URL(url, window.location.origin);
      requestUrl.searchParams.set('limit', String(pageLimit));
      requestUrl.searchParams.set('offset', String(offset));

      const resp = await fetch(requestUrl.toString(), { credentials: 'same-origin' });
      if (!resp.ok) return;
      const data = await resp.json();

      const announcements = Array.isArray(data.announcements) ? data.announcements : [];
      const meta = data.meta || {};
      _announcementHasMore = Boolean(meta.has_more);

      if (append) {
        const existingIds = new Set(_announcementItems.map((item) => item.id));
        announcements.forEach((item) => {
          if (!existingIds.has(item.id)) {
            _announcementItems.push(item);
          }
        });
      } else {
        _announcementItems = announcements;
      }

      _announcementLastUpdatedAt = new Date();
      _updateAnnouncementSyncLabel();
      _toggleAnnouncementLoadMoreLoading(append, false);
      _renderAnnouncementsFeed(_announcementItems);

    } catch (err) {
      console.warn('[HubEngine] Announcements poll failed:', err.message);
    } finally {
      _announcementLoading = false;
      _toggleAnnouncementLoadMoreLoading(append, false);
    }
  }

  function _bindFeedControls() {
    const searchInput = document.getElementById('hub-ann-search');
    if (searchInput && searchInput.dataset.bound !== '1') {
      searchInput.dataset.bound = '1';
      searchInput.addEventListener('input', () => {
        clearTimeout(_announcementSearchTimer);
        _announcementSearchTimer = setTimeout(() => {
          _announcementSearch = (searchInput.value || '').trim().toLowerCase();
          _renderAnnouncementsFeed(_announcementItems);
        }, 160);
      });
    }

    const filters = document.getElementById('hub-ann-filters');
    if (filters && filters.dataset.bound !== '1') {
      filters.dataset.bound = '1';
      filters.querySelectorAll('[data-hub-feed-filter]').forEach((btn) => {
        btn.addEventListener('click', () => {
          _announcementFilter = btn.getAttribute('data-hub-feed-filter') || 'all';
          _renderAnnouncementsFeed(_announcementItems);
        });
      });
    }

    const feed = document.getElementById('hub-announcements-feed');
    if (feed && feed.dataset.boundScroll !== '1') {
      feed.dataset.boundScroll = '1';
      feed.addEventListener('scroll', () => {
        if (_currentTab !== 'announcements') return;
        if (_announcementLoading || !_announcementHasMore) return;

        clearTimeout(_announcementScrollTimer);
        _announcementScrollTimer = setTimeout(() => {
          const nearBottom = feed.scrollTop + feed.clientHeight >= (feed.scrollHeight - 140);
          if (nearBottom) {
            loadMoreAnnouncements();
          }
        }, 80);
      });
    }
  }

  function _updateAnnouncementSyncLabel() {
    const stamp = document.getElementById('hub-ann-last-sync');
    if (!stamp) return;
    if (!_announcementLastUpdatedAt) {
      stamp.textContent = 'Waiting for first sync';
      return;
    }
    stamp.textContent = `Synced ${_formatTime(_announcementLastUpdatedAt, { hour: '2-digit', minute: '2-digit' })}`;
  }

  function _toggleAnnouncementLoadMoreLoading(isLoadingMore, isLoading) {
    const btn = document.getElementById('hub-ann-load-more-btn');
    if (!btn) return;

    btn.disabled = isLoading;
    if (isLoading && isLoadingMore) {
      btn.textContent = 'Loading older updates...';
    } else {
      btn.textContent = 'Load Older';
    }
  }

  function loadMoreAnnouncements() {
    if (_announcementLoading || !_announcementHasMore) return;
    _pollAnnouncements({ append: true, forceLimit: 40 });
  }

  function refreshAnnouncements() {
    if (_announcementLoading) return;
    _pollAnnouncements({ append: false });
  }

  function _normalizeAnnouncementLegacyTime(rawLabel) {
    const text = String(rawLabel || '').trim();
    if (!text) return '';
    const lowered = text.toLowerCase();
    if (lowered === 'just now' || lowered === 'now' || lowered === 'moments ago') return 'Just now';
    return text
      .replace(/minutes?/i, 'min')
      .replace(/hours?/i, 'hr')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function _formatAnnouncementRelativeTime(createdAt) {
    const dt = _toValidDate(createdAt);
    if (!dt) return '';

    const diffSeconds = Math.max(0, Math.floor((Date.now() - dt.getTime()) / 1000));
    if (diffSeconds < 60) return 'Just now';
    if (diffSeconds < 3600) return `${Math.max(1, Math.floor(diffSeconds / 60))} min ago`;
    if (diffSeconds < 86400) return `${Math.max(1, Math.floor(diffSeconds / 3600))} hr ago`;
    if (diffSeconds < 172800) return 'Yesterday';
    if (diffSeconds < 604800) return `${Math.max(2, Math.floor(diffSeconds / 86400))} days ago`;
    if (diffSeconds < 31536000) {
      return _formatDate(dt, { month: 'short', day: 'numeric' }) || '';
    }
    return _formatDate(dt, { year: 'numeric', month: 'short', day: 'numeric' }) || '';
  }

  function _announcementSortTimestamp(announcement) {
    const dt = _toValidDate(
      announcement?.created_at
      || announcement?.createdAt
      || announcement?.timestamp
      || null
    );
    return dt ? dt.getTime() : 0;
  }

  function _announcementSortNumericId(announcement) {
    const rawId = String(announcement?.id || '').trim();
    if (!rawId) return 0;

    const tail = rawId.includes('-') ? rawId.split('-').pop() : rawId;
    const parsed = Number.parseInt(String(tail || ''), 10);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function _sortAnnouncementsCanonical(items) {
    const source = Array.isArray(items) ? items.slice() : [];
    source.sort((a, b) => {
      const tsDiff = _announcementSortTimestamp(b) - _announcementSortTimestamp(a);
      if (tsDiff !== 0) return tsDiff;

      const idDiff = _announcementSortNumericId(b) - _announcementSortNumericId(a);
      if (idDiff !== 0) return idDiff;

      return String(b?.id || '').localeCompare(String(a?.id || ''));
    });
    return source;
  }

  function _resolveAnnouncementTimeLabel(announcement) {
    const ann = announcement || {};
    const createdAt = _toValidDate(ann.created_at || ann.createdAt || ann.timestamp || null);

    if (createdAt) {
      return _formatAnnouncementRelativeTime(createdAt);
    }
    return 'Time unavailable';
  }

  function _hydrateAnnouncementTimesFromDom(rootSelector) {
    const selector = String(rootSelector || '').trim();
    if (!selector) return;

    const rows = Array.from(document.querySelectorAll(`${selector} [data-ann-created-at]`));
    if (!rows.length) return;

    rows.forEach((node) => {
      const createdAt = node.getAttribute('data-ann-created-at') || '';
      node.textContent = _resolveAnnouncementTimeLabel({ created_at: createdAt });
    });
  }

  function _hydrateOverviewAnnouncementTimesFromDom() {
    _hydrateAnnouncementTimesFromDom('#hub-overview-announcements-feed');
  }

  function _initDesktopSidebar() {
    const shell = document.getElementById('hub-shell');
    if (!shell) return;

    const stored = localStorage.getItem(SIDEBAR_COLLAPSE_KEY);
    if (stored === '1') {
      shell.classList.add('hub-sidebar-collapsed');
    }

    document.querySelectorAll('.hub-sidebar-desktop .hub-nav-btn').forEach((btn) => {
      const labelEl = btn.querySelector('.hub-nav-label') || btn.querySelector('span');
      const label = (labelEl?.textContent || '').trim();
      if (label) {
        btn.setAttribute('data-nav-label', label);
      }
    });

    _syncSidebarToggleIcon();
  }

  function _syncSidebarToggleIcon() {
    const shell = document.getElementById('hub-shell');
    if (!shell) return;

    const collapsed = shell.classList.contains('hub-sidebar-collapsed');

    document.querySelectorAll('[data-hub-sidebar-toggle]').forEach((btn) => {
      const icon = btn.querySelector('i[data-lucide]');
      if (icon) {
        icon.setAttribute('data-lucide', collapsed ? 'panel-left-open' : 'panel-left-close');
      }
      btn.setAttribute('title', collapsed ? 'Expand Sidebar' : 'Collapse Sidebar');
    });

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function toggleDesktopSidebar() {
    const shell = document.getElementById('hub-shell');
    if (!shell) return;
    shell.classList.toggle('hub-sidebar-collapsed');
    const collapsed = shell.classList.contains('hub-sidebar-collapsed');
    localStorage.setItem(SIDEBAR_COLLAPSE_KEY, collapsed ? '1' : '0');
    _syncSidebarToggleIcon();
  }

  function openAnnouncementsPanel() {
    switchTab('announcements');
    requestAnimationFrame(() => {
      const feed = document.getElementById('hub-announcements-feed');
      if (!feed) return;
      feed.scrollIntoView({ behavior: 'smooth', block: 'start' });
      feed.classList.add('hub-ann-focus');
      setTimeout(() => feed.classList.remove('hub-ann-focus'), 1200);
    });
  }

  function _renderAnnouncementsFeed(items) {
      const feed = document.getElementById('hub-announcements-feed');

      const source = _sortAnnouncementsCanonical(items);
      const filtered = source.filter((ann) => {
        if (_announcementFilter === 'pinned' && !ann.is_pinned) return false;
        if (_announcementFilter === 'urgent' && String(ann.type || '').toLowerCase() !== 'urgent') return false;
        if (_announcementFilter === 'success' && String(ann.type || '').toLowerCase() !== 'success') return false;
        if (_announcementSearch) {
          const title = String(ann.title || '').toLowerCase();
          const message = String(ann.message || '').toLowerCase();
          if (!title.includes(_announcementSearch) && !message.includes(_announcementSearch)) return false;
        }
        return true;
      });

      const html = filtered.map((ann) => {
        const type = String(ann.type || 'info').toLowerCase();
        const borderColor = type === 'urgent' ? '#FF2A55'
                          : type === 'warning' ? '#FFB800'
                          : type === 'success' ? '#00FF66'
                          : '#00F0FF';
        const borderStyle = type === 'success' ? 'border-dashed' : '';
        const badgeBg = type === 'urgent' ? 'bg-[#FF2A55]/10 text-[#FF2A55] border border-[#FF2A55]/30'
                      : type === 'warning' ? 'bg-[#FFB800]/10 text-[#FFB800] border border-[#FFB800]/30'
                      : type === 'success' ? 'bg-[#00FF66]/10 text-[#00FF66] border border-[#00FF66]/30'
                      : 'bg-[#00F0FF]/10 text-[#00F0FF] border border-[#00F0FF]/30';
        const titleSize = type === 'urgent' ? 'text-2xl' : 'text-xl';
        const bodyColor = type === 'urgent' ? 'text-gray-300' : 'text-gray-400';
        const glowStyle = type === 'urgent' ? ' style="text-shadow: 0 0 10px rgba(255,42,85,0.4)"' : '';
        const timeLabel = _resolveAnnouncementTimeLabel(ann);

        return `
          <div class="premium-card p-6 md:p-8 border-l-4 ${borderStyle}" style="border-left-color:${borderColor}">
            ${type === 'urgent' ? '<div class="absolute right-0 top-0 p-6 opacity-5 pointer-events-none"><i data-lucide="siren" class="w-32 h-32 text-[#FF2A55]"></i></div>' : ''}
            <div class="flex items-center gap-3 mb-4 relative z-10">
              ${ann.is_pinned ? '<span class="hub-badge bg-[#FF2A55]/20 text-[#FF8AA0] border border-[#FF2A55]/40" style="box-shadow: 0 0 15px rgba(255,42,85,0.3)"><i data-lucide="pin" class="w-3 h-3"></i> Pinned</span>' : ''}
              <span class="hub-badge ${badgeBg}">${_esc(ann.type || 'Info')}</span>
              <span class="font-mono text-[10px] text-gray-400" data-ann-created-at="${_esc(ann.created_at || ann.createdAt || ann.timestamp || '')}">${_esc(timeLabel)}</span>
            </div>
            ${ann.title ? `<h3 class="font-display font-bold ${titleSize} text-white mb-3 relative z-10"${glowStyle}>${_esc(ann.title)}</h3>` : ''}
            <p class="text-sm ${bodyColor} leading-relaxed relative z-10 max-w-3xl">${_esc(ann.message)}</p>
          </div>`;
      }).join('');

      if (feed) {
        feed.innerHTML = html || `<div class="premium-card p-10 flex flex-col items-center justify-center text-center">
          <div class="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center mb-4">
            <i data-lucide="radio" class="w-8 h-8 text-gray-600"></i>
          </div>
          <h3 class="font-display text-lg font-bold text-white mb-2">No announcements yet</h3>
          <p class="text-sm text-gray-500 max-w-md">Organizer updates will appear here in real-time.</p>
        </div>`;
      }

      _renderOverviewAnnouncements(source);

      // Update count
      const countEl = document.getElementById('hub-ann-count');
      if (countEl) {
        const n = filtered.length;
        const total = source.length;
        countEl.textContent = n === total
          ? `${n} update${n !== 1 ? 's' : ''}`
          : `${n}/${total} updates`;
      }

      const loadMoreWrap = document.getElementById('hub-ann-load-more-wrap');
      if (loadMoreWrap) {
        loadMoreWrap.classList.toggle('hidden', !_announcementHasMore);
        loadMoreWrap.classList.toggle('flex', _announcementHasMore);
      }

      const filters = document.getElementById('hub-ann-filters');
      if (filters) {
        filters.querySelectorAll('[data-hub-feed-filter]').forEach((btn) => {
          const f = btn.getAttribute('data-hub-feed-filter');
          const active = f === _announcementFilter || (f === 'all' && _announcementFilter === 'all');
          btn.classList.toggle('bg-white/10', active);
          btn.classList.toggle('text-white', active);
          btn.classList.toggle('font-bold', active);
          btn.classList.toggle('text-gray-500', !active);
          btn.classList.toggle('font-medium', !active);
        });
      }

      if (typeof lucide !== 'undefined') lucide.createIcons();
    }

  function _renderOverviewAnnouncements(items) {
      const feed = document.getElementById('hub-overview-announcements-feed');
      if (!feed) return;

      const source = _sortAnnouncementsCanonical(items).slice(0, 5);
      const html = source.map((ann, index) => {
        const type = String(ann?.type || 'info').toLowerCase();
        const iconClass = OVERVIEW_ANN_ICON_CLASS[type] || OVERVIEW_ANN_ICON_CLASS.info;
        const cardToneClass = index === 0 ? OVERVIEW_ANN_ITEM_LATEST_CLASS : OVERVIEW_ANN_ITEM_DEFAULT_CLASS;
        const timeLabel = _resolveAnnouncementTimeLabel(ann);
        return `
          <article class="${OVERVIEW_ANN_ITEM_CLASS} ${cardToneClass}">
            <div class="${iconClass} mt-0.5 inline-flex h-9 w-9 items-center justify-center rounded-lg border">
              <i data-lucide="${_esc(ann.icon || 'megaphone')}" class="w-3.5 h-3.5"></i>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-2">
                <p class="truncate text-sm font-semibold text-white">${_esc(ann.title || 'Announcement')}</p>
                <span class="shrink-0 font-mono text-[9px] text-zinc-500" data-ann-created-at="${_esc(ann.created_at || '')}">${_esc(timeLabel)}</span>
              </div>
              <p class="mt-1 text-[11px] leading-relaxed text-zinc-400">${_esc(ann.message || '')}</p>
            </div>
          </article>`;
      }).join('');

      feed.innerHTML = html || '<div class="flex flex-col items-center justify-center rounded-xl border border-white/8 bg-black/20 py-10 text-center"><i data-lucide="radio" class="mb-3 h-8 w-8 text-zinc-700"></i><p class="text-sm text-zinc-500">No announcements yet</p><p class="mt-1 text-xs text-zinc-600">Organizer updates will appear here.</p></div>';
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
        headers: _csrfHeaders({
          'Content-Type': 'application/json',
        }),
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
      _emitToast(isError ? 'error' : 'success', message);
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
          const label = _ordinal(place) + ' Place';

          // Tier-specific visual treatment
          let tierIcon, tierGlow;
          if (place === '1') {
            tierIcon = `<div style="background:linear-gradient(135deg,#FFB800,#E08800);box-shadow:0 0 25px rgba(255,184,0,0.35);" class="w-12 h-12 rounded-xl flex items-center justify-center mb-3 mx-auto"><i data-lucide="trophy" class="w-6 h-6 text-white"></i></div>`;
            tierGlow = '';
          } else if (place === '2') {
            tierIcon = `<div style="background:linear-gradient(135deg,#D0D0D0,#909090);box-shadow:0 0 20px rgba(192,192,192,0.2);" class="w-12 h-12 rounded-xl flex items-center justify-center mb-3 mx-auto"><i data-lucide="medal" class="w-6 h-6 text-gray-900"></i></div>`;
            tierGlow = '';
          } else if (place === '3') {
            tierIcon = `<div style="background:linear-gradient(135deg,#CD7F32,#7B4A1A);box-shadow:0 0 20px rgba(205,127,50,0.2);" class="w-12 h-12 rounded-xl flex items-center justify-center mb-3 mx-auto"><i data-lucide="award" class="w-6 h-6 text-white"></i></div>`;
            tierGlow = '';
          } else {
            tierIcon = `<div class="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-3 mx-auto border border-white/10"><i data-lucide="gift" class="w-6 h-6 text-gray-400"></i></div>`;
            tierGlow = '';
          }

          html += `
            <div class="prize-placement-card ${cardClass} text-center ${tierGlow}">
              ${tierIcon}
              <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">${_esc(label)}</p>
              <p class="text-2xl font-black text-[#FFB800]" style="font-family:Outfit,sans-serif;">${_esc(String(share))}</p>
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
            ? `<button class="prize-claim-btn" data-click="HubEngine.openPrizeModal" data-click-args="[&quot;${p.id}&quot;,&quot;${_esc(p.amount)}&quot;,&quot;${_esc(p.placement_display)}&quot;]">Claim Prize</button>`
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
        headers: _csrfHeaders({
          'Content-Type': 'application/json',
        }),
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
      _syncResourcesQuickNav({ hasRules: false, hasSocial: false, hasSponsors: false });
      _setResourcesEmptyState(
        'No resources available yet',
        'The organizer has not published any resources for this tournament yet.',
        false,
      );
      return;
    }

    _syncResourcesQuickNav({
      hasRules: Boolean(hasRules),
      hasSocial: Boolean(hasSocial || hasContact || hasSupportInfo),
      hasSponsors: Boolean(hasSponsors),
    });

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
          discord: 'message-circle', twitter: 'at-sign', instagram: 'camera',
          youtube: 'play', facebook: 'users', tiktok: 'music',
          website: 'globe', twitch: 'tv', youtube_stream: 'radio',
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
        const seenSocial = new Set();
        const uniqueLinks = data.social_links.filter((link) => {
          const normUrl = String(link.url || '').trim().toLowerCase();
          if (!normUrl) return false;
          const dedupeKey = `${link.key || ''}|${normUrl}`;
          if (seenSocial.has(dedupeKey)) return false;
          seenSocial.add(dedupeKey);
          return true;
        });

        uniqueLinks.forEach((link, idx) => {
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

  function _bindResourcesQuickNav() {
    const nav = document.getElementById('resources-quick-nav');
    if (!nav || nav.dataset.bound === '1') return;

    nav.dataset.bound = '1';
    nav.querySelectorAll('[data-hub-resource-target]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-hub-resource-target');
        if (!targetId) return;

        const target = document.getElementById(targetId);
        if (!target || target.classList.contains('hidden')) return;

        nav.querySelectorAll('[data-hub-resource-target]').forEach((b) => {
          const isActive = b === btn;
          b.classList.toggle('bg-cyan-400/15', isActive);
          b.classList.toggle('text-cyan-200', isActive);
          b.classList.toggle('border-cyan-400/30', isActive);
          b.classList.toggle('border-white/15', !isActive);
          b.classList.toggle('text-gray-300', !isActive);
        });

        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  function _syncResourcesQuickNav(flags) {
    const nav = document.getElementById('resources-quick-nav');
    if (!nav) return;

    const map = {
      rules: Boolean(flags?.hasRules),
      social: Boolean(flags?.hasSocial),
      sponsors: Boolean(flags?.hasSponsors),
    };

    nav.querySelectorAll('[data-hub-resource-key]').forEach((btn) => {
      const key = btn.getAttribute('data-hub-resource-key');
      const enabled = Boolean(map[key]);
      btn.classList.toggle('hidden', !enabled);
      btn.disabled = !enabled;
    });
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

  function _initials(name, maxChars = 2) {
    const safe = String(name || '').trim();
    if (!safe) return '?';
    const parts = safe.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0].charAt(0) + parts[1].charAt(0)).toUpperCase().slice(0, maxChars);
    }
    return safe.slice(0, maxChars).toUpperCase();
  }

  function _loadBrokenAvatarUrlCache() {
    try {
      const raw = window.sessionStorage.getItem(BROKEN_AVATAR_CACHE_KEY);
      if (!raw) return;
      const values = JSON.parse(raw);
      if (!Array.isArray(values)) return;
      values.forEach((value) => {
        const url = String(value || '').trim();
        if (url) _brokenAvatarUrls.add(url);
      });
    } catch (_err) {
      // Ignore malformed cache.
    }
  }

  function _persistBrokenAvatarUrlCache() {
    try {
      const values = Array.from(_brokenAvatarUrls).slice(-180);
      window.sessionStorage.setItem(BROKEN_AVATAR_CACHE_KEY, JSON.stringify(values));
    } catch (_err) {
      // Ignore storage failures.
    }
  }

  function _loadOutcomeDismissState() {
    _dismissedOutcomeKeys.clear();
    try {
      const raw = window.localStorage.getItem(OUTCOME_DISMISS_KEY);
      if (!raw) return;
      const values = JSON.parse(raw);
      if (!Array.isArray(values)) return;
      values.forEach((value) => {
        const key = String(value || '').trim();
        if (key) _dismissedOutcomeKeys.add(key);
      });
    } catch (_err) {
      // Ignore malformed storage payload.
    }
  }

  function _persistOutcomeDismissState() {
    try {
      const values = Array.from(_dismissedOutcomeKeys).slice(-200);
      window.localStorage.setItem(OUTCOME_DISMISS_KEY, JSON.stringify(values));
    } catch (_err) {
      // Ignore storage failures.
    }
  }

  function _isOutcomeDismissed(key) {
    const normalized = String(key || '').trim();
    if (!normalized) return false;
    return _dismissedOutcomeKeys.has(normalized);
  }

  function _normalizeGameAlias(rawValue) {
    return String(rawValue || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  function _resolveOverviewGameBranding() {
    if (_overviewGameBranding) {
      return _overviewGameBranding;
    }

    const rawSlug = String(_shell?.dataset.gameSlug || '').trim();
    const rawName = String(_shell?.dataset.gameName || '').trim();
    const candidates = [rawSlug, rawName];

    let normalized = '';
    let logoFile = '';
    for (const raw of candidates) {
      const candidate = _normalizeGameAlias(raw);
      if (!candidate) continue;
      if (HUB_GAME_LOGO_MAP[candidate]) {
        normalized = candidate;
        logoFile = HUB_GAME_LOGO_MAP[candidate];
        break;
      }
      if (!normalized) {
        normalized = candidate;
      }
    }

    _overviewGameBranding = {
      normalized,
      displayName: rawName || rawSlug || 'Tournament',
      logoFile,
      logoUrl: logoFile ? `${GAME_LOGO_BASE_PATH}${logoFile}` : '',
    };
    return _overviewGameBranding;
  }

  function _applyOverviewGameBranding() {
    const branding = _resolveOverviewGameBranding();
    const logoSlots = [
      'hub-overview-game-logo',
      'hub-overview-intel-game-logo',
      'hub-overview-outcome-spotlight-logo',
      'hub-overview-share-preview-logo',
    ];

    logoSlots.forEach((id) => {
      const img = document.getElementById(id);
      if (!img) return;
      const fallback = img.parentElement ? img.parentElement.querySelector('i[data-lucide]') : null;

      if (branding.logoUrl) {
        img.src = branding.logoUrl;
        img.alt = `${branding.displayName} logo`;
        img.classList.remove('hidden');
        if (fallback) {
          fallback.classList.add('hidden');
        }
      } else {
        img.removeAttribute('src');
        img.classList.add('hidden');
        if (fallback) {
          fallback.classList.remove('hidden');
        }
      }
    });

    const ghost = document.getElementById('hub-overview-outcome-spotlight-ghost');
    if (ghost) {
      ghost.style.backgroundImage = branding.logoUrl ? `url("${branding.logoUrl}")` : '';
      ghost.classList.toggle('is-empty', !branding.logoUrl);
    }

    const heroGameName = document.getElementById('hub-overview-hero-game-name');
    if (heroGameName && branding.displayName) {
      heroGameName.textContent = branding.displayName;
    }
  }

  function _stopOverviewHeroFx() {
    if (_heroFxAnimId) {
      cancelAnimationFrame(_heroFxAnimId);
      _heroFxAnimId = null;
    }

    const canvas = document.getElementById('hub-overview-hero-fx-canvas');
    if (!canvas || typeof canvas.getContext !== 'function') {
      _heroFxParticles = [];
      return;
    }

    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width || 0, canvas.height || 0);
    }
    _heroFxParticles = [];
  }

  function _startOverviewHeroFx() {
    const card = document.getElementById('hub-overview-action-card');
    const canvas = document.getElementById('hub-overview-hero-fx-canvas');
    if (!card || !canvas || typeof canvas.getContext !== 'function') return;

    const reducedMotion = Boolean(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    if (card.classList.contains('hidden') || reducedMotion) {
      _stopOverviewHeroFx();
      return;
    }

    if (_heroFxAnimId) {
      return;
    }

    const ratio = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeCanvas = () => {
      const rect = card.getBoundingClientRect();
      const width = Math.max(1, Math.floor(rect.width));
      const height = Math.max(1, Math.floor(rect.height));
      canvas.width = Math.floor(width * ratio);
      canvas.height = Math.floor(height * ratio);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      return { width, height };
    };

    let bounds = resizeCanvas();
    const desiredCount = Math.max(16, Math.round(bounds.width / 52));
    _heroFxParticles = Array.from({ length: desiredCount }).map(() => ({
      x: Math.random() * bounds.width,
      y: Math.random() * bounds.height,
      vx: (Math.random() - 0.5) * 0.18,
      vy: -(Math.random() * 0.26 + 0.06),
      size: Math.random() * 1.7 + 0.6,
      alpha: Math.random() * 0.26 + 0.08,
      decay: Math.random() * 0.0014 + 0.0005,
    }));

    const frame = () => {
      if (!canvas.isConnected || card.classList.contains('hidden')) {
        _stopOverviewHeroFx();
        return;
      }

      const nextRect = card.getBoundingClientRect();
      if (Math.abs(nextRect.width - bounds.width) > 1 || Math.abs(nextRect.height - bounds.height) > 1) {
        bounds = resizeCanvas();
      }

      ctx.clearRect(0, 0, bounds.width, bounds.height);

      _heroFxParticles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.alpha = Math.max(0, p.alpha - p.decay);

        if (p.y < -8 || p.alpha <= 0) {
          p.x = Math.random() * bounds.width;
          p.y = bounds.height + (Math.random() * 16);
          p.alpha = Math.random() * 0.26 + 0.08;
          p.size = Math.random() * 1.7 + 0.6;
        }

        if (p.x < -10) p.x = bounds.width + 8;
        if (p.x > bounds.width + 10) p.x = -8;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(56, 189, 248, ${Math.max(0.04, p.alpha)})`;
        ctx.shadowBlur = 8;
        ctx.shadowColor = 'rgba(34, 211, 238, 0.24)';
        ctx.fill();
      });

      ctx.shadowBlur = 0;
      _heroFxAnimId = requestAnimationFrame(frame);
    };

    frame();
  }

  function _mountOutcomeSpotlightToBody() {
    const overlay = document.getElementById('hub-overview-outcome-spotlight');
    if (!overlay || overlay.dataset.portalMounted === '1') return;
    try {
      document.body.appendChild(overlay);
      overlay.dataset.portalMounted = '1';
    } catch (_err) {
      // Keep inline rendering fallback if body append fails.
    }
  }

  function _stopOutcomeSpotlightFx() {
    if (_outcomeFxAnimId) {
      cancelAnimationFrame(_outcomeFxAnimId);
      _outcomeFxAnimId = null;
    }
    const canvas = document.getElementById('hub-overview-spotlight-fx-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext && canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width || 0, canvas.height || 0);
    _outcomeFxParticles = [];
  }

  function _startOutcomeSpotlightFx() {
    const canvas = document.getElementById('hub-overview-spotlight-fx-canvas');
    if (!canvas || typeof canvas.getContext !== 'function') return;

    const spotlight = document.getElementById('hub-overview-outcome-spotlight');
    const state = String(spotlight?.getAttribute('data-outcome-state') || 'advanced').toLowerCase();
    const isEliminated = state === 'eliminated';
    const ratio = Math.max(1, Math.min(window.devicePixelRatio || 1, 2));

    const resizeCanvas = () => {
      const width = window.innerWidth || document.documentElement.clientWidth || 1;
      const height = window.innerHeight || document.documentElement.clientHeight || 1;
      canvas.width = Math.floor(width * ratio);
      canvas.height = Math.floor(height * ratio);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      }
    };

    resizeCanvas();

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    _outcomeFxParticles = Array.from({ length: isEliminated ? 28 : 44 }).map(() => ({
      x: Math.random() * (window.innerWidth || 1),
      y: isEliminated ? Math.random() * (window.innerHeight || 1) : (window.innerHeight || 1) + (Math.random() * 160),
      vx: (Math.random() - 0.5) * (isEliminated ? 0.22 : 0.62),
      vy: isEliminated ? (Math.random() * 0.34 + 0.08) : -(Math.random() * 1.45 + 0.42),
      size: isEliminated ? (Math.random() * 1.4 + 0.5) : (Math.random() * 2.4 + 0.7),
      alpha: isEliminated ? (Math.random() * 0.3 + 0.08) : (Math.random() * 0.45 + 0.24),
      decay: isEliminated ? 0.0004 : 0.0031,
    }));

    const baseColor = isEliminated ? '182, 190, 204' : '0, 229, 255';

    const frame = () => {
      if (!document.body.classList.contains('hub-outcome-open')) {
        _stopOutcomeSpotlightFx();
        return;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      _outcomeFxParticles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.alpha = Math.max(0, p.alpha - p.decay);

        if (isEliminated) {
          if (p.y > (window.innerHeight || 1) + 12 || p.alpha <= 0) {
            p.y = -10;
            p.x = Math.random() * (window.innerWidth || 1);
            p.alpha = Math.random() * 0.28 + 0.08;
          }
        } else if (p.y < -15 || p.alpha <= 0) {
          p.y = (window.innerHeight || 1) + 12;
          p.x = Math.random() * (window.innerWidth || 1);
          p.alpha = Math.random() * 0.45 + 0.25;
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${baseColor}, ${Math.max(0.04, p.alpha)})`;
        ctx.shadowBlur = isEliminated ? 0 : 10;
        ctx.shadowColor = isEliminated ? 'transparent' : `rgba(${baseColor}, 0.7)`;
        ctx.fill();
      });

      ctx.shadowBlur = 0;
      _outcomeFxAnimId = requestAnimationFrame(frame);
    };

    frame();
  }

  function _openOutcomeSpotlight({ force = false } = {}) {
    const spotlight = document.getElementById('hub-overview-outcome-spotlight');
    if (!spotlight) return;

    _dismissOutcomeShareModal();

    const key = String(spotlight.dataset.outcomeKey || '').trim();
    if (!key) return;
    if (!force && _isOutcomeDismissed(key)) return;

    document.body.classList.add('hub-outcome-open');
    spotlight.classList.remove('hidden');
    spotlight.classList.remove('is-open');
    void spotlight.offsetWidth;
    spotlight.classList.add('is-open');
    spotlight.setAttribute('aria-hidden', 'false');

    _startOutcomeSpotlightFx();
  }

  function _dismissOutcomeSpotlight(options = {}) {
    const persist = options?.persist !== false;
    _dismissOutcomeShareModal();
    document.body.classList.remove('hub-outcome-open');
    _stopOutcomeSpotlightFx();
    const spotlight = document.getElementById('hub-overview-outcome-spotlight');
    if (!spotlight) return;

    const key = String(spotlight.dataset.outcomeKey || '').trim();
    if (persist && key) {
      _dismissedOutcomeKeys.add(key);
      _persistOutcomeDismissState();
    }

    spotlight.classList.remove('is-open');
    spotlight.classList.add('hidden');
    spotlight.setAttribute('aria-hidden', 'true');
  }

  function openOutcomeSpotlight() {
    _openOutcomeSpotlight({ force: true });
  }

  function _dismissOutcomeShareModal() {
    document.body.classList.remove('hub-share-open');
    const shareTrigger = document.getElementById('hub-overview-outcome-spotlight-share-trigger');
    if (shareTrigger) {
      shareTrigger.setAttribute('aria-expanded', 'false');
    }
    const actionBar = document.getElementById('hub-overview-outcome-spotlight-action-bar');
    if (actionBar) {
      actionBar.classList.remove('hidden');
    }
    const modal = document.getElementById('hub-overview-share-modal');
    if (!modal) return;
    modal.classList.remove('is-open');
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
  }

  function _openOutcomeShareModal() {
    const modal = document.getElementById('hub-overview-share-modal');
    if (!modal) return;

    if (!_outcomeSharePayload) {
      _emitToast('info', 'No result spotlight is available to share yet.');
      return;
    }

    const previewTitle = document.getElementById('hub-overview-share-preview-title');
    const previewBody = document.getElementById('hub-overview-share-preview-body');
    const caption = document.getElementById('hub-overview-share-caption');
    const actionBar = document.getElementById('hub-overview-outcome-spotlight-action-bar');
    const shareTrigger = document.getElementById('hub-overview-outcome-spotlight-share-trigger');

    if (previewTitle) {
      previewTitle.textContent = _outcomeSharePayload.title || 'Result Spotlight';
    }
    if (previewBody) {
      previewBody.textContent = _outcomeSharePayload.body || 'Post your moment to the community feed.';
    }
    if (caption) {
      caption.value = _outcomeSharePayload.caption || '';
    }

    _applyOverviewGameBranding();

    const spotlight = document.getElementById('hub-overview-outcome-spotlight');
    if (spotlight && spotlight.classList.contains('hidden')) {
      _openOutcomeSpotlight({ force: true });
      if (spotlight.classList.contains('hidden')) {
        _emitToast('info', 'Open the result spotlight before editing your caption.');
        return;
      }
    }

    modal.classList.remove('hidden');
    modal.classList.remove('is-open');
    void modal.offsetWidth;
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    if (actionBar) {
      actionBar.classList.add('hidden');
    }
    if (shareTrigger) {
      shareTrigger.setAttribute('aria-expanded', 'true');
    }
    document.body.classList.add('hub-share-open');

    if (caption) {
      setTimeout(() => {
        caption.focus();
        caption.setSelectionRange(caption.value.length, caption.value.length);
      }, 40);
    }
  }

  async function _copyOutcomeShareCaption() {
    const caption = document.getElementById('hub-overview-share-caption');
    const text = String(caption?.value || _outcomeSharePayload?.caption || '').trim();
    if (!text) {
      _emitToast('warning', 'Caption is empty.');
      return;
    }

    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const helper = document.createElement('textarea');
        helper.value = text;
        helper.style.position = 'fixed';
        helper.style.left = '-9999px';
        document.body.appendChild(helper);
        helper.focus();
        helper.select();
        document.execCommand('copy');
        document.body.removeChild(helper);
      }
      _emitToast('success', 'Share caption copied.');
    } catch (_err) {
      _emitToast('warning', 'Copy failed. Select the caption manually.');
    }
  }

  function _submitOutcomeShare() {
    const caption = document.getElementById('hub-overview-share-caption');
    const text = String(caption?.value || '').trim();
    if (!text) {
      _emitToast('warning', 'Add a caption before posting.');
      return;
    }
    _outcomeSharePayload = {
      ...(_outcomeSharePayload || {}),
      caption: text,
    };
    _emitToast('success', 'Caption is ready to post in community channels.');
    _dismissOutcomeShareModal();
  }

  function _markAvatarUrlBroken(url) {
    const key = String(url || '').trim();
    if (!key) return;
    if (_brokenAvatarUrls.has(key)) return;
    _brokenAvatarUrls.add(key);
    _persistBrokenAvatarUrlCache();
  }

  function _renderAvatarInitial(name, initialClass = 'stnd-team-initial') {
    return `<span class="${initialClass}">${_esc(_initials(name, 2))}</span>`;
  }

  function _renderAvatarInner(name, mediaUrl, initialClass = 'stnd-team-initial', imageClass = 'stnd-team-avatar-img') {
    const safeNameRaw = String(name || 'Participant');
    const safeName = _esc(safeNameRaw);
    const normalizedUrl = String(mediaUrl || '').trim();

    if (normalizedUrl && !_brokenAvatarUrls.has(normalizedUrl)) {
      return `<img src="${_esc(normalizedUrl)}" class="${imageClass}" alt="${safeName}" loading="lazy" decoding="async" data-avatar-name="${safeName}" data-avatar-url="${_esc(normalizedUrl)}" data-avatar-initial-class="${_esc(initialClass)}" data-fallback="hide">`;
    }
    return _renderAvatarInitial(safeNameRaw, initialClass);
  }

  function handleAvatarLoadError(imageEl) {
    if (!imageEl) return;

    const failedUrl = String(
      imageEl.getAttribute('data-avatar-url') || imageEl.getAttribute('src') || ''
    ).trim();
    if (failedUrl) {
      _markAvatarUrlBroken(failedUrl);
    }

    const parent = imageEl.parentElement;
    if (!parent) return;

    const fallbackName = imageEl.getAttribute('data-avatar-name') || imageEl.getAttribute('alt') || 'Participant';
    const initialClass = imageEl.getAttribute('data-avatar-initial-class') || 'stnd-team-initial';
    parent.innerHTML = _renderAvatarInitial(fallbackName, initialClass);
  }

  function _humanTournamentStatus(rawStatus) {
    const status = String(rawStatus || '').toLowerCase();
    const labels = {
      registration_open: 'Registration Open',
      registration_closed: 'Registration Closed',
      check_in: 'Check-In',
      live: 'Live',
      completed: 'Completed',
      cancelled: 'Cancelled',
      draft: 'Draft',
      published: 'Published',
    };
    return labels[status] || (status ? (status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, ' ')) : 'Status');
  }

  function _statusBadgeClass(rawStatus) {
    const status = String(rawStatus || '').toLowerCase();
    if (status === 'live') return 'hub-badge-live';
    if (status === 'check_in') return 'hub-badge-warning';
    if (status === 'completed' || status === 'cancelled') return 'hub-badge-neutral';
    return 'hub-badge-info';
  }

  function _overviewTitleFromStatus(rawStatus) {
    const status = String(rawStatus || '').toLowerCase();
    if (status === 'live') return 'LIVE / IN PROGRESS';
    if (status === 'registration_open') return 'REGISTRATION OPEN';
    if (status === 'registration_closed' || status === 'check_in') return 'AWAITING START';
    if (status === 'completed') return 'TOURNAMENT COMPLETE';
    return '';
  }

  function _syncTournamentStatusUi(rawStatus) {
    const status = String(rawStatus || '').toLowerCase();
    if (!status) return;

    if (_shell) {
      _shell.dataset.tournamentStatus = status;
    }

    const badge = document.getElementById('hub-tournament-status-badge');
    if (badge) {
      badge.className = `hub-badge ${_statusBadgeClass(status)}`;
    }

    const badgeText = document.getElementById('hub-tournament-status-text');
    if (badgeText) {
      badgeText.textContent = _humanTournamentStatus(status);
    }

    const dot = document.getElementById('hub-tournament-status-dot');
    if (dot) {
      const isLive = status === 'live';
      dot.classList.toggle('hidden', !isLive);
      dot.className = `w-1.5 h-1.5 rounded-full ${isLive ? 'bg-[#00FF66] animate-pulse' : 'bg-transparent hidden'}`;
    }

    const overviewTitle = document.getElementById('hub-overview-title');
    const nextTitle = _overviewTitleFromStatus(status);
    if (overviewTitle && nextTitle) {
      overviewTitle.textContent = nextTitle;
    }
  }

  function _updateOverviewPhaseEvent(phaseEvent) {
    const labelEl = document.getElementById('hub-overview-phase-label');
    if (labelEl && phaseEvent?.label) {
      labelEl.textContent = phaseEvent.label;
    }

    const timeLabel = document.getElementById('hub-overview-action-time-label');
    if (timeLabel && phaseEvent?.label) {
      if (!document.getElementById('hub-overview-action-time')?.dataset.matchTime) {
        timeLabel.textContent = `${phaseEvent.label} In`;
      }
    }

    const pill = document.getElementById('hub-overview-phase-pill');
    if (!pill) return;

    const type = String(phaseEvent?.type || 'info').toLowerCase();
    const current = OVERVIEW_PHASE_STYLES[type] || OVERVIEW_PHASE_STYLES.info;
    pill.className = current.wrap;

    const dotEl = pill.querySelector('span');
    if (dotEl) {
      dotEl.className = current.dot;
    }

    if (labelEl) {
      labelEl.className = current.label;
    }
  }

  function _formatCountdownLabel(targetDate) {
    if (!(targetDate instanceof Date) || Number.isNaN(targetDate.getTime())) {
      return 'TBD';
    }
    const diffMs = targetDate.getTime() - Date.now();
    if (diffMs <= 0) return 'Now';
    const totalMinutes = Math.floor(diffMs / 60000);
    const days = Math.floor(totalMinutes / (60 * 24));
    const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
    const mins = totalMinutes % 60;
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${String(mins).padStart(2, '0')}m`;
    return `${mins}m`;
  }

  function _toValidDate(value) {
    if (!value) return null;
    const dt = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(dt.getTime())) return null;
    return dt;
  }

  function _resolveLobbyWindow(match) {
    // ── Canonical lobby state from backend (single source of truth) ──
    // When the backend sends lobby_state, trust it completely.
    const backendState = match?.lobby_state || '';
    if (backendState) {
      const scheduledAt = _toValidDate(match?.scheduled_at);
      const opensAt = _toValidDate(match?.lobby_window_opens_at);
      const closesAt = _toValidDate(match?.lobby_closes_at);
      const rawMinutes = Number.parseInt(String(match?.lobby_window_minutes_before ?? ''), 10);
      const minutesBefore = Number.isFinite(rawMinutes) && rawMinutes > 0
        ? rawMinutes
        : PRE_MATCH_LOBBY_WINDOW_MINUTES;
      const isOpen = backendState === 'lobby_open' || backendState === 'live_grace_or_ready';
      const isClosed = backendState === 'lobby_closed' || backendState === 'forfeit_review';
      const canEnter = match?.lobby_can_enter === true;
      const canReschedule = match?.lobby_can_reschedule === true;
      return {
        isOpen,
        isClosed,
        canEnter,
        canReschedule,
        lobbyState: backendState,
        minutesBefore,
        opensAt,
        closesAt,
        scheduledAt,
        policySummary: match?.lobby_policy_summary || '',
        startsInSeconds: Number.isFinite(Number(match?.lobby_window_starts_in_seconds))
          ? Number(match?.lobby_window_starts_in_seconds)
          : null,
      };
    }

    // ── Fallback: compute locally (legacy / non-hub surfaces) ──
    const state = String(match?.state || '').toLowerCase();
    const terminal = ['completed', 'forfeit', 'cancelled', 'disputed'].includes(state);
    const forcedOpen = ['ready', 'live', 'pending_result'].includes(state);

    const rawMinutes = Number.parseInt(String(match?.lobby_window_minutes_before ?? ''), 10);
    const minutesBefore = Number.isFinite(rawMinutes) && rawMinutes > 0
      ? rawMinutes
      : PRE_MATCH_LOBBY_WINDOW_MINUTES;

    const scheduledAt = _toValidDate(match?.scheduled_at);
    const opensAtFromApi = _toValidDate(match?.lobby_window_opens_at);
    const opensAt = opensAtFromApi || (scheduledAt ? new Date(scheduledAt.getTime() - (minutesBefore * 60 * 1000)) : null);

    const LOBBY_CLOSE_AFTER_MINUTES = 10;
    const closesAtFromApi = _toValidDate(match?.lobby_closes_at);
    const closesAt = closesAtFromApi || (scheduledAt ? new Date(scheduledAt.getTime() + (LOBBY_CLOSE_AFTER_MINUTES * 60 * 1000)) : null);
    const isClosed = !forcedOpen && closesAt ? Date.now() > closesAt.getTime() : false;

    const isOpen = !terminal && !isClosed && (
      forcedOpen
      || (opensAt ? Date.now() >= opensAt.getTime() : false)
    );

    return {
      isOpen,
      isClosed,
      canEnter: isOpen,
      canReschedule: isClosed && !terminal,
      lobbyState: terminal ? 'completed' : (forcedOpen ? 'live_grace_or_ready' : (isClosed ? 'lobby_closed' : (isOpen ? 'lobby_open' : 'upcoming_not_open'))),
      minutesBefore,
      opensAt,
      closesAt,
      scheduledAt,
      policySummary: '',
      startsInSeconds: Number.isFinite(Number(match?.lobby_window_starts_in_seconds))
        ? Number(match?.lobby_window_starts_in_seconds)
        : null,
    };
  }

  function _pickOverviewTargetMatch(matches) {
    const all = Array.isArray(matches) ? matches : [];
    if (!all.length) return null;

    const nonTerminal = all.filter((m) => !['completed', 'forfeit', 'cancelled'].includes(String(m?.state || '').toLowerCase()));
    if (!nonTerminal.length) return null;

    const live = nonTerminal.find((m) => String(m?.state || '').toLowerCase() === 'live');
    if (live) return live;

    const incomingReschedule = _collectIncomingRescheduleMatches(nonTerminal)[0];
    if (incomingReschedule) return incomingReschedule;

    const lobbyOpen = nonTerminal.find((m) => {
      const windowInfo = _resolveLobbyWindow(m);
      return windowInfo.isOpen && Boolean(m?.match_room_url);
    });
    if (lobbyOpen) return lobbyOpen;

    const ready = nonTerminal.find((m) => ['ready', 'check_in', 'pending_result'].includes(String(m?.state || '').toLowerCase()));
    if (ready) return ready;

    const scheduled = nonTerminal
      .filter((m) => m?.scheduled_at)
      .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at));

    if (scheduled.length) {
      const now = Date.now();
      const upcoming = scheduled.find((m) => {
        const dt = new Date(m.scheduled_at);
        return !Number.isNaN(dt.getTime()) && dt.getTime() >= now;
      });
      return upcoming || scheduled[0];
    }

    return nonTerminal[0];
  }

  function _collectIncomingRescheduleMatches(matches) {
    const all = Array.isArray(matches) ? matches : [];
    const seen = new Set();
    return all.filter((m) => {
      const pendingId = String(m?.reschedule?.pending_request?.id || '').trim();
      if (!pendingId) return false;
      if (!m?.reschedule?.can_respond) return false;
      if (seen.has(pendingId)) return false;
      seen.add(pendingId);
      return true;
    });
  }

  function _renderIncomingRescheduleInbox(matches) {
    const incoming = _collectIncomingRescheduleMatches(matches);
    if (!incoming.length) return '';

    const cards = incoming.slice(0, 3).map((m) => {
      const matchId = JSON.stringify(String(m.id || ''));
      const proposedAt = _formatRescheduleDatetimeLabel(m?.reschedule?.pending_request?.new_time);
      const opponent = m?.opponent_name || m?.p2_name || m?.p1_name || 'your opponent';
      const canCounter = Boolean(m?.reschedule?.can_counter_offer);

      return `
        <div class="hub-glass rounded-xl border border-amber-300/30 bg-gradient-to-br from-amber-300/12 via-[#0e1222]/88 to-[#0a1220]/92 p-3">
          <div class="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div class="min-w-0">
              <p class="text-[10px] font-black uppercase tracking-[0.18em] text-amber-200">Response Required</p>
              <p class="text-sm font-semibold text-white mt-1">${_esc(m.round_name || 'Round')} · Match ${_esc(String(m.match_number || ''))}</p>
              <p class="text-xs text-gray-300 mt-1">${_esc(opponent)} proposed ${_esc(proposedAt)}.</p>
            </div>
            <div class="flex flex-wrap gap-2 lg:justify-end">
              <button data-click="HubEngine.respondReschedule" data-click-args="[&quot;${matchId}&quot;,&quot;accept&quot;]" class='px-3 py-1.5 rounded-lg border border-[#00FF66]/35 bg-[#00FF66]/12 text-[#66FFAE] text-[10px] font-black uppercase tracking-wider hover:bg-[#00FF66]/20 transition-colors'>Accept</button>
              ${canCounter ? `<button data-click="HubEngine.respondReschedule" data-click-args="[&quot;${matchId}&quot;,&quot;counter&quot;]" class='px-3 py-1.5 rounded-lg border border-blue-400/35 bg-blue-400/15 text-blue-100 text-[10px] font-black uppercase tracking-wider hover:bg-blue-400/25 transition-colors'>Propose New Time</button>` : ''}
              <button data-click="HubEngine.respondReschedule" data-click-args="[&quot;${matchId}&quot;,&quot;reject&quot;]" class='px-3 py-1.5 rounded-lg border border-[#FF2A55]/35 bg-[#FF2A55]/12 text-[#FF97AA] text-[10px] font-black uppercase tracking-wider hover:bg-[#FF2A55]/20 transition-colors'>Reject</button>
            </div>
          </div>
        </div>`;
    }).join('');

    const overflowCount = incoming.length - 3;
    const overflow = overflowCount > 0
      ? `<p class="text-[10px] text-gray-500 uppercase tracking-widest">+${overflowCount} more pending reschedule request${overflowCount > 1 ? 's' : ''} in Match Lobby.</p>`
      : '';

    return `
      <div class="mb-4 space-y-2">
        ${cards}
        ${overflow}
      </div>`;
  }

  function _renderLifecyclePipeline(pipeline) {
    if (!pipeline || !Array.isArray(pipeline.steps)) return;

    const phaseLabel = document.getElementById('hub-lifecycle-phase-label');
    if (phaseLabel && pipeline.phase_label) {
      phaseLabel.textContent = pipeline.phase_label;
    }

    const progress = document.getElementById('hub-lifecycle-progress');
    if (progress && Number.isFinite(Number(pipeline.progress_percent))) {
      const pct = Math.max(0, Math.min(100, Number(pipeline.progress_percent)));
      progress.style.width = `${pct}%`;
    }

    pipeline.steps.forEach((step) => {
      const root = document.getElementById(`hub-pipeline-step-${step.key}`);
      if (!root) return;

      root.classList.remove('is-active', 'is-completed', 'is-upcoming');
      if (step.active) {
        root.classList.add('is-active');
      } else if (step.completed) {
        root.classList.add('is-completed');
      } else {
        root.classList.add('is-upcoming');
      }

      const circle = root.querySelector('[data-pipeline-circle]');
      const label = root.querySelector('[data-pipeline-label]');

      if (circle) {
        if (step.active) {
          circle.className = OVERVIEW_PIPELINE_NODE_CLASS.active;
          circle.innerHTML = '<span class="hub-overview-pipeline-core"></span>';
        } else if (step.completed) {
          circle.className = OVERVIEW_PIPELINE_NODE_CLASS.completed;
          circle.innerHTML = '<span class="hub-overview-pipeline-core"></span>';
        } else {
          circle.className = OVERVIEW_PIPELINE_NODE_CLASS.upcoming;
          circle.innerHTML = '<span class="hub-overview-pipeline-core"></span>';
        }
      }

      if (label) {
        label.textContent = step.label || '';
        if (step.active) {
          label.className = OVERVIEW_PIPELINE_LABEL_CLASS.active;
        } else if (step.completed) {
          label.className = OVERVIEW_PIPELINE_LABEL_CLASS.completed;
        } else {
          label.className = OVERVIEW_PIPELINE_LABEL_CLASS.upcoming;
        }
      }
    });
  }

  function _runOverviewCommandAction(rawAction, backendCommand) {
    const action = String(rawAction || 'view_schedule').toLowerCase();
    const command = backendCommand || {};

    if (action === 'open_result_spotlight' || action === 'view_result_spotlight') {
      _openOutcomeSpotlight({ force: true });
      return;
    }

    if (action === 'open_outcome_share' || action === 'share_result') {
      _openOutcomeShareModal();
      return;
    }

    if (action === 'check_in') {
      performCheckIn();
      return;
    }

    if (action === 'enter_lobby') {
      const targetUrl = command.cta_url || command.match_room_url;
      if (targetUrl) {
        _openMatchRoom(targetUrl);
        return;
      }
      switchTab('matches');
      return;
    }

    if (action === 'respond_reschedule') {
      const matchId = command.match_id || command.matchId;
      if (matchId) {
        respondReschedule(matchId);
        return;
      }
      switchTab('schedule');
      return;
    }

    if (action === 'open_matches' || action === 'view_next_assignment') {
      switchTab('matches');
      return;
    }
    if (action === 'open_bracket') {
      switchTab('bracket');
      return;
    }
    if (action === 'open_standings') {
      switchTab('standings');
      return;
    }
    if (action === 'open_support') {
      switchTab('support');
      return;
    }
    if (action === 'open_announcements') {
      switchTab('announcements');
      return;
    }

    switchTab('schedule');
  }

  function _renderOutcomeCtaButtons(containerEl, ctas, backendCommand, variant) {
    if (!containerEl) return;
    if (variant === 'spotlight') {
      containerEl.innerHTML = '';
      return;
    }
    const rows = Array.isArray(ctas) ? ctas : [];

    const outcomeState = String(backendCommand?.outcome_state || backendCommand?.outcome_experience?.state || '').toLowerCase();
    const iconMap = {
      enter_lobby: 'swords',
      open_bracket: 'git-branch',
      open_matches: 'swords',
      view_next_assignment: 'crosshair',
      open_announcements: 'megaphone',
      open_standings: 'list-ordered',
      open_support: 'life-buoy',
      open_result_spotlight: 'sparkles',
      open_outcome_share: 'send',
      share_result: 'send',
    };

    const normalizeRows = (inputRows) => {
      const unique = new Map();
      inputRows.forEach((cta) => {
        const action = String(cta?.action || '').trim().toLowerCase();
        if (!action || unique.has(action)) return;
        const label = String(cta?.label || action || 'Open').trim() || 'Open';
        unique.set(action, { action, label });
      });
      return Array.from(unique.values());
    };

    let actionRows = [];
    if (variant === 'spotlight') {
      const spotlightRows = normalizeRows(rows.filter((cta) => {
        const action = String(cta?.action || '').toLowerCase();
        return action !== 'open_outcome_share' && action !== 'share_result';
      }));

      const priorityOrder = outcomeState === 'eliminated'
        ? ['open_standings', 'open_bracket', 'open_support', 'open_announcements', 'open_matches']
        : ['enter_lobby', 'open_matches', 'view_next_assignment', 'open_bracket', 'open_announcements', 'open_standings', 'open_support'];

      const seenActions = new Set();
      priorityOrder.forEach((action) => {
        const row = spotlightRows.find((item) => item.action === action);
        if (!row || seenActions.has(action)) return;
        seenActions.add(action);
        actionRows.push(row);
      });

      spotlightRows.forEach((row) => {
        if (seenActions.has(row.action)) return;
        seenActions.add(row.action);
        actionRows.push(row);
      });

      if (!actionRows.length) {
        actionRows.push({
          action: outcomeState === 'eliminated' ? 'open_standings' : 'open_bracket',
          label: outcomeState === 'eliminated' ? 'View Standings' : 'View Bracket',
        });
      }

      actionRows = actionRows.slice(0, 2);
    } else {
      actionRows = normalizeRows(rows).slice(0, 4);
    }

    containerEl.innerHTML = actionRows.map((cta, index) => {
      const action = String(cta?.action || '').trim().toLowerCase();
      const label = String(cta?.label || action || 'Open').trim() || 'Open';
      const icon = iconMap[action] || 'arrow-up-right';
      const buttonClass = variant === 'spotlight'
        ? `hub-outcome-cta-btn ${index === 0 ? 'primary' : 'secondary'}`
        : 'hub-outcome-cta-btn secondary';
      return `<button type="button" data-outcome-action="${_esc(action)}" class="${buttonClass}"><i data-lucide="${icon}" class="w-3.5 h-3.5"></i><span>${_esc(label)}</span></button>`;
    }).join('');

    Array.from(containerEl.querySelectorAll('[data-outcome-action]')).forEach((btn) => {
      btn.onclick = () => {
        const action = btn.getAttribute('data-outcome-action');
        _runOverviewCommandAction(action, backendCommand);
      };
    });

    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }

  function _resolveOutcomeMatchContext(backendCommand, source, target) {
    const allMatches = [
      ...((source && Array.isArray(source.active_matches)) ? source.active_matches : []),
      ...((source && Array.isArray(source.match_history)) ? source.match_history : []),
    ];

    const desiredId = String(backendCommand?.match_id || '').trim();
    let selected = null;
    if (desiredId) {
      selected = allMatches.find((item) => String(item?.id || '') === desiredId) || null;
    }
    if (!selected && target) {
      selected = target;
    }
    if (!selected) {
      selected = allMatches.find((item) => ['completed', 'forfeit', 'disputed', 'pending_result'].includes(String(item?.state || '').toLowerCase())) || null;
    }

    const opponentName = String(
      backendCommand?.opponent_name
      || selected?.opponent_name
      || selected?.p2_name
      || selected?.p1_name
      || 'Pending Opponent'
    ).trim();

    const yourScore = selected?.your_score;
    const oppScore = selected?.opponent_score;
    const p1Score = selected?.p1_score;
    const p2Score = selected?.p2_score;
    const hasPerspectiveScore = Number.isFinite(Number(yourScore)) && Number.isFinite(Number(oppScore));
    const hasPairScore = Number.isFinite(Number(p1Score)) && Number.isFinite(Number(p2Score));
    const scoreline = hasPerspectiveScore
      ? `${yourScore} - ${oppScore}`
      : (hasPairScore ? `${p1Score} - ${p2Score}` : 'Awaiting Verification');

    const stageParts = [];
    if (backendCommand?.match_stage_label || selected?.stage_label || selected?.match_stage_label) {
      stageParts.push(backendCommand?.match_stage_label || selected?.stage_label || selected?.match_stage_label);
    }
    if (backendCommand?.match_round_name || selected?.round_name) {
      stageParts.push(backendCommand?.match_round_name || selected?.round_name);
    }
    if (backendCommand?.match_number || selected?.match_number) {
      stageParts.push(`Match #${backendCommand?.match_number || selected?.match_number}`);
    }

    return {
      selected,
      opponentName,
      scoreline,
      stageText: stageParts.join(' · ') || 'Bracket Stage',
    };
  }

  function _renderOutcomeExperience(backendCommand, context = {}) {
    const spotlight = document.getElementById('hub-overview-outcome-spotlight');
    const heroSpotlightBtn = document.getElementById('hub-overview-spotlight-btn');
    const spotlightState = document.getElementById('hub-overview-outcome-spotlight-state');
    const spotlightIcon = document.getElementById('hub-overview-outcome-spotlight-icon');
    const spotlightTitle = document.getElementById('hub-overview-outcome-spotlight-title');
    const spotlightBody = document.getElementById('hub-overview-outcome-spotlight-body');
    const spotlightStage = document.getElementById('hub-overview-outcome-spotlight-stage');
    const spotlightPlayer = document.getElementById('hub-overview-outcome-spotlight-player');
    const spotlightOpponent = document.getElementById('hub-overview-outcome-spotlight-opponent');
    const spotlightScore = document.getElementById('hub-overview-outcome-spotlight-score');
    const spotlightTournament = document.getElementById('hub-overview-outcome-spotlight-tournament');
    const spotlightDismiss = document.getElementById('hub-overview-outcome-spotlight-dismiss');

    const experience = backendCommand && typeof backendCommand === 'object'
      ? (backendCommand.outcome_experience || null)
      : null;
    _latestOutcomeCommand = backendCommand || null;
    _latestOutcomeContext = context || null;

    if (!experience || !experience.enabled) {
      _outcomeSharePayload = null;
      if (heroSpotlightBtn) {
        heroSpotlightBtn.classList.add('hidden');
      }
      if (spotlight) {
        _dismissOutcomeSpotlight({ persist: false });
        spotlight.removeAttribute('data-outcome-key');
        spotlight.removeAttribute('data-outcome-state');
      }
      return;
    }

    const state = String(experience.state || backendCommand?.outcome_state || '').toLowerCase();
    const key = String(experience.key || '').trim();
    const spotlightData = experience.spotlight || {};
    const persistentData = experience.persistent || {};
    const tournamentName = String(_shell?.dataset.tournamentName || spotlightTournament?.textContent || '').trim();
    const gameName = String(_shell?.dataset.gameName || '').trim();
    const titleText = String(spotlightData.title || persistentData.title || (state === 'eliminated' ? 'Run Complete' : 'Victory Confirmed'));
    const bodyText = String(spotlightData.body || persistentData.body || backendCommand?.subtitle || '');
    const suggestion = String(experience.community_post_suggestion || '').trim();
    const outcomeContext = _resolveOutcomeMatchContext(backendCommand, context?.source || null, context?.target || null);

    const fallbackCaption = [
      titleText,
      tournamentName,
      gameName,
    ].filter(Boolean).join(' | ');

    _outcomeSharePayload = {
      title: titleText,
      body: bodyText,
      caption: suggestion || fallbackCaption,
    };

    const spotlightEnabled = Boolean(spotlightData.enabled);
    if (heroSpotlightBtn) {
      const canOpenSpotlight = Boolean(spotlightEnabled && key);
      heroSpotlightBtn.classList.toggle('hidden', !canOpenSpotlight);
      heroSpotlightBtn.classList.toggle('is-fresh', Boolean(canOpenSpotlight && !_isOutcomeDismissed(key)));
      heroSpotlightBtn.innerHTML = '<i data-lucide="sparkles" class="w-4 h-4"></i><span>Reveal</span>';
      heroSpotlightBtn.onclick = canOpenSpotlight
        ? () => _openOutcomeSpotlight({ force: true })
        : null;
    }

    if (!spotlight) {
      return;
    }

    if (!spotlightEnabled || !key) {
      _dismissOutcomeSpotlight({ persist: false });
      return;
    }

    spotlight.dataset.outcomeKey = key;
    spotlight.setAttribute('data-outcome-state', state || 'neutral');

    if (spotlightState) {
      spotlightState.textContent = String(spotlightData.stat_line || (state === 'eliminated' ? 'Run Complete' : 'Advanced'));
    }
    if (spotlightIcon) {
      if (state === 'eliminated') {
        spotlightIcon.innerHTML = '<i data-lucide="shield" class="w-6 h-6"></i>';
      } else {
        spotlightIcon.innerHTML = '<i data-lucide="trophy" class="w-6 h-6"></i>';
      }
    }
    if (spotlightTitle) {
      spotlightTitle.textContent = titleText;
    }
    if (spotlightStage) {
      spotlightStage.textContent = outcomeContext.stageText;
    }
    if (spotlightBody) {
      spotlightBody.textContent = bodyText;
    }
    if (spotlightPlayer) {
      spotlightPlayer.textContent = _shell?.dataset.username || spotlightPlayer.textContent || 'Competitor';
    }
    if (spotlightTournament) {
      spotlightTournament.textContent = tournamentName || spotlightTournament.textContent || 'Tournament';
    }
    if (spotlightOpponent) {
      spotlightOpponent.textContent = `vs ${outcomeContext.opponentName}`;
    }
    if (spotlightScore) {
      spotlightScore.textContent = outcomeContext.scoreline;
    }
    if (spotlightDismiss) {
      spotlightDismiss.setAttribute('aria-label', String(spotlightData.dismiss_label || 'Close spotlight'));
    }
    _applyOverviewGameBranding();

    const shouldAutoShow = Boolean(
      _currentTab === 'overview'
      && key
      && !_isOutcomeDismissed(key)
    );

    if (shouldAutoShow) {
      _openOutcomeSpotlight();
    } else {
      _dismissOutcomeSpotlight({ persist: false });
    }

    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  }

  function _setOverviewBadgeTone(el, tone, label) {
    if (!el) return;
    const safeTone = ['danger', 'success', 'warning', 'info'].includes(tone) ? tone : 'info';
    const toneClass = OVERVIEW_BADGE_TONE_CLASS[safeTone] || OVERVIEW_BADGE_TONE_CLASS.info;
    el.className = `${OVERVIEW_BADGE_BASE_CLASS} ${toneClass}`.trim();
    el.textContent = label || 'Standby';
  }

  function _renderOverviewHeroTitle(titleEl, rawTitle, outcomeState = '') {
    if (!titleEl) return;

    const titleText = String(rawTitle || '').trim() || 'Standby';
    const words = titleText.split(/\s+/).filter(Boolean);
    if (words.length < 2 || titleText.includes(':') || titleText.includes('/')) {
      titleEl.textContent = titleText;
      return;
    }

    const state = String(outcomeState || '').toLowerCase();
    const normalizedWords = words.map((word) => word.replace(/[^A-Za-z]/g, '').toLowerCase());
    let accentIndex = words.length - 1;

    if (state === 'advanced') {
      const preferred = ['bracket', 'qualified', 'advanced', 'advance'];
      const idx = normalizedWords.findIndex((word) => preferred.includes(word));
      if (idx >= 0) accentIndex = idx;
    } else if (state === 'eliminated') {
      const preferred = ['eliminated', 'complete', 'closed', 'out'];
      const idx = normalizedWords.findIndex((word) => preferred.includes(word));
      if (idx >= 0) accentIndex = idx;
    }

    const accentWord = words[accentIndex] || '';
    if (!/^[A-Za-z][A-Za-z0-9_-]{1,}$/.test(accentWord)) {
      titleEl.textContent = titleText;
      return;
    }

    const leadText = words.slice(0, accentIndex).join(' ');
    const tailText = words.slice(accentIndex + 1).join(' ');
    const accentClass = state === 'advanced'
      ? 'is-advanced'
      : state === 'eliminated'
        ? 'is-eliminated'
        : (state === 'live' || state === 'ready')
          ? 'is-live'
          : (state === 'pending' || state === 'standby' || state === 'waiting')
            ? 'is-pending'
            : (state === 'season_complete' || state === 'complete')
              ? 'is-complete'
              : 'is-neutral';

    const htmlChunks = [];
    if (leadText) {
      htmlChunks.push(`<span class="hub-overview-hero-title-main">${_esc(leadText)}</span>`);
    }
    htmlChunks.push(`<span class="hub-overview-hero-title-accent ${accentClass}">${_esc(accentWord)}</span>`);
    if (tailText) {
      htmlChunks.push(`<span class="hub-overview-hero-title-main">${_esc(tailText)}</span>`);
    }
    titleEl.innerHTML = htmlChunks.join(' ');
  }

  function _setOverviewPrimaryAction(buttonEl, config = {}, backendCommand = null) {
    if (!buttonEl) return;
    const action = String(config.action || 'view_schedule').toLowerCase();
    const label = String(config.label || 'View Schedule');
    const tone = ['danger', 'success', 'warning', 'info'].includes(config.tone) ? config.tone : 'info';
    const disabled = Boolean(config.disabled);
    const iconMap = {
      check_in: 'shield-alert',
      enter_lobby: 'swords',
      open_matches: 'crosshair',
      open_bracket: 'git-branch',
      open_standings: 'list-ordered',
      open_support: 'life-buoy',
      open_announcements: 'megaphone',
      respond_reschedule: 'clock-3',
      view_schedule: 'calendar',
      open_result_spotlight: 'sparkles',
      open_outcome_share: 'send',
    };
    const icon = config.icon || iconMap[action] || 'calendar';

    buttonEl.className = OVERVIEW_PRIMARY_BTN_BASE_CLASS;
    buttonEl.dataset.tone = tone;
    buttonEl.dataset.hubAction = action;
    buttonEl.disabled = disabled;
    buttonEl.innerHTML = `<i data-lucide="${icon}" class="w-4 h-4"></i><span>${_esc(label)}</span>`;
    buttonEl.onclick = () => {
      if (buttonEl.disabled) return;
      if (typeof config.onClick === 'function') {
        config.onClick();
        return;
      }
      _runOverviewCommandAction(action, backendCommand || {});
    };
  }

  function _setOverviewSecondaryAction(buttonEl, config = {}, backendCommand = null) {
    if (!buttonEl) return;
    const show = config.show !== false;
    const variantClass = config.variant === 'tertiary' ? OVERVIEW_TERTIARY_BTN_CLASS : OVERVIEW_SECONDARY_BTN_CLASS;
    buttonEl.className = show ? variantClass : `${variantClass} hidden`;
    if (!show) {
      buttonEl.onclick = null;
      return;
    }

    const action = String(config.action || 'open_matches').toLowerCase();
    const label = String(config.label || 'View Next Assignment');
    const iconMap = {
      open_matches: 'crosshair',
      open_bracket: 'git-branch',
      open_standings: 'list-ordered',
      open_support: 'life-buoy',
      open_announcements: 'megaphone',
      open_result_spotlight: 'sparkles',
      open_outcome_share: 'send',
    };
    const icon = config.icon || iconMap[action] || 'arrow-right';

    buttonEl.dataset.hubAction = action;
    buttonEl.innerHTML = `<i data-lucide="${icon}" class="w-4 h-4"></i><span>${_esc(label)}</span>`;
    buttonEl.onclick = () => {
      if (typeof config.onClick === 'function') {
        config.onClick();
        return;
      }
      _runOverviewCommandAction(action, backendCommand || {});
    };
  }

  function _matchFormToken(match) {
    const explicitWin = match?.is_winner;
    if (explicitWin === true) return 'W';
    if (explicitWin === false) return 'L';

    const yourScore = Number(match?.your_score);
    const oppScore = Number(match?.opponent_score);
    if (Number.isFinite(yourScore) && Number.isFinite(oppScore)) {
      if (yourScore > oppScore) return 'W';
      if (yourScore < oppScore) return 'L';
      return 'D';
    }

    if (match?.is_staff_view) {
      const p1Score = Number(match?.p1_score);
      const p2Score = Number(match?.p2_score);
      if (Number.isFinite(p1Score) && Number.isFinite(p2Score)) {
        if (p1Score > p2Score) return 'W';
        if (p1Score < p2Score) return 'L';
        return 'D';
      }
    }

    const result = String(match?.result || match?.outcome || '').toLowerCase();
    if (result.includes('win')) return 'W';
    if (result.includes('loss') || result.includes('lose')) return 'L';
    if (result.includes('draw') || result.includes('tie')) return 'D';
    return '-';
  }

  function _rerenderOverviewIntelFromCache() {
    const source = _matchesCache || {};
    const allMatches = [
      ...(Array.isArray(source.active_matches) ? source.active_matches : []),
      ...(Array.isArray(source.match_history) ? source.match_history : []),
    ];
    const target = _pickOverviewTargetMatch(allMatches);
    _renderOverviewIntelligence(target, source, _lastPolledState);
  }

  function setOverviewIntelView(view = 'auto') {
    const normalized = String(view || '').toLowerCase();
    if (normalized === 'my' || normalized === 'opponent') {
      _overviewIntelViewMode = normalized;
    } else {
      _overviewIntelViewMode = 'auto';
    }
    _rerenderOverviewIntelFromCache();
  }

  function _renderOverviewIntelligence(target, source, stateData = null) {
    const opponentEl = document.getElementById('hub-overview-intel-opponent');
    const stageEl = document.getElementById('hub-overview-intel-stage');
    const kickerEl = document.getElementById('hub-overview-intel-kicker');
    const microLabelEl = document.getElementById('hub-overview-intel-micro-label');
    const formLabelEl = document.querySelector('#hub-overview-intel-card .hub-overview-intel-form-label');
    const formEl = document.getElementById('hub-overview-intel-form');
    const winrateEl = document.getElementById('hub-overview-intel-stat-winrate');
    const recordEl = document.getElementById('hub-overview-intel-stat-record');
    const liveEl = document.getElementById('hub-overview-intel-stat-live');
    const winrateLabelEl = document.getElementById('hub-overview-intel-stat-winrate-label');
    const recordLabelEl = document.getElementById('hub-overview-intel-stat-record-label');
    const liveLabelEl = document.getElementById('hub-overview-intel-stat-live-label');
    const signalsEl = document.getElementById('hub-overview-intel-signals');
    const noteTitleEl = document.getElementById('hub-overview-intel-note-title');
    const noteEl = document.getElementById('hub-overview-intel-note');
    const intelAvatarEl = document.getElementById('hub-overview-intel-avatar');
    const intelAvatarFallbackEl = document.getElementById('hub-overview-intel-avatar-fallback');
    const toggleMyBtn = document.getElementById('hub-overview-intel-toggle-my');
    const toggleOpponentBtn = document.getElementById('hub-overview-intel-toggle-opponent');
    if (!opponentEl || !stageEl || !formEl || !winrateEl || !recordEl || !liveEl || !noteEl) {
      return;
    }

    const getPathValue = (obj, path) => {
      if (!obj || !path) return undefined;
      return String(path)
        .split('.')
        .reduce((acc, key) => (acc && Object.prototype.hasOwnProperty.call(acc, key) ? acc[key] : undefined), obj);
    };

    const firstNonEmptyValue = (...values) => {
      for (const value of values) {
        if (value === null || value === undefined) continue;
        const text = String(value).trim();
        if (text) return value;
      }
      return '';
    };

    const readNumber = (value) => {
      if (value === null || value === undefined || value === '') return null;
      const parsed = Number(String(value).replace(/[^0-9.-]/g, ''));
      return Number.isFinite(parsed) ? parsed : null;
    };

    const normalizeMetric = (value, { percent = false, precision = 1 } = {}) => {
      const text = String(value ?? '').trim();
      if (!text) return '';
      if (percent) {
        if (text.includes('%')) return text;
        const percentNum = readNumber(text);
        if (percentNum === null) return '';
        return `${Math.round(percentNum)}%`;
      }
      const asNumber = readNumber(text);
      if (asNumber === null) return text;
      if (Number.isInteger(asNumber)) return String(asNumber);
      return asNumber.toFixed(precision);
    };

    const averageFromHistory = (paths, { precision = 1 } = {}) => {
      const values = [];
      orderedHistory.forEach((match) => {
        const raw = firstNonEmptyValue(...paths.map((path) => getPathValue(match, path)));
        const parsed = readNumber(raw);
        if (parsed !== null) values.push(parsed);
      });
      if (!values.length) return '';
      const avg = values.reduce((sum, v) => sum + v, 0) / values.length;
      return Number.isInteger(avg) ? String(avg) : avg.toFixed(precision);
    };

    const sumFromHistory = (paths) => {
      let total = 0;
      let found = false;
      orderedHistory.forEach((match) => {
        const raw = firstNonEmptyValue(...paths.map((path) => getPathValue(match, path)));
        const parsed = readNumber(raw);
        if (parsed === null) return;
        total += parsed;
        found = true;
      });
      return found ? total : null;
    };

    const ratioFromHistory = (numeratorPaths, denominatorPaths, precision = 2) => {
      const numerator = sumFromHistory(numeratorPaths);
      const denominator = sumFromHistory(denominatorPaths);
      if (numerator === null || denominator === null || denominator <= 0) return '';
      const ratio = numerator / denominator;
      return Number.isInteger(ratio) ? String(ratio) : ratio.toFixed(precision);
    };

    const resolveTargetMetric = (paths, opts = {}) => {
      if (!target || typeof target !== 'object') return '';
      const raw = firstNonEmptyValue(...paths.map((path) => getPathValue(target, path)));
      return normalizeMetric(raw, opts);
    };

    const normalizeAvatarCandidateUrl = (value) => {
      const raw = String(value || '').trim();
      if (!raw) return '';

      if (/^(?:https?:|data:|blob:)/i.test(raw)) return raw;
      if (raw.startsWith('//')) return `${window.location.protocol}${raw}`;
      if (raw.startsWith('/')) return raw;

      const cleaned = raw.replace(/^\.\/?/, '');
      if (!cleaned) return '';
      if (cleaned.startsWith('user_avatars/') || cleaned.startsWith('team_logos/')) {
        return `/media/${cleaned}`;
      }
      return `/${cleaned}`;
    };

    const areAvatarUrlsEqual = (left, right) => {
      const a = normalizeAvatarCandidateUrl(left);
      const b = normalizeAvatarCandidateUrl(right);
      return Boolean(a && b && a === b);
    };

    const resolveNavbarAvatarUrl = () => {
      const el = document.querySelector('#hub-navbar a[href="/dashboard/"] img');
      return normalizeAvatarCandidateUrl(el?.getAttribute('src') || '');
    };

    const resolveSelfAvatarUrl = (match) => {
      const navbarAvatar = resolveNavbarAvatarUrl();
      if (!match || typeof match !== 'object') return navbarAvatar;

      const opponentLogo = normalizeAvatarCandidateUrl(match.opponent_logo_url);
      const p1Logo = normalizeAvatarCandidateUrl(match.p1_logo_url);
      const p2Logo = normalizeAvatarCandidateUrl(match.p2_logo_url);

      if (opponentLogo && p1Logo && areAvatarUrlsEqual(opponentLogo, p1Logo) && p2Logo) {
        return p2Logo;
      }
      if (opponentLogo && p2Logo && areAvatarUrlsEqual(opponentLogo, p2Logo) && p1Logo) {
        return p1Logo;
      }

      const sideCandidates = [p1Logo, p2Logo]
        .filter(Boolean)
        .filter((url) => !areAvatarUrlsEqual(url, opponentLogo));

      const candidates = [
        match.profile_avatar_url,
        match.avatar_url,
        navbarAvatar,
        ...sideCandidates,
        match.team_avatar_url,
        match.logo_url,
        match.team_logo_url,
      ];

      for (const candidate of candidates) {
        const normalized = normalizeAvatarCandidateUrl(candidate);
        if (normalized) return normalized;
      }
      return '';
    };

    const resolveOpponentAvatarUrl = (match) => {
      if (!match || typeof match !== 'object') return '';

      const directCandidates = [
        match.opponent_avatar_url,
        match.opponent_profile_avatar_url,
        match.opponent_logo_url,
        match.opponent_photo_url,
      ];
      for (const candidate of directCandidates) {
        const normalized = normalizeAvatarCandidateUrl(candidate);
        if (normalized) return normalized;
      }

      const inferredSelf = resolveSelfAvatarUrl(match);
      const sideCandidates = [
        match.p1_logo_url,
        match.p2_logo_url,
      ]
        .map((url) => normalizeAvatarCandidateUrl(url))
        .filter(Boolean)
        .filter((url) => !areAvatarUrlsEqual(url, inferredSelf));
      if (sideCandidates.length) {
        return sideCandidates[0];
      }

      const fallbackCandidates = [
        match.team_logo_url,
        match.team_avatar_url,
        match.logo_url,
        match.avatar_url,
      ];
      for (const candidate of fallbackCandidates) {
        const normalized = normalizeAvatarCandidateUrl(candidate);
        if (normalized && !areAvatarUrlsEqual(normalized, inferredSelf)) return normalized;
      }
      return '';
    };

    const resolveIntelAvatarUrl = (match, preference = 'auto') => {
      const mode = String(preference || 'auto').toLowerCase();
      if (mode === 'self') {
        return resolveSelfAvatarUrl(match);
      }
      if (mode === 'opponent') {
        return resolveOpponentAvatarUrl(match);
      }
      return resolveOpponentAvatarUrl(match) || resolveSelfAvatarUrl(match);
    };

    const syncIntelAvatar = (displayName, match, preference = 'auto') => {
      if (!intelAvatarEl && !intelAvatarFallbackEl) return;

      const avatarShell = intelAvatarEl ? intelAvatarEl.closest('.hub-overview-intel-avatar') : null;

      const safeName = String(displayName || '').trim();
      const initials = safeName
        ? safeName
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part.charAt(0))
            .join('')
            .toUpperCase()
        : 'OP';

      if (intelAvatarFallbackEl) {
        intelAvatarFallbackEl.textContent = initials || 'OP';
      }

      if (!intelAvatarEl) return;

      const avatarUrl = resolveIntelAvatarUrl(match, preference);
      if (avatarUrl && !_brokenAvatarUrls.has(avatarUrl)) {
        intelAvatarEl.onerror = null;
        intelAvatarEl.src = avatarUrl;
        intelAvatarEl.alt = safeName ? `${safeName} avatar` : 'Intel avatar';
        intelAvatarEl.classList.remove('hidden');
        if (avatarShell) {
          avatarShell.classList.add('has-image');
        }
        if (intelAvatarFallbackEl) {
          intelAvatarFallbackEl.classList.add('hidden');
        }
        intelAvatarEl.onerror = () => {
          _markAvatarUrlBroken(avatarUrl);
          intelAvatarEl.removeAttribute('src');
          intelAvatarEl.classList.add('hidden');
          if (intelAvatarFallbackEl) {
            intelAvatarFallbackEl.classList.remove('hidden');
          }
        };
        return;
      }

      intelAvatarEl.removeAttribute('src');
      intelAvatarEl.classList.add('hidden');
      if (avatarShell) {
        avatarShell.classList.remove('has-image');
      }
      if (intelAvatarFallbackEl) {
        intelAvatarFallbackEl.classList.remove('hidden');
      }
    };

    const normalizeFormTokens = (tokens) => {
      const normalized = Array.isArray(tokens)
        ? tokens
            .map((token) => String(token || '').trim().toUpperCase())
            .map((token) => (token === 'W' || token === 'L' || token === 'D' ? token : '-'))
        : [];
      while (normalized.length < 4) {
        normalized.push('-');
      }
      return normalized.slice(0, 4);
    };

    const renderFormTokens = (tokens) => {
      const normalized = normalizeFormTokens(tokens);
      formEl.innerHTML = normalized
        .map((token) => {
          if (token === 'W') return `<span class="${OVERVIEW_FORM_PILL_CLASS.win}">W</span>`;
          if (token === 'L') return `<span class="${OVERVIEW_FORM_PILL_CLASS.loss}">L</span>`;
          if (token === 'D') return `<span class="${OVERVIEW_FORM_PILL_CLASS.draw}">D</span>`;
          return `<span class="${OVERVIEW_FORM_PILL_CLASS.muted}">-</span>`;
        })
        .join('');
    };

    const branding = _resolveOverviewGameBranding();
    const gameKey = String(branding?.normalized || '').toLowerCase();
    const username = String(_shell?.dataset.username || '').trim();

    const resolveGameProfile = (key) => {
      const value = String(key || '').toLowerCase();
      if (['efootball', 'pes', 'proevolutionsoccer', 'fifa', 'fc24'].some((item) => value.includes(item))) {
        return 'football';
      }
      if (['valorant', 'cs2', 'csgo', 'rainbowsix', 'r6'].some((item) => value.includes(item))) {
        return 'tactical';
      }
      if (['pubg', 'pubgm', 'pubgmobile', 'freefire', 'ff', 'fortnite', 'apex'].some((item) => value.includes(item))) {
        return 'battle-royale';
      }
      if (['dota', 'dota2', 'league', 'lol'].some((item) => value.includes(item))) {
        return 'moba';
      }
      return 'generic';
    };

    const gameProfile = resolveGameProfile(gameKey);
    const intelCardEl = document.getElementById('hub-overview-intel-card');
    if (intelCardEl) {
      intelCardEl.setAttribute('data-intel-game-profile', gameProfile);
    }

    const historyMatches = Array.isArray(source?.match_history) ? source.match_history : [];
    const orderedHistory = historyMatches.slice().sort((a, b) => {
      const aDate = _toValidDate(a?.scheduled_at);
      const bDate = _toValidDate(b?.scheduled_at);
      const aTs = aDate ? aDate.getTime() : 0;
      const bTs = bDate ? bDate.getTime() : 0;
      if (aTs !== bTs) return aTs - bTs;
      return Number(a?.id || 0) - Number(b?.id || 0);
    });

    const latestHistory = orderedHistory.length ? orderedHistory[orderedHistory.length - 1] : null;
    const tournamentStatus = String(stateData?.tournament_status || _shell?.dataset.tournamentStatus || '').toLowerCase();
    const outcomeState = String(stateData?.command_center?.outcome_state || stateData?.command_center?.outcome_experience?.state || '').toLowerCase();
    const runEnded = outcomeState === 'eliminated' || ['completed', 'complete', 'finished', 'closed', 'archived'].includes(tournamentStatus);

    const resolveOpponentIdentity = (match) => {
      if (!match || typeof match !== 'object') {
        return { name: '', isVerified: false };
      }

      let name = String(match?.opponent_name || '').trim();
      const p1Name = String(match?.p1_name || '').trim();
      const p2Name = String(match?.p2_name || '').trim();
      const userLower = username.toLowerCase();

      if (!name) {
        const candidates = [p1Name, p2Name].filter(Boolean);
        const external = candidates.find((candidate) => String(candidate).toLowerCase() !== userLower);
        name = external || candidates[0] || '';
      }

      const lowered = String(name || '').toLowerCase();
      const isPlaceholder = !name
        || lowered === 'tbd'
        || lowered.includes('awaiting')
        || lowered.includes('pending');

      return {
        name: name || 'Stand By',
        isVerified: !isPlaceholder,
      };
    };

    const formatMatchContext = (match) => {
      if (!match || typeof match !== 'object') return '';
      const parts = [];
      if (match?.stage_label || match?.match_stage_label) parts.push(match.stage_label || match.match_stage_label);
      if (match?.round_name) parts.push(match.round_name);
      if (match?.match_number) parts.push(`Match #${match.match_number}`);
      return parts.join(' · ');
    };

    const resolveLastResult = (match) => {
      const token = _matchFormToken(match);
      if (token === 'W') return 'Win';
      if (token === 'L') return 'Loss';
      if (token === 'D') return 'Draw';
      return 'Data Pending';
    };

    const resolveScoreline = (match) => {
      if (!match || typeof match !== 'object') return 'Data Pending';
      const yourScore = readNumber(match?.your_score);
      const oppScore = readNumber(match?.opponent_score);
      if (yourScore !== null && oppScore !== null) return `${yourScore}-${oppScore}`;
      const p1Score = readNumber(match?.p1_score);
      const p2Score = readNumber(match?.p2_score);
      if (p1Score !== null && p2Score !== null) return `${p1Score}-${p2Score}`;
      return 'Data Pending';
    };

    const extractOpponentFormTokens = (match) => {
      if (!match || typeof match !== 'object') return ['-', '-', '-', '-'];
      const candidates = [
        match.opponent_recent_form,
        match.opponent_form,
        match.opponent_last_results,
      ];

      for (const candidate of candidates) {
        if (Array.isArray(candidate) && candidate.length) {
          return normalizeFormTokens(candidate);
        }
        if (typeof candidate === 'string' && candidate.trim()) {
          const split = candidate
            .split(/[^a-zA-Z]+/)
            .filter(Boolean)
            .map((token) => token.trim().toUpperCase());
          if (split.length) {
            return normalizeFormTokens(split);
          }
        }
      }

      return ['-', '-', '-', '-'];
    };

    const scorePairFor = (match) => {
      if (!match) return null;

      const yourScore = Number(match?.your_score);
      const oppScore = Number(match?.opponent_score);
      if (Number.isFinite(yourScore) && Number.isFinite(oppScore)) {
        return { scored: yourScore, conceded: oppScore };
      }

      const p1Score = Number(match?.p1_score);
      const p2Score = Number(match?.p2_score);
      if (Number.isFinite(p1Score) && Number.isFinite(p2Score)) {
        return { scored: p1Score, conceded: p2Score };
      }

      return null;
    };

    const scoredHistory = orderedHistory
      .map((item) => {
        const pair = scorePairFor(item);
        if (!pair) return null;
        return { ...pair, token: _matchFormToken(item) };
      })
      .filter(Boolean);

    let wins = 0;
    let losses = 0;
    let draws = 0;
    orderedHistory.forEach((item) => {
      const token = _matchFormToken(item);
      if (token === 'W') wins += 1;
      if (token === 'L') losses += 1;
      if (token === 'D') draws += 1;
    });

    const myRecentTokens = orderedHistory.slice(-4).reverse().map((item) => _matchFormToken(item));

    const resolvedMatches = wins + losses + draws;
    const decisiveMatches = wins + losses;
    const totalGoals = scoredHistory.reduce((sum, row) => sum + row.scored, 0);
    const cleanSheets = scoredHistory.filter((row) => row.conceded === 0).length;
    const avgGoals = scoredHistory.length ? (totalGoals / scoredHistory.length).toFixed(1) : '';

    const myWinRate = resolvedMatches > 0
      ? `${decisiveMatches > 0 ? Math.round((wins / decisiveMatches) * 100) : 0}%`
      : 'Awaiting Data';
    const hasReliableHistory = resolvedMatches > 0;

    const makePendingStats = (base) => ({
      ...base,
      winrateValue: 'Data Pending',
      recordValue: 'Data Pending',
      liveValue: 'Data Pending',
    });

    const resolvePlayerStats = () => {
      if (gameProfile === 'football') {
        return {
          winrateLabel: 'Win Rate',
          recordLabel: 'Avg Goals / Match',
          liveLabel: 'Clean Sheets',
          winrateValue: hasReliableHistory ? myWinRate : 'Data Pending',
          recordValue: hasReliableHistory ? (avgGoals || 'N/A') : 'Data Pending',
          liveValue: hasReliableHistory ? String(cleanSheets) : 'Data Pending',
        };
      }

      if (gameProfile === 'tactical') {
        const avgRounds = averageFromHistory([
          'your_avg_rounds_won',
          'stats.avg_rounds_won',
          'player_stats.avg_rounds_won',
          'avg_rounds_won',
        ]);
        const kdFromRows = averageFromHistory([
          'your_kd',
          'stats.kd',
          'player_stats.kd',
          'kd_ratio',
          'your_kd_ratio',
        ], { precision: 2 });
        const kdFromTotals = ratioFromHistory(
          ['your_kills', 'kills', 'stats.kills', 'player_stats.kills'],
          ['your_deaths', 'deaths', 'stats.deaths', 'player_stats.deaths'],
          2,
        );
        return {
          winrateLabel: 'Win Rate',
          recordLabel: 'Avg Rounds Won / Match',
          liveLabel: 'K/D',
          winrateValue: hasReliableHistory ? myWinRate : 'Data Pending',
          recordValue: avgRounds || (hasReliableHistory ? (avgGoals || 'N/A') : 'Data Pending'),
          liveValue: kdFromRows || kdFromTotals || 'Data Pending',
        };
      }

      if (gameProfile === 'battle-royale') {
        const avgPlacement = averageFromHistory([
          'your_avg_placement',
          'placement',
          'stats.placement',
          'player_stats.placement',
        ]);
        const avgKills = averageFromHistory([
          'your_avg_kills',
          'your_kills',
          'kills',
          'stats.kills',
          'player_stats.kills',
        ]);
        return {
          winrateLabel: 'Win Rate',
          recordLabel: 'Avg Placement',
          liveLabel: 'Avg Kills / Match',
          winrateValue: hasReliableHistory ? myWinRate : 'Data Pending',
          recordValue: avgPlacement || 'Data Pending',
          liveValue: avgKills || 'Data Pending',
        };
      }

      if (gameProfile === 'moba') {
        const avgKills = averageFromHistory([
          'your_avg_kills',
          'your_kills',
          'kills',
          'stats.kills',
          'player_stats.kills',
        ]);
        const kdaFromRows = averageFromHistory([
          'your_kda',
          'stats.kda',
          'player_stats.kda',
        ], { precision: 2 });
        const kdaFromTotals = ratioFromHistory(
          ['your_kills', 'kills', 'stats.kills', 'player_stats.kills'],
          ['your_deaths', 'deaths', 'stats.deaths', 'player_stats.deaths'],
          2,
        );
        return {
          winrateLabel: 'Win Rate',
          recordLabel: 'Avg Kills / Match',
          liveLabel: 'KDA',
          winrateValue: hasReliableHistory ? myWinRate : 'Data Pending',
          recordValue: avgKills || 'Data Pending',
          liveValue: kdaFromRows || kdaFromTotals || 'Data Pending',
        };
      }

      return {
        winrateLabel: 'Win Rate',
        recordLabel: 'Avg Score / Match',
        liveLabel: 'Matches Played',
        winrateValue: hasReliableHistory ? myWinRate : 'Data Pending',
        recordValue: hasReliableHistory ? (avgGoals || 'N/A') : 'Data Pending',
        liveValue: hasReliableHistory ? String(resolvedMatches) : 'Data Pending',
      };
    };

    const resolveOpponentStats = () => {
      if (gameProfile === 'football') {
        return {
          winrateLabel: 'Win Rate',
          recordLabel: 'Avg Goals / Match',
          liveLabel: 'Clean Sheets',
          winrateValue: resolveTargetMetric(['opponent_win_rate', 'opponent_winrate', 'opponent_stats.win_rate', 'opponent_stats.winrate'], { percent: true }) || 'Data Pending',
          recordValue: resolveTargetMetric(['opponent_avg_goals', 'opponent_stats.avg_goals', 'opponent_avg_score', 'opponent_stats.avg_score']) || 'Data Pending',
          liveValue: resolveTargetMetric(['opponent_clean_sheets', 'opponent_stats.clean_sheets']) || 'Data Pending',
        };
      }

      if (gameProfile === 'tactical') {
        const kdValue = resolveTargetMetric(['opponent_kd', 'opponent_avg_kd', 'opponent_kd_ratio', 'opponent_stats.kd', 'opponent_stats.kd_ratio'], { precision: 2 });
        const cleanMaps = resolveTargetMetric(['opponent_clean_wins', 'opponent_stats.clean_wins', 'opponent_stats.clean_maps']);
        return {
          winrateLabel: 'Win Rate',
          recordLabel: 'Avg Rounds Won / Match',
          liveLabel: kdValue ? 'K/D' : 'Clean Wins / Maps',
          winrateValue: resolveTargetMetric(['opponent_win_rate', 'opponent_winrate', 'opponent_stats.win_rate', 'opponent_stats.winrate'], { percent: true }) || 'Data Pending',
          recordValue: resolveTargetMetric(['opponent_avg_rounds_won', 'opponent_rounds_won_avg', 'opponent_stats.avg_rounds_won', 'opponent_stats.avg_round_wins']) || 'Data Pending',
          liveValue: kdValue || cleanMaps || 'Data Pending',
        };
      }

      if (gameProfile === 'battle-royale') {
        return {
          winrateLabel: 'Win Rate',
          recordLabel: 'Avg Placement',
          liveLabel: 'Avg Kills / Match',
          winrateValue: resolveTargetMetric(['opponent_win_rate', 'opponent_winrate', 'opponent_stats.win_rate', 'opponent_stats.winrate'], { percent: true }) || 'Data Pending',
          recordValue: resolveTargetMetric(['opponent_avg_placement', 'opponent_placement_avg', 'opponent_stats.avg_placement']) || 'Data Pending',
          liveValue: resolveTargetMetric(['opponent_avg_kills', 'opponent_kills_avg', 'opponent_stats.avg_kills']) || 'Data Pending',
        };
      }

      if (gameProfile === 'moba') {
        const kdaValue = resolveTargetMetric(['opponent_kda', 'opponent_stats.kda', 'opponent_kd', 'opponent_stats.kd'], { precision: 2 });
        const deathsValue = resolveTargetMetric(['opponent_avg_deaths', 'opponent_stats.avg_deaths']);
        return {
          winrateLabel: 'Win Rate',
          recordLabel: 'Avg Kills / Match',
          liveLabel: kdaValue ? 'KDA' : 'Avg Deaths / Match',
          winrateValue: resolveTargetMetric(['opponent_win_rate', 'opponent_winrate', 'opponent_stats.win_rate', 'opponent_stats.winrate'], { percent: true }) || 'Data Pending',
          recordValue: resolveTargetMetric(['opponent_avg_kills', 'opponent_stats.avg_kills']) || 'Data Pending',
          liveValue: kdaValue || deathsValue || 'Data Pending',
        };
      }

      return {
        winrateLabel: 'Win Rate',
        recordLabel: 'Avg Score / Match',
        liveLabel: 'Match Record',
        winrateValue: resolveTargetMetric(['opponent_win_rate', 'opponent_winrate', 'opponent_stats.win_rate', 'opponent_stats.winrate'], { percent: true }) || 'Data Pending',
        recordValue: resolveTargetMetric(['opponent_avg_score', 'opponent_stats.avg_score', 'opponent_avg_goals', 'opponent_stats.avg_goals']) || 'Data Pending',
        liveValue: String(firstNonEmptyValue(
          getPathValue(target, 'opponent_record'),
          getPathValue(target, 'opponent_stats.record'),
          getPathValue(target, 'opponent_stats.wins') && getPathValue(target, 'opponent_stats.losses')
            ? `${getPathValue(target, 'opponent_stats.wins')}W-${getPathValue(target, 'opponent_stats.losses')}L`
            : '',
        ) || 'Data Pending'),
      };
    };

    const mySnapshot = {
      kicker: '',
      microLabel: '',
      profileName: username || 'You',
      stageLine: hasReliableHistory
        ? 'Recent verified form available.'
        : 'Awaiting Opponent Assignment.',
      formLabel: 'Recent Form',
      formTokens: myRecentTokens,
      stats: resolvePlayerStats(),
      noteTitle: '',
      note: hasReliableHistory
        ? 'Last verified result and trend are ready.'
        : 'No verified matchup is available yet.',
      signals: [],
      avatarName: username || 'You',
      avatarMatch: target || latestHistory || null,
      avatarPreference: 'self',
      fallbackSignalLabel: '',
    };

    const fallbackSnapshot = {
      kicker: '',
      microLabel: '',
      profileName: 'Awaiting Opponent Assignment',
      stageLine: 'No verified matchup is available yet.',
      formLabel: 'Recent Form',
      formTokens: ['-', '-', '-', '-'],
      stats: makePendingStats(resolvePlayerStats()),
      noteTitle: '',
      note: 'No verified matchup is available yet.',
      signals: [],
      avatarName: username || 'You',
      avatarMatch: target || latestHistory || null,
      avatarPreference: 'self',
      fallbackSignalLabel: '',
    };

    const opponentIdentity = resolveOpponentIdentity(target);
    const hasVerifiedOpponent = Boolean(opponentIdentity.isVerified);
    const opponentFormTokens = hasVerifiedOpponent ? extractOpponentFormTokens(target) : ['-', '-', '-', '-'];

    const opponentStats = resolveOpponentStats();
    const hasOpponentMetricData = [opponentStats.winrateValue, opponentStats.recordValue, opponentStats.liveValue].some((value) => value !== 'Data Pending');
    const hasOpponentFormData = opponentFormTokens.some((token) => token !== '-');
    const matchContext = formatMatchContext(target);

    const scoutingSnapshot = {
      kicker: '',
      microLabel: '',
      profileName: hasVerifiedOpponent ? opponentIdentity.name : 'Awaiting Opponent Assignment',
      stageLine: hasVerifiedOpponent
        ? (matchContext || 'Recent verified form available.')
        : 'Awaiting Opponent Assignment.',
      formLabel: 'Recent Form',
      formTokens: hasVerifiedOpponent ? opponentFormTokens : ['-', '-', '-', '-'],
      stats: hasVerifiedOpponent ? opponentStats : makePendingStats(opponentStats),
      noteTitle: '',
      note: hasVerifiedOpponent
        ? ((hasOpponentFormData || hasOpponentMetricData)
          ? 'Verified scouting data is ready.'
          : 'Limited-data scouting view.')
        : 'Opponent scouting unlocks after assignment.',
      signals: [],
      avatarName: hasVerifiedOpponent ? opponentIdentity.name : 'OP',
      avatarMatch: hasVerifiedOpponent ? target : null,
      avatarPreference: 'opponent',
      fallbackSignalLabel: '',
    };

    const scoutingRecapSnapshot = {
      kicker: '',
      microLabel: '',
      profileName: 'No Active Opponent',
      stageLine: 'Opponent scouting unavailable.',
      formLabel: 'Recent Form',
      formTokens: myRecentTokens,
      stats: {
        winrateLabel: 'Last Result',
        recordLabel: 'Final Round',
        liveLabel: 'Scoreline',
        winrateValue: resolveLastResult(latestHistory),
        recordValue: firstNonEmptyValue(
          latestHistory?.round_name,
          latestHistory?.stage_label,
          latestHistory?.match_stage_label,
          'Data Pending',
        ),
        liveValue: resolveScoreline(latestHistory),
      },
      noteTitle: '',
      note: 'Review final standings for full recap context.',
      signals: [],
      avatarName: username || 'You',
      avatarMatch: latestHistory || target || null,
      avatarPreference: 'self',
      fallbackSignalLabel: '',
    };

    const requestedView = (_overviewIntelViewMode === 'my' || _overviewIntelViewMode === 'opponent')
      ? _overviewIntelViewMode
      : 'auto';
    const selectedView = requestedView === 'auto'
      ? ((hasVerifiedOpponent || runEnded) ? 'opponent' : 'my')
      : requestedView;

    let snapshot = mySnapshot;
    if (selectedView === 'opponent') {
      snapshot = runEnded && !hasVerifiedOpponent ? scoutingRecapSnapshot : scoutingSnapshot;
    } else if (selectedView === 'my' && !hasReliableHistory && !hasVerifiedOpponent && !runEnded) {
      snapshot = fallbackSnapshot;
    }

    if (toggleMyBtn) {
      const myActive = selectedView === 'my';
      toggleMyBtn.classList.toggle('active', myActive);
      toggleMyBtn.setAttribute('aria-pressed', myActive ? 'true' : 'false');
      toggleMyBtn.disabled = false;
    }
    if (toggleOpponentBtn) {
      const opponentActive = selectedView === 'opponent';
      toggleOpponentBtn.classList.toggle('active', opponentActive);
      toggleOpponentBtn.classList.toggle('is-waiting', !hasVerifiedOpponent && !runEnded);
      toggleOpponentBtn.setAttribute('aria-pressed', opponentActive ? 'true' : 'false');
      toggleOpponentBtn.disabled = false;
    }

    if (kickerEl) kickerEl.textContent = snapshot.kicker;
    if (microLabelEl) microLabelEl.textContent = snapshot.microLabel;
    opponentEl.textContent = snapshot.profileName;
    stageEl.textContent = snapshot.stageLine;
    if (formLabelEl) formLabelEl.textContent = snapshot.formLabel;
    renderFormTokens(snapshot.formTokens);

    if (winrateLabelEl) winrateLabelEl.textContent = snapshot.stats.winrateLabel;
    if (recordLabelEl) recordLabelEl.textContent = snapshot.stats.recordLabel;
    if (liveLabelEl) liveLabelEl.textContent = snapshot.stats.liveLabel;
    winrateEl.textContent = snapshot.stats.winrateValue;
    recordEl.textContent = snapshot.stats.recordValue;
    liveEl.textContent = snapshot.stats.liveValue;

    if (noteTitleEl) noteTitleEl.textContent = snapshot.noteTitle;
    noteEl.textContent = snapshot.note;
    if (signalsEl) {
      signalsEl.innerHTML = '';
    }
    syncIntelAvatar(
      snapshot.avatarName || opponentEl.textContent,
      snapshot.avatarMatch,
      snapshot.avatarPreference || 'auto',
    );
  }

  function _renderOverviewActionCard(matchPayload, stateData = null) {
    const card = document.getElementById('hub-overview-action-card');
    if (!card) return;
    const standbyCard = document.getElementById('hub-overview-standby-card');

    const status = String(stateData?.tournament_status || _shell?.dataset.tournamentStatus || '').toLowerCase();
    const source = matchPayload || _matchesCache || {};
    const allMatches = [
      ...(source.active_matches || []),
      ...(source.match_history || []),
    ];
    const target = _pickOverviewTargetMatch(allMatches);

    const badge = document.getElementById('hub-overview-action-badge');
    const title = document.getElementById('hub-overview-action-title');
    const subtitle = document.getElementById('hub-overview-action-subtitle');
    const meta = document.getElementById('hub-overview-action-meta');
    const timeLabel = document.getElementById('hub-overview-action-time-label');
    const timeValue = document.getElementById('hub-overview-action-time');
    const actionBtn = document.getElementById('hub-overview-action-btn');
    const secondaryBtn = document.getElementById('hub-overview-secondary-btn');
    const heroOutcome = document.getElementById('hub-overview-hero-outcome');
    const statusLabel = document.getElementById('hub-overview-status-label');
    const backendCommand = stateData?.command_center;
    const setHeroTitle = (text, state = '') => {
      _renderOverviewHeroTitle(title, text, state || card.dataset.outcomeState || '');
    };

    _renderOutcomeExperience(backendCommand || null, { source, target });
    _applyOverviewGameBranding();
    _renderOverviewIntelligence(target, source, stateData);

    if (statusLabel && stateData?.user_status) {
      statusLabel.textContent = stateData.user_status;
    }

    if (backendCommand && Object.prototype.hasOwnProperty.call(backendCommand, 'show')) {
      const showCard = Boolean(backendCommand.show);
      card.classList.toggle('hidden', !showCard);
      if (standbyCard) {
        standbyCard.classList.toggle('hidden', showCard);
      }
      if (!showCard) {
        _startOverviewHeroFx();
        return;
      }

      const tone = String(backendCommand.badge_tone || 'info').toLowerCase();
      card.dataset.tone = ['danger', 'success', 'warning', 'info'].includes(tone) ? tone : 'info';
      _setOverviewBadgeTone(badge, tone, backendCommand.badge_label || 'Standby');

      const outcomeState = String(backendCommand.outcome_state || backendCommand.outcome_experience?.state || '').toLowerCase();
      const experience = backendCommand.outcome_experience || {};
      card.dataset.outcomeState = outcomeState || '';
      const lobbyState = String(backendCommand.lobby_state || '').toLowerCase();
      const countdownMode = String(backendCommand.countdown_mode || '').toLowerCase();
      const targetState = String(target?.state || '').toLowerCase();
      const seasonComplete = ['completed', 'complete', 'finished', 'closed', 'archived'].includes(status);
      const hasVerifiedTarget = Boolean(target && !['completed', 'forfeit', 'cancelled'].includes(targetState));

      let heroScenario = 'pending';
      let resolvedTitle = backendCommand.title || 'Standing By';
      let resolvedSubtitle = backendCommand.subtitle || 'No immediate match action is required. Monitor announcements and schedule updates.';

      if (outcomeState === 'eliminated') {
        heroScenario = 'eliminated';
        resolvedTitle = 'Run Complete';
        resolvedSubtitle = 'Your tournament run has ended. Review final standings, bracket outcomes, and support options if needed.';
      } else if (seasonComplete) {
        heroScenario = 'season_complete';
        resolvedTitle = 'Season Complete';
        resolvedSubtitle = 'Tournament operations are complete. Review final results, announcements, and records.';
      } else if (countdownMode === 'live' || lobbyState === 'live' || targetState === 'live') {
        heroScenario = 'live';
        resolvedTitle = 'Live Ops';
        resolvedSubtitle = 'Your tournament session is active. Review assignment details and complete required actions.';
      } else if (outcomeState === 'advanced') {
        if (hasVerifiedTarget) {
          heroScenario = 'advanced';
          resolvedTitle = 'Advanced in Bracket';
          resolvedSubtitle = 'Victory secured. Keep momentum and watch for your next assignment update.';
        } else {
          heroScenario = 'pending';
          resolvedTitle = 'Assignment Pending';
          resolvedSubtitle = 'You advanced successfully. Your next verified matchup will appear once the bracket updates.';
        }
      } else if (status === 'live' && hasVerifiedTarget) {
        heroScenario = 'live';
        resolvedTitle = 'Live Ops';
        resolvedSubtitle = 'Your tournament session is active. Review assignment details and complete required actions.';
      } else {
        heroScenario = 'standby';
        resolvedTitle = 'Standing By';
        resolvedSubtitle = 'No immediate match action is required. Monitor announcements and schedule updates.';
      }

      const scenarioState = heroScenario === 'advanced'
        ? 'advanced'
        : heroScenario === 'eliminated'
          ? 'eliminated'
          : heroScenario === 'season_complete'
            ? 'season_complete'
            : heroScenario === 'live'
              ? 'live'
              : 'pending';

      setHeroTitle(resolvedTitle, scenarioState);
      if (subtitle) subtitle.textContent = resolvedSubtitle;

      const metaParts = [];
      if (backendCommand.match_stage_label) metaParts.push(backendCommand.match_stage_label);
      if (backendCommand.match_round_name) metaParts.push(backendCommand.match_round_name);
      if (backendCommand.match_number) metaParts.push(`Match #${backendCommand.match_number}`);
      if (meta) {
        meta.textContent = metaParts.join(' · ');
        meta.classList.toggle('hidden', !meta.textContent);
      }

      if (heroOutcome) {
        if (heroScenario === 'advanced') heroOutcome.textContent = 'Advanced';
        else if (heroScenario === 'eliminated') heroOutcome.textContent = 'Run Ended';
        else if (heroScenario === 'season_complete') heroOutcome.textContent = 'Season Complete';
        else if (heroScenario === 'live') heroOutcome.textContent = 'Live Ops';
        else heroOutcome.textContent = 'Standing By';
      }

      if (timeLabel) {
        timeLabel.textContent = backendCommand.countdown_label || 'Next Update';
      }

      if (timeValue) {
        const mode = String(backendCommand.countdown_mode || '').toLowerCase();
        const lobbyState = String(backendCommand.lobby_state || '').toLowerCase();
        if (lobbyState === 'lobby_closed' || lobbyState === 'forfeit_review') {
          timeValue.dataset.matchTime = '';
          timeValue.textContent = backendCommand.countdown_text || 'EXPIRED';
          timeValue.classList.add('text-red-400');
          _stopOverviewCountdown();
        } else if (mode === 'live') {
          timeValue.dataset.matchTime = 'live';
          timeValue.textContent = 'LIVE NOW';
          timeValue.classList.remove('text-red-400');
          _stopOverviewCountdown();
        } else if (backendCommand.countdown_target) {
          const targetTime = _toValidDate(backendCommand.countdown_target);
          timeValue.dataset.matchTime = 'countdown';
          timeValue.classList.remove('text-red-400');
          _startOverviewCountdown(targetTime);
        } else {
          timeValue.dataset.matchTime = '';
          timeValue.textContent = backendCommand.countdown_text || 'Awaiting schedule';
          timeValue.classList.remove('text-red-400');
          _stopOverviewCountdown();
        }
      }

      _setOverviewPrimaryAction(actionBtn, {
        action: backendCommand.cta_action || 'view_schedule',
        label: backendCommand.cta_label || 'View Schedule',
        tone,
        disabled: Boolean(backendCommand.cta_disabled),
      }, backendCommand);

      if (outcomeState === 'eliminated') {
        _setOverviewSecondaryAction(secondaryBtn, {
          action: 'open_standings',
          label: 'View Standings',
          icon: 'list-ordered',
        }, backendCommand);
      } else if (outcomeState === 'advanced') {
        _setOverviewSecondaryAction(secondaryBtn, {
          action: 'open_matches',
          label: 'View Next Assignment',
          icon: 'crosshair',
        }, backendCommand);
      } else {
        _setOverviewSecondaryAction(secondaryBtn, {
          action: 'open_bracket',
          label: 'Open Bracket',
          icon: 'git-branch',
        }, backendCommand);
      }

      if (typeof lucide !== 'undefined') lucide.createIcons();
      _startOverviewHeroFx();
      return;
    }

    if (standbyCard) {
      standbyCard.classList.add('hidden');
    }
    card.classList.remove('hidden');
    card.dataset.tone = 'info';
    card.dataset.outcomeState = '';

    if (!target) {
      const seasonComplete = ['completed', 'complete', 'finished', 'closed', 'archived'].includes(status);
      const runEnded = String(stateData?.command_center?.outcome_state || '').toLowerCase() === 'eliminated';
      _setOverviewBadgeTone(badge, 'info', status === 'live' ? 'Live Window' : 'Standby');
      if (runEnded) {
        setHeroTitle('Run Complete', 'eliminated');
      } else if (seasonComplete) {
        setHeroTitle('Season Complete', 'season_complete');
      } else {
        setHeroTitle('Standing By', 'pending');
      }
      if (subtitle) {
        if (runEnded) {
          subtitle.textContent = 'Your tournament run has ended. Review final standings, bracket outcomes, and support options if needed.';
        } else if (seasonComplete) {
          subtitle.textContent = 'Tournament operations are complete. Review final results, announcements, and records.';
        } else {
          subtitle.textContent = 'No immediate match action is required. Monitor announcements and schedule updates.';
        }
      }
      if (meta) meta.classList.add('hidden');
      if (heroOutcome) {
        if (runEnded) heroOutcome.textContent = 'Run Ended';
        else if (seasonComplete) heroOutcome.textContent = 'Season Complete';
        else heroOutcome.textContent = 'Standing By';
      }
      if (timeLabel) {
        const phaseLabel = stateData?.phase_event?.label;
        timeLabel.textContent = phaseLabel ? `${phaseLabel} In` : 'Next Update';
      }
      if (timeValue) {
        timeValue.dataset.matchTime = '';
        timeValue.textContent = stateData?.phase_event?.target ? '--:--' : 'Awaiting schedule';
        timeValue.classList.remove('text-red-400');
      }
      _setOverviewPrimaryAction(actionBtn, {
        action: 'open_bracket',
        label: 'Open Bracket',
        tone: 'info',
        icon: 'git-branch',
        onClick: () => switchTab('bracket'),
      });
      _setOverviewSecondaryAction(secondaryBtn, {
        action: 'open_matches',
        label: 'View Next Assignment',
        icon: 'crosshair',
        onClick: () => switchTab('matches'),
      });
      _stopOverviewCountdown();
      if (typeof lucide !== 'undefined') lucide.createIcons();
      _startOverviewHeroFx();
      return;
    }

    const pendingRequest = target?.reschedule?.pending_request || null;
    const canRespondToProposal = Boolean(target?.reschedule?.can_respond && pendingRequest?.id);
    if (canRespondToProposal) {
      const proposedLabel = _formatRescheduleDatetimeLabel(pendingRequest?.new_time);
      const overviewIsStaff = Boolean(target.is_staff_view);
      const matchup = overviewIsStaff
        ? `${target.p1_name || 'TBD'} vs ${target.p2_name || 'TBD'}`
        : `vs ${target.opponent_name || 'TBD'}`;

      card.dataset.tone = 'warning';
      _setOverviewBadgeTone(badge, 'warning', 'Response Required');
        setHeroTitle(`Reschedule Request: ${matchup}`);
      if (subtitle) subtitle.textContent = 'Your opponent proposed a new match time. Review and accept or reject this request.';
      if (meta) meta.classList.add('hidden');
      if (heroOutcome) heroOutcome.textContent = 'Response Required';
      if (timeLabel) timeLabel.textContent = 'Proposed For';
      if (timeValue) {
        timeValue.dataset.matchTime = '';
        timeValue.textContent = proposedLabel;
        timeValue.classList.remove('text-red-400');
      }
      _setOverviewPrimaryAction(actionBtn, {
        action: 'respond_reschedule',
        label: 'Review Proposal',
        tone: 'warning',
        icon: 'clock-3',
        onClick: () => respondReschedule(target.id),
      });
      _setOverviewSecondaryAction(secondaryBtn, {
        action: 'open_matches',
        label: 'Open Match Lobby',
      });
      _stopOverviewCountdown();
      if (typeof lucide !== 'undefined') lucide.createIcons();
      _startOverviewHeroFx();
      return;
    }

    const targetState = String(target.state || '').toLowerCase();
    const isLive = targetState === 'live';
    const isReady = ['ready', 'check_in'].includes(targetState);
    const isStaffPerspective = Boolean(target.is_staff_view);
    const matchup = isStaffPerspective
      ? `${target.p1_name || 'TBD'} vs ${target.p2_name || 'TBD'}`
      : `vs ${target.opponent_name || 'TBD'}`;
    const scheduled = target.scheduled_at ? new Date(target.scheduled_at) : null;
    const canOpenLobby = Boolean(target.match_room_url);
    const lobbyWindow = _resolveLobbyWindow(target);
    const isLobbyWindowOpen = canOpenLobby && lobbyWindow.isOpen;
    const isLobbyClosed = lobbyWindow.isClosed;
    const opensAt = lobbyWindow.opensAt;

    if (isLive) {
      card.dataset.tone = 'danger';
      _setOverviewBadgeTone(badge, 'danger', 'Live');
      setHeroTitle('Live Ops', 'live');
      if (heroOutcome) heroOutcome.textContent = 'Live Ops';
    } else if (isLobbyClosed) {
      card.dataset.tone = 'danger';
      _setOverviewBadgeTone(badge, 'danger', 'Lobby Closed');
      setHeroTitle('Assignment Pending', 'pending');
      if (heroOutcome) heroOutcome.textContent = 'Window Closed';
    } else if (isLobbyWindowOpen) {
      card.dataset.tone = 'success';
      _setOverviewBadgeTone(badge, 'success', 'Lobby Open');
      setHeroTitle('Live Ops', 'live');
      if (heroOutcome) heroOutcome.textContent = 'Action Ready';
    } else if (isReady) {
      card.dataset.tone = 'success';
      _setOverviewBadgeTone(badge, 'success', 'Ready');
      setHeroTitle('Live Ops', 'live');
      if (heroOutcome) heroOutcome.textContent = 'Action Ready';
    } else {
      card.dataset.tone = 'info';
      _setOverviewBadgeTone(badge, 'info', opensAt ? 'Upcoming' : 'Up Next');
      setHeroTitle('Assignment Pending', 'pending');
      if (heroOutcome) heroOutcome.textContent = 'Pending';
    }

    if (meta) {
      const metaParts = [];
      if (target.stage_label || target.match_stage_label) metaParts.push(target.stage_label || target.match_stage_label);
      if (target.round_name) metaParts.push(target.round_name);
      if (target.match_number) metaParts.push(`Match #${target.match_number}`);
      meta.textContent = metaParts.join(' · ');
      meta.classList.toggle('hidden', !meta.textContent);
    }

    if (subtitle) {
      const lobbyCode = target.lobby_info?.lobby_code || target.lobby_code || '';
      const scheduledLabel = scheduled && !Number.isNaN(scheduled.getTime())
        ? `Match starts ${_formatDateTime(scheduled, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}.`
        : 'Schedule time pending.';

      if (isLive) {
        subtitle.textContent = 'Your tournament session is active. Review assignment details and complete required actions.';
      } else if (isLobbyClosed) {
        subtitle.textContent = 'Your lobby window has closed for this assignment. Request a reschedule or contact support if needed.';
      } else if (isLobbyWindowOpen) {
        subtitle.textContent = `Your assignment is active for pre-match operations. Enter lobby and complete setup.${lobbyCode ? ` Lobby ${lobbyCode}.` : ''}`;
      } else if (isReady) {
        subtitle.textContent = `Your next verified matchup is ready. Enter the lobby and prepare for kickoff.${lobbyCode ? ` Lobby ${lobbyCode}.` : ''}`;
      } else if (opensAt) {
        subtitle.textContent = `Assignment pending. Lobby unlocks ${_formatCountdownLabel(opensAt)} before this match.${lobbyCode ? ` Lobby ${lobbyCode}.` : ''}`;
      } else {
        subtitle.textContent = `Assignment pending. ${scheduledLabel}${lobbyCode ? ` Lobby ${lobbyCode}.` : ''}`;
      }
    }

    if (timeLabel) {
      if (isLive || isLobbyClosed) {
        timeLabel.textContent = 'Status';
      } else if (isLobbyWindowOpen) {
        timeLabel.textContent = 'Match Starts In';
      } else {
        timeLabel.textContent = opensAt ? 'Lobby Opens In' : 'Starts In';
      }
    }

    if (timeValue) {
      if (isLive) {
        timeValue.dataset.matchTime = 'live';
        timeValue.textContent = 'LIVE NOW';
        timeValue.classList.remove('text-red-400');
        _stopOverviewCountdown();
      } else if (isLobbyClosed) {
        timeValue.dataset.matchTime = 'closed';
        timeValue.textContent = 'EXPIRED';
        timeValue.classList.add('text-red-400');
        _stopOverviewCountdown();
      } else if (isLobbyWindowOpen) {
        timeValue.dataset.matchTime = 'countdown';
        timeValue.classList.remove('text-red-400');
        _startOverviewCountdown(scheduled);
      } else if (opensAt) {
        timeValue.dataset.matchTime = 'countdown';
        timeValue.classList.remove('text-red-400');
        _startOverviewCountdown(opensAt);
      } else {
        timeValue.dataset.matchTime = 'countdown';
        timeValue.classList.remove('text-red-400');
        _startOverviewCountdown(scheduled);
      }
    }

    if (isLobbyClosed) {
      _setOverviewPrimaryAction(actionBtn, {
        action: 'open_matches',
        label: 'Request Reschedule',
        tone: 'warning',
        icon: 'clock-3',
        onClick: () => switchTab('matches'),
      });
      _setOverviewSecondaryAction(secondaryBtn, {
        action: 'open_support',
        label: 'Open Support',
      });
    } else if (isLive || isReady || isLobbyWindowOpen) {
      _setOverviewPrimaryAction(actionBtn, {
        action: 'enter_lobby',
        label: canOpenLobby ? 'Enter Lobby' : 'Open Match Lobby',
        tone: isLive ? 'danger' : 'success',
        icon: 'swords',
        onClick: () => {
          if (canOpenLobby) {
            _openMatchRoom(target.match_room_url);
            return;
          }
          switchTab('matches');
        },
      });
      _setOverviewSecondaryAction(secondaryBtn, {
        action: 'open_bracket',
        label: 'Open Bracket',
      });
    } else {
      _setOverviewPrimaryAction(actionBtn, {
        action: 'open_bracket',
        label: 'Open Bracket',
        tone: 'info',
        icon: 'git-branch',
        onClick: () => switchTab('bracket'),
      });
      _setOverviewSecondaryAction(secondaryBtn, {
        action: 'open_matches',
        label: 'View Next Assignment',
        icon: 'crosshair',
      });
    }

    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
    _startOverviewHeroFx();
  }

  async function _refreshOverviewActionCard({ forceFetch = false, stateData = null } = {}) {
    const hasBackendCommand = Boolean(
      stateData?.command_center && Object.prototype.hasOwnProperty.call(stateData.command_center, 'show')
    );
    const hasHydratedPayload = Boolean(
      _matchesCache
      && (Array.isArray(_matchesCache.active_matches) || Array.isArray(_matchesCache.match_history))
    );

    const freshEnough = _matchesCache && (Date.now() - _matchesCacheFetchedAt) < 60000;
    if (!forceFetch && freshEnough && (!hasBackendCommand || hasHydratedPayload)) {
      _renderOverviewActionCard(_matchesCache, stateData || _lastPolledState);
      return;
    }

    if (_overviewMatchRefreshInFlight) {
      _renderOverviewActionCard(_matchesCache, stateData || _lastPolledState);
      return;
    }

    const url = _shell?.dataset.apiMatches;
    if (!url) {
      _renderOverviewActionCard(_matchesCache, stateData || _lastPolledState);
      return;
    }

    _overviewMatchRefreshInFlight = true;
    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _matchesCache = data;
      _matchesCacheFetchedAt = Date.now();
      _renderOverviewActionCard(data, stateData || _lastPolledState);
    } catch (err) {
      console.warn('[HubEngine] Overview action fetch failed:', err.message);
      _renderOverviewActionCard(_matchesCache, stateData || _lastPolledState);
    } finally {
      _overviewMatchRefreshInFlight = false;
    }
  }

  function _bindScheduleControls() {
    const filterWrap = document.getElementById('schedule-match-filter');
    if (!filterWrap || filterWrap.dataset.bound === '1') {
      _setScheduleFilter(_scheduleFilter, { rerender: false });
      return;
    }

    filterWrap.dataset.bound = '1';
    filterWrap.querySelectorAll('[data-schedule-filter]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const next = btn.getAttribute('data-schedule-filter') || 'all';
        _setScheduleFilter(next, { rerender: true });
      });
    });

    _setScheduleFilter(_scheduleFilter, { rerender: false });
  }

  function _setScheduleFilter(nextFilter, { rerender = true } = {}) {
    const isStaffView = _shell?.dataset.isStaffView === 'true';
    const normalized = String(nextFilter || '').toLowerCase() === 'my' ? 'my' : 'all';
    _scheduleFilter = isStaffView ? 'all' : normalized;

    document.querySelectorAll('#schedule-match-filter [data-schedule-filter]').forEach((btn) => {
      const key = btn.getAttribute('data-schedule-filter') || 'all';
      const active = key === _scheduleFilter;
      btn.className = active
        ? 'hub-schedule-filter-btn active px-3 py-1.5 rounded-md text-[10px] font-black uppercase tracking-wider text-cyan-200 bg-cyan-400/15 border border-cyan-300/25 transition-colors'
        : 'hub-schedule-filter-btn px-3 py-1.5 rounded-md text-[10px] font-black uppercase tracking-wider text-gray-400 border border-transparent hover:text-white transition-colors';
    });

    if (!rerender) return;

    if (_scheduleMatchesCache) {
      _renderScheduleMatches(_scheduleMatchesCache);
      return;
    }
    _fetchScheduleMatches();
  }

  // ──────────────────────────────────────────────────────────
  // Utilities
  // ──────────────────────────────────────────────────────────
  function _getCookie(name) {
    const cookies = String(document.cookie || '').split(';');
    const needle = `${name}=`;
    for (const c of cookies) {
      const item = c.trim();
      if (!item.startsWith(needle)) continue;
      return decodeURIComponent(item.slice(needle.length));
    }
    return '';
  }

  function _sanitizeCsrfToken(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    return raw.replace(/^['\"]|['\"]$/g, '');
  }

  function _resolveCsrfToken() {
    const shellToken = _sanitizeCsrfToken(_shell?.dataset?.csrfToken || '');
    if (shellToken) return shellToken;

    const hiddenInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    const inputToken = _sanitizeCsrfToken(hiddenInput ? hiddenInput.value : '');
    if (inputToken) return inputToken;

    const meta = document.querySelector('meta[name="csrf-token"], meta[name="csrfmiddlewaretoken"]');
    const metaToken = _sanitizeCsrfToken(meta ? meta.getAttribute('content') : '');
    if (metaToken) return metaToken;

    return _sanitizeCsrfToken(_getCookie('csrftoken'));
  }

  function _csrfHeaders(extraHeaders) {
    const base = {
      'X-CSRFToken': _resolveCsrfToken(),
      'X-Requested-With': 'XMLHttpRequest',
    };
    return {
      ...base,
      ...(extraHeaders || {}),
    };
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
          <button data-click="HubEngine.closeMapViewer" class="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors">
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

      if (!data.generated && data.group_context?.has_groups && data.group_context?.groups_drawn) {
        const renderedGroupTables = await _renderBracketGroupTablesFallback(data.group_context);
        if (renderedGroupTables) return;
      }

      _renderBracket(data);
    } catch (err) {
      console.warn('[HubEngine] Bracket fetch failed:', err.message);
      _hide('bracket-skeleton');
      _showError('hub-bracket-tree', 'Failed to load bracket. Please try again.', 'bracket');
    }
  }

  function _buildProjectedSeedingPanel(groupContext) {
    const pairs = Array.isArray(groupContext?.projected_seeding_pairs)
      ? groupContext.projected_seeding_pairs
      : [];
    if (!pairs.length) return '';

    const title = groupContext?.projected_seeding_title || 'Projected Seeding (Cross-Match)';
    return `<div class="hub-glass rounded-xl p-4 border border-cyan-400/20 bg-cyan-400/[0.04] mb-5">
      <p class="text-[10px] font-bold uppercase tracking-widest text-cyan-300 mb-3">${_esc(title)}</p>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
        ${pairs.map((pair) => `
          <div class="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 flex items-center justify-between text-xs font-semibold text-white">
            <span>${_esc(pair?.p1_label || '?')}</span>
            <span class="text-[10px] uppercase tracking-widest text-gray-500">vs</span>
            <span>${_esc(pair?.p2_label || '?')}</span>
          </div>
        `).join('')}
      </div>
    </div>`;
  }

  function _buildBracketGroupTables(groups, message, groupContext) {
    let html = '<div class="space-y-8">';

    const projectedPanel = _buildProjectedSeedingPanel(groupContext);
    if (projectedPanel) {
      html += projectedPanel;
    }

    html += `
      <div class="premium-card p-6 border-l-4 border-l-[#00F0FF]">
        <p class="font-mono text-[10px] font-bold uppercase tracking-widest text-[#00F0FF] mb-2">Group Stage</p>
        <h3 class="font-display font-bold text-xl text-white">Group Tables Are Ready</h3>
        <p class="text-sm text-gray-400 mt-2">${_esc(message || 'Groups are drawn. The organizer will generate round-robin matches next; current group standings are shown below.')}</p>
      </div>`;

    groups.forEach((group) => {
      const standings = Array.isArray(group?.standings) ? group.standings : [];
      html += `
        <div class="mb-8">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-8 h-8 rounded-lg bg-[#00F0FF]/20 flex items-center justify-center border border-[#00F0FF]/30">
              <i data-lucide="flag" class="w-4 h-4 text-[#00F0FF]"></i>
            </div>
            <h3 class="font-display font-bold text-2xl text-white">${_esc(group?.name || 'Group')}</h3>
          </div>
          <div class="premium-card overflow-x-auto p-1">
            <table class="w-full text-left border-collapse">
              <thead><tr class="bg-black/40 border-b border-white/10">
                <th class="p-4 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest w-12 text-center">#</th>
                <th class="p-4 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest min-w-[180px]">Team</th>
                <th class="p-4 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">P</th>
                <th class="p-4 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">W</th>
                <th class="p-4 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">D</th>
                <th class="p-4 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">L</th>
                <th class="p-4 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center hidden md:table-cell">GD</th>
                <th class="p-4 font-mono text-sm font-black text-[#00F0FF] uppercase tracking-widest text-right pr-6">PTS</th>
              </tr></thead>
              <tbody class="divide-y divide-white/5">`;

      if (!standings.length) {
        html += `<tr><td colspan="8" class="p-6 text-center text-sm text-gray-500">No standings rows available yet.</td></tr>`;
      } else {
        standings.forEach((row) => {
          const gd = Number(row?.goal_difference || 0);
          const isYou = row?.is_you;
          const avatarInner = _renderAvatarInner(row?.name || 'TBD', row?.logo_url || '', '', 'w-9 h-9 rounded-lg object-cover');
          let rankBadge;
          if (row.rank === 1) {
            rankBadge = `<div class="w-7 h-7 rounded bg-gradient-to-br from-yellow-400 to-yellow-600 text-black font-black text-xs flex items-center justify-center mx-auto">${row.rank}</div>`;
          } else if (row.rank === 2) {
            rankBadge = `<div class="w-7 h-7 rounded bg-gray-700 text-white font-black text-xs flex items-center justify-center mx-auto">${row.rank}</div>`;
          } else {
            rankBadge = `<div class="w-7 h-7 rounded bg-gray-800 text-gray-400 font-black text-xs flex items-center justify-center mx-auto">${row.rank ?? '-'}</div>`;
          }
          const rowCls = isYou ? 'bg-[#00F0FF]/5 border-l-4 border-l-[#00F0FF]' : 'hover:bg-white/5 transition';
          const nameCls = isYou ? 'font-display font-bold text-white text-[#00F0FF]' : 'font-display font-bold text-white';
          const ptsCls = isYou ? 'font-mono font-black text-xl text-[#00F0FF] glow-text-primary' : 'font-mono font-black text-xl text-white';
          const youTag = isYou ? `<span class="font-mono text-[9px] uppercase tracking-widest text-[#00F0FF] font-bold">You</span>` : '';
          html += `
                <tr class="${rowCls}">
                  <td class="p-4 text-center">${rankBadge}</td>
                  <td class="p-4"><div class="flex items-center gap-3"><div class="w-9 h-9 rounded-lg bg-[#050508] overflow-hidden${isYou ? ' ring-2 ring-[#00F0FF]' : ''}">${avatarInner}</div><div class="flex flex-col"><span class="${nameCls}">${_esc(row?.name || 'TBD')}</span>${youTag}</div></div></td>
                  <td class="p-4 text-center font-mono text-gray-300">${row?.matches_played ?? 0}</td>
                  <td class="p-4 text-center font-mono text-[#00FF66] font-bold">${row?.won ?? 0}</td>
                  <td class="p-4 text-center font-mono text-gray-500">${row?.drawn ?? 0}</td>
                  <td class="p-4 text-center font-mono ${(row?.lost || 0) > 0 ? 'text-[#FF2A55] font-bold' : 'text-gray-600'}">${row?.lost ?? 0}</td>
                  <td class="p-4 text-center font-mono ${gd > 0 ? 'text-[#00FF66]' : gd < 0 ? 'text-[#FF2A55]' : 'text-gray-400'} hidden md:table-cell">${gd > 0 ? '+' : ''}${gd}</td>
                  <td class="p-4 text-right pr-6 ${ptsCls}">${_esc(String(row?.points ?? 0))}</td>
                </tr>`;
        });
      }

      html += `
              </tbody>
            </table>
          </div>
        </div>`;
    });

    html += '</div>';
    return html;
  }

  async function _renderBracketGroupTablesFallback(groupContext) {
    const tree = document.getElementById('hub-bracket-tree');
    const standingsUrl = _shell?.dataset.apiStandings;
    if (!tree || !standingsUrl) return false;

    try {
      let standingsData = _standingsCache;
      const hasGroupStandings = standingsData
        && standingsData.standings_type === 'groups'
        && Array.isArray(standingsData.groups)
        && standingsData.groups.length > 0;

      if (!hasGroupStandings) {
        const resp = await fetch(standingsUrl, { credentials: 'same-origin' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        standingsData = await resp.json();
        _standingsCache = standingsData;
      }

      if (!standingsData || standingsData.standings_type !== 'groups' || !Array.isArray(standingsData.groups) || standingsData.groups.length === 0) {
        return false;
      }

      tree.classList.remove('hidden');
      tree.innerHTML = _buildBracketGroupTables(standingsData.groups, groupContext?.message, groupContext);
      _hide('bracket-not-generated');
      _hide('bracket-zoom-controls');
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return true;
    } catch (err) {
      console.warn('[HubEngine] Group standings fallback render failed:', err.message);
      return false;
    }
  }

  function _updateBracketEmptyState(data) {
    const titleEl = document.getElementById('bracket-empty-title');
    const messageEl = document.getElementById('bracket-empty-message');
    const projectedEl = document.getElementById('bracket-empty-projected');
    if (!titleEl || !messageEl) return;

    let title = 'Bracket Not Generated';
    let message = 'The tournament bracket will appear here once the organizer generates matchups. This typically happens after check-in closes.';

    const groupCtx = data && data.group_context ? data.group_context : null;
    if (groupCtx && groupCtx.has_groups) {
      if (groupCtx.groups_drawn) {
        title = 'Group Stage Matches Pending';
        message = groupCtx.message || 'Groups are drawn, but matches are not generated yet. The organizer will generate group-stage matches soon.';
      } else {
        title = 'Group Stage Setup In Progress';
        message = groupCtx.message || 'Group stage is configured but the draw is not finalized yet. Bracket data will appear after those steps are completed.';
      }
    } else if (data && data.has_bracket_record) {
      title = 'Bracket Setup In Progress';
      message = 'A bracket draft exists, but no bracket matches are available yet.';
    }

    titleEl.textContent = title;
    messageEl.textContent = message;

    if (projectedEl) {
      const projectedHtml = _buildProjectedSeedingPanel(groupCtx);
      projectedEl.innerHTML = projectedHtml;
      projectedEl.classList.toggle('hidden', !projectedHtml);
    }
  }

  function _renderBracket(data) {
    _hide('bracket-skeleton');

    const tree = document.getElementById('hub-bracket-tree');
    if (!tree) return;

    if (!data.generated || !data.rounds || data.rounds.length === 0) {
      tree.innerHTML = '';
      tree.classList.add('hidden');
      _updateBracketEmptyState(data || {});
      _show('bracket-not-generated');
      _hide('bracket-zoom-controls');
      return;
    }

    const myPid = data.my_participant_id || null;
    function _isMyMatch(m) {
      if (!myPid) return false;
      const p1id = m.participant1?.id || null;
      const p2id = m.participant2?.id || null;
      return p1id === myPid || p2id === myPid;
    }

    tree.classList.remove('hidden');
    _hide('bracket-not-generated');
    _show('bracket-zoom-controls');
    const fmtEl = document.getElementById('bracket-format-label');
    if (fmtEl && data.format_display) fmtEl.textContent = data.format_display;

    // ── Match card renderer (premium demo design) ──
    function matchHTML(m) {
      const p1 = m.participant1 || { name: 'TBD', score: null, is_winner: false };
      const p2 = m.participant2 || { name: 'TBD', score: null, is_winner: false };
      const isLive = m.state === 'live';
      const isDone = m.state === 'completed' || m.state === 'forfeit';
      const isPending = !isDone && !isLive;
      const isTBD = isPending && p1.name === 'TBD' && p2.name === 'TBD';
      const isMine = _isMyMatch(m);
      const mineAttr = isMine ? ' data-mine="1"' : '';
      const mineCls = isMine ? ' bk-mine' : '';
      const p1Avatar = _renderAvatarInner(p1.name || 'TBD', p1.logo_url || '', 'text-[9px] font-black text-white flex items-center justify-center', 'w-full h-full object-cover');
      const p2Avatar = _renderAvatarInner(p2.name || 'TBD', p2.logo_url || '', 'text-[9px] font-black text-white flex items-center justify-center', 'w-full h-full object-cover');
      const matchNum = m.match_number ? `M${m.match_number}` : '';

      // ── LIVE match ──
      if (isLive) {
        return `<div class="bk-match bk-live${mineCls}" data-mid="${m.id || ''}"${mineAttr}>
          <div class="bk-match-head" style="background:rgba(0,240,255,0.08);border-bottom:1px solid rgba(0,240,255,0.15);">
            <span class="bk-mnum">${matchNum}</span>
            <span class="bk-badge-live"><span class="bk-dot"></span> LIVE</span>
          </div>
          <div class="bk-team">
            <div class="bk-team-meta"><div class="bk-team-avatar">${p1Avatar}</div><span class="bk-name" style="color:#fff;font-weight:700;">${_esc(p1.name)}</span></div>
            <span class="bk-sc" style="color:#9CA3AF;">${p1.score != null ? p1.score : '-'}</span>
          </div>
          <div class="bk-vs">VS</div>
          <div class="bk-team">
            <div class="bk-team-meta"><div class="bk-team-avatar">${p2Avatar}</div><span class="bk-name" style="color:#fff;font-weight:700;">${_esc(p2.name)}</span></div>
            <span class="bk-sc" style="color:#9CA3AF;">${p2.score != null ? p2.score : '-'}</span>
          </div>
        </div>`;
      }

      // ── UPCOMING / PENDING match ──
      if (isPending) {
        // Canonical bracket badge: lobby_state → check_in/ready → datetime → TBD
        const lobbyState = m.lobby_state || '';
        let upLabel, badgeCls;
        if (lobbyState === 'lobby_open' || lobbyState === 'live_grace_or_ready') {
          upLabel = 'LOBBY OPEN';
          badgeCls = 'bk-badge-up bk-badge-lobby';
        } else if (lobbyState === 'lobby_closed' || lobbyState === 'forfeit_review') {
          upLabel = 'EXPIRED';
          badgeCls = 'bk-badge-up bk-badge-expired';
        } else if (m.state === 'check_in') {
          upLabel = 'CHECK IN';
          badgeCls = 'bk-badge-up';
        } else if (m.state === 'ready') {
          upLabel = 'READY';
          badgeCls = 'bk-badge-up';
        } else if (isTBD) {
          upLabel = 'TBD';
          badgeCls = 'bk-badge-up bk-badge-tbd';
        } else if (m.scheduled_at) {
          // Scheduled match with real participants — show formatted datetime
          const dt = new Date(m.scheduled_at);
          if (!Number.isNaN(dt.getTime())) {
            const opts = _timeFormatOptions({ day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' });
            upLabel = dt.toLocaleString([], opts);
          } else {
            upLabel = 'UPCOMING';
          }
          badgeCls = 'bk-badge-up bk-badge-sched-dt';
        } else {
          upLabel = 'UPCOMING';
          badgeCls = 'bk-badge-up';
        }
        const nameStyle = isTBD ? 'color:#4B5563;font-style:italic;' : '';
        const tbdCls = isTBD ? ' bk-tbd' : '';
        const schedCls = !isTBD ? ' bk-sched' : '';
        return `<div class="bk-match${mineCls}${tbdCls}${schedCls}" data-mid="${m.id || ''}"${mineAttr}>
          <div class="bk-match-head">
            <span class="bk-mnum">${matchNum}</span>
            <span class="${badgeCls}">${_esc(upLabel)}</span>
          </div>
          <div class="bk-team">
            <div class="bk-team-meta"><div class="bk-team-avatar">${p1Avatar}</div><span class="bk-name" style="${nameStyle}">${_esc(p1.name)}</span></div>
            <span class="bk-sc">–</span>
          </div>
          <div class="bk-vs">VS</div>
          <div class="bk-team">
            <div class="bk-team-meta"><div class="bk-team-avatar">${p2Avatar}</div><span class="bk-name" style="${nameStyle}">${_esc(p2.name)}</span></div>
            <span class="bk-sc">–</span>
          </div>
        </div>`;
      }

      // ── COMPLETED match ──
      const p1w = p1.is_winner;
      const p2w = p2.is_winner;
      return `<div class="bk-match bk-done${mineCls}" data-mid="${m.id || ''}"${mineAttr}>
        <div class="bk-match-head">
          <span class="bk-mnum">${matchNum}</span>
          <span class="bk-badge-ft">FT</span>
        </div>
        <div class="bk-team${p1w ? ' bk-w' : ''}"${!p1w && isDone ? ' style="opacity:0.5;"' : ''}>
          <div class="bk-team-meta">${p1w ? '<div style="width:3px;align-self:stretch;border-radius:2px;background:#00FF66;box-shadow:0 0 8px rgba(0,255,102,0.3);flex-shrink:0;"></div>' : ''}<div class="bk-team-avatar${p1w ? ' border border-[#00FF66]/40' : ''}">${p1Avatar}</div><span class="bk-name">${_esc(p1.name)}</span></div>
          <span class="bk-sc">${p1.score != null ? p1.score : '-'}</span>
        </div>
        <div class="bk-vs">VS</div>
        <div class="bk-team${p2w ? ' bk-w' : ''}"${!p2w && isDone ? ' style="opacity:0.5;"' : ''}>
          <div class="bk-team-meta">${p2w ? '<div style="width:3px;align-self:stretch;border-radius:2px;background:#00FF66;box-shadow:0 0 8px rgba(0,255,102,0.3);flex-shrink:0;"></div>' : ''}<div class="bk-team-avatar${p2w ? ' border border-[#00FF66]/40' : ''}">${p2Avatar}</div><span class="bk-name">${_esc(p2.name)}</span></div>
          <span class="bk-sc">${p2.score != null ? p2.score : '-'}</span>
        </div>
      </div>`;
    }

    function normalizeGroupRoundName(groupName, roundName, roundNumber) {
      if (!roundName) return roundNumber ? `Round ${roundNumber}` : 'Round';
      const prefix = `${groupName} - `;
      if (groupName && roundName.startsWith(prefix)) {
        return roundName.slice(prefix.length);
      }
      return roundName;
    }

    function buildGroupSectionsFromRounds(rounds) {
      const grouped = {};
      (rounds || []).forEach((round) => {
        const matches = Array.isArray(round?.matches) ? round.matches : [];
        const firstMatch = matches[0] || {};
        const groupName = round?.group_name || firstMatch.group_name || 'Ungrouped';

        if (!grouped[groupName]) {
          grouped[groupName] = {
            group_name: groupName,
            rounds: [],
          };
        }

        grouped[groupName].rounds.push({
          round_number: round?.round_number || 0,
          round_name: normalizeGroupRoundName(groupName, round?.round_name, round?.round_number),
          matches,
        });
      });

      return Object.values(grouped).map((group) => {
        group.rounds.sort((a, b) => (a.round_number || 0) - (b.round_number || 0));
        return group;
      });
    }

    const fmt = (data.format || '').toLowerCase();
    const isDE = fmt.includes('double');

    const explicitGroupSections = Array.isArray(data.group_stage?.groups) ? data.group_stage.groups : [];
    const shouldRenderGroupStage = data.generated_mode === 'group_stage'
      && (explicitGroupSections.length > 0 || data.rounds.some((round) => !!round?.group_name));

    if (shouldRenderGroupStage) {
      const groupSections = explicitGroupSections.length > 0
        ? explicitGroupSections
        : buildGroupSectionsFromRounds(data.rounds);

      let groupedHtml = _buildProjectedSeedingPanel(data.group_context || null);

      groupSections.forEach((group) => {
        const rounds = Array.isArray(group?.rounds) ? group.rounds : [];
        if (!rounds.length) return;

        // Premium group header
        groupedHtml += `<div class="mb-10">`;
        groupedHtml += `<div class="flex items-center gap-3 mb-6">`;
        groupedHtml += `<div class="w-8 h-8 rounded-lg bg-[#00F0FF]/20 flex items-center justify-center border border-[#00F0FF]/30"><i data-lucide="flag" class="w-4 h-4 text-[#00F0FF]"></i></div>`;
        groupedHtml += `<h3 class="font-display font-bold text-2xl text-white">${_esc(group?.group_name || 'Group')}</h3>`;
        groupedHtml += `</div>`;

        rounds.forEach((round) => {
          const title = round?.round_name || (round?.round_number ? `Round ${round.round_number}` : 'Round');
          const matches = round.matches || [];
          if (!matches.length) return;

          groupedHtml += `<div class="mb-6">`;
          groupedHtml += `<div class="flex items-center gap-3 mb-4">`;
          groupedHtml += `<span class="font-mono text-[10px] font-bold uppercase tracking-widest text-gray-500">${_esc(title)}</span>`;
          groupedHtml += `<div class="h-px flex-1 bg-gradient-to-r from-white/10 to-transparent"></div>`;
          groupedHtml += `</div>`;

          groupedHtml += `<div class="grid grid-cols-1 md:grid-cols-2 gap-4">`;
          matches.forEach((m) => {
            const p1 = m.participant1 || { name: 'TBD', score: null, is_winner: false };
            const p2 = m.participant2 || { name: 'TBD', score: null, is_winner: false };
            const isLive = m.state === 'live';
            const isDone = m.state === 'completed' || m.state === 'forfeit';

            const stateColors = {
              live: '#FF2A55', ready: '#00FF66', check_in: '#00F0FF',
              scheduled: '#FFB800', completed: '#4B5563', forfeit: '#4B5563'
            };
            const borderColor = isLive ? stateColors.live : isDone
              ? (p1.is_winner || p2.is_winner ? '#00FF66' : '#4B5563')
              : (stateColors[m.state] || '#4B5563');

            const p1Avatar = _renderAvatarInner(p1.name || 'TBD', p1.logo_url || '', 'text-[9px] font-black text-white flex items-center justify-center', 'w-full h-full object-cover');
            const p2Avatar = _renderAvatarInner(p2.name || 'TBD', p2.logo_url || '', 'text-[9px] font-black text-white flex items-center justify-center', 'w-full h-full object-cover');

            const p1NameCls = p1.is_winner ? 'font-display font-bold text-sm text-white' : (isDone && !p1.is_winner ? 'font-display text-sm text-gray-500' : 'font-display text-sm text-white');
            const p2NameCls = p2.is_winner ? 'font-display font-bold text-sm text-white' : (isDone && !p2.is_winner ? 'font-display text-sm text-gray-500' : 'font-display text-sm text-white');
            const p1ScoreCls = p1.is_winner ? 'font-mono font-black text-[#00FF66]' : 'font-mono text-gray-500';
            const p2ScoreCls = p2.is_winner ? 'font-mono font-black text-[#00FF66]' : 'font-mono text-gray-500';

            let stateHtml = '';
            if (isLive) {
              stateHtml = `<span class="flex items-center gap-1.5 text-[9px] font-black uppercase tracking-widest text-[#FF2A55]"><span class="w-1.5 h-1.5 rounded-full bg-[#FF2A55] animate-pulse"></span> LIVE</span>`;
            } else if (isDone) {
              stateHtml = `<span class="text-[9px] font-bold uppercase tracking-widest text-gray-600">FT</span>`;
            } else {
              const upLabel = m.state === 'check_in' ? 'CI' : m.state === 'ready' ? 'RDY' : 'VS';
              stateHtml = `<span class="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded" style="color:rgba(255,184,0,0.7);background:rgba(255,184,0,0.08);">${upLabel}</span>`;
            }

            const cardOpacity = !isDone && !isLive ? 'opacity-60' : '';
            const pendingCardStyle = !isDone && !isLive ? 'background:rgba(5,5,8,0.5);' : '';

            groupedHtml += `
              <div class="premium-card p-4 border-l-4 hover:bg-white/5 transition ${cardOpacity}" style="border-left-color:${borderColor};${pendingCardStyle}">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3 flex-1 min-w-0">
                    <div class="w-8 h-8 rounded bg-[#050508] overflow-hidden shrink-0">${p1Avatar}</div>
                    <span class="${p1NameCls} truncate">${_esc(p1.name)}</span>
                  </div>
                  <div class="flex items-center gap-3 shrink-0 mx-4">
                    <span class="${p1ScoreCls}">${p1.score != null ? p1.score : '-'}</span>
                    ${stateHtml}
                    <span class="${p2ScoreCls}">${p2.score != null ? p2.score : '-'}</span>
                  </div>
                  <div class="flex items-center gap-3 flex-1 min-w-0 justify-end">
                    <span class="${p2NameCls} truncate text-right">${_esc(p2.name)}</span>
                    <div class="w-8 h-8 rounded bg-[#050508] overflow-hidden shrink-0">${p2Avatar}</div>
                  </div>
                </div>
              </div>`;
          });
          groupedHtml += `</div>`;
          groupedHtml += `</div>`;
        });

        groupedHtml += `</div>`;
      });

      tree.innerHTML = groupedHtml;
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

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

    // ── Build HTML for all sections ──
    let html = '';
    sections.forEach(sec => {
      const maxMatches = Math.max(...sec.rounds.map(r => (r.matches || []).length), 1);
      const secH = Math.max(maxMatches * 160, 200);

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
          const isMyPath = cc.hasAttribute('data-mine') || nc.hasAttribute('data-mine');
          path.classList.add(isMyPath ? 'bk-line-mine' : 'bk-line');
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

      // ── Champion banner (premium) ──
      const champ = data.rows.find(r => r.rank === 1);
      if (champ) {
        html += `<div class="premium-card p-8 mb-8 border-l-4 border-l-yellow-400 relative overflow-hidden">`;
        html += `<div class="absolute top-0 right-0 w-32 h-32 bg-gradient-to-bl from-yellow-400/10 to-transparent rounded-bl-full"></div>`;
        html += `<div class="flex items-center gap-6 relative z-10">`;
        html += `<div style="background:linear-gradient(135deg,#FFB800,#E08800);box-shadow:0 0 30px rgba(255,184,0,0.3);" class="w-16 h-16 rounded-xl flex items-center justify-center text-3xl">👑</div>`;
        html += `<div>`;
        html += `<div class="font-mono text-[10px] uppercase tracking-widest text-yellow-400 mb-1">Tournament Champion</div>`;
        html += `<div class="font-display font-black text-3xl text-white">${_esc(champ.name)}</div>`;
        html += `<div class="font-mono text-xs text-gray-400 mt-1">${champ.wins}W – ${champ.losses}L · Maps ${champ.map_wins || 0}–${champ.map_losses || 0} · RD ${champ.round_diff > 0 ? '+' : ''}${champ.round_diff}</div>`;
        html += `</div></div></div>`;
      }

      // ── Final placements table (premium) ──
      html += `<div class="premium-card overflow-x-auto p-1">`;
      html += `<table class="w-full text-left border-collapse">`;
      html += `<thead><tr class="bg-black/40 border-b border-white/10">`;
      html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest w-16 text-center">Place</th>`;
      html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest min-w-[200px]">Team</th>`;
      html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">Series</th>`;
      html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center hidden md:table-cell">Maps</th>`;
      html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center hidden md:table-cell">Rnd Diff</th>`;
      html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-right pr-8">Win%</th>`;
      html += `</tr></thead><tbody class="divide-y divide-white/5">`;

      data.rows.forEach(row => {
        const tc = tierColor(row.rank);
        let rankBadge;
        if (row.rank === 1) {
          rankBadge = `<div style="background:linear-gradient(135deg,#FFB800,#E08800);box-shadow:0 0 12px rgba(255,184,0,0.35);" class="w-8 h-8 rounded font-black flex items-center justify-center mx-auto text-white">1</div>`;
        } else if (row.rank === 2) {
          rankBadge = `<div style="background:linear-gradient(135deg,#C0C0C0,#808080);" class="w-8 h-8 rounded font-black flex items-center justify-center mx-auto text-gray-900">${row.rank}</div>`;
        } else if (row.rank <= 4) {
          rankBadge = `<div style="background:linear-gradient(135deg,#CD7F32,#7B4A1A);" class="w-8 h-8 rounded font-black flex items-center justify-center mx-auto text-white">${row.rank}</div>`;
        } else {
          rankBadge = `<div class="w-8 h-8 rounded bg-gray-800 text-gray-400 font-black flex items-center justify-center mx-auto">${row.rank}</div>`;
        }
        const isYou = row.is_you;
        const youRowCls = isYou ? 'bg-[#00F0FF]/5 hover:bg-[#00F0FF]/10 transition border-l-4 border-l-[#00F0FF] relative' : 'hover:bg-white/5 transition';
        const nameCls = isYou ? 'font-display font-bold text-lg text-[#00F0FF]' : 'font-display font-bold text-lg text-white';
        const avatarRing = isYou ? ' ring-2 ring-[#00F0FF]' : '';
        const youLabel = isYou ? `<span class="font-mono text-[9px] uppercase tracking-widest text-[#00F0FF] font-bold">You</span>` : '';
        const totalGames = row.wins + row.losses;
        const winPct = totalGames > 0 ? Math.round((row.wins / totalGames) * 100) : 0;
        const mapW = row.map_wins || 0;
        const mapL = row.map_losses || 0;
        const rdSign = row.round_diff > 0 ? '+' : '';
        const avatarInner = _renderAvatarInner(row.name || 'TBD', row.logo_url || '', '', 'w-10 h-10 rounded-lg object-cover');

        html += `<tr class="${youRowCls}">`;
        html += `<td class="p-5 text-center">${rankBadge}</td>`;
        html += `<td class="p-5"><div class="flex items-center gap-4"><div class="w-10 h-10 rounded-lg bg-[#050508] overflow-hidden${avatarRing}">${avatarInner}</div><div class="flex flex-col"><span class="${nameCls}">${_esc(row.name)}</span>${youLabel}</div></div></td>`;
        html += `<td class="p-5 text-center"><span class="font-mono"><span style="color:#00FF66" class="font-bold">${row.wins}</span><span class="text-gray-600 mx-1">–</span><span style="color:#FF2A55">${row.losses}</span></span></td>`;
        html += `<td class="p-5 text-center font-mono text-gray-300 hidden md:table-cell">${mapW}–${mapL}</td>`;
        html += `<td class="p-5 text-center font-mono ${row.round_diff > 0 ? 'text-[#00FF66]' : row.round_diff < 0 ? 'text-[#FF2A55]' : 'text-gray-400'} hidden md:table-cell">${rdSign}${row.round_diff}</td>`;
        html += `<td class="p-5 text-right pr-8"><div class="flex items-center gap-2 justify-end"><div class="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden"><div class="h-full rounded-full" style="width:${winPct}%;background:${tc}"></div></div><span class="font-mono text-sm font-bold text-gray-300">${winPct}%</span></div></td>`;
        html += `</tr>`;
      });

      html += `</tbody></table></div>`;
    }

    // ── Group-based standings (premium) ──
    else if (Array.isArray(data.groups) && data.groups.length > 0) {
      // Stage context header
      if (data.stage_label) {
        html += `<div class="flex items-center gap-3 mb-6">`;
        html += `<div class="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center border border-white/10"><i data-lucide="layers" class="w-4 h-4 text-gray-400"></i></div>`;
        html += `<h2 class="font-display font-bold text-xl text-gray-400 uppercase tracking-widest">${_esc(data.stage_label)}</h2>`;
        if (data.current_stage === 'knockout_stage') {
          html += `<span class="ml-auto text-[10px] font-mono text-[#00FF66] bg-[#00FF66]/10 px-3 py-1 rounded-full border border-[#00FF66]/20">Group Stage Complete</span>`;
        }
        html += `</div>`;
      }
      data.groups.forEach(group => {
        html += `<div class="mb-10">`;
        html += `<div class="flex items-center gap-3 mb-6">`;
        html += `<div class="w-8 h-8 rounded-lg bg-[#00F0FF]/20 flex items-center justify-center border border-[#00F0FF]/30"><i data-lucide="flag" class="w-4 h-4 text-[#00F0FF]"></i></div>`;
        html += `<h3 class="font-display font-bold text-2xl text-white">${_esc(group.name)}</h3>`;
        html += `</div>`;

        html += `<div class="premium-card overflow-x-auto p-1">`;
        html += `<table class="w-full text-left border-collapse">`;
        html += `<thead><tr class="bg-black/40 border-b border-white/10">`;
        html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest w-16 text-center">Rank</th>`;
        html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest min-w-[200px]">Participant</th>`;
        html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">PLD</th>`;
        html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">W</th>`;
        html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">D</th>`;
        html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center">L</th>`;
        html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center hidden md:table-cell">GD</th>`;
        html += `<th class="p-5 font-mono text-[10px] font-bold text-gray-500 uppercase tracking-widest text-center hidden lg:table-cell">Form</th>`;
        html += `<th class="p-5 font-mono text-sm font-black text-[#00F0FF] uppercase tracking-widest text-right pr-8">PTS</th>`;
        html += `</tr></thead><tbody class="divide-y divide-white/5">`;

        (group.standings || []).forEach(row => {
          const isYou = row.is_you;
          let rankBadge;
          if (row.rank === 1) {
            rankBadge = `<div style="background:linear-gradient(135deg,#FFB800,#E08800);box-shadow:0 0 12px rgba(255,184,0,0.35);" class="w-8 h-8 rounded font-black flex items-center justify-center mx-auto text-white">${row.rank}</div>`;
          } else if (row.rank === 2) {
            rankBadge = `<div style="background:linear-gradient(135deg,#C0C0C0,#808080);" class="w-8 h-8 rounded font-black flex items-center justify-center mx-auto text-gray-900">${row.rank}</div>`;
          } else {
            rankBadge = `<div class="w-8 h-8 rounded bg-gray-800 text-gray-400 font-black flex items-center justify-center mx-auto">${row.rank}</div>`;
          }
          const youRowCls = isYou
            ? 'bg-[#00F0FF]/5 hover:bg-[#00F0FF]/10 transition border-l-4 border-l-[#00F0FF] relative'
            : (row.is_advancing ? 'hover:bg-white/5 transition' : 'hover:bg-white/5 transition opacity-60');
          const nameCls = isYou ? 'font-display font-bold text-lg text-[#00F0FF]' : 'font-display font-bold text-lg text-white';
          const avatarRing = isYou ? ' ring-2 ring-[#00F0FF]' : '';
          const youLabel = isYou ? `<span class="font-mono text-[9px] uppercase tracking-widest text-[#00F0FF] font-bold">You</span>` : '';
          const advancingBadge = (row.is_advancing && !isYou) ? `<span class="font-mono text-[9px] uppercase tracking-widest text-[#00FF66] font-bold">Qualified</span>` : '';
          const eliminatedBadge = (row.is_eliminated && !isYou) ? `<span class="font-mono text-[9px] uppercase tracking-widest text-[#FF2A55]/60 font-bold">Eliminated</span>` : '';
          const avatarInner = _renderAvatarInner(row.name || 'TBD', row.logo_url || '', '', 'w-10 h-10 rounded-lg object-cover');

          const gdColor = row.goal_difference > 0 ? 'text-[#00FF66]' : row.goal_difference < 0 ? 'text-[#FF2A55]' : 'text-gray-300';
          const gdSign = row.goal_difference > 0 ? '+' : '';

          // Form indicators (W/L/D colored blocks)
          let formHtml = '';
          if (Array.isArray(row.form) && row.form.length > 0) {
            formHtml = row.form.map(r => {
              const u = String(r).toUpperCase();
              const formStyle = u === 'W' ? 'background:#00FF66;color:#000;' : u === 'L' ? 'background:#FF2A55;color:#fff;' : 'background:#6b7280;color:#fff;';
              return `<span style="${formStyle}" class="w-4 h-4 rounded text-[8px] font-black flex items-center justify-center">${u}</span>`;
            }).join('');
          }

          const ptsCls = isYou
            ? 'p-5 text-right pr-8 font-mono font-black text-2xl text-[#00F0FF] glow-text-primary'
            : 'p-5 text-right pr-8 font-mono font-black text-2xl text-white';

          html += `<tr class="${youRowCls}">`;
          html += `<td class="p-5 text-center">${rankBadge}</td>`;
          html += `<td class="p-5"><div class="flex items-center gap-4"><div class="w-10 h-10 rounded-lg bg-[#050508] overflow-hidden${avatarRing}">${avatarInner}</div><div class="flex flex-col"><span class="${nameCls}">${_esc(row.name)}</span>${youLabel}${advancingBadge}${eliminatedBadge}</div></div></td>`;
          html += `<td class="p-5 text-center font-mono text-gray-300">${row.matches_played}</td>`;
          html += `<td class="p-5 text-center font-mono font-bold" style="color:#00FF66">${row.won}</td>`;
          html += `<td class="p-5 text-center font-mono text-gray-500">${row.drawn}</td>`;
          html += `<td class="p-5 text-center font-mono ${row.lost > 0 ? 'font-bold' : 'text-gray-600'}" ${row.lost > 0 ? 'style="color:#FF2A55"' : ''}>${row.lost}</td>`;
          html += `<td class="p-5 text-center font-mono ${gdColor} hidden md:table-cell">${gdSign}${row.goal_difference}</td>`;
          html += `<td class="p-5 text-center hidden lg:table-cell"><div class="flex items-center justify-center gap-1">${formHtml}</div></td>`;
          html += `<td class="${ptsCls}">${row.points}</td>`;
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
    _updateStandingsIntelligence(data);
  }

  // ── Standings intelligence banner ──
  function _updateStandingsIntelligence(data) {
    const el = document.getElementById('hub-standings-intelligence');
    if (!el) return;

    // Find the user's row across groups or bracket rows
    let myRow = null;
    let myGroup = null;
    if (Array.isArray(data.groups)) {
      for (const g of data.groups) {
        for (const r of (g.standings || [])) {
          if (r.is_you) { myRow = r; myGroup = g.name; break; }
        }
        if (myRow) break;
      }
    } else if (Array.isArray(data.rows)) {
      myRow = data.rows.find(r => r.is_you);
    }

    if (!myRow) { el.classList.add('hidden'); return; }

    let msg = '';
    let icon = 'user';
    let color = 'cyan';

    if (myRow.is_advancing) {
      icon = 'trophy';
      color = 'emerald';
      msg = myGroup
        ? `Rank #${myRow.rank} in ${myGroup} — <span class="text-emerald-400 font-bold">Qualified for Knockout</span>`
        : `Rank #${myRow.rank} — Advancing`;
    } else if (myRow.is_eliminated) {
      icon = 'eye';
      color = 'gray';
      msg = myGroup
        ? `Rank #${myRow.rank} in ${myGroup} — Eliminated from group stage`
        : `Rank #${myRow.rank} — Eliminated`;
    } else {
      msg = myGroup
        ? `You are ranked <span class="text-white font-bold">#${myRow.rank}</span> in ${myGroup}`
        : `You are ranked <span class="text-white font-bold">#${myRow.rank}</span>`;

      const adv = data.advancing_per_group;
      if (adv && myGroup) {
        msg += ` · Top ${adv} advance to Knockout`;
      }
    }

    const borderCls = color === 'emerald' ? 'border-emerald-500/20 bg-emerald-500/[0.04]' :
                      color === 'gray' ? 'border-gray-500/20 bg-gray-500/[0.04]' :
                      'border-cyan-500/20 bg-cyan-500/[0.04]';
    const iconCls = color === 'emerald' ? 'text-emerald-400' :
                    color === 'gray' ? 'text-gray-400' :
                    'text-cyan-400';

    el.innerHTML = `<div class="rounded-xl p-3.5 border ${borderCls} flex items-center gap-3">
      <i data-lucide="${icon}" class="w-4 h-4 ${iconCls} flex-shrink-0"></i>
      <p class="text-xs text-gray-300">${msg}</p>
    </div>`;
    el.classList.remove('hidden');
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ──────────────────────────────────────────────────────────
  // Matches Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  // ── Announcement intelligence card (populated after matches fetch) ──
  function _updateAnnouncementIntelligence(data) {
    const el = document.getElementById('hub-ann-intelligence');
    if (!el) return;

    const active = Array.isArray(data.active_matches) ? data.active_matches : [];
    const history = Array.isArray(data.match_history) ? data.match_history : [];
    const myPid = data.my_participant_id || null;
    const currentStage = data.current_stage || null;
    const tournamentFormat = data.tournament_format || null;
    const isGroupPlayoff = tournamentFormat === 'group_playoff';

    // Find user's next scheduled/upcoming match
    let myNext = null;
    if (myPid) {
      for (const m of active) {
        const p1id = m.participant1?.id || m.p1_id || null;
        const p2id = m.participant2?.id || m.p2_id || null;
        if (p1id === myPid || p2id === myPid) {
          const s = String(m.state || '');
          if (s === 'scheduled' || s === 'check_in' || s === 'ready') {
            myNext = m;
            break;
          }
        }
      }
    }

    if (!myNext && active.length === 0 && !isGroupPlayoff) {
      el.classList.add('hidden');
      return;
    }

    let html = '';

    // ── Lifecycle Intelligence: Stage Transition Banner ──
    if (isGroupPlayoff && currentStage === 'knockout_stage') {
      const cancelledGroupMatches = history.filter(m => m.state === 'cancelled' && m.phase === 'group_stage').length;
      const knockoutMatches = active.length;
      html += `<div class="flex items-center gap-2.5 mb-3 p-3 rounded-lg" style="background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.15);">`;
      html += `<div class="w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0" style="background:rgba(16,185,129,0.15);"><i data-lucide="check-circle" class="w-3.5 h-3.5 text-emerald-400"></i></div>`;
      html += `<div>`;
      html += `<span class="text-xs font-bold text-emerald-400">Group Stage Complete</span>`;
      html += `<span class="text-[10px] text-gray-500 ml-2">Knockout bracket is now live`;
      if (knockoutMatches) html += ` · ${knockoutMatches} match${knockoutMatches > 1 ? 'es' : ''} scheduled`;
      html += `</span></div></div>`;
    }

    // ── Lifecycle Event Cards ──
    const lifecycleEvents = [];

    // Event: Group Stage Complete
    if (isGroupPlayoff && currentStage === 'knockout_stage') {
      lifecycleEvents.push({ icon: 'check-circle', color: 'emerald', title: 'Group Stage Complete', desc: 'All group matches concluded. Bracket seeded from final standings.' });
    }

    // Event: Group Draw Complete (groups exist but still in group stage)
    if (isGroupPlayoff && currentStage === 'group_stage' && active.length > 0) {
      lifecycleEvents.push({ icon: 'layers', color: 'cyan', title: 'Group Draw Complete', desc: 'Groups have been drawn. Group stage matches are underway.' });
    }

    // Event: Bracket Published / Knockout Active
    if (currentStage === 'knockout_stage' && active.length > 0) {
      const knockoutActive = active.filter(m => m.phase === 'knockout_stage' || m.round_name !== 'Group Stage');
      if (knockoutActive.length > 0) {
        lifecycleEvents.push({ icon: 'git-branch', color: 'cyan', title: 'Bracket Published', desc: knockoutActive.length + ' knockout match' + (knockoutActive.length > 1 ? 'es' : '') + ' in bracket.' });
      }
    }

    // Event: Tournament Complete / Rewards Available (all matches done, effective status = completed)
    const allMatchesDone = active.length === 0 && history.length > 0;
    const effectiveStatus = data.effective_status || data.status || null;
    if (allMatchesDone && effectiveStatus === 'completed') {
      lifecycleEvents.push({ icon: 'trophy', color: 'amber', title: 'Tournament Complete', desc: 'All matches concluded. Final standings and rewards are available.' });
    }

    // Events derived from user's match data
    if (myPid) {
      // Find user's completed knockout matches
      const myCompleted = history.filter(m => {
        const p1id = m.participant1?.id || m.p1_id || null;
        const p2id = m.participant2?.id || m.p2_id || null;
        return (p1id === myPid || p2id === myPid) && m.state === 'completed';
      });
      const myKnockoutWins = myCompleted.filter(m => m.winner_id === myPid);
      const myKnockoutLosses = myCompleted.filter(m => m.winner_id && m.winner_id !== myPid);

      // Event: Advanced in bracket (won a knockout match)
      if (myKnockoutWins.length > 0 && currentStage === 'knockout_stage') {
        lifecycleEvents.push({ icon: 'trending-up', color: 'emerald', title: 'Advanced', desc: 'Won ' + myKnockoutWins.length + ' knockout match' + (myKnockoutWins.length > 1 ? 'es' : '') + '. Moving forward in the bracket.' });
      }

      // Event: Eliminated (lost in knockout, no next match)
      if (myKnockoutLosses.length > 0 && !myNext && currentStage === 'knockout_stage') {
        lifecycleEvents.push({ icon: 'x-circle', color: 'red', title: 'Eliminated', desc: 'Your tournament run has ended. Check the bracket for final results.' });
      }

      // Event: Opponent Assigned
      if (myNext) {
        const p1id = myNext.participant1?.id || myNext.p1_id || null;
        const oppName = (p1id === myPid)
          ? (myNext.participant2?.name || myNext.p2_name || 'TBD')
          : (myNext.participant1?.name || myNext.p1_name || 'TBD');
        if (oppName && oppName !== 'TBD') {
          lifecycleEvents.push({ icon: 'crosshair', color: 'amber', title: 'Opponent Assigned', desc: 'You face ' + oppName + ' in your next match.' });
        }
      }

      // Event: Check-in Open
      if (myNext && myNext.state === 'check_in') {
        lifecycleEvents.push({ icon: 'ticket', color: 'amber', title: 'Check-in Open', desc: 'Check in now to confirm your participation.', urgent: true });
      }

      // Event: Match Ready
      if (myNext && myNext.state === 'ready') {
        lifecycleEvents.push({ icon: 'zap', color: 'amber', title: 'Match Ready', desc: 'Both players checked in. Enter the match lobby.', urgent: true });
      }

      // Event: Lobby timing
      if (myNext && myNext.state === 'scheduled' && myNext.scheduled_at) {
        try {
          const d = new Date(myNext.scheduled_at);
          const diff = d.getTime() - Date.now();
          if (diff > 0 && diff <= 1800000) {
            lifecycleEvents.push({ icon: 'clock', color: 'amber', title: 'Lobby Opens Soon', desc: 'Match lobby opens in less than 30 minutes.' });
          }
        } catch (_) {}
      }

      // Event: Match Live (user's match is currently in progress)
      if (myPid) {
        const myLiveMatch = active.find(m => {
          const p1id = m.participant1?.id || m.p1_id || null;
          const p2id = m.participant2?.id || m.p2_id || null;
          return (p1id === myPid || p2id === myPid) && String(m.state || '') === 'live';
        });
        if (myLiveMatch) {
          lifecycleEvents.push({ icon: 'radio', color: 'red', title: 'Match Live', desc: 'Your match is in progress right now.', urgent: true });
        }
      }
    }

    // Render lifecycle event cards
    if (lifecycleEvents.length > 0) {
      html += `<div class="space-y-2 mb-4">`;
      const colorMap = { emerald: 'rgba(16,185,129,VAL)', cyan: 'rgba(6,182,212,VAL)', amber: 'rgba(245,158,11,VAL)', red: 'rgba(239,68,68,VAL)' };
      for (const evt of lifecycleEvents) {
        const cFn = colorMap[evt.color] || colorMap.cyan;
        const border = cFn.replace('VAL', '0.2');
        const bg = cFn.replace('VAL', '0.04');
        const iconColor = evt.color === 'emerald' ? 'text-emerald-400' : evt.color === 'amber' ? 'text-amber-400' : evt.color === 'red' ? 'text-red-400' : 'text-cyan-400';
        html += `<div class="flex items-start gap-2.5 p-2.5 rounded-lg" style="background:${bg};border:1px solid ${border};">`;
        html += `<i data-lucide="${_esc(evt.icon)}" class="w-3.5 h-3.5 ${iconColor} mt-0.5 flex-shrink-0"></i>`;
        html += `<div><span class="text-xs font-bold text-white">${_esc(evt.title)}</span>`;
        html += `<span class="text-[10px] text-gray-500 ml-1.5">${_esc(evt.desc)}</span></div>`;
        if (evt.urgent) html += `<span class="ml-auto text-[8px] font-black text-amber-400 uppercase tracking-wider flex-shrink-0 mt-0.5">Action</span>`;
        html += `</div>`;
      }
      html += `</div>`;
    }

    // ── Your Status Section ──
    html += `<div class="flex items-center gap-2 mb-3">`;
    html += `<span class="hub-badge bg-[#00F0FF]/10 text-[#00F0FF] border border-[#00F0FF]/30"><i data-lucide="compass" class="w-3 h-3"></i> Your Status</span>`;
    html += `</div>`;

    if (myNext) {
      const p1id = myNext.participant1?.id || myNext.p1_id || null;
      const oppName = (p1id === myPid)
        ? (myNext.participant2?.name || myNext.p2_name || 'TBD')
        : (myNext.participant1?.name || myNext.p1_name || 'TBD');
      const stateLabel = myNext.state === 'check_in' ? 'Check-in Open'
                       : myNext.state === 'ready' ? 'Match Ready'
                       : 'Scheduled';
      const schedAt = myNext.scheduled_at;
      let timeHint = '';
      if (schedAt) {
        try {
          const d = new Date(schedAt);
          if (!isNaN(d.getTime())) {
            const diff = d.getTime() - Date.now();
            if (diff > 0 && diff < 86400000) {
              const hrs = Math.floor(diff / 3600000);
              const mins = Math.floor((diff % 3600000) / 60000);
              timeHint = hrs > 0 ? `in ${hrs}h ${mins}m` : `in ${mins}m`;
            } else {
              timeHint = d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
            }
          }
        } catch (_) {}
      }

      // Stage context for knockout matches
      const phaseHint = (isGroupPlayoff && currentStage === 'knockout_stage' && myNext.round_name)
        ? ` · ${myNext.round_name}` : '';

      html += `<h4 class="font-display font-bold text-base text-white mb-1">Next Match: vs ${_esc(oppName)}</h4>`;
      html += `<p class="text-xs text-gray-400">`;
      html += `<span class="font-bold text-[#FFB800]">${stateLabel}</span>`;
      if (timeHint) html += ` · ${timeHint}`;
      html += phaseHint;
      html += `</p>`;
      if (myNext.state === 'scheduled') {
        html += `<p class="text-[10px] text-gray-600 mt-2 italic">Lobby opens 30 minutes before match time.</p>`;
      }
    } else if (myPid) {
      // Participant with no upcoming match — check elimination
      const hasLive = active.some(m => m.state === 'live');
      const myFinished = history.filter(m => {
        const p1id = m.participant1?.id || m.p1_id || null;
        const p2id = m.participant2?.id || m.p2_id || null;
        return p1id === myPid || p2id === myPid;
      });
      const myLosses = myFinished.filter(m => {
        return m.loser_id === myPid || (m.winner_id && m.winner_id !== myPid);
      });

      if (isGroupPlayoff && currentStage === 'knockout_stage' && active.length === 0 && myFinished.length > 0) {
        // All knockout matches done and no more scheduled — tournament ending
        html += `<h4 class="font-display font-bold text-base text-white mb-1">Tournament Complete</h4>`;
        html += `<p class="text-xs text-gray-400">All matches have concluded. Check the bracket for final results.</p>`;
      } else if (hasLive) {
        html += `<h4 class="font-display font-bold text-base text-white mb-1">Matches In Progress</h4>`;
        html += `<p class="text-xs text-gray-400">Other matches are being played. Your next match will be determined by current results.</p>`;
      } else {
        html += `<h4 class="font-display font-bold text-base text-white mb-1">Still Competing</h4>`;
        html += `<p class="text-xs text-gray-400">No immediate action needed. Check the Matches tab for updates.</p>`;
      }
    } else {
      // Spectator
      const liveCount = active.filter(m => m.state === 'live').length;
      const upcomingCount = active.filter(m => m.state === 'scheduled' || m.state === 'check_in' || m.state === 'ready').length;
      if (liveCount) {
        html += `<h4 class="font-display font-bold text-base text-white mb-1">${liveCount} Match${liveCount > 1 ? 'es' : ''} Live Now</h4>`;
      } else if (upcomingCount) {
        html += `<h4 class="font-display font-bold text-base text-white mb-1">${upcomingCount} Match${upcomingCount > 1 ? 'es' : ''} Upcoming</h4>`;
      } else if (isGroupPlayoff && currentStage === 'knockout_stage') {
        html += `<h4 class="font-display font-bold text-base text-white mb-1">Knockout Stage Active</h4>`;
        html += `<p class="text-xs text-gray-400">Group stage is complete. Watch the knockout bracket unfold.</p>`;
      }
      if (liveCount || upcomingCount) {
        html += `<p class="text-xs text-gray-400">Follow along in the Matches and Bracket tabs.</p>`;
      }
    }

    el.innerHTML = html;
    el.classList.remove('hidden');
    if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [el] });
  }

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
      _matchesCacheFetchedAt = Date.now();
      _hide('matches-skeleton');
      _renderMatches(data);
      _updateAnnouncementIntelligence(data);
    } catch (err) {
      console.warn('[HubEngine] Matches fetch failed:', err.message);
      _hide('matches-skeleton');
      _showError('hub-match-cards', 'Failed to load matches. Please try again.', 'matches');
    }
  }

  function _matchStatePriority(match) {
    const state = String(match?.state || '').toLowerCase();
    if (state === 'live') return 0;
    if (state === 'ready') return 1;
    if (state === 'check_in') return 2;
    if (state === 'pending_result') return 3;
    if (state === 'scheduled') return 4;
    return 5;
  }

  function _sortMatchesByUrgency(matches) {
    const list = Array.isArray(matches) ? matches.slice() : [];
    const nowMs = Date.now();

    return list.sort((a, b) => {
      const aPriority = _matchStatePriority(a);
      const bPriority = _matchStatePriority(b);
      if (aPriority !== bPriority) return aPriority - bPriority;

      const aTime = _toValidDate(a?.scheduled_at);
      const bTime = _toValidDate(b?.scheduled_at);
      const aTs = aTime ? aTime.getTime() : Number.POSITIVE_INFINITY;
      const bTs = bTime ? bTime.getTime() : Number.POSITIVE_INFINITY;

      const aDistance = Number.isFinite(aTs) ? Math.abs(aTs - nowMs) : Number.POSITIVE_INFINITY;
      const bDistance = Number.isFinite(bTs) ? Math.abs(bTs - nowMs) : Number.POSITIVE_INFINITY;
      if (aDistance !== bDistance) return aDistance - bDistance;
      if (aTs !== bTs) return aTs - bTs;

      const aNumber = Number.parseInt(String(a?.match_number || '0'), 10);
      const bNumber = Number.parseInt(String(b?.match_number || '0'), 10);
      return aNumber - bNumber;
    });
  }

  function _sortMatchHistory(matches) {
    const list = Array.isArray(matches) ? matches.slice() : [];
    return list.sort((a, b) => {
      const aTime = _toValidDate(a?.completed_at) || _toValidDate(a?.scheduled_at);
      const bTime = _toValidDate(b?.completed_at) || _toValidDate(b?.scheduled_at);
      const aTs = aTime ? aTime.getTime() : 0;
      const bTs = bTime ? bTime.getTime() : 0;
      if (aTs !== bTs) return bTs - aTs;

      const aNumber = Number.parseInt(String(a?.match_number || '0'), 10);
      const bNumber = Number.parseInt(String(b?.match_number || '0'), 10);
      return bNumber - aNumber;
    });
  }

  function _renderMatchIdentityBlock(name, mediaUrl, sideLabel, sideClass = '') {
    const safeName = name || 'TBD';
    const avatar = _renderAvatarInner(safeName, mediaUrl || '', 'hub-match-side-initial', 'hub-match-side-image');
    return `
      <div class="hub-match-side ${sideClass}">
        <div class="hub-match-side-avatar">${avatar}</div>
        <div class="min-w-0">
          <p class="hub-match-side-label">${_esc(sideLabel || 'Side')}</p>
          <p class="hub-match-side-name" title="${_esc(safeName)}">${_esc(safeName)}</p>
        </div>
      </div>`;
  }

  function _matchKickoffLabel(match) {
    const scheduled = _toValidDate(match?.scheduled_at);
    if (!scheduled) return 'Schedule pending';
    return _formatDateTime(scheduled, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  function _matchUrgencyText(match, lobbyWindow, lobbyOpen) {
    const state = String(match?.state || '').toLowerCase();
    if (state === 'live') {
      return 'Match is live. Lock in and report right after final whistle.';
    }
    if (lobbyOpen) {
      return `Room is open ${lobbyWindow.minutesBefore} minutes before kickoff.`;
    }
    if (lobbyWindow.opensAt) {
      return `Room unlocks in ${_formatCountdownLabel(lobbyWindow.opensAt)}.`;
    }
    const scheduled = _toValidDate(match?.scheduled_at);
    if (!scheduled) return 'Kickoff time will appear after organizer scheduling.';
    if (scheduled.getTime() < Date.now()) return 'Kickoff window passed. Waiting for organizer update.';
    return `Kickoff in ${_formatCountdownLabel(scheduled)}.`;
  }

  function _renderMatchActionControls(match, { compact = false } = {}) {
    const m = match || {};
    const matchId = JSON.stringify(String(m.id || ''));
    const hasLobby = Boolean(m.match_room_url);
    const stateRaw = String(m.state || '').toLowerCase();
    const terminalState = ['completed', 'forfeit', 'cancelled', 'disputed'].includes(stateRaw);
    const lobbyWindow = _resolveLobbyWindow(m);
    const lobbyOpen = hasLobby && lobbyWindow.isOpen;
    const lobbyClosed = lobbyWindow.isClosed;
    const reschedule = m.reschedule || {};
    const pendingRequest = reschedule.pending_request || null;
    const canPropose = Boolean(reschedule.can_propose);
    const canRespond = Boolean(reschedule.can_respond && pendingRequest && pendingRequest.id);
    const canCounter = Boolean(reschedule.can_counter_offer && pendingRequest && pendingRequest.id);

    const mySide = Number(reschedule.my_side || 0);
    const proposerSide = Number(pendingRequest?.proposer_side || 0);
    const iProposed = Boolean(pendingRequest && mySide && proposerSide && mySide === proposerSide);

    const proposedLabel = _formatRescheduleDatetimeLabel(pendingRequest?.new_time);

    const notices = [];

    // Lobby-closed alert banner
    if (lobbyClosed && !terminalState) {
      const closedReason = m.lobby_info?.lobby_closed_reason;
      const reasonText = closedReason === 'both_no_show'
        ? 'Both participants failed to check in within the allocated time.'
        : 'The lobby window has expired.';
      notices.push(`<div class="flex items-start gap-2.5 p-3 rounded-lg border border-[#FF2A55]/25 bg-[#FF2A55]/8"><i data-lucide="alert-triangle" class="w-4 h-4 text-[#FF2A55] shrink-0 mt-0.5"></i><p class="text-xs text-[#FF8AA0] leading-relaxed">Lobby Closed — ${_esc(reasonText)}</p></div>`);
    }

    if (pendingRequest) {
      let text = `Reschedule proposal pending for ${proposedLabel}.`;
      if (canRespond) {
        text = `Opponent proposed ${proposedLabel}. Respond below.`;
      } else if (iProposed) {
        text = `You proposed ${proposedLabel}. Waiting for opponent response.`;
      }
      notices.push(`<p class="hub-match-note warning">${_esc(text)}</p>`);
    }

    const buttonBase = compact
      ? 'hub-match-cta hub-match-cta-compact'
      : 'hub-match-cta';

    const makeButton = (label, clickHandler, tone = 'neutral', { disabled = false, icon = '' } = {}) => {
      const disabledAttr = disabled ? ' disabled' : '';
      const disabledClass = disabled ? ' hub-match-cta-disabled' : '';
      const iconHtml = icon ? `<i data-lucide="${icon}" class="w-3.5 h-3.5"></i>` : '';
      // Parse clickHandler string into data-click attributes
      let clickAttrs = '';
      if (clickHandler && clickHandler !== 'void(0)') {
        const hMatch = clickHandler.match(/^([\w.]+)\((.*)\)$/s);
        if (hMatch) {
          clickAttrs = `data-click="${hMatch[1]}"`;
          if (hMatch[2].trim()) clickAttrs += ` data-click-args="[${hMatch[2].trim()}]"`;
        }
      }
      return `<button ${clickAttrs} class='${buttonBase} hub-match-cta-${tone}${disabledClass}'${disabledAttr}>${iconHtml}${_esc(label)}</button>`;
    };

    const buttons = [];

    if (lobbyClosed && !terminalState) {
      // Only show reschedule contact button when lobby is closed
      buttons.push(makeButton('Request Reschedule', `HubEngine.requestExpiredLobbyReschedule(${matchId})`, 'warning', { icon: 'calendar-x' }));
    } else if (hasLobby) {
      if (lobbyOpen) {
        buttons.push(makeButton('Enter Match Room', `HubEngine.openMatchLobby(${matchId})`, 'primary', { icon: 'log-in' }));
      }
      // No "unlocks in" notice — that info is in the footer metadata
    }

    // Reschedule buttons (only if lobby not closed — closed state has its own CTA)
    if (!lobbyClosed) {
      if (canPropose) {
        buttons.push(makeButton('Propose New Time', `HubEngine.openRescheduleProposal(${matchId})`, 'neutral'));
      }

      if (pendingRequest && iProposed) {
        buttons.push(makeButton('Reschedule Pending', 'void(0)', 'neutral', { disabled: true }));
      }

      if (canRespond) {
        buttons.push(makeButton('Accept', `HubEngine.respondReschedule(${matchId}, "accept")`, 'positive'));
        if (canCounter) {
          buttons.push(makeButton('Counter Offer', `HubEngine.respondReschedule(${matchId}, "counter")`, 'info'));
        }
        buttons.push(makeButton('Reject', `HubEngine.respondReschedule(${matchId}, "reject")`, 'danger'));
      }
    }

    if (!notices.length && buttons.length === 0) return '';

    return `
      <div class="${compact ? 'mt-2.5' : 'mt-3'} space-y-2">
        ${notices.join('')}
        ${buttons.length ? `<div class="hub-match-cta-row">${buttons.join('')}</div>` : ''}
      </div>`;
  }

  function _renderMatches(data) {
    _hide('matches-skeleton');
    _renderOverviewActionCard(data, _lastPolledState);

    const activeMatches = _sortMatchesByUrgency(data?.active_matches || []);
    const historyMatches = _sortMatchHistory(data?.match_history || []);
    const isStaff = activeMatches.some((m) => m.is_staff_view) || historyMatches.some((m) => m.is_staff_view);

    // Active matches
    const cardsEl = document.getElementById('hub-match-cards');
    if (cardsEl) {
      if (activeMatches.length > 0) {
        _hide('matches-empty');
        let html = '';
        // Group active matches by stage for section headers
        const knockoutActive = activeMatches.filter(m => m.is_knockout || (m.stage || '').toLowerCase().includes('knockout'));
        const groupActive = activeMatches.filter(m => !m.is_knockout && !(m.stage || '').toLowerCase().includes('knockout'));
        const hasMultipleActiveStages = knockoutActive.length > 0 && groupActive.length > 0;

        if (hasMultipleActiveStages && knockoutActive.length > 0) {
          html += `<div class="flex items-center gap-2 mb-3 mt-2"><i data-lucide="trophy" class="w-4 h-4 text-[#FFB800]"></i><span class="text-[10px] font-black uppercase tracking-widest text-[#FFB800]">Knockout Stage</span><div class="flex-1 h-px bg-white/5"></div></div>`;
        }
        const renderCard = (m) => {
          const stateRaw = String(m?.state || '').toLowerCase();
          const isLive = stateRaw === 'live';
          const isReady = stateRaw === 'ready';
          const hasLobby = Boolean(m?.match_room_url);
          const lobbyWindow = _resolveLobbyWindow(m);
          const lobbyOpen = hasLobby && lobbyWindow.isOpen;
          const lobbyClosed = lobbyWindow.isClosed;

          const stateColors = { live: '#FF2A55', ready: '#00FF66', check_in: '#00F0FF', scheduled: '#FFB800', pending_result: '#f97316' };
          const borderColor = lobbyClosed ? '#FF2A55' : (stateColors[stateRaw] || '#4B5563');

          // Status label with lobby awareness
          let statusLabel;
          if (lobbyClosed && !isLive) {
            statusLabel = 'Lobby Closed';
          } else if (lobbyOpen && !isLive) {
            statusLabel = 'Lobby Open';
          } else {
            statusLabel = m.state_display || m.state || 'Scheduled';
          }

          // Badge classes
          let badgeCls;
          if (lobbyClosed && !isLive) {
            badgeCls = 'bg-[#FF2A55]/10 text-[#FF2A55] border-[#FF2A55]/30';
          } else if (isLive) {
            badgeCls = 'bg-[#FF2A55]/10 text-[#FF2A55] border-[#FF2A55]/30';
          } else if (lobbyOpen || isReady) {
            badgeCls = 'bg-[#00FF66]/10 text-[#00FF66] border-[#00FF66]/30';
          } else if (stateRaw === 'pending_result') {
            badgeCls = 'bg-orange-500/10 text-orange-400 border-orange-500/30';
          } else {
            badgeCls = 'bg-[#FFB800]/10 text-[#FFB800] border-[#FFB800]/30';
          }

          // Badge icon
          let badgeIcon;
          if (lobbyClosed && !isLive) {
            badgeIcon = '<i data-lucide="lock" class="w-3 h-3"></i>';
          } else if (isLive) {
            badgeIcon = '<span class="w-1.5 h-1.5 rounded-full bg-[#FF2A55] animate-pulse"></span>';
          } else {
            badgeIcon = '<i data-lucide="clock" class="w-3 h-3"></i>';
          }

          const p1Name = m?.p1_name || (!isStaff ? 'You' : 'TBD');
          const p2Name = m?.p2_name || m?.opponent_name || 'TBD';
          const p1Logo = m?.p1_logo_url || '';
          const p2Logo = m?.p2_logo_url || m?.opponent_logo_url || '';
          const p1AvatarHtml = _renderAvatarInner(p1Name, p1Logo, 'text-[10px] font-black text-white flex items-center justify-center', 'w-full h-full object-cover');
          const p2AvatarHtml = _renderAvatarInner(p2Name, p2Logo, 'text-[10px] font-black text-white flex items-center justify-center', 'w-full h-full object-cover');
          const kickoffLabel = _matchKickoffLabel(m);
          const lobbyCode = m.lobby_info?.lobby_code || '';
          const showScoreline = isLive || stateRaw === 'pending_result';

          // Presence indicator dots
          const p1OnlineDot = m.p1_online
            ? '<span class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-[#0a0a0f]" style="background:#00FF66"></span>'
            : '<span class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-[#0a0a0f]" style="background:#4B5563"></span>';
          const p2OnlineDot = m.p2_online
            ? '<span class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-[#0a0a0f]" style="background:#00FF66"></span>'
            : '<span class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-[#0a0a0f]" style="background:#4B5563"></span>';

          // Determine which side is "you"
          const isParticipantOwn = Boolean(m.is_my_match && !m.is_staff_view);
          const opponentName = String(m?.opponent_name || '').trim().toLowerCase();
          const isP1You = isParticipantOwn && String(m?.p1_name || '').trim().toLowerCase() !== opponentName;
          const p1Border = isP1You ? 'ring-2 ring-[#00F0FF]/70' : '';
          const p2Border = (!isP1You && isParticipantOwn) ? 'ring-2 ring-[#00F0FF]/70' : '';
          const p1NameCls = isP1You ? 'text-[#00F0FF]' : 'text-white';
          const p2NameCls = (!isP1You && isParticipantOwn) ? 'text-[#00F0FF]' : 'text-gray-300';

          // Card styling — compact glassmorphism
          const closedDim = (lobbyClosed && !isLive) ? ' opacity-80' : '';
          const glowShadow = isLive ? 'shadow-[0_0_24px_rgba(255,42,85,0.18)]' : '';
          const cardCls = `bg-black/40 backdrop-blur-md border border-white/10 rounded-xl overflow-hidden border-l-4 relative group hover:bg-white/[0.04] transition${closedDim} ${glowShadow}`;

          html += `
            <article class="${cardCls}" style="border-left-color:${borderColor}">
              ${isLive ? '<div class="absolute inset-0 bg-gradient-to-r from-[#FF2A55]/5 to-transparent pointer-events-none"></div>' : ''}
              <div class="relative p-4 md:px-5 md:py-4">
                <!-- Top row: Round info + Status Badge -->
                <div class="flex items-center justify-between mb-3">
                  <span class="font-mono text-[10px] text-gray-500 uppercase tracking-widest">${_esc(m.round_name || 'Round')} · #${_esc(String(m.match_number || ''))}</span>
                  <span class="hub-badge ${badgeCls} shrink-0">${badgeIcon} ${_esc(statusLabel)}</span>
                </div>

                <!-- Middle row: Team A → VS/Score → Team B -->
                <div class="flex items-center justify-between gap-3 md:gap-6">
                  <div class="flex items-center gap-3 flex-1 min-w-0 justify-end md:justify-start">
                    <span class="font-bold text-base ${p1NameCls} text-right truncate" style="font-family:Outfit,sans-serif">${_esc(p1Name)}</span>
                    <div class="relative w-12 h-12 rounded-lg bg-[#0a0a0f] overflow-visible shrink-0">
                      <div class="w-full h-full rounded-lg overflow-hidden border border-white/10 ${p1Border}">${p1AvatarHtml}</div>
                      ${p1OnlineDot}
                    </div>
                  </div>
                  <div class="shrink-0 px-1">
                    ${showScoreline
                      ? `<div class="flex items-center gap-2"><span class="font-mono font-black text-xl text-white">${Number(m.p1_score || 0)}</span><span class="text-[10px] font-black text-gray-600 bg-black/60 px-1.5 py-0.5 rounded">${isLive ? 'LIVE' : 'FT'}</span><span class="font-mono font-black text-xl text-white">${Number(m.p2_score || 0)}</span></div>`
                      : `<span class="font-black text-xs text-gray-600 bg-black/50 px-3 py-1.5 rounded-lg border border-white/5" style="font-family:Outfit,sans-serif">VS</span>`
                    }
                  </div>
                  <div class="flex items-center gap-3 flex-1 min-w-0">
                    <div class="relative w-12 h-12 rounded-lg bg-[#0a0a0f] overflow-visible shrink-0">
                      <div class="w-full h-full rounded-lg overflow-hidden border border-white/10 ${p2Border}">${p2AvatarHtml}</div>
                      ${p2OnlineDot}
                    </div>
                    <span class="font-bold text-base ${p2NameCls} truncate" style="font-family:Outfit,sans-serif">${_esc(p2Name)}</span>
                  </div>
                </div>

                <!-- Bottom row: Metadata + Action controls -->
                <div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 pt-3 border-t border-white/5 text-[11px]">
                  <div class="flex items-center gap-1.5 text-gray-400">
                    <i data-lucide="calendar-clock" class="w-3 h-3 text-[#00F0FF]/70"></i>
                    <span class="font-mono">${_esc(kickoffLabel)}</span>
                  </div>
                  ${lobbyCode ? `<div class="flex items-center gap-1.5 text-[#00F0FF]"><i data-lucide="key-round" class="w-3 h-3"></i><span class="font-mono">Room ${_esc(lobbyCode)}</span></div>` : ''}
                  ${(lobbyClosed && !isLive) ? '<div class="flex items-center gap-1.5 text-[#FF2A55]"><i data-lucide="timer-off" class="w-3 h-3"></i><span class="font-mono">Expired</span></div>' : ''}
                </div>

                ${_renderMatchActionControls(m)}
              </div>
            </article>`;
        };

        // Render knockout active matches first, then group stage
        knockoutActive.forEach(m => { renderCard(m); });
        if (hasMultipleActiveStages && groupActive.length > 0) {
          html += `<div class="flex items-center gap-2 mb-3 mt-5"><i data-lucide="users" class="w-4 h-4 text-[#00F0FF]"></i><span class="text-[10px] font-black uppercase tracking-widest text-[#00F0FF]">Group Stage</span><div class="flex-1 h-px bg-white/5"></div></div>`;
        }
        groupActive.forEach(m => { renderCard(m); });

        cardsEl.innerHTML = html;
        cardsEl.classList.remove('hidden');
        if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [cardsEl] });
      } else {
        cardsEl.innerHTML = '';
        cardsEl.classList.add('hidden');
        _renderMatchLobbyEmptyState();
        _show('matches-empty');
      }
    }

    _renderMobileMatchesSchedule(data);
    _renderMobileLobby(data);

    // Match history
    const historyEl = document.getElementById('hub-match-history');
    if (historyEl) {
      if (historyMatches.length > 0) {
        // Store match data for map viewer access
        window._hubMatchHistory = historyMatches;

        // Group history by stage for section headers
        const knockoutHistory = historyMatches.filter(m => m.is_knockout || (m.stage || '').toLowerCase().includes('knockout'));
        const groupHistory = historyMatches.filter(m => !m.is_knockout && !(m.stage || '').toLowerCase().includes('knockout'));
        const hasMultipleStages = knockoutHistory.length > 0 && groupHistory.length > 0;

        let html = '';
        let globalIdx = 0;

        function renderHistoryCard(m, mi) {
          const isWin = m.is_winner === true;
          const isLoss = m.is_winner === false;
          const borderColor = isWin ? '#00FF66' : isLoss ? '#FF2A55' : '#4B5563';
          const resultBadge = isStaff
            ? (m.winner_name ? _esc(m.winner_name) : '—')
            : (isWin ? 'W' : isLoss ? 'L' : 'D');
          const resultBgClass = isWin ? 'text-[#00FF66] bg-[#00FF66]/10' : isLoss ? 'text-[#FF2A55] bg-[#FF2A55]/10' : 'text-gray-400 bg-white/5';
          const p1Score = m.p1_score ?? 0;
          const p2Score = m.p2_score ?? 0;
          const p1ScoreClass = isWin ? 'text-[#00FF66] glow-text-success' : 'text-gray-500';
          const p2ScoreClass = isLoss ? 'text-white' : 'text-gray-500';

          const p1Name = isStaff ? _esc(m.p1_name || 'TBD') : _esc(m.p1_name || 'You');
          const p2Name = isStaff ? _esc(m.p2_name || 'TBD') : _esc(m.opponent_name || 'TBD');
          const p1Logo = m.p1_logo_url || '';
          const p2Logo = isStaff ? (m.p2_logo_url || '') : (m.opponent_logo_url || m.p2_logo_url || '');
          const p1AvatarHtml = _renderAvatarInner(p1Name, p1Logo, 'text-[10px] font-black text-white flex items-center justify-center', 'w-full h-full object-cover');
          const p2AvatarHtml = _renderAvatarInner(p2Name, p2Logo, 'text-[10px] font-black text-white flex items-center justify-center', 'w-full h-full object-cover');

          const hasDetail = Array.isArray(m.game_scores) && m.game_scores.length > 0;
          const cursorCls = hasDetail ? 'cursor-pointer' : '';
          const clickAttr = hasDetail ? `data-click="HubEngine.openMapViewer" data-click-args="[window._hubMatchHistory[${mi}]]"` : '';

          html += `
            <div class="premium-card p-4 flex flex-col md:flex-row items-center justify-between gap-4 border-l-4 bg-black/40 hover:bg-black/60 transition ${cursorCls}" style="border-left-color:${borderColor}" ${clickAttr}>
              <div class="flex items-center gap-4 w-full md:w-1/3">
                <span class="font-mono text-[10px] text-gray-500 w-16">${_esc(m.round_name || 'Round')}</span>
                <div class="flex items-center gap-2">
                  <div class="w-8 h-8 rounded bg-[#050508] overflow-hidden">${p1AvatarHtml}</div>
                  <span class="font-display font-bold text-white">${p1Name}</span>
                </div>
              </div>

              <div class="flex items-center justify-center gap-4 w-full md:w-1/3">
                <span class="font-mono font-bold text-xl ${p1ScoreClass}">${p1Score}</span>
                <span class="text-xs text-gray-600 bg-black/50 px-2 py-0.5 rounded">FT</span>
                <span class="font-mono font-bold text-xl ${p2ScoreClass}">${p2Score}</span>
              </div>

              <div class="flex items-center justify-end gap-4 w-full md:w-1/3">
                <div class="flex items-center gap-2">
                  <span class="font-display font-medium text-gray-400 text-right">${p2Name}</span>
                  <div class="w-8 h-8 rounded bg-[#050508] overflow-hidden opacity-50">${p2AvatarHtml}</div>
                </div>
                <span class="w-8 text-center text-xs font-black ${resultBgClass} py-1 rounded">${resultBadge}</span>
              </div>
            </div>`;
        }

        // Render with stage section headers
        if (hasMultipleStages && knockoutHistory.length) {
          html += `<div class="flex items-center gap-3 mb-3 mt-2"><span class="font-mono text-[10px] font-black text-[#00F0FF] uppercase tracking-widest">Knockout Stage</span><div class="h-px flex-1 bg-[#00F0FF]/20"></div></div>`;
          knockoutHistory.forEach((m) => { renderHistoryCard(m, globalIdx); globalIdx++; });
        }
        if (hasMultipleStages && groupHistory.length) {
          html += `<div class="flex items-center gap-3 mb-3 mt-6"><span class="font-mono text-[10px] font-black text-gray-500 uppercase tracking-widest">Group Stage</span><div class="h-px flex-1 bg-white/10"></div></div>`;
          groupHistory.forEach((m) => { renderHistoryCard(m, globalIdx); globalIdx++; });
        }
        if (!hasMultipleStages) {
          historyMatches.forEach((m) => { renderHistoryCard(m, globalIdx); globalIdx++; });
        }

        historyEl.innerHTML = html;
        if (typeof lucide !== 'undefined') lucide.createIcons({ nodes: [historyEl] });
      } else {
        _show('match-history-empty');
      }
    }

    // Icons for empty states and other containers handled by scoped calls above
  }

  function _renderMobileMatchesSchedule(data) {
    const wrap = document.getElementById('hub-mobile-matches-schedule');
    if (!wrap) return;

    const allMatches = [
      ...(data?.active_matches || []),
      ...(data?.match_history || []),
    ];

    if (!allMatches.length) {
      wrap.innerHTML = '<div class="hub-glass rounded-xl p-4 text-center text-xs text-gray-500">No scheduled matches yet.</div>';
      return;
    }

    const sorted = _sortMatchesByUrgency(allMatches);

    const html = sorted.slice(0, 10).map((m) => {
      const scheduled = _toValidDate(m?.scheduled_at);
      const timeLabel = scheduled
        ? _formatDateTime(scheduled, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
        : 'Unscheduled';
      const state = String(m?.state || '').toLowerCase();
      const stateColor = state === 'live'
        ? 'text-[#FF6B88]'
        : state === 'completed' || state === 'forfeit'
          ? 'text-gray-400'
          : state === 'ready'
            ? 'text-[#88FFB7]'
            : 'text-cyan-200';

      const p1Name = m?.p1_name || (!m?.is_staff_view ? 'You' : 'TBD');
      const p2Name = m?.p2_name || m?.opponent_name || 'TBD';
      const p1Avatar = _renderAvatarInner(p1Name, m?.p1_logo_url || '', 'hub-mobile-schedule-initial', 'hub-mobile-schedule-image');
      const p2Avatar = _renderAvatarInner(p2Name, m?.p2_logo_url || m?.opponent_logo_url || '', 'hub-mobile-schedule-initial', 'hub-mobile-schedule-image');

      const relative = scheduled ? _formatCountdownLabel(scheduled) : 'TBD';

      return `
        <div class="hub-mobile-schedule-card">
          <div class="hub-mobile-schedule-top">
            <p class="text-[10px] text-gray-400 uppercase tracking-wider">${_esc(m.round_name || 'Round')} · Match ${m.match_number || ''}</p>
            <span class="text-[10px] font-bold uppercase tracking-wider ${stateColor}">${_esc(m.state_display || m.state || 'scheduled')}</span>
          </div>

          <div class="hub-mobile-schedule-versus">
            <div class="hub-mobile-schedule-side">
              <div class="hub-mobile-schedule-avatar">${p1Avatar}</div>
              <p class="hub-mobile-schedule-name" title="${_esc(p1Name)}">${_esc(p1Name)}</p>
            </div>
            <p class="hub-mobile-schedule-vs">VS</p>
            <div class="hub-mobile-schedule-side hub-mobile-schedule-side-right">
              <p class="hub-mobile-schedule-name" title="${_esc(p2Name)}">${_esc(p2Name)}</p>
              <div class="hub-mobile-schedule-avatar">${p2Avatar}</div>
            </div>
          </div>

          <div class="hub-mobile-schedule-meta">
            <span>${_esc(timeLabel)}</span>
            <span class="hub-mobile-schedule-dot"></span>
            <span>${_esc(relative)}</span>
          </div>
        </div>`;
    }).join('');

    wrap.innerHTML = html;
  }

  // ──────────────────────────────────────────────────────────
  // Mobile lobby countdown live ticker
  // ──────────────────────────────────────────────────────────
  let _mobileLobbyCountdownId = null;

  function _startMobileLobbyCountdown(targetDate, closesAt, countdownEl, joinBtn, statusEl, panelEl) {
    _stopMobileLobbyCountdown();
    if (!countdownEl || !targetDate) return;

    function tick() {
      const now = Date.now();

      // Check if lobby closed
      if (closesAt && now > closesAt.getTime()) {
        countdownEl.textContent = 'CLOSED';
        countdownEl.style.color = '#ef4444';
        if (statusEl) {
          statusEl.className = 'hub-badge hub-badge-neutral';
          statusEl.textContent = 'Lobby Closed';
        }
        if (joinBtn) {
          joinBtn.textContent = 'Lobby Closed';
          joinBtn.disabled = true;
          joinBtn.classList.remove('hub-mobile-lobby-primary-live');
        }
        if (panelEl) {
          panelEl.classList.remove('hub-mobile-lobby-live', 'hub-mobile-lobby-ready');
          panelEl.classList.add('hub-mobile-lobby-waiting');
        }
        _stopMobileLobbyCountdown();
        return;
      }

      const diff = targetDate.getTime() - now;
      if (diff <= 0) {
        countdownEl.textContent = 'NOW';
        countdownEl.style.color = '';
        // Show remaining lobby time if closesAt is available
        if (closesAt) {
          const lobbyRemaining = closesAt.getTime() - now;
          if (lobbyRemaining > 0) {
            const mins = Math.floor(lobbyRemaining / 60000);
            const secs = Math.floor((lobbyRemaining % 60000) / 1000);
            countdownEl.textContent = `Lobby: ${mins}:${String(secs).padStart(2, '0')}`;
          }
        }
        return;
      }

      const totalSec = Math.floor(diff / 1000);
      const h = Math.floor(totalSec / 3600);
      const m = Math.floor((totalSec % 3600) / 60);
      const s = totalSec % 60;
      countdownEl.style.color = '';

      if (h > 0) {
        countdownEl.textContent = `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
      } else {
        countdownEl.textContent = `${m}:${String(s).padStart(2, '0')}`;
      }
    }

    tick();
    _mobileLobbyCountdownId = setInterval(tick, 1000);
  }

  function _stopMobileLobbyCountdown() {
    if (_mobileLobbyCountdownId) {
      clearInterval(_mobileLobbyCountdownId);
      _mobileLobbyCountdownId = null;
    }
  }

  // ──────────────────────────────────────────────────────────
  // Overview action card live countdown ticker
  // ──────────────────────────────────────────────────────────
  let _overviewCountdownId = null;
  let _overviewCountdownTarget = null;

  function _startOverviewCountdown(targetDate) {
    const el = document.getElementById('hub-overview-action-time');
    if (!el) return;

    // Avoid restarting if same target
    if (_overviewCountdownTarget && targetDate &&
        _overviewCountdownTarget.getTime() === targetDate.getTime() && _overviewCountdownId) {
      return;
    }
    _stopOverviewCountdown();
    if (!targetDate || Number.isNaN(targetDate.getTime())) return;

    _overviewCountdownTarget = targetDate;

    function tick() {
      const diff = targetDate.getTime() - Date.now();
      if (diff <= 0) {
        // Guard: if lobby is already closed, show EXPIRED instead of NOW
        const ccState = _lastPolledState?.command_center?.lobby_state || '';
        if (ccState === 'lobby_closed' || ccState === 'forfeit_review') {
          el.textContent = 'EXPIRED';
          el.classList.add('text-red-400');
        } else {
          el.textContent = 'NOW';
          el.classList.remove('text-red-400');
        }
        _stopOverviewCountdown();
        _pollState();
        return;
      }
      const totalSec = Math.floor(diff / 1000);
      const h = Math.floor(totalSec / 3600);
      const m = Math.floor((totalSec % 3600) / 60);
      const s = totalSec % 60;
      if (h > 0) {
        el.textContent = `${h}h ${String(m).padStart(2, '0')}m ${String(s).padStart(2, '0')}s`;
      } else if (m > 0) {
        el.textContent = `${m}m ${String(s).padStart(2, '0')}s`;
      } else {
        el.textContent = `${s}s`;
      }
    }

    tick();
    _overviewCountdownId = setInterval(tick, 1000);
  }

  function _stopOverviewCountdown() {
    if (_overviewCountdownId) {
      clearInterval(_overviewCountdownId);
      _overviewCountdownId = null;
    }
    _overviewCountdownTarget = null;
  }

  function _renderMobileLobby(data) {
    const panel = document.getElementById('hub-mobile-lobby-panel');
    if (!panel) return;

    const statusEl = document.getElementById('hub-mobile-lobby-status');
    const roundEl = document.getElementById('hub-mobile-lobby-round');
    const titleEl = document.getElementById('hub-mobile-lobby-title');
    const subtitleEl = document.getElementById('hub-mobile-lobby-subtitle');
    const countdownEl = document.getElementById('hub-mobile-lobby-countdown');
    const roomEl = document.getElementById('hub-mobile-lobby-room');
    const joinBtn = document.getElementById('hub-mobile-lobby-join');
    const sideAAvatarEl = document.getElementById('hub-mobile-lobby-side-a-avatar');
    const sideANameEl = document.getElementById('hub-mobile-lobby-side-a-name');
    const sideBAvatarEl = document.getElementById('hub-mobile-lobby-side-b-avatar');
    const sideBNameEl = document.getElementById('hub-mobile-lobby-side-b-name');
    const noteWrap = document.getElementById('hub-mobile-lobby-admin-note');
    const noteText = document.getElementById('hub-mobile-lobby-admin-note-text');

    const allMatches = data?.active_matches || [];
    const live = allMatches.find((m) => String(m.state || '').toLowerCase() === 'live');
    const ready = allMatches.find((m) => String(m.state || '').toLowerCase() === 'ready');
    const warmup = allMatches.find((m) => {
      const lobbyWindow = _resolveLobbyWindow(m);
      return lobbyWindow.isOpen && Boolean(m?.match_room_url);
    });
    const target = live || ready || warmup || allMatches[0] || null;

    panel.classList.remove('hub-mobile-lobby-live', 'hub-mobile-lobby-ready', 'hub-mobile-lobby-waiting');

    if (!target) {
      panel.classList.add('hub-mobile-lobby-waiting');
      if (statusEl) {
        statusEl.className = 'hub-badge hub-badge-neutral';
        statusEl.textContent = 'Waiting';
      }
      if (roundEl) roundEl.textContent = 'No active round';
      if (titleEl) titleEl.textContent = 'No active match yet';
      if (subtitleEl) subtitleEl.textContent = 'No room assignment yet. This tab will auto-focus when your match opens.';
      if (countdownEl) countdownEl.textContent = '--:--';
      if (roomEl) roomEl.textContent = 'TBD';
      if (sideAAvatarEl) {
        sideAAvatarEl.innerHTML = _renderAvatarInner('Team A', '', 'hub-mobile-lobby-team-initial', 'hub-mobile-lobby-team-image');
      }
      if (sideBAvatarEl) {
        sideBAvatarEl.innerHTML = _renderAvatarInner('Team B', '', 'hub-mobile-lobby-team-initial', 'hub-mobile-lobby-team-image');
      }
      if (sideANameEl) sideANameEl.textContent = 'Team A';
      if (sideBNameEl) sideBNameEl.textContent = 'Team B';
      if (joinBtn) {
        joinBtn.textContent = 'Open Match Queue';
        joinBtn.classList.remove('hub-mobile-lobby-primary-live');
        joinBtn.onclick = () => switchTab('matches');
      }
      if (noteWrap) noteWrap.classList.add('hidden');
      return;
    }

    const stateRaw = String(target.state || '').toLowerCase();
    const isLive = stateRaw === 'live';
    const isReady = stateRaw === 'ready';
    const lobbyWindow = _resolveLobbyWindow(target);
    const isWarmup = !isLive && !isReady && lobbyWindow.isOpen && Boolean(target.match_room_url);

    if (isLive) {
      panel.classList.add('hub-mobile-lobby-live');
    } else if (isReady || isWarmup) {
      panel.classList.add('hub-mobile-lobby-ready');
    } else {
      panel.classList.add('hub-mobile-lobby-waiting');
    }

    if (statusEl) {
      statusEl.className = `hub-badge ${isLive ? 'hub-badge-danger' : (isReady || isWarmup) ? 'hub-badge-live' : 'hub-badge-info'}`;
      statusEl.textContent = isLive ? 'Live' : (isWarmup ? 'Room Open' : (target.state_display || 'Ready'));
    }
    if (roundEl) roundEl.textContent = `${target.round_name || 'Round'} · Match ${target.match_number || ''}`;
    if (titleEl) {
      const p1 = target.p1_name || 'Team A';
      const p2 = target.p2_name || target.opponent_name || 'Team B';
      titleEl.textContent = `${p1} vs ${p2}`;

      if (sideAAvatarEl) {
        const p1Online = Boolean(target.p1_online);
        const dotColor = p1Online ? '#00FF66' : '#4B5563';
        sideAAvatarEl.innerHTML = _renderAvatarInner(p1, target.p1_logo_url || '', 'hub-mobile-lobby-team-initial', 'hub-mobile-lobby-team-image')
          + `<span class="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-[#0e1222]" style="background:${dotColor}"></span>`;
        sideAAvatarEl.style.position = 'relative';
        sideAAvatarEl.style.overflow = 'visible';
      }
      if (sideBAvatarEl) {
        const p2Online = Boolean(target.p2_online);
        const dotColor = p2Online ? '#00FF66' : '#4B5563';
        sideBAvatarEl.innerHTML = _renderAvatarInner(p2, target.p2_logo_url || target.opponent_logo_url || '', 'hub-mobile-lobby-team-initial', 'hub-mobile-lobby-team-image')
          + `<span class="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-[#0e1222]" style="background:${dotColor}"></span>`;
        sideBAvatarEl.style.position = 'relative';
        sideBAvatarEl.style.overflow = 'visible';
      }
      if (sideANameEl) sideANameEl.textContent = p1;
      if (sideBNameEl) sideBNameEl.textContent = p2;
    }
    if (subtitleEl) {
      subtitleEl.textContent = isLive
        ? 'Room is live. Finish strong and submit the result right away.'
        : (isWarmup
          ? `Room opened ${lobbyWindow.minutesBefore} minutes before kickoff. Lock settings and get ready.`
          : (target.scheduled_at
            ? `Kickoff at ${_formatDateTime(target.scheduled_at, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}. Stay warmed up.`
            : 'Room setup is in progress. Keep your squad ready.'));
    }

    const scheduled = target.scheduled_at ? new Date(target.scheduled_at) : null;
    if (countdownEl) {
      if (isLive) {
        countdownEl.textContent = 'LIVE';
        _stopMobileLobbyCountdown();
      } else if (lobbyWindow.isClosed) {
        countdownEl.textContent = 'CLOSED';
        countdownEl.style.color = '#ef4444';
        _stopMobileLobbyCountdown();
      } else if (scheduled && !Number.isNaN(scheduled.getTime())) {
        _startMobileLobbyCountdown(scheduled, lobbyWindow.closesAt || null, countdownEl, joinBtn, statusEl, panel);
      } else {
        countdownEl.textContent = '--:--';
        _stopMobileLobbyCountdown();
      }
    }

    const roomCode = target.lobby_info?.lobby_code || target.lobby_code || 'Pending';
    if (roomEl) roomEl.textContent = roomCode;
    const matchRoomUrl = target.match_room_url || '';

    if (joinBtn) {
      if (lobbyWindow.isClosed && !isLive) {
        joinBtn.textContent = 'Lobby Closed';
        joinBtn.disabled = true;
        joinBtn.classList.remove('hub-mobile-lobby-primary-live');
        joinBtn.onclick = null;
      } else if ((isLive || isReady || isWarmup) && matchRoomUrl) {
        joinBtn.textContent = 'Enter Match Room';
        joinBtn.disabled = false;
        joinBtn.classList.add('hub-mobile-lobby-primary-live');
        joinBtn.onclick = () => {
          _openMatchRoom(matchRoomUrl);
        };
      } else {
        joinBtn.textContent = 'Open Match Queue';
        joinBtn.disabled = false;
        joinBtn.classList.remove('hub-mobile-lobby-primary-live');
        joinBtn.onclick = () => {
          switchTab('matches');
        };
      }
    }

    const note = target.admin_note || target.note || '';
    if (noteWrap && noteText) {
      if (note) {
        noteText.textContent = note;
        noteWrap.classList.remove('hidden');
      } else {
        noteWrap.classList.add('hidden');
      }
    }

    if (_isMobileViewport() && (isLive || isReady || isWarmup) && !_mobileLobbyAutoFocused && _currentTab !== 'lobby') {
      _mobileLobbyAutoFocused = true;
      switchTab('lobby');
      _showWsToast(isLive ? 'Your match is live. Opening Lobby.' : 'Lobby is open for your upcoming match.', 'info');
    }
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
        <button class="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-bold text-gray-300 hover:text-white transition-colors" data-click="HubEngine.switchTab" data-click-args="[&quot;schedule&quot;]">
          View Schedule
        </button>
        <button class="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-bold text-gray-300 hover:text-white transition-colors" data-click="HubEngine.switchTab" data-click-args="[&quot;bracket&quot;]">
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
      let data = _scheduleMatchesCache;
      if (!data) {
        const requestUrl = new URL(url, window.location.origin);
        if (_shell?.dataset.isStaffView !== 'true') {
          requestUrl.searchParams.set('scope', 'all');
        }

        const resp = await fetch(requestUrl.toString(), { credentials: 'same-origin' });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        data = await resp.json();
        _scheduleMatchesCache = data;
      }
      _renderScheduleMatches(data);
    } catch (err) {
      console.warn('[Hub] Schedule matches fetch failed:', err.message);
      if (skeleton) skeleton.classList.add('hidden');
      if (empty) { empty.classList.remove('hidden'); }
    }
  }

  // ── Schedule date tape state ──
  let _scheduleSelectedDay = null; // null = show all (default: today)

  function _renderScheduleMatches(data) {
    const skeleton = document.getElementById('schedule-match-skeleton');
    const empty    = document.getElementById('schedule-match-empty');
    const list     = document.getElementById('schedule-match-list');
    const tapeWrap = document.getElementById('schedule-date-tape-wrapper');
    const tape     = document.getElementById('schedule-date-tape');

    if (skeleton) skeleton.classList.add('hidden');

    // Combine active + history matches (exclude cancelled group-stage clutter)
    const allMatches = [
      ...(data.active_matches || []),
      ...(data.match_history || [])
    ].filter(m => m.state !== 'cancelled');

    const isParticipantView = _shell?.dataset.isStaffView !== 'true';
    const filteredMatches = isParticipantView && _scheduleFilter === 'my'
      ? allMatches.filter((m) => Boolean(m.is_my_match))
      : allMatches;

    if (filteredMatches.length === 0) {
      if (tapeWrap) tapeWrap.classList.add('hidden');
      if (empty) {
        empty.classList.remove('hidden');
        empty.innerHTML = `
          <i data-lucide="calendar-off" class="w-10 h-10 text-gray-600 mx-auto mb-3"></i>
          <p class="text-sm text-gray-500">${_scheduleFilter === 'my' ? 'No personal matches scheduled yet.' : 'No matches scheduled yet.'}</p>
          <p class="text-xs text-gray-600 mt-1">${_scheduleFilter === 'my' ? 'Switch to All Matches to browse the full event timetable.' : 'Match times will appear here once the bracket is generated.'}</p>
        `;
      }
      if (list) list.classList.add('hidden');
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    // Sort by scheduled_at (earliest first), unscheduled at end
    const sorted = filteredMatches.slice().sort((a, b) => {
      if (!a.scheduled_at && !b.scheduled_at) return 0;
      if (!a.scheduled_at) return 1;
      if (!b.scheduled_at) return -1;
      return new Date(a.scheduled_at) - new Date(b.scheduled_at);
    });

    // Group by day key (YYYY-MM-DD)
    const dayGroups = {};
    const todayStr = new Date().toDateString();
    sorted.forEach(m => {
      const dt = m.scheduled_at ? new Date(m.scheduled_at) : null;
      const dayKey = dt ? dt.toDateString() : 'Unscheduled';
      if (!dayGroups[dayKey]) dayGroups[dayKey] = { matches: [], date: dt };
      dayGroups[dayKey].matches.push(m);
    });

    // ── Build date tape chips ──
    if (tape && tapeWrap) {
      const dayKeys = Object.keys(dayGroups);
      let tapeHtml = '';

      // "All" chip
      const allActive = _scheduleSelectedDay === null;
      tapeHtml += `<button data-click="HubEngine.scheduleSelectDay" data-click-args="[null]" class="shrink-0 px-4 py-3 rounded-xl border text-center transition-all ${allActive ? 'bg-[#00F0FF]/20 border-[#00F0FF]/40 shadow-[0_0_15px_rgba(0,240,255,0.3)]' : 'bg-black/40 border-white/10 hover:border-white/20'}">
        <div class="font-mono text-[10px] uppercase tracking-widest ${allActive ? 'text-[#00F0FF]' : 'text-gray-500'}">All</div>
        <div class="font-mono font-bold text-sm ${allActive ? 'text-[#00F0FF]' : 'text-gray-400'}">${filteredMatches.length}</div>
      </button>`;

      let todayIdx = -1;
      let chipIdx = 1; // 0 is the "All" chip
      dayKeys.forEach((dayKey) => {
        const info = dayGroups[dayKey];
        const isToday = dayKey === todayStr;
        const isSelected = _scheduleSelectedDay === dayKey;
        const isActive = isSelected;
        const matchCount = info.matches.length;
        const hasLive = info.matches.some(m => m.state === 'live');

        if (isToday) todayIdx = chipIdx;

        let dayLabel, dateLabel;
        if (dayKey === 'Unscheduled') {
          dayLabel = 'TBD';
          dateLabel = 'Unsched.';
        } else {
          const d = info.date;
          dayLabel = isToday ? 'TODAY' : ['SUN','MON','TUE','WED','THU','FRI','SAT'][d.getDay()];
          dateLabel = `${d.getDate()} ${['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.getMonth()]}`;
        }

        const activeCls = isActive
          ? 'bg-[#00F0FF]/20 border-[#00F0FF]/40 shadow-[0_0_15px_rgba(0,240,255,0.3)]'
          : isToday
            ? 'bg-white/5 border-[#00F0FF]/20 hover:border-[#00F0FF]/40'
            : 'bg-black/40 border-white/10 hover:border-white/20';
        const textCls = isActive ? 'text-[#00F0FF]' : isToday ? 'text-white' : 'text-gray-400';
        const subCls = isActive ? 'text-[#00F0FF]' : isToday ? 'text-[#00F0FF]' : 'text-gray-500';

        tapeHtml += `<button data-click="HubEngine.scheduleSelectDay" data-click-args="[&quot;${_esc(dayKey)}&quot;]" class="shrink-0 px-4 py-3 rounded-xl border text-center transition-all min-w-[72px] ${activeCls} relative" data-tape-day="${_esc(dayKey)}">
          ${hasLive ? '<span class="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[#FF2A55] animate-pulse"></span>' : ''}
          <div class="font-mono text-[10px] uppercase tracking-widest ${subCls}">${dayLabel}</div>
          <div class="font-mono font-bold text-sm ${textCls}">${dateLabel}</div>
          <div class="font-mono text-[9px] ${subCls} mt-0.5">${matchCount} match${matchCount !== 1 ? 'es' : ''}</div>
        </button>`;
        chipIdx++;
      });

      tape.innerHTML = tapeHtml;
      tapeWrap.classList.remove('hidden');

      // Auto-scroll to today chip (or first chip if no today)
      requestAnimationFrame(() => {
        const targetIdx = todayIdx >= 0 ? todayIdx : 0;
        const chips = tape.children;
        if (chips[targetIdx]) {
          chips[targetIdx].scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        }
      });

      // If first render and today exists, select today
      if (_scheduleSelectedDay === null && todayIdx >= 0) {
        // Show all on first render by default, tape highlights today
      }
    }

    // ── Filter matches by selected day ──
    const displayMatches = _scheduleSelectedDay
      ? sorted.filter(m => {
          if (_scheduleSelectedDay === 'Unscheduled') return !m.scheduled_at;
          const dt = m.scheduled_at ? new Date(m.scheduled_at) : null;
          return dt && dt.toDateString() === _scheduleSelectedDay;
        })
      : sorted;

    if (displayMatches.length === 0) {
      if (list) list.classList.add('hidden');
      if (empty) {
        empty.classList.remove('hidden');
        empty.innerHTML = `
          <i data-lucide="calendar-x" class="w-10 h-10 text-gray-600 mx-auto mb-3"></i>
          <p class="text-sm text-gray-500">No matches on this day.</p>
        `;
      }
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    // Re-group display matches by day for rendering
    const displayGroups = {};
    displayMatches.forEach(m => {
      const day = m.scheduled_at
        ? _formatDate(m.scheduled_at, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })
        : 'Unscheduled';
      if (!displayGroups[day]) displayGroups[day] = [];
      displayGroups[day].push(m);
    });

    let html = _renderIncomingRescheduleInbox(displayMatches);
    for (const [day, matches] of Object.entries(displayGroups)) {
      const isToday = day !== 'Unscheduled' && new Date(matches[0].scheduled_at).toDateString() === todayStr;
      html += `
        <div class="mb-8">
          <div class="flex items-center gap-4 mb-6">
            <div class="px-3 py-1.5 ${isToday ? 'bg-[#00F0FF]/10 border-[#00F0FF]/30' : 'bg-white/5 border-white/10'} border rounded-lg flex items-center gap-2">
              <i data-lucide="calendar" class="w-4 h-4 ${isToday ? 'text-[#00F0FF]' : 'text-gray-500'}"></i>
              <span class="font-mono text-xs ${isToday ? 'text-[#00F0FF]' : 'text-white'} font-bold tracking-widest">${isToday ? 'TODAY' : _esc(day).toUpperCase()}</span>
            </div>
            <div class="h-px flex-1 bg-gradient-to-r from-white/10 to-transparent"></div>
          </div>`;

      matches.forEach(m => {
        const stateColors = {
          live: '#FF2A55', ready: '#00FF66', check_in: '#00F0FF',
          scheduled: '#FFB800', completed: '#6b7280', cancelled: '#4b5563',
          forfeit: '#4b5563', disputed: '#f97316'
        };
        const color = stateColors[m.state] || '#6b7280';
        const time = m.scheduled_at
          ? _formatTime(m.scheduled_at, { hour: '2-digit', minute: '2-digit' })
          : '—';
        const isLive = m.state === 'live';
        const isCompleted = m.state === 'completed' || m.state === 'forfeit';
        const isParticipantOwnMatch = Boolean(m.is_my_match && !m.is_staff_view);

        const stateLabel = m.state_display || m.state || 'Scheduled';
        const stateBadgeClass = isLive ? 'bg-[#FF2A55]/10 text-[#FF2A55] border-[#FF2A55]/30'
                              : m.state === 'ready' ? 'bg-[#00FF66]/10 text-[#00FF66] border-[#00FF66]/30'
                              : isCompleted ? 'bg-white/5 text-gray-400 border-white/10'
                              : 'bg-[#FFB800]/10 text-[#FFB800] border-[#FFB800]/30';

        const p1Name = m.is_staff_view
          ? _esc(m.p1_name || 'TBD')
          : (isParticipantOwnMatch ? 'You' : _esc(m.p1_name || 'TBD'));
        const p2Name = m.is_staff_view
          ? _esc(m.p2_name || 'TBD')
          : (isParticipantOwnMatch ? _esc(m.opponent_name || 'TBD') : _esc(m.p2_name || 'TBD'));

        const p1Logo = m.p1_logo_url || '';
        const p2Logo = m.is_staff_view ? (m.p2_logo_url || '') : (m.opponent_logo_url || m.p2_logo_url || '');
        const isP1You = isParticipantOwnMatch && p1Name === 'You';
        const p1Border = isP1You ? 'border-[#00F0FF] shadow-[0_0_15px_rgba(0,240,255,0.2)]' : 'border-white/10';
        const p2Border = (!isP1You && isParticipantOwnMatch) ? 'border-[#00F0FF] shadow-[0_0_15px_rgba(0,240,255,0.2)]' : 'border-white/10';
        const p1NameClass = isP1You ? 'text-[#00F0FF]' : 'text-white';
        const p2NameClass = (!isP1You && isParticipantOwnMatch) ? 'text-[#00F0FF]' : 'text-gray-400';
        const p1AvatarHtml = _renderAvatarInner(p1Name, p1Logo, 'text-xs font-black text-white', 'w-full h-full object-cover');
        const p2AvatarHtml = _renderAvatarInner(p2Name, p2Logo, 'text-xs font-black text-white', 'w-full h-full object-cover opacity-50');

        // Score display for completed matches
        let centerContent;
        if (isLive || isCompleted) {
          const leftScore = isParticipantOwnMatch ? (m.your_score ?? 0) : (m.p1_score ?? 0);
          const rightScore = isParticipantOwnMatch ? (m.opponent_score ?? 0) : (m.p2_score ?? 0);
          const leftNum = Number(leftScore);
          const rightNum = Number(rightScore);
          const leftWon = leftNum > rightNum;
          const leftClass = leftWon ? 'text-[#00FF66] glow-text-success' : 'text-gray-500';
          const rightClass = !leftWon && rightNum > leftNum ? 'text-[#00FF66] glow-text-success' : 'text-gray-500';
          centerContent = `
            <div class="flex items-center gap-4">
              <span class="font-mono font-bold text-xl ${leftClass}">${leftScore}</span>
              <span class="text-xs text-gray-600 bg-black/50 px-2 py-0.5 rounded">${isCompleted ? 'FT' : 'LIVE'}</span>
              <span class="font-mono font-bold text-xl ${rightClass}">${rightScore}</span>
            </div>`;
        } else {
          centerContent = `<span class="font-display font-black text-sm text-gray-600 shrink-0 bg-black/50 px-3 py-1.5 rounded-lg border border-white/5">VS</span>`;
        }

        html += `
          <div class="premium-card p-5 border-l-4 mb-4 hover:bg-white/5 transition group" style="border-left-color:${color}">
            <div class="flex flex-col md:flex-row items-center gap-6 relative z-10">
              <div class="w-full md:w-32 text-center border-b md:border-b-0 md:border-r border-white/10 pb-4 md:pb-0 md:pr-6 shrink-0">
                <p class="font-mono font-bold text-3xl text-white">${_esc(time)}</p>
                <p class="font-mono text-[10px] text-[#00F0FF] mt-1 tracking-widest uppercase">${_esc(m.round_name || 'Round')}</p>
              </div>

              <div class="flex-1 w-full flex items-center justify-between md:justify-center gap-4 md:gap-10">
                <div class="flex items-center gap-4 w-[40%] md:w-auto justify-end">
                  <span class="font-display font-bold text-lg ${p1NameClass} text-right truncate">${p1Name}</span>
                  <div class="w-12 h-12 rounded-xl bg-[#050508] overflow-hidden shrink-0 border ${p1Border}">${p1AvatarHtml}</div>
                </div>
                ${centerContent}
                <div class="flex items-center gap-4 w-[40%] md:w-auto justify-start">
                  <div class="w-12 h-12 rounded-xl bg-[#050508] overflow-hidden shrink-0 border ${p2Border}">${p2AvatarHtml}</div>
                  <span class="font-display font-bold text-lg ${p2NameClass} truncate">${p2Name}</span>
                </div>
              </div>

              <div class="w-full md:w-auto mt-4 md:mt-0 shrink-0">
                <span class="hub-badge ${stateBadgeClass}">
                  ${isLive ? '<span class="w-1.5 h-1.5 rounded-full bg-[#FF2A55] animate-pulse"></span>' : '<i data-lucide="clock" class="w-3 h-3"></i>'}
                  ${_esc(stateLabel)}
                </span>
              </div>
            </div>
            ${_renderMatchActionControls(m, { compact: true })}
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

  function scheduleSelectDay(dayKey) {
    _scheduleSelectedDay = dayKey;
    // Re-render with current cached data
    if (_scheduleMatchesCache) {
      _renderScheduleMatches(_scheduleMatchesCache);
    }
  }

  // Public helper for refresh button
  function refreshScheduleMatches() {
    _scheduleMatchesCache = null;
    _scheduleSelectedDay = null;
    _fetchScheduleMatches();
  }

  function openMatchLobby(matchId) {
    const match = _findMatchById(matchId);
    if (!match || !match.match_room_url) {
      _emitToast('warning', 'Match lobby is not available for this card yet.');
      return;
    }

    const lobbyWindow = _resolveLobbyWindow(match);
    if (!lobbyWindow.isOpen) {
      _emitToast('info', `Lobby opens ${lobbyWindow.minutesBefore} minutes before scheduled match time.`);
      return;
    }

    _openMatchRoom(match.match_room_url);
  }

  function _setRescheduleModalBusy(isBusy) {
    _rescheduleModalBusy = Boolean(isBusy);
    const modal = document.getElementById('hub-reschedule-modal');
    if (!modal) return;

    modal.querySelectorAll('button, input, textarea').forEach((el) => {
      if (el.id === 'hub-reschedule-modal-close') return;
      if (el.id === 'hub-reschedule-modal-cancel' && _rescheduleModalBusy) return;
      if ('disabled' in el) {
        el.disabled = _rescheduleModalBusy;
      }
    });

    const cancelBtn = document.getElementById('hub-reschedule-modal-cancel');
    if (cancelBtn) {
      cancelBtn.disabled = false;
    }
  }

  function closeRescheduleModal() {
    if (_rescheduleModalBusy) return;
    _rescheduleModalState = null;
    _closeModal('hub-reschedule-modal');
  }

  function requestExpiredLobbyReschedule(matchId) {
    const match = _findMatchById(matchId);
    const matchLabel = match ? `Match #${match.match_number || match.id}` : `Match #${matchId}`;

    // Switch to support tab and pre-fill the dispute form
    switchTab('support');

    // Small delay to let the tab render before populating fields
    setTimeout(() => {
      selectSupportCategory('dispute');

      const matchRef = document.getElementById('support-match-ref');
      if (matchRef) matchRef.value = matchLabel;

      const subject = document.getElementById('support-subject');
      if (subject) subject.value = `Reschedule Request — ${matchLabel} (Expired Lobby)`;

      const message = document.getElementById('support-message');
      if (message) {
        message.value = `The match lobby for ${matchLabel} has expired. I would like to request an admin-mediated reschedule.\n\nReason: `;
        message.focus();
        _updateCharCount();
      }

      _emitToast('info', 'Expired lobby reschedules require organizer approval. Fill in the details below.');
    }, 200);
  }

  function openRescheduleProposal(matchId) {
    const match = _findMatchById(matchId);
    if (!match) {
      _emitToast('error', 'Unable to find this match in the current view. Refresh and try again.');
      return;
    }

    if (!match?.reschedule?.can_propose) {
      _emitToast('warning', 'Reschedule proposals are not available for this match right now.');
      return;
    }

    const titleEl = document.getElementById('hub-reschedule-modal-title');
    const subtitleEl = document.getElementById('hub-reschedule-modal-subtitle');
    const currentWrapEl = document.getElementById('hub-reschedule-modal-current-wrap');
    const currentValueEl = document.getElementById('hub-reschedule-modal-current');
    const proposedWrapEl = document.getElementById('hub-reschedule-modal-proposed-wrap');
    const proposedValueEl = document.getElementById('hub-reschedule-modal-proposed');
    const datetimeWrapEl = document.getElementById('hub-reschedule-modal-datetime-wrap');
    const datetimeInput = document.getElementById('hub-reschedule-modal-datetime');
    const noteLabelEl = document.getElementById('hub-reschedule-modal-note-label');
    const noteInput = document.getElementById('hub-reschedule-modal-note');
    const noteHintEl = document.getElementById('hub-reschedule-modal-note-hint');
    const helperEl = document.getElementById('hub-reschedule-modal-helper');
    const secondaryBtn = document.getElementById('hub-reschedule-modal-secondary');
    const tertiaryBtn = document.getElementById('hub-reschedule-modal-tertiary');
    const primaryBtn = document.getElementById('hub-reschedule-modal-primary');

    if (!titleEl || !subtitleEl || !datetimeInput || !noteInput || !secondaryBtn || !primaryBtn) {
      _emitToast('error', 'Reschedule modal is not available. Refresh and try again.');
      return;
    }

    const currentScheduled = match.scheduled_at ? new Date(match.scheduled_at) : null;
    const defaultDate = currentScheduled && !Number.isNaN(currentScheduled.getTime())
      ? new Date(currentScheduled.getTime() + (30 * 60 * 1000))
      : new Date(Date.now() + (60 * 60 * 1000));
    defaultDate.setSeconds(0, 0);

    _rescheduleModalState = {
      mode: 'proposal',
      matchId: String(match.id || ''),
    };

    titleEl.textContent = 'Propose Reschedule';
    subtitleEl.textContent = `Send a new kickoff time for Match ${match.match_number || ''}.`;
    if (currentWrapEl) currentWrapEl.classList.remove('hidden');
    if (currentValueEl) {
      currentValueEl.textContent = _formatRescheduleDatetimeLabel(match.scheduled_at) || 'Not scheduled';
    }
    if (proposedWrapEl) proposedWrapEl.classList.add('hidden');
    if (proposedValueEl) proposedValueEl.textContent = '';
    if (datetimeWrapEl) datetimeWrapEl.classList.remove('hidden');

    datetimeInput.value = _toDatetimeLocalValue(defaultDate);
    datetimeInput.min = _toDatetimeLocalValue(new Date(Date.now() + (5 * 60 * 1000)));

    if (noteLabelEl) noteLabelEl.textContent = 'Optional reason for your opponent';
    if (noteHintEl) noteHintEl.textContent = 'Keep this short and actionable (max 500 characters).';
    if (helperEl) helperEl.textContent = 'Time is converted from your selected platform timezone and sent to the server in UTC.';
    noteInput.value = '';
    noteInput.placeholder = 'Example: Player has internet outage until 8:30 PM.';

    secondaryBtn.className = 'hidden';
    secondaryBtn.textContent = 'Reject';
    secondaryBtn.onclick = null;

    if (tertiaryBtn) {
      tertiaryBtn.classList.add('hidden');
      tertiaryBtn.onclick = null;
    }

    primaryBtn.className = 'px-4 py-2 rounded-lg bg-amber-300/20 hover:bg-amber-300/30 border border-amber-300/35 text-amber-100 text-xs font-black uppercase tracking-wider transition-colors';
    primaryBtn.textContent = 'Send Proposal';
    primaryBtn.onclick = () => _submitRescheduleProposal();

    _setRescheduleModalBusy(false);
    _openModal('hub-reschedule-modal', 'hub-reschedule-modal-title');
  }

  async function _submitRescheduleProposal() {
    if (_rescheduleModalBusy || !_rescheduleModalState || _rescheduleModalState.mode !== 'proposal') return;

    const match = _findMatchById(_rescheduleModalState.matchId);
    if (!match) {
      _emitToast('error', 'Unable to find this match. Refresh and try again.');
      return;
    }

    const datetimeInput = document.getElementById('hub-reschedule-modal-datetime');
    const noteInput = document.getElementById('hub-reschedule-modal-note');
    const primaryBtn = document.getElementById('hub-reschedule-modal-primary');
    if (!datetimeInput || !noteInput || !primaryBtn) return;

    const parsed = _parseLocalDatetime(datetimeInput.value);
    if (!parsed) {
      _emitToast('error', 'Invalid date/time. Use the date picker format.');
      return;
    }

    const reason = String(noteInput.value || '').trim().slice(0, 500);
    const url = _proposalEndpoint(match.id);
    if (!url) {
      _emitToast('error', 'Reschedule endpoint is unavailable.');
      return;
    }

    const originalLabel = primaryBtn.textContent;

    try {
      _setRescheduleModalBusy(true);
      primaryBtn.textContent = 'Sending...';

      const resp = await fetch(url, {
        method: 'POST',
        headers: _csrfHeaders({
          'Content-Type': 'application/json',
        }),
        credentials: 'same-origin',
        body: JSON.stringify({
          new_time: parsed.toISOString(),
          reason,
        }),
      });

      const payload = await resp.json().catch(() => ({}));
      if (!resp.ok || payload?.success === false) {
        throw new Error(_rescheduleErrorMessage(payload));
      }

      if (payload?.request) {
        _mutateCachedMatch(match.id, (cached) => {
          if (!cached.reschedule || typeof cached.reschedule !== 'object') {
            cached.reschedule = {};
          }
          cached.reschedule.pending_request = payload.request;
          cached.reschedule.can_propose = false;
          cached.reschedule.can_respond = false;
        });
        _rerenderMatchSurfacesFromCache();
      }

      _setRescheduleModalBusy(false);
      closeRescheduleModal();
      _emitToast('success', 'Reschedule proposal sent. Status is now pending opponent approval.');
      void _refreshMatchSurfaces();
    } catch (err) {
      _emitToast('error', err?.message || 'Failed to send reschedule proposal.');
      _setRescheduleModalBusy(false);
      primaryBtn.textContent = originalLabel;
      return;
    }

    primaryBtn.textContent = originalLabel;
  }

  function _openRescheduleCounterOffer(match, pendingRequest) {
    const titleEl = document.getElementById('hub-reschedule-modal-title');
    const subtitleEl = document.getElementById('hub-reschedule-modal-subtitle');
    const currentWrapEl = document.getElementById('hub-reschedule-modal-current-wrap');
    const currentValueEl = document.getElementById('hub-reschedule-modal-current');
    const proposedWrapEl = document.getElementById('hub-reschedule-modal-proposed-wrap');
    const proposedValueEl = document.getElementById('hub-reschedule-modal-proposed');
    const datetimeWrapEl = document.getElementById('hub-reschedule-modal-datetime-wrap');
    const datetimeInput = document.getElementById('hub-reschedule-modal-datetime');
    const noteLabelEl = document.getElementById('hub-reschedule-modal-note-label');
    const noteInput = document.getElementById('hub-reschedule-modal-note');
    const noteHintEl = document.getElementById('hub-reschedule-modal-note-hint');
    const helperEl = document.getElementById('hub-reschedule-modal-helper');
    const secondaryBtn = document.getElementById('hub-reschedule-modal-secondary');
    const tertiaryBtn = document.getElementById('hub-reschedule-modal-tertiary');
    const primaryBtn = document.getElementById('hub-reschedule-modal-primary');

    if (!titleEl || !subtitleEl || !datetimeInput || !noteInput || !primaryBtn) {
      _emitToast('error', 'Reschedule modal is not available. Refresh and try again.');
      return;
    }

    const currentScheduled = match?.scheduled_at ? new Date(match.scheduled_at) : null;
    const proposedScheduled = pendingRequest?.new_time ? new Date(pendingRequest.new_time) : null;
    const seedDate = proposedScheduled && !Number.isNaN(proposedScheduled.getTime())
      ? new Date(proposedScheduled.getTime() + (30 * 60 * 1000))
      : (currentScheduled && !Number.isNaN(currentScheduled.getTime())
        ? new Date(currentScheduled.getTime() + (30 * 60 * 1000))
        : new Date(Date.now() + (60 * 60 * 1000)));
    seedDate.setSeconds(0, 0);

    _rescheduleModalState = {
      mode: 'counter',
      matchId: String(match?.id || ''),
      requestId: String(pendingRequest?.id || ''),
    };

    titleEl.textContent = 'Counter Reschedule Request';
    subtitleEl.textContent = `Match ${match?.match_number || ''} · ${match?.opponent_name || 'Opponent'}`;
    if (currentWrapEl) currentWrapEl.classList.remove('hidden');
    if (currentValueEl) {
      currentValueEl.textContent = _formatRescheduleDatetimeLabel(match?.scheduled_at) || 'Not scheduled';
    }
    if (proposedWrapEl) proposedWrapEl.classList.remove('hidden');
    if (proposedValueEl) proposedValueEl.textContent = _formatRescheduleDatetimeLabel(pendingRequest?.new_time) || '--';
    if (datetimeWrapEl) datetimeWrapEl.classList.remove('hidden');

    datetimeInput.value = _toDatetimeLocalValue(seedDate);
    datetimeInput.min = _toDatetimeLocalValue(new Date(Date.now() + (5 * 60 * 1000)));

    if (noteLabelEl) noteLabelEl.textContent = 'Optional counter-offer note';
    if (noteHintEl) noteHintEl.textContent = 'Keep this short and actionable (max 500 characters).';
    if (helperEl) helperEl.textContent = 'Pick a new kickoff time to send back to your opponent.';
    noteInput.value = '';
    noteInput.placeholder = 'Example: We can play at 9:30 PM instead.';

    if (secondaryBtn) {
      secondaryBtn.classList.add('hidden');
      secondaryBtn.onclick = null;
    }
    if (tertiaryBtn) {
      tertiaryBtn.classList.add('hidden');
      tertiaryBtn.onclick = null;
    }

    primaryBtn.className = 'px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/35 text-blue-100 text-xs font-black uppercase tracking-wider transition-colors';
    primaryBtn.textContent = 'Send Counter-Offer';
    primaryBtn.onclick = () => _submitRescheduleResponse('counter');

    _setRescheduleModalBusy(false);
    _openModal('hub-reschedule-modal', 'hub-reschedule-modal-title');
  }

  function respondReschedule(matchId, action = '') {
    const preferredAction = String(action || '').toLowerCase();
    if (preferredAction && !['accept', 'reject', 'counter'].includes(preferredAction)) return;

    const match = _findMatchById(matchId);
    if (!match) {
      _emitToast('error', 'Unable to find this match in the current view. Refresh and try again.');
      return;
    }

    const pendingRequest = match?.reschedule?.pending_request;
    if (!match?.reschedule?.can_respond || !pendingRequest?.id) {
      _emitToast('warning', 'No pending reschedule proposal is waiting for your response.');
      return;
    }

    const titleEl = document.getElementById('hub-reschedule-modal-title');
    const subtitleEl = document.getElementById('hub-reschedule-modal-subtitle');
    const currentWrapEl = document.getElementById('hub-reschedule-modal-current-wrap');
    const proposedWrapEl = document.getElementById('hub-reschedule-modal-proposed-wrap');
    const proposedValueEl = document.getElementById('hub-reschedule-modal-proposed');
    const datetimeWrapEl = document.getElementById('hub-reschedule-modal-datetime-wrap');
    const noteLabelEl = document.getElementById('hub-reschedule-modal-note-label');
    const noteInput = document.getElementById('hub-reschedule-modal-note');
    const noteHintEl = document.getElementById('hub-reschedule-modal-note-hint');
    const helperEl = document.getElementById('hub-reschedule-modal-helper');
    const secondaryBtn = document.getElementById('hub-reschedule-modal-secondary');
    const tertiaryBtn = document.getElementById('hub-reschedule-modal-tertiary');
    const primaryBtn = document.getElementById('hub-reschedule-modal-primary');

    if (!titleEl || !subtitleEl || !proposedValueEl || !noteInput || !secondaryBtn || !primaryBtn) {
      _emitToast('error', 'Reschedule modal is not available. Refresh and try again.');
      return;
    }

    if (preferredAction === 'counter') {
      _openRescheduleCounterOffer(match, pendingRequest);
      return;
    }

    const defaultAction = preferredAction || 'accept';
    const oppositeAction = defaultAction === 'accept' ? 'reject' : 'accept';

    _rescheduleModalState = {
      mode: 'respond',
      matchId: String(match.id || ''),
      requestId: String(pendingRequest.id || ''),
    };

    titleEl.textContent = defaultAction === 'reject' ? 'Reject Reschedule Request' : 'Respond To Reschedule Request';
    subtitleEl.textContent = `Match ${match.match_number || ''} · ${match.opponent_name || 'Opponent'}`;
    if (currentWrapEl) currentWrapEl.classList.add('hidden');
    if (proposedWrapEl) proposedWrapEl.classList.remove('hidden');
    proposedValueEl.textContent = _formatRescheduleDatetimeLabel(pendingRequest.new_time);
    if (datetimeWrapEl) datetimeWrapEl.classList.add('hidden');

    if (noteLabelEl) {
      noteLabelEl.textContent = defaultAction === 'reject'
        ? 'Optional note for rejection'
        : 'Optional note for acceptance';
    }
    if (noteHintEl) noteHintEl.textContent = 'Your note is visible in the request audit log (max 500 characters).';
    if (helperEl) helperEl.textContent = 'Choose accept to move the match immediately, or reject to keep the current schedule.';
    noteInput.value = '';
    noteInput.placeholder = defaultAction === 'reject'
      ? 'Example: Team cannot play this slot; propose after 9:00 PM.'
      : 'Example: Confirmed with our roster, this works.';

    const applyButtonStyle = (btn, btnAction) => {
      if (!btn) return;
      if (btnAction === 'accept') {
        btn.className = 'px-4 py-2 rounded-lg bg-[#00FF66]/20 hover:bg-[#00FF66]/30 border border-[#00FF66]/35 text-[#66FFAE] text-xs font-black uppercase tracking-wider transition-colors';
        btn.textContent = 'Accept Proposal';
      } else {
        btn.className = 'px-4 py-2 rounded-lg bg-[#FF2A55]/18 hover:bg-[#FF2A55]/28 border border-[#FF2A55]/35 text-[#FF97AA] text-xs font-black uppercase tracking-wider transition-colors';
        btn.textContent = 'Reject Proposal';
      }
    };

    secondaryBtn.classList.remove('hidden');
    applyButtonStyle(primaryBtn, defaultAction);
    applyButtonStyle(secondaryBtn, oppositeAction);

    if (tertiaryBtn) {
      if (match?.reschedule?.can_counter_offer) {
        tertiaryBtn.classList.remove('hidden');
        tertiaryBtn.textContent = 'Propose New Time';
        tertiaryBtn.onclick = () => _openRescheduleCounterOffer(match, pendingRequest);
      } else {
        tertiaryBtn.classList.add('hidden');
        tertiaryBtn.onclick = null;
      }
    }

    primaryBtn.onclick = () => _submitRescheduleResponse(defaultAction);
    secondaryBtn.onclick = () => _submitRescheduleResponse(oppositeAction);

    _setRescheduleModalBusy(false);
    _openModal('hub-reschedule-modal', 'hub-reschedule-modal-title');
  }

  async function _submitRescheduleResponse(action) {
    const normalizedAction = String(action || '').toLowerCase();
    if (!['accept', 'reject', 'counter'].includes(normalizedAction)) return;
    const expectedMode = normalizedAction === 'counter' ? 'counter' : 'respond';
    if (_rescheduleModalBusy || !_rescheduleModalState || _rescheduleModalState.mode !== expectedMode) return;

    const match = _findMatchById(_rescheduleModalState.matchId);
    if (!match) {
      _emitToast('error', 'Unable to find this match. Refresh and try again.');
      return;
    }

    const noteInput = document.getElementById('hub-reschedule-modal-note');
    const primaryBtn = document.getElementById('hub-reschedule-modal-primary');
    const secondaryBtn = document.getElementById('hub-reschedule-modal-secondary');
    const datetimeInput = document.getElementById('hub-reschedule-modal-datetime');
    if (!noteInput || !primaryBtn || !secondaryBtn) return;
    if (normalizedAction === 'counter' && !datetimeInput) return;

    const responseNote = String(noteInput.value || '').trim().slice(0, 500);
    let counterTime = null;
    if (normalizedAction === 'counter') {
      counterTime = _parseLocalDatetime(datetimeInput.value);
      if (!counterTime) {
        _emitToast('error', 'Invalid date/time. Use the date picker format.');
        return;
      }
    }
    const url = _respondEndpoint(match.id);
    if (!url) {
      _emitToast('error', 'Reschedule endpoint is unavailable.');
      return;
    }

    const originalPrimary = primaryBtn.textContent;
    const originalSecondary = secondaryBtn.textContent;

    try {
      _setRescheduleModalBusy(true);
      if (normalizedAction === 'accept') {
        primaryBtn.textContent = 'Accepting...';
      } else if (normalizedAction === 'reject') {
        secondaryBtn.textContent = 'Rejecting...';
      } else {
        primaryBtn.textContent = 'Sending...';
      }

      const resp = await fetch(url, {
        method: 'POST',
        headers: _csrfHeaders({
          'Content-Type': 'application/json',
        }),
        credentials: 'same-origin',
        body: JSON.stringify({
          action: normalizedAction,
          request_id: _rescheduleModalState.requestId,
          response_note: responseNote,
          new_time: counterTime ? counterTime.toISOString() : undefined,
        }),
      });

      const payload = await resp.json().catch(() => ({}));
      if (!resp.ok || payload?.success === false) {
        throw new Error(_rescheduleErrorMessage(payload));
      }

      _mutateCachedMatch(match.id, (cached) => {
        if (!cached.reschedule || typeof cached.reschedule !== 'object') {
          cached.reschedule = {};
        }
        if (normalizedAction === 'counter' && payload?.request) {
          cached.reschedule.pending_request = payload.request;
          cached.reschedule.can_respond = false;
          cached.reschedule.can_counter_offer = false;
          cached.reschedule.can_propose = false;
        } else {
          cached.reschedule.pending_request = null;
          cached.reschedule.can_respond = false;
          cached.reschedule.can_counter_offer = false;
          if (normalizedAction === 'accept' && payload?.scheduled_at) {
            cached.scheduled_at = payload.scheduled_at;
          }
        }
      });
      _rerenderMatchSurfacesFromCache();

      _setRescheduleModalBusy(false);
      closeRescheduleModal();

      if (normalizedAction === 'counter') {
        _emitToast('success', 'Counter-offer sent. Waiting for opponent response.');
      } else if (normalizedAction === 'accept' && payload?.scheduled_at) {
        _emitToast('success', `Reschedule accepted. New time: ${_formatRescheduleDatetimeLabel(payload.scheduled_at)}.`);
      } else {
        _emitToast('success', normalizedAction === 'accept' ? 'Reschedule accepted.' : 'Reschedule rejected.');
      }

      void _refreshMatchSurfaces();
    } catch (err) {
      _emitToast('error', err?.message || 'Failed to submit reschedule response.');
      _setRescheduleModalBusy(false);
      primaryBtn.textContent = originalPrimary;
      secondaryBtn.textContent = originalSecondary;
      return;
    }

    primaryBtn.textContent = originalPrimary;
    secondaryBtn.textContent = originalSecondary;
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
      requestUrl.searchParams.set('sort', _participantsSort);
      requestUrl.searchParams.set('include_member_avatars', '1');
      requestUrl.searchParams.set('include_profile_avatars', '1');

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

  function _participantMetaPill(p) {
    const source = p || {};
    const meta = [];

    const country = source.country_code || source.country || '';
    const region = source.region_code || source.region || '';
    const role = source.player_role || source.role || '';
    const platform = source.platform || '';

    if (country) meta.push(String(country).toUpperCase());
    else if (region) meta.push(String(region));

    if (role) meta.push(String(role));
    if (platform) meta.push(String(platform));
    if (source.seed) meta.push(`Seed #${source.seed}`);

    if (!meta.length) {
      meta.push(source.type === 'team' ? 'Team' : 'Solo');
    }

    meta.push('Verified');

    return `<span class="px-2 py-0.5 rounded border border-white/10 bg-white/5 text-[9px] font-bold text-gray-300 uppercase tracking-widest inline-flex items-center gap-1">${_esc(meta.join(' • '))}</span>`;
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
      const memberCount = (isTeam && p.member_count) ? `<p class="text-[10px] text-gray-500 uppercase tracking-widest" style="font-family:'Space Grotesk',monospace;">${p.member_count} Member${p.member_count !== 1 ? 's' : ''}</p>` : '';
      const metaPill = _participantMetaPill(p);

      // Seed badge (top-right of card)
      let seedBadge = '';
      if (p.seed) {
        seedBadge = `<div class="absolute top-3 right-3 font-mono text-[10px] font-bold px-2 py-0.5 rounded-md border ${p.seed <= 4 ? 'bg-[#FFB800]/10 border-[#FFB800]/30 text-[#FFB800]' : 'bg-white/5 border-white/10 text-gray-500'}">#${p.seed}</div>`;
      }

      // Stacked member avatars (team mode)
      let avatarStack = '';
      if (isTeam && p.member_avatars && p.member_avatars.length > 0) {
        avatarStack = '<div class="flex -space-x-2 overflow-hidden mt-3">';
        p.member_avatars.slice(0, 3).forEach(ma => {
          if (ma.avatar_url) {
            avatarStack += `<img class="inline-block h-8 w-8 rounded-full ring-2 ring-[#08080C] object-cover" src="${_esc(ma.avatar_url)}" alt="${_esc(ma.initial)}" loading="lazy" decoding="async" data-fallback-text="${_esc(ma.initial)}" data-fallback-class="inline-flex h-8 w-8 rounded-full ring-2 ring-[#08080C] bg-gray-800 items-center justify-center text-[10px] font-bold text-white">`;
          } else {
            avatarStack += `<div class="inline-flex h-8 w-8 rounded-full ring-2 ring-[#08080C] bg-gray-800 items-center justify-center text-[10px] font-bold text-white">${_esc(ma.initial)}</div>`;
          }
        });
        avatarStack += '</div>';
      }

      // Logo / avatar (prefer logo_url, fall back to profile_avatar_url)
      const avatarSrc = p.logo_url || p.profile_avatar_url || '';
      const logo = avatarSrc
        ? `<img src="${_esc(avatarSrc)}" class="w-full h-full object-cover" alt="${_esc(p.name)}" loading="lazy" decoding="async" data-fallback="hide">`
        : `<span class="font-black text-xl" style="font-family:Outfit,sans-serif;">${_esc(p.tag)}</span>`;
      const logoColorClass = p.is_you ? 'bg-[#00F0FF]/20 text-[#00F0FF]' : 'bg-white/5 text-gray-400';

      // Wrap in link if detail_url exists
      const href = p.detail_url ? ` href="${_esc(p.detail_url)}"` : '';
      const tag = p.detail_url ? 'a' : 'div';

      html += `
        <${tag}${href} class="hub-glass p-5 rounded-xl border${youBorder} hover:border-white/20 transition-all group cursor-pointer block relative" data-participant-name="${_esc(p.name.toLowerCase())}">
          ${seedBadge}
          <div class="flex items-center gap-4 mb-1">
            <div class="w-12 h-12 rounded-lg ${logoColorClass} flex items-center justify-center overflow-hidden border border-white/10 shrink-0 group-hover:scale-110 transition-transform">
              ${logo}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-start gap-1 flex-wrap">
                <h3 class="font-bold text-white text-lg group-hover:text-[#00F0FF] transition-colors break-words whitespace-normal leading-tight" style="font-family:Outfit,sans-serif;">${_esc(p.name)}</h3>
                ${youBadge}
                ${checkedIn}
              </div>
              <div class="mt-1">${metaPill}</div>
              ${memberCount}
            </div>
          </div>
          ${avatarStack}
        </${tag}>`;
    });

    grid.innerHTML = html;
    grid.classList.remove('hidden');
    _renderMobileStandingsParticipants(list);
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function _renderMobileStandingsParticipants(list) {
    const wrap = document.getElementById('hub-mobile-standings-participants');
    if (!wrap) return;

    const source = Array.isArray(list) ? list : [];
    if (!source.length) {
      wrap.innerHTML = '<div class="text-xs text-gray-500 text-center py-4">No participant data yet.</div>';
      return;
    }

    const html = source.slice(0, 12).map((p) => {
      const name = _esc(p.name || 'Participant');
      const tag = _esc(p.tag || '?');
      const avatarSrc = p.logo_url || p.profile_avatar_url || '';
      const avatar = avatarSrc
        ? `<img src="${_esc(avatarSrc)}" class="w-full h-full object-cover" alt="${name}" loading="lazy" decoding="async" data-fallback="hide">`
        : `<span class="font-black text-sm" style="font-family:Outfit,sans-serif;">${tag}</span>`;
      const metaPill = _participantMetaPill(p);
      const seed = p.seed ? `<span class="text-[10px] text-slate-400 font-semibold">#${p.seed}</span>` : '';
      return `
        <div class="rounded-2xl border border-white/10 bg-[rgba(13,20,32,0.68)] p-3.5 shadow-[0_12px_24px_rgba(0,0,0,0.32)]">
          <div class="flex items-start justify-between gap-3">
            <div class="flex items-center gap-2.5 min-w-0">
              <div class="w-10 h-10 rounded-full border border-cyan-200/25 bg-cyan-400/10 flex items-center justify-center overflow-hidden shrink-0">
                ${avatar}
              </div>
              <div class="min-w-0">
                <p class="text-sm font-semibold text-white truncate">${name}</p>
                <div class="mt-1">${metaPill}</div>
              </div>
            </div>
            ${seed}
          </div>
        </div>`;
    }).join('');

    wrap.innerHTML = html;
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

  function _bindParticipantsControls() {
    const sortSelect = document.getElementById('participants-sort');
    if (sortSelect && sortSelect.dataset.bound !== '1') {
      sortSelect.dataset.bound = '1';
      try {
        const storedSort = window.localStorage?.getItem(PARTICIPANTS_SORT_KEY);
        if (storedSort) {
          _participantsSort = storedSort;
        }
      } catch (e) {
        // Ignore localStorage failures.
      }
      sortSelect.value = _participantsSort;
      sortSelect.addEventListener('change', () => {
        _participantsSort = sortSelect.value || 'joined_desc';
        try {
          window.localStorage?.setItem(PARTICIPANTS_SORT_KEY, _participantsSort);
        } catch (e) {
          // Ignore localStorage failures.
        }
        _fetchParticipants({ reset: true });
      });
    }

    const mobileSearch = document.getElementById('hub-mobile-standings-search');
    if (mobileSearch && mobileSearch.dataset.bound !== '1') {
      mobileSearch.dataset.bound = '1';
      mobileSearch.addEventListener('input', () => {
        const q = (mobileSearch.value || '').toLowerCase().trim();
        if (!q) {
          _renderMobileStandingsParticipants(_participantsAll);
          return;
        }
        const filtered = (_participantsAll || []).filter((p) =>
          String(p.name || '').toLowerCase().includes(q) || String(p.tag || '').toLowerCase().includes(q)
        );
        _renderMobileStandingsParticipants(filtered);
      });
    }
  }

  // ──────────────────────────────────────────────────────────
  // S27: WebSocket — Real-Time Sync
  // ──────────────────────────────────────────────────────────
  function _connectWebSocket() {
    if (!_shell) return;
    const tid = _shell.dataset.tournamentId;
    if (!tid) { console.warn('[Hub] No tournament ID for WS'); return; }

    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    let url = `${proto}://${location.host}/ws/tournament/${tid}/`;
    let jwt = null;
    try {
      jwt = window.localStorage?.getItem('access_token') || window.sessionStorage?.getItem('access_token') || null;
    } catch (e) {
      jwt = null;
    }
    if (jwt) {
      url += `?token=${encodeURIComponent(jwt)}`;
    }

    try {
      _ws = new WebSocket(url);
    } catch (e) {
      console.warn('[Hub] WS failed:', e);
      return;
    }

    _ws.onopen = () => {
      console.info('[Hub] WS connected');
      _wsReconnectAttempts = 0;
      _wsConnected = true;
      _restartPolling();
      _pollState({ force: true });
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
      _wsConnected = false;
      _restartPolling();
      const ind = document.getElementById('hub-ws-indicator');
      if (ind) { ind.classList.remove('connected'); ind.classList.add('disconnected'); }
      if (evt.code === 4001 || evt.code === 4002 || evt.code === 4003) {
        console.info(`[Hub] WS auth unavailable (${evt.code}) — using poll fallback`);
        return;
      }
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
        _scheduleMatchesCache = null;
        _matchesCacheFetchedAt = 0;
        _refreshActiveTab(['bracket', 'standings', 'matches', 'schedule']);
        _pollState({ force: true });
        _refreshOverviewActionCard({ forceFetch: true, stateData: _lastPolledState });
        break;

      case 'match_completed':
        // Invalidate matches + standings
        _matchesCache = null;
        _standingsCache = null;
        _bracketCache = null;
        _scheduleMatchesCache = null;
        _matchesCacheFetchedAt = 0;
        _refreshActiveTab(['bracket', 'standings', 'matches', 'schedule']);
        _pollState({ force: true });
        _refreshOverviewActionCard({ forceFetch: true, stateData: _lastPolledState });
        // Show a toast notification
        _showWsToast('Match completed', 'info');
        break;

      case 'match_update':
        _matchesCache = null;
        _scheduleMatchesCache = null;
        _matchesCacheFetchedAt = 0;
        _refreshActiveTab(['matches', 'schedule']);
        _pollState({ force: true });
        _refreshOverviewActionCard({ forceFetch: true, stateData: _lastPolledState });
        break;

      case 'announcement_refresh':
        _pollAnnouncements({ force: true });
        break;

      case 'ping':
        // Server heartbeat ping; reply immediately to avoid timeout close (4004).
        if (_ws && _ws.readyState === WebSocket.OPEN) {
          _ws.send(JSON.stringify({
            type: 'pong',
            timestamp: msg.timestamp || Date.now(),
          }));
        }
        break;

      case 'pong':
        break;

      default:
        // Unknown event — do a general poll refresh
        _pollState({ force: true });
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
    _stopOverviewHeroFx();
    _stopPolling();
    if (_countdownId) clearInterval(_countdownId);
    if (_wsPingId) clearInterval(_wsPingId);
    if (_resizeTimer) clearTimeout(_resizeTimer);
    if (_mobileChromeIdleTimer) clearTimeout(_mobileChromeIdleTimer);

    const viewport = document.getElementById('hub-viewport');
    if (viewport) {
      if (_onViewportScroll) viewport.removeEventListener('scroll', _onViewportScroll);
      if (_onViewportTouchStart) viewport.removeEventListener('touchstart', _onViewportTouchStart);
      if (_onViewportPointerDown) viewport.removeEventListener('pointerdown', _onViewportPointerDown);
    }

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
    _onViewportScroll = null;
    _onViewportTouchStart = null;
    _onViewportPointerDown = null;
    _mobileChromeIdleTimer = null;
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
  // Action Center Alert Modal
  // ──────────────────────────────────────────────────────────
  function openAlertModal(source) {
    const titleEl = document.getElementById('hub-alert-modal-title');
    const bodyEl = document.getElementById('hub-alert-modal-body');
    const timeEl = document.getElementById('hub-alert-modal-time');
    const actionEl = document.getElementById('hub-alert-modal-action');
    const typeEl = document.getElementById('hub-alert-modal-type');
    const iconEl = document.getElementById('hub-alert-modal-icon');
    const iconWrapEl = document.getElementById('hub-alert-modal-icon-wrap');
    const modalShell = document.getElementById('hub-alert-modal-shell');
    if (!titleEl || !bodyEl || !timeEl || !actionEl || !typeEl || !iconEl || !iconWrapEl || !modalShell) return;

    const dataset = source && source.dataset ? source.dataset : {};
    const title = (dataset.alertTitle || '').trim() || 'Tournament Alert';
    const body = (dataset.alertBody || '').trim() || 'No details available for this alert.';
    const time = (dataset.alertTime || '').trim();
    const targetUrl = (dataset.alertTargetUrl || '').trim() || '/notifications/';
    const actionLabel = (dataset.alertActionLabel || '').trim() || 'Open';
    const alertId = Number(dataset.alertId || 0);
    const tone = (dataset.alertTone || 'info').trim().toLowerCase();
    const typeLabel = (dataset.alertTypeLabel || 'Update').trim();
    const iconName = (dataset.alertIcon || 'bell-ring').trim().toLowerCase();

    const iconByName = {
      'shield-alert': '⛔',
      'badge-check': '✅',
      'users-round': '👥',
      'receipt-text': '🧾',
      'bell-ring': '🔔',
    };
    const iconByTone = {
      danger: '⛔',
      warning: '⚠',
      success: '✅',
      info: '🔔',
    };

    const toneStyles = {
      danger: { text: '#ff8aa0', border: 'rgba(255,42,85,.35)', bg: 'rgba(255,42,85,.16)', shell: 'rgba(255,42,85,.22)' },
      warning: { text: '#ffd56e', border: 'rgba(255,184,0,.35)', bg: 'rgba(255,184,0,.16)', shell: 'rgba(255,184,0,.22)' },
      success: { text: '#66ffae', border: 'rgba(0,255,102,.35)', bg: 'rgba(0,255,102,.16)', shell: 'rgba(0,255,102,.22)' },
      info: { text: '#a5f3fc', border: 'rgba(34,211,238,.35)', bg: 'rgba(34,211,238,.16)', shell: 'rgba(34,211,238,.22)' },
    };

    const selectedTone = toneStyles[tone] ? tone : 'info';
    const toneStyle = toneStyles[selectedTone];

    const applyTone = (el, bgAlpha = toneStyle.bg) => {
      el.style.backgroundColor = bgAlpha;
      el.style.borderColor = toneStyle.border;
      el.style.color = toneStyle.text;
    };
    applyTone(typeEl);
    applyTone(iconWrapEl);
    applyTone(actionEl, toneStyle.bg);
    modalShell.style.borderColor = toneStyle.shell;

    titleEl.textContent = title;
    bodyEl.textContent = body;
    timeEl.textContent = time;
    typeEl.textContent = typeLabel;
    iconEl.textContent = iconByName[iconName] || iconByTone[selectedTone] || '🔔';
    actionEl.textContent = actionLabel;
    actionEl.href = targetUrl;

    const clearBtn = document.getElementById('hub-alert-modal-clear');
    if (clearBtn) {
      const hasAlertId = alertId > 0;
      clearBtn.dataset.alertId = hasAlertId ? String(alertId) : '';
      clearBtn.disabled = !hasAlertId;
      clearBtn.classList.toggle('opacity-50', !hasAlertId);
      clearBtn.classList.toggle('cursor-not-allowed', !hasAlertId);
    }

    _openModal('hub-alert-modal', 'hub-alert-modal-title');
  }

  function closeAlertModal() {
    _closeModal('hub-alert-modal');
  }

  function requestAlertClear() {
    const clearBtn = document.getElementById('hub-alert-modal-clear');
    const alertId = Number(clearBtn?.dataset?.alertId || 0);
    if (!alertId) return;

    const alertTitle = (document.getElementById('hub-alert-modal-title')?.textContent || '').trim();
    const confirmCopy = document.getElementById('hub-alert-confirm-copy');
    const confirmRoot = document.getElementById('hub-alert-confirm-modal');
    if (!confirmRoot) return;

    if (confirmCopy) {
      confirmCopy.textContent = `This will remove "${alertTitle || 'this alert'}" from your Action Center.`;
    }
    confirmRoot.dataset.alertId = String(alertId);
    _openModal('hub-alert-confirm-modal', 'hub-alert-confirm-title');
  }

  function closeAlertConfirmModal() {
    _closeModal('hub-alert-confirm-modal');
  }

  let _pendingAlertDelete = null;

  function _removeUndoBar() {
    const existing = document.getElementById('hub-alert-undo-bar');
    if (existing) existing.remove();
  }

  function _showUndoBar({ message, onUndo }) {
    _removeUndoBar();
    const bar = document.createElement('div');
    bar.id = 'hub-alert-undo-bar';
    bar.className = 'fixed bottom-4 right-4 z-[120] hub-glass rounded-xl border border-cyan-400/30 bg-[#0a1728]/95 px-4 py-3 shadow-[0_12px_40px_rgba(2,8,24,.55)]';
    bar.innerHTML = `
      <div class="flex items-center gap-3">
        <p class="text-xs text-gray-100">${_esc(message || 'Alert cleared.')}</p>
        <button type="button" id="hub-alert-undo-btn" class="px-2.5 py-1 rounded-md bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/30 text-cyan-200 text-[10px] font-black uppercase tracking-wider">Undo</button>
      </div>`;
    document.body.appendChild(bar);

    const undoBtn = document.getElementById('hub-alert-undo-btn');
    if (undoBtn) {
      undoBtn.addEventListener('click', () => {
        try {
          if (typeof onUndo === 'function') onUndo();
        } finally {
          _removeUndoBar();
        }
      }, { once: true });
    }
  }

  async function _persistAlertDelete(slug, alertId) {
    const resp = await fetch(`/tournaments/${slug}/hub/api/alerts/${alertId}/delete/`, {
      method: 'POST',
      headers: _csrfHeaders({
        'Content-Type': 'application/json',
      }),
      credentials: 'same-origin',
    });
    const data = await resp.json();
    if (!resp.ok || !data.success) {
      throw new Error(data.error || `HTTP ${resp.status}`);
    }
    return data;
  }

  async function confirmAlertClear() {
    const slug = _shell?.dataset?.slug || '';
    const confirmRoot = document.getElementById('hub-alert-confirm-modal');
    const alertId = Number(confirmRoot?.dataset?.alertId || 0);
    if (!slug || !alertId) return;

    try {
      if (_pendingAlertDelete?.timerId) {
        clearTimeout(_pendingAlertDelete.timerId);
        _pendingAlertDelete = null;
        _removeUndoBar();
      }

      closeAlertConfirmModal();
      closeAlertModal();

      const row = document.querySelector(`[data-hub-alert-row="${alertId}"]`);
      if (row) {
        row.remove();
      }

      const deletionState = {
        slug,
        alertId,
        undone: false,
        timerId: null,
      };
      _pendingAlertDelete = deletionState;

      _showUndoBar({
        message: 'Alert cleared. Undo within 5 seconds.',
        onUndo: async () => {
          deletionState.undone = true;
          if (deletionState.timerId) clearTimeout(deletionState.timerId);
          _pendingAlertDelete = null;
          await refreshActionCenter();
          _emitToast('success', 'Alert restored.');
        },
      });

      deletionState.timerId = setTimeout(async () => {
        if (deletionState.undone) return;
        try {
          await _persistAlertDelete(slug, alertId);
          _removeUndoBar();
          await refreshActionCenter();
          _emitToast('success', 'Alert removed.');
        } catch (persistErr) {
          console.error('[HubEngine] Failed to persist alert delete:', persistErr);
          await refreshActionCenter();
          _emitToast('error', 'Could not remove alert. It has been restored.');
        } finally {
          if (_pendingAlertDelete === deletionState) {
            _pendingAlertDelete = null;
          }
        }
      }, 5000);
    } catch (err) {
      console.error('[HubEngine] Failed to clear alert:', err);
      _emitToast('error', 'Could not clear alert. Please try again.');
    }
  }

  async function refreshActionCenter() {
    const actionCenter = document.getElementById('hub-action-center');
    if (!actionCenter) return;

    try {
      const refreshUrl = new URL(window.location.href);
      refreshUrl.searchParams.set('_ac_refresh', String(Date.now()));
      const resp = await fetch(refreshUrl.toString(), {
        method: 'GET',
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const html = await resp.text();

      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const nextActionCenter = doc.getElementById('hub-action-center');
      if (nextActionCenter) {
        actionCenter.replaceWith(nextActionCenter);
        if (typeof lucide !== 'undefined') lucide.createIcons();
      } else {
        actionCenter.remove();
      }
    } catch (err) {
      console.error('[HubEngine] Failed to refresh Action Center:', err);
    }
  }

  // ──────────────────────────────────────────────────────────
  // VIP Pass Modal
  // ──────────────────────────────────────────────────────────
  function openTicketModal() {
    _openModal('ticketModal', 'hub-ticket-modal-title');
    _ensureTicketQr();
  }

  function closeTicketModal() {
    _closeModal('ticketModal');
  }

  async function downloadTicketPass() {
    const card = document.getElementById('hub-ticket-export');
    if (!card) return;

    const button = document.querySelector('#ticketModal button[data-click="HubEngine.downloadTicketPass"]');
    const originalHtml = button ? button.innerHTML : '';

    if (button) {
      button.disabled = true;
      button.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Rendering...';
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    try {
      if (typeof html2canvas === 'undefined') {
        throw new Error('html2canvas is unavailable');
      }

      if (typeof lucide !== 'undefined') {
        lucide.createIcons();
      }

      _ensureTicketQr();

      await _waitForTicketAssets(card, 2800);
      card.classList.add('is-exporting');

      const rect = card.getBoundingClientRect();
      const canvas = await html2canvas(card, {
        scale: 4,
        backgroundColor: '#050508',
        foreignObjectRendering: false,
        useCORS: true,
        allowTaint: true,
        imageTimeout: 0,
        scrollX: 0,
        scrollY: -window.scrollY,
        width: Math.ceil(rect.width),
        height: Math.ceil(rect.height),
      });

      const link = document.createElement('a');
      link.download = 'VIP_Pass.png';
      link.href = canvas.toDataURL('image/png', 1.0);
      link.click();
    } catch (err) {
      console.error('[HubEngine] VIP pass download failed:', err);
      _emitToast('error', 'Could not generate VIP pass image. Please try again.');
      _announceLiveMessage('Could not generate VIP pass image. Please try again.', 'assertive');
    } finally {
      card.classList.remove('is-exporting');
      if (button) {
        button.disabled = false;
        button.innerHTML = originalHtml;
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    }
  }

  async function _waitForTicketAssets(root, timeoutMs = 2500) {
    if (!root) return;

    const waits = [];
    if (document.fonts && document.fonts.ready) {
      waits.push(document.fonts.ready.catch(() => null));
    }
    waits.push(_waitForImageAssets(root, timeoutMs));
    waits.push(_waitForTicketQrReady(Math.min(timeoutMs, 1800)));

    await Promise.all(waits);
    await new Promise((resolve) => setTimeout(resolve, 120));
  }

  function _waitForImageAssets(root, timeoutMs = 2000) {
    return new Promise((resolve) => {
      const images = Array.from(root.querySelectorAll('img'));
      if (!images.length) {
        resolve();
        return;
      }

      let done = false;
      const finish = () => {
        if (done) return;
        done = true;
        resolve();
      };

      const pending = images.filter((img) => !img.complete || img.naturalWidth === 0);
      if (!pending.length) {
        finish();
        return;
      }

      let remaining = pending.length;
      const onSettled = () => {
        remaining -= 1;
        if (remaining <= 0) finish();
      };

      pending.forEach((img) => {
        img.addEventListener('load', onSettled, { once: true });
        img.addEventListener('error', onSettled, { once: true });
      });

      setTimeout(finish, timeoutMs);
    });
  }

  function _waitForTicketQrReady(timeoutMs = 1500) {
    return new Promise((resolve) => {
      const started = Date.now();
      (function check() {
        const qrRoot = document.getElementById('hub-ticket-qr');
        if (qrRoot && qrRoot.querySelector('canvas, img')) {
          resolve();
          return;
        }
        if ((Date.now() - started) >= timeoutMs) {
          resolve();
          return;
        }
        setTimeout(check, 40);
      })();
    });
  }

  function _ensureTicketQr() {
    const qrRoot = document.getElementById('hub-ticket-qr');
    if (!qrRoot || typeof QRCode === 'undefined') return;
    if (qrRoot.querySelector('canvas, img')) return;

    const slug = _shell?.dataset?.slug || '';
    qrRoot.innerHTML = '';
    new QRCode(qrRoot, {
      text: `${window.location.origin}/tournaments/${slug}/`,
      width: 150,
      height: 150,
      colorDark: '#000000',
      colorLight: '#ffffff',
      correctLevel: QRCode.CorrectLevel.H,
    });
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
    _emitToast('warning', _getLockReason());
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
        headers: _csrfHeaders({
          'Content-Type': 'application/json',
        }),
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
    toggleDesktopSidebar,
    openAnnouncementsPanel,
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
    loadMoreAnnouncements,
    refreshAnnouncements,
    // Module 10: Contact & Guide
    openAlertModal,
    closeAlertModal,
    requestAlertClear,
    closeAlertConfirmModal,
    confirmAlertClear,
    showContactModal,
    closeContactModal,
    // Module 11: Status Detail
    showStatusModal,
    closeStatusModal,
    openTicketModal,
    closeTicketModal,
    downloadTicketPass,
    dismissGuide,
    openOutcomeSpotlight,
    setOverviewIntelView,
    // Module 12: Support & Disputes
    selectSupportCategory,
    submitSupportRequest,
    loadMoreSupportTickets,
    // S27: WebSocket status
    isWsConnected: () => _ws && _ws.readyState === WebSocket.OPEN,
    refreshScheduleMatches,
    scheduleSelectDay,
    openMatchLobby,
    openRescheduleProposal,
    requestExpiredLobbyReschedule,
    closeRescheduleModal,
    respondReschedule,
    // Map viewer
    openMapViewer,
    closeMapViewer,
    retryAction: _runRetryAction,
    handleAvatarLoadError,
  };
})();

// Expose on window so csp-delegator can resolve "HubEngine.*" paths
window.HubEngine = HubEngine;
