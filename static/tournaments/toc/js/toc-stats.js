/**
 * TOC Sprint 9 — Stats, Certificates & Trust Index
 * ==================================================
 * S9-F1  Advanced stats dashboard cards (Overview tab)
 * S9-F2  Certificate template editor (Settings tab)
 * S9-F3  Bulk certificate generation
 * S9-F4  Trust Index display on participant detail
 */
;(function () {
    'use strict';

    const NS = (window.TOC = window.TOC || {});
    const api = (ep, opts) => NS.api(ep, opts);

    const state = {
        stats: null,
        templates: [],
        trophies: [],
    };

    /* ────────────────────────────────────────────
     * S9-F1  Advanced Stats Dashboard
     * ──────────────────────────────────────────── */
    async function loadAdvancedStats () {
        try {
            const d = await api('stats/');
            state.stats = d;

            const set = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.textContent = val;
            };

            set('stat-completion', (d.matches?.completion_pct ?? 0) + '%');
            set('stat-avg-duration', d.matches?.avg_duration_minutes != null ? d.matches.avg_duration_minutes + 'm' : '—');
            set('stat-dq-rate', (d.participants?.dq_rate_pct ?? 0) + '%');
            set('stat-checked-in', d.participants?.checked_in ?? 0);
            set('stat-open-disputes', d.disputes?.open ?? 0);
            set('stat-in-progress', d.matches?.in_progress ?? 0);
        } catch (e) {
            console.warn('[TOC.stats] loadAdvancedStats failed', e);
        }
    }

    /* ────────────────────────────────────────────
     * S9-F2  Certificate Template Editor
     * ──────────────────────────────────────────── */
    async function loadTemplates () {
        try {
            state.templates = await api('certificates/');
            renderTemplates();
        } catch (e) {
            console.warn('[TOC.stats] loadTemplates failed', e);
        }
    }

    function renderTemplates () {
        const list = document.getElementById('cert-template-list');
        if (!list) return;
        if (!state.templates.length) {
            list.innerHTML = '<p class="text-xs text-dc-text italic text-center py-6">No certificate templates yet. Create one to get started.</p>';
            return;
        }
        list.innerHTML = state.templates.map(t => `
            <div class="glass-box rounded-lg p-4 flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                        <span class="text-sm font-bold text-white">${esc(t.name)}</span>
                        ${t.is_default ? '<span class="text-[9px] font-bold uppercase bg-theme/20 text-theme px-2 py-0.5 rounded">Default</span>' : ''}
                    </div>
                    <p class="text-[11px] text-dc-text mt-1">Variables: ${(t.variables || []).map(v => '<code class="text-theme">' + esc(v) + '</code>').join(', ') || 'None'}</p>
                </div>
                <div class="flex gap-1.5 shrink-0">
                    <button onclick="TOC.stats.editTemplate('${t.id}')" class="p-1.5 text-dc-text hover:text-white rounded hover:bg-white/5 transition-colors" title="Edit"><i data-lucide="pencil" class="w-3.5 h-3.5"></i></button>
                    <button onclick="TOC.stats.generateSingle('${t.id}')" class="p-1.5 text-dc-text hover:text-dc-success rounded hover:bg-dc-success/10 transition-colors" title="Generate for user"><i data-lucide="file-output" class="w-3.5 h-3.5"></i></button>
                    <button onclick="TOC.stats.deleteTemplate('${t.id}')" class="p-1.5 text-dc-text hover:text-dc-danger rounded hover:bg-dc-danger/10 transition-colors" title="Delete"><i data-lucide="trash-2" class="w-3.5 h-3.5"></i></button>
                </div>
            </div>
        `).join('');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function openCreateTemplate () {
        showOverlay('Create Certificate Template', `
            <div class="space-y-4">
                <div>
                    <label class="block text-xs text-dc-text mb-1">Template Name</label>
                    <input id="cert-tpl-name" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" placeholder="Winner Certificate">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">HTML Template</label>
                    <textarea id="cert-tpl-html" rows="10" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright font-mono focus:outline-none focus:border-theme/50" placeholder="<h1>Certificate of Achievement</h1><p>Awarded to $participant_name...</p>"></textarea>
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Variables (comma-separated)</label>
                    <input id="cert-tpl-vars" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" placeholder="participant_name, tournament_name, date">
                </div>
                <label class="flex items-center gap-2 cursor-pointer">
                    <input id="cert-tpl-default" type="checkbox" class="accent-theme">
                    <span class="text-xs text-dc-text">Set as Default Template</span>
                </label>
                <button onclick="TOC.stats.confirmCreateTemplate()" class="w-full py-2.5 rounded-lg bg-theme text-dc-bg font-bold text-sm hover:brightness-110 transition-all">Create Template</button>
            </div>
        `);
    }

    async function confirmCreateTemplate () {
        const name = document.getElementById('cert-tpl-name')?.value?.trim();
        const html = document.getElementById('cert-tpl-html')?.value || '';
        const vars = (document.getElementById('cert-tpl-vars')?.value || '').split(',').map(s => s.trim()).filter(Boolean);
        const is_default = document.getElementById('cert-tpl-default')?.checked || false;
        if (!name) return;

        await api('certificates/', {
            method: 'POST',
            body: JSON.stringify({ name, template_html: html, variables: vars, is_default }),
        });
        closeOverlay();
        loadTemplates();
    }

    function editTemplate (id) {
        const tpl = state.templates.find(t => t.id === id);
        if (!tpl) return;

        showOverlay('Edit Certificate Template', `
            <div class="space-y-4">
                <div>
                    <label class="block text-xs text-dc-text mb-1">Template Name</label>
                    <input id="cert-edit-name" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" value="${esc(tpl.name)}">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Variables (comma-separated)</label>
                    <input id="cert-edit-vars" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" value="${(tpl.variables || []).join(', ')}">
                </div>
                <label class="flex items-center gap-2 cursor-pointer">
                    <input id="cert-edit-default" type="checkbox" class="accent-theme" ${tpl.is_default ? 'checked' : ''}>
                    <span class="text-xs text-dc-text">Set as Default Template</span>
                </label>
                <button onclick="TOC.stats.confirmEditTemplate('${id}')" class="w-full py-2.5 rounded-lg bg-theme text-dc-bg font-bold text-sm hover:brightness-110 transition-all">Save Changes</button>
            </div>
        `);
    }

    async function confirmEditTemplate (id) {
        const name = document.getElementById('cert-edit-name')?.value?.trim();
        const vars = (document.getElementById('cert-edit-vars')?.value || '').split(',').map(s => s.trim()).filter(Boolean);
        const is_default = document.getElementById('cert-edit-default')?.checked || false;
        if (!name) return;

        await api(`certificates/${id}/`, {
            method: 'PUT',
            body: JSON.stringify({ name, variables: vars, is_default }),
        });
        closeOverlay();
        loadTemplates();
    }

    async function deleteTemplate (id) {
        if (!confirm('Delete this certificate template? This cannot be undone.')) return;
        await api(`certificates/${id}/`, { method: 'DELETE' });
        loadTemplates();
    }

    function generateSingle (templateId) {
        showOverlay('Generate Certificate', `
            <div class="space-y-4">
                <div>
                    <label class="block text-xs text-dc-text mb-1">User ID</label>
                    <input id="cert-gen-user" type="number" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" placeholder="Enter user ID">
                </div>
                <button onclick="TOC.stats.confirmGenerateSingle('${templateId}')" class="w-full py-2.5 rounded-lg bg-theme text-dc-bg font-bold text-sm hover:brightness-110 transition-all">Generate</button>
            </div>
        `);
    }

    async function confirmGenerateSingle (templateId) {
        const userId = document.getElementById('cert-gen-user')?.value;
        if (!userId) return;
        const result = await api(`certificates/${templateId}/generate/`, {
            method: 'POST',
            body: JSON.stringify({ user_id: parseInt(userId) }),
        });
        closeOverlay();
        if (result.rendered_html) {
            showOverlay('Certificate Preview', `
                <div class="bg-white rounded-lg p-6 text-black">${result.rendered_html}</div>
                <button onclick="TOC.stats.closeOverlay()" class="mt-4 w-full py-2 rounded-lg border border-dc-border text-dc-text text-sm hover:bg-dc-surface transition-colors">Close</button>
            `);
        }
    }

    function openBulkGenerate () {
        if (!state.templates.length) {
            alert('Create a certificate template first.');
            return;
        }
        const opts = state.templates.map(t =>
            `<option value="${t.id}">${esc(t.name)}${t.is_default ? ' (Default)' : ''}</option>`
        ).join('');

        showOverlay('Bulk Generate Certificates', `
            <div class="space-y-4">
                <div>
                    <label class="block text-xs text-dc-text mb-1">Template</label>
                    <select id="bulk-cert-tpl" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                        ${opts}
                    </select>
                </div>
                <p class="text-xs text-dc-text">Generates certificates for all approved participants.</p>
                <button onclick="TOC.stats.confirmBulkGenerate()" class="w-full py-2.5 rounded-lg bg-dc-success text-dc-bg font-bold text-sm hover:brightness-110 transition-all">Generate for All Approved</button>
            </div>
        `);
    }

    async function confirmBulkGenerate () {
        const tplId = document.getElementById('bulk-cert-tpl')?.value;
        if (!tplId) return;

        const btn = document.querySelector('#toc-overlay button[onclick*="confirmBulkGenerate"]');
        if (btn) { btn.disabled = true; btn.textContent = 'Generating...'; }

        const result = await api(`certificates/${tplId}/bulk-generate/`, { method: 'POST' });
        closeOverlay();
        showOverlay('Bulk Generation Complete', `
            <div class="text-center space-y-4 py-4">
                <i data-lucide="check-circle-2" class="w-12 h-12 text-dc-success mx-auto"></i>
                <p class="text-white font-bold">${result.generated} / ${result.total} certificates generated</p>
                <button onclick="TOC.stats.closeOverlay()" class="px-6 py-2 rounded-lg border border-dc-border text-dc-text text-sm hover:bg-dc-surface transition-colors">Close</button>
            </div>
        `);
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    /* ────────────────────────────────────────────
     * S9-F4  Trust Index (injected into participant detail)
     * ──────────────────────────────────────────── */
    async function loadTrustIndex (userId) {
        try {
            const d = await api(`trust/${userId}/`);
            return d;
        } catch (e) {
            console.warn('[TOC.stats] loadTrustIndex failed', e);
            return null;
        }
    }

    async function loadTrustEvents (userId) {
        try {
            return await api(`trust/${userId}/events/`);
        } catch (e) { return []; }
    }

    function renderTrustBadge (trust) {
        if (!trust) return '';
        const colors = {
            excellent: 'text-dc-success bg-dc-success/10 border-dc-success/30',
            good: 'text-dc-info bg-dc-info/10 border-dc-info/30',
            fair: 'text-dc-warning bg-dc-warning/10 border-dc-warning/30',
            poor: 'text-dc-danger bg-dc-danger/10 border-dc-danger/30',
            critical: 'text-red-500 bg-red-500/10 border-red-500/30',
        };
        const cls = colors[trust.rating] || colors.fair;
        return `
            <div class="glass-box rounded-lg p-4 mt-3">
                <div class="flex items-center justify-between mb-2">
                    <span class="text-[10px] font-bold uppercase tracking-widest text-dc-text">Trust Index</span>
                    <span class="text-[10px] font-bold uppercase border px-2 py-0.5 rounded ${cls}">${trust.rating}</span>
                </div>
                <div class="flex items-end gap-3">
                    <span class="text-3xl font-display font-black text-white">${trust.trust_index}</span>
                    <span class="text-xs text-dc-text mb-1">/100 &middot; ${trust.event_count} events</span>
                </div>
                <div class="w-full bg-dc-bg rounded-full h-2 mt-2">
                    <div class="h-2 rounded-full transition-all" style="width:${trust.trust_index}%; background: var(--theme)"></div>
                </div>
            </div>
        `;
    }

    /* ────────────────────────────────────────────
     * Trophies (used in participant drawer)
     * ──────────────────────────────────────────── */
    async function loadUserTrophies (userId) {
        try {
            return await api(`trophies/user/${userId}/`);
        } catch (e) { return []; }
    }

    function renderUserTrophies (trophies) {
        if (!trophies || !trophies.length) return '';
        const rarityColors = {
            common: 'text-dc-text',
            uncommon: 'text-dc-success',
            rare: 'text-dc-info',
            epic: 'text-purple-400',
            legendary: 'text-dc-warning',
        };
        return `
            <div class="glass-box rounded-lg p-4 mt-3">
                <p class="text-[10px] font-bold uppercase tracking-widest text-dc-text mb-2">Trophies</p>
                <div class="flex flex-wrap gap-2">
                    ${trophies.map(t => `
                        <span class="inline-flex items-center gap-1 px-2 py-1 rounded border border-dc-border text-xs ${rarityColors[t.trophy__rarity] || ''}">
                            <i data-lucide="${esc(t.trophy__icon || 'trophy')}" class="w-3 h-3"></i>
                            ${esc(t.trophy__name)}
                        </span>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /* ────────────────────────────────────────────
     * Helpers
     * ──────────────────────────────────────────── */
    function esc (s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

    function showOverlay (title, bodyHtml) {
        let ol = document.getElementById('toc-overlay');
        if (!ol) {
            ol = document.createElement('div');
            ol.id = 'toc-overlay';
            ol.className = 'fixed inset-0 z-[120] flex items-center justify-center';
            document.body.appendChild(ol);
        }
        ol.innerHTML = `
            <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" onclick="TOC.stats.closeOverlay()"></div>
            <div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-lg relative z-10 overflow-hidden">
                <div class="h-1 w-full bg-theme"></div>
                <div class="p-5">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="font-display font-bold text-sm text-white">${title}</h2>
                        <button class="p-1 text-dc-text hover:text-white" onclick="TOC.stats.closeOverlay()"><i data-lucide="x" class="w-4 h-4"></i></button>
                    </div>
                    ${bodyHtml}
                </div>
            </div>
        `;
        ol.classList.remove('hidden');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function closeOverlay () {
        const ol = document.getElementById('toc-overlay');
        if (ol) ol.classList.add('hidden');
    }

    /* ────────────────────────────────────────────
     * Init
     * ──────────────────────────────────────────── */
    function init () {
        loadAdvancedStats();
        loadTemplates();
    }

    /* ── Public API ── */
    NS.stats = {
        init,
        loadAdvancedStats,
        loadTemplates,
        openCreateTemplate,
        confirmCreateTemplate,
        editTemplate,
        confirmEditTemplate,
        deleteTemplate,
        generateSingle,
        confirmGenerateSingle,
        openBulkGenerate,
        confirmBulkGenerate,
        loadTrustIndex,
        loadTrustEvents,
        renderTrustBadge,
        loadUserTrophies,
        renderUserTrophies,
        showOverlay,
        closeOverlay,
    };

})();
