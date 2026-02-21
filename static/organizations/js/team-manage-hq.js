/**
 * Team Manage HQ — Client-side Controller
 * =========================================
 * Powers all AJAX operations for the team management console.
 * Reads configuration from window.MANAGE_HQ injected by the Django template.
 *
 * Sections: Command · Roster · Competition · Training · Community · Profile · Settings · Treasury · History
 */
(function () {
  "use strict";

  /* ── Config (injected by template) ── */
  const CFG  = window.MANAGE_HQ || {};
  const SLUG = CFG.slug;
  const CSRF = CFG.csrfToken;
  const API  = `/api/vnext/teams/${SLUG}`;

  /* ── Fetch wrapper ── */
  async function api(path, opts = {}) {
    const url = path.startsWith("http") || path.startsWith("/") ? path : `${API}/${path}`;
    const headers = { "X-CSRFToken": CSRF, ...(opts.headers || {}) };
    if (!(opts.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    const res = await fetch(url, { credentials: "same-origin", ...opts, headers });
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      if (res.status === 403) throw new Error("Permission denied (403). Please refresh and try again.");
      if (res.status === 401 || res.redirected) throw new Error("Session expired. Please refresh the page and log in again.");
      throw new Error(`Server returned non-JSON response (${res.status}). Please refresh the page.`);
    }
    const data = await res.json();
    if (!res.ok || data.success === false) {
      throw new Error(data.error || data.message || `Request failed (${res.status})`);
    }
    return data;
  }

  /* ── Toast notifications ── */
  function ensureToastContainer() {
    let c = document.getElementById("hq-toast-container");
    if (!c) {
      c = document.createElement("div");
      c.id = "hq-toast-container";
      c.className = "fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none";
      document.body.appendChild(c);
    }
    return c;
  }

  function toast(msg, type = "success") {
    const c = ensureToastContainer();
    const colors = {
      success: "bg-emerald-600/90 border-emerald-400/40",
      error:   "bg-red-600/90 border-red-400/40",
      info:    "bg-blue-600/90 border-blue-400/40",
    };
    const icons = { success: "check-circle", error: "alert-triangle", info: "info" };
    const el = document.createElement("div");
    el.className = `pointer-events-auto flex items-center gap-2 px-4 py-3 rounded-xl border text-sm text-white backdrop-blur-xl shadow-lg transition-all duration-300 ${colors[type] || colors.info}`;
    el.innerHTML = `<i data-lucide="${icons[type] || "info"}" class="w-4 h-4 shrink-0"></i><span>${esc(msg)}</span>`;
    c.appendChild(el);
    if (window.lucide) lucide.createIcons({ nodes: [el] });
    el.style.opacity = "0"; el.style.transform = "translateX(20px)";
    requestAnimationFrame(() => { el.style.opacity = "1"; el.style.transform = "translateX(0)"; });
    setTimeout(() => {
      el.style.opacity = "0"; el.style.transform = "translateX(20px)";
      setTimeout(() => el.remove(), 300);
    }, 4000);
  }

  /* ── Utility ── */
  function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
  function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
  function qsa(sel, ctx) { return [...(ctx || document).querySelectorAll(sel)]; }

  function renderTimestamp(ts) {
    if (!ts) return "";
    try {
      const d = new Date(ts);
      return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    } catch { return ts; }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     MODAL SYSTEM
     ═══════════════════════════════════════════════════════════════════════ */
  const Modal = {
    _stack: [],

    open(id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.remove("hidden");
      el.classList.add("flex");
      this._stack.push(id);
      setTimeout(() => {
        const inp = qs("input:not([type=hidden]),select,textarea", el);
        if (inp) inp.focus();
      }, 100);
    },

    close(id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.classList.add("hidden");
      el.classList.remove("flex");
      this._stack = this._stack.filter(i => i !== id);
    },

    closeTop() {
      if (this._stack.length) this.close(this._stack[this._stack.length - 1]);
    },
  };

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") Modal.closeTop();
  });

  /* ═══════════════════════════════════════════════════════════════════════
     COMMAND CENTER
     ═══════════════════════════════════════════════════════════════════════ */
  const ACTIVITY_STYLES = {
    roster:     { icon: 'users',      bg: 'bg-blue-500/15',   color: 'text-blue-400' },
    tournament: { icon: 'trophy',     bg: 'bg-amber-500/15',  color: 'text-amber-400' },
    settings:   { icon: 'settings',   bg: 'bg-white/10',      color: 'text-white/60' },
    profile:    { icon: 'palette',    bg: 'bg-purple-500/15', color: 'text-purple-400' },
    invite:     { icon: 'mail',       bg: 'bg-cyan-500/15',   color: 'text-cyan-400' },
    join:       { icon: 'user-plus',  bg: 'bg-emerald-500/15',color: 'text-emerald-400' },
    remove:     { icon: 'user-x',     bg: 'bg-red-500/15',    color: 'text-red-400' },
    role:       { icon: 'shield',     bg: 'bg-indigo-500/15', color: 'text-indigo-400' },
    training:   { icon: 'crosshair',  bg: 'bg-teal-500/15',   color: 'text-teal-400' },
    community:  { icon: 'message-square', bg: 'bg-pink-500/15', color: 'text-pink-400' },
    discord:    { icon: 'message-circle', bg: 'bg-indigo-500/15', color: 'text-indigo-400' },
    default:    { icon: 'activity',   bg: 'bg-white/10',      color: 'text-white/60' },
  };

  function _renderActivityItem(a) {
    const style = ACTIVITY_STYLES[a.type] || ACTIVITY_STYLES.default;
    const actor = a.actor ? `<span class="text-white/60 font-medium">${esc(a.actor)}</span> · ` : '';
    return `
      <div class="flex items-start gap-3 py-2.5 border-b border-white/[0.06] last:border-0 group hover:bg-white/[0.02] -mx-1 px-1 rounded-lg transition">
        <div class="h-8 w-8 rounded-lg ${style.bg} grid place-items-center shrink-0 mt-0.5">
          <i data-lucide="${style.icon}" class="w-3.5 h-3.5 ${style.color}"></i>
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-sm text-white/90 leading-snug">${esc(a.description || a.title || 'Activity')}</p>
          <p class="text-[11px] text-white/35 mt-0.5">${actor}${esc(a.time_ago || '')}</p>
        </div>
      </div>`;
  }

  const Command = {
    _offset: 0,
    _hasMore: false,

    init() {
      this._offset = 0;
      this._hasMore = false;
      this.loadActivity();
    },

    async loadActivity(append = false) {
      const container = document.getElementById('activity-feed');
      if (!container) return;

      if (!append) {
        container.innerHTML = `
          <div class="text-center py-6">
            <div class="animate-spin h-5 w-5 border-2 border-white/20 border-t-teal-400 rounded-full mx-auto"></div>
            <p class="text-xs text-white/30 mt-2">Loading activity…</p>
          </div>`;
      }

      try {
        const data = await api(`${API}/activity/?limit=15&offset=${this._offset}`, { method: 'GET' });
        const items = data.events || data.activities || data.activity || [];
        this._hasMore = data.has_more || false;
        this._offset += items.length;

        if (!items.length && !append) {
          container.innerHTML = `
            <div class="text-center py-8">
              <i data-lucide="inbox" class="w-8 h-8 text-white/15 mx-auto mb-2"></i>
              <p class="text-sm text-white/40">No activity recorded yet.</p>
              <p class="text-xs text-white/25 mt-1">Actions like roster changes, settings updates, and tournament entries will appear here.</p>
            </div>`;
          if (window.lucide) lucide.createIcons({ nodes: [container] });
          return;
        }

        const html = items.map(a => _renderActivityItem(a)).join('');

        if (append) {
          // Remove existing load-more button before appending
          const existingBtn = container.querySelector('.load-more-wrap');
          if (existingBtn) existingBtn.remove();
          container.insertAdjacentHTML('beforeend', html);
        } else {
          container.innerHTML = html;
        }

        // Add Load More button if there's more data
        if (this._hasMore) {
          const loadMoreHtml = `
            <div class="load-more-wrap text-center pt-3">
              <button onclick="ManageHQ.loadMoreActivity()" id="load-more-activity"
                class="text-xs px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-white/50 hover:text-white/70 border border-white/10 transition font-medium">
                Load More Activity
              </button>
            </div>`;
          container.insertAdjacentHTML('beforeend', loadMoreHtml);
        }

        if (window.lucide) lucide.createIcons({ nodes: [container] });
      } catch (err) {
        if (!append) {
          container.innerHTML = `
            <div class="text-center py-6">
              <i data-lucide="wifi-off" class="w-6 h-6 text-white/15 mx-auto mb-2"></i>
              <p class="text-sm text-white/40">Activity feed unavailable.</p>
            </div>`;
          if (window.lucide) lucide.createIcons({ nodes: [container] });
        }
      }
    },

    loadMore() {
      const btn = document.getElementById('load-more-activity');
      if (btn) { btn.textContent = 'Loading…'; btn.disabled = true; }
      this.loadActivity(true);
    },
  };

  /* ═══════════════════════════════════════════════════════════════════════
     ROSTER OPS
     ═══════════════════════════════════════════════════════════════════════ */
  const Roster = {
    _searchTimeout: null,
    _selectedUser: null,

    init() {
      const invForm = document.getElementById("invite-form");
      if (invForm) invForm.addEventListener("submit", (e) => { e.preventDefault(); this.sendInvite(); });

      const roleForm = document.getElementById("role-edit-form");
      if (roleForm) roleForm.addEventListener("submit", (e) => { e.preventDefault(); this.saveRole(); });

      // Player search autocomplete
      const searchInput = qs("#invite-username");
      if (searchInput) {
        searchInput.setAttribute("autocomplete", "off");
        searchInput.addEventListener("input", () => this._onSearchInput());
        searchInput.addEventListener("keydown", (e) => this._onSearchKeydown(e));
        // Close dropdown when clicking outside
        document.addEventListener("click", (e) => {
          if (!e.target.closest("#invite-search-wrapper")) this._closeDropdown();
        });
      }
    },

    _onSearchInput() {
      clearTimeout(this._searchTimeout);
      const q = qs("#invite-username")?.value.trim();
      if (!q || q.length < 2) { this._closeDropdown(); return; }
      this._searchTimeout = setTimeout(() => this._searchPlayers(q), 250);
    },

    _onSearchKeydown(e) {
      const dd = qs("#invite-search-dropdown");
      if (!dd || dd.classList.contains("hidden")) return;
      const items = qsa(".search-result-item", dd);
      const active = dd.querySelector(".search-result-item.bg-white\\/10");
      let idx = items.indexOf(active);

      if (e.key === "ArrowDown") { e.preventDefault(); idx = Math.min(idx + 1, items.length - 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); idx = Math.max(idx - 1, 0); }
      else if (e.key === "Enter" && active) { e.preventDefault(); active.click(); return; }
      else if (e.key === "Escape") { this._closeDropdown(); return; }
      else return;

      items.forEach(i => i.classList.remove("bg-white/10"));
      if (items[idx]) items[idx].classList.add("bg-white/10");
    },

    async _searchPlayers(query) {
      try {
        const data = await api(`search-players/?q=${encodeURIComponent(query)}`, { method: "GET" });
        this._renderDropdown(data.results || []);
      } catch { this._closeDropdown(); }
    },

    _renderDropdown(results) {
      let dd = qs("#invite-search-dropdown");
      if (!dd) {
        dd = document.createElement("div");
        dd.id = "invite-search-dropdown";
        dd.className = "absolute left-0 right-0 top-full mt-1 rounded-xl border border-white/10 bg-[#0a0a1a]/95 backdrop-blur-xl shadow-2xl z-50 max-h-[280px] overflow-y-auto";
        const wrapper = qs("#invite-search-wrapper");
        if (wrapper) { wrapper.style.position = "relative"; wrapper.appendChild(dd); }
        else return;
      }

      if (!results.length) {
        dd.innerHTML = `<div class="px-4 py-3 text-sm text-white/40 text-center">No players found</div>`;
        dd.classList.remove("hidden");
        return;
      }

      dd.innerHTML = results.map(u => `
        <div class="search-result-item flex items-center gap-3 px-4 py-2.5 hover:bg-white/10 cursor-pointer transition-colors"
             data-username="${esc(u.username)}" data-id="${u.id}">
          ${u.avatar_url
            ? `<img src="${esc(u.avatar_url)}" class="w-8 h-8 rounded-full object-cover border border-white/10" alt="">`
            : `<div class="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500/30 to-purple-500/30 grid place-items-center text-xs font-bold text-white">${esc((u.username || "?")[0].toUpperCase())}</div>`
          }
          <div class="flex-1 min-w-0">
            <div class="text-sm font-semibold text-white truncate">${esc(u.display_name)}</div>
            <div class="text-xs text-white/40 truncate">@${esc(u.username)}</div>
          </div>
          <i data-lucide="plus-circle" class="w-4 h-4 text-cyan-400 opacity-0 group-hover:opacity-100 shrink-0"></i>
        </div>
      `).join("");
      dd.classList.remove("hidden");
      if (window.lucide) lucide.createIcons({ nodes: [dd] });

      qsa(".search-result-item", dd).forEach(el => {
        el.addEventListener("click", () => {
          const username = el.dataset.username;
          qs("#invite-username").value = username;
          this._selectedUser = username;
          this._closeDropdown();
          qs("#invite-username").focus();
        });
      });
    },

    _closeDropdown() {
      const dd = qs("#invite-search-dropdown");
      if (dd) dd.classList.add("hidden");
    },

    openInviteModal() {
      const form = document.getElementById("invite-form");
      if (form) form.reset();
      this._selectedUser = null;
      this._closeDropdown();
      qs("#invite-error")?.classList.add("hidden");
      Modal.open("modal-invite");
    },

    async sendInvite() {
      const username = qs("#invite-username")?.value.trim();
      const role     = qs("#invite-role")?.value || "PLAYER";
      const errEl    = qs("#invite-error");
      const btn      = qs("#invite-submit-btn");

      if (!username) { errEl.textContent = "Enter a username or email."; errEl.classList.remove("hidden"); return; }

      btn.disabled = true; btn.textContent = "Sending…";
      try {
        const data = await api("invite/", {
          method: "POST",
          body: JSON.stringify({ username_or_email: username, role }),
        });
        toast(data.message || "Invite sent!");
        Modal.close("modal-invite");
        const list = document.getElementById("pending-invites-list");
        if (list && data.invite) {
          const inv = data.invite;
          const row = document.createElement("div");
          row.id = `invite-${inv.id}`;
          row.className = "rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 flex items-center justify-between";
          row.innerHTML = `
            <div class="flex items-center gap-3">
              <div class="h-8 w-8 rounded-lg bg-white/10 grid place-items-center text-xs font-bold">${esc((inv.username || "?")[0].toUpperCase())}</div>
              <div>
                <div class="text-sm font-semibold">${esc(inv.username)}</div>
                <div class="text-xs text-white/40">${esc(inv.role)} · Just now</div>
              </div>
            </div>
            <button onclick="ManageHQ.cancelInvite(${inv.id}, this)" class="text-xs px-3 py-1 rounded-lg border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 transition">Cancel</button>
          `;
          list.prepend(row);
          document.getElementById("pending-invites-section")?.classList.remove("hidden");
        }
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Send Invite";
      }
    },

    async cancelInvite(inviteId, btn) {
      if (!confirm("Cancel this invitation?")) return;
      try {
        await api(`${API}/invites/${inviteId}/cancel/`, { method: "POST" });
        toast("Invite cancelled.");
        document.getElementById(`invite-${inviteId}`)?.remove();
      } catch (err) { toast(err.message, "error"); }
    },

    openRoleModal(membershipId, currentRole, username, isCaptain, playerRole, rosterSlot, displayName, rosterImageUrl) {
      qs("#role-membership-id").value  = membershipId;
      qs("#role-username-display").textContent = username;
      qs("#role-select").value        = currentRole;
      const slotField = qs("#role-roster-slot");
      if (slotField) slotField.value = rosterSlot || "";
      const captainCb = qs("#role-captain-cb");
      if (captainCb) captainCb.checked = isCaptain;
      const prField = qs("#role-player-role");
      if (prField) prField.value = playerRole || "";
      const dnField = qs("#role-display-name");
      if (dnField) dnField.value = displayName || "";
      qs("#role-error")?.classList.add("hidden");

      // ── Photo preview ──
      const photoPreview = qs("#role-photo-preview");
      const photoInput = qs("#role-photo-input");
      if (photoPreview) {
        if (rosterImageUrl) {
          photoPreview.innerHTML = `<img src="${rosterImageUrl}" class="w-full h-full object-cover">`;
        } else {
          photoPreview.innerHTML = `<svg class="w-6 h-6 text-white/20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>`;
        }
      }
      if (photoInput) photoInput.value = "";

      // ── Load permissions from data attribute ──
      const permSection = document.getElementById("role-permissions-section");
      const permGrid = document.getElementById("role-perm-grid");
      if (permSection) {
        // Don't show permissions for OWNER (they have ALL)
        if (currentRole === "OWNER") {
          permSection.classList.add("hidden");
        } else {
          permSection.classList.remove("hidden");
        }
        if (permGrid) permGrid.classList.add("hidden"); // Start collapsed
      }
      // Read permissions JSON from closest card data attribute
      const card = document.querySelector(`[data-membership-id="${membershipId}"]`);
      let memberPerms = {};
      if (card) {
        try { memberPerms = JSON.parse(card.dataset.permissions || "{}"); } catch (e) { /* ignore */ }
      }
      // Populate checkboxes
      document.querySelectorAll(".perm-cb").forEach(cb => {
        const perm = cb.dataset.perm;
        cb.checked = memberPerms[perm] === true;
        cb.indeterminate = false;
      });

      Modal.open("modal-role-edit");
      if (window.lucide) lucide.createIcons();
    },

    _collectPermissions() {
      const perms = {};
      document.querySelectorAll(".perm-cb").forEach(cb => {
        perms[cb.dataset.perm] = cb.checked;
      });
      return perms;
    },

    async saveRole() {
      const memId      = qs("#role-membership-id").value;
      const role       = qs("#role-select").value;
      const rosterSlot = qs("#role-roster-slot")?.value || "";
      const captain    = qs("#role-captain-cb")?.checked || false;
      const playerRole = qs("#role-player-role")?.value || "";
      const displayName = qs("#role-display-name")?.value || "";
      const permissions = this._collectPermissions();
      const errEl      = qs("#role-error");
      const btn        = qs("#role-submit-btn");

      btn.disabled = true; btn.textContent = "Saving…";
      try {
        await api(`${API}/members/${memId}/role/`, {
          method: "POST",
          body: JSON.stringify({ role, roster_slot: rosterSlot, assign_captain: captain ? "true" : "false", player_role: playerRole, display_name: displayName, permissions }),
        });

        // Upload roster photo if one was selected
        const photoInput = qs("#role-photo-input");
        if (photoInput && photoInput.files && photoInput.files[0]) {
          const fd = new FormData();
          fd.append("roster_image", photoInput.files[0]);
          await fetch(`${API}/members/${memId}/roster-photo/`, {
            method: "POST",
            headers: { "X-CSRFToken": CSRF },
            body: fd,
          });
        }

        toast("Role updated.");
        Modal.close("modal-role-edit");
        setTimeout(() => location.reload(), 600);
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Save Changes";
      }
    },

    async swapSlot(membershipId, newSlot) {
      try {
        await api(`${API}/members/${membershipId}/role/`, {
          method: "POST",
          body: JSON.stringify({ roster_slot: newSlot }),
        });
        toast(`Moved to ${newSlot.toLowerCase()}.`);
        setTimeout(() => location.reload(), 600);
      } catch (err) {
        toast(err.message, "error");
      }
    },

    async toggleRosterLock(locked) {
      try {
        const data = await api(`${API}/roster/lock/`, {
          method: "POST",
          body: JSON.stringify({ locked }),
        });
        toast(data.message || (locked ? "Roster locked." : "Roster unlocked."));
        setTimeout(() => location.reload(), 600);
      } catch (err) {
        toast(err.message, "error");
      }
    },

    openRemoveModal(membershipId, username) {
      qs("#remove-membership-id").value    = membershipId;
      qs("#remove-username-display").textContent = username;
      qs("#remove-confirm-input").value    = "";
      qs("#remove-confirm-target").textContent = username;
      qs("#remove-error")?.classList.add("hidden");
      Modal.open("modal-remove");
    },

    async confirmRemove() {
      const memId    = qs("#remove-membership-id").value;
      const expected = qs("#remove-username-display").textContent;
      const typed    = qs("#remove-confirm-input").value.trim();
      const errEl    = qs("#remove-error");
      const btn      = qs("#remove-submit-btn");

      if (typed !== expected) {
        errEl.textContent = `Type "${expected}" to confirm.`;
        errEl.classList.remove("hidden");
        return;
      }

      btn.disabled = true; btn.textContent = "Removing…";
      try {
        await api(`${API}/members/${memId}/remove/`, {
          method: "POST",
          body: JSON.stringify({ confirmation: typed }),
        });
        toast("Member removed.");
        Modal.close("modal-remove");
        document.querySelector(`[data-membership-id="${memId}"]`)?.remove();
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Remove Member";
      }
    },

    async handleJoinRequest(requestId, action, btn) {
      if (btn) { btn.disabled = true; }
      try {
        await api(`join-requests/${requestId}/handle/`, {
          method: "POST",
          body: JSON.stringify({ action }),
        });
        toast(action === "approve" ? "Member approved!" : "Request rejected.");
        document.getElementById(`jr-${requestId}`)?.remove();
        const badge = document.getElementById("jr-count-badge");
        if (badge) {
          const n = Math.max(0, parseInt(badge.textContent) - 1);
          badge.textContent = n;
          if (n === 0) badge.closest("[data-jr-section]")?.classList.add("hidden");
        }
      } catch (err) {
        toast(err.message, "error");
        if (btn) btn.disabled = false;
      }
    },
  };

  /* ═══════════════════════════════════════════════════════════════════════
     COMPETITION HUB
     ═══════════════════════════════════════════════════════════════════════ */
  const Competition = {
    _loaded: false,

    init() {
      // Lazy-load when section becomes visible
      const section = document.getElementById("competition");
      if (!section) return;
      const observer = new MutationObserver(() => {
        if (section.classList.contains("is-active") && !this._loaded) {
          this._loaded = true;
          this.loadData();
        }
      });
      observer.observe(section, { attributes: true, attributeFilter: ["class"] });
    },

    async loadData() {
      // Competition data will come from P1 API endpoint when available.
      // For now we leave the static placeholders.
    },
  };

  /* ═══════════════════════════════════════════════════════════════════════
     TRAINING LAB — Challenge & Bounty System + Scrims/Schedule/VODs
     ═══════════════════════════════════════════════════════════════════════ */
  const Training = {
    _loaded: false,
    _challengeAPI: '/api/v1',

    init() {
      const section = document.getElementById("training");
      if (!section) return;
      const observer = new MutationObserver(() => {
        if (section.classList.contains("is-active") && !this._loaded) {
          this._loaded = true;
          this.loadChallenges();
          this.loadBounties();
          this.loadStats();
        }
      });
      observer.observe(section, { attributes: true, attributeFilter: ["class"] });

      // Challenge form
      const challengeForm = document.getElementById("issue-challenge-form");
      if (challengeForm) challengeForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitChallenge(); });

      // Show/hide direct team field based on challenge type
      const chType = document.getElementById("ch-type");
      if (chType) chType.addEventListener("change", () => {
        const wrap = document.getElementById("ch-direct-team-wrap");
        if (wrap) wrap.classList.toggle("hidden", chType.value !== "DIRECT");
      });

      // Bounty form
      const bountyForm = document.getElementById("create-bounty-form");
      if (bountyForm) bountyForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitBounty(); });

      // Legacy forms (scrims, schedule, vods)
      const scheduleForm = document.getElementById("schedule-practice-form");
      if (scheduleForm) scheduleForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitSchedule(); });

      const scrimForm = document.getElementById("post-scrim-form");
      if (scrimForm) scrimForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitScrim(); });

      const vodForm = document.getElementById("add-vod-form");
      if (vodForm) vodForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitVod(); });
    },

    // ── Sub-tab Navigation ──
    switchSubTab(tab) {
      document.querySelectorAll(".training-panel").forEach(p => p.classList.add("hidden"));
      document.querySelectorAll(".training-sub-tab").forEach(t => {
        const isActive = t.dataset.tab === tab;
        t.classList.toggle("bg-white/10", isActive);
        t.classList.toggle("text-white", isActive);
        t.classList.toggle("text-white/50", !isActive);
      });
      const panel = document.getElementById(`training-panel-${tab}`);
      if (panel) panel.classList.remove("hidden");
    },

    // ── Load Challenges ──
    async loadChallenges() {
      const section = document.getElementById("training");
      const slug = section?.dataset.teamSlug;
      if (!slug) return;

      try {
        const data = await api(`${this._challengeAPI}/teams/${slug}/challenges/`, { method: "GET" });
        const list = document.getElementById("challenge-list");
        const history = document.getElementById("challenge-history");
        const emptyState = document.getElementById("ch-empty-state");
        const countEl = document.getElementById("ch-active-count");

        if (!Array.isArray(data) || data.length === 0) {
          if (countEl) countEl.textContent = "0";
          return;
        }

        const active = data.filter(c => !["COMPLETED", "CANCELLED", "EXPIRED", "SETTLED"].includes(c.status));
        const completed = data.filter(c => ["COMPLETED", "CANCELLED", "EXPIRED", "SETTLED"].includes(c.status));

        if (countEl) countEl.textContent = active.length;

        if (list && active.length > 0) {
          if (emptyState) emptyState.style.display = "none";
          active.forEach(c => list.appendChild(this._renderChallengeCard(c)));
        }

        if (history && completed.length > 0) {
          history.innerHTML = "";
          completed.forEach(c => history.appendChild(this._renderChallengeCard(c, true)));
        }
      } catch {
        // API may not be connected yet
      }
    },

    _renderChallengeCard(c, isHistory = false) {
      const div = document.createElement("div");
      div.dataset.status = c.status;
      const statusColors = {
        OPEN: "text-blue-400 bg-blue-500/10 border-blue-500/20",
        PENDING: "text-amber-400 bg-amber-500/10 border-amber-500/20",
        ACCEPTED: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
        SCHEDULED: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
        IN_PROGRESS: "text-orange-400 bg-orange-500/10 border-orange-500/20",
        COMPLETED: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
        CANCELLED: "text-slate-400 bg-slate-500/10 border-slate-500/20",
        EXPIRED: "text-slate-500 bg-slate-500/5 border-slate-500/15",
        SETTLED: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
      };
      const colorClass = statusColors[c.status] || "text-white/50 bg-white/5 border-white/10";

      const opponent = c.challenged_team_name || "Open Challenge";
      const time = c.scheduled_at ? new Date(c.scheduled_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" }) : "";
      const prize = c.prize_type !== "NONE" ? `${c.prize_amount} ${c.prize_type}` : "";

      div.className = `rounded-xl border border-white/10 bg-white/3 p-4 hover:bg-white/5 transition`;
      div.innerHTML = `
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-xs px-2 py-0.5 rounded-full border font-semibold ${colorClass}">${c.status_display || c.status}</span>
              <span class="text-[10px] text-white/30 font-mono">${c.reference_code || ""}</span>
              ${prize ? `<span class="text-[10px] text-amber-400 font-bold">${prize}</span>` : ""}
            </div>
            <h4 class="text-sm font-bold text-white/90 truncate">${this._esc(c.title)}</h4>
            <div class="flex items-center gap-3 mt-1.5 text-[11px] text-white/40">
              <span><strong class="text-white/60">${this._esc(c.challenger_team_name)}</strong> vs <strong class="text-white/60">${this._esc(opponent)}</strong></span>
              ${c.game_short_code ? `<span class="px-1.5 py-0.5 rounded bg-white/5 text-[10px] font-mono">${c.game_short_code}</span>` : ""}
              <span>BO${c.best_of}</span>
              ${time ? `<span>${time}</span>` : ""}
            </div>
          </div>
          ${!isHistory ? this._renderChallengeActions(c) : ""}
        </div>
      `;
      return div;
    },

    _renderChallengeActions(c) {
      const slug = document.getElementById("training")?.dataset.teamSlug;
      const isOurs = c.challenger_team_slug === slug;
      let html = '<div class="flex items-center gap-1.5 shrink-0">';

      if (c.status === "PENDING" && !isOurs) {
        html += `<button onclick="ManageHQ.Training.acceptChallenge('${c.id}')" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white transition">Accept</button>`;
        html += `<button onclick="ManageHQ.Training.declineChallenge('${c.id}')" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 hover:bg-red-500/20 text-white/60 hover:text-red-400 transition">Decline</button>`;
      } else if (c.status === "OPEN" || (c.status === "PENDING" && isOurs)) {
        html += `<button onclick="ManageHQ.Training.cancelChallenge('${c.id}')" class="px-3 py-1.5 rounded-lg text-xs font-medium bg-white/5 hover:bg-white/10 text-white/50 transition">Cancel</button>`;
      } else if (c.status === "ACCEPTED" || c.status === "SCHEDULED") {
        html += `<button onclick="ManageHQ.Training.openResultModal('${c.id}')" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white transition">Submit Result</button>`;
      }
      html += '</div>';
      return html;
    },

    _esc(text) {
      const d = document.createElement("div");
      d.textContent = text || "";
      return d.innerHTML;
    },

    // ── Challenge CRUD ──
    async submitChallenge() {
      const section = document.getElementById("training");
      const teamId = section?.dataset.teamId;
      const gameId = section?.dataset.gameId;
      const btn = qs("#ch-submit");
      const errEl = qs("#ch-error");
      if (!teamId || !gameId) { if (errEl) { errEl.textContent = "Team/game not configured."; errEl.classList.remove("hidden"); } return; }

      btn.disabled = true;
      const origText = btn.innerHTML;
      btn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Issuing…';

      try {
        const payload = {
          challenger_team_id: parseInt(teamId),
          game_id: parseInt(gameId),
          title: qs("#ch-title")?.value.trim(),
          description: qs("#ch-description")?.value.trim() || "",
          challenge_type: qs("#ch-type")?.value || "OPEN",
          best_of: parseInt(qs("#ch-bestof")?.value) || 1,
          prize_type: qs("#ch-prize-type")?.value || "NONE",
          prize_amount: parseFloat(qs("#ch-prize-amount")?.value) || 0,
          is_public: true,
        };

        const scheduled = qs("#ch-scheduled")?.value;
        if (scheduled) payload.scheduled_at = new Date(scheduled).toISOString();

        // Direct challenge — resolve team slug to ID
        if (payload.challenge_type === "DIRECT") {
          const targetSlug = qs("#ch-challenged-slug")?.value.trim();
          if (!targetSlug) throw new Error("Enter the opponent team's slug for a direct challenge.");
          // Look up team ID by fetching the team challenges endpoint (or do inline)
          try {
            const teamData = await fetch(`/api/vnext/teams/${targetSlug}/`, { credentials: "same-origin" }).then(r => r.json());
            if (teamData.id) payload.challenged_team_id = teamData.id;
            else throw new Error(`Team "${targetSlug}" not found.`);
          } catch {
            throw new Error(`Could not find team "${targetSlug}". Check the slug.`);
          }
        }

        await api(`${this._challengeAPI}/challenges/`, {
          method: "POST",
          body: JSON.stringify(payload),
        });

        toast("Challenge issued! Let's go! 🔥");
        qs("#issue-challenge-form")?.reset();
        errEl?.classList.add("hidden");
        this.loadChallenges();
        this.loadStats();
      } catch (err) {
        if (errEl) { errEl.textContent = err.message; errEl.classList.remove("hidden"); }
      } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
      }
    },

    async acceptChallenge(id) {
      try {
        const section = document.getElementById("training");
        const teamId = section?.dataset.teamId;
        await api(`${this._challengeAPI}/challenges/${id}/accept/`, {
          method: "POST",
          body: JSON.stringify({ accepting_team_id: parseInt(teamId) }),
        });
        toast("Challenge accepted! Prepare for battle! ⚔️");
        this.loadChallenges();
        this.loadStats();
      } catch (err) { toast(err.message, "error"); }
    },

    async declineChallenge(id) {
      try {
        await api(`${this._challengeAPI}/challenges/${id}/decline/`, { method: "POST", body: "{}" });
        toast("Challenge declined.");
        this.loadChallenges();
      } catch (err) { toast(err.message, "error"); }
    },

    async cancelChallenge(id) {
      try {
        await api(`${this._challengeAPI}/challenges/${id}/cancel/`, { method: "POST", body: "{}" });
        toast("Challenge cancelled.");
        this.loadChallenges();
        this.loadStats();
      } catch (err) { toast(err.message, "error"); }
    },

    openResultModal(challengeId) {
      // Quick inline prompt for result
      const result = prompt("Enter result:\n1 = Our team won\n2 = Opponent won\n3 = Draw");
      if (!result) return;
      const map = { "1": "CHALLENGER_WIN", "2": "CHALLENGED_WIN", "3": "DRAW" };
      const val = map[result];
      if (!val) { toast("Invalid choice. Enter 1, 2, or 3.", "error"); return; }
      this.submitResult(challengeId, val);
    },

    async submitResult(id, result) {
      try {
        await api(`${this._challengeAPI}/challenges/${id}/result/`, {
          method: "POST",
          body: JSON.stringify({ result }),
        });
        toast("Result submitted! GG! 🏆");
        this.loadChallenges();
        this.loadStats();
      } catch (err) { toast(err.message, "error"); }
    },

    // ── Load & Render Bounties ──
    async loadBounties() {
      const section = document.getElementById("training");
      const slug = section?.dataset.teamSlug;
      if (!slug) return;

      try {
        const data = await api(`${this._challengeAPI}/teams/${slug}/bounties/`, { method: "GET" });
        const list = document.getElementById("bounty-list");
        const emptyState = document.getElementById("bn-empty-state");
        const countEl = document.getElementById("bn-active-count");
        const statEl = document.getElementById("stat-bounties-active");

        if (!Array.isArray(data) || data.length === 0) {
          if (countEl) countEl.textContent = "0";
          if (statEl) statEl.textContent = "0";
          return;
        }

        if (countEl) countEl.textContent = data.length;
        if (statEl) statEl.textContent = data.length;

        if (list && data.length > 0) {
          if (emptyState) emptyState.style.display = "none";
          data.forEach(b => list.appendChild(this._renderBountyCard(b)));
        }
      } catch {}
    },

    _renderBountyCard(b) {
      const div = document.createElement("div");
      const typeLabels = { BEAT_US: "Beat Us", WIN_STREAK: "Win Streak", FIRST_BLOOD: "First Blood", TOURNAMENT_WIN: "Tournament Win", CUSTOM: "Custom" };
      div.className = "rounded-xl border border-amber-500/10 bg-gradient-to-r from-amber-500/5 to-transparent p-4 hover:from-amber-500/10 transition";
      div.innerHTML = `
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-1">
              <span class="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 font-semibold border border-amber-500/20">${typeLabels[b.bounty_type] || b.bounty_type}</span>
              <span class="text-[10px] text-white/30 font-mono">${b.reference_code || ""}</span>
            </div>
            <h4 class="text-sm font-bold text-white/90 truncate">${this._esc(b.title)}</h4>
            ${b.description ? `<p class="text-[11px] text-white/40 mt-1 line-clamp-2">${this._esc(b.description)}</p>` : ""}
            <div class="flex items-center gap-3 mt-1.5 text-[11px] text-white/40">
              <span class="text-amber-400 font-bold">${b.reward_amount} ${b.reward_type}</span>
              <span>${b.claim_count || 0} / ${b.max_claims} claims</span>
              ${b.game_short_code ? `<span class="px-1.5 py-0.5 rounded bg-white/5 text-[10px] font-mono">${b.game_short_code}</span>` : ""}
              ${b.expires_at ? `<span>Expires ${new Date(b.expires_at).toLocaleDateString()}</span>` : ""}
            </div>
          </div>
          ${b.is_claimable ? '<div class="shrink-0"><span class="px-2 py-1 rounded-lg text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">Claimable</span></div>' : ''}
        </div>
      `;
      return div;
    },

    async submitBounty() {
      const section = document.getElementById("training");
      const teamId = section?.dataset.teamId;
      const gameId = section?.dataset.gameId;
      const btn = qs("#bn-submit");
      const errEl = qs("#bn-error");
      if (!teamId || !gameId) { if (errEl) { errEl.textContent = "Team/game not configured."; errEl.classList.remove("hidden"); } return; }

      btn.disabled = true;
      const origText = btn.innerHTML;
      btn.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i> Posting…';

      try {
        const payload = {
          issuer_team_id: parseInt(teamId),
          game_id: parseInt(gameId),
          title: qs("#bn-title")?.value.trim(),
          description: qs("#bn-description")?.value.trim() || "",
          bounty_type: qs("#bn-type")?.value || "BEAT_US",
          reward_type: qs("#bn-reward-type")?.value || "CP",
          reward_amount: parseFloat(qs("#bn-reward-amount")?.value) || 0,
          max_claims: parseInt(qs("#bn-max-claims")?.value) || 1,
          is_public: true,
        };

        const expires = qs("#bn-expires")?.value;
        if (expires) payload.expires_at = new Date(expires).toISOString();

        await api(`${this._challengeAPI}/bounties/`, {
          method: "POST",
          body: JSON.stringify(payload),
        });

        toast("Bounty posted! Let the hunt begin! 🎯");
        qs("#create-bounty-form")?.reset();
        errEl?.classList.add("hidden");
        this.loadBounties();
        this.loadStats();
      } catch (err) {
        if (errEl) { errEl.textContent = err.message; errEl.classList.remove("hidden"); }
      } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
      }
    },

    // ── Challenge Stats ──
    async loadStats() {
      const section = document.getElementById("training");
      const slug = section?.dataset.teamSlug;
      if (!slug) return;

      try {
        const data = await api(`${this._challengeAPI}/teams/${slug}/challenges/stats/`, { method: "GET" });
        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setEl("stat-challenges-issued", data.total || 0);
        setEl("stat-challenges-won", data.wins || 0);
        setEl("stat-challenges-total", data.total || 0);
      } catch {}
    },

    // ── Challenge Filter ──
    filterChallenges() {
      const status = qs("#ch-filter-status")?.value || "";
      qsa("#challenge-list > div[data-status]").forEach(el => {
        el.style.display = (!status || el.dataset.status === status) ? "" : "none";
      });
    },

    // ── Legacy: Schedule/Scrim/VOD (kept for backwards compatibility) ──
    openScheduleModal() {
      const form = document.getElementById("schedule-practice-form");
      if (form) form.reset();
      qs("#schedule-error")?.classList.add("hidden");
      Modal.open("modal-schedule-practice");
    },

    async submitSchedule() {
      const btn = qs("#schedule-submit");
      const errEl = qs("#schedule-error");
      btn.disabled = true; btn.textContent = "Scheduling…";
      try {
        const payload = {
          title: qs("#schedule-title")?.value.trim(),
          date: qs("#schedule-date")?.value,
          time: qs("#schedule-time")?.value,
          duration: qs("#schedule-duration")?.value,
          type: qs("#schedule-type")?.value,
          notes: qs("#schedule-notes")?.value.trim(),
        };
        const data = await api("training/schedule/", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        toast(data.message || "Practice session scheduled!");
        Modal.close("modal-schedule-practice");
        this.loadData();
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Schedule";
      }
    },

    openScrimModal() {
      const form = document.getElementById("post-scrim-form");
      if (form) form.reset();
      qs("#scrim-error")?.classList.add("hidden");
      Modal.open("modal-post-scrim");
    },

    async submitScrim() {
      const btn = qs("#scrim-submit");
      const errEl = qs("#scrim-error");
      btn.disabled = true; btn.textContent = "Posting…";
      try {
        const payload = {
          date: qs("#scrim-date")?.value,
          time: qs("#scrim-time")?.value,
          format: qs("#scrim-format")?.value,
          notes: qs("#scrim-notes")?.value.trim(),
        };
        const data = await api("training/scrims/", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        toast(data.message || "Scrim request posted!");
        Modal.close("modal-post-scrim");
        this.loadData();
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Post LFG";
      }
    },

    openVodModal() {
      const form = document.getElementById("add-vod-form");
      if (form) form.reset();
      qs("#vod-error")?.classList.add("hidden");
      Modal.open("modal-add-vod");
    },

    async submitVod() {
      const btn = qs("#vod-submit");
      const errEl = qs("#vod-error");
      btn.disabled = true; btn.textContent = "Adding…";
      try {
        const payload = {
          title: qs("#vod-title")?.value.trim(),
          url: qs("#vod-url")?.value.trim(),
          category: qs("#vod-category")?.value,
          notes: qs("#vod-notes")?.value.trim(),
        };
        const data = await api("training/vods/", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        toast(data.message || "VOD added!");
        Modal.close("modal-add-vod");
        this.loadData();
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Add VOD";
      }
    },

    filterScrims() {
      // Client-side filter of rendered scrims
      const status = qs("#scrim-filter-status")?.value || "";
      const type = qs("#scrim-filter-type")?.value || "";
      qsa("#scrim-list [data-scrim]").forEach(el => {
        const show = (!status || el.dataset.status === status) && (!type || el.dataset.type === type);
        el.style.display = show ? "" : "none";
      });
    },

    filterVods(tab) {
      // Update tab UI
      qsa(".vod-tab").forEach(t => {
        const isActive = t.dataset.vodTab === tab;
        t.classList.toggle("bg-white/10", isActive);
        t.classList.toggle("text-white", isActive);
        t.classList.toggle("text-white/50", !isActive);
      });
      // Client-side filter
      qsa("#vod-library-grid [data-vod-cat]").forEach(el => {
        el.style.display = (tab === "all" || el.dataset.vodCat === tab) ? "" : "none";
      });
    },

    renderSessions(sessions) {
      const container = qs("#upcoming-sessions");
      if (!container || !sessions.length) return;
      container.innerHTML = sessions.map(s => `
        <div class="rounded-xl border border-cyan-500/15 bg-cyan-500/5 p-3 flex items-center gap-3">
          <div class="h-10 w-10 rounded-lg bg-cyan-500/15 grid place-items-center shrink-0">
            <i data-lucide="calendar" class="w-4 h-4 text-cyan-400"></i>
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold truncate">${esc(s.title)}</p>
            <p class="text-xs text-white/40">${esc(s.date)} at ${esc(s.time)} · ${esc(s.duration || "")}min · ${esc(s.type || "")}</p>
          </div>
        </div>
      `).join("");
      if (window.lucide) lucide.createIcons({ nodes: [container] });
    },

    renderScrims(scrims) {
      const container = qs("#scrim-list");
      if (!container || !scrims.length) return;
      container.innerHTML = scrims.map(s => `
        <div class="rounded-xl border border-emerald-500/15 bg-emerald-500/5 p-3 flex items-center gap-3" data-scrim data-status="${esc(s.status)}" data-type="${esc(s.format)}">
          <div class="h-10 w-10 rounded-lg bg-emerald-500/15 grid place-items-center shrink-0">
            <i data-lucide="swords" class="w-4 h-4 text-emerald-400"></i>
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold">${esc(s.format)} · ${esc(s.date)}</p>
            <p class="text-xs text-white/40">${esc(s.notes || "No notes")}</p>
          </div>
          <span class="text-[10px] px-1.5 py-0.5 rounded-full ${s.status === 'open' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-white/8 text-white/40'}">${esc(s.status)}</span>
        </div>
      `).join("");
      if (window.lucide) lucide.createIcons({ nodes: [container] });
    },

    renderVods(vods) {
      const grid = qs("#vod-library-grid");
      if (!grid || !vods.length) return;
      grid.innerHTML = vods.map(v => `
        <a href="${esc(v.url)}" target="_blank" rel="noopener"
           class="rounded-xl border border-white/10 bg-white/5 p-3 hover:bg-white/8 transition block" data-vod-cat="${esc(v.category)}">
          <div class="h-20 rounded-lg bg-purple-500/10 grid place-items-center mb-2">
            <i data-lucide="play-circle" class="w-6 h-6 text-purple-400/60"></i>
          </div>
          <p class="text-xs font-semibold truncate">${esc(v.title)}</p>
          <p class="text-[10px] text-white/40 mt-0.5">${esc(v.category)}</p>
        </a>
      `).join("");
      if (window.lucide) lucide.createIcons({ nodes: [grid] });
    },

    renderBounties(bounties) {
      const container = qs("#bounty-list");
      if (!container || !bounties.length) return;
      container.innerHTML = bounties.map(b => `
        <div class="rounded-xl border border-amber-500/15 bg-amber-500/5 p-3 flex items-center gap-3">
          <div class="h-10 w-10 rounded-lg bg-amber-500/15 grid place-items-center shrink-0">
            <i data-lucide="flame" class="w-4 h-4 text-amber-400"></i>
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold">${esc(b.title)}</p>
            <p class="text-xs text-white/40 mt-0.5">${esc(b.description || "")}</p>
          </div>
          <div class="text-right shrink-0">
            <span class="text-xs font-bold text-amber-400">${b.reward || 0} pts</span>
            ${b.deadline ? `<p class="text-[10px] text-white/30 mt-0.5">${esc(b.deadline)}</p>` : ""}
          </div>
        </div>
      `).join("");
      if (window.lucide) lucide.createIcons({ nodes: [container] });
    },

    updateScrimStats(stats) {
      const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
      el("scrim-stat-total", stats.total || 0);
      el("scrim-stat-wins", stats.wins || 0);
      el("scrim-stat-losses", stats.losses || 0);
    },
  };

  /* ═══════════════════════════════════════════════════════════════════════
     COMMUNITY & MEDIA
     ═══════════════════════════════════════════════════════════════════════ */
  const Community = {
    _loaded: false,

    init() {
      const section = document.getElementById("community");
      if (!section) return;
      const observer = new MutationObserver(() => {
        if (section.classList.contains("is-active") && !this._loaded) {
          this._loaded = true;
          this.loadData();
        }
      });
      observer.observe(section, { attributes: true, attributeFilter: ["class"] });

      // Form handlers
      const postForm = document.getElementById("new-post-form");
      if (postForm) postForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitPost(); });

      const mediaForm = document.getElementById("upload-media-form");
      if (mediaForm) mediaForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitMedia(); });

      const highlightForm = document.getElementById("add-highlight-form");
      if (highlightForm) highlightForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitHighlight(); });

      // Media file preview
      const fileInput = document.getElementById("media-file-input");
      if (fileInput) {
        fileInput.addEventListener("change", () => {
          const file = fileInput.files?.[0];
          if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
              qs("#media-preview-img").src = e.target.result;
              qs("#media-file-preview")?.classList.remove("hidden");
            };
            reader.readAsDataURL(file);
          }
        });
      }
    },

    async loadData() {
      try {
        const data = await api(`${API}/community/`, { method: "GET" });
        if (data.posts) this.renderFeed(data.posts);
        if (data.gallery) this.renderGallery(data.gallery);
        if (data.highlights) this.renderHighlights(data.highlights);
      } catch {
        // API not yet available — leave placeholders
      }
    },

    openPostModal() {
      const form = document.getElementById("new-post-form");
      if (form) form.reset();
      qs("#post-error")?.classList.add("hidden");
      Modal.open("modal-new-post");
    },

    async submitPost() {
      const btn = qs("#post-submit");
      const errEl = qs("#post-error");
      btn.disabled = true; btn.textContent = "Publishing…";
      try {
        const postType = document.querySelector('input[name="post_type"]:checked')?.value || "update";
        const payload = {
          type: postType,
          content: qs("#post-content")?.value.trim(),
          pinned: qs("#post-pin")?.checked || false,
        };
        const data = await api("community/posts/", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        toast(data.message || "Post published!");
        Modal.close("modal-new-post");
        this.loadData();
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Publish";
      }
    },

    openMediaUpload() {
      const form = document.getElementById("upload-media-form");
      if (form) form.reset();
      qs("#media-error")?.classList.add("hidden");
      qs("#media-file-preview")?.classList.add("hidden");
      Modal.open("modal-upload-media");
    },

    async submitMedia() {
      const btn = qs("#media-submit");
      const errEl = qs("#media-error");
      const fileInput = document.getElementById("media-file-input");
      const file = fileInput?.files?.[0];
      if (!file) { errEl.textContent = "Select a file to upload."; errEl.classList.remove("hidden"); return; }

      btn.disabled = true; btn.textContent = "Uploading…";
      try {
        const fd = new FormData();
        fd.append("title", qs("#media-title")?.value.trim());
        fd.append("category", qs("#media-category")?.value);
        fd.append("file", file);
        const data = await api("community/media/", {
          method: "POST",
          body: fd,
          headers: { "X-CSRFToken": CSRF },
        });
        toast(data.message || "Media uploaded!");
        Modal.close("modal-upload-media");
        this.loadData();
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Upload";
      }
    },

    openHighlightModal() {
      const form = document.getElementById("add-highlight-form");
      if (form) form.reset();
      qs("#highlight-error")?.classList.add("hidden");
      Modal.open("modal-add-highlight");
    },

    async submitHighlight() {
      const btn = qs("#highlight-submit");
      const errEl = qs("#highlight-error");
      btn.disabled = true; btn.textContent = "Adding…";
      try {
        const payload = {
          title: qs("#highlight-title")?.value.trim(),
          url: qs("#highlight-url")?.value.trim(),
          description: qs("#highlight-desc")?.value.trim(),
        };
        const data = await api("community/highlights/", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        toast(data.message || "Highlight added!");
        Modal.close("modal-add-highlight");
        this.loadData();
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Add Highlight";
      }
    },

    filterGallery(tab) {
      qsa(".gallery-tab").forEach(t => {
        const isActive = t.dataset.galleryTab === tab;
        t.classList.toggle("bg-white/10", isActive);
        t.classList.toggle("text-white", isActive);
        t.classList.toggle("text-white/50", !isActive);
      });
      qsa("#media-gallery-grid [data-gallery-cat]").forEach(el => {
        el.style.display = (tab === "all" || el.dataset.galleryCat === tab) ? "" : "none";
      });
    },

    /* ── Communications Modal ── */
    openCommsModal() {
      // Pre-fill current values from the display cards
      const discordEl = qs("#comms-discord-url");
      const whatsappEl = qs("#comms-whatsapp-url");
      const messengerEl = qs("#comms-messenger-url");
      // Read current values from data attributes on the section
      const section = qs("#comms-section");
      if (section) {
        if (discordEl) discordEl.value = section.dataset.discord || "";
        if (whatsappEl) whatsappEl.value = section.dataset.whatsapp || "";
        if (messengerEl) messengerEl.value = section.dataset.messenger || "";
      }
      qs("#comms-error")?.classList.add("hidden");
      Modal.open("modal-comms");
    },

    async saveComms() {
      const btn = qs("#comms-submit");
      const errEl = qs("#comms-error");
      btn.disabled = true; btn.textContent = "Saving…";
      try {
        const payload = {
          discord_url: qs("#comms-discord-url")?.value.trim() || "",
          whatsapp: qs("#comms-whatsapp-url")?.value.trim() || "",
          messenger: qs("#comms-messenger-url")?.value.trim() || "",
        };
        await api("profile/", { method: "POST", body: JSON.stringify(payload) });
        toast("Communication links saved! Refreshing…");
        Modal.close("modal-comms");
        setTimeout(() => location.reload(), 600);
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Save Links";
      }
    },

    async testDiscordWebhook() {
      const btn = qs("#btn-test-discord");
      if (!btn) return;
      const orig = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="animate-pulse">Testing…</span>';
      try {
        const res = await api("discord/test-webhook/", { method: "POST" });
        toast(res.message || "Test sent to Discord!", "success");
        btn.innerHTML = '<i data-lucide="check" class="w-3 h-3 inline -mt-0.5"></i> Sent';
        if (window.lucide) lucide.createIcons();
        setTimeout(() => { btn.innerHTML = orig; btn.disabled = false; if (window.lucide) lucide.createIcons(); }, 3000);
      } catch (err) {
        toast(err.message || "Webhook test failed", "error");
        btn.innerHTML = orig; btn.disabled = false;
        if (window.lucide) lucide.createIcons();
      }
    },

    renderFeed(posts) {
      const container = qs("#team-feed");
      if (!container || !posts.length) return;
      container.innerHTML = posts.map(p => `
        <div class="rounded-xl border border-white/8 bg-white/3 p-4 ${p.pinned ? 'border-l-2 border-l-pink-400' : ''}">
          <div class="flex items-center gap-2 mb-2">
            <div class="h-7 w-7 rounded-full bg-white/10 grid place-items-center shrink-0">
              <span class="text-[10px] font-bold">${esc((p.author || "?")[0].toUpperCase())}</span>
            </div>
            <div class="min-w-0">
              <span class="text-xs font-semibold">${esc(p.author || "Team")}</span>
              <span class="text-[10px] text-white/30 ml-1.5">${esc(p.time_ago || "")}</span>
            </div>
            ${p.pinned ? '<i data-lucide="pin" class="w-3 h-3 text-pink-400 ml-auto shrink-0"></i>' : ''}
          </div>
          <p class="text-sm text-white/80 leading-relaxed">${esc(p.content)}</p>
          ${p.type !== "update" ? `<span class="inline-block mt-2 text-[10px] px-1.5 py-0.5 rounded-full bg-white/5 text-white/40">${esc(p.type)}</span>` : ""}
        </div>
      `).join("");
      if (window.lucide) lucide.createIcons({ nodes: [container] });
    },

    renderGallery(items) {
      const grid = qs("#media-gallery-grid");
      if (!grid || !items.length) return;
      const countEl = qs("#gallery-count");
      if (countEl) countEl.textContent = `${items.length} item${items.length > 1 ? "s" : ""}`;
      grid.innerHTML = items.map(m => `
        <div class="rounded-xl border border-white/10 overflow-hidden group cursor-pointer" data-gallery-cat="${esc(m.category)}">
          <div class="aspect-square bg-violet-500/5 relative overflow-hidden">
            ${m.url ? `<img src="${esc(m.url)}" alt="${esc(m.title)}" class="w-full h-full object-cover">` :
              `<div class="grid place-items-center h-full"><i data-lucide="image" class="w-6 h-6 text-white/15"></i></div>`}
            <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition grid place-items-center">
              <i data-lucide="expand" class="w-5 h-5 text-white/80"></i>
            </div>
          </div>
          <div class="p-2">
            <p class="text-[10px] font-medium truncate">${esc(m.title)}</p>
          </div>
        </div>
      `).join("");
      if (window.lucide) lucide.createIcons({ nodes: [grid] });
    },

    renderHighlights(highlights) {
      const grid = qs("#highlights-grid");
      if (!grid || !highlights.length) return;
      grid.innerHTML = highlights.map(h => `
        <a href="${esc(h.url)}" target="_blank" rel="noopener"
           class="rounded-xl border border-white/10 bg-white/5 hover:bg-white/8 transition block overflow-hidden">
          <div class="h-28 bg-rose-500/5 grid place-items-center">
            <i data-lucide="play-circle" class="w-8 h-8 text-rose-400/40"></i>
          </div>
          <div class="p-3">
            <p class="text-xs font-semibold truncate">${esc(h.title)}</p>
            ${h.description ? `<p class="text-[10px] text-white/40 mt-0.5 line-clamp-2">${esc(h.description)}</p>` : ""}
          </div>
        </a>
      `).join("");
      if (window.lucide) lucide.createIcons({ nodes: [grid] });
    },
  };

  /* ═══════════════════════════════════════════════════════════════════════
     DISCORD INTEGRATION
     Bi-directional chat sync, config management, voice join.
     ═══════════════════════════════════════════════════════════════════════ */
  const Discord = {
    pollInterval: null,
    botStatusInterval: null,
    lastMessageId: 0,
    _configOpen: false,

    init() {
      // Config form
      const form = document.getElementById("discordConfigForm");
      if (form) form.addEventListener("submit", (e) => { e.preventDefault(); this.saveConfig(); });

      // Config panel toggle (Item 1 — collapse / expand)
      const toggleBtn = document.getElementById("discordConfigToggle");
      if (toggleBtn) toggleBtn.addEventListener("click", () => this.toggleConfigPanel());

      // Cancel button — collapse back to View Mode
      const cancelBtn = document.getElementById("discordCancelEditBtn");
      if (cancelBtn) cancelBtn.addEventListener("click", () => {
        this._configOpen = true; // force state so toggle flips to false
        this.toggleConfigPanel();
      });

      // Smart URL → ID extraction on all .discord-id-input fields
      document.querySelectorAll('.discord-id-input').forEach(inp => {
        inp.addEventListener('paste', (e) => {
          // Defer so pasted value is in the input
          setTimeout(() => this._extractDiscordId(inp), 0);
        });
        inp.addEventListener('blur', () => this._extractDiscordId(inp));
      });

      // Community Invite URL validation
      const inviteInput = document.getElementById('discordInviteUrlInput');
      if (inviteInput) {
        inviteInput.addEventListener('blur', () => this._validateInviteUrl(inviteInput));
        inviteInput.addEventListener('input', () => {
          // Clear error state on edit
          inviteInput.classList.remove('border-red-500/50', 'ring-1', 'ring-red-500/30');
          const err = inviteInput.parentElement?.querySelector('.invite-url-error');
          if (err) err.remove();
        });
      }

      // Webhook reveal toggle
      const revealBtn = document.getElementById('discordWebhookReveal');
      const webhookInput = document.getElementById('discordWebhookInput');
      if (revealBtn && webhookInput) {
        revealBtn.addEventListener('click', () => {
          const isPassword = webhookInput.type === 'password';
          webhookInput.type = isPassword ? 'url' : 'password';
          revealBtn.querySelector('span').textContent = isPassword ? 'Hide URL' : 'Show URL';
          const icon = revealBtn.querySelector('[data-lucide]');
          if (icon) { icon.setAttribute('data-lucide', isPassword ? 'eye-off' : 'eye'); if (window.lucide) lucide.createIcons({ nodes: [revealBtn] }); }
        });
      }

      // If no guild_id is set, auto-expand config panel on first visit
      const panel = document.getElementById("discordConfigPanel");
      if (panel && !panel.classList.contains("hidden")) {
        this._configOpen = true;
        this._updateToggleUI();
      }

      // Chat send form
      const chatForm = document.getElementById("chatSendForm");
      if (chatForm) chatForm.addEventListener("submit", (e) => { e.preventDefault(); this.sendChat(); });

      // Start chat: load history, connect WebSocket, fallback to polling
      const chatEl = document.getElementById("chatMessages");
      if (chatEl && chatEl.dataset.teamSlug) {
        this._currentUserId = parseInt(chatEl.dataset.currentUserId, 10) || 0;
        this._timeFormat = chatEl.dataset.timeFormat || '12h';
        this._teamId = chatEl.dataset.teamId;
        this.loadChatHistory();
        this._connectWebSocket();
      }

      // Bot status auto-polling (every 10s when bot is offline)
      this._startBotStatusPolling();

      // Smart Voice Join — discord:// deep-link with fallback (Item 3)
      document.querySelectorAll(".discord-voice-join").forEach(btn => {
        btn.addEventListener("click", () => this.joinVoice(btn));
      });
    },

    /* ── Config panel collapse / expand (Item 1) ── */
    toggleConfigPanel() {
      this._configOpen = !this._configOpen;
      const panel = document.getElementById("discordConfigPanel");
      const summary = document.getElementById("discordConfigSummary");
      if (panel) panel.classList.toggle("hidden", !this._configOpen);
      if (summary) summary.classList.toggle("hidden", this._configOpen);
      this._updateToggleUI();
    },

    _updateToggleUI() {
      const label = document.getElementById("discordConfigToggleLabel");
      const chevron = document.getElementById("discordConfigChevron");
      const btn = document.getElementById("discordConfigToggle");
      if (label) label.textContent = this._configOpen ? "Close" : "Edit Configuration";
      if (chevron) chevron.style.transform = this._configOpen ? "rotate(180deg)" : "";
      if (btn) btn.setAttribute("aria-expanded", this._configOpen ? "true" : "false");
    },

    /**
     * Smart extraction: if user pastes a full Discord URL or anything
     * containing a snowflake ID, extract just the numeric ID.
     * e.g. "https://discord.com/channels/123/456" → "456" (last segment)
     *      "discord.gg/AbCdE" → left alone (not a numeric ID)
     */
    _extractDiscordId(input) {
      const val = (input.value || '').trim();
      if (!val) return;
      // Already a pure numeric ID — leave as-is
      if (/^\d{15,22}$/.test(val)) return;
      // Try to extract the last numeric snowflake from a URL path
      const urlMatch = val.match(/(?:channels|guilds)\/(\d{15,22})(?:\/(\d{15,22}))?/);
      if (urlMatch) {
        // Use the last captured group (most specific — channel > guild)
        input.value = urlMatch[2] || urlMatch[1];
        input.classList.add('border-emerald-500/40');
        setTimeout(() => input.classList.remove('border-emerald-500/40'), 2000);
        return;
      }
      // Fallback: find any 15-22 digit number in the string
      const snowflake = val.match(/(\d{15,22})/);
      if (snowflake) {
        input.value = snowflake[1];
        input.classList.add('border-emerald-500/40');
        setTimeout(() => input.classList.remove('border-emerald-500/40'), 2000);
      }
    },

    /**
     * Validate Community Invite URL — must be discord.gg/ or discord.com/invite/
     */
    _validateInviteUrl(input) {
      const val = (input.value || '').trim();
      if (!val) return true; // optional field
      const valid = /^https:\/\/(discord\.gg|discord\.com\/invite)\/[a-zA-Z0-9\-]+/.test(val);
      if (!valid) {
        input.classList.add('border-red-500/50', 'ring-1', 'ring-red-500/30');
        // Add error message if not already present
        if (!input.parentElement?.querySelector('.invite-url-error')) {
          const msg = document.createElement('p');
          msg.className = 'invite-url-error text-[10px] text-red-400/80 mt-1';
          msg.textContent = 'Must be a discord.gg/ or discord.com/invite/ link';
          input.parentElement?.appendChild(msg);
        }
        return false;
      }
      return true;
    },

    async saveConfig() {
      const form = document.getElementById("discordConfigForm");
      if (!form) return;

      // Validate invite URL before saving
      const inviteInput = document.getElementById('discordInviteUrlInput');
      if (inviteInput && !this._validateInviteUrl(inviteInput)) {
        toast("Invalid Community Invite URL — must be a discord.gg/ link", "error");
        return;
      }

      const statusEl = document.getElementById("discordSaveStatus");
      const data = {};
      form.querySelectorAll("input[name]").forEach((inp) => { data[inp.name] = inp.value.trim(); });

      try {
        const res = await api("discord/save/", { method: "POST", body: JSON.stringify(data) });
        if (statusEl) {
          statusEl.textContent = res.message || "Saved!";
          statusEl.classList.remove("hidden");
          setTimeout(() => statusEl.classList.add("hidden"), 4000);
        }
        toast("Discord configuration saved!", "success");
        // Update bot status indicator
        if (res.discord_bot_active !== undefined) {
          this._updateBotStatusUI(res.discord_bot_active);
        }
        // Collapse config panel after successful save (Item 1)
        if (data.discord_guild_id) {
          this._configOpen = false;
          const panel = document.getElementById("discordConfigPanel");
          const summary = document.getElementById("discordConfigSummary");
          if (panel) panel.classList.add("hidden");
          // Rebuild summary badges from the just-saved data
          if (summary) {
            const isOnline = !!res.discord_bot_active;
            const statusIcon = isOnline ? 'bg-emerald-500/15' : 'bg-red-500/10';
            const statusIconText = isOnline ? 'text-emerald-400' : 'text-red-400';
            const statusText = isOnline ? '✅ Active' : '🔴 Disconnected';
            const statusTextCls = isOnline ? 'text-emerald-300' : 'text-red-400';
            const heroBorder = isOnline ? 'border-emerald-500/15 bg-emerald-500/[0.03]' : 'border-red-500/15 bg-red-500/[0.03]';

            // Mask guild ID: show first 4 + last 4 with … in middle
            const gid = esc(data.discord_guild_id);
            const maskedGid = gid.length > 8 ? gid.slice(0, 4) + '…' + gid.slice(-4) : gid;

            let html = `<div id="discordViewHero" class="rounded-2xl border ${heroBorder} px-4 py-3.5 mb-3">
              <div class="flex items-center gap-3">
                <div class="h-10 w-10 rounded-xl ${statusIcon} grid place-items-center shrink-0">
                  <svg class="w-5 h-5 ${statusIconText}" viewBox="0 0 24 24" fill="currentColor"><path d="M20.317 4.37a19.79 19.79 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.865-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.618-1.25.077.077 0 00-.079-.037A19.74 19.74 0 003.677 4.37a.07.07 0 00-.032.028C.533 9.046-.32 13.58.099 18.058a.082.082 0 00.031.056c2.053 1.508 4.041 2.423 5.993 3.03a.077.077 0 00.084-.028c.462-.63.873-1.295 1.226-1.994a.076.076 0 00-.041-.106 13.11 13.11 0 01-1.872-.892.077.077 0 01-.008-.128c.126-.094.252-.192.372-.291a.074.074 0 01.078-.01c3.928 1.793 8.18 1.793 12.061 0a.074.074 0 01.079.01c.12.099.245.197.372.291a.077.077 0 01-.006.128 12.3 12.3 0 01-1.873.891.076.076 0 00-.041.107c.36.698.772 1.363 1.225 1.993a.076.076 0 00.084.028c1.961-.607 3.95-1.522 6.002-3.029a.077.077 0 00.031-.055c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.029z"/></svg>
                </div>
                <div class="flex-1 min-w-0">
                  <p id="discordViewStatusText" class="text-sm font-bold ${statusTextCls}">${statusText}</p>
                  <p class="text-[11px] text-white/40 mt-0.5 truncate">Linked to Server: <span class="font-mono text-white/50">${maskedGid}</span></p>
                </div>
              </div>
            </div>`;

            let badges = '';
            if (data.discord_chat_channel_id)
              badges += `<div class="flex items-center gap-2 rounded-xl bg-indigo-500/5 border border-indigo-500/15 px-3 py-2"><i data-lucide="message-circle" class="w-3.5 h-3.5 text-indigo-400 shrink-0"></i><span class="text-xs text-indigo-300 truncate">Chat synced</span></div>`;
            if (data.discord_voice_channel_id)
              badges += `<div class="flex items-center gap-2 rounded-xl bg-emerald-500/5 border border-emerald-500/15 px-3 py-2"><i data-lucide="headphones" class="w-3.5 h-3.5 text-emerald-400 shrink-0"></i><span class="text-xs text-emerald-300 truncate">Voice ready</span></div>`;
            if (data.discord_announcement_channel_id)
              badges += `<div class="flex items-center gap-2 rounded-xl bg-amber-500/5 border border-amber-500/15 px-3 py-2"><i data-lucide="megaphone" class="w-3.5 h-3.5 text-amber-400 shrink-0"></i><span class="text-xs text-amber-300 truncate">Announcements on</span></div>`;
            if (data.discord_webhook_url)
              badges += `<div class="flex items-center gap-2 rounded-xl bg-violet-500/5 border border-violet-500/15 px-3 py-2"><i data-lucide="webhook" class="w-3.5 h-3.5 text-violet-400 shrink-0"></i><span class="text-xs text-violet-300 truncate">Webhook ••••••••</span></div>`;
            if (data.discord_captain_role_id)
              badges += `<div class="flex items-center gap-2 rounded-xl bg-yellow-500/5 border border-yellow-500/15 px-3 py-2"><i data-lucide="shield" class="w-3.5 h-3.5 text-yellow-400 shrink-0"></i><span class="text-xs text-yellow-300 truncate">Captain role synced</span></div>`;
            if (data.discord_manager_role_id)
              badges += `<div class="flex items-center gap-2 rounded-xl bg-yellow-500/5 border border-yellow-500/15 px-3 py-2"><i data-lucide="shield-check" class="w-3.5 h-3.5 text-yellow-400 shrink-0"></i><span class="text-xs text-yellow-300 truncate">Manager role synced</span></div>`;
            if (badges) html += `<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">${badges}</div>`;
            summary.innerHTML = html;
            summary.classList.remove("hidden");
            if (window.lucide) lucide.createIcons({ nodes: [summary] });
          }
          this._updateToggleUI();
        }
      } catch (err) {
        toast(err.message || "Failed to save Discord config", "error");
      }
    },

    /* ── Bot Status Auto-Polling ── */
    _startBotStatusPolling() {
      const botEl = document.getElementById("discordBotStatus");
      if (!botEl) return;
      // Poll every 10s
      this.botStatusInterval = setInterval(() => this._pollBotStatus(), 10000);
    },

    async _pollBotStatus() {
      try {
        const res = await api("discord/", { method: "GET" });
        this._updateBotStatusUI(res.discord_bot_active);
      } catch (_) { /* silent — network hiccup */ }
    },

    _updateBotStatusUI(isOnline) {
      // Header badge
      const botEl = document.getElementById("discordBotStatus");
      if (botEl) {
        botEl.innerHTML = isOnline
          ? '<span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span><span class="text-emerald-400 font-medium">Bot Online</span>'
          : '<span class="h-2 w-2 rounded-full bg-red-400/60"></span><span class="text-red-400/80 font-medium">Bot Offline</span>';
      }
      // Update the View Mode summary hero card if visible
      const summary = document.getElementById("discordConfigSummary");
      if (summary && !summary.classList.contains("hidden")) {
        const heroStatus = document.getElementById('discordViewStatusText');
        if (heroStatus) {
          heroStatus.className = `text-sm font-bold ${isOnline ? 'text-emerald-300' : 'text-red-400'}`;
          heroStatus.textContent = isOnline ? '✅ Active' : '🔴 Disconnected';
        }
        const heroCard = document.getElementById('discordViewHero');
        if (heroCard) {
          heroCard.className = `rounded-2xl border ${isOnline ? 'border-emerald-500/15 bg-emerald-500/[0.03]' : 'border-red-500/15 bg-red-500/[0.03]'} px-4 py-3.5 mb-3`;
        }
        const heroBg = summary.querySelector('.h-10.w-10');
        if (heroBg) {
          heroBg.className = `h-10 w-10 rounded-xl ${isOnline ? 'bg-emerald-500/15' : 'bg-red-500/10'} grid place-items-center shrink-0`;
          const svg = heroBg.querySelector('svg');
          if (svg) svg.className.baseVal = `w-5 h-5 ${isOnline ? 'text-emerald-400' : 'text-red-400'}`;
        }
      }
    },

    /* ── Smart Voice Join — discord:// deep-link with fallback (Item 3) ── */
    joinVoice(btn) {
      const guildId = btn.dataset.guildId;
      const channelId = btn.dataset.channelId;
      if (!guildId || !channelId) return;

      const webUrl = `https://discord.com/channels/${guildId}/${channelId}`;
      const deepLink = `discord://discord.com/channels/${guildId}/${channelId}`;

      // Try the discord:// protocol first. If the app isn't installed,
      // the iframe trick silently fails and we fall back to the web URL.
      const iframe = document.createElement("iframe");
      iframe.style.display = "none";
      iframe.src = deepLink;
      document.body.appendChild(iframe);

      // Fallback: open browser link after a short delay
      const fallbackTimer = setTimeout(() => {
        window.open(webUrl, "_blank", "noopener");
      }, 1500);

      // If the page loses focus, the app opened — cancel the fallback
      const onBlur = () => {
        clearTimeout(fallbackTimer);
        window.removeEventListener("blur", onBlur);
      };
      window.addEventListener("blur", onBlur);

      // Cleanup iframe
      setTimeout(() => { if (iframe.parentNode) iframe.parentNode.removeChild(iframe); }, 3000);
    },

    async loadChatHistory() {
      try {
        const res = await api("discord/chat/", { method: "GET" });
        const container = document.getElementById("chatMessages");
        if (!container || !res.messages) return;

        if (res.messages.length === 0) {
          container.innerHTML = '<div class="flex items-center justify-center h-full"><p class="text-sm text-white/30">No messages yet. Say something!</p></div>';
          return;
        }

        container.innerHTML = res.messages.map(m => this._renderMessage(m)).join("");
        this.lastMessageId = res.messages[res.messages.length - 1].id;
        container.scrollTop = container.scrollHeight;
      } catch (err) {
        console.warn("Discord chat load failed:", err);
      }
    },

    /* ── WebSocket connection for real-time chat ── */
    _connectWebSocket() {
      if (!this._teamId) { this.startPolling(); return; }
      try {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${proto}//${location.host}/ws/teams/${this._teamId}/`;
        this._ws = new WebSocket(wsUrl);

        this._ws.onopen = () => {
          console.debug('[Chat] WebSocket connected');
          const indicator = document.getElementById("chatWsStatus");
          if (indicator) indicator.classList.remove("hidden");
          // Stop polling if it was running
          if (this.pollInterval) { clearInterval(this.pollInterval); this.pollInterval = null; }
        };

        this._ws.onmessage = (evt) => {
          try {
            const data = JSON.parse(evt.data);
            if (data.type === 'chat.message') {
              this._handleIncomingMessage(data);
            }
          } catch (_) { /* non-JSON or irrelevant event */ }
        };

        this._ws.onclose = () => {
          console.debug('[Chat] WebSocket closed — falling back to polling');
          const indicator = document.getElementById("chatWsStatus");
          if (indicator) indicator.classList.add("hidden");
          // Reconnect after 3s, or fall back to polling
          this._wsReconnectTimer = setTimeout(() => this._connectWebSocket(), 3000);
        };

        this._ws.onerror = () => {
          console.debug('[Chat] WebSocket error — falling back to polling');
          this._ws.close();
          this.startPolling();
        };
      } catch (_) {
        this.startPolling();
      }
    },

    _handleIncomingMessage(data) {
      // Deduplicate — don't render if we already have this message ID
      const container = document.getElementById("chatMessages");
      if (!container) return;
      const msgId = data.id;
      if (msgId && container.querySelector(`[data-msg-id="${msgId}"]`)) return;

      // Remove "no messages" placeholder
      const placeholder = container.querySelector(".text-white\\/30");
      if (placeholder && placeholder.closest(".flex.items-center.justify-center")) {
        container.innerHTML = "";
      }

      container.insertAdjacentHTML("beforeend", this._renderMessage(data));
      if (msgId) this.lastMessageId = Math.max(this.lastMessageId || 0, msgId);
      container.scrollTop = container.scrollHeight;
    },

    startPolling() {
      if (this.pollInterval) return; // already polling
      this.pollInterval = setInterval(async () => {
        try {
          const indicator = document.getElementById("chatSyncIndicator");
          if (indicator) indicator.classList.remove("hidden");

          const res = await api(`discord/chat/?after=${this.lastMessageId}`, { method: "GET" });
          if (res.messages && res.messages.length > 0) {
            const container = document.getElementById("chatMessages");
            if (!container) return;
            const placeholder = container.querySelector(".text-white\\/30");
            if (placeholder && placeholder.closest(".flex.items-center.justify-center")) {
              container.innerHTML = "";
            }
            res.messages.forEach(m => {
              if (!container.querySelector(`[data-msg-id="${m.id}"]`)) {
                container.insertAdjacentHTML("beforeend", this._renderMessage(m));
              }
            });
            this.lastMessageId = res.messages[res.messages.length - 1].id;
            container.scrollTop = container.scrollHeight;
          }

          if (indicator) setTimeout(() => indicator.classList.add("hidden"), 500);
        } catch (_) { /* silent */ }
      }, 3000);
    },

    async sendChat() {
      const input = document.getElementById("chatInput");
      if (!input) return;
      const content = input.value.trim();
      if (!content) return;

      input.value = "";
      try {
        const res = await api("discord/chat/send/", { method: "POST", body: JSON.stringify({ content }) });
        if (res.message) {
          this._handleIncomingMessage(res.message);
        }
      } catch (err) {
        toast(err.message || "Failed to send message", "error");
        input.value = content;
      }
    },

    /* ── Lightweight Markdown parser for Discord-style formatting ── */
    _parseMd(text) {
      let s = esc(text);
      // Code blocks ``` ... ``` (must be before inline code)
      s = s.replace(/```([^`]+?)```/g, '<pre class="bg-white/5 rounded-lg px-3 py-2 my-1 text-xs font-mono overflow-x-auto whitespace-pre-wrap">$1</pre>');
      // Inline code `...`
      s = s.replace(/`([^`]+?)`/g, '<code class="bg-white/10 rounded px-1 py-0.5 text-xs font-mono">$1</code>');
      // Bold **...**
      s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      // Italic *...*
      s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
      // Underline __...__
      s = s.replace(/__(.+?)__/g, '<u>$1</u>');
      // Strikethrough ~~...~~
      s = s.replace(/~~(.+?)~~/g, '<del class="text-white/40">$1</del>');
      // Spoiler ||...||  (click to reveal)
      s = s.replace(/\|\|(.+?)\|\|/g, '<span class="bg-white/20 text-transparent hover:text-white/80 rounded px-1 cursor-pointer transition select-all" title="Spoiler">$1</span>');
      // URLs
      s = s.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener" class="text-indigo-400 hover:underline break-all">$1</a>');
      // Newlines
      s = s.replace(/\n/g, '<br>');
      return s;
    },

    /* ── Time formatter respecting user preference ── */
    _formatTime(isoStr) {
      if (!isoStr) return '';
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return '';
      const now = new Date();
      const isToday = d.toDateString() === now.toDateString();
      const yesterday = new Date(now); yesterday.setDate(yesterday.getDate() - 1);
      const isYesterday = d.toDateString() === yesterday.toDateString();

      const use12 = this._timeFormat === '12h';
      const timeStr = d.toLocaleTimeString([], {
        hour: '2-digit', minute: '2-digit',
        hour12: use12,
      });

      if (isToday) return timeStr;
      if (isYesterday) return `Yesterday ${timeStr}`;
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + timeStr;
    },

    /* ── Discord blurple logo SVG (inline, 12px) ── */
    _discordBadgeSvg: '<svg class="w-3 h-3 inline-block" viewBox="0 0 24 24" fill="#5865F2"><path d="M20.317 4.37a19.79 19.79 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.865-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.618-1.25.077.077 0 00-.079-.037A19.74 19.74 0 003.677 4.37a.07.07 0 00-.032.028C.533 9.046-.32 13.58.099 18.058a.082.082 0 00.031.056c2.053 1.508 4.041 2.423 5.993 3.03a.078.078 0 00.084-.028c.462-.63.873-1.295 1.226-1.994a.076.076 0 00-.041-.106 13.11 13.11 0 01-1.872-.892.077.077 0 01-.008-.128c.126-.094.252-.192.372-.291a.074.074 0 01.078-.01c3.928 1.793 8.18 1.793 12.061 0a.074.074 0 01.079.01c.12.099.245.197.372.291a.077.077 0 01-.006.128 12.3 12.3 0 01-1.873.891.076.076 0 00-.041.107c.36.698.772 1.363 1.225 1.993a.076.076 0 00.084.028c1.961-.607 3.95-1.522 6.002-3.029a.077.077 0 00.031-.055c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.029z"/></svg>',

    /* ── Modern chat bubble renderer ── */
    _renderMessage(m) {
      const isMe = m.author_id && m.author_id === this._currentUserId;
      const isDiscord = m.source === 'discord';
      const time = this._formatTime(m.timestamp);
      const content = this._parseMd(m.content || '');
      const msgId = m.id || '';

      if (isMe) {
        // ── RIGHT-ALIGNED: My message ──
        return `
          <div class="flex justify-end" data-msg-id="${msgId}">
            <div class="max-w-[75%] min-w-[60px]">
              <div class="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl rounded-tr-md px-3.5 py-2 shadow-lg shadow-indigo-500/10">
                <div class="text-sm text-white break-words leading-relaxed">${content}</div>
              </div>
              <div class="flex items-center justify-end gap-1.5 mt-1 px-1">
                <span class="text-[10px] text-white/25">${time}</span>
              </div>
            </div>
          </div>
        `;
      }

      // ── LEFT-ALIGNED: Other person's message ──
      const initial = esc((m.author || '?')[0].toUpperCase());
      const avatarHtml = m.avatar_url
        ? `<img src="${esc(m.avatar_url)}" alt="" class="h-8 w-8 rounded-full object-cover shrink-0">`
        : `<div class="h-8 w-8 rounded-full ${isDiscord ? 'bg-[#5865F2]/20' : 'bg-emerald-500/15'} grid place-items-center shrink-0">
             <span class="text-[11px] font-bold ${isDiscord ? 'text-[#5865F2]' : 'text-emerald-400'}">${initial}</span>
           </div>`;

      const discordIcon = isDiscord
        ? `<span class="ml-1 opacity-60" title="Sent from Discord">${this._discordBadgeSvg}</span>`
        : '';

      return `
        <div class="flex items-end gap-2" data-msg-id="${msgId}">
          ${avatarHtml}
          <div class="max-w-[75%] min-w-[60px]">
            <div class="flex items-center gap-1.5 mb-0.5 px-1">
              <span class="text-[11px] font-semibold ${isDiscord ? 'text-[#5865F2]/80' : 'text-white/60'}">${esc(m.author || 'Unknown')}</span>
              ${discordIcon}
            </div>
            <div class="bg-white/[0.06] backdrop-blur-sm rounded-2xl rounded-tl-md px-3.5 py-2 border border-white/[0.04]">
              <div class="text-sm text-white/80 break-words leading-relaxed">${content}</div>
            </div>
            <div class="flex items-center gap-1.5 mt-1 px-1">
              <span class="text-[10px] text-white/25">${time}</span>
            </div>
          </div>
        </div>
      `;
    },

    destroy() {
      if (this.pollInterval) clearInterval(this.pollInterval);
      if (this.botStatusInterval) clearInterval(this.botStatusInterval);
      if (this._ws) { try { this._ws.close(); } catch (_) {} }
      if (this._wsReconnectTimer) clearTimeout(this._wsReconnectTimer);
    },
  };

  /* ═══════════════════════════════════════════════════════════════════════
     TEAM PROFILE
     ═══════════════════════════════════════════════════════════════════════ */
  const Profile = {
    init() {
      const profForm = document.getElementById("profile-info-form");
      if (profForm) profForm.addEventListener("submit", (e) => { e.preventDefault(); this.saveInfo(); });

      const socialForm = document.getElementById("profile-socials-form");
      if (socialForm) socialForm.addEventListener("submit", (e) => { e.preventDefault(); this.saveSocials(); });
    },

    async saveInfo() {
      const btn = qs("#profile-info-submit");
      btn.disabled = true; btn.textContent = "Saving…";
      try {
        const payload = {};
        ["name", "tag", "region"].forEach(f => {
          const el = qs(`#profile-${f}`);
          if (el && !el.disabled) payload[f] = el.value;
        });
        if (Object.keys(payload).length === 0) {
          toast("All identity fields are currently locked.", "warning");
          return;
        }
        const res = await api("profile/", { method: "POST", body: JSON.stringify(payload) });
        // Show individual field lock warnings if any
        if (res.field_locks) {
          const locked = Object.entries(res.field_locks)
            .filter(([, v]) => v.locked)
            .map(([k]) => k);
          if (locked.length) {
            toast(`Some fields were skipped (locked): ${locked.join(', ')}`, 'warning');
          }
        }
        toast("Team info updated.");
      } catch (err) {
        const msg = err.message || "Failed to save";
        if (msg.includes("locked") || msg.includes("cooldown")) {
          toast(msg, "warning");
        } else {
          toast(msg, "error");
        }
      }
      finally { btn.disabled = false; btn.textContent = "Save Changes"; }
    },

    async saveSocials() {
      const btn = qs("#profile-socials-submit");
      btn.disabled = true; btn.textContent = "Saving…";
      try {
        const payload = {};
        ["twitter", "instagram", "youtube", "twitch", "facebook", "tiktok", "website", "discord_url", "discord_webhook", "whatsapp", "messenger"].forEach(f => {
          const el = qs(`#social-${f}`);
          if (el) payload[f] = el.value;
        });
        await api("profile/", { method: "POST", body: JSON.stringify(payload) });
        toast("Social links saved.");
      } catch (err) { toast(err.message, "error"); }
      finally { btn.disabled = false; btn.textContent = "Save Links"; }
    },

    async uploadMedia(input) {
      const type = input.dataset.mediaUpload;
      const file = input.files?.[0];
      if (!file) return;

      const preview = document.getElementById(`preview-${type}`);
      if (preview) {
        const reader = new FileReader();
        reader.onload = (e) => { preview.src = e.target.result; preview.classList.remove("hidden"); };
        reader.readAsDataURL(file);
      }

      try {
        const fd = new FormData();
        fd.append("type", type);
        fd.append("file", file);
        const data = await api("media/", {
          method: "POST",
          body: fd,
          headers: { "X-CSRFToken": CSRF },
        });
        toast(data.message || "Upload complete.");
        if (data.url && preview) preview.src = data.url;
      } catch (err) {
        toast(err.message, "error");
      }
    },
  };

  /* ═══════════════════════════════════════════════════════════════════════
     SETTINGS
     ═══════════════════════════════════════════════════════════════════════ */
  const Settings = {
    init() { /* Toggle saves are driven by inline onchange handlers */ },

    async toggle(field, value) {
      try {
        await api("settings/", {
          method: "POST",
          body: JSON.stringify({ [field]: value }),
        });
        const label = String(field).replace(/_/g, " ");
        const desc = typeof value === "boolean"
          ? `${label} ${value ? "enabled" : "disabled"}.`
          : `${label} set to ${value}.`;
        toast(desc, "info");
      } catch (err) {
        toast(err.message, "error");
        const cb = qs(`[data-setting-toggle="${field}"]`);
        if (cb) cb.checked = !value;
      }
    },

    async saveIdentity() {
      const btn = document.getElementById("identity-save-btn");
      const status = document.getElementById("identity-save-status");
      const platform  = document.getElementById("hq-field-platform")?.value || '';
      const playstyle = document.getElementById("hq-field-playstyle")?.value || '';
      const playpace  = document.getElementById("hq-field-playpace")?.value || '';
      const playfocus = document.getElementById("hq-field-playfocus")?.value || '';

      if (btn) { btn.disabled = true; btn.textContent = "Saving…"; }
      if (status) { status.textContent = ""; }

      try {
        await api("settings/", {
          method: "POST",
          body: JSON.stringify({ platform, playstyle, playpace, playfocus }),
        });
        toast("Team identity & platform saved.", "success");
        if (status) { status.textContent = "✓ Saved"; status.className = "text-[10px] text-emerald-400"; }
      } catch (err) {
        toast(err.message, "error");
        if (status) { status.textContent = "Failed to save"; status.className = "text-[10px] text-red-400"; }
      } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="save" class="w-3.5 h-3.5 inline -mt-0.5 mr-1"></i> Save Changes'; }
        if (window.lucide) lucide.createIcons();
      }
    },

    async toggleOwnerPrivacy(hide) {
      try {
        await api("owner-privacy/", {
          method: "POST",
          body: JSON.stringify({ hide_ownership: hide }),
        });
        toast(hide ? "Ownership status hidden from public" : "Ownership status visible on public page", "info");
      } catch (err) {
        toast(err.message, "error");
        const toggle = document.getElementById("hide-ownership-toggle");
        if (toggle) toggle.checked = !hide;
      }
    },

    async leaveTeam() {
      if (!confirm("Are you sure you want to leave this team? This cannot be undone.")) return;
      try {
        const data = await api("leave/", { method: "POST", body: JSON.stringify({}) });
        toast(data.message || "You have left the team.");
        setTimeout(() => { window.location.href = "/teams/"; }, 1200);
      } catch (err) {
        toast(err.message, "error");
      }
    },

    async disbandTeam() {
      const input = qs("#disband-confirm-input");
      const errEl = qs("#disband-error");
      const btn   = qs("#disband-submit-btn");
      const name  = input?.value.trim();

      if (!name) { errEl.textContent = "Please type the team name to confirm."; errEl.classList.remove("hidden"); return; }

      btn.disabled = true; btn.textContent = "Disbanding…";
      try {
        const data = await api("disband/", {
          method: "POST",
          body: JSON.stringify({ confirm: name }),
        });
        toast(data.message || "Team disbanded.");
        Modal.close("modal-disband");
        setTimeout(() => { window.location.href = data.redirect || "/teams/"; }, 1200);
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Disband Forever";
      }
    },

    async transferOwnership() {
      const memberId = qs("#transfer-member-select")?.value;
      const confirmed = qs("#transfer-confirm-cb")?.checked;
      const errEl = qs("#transfer-error");
      const btn   = qs("#transfer-submit-btn");

      if (!memberId) { errEl.textContent = "Select a member."; errEl.classList.remove("hidden"); return; }
      if (!confirmed) { errEl.textContent = "You must check the confirmation box."; errEl.classList.remove("hidden"); return; }

      btn.disabled = true; btn.textContent = "Transferring…";
      try {
        const data = await api("transfer-ownership/", {
          method: "POST",
          body: JSON.stringify({ member_id: parseInt(memberId, 10), confirm: true }),
        });
        toast(data.message || "Ownership transferred.");
        Modal.close("modal-transfer");
        setTimeout(() => location.reload(), 1000);
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Transfer Ownership";
      }
    },

    async generateInviteLink(regenerate) {
      const btn = regenerate ? qs("#invite-link-regen-btn") : qs("#invite-link-gen-btn");
      if (btn) { btn.disabled = true; }
      try {
        const data = await api("invite-link/", {
          method: "POST",
          body: JSON.stringify({ regenerate: !!regenerate }),
        });
        const display = qs("#invite-link-display");
        if (display) display.value = data.invite_url || "";
        // Show the display section, hide generate button
        qs("#invite-link-url-section")?.classList.remove("hidden");
        qs("#invite-link-gen-btn")?.classList.add("hidden");
        toast(regenerate ? "Invite link regenerated." : "Invite link generated.");
      } catch (err) {
        toast(err.message, "error");
      } finally {
        if (btn) btn.disabled = false;
      }
    },

    copyInviteLink() {
      const display = qs("#invite-link-display");
      if (!display?.value) { toast("No invite link to copy.", "error"); return; }
      navigator.clipboard.writeText(display.value).then(
        () => toast("Invite link copied!", "info"),
        () => { display.select(); document.execCommand("copy"); toast("Invite link copied!", "info"); }
      );
    },
  };

  /* ═══════════════════════════════════════════════════════════════════════
     HISTORY & ARCHIVE
     ═══════════════════════════════════════════════════════════════════════ */
  const History = {
    _loaded: false,
    _filters: {},

    init() {
      const section = document.getElementById("history");
      if (!section) return;
      const observer = new MutationObserver(() => {
        if (section.classList.contains("is-active") && !this._loaded) {
          this._loaded = true;
          this.loadTimeline();
        }
      });
      observer.observe(section, { attributes: true, attributeFilter: ["class"] });
    },

    async loadTimeline(filters) {
      const container = document.getElementById("history-timeline");
      const emptyEl   = document.getElementById("history-timeline-empty");
      if (!container) return;

      let url = `${API}/activity/`;
      const params = new URLSearchParams();
      if (filters?.type) params.set("type", filters.type);
      if (filters?.from) params.set("from", filters.from);
      if (filters?.to)   params.set("to", filters.to);
      if (params.toString()) url += `?${params.toString()}`;

      try {
        const data = await api(url, { method: "GET" });
        const items = data.events || data.activities || data.activity || [];
        if (!items.length) {
          container.classList.add("hidden");
          emptyEl?.classList.remove("hidden");
          return;
        }
        container.classList.remove("hidden");
        emptyEl?.classList.add("hidden");
        container.innerHTML = items.map(a => `
          <div class="flex items-start gap-3 py-3 border-b border-white/8 last:border-0">
            <div class="h-8 w-8 rounded-lg ${(ACTIVITY_STYLES[a.type] || ACTIVITY_STYLES.default).bg} grid place-items-center shrink-0 mt-0.5">
              <i data-lucide="${(ACTIVITY_STYLES[a.type] || ACTIVITY_STYLES.default).icon}" class="w-3.5 h-3.5 ${(ACTIVITY_STYLES[a.type] || ACTIVITY_STYLES.default).color}"></i>
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium">${esc(a.description || a.title || "Activity")}</p>
              <div class="flex items-center gap-2 text-xs text-white/40 mt-0.5">
                ${a.actor ? `<span>${esc(a.actor)}</span><span class="text-white/20">·</span>` : ""}
                <span>${esc(a.time_ago || renderTimestamp(a.created_at) || "")}</span>
                ${a.type ? `<span class="text-white/20">·</span><span class="text-[10px] px-1.5 py-0.5 rounded bg-white/5">${esc(a.type)}</span>` : ""}
              </div>
            </div>
          </div>
        `).join("");
        if (window.lucide) lucide.createIcons({ nodes: [container] });
      } catch (err) {
        container.innerHTML = `<p class="text-sm text-white/40 text-center py-6">Timeline unavailable.</p>`;
      }
    },

    applyFilters() {
      this._filters = {
        type: qs("#history-filter-type")?.value || "",
        from: qs("#history-filter-from")?.value || "",
        to:   qs("#history-filter-to")?.value || "",
      };
      this.loadTimeline(this._filters);
    },

    clearFilters() {
      const typeEl = qs("#history-filter-type");
      const fromEl = qs("#history-filter-from");
      const toEl   = qs("#history-filter-to");
      if (typeEl) typeEl.value = "";
      if (fromEl) fromEl.value = "";
      if (toEl)   toEl.value = "";
      this._filters = {};
      this.loadTimeline();
    },
  };


  /* ═══════════════════════════════════════════════════════════════════════
     MODULE 8 — Notifications (bell badge + dropdown panel)
     ═══════════════════════════════════════════════════════════════════════ */
  const Notifications = {
    _pollTimer: null,
    _open: false,

    init() {
      this.pollBadge();
      this._pollTimer = setInterval(() => this.pollBadge(), 30_000);
      // Close panel on outside click
      document.addEventListener("click", (e) => {
        const wrap = qs("#notifBellWrap");
        if (this._open && wrap && !wrap.contains(e.target)) {
          this.closePanel();
        }
      });
    },

    async pollBadge() {
      try {
        const res = await fetch("/notifications/api/unread-count/", { credentials: "same-origin" });
        const data = await res.json();
        const badge = qs("#notifBadge");
        if (!badge) return;
        const count = data.count || 0;
        badge.textContent = count > 99 ? "99+" : count;
        badge.classList.toggle("hidden", count === 0);
        badge.classList.toggle("flex", count > 0);
      } catch { /* silent */ }
    },

    togglePanel() {
      if (this._open) {
        this.closePanel();
      } else {
        this.openPanel();
      }
    },

    async openPanel() {
      const panel = qs("#notifPanel");
      const btn = qs("#notifBellBtn");
      if (!panel) return;
      this._open = true;
      panel.classList.remove("hidden");
      if (btn) btn.setAttribute("aria-expanded", "true");
      try {
        const data = await api("/notifications/api/nav-preview/");
        const list = qs("#notifList");
        if (!list) return;
        if (!data.items || data.items.length === 0) {
          list.innerHTML = `<div class="px-4 py-6 text-center text-xs text-white/30">No notifications yet</div>`;
          return;
        }
        list.innerHTML = data.items.map(n => `
          <a href="${esc(n.url || '#')}" class="flex items-start gap-3 px-4 py-3 hover:bg-white/5 transition ${n.is_read ? 'opacity-50' : ''}">
            <div class="shrink-0 mt-0.5 w-7 h-7 rounded-full ${n.is_read ? 'bg-white/5' : 'bg-blue-500/20'} grid place-items-center">
              <i data-lucide="${this._icon(n.type)}" class="w-3.5 h-3.5 ${n.is_read ? 'text-white/30' : 'text-blue-400'}"></i>
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-xs font-semibold leading-tight ${n.is_read ? 'text-white/50' : 'text-white/90'}">${esc(n.title || 'Notification')}</p>
              <p class="text-[11px] text-white/40 leading-snug mt-0.5 line-clamp-2">${esc(n.message || '')}</p>
              <span class="text-[10px] text-white/25 mt-1 inline-block">${this._timeAgo(n.created_at)}</span>
            </div>
            ${!n.is_read ? '<span class="shrink-0 mt-2 w-2 h-2 rounded-full bg-blue-400"></span>' : ''}
          </a>
        `).join("");
        if (window.lucide) lucide.createIcons({ nodes: [list] });
        // Update badge from this data too
        const badge = qs("#notifBadge");
        if (badge && data.unread_count !== undefined) {
          badge.textContent = data.unread_count > 99 ? "99+" : data.unread_count;
          badge.classList.toggle("hidden", data.unread_count === 0);
          badge.classList.toggle("flex", data.unread_count > 0);
        }
      } catch {
        const list = qs("#notifList");
        if (list) list.innerHTML = `<div class="px-4 py-6 text-center text-xs text-white/30">Could not load notifications</div>`;
      }
    },

    closePanel() {
      const panel = qs("#notifPanel");
      const btn = qs("#notifBellBtn");
      if (panel) panel.classList.add("hidden");
      if (btn) btn.setAttribute("aria-expanded", "false");
      this._open = false;
    },

    async markAllRead() {
      try {
        await fetch("/notifications/mark-all-read/", {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRFToken": CSRF },
        });
        this.pollBadge();
        if (this._open) this.openPanel(); // refresh panel
        toast("All notifications marked as read", "info");
      } catch { /* silent */ }
    },

    _icon(type) {
      const map = {
        invite_sent: "mail",
        invite_accepted: "user-check",
        roster_changed: "users",
        tournament_registered: "trophy",
        follow_request: "user-plus",
        match_result: "swords",
      };
      return map[type] || "bell";
    },

    _timeAgo(iso) {
      if (!iso) return "";
      const diff = Date.now() - new Date(iso).getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 1) return "just now";
      if (mins < 60) return `${mins}m ago`;
      const hrs = Math.floor(mins / 60);
      if (hrs < 24) return `${hrs}h ago`;
      const days = Math.floor(hrs / 24);
      return `${days}d ago`;
    },
  };


  /* ═══════════════════════════════════════════════════════════════════════
     SELF-EDIT — Player edits own roster info (display name, role, photo)
     ═══════════════════════════════════════════════════════════════════════ */
  const SelfEdit = {
    _photoFile: null,

    init() {
      const form = document.getElementById("self-edit-form");
      if (form) form.addEventListener("submit", (e) => { e.preventDefault(); this.save(); });
    },

    open(membershipId, username, playerRole, rosterSlot, displayName, rosterImageUrl) {
      qs("#self-edit-membership-id").value = membershipId;
      qs("#self-edit-display-name").value = displayName || "";
      qs("#self-edit-player-role").value = playerRole || "";
      this._photoFile = null;
      // Pre-load existing roster image or show camera icon
      const preview = qs("#self-edit-photo-preview");
      if (preview) {
        if (rosterImageUrl) {
          preview.innerHTML = `<img src="${rosterImageUrl}" alt="Current photo" class="w-full h-full object-cover">`;
        } else {
          preview.innerHTML = `<i data-lucide="camera" class="w-5 h-5 text-white/20"></i>`;
        }
      }
      qs("#self-edit-error")?.classList.add("hidden");
      Modal.open("modal-self-edit");
      if (window.lucide) lucide.createIcons();
    },

    previewPhoto(input) {
      const file = input.files?.[0];
      if (!file) return;
      this._photoFile = file;
      const reader = new FileReader();
      reader.onload = (e) => {
        const preview = qs("#self-edit-photo-preview");
        if (preview) preview.innerHTML = `<img src="${e.target.result}" alt="Preview" class="w-full h-full object-cover">`;
      };
      reader.readAsDataURL(file);
    },

    async save() {
      const memId = qs("#self-edit-membership-id").value;
      const displayName = qs("#self-edit-display-name")?.value || "";
      const playerRole = qs("#self-edit-player-role")?.value || "";
      const errEl = qs("#self-edit-error");
      const btn = qs("#self-edit-submit-btn");

      btn.disabled = true; btn.textContent = "Saving…";
      try {
        // Save roster info via role endpoint (self-edit allowed)
        await api(`${API}/members/${memId}/role/`, {
          method: "POST",
          body: JSON.stringify({ display_name: displayName, player_role: playerRole }),
        });

        // Upload photo if selected
        if (this._photoFile) {
          const fd = new FormData();
          fd.append("roster_image", this._photoFile);
          await api(`${API}/members/${memId}/roster-photo/`, {
            method: "POST",
            body: fd,
            headers: { "X-CSRFToken": CSRF },
          });
        }

        toast("Your roster info updated!");
        Modal.close("modal-self-edit");
        setTimeout(() => location.reload(), 600);
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Save Changes";
      }
    },
  };


  /* ═══════════════════════════════════════════════════════════════════════
     TREASURY — Payment Methods CRUD
     ═══════════════════════════════════════════════════════════════════════ */
  const Treasury = {
    _currentMethod: null,

    editPaymentMethod(method, label, currentValue) {
      this._currentMethod = method;
      document.getElementById('pm-modal-title').textContent = `Edit ${label}`;
      document.getElementById('pm-field-label').textContent = label;
      document.getElementById('pm-method-key').value = method;
      document.getElementById('pm-mobile-input').value = currentValue || '';
      const removeBtn = document.getElementById('pm-remove-btn');
      if (removeBtn) removeBtn.classList.toggle('hidden', !currentValue);
      Modal.open('modal-payment-method');
      setTimeout(() => document.getElementById('pm-mobile-input')?.focus(), 100);
    },

    async savePaymentMethod() {
      const method = document.getElementById('pm-method-key').value;
      const value = (document.getElementById('pm-mobile-input')?.value || '').trim();
      try {
        const res = await api('payment-methods/', {
          method: 'POST',
          body: JSON.stringify({ method, value, action: 'save' }),
        });
        const display = document.getElementById(`pm-${method}-display`);
        if (display) {
          display.textContent = res.active ? res.masked : 'Not configured';
          display.className = `text-xs ${res.active ? 'text-emerald-400' : 'text-white/30'}`;
        }
        Modal.close('modal-payment-method');
        toast(res.message || 'Payment method updated!', 'success');
      } catch (err) {
        toast(err.message || 'Failed to save', 'error');
      }
    },

    async removePaymentMethod() {
      const method = document.getElementById('pm-method-key').value;
      try {
        const res = await api('payment-methods/', {
          method: 'POST',
          body: JSON.stringify({ method, action: 'remove' }),
        });
        const display = document.getElementById(`pm-${method}-display`);
        if (display) {
          display.textContent = 'Not configured';
          display.className = 'text-xs text-white/30';
        }
        Modal.close('modal-payment-method');
        toast(res.message || 'Payment method removed.', 'success');
      } catch (err) {
        toast(err.message || 'Failed to remove', 'error');
      }
    },

    editBankAccount() {
      Modal.open('modal-bank-account');
      setTimeout(() => document.getElementById('pm-bank-name')?.focus(), 100);
    },

    async saveBankAccount() {
      try {
        const res = await api('payment-methods/', {
          method: 'POST',
          body: JSON.stringify({
            method: 'bank',
            action: 'save',
            account_name: document.getElementById('pm-bank-name')?.value || '',
            account_number: document.getElementById('pm-bank-number')?.value || '',
            bank_name: document.getElementById('pm-bank-institution')?.value || '',
            branch: document.getElementById('pm-bank-branch')?.value || '',
          }),
        });
        const display = document.getElementById('pm-bank-display');
        if (display) {
          display.textContent = res.active ? res.masked : 'Not configured';
          display.className = `text-xs ${res.active ? 'text-emerald-400' : 'text-white/30'}`;
        }
        Modal.close('modal-bank-account');
        toast(res.message || 'Bank account updated!', 'success');
      } catch (err) {
        toast(err.message || 'Failed to save', 'error');
      }
    },

    async removeBankAccount() {
      try {
        const res = await api('payment-methods/', {
          method: 'POST',
          body: JSON.stringify({ method: 'bank', action: 'remove' }),
        });
        const display = document.getElementById('pm-bank-display');
        if (display) {
          display.textContent = 'Not configured';
          display.className = 'text-xs text-white/30';
        }
        // Clear form inputs too
        ['pm-bank-name', 'pm-bank-number', 'pm-bank-institution', 'pm-bank-branch'].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.value = '';
        });
        Modal.close('modal-bank-account');
        toast(res.message || 'Bank account removed.', 'success');
      } catch (err) {
        toast(err.message || 'Failed to remove', 'error');
      }
    },
  };

  /* ═══════════════════════════════════════════════════════════════════════
     PlayerInfo — Comprehensive player profile viewer
     ═══════════════════════════════════════════════════════════════════════ */
  let _playerInfoUserId = null;

  const SOCIAL_ICONS = {
    discord: { icon: '💬', color: 'text-indigo-400', bg: 'bg-indigo-500/10 border-indigo-500/20' },
    twitter: { icon: '𝕏',  color: 'text-sky-400',    bg: 'bg-sky-500/10 border-sky-500/20' },
    twitch:  { icon: '📺', color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/20' },
    youtube: { icon: '▶',  color: 'text-red-400',    bg: 'bg-red-500/10 border-red-500/20' },
    facebook:{ icon: '📘', color: 'text-blue-400',   bg: 'bg-blue-500/10 border-blue-500/20' },
    instagram:{icon: '📷', color: 'text-pink-400',   bg: 'bg-pink-500/10 border-pink-500/20' },
    tiktok:  { icon: '🎵', color: 'text-white/80',   bg: 'bg-white/5 border-white/15' },
    steam:   { icon: '🎮', color: 'text-blue-300',   bg: 'bg-blue-500/10 border-blue-500/20' },
    riot:    { icon: '⚔',  color: 'text-red-300',    bg: 'bg-red-500/10 border-red-500/20' },
    github:  { icon: '🐙', color: 'text-white/80',   bg: 'bg-white/5 border-white/15' },
    kick:    { icon: '🟢', color: 'text-green-400',  bg: 'bg-green-500/10 border-green-500/20' },
    facebook_gaming:{ icon: '🎮', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
  };

  function _setText(id, val, fallback = '—') {
    const el = document.getElementById(id);
    if (el) el.textContent = val || fallback;
  }

  function _showSection(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('hidden');
  }

  function _hideSection(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  }

  const PlayerInfo = {
    async open(userId, username) {
      _playerInfoUserId = userId;
      const title = document.getElementById('player-info-username');
      if (title) title.textContent = `${username}`;

      // Reset state
      const loading = document.getElementById('player-info-loading');
      const data    = document.getElementById('player-info-data');
      const error   = document.getElementById('player-info-error');
      const warning = document.getElementById('pi-missing-warning');
      if (loading) loading.classList.remove('hidden');
      if (data)    data.classList.add('hidden');
      if (error)   { error.classList.add('hidden'); error.textContent = ''; }
      if (warning) warning.classList.add('hidden');
      _hideSection('pi-personal-section');
      _hideSection('pi-gaming-section');
      _hideSection('pi-socials-section');
      _hideSection('pi-membership-section');

      Modal.open('modal-player-info');

      try {
        const res = await api(`player-info/${userId}/`);
        if (loading) loading.classList.add('hidden');
        if (data)    data.classList.remove('hidden');

        const prof = res.profile || {};
        const gp   = res.game_passport;
        const soc  = res.socials || [];
        const mem  = res.membership || {};

        // ── Header Card ──
        _setText('pi-display-name', prof.display_name || username);
        const avatarImg = document.getElementById('pi-avatar');
        const avatarFallback = document.getElementById('pi-avatar-fallback');
        if (prof.avatar_url) {
          if (avatarImg)      { avatarImg.src = prof.avatar_url; avatarImg.classList.remove('hidden'); }
          if (avatarFallback) avatarFallback.classList.add('hidden');
        } else {
          if (avatarImg)      avatarImg.classList.add('hidden');
          if (avatarFallback) avatarFallback.classList.remove('hidden');
        }

        // Role badge
        const roleBadge = document.getElementById('pi-role-badge');
        if (roleBadge && mem.role) {
          roleBadge.textContent = mem.role.charAt(0).toUpperCase() + mem.role.slice(1).toLowerCase();
          roleBadge.classList.remove('hidden');
        }

        // Level badge
        if (prof.level && prof.level > 1) {
          _setText('pi-level-badge', `Lv. ${prof.level}`);
          _showSection('pi-level-badge');
        }

        // Joined date
        if (mem.joined_at) {
          const d = new Date(mem.joined_at);
          _setText('pi-joined-date', `Joined ${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`);
          _showSection('pi-joined-date');
        }

        // Captain badge
        if (mem.is_captain) _showSection('pi-captain-badge');
        else _hideSection('pi-captain-badge');

        // ── Game Passport ──
        if (!gp || !gp.ign) {
          _setText('pi-ign', '—'); _setText('pi-discriminator', '—');
          _setText('pi-platform', '—'); _setText('pi-main-role', '—');
          _setText('pi-rank', '—'); _setText('pi-rank-points', '—');
          _setText('pi-peak-rank', '—'); _setText('pi-region', '—');
          _setText('pi-lft', '—');
          _setText('pi-matches', '0'); _setText('pi-winrate', '0%');
          _setText('pi-kd', '—'); _setText('pi-hours', '—');
          _hideSection('pi-verification-banner');
          _hideSection('pi-ext-identity-row');
          _hideSection('pi-rank-tier-row');
          const rankImg = document.getElementById('pi-rank-image');
          if (rankImg) rankImg.classList.add('hidden');
          if (warning) warning.classList.remove('hidden');
        } else {
          _setText('pi-ign', gp.ign);
          _setText('pi-discriminator', gp.discriminator);
          _setText('pi-platform', gp.platform);
          _setText('pi-main-role', gp.main_role);
          _setText('pi-rank', gp.rank_name);
          _setText('pi-rank-points', gp.rank_points != null ? String(gp.rank_points) : '—');
          _setText('pi-peak-rank', gp.peak_rank);
          _setText('pi-region', gp.region);
          _setText('pi-lft', gp.is_lft ? 'Looking for Team' : 'Not Looking');
          _setText('pi-matches', String(gp.matches_played || 0));
          _setText('pi-winrate', `${gp.win_rate || 0}%`);
          _setText('pi-kd', gp.kd_ratio != null ? gp.kd_ratio.toFixed(2) : '—');
          _setText('pi-hours', gp.hours_played != null ? String(gp.hours_played) : '—');

          // Rank image
          const rankImg = document.getElementById('pi-rank-image');
          if (rankImg && gp.rank_image) {
            rankImg.src = gp.rank_image;
            rankImg.alt = gp.rank_name || 'Rank';
            rankImg.classList.remove('hidden');
          } else if (rankImg) {
            rankImg.classList.add('hidden');
          }

          // Rank tier
          if (gp.rank_tier) {
            _setText('pi-rank-tier', `Tier ${gp.rank_tier}`);
            _showSection('pi-rank-tier-row');
          } else {
            _hideSection('pi-rank-tier-row');
          }

          // Extended identity (in_game_name, game_display_name, identity_key)
          if (gp.in_game_name || gp.game_display_name || gp.identity_key) {
            _setText('pi-in-game-name', gp.in_game_name || '—');
            _setText('pi-game-display-name', gp.game_display_name || '—');
            _setText('pi-identity-key', gp.identity_key || '—');
            _showSection('pi-ext-identity-row');
          } else {
            _hideSection('pi-ext-identity-row');
          }

          // Verification banner
          const verBanner = document.getElementById('pi-verification-banner');
          if (verBanner && (gp.verification_status || gp.status || gp.visibility)) {
            verBanner.classList.remove('hidden');
            const vIcon = document.getElementById('pi-verified-icon');
            const uIcon = document.getElementById('pi-unverified-icon');
            const vText = document.getElementById('pi-verification-text');
            if (gp.is_verified) {
              if (vIcon) vIcon.classList.remove('hidden');
              if (uIcon) uIcon.classList.add('hidden');
              if (vText) { vText.textContent = 'Verified'; vText.className = 'text-[10px] font-medium text-green-400'; }
            } else {
              if (vIcon) vIcon.classList.add('hidden');
              if (uIcon) uIcon.classList.remove('hidden');
              if (vText) {
                const vs = gp.verification_status || 'Unverified';
                vText.textContent = vs.charAt(0).toUpperCase() + vs.slice(1).toLowerCase();
                vText.className = 'text-[10px] font-medium text-white/60';
              }
            }
            _setText('pi-passport-status', gp.status ? gp.status.charAt(0).toUpperCase() + gp.status.slice(1).toLowerCase() : '—');
            _setText('pi-visibility-badge', gp.visibility ? gp.visibility.toUpperCase() : '—');
          } else if (verBanner) {
            verBanner.classList.add('hidden');
          }

          if (!gp.ign || !gp.main_role) {
            if (warning) warning.classList.remove('hidden');
          }
        }

        // ── Personal Info ──
        const hasPersonal = prof.real_full_name || prof.date_of_birth || prof.nationality || prof.country || prof.city;
        if (hasPersonal) {
          _showSection('pi-personal-section');
          _setText('pi-real-name', prof.real_full_name);
          _setText('pi-dob', prof.date_of_birth);
          _setText('pi-nationality', prof.nationality);
          _setText('pi-country', prof.country);
          _setText('pi-city', prof.city);
          _setText('pi-gender', prof.gender ? prof.gender.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : '');
          _setText('pi-pronouns', prof.pronouns ? prof.pronouns.replace(/_/g, '/') : '');
          _setText('pi-timezone', prof.timezone);
          _setText('pi-language', prof.language || '—');
        }

        // ── Gaming Profile ──
        const hasGaming = prof.competitive_goal || prof.play_style || prof.device_platform || prof.bio;
        if (hasGaming) {
          _showSection('pi-gaming-section');
          _setText('pi-comp-goal', prof.competitive_goal);
          _setText('pi-play-style', prof.play_style ? prof.play_style.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : '');
          _setText('pi-device', prof.device_platform ? prof.device_platform.replace(/_/g, ' ') : '');
          _setText('pi-active-hours', prof.active_hours);
          const roles = [prof.main_role, prof.secondary_role].filter(Boolean).join(' / ');
          _setText('pi-roles', roles);
          _setText('pi-bio', prof.bio || prof.profile_story);
          _setText('pi-lft-status', prof.lft_status || '—');
          _setText('pi-lan', prof.lan_availability ? 'Yes' : 'No');
        }
        // Reputation & XP bar (show if either exists)
        const repXpBar = document.getElementById('pi-rep-xp-bar');
        if (repXpBar && (prof.reputation_score || prof.xp)) {
          repXpBar.classList.remove('hidden');
          _setText('pi-reputation', prof.reputation_score != null ? String(prof.reputation_score) : '—');
          _setText('pi-xp', prof.xp != null ? String(prof.xp) : '—');
        } else if (repXpBar) {
          repXpBar.classList.add('hidden');
        }

        // ── Social Links ──
        if (soc.length > 0) {
          _showSection('pi-socials-section');
          const container = document.getElementById('pi-socials-list');
          if (container) {
            container.innerHTML = soc.map(s => {
              const cfg = SOCIAL_ICONS[s.platform] || { icon: '🔗', color: 'text-white/60', bg: 'bg-white/5 border-white/15' };
              const label = s.handle || s.platform.charAt(0).toUpperCase() + s.platform.slice(1);
              return `<a href="${s.url}" target="_blank" rel="noopener"
                class="flex items-center gap-2 px-3 py-2 rounded-lg border ${cfg.bg} hover:brightness-125 transition text-xs">
                <span class="text-sm">${cfg.icon}</span>
                <span class="${cfg.color} font-medium truncate">${label}</span>
                ${s.is_verified ? '<span class="text-[9px] text-green-400 ml-auto">✓</span>' : ''}
              </a>`;
            }).join('');
          }
        }

        // ── Membership Info ──
        if (mem.role) {
          _showSection('pi-membership-section');
          _setText('pi-team-role', mem.role ? mem.role.charAt(0).toUpperCase() + mem.role.slice(1).toLowerCase() : '');
          _setText('pi-roster-slot', mem.roster_slot ? mem.roster_slot.charAt(0).toUpperCase() + mem.roster_slot.slice(1).toLowerCase() : '');
          _setText('pi-player-role', mem.player_role);
          _setText('pi-member-dn', mem.display_name || prof.display_name || username);
        }

        // Re-render lucide icons for new DOM
        if (window.lucide) lucide.createIcons();

      } catch (err) {
        if (loading) loading.classList.add('hidden');
        if (error) { error.classList.remove('hidden'); error.textContent = err.message || 'Failed to load player info'; }
      }
    },
    async nudge() {
      if (!_playerInfoUserId) return;
      const btn = document.getElementById('pi-nudge-btn');
      if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }
      try {
        await api(`player-info/${_playerInfoUserId}/nudge/`, { method: 'POST' });
        toast('Reminder sent to player.', 'success');
        if (btn) { btn.textContent = '✓ Sent'; }
      } catch (err) {
        toast(err.message || 'Failed to send reminder', 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="bell" class="w-3 h-3 inline -mt-0.5"></i> Send Reminder'; }
      }
    },
  };


  /* ═══════════════════════════════════════════════════════════════════════
     MEMBER INFO POPOVER  (lightweight info overlay for roster cards)
     ═══════════════════════════════════════════════════════════════════════ */
  const MemberInfo = {
    _overlay: null,

    show(memberId, displayName, username, roleDisplay, playerRole, email, joinedAt) {
      this.close();                       // close any existing

      // Read game passport data from card data attributes
      const card = document.querySelector(`[data-membership-id="${memberId}"]`);
      const gpIgn        = card?.dataset.gpIgn || '';
      const gpRank       = card?.dataset.gpRank || '';
      const gpRankImg    = card?.dataset.gpRankImg || '';
      const gpRole       = card?.dataset.gpRole || '';
      const gpRegion     = card?.dataset.gpRegion || '';
      const gpMatches    = card?.dataset.gpMatches || '0';
      const gpWinrate    = card?.dataset.gpWinrate || '0';
      const gpKd         = card?.dataset.gpKd || '';
      const gpPlatform   = card?.dataset.gpPlatform || '';
      const gpRankPoints = card?.dataset.gpRankPoints || '';
      const gpPeakRank   = card?.dataset.gpPeakRank || '';
      const gpHours      = card?.dataset.gpHours || '';
      const gpLft        = card?.dataset.gpLft || 'false';
      const gpVerified   = card?.dataset.gpVerified || '';
      const profileUrl   = card?.dataset.profileUrl || `/@${username}/`;

      // ── Basic Info rows ──
      const rows = [];
      rows.push(this._row('User',        `<span class="font-semibold text-white">${this._esc(displayName)}</span> <span class="text-white/40">@${this._esc(username)}</span>`));
      rows.push(this._row('Team Role',   `<span class="px-1.5 py-0.5 rounded bg-cyan-500/15 text-cyan-300 text-[10px] font-bold uppercase tracking-wider">${this._esc(roleDisplay)}</span>`));
      if (playerRole) rows.push(this._row('Player Role', this._esc(playerRole)));
      if (email)      rows.push(this._row('Email',       `<a href="mailto:${this._esc(email)}" class="text-cyan-400 hover:underline">${this._esc(email)}</a>`));
      if (joinedAt)   rows.push(this._row('Joined',      this._fmtDate(joinedAt)));

      // ── Game Passport rows (show ALL available fields) ──
      const gpRows = [];
      if (gpIgn) {
        gpRows.push(this._row('In-Game Name', `<span class="font-semibold text-white">${this._esc(gpIgn)}</span>`));
      }
      if (gpPlatform) {
        gpRows.push(this._row('Platform', `<span class="px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-300 text-[10px] font-bold uppercase">${this._esc(gpPlatform)}</span>`));
      }
      if (gpRegion) {
        gpRows.push(this._row('Region', `<span class="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 text-[10px] font-bold uppercase">${this._esc(gpRegion)}</span>`));
      }
      if (gpRank) {
        const rankBadge = gpRankImg
          ? `<img src="${this._esc(gpRankImg)}" class="w-5 h-5 inline -mt-0.5 mr-1.5" alt="">`
          : '';
        const rpText = gpRankPoints ? ` <span class="text-white/40 text-[10px]">(${this._esc(gpRankPoints)} pts)</span>` : '';
        gpRows.push(this._row('Current Rank', `${rankBadge}<span class="text-amber-300 font-semibold">${this._esc(gpRank)}</span>${rpText}`));
      }
      if (gpPeakRank) {
        gpRows.push(this._row('Peak Rank', `<span class="text-yellow-200">${this._esc(gpPeakRank)}</span>`));
      }
      if (gpRole) {
        gpRows.push(this._row('Main Role', `<span class="text-purple-300">${this._esc(gpRole)}</span>`));
      }

      // Stats section
      const statParts = [];
      if (parseInt(gpMatches) > 0) statParts.push(`<span class="text-white">${gpMatches}</span> matches`);
      if (parseInt(gpWinrate) > 0) statParts.push(`<span class="text-emerald-400">${gpWinrate}%</span> WR`);
      if (gpKd) statParts.push(`<span class="text-cyan-400">${gpKd}</span> K/D`);
      if (statParts.length > 0) {
        gpRows.push(this._row('Stats', statParts.join(' <span class="text-white/20 mx-0.5">&middot;</span> ')));
      }
      if (gpHours) {
        gpRows.push(this._row('Hours Played', `<span class="text-white/70">${this._esc(gpHours)}h</span>`));
      }

      // Status indicators
      if (gpLft === 'true') {
        gpRows.push(this._row('LFT Status', `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-green-500/15 text-green-400 text-[10px] font-bold"><span class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span> Looking for Team</span>`));
      }
      if (gpVerified === 'VERIFIED') {
        gpRows.push(this._row('Verification', `<span class="inline-flex items-center gap-1 text-emerald-400 text-[11px] font-semibold"><i data-lucide="badge-check" class="w-3.5 h-3.5"></i> Verified</span>`));
      } else if (gpVerified === 'PENDING') {
        gpRows.push(this._row('Verification', `<span class="inline-flex items-center gap-1 text-amber-400/80 text-[11px]"><i data-lucide="clock" class="w-3.5 h-3.5"></i> Pending</span>`));
      } else if (gpVerified === 'FLAGGED') {
        gpRows.push(this._row('Verification', `<span class="inline-flex items-center gap-1 text-red-400/80 text-[11px]"><i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i> Flagged</span>`));
      }

      const hasPassport = gpRows.length > 0;

      const html = `
        <div id="member-info-overlay" class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm" onclick="ManageHQ.closeMemberInfo(event)">
          <div class="relative w-full max-w-md mx-4 rounded-2xl border border-white/10 bg-[#0d1117] shadow-2xl overflow-hidden" onclick="event.stopPropagation()">
            <div class="flex items-center justify-between px-5 pt-4 pb-2">
              <h3 class="text-sm font-bold text-white flex items-center gap-2">
                <i data-lucide="info" class="w-4 h-4 text-cyan-400"></i> Player Info
              </h3>
              <button onclick="ManageHQ.closeMemberInfo()" class="h-7 w-7 rounded-lg bg-white/5 hover:bg-white/10 grid place-items-center transition">
                <i data-lucide="x" class="w-3.5 h-3.5 text-white/50"></i>
              </button>
            </div>
            <div class="px-5 pb-2 space-y-2">
              ${rows.join('')}
            </div>

            ${hasPassport ? `
            <div class="mx-5 border-t border-white/8"></div>
            <div class="px-5 pt-3 pb-2">
              <div class="text-[10px] font-bold uppercase tracking-wider text-white/30 mb-2 flex items-center gap-1.5">
                <i data-lucide="gamepad-2" class="w-3 h-3"></i> Game Passport
              </div>
              <div class="space-y-1.5">
                ${gpRows.join('')}
              </div>
            </div>` : `
            <div class="mx-5 border-t border-white/8"></div>
            <div class="px-5 pt-3 pb-2">
              <div class="text-xs text-white/30 flex items-center gap-1.5">
                <i data-lucide="alert-circle" class="w-3 h-3"></i> No game passport linked
              </div>
            </div>`}

            <div class="mx-5 border-t border-white/8"></div>
            <div class="px-5 pt-3 pb-4">
              <a href="${this._esc(profileUrl)}" target="_blank"
                 class="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl border border-cyan-500/20 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 text-xs font-semibold transition">
                <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
                View Full Profile
              </a>
            </div>
          </div>
        </div>`;

      document.body.insertAdjacentHTML('beforeend', html);
      this._overlay = document.getElementById('member-info-overlay');

      // re-init lucide icons inside the overlay
      if (window.lucide) lucide.createIcons({ attrs: { class: '' }, nameAttr: 'data-lucide' });
    },

    close(e) {
      if (e && e.target && e.target.id !== 'member-info-overlay') return;
      const el = document.getElementById('member-info-overlay');
      if (el) el.remove();
      this._overlay = null;
    },

    _row(label, value) {
      return `<div class="flex items-start gap-3 py-1.5 border-b border-white/5 last:border-0">
        <span class="text-[11px] text-white/40 uppercase tracking-wider w-24 shrink-0 pt-0.5">${label}</span>
        <span class="text-xs text-white/80 flex-1 min-w-0">${value}</span>
      </div>`;
    },

    _esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; },

    _fmtDate(iso) {
      if (!iso) return '—';
      try { return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }); }
      catch { return iso; }
    },
  };


  /* ═══════════════════════════════════════════════════════════════════════
     PUBLIC API (used by onclick handlers in templates)
     ═══════════════════════════════════════════════════════════════════════ */
  window.ManageHQ = {
    // Core
    api,
    toast,
    // Roster
    openInviteModal:   ()                        => Roster.openInviteModal(),
    cancelInvite:      (id, btn)                 => Roster.cancelInvite(id, btn),
    openRoleModal:     (id, role, name, cap, pr, slot, dn, img) => Roster.openRoleModal(id, role, name, cap, pr, slot, dn, img),
    openRemoveModal:   (id, name)                => Roster.openRemoveModal(id, name),
    confirmRemove:     ()                        => Roster.confirmRemove(),
    handleJoinRequest: (id, act, btn)            => Roster.handleJoinRequest(id, act, btn),
    swapSlot:          (id, slot)                => Roster.swapSlot(id, slot),
    toggleRosterLock:  (locked)                  => Roster.toggleRosterLock(locked),
    // Player Info
    openPlayerInfoModal: (userId, username)       => PlayerInfo.open(userId, username),
    nudgePlayerPassport: ()                       => PlayerInfo.nudge(),
    // Member Info (roster card info button)
    showMemberInfo:    (id, dn, un, role, pr, em, ja) => MemberInfo.show(id, dn, un, role, pr, em, ja),
    closeMemberInfo:   (e)                        => MemberInfo.close(e),
    // Command Center
    loadMoreActivity:  ()                        => Command.loadMore(),
    // Self-Edit (player edits own card)
    openSelfEditModal: (id, name, pr, slot, dn, img) => SelfEdit.open(id, name, pr, slot, dn, img),
    previewSelfPhoto:  (input)                   => SelfEdit.previewPhoto(input),
    // Profile
    uploadMedia:       (inp)                     => Profile.uploadMedia(inp),
    // Settings
    toggleSetting:     (field, val)              => Settings.toggle(field, val),
    updateField:       (field, val)              => Settings.toggle(field, val),
    saveIdentity:      ()                        => Settings.saveIdentity(),
    toggleOwnerPrivacy:(hide)                    => Settings.toggleOwnerPrivacy(hide),
    leaveTeam:         ()                        => Settings.leaveTeam(),
    disbandTeam:       ()                        => Settings.disbandTeam(),
    transferOwnership: ()                        => Settings.transferOwnership(),
    generateInviteLink:(regen)                   => Settings.generateInviteLink(regen),
    copyInviteLink:    ()                        => Settings.copyInviteLink(),
    openTransferModal: ()                        => Modal.open("modal-transfer"),
    openDisbandModal:  ()                        => Modal.open("modal-disband"),
    // Modal
    closeModal:        (id)                      => Modal.close(id),
    // History (used by filter bar in template)
    History: {
      applyFilters: () => History.applyFilters(),
      clearFilters: () => History.clearFilters(),
      addMilestone: () => History.addMilestone(),
    },
    // Training Lab
    Training: {
      switchSubTab:      (tab) => Training.switchSubTab(tab),
      openScheduleModal: () => Training.openScheduleModal(),
      openScrimModal:    () => Training.openScrimModal(),
      openVodModal:      () => Training.openVodModal(),
      openBountyModal:   () => Training.openBountyModal(),
      filterScrims:      () => Training.filterScrims(),
      filterVods:        (tab) => Training.filterVods(tab),
      acceptChallenge:   (id) => Training.acceptChallenge(id),
      declineChallenge:  (id) => Training.declineChallenge(id),
      cancelChallenge:   (id) => Training.cancelChallenge(id),
      openResultModal:   (id) => Training.openResultModal(id),
      submitResult:      (id, result) => Training.submitResult(id, result),
    },
    // Community & Media
    Community: {
      openPostModal:      () => Community.openPostModal(),
      openMediaUpload:    () => Community.openMediaUpload(),
      openHighlightModal: () => Community.openHighlightModal(),
      openCommsModal:     () => Community.openCommsModal(),
      saveComms:          () => Community.saveComms(),
      testDiscordWebhook: () => Community.testDiscordWebhook(),
      filterGallery:      (tab) => Community.filterGallery(tab),
    },
    // Discord Integration
    Discord: {
      saveConfig:    () => Discord.saveConfig(),
      sendChat:      () => Discord.sendChat(),
    },
    // Notifications (used by bell in topbar)
    toggleNotifPanel:  ()                        => Notifications.togglePanel(),
    markAllNotifRead:  ()                        => Notifications.markAllRead(),
    // Treasury — Payment Methods
    editPaymentMethod: (m, l, v)                 => Treasury.editPaymentMethod(m, l, v),
    savePaymentMethod: ()                        => Treasury.savePaymentMethod(),
    removePaymentMethod: ()                      => Treasury.removePaymentMethod(),
    editBankAccount:   ()                        => Treasury.editBankAccount(),
    saveBankAccount:   ()                        => Treasury.saveBankAccount(),
    removeBankAccount: ()                        => Treasury.removeBankAccount(),
  };

  /* ── Init on DOM ready ── */
  document.addEventListener("DOMContentLoaded", () => {
    Command.init();
    Roster.init();
    Competition.init();
    Training.init();
    Community.init();
    Discord.init();
    Profile.init();
    Settings.init();
    History.init();
    Notifications.init();
    SelfEdit.init();
  });
})();
