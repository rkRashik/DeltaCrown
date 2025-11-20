/**
 * DeltaCrown Tournaments Hub - Professional JavaScript
 * Industry-level interactivity for tournament listing page
 * 
 * Features:
 * - Auto-submit filters with smooth transitions
 * - Sort functionality
 * - Mobile filter panel
 * - Scroll animations
 * - Search debouncing
 */

(function() {
    'use strict';
    
    // ==================== Configuration ====================
    const CONFIG = {
        searchDebounceMs: 500,
        animationDuration: 300,
        scrollThreshold: 100
    };
    
    // ==================== State Management ====================
    let searchTimeout = null;
    let isFilterPanelOpen = false;
    
    // ==================== DOM Elements ====================
    const elements = {
        filtersForm: document.getElementById('filters-form'),
        searchInput: document.querySelector('.dc-search-input'),
        sortSelect: document.getElementById('sort-select'),
        filterInputs: document.querySelectorAll('.dc-filter-option input[type="radio"]'),
        resetButton: document.getElementById('reset-filters'),
        mobileFilterBtn: document.getElementById('open-filters'),
        closeFiltersBtn: document.getElementById('close-filters'),
        filtersPanel: document.getElementById('filters-panel'),
        tournamentCards: document.querySelectorAll('.dc-tournament-card'),
        body: document.body
    };
    
    // ==================== Utility Functions ====================
    
    /**
     * Debounce function for search input
     */
    function debounce(func, wait) {
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(searchTimeout);
                func(...args);
            };
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Get current URL parameters
     */
    function getURLParams() {
        const params = new URLSearchParams(window.location.search);
        return Object.fromEntries(params.entries());
    }
    
    /**
     * Update URL without page reload
     */
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
    
    /**
     * Submit form with current parameters
     */
    function submitFilters() {
        if (elements.filtersForm) {
            elements.filtersForm.submit();
        }
    }
    
    /**
     * Smooth scroll to top
     */
    function scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
    
    // ==================== Search Functionality ====================
    
    /**
     * Handle search input
     */
    function handleSearch(event) {
        const searchValue = event.target.value.trim();
        console.log('Search:', searchValue);
        
        // Update URL parameter
        updateURL({ q: searchValue });
        
        // Submit form after debounce
        submitFilters();
    }
    
    /**
     * Initialize search
     */
    function initSearch() {
        if (elements.searchInput) {
            const debouncedSearch = debounce(handleSearch, CONFIG.searchDebounceMs);
            elements.searchInput.addEventListener('input', debouncedSearch);
            console.log('Search initialized');
        }
    }
    
    // ==================== Filter Functionality ====================
    
    /**
     * Handle filter change
     */
    function handleFilterChange(event) {
        const input = event.target;
        const filterName = input.name;
        const filterValue = input.value;
        
        console.log('Filter changed:', filterName, filterValue);
        
        // Update URL parameter
        const params = { [filterName]: filterValue };
        updateURL(params);
        
        // Submit form immediately
        submitFilters();
    }
    
    /**
     * Initialize filters
     */
    function initFilters() {
        if (elements.filterInputs.length > 0) {
            elements.filterInputs.forEach(input => {
                input.addEventListener('change', handleFilterChange);
            });
            console.log('Filters initialized:', elements.filterInputs.length);
        }
    }
    
    /**
     * Reset all filters
     */
    function resetFilters(event) {
        event.preventDefault();
        console.log('Resetting filters');
        
        // Clear URL parameters except search
        const currentSearch = elements.searchInput ? elements.searchInput.value : '';
        window.location.href = window.location.pathname + (currentSearch ? `?q=${encodeURIComponent(currentSearch)}` : '');
    }
    
    /**
     * Initialize reset button
     */
    function initResetButton() {
        if (elements.resetButton) {
            elements.resetButton.addEventListener('click', resetFilters);
            console.log('Reset button initialized');
        }
    }
    
    // ==================== Sort Functionality ====================
    
    /**
     * Handle sort change
     */
    function handleSortChange(event) {
        const sortValue = event.target.value;
        console.log('Sort changed:', sortValue);
        
        // Update URL parameter
        updateURL({ sort: sortValue });
        
        // Submit form
        submitFilters();
    }
    
    /**
     * Initialize sort dropdown
     */
    function initSort() {
        if (elements.sortSelect) {
            elements.sortSelect.addEventListener('change', handleSortChange);
            console.log('Sort initialized');
        }
    }
    
    // ==================== Mobile Filter Panel ====================
    
    /**
     * Open mobile filter panel
     */
    function openFilterPanel() {
        if (elements.filtersPanel) {
            elements.filtersPanel.classList.add('active');
            elements.body.style.overflow = 'hidden';
            isFilterPanelOpen = true;
            console.log('Filter panel opened');
        }
    }
    
    /**
     * Close mobile filter panel
     */
    function closeFilterPanel() {
        if (elements.filtersPanel) {
            elements.filtersPanel.classList.remove('active');
            elements.body.style.overflow = '';
            isFilterPanelOpen = false;
            console.log('Filter panel closed');
        }
    }
    
    /**
     * Initialize mobile filter panel
     */
    function initMobileFilterPanel() {
        if (elements.mobileFilterBtn) {
            elements.mobileFilterBtn.addEventListener('click', openFilterPanel);
            console.log('Mobile filter button initialized');
        }
        
        if (elements.closeFiltersBtn) {
            elements.closeFiltersBtn.addEventListener('click', closeFilterPanel);
            console.log('Close filter button initialized');
        }
        
        // Close on escape key
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && isFilterPanelOpen) {
                closeFilterPanel();
            }
        });
    }
    
    // ==================== Card Animations ====================
    
    /**
     * Animate cards on scroll
     */
    function initCardAnimations() {
        if (!elements.tournamentCards.length) return;
        
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }, index * 100);
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);
        
        elements.tournamentCards.forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            card.style.transition = `opacity ${CONFIG.animationDuration}ms ease, transform ${CONFIG.animationDuration}ms ease`;
            observer.observe(card);
        });
        
        console.log('Card animations initialized:', elements.tournamentCards.length);
    }
    
    // ==================== Scroll to Top ====================
    
    /**
     * Show/hide scroll to top button
     */
    function initScrollToTop() {
        let scrollTopBtn = document.querySelector('.dc-scroll-top');
        
        // Create button if it doesn't exist
        if (!scrollTopBtn) {
            scrollTopBtn = document.createElement('button');
            scrollTopBtn.className = 'dc-scroll-top';
            scrollTopBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
            scrollTopBtn.setAttribute('aria-label', 'Scroll to top');
            document.body.appendChild(scrollTopBtn);
            
            // Add styles
            Object.assign(scrollTopBtn.style, {
                position: 'fixed',
                bottom: '2rem',
                right: '2rem',
                width: '48px',
                height: '48px',
                background: 'linear-gradient(135deg, var(--dc-primary), var(--dc-primary-dark))',
                color: 'var(--dc-text-primary)',
                border: 'none',
                borderRadius: 'var(--dc-radius-full)',
                cursor: 'pointer',
                display: 'none',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.25rem',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)',
                transition: 'all 0.3s ease',
                zIndex: '999'
            });
        }
        
        // Show/hide on scroll
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > CONFIG.scrollThreshold) {
                scrollTopBtn.style.display = 'flex';
            } else {
                scrollTopBtn.style.display = 'none';
            }
        });
        
        // Scroll to top on click
        scrollTopBtn.addEventListener('click', scrollToTop);
        
        console.log('Scroll to top initialized');
    }
    
    // ==================== Initialization ====================
    
    /**
     * Initialize all functionality
     */
    function init() {
        console.log('🎮 DeltaCrown Tournaments Hub - Initializing...');
        
        // Initialize features
        initSearch();
        initFilters();
        initResetButton();
        initSort();
        initMobileFilterPanel();
        initCardAnimations();
        initScrollToTop();
        
        console.log('✅ DeltaCrown Tournaments Hub - Initialized successfully!');
    }
    
    // ==================== Execute on DOM Ready ====================
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();
