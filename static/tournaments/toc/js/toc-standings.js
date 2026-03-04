/**
 * TOC Standings Module — Sprint 28
 * Standings/leaderboards tab: group standings, qualification tracker,
 * historical snapshots, export.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);

  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }

  let dashboardData = null;

  /* ─── Fetch & render ─────────────────────────────────────── */
  async function refresh() {
    const groupId = $('#standings-group-filter')?.value || '';
    try {
      const data = await API.get(`standings/?group_id=${groupId}`);
      dashboardData = data;
      renderStats(data);
      renderStandings(data);
      renderGroupFilter(data.groups || []);
    } catch (e) {
      console.error('[standings] fetch error', e);
    }
    // Also load qualification
    try {
      const qual = await API.get('standings/qualification/');
      renderQualification(qual);
    } catch (_) {}
  }

  function renderStats(data) {
    const s = data.summary || {};
    const el = (id, v) => { const e = $(`#standings-stat-${id}`); if (e) e.textContent = v; };
    el('groups', s.total_groups || data.groups?.length || 0);
    el('teams', s.total_teams || 0);
    el('matches', s.total_matches || 0);
    el('leader', s.leader || '-');
  }

  function renderGroupFilter(groups) {
    const sel = $('#standings-group-filter');
    if (!sel) return;
    const current = sel.value;
    // Keep All Groups option, replace the rest
    const opts = ['<option value="">All Groups</option>'];
    groups.forEach(g => {
      opts.push(`<option value="${g.group_id}"${g.group_id == current ? ' selected' : ''}>${g.group_name || 'Group ' + g.group_id}</option>`);
    });
    sel.innerHTML = opts.join('');
  }

  function renderStandings(data) {
    const container = $('#standings-content');
    if (!container) return;

    const groups = data.groups || [];
    if (!groups.length) {
      container.innerHTML = `
        <div class="glass-box rounded-xl p-8 text-center">
          <i data-lucide="trophy" class="w-10 h-10 mx-auto mb-3 text-dc-text opacity-20"></i>
          <p class="text-sm text-dc-text">No standings data yet. Generate brackets and play some matches first.</p>
        </div>`;
      refreshIcons();
      return;
    }

    let html = '';
    groups.forEach(g => {
      const standings = g.standings || [];
      html += `
        <div class="glass-box rounded-xl overflow-hidden">
          <div class="p-4 border-b border-dc-border bg-dc-panel/50">
            <h3 class="font-display font-bold text-white text-sm">${esc(g.group_name || 'Group')}</h3>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-dc-border text-dc-text uppercase tracking-widest">
                  <th class="px-4 py-3 text-left">#</th>
                  <th class="px-4 py-3 text-left">Team</th>
                  <th class="px-4 py-3 text-center">W</th>
                  <th class="px-4 py-3 text-center">D</th>
                  <th class="px-4 py-3 text-center">L</th>
                  <th class="px-4 py-3 text-center">Pts</th>
                  <th class="px-4 py-3 text-center">Win%</th>
                  <th class="px-4 py-3 text-center">Form</th>
                </tr>
              </thead>
              <tbody>`;

      standings.forEach((s, idx) => {
        const isQualified = idx < (g.qualify_count || 2);
        const bgCls = isQualified ? 'bg-dc-success/5' : '';
        const rankCls = isQualified ? 'text-dc-success font-bold' : 'text-dc-text';
        const form = (s.form || []).map(f => {
          if (f === 'W') return '<span class="inline-block w-5 h-5 rounded text-[10px] font-bold bg-dc-success/20 text-dc-success flex items-center justify-center">W</span>';
          if (f === 'L') return '<span class="inline-block w-5 h-5 rounded text-[10px] font-bold bg-dc-danger/20 text-dc-danger flex items-center justify-center">L</span>';
          return '<span class="inline-block w-5 h-5 rounded text-[10px] font-bold bg-dc-text/10 text-dc-text flex items-center justify-center">D</span>';
        }).join('');

        html += `
                <tr class="border-b border-dc-border/50 hover:bg-white/[.02] ${bgCls}">
                  <td class="px-4 py-2.5 ${rankCls}">${s.rank || idx + 1}</td>
                  <td class="px-4 py-2.5 text-white font-medium">${esc(s.name)}</td>
                  <td class="px-4 py-2.5 text-center text-dc-success">${s.wins || 0}</td>
                  <td class="px-4 py-2.5 text-center text-dc-text">${s.draws || 0}</td>
                  <td class="px-4 py-2.5 text-center text-dc-danger">${s.losses || 0}</td>
                  <td class="px-4 py-2.5 text-center text-theme font-bold">${s.points || 0}</td>
                  <td class="px-4 py-2.5 text-center">${s.win_rate || '0'}%</td>
                  <td class="px-4 py-2.5"><div class="flex gap-0.5 justify-center">${form}</div></td>
                </tr>`;
      });

      html += `
              </tbody>
            </table>
          </div>
        </div>`;
    });

    container.innerHTML = html;
    refreshIcons();
  }

  function renderQualification(data) {
    const container = $('#standings-qualification');
    if (!container) return;

    const groups = data.groups || [];
    if (!groups.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No qualification data</p>';
      return;
    }

    let html = '<div class="grid grid-cols-1 md:grid-cols-2 gap-3">';
    groups.forEach(g => {
      const qualified = g.qualified || [];
      html += `
        <div class="bg-dc-surface/50 rounded-lg p-3">
          <h4 class="text-xs font-bold text-white mb-2">${esc(g.group_name)}</h4>
          <div class="space-y-1">`;
      qualified.forEach(q => {
        html += `
            <div class="flex items-center justify-between text-xs">
              <span class="text-dc-textBright">${esc(q.name)}</span>
              <span class="text-dc-success text-[10px] font-bold">QUALIFIED</span>
            </div>`;
      });
      html += '</div></div>';
    });
    html += '</div>';
    container.innerHTML = html;
  }

  async function exportStandings() {
    try {
      const data = await API.get('standings/export/');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `standings_${slug}.json`; a.click();
      URL.revokeObjectURL(url);
      toast('Standings exported', 'success');
    } catch (e) {
      toast('Export failed', 'error');
    }
  }

  function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
  function refreshIcons() { if (typeof lucide !== 'undefined') lucide.createIcons(); }

  /* ─── Public API ─────────────────────────────────────────── */
  window.TOC = window.TOC || {};
  window.TOC.standings = { refresh, exportStandings };

  // Auto-load when tab is activated
  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail && e.detail.tab === 'standings') refresh();
  });
})();
