/**
 * Tournament Detail Page — Extracted JavaScript
 * Shared JS for _base_detail.html and all phase templates.
 * Toast notifications, countdown timer, lucide init.
 */

(function () {
  'use strict';

  /* ==========================================================
     TOAST NOTIFICATION
     Uses the #dc-toast / #dc-toast-msg elements in the template.
     ========================================================== */
  window.showToast = function (msg, duration) {
    duration = duration || 2500;
    var el = document.getElementById('dc-toast');
    var msgEl = document.getElementById('dc-toast-msg');
    if (!el || !msgEl) return;
    msgEl.textContent = msg;
    el.classList.add('show');
    setTimeout(function () { el.classList.remove('show'); }, duration);
  };

  /* ==========================================================
     COUNTDOWN TIMER
     ========================================================== */
  window.initCountdown = function (targetISO, containerId) {
    if (!targetISO) return;
    var target = new Date(targetISO).getTime();
    var container = document.getElementById(containerId);
    if (!container) return;

    function update() {
      var now = Date.now();
      var diff = target - now;
      if (diff <= 0) {
        container.innerHTML = '<span class="text-lg font-bold text-game-accent uppercase tracking-wider">Time\'s Up!</span>';
        return;
      }
      var d = Math.floor(diff / 86400000);
      var h = Math.floor((diff % 86400000) / 3600000);
      var m = Math.floor((diff % 3600000) / 60000);
      var s = Math.floor((diff % 60000) / 1000);

      container.innerHTML =
        '<div class="flex items-center gap-3 sm:gap-4">'
        + '<div class="text-center"><div class="countdown-digit">' + String(d).padStart(2, '0') + '</div><div class="countdown-label">Days</div></div>'
        + '<span class="text-2xl text-white/20 font-bold -mt-5">:</span>'
        + '<div class="text-center"><div class="countdown-digit">' + String(h).padStart(2, '0') + '</div><div class="countdown-label">Hours</div></div>'
        + '<span class="text-2xl text-white/20 font-bold -mt-5">:</span>'
        + '<div class="text-center"><div class="countdown-digit">' + String(m).padStart(2, '0') + '</div><div class="countdown-label">Mins</div></div>'
        + '<span class="text-2xl text-white/20 font-bold -mt-5">:</span>'
        + '<div class="text-center"><div class="countdown-digit">' + String(s).padStart(2, '0') + '</div><div class="countdown-label">Secs</div></div>'
        + '</div>';
    }
    update();
    setInterval(update, 1000);
  };

  /* ==========================================================
     DOMContentLoaded INIT
     ========================================================== */
  document.addEventListener('DOMContentLoaded', function () {
    if (typeof lucide !== 'undefined') lucide.createIcons();
  });
})();
