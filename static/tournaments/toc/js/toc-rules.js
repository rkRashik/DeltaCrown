/**
 * TOC Rules & Info Module — Sprint 28
 * Rulebook sections, FAQ, prize info, quick reference, version publishing.
 */
;(function () {
  'use strict';

  const API = window.TOC?.api;
  const slug = window.TOC?.slug;
  if (!API || !slug) return;

  const $ = (sel) => document.querySelector(sel);
  function toast(msg, type) { if (window.TOC?.toast) window.TOC.toast(msg, type); }
  function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
  function refreshIcons() { if (typeof lucide !== 'undefined') lucide.createIcons(); }

  const CACHE_TTL_MS = 25000;
  const AUTO_REFRESH_MS = 60000;
  const STAT_IDS = ['sections', 'faq', 'version', 'ack'];
  const PANEL_IDS = ['rules-quick-ref', 'rules-match-config-card', 'rules-sections-list', 'rules-faq-list', 'rules-prize-info'];

  const MATCH_CONFIG_SCHEMAS = {
    efootball: {
      title: 'eFootball',
      fields: [
        { key: 'match_type', label: 'Match Type', type: 'text', placeholder: 'e.g. Exhibition Match' },
        { key: 'match_time', label: 'Match Time (minutes)', type: 'number', placeholder: 'e.g. 10', min: 1 },
        { key: 'injuries', label: 'Injuries', type: 'checkbox' },
        { key: 'extra_time', label: 'Extra Time', type: 'checkbox' },
        { key: 'penalties', label: 'Penalties', type: 'checkbox' },
        { key: 'substitutions', label: 'Substitutions', type: 'text', placeholder: 'e.g. 5' },
        { key: 'condition_home', label: 'Condition Home', type: 'text', placeholder: 'e.g. Normal' },
        { key: 'condition_away', label: 'Condition Away', type: 'text', placeholder: 'e.g. Normal' },
      ],
    },
    valorant: {
      title: 'Valorant',
      fields: [
        { key: 'mode', label: 'Mode', type: 'text', placeholder: 'e.g. Competitive' },
        { key: 'cheats', label: 'Cheats', type: 'checkbox' },
        { key: 'tournament_mode', label: 'Tournament Mode', type: 'checkbox' },
        { key: 'overtime_win_by_two', label: 'Overtime Win by Two', type: 'checkbox' },
        { key: 'server_region', label: 'Server Region', type: 'text', placeholder: 'e.g. AP-South' },
      ],
    },
  };

  const MATCH_CONFIG_META_KEYS = new Set(['game_key', 'schema_version', 'values', 'fields', 'veto_sequence']);

  let dashData = null;
  let inflightPromise = null;
  let activeRequestId = 0;
  let lastFetchedAt = 0;
  let autoRefreshTimer = null;

  let matchConfigEnvelope = {};
  let matchConfigValues = {};
  let matchConfigSchemaKey = '';

  function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  }

  function asBool(value, fallback) {
    if (value === true || value === false) return value;
    if (typeof value === 'number') return value !== 0;
    const token = String(value || '').trim().toLowerCase();
    if (token === 'true' || token === '1' || token === 'yes' || token === 'on') return true;
    if (token === 'false' || token === '0' || token === 'no' || token === 'off') return false;
    return !!fallback;
  }

  function canonicalGameKey(raw) {
    const token = String(raw || '').trim().toLowerCase();
    if (!token) return '';
    if (token.includes('efootball') || token === 'pes') return 'efootball';
    if (token.includes('valorant')) return 'valorant';
    return token;
  }

  function currentGameSchemaKey() {
    const configKey = canonicalGameKey(window.TOC?.config?.gameSlug || window.TOC_CONFIG?.gameSlug || '');
    return configKey;
  }

  function unpackMatchSettings(rawSettings) {
    const payload = asObject(rawSettings);
    let values = asObject(payload.values);

    if (!Object.keys(values).length) {
      values = asObject(payload.fields);
    }

    if (!Object.keys(values).length) {
      values = {};
      Object.keys(payload).forEach((key) => {
        if (!MATCH_CONFIG_META_KEYS.has(key)) {
          values[key] = payload[key];
        }
      });
    }

    return { payload, values };
  }

  function setMatchConfigStatus(message, tone) {
    const el = $('#rules-match-config-status');
    if (!el) return;

    const mode = tone || 'muted';
    el.className = 'text-[11px] mb-3';
    if (mode === 'error') {
      el.classList.add('text-dc-danger');
    } else if (mode === 'success') {
      el.classList.add('text-dc-success');
    } else if (mode === 'warning') {
      el.classList.add('text-dc-warning');
    } else {
      el.classList.add('text-dc-text');
    }
    el.textContent = message || '';
  }

  function renderMatchConfigEditor(schemaKey, values) {
    const fieldsHost = $('#rules-match-config-fields');
    const subtitle = $('#rules-match-config-subtitle');
    const saveBtn = $('#rules-match-config-save-btn');
    if (!fieldsHost) return;

    const schema = MATCH_CONFIG_SCHEMAS[schemaKey] || null;
    if (!schema) {
      if (subtitle) subtitle.textContent = 'No supported schema for this game yet. Supported now: eFootball, Valorant.';
      if (saveBtn) saveBtn.disabled = true;
      fieldsHost.innerHTML = '<p class="text-xs text-dc-text text-center py-4 col-span-full opacity-60">This tournament game does not have a dynamic match configuration schema yet.</p>';
      return;
    }

    if (subtitle) subtitle.textContent = `${schema.title} schema detected. Saved values will appear in the live match lobby rules panel.`;
    if (saveBtn) saveBtn.disabled = false;

    const safeValues = asObject(values);
    let html = '';
    schema.fields.forEach((field) => {
      const key = String(field.key || '').trim();
      if (!key) return;
      const label = esc(field.label || key);
      const type = String(field.type || 'text').toLowerCase();
      const current = safeValues[key];

      if (type === 'checkbox') {
        html += `
          <label class="flex items-center justify-between gap-3 rounded-lg border border-dc-border/70 bg-dc-surface/40 px-3 py-2.5 text-xs text-dc-text cursor-pointer">
            <span class="font-semibold text-dc-textBright">${label}</span>
            <input data-match-config-field="${esc(key)}" type="checkbox" class="rounded border-dc-border bg-dc-surface text-theme" ${asBool(current, false) ? 'checked' : ''}>
          </label>`;
        return;
      }

      const inputType = type === 'number' ? 'number' : 'text';
      const placeholder = esc(field.placeholder || '');
      const minAttr = inputType === 'number' && Number.isFinite(field.min) ? ` min="${field.min}"` : '';
      const valueAttr = current == null ? '' : String(current);

      html += `
        <div>
          <label class="block text-[10px] text-dc-text uppercase tracking-widest mb-1">${label}</label>
          <input data-match-config-field="${esc(key)}" data-input-type="${inputType}" type="${inputType}"${minAttr} value="${esc(valueAttr)}" placeholder="${placeholder}" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-dc-textBright focus:outline-none focus:border-theme/50">
        </div>`;
    });

    fieldsHost.innerHTML = html || '<p class="text-xs text-dc-text text-center py-4 col-span-full opacity-60">No configurable fields in this schema.</p>';
  }

  async function loadMatchConfig(options) {
    const opts = options || {};
    const silent = opts.silent === true;

    if (!silent) {
      setMatchConfigStatus('Loading match configuration...', 'muted');
    }

    try {
      const data = await API.get('settings/game-config/');
      matchConfigEnvelope = asObject(data);

      const unpacked = unpackMatchSettings(matchConfigEnvelope.match_settings);
      matchConfigValues = asObject(unpacked.values);

      const payloadKey = canonicalGameKey(unpacked.payload.game_key);
      matchConfigSchemaKey = payloadKey || currentGameSchemaKey();

      renderMatchConfigEditor(matchConfigSchemaKey, matchConfigValues);
      setMatchConfigStatus('Configuration is ready. Save after making edits to sync with match lobby rules.', 'success');
      return matchConfigEnvelope;
    } catch (e) {
      const detail = e && e.message ? String(e.message) : 'Request failed';
      setMatchConfigStatus(`Could not load match configuration: ${detail}`, 'error');
      renderMatchConfigEditor(currentGameSchemaKey(), {});
      return null;
    }
  }

  function collectMatchConfigValues(schemaKey) {
    const schema = MATCH_CONFIG_SCHEMAS[schemaKey];
    if (!schema) return {};

    const values = {};
    schema.fields.forEach((field) => {
      const key = String(field.key || '').trim();
      if (!key) return;

      const input = document.querySelector(`[data-match-config-field="${key}"]`);
      if (!input) return;

      const type = String(field.type || 'text').toLowerCase();
      if (type === 'checkbox') {
        values[key] = !!input.checked;
        return;
      }

      const rawValue = String(input.value || '').trim();
      if (!rawValue) return;
      if (type === 'number') {
        const parsed = Number(rawValue);
        values[key] = Number.isFinite(parsed) ? parsed : rawValue;
        return;
      }
      values[key] = rawValue;
    });
    return values;
  }

  async function saveMatchConfig() {
    const schema = MATCH_CONFIG_SCHEMAS[matchConfigSchemaKey];
    if (!schema) {
      toast('No supported match configuration schema for this game.', 'error');
      return;
    }

    const nextValues = collectMatchConfigValues(matchConfigSchemaKey);
    const currentSettings = asObject(matchConfigEnvelope.match_settings);

    const nextSettings = {
      ...currentSettings,
      game_key: matchConfigSchemaKey,
      schema_version: String(currentSettings.schema_version || '1.0'),
      values: nextValues,
    };
    delete nextSettings.fields;

    const payload = {
      game_id: matchConfigEnvelope.game_id || null,
      default_match_format: matchConfigEnvelope.default_match_format || 'bo1',
      scoring_rules: asObject(matchConfigEnvelope.scoring_rules),
      enable_veto: asBool(matchConfigEnvelope.enable_veto, false),
      veto_type: String(matchConfigEnvelope.veto_type || 'standard'),
      match_settings: nextSettings,
    };

    try {
      setMatchConfigStatus('Saving match configuration...', 'warning');
      await API.put('settings/game-config/', payload);

      matchConfigEnvelope = {
        ...matchConfigEnvelope,
        ...payload,
        match_settings: nextSettings,
      };
      matchConfigValues = nextValues;

      setMatchConfigStatus('Match configuration saved. Match lobby rules are now synced.', 'success');
      toast('Match configuration saved', 'success');
    } catch (e) {
      const detail = e && e.message ? String(e.message) : 'Save failed';
      setMatchConfigStatus(`Failed to save match configuration: ${detail}`, 'error');
      toast('Failed to save match configuration', 'error');
    }
  }

  function isRulesTabActive() {
    return (window.location.hash || '').replace('#', '') === 'rules';
  }

  function hasFreshCache() {
    return !!dashData && (Date.now() - lastFetchedAt) < CACHE_TTL_MS;
  }

  function formatTime(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  function setSyncStatus(state, note) {
    const el = $('#rules-sync-status');
    if (!el) return;
    if (state === 'loading') {
      el.className = 'text-[10px] font-mono text-dc-warning mt-1';
      el.textContent = note || 'Syncing rules...';
      return;
    }
    if (state === 'error') {
      el.className = 'text-[10px] font-mono text-dc-danger mt-1';
      el.textContent = note || 'Sync failed';
      return;
    }
    if (lastFetchedAt > 0) {
      el.className = 'text-[10px] font-mono text-dc-text mt-1';
      el.textContent = `Last sync ${formatTime(new Date(lastFetchedAt))}`;
      return;
    }
    el.className = 'text-[10px] font-mono text-dc-text mt-1';
    el.textContent = 'Not synced yet';
  }

  function setErrorBanner(message) {
    const el = $('#rules-error-banner');
    if (!el) return;
    if (!message) {
      el.classList.add('hidden');
      el.innerHTML = '';
      return;
    }
    el.classList.remove('hidden');
    el.innerHTML = `
      <div class="flex items-start gap-3">
        <i data-lucide="wifi-off" class="w-4 h-4 text-dc-danger shrink-0 mt-0.5"></i>
        <div class="min-w-0 flex-1">
          <p class="text-xs font-bold text-white">Rules request failed</p>
          <p class="text-[11px] text-dc-text mt-1">${esc(message)}</p>
          <button type="button" class="mt-2 px-2.5 py-1 rounded border border-dc-danger/40 text-[10px] font-bold uppercase tracking-wider text-dc-danger hover:bg-dc-danger/20 transition-colors" data-click="TOC.rules.refresh" data-click-args="[{&quot;force&quot;:true}]">Retry now</button>
        </div>
      </div>`;
    refreshIcons();
  }

  function setLoading(loading) {
    STAT_IDS.forEach((id) => {
      const el = $(`#rules-stat-${id}`);
      if (!el) return;
      el.classList.toggle('toc-loading-value', loading);
    });
    PANEL_IDS.forEach((id) => {
      const el = $(`#${id}`);
      if (!el) return;
      el.classList.toggle('toc-panel-loading', loading);
      if (loading) el.setAttribute('aria-busy', 'true');
      else el.removeAttribute('aria-busy');
    });
  }

  function renderDashboard(data) {
    const safe = data && typeof data === 'object' ? data : {};
    renderStats(safe.summary && typeof safe.summary === 'object' ? safe.summary : {});
    renderSections(Array.isArray(safe.sections) ? safe.sections : []);
    renderFaq(Array.isArray(safe.faq) ? safe.faq : []);
    renderQuickRef(safe.quick_reference && typeof safe.quick_reference === 'object' ? safe.quick_reference : {});
    renderPrizeInfo(safe.prize_info && typeof safe.prize_info === 'object' ? safe.prize_info : {});
    setLoading(false);
    setErrorBanner('');
    setSyncStatus('ok');
  }

  function renderEmptyState(message) {
    const text = esc(message || 'No data available');
    const sections = $('#rules-sections-list');
    const faq = $('#rules-faq-list');
    if (sections) {
      sections.innerHTML = `<div class="glass-box rounded-xl p-8 text-center"><p class="text-xs text-dc-text opacity-60">${text}</p></div>`;
    }
    if (faq) faq.innerHTML = `<p class="text-xs text-dc-text text-center py-4 opacity-60">${text}</p>`;
    setLoading(false);
  }

  async function refresh(options) {
    const opts = options || {};
    const force = opts.force === true;
    const silent = opts.silent === true;

    if (dashData && !force) {
      renderDashboard(dashData);
      loadMatchConfig({ silent: true });
      if (hasFreshCache()) return dashData;
    }

    if (inflightPromise && !force) return inflightPromise;

    if (!silent) {
      setLoading(true);
      setSyncStatus('loading', dashData ? 'Refreshing rules...' : 'Loading rules...');
    }

    const requestId = ++activeRequestId;
    inflightPromise = (async () => {
      try {
        const data = await API.get('rules/');
        if (requestId !== activeRequestId) return dashData || data;
        dashData = data;
        lastFetchedAt = Date.now();
        renderDashboard(data);
        loadMatchConfig({ silent: true });
        return data;
      } catch (e) {
        if (requestId !== activeRequestId) return dashData;
        const detail = e && e.message ? String(e.message) : 'Request failed';
        console.error('[rules] fetch error', e);
        if (dashData) {
          setLoading(false);
          setSyncStatus('error', `Using cached data (${detail})`);
          setErrorBanner(`Live refresh failed, showing cached rules data. ${detail}`);
        } else {
          setSyncStatus('error', detail);
          setErrorBanner(detail);
          renderEmptyState('Rules data is unavailable right now.');
        }
        return dashData;
      } finally {
        if (requestId === activeRequestId) inflightPromise = null;
      }
    })();

    return inflightPromise;
  }

  function invalidate() {
    lastFetchedAt = 0;
  }

  function startAutoRefresh() {
    stopAutoRefresh();
    autoRefreshTimer = setInterval(() => {
      if (!isRulesTabActive()) return;
      refresh({ silent: true });
    }, AUTO_REFRESH_MS);
  }

  function stopAutoRefresh() {
    if (autoRefreshTimer) {
      clearInterval(autoRefreshTimer);
      autoRefreshTimer = null;
    }
  }

  function onTabChange(e) {
    if (e.detail?.tab === 'rules') {
      refresh();
      startAutoRefresh();
      return;
    }
    stopAutoRefresh();
  }

  function onVisibilityChange() {
    if (!document.hidden && isRulesTabActive() && !hasFreshCache()) {
      refresh({ silent: true });
    }
  }

  function renderStats(s) {
    const el = (id, v) => { const e = $(`#rules-stat-${id}`); if (e) e.textContent = v; };
    el('sections', s.total_sections || 0);
    el('faq', s.total_faq || 0);
    el('version', s.current_version || '1.0');
    el('ack', (s.ack_pct || 0) + '%');
  }

  function renderSections(sections) {
    const container = $('#rules-sections-list');
    if (!container) return;

    if (!sections.length) {
      container.innerHTML = '<div class="glass-box rounded-xl p-8 text-center"><p class="text-xs text-dc-text opacity-50">No rule sections yet. Click "Add Section" to start.</p></div>';
      return;
    }

    let html = '';
    sections.forEach(s => {
      html += `
        <details class="glass-box rounded-xl group">
          <summary class="p-5 cursor-pointer flex items-center justify-between select-none">
            <span class="font-display font-bold text-white text-sm flex items-center gap-2">
              <i data-lucide="file-text" class="w-4 h-4 text-theme"></i> ${esc(s.title)}
            </span>
            <div class="flex items-center gap-2">
              <button data-click="event.stopPropagation" class="text-[10px] text-theme hover:underline">Edit</button>
              <button data-click="event.stopPropagation" class="text-[10px] text-dc-danger hover:underline">Delete</button>
              <i data-lucide="chevron-down" class="w-4 h-4 text-dc-text group-open:rotate-180 transition-transform"></i>
            </div>
          </summary>
          <div class="px-5 pb-5">
            <div class="prose prose-invert prose-sm max-w-none text-dc-text">
              ${s.content ? s.content.replace(/\n/g, '<br>') : '<p class="text-dc-text opacity-50">No content yet</p>'}
            </div>
            ${s.updated_at ? `<p class="text-[10px] text-dc-text mt-3 opacity-50">Last updated: ${new Date(s.updated_at).toLocaleString()}</p>` : ''}
          </div>
        </details>`;
    });
    container.innerHTML = html;
    refreshIcons();
  }

  function renderFaq(faqs) {
    const container = $('#rules-faq-list');
    if (!container) return;

    if (!faqs.length) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">No FAQs yet</p>';
      return;
    }

    let html = '';
    faqs.forEach(f => {
      html += `
        <details class="bg-dc-surface/50 rounded-lg group">
          <summary class="p-3 cursor-pointer flex items-center justify-between select-none text-sm">
            <span class="text-white font-medium">${esc(f.question)}</span>
            <div class="flex items-center gap-2">
              <button data-click="event.stopPropagation" class="text-[10px] text-theme hover:underline">Edit</button>
              <button data-click="event.stopPropagation" class="text-[10px] text-dc-danger hover:underline">Delete</button>
              <i data-lucide="chevron-down" class="w-3 h-3 text-dc-text group-open:rotate-180 transition-transform"></i>
            </div>
          </summary>
          <div class="px-3 pb-3 text-xs text-dc-text">${esc(f.answer)}</div>
        </details>`;
    });
    container.innerHTML = html;
    refreshIcons();
  }

  function renderQuickRef(qr) {
    const container = $('#rules-quick-ref');
    if (!container) return;

    if (!qr.format && !qr.match_format && !qr.checkin_time) {
      container.innerHTML = '<p class="text-dc-text text-xs text-center py-4 col-span-full opacity-50">Not configured</p>';
      return;
    }

    const items = [
      { label: 'Format', value: qr.format },
      { label: 'Match Format', value: qr.match_format },
      { label: 'Check-in Time', value: qr.checkin_time },
      { label: 'Map Pool', value: qr.map_pool },
      { label: 'Special Rules', value: qr.special_rules },
      { label: 'Contact', value: qr.contact },
    ].filter(i => i.value);

    let html = '';
    items.forEach(i => {
      html += `
        <div class="bg-dc-surface/50 rounded-lg p-3">
          <p class="text-[10px] text-dc-text uppercase tracking-widest mb-1">${esc(i.label)}</p>
          <p class="text-sm text-white">${esc(i.value)}</p>
        </div>`;
    });
    container.innerHTML = html;
  }

  function renderPrizeInfo(pi) {
    const container = $('#rules-prize-info');
    if (!container) return;

    if (!pi.distribution?.length && !pi.payment_method) {
      container.innerHTML = '<p class="text-xs text-dc-text text-center py-4 opacity-50">Not configured</p>';
      return;
    }

    let html = '<div class="space-y-3">';
    if (pi.distribution?.length) {
      html += '<div class="space-y-1">';
      pi.distribution.forEach((d, i) => {
        html += `<div class="flex justify-between text-xs"><span class="text-dc-text">${ordinal(i + 1)} Place</span><span class="text-white font-bold">${esc(String(d))}</span></div>`;
      });
      html += '</div>';
    }
    if (pi.payment_method) html += `<p class="text-xs text-dc-text">Payment: ${esc(pi.payment_method)}</p>`;
    if (pi.payment_schedule) html += `<p class="text-xs text-dc-text">Schedule: ${esc(pi.payment_schedule)}</p>`;
    if (pi.notes) html += `<p class="text-xs text-dc-text mt-2">${esc(pi.notes)}</p>`;
    html += '</div>';
    container.innerHTML = html;
  }

  function ordinal(n) {
    const s = ['th', 'st', 'nd', 'rd'];
    const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
  }

  /* ─── Drawer helpers ─────────────────────── */
  const FIELD = 'w-full bg-dc-surface/50 border border-dc-border/50 rounded-lg px-3 py-2 text-sm text-white placeholder-dc-text/40 focus:outline-none focus:border-theme';
  const LABEL = 'block text-[10px] text-dc-text uppercase tracking-widest mb-1';
  function drawerFooter(submitCall, submitLabel, danger = false) {
    const btnCls = danger ? 'bg-dc-danger hover:opacity-90' : 'bg-theme hover:opacity-90';
    const scMatch = submitCall.match(/^([\w.]+)\((.*)\)$/s);
    const scAttrs = scMatch
      ? `data-click="${scMatch[1]}"` + (scMatch[2].trim() ? ` data-click-args="[${scMatch[2].trim()}]"` : '')
      : '';
    return `<div class="flex gap-3 p-4 pt-0">
      <button ${scAttrs} class="flex-1 ${btnCls} text-white text-sm font-bold py-2 rounded-lg transition">${submitLabel}</button>
      <button data-click="TOC.drawer.close" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
  }

  /* ─── Actions ─────────────────────────────── */
  function addSection() {
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Section ID *</label>
        <input id="rules-sec-id" type="text" class="${FIELD}" placeholder="e.g. custom_rules"></div>
      <div><label class="${LABEL}">Title *</label>
        <input id="rules-sec-title" type="text" class="${FIELD}" placeholder="Section title"></div>
      <div><label class="${LABEL}">Content</label>
        <textarea id="rules-sec-content" rows="5" class="${FIELD} resize-none" placeholder="Section content (Markdown supported)"></textarea></div>
    </div>`;
    TOC.drawer.open('Add Rule Section', body, drawerFooter("TOC.rules._submitAddSection()", 'Add Section'));
    setTimeout(() => document.getElementById('rules-sec-id')?.focus(), 50);
  }

  function _submitAddSection() {
    const id = document.getElementById('rules-sec-id')?.value.trim();
    const title = document.getElementById('rules-sec-title')?.value.trim();
    const content = document.getElementById('rules-sec-content')?.value.trim() || '';
    if (!id) { toast('Section ID is required', 'error'); return; }
    API.post(`rules/sections/${id}/`, { title: title || id, content })
      .then(() => { toast('Section added', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function editSection(sectionId) {
    const s = (dashData?.sections || []).find(x => x.id === sectionId);
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Title *</label>
        <input id="rules-esec-title" type="text" value="${esc(s?.title || '')}" class="${FIELD}"></div>
      <div><label class="${LABEL}">Content</label>
        <textarea id="rules-esec-content" rows="6" class="${FIELD} resize-none">${esc(s?.content || '')}</textarea></div>
    </div>`;
    TOC.drawer.open('Edit Section', body, drawerFooter(`TOC.rules._submitEditSection('${sectionId}')`, 'Save Changes'));
  }

  function _submitEditSection(sectionId) {
    const title = document.getElementById('rules-esec-title')?.value.trim();
    const content = document.getElementById('rules-esec-content')?.value.trim() || '';
    if (!title) { toast('Title is required', 'error'); return; }
    API.post(`rules/sections/${sectionId}/`, { title, content })
      .then(() => { toast('Updated', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteSection(sectionId) {
    if (!confirm('Delete this section?')) return;
    API.delete(`rules/sections/${sectionId}/`)
      .then(() => { toast('Deleted', 'success'); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function addFaq() {
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Question *</label>
        <input id="rules-faq-q" type="text" class="${FIELD}" placeholder="Frequently asked question"></div>
      <div><label class="${LABEL}">Answer *</label>
        <textarea id="rules-faq-a" rows="4" class="${FIELD} resize-none" placeholder="Detailed answer..."></textarea></div>
    </div>`;
    TOC.drawer.open('Add FAQ', body, drawerFooter("TOC.rules._submitAddFaq()", 'Add FAQ'));
    setTimeout(() => document.getElementById('rules-faq-q')?.focus(), 50);
  }

  function _submitAddFaq() {
    const question = document.getElementById('rules-faq-q')?.value.trim();
    const answer = document.getElementById('rules-faq-a')?.value.trim() || '';
    if (!question) { toast('Question is required', 'error'); return; }
    API.post('rules/faq/', { question, answer })
      .then(() => { toast('FAQ added', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function editFaq(faqId) {
    const f = (dashData?.faq || []).find(x => x.id === faqId);
    const body = `<div class="space-y-4 p-5">
      <div><label class="${LABEL}">Question *</label>
        <input id="rules-efaq-q" type="text" value="${esc(f?.question || '')}" class="${FIELD}"></div>
      <div><label class="${LABEL}">Answer</label>
        <textarea id="rules-efaq-a" rows="4" class="${FIELD} resize-none">${esc(f?.answer || '')}</textarea></div>
    </div>`;
    TOC.drawer.open('Edit FAQ', body, drawerFooter(`TOC.rules._submitEditFaq('${faqId}')`, 'Save Changes'));
  }

  function _submitEditFaq(faqId) {
    const question = document.getElementById('rules-efaq-q')?.value.trim();
    const answer = document.getElementById('rules-efaq-a')?.value.trim() || '';
    if (!question) { toast('Question is required', 'error'); return; }
    API.put(`rules/faq/${faqId}/`, { question, answer })
      .then(() => { toast('Updated', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteFaq(faqId) {
    if (!confirm('Delete this FAQ?')) return;
    API.delete(`rules/faq/${faqId}/`)
      .then(() => { toast('Deleted', 'success'); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function publishVersion() {
    const body = `<div class="space-y-4 p-5">
      <p class="text-xs text-dc-text">Publishing timestamps the rulebook and sends acknowledgement requests to all participants.</p>
      <div><label class="${LABEL}">Version Number *</label>
        <input id="rules-pub-version" type="text" class="${FIELD}" placeholder="e.g. 2.0"></div>
      <div><label class="${LABEL}">Changelog</label>
        <textarea id="rules-pub-changelog" rows="4" class="${FIELD} resize-none" placeholder="What changed in this version?"></textarea></div>
    </div>`;
    const footer = `<div class="flex gap-3 p-4 pt-0">
      <button data-click="TOC.rules._submitPublish" class="flex-1 bg-dc-success hover:opacity-90 text-white text-sm font-bold py-2 rounded-lg transition">Publish Version</button>
      <button data-click="TOC.drawer.close" class="text-dc-text text-sm py-2 px-4 hover:text-white transition">Cancel</button>
    </div>`;
    TOC.drawer.open('Publish Rulebook Version', body, footer);
    setTimeout(() => document.getElementById('rules-pub-version')?.focus(), 50);
  }

  function _submitPublish() {
    const version = document.getElementById('rules-pub-version')?.value.trim();
    const changelog = document.getElementById('rules-pub-changelog')?.value.trim() || '';
    if (!version) { toast('Version number is required', 'error'); return; }
    API.post('rules/publish/', { version, changelog })
      .then(() => { toast(`Version ${version} published`, 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  function editQuickRef() {
    const qr = dashData?.quick_reference || {};
    const body = `<div class="space-y-4 p-5">
      <div class="grid grid-cols-2 gap-3">
        <div><label class="${LABEL}">Format</label>
          <input id="rules-qr-format" type="text" value="${esc(qr.format || '')}" class="${FIELD}" placeholder="e.g. Double Elim"></div>
        <div><label class="${LABEL}">Match Format</label>
          <input id="rules-qr-match" type="text" value="${esc(qr.match_format || '')}" class="${FIELD}" placeholder="e.g. Best of 3"></div>
        <div><label class="${LABEL}">Check-in Time</label>
          <input id="rules-qr-checkin" type="text" value="${esc(qr.checkin_time || '')}" class="${FIELD}" placeholder="e.g. 15 min before"></div>
        <div><label class="${LABEL}">Map Pool</label>
          <input id="rules-qr-maps" type="text" value="${esc(qr.map_pool || '')}" class="${FIELD}" placeholder="e.g. Dust2, Mirage"></div>
      </div>
      <div><label class="${LABEL}">Contact</label>
        <input id="rules-qr-contact" type="text" value="${esc(qr.contact || '')}" class="${FIELD}" placeholder="Discord handle or email"></div>
    </div>`;
    TOC.drawer.open('Edit Quick Reference', body, drawerFooter("TOC.rules._submitQuickRef()", 'Save Quick Reference'));
  }

  function _submitQuickRef() {
    const format       = document.getElementById('rules-qr-format')?.value.trim()  || '';
    const match_format = document.getElementById('rules-qr-match')?.value.trim()   || '';
    const checkin_time = document.getElementById('rules-qr-checkin')?.value.trim() || '';
    const map_pool     = document.getElementById('rules-qr-maps')?.value.trim()    || '';
    const contact      = document.getElementById('rules-qr-contact')?.value.trim() || '';
    API.post('rules/quick-reference/', { format, match_format, checkin_time, map_pool, contact })
      .then(() => { toast('Updated', 'success'); TOC.drawer.close(); invalidate(); refresh({ force: true }); })
      .catch(() => toast('Failed', 'error'));
  }

  window.TOC = window.TOC || {};
  window.TOC.rules = {
    refresh, invalidate,
    saveMatchConfig,
    addSection, _submitAddSection,
    editSection, _submitEditSection, deleteSection,
    addFaq, _submitAddFaq,
    editFaq, _submitEditFaq, deleteFaq,
    publishVersion, _submitPublish,
    editQuickRef, _submitQuickRef,
  };

  document.addEventListener('toc:tab-changed', onTabChange);
  document.addEventListener('visibilitychange', onVisibilityChange);

  if (isRulesTabActive()) {
    refresh();
    startAutoRefresh();
  }
})();
