(function(){
  const grid = document.getElementById("t-grid");
  if (!grid) return;

  // 1) Compute slot progress widths
  grid.querySelectorAll(".progress").forEach(p => {
    const total = +p.getAttribute("data-slots-total") || 0;
    const taken = +p.getAttribute("data-slots-taken") || 0;
    const bar = p.querySelector(".progress__bar");
    if (!bar || !total) return;
    const pct = Math.max(0, Math.min(100, Math.round((taken / total) * 100)));
    bar.style.width = pct + "%";
  });

  // 2) Client-side filters (progressive enhancement)
  const form = document.getElementById("t-filter");
  const gameSel = document.getElementById("filter-game");
  const statusWrap = document.getElementById("filter-status");
  const sortSel = document.getElementById("filter-sort");
  const searchInput = form?.querySelector('input[name="q"]');

  function applyFilters(){
    const q = (searchInput?.value || "").toLowerCase().trim();
    const game = (gameSel?.value || "").toLowerCase().trim();
    const status = statusWrap?.querySelector('input[type="radio"]:checked')?.value || "";

    let cards = Array.from(grid.querySelectorAll(".t-card"));
    // Filter
    cards.forEach(card => {
      const name = (card.querySelector(".t-card__title")?.textContent || "").toLowerCase();
      const g = (card.getAttribute("data-game") || "").toLowerCase();
      const s = (card.getAttribute("data-status") || "").toLowerCase();

      let ok = true;
      if (q && !name.includes(q)) ok = false;
      if (game && g !== game && !g.includes(game)) ok = false;
      if (status && s !== status) ok = false;

      card.style.display = ok ? "" : "none";
    });

    // Sort (only visible cards)
    const method = sortSel?.value || "";
    const visible = cards.filter(c => c.style.display !== "none");

    function val(card, key){
      switch (key) {
        case "start":
          return new Date(card.getAttribute("data-start") || 0).getTime() || 0;
        case "prize":
          return +(card.getAttribute("data-prize") || 0);
        case "entry":
          return +(card.getAttribute("data-entry") || 0);
        default:
          return 0;
      }
    }

    if (method) {
      visible.sort((a,b) => val(a, method) - val(b, method));
      visible.forEach(node => grid.appendChild(node));
    }
  }

  form?.addEventListener("change", (e) => {
    if (e.target.matches("select") || e.target.matches("input[type=radio]")) {
      applyFilters();
    }
  });
  searchInput?.addEventListener("input", () => { applyFilters(); });

  // Initial
  applyFilters();
})();
