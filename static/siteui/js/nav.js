(function () {
  const nav = document.querySelector('[data-site-nav]');
  if (!nav) return;

  const notifBadge = nav.querySelector('[data-notif-badge]');
  const notifTrigger = nav.querySelector('.notif-trigger');
  
  // Modern Mobile Navigation Elements
  const mobileToggle = nav.querySelector('[data-open-drawer="main-drawer"]') || nav.querySelector('.mobile-nav-toggle');
  const mobileNav = document.getElementById('mobileNav');
  const mobileNavOverlay = document.getElementById('mobileNavOverlay');
  const mobileNavClose = document.querySelector('.mobile-nav-close');
  const mobileThemeToggle = document.getElementById('mobile-theme-toggle');
  
  // Legacy drawer support
  const mobileDrawer = document.getElementById('main-drawer');
  const mobileCloseButtons = mobileDrawer ? mobileDrawer.querySelectorAll('[data-close-drawer]') : [];
  
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* Sticky shrink on scroll */
  const toggleShrink = () => {
    const offset = window.scrollY || document.documentElement.scrollTop;
    if (offset > 24) {
      nav.classList.add('is-shrunk');
    } else {
      nav.classList.remove('is-shrunk');
    }
  };
  toggleShrink();
  window.addEventListener('scroll', () => {
    if (prefersReducedMotion.matches) {
      toggleShrink();
    } else {
      window.requestAnimationFrame(toggleShrink);
    }
  }, { passive: true });

  /* Notification badge auto-update */
  if (notifBadge && notifTrigger) {
    const setBadge = (count) => {
      const display = count > 0 ? String(count) : '3';
      notifBadge.textContent = display;
      notifBadge.toggleAttribute('data-has-unread', count > 0);
      notifTrigger.setAttribute('aria-label', count > 0 ? `Notifications (${count} unread)` : 'Notifications');
    };

    const updateCount = async () => {
      try {
        const response = await fetch('/notifications/unread_count/', { credentials: 'same-origin' });
        if (!response.ok) return;
        const data = await response.json();
        if (typeof data.count === 'number') {
          setBadge(data.count);
        }
      } catch (error) {
        // swallow silently
      }
    };

    setBadge(Number(notifBadge.textContent.trim()) || 0);
    updateCount();
    setInterval(updateCount, 60_000);
  }

  /* Dropdown helpers */
  const dropdowns = [];

  const getFocusable = (root) => Array.from(root.querySelectorAll('[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'))
    .filter((el) => !el.hasAttribute('disabled') && !el.getAttribute('aria-hidden'));

  const closeAllDropdowns = () => {
    dropdowns.forEach(({ button, menu }) => {
      menu.hidden = true;
      menu.removeAttribute('data-open');
      button.setAttribute('aria-expanded', 'false');
    });
  };

  const setupDropdown = (button, menu) => {
    if (!button || !menu) return;

    const open = () => {
      closeAllDropdowns();
      menu.hidden = false;
      menu.setAttribute('data-open', 'true');
      button.setAttribute('aria-expanded', 'true');
      const focusable = getFocusable(menu);
      if (focusable.length) {
        focusable[0].focus({ preventScroll: true });
      }
    };

    const close = ({ focusButton } = { focusButton: false }) => {
      menu.removeAttribute('data-open');
      button.setAttribute('aria-expanded', 'false');
      // Wait for animation to complete before hiding
      setTimeout(() => {
        menu.hidden = true;
      }, 300);
      if (focusButton) {
        button.focus({ preventScroll: true });
      }
    };

    button.addEventListener('click', (event) => {
      event.preventDefault();
      if (menu.hidden) {
        open();
      } else {
        close();
      }
    });

    button.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        open();
      }
    });

    menu.addEventListener('keydown', (event) => {
      const focusable = getFocusable(menu);
      const index = focusable.indexOf(document.activeElement);
      if (event.key === 'Escape') {
        event.preventDefault();
        close({ focusButton: true });
        return;
      }
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        (focusable[index + 1] || focusable[0])?.focus();
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        (focusable[index - 1] || focusable[focusable.length - 1])?.focus();
      }
      if (event.key === 'Tab') {
        setTimeout(() => {
          if (!menu.contains(document.activeElement)) {
            close();
          }
        }, 0);
      }
    });

    document.addEventListener('click', (event) => {
      if (!menu.contains(event.target) && !button.contains(event.target)) {
        close();
      }
    });

    window.addEventListener('resize', () => close(), { passive: true });
    window.addEventListener('scroll', () => close(), { passive: true });

    dropdowns.push({ button, menu, close });
  };

  document.querySelectorAll('[data-menu-toggle]').forEach((btn) => {
    const menuId = btn.getAttribute('aria-controls');
    const menu = menuId ? document.getElementById(menuId) : null;
    if (menu) setupDropdown(btn, menu);
  });

  document.querySelectorAll('[data-avatar-toggle]').forEach((btn) => {
    const menuId = btn.getAttribute('aria-controls');
    const menu = menuId ? document.getElementById(menuId) : null;
    if (menu) setupDropdown(btn, menu);
  });

  /* Mobile drawer interactions */
  if (mobileToggle && (mobileDrawer || (mobileNav && mobileNavOverlay))) {
    let previouslyFocused = null;

    const focusableInDrawer = () => getFocusable(mobileDrawer.querySelector('.mobile-drawer__panel'));

    const openDrawer = () => {
      if (!mobileDrawer) return;
      previouslyFocused = document.activeElement;
      mobileDrawer.hidden = false;
      mobileDrawer.setAttribute('data-open', 'true');
      document.body.classList.add('has-mobile-drawer-open');
      const focusables = focusableInDrawer();
      (focusables[0] || mobileDrawer).focus({ preventScroll: true });
    };

    const closeDrawer = ({ returnFocus } = { returnFocus: true }) => {
      if (!mobileDrawer) return;
      mobileDrawer.removeAttribute('data-open');
      document.body.classList.remove('has-mobile-drawer-open');
      setTimeout(() => {
        mobileDrawer.hidden = true;
      }, prefersReducedMotion.matches ? 0 : 200);
      if (returnFocus && previouslyFocused) {
        previouslyFocused.focus({ preventScroll: true });
      }
    };

    mobileToggle.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      
      // Check if we have modern mobile nav
      if (mobileNav && mobileNavOverlay) {
        openModernMobileNav();
      } else if (mobileDrawer) {
        openDrawer();
        mobileToggle.setAttribute('aria-expanded', 'true');
      }
    });

    // Add touch support for better mobile interaction
    mobileToggle.addEventListener('touchend', (event) => {
      event.preventDefault();
      event.stopPropagation();
      
      if (mobileNav && mobileNavOverlay) {
        if (!mobileNav.classList.contains('active')) {
          openModernMobileNav();
        }
      } else if (mobileDrawer && mobileDrawer.hidden) {
        openDrawer();
        mobileToggle.setAttribute('aria-expanded', 'true');
      }
    });

    // Modern Mobile Navigation Handlers
    if (mobileNavClose) {
      mobileNavClose.addEventListener('click', closeModernMobileNav);
    }

    if (mobileNavOverlay) {
      mobileNavOverlay.addEventListener('click', closeModernMobileNav);
    }

    // Theme toggle for mobile nav
    if (mobileThemeToggle) {
      mobileThemeToggle.addEventListener('change', (event) => {
        const isDark = event.target.checked;
        document.documentElement.setAttribute('data-bs-theme', isDark ? 'dark' : 'light');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
      });
      
      // Initialize theme toggle state
      const currentTheme = localStorage.getItem('theme') || 'light';
      mobileThemeToggle.checked = currentTheme === 'dark';
    }

    // Legacy drawer handlers
    mobileCloseButtons.forEach((btn) => {
      btn.addEventListener('click', (event) => {
        event.preventDefault();
        closeDrawer();
        mobileToggle.setAttribute('aria-expanded', 'false');
      });
    });

    if (mobileDrawer) {
      mobileDrawer.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
          event.preventDefault();
          closeDrawer();
          mobileToggle.setAttribute('aria-expanded', 'false');
        }
        if (event.key === 'Tab') {
          const focusables = focusableInDrawer();
          if (!focusables.length) return;
          const index = focusables.indexOf(document.activeElement);
          if (event.shiftKey && (index <= 0 || document.activeElement === mobileDrawer)) {
            event.preventDefault();
            focusables[focusables.length - 1].focus();
          } else if (!event.shiftKey && index === focusables.length - 1) {
            event.preventDefault();
            focusables[0].focus();
          }
        }
      });

      mobileDrawer.addEventListener('click', (event) => {
        if (event.target === mobileDrawer || event.target.classList.contains('mobile-drawer__overlay')) {
          closeDrawer();
          mobileToggle.setAttribute('aria-expanded', 'false');
        }
      });
    }

    if (mobileDrawer) {
      document.addEventListener('click', (event) => {
        if (!mobileDrawer.hidden && !mobileDrawer.contains(event.target) && event.target !== mobileToggle) {
          closeDrawer();
          mobileToggle.setAttribute('aria-expanded', 'false');
        }
      });
    }

    window.addEventListener('resize', () => {
      if (window.innerWidth >= 1024) {
        if (mobileNav && mobileNav.classList.contains('active')) {
          closeModernMobileNav({ returnFocus: false });
        }
        if (mobileDrawer && !mobileDrawer.hidden) {
          closeDrawer({ returnFocus: false });
          mobileToggle.setAttribute('aria-expanded', 'false');
        }
      }
    });
  }

  /* ========================================
     MODERN MOBILE NAVIGATION FUNCTIONS
     ======================================== */
  
  // Open modern mobile navigation
  function openModernMobileNav() {
    if (!mobileNav || !mobileNavOverlay) return;
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
    
    // Show overlay and navigation
    mobileNavOverlay.classList.add('active');
    mobileNav.classList.add('active');
    
    // Update toggle button state
    if (mobileToggle) {
      mobileToggle.setAttribute('aria-expanded', 'true');
      mobileToggle.classList.add('active');
    }
    
    // Focus first focusable element in nav
    const firstFocusable = mobileNav.querySelector('a, button, [tabindex]:not([tabindex="-1"])');
    if (firstFocusable && !prefersReducedMotion.matches) {
      setTimeout(() => firstFocusable.focus(), 300);
    }
    
    // Setup keyboard navigation
    setupMobileNavKeyboard();
  }
  
  // Close modern mobile navigation
  function closeModernMobileNav(options = {}) {
    if (!mobileNav || !mobileNavOverlay) return;
    
    // Restore body scroll
    document.body.style.overflow = '';
    
    // Hide overlay and navigation
    mobileNavOverlay.classList.remove('active');
    mobileNav.classList.remove('active');
    
    // Update toggle button state
    if (mobileToggle) {
      mobileToggle.setAttribute('aria-expanded', 'false');
      mobileToggle.classList.remove('active');
      
      // Return focus to toggle button unless specified otherwise
      if (options.returnFocus !== false && !prefersReducedMotion.matches) {
        setTimeout(() => mobileToggle.focus(), 100);
      }
    }
    
    // Clean up keyboard listeners
    cleanupMobileNavKeyboard();
  }
  
  // Setup keyboard navigation for mobile nav
  function setupMobileNavKeyboard() {
    if (!mobileNav) return;
    
    mobileNav.addEventListener('keydown', handleMobileNavKeydown);
    
    // Close on escape key anywhere
    document.addEventListener('keydown', handleDocumentKeydown);
  }
  
  // Cleanup keyboard navigation
  function cleanupMobileNavKeyboard() {
    if (!mobileNav) return;
    
    mobileNav.removeEventListener('keydown', handleMobileNavKeydown);
    document.removeEventListener('keydown', handleDocumentKeydown);
  }
  
  // Handle keyboard navigation within mobile nav
  function handleMobileNavKeydown(event) {
    if (event.key === 'Tab') {
      const focusableElements = mobileNav.querySelectorAll(
        'a:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      
      if (!focusableElements.length) return;
      
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      
      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }
  }
  
  // Handle escape key to close mobile nav
  function handleDocumentKeydown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      closeModernMobileNav();
    }
  }
  
  // Touch gesture support for mobile nav
  if (mobileNav) {
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;
    
    mobileNav.addEventListener('touchstart', (event) => {
      touchStartX = event.changedTouches[0].screenX;
      touchStartY = event.changedTouches[0].screenY;
    }, { passive: true });
    
    mobileNav.addEventListener('touchend', (event) => {
      touchEndX = event.changedTouches[0].screenX;
      touchEndY = event.changedTouches[0].screenY;
      
      // Calculate swipe distance and direction
      const swipeDistanceX = touchEndX - touchStartX;
      const swipeDistanceY = Math.abs(touchEndY - touchStartY);
      
      // Close nav on right swipe (swipe distance > 100px and mostly horizontal)
      if (swipeDistanceX > 100 && swipeDistanceY < 100) {
        closeModernMobileNav();
      }
    }, { passive: true });
  }
  
  // Initialize theme toggle synchronization
  function initializeThemeSync() {
    const desktopThemeToggle = document.querySelector('#theme-toggle');
    const mobileThemeToggle = document.querySelector('#mobile-theme-toggle');
    
    if (!desktopThemeToggle || !mobileThemeToggle) return;
    
    // Sync mobile toggle with desktop toggle
    const syncThemeToggles = () => {
      const currentTheme = localStorage.getItem('theme') || 'light';
      const isDark = currentTheme === 'dark';
      
      desktopThemeToggle.checked = isDark;
      mobileThemeToggle.checked = isDark;
    };
    
    // Listen for theme changes
    desktopThemeToggle.addEventListener('change', (event) => {
      const isDark = event.target.checked;
      mobileThemeToggle.checked = isDark;
    });
    
    // Initialize sync
    syncThemeToggles();
  }
  
  // Initialize theme synchronization
  initializeThemeSync();
  
  // Initialize mobile navigation
  function initializeMobileNavigation() {
    if (mobileToggle && mobileNav && mobileNavOverlay) {
      return true;
    }
    return false;
  }

  // Initialize mobile navigation
  const isMobileNavReady = initializeMobileNavigation();
})();
