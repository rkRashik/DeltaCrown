// DeltaCrown Theme (no visible toggle)
// Behavior:
// 1) If URL has ?theme=light|dark|auto → persist to localStorage and apply.
// 2) Else if localStorage 'dc-theme' exists → apply.
// 3) Else → follow OS (prefers-color-scheme). No data-theme attribute set.
//
// You can override anytime by visiting /page?theme=dark or /page?theme=auto

(function () {
  const KEY = "dc-theme";
  const root = document.documentElement;
  const allowed = new Set(["light", "dark", "auto"]);

  function setTheme(value) {
    if (value === "auto" || !value) {
      // Remove explicit override → let CSS media query handle it
      root.removeAttribute("data-theme");
      localStorage.setItem(KEY, "auto");
      return "auto";
    }
    root.setAttribute("data-theme", value);
    localStorage.setItem(KEY, value);
    return value;
  }

  // 1) URL param override (e.g., ?theme=dark)
  try {
    const url = new URL(window.location.href);
    const q = url.searchParams.get("theme");
    if (q && allowed.has(q)) {
      setTheme(q);
      // clean param from URL without reload
      url.searchParams.delete("theme");
      window.history.replaceState({}, "", url.toString());
      return; // done for this load
    }
  } catch (_) {}

  // 2) Stored preference
  const stored = localStorage.getItem(KEY);
  if (allowed.has(stored)) {
    setTheme(stored);
    return;
  }

  // 3) Default to auto (OS)
  setTheme("auto");

  // Optional: react to OS changes only when in auto
  try {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", () => {
      if ((localStorage.getItem(KEY) || "auto") === "auto") {
        setTheme("auto"); // ensures attribute is absent
      }
    });
  } catch (_) {}

  // Small helper for dev console: window.setTheme('light'|'dark'|'auto')
  window.setTheme = setTheme;
})();
