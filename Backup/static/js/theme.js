(function () {
  const root = document.documentElement;
  const btn = document.getElementById("theme-toggle");
  const icon = document.getElementById("theme-icon");

  function apply(mode) {
    const m = mode || "system";
    if (m === "light") {
      root.dataset.theme = "light";
    } else if (m === "dark") {
      root.dataset.theme = "dark";
    } else {
      // system
      delete root.dataset.theme;
      if (window.matchMedia("(prefers-color-scheme: light)").matches) {
        root.dataset.theme = "light";
      } else {
        root.dataset.theme = "dark";
      }
    }
    localStorage.setItem("theme", m);
    if (icon) {
      icon.innerHTML =
        (root.dataset.theme === "light")
          ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m8.66-9H21m-17 0H3m2.93-6.07L5.5 5.5m12.02 12.02l1.43 1.43m0-13.45l-1.43-1.43M6.93 17.07l-1.43 1.43"/>'
          : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>';
    }
  }

  // init
  const saved = localStorage.getItem("theme");
  apply(saved || "system");

  // change on OS preference updates when in system mode
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if ((localStorage.getItem("theme") || "system") === "system") apply("system");
  });

  if (btn) {
    btn.addEventListener("click", () => {
      const current = localStorage.getItem("theme") || "system";
      apply(current === "dark" ? "light" : current === "light" ? "system" : "dark");
    });
  }
})();
