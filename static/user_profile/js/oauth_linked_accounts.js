/*
 * Phase 9 Player Hub controller.
 * Drives connected roster, add-game cards, schema modal, and OTP disconnect flow.
 */

(function () {
    'use strict';

    const ROOT_ID = 'tab-passports';

    const DIRECT_CONNECT_ROUTES = {
        // valorant: RSO approval pending — manual entry only until production approval granted
        cs2:      '/profile/api/oauth/steam/login/?response_mode=json&callback_mode=redirect',
        dota2:    '/profile/api/oauth/steam/login/?response_mode=json&callback_mode=redirect',
        rocketleague: '/profile/api/oauth/epic/login/?response_mode=json&callback_mode=redirect'
    };

    const SLUG_ALIASES = {
        valorant: 'valorant',
        cs2: 'cs2',
        'counter-strike-2': 'cs2',
        counterstrike2: 'cs2',
        dota2: 'dota2',
        'dota-2': 'dota2',
        rocketleague: 'rocketleague',
        'rocket-league': 'rocketleague',
        efootball: 'efootball',
        'efootball-1773578027': 'efootball',
        pubgmobile: 'pubgm',
        'pubg-mobile': 'pubgm',
        pubgm: 'pubgm',
        'ea-fc': 'ea-fc',
        easportsfc26: 'ea-fc',
        fc26: 'ea-fc',
        eafc: 'ea-fc',
        codm: 'codm',
        mlbb: 'mlbb',
        freefire: 'freefire',
        r6siege: 'r6siege',
        'r6-siege': 'r6siege'
    };

    const FIELD_LABEL_OVERRIDES = {
        ign: 'In-Game Name',
        in_game_name: 'In-Game Name',
        game_id: 'Game ID',
        identity_key: 'Game ID',
        ea_id: 'EA ID',
        codm_uid: 'COD Mobile UID',
        user_id: 'User ID',
        player_id: 'Player ID',
        server_id: 'Server ID',
        konami_id: 'Konami ID'
    };

    const state = {
        initialized: false,
        initPromise: null,
        eventsBound: false,
        oauthReturnHandled: false,
        games: [],
        passports: [],
        selectedGame: null,
        modalMode: 'create',
        editingPassportId: null,
        otpPassport: null,
        resendSeconds: 0,
        resendTimerId: null
    };

    function rootEl() {
        return document.getElementById(ROOT_ID);
    }

    function byId(id) {
        return document.getElementById(id);
    }

    function normalize(value) {
        return String(value || '')
            .trim()
            .toLowerCase()
            .replace(/_/g, '-')
            .replace(/\s+/g, '')
            .replace(/[^a-z0-9-]/g, '');
    }

    function canonicalSlug(value) {
        const slug = normalize(value);
        return SLUG_ALIASES[slug] || slug;
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function getCsrfToken() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input && input.value) {
            return input.value;
        }

        const cookie = document.cookie
            .split(';')
            .map(function (part) {
                return part.trim();
            })
            .find(function (part) {
                return part.indexOf('csrftoken=') === 0;
            });

        return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
    }

    async function apiFetch(url, options) {
        const requestOptions = options || {};
        const method = (requestOptions.method || 'GET').toUpperCase();
        const headers = Object.assign({ Accept: 'application/json' }, requestOptions.headers || {});

        if (!headers['Content-Type'] && method !== 'GET') {
            headers['Content-Type'] = 'application/json';
        }

        const csrf = getCsrfToken();
        if (csrf && method !== 'GET') {
            headers['X-CSRFToken'] = csrf;
        }

        const response = await fetch(url, Object.assign({}, requestOptions, { headers: headers }));

        let payload = null;
        try {
            payload = await response.json();
        } catch (error) {
            payload = null;
        }

        if (!response.ok || (payload && payload.success === false)) {
            const err = new Error(
                (payload && (payload.message || payload.error || payload.error_code)) ||
                'Request failed.'
            );
            err.status = response.status;
            err.code = (payload && (payload.error_code || payload.error)) || 'REQUEST_FAILED';
            err.fieldErrors = (payload && (payload.field_errors || payload.fieldErrors)) || {};
            err.payload = payload;
            throw err;
        }

        return payload || {};
    }

    function showToast(message, type) {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type || 'info');
            return;
        }

        if (window.Toast && typeof window.Toast[type || 'info'] === 'function') {
            window.Toast[type || 'info'](message);
            return;
        }

        if (type === 'error') {
            console.error('[PlayerHub]', message);
            return;
        }

        console.log('[PlayerHub]', message);
    }

    function getProviderLabel(slug) {
        const canonical = canonicalSlug(slug);
        if (canonical === 'cs2' || canonical === 'dota2') return 'Steam';
        if (canonical === 'valorant') return 'Riot';
        if (canonical === 'rocketleague') return 'Epic';
        return 'Provider';
    }

    function ensureOAuthHandoffOverlay() {
        let overlay = byId('gp-oauth-handoff');
        if (overlay) return overlay;

        overlay = document.createElement('div');
        overlay.id = 'gp-oauth-handoff';
        overlay.className = 'gp-oauth-handoff hidden';
        overlay.innerHTML =
            '<div class="gp-oauth-handoff-card">' +
                '<div class="gp-oauth-handoff-ring"><i class="fa-solid fa-shield-halved"></i></div>' +
                '<h4 id="gp-oauth-handoff-title">Preparing secure sign-in</h4>' +
                '<p id="gp-oauth-handoff-subtitle">Connecting to your game provider...</p>' +
                '<div class="gp-oauth-handoff-loader"><span></span><span></span><span></span></div>' +
            '</div>';

        document.body.appendChild(overlay);
        return overlay;
    }

    function showOAuthHandoff(headline, subtitle) {
        const overlay = ensureOAuthHandoffOverlay();
        const title = byId('gp-oauth-handoff-title');
        const desc = byId('gp-oauth-handoff-subtitle');

        if (title) title.textContent = headline || 'Preparing secure sign-in';
        if (desc) desc.textContent = subtitle || 'Connecting to your game provider...';

        overlay.classList.remove('hidden');
        requestAnimationFrame(function () {
            overlay.classList.add('active');
        });
    }

    function hideOAuthHandoff() {
        const overlay = byId('gp-oauth-handoff');
        if (!overlay) return;

        overlay.classList.remove('active');
        setTimeout(function () {
            overlay.classList.add('hidden');
        }, 220);
    }

    function extractAuthorizationUrl(payload) {
        if (!payload) return '';
        if (typeof payload.authorization_url === 'string' && payload.authorization_url) {
            return payload.authorization_url;
        }
        if (payload.data && typeof payload.data.authorization_url === 'string' && payload.data.authorization_url) {
            return payload.data.authorization_url;
        }
        return '';
    }

    function setButtonLoading(button, isLoading, loadingText) {
        if (!button) return;

        if (isLoading) {
            if (!button.dataset.originalLabel) {
                button.dataset.originalLabel = button.innerHTML;
            }
            button.disabled = true;
            button.classList.add('opacity-70', 'cursor-wait');
            button.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> ' + escapeHtml(loadingText || 'Connecting...');
            return;
        }

        button.disabled = false;
        button.classList.remove('opacity-70', 'cursor-wait');
        if (button.dataset.originalLabel) {
            button.innerHTML = button.dataset.originalLabel;
            delete button.dataset.originalLabel;
        }
    }

    async function startDirectConnect(slug, route, button) {
        const providerLabel = getProviderLabel(slug);
        setButtonLoading(button, true, 'Connecting...');

        showOAuthHandoff(
            'Preparing ' + providerLabel + ' sign-in',
            'Securing handoff from Player Hub...'
        );

        try {
            const payload = await apiFetch(route);
            const authorizationUrl = extractAuthorizationUrl(payload);
            if (!authorizationUrl) {
                throw new Error('OAuth redirect URL was missing.');
            }

            showOAuthHandoff(
                'Opening ' + providerLabel,
                'Redirecting to secure authentication...'
            );

            window.location.href = authorizationUrl;
        } catch (error) {
            hideOAuthHandoff();
            setButtonLoading(button, false);
            showToast(error.message || ('Could not start ' + providerLabel + ' login.'), 'error');
        }
    }

    async function handleOAuthReturnState() {
        if (state.oauthReturnHandled) {
            return;
        }

        const params = new URLSearchParams(window.location.search || '');
        const provider = params.get('oauth_provider');
        const status = params.get('oauth_status');
        if (!provider || !status) {
            return;
        }

        state.oauthReturnHandled = true;

        const message = params.get('oauth_message') || '';
        const providerLabel = provider.charAt(0).toUpperCase() + provider.slice(1);
        if (status === 'connected' || status === 'success') {
            showOAuthHandoff(
                providerLabel + ' account linked',
                'Refreshing your Player Hub roster...'
            );

            await refreshData();
            setTimeout(function () {
                hideOAuthHandoff();
            }, 900);
            showToast(message || (providerLabel + ' account connected successfully.'), 'success');
        } else {
            hideOAuthHandoff();
            const errorCode = params.get('oauth_error');
            const fallback = providerLabel + ' sign-in failed.' + (errorCode ? ' (' + errorCode + ')' : '');
            showToast(message || fallback, 'error');
        }

        ['oauth_provider', 'oauth_status', 'oauth_game', 'oauth_message', 'oauth_error'].forEach(function (key) {
            params.delete(key);
        });
        const query = params.toString();
        const nextUrl = window.location.pathname + (query ? ('?' + query) : '') + window.location.hash;
        window.history.replaceState({}, document.title, nextUrl);
    }

    function extractGames(payload) {
        if (!payload) return [];
        if (Array.isArray(payload.data && payload.data.games)) return payload.data.games;
        if (Array.isArray(payload.games)) return payload.games;
        if (Array.isArray(payload.data)) return payload.data;
        if (Array.isArray(payload)) return payload;
        return [];
    }

    function extractPassports(payload) {
        if (!payload) return [];
        if (Array.isArray(payload.data && payload.data.passports)) return payload.data.passports;
        if (Array.isArray(payload.passports)) return payload.passports;
        if (Array.isArray(payload.data)) return payload.data;
        if (Array.isArray(payload)) return payload;
        return [];
    }

    function getPassportSlug(passport) {
        return canonicalSlug(
            passport && (
                (passport.game && passport.game.slug) ||
                passport.game_slug ||
                passport.game_display_name ||
                (passport.game && passport.game.name)
            )
        );
    }

    function findGameBySlug(slug) {
        const target = canonicalSlug(slug);
        return state.games.find(function (game) {
            return canonicalSlug(game.slug || game.name || game.display_name) === target;
        }) || null;
    }

    function getIdentityLabel(passport) {
        if (!passport) return '';
        if (passport.identity_key) return passport.identity_key;

        const ign = passport.ign || passport.in_game_name || '';
        const discr = passport.discriminator ? '#' + passport.discriminator : '';
        if (ign || discr) return ign + discr;

        const metadata = passport.metadata || {};
        const values = Object.keys(metadata).map(function (key) {
            return metadata[key];
        }).filter(Boolean);

        return values.length ? String(values[0]) : 'Linked';
    }

    function getPassportLockState(passport) {
        if (!passport) {
            return {
                kind: 'open',
                isDeleteBlocked: false,
                title: '',
                message: ''
            };
        }

        if (passport.verification_status === 'VERIFIED') {
            return {
                kind: 'verified',
                isDeleteBlocked: true,
                title: 'Verified account',
                message: 'Verified game links cannot be disconnected from this screen.'
            };
        }

        if (passport.cooldown && passport.cooldown.is_active) {
            const days = Number(passport.cooldown.days_remaining || 0);
            return {
                kind: 'cooldown',
                isDeleteBlocked: true,
                title: 'Disconnect locked',
                message: days > 0
                    ? 'This game is in cooldown for ' + days + ' more day(s).'
                    : 'This game is in cooldown right now.'
            };
        }

        if (passport.is_locked) {
            const daysLocked = Number(passport.days_locked || 0);
            return {
                kind: 'locked',
                isDeleteBlocked: true,
                title: 'Disconnect locked',
                message: daysLocked > 0
                    ? 'This game is locked for ' + daysLocked + ' more day(s).'
                    : 'This game is currently locked.'
            };
        }

        return {
            kind: 'open',
            isDeleteBlocked: false,
            title: '',
            message: ''
        };
    }

    function showDeletionBlockedMessage(title, message) {
        const text = (title ? title + ': ' : '') + (message || 'This game cannot be disconnected right now.');
        showToast(text, 'warning');
    }

    function hexToRgba(hex, alpha) {
        const clean = String(hex || '').replace('#', '').trim();
        if (!/^[a-fA-F0-9]{6}$/.test(clean)) {
            return 'rgba(0, 240, 255, ' + alpha + ')';
        }

        const r = parseInt(clean.slice(0, 2), 16);
        const g = parseInt(clean.slice(2, 4), 16);
        const b = parseInt(clean.slice(4, 6), 16);
        return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + alpha + ')';
    }

    function getGameDisplay(game, passport) {
        return (game && (game.display_name || game.name)) || passport.game_display_name || 'Game';
    }

    function getGameAccent(game) {
        return (game && game.primary_color) || '#00f0ff';
    }

    function getGameIconMarkup(game, fallbackText) {
        if (game && game.icon_url) {
            return '<img src="' + escapeHtml(game.icon_url) + '" alt="' + escapeHtml(fallbackText) + '" class="w-full h-full object-contain" />';
        }

        return '<span class="text-sm font-black text-white">' + escapeHtml(String(fallbackText).slice(0, 2).toUpperCase()) + '</span>';
    }

    function humanizeFieldKey(key) {
        return String(key || '')
            .replace(/_/g, ' ')
            .replace(/\s+/g, ' ')
            .trim()
            .replace(/\b\w/g, function (char) {
                return char.toUpperCase();
            })
            .replace(/\bId\b/g, 'ID')
            .replace(/\bIgn\b/g, 'IGN')
            .replace(/\bUid\b/g, 'UID');
    }

    function getSchemaLabelMap(game) {
        const map = {};
        const schema = Array.isArray(game && game.passport_schema) ? game.passport_schema : [];

        schema.forEach(function (field) {
            const key = String(field && field.key || '').trim();
            if (!key) return;

            const label = String(field && field.label || '').trim();
            if (label) {
                map[key] = label;
            }
        });

        return map;
    }

    function getFieldDisplayLabel(key, game, preferredLabel) {
        const cleanKey = String(key || '').trim();
        if (!cleanKey) return 'Field';

        const explicit = String(preferredLabel || '').trim();
        if (explicit) {
            return explicit;
        }

        const schemaLabels = getSchemaLabelMap(game);
        if (schemaLabels[cleanKey]) {
            return schemaLabels[cleanKey];
        }

        const override = FIELD_LABEL_OVERRIDES[cleanKey];
        if (override) {
            return override;
        }

        return humanizeFieldKey(cleanKey);
    }

    function isApiSyncedPassport(passport, game) {
        return !!(
            (game && game.api_synced) ||
            (passport && passport.api_synced) ||
            (passport && passport.game && passport.game.api_synced)
        );
    }

    function isLiveStatsSnapshot(value) {
        if (!value || typeof value !== 'object' || Array.isArray(value)) {
            return false;
        }

        return !!(
            value.recent_kd_ratio !== undefined ||
            value.recent_win_rate_pct !== undefined ||
            value.sample_size !== undefined ||
            value.most_played_role !== undefined ||
            value.synced_at !== undefined
        );
    }

    function asNumber(value) {
        if (value === null || value === undefined || value === '') return null;
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function asInt(value) {
        const parsed = asNumber(value);
        return parsed === null ? null : Math.round(parsed);
    }

    function formatAgoLabel(value) {
        if (!value) return 'Live feed';

        const ts = new Date(value);
        if (Number.isNaN(ts.getTime())) return 'Live feed';

        const deltaMs = Date.now() - ts.getTime();
        if (deltaMs < 0) return 'Just now';

        const minutes = Math.floor(deltaMs / 60000);
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return minutes + 'm ago';

        const hours = Math.floor(minutes / 60);
        if (hours < 24) return hours + 'h ago';

        const days = Math.floor(hours / 24);
        return days + 'd ago';
    }

    function getRoleVisual(role) {
        const normalized = String(role || '').trim().toLowerCase();
        const map = {
            duelist: { cls: 'duelist', icon: 'fa-crosshairs' },
            initiator: { cls: 'initiator', icon: 'fa-satellite-dish' },
            controller: { cls: 'controller', icon: 'fa-chess-rook' },
            sentinel: { cls: 'sentinel', icon: 'fa-shield-halved' },
            support: { cls: 'support', icon: 'fa-life-ring' },
            sniper: { cls: 'sniper', icon: 'fa-bullseye' },
            fragger: { cls: 'fragger', icon: 'fa-bolt' },
            roamer: { cls: 'roamer', icon: 'fa-compass' },
            jungler: { cls: 'jungler', icon: 'fa-tree' }
        };

        return map[normalized] || { cls: 'generic', icon: 'fa-user-astronaut' };
    }

    function getTrendMeta(kind, value) {
        const numeric = asNumber(value);
        if (numeric === null) {
            return {
                cls: 'neutral',
                icon: 'fa-wave-square',
                label: 'No trend',
            };
        }

        if (kind === 'kd') {
            if (numeric >= 1.3) {
                return { cls: 'up', icon: 'fa-arrow-trend-up', label: 'Rising' };
            }
            if (numeric < 0.9) {
                return { cls: 'down', icon: 'fa-arrow-trend-down', label: 'Recovery' };
            }
            return { cls: 'flat', icon: 'fa-arrow-right-long', label: 'Steady' };
        }

        if (numeric >= 58) {
            return { cls: 'up', icon: 'fa-arrow-trend-up', label: 'Hot streak' };
        }
        if (numeric < 46) {
            return { cls: 'down', icon: 'fa-arrow-trend-down', label: 'Climbing' };
        }
        return { cls: 'flat', icon: 'fa-arrow-right-long', label: 'Stable' };
    }

    function getLivePerformance(passport, game) {
        const metadata = passport && typeof passport.metadata === 'object' && passport.metadata ? passport.metadata : {};
        const payload = passport && typeof passport.live_performance === 'object' && passport.live_performance ? passport.live_performance : {};
        const map = metadata.live_stats && typeof metadata.live_stats === 'object' ? metadata.live_stats : {};
        const slug = canonicalSlug((game && (game.slug || game.name || game.display_name)) || getPassportSlug(passport));

        const aliasKeys = [slug, slug.replace(/-/g, ''), slug.replace(/-/g, '_')];
        let snapshot = null;
        aliasKeys.some(function (key) {
            const candidate = map[key];
            if (candidate && typeof candidate === 'object' && !Array.isArray(candidate)) {
                snapshot = candidate;
                return true;
            }
            return false;
        });

        if (!snapshot) {
            if (isLiveStatsSnapshot(map)) {
                snapshot = map;
            }
        }

        if (!snapshot) {
            Object.keys(map).some(function (key) {
                const candidate = map[key];
                if (candidate && typeof candidate === 'object' && !Array.isArray(candidate)) {
                    snapshot = candidate;
                    return true;
                }
                return false;
            });
        }

        const kdRatio = asNumber(payload.kd_ratio);
        const winRate = asNumber(payload.win_rate_pct);
        const matchesPlayed = asInt(payload.matches_played);

        const merged = {
            kdRatio: kdRatio !== null
                ? kdRatio
                : asNumber(snapshot && snapshot.recent_kd_ratio) !== null
                    ? asNumber(snapshot && snapshot.recent_kd_ratio)
                    : asNumber(passport && passport.kd_ratio),
            winRate: winRate !== null
                ? winRate
                : asNumber(snapshot && snapshot.recent_win_rate_pct) !== null
                    ? asNumber(snapshot && snapshot.recent_win_rate_pct)
                    : asNumber(passport && passport.win_rate),
            matchesPlayed: matchesPlayed !== null
                ? matchesPlayed
                : asInt(snapshot && snapshot.sample_size) !== null
                    ? asInt(snapshot && snapshot.sample_size)
                    : asInt(passport && passport.matches_played) || 0,
            mainRole: String(
                payload.main_role ||
                (snapshot && snapshot.most_played_role) ||
                (passport && passport.main_role) ||
                ''
            ).trim(),
            syncedAt: payload.synced_at || (snapshot && snapshot.synced_at) || metadata.riot_last_match_sync_at || '',
            hasStats: !!(
                payload.has_stats ||
                (snapshot && Object.keys(snapshot).length) ||
                kdRatio !== null ||
                winRate !== null ||
                (matchesPlayed || 0) > 0 ||
                String(payload.main_role || (snapshot && snapshot.most_played_role) || (passport && passport.main_role) || '').trim()
            ),
        };

        return merged;
    }

    function shouldRenderLivePerformance(passport, game) {
        if (isApiSyncedPassport(passport, game)) {
            return true;
        }

        const perf = getLivePerformance(passport, game);
        return !!perf.hasStats;
    }

    function renderLivePerformance(passport, game) {
        if (!shouldRenderLivePerformance(passport, game)) {
            return '';
        }

        const perf = getLivePerformance(passport, game);
        if (!perf.hasStats) {
            return (
                '<section class="gp-live-panel gp-live-syncing" aria-label="Live Performance Syncing">' +
                    '<div class="gp-live-head">' +
                        '<span class="gp-live-title"><i class="fa-solid fa-chart-line"></i> Live Performance</span>' +
                        '<span class="gp-live-sync-tag">Pending</span>' +
                    '</div>' +
                    '<div class="gp-live-syncing-body">' +
                        '<i class="fa-solid fa-arrows-rotate fa-spin"></i>' +
                        '<div>' +
                            '<p class="gp-live-syncing-copy gp-live-syncing-pulse">Fetching live stats...</p>' +
                            '<p class="gp-live-syncing-sub">K/D, win rate, and role projection will appear after the next sync cycle.</p>' +
                        '</div>' +
                    '</div>' +
                '</section>'
            );
        }

        const kdTrend = getTrendMeta('kd', perf.kdRatio);
        const wrTrend = getTrendMeta('wr', perf.winRate);
        const winPct = Math.max(0, Math.min(100, perf.winRate || 0));
        const roleName = perf.mainRole || 'Unassigned';
        const roleVisual = getRoleVisual(roleName);
        const kdText = perf.kdRatio !== null ? perf.kdRatio.toFixed(2) : '--';
        const wrText = perf.winRate !== null ? perf.winRate.toFixed(1) + '%' : '--';
        const syncedLabel = formatAgoLabel(perf.syncedAt);

        return (
            '<section class="gp-live-panel" aria-label="Live Performance Metrics">' +
                '<div class="gp-live-head">' +
                    '<span class="gp-live-title"><i class="fa-solid fa-chart-line"></i> Live Performance</span>' +
                    '<span class="gp-live-sync-tag">Synced ' + escapeHtml(syncedLabel) + '</span>' +
                '</div>' +
                '<div class="gp-live-grid">' +
                    '<div class="gp-live-metric">' +
                        '<span class="gp-live-label">K/D Ratio</span>' +
                        '<span class="gp-live-value">' + escapeHtml(kdText) + '</span>' +
                        '<span class="gp-live-trend gp-live-trend-' + kdTrend.cls + '"><i class="fa-solid ' + kdTrend.icon + '"></i>' + escapeHtml(kdTrend.label) + '</span>' +
                    '</div>' +
                    '<div class="gp-live-metric gp-live-metric-ring">' +
                        '<div class="gp-win-ring" style="--gp-win-rate:' + winPct + ';"><span>' + escapeHtml(wrText) + '</span></div>' +
                        '<span class="gp-live-label">Win Rate</span>' +
                        '<span class="gp-live-trend gp-live-trend-' + wrTrend.cls + '"><i class="fa-solid ' + wrTrend.icon + '"></i>' + escapeHtml(wrTrend.label) + '</span>' +
                    '</div>' +
                    '<div class="gp-live-metric">' +
                        '<span class="gp-live-label">Matches</span>' +
                        '<span class="gp-live-value">' + escapeHtml(String(perf.matchesPlayed || 0)) + '</span>' +
                        '<span class="gp-live-subtle">Recent sample</span>' +
                    '</div>' +
                    '<div class="gp-live-metric">' +
                        '<span class="gp-live-label">Main Role</span>' +
                        '<span class="gp-role-chip gp-role-' + roleVisual.cls + '"><i class="fa-solid ' + roleVisual.icon + '"></i>' + escapeHtml(roleName) + '</span>' +
                    '</div>' +
                '</div>' +
            '</section>'
        );
    }

    // Traverse a dot-notation path (e.g. "provider_data.steam.persona_name") on a passport object.
    function getFieldValueFromPath(passport, valuePath) {
        if (!valuePath || !passport) return '';
        var parts = String(valuePath).split('.');
        var obj = passport;
        for (var i = 0; i < parts.length; i++) {
            if (obj == null || typeof obj !== 'object') return '';
            obj = obj[parts[i]];
        }
        return (obj == null || obj === '') ? '' : String(obj);
    }

    function getPassportFieldValue(passport, key) {
        const metadata = passport && passport.metadata || {};
        const cleanKey = String(key || '').trim();
        const directValue = metadata[cleanKey];

        if (directValue != null && String(directValue).trim()) {
            return String(directValue);
        }

        if (cleanKey === 'ign' || cleanKey === 'in_game_name') {
            return String(passport && (passport.ign || passport.in_game_name) || '');
        }

        if (cleanKey === 'discriminator') {
            return String(passport && passport.discriminator || '');
        }

        if (cleanKey === 'region') {
            return String(passport && passport.region || '');
        }

        if (cleanKey === 'rank') {
            return String(passport && passport.rank_name || '');
        }

        if (cleanKey === 'game_id') {
            return String(passport && passport.identity_key || '');
        }

        return '';
    }

    var COLLECT_META_SKIP = {
        identity_key: true, live_stats: true, api_synced: true,
        oauth_provider: true, riot_last_match_sync_at: true,
        steamid: true, steam_id: true, avatar: true, avatar_medium: true,
        avatar_full: true, profile_url: true, synced_at: true,
        avatar_url: true, image_url: true, thumbnail_url: true, photo_url: true
    };

    function looksLikeUrl(val) {
        return /^https?:\/\//i.test(String(val || ''));
    }

    function collectMetaTags(passport, game) {
        // Prefer field_schema from the passport (populated by GameProfileSerializer)
        var fieldSchema = Array.isArray(passport && passport.field_schema) ? passport.field_schema : [];
        if (fieldSchema.length) {
            var schemaTags = [];
            for (var si = 0; si < fieldSchema.length; si++) {
                var sf = fieldSchema[si];
                // Normalise key across both schema formats
                var sfKey = String(sf.key || sf.field_name || '').trim();
                if (!sfKey || COLLECT_META_SKIP[sfKey]) continue;
                var sfVal = sf.value_path
                    ? getFieldValueFromPath(passport, sf.value_path)
                    : getPassportFieldValue(passport, sfKey);
                if (!sfVal) continue;
                // Skip raw URL values ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â images/links surface in dedicated UI slots, not chips
                if (looksLikeUrl(sfVal)) continue;
                schemaTags.push({
                    key: sfKey,
                    label: sf.display_name || sf.label || getFieldDisplayLabel(sfKey, game),
                    value: sfVal,
                    fieldClass: String(sf.field_class || '')
                });
                if (schemaTags.length >= 4) break;
            }
            if (schemaTags.length) return schemaTags;
        }

        // Fallback: scan metadata dict
        var metadata = passport.metadata || {};
        var tags = [];
        Object.keys(metadata).forEach(function (key) {
            if (COLLECT_META_SKIP[key]) return;
            var value = metadata[key];
            if (value === null || value === undefined || value === '') return;
            if (typeof value === 'object') return;
            // Skip raw URL values ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â images/links surface in dedicated UI slots, not chips
            if (looksLikeUrl(value)) return;
            tags.push({ key: key, label: getFieldDisplayLabel(key, game), value: value });
        });

        if (!tags.length && passport.region) {
            tags.push({ key: 'region', label: getFieldDisplayLabel('region', game), value: passport.region });
        }
        if (!tags.length && passport.main_role) {
            tags.push({ key: 'role', label: getFieldDisplayLabel('role', game), value: passport.main_role });
        }
        if (!tags.length && game && game.display_name) {
            tags.push({ key: 'status', label: getFieldDisplayLabel('status', game), value: 'Ready' });
        }
        return tags.slice(0, 4);
    }
    function renderSkeletons(count) {
        const container = document.getElementById('activeRosterGrid');
        if (!container) return;
        count = count || 3;
        var skeletonHTML = '';
        for (var i = 0; i < count; i++) {
            skeletonHTML +=
                '<div class="liquid-glass rounded-[2rem] p-1 animate-pulse overflow-hidden w-full">' +
                    '<div class="bg-[#0A0F1A] rounded-[30px] h-full w-full p-5 flex flex-col min-h-[300px]">' +
                        '<div class="flex items-start gap-3 mb-4">' +
                            '<div class="w-14 h-14 rounded-2xl bg-white/5 shrink-0"></div>' +
                            '<div class="flex flex-col gap-2 flex-1 min-w-0 pt-1">' +
                                '<div class="h-2 bg-white/5 rounded-full w-1/3"></div>' +
                                '<div class="h-4 bg-white/8 rounded-full w-2/3"></div>' +
                                '<div class="flex gap-1.5 mt-1">' +
                                    '<div class="h-4 bg-white/5 rounded-md w-20"></div>' +
                                    '<div class="h-4 bg-white/5 rounded-md w-16"></div>' +
                                '</div>' +
                            '</div>' +
                            '<div class="flex flex-col gap-1.5 shrink-0">' +
                                '<div class="h-7 bg-white/5 rounded-xl w-20"></div>' +
                                '<div class="h-7 bg-white/5 rounded-xl w-20"></div>' +
                            '</div>' +
                        '</div>' +
                        '<div class="grid grid-cols-2 gap-2 mt-3">' +
                            '<div class="h-14 bg-white/5 rounded-xl"></div>' +
                            '<div class="h-14 bg-white/5 rounded-xl"></div>' +
                            '<div class="h-14 bg-white/5 rounded-xl"></div>' +
                            '<div class="h-14 bg-white/5 rounded-xl"></div>' +
                        '</div>' +
                        '<div class="mt-auto pt-3 border-t border-white/5 flex justify-between">' +
                            '<div class="h-4 bg-white/5 rounded-full w-16"></div>' +
                            '<div class="h-4 bg-white/5 rounded-full w-24"></div>' +
                        '</div>' +
                    '</div>' +
                '</div>';
        }
        container.innerHTML = skeletonHTML;
    }

    function renderConnectedGames() {
        const container = document.getElementById('activeRosterGrid');
        const empty = byId('gp-connected-empty');
        const counter = byId('gp-roster-count');
        if (!container) return;

        if (!state.passports.length) {
            container.innerHTML =
                '<div class="border border-dashed border-white/20 bg-white/[0.02] backdrop-blur-md p-10 text-center rounded-[2rem] col-span-full flex flex-col items-center gap-4">' +
                    '<i class="fa-solid fa-ghost text-5xl text-teal-500/50"></i>' +
                    '<div>' +
                        '<h3 class="text-xl font-black text-white mb-1">Your Roster is Empty</h3>' +
                        '<p class="text-sm text-slate-400 max-w-sm mx-auto">Link your first game from the <span class="text-teal-400 font-bold">Game Library</span> below to build your competitive identity.</p>' +
                    '</div>' +
                    '<div class="flex items-center gap-2 text-xs text-slate-500 animate-bounce mt-1">' +
                        '<i class="fa-solid fa-arrow-down"></i>' +
                        '<span class="font-bold uppercase tracking-widest">Scroll to Game Library</span>' +
                        '<i class="fa-solid fa-arrow-down"></i>' +
                    '</div>' +
                '</div>';
            if (empty) empty.classList.add('hidden');
            if (counter) counter.textContent = '0';
            return;
        }

        if (empty) empty.classList.add('hidden');
        if (counter) counter.textContent = String(state.passports.length);

        container.innerHTML = '';

        state.passports.forEach(function (passport, index) {
            var game = findGameBySlug(getPassportSlug(passport));
            var title = getGameDisplay(game, passport);
            var identity = getIdentityLabel(passport);
            var lockState = getPassportLockState(passport);
            var accent = getGameAccent(game);
            var icon = getGameIconMarkup(game, title);
            var tags = collectMetaTags(passport, game);
            var gameSlug = getPassportSlug(passport);
            var isLocked = lockState.isDeleteBlocked;

            var providerData = (passport.provider_data && typeof passport.provider_data === 'object')
                ? passport.provider_data : {};

            // Resolve Avatar
            var avatarUrl = '';
            if (providerData.steam && providerData.steam.avatar_full) avatarUrl = providerData.steam.avatar_full;
            else if (providerData.steam && providerData.steam.avatar_medium) avatarUrl = providerData.steam.avatar_medium;
            else if (providerData.riot && providerData.riot.profile_icon_url) avatarUrl = providerData.riot.profile_icon_url;

            var avatarHTML = avatarUrl
                ? '<img src="' + escapeHtml(avatarUrl) + '" class="w-full h-full object-cover" alt="Avatar">'
                : '<span class="text-2xl font-black text-white">' + icon + '</span>';

            // Background
            var bgImage = (game && game.icon_url)
                ? '<img src="' + escapeHtml(game.icon_url) + '" class="absolute inset-0 w-full h-full object-cover opacity-10 mix-blend-luminosity blur-[2px] pointer-events-none z-0" alt="BG">'
                : '';

            // Badges
            var isApiSynced = isApiSyncedPassport(passport, game)
                || !!(providerData.steam && providerData.steam.persona_name)
                || !!(providerData.riot && providerData.riot.puuid)
                || shouldRenderLivePerformance(passport, game);
            var vstatus = String(passport.verification_status || '').toUpperCase();
            var badgeHTML = (vstatus === 'FLAGGED')
                ? '<span class="bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-md text-[10px] font-bold text-red-400 flex items-center gap-1"><i class="fa-solid fa-triangle-exclamation"></i> FLAGGED</span>'
                : ((vstatus === 'VERIFIED' || isApiSynced)
                    ? '<span class="bg-white/10 border border-white/5 px-2 py-0.5 rounded-md text-[10px] font-bold text-slate-300 flex items-center gap-1"><i class="fa-solid fa-shield-check"></i> VERIFIED</span>'
                    : '<span class="bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-md text-[10px] font-bold text-amber-400 flex items-center gap-1"><i class="fa-solid fa-clock"></i> PENDING</span>');

            var typeBadgeHTML = isApiSynced
                ? '<span class="liquid-glass px-2 py-0.5 rounded-md text-[10px] font-bold text-teal-400 flex items-center gap-1 whitespace-nowrap"><i class="fa-solid fa-cloud-arrow-down"></i> API SYNCED</span>'
                : '<span class="bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-md text-[10px] font-bold text-amber-400 flex items-center gap-1 whitespace-nowrap"><i class="fa-solid fa-keyboard"></i> MANUAL ENTRY</span>';

            // Privacy footer
            var visibilityVal = String(passport.visibility || 'PUBLIC').toUpperCase();
            var isPublic = visibilityVal === 'PUBLIC';
            var privacyIcon = isPublic ? '<i class="fa-solid fa-eye text-teal-500"></i>' : '<i class="fa-solid fa-eye-slash text-slate-500"></i>';
            var privacyText = isPublic ? '<span class="text-slate-300">Public</span>' : '<span class="text-slate-500">Private</span>';

            // Data chips from collectMetaTags
            var dataChipsHTML = '';
            if (tags && tags.length) {
                tags.slice(0, 4).forEach(function (entry) {
                    dataChipsHTML +=
                        '<div class="bg-black/40 border border-white/5 rounded-xl p-3 backdrop-blur-md overflow-hidden">' +
                            '<p class="text-[9px] text-slate-500 font-black uppercase tracking-widest mb-1 truncate">' + escapeHtml(entry.label || entry.key) + '</p>' +
                            '<p class="text-sm font-medium text-slate-200 truncate">' + escapeHtml(String(entry.value || '--')) + '</p>' +
                        '</div>';
                });
            } else {
                dataChipsHTML = '<div class="col-span-2 text-slate-500 text-xs italic p-2">No identity data configured.</div>';
            }

            var ign = escapeHtml(identity) || 'Configure ID';

            // Edit button — uses data-action delegation (openIdModal lives in closure)
            var editBtnHtml = !isLocked
                ? '<button type="button" data-action="edit" data-passport-id="' + String(passport.id) + '" class="liquid-glass px-3 py-1.5 rounded-xl text-xs font-bold text-white hover:bg-white/10 transition flex items-center gap-1.5 whitespace-nowrap"><i class="fa-solid fa-pen"></i> EDIT ID</button>'
                : '';

            var lockFooterHtml = isLocked
                ? '<span class="text-xs font-black text-amber-500 tracking-wide uppercase"><i class="fa-solid fa-lock mr-1"></i> Identity Locked</span>'
                : '<span class="text-xs font-black text-green-400 tracking-wide uppercase"><i class="fa-solid fa-check mr-1"></i> Roster Ready</span>';

            var gameLabel = escapeHtml(String(game && game.display_name || title || gameSlug));

            var div = document.createElement('div');
            div.id = 'card-' + passport.id;
            div.className = 'liquid-glass rounded-[2rem] p-1 accent-' + gameSlug + ' transition-all duration-300 relative group overflow-hidden w-full';
            div.style.cssText = '--game-color:' + accent + ';animation-delay:' + (index * 80) + 'ms;';
            div.innerHTML =
                '<div class="bg-[#0A0F1A] rounded-[30px] h-full w-full p-5 relative z-10 overflow-hidden game-glow flex flex-col min-h-[300px]">' +
                    bgImage +
                    '<div class="relative z-20 flex flex-col flex-1 min-h-0">' +
                        '<div class="flex justify-between items-start w-full mb-4 gap-3">' +
                            '<div class="flex items-center gap-3 flex-1 min-w-0">' +
                                '<div class="w-14 h-14 rounded-2xl overflow-hidden border border-white/20 shadow-2xl bg-slate-800 flex items-center justify-center shrink-0">' +
                                    avatarHTML +
                                '</div>' +
                                '<div class="flex flex-col flex-1 min-w-0">' +
                                    '<span class="text-[10px] font-black text-white/50 tracking-widest uppercase truncate mb-0.5">' + gameLabel + '</span>' +
                                    '<h3 class="text-xl font-black text-white leading-tight truncate" title="' + ign + '">' + ign + '</h3>' +
                                    '<div class="flex flex-wrap gap-1.5 mt-1">' +
                                        typeBadgeHTML +
                                        badgeHTML +
                                    '</div>' +
                                '</div>' +
                            '</div>' +
                            '<div class="flex flex-col gap-1.5 shrink-0 items-end">' +
                                editBtnHtml +
                                '<button type="button" data-action="disconnect" data-passport-id="' + String(passport.id) + '" class="bg-red-500/10 border border-red-500/20 px-3 py-1.5 rounded-xl text-xs font-bold text-red-400 hover:bg-red-500/20 transition flex items-center gap-1.5 whitespace-nowrap"' + (isLocked ? ' disabled' : '') + '><i class="fa-solid fa-link-slash"></i> UNLINK</button>' +
                            '</div>' +
                        '</div>' +
                        '<div class="grid grid-cols-2 gap-2 mt-3 w-full">' +
                            dataChipsHTML +
                        '</div>' +
                        '<div class="mt-auto pt-3 border-t border-white/5 flex justify-between items-center w-full">' +
                            '<button type="button" data-action="toggle-privacy" data-passport-id="' + String(passport.id) + '" data-game-slug="' + escapeHtml(gameSlug) + '" data-current="' + visibilityVal + '" class="flex items-center gap-2 text-xs font-bold hover:opacity-80 transition">' +
                                privacyIcon + ' ' + privacyText +
                            '</button>' +
                            lockFooterHtml +
                        '</div>' +
                    '</div>' +
                '</div>';

            container.appendChild(div);
        });
    }
    function renderAddGames() {
        const grid = byId('gp-add-grid');
        if (!grid) return;

        const linkedSlugs = new Set(state.passports.map(function (passport) {
            return getPassportSlug(passport);
        }));

        const availableGames = state.games.filter(function (game) {
            return !linkedSlugs.has(canonicalSlug(game.slug || game.name || game.display_name));
        });

        if (!availableGames.length) {
            grid.innerHTML = (
                '<div class="col-span-full liquid-glass rounded-2xl p-10 text-center">' +
                    '<div class="w-14 h-14 mx-auto mb-4 rounded-2xl border border-white/10 bg-white/5 flex items-center justify-center">' +
                        '<i class="fa-solid fa-trophy text-xl text-teal-400/70"></i>' +
                    '</div>' +
                    '<h4 class="text-white font-black text-base">All games connected</h4>' +
                    '<p class="text-slate-500 text-xs mt-1">Your roster is ready for team play and tournaments.</p>' +
                '</div>'
            );
            return;
        }

        grid.innerHTML = availableGames.map(function (game) {
            const slug = canonicalSlug(game.slug || game.name || game.display_name);
            const title = game.display_name || game.name || slug;
            const accent = getGameAccent(game);
            const icon = getGameIconMarkup(game, title);
            const isDirect = !!DIRECT_CONNECT_ROUTES[slug];

            // Type badge: AUTO-SYNC vs MANUAL
            var typeBadge = isDirect
                ? '<span class="bg-white/5 border border-white/10 px-2 py-1 rounded text-[9px] font-bold text-slate-400 flex items-center gap-1">' +
                      '<i class="fa-solid fa-bolt text-teal-400"></i> AUTO-SYNC' +
                  '</span>'
                : '<span class="bg-white/5 border border-white/10 px-2 py-1 rounded text-[9px] font-bold text-slate-400 flex items-center gap-1">' +
                      '<i class="fa-solid fa-keyboard text-amber-500"></i> MANUAL' +
                  '</span>';

            // Connect button label
            var connectLabel = isDirect ? 'CONNECT' : 'ADD ID MANUALLY';
            var accentHex = escapeHtml(accent);

            return (
                '<div class="liquid-glass-hover liquid-glass rounded-2xl p-5 flex flex-col justify-between cursor-pointer group gp-add-card">' +
                    '<div class="flex justify-between items-start mb-4">' +
                        '<div class="w-14 h-14 rounded-xl border border-white/10 bg-black/30 flex items-center justify-center group-hover:scale-110 transition-transform duration-500 text-xl" style="color:' + accentHex + ';">' +
                            icon +
                        '</div>' +
                        typeBadge +
                    '</div>' +
                    '<div>' +
                        '<h4 class="text-lg font-black text-white mb-1">' + escapeHtml(title) + '</h4>' +
                        '<p class="text-xs text-slate-500 mb-4">' +
                            (isDirect ? 'Secure OAuth provider connect.' : 'Enter your in-game player ID fields.') +
                        '</p>' +
                        '<button type="button" data-action="add-game" data-game-slug="' + escapeHtml(slug) + '" ' +
                            'class="w-full py-2.5 px-4 rounded-xl bg-white/5 border border-white/10 text-sm font-bold text-white text-center hover:bg-white/10 transition-all duration-300">' +
                            connectLabel +
                        '</button>' +
                    '</div>' +
                '</div>'
            );
        }).join('');
    }
    function syncBodyModalLock() {
        const idModal = byId('gp-id-modal');
        const disModal = byId('gp-disconnect-modal');
        const idOpen = !!(idModal && !idModal.classList.contains('hidden'));
        const disOpen = !!(disModal && !disModal.classList.contains('hidden'));

        document.body.classList.toggle('gp-modal-open', idOpen || disOpen);
    }

    function promoteModalsToBody() {
        ['gp-id-modal', 'gp-disconnect-modal'].forEach(function (modalId) {
            const modal = byId(modalId);
            if (!modal || !document.body || modal.parentElement === document.body) {
                return;
            }

            document.body.appendChild(modal);
        });
    }

    function renderPlayerHub() {
        renderConnectedGames();
        renderAddGames();

        window.dispatchEvent(new CustomEvent('game-passports:data-updated', {
            detail: { passports: state.passports }
        }));
    }

    function showFormError(message) {
        const el = byId('gp-id-error');
        if (!el) return;
        el.textContent = message || 'Unable to save passport right now.';
        el.classList.remove('hidden');
    }

    function hideFormError() {
        const el = byId('gp-id-error');
        if (!el) return;
        el.textContent = '';
        el.classList.add('hidden');
    }

    function getFieldOptions(field) {
        if (!Array.isArray(field.options)) return [];
        return field.options.map(function (option) {
            if (typeof option === 'string') {
                return { value: option, label: option };
            }

            return {
                value: option && option.value != null ? String(option.value) : '',
                label: option && option.label != null ? String(option.label) : String(option && option.value != null ? option.value : '')
            };
        });
    }

    // Render one field from a passport_schema or field_schema entry.
    // currentPassport is required for locked field classes (VERIFIED_IDENTITY, API_SYNCED).
    function renderSchemaField(field, currentPassport) {
        var key = String(field.key || 'field');
        var label = getFieldDisplayLabel(key, state.selectedGame, field.label);
        var type = String(field.type || 'text').toLowerCase();
        var required = !!field.required;
        var fieldClass = String(field.field_class || '').toUpperCase();
        var isLocked = fieldClass === 'VERIFIED_IDENTITY' || fieldClass === 'API_SYNCED';

        // ΓöÇΓöÇ Locked field: render as read-only display panel ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        if (isLocked) {
            var rawValue = '';
            if (currentPassport) {
                rawValue = field.value_path
                    ? getFieldValueFromPath(currentPassport, field.value_path)
                    : getPassportFieldValue(currentPassport, key);
            }
            var lockIcon = fieldClass === 'VERIFIED_IDENTITY'
                ? '<i class="fa-solid fa-lock text-amber-400 text-[10px]"></i>'
                : '<i class="fa-solid fa-cloud text-z-cyan text-[10px]"></i>';
            var panelCls = fieldClass === 'VERIFIED_IDENTITY'
                ? 'border-amber-500/25 bg-amber-500/8 text-amber-100/80'
                : 'border-z-cyan/20 bg-z-cyan/5 text-z-cyan/80';
            return (
                '<div class="mb-4">' +
                    '<div class="flex items-center gap-1.5 mb-1.5 ml-1">' +
                        lockIcon +
                        '<label class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">' +
                            escapeHtml(label) +
                        '</label>' +
                    '</div>' +
                    '<div class="w-full rounded-lg border ' + panelCls + ' px-4 py-2.5 text-sm font-mono select-all cursor-default">' +
                        (rawValue
                            ? escapeHtml(rawValue)
                            : '<span class="text-gray-500 italic text-xs">Not synced yet</span>') +
                    '</div>' +
                '</div>'
            );
        }

        var minLength = field.min_length ? Number(field.min_length) : 0;
        var maxLength = field.max_length ? Number(field.max_length) : 0;

        var baseLabel =
            '<label class="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5 ml-1" for="gp-field-' + escapeHtml(key) + '">' +
                escapeHtml(label) + (required ? ' <span class="text-red-400">*</span>' : '') +
            '</label>';

        var helpText = field.help_text
            ? '<p class="text-[11px] text-gray-500 mt-1">' + escapeHtml(field.help_text) + '</p>'
            : '';

        if (type === 'select') {
            var optionsMarkup = getFieldOptions(field).map(function (option) {
                return '<option value="' + escapeHtml(option.value) + '">' + escapeHtml(option.label) + '</option>';
            }).join('');

            return (
                '<div class="mb-4 relative">' +
                    baseLabel +
                    '<select id="gp-field-' + escapeHtml(key) + '" data-id-field="' + escapeHtml(key) + '" class="w-full bg-gray-900/60 border border-slate-600/50 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition appearance-none cursor-pointer"' + (required ? ' required' : '') + '>' +
                        '<option value="">Select ' + escapeHtml(label) + '</option>' +
                        optionsMarkup +
                    '</select>' +
                    '<div class="absolute right-4 top-[42px] pointer-events-none text-gray-500"><i class="fa-solid fa-chevron-down text-xs"></i></div>' +
                    helpText +
                '</div>'
            );
        }

        return (
            '<div class="mb-4 relative">' +
                baseLabel +
                '<input id="gp-field-' + escapeHtml(key) + '" data-id-field="' + escapeHtml(key) + '" type="text" class="w-full bg-gray-900/60 border border-slate-600/50 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition" autocomplete="off"' +
                    (field.placeholder ? ' placeholder="' + escapeHtml(String(field.placeholder)) + '"' : '') +
                    (required ? ' required' : '') +
                    (minLength ? ' minlength="' + String(minLength) + '"' : '') +
                    (maxLength ? ' maxlength="' + String(maxLength) + '"' : '') +
                ' />' +
                helpText +
            '</div>'
        );
    }

    function setIdModalVisible(open) {
        const modal = byId('gp-id-modal');
        const shell = byId('gp-id-modal-shell');
        if (!modal || !shell) return;

        if (open) {
            modal.classList.remove('hidden');
            modal.setAttribute('aria-hidden', 'false');
            setTimeout(function () {
                modal.classList.remove('opacity-0');
                shell.classList.remove('scale-95');
                syncBodyModalLock();
            }, 10);
            return;
        }

        modal.classList.add('opacity-0');
        shell.classList.add('scale-95');
        modal.setAttribute('aria-hidden', 'true');
        setTimeout(function () {
            modal.classList.add('hidden');
            syncBodyModalLock();
        }, 300);
    }

    function openIdModal(slug, options) {
        const modalOptions = options || {};
        const game = findGameBySlug(slug);
        if (!game) {
            showToast('This game is not available right now.', 'error');
            return;
        }

        const editingPassport = modalOptions.passport || null;
        const isEditMode = !!editingPassport;

        state.selectedGame = game;
        state.modalMode = isEditMode ? 'edit' : 'create';
        state.editingPassportId = isEditMode ? Number(editingPassport.id) : null;
        hideFormError();

        const iconEl = byId('gp-id-modal-icon');
        const titleEl = byId('gp-id-modal-title');
        const subtitleEl = byId('gp-id-modal-subtitle');
        var fieldsEl = byId('gp-id-fields');
        var saveBtn = byId('gp-id-save');

        var title = game.display_name || game.name || 'Game';
        var accent = getGameAccent(game);

        if (iconEl) {
            iconEl.style.backgroundColor = hexToRgba(accent, 0.2);
            iconEl.style.borderColor = hexToRgba(accent, 0.5);
            iconEl.style.color = accent;
            iconEl.innerHTML = game.icon_url
                ? '<img src="' + escapeHtml(game.icon_url) + '" alt="' + escapeHtml(title) + '" class="w-6 h-6 object-contain" />'
                : escapeHtml(String(title).slice(0, 2).toUpperCase());
        }

        if (titleEl) titleEl.textContent = isEditMode ? ('Edit ' + title + ' Details') : ('Set ID for ' + title);
        if (subtitleEl) subtitleEl.textContent = isEditMode
            ? 'Update your player details and keep your roster current.'
            : 'Enter your player details to finish linking this game.';

        if (saveBtn) {
            saveBtn.innerHTML = isEditMode
                ? '<i class="fa-solid fa-pen-to-square"></i> Update Passport'
                : '<i class="fa-solid fa-shield-check"></i> Save Passport';
        }

        // Use field_schema from passport (dynamic) if available in edit mode, else fall back.
        var fieldSchema = isEditMode && Array.isArray(editingPassport && editingPassport.field_schema)
            ? editingPassport.field_schema
            : null;
        var schema = fieldSchema || (Array.isArray(game.passport_schema) ? game.passport_schema : []);
        var passportForSchema = isEditMode ? editingPassport : null;

        if (fieldsEl) {
            if (!schema.length) {
                fieldsEl.innerHTML = '<div class="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">This game has no profile fields configured right now.</div>';
            } else {
                fieldsEl.innerHTML = schema.map(function (field) {
                    return renderSchemaField(field, passportForSchema);
                }).join('');
            }
        }

        // Pre-fill only USER_EDITABLE / PREFERENCE fields (locked fields render inline)
        if (isEditMode && schema.length) {
            schema.forEach(function (field) {
                var fc = String(field.field_class || '').toUpperCase();
                if (fc === 'VERIFIED_IDENTITY' || fc === 'API_SYNCED') return;

                // Normalise key across both schema formats
                var key = String(field.key || field.field_name || '').trim();
                if (!key) return;

                var input = document.querySelector('[data-id-field="' + key + '"]');
                if (!input) return;

                var rawValue = getPassportFieldValue(editingPassport, key);
                var value = String(rawValue || '').trim();
                if (!value) return;

                if (String(input.tagName || '').toLowerCase() === 'select') {
                    var hasOption = Array.from(input.options || []).some(function (opt) {
                        return String(opt.value) === value;
                    });
                    if (hasOption) { input.value = value; }
                    return;
                }

                input.value = value;
            });
        }

        setIdModalVisible(true);
    }

    function closeIdModal() {
        setIdModalVisible(false);
        hideFormError();
        state.selectedGame = null;
        state.modalMode = 'create';
        state.editingPassportId = null;
    }

    function validateField(field, value) {
        const text = String(value == null ? '' : value).trim();
        const fieldKey = field.key || field.field_name || '';
        const fieldLabel = getFieldDisplayLabel(fieldKey, state.selectedGame, field.display_name || field.label);

        if (field.required && !text) {
            return fieldLabel + ' is required.';
        }

        if (field.min_length && text && text.length < Number(field.min_length)) {
            return fieldLabel + ' must be at least ' + Number(field.min_length) + ' characters.';
        }

        if (field.max_length && text.length > Number(field.max_length)) {
            return fieldLabel + ' must be at most ' + Number(field.max_length) + ' characters.';
        }

        if (field.validation_regex && text) {
            try {
                const regex = new RegExp(field.validation_regex);
                if (!regex.test(text)) {
                    return field.validation_error_message || fieldLabel + ' format is invalid.';
                }
            } catch (error) {
                console.warn('[PlayerHub] Invalid regex for field', field.key);
            }
        }

        return '';
    }

    function collectMetadataFromForm() {
        var game = state.selectedGame;
        var result = { metadata: {}, errors: [] };

        if (!game) {
            result.errors.push('No game selected.');
            return result;
        }

        // Use field_schema from the passport being edited if available
        var editingPassport = state.modalMode === 'edit' && state.editingPassportId
            ? state.passports.find(function (p) { return Number(p.id) === Number(state.editingPassportId); })
            : null;
        var fieldSchema = editingPassport && Array.isArray(editingPassport.field_schema)
            ? editingPassport.field_schema
            : null;
        var schema = fieldSchema || (Array.isArray(game.passport_schema) ? game.passport_schema : []);

        schema.forEach(function (field) {
            // Skip locked fields ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â they are not submitted in the form
            var fc = String(field.field_class || '').toUpperCase();
            if (!fc) fc = (field.immutable || field.locked) ? 'VERIFIED_IDENTITY' : 'USER_EDITABLE';
            if (fc === 'VERIFIED_IDENTITY' || fc === 'API_SYNCED') return;

            // Normalise key across both schema formats
            var fieldKey = String(field.key || field.field_name || '').trim();
            var input = document.querySelector('[data-id-field="' + fieldKey + '"]');
            if (!input) return;

            var value = String(input.value || '').trim();
            var validationError = validateField(field, value);

            if (validationError) {
                result.errors.push(validationError);
                return;
            }

            result.metadata[fieldKey] = value;
        });

        return result;
    }

    async function saveIdForm(event) {
        event.preventDefault();
        hideFormError();

        if (!state.selectedGame) {
            showFormError('No game selected.');
            return;
        }

        const assembled = collectMetadataFromForm();
        if (assembled.errors.length) {
            showFormError(assembled.errors[0]);
            return;
        }

        const saveBtn = byId('gp-id-save');
        const originalText = saveBtn ? saveBtn.innerHTML : 'Save Passport';
        const isEditMode = state.modalMode === 'edit' && Number(state.editingPassportId) > 0;

        try {
            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...';
            }

            if (isEditMode) {
                const existingPassport = state.passports.find(function (item) {
                    return Number(item.id) === Number(state.editingPassportId);
                });

                await apiFetch('/profile/api/game-passports/update/', {
                    method: 'POST',
                    body: JSON.stringify({
                        id: state.editingPassportId,
                        metadata: assembled.metadata,
                        pinned: existingPassport ? !!existingPassport.is_pinned : false
                    })
                });
            } else {
                await apiFetch('/profile/api/game-passports/create/', {
                    method: 'POST',
                    body: JSON.stringify({
                        game_id: state.selectedGame.id,
                        metadata: assembled.metadata,
                        pinned: false
                    })
                });
            }

            closeIdModal();
            await refreshData();
            showToast(isEditMode ? 'Passport updated successfully.' : 'Game linked successfully.', 'success');
        } catch (error) {
            const fieldErrors = error.fieldErrors || {};
            const firstKey = Object.keys(fieldErrors)[0] || '';
            const firstError = firstKey ? fieldErrors[firstKey] : '';
            const message = Array.isArray(firstError) ? firstError[0] : firstError;
            showFormError(message || error.message || 'Unable to save passport right now.');
        } finally {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = originalText;
            }
        }
    }

    function showDisconnectError(message) {
        const el = byId('gp-disconnect-error');
        if (!el) return;
        el.textContent = message || 'Disconnect failed.';
        el.classList.remove('hidden');
    }

    function hideDisconnectError() {
        const el = byId('gp-disconnect-error');
        if (!el) return;
        el.textContent = '';
        el.classList.add('hidden');
    }

    function updateResendUi() {
        const timerEl = byId('gp-disconnect-timer');
        const resendBtn = byId('gp-disconnect-resend');
        if (!timerEl || !resendBtn) return;

        if (state.resendSeconds > 0) {
            timerEl.textContent = 'Resend in ' + state.resendSeconds + 's';
            resendBtn.disabled = true;
            resendBtn.classList.add('opacity-40', 'cursor-not-allowed');
            return;
        }

        timerEl.textContent = '';
        resendBtn.disabled = false;
        resendBtn.classList.remove('opacity-40', 'cursor-not-allowed');
    }

    function clearResendTimer() {
        if (state.resendTimerId) {
            clearInterval(state.resendTimerId);
            state.resendTimerId = null;
        }

        state.resendSeconds = 0;
        updateResendUi();
    }

    function startResendTimer(seconds) {
        clearResendTimer();

        state.resendSeconds = Number(seconds || 60);
        updateResendUi();

        state.resendTimerId = setInterval(function () {
            state.resendSeconds = Math.max(0, state.resendSeconds - 1);
            updateResendUi();

            if (state.resendSeconds === 0) {
                clearResendTimer();
            }
        }, 1000);
    }

    async function requestDeleteOtp(passportId) {
        await apiFetch('/profile/api/game-passports/request-delete-otp/', {
            method: 'POST',
            body: JSON.stringify({ passport_id: passportId })
        });
    }

    async function confirmDeleteOtp(passportId, code) {
        await apiFetch('/profile/api/game-passports/confirm-delete/', {
            method: 'POST',
            body: JSON.stringify({ passport_id: passportId, otp_code: code })
        });
    }

    function setDisconnectModalVisible(open) {
        const modal = byId('gp-disconnect-modal');
        const shell = byId('gp-disconnect-shell');
        if (!modal || !shell) return;

        if (open) {
            modal.classList.remove('hidden');
            modal.setAttribute('aria-hidden', 'false');
            setTimeout(function () {
                modal.classList.remove('opacity-0');
                shell.classList.remove('scale-95');
                syncBodyModalLock();
            }, 10);
            return;
        }

        modal.classList.add('opacity-0');
        shell.classList.add('scale-95');
        modal.setAttribute('aria-hidden', 'true');
        setTimeout(function () {
            modal.classList.add('hidden');
            syncBodyModalLock();
        }, 300);
    }

    function openDisconnectModal(passport) {
        state.otpPassport = passport;
        hideDisconnectError();

        const context = byId('gp-disconnect-context');
        const codeInput = byId('gp-disconnect-code');
        const game = findGameBySlug(getPassportSlug(passport));
        const title = getGameDisplay(game, passport);
        const identity = getIdentityLabel(passport);

        if (context) {
            context.textContent = title + ' - ' + identity;
        }

        if (codeInput) {
            codeInput.value = '';
            codeInput.focus();
        }

        startResendTimer(60);
        setDisconnectModalVisible(true);
    }

    function closeDisconnectModal() {
        setDisconnectModalVisible(false);
        hideDisconnectError();
        clearResendTimer();
        state.otpPassport = null;
    }

    async function resendDisconnectCode() {
        if (!state.otpPassport || state.resendSeconds > 0) {
            return;
        }

        try {
            await requestDeleteOtp(state.otpPassport.id);
            startResendTimer(60);
            showToast('A new code has been sent.', 'success');
        } catch (error) {
            const details = (error.payload && error.payload.metadata) || {};
            if (error.status === 429 && Number(details.seconds_remaining || 0) > 0) {
                startResendTimer(Number(details.seconds_remaining));
            }
            const message = error.message || 'Could not resend the code.';
            showDisconnectError(message);
            showToast(message, 'error');
        }
    }

    async function confirmDisconnect() {
        if (!state.otpPassport) {
            showDisconnectError('No game selected for disconnect.');
            return;
        }

        const input = byId('gp-disconnect-code');
        const confirmBtn = byId('gp-disconnect-confirm');
        const code = input ? String(input.value || '').trim() : '';

        if (!/^\d{6}$/.test(code)) {
            showDisconnectError('Please enter a valid 6-digit code.');
            return;
        }

        const originalText = confirmBtn ? confirmBtn.textContent : 'Disconnect';

        try {
            if (confirmBtn) {
                confirmBtn.disabled = true;
                confirmBtn.textContent = 'Disconnecting...';
            }

            await confirmDeleteOtp(state.otpPassport.id, code);
            closeDisconnectModal();
            await refreshData();
            showToast('Game disconnected.', 'success');
        } catch (error) {
            const message = error.message || 'Could not disconnect this game.';
            showDisconnectError(message);
            showToast(message, 'error');
        } finally {
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.textContent = originalText;
            }
        }
    }

    async function initiateOTPDelete(passportId, triggerButton) {
        const passport = state.passports.find(function (item) {
            return Number(item.id) === Number(passportId);
        });

        if (!passport) {
            showToast('Game link not found.', 'error');
            return;
        }

        const lockState = getPassportLockState(passport);
        if (lockState.isDeleteBlocked) {
            showDeletionBlockedMessage(lockState.title, lockState.message, lockState.kind);
            return;
        }

        setButtonLoading(triggerButton, true, 'Sending Code...');
        try {
            await requestDeleteOtp(passport.id);
            openDisconnectModal(passport);
            showToast('Confirmation code sent.', 'success');
        } catch (error) {
            const details = (error.payload && error.payload.metadata) || {};
            if (error.status === 429 && Number(details.seconds_remaining || 0) > 0) {
                startResendTimer(Number(details.seconds_remaining));
            }
            showToast(error.message || 'Could not start disconnect flow.', 'error');
        } finally {
            setButtonLoading(triggerButton, false);
        }
    }

    async function handleRootClick(event) {
        const actionBtn = event.target.closest('[data-action]');
        if (!actionBtn) return;

        const action = actionBtn.dataset.action;

        if (action === 'add-game') {
            const slug = canonicalSlug(actionBtn.dataset.gameSlug || '');
            const route = DIRECT_CONNECT_ROUTES[slug];

            if (route) {
                await startDirectConnect(slug, route, actionBtn);
                return;
            }

            openIdModal(slug, { mode: 'create' });
            return;
        }

        if (action === 'edit') {
            const passportId = Number(actionBtn.dataset.passportId || '0');
            if (!passportId) return;

            const passport = state.passports.find(function (item) {
                return Number(item.id) === passportId;
            });

            if (!passport) {
                showToast('Game link not found.', 'error');
                return;
            }

            const slug = getPassportSlug(passport);
            const game = findGameBySlug(slug);

            if (isApiSyncedPassport(passport, game)) {
                showToast('Synced games are read-only here. Update from provider sync.', 'warning');
                return;
            }

            setButtonLoading(actionBtn, true, 'Opening...');
            try {
                openIdModal(slug, { mode: 'edit', passport: passport });
            } finally {
                setButtonLoading(actionBtn, false);
            }
            return;
        }

        if (action === 'disconnect') {
            const passportId = Number(actionBtn.dataset.passportId || '0');
            if (!passportId) return;

            if (window.gamePassports && typeof window.gamePassports.initiateOTPDelete === 'function') {
                window.gamePassports.initiateOTPDelete(passportId, actionBtn);
                return;
            }

            initiateOTPDelete(passportId, actionBtn);
        }

        if (action === 'toggle-privacy') {
            const passportId = Number(actionBtn.dataset.passportId || '0');
            const gameSlug = actionBtn.dataset.gameSlug || '';
            const current = String(actionBtn.dataset.current || 'PUBLIC').toUpperCase();
            var newVis = current === 'PUBLIC' ? 'PRIVATE' : 'PUBLIC';

            actionBtn.disabled = true;
            actionBtn.classList.add('gp-btn-disabled');

            try {
                var result = await apiFetch('/profile/api/passports/set-visibility/', {
                    method: 'POST',
                    body: JSON.stringify({ game: gameSlug, visibility: newVis })
                });

                if (result && result.success) {
                    var passport = state.passports.find(function (p) { return Number(p.id) === passportId; });
                    if (passport) passport.visibility = newVis;
                    renderPlayerHub();
                    showToast('Privacy set to ' + newVis.charAt(0) + newVis.slice(1).toLowerCase(), 'success');
                } else {
                    showToast((result && result.error) || 'Failed to update privacy', 'error');
                    actionBtn.disabled = false;
                    actionBtn.classList.remove('gp-btn-disabled');
                }
            } catch (err) {
                showToast('Failed to update privacy', 'error');
                actionBtn.disabled = false;
                actionBtn.classList.remove('gp-btn-disabled');
            }
        }
    }

    function bindEvents() {
        if (state.eventsBound) {
            return;
        }

        const root = rootEl();
        if (root) {
            root.addEventListener('click', function (event) {
                handleRootClick(event).catch(function (error) {
                    showToast(error.message || 'Unexpected error while handling action.', 'error');
                });
            });
        }

        const idClose = byId('gp-id-modal-close');
        const idCancel = byId('gp-id-cancel');
        const idOverlay = byId('gp-id-modal-overlay');
        const idForm = byId('gp-id-form');

        if (idClose) idClose.addEventListener('click', closeIdModal);
        if (idCancel) idCancel.addEventListener('click', closeIdModal);
        if (idOverlay) idOverlay.addEventListener('click', closeIdModal);
        if (idForm) idForm.addEventListener('submit', saveIdForm);

        const disOverlay = byId('gp-disconnect-overlay');
        const disCancel = byId('gp-disconnect-cancel');
        const disConfirm = byId('gp-disconnect-confirm');
        const disResend = byId('gp-disconnect-resend');
        const disCode = byId('gp-disconnect-code');

        if (disOverlay) disOverlay.addEventListener('click', closeDisconnectModal);
        if (disCancel) disCancel.addEventListener('click', closeDisconnectModal);
        if (disConfirm) disConfirm.addEventListener('click', confirmDisconnect);
        if (disResend) disResend.addEventListener('click', resendDisconnectCode);

        if (disCode) {
            disCode.addEventListener('input', function (event) {
                event.target.value = String(event.target.value || '').replace(/\D/g, '').slice(0, 6);
            });
            disCode.addEventListener('keydown', function (event) {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    confirmDisconnect();
                }
            });
        }

        document.addEventListener('keydown', function (event) {
            if (event.key !== 'Escape') return;

            const idModal = byId('gp-id-modal');
            if (idModal && !idModal.classList.contains('hidden')) {
                closeIdModal();
                return;
            }

            const disModal = byId('gp-disconnect-modal');
            if (disModal && !disModal.classList.contains('hidden')) {
                closeDisconnectModal();
            }
        });

        // Career deep-link: delegated listener ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â supports any [data-career-deep-link] element,
        // including outer container divs. Skips clicks that land on interactive children.
        document.addEventListener('click', function (evt) {
            var trigger = evt.target && typeof evt.target.closest === 'function'
                ? evt.target.closest('[data-career-deep-link]')
                : null;
            if (!trigger) return;
            // If the click hit an interactive child (not the trigger itself), let it handle normally
            if (evt.target !== trigger && evt.target.closest('button, input, select, textarea, a[href]:not([data-career-deep-link])')) return;
            evt.preventDefault();
            if (typeof window.switchTab === 'function') {
                window.switchTab('career');
                setTimeout(function () {
                    var careerEl = document.getElementById('tab-career');
                    if (careerEl) careerEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 60);
            }
        }, false);

        state.eventsBound = true;
    }

    async function loadData() {
        const responses = await Promise.all([
            apiFetch('/profile/api/games/'),
            apiFetch('/profile/api/game-passports/')
        ]);

        state.games = extractGames(responses[0]);
        state.passports = extractPassports(responses[1]);
    }

    async function refreshData() {
        renderSkeletons(3);
        await loadData();
        renderPlayerHub();
    }

    async function init() {
        if (state.initialized) return;

        const root = rootEl();
        if (!root) return;

        promoteModalsToBody();
        bindEvents();
        await refreshData();
        await handleOAuthReturnState();
        state.initialized = true;
    }

    function ensureInitialized() {
        if (state.initialized) {
            return Promise.resolve();
        }

        if (state.initPromise) {
            return state.initPromise;
        }

        state.initPromise = init()
            .catch(function (error) {
                showToast(error.message || 'Could not load Player Hub.', 'error');
            })
            .finally(function () {
                state.initPromise = null;
            });

        return state.initPromise;
    }

    window.openManualBuilderModal = function (slug) {
        ensureInitialized().then(function () {
            openIdModal(slug);
        });
    };

    window.gamePassports = {
        init: ensureInitialized,
        ensureInitialized: ensureInitialized,
        refresh: refreshData,
        getCurrentPassports: function () {
            return state.passports.slice();
        },
        getPassportLockState: getPassportLockState,
        showDeletionBlockedMessage: showDeletionBlockedMessage,
        initiateOTPDelete: initiateOTPDelete,
        confirmOTPDelete: confirmDisconnect,
        resendOTP: resendDisconnectCode,
        cancelOTPDelete: closeDisconnectModal
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            const root = rootEl();
            if (root && root.classList.contains('active')) {
                ensureInitialized();
            }
        });
    } else {
        const root = rootEl();
        if (root && root.classList.contains('active')) {
            ensureInitialized();
        }
    }
})();

// Universal OAuth return handler — fires unconditionally on every page load so
// toasts are shown even when the passports tab is not the active tab on arrival.
document.addEventListener('DOMContentLoaded', function () {
    var params = new URLSearchParams(window.location.search);
    if (!params.has('oauth_status')) return;

    var status = params.get('oauth_status');
    var rawMsg = params.get('oauth_message') || '';
    var msg = rawMsg ? decodeURIComponent(rawMsg.replace(/\+/g, ' ')) : 'Operation completed';

    if (status === 'failed' || status === 'error') {
        if (typeof window.showToast === 'function') window.showToast(msg, 'error');
    } else {
        if (typeof window.showToast === 'function') window.showToast(msg, 'success');
    }

    // Clean the URL — redirect to passports tab so the refreshed list is visible.
    var nextUrl = window.location.pathname + '?tab=passports';
    window.history.replaceState({}, document.title, nextUrl);
});
