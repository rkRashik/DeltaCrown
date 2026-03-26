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
        if (!announcements.length) {
            container.innerHTML = '<div class="py-12 text-center text-dc-text text-xs">No announcements yet. Compose one!</div>';
            return;
        }
        container.innerHTML = announcements.map(a => {
            const visuals = inferAnnouncementVisual(a);
            const pinIcon = a.is_pinned ? '<i data-lucide="pin" class="w-3.5 h-3.5 text-dc-warning"></i>' : '';
            const importantBadge = a.is_important ? '<span class="px-2 py-0.5 text-xs rounded-full bg-dc-danger/10 text-dc-danger">Important</span>' : '';
            const typeBadge = '<span class="px-2 py-0.5 text-xs rounded-full ' + visuals.tone + '">' + visuals.label + '</span>';
            const timeAgo = relativeTime(a.created_at);
            return `
                <div class="glass-box rounded-xl p-5 space-y-3 ${a.is_important ? 'border-l-2 border-l-dc-danger' : ''}">
                    <div class="flex items-start justify-between gap-3">
                        <div class="flex items-center gap-2">
                            ${pinIcon}
                            <span class="text-base leading-none">${visuals.symbol}</span>
                            <h4 class="font-bold text-white text-sm flex items-center gap-1.5"><i data-lucide="${visuals.icon}" class="w-3.5 h-3.5 text-theme"></i>${a.title}</h4>
                            ${typeBadge}
                            ${importantBadge}
                        </div>
                        <div class="flex items-center gap-2 shrink-0">
                            <button onclick="TOC.announcements.togglePin(${a.id}, ${!a.is_pinned})" title="${a.is_pinned ? 'Unpin' : 'Pin'}" data-cap-require="make_announcements" class="text-dc-text hover:text-dc-warning">
                                <i data-lucide="${a.is_pinned ? 'pin-off' : 'pin'}" class="w-3.5 h-3.5"></i>
                            </button>
                            <button onclick="TOC.announcements.editAnnouncement(${a.id})" data-cap-require="make_announcements" class="text-dc-text hover:text-dc-textBright">
                                <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
                            </button>
                            <button onclick="TOC.announcements.deleteAnnouncement(${a.id})" data-cap-require="make_announcements" class="text-dc-text hover:text-dc-danger">
                                <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                            </button>
                        </div>
                    </div>
                    <p class="text-sm text-dc-text leading-relaxed">${a.message}</p>
                    <div class="flex items-center gap-3 text-xs text-dc-text/60">
                        <span>${a.author}</span>
                        <span>·</span>
                        <span>${timeAgo}</span>
                    </div>
                </div>
            `;
        }).join('');
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
                <button onclick="TOC.announcements.confirmCompose()" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Publish</button>
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
                <button onclick="TOC.announcements.confirmEdit(${id})" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Save</button>
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
                <button onclick="TOC.announcements.confirmBroadcast('${target}')" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Send Broadcast</button>
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
                        <button onclick="TOC.announcements.openSmartCard('${t.key}')" class="w-full p-3 rounded-lg border border-dc-border hover:border-theme/40 transition-colors text-left flex items-center gap-3">
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
                '<button onclick="TOC.announcements.sendSmartCard(\'' + templateKey + '\')" class="w-full py-2 rounded-lg bg-theme text-black text-sm font-bold hover:opacity-90">Publish Smart Card</button>' +
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

    /* ------------------------------------------------------------------ */
    /*  Init                                                               */
    /* ------------------------------------------------------------------ */

    function init() {
        refresh();
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
    };
})();
