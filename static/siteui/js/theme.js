// static/siteui/js/theme.js
(function () {
  const root = document.documentElement;
  const KEY = "deltacrown:theme"; // 'light' | 'dark' | 'system'

  function prefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function apply(value) {
    const mode = value || "system";
    root.setAttribute("data-theme", mode);
    // IMPORTANT: Toggle Tailwind's dark class so all `dark:*` utilities work
    const isDark = mode === "dark" || (mode === "system" && prefersDark());
    root.classList.toggle("dark", isDark);

    const label = document.querySelector("[data-theme-label]");
    if (label) label.textContent = mode;
  }

  function saved() {
    return localStorage.getItem(KEY) || "system";
  }

  function nextMode(current) {
    return current === "system" ? "dark" : current === "dark" ? "light" : "system";
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
