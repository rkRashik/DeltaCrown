/**
 * TOC Brackets Module — Sprint 5
 * Bracket generation, seeding, group stages, qualifier pipelines.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);

  const stateColors = {
    scheduled: 'border-dc-border text-dc-text',
    live: 'border-dc-success text-dc-success',
    completed: 'border-dc-info text-dc-info',
    pending_result: 'border-dc-warning text-dc-warning',
    disputed: 'border-dc-danger text-dc-danger',
    forfeit: 'border-dc-text text-dc-text',
    cancelled: 'border-dc-danger/50 text-dc-danger/50',
  };

  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }

  /* ─── Bracket state ──────────────────────────────────────── */
  let bracketData = null;

  async function refresh() {
    try {
      const data = await API.get('brackets/');
      bracketData = data;
      renderBracket(data);
      refreshGroups();
      refreshPipelines();
    } catch (e) {
      console.error('[brackets] fetch error', e);
    }
  }

  function renderBracket(data) {
    const infoBar = $('#bracket-info-bar');
    const tree = $('#bracket-tree');
    const seedEditor = $('#seeding-editor');
    if (!tree) return;

    if (!data.exists || !data.bracket) {
      if (infoBar) infoBar.classList.add('hidden');
      if (seedEditor) seedEditor.classList.add('hidden');
      tree.innerHTML = `
        <div class="flex items-center justify-center h-60 text-dc-text text-sm">
          <div class="text-center">
            <i data-lucide="git-branch" class="w-12 h-12 text-dc-text/20 mx-auto mb-3"></i>
            <p>No bracket generated yet</p>
            <p class="text-[10px] mt-1 text-dc-text/60">Click "Generate" to create the bracket</p>
          </div>
        </div>`;
      if (typeof lucide !== 'undefined') lucide.createIcons();
      return;
    }

    const b = data.bracket;
    if (infoBar) {
      infoBar.classList.remove('hidden');
      $('#bracket-format').textContent = (b.format || '').replace(/_/g, ' ');
      $('#bracket-rounds').textContent = b.total_rounds || '—';
      $('#bracket-matches').textContent = b.total_matches || '—';
      $('#bracket-seeding').textContent = (b.seeding_method || '').replace(/_/g, ' ');
      const statusEl = $('#bracket-status');
      if (statusEl) {
        statusEl.textContent = b.is_finalized ? 'Published' : 'Draft';
        statusEl.className = b.is_finalized
          ? 'font-bold text-dc-success'
          : 'font-bold text-dc-warning';
      }
    }

    // Render nodes by round
    const nodes = data.nodes || [];
    if (!nodes.length) {
      tree.innerHTML = '<p class="text-dc-text text-center py-8">Bracket generated but no nodes found.</p>';
      return;
    }

    // Check for double elimination (losers bracket nodes exist)
    const hasLosers = nodes.some(n => n.bracket_type === 'losers');

    if (hasLosers) {
      const winnersNodes = nodes.filter(n => n.bracket_type !== 'losers');
      const losersNodes = nodes.filter(n => n.bracket_type === 'losers');

      tree.innerHTML = `
        <div class="space-y-6">
          <div>
            <div class="flex items-center gap-2 mb-3 px-2">
              <div class="w-3 h-3 rounded-full bg-dc-success"></div>
              <h3 class="text-sm font-bold text-white uppercase tracking-widest">Winners Bracket</h3>
            </div>
            ${buildBracketGrid(winnersNodes, 'winners')}
          </div>
          <div class="border-t border-dc-border/30 pt-6">
            <div class="flex items-center gap-2 mb-3 px-2">
              <div class="w-3 h-3 rounded-full bg-dc-danger"></div>
              <h3 class="text-sm font-bold text-white uppercase tracking-widest">Losers Bracket</h3>
            </div>
            ${buildBracketGrid(losersNodes, 'losers')}
          </div>
        </div>`;

      requestAnimationFrame(() => {
        drawBracketConnectors('bracket-grid-winners');
        drawBracketConnectors('bracket-grid-losers');
      });
    } else {
      // Single elimination or round robin
      tree.innerHTML = buildBracketGrid(nodes, 'main');
      requestAnimationFrame(() => drawBracketConnectors('bracket-grid-main'));
    }

    // Show seeding editor if not finalized
    if (seedEditor && !b.is_finalized && nodes.length) {
      seedEditor.classList.remove('hidden');
      renderSeedList(nodes);
    } else if (seedEditor) {
      seedEditor.classList.add('hidden');
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function buildBracketGrid(nodes, gridId) {
    const rounds = {};
    nodes.forEach(n => {
      const rn = n.round_number || 0;
      if (!rounds[rn]) rounds[rn] = [];
      rounds[rn].push(n);
    });

    const sortedRounds = Object.keys(rounds).sort((a, b) => a - b);
    const totalRounds = sortedRounds.length;

    sortedRounds.forEach(rn => {
      rounds[rn].sort((a, b) => (a.match_number_in_round || a.position || 0) - (b.match_number_in_round || b.position || 0));
    });

    return `
      <div class="bracket-tree-wrap flex gap-0 min-w-max py-4 px-2" id="bracket-grid-${gridId}">
        ${sortedRounds.map((rn, idx) => {
          const roundNodes = rounds[rn];
          const roundLabel = idx === totalRounds - 1 && totalRounds > 1 ? 'Final'
            : idx === totalRounds - 2 && totalRounds > 2 ? 'Semi-Finals'
            : `Round ${parseInt(rn)}`;
          return `
            <div class="bracket-round" data-round="${rn}">
              <div class="text-[9px] font-bold text-dc-text uppercase tracking-widest text-center mb-3 pb-2 border-b border-dc-border mx-2">${roundLabel}</div>
              ${roundNodes.map((n, mi) => renderMatchCard(n, idx, mi)).join('')}
            </div>`;
        }).join('')}
      </div>`;
  }

  function renderMatchCard(node, roundIdx, matchIdx) {
    const m = node.match;
    const state = m?.state || 'scheduled';
    const sc = stateColors[state] || stateColors.scheduled;
    const hasWinner = !!node.winner_id;
    const p1Win = node.winner_id && node.winner_id === node.participant1_id;
    const p2Win = node.winner_id && node.winner_id === node.participant2_id;
    const isBye = node.is_bye;
    const nodeId = node.id || `${roundIdx}-${matchIdx}`;

    return `
      <div class="bracket-match-card bg-dc-bg border ${sc} rounded-lg overflow-hidden hover:border-dc-borderLight mx-2 my-1 ${isBye ? 'bracket-bye-card' : ''}"
           data-node-id="${nodeId}" data-round="${roundIdx}" data-match="${matchIdx}"
           onclick="TOC.brackets.onMatchCardClick && TOC.brackets.onMatchCardClick(${JSON.stringify(node).replace(/"/g, '&quot;')})">
        <div class="flex items-center justify-between px-3 py-2 border-b border-dc-border/50 ${p1Win ? 'bg-dc-success/5' : ''}">
          <span class="text-xs ${p1Win ? 'text-dc-success font-bold' : 'text-dc-textBright'} truncate max-w-[140px]">${node.participant1_name || (isBye ? 'BYE' : 'TBD')}</span>
          <span class="text-xs font-mono font-bold ${p1Win ? 'text-dc-success' : 'text-dc-text'}">${m?.participant1_score ?? '—'}</span>
        </div>
        <div class="flex items-center justify-between px-3 py-2 ${p2Win ? 'bg-dc-success/5' : ''}">
          <span class="text-xs ${p2Win ? 'text-dc-success font-bold' : 'text-dc-textBright'} truncate max-w-[140px]">${node.participant2_name || 'TBD'}</span>
          <span class="text-xs font-mono font-bold ${p2Win ? 'text-dc-success' : 'text-dc-text'}">${m?.participant2_score ?? '—'}</span>
        </div>
      </div>`;
  }

  /* ─── SVG bracket connector lines ────────────────────────── */
  function drawBracketConnectors(gridId) {
    const grid = document.getElementById(gridId);
    if (!grid) return;

    // Remove old SVG if present
    const oldSvg = grid.querySelector('svg.bracket-connectors');
    if (oldSvg) oldSvg.remove();

    const roundCols = grid.querySelectorAll('.bracket-round');
    if (roundCols.length < 2) return;

    const gridRect = grid.getBoundingClientRect();
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('bracket-connectors');
    svg.setAttribute('width', gridRect.width);
    svg.setAttribute('height', gridRect.height);
    svg.style.width = gridRect.width + 'px';
    svg.style.height = gridRect.height + 'px';

    // For each consecutive pair of rounds, draw connectors
    for (let ri = 0; ri < roundCols.length - 1; ri++) {
      const curCards = roundCols[ri].querySelectorAll('.bracket-match-card');
      const nextCards = roundCols[ri + 1].querySelectorAll('.bracket-match-card');

      // Each pair of matches in current round feeds into one match in next round
      for (let ni = 0; ni < nextCards.length; ni++) {
        const topIdx = ni * 2;
        const botIdx = ni * 2 + 1;
        const topCard = curCards[topIdx];
        const botCard = curCards[botIdx];
        const destCard = nextCards[ni];

        if (!destCard) continue;

        const destRect = destCard.getBoundingClientRect();
        const destY = destRect.top + destRect.height / 2 - gridRect.top;
        const destX = destRect.left - gridRect.left;

        if (topCard) {
          const topRect = topCard.getBoundingClientRect();
          const topY = topRect.top + topRect.height / 2 - gridRect.top;
          const topX = topRect.right - gridRect.left;
          drawConnector(svg, topX, topY, destX, destY);
        }
        if (botCard) {
          const botRect = botCard.getBoundingClientRect();
          const botY = botRect.top + botRect.height / 2 - gridRect.top;
          const botX = botRect.right - gridRect.left;
          drawConnector(svg, botX, botY, destX, destY);
        }
      }
    }

    grid.prepend(svg);
  }

  function drawConnector(svg, x1, y1, x2, y2) {
    const midX = x1 + (x2 - x1) / 2;
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    // Right-angle stepped connector: horizontal → vertical → horizontal
    path.setAttribute('d', `M ${x1} ${y1} H ${midX} V ${y2} H ${x2}`);
    svg.appendChild(path);
  }

  /* ─── Seeding editor (S5-F2) ─────────────────────────────── */
  function renderSeedList(nodes) {
    const container = $('#seed-list');
    if (!container) return;

    // Get unique participants from round 1
    const round1 = nodes.filter(n => n.round_number === 1 || n.round_number === nodes.reduce((min, n) => Math.min(min, n.round_number), 999));
    const participants = [];
    const seen = new Set();
    round1.forEach(n => {
      if (n.participant1_id && !seen.has(n.participant1_id)) {
        seen.add(n.participant1_id);
        participants.push({ id: n.participant1_id, name: n.participant1_name });
      }
      if (n.participant2_id && !seen.has(n.participant2_id)) {
        seen.add(n.participant2_id);
        participants.push({ id: n.participant2_id, name: n.participant2_name });
      }
    });

    container.innerHTML = participants.map((p, i) => `
      <div class="flex items-center gap-3 bg-dc-bg border border-dc-border rounded-lg px-3 py-2 hover:border-dc-borderLight transition-colors cursor-move" data-reg-id="${p.id}" draggable="true">
        <span class="w-6 h-6 rounded bg-dc-panel border border-dc-border flex items-center justify-center text-[10px] font-mono font-bold text-theme">${i + 1}</span>
        <span class="text-xs text-dc-textBright font-semibold flex-1">${p.name || 'Unknown'}</span>
        <i data-lucide="grip-vertical" class="w-3 h-3 text-dc-text/30"></i>
      </div>
    `).join('');

    // Simple drag-and-drop
    let dragEl = null;
    container.querySelectorAll('[draggable]').forEach(el => {
      el.addEventListener('dragstart', e => { dragEl = el; el.classList.add('opacity-50'); });
      el.addEventListener('dragend', () => { if (dragEl) dragEl.classList.remove('opacity-50'); dragEl = null; });
      el.addEventListener('dragover', e => e.preventDefault());
      el.addEventListener('drop', e => {
        e.preventDefault();
        if (dragEl && dragEl !== el) {
          const parent = el.parentNode;
          const children = [...parent.children];
          const fromIdx = children.indexOf(dragEl);
          const toIdx = children.indexOf(el);
          if (fromIdx < toIdx) el.after(dragEl);
          else el.before(dragEl);
          // Re-number seeds
          parent.querySelectorAll('[data-reg-id]').forEach((row, i) => {
            const badge = row.querySelector('span');
            if (badge) badge.textContent = i + 1;
          });
        }
      });
    });

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  async function saveSeedOrder() {
    const list = $('#seed-list');
    if (!list) return;
    const seeds = [...list.querySelectorAll('[data-reg-id]')].map((el, i) => ({
      registration_id: parseInt(el.dataset.regId),
      seed: i + 1,
    }));
    try {
      await API.put('brackets/seeds/', { seeds });
      toast('Seed order saved', 'success');
      refresh();
    } catch (e) {
      toast(e.message || 'Failed to save seeds', 'error');
    }
  }

  /* ─── Bracket actions (S5-F3) ────────────────────────────── */
  async function generate() {
    if (!confirm('Generate bracket from current registrations?')) return;
    try {
      await API.post('brackets/generate/');
      toast('Bracket generated', 'success');
      refresh();
    } catch (e) {
      toast(e.message || 'Generation failed', 'error');
    }
  }

  async function resetBracket() {
    if (!confirm('RESET bracket? This deletes the current bracket and all matches. This cannot be undone.')) return;
    try {
      await API.post('brackets/reset/');
      toast('Bracket reset', 'info');
      refresh();
    } catch (e) {
      toast(e.message || 'Reset failed', 'error');
    }
  }

  async function publish() {
    if (!confirm('Publish bracket? Participants will be able to see it.')) return;
    try {
      await API.post('brackets/publish/');
      toast('Bracket published', 'success');
      refresh();
    } catch (e) {
      toast(e.message || 'Publish failed', 'error');
    }
  }

  /* ─── Group stage (S5-F4) ────────────────────────────────── */
  async function refreshGroups() {
    try {
      const data = await API.get('groups/');
      renderGroups(data);
    } catch (e) {
      console.error('[brackets] groups error', e);
    }
  }

  function renderGroups(data) {
    const container = $('#groups-panel');
    if (!container) return;

    if (!data.exists || !data.groups?.length) {
      container.innerHTML = '<div class="flex items-center justify-center h-32 text-dc-text text-sm">No group stage configured</div>';
      return;
    }

    container.innerHTML = data.groups.map(g => `
      <div class="bg-dc-bg border border-dc-border rounded-xl p-3 mb-3">
        <div class="flex items-center justify-between mb-2">
          <h4 class="text-xs font-bold text-white">${g.name}</h4>
          <span class="text-[9px] font-mono text-dc-text">${g.standings?.length || 0} teams</span>
        </div>
        ${g.standings?.length ? `
          <table class="w-full text-[10px]">
            <thead><tr class="text-dc-text border-b border-dc-border/50">
              <th class="text-left py-1 px-1">#</th>
              <th class="text-left py-1 px-1">Team</th>
              <th class="text-center py-1 px-1">W</th>
              <th class="text-center py-1 px-1">D</th>
              <th class="text-center py-1 px-1">L</th>
              <th class="text-center py-1 px-1">Pts</th>
            </tr></thead>
            <tbody>${g.standings.map(s => `
              <tr class="border-b border-dc-border/30 ${s.is_advancing ? 'bg-dc-success/5' : ''} ${s.is_eliminated ? 'opacity-50' : ''}">
                <td class="py-1 px-1 font-mono font-bold text-dc-text">${s.rank || '—'}</td>
                <td class="py-1 px-1 text-dc-textBright font-semibold">${s.team_name || s.user_id || '—'}</td>
                <td class="py-1 px-1 text-center text-dc-success font-mono">${s.wins}</td>
                <td class="py-1 px-1 text-center text-dc-text font-mono">${s.draws}</td>
                <td class="py-1 px-1 text-center text-dc-danger font-mono">${s.losses}</td>
                <td class="py-1 px-1 text-center text-white font-mono font-bold">${s.points}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        ` : '<p class="text-dc-text/60 text-[10px]">No standings yet</p>'}
      </div>
    `).join('');
  }

  function openGroupConfig() {
    const html = `
      <div class="p-6 space-y-4">
        <h3 class="font-display font-black text-lg text-white">Configure Groups</h3>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Groups</label>
            <input id="gc-num-groups" type="number" value="4" min="2" max="32" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Group Size</label>
            <input id="gc-group-size" type="number" value="4" min="2" max="16" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Format</label>
            <select id="gc-format" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
              <option value="round_robin">Round Robin</option>
              <option value="double_round_robin">Double RR</option>
            </select>
          </div>
          <div>
            <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Advance Per Group</label>
            <input id="gc-advance" type="number" value="2" min="1" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none">
          </div>
        </div>
        <button onclick="TOC.brackets.confirmGroupConfig()" class="w-full py-2.5 bg-theme text-dc-bg text-xs font-black uppercase tracking-widest rounded-lg hover:opacity-90 transition-opacity">Save Configuration</button>
      </div>`;
    showOverlay('group-config-overlay', html);
  }

  async function confirmGroupConfig() {
    try {
      await API.post('groups/configure/', {
        num_groups: parseInt($('#gc-num-groups')?.value) || 4,
        group_size: parseInt($('#gc-group-size')?.value) || 4,
        format: $('#gc-format')?.value || 'round_robin',
        advancement_count: parseInt($('#gc-advance')?.value) || 2,
      });
      toast('Groups configured', 'success');
      closeOverlay('group-config-overlay');
      refreshGroups();
    } catch (e) {
      toast(e.message || 'Config failed', 'error');
    }
  }

  async function drawGroups() {
    if (!confirm('Execute group draw?')) return;
    try {
      await API.post('groups/draw/', { method: 'random' });
      toast('Groups drawn', 'success');
      refreshGroups();
    } catch (e) {
      toast(e.message || 'Draw failed', 'error');
    }
  }

  /* ─── Pipelines ──────────────────────────────────────────── */
  async function refreshPipelines() {
    try {
      const data = await API.get('pipelines/');
      renderPipelines(data);
    } catch (e) {
      console.error('[brackets] pipelines error', e);
    }
  }

  function renderPipelines(list) {
    const container = $('#pipelines-panel');
    if (!container) return;

    if (!list?.length) {
      container.innerHTML = '<div class="flex items-center justify-center h-32 text-dc-text text-sm">No pipelines configured</div>';
      return;
    }

    container.innerHTML = list.map(p => `
      <div class="bg-dc-bg border border-dc-border rounded-xl p-4 hover:border-dc-borderLight transition-colors group">
        <div class="flex items-start justify-between mb-2">
          <div>
            <h4 class="text-sm font-bold text-white">${p.name}</h4>
            <span class="text-[9px] font-bold uppercase text-dc-text">${p.status}</span>
          </div>
          <button onclick="TOC.brackets.deletePipeline('${p.id}')" class="opacity-0 group-hover:opacity-100 transition-opacity w-6 h-6 rounded bg-dc-danger/10 text-dc-danger flex items-center justify-center hover:bg-dc-danger/20"><i data-lucide="trash-2" class="w-3 h-3"></i></button>
        </div>
        ${p.description ? `<p class="text-[10px] text-dc-text mb-2">${p.description}</p>` : ''}
        <div class="flex items-center gap-1 flex-wrap">
          ${p.stages.map((s, i) => `
            <span class="text-[9px] bg-dc-panel border border-dc-border rounded px-2 py-0.5 text-dc-textBright">${s.name}</span>
            ${i < p.stages.length - 1 ? '<i data-lucide="arrow-right" class="w-3 h-3 text-dc-text/30"></i>' : ''}
          `).join('')}
        </div>
      </div>
    `).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function openCreatePipeline() {
    const html = `
      <div class="p-6 space-y-4">
        <h3 class="font-display font-black text-lg text-white">New Pipeline</h3>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Name</label>
          <input id="pl-name" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none" placeholder="e.g. Open Qualifier">
        </div>
        <div>
          <label class="text-[9px] font-bold text-dc-text uppercase tracking-widest block mb-1">Description</label>
          <textarea id="pl-desc" rows="2" class="w-full bg-dc-bg border border-dc-border rounded-lg px-3 py-2 text-white text-xs focus:border-theme outline-none resize-none" placeholder="Optional description..."></textarea>
        </div>
        <button onclick="TOC.brackets.confirmCreatePipeline()" class="w-full py-2.5 bg-purple-600 text-white text-xs font-black uppercase tracking-widest rounded-lg hover:bg-purple-500 transition-colors">Create Pipeline</button>
      </div>`;
    showOverlay('pipeline-create-overlay', html);
  }

  async function confirmCreatePipeline() {
    const name = $('#pl-name')?.value?.trim();
    if (!name) { toast('Name required', 'error'); return; }
    try {
      await API.post('pipelines/', {
        name,
        description: $('#pl-desc')?.value?.trim() || '',
      });
      toast('Pipeline created', 'success');
      closeOverlay('pipeline-create-overlay');
      refreshPipelines();
    } catch (e) {
      toast(e.message || 'Create failed', 'error');
    }
  }

  async function deletePipeline(id) {
    if (!confirm('Delete this pipeline?')) return;
    try {
      await API.delete(`pipelines/${id}/`);
      toast('Pipeline deleted', 'success');
      refreshPipelines();
    } catch (e) {
      toast(e.message || 'Delete failed', 'error');
    }
  }

  /* ─── Overlay helpers ────────────────────────────────────── */
  function showOverlay(id, innerHtml) {
    const existing = document.getElementById(id);
    if (existing) existing.remove();
    const modal = document.createElement('div');
    modal.id = id;
    modal.className = 'fixed inset-0 z-[110] flex items-center justify-center';
    modal.innerHTML = `
      <div class="absolute inset-0 bg-black/80 backdrop-blur-md" onclick="TOC.brackets.closeOverlay('${id}')"></div>
      <div class="bg-dc-surface border border-dc-borderLight shadow-[0_20px_60px_rgba(0,0,0,0.8)] rounded-xl w-full max-w-md relative z-10 overflow-hidden">
        <div class="h-1 w-full bg-theme"></div>
        ${innerHtml}
      </div>`;
    document.body.appendChild(modal);
  }

  function closeOverlay(id) {
    document.getElementById(id)?.remove();
  }

  /* ─── Match card interaction ───────────────────────────────── */
  function onMatchCardClick(node) {
    if (!node || node.is_bye) return;
    const m = node.match;
    const state = m?.state || 'scheduled';
    const p1Name = node.participant1_name || 'TBD';
    const p2Name = node.participant2_name || 'TBD';
    
    const html = `
      <div class="p-6 space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="font-display font-black text-lg text-white">Match Details</h3>
          <span class="text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${stateColors[state] || 'border-dc-border text-dc-text'}">${state}</span>
        </div>
        
        <div class="bg-dc-bg rounded-xl border border-dc-border p-4">
          <div class="flex items-center justify-between mb-3">
            <div class="flex-1 text-center">
              <p class="text-sm font-bold ${node.winner_id === node.participant1_id ? 'text-dc-success' : 'text-white'}">${p1Name}</p>
              <p class="text-2xl font-mono font-black mt-1 ${node.winner_id === node.participant1_id ? 'text-dc-success' : 'text-dc-text'}">${m?.participant1_score ?? '—'}</p>
            </div>
            <div class="mx-4 text-dc-text/30 font-bold text-lg">VS</div>
            <div class="flex-1 text-center">
              <p class="text-sm font-bold ${node.winner_id === node.participant2_id ? 'text-dc-success' : 'text-white'}">${p2Name}</p>
              <p class="text-2xl font-mono font-black mt-1 ${node.winner_id === node.participant2_id ? 'text-dc-success' : 'text-dc-text'}">${m?.participant2_score ?? '—'}</p>
            </div>
          </div>
        </div>
        
        <div class="grid grid-cols-2 gap-2 text-[10px]">
          <div class="bg-dc-bg rounded-lg p-2 border border-dc-border/50">
            <span class="text-dc-text">Round</span>
            <p class="text-white font-mono font-bold">${node.round_number || '—'}</p>
          </div>
          <div class="bg-dc-bg rounded-lg p-2 border border-dc-border/50">
            <span class="text-dc-text">Match</span>
            <p class="text-white font-mono font-bold">#${node.match_number_in_round || node.position || '—'}</p>
          </div>
          ${m?.scheduled_time ? `
          <div class="bg-dc-bg rounded-lg p-2 border border-dc-border/50 col-span-2">
            <span class="text-dc-text">Scheduled</span>
            <p class="text-white font-mono font-bold">${new Date(m.scheduled_time).toLocaleString()}</p>
          </div>` : ''}
        </div>

        ${m && state !== 'completed' && state !== 'forfeit' ? `
        <div class="flex gap-2">
          ${state === 'scheduled' ? `<button onclick="TOC.matches?.markLive && TOC.matches.markLive(${m.id})" class="flex-1 py-2 bg-dc-success/20 text-dc-success text-xs font-bold rounded-lg hover:bg-dc-success/30 transition-colors">Start Match</button>` : ''}
          ${state === 'live' ? `<button onclick="TOC.matches?.openScoreDrawer && TOC.matches.openScoreDrawer(${m.id}, '${p1Name}', '${p2Name}')" class="flex-1 py-2 bg-theme/20 text-theme text-xs font-bold rounded-lg hover:bg-theme/30 transition-colors">Enter Score</button>` : ''}
        </div>` : ''}
      </div>`;
    showOverlay('bracket-match-detail', html);
  }

  /* ─── Init ───────────────────────────────────────────────── */
  function init() { refresh(); }

  window.TOC = window.TOC || {};
  window.TOC.brackets = {
    init, refresh, generate, resetBracket, publish,
    saveSeedOrder, refreshGroups, openGroupConfig, confirmGroupConfig,
    drawGroups, refreshPipelines, openCreatePipeline, confirmCreatePipeline,
    deletePipeline, closeOverlay, onMatchCardClick,
  };

  document.addEventListener('toc:tab-changed', function (e) {
    if (e.detail?.tab === 'brackets') init();
  });
})();
