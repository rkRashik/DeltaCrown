// static/siteui/js/theme.js
(function () {
  const root = document.documentElement;
  const KEY = "deltacrown:theme"; // 'light' | 'dark' | 'system'

  function prefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function apply(value) {
    const mode = value || "system";
    // If light mode is somehow set, default to dark
    const finalMode = mode === "light" ? "dark" : mode;
    root.setAttribute("data-theme", finalMode);
    // IMPORTANT: Toggle Tailwind's dark class so all `dark:*` utilities work
    const isDark = finalMode === "dark" || (finalMode === "system" && prefersDark());
    root.classList.toggle("dark", isDark);

    const label = document.querySelector("[data-theme-label]");
    if (label) label.textContent = finalMode;
  }

  function saved() {
    const savedValue = localStorage.getItem(KEY);
    // If light mode is saved, convert to dark
    if (savedValue === "light") {
      localStorage.setItem(KEY, "dark");
      return "dark";
    }
    return savedValue || "dark"; // Default to dark instead of system
  }

  function nextMode(current) {
    return current === "dark" ? "system" : "dark";
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-theme-toggle]");
    if (!btn) return;
    const newVal = nextMode(saved());
    localStorage.setItem(KEY, newVal);
    apply(newVal);
  });

  // React to OS theme changes when in 'system'
  if (window.matchMedia) {
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    mql.addEventListener("change", () => {
      if (saved() === "system") apply("system");
    });
  }

  // Initial paint
  apply(saved());
})();
