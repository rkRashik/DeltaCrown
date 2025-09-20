// tournament-matches-neo.js
// Enhancements for templates/dashboard/my_matches.html (and legacy .mymatches)
// - Check-all checkbox
// - Enable/disable bulk action button depending on selection
// - Optional auto-refresh (?auto=1) when tab is visible
// - Safe no-ops if pieces are missing

(function () {
  const root = document.querySelector(".mmneo") || document.querySelector(".mymatches");
  if (!root) return;

  // --- Check-all for bulk form ------------------------------------------------
  const bulkForm = root.querySelector("form.mm-bulk") || root.querySelector("form[action*='my/matches/bulk']");
  const checkAll = root.querySelector('[data-mm="check-all"]');

  function matchCheckboxes() {
    return Array.from(root.querySelectorAll('input[type="checkbox"][name="match_ids"]'));
  }

  function updateBulkButton() {
    const btn = bulkForm ? bulkForm.querySelector('button[type="submit"]') : null;
    if (!btn) return;
    const anyChecked = matchCheckboxes().some(cb => cb.checked);
    btn.disabled = !anyChecked;
  }

  if (checkAll) {
    checkAll.addEventListener("change", (e) => {
      matchCheckboxes().forEach(cb => cb.checked = e.target.checked);
      updateBulkButton();
    });
  }
  matchCheckboxes().forEach(cb => {
    cb.addEventListener("change", updateBulkButton);
  });
  updateBulkButton();

  // --- Optional auto-refresh (disabled by default) ---------------------------
  // Turn on via ?auto=1 in the URL, respects visibility + reduced motion
  function urlHasAuto() {
    try {
      const u = new URL(window.location.href);
      return u.searchParams.get("auto") === "1";
    } catch { return false; }
  }

  if (urlHasAuto()) {
    const isReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!isReduced) {
      let timer = null;
      const periodMs = 90000; // 90s default
      const restart = () => {
        if (timer) clearInterval(timer);
        timer = setInterval(() => {
          if (document.visibilityState === "visible") {
            window.location.reload();
          }
        }, periodMs);
      };
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible") restart();
      });
      restart();
    }
  }

  // --- Progressive: CSV/ICS buttons are normal links; nothing else needed ----
  // --- Progressive: Filters are server-side via GET; JS not required. -------

  // --- Small UX: row hover ripple (CSS driven), no JS needed -----------------
})();
