/* ============================================================================
   DeltaCrown Homepage — "Front Row Hybrid" body runtime.

   Deliberately tiny and render-safe. All section + ambient motion is pure CSS
   (see home.css). This file only owns two isolated, framework-free behaviours:

     1. Live registration countdown — writes ONLY to its own text node every
        second (never re-renders the tree; the handoff "Lessons" regression).
     2. Homepage personalization — optional subtle fade between the server-provided
        verified contextual headline. Universal markup always works
        without JS; respects prefers-reduced-motion.
   ============================================================================ */
(function () {
  'use strict';

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  /* ── 1. Live countdown ──────────────────────────────────────────────────
     Renders the time remaining until an ISO deadline as HH:MM:SS, where the
     hour field is NOT capped at 24 (matches the design's "31:48:06"). */
  function initCountdowns() {
    var els = document.querySelectorAll('[data-countdown]');
    if (!els.length) return;

    function tick() {
      var now = Date.now();
      for (var i = 0; i < els.length; i++) {
        var el = els[i];
        var iso = el.getAttribute('data-countdown');
        var target = iso ? Date.parse(iso) : NaN;
        if (isNaN(target)) { continue; }
        var diff = Math.floor((target - now) / 1000);
        if (diff <= 0) {
          el.textContent = el.getAttribute('data-countdown-done') || 'Closed';
          el.removeAttribute('data-countdown');
          continue;
        }
        var h = Math.floor(diff / 3600);
        if (h >= 24) {
          var d = Math.floor(h / 24);
          var rh = h % 24;
          el.textContent = d + 'd ' + rh + 'h';
        } else {
          var m = Math.floor((diff % 3600) / 60);
          var s = diff % 60;
          el.textContent = pad(h) + ':' + pad(m) + ':' + pad(s);
        }
      }
    }

    tick();
    setInterval(tick, 1000);
  }

  /* ── 2. Homepage personalization ─────────────────────────────────────────────
     Each rotation item may carry: subcopy, primary_label/url, secondary_label/url.
     Primary CTA stays stable for critical states (the resolver only supplies
     rotation_items where rotating is safe). */
  function initHeroPersonalization() {
    var headings = document.querySelectorAll('.ol-hero-heading');
    if (!headings.length) return;
    function reveal() {
      headings.forEach(function (heading) {
        var context = heading.querySelector('.ol-hero-context');
        var universal = heading.querySelector('.ol-hero-universal');
        if (!context || !universal) return;
        heading.classList.add('is-personalized');
        universal.setAttribute('aria-hidden', 'true');
        context.removeAttribute('aria-hidden');
      });
    }
    // One enhancement only. Server-resolved action links stay immediately usable.
    // Two frames ensure the universal message has painted before the short hold.
    function schedule() {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { window.setTimeout(reveal, 1200); });
      });
    }
    if (document.visibilityState === 'hidden') {
      document.addEventListener('visibilitychange', function ready() {
        if (document.visibilityState !== 'hidden') {
          document.removeEventListener('visibilitychange', ready);
          schedule();
        }
      });
    } else { schedule(); }
  }

  /* ── 3. Tournament filters ──────────────────────────────────────────────
     Client-side, no reload. Toggles card visibility by data-game / data-entry /
     data-status, keeps aria-pressed in sync, prunes filters that match nothing,
     and shows a polite empty note. Progressive enhancement: without JS every
     card stays visible and the "All tournaments" link still works. */
  function initTournamentFilters() {
    var root = document.getElementById('homeTfilters');
    var grid = document.getElementById('homeTgrid');
    if (!root || !grid) return;
    var btns = Array.prototype.slice.call(root.querySelectorAll('.dc-tfilter'));
    var cards = Array.prototype.slice.call(grid.querySelectorAll('.dc-tcard'));
    var emptyNote = document.getElementById('homeTempty');
    if (!btns.length || !cards.length) return;

    function matches(card, type, val) {
      if (type === 'all') return true;
      if (type === 'game') return card.getAttribute('data-game') === val;
      if (type === 'entry') return card.getAttribute('data-entry') === val;
      if (type === 'status') return card.getAttribute('data-status') === val;
      return true;
    }

    // Hide any filter that would match zero cards (e.g. "Free entry" with no free events).
    btns.forEach(function (b) {
      var type = b.getAttribute('data-filter-type');
      if (type === 'all') return;
      var val = b.getAttribute('data-filter-value');
      var any = cards.some(function (c) { return matches(c, type, val); });
      if (!any) b.style.display = 'none';
    });

    function apply(type, val) {
      var shown = 0;
      cards.forEach(function (c) {
        var ok = matches(c, type, val);
        c.style.display = ok ? '' : 'none';
        if (ok) shown++;
      });
      if (emptyNote) emptyNote.style.display = shown ? 'none' : '';
    }

    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        btns.forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        b.setAttribute('aria-pressed', 'true');
        apply(b.getAttribute('data-filter-type'), b.getAttribute('data-filter-value'));
      });
    });
  }

  function init() {
    initCountdowns();
    initHeroPersonalization();
    initTournamentFilters();
  }

  if (document.readyState !== 'loading') {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }
}());
