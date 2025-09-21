(function () {
  const nav = document.querySelector('[data-site-nav]');
  if (!nav) return;

  const notifBadge = nav.querySelector('[data-notif-badge]');
  const notifTrigger = nav.querySelector('.notif-trigger');
  const mobileToggle = nav.querySelector('[data-open-drawer="main-drawer"]');
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
  if (mobileToggle && mobileDrawer) {
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
      openDrawer();
      mobileToggle.setAttribute('aria-expanded', 'true');
    });

    mobileCloseButtons.forEach((btn) => {
      btn.addEventListener('click', (event) => {
        event.preventDefault();
        closeDrawer();
        mobileToggle.setAttribute('aria-expanded', 'false');
      });
    });

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
      if (event.target === mobileDrawer) {
        closeDrawer();
        mobileToggle.setAttribute('aria-expanded', 'false');
      }
    });

    document.addEventListener('click', (event) => {
      if (!mobileDrawer.hidden && !mobileDrawer.contains(event.target) && event.target !== mobileToggle) {
        closeDrawer();
        mobileToggle.setAttribute('aria-expanded', 'false');
      }
    });

    window.addEventListener('resize', () => {
      if (window.innerWidth >= 1024) {
        closeDrawer({ returnFocus: false });
        mobileToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }
})();
