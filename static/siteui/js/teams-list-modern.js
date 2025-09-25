(function () {
  'use strict';

  var THEME_KEY = 'teams-theme';

  function initTheme() {
    var saved = localStorage.getItem(THEME_KEY);
    if (!saved) {
      var prefersDark = false;
      if (window.matchMedia) {
        prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      }
      saved = prefersDark ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', saved);
  }

  function toggleTheme() {
    var root = document.documentElement;
    var current = root.getAttribute('data-theme');
    var next = current === 'light' ? 'dark' : 'light';
    root.setAttribute('data-theme', next);
    localStorage.setItem(THEME_KEY, next);
  }

  function setupThemeToggle() {
    var button = document.getElementById('theme-toggle-btn');
    if (!button) {
      return;
    }
    button.addEventListener('click', function () {
      toggleTheme();
      button.classList.add('is-active');
      window.setTimeout(function () {
        button.classList.remove('is-active');
      }, 180);
    });
  }

  function debounce(fn, wait) {
    var timeoutId;
    return function () {
      var args = arguments;
      window.clearTimeout(timeoutId);
      timeoutId = window.setTimeout(function () {
        fn.apply(null, args);
      }, wait);
    };
  }

  function setupFilterForm() {
    var form = document.getElementById('teams-filter-form');
    if (!form) {
      return;
    }

    var submitForm = function () {
      var pageInput = form.querySelector('input[name="page"]');
      if (pageInput) {
        pageInput.parentNode.removeChild(pageInput);
      }
      form.submit();
    };

    var debouncedSubmit = debounce(submitForm, 450);

    form.querySelectorAll('[data-auto-submit="change"]').forEach(function (el) {
      el.addEventListener('change', submitForm);
    });

    form.querySelectorAll('[data-auto-submit="toggle"]').forEach(function (el) {
      el.addEventListener('change', submitForm);
    });

    form.querySelectorAll('[data-auto-submit="debounced"]').forEach(function (el) {
      el.addEventListener('input', debouncedSubmit);
      el.addEventListener('keydown', function (event) {
        if (event.key === 'Enter') {
          event.preventDefault();
          submitForm();
        }
      });
    });
  }

  function setupCardInteractions() {
    var cards = document.querySelectorAll('.team-card-modern');
    cards.forEach(function (card) {
      card.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
          var link = card.querySelector('.team-card-link');
          if (link) {
            event.preventDefault();
            link.click();
          }
        }
      });
    });
  }

  // Modern AJAX pagination with smooth loading
  function setupAsyncPagination() {
    var teamsContainer = document.querySelector('.teams-rankings');
    var paginationContainer = document.querySelector('.pagination-container');
    
    if (!teamsContainer || !paginationContainer) {
      return;
    }

    // Create loading overlay
    function createLoadingOverlay() {
      var overlay = document.createElement('div');
      overlay.className = 'loading-overlay';
      overlay.innerHTML = `
        <div class="loading-spinner">
          <div class="spinner"></div>
          <span class="loading-text">Loading teams...</span>
        </div>
      `;
      return overlay;
    }

    // Add loading state
    function showLoading() {
      var overlay = createLoadingOverlay();
      teamsContainer.style.position = 'relative';
      teamsContainer.appendChild(overlay);
      
      // Smooth fade in
      requestAnimationFrame(() => {
        overlay.style.opacity = '1';
      });
    }

    // Remove loading state
    function hideLoading() {
      var overlay = teamsContainer.querySelector('.loading-overlay');
      if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(() => {
          if (overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
          }
        }, 200);
      }
    }

    // Handle async navigation
    function handleAsyncNavigation(url, event) {
      event.preventDefault();
      
      // Update URL without page refresh
      if (window.history && window.history.pushState) {
        window.history.pushState({}, '', url);
      }
      
      showLoading();
      
      fetch(url, {
        method: 'GET',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'text/html'
        }
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.text();
      })
      .then(html => {
        // Create temporary container to parse response
        var temp = document.createElement('div');
        temp.innerHTML = html;
        
        // Extract teams rankings and pagination
        var newTeamsRankings = temp.querySelector('.teams-rankings');
        var newPagination = temp.querySelector('.pagination-container');
        
        if (newTeamsRankings && newPagination) {
          // Smooth fade out current content
          var currentRankings = teamsContainer;
          if (currentRankings) {
            currentRankings.style.opacity = '0';
            currentRankings.style.transform = 'translateY(10px)';
            
            setTimeout(() => {
              // Replace content
              currentRankings.parentNode.replaceChild(newTeamsRankings, currentRankings);
              paginationContainer.innerHTML = newPagination.innerHTML;
              
              // Setup new pagination links
              setupPaginationLinks();
              setupCardInteractions();
              
              // Smooth fade in new content
              newTeamsRankings.style.opacity = '0';
              newTeamsRankings.style.transform = 'translateY(10px)';
              
              requestAnimationFrame(() => {
                newTeamsRankings.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                newTeamsRankings.style.opacity = '1';
                newTeamsRankings.style.transform = 'translateY(0)';
              });
              
              hideLoading();
              
              // Smooth scroll to top of teams container
              document.querySelector('.teams-list-container').scrollIntoView({
                behavior: 'smooth',
                block: 'start'
              });
            }, 150);
          }
        }
      })
      .catch(error => {
        console.error('Error loading page:', error);
        hideLoading();
        
        // Fallback to normal navigation
        window.location.href = url;
      });
    }

    // Setup pagination link handlers
    function setupPaginationLinks() {
      var paginationLinks = document.querySelectorAll('[data-async="true"]');
      paginationLinks.forEach(function(link) {
        link.addEventListener('click', function(event) {
          handleAsyncNavigation(this.href, event);
        });
      });
    }

    // Initialize pagination
    setupPaginationLinks();

    // Handle browser back/forward buttons
    window.addEventListener('popstate', function(event) {
      window.location.reload();
    });
  }

  // Enhanced smooth scrolling for all navigation
  function setupSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      });
    });
  }

  // Performance optimization: Intersection Observer for lazy loading
  function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
      const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            const src = img.dataset.src;
            if (src) {
              img.src = src;
              img.classList.add('loaded');
              observer.unobserve(img);
            }
          }
        });
      });

      document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
      });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    initTheme();
    setupThemeToggle();
    setupFilterForm();
    setupCardInteractions();
    setupAsyncPagination();
    setupSmoothScrolling();
    setupLazyLoading();
  });
})();
