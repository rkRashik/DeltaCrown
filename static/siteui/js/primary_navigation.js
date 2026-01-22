/**
 * DELTACROWN PRIMARY NAVIGATION SYSTEM
 * Modern 2026 Esports-Grade JavaScript
 * Handles: Scroll Effects, Dropdowns, Search Modal, Mobile Menu
 */

(function() {
  'use strict';

  // Navigation State
  const dcNav = {
    navbar: null,
    mobileHeader: null,
    lastScrollY: 0,
    ticking: false,

    // Initialize
    init() {
      this.navbar = document.getElementById('dc-navbar');
      this.mobileHeader = document.getElementById('dc-mobile-header');
      
      this.initScrollEffects();
      this.initDropdowns();
      this.initSearch();
      this.initMobileMenu();
      this.initKeyboardShortcuts();
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
        const isMobile = window.innerWidth < 768;
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

    // === DROPDOWNS ===
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
          this.toggleDropdown(notifMenu);
          this.closeDropdown(profileMenu);
          if (profileChevron) profileChevron.style.transform = 'rotate(0deg)';
        });
      }

      // Profile dropdown
      if (profileBtn && profileMenu) {
        profileBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          this.toggleDropdown(profileMenu);
          this.closeDropdown(notifMenu);
          
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
          this.closeDropdown(notifMenu);
          this.closeDropdown(profileMenu);
          if (profileChevron) profileChevron.style.transform = 'rotate(0deg)';
        }
      });

      // Close on escape
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          this.closeDropdown(notifMenu);
          this.closeDropdown(profileMenu);
          if (profileChevron) profileChevron.style.transform = 'rotate(0deg)';
        }
      });
    },

    toggleDropdown(dropdown) {
      if (!dropdown) return;
      dropdown.classList.toggle('show');
    },

    closeDropdown(dropdown) {
      if (!dropdown) return;
      dropdown.classList.remove('show');
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

    // === MOBILE MENU ===
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
