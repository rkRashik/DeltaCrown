(function () {
  const root = document.documentElement;
  const KEY = "deltacrown:theme"; // 'light' | 'dark' | 'system'

  function apply(value) {
    root.setAttribute("data-theme", value || "system");
    const label = document.querySelector('[data-theme-label]');
    if (label) label.textContent = value || "system";
  }

  function saved() { return localStorage.getItem(KEY) || "system"; }

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

  apply(saved());
})();
