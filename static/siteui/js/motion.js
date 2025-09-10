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
