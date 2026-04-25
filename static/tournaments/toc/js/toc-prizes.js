/**
 * TOC — Prizes & Awards tab.
 *
 * Loads /api/toc/<slug>/prizes/ for the editor + public preview,
 * persists via /save/, recomputes placements via /publish/.
 */

;(function () {
  'use strict';

  const CFG = window.TOC_CONFIG || {};
  const API = CFG.apiBase || '';
  const $ = (s, ctx) => (ctx || document).querySelector(s);

  // ── Local editor state ──
  let state = {
    currency: 'BDT',
    fiat_pool: 0,
    coin_pool: 0,
    placements: [],
    special_awards: [],
    certificates_enabled: true,
  };
  let lastPreview = null;

  function ordinal(n) {
    const v = n % 100;
    if (v >= 11 && v <= 13) return `${n}th`;
    const s = { 1: 'st', 2: 'nd', 3: 'rd' };
    return `${n}${s[n % 10] || 'th'}`;
  }

  function formatNum(n) {
    n = Number(n) || 0;
    return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function updatePctTotal() {
    const total = (state.placements || []).reduce(
      (acc, p) => acc + (Number(p.percent) || 0), 0,
    );
    const el = $('#prizes-pct-total');
    if (!el) return;
    el.textContent = `${total}%`;
    el.classList.toggle('text-dc-success', total === 100);
    el.classList.toggle('text-dc-warning', total !== 100 && total !== 0);
  }

  function syncFromPercent(idx) {
    const tier = state.placements[idx];
    if (!tier) return;
    const pct = Number(tier.percent) || 0;
    if (state.fiat_pool > 0) tier.fiat = Math.round(state.fiat_pool * pct / 100);
    if (state.coin_pool > 0) tier.coins = Math.round(state.coin_pool * pct / 100);
    renderTiers();
  }

  function renderTiers() {
    const list = $('#prizes-tier-list');
    if (!list) return;
    list.innerHTML = '';
    (state.placements || []).forEach((tier, idx) => {
      const row = document.createElement('div');
      row.className = 'grid grid-cols-12 gap-2 items-center px-2 py-2 rounded-lg border border-dc-border bg-dc-surface/30';
      row.innerHTML = `
        <div class="col-span-1 font-mono text-xs text-dc-textBright">${ordinal(tier.rank)}</div>
        <div class="col-span-4">
          <input data-prize-tier-title="${idx}" type="text" maxlength="80" value="${escapeAttr(tier.title || '')}"
            class="w-full bg-transparent border-b border-dc-border focus:border-theme/60 px-1 py-0.5 text-xs text-white outline-none">
        </div>
        <div class="col-span-2">
          <input data-prize-tier-pct="${idx}" type="number" min="0" max="100" value="${tier.percent || 0}"
            class="w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-center text-white outline-none focus:border-theme/40">
        </div>
        <div class="col-span-2">
          <input data-prize-tier-fiat="${idx}" type="number" min="0" value="${tier.fiat || 0}"
            class="w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-right text-white outline-none focus:border-theme/40">
        </div>
        <div class="col-span-2">
          <input data-prize-tier-coins="${idx}" type="number" min="0" value="${tier.coins || 0}"
            class="w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-right text-white outline-none focus:border-theme/40">
        </div>
        <div class="col-span-1 text-right">
          <button data-prize-tier-remove="${idx}" class="text-dc-text hover:text-dc-danger transition-colors">
            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      `;
      list.appendChild(row);
    });
    if (window.lucide) window.lucide.createIcons();
    updatePctTotal();
  }

  function renderAwards() {
    const list = $('#prizes-award-list');
    if (!list) return;
    list.innerHTML = '';
    const empty = $('#prizes-award-empty');
    if (empty) empty.classList.toggle('hidden', (state.special_awards || []).length > 0);
    (state.special_awards || []).forEach((a, idx) => {
      const card = document.createElement('div');
      card.className = 'rounded-lg border border-dc-border bg-dc-surface/30 p-3 space-y-2';
      card.innerHTML = `
        <div class="flex items-start gap-2">
          <input data-prize-award-title="${idx}" type="text" maxlength="120" value="${escapeAttr(a.title || '')}"
            class="flex-1 bg-transparent border-b border-dc-border focus:border-theme/60 px-1 py-0.5 text-sm text-white outline-none" placeholder="Award title">
          <button data-prize-award-remove="${idx}" class="text-dc-text hover:text-dc-danger transition-colors px-1">
            <i data-lucide="x" class="w-3.5 h-3.5"></i>
          </button>
        </div>
        <input data-prize-award-desc="${idx}" type="text" maxlength="240" value="${escapeAttr(a.description || '')}"
          class="w-full bg-transparent border-b border-dc-border focus:border-theme/60 px-1 py-0.5 text-xs text-dc-textBright outline-none" placeholder="Criteria / description">
        <div class="grid grid-cols-2 gap-2">
          <label class="text-[10px] text-dc-text">Type
            <select data-prize-award-type="${idx}" class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-white outline-none">
              <option value="cash" ${a.type === 'cash' ? 'selected' : ''}>Cash</option>
              <option value="hardware" ${a.type === 'hardware' ? 'selected' : ''}>Hardware</option>
              <option value="digital" ${a.type === 'digital' ? 'selected' : ''}>Digital code</option>
            </select>
          </label>
          <label class="text-[10px] text-dc-text">Icon
            <input data-prize-award-icon="${idx}" type="text" maxlength="40" value="${escapeAttr(a.icon || 'medal')}"
              class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-white outline-none" placeholder="medal">
          </label>
          <label class="text-[10px] text-dc-text">Fiat
            <input data-prize-award-fiat="${idx}" type="number" min="0" value="${a.fiat || 0}"
              class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-right text-white outline-none">
          </label>
          <label class="text-[10px] text-dc-text">Coins
            <input data-prize-award-coins="${idx}" type="number" min="0" value="${a.coins || 0}"
              class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-right text-white outline-none">
          </label>
        </div>
        <input data-prize-award-text="${idx}" type="text" maxlength="240" value="${escapeAttr(a.reward_text || '')}"
          class="w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-white outline-none" placeholder="Reward detail (e.g. 'Logitech G Pro X')">
        <label class="text-[10px] text-dc-text block mt-1">Recipient (name or team — optional)
          <input data-prize-award-recipient="${idx}" type="text" maxlength="120" value="${escapeAttr(a.recipient_name || '')}"
            class="mt-1 w-full bg-dc-panel border border-dc-border rounded px-2 py-1 text-xs text-white outline-none" placeholder="Awaiting assignment">
        </label>
      `;
      list.appendChild(card);
    });
    if (window.lucide) window.lucide.createIcons();
  }

  function renderPreview(payload) {
    lastPreview = payload || lastPreview;
    if (!payload) return;
    const status = $('#prizes-preview-status');
    if (status) {
      status.textContent = payload.finalized
        ? `Finalized · ${(payload.top4 || []).length} placements`
        : 'Awaiting completion · winners shown after publish';
    }
    const podium = $('#prizes-preview-podium');
    if (podium) {
      podium.innerHTML = '';
      const top3 = (payload.placements || []).slice(0, 3);
      const order = [1, 0, 2]; // 2nd | 1st | 3rd visual order
      order.forEach((slot) => {
        const tier = top3[slot];
        if (!tier) return;
        const cell = document.createElement('div');
        const isChamp = tier.rank === 1;
        cell.className = `rounded-xl p-3 text-center border ${isChamp ? 'border-yellow-500/50 bg-yellow-500/10' : 'border-dc-border bg-dc-surface/40'}`;
        cell.innerHTML = `
          <div class="text-[10px] uppercase tracking-widest text-dc-text">${ordinal(tier.rank)}</div>
          <div class="text-sm text-white font-bold mt-1 truncate">${escapeHtml(tier.title || '')}</div>
          ${tier.winner ? `<div class="text-[10px] text-theme mt-1 truncate">${escapeHtml(tier.winner.team_name || '')}</div>` : ''}
          <div class="text-xs font-mono text-dc-textBright mt-2">${payload.currency || 'BDT'} ${formatNum(tier.fiat)}</div>
          <div class="text-[10px] font-mono text-theme">${formatNum(tier.coins)} DC</div>
        `;
        podium.appendChild(cell);
      });
    }
    const list = $('#prizes-preview-list');
    if (list) {
      list.innerHTML = '';
      (payload.placements || []).slice(3).forEach((tier) => {
        const row = document.createElement('div');
        row.className = 'flex items-center justify-between text-xs px-2 py-1 rounded border border-dc-border bg-dc-surface/30';
        row.innerHTML = `
          <span class="text-dc-textBright">${ordinal(tier.rank)} · ${escapeHtml(tier.title || '')}</span>
          <span class="font-mono text-dc-textBright">${payload.currency || 'BDT'} ${formatNum(tier.fiat)} · ${formatNum(tier.coins)} DC</span>
        `;
        list.appendChild(row);
      });
    }
  }

  function escapeAttr(s) {
    return String(s == null ? '' : s).replace(/"/g, '&quot;').replace(/</g, '&lt;');
  }
  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // ── API ──

  async function load() {
    const status = $('#prizes-sync-status');
    if (status) status.textContent = 'Loading…';
    try {
      const data = await TOC.fetch(`${API}/prizes/`);
      Object.assign(state, data.config || {});
      if (!Array.isArray(state.placements)) state.placements = [];
      if (!Array.isArray(state.special_awards)) state.special_awards = [];
      renderEditor();
      renderPreview(data.public_preview);
      if (status) status.textContent = `Loaded · ${state.placements.length} tiers`;
    } catch (e) {
      const banner = $('#prizes-error-banner');
      if (banner) {
        banner.textContent = (e && e.message) || 'Failed to load prizes.';
        banner.classList.remove('hidden');
      }
      if (status) status.textContent = 'Load failed';
    }
  }

  async function save() {
    const status = $('#prizes-sync-status');
    if (status) status.textContent = 'Saving…';
    try {
      const data = await TOC.fetch(`${API}/prizes/save/`, {
        method: 'POST', body: state,
      });
      Object.assign(state, data.config || {});
      renderEditor();
      // Refresh preview from server-side payload.
      try {
        const refresh = await TOC.fetch(`${API}/prizes/`);
        renderPreview(refresh.public_preview);
      } catch (_) { /* ignore */ }
      TOC.toast('Prize configuration saved.', 'success');
      if (status) status.textContent = 'Saved';
    } catch (e) {
      TOC.toast((e && e.message) || 'Save failed.', 'error');
      if (status) status.textContent = 'Save failed';
    }
  }

  async function publish() {
    const status = $('#prizes-sync-status');
    if (status) status.textContent = 'Publishing…';
    try {
      const data = await TOC.fetch(`${API}/prizes/publish/`, { method: 'POST' });
      renderPreview(data.public_preview);
      TOC.toast('Placements published.', 'success');
      if (status) status.textContent = 'Published';
    } catch (e) {
      TOC.toast((e && e.message) || 'Publish failed.', 'error');
      if (status) status.textContent = 'Publish failed';
    }
  }

  // ── Editor wiring ──

  function renderEditor() {
    const cur = $('#prizes-currency'); if (cur) cur.value = state.currency || 'BDT';
    const fp = $('#prizes-fiat-pool'); if (fp) fp.value = state.fiat_pool || 0;
    const cp = $('#prizes-coin-pool'); if (cp) cp.value = state.coin_pool || 0;
    const ce = $('#prizes-certificates-enabled');
    if (ce) ce.checked = state.certificates_enabled !== false;
    renderTiers();
    renderAwards();
  }

  function bindEditorEvents() {
    $('#prizes-currency')?.addEventListener('change', (e) => { state.currency = (e.target.value || 'BDT').toUpperCase().slice(0, 10); });
    $('#prizes-fiat-pool')?.addEventListener('change', (e) => { state.fiat_pool = Number(e.target.value) || 0; state.placements.forEach((_, i) => syncFromPercent(i)); });
    $('#prizes-coin-pool')?.addEventListener('change', (e) => { state.coin_pool = Number(e.target.value) || 0; state.placements.forEach((_, i) => syncFromPercent(i)); });
    $('#prizes-certificates-enabled')?.addEventListener('change', (e) => { state.certificates_enabled = !!e.target.checked; });

    $('#prizes-tier-list')?.addEventListener('input', (e) => {
      const t = e.target;
      const idx = (a) => Number(t.getAttribute(a));
      if (t.hasAttribute('data-prize-tier-title')) state.placements[idx('data-prize-tier-title')].title = t.value;
      else if (t.hasAttribute('data-prize-tier-pct')) {
        state.placements[idx('data-prize-tier-pct')].percent = Math.max(0, Math.min(100, Number(t.value) || 0));
        syncFromPercent(idx('data-prize-tier-pct'));
      } else if (t.hasAttribute('data-prize-tier-fiat')) state.placements[idx('data-prize-tier-fiat')].fiat = Math.max(0, Number(t.value) || 0);
      else if (t.hasAttribute('data-prize-tier-coins')) state.placements[idx('data-prize-tier-coins')].coins = Math.max(0, Number(t.value) || 0);
      updatePctTotal();
    });
    $('#prizes-tier-list')?.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-prize-tier-remove]');
      if (!btn) return;
      const i = Number(btn.getAttribute('data-prize-tier-remove'));
      state.placements.splice(i, 1);
      // Renumber ranks.
      state.placements.forEach((p, idx) => { p.rank = idx + 1; });
      renderTiers();
    });
    $('#prizes-add-tier-btn')?.addEventListener('click', () => {
      const next = (state.placements.length || 0) + 1;
      state.placements.push({ rank: next, title: ordinal(next), percent: 0, fiat: 0, coins: 0 });
      renderTiers();
    });

    $('#prizes-award-list')?.addEventListener('input', (e) => {
      const t = e.target;
      const i = (a) => Number(t.getAttribute(a));
      if (t.hasAttribute('data-prize-award-title')) state.special_awards[i('data-prize-award-title')].title = t.value;
      else if (t.hasAttribute('data-prize-award-desc')) state.special_awards[i('data-prize-award-desc')].description = t.value;
      else if (t.hasAttribute('data-prize-award-icon')) state.special_awards[i('data-prize-award-icon')].icon = t.value;
      else if (t.hasAttribute('data-prize-award-fiat')) state.special_awards[i('data-prize-award-fiat')].fiat = Math.max(0, Number(t.value) || 0);
      else if (t.hasAttribute('data-prize-award-coins')) state.special_awards[i('data-prize-award-coins')].coins = Math.max(0, Number(t.value) || 0);
      else if (t.hasAttribute('data-prize-award-text')) state.special_awards[i('data-prize-award-text')].reward_text = t.value;
      else if (t.hasAttribute('data-prize-award-recipient')) state.special_awards[i('data-prize-award-recipient')].recipient_name = t.value;
    });
    $('#prizes-award-list')?.addEventListener('change', (e) => {
      const t = e.target;
      if (t.hasAttribute('data-prize-award-type')) {
        const i = Number(t.getAttribute('data-prize-award-type'));
        state.special_awards[i].type = t.value;
      }
    });
    $('#prizes-award-list')?.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-prize-award-remove]');
      if (!btn) return;
      const i = Number(btn.getAttribute('data-prize-award-remove'));
      state.special_awards.splice(i, 1);
      renderAwards();
    });
    $('#prizes-add-award-btn')?.addEventListener('click', () => {
      state.special_awards.push({
        id: '', title: 'New Award', description: '', type: 'cash',
        icon: 'medal', fiat: 0, coins: 0, reward_text: '',
      });
      renderAwards();
    });

    $('#prizes-refresh-btn')?.addEventListener('click', load);
    $('#prizes-save-btn')?.addEventListener('click', save);
    $('#prizes-publish-btn')?.addEventListener('click', publish);

    $('#prizes-apply-template-btn')?.addEventListener('click', () => {
      const sel = $('#prizes-smart-template');
      if (!sel) return;
      const key = sel.value;
      const tpl = SMART_TEMPLATES[key];
      if (!tpl) {
        TOC.toast('Pick a template from the dropdown first.', 'info');
        return;
      }
      state.special_awards = tpl.map((a, i) => Object.assign({
        id: '', title: '', description: '', type: 'cash', icon: 'medal',
        fiat: 0, coins: 0, reward_text: '',
      }, a, { id: `tpl-${key}-${i}` }));
      renderAwards();
      TOC.toast(`Loaded ${tpl.length} award template(s). Remember to Save.`, 'success');
    });
  }

  // Smart Engine templates — seed awards only, never overwrites placements.
  const SMART_TEMPLATES = {
    valorant: [
      { title: 'Match MVP', description: 'Highest ACS in the Grand Final series.',
        type: 'cash', icon: 'medal', fiat: 1500, coins: 1000 },
      { title: 'Headshot Machine', description: 'Highest overall HS% (min 50 kills total).',
        type: 'digital', icon: 'crosshair', reward_text: '1000 VP Riot Code' },
      { title: 'Clutch Minister', description: 'Most 1vX rounds won.',
        type: 'cash', icon: 'shield', coins: 1500 },
    ],
    efootball: [
      { title: 'Golden Boot', description: 'Top scorer of the tournament.',
        type: 'cash', icon: 'crosshair', fiat: 2000, coins: 500 },
      { title: 'Golden Glove', description: 'Most clean sheets kept.',
        type: 'cash', icon: 'shield', fiat: 1000, coins: 500 },
      { title: 'Goal of the Tournament', description: 'Community voted best goal.',
        type: 'digital', icon: 'zap', coins: 2000, reward_text: 'Premium Pack' },
    ],
    pubgm: [
      { title: 'Terminator', description: 'Player with the highest total frags.',
        type: 'cash', icon: 'crosshair', fiat: 3000 },
      { title: 'Lone Survivor', description: 'Highest average survival time.',
        type: 'cash', icon: 'shield', coins: 2000 },
    ],
    dota2: [
      { title: 'The Aegis MVP', description: 'Overall most impactful player.',
        type: 'cash', icon: 'medal', fiat: 5000 },
      { title: 'Master Support', description: 'Highest average assists + healing.',
        type: 'cash', icon: 'shield', fiat: 1500, coins: 1500 },
    ],
    generic: [
      { title: 'Tournament MVP', description: 'Selected by panel for outstanding performance.',
        type: 'cash', icon: 'medal', coins: 2500 },
      { title: 'Fan Favorite', description: 'Community-voted most exciting player.',
        type: 'cash', icon: 'zap', fiat: 1000 },
    ],
  };

  // ── Tab activation ──

  function isActive() {
    const view = document.querySelector('#view-prizes');
    return view && !view.classList.contains('hidden-view');
  }

  document.addEventListener('DOMContentLoaded', () => {
    if (!document.querySelector('#view-prizes')) return;
    bindEditorEvents();
    if (isActive()) load();
  });

  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail && e.detail.tab === 'prizes') load();
  });

  window.TOC = window.TOC || {};
  window.TOC.prizes = { load, save, publish };
})();
