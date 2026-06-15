/* ============================================================================
   DeltaCrown Homepage — "Front Row Hybrid" body runtime.

   Deliberately tiny and render-safe. All section + ambient motion is pure CSS
   (see home.css). This file only owns two isolated, framework-free behaviours:

     1. Live registration countdown — writes ONLY to its own text node every
        second (never re-renders the tree; the handoff "Lessons" regression).
     2. Hero state rotation — optional subtle fade between the server-provided
        CTA variants (hero_ctx.rotation_items). Static markup always works
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
        var m = Math.floor((diff % 3600) / 60);
        var s = diff % 60;
        el.textContent = pad(h) + ':' + pad(m) + ':' + pad(s);
      }
    }

    tick();
    setInterval(tick, 1000);
  }

  /* ── 2. Hero state rotation ─────────────────────────────────────────────
     Each rotation item may carry: subcopy, primary_label/url, secondary_label/url.
     Primary CTA stays stable for critical states (the resolver only supplies
     rotation_items where rotating is safe). */
  function initHeroRotation() {
    var subEl = document.getElementById('heroSub');
    var dataEl = document.getElementById('heroRotationItems');
    var primaryBtn = document.getElementById('heroPrimaryBtn');
    var secondaryBtn = document.getElementById('heroSecondaryBtn');
    if (!subEl || !dataEl) return;

    var items;
    try { items = JSON.parse(dataEl.textContent); } catch (e) { return; }
    if (!Array.isArray(items) || items.length < 2) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var idx = 0;
    var paused = false;
    var DUR = 380;

    var heroEl = subEl.closest('[data-section="hero"]');
    if (heroEl) {
      heroEl.addEventListener('mouseenter', function () { paused = true; }, { passive: true });
      heroEl.addEventListener('mouseleave', function () { paused = false; }, { passive: true });
      heroEl.addEventListener('focusin', function () { paused = true; }, { passive: true });
      heroEl.addEventListener('focusout', function () { paused = false; }, { passive: true });
    }

    function applyItem(item) {
      if (item.subcopy) subEl.textContent = item.subcopy;
      if (primaryBtn && item.primary_label) {
        var span = primaryBtn.querySelector('span');
        if (span) span.textContent = item.primary_label;
        if (item.primary_url) primaryBtn.setAttribute('href', item.primary_url);
      }
      if (secondaryBtn && item.secondary_label) {
        var sspan = secondaryBtn.querySelector('span');
        if (sspan) sspan.textContent = item.secondary_label;
        else secondaryBtn.textContent = item.secondary_label;
        if (item.secondary_url) secondaryBtn.setAttribute('href', item.secondary_url);
      }
    }

    function fadeEls(els, out) {
      els.forEach(function (el) {
        el.style.transition = 'opacity ' + DUR + 'ms ease, transform ' + DUR + 'ms ease';
        el.style.opacity = out ? '0' : '1';
        el.style.transform = out ? 'translateY(5px)' : 'translateY(0)';
      });
    }

    function rotate() {
      if (paused) return;
      idx = (idx + 1) % items.length;
      var next = items[idx];
      var els = [subEl];
      if (primaryBtn && next.primary_label) els.push(primaryBtn);
      if (secondaryBtn && next.secondary_label) els.push(secondaryBtn);

      fadeEls(els, true);
      setTimeout(function () {
        applyItem(next);
        fadeEls(els, false);
      }, DUR);
    }

    setInterval(rotate, 9000);
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
    initHeroRotation();
    initTournamentFilters();
  }

  if (document.readyState !== 'loading') {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }
}());
