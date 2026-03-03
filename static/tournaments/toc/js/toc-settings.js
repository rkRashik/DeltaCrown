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
    const setVal = (container, field, value) => {
        const el = container?.querySelector('[data-field="' + field + '"]');
        if (!el) return;
        if (el.type === 'checkbox') el.checked = !!value;
        else if (el.tagName === 'TEXTAREA') el.value = value || '';
        else el.value = value ?? '';
    };
    const getVal = (container, field) => {
        const el = container?.querySelector('[data-field="' + field + '"]');
        if (!el) return undefined;
        if (el.type === 'checkbox') return el.checked;
        if (el.type === 'number') return el.value === '' ? null : Number(el.value);
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
            else data[k] = el.value;
        });
        return data;
    };

    /* State */
    let vetoSequence = [];
    let rulebookVersions = [];
    let paymentMethods = [];

    /* ==================================================================
     * LOAD SETTINGS — populates all Tournament-model sections
     * ================================================================== */
    async function loadSettings () {
        try {
            const s = await API('settings/');
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
            // Social
            const social = document.getElementById('settings-social');
            if (social && s.social) {
                setVal(social, 'contact_email', s.social.contact_email);
                setVal(social, 'social_discord', s.social.social_discord);
                setVal(social, 'social_twitter', s.social.social_twitter);
                setVal(social, 'social_instagram', s.social.social_instagram);
                setVal(social, 'social_youtube', s.social.social_youtube);
                setVal(social, 'social_website', s.social.social_website);
            }
            // Waitlist
            const wait = document.getElementById('settings-waitlist');
            if (wait && s.waitlist) {
                setVal(wait, 'auto_forfeit_no_shows', s.waitlist.auto_forfeit_no_shows);
                setVal(wait, 'waitlist_auto_promote', s.waitlist.waitlist_auto_promote);
                setVal(wait, 'no_show_timeout_minutes', s.waitlist.no_show_timeout_minutes);
                setVal(wait, 'max_waitlist_size', s.waitlist.max_waitlist_size);
            }
            // SEO
            const seo = document.getElementById('settings-seo');
            if (seo && s.seo) {
                setVal(seo, 'meta_description', s.seo.meta_description);
                const kw = s.seo.meta_keywords;
                setVal(seo, 'meta_keywords', Array.isArray(kw) ? kw.join(', ') : kw || '');
            }
            // Sync conditional sections
            syncModeVisibility();
            syncCheckInVisibility();
            syncFeeVisibility();
        } catch (e) {
            console.warn('[TOC.settings] loadSettings failed', e);
        }
    }

    /* ==================================================================
     * SAVE ALL — gathers all Tournament-model fields and PUTs them
     * ================================================================== */
    async function saveAll () {
        try {
            const payload = Object.assign({},
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
            );
            // Convert meta_keywords string to array
            if (typeof payload.meta_keywords === 'string') {
                payload.meta_keywords = payload.meta_keywords.split(',').map(s => s.trim()).filter(Boolean);
            }
            await API('settings/', { method: 'PUT', body: JSON.stringify(payload) });
            toast('Settings saved', 'success');
        } catch (e) {
            toast('Save failed: ' + (e.message || e), 'error');
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

    async function publishRulebook (versionId) {
        if (!confirm('Publish this version? This will deactivate other versions.')) return;
        await API('settings/rulebook/' + versionId + '/publish/', { method: 'POST' });
        loadRulebook(); toast('Rulebook published', 'success');
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
            list.innerHTML = paymentMethods.map(function (m) {
                var label = m.method.charAt(0).toUpperCase() + m.method.slice(1);
                var acct = m.account_number || m.bank_name || '';
                return '<div class="flex items-center justify-between py-2 px-3 bg-dc-surface/50 rounded-lg border border-dc-border">'
                    + '<div class="flex items-center gap-2">'
                    + '<span class="w-2 h-2 rounded-full ' + (m.is_enabled ? 'bg-dc-success' : 'bg-dc-text/30') + '"></span>'
                    + '<span class="text-sm text-white font-medium">' + esc(label) + '</span>'
                    + (acct ? '<span class="text-xs text-dc-text">' + esc(acct) + '</span>' : '')
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
            + '<button onclick="TOC.settings.confirmAddPaymentMethod()" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Add Method</button>'
            + '</div>');
        syncPaymentMethodFields();
    }

    function syncPaymentMethodFields () {
        var method = document.getElementById('pm-method')?.value || 'bkash';
        var container = document.getElementById('pm-fields');
        if (!container) return;
        var html = '';
        if (method === 'bkash' || method === 'nagad' || method === 'rocket') {
            var prefix = method;
            html = '<div class="space-y-3">'
                + '<div><label class="block text-xs text-dc-text mb-1">Account Number</label>'
                + '<input id="pm-account-number" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" placeholder="01XXXXXXXXX"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Account Name</label>'
                + '<input id="pm-account-name" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Account Type</label>'
                + '<select id="pm-account-type" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">'
                + '<option value="personal">Personal</option><option value="merchant">Merchant</option><option value="agent">Agent</option></select></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Instructions</label>'
                + '<textarea id="pm-instructions" rows="2" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></textarea></div>'
                + '<label class="flex items-center gap-2 text-sm text-dc-text cursor-pointer"><input id="pm-ref-required" type="checkbox" checked class="rounded border-dc-border bg-dc-surface text-theme"> Reference Required</label>'
                + '</div>';
        } else if (method === 'bank_transfer') {
            html = '<div class="space-y-3">'
                + '<div><label class="block text-xs text-dc-text mb-1">Bank Name</label><input id="pm-bank-name" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Branch</label><input id="pm-bank-branch" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Account Number</label><input id="pm-bank-acct" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Account Name</label><input id="pm-bank-acct-name" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Routing Number</label><input id="pm-bank-routing" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
                + '<div><label class="block text-xs text-dc-text mb-1">Instructions</label><textarea id="pm-bank-instructions" rows="2" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></textarea></div>'
                + '</div>';
        } else {
            html = '<div><label class="block text-xs text-dc-text mb-1">Instructions</label>'
                + '<textarea id="pm-dc-instructions" rows="2" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></textarea></div>';
        }
        container.innerHTML = html;
    }

    async function confirmAddPaymentMethod () {
        var method = document.getElementById('pm-method')?.value;
        if (!method) return;
        var payload = { method: method };
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
            payload.bank_instructions = document.getElementById('pm-bank-instructions')?.value || '';
        } else {
            payload.deltacoin_instructions = document.getElementById('pm-dc-instructions')?.value || '';
        }
        try {
            await API('settings/payment-methods/', { method: 'POST', body: JSON.stringify(payload) });
            closeOverlay(); loadPaymentMethods(); toast('Payment method added', 'success');
        } catch (e) { toast('Failed to add payment method', 'error'); }
    }

    function editPaymentMethod (id) {
        // Re-load the specific method — for simplicity, ask user to delete and re-add
        toast('To edit, delete and re-add the payment method', 'info');
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
     * INIT
     * ================================================================== */
    function init () {
        loadSettings();
        loadGameConfig();
        loadMapPool();
        loadRegions();
        loadRulebook();
        loadBRScoring();
        loadPaymentMethods();
        applyGameAwareVisibility();
    }

    // Public API
    window.TOC = window.TOC || {};
    window.TOC.settings = {
        init,
        saveAll,
        saveGameConfig,
        syncModeVisibility,
        syncCheckInVisibility,
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
        deletePaymentMethod,
        uploadFile,
    };

    // Auto-init when navigating to Settings tab
    document.addEventListener('toc:tab-changed', function (e) {
        if (e.detail?.tab === 'settings') init();
    });
})();
