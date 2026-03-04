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

  let dashData = null;

  async function refresh() {
    try {
      const data = await API.get('rules/');
      dashData = data;
      renderStats(data.summary || {});
      renderSections(data.sections || []);
      renderFaq(data.faq || []);
      renderQuickRef(data.quick_reference || {});
      renderPrizeInfo(data.prize_info || {});
    } catch (e) {
      console.error('[rules] fetch error', e);
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
              <button onclick="event.stopPropagation(); TOC.rules.editSection('${s.id}')" class="text-[10px] text-theme hover:underline">Edit</button>
              <button onclick="event.stopPropagation(); TOC.rules.deleteSection('${s.id}')" class="text-[10px] text-dc-danger hover:underline">Delete</button>
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
              <button onclick="event.stopPropagation(); TOC.rules.editFaq('${f.id}')" class="text-[10px] text-theme hover:underline">Edit</button>
              <button onclick="event.stopPropagation(); TOC.rules.deleteFaq('${f.id}')" class="text-[10px] text-dc-danger hover:underline">Delete</button>
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

  /* ─── Actions ─────────────────────────────── */
  function addSection() {
    const id = prompt('Section ID (e.g. "custom_rules"):');
    if (!id) return;
    const title = prompt('Section title:') || id;
    const content = prompt('Content (you can edit later):') || '';
    API.post(`rules/sections/${id}/`, { title, content })
      .then(() => { toast('Section added', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function editSection(sectionId) {
    const section = (dashData?.sections || []).find(s => s.id === sectionId);
    const title = prompt('Section title:', section?.title || '');
    if (title === null) return;
    const content = prompt('Content:', section?.content || '');
    if (content === null) return;
    API.post(`rules/sections/${sectionId}/`, { title, content })
      .then(() => { toast('Updated', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteSection(sectionId) {
    if (!confirm('Delete this section?')) return;
    API.delete(`rules/sections/${sectionId}/`)
      .then(() => { toast('Deleted', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function addFaq() {
    const question = prompt('Question:');
    if (!question) return;
    const answer = prompt('Answer:') || '';
    API.post('rules/faq/', { question, answer })
      .then(() => { toast('FAQ added', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function editFaq(faqId) {
    const faq = (dashData?.faq || []).find(f => f.id === faqId);
    const question = prompt('Question:', faq?.question || '');
    if (question === null) return;
    const answer = prompt('Answer:', faq?.answer || '');
    if (answer === null) return;
    API.put(`rules/faq/${faqId}/`, { question, answer })
      .then(() => { toast('Updated', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function deleteFaq(faqId) {
    if (!confirm('Delete this FAQ?')) return;
    API.delete(`rules/faq/${faqId}/`)
      .then(() => { toast('Deleted', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function publishVersion() {
    const version = prompt('Version number (e.g. 2.0):');
    if (!version) return;
    const changelog = prompt('Changelog:') || '';
    API.post('rules/publish/', { version, changelog })
      .then(() => { toast(`Version ${version} published`, 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  function editQuickRef() {
    const qr = dashData?.quick_reference || {};
    const format = prompt('Format:', qr.format || '');
    const match_format = prompt('Match Format:', qr.match_format || '');
    const checkin_time = prompt('Check-in Time:', qr.checkin_time || '');
    const map_pool = prompt('Map Pool:', qr.map_pool || '');
    const contact = prompt('Contact:', qr.contact || '');
    API.post('rules/quick-reference/', { format, match_format, checkin_time, map_pool, contact })
      .then(() => { toast('Updated', 'success'); refresh(); })
      .catch(() => toast('Failed', 'error'));
  }

  window.TOC = window.TOC || {};
  window.TOC.rules = { refresh, addSection, editSection, deleteSection, addFaq, editFaq, deleteFaq, publishVersion, editQuickRef };

  // Auto-load when tab is activated
  document.addEventListener('toc:tab-changed', (e) => {
    if (e.detail && e.detail.tab === 'rules') refresh();
  });
})();
