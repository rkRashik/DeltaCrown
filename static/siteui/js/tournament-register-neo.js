// tournament-register-neo.js
// Premium registration UX: payment method toggle, inline validation, copy helpers, micro-animations

(function () {
  const root = document.querySelector(".reg-neo");
  if (!root) return;

  // Copy helpers
  root.querySelectorAll("[data-copy]").forEach(el => {
    el.addEventListener("click", async () => {
      const text = el.getAttribute("data-copy") || "";
      try {
        await navigator.clipboard.writeText(text);
        el.classList.add("copied");
        setTimeout(() => el.classList.remove("copied"), 1000);
      } catch (e) {}
    });
  });

  // Payment method toggle
  const methodBtns = Array.from(root.querySelectorAll(".method input"));
  const infoBlocks = {
    bkash: root.querySelector(".pay-info[data-method='bkash']"),
    nagad: root.querySelector(".pay-info[data-method='nagad']"),
    rocket: root.querySelector(".pay-info[data-method='rocket']"),
  };

  function setMethod(name) {
    // Toggle visual active
    Array.from(root.querySelectorAll(".method")).forEach(m => m.classList.remove("is-active"));
    const wrap = root.querySelector(`.method input[value='${name}']`)?.closest(".method");
    if (wrap) wrap.classList.add("is-active");

    // Show corresponding instructions
    Object.keys(infoBlocks).forEach(k => {
      const el = infoBlocks[k];
      if (!el) return;
      el.classList.toggle("show", k === name);
    });

    // Sync hidden input if you use one
    const hidden = root.querySelector("input[name='method']");
    if (hidden) hidden.value = name;
  }

  methodBtns.forEach(radio => {
    radio.addEventListener("change", () => setMethod(radio.value));
  });

  // Initialize default method if any checked
  const checked = methodBtns.find(m => m.checked)?.value || "bkash";
  setMethod(checked);

  // Inline validation
  const form = root.querySelector("form");
  if (form) {
    form.addEventListener("submit", (e) => {
      // minimal required fields
      const required = ["display_name", "phone"];
      let ok = true;
      required.forEach(name => {
        const field = form.querySelector(`[name='${name}']`);
        if (!field) return;
        const val = (field.value || "").trim();
        const row = field.closest(".field") || field.parentElement;
        const err = row ? row.querySelector(".err") : null;
        if (!val) {
          ok = false;
          if (err) err.textContent = "Required field";
          field.setAttribute("aria-invalid", "true");
        } else {
          if (err) err.textContent = "";
          field.removeAttribute("aria-invalid");
        }
      });

      // If entry fee > 0 and a method requires a txn id, enforce it
      const needsTxn = !!root.querySelector("[data-fee-positive='1']");
      if (needsTxn) {
        const txn = form.querySelector("[name='txn']");
        if (txn && (txn.value || "").trim().length < 6) {
          ok = false;
          const row = txn.closest(".field");
          const err = row ? row.querySelector(".err") : null;
          if (err) err.textContent = "Enter a valid transaction ID";
          txn.setAttribute("aria-invalid", "true");
        }
      }

      if (!ok) {
        e.preventDefault();
        const firstErr = form.querySelector("[aria-invalid='true']");
        if (firstErr) firstErr.focus({ preventScroll: false });
        return;
      }

      // Submit micro animation
      const submitBtn = form.querySelector("button[type='submit'], .btn-neo[type='submit']");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.style.opacity = ".7";
        submitBtn.textContent = "Submitting…";
      }
    });
  }

  // Micro-animations on CTA
  root.querySelectorAll(".btn-neo").forEach(btn => {
    btn.addEventListener("pointermove", (e) => {
      const r = btn.getBoundingClientRect();
      btn.style.setProperty("--mx", (e.clientX - r.left) + "px");
      btn.style.setProperty("--my", (e.clientY - r.top) + "px");
    });
  });
})();
