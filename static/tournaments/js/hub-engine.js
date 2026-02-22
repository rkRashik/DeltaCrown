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

    // Keyboard: Escape closes mobile sidebar
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeMobileSidebar();
    });
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
  // Cleanup (if SPA navigates away)
  // ──────────────────────────────────────────────────────────
  function destroy() {
    if (_pollStateId) clearInterval(_pollStateId);
    if (_pollAnnId) clearInterval(_pollAnnId);
    if (_countdownId) clearInterval(_countdownId);
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
  };
})();
