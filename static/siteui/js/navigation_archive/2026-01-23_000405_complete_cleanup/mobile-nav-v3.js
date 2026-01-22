/**
 * =========================================================================
 * MODERN ICON-BASED MOBILE NAVIGATION V3 - JavaScript Controller
 * =========================================================================
 * 
 * Features:
 * - Hamburger menu toggle for drawer
 * - Smooth slide-in/out animations
 * - Body scroll locking when drawer is open
 * - Touch gesture support (swipe right to close)
 * - Keyboard navigation (Escape to close, Tab trap)
 * - Theme toggle synchronization
 * - Focus management
 * - Auto-hide bottom nav on scroll down (optional)
 * - Screen reader announcements
 * 
 * Author: GitHub Copilot
 * Date: October 5, 2025
 * =========================================================================
 */

(function() {
  'use strict';

  // =========================================================================
  // ELEMENT SELECTORS
  // =========================================================================

  const hamburgerBtn = document.querySelector('[data-mobile-menu-toggle]');
  const closeBtn = document.querySelector('[data-mobile-menu-close]');
  const backdrop = document.getElementById('mobileMenuBackdrop');
  const drawer = document.getElementById('mobileMenuDrawer');
  const bottomNav = document.getElementById('mobileBottomNav');
  const headerBar = document.getElementById('mobileHeaderBar');
  const body = document.body;

  // Early exit if elements don't exist
  if (!hamburgerBtn || !drawer || !backdrop) {
    console.warn('Mobile nav V3: Required elements not found');
    return;
  }

  // =========================================================================
  // STATE MANAGEMENT
  // =========================================================================

  let isDrawerOpen = false;
  let lastScrollY = window.scrollY;
  let scrollTimeout = null;
  let touchStartX = 0;
  let touchStartY = 0;
  let touchEndX = 0;
  let touchEndY = 0;

  // =========================================================================
  // DRAWER FUNCTIONS
  // =========================================================================

  /**
   * Open the menu drawer
   */
  function openDrawer() {
    if (isDrawerOpen) return;

    isDrawerOpen = true;

    // Update ARIA attributes
    drawer.setAttribute('aria-hidden', 'false');
    hamburgerBtn.setAttribute('aria-expanded', 'true');

    // Add active classes
    backdrop.classList.add('active');
    drawer.classList.add('active');

    // Lock body scroll
    lockBodyScroll();

    // Focus first focusable element in drawer
    setTimeout(() => {
      const firstFocusable = drawer.querySelector('button, a, input, [tabindex]:not([tabindex="-1"])');
      if (firstFocusable) {
        firstFocusable.focus();
      }
    }, 400);

    // Announce to screen readers
    announceToScreenReader('Menu opened');
  }

  /**
   * Close the menu drawer
   */
  function closeDrawer() {
    if (!isDrawerOpen) return;

    isDrawerOpen = false;

    // Update ARIA attributes
    drawer.setAttribute('aria-hidden', 'true');
    hamburgerBtn.setAttribute('aria-expanded', 'false');

    // Remove active classes
    backdrop.classList.remove('active');
    drawer.classList.remove('active');

    // Unlock body scroll
    unlockBodyScroll();

    // Return focus to hamburger button
    setTimeout(() => {
      hamburgerBtn.focus();
    }, 100);

    // Announce to screen readers
    announceToScreenReader('Menu closed');
  }

  /**
   * Toggle drawer state
   */
  function toggleDrawer() {
    if (isDrawerOpen) {
      closeDrawer();
    } else {
      openDrawer();
    }
  }

  // =========================================================================
  // SCROLL MANAGEMENT
  // =========================================================================

  /**
   * Lock body scroll when drawer is open
   */
  function lockBodyScroll() {
    // Store current scroll position
    body.dataset.scrollY = window.scrollY.toString();
    
    // Add overflow hidden
    body.style.overflow = 'hidden';
    body.style.position = 'fixed';
    body.style.top = `-${window.scrollY}px`;
    body.style.width = '100%';
  }

  /**
   * Unlock body scroll when drawer closes
   */
  function unlockBodyScroll() {
    const scrollY = parseInt(body.dataset.scrollY || '0', 10);

    // Remove overflow styles
    body.style.overflow = '';
    body.style.position = '';
    body.style.top = '';
    body.style.width = '';

    // Restore scroll position
    window.scrollTo(0, scrollY);
  }

  /**
   * Handle scroll to hide/show bottom nav (optional)
   * Uncomment to enable auto-hide on scroll down
   */
  function handleScroll() {
    // Skip if drawer is open
    if (isDrawerOpen) return;

    const currentScrollY = window.scrollY;

    // Clear existing timeout
    if (scrollTimeout) {
      clearTimeout(scrollTimeout);
    }

    // Debounce scroll handling
    scrollTimeout = setTimeout(() => {
      // Add scrolled class to header when scrolled down
      if (currentScrollY > 50) {
        if (headerBar) {
          headerBar.classList.add('scrolled');
        }
      } else {
        if (headerBar) {
          headerBar.classList.remove('scrolled');
        }
      }

      // Optional: Hide bottom nav on scroll down, show on scroll up
      // Uncomment lines below to enable this feature
      /*
      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        // Scrolling down - hide bottom nav
        if (bottomNav) {
          bottomNav.classList.add('hidden');
        }
      } else {
        // Scrolling up - show bottom nav
        if (bottomNav) {
          bottomNav.classList.remove('hidden');
        }
      }
      */

      lastScrollY = currentScrollY;
    }, 100);
  }

  // =========================================================================
  // TOUCH GESTURES
  // =========================================================================

  /**
   * Handle touch start
   */
  function handleTouchStart(e) {
    if (!isDrawerOpen) return;

    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }

  /**
   * Handle touch end - detect swipe right to close
   */
  function handleTouchEnd(e) {
    if (!isDrawerOpen) return;

    touchEndX = e.changedTouches[0].clientX;
    touchEndY = e.changedTouches[0].clientY;

    handleSwipeGesture();
  }

  /**
   * Process swipe gesture
   */
  function handleSwipeGesture() {
    const swipeDistanceX = touchEndX - touchStartX;
    const swipeDistanceY = Math.abs(touchEndY - touchStartY);

    // Swipe right to close (must be horizontal swipe > 100px)
    if (swipeDistanceX > 100 && swipeDistanceY < 50) {
      closeDrawer();
    }
  }

  // =========================================================================
  // KEYBOARD NAVIGATION
  // =========================================================================

  /**
   * Handle keyboard navigation
   */
  function handleKeyboardNavigation(e) {
    if (!isDrawerOpen) return;

    // Escape key closes drawer
    if (e.key === 'Escape' || e.keyCode === 27) {
      e.preventDefault();
      closeDrawer();
      return;
    }

    // Tab key - trap focus within drawer
    if (e.key === 'Tab' || e.keyCode === 9) {
      handleTabKeyPress(e);
    }
  }

  /**
   * Trap Tab key within drawer
   */
  function handleTabKeyPress(e) {
    const focusableElements = drawer.querySelectorAll(
      'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );

    const focusableArray = Array.from(focusableElements);
    const firstFocusable = focusableArray[0];
    const lastFocusable = focusableArray[focusableArray.length - 1];

    // Shift + Tab on first element - focus last
    if (e.shiftKey && document.activeElement === firstFocusable) {
      e.preventDefault();
      lastFocusable.focus();
    }
    // Tab on last element - focus first
    else if (!e.shiftKey && document.activeElement === lastFocusable) {
      e.preventDefault();
      firstFocusable.focus();
    }
  }

  // =========================================================================
  // THEME TOGGLE SYNCHRONIZATION
  // =========================================================================

  /**
   * Synchronize all theme toggles across the site
   */
  function syncThemeToggles() {
    const themeToggles = document.querySelectorAll('[data-theme-toggle]');
    const isDark = body.getAttribute('data-bs-theme') === 'dark' || body.classList.contains('dark-theme');

    themeToggles.forEach(toggle => {
      toggle.checked = isDark;
    });
  }

  /**
   * Handle theme toggle change
   */
  function handleThemeToggle(e) {
    const isChecked = e.target.checked;
    const theme = isChecked ? 'dark' : 'light';

    // Update body attribute
    body.setAttribute('data-bs-theme', theme);

    // Update body class (for backward compatibility)
    if (isChecked) {
      body.classList.add('dark-theme');
    } else {
      body.classList.remove('dark-theme');
    }

    // Save to localStorage
    try {
      localStorage.setItem('theme', theme);
    } catch (err) {
      console.warn('Mobile nav V3: Could not save theme to localStorage', err);
    }

    // Sync all theme toggles
    syncThemeToggles();

    // Announce to screen readers
    announceToScreenReader(`${theme} mode activated`);

    // Dispatch custom event for other scripts
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
  }

  // =========================================================================
  // ACCESSIBILITY
  // =========================================================================

  /**
   * Announce message to screen readers
   */
  function announceToScreenReader(message) {
    // Create or get announcement element
    let announcer = document.getElementById('mobile-nav-announcer');
    
    if (!announcer) {
      announcer = document.createElement('div');
      announcer.id = 'mobile-nav-announcer';
      announcer.setAttribute('role', 'status');
      announcer.setAttribute('aria-live', 'polite');
      announcer.setAttribute('aria-atomic', 'true');
      announcer.style.position = 'absolute';
      announcer.style.left = '-10000px';
      announcer.style.width = '1px';
      announcer.style.height = '1px';
      announcer.style.overflow = 'hidden';
      body.appendChild(announcer);
    }

    // Clear and set new message
    announcer.textContent = '';
    setTimeout(() => {
      announcer.textContent = message;
    }, 100);
  }

  // =========================================================================
  // ACTIVE LINK HIGHLIGHTING
  // =========================================================================

  /**
   * Highlight active navigation link based on current URL
   */
  function updateActiveLinks() {
    const currentPath = window.location.pathname;
    const navItems = bottomNav ? bottomNav.querySelectorAll('.mobile-bottom-nav__item') : [];

    navItems.forEach(item => {
      const href = item.getAttribute('href');
      
      if (href === currentPath || (href !== '/' && currentPath.startsWith(href))) {
        item.classList.add('mobile-bottom-nav__item--active');
        item.setAttribute('aria-current', 'page');
      } else {
        item.classList.remove('mobile-bottom-nav__item--active');
        item.removeAttribute('aria-current');
      }
    });
  }

  // =========================================================================
  // INITIALIZATION
  // =========================================================================

  /**
   * Initialize mobile navigation
   */
  function init() {
    dcLog('Mobile nav V3: Initializing...');

    // Event Listeners - Drawer Controls
    if (hamburgerBtn) {
      hamburgerBtn.addEventListener('click', toggleDrawer);
    }

    if (closeBtn) {
      closeBtn.addEventListener('click', closeDrawer);
    }

    if (backdrop) {
      backdrop.addEventListener('click', closeDrawer);
    }

    // Event Listeners - Touch Gestures
    if (drawer) {
      drawer.addEventListener('touchstart', handleTouchStart, { passive: true });
      drawer.addEventListener('touchend', handleTouchEnd, { passive: true });
    }

    // Event Listeners - Keyboard Navigation
    document.addEventListener('keydown', handleKeyboardNavigation);

    // Event Listeners - Scroll (optional auto-hide)
    window.addEventListener('scroll', handleScroll, { passive: true });

    // Event Listeners - Theme Toggle
    const themeToggles = document.querySelectorAll('[data-theme-toggle]');
    themeToggles.forEach(toggle => {
      toggle.addEventListener('change', handleThemeToggle);
    });

    // Initialize theme on page load
    syncThemeToggles();

    // Update active links
    updateActiveLinks();

    // Listen for custom navigation events
    window.addEventListener('popstate', updateActiveLinks);

    dcLog('Mobile nav V3: Initialized successfully');
  }

  // =========================================================================
  // AUTO-INITIALIZE ON DOM READY
  // =========================================================================

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // =========================================================================
  // PUBLIC API
  // =========================================================================

  window.MobileNavV3 = {
    open: openDrawer,
    close: closeDrawer,
    toggle: toggleDrawer,
    isOpen: () => isDrawerOpen,
    updateActiveLinks: updateActiveLinks,
    version: '3.0.0'
  };

  dcLog('Mobile nav V3: Module loaded (v3.0.0)');

})();
