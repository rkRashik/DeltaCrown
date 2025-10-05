/*
 * =========================================================================
 * MODERN RESPONSIVE MOBILE NAVIGATION V2 - JavaScript Controller
 * =========================================================================
 * 
 * Handles all interactions for the mobile navigation including:
 * - Opening/closing menu with smooth animations
 * - Keyboard navigation (Tab, Escape, Arrow keys)
 * - Touch gesture support (swipe to close)
 * - Focus management and accessibility
 * - Theme toggle synchronization
 * - Body scroll locking
 * - Performance optimizations
 * 
 * Author: GitHub Copilot
 * Date: October 5, 2025
 * =========================================================================
 */

(function() {
  'use strict';

  // Check if reduced motion is preferred
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  // DOM Elements
  const mobileToggle = document.querySelector('[data-open-drawer="main-drawer"]') || 
                        document.querySelector('.mobile-nav-toggle');
  const mobileNav = document.getElementById('mobileNavV2');
  const mobileBackdrop = document.getElementById('mobileNavBackdrop');
  const mobileClose = document.querySelector('[data-mobile-nav-close]');
  const mobileThemeToggle = document.getElementById('mobileThemeToggleV2');
  
  // Exit early if elements don't exist
  if (!mobileToggle || !mobileNav || !mobileBackdrop) {
    console.warn('Mobile navigation V2 elements not found');
    return;
  }

  // State management
  let isOpen = false;
  let previouslyFocused = null;
  let touchStartX = 0;
  let touchStartY = 0;
  let touchEndX = 0;
  let touchEndY = 0;

  /* =========================================================================
     CORE NAVIGATION FUNCTIONS
     ========================================================================= */

  /**
   * Opens the mobile navigation menu
   */
  function openMobileNav() {
    if (isOpen) return;
    
    // Store currently focused element
    previouslyFocused = document.activeElement;
    
    // Prevent body scroll
    document.body.classList.add('mobile-nav-open');
    document.body.style.overflow = 'hidden';
    
    // Show backdrop and navigation
    mobileBackdrop.classList.add('active');
    mobileBackdrop.setAttribute('aria-hidden', 'false');
    
    mobileNav.classList.add('active');
    mobileNav.setAttribute('aria-hidden', 'false');
    
    // Update toggle button state
    if (mobileToggle) {
      mobileToggle.setAttribute('aria-expanded', 'true');
      mobileToggle.classList.add('active');
    }
    
    // Set focus to first focusable element
    if (!prefersReducedMotion) {
      setTimeout(() => {
        const firstFocusable = getFirstFocusableElement();
        if (firstFocusable) {
          firstFocusable.focus();
        }
      }, 300); // Wait for animation to complete
    } else {
      const firstFocusable = getFirstFocusableElement();
      if (firstFocusable) {
        firstFocusable.focus();
      }
    }
    
    // Update state
    isOpen = true;
    
    // Announce to screen readers
    announceToScreenReader('Navigation menu opened');
  }

  /**
   * Closes the mobile navigation menu
   * @param {boolean} returnFocus - Whether to return focus to the toggle button
   */
  function closeMobileNav(returnFocus = true) {
    if (!isOpen) return;
    
    // Restore body scroll
    document.body.classList.remove('mobile-nav-open');
    document.body.style.overflow = '';
    
    // Hide backdrop and navigation
    mobileBackdrop.classList.remove('active');
    mobileBackdrop.setAttribute('aria-hidden', 'true');
    
    mobileNav.classList.remove('active');
    mobileNav.setAttribute('aria-hidden', 'true');
    
    // Update toggle button state
    if (mobileToggle) {
      mobileToggle.setAttribute('aria-expanded', 'false');
      mobileToggle.classList.remove('active');
    }
    
    // Return focus if requested
    if (returnFocus && previouslyFocused) {
      if (!prefersReducedMotion) {
        setTimeout(() => {
          previouslyFocused.focus();
        }, 100); // Small delay for better UX
      } else {
        previouslyFocused.focus();
      }
    }
    
    // Update state
    isOpen = false;
    
    // Announce to screen readers
    announceToScreenReader('Navigation menu closed');
  }

  /**
   * Toggles the mobile navigation menu
   */
  function toggleMobileNav() {
    if (isOpen) {
      closeMobileNav();
    } else {
      openMobileNav();
    }
  }

  /* =========================================================================
     EVENT LISTENERS
     ========================================================================= */

  // Toggle button click
  if (mobileToggle) {
    mobileToggle.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleMobileNav();
    });
    
    // Touch support for mobile toggle
    mobileToggle.addEventListener('touchend', (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (!isOpen) {
        openMobileNav();
      }
    });
  }

  // Close button click
  if (mobileClose) {
    mobileClose.addEventListener('click', (event) => {
      event.preventDefault();
      closeMobileNav();
    });
  }

  // Backdrop click
  if (mobileBackdrop) {
    mobileBackdrop.addEventListener('click', () => {
      closeMobileNav();
    });
  }

  // Close on Escape key
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isOpen) {
      event.preventDefault();
      closeMobileNav();
    }
  });

  // Handle keyboard navigation within the menu
  if (mobileNav) {
    mobileNav.addEventListener('keydown', handleKeyboardNavigation);
  }

  // Close menu when resizing to desktop
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      if (window.innerWidth >= 1024 && isOpen) {
        closeMobileNav(false);
      }
    }, 200);
  }, { passive: true });

  /* =========================================================================
     TOUCH GESTURE SUPPORT
     ========================================================================= */

  if (mobileNav) {
    // Track touch start
    mobileNav.addEventListener('touchstart', (event) => {
      touchStartX = event.changedTouches[0].screenX;
      touchStartY = event.changedTouches[0].screenY;
    }, { passive: true });
    
    // Track touch end and detect swipe
    mobileNav.addEventListener('touchend', (event) => {
      touchEndX = event.changedTouches[0].screenX;
      touchEndY = event.changedTouches[0].screenY;
      handleSwipeGesture();
    }, { passive: true });
  }

  /**
   * Handles swipe gestures to close the menu
   * Swipe left to close (swipe distance > 100px and mostly horizontal)
   */
  function handleSwipeGesture() {
    const swipeDistanceX = touchStartX - touchEndX; // Positive if swiping left
    const swipeDistanceY = Math.abs(touchEndY - touchStartY);
    
    // Close nav on left swipe (swipe distance > 100px and mostly horizontal)
    if (swipeDistanceX > 100 && swipeDistanceY < 100) {
      closeMobileNav();
    }
  }

  /* =========================================================================
     KEYBOARD NAVIGATION
     ========================================================================= */

  /**
   * Handles keyboard navigation within the mobile menu
   * @param {KeyboardEvent} event
   */
  function handleKeyboardNavigation(event) {
    const focusableElements = getFocusableElements();
    if (!focusableElements.length) return;
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    const currentIndex = focusableElements.indexOf(document.activeElement);
    
    switch (event.key) {
      case 'Tab':
        // Trap focus within menu
        if (event.shiftKey) {
          // Shift + Tab - move backwards
          if (document.activeElement === firstElement) {
            event.preventDefault();
            lastElement.focus();
          }
        } else {
          // Tab - move forwards
          if (document.activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
          }
        }
        break;
        
      case 'ArrowDown':
        // Move to next focusable element
        event.preventDefault();
        if (currentIndex < focusableElements.length - 1) {
          focusableElements[currentIndex + 1].focus();
        } else {
          firstElement.focus();
        }
        break;
        
      case 'ArrowUp':
        // Move to previous focusable element
        event.preventDefault();
        if (currentIndex > 0) {
          focusableElements[currentIndex - 1].focus();
        } else {
          lastElement.focus();
        }
        break;
        
      case 'Home':
        // Move to first focusable element
        event.preventDefault();
        firstElement.focus();
        break;
        
      case 'End':
        // Move to last focusable element
        event.preventDefault();
        lastElement.focus();
        break;
    }
  }

  /**
   * Gets all focusable elements within the mobile nav
   * @returns {Array<HTMLElement>}
   */
  function getFocusableElements() {
    if (!mobileNav) return [];
    
    const focusableSelectors = [
      'a[href]:not([disabled]):not([tabindex="-1"])',
      'button:not([disabled]):not([tabindex="-1"])',
      'input:not([disabled]):not([tabindex="-1"])',
      'select:not([disabled]):not([tabindex="-1"])',
      'textarea:not([disabled]):not([tabindex="-1"])',
      '[tabindex]:not([tabindex="-1"]):not([disabled])'
    ].join(', ');
    
    return Array.from(mobileNav.querySelectorAll(focusableSelectors))
      .filter(element => {
        // Additional checks to ensure element is actually focusable
        return element.offsetParent !== null && 
               !element.hasAttribute('aria-hidden') && 
               getComputedStyle(element).visibility !== 'hidden';
      });
  }

  /**
   * Gets the first focusable element in the mobile nav
   * @returns {HTMLElement|null}
   */
  function getFirstFocusableElement() {
    const focusableElements = getFocusableElements();
    return focusableElements.length > 0 ? focusableElements[0] : null;
  }

  /* =========================================================================
     THEME TOGGLE SYNCHRONIZATION
     ========================================================================= */

  if (mobileThemeToggle) {
    // Initialize theme toggle state
    const currentTheme = localStorage.getItem('theme') || 'light';
    mobileThemeToggle.checked = currentTheme === 'dark';
    
    // Listen for theme changes
    mobileThemeToggle.addEventListener('change', (event) => {
      const isDark = event.target.checked;
      const newTheme = isDark ? 'dark' : 'light';
      
      // Update theme
      document.documentElement.setAttribute('data-bs-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      
      // Sync with desktop theme toggle
      const desktopThemeToggle = document.querySelector('#theme-toggle');
      if (desktopThemeToggle) {
        desktopThemeToggle.checked = isDark;
      }
      
      // Sync with profile theme toggle
      const profileThemeToggle = document.querySelector('#profile-theme-toggle');
      if (profileThemeToggle) {
        profileThemeToggle.checked = isDark;
      }
      
      // Announce theme change
      announceToScreenReader(`Theme changed to ${newTheme} mode`);
    });
    
    // Listen for theme changes from other toggles
    window.addEventListener('storage', (event) => {
      if (event.key === 'theme') {
        mobileThemeToggle.checked = event.newValue === 'dark';
      }
    });
  }

  /* =========================================================================
     NAVIGATION LINK ACTIVE STATE
     ========================================================================= */

  /**
   * Updates active link based on current URL
   */
  function updateActiveLink() {
    if (!mobileNav) return;
    
    const currentPath = window.location.pathname;
    const navLinks = mobileNav.querySelectorAll('.mobile-nav-v2__link');
    
    navLinks.forEach(link => {
      const linkPath = link.getAttribute('href');
      if (linkPath && currentPath.startsWith(linkPath) && linkPath !== '/') {
        link.classList.add('mobile-nav-v2__link--active');
        link.setAttribute('aria-current', 'page');
      } else if (linkPath === '/' && currentPath === '/') {
        link.classList.add('mobile-nav-v2__link--active');
        link.setAttribute('aria-current', 'page');
      } else {
        link.classList.remove('mobile-nav-v2__link--active');
        link.removeAttribute('aria-current');
      }
    });
  }

  // Update active link on page load
  updateActiveLink();

  // Update active link when using browser back/forward
  window.addEventListener('popstate', updateActiveLink);

  /* =========================================================================
     ACCESSIBILITY UTILITIES
     ========================================================================= */

  /**
   * Announces a message to screen readers
   * @param {string} message - The message to announce
   */
  function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    // Remove after announcement
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }

  /* =========================================================================
     PERFORMANCE OPTIMIZATIONS
     ========================================================================= */

  /**
   * Lazy load images in the mobile nav
   */
  function lazyLoadImages() {
    if ('IntersectionObserver' in window) {
      const images = mobileNav.querySelectorAll('img[loading="lazy"]');
      
      const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            if (img.dataset.src) {
              img.src = img.dataset.src;
              img.removeAttribute('data-src');
            }
            observer.unobserve(img);
          }
        });
      });
      
      images.forEach(img => imageObserver.observe(img));
    }
  }

  // Initialize lazy loading
  lazyLoadImages();

  /**
   * Preload critical resources
   */
  function preloadCriticalResources() {
    // Preload avatar image if user is authenticated
    const avatarImg = mobileNav.querySelector('.mobile-nav-v2__avatar img');
    if (avatarImg && avatarImg.src) {
      const link = document.createElement('link');
      link.rel = 'preload';
      link.as = 'image';
      link.href = avatarImg.src;
      document.head.appendChild(link);
    }
  }

  // Preload on page load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', preloadCriticalResources);
  } else {
    preloadCriticalResources();
  }

  /* =========================================================================
     PUBLIC API (for debugging and external control)
     ========================================================================= */

  window.MobileNavV2 = {
    open: openMobileNav,
    close: closeMobileNav,
    toggle: toggleMobileNav,
    isOpen: () => isOpen,
    version: '2.0.0'
  };

  /* =========================================================================
     INITIALIZATION COMPLETE
     ========================================================================= */

  console.log('✅ Mobile Navigation V2 initialized successfully');

})();
