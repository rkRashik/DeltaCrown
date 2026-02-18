/**
 * DeltaCrown Tournament JS — Phase 4 Frontend Rebuild
 *
 * Handles:
 *  1. Hero carousel auto-slide
 *  2. Tab switching (detail page)
 *  3. Game filter sidebar toggle (mobile)
 *  4. Lucide icon re-init after HTMX swaps
 */

(function () {
  'use strict';

  /* ── 1. Hero Carousel ── */
  function initCarousel() {
    const slides = document.querySelectorAll('.hero-slide');
    const dots = document.querySelectorAll('.carousel-dot');
    if (!slides.length) return;

    let current = 0;
    const total = slides.length;

    function goTo(idx) {
      slides.forEach(s => s.classList.remove('active'));
      dots.forEach(d => d.classList.remove('bg-white', 'w-6'));
      dots.forEach(d => d.classList.add('bg-white/30'));

      current = ((idx % total) + total) % total;
      slides[current].classList.add('active');
      if (dots[current]) {
        dots[current].classList.remove('bg-white/30');
        dots[current].classList.add('bg-white', 'w-6');
      }
    }

    // Auto-advance every 6s
    let timer = setInterval(() => goTo(current + 1), 6000);

    // Manual dot clicks
    dots.forEach((dot, i) => {
      dot.addEventListener('click', () => {
        clearInterval(timer);
        goTo(i);
        timer = setInterval(() => goTo(current + 1), 6000);
      });
    });

    // Prev / Next buttons
    const prevBtn = document.getElementById('carousel-prev');
    const nextBtn = document.getElementById('carousel-next');
    if (prevBtn) prevBtn.addEventListener('click', () => { clearInterval(timer); goTo(current - 1); timer = setInterval(() => goTo(current + 1), 6000); });
    if (nextBtn) nextBtn.addEventListener('click', () => { clearInterval(timer); goTo(current + 1); timer = setInterval(() => goTo(current + 1), 6000); });

    goTo(0);
  }

  /* ── 2. Tab Switching ── */
  function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn[data-tab]');
    const tabPanels = document.querySelectorAll('.tab-panel[data-tab]');
    if (!tabBtns.length) return;

    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.tab;

        tabBtns.forEach(b => {
          b.classList.remove('active');
          b.setAttribute('aria-selected', 'false');
        });
        tabPanels.forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
        const panel = document.querySelector(`.tab-panel[data-tab="${target}"]`);
        if (panel) panel.classList.add('active');

        // Re-init lucide for any newly-visible icons
        if (typeof lucide !== 'undefined') lucide.createIcons();
      });
    });
  }

  /* ── 3. Mobile Filter Toggle ── */
  function initFilterToggle() {
    const toggleBtn = document.getElementById('filter-toggle');
    const sidebar = document.getElementById('filter-sidebar');
    if (!toggleBtn || !sidebar) return;

    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('hidden');
      sidebar.classList.toggle('fixed');
      sidebar.classList.toggle('inset-0');
      sidebar.classList.toggle('z-50');
    });

    // Close on overlay click
    const overlay = sidebar.querySelector('.filter-overlay');
    if (overlay) {
      overlay.addEventListener('click', () => {
        sidebar.classList.add('hidden');
        sidebar.classList.remove('fixed', 'inset-0', 'z-50');
      });
    }
  }

  /* ── 4. Game Filter Nav Pills ── */
  function initGameFilter() {
    const pills = document.querySelectorAll('.game-filter-pill');
    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        const game = pill.dataset.game || '';
        const url = new URL(window.location);
        if (game) {
          url.searchParams.set('game', game);
        } else {
          url.searchParams.delete('game');
        }
        url.searchParams.delete('page');
        window.location.href = url.toString();
      });
    });
  }

  /* ── Init on DOM ready ── */
  document.addEventListener('DOMContentLoaded', () => {
    initCarousel();
    initTabs();
    initFilterToggle();
    initGameFilter();
  });

  // Re-init Lucide after any HTMX swap
  document.addEventListener('htmx:afterSwap', () => {
    if (typeof lucide !== 'undefined') lucide.createIcons();
  });
})();
