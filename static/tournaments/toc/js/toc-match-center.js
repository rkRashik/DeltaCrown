/**
 * TOC Engagement Module — Match Center
 *
 * Controls public match center presentation only (no operational workflow).
 */
;(function () {
    'use strict';

    const NS = (window.TOC = window.TOC || {});
    const CFG = window.TOC_CONFIG || {};

    const $ = (sel, root) => (root || document).querySelector(sel);

    const state = {
        initialized: false,
        loading: false,
        selectedMatchId: '',
        matches: [],
        gameFamily: 'vs',
        lastLoadedAt: 0,
        config: {
            enabled: true,
            show_timeline: true,
            show_media: true,
            show_stats: true,
            show_fan_pulse: true,
            theme: 'cyber',
            poll_question: 'Who takes the series?',
            poll_option_a: 'Team A',
            poll_option_b: 'Team B',
            auto_refresh_seconds: 20,
            match_overrides: {},
        },
    };

    const RELOAD_THROTTLE_MS = 5000;

    function toast(message, tone) {
        if (NS.toast) {
            NS.toast(message, tone || 'info');
        }
    }

    function refreshIcons() {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    function asBool(value, fallback) {
        if (typeof value === 'boolean') return value;
        if (typeof value === 'number') return Boolean(value);
        if (typeof value === 'string') {
            const token = value.trim().toLowerCase();
            if (['1', 'true', 'yes', 'on'].includes(token)) return true;
            if (['0', 'false', 'no', 'off'].includes(token)) return false;
        }
        return Boolean(fallback);
    }

    function asText(value, fallback, maxLength) {
        const text = String(value || '').trim();
        if (!text) return String(fallback || '').slice(0, maxLength || 240);
        return text.slice(0, maxLength || 240);
    }

    function asInt(value, fallback, minimum, maximum) {
        const parsed = Number.parseInt(value, 10);
        let next = Number.isFinite(parsed) ? parsed : fallback;
        if (typeof minimum === 'number') next = Math.max(minimum, next);
        if (typeof maximum === 'number') next = Math.min(maximum, next);
        return next;
    }

    function setSyncStatus(message, tone) {
        const el = $('#matchcenter-sync-status');
        if (!el) return;

        if (tone === 'loading') {
            el.className = 'text-[10px] font-mono text-dc-warning mt-2';
            el.textContent = message || 'Syncing...';
            return;
        }
        if (tone === 'error') {
            el.className = 'text-[10px] font-mono text-dc-danger mt-2';
            el.textContent = message || 'Sync failed';
            return;
        }
        if (tone === 'success') {
            el.className = 'text-[10px] font-mono text-dc-success mt-2';
            el.textContent = message || 'Synced';
            return;
        }

        el.className = 'text-[10px] font-mono text-dc-text mt-2';
        el.textContent = message || 'Not synced yet';
    }

    function setError(message) {
        const banner = $('#matchcenter-error-banner');
        if (!banner) return;

        if (!message) {
            banner.classList.add('hidden');
            banner.innerHTML = '';
            return;
        }

        banner.classList.remove('hidden');
        banner.innerHTML = ''
            + '<div class="flex items-start gap-2">'
            + '<i data-lucide="triangle-alert" class="w-4 h-4 text-dc-danger shrink-0 mt-0.5"></i>'
            + '<div class="min-w-0 flex-1">'
            + '<p class="text-xs font-bold text-white">Match Center sync failed</p>'
            + '<p class="text-[11px] text-dc-text mt-1">' + String(message || 'Unknown error') + '</p>'
            + '</div></div>';
        refreshIcons();
    }

    function selectedMatch() {
        if (!state.selectedMatchId) return null;
        return state.matches.find((m) => String(m.id) === String(state.selectedMatchId)) || null;
    }

    function getOverride(matchId) {
        if (!matchId) return {};
        const key = String(matchId);
        const map = state.config.match_overrides && typeof state.config.match_overrides === 'object'
            ? state.config.match_overrides
            : {};
        const value = map[key];
        return value && typeof value === 'object' ? value : {};
    }

    function setGlobalFormValues() {
        $('#matchcenter-enabled').checked = asBool(state.config.enabled, true);
        $('#matchcenter-show-timeline').checked = asBool(state.config.show_timeline, true);
        $('#matchcenter-show-media').checked = asBool(state.config.show_media, true);
        $('#matchcenter-show-stats').checked = asBool(state.config.show_stats, true);
        $('#matchcenter-show-fan-pulse').checked = asBool(state.config.show_fan_pulse, true);
        $('#matchcenter-theme').value = asText(state.config.theme, 'cyber', 24).toLowerCase();
        $('#matchcenter-auto-refresh').value = String(asInt(state.config.auto_refresh_seconds, 20, 10, 120));
        $('#matchcenter-poll-question').value = asText(state.config.poll_question, 'Who takes the series?', 180);
        $('#matchcenter-poll-option-a').value = asText(state.config.poll_option_a, 'Team A', 80);
        $('#matchcenter-poll-option-b').value = asText(state.config.poll_option_b, 'Team B', 80);
    }

    function renderMatchSelect() {
        const select = $('#matchcenter-match-select');
        if (!select) return;

        const options = ['<option value="">Select a match...</option>'];
        state.matches.forEach((match) => {
            const label = 'R' + (match.round_number || '-')
                + ' · M' + (match.match_number || '-')
                + ' · ' + (match.participant1_name || 'Team A')
                + ' vs '
                + (match.participant2_name || 'Team B');
            options.push('<option value="' + String(match.id) + '">' + label + '</option>');
        });

        select.innerHTML = options.join('');
        if (!state.selectedMatchId && state.matches.length) {
            state.selectedMatchId = String(state.matches[0].id);
        }
        select.value = state.selectedMatchId || '';
    }

    function renderOverrideEditor() {
        const override = getOverride(state.selectedMatchId);

        $('#matchcenter-headline').value = asText(override.headline, '', 120);
        $('#matchcenter-subline').value = asText(override.subline, '', 120);
        $('#matchcenter-stream-url').value = asText(override.stream_url, '', 500);
        $('#matchcenter-media-url').value = asText(override.featured_media_url, '', 500);

        const pollQ = $('#matchcenter-override-poll-question');
        const pollA = $('#matchcenter-override-poll-a');
        const pollB = $('#matchcenter-override-poll-b');
        if (pollQ) pollQ.value = asText(override.poll_question, '', 180);
        if (pollA) pollA.value = asText(override.poll_option_a, '', 80);
        if (pollB) pollB.value = asText(override.poll_option_b, '', 80);

        $('#matchcenter-override-show-timeline').checked = asBool(override.show_timeline, state.config.show_timeline);
        $('#matchcenter-override-show-media').checked = asBool(override.show_media, state.config.show_media);
        $('#matchcenter-override-show-stats').checked = asBool(override.show_stats, state.config.show_stats);
        $('#matchcenter-override-show-fan-pulse').checked = asBool(override.show_fan_pulse, state.config.show_fan_pulse);
    }

    function writeOverrideFromEditor() {
        if (!state.selectedMatchId) return;

        const key = String(state.selectedMatchId);
        const map = state.config.match_overrides && typeof state.config.match_overrides === 'object'
            ? state.config.match_overrides
            : {};

        const pollQ = $('#matchcenter-override-poll-question');
        const pollA = $('#matchcenter-override-poll-a');
        const pollB = $('#matchcenter-override-poll-b');

        const draft = {
            headline: asText($('#matchcenter-headline').value, '', 120),
            subline: asText($('#matchcenter-subline').value, '', 120),
            stream_url: asText($('#matchcenter-stream-url').value, '', 500),
            featured_media_url: asText($('#matchcenter-media-url').value, '', 500),
            poll_question: pollQ ? asText(pollQ.value, '', 180) : '',
            poll_option_a: pollA ? asText(pollA.value, '', 80) : '',
            poll_option_b: pollB ? asText(pollB.value, '', 80) : '',
            show_timeline: asBool($('#matchcenter-override-show-timeline').checked, true),
            show_media: asBool($('#matchcenter-override-show-media').checked, true),
            show_stats: asBool($('#matchcenter-override-show-stats').checked, true),
            show_fan_pulse: asBool($('#matchcenter-override-show-fan-pulse').checked, true),
        };

        const cleaned = {};
        Object.keys(draft).forEach((field) => {
            const value = draft[field];
            if (typeof value === 'string') {
                if (value.trim()) cleaned[field] = value.trim();
                return;
            }
            if (typeof value === 'boolean') {
                cleaned[field] = value;
            }
        });

        if (Object.keys(cleaned).length) {
            map[key] = cleaned;
        } else {
            delete map[key];
        }
        state.config.match_overrides = map;
    }

    function clearSelectedOverride() {
        if (!state.selectedMatchId) return;
        const map = state.config.match_overrides && typeof state.config.match_overrides === 'object'
            ? state.config.match_overrides
            : {};
        delete map[String(state.selectedMatchId)];
        state.config.match_overrides = map;
        renderOverrideEditor();
        renderPreview();
    }

    function renderPreview() {
        const match = selectedMatch();
        const override = getOverride(state.selectedMatchId);

        const baseTitle = match
            ? ((match.participant1_name || 'Team A') + ' vs ' + (match.participant2_name || 'Team B'))
            : 'Match Center Preview';

        const title = asText(override.headline, baseTitle, 120);
        const subline = asText(override.subline, 'Select a match to preview overrides.', 120);

        $('#matchcenter-preview-title').textContent = title;
        $('#matchcenter-preview-subline').textContent = subline;

        const theme = asText(state.config.theme, 'cyber', 24);
        $('#matchcenter-preview-theme').textContent = theme.toUpperCase();

        const boolLabel = function (value) { return value ? 'On' : 'Off'; };
        const showStats = asBool(
            override.show_stats,
            asBool(state.config.show_stats, true),
        );
        const showTimeline = asBool(
            override.show_timeline,
            asBool(state.config.show_timeline, true),
        );
        const showMedia = asBool(
            override.show_media,
            asBool(state.config.show_media, true),
        );
        const showFanPulse = asBool(
            override.show_fan_pulse,
            asBool(state.config.show_fan_pulse, true),
        );

        $('#matchcenter-preview-stats').textContent = boolLabel(showStats);
        $('#matchcenter-preview-timeline').textContent = boolLabel(showTimeline);
        $('#matchcenter-preview-media').textContent = boolLabel(showMedia);
        $('#matchcenter-preview-fan-pulse').textContent = boolLabel(showFanPulse);

        const question = asText(
            override.poll_question,
            asText(state.config.poll_question, 'Who takes the series?', 180),
            180,
        );
        const optionA = asText(
            override.poll_option_a,
            asText(state.config.poll_option_a, 'Team A', 80),
            80,
        );
        const optionB = asText(
            override.poll_option_b,
            asText(state.config.poll_option_b, 'Team B', 80),
            80,
        );

        $('#matchcenter-preview-question').textContent = question;
        $('#matchcenter-preview-option-a').textContent = optionA;
        $('#matchcenter-preview-option-b').textContent = optionB;

        const variantBadge = $('#matchcenter-preview-variant');
        if (variantBadge) {
            const family = String(state.gameFamily || 'vs').toLowerCase();
            const labels = { br: 'BR', efootball: 'eFootball', vs: 'VS' };
            variantBadge.textContent = labels[family] || 'VS';
            variantBadge.classList.remove('hidden');
        }
    }

    function formToConfig() {
        state.config.enabled = asBool($('#matchcenter-enabled').checked, true);
        state.config.show_timeline = asBool($('#matchcenter-show-timeline').checked, true);
        state.config.show_media = asBool($('#matchcenter-show-media').checked, true);
        state.config.show_stats = asBool($('#matchcenter-show-stats').checked, true);
        state.config.show_fan_pulse = asBool($('#matchcenter-show-fan-pulse').checked, true);
        state.config.theme = asText($('#matchcenter-theme').value, 'cyber', 24).toLowerCase();
        state.config.auto_refresh_seconds = asInt($('#matchcenter-auto-refresh').value, 20, 10, 120);
        state.config.poll_question = asText($('#matchcenter-poll-question').value, 'Who takes the series?', 180);
        state.config.poll_option_a = asText($('#matchcenter-poll-option-a').value, 'Team A', 80);
        state.config.poll_option_b = asText($('#matchcenter-poll-option-b').value, 'Team B', 80);

        writeOverrideFromEditor();

        return {
            enabled: state.config.enabled,
            show_timeline: state.config.show_timeline,
            show_media: state.config.show_media,
            show_stats: state.config.show_stats,
            show_fan_pulse: state.config.show_fan_pulse,
            theme: state.config.theme,
            auto_refresh_seconds: state.config.auto_refresh_seconds,
            poll_question: state.config.poll_question,
            poll_option_a: state.config.poll_option_a,
            poll_option_b: state.config.poll_option_b,
            match_overrides: state.config.match_overrides || {},
        };
    }

    async function fetchConfig() {
        if (!NS.api || typeof NS.api.get !== 'function') {
            throw new Error('TOC API helper unavailable.');
        }

        const payload = await NS.api.get('match-center/config/');
        const config = payload && typeof payload.config === 'object' ? payload.config : {};
        const matches = Array.isArray(payload && payload.matches) ? payload.matches : [];

        state.config = {
            ...state.config,
            ...config,
            match_overrides: config.match_overrides && typeof config.match_overrides === 'object'
                ? config.match_overrides
                : {},
        };
        state.matches = matches;
        if (payload && typeof payload.game_family === 'string') {
            state.gameFamily = payload.game_family;
        }

        if (state.selectedMatchId && !state.matches.some((m) => String(m.id) === String(state.selectedMatchId))) {
            state.selectedMatchId = '';
        }
        if (!state.selectedMatchId && state.matches.length) {
            state.selectedMatchId = String(state.matches[0].id);
        }
    }

    async function load() {
        if (state.loading) return;
        state.loading = true;
        setError('');
        setSyncStatus('Loading match center settings...', 'loading');

        try {
            await fetchConfig();
            setGlobalFormValues();
            renderMatchSelect();
            renderOverrideEditor();
            renderPreview();
            state.lastLoadedAt = Date.now();
            setSyncStatus('Ready. Update values and click Save Match Center.', 'neutral');
        } catch (error) {
            const message = error && error.message ? String(error.message) : 'Unable to load Match Center settings.';
            setError(message);
            setSyncStatus(message, 'error');
            toast(message, 'error');
        } finally {
            state.loading = false;
            refreshIcons();
        }
    }

    async function save() {
        if (state.loading) return;
        state.loading = true;
        setError('');
        setSyncStatus('Syncing Match Center settings...', 'loading');

        const saveBtn = $('#matchcenter-save-btn');
        const previousHtml = saveBtn ? saveBtn.innerHTML : '';
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i> Saving...';
            refreshIcons();
        }

        try {
            const payload = formToConfig();
            if (!NS.api || typeof NS.api.post !== 'function') {
                throw new Error('TOC API helper unavailable.');
            }
            const response = await NS.api.post('match-center/config/', payload);
            const nextConfig = response && typeof response.config === 'object' ? response.config : payload;
            const nextMatches = Array.isArray(response && response.matches) ? response.matches : state.matches;

            state.config = {
                ...state.config,
                ...nextConfig,
                match_overrides: nextConfig.match_overrides && typeof nextConfig.match_overrides === 'object'
                    ? nextConfig.match_overrides
                    : {},
            };
            state.matches = nextMatches;
            if (response && typeof response.game_family === 'string') {
                state.gameFamily = response.game_family;
            }

            setGlobalFormValues();
            renderMatchSelect();
            renderOverrideEditor();
            renderPreview();
            state.lastLoadedAt = Date.now();

            const invalidUrls = response && Array.isArray(response.invalid_urls) ? response.invalid_urls : [];
            if (invalidUrls.length) {
                const labels = invalidUrls.map((u) => (u && u.label) || (u && u.field) || 'URL').join(', ');
                toast('Saved, but some override URLs were rejected: ' + labels, 'warning');
            } else {
                toast('Match Center settings synced to public match pages.', 'success');
            }
            setSyncStatus('Last synced ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }), 'success');
        } catch (error) {
            const message = error && error.message ? String(error.message) : 'Unable to save Match Center settings.';
            setError(message);
            setSyncStatus(message, 'error');
            toast(message, 'error');
        } finally {
            state.loading = false;
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.innerHTML = previousHtml;
                refreshIcons();
            }
        }
    }

    function openSelectedPublicMatch() {
        const match = selectedMatch();
        if (!match) {
            toast('Select a match first.', 'warning');
            return;
        }

        const template = String(CFG.matchCenterPublicUrlTemplate || '').trim();
        let target = '';
        if (template && template.indexOf('__MATCH_ID__') !== -1) {
            target = template.replace('__MATCH_ID__', String(match.id));
        } else {
            target = '/tournaments/' + String(CFG.tournamentSlug || '') + '/matches/' + String(match.id) + '/';
        }
        window.open(target, '_blank', 'noopener');
    }

    function bindEvents() {
        const refreshBtn = $('#matchcenter-refresh-btn');
        const saveBtn = $('#matchcenter-save-btn');
        const select = $('#matchcenter-match-select');
        const clearBtn = $('#matchcenter-clear-override-btn');
        const openBtn = $('#matchcenter-open-public-btn');

        if (refreshBtn) {
            refreshBtn.addEventListener('click', function () {
                load();
            });
        }
        if (saveBtn) {
            saveBtn.addEventListener('click', function () {
                save();
            });
        }
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                clearSelectedOverride();
            });
        }
        if (openBtn) {
            openBtn.addEventListener('click', function () {
                openSelectedPublicMatch();
            });
        }

        if (select) {
            select.addEventListener('change', function () {
                writeOverrideFromEditor();
                state.selectedMatchId = String(select.value || '');
                renderOverrideEditor();
                renderPreview();
            });
        }

        const liveInputs = [
            '#matchcenter-enabled',
            '#matchcenter-show-timeline',
            '#matchcenter-show-media',
            '#matchcenter-show-stats',
            '#matchcenter-show-fan-pulse',
            '#matchcenter-theme',
            '#matchcenter-auto-refresh',
            '#matchcenter-poll-question',
            '#matchcenter-poll-option-a',
            '#matchcenter-poll-option-b',
            '#matchcenter-headline',
            '#matchcenter-subline',
            '#matchcenter-stream-url',
            '#matchcenter-media-url',
            '#matchcenter-override-poll-question',
            '#matchcenter-override-poll-a',
            '#matchcenter-override-poll-b',
            '#matchcenter-override-show-timeline',
            '#matchcenter-override-show-media',
            '#matchcenter-override-show-stats',
            '#matchcenter-override-show-fan-pulse',
        ];

        liveInputs.forEach((selector) => {
            const el = $(selector);
            if (!el) return;
            const eventName = (el.type === 'checkbox' || el.tagName === 'SELECT') ? 'change' : 'input';
            el.addEventListener(eventName, function () {
                formToConfig();
                renderPreview();
            });
        });
    }

    function initOnce() {
        if (state.initialized) return;
        state.initialized = true;
        bindEvents();
        load();
    }

    document.addEventListener('toc:tab-changed', function (event) {
        if (!event || !event.detail || event.detail.tab !== 'match-center') return;
        if (!state.initialized) {
            initOnce();
            return;
        }
        if (state.loading) return;
        if (Date.now() - state.lastLoadedAt < RELOAD_THROTTLE_MS) return;
        load();
    });

    if (window.location.hash.replace('#', '').trim() === 'match-center') {
        initOnce();
    }

    NS.matchCenter = {
        load,
        save,
        openSelectedPublicMatch,
    };
})();
