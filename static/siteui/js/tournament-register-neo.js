// tournament-register-neo.js
// Hooks for the registration form in templates/tournaments/register.html
// - Toggles payment instruction panels (bKash/Nagad/Rocket)
// - Copies helper values (number/reference) to clipboard
// - Light client-side validation (txn required if fee > 0, phone format)
// - Reduced-motion friendly; graceful no-ops if elements are missing

(function () {
  const root = document.querySelector(".reg-neo");
  if (!root) return;

  const form = root.querySelector("form");
  if (!form) return;

  const methodRadios = Array.from(form.querySelectorAll("input[type='radio'][name='method']"));
  const methodWraps = Array.from(form.querySelectorAll(".method"));
  const infoBlocks = {};
  Array.from(form.querySelectorAll(".pay-info[data-method]")).forEach(el => {
    infoBlocks[el.getAttribute("data-method")] = el;
  });

  // --- Helpers ---------------------------------------------------------------
  function currentMethod() {
    const m = methodRadios.find(r => r.checked);
    return (m && m.value) || null;
  }

  function setMethod(name) {
    // Visual selection on chips
    methodWraps.forEach(w => w.classList.remove("is-active"));
    const activeWrap = form.querySelector(`.method input[value='${name}']`)?.closest(".method");
    if (activeWrap) activeWrap.classList.add("is-active");

    // Show the corresponding instructions (match CSS: .is-active)
    Object.keys(infoBlocks).forEach(k => {
      infoBlocks[k].classList.toggle("is-active", k === name);
    });

    // Mirror hidden input if present (harmless if absent)
    const hidden = form.querySelector("input[name='method'][type='hidden']");
    if (hidden) hidden.value = name;
  }

  function getTxnInput(activeMethod) {
    // Within the active panel, prefer an input with name="txn"
    const panel = infoBlocks[activeMethod];
    if (!panel) return null;
    const explicit = panel.querySelector("input[name='txn']");
    if (explicit) return explicit;

    // Fallback: first text input inside the panel
    return panel.querySelector("input[type='text'], input[type='search'], input[type='tel'], input[type='number']");
  }

  function isFeePositive() {
    // The template sets data-fee-positive="1" on .formgrid when entry_fee > 0
    const formgrid = root.querySelector(".formgrid");
    return formgrid && formgrid.getAttribute("data-fee-positive") === "1";
  }

  function setError(input, message) {
    if (!input) return;
    const field = input.closest(".field") || input.parentElement;
    if (!field) return;
    let err = field.querySelector(".err");
    if (!err) {
      err = document.createElement("div");
      err.className = "err";
      field.appendChild(err);
    }
    err.textContent = message || "";
    field.setAttribute("data-invalid", message ? "1" : "0");
    input.setAttribute("aria-invalid", message ? "true" : "false");
  }

  function clearErrors() {
    form.querySelectorAll(".field[data-invalid='1']").forEach(f => {
      f.removeAttribute("data-invalid");
    });
    form.querySelectorAll(".err").forEach(e => { e.textContent = ""; });
    form.querySelectorAll("[aria-invalid='true']").forEach(i => i.setAttribute("aria-invalid", "false"));
  }

  // --- Events ----------------------------------------------------------------
  methodRadios.forEach(r => {
    r.addEventListener("change", () => {
      setMethod(r.value);
    });
  });

  // Copy helpers (e.g., number/reference)
  form.querySelectorAll(".copy[data-copy]").forEach(el => {
    el.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(el.getAttribute("data-copy") || "");
        el.classList.add("copied");
        setTimeout(() => el.classList.remove("copied"), 1000);
      } catch (e) { /* ignore */ }
    });
  });

  // Default method: checked radio or first available
  (function initDefault() {
    let name = currentMethod();
    if (!name && methodRadios.length) {
      methodRadios[0].checked = true;
      name = methodRadios[0].value;
    }
    if (name) setMethod(name);

    // If no JS, all .pay-info are hidden; ensure the checked one is visible on load
    // This runs once on init to reveal the initial panel.
  })();

  // Lightweight client-side validation
  let submitting = false;
  form.addEventListener("submit", (e) => {
    clearErrors();

    // Honeypot: "website" must stay blank (ignored server-side too)
    const hp = form.querySelector("input[name='website']");
    if (hp && hp.value.trim() !== "") {
      e.preventDefault();
      return false;
    }

    // Phone: basic local pattern (optional tightening as needed)
    const phone = form.querySelector("input[name='phone']");
    if (phone && phone.value) {
      const ok = /^(?:\+?880|0)1[0-9]{9}$/.test(phone.value.replace(/\s+/g, ""));
      if (!ok) {
        e.preventDefault();
        setError(phone, "Enter a valid Bangladeshi mobile number.");
        phone.focus();
        return false;
      }
    }

    // If fee > 0, txn is required in the active panel
    if (isFeePositive()) {
      const cm = currentMethod();
      const txn = getTxnInput(cm);
      if (!txn || !txn.value || txn.value.trim().length < 6) {
        e.preventDefault();
        setMethod(cm || ""); // ensure the right panel is visible
        setError(txn, "Enter your payment transaction ID.");
        txn && txn.focus();
        return false;
      }
    }

    if (submitting) {
      e.preventDefault();
      return false;
    }
    submitting = true;

    // Disable primary submit to prevent double-post
    const submitBtn = form.querySelector("button[type='submit'], .btn-neo[type='submit']");
    submitBtn && (submitBtn.disabled = true);
  });
})();
