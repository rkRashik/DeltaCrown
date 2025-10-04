/**
 * Tournament Hub V4 - Interactive Features
 * Professional, modern JavaScript for hub interactions
 */

(function() {
    'use strict';

    // ========================================
    // DOM Elements
    // ========================================
    const searchInput = document.getElementById('tournament-search');
    const searchClear = document.getElementById('search-clear');
    const filtersSidebar = document.getElementById('filters-sidebar');
    const mobileFiltersToggle = document.getElementById('mobile-filters-toggle');
    const filtersClose = document.getElementById('filters-close');
    const filterReset = document.getElementById('filter-reset');
    const sortSelect = document.getElementById('sort-select');
    const scrollTop = document.getElementById('scroll-top');

    // ========================================
    // Search Functionality
    // ========================================
    if (searchInput && searchClear) {
        // Show/hide clear button
        searchInput.addEventListener('input', function() {
            if (this.value.length > 0) {
                searchClear.style.display = 'flex';
            } else {
                searchClear.style.display = 'none';
            }
        });

        // Clear search
        searchClear.addEventListener('click', function() {
            searchInput.value = '';
            searchClear.style.display = 'none';
            searchInput.focus();
            performSearch('');
        });

        // Search on enter
        searchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                performSearch(this.value);
            }
        });
    }

    function performSearch(query) {
        const url = new URL(window.location.href);
        if (query) {
            url.searchParams.set('q', query);
        } else {
            url.searchParams.delete('q');
        }
        url.searchParams.set('page', '1');
        window.location.href = url.toString();
    }

    // ========================================
    // Filter Sidebar
    // ========================================
    if (mobileFiltersToggle && filtersSidebar) {
        mobileFiltersToggle.addEventListener('click', function() {
            filtersSidebar.classList.add('open');
            document.body.style.overflow = 'hidden';
        });
    }

    if (filtersClose && filtersSidebar) {
        filtersClose.addEventListener('click', function() {
            filtersSidebar.classList.remove('open');
            document.body.style.overflow = '';
        });
    }

    // Close sidebar when clicking outside
    if (filtersSidebar) {
        document.addEventListener('click', function(e) {
            if (filtersSidebar.classList.contains('open') && 
                !filtersSidebar.contains(e.target) && 
                e.target !== mobileFiltersToggle) {
                filtersSidebar.classList.remove('open');
                document.body.style.overflow = '';
            }
        });
    }

    // ========================================
    // Filter Controls
    // ========================================
    const filterInputs = document.querySelectorAll('.filter-option input');
    filterInputs.forEach(input => {
        input.addEventListener('change', function() {
            applyFilters();
        });
    });

    function applyFilters() {
        const url = new URL(window.location.href);
        
        // Status filter
        const statusFilter = document.querySelector('input[name="status"]:checked');
        if (statusFilter && statusFilter.value !== 'all') {
            url.searchParams.set('status', statusFilter.value);
        } else {
            url.searchParams.delete('status');
        }

        // Fee filter
        const feeFilter = document.querySelector('input[name="fee"]:checked');
        if (feeFilter && feeFilter.value !== 'all') {
            url.searchParams.set('fee', feeFilter.value);
        } else {
            url.searchParams.delete('fee');
        }

        // Prize filter
        const prizeFilter = document.querySelector('input[name="prize"]:checked');
        if (prizeFilter && prizeFilter.value !== 'all') {
            url.searchParams.set('prize', prizeFilter.value);
        } else {
            url.searchParams.delete('prize');
        }

        url.searchParams.set('page', '1');
        window.location.href = url.toString();
    }

    // Reset filters
    if (filterReset) {
        filterReset.addEventListener('click', function() {
            window.location.href = window.location.pathname;
        });
    }

    // ========================================
    // Sort Dropdown
    // ========================================
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            const url = new URL(window.location.href);
            if (this.value) {
                url.searchParams.set('sort', this.value);
            } else {
                url.searchParams.delete('sort');
            }
            url.searchParams.set('page', '1');
            window.location.href = url.toString();
        });
    }

    // ========================================
    // Scroll to Top
    // ========================================
    if (scrollTop) {
        // Show/hide scroll to top button
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                scrollTop.classList.add('visible');
            } else {
                scrollTop.classList.remove('visible');
            }
        });

        // Scroll to top on click
        scrollTop.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // ========================================
    // Card Hover Effects
    // ========================================
    const tournamentCards = document.querySelectorAll('.tournament-card');
    tournamentCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.setProperty('--hover-scale', '1');
        });

        card.addEventListener('mouseleave', function() {
            this.style.setProperty('--hover-scale', '0');
        });
    });

    // ========================================
    // Game Card Active State
    // ========================================
    const gameCards = document.querySelectorAll('.game-card');
    const urlParams = new URLSearchParams(window.location.search);
    const currentGame = urlParams.get('game');

    gameCards.forEach(card => {
        const gameSlug = card.getAttribute('data-game');
        if (gameSlug === currentGame || (!currentGame && gameSlug === 'all')) {
            card.classList.add('active');
        }
    });

    // ========================================
    // Keyboard Navigation
    // ========================================
    document.addEventListener('keydown', function(e) {
        // ESC to close sidebar
        if (e.key === 'Escape' && filtersSidebar && filtersSidebar.classList.contains('open')) {
            filtersSidebar.classList.remove('open');
            document.body.style.overflow = '';
        }

        // CMD/CTRL + K to focus search
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            if (searchInput) {
                searchInput.focus();
            }
        }
    });

    // ========================================
    // Lazy Load Images
    // ========================================
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    observer.unobserve(img);
                }
            });
        });

        const lazyImages = document.querySelectorAll('img[data-src]');
        lazyImages.forEach(img => imageObserver.observe(img));
    }

    // ========================================
    // Performance: Debounce Search
    // ========================================
    function debounce(func, wait) {
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

    // Apply debounced search for real-time filtering (optional)
    if (searchInput) {
        const debouncedSearch = debounce(function() {
            // Uncomment for real-time search
            // performSearch(searchInput.value);
        }, 500);

        searchInput.addEventListener('input', debouncedSearch);
    }

    // ========================================
    // Smooth Scroll for Anchor Links
    // ========================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // ========================================
    // Page Load Animation
    // ========================================
    window.addEventListener('load', function() {
        document.body.classList.add('loaded');
    });

    // ========================================
    // Console Info
    // ========================================
    console.log('%cDeltaCrown Hub V4', 'font-size: 24px; font-weight: bold; color: #00ff88;');
    console.log('%cModern Tournament Hub - Ready', 'font-size: 14px; color: #94a3b8;');

})();
