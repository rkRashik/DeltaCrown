/*
 * Phase 9 Player Hub controller.
 * Drives connected roster, add-game cards, schema modal, and OTP disconnect flow.
 */

(function () {
    'use strict';

    const ROOT_ID = 'tab-passports';

    const DIRECT_CONNECT_ROUTES = {
        valorant: '/api/oauth/riot/login/',
        cs2: '/profile/api/oauth/steam/login/?game=cs2&response_mode=json&callback_mode=redirect',
        dota2: '/profile/api/oauth/steam/login/?game=dota2&response_mode=json&callback_mode=redirect',
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
        if (status === 'connected') {
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

    function collectMetaTags(passport, game) {
        const metadata = passport.metadata || {};
        const hide = {
            identity_key: true,
            live_stats: true,
            api_synced: true,
            oauth_provider: true,
            riot_last_match_sync_at: true
        };

        const tags = [];
        Object.keys(metadata).forEach(function (key) {
            if (hide[key]) return;
            const value = metadata[key];
            if (value === null || value === undefined || value === '') return;
            if (typeof value === 'object') return;
            tags.push({
                key: key,
                label: getFieldDisplayLabel(key, game),
                value: value
            });
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

    function renderConnectedGames() {
        const grid = byId('gp-connected-grid');
        const empty = byId('gp-connected-empty');
        if (!grid || !empty) return;

        if (!state.passports.length) {
            grid.innerHTML = '';
            empty.classList.remove('hidden');
            return;
        }

        empty.classList.add('hidden');

        const markup = state.passports.map(function (passport, index) {
            const game = findGameBySlug(getPassportSlug(passport));
            const title = getGameDisplay(game, passport);
            const identity = getIdentityLabel(passport);
            const lockState = getPassportLockState(passport);
            const accent = getGameAccent(game);
            const accentSoft = hexToRgba(accent, 0.25);
            const accentGlow = hexToRgba(accent, 0.2);
            const icon = getGameIconMarkup(game, title);
            const tags = collectMetaTags(passport, game);
            const canEdit = !isApiSyncedPassport(passport, game);
            const isApiSynced = isApiSyncedPassport(passport, game) || shouldRenderLivePerformance(passport, game);
            const isLocked = lockState.isDeleteBlocked;
            const livePerformanceMarkup = renderLivePerformance(passport, game);

            const sourceChip = isApiSynced
                ? '<span class="gp-source-chip gp-source-api"><i class="fa-solid fa-bolt text-[10px]"></i> API Synced</span>'
                : '<span class="gp-source-chip gp-source-manual"><i class="fa-solid fa-user-pen text-[10px]"></i> Manual</span>';

            const lockText = isLocked
                ? '<span class="gp-lock-text gp-lock-active">Identity Locked</span>'
                : '<span class="gp-lock-text gp-lock-open">Roster Ready</span>';

            const dataTagMarkup = tags.map(function (entry) {
                return (
                    '<div class="gp-data-chip">' +
                        '<span class="gp-data-chip-label">' + escapeHtml(entry.label || entry.key) + '</span>' +
                        '<span class="gp-data-chip-value">' + escapeHtml(entry.value) + '</span>' +
                    '</div>'
                );
            }).join('');

            const editAction = canEdit && !isLocked
                ? '<button type="button" data-action="edit" data-passport-id="' + String(passport.id) + '" class="gp-btn gp-btn-edit">' +
                    '<i class="fa-solid fa-pen-to-square"></i> Edit' +
                  '</button>'
                : '';

            const disconnectClass = isLocked ? 'gp-btn gp-btn-disconnect gp-btn-disabled' : 'gp-btn gp-btn-disconnect';
            const disconnectDisabled = isLocked ? ' disabled' : '';

            return (
                '<article class="gp-glass-panel gp-connected-card gp-roster-card gp-compact-card p-4 animate-slide-up relative" style="--gp-accent:' + escapeHtml(accent) + '; --gp-accent-soft:' + escapeHtml(accentSoft) + '; --gp-accent-glow:' + escapeHtml(accentGlow) + '; animation-delay:' + (index * 45) + 'ms;">' +
                    '<div class="gp-card-overlay"></div>' +
                    '<div class="relative z-10">' +
                        '<div class="gp-roster-head">' +
                            '<div class="flex items-center gap-3 min-w-0">' +
                                '<div class="gp-roster-icon w-12 h-12 rounded-lg border bg-black/35 flex items-center justify-center text-xl shrink-0">' + icon + '</div>' +
                                '<div class="min-w-0">' +
                                    '<h4 class="gp-roster-title">' + escapeHtml(title) + '</h4>' +
                                    '<div class="gp-roster-identity">' + escapeHtml(identity) + '</div>' +
                                '</div>' +
                            '</div>' +
                            sourceChip +
                        '</div>' +
                        '<div class="gp-data-chip-list">' + dataTagMarkup + '</div>' +
                        livePerformanceMarkup +
                        '<div class="gp-roster-divider"></div>' +
                        '<div class="gp-roster-foot">' +
                            lockText +
                            '<div class="flex items-center gap-2">' +
                                editAction +
                                '<button type="button" data-action="disconnect" data-passport-id="' + String(passport.id) + '" class="' + disconnectClass + '"' + disconnectDisabled + '>' +
                                '<i class="fa-solid fa-unlink"></i> Disconnect' +
                                '</button>' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                '</article>'
            );
        }).join('');

        grid.innerHTML = markup;
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
                '<div class="gp-glass-panel rounded-2xl p-8 text-center col-span-full border border-dashed border-white/20">' +
                    '<div class="w-14 h-14 mx-auto mb-3 rounded-xl border border-white/10 bg-white/5 flex items-center justify-center text-z-purple">' +
                        '<i class="fa-solid fa-trophy text-xl"></i>' +
                    '</div>' +
                    '<h4 class="text-white font-bold text-lg">All games connected</h4>' +
                    '<p class="text-gray-500 text-sm mt-1">Your roster is ready for team play and tournaments.</p>' +
                '</div>'
            );
            return;
        }

        grid.innerHTML = availableGames.map(function (game) {
            const slug = canonicalSlug(game.slug || game.name || game.display_name);
            const title = game.display_name || game.name || slug;
            const accent = getGameAccent(game);
            const accentSoft = hexToRgba(accent, 0.2);
            const icon = getGameIconMarkup(game, title);
            const isDirect = !!DIRECT_CONNECT_ROUTES[slug];
            const connectType = isDirect ? 'Direct' : 'Manual';
            const chipIcon = isDirect
                ? '<i class="fa-solid fa-bolt"></i>'
                : '<i class="fa-solid fa-id-card"></i>';

            return (
                '<article class="gp-glass-panel gp-add-card gp-compact-card rounded-xl p-3.5 border border-white/10" style="--gp-accent:' + escapeHtml(accent) + '; background:linear-gradient(152deg,' + escapeHtml(accentSoft) + ',' + hexToRgba(accent, 0.05) + ');">' +
                    '<div class="flex items-start justify-between gap-2">' +
                        '<div class="gp-roster-icon w-10 h-10 rounded-lg border bg-black/35 flex items-center justify-center text-lg font-black shrink-0">' + icon + '</div>' +
                        '<span class="gp-add-type-chip">' + chipIcon + ' ' + escapeHtml(connectType) + '</span>' +
                    '</div>' +
                    '<div class="mt-3 min-w-0">' +
                        '<h4 class="gp-add-title">' + escapeHtml(title) + '</h4>' +
                        '<p class="gp-add-subtitle">' + (isDirect ? 'Instant provider connect' : 'Fill player ID fields') + '</p>' +
                    '</div>' +
                    '<button type="button" data-action="add-game" data-game-slug="' + escapeHtml(slug) + '" class="gp-btn gp-btn-connect w-full mt-3">Connect</button>' +
                '</article>'
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

    function renderSchemaField(field) {
        const key = String(field.key || 'field');
        const label = getFieldDisplayLabel(key, state.selectedGame, field.label);
        const type = String(field.type || 'text').toLowerCase();
        const required = !!field.required;
        const minLength = field.min_length ? Number(field.min_length) : 0;
        const maxLength = field.max_length ? Number(field.max_length) : 0;

        const baseLabel =
            '<label class="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1.5 ml-1" for="gp-field-' + escapeHtml(key) + '">' +
                escapeHtml(label) + (required ? ' <span class="text-red-400">*</span>' : '') +
            '</label>';

        const helpText = field.help_text
            ? '<p class="text-[11px] text-gray-500 mt-1">' + escapeHtml(field.help_text) + '</p>'
            : '';

        if (type === 'select') {
            const optionsMarkup = getFieldOptions(field).map(function (option) {
                return '<option value="' + escapeHtml(option.value) + '">' + escapeHtml(option.label) + '</option>';
            }).join('');

            return (
                '<div class="mb-4 relative">' +
                    baseLabel +
                    '<select id="gp-field-' + escapeHtml(key) + '" data-id-field="' + escapeHtml(key) + '" class="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-z-cyan focus:ring-1 focus:ring-z-cyan transition appearance-none cursor-pointer"' + (required ? ' required' : '') + '>' +
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
                '<input id="gp-field-' + escapeHtml(key) + '" data-id-field="' + escapeHtml(key) + '" type="text" class="w-full bg-black/50 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-z-cyan focus:ring-1 focus:ring-z-cyan transition" autocomplete="off"' +
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
        const fieldsEl = byId('gp-id-fields');
        const saveBtn = byId('gp-id-save');

        const title = game.display_name || game.name || 'Game';
        const accent = getGameAccent(game);

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

        const schema = Array.isArray(game.passport_schema) ? game.passport_schema : [];

        if (fieldsEl) {
            if (!schema.length) {
                fieldsEl.innerHTML = '<div class="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">This game has no profile fields configured right now.</div>';
            } else {
                fieldsEl.innerHTML = schema.map(renderSchemaField).join('');
            }
        }

        if (isEditMode && schema.length) {
            schema.forEach(function (field) {
                const key = String(field.key || '').trim();
                if (!key) return;

                const input = document.querySelector('[data-id-field="' + key + '"]');
                if (!input) return;

                const rawValue = getPassportFieldValue(editingPassport, key);
                const value = String(rawValue || '').trim();
                if (!value) return;

                if (String(input.tagName || '').toLowerCase() === 'select') {
                    const hasOption = Array.from(input.options || []).some(function (opt) {
                        return String(opt.value) === value;
                    });
                    if (hasOption) {
                        input.value = value;
                    }
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
        const fieldLabel = getFieldDisplayLabel(field.key, state.selectedGame, field.label);

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
        const game = state.selectedGame;
        const result = { metadata: {}, errors: [] };

        if (!game) {
            result.errors.push('No game selected.');
            return result;
        }

        const schema = Array.isArray(game.passport_schema) ? game.passport_schema : [];

        schema.forEach(function (field) {
            const input = document.querySelector('[data-id-field="' + field.key + '"]');
            if (!input) return;

            const value = String(input.value || '').trim();
            const validationError = validateField(field, value);

            if (validationError) {
                result.errors.push(validationError);
                return;
            }

            result.metadata[field.key] = value;
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

            openIdModal(slug, { mode: 'edit', passport: passport });
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
