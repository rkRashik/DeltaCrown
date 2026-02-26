/**
 * TOC Core — Tournament Operations Center Shell Runtime
 *
 * IIFE that exposes `window.TOC` namespace.
 *
 * Public API:
 *   TOC.navigate(tabId)               — Hash-based tab router
 *   TOC.fetch(url, opts)              — CSRF-aware async fetch wrapper
 *   TOC.drawer.open(title, html)      — Slide-out right drawer
 *   TOC.drawer.close()
 *   TOC.toast(message, type, opts)    — Toast notifications
 *   TOC.cmdk.open() / .close() / .toggle()  — Command palette
 *   TOC.badge(tabId, count)           — Nav badge update
 *   TOC.config                        — Alias to TOC_CONFIG
 *
 * Sprint 0 — Foundation Shell
 * Tracker: S0-J1 through S0-J8
 */

;(function () {
    'use strict';

    /* ───────────────────────────────────────────────
       S0-J1: DOM Helpers
       ─────────────────────────────────────────────── */

    const $ = (sel, root) => (root || document).querySelector(sel);
    const $$ = (sel, root) => [...(root || document).querySelectorAll(sel)];

    /* ───────────────────────────────────────────────
       S0-J2: Config
       ─────────────────────────────────────────────── */

    const CFG = window.TOC_CONFIG || {};
    const IS_MAC = /Mac|iPod|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
    const MOD_KEY_LABEL = IS_MAC ? '⌘' : 'Ctrl';

    /* ───────────────────────────────────────────────
       S0-J3: Tab Router (hash-based)
       ─────────────────────────────────────────────── */

    const ACTIVE_NAV_CLASSES = ['bg-theme-surface', 'text-theme', 'font-bold'];
    const INACTIVE_NAV_CLASSES = ['text-dc-text', 'hover:bg-dc-panel', 'hover:text-white', 'font-medium'];

    function navigate(tabId) {
        if (!tabId) tabId = 'overview';

        // Update hash without triggering extra hashchange
        const cleanHash = '#' + tabId;
        if (window.location.hash !== cleanHash) {
            history.replaceState(null, '', cleanHash);
        }

        // Show / hide content panels
        $$('[data-tab-content]').forEach(panel => {
            if (panel.dataset.tabContent === tabId) {
                panel.classList.remove('hidden-view');
            } else {
                panel.classList.add('hidden-view');
            }
        });

        // Update sidebar active state
        $$('.toc-nav-btn[data-tab]').forEach(btn => {
            const isActive = btn.dataset.tab === tabId;
            ACTIVE_NAV_CLASSES.forEach(c => btn.classList.toggle(c, isActive));
            INACTIVE_NAV_CLASSES.forEach(c => btn.classList.toggle(c, !isActive));

            // Icon color
            const icon = $('i[data-lucide]', btn);
            if (icon) {
                icon.classList.toggle('text-theme', isActive);
            }
        });

        // Re-init Lucide icons for newly visible panel
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    function onHashChange() {
        const hash = window.location.hash.replace('#', '').trim();
        navigate(hash || 'overview');
    }

    window.addEventListener('hashchange', onHashChange);


    /* ───────────────────────────────────────────────
       S0-J4: Fetch Wrapper (CSRF-aware)
       ─────────────────────────────────────────────── */

    async function tocFetch(url, opts = {}) {
        const defaults = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CFG.csrfToken || '',
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
        };

        const config = {
            ...defaults,
            ...opts,
            headers: { ...defaults.headers, ...(opts.headers || {}) },
        };

        // Auto-serialize body objects
        if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
            config.body = JSON.stringify(config.body);
        }

        // Strip Content-Type for FormData (browser sets boundary)
        if (opts.body instanceof FormData) {
            delete config.headers['Content-Type'];
        }

        // Timeout via AbortController
        const timeout = opts.timeout || 30000;
        const controller = new AbortController();
        config.signal = controller.signal;
        const timer = setTimeout(() => controller.abort(), timeout);

        try {
            const res = await fetch(url, config);
            clearTimeout(timer);

            if (!res.ok) {
                const text = await res.text().catch(() => '');
                const err = new Error(`TOC Fetch ${res.status}: ${text.slice(0, 200)}`);
                err.status = res.status;
                err.response = res;
                throw err;
            }

            const ct = res.headers.get('content-type') || '';
            return ct.includes('application/json') ? res.json() : res.text();
        } catch (e) {
            clearTimeout(timer);
            if (e.name === 'AbortError') {
                throw new Error('TOC Fetch: Request timed out');
            }
            throw e;
        }
    }


    /* ───────────────────────────────────────────────
       S0-J5: Drawer API
       ─────────────────────────────────────────────── */

    const drawer = {
        el: () => $('#toc-drawer'),
        _titleEl: () => $('#toc-drawer-title'),
        _bodyEl: () => $('#toc-drawer-body'),
        _footerEl: () => $('#toc-drawer-footer'),

        open(title, bodyHtml, footerHtml) {
            const el = this.el();
            if (!el) return;

            this._titleEl().textContent = title || '';
            this._bodyEl().innerHTML = bodyHtml || '';

            const footer = this._footerEl();
            if (footerHtml) {
                footer.innerHTML = footerHtml;
                footer.classList.remove('hidden');
            } else {
                footer.innerHTML = '';
                footer.classList.add('hidden');
            }

            el.classList.remove('hidden');

            // Re-init Lucide icons inside drawer
            if (typeof lucide !== 'undefined') {
                lucide.createIcons({ nameAttr: 'data-lucide' });
            }
        },

        close() {
            const el = this.el();
            if (el) el.classList.add('hidden');
        },
    };


    /* ───────────────────────────────────────────────
       S0-J6: Toast API
       ─────────────────────────────────────────────── */

    const TOAST_ICONS = {
        success: 'check-circle-2',
        error: 'alert-triangle',
        warning: 'alert-circle',
        info: 'info',
    };

    const TOAST_COLORS = {
        success: { border: 'border-dc-success/30', bg: 'bg-dc-successBg', text: 'text-dc-success' },
        error:   { border: 'border-dc-danger/30',  bg: 'bg-dc-dangerBg',  text: 'text-dc-danger'  },
        warning: { border: 'border-dc-warning/30', bg: 'bg-dc-warningBg', text: 'text-dc-warning' },
        info:    { border: 'border-theme/30',       bg: 'bg-theme-surface', text: 'text-theme'     },
    };

    function toast(message, type = 'info', opts = {}) {
        const stack = $('#toc-toast-stack');
        if (!stack) return;

        const duration = opts.duration ?? 5000;
        const colors = TOAST_COLORS[type] || TOAST_COLORS.info;
        const iconName = TOAST_ICONS[type] || TOAST_ICONS.info;

        const el = document.createElement('div');
        el.className = `pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-lg border ${colors.border} ${colors.bg} bg-dc-surface shadow-[0_10px_30px_rgba(0,0,0,0.6)] min-w-[280px] max-w-[400px] opacity-0 translate-y-2 transition-all duration-300`;

        el.innerHTML = `
            <i data-lucide="${iconName}" class="w-4 h-4 ${colors.text} shrink-0"></i>
            <span class="text-xs text-dc-textBright flex-1">${escapeHtml(message)}</span>
            <button class="text-dc-text hover:text-white p-1 shrink-0" data-toast-dismiss>
                <i data-lucide="x" class="w-3.5 h-3.5"></i>
            </button>
        `;

        stack.appendChild(el);

        // Init icons in toast
        if (typeof lucide !== 'undefined') lucide.createIcons({ nameAttr: 'data-lucide' });

        // Slide-in animation
        requestAnimationFrame(() => {
            el.classList.remove('opacity-0', 'translate-y-2');
            el.classList.add('opacity-100', 'translate-y-0');
        });

        // Dismiss handler
        const dismissBtn = $('[data-toast-dismiss]', el);
        if (dismissBtn) {
            dismissBtn.addEventListener('click', () => removeToast(el));
        }

        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => removeToast(el), duration);
        }

        return el;
    }

    function removeToast(el) {
        if (!el || !el.parentNode) return;
        el.classList.add('opacity-0', 'translate-y-2');
        el.classList.remove('opacity-100', 'translate-y-0');
        setTimeout(() => el.remove(), 300);
    }


    /* ───────────────────────────────────────────────
       S0-J7: Command Palette (Cmd+K)
       ─────────────────────────────────────────────── */

    const cmdk = {
        el: () => $('#cmd-palette'),
        inputEl: () => $('#cmdk-input'),

        open() {
            const el = this.el();
            if (!el) return;
            el.classList.remove('hidden');
            // Small delay to let display settle before focusing
            setTimeout(() => {
                const input = this.inputEl();
                if (input) {
                    input.value = '';
                    input.focus();
                }
                this._resetFilter();
            }, 50);
        },

        close() {
            const el = this.el();
            if (el) el.classList.add('hidden');
        },

        toggle() {
            const el = this.el();
            if (!el) return;
            el.classList.contains('hidden') ? this.open() : this.close();
        },

        _resetFilter() {
            $$('.cmdk-item').forEach(item => {
                item.classList.remove('hidden');
                item.classList.remove('bg-dc-panel');
            });
        },

        _filter(query) {
            const q = query.toLowerCase().trim();
            const items = $$('.cmdk-item');
            let firstVisible = null;

            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                const visible = !q || text.includes(q);
                item.classList.toggle('hidden', !visible);
                item.classList.remove('bg-dc-panel');
                if (visible && !firstVisible) firstVisible = item;
            });

            // Highlight first visible item
            if (firstVisible) {
                firstVisible.classList.add('bg-dc-panel');
            }
        },

        _getHighlighted() {
            return $('.cmdk-item.bg-dc-panel:not(.hidden)');
        },

        _moveHighlight(direction) {
            const items = $$('.cmdk-item:not(.hidden)');
            if (!items.length) return;

            const current = this._getHighlighted();
            let idx = current ? items.indexOf(current) : -1;

            if (current) current.classList.remove('bg-dc-panel');

            idx += direction;
            if (idx < 0) idx = items.length - 1;
            if (idx >= items.length) idx = 0;

            items[idx].classList.add('bg-dc-panel');
            items[idx].scrollIntoView({ block: 'nearest' });
        },

        _executeHighlighted() {
            const item = this._getHighlighted();
            if (!item) return;

            const action = item.dataset.action;
            const target = item.dataset.target;

            if (action === 'navigate' && target) {
                navigate(target);
            }
            this.close();
        },
    };


    /* ───────────────────────────────────────────────
       S0-J7 (cont): Cmd+K Input Events
       ─────────────────────────────────────────────── */

    function initCmdK() {
        const input = cmdk.inputEl();
        if (!input) return;

        input.addEventListener('input', (e) => {
            cmdk._filter(e.target.value);
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                cmdk._moveHighlight(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                cmdk._moveHighlight(-1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                cmdk._executeHighlighted();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                cmdk.close();
            }
        });

        // Item clicks
        $$('.cmdk-item').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                const target = item.dataset.target;
                if (action === 'navigate' && target) {
                    navigate(target);
                }
                cmdk.close();
            });
        });
    }


    /* ───────────────────────────────────────────────
       S0-J8: Badge API
       ─────────────────────────────────────────────── */

    function badge(tabId, count) {
        const el = $(`[data-badge="${tabId}"]`);
        if (!el) return;

        if (count && count > 0) {
            el.textContent = count > 99 ? '99+' : String(count);
            el.classList.remove('hidden');
        } else {
            el.textContent = '';
            el.classList.add('hidden');
        }
    }


    /* ───────────────────────────────────────────────
       S0-J8 (cont): Sidebar Collapse
       ─────────────────────────────────────────────── */

    const SIDEBAR_KEY = 'toc-sidebar-collapsed';

    function initSidebarCollapse() {
        const sidebar = $('#toc-sidebar');
        const btn = $('#sidebar-collapse-btn');
        if (!sidebar || !btn) return;

        // Restore state
        if (localStorage.getItem(SIDEBAR_KEY) === '1') {
            sidebar.classList.add('collapsed');
        }

        btn.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            localStorage.setItem(SIDEBAR_KEY, sidebar.classList.contains('collapsed') ? '1' : '0');
        });
    }


    /* ───────────────────────────────────────────────
       Keyboard Shortcuts
       ─────────────────────────────────────────────── */

    function initKeyboard() {
        document.addEventListener('keydown', (e) => {
            // Cmd+K or Ctrl+K → toggle command palette
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                cmdk.toggle();
                return;
            }

            // Escape → close topmost overlay
            if (e.key === 'Escape') {
                // Command palette
                const cmdPalette = cmdk.el();
                if (cmdPalette && !cmdPalette.classList.contains('hidden')) {
                    cmdk.close();
                    return;
                }

                // Freeze modal
                const freezeModal = $('#modal-freeze');
                if (freezeModal && !freezeModal.classList.contains('hidden')) {
                    freezeModal.classList.add('hidden');
                    return;
                }

                // Drawer
                const drawerEl = drawer.el();
                if (drawerEl && !drawerEl.classList.contains('hidden')) {
                    drawer.close();
                    return;
                }
            }
        });
    }


    /* ───────────────────────────────────────────────
       Utility: Escape HTML
       ─────────────────────────────────────────────── */

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }


    /* ───────────────────────────────────────────────
       Initialization
       ─────────────────────────────────────────────── */

    function init() {
        initSidebarCollapse();
        initCmdK();
        initKeyboard();

        // Set platform-aware modifier key label
        const modKeyEl = $('#toc-search-mod-key');
        if (modKeyEl) modKeyEl.textContent = MOD_KEY_LABEL;

        // Navigate to hash or default to overview
        const hash = window.location.hash.replace('#', '').trim();
        navigate(hash || 'overview');
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }


    /* ───────────────────────────────────────────────
       Public API — window.TOC
       ─────────────────────────────────────────────── */

    /* ── Build api helper: callable as api(url, opts) AND api.get/post/put/delete ── */
    const apiBase = CFG.apiBase || '';
    const _apiUrl = (path) => `${apiBase}/${String(path).replace(/^\//, '')}`;
    const api = function (path, opts) { return tocFetch(_apiUrl(path), opts); };
    api.get    = (path) => tocFetch(_apiUrl(path));
    api.post   = (path, data) => tocFetch(_apiUrl(path), { method: 'POST', body: data });
    api.put    = (path, data) => tocFetch(_apiUrl(path), { method: 'PUT', body: data });
    api.patch  = (path, data) => tocFetch(_apiUrl(path), { method: 'PATCH', body: data });
    api.delete = (path) => tocFetch(_apiUrl(path), { method: 'DELETE' });
    api.getRaw = async (path) => {
        const res = await fetch(_apiUrl(path), {
            headers: { 'X-CSRFToken': CFG.csrfToken || '', 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin',
        });
        if (!res.ok) throw new Error(`TOC API ${res.status}`);
        return res;
    };

    window.TOC = {
        config: CFG,
        slug: CFG.tournamentSlug || '',
        api,
        navigate,
        fetch: tocFetch,
        tocFetch: tocFetch,
        drawer,
        toast,
        cmdk,
        badge,
    };

})();
