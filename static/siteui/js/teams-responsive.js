/**
 * TEAMS RESPONSIVE INTERACTION HANDLER
 * Handles mobile sidebar, touch gestures, and responsive behaviors
 */

(function() {
  'use strict';

  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  function init() {
    initMobileSidebar();
    initResponsiveCards();
    initTouchGestures();
    initResponsiveSearch();
    initViewportHeightFix();
  }

  /**
   * Mobile Sidebar Toggle
   */
  function initMobileSidebar() {
    const toggle = document.getElementById('mobile-sidebar-toggle');
    const sidebar = document.getElementById('left-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const close = document.getElementById('sidebar-close');

    if (!toggle || !sidebar || !overlay) return;

    // Open sidebar
    toggle.addEventListener('click', () => {
      sidebar.classList.add('is-open');
      overlay.classList.add('is-visible');
      document.body.style.overflow = 'hidden';
    });

    // Close sidebar
    const closeSidebar = () => {
      sidebar.classList.remove('is-open');
      overlay.classList.remove('is-visible');
      document.body.style.overflow = '';
    };

    if (close) {
      close.addEventListener('click', closeSidebar);
    }

    overlay.addEventListener('click', closeSidebar);

    // Close on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
        closeSidebar();
      }
    });

    // Close on window resize to desktop
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (window.innerWidth >= 1024 && sidebar.classList.contains('is-open')) {
          closeSidebar();
        }
      }, 250);
    });
  }

  /**
   * Responsive Card Click Handling
   * Improves touch interaction on mobile devices
   */
  function initResponsiveCards() {
    const cards = document.querySelectorAll('.team-card');
    
    cards.forEach(card => {
      // Add active state for touch feedback
      card.addEventListener('touchstart', function() {
        this.style.transform = 'scale(0.98)';
      }, { passive: true });

      card.addEventListener('touchend', function() {
        this.style.transform = '';
      }, { passive: true });

      card.addEventListener('touchcancel', function() {
        this.style.transform = '';
      }, { passive: true });

      // Prevent card click when clicking action buttons
      const actionBtns = card.querySelectorAll('.team-action-btn');
      actionBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
        });
      });
    });
  }

  /**
   * Touch Gesture Support
   * Adds swipe-to-close for mobile sidebar
   */
  function initTouchGestures() {
    const sidebar = document.getElementById('left-sidebar');
    if (!sidebar) return;

    let touchStartX = 0;
    let touchEndX = 0;
    let isSwiping = false;

    sidebar.addEventListener('touchstart', (e) => {
      touchStartX = e.changedTouches[0].screenX;
      isSwiping = true;
    }, { passive: true });

    sidebar.addEventListener('touchmove', (e) => {
      if (!isSwiping) return;
      touchEndX = e.changedTouches[0].screenX;
      
      // Visual feedback during swipe
      const diff = touchEndX - touchStartX;
      if (diff < 0) { // Swiping left
        const translateX = Math.max(diff, -320);
        sidebar.style.transform = `translateX(${translateX}px)`;
      }
    }, { passive: true });

    sidebar.addEventListener('touchend', () => {
      if (!isSwiping) return;
      isSwiping = false;

      const diff = touchEndX - touchStartX;
      
      // If swiped more than 100px, close sidebar
      if (diff < -100) {
        sidebar.classList.remove('is-open');
        document.getElementById('sidebar-overlay')?.classList.remove('is-visible');
        document.body.style.overflow = '';
      }
      
      // Reset transform
      sidebar.style.transform = '';
    }, { passive: true });
  }

  /**
   * Responsive Search Behavior
   * Auto-focus on desktop, better mobile keyboard handling
   */
  function initResponsiveSearch() {
    const searchInput = document.getElementById('team-search');
    if (!searchInput) return;

    // Auto-focus on desktop only
    if (window.innerWidth >= 1024) {
      searchInput.focus();
    }

    // Handle mobile keyboard
    if (window.innerWidth < 768) {
      searchInput.addEventListener('focus', () => {
        // Scroll search into view on mobile
        setTimeout(() => {
          searchInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 300);
      });

      searchInput.addEventListener('blur', () => {
        // Scroll back to top after keyboard dismissal
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }

    // Clear button functionality
    const clearBtn = document.getElementById('search-clear');
    if (clearBtn) {
      searchInput.addEventListener('input', () => {
        clearBtn.style.display = searchInput.value ? 'flex' : 'none';
      });

      clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearBtn.style.display = 'none';
        searchInput.focus();
        
        // Trigger search update
        const event = new Event('input', { bubbles: true });
        searchInput.dispatchEvent(event);
      });
    }
  }

  /**
   * Viewport Height Fix for Mobile Browsers
   * Fixes 100vh issues with mobile browser UI
   */
  function initViewportHeightFix() {
    const setVH = () => {
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--vh', `${vh}px`);
    };

    setVH();
    
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(setVH, 100);
    });

    // Handle orientation change
    window.addEventListener('orientationchange', () => {
      setTimeout(setVH, 100);
    });
  }

  /**
   * Enhanced Filter Toggle Animation
   */
  const filterToggles = document.querySelectorAll('.filter-toggle');
  filterToggles.forEach(toggle => {
    toggle.addEventListener('click', function() {
      const isExpanded = this.getAttribute('aria-expanded') === 'true';
      const targetId = this.id.replace('-toggle', '');
      const target = document.getElementById(targetId);
      
      if (target) {
        if (isExpanded) {
          target.classList.remove('expanded');
          this.setAttribute('aria-expanded', 'false');
        } else {
          target.classList.add('expanded');
          this.setAttribute('aria-expanded', 'true');
        }
      }
    });
  });

  /**
   * Responsive Image Lazy Loading
   */
  if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          if (img.dataset.src) {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
            observer.unobserve(img);
          }
        }
      });
    }, {
      rootMargin: '50px 0px',
      threshold: 0.01
    });

    document.querySelectorAll('img[data-src]').forEach(img => {
      imageObserver.observe(img);
    });
  }

  /**
   * Smooth Scroll for Anchor Links
   */
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      if (href === '#' || href === '#!') return;
      
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        const offset = window.innerWidth < 1024 ? 60 : 0; // Account for mobile nav
        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - offset;
        
        window.scrollTo({
          top: targetPosition,
          behavior: 'smooth'
        });
      }
    });
  });

  /**
   * Performance: Throttle Scroll Events
   */
  let scrollTimer;
  let lastScrollY = window.pageYOffset;

  window.addEventListener('scroll', () => {
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(() => {
      const currentScrollY = window.pageYOffset;
      const scrollDirection = currentScrollY > lastScrollY ? 'down' : 'up';
      lastScrollY = currentScrollY;

      // Add/remove class based on scroll position
      document.body.classList.toggle('is-scrolled', currentScrollY > 50);
      document.body.dataset.scrollDirection = scrollDirection;
    }, 100);
  }, { passive: true });

  /**
   * Enhanced Theme Toggle Animation
   */
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      // Add transition class
      document.documentElement.classList.add('theme-transitioning');
      
      setTimeout(() => {
        document.documentElement.classList.remove('theme-transitioning');
      }, 300);
    });
  }

  /**
   * Network Status Indicator
   */
  window.addEventListener('online', () => {
    showToast('Connection restored', 'success');
  });

  window.addEventListener('offline', () => {
    showToast('You are offline', 'warning');
  });

  function showToast(message, type = 'info') {
    // Integration with existing toast system
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
    }
  }

  /**
   * Accessibility: Skip to Content
   */
  const skipLink = document.querySelector('.skip-link');
  if (skipLink) {
    skipLink.addEventListener('click', (e) => {
      e.preventDefault();
      const target = document.querySelector(skipLink.getAttribute('href'));
      if (target) {
        target.setAttribute('tabindex', '-1');
        target.focus();
        target.removeAttribute('tabindex');
      }
    });
  }

})();
