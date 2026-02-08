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
  const API  = `/teams/api/${SLUG}/manage`;

  /* ── Fetch wrapper ── */
  async function api(path, opts = {}) {
    const url = path.startsWith("http") || path.startsWith("/") ? path : `${API}/${path}`;
    const headers = { "X-CSRFToken": CSRF, ...(opts.headers || {}) };
    if (!(opts.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    const res = await fetch(url, { credentials: "same-origin", ...opts, headers });
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

  function activityIcon(type) {
    const map = {
      roster: "users", tournament: "trophy", settings: "settings",
      profile: "palette", invite: "mail", join: "user-plus",
      remove: "user-x", role: "shield", default: "activity",
    };
    return map[type] || map.default;
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
  const Command = {
    init() {
      this.loadActivity();
    },

    async loadActivity() {
      const container = document.getElementById("activity-feed");
      if (!container) return;
      try {
        const data = await api(`${API}/activity/`, { method: "GET" });
        const items = data.activities || data.activity || [];
        if (!items.length) {
          container.innerHTML = `<p class="text-sm text-white/50 text-center py-6">No recent activity yet.</p>`;
          return;
        }
        container.innerHTML = items.map(a => `
          <div class="flex items-start gap-3 py-2.5 border-b border-white/8 last:border-0">
            <div class="h-8 w-8 rounded-lg bg-white/10 grid place-items-center shrink-0">
              <i data-lucide="${activityIcon(a.type)}" class="w-3.5 h-3.5"></i>
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium truncate">${esc(a.description || a.title || "Activity")}</p>
              <p class="text-xs text-white/40 mt-0.5">${esc(a.time_ago || a.created_at || "")}</p>
            </div>
          </div>
        `).join("");
        if (window.lucide) lucide.createIcons({ nodes: [container] });
      } catch (err) {
        container.innerHTML = `<p class="text-sm text-white/40 text-center py-6">Activity feed unavailable.</p>`;
      }
    },
  };

  /* ═══════════════════════════════════════════════════════════════════════
     ROSTER OPS
     ═══════════════════════════════════════════════════════════════════════ */
  const Roster = {
    init() {
      const invForm = document.getElementById("invite-form");
      if (invForm) invForm.addEventListener("submit", (e) => { e.preventDefault(); this.sendInvite(); });

      const roleForm = document.getElementById("role-edit-form");
      if (roleForm) roleForm.addEventListener("submit", (e) => { e.preventDefault(); this.saveRole(); });
    },

    openInviteModal() {
      const form = document.getElementById("invite-form");
      if (form) form.reset();
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

    openRoleModal(membershipId, currentRole, username, isCaptain, playerRole) {
      qs("#role-membership-id").value  = membershipId;
      qs("#role-username-display").textContent = username;
      qs("#role-select").value        = currentRole;
      const captainCb = qs("#role-captain-cb");
      if (captainCb) captainCb.checked = isCaptain;
      const prField = qs("#role-player-role");
      if (prField) prField.value = playerRole || "";
      qs("#role-error")?.classList.add("hidden");
      Modal.open("modal-role-edit");
    },

    async saveRole() {
      const memId     = qs("#role-membership-id").value;
      const role      = qs("#role-select").value;
      const captain   = qs("#role-captain-cb")?.checked || false;
      const playerRole = qs("#role-player-role")?.value || "";
      const errEl     = qs("#role-error");
      const btn       = qs("#role-submit-btn");

      btn.disabled = true; btn.textContent = "Saving…";
      try {
        await api(`${API}/members/${memId}/role/`, {
          method: "POST",
          body: JSON.stringify({ role, assign_captain: captain ? "true" : "false", player_role: playerRole }),
        });
        toast("Role updated.");
        Modal.close("modal-role-edit");
        setTimeout(() => location.reload(), 600);
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Save Changes";
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
     TRAINING LAB
     ═══════════════════════════════════════════════════════════════════════ */
  const Training = {
    _loaded: false,

    init() {
      const section = document.getElementById("training");
      if (!section) return;
      const observer = new MutationObserver(() => {
        if (section.classList.contains("is-active") && !this._loaded) {
          this._loaded = true;
          this.loadData();
        }
      });
      observer.observe(section, { attributes: true, attributeFilter: ["class"] });

      // Form handlers
      const scheduleForm = document.getElementById("schedule-practice-form");
      if (scheduleForm) scheduleForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitSchedule(); });

      const scrimForm = document.getElementById("post-scrim-form");
      if (scrimForm) scrimForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitScrim(); });

      const vodForm = document.getElementById("add-vod-form");
      if (vodForm) vodForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitVod(); });

      const bountyForm = document.getElementById("new-bounty-form");
      if (bountyForm) bountyForm.addEventListener("submit", (e) => { e.preventDefault(); this.submitBounty(); });
    },

    async loadData() {
      // Load schedule, scrims, vods, bounties from API when available
      try {
        const data = await api(`${API}/training/`, { method: "GET" });
        if (data.sessions) this.renderSessions(data.sessions);
        if (data.scrims) this.renderScrims(data.scrims);
        if (data.vods) this.renderVods(data.vods);
        if (data.bounties) this.renderBounties(data.bounties);
        if (data.stats) this.updateScrimStats(data.stats);
      } catch {
        // API not yet available — leave placeholders
      }
    },

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

    openBountyModal() {
      const form = document.getElementById("new-bounty-form");
      if (form) form.reset();
      qs("#bounty-error")?.classList.add("hidden");
      Modal.open("modal-new-bounty");
    },

    async submitBounty() {
      const btn = qs("#bounty-submit");
      const errEl = qs("#bounty-error");
      btn.disabled = true; btn.textContent = "Creating…";
      try {
        const payload = {
          title: qs("#bounty-title")?.value.trim(),
          description: qs("#bounty-desc")?.value.trim(),
          reward: parseInt(qs("#bounty-reward")?.value) || 100,
          deadline: qs("#bounty-deadline")?.value,
        };
        const data = await api("training/bounties/", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        toast(data.message || "Bounty created!");
        Modal.close("modal-new-bounty");
        this.loadData();
      } catch (err) {
        errEl.textContent = err.message; errEl.classList.remove("hidden");
      } finally {
        btn.disabled = false; btn.textContent = "Create Bounty";
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
        ["name", "tag", "tagline", "description", "region"].forEach(f => {
          const el = qs(`#profile-${f}`);
          if (el) payload[f] = el.value;
        });
        await api("profile/", { method: "POST", body: JSON.stringify(payload) });
        toast("Profile updated.");
      } catch (err) { toast(err.message, "error"); }
      finally { btn.disabled = false; btn.textContent = "Save Changes"; }
    },

    async saveSocials() {
      const btn = qs("#profile-socials-submit");
      btn.disabled = true; btn.textContent = "Saving…";
      try {
        const payload = {};
        ["twitter", "instagram", "youtube", "twitch"].forEach(f => {
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
        const items = data.activities || data.activity || [];
        if (!items.length) {
          container.classList.add("hidden");
          emptyEl?.classList.remove("hidden");
          return;
        }
        container.classList.remove("hidden");
        emptyEl?.classList.add("hidden");
        container.innerHTML = items.map(a => `
          <div class="flex items-start gap-3 py-3 border-b border-white/8 last:border-0">
            <div class="h-8 w-8 rounded-lg bg-white/10 grid place-items-center shrink-0 mt-0.5">
              <i data-lucide="${activityIcon(a.type)}" class="w-3.5 h-3.5"></i>
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
     PUBLIC API (used by onclick handlers in templates)
     ═══════════════════════════════════════════════════════════════════════ */
  window.ManageHQ = {
    // Roster
    openInviteModal:   ()                        => Roster.openInviteModal(),
    cancelInvite:      (id, btn)                 => Roster.cancelInvite(id, btn),
    openRoleModal:     (id, role, name, cap, pr) => Roster.openRoleModal(id, role, name, cap, pr),
    openRemoveModal:   (id, name)                => Roster.openRemoveModal(id, name),
    confirmRemove:     ()                        => Roster.confirmRemove(),
    handleJoinRequest: (id, act, btn)            => Roster.handleJoinRequest(id, act, btn),
    // Profile
    uploadMedia:       (inp)                     => Profile.uploadMedia(inp),
    // Settings
    toggleSetting:     (field, val)              => Settings.toggle(field, val),
    // Modal
    closeModal:        (id)                      => Modal.close(id),
    // History (used by filter bar in template)
    History: {
      applyFilters: () => History.applyFilters(),
      clearFilters: () => History.clearFilters(),
    },
    // Training Lab
    Training: {
      openScheduleModal: () => Training.openScheduleModal(),
      openScrimModal:    () => Training.openScrimModal(),
      openVodModal:      () => Training.openVodModal(),
      openBountyModal:   () => Training.openBountyModal(),
      filterScrims:      () => Training.filterScrims(),
      filterVods:        (tab) => Training.filterVods(tab),
    },
    // Community & Media
    Community: {
      openPostModal:      () => Community.openPostModal(),
      openMediaUpload:    () => Community.openMediaUpload(),
      openHighlightModal: () => Community.openHighlightModal(),
      filterGallery:      (tab) => Community.filterGallery(tab),
    },
    // Notifications (used by bell in topbar)
    toggleNotifPanel:  ()                        => Notifications.togglePanel(),
    markAllNotifRead:  ()                        => Notifications.markAllRead(),
  };

  /* ── Init on DOM ready ── */
  document.addEventListener("DOMContentLoaded", () => {
    Command.init();
    Roster.init();
    Competition.init();
    Training.init();
    Community.init();
    Profile.init();
    Settings.init();
    History.init();
    Notifications.init();
  });
})();
