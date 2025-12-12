/**
 * About Page Interactivity
 * 
 * Features:
 * - Tab system for "Who It's For" section
 * - Animated count-up numbers on scroll
 * - Smooth transitions and accessibility
 */

(function() {
  'use strict';

  // ============================================
  // TAB SYSTEM
  // ============================================
  
  function initTabSystem() {
    const tabButtons = document.querySelectorAll('.stakeholder-tab');
    const tabPanels = document.querySelectorAll('.tab-panel');
    
    if (!tabButtons.length || !tabPanels.length) return;

    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const targetTab = button.getAttribute('data-tab');
        
        // Update button states
        tabButtons.forEach(btn => {
          btn.classList.remove('border-orange-500', 'border-cyan-500', 'border-green-500', 'border-purple-500', 'bg-gray-800');
          btn.classList.add('border-transparent', 'text-gray-400');
          btn.setAttribute('aria-selected', 'false');
        });
        
        // Activate clicked button
        button.classList.remove('border-transparent', 'text-gray-400');
        button.classList.add('bg-gray-800');
        button.setAttribute('aria-selected', 'true');
        
        // Set appropriate color based on tab
        const colorMap = {
          'players': 'border-orange-500 text-orange-400',
          'teams': 'border-cyan-500 text-cyan-400',
          'organizers': 'border-green-500 text-green-400',
          'sponsors': 'border-purple-500 text-purple-400'
        };
        
        const colors = colorMap[targetTab].split(' ');
        button.classList.add(...colors);
        
        // Update panel visibility
        tabPanels.forEach(panel => {
          if (panel.id === `panel-${targetTab}`) {
            panel.classList.remove('hidden');
            panel.classList.add('animate-fadeIn');
          } else {
            panel.classList.add('hidden');
          }
        });
      });

      // Keyboard navigation
      button.addEventListener('keydown', (e) => {
        let targetButton = null;
        
        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
          e.preventDefault();
          targetButton = button.previousElementSibling || tabButtons[tabButtons.length - 1];
        } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
          e.preventDefault();
          targetButton = button.nextElementSibling || tabButtons[0];
        } else if (e.key === 'Home') {
          e.preventDefault();
          targetButton = tabButtons[0];
        } else if (e.key === 'End') {
          e.preventDefault();
          targetButton = tabButtons[tabButtons.length - 1];
        }
        
        if (targetButton) {
          targetButton.focus();
          targetButton.click();
        }
      });
    });
  }

  // ============================================
  // ANIMATED COUNTERS
  // ============================================
  
  function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16); // 60fps
    let current = start;
    
    const timer = setInterval(() => {
      current += increment;
      if (current >= target) {
        element.textContent = target;
        clearInterval(timer);
      } else {
        element.textContent = Math.floor(current);
      }
    }, 16);
  }

  function initCounters() {
    const counters = document.querySelectorAll('.counter');
    if (!counters.length) return;

    const observerOptions = {
      threshold: 0.5,
      rootMargin: '0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && !entry.target.classList.contains('counted')) {
          const target = parseInt(entry.target.getAttribute('data-target'));
          animateCounter(entry.target, target);
          entry.target.classList.add('counted');
        }
      });
    }, observerOptions);

    counters.forEach(counter => observer.observe(counter));
  }

  // ============================================
  // SCROLL REVEAL ANIMATIONS
  // ============================================
  
  function initScrollReveal() {
    const revealElements = document.querySelectorAll('.glass-card, .timeline-step');
    if (!revealElements.length) return;

    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '0';
          entry.target.style.transform = 'translateY(30px)';
          
          setTimeout(() => {
            entry.target.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
          }, 100);
          
          observer.unobserve(entry.target);
        }
      });
    }, observerOptions);

    revealElements.forEach(el => observer.observe(el));
  }

  // ============================================
  // SMOOTH SCROLL FOR ANCHOR LINKS
  // ============================================
  
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href === '#') return;
        
        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      });
    });
  }

  // ============================================
  // INITIALIZATION
  // ============================================
  
  function init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
      return;
    }

    // Only run on about page
    if (!document.getElementById('about-page')) return;

    console.log('🎮 About page interactivity initialized');

    // Initialize all features
    initTabSystem();
    initCounters();
    initScrollReveal();
    initSmoothScroll();
  }

  // Start initialization
  init();

})();
