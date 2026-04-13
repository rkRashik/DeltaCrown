/**
 * TOC Announcements Module — Sprint 8
 *
 * Announcement feed, compose form, broadcast with recipient
 * targeting, and Quick Comms pre-built templates.
 */
(function () {
    'use strict';

    const API = window.TOC?.api;
    if (!API) return;

    /* ------------------------------------------------------------------ */
    /*  State                                                              */
    /* ------------------------------------------------------------------ */
    let announcements = [];
    let lifecycleEvents = [];
    let stats = { total: 0, pinned: 0, important: 0 };
    let debounceTimer = null;

    /* ------------------------------------------------------------------ */
    /*  Load & Render                                                      */
    /* ------------------------------------------------------------------ */

    async function refresh() {
        const search = document.getElementById('ann-search')?.value || '';
        const pinned = document.getElementById('ann-pinned-filter')?.checked || false;
        try {
            const res = await API.get(`announcements/?search=${encodeURIComponent(search)}&pinned=${pinned}`);
            announcements = res.announcements || [];
            lifecycleEvents = res.lifecycle || [];
            stats = res.stats || stats;
            renderStats();
            renderFeed();
        } catch (e) { console.warn('Announcements load error', e); }
    }

    function debouncedRefresh() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(refresh, 300);
    }

    function renderStats() {
        const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
        el('ann-stat-total', stats.total);
        el('ann-stat-pinned', stats.pinned);
        el('ann-stat-important', stats.important);
    }

    function renderFeed() {
        const container = document.getElementById('announcement-feed');
        if (!container) return;
        if (!announcements.length && !lifecycleEvents.length) {
            container.innerHTML = '<div class="py-12 text-center text-dc-text text-xs">No announcements yet. Compose one!</div>';
            return;
        }

        // Manual announcements
        const manualHtml = announcements.map(a => {
            const visuals = inferAnnouncementVisual(a);
            const pinIcon = a.is_pinned ? '<i data-lucide="pin" class="w-3 h-3 text-dc-warning"></i>' : '';
            const importantBadge = a.is_important ? '<span class="px-1.5 py-0.5 text-[10px] rounded-full bg-red-500/10 text-red-400 font-bold uppercase tracking-wider">Important</span>' : '';
            const typeBadge = '<span class="px-1.5 py-0.5 text-[10px] rounded-full font-bold uppercase tracking-wider ' + visuals.tone + '">' + visuals.label + '</span>';
            const timeAgo = relativeTime(a.created_at);
            return `
                <div class="glass-box rounded-xl overflow-hidden ${a.is_important ? 'ring-1 ring-red-500/20' : ''}">
                    <div class="flex items-start gap-3.5 p-4">
                        <div class="w-9 h-9 rounded-lg ${visuals.tone.split(' ')[0]} flex items-center justify-center flex-shrink-0 mt-0.5">
                            <i data-lucide="${visuals.icon}" class="w-4 h-4 ${visuals.tone.split(' ')[1]}"></i>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center gap-2 flex-wrap">
                                ${pinIcon}
                                <h4 class="font-bold text-white text-sm leading-tight">${a.title}</h4>
                                ${typeBadge}
                                ${importantBadge}
                            </div>
                            <p class="text-[13px] text-dc-text/70 leading-relaxed mt-1.5">${a.message}</p>
                            <div class="flex items-center gap-2 text-[10px] text-dc-text/40 mt-2.5">
                                <span class="font-medium">${a.author}</span>
                                <span class="text-dc-text/20">·</span>
                                <span>${timeAgo}</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button data-click="TOC.announcements.togglePin" data-click-args="[${a.id}, ${!a.is_pinned}]" title="${a.is_pinned ? 'Unpin' : 'Pin'}" data-cap-require="make_announcements" class="p-1 rounded text-dc-text/40 hover:text-dc-warning hover:bg-dc-warning/10 transition">
                                <i data-lucide="${a.is_pinned ? 'pin-off' : 'pin'}" class="w-3.5 h-3.5"></i>
                            </button>
                            <button data-click="TOC.announcements.editAnnouncement" data-click-args="[${a.id}]" data-cap-require="make_announcements" class="p-1 rounded text-dc-text/40 hover:text-dc-textBright hover:bg-white/5 transition">
                                <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
                            </button>
                            <button data-click="TOC.announcements.deleteAnnouncement" data-click-args="[${a.id}]" data-cap-require="make_announcements" class="p-1 rounded text-dc-text/40 hover:text-dc-danger hover:bg-dc-danger/10 transition">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Lifecycle events (system-derived, read-only) — smart cards with scope badges
        const lifecycleHtml = lifecycleEvents.length ? `
            <div class="mt-6 space-y-2">
                <div class="flex items-center gap-2 mb-3">
                    <div class="w-5 h-5 rounded bg-cyan-500/10 flex items-center justify-center">
                        <i data-lucide="sparkles" class="w-3 h-3 text-cyan-400/60"></i>
                    </div>
                    <span class="text-[10px] font-bold text-dc-text/50 uppercase tracking-[0.15em]">Tournament Intelligence</span>
                    <span class="text-[9px] text-dc-text/25 ml-auto">${lifecycleEvents.length} events</span>
                </div>
                ${lifecycleEvents.map(evt => {
                    const palette = {
                        emerald: { text: 'text-emerald-400', bg: 'bg-emerald-500/8', ring: 'ring-emerald-500/15', dot: 'bg-emerald-400' },
                        amber:   { text: 'text-amber-400',   bg: 'bg-amber-500/8',   ring: 'ring-amber-500/15',   dot: 'bg-amber-400' },
                        red:     { text: 'text-red-400',     bg: 'bg-red-500/8',     ring: 'ring-red-500/15',     dot: 'bg-red-400' },
                        cyan:    { text: 'text-cyan-400',    bg: 'bg-cyan-500/8',    ring: 'ring-cyan-500/15',    dot: 'bg-cyan-400' },
                    };
                    const c = palette[evt.color] || palette.cyan;
                    const timeAgo = evt.created_at ? relativeTime(evt.created_at) : '';
                    const urgentPulse = evt.is_important ? '<span class="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse flex-shrink-0"></span>' : '';
                    const scopeBadge = evt.scope === 'personal'
                        ? '<span class="text-[8px] font-bold text-amber-400/60 bg-amber-500/8 px-1 py-0.5 rounded uppercase tracking-wider">Personal</span>'
                        : '<span class="text-[8px] font-bold text-cyan-400/40 bg-cyan-500/5 px-1 py-0.5 rounded uppercase tracking-wider">Global</span>';
                    return `
                        <div class="group flex items-start gap-3 px-3.5 py-3 rounded-lg ${c.bg} ring-1 ${c.ring} hover:ring-white/10 transition-all duration-200">
                            <div class="w-7 h-7 rounded-lg ${c.bg} ring-1 ${c.ring} flex items-center justify-center flex-shrink-0 mt-0.5">
                                <i data-lucide="${evt.icon || 'info'}" class="w-3.5 h-3.5 ${c.text}"></i>
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2">
                                    ${urgentPulse}
                                    <span class="text-xs font-bold text-white/90">${evt.title}</span>
                                    ${scopeBadge}
                                </div>
                                <p class="text-[11px] text-dc-text/45 mt-0.5 line-clamp-1">${evt.message}</p>
                            </div>
                            ${timeAgo ? `<span class="text-[9px] text-dc-text/30 tabular-nums flex-shrink-0 mt-1">${timeAgo}</span>` : ''}
                        </div>
                    `;
                }).join('')}
            </div>
        ` : '';

        container.innerHTML = manualHtml + lifecycleHtml;
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    /* ------------------------------------------------------------------ */
    /*  Compose                                                            */
    /* ------------------------------------------------------------------ */

    function openCompose() {
        const html = `
            <div class="space-y-4">
                <h3 class="font-display font-bold text-white text-lg">Compose Announcement</h3>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Title *</label>
                    <input id="compose-title" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Message</label>
                    <textarea id="compose-message" rows="5" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></textarea>
                </div>
                <div class="flex items-center gap-4">
                    <label class="flex items-center gap-2 text-sm text-dc-text cursor-pointer">
                        <input id="compose-pinned" type="checkbox" class="rounded border-dc-border bg-dc-surface text-theme"> Pin
                    </label>
                    <label class="flex items-center gap-2 text-sm text-dc-text cursor-pointer">
                        <input id="compose-important" type="checkbox" class="rounded border-dc-border bg-dc-surface text-theme"> Important
                    </label>
                </div>
                <button data-click="TOC.announcements.confirmCompose" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Publish</button>
            </div>
        `;
        showOverlay(html);
    }

    async function confirmCompose() {
        const title = document.getElementById('compose-title')?.value?.trim();
        if (!title) return;
        try {
            await API.post('announcements/', {
                title,
                message: document.getElementById('compose-message')?.value || '',
                is_pinned: document.getElementById('compose-pinned')?.checked || false,
                is_important: document.getElementById('compose-important')?.checked || false,
            });
            closeOverlay();
            refresh();
            window.TOC?.toast?.('Announcement published', 'success');
        } catch (e) { window.TOC?.toast?.('Publish failed', 'error'); }
    }

    /* ------------------------------------------------------------------ */
    /*  Edit / Delete / Pin                                                */
    /* ------------------------------------------------------------------ */

    function editAnnouncement(id) {
        const a = announcements.find(x => x.id === id);
        if (!a) return;
        const html = `
            <div class="space-y-4">
                <h3 class="font-display font-bold text-white text-lg">Edit Announcement</h3>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Title</label>
                    <input id="edit-ann-title" type="text" value="${a.title}" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Message</label>
                    <textarea id="edit-ann-message" rows="5" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">${a.message}</textarea>
                </div>
                <button data-click="TOC.announcements.confirmEdit" data-click-args="[${id}]" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Save</button>
            </div>
        `;
        showOverlay(html);
    }

    async function confirmEdit(id) {
        try {
            await API.put(`announcements/${id}/`, {
                title: document.getElementById('edit-ann-title')?.value?.trim() || '',
                message: document.getElementById('edit-ann-message')?.value || '',
            });
            closeOverlay();
            refresh();
        } catch (e) { window.TOC?.toast?.('Update failed', 'error'); }
    }

    async function deleteAnnouncement(id) {
        if (!confirm('Delete this announcement?')) return;
        try {
            await API.delete(`announcements/${id}/`);
            refresh();
        } catch (e) { window.TOC?.toast?.('Delete failed', 'error'); }
    }

    async function togglePin(id, pinned) {
        try {
            await API.put(`announcements/${id}/`, { is_pinned: pinned });
            refresh();
        } catch (e) { window.TOC?.toast?.('Pin toggle failed', 'error'); }
    }

    /* ------------------------------------------------------------------ */
    /*  Broadcast                                                          */
    /* ------------------------------------------------------------------ */

    function broadcast(target) {
        const html = `
            <div class="space-y-4">
                <h3 class="font-display font-bold text-white text-lg">Broadcast to: <span class="text-theme">${target}</span></h3>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Title *</label>
                    <input id="broadcast-title" type="text" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
                </div>
                <div>
                    <label class="block text-xs text-dc-text mb-1">Message</label>
                    <textarea id="broadcast-message" rows="4" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></textarea>
                </div>
                <label class="flex items-center gap-2 text-sm text-dc-text cursor-pointer">
                    <input id="broadcast-important" type="checkbox" class="rounded border-dc-border bg-dc-surface text-theme"> Mark as important
                </label>
                <button data-click="TOC.announcements.confirmBroadcast" data-click-args="['${target}']" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Send Broadcast</button>
            </div>
        `;
        showOverlay(html);
    }

    async function confirmBroadcast(target) {
        const title = document.getElementById('broadcast-title')?.value?.trim();
        if (!title) return;
        try {
            const res = await API.post('announcements/broadcast/', {
                title,
                message: document.getElementById('broadcast-message')?.value || '',
                is_important: document.getElementById('broadcast-important')?.checked || false,
                targets: target,
            });
            closeOverlay();
            refresh();
            window.TOC?.toast?.(`Broadcast sent to ${res.notified || 0} recipients`, 'success');
        } catch (e) { window.TOC?.toast?.('Broadcast failed', 'error'); }
    }

    /* ------------------------------------------------------------------ */
    /*  Quick Comms                                                        */
    /* ------------------------------------------------------------------ */

    function openQuickComms() {
        const templates = [
            { key: 'match_starting', label: 'Matches Starting Soon', icon: 'play-circle', symbol: '⚔️', mode: 'quick' },
            { key: 'check_in_reminder', label: 'Check-In Reminder', icon: 'bell', symbol: '✅', mode: 'quick' },
            { key: 'schedule_update', label: 'Schedule Updated', icon: 'calendar', symbol: '🗓️', mode: 'quick' },
            { key: 'bracket_published', label: 'Bracket Published', icon: 'git-branch', symbol: '🧩', mode: 'quick' },
            { key: 'results_finalized', label: 'Results Finalized', icon: 'trophy', symbol: '🏆', mode: 'quick' },
            { key: 'live_group_draw', label: 'Live Group Draw Notice', icon: 'radio', symbol: '📡', mode: 'form' },
            { key: 'stream_live', label: 'Stream Is Live', icon: 'tv', symbol: '🎥', mode: 'form' },
            { key: 'round_ready', label: 'Round Ready Callout', icon: 'swords', symbol: '🔥', mode: 'form' },
        ];
        const html = `
            <div class="space-y-4">
                <h3 class="font-display font-bold text-white text-lg flex items-center gap-2">
                    <i data-lucide="zap" class="w-5 h-5 text-dc-warning"></i> Quick Comms
                </h3>
                <p class="text-xs text-dc-text">One-click + smart parameter templates for faster organizer communication.</p>
                <div class="space-y-2">
                    ${templates.map(t => `
                        <button data-click="TOC.announcements.openSmartCard" data-click-args="['${t.key}']" class="w-full p-3 rounded-lg border border-dc-border hover:border-theme/40 transition-colors text-left flex items-center gap-3">
                            <span class="text-base leading-none">${t.symbol || '📣'}</span>
                            <i data-lucide="${t.icon}" class="w-5 h-5 text-theme shrink-0"></i>
                            <span class="text-sm font-bold text-white">${t.label}</span>
                            <span class="ml-auto text-[10px] uppercase tracking-wider ${t.mode === 'quick' ? 'text-dc-success' : 'text-dc-warning'}">${t.mode === 'quick' ? 'One Tap' : 'Smart Card'}</span>
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
        showOverlay(html);
    }

    async function sendQuickComm(templateKey) {
        try {
            const res = await API.post('announcements/quick-comms/', { template: templateKey });
            closeOverlay();
            refresh();
            window.TOC?.toast?.(`Quick Comm sent to ${res.notified || 0} recipients`, 'success');
        } catch (e) { window.TOC?.toast?.('Quick Comm failed', 'error'); }
    }

    function openSmartCard(templateKey) {
        const forms = {
            live_group_draw: {
                title: '📡 Live Group Draw will happen at {time}',
                message: '🎯 Live group draw starts at {time}. Join now: {link}',
                fields: [
                    { id: 'time', label: 'Draw Time', placeholder: '8:30 PM (GMT+6)' },
                    { id: 'link', label: 'Live Draw Link', placeholder: 'https://...' },
                ],
            },
            stream_live: {
                title: '🎥 Stream is now LIVE',
                message: '📺 We are live now. Watch here: {link}',
                fields: [
                    { id: 'link', label: 'Stream Link', placeholder: 'https://...' },
                ],
            },
            round_ready: {
                title: '🔥 Round {round} is ready',
                message: '⚔️ Round {round} matches are ready. Check match lobby and report on time.',
                fields: [
                    { id: 'round', label: 'Round Number/Name', placeholder: 'R2 / Quarter Final' },
                ],
            },
        };

        const cfg = forms[templateKey];
        if (!cfg) {
            sendQuickComm(templateKey);
            return;
        }

        const fieldsHtml = cfg.fields.map(f =>
            '<div><label class="block text-xs text-dc-text mb-1">' + f.label + '</label>' +
            '<input id="smart-' + f.id + '" type="text" placeholder="' + f.placeholder + '" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50"></div>'
        ).join('');

        showOverlay(
            '<div class="space-y-4">' +
                '<h3 class="font-display font-bold text-white text-lg">Smart Announcement Card</h3>' +
                '<p class="text-xs text-dc-text">Auto-generate a polished announcement with your input.</p>' +
                fieldsHtml +
                '<button data-click="TOC.announcements.sendSmartCard" data-click-args="[&quot;' + templateKey + '&quot;]" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Publish Smart Card</button>' +
            '</div>'
        );
    }

    async function sendSmartCard(templateKey) {
        const forms = {
            live_group_draw: {
                title: '📡 Live Group Draw will happen at {time}',
                message: '🎯 Live group draw starts at {time}. Join now: {link}',
                required: ['time', 'link'],
            },
            stream_live: {
                title: '🎥 Stream is now LIVE',
                message: '📺 We are live now. Watch here: {link}',
                required: ['link'],
            },
            round_ready: {
                title: '🔥 Round {round} is ready',
                message: '⚔️ Round {round} matches are ready. Check match lobby and report on time.',
                required: ['round'],
            },
        };
        const cfg = forms[templateKey];
        if (!cfg) return;

        const values = {};
        for (const key of cfg.required) {
            values[key] = (document.getElementById('smart-' + key)?.value || '').trim();
            if (!values[key]) {
                window.TOC?.toast?.('Please fill all required fields.', 'error');
                return;
            }
        }

        let title = cfg.title;
        let message = cfg.message;
        Object.keys(values).forEach((key) => {
            title = title.replaceAll('{' + key + '}', values[key]);
            message = message.replaceAll('{' + key + '}', values[key]);
        });

        try {
            await API.post('announcements/broadcast/', {
                title,
                message,
                is_important: true,
                targets: 'all',
            });
            closeOverlay();
            refresh();
            window.TOC?.toast?.('Smart announcement published.', 'success');
        } catch (e) {
            window.TOC?.toast?.('Smart card publish failed', 'error');
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Helpers                                                            */
    /* ------------------------------------------------------------------ */

    function relativeTime(iso) {
        if (!iso) return '';
        const diff = (Date.now() - new Date(iso).getTime()) / 1000;
        if (diff < 60) return 'just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return `${Math.floor(diff / 86400)}d ago`;
    }

    function inferAnnouncementVisual(item) {
        const text = String((item?.title || '') + ' ' + (item?.message || '')).toLowerCase();
        if (item?.is_important || text.includes('urgent') || text.includes('critical')) {
            return { symbol: '🚨', icon: 'siren', label: 'Urgent', tone: 'bg-dc-danger/10 text-dc-danger' };
        }
        if (text.includes('draw') || text.includes('schedule') || text.includes('time')) {
            return { symbol: '🗓️', icon: 'calendar-clock', label: 'Schedule', tone: 'bg-dc-warning/10 text-dc-warning' };
        }
        if (text.includes('stream') || text.includes('live')) {
            return { symbol: '📡', icon: 'radio', label: 'Live', tone: 'bg-dc-info/10 text-dc-info' };
        }
        if (text.includes('result') || text.includes('winner') || text.includes('qualified')) {
            return { symbol: '🏆', icon: 'trophy', label: 'Result', tone: 'bg-dc-success/10 text-dc-success' };
        }
        return { symbol: '📣', icon: 'megaphone', label: 'Update', tone: 'bg-theme/10 text-theme' };
    }

    function showOverlay(html) {
        let overlay = document.getElementById('announcements-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'announcements-overlay';
            overlay.className = 'fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm';
            overlay.addEventListener('click', e => { if (e.target === overlay) closeOverlay(); });
            document.body.appendChild(overlay);
        }
        overlay.innerHTML = `<div class="glass-box rounded-2xl p-6 w-full max-w-md mx-4 max-h-[80vh] overflow-y-auto">${html}</div>`;
        overlay.classList.remove('hidden');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function closeOverlay() {
        const overlay = document.getElementById('announcements-overlay');
        if (overlay) overlay.classList.add('hidden');
    }

    /* ================================================================== */
    /*  AUTOMATION CONTROL CENTER v2 — Full Rebuild + Polish              */
    /*  Premium command-center panel: group navigation, rich cards,       */
    /*  summary stats, mobile-responsive, animated, accessible.           */
    /* ================================================================== */

    /* ── Constants ─────────────────────────────────────────────────── */

    /* Wiring classification for honest UI treatment */
    const WIRING = {
        fully_wired:       { label: 'Both',           badge: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/25', icon: 'radio-tower', desc: 'Push notification + feed display' },
        notification_only: { label: 'Notification',   badge: 'bg-blue-500/15 text-blue-300 ring-blue-500/25',       icon: 'bell',        desc: 'Push notification only' },
        feed_only:         { label: 'Feed Only',      badge: 'bg-amber-500/15 text-amber-300 ring-amber-500/25',    icon: 'rss',         desc: 'Announcement feed only' },
        coming_soon:       { label: 'Coming Soon',    badge: 'bg-zinc-700/40 text-zinc-500 ring-zinc-700/30',       icon: 'lock',        desc: 'Not yet implemented' },
    };

    const CHANNEL = {
        both:         { label: 'Notification + Feed', icon: 'radio-tower', color: 'text-emerald-400' },
        notification: { label: 'Notification',        icon: 'bell',        color: 'text-blue-400' },
        feed:         { label: 'Feed',                icon: 'rss',         color: 'text-amber-400' },
        none:         { label: 'None',                icon: 'circle-off',  color: 'text-zinc-600' },
    };

    const AUD = {
        public:         { label: 'Public',                desc: 'Visible to anyone browsing the tournament page',           color: 'bg-blue-500/15 text-blue-300 ring-blue-500/20',    icon: 'globe' },
        all:            { label: 'All Participants',      desc: 'Sent to every registered participant',                     color: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/20', icon: 'users' },
        personal:       { label: 'Affected Participant',  desc: 'Only the specific player affected by this event',          color: 'bg-amber-500/15 text-amber-300 ring-amber-500/20', icon: 'user' },
        not_checked_in: { label: 'Not Checked-in',        desc: 'Players who have not yet checked in for their match',      color: 'bg-rose-500/15 text-rose-300 ring-rose-500/20',    icon: 'user-x' },
        checked_in:     { label: 'Checked-in Only',       desc: 'Players who have already checked in',                      color: 'bg-teal-500/15 text-teal-300 ring-teal-500/20',    icon: 'user-check' },
        staff:          { label: 'Staff Only',            desc: 'Tournament staff and organizers only',                     color: 'bg-purple-500/15 text-purple-300 ring-purple-500/20', icon: 'shield' },
    };

    const TRIGGER_HUMANIZE = {
        'Status → registration_open':            'When registration opens',
        'Status → registration_closed':          'When registration closes',
        'Status → completed':                    'When the tournament is completed',
        '24 h before registration deadline':     '24 hours before registration deadline',
        'Check-in window opens':                 'When the check-in window opens',
        '15 min before check-in closes':         '15 minutes before check-in closes',
        'Groups drawn & published':              'When groups are drawn and published',
        'Group matches created':                 'When group stage matches are generated',
        'All group matches concluded':           'When all group matches are finished',
        'Participant qualifies from group':       'When a participant qualifies for knockout',
        'Bracket seeded & published':            'When the knockout bracket is published',
        'First knockout match begins':           'When the first knockout match starts',
        'Winner of bracket match':               'When a participant wins a bracket match',
        'Participant knocked out':               'When a participant is eliminated',
        'Next-round matchup determined':         'When a new opponent is assigned',
        '~30 min before lobby opens':            '~30 minutes before lobby opens',
        'Match lobby check-in window starts':    'When the match lobby check-in opens',
        'Check-in window closes without entry':  'When a participant misses the check-in window',
        'Match transitions to live state':       'When a match goes live',
        'Organizer starts broadcast':            'When the stream goes live',
    };

    /* Per-category helper text explaining the operational purpose */
    const EVENT_PURPOSE = {
        registration_open:      'Drives sign-ups by announcing the tournament is accepting entries.',
        registration_closing:   'Creates urgency for undecided players to register before the deadline.',
        registrations_closed:   'Confirms registration is locked so participants know the field is set.',
        checkin_open:           'Prompts participants to confirm attendance before the window expires.',
        checkin_closing:        'Final warning for no-shows — gives them one last chance to check in.',
        group_draw_completed:   'Lets players see their group assignment and prepare for opponents.',
        matches_generated:      'Tells players their matches are scheduled and ready to play.',
        group_stage_completed:  'Closes the group phase and signals the transition to knockout.',
        qualified_to_knockout:  'Personal congrats and next-step guidance for advancing players.',
        bracket_published:      'Reveals the knockout draw so fans and players can see matchups.',
        knockout_live:          'Signals that elimination matches have officially started.',
        advanced_to_next_round: 'Celebrates the win and tells the player who they face next.',
        eliminated:             'Respectful notification that the player\'s run has ended.',
        opponent_assigned:      'Tells a player exactly who they play next — critical for preparation.',
        lobby_opens_soon:       'Early heads-up so the player can be ready when the lobby opens.',
        lobby_is_open:          'Immediate call-to-action: check in or risk missing the match.',
        lobby_expired:          'Warns the player they missed check-in — may trigger forfeit rules.',
        match_live:             'Confirms the match is underway — good luck message.',
        stream_live:            'Drives viewership by announcing the live broadcast to the public.',
        tournament_completed:   'Final wrap-up: results, prizes, and thank-yous to all participants.',
    };

    /* Group-level context descriptions */
    const GROUP_DESC = {
        registration: 'Notifications for the sign-up period — from open to close.',
        checkin:      'Reminders and alerts during the tournament check-in window.',
        group:        'Events during group stage play, from draw through completion.',
        knockout:     'Bracket progression events — seeding, wins, and eliminations.',
        match:        'Per-match alerts: lobby reminders, opponent alerts, and live status.',
        completion:   'End-of-tournament wrap-up and broadcast notifications.',
    };

    /* CSS keyframe injection for panel animation (once) */
    let _autoStyleInjected = false;
    function _injectAutoStyles() {
        if (_autoStyleInjected) return;
        _autoStyleInjected = true;
        const style = document.createElement('style');
        style.textContent = `
            @keyframes autoFadeIn { from { opacity: 0; } to { opacity: 1; } }
            @keyframes autoSlideUp { from { opacity: 0; transform: translateY(24px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
            @keyframes autoFadeOut { from { opacity: 1; } to { opacity: 0; } }
            @keyframes autoSlideDown { from { opacity: 1; transform: translateY(0) scale(1); } to { opacity: 0; transform: translateY(16px) scale(0.98); } }
            .auto-backdrop-enter { animation: autoFadeIn 0.25s ease-out both; }
            .auto-panel-enter { animation: autoSlideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1) both; animation-delay: 0.05s; }
            .auto-backdrop-exit { animation: autoFadeOut 0.2s ease-in both; }
            .auto-panel-exit { animation: autoSlideDown 0.2s ease-in both; }
            .auto-card-body-anim { overflow: hidden; transition: max-height 0.25s ease-out, opacity 0.2s ease-out; }
            .auto-card-body-collapsed { max-height: 0 !important; opacity: 0; }
            .auto-card-body-expanded { opacity: 1; }
        `;
        document.head.appendChild(style);
    }

    /* ── State ─────────────────────────────────────────────────────── */

    let _autoData = null;       // { categories, groups } from API
    let _autoLocal = [];        // local editable copy of categories
    let _autoOriginal = '';     // JSON snapshot for dirty detection
    let _autoActiveGroup = '';  // currently selected group key

    function _isAutoDirty() {
        return JSON.stringify(_autoLocal.map(c => ({ k: c.key, e: c.enabled, m: c.custom_message })))
            !== _autoOriginal;
    }

    function _autoStats() {
        const total = _autoLocal.length;
        const wired = _autoLocal.filter(c => c.wiring !== 'coming_soon');
        const enabled = wired.filter(c => c.enabled).length;
        const disabled = wired.length - enabled;
        const comingSoon = _autoLocal.filter(c => c.wiring === 'coming_soon').length;
        const customized = _autoLocal.filter(c => c.custom_message).length;
        return { total, wired: wired.length, enabled, disabled, comingSoon, customized };
    }

    /* ── Open / Close with animation ───────────────────────────────── */

    async function openAutomation() {
        _injectAutoStyles();
        try {
            const res = await API.get('announcements/automation/');
            _autoData = { categories: res.categories || [], groups: res.groups || [] };
        } catch (e) {
            window.TOC?.toast?.('Failed to load automation config', 'error');
            return;
        }

        _autoLocal = _autoData.categories.map(c => ({ ...c }));
        _autoOriginal = JSON.stringify(_autoLocal.map(c => ({ k: c.key, e: c.enabled, m: c.custom_message })));
        _autoActiveGroup = _autoData.groups[0]?.key || '';

        _renderAutomationPanel();
    }

    function _closeAutomation() {
        if (_isAutoDirty()) {
            if (!confirm('You have unsaved changes. Discard them?')) return;
        }
        const root = document.getElementById('auto-panel-root');
        if (!root) { return; }

        // Animate out
        const backdrop = root.querySelector('#auto-backdrop');
        const shell = root.querySelector('#auto-panel-shell');
        if (backdrop) { backdrop.classList.remove('auto-backdrop-enter'); backdrop.classList.add('auto-backdrop-exit'); }
        if (shell)    { shell.classList.remove('auto-panel-enter');    shell.classList.add('auto-panel-exit'); }

        document.removeEventListener('keydown', _autoEscHandler);
        setTimeout(() => {
            root.remove();
            document.body.style.overflow = '';
        }, 250);
        _autoData = null;
        _autoLocal = [];
    }

    /* ── Master Render ─────────────────────────────────────────────── */

    function _renderAutomationPanel() {
        document.getElementById('auto-panel-root')?.remove();
        document.getElementById('announcements-overlay')?.classList.add('hidden');

        const root = document.createElement('div');
        root.id = 'auto-panel-root';
        root.className = 'fixed inset-0 z-[200] flex items-stretch';
        root.innerHTML = `
            <!-- Backdrop with fade-in -->
            <div id="auto-backdrop" class="absolute inset-0 bg-black/80 backdrop-blur-md auto-backdrop-enter"></div>

            <!-- Panel shell with slide-up -->
            <div id="auto-panel-shell" class="relative z-10 flex flex-col w-full max-w-[1100px] mx-auto my-2 sm:my-4 md:my-6 rounded-2xl overflow-hidden border border-dc-borderLight/50 auto-panel-enter"
                 style="background: #0c0c14; box-shadow: 0 25px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.04) inset;">

                <!-- HEADER -->
                ${_autoRenderHeader()}

                <!-- MOBILE GROUP SELECTOR (visible below lg) -->
                <div id="auto-mobile-nav" class="lg:hidden border-b border-dc-border/40 overflow-x-auto" style="background: #09090f; scrollbar-width: none;">
                    ${_autoRenderMobileNav()}
                </div>

                <!-- MOBILE STATS BAR (visible below xl) -->
                <div class="xl:hidden flex items-center gap-3 px-4 py-2.5 border-b border-dc-border/30 overflow-x-auto" style="background: #09090f; scrollbar-width: none;">
                    ${(() => {
                        const s = _autoStats();
                        return `
                            <span class="flex items-center gap-1.5 text-[11px] text-zinc-400 whitespace-nowrap"><i data-lucide="check-circle" class="w-3 h-3 text-emerald-500"></i> ${s.enabled}/${s.wired} active</span>
                            <span class="text-zinc-700">·</span>
                            <span class="flex items-center gap-1.5 text-[11px] text-zinc-500 whitespace-nowrap"><i data-lucide="circle-off" class="w-3 h-3 text-zinc-600"></i> ${s.disabled} off</span>
                            <span class="text-zinc-700">·</span>
                            <span class="flex items-center gap-1.5 text-[11px] text-zinc-500 whitespace-nowrap"><i data-lucide="lock" class="w-3 h-3 text-zinc-600"></i> ${s.comingSoon} planned</span>
                            <span class="text-zinc-700">·</span>
                            <span class="flex items-center gap-1.5 text-[11px] text-amber-400 whitespace-nowrap"><i data-lucide="pencil" class="w-3 h-3"></i> ${s.customized} custom</span>
                        `;
                    })()}
                </div>

                <!-- BODY: Nav + Content + Summary -->
                <div class="flex flex-1 min-h-0 overflow-hidden">
                    <!-- LEFT NAV (desktop only) -->
                    <nav id="auto-nav" class="hidden lg:block w-56 flex-shrink-0 border-r border-dc-border/50 overflow-y-auto" style="background: #09090f;">
                        ${_autoRenderNav()}
                    </nav>

                    <!-- CENTER CONTENT -->
                    <main id="auto-content" class="flex-1 overflow-y-auto p-4 sm:p-6" style="scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.08) transparent;">
                        ${_autoRenderContent()}
                    </main>

                    <!-- RIGHT SUMMARY (desktop only) -->
                    <aside id="auto-summary" class="w-60 flex-shrink-0 border-l border-dc-border/50 overflow-y-auto p-5 hidden xl:block" style="background: #09090f;">
                        ${_autoRenderSummary()}
                    </aside>
                </div>

                <!-- FOOTER -->
                ${_autoRenderFooter()}
            </div>
        `;

        document.body.appendChild(root);
        document.body.style.overflow = 'hidden';

        root.querySelector('#auto-backdrop').addEventListener('click', _closeAutomation);
        document.addEventListener('keydown', _autoEscHandler);
        _autoBindNav();
        _autoBindCards();
        _autoBindFooter();
        if (typeof lucide !== 'undefined') lucide.createIcons({ attrs: { 'stroke-width': 1.75 } });
    }

    function _autoEscHandler(e) {
        if (e.key === 'Escape') {
            e.preventDefault();
            _closeAutomation();
        }
    }

    /* ── Header ────────────────────────────────────────────────────── */

    function _autoRenderHeader() {
        const s = _autoStats();
        return `
            <header class="flex items-center gap-3 sm:gap-4 px-4 sm:px-6 py-3 sm:py-4 border-b border-dc-border/60" style="background: linear-gradient(180deg, #101018 0%, #0c0c14 100%);">
                <div class="w-10 h-10 sm:w-11 sm:h-11 rounded-xl flex items-center justify-center flex-shrink-0" style="background: linear-gradient(135deg, var(--color-primary, #3b82f6) 0%, var(--color-primary-dark, #1d4ed8) 100%); box-shadow: 0 4px 20px rgba(59,130,246,0.25);">
                    <i data-lucide="radar" class="w-5 h-5 text-white"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <h2 class="text-[15px] sm:text-[17px] font-bold text-white tracking-tight leading-tight" style="font-family: 'Outfit','Space Grotesk',system-ui,sans-serif;">Automation Control Center</h2>
                    <p class="text-[11px] sm:text-xs text-zinc-400 mt-0.5 hidden sm:block">Configure lifecycle notifications across tournament phases.</p>
                </div>
                <div class="flex items-center gap-2 sm:gap-3 flex-shrink-0">
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-full text-[10px] sm:text-[11px] font-bold uppercase tracking-wider ${s.enabled === s.wired ? 'bg-emerald-500/12 text-emerald-400 ring-1 ring-emerald-500/20' : 'bg-amber-500/12 text-amber-400 ring-1 ring-amber-500/20'}">
                        <span class="w-1.5 h-1.5 rounded-full ${s.enabled === s.wired ? 'bg-emerald-400' : 'bg-amber-400'} animate-pulse"></span>
                        ${s.enabled}/${s.wired} active
                    </span>
                    ${s.comingSoon ? `<span class="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-semibold bg-zinc-800/60 text-zinc-500 ring-1 ring-zinc-700/30"><i data-lucide="lock" class="w-2.5 h-2.5"></i> ${s.comingSoon} planned</span>` : ''}
                    <button id="auto-close-btn" class="w-8 h-8 rounded-lg flex items-center justify-center text-zinc-500 hover:text-white hover:bg-white/8 transition-colors" title="Close (Esc)">
                        <i data-lucide="x" class="w-4.5 h-4.5"></i>
                    </button>
                </div>
            </header>`;
    }

    /* ── Mobile Navigation (horizontal pills) ─────────────────────── */

    function _autoRenderMobileNav() {
        const groups = _autoData.groups || [];
        return `
            <div class="flex items-center gap-1.5 px-3 py-2.5" style="-webkit-overflow-scrolling: touch;">
                ${groups.map(g => {
                    const cats = _autoLocal.filter(c => c.group === g.key);
                    const wired = cats.filter(c => c.wiring !== 'coming_soon');
                    const active = wired.filter(c => c.enabled).length;
                    const isActive = g.key === _autoActiveGroup;
                    return `
                        <button class="auto-nav-btn flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold whitespace-nowrap transition-all duration-150
                            ${isActive
                                ? 'bg-white/10 text-white ring-1 ring-white/15'
                                : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'
                            }"
                            data-group="${g.key}">
                            <i data-lucide="${g.icon}" class="w-3.5 h-3.5"></i>
                            <span>${g.label}</span>
                            <span class="text-[9px] ${isActive ? 'text-zinc-400' : 'text-zinc-600'}">${wired.length ? active + '/' + wired.length : '—'}</span>
                        </button>`;
                }).join('')}
            </div>`;
    }

    /* ── Left Navigation (desktop) ─────────────────────────────────── */

    function _autoRenderNav() {
        const groups = _autoData.groups || [];
        return `
            <div class="py-3 px-2.5 space-y-0.5">
                <div class="px-3 pb-2 mb-1">
                    <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-zinc-600">Phase Groups</span>
                </div>
                ${groups.map(g => {
                    const cats = _autoLocal.filter(c => c.group === g.key);
                    const wired = cats.filter(c => c.wiring !== 'coming_soon');
                    const active = wired.filter(c => c.enabled).length;
                    const isActive = g.key === _autoActiveGroup;
                    return `
                        <button class="auto-nav-btn w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-150
                            ${isActive
                                ? 'bg-white/8 text-white ring-1 ring-white/10'
                                : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/4'
                            }"
                            data-group="${g.key}">
                            <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${isActive ? 'bg-white/10' : 'bg-white/[0.03]'}">
                                <i data-lucide="${g.icon}" class="w-4 h-4 ${isActive ? 'text-white' : 'text-zinc-500'}"></i>
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="text-[13px] font-semibold leading-tight truncate">${g.label}</div>
                                <div class="text-[10px] ${isActive ? 'text-zinc-400' : 'text-zinc-600'} mt-0.5">${wired.length ? active + '/' + wired.length + ' active' : 'All planned'}</div>
                            </div>
                        </button>`;
                }).join('')}
            </div>`;
    }

    /* ── Center Content ────────────────────────────────────────────── */

    function _autoRenderContent() {
        const group = (_autoData.groups || []).find(g => g.key === _autoActiveGroup);
        if (!group) return '<div class="text-zinc-500 text-sm py-12 text-center">Select a category group</div>';

        const cats = _autoLocal.filter(c => c.group === _autoActiveGroup);
        const wired = cats.filter(c => c.wiring !== 'coming_soon');
        const groupDesc = GROUP_DESC[_autoActiveGroup] || '';
        return `
            <div class="mb-5">
                <div class="flex items-center gap-3 mb-1">
                    <div class="w-8 h-8 rounded-lg flex items-center justify-center bg-white/[0.05]">
                        <i data-lucide="${group.icon}" class="w-4.5 h-4.5 text-zinc-300"></i>
                    </div>
                    <div>
                        <h3 class="text-base font-bold text-white">${group.label}</h3>
                        <p class="text-[11px] text-zinc-500 leading-relaxed mt-0.5">${groupDesc}</p>
                    </div>
                    <span class="ml-auto text-[11px] text-zinc-500 tabular-nums">${wired.length ? wired.filter(c => c.enabled).length + ' of ' + wired.length + ' active' : 'All planned'}</span>
                </div>
            </div>
            <div class="space-y-3" id="auto-cards-list">
                ${cats.map(c => _autoRenderCard(c)).join('')}
            </div>`;
    }

    function _autoRenderCard(cat) {
        const audience = AUD[cat.audience] || AUD.all;
        const trigger = TRIGGER_HUMANIZE[cat.trigger] || cat.trigger;
        const purpose = EVENT_PURPOSE[cat.key] || '';
        const hasCustom = !!cat.custom_message;
        const wire = WIRING[cat.wiring] || WIRING.coming_soon;
        const chan = CHANNEL[cat.channel] || CHANNEL.none;
        const isComingSoon = cat.wiring === 'coming_soon';

        // Three clear states with distinct visual weight
        let stateLabel, stateCls, stateIcon;
        if (isComingSoon) {
            stateLabel = 'Planned'; stateCls = 'bg-zinc-800/80 text-zinc-600 ring-zinc-700/30'; stateIcon = 'lock';
        } else if (!cat.enabled) {
            stateLabel = 'Off'; stateCls = 'bg-zinc-800/80 text-zinc-500 ring-zinc-700/50'; stateIcon = 'circle-off';
        } else if (hasCustom) {
            stateLabel = 'Custom'; stateCls = 'bg-amber-500/12 text-amber-400 ring-amber-500/25'; stateIcon = 'pencil';
        } else {
            stateLabel = 'Default'; stateCls = 'bg-emerald-500/12 text-emerald-400 ring-emerald-500/25'; stateIcon = 'check';
        }

        return `
            <div class="auto-card rounded-xl border transition-all duration-200
                ${isComingSoon
                    ? 'border-dc-border/20 opacity-40 pointer-events-auto'
                    : cat.enabled
                        ? 'border-dc-border/60 hover:border-zinc-600/70'
                        : 'border-dc-border/30 opacity-55'
                }"
                style="background: ${isComingSoon ? '#08080d' : cat.enabled ? '#0f0f18' : '#0a0a10'}; border-left: 3px solid ${isComingSoon ? '#1a1a22' : !cat.enabled ? '#27272a' : (hasCustom ? 'rgb(245 158 11 / 0.5)' : 'rgb(16 185 129 / 0.4)')};"
                data-auto-key="${cat.key}">

                <!-- Card Header — who / when / what at a glance -->
                <div class="flex items-start gap-3 px-4 sm:px-5 py-3.5">
                    <!-- Toggle (disabled for coming_soon) -->
                    <label class="relative inline-flex items-center ${isComingSoon ? 'cursor-not-allowed' : 'cursor-pointer'} flex-shrink-0 mt-0.5" title="${isComingSoon ? 'Coming soon — not yet implemented' : cat.enabled ? 'Disable' : 'Enable'}">
                        <input type="checkbox" class="sr-only peer auto-toggle" data-key="${cat.key}" ${cat.enabled && !isComingSoon ? 'checked' : ''} ${isComingSoon ? 'disabled' : ''}>
                        <div class="w-10 h-[22px] rounded-full transition-colors duration-200
                            ${isComingSoon ? 'bg-zinc-900 cursor-not-allowed' : 'bg-zinc-800 peer-checked:bg-emerald-600'}
                            peer-focus-visible:ring-2 peer-focus-visible:ring-emerald-500/40 peer-focus-visible:ring-offset-1 peer-focus-visible:ring-offset-black
                            after:content-[''] after:absolute after:top-[3px] after:left-[3px]
                            ${isComingSoon ? 'after:bg-zinc-700' : 'after:bg-zinc-400'}
                            after:rounded-full after:h-4 after:w-4 after:transition-all after:duration-200
                            peer-checked:after:translate-x-[18px] peer-checked:after:bg-white"></div>
                    </label>

                    <!-- Event Info -->
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-[13px] font-bold ${isComingSoon ? 'text-zinc-600' : cat.enabled ? 'text-white' : 'text-zinc-500'} leading-tight">${cat.label}</span>
                            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ring-1 ${stateCls}">
                                <i data-lucide="${stateIcon}" class="w-2.5 h-2.5"></i>
                                ${stateLabel}
                            </span>
                            <!-- Delivery channel badge -->
                            <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold ring-1 ${wire.badge}" title="${wire.desc}">
                                <i data-lucide="${chan.icon}" class="w-2.5 h-2.5"></i>
                                ${chan.label}
                            </span>
                        </div>

                        <!-- Trigger timing -->
                        <div class="flex items-center gap-1.5 mt-1">
                            <i data-lucide="zap" class="w-3 h-3 ${isComingSoon ? 'text-zinc-700' : 'text-zinc-600'} flex-shrink-0"></i>
                            <span class="text-[11px] ${isComingSoon ? 'text-zinc-700' : 'text-zinc-400'} leading-snug">${trigger}</span>
                        </div>

                        <!-- Recipients + purpose row -->
                        <div class="flex items-center gap-2 mt-1.5 flex-wrap">
                            <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold ring-1 ${isComingSoon ? 'bg-zinc-800/30 text-zinc-600 ring-zinc-700/20' : audience.color}" title="${audience.desc}">
                                <i data-lucide="${audience.icon}" class="w-2.5 h-2.5"></i>
                                ${audience.label}
                            </span>
                            ${purpose ? `<span class="text-[10px] ${isComingSoon ? 'text-zinc-700' : 'text-zinc-600'} leading-snug hidden sm:inline">— ${purpose}</span>` : ''}
                        </div>

                        ${!isComingSoon ? `
                        <!-- Current message preview (always visible for wired categories) -->
                        <div class="mt-2 px-2.5 py-1.5 rounded-md text-[11px] leading-relaxed border border-dashed ${hasCustom ? 'border-amber-800/40 text-amber-300/70 bg-amber-500/[0.03]' : 'border-zinc-800/60 text-zinc-500 bg-white/[0.01]'}">
                            ${hasCustom ? '<span class="text-amber-500/60 font-bold uppercase text-[8px] tracking-wider mr-1">Custom:</span>' : ''}${cat.custom_message || cat.default_message}
                        </div>
                        ` : ''}
                    </div>

                    <!-- Expand toggle (hidden for coming_soon) -->
                    ${!isComingSoon ? `
                    <button class="auto-expand-btn w-7 h-7 rounded-lg flex items-center justify-center text-zinc-600 hover:text-zinc-300 hover:bg-white/5 transition-colors flex-shrink-0 mt-0.5" data-key="${cat.key}" title="Edit message">
                        <i data-lucide="chevron-down" class="w-4 h-4 transition-transform duration-200"></i>
                    </button>
                    ` : ''}
                </div>

                ${!isComingSoon ? `
                <!-- Expandable Configuration Section (animated) -->
                <div class="auto-card-body auto-card-body-anim auto-card-body-collapsed border-t border-dc-border/30" data-body-key="${cat.key}" style="max-height: 0;">
                    <div class="px-4 sm:px-5 py-4 space-y-4" style="background: rgba(0,0,0,0.2);">
                        <!-- Default message -->
                        <div>
                            <label class="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-2">
                                <i data-lucide="file-text" class="w-3 h-3"></i> Default Message
                            </label>
                            <div class="px-3 py-2.5 rounded-lg text-[12px] text-zinc-400 leading-relaxed border border-dashed border-zinc-800" style="background: rgba(255,255,255,0.015);">
                                ${cat.default_message}
                            </div>
                        </div>

                        <!-- Custom override -->
                        <div>
                            <label class="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-2">
                                <i data-lucide="pencil" class="w-3 h-3"></i> Custom Override
                                <span class="normal-case font-normal text-zinc-600 ml-1">— leave empty to use default</span>
                            </label>
                            <textarea class="auto-custom-msg w-full rounded-lg px-3.5 py-2.5 text-[13px] leading-relaxed resize-none transition-colors duration-200
                                bg-zinc-900/80 border border-zinc-700/60 text-zinc-200
                                placeholder-zinc-600
                                focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20"
                                data-key="${cat.key}"
                                rows="2"
                                placeholder="Write a custom message that participants will see…">${cat.custom_message || ''}</textarea>
                        </div>

                        <!-- Live preview — shows what participants actually receive -->
                        <div>
                            <label class="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-2">
                                <i data-lucide="eye" class="w-3 h-3"></i> What participants will see
                            </label>
                            <div class="rounded-lg border border-zinc-800/80 overflow-hidden" style="background: #0b0b12;">
                                <div class="flex items-center gap-2.5 px-3.5 py-2.5 border-b border-zinc-800/40">
                                    <div class="w-6 h-6 rounded-md bg-blue-500/15 flex items-center justify-center">
                                        <i data-lucide="bell" class="w-3 h-3 text-blue-400"></i>
                                    </div>
                                    <div class="flex-1 min-w-0">
                                        <span class="text-xs font-bold text-zinc-200">${cat.label}</span>
                                        <span class="ml-2 text-[9px] text-zinc-600">Tournament Notification</span>
                                    </div>
                                    <span class="text-[9px] text-zinc-600 tabular-nums">just now</span>
                                </div>
                                <div class="px-3.5 py-3 text-[12px] text-zinc-300 leading-relaxed auto-preview-text" data-preview-key="${cat.key}">
                                    ${cat.custom_message || cat.default_message}
                                </div>
                                <div class="px-3.5 pb-2.5 flex items-center gap-2">
                                    <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-bold ring-1 ${audience.color}">
                                        <i data-lucide="${audience.icon}" class="w-2 h-2"></i> Sent to: ${audience.label}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                ` : ''}
            </div>`;
    }

    /* ── Right Summary ─────────────────────────────────────────────── */

    function _autoRenderSummary() {
        const s = _autoStats();
        return `
            <div class="space-y-5">
                <div>
                    <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-zinc-600">Configuration Summary</span>
                </div>

                <div class="space-y-3">
                    <div class="flex items-center justify-between">
                        <span class="flex items-center gap-1.5 text-xs text-zinc-400"><i data-lucide="check-circle" class="w-3 h-3 text-emerald-500"></i> Active</span>
                        <span class="text-sm font-bold text-emerald-400 tabular-nums" id="auto-sum-active">${s.enabled}</span>
                    </div>
                    <div class="w-full h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                        <div class="h-full rounded-full bg-emerald-500 transition-all duration-300" id="auto-sum-bar" style="width: ${s.wired ? (s.enabled / s.wired * 100) : 0}%"></div>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="flex items-center gap-1.5 text-xs text-zinc-400"><i data-lucide="circle-off" class="w-3 h-3 text-zinc-600"></i> Disabled</span>
                        <span class="text-sm font-bold text-zinc-500 tabular-nums" id="auto-sum-disabled">${s.disabled}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="flex items-center gap-1.5 text-xs text-zinc-400"><i data-lucide="lock" class="w-3 h-3 text-zinc-600"></i> Coming Soon</span>
                        <span class="text-sm font-bold text-zinc-600 tabular-nums">${s.comingSoon}</span>
                    </div>
                    <div class="flex items-center justify-between">
                        <span class="flex items-center gap-1.5 text-xs text-zinc-400"><i data-lucide="pencil" class="w-3 h-3 text-amber-500"></i> Custom</span>
                        <span class="text-sm font-bold text-amber-400 tabular-nums" id="auto-sum-custom">${s.customized}</span>
                    </div>
                    <div class="flex items-center justify-between border-t border-zinc-800/60 pt-2">
                        <span class="text-xs text-zinc-400">Wired events</span>
                        <span class="text-sm font-bold text-zinc-300 tabular-nums">${s.wired} of ${s.total}</span>
                    </div>
                </div>

                <div class="border-t border-zinc-800/80 pt-4">
                    <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-zinc-600">Unsaved Changes</span>
                    <div class="mt-2 flex items-center gap-2" id="auto-dirty-indicator">
                        <span class="w-2 h-2 rounded-full bg-zinc-700"></span>
                        <span class="text-[11px] text-zinc-600">No changes</span>
                    </div>
                </div>

                <div class="border-t border-zinc-800/80 pt-4">
                    <span class="text-[9px] font-bold uppercase tracking-[0.15em] text-zinc-600">Phase Breakdown</span>
                    <div class="mt-3 space-y-2.5">
                        ${(_autoData.groups || []).map(g => {
                            const cats = _autoLocal.filter(c => c.group === g.key);
                            const wired = cats.filter(c => c.wiring !== 'coming_soon');
                            const active = wired.filter(c => c.enabled).length;
                            const pct = wired.length ? (active / wired.length * 100) : 0;
                            return `
                                <div>
                                    <div class="flex items-center justify-between text-[11px] mb-1">
                                        <span class="text-zinc-500">${g.label}</span>
                                        <span class="${!wired.length ? 'text-zinc-700' : active === wired.length ? 'text-emerald-400' : (active === 0 ? 'text-zinc-600' : 'text-amber-400')} tabular-nums">${wired.length ? active + '/' + wired.length : '—'}</span>
                                    </div>
                                    <div class="w-full h-1 rounded-full bg-zinc-800 overflow-hidden">
                                        <div class="h-full rounded-full transition-all duration-300 ${!wired.length ? 'bg-zinc-800' : active === wired.length ? 'bg-emerald-500/60' : (active === 0 ? 'bg-zinc-700' : 'bg-amber-500/50')}" style="width: ${pct}%"></div>
                                    </div>
                                </div>`;
                        }).join('')}
                    </div>
                </div>
            </div>`;
    }

    /* ── Footer ────────────────────────────────────────────────────── */

    function _autoRenderFooter() {
        return `
            <footer class="flex items-center justify-between gap-3 px-4 sm:px-6 py-3 sm:py-3.5 border-t border-dc-border/60" style="background: #0a0a10;">
                <button id="auto-btn-reset" class="px-3 sm:px-4 py-2 rounded-lg text-[12px] sm:text-[13px] font-semibold text-zinc-400 hover:text-white border border-zinc-700/60 hover:border-zinc-600 bg-transparent hover:bg-white/5 transition-all duration-150">
                    <span class="hidden sm:inline">Reset to Defaults</span><span class="sm:hidden">Reset</span>
                </button>
                <div class="flex items-center gap-2">
                    <button id="auto-btn-cancel" class="px-4 sm:px-5 py-2 rounded-lg text-[12px] sm:text-[13px] font-semibold text-zinc-400 hover:text-white hover:bg-white/5 transition-all duration-150">
                        Cancel
                    </button>
                    <button id="auto-btn-save" class="px-4 sm:px-6 py-2 rounded-lg text-[12px] sm:text-[13px] font-bold text-white transition-all duration-150"
                        style="background: linear-gradient(135deg, var(--color-primary, #3b82f6) 0%, var(--color-primary-dark, #1d4ed8) 100%); box-shadow: 0 2px 12px rgba(59,130,246,0.3);">
                        <span class="hidden sm:inline">Save Configuration</span><span class="sm:hidden">Save</span>
                    </button>
                </div>
            </footer>`;
    }

    /* ── Event Bindings ────────────────────────────────────────────── */

    function _autoBindNav() {
        const root = document.getElementById('auto-panel-root');
        if (!root) return;
        root.querySelectorAll('.auto-nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                _autoActiveGroup = btn.dataset.group;
                _autoRefreshUI();
            });
        });
    }

    function _autoBindCards() {
        const root = document.getElementById('auto-panel-root');
        if (!root) return;

        // Toggles
        root.querySelectorAll('.auto-toggle').forEach(toggle => {
            toggle.addEventListener('change', () => {
                const cat = _autoLocal.find(c => c.key === toggle.dataset.key);
                if (cat) cat.enabled = toggle.checked;
                _autoRefreshUI();
            });
        });

        // Expand/collapse with smooth animation
        root.querySelectorAll('.auto-expand-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const body = root.querySelector(`[data-body-key="${btn.dataset.key}"]`);
                if (!body) return;
                const icon = btn.querySelector('[data-lucide]');
                const isCollapsed = body.classList.contains('auto-card-body-collapsed');
                if (isCollapsed) {
                    // Expand: measure content, set max-height, animate
                    body.classList.remove('auto-card-body-collapsed');
                    body.classList.add('auto-card-body-expanded');
                    body.style.maxHeight = body.scrollHeight + 'px';
                    if (icon) icon.style.transform = 'rotate(180deg)';
                    // Re-init lucide icons in newly visible section
                    if (typeof lucide !== 'undefined') lucide.createIcons({ attrs: { 'stroke-width': 1.75 } });
                } else {
                    // Collapse: set explicit height first, then collapse
                    body.style.maxHeight = body.scrollHeight + 'px';
                    requestAnimationFrame(() => {
                        body.classList.add('auto-card-body-collapsed');
                        body.classList.remove('auto-card-body-expanded');
                        body.style.maxHeight = '0';
                    });
                    if (icon) icon.style.transform = '';
                }
            });
        });

        // Custom message textarea live update
        root.querySelectorAll('.auto-custom-msg').forEach(ta => {
            ta.addEventListener('input', () => {
                const cat = _autoLocal.find(c => c.key === ta.dataset.key);
                if (cat) cat.custom_message = ta.value.trim();
                // Update preview
                const preview = root.querySelector(`[data-preview-key="${ta.dataset.key}"]`);
                if (preview) preview.textContent = ta.value.trim() || cat.default_message;
                _autoUpdateDirtyState();
            });
        });
    }

    function _autoBindFooter() {
        const root = document.getElementById('auto-panel-root');
        if (!root) return;
        root.querySelector('#auto-close-btn')?.addEventListener('click', _closeAutomation);
        root.querySelector('#auto-btn-cancel')?.addEventListener('click', _closeAutomation);
        root.querySelector('#auto-btn-save')?.addEventListener('click', saveAutomation);
        root.querySelector('#auto-btn-reset')?.addEventListener('click', _autoResetDefaults);
    }

    /* ── UI Refresh ────────────────────────────────────────────────── */

    function _autoRefreshUI() {
        const root = document.getElementById('auto-panel-root');
        if (!root) return;

        const nav = root.querySelector('#auto-nav');
        if (nav) nav.innerHTML = _autoRenderNav();

        const mobileNav = root.querySelector('#auto-mobile-nav');
        if (mobileNav) mobileNav.innerHTML = _autoRenderMobileNav();

        const content = root.querySelector('#auto-content');
        if (content) content.innerHTML = _autoRenderContent();

        const summary = root.querySelector('#auto-summary');
        if (summary) summary.innerHTML = _autoRenderSummary();

        _autoBindNav();
        _autoBindCards();
        _autoUpdateDirtyState();

        if (typeof lucide !== 'undefined') lucide.createIcons({ attrs: { 'stroke-width': 1.75 } });
    }

    function _autoUpdateDirtyState() {
        const dirty = _isAutoDirty();
        const el = document.getElementById('auto-dirty-indicator');
        if (el) {
            el.innerHTML = dirty
                ? '<span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span><span class="text-[11px] text-amber-400 font-semibold">Unsaved changes</span>'
                : '<span class="w-2 h-2 rounded-full bg-zinc-700"></span><span class="text-[11px] text-zinc-600">No changes</span>';
        }
        const s = _autoStats();
        const setTx = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
        setTx('auto-sum-active', s.enabled);
        setTx('auto-sum-disabled', s.disabled);
        setTx('auto-sum-custom', s.customized);
        const bar = document.getElementById('auto-sum-bar');
        if (bar) bar.style.width = (s.wired ? (s.enabled / s.wired * 100) : 0) + '%';
    }

    /* ── Save ──────────────────────────────────────────────────────── */

    async function saveAutomation() {
        const categories = _autoLocal.map(c => ({
            key: c.key,
            enabled: c.enabled,
            custom_message: c.custom_message || '',
        }));

        const btn = document.getElementById('auto-btn-save');
        if (btn) { btn.textContent = 'Saving…'; btn.style.opacity = '0.6'; btn.disabled = true; }

        try {
            await API.put('announcements/automation/', { categories });
            _autoOriginal = JSON.stringify(_autoLocal.map(c => ({ k: c.key, e: c.enabled, m: c.custom_message })));
            _autoUpdateDirtyState();
            window.TOC?.toast?.('Automation config saved', 'success');

            setTimeout(() => {
                const root = document.getElementById('auto-panel-root');
                if (!root) return;
                // Animate out
                const backdrop = root.querySelector('#auto-backdrop');
                const shell = root.querySelector('#auto-panel-shell');
                if (backdrop) { backdrop.classList.remove('auto-backdrop-enter'); backdrop.classList.add('auto-backdrop-exit'); }
                if (shell)    { shell.classList.remove('auto-panel-enter');    shell.classList.add('auto-panel-exit'); }
                setTimeout(() => {
                    root.remove();
                    document.body.style.overflow = '';
                    document.removeEventListener('keydown', _autoEscHandler);
                    refresh();
                }, 250);
            }, 600);
        } catch (e) {
            window.TOC?.toast?.('Failed to save automation config', 'error');
        } finally {
            if (btn) { btn.textContent = 'Save Configuration'; btn.style.opacity = '1'; btn.disabled = false; }
        }
    }

    function _autoResetDefaults() {
        if (!confirm('Reset all automation settings to defaults? This will enable all categories and clear custom messages.')) return;
        _autoLocal.forEach(c => {
            c.enabled = true;
            c.custom_message = '';
        });
        _autoRefreshUI();
    }

    /* ------------------------------------------------------------------ */
    /*  Init / Boot                                                        */
    /* ------------------------------------------------------------------ */

    let _booted = false;

    function init() {
        if (_booted) { refresh(); return; }
        _booted = true;
        refresh();
    }

    function _boot() {
        const activeTab = (window.location.hash || '#overview').replace('#', '') || 'overview';
        if (activeTab === 'announcements') init();

        document.addEventListener('toc:tab-changed', function (e) {
            if (e.detail && e.detail.tab === 'announcements') init();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _boot);
    } else {
        _boot();
    }

    // Public API
    window.TOC = window.TOC || {};
    window.TOC.announcements = {
        init,
        refresh,
        debouncedRefresh,
        openCompose,
        confirmCompose,
        editAnnouncement,
        confirmEdit,
        deleteAnnouncement,
        togglePin,
        broadcast,
        confirmBroadcast,
        openQuickComms,
        openSmartCard,
        sendSmartCard,
        sendQuickComm,
        openAutomation,
        saveAutomation,
        _closeOverlay: closeOverlay,
        _closeAutomation,
    };
})();
