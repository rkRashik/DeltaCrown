/* ============================================================
   DeltaCrown Command Center — interactions (vanilla JS)
   ============================================================ */
(function () {
  "use strict";

  const $  = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const CC = document.querySelector(".dc-cc");
  if (!CC) return;
  const q  = (s) => CC.querySelector(s);
  const qq = (s) => Array.from(CC.querySelectorAll(s));

  /* ---- CSRF helper ---- */
  function getCsrf() {
    const m = document.querySelector("meta[name='csrf-token']");
    if (m) return m.getAttribute("content");
    const c = document.cookie.split(";").find(p => p.trim().startsWith("csrftoken="));
    return c ? c.split("=")[1] : "";
  }

  /* ---- Toast ---- */
  const toastWrap = document.getElementById("dc-cc-toasts") ||
    (() => { const el = document.createElement("div"); el.id = "dc-cc-toasts"; el.className = "dc-cc-toasts"; document.body.appendChild(el); return el; })();

  function toast(title, sub, kind) {
    kind = kind || "info";
    const icons = { ok: "ph-check-circle", no: "ph-x-circle", info: "ph-bell" };
    const el = document.createElement("div");
    el.className = "dc-cc-toast";
    el.innerHTML =
      `<div class="ti ${kind}"><i class="ph-bold ${icons[kind] || icons.info}"></i></div>` +
      `<div class="tt"><b>${title}</b>${sub ? `<span>${sub}</span>` : ""}</div>`;
    toastWrap.appendChild(el);
    setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 300); }, 3200);
  }
  window.__dcToast = toast;

  /* ---- Animated counters ---- */
  function runCounters() {
    qq("[data-count]").forEach(el => {
      const target = parseFloat(el.dataset.count);
      if (isNaN(target)) return;
      const dec    = el.dataset.count.includes(".") ? 1 : 0;
      const prefix = el.dataset.prefix || "";
      const suffix = el.dataset.suffix || "";
      const dur = 850;
      const start = performance.now();
      function tick(now) {
        const p = Math.min((now - start) / dur, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        const v = (target * eased).toFixed(dec);
        el.textContent = prefix + Number(v).toLocaleString() + suffix;
        if (p < 1) requestAnimationFrame(tick);
        else el.textContent = prefix + target.toLocaleString() + suffix;
      }
      requestAnimationFrame(tick);
    });
    qq("[data-fill]").forEach(el => {
      const w = el.dataset.fill;
      el.style.width = "0%";
      requestAnimationFrame(() => requestAnimationFrame(() => { el.style.width = w + "%"; }));
    });
  }

  /* ---- Live countdown ---- */
  const timerEl = q("#matchTimer");
  if (timerEl) {
    let secs = parseInt(timerEl.dataset.secs || "0", 10);
    const fmt = s => {
      const m = Math.floor(s / 60), r = s % 60;
      return String(m).padStart(2, "0") + ":" + String(r).padStart(2, "0");
    };
    timerEl.textContent = fmt(secs);
    setInterval(() => { if (secs > 0) secs--; timerEl.textContent = fmt(secs); }, 1000);
  }

  /* ---- Performance lens / context switcher ---- */
  let lensesData = {};
  try { lensesData = JSON.parse((q("#lensesJson") || {}).textContent || "{}"); } catch(e) {}

  function boardRowHTML(row) {
    const rankColor = row.is_me ? "var(--acc-400)" : (row.c || "var(--dc-fg-soft)");
    const me  = row.is_me ? ' <span style="color:var(--acc-400);font-size:11px;">· you</span>' : "";
    const cls = row.is_me ? "row unread" : "row";
    const st  = row.is_me ? ' style="background:var(--acc-tint);border-radius:10px;"' : "";
    return `<div class="${cls}"${st}>` +
      `<div class="tr" style="width:32px;color:${rankColor};font-weight:700;">${row.r}</div>` +
      `<div class="crest" style="width:30px;height:30px;font-size:11px;background:linear-gradient(135deg,${row.g1||"#6849E5"},${row.g2||"#0A84FF"});">${row.tag}</div>` +
      `<div class="grow"><div class="t">${row.name}${me}</div></div>` +
      `<div class="tr">${row.pts}</div></div>`;
  }

  function renderLens(id) {
    const d = lensesData[id];
    if (!d) return;
    const set = (sel, prop, val) => { const el = q(sel); if (el) el[prop] = val; };
    /* stat tiles */
    const cpEl = q("#statCP");
    if (cpEl) { cpEl.dataset.count = d.rank.cp; cpEl.textContent = Number(d.rank.cp).toLocaleString(); }
    set("#statCPsub", "innerHTML",
      `<span style="color:${d.rank.tier_color};font-weight:600;">${d.rank.tier.toUpperCase()}</span>` +
      ` · <span class="up">+${d.rank.cp_delta||0} this week</span>`);
    const wrEl = q("#statWR");
    if (wrEl) { wrEl.dataset.count = d.stats.win_rate; wrEl.textContent = d.stats.win_rate + "%"; }
    set("#statWRsub", "textContent", `${d.stats.wins}W · ${d.stats.losses}L · ${d.stats.draws}D`);
    /* rank card */
    const badge = q("#rankBadge");
    if (badge) { badge.style.background = d.rank.tier_color; }
    const tier = q("#rankTier");
    if (tier) { tier.textContent = d.rank.tier; tier.style.color = d.rank.tier_color; }
    set("#rankPos",    "textContent", d.rank.pos);
    set("#rankPts",    "textContent", d.rank.pts);
    set("#rankLevel",  "textContent", "Level " + d.rank.level);
    set("#rankXpText", "textContent", d.rank.xp_current.toLocaleString() + " / " + d.rank.xp_needed.toLocaleString() + " XP");
    const bar = q("#rankBar");
    if (bar) { bar.dataset.fill = d.rank.xp_pct; bar.style.width = d.rank.xp_pct + "%"; }
    const promo = q("#rankPromo");
    if (promo) { promo.textContent = d.rank.promo_text; promo.style.color = d.rank.promo_color || "var(--dc-fg-soft)"; }
    /* streak */
    const sn = q("#streakN");
    if (sn) { sn.dataset.count = d.streak.current; sn.textContent = d.streak.current; }
    set("#streakLabel", "textContent", d.streak.label);
    const pills = q("#streakPills");
    if (pills) pills.innerHTML = d.streak.last_5.map(x => `<b class="${x}"></b>`).join("");
    set("#streakBest", "textContent", d.streak.best + " wins");
    /* leaderboard */
    const board = q("#boardRows");
    if (board) board.innerHTML = d.board.map(boardRowHTML).join("");
    /* re-run counters for animated values */
    runCounters();
  }

  const ctxPills = q("#ctxPills");
  if (ctxPills) {
    ctxPills.addEventListener("click", e => {
      const b = e.target.closest(".ctx");
      if (!b) return;
      qq("#ctxPills .ctx").forEach(x => x.classList.remove("on"));
      b.classList.add("on");
      renderLens(b.dataset.ctx);
    });
  }

  /* ---- Notifications filter + mark-all-read ---- */
  function notifCounts() {
    const rows = qq("#notifRows .row");
    const c = { all: rows.length, unread: 0, match: 0, invite: 0, reward: 0 };
    rows.forEach(r => {
      if (r.classList.contains("unread")) c.unread++;
      const t = r.dataset.type;
      if (c[t] !== undefined) c[t]++;
    });
    qq("#notifFilters .ct").forEach(el => {
      const k = el.dataset.countFor;
      el.textContent = c[k] != null ? c[k] : "";
    });
  }
  function applyNotifFilter(f) {
    qq("#notifRows .row").forEach(r => {
      const show = f === "all" || (f === "unread" && r.classList.contains("unread")) || r.dataset.type === f;
      r.style.display = show ? "" : "none";
    });
  }
  const notifFilters = q("#notifFilters");
  if (notifFilters) {
    notifFilters.addEventListener("click", e => {
      const b = e.target.closest(".nf-f");
      if (!b) return;
      qq("#notifFilters .nf-f").forEach(x => x.classList.remove("on"));
      b.classList.add("on");
      applyNotifFilter(b.dataset.f);
    });
  }
  const markAllBtn = q("#notifMarkAll");
  if (markAllBtn) {
    markAllBtn.addEventListener("click", () => {
      const unread = qq("#notifRows .row.unread");
      fetch("/notifications/mark-all-read/", {
        method: "POST",
        headers: { "X-CSRFToken": getCsrf(), "X-Requested-With": "XMLHttpRequest" },
      }).catch(() => {});
      unread.forEach(r => r.classList.remove("unread"));
      notifCounts();
      const bell = document.querySelector(".notif-badge, .notification-count");
      if (bell) bell.textContent = "0";
      toast("All caught up", unread.length + " notifications marked read", "ok");
    });
  }
  notifCounts();

  /* ---- Invites accept / decline ---- */
  function bumpInviteCount() {
    const remaining = qq("#inviteList .invite").length;
    const countEl = q("#inviteCount");
    if (countEl) countEl.textContent = remaining;
    if (remaining <= 0) {
      const empty = q("#inviteEmpty");
      if (empty) empty.classList.remove("hide");
    }
  }
  const inviteList = q("#inviteList");
  if (inviteList) {
    inviteList.addEventListener("click", e => {
      const btn = e.target.closest(".mini");
      if (!btn) return;
      const inv    = btn.closest(".invite");
      const invId  = inv.dataset.inviteId;
      const team   = inv.dataset.team || "team";
      const ok     = btn.classList.contains("ok");
      const action = ok ? "accept" : "decline";
      inv.classList.add("dismiss");
      fetch(`/notifications/api/team-invite/${invId}/${action}/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCsrf(), "X-Requested-With": "XMLHttpRequest" },
      }).catch(() => {});
      setTimeout(() => { inv.remove(); bumpInviteCount(); }, 300);
      if (ok) toast("Invite accepted", "You joined " + team, "ok");
      else toast("Invite declined", team + " invite dismissed", "no");
    });
  }

  /* ---- Daily reward claim ---- */
  const claimBtn = q("#dailyClaim");
  if (claimBtn) {
    claimBtn.addEventListener("click", function () {
      if (this.disabled) return;
      this.disabled = true;
      fetch("/api/daily-reward/claim/", {
        method: "POST",
        headers: { "X-CSRFToken": getCsrf(), "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
      }).then(r => r.json()).then(data => {
        if (data.ok) {
          const today = q("#drToday");
          if (today) { today.classList.add("done"); today.classList.remove("today"); const c = today.querySelector(".c"); if (c) c.innerHTML = '<i class="ph-bold ph-check"></i>'; }
          const streakEl = q("#loginStreak"); if (streakEl) streakEl.textContent = data.streak;
          if (data.balance != null) { const walletEl = q("#walletBal"); if (walletEl) walletEl.textContent = Number(data.balance).toLocaleString(); }
          this.style.opacity = "0.6"; this.style.cursor = "default";
          const dcPart = data.dc_earned > 0 ? " +" + data.dc_earned + " DC" : "";
          this.innerHTML = '<i class="ph-bold ph-check-circle"></i> Claimed · +' + data.xp_earned + " XP" + dcPart;
          const milestonePart = data.milestone ? " · " + data.milestone.label + "!" : "";
          toast("Daily reward claimed", "+" + data.xp_earned + " XP" + dcPart + milestonePart, "ok");
        } else {
          this.disabled = false;
          toast("Already claimed", data.error || "Come back tomorrow!", "info");
        }
      }).catch(() => { this.disabled = false; toast("Error", "Could not claim reward", "no"); });
    });
  }

  /* ---- Wallet actions ---- */
  const addFundsBtn = q("#addFunds");
  if (addFundsBtn) addFundsBtn.addEventListener("click", () => toast("Add DeltaCoin", "Top up via bKash, Nagad or card", "info"));
  const sendDcBtn = q("#sendDc");
  if (sendDcBtn) sendDcBtn.addEventListener("click", () => toast("Send DeltaCoin", "Transfer to a teammate or team wallet", "info"));

  /* ---- Join-request withdraw ---- */
  const jrList = q("#jrList");
  if (jrList) {
    jrList.addEventListener("click", e => {
      const b = e.target.closest(".jr-withdraw");
      if (!b) return;
      const row  = b.closest(".row");
      const jrId = row.dataset.jrId;
      const team = row.dataset.team || "team";
      fetch(`/api/join-request/${jrId}/withdraw/`, {
        method: "POST",
        headers: { "X-CSRFToken": getCsrf(), "X-Requested-With": "XMLHttpRequest" },
      }).catch(() => {});
      row.style.transition = "opacity 240ms, transform 240ms";
      row.style.opacity = "0";
      row.style.transform = "translateX(12px)";
      setTimeout(() => row.remove(), 240);
      toast("Request withdrawn", "Application to " + team + " cancelled", "no");
    });
  }

  /* ---- Onboarding checklist (new player) ---- */
  const checklist = q("#checklist");
  if (checklist) {
    function refreshRing() {
      const items = qq("#checklist .check");
      const done  = items.filter(i => i.classList.contains("done")).length;
      const pct   = items.length ? Math.round(done / items.length * 100) : 0;
      const ring  = q("#clRing"); if (ring) ring.style.setProperty("--p", pct);
      const num   = q("#clRingNum"); if (num) num.textContent = pct + "%";
      const cnt   = q("#clCount"); if (cnt) cnt.textContent = done + "/" + items.length;
    }
    checklist.addEventListener("click", e => {
      const c = e.target.closest(".check");
      if (!c || c.dataset.done === "true") return;
      refreshRing();
    });
    refreshRing();
  }

  /* ---- Initial render ---- */
  runCounters();

  /* ---- Primary lens auto-select ---- */
  const primaryPill = q("#ctxPills .ctx[data-primary='1']") || q("#ctxPills .ctx");
  if (primaryPill && Object.keys(lensesData).length) {
    renderLens(primaryPill.dataset.ctx);
  }

  /* ========================================================
     CROWN RANK / XP CAROUSEL
     Uses display-toggle + CSS fade (no transform, no width math).
     Slides: .rank-xp-slide  Dots: .rank-xp-dot[data-slide]
     ======================================================== */
  (function() {
    var slides = Array.from(document.querySelectorAll('.rank-xp-slide'));
    var dots   = Array.from(document.querySelectorAll('.rank-xp-dot[data-slide]'));
    var outer  = document.querySelector('.rank-xp-outer');
    if (!slides.length || !outer) return;

    var idx = 0;
    var TOTAL = slides.length;
    var autoTimer = null;
    var titles = ['Crown Rank', 'XP & Level'];
    var icons  = ['<i class="ph-fill ph-medal"></i>', '<i class="ph-fill ph-lightning"></i>'];

    // Show slide 0 on init
    slides[0].classList.add('dc-slide-on');

    function go(n) {
      var next = ((n % TOTAL) + TOTAL) % TOTAL;
      if (next === idx) return;
      slides[idx].classList.remove('dc-slide-on');
      idx = next;
      slides[idx].classList.add('dc-slide-on');

      dots.forEach(function(d, i) { d.classList.toggle('on', i === idx); });
      var titleEl = document.getElementById('rankXpTitle');
      var icEl    = document.getElementById('rankXpIc');
      if (titleEl) titleEl.textContent = titles[idx] || '';
      if (icEl)    icEl.innerHTML      = icons[idx]  || '';
    }

    function startAuto() { autoTimer = setInterval(function() { go(idx + 1); }, 5000); }
    function resetAuto() { clearInterval(autoTimer); startAuto(); }

    /* Dot clicks */
    dots.forEach(function(dot) {
      dot.addEventListener('click', function() {
        resetAuto();
        go(parseInt(dot.dataset.slide, 10));
      });
    });

    /* Touch swipe */
    var tStartX = 0, tMoved = false;
    outer.addEventListener('touchstart', function(e) { tStartX = e.touches[0].clientX; tMoved = false; }, {passive:true});
    outer.addEventListener('touchmove',  function()  { tMoved = true; }, {passive:true});
    outer.addEventListener('touchend',   function(e) {
      if (!tMoved) return;
      var dx = e.changedTouches[0].clientX - tStartX;
      if (Math.abs(dx) > 40) { resetAuto(); go(dx < 0 ? idx + 1 : idx - 1); }
    }, {passive:true});

    /* Mouse drag */
    var mStartX = 0, dragging = false, mMoved = false;
    outer.addEventListener('mousedown', function(e) {
      e.preventDefault();
      mStartX = e.clientX; dragging = true; mMoved = false;
      outer.style.cursor = 'grabbing';
    });
    document.addEventListener('mousemove', function() { if (dragging) mMoved = true; });
    document.addEventListener('mouseup', function(e) {
      if (!dragging) return;
      dragging = false; outer.style.cursor = '';
      if (!mMoved) return;
      var dx = e.clientX - mStartX;
      if (Math.abs(dx) > 40) { resetAuto(); go(dx < 0 ? idx + 1 : idx - 1); }
    });

    outer.addEventListener('mouseenter', function() { clearInterval(autoTimer); });
    outer.addEventListener('mouseleave', function() { if (!dragging) startAuto(); });

    startAuto();
  })();

  /* ========================================================
     WEEK SLIDER
     Buttons use data-week-dir="-1|1"; no inline handlers.
     ======================================================== */
  (function() {
    function shiftWeek(dir) {
      var url = new URL(window.location.href);
      var cur = parseInt(url.searchParams.get('week') || '0', 10);
      url.searchParams.set('week', cur + dir);
      window.location.href = url.toString();
    }

    Array.from(document.querySelectorAll('[data-week-dir]')).forEach(function(btn) {
      btn.addEventListener('click', function() {
        shiftWeek(parseInt(btn.dataset.weekDir, 10));
      });
    });

    var weekGrid = document.getElementById('weekGrid');
    if (weekGrid) {
      var wStartX = 0;
      weekGrid.addEventListener('touchstart', function(e) { wStartX = e.touches[0].clientX; }, {passive:true});
      weekGrid.addEventListener('touchend', function(e) {
        var dx = e.changedTouches[0].clientX - wStartX;
        if (Math.abs(dx) > 60) shiftWeek(dx < 0 ? 1 : -1);
      }, {passive:true});
    }
  })();

})();
