// DeltaCrown effects: scroll reveal + gentle parallax (guarded by prefers-reduced-motion)
(function () {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Scroll reveal
  if (!reduce && "IntersectionObserver" in window) {
    const els = Array.from(document.querySelectorAll(".dc-reveal"));
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("is-in");
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.15 });
    els.forEach(el => io.observe(el));
  } else {
    // If reduced motion, just show them
    document.querySelectorAll(".dc-reveal").forEach(el => el.classList.add("is-in"));
  }

  // Parallax: elements with [data-parallax="y"] will move slightly on scroll
  // Only in hero for now.
  if (!reduce) {
    const plx = document.querySelectorAll("[data-parallax='y']");
    const onScroll = () => {
      const y = window.scrollY || window.pageYOffset || 0;
      plx.forEach((el) => {
        const depth = parseFloat(el.getAttribute("data-depth") || "0.06"); // small movement
        el.style.transform = `translate3d(0, ${Math.min(1, y * depth)}px, 0)`;
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }
})();
