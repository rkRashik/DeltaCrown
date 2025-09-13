// static/siteui/js/tournaments-detail.js
(function () {
  // Tabs
  const tabsRoot = document.querySelector("[data-tabs]");
  if (tabsRoot) {
    const tabs = tabsRoot.querySelectorAll("button[data-tab]");
    const panels = {
      overview: document.getElementById("tab-overview"),
      participants: document.getElementById("tab-participants"),
      bracket: document.getElementById("tab-bracket"),
      standings: document.getElementById("tab-standings"),
      watch: document.getElementById("tab-watch"),
    };

    function show(id) {
      tabs.forEach((b) => {
        const active = b.dataset.tab === id;
        // Active background for both light & dark
        b.classList.toggle("bg-slate-200", active);
        b.classList.toggle("dark:bg-slate-700", active);
        // Text contrast
        b.classList.toggle("text-slate-900", active);
        b.classList.toggle("dark:text-slate-100", active);
        b.classList.toggle("text-slate-700", !active);
        b.classList.toggle("dark:text-slate-300", !active);
      });
      Object.entries(panels).forEach(([k, el]) => el && el.classList.toggle("hidden", k !== id));
    }

    // Initial state (use the first tab if none is marked active)
    const initial = Array.from(tabs).find((b) => b.classList.contains("bg-slate-200"))?.dataset.tab || "overview";
    show(initial);

    tabs.forEach((b) =>
      b.addEventListener("click", () => {
        show(b.dataset.tab);
        // update hash for shareable deep link (optional, harmless)
        history.replaceState(null, "", `#${b.dataset.tab}`);
      })
    );

    // Deep link restore
    const hash = location.hash.replace("#", "");
    if (hash && panels[hash]) show(hash);
  }

  // Countdown (unchanged)
  const cd = document.getElementById("countdown");
  if (cd) {
    const deadline = new Date(cd.dataset.deadline);
    function tick() {
      const now = new Date();
      let diff = Math.max(0, deadline - now);
      const s = Math.floor(diff / 1000);
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      const sec = s % 60;
      cd.textContent = `Starts in ${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
      if (diff > 0) requestAnimationFrame(() => setTimeout(tick, 250));
      else cd.textContent = "Starting soon";
    }
    tick();
  }
})();
