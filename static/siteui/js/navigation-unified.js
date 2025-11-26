/**
 * Desktop Notification & Profile Dropdowns
 * Modern, professional dropdown system
 */
(function() {
  'use strict';

  const notifBtn = document.querySelector('[data-notif-toggle]');
  const profileBtn = document.querySelector('[data-profile-toggle]');
  let notifDropdown = null;
  let profileDropdown = null;

  // Create Notification Dropdown
  if (notifBtn) {
    notifDropdown = createNotificationDropdown();
    notifBtn.parentNode.appendChild(notifDropdown);

    notifBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      toggleDropdown(notifDropdown);
      closeDropdown(profileDropdown);
    });
  }

  // Create Profile Dropdown
  if (profileBtn) {
    profileDropdown = createProfileDropdown();
    profileBtn.parentNode.appendChild(profileDropdown);

    profileBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      toggleDropdown(profileDropdown);
      closeDropdown(notifDropdown);
    });
  }

  // Close on outside click
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.dc-desktop-dropdown')) {
      closeDropdown(notifDropdown);
      closeDropdown(profileDropdown);
    }
  });

  // Close on escape
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeDropdown(notifDropdown);
      closeDropdown(profileDropdown);
    }
  });

  // =================================================================
  // SCROLLING NAVBAR WITH GLASSY EFFECT
  // =================================================================
  
  const navbar = document.querySelector('.unified-nav-desktop');
  let lastScrollY = window.scrollY;
  let ticking = false;
  
  function updateNavbar() {
    const scrollY = window.scrollY;
    
    if (scrollY > 50) {
      navbar?.classList.add('scrolled');
    } else {
      navbar?.classList.remove('scrolled');
    }
    
    ticking = false;
  }
  
  function requestNavbarUpdate() {
    if (!ticking) {
      window.requestAnimationFrame(updateNavbar);
      ticking = true;
    }
  }
  
  window.addEventListener('scroll', requestNavbarUpdate, { passive: true });
  updateNavbar(); // Initial check

  // =================================================================
  // THEME TOGGLE SYSTEM
  // =================================================================
  
  const themeToggles = document.querySelectorAll('[data-theme-toggle]');
  
  // Load saved theme or default to dark
  const savedTheme = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  document.body.setAttribute('data-theme', savedTheme);
  
  // Set initial toggle states
  themeToggles.forEach(toggle => {
    toggle.checked = savedTheme === 'dark';
  });
  
  // Handle theme changes
  themeToggles.forEach(toggle => {
    toggle.addEventListener('change', function() {
      const newTheme = this.checked ? 'dark' : 'light';
      
      // Apply theme
      document.documentElement.setAttribute('data-theme', newTheme);
      document.body.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      
      // Sync all toggles
      themeToggles.forEach(t => {
        t.checked = this.checked;
      });
    });
  });

  /**
   * Create Notification Dropdown
   */
  function createNotificationDropdown() {
    const dropdown = document.createElement('div');
    dropdown.className = 'dc-desktop-dropdown dc-notif-dropdown';
    dropdown.innerHTML = `
      <div class="dc-notif-dropdown__header">
        <h3 class="dc-notif-dropdown__title">Notifications</h3>
        <button class="dc-notif-dropdown__mark-all" type="button">Mark all read</button>
      </div>
      <div class="dc-notif-dropdown__list">
        <div class="dc-notif-dropdown__empty">
          <div class="dc-notif-dropdown__empty-icon">
            <i class="fas fa-bell-slash"></i>
          </div>
          <div class="dc-notif-dropdown__empty-text">No notifications yet</div>
        </div>
      </div>
      <div class="dc-notif-dropdown__footer">
        <a href="/notifications/" class="dc-notif-dropdown__view-all">View all notifications</a>
      </div>
    `;
    return dropdown;
  }

  /**
   * Create Profile Dropdown
   */
  function createProfileDropdown() {
    const dropdown = document.createElement('div');
    dropdown.className = 'dc-desktop-dropdown dc-profile-dropdown';
    
    // Get user info from avatar button
    const avatarImg = profileBtn.querySelector('img');
    const username = avatarImg ? avatarImg.alt : 'User';
    const avatarUrl = avatarImg ? avatarImg.src : '/static/img/user_avatar/default-avatar.png';

    dropdown.innerHTML = `
      <div class="dc-profile-dropdown__header">
        <img src="${avatarUrl}" alt="${username}" class="dc-profile-dropdown__avatar">
        <div class="dc-profile-dropdown__info">
          <div class="dc-profile-dropdown__name">${username}</div>
          <div class="dc-profile-dropdown__username">@${username}</div>
        </div>
      </div>
      <div class="dc-profile-dropdown__menu">
        <a href="/u/${username}/" class="dc-profile-dropdown__item">
          <i class="fas fa-user dc-profile-dropdown__item-icon"></i>
          <span>My Profile</span>
        </a>
        <a href="/dashboard/" class="dc-profile-dropdown__item">
          <i class="fas fa-th-large dc-profile-dropdown__item-icon"></i>
          <span>Dashboard</span>
        </a>
        <a href="/user/me/settings/" class="dc-profile-dropdown__item">
          <i class="fas fa-cog dc-profile-dropdown__item-icon"></i>
          <span>Settings</span>
        </a>
        <a href="/notifications/" class="dc-profile-dropdown__item">
          <i class="fas fa-bell dc-profile-dropdown__item-icon"></i>
          <span>Notifications</span>
        </a>
        <div class="dc-profile-dropdown__divider"></div>
        <a href="/accounts/logout/" class="dc-profile-dropdown__item dc-profile-dropdown__item--danger">
          <i class="fas fa-sign-out-alt dc-profile-dropdown__item-icon"></i>
          <span>Sign Out</span>
        </a>
      </div>
    `;
    return dropdown;
  }

  /**
   * Toggle dropdown open/close
   */
  function toggleDropdown(dropdown) {
    if (!dropdown) return;
    const isOpen = dropdown.classList.contains('is-open');
    if (isOpen) {
      closeDropdown(dropdown);
    } else {
      openDropdown(dropdown);
    }
  }

  /**
   * Open dropdown
   */
  function openDropdown(dropdown) {
    if (!dropdown) return;
    dropdown.classList.add('is-open');
  }

  /**
   * Close dropdown
   */
  function closeDropdown(dropdown) {
    if (!dropdown) return;
    dropdown.classList.remove('is-open');
  }

})();
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
