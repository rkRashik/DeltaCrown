/**
 * Tournament Hub - Enhanced Modern JavaScript
 * Handles filter interactions, smooth scrolling, and dynamic updates
 */

(function() {
  'use strict';

  // Smooth scroll to sections
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href === '#' || href === '#!') return;
        
        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
          
          // Update URL without scrolling
          history.pushState(null, null, href);
        }
      });
    });
  }

  // Filter Orb functionality
  function initFilterOrb() {
    const filterOrb = document.querySelector('[data-behavior="filter-orb"]');
    if (!filterOrb) return;

    const toggle = filterOrb.querySelector('.filter-orb__toggle');
    const panel = filterOrb.querySelector('.filter-orb__panel');
    const closeBtn = filterOrb.querySelector('[data-close="filter-orb"]');

    if (!toggle || !panel) return;

    // Toggle panel
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
      
      if (isExpanded) {
        closePanel();
      } else {
        openPanel();
      }
    });

    // Close button
    if (closeBtn) {
      closeBtn.addEventListener('click', closePanel);
    }

    // Click outside to close
    document.addEventListener('click', (e) => {
      if (!filterOrb.contains(e.target) && toggle.getAttribute('aria-expanded') === 'true') {
        closePanel();
      }
    });

    // Escape key to close
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
        closePanel();
        toggle.focus();
      }
    });

    function openPanel() {
      toggle.setAttribute('aria-expanded', 'true');
      panel.hidden = false;
      panel.style.display = 'block';
      
      // Focus first input
      const firstInput = panel.querySelector('input, select');
      if (firstInput) {
        setTimeout(() => firstInput.focus(), 100);
      }
    }

    function closePanel() {
      toggle.setAttribute('aria-expanded', 'false');
      panel.hidden = true;
      panel.style.display = 'none';
    }
  }

  // Auto-submit filter form on select change (optional)
  function initAutoFilter() {
    const filterForm = document.querySelector('.filter-orb form');
    if (!filterForm) return;

    const selects = filterForm.querySelectorAll('select');
    selects.forEach(select => {
      select.addEventListener('change', () => {
        // Optional: Auto-submit on change
        // Uncomment if you want instant filtering
        // filterForm.submit();
      });
    });
  }

  // Lazy load images
  function initLazyLoading() {
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
      });

      document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
      });

      // Also handle iframes
      document.querySelectorAll('iframe[data-src]').forEach(iframe => {
        imageObserver.observe(iframe);
      });
    } else {
      // Fallback for browsers without IntersectionObserver
      document.querySelectorAll('img[data-src], iframe[data-src]').forEach(el => {
        el.src = el.dataset.src;
        el.removeAttribute('data-src');
      });
    }
  }

  // Countdown timer enhancement
  function initCountdowns() {
    const countdowns = document.querySelectorAll('[data-countdown]');
    
    countdowns.forEach(countdown => {
      const targetISO = countdown.dataset.countdown;
      if (!targetISO) return;

      const targetDate = new Date(targetISO);
      
      const updateCountdown = () => {
        const now = new Date();
        const diff = targetDate - now;

        if (diff <= 0) {
          countdown.innerHTML = '<span class="muted">Started</span>';
          return;
        }

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);

        const dEl = countdown.querySelector('[data-d]');
        const hEl = countdown.querySelector('[data-h]');
        const mEl = countdown.querySelector('[data-m]');
        const sEl = countdown.querySelector('[data-s]');

        if (dEl) dEl.textContent = days;
        if (hEl) hEl.textContent = String(hours).padStart(2, '0');
        if (mEl) mEl.textContent = String(minutes).padStart(2, '0');
        if (sEl) sEl.textContent = String(seconds).padStart(2, '0');
      };

      updateCountdown();
      setInterval(updateCountdown, 1000);
    });
  }

  // Game card hover effects
  function initGameCards() {
    const gameCards = document.querySelectorAll('.dc-game');
    
    gameCards.forEach(card => {
      card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
      });
      
      card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
      });
    });
  }

  // Tournament card animations
  function initCardAnimations() {
    if ('IntersectionObserver' in window) {
      const cardObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
          if (entry.isIntersecting) {
            setTimeout(() => {
              entry.target.style.opacity = '1';
              entry.target.style.transform = 'translateY(0)';
            }, index * 50);
            cardObserver.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.1
      });

      document.querySelectorAll('.dc-card, .dc-game, .vp-card').forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        cardObserver.observe(card);
      });
    }
  }

  // Share functionality
  function initShareButtons() {
    document.querySelectorAll('[data-share]').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        
        const shareData = {
          title: document.title,
          url: window.location.href
        };

        if (navigator.share) {
          try {
            await navigator.share(shareData);
          } catch (err) {
            if (err.name !== 'AbortError') {
              fallbackShare();
            }
          }
        } else {
          fallbackShare();
        }
      });
    });

    function fallbackShare() {
      const url = window.location.href;
      const textarea = document.createElement('textarea');
      textarea.value = url;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      
      try {
        document.execCommand('copy');
        showToast('Link copied to clipboard!');
      } catch (err) {
        console.error('Failed to copy:', err);
      }
      
      document.body.removeChild(textarea);
    }
  }

  // Simple toast notification
  function showToast(message, duration = 3000) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: var(--bg-2);
      color: var(--text);
      padding: 12px 20px;
      border-radius: 12px;
      border: 1px solid var(--border);
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      z-index: 1000;
      animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'slideOut 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // Add CSS animations for toast
  function addToastStyles() {
    if (document.getElementById('toast-styles')) return;

    const style = document.createElement('style');
    style.id = 'toast-styles';
    style.textContent = `
      @keyframes slideIn {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
      
      @keyframes slideOut {
        from {
          transform: translateX(0);
          opacity: 1;
        }
        to {
          transform: translateX(100%);
          opacity: 0;
        }
      }
    `;
    document.head.appendChild(style);
  }

  // Initialize everything when DOM is ready
  function init() {
    initSmoothScroll();
    initFilterOrb();
    initAutoFilter();
    initLazyLoading();
    initCountdowns();
    initGameCards();
    initCardAnimations();
    initShareButtons();
    addToastStyles();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose toast function globally for other scripts
  window.showToast = showToast;

})();
