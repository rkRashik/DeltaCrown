/**
 * DELTACROWN PRIMARY NAVIGATION SYSTEM
 * Modern 2026 Esports-Grade JavaScript
 * Handles: Scroll Effects, Dropdowns, Search Modal, Mobile Menu, Swipe Gestures
 */

(function () {
  'use strict';

  // Navigation State
  const dcNav = {
    navbar: null,
    mobileHeader: null,
    lastScrollY: 0,
    ticking: false,

    // Breakpoints (matching CSS)
    breakpoints: {
      sm: 640,
      md: 768,
      lg: 1024,
      xl: 1280
    },

    // Initialize
    init() {
      this.navbar = document.getElementById('dc-navbar');
      this.mobileHeader = document.getElementById('dc-mobile-header');

      this.initScrollEffects();
      this.initDropdowns();
      this.initSearch();
      this.initMobileMenu();
      this.initKeyboardShortcuts();
      this.initSwipeGestures();
    },

    // === SCROLL EFFECTS (Liquid Glass) ===
    initScrollEffects() {
      const updateNav = () => {
        const scrollY = window.scrollY;

        // Glass effect on scroll (both desktop and mobile)
        if (scrollY > 50) {
          this.navbar?.classList.add('scrolled');
        } else {
          this.navbar?.classList.remove('scrolled');
        }

        // Smart hide/show ONLY on mobile
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
      updateNav(); // Initial check
    },

    // === DROPDOWNS WITH SMART POSITIONING ===
    initDropdowns() {
      const notifBtn = document.getElementById('dc-notif-btn');
      const notifMenu = document.getElementById('dc-notif-menu');
      const profileBtn = document.getElementById('dc-profile-btn');
      const profileMenu = document.getElementById('dc-profile-menu');
      const profileChevron = document.getElementById('dc-profile-chevron');

      // Notification dropdown
      if (notifBtn && notifMenu) {
        notifBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          this.toggleDropdown(notifMenu, notifBtn);
          this.closeDropdown(profileMenu, profileBtn);
          if (profileChevron) profileChevron.style.transform = 'rotate(0deg)';
        });
      }

      // Profile dropdown
      if (profileBtn && profileMenu) {
        profileBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          this.toggleDropdown(profileMenu, profileBtn);
          this.closeDropdown(notifMenu, notifBtn);

          // Rotate chevron
          if (profileChevron) {
            const isOpen = profileMenu.classList.contains('show');
            profileChevron.style.transform = isOpen ? 'rotate(180deg)' : 'rotate(0deg)';
          }
        });
      }

      // Close dropdowns on outside click
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.dc-dropdown') && !e.target.closest('button')) {
          this.closeDropdown(notifMenu, notifBtn);
          this.closeDropdown(profileMenu, profileBtn);
          if (profileChevron) profileChevron.style.transform = 'rotate(0deg)';
        }
      });

      // Close on escape
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.closeDropdown(notifMenu, notifBtn);
          this.closeDropdown(profileMenu, profileBtn);
          if (profileChevron) profileChevron.style.transform = 'rotate(0deg)';
        }
      });

      // Keyboard navigation in dropdowns
      this.initDropdownKeyboardNav(notifMenu);
      this.initDropdownKeyboardNav(profileMenu);
    },

    // Smart dropdown positioning to prevent overflow
    positionDropdown(dropdown, button) {
      if (!dropdown || !button) return;

      const rect = button.getBoundingClientRect();
      const dropdownRect = dropdown.getBoundingClientRect();
      const viewportWidth = window.innerWidth;

      // Reset positioning
      dropdown.style.right = '0';
      dropdown.style.left = 'auto';

      // Check if dropdown would overflow right edge
      if (rect.right < dropdownRect.width) {
        dropdown.style.right = 'auto';
        dropdown.style.left = '0';
      }

      // Check if dropdown would overflow left edge
      const dropdownLeft = rect.left + rect.width - dropdownRect.width;
      if (dropdownLeft < 0) {
        dropdown.style.right = '0';
        dropdown.style.left = 'auto';
      }
    },

    toggleDropdown(dropdown, button) {
      if (!dropdown) return;

      const isOpen = dropdown.classList.contains('show');

      if (!isOpen) {
        dropdown.classList.add('show');
        this.positionDropdown(dropdown, button);

        // Update ARIA
        if (button) {
          button.setAttribute('aria-expanded', 'true');
        }

        // Focus first item
        const firstItem = dropdown.querySelector('.dc-dd-item, a, button');
        if (firstItem) {
          setTimeout(() => firstItem.focus(), 100);
        }
      } else {
        dropdown.classList.remove('show');

        // Update ARIA
        if (button) {
          button.setAttribute('aria-expanded', 'false');
          button.focus();
        }
      }
    },

    closeDropdown(dropdown, button) {
      if (!dropdown) return;
      dropdown.classList.remove('show');

      // Update ARIA
      if (button) {
        button.setAttribute('aria-expanded', 'false');
      }
    },

    // Keyboard navigation for dropdowns
    initDropdownKeyboardNav(dropdown) {
      if (!dropdown) return;

      dropdown.addEventListener('keydown', (e) => {
        const items = Array.from(dropdown.querySelectorAll('.dc-dd-item, a, button'));
        const currentIndex = items.indexOf(document.activeElement);

        switch (e.key) {
          case 'ArrowDown':
            e.preventDefault();
            const nextIndex = (currentIndex + 1) % items.length;
            items[nextIndex]?.focus();
            break;

          case 'ArrowUp':
            e.preventDefault();
            const prevIndex = (currentIndex - 1 + items.length) % items.length;
            items[prevIndex]?.focus();
            break;

          case 'Home':
            e.preventDefault();
            items[0]?.focus();
            break;

          case 'End':
            e.preventDefault();
            items[items.length - 1]?.focus();
            break;
        }
      });
    },

    // === SEARCH MODAL (Command Palette) ===
    initSearch() {
      const overlay = document.getElementById('dc-search-overlay');
      const input = document.getElementById('dc-cmd-input');

      this.toggleSearch = () => {
        const isOpen = overlay.classList.contains('open');

        if (isOpen) {
          overlay.classList.remove('open');
          document.body.style.overflow = '';
        } else {
          overlay.classList.add('open');
          document.body.style.overflow = 'hidden';
          setTimeout(() => input?.focus(), 100);
        }
      };

      // Close on background click
      overlay?.addEventListener('click', (e) => {
        if (e.target === overlay) {
          this.toggleSearch();
        }
      });

      // Expose globally for onclick handlers
      window.dcNav = this;
    },

    // === MOBILE MENU WITH SWIPE GESTURES ===
    initMobileMenu() {
      const menuToggle = document.getElementById('dc-mobile-menu-toggle');
      const drawer = document.getElementById('dc-mobile-drawer');
      const drawerClose = document.getElementById('dc-mobile-drawer-close');
      const backdrop = document.getElementById('dc-mobile-backdrop');

      const openMenu = () => {
        drawer?.classList.add('open');
        backdrop?.classList.add('visible');
        backdrop?.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
      };

      const closeMenu = () => {
        drawer?.classList.remove('open');
        backdrop?.classList.remove('visible');
        setTimeout(() => backdrop?.classList.add('hidden'), 300);
        document.body.style.overflow = '';
      };

      menuToggle?.addEventListener('click', openMenu);
      drawerClose?.addEventListener('click', closeMenu);
      backdrop?.addEventListener('click', closeMenu);

      // Close on escape
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && drawer?.classList.contains('open')) {
          closeMenu();
        }
      });

      // Expose for swipe gesture handler
      this.closeMenu = closeMenu;
    },

    // === SWIPE GESTURES FOR MOBILE DRAWER ===
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

        // Only allow swipe to close (right direction)
        if (diff > 0) {
          drawer.style.transform = `translateX(${diff}px)`;
        }
      }, { passive: true });

      drawer.addEventListener('touchend', () => {
        if (!isDragging) return;

        const diff = currentX - startX;

        // If swiped more than 100px, close the drawer
        if (diff > 100) {
          this.closeMenu();
        }

        // Reset
        drawer.style.transform = '';
        isDragging = false;
      }, { passive: true });
    },

    // === KEYBOARD SHORTCUTS ===
    initKeyboardShortcuts() {
      document.addEventListener('keydown', (e) => {
        // Cmd+K or Ctrl+K -> Open search
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
          e.preventDefault();
          this.toggleSearch();
        }

        // Escape -> Close search
        if (e.key === 'Escape') {
          const overlay = document.getElementById('dc-search-overlay');
          if (overlay?.classList.contains('open')) {
            this.toggleSearch();
          }
        }
      });
    }
  };

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => dcNav.init());
  } else {
    dcNav.init();
  }

  // Expose globally
  window.dcNav = dcNav;

})();
