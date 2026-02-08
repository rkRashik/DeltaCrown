/**
 * DELTACROWN PRIMARY NAVIGATION SYSTEM
 * Modern 2026 Esports-Grade JavaScript (Refactored for Robustness)
 * Handles: Scroll Effects, Dropdowns, Search Modal, Mobile Menu, Swipe Gestures
 */

(function () {
  'use strict';

  // Navigation Controller
  const dcNav = {
    navbar: null,
    mobileHeader: null,
    lastScrollY: 0,
    ticking: false,

    // Breakpoints
    breakpoints: {
      sm: 640,
      md: 768,
      lg: 1024,
      xl: 1280
    },

    // Initialize
    init() {
      // DOM Elements
      this.navbar = document.getElementById('dc-navbar');
      this.mobileHeader = document.getElementById('dc-mobile-header');

      // Initialize Modules
      this.initScrollEffects();
      this.initDropdowns();
      this.initSearch();
      this.initMobileMenu();
      this.initKeyboardShortcuts();
      this.initSwipeGestures();

      console.log('DeltaCrown Navigation Initialized');
    },

    // === MOBILE MENU CONTROLS (Exposed for Inline Handlers) ===
    openMenu() {
      const drawer = document.getElementById('dc-mobile-drawer');
      const backdrop = document.getElementById('dc-mobile-backdrop');

      if (drawer) {
        // CLEANUP: Remove any inline hacks first
        drawer.style.transform = '';
        drawer.style.removeProperty('transform');
        drawer.classList.add('open');
      }

      if (backdrop) {
        backdrop.style.display = ''; // Reset display
        backdrop.classList.add('visible');
        backdrop.classList.remove('hidden');
      }
      document.body.style.overflow = 'hidden';
    },

    closeMenu() {
      const drawer = document.getElementById('dc-mobile-drawer');
      const backdrop = document.getElementById('dc-mobile-backdrop');

      if (drawer) {
        drawer.classList.remove('open');
        drawer.style.transform = ''; // Ensure no leftover inline transforms
      }

      if (backdrop) {
        backdrop.classList.remove('visible');
        // Delay hiding display:none to allow opacity transition
        setTimeout(() => {
          // Only add hidden if it wasn't reopened in the meantime
          if (!backdrop.classList.contains('visible')) {
            backdrop.classList.add('hidden');
            backdrop.style.display = ''; // Clean up
          }
        }, 300);
      }
      document.body.style.overflow = '';
    },

    toggleSearch() {
      const overlay = document.getElementById('dc-search-overlay');
      const input = document.getElementById('dc-cmd-input');
      const isOpen = overlay?.classList.contains('open');

      if (isOpen) {
        overlay.classList.remove('open');
        document.body.style.overflow = '';
      } else if (overlay) {
        overlay.classList.add('open');
        document.body.style.overflow = 'hidden';
        setTimeout(() => input?.focus(), 100);
      }
    },

    // === SCROLL EFFECTS ===
    initScrollEffects() {
      const updateNav = () => {
        const scrollY = window.scrollY;

        // Desktop & Mobile Glass Effect
        if (scrollY > 50) {
          this.navbar?.classList.add('scrolled');
        } else {
          this.navbar?.classList.remove('scrolled');
        }

        // Mobile Smart Hide/Show
        const isMobile = window.innerWidth < this.breakpoints.md;
        if (isMobile) {
          if (scrollY > this.lastScrollY && scrollY > 100) {
            this.navbar?.classList.add('nav-hidden');
            this.mobileHeader?.classList.add('nav-hidden');
          } else {
            this.navbar?.classList.remove('nav-hidden');
            this.mobileHeader?.classList.remove('nav-hidden');
          }
        }

        this.lastScrollY = scrollY;
        this.ticking = false;
      };

      const requestTick = () => {
        if (!this.ticking) {
          window.requestAnimationFrame(updateNav);
          this.ticking = true;
        }
      };

      window.addEventListener('scroll', requestTick, { passive: true });
      updateNav();
    },

    // === DROPDOWNS ===
    initDropdowns() {
      const notifBtn = document.getElementById('dc-notif-btn');
      const notifMenu = document.getElementById('dc-notif-menu');
      const profileBtn = document.getElementById('dc-profile-btn');
      const profileMenu = document.getElementById('dc-profile-menu');
      const profileChevron = document.getElementById('dc-profile-chevron');

      // Helper to toggle
      const toggle = (menu, btn, otherMenu, otherBtn) => {
        if (!menu) return;
        const isOpen = menu.classList.contains('show');

        // Close other
        if (otherMenu) {
          otherMenu.classList.remove('show');
          if (otherBtn) otherBtn.setAttribute('aria-expanded', 'false');
        }

        if (isOpen) {
          menu.classList.remove('show');
          if (btn) btn.setAttribute('aria-expanded', 'false');
        } else {
          menu.classList.add('show');
          this.positionDropdown(menu, btn);
          if (btn) btn.setAttribute('aria-expanded', 'true');

          // Focus first item
          const first = menu.querySelector('a, button');
          if (first) setTimeout(() => first.focus(), 50);
        }
      };

      // Listeners
      if (notifBtn) {
        notifBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          toggle(notifMenu, notifBtn, profileMenu, profileBtn);
          if (profileChevron) profileChevron.style.transform = 'rotate(0deg)';
        });
      }

      if (profileBtn) {
        profileBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          toggle(profileMenu, profileBtn, notifMenu, notifBtn);
          if (profileChevron) {
            const willOpen = !profileMenu.classList.contains('show'); // It's toggling
            profileChevron.style.transform = willOpen ? 'rotate(180deg)' : 'rotate(0deg)';
          }
        });
      }

      // Close on outside click
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.dc-dropdown') && !e.target.closest('button')) {
          if (notifMenu) notifMenu.classList.remove('show');
          if (profileMenu) profileMenu.classList.remove('show');
          if (profileChevron) profileChevron.style.transform = 'rotate(0deg)';
          if (notifBtn) notifBtn.setAttribute('aria-expanded', 'false');
          if (profileBtn) profileBtn.setAttribute('aria-expanded', 'false');
        }
      });
    },

    positionDropdown(dropdown, button) {
      if (!dropdown || !button) return;
      const rect = button.getBoundingClientRect();
      const dropRect = dropdown.getBoundingClientRect();

      // Default right align
      dropdown.style.right = '0';
      dropdown.style.left = 'auto';

      // Check overflow left
      const leftEdge = rect.right - dropRect.width;
      if (leftEdge < 0) {
        dropdown.style.right = 'auto';
        dropdown.style.left = '0';
      }
    },

    // === SEARCH ===
    initSearch() {
      const overlay = document.getElementById('dc-search-overlay');
      overlay?.addEventListener('click', (e) => {
        if (e.target === overlay) this.toggleSearch();
      });
    },

    // === MOBILE MENU INIT ===
    initMobileMenu() {
      const menuToggle = document.getElementById('dc-mobile-menu-toggle');
      const drawerClose = document.getElementById('dc-mobile-drawer-close');
      const backdrop = document.getElementById('dc-mobile-backdrop');
      const drawer = document.getElementById('dc-mobile-drawer');

      // Bind events using class methods
      menuToggle?.addEventListener('click', () => this.openMenu());
      drawerClose?.addEventListener('click', () => this.closeMenu());
      backdrop?.addEventListener('click', () => this.closeMenu());

      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && drawer?.classList.contains('open')) {
          this.closeMenu();
        }
      });
    },

    // === SWIPE GESTURES ===
    initSwipeGestures() {
      const drawer = document.getElementById('dc-mobile-drawer');
      if (!drawer) return;

      let startX = 0;
      let currentX = 0;
      let isDragging = false;

      drawer.addEventListener('touchstart', (e) => {
        startX = e.touches[0].clientX;
        currentX = startX;
        isDragging = true;
      }, { passive: true });

      drawer.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        currentX = e.touches[0].clientX;
        const diff = currentX - startX;

        // Only move if swiping right (closing)
        if (diff > 0) {
          drawer.style.transform = `translateX(${diff}px)`;
        }
      }, { passive: true });

      drawer.addEventListener('touchend', () => {
        if (!isDragging) return;
        const diff = currentX - startX;

        // Threshold to close
        if (diff > 100) {
          this.closeMenu();
        } else {
          // Snap back
          drawer.style.transform = '';
        }
        isDragging = false;

        // Clean up inline style to let CSS take over
        setTimeout(() => {
          if (!drawer.classList.contains('open')) {
            drawer.style.transform = '';
          }
        }, 300);
      }, { passive: true });
    },

    // === SHORTCUTS ===
    initKeyboardShortcuts() {
      document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          this.toggleSearch();
        }
        if (e.key === 'Escape') {
          const overlay = document.getElementById('dc-search-overlay');
          if (overlay?.classList.contains('open')) this.toggleSearch();
        }
      });
    }
  };

  // Expose globally IMMEDIATELY
  window.dcNav = dcNav;

  // Initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => dcNav.init());
  } else {
    // If loaded async/defer
    dcNav.init();
  }

})();
