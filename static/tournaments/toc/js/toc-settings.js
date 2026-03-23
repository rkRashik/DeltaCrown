/**
 * TOC Sprint 10G — Settings & Configuration (1:1 Database Parity)
 * =================================================================
 * Full game-aware tournament settings with dynamic section visibility.
 * Sections: Basic, Media, Format, Schedule, Venue, Fees, Payment Methods,
 *           Prizes, Rules, Features, Social, Game Config, Map Pool,
 *           Regions, Rulebook, BR Scoring, Certs, Waitlist, SEO.
 */
;(function () {
    'use strict';

    const NS = (window.TOC = window.TOC || {});
    const API = (ep, opts) => NS.api(ep, opts);
    const CFG = () => window.TOC_CONFIG || {};
    const esc = (s) => { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; };
    const showOverlay = (...a) => NS.rbac?.showOverlay?.(...a) || console.warn('showOverlay unavailable');
    const closeOverlay = () => NS.rbac?.closeOverlay?.();
    const toast = (m, t) => NS.toast?.(m, t);
    const _richTextEditors = new Map();
    const setVal = (container, field, value) => {
        const el = container?.querySelector('[data-field="' + field + '"]');
        if (!el) return;
        if (el.type === 'checkbox') el.checked = !!value;
        else if (el.tagName === 'TEXTAREA') {
            const editor = _richTextEditors.get(el);
            if (editor) editor.setData(value || '');
            else el.value = value || '';
        }
        else el.value = value ?? '';
    };
    const getVal = (container, field) => {
        const el = container?.querySelector('[data-field="' + field + '"]');
        if (!el) return undefined;
        if (el.type === 'checkbox') return el.checked;
        if (el.type === 'number') return el.value === '' ? null : Number(el.value);
        if (el.type === 'datetime-local') return el.value ? el.value.replace('T', ' ') : null;
        if (el.tagName === 'TEXTAREA') {
            const editor = _richTextEditors.get(el);
            return editor ? editor.getData() : el.value;
        }
        return el.value;
    };
    const gatherFields = (containerId) => {
        const c = document.getElementById(containerId);
        if (!c) return {};
        const data = {};
        c.querySelectorAll('[data-field]').forEach(el => {
            const k = el.getAttribute('data-field');
            if (el.type === 'checkbox') data[k] = el.checked;
            else if (el.type === 'number') data[k] = el.value === '' ? null : Number(el.value);
            else if (el.type === 'datetime-local') data[k] = el.value ? el.value.replace('T', ' ') : null;
            else if (el.tagName === 'TEXTAREA') {
                const editor = _richTextEditors.get(el);
                data[k] = editor ? editor.getData() : el.value;
            }
            else data[k] = el.value;
        });
        return data;
    };

    /* State */
    let vetoSequence = [];
    let rulebookVersions = [];
    let paymentMethods = [];
    let _settingsInflight = null;
    let _settingsLastInitAt = 0;
    let _settingsLoadedOnce = false;
    let _settingsDirty = false;
    let _suspendDirtyTracking = false;
    let _fieldSectionMap = null;
    const _sectionState = {};
    let _settingsVersion = null;
    const _sectionSnapshots = {};

    const SETTINGS_CACHE_TTL_MS = 90000;
    const SETTINGS_SECTION_IDS = [
        'settings-basic',
        'settings-media',
        'settings-format',
        'settings-dates',
        'settings-venue',
        'settings-fees',
        'settings-prizes',
        'settings-rules',
        'settings-features',
        'settings-social',
        'settings-waitlist',
        'settings-seo',
    ];

    const SETTINGS_CUSTOM_SECTION_SAVERS = {
        'settings-game-section': function () { return saveGameConfig(); },
        'settings-br-section': function () { return saveBRScoring(); },
        'settings-scoring-section': function () { return saveScoringConfig(); },
    };

    function isSettingsTabActive() {
        return (window.location.hash || '').replace('#', '') === 'settings';
    }

    function hasFreshSettingsCache() {
        return _settingsLoadedOnce && _settingsLastInitAt > 0 && (Date.now() - _settingsLastInitAt) < SETTINGS_CACHE_TTL_MS;
    }

    function _formatTime(date) {
        if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    function setSettingsSyncStatus(state, note) {
        const el = document.getElementById('settings-sync-status');
        if (!el) return;

        if (state === 'loading') {
            el.className = 'text-[10px] font-mono text-dc-warning mt-1';
            el.textContent = note || 'Syncing settings...';
            return;
        }

        if (state === 'error') {
            el.className = 'text-[10px] font-mono text-dc-danger mt-1';
            el.textContent = note || 'Sync failed';
            return;
        }

        if (_settingsLastInitAt > 0) {
            el.className = 'text-[10px] font-mono text-dc-text mt-1';
            el.textContent = 'Last sync ' + _formatTime(new Date(_settingsLastInitAt));
            return;
        }

        el.className = 'text-[10px] font-mono text-dc-text mt-1';
        el.textContent = 'Not synced yet';
    }

    function setSettingsErrorBanner(message) {
        const el = document.getElementById('settings-error-banner');
        if (!el) return;

        if (!message) {
            el.classList.add('hidden');
            el.innerHTML = '';
            return;
        }

        el.classList.remove('hidden');
        el.innerHTML = '<div class="flex items-start gap-3">'
            + '<i data-lucide="wifi-off" class="w-4 h-4 text-dc-danger shrink-0 mt-0.5"></i>'
            + '<div class="min-w-0 flex-1">'
            + '<p class="text-xs font-bold text-white">Settings refresh failed</p>'
            + '<p class="text-[11px] text-dc-text mt-1">' + esc(message) + '</p>'
            + '<button type="button" class="mt-2 px-2.5 py-1 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" onclick="TOC.settings.init({ force: true })">Retry now</button>'
            + '</div></div>';
        if (typeof lucide !== 'undefined') {
            try { lucide.createIcons(); } catch (e) { /* ok */ }
        }
    }

    function _markSettingsDirty (isDirty) {
        if (_suspendDirtyTracking) return;
        _settingsDirty = !!isDirty;

        const dirtyEl = document.getElementById('settings-dirty-indicator');
        if (dirtyEl) dirtyEl.classList.toggle('hidden', !_settingsDirty);

        const saveBtn = document.getElementById('btn-settings-save-all');
        if (saveBtn) {
            saveBtn.disabled = !_settingsDirty;
            saveBtn.classList.toggle('opacity-50', !_settingsDirty);
            saveBtn.classList.toggle('cursor-not-allowed', !_settingsDirty);
            if (_settingsDirty) {
                saveBtn.title = 'Save pending settings changes';
            } else {
                saveBtn.title = 'No pending settings changes';
            }
        }
    }

    function _buildFieldSectionMap () {
        if (_fieldSectionMap) return _fieldSectionMap;
        _fieldSectionMap = {};
        document.querySelectorAll('[id^="settings-"][data-field], [id^="settings-"] [data-field]').forEach(function (el) {
            const field = el.getAttribute('data-field');
            if (!field) return;
            const section = el.closest('[id^="settings-"]');
            if (!section || !section.id) return;
            _fieldSectionMap[field] = section.id;
        });
        return _fieldSectionMap;
    }

    function _ensureSectionStateBadges () {
        document.querySelectorAll('#view-settings [id^="settings-"]').forEach(function (section) {
            const details = section.closest('details');
            if (!details) return;
            const summaryTitle = details.querySelector('summary span');
            if (!summaryTitle || summaryTitle.querySelector('[data-settings-section-state]')) return;
            const pill = document.createElement('span');
            pill.setAttribute('data-settings-section-state', section.id);
            pill.className = 'hidden ml-2 px-2 py-0.5 rounded-full text-[9px] uppercase tracking-wider font-bold border';
            summaryTitle.appendChild(pill);
        });
    }

    function _renderSectionState (sectionId, state, text) {
        const pill = document.querySelector('[data-settings-section-state="' + sectionId + '"]');
        if (!pill) return;

        if (!state || state === 'clean') {
            pill.classList.add('hidden');
            pill.textContent = '';
            return;
        }

        pill.classList.remove('hidden');
        pill.classList.remove('border-dc-warning/40', 'text-dc-warning', 'bg-dc-warning/10');
        pill.classList.remove('border-dc-success/40', 'text-dc-success', 'bg-dc-success/10');
        pill.classList.remove('border-theme/40', 'text-theme', 'bg-theme/10');
        pill.classList.remove('border-dc-danger/40', 'text-dc-danger', 'bg-dc-danger/10');

        if (state === 'dirty') {
            pill.classList.add('border-dc-warning/40', 'text-dc-warning', 'bg-dc-warning/10');
            pill.textContent = text || 'Unsaved';
            return;
        }

        if (state === 'saving') {
            pill.classList.add('border-theme/40', 'text-theme', 'bg-theme/10');
            pill.textContent = text || 'Saving';
            return;
        }

        if (state === 'saved') {
            pill.classList.add('border-dc-success/40', 'text-dc-success', 'bg-dc-success/10');
            pill.textContent = text || 'Saved';
            return;
        }

        if (state === 'error') {
            pill.classList.add('border-dc-danger/40', 'text-dc-danger', 'bg-dc-danger/10');
            pill.textContent = text || 'Fix errors';
        }
    }

    function _setSectionState (sectionId, state, text) {
        if (!sectionId) return;
        _sectionState[sectionId] = state;
        _renderSectionState(sectionId, state, text);
    }

    function _refreshGlobalDirtyFromSections () {
        _markSettingsDirty(_dirtySections().length > 0);
    }

    function _syncConditionalVisibility () {
        syncModeVisibility();
        syncCheckInVisibility();
        syncFeeVisibility();
        syncNoShowVisibility();
    }

    function _captureSectionSnapshot (sectionId) {
        if (!sectionId) return;
        _sectionSnapshots[sectionId] = gatherFields(sectionId);
    }

    function _captureAllSectionSnapshots () {
        SETTINGS_SECTION_IDS.forEach(function (sectionId) {
            _captureSectionSnapshot(sectionId);
        });
    }

    function _restoreSectionSnapshots (sectionIds) {
        _suspendDirtyTracking = true;
        try {
            (sectionIds || []).forEach(function (sectionId) {
                const section = document.getElementById(sectionId);
                const snapshot = _sectionSnapshots[sectionId];
                if (!section || !snapshot) return;
                Object.keys(snapshot).forEach(function (field) {
                    setVal(section, field, snapshot[field]);
                });
                _setSectionState(sectionId, 'clean');
            });
            _syncConditionalVisibility();
        } finally {
            _suspendDirtyTracking = false;
        }
    }

    function _updateSettingsVersionFromResponse (result) {
        const version = result && result.settings_version;
        if (typeof version === 'string' && version.length > 0) {
            _settingsVersion = version;
        }
    }

    function _markAllSections (state) {
        document.querySelectorAll('#view-settings [id^="settings-"]').forEach(function (section) {
            _setSectionState(section.id, state);
        });
    }

    function _dirtySections () {
        return Object.keys(_sectionState).filter(function (sectionId) {
            return _sectionState[sectionId] === 'dirty';
        });
    }

    function _clearFieldErrors () {
        document.querySelectorAll('[data-settings-field-error-for]').forEach(function (el) { el.remove(); });
        document.querySelectorAll('[data-field]').forEach(function (fieldEl) {
            fieldEl.classList.remove('border-dc-danger', 'ring-1', 'ring-dc-danger/40');
            fieldEl.removeAttribute('aria-invalid');
            fieldEl.removeAttribute('aria-describedby');
        });
    }

    function _applyFieldErrors (fieldErrors, sectionErrors) {
        _clearFieldErrors();

        const map = _buildFieldSectionMap();
        const sectionsWithErrors = new Set();
        let focused = false;

        Object.entries(fieldErrors || {}).forEach(function (entry) {
            const field = entry[0];
            const messages = Array.isArray(entry[1]) ? entry[1] : [String(entry[1] || 'Invalid value')];
            const input = document.querySelector('[data-field="' + field + '"]');
            if (!input) return;

            input.classList.add('border-dc-danger', 'ring-1', 'ring-dc-danger/40');
            input.setAttribute('aria-invalid', 'true');

            const errId = 'settings-error-' + field;
            input.setAttribute('aria-describedby', errId);

            const msgEl = document.createElement('p');
            msgEl.id = errId;
            msgEl.setAttribute('data-settings-field-error-for', field);
            msgEl.className = 'mt-1 text-[11px] text-dc-danger';
            msgEl.textContent = messages[0] || 'Invalid value';
            input.insertAdjacentElement('afterend', msgEl);

            const sectionId = map[field];
            if (sectionId) sectionsWithErrors.add(sectionId);

            if (!focused) {
                input.focus();
                focused = true;
            }
        });

        Object.keys(sectionErrors || {}).forEach(function (sectionId) {
            sectionsWithErrors.add(sectionId);
        });

        sectionsWithErrors.forEach(function (sectionId) {
            _setSectionState(sectionId, 'error');
        });
    }

    async function _extractErrorPayload (e) {
        if (!e || !e.response) return null;
        try {
            return await e.response.clone().json();
        } catch (ignored) {
            return null;
        }
    }

    function _bindDirtyTracking () {
        const sections = SETTINGS_SECTION_IDS.concat(['settings-game-config', 'settings-br-scoring', 'settings-scoring']);

        sections.forEach(function (id) {
            const el = document.getElementById(id);
            if (!el || el.dataset.dirtyBound === '1') return;
            el.dataset.dirtyBound = '1';

            ['input', 'change'].forEach(function (evt) {
                el.addEventListener(evt, function () {
                    if (_suspendDirtyTracking) return;
                    _setSectionState(id, 'dirty');
                    _refreshGlobalDirtyFromSections();
                });
            });
        });
    }

    async function _initRichTextEditors () {
        const inputs = document.querySelectorAll('#view-settings textarea[data-richtext="true"]');
        if (!inputs.length) return;

        function isUrl(value) {
            return /^https?:\/\//i.test(String(value || '').trim());
        }

        function normalizeHtml(value) {
            const html = String(value || '').trim();
            if (!html) return '';
            if (html === '<br>' || html === '<p><br></p>') return '';
            return html;
        }

        function markDirtyForInput(input) {
            if (_suspendDirtyTracking) return;
            const section = input.closest('[id^="settings-"]');
            if (!section || !section.id) return;
            _setSectionState(section.id, 'dirty');
            _refreshGlobalDirtyFromSections();
        }

        function exec(command, value) {
            try {
                document.execCommand(command, false, value);
            } catch (err) {
                console.warn('[TOC.settings] rich text command failed', command, err);
            }
        }

        for (const input of inputs) {
            if (_richTextEditors.has(input)) continue;
            try {
                const shell = document.createElement('div');
                shell.className = 'toc-richtext-shell rounded-lg border border-dc-border bg-dc-surface overflow-hidden';

                const toolbar = document.createElement('div');
                toolbar.className = 'toc-richtext-toolbar flex flex-wrap items-center gap-1 p-2 border-b border-dc-border bg-dc-panel';

                const editorEl = document.createElement('div');
                editorEl.className = 'toc-richtext-editor min-h-[140px] p-3 text-sm text-dc-textBright focus:outline-none';
                editorEl.contentEditable = 'true';
                editorEl.innerHTML = input.value || '';

                const buttons = [
                    { label: 'B', title: 'Bold', cmd: 'bold' },
                    { label: 'I', title: 'Italic', cmd: 'italic' },
                    { label: 'U', title: 'Underline', cmd: 'underline' },
                    { label: '• List', title: 'Bulleted List', cmd: 'insertUnorderedList' },
                    { label: '1. List', title: 'Numbered List', cmd: 'insertOrderedList' },
                    { label: 'Quote', title: 'Block Quote', cmd: 'formatBlock', val: 'blockquote' },
                    { label: 'Clear', title: 'Clear Formatting', cmd: 'removeFormat' },
                ];

                buttons.forEach(function (btnCfg) {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'px-2 py-1 rounded border border-dc-border text-[11px] font-bold text-dc-textBright hover:bg-dc-surface transition-colors';
                    btn.textContent = btnCfg.label;
                    btn.title = btnCfg.title;
                    btn.addEventListener('click', function () {
                        editorEl.focus();
                        exec(btnCfg.cmd, btnCfg.val);
                        input.value = normalizeHtml(editorEl.innerHTML);
                        markDirtyForInput(input);
                    });
                    toolbar.appendChild(btn);
                });

                const linkBtn = document.createElement('button');
                linkBtn.type = 'button';
                linkBtn.className = 'px-2 py-1 rounded border border-dc-border text-[11px] font-bold text-dc-textBright hover:bg-dc-surface transition-colors';
                linkBtn.textContent = 'Link';
                linkBtn.title = 'Insert Link';
                linkBtn.addEventListener('click', function () {
                    editorEl.focus();
                    const url = window.prompt('Enter URL (https://...)');
                    if (!url || !isUrl(url)) return;
                    exec('createLink', url);
                    input.value = normalizeHtml(editorEl.innerHTML);
                    markDirtyForInput(input);
                });
                toolbar.appendChild(linkBtn);

                shell.appendChild(toolbar);
                shell.appendChild(editorEl);

                input.style.display = 'none';
                input.insertAdjacentElement('afterend', shell);

                editorEl.addEventListener('input', function () {
                    input.value = normalizeHtml(editorEl.innerHTML);
                    markDirtyForInput(input);
                });
                editorEl.addEventListener('blur', function () {
                    input.value = normalizeHtml(editorEl.innerHTML);
                });

                const editor = {
                    setData: function (value) {
                        editorEl.innerHTML = value || '';
                        input.value = normalizeHtml(editorEl.innerHTML);
                    },
                    getData: function () {
                        return normalizeHtml(editorEl.innerHTML);
                    },
                };

                _richTextEditors.set(input, editor);
            } catch (err) {
                console.warn('[TOC.settings] rich text init failed for', input.getAttribute('data-field'), err);
            }
        }
    }

    function _ensureSectionActionButtons () {
        const detailsBlocks = document.querySelectorAll('#view-settings details');
        detailsBlocks.forEach(function (details) {
            if (!details || details.dataset.sectionSaveBound === '1') return;

            const summary = details.querySelector(':scope > summary');
            if (!summary) return;

            let sectionId = null;
            const candidates = Array.from(details.querySelectorAll('[id^="settings-"]'));
            const modelSection = candidates.find(function (el) {
                return SETTINGS_SECTION_IDS.includes(el.id) || !!el.querySelector('[data-field]');
            });
            if (modelSection) {
                sectionId = modelSection.id;
            }

            const detailsId = details.id || '';
            const hasCustomSaver = typeof SETTINGS_CUSTOM_SECTION_SAVERS[detailsId] === 'function';
            const canSaveSection = true;

            const legacyActionWrap = details.querySelector(':scope > .toc-settings-section-actions');
            if (legacyActionWrap) legacyActionWrap.remove();

            const btn = document.createElement('button');
            btn.type = 'button';
            btn.setAttribute('data-settings-save-detail', detailsId || sectionId || 'generic');
            btn.className = 'ml-3 px-3 py-1 rounded-md border text-[10px] font-bold uppercase tracking-wider transition-colors '
                + 'border-theme/35 text-theme hover:text-white hover:border-theme/60 hover:bg-theme/15';
            if (!canSaveSection) {
                btn.disabled = true;
                btn.title = 'No direct save action for this section';
            }
            btn.textContent = 'Save';

            const chevron = summary.querySelector('i[data-lucide="chevron-down"]');
            if (chevron && chevron.parentNode === summary) {
                summary.insertBefore(btn, chevron);
            } else {
                summary.appendChild(btn);
            }

            if (btn) {
                btn.addEventListener('click', function (evt) {
                    evt.preventDefault();
                    evt.stopPropagation();

                    if (hasCustomSaver) {
                        SETTINGS_CUSTOM_SECTION_SAVERS[detailsId]();
                        return;
                    }

                    if (sectionId) {
                        saveSection(sectionId);
                        return;
                    }

                    // Non-field utility sections fallback to Save All.
                    saveAll();
                });
            }

            details.dataset.sectionSaveBound = '1';
        });
    }

    function _normalizeSettingsPayload (payload) {
        const normalized = Object.assign({}, payload || {});
        if (typeof normalized.meta_keywords === 'string') {
            normalized.meta_keywords = normalized.meta_keywords.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
        }
        return normalized;
    }

    async function saveSection (sectionId) {
        const sectionEl = document.getElementById(sectionId);
        if (!sectionEl) return;

        try {
            _clearFieldErrors();
            _setSectionState(sectionId, 'saving');

            const payload = _normalizeSettingsPayload(gatherFields(sectionId));
            if (!Object.keys(payload).length) {
                _setSectionState(sectionId, 'clean');
                _refreshGlobalDirtyFromSections();
                return;
            }
            if (_settingsVersion) payload.settings_version = _settingsVersion;

            const result = await API('settings/', { method: 'PUT', body: JSON.stringify(payload) });
            _updateSettingsVersionFromResponse(result);
            const updatedFields = Array.isArray(result?.updated_fields) ? result.updated_fields : [];

            if (!updatedFields.length) {
                _setSectionState(sectionId, 'saved');
                setTimeout(function () { _setSectionState(sectionId, 'clean'); }, 1200);
                _captureSectionSnapshot(sectionId);
                _refreshGlobalDirtyFromSections();
                return;
            }

            const fieldMap = _buildFieldSectionMap();
            updatedFields.forEach(function (field) {
                const sid = fieldMap[field] || sectionId;
                _setSectionState(sid, 'saved');
                setTimeout(function () { _setSectionState(sid, 'clean'); }, 1200);
                _captureSectionSnapshot(sid);
            });

            _refreshGlobalDirtyFromSections();
            toast('Section saved', 'success');
        } catch (e) {
            const payload = await _extractErrorPayload(e);
            const err = payload && payload.error;
            if (err && err.type === 'validation') {
                _applyFieldErrors(err.fields || {}, err.sections || {});
                toast(err.message || 'Validation failed', 'error');
            } else if (err && err.type === 'conflict') {
                _updateSettingsVersionFromResponse({ settings_version: err.server_settings_version });
                _restoreSectionSnapshots([sectionId]);
                _setSectionState(sectionId, 'error', 'Stale');
                toast(err.message || 'Settings are out of date. Section rolled back.', 'warning');
                init({ force: true, silent: true });
            } else {
                _setSectionState(sectionId, 'error');
                toast('Section save failed: ' + (e.message || e), 'error');
            }
            _refreshGlobalDirtyFromSections();
        }
    }

    /* ==================================================================
     * LOAD SETTINGS — populates all Tournament-model sections
     * ================================================================== */
    async function loadSettings () {
        try {
            _suspendDirtyTracking = true;
            let s = null;
            try {
                s = await API('settings/');
            } catch (apiErr) {
                const fallback = window.TOC_INITIAL_SETTINGS;
                if (fallback && typeof fallback === 'object' && fallback.basic && fallback.format) {
                    s = fallback;
                } else {
                    throw apiErr;
                }
            }
            if (!s || typeof s !== 'object' || !s.basic || !s.format) {
                const fallback = window.TOC_INITIAL_SETTINGS;
                if (fallback && typeof fallback === 'object' && fallback.basic && fallback.format) {
                    s = fallback;
                } else {
                    throw new Error('Settings payload is missing required sections.');
                }
            }
            if (typeof s?._meta?.settings_version === 'string' && s._meta.settings_version.length > 0) {
                _settingsVersion = s._meta.settings_version;
            }
            // Basic
            const basic = document.getElementById('settings-basic');
            if (basic && s.basic) {
                setVal(basic, 'name', s.basic.name);
                setVal(basic, 'status', s.basic.status);
                setVal(basic, 'description', s.basic.description);
                setVal(basic, 'is_official', s.basic.is_official);
                setVal(basic, 'is_featured', s.basic.is_featured);
            }
            // Media
            const media = document.getElementById('settings-media');
            if (media && s.media) {
                setVal(media, 'promo_video_url', s.media.promo_video_url);
                setVal(media, 'stream_twitch_url', s.media.stream_twitch_url);
                setVal(media, 'stream_youtube_url', s.media.stream_youtube_url);
                if (s.media.banner_image) {
                    const bStat = document.getElementById('banner-status');
                    if (bStat) bStat.textContent = s.media.banner_image.split('/').pop();
                }
                if (s.media.thumbnail_image) {
                    const tStat = document.getElementById('thumbnail-status');
                    if (tStat) tStat.textContent = s.media.thumbnail_image.split('/').pop();
                }
            }
            // Format
            const fmt = document.getElementById('settings-format');
            if (fmt && s.format) {
                setVal(fmt, 'format', s.format.format);
                setVal(fmt, 'participation_type', s.format.participation_type);
                setVal(fmt, 'platform', s.format.platform);
                setVal(fmt, 'mode', s.format.mode);
                setVal(fmt, 'max_participants', s.format.max_participants);
                setVal(fmt, 'min_participants', s.format.min_participants);
                setVal(fmt, 'max_guest_teams', s.format.max_guest_teams);
                setVal(fmt, 'allow_display_name_override', s.format.allow_display_name_override);
                // Sync the mode select trigger
                const modeSel = document.getElementById('setting-mode');
                if (modeSel) modeSel.value = s.format.mode || 'online';
            }
            // Dates
            const dates = document.getElementById('settings-dates');
            if (dates && s.dates) {
                ['registration_start', 'registration_end', 'tournament_start', 'tournament_end'].forEach(f => {
                    if (s.dates[f]) setVal(dates, f, s.dates[f].substring(0, 16));
                });
                if (s.dates.timezone_name) setVal(dates, 'timezone_name', s.dates.timezone_name);
            }
            // Venue
            const venue = document.getElementById('settings-venue');
            if (venue && s.venue) {
                setVal(venue, 'venue_name', s.venue.venue_name);
                setVal(venue, 'venue_city', s.venue.venue_city);
                setVal(venue, 'venue_address', s.venue.venue_address);
                setVal(venue, 'venue_map_url', s.venue.venue_map_url);
            }
            // Fees
            const fees = document.getElementById('settings-fees');
            if (fees && s.fees) {
                setVal(fees, 'has_entry_fee', s.fees.has_entry_fee);
                setVal(fees, 'entry_fee_amount', s.fees.entry_fee_amount);
                setVal(fees, 'entry_fee_currency', s.fees.entry_fee_currency);
                setVal(fees, 'entry_fee_deltacoin', s.fees.entry_fee_deltacoin);
                setVal(fees, 'payment_deadline_hours', s.fees.payment_deadline_hours);
                setVal(fees, 'refund_policy', s.fees.refund_policy);
                setVal(fees, 'refund_policy_text', s.fees.refund_policy_text);
                setVal(fees, 'enable_fee_waiver', s.fees.enable_fee_waiver);
                setVal(fees, 'fee_waiver_top_n_teams', s.fees.fee_waiver_top_n_teams);
            }
            // Prizes
            const prizes = document.getElementById('settings-prizes');
            if (prizes && s.prizes) {
                setVal(prizes, 'prize_pool', s.prizes.prize_pool);
                setVal(prizes, 'prize_currency', s.prizes.prize_currency);
                setVal(prizes, 'prize_deltacoin', s.prizes.prize_deltacoin);
            }
            // Rules
            const rules = document.getElementById('settings-rules');
            if (rules && s.rules) {
                setVal(rules, 'rules_text', s.rules.rules_text);
                setVal(rules, 'terms_and_conditions', s.rules.terms_and_conditions);
                setVal(rules, 'require_terms_acceptance', s.rules.require_terms_acceptance);
                if (s.rules.rules_pdf) {
                    const rs = document.getElementById('rules-pdf-status');
                    if (rs) rs.textContent = s.rules.rules_pdf.split('/').pop();
                }
                if (s.rules.terms_pdf) {
                    const ts = document.getElementById('terms-pdf-status');
                    if (ts) ts.textContent = s.rules.terms_pdf.split('/').pop();
                }
            }
            // Features
            const feat = document.getElementById('settings-features');
            if (feat && s.features) {
                setVal(feat, 'enable_check_in', s.features.enable_check_in);
                setVal(feat, 'enable_dynamic_seeding', s.features.enable_dynamic_seeding);
                setVal(feat, 'enable_live_updates', s.features.enable_live_updates);
                setVal(feat, 'enable_certificates', s.features.enable_certificates);
                setVal(feat, 'enable_challenges', s.features.enable_challenges);
                setVal(feat, 'enable_fan_voting', s.features.enable_fan_voting);
                setVal(feat, 'check_in_minutes_before', s.features.check_in_minutes_before);
                setVal(feat, 'check_in_closes_minutes_before', s.features.check_in_closes_minutes_before);
            }
            // Social & Contact
            const social = document.getElementById('settings-social');
            if (social && s.social) {
                setVal(social, 'contact_email', s.social.contact_email);
                setVal(social, 'contact_phone', s.social.contact_phone);
                setVal(social, 'social_discord', s.social.social_discord);
                setVal(social, 'discord_webhook_url', s.social.discord_webhook_url);
                setVal(social, 'social_twitter', s.social.social_twitter);
                setVal(social, 'social_instagram', s.social.social_instagram);
                setVal(social, 'social_youtube', s.social.social_youtube);
                setVal(social, 'social_website', s.social.social_website);
                setVal(social, 'social_facebook', s.social.social_facebook);
                setVal(social, 'social_tiktok', s.social.social_tiktok);
                setVal(social, 'support_info', s.social.support_info);
            }
            // Waitlist
            const wait = document.getElementById('settings-waitlist');
            if (wait && s.waitlist) {
                setVal(wait, 'auto_forfeit_no_shows', s.waitlist.auto_forfeit_no_shows);
                setVal(wait, 'waitlist_auto_promote', s.waitlist.waitlist_auto_promote);
                setVal(wait, 'enable_no_show_timer', s.waitlist.enable_no_show_timer);
                setVal(wait, 'no_show_timeout_minutes', s.waitlist.no_show_timeout_minutes);
                setVal(wait, 'max_waitlist_size', s.waitlist.max_waitlist_size);
                syncNoShowVisibility();
            }
            // SEO
            const seo = document.getElementById('settings-seo');
            if (seo && s.seo) {
                setVal(seo, 'meta_description', s.seo.meta_description);
                const kw = s.seo.meta_keywords;
                setVal(seo, 'meta_keywords', Array.isArray(kw) ? kw.join(', ') : kw || '');
            }
            // Sync conditional sections
            _syncConditionalVisibility();
            return true;
        } catch (e) {
            console.warn('[TOC.settings] loadSettings failed', e);
            return false;
        } finally {
            _suspendDirtyTracking = false;
        }
    }

    /* ==================================================================
     * SAVE ALL — gathers all Tournament-model fields and PUTs them
     * ================================================================== */
    async function saveAll () {
        const saveBtn = document.getElementById('btn-settings-save-all');
        const oldText = saveBtn ? saveBtn.innerHTML : '';
        try {
            _clearFieldErrors();

            if (saveBtn) {
                saveBtn.disabled = true;
                saveBtn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Saving...';
            }

            const dirtySections = _dirtySections();
            dirtySections.forEach(function (id) { _setSectionState(id, 'saving'); });

            const payload = _normalizeSettingsPayload(Object.assign({},
                gatherFields('settings-basic'),
                gatherFields('settings-media'),
                gatherFields('settings-format'),
                gatherFields('settings-dates'),
                gatherFields('settings-venue'),
                gatherFields('settings-fees'),
                gatherFields('settings-prizes'),
                gatherFields('settings-rules'),
                gatherFields('settings-features'),
                gatherFields('settings-social'),
                gatherFields('settings-waitlist'),
                gatherFields('settings-seo'),
            ));
            if (_settingsVersion) payload.settings_version = _settingsVersion;

            const result = await API('settings/', { method: 'PUT', body: JSON.stringify(payload) });
            _updateSettingsVersionFromResponse(result);
            toast('Settings saved', 'success');
            _markSettingsDirty(false);

            const fieldMap = _buildFieldSectionMap();
            const updatedFields = Array.isArray(result?.updated_fields) ? result.updated_fields : [];
            const savedSections = new Set();
            updatedFields.forEach(function (field) {
                if (fieldMap[field]) savedSections.add(fieldMap[field]);
            });
            if (!savedSections.size) {
                dirtySections.forEach(function (id) { savedSections.add(id); });
            }
            savedSections.forEach(function (id) { _setSectionState(id, 'saved'); });
            setTimeout(function () {
                savedSections.forEach(function (id) { _setSectionState(id, 'clean'); });
            }, 1600);
            _captureAllSectionSnapshots();

            // Update sidebar context badges to reflect saved values
            _syncSidebarBadges(payload);
        } catch (e) {
            const payload = await _extractErrorPayload(e);
            const err = payload && payload.error;
            if (err && err.type === 'validation') {
                _applyFieldErrors(err.fields || {}, err.sections || {});
                toast(err.message || 'Validation failed', 'error');
            } else if (err && err.type === 'conflict') {
                const dirtySections = _dirtySections();
                _updateSettingsVersionFromResponse({ settings_version: err.server_settings_version });
                _restoreSectionSnapshots(dirtySections);
                dirtySections.forEach(function (id) { _setSectionState(id, 'error', 'Stale'); });
                toast(err.message || 'Settings changed elsewhere. Unsaved edits were rolled back.', 'warning');
                init({ force: true, silent: true });
            } else {
                _dirtySections().forEach(function (id) { _setSectionState(id, 'error'); });
                toast('Save failed: ' + (e.message || e), 'error');
            }
        } finally {
            if (saveBtn) {
                saveBtn.innerHTML = '<i data-lucide="save" class="w-4 h-4"></i> Save All Changes';
                if (typeof lucide !== 'undefined') {
                    try { lucide.createIcons(); } catch (err) { /* no-op */ }
                }
                saveBtn.disabled = !_settingsDirty;
            }
        }
    }

    function _syncSidebarBadges (payload) {
        if (payload.participation_type) {
            const el = document.getElementById('sidebar-badge-participation');
            if (el) {
                const isSolo = payload.participation_type === 'solo';
                const icon = el.querySelector('i[data-lucide]');
                if (icon) {
                    icon.setAttribute('data-lucide', isSolo ? 'user' : 'users');
                    if (typeof lucide !== 'undefined') lucide.createIcons();
                }
                const text = el.childNodes[el.childNodes.length - 1];
                if (text && text.nodeType === Node.TEXT_NODE) {
                    text.textContent = ' ' + payload.participation_type.charAt(0).toUpperCase() + payload.participation_type.slice(1);
                }
            }
        }
        if (payload.format) {
            const el = document.getElementById('sidebar-badge-format');
            if (el) {
                const display = payload.format.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                const text = el.childNodes[el.childNodes.length - 1];
                if (text && text.nodeType === Node.TEXT_NODE) {
                    text.textContent = ' ' + display;
                }
            }
        }
        if (payload.status) {
            const el = document.getElementById('sidebar-badge-status');
            if (el) {
                const display = payload.status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                const text = el.childNodes[el.childNodes.length - 1];
                if (text && text.nodeType === Node.TEXT_NODE) {
                    text.textContent = display;
                }
            }
        }
    }

    /* ==================================================================
     * CONDITIONAL SECTION VISIBILITY
     * ================================================================== */
    function syncModeVisibility () {
        const mode = document.getElementById('setting-mode')?.value || 'online';
        const venueSection = document.getElementById('settings-venue-section');
        if (venueSection) venueSection.classList.toggle('hidden', mode === 'online');
    }

    function syncCheckInVisibility () {
        const on = document.getElementById('toggle-check-in')?.checked || false;
        const win = document.getElementById('check-in-window');
        if (win) win.classList.toggle('hidden', !on);
    }

    function syncNoShowVisibility () {
        const on = document.getElementById('toggle-no-show-timer')?.checked || false;
        const det = document.getElementById('no-show-timer-details');
        if (det) det.classList.toggle('hidden', !on);
    }

    function syncFeeVisibility () {
        const on = document.getElementById('toggle-entry-fee')?.checked || false;
        const det = document.getElementById('fee-details');
        if (det) det.classList.toggle('hidden', !on);
    }

    /* ==================================================================
     * GAME-AWARE VISIBILITY
     * ================================================================== */
    function applyGameAwareVisibility () {
        const cat = CFG().gameCategory || 'OTHER';
        const gt  = CFG().gameType || 'TEAM_VS_TEAM';

        const isBR = (cat === 'BR' || gt === 'BATTLE_ROYALE' || gt === 'FREE_FOR_ALL');
        // Sports/Fighting/CCG games typically don't have map pools
        const noMaps = ['SPORTS', 'FIGHTING', 'CCG'].includes(cat) || gt === '1V1';

        // BR Scoring: only for BR games
        const brSection = document.getElementById('settings-br-section');
        if (brSection) brSection.classList.toggle('hidden', !isBR);

        // Map Pool: hide for games without maps
        const mapSection = document.getElementById('settings-mappool-section');
        if (mapSection) mapSection.classList.toggle('hidden', noMaps);
    }

    /* ==================================================================
     * GAME CONFIG (GameMatchConfig model)
     * ================================================================== */
    async function loadGameConfig () {
        try {
            const gc = await API('settings/game-config/');
            if (!gc) return;
            const c = document.getElementById('settings-game-config');
            if (c) {
                setVal(c, 'default_match_format', gc.default_match_format);
                setVal(c, 'enable_veto', gc.enable_veto);
                setVal(c, 'veto_type', gc.veto_type);
            }
            vetoSequence = gc.veto_sequence || [];
            renderVetoSteps();
            syncVetoVisibility();
        } catch (e) { console.warn('[TOC.settings] loadGameConfig failed', e); }
    }

    function syncVetoVisibility () {
        const on = document.getElementById('toggle-veto')?.checked || false;
        const sel = document.getElementById('veto-type-select');
        const builder = document.getElementById('veto-builder-section');
        if (sel) sel.classList.toggle('hidden', !on);
        if (builder) builder.classList.toggle('hidden', !on);
    }

    async function saveGameConfig () {
        try {
            const c = document.getElementById('settings-game-config');
            const payload = {
                default_match_format: getVal(c, 'default_match_format'),
                enable_veto: getVal(c, 'enable_veto'),
                veto_type: getVal(c, 'veto_type'),
                veto_sequence: vetoSequence,
            };
            await API('settings/game-config/', { method: 'PUT', body: JSON.stringify(payload) });
            toast('Game config saved', 'success');
            _markSettingsDirty(false);
        } catch (e) { toast('Game config save failed', 'error'); }
    }

    /* ── Veto Builder ── */
    function addVetoStep (action) {
        vetoSequence.push({ action: action, team: 'higher_seed' });
        renderVetoSteps();
    }

    function removeVetoStep (idx) {
        vetoSequence.splice(idx, 1);
        renderVetoSteps();
    }

    function changeVetoTeam (idx, team) {
        if (vetoSequence[idx]) vetoSequence[idx].team = team;
    }

    function renderVetoSteps () {
        const list = document.getElementById('veto-steps-list');
        if (!list) return;
        if (!vetoSequence.length) {
            list.innerHTML = '<p class="text-xs text-dc-text italic">No steps defined. Add bans/picks above.</p>';
            return;
        }
        list.innerHTML = vetoSequence.map((s, i) => {
            var badge = s.action === 'ban' ? 'bg-dc-danger/20 text-dc-danger' : s.action === 'pick' ? 'bg-dc-success/20 text-dc-success' : 'bg-dc-warning/20 text-dc-warning';
            return '<div class="flex items-center gap-2 py-1.5 px-3 bg-dc-surface/50 rounded-lg border border-dc-border">'
                + '<span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded ' + badge + '">' + esc(s.action) + '</span>'
                + '<select onchange="TOC.settings.changeVetoTeam(' + i + ', this.value)" class="flex-1 bg-dc-surface border border-dc-border rounded px-2 py-1 text-xs text-dc-textBright">'
                + '<option value="higher_seed"' + (s.team === 'higher_seed' ? ' selected' : '') + '>Higher Seed</option>'
                + '<option value="lower_seed"' + (s.team === 'lower_seed' ? ' selected' : '') + '>Lower Seed</option>'
                + '</select>'
                + '<button onclick="TOC.settings.removeVetoStep(' + i + ')" class="p-1 text-dc-danger hover:bg-dc-danger/10 rounded" title="Remove">&times;</button>'
                + '</div>';
        }).join('');
    }

    /* ==================================================================
     * MAP POOL
     * ================================================================== */
    async function loadMapPool () {
        try {
            const maps = await API('settings/map-pool/');
            const list = document.getElementById('map-pool-list');
            if (!list) return;
            if (!maps || !maps.length) {
                list.innerHTML = '<p class="text-xs text-dc-text italic text-center py-4">No maps configured.</p>';
                return;
            }
            list.innerHTML = maps.map(m =>
                '<div class="flex items-center justify-between py-2 px-3 bg-dc-surface/50 rounded-lg border border-dc-border">'
                + '<div class="flex items-center gap-2">'
                + '<span class="w-2 h-2 rounded-full ' + (m.is_active ? 'bg-dc-success' : 'bg-dc-text/30') + '"></span>'
                + '<span class="text-sm text-white font-medium">' + esc(m.map_name) + '</span>'
                + (m.map_code ? '<span class="text-[10px] text-dc-text font-mono">' + esc(m.map_code) + '</span>' : '')
                + '</div>'
                + '<div class="flex items-center gap-1">'
                + '<button onclick="TOC.settings.toggleMap(\'' + m.id + '\', ' + !m.is_active + ')" class="px-2 py-1 text-[10px] border border-dc-border rounded hover:bg-dc-surface transition-colors text-dc-text">' + (m.is_active ? 'Disable' : 'Enable') + '</button>'
                + '<button onclick="TOC.settings.deleteMap(\'' + m.id + '\')" class="px-2 py-1 text-[10px] border border-dc-danger/30 text-dc-danger rounded hover:bg-dc-danger/10 transition-colors">Delete</button>'
                + '</div></div>'
            ).join('');
        } catch (e) { console.warn('[TOC.settings] loadMapPool failed', e); }
    }

    function openAddMap () {
        showOverlay('Add Map', '<div class="space-y-4">'
            + '<div><label class="block text-xs text-dc-text mb-1">Map Name</label>'
            + '<input id="new-map-name" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
            + '<div><label class="block text-xs text-dc-text mb-1">Map Code</label>'
            + '<input id="new-map-code" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
            + '<button onclick="TOC.settings.confirmAddMap()" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Add Map</button>'
            + '</div>');
    }

    async function confirmAddMap () {
        var name = document.getElementById('new-map-name')?.value?.trim();
        if (!name) return;
        await API('settings/map-pool/', { method: 'POST', body: JSON.stringify({ map_name: name, map_code: document.getElementById('new-map-code')?.value?.trim() || '' }) });
        closeOverlay(); loadMapPool(); toast('Map added', 'success');
    }

    async function toggleMap (id, active) {
        await API('settings/map-pool/' + id + '/', { method: 'PATCH', body: JSON.stringify({ is_active: active }) });
        loadMapPool();
    }

    async function deleteMap (id) {
        if (!confirm('Delete this map?')) return;
        await API('settings/map-pool/' + id + '/', { method: 'DELETE' });
        loadMapPool(); toast('Map deleted', 'success');
    }

    /* ==================================================================
     * SERVER REGIONS
     * ================================================================== */
    async function loadRegions () {
        try {
            const regions = await API('settings/regions/');
            const list = document.getElementById('region-list');
            if (!list) return;
            if (!regions || !regions.length) {
                list.innerHTML = '<p class="text-xs text-dc-text italic text-center py-4">No regions configured.</p>';
                return;
            }
            list.innerHTML = regions.map(r =>
                '<div class="flex items-center justify-between py-2 px-3 bg-dc-surface/50 rounded-lg border border-dc-border">'
                + '<div><span class="text-sm text-white font-medium">' + esc(r.name) + '</span>'
                + ' <span class="text-[10px] text-dc-text font-mono">' + esc(r.code) + '</span></div>'
                + '<button onclick="TOC.settings.deleteRegion(\'' + r.id + '\')" class="px-2 py-1 text-[10px] border border-dc-danger/30 text-dc-danger rounded hover:bg-dc-danger/10 transition-colors">Delete</button>'
                + '</div>'
            ).join('');
        } catch (e) { console.warn('[TOC.settings] loadRegions failed', e); }
    }

    function openAddRegion () {
        showOverlay('Add Region', '<div class="space-y-4">'
            + '<div><label class="block text-xs text-dc-text mb-1">Region Name</label>'
            + '<input id="new-region-name" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
            + '<div><label class="block text-xs text-dc-text mb-1">Region Code</label>'
            + '<input id="new-region-code" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
            + '<button onclick="TOC.settings.confirmAddRegion()" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Add Region</button>'
            + '</div>');
    }

    async function confirmAddRegion () {
        var name = document.getElementById('new-region-name')?.value?.trim();
        var code = document.getElementById('new-region-code')?.value?.trim();
        if (!name || !code) return;
        await API('settings/regions/', { method: 'POST', body: JSON.stringify({ name: name, code: code }) });
        closeOverlay(); loadRegions(); toast('Region added', 'success');
    }

    async function deleteRegion (id) {
        if (!confirm('Delete this region?')) return;
        await API('settings/regions/' + id + '/', { method: 'DELETE' });
        loadRegions(); toast('Region deleted', 'success');
    }

    /* ==================================================================
     * RULEBOOK VERSIONS
     * ================================================================== */
    async function loadRulebook () {
        try {
            const versions = await API('settings/rulebook/');
            rulebookVersions = versions || [];
            const list = document.getElementById('rulebook-list');
            if (!list) return;
            if (!rulebookVersions.length) {
                list.innerHTML = '<p class="text-xs text-dc-text italic text-center py-4">No rulebook versions yet.</p>';
                return;
            }
            list.innerHTML = rulebookVersions.map(v =>
                '<div class="flex items-center justify-between py-2 px-3 bg-dc-surface/50 rounded-lg border border-dc-border">'
                + '<div class="flex items-center gap-2">'
                + '<span class="text-sm text-white font-bold">v' + esc(v.version) + '</span>'
                + (v.is_active ? '<span class="text-[10px] bg-dc-success/20 text-dc-success px-2 py-0.5 rounded-full">Active</span>' : '')
                + (v.changelog ? '<span class="text-xs text-dc-text truncate max-w-[200px]">' + esc(v.changelog) + '</span>' : '')
                + '</div>'
                + '<div class="flex items-center gap-1">'
                + '<button onclick="TOC.settings.editRulebook(\'' + v.id + '\')" class="px-2 py-1 text-[10px] border border-dc-border rounded hover:bg-dc-surface transition-colors text-dc-text">Edit</button>'
                + (!v.is_active ? '<button onclick="TOC.settings.publishRulebook(\'' + v.id + '\')" class="px-2 py-1 text-[10px] border border-dc-success/30 text-dc-success rounded hover:bg-dc-success/10 transition-colors">Publish</button>' : '')
                + '</div></div>'
            ).join('');
        } catch (e) { console.warn('[TOC.settings] loadRulebook failed', e); }
    }

    function openCreateRulebook () {
        showOverlay('New Rulebook Version', '<div class="space-y-4">'
            + '<div><label class="block text-xs text-dc-text mb-1">Version (e.g. 1.0, 2.0)</label>'
            + '<input id="new-rb-version" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
            + '<div><label class="block text-xs text-dc-text mb-1">Content (Markdown/HTML)</label>'
            + '<textarea id="new-rb-content" rows="8" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright font-mono focus:outline-none focus:border-theme/50"></textarea></div>'
            + '<div class="grid grid-cols-2 gap-3">'
            + '<div><label class="block text-xs text-dc-text mb-1">Change Type</label>'
            + '<select id="new-rb-change-type" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">'
            + '<option value="minor">Minor (formatting, typo)</option><option value="material">Material (rule change)</option></select></div>'
            + '<div class="flex items-end pb-1"><label class="flex items-center gap-2 text-sm text-dc-text cursor-pointer"><input id="new-rb-reconsent" type="checkbox" class="rounded border-dc-border bg-dc-surface text-theme"> Require Re-Consent</label></div></div>'
            + '<div><label class="block text-xs text-dc-text mb-1">Changelog</label>'
            + '<input id="new-rb-changelog" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
            + '<button onclick="TOC.settings.confirmCreateRulebook()" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Create Version</button>'
            + '</div>');
    }

    async function confirmCreateRulebook () {
        var v = document.getElementById('new-rb-version')?.value?.trim();
        if (!v) return;
        await API('settings/rulebook/', { method: 'POST', body: JSON.stringify({
            version: v,
            content: document.getElementById('new-rb-content')?.value || '',
            changelog: document.getElementById('new-rb-changelog')?.value?.trim() || '',
            change_type: document.getElementById('new-rb-change-type')?.value || 'minor',
            require_reconsent: document.getElementById('new-rb-reconsent')?.checked || false,
        }) });
        closeOverlay(); loadRulebook(); toast('Rulebook created', 'success');
    }

    function editRulebook (versionId) {
        var v = rulebookVersions.find(function (r) { return String(r.id) === String(versionId); });
        if (!v) return;
        showOverlay('Edit Rulebook v' + esc(v.version), '<div class="space-y-4">'
            + '<div><label class="block text-xs text-dc-text mb-1">Content (Markdown/HTML)</label>'
            + '<textarea id="edit-rb-content" rows="10" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright font-mono focus:outline-none focus:border-theme/50">' + esc(v.content || '') + '</textarea></div>'
            + '<div class="grid grid-cols-2 gap-3">'
            + '<div><label class="block text-xs text-dc-text mb-1">Change Type</label>'
            + '<select id="edit-rb-change-type" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">'
            + '<option value="minor">Minor</option><option value="material">Material</option></select></div>'
            + '<div class="flex items-end pb-1"><label class="flex items-center gap-2 text-sm text-dc-text cursor-pointer"><input id="edit-rb-reconsent" type="checkbox" class="rounded border-dc-border bg-dc-surface text-theme"> Require Re-Consent</label></div></div>'
            + '<div><label class="block text-xs text-dc-text mb-1">Changelog</label>'
            + '<input id="edit-rb-changelog" type="text" value="' + esc(v.changelog || '') + '" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
            + '<button onclick="TOC.settings.confirmEditRulebook(\'' + versionId + '\')" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Save Changes</button>'
            + '</div>');
    }

    async function confirmEditRulebook (versionId) {
        try {
            await API('settings/rulebook/' + versionId + '/', { method: 'PUT', body: JSON.stringify({
                content: document.getElementById('edit-rb-content')?.value || '',
                changelog: document.getElementById('edit-rb-changelog')?.value?.trim() || '',
                change_type: document.getElementById('edit-rb-change-type')?.value || 'minor',
                require_reconsent: document.getElementById('edit-rb-reconsent')?.checked || false,
            }) });
            closeOverlay(); loadRulebook(); toast('Rulebook updated', 'success');
        } catch (e) { toast('Update failed', 'error'); }
    }

    function publishRulebook (versionId) {
        TOC.dangerConfirm({
            title: 'Publish Rulebook Version',
            message: 'This version will become active and all other versions will be deactivated. Participants may be prompted to re-acknowledge.',
            confirmText: 'Publish Version',
            variant: 'warning',
            onConfirm: async function () {
                await API('settings/rulebook/' + versionId + '/publish/', { method: 'POST' });
                loadRulebook(); toast('Rulebook published', 'success');
            },
        });
    }

    /* ==================================================================
     * BR SCORING
     * ================================================================== */
    async function loadBRScoring () {
        try {
            const br = await API('settings/br-scoring/');
            if (!br) return;
            const c = document.getElementById('settings-br-scoring');
            if (!c) return;
            setVal(c, 'kill_points', br.kill_points);
            var pp = br.placement_points;
            setVal(c, 'placement_points', typeof pp === 'object' ? JSON.stringify(pp, null, 2) : pp || '');
        } catch (e) { /* no BR scoring configured — ok */ }
    }

    async function saveBRScoring () {
        try {
            var c = document.getElementById('settings-br-scoring');
            var ppRaw = getVal(c, 'placement_points');
            var pp = {};
            try { pp = JSON.parse(ppRaw); } catch (e) { toast('Invalid JSON in placement points', 'error'); return; }
            await API('settings/br-scoring/', { method: 'PUT', body: JSON.stringify({
                kill_points: getVal(c, 'kill_points'),
                placement_points: pp,
            }) });
            toast('BR Scoring saved', 'success');
            _markSettingsDirty(false);
        } catch (e) { toast('BR Scoring save failed', 'error'); }
    }

    /* ==================================================================
     * PAYMENT METHODS (TournamentPaymentMethod CRUD)
     * ================================================================== */
    async function loadPaymentMethods () {
        try {
            const methods = await API('settings/payment-methods/');
            paymentMethods = methods || [];
            var list = document.getElementById('payment-methods-list');
            if (!list) return;
            if (!paymentMethods.length) {
                list.innerHTML = '<p class="text-xs text-dc-text italic text-center py-4">No payment methods configured.</p>';
                return;
            }

            function methodLabel (method) {
                var labels = {
                    bkash: 'bKash',
                    nagad: 'Nagad',
                    rocket: 'Rocket',
                    bank_transfer: 'Bank Transfer',
                    deltacoin: 'DeltaCoin',
                };
                return labels[method] || (method ? method.charAt(0).toUpperCase() + method.slice(1) : 'Method');
            }

            function summarizeAccount (m) {
                var raw = m.account_number || m.bank_account_number || m.bank_name || '';
                if (!raw) return '';
                var text = String(raw);
                if (/^\d{8,}$/.test(text)) {
                    return '••••' + text.slice(-4);
                }
                return text;
            }

            list.innerHTML = paymentMethods.map(function (m) {
                var label = methodLabel(m.method);
                var acct = summarizeAccount(m);
                return '<div class="flex items-center justify-between py-2 px-3 bg-dc-surface/50 rounded-lg border border-dc-border gap-2">'
                    + '<div class="flex items-center gap-2">'
                    + '<span class="w-2 h-2 rounded-full ' + (m.is_enabled ? 'bg-dc-success' : 'bg-dc-text/30') + '"></span>'
                    + '<span class="text-[11px] px-2 py-0.5 rounded-full border border-dc-border text-dc-textBright bg-dc-bg/70">' + esc(label) + '</span>'
                    + (acct ? '<span class="text-xs text-dc-text">' + esc(acct) + '</span>' : '')
                    + '<span class="text-[10px] ' + (m.is_enabled ? 'text-dc-success' : 'text-dc-text') + '">' + (m.is_enabled ? 'Enabled' : 'Disabled') + '</span>'
                    + '</div>'
                    + '<div class="flex items-center gap-1">'
                    + '<button onclick="TOC.settings.editPaymentMethod(' + m.id + ')" class="px-2 py-1 text-[10px] border border-dc-border rounded hover:bg-dc-surface transition-colors text-dc-text">Edit</button>'
                    + '<button onclick="TOC.settings.deletePaymentMethod(' + m.id + ')" class="px-2 py-1 text-[10px] border border-dc-danger/30 text-dc-danger rounded hover:bg-dc-danger/10 transition-colors">Delete</button>'
                    + '</div></div>';
            }).join('');
        } catch (e) { console.warn('[TOC.settings] loadPaymentMethods failed', e); }
    }

    function openAddPaymentMethod () {
        showOverlay('Add Payment Method', '<div class="space-y-4">'
            + '<div><label class="block text-xs text-dc-text mb-1">Provider</label>'
            + '<select id="pm-method" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" onchange="TOC.settings.syncPaymentMethodFields()">'
            + '<option value="bkash">bKash</option><option value="nagad">Nagad</option><option value="rocket">Rocket</option>'
            + '<option value="bank_transfer">Bank Transfer</option><option value="deltacoin">DeltaCoin</option></select></div>'
            + '<div id="pm-fields"></div>'
            + '<div class="flex items-center gap-2">'
            + '<button id="pm-submit-add" onclick="TOC.settings.confirmAddPaymentMethod()" class="flex-1 py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Add Method</button>'
            + '<button onclick="TOC.settings.dismissPaymentOverlay()" class="px-4 py-2 rounded-lg border border-dc-border text-dc-text text-sm hover:bg-dc-surface transition-colors">Cancel</button>'
            + '</div>'
            + '</div>');
        syncPaymentMethodFields();
    }

    function dismissPaymentOverlay () {
        closeOverlay();
    }

    function syncPaymentMethodFields (seed) {
        var method = document.getElementById('pm-method')?.value || 'bkash';
        var container = document.getElementById('pm-fields');
        if (!container) return;
        var s = seed || {};
        var hint = {
            bkash: 'Use the same number participants send payment from to reduce review friction.',
            nagad: 'Keep account name identical to your KYC/legal display name.',
            rocket: 'Agent wallets are recommended for high-volume tournaments.',
            bank_transfer: 'Include SWIFT and routing details for international/local transfers.',
            deltacoin: 'Add short payout notes if you require memo/reference format.',
        };
        var html = '';
        html += '<div class="mb-2 text-[11px] text-dc-text bg-dc-bg/60 border border-dc-border rounded-lg px-3 py-2">'
            + '<span class="text-dc-textBright font-semibold">Tip:</span> ' + esc(hint[method] || 'Complete all required fields to avoid failed payments.')
            + '</div>';
        if (method === 'bkash' || method === 'nagad' || method === 'rocket') {
            var prefix = method;
            html += '<div class="space-y-3">'
                + '<div><label class="block text-xs text-dc-text mb-1">Account Number</label>'
                + '<input id="pm-account-number" type="text" value="' + esc(s[prefix + '_account_number'] || '') + '" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" placeholder="01XXXXXXXXX" autocomplete="off"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Account Name</label>'
                + '<input id="pm-account-name" type="text" value="' + esc(s[prefix + '_account_name'] || '') + '" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" autocomplete="name"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Account Type</label>'
                + '<select id="pm-account-type" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">'
                + '<option value="personal">Personal</option><option value="merchant">Merchant</option><option value="agent">Agent</option></select></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Instructions</label>'
                + '<textarea id="pm-instructions" rows="2" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">' + esc(s[prefix + '_instructions'] || '') + '</textarea></div>'
                + '<label class="flex items-center gap-2 text-sm text-dc-text cursor-pointer"><input id="pm-ref-required" type="checkbox" ' + ((s[prefix + '_reference_required'] ?? true) ? 'checked' : '') + ' class="rounded border-dc-border bg-dc-surface text-theme"> Reference Required</label>'
                + '</div>';
        } else if (method === 'bank_transfer') {
            html += '<div class="space-y-3">'
                + '<div><label class="block text-xs text-dc-text mb-1">Bank Name</label><input id="pm-bank-name" value="' + esc(s.bank_name || '') + '" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Branch</label><input id="pm-bank-branch" value="' + esc(s.bank_branch || '') + '" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Account Number</label><input id="pm-bank-acct" value="' + esc(s.bank_account_number || '') + '" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Account Name</label><input id="pm-bank-acct-name" value="' + esc(s.bank_account_name || '') + '" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Routing Number</label><input id="pm-bank-routing" value="' + esc(s.bank_routing_number || '') + '" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">SWIFT Code</label><input id="pm-bank-swift" value="' + esc(s.bank_swift_code || '') + '" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Instructions</label><textarea id="pm-bank-instructions" rows="2" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">' + esc(s.bank_instructions || '') + '</textarea></div>'
                + '<label class="flex items-center gap-2 text-sm text-dc-text cursor-pointer"><input id="pm-bank-ref-required" type="checkbox" ' + ((s.bank_reference_required ?? true) ? 'checked' : '') + ' class="rounded border-dc-border bg-dc-surface text-theme"> Reference Required</label>'
                + '</div>';
        } else {
            html += '<div><label class="block text-xs text-dc-text mb-1">Instructions</label>'
                + '<textarea id="pm-dc-instructions" rows="2" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">' + esc(s.deltacoin_instructions || '') + '</textarea></div>';
        }
        container.innerHTML = html;
        if (method === 'bkash' || method === 'nagad' || method === 'rocket') {
            var typeEl = document.getElementById('pm-account-type');
            if (typeEl) typeEl.value = s[method + '_account_type'] || 'personal';
        }
    }

    function buildPaymentMethodPayload (method) {
        var payload = {};
        if (method === 'bkash' || method === 'nagad' || method === 'rocket') {
            payload[method + '_account_number'] = document.getElementById('pm-account-number')?.value || '';
            payload[method + '_account_name'] = document.getElementById('pm-account-name')?.value || '';
            payload[method + '_account_type'] = document.getElementById('pm-account-type')?.value || 'personal';
            payload[method + '_instructions'] = document.getElementById('pm-instructions')?.value || '';
            payload[method + '_reference_required'] = document.getElementById('pm-ref-required')?.checked ?? true;
        } else if (method === 'bank_transfer') {
            payload.bank_name = document.getElementById('pm-bank-name')?.value || '';
            payload.bank_branch = document.getElementById('pm-bank-branch')?.value || '';
            payload.bank_account_number = document.getElementById('pm-bank-acct')?.value || '';
            payload.bank_account_name = document.getElementById('pm-bank-acct-name')?.value || '';
            payload.bank_routing_number = document.getElementById('pm-bank-routing')?.value || '';
            payload.bank_swift_code = document.getElementById('pm-bank-swift')?.value || '';
            payload.bank_instructions = document.getElementById('pm-bank-instructions')?.value || '';
            payload.bank_reference_required = document.getElementById('pm-bank-ref-required')?.checked ?? true;
        } else {
            payload.deltacoin_instructions = document.getElementById('pm-dc-instructions')?.value || '';
        }
        return payload;
    }

    function validatePaymentMethodPayload (method, payload) {
        function markInvalid (id, message) {
            var el = document.getElementById(id);
            if (!el) {
                toast(message, 'error');
                return false;
            }
            el.classList.add('border-dc-danger');
            el.focus();
            toast(message, 'error');
            return false;
        }

        ['pm-account-number', 'pm-account-name', 'pm-bank-name', 'pm-bank-acct', 'pm-bank-acct-name'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.classList.remove('border-dc-danger');
        });

        if (method === 'bkash' || method === 'nagad' || method === 'rocket') {
            if (!String(payload[method + '_account_number'] || '').trim()) {
                return markInvalid('pm-account-number', 'Account number is required');
            }
            if (!String(payload[method + '_account_name'] || '').trim()) {
                return markInvalid('pm-account-name', 'Account name is required');
            }
        }

        if (method === 'bank_transfer') {
            if (!String(payload.bank_name || '').trim()) {
                return markInvalid('pm-bank-name', 'Bank name is required');
            }
            if (!String(payload.bank_account_number || '').trim()) {
                return markInvalid('pm-bank-acct', 'Bank account number is required');
            }
            if (!String(payload.bank_account_name || '').trim()) {
                return markInvalid('pm-bank-acct-name', 'Bank account name is required');
            }
        }

        return true;
    }

    async function confirmAddPaymentMethod () {
        var method = document.getElementById('pm-method')?.value;
        if (!method) return;
        var payload = { method: method };
        Object.assign(payload, buildPaymentMethodPayload(method));
        if (!validatePaymentMethodPayload(method, payload)) return;

        var btn = document.getElementById('pm-submit-add');
        var previousText = btn ? btn.textContent : '';
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Adding...';
            btn.classList.add('opacity-70');
        }
        try {
            await API('settings/payment-methods/', { method: 'POST', body: JSON.stringify(payload) });
            closeOverlay(); loadPaymentMethods(); toast('Payment method added', 'success');
        } catch (e) {
            toast('Failed to add payment method', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = previousText || 'Add Method';
                btn.classList.remove('opacity-70');
            }
        }
    }

    function editPaymentMethod (id) {
        var m = paymentMethods.find(function (x) { return Number(x.id) === Number(id); });
        if (!m) { toast('Payment method not found', 'error'); return; }

        var method = m.method || 'deltacoin';
        var labels = { bkash: 'bKash', nagad: 'Nagad', rocket: 'Rocket', bank_transfer: 'Bank Transfer', deltacoin: 'DeltaCoin' };
        var label = labels[method] || (method.charAt(0).toUpperCase() + method.slice(1));
        showOverlay('Edit Payment Method: ' + label, '<div class="space-y-4">'
            + '<div><label class="block text-xs text-dc-text mb-1">Provider</label>'
            + '<input type="text" readonly value="' + esc(label) + '" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-text"></div>'
            + '<select id="pm-method" class="hidden"><option value="' + esc(method) + '" selected>' + esc(method) + '</option></select>'
            + '<div id="pm-fields"></div>'
            + '<div class="flex items-center justify-between gap-3">'
            + '<label class="flex items-center gap-2 text-sm text-dc-text cursor-pointer"><input id="pm-is-enabled" type="checkbox" ' + (m.is_enabled ? 'checked' : '') + ' class="rounded border-dc-border bg-dc-surface text-theme"> Enabled</label>'
            + '<div class="flex items-center gap-2">'
            + '<button onclick="TOC.settings.dismissPaymentOverlay()" class="px-4 py-2 rounded-lg border border-dc-border text-dc-text text-sm hover:bg-dc-surface transition-colors">Cancel</button>'
            + '<button id="pm-submit-edit" onclick="TOC.settings.confirmEditPaymentMethod(' + Number(id) + ')" class="px-4 py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Save Changes</button>'
            + '</div>'
            + '</div>'
            + '</div>');
        syncPaymentMethodFields(m);
    }

    async function confirmEditPaymentMethod (id) {
        var method = document.getElementById('pm-method')?.value;
        if (!method) return;
        var payload = {
            is_enabled: document.getElementById('pm-is-enabled')?.checked ?? true,
        };
        Object.assign(payload, buildPaymentMethodPayload(method));
        if (!validatePaymentMethodPayload(method, payload)) return;

        var btn = document.getElementById('pm-submit-edit');
        var previousText = btn ? btn.textContent : '';
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Saving...';
            btn.classList.add('opacity-70');
        }
        try {
            await API('settings/payment-methods/' + id + '/', { method: 'PUT', body: JSON.stringify(payload) });
            closeOverlay();
            loadPaymentMethods();
            toast('Payment method updated', 'success');
        } catch (e) {
            toast('Update failed', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = previousText || 'Save Changes';
                btn.classList.remove('opacity-70');
            }
        }
    }

    async function deletePaymentMethod (id) {
        if (!confirm('Delete this payment method?')) return;
        try {
            await API('settings/payment-methods/' + id + '/', { method: 'DELETE' });
            loadPaymentMethods(); toast('Payment method deleted', 'success');
        } catch (e) { toast('Delete failed', 'error'); }
    }

    /* ==================================================================
     * FILE UPLOAD (banner, thumbnail, rules_pdf, terms_pdf)
     * ================================================================== */
    async function uploadFile (fieldName, inputEl) {
        if (!inputEl.files || !inputEl.files[0]) return;
        var file = inputEl.files[0];
        var formData = new FormData();
        formData.append('field', fieldName);
        formData.append('file', file);
        try {
            var resp = await fetch(CFG().apiBase + '/settings/upload/', {
                method: 'POST',
                headers: { 'X-CSRFToken': CFG().csrfToken },
                body: formData,
            });
            if (!resp.ok) throw new Error('Upload failed');
            var data = await resp.json();
            // Update status label
            var statusMap = {
                'banner_image': 'banner-status',
                'thumbnail_image': 'thumbnail-status',
                'rules_pdf': 'rules-pdf-status',
                'terms_pdf': 'terms-pdf-status',
            };
            var statusEl = document.getElementById(statusMap[fieldName]);
            if (statusEl) statusEl.textContent = file.name;
            toast(fieldName.replace(/_/g, ' ') + ' uploaded', 'success');
        } catch (e) { toast('Upload failed: ' + e.message, 'error'); }
    }

    /* ==================================================================
     * S27: SCORING SYSTEM CONFIGURATION
     * ================================================================== */

    const SCORING_PRESETS = {
        valorant: {
            scoring_type: 'rounds',
            win_points: 3, draw_points: 1, loss_points: 0, forfeit_points: -1,
            rounds_to_win: 13, overtime_rounds: 6, ot_halves: 2,
            tiebreakers: ['head_to_head', 'round_difference', 'rounds_won', 'buchholz'],
        },
        moba: {
            scoring_type: 'win_loss',
            win_points: 3, draw_points: 0, loss_points: 0, forfeit_points: -1,
            tiebreakers: ['head_to_head', 'game_wins', 'time_rating'],
        },
        br: {
            scoring_type: 'kills',
            win_points: 0, draw_points: 0, loss_points: 0, forfeit_points: -3,
            tiebreakers: ['total_points', 'total_kills', 'highest_placement', 'avg_placement'],
        },
        sports: {
            scoring_type: 'goals',
            win_points: 3, draw_points: 1, loss_points: 0, forfeit_points: -1,
            match_duration: 90, extra_time: 'extra_time_30', aggregate: false,
            tiebreakers: ['head_to_head', 'goal_difference', 'goals_scored', 'away_goals'],
        },
    };

    const ALL_TIEBREAKERS = [
        { key: 'head_to_head', label: 'Head-to-Head Record' },
        { key: 'round_difference', label: 'Round Difference' },
        { key: 'rounds_won', label: 'Rounds Won' },
        { key: 'game_wins', label: 'Game Wins (series)' },
        { key: 'goal_difference', label: 'Goal Difference' },
        { key: 'goals_scored', label: 'Goals Scored' },
        { key: 'away_goals', label: 'Away Goals' },
        { key: 'total_points', label: 'Total Points' },
        { key: 'total_kills', label: 'Total Kills' },
        { key: 'highest_placement', label: 'Highest Placement' },
        { key: 'avg_placement', label: 'Average Placement' },
        { key: 'time_rating', label: 'Time Rating' },
        { key: 'buchholz', label: 'Buchholz Score' },
        { key: 'sonneborn_berger', label: 'Sonneborn-Berger' },
        { key: 'coin_flip', label: 'Coin Flip (emergency)' },
    ];

    let _currentTiebreakers = ['head_to_head', 'round_difference', 'rounds_won'];

    /* ── S27: Scoring Config helpers (direct DOM, not data-field) ── */
    function _scoringEl(id) { return document.getElementById(id); }
    function _setScoringVal(id, val) { var el = _scoringEl(id); if (el) el.value = val ?? ''; }
    function _getScoringVal(id) { var el = _scoringEl(id); return el ? el.value : ''; }

    async function loadScoringConfig() {
        try {
            var data = await API('settings/game-config/');
            var rules = data.scoring_rules || {};

            _setScoringVal('scoring-type', rules.scoring_type || 'win_loss');
            _setScoringVal('scoring-win-pts', rules.win_points ?? 3);
            _setScoringVal('scoring-draw-pts', rules.draw_points ?? 1);
            _setScoringVal('scoring-loss-pts', rules.loss_points ?? 0);
            _setScoringVal('scoring-forfeit-pts', rules.forfeit_points ?? -1);
            _setScoringVal('scoring-rounds-to-win', rules.rounds_to_win ?? 13);
            _setScoringVal('scoring-overtime-rounds', rules.overtime_rounds ?? 6);
            _setScoringVal('scoring-ot-halves', rules.ot_halves ?? 2);
            _setScoringVal('scoring-match-duration', rules.match_duration ?? 90);
            _setScoringVal('scoring-extra-time', rules.extra_time || 'none');

            var aggEl = document.getElementById('scoring-aggregate');
            if (aggEl) aggEl.checked = !!rules.aggregate;

            _currentTiebreakers = rules.tiebreakers || ['head_to_head', 'round_difference', 'rounds_won'];
            renderTiebreakers();
            onScoringTypeChange(rules.scoring_type || 'win_loss');
        } catch (e) {
            console.warn('[toc:settings] scoring config load failed', e);
        }
    }

    async function saveScoringConfig() {
        var rules = {
            scoring_type: _getScoringVal('scoring-type'),
            win_points: parseInt(_getScoringVal('scoring-win-pts')) || 0,
            draw_points: parseInt(_getScoringVal('scoring-draw-pts')) || 0,
            loss_points: parseInt(_getScoringVal('scoring-loss-pts')) || 0,
            forfeit_points: parseInt(_getScoringVal('scoring-forfeit-pts')) || 0,
            rounds_to_win: parseInt(_getScoringVal('scoring-rounds-to-win')) || 13,
            overtime_rounds: parseInt(_getScoringVal('scoring-overtime-rounds')) || 0,
            ot_halves: parseInt(_getScoringVal('scoring-ot-halves')) || 0,
            match_duration: parseInt(_getScoringVal('scoring-match-duration')) || 90,
            extra_time: _getScoringVal('scoring-extra-time') || 'none',
            aggregate: document.getElementById('scoring-aggregate')?.checked || false,
            tiebreakers: _currentTiebreakers,
        };
        try {
            await API('settings/game-config/', {
                method: 'POST',
                body: JSON.stringify({ scoring_rules: rules }),
            });
            toast('Scoring configuration saved', 'success');
            _markSettingsDirty(false);
        } catch (e) {
            toast('Save failed: ' + e.message, 'error');
        }
    }

    function onScoringTypeChange(type) {
        var pointTable = document.getElementById('scoring-point-table');
        var roundsConfig = document.getElementById('scoring-rounds-config');
        var goalsConfig = document.getElementById('scoring-goals-config');

        if (pointTable) pointTable.classList.toggle('hidden', type === 'kills' || type === 'placement');
        if (roundsConfig) roundsConfig.classList.toggle('hidden', type !== 'rounds');
        if (goalsConfig) goalsConfig.classList.toggle('hidden', type !== 'goals');
    }

    function applyScoringPreset(presetName) {
        var preset = SCORING_PRESETS[presetName];
        if (!preset) return;

        setVal('scoring-type', preset.scoring_type);
        if (preset.win_points != null) setVal('scoring-win-pts', preset.win_points);
        if (preset.draw_points != null) setVal('scoring-draw-pts', preset.draw_points);
        if (preset.loss_points != null) setVal('scoring-loss-pts', preset.loss_points);
        if (preset.forfeit_points != null) setVal('scoring-forfeit-pts', preset.forfeit_points);
        if (preset.rounds_to_win != null) setVal('scoring-rounds-to-win', preset.rounds_to_win);
        if (preset.overtime_rounds != null) setVal('scoring-overtime-rounds', preset.overtime_rounds);
        if (preset.ot_halves != null) setVal('scoring-ot-halves', preset.ot_halves);
        if (preset.match_duration != null) setVal('scoring-match-duration', preset.match_duration);
        if (preset.extra_time != null) setVal('scoring-extra-time', preset.extra_time);

        var aggEl = document.getElementById('scoring-aggregate');
        if (aggEl) aggEl.checked = !!preset.aggregate;

        if (preset.tiebreakers) {
            _currentTiebreakers = [...preset.tiebreakers];
            renderTiebreakers();
        }

        onScoringTypeChange(preset.scoring_type);
        toast('Preset "' + presetName + '" applied — save to persist', 'info');
    }

    function renderTiebreakers() {
        var container = document.getElementById('tiebreaker-list');
        if (!container) return;

        container.innerHTML = _currentTiebreakers.map(function (key, idx) {
            var tb = ALL_TIEBREAKERS.find(function (t) { return t.key === key; });
            var label = tb ? tb.label : key;
            return '<div class="flex items-center gap-2 p-2 bg-dc-surface border border-dc-border rounded-lg group">' +
                '<span class="text-[10px] font-mono text-dc-text w-5 text-center">' + (idx + 1) + '</span>' +
                '<span class="text-xs text-dc-textBright flex-1">' + esc(label) + '</span>' +
                '<button onclick="TOC.settings.moveTiebreaker(' + idx + ', -1)" class="text-dc-text hover:text-white transition-colors p-0.5' + (idx === 0 ? ' opacity-20 pointer-events-none' : '') + '"><i data-lucide="chevron-up" class="w-3 h-3"></i></button>' +
                '<button onclick="TOC.settings.moveTiebreaker(' + idx + ', 1)" class="text-dc-text hover:text-white transition-colors p-0.5' + (idx === _currentTiebreakers.length - 1 ? ' opacity-20 pointer-events-none' : '') + '"><i data-lucide="chevron-down" class="w-3 h-3"></i></button>' +
                '<button onclick="TOC.settings.removeTiebreaker(' + idx + ')" class="text-dc-text hover:text-dc-danger transition-colors p-0.5 opacity-0 group-hover:opacity-100"><i data-lucide="x" class="w-3 h-3"></i></button>' +
                '</div>';
        }).join('');

        // Add button for unused tiebreakers
        var unused = ALL_TIEBREAKERS.filter(function (t) { return _currentTiebreakers.indexOf(t.key) === -1; });
        if (unused.length > 0) {
            container.innerHTML += '<div class="mt-2"><select onchange="TOC.settings.addTiebreaker(this.value); this.value=\'\';" class="bg-dc-surface border border-dc-border rounded-lg px-3 py-1.5 text-[10px] text-dc-textBright focus:border-theme/50 outline-none">' +
                '<option value="">+ Add tiebreaker…</option>' +
                unused.map(function (t) { return '<option value="' + t.key + '">' + esc(t.label) + '</option>'; }).join('') +
                '</select></div>';
        }

        if (typeof lucide !== 'undefined') try { lucide.createIcons(); } catch (e) { /* ok */ }
    }

    function addTiebreaker(key) {
        if (!key || _currentTiebreakers.indexOf(key) !== -1) return;
        _currentTiebreakers.push(key);
        renderTiebreakers();
    }

    function removeTiebreaker(idx) {
        _currentTiebreakers.splice(idx, 1);
        renderTiebreakers();
    }

    function moveTiebreaker(idx, dir) {
        var newIdx = idx + dir;
        if (newIdx < 0 || newIdx >= _currentTiebreakers.length) return;
        var temp = _currentTiebreakers[idx];
        _currentTiebreakers[idx] = _currentTiebreakers[newIdx];
        _currentTiebreakers[newIdx] = temp;
        renderTiebreakers();
    }

    /* ==================================================================
     * CLONE TOURNAMENT
     * ================================================================== */
    function cloneTournament() {
        const defaultName = (document.querySelector('[data-field="name"]')?.value || 'Tournament') + ' (Copy)';
        const FIELD = 'w-full bg-dc-bg border border-dc-border/60 rounded-lg px-3 py-2 text-white text-sm focus:border-theme focus:outline-none';
        const body = `<div class="space-y-4 p-5">
          <p class="text-xs text-dc-text">Creates a full copy of this tournament with all settings, rules and configuration — but no participants or match data.</p>
          <div>
            <label class="block text-[10px] text-dc-text uppercase tracking-widest mb-1">New Tournament Name *</label>
            <input id="clone-tournament-name" type="text" value="${defaultName.replace(/"/g, '&quot;')}" class="${FIELD}">
          </div>
        </div>`;
        const footer = `<div class="flex gap-3 p-4 pt-0">
          <button onclick="TOC.settings._confirmClone()" class="flex-1 bg-theme hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Clone Tournament</button>
          <button onclick="TOC.drawer.close()" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
        </div>`;
        TOC.drawer.open('Clone Tournament', body, footer);
        setTimeout(() => {
            const inp = document.getElementById('clone-tournament-name');
            if (inp) { inp.focus(); inp.select(); }
        }, 50);
    }

    async function _confirmClone() {
        const defaultName = (document.querySelector('[data-field="name"]')?.value || 'Tournament') + ' (Copy)';
        const newName = document.getElementById('clone-tournament-name')?.value.trim() || defaultName;
        TOC.drawer.close();

        const btn = document.getElementById('btn-clone-tournament');
        if (btn) { btn.disabled = true; btn.textContent = 'Cloning…'; }

        try {
            const result = await API.post('settings/clone/', { name: newName });
            toast('Tournament cloned! Redirecting…', 'success');
            setTimeout(() => {
                window.location.href = `/tournaments/${result.slug}/manage/`;
            }, 1200);
        } catch (e) {
            toast('Clone failed: ' + (e?.data?.error || 'Unknown error'), 'error');
            if (btn) { btn.disabled = false; btn.textContent = 'Clone Tournament'; }
        }
    }

    /* ==================================================================
     * INIT
     * ================================================================== */
    async function init (options) {
        const opts = options || {};
        const force = opts.force === true;
        const silent = opts.silent === true;

        if (!force && hasFreshSettingsCache()) {
            await _initRichTextEditors();
            setSettingsSyncStatus('ok');
            return;
        }

        if (_settingsInflight && !force) {
            return _settingsInflight;
        }

        if (!silent) {
            setSettingsSyncStatus('loading', _settingsLastInitAt > 0 ? 'Refreshing settings...' : 'Loading settings...');
        }

        _settingsInflight = (async function () {
            try {
                const settingsLoaded = await loadSettings();
                if (!settingsLoaded) {
                    throw new Error('Unable to load tournament settings data.');
                }

                await _initRichTextEditors();
                const refreshed = await loadSettings();
                if (!refreshed) {
                    throw new Error('Unable to hydrate rich text settings content.');
                }

                // Render per-section controls as soon as core settings are present.
                _ensureSectionStateBadges();
                _ensureSectionActionButtons();

                const results = await Promise.allSettled([
                    loadGameConfig(),
                    loadMapPool(),
                    loadRegions(),
                    loadRulebook(),
                    loadBRScoring(),
                    loadPaymentMethods(),
                    loadScoringConfig(),
                ]);

                const failed = results.filter(function (r) { return r && r.status === 'rejected'; });
                if (failed.length > 0) {
                    throw new Error(failed[0] && failed[0].reason && failed[0].reason.message
                        ? String(failed[0].reason.message)
                        : 'One or more settings sections failed to refresh');
                }

                applyGameAwareVisibility();
                _bindDirtyTracking();
                _markSettingsDirty(false);
                _settingsLastInitAt = Date.now();
                _settingsLoadedOnce = true;
                setSettingsErrorBanner('');
                setSettingsSyncStatus('ok');
                _markAllSections('clean');
            } catch (e) {
                const detail = e && e.message ? String(e.message) : 'Request failed';
                _settingsLastInitAt = 0;
                _settingsLoadedOnce = false;
                setSettingsSyncStatus('error', detail);
                setSettingsErrorBanner(detail);
            } finally {
                _settingsInflight = null;
            }
        })();

        return _settingsInflight;
    }

    // Public API
    window.TOC = window.TOC || {};
    window.TOC.settings = {
        init,
        saveAll,
        saveSection,
        saveGameConfig,
        syncModeVisibility,
        syncCheckInVisibility,
        syncNoShowVisibility,
        syncFeeVisibility,
        syncVetoVisibility,
        addVetoStep,
        removeVetoStep,
        changeVetoTeam,
        loadMapPool,
        openAddMap,
        confirmAddMap,
        toggleMap,
        deleteMap,
        openAddRegion,
        confirmAddRegion,
        deleteRegion,
        openCreateRulebook,
        confirmCreateRulebook,
        publishRulebook,
        editRulebook,
        confirmEditRulebook,
        saveBRScoring,
        openAddPaymentMethod,
        syncPaymentMethodFields,
        confirmAddPaymentMethod,
        editPaymentMethod,
        confirmEditPaymentMethod,
        dismissPaymentOverlay,
        deletePaymentMethod,
        uploadFile,
        // S27: Scoring system
        saveScoringConfig,
        onScoringTypeChange,
        applyScoringPreset,
        addTiebreaker,
        removeTiebreaker,
        moveTiebreaker,
        // S28: Tournament cloning
        cloneTournament, _confirmClone,
    };

    // ── Discord Webhook Test Button ──
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('#btn-test-discord-webhook');
        if (!btn) return;

        const input = document.querySelector('[data-field="discord_webhook_url"]');
        const webhookUrl = input ? input.value.trim() : '';
        if (!webhookUrl) {
            window.tocToast?.('Enter a Discord webhook URL first', 'warning');
            return;
        }
        if (!webhookUrl.startsWith('https://discord.com/api/webhooks/')) {
            window.tocToast?.('Invalid Discord webhook URL format', 'warning');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"></circle><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" class="opacity-75"></path></svg> Testing...';

        const slug = window.TOC_CONFIG?.slug || '';
        fetch(`/api/toc/${slug}/settings/discord-webhook-test/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || '',
            },
            body: JSON.stringify({ webhook_url: webhookUrl }),
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                window.tocToast?.('✅ Discord webhook test sent! Check your Discord channel.', 'success');
            } else {
                window.tocToast?.(data.error || 'Webhook test failed', 'error');
            }
        })
        .catch(() => window.tocToast?.('Network error testing webhook', 'error'))
        .finally(() => {
            btn.disabled = false;
            btn.innerHTML = '<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286z"/></svg> Test';
        });
    });

    function _onSettingsVisibilityChange() {
        if (!document.hidden && isSettingsTabActive() && !hasFreshSettingsCache()) {
            init({ silent: true });
        }
    }

    function _onBeforeUnload(e) {
        if (!_settingsDirty) return;
        e.preventDefault();
        e.returnValue = 'You have unsaved settings changes. Are you sure you want to leave?';
        return e.returnValue;
    }

    // Auto-init when navigating to Settings tab
    document.addEventListener('toc:tab-changed', function (e) {
        if (e.detail?.tab === 'settings') {
            _initRichTextEditors();
            init();
        }
    });

    document.addEventListener('visibilitychange', _onSettingsVisibilityChange);
    window.addEventListener('beforeunload', _onBeforeUnload);

    if (isSettingsTabActive()) {
        init({ silent: true });
        _initRichTextEditors();
    } else {
        _bindDirtyTracking();
        _markSettingsDirty(false);
    }
})();
