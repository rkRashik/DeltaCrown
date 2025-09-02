// static/src/js/forms.js
// Disable submit buttons on submit, add aria-busy, and optional confirmation.
// Lightweight; no dependencies.

(function () {
  function on(el, ev, fn) { el && el.addEventListener(ev, fn); }
  function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

  document.addEventListener("DOMContentLoaded", () => {
    qsa("form").forEach(form => {
      on(form, "submit", (e) => {
        // Optional confirm on the clicked submit button
        const submitter = e.submitter;
        if (submitter && submitter.hasAttribute("data-confirm")) {
          const msg = submitter.getAttribute("data-confirm");
          if (!window.confirm(msg)) {
            e.preventDefault();
            return;
          }
        }
        // Busy state
        form.setAttribute("aria-busy", "true");

        // Disable all submit buttons
        qsa('button[type="submit"], input[type="submit"]', form).forEach(btn => {
          if (btn.disabled) return;
          btn.disabled = true;

          // If the button has a data-busy-text, swap text to include a spinner
          const busyText = btn.getAttribute("data-busy-text");
          if (busyText) {
            // Try to preserve width to avoid layout shift
            const w = btn.getBoundingClientRect().width;
            btn.style.width = w ? w + "px" : null;
            btn.dataset._origText = btn.innerHTML;
            btn.innerHTML = '<span class="spinner" aria-hidden="true"></span> ' + busyText;
          }
        });
      });
    });
  });
})();
