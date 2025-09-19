// tournaments-detail.js
// Non-intrusive orchestrator for the Tournament Detail page.
// Plays nicely with tournament-detail-neo.js (no duplication).

(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

  const root = $(".tneo") || $(".tournament-detail") || $(".tournament-page");
  if (!root) return;

  // ---- Share / Copy link ----------------------------------------------------
  $$(".js-share, [data-share]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const title = document.title || "Tournament";
      const url = window.location.href;
      try {
        if (navigator.share) {
          await navigator.share({ title, url });
        } else {
          await navigator.clipboard.writeText(url);
          btn.classList.add("copied");
          setTimeout(() => btn.classList.remove("copied"), 900);
        }
      } catch (e) {}
    });
  });

  // ---- Favorite / Bell (visual only; emit custom events) --------------------
  const fav = $("[data-favorite]");
  const bell = $("[data-notify]");
  if (fav) {
    fav.addEventListener("click", () => {
      fav.classList.toggle("is-on");
      root.dispatchEvent(new CustomEvent("favorite:toggle", { detail: { on: fav.classList.contains("is-on") }}));
    });
  }
  if (bell) {
    bell.addEventListener("click", () => {
      bell.classList.toggle("is-on");
      root.dispatchEvent(new CustomEvent("notify:toggle", { detail: { on: bell.classList.contains("is-on") }}));
    });
  }

  // ---- Sticky in-page nav (anchors) ----------------------------------------
  const anchorNav = $(".tabs, .tournament-tabs, .tabs-wrap");
  if (anchorNav) {
    anchorNav.addEventListener("click", (e) => {
      const a = e.target.closest("[data-tab], [href^='#']");
      if (!a) return;
      const name = a.dataset.tab || a.getAttribute("href").replace("#","");
      const target = root.querySelector(`.pane[data-pane='${name}']`) || $("#" + name);
      if (!target) return;

      e.preventDefault();
      const top = target.getBoundingClientRect().top + window.scrollY - 72; // offset for sticky headers
      window.scrollTo({ top, behavior: "smooth" });

      // Mark active (if not handled by neo.js)
      $$(".tab", anchorNav).forEach(t => t.classList.toggle("is-active", (t.dataset.tab === name)));
      const url = new URL(window.location.href);
      url.hash = "";
      url.searchParams.set("tab", name);
      history.replaceState({}, "", url.toString());
    });
  }

  // ---- Lazy videos (non-iframe thumbnails -> iframe) -----------------------
  $$(".js-lazy-video").forEach(card => {
    const btn = $(".js-play", card);
    const id = card.getAttribute("data-yt");
    if (!btn || !id) return;
    btn.addEventListener("click", () => {
      const iframe = document.createElement("iframe");
      iframe.width = "100%";
      iframe.height = "100%";
      iframe.allow =
        "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
      iframe.allowFullscreen = true;
      iframe.src = "https://www.youtube.com/embed/" + encodeURIComponent(id) + "?autoplay=1&rel=0";
      card.innerHTML = "";
      card.appendChild(iframe);
    });
  });

  // ---- Countdown “pips” (optional tiny LEDs) --------------------------------
  const pip = $("[data-pips]");
  if (pip) {
    let i = 0;
    setInterval(() => {
      i = (i + 1) % 3;
      pip.setAttribute("data-pips", i + 1);
    }, 700);
  }

  // ---- External: emit events so pages can hook (analytics, etc.) -----------
  root.dispatchEvent(new CustomEvent("tournament:detail:init", {
    detail: {
      slug: root.getAttribute("data-slug") || null,
      game: root.getAttribute("data-game") || null,
    }
  }));
})();
