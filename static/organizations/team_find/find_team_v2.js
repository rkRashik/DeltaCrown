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
  const GAMES = (() => { try { return JSON.parse((document.getElementById("dc-scout-games") || {}).textContent || "{}"); } catch (e) { return {}; } })();
  const hasMatch = page.dataset.hasMatch === "1";
  let state = readUrlState(true);
  state.fr = new Set();   /* role filters (lowercased) */
  state.fk = new Set();   /* rank filters (lowercased) */
  state.tg = { verified: false, openroles: false, ranked: false };
  state.minScore = 0;

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
      if (by === "match") return Number(b.dataset.score || 0) - Number(a.dataset.score || 0);
      if (by === "name") return normalize(a.dataset.sortName).localeCompare(normalize(b.dataset.sortName));
      if (by === "members") return Number(b.dataset.sortMembers || 0) - Number(a.dataset.sortMembers || 0);
      return Number(a.dataset.originalIndex || 0) - Number(b.dataset.originalIndex || 0);
    });
    cards.forEach(c => grid.appendChild(c));
  }

  function matchesCard(card) {
    const q = normalize(state.q), region = normalize(state.region), platform = normalize(state.platform);
    const hay = normalize(card.dataset.search);
    if (q && !hay.includes(q)) return false;
    if (state.game && (card.dataset.gameSlug || "") !== state.game) return false;
    if (region && !normalize(card.dataset.region).includes(region)) return false;
    if (platform && !normalize(card.dataset.platform).includes(platform)) return false;
    if (state.fr.size) { const cr = normalize(card.dataset.role); if (![...state.fr].some(r => cr.includes(r))) return false; }
    if (state.fk.size) { const ck = normalize(card.dataset.rank); if (![...state.fk].some(r => ck.includes(r))) return false; }
    if (state.tg.verified && card.dataset.verified !== "1") return false;
    if (state.tg.openroles && !(Number(card.dataset.openroles || 0) > 1)) return false;
    if (state.tg.ranked && !normalize(card.dataset.rank)) return false;
    if (state.minScore && Number(card.dataset.score || 0) < state.minScore) return false;
    return true;
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
    const rebuild = ("game" in patch) || ("mode" in patch);
    if ("mode" in patch) { state.fr.clear(); state.fk.clear(); state.tg = { verified: false, openroles: false, ranked: false }; state.minScore = 0; }
    state = Object.assign({}, state, patch);
    syncControls();
    if (rebuild) buildAdvanced();
    applyFilters();
    if (!opts || opts.push !== false) pushStateUrl();
  }
  function debounce(fn, wait) { let t; return function () { const a = arguments; clearTimeout(t); t = setTimeout(() => fn.apply(null, a), wait); }; }

  /* ---- advanced game-aware filters (quick pills, role/rank chips, match slider) ---- */
  function qfPill(k, icon, label) { return `<button type="button" class="qf ${state.tg[k] ? "on" : ""}" data-ftoggle="${k}"><i class="ph-fill ${icon}"></i>${label}</button>`; }
  function advancedHtml() {
    const g = state.game && GAMES[state.game] ? GAMES[state.game] : null;
    const isTeams = state.mode === "teams";
    let h = `<div class="fgroup nopad"><div class="fttl"><span><i class="ph ph-lightning"></i>Quick filters</span></div><div class="qf-row">`;
    h += isTeams ? (qfPill("verified", "ph-seal-check", "Org verified") + qfPill("openroles", "ph-stack", "Multi-role")) : qfPill("ranked", "ph-medal", "Has rank");
    h += `</div></div>`;
    h += `<div class="fgroup"><div class="fttl"><span><i class="ph ph-user-focus"></i>Role</span>${g ? `<span class="fttl-game">${esc(g.name)}</span>` : ""}</div>`;
    if (g && g.roles && g.roles.length) h += `<div class="chip-multi">` + g.roles.map(r => `<button type="button" class="fchip ${state.fr.has(r.toLowerCase()) ? "on" : ""}" data-frole="${esc(r)}">${esc(r)}</button>`).join("") + `</div>`;
    else h += `<div class="privacy-note"><i class="ph-fill ph-info"></i> Pick a game above to filter by its specific roles &amp; ranks.</div>`;
    h += `</div>`;
    if (g && g.ranks && g.ranks.length) h += `<div class="fgroup"><div class="fttl"><span><i class="ph ph-trophy"></i>Rank</span></div><div class="chip-multi">` + g.ranks.map(r => `<button type="button" class="fchip ${state.fk.has(r.toLowerCase()) ? "on" : ""}" data-frank="${esc(r)}">${esc(r)}</button>`).join("") + `</div></div>`;
    if (hasMatch) h += `<div class="fgroup"><div class="fttl"><span><i class="ph ph-target"></i>Minimum match</span></div><div class="fslider"><div class="vrow"><span>Any</span><span class="v" data-scoreval>${state.minScore ? state.minScore + "%+" : "Any"}</span></div><input type="range" min="0" max="95" step="5" value="${state.minScore}" data-minscore style="--fill:${state.minScore}%"></div></div>`;
    return h;
  }
  function buildAdvanced() { $$("[data-filter-advanced],[data-filter-advanced-m]").forEach(h => { h.innerHTML = advancedHtml(); }); }
  page.addEventListener("click", e => {
    const ro = e.target.closest("[data-frole]");
    if (ro) { const v = ro.dataset.frole.toLowerCase(); state.fr.has(v) ? state.fr.delete(v) : state.fr.add(v); buildAdvanced(); applyFilters(); return; }
    const rk = e.target.closest("[data-frank]");
    if (rk) { const v = rk.dataset.frank.toLowerCase(); state.fk.has(v) ? state.fk.delete(v) : state.fk.add(v); buildAdvanced(); applyFilters(); return; }
    const tg = e.target.closest("[data-ftoggle]");
    if (tg) { const k = tg.dataset.ftoggle; state.tg[k] = !state.tg[k]; buildAdvanced(); applyFilters(); return; }
  });
  page.addEventListener("input", e => {
    if (!e.target.matches("[data-minscore]")) return;
    state.minScore = +e.target.value;
    e.target.style.setProperty("--fill", state.minScore + "%");
    $$("[data-scoreval]").forEach(s => s.textContent = state.minScore ? state.minScore + "%+" : "Any");
    applyFilters();
  });

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
  $$("[data-reset-filters]").forEach(b => b.addEventListener("click", e => {
    e.preventDefault();
    state.fr.clear(); state.fk.clear();
    state.tg = { verified: false, openroles: false, ranked: false };
    state.minScore = 0;
    setState({ game: "", q: "", region: "", platform: "", sort: "newest" });
    buildAdvanced();
  }));
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
      const team = activePerm();
      const name = team ? clean((team.querySelector(".pn") || {}).textContent) || "Your Team" : "Your Team";
      const color = (team && team.dataset.color) || "#0A84FF";
      const roleSel = f.querySelector("[data-pf-role]");
      const role = clean(f.querySelector("[name=title]").value) || (roleSel && roleSel.value) || "Open role";
      const rankSel = f.querySelector("[data-pf-rank]");
      const rank = rankSel ? clean(rankSel.value) : "";
      const region = clean(f.querySelector("[name=region]").value);
      const pitch = clean(f.querySelector("[name=short_pitch]").value) || "Your recruitment pitch appears here.";
      host.innerHTML = `<article class="scard" style="--g:${color}">
        <div class="scard-top"><div class="crest" style="background:${color}22">${esc(name.slice(0, 3).toUpperCase())}</div>
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

  /* permission-aware team switcher + game-aware role/rank fields */
  function activePerm() { return $("[data-perm-team].active") || $("[data-perm-team]"); }
  function fillGameFields(gameSlug) {
    const g = GAMES[gameSlug];
    const roleSel = $("[data-pf-role]"), rankSel = $("[data-pf-rank]"), glabel = $("[data-pf-gamelabel]");
    if (glabel) glabel.textContent = g ? g.name : "";
    const roles = (g && g.roles && g.roles.length) ? g.roles : ["IGL", "Entry", "Support", "Flex", "Coach"];
    if (roleSel) roleSel.innerHTML = roles.map(r => `<option>${esc(r)}</option>`).join("");
    const ranks = (g && g.ranks) ? g.ranks : [];
    if (rankSel) rankSel.innerHTML = `<option value="">Any rank</option>` + ranks.map(r => `<option>${esc(r)}</option>`).join("");
  }
  function mapRoleCategory(role) {
    const n = (role || "").toLowerCase();
    const map = [["igl", "IGL"], ["shot", "IGL"], ["call", "IGL"], ["duelist", "DUELIST"], ["entry", "ENTRY"], ["rush", "ENTRY"], ["assault", "ENTRY"], ["fragger", "ENTRY"], ["awp", "SNIPER"], ["sniper", "SNIPER"], ["controller", "CONTROLLER"], ["smoke", "CONTROLLER"], ["sentinel", "SENTINEL"], ["anchor", "SENTINEL"], ["initiat", "INITIATOR"], ["support", "SUPPORT"], ["sup", "SUPPORT"], ["lurk", "LURKER"], ["tank", "TANK"], ["dps", "DPS"], ["carry", "DPS"], ["mid", "DPS"], ["heal", "HEALER"], ["coach", "COACH"], ["analyst", "ANALYST"], ["manager", "MANAGER"], ["content", "CONTENT"]];
    for (const [k, v] of map) if (n.includes(k)) return v;
    return "OTHER";
  }
  const teamForm = $("[data-team-post-form]");
  $$("[data-perm-team]").forEach(b => b.addEventListener("click", () => {
    $$("[data-perm-team]").forEach(o => o.classList.toggle("active", o === b));
    fillGameFields(b.dataset.game);
    const r = teamForm.querySelector("[data-team-post-region]"), p = teamForm.querySelector("[data-team-post-platform]");
    if (r) r.value = b.dataset.region || ""; if (p) p.value = b.dataset.platform || "";
    previewFor("team");
  }));
  const crossSwitch = teamForm && teamForm.querySelector("[data-cross-switch]");
  const crossInput = teamForm && teamForm.querySelector("[data-cross-input]");
  if (crossSwitch) crossSwitch.addEventListener("click", () => { const on = crossSwitch.classList.toggle("on"); if (crossInput) crossInput.checked = on; });
  if (teamForm) {
    const init = activePerm();
    if (init) {
      fillGameFields(init.dataset.game);
      const r = teamForm.querySelector("[data-team-post-region]"), p = teamForm.querySelector("[data-team-post-platform]");
      if (r && !r.value) r.value = init.dataset.region || ""; if (p && !p.value) p.value = init.dataset.platform || "";
    }
    teamForm.addEventListener("input", () => previewFor("team"));
    teamForm.addEventListener("submit", async e => {
      e.preventDefault();
      const status = teamForm.querySelector("[data-team-post-status]");
      const submit = teamForm.querySelector("[type=submit]");
      const team = activePerm();
      if (!team || !team.dataset.apiUrl) { setStatus(status, "Pick a team to post as.", false); return; }
      const roleSel = teamForm.querySelector("[data-pf-role]");
      const role = roleSel ? clean(roleSel.value) : "";
      const d = new FormData(teamForm);
      const pitch = clean(d.get("short_pitch"));
      const payload = {
        title: clean(d.get("title")) || role,
        role_category: mapRoleCategory(role),
        rank_requirement: clean(d.get("rank_requirement")),
        region: clean(d.get("region")), platform: clean(d.get("platform")),
        short_pitch: pitch, description: pitch,
        cross_post_community: crossInput ? crossInput.checked : false,
        is_active: true,
      };
      try { if (submit) submit.disabled = true; setStatus(status, "Publishing…", true);
        await postJson(team.dataset.apiUrl, payload);
        setStatus(status, "Published to the Scouting Grounds and your team's manage page. Reload to see it.", true);
        toast("success", "Recruitment published", "Live for " + (clean((team.querySelector(".pn") || {}).textContent) || "your team") + ".");
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
  window.addEventListener("popstate", () => {
    const adv = { fr: state.fr, fk: state.fk, tg: state.tg, minScore: state.minScore };
    state = Object.assign(readUrlState(false), adv);
    syncControls(); buildAdvanced(); applyFilters();
  });

  /* ---- init ---- */
  syncControls();
  buildAdvanced();
  applyFilters();
  buildSpotlight();
  buildTicker();
  runReveal();
  previewFor("choice");
})();
