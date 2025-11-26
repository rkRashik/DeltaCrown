/**
 * FE-T-002 & FE-T-003: Tournament Detail Page JavaScript
 * Purpose: Client-side interactions for tournament detail page
 * Source: Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md
 */

document.addEventListener('DOMContentLoaded', function() {
  dcLog('Tournament detail page initialized');

  // Smooth scroll to sections
  const anchorLinks = document.querySelectorAll('a[href^="#"]');
  anchorLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      const targetId = this.getAttribute('href').substring(1);
      const targetElement = document.getElementById(targetId);
      
      if (targetElement) {
        e.preventDefault();
        targetElement.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
        
        // Update URL hash without jumping
        history.pushState(null, null, `#${targetId}`);
      }
    });
  });

  // CTA button state management (for future HTMX integration)
  const ctaButton = document.querySelector('.cta-card button, .cta-card a');
  if (ctaButton) {
    ctaButton.addEventListener('click', function(e) {
      // Future: Handle registration modal or redirect
      dcLog('CTA clicked:', this.textContent);
    });
  }

  // Countdown timer (if registration closing soon)
  const countdownElement = document.querySelector('[data-countdown]');
  if (countdownElement) {
    const targetDate = new Date(countdownElement.dataset.countdown);
    
    function updateCountdown() {
      const now = new Date();
      const diff = targetDate - now;
      
      if (diff > 0) {
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);
        
        countdownElement.textContent = `${days}d ${hours}h ${minutes}m ${seconds}s`;
      } else {
        countdownElement.textContent = 'Registration closed';
      }
    }
    
    updateCountdown();
    setInterval(updateCountdown, 1000);
  }

  // Share button functionality
  const shareButton = document.querySelector('[data-share]');
  if (shareButton) {
    shareButton.addEventListener('click', function(e) {
      e.preventDefault();
      
      if (navigator.share) {
        navigator.share({
          title: document.title,
          url: window.location.href
        }).catch(err => dcLog('Share failed:', err));
      } else {
        // Fallback: Copy to clipboard
        navigator.clipboard.writeText(window.location.href).then(() => {
          alert('Link copied to clipboard!');
        });
      }
    });
  }

  // Keyboard navigation for tabs (already in tabs.html but reinforced here)
  const tabHeaders = document.querySelectorAll('.tab-header');
  tabHeaders.forEach((header, index) => {
    header.setAttribute('role', 'tab');
    header.setAttribute('tabindex', header.classList.contains('active') ? '0' : '-1');
  });

  // Accessibility: Announce tab changes to screen readers
  const tabPanes = document.querySelectorAll('.tab-pane');
  tabPanes.forEach(pane => {
    pane.setAttribute('role', 'tabpanel');
  });
});
