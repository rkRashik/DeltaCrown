/**
 * Tournament Hub V3 - Modern Interactive Hub with Advanced Features
 * Features: Advanced filtering, search, infinite scroll, featured carousel, real-time updates
 * Version: 3.0.0
 * Last Updated: October 4, 2025
 */

class TournamentHubV3 {
    constructor() {
        this.state = {
            filters: {
                q: '',
                game: '',
                status: '',
                fee: '',
                prize: '',
                sort: 'newest'
            },
            pagination: {
                page: 1,
                hasNext: true,
                loading: false
            },
            tournaments: [],
            featuredIndex: 0,
            cache: {
                featured: null,
                stats: null,
                lastUpdate: null
            }
        };

        this.config = {
            apiEndpoints: {
                featured: '/tournaments/api/featured/',
                list: '/tournaments/',
                stats: '/tournaments/api/stats/'
            },
            cacheTimeout: 60000, // 1 minute
            searchDebounceDelay: 500,
            infiniteScrollThreshold: 300,
            featuredCarouselInterval: 8000,
            updateInterval: 60000 // 1 minute for real-time updates
        };

        this.elements = {};
        this.timers = {
            search: null,
            carousel: null,
            update: null
        };

        this.init();
    }

    /**
     * Initialize the hub
     */
    init() {
        this.cacheElements();
        this.bindEvents();
        this.initializeState();
        this.initFeaturedCarousel();
        this.initInfiniteScroll();
        this.initScrollToTop();
        this.startRealTimeUpdates();
        
        console.log('Tournament Hub V3 initialized');
    }

    /**
     * Cache DOM elements
     */
    cacheElements() {
        this.elements = {
            // Search
            searchInput: document.getElementById('hub-search-input'),
            searchClear: document.getElementById('hub-search-clear'),
            
            // Filters
            gameFilters: document.querySelectorAll('[data-game-filter]'),
            statusFilters: document.querySelectorAll('[data-status-filter]'),
            feeFilters: document.querySelectorAll('[data-fee-filter]'),
            prizeFilters: document.querySelectorAll('[data-prize-filter]'),
            sortSelect: document.getElementById('hub-sort-select'),
            
            // Filter reset
            filterReset: document.getElementById('hub-filter-reset'),
            activeFilterCount: document.getElementById('active-filter-count'),
            
            // Tournament grid
            tournamentGrid: document.getElementById('tournaments-grid'),
            
            // Loading states
            gridLoading: document.getElementById('grid-loading'),
            gridEmpty: document.getElementById('grid-empty'),
            
            // Featured carousel
            featuredCarousel: document.getElementById('featured-carousel'),
            featuredPrev: document.getElementById('featured-prev'),
            featuredNext: document.getElementById('featured-next'),
            featuredIndicators: document.getElementById('featured-indicators'),
            
            // Stats
            statsContainer: document.getElementById('platform-stats'),
            
            // Scroll to top
            scrollToTop: document.querySelector('.scroll-to-top-btn'),
            
            // Mobile filter toggle
            filterToggle: document.getElementById('mobile-filter-toggle'),
            filterSidebar: document.getElementById('filter-sidebar'),
            filterClose: document.getElementById('filter-close')
        };
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Search
        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('input', (e) => {
                this.handleSearchInput(e.target.value);
            });
        }

        if (this.elements.searchClear) {
            this.elements.searchClear.addEventListener('click', () => {
                this.clearSearch();
            });
        }

        // Game filters
        this.elements.gameFilters.forEach(btn => {
            btn.addEventListener('click', () => {
                this.handleGameFilter(btn.dataset.gameFilter);
            });
        });

        // Status filters
        this.elements.statusFilters.forEach(btn => {
            btn.addEventListener('click', () => {
                this.handleStatusFilter(btn.dataset.statusFilter);
            });
        });

        // Fee filters
        this.elements.feeFilters.forEach(btn => {
            btn.addEventListener('click', () => {
                this.handleFeeFilter(btn.dataset.feeFilter);
            });
        });

        // Prize filters
        this.elements.prizeFilters.forEach(btn => {
            btn.addEventListener('click', () => {
                this.handlePrizeFilter(btn.dataset.prizeFilter);
            });
        });

        // Sort select
        if (this.elements.sortSelect) {
            this.elements.sortSelect.addEventListener('change', (e) => {
                this.handleSort(e.target.value);
            });
        }

        // Filter reset
        if (this.elements.filterReset) {
            this.elements.filterReset.addEventListener('click', () => {
                this.resetFilters();
            });
        }

        // Featured carousel
        if (this.elements.featuredPrev) {
            this.elements.featuredPrev.addEventListener('click', () => {
                this.prevFeatured();
            });
        }

        if (this.elements.featuredNext) {
            this.elements.featuredNext.addEventListener('click', () => {
                this.nextFeatured();
            });
        }

        // Mobile filter toggle
        if (this.elements.filterToggle) {
            this.elements.filterToggle.addEventListener('click', () => {
                this.toggleFilterSidebar();
            });
        }

        if (this.elements.filterClose) {
            this.elements.filterClose.addEventListener('click', () => {
                this.closeFilterSidebar();
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
    }

    /**
     * Initialize state from URL parameters
     */
    initializeState() {
        const params = new URLSearchParams(window.location.search);
        
        this.state.filters.q = params.get('q') || '';
        this.state.filters.game = params.get('game') || '';
        this.state.filters.status = params.get('status') || '';
        this.state.filters.fee = params.get('fee') || '';
        this.state.filters.prize = params.get('prize') || '';
        this.state.filters.sort = params.get('sort') || 'newest';

        // Update UI to reflect state
        this.updateFilterUI();
        this.updateActiveFilterCount();

        // Show/hide search clear button
        if (this.elements.searchInput && this.elements.searchClear) {
            this.elements.searchClear.style.display = 
                this.state.filters.q ? 'block' : 'none';
        }
    }

    /**
     * Update filter UI to reflect current state
     */
    updateFilterUI() {
        // Update search input
        if (this.elements.searchInput) {
            this.elements.searchInput.value = this.state.filters.q;
        }

        // Update game filters
        this.elements.gameFilters.forEach(btn => {
            const isActive = btn.dataset.gameFilter === this.state.filters.game ||
                           (!this.state.filters.game && btn.dataset.gameFilter === 'all');
            btn.classList.toggle('active', isActive);
        });

        // Update status filters
        this.elements.statusFilters.forEach(btn => {
            const isActive = btn.dataset.statusFilter === this.state.filters.status ||
                           (!this.state.filters.status && btn.dataset.statusFilter === 'all');
            btn.classList.toggle('active', isActive);
        });

        // Update fee filters
        this.elements.feeFilters.forEach(btn => {
            const isActive = btn.dataset.feeFilter === this.state.filters.fee ||
                           (!this.state.filters.fee && btn.dataset.feeFilter === 'all');
            btn.classList.toggle('active', isActive);
        });

        // Update prize filters
        this.elements.prizeFilters.forEach(btn => {
            const isActive = btn.dataset.prizeFilter === this.state.filters.prize ||
                           (!this.state.filters.prize && btn.dataset.prizeFilter === 'all');
            btn.classList.toggle('active', isActive);
        });

        // Update sort select
        if (this.elements.sortSelect) {
            this.elements.sortSelect.value = this.state.filters.sort;
        }
    }

    /**
     * Handle search input with debouncing
     */
    handleSearchInput(query) {
        this.state.filters.q = query;

        // Show/hide clear button
        if (this.elements.searchClear) {
            this.elements.searchClear.style.display = query ? 'block' : 'none';
        }

        // Debounce search
        clearTimeout(this.timers.search);
        this.timers.search = setTimeout(() => {
            this.applyFilters();
        }, this.config.searchDebounceDelay);
    }

    /**
     * Clear search
     */
    clearSearch() {
        this.state.filters.q = '';
        if (this.elements.searchInput) {
            this.elements.searchInput.value = '';
        }
        if (this.elements.searchClear) {
            this.elements.searchClear.style.display = 'none';
        }
        this.applyFilters();
    }

    /**
     * Handle game filter
     */
    handleGameFilter(game) {
        this.state.filters.game = game === 'all' ? '' : game;
        this.updateFilterUI();
        this.applyFilters();
    }

    /**
     * Handle status filter
     */
    handleStatusFilter(status) {
        this.state.filters.status = status === 'all' ? '' : status;
        this.updateFilterUI();
        this.applyFilters();
    }

    /**
     * Handle fee filter
     */
    handleFeeFilter(fee) {
        this.state.filters.fee = fee === 'all' ? '' : fee;
        this.updateFilterUI();
        this.applyFilters();
    }

    /**
     * Handle prize filter
     */
    handlePrizeFilter(prize) {
        this.state.filters.prize = prize === 'all' ? '' : prize;
        this.updateFilterUI();
        this.applyFilters();
    }

    /**
     * Handle sort change
     */
    handleSort(sortBy) {
        this.state.filters.sort = sortBy;
        this.applyFilters();
    }

    /**
     * Reset all filters
     */
    resetFilters() {
        this.state.filters = {
            q: '',
            game: '',
            status: '',
            fee: '',
            prize: '',
            sort: 'newest'
        };
        this.state.pagination.page = 1;
        
        this.updateFilterUI();
        this.applyFilters();
    }

    /**
     * Apply filters and reload tournaments
     */
    applyFilters() {
        this.state.pagination.page = 1;
        this.state.pagination.hasNext = true;
        
        this.updateURL();
        this.updateActiveFilterCount();
        this.loadTournaments(true);
    }

    /**
     * Update browser URL with current filters
     */
    updateURL() {
        const params = new URLSearchParams();
        
        if (this.state.filters.q) params.set('q', this.state.filters.q);
        if (this.state.filters.game) params.set('game', this.state.filters.game);
        if (this.state.filters.status) params.set('status', this.state.filters.status);
        if (this.state.filters.fee) params.set('fee', this.state.filters.fee);
        if (this.state.filters.prize) params.set('prize', this.state.filters.prize);
        if (this.state.filters.sort && this.state.filters.sort !== 'newest') {
            params.set('sort', this.state.filters.sort);
        }
        
        const newURL = params.toString() 
            ? `${window.location.pathname}?${params.toString()}`
            : window.location.pathname;
        
        window.history.replaceState({}, '', newURL);
    }

    /**
     * Update active filter count badge
     */
    updateActiveFilterCount() {
        const count = Object.values(this.state.filters).filter(v => 
            v && v !== 'newest'
        ).length;
        
        if (this.elements.activeFilterCount) {
            this.elements.activeFilterCount.textContent = count;
            this.elements.activeFilterCount.style.display = count > 0 ? 'inline-flex' : 'none';
        }

        if (this.elements.filterReset) {
            this.elements.filterReset.disabled = count === 0;
        }
    }

    /**
     * Load tournaments from server
     */
    async loadTournaments(reset = false) {
        if (this.state.pagination.loading) return;
        
        this.state.pagination.loading = true;
        
        if (reset) {
            this.showLoading();
        }

        try {
            const params = new URLSearchParams({
                ...this.state.filters,
                page: this.state.pagination.page
            });

            // Remove empty params
            for (const [key, value] of [...params.entries()]) {
                if (!value) params.delete(key);
            }

            const response = await fetch(`${this.config.apiEndpoints.list}?${params.toString()}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) throw new Error('Failed to load tournaments');

            const html = await response.text();
            
            // Parse response
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newCards = doc.querySelectorAll('.tournament-card-modern');

            if (reset) {
                this.elements.tournamentGrid.innerHTML = '';
                this.state.tournaments = [];
            }

            if (newCards.length === 0) {
                if (reset) {
                    this.showEmptyState();
                } else {
                    this.state.pagination.hasNext = false;
                }
            } else {
                // Append new cards
                newCards.forEach(card => {
                    this.elements.tournamentGrid.appendChild(card.cloneNode(true));
                });

                // Check if there are more pages
                const pagination = doc.querySelector('.pagination-wrapper');
                this.state.pagination.hasNext = pagination?.querySelector('.btn-pagination:last-child') !== null;

                this.hideLoading();
                this.hideEmptyState();
            }

        } catch (error) {
            console.error('Error loading tournaments:', error);
            this.showError('Failed to load tournaments. Please try again.');
        } finally {
            this.state.pagination.loading = false;
        }
    }

    /**
     * Initialize infinite scroll
     */
    initInfiniteScroll() {
        let ticking = false;

        window.addEventListener('scroll', () => {
            if (ticking) return;

            window.requestAnimationFrame(() => {
                const scrollPosition = window.innerHeight + window.scrollY;
                const threshold = document.documentElement.scrollHeight - this.config.infiniteScrollThreshold;

                if (scrollPosition >= threshold && 
                    this.state.pagination.hasNext && 
                    !this.state.pagination.loading) {
                    this.state.pagination.page++;
                    this.loadTournaments(false);
                }

                ticking = false;
            });

            ticking = true;
        });
    }

    /**
     * Initialize featured tournament carousel
     */
    initFeaturedCarousel() {
        if (!this.elements.featuredCarousel) return;

        // Auto-rotate carousel
        this.timers.carousel = setInterval(() => {
            this.nextFeatured();
        }, this.config.featuredCarouselInterval);

        // Pause on hover
        this.elements.featuredCarousel.addEventListener('mouseenter', () => {
            clearInterval(this.timers.carousel);
        });

        this.elements.featuredCarousel.addEventListener('mouseleave', () => {
            this.timers.carousel = setInterval(() => {
                this.nextFeatured();
            }, this.config.featuredCarouselInterval);
        });

        // Update indicators
        this.updateCarouselIndicators();
    }

    /**
     * Show next featured tournament
     */
    nextFeatured() {
        const items = this.elements.featuredCarousel?.querySelectorAll('.featured-item');
        if (!items || items.length <= 1) return;

        this.state.featuredIndex = (this.state.featuredIndex + 1) % items.length;
        this.updateCarousel();
    }

    /**
     * Show previous featured tournament
     */
    prevFeatured() {
        const items = this.elements.featuredCarousel?.querySelectorAll('.featured-item');
        if (!items || items.length <= 1) return;

        this.state.featuredIndex = (this.state.featuredIndex - 1 + items.length) % items.length;
        this.updateCarousel();
    }

    /**
     * Update carousel display
     */
    updateCarousel() {
        const items = this.elements.featuredCarousel?.querySelectorAll('.featured-item');
        if (!items) return;

        items.forEach((item, index) => {
            item.classList.toggle('active', index === this.state.featuredIndex);
        });

        this.updateCarouselIndicators();
    }

    /**
     * Update carousel indicators
     */
    updateCarouselIndicators() {
        if (!this.elements.featuredIndicators) return;

        const items = this.elements.featuredCarousel?.querySelectorAll('.featured-item');
        if (!items || items.length <= 1) return;

        this.elements.featuredIndicators.innerHTML = '';
        
        items.forEach((_, index) => {
            const indicator = document.createElement('button');
            indicator.classList.add('carousel-indicator');
            if (index === this.state.featuredIndex) {
                indicator.classList.add('active');
            }
            indicator.addEventListener('click', () => {
                this.state.featuredIndex = index;
                this.updateCarousel();
            });
            this.elements.featuredIndicators.appendChild(indicator);
        });
    }

    /**
     * Start real-time updates for stats and featured
     */
    startRealTimeUpdates() {
        this.timers.update = setInterval(() => {
            this.updateStats();
        }, this.config.updateInterval);
    }

    /**
     * Update platform stats
     */
    async updateStats() {
        try {
            const response = await fetch(this.config.apiEndpoints.stats);
            if (!response.ok) return;

            const data = await response.json();
            
            if (this.elements.statsContainer) {
                // Update stat values with animation
                this.animateStatUpdate(data);
            }

            this.state.cache.stats = data;
            this.state.cache.lastUpdate = Date.now();

        } catch (error) {
            console.error('Error updating stats:', error);
        }
    }

    /**
     * Animate stat value updates
     */
    animateStatUpdate(newStats) {
        const statElements = this.elements.statsContainer.querySelectorAll('.stat-value');
        
        statElements.forEach(el => {
            const key = el.dataset.stat;
            if (key && newStats[key]) {
                const oldValue = parseInt(el.textContent.replace(/[^0-9]/g, '')) || 0;
                const newValue = newStats[key];
                
                if (oldValue !== newValue) {
                    this.animateNumber(el, oldValue, newValue, 1000);
                }
            }
        });
    }

    /**
     * Animate number change
     */
    animateNumber(element, from, to, duration) {
        const start = Date.now();
        const prefix = element.textContent.match(/^[^0-9]*/)?.[0] || '';
        const suffix = element.textContent.match(/[^0-9]*$/)?.[0] || '';

        const animate = () => {
            const now = Date.now();
            const progress = Math.min((now - start) / duration, 1);
            const value = Math.floor(from + (to - from) * progress);
            
            element.textContent = prefix + value.toLocaleString() + suffix;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        animate();
    }

    /**
     * Initialize scroll to top button
     */
    initScrollToTop() {
        if (!this.elements.scrollToTop) return;

        window.addEventListener('scroll', () => {
            if (window.scrollY > 300) {
                this.elements.scrollToTop.classList.add('visible');
            } else {
                this.elements.scrollToTop.classList.remove('visible');
            }
        });

        this.elements.scrollToTop.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    /**
     * Toggle mobile filter sidebar
     */
    toggleFilterSidebar() {
        if (this.elements.filterSidebar) {
            this.elements.filterSidebar.classList.toggle('open');
            document.body.classList.toggle('filter-open');
        }
    }

    /**
     * Close mobile filter sidebar
     */
    closeFilterSidebar() {
        if (this.elements.filterSidebar) {
            this.elements.filterSidebar.classList.remove('open');
            document.body.classList.remove('filter-open');
        }
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts(e) {
        // Escape key closes filter sidebar
        if (e.key === 'Escape') {
            this.closeFilterSidebar();
        }

        // Ctrl/Cmd + K focuses search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            this.elements.searchInput?.focus();
        }
    }

    /**
     * Show loading state
     */
    showLoading() {
        if (this.elements.gridLoading) {
            this.elements.gridLoading.style.display = 'block';
        }
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        if (this.elements.gridLoading) {
            this.elements.gridLoading.style.display = 'none';
        }
    }

    /**
     * Show empty state
     */
    showEmptyState() {
        if (this.elements.gridEmpty) {
            this.elements.gridEmpty.style.display = 'flex';
        }
        this.hideLoading();
    }

    /**
     * Hide empty state
     */
    hideEmptyState() {
        if (this.elements.gridEmpty) {
            this.elements.gridEmpty.style.display = 'none';
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = 'hub-toast hub-toast-error';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * Cleanup on destroy
     */
    destroy() {
        clearInterval(this.timers.carousel);
        clearInterval(this.timers.update);
        clearTimeout(this.timers.search);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.tournamentHub = new TournamentHubV3();
});
