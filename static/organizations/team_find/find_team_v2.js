/* ============================================================
   DeltaCrown — Find Team / Scouting Grounds v2 · APP ENGINE
   Server-rendered REAL data (recruitment posts + public LFT
   profiles). This script adds the premium interactive layer:
   client-side filter / sort / search, collapsible game selector,
   command palette, quick-view drawer, role + theme preview,
   featured spotlight, live activity ticker, and real post forms.
   No fabricated rows are ever generated.
   ============================================================ */
(function () {
  const page = document.querySelector("[data-find-team-v2]");
  if (!page) return;

  const $ = (s, r = page) => r.querySelector(s);
  const $$ = (s, r = page) => [...r.querySelectorAll(s)];
  const canonicalUrl = page.dataset.canonicalUrl || "/teams/find/";
  const initialGame = page.dataset.initialGame || "";

  const panels = $$("[data-result-panel]");
  const tabs = $$("[data-mode-tab]");
  const gameOptions = $$("[data-game-option]");
  const filterControls = $$("[data-filter-control]");
  const searchInputs = $$("[data-find-search]");
  const resultCount = $("[data-result-count]");
  const resultLabel = $("[data-result-label]");

  $$("[data-find-card]").forEach((card, i) => { card.dataset.originalIndex = String(i); });

  const clean = (v) => (v || "").trim();
  const normalize = (v) => clean(v).toLowerCase();
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function readUrlState(useInitialGame) {
    const p = new URLSearchParams(window.location.search);
    const rawGame = p.get("game") || "";
    return {
      mode: p.get("mode") === "players" ? "players" : "teams",
      game: rawGame && rawGame !== "all" ? rawGame : (useInitialGame ? initialGame : ""),
      q: p.get("q") || "",
      region: p.get("region") || "",
      platform: p.get("platform") || "",
      sort: p.get("sort") || "newest",
    };
  }
  let state = readUrlState(true);

  function stateUrl() {
    const url = new URL(canonicalUrl, window.location.origin);
    if (state.game) url.searchParams.set("game", state.game);
    if (state.mode === "players") url.searchParams.set("mode", "players");
    if (clean(state.q)) url.searchParams.set("q", clean(state.q));
    if (clean(state.region)) url.searchParams.set("region", clean(state.region));
    if (clean(state.platform)) url.searchParams.set("platform", clean(state.platform));
    if (state.sort && state.sort !== "newest") url.searchParams.set("sort", state.sort);
    return `${url.pathname}${url.search}`;
  }
  function pushStateUrl() {
    const next = stateUrl();
    if (next !== `${window.location.pathname}${window.location.search}`) window.history.pushState({ ft: state }, "", next);
  }

  function setControlValue(name, value) {
    filterControls.filter(c => c.dataset.filterControl === name).forEach(c => { c.value = value || ""; if (c.value !== (value || "")) c.value = ""; });
  }

  function updateGameCurrent() {
    const opt = gameOptions.find(o => (o.dataset.game || "") === (state.game || "") && o.closest("[data-game-select]"));
    const cur = $("[data-game-select] .gs-current");
    if (!opt || !cur) return;
    const name = opt.querySelector(".gs-it-name");
    const logo = opt.querySelector(".gs-logo");
    const curName = cur.querySelector(".gs-cur-name");
    const curIcon = cur.querySelector(".gicon");
    if (name && curName) curName.textContent = name.textContent.trim();
    if (logo && curIcon) curIcon.innerHTML = logo.innerHTML;
    cur.classList.toggle("all", !state.game);
    cur.style.setProperty("--g", opt.style.getPropertyValue("--g") || "#0A84FF");
  }

  function syncControls() {
    tabs.forEach(tab => {
      const active = tab.dataset.modeTab === state.mode;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    panels.forEach(p => { p.hidden = p.dataset.resultPanel !== state.mode; });
    searchInputs.forEach(i => { if (i.value !== state.q) i.value = state.q || ""; });
    setControlValue("region", state.region);
    setControlValue("platform", state.platform);
    setControlValue("sort", state.sort || "newest");
    gameOptions.forEach(o => {
      const active = (o.dataset.game || "") === (state.game || "");
      o.classList.toggle("active", active);
      if (active) o.setAttribute("aria-current", "page"); else o.removeAttribute("aria-current");
    });
    updateGameCurrent();
  }

  function activePanel() { return panels.find(p => p.dataset.resultPanel === state.mode) || panels[0]; }

  function sortPanel(panel) {
    if (!panel) return;
    const grid = panel.querySelector("[data-card-grid]"); if (!grid) return;
    const cards = [...grid.querySelectorAll("[data-find-card]")];
    const by = state.sort || "newest";
    cards.sort((a, b) => {
      if (by === "name") return normalize(a.dataset.sortName).localeCompare(normalize(b.dataset.sortName));
      if (by === "members") return Number(b.dataset.sortMembers || 0) - Number(a.dataset.sortMembers || 0);
      return Number(a.dataset.originalIndex || 0) - Number(b.dataset.originalIndex || 0);
    });
    cards.forEach(c => grid.appendChild(c));
  }

  function matchesCard(card) {
    const q = normalize(state.q), region = normalize(state.region), platform = normalize(state.platform);
    const hay = normalize(card.dataset.search);
    return (!q || hay.includes(q))
      && (!state.game || (card.dataset.gameSlug || "") === state.game)
      && (!region || normalize(card.dataset.region).includes(region))
      && (!platform || normalize(card.dataset.platform).includes(platform));
  }

  function updateCount(panel) {
    if (!panel) return;
    const cards = [...panel.querySelectorAll("[data-find-card]")];
    const visible = cards.filter(c => !c.classList.contains("is-hidden"));
    const empty = panel.querySelector("[data-empty-state]");
    if (empty) empty.classList.toggle("is-hidden", visible.length > 0);
    if (resultCount) resultCount.textContent = String(visible.length);
    if (resultLabel) resultLabel.textContent = state.mode === "players" ? "LFT players" : "LFP teams";
  }

  function applyFilters() {
    const panel = activePanel();
    sortPanel(panel);
    panels.forEach(p => {
      [...p.querySelectorAll("[data-find-card]")].forEach(c => c.classList.toggle("is-hidden", !matchesCard(c)));
      if (p === panel) updateCount(p);
    });
  }

  function setState(patch, opts) {
    state = Object.assign({}, state, patch);
    syncControls();
    applyFilters();
    if (!opts || opts.push !== false) pushStateUrl();
  }
  function debounce(fn, wait) { let t; return function () { const a = arguments; clearTimeout(t); t = setTimeout(() => fn.apply(null, a), wait); }; }

  /* ---- tabs / search / game / filters ---- */
  tabs.forEach(tab => tab.addEventListener("click", () => setState({ mode: tab.dataset.modeTab || "teams" })));
  const debouncedSearch = debounce(v => setState({ q: v }), 130);
  searchInputs.forEach(inp => {
    inp.addEventListener("input", () => { searchInputs.forEach(o => { if (o !== inp) o.value = inp.value; }); debouncedSearch(inp.value); });
    if (inp.form) inp.form.addEventListener("submit", e => { e.preventDefault(); setState({ q: inp.value }); });
  });
  gameOptions.forEach(o => o.addEventListener("click", e => {
    e.preventDefault();
    setState({ game: o.dataset.game || "" });
    $$("[data-game-select]").forEach(g => g.classList.remove("open"));
    closeCmdk();
  }));
  filterControls.forEach(c => {
    c.addEventListener("change", () => { const k = c.dataset.filterControl; if (!k) return; const patch = {}; patch[k] = c.value || (k === "sort" ? "newest" : ""); setState(patch); });
    if (c.form) c.form.addEventListener("submit", e => e.preventDefault());
  });
  $$("[data-reset-filters]").forEach(b => b.addEventListener("click", e => { e.preventDefault(); setState({ game: "", q: "", region: "", platform: "", sort: "newest" }); }));
  $$("[data-clear-game]").forEach(b => b.addEventListener("click", e => { e.preventDefault(); setState({ game: "" }); }));

  /* ---- collapsible game selector ---- */
  $$("[data-gs-toggle]").forEach(b => b.addEventListener("click", () => { const gs = b.closest("[data-game-select]"); if (gs) gs.classList.toggle("open"); }));

  /* ---- command palette ---- */
  const cmdkOverlay = $("[data-cmdk-overlay]");
  const cmdkSearch = $("[data-cmdk-search]");
  function openCmdk() { if (!cmdkOverlay) return; cmdkOverlay.classList.add("open"); document.body.style.overflow = "hidden"; if (cmdkSearch) { cmdkSearch.value = ""; filterCmdk(""); setTimeout(() => cmdkSearch.focus(), 40); } }
  function closeCmdk() { if (!cmdkOverlay) return; cmdkOverlay.classList.remove("open"); document.body.style.overflow = ""; }
  function filterCmdk(q) { const n = normalize(q); $$("[data-cmdk-game]").forEach(it => it.classList.toggle("is-hidden", n && !normalize(it.dataset.cmdkGame).includes(n))); }
  $$("[data-open-cmdk]").forEach(b => b.addEventListener("click", openCmdk));
  $$("[data-close-cmdk]").forEach(b => b.addEventListener("click", closeCmdk));
  if (cmdkOverlay) cmdkOverlay.addEventListener("click", e => { if (e.target === cmdkOverlay) closeCmdk(); });
  if (cmdkSearch) cmdkSearch.addEventListener("input", () => filterCmdk(cmdkSearch.value));

  /* ---- quick-view drawer (from per-card <template>) ---- */
  const drawer = $("[data-drawer]");
  const drawerOverlay = $("[data-drawer-overlay]");
  const drawerBody = $("[data-drawer-body]");
  function openDrawer(id) {
    const tpl = document.getElementById(id);
    if (!tpl || !drawer || !drawerBody) return;
    drawerBody.innerHTML = tpl.innerHTML;
    drawer.classList.add("open");
    drawerOverlay.classList.add("open");
    document.body.style.overflow = "hidden";
  }
  function closeDrawer() { if (!drawer) return; drawer.classList.remove("open"); drawerOverlay.classList.remove("open"); drawerBody.innerHTML = ""; document.body.style.overflow = ""; }
  page.addEventListener("click", e => {
    const opener = e.target.closest("[data-open-drawer]");
    if (opener && !e.target.closest("a")) { e.preventDefault(); openDrawer(opener.dataset.openDrawer); }
  });
  $$("[data-close-drawer]").forEach(b => b.addEventListener("click", closeDrawer));
  if (drawerOverlay) drawerOverlay.addEventListener("click", e => { if (e.target === drawerOverlay) closeDrawer(); });

  /* ---- post modal ---- */
  const modal = $("[data-post-modal]");
  const steps = $$("[data-post-step]");
  function showStep(step) { steps.forEach(n => { n.hidden = n.dataset.postStep !== step; }); previewFor(step); }
  function openPost() { if (!modal) return; showStep("choice"); modal.classList.add("open"); document.body.style.overflow = "hidden"; }
  function closePost() { if (!modal) return; modal.classList.remove("open"); document.body.style.overflow = ""; }
  $$("[data-open-post-modal]").forEach(b => b.addEventListener("click", openPost));
  $$("[data-close-post-modal]").forEach(b => b.addEventListener("click", closePost));
  if (modal) modal.addEventListener("click", e => { if (e.target === modal) closePost(); });
  $$("[data-post-path]").forEach(b => b.addEventListener("click", () => showStep(b.dataset.postPath || "choice")));
  $$("[data-post-back]").forEach(b => b.addEventListener("click", () => showStep("choice")));

  function previewFor(step) {
    const host = $("#dc-modal-preview-card"); if (!host) return;
    if (step === "team") {
      const f = $("[data-team-post-form]"); if (!f) { host.innerHTML = ""; return; }
      const opt = f.querySelector("[data-team-post-team]") && f.querySelector("[data-team-post-team]").selectedOptions[0];
      const name = opt ? opt.textContent.split(" - ")[0].trim() : "Your Team";
      const role = clean(f.querySelector("[name=title]").value) || (f.querySelector("[name=role_category]").selectedOptions[0] || {}).textContent || "Open role";
      const rank = clean(f.querySelector("[name=rank_requirement]").value);
      const region = clean(f.querySelector("[name=region]").value);
      const pitch = clean(f.querySelector("[name=short_pitch]").value) || "Your recruitment pitch appears here.";
      host.innerHTML = `<article class="scard" style="--g:#0A84FF">
        <div class="scard-top"><div class="crest" style="background:#0A84FF22">${esc(name.slice(0, 3))}</div>
          <div class="scard-id"><div class="scard-name"><span class="nm">${esc(name)}</span></div>
          <div class="scard-meta">${region ? `<span class="mi"><i class="ph-fill ph-map-pin"></i>${esc(region)}</span>` : ""}</div></div></div>
        <div style="display:flex;gap:6px"><span class="chip chip-recruit"><i class="ph-fill ph-megaphone"></i>RECRUITING</span></div>
        <div class="brief"><div class="brief-role"><div><div class="need">Open role</div><div class="role">${esc(role)}</div></div></div>
        ${rank ? `<div class="req-row"><span class="req"><i class="ph-fill ph-medal"></i>Min <b>${esc(rank)}</b></span></div>` : ""}</div>
        <p class="pitch q">${esc(pitch)}</p></article>`;
    } else if (step === "player") {
      const f = $("[data-lft-post-form]"); if (!f) { host.innerHTML = ""; return; }
      const role = clean(f.querySelector("[name=primary_roles]").value) || "Your roles";
      const region = clean(f.querySelector("[name=preferred_region]").value);
      const availSel = f.querySelector("[name=availability]");
      const avail = availSel && availSel.selectedOptions[0] ? availSel.selectedOptions[0].textContent : "";
      host.innerHTML = `<article class="scard" style="--g:#8470EE">
        <div class="scard-top"><div class="crest round" style="background:linear-gradient(135deg,#8470EE,#8470EE88)">ME</div>
          <div class="scard-id"><div class="scard-name"><span class="nm">You</span></div>
          <div class="scard-meta">${region ? `<span class="mi"><i class="ph-fill ph-map-pin"></i>${esc(region)}</span>` : ""}</div></div></div>
        <div style="display:flex;gap:6px;flex-wrap:wrap"><span class="chip chip-free"><i class="ph-fill ph-flag-banner"></i>LOOKING FOR TEAM</span><span class="chip chip-muted">${esc(role)}</span></div>
        ${avail ? `<div class="scard-meta"><span class="mi"><i class="ph-fill ph-calendar-dots"></i>${esc(avail)}</span></div>` : ""}</article>`;
    } else {
      host.innerHTML = `<div class="privacy-note"><i class="ph-fill ph-eye"></i> Pick a path — a live preview of your card appears here as you type.</div>`;
    }
  }

  /* ---- real form submission (existing endpoints) ---- */
  function csrfToken() {
    const meta = document.querySelector("meta[name='csrf-token']");
    if (meta && meta.content && meta.content !== "NOTPROVIDED") return meta.content;
    const input = modal && modal.querySelector("[name=csrfmiddlewaretoken]");
    if (input && input.value && input.value !== "NOTPROVIDED") return input.value;
    const cookie = document.cookie.split(";").map(p => p.trim()).find(p => p.startsWith("csrftoken="));
    return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
  }
  async function postJson(url, payload) {
    const res = await fetch(url, { method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken(), "X-Requested-With": "XMLHttpRequest" },
      body: JSON.stringify(payload) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.success === false || data.error) throw new Error(data.error || "Request failed.");
    return data;
  }
  function setStatus(node, msg, ok) { if (!node) return; node.textContent = msg || ""; node.classList.toggle("is-ok", !!ok); node.classList.toggle("is-error", !!msg && !ok); }

  const teamForm = $("[data-team-post-form]");
  const teamSelect = teamForm && teamForm.querySelector("[data-team-post-team]");
  function fillTeamDefaults(force) {
    if (!teamSelect) return;
    const sel = teamSelect.selectedOptions[0]; if (!sel) return;
    const region = teamForm.querySelector("[data-team-post-region]");
    const platform = teamForm.querySelector("[data-team-post-platform]");
    if (region && (force || !region.value)) region.value = sel.dataset.region || "";
    if (platform && (force || !platform.value)) platform.value = sel.dataset.platform || "";
  }
  if (teamSelect) { teamSelect.addEventListener("change", () => { fillTeamDefaults(true); previewFor("team"); }); fillTeamDefaults(false); }
  if (teamForm) {
    teamForm.addEventListener("input", () => previewFor("team"));
    teamForm.addEventListener("submit", async e => {
      e.preventDefault();
      const status = teamForm.querySelector("[data-team-post-status]");
      const submit = teamForm.querySelector("[type=submit]");
      const sel = teamSelect && teamSelect.selectedOptions[0];
      if (!sel || !sel.dataset.apiUrl) { setStatus(status, "Choose a manageable team first.", false); return; }
      const d = new FormData(teamForm);
      const pitch = clean(d.get("short_pitch"));
      const payload = { title: clean(d.get("title")), role_category: clean(d.get("role_category")), rank_requirement: clean(d.get("rank_requirement")),
        region: clean(d.get("region")), platform: clean(d.get("platform")), short_pitch: pitch, description: pitch,
        cross_post_community: d.has("cross_post_community"), is_active: d.has("is_active") };
      try { if (submit) submit.disabled = true; setStatus(status, "Publishing…", true);
        await postJson(sel.dataset.apiUrl, payload);
        setStatus(status, "Published. Reload to see it in the grid.", true);
        toast("success", "Recruitment published", "Live on the Scouting Grounds.");
        teamForm.reset(); fillTeamDefaults(true); previewFor("team");
      } catch (err) { setStatus(status, err.message || "Could not publish.", false); toast("error", "Publish failed", err.message || ""); }
      finally { if (submit) submit.disabled = false; }
    });
  }
  const lftForm = $("[data-lft-post-form]");
  if (lftForm) {
    lftForm.addEventListener("input", () => previewFor("player"));
    lftForm.addEventListener("submit", async e => {
      e.preventDefault();
      const status = lftForm.querySelector("[data-lft-post-status]");
      const submit = lftForm.querySelector("[type=submit]");
      const d = new FormData(lftForm);
      const payload = { career_status: clean(d.get("career_status")), availability: clean(d.get("availability")),
        primary_roles: clean(d.get("primary_roles")), secondary_roles: clean(d.get("secondary_roles")),
        preferred_region: clean(d.get("preferred_region")), passport_id: clean(d.get("passport_id")) };
      try { if (submit) submit.disabled = true; setStatus(status, "Publishing…", true);
        await postJson(lftForm.dataset.lftApiUrl, payload);
        setStatus(status, "Published. Reload to see your LFT card.", true);
        toast("success", "LFT profile published", "You're discoverable now.");
      } catch (err) { setStatus(status, err.message || "Could not publish.", false); toast("error", "Publish failed", err.message || ""); }
      finally { if (submit) submit.disabled = false; }
    });
  }

  /* ---- mobile filter ---- */
  const mFilter = $("[data-mobile-filter]");
  const mOverlay = $("[data-mobile-filter-overlay]");
  function openMfilter() { if (!mFilter) return; mFilter.classList.add("open"); mOverlay.classList.add("open"); document.body.style.overflow = "hidden"; }
  function closeMfilter() { if (!mFilter) return; mFilter.classList.remove("open"); mOverlay.classList.remove("open"); document.body.style.overflow = ""; }
  $$("[data-open-mobile-filter]").forEach(b => b.addEventListener("click", openMfilter));
  $$("[data-close-mobile-filter]").forEach(b => b.addEventListener("click", closeMfilter));
  if (mOverlay) mOverlay.addEventListener("click", e => { if (e.target === mOverlay) closeMfilter(); });

  /* ---- toast ---- */
  function toast(kind, title, sub) {
    const wrap = $("[data-toast-wrap]"); if (!wrap) return;
    const el = document.createElement("div");
    el.className = `toast ${kind}`;
    const icon = kind === "success" ? "ph-check-circle" : kind === "error" ? "ph-warning-circle" : "ph-info";
    el.innerHTML = `<span class="ti"><i class="ph-fill ${icon}"></i></span><div><div class="tt">${esc(title)}</div>${sub ? `<div class="ts">${esc(sub)}</div>` : ""}</div>`;
    wrap.appendChild(el);
    setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 300); }, 3400);
  }

  /* ---- ribbon counters + reveal ---- */
  function animateCount(el) {
    if (el.dataset.done) return; el.dataset.done = "1";
    const target = +el.dataset.count || 0;
    el.textContent = target.toLocaleString();
    const dur = 1000, t0 = performance.now();
    const tick = t => { const p = Math.min(1, (t - t0) / dur); el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3))).toLocaleString(); if (p < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }
  function runReveal() { $$(".stat-ribbon [data-count]").forEach(animateCount); $$(".reveal").forEach(el => el.classList.add("in")); }

  /* ---- featured spotlight (built from real cards) ---- */
  let spotTimer = null, spotCur = 0, spotSlides = [];
  function cardToSlide(card) {
    const type = card.dataset.cardType;
    const accent = card.style.getPropertyValue("--g") || "#0A84FF";
    const name = (card.querySelector(".nm") || {}).textContent || "";
    const drawerId = card.dataset.openDrawer || "";
    const crestEl = card.querySelector(".crest");
    const isRound = crestEl && crestEl.classList.contains("round");
    const crestInner = crestEl ? crestEl.innerHTML : "";
    let sub = "", pitch = "", badge, cta;
    if (type === "team") {
      const role = (card.querySelector(".brief-role .role") || {}).textContent || "Open roster slot";
      const game = (card.querySelector(".gtag") || {}).textContent || "";
      sub = `Recruiting ${clean(role)}${game ? " · " + clean(game) : ""}`;
      pitch = clean((card.querySelector(".pitch") || {}).textContent || `${clean(name)} is recruiting now.`);
      badge = `<span class="chip chip-recruit"><i class="ph-fill ph-megaphone"></i>RECRUITING</span>`;
      cta = "View &amp; Apply";
    } else {
      const role = (card.querySelector(".chip-muted") || {}).textContent || "Player";
      const game = (card.querySelector(".gtag") || {}).textContent || "";
      sub = `${clean(role)}${game ? " · " + clean(game) : ""}`;
      pitch = "Free agent available for recruitment.";
      badge = `<span class="chip chip-free"><i class="ph-fill ph-flag-banner"></i>LFT</span>`;
      cta = "View Profile";
    }
    return { accent, name: clean(name), drawerId, crestInner, isRound, sub, pitch, badge, cta };
  }
  function buildSpotlight() {
    const stage = $("#dc-spot-stage"), dots = $("#dc-spot-dots"), glow = $("#dc-spot-glow");
    if (!stage) return;
    const teamCards = $$('[data-result-panel="teams"] [data-find-card]').slice(0, 3);
    const playerCards = $$('[data-result-panel="players"] [data-find-card]').slice(0, 2);
    spotSlides = [...teamCards, ...playerCards].slice(0, 4).map(cardToSlide);
    if (!spotSlides.length) {
      stage.innerHTML = `<div class="spot-empty"><i class="ph ph-binoculars"></i><div>No recruitment activity to feature yet.<br>Be the first to post.</div></div>`;
      if (dots) dots.innerHTML = ""; return;
    }
    stage.innerHTML = spotSlides.map((s, i) => `<div class="spot-slide ${i === 0 ? "on" : ""}" data-si="${i}">
      <div style="display:flex;gap:6px;flex-wrap:wrap">${s.badge}</div>
      <div class="spot-entity"><span class="spot-crest ${s.isRound ? "round" : ""}" style="background:${s.accent}33">${s.crestInner}</span>
        <div style="min-width:0"><div class="spot-name">${esc(s.name)}</div><div class="spot-sub">${esc(s.sub)}</div></div></div>
      <p class="spot-pitch">${esc(s.pitch).slice(0, 150)}</p>
      <div class="spot-foot"><button type="button" class="btn btn-primary btn-sm" data-open-drawer="${esc(s.drawerId)}"><i class="ph-bold ph-arrow-right"></i>${s.cta}</button></div>
    </div>`).join("");
    if (dots) dots.innerHTML = spotSlides.map((_, i) => `<span class="${i === 0 ? "on" : ""}" data-dot="${i}"></span>`).join("");
    const setGlow = i => { if (glow) glow.style.background = `radial-gradient(120% 80% at 80% 10%, ${spotSlides[i].accent}33, transparent 60%)`; };
    setGlow(0);
    const show = i => { spotCur = (i + spotSlides.length) % spotSlides.length;
      stage.querySelectorAll(".spot-slide").forEach(s => s.classList.toggle("on", +s.dataset.si === spotCur));
      if (dots) dots.querySelectorAll("[data-dot]").forEach(d => d.classList.toggle("on", +d.dataset.dot === spotCur));
      setGlow(spotCur); };
    const loop = () => { spotTimer = setInterval(() => show(spotCur + 1), 4500); };
    if (spotTimer) clearInterval(spotTimer);
    if (spotSlides.length > 1) loop();
    const sp = $("#dc-spotlight");
    sp.addEventListener("mouseenter", () => clearInterval(spotTimer));
    sp.addEventListener("mouseleave", () => { if (spotSlides.length > 1) loop(); });
    if (dots) dots.addEventListener("click", e => { const d = e.target.closest("[data-dot]"); if (d) { clearInterval(spotTimer); show(+d.dataset.dot); if (spotSlides.length > 1) loop(); } });
  }

  /* ---- live activity ticker (built from real cards) ---- */
  function buildTicker() {
    const track = $("#dc-ticker-track"); if (!track) return;
    const acts = [];
    $$('[data-result-panel="teams"] [data-find-card]').slice(0, 6).forEach(c => {
      const name = clean((c.querySelector(".nm") || {}).textContent);
      const role = clean((c.querySelector(".brief-role .role") || {}).textContent);
      if (name) acts.push(["ph-megaphone", "#2ECC71", `<b>${esc(name)}</b> is recruiting${role ? " a <b>" + esc(role) + "</b>" : ""}`]);
    });
    $$('[data-result-panel="players"] [data-find-card]').slice(0, 6).forEach(c => {
      const name = clean((c.querySelector(".nm") || {}).textContent);
      if (name) acts.push(["ph-identification-badge", "#B8A6F2", `<b>${esc(name)}</b> posted an <b>LFT profile</b>`]);
    });
    if (!acts.length) { if (track.parentElement) track.parentElement.style.display = "none"; return; }
    const one = acts.map(([ic, col, html]) => `<span class="tk"><i class="ph-fill ${ic}" style="color:${col}"></i>${html}</span><span class="tdot"></span>`).join("");
    track.innerHTML = one + one;
  }

  /* ---- keyboard + history ---- */
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openCmdk(); return; }
    if (e.key !== "Escape") return;
    closeCmdk(); closeDrawer(); closePost(); closeMfilter();
  });
  window.addEventListener("popstate", () => { state = readUrlState(false); syncControls(); applyFilters(); });

  /* ---- init ---- */
  syncControls();
  applyFilters();
  buildSpotlight();
  buildTicker();
  runReveal();
  previewFor("choice");
})();
