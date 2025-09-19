// static/siteui/js/tournament-detail-neo.js
(function () {
  const root = document.querySelector(".tneo");
  if (!root) return;

  // ---- Tabs / Panes ---------------------------------------------------------
  const tabs = Array.from(root.querySelectorAll(".tabs .tab"));
  const panes = Array.from(root.querySelectorAll(".pane"));

  function activate(name) {
    // toggle active class
    tabs.forEach(t => t.classList.toggle("is-active", t.dataset.tab === name));
    panes.forEach(p => p.classList.toggle("is-active", p.dataset.pane === name));

    // lazy mount heavy embeds when first shown
    if (name === "live") lazyMountIframe(".pane[data-pane='live'] iframe");
    if (name === "bracket") lazyMountIframe(".pane[data-pane='bracket'] iframe");

    // update URL (no jump)
    const url = new URL(window.location.href);
    url.searchParams.set("tab", name);
    window.history.replaceState({}, "", url.toString());
  }

  function lazyMountIframe(sel) {
    const iframe = root.querySelector(sel);
    if (!iframe) return;
    // If src already set, do nothing
    if (iframe.getAttribute("data-src") == null && iframe.getAttribute("src")) return;
    const src = iframe.getAttribute("data-src") || iframe.getAttribute("src");
    if (!src) return;
    // Move to data-src initially to prevent autoload on first paint
    if (iframe.getAttribute("data-src") == null && iframe.getAttribute("src")) {
      iframe.setAttribute("data-src", iframe.getAttribute("src"));
      iframe.removeAttribute("src");
    }
    // Mount when pane becomes visible
    if (!iframe.getAttribute("src")) {
      iframe.setAttribute("src", iframe.getAttribute("data-src"));
    }
  }

  // initial tab from ?tab= or first tab
  (function initTab() {
    const params = new URLSearchParams(window.location.search);
    const wanted = params.get("tab");
    const firstTab = tabs[0]?.dataset.tab;
    activate(wanted || firstTab || "overview");
  })();

  // click handlers
  tabs.forEach(btn => {
    btn.addEventListener("click", () => activate(btn.dataset.tab));
  });

  // ---- Sticky section spy (for long pages with anchors) ---------------------
  const sectionMap = panes.reduce((m, p) => {
    m[p.dataset.pane] = p;
    return m;
  }, {});

  let spyTick = null;
  function onScrollSpy() {
    if (spyTick) return;
    spyTick = requestAnimationFrame(() => {
      spyTick = null;
      const viewportMid = window.scrollY + window.innerHeight * 0.35;
      let activeName = null;

      for (const name in sectionMap) {
        const el = sectionMap[name];
        const rect = el.getBoundingClientRect();
        const top = window.scrollY + rect.top;
        const bottom = top + rect.height;
        if (viewportMid >= top && viewportMid < bottom) {
          activeName = name;
          break;
        }
      }
      if (activeName) {
        tabs.forEach(t => t.classList.toggle("is-active", t.dataset.tab === activeName));
      }
    });
  }
  document.addEventListener("scroll", onScrollSpy, { passive: true });

  // ---- Countdown (hero) -----------------------------------------------------
  // Expects a target ISO datetime in [data-countdown] element
  const ctn = root.querySelector("[data-countdown]");
  if (ctn) {
    const targetISO = ctn.getAttribute("data-countdown");
    const target = targetISO ? new Date(targetISO) : null;

    function two(n) { return n < 10 ? "0" + n : "" + n; }

    function tick() {
      if (!target) return;
      const now = new Date();
      const diff = Math.max(0, Math.floor((target - now) / 1000));
      const d = Math.floor(diff / 86400);
      const h = Math.floor((diff % 86400) / 3600);
      const m = Math.floor((diff % 3600) / 60);
      const s = diff % 60;

      ctn.querySelector("[data-d]").textContent = d;
      ctn.querySelector("[data-h]").textContent = two(h);
      ctn.querySelector("[data-m]").textContent = two(m);
      ctn.querySelector("[data-s]").textContent = two(s);

      if (diff === 0) {
        ctn.classList.add("done");
        clearInterval(timer);
      }
    }

    const timer = setInterval(tick, 1000);
    tick();
  }

  // ---- Micro-animations (CTA hover glow) -----------------------------------
  const ctas = root.querySelectorAll(".btn-neo");
  ctas.forEach(btn => {
    btn.addEventListener("pointermove", (e) => {
      const r = btn.getBoundingClientRect();
      const x = e.clientX - r.left;
      const y = e.clientY - r.top;
      btn.style.setProperty("--mx", x + "px");
      btn.style.setProperty("--my", y + "px");
    });
  });

  // ---- “Copy to clipboard” helpers (for lobby code, etc.) -------------------
  root.querySelectorAll("[data-copy]").forEach(el => {
    el.addEventListener("click", async () => {
      const text = el.getAttribute("data-copy");
      try {
        await navigator.clipboard.writeText(text || "");
        el.classList.add("copied");
        setTimeout(() => el.classList.remove("copied"), 1200);
      } catch (e) {}
    });
  });

  // ---- Lazy images (if any with data-src) -----------------------------------
  const lazyImgs = [].slice.call(root.querySelectorAll("img[data-src]"));
  if ("IntersectionObserver" in window && lazyImgs.length) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          const img = e.target;
          img.src = img.getAttribute("data-src");
          img.removeAttribute("data-src");
          io.unobserve(img);
        }
      });
    }, { rootMargin: "200px" });
    lazyImgs.forEach(img => io.observe(img));
  }
})();
