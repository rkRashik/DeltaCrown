/**
 * TOC Settings Module — Sprint 8
 *
 * Manages collapsible settings sections, game config, map pool
 * editor, server regions, rulebook versioning, and BR scoring.
 */
(function () {
    'use strict';

    const API = window.TOC?.api;
    if (!API) return;

    /* ------------------------------------------------------------------ */
    /*  State                                                              */
    /* ------------------------------------------------------------------ */
    let settingsCache = null;
    let gameConfigCache = null;
    let mapPool = [];
    let regions = [];
    let rulebookVersions = [];
    let brScoring = null;

    /* ------------------------------------------------------------------ */
    /*  Settings (Basic / Format / Prizes)                                 */
    /* ------------------------------------------------------------------ */

    async function loadSettings() {
        try {
            settingsCache = await API.get('settings/');
            populateSection('settings-basic', settingsCache.basic || {});
            populateSection('settings-format', { ...(settingsCache.format || {}), ...(settingsCache.registration_rules || {}), ...(settingsCache.features || {}) });
            populateSection('settings-prizes', settingsCache.prizes || {});
        } catch (e) { console.warn('Settings load error', e); }
    }

    function populateSection(containerId, data) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.querySelectorAll('[data-field]').forEach(el => {
            const key = el.dataset.field;
            if (!(key in data)) return;
            if (el.type === 'checkbox') {
                el.checked = !!data[key];
            } else {
                el.value = data[key] ?? '';
            }
        });
    }

    function gatherSection(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return {};
        const data = {};
        container.querySelectorAll('[data-field]').forEach(el => {
            const key = el.dataset.field;
            if (el.type === 'checkbox') {
                data[key] = el.checked;
            } else if (el.type === 'number') {
                data[key] = el.value ? Number(el.value) : null;
            } else {
                data[key] = el.value;
            }
        });
        return data;
    }

    async function saveAll() {
        const payload = {
            ...gatherSection('settings-basic'),
            ...gatherSection('settings-format'),
            ...gatherSection('settings-prizes'),
        };
        try {
            await API.put('settings/', payload);
            window.TOC?.toast?.('Settings saved', 'success');
        } catch (e) {
            window.TOC?.toast?.('Save failed', 'error');
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Game Match Config                                                  */
    /* ------------------------------------------------------------------ */

    async function loadGameConfig() {
        try {
            gameConfigCache = await API.get('settings/game-config/');
            populateSection('settings-game-config', gameConfigCache || {});
        } catch (e) { console.warn('Game config load error', e); }
    }

    async function saveGameConfig() {
        const payload = gatherSection('settings-game-config');
        try {
            await API.put('settings/game-config/', payload);
            window.TOC?.toast?.('Game config saved', 'success');
        } catch (e) {
            window.TOC?.toast?.('Save failed', 'error');
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Map Pool                                                           */
    /* ------------------------------------------------------------------ */

    async function loadMapPool() {
        try {
            mapPool = await API.get('settings/map-pool/');
            renderMapPool();
        } catch (e) { console.warn('Map pool load error', e); }
    }

    function renderMapPool() {
        const container = document.getElementById('map-pool-list');
        if (!container) return;
        if (!mapPool.length) {
            container.innerHTML = '<div class="py-6 text-center text-dc-text text-xs">No maps in pool. Add some!</div>';
            return;
        }
        container.innerHTML = mapPool.map((m, i) => `
            <div class="flex items-center gap-3 p-3 rounded-lg border border-dc-border bg-dc-surface/50 group" data-map-id="${m.id}">
                <span class="text-dc-text text-xs font-mono w-6 text-center">${i + 1}</span>
                ${m.image ? `<img src="${m.image}" class="w-10 h-10 rounded object-cover" alt="${m.map_name}">` : '<div class="w-10 h-10 rounded bg-dc-panel flex items-center justify-center"><i data-lucide="map-pin" class="w-4 h-4 text-dc-text"></i></div>'}
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-bold text-white truncate">${m.map_name}</div>
                    ${m.map_code ? `<div class="text-xs text-dc-text font-mono">${m.map_code}</div>` : ''}
                </div>
                <span class="px-2 py-0.5 text-xs rounded-full ${m.is_active ? 'bg-dc-success/10 text-dc-success' : 'bg-dc-text/10 text-dc-text'}">${m.is_active ? 'Active' : 'Inactive'}</span>
                <button onclick="TOC.settings.toggleMap('${m.id}', ${!m.is_active})" class="text-dc-text hover:text-dc-textBright text-xs">${m.is_active ? 'Disable' : 'Enable'}</button>
                <button onclick="TOC.settings.deleteMap('${m.id}')" class="text-dc-text hover:text-dc-danger text-xs">
                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                </button>
            </div>
        `).join('');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function openAddMap() {
        const html = `
            <div class="space-y-4">
                <h3 class="font-display font-bold text-white text-lg">Add Map</h3>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Map Name *</label>
                    <input id="new-map-name" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Map Code</label>
                    <input id="new-map-code" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Image URL</label>
                    <input id="new-map-image" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <button onclick="TOC.settings.confirmAddMap()" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Add Map</button>
            </div>
        `;
        showOverlay(html);
    }

    async function confirmAddMap() {
        const name = document.getElementById('new-map-name')?.value?.trim();
        if (!name) return;
        try {
            await API.post('settings/map-pool/', {
                map_name: name,
                map_code: document.getElementById('new-map-code')?.value?.trim() || '',
                image: document.getElementById('new-map-image')?.value?.trim() || '',
            });
            closeOverlay();
            loadMapPool();
        } catch (e) {
            window.TOC?.toast?.('Add map failed', 'error');
        }
    }

    async function toggleMap(mapId, active) {
        try {
            await API.put(`settings/map-pool/${mapId}/`, { is_active: active });
            loadMapPool();
        } catch (e) { window.TOC?.toast?.('Toggle failed', 'error'); }
    }

    async function deleteMap(mapId) {
        if (!confirm('Remove this map from the pool?')) return;
        try {
            await API.delete(`settings/map-pool/${mapId}/`);
            loadMapPool();
        } catch (e) { window.TOC?.toast?.('Delete failed', 'error'); }
    }

    /* ------------------------------------------------------------------ */
    /*  Server Regions                                                     */
    /* ------------------------------------------------------------------ */

    async function loadRegions() {
        try {
            regions = await API.get('settings/regions/');
            renderRegions();
        } catch (e) { console.warn('Regions load error', e); }
    }

    function renderRegions() {
        const container = document.getElementById('region-list');
        if (!container) return;
        if (!regions.length) {
            container.innerHTML = '<div class="py-6 text-center text-dc-text text-xs">No server regions configured.</div>';
            return;
        }
        container.innerHTML = regions.map(r => `
            <div class="flex items-center gap-3 p-3 rounded-lg border border-dc-border bg-dc-surface/50">
                <i data-lucide="globe" class="w-4 h-4 text-theme"></i>
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-bold text-white">${r.name}</div>
                    <div class="text-xs text-dc-text font-mono">${r.code}</div>
                </div>
                <span class="px-2 py-0.5 text-xs rounded-full ${r.is_active ? 'bg-dc-success/10 text-dc-success' : 'bg-dc-text/10 text-dc-text'}">${r.is_active ? 'Active' : 'Inactive'}</span>
                <button onclick="TOC.settings.deleteRegion('${r.id}')" class="text-dc-text hover:text-dc-danger text-xs">
                    <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                </button>
            </div>
        `).join('');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function openAddRegion() {
        const html = `
            <div class="space-y-4">
                <h3 class="font-display font-bold text-white text-lg">Add Server Region</h3>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Region Name *</label>
                    <input id="new-region-name" type="text" placeholder="US East" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Region Code *</label>
                    <input id="new-region-code" type="text" placeholder="us-east" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Ping Endpoint</label>
                    <input id="new-region-ping" type="text" placeholder="https://..." class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <button onclick="TOC.settings.confirmAddRegion()" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Add Region</button>
            </div>
        `;
        showOverlay(html);
    }

    async function confirmAddRegion() {
        const name = document.getElementById('new-region-name')?.value?.trim();
        const code = document.getElementById('new-region-code')?.value?.trim();
        if (!name || !code) return;
        try {
            await API.post('settings/regions/', {
                name,
                code,
                ping_endpoint: document.getElementById('new-region-ping')?.value?.trim() || '',
            });
            closeOverlay();
            loadRegions();
        } catch (e) { window.TOC?.toast?.('Add region failed', 'error'); }
    }

    async function deleteRegion(regionId) {
        if (!confirm('Remove this server region?')) return;
        try {
            await API.delete(`settings/regions/${regionId}/`);
            loadRegions();
        } catch (e) { window.TOC?.toast?.('Delete failed', 'error'); }
    }

    /* ------------------------------------------------------------------ */
    /*  Rulebook Versions                                                  */
    /* ------------------------------------------------------------------ */

    async function loadRulebook() {
        try {
            rulebookVersions = await API.get('settings/rulebook/');
            renderRulebook();
        } catch (e) { console.warn('Rulebook load error', e); }
    }

    function renderRulebook() {
        const container = document.getElementById('rulebook-list');
        if (!container) return;
        if (!rulebookVersions.length) {
            container.innerHTML = '<div class="py-6 text-center text-dc-text text-xs">No rulebook versions yet.</div>';
            return;
        }
        container.innerHTML = rulebookVersions.map(v => `
            <div class="p-4 rounded-lg border ${v.is_active ? 'border-dc-success/40 bg-dc-success/5' : 'border-dc-border bg-dc-surface/50'} space-y-2">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-white">v${v.version}</span>
                        ${v.is_active ? '<span class="px-2 py-0.5 text-xs rounded-full bg-dc-success/10 text-dc-success">Published</span>' : '<span class="px-2 py-0.5 text-xs rounded-full bg-dc-text/10 text-dc-text">Draft</span>'}
                    </div>
                    <div class="flex items-center gap-2">
                        ${!v.is_active ? `<button onclick="TOC.settings.publishRulebook('${v.id}')" class="px-3 py-1 rounded text-xs border border-dc-success/30 text-dc-success hover:bg-dc-success/10">Publish</button>` : ''}
                        <button onclick="TOC.settings.editRulebook('${v.id}')" class="text-dc-text hover:text-dc-textBright text-xs">
                            <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
                        </button>
                    </div>
                </div>
                ${v.changelog ? `<div class="text-xs text-dc-text">${v.changelog}</div>` : ''}
                <div class="text-xs text-dc-text/60">${v.created_at ? new Date(v.created_at).toLocaleDateString() : ''}</div>
            </div>
        `).join('');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function openCreateRulebook() {
        const html = `
            <div class="space-y-4">
                <h3 class="font-display font-bold text-white text-lg">New Rulebook Version</h3>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Version *</label>
                    <input id="new-rb-version" type="text" placeholder="1.0" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Content (Markdown/HTML)</label>
                    <textarea id="new-rb-content" rows="8" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright font-mono focus:outline-none focus:border-theme/50"></textarea>
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Changelog</label>
                    <input id="new-rb-changelog" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <button onclick="TOC.settings.confirmCreateRulebook()" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Create Version</button>
            </div>
        `;
        showOverlay(html);
    }

    async function confirmCreateRulebook() {
        const version = document.getElementById('new-rb-version')?.value?.trim();
        if (!version) return;
        try {
            await API.post('settings/rulebook/', {
                version,
                content: document.getElementById('new-rb-content')?.value || '',
                changelog: document.getElementById('new-rb-changelog')?.value?.trim() || '',
            });
            closeOverlay();
            loadRulebook();
        } catch (e) { window.TOC?.toast?.('Create failed', 'error'); }
    }

    async function publishRulebook(versionId) {
        if (!confirm('Publish this rulebook version? It will become the active version.')) return;
        try {
            await API.post(`settings/rulebook/${versionId}/publish/`);
            loadRulebook();
            window.TOC?.toast?.('Rulebook published', 'success');
        } catch (e) { window.TOC?.toast?.('Publish failed', 'error'); }
    }

    function editRulebook(versionId) {
        const v = rulebookVersions.find(r => String(r.id) === String(versionId));
        if (!v) return;
        const html = `
            <div class="space-y-4">
                <h3 class="font-display font-bold text-white text-lg">Edit Rulebook v${v.version}</h3>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Content</label>
                    <textarea id="edit-rb-content" rows="10" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright font-mono focus:outline-none focus:border-theme/50">${v.content || ''}</textarea>
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Changelog</label>
                    <input id="edit-rb-changelog" type="text" value="${v.changelog || ''}" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <button onclick="TOC.settings.confirmEditRulebook('${versionId}')" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Save Changes</button>
            </div>
        `;
        showOverlay(html);
    }

    async function confirmEditRulebook(versionId) {
        try {
            await API.put(`settings/rulebook/${versionId}/`, {
                content: document.getElementById('edit-rb-content')?.value || '',
                changelog: document.getElementById('edit-rb-changelog')?.value?.trim() || '',
            });
            closeOverlay();
            loadRulebook();
        } catch (e) { window.TOC?.toast?.('Update failed', 'error'); }
    }

    /* ------------------------------------------------------------------ */
    /*  BR Scoring                                                         */
    /* ------------------------------------------------------------------ */

    async function loadBRScoring() {
        try {
            brScoring = await API.get('settings/br-scoring/');
            if (brScoring && Object.keys(brScoring).length) {
                const container = document.getElementById('settings-br-scoring');
                if (!container) return;
                const kpEl = container.querySelector('[data-field="kill_points"]');
                const ppEl = container.querySelector('[data-field="placement_points"]');
                if (kpEl) kpEl.value = brScoring.kill_points || 1;
                if (ppEl) ppEl.value = JSON.stringify(brScoring.placement_points || {}, null, 2);
            }
        } catch (e) { console.warn('BR scoring load error', e); }
    }

    async function saveBRScoring() {
        const container = document.getElementById('settings-br-scoring');
        if (!container) return;
        const kp = container.querySelector('[data-field="kill_points"]')?.value || 1;
        const ppRaw = container.querySelector('[data-field="placement_points"]')?.value || '{}';
        let pp;
        try { pp = JSON.parse(ppRaw); } catch { window.TOC?.toast?.('Invalid JSON for placement points', 'error'); return; }
        try {
            await API.put('settings/br-scoring/', {
                kill_points: Number(kp),
                placement_points: pp,
            });
            window.TOC?.toast?.('BR scoring saved', 'success');
        } catch (e) { window.TOC?.toast?.('Save failed', 'error'); }
    }

    /* ------------------------------------------------------------------ */
    /*  Overlay helper                                                     */
    /* ------------------------------------------------------------------ */

    function showOverlay(html) {
        let overlay = document.getElementById('settings-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'settings-overlay';
            overlay.className = 'fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm';
            overlay.addEventListener('click', e => { if (e.target === overlay) closeOverlay(); });
            document.body.appendChild(overlay);
        }
        overlay.innerHTML = `<div class="glass-box rounded-2xl p-6 w-full max-w-md mx-4 max-h-[80vh] overflow-y-auto">${html}</div>`;
        overlay.classList.remove('hidden');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function closeOverlay() {
        const overlay = document.getElementById('settings-overlay');
        if (overlay) overlay.classList.add('hidden');
    }

    /* ------------------------------------------------------------------ */
    /*  Init                                                               */
    /* ------------------------------------------------------------------ */

    function init() {
        loadSettings();
        loadGameConfig();
        loadMapPool();
        loadRegions();
        loadRulebook();
        loadBRScoring();
    }

    // Public API
    window.TOC = window.TOC || {};
    window.TOC.settings = {
        init,
        saveAll,
        saveGameConfig,
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
    };
})();
