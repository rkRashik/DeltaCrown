(() => {
  const key = "dc_theme";
  const mKey = "dc_reduced_motion";
  const root = document.documentElement;

  // Reduced motion preference
  const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.dataset.reducedMotion = prefersReduced ? "reduce" : "no-preference";

  // Theme
  function applyTheme(mode) {
    if (mode === "dark") root.classList.add("dark");
    else root.classList.remove("dark");
    localStorage.setItem(key, mode);
  }

  function initTheme() {
    const saved = localStorage.getItem(key);
    if (saved) return applyTheme(saved);
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(prefersDark ? "dark" : "light");
  }

  document.addEventListener("click", (e) => {
    const t = e.target.closest("#theme-toggle");
    if (!t) return;
    const next = document.documentElement.classList.contains("dark") ? "light" : "dark";
    applyTheme(next);
    t.setAttribute("aria-pressed", next === "dark" ? "true" : "false");
  });

  initTheme();
})();
