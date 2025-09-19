// tournament-matches-neo.js
// "My Matches" UX: filters, auto-refresh (optional), copy helpers, small animations

(function () {
  const root = document.querySelector(".mymatches");
  if (!root) return;

  // ------------- State -------------
  let autoRefreshOn = false;
  let autoTimer = null;
  const REFRESH_MS = 30 * 1000;

  // ------------- Elements -------------
  const filterGame = root.querySelector("[data-filter='game']");
  const filterState = root.querySelector("[data-filter='state']"); // upcoming|live|done|all
  const filterText = root.querySelector("[data-filter='search']");
  const autoSwitch = root.querySelector(".switch");
  const list = root.querySelector(".mm-list");

  // ------------- Helpers -------------
  function matches() {
    return Array.from(root.querySelectorAll(".mm-card"));
  }

  function text(el) {
    return (el.textContent || "").toLowerCase();
  }

  function applyFilters() {
    const game = (filterGame?.value || "all").toLowerCase();
    const state = (filterState?.value || "all").toLowerCase();
    const q = (filterText?.value || "").trim().toLowerCase();

    const rows = matches();
    let visible = 0;

    rows.forEach(row => {
      const tGame = (row.getAttribute("data-game") || "").toLowerCase();
      const tState = (row.getAttribute("data-state") || "").toLowerCase();
      const tText = text(row);

      let show = true;
      if (game !== "all" && tGame !== game) show = false;
      if (state !== "all" && tState !== state) show = false;
      if (q && !tText.includes(q)) show = false;

      row.style.display = show ? "" : "none";
      if (show) visible++;
    });

    const empty = root.querySelector(".mm-empty");
    if (empty) empty.style.display = visible === 0 ? "" : "none";
  }

  function setAuto(on) {
    autoRefreshOn = !!on;
    root.querySelector(".switch").classList.toggle("on", autoRefreshOn);
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
    if (autoRefreshOn) {
      autoTimer = setInterval(refresh, REFRESH_MS);
    }
  }

  async function refresh() {
    // Non-invasive: this demo reads data attributes already on the page.
    // If you expose an endpoint (e.g., /tournaments/my/matches/partial/),
    // replace this with a fetch and replace the `.mm-list` HTML.
    matches().forEach(card => {
      // Example: bump "starts-in" countdown badges if you output [data-start-iso]
      const iso = card.getAttribute("data-start-iso");
      if (!iso) return;
      const el = card.querySelector("[data-start-in]");
      if (!el) return;
      const diff = Math.max(0, Math.floor((new Date(iso) - new Date()) / 1000));
      const m = Math.floor(diff / 60), s = diff % 60;
      el.textContent = `${m}:${s.toString().padStart(2,"0")}`;
    });
  }

  // ------------- Events -------------
  if (filterGame) filterGame.addEventListener("change", applyFilters);
  if (filterState) filterState.addEventListener("change", applyFilters);
  if (filterText) filterText.addEventListener("input", applyFilters);

  if (autoSwitch) {
    autoSwitch.addEventListener("click", () => setAuto(!autoRefreshOn));
  }

  // Copy helpers (e.g., lobby code buttons)
  root.querySelectorAll("[data-copy]").forEach(el => {
    el.addEventListener("click", async () => {
      const text = el.getAttribute("data-copy") || "";
      try {
        await navigator.clipboard.writeText(text);
        el.classList.add("copied");
        setTimeout(() => el.classList.remove("copied"), 1000);
      } catch (e) {}
    });
  });

  // CTA hover micro-anim
  root.querySelectorAll(".btn-neo").forEach(btn => {
    btn.addEventListener("pointermove", (e) => {
      const r = btn.getBoundingClientRect();
      btn.style.setProperty("--mx", (e.clientX - r.left) + "px");
      btn.style.setProperty("--my", (e.clientY - r.top) + "px");
    });
  });

  // Initial run
  applyFilters();
  // Optionally turn on auto refresh by default:
  // setAuto(true);
})();
