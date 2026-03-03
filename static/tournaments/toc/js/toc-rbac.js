/**
 * TOC Sprint 10H — RBAC & Economy Integration
 * =============================================
 * S10-F1  Staff management section in Settings (Radio Card assign modal)
 * S10-F2  Permission-gated UI (tab-level + element-level capability RBAC)
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

    function _renderCapBadges (caps) {
        if (!caps || typeof caps !== 'object') return '';
        var keys = Object.keys(caps).filter(function (k) { return caps[k] && k !== 'full_access'; });
        if (!keys.length) return '';
        return '<div class="flex flex-wrap gap-1 mt-1.5">' +
            keys.map(function (k) {
                var label = k.replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); });
                return '<span class="text-[9px] font-bold uppercase tracking-wider bg-theme/10 text-theme/80 px-1.5 py-0.5 rounded">' + esc(label) + '</span>';
            }).join('') + '</div>';
    }

    function openAssignStaff () {
        var roleCards = '';
        for (var i = 0; i < state.roles.length; i++) {
            var r = state.roles[i];
            var isFirst = i === 0;
            roleCards += '<label class="staff-role-card group flex items-start gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all '
                + (isFirst ? 'border-theme bg-theme/5' : 'border-dc-border hover:border-theme/40 bg-dc-surface/50')
                + '" data-role-card="' + r.id + '">'
                + '<input type="radio" name="staff-role-radio" value="' + r.id + '"' + (isFirst ? ' checked' : '')
                + ' class="mt-0.5 accent-[var(--theme-color,#f59e0b)]" onchange="TOC.rbac._onRoleCardChange(this)">'
                + '<div class="flex-1 min-w-0">'
                + '<p class="text-sm font-bold text-white leading-tight">' + esc(r.name) + '</p>'
                + '<p class="text-[11px] text-dc-text mt-0.5 leading-snug">' + esc(r.description || '') + '</p>'
                + _renderCapBadges(r.capabilities)
                + '</div>'
                + '</label>';
        }

        var body = '<div class="space-y-4">'
            + '<div>'
            + '<label class="block text-xs text-dc-text mb-1">Search User (username or email)</label>'
            + '<input id="staff-user-search" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50" placeholder="Type username or email\u2026" autocomplete="off">'
            + '<div id="staff-user-results" class="mt-1 max-h-40 overflow-y-auto hidden border border-dc-border rounded-lg bg-dc-surface"></div>'
            + '<input id="staff-user-id" type="hidden">'
            + '<div id="staff-user-selected" class="mt-1 text-xs text-dc-success hidden"></div>'
            + '</div>'
            + '<div>'
            + '<label class="block text-xs font-bold uppercase tracking-widest text-dc-text mb-2">Select Role</label>'
            + '<div id="staff-role-cards" class="space-y-2 max-h-60 overflow-y-auto pr-1">'
            + (roleCards || '<p class="text-xs text-dc-text italic text-center py-4">No roles available. Seed roles first.</p>')
            + '</div>'
            + '</div>'
            + '<button onclick="TOC.rbac.confirmAssignStaff()" class="w-full py-2.5 rounded-lg bg-theme text-dc-bg font-bold text-sm hover:brightness-110 transition-all">Assign Staff Member</button>'
            + '</div>';

        showOverlay('Assign Staff Member', body);

        // Wire up live search with debounce
        var debounce = null;
        var input = document.getElementById('staff-user-search');
        if (input) {
            input.addEventListener('input', function () {
                clearTimeout(debounce);
                debounce = setTimeout(function () { _searchUsers(input.value.trim()); }, 300);
            });
        }
    }

    function _onRoleCardChange (radio) {
        document.querySelectorAll('.staff-role-card').forEach(function (card) {
            card.classList.remove('border-theme', 'bg-theme/5');
            card.classList.add('border-dc-border', 'bg-dc-surface/50');
        });
        var card = radio.closest('.staff-role-card');
        if (card) {
            card.classList.remove('border-dc-border', 'bg-dc-surface/50');
            card.classList.add('border-theme', 'bg-theme/5');
        }
    }

    async function _searchUsers (q) {
        const resultsEl = document.getElementById('staff-user-results');
        if (!resultsEl) return;
        if (q.length < 2) { resultsEl.classList.add('hidden'); return; }

        try {
            const users = await api(`users/search/?q=${encodeURIComponent(q)}`);
            if (!users.length) {
                resultsEl.innerHTML = '<div class="p-2 text-xs text-dc-text italic">No users found</div>';
            } else {
                resultsEl.innerHTML = users.map(u => `
                    <button type="button" onclick="TOC.rbac.selectUser(${u.id}, '${esc(u.username).replace(/'/g, "\\'")}', '${esc(u.email).replace(/'/g, "\\'")}')"
                        class="w-full text-left px-3 py-2 text-sm text-dc-textBright hover:bg-theme/10 flex items-center gap-2 border-b border-dc-border last:border-0">
                        <span class="font-bold">${esc(u.username)}</span>
                        <span class="text-xs text-dc-text">${esc(u.email)}</span>
                    </button>
                `).join('');
            }
            resultsEl.classList.remove('hidden');
        } catch (e) {
            resultsEl.innerHTML = '<div class="p-2 text-xs text-dc-danger">Search failed</div>';
            resultsEl.classList.remove('hidden');
        }
    }

    function selectUser (id, username, email) {
        document.getElementById('staff-user-id').value = id;
        document.getElementById('staff-user-search').value = username;
        const selectedEl = document.getElementById('staff-user-selected');
        if (selectedEl) {
            selectedEl.textContent = `\u2714 ${username} (${email}) \u2014 ID ${id}`;
            selectedEl.classList.remove('hidden');
        }
        document.getElementById('staff-user-results')?.classList.add('hidden');
    }

    async function confirmAssignStaff () {
        const userId = document.getElementById('staff-user-id')?.value;
        const checkedRadio = document.querySelector('input[name="staff-role-radio"]:checked');
        const roleId = checkedRadio ? checkedRadio.value : null;
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
            enforceCapabilityRBAC();
        } catch (e) {
            console.warn('[TOC.rbac] loadPermissions failed', e);
        }
    }

    /** Resolve the user's capability set from the injected window variable + API response */
    function _getCaps () {
        // Prefer the server-injected capabilities; fall back to API response
        var caps = window.TOC_USER_CAPABILITIES || [];
        if (state.permissions && state.permissions.capabilities && state.permissions.capabilities.length) {
            caps = state.permissions.capabilities;
        }
        return caps;
    }

    function _hasCap (cap) {
        var caps = _getCaps();
        return caps.indexOf('full_access') !== -1 || caps.indexOf(cap) !== -1;
    }

    function applyPermissionGating () {
        var p = state.permissions;
        if (!p) return;

        // If full access or organizer — leave everything visible
        if (p.tabs === '*' || p.is_organizer || _hasCap('full_access')) return;

        var allowed = new Set(Array.isArray(p.tabs) ? p.tabs : []);

        // Hide tab buttons for unauthorized tabs
        document.querySelectorAll('[data-tab]').forEach(function (btn) {
            var tab = btn.getAttribute('data-tab');
            if (tab && !allowed.has(tab)) {
                btn.style.opacity = '0.3';
                btn.style.pointerEvents = 'none';
                btn.title = 'No access';
            }
        });

        // Hide views for unauthorized tabs
        document.querySelectorAll('[data-tab-content]').forEach(function (view) {
            var tab = view.getAttribute('data-tab-content');
            if (tab && !allowed.has(tab)) {
                view.classList.add('hidden');
            }
        });
    }

    /**
     * S10-F2b – Element-level capability enforcement.
     * Disables / hides individual interactive elements based on current user capabilities.
     * MUST be called on page init AND on every tab switch.
     */
    function enforceCapabilityRBAC () {
        if (_hasCap('full_access')) return;   // full_access → no restrictions

        // ── Settings tab inputs ──────────────────────
        if (!_hasCap('edit_settings')) {
            _disableAll('[data-tab-content="settings"] input, [data-tab-content="settings"] select, [data-tab-content="settings"] textarea');
            _hideAll('[data-tab-content="settings"] button[type="submit"], [data-cap-require="edit_settings"]');
        }

        // ── Payment approve / reject buttons ─────────
        if (!_hasCap('approve_payments')) {
            _hideAll('[data-cap-require="approve_payments"], .btn-verify-payment, .btn-reject-payment');
        }

        // ── Bracket / match management ───────────────
        if (!_hasCap('manage_brackets')) {
            _disableAll('[data-cap-require="manage_brackets"]');
            _hideAll('.btn-generate-bracket, .btn-reset-bracket, .btn-advance-round');
        }

        // ── Registrations ────────────────────────────
        if (!_hasCap('manage_registrations')) {
            _hideAll('[data-cap-require="manage_registrations"], .btn-approve-reg, .btn-reject-reg');
        }

        // ── Announcements ────────────────────────────
        if (!_hasCap('make_announcements')) {
            _hideAll('[data-cap-require="make_announcements"]');
            _disableAll('[data-tab-content="announcements"] textarea, [data-tab-content="announcements"] button[type="submit"]');
        }

        // ── Disputes ─────────────────────────────────
        if (!_hasCap('resolve_disputes')) {
            _disableAll('[data-cap-require="resolve_disputes"]');
        }

        // ── Generic data-cap-require fallback ────────
        document.querySelectorAll('[data-cap-require]').forEach(function (el) {
            var req = el.getAttribute('data-cap-require');
            if (req && !_hasCap(req)) {
                el.style.display = 'none';
            }
        });
    }

    function _disableAll (selector) {
        document.querySelectorAll(selector).forEach(function (el) {
            el.disabled = true;
            el.classList.add('opacity-40', 'pointer-events-none');
            el.title = 'Insufficient permissions';
        });
    }

    function _hideAll (selector) {
        document.querySelectorAll(selector).forEach(function (el) {
            el.style.display = 'none';
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
        selectUser,
        removeStaff,
        loadPermissions,
        applyPermissionGating,
        enforceCapabilityRBAC,
        _onRoleCardChange,
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

    // Auto-init when navigating to Settings tab (staff section lives there)
    document.addEventListener('toc:tab-changed', function (e) {
        if (e.detail?.tab === 'settings') init();
        // Re-enforce RBAC on every tab switch
        enforceCapabilityRBAC();
    });

})();
