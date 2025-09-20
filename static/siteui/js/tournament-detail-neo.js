// tournament-detail-neo.js — premium detail page logic (tabs, countdown, lazy mounts)
// Enhancements: keyboard tabs, aria-selected sync, deep links (?tab= / #tab), popstate support.

(function () {
  const root = document.querySelector(".tneo");
  if (!root) return;

  // ---- Tabs / Panes ---------------------------------------------------------
  const tabs = Array.from(root.querySelectorAll(".tabs .tab"));
  const panes = Array.from(root.querySelectorAll(".pane"));

  function setAria(name) {
    tabs.forEach(t => t.setAttribute("aria-selected", String(t.dataset.tab === name)));
  }

  function lazyMountIframesIn(paneName) {
    const wrap = root.querySelector(`.pane[data-pane='${paneName}']`);
    if (!wrap) return;
    wrap.querySelectorAll("iframe").forEach(iframe => {
      // If already mounted, skip
      if (iframe.getAttribute("src")) return;
      const src = iframe.getAttribute("data-src");
      if (src) iframe.setAttribute("src", src);
    });
  }

  function activate(name) {
    if (!name) return;
    tabs.forEach(t => t.classList.toggle("is-active", t.dataset.tab === name));
    panes.forEach(p => p.classList.toggle("is-active", p.dataset.pane === name));
    setAria(name);

    // lazy mount heavy embeds when first shown
    if (name === "live") lazyMountIframesIn("live");
    if (name === "bracket") lazyMountIframesIn("bracket");

    // update URL (no jump)
    const url = new URL(window.location.href);
    url.searchParams.set("tab", name);
    url.hash = ""; // normalize to ?tab=
    window.history.replaceState({ tab: name }, "", url.toString());
  }

  // initial tab from #hash or ?tab= or first tab
  (function initTab() {
    const url = new URL(window.location.href);
    const qsTab = url.searchParams.get("tab");
    const hash = (window.location.hash || "").replace("#", "");
    const names = new Set(tabs.map(t => t.dataset.tab));
    const firstTab = tabs[0]?.dataset.tab || "overview";
    const wanted = names.has(hash) ? hash : (names.has(qsTab) ? qsTab : firstTab);

    // Move any eager src -> data-src for bracket/live to prevent autoload
    ["live", "bracket"].forEach(pn => {
      root.querySelectorAll(`.pane[data-pane='${pn}'] iframe[src]`).forEach(ifr => {
        if (!ifr.getAttribute("data-src")) {
          ifr.setAttribute("data-src", ifr.getAttribute("src"));
          ifr.removeAttribute("src");
        }
      });
    });

    activate(wanted);
  })();

  // click handlers
  tabs.forEach(btn => {
    btn.addEventListener("click", () => activate(btn.dataset.tab));
    // keyboard nav (Left/Right/Home/End)
    btn.addEventListener("keydown", (e) => {
      const i = tabs.indexOf(btn);
      if (e.key === "ArrowRight") {
        e.preventDefault();
        const next = tabs[(i + 1) % tabs.length];
        next.focus(); activate(next.dataset.tab);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        const prev = tabs[(i - 1 + tabs.length) % tabs.length];
        prev.focus(); activate(prev.dataset.tab);
      } else if (e.key === "Home") {
        e.preventDefault();
        tabs[0].focus(); activate(tabs[0].dataset.tab);
      } else if (e.key === "End") {
        e.preventDefault();
        const last = tabs[tabs.length - 1];
        last.focus(); activate(last.dataset.tab);
      }
    });
  });

  // respond to back/forward when ?tab= changes
  window.addEventListener("popstate", () => {
    const params = new URLSearchParams(window.location.search);
    const name = params.get("tab");
    if (name) activate(name);
  });

  // ---- Sticky section spy (for long pages with anchors) ---------------------
  const sectionMap = panes.reduce((m, p) => { m[p.dataset.pane] = p; return m; }, {});
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
        if (viewportMid >= top && viewportMid < bottom) { activeName = name; break; }
      }
      if (activeName) {
        tabs.forEach(t => t.classList.toggle("is-active", t.dataset.tab === activeName));
        setAria(activeName);
      }
    });
  }
  document.addEventListener("scroll", onScrollSpy, { passive: true });

  // ---- Countdown (hero) -----------------------------------------------------
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
  const lazyImgs = Array.from(root.querySelectorAll("img[data-src]"));
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
