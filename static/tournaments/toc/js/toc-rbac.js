/**
 * TOC Sprint 10 — RBAC & Economy Integration
 * =============================================
 * S10-F1  Staff management section in Settings
 * S10-F2  Permission-gated UI
 * S10-F3  DeltaCoin balance display in Payments tab
 * S10-F4  Wallet transaction history in participant drawer
 */
;(function () {
    'use strict';

    const NS = (window.TOC = window.TOC || {});
    const api = (ep, opts) => NS.api(ep, opts);

    const state = {
        staff: [],
        roles: [],
        permissions: null,
    };

    /* ────────────────────────────────────────────
     * S10-F1  Staff Management
     * ──────────────────────────────────────────── */
    async function loadStaff () {
        try {
            const [staff, roles] = await Promise.all([
                api('staff/'),
                api('roles/'),
            ]);
            state.staff = staff;
            state.roles = roles;
            renderStaff();
        } catch (e) {
            console.warn('[TOC.rbac] loadStaff failed', e);
        }
    }

    function renderStaff () {
        const grid = document.getElementById('staff-grid');
        if (!grid) return;

        if (!state.staff.length) {
            grid.innerHTML = '<p class="text-xs text-dc-text italic text-center py-6">No staff assigned yet.</p>';
            return;
        }

        grid.innerHTML = state.staff.map(s => `
            <div class="glass-box rounded-lg p-3 flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-dc-info/10 border border-dc-info/30 flex items-center justify-center">
                        <i data-lucide="user" class="w-4 h-4 text-dc-info"></i>
                    </div>
                    <div>
                        <span class="text-sm font-bold text-white">${esc(s.display_name || s.username)}</span>
                        <span class="text-[10px] font-bold uppercase bg-dc-info/20 text-dc-info px-2 py-0.5 rounded ml-2">${esc(s.role_name)}</span>
                    </div>
                </div>
                <button onclick="TOC.rbac.removeStaff(${s.id})" class="p-1.5 text-dc-text hover:text-dc-danger rounded hover:bg-dc-danger/10 transition-colors" title="Remove">
                    <i data-lucide="user-minus" class="w-3.5 h-3.5"></i>
                </button>
            </div>
        `).join('');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function openAssignStaff () {
        const roleOpts = state.roles.map(r =>
            `<option value="${r.id}">${esc(r.name)}</option>`
        ).join('');

        showOverlay('Assign Staff Member', `
            <div class="space-y-4">
                <div>
                    <label class="block text-xs text-dc-text mb-1">User ID</label>
                    <input id="staff-user-id" type="number" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" placeholder="Enter user ID">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Role</label>
                    <select id="staff-role" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                        ${roleOpts}
                    </select>
                </div>
                <button onclick="TOC.rbac.confirmAssignStaff()" class="w-full py-2.5 rounded-lg bg-theme text-dc-bg font-bold text-sm hover:brightness-110 transition-all">Assign</button>
            </div>
        `);
    }

    async function confirmAssignStaff () {
        const userId = document.getElementById('staff-user-id')?.value;
        const roleId = document.getElementById('staff-role')?.value;
        if (!userId || !roleId) return;

        await api('staff/', {
            method: 'POST',
            body: JSON.stringify({ user_id: parseInt(userId), role_id: parseInt(roleId) }),
        });
        closeOverlay();
        loadStaff();
    }

    async function removeStaff (assignmentId) {
        if (!confirm('Remove this staff member?')) return;
        await api(`staff/${assignmentId}/`, { method: 'DELETE' });
        loadStaff();
    }

    /* ────────────────────────────────────────────
     * S10-F2  Permission-gated UI
     * ──────────────────────────────────────────── */
    async function loadPermissions () {
        try {
            state.permissions = await api('permissions/');
            applyPermissionGating();
        } catch (e) {
            console.warn('[TOC.rbac] loadPermissions failed', e);
        }
    }

    function applyPermissionGating () {
        const p = state.permissions;
        if (!p) return;

        // If full access, do nothing
        if (p.tabs === '*' || p.is_organizer) return;

        const allowed = new Set(p.tabs || []);

        // Hide tab buttons for unauthorized tabs
        document.querySelectorAll('[data-tab]').forEach(btn => {
            const tab = btn.getAttribute('data-tab');
            if (tab && !allowed.has(tab)) {
                btn.style.opacity = '0.3';
                btn.style.pointerEvents = 'none';
                btn.title = 'No access';
            }
        });

        // Hide views for unauthorized tabs
        document.querySelectorAll('[data-tab-content]').forEach(view => {
            const tab = view.getAttribute('data-tab-content');
            if (tab && !allowed.has(tab)) {
                view.classList.add('hidden');
            }
        });
    }

    /* ────────────────────────────────────────────
     * S10-F3 / F4  DeltaCoin Economy
     * ──────────────────────────────────────────── */
    async function loadEconomyPoolBalance () {
        // Display organizer's DeltaCoin or a generic pool indicator
        const el = document.getElementById('economy-pool-balance');
        if (!el) return;
        try {
            const d = await api(`economy/balance/0/`);
            el.textContent = d.balance + ' DC';
        } catch (e) {
            el.textContent = 'N/A';
        }
    }

    async function loadUserTransactions (userId) {
        try {
            return await api(`economy/transactions/${userId}/`);
        } catch (e) { return []; }
    }

    function renderTransactionHistory (transactions) {
        if (!transactions || !transactions.length) return '<p class="text-xs text-dc-text italic">No transactions.</p>';
        return `
            <div class="glass-box rounded-lg p-4 mt-3">
                <p class="text-[10px] font-bold uppercase tracking-widest text-dc-text mb-2">DeltaCoin Transactions</p>
                <div class="space-y-2 max-h-40 overflow-y-auto">
                    ${transactions.map(t => `
                        <div class="flex items-center justify-between text-xs">
                            <span class="text-dc-text">${esc(t.description || t.transaction_type)}</span>
                            <span class="${parseFloat(t.amount) >= 0 ? 'text-dc-success' : 'text-dc-danger'} font-mono font-bold">${parseFloat(t.amount) >= 0 ? '+' : ''}${t.amount} DC</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    function processEntryFee () {
        showOverlay('Process Entry Fee', `
            <div class="space-y-4">
                <div>
                    <label class="block text-xs text-dc-text mb-1">User ID</label>
                    <input id="fee-user-id" type="number" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Amount (leave blank for configured fee)</label>
                    <input id="fee-amount" type="number" step="0.01" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <button onclick="TOC.rbac.confirmProcessFee()" class="w-full py-2.5 rounded-lg bg-theme text-dc-bg font-bold text-sm hover:brightness-110 transition-all">Deduct Fee</button>
            </div>
        `);
    }

    async function confirmProcessFee () {
        const userId = document.getElementById('fee-user-id')?.value;
        if (!userId) return;
        const amount = document.getElementById('fee-amount')?.value || null;

        const result = await api('economy/entry-fee/', {
            method: 'POST',
            body: JSON.stringify({ user_id: parseInt(userId), amount: amount ? parseFloat(amount) : null }),
        });
        closeOverlay();
        alert(`Entry fee: ${result.status}${result.deducted ? ' — ' + result.deducted + ' DC' : ''}`);
    }

    function distributePrize () {
        showOverlay('Distribute DeltaCoin Prize', `
            <div class="space-y-4">
                <div>
                    <label class="block text-xs text-dc-text mb-1">User ID</label>
                    <input id="prize-user-id" type="number" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Amount</label>
                    <input id="prize-amount" type="number" step="0.01" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Description</label>
                    <input id="prize-desc" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" placeholder="1st Place Prize">
                </div>
                <button onclick="TOC.rbac.confirmDistributePrize()" class="w-full py-2.5 rounded-lg bg-dc-warning text-dc-bg font-bold text-sm hover:brightness-110 transition-all">Distribute</button>
            </div>
        `);
    }

    async function confirmDistributePrize () {
        const userId = document.getElementById('prize-user-id')?.value;
        const amount = document.getElementById('prize-amount')?.value;
        if (!userId || !amount) return;
        const desc = document.getElementById('prize-desc')?.value || '';

        const result = await api('economy/distribute-prize/', {
            method: 'POST',
            body: JSON.stringify({ user_id: parseInt(userId), amount: parseFloat(amount), description: desc }),
        });
        closeOverlay();
        alert(`Prize: ${result.status}${result.credited ? ' — ' + result.credited + ' DC' : ''}`);
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
            <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" onclick="TOC.rbac.closeOverlay()"></div>
            <div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-lg relative z-10 overflow-hidden">
                <div class="h-1 w-full bg-theme"></div>
                <div class="p-5">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="font-display font-bold text-sm text-white">${title}</h2>
                        <button class="p-1 text-dc-text hover:text-white" onclick="TOC.rbac.closeOverlay()"><i data-lucide="x" class="w-4 h-4"></i></button>
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
        loadPermissions();
        loadStaff();
        loadEconomyPoolBalance();
    }

    /* ── Public API ── */
    NS.rbac = {
        init,
        loadStaff,
        openAssignStaff,
        confirmAssignStaff,
        removeStaff,
        loadPermissions,
        applyPermissionGating,
        loadEconomyPoolBalance,
        loadUserTransactions,
        renderTransactionHistory,
        processEntryFee,
        confirmProcessFee,
        distributePrize,
        confirmDistributePrize,
        showOverlay,
        closeOverlay,
    };

})();
