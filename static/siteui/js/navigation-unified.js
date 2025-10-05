/**
 * UNIFIED NAVIGATION SYSTEM
 * Handles mobile drawer menu interactions
 */

(function() {
  'use strict';

  // Mobile menu elements
  const menuToggle = document.querySelector('[data-mobile-menu-toggle]');
  const menuClose = document.querySelector('[data-mobile-menu-close]');
  const drawer = document.querySelector('[data-mobile-drawer]');
  const backdrop = document.querySelector('[data-mobile-backdrop]');

  if (!menuToggle || !drawer || !backdrop) {
    return; // Exit if elements don't exist
  }

  /**
   * Open the mobile drawer menu
   */
  function openMenu() {
    drawer.classList.add('is-open');
    backdrop.classList.add('is-visible');
    document.body.style.overflow = 'hidden';
    
    // Update ARIA
    if (menuToggle) {
      menuToggle.setAttribute('aria-expanded', 'true');
      menuToggle.setAttribute('aria-label', 'Close menu');
    }
  }

  /**
   * Close the mobile drawer menu
   */
  function closeMenu() {
    drawer.classList.remove('is-open');
    backdrop.classList.remove('is-visible');
    document.body.style.overflow = '';
    
    // Update ARIA
    if (menuToggle) {
      menuToggle.setAttribute('aria-expanded', 'false');
      menuToggle.setAttribute('aria-label', 'Open menu');
    }
  }

  /**
   * Toggle menu open/closed
   */
  function toggleMenu() {
    if (drawer.classList.contains('is-open')) {
      closeMenu();
    } else {
      openMenu();
    }
  }

  // Event listeners
  if (menuToggle) {
    menuToggle.addEventListener('click', toggleMenu);
  }

  if (menuClose) {
    menuClose.addEventListener('click', closeMenu);
  }

  if (backdrop) {
    backdrop.addEventListener('click', closeMenu);
  }

  // Close menu on escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && drawer.classList.contains('is-open')) {
      closeMenu();
    }
  });

  // Close menu when navigation link is clicked (optional UX improvement)
  const drawerLinks = drawer.querySelectorAll('a');
  drawerLinks.forEach(function(link) {
    link.addEventListener('click', function() {
      // Small delay to allow navigation to start
      setTimeout(closeMenu, 150);
    });
  });

  // Handle window resize - close menu if switching to desktop
  let resizeTimer;
  window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
      if (window.innerWidth >= 1024 && drawer.classList.contains('is-open')) {
        closeMenu();
      }
    }, 250);
  });

})();
