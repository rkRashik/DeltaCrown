/**
 * Tournament Creation Wizard — Vanilla JS Engine
 * Handles: step navigation, game intelligence, form state, API submission
 */

// ── State ──────────────────────────────────────────────────────────
const S = {
  step: 0,
  gameId: null,
  gameslug: '',
  name: '',
  participation: 'team',
  format: 'single_elimination',
  platform: 'pc',
  capacity: 16,
  regStart: '', regEnd: '', tourStart: '', tourEnd: '',
  hasEntryFee: false, entryFeeAmount: 0, entryFeeCurrency: 'BDT',
  prizePool: 0, prizeCurrency: 'BDT',
  description: '', rulesText: '',
};
let GAMES = [];
let FORMATS = [];
let PLATFORMS = [];

// ── Init ───────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  GAMES = JSON.parse(document.getElementById('gamesData').textContent);
  FORMATS = JSON.parse(document.getElementById('formatChoicesData').textContent);
  PLATFORMS = JSON.parse(document.getElementById('platformChoicesData').textContent);
  renderGameGrid();
  renderFormatGrid();
  renderPlatformGrid();
  renderSizeChips();
  setSmartDefaults();
  bindInputs();
});

// ── Game Grid ──────────────────────────────────────────────────────
function renderGameGrid() {
  const grid = document.getElementById('gameGrid');
  grid.innerHTML = GAMES.map(g => `
    <button onclick="selectGame(${g.id})" id="game-${g.id}"
      class="game-card rounded-xl p-3 border border-white/8 text-center transition-all hover:border-white/20 hover:bg-white/3 cursor-pointer group">
      <div class="w-10 h-10 rounded-lg mx-auto mb-2 flex items-center justify-center text-lg font-bold"
        style="background:${g.primary_color}22;color:${g.primary_color}">
        ${g.icon_url ? `<img src="${g.icon_url}" class="w-6 h-6 rounded" alt="">` : g.short_code}
      </div>
      <div class="text-xs font-semibold text-white truncate">${g.display_name}</div>
      <div class="text-[10px] text-gray-500 mt-0.5">${g.category_label}</div>
    </button>
  `).join('');
}

function selectGame(id) {
  const g = GAMES.find(x => x.id === id);
  if (!g) return;
  // Deselect prev
  document.querySelectorAll('.game-card').forEach(c => c.classList.remove('selected'));
  document.getElementById('game-' + id).classList.add('selected');

  S.gameId = id;
  S.gameslug = g.slug;

  // Set accent color
  const app = document.getElementById('createApp');
  app.style.setProperty('--accent', g.primary_color);
  const rgb = hexToRgb(g.primary_color);
  app.style.setProperty('--accent-rgb', rgb);

  // Auto-set participation
  setParticipation(g.recommended_participation);
  document.getElementById('teamSizeHint').textContent = g.team_size_display;

  // Auto-set platform & format
  S.platform = g.recommended_platform;
  renderPlatformGrid();
  S.format = g.recommended_format;
  renderFormatGrid();

  // Capacity suggestions
  S.capacity = g.recommended_sizes[1] || g.recommended_sizes[0] || 16;
  document.getElementById('capacitySlider').value = S.capacity;
  document.getElementById('capacityLabel').textContent = S.capacity;
  renderSizeChips();

  // Rule template
  if (g.rule_template) document.getElementById('rulesText').value = g.rule_template;

  // Tips panel
  showTips(g);
  updateConfigPreview();
}

function showTips(g) {
  const panel = document.getElementById('tipsPanel');
  panel.classList.remove('hidden');
  document.getElementById('tipTitle').textContent = g.display_name;
  document.getElementById('tipSubtitle').textContent = g.subtitle + ' • ' + g.match_format_label;
  const list = document.getElementById('tipsList');
  list.innerHTML = (g.tips || []).map(t => `
    <div class="flex items-start gap-2">
      <span class="text-cyan-400 mt-0.5 text-xs">▸</span>
      <span class="text-xs text-gray-300">${t}</span>
    </div>
  `).join('');
}

// ── Format Grid ────────────────────────────────────────────────────
function renderFormatGrid() {
  const g = GAMES.find(x => x.id === S.gameId);
  const icons = {trophy:'🏆',shield:'🛡️','refresh-cw':'🔄',layers:'📊','git-merge':'⚔️'};
  const grid = document.getElementById('formatGrid');
  grid.innerHTML = FORMATS.map(f => {
    const supported = g ? (g.supported_formats[f.value] !== false) : true;
    const recommended = g && g.recommended_format === f.value;
    const selected = S.format === f.value;
    return `
      <button onclick="selectFormat('${f.value}')"
        class="format-card ${selected ? 'selected' : ''} ${!supported ? 'disabled' : ''}
          rounded-xl p-4 border border-white/8 text-left transition-all hover:border-white/15 flex items-start gap-4 w-full">
        <div class="text-xl mt-0.5">${icons[f.icon]||'📋'}</div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold text-white">${f.label}</span>
            ${recommended ? '<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 font-medium">Recommended</span>' : ''}
            ${!supported ? '<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 font-medium">Not Supported</span>' : ''}
          </div>
          <p class="text-xs text-gray-400 mt-1">${f.description}</p>
          <p class="text-[10px] text-gray-500 mt-1">Best for: ${f.best_for}</p>
        </div>
      </button>`;
  }).join('');
}

function selectFormat(val) {
  S.format = val;
  renderFormatGrid();
  updateConfigPreview();
}

// ── Platform Grid ──────────────────────────────────────────────────
function renderPlatformGrid() {
  const icons = {monitor:'💻',smartphone:'📱','gamepad-2':'🎮',globe:'🌐'};
  const grid = document.getElementById('platformGrid');
  grid.innerHTML = PLATFORMS.map(p => `
    <button onclick="selectPlatform('${p.value}')"
      class="format-card ${S.platform===p.value?'selected':''} rounded-xl p-3 border border-white/8 text-center transition-all hover:border-white/15">
      <div class="text-xl mb-1">${icons[p.icon]||'🎮'}</div>
      <div class="text-xs font-semibold text-white">${p.label}</div>
    </button>
  `).join('');
}

function selectPlatform(val) {
  S.platform = val;
  renderPlatformGrid();
  updateConfigPreview();
}

// ── Capacity ───────────────────────────────────────────────────────
function renderSizeChips() {
  const g = GAMES.find(x => x.id === S.gameId);
  const sizes = g ? g.recommended_sizes : [8, 16, 32, 64, 128];
  document.getElementById('sizeChips').innerHTML = sizes.map(n => `
    <button onclick="setCapacity(${n})"
      class="size-chip ${S.capacity===n?'recommended':''} px-3 py-1.5 rounded-lg border border-white/10 text-xs font-medium text-gray-300
        hover:border-white/20 transition-all ${S.capacity===n?'text-cyan-400':''}">
      ${n}
    </button>
  `).join('');
}

function setCapacity(n) {
  S.capacity = n;
  document.getElementById('capacitySlider').value = n;
  document.getElementById('capacityLabel').textContent = n;
  renderSizeChips();
  updateConfigPreview();
}

// ── Participation ──────────────────────────────────────────────────
function setParticipation(type) {
  S.participation = type;
  document.getElementById('btn-team').classList.toggle('selected', type === 'team');
  document.getElementById('btn-solo').classList.toggle('selected', type === 'solo');
  updateConfigPreview();
}

// ── Smart Defaults ─────────────────────────────────────────────────
function setSmartDefaults() {
  const now = new Date();
  const regStart = new Date(now.getTime() + 3600000); // +1h
  const regEnd = new Date(now.getTime() + 4*86400000); // +4d
  const tourStart = new Date(now.getTime() + 7*86400000); // +7d
  document.getElementById('regStart').value = toLocalISO(regStart);
  document.getElementById('regEnd').value = toLocalISO(regEnd);
  document.getElementById('tourStart').value = toLocalISO(tourStart);
  S.regStart = document.getElementById('regStart').value;
  S.regEnd = document.getElementById('regEnd').value;
  S.tourStart = document.getElementById('tourStart').value;
}

// ── Input Bindings ─────────────────────────────────────────────────
function bindInputs() {
  const nameInput = document.getElementById('tournamentName');
  nameInput.addEventListener('input', () => {
    S.name = nameInput.value;
    document.getElementById('slugPreview').textContent = slugify(S.name) || '—';
  });
  document.getElementById('capacitySlider').addEventListener('input', e => {
    S.capacity = parseInt(e.target.value);
    document.getElementById('capacityLabel').textContent = S.capacity;
    renderSizeChips();
  });
  ['regStart','regEnd','tourStart','tourEnd'].forEach(id => {
    document.getElementById(id).addEventListener('change', e => { S[id] = e.target.value; });
  });
  document.getElementById('entryFeeToggle').addEventListener('change', e => {
    S.hasEntryFee = e.target.checked;
    document.getElementById('feeFields').classList.toggle('hidden', !e.target.checked);
  });
  ['entryFeeAmount','entryFeeCurrency','prizePool','prizeCurrency','description','rulesText'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', e => { S[id] = e.target.value; });
  });
}

function loadRuleTemplate() {
  const g = GAMES.find(x => x.id === S.gameId);
  if (g && g.rule_template) document.getElementById('rulesText').value = g.rule_template;
}

// ── Config Preview ─────────────────────────────────────────────────
function updateConfigPreview() {
  const g = GAMES.find(x => x.id === S.gameId);
  const items = [
    ['Game', g ? g.display_name : 'Not selected'],
    ['Type', S.participation === 'team' ? 'Team' : 'Solo'],
    ['Format', S.format.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())],
    ['Capacity', S.capacity + (S.participation==='team' ? ' teams' : ' players')],
    ['Platform', S.platform.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())],
  ];
  document.getElementById('configPreview').innerHTML = items.map(([k,v]) =>
    `<div class="flex justify-between"><span class="text-gray-500">${k}</span><span class="text-gray-200 font-medium">${v}</span></div>`
  ).join('');
}

// ── Step Navigation ────────────────────────────────────────────────
function goToStep(n) {
  if (n > S.step + 1) return; // Can't skip ahead
  if (n > S.step && !validateStep(S.step)) return;
  S.step = n;
  renderStep();
}

function nextStep() {
  if (!validateStep(S.step)) return;
  if (S.step < 3) { S.step++; renderStep(); }
}

function prevStep() {
  if (S.step > 0) { S.step--; renderStep(); }
}

function renderStep() {
  // Panels
  document.querySelectorAll('.step-panel').forEach((p, i) => {
    p.classList.toggle('hidden', i !== S.step);
    if (i === S.step) { p.classList.remove('slide-in'); void p.offsetWidth; p.classList.add('slide-in'); }
  });
  // Dots
  document.querySelectorAll('.step-dot').forEach((d, i) => {
    d.classList.remove('active', 'done');
    d.classList.toggle('done', i < S.step);
    d.classList.toggle('active', i === S.step);
    d.querySelector ? null : null;
    d.style.color = i <= S.step ? '#fff' : '';
  });
  // Progress line
  document.getElementById('progressLine').style.width = ((S.step + 0.5) / 4 * 100) + '%';
  // Buttons
  document.getElementById('btnPrev').classList.toggle('hidden', S.step === 0);
  document.getElementById('btnNext').classList.toggle('hidden', S.step === 3);
  document.getElementById('btnSubmit').classList.toggle('hidden', S.step !== 3);
  // Build review on step 4
  if (S.step === 3) buildReview();
  // Scroll top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Validation ─────────────────────────────────────────────────────
function validateStep(n) {
  if (n === 0) {
    if (!S.gameId) { showToastError('Please select a game'); return false; }
    if (!document.getElementById('tournamentName').value.trim()) {
      showToastError('Please enter a tournament name'); return false;
    }
    S.name = document.getElementById('tournamentName').value.trim();
    return true;
  }
  if (n === 1) {
    S.regStart = document.getElementById('regStart').value;
    S.regEnd = document.getElementById('regEnd').value;
    S.tourStart = document.getElementById('tourStart').value;
    if (!S.regStart || !S.regEnd || !S.tourStart) {
      showToastError('Please fill in all required dates'); return false;
    }
    if (new Date(S.regStart) >= new Date(S.regEnd)) {
      showToastError('Registration start must be before end'); return false;
    }
    if (new Date(S.regEnd) >= new Date(S.tourStart)) {
      showToastError('Registration must end before tournament starts'); return false;
    }
    return true;
  }
  if (n === 2) {
    S.description = document.getElementById('description').value;
    S.rulesText = document.getElementById('rulesText').value;
    S.entryFeeAmount = parseFloat(document.getElementById('entryFeeAmount').value) || 0;
    S.entryFeeCurrency = document.getElementById('entryFeeCurrency').value;
    S.prizePool = parseFloat(document.getElementById('prizePool').value) || 0;
    S.prizeCurrency = document.getElementById('prizeCurrency').value;
    return true;
  }
  return true;
}

// ── Review Builder ─────────────────────────────────────────────────
function buildReview() {
  const g = GAMES.find(x => x.id === S.gameId);
  const rows = [
    ['🎮 Game', g ? g.display_name : '—'],
    ['📝 Name', S.name],
    ['👥 Type', S.participation === 'team' ? `Team (${g?.team_size_display||'5v5'})` : 'Solo (1v1)'],
    ['🏆 Format', S.format.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())],
    ['📊 Capacity', S.capacity],
    ['💻 Platform', S.platform.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase())],
    ['📅 Reg Opens', formatDate(S.regStart)],
    ['📅 Reg Closes', formatDate(S.regEnd)],
    ['📅 Tournament', formatDate(S.tourStart)],
    ['💰 Entry Fee', S.hasEntryFee ? `${S.entryFeeAmount} ${S.entryFeeCurrency}` : 'Free'],
    ['🏅 Prize Pool', S.prizePool > 0 ? `${S.prizePool} ${S.prizeCurrency}` : 'None'],
  ];
  document.getElementById('reviewContent').innerHTML = rows.map(([k,v]) => `
    <div class="flex justify-between items-center py-2.5 border-b border-white/5 last:border-0">
      <span class="text-sm text-gray-400">${k}</span>
      <span class="text-sm font-medium text-white">${v}</span>
    </div>
  `).join('');
}

// ── Submit ─────────────────────────────────────────────────────────
async function submitTournament() {
  if (!validateStep(0) || !validateStep(1) || !validateStep(2)) return;

  const overlay = document.getElementById('loadingOverlay');
  overlay.classList.remove('hidden');

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
  const payload = {
    name: S.name,
    game_id: S.gameId,
    format: S.format,
    participation_type: S.participation,
    max_participants: S.capacity,
    min_participants: 2,
    platform: S.platform,
    registration_start: new Date(S.regStart).toISOString(),
    registration_end: new Date(S.regEnd).toISOString(),
    tournament_start: new Date(S.tourStart).toISOString(),
    description: S.description || '',
    rules_text: S.rulesText || '',
    has_entry_fee: S.hasEntryFee,
    entry_fee_amount: S.hasEntryFee ? S.entryFeeAmount : 0,
    entry_fee_currency: S.entryFeeCurrency,
    prize_pool: S.prizePool || 0,
    prize_currency: S.prizeCurrency,
  };
  if (S.tourEnd) payload.tournament_end = new Date(S.tourEnd).toISOString();

  try {
    const resp = await fetch('/api/tournaments/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (resp.ok) {
      const slug = data.slug || data.tournament?.slug || '';
      if (window.showToast) window.showToast({ type: 'success', message: 'Tournament created!' });
      setTimeout(() => { window.location.href = slug ? `/toc/${slug}/?onboarding=true` : '/tournaments/my/'; }, 800);
    } else {
      overlay.classList.add('hidden');
      const errMsg = data.detail || data.error || Object.values(data).flat().join(', ') || 'Creation failed';
      showToastError(errMsg);
    }
  } catch (e) {
    overlay.classList.add('hidden');
    showToastError('Network error. Please try again.');
  }
}

// ── Helpers ────────────────────────────────────────────────────────
function slugify(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80); }
function toLocalISO(d) { return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16); }
function formatDate(s) { if (!s) return '—'; return new Date(s).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',hour:'2-digit',minute:'2-digit'}); }
function hexToRgb(h) { const r=parseInt(h.slice(1,3),16),g=parseInt(h.slice(3,5),16),b=parseInt(h.slice(5,7),16); return `${r},${g},${b}`; }
function showToastError(msg) { if (window.showToast) window.showToast({type:'error',message:msg}); else alert(msg); }
