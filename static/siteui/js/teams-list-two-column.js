/**
 * Professional Two-Column Team Rankings Page
 * Enhanced with Professional Sorting Controls and Compact Design
 */

class TeamsPage {
  constructor() {
    this.currentPage = 1;
    this.loading = false;
    this.hasMorePages = true;
    this.searchTimeout = null;
    this.currentFilters = this.getUrlParams();
    
    this.init();
  }

  init() {
    this.bindEvents();
    this.setupInfiniteScroll();
    this.setupSearch();
    this.setupMobileSidebar();
    this.setupAccessibility();
    this.setupThemeToggle();
    this.setupExpandableFilters();
    this.initializeView();
  }

  // Event Bindings
  bindEvents() {
    // Load More Button
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', () => this.loadMoreTeams());
    }

    // Sort Select
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
      sortSelect.addEventListener('change', (e) => this.handleSortChange(e));
    }

    // Game Filter Links
    const gameFilters = document.querySelectorAll('.game-filter-item');
    gameFilters.forEach(filter => {
      filter.addEventListener('click', (e) => this.handleGameFilter(e));
    });

    // Mobile Sidebar Toggle
    const mobileToggle = document.getElementById('mobile-sidebar-toggle');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const sidebarClose = document.getElementById('sidebar-close');

    if (mobileToggle) {
      mobileToggle.addEventListener('click', () => this.toggleMobileSidebar(true));
    }
    
    if (sidebarOverlay) {
      sidebarOverlay.addEventListener('click', () => this.toggleMobileSidebar(false));
    }
    
    if (sidebarClose) {
      sidebarClose.addEventListener('click', () => this.toggleMobileSidebar(false));
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));

    // Game filter toggle
    const gameFilterToggle = document.getElementById('game-filter-toggle');
    if (gameFilterToggle) {
      gameFilterToggle.addEventListener('click', () => this.toggleGameFilters());
    }

    // Theme toggle - REMOVED (using unified navigation theme toggle)
    // const themeToggle = document.getElementById('theme-toggle');
    // if (themeToggle) {
    //   themeToggle.addEventListener('click', () => this.toggleTheme());
    // }
  }

  // Enhanced Search Setup with Professional Controls
  setupSearch() {
    const searchInput = document.getElementById('team-search');
    if (!searchInput) return;

    // Real-time search with debouncing
    searchInput.addEventListener('input', (e) => {
      clearTimeout(this.searchTimeout);
      const query = e.target.value.trim();
      
      // Show/hide clear button
      const clearBtn = document.getElementById('search-clear');
      if (clearBtn) {
        clearBtn.style.display = query ? 'block' : 'none';
      }
      
      this.searchTimeout = setTimeout(() => {
        this.currentFilters.q = query;
        this.performSearch();
      }, 300); // 300ms debounce
    });

    // Handle Enter key
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        clearTimeout(this.searchTimeout);
        this.currentFilters.q = e.target.value.trim();
        this.performSearch();
      }
    });

    // Clear search button
    const clearBtn = document.getElementById('search-clear');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearBtn.style.display = 'none';
        this.currentFilters.q = '';
        this.performSearch();
        searchInput.focus();
      });
    }

    // Sort direction toggle
    const sortToggle = document.getElementById('sort-direction-toggle');
    if (sortToggle) {
      sortToggle.addEventListener('click', () => {
        this.toggleSortDirection();
      });
    }

    // View toggle buttons
    const viewToggles = document.querySelectorAll('.view-toggle');
    viewToggles.forEach(toggle => {
      toggle.addEventListener('click', (e) => {
        const viewType = e.target.closest('.view-toggle').dataset.view;
        this.changeView(viewType);
      });
    });
  }

  // Perform search and update results
  async performSearch() {
    this.showLoading(true);
    
    try {
      const params = new URLSearchParams(this.currentFilters);
      const response = await fetch(`${window.location.pathname}?${params}`, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'text/html'
        }
      });

      if (response.ok) {
        const html = await response.text();
        this.updateTeamList(html);
        this.updateUrl(this.currentFilters);
        this.currentPage = 1;
        this.hasMorePages = true;
      }
    } catch (error) {
      console.error('Search failed:', error);
      this.showErrorMessage('Search failed. Please try again.');
    } finally {
      this.showLoading(false);
    }
  }

  // Handle professional sort changes
  handleSortChange(e) {
    const sortValue = e.target.value;
    
    // Parse sort type and direction from the value
    if (sortValue.includes('_')) {
      const [sortField, direction] = sortValue.split('_');
      this.currentFilters.sort = this.mapSortField(sortField);
      this.currentFilters.order = direction === 'high' ? 'desc' : 'asc';
    } else {
      // Fallback for legacy sort values
      this.currentFilters.sort = sortValue;
      this.currentFilters.order = 'desc';
    }
    
    this.updateSortDirectionIcon();
    this.performSearch();
  }

  // Map sort field names for backend compatibility
  mapSortField(field) {
    const fieldMap = {
      'rank': 'powerrank',
      'points': 'points',
      'members': 'members',
      'name': 'az',
      'newest': 'recent',
      'oldest': 'recent'
    };
    return fieldMap[field] || field;
  }

  // Toggle sort direction
  toggleSortDirection() {
    this.currentFilters.order = this.currentFilters.order === 'asc' ? 'desc' : 'asc';
    this.updateSortDirectionIcon();
    this.performSearch();
  }

  // Update sort direction icon
  updateSortDirectionIcon() {
    const toggle = document.getElementById('sort-direction-toggle');
    const icon = document.getElementById('sort-direction-icon');
    
    if (toggle && icon) {
      toggle.className = `sort-direction-toggle ${this.currentFilters.order || 'desc'}`;
      
      if (this.currentFilters.order === 'asc') {
        icon.className = 'fas fa-sort-amount-up';
        toggle.setAttribute('title', 'Sort: Low to High');
      } else {
        icon.className = 'fas fa-sort-amount-down';
        toggle.setAttribute('title', 'Sort: High to Low');
      }
    }
  }

  // Change view type (grid/list)
  changeView(viewType) {
    const toggles = document.querySelectorAll('.view-toggle');
    const teamList = document.getElementById('team-list-container');
    
    // Update active state
    toggles.forEach(toggle => {
      toggle.classList.toggle('active', toggle.dataset.view === viewType);
    });
    
    // Apply view class to team list
    if (teamList) {
      teamList.className = teamList.className.replace(/view-\w+/g, '');
      teamList.classList.add(`view-${viewType}`);
    }
    
    // Store preference
    localStorage.setItem('teams-view-preference', viewType);
  }

  // Initialize view from saved preference
  initializeView() {
    const savedView = localStorage.getItem('teams-view-preference') || 'list';
    this.changeView(savedView);
    this.updateSortDirectionIcon();
  }

  // Handle game filter clicks
  handleGameFilter(e) {
    e.preventDefault();
    const gameCode = e.currentTarget.dataset.game;
    
    // Update active state
    document.querySelectorAll('.game-filter-item').forEach(item => {
      item.classList.remove('active');
    });
    e.currentTarget.classList.add('active');
    
    // Update filters
    this.currentFilters.game = gameCode;
    this.performSearch();
    
    // Close mobile sidebar if open
    if (window.innerWidth <= 1024) {
      this.toggleMobileSidebar(false);
    }
  }

  // Infinite Scroll Setup
  setupInfiniteScroll() {
    const container = document.getElementById('team-list-container');
    if (!container) return;

    // Use Intersection Observer for better performance
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && this.hasMorePages && !this.loading) {
          const loadMoreBtn = document.getElementById('load-more-btn');
          if (loadMoreBtn && entry.target === loadMoreBtn) {
            this.loadMoreTeams();
          }
        }
      });
    }, {
      root: container,
      rootMargin: '100px'
    });

    // Observe the load more button
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
      observer.observe(loadMoreBtn);
    }
  }

  // Load More Teams (AJAX)
  async loadMoreTeams() {
    if (this.loading || !this.hasMorePages) return;
    
    this.loading = true;
    this.showLoadMoreLoading(true);
    
    try {
      const nextPage = this.currentPage + 1;
      const params = new URLSearchParams({
        ...this.currentFilters,
        page: nextPage
      });
      
      const response = await fetch(`${window.location.pathname}?${params}`, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'Accept': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.teams && data.teams.length > 0) {
          this.appendTeams(data.teams);
          this.currentPage = nextPage;
          this.hasMorePages = data.has_next;
          
          if (!data.has_next) {
            this.hideLoadMoreButton();
          }
        } else {
          this.hasMorePages = false;
          this.hideLoadMoreButton();
        }
      }
    } catch (error) {
      console.error('Load more failed:', error);
      this.showErrorMessage('Failed to load more teams. Please try again.');
    } finally {
      this.loading = false;
      this.showLoadMoreLoading(false);
    }
  }

  // Utility Methods
  getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    return Object.fromEntries(params.entries());
  }

  updateUrl(filters) {
    const url = new URL(window.location);
    url.search = new URLSearchParams(filters).toString();
    window.history.pushState({}, '', url);
  }

  updateTeamList(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const newTeamList = doc.querySelector('#team-list');
    const currentTeamList = document.getElementById('team-list');
    
    if (newTeamList && currentTeamList) {
      currentTeamList.innerHTML = newTeamList.innerHTML;
      this.setupInfiniteScroll(); // Re-setup observers
    }
  }

  appendTeams(teams) {
    const teamList = document.getElementById('team-list');
    if (!teamList) return;
    
    teams.forEach(team => {
      const teamElement = this.createTeamElement(team);
      teamList.appendChild(teamElement);
    });
  }

  createTeamElement(team) {
    const div = document.createElement('div');
    div.className = 'team-card';
    div.innerHTML = `
      <div class="team-header">
        <div class="team-rank ${team.rank <= 3 ? 'top-3' : ''}">${team.rank}</div>
        ${team.logo ? 
          `<img src="${team.logo}" alt="${team.name} logo" class="team-logo">` :
          `<div class="team-logo-placeholder">${team.name.charAt(0).toUpperCase()}</div>`
        }
        <div class="team-info">
          <h2 class="team-name">${team.name}</h2>
          ${team.tag ? `<div class="team-tag">[${team.tag}]</div>` : ''}
          ${team.game ? `<div class="team-game-badge"><span>${team.game}</span></div>` : ''}
        </div>
      </div>
      <div class="team-stats">
        <div class="team-stat-item">
          <div class="team-stat-value">${team.members_count}</div>
          <div class="team-stat-label">Members</div>
        </div>
        <div class="team-stat-item">
          <div class="team-stat-value">${team.total_points}</div>
          <div class="team-stat-label">Points</div>
        </div>
      </div>
      <div class="team-actions">
        <a href="/teams/${team.slug}/" class="team-action-btn primary">View Team</a>
      </div>
    `;
    return div;
  }

  // Loading and UI State Methods
  showLoading(show) {
    const loadingIndicator = document.getElementById('search-loading');
    if (loadingIndicator) {
      loadingIndicator.style.display = show ? 'block' : 'none';
    }
  }

  showLoadMoreLoading(show) {
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
      loadMoreBtn.textContent = show ? 'Loading...' : 'Load More Teams';
      loadMoreBtn.disabled = show;
    }
  }

  hideLoadMoreButton() {
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
      loadMoreBtn.style.display = 'none';
    }
  }

  showErrorMessage(message) {
    // Create or update error message
    let errorDiv = document.getElementById('error-message');
    if (!errorDiv) {
      errorDiv = document.createElement('div');
      errorDiv.id = 'error-message';
      errorDiv.className = 'error-message';
      document.querySelector('.right-content').prepend(errorDiv);
    }
    
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
      errorDiv.style.display = 'none';
    }, 5000);
  }

  // Mobile Sidebar Management
  setupMobileSidebar() {
    // Handle window resize
    window.addEventListener('resize', () => {
      if (window.innerWidth > 1024) {
        this.toggleMobileSidebar(false);
      }
    });
  }

  toggleMobileSidebar(show) {
    const sidebar = document.getElementById('left-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    if (sidebar && overlay) {
      if (show) {
        sidebar.classList.add('mobile-open');
        overlay.style.display = 'block';
        document.body.style.overflow = 'hidden';
      } else {
        sidebar.classList.remove('mobile-open');
        overlay.style.display = 'none';
        document.body.style.overflow = '';
      }
    }
  }

  // Accessibility Setup
  setupAccessibility() {
    // Add ARIA labels and keyboard navigation
    const searchInput = document.getElementById('team-search');
    if (searchInput) {
      searchInput.setAttribute('aria-describedby', 'search-help');
    }

    // Handle focus management for modal/sidebar
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.toggleMobileSidebar(false);
      }
    });
  }

  // Theme Toggle Setup
  setupThemeToggle() {
    // Apply saved theme on load
    const savedTheme = localStorage.getItem('theme-preference');
    if (savedTheme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else if (savedTheme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    }
    // If no saved preference, respect system preference
  }

  // Toggle Theme Method - REMOVED (using unified navigation theme toggle)
  /*
  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme-preference', newTheme);
    
    // Add transition effect
    document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    setTimeout(() => {
      document.body.style.transition = '';
    }, 300);
  }
  */

  // Expandable Filters Setup
  setupExpandableFilters() {
    // Initialize filters in expanded state
    const gameFilters = document.getElementById('game-filters');
    if (gameFilters) {
      gameFilters.classList.add('expanded');
    }
  }

  // Toggle Game Filters
  toggleGameFilters() {
    const toggle = document.getElementById('game-filter-toggle');
    const filters = document.getElementById('game-filters');
    
    if (!toggle || !filters) return;
    
    const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
    const newExpanded = !isExpanded;
    
    toggle.setAttribute('aria-expanded', newExpanded.toString());
    
    if (newExpanded) {
      filters.classList.add('expanded');
    } else {
      filters.classList.remove('expanded');
    }
  }

  // Keyboard Shortcuts
  handleKeyboardShortcuts(e) {
    // Ctrl+K or Cmd+K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      const searchInput = document.getElementById('team-search');
      if (searchInput) {
        searchInput.focus();
      }
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('teams-page-container')) {
    new TeamsPage();
  }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TeamsPage;
}