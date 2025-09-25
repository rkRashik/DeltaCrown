// Copy invite link
(function(){
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-copy],[data-copy-invite]");
    if (!btn) return;
    let text = "";
    if (btn.hasAttribute("data-copy")) {
      const input = document.querySelector(btn.getAttribute("data-copy"));
      if (input) text = input.value;
    } else if (btn.hasAttribute("data-copy-invite")) {
      text = btn.getAttribute("data-invite-url") || "";
    }
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
      const toasts = document.getElementById("dc-toasts");
      if (!toasts) return;
      const n = document.createElement("div");
      n.className = "glass rounded-xl px-3 py-2 text-sm";
      n.textContent = "Invite link copied";
      toasts.appendChild(n);
      setTimeout(() => n.remove(), 2200);
    });
  });
})();

// Teams list: light client-side filtering (optional)
(function(){
  const form = document.getElementById("teams-filter");
  const grid = document.getElementById("teams-grid");
  if (!form || !grid) return;

  function apply(){
    const q = (form.querySelector('input[name="q"]')?.value || "").toLowerCase().trim();
    const game = (form.querySelector('select[name="game"]')?.value || "").toLowerCase().trim();
    const open = form.querySelector('select[name="open"]')?.value || "";

    grid.querySelectorAll(".t-card").forEach(card => {
      const name = (card.querySelector(".t-card__title")?.textContent || "").toLowerCase();
      const g = (card.getAttribute("data-game") || "").toLowerCase();
      let ok = true;
      if (q && !name.includes(q)) ok = false;
      if (game && g !== game && !g.includes(game)) ok = false;
      if (open === "1" && !card.querySelector('[data-open="1"]')) ok = false;
      card.style.display = ok ? "" : "none";
    });
  }

  form.addEventListener("change", (e) => {
    if (e.target.matches("select")) apply();
  });
  form.addEventListener("submit", () => setTimeout(apply, 0));
  apply();
})();
