// Reveal on scroll (respects reduced motion)
(function () {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    document.querySelectorAll("[data-reveal]").forEach(n => n.classList.add("is-shown"));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        const delay = +e.target.getAttribute("data-reveal-delay") || 0;
        setTimeout(() => e.target.classList.add("is-shown"), delay);
        io.unobserve(e.target);
      }
    });
  }, { rootMargin: "0px 0px -10% 0px" });
  document.querySelectorAll("[data-reveal]").forEach(n => io.observe(n));
})();

// Count up (tests expect data-count-to)
(function () {
  const els = document.querySelectorAll("[data-count-to]");
  if (!els.length) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      const el = e.target;
      const target = +el.getAttribute("data-count-to");
      const prefix = el.getAttribute("data-prefix") || "";
      const suffix = el.getAttribute("data-suffix") || "";
      const start = performance.now();
      const duration = 1200;

      function tick(now) {
        const p = Math.min(1, (now - start) / duration);
        const val = Math.floor(target * p);
        el.textContent = prefix + val.toLocaleString() + suffix;
        if (p < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
      io.unobserve(el);
    });
  }, { threshold: .4 });
  els.forEach(el => io.observe(el));
})();

// Countdown (expects ISO string in data-deadline)
(function () {
  function render(el) {
    const iso = el.getAttribute("data-deadline");
    if (!iso) return;
    const digits = el.querySelector("[data-countdown-digits]");
    const end = new Date(iso).getTime();
    function fmt() {
      if (isNaN(end)) return "—";
      const d = Math.max(0, end - Date.now());
      const hh = String(Math.floor(d / 3600000)).padStart(2, "0");
      const mm = String(Math.floor((d % 3600000) / 60000)).padStart(2, "0");
      const ss = String(Math.floor((d % 60000) / 1000)).padStart(2, "0");
      return `${hh}:${mm}:${ss}`;
    }
    function tick() { if (digits) digits.textContent = fmt(); }
    tick();
    setInterval(tick, 1000);
  }
  document.querySelectorAll("[data-countdown]").forEach(render);
})();


// Countdown (expects ISO string in data-deadline)
(function () {
  function init(el) {
    const iso = el.getAttribute("data-deadline");
    const digits = el.querySelector("[data-countdown-digits]");
    const label = el.querySelector("[data-countdown-label]");
    if (!iso || !digits) return;

    const end = new Date(iso).getTime();
    if (Number.isNaN(end)) { digits.textContent = "—"; return; }

    function tick() {
      const now = Date.now();
      const diff = end - now;

      if (diff <= 0) {
        if (label) label.textContent = "Status";
        digits.textContent = "Live Now";
        return; // stop ticking
      }

      let remaining = diff;
      const days = Math.floor(remaining / 86400000); remaining %= 86400000;
      const hh = String(Math.floor(remaining / 3600000)).padStart(2, "0");
      remaining %= 3600000;
      const mm = String(Math.floor(remaining / 60000)).padStart(2, "0");
      remaining %= 60000;
      const ss = String(Math.floor(remaining / 1000)).padStart(2, "0");

      digits.textContent = (days > 0 ? days + "d " : "") + `${hh}:${mm}:${ss}`;
    }

    tick();
    const id = setInterval(tick, 1000);
    // Optional: clear on page unload
    window.addEventListener("beforeunload", () => clearInterval(id), { once: true });
  }

  document.querySelectorAll("[data-countdown]").forEach(init);
})();
