/*
 * TOC Sync Health Aggregator
 * Builds a single cross-tab health snapshot from existing sync status labels
 * and error banners so operators can spot issues instantly.
 */
;(function () {
  'use strict';

  const $ = (sel) => document.querySelector(sel);
  let lastIssuePrefixes = [];

  function syncNodes() {
    return Array.from(document.querySelectorAll('[id$="-sync-status"]'));
  }

  function moduleNameFromId(id) {
    if (!id) return 'Unknown';
    const base = id.replace(/-sync-status$/, '');
    return base
      .split('-')
      .map((p) => p ? (p[0].toUpperCase() + p.slice(1)) : p)
      .join(' ');
  }

  function classifySync(node) {
    if (!node) return 'unknown';
    const text = (node.textContent || '').toLowerCase();
    const cls = node.className || '';

    if (cls.includes('text-dc-danger') || text.includes('failed') || text.includes('error')) return 'error';
    if (cls.includes('text-dc-warning') || text.includes('syncing') || text.includes('not synced')) return 'syncing';
    return 'ok';
  }

  function moduleHasBannerError(prefix) {
    if (!prefix) return false;
    const banner = document.getElementById(prefix + '-error-banner');
    return !!(banner && !banner.classList.contains('hidden'));
  }

  function getCurrentTabId() {
    return (window.location.hash || '').replace('#', '') || 'overview';
  }

  function invokeModuleRefresh(prefix, force) {
    const toc = window.TOC || {};
    const moduleApi = toc[prefix];

    // Handle module-specific API naming differences.
    if (prefix === 'overview' && moduleApi && typeof moduleApi.load === 'function') {
      return moduleApi.load();
    }
    if (prefix === 'settings' && moduleApi && typeof moduleApi.init === 'function') {
      return moduleApi.init({ force: !!force });
    }
    if (moduleApi && typeof moduleApi.refresh === 'function') {
      return moduleApi.refresh({ force: !!force });
    }
    return null;
  }

  function showToast(msg, type) {
    if (window.TOC && typeof window.TOC.toast === 'function') {
      window.TOC.toast(msg, type || 'info');
    }
  }

  async function refreshVisibleModule() {
    const current = getCurrentTabId();
    const op = invokeModuleRefresh(current, true);
    if (!op) {
      showToast('No refresh action for this tab', 'warning');
      return;
    }
    try {
      await Promise.resolve(op);
      showToast('Visible tab refreshed', 'success');
    } catch (err) {
      showToast('Refresh failed', 'error');
    }
  }

  async function refreshAllModules() {
    const modules = syncNodes()
      .map((n) => (n.id || '').replace(/-sync-status$/, ''))
      .filter(Boolean);

    const unique = Array.from(new Set(modules));
    const ops = unique.map((prefix) => {
      try {
        const call = invokeModuleRefresh(prefix, true);
        return call ? Promise.resolve(call) : Promise.resolve();
      } catch (_) {
        return Promise.resolve();
      }
    });

    await Promise.allSettled(ops);
    showToast('All modules refresh requested', 'success');
    updateHealthSummary();
  }

  function jumpToFirstIssue() {
    if (!lastIssuePrefixes.length) {
      showToast('No module issues detected', 'success');
      return;
    }
    const first = lastIssuePrefixes[0];
    if (window.TOC && typeof window.TOC.navigate === 'function') {
      window.TOC.navigate(first);
    } else {
      window.location.hash = '#' + first;
    }
    showToast('Navigated to first issue', 'warning');
  }

  function hydrateA11y() {
    syncNodes().forEach((node) => {
      if (!node.hasAttribute('role')) node.setAttribute('role', 'status');
      if (!node.hasAttribute('aria-live')) node.setAttribute('aria-live', 'polite');
    });
  }

  function bindActionButtons() {
    const btnVisible = $('#toc-health-refresh-visible');
    const btnAll = $('#toc-health-refresh-all');
    const btnJump = $('#toc-health-jump-issue');

    if (btnVisible) btnVisible.addEventListener('click', refreshVisibleModule);
    if (btnAll) btnAll.addEventListener('click', refreshAllModules);
    if (btnJump) btnJump.addEventListener('click', jumpToFirstIssue);
  }

  function updateHealthSummary() {
    const nodes = syncNodes();
    const total = nodes.length;
    let ok = 0;
    let syncing = 0;
    let error = 0;
    const issueNames = [];
    const issuePrefixes = [];

    nodes.forEach((node) => {
      const id = node.id || '';
      const prefix = id.replace(/-sync-status$/, '');
      const state = classifySync(node);
      const hasBanner = moduleHasBannerError(prefix);
      const name = moduleNameFromId(id);

      if (hasBanner || state === 'error') {
        error += 1;
        issueNames.push(name);
        issuePrefixes.push(prefix);
        return;
      }

      if (state === 'syncing') {
        syncing += 1;
        return;
      }

      ok += 1;
    });

    const totalEl = $('#toc-health-total');
    const okEl = $('#toc-health-ok');
    const warnEl = $('#toc-health-warn');
    const errEl = $('#toc-health-error');
    const lastEl = $('#toc-health-last');
    const issuesEl = $('#toc-health-issues');
    const summaryEl = $('#toc-health-summary');

    lastIssuePrefixes = issuePrefixes;

    if (totalEl) totalEl.textContent = String(total);
    if (okEl) okEl.textContent = String(ok);
    if (warnEl) warnEl.textContent = String(syncing);
    if (errEl) errEl.textContent = String(error);
    if (lastEl) {
      const now = new Date();
      lastEl.textContent = 'Updated ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    if (issuesEl) {
      if (issueNames.length > 0) {
        issuesEl.textContent = 'Needs attention: ' + issueNames.join(', ');
        issuesEl.className = 'text-[11px] text-dc-danger truncate';
      } else if (syncing > 0) {
        issuesEl.textContent = 'Background sync in progress...';
        issuesEl.className = 'text-[11px] text-dc-warning truncate';
      } else {
        issuesEl.textContent = 'All monitored modules are healthy.';
        issuesEl.className = 'text-[11px] text-dc-success truncate';
      }
    }

    if (summaryEl) {
      summaryEl.dataset.healthState = error > 0 ? 'error' : (syncing > 0 ? 'syncing' : 'ok');
    }
  }

  function bindObservers() {
    const root = document.body;
    if (!root || typeof MutationObserver === 'undefined') return;

    const observer = new MutationObserver((mutations) => {
      let shouldUpdate = false;
      for (let i = 0; i < mutations.length; i += 1) {
        const m = mutations[i];
        const target = m.target;
        if (!(target instanceof HTMLElement)) continue;

        const id = target.id || '';
        if (id.endsWith('-sync-status') || id.endsWith('-error-banner')) {
          shouldUpdate = true;
          break;
        }
      }

      if (shouldUpdate) updateHealthSummary();
    });

    observer.observe(root, {
      subtree: true,
      attributes: true,
      childList: true,
      characterData: true,
      attributeFilter: ['class'],
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    hydrateA11y();
    bindActionButtons();
    updateHealthSummary();
    bindObservers();

    document.addEventListener('toc:tab-changed', function () {
      updateHealthSummary();
    });
  });
})();
