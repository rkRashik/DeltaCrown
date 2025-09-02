// static/src/js/toasts.js
import { qs, qsa, on } from "./helpers.js";

(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const root = qs("#toast-root");
    if (!root) return;

    // Auto-dismiss in 4s unless focused/hovered
    qsa(".toast", root).forEach(t => {
      const btn = qs(".close", t);
      let tm = setTimeout(() => close(), 4000);

      function close() {
        t.style.opacity = "0";
        t.style.transform = "translateY(-6px)";
        setTimeout(() => t.remove(), 180);
      }

      on(t, "mouseenter", () => clearTimeout(tm));
      on(t, "mouseleave", () => tm = setTimeout(() => close(), 1500));
      on(btn, "click", close);
    });
  });
})();
