// static/js/theme.js
// Theme toggle + persistence
(function () {
  const KEY = "dc-theme"; // 'light' | 'dark' | 'auto'
  const root = document.documentElement;

  function apply(theme) {
    if (!theme || theme === "auto") {
      root.removeAttribute("data-theme"); // let prefers-color-scheme drive
      localStorage.setItem(KEY, "auto");
      return;
    }
    root.setAttribute("data-theme", theme);
    localStorage.setItem(KEY, theme);
  }

  function get() {
    return localStorage.getItem(KEY) || "auto";
  }

  // Initialize
  apply(get());

  // Button binding
  function nextTheme(current) {
    // cycle: auto -> dark -> light -> auto
    if (current === "auto") return "dark";
    if (current === "dark") return "light";
    return "auto";
  }

  function updateButtonVisual(btn, theme) {
    if (!btn) return;
    btn.setAttribute("data-theme", theme);
    btn.title = "Theme: " + theme;
  }

  function bind() {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    updateButtonVisual(btn, get());
    btn.addEventListener("click", () => {
      const n = nextTheme(get());
      apply(n);
      updateButtonVisual(btn, n);
    });
  }

  document.addEventListener("DOMContentLoaded", bind);

  // React to OS changes when in auto
  try {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", () => {
      if (get() === "auto") apply("auto");
    });
  } catch (_) {}
})();
