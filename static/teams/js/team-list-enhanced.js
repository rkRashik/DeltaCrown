// ========================================
// TEAMS LIST - ENHANCED PAGINATION & LOADING
// Progressive enhancement with smooth AJAX loading
// ========================================

(function() {
    'use strict';

    // ========================================
    // CONFIGURATION
    // ========================================
    const config = {
        enableAjax: true, // Progressive enhancement
        debounceDelay: 500,
        scrollToTopOnPageChange: true
    };

    // ========================================
    // STATE MANAGEMENT
    // ========================================
    const state = {
        currentView: localStorage.getItem('teamListView') || 'grid',
        loading: false,
        lastRequestAbortController: null
    };

    // ========================================
    // DOM ELEMENTS
    // ========================================
    const elements = {
        teamsContainer: document.querySelector('.teams-container'),
        paginationContainer: document.querySelector('.pagination-modern-container, .pagination-container-premium'),
        loadingOverlay: document.getElementById('loading-overlay-premium'),
        searchInput: document.getElementById('team-search-premium'),
        searchClear: document.getElementById('search-clear-premium'),
        sortSelect: document.getElementById('sort-select-premium'),
        viewBtns: document.querySelectorAll('.view-btn'),
        filterToggle: document.querySelector('.btn-filters'),
        advancedFilters: document.getElementById('advanced-filters'),
        filterChips: document.querySelectorAll('.filter-chip'),
        applyFiltersBtn: document.querySelector('.apply-filters-btn'),
        resetFiltersBtn: document.querySelector('.reset-filters-btn'),
        scrollToTopBtn: document.querySelector('.scroll-to-top'),
        loadMoreBtn: document.getElementById('load-more-btn'),
        pageJumpInput: document.getElementById('page-jump-input-modern'),
        pageJumpBtn: document.getElementById('page-jump-btn-modern')
    };

    // ========================================
    // INITIALIZATION
    // ========================================
    function init() {
        if (!elements.teamsContainer) {
            console.log('Teams container not found - skipping initialization');
            return;
        }

        setupEventListeners();
        loadViewPreference();
        updateSearchClearButton();
        setupScrollToTop();
        initializeFiltersFromURL();
        setupLoadMore();
        setupPageJump();
        
        console.log('✅ Teams List Enhanced - Initialized');
    }

    // ========================================
    // INITIALIZE FILTERS FROM URL
    // ========================================
    function initializeFiltersFromURL() {
        const params = new URLSearchParams(window.location.search);
        
        // Set filter chips active state
        elements.filterChips.forEach(chip => {
            const filterType = chip.dataset.filter;
            const isActive = params.get(filterType) === 'true';
            chip.classList.toggle('active', isActive);
        });
        
        // Set region select
        const regionSelect = document.getElementById('regionFilter');
        if (regionSelect && params.has('region')) {
            regionSelect.value = params.get('region');
        }
        
        // Set member count inputs
        const minMembers = document.getElementById('minMembers');
        const maxMembers = document.getElementById('maxMembers');
        if (minMembers && params.has('min_members')) {
            minMembers.value = params.get('min_members');
        }
        if (maxMembers && params.has('max_members')) {
            maxMembers.value = params.get('max_members');
        }
    }

    // ========================================
    // EVENT LISTENERS
    // ========================================
    function setupEventListeners() {
        // Search input with debounce
        if (elements.searchInput) {
            let searchTimeout;
            elements.searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                updateSearchClearButton();
                
                searchTimeout = setTimeout(() => {
                    navigateWithParams({ q: e.target.value.trim() || null, page: null });
                }, config.debounceDelay);
            });
        }

        // Search clear button
        if (elements.searchClear) {
            elements.searchClear.addEventListener('click', () => {
                if (elements.searchInput) {
                    elements.searchInput.value = '';
                    updateSearchClearButton();
                    navigateWithParams({ q: null, page: null });
                }
            });
        }

        // Sort select
        if (elements.sortSelect) {
            elements.sortSelect.addEventListener('change', (e) => {
                navigateWithParams({ sort: e.target.value, page: null });
            });
        }

        // View switcher
        elements.viewBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const view = btn.dataset.view;
                switchView(view);
            });
        });

        // Filter toggle
        if (elements.filterToggle) {
            elements.filterToggle.addEventListener('click', toggleAdvancedFilters);
        }

        // Filter chips
        elements.filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                chip.classList.toggle('active');
            });
        });

        // Apply filters button
        if (elements.applyFiltersBtn) {
            elements.applyFiltersBtn.addEventListener('click', applyFilters);
        }

        // Reset filters button
        if (elements.resetFiltersBtn) {
            elements.resetFiltersBtn.addEventListener('click', resetFilters);
        }

        // Pagination links - AJAX enhancement
        if (config.enableAjax) {
            setupPaginationAjax();
        }

        // Scroll to top button
        if (elements.scrollToTopBtn) {
            window.addEventListener('scroll', handleScroll);
            elements.scrollToTopBtn.addEventListener('click', scrollToTop);
        }
    }

    // ========================================
    // PAGINATION AJAX ENHANCEMENT
    // ========================================
    function setupPaginationAjax() {
        document.addEventListener('click', (e) => {
            // Check if clicked element is a pagination link
            const paginationLink = e.target.closest('.page-num:not(.active), .page-nav-btn:not(.disabled), .pagination-number, .pagination-btn:not(.disabled)');
            
            if (paginationLink && paginationLink.href) {
                e.preventDefault();
                const url = new URL(paginationLink.href);
                loadPageAjax(url);
            }
        });
    }

    // ========================================
    // LOAD MORE FUNCTIONALITY
    // ========================================
    function setupLoadMore() {
        if (elements.loadMoreBtn) {
            elements.loadMoreBtn.addEventListener('click', handleLoadMore);
        }
    }

    async function handleLoadMore() {
        if (!elements.loadMoreBtn || state.loading) return;

        const nextPage = parseInt(elements.loadMoreBtn.dataset.nextPage);
        if (!nextPage) return;

        state.loading = true;
        elements.loadMoreBtn.classList.add('loading');
        
        // Show spinner, hide icon
        const btnIcon = elements.loadMoreBtn.querySelector('.btn-icon');
        const btnSpinner = elements.loadMoreBtn.querySelector('.btn-spinner');
        if (btnIcon) btnIcon.style.display = 'none';
        if (btnSpinner) btnSpinner.style.display = 'inline-block';

        try {
            const url = new URL(window.location.href);
            url.searchParams.set('page', nextPage);

            const response = await fetch(url.toString(), {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'text/html'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');

            // Append new teams to existing container
            const newTeams = doc.querySelectorAll('.team-card-premium');
            if (newTeams.length > 0 && elements.teamsContainer) {
                newTeams.forEach(team => {
                    elements.teamsContainer.appendChild(team);
                });
            }

            // Update or remove load more button
            const newLoadMoreBtn = doc.getElementById('load-more-btn');
            if (newLoadMoreBtn) {
                const newNextPage = newLoadMoreBtn.dataset.nextPage;
                elements.loadMoreBtn.dataset.nextPage = newNextPage;
                
                // Update subtext
                const btnSubtext = elements.loadMoreBtn.querySelector('.btn-subtext');
                const newBtnSubtext = newLoadMoreBtn.querySelector('.btn-subtext');
                if (btnSubtext && newBtnSubtext) {
                    btnSubtext.textContent = newBtnSubtext.textContent;
                }
            } else {
                // No more pages - remove button
                elements.loadMoreBtn.remove();
            }

        } catch (error) {
            console.error('Load more failed:', error);
            alert('Failed to load more teams. Please try refreshing the page.');
        } finally {
            state.loading = false;
            elements.loadMoreBtn?.classList.remove('loading');
            if (btnIcon) btnIcon.style.display = '';
            if (btnSpinner) btnSpinner.style.display = 'none';
        }
    }

    // ========================================
    // PAGE JUMP FUNCTIONALITY
    // ========================================
    function setupPageJump() {
        if (elements.pageJumpBtn && elements.pageJumpInput) {
            elements.pageJumpBtn.addEventListener('click', handlePageJump);
            elements.pageJumpInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    handlePageJump();
                }
            });
        }
    }

    function handlePageJump() {
        if (!elements.pageJumpInput) return;

        const pageNumber = parseInt(elements.pageJumpInput.value);
        const maxPage = parseInt(elements.pageJumpInput.max);

        if (isNaN(pageNumber) || pageNumber < 1 || pageNumber > maxPage) {
            alert(`Please enter a page number between 1 and ${maxPage}`);
            return;
        }

        navigateWithParams({ page: pageNumber });
    }

    // ========================================
    // LOAD PAGE VIA AJAX
    // ========================================
    async function loadPageAjax(url) {
        if (state.loading) {
            if (state.lastRequestAbortController) {
                state.lastRequestAbortController.abort();
            }
        }

        state.loading = true;
        state.lastRequestAbortController = new AbortController();
        showLoading();

        try {
            const response = await fetch(url.toString(), {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'text/html'
                },
                signal: state.lastRequestAbortController.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const html = await response.text();
            updatePageContent(html, url);
            
            // Update browser URL without reload
            window.history.pushState({}, '', url.toString());

            if (config.scrollToTopOnPageChange) {
                scrollToElement(elements.teamsContainer);
            }

        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Request aborted');
            } else {
                console.error('Error loading page:', error);
                // Fallback to normal navigation
                window.location.href = url.toString();
            }
        } finally {
            state.loading = false;
            hideLoading();
        }
    }

    // ========================================
    // UPDATE PAGE CONTENT
    // ========================================
    function updatePageContent(html, url) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        // Update teams container
        const newTeamsContainer = doc.querySelector('.teams-container');
        if (newTeamsContainer && elements.teamsContainer) {
            elements.teamsContainer.innerHTML = newTeamsContainer.innerHTML;
        }

        // Update pagination (support both old and new classes)
        const newPagination = doc.querySelector('.pagination-modern-container, .pagination-container-premium');
        const currentPagination = document.querySelector('.pagination-modern-container, .pagination-container-premium');
        if (newPagination && currentPagination) {
            currentPagination.replaceWith(newPagination);
            // Re-setup load more and page jump after replacement
            elements.loadMoreBtn = document.getElementById('load-more-btn');
            elements.pageJumpInput = document.getElementById('page-jump-input-modern');
            elements.pageJumpBtn = document.getElementById('page-jump-btn-modern');
            setupLoadMore();
            setupPageJump();
        } else if (!newPagination && currentPagination) {
            // No pagination needed
            currentPagination.remove();
        } else if (newPagination && !currentPagination) {
            // Add pagination
            elements.teamsContainer.insertAdjacentElement('afterend', newPagination);
            elements.loadMoreBtn = document.getElementById('load-more-btn');
            elements.pageJumpInput = document.getElementById('page-jump-input-modern');
            elements.pageJumpBtn = document.getElementById('page-jump-btn-modern');
            setupLoadMore();
            setupPageJump();
        }

        // Update results count if exists
        const newResultsCount = doc.querySelector('.results-count');
        const currentResultsCount = document.querySelector('.results-count');
        if (newResultsCount && currentResultsCount) {
            currentResultsCount.innerHTML = newResultsCount.innerHTML;
        }

        // Re-setup pagination AJAX for new links
        setupPaginationAjax();

        // Trigger view refresh to maintain grid/list state
        switchView(state.currentView);
    }

    // ========================================
    // NAVIGATION HELPERS
    // ========================================
    function navigateWithParams(updates) {
        const url = new URL(window.location.href);
        
        // Apply updates
        Object.entries(updates).forEach(([key, value]) => {
            if (value === null || value === '') {
                url.searchParams.delete(key);
            } else {
                url.searchParams.set(key, value);
            }
        });

        if (config.enableAjax) {
            loadPageAjax(url);
        } else {
            window.location.href = url.toString();
        }
    }

    // ========================================
    // FILTERS
    // ========================================
    function applyFilters() {
        const params = {};

        // Get filter chip states
        elements.filterChips.forEach(chip => {
            const filterType = chip.dataset.filter;
            if (chip.classList.contains('active')) {
                params[filterType] = 'true';
            }
        });

        // Get region
        const regionSelect = document.getElementById('regionFilter');
        if (regionSelect && regionSelect.value) {
            params.region = regionSelect.value;
        }

        // Get member counts
        const minMembers = document.getElementById('minMembers');
        const maxMembers = document.getElementById('maxMembers');
        if (minMembers && minMembers.value) {
            params.min_members = minMembers.value;
        }
        if (maxMembers && maxMembers.value) {
            params.max_members = maxMembers.value;
        }

        params.page = null; // Reset to page 1
        navigateWithParams(params);

        // Close filters panel
        if (elements.advancedFilters) {
            elements.advancedFilters.style.display = 'none';
        }
    }

    function resetFilters() {
        // Clear all filter chips
        elements.filterChips.forEach(chip => {
            chip.classList.remove('active');
        });

        // Clear select and inputs
        const regionSelect = document.getElementById('regionFilter');
        const minMembers = document.getElementById('minMembers');
        const maxMembers = document.getElementById('maxMembers');
        
        if (regionSelect) regionSelect.value = '';
        if (minMembers) minMembers.value = '';
        if (maxMembers) maxMembers.value = '';

        // Navigate to clean URL (keep only search query if present)
        const url = new URL(window.location.href);
        const query = url.searchParams.get('q');
        url.search = '';
        if (query) {
            url.searchParams.set('q', query);
        }

        if (config.enableAjax) {
            loadPageAjax(url);
        } else {
            window.location.href = url.toString();
        }
    }

    function toggleAdvancedFilters() {
        if (elements.advancedFilters) {
            const isVisible = elements.advancedFilters.style.display === 'block';
            elements.advancedFilters.style.display = isVisible ? 'none' : 'block';
        }
    }

    // ========================================
    // VIEW SWITCHING
    // ========================================
    function switchView(view) {
        state.currentView = view;

        // Update buttons
        elements.viewBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });

        // Update container
        if (elements.teamsContainer) {
            elements.teamsContainer.classList.toggle('list-view', view === 'list');
        }

        // Save preference
        localStorage.setItem('teamListView', view);
    }

    function loadViewPreference() {
        switchView(state.currentView);
    }

    // ========================================
    // SEARCH HELPERS
    // ========================================
    function updateSearchClearButton() {
        if (elements.searchClear && elements.searchInput) {
            elements.searchClear.style.display = 
                elements.searchInput.value.trim() ? 'flex' : 'none';
        }
    }

    // ========================================
    // LOADING STATES
    // ========================================
    function showLoading() {
        if (elements.loadingOverlay) {
            elements.loadingOverlay.style.display = 'flex';
        }
    }

    function hideLoading() {
        if (elements.loadingOverlay) {
            elements.loadingOverlay.style.display = 'none';
        }
    }

    // ========================================
    // SCROLL HELPERS
    // ========================================
    function setupScrollToTop() {
        handleScroll(); // Initial state
    }

    function handleScroll() {
        if (elements.scrollToTopBtn) {
            elements.scrollToTopBtn.style.display = 
                window.pageYOffset > 300 ? 'flex' : 'none';
        }
    }

    function scrollToTop() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function scrollToElement(element) {
        if (element) {
            const offset = 100; // Account for fixed header
            const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
            window.scrollTo({
                top: elementPosition - offset,
                behavior: 'smooth'
            });
        }
    }

    // ========================================
    // INIT ON DOM READY
    // ========================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Handle browser back/forward buttons
    window.addEventListener('popstate', () => {
        location.reload(); // Simple reload on back/forward for consistency
    });

})();
