/**
 * Mobile Navigation Controller
 * Handles drawer toggle and smooth animations
 */

(() => {
  'use strict';

  // Elements
  const drawer = document.getElementById('mobileDrawer');
  const backdrop = document.getElementById('mobileBackdrop');
  const toggleButtons = document.querySelectorAll('[data-drawer-toggle]');
  const closeButtons = document.querySelectorAll('[data-drawer-close]');

  if (!drawer || !backdrop) return;

  let isOpen = false;
  let startX = 0;
  let currentX = 0;

  // Open drawer
  const openDrawer = () => {
    if (isOpen) return;
    isOpen = true;
    drawer.classList.add('open');
    backdrop.classList.add('active');
    document.body.style.overflow = 'hidden';
    drawer.setAttribute('aria-hidden', 'false');
  };

  // Close drawer
  const closeDrawer = () => {
    if (!isOpen) return;
    isOpen = false;
    drawer.classList.remove('open');
    backdrop.classList.remove('active');
    document.body.style.overflow = '';
    drawer.setAttribute('aria-hidden', 'true');
  };

  // Toggle drawer
  const toggleDrawer = () => {
    isOpen ? closeDrawer() : openDrawer();
  };

  // Event listeners
  toggleButtons.forEach(btn => {
    btn.addEventListener('click', toggleDrawer);
  });

  closeButtons.forEach(btn => {
    btn.addEventListener('click', closeDrawer);
  });

  backdrop.addEventListener('click', closeDrawer);

  // Keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isOpen) {
      closeDrawer();
    }
  });

  // Swipe to close
  drawer.addEventListener('touchstart', (e) => {
    startX = e.touches[0].clientX;
  }, { passive: true });

  drawer.addEventListener('touchmove', (e) => {
    if (!isOpen) return;
    currentX = e.touches[0].clientX;
    const diff = currentX - startX;
    
    if (diff > 0) {
      const translateX = Math.min(diff, drawer.offsetWidth);
      drawer.style.transform = `translateX(${translateX}px)`;
    }
  }, { passive: true });

  drawer.addEventListener('touchend', () => {
    const diff = currentX - startX;
    
    if (diff > 100) {
      closeDrawer();
    }
    
    drawer.style.transform = '';
    startX = 0;
    currentX = 0;
  }, { passive: true });

  // Theme toggle
  const themeToggle = document.querySelector('[data-theme-toggle]');
  if (themeToggle) {
    const syncTheme = () => {
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      themeToggle.checked = isDark;
    };

    themeToggle.addEventListener('change', (e) => {
      const newTheme = e.target.checked ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
    });

    syncTheme();

    // Watch for external theme changes
    const observer = new MutationObserver(syncTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme']
    });
  }

  // Smooth scroll enhancement for nav links
  document.querySelectorAll('.nav-item[href^="/"], .drawer-links a[href^="/"]').forEach(link => {
    link.addEventListener('click', () => {
      if (isOpen) {
        setTimeout(closeDrawer, 200);
      }
    });
  });

  // Add glow animation on interaction
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', function(e) {
      this.style.animation = 'none';
      setTimeout(() => {
        this.style.animation = '';
      }, 10);
    });
  });

  // Initialize
  drawer.setAttribute('aria-hidden', 'true');

})();
