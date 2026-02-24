/**
 * TOC — Participants Advanced Module (Sprint 3)
 *
 * Emergency Subs, Free Agent Pool, Waitlist Management,
 * Guest Team Conversion, Fee Waiver drawer.
 *
 * Namespace: TOC.participantsAdv
 */
(function () {
    'use strict';

    const CFG = window.TOC_CONFIG;
    const API = CFG.apiBase;

    /* ────────────────────────────────────────────────────────────── */
    /* Module state                                                   */
    /* ────────────────────────────────────────────────────────────── */

    const state = {
        emergencySubs: [],
        freeAgents: [],
        waitlist: [],
    };

    /* ────────────────────────────────────────────────────────────── */
    /* Status badge helper                                            */
    /* ────────────────────────────────────────────────────────────── */

    function statusBadge(status) {
        const map = {
            pending:   'bg-dc-warningBg text-dc-warning border-dc-warning/20',
            approved:  'bg-dc-successBg text-dc-success border-dc-success/20',
            denied:    'bg-dc-dangerBg text-dc-danger border-dc-danger/20',
            available: 'bg-dc-infoBg text-dc-info border-dc-info/20',
            assigned:  'bg-dc-successBg text-dc-success border-dc-success/20',
            drafted:   'bg-theme-surface text-theme border-theme-border',
            withdrawn: 'bg-dc-dangerBg text-dc-danger border-dc-danger/20',
            expired:   'bg-dc-panel text-dc-text border-dc-border',
        };
        const cls = map[status] || 'bg-dc-panel text-dc-text border-dc-border';
        return `<span class="px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border ${cls}">${status}</span>`;
    }

    function timeAgo(iso) {
        if (!iso) return '—';
        const d = new Date(iso);
        const diff = Math.floor((Date.now() - d.getTime()) / 1000);
        if (diff < 60) return 'just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return d.toLocaleDateString();
    }

    /* ════════════════════════════════════════════════════════════════ */
    /* S3-F1: Emergency Substitution Panel                            */
    /* ════════════════════════════════════════════════════════════════ */

    async function refreshEmergencySubs() {
        try {
            const resp = await TOC.fetch(`${API}/emergency-subs/`);
            state.emergencySubs = resp.results || [];
            renderEmergencySubs();
        } catch (e) {
            console.error('[TOC:PartAdv] Failed to load emergency subs:', e);
        }
    }

    function renderEmergencySubs() {
        const list = document.getElementById('esub-list');
        const badge = document.getElementById('esub-count');
        if (!list) return;

        const pending = state.emergencySubs.filter(s => s.status === 'pending');

        if (badge) {
            badge.textContent = String(state.emergencySubs.length);
            badge.classList.toggle('hidden', state.emergencySubs.length === 0);
        }

        if (state.emergencySubs.length === 0) {
            list.innerHTML = `
                <div class="text-center py-8 text-dc-text text-xs">
                    <i data-lucide="check-circle" class="w-8 h-8 mx-auto mb-2 opacity-30"></i>
                    <p>No substitution requests</p>
                </div>`;
            lucide.createIcons({ nodes: [list] });
            return;
        }

        list.innerHTML = state.emergencySubs.map(sub => `
            <div class="bg-dc-bg border border-dc-border rounded-lg p-4 hover:border-dc-borderLight transition-colors">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2">
                        ${statusBadge(sub.status)}
                        <span class="text-[9px] text-dc-text font-mono">${timeAgo(sub.created_at)}</span>
                    </div>
                    <span class="text-[9px] text-dc-text font-mono">REG #${sub.registration_id}</span>
                </div>
                <div class="flex items-center gap-3 mb-3">
                    <div class="flex items-center gap-2">
                        <div class="w-7 h-7 rounded-lg bg-dc-dangerBg border border-dc-danger/20 flex items-center justify-center">
                            <i data-lucide="user-minus" class="w-3.5 h-3.5 text-dc-danger"></i>
                        </div>
                        <div>
                            <p class="text-xs font-bold text-white">${sub.dropping_player || '—'}</p>
                            <p class="text-[9px] text-dc-text">Dropping</p>
                        </div>
                    </div>
                    <i data-lucide="arrow-right" class="w-4 h-4 text-dc-text"></i>
                    <div class="flex items-center gap-2">
                        <div class="w-7 h-7 rounded-lg bg-dc-successBg border border-dc-success/20 flex items-center justify-center">
                            <i data-lucide="user-plus" class="w-3.5 h-3.5 text-dc-success"></i>
                        </div>
                        <div>
                            <p class="text-xs font-bold text-white">${sub.substitute_player || '—'}</p>
                            <p class="text-[9px] text-dc-text">Substitute</p>
                        </div>
                    </div>
                </div>
                <p class="text-[11px] text-dc-text mb-3 italic">"${sub.reason}"</p>
                ${sub.status === 'pending' ? `
                <div class="flex items-center gap-2 pt-2 border-t border-dc-border/50">
                    <button onclick="TOC.participantsAdv.approveEmergencySub('${sub.id}')" class="flex-1 px-3 py-1.5 bg-dc-success/10 border border-dc-success/20 text-dc-success text-[10px] font-bold uppercase tracking-widest rounded hover:bg-dc-success/20 transition-colors">
                        <i data-lucide="check" class="w-3 h-3 inline-block mr-1"></i> Approve
                    </button>
                    <button onclick="TOC.participantsAdv.denyEmergencySub('${sub.id}')" class="flex-1 px-3 py-1.5 bg-dc-danger/10 border border-dc-danger/20 text-dc-danger text-[10px] font-bold uppercase tracking-widest rounded hover:bg-dc-danger/20 transition-colors">
                        <i data-lucide="x" class="w-3 h-3 inline-block mr-1"></i> Deny
                    </button>
                </div>` : `
                <div class="pt-2 border-t border-dc-border/50 text-[10px] text-dc-text">
                    Reviewed by <span class="text-white font-bold">${sub.reviewed_by || '—'}</span>
                    ${sub.review_notes ? ` — "${sub.review_notes}"` : ''}
                </div>`}
            </div>
        `).join('');

        lucide.createIcons({ nodes: [list] });
    }

    async function approveEmergencySub(subId) {
        try {
            const result = await TOC.fetch(`${API}/emergency-subs/${subId}/approve/`, {
                method: 'POST', body: JSON.stringify({ notes: '' }),
            });
            TOC.toast('Emergency sub approved', 'success');
            await refreshEmergencySubs();
        } catch (e) {
            TOC.toast(e.message || 'Failed to approve', 'error');
        }
    }

    async function denyEmergencySub(subId) {
        try {
            const result = await TOC.fetch(`${API}/emergency-subs/${subId}/deny/`, {
                method: 'POST', body: JSON.stringify({ notes: '' }),
            });
            TOC.toast('Emergency sub denied', 'success');
            await refreshEmergencySubs();
        } catch (e) {
            TOC.toast(e.message || 'Failed to deny', 'error');
        }
    }

    /* ════════════════════════════════════════════════════════════════ */
    /* S3-F2: Free Agent Pool                                         */
    /* ════════════════════════════════════════════════════════════════ */

    async function refreshFreeAgents() {
        try {
            const statusVal = document.getElementById('fa-status-filter')?.value || '';
            const params = new URLSearchParams();
            if (statusVal) params.set('status', statusVal);

            const resp = await TOC.fetch(`${API}/free-agents/?${params.toString()}`);
            state.freeAgents = resp.results || [];
            renderFreeAgents();
        } catch (e) {
            console.error('[TOC:PartAdv] Failed to load free agents:', e);
        }
    }

    function renderFreeAgents() {
        const tbody = document.getElementById('fa-tbody');
        const badge = document.getElementById('fa-count');
        if (!tbody) return;

        if (badge) {
            badge.textContent = String(state.freeAgents.length);
            badge.classList.toggle('hidden', state.freeAgents.length === 0);
        }

        if (state.freeAgents.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="px-3 py-8 text-center text-dc-text text-xs">No free agents registered</td></tr>`;
            return;
        }

        tbody.innerHTML = state.freeAgents.map(fa => `
            <tr class="border-b border-dc-border/50 hover:bg-dc-panel/50 transition-colors">
                <td class="px-3 py-2.5">
                    <div class="flex items-center gap-2">
                        <div class="w-6 h-6 rounded bg-dc-panel border border-dc-borderLight flex items-center justify-center text-[9px] font-bold text-white">
                            ${(fa.username || '?')[0].toUpperCase()}
                        </div>
                        <span class="text-xs font-bold text-white">${fa.username || '—'}</span>
                    </div>
                </td>
                <td class="px-3 py-2.5 text-xs text-dc-text">${fa.preferred_role || '—'}</td>
                <td class="px-3 py-2.5 text-xs text-dc-text">${fa.rank_info || '—'}</td>
                <td class="px-3 py-2.5 text-xs text-dc-text font-mono">${fa.game_id || '—'}</td>
                <td class="px-3 py-2.5">${statusBadge(fa.status)}</td>
                <td class="px-3 py-2.5 text-right">
                    ${fa.status === 'available' ? `
                        <button onclick="TOC.participantsAdv.openAssignDrawer('${fa.id}', '${fa.username}')" class="px-2 py-1 bg-theme-surface border border-theme-border text-theme text-[9px] font-bold rounded hover:bg-theme hover:text-dc-bg transition-all">
                            Assign
                        </button>
                    ` : `
                        <span class="text-[9px] text-dc-text">${fa.assigned_to_team || '—'}</span>
                    `}
                </td>
            </tr>
        `).join('');

        lucide.createIcons({ nodes: [tbody] });
    }

    function openAssignDrawer(faId, username) {
        TOC.drawer.open(
            `Assign Free Agent: ${username}`,
            `<div class="space-y-4">
                <div class="bg-dc-panel border border-dc-borderLight rounded-lg p-3">
                    <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-2">Team ID</label>
                    <input id="fa-assign-team-id" type="number" class="w-full bg-dc-bg border border-dc-border rounded px-3 py-2 text-white text-xs focus:border-theme outline-none" placeholder="Enter team ID">
                </div>
                <button onclick="TOC.participantsAdv.confirmAssign('${faId}')" class="w-full py-2.5 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:brightness-110 transition-all shadow-[0_0_15px_var(--color-primary-muted)]">
                    Assign to Team
                </button>
            </div>`
        );
    }

    async function confirmAssign(faId) {
        const teamId = document.getElementById('fa-assign-team-id')?.value;
        if (!teamId) { TOC.toast('Team ID required', 'error'); return; }

        try {
            await TOC.fetch(`${API}/free-agents/${faId}/assign/`, {
                method: 'POST', body: JSON.stringify({ team_id: parseInt(teamId) }),
            });
            TOC.toast('Free agent assigned', 'success');
            TOC.drawer.close();
            await refreshFreeAgents();
        } catch (e) {
            TOC.toast(e.message || 'Failed to assign', 'error');
        }
    }

    /* ════════════════════════════════════════════════════════════════ */
    /* S3-F3: Waitlist Management                                     */
    /* ════════════════════════════════════════════════════════════════ */

    async function refreshWaitlist() {
        try {
            const resp = await TOC.fetch(`${API}/waitlist/`);
            state.waitlist = resp.results || [];
            renderWaitlist();
        } catch (e) {
            console.error('[TOC:PartAdv] Failed to load waitlist:', e);
        }
    }

    function renderWaitlist() {
        const list = document.getElementById('waitlist-list');
        const badge = document.getElementById('waitlist-count');
        if (!list) return;

        if (badge) {
            badge.textContent = String(state.waitlist.length);
            badge.classList.toggle('hidden', state.waitlist.length === 0);
        }

        if (state.waitlist.length === 0) {
            list.innerHTML = `
                <div class="text-center py-8 text-dc-text text-xs">
                    <i data-lucide="check-circle" class="w-8 h-8 mx-auto mb-2 opacity-30"></i>
                    <p>Waitlist is empty</p>
                </div>`;
            lucide.createIcons({ nodes: [list] });
            return;
        }

        list.innerHTML = state.waitlist.map((w, idx) => `
            <div class="flex items-center justify-between bg-dc-bg border border-dc-border rounded-lg px-4 py-3 hover:border-dc-borderLight transition-colors">
                <div class="flex items-center gap-3">
                    <div class="w-7 h-7 rounded-lg bg-dc-panel border border-dc-borderLight flex items-center justify-center text-[10px] font-mono font-bold text-dc-warning">
                        #${w.position || idx + 1}
                    </div>
                    <div>
                        <p class="text-xs font-bold text-white">${w.participant_name}</p>
                        <p class="text-[9px] text-dc-text font-mono">${w.registration_number || ''} · ${timeAgo(w.registered_at)}</p>
                    </div>
                </div>
                <button onclick="TOC.participantsAdv.promoteWaitlist(${w.id})" class="px-3 py-1.5 bg-dc-success/10 border border-dc-success/20 text-dc-success text-[10px] font-bold uppercase tracking-widest rounded hover:bg-dc-success/20 transition-colors">
                    <i data-lucide="arrow-up" class="w-3 h-3 inline-block mr-1"></i> Promote
                </button>
            </div>
        `).join('');

        lucide.createIcons({ nodes: [list] });
    }

    async function promoteWaitlist(regId) {
        try {
            const result = await TOC.fetch(`${API}/participants/${regId}/promote-waitlist/`, {
                method: 'POST',
            });
            TOC.toast(result.message || 'Promoted from waitlist', 'success');
            await refreshWaitlist();
            // Also refresh the main participant grid
            if (TOC.participants && TOC.participants.refresh) {
                TOC.participants.refresh();
            }
        } catch (e) {
            TOC.toast(e.message || 'Failed to promote', 'error');
        }
    }

    async function autoPromote() {
        try {
            const result = await TOC.fetch(`${API}/participants/auto-promote/`, {
                method: 'POST',
            });
            TOC.toast(result.message || 'Auto-promote completed', result.promoted ? 'success' : 'info');
            await refreshWaitlist();
            if (TOC.participants && TOC.participants.refresh) {
                TOC.participants.refresh();
            }
        } catch (e) {
            TOC.toast(e.message || 'Failed to auto-promote', 'error');
        }
    }

    /* ════════════════════════════════════════════════════════════════ */
    /* S3-F4: Guest Team Conversion                                   */
    /* ════════════════════════════════════════════════════════════════ */

    async function convertGuest(regId) {
        try {
            const result = await TOC.fetch(`${API}/participants/${regId}/convert-guest/`, {
                method: 'POST',
            });
            TOC.toast(result.message || 'Guest team converted', 'success');
            if (TOC.participants && TOC.participants.refresh) {
                TOC.participants.refresh();
            }
        } catch (e) {
            TOC.toast(e.message || 'Failed to convert', 'error');
        }
    }

    /* ════════════════════════════════════════════════════════════════ */
    /* S3-F5: Fee Waiver Drawer                                       */
    /* ════════════════════════════════════════════════════════════════ */

    function openFeeWaiverDrawer(regId, participantName) {
        TOC.drawer.open(
            `Fee Waiver: ${participantName}`,
            `<div class="space-y-4">
                <div class="bg-dc-warningBg border border-dc-warning/20 rounded-lg p-3 text-center">
                    <i data-lucide="badge-percent" class="w-6 h-6 text-dc-warning mx-auto mb-1"></i>
                    <p class="text-xs text-dc-warning font-bold">Waive Entry Fee</p>
                    <p class="text-[10px] text-dc-text mt-1">This will set payment status to WAIVED.</p>
                </div>
                <div class="bg-dc-panel border border-dc-borderLight rounded-lg p-3">
                    <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-2">Reason (required)</label>
                    <textarea id="waiver-reason" rows="3" class="w-full bg-dc-bg border border-dc-border rounded px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none" placeholder="e.g., Top-ranked team, sponsor invitation..."></textarea>
                </div>
                <button onclick="TOC.participantsAdv.confirmFeeWaiver(${regId})" class="w-full py-2.5 bg-dc-warning text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:brightness-110 transition-all">
                    Confirm Fee Waiver
                </button>
            </div>`,
            null
        );
        // Re-render lucide icons in the drawer
        setTimeout(() => { lucide.createIcons(); }, 50);
    }

    async function confirmFeeWaiver(regId) {
        const reason = document.getElementById('waiver-reason')?.value?.trim();
        if (!reason) { TOC.toast('Waiver reason is required', 'error'); return; }

        try {
            const result = await TOC.fetch(`${API}/participants/${regId}/fee-waiver/`, {
                method: 'POST', body: JSON.stringify({ reason }),
            });
            TOC.toast(result.message || 'Fee waived', 'success');
            TOC.drawer.close();
            if (TOC.participants && TOC.participants.refresh) {
                TOC.participants.refresh();
            }
        } catch (e) {
            TOC.toast(e.message || 'Failed to waive fee', 'error');
        }
    }

    /* ════════════════════════════════════════════════════════════════ */
    /* Init — load data when participants tab activates               */
    /* ════════════════════════════════════════════════════════════════ */

    function init() {
        refreshEmergencySubs();
        refreshFreeAgents();
        refreshWaitlist();
    }

    // Listen for tab activation
    const origNavigate = TOC.navigate;
    if (origNavigate) {
        TOC.navigate = function (tabId) {
            origNavigate(tabId);
            if (tabId === 'participants') {
                // Small delay to ensure DOM is visible
                setTimeout(init, 100);
            }
        };
    }

    // Auto-init if participants tab is already active
    document.addEventListener('DOMContentLoaded', () => {
        const view = document.getElementById('view-participants');
        if (view && !view.classList.contains('hidden-view')) {
            setTimeout(init, 300);
        }
    });

    /* ════════════════════════════════════════════════════════════════ */
    /* Export to TOC namespace                                        */
    /* ════════════════════════════════════════════════════════════════ */

    window.TOC = window.TOC || {};
    window.TOC.participantsAdv = {
        init,
        refreshEmergencySubs,
        approveEmergencySub,
        denyEmergencySub,
        refreshFreeAgents,
        openAssignDrawer,
        confirmAssign,
        refreshWaitlist,
        promoteWaitlist,
        autoPromote,
        convertGuest,
        openFeeWaiverDrawer,
        confirmFeeWaiver,
    };

})();
