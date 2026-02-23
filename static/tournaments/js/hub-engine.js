/**
 * ═══════════════════════════════════════════════════════════
 * THE HUB — SPA State Engine
 * DeltaCrown Sprint 12
 *
 * Responsibilities:
 *  • Tab switching (zero full-page reloads)
 *  • API polling (state / announcements every N seconds)
 *  • Countdown timer (phase events)
 *  • Check-in action (POST)
 *  • Mobile sidebar toggle
 *  • Dynamic DOM updates from poll data
 * ═══════════════════════════════════════════════════════════
 */

const HubEngine = (() => {
  // ── Config ──────────────────────────────────────────────
  const POLL_STATE_INTERVAL   = 20_000;   // 20s
  const POLL_ANN_INTERVAL     = 45_000;   // 45s
  const COUNTDOWN_TICK        = 1_000;    // 1s

  // ── State ───────────────────────────────────────────────
  let _shell       = null;
  let _currentTab  = 'overview';
  let _pollStateId = null;
  let _pollAnnId   = null;
  let _countdownId = null;
  let _csrfToken   = '';

  // Lazy-load caches (fetched once per session)
  let _prizesCache       = null;
  let _resourcesCache    = null;
  let _bracketCache      = null;
  let _standingsCache    = null;
  let _matchesCache      = null;
  let _participantsCache = null;
  let _participantsAll   = [];  // for search filtering

  // ── Init ────────────────────────────────────────────────
  function init() {
    _shell = document.getElementById('hub-shell');
    if (!_shell) return;

    _csrfToken = _getCookie('csrftoken');

    // Start countdown
    _startCountdown();

    // Start polling
    _pollStateId = setInterval(_pollState, POLL_STATE_INTERVAL);
    _pollAnnId   = setInterval(_pollAnnouncements, POLL_ANN_INTERVAL);

    // Keyboard: Escape closes mobile sidebar + modals
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeMobileSidebar();
        closeContactModal();
        closeStatusModal();
        dismissGuide();
      }
    });

    // First-visit welcome guide
    setTimeout(_checkWelcomeGuide, 500);
  }

  // ──────────────────────────────────────────────────────────
  // Tab Switching
  // ──────────────────────────────────────────────────────────
  function switchTab(tabId) {
    if (tabId === _currentTab) return;

    // Hide all tab contents
    document.querySelectorAll('.hub-tab-content').forEach(el => {
      el.classList.remove('active');
    });

    // Show target
    const target = document.getElementById('hub-tab-' + tabId);
    if (target) {
      target.classList.add('active');
    }

    // Update sidebar nav buttons (both desktop + mobile copies)
    document.querySelectorAll('.hub-nav-btn').forEach(btn => {
      const btnTab = btn.getAttribute('data-hub-tab');
      if (btnTab === tabId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    _currentTab = tabId;

    // Scroll content to top
    const viewport = document.getElementById('hub-viewport');
    if (viewport) viewport.scrollTo({ top: 0, behavior: 'smooth' });

    // Close mobile sidebar if open
    closeMobileSidebar();

    // Async data fetch for lazy tabs
    if (tabId === 'prizes' && !_prizesCache) {
      _fetchPrizes();
    }
    if (tabId === 'resources' && !_resourcesCache) {
      _fetchResources();
    }
    if (tabId === 'bracket' && !_bracketCache) {
      _fetchBracket();
    }
    if (tabId === 'standings' && !_standingsCache) {
      _fetchStandings();
    }
    if (tabId === 'matches' && !_matchesCache) {
      _fetchMatches();
    }
    if (tabId === 'participants' && !_participantsCache) {
      _fetchParticipants();
    }

    // Re-init lucide icons for dynamic content
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ──────────────────────────────────────────────────────────
  // Mobile Sidebar
  // ──────────────────────────────────────────────────────────
  function openMobileSidebar() {
    const overlay = document.getElementById('hub-mobile-overlay');
    const sidebar = document.getElementById('hub-mobile-sidebar');
    if (overlay) overlay.classList.add('open');
    if (sidebar) sidebar.classList.add('open');
  }

  function closeMobileSidebar() {
    const overlay = document.getElementById('hub-mobile-overlay');
    const sidebar = document.getElementById('hub-mobile-sidebar');
    if (overlay) overlay.classList.remove('open');
    if (sidebar) sidebar.classList.remove('open');
  }

  // ──────────────────────────────────────────────────────────
  // Countdown Timer
  // ──────────────────────────────────────────────────────────
  function _startCountdown() {
    const el = document.getElementById('hub-countdown');
    if (!el) return;

    const targetISO = el.getAttribute('data-target');
    if (!targetISO) return;

    const targetDate = new Date(targetISO);

    function tick() {
      const now  = new Date();
      const diff = targetDate - now;

      if (diff <= 0) {
        _setCountdown('00', '00', '00');
        clearInterval(_countdownId);
        // Trigger state refresh
        _pollState();
        return;
      }

      const totalSec = Math.floor(diff / 1000);
      const h = String(Math.floor(totalSec / 3600)).padStart(2, '0');
      const m = String(Math.floor((totalSec % 3600) / 60)).padStart(2, '0');
      const s = String(totalSec % 60).padStart(2, '0');
      _setCountdown(h, m, s);
    }

    tick(); // immediate first tick
    _countdownId = setInterval(tick, COUNTDOWN_TICK);
  }

  function _setCountdown(h, m, s) {
    const hEl = document.getElementById('hub-cd-hours');
    const mEl = document.getElementById('hub-cd-minutes');
    const sEl = document.getElementById('hub-cd-seconds');
    if (hEl) hEl.textContent = h;
    if (mEl) mEl.textContent = m;
    if (sEl) sEl.textContent = s;
  }

  // ──────────────────────────────────────────────────────────
  // Check-In Action
  // ──────────────────────────────────────────────────────────
  async function performCheckIn() {
    const url = _shell?.dataset.apiCheckin;
    if (!url) return;

    // Disable buttons
    document.querySelectorAll('#hub-checkin-btn, #hub-checkin-btn-lobby').forEach(btn => {
      btn.disabled = true;
      btn.textContent = 'Checking in...';
    });

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': _csrfToken,
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
      });

      const data = await resp.json();

      if (data.success) {
        // Update buttons to "done" state
        document.querySelectorAll('#hub-checkin-btn, #hub-checkin-btn-lobby').forEach(btn => {
          btn.className = 'hub-checkin-btn done clip-slant w-full lg:w-auto flex items-center justify-center gap-3';
          btn.innerHTML = '<i data-lucide="check" class="w-5 h-5"></i> Checked In';
          btn.disabled = true;
          btn.onclick = null;
        });

        // Update shell data attribute
        if (_shell) _shell.dataset.isCheckedIn = 'true';

        // Show toast if available
        if (window.showToast) {
          window.showToast({ type: 'success', message: 'Successfully checked in!' });
        }

        // Re-init icons
        if (typeof lucide !== 'undefined') lucide.createIcons();

        // Refresh state
        _pollState();
      } else {
        const errMsg = data.error || 'Check-in failed. Please try again.';
        if (window.showToast) {
          window.showToast({ type: 'error', message: errMsg });
        }
        // Re-enable buttons
        document.querySelectorAll('#hub-checkin-btn, #hub-checkin-btn-lobby').forEach(btn => {
          btn.disabled = false;
          btn.innerHTML = '<i data-lucide="check-circle" class="w-5 h-5"></i> Check In Now';
        });
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    } catch (err) {
      console.error('[HubEngine] Check-in error:', err);
      if (window.showToast) {
        window.showToast({ type: 'error', message: 'Network error. Please try again.' });
      }
      document.querySelectorAll('#hub-checkin-btn, #hub-checkin-btn-lobby').forEach(btn => {
        btn.disabled = false;
        btn.innerHTML = '<i data-lucide="check-circle" class="w-5 h-5"></i> Check In Now';
      });
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }
  }

  // ──────────────────────────────────────────────────────────
  // State Polling
  // ──────────────────────────────────────────────────────────
  async function _pollState() {
    const url = _shell?.dataset.apiState;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) return;
      const data = await resp.json();

      // Update reg count
      const regEl = document.getElementById('hub-reg-count');
      if (regEl && data.reg_count !== undefined) {
        regEl.textContent = data.reg_count;
      }

      // Update user status label
      const statusEl = document.getElementById('hub-status-label');
      if (statusEl && data.user_status) {
        statusEl.textContent = data.user_status;
      }

      // Update check-in state if it changed
      if (data.check_in) {
        const shellChecked = _shell?.dataset.isCheckedIn === 'true';
        if (data.check_in.is_checked_in && !shellChecked) {
          _shell.dataset.isCheckedIn = 'true';
          // Could trigger UI update here
        }
      }

      // Update countdown target if phase changed
      if (data.phase_event && data.phase_event.target) {
        const cdEl = document.getElementById('hub-countdown');
        if (cdEl) {
          const current = cdEl.getAttribute('data-target');
          if (current !== data.phase_event.target) {
            cdEl.setAttribute('data-target', data.phase_event.target);
            // Restart countdown
            if (_countdownId) clearInterval(_countdownId);
            _startCountdown();
          }
        }
      }

    } catch (err) {
      console.warn('[HubEngine] State poll failed:', err.message);
    }
  }

  // ──────────────────────────────────────────────────────────
  // Announcements Polling
  // ──────────────────────────────────────────────────────────
  async function _pollAnnouncements() {
    const url = _shell?.dataset.apiAnnouncements;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) return;
      const data = await resp.json();

      if (!data.announcements || !data.announcements.length) return;

      const feed = document.getElementById('hub-announcements-feed');
      if (!feed) return;

      // Rebuild feed
      const html = data.announcements.map((ann, i) => {
        const dotClass = ann.type === 'urgent' ? 'ann-dot-urgent'
                       : ann.type === 'warning' ? 'ann-dot-warning'
                       : ann.type === 'success' ? 'ann-dot-success'
                       : 'ann-dot-info';

        const typeClass = ann.type === 'urgent' ? 'bg-[#FF2A55]/20 text-[#FF2A55]'
                        : ann.type === 'warning' ? 'bg-[#FFB800]/20 text-[#FFB800]'
                        : ann.type === 'success' ? 'bg-[#00FF66]/20 text-[#00FF66]'
                        : 'bg-white/10 text-gray-300';

        const isLast = i === data.announcements.length - 1;

        return `
          <div class="relative pl-6 border-l border-white/5 ${isLast ? '' : 'pb-6'}">
            <div class="absolute left-0 top-1.5 w-2 h-2 rounded-full -ml-[5px] ${dotClass}"></div>
            <div class="flex items-center gap-2 mb-1 flex-wrap">
              ${ann.is_pinned ? '<span class="px-1.5 py-0.5 rounded bg-[#FFB800]/20 text-[#FFB800] text-[8px] font-black uppercase">Pinned</span>' : ''}
              <span class="px-1.5 py-0.5 rounded ${typeClass} text-[8px] font-black uppercase">${_esc(ann.type || 'Info')}</span>
              <span class="text-[10px] text-gray-500" style="font-family:'Space Grotesk',monospace;">${_esc(ann.time_ago)}</span>
            </div>
            ${ann.title ? `<p class="font-bold text-white text-sm mb-1">${_esc(ann.title)}</p>` : ''}
            <p class="text-xs text-gray-400 leading-relaxed">${_esc(ann.message)}</p>
          </div>`;
      }).join('');

      feed.innerHTML = html;

      // Update count
      const countEl = document.getElementById('hub-ann-count');
      if (countEl) {
        const n = data.announcements.length;
        countEl.textContent = `${n} update${n !== 1 ? 's' : ''}`;
      }

    } catch (err) {
      console.warn('[HubEngine] Announcements poll failed:', err.message);
    }
  }

  // ──────────────────────────────────────────────────────────
  // Squad Management — Roster Slot Swaps
  // ──────────────────────────────────────────────────────────
  async function swapToSub(membershipId) {
    await _swapSlot(membershipId, 'SUBSTITUTE');
  }

  async function swapToStarter(membershipId) {
    await _swapSlot(membershipId, 'STARTER');
  }

  async function _swapSlot(membershipId, newSlot) {
    const url = _shell?.dataset.apiSquad;
    if (!url) return;

    // Find and disable the button
    const card = document.querySelector(`[data-member-id="${membershipId}"]`);
    const btn = card?.querySelector('.squad-swap-btn');
    if (btn) {
      btn.classList.add('loading');
      btn.disabled = true;
    }

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': _csrfToken,
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          membership_id: membershipId,
          new_slot: newSlot,
        }),
      });

      const data = await resp.json();

      if (data.success) {
        _showSquadToast(`${data.display_name} moved to ${newSlot.toLowerCase()}`);
        // Reload the page to reflect changes (simplest approach for server-rendered content)
        setTimeout(() => window.location.reload(), 800);
      } else {
        _showSquadToast(data.error || 'Swap failed', true);
        if (btn) {
          btn.classList.remove('loading');
          btn.disabled = false;
        }
      }
    } catch (err) {
      console.error('[HubEngine] Squad swap error:', err);
      _showSquadToast('Network error. Please try again.', true);
      if (btn) {
        btn.classList.remove('loading');
        btn.disabled = false;
      }
    }
  }

  function _showSquadToast(message, isError = false) {
    const toast = document.getElementById('squad-toast');
    const msgEl = document.getElementById('squad-toast-msg');
    if (!toast || !msgEl) {
      // Fallback to global toast
      if (window.showToast) {
        window.showToast({ type: isError ? 'error' : 'success', message });
      }
      return;
    }

    msgEl.textContent = message;
    const inner = toast.querySelector('div');
    if (inner) {
      if (isError) {
        inner.className = 'px-6 py-3 rounded-xl bg-[#FF2A55]/10 border border-[#FF2A55]/20 backdrop-blur-xl shadow-2xl flex items-center gap-3';
      } else {
        inner.className = 'px-6 py-3 rounded-xl bg-[#00FF66]/10 border border-[#00FF66]/20 backdrop-blur-xl shadow-2xl flex items-center gap-3';
      }
    }

    toast.classList.remove('hidden');
    setTimeout(() => toast.classList.add('hidden'), 3000);
  }

  // ──────────────────────────────────────────────────────────
  // Bracket Zoom Controls
  // ──────────────────────────────────────────────────────────
  let _bracketScale = 1;

  function bracketZoom(dir) {
    const tree = document.getElementById('hub-bracket-tree');
    if (!tree) return;
    _bracketScale = Math.max(0.3, Math.min(2, _bracketScale + dir * 0.2));
    tree.style.transform = `scale(${_bracketScale})`;
  }

  function bracketReset() {
    const tree = document.getElementById('hub-bracket-tree');
    if (!tree) return;
    _bracketScale = 1;
    tree.style.transform = 'scale(1)';
  }

  // ──────────────────────────────────────────────────────────
  // Prizes Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchPrizes() {
    const url = _shell?.dataset.apiPrizeClaim;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _prizesCache = data;
      _renderPrizes(data);
    } catch (err) {
      console.warn('[HubEngine] Prizes fetch failed:', err.message);
      // Show empty state
      _hide('prize-pool-skeleton');
      _hide('prize-dist-skeleton');
      _show('prize-empty-state');
    }
  }

  function _renderPrizes(data) {
    // ── Prize Pool ──
    _hide('prize-pool-skeleton');
    const poolContent = document.getElementById('prize-pool-content');
    if (poolContent) {
      const amt = parseFloat(data.prize_pool?.total || 0);
      document.getElementById('prize-pool-amount').textContent = amt > 0 ? _formatNumber(amt) : '—';
      document.getElementById('prize-pool-currency').textContent = data.prize_pool?.currency || 'BDT';
      document.getElementById('prize-deltacoin').textContent = _formatNumber(data.prize_pool?.deltacoin || 0);
      poolContent.classList.remove('hidden');
    }

    // Tournament status badge
    const statusEl = document.getElementById('prize-tournament-status');
    if (statusEl && data.tournament_status) {
      const s = data.tournament_status;
      const cls = s === 'live' ? 'live' : s === 'completed' ? 'neutral' : 'info';
      statusEl.className = `hub-badge hub-badge-${cls}`;
      statusEl.textContent = s.charAt(0).toUpperCase() + s.slice(1);
    }

    // ── Distribution Breakdown ──
    _hide('prize-dist-skeleton');
    const distContent = document.getElementById('prize-dist-content');
    if (distContent) {
      const dist = data.prize_pool?.distribution || {};
      const entries = Object.entries(dist);

      if (entries.length > 0) {
        let html = '';
        entries.forEach(([place, share]) => {
          const cardClass = place === '1' ? 'gold' : place === '2' ? 'silver' : place === '3' ? 'bronze' : '';
          const emoji = place === '1' ? '🥇' : place === '2' ? '🥈' : place === '3' ? '🥉' : '🏅';
          const label = _ordinal(place) + ' Place';
          html += `
            <div class="prize-placement-card ${cardClass}">
              <div class="text-lg mb-1">${emoji}</div>
              <p class="text-xs font-bold text-white">${_esc(label)}</p>
              <p class="text-lg font-black text-[#FFB800]" style="font-family:Outfit,sans-serif;">${_esc(String(share))}</p>
            </div>`;
        });
        distContent.innerHTML = html;
        distContent.classList.remove('hidden');
      }

      // Also render from overview aggregates if available
      if (data.overview && data.overview.length > 0 && entries.length === 0) {
        let html = '';
        data.overview.forEach(row => {
          html += `
            <div class="prize-placement-card">
              <p class="text-xs font-bold text-white">${_esc(row.placement)}</p>
              <p class="text-lg font-black text-[#FFB800]" style="font-family:Outfit,sans-serif;">${_formatNumber(parseFloat(row.total))}</p>
              <p class="text-[10px] text-gray-500">${row.count} recipient${row.count !== 1 ? 's' : ''}</p>
            </div>`;
        });
        distContent.innerHTML = html;
        distContent.classList.remove('hidden');
      }
    }

    // ── Your Prizes ──
    if (data.your_prizes && data.your_prizes.length > 0) {
      const section = document.getElementById('your-prizes-section');
      const list = document.getElementById('your-prizes-list');
      if (section && list) {
        let html = '';
        data.your_prizes.forEach(p => {
          const claimedBadge = p.claimed
            ? `<span class="hub-badge hub-badge-${p.claim_status === 'paid' ? 'live' : p.claim_status === 'rejected' ? 'danger' : 'warning'}">${_esc(p.claim_status)}</span>`
            : '';
          const claimBtn = !p.claimed
            ? `<button class="prize-claim-btn" onclick="HubEngine.openPrizeModal(${p.id}, '${_esc(p.amount)}', '${_esc(p.placement_display)}')">Claim Prize</button>`
            : '';

          html += `
            <div class="prize-your-card">
              <div>
                <p class="text-sm font-bold text-white">${_esc(p.placement_display)}</p>
                <p class="text-xs text-gray-400 mt-0.5">Amount: <span class="text-[#FFB800] font-bold">${_formatNumber(parseFloat(p.amount))}</span></p>
              </div>
              <div class="flex items-center gap-3">
                ${claimedBadge}
                ${claimBtn}
              </div>
            </div>`;
        });
        list.innerHTML = html;
        section.classList.remove('hidden');
      }
    }

    // ── Empty check ──
    const hasPool = parseFloat(data.prize_pool?.total || 0) > 0 || (data.prize_pool?.deltacoin || 0) > 0;
    const hasPrizes = data.your_prizes && data.your_prizes.length > 0;
    const hasOverview = data.overview && data.overview.length > 0;
    if (!hasPool && !hasPrizes && !hasOverview) {
      _show('prize-empty-state');
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ── Prize Claim Modal ──
  function openPrizeModal(txId, amount, placement) {
    document.getElementById('claim-transaction-id').value = txId;
    document.getElementById('claim-modal-amount').textContent = amount;
    document.getElementById('claim-modal-placement').textContent = placement;
    document.getElementById('claim-error').classList.add('hidden');
    document.getElementById('claim-success').classList.add('hidden');
    document.getElementById('claim-submit-btn').disabled = false;

    // Show/hide destination field based on method
    _onPayoutMethodChange();
    const select = document.getElementById('claim-payout-method');
    if (select) {
      select.removeEventListener('change', _onPayoutMethodChange);
      select.addEventListener('change', _onPayoutMethodChange);
    }

    document.getElementById('prize-claim-modal').classList.remove('hidden');
  }

  function closePrizeModal() {
    document.getElementById('prize-claim-modal').classList.add('hidden');
  }

  function _onPayoutMethodChange() {
    const method = document.getElementById('claim-payout-method')?.value;
    const wrap = document.getElementById('claim-destination-wrap');
    if (wrap) {
      wrap.classList.toggle('hidden', method === 'deltacoin');
    }
  }

  async function submitPrizeClaim() {
    const url = _shell?.dataset.apiPrizeClaim;
    if (!url) return;

    const txId = document.getElementById('claim-transaction-id').value;
    const method = document.getElementById('claim-payout-method').value;
    const dest = document.getElementById('claim-payout-destination')?.value || '';
    const btn = document.getElementById('claim-submit-btn');
    const errEl = document.getElementById('claim-error');
    const okEl = document.getElementById('claim-success');

    btn.disabled = true;
    btn.textContent = 'Submitting...';
    errEl.classList.add('hidden');
    okEl.classList.add('hidden');

    try {
      const resp = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': _csrfToken,
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          transaction_id: parseInt(txId),
          payout_method: method,
          payout_destination: dest,
        }),
      });

      const data = await resp.json();

      if (data.success) {
        okEl.textContent = 'Prize claimed successfully! Your payout is being processed.';
        okEl.classList.remove('hidden');
        btn.textContent = 'Claimed';
        // Refresh cache
        _prizesCache = null;
        setTimeout(() => {
          closePrizeModal();
          _fetchPrizes();
        }, 1500);
      } else {
        errEl.textContent = data.error || 'Failed to claim prize.';
        errEl.classList.remove('hidden');
        btn.disabled = false;
        btn.textContent = 'Submit Claim';
      }
    } catch (err) {
      console.error('[HubEngine] Prize claim error:', err);
      errEl.textContent = 'Network error. Please try again.';
      errEl.classList.remove('hidden');
      btn.disabled = false;
      btn.textContent = 'Submit Claim';
    }
  }

  // ──────────────────────────────────────────────────────────
  // Resources Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchResources() {
    const url = _shell?.dataset.apiResources;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _resourcesCache = data;
      _renderResources(data);
    } catch (err) {
      console.warn('[HubEngine] Resources fetch failed:', err.message);
      _hide('rules-skeleton');
      _show('resources-empty-state');
    }
  }

  function _renderResources(data) {
    _hide('rules-skeleton');

    const hasRules = data.rules?.text || data.rules?.pdf_url;
    const hasSocial = data.social_links && data.social_links.length > 0;
    const hasSponsors = data.sponsors && data.sponsors.length > 0;
    const hasContact = !!data.contact_email;

    if (!hasRules && !hasSocial && !hasSponsors && !hasContact) {
      _show('resources-empty-state');
      return;
    }

    // ── Rules ──
    if (hasRules) {
      const rulesContent = document.getElementById('rules-content');
      if (rulesContent) rulesContent.classList.remove('hidden');

      // PDF link
      if (data.rules.pdf_url) {
        const pdfLink = document.getElementById('rules-pdf-link');
        if (pdfLink) pdfLink.classList.remove('hidden');
        const pdfUrl = document.getElementById('rules-pdf-url');
        if (pdfUrl) pdfUrl.href = data.rules.pdf_url;
      }

      // Rules text
      if (data.rules.text) {
        const textEl = document.getElementById('rules-text-content');
        if (textEl) {
          textEl.innerHTML = _renderSimpleMarkdown(data.rules.text);
        }
      }

      // Terms
      if (data.rules.terms) {
        const termsSec = document.getElementById('terms-section');
        const termsText = document.getElementById('terms-text-content');
        if (termsSec) termsSec.classList.remove('hidden');
        if (termsText) termsText.textContent = data.rules.terms;
      }
    } else {
      _show('rules-empty');
    }

    // ── Social Links ──
    if (hasSocial || hasContact) {
      const socialSection = document.getElementById('resources-social-section');
      if (socialSection) socialSection.classList.remove('hidden');

      const grid = document.getElementById('social-links-grid');
      if (grid && hasSocial) {
        const iconMap = {
          discord: 'message-circle', twitter: 'twitter', instagram: 'instagram',
          youtube: 'youtube', website: 'globe', twitch: 'tv', youtube_stream: 'play-circle',
        };
        let html = '';
        data.social_links.forEach(link => {
          const icon = iconMap[link.key] || 'link';
          html += `
            <a href="${_esc(link.url)}" target="_blank" rel="noopener" class="social-link-card">
              <div class="social-icon ${_esc(link.key)}">
                <i data-lucide="${icon}" class="w-4 h-4"></i>
              </div>
              <span>${_esc(link.label)}</span>
            </a>`;
        });
        grid.innerHTML = html;
      }

      if (hasContact) {
        const emailRow = document.getElementById('contact-email-row');
        const emailLink = document.getElementById('contact-email-link');
        const emailText = document.getElementById('contact-email-text');
        if (emailRow) emailRow.classList.remove('hidden');
        if (emailLink) emailLink.href = 'mailto:' + data.contact_email;
        if (emailText) emailText.textContent = data.contact_email;
      }
    }

    // ── Sponsors ──
    if (hasSponsors) {
      const sponsorsSection = document.getElementById('resources-sponsors-section');
      if (sponsorsSection) sponsorsSection.classList.remove('hidden');

      const tierMap = { title: 'sponsors-title', gold: 'sponsors-gold', silver: 'sponsors-silver', bronze: 'sponsors-bronze', partner: 'sponsors-partner' };
      const tierGridMap = { title: 'sponsors-title', gold: 'sponsors-gold-grid', silver: 'sponsors-silver-grid', bronze: 'sponsors-bronze-grid', partner: 'sponsors-partner-grid' };

      // Group sponsors by tier
      const grouped = {};
      data.sponsors.forEach(s => {
        if (!grouped[s.tier]) grouped[s.tier] = [];
        grouped[s.tier].push(s);
      });

      Object.entries(grouped).forEach(([tier, sponsors]) => {
        const wrapper = document.getElementById(tierMap[tier]);
        const grid = document.getElementById(tierGridMap[tier]);
        if (!wrapper) return;
        wrapper.classList.remove('hidden');

        const target = grid || wrapper;
        let html = '';

        sponsors.forEach(s => {
          const isTitle = tier === 'title';
          const cardClass = isTitle ? 'sponsor-card title-sponsor' : 'sponsor-card';
          const img = s.banner_url || s.logo_url;
          const imgTag = img
            ? `<img src="${_esc(img)}" alt="${_esc(s.name)}" class="${isTitle ? 'h-16 p-4' : 'h-10 p-2'} object-contain mx-auto">`
            : `<div class="h-10 flex items-center justify-center text-sm font-bold text-gray-400">${_esc(s.name)}</div>`;

          const link = s.website_url ? `href="${_esc(s.website_url)}" target="_blank" rel="noopener"` : '';
          html += `
            <a ${link} class="${cardClass}">
              ${imgTag}
              <div class="sponsor-info">
                <p class="sponsor-name">${_esc(s.name)}</p>
                ${s.description ? `<p class="text-[10px] text-gray-500 mt-0.5 line-clamp-2">${_esc(s.description)}</p>` : ''}
              </div>
            </a>`;
        });
        target.innerHTML = html;
      });
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // Smart content renderer: detects HTML vs plain/markdown
  function _renderSimpleMarkdown(text) {
    if (!text) return '';

    // Detect if content is already HTML (starts with a tag or contains common block tags)
    const trimmed = text.trim();
    if (/^<[a-z][\s\S]*>/i.test(trimmed) || /<(p|div|h[1-6]|ul|ol|li|br|table|blockquote)\b/i.test(trimmed)) {
      // Content is HTML — render directly (trusted content from admin)
      return trimmed;
    }

    // Plain text / markdown — escape then transform
    let html = _esc(text);
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h4 class="text-sm font-bold text-white mt-4 mb-1">$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3 class="text-base font-bold text-white mt-5 mb-2">$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2 class="text-lg font-bold text-white mt-6 mb-2">$1</h2>');
    // Bold / italic
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Lists
    html = html.replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>');
    html = html.replace(/^(\d+)\. (.+)$/gm, '<li class="ml-4 list-decimal">$2</li>');
    // Line breaks → paragraphs
    html = html.replace(/\n\n/g, '</p><p class="mb-2">');
    html = html.replace(/\n/g, '<br>');
    html = '<p class="mb-2">' + html + '</p>';
    return html;
  }

  // ── DOM helpers ──
  function _show(id) { const el = document.getElementById(id); if (el) el.classList.remove('hidden'); }
  function _hide(id) { const el = document.getElementById(id); if (el) el.classList.add('hidden'); }
  function _formatNumber(n) { return n.toLocaleString('en-US', { maximumFractionDigits: 2 }); }
  function _ordinal(n) {
    const num = parseInt(n);
    if (isNaN(num)) return n;
    const s = ['th', 'st', 'nd', 'rd'];
    const v = num % 100;
    return num + (s[(v - 20) % 10] || s[v] || s[0]);
  }

  // ──────────────────────────────────────────────────────────
  // Utilities
  // ──────────────────────────────────────────────────────────
  function _getCookie(name) {
    const cookies = document.cookie.split(';');
    for (const c of cookies) {
      const [k, v] = c.trim().split('=');
      if (k === name) return decodeURIComponent(v);
    }
    return '';
  }

  function _esc(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ──────────────────────────────────────────────────────────
  // Bracket Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchBracket() {
    const url = _shell?.dataset.apiBracket;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _bracketCache = data;
      _renderBracket(data);
    } catch (err) {
      console.warn('[HubEngine] Bracket fetch failed:', err.message);
      _hide('bracket-skeleton');
      _show('bracket-not-generated');
    }
  }

  function _renderBracket(data) {
    _hide('bracket-skeleton');

    if (!data.generated || !data.rounds || data.rounds.length === 0) {
      _show('bracket-not-generated');
      return;
    }

    // Show zoom controls
    _show('bracket-zoom-controls');

    // Update format label
    const fmtEl = document.getElementById('bracket-format-label');
    if (fmtEl && data.format_display) fmtEl.textContent = data.format_display;

    const tree = document.getElementById('hub-bracket-tree');
    if (!tree) return;

    let html = '<div class="bracket-rounds-flex">';

    data.rounds.forEach((round, ri) => {
      html += `<div class="bracket-round">`;
      html += `<div class="bracket-round-header">${_esc(round.round_name)}</div>`;
      html += `<div class="bracket-round-matches">`;

      round.matches.forEach(m => {
        const liveClass = m.state === 'live' ? ' bracket-match-live' : '';
        const doneClass = m.state === 'completed' || m.state === 'forfeit' ? ' bracket-match-done' : '';
        html += `<div class="bracket-match-card${liveClass}${doneClass}">`;

        // Participant 1
        const p1Win = m.participant1.is_winner ? ' bracket-winner' : '';
        html += `<div class="bracket-participant${p1Win}">`;
        html += `<span class="bracket-p-name">${_esc(m.participant1.name)}</span>`;
        html += `<span class="bracket-p-score">${m.participant1.score}</span>`;
        html += `</div>`;

        // Participant 2
        const p2Win = m.participant2.is_winner ? ' bracket-winner' : '';
        html += `<div class="bracket-participant${p2Win}">`;
        html += `<span class="bracket-p-name">${_esc(m.participant2.name)}</span>`;
        html += `<span class="bracket-p-score">${m.participant2.score}</span>`;
        html += `</div>`;

        // State badge
        if (m.state === 'live') {
          html += `<div class="bracket-match-badge live"><span class="w-1.5 h-1.5 rounded-full bg-[#FF2A55] animate-pulse inline-block"></span> LIVE</div>`;
        } else if (m.state === 'completed') {
          html += `<div class="bracket-match-badge done">Final</div>`;
        }

        html += `</div>`; // match-card
      });

      html += `</div></div>`; // matches, round
    });

    html += '</div>';
    tree.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ──────────────────────────────────────────────────────────
  // Standings Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchStandings() {
    const url = _shell?.dataset.apiStandings;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _standingsCache = data;
      _renderStandings(data);
    } catch (err) {
      console.warn('[HubEngine] Standings fetch failed:', err.message);
      _hide('standings-skeleton');
      _show('standings-empty');
    }
  }

  function _renderStandings(data) {
    _hide('standings-skeleton');

    if (!data.has_standings || !data.groups || data.groups.length === 0) {
      _show('standings-empty');
      return;
    }

    _show('standings-format-badge');
    const container = document.getElementById('hub-standings-container');
    if (!container) return;

    let html = '';
    data.groups.forEach(group => {
      html += `<div class="standings-group">`;
      html += `<h3 class="text-sm font-black text-white uppercase tracking-widest mb-4 flex items-center gap-2">`;
      html += `<i data-lucide="flag" class="w-4 h-4 text-[#00F0FF]"></i> ${_esc(group.name)}</h3>`;

      html += `<div class="hub-glass rounded-xl overflow-hidden">`;
      html += `<table class="standings-table w-full">`;
      html += `<thead><tr>`;
      html += `<th class="standings-th w-12">#</th>`;
      html += `<th class="standings-th text-left">Team</th>`;
      html += `<th class="standings-th">P</th>`;
      html += `<th class="standings-th">W</th>`;
      html += `<th class="standings-th">D</th>`;
      html += `<th class="standings-th">L</th>`;
      html += `<th class="standings-th">GD</th>`;
      html += `<th class="standings-th font-bold">Pts</th>`;
      html += `</tr></thead><tbody>`;

      group.standings.forEach(row => {
        const youClass = row.is_you ? ' standings-row-you' : '';
        const rankBadge = row.rank <= 2 ? ' standings-qualified' : row.rank <= 4 ? ' standings-playoff' : '';
        html += `<tr class="standings-row${youClass}">`;
        html += `<td class="standings-td font-bold${rankBadge}">${row.rank}</td>`;
        html += `<td class="standings-td text-left font-medium text-white">`;
        html += `${_esc(row.name)}`;
        if (row.is_you) html += ` <span class="text-[#00F0FF] text-[10px] font-bold">(YOU)</span>`;
        html += `</td>`;
        html += `<td class="standings-td">${row.matches_played}</td>`;
        html += `<td class="standings-td text-[#00FF66]">${row.won}</td>`;
        html += `<td class="standings-td">${row.drawn}</td>`;
        html += `<td class="standings-td text-[#FF2A55]">${row.lost}</td>`;
        html += `<td class="standings-td">${row.goal_difference > 0 ? '+' : ''}${row.goal_difference}</td>`;
        html += `<td class="standings-td font-bold text-white">${row.points}</td>`;
        html += `</tr>`;
      });

      html += `</tbody></table></div></div>`;
    });

    container.innerHTML = html;
    container.classList.remove('hidden');
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ──────────────────────────────────────────────────────────
  // Matches Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchMatches() {
    const url = _shell?.dataset.apiMatches;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _matchesCache = data;
      _renderMatches(data);
    } catch (err) {
      console.warn('[HubEngine] Matches fetch failed:', err.message);
      _hide('matches-skeleton');
      _show('matches-empty');
    }
  }

  function _renderMatches(data) {
    _hide('matches-skeleton');

    // Active matches
    const cardsEl = document.getElementById('hub-match-cards');
    if (cardsEl) {
      if (data.active_matches && data.active_matches.length > 0) {
        let html = '';
        data.active_matches.forEach(m => {
          const stateColor = m.state === 'live' ? '#FF2A55' : m.state === 'ready' ? '#00FF66' : '#00F0FF';
          const lobbyCode = m.lobby_info?.lobby_code || '';
          html += `
            <div class="hub-glass rounded-xl p-5 border-l-4 match-card-active" style="border-left-color: ${stateColor}">
              <div class="flex items-center justify-between mb-3">
                <span class="text-[10px] font-bold text-gray-500 uppercase tracking-widest">${_esc(m.round_name)} &middot; Match ${m.match_number}</span>
                <span class="hub-badge" style="background:${stateColor}20;color:${stateColor}">
                  ${m.state === 'live' ? '<span class="w-1.5 h-1.5 rounded-full animate-pulse inline-block" style="background:' + stateColor + '"></span> ' : ''}
                  ${_esc(m.state_display)}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-bold text-white">vs ${_esc(m.opponent_name)}</p>
                  ${m.state === 'live' ? `<p class="text-lg font-black text-white mt-1" style="font-family:Outfit,sans-serif;">${m.your_score} — ${m.opponent_score}</p>` : ''}
                </div>
                ${lobbyCode ? `<div class="text-right"><p class="text-[10px] text-gray-500">Lobby Code</p><p class="text-sm font-bold text-[#00F0FF]" style="font-family:'Space Grotesk',monospace;">${_esc(lobbyCode)}</p></div>` : ''}
              </div>
              ${m.scheduled_at ? `<p class="text-[10px] text-gray-600 mt-2">Scheduled: ${new Date(m.scheduled_at).toLocaleString()}</p>` : ''}
            </div>`;
        });
        cardsEl.innerHTML = html;
        cardsEl.classList.remove('hidden');
      } else {
        _show('matches-empty');
      }
    }

    // Match history
    const historyEl = document.getElementById('hub-match-history');
    if (historyEl) {
      if (data.match_history && data.match_history.length > 0) {
        let html = '';
        data.match_history.forEach(m => {
          const resultClass = m.is_winner === true ? 'text-[#00FF66]' : m.is_winner === false ? 'text-[#FF2A55]' : 'text-gray-400';
          const resultLabel = m.is_winner === true ? 'WIN' : m.is_winner === false ? 'LOSS' : 'DRAW';
          html += `
            <div class="hub-glass rounded-xl p-4 flex items-center justify-between match-history-card">
              <div class="flex items-center gap-4">
                <span class="text-xs font-black ${resultClass} w-10">${resultLabel}</span>
                <div>
                  <p class="text-sm font-medium text-white">vs ${_esc(m.opponent_name)}</p>
                  <p class="text-[10px] text-gray-500">${_esc(m.round_name)}</p>
                </div>
              </div>
              <div class="text-right">
                <p class="text-lg font-black text-white" style="font-family:Outfit,sans-serif;">${m.your_score} — ${m.opponent_score}</p>
              </div>
            </div>`;
        });
        historyEl.innerHTML = html;
      } else {
        _show('match-history-empty');
      }
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  // ──────────────────────────────────────────────────────────
  // Participants Tab — Async Fetch & Render
  // ──────────────────────────────────────────────────────────
  async function _fetchParticipants() {
    const url = _shell?.dataset.apiParticipants;
    if (!url) return;

    try {
      const resp = await fetch(url, { credentials: 'same-origin' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      _participantsCache = data;
      _participantsAll = data.participants || [];
      _renderParticipants(_participantsAll);
    } catch (err) {
      console.warn('[HubEngine] Participants fetch failed:', err.message);
      _hide('participants-skeleton');
      _show('participants-empty');
    }
  }

  function _renderParticipants(list) {
    _hide('participants-skeleton');
    _hide('participants-empty');
    _hide('participants-no-results');

    const grid = document.getElementById('participants-grid');
    if (!grid) return;

    if (!list || list.length === 0) {
      grid.classList.add('hidden');
      _show('participants-empty');
      return;
    }

    // Update count
    const countEl = document.getElementById('participants-count');
    if (countEl && _participantsCache) countEl.textContent = _participantsCache.total;

    const isTeam = _participantsCache?.is_team;
    let html = '';
    list.forEach((p, i) => {
      const youBorder = p.is_you ? ' border-[#00F0FF]/30' : ' border-white/5';
      const youBadge = p.is_you ? `<span class="px-1.5 py-0.5 rounded bg-[#00F0FF]/20 text-[#00F0FF] text-[8px] font-black uppercase ml-1">You</span>` : '';
      const checkedIn = p.checked_in ? '<span class="w-2 h-2 rounded-full bg-[#00FF66] shadow-[0_0_5px_#00FF66] ml-auto shrink-0"></span>' : '';
      const seedBadge = p.seed ? `<span class="text-[10px] text-gray-600 ml-auto">#${p.seed}</span>` : '';
      const memberCount = (isTeam && p.member_count) ? `<p class="text-[10px] text-gray-500 uppercase tracking-widest" style="font-family:'Space Grotesk',monospace;">${p.member_count} Member${p.member_count !== 1 ? 's' : ''}</p>` : '';
      const statusBadge = (!p.verified && p.status_label)
        ? `<span class="px-1.5 py-0.5 rounded bg-[#FFB800]/15 text-[#FFB800] text-[8px] font-black uppercase border border-[#FFB800]/20 ml-1">${_esc(p.status_label)}</span>`
        : '';
      const verifiedBadge = p.verified === true && !p.is_you
        ? '<span class="w-2 h-2 rounded-full bg-[#00F0FF]/40 shrink-0" title="Verified"></span>'
        : '';

      // Stacked member avatars (team mode)
      let avatarStack = '';
      if (isTeam && p.member_avatars && p.member_avatars.length > 0) {
        avatarStack = '<div class="flex -space-x-2 overflow-hidden mt-3">';
        p.member_avatars.forEach(ma => {
          if (ma.avatar_url) {
            avatarStack += `<img class="inline-block h-8 w-8 rounded-full ring-2 ring-[#08080C] object-cover" src="${_esc(ma.avatar_url)}" alt="${_esc(ma.initial)}">`;
          } else {
            avatarStack += `<div class="inline-flex h-8 w-8 rounded-full ring-2 ring-[#08080C] bg-gray-800 items-center justify-center text-[10px] font-bold text-white">${_esc(ma.initial)}</div>`;
          }
        });
        avatarStack += '</div>';
      }

      // Logo / avatar
      const logo = p.logo_url
        ? `<img src="${_esc(p.logo_url)}" class="w-full h-full object-cover" alt="${_esc(p.name)}">`
        : `<span class="font-black text-xl" style="font-family:Outfit,sans-serif;">${_esc(p.tag)}</span>`;
      const logoColorClass = p.is_you ? 'bg-[#00F0FF]/20 text-[#00F0FF]' : 'bg-white/5 text-gray-400';

      // Wrap in link if detail_url exists
      const href = p.detail_url ? ` href="${_esc(p.detail_url)}"` : '';
      const tag = p.detail_url ? 'a' : 'div';
      const unverifiedClass = (p.verified === false) ? ' opacity-80 border-dashed' : '';

      html += `
        <${tag}${href} class="hub-glass p-5 rounded-xl border${youBorder}${unverifiedClass} hover:border-white/20 transition-all group cursor-pointer block" data-participant-name="${_esc(p.name.toLowerCase())}">
          <div class="flex items-center gap-4 mb-1">
            <div class="w-12 h-12 rounded-lg ${logoColorClass} flex items-center justify-center overflow-hidden border border-white/10 shrink-0 group-hover:scale-110 transition-transform">
              ${logo}
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1">
                <h3 class="font-bold text-white text-lg group-hover:text-[#00F0FF] transition-colors truncate" style="font-family:Outfit,sans-serif;">${_esc(p.name)}</h3>
                ${youBadge}
                ${statusBadge}
                ${checkedIn}
              </div>
              ${memberCount}
            </div>
          </div>
          ${avatarStack}
        </${tag}>`;
    });

    grid.innerHTML = html;
    grid.classList.remove('hidden');
    if (typeof lucide !== 'undefined') lucide.createIcons();
  }

  function filterParticipants(query) {
    if (!_participantsAll || _participantsAll.length === 0) return;
    const q = (query || '').toLowerCase().trim();

    if (!q) {
      _renderParticipants(_participantsAll);
      return;
    }

    const filtered = _participantsAll.filter(p =>
      p.name.toLowerCase().includes(q) || (p.tag || '').toLowerCase().includes(q)
    );

    if (filtered.length === 0) {
      const grid = document.getElementById('participants-grid');
      if (grid) grid.classList.add('hidden');
      _show('participants-no-results');
    } else {
      _hide('participants-no-results');
      _renderParticipants(filtered);
    }
  }

  // ──────────────────────────────────────────────────────────
  // Cleanup (if SPA navigates away)
  // ──────────────────────────────────────────────────────────
  function destroy() {
    if (_pollStateId) clearInterval(_pollStateId);
    if (_pollAnnId) clearInterval(_pollAnnId);
    if (_countdownId) clearInterval(_countdownId);
  }

  // ──────────────────────────────────────────────────────────
  // Registration Status Modal
  // ──────────────────────────────────────────────────────────
  function showStatusModal() {
    const modal = document.getElementById('hub-status-modal');
    if (modal) {
      modal.classList.remove('hidden');
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }
  }

  function closeStatusModal() {
    const modal = document.getElementById('hub-status-modal');
    if (modal) modal.classList.add('hidden');
  }

  // ──────────────────────────────────────────────────────────
  // Contact Admin Modal
  // ──────────────────────────────────────────────────────────
  function showContactModal() {
    const modal = document.getElementById('hub-contact-modal');
    if (modal) {
      modal.classList.remove('hidden');
      if (typeof lucide !== 'undefined') lucide.createIcons();
    }
  }

  function closeContactModal() {
    const modal = document.getElementById('hub-contact-modal');
    if (modal) modal.classList.add('hidden');
  }

  // ──────────────────────────────────────────────────────────
  // Welcome Guide (first-visit)
  // ──────────────────────────────────────────────────────────
  function _checkWelcomeGuide() {
    const slug = _shell?.dataset.slug || 'default';
    const key = `hub_guide_seen_${slug}`;
    if (!localStorage.getItem(key)) {
      const guide = document.getElementById('hub-welcome-guide');
      if (guide) {
        guide.classList.remove('hidden');
        if (typeof lucide !== 'undefined') lucide.createIcons();
      }
    }
  }

  function dismissGuide() {
    const slug = _shell?.dataset.slug || 'default';
    const key = `hub_guide_seen_${slug}`;
    localStorage.setItem(key, '1');
    const guide = document.getElementById('hub-welcome-guide');
    if (guide) guide.classList.add('hidden');
  }

  // ── Public API ──────────────────────────────────────────
  return {
    init,
    destroy,
    switchTab,
    performCheckIn,
    openMobileSidebar,
    closeMobileSidebar,
    swapToSub,
    swapToStarter,
    bracketZoom,
    bracketReset,
    // Module 5: Bounty Board
    openPrizeModal,
    closePrizeModal,
    submitPrizeClaim,
    // Module 9: Participants
    filterParticipants,
    // Module 10: Contact & Guide
    showContactModal,
    closeContactModal,
    // Module 11: Status Detail
    showStatusModal,
    closeStatusModal,
    dismissGuide,
  };
})();
