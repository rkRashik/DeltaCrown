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

    function esc(s) {
        const d = document.createElement('div');
        d.textContent = s ?? '';
        return d.innerHTML;
    }

    const state = {
        emergencySubs: [],
        freeAgents: [],
        waitlist: [],
        disqualified: [],
        disqualifiedFilter: '',
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
        return `<span class="px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider border ${cls}">${esc(status)}</span>`;
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

    function errorMessage(err, fallback) {
        return (err && err.message) ? err.message : fallback;
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
                            <p class="text-xs font-bold text-white">${esc(sub.dropping_player || '—')}</p>
                            <p class="text-[9px] text-dc-text">Dropping</p>
                        </div>
                    </div>
                    <i data-lucide="arrow-right" class="w-4 h-4 text-dc-text"></i>
                    <div class="flex items-center gap-2">
                        <div class="w-7 h-7 rounded-lg bg-dc-successBg border border-dc-success/20 flex items-center justify-center">
                            <i data-lucide="user-plus" class="w-3.5 h-3.5 text-dc-success"></i>
                        </div>
                        <div>
                            <p class="text-xs font-bold text-white">${esc(sub.substitute_player || '—')}</p>
                            <p class="text-[9px] text-dc-text">Substitute</p>
                        </div>
                    </div>
                </div>
                <p class="text-[11px] text-dc-text mb-3 italic">"${esc(sub.reason)}"</p>
                ${sub.status === 'pending' ? `
                <div class="flex items-center gap-2 pt-2 border-t border-dc-border/50">
                    <button data-click="TOC.participantsAdv.approveEmergencySub" data-click-args="['${sub.id}']" class="flex-1 px-3 py-1.5 bg-dc-success/10 border border-dc-success/20 text-dc-success text-[10px] font-bold uppercase tracking-widest rounded hover:bg-dc-success/20 transition-colors">
                        <i data-lucide="check" class="w-3 h-3 inline-block mr-1"></i> Approve
                    </button>
                    <button data-click="TOC.participantsAdv.denyEmergencySub" data-click-args="['${sub.id}']" class="flex-1 px-3 py-1.5 bg-dc-danger/10 border border-dc-danger/20 text-dc-danger text-[10px] font-bold uppercase tracking-widest rounded hover:bg-dc-danger/20 transition-colors">
                        <i data-lucide="x" class="w-3 h-3 inline-block mr-1"></i> Deny
                    </button>
                </div>` : `
                <div class="pt-2 border-t border-dc-border/50 text-[10px] text-dc-text">
                    Reviewed by <span class="text-white font-bold">${esc(sub.reviewed_by || '—')}</span>
                    ${sub.review_notes ? ` — "${esc(sub.review_notes)}"` : ''}
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
            TOC.toast('Done: emergency substitution approved.', 'success');
            await refreshEmergencySubs();
        } catch (e) {
            TOC.toast(errorMessage(e, 'Could not approve the emergency substitution request.'), 'error');
        }
    }

    async function denyEmergencySub(subId) {
        try {
            const result = await TOC.fetch(`${API}/emergency-subs/${subId}/deny/`, {
                method: 'POST', body: JSON.stringify({ notes: '' }),
            });
            TOC.toast('Done: emergency substitution denied.', 'success');
            await refreshEmergencySubs();
        } catch (e) {
            TOC.toast(errorMessage(e, 'Could not deny the emergency substitution request.'), 'error');
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
                        <button data-click="TOC.participantsAdv.openAssignDrawer" data-click-args="['${fa.id}', '${fa.username}']" class="px-2 py-1 bg-theme-surface border border-theme-border text-theme text-[9px] font-bold rounded hover:bg-theme hover:text-dc-bg transition-all">
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
                <button data-click="TOC.participantsAdv.confirmAssign" data-click-args="['${faId}']" class="w-full py-2.5 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:brightness-110 transition-all shadow-[0_0_15px_var(--color-primary-muted)]">
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
            TOC.toast('Done: free agent assigned to the selected team.', 'success');
            TOC.drawer.close();
            await refreshFreeAgents();
        } catch (e) {
            TOC.toast(errorMessage(e, 'Could not assign this free agent.'), 'error');
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
                        <p class="text-xs font-bold text-white">${esc(w.participant_name)}</p>
                        <p class="text-[9px] text-dc-text font-mono">${esc(w.registration_number || '')} · ${timeAgo(w.registered_at)}</p>
                    </div>
                </div>
                <button data-click="TOC.participantsAdv.promoteWaitlist" data-click-args="[${w.id}]" class="px-3 py-1.5 bg-dc-success/10 border border-dc-success/20 text-dc-success text-[10px] font-bold uppercase tracking-widest rounded hover:bg-dc-success/20 transition-colors">
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
            TOC.toast(result.message || 'Done: participant promoted from waitlist.', 'success');
            await refreshWaitlist();
            // Also refresh the main participant grid
            if (TOC.participants && TOC.participants.refresh) {
                TOC.participants.refresh();
            }
        } catch (e) {
            TOC.toast(errorMessage(e, 'Could not promote this waitlisted participant.'), 'error');
        }
    }

    async function autoPromote() {
        try {
            const result = await TOC.fetch(`${API}/participants/auto-promote/`, {
                method: 'POST',
            });
            TOC.toast(
                result.message || (result.promoted ? 'Done: auto-promote completed.' : 'No waitlist promotions were needed.'),
                result.promoted ? 'success' : 'info'
            );
            await refreshWaitlist();
            if (TOC.participants && TOC.participants.refresh) {
                TOC.participants.refresh();
            }
        } catch (e) {
            TOC.toast(errorMessage(e, 'Could not run auto-promote right now.'), 'error');
        }
    }

    async function refreshDisqualified() {
        try {
            const params = new URLSearchParams();
            if (state.disqualifiedFilter) params.set('status', state.disqualifiedFilter);
            const qs = params.toString();
            const resp = await TOC.fetch(`${API}/disqualified/${qs ? ('?' + qs) : ''}`);
            state.disqualified = resp.results || [];
            renderDisqualified();
        } catch (e) {
            console.error('[TOC:PartAdv] Failed to load disqualified list:', e);
        }
    }

    function renderDisqualifiedChips() {
        const wrap = document.getElementById('disqualified-filter-chips');
        if (!wrap) return;
        const chips = wrap.querySelectorAll('[data-disq-filter]');
        chips.forEach((chip) => {
            const val = chip.getAttribute('data-disq-filter') || '';
            const active = val === state.disqualifiedFilter;
            chip.classList.toggle('border-theme/30', active);
            chip.classList.toggle('bg-theme/10', active);
            chip.classList.toggle('text-theme', active);
            chip.classList.toggle('border-dc-border', !active);
            chip.classList.toggle('text-dc-text', !active);
        });
    }

    function renderDisqualified() {
        const list = document.getElementById('disqualified-list');
        const badge = document.getElementById('disqualified-count');
        if (!list) return;

        renderDisqualifiedChips();

        if (badge) {
            badge.textContent = String(state.disqualified.length);
            badge.classList.toggle('hidden', state.disqualified.length === 0);
        }

        if (state.disqualified.length === 0) {
            list.innerHTML = `
                <div id="disqualified-filter-chips" class="flex items-center flex-wrap gap-2 mb-3">
                    <button data-disq-filter="" class="disq-chip px-2 py-1 rounded border text-[10px] font-bold uppercase tracking-widest">All</button>
                    <button data-disq-filter="rejected" class="disq-chip px-2 py-1 rounded border text-[10px] font-bold uppercase tracking-widest">Rejected</button>
                    <button data-disq-filter="cancelled" class="disq-chip px-2 py-1 rounded border text-[10px] font-bold uppercase tracking-widest">Cancelled</button>
                    <button data-disq-filter="no_show" class="disq-chip px-2 py-1 rounded border text-[10px] font-bold uppercase tracking-widest">No-Show</button>
                </div>
                <div class="text-center py-8 text-dc-text text-xs">
                    <i data-lucide="shield-check" class="w-8 h-8 mx-auto mb-2 opacity-30"></i>
                    <p>No disqualified records</p>
                </div>`;
            bindDisqualifiedFilters();
            renderDisqualifiedChips();
            lucide.createIcons({ nodes: [list] });
            return;
        }

        list.innerHTML = `<div id="disqualified-filter-chips" class="flex items-center flex-wrap gap-2 mb-3">
                <button data-disq-filter="" class="disq-chip px-2 py-1 rounded border text-[10px] font-bold uppercase tracking-widest">All</button>
                <button data-disq-filter="rejected" class="disq-chip px-2 py-1 rounded border text-[10px] font-bold uppercase tracking-widest">Rejected</button>
                <button data-disq-filter="cancelled" class="disq-chip px-2 py-1 rounded border text-[10px] font-bold uppercase tracking-widest">Cancelled</button>
                <button data-disq-filter="no_show" class="disq-chip px-2 py-1 rounded border text-[10px] font-bold uppercase tracking-widest">No-Show</button>
            </div>` + state.disqualified.map((row) => {
            const statusTone = row.status === 'cancelled'
                ? 'bg-zinc-500/10 border-zinc-500/30 text-zinc-300'
                : 'bg-dc-danger/10 border-dc-danger/30 text-dc-danger';
            const reason = row.disqualification_reason || 'No reason provided';
            return `
                <div class="rounded-lg border border-dc-border bg-dc-bg px-4 py-3 hover:border-dc-borderLight transition-colors">
                    <div class="flex items-start justify-between gap-3">
                        <div class="min-w-0">
                            <div class="flex items-center gap-2 flex-wrap">
                                <p class="text-xs font-bold text-white truncate">${row.participant_name || 'Unknown'}</p>
                                <span class="text-[9px] px-2 py-0.5 rounded border font-bold uppercase tracking-wider ${statusTone}">${row.status_display || row.status || 'Inactive'}</span>
                                ${row.slot_number ? `<span class="text-[9px] px-1.5 py-0.5 rounded border border-dc-warning/30 bg-dc-warning/10 text-dc-warning font-mono">Slot ${row.slot_number}</span>` : ''}
                            </div>
                            <p class="text-[10px] text-dc-text font-mono mt-1">${row.registration_number || ''}</p>
                            <p class="text-[11px] text-dc-text mt-2">${reason}</p>
                        </div>
                        <div class="shrink-0 flex items-center gap-2">
                            <button data-click="TOC.participantsAdv.openMoveToWaitlistPrompt" data-click-args="[${row.id}]" data-cap-require="manage_registrations" class="px-2.5 py-1.5 bg-dc-warning/10 border border-dc-warning/20 text-dc-warning text-[10px] font-bold uppercase tracking-widest rounded hover:bg-dc-warning/20 transition-colors">
                                Move to Waitlist
                            </button>
                        </div>
                    </div>
                </div>`;
        }).join('');

        bindDisqualifiedFilters();
        renderDisqualifiedChips();
        lucide.createIcons({ nodes: [list] });
    }

    function bindDisqualifiedFilters() {
        const wrap = document.getElementById('disqualified-filter-chips');
        if (!wrap || wrap.dataset.bound === '1') return;
        wrap.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-disq-filter]');
            if (!btn) return;
            state.disqualifiedFilter = btn.getAttribute('data-disq-filter') || '';
            refreshDisqualified();
        });
        wrap.dataset.bound = '1';
    }

    function openMoveToWaitlistPrompt(regId) {
        TOC.drawer.open(
            'Move to Waitlist',
            `<div class="space-y-4">
                <div class="bg-dc-warning/10 border border-dc-warning/30 rounded-lg p-3 text-xs text-dc-warning">
                    This action moves the participant from inactive/disqualified state to waitlist for reconsideration.
                </div>
                <div class="bg-dc-panel border border-dc-borderLight rounded-lg p-3">
                    <label class="text-[10px] font-bold text-dc-text uppercase tracking-widest block mb-2">Reason (required)</label>
                    <textarea id="move-waitlist-reason" rows="4" class="w-full bg-dc-bg border border-dc-border rounded px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none" placeholder="Write why this participant is being reconsidered..."></textarea>
                </div>
                <button data-click="TOC.participantsAdv.confirmMoveToWaitlist" data-click-args="[${regId}]" class="w-full py-2.5 bg-dc-warning text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:brightness-110 transition-all">
                    Confirm Move
                </button>
            </div>`
        );
        setTimeout(() => { if (typeof lucide !== 'undefined') lucide.createIcons(); }, 30);
    }

    async function confirmMoveToWaitlist(regId) {
        const reason = (document.getElementById('move-waitlist-reason')?.value || '').trim();
        if (!reason) {
            TOC.toast('Reason is required before moving to waitlist.', 'error');
            return;
        }
        await moveToWaitlist(regId, reason);
        TOC.drawer.close();
    }

    async function moveToWaitlist(regId, reason) {
        try {
            const result = await TOC.fetch(`${API}/participants/${regId}/move-to-waitlist/`, {
                method: 'POST',
                body: JSON.stringify({ reason: reason || 'Reconsidered by organizer from disqualified list' }),
            });
            TOC.toast(result.message || 'Moved to waitlist.', 'success');
            await refreshDisqualified();
            await refreshWaitlist();
            if (TOC.participants && TOC.participants.refresh) {
                TOC.participants.refresh();
            }
        } catch (e) {
            TOC.toast(errorMessage(e, 'Could not move this participant to waitlist.'), 'error');
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
            TOC.toast(result.message || 'Done: guest entry converted successfully.', 'success');
            if (TOC.participants && TOC.participants.refresh) {
                TOC.participants.refresh();
            }
        } catch (e) {
            TOC.toast(errorMessage(e, 'Could not convert this guest team.'), 'error');
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
                <button data-click="TOC.participantsAdv.confirmFeeWaiver" data-click-args="[${regId}]" class="w-full py-2.5 bg-dc-warning text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:brightness-110 transition-all">
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
            TOC.toast(result.message || 'Done: fee waiver applied.', 'success');
            TOC.drawer.close();
            if (TOC.participants && TOC.participants.refresh) {
                TOC.participants.refresh();
            }
        } catch (e) {
            TOC.toast(errorMessage(e, 'Could not apply the fee waiver.'), 'error');
        }
    }

    /* ════════════════════════════════════════════════════════════════ */
    /* Init — load data when participants tab activates               */
    /* ════════════════════════════════════════════════════════════════ */

    let _initialized = false;

    function init() {
        if (_initialized) return;
        _initialized = true;
        refreshEmergencySubs();
        refreshFreeAgents();
        refreshWaitlist();
        refreshDisqualified();
    }

    // Listen for tab activation
    document.addEventListener('toc:tab-changed', function (e) {
        if (e.detail && e.detail.tab === 'participants') {
            setTimeout(init, 100);
        }
    });

    // Auto-init if participants tab is already active
    document.addEventListener('DOMContentLoaded', () => {
        const currentTab = (window.location.hash || '#overview').replace('#', '');
        if (currentTab === 'participants') {
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
        refreshDisqualified,
        promoteWaitlist,
        autoPromote,
        moveToWaitlist,
        openMoveToWaitlistPrompt,
        confirmMoveToWaitlist,
        convertGuest,
        openFeeWaiverDrawer,
        confirmFeeWaiver,
    };

})();
