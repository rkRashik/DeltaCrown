// Password show/hide
(function(){
  document.addEventListener("click", (e)=>{
    const btn = e.target.closest("[data-toggle-password]");
    if (!btn) return;
    const inputId = btn.getAttribute("data-toggle-password");
    const input = document.getElementById(inputId);
    if (!input) return;
    const t = input.getAttribute("type") === "password" ? "text" : "password";
    input.setAttribute("type", t);
    btn.setAttribute("aria-pressed", t === "text" ? "true" : "false");
  });
})();

// Legacy toast removed - now using DC.toast from notifications.js
// Kept for backward compatibility, but redirects to new system
window.dcToast = (msg) => {
  if (window.DC && DC.toast) {
    DC.toast.info(msg);
  } else {
    console.warn('Toast system not loaded');
  }
};

/* OwnLobby account pages: password show/hide, submitting state, numeric code input.
   Progressive enhancement only; every form still posts normally without this file. */
(function () {
  'use strict';

  document.querySelectorAll('[data-auth-pw]').forEach(function (wrap) {
    var input = wrap.querySelector('input');
    var btn = wrap.querySelector('.auth-pw__toggle');
    if (!input || !btn) return;
    btn.hidden = false;
    btn.addEventListener('click', function () {
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.textContent = show ? 'Hide' : 'Show';
      btn.setAttribute('aria-pressed', show ? 'true' : 'false');
      btn.setAttribute('aria-label', (show ? 'Hide ' : 'Show ') + (btn.getAttribute('data-label') || 'password'));
    });
  });

  document.querySelectorAll('form[data-auth-form]').forEach(function (form) {
    form.addEventListener('submit', function () {
      var btn = form.querySelector('button[type="submit"].btn-auth');
      if (!btn || btn.getAttribute('aria-busy') === 'true') return;
      var busy = btn.getAttribute('data-busy-text');
      btn.setAttribute('aria-busy', 'true');
      if (busy) btn.textContent = busy;
      // Disable after the browser has captured the submit so the POST still goes out once.
      setTimeout(function () { btn.disabled = true; }, 0);
    });
  });

  // Back/forward cache restores the page with the busy state still set.
  window.addEventListener('pageshow', function (e) {
    if (!e.persisted) return;
    document.querySelectorAll('button.btn-auth[aria-busy="true"]').forEach(function (btn) {
      btn.disabled = false;
      btn.removeAttribute('aria-busy');
      if (btn.getAttribute('data-idle-text')) btn.textContent = btn.getAttribute('data-idle-text');
    });
  });

  // After a failed submit, put the keyboard on the first field that needs attention.
  var bad = document.querySelector('.auth-form [aria-invalid="true"], .auth-form input.form-input[aria-invalid="true"]');
  if (bad) bad.focus();

  document.querySelectorAll('input[data-digits-only]').forEach(function (input) {
    input.addEventListener('input', function () {
      var clean = input.value.replace(/\D/g, '').slice(0, input.maxLength > 0 ? input.maxLength : 12);
      if (clean !== input.value) input.value = clean;
    });
  });
})();
