/**
 * FE-T-001: Tournament Filters JavaScript
 * Purpose: Client-side filter interactions and URL parameter handling
 * Source: Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md
 */

document.addEventListener('DOMContentLoaded', function() {
  // Auto-submit search form on input (with debounce)
  const searchForm = document.getElementById('tournament-search-form');
  const searchInput = searchForm?.querySelector('input[name="search"]');
  
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener('input', function() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        searchForm.submit();
      }, 500); // 500ms debounce
    });
  }

  // Smooth scroll to top when pagination changes
  const paginationLinks = document.querySelectorAll('.pagination-container a');
  paginationLinks.forEach(link => {
    link.addEventListener('click', function(e) {
      // Let the default navigation happen, but smooth scroll first
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  });

  // Update URL without reloading (for future HTMX integration)
  function updateURL(params) {
    const url = new URL(window.location);
    Object.keys(params).forEach(key => {
      if (params[key]) {
        url.searchParams.set(key, params[key]);
      } else {
        url.searchParams.delete(key);
      }
    });
    window.history.pushState({}, '', url);
  }

  // Accessibility: Keyboard navigation for status tabs
  const statusTabs = document.querySelectorAll('.status-filter-tabs a');
  statusTabs.forEach((tab, index) => {
    tab.addEventListener('keydown', function(e) {
      let nextTab;
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        nextTab = statusTabs[index + 1] || statusTabs[0];
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        nextTab = statusTabs[index - 1] || statusTabs[statusTabs.length - 1];
      }
      if (nextTab) {
        nextTab.focus();
      }
    });
  });

  // Loading indicator for form submissions
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', function() {
      // Add loading class to grid
      const grid = document.querySelector('.tournament-grid');
      if (grid) {
        grid.classList.add('htmx-swapping');
      }
    });
  });

  // Clear filters button functionality
  const clearFiltersBtn = document.querySelector('[href*="clear"]');
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', function(e) {
      // Clear all URL parameters
      window.location.href = window.location.pathname;
    });
  }

  dcLog('Tournament filters initialized');
});
