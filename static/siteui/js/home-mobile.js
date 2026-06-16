/* ============================================================================
   DeltaCrown Mobile Homepage runtime.
   Owns two isolated behaviours:
     1. Tournament bottom sheet — open/close, populate from data-* attrs.
     2. Live countdown — same as desktop, isolated to .dc-home-m nodes.
   ============================================================================ */
(function () {
  'use strict';

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  /* ── 1. Bottom sheet ──────────────────────────────────────────────────── */
  function initMobileSheet() {
    var root = document.querySelector('.dc-home-m');
    if (!root) return;
    var scrim = root.querySelector('.m-sheet-scrim');
    var sheet = root.querySelector('.m-sheet');
    var closeBtn = root.querySelector('.m-sheet-close');
    var cards = Array.prototype.slice.call(root.querySelectorAll('.m-tcard'));
    if (!sheet || !scrim) return;

    var sTitle  = document.getElementById('mSheetTitle');
    var sGame   = document.getElementById('mSheetGame');
    var sPrize  = document.getElementById('mSheetPrize');
    var sFormat = document.getElementById('mSheetFormat');
    var sBar    = document.getElementById('mSheetBar');
    var sSlots  = document.getElementById('mSheetSlots');
    var sPoster = document.getElementById('mSheetPoster');
    var sUrl    = document.getElementById('mSheetUrl');
    var sClock  = document.getElementById('mSheetClock');

    function populate(card) {
      var d = card.dataset;
      if (sTitle)  sTitle.textContent  = d.tName   || '';
      if (sGame)   sGame.textContent   = d.tGame   || '';
      if (sPrize)  sPrize.textContent  = d.tPrize  || '';
      if (sFormat) sFormat.textContent = d.tFormat || '';
      if (sBar)    sBar.style.width    = (d.tPct || '0') + '%';
      if (sSlots)  sSlots.textContent  = d.tSlots  || '';
      if (sPoster) sPoster.style.backgroundImage = d.tPoster ? "url('" + d.tPoster + "')" : '';
      if (sUrl)    sUrl.href = d.tUrl || '#';
      if (sClock) {
        sClock.textContent = '';
        if (d.tCountdown) { sClock.setAttribute('data-countdown', d.tCountdown); }
        else { sClock.removeAttribute('data-countdown'); sClock.textContent = '—'; }
      }
    }

    function open(card) {
      populate(card);
      root.classList.add('m-sheet-open');
      document.body.style.overflow = 'hidden';
      sheet.scrollTop = 0;
    }

    function close() {
      root.classList.remove('m-sheet-open');
      document.body.style.overflow = '';
    }

    cards.forEach(function (c) { c.addEventListener('click', function () { open(c); }); });
    if (closeBtn) closeBtn.addEventListener('click', close);
    scrim.addEventListener('click', close);
  }

  /* ── 2. Live countdown (isolated to mobile tree) ─────────────────────── */
  function initMobileCountdowns() {
    var root = document.querySelector('.dc-home-m');
    if (!root) return;

    function tick() {
      var now = Date.now();
      var els = root.querySelectorAll('[data-countdown]');
      for (var i = 0; i < els.length; i++) {
        var el = els[i];
        var iso = el.getAttribute('data-countdown');
        var target = iso ? Date.parse(iso) : NaN;
        if (isNaN(target)) continue;
        var diff = Math.floor((target - now) / 1000);
        if (diff <= 0) { el.textContent = 'Closed'; el.removeAttribute('data-countdown'); continue; }
        var h = Math.floor(diff / 3600);
        var m = Math.floor((diff % 3600) / 60);
        var s = diff % 60;
        el.textContent = pad(h) + ':' + pad(m) + ':' + pad(s);
      }
    }

    tick();
    setInterval(tick, 1000);
  }

  function init() {
    /* Only run if the mobile tree is currently active (visible) */
    var root = document.querySelector('.dc-home-m');
    if (!root || root.offsetParent === null) return;
    initMobileSheet();
    initMobileCountdowns();
  }

  if (document.readyState !== 'loading') { init(); }
  else { document.addEventListener('DOMContentLoaded', init); }
}());
