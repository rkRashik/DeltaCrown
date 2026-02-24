/**
 * TOC Sprint 11 — Audit Trail & Real-Time Infrastructure
 * ========================================================
 * S11-F1  Audit log viewer
 * S11-F2  WebSocket connection manager
 * S11-F3  Real-time indicators (ws dot, toast on events)
 * S11-F4  Tab badges update via WebSocket push
 */
;(function () {
    'use strict';

    const NS = (window.TOC = window.TOC || {});
    const api = (ep, opts) => NS.api(ep, opts);

    /* ════════════════════════════════════════════
     * S11-F1  Audit Log Viewer
     * ════════════════════════════════════════════ */

    let auditDebounce = null;
    const auditState = { entries: [] };

    async function refreshAuditLog () {
        try {
            const action = document.getElementById('audit-filter-action')?.value || '';
            const tab = document.getElementById('audit-filter-tab')?.value || '';
            const params = new URLSearchParams();
            if (action) params.set('action', action);
            if (tab) params.set('tab', tab);
            const qs = params.toString();
            auditState.entries = await api(`audit-log/${qs ? '?' + qs : ''}`);
            renderAuditLog();
        } catch (e) {
            console.warn('[TOC.audit] refresh failed', e);
        }
    }

    function debouncedRefresh () {
        clearTimeout(auditDebounce);
        auditDebounce = setTimeout(refreshAuditLog, 300);
    }

    function renderAuditLog () {
        const feed = document.getElementById('audit-log-feed');
        if (!feed) return;

        if (!auditState.entries.length) {
            feed.innerHTML = '<p class="text-xs text-dc-text italic text-center py-6">No audit entries found.</p>';
            return;
        }

        feed.innerHTML = auditState.entries.map(e => {
            const time = relativeTime(e.created_at);
            const tabBadge = e.detail?.tab
                ? `<span class="text-[9px] uppercase bg-dc-panel border border-dc-border text-dc-text px-1.5 py-0.5 rounded">${esc(e.detail.tab)}</span>`
                : '';
            return `
                <div class="flex items-start gap-3 px-3 py-2 rounded-lg hover:bg-dc-panel/50 transition-colors text-xs group">
                    <div class="w-6 h-6 rounded-full bg-dc-surface border border-dc-border flex items-center justify-center shrink-0 mt-0.5">
                        <i data-lucide="activity" class="w-3 h-3 text-dc-text"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="font-bold text-white">${esc(e.username)}</span>
                            <span class="text-dc-text font-mono">${esc(e.action)}</span>
                            ${tabBadge}
                        </div>
                        ${e.diff ? `<pre class="text-[10px] text-dc-text/70 mt-1 truncate max-w-full font-mono hidden group-hover:block">${esc(JSON.stringify(e.diff).slice(0, 200))}</pre>` : ''}
                    </div>
                    <span class="text-[10px] text-dc-text/50 shrink-0 whitespace-nowrap">${time}</span>
                </div>
            `;
        }).join('');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    /* ════════════════════════════════════════════
     * S11-F2  WebSocket Connection Manager
     * ════════════════════════════════════════════ */

    let ws = null;
    let wsReconnectTimer = null;
    let wsReconnectDelay = 1000;
    const MAX_RECONNECT_DELAY = 30000;

    function connectWebSocket () {
        const slug = NS.slug;
        if (!slug) return;

        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const url = `${proto}://${location.host}/ws/toc/${slug}/`;

        try {
            ws = new WebSocket(url);
        } catch (e) {
            console.warn('[TOC.ws] WebSocket constructor failed', e);
            setWSStatus('error');
            scheduleReconnect();
            return;
        }

        ws.onopen = () => {
            wsReconnectDelay = 1000; // Reset backoff
            setWSStatus('connected');
        };

        ws.onclose = () => {
            setWSStatus('disconnected');
            scheduleReconnect();
        };

        ws.onerror = () => {
            setWSStatus('error');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWSMessage(data);
            } catch (e) {
                console.warn('[TOC.ws] parse error', e);
            }
        };
    }

    function scheduleReconnect () {
        clearTimeout(wsReconnectTimer);
        wsReconnectTimer = setTimeout(() => {
            wsReconnectDelay = Math.min(wsReconnectDelay * 2, MAX_RECONNECT_DELAY);
            connectWebSocket();
        }, wsReconnectDelay);
    }

    /* ════════════════════════════════════════════
     * S11-F3  Real-Time Indicators
     * ════════════════════════════════════════════ */

    function setWSStatus (status) {
        const dot = document.getElementById('ws-dot');
        const label = document.getElementById('ws-label');
        if (!dot || !label) return;

        const map = {
            connected: { color: 'bg-dc-success', text: 'Live', cls: 'animate-pulse' },
            disconnected: { color: 'bg-dc-text/30', text: 'Offline', cls: '' },
            error: { color: 'bg-dc-danger', text: 'Error', cls: '' },
        };

        const s = map[status] || map.disconnected;
        dot.className = `w-2 h-2 rounded-full transition-colors ${s.color} ${s.cls}`;
        label.textContent = s.text;
        label.className = `text-[9px] font-mono uppercase ${status === 'connected' ? 'text-dc-success' : 'text-dc-text/50'}`;
    }

    function showToast (message, type = 'info') {
        const container = document.getElementById('toc-toast-container') || createToastContainer();
        const toast = document.createElement('div');
        const colors = {
            info: 'border-dc-info/30 bg-dc-info/10 text-dc-info',
            success: 'border-dc-success/30 bg-dc-success/10 text-dc-success',
            warning: 'border-dc-warning/30 bg-dc-warning/10 text-dc-warning',
            error: 'border-dc-danger/30 bg-dc-danger/10 text-dc-danger',
        };
        toast.className = `px-4 py-2 rounded-lg border text-xs font-bold ${colors[type] || colors.info} shadow-lg animate-slide-in`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 4000);
    }

    function createToastContainer () {
        const c = document.createElement('div');
        c.id = 'toc-toast-container';
        c.className = 'fixed bottom-6 right-6 z-[200] flex flex-col gap-2 items-end';
        document.body.appendChild(c);
        return c;
    }

    /* ════════════════════════════════════════════
     * S11-F4  Tab Badges via WebSocket
     * ════════════════════════════════════════════ */

    function handleWSMessage (data) {
        if (data.type === 'pong') return;

        if (data.type === 'event') {
            const et = data.event_type || '';
            const payload = data.payload || {};

            // Show toast for important events
            if (et === 'audit') {
                showToast(`${payload.user || 'System'}: ${payload.action || 'action'}`, 'info');
            } else if (et === 'match_update') {
                showToast('Match score updated', 'success');
                incrementBadge('matches');
            } else if (et === 'registration') {
                showToast('New registration', 'info');
                incrementBadge('participants');
            } else if (et === 'dispute') {
                showToast('Dispute activity', 'warning');
                incrementBadge('disputes');
            } else if (et === 'announcement') {
                showToast('New announcement', 'info');
                incrementBadge('announcements');
            }

            // Refresh audit log if open
            if (document.getElementById('settings-audit-section')?.open) {
                debouncedRefresh();
            }
        }
    }

    function incrementBadge (tabName) {
        const btn = document.querySelector(`[data-tab="${tabName}"]`);
        if (!btn) return;

        let badge = btn.querySelector('.ws-badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'ws-badge absolute -top-1 -right-1 w-4 h-4 flex items-center justify-center text-[8px] font-bold bg-dc-danger text-white rounded-full';
            badge.textContent = '0';
            btn.style.position = 'relative';
            btn.appendChild(badge);
        }
        const count = parseInt(badge.textContent || '0') + 1;
        badge.textContent = count > 9 ? '9+' : count;
    }

    /* ────────────────────────────────────────────
     * Helpers
     * ──────────────────────────────────────────── */
    function esc (s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

    function relativeTime (dateStr) {
        if (!dateStr) return '';
        const diff = (Date.now() - new Date(dateStr).getTime()) / 1000;
        if (diff < 60) return 'just now';
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
        return Math.floor(diff / 86400) + 'd ago';
    }

    /* ────────────────────────────────────────────
     * Init
     * ──────────────────────────────────────────── */
    function init () {
        refreshAuditLog();
        connectWebSocket();
    }

    /* ── Public API ── */
    NS.audit = {
        init,
        refresh: refreshAuditLog,
        debouncedRefresh,
        connectWebSocket,
        showToast,
    };

})();
