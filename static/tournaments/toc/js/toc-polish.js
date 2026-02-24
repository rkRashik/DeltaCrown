/**
 * TOC Sprint 12 — Polish, Edge Cases & Tier-1 Hardening
 * =======================================================
 * S12-T1  Loading skeleton states for all tabs
 * S12-T2  Error boundary: graceful error states per tab with retry
 * S12-T3  Empty states: contextual messaging for zero rows
 * S12-T4  Keyboard accessibility: focus management, aria attributes
 * S12-T5  Performance: lazy-load tabs, debounce, virtual scroll stub
 * S12-T6  Mobile/tablet responsive helpers
 * S12-T7  Dark mode consistency (already dc-* system — verify pass)
 * S12-T8  Edge cases: stale data, concurrent edit warnings
 * S12-T9  Stress test readiness: pagination guards, DOM limit
 * S12-T10 Final review helpers
 */
;(function () {
    'use strict';

    const NS = (window.TOC = window.TOC || {});

    /* ════════════════════════════════════════════
     * S12-T1  Loading Skeleton States
     * ════════════════════════════════════════════ */

    function showSkeleton (containerId, rows = 4) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = Array.from({ length: rows }, () =>
            `<div class="glass-box rounded-xl p-5 animate-pulse">
                <div class="h-4 bg-dc-bg rounded w-3/4 mb-3"></div>
                <div class="h-3 bg-dc-bg rounded w-1/2"></div>
            </div>`
        ).join('');
    }

    function showLoadingSpinner (containerId) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = `
            <div class="flex items-center justify-center py-12">
                <div class="w-6 h-6 border-2 border-theme border-t-transparent rounded-full animate-spin"></div>
            </div>
        `;
    }

    /* ════════════════════════════════════════════
     * S12-T2  Error Boundary
     * ════════════════════════════════════════════ */

    /**
     * Wrap any async tab loader in error boundary.
     * Usage: TOC.polish.withErrorBoundary('container-id', async () => { ... })
     */
    async function withErrorBoundary (containerId, loaderFn) {
        const el = document.getElementById(containerId);
        try {
            showLoadingSpinner(containerId);
            await loaderFn();
        } catch (err) {
            console.error(`[TOC] Error loading ${containerId}:`, err);
            if (el) {
                el.innerHTML = `
                    <div class="flex flex-col items-center justify-center py-12 text-center">
                        <i data-lucide="alert-triangle" class="w-10 h-10 text-dc-danger mb-3"></i>
                        <p class="text-sm font-bold text-dc-danger">Failed to load data</p>
                        <p class="text-xs text-dc-text mt-1 mb-4">${esc(err.message || 'Unknown error')}</p>
                        <button onclick="location.reload()" class="px-4 py-2 rounded-lg border border-dc-border text-dc-text text-xs hover:bg-dc-surface transition-all">
                            <i data-lucide="refresh-cw" class="w-3 h-3 inline mr-1"></i> Retry
                        </button>
                    </div>
                `;
                if (typeof lucide !== 'undefined') lucide.createIcons();
            }
        }
    }

    /* ════════════════════════════════════════════
     * S12-T3  Empty States
     * ════════════════════════════════════════════ */

    const EMPTY_MESSAGES = {
        participants: { icon: 'users', title: 'No Participants', desc: 'Registrations will appear here once players sign up.' },
        payments: { icon: 'wallet', title: 'No Payments', desc: 'Payment records will appear when entry fees are processed.' },
        brackets: { icon: 'git-branch', title: 'No Brackets', desc: 'Generate brackets once registration is finalized.' },
        matches: { icon: 'swords', title: 'No Matches', desc: 'Matches will be created when brackets are generated.' },
        disputes: { icon: 'shield-alert', title: 'No Disputes', desc: 'All clear! No disputes have been filed.' },
        announcements: { icon: 'megaphone', title: 'No Announcements', desc: 'Create an announcement to communicate with participants.' },
        'audit-log-feed': { icon: 'scroll-text', title: 'No Activity', desc: 'Audit entries will appear as actions are performed.' },
        'staff-grid': { icon: 'users', title: 'No Staff', desc: 'Assign tournament staff to manage operations.' },
        'cert-template-list': { icon: 'award', title: 'No Templates', desc: 'Create a certificate template to get started.' },
    };

    function showEmptyState (containerId, customMsg) {
        const el = document.getElementById(containerId);
        if (!el) return;

        const cfg = customMsg || EMPTY_MESSAGES[containerId] || { icon: 'inbox', title: 'No Data', desc: 'Nothing to display.' };

        el.innerHTML = `
            <div class="flex flex-col items-center justify-center py-10 text-center">
                <i data-lucide="${cfg.icon}" class="w-12 h-12 text-dc-text/20 mb-3"></i>
                <p class="text-sm font-bold text-dc-text">${cfg.title}</p>
                <p class="text-xs text-dc-text/60 mt-1">${cfg.desc}</p>
            </div>
        `;
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    /* ════════════════════════════════════════════
     * S12-T4  Keyboard Accessibility
     * ════════════════════════════════════════════ */

    function initAccessibility () {
        // Tab navigation with arrow keys
        const tabBtns = document.querySelectorAll('[data-tab]');
        tabBtns.forEach((btn, idx) => {
            btn.setAttribute('role', 'tab');
            btn.setAttribute('tabindex', idx === 0 ? '0' : '-1');
            btn.addEventListener('keydown', (e) => {
                let target = null;
                if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                    target = tabBtns[(idx + 1) % tabBtns.length];
                } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
                    target = tabBtns[(idx - 1 + tabBtns.length) % tabBtns.length];
                } else if (e.key === 'Home') {
                    target = tabBtns[0];
                } else if (e.key === 'End') {
                    target = tabBtns[tabBtns.length - 1];
                }
                if (target) {
                    e.preventDefault();
                    target.focus();
                    target.click();
                }
            });
        });

        // Escape closes overlays/drawers
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const overlay = document.getElementById('toc-overlay');
                if (overlay && !overlay.classList.contains('hidden')) {
                    overlay.classList.add('hidden');
                    return;
                }
                const drawer = document.getElementById('toc-drawer');
                if (drawer && !drawer.classList.contains('hidden')) {
                    if (NS.drawer && NS.drawer.close) NS.drawer.close();
                }
            }
        });

        // Focus trap for modals
        document.addEventListener('keydown', (e) => {
            if (e.key !== 'Tab') return;
            const overlay = document.getElementById('toc-overlay');
            if (!overlay || overlay.classList.contains('hidden')) return;

            const focusable = overlay.querySelectorAll('button, input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (!focusable.length) return;

            const first = focusable[0];
            const last = focusable[focusable.length - 1];

            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        });

        // ARIA labels for main landmarks
        const sidebar = document.querySelector('aside');
        if (sidebar) sidebar.setAttribute('aria-label', 'Tournament navigation');

        const main = document.querySelector('main');
        if (main) main.setAttribute('role', 'main');

        // ARIA attributes for glass-box details elements
        document.querySelectorAll('details.glass-box').forEach(d => {
            d.setAttribute('role', 'region');
            const summary = d.querySelector('summary');
            if (summary) {
                summary.setAttribute('role', 'button');
                summary.setAttribute('aria-expanded', d.open ? 'true' : 'false');
                d.addEventListener('toggle', () => {
                    summary.setAttribute('aria-expanded', d.open ? 'true' : 'false');
                });
            }
        });
    }

    /* ════════════════════════════════════════════
     * S12-T5  Performance: Lazy-Load Tabs
     * ════════════════════════════════════════════ */

    const loadedTabs = new Set();

    function registerLazyTab (tabName, loaderFn) {
        NS._lazyTabs = NS._lazyTabs || {};
        NS._lazyTabs[tabName] = loaderFn;
    }

    function onTabSwitch (tabName) {
        if (loadedTabs.has(tabName)) return;
        loadedTabs.add(tabName);

        const loader = NS._lazyTabs && NS._lazyTabs[tabName];
        if (loader) {
            loader();
        }
    }

    // Debounce utility (S12-T5)
    function debounce (fn, delay = 300) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    // Virtual scroll stub — for tables with 500+ rows
    function setupVirtualScroll (containerId, items, renderRow, rowHeight = 40) {
        const el = document.getElementById(containerId);
        if (!el || items.length < 200) {
            // Below threshold, render normally
            return false;
        }

        const totalHeight = items.length * rowHeight;
        const viewportHeight = el.clientHeight || 400;
        const buffer = 10;

        el.style.height = viewportHeight + 'px';
        el.style.overflow = 'auto';
        el.style.position = 'relative';

        const inner = document.createElement('div');
        inner.style.height = totalHeight + 'px';
        inner.style.position = 'relative';
        el.innerHTML = '';
        el.appendChild(inner);

        function render () {
            const scrollTop = el.scrollTop;
            const startIdx = Math.max(0, Math.floor(scrollTop / rowHeight) - buffer);
            const endIdx = Math.min(items.length, Math.ceil((scrollTop + viewportHeight) / rowHeight) + buffer);

            inner.innerHTML = '';
            for (let i = startIdx; i < endIdx; i++) {
                const row = document.createElement('div');
                row.style.position = 'absolute';
                row.style.top = (i * rowHeight) + 'px';
                row.style.width = '100%';
                row.innerHTML = renderRow(items[i], i);
                inner.appendChild(row);
            }
        }

        el.addEventListener('scroll', debounce(render, 16));
        render();
        return true;
    }

    /* ════════════════════════════════════════════
     * S12-T6  Mobile / Tablet Responsive
     * ════════════════════════════════════════════ */

    function initResponsive () {
        // Sidebar collapse on mobile
        const sidebar = document.querySelector('aside');
        const toggleBtn = document.getElementById('sidebar-toggle');

        if (sidebar && window.innerWidth < 1024) {
            sidebar.classList.add('hidden', 'lg:flex');
        }

        if (toggleBtn && sidebar) {
            toggleBtn.addEventListener('click', () => {
                sidebar.classList.toggle('hidden');
            });
        }

        // Horizontal scroll hint for tables on small screens
        document.querySelectorAll('table').forEach(table => {
            const wrapper = table.closest('.overflow-x-auto') || table.parentElement;
            if (wrapper && wrapper.scrollWidth > wrapper.clientWidth) {
                wrapper.classList.add('scroll-hint');
            }
        });
    }

    /* ════════════════════════════════════════════
     * S12-T7  Dark Mode Consistency
     * ════════════════════════════════════════════ */

    function auditDarkMode () {
        // Already using dc-* tokens — this is a verification pass
        const issues = [];
        document.querySelectorAll('*').forEach(el => {
            const style = getComputedStyle(el);
            const bg = style.backgroundColor;
            const color = style.color;

            // Flag white backgrounds or dark text on dark bg
            if (bg === 'rgb(255, 255, 255)' && el.offsetParent) {
                issues.push({ el, issue: 'White background detected' });
            }
        });

        if (issues.length > 0) {
            console.warn(`[TOC.polish] Dark mode audit: ${issues.length} potential issues`, issues.slice(0, 5));
        } else {
            console.info('[TOC.polish] Dark mode audit: All clear ✓');
        }
    }

    /* ════════════════════════════════════════════
     * S12-T8  Edge Cases: Stale Data Warning
     * ════════════════════════════════════════════ */

    let lastFetchTimestamp = Date.now();
    const STALE_THRESHOLD = 5 * 60 * 1000; // 5 minutes

    function markFresh () {
        lastFetchTimestamp = Date.now();
    }

    function checkStale () {
        if (Date.now() - lastFetchTimestamp > STALE_THRESHOLD) {
            showStaleWarning();
        }
    }

    function showStaleWarning () {
        const existing = document.getElementById('stale-warning');
        if (existing) return;

        const bar = document.createElement('div');
        bar.id = 'stale-warning';
        bar.className = 'fixed top-0 left-0 right-0 z-[300] bg-dc-warning/90 text-dc-bg text-center py-2 text-xs font-bold';
        bar.innerHTML = `
            Data may be stale. <button onclick="location.reload()" class="underline ml-2">Refresh now</button>
            <button onclick="this.parentElement.remove()" class="ml-4 opacity-70 hover:opacity-100">✕</button>
        `;
        document.body.prepend(bar);
    }

    // Check every 60 seconds
    setInterval(checkStale, 60000);

    /* ════════════════════════════════════════════
     * S12-T9  Stress / Pagination Guards
     * ════════════════════════════════════════════ */

    const MAX_DOM_ROWS = 500;

    function guardedRender (items, renderFn) {
        if (items.length > MAX_DOM_ROWS) {
            console.warn(`[TOC.polish] Large dataset (${items.length} rows), limiting to ${MAX_DOM_ROWS}`);
            return renderFn(items.slice(0, MAX_DOM_ROWS));
        }
        return renderFn(items);
    }

    /* ════════════════════════════════════════════
     * Helpers
     * ════════════════════════════════════════════ */
    function esc (s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

    /* ════════════════════════════════════════════
     * Init
     * ════════════════════════════════════════════ */
    function init () {
        initAccessibility();
        initResponsive();

        // Lazy tab switch hook
        const origSwitchTab = NS.switchTab;
        if (origSwitchTab) {
            NS.switchTab = function (tabName) {
                origSwitchTab(tabName);
                onTabSwitch(tabName);
            };
        }

        // Schedule dark mode audit in dev
        if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
            setTimeout(auditDarkMode, 3000);
        }
    }

    /* ── Public API ── */
    NS.polish = {
        init,
        showSkeleton,
        showLoadingSpinner,
        withErrorBoundary,
        showEmptyState,
        debounce,
        setupVirtualScroll,
        guardedRender,
        markFresh,
        checkStale,
        registerLazyTab,
        onTabSwitch,
        EMPTY_MESSAGES,
    };

})();
