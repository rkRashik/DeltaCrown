/**
 * 🎮 TEAMS LIST MANAGER - MOBILE-FIRST JAVASCRIPT 🎮
 * Clean, professional JavaScript for teams listing with mobile optimization
 * Version: 2.0 - Completely rewritten for better functionality
 */

class TeamsListManager {
  constructor() {
    this.isMobile = window.innerWidth < 768;
    this.searchTimeout = null;
    this.activeOverlay = null;
    
    // Initialize immediately
    this.init();
    
    console.log('✅ Teams List Manager initialized successfully');
  }

  init() {
    this.setupSearch();
    this.setupMobileNavigation();
    this.setupFilters();
    this.setupTeamInteractions();
    this.setupResponsiveHandlers();
    this.setupKeyboardNavigation();
    this.setupRulesToggle();
  }

  /**
   * SEARCH FUNCTIONALITY
   */
  setupSearch() {
    // Desktop search
    const desktopSearchInput = document.getElementById('q');
    if (desktopSearchInput) {
      desktopSearchInput.addEventListener('input', this.handleSearch.bind(this));
    }

    // Mobile search
    const mobileSearchInput = document.getElementById('mobile-search');
    if (mobileSearchInput) {
      mobileSearchInput.addEventListener('input', this.handleMobileSearch.bind(this));
    }

    // Mobile search button
    const mobileSearchBtn = document.querySelector('.mobile-search-btn');
    if (mobileSearchBtn) {
      mobileSearchBtn.addEventListener('click', this.handleMobileSearchSubmit.bind(this));
    }

    // Form submissions
    const searchForm = document.getElementById('teams-search-form');
    if (searchForm) {
      searchForm.addEventListener('submit', this.handleFormSubmit.bind(this));
    }
  }

  handleSearch(event) {
    const query = event.target.value;
    
    // Debounce search
    clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
      this.performSearch(query);
    }, 300);
  }

  handleMobileSearch(event) {
    const query = event.target.value;
    
    // Update desktop search input if exists
    const desktopInput = document.getElementById('q');
    if (desktopInput && desktopInput.value !== query) {
      desktopInput.value = query;
    }

    // Perform search with debounce
    clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
      this.performSearch(query);
    }, 300);
  }

  handleMobileSearchSubmit(event) {
    event.preventDefault();
    const mobileInput = document.getElementById('mobile-search');
    if (mobileInput) {
      this.performSearch(mobileInput.value);
    }
  }

  performSearch(query) {
    // Get current form data
    const form = document.getElementById('teams-search-form');
    if (!form) return;

    const formData = new FormData(form);
    formData.set('q', query);

    // Build URL with parameters
    const params = new URLSearchParams(formData);
    const newUrl = `${window.location.pathname}?${params.toString()}`;

    // Navigate to new URL (this will reload the page with search results)
    window.location.href = newUrl;
  }

  handleFormSubmit(event) {
    // Allow normal form submission
    console.log('🔍 Form submitted');
  }

  /**
   * MOBILE NAVIGATION
   */
  setupMobileNavigation() {
    // Mobile filter buttons
    const filterButtons = document.querySelectorAll('.mobile-filter-btn');
    filterButtons.forEach(button => {
      button.addEventListener('click', this.handleMobileFilterClick.bind(this));
    });

    // Mobile overlay close buttons
    const closeButtons = document.querySelectorAll('.mobile-overlay-close');
    closeButtons.forEach(button => {
      button.addEventListener('click', this.closeMobileOverlay.bind(this));
    });

    // Sidebar toggle for mobile
    const sidebarToggle = document.getElementById('toggle-sidebar');
    if (sidebarToggle) {
      sidebarToggle.addEventListener('click', this.toggleMobileSidebar.bind(this));
    }

    // Sidebar close button
    const sidebarClose = document.getElementById('sidebar-close');
    if (sidebarClose) {
      sidebarClose.addEventListener('click', this.closeMobileSidebar.bind(this));
    }

    // Backdrop click to close overlays
    const backdrop = document.getElementById('mobile-backdrop');
    if (backdrop) {
      backdrop.addEventListener('click', this.closeMobileOverlay.bind(this));
    }

    const sidebarOverlay = document.getElementById('sidebar-overlay');
    if (sidebarOverlay) {
      sidebarOverlay.addEventListener('click', this.closeMobileSidebar.bind(this));
    }
  }

  handleMobileFilterClick(event) {
    const button = event.currentTarget;
    const filterType = button.dataset.filter;

    if (filterType === 'actions') {
      this.showMobileOverlay('actions-overlay');
    } else if (filterType === 'game') {
      this.showMobileOverlay('game-overlay');
    } else if (filterType === 'sort') {
      this.showMobileOverlay('sort-overlay');
    }

    // Add active state
    document.querySelectorAll('.mobile-filter-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    button.classList.add('active');
  }

  showMobileOverlay(overlayId) {
    const overlay = document.getElementById(overlayId);
    
    if (overlay) {
      // Close any existing overlay first
      this.closeMobileOverlay();
      
      this.activeOverlay = overlay;
      
      // Add active state with smooth animation
      requestAnimationFrame(() => {
        overlay.classList.add('active');
        
        // Add haptic feedback on supported devices
        if (navigator.vibrate) {
          navigator.vibrate(50);
        }
      });
      
      // Prevent body scrolling
      document.body.style.overflow = 'hidden';
      
      // Focus trap for accessibility
      this.trapFocus(overlay);
      
      // Add escape key listener
      this.addEscapeListener();
    }
  }

  closeMobileOverlay() {
    if (this.activeOverlay) {
      // Add closing animation
      this.activeOverlay.classList.add('closing');
      
      setTimeout(() => {
        this.activeOverlay.classList.remove('active', 'closing');
        this.activeOverlay = null;
      }, 200);
    }

    // Restore body scrolling
    document.body.style.overflow = '';

    // Remove active state from filter buttons with animation
    document.querySelectorAll('.mobile-filter-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    
    // Remove escape listener
    this.removeEscapeListener();
  }

  trapFocus(element) {
    const focusableElements = element.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }
  }

  addEscapeListener() {
    this.escapeHandler = (e) => {
      if (e.key === 'Escape') {
        this.closeMobileOverlay();
      }
    };
    document.addEventListener('keydown', this.escapeHandler);
  }

  removeEscapeListener() {
    if (this.escapeHandler) {
      document.removeEventListener('keydown', this.escapeHandler);
      this.escapeHandler = null;
    }
  }

  toggleMobileSidebar() {
    const sidebar = document.getElementById('teams-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    if (sidebar && overlay) {
      sidebar.classList.add('active');
      overlay.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  }

  closeMobileSidebar() {
    const sidebar = document.getElementById('teams-sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    
    if (sidebar && overlay) {
      sidebar.classList.remove('active');
      overlay.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  /**
   * FILTER FUNCTIONALITY
   */
  setupFilters() {
    // Desktop filter selects
    const gameSelect = document.getElementById('game');
    const sortSelect = document.getElementById('sort');

    if (gameSelect) {
      gameSelect.addEventListener('change', this.handleFilterChange.bind(this));
    }

    if (sortSelect) {
      sortSelect.addEventListener('change', this.handleFilterChange.bind(this));
    }

    // Mobile filter options
    const mobileFilterOptions = document.querySelectorAll('.mobile-filter-option');
    mobileFilterOptions.forEach(option => {
      option.addEventListener('click', this.handleMobileFilterSelect.bind(this));
    });

    // Sidebar filter links
    const filterLinks = document.querySelectorAll('.filter-option');
    filterLinks.forEach(link => {
      link.addEventListener('click', this.handleSidebarFilterClick.bind(this));
    });
  }

  handleFilterChange(event) {
    // Submit form when filter changes
    const form = document.getElementById('teams-search-form');
    if (form) {
      form.submit();
    }
  }

  handleMobileFilterSelect(event) {
    event.preventDefault();
    const option = event.currentTarget;
    const value = option.dataset.value;
    const overlayId = option.closest('.mobile-overlay').id;

    // Update corresponding form field
    if (overlayId === 'game-overlay') {
      const gameSelect = document.getElementById('game');
      if (gameSelect) {
        gameSelect.value = value;
        this.handleFilterChange({ target: gameSelect });
      }
    } else if (overlayId === 'sort-overlay') {
      const sortSelect = document.getElementById('sort');
      if (sortSelect) {
        sortSelect.value = value;
        this.handleFilterChange({ target: sortSelect });
      }
    }

    this.closeMobileOverlay();
  }

  handleSidebarFilterClick(event) {
    // Allow normal navigation for sidebar links
    console.log('📊 Sidebar filter clicked:', event.currentTarget.textContent);
  }

  /**
   * TEAM INTERACTIONS
   */
  setupTeamInteractions() {
    // Team row clicks
    const teamRows = document.querySelectorAll('.team-row');
    teamRows.forEach(row => {
      row.addEventListener('click', this.handleTeamRowClick.bind(this));
    });

    // Action button clicks (prevent event bubbling)
    const actionButtons = document.querySelectorAll('.team-actions a, .team-actions button');
    actionButtons.forEach(button => {
      button.addEventListener('click', this.handleActionClick.bind(this));
    });

    // Add loading states to action buttons
    const viewButtons = document.querySelectorAll('.btn-view');
    const applyButtons = document.querySelectorAll('.btn-apply');
    
    viewButtons.forEach(button => {
      button.addEventListener('click', this.addLoadingState.bind(this));
    });
    
    applyButtons.forEach(button => {
      button.addEventListener('click', this.addLoadingState.bind(this));
    });
  }

  handleTeamRowClick(event) {
    // Don't navigate if clicking on action buttons
    if (event.target.closest('.team-actions')) {
      return;
    }

    const row = event.currentTarget;
    const teamId = row.dataset.teamId;
    
    if (teamId) {
      // Add visual feedback
      row.style.transform = 'scale(0.98)';
      row.style.transition = 'transform 0.1s ease';
      
      setTimeout(() => {
        row.style.transform = '';
      }, 100);

      // Navigate to team detail (you'll need to implement this based on your URL structure)
      console.log('🏆 Navigate to team:', teamId);
    }
  }

  handleActionClick(event) {
    // Prevent event bubbling to team row
    event.stopPropagation();
    console.log('🎯 Action clicked:', event.currentTarget.textContent);
  }

  addLoadingState(event) {
    const button = event.currentTarget;
    const originalText = button.innerHTML;
    
    // Add loading state
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    button.disabled = true;
    
    // Remove loading state after 2 seconds (adjust based on your needs)
    setTimeout(() => {
      button.innerHTML = originalText;
      button.disabled = false;
    }, 2000);
  }

  /**
   * RESPONSIVE HANDLING
   */
  setupResponsiveHandlers() {
    window.addEventListener('resize', this.handleResize.bind(this));
    this.handleResize(); // Initial check
  }

  handleResize() {
    const wasMobile = this.isMobile;
    this.isMobile = window.innerWidth < 768;

    // Close overlays when switching to desktop
    if (wasMobile && !this.isMobile) {
      this.closeMobileOverlay();
      this.closeMobileSidebar();
    }

    // Update mobile navbar visibility
    this.updateMobileNavbar();
  }

  updateMobileNavbar() {
    const mobileNavbar = document.querySelector('.mobile-second-navbar');
    if (mobileNavbar) {
      mobileNavbar.style.display = this.isMobile ? 'block' : 'none';
    }
  }

  /**
   * KEYBOARD NAVIGATION
   */
  setupKeyboardNavigation() {
    document.addEventListener('keydown', this.handleKeyDown.bind(this));
  }

  handleKeyDown(event) {
    // Escape key to close overlays
    if (event.key === 'Escape') {
      this.closeMobileOverlay();
      this.closeMobileSidebar();
    }

    // Enter key on team rows
    if (event.key === 'Enter' && event.target.classList.contains('team-row')) {
      event.target.click();
    }
  }

  /**
   * RULES SECTION TOGGLE (Sidebar Version)
   */
  setupRulesToggle() {
    const rulesToggle = document.getElementById('rules-toggle');
    const rulesContent = document.getElementById('rules-content');
    
    if (!rulesToggle || !rulesContent) return;
    
    // Set initial state - collapsed by default (inline style sets display: none)
    rulesToggle.classList.remove('active');
    
    // Toggle handler
    const toggleRules = () => {
      const isHidden = rulesContent.style.display === 'none';
      
      if (isHidden) {
        // Expand
        rulesContent.style.display = 'block';
        rulesContent.classList.add('show');
        rulesToggle.classList.add('active');
      } else {
        // Collapse
        rulesContent.style.display = 'none';
        rulesContent.classList.remove('show');
        rulesToggle.classList.remove('active');
      }
    };
    
    // Event listeners
    rulesToggle.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleRules();
    });
    
    // Keyboard support
    rulesToggle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleRules();
      }
    });
  }

  /**
   * LEGACY RULES TOGGLE (if needed for other pages)
   */
  setupLegacyRulesToggle() {
    const rulesToggle = document.querySelector('.ranking-rules-section .rules-toggle');
    const rulesContent = document.querySelector('.ranking-rules-section .rules-content');
    
    if (!rulesToggle || !rulesContent) return;
    
    // Set initial state - collapsed by default
    rulesContent.classList.remove('active');
    rulesToggle.classList.remove('active');
    
    // Toggle handler
    const toggleRules = () => {
      const isActive = rulesContent.classList.contains('active');
      
      if (isActive) {
        // Collapse
        rulesContent.classList.remove('active');
        rulesToggle.classList.remove('active');
      } else {
        // Expand
        rulesContent.classList.add('active');
        rulesToggle.classList.add('active');
        
        // Smooth scroll to rules section on mobile
        if (this.isMobile) {
          setTimeout(() => {
            rulesHeader.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }, 100);
        }
      }
      
      // Analytics tracking (if available)
      if (typeof gtag !== 'undefined') {
        gtag('event', 'rules_toggle', {
          'event_category': 'Teams',
          'event_label': isActive ? 'collapse' : 'expand'
        });
      }
    };
    
    // Add click handlers
    rulesToggle.addEventListener('click', toggleRules);
    rulesHeader.addEventListener('click', toggleRules);
    
    // Keyboard accessibility
    rulesHeader.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleRules();
      }
    });
    
    // Add ARIA attributes
    rulesHeader.setAttribute('tabindex', '0');
    rulesHeader.setAttribute('role', 'button');
    rulesHeader.setAttribute('aria-expanded', 'false');
    rulesContent.setAttribute('aria-hidden', 'true');
    
    // Update ARIA on toggle
    const originalToggle = toggleRules;
    const toggleWithAria = () => {
      originalToggle();
      const isExpanded = rulesContent.classList.contains('active');
      rulesHeader.setAttribute('aria-expanded', isExpanded.toString());
      rulesContent.setAttribute('aria-hidden', (!isExpanded).toString());
    };
    
    rulesToggle.removeEventListener('click', toggleRules);
    rulesHeader.removeEventListener('click', toggleRules);
    rulesToggle.addEventListener('click', toggleWithAria);
    rulesHeader.addEventListener('click', toggleWithAria);
  }

  /**
   * UTILITY METHODS
   */
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Add smooth scroll behavior for mobile navigation
  smoothScrollTo(element) {
    if (element) {
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  }
}

// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TeamsListManager;
}