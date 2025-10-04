/**
 * TOURNAMENT HUB V5 - INTERACTIVE FEATURES
 * Modern, smooth interactions with polished UX
 */

(function() {
    'use strict';

    // ============================================================================
    // INITIALIZATION
    // ============================================================================
    
    document.addEventListener('DOMContentLoaded', () => {
        initSearchBar();
        initFiltersPanel();
        initSortDropdown();
        initScrollToTop();
        initQuickActions();
        initProgressBars();
        logInitSuccess();
    });

    // ============================================================================
    // MODERN SEARCH BAR
    // ============================================================================
    
    function initSearchBar() {
        const searchForm = document.querySelector('.search-modern');
        const searchInput = document.querySelector('.search-input-modern');
        const clearBtn = document.querySelector('.search-clear-btn');
        const submitBtn = document.querySelector('.search-submit-btn');

        if (!searchForm || !searchInput) return;

        // Show/hide clear button based on input
        searchInput.addEventListener('input', () => {
            if (searchInput.value.trim().length > 0) {
                clearBtn.style.display = 'flex';
            } else {
                clearBtn.style.display = 'none';
            }
        });

        // Clear input
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                searchInput.value = '';
                clearBtn.style.display = 'none';
                searchInput.focus();
            });
        }

        // Submit form
        if (submitBtn) {
            submitBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const searchQuery = searchInput.value.trim();
                
                if (searchQuery.length > 0) {
                    performSearch(searchQuery);
                }
            });
        }

        // Submit on Enter key
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const searchQuery = searchInput.value.trim();
                
                if (searchQuery.length > 0) {
                    performSearch(searchQuery);
                }
            }
        });

        // Clear on Escape key
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                searchInput.value = '';
                clearBtn.style.display = 'none';
                searchInput.blur();
            }
        });
    }

    function performSearch(query) {
        // Add search query to URL params
        const url = new URL(window.location.href);
        url.searchParams.set('search', query);
        url.searchParams.delete('page'); // Reset pagination
        
        // Navigate to search results
        window.location.href = url.toString();
    }

    // ============================================================================
    // FILTERS PANEL (MOBILE)
    // ============================================================================
    
    function initFiltersPanel() {
        const filtersPanel = document.querySelector('.filters-panel');
        const filterToggleBtn = document.querySelector('.mobile-filter-toggle');
        const closeFiltersBtn = document.querySelector('.close-filters-btn');
        const resetFiltersBtn = document.querySelector('.filters-reset-btn');

        if (!filtersPanel) return;

        // Open filters (mobile)
        if (filterToggleBtn) {
            filterToggleBtn.addEventListener('click', () => {
                filtersPanel.classList.add('open');
                document.body.style.overflow = 'hidden'; // Prevent background scroll
            });
        }

        // Close filters
        if (closeFiltersBtn) {
            closeFiltersBtn.addEventListener('click', () => {
                filtersPanel.classList.remove('open');
                document.body.style.overflow = ''; // Restore scroll
            });
        }

        // Close filters on outside click
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 1024) {
                if (filtersPanel.classList.contains('open') && 
                    !filtersPanel.contains(e.target) && 
                    !filterToggleBtn.contains(e.target)) {
                    filtersPanel.classList.remove('open');
                    document.body.style.overflow = '';
                }
            }
        });

        // Reset filters
        if (resetFiltersBtn) {
            resetFiltersBtn.addEventListener('click', () => {
                // Remove all filter params from URL
                const url = new URL(window.location.href);
                url.searchParams.delete('game');
                url.searchParams.delete('status');
                url.searchParams.delete('format');
                url.searchParams.delete('page');
                
                window.location.href = url.toString();
            });
        }

        // Handle filter changes
        const filterInputs = filtersPanel.querySelectorAll('input[type="radio"]');
        filterInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                const filterType = e.target.name;
                const filterValue = e.target.value;
                
                applyFilter(filterType, filterValue);
            });
        });
    }

    function applyFilter(filterType, filterValue) {
        const url = new URL(window.location.href);
        
        if (filterValue === 'all' || filterValue === '') {
            url.searchParams.delete(filterType);
        } else {
            url.searchParams.set(filterType, filterValue);
        }
        
        url.searchParams.delete('page'); // Reset pagination
        window.location.href = url.toString();
    }

    // ============================================================================
    // SORT DROPDOWN
    // ============================================================================
    
    function initSortDropdown() {
        const sortSelect = document.querySelector('.sort-select-modern');
        
        if (!sortSelect) return;

        sortSelect.addEventListener('change', (e) => {
            const sortValue = e.target.value;
            applySorting(sortValue);
        });
    }

    function applySorting(sortValue) {
        const url = new URL(window.location.href);
        
        if (sortValue) {
            url.searchParams.set('sort', sortValue);
        } else {
            url.searchParams.delete('sort');
        }
        
        url.searchParams.delete('page'); // Reset pagination
        window.location.href = url.toString();
    }

    // ============================================================================
    // SCROLL TO TOP
    // ============================================================================
    
    function initScrollToTop() {
        const scrollBtn = document.querySelector('.scroll-top-btn');
        
        if (!scrollBtn) return;

        // Show/hide button based on scroll position
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 400) {
                scrollBtn.classList.add('visible');
            } else {
                scrollBtn.classList.remove('visible');
            }
        });

        // Scroll to top on click
        scrollBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // ============================================================================
    // QUICK ACTIONS (HOVER OVERLAY)
    // ============================================================================
    
    function initQuickActions() {
        const tournamentCards = document.querySelectorAll('.tournament-card-modern');
        
        tournamentCards.forEach(card => {
            const quickOverlay = card.querySelector('.card-quick-overlay');
            const quickActionBtn = card.querySelector('.quick-action-btn');
            
            if (!quickOverlay || !quickActionBtn) return;

            // Prevent overlay clicks from propagating to card link
            quickOverlay.addEventListener('click', (e) => {
                if (e.target === quickActionBtn || quickActionBtn.contains(e.target)) {
                    // Allow button click
                    return;
                }
                e.stopPropagation();
            });
        });
    }

    // ============================================================================
    // PROGRESS BARS ANIMATION
    // ============================================================================
    
    function initProgressBars() {
        const progressBars = document.querySelectorAll('.progress-modern-bar');
        
        if (progressBars.length === 0) return;

        // Animate progress bars on scroll into view
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const bar = entry.target;
                    const targetWidth = bar.dataset.progress || bar.style.width;
                    
                    // Animate from 0 to target width
                    bar.style.width = '0%';
                    setTimeout(() => {
                        bar.style.width = targetWidth;
                    }, 100);
                    
                    observer.unobserve(bar);
                }
            });
        }, {
            threshold: 0.5
        });

        progressBars.forEach(bar => {
            // Store original width
            bar.dataset.progress = bar.style.width;
            observer.observe(bar);
        });
    }

    // ============================================================================
    // GAME FILTERS (BROWSE BY GAME)
    // ============================================================================
    
    function initGameFilters() {
        const gameTiles = document.querySelectorAll('.game-tile');
        
        gameTiles.forEach(tile => {
            tile.addEventListener('click', (e) => {
                e.preventDefault();
                
                const gameSlug = tile.dataset.game;
                
                if (gameSlug) {
                    const url = new URL(window.location.href);
                    url.searchParams.set('game', gameSlug);
                    url.searchParams.delete('page');
                    
                    window.location.href = url.toString();
                }
            });
        });

        // Highlight active game
        const urlParams = new URLSearchParams(window.location.search);
        const activeGame = urlParams.get('game');
        
        if (activeGame) {
            gameTiles.forEach(tile => {
                if (tile.dataset.game === activeGame) {
                    tile.classList.add('active');
                }
            });
        }
    }

    // ============================================================================
    // SMOOTH SCROLLING FOR ANCHOR LINKS
    // ============================================================================
    
    function initSmoothScrolling() {
        const links = document.querySelectorAll('a[href^="#"]');
        
        links.forEach(link => {
            link.addEventListener('click', (e) => {
                const href = link.getAttribute('href');
                
                if (href === '#' || href === '#!') return;
                
                const target = document.querySelector(href);
                
                if (target) {
                    e.preventDefault();
                    
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // Update URL hash without jumping
                    history.pushState(null, null, href);
                }
            });
        });
    }

    // ============================================================================
    // KEYBOARD SHORTCUTS
    // ============================================================================
    
    function initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K: Focus search
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('.search-input-modern');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }
            
            // Escape: Close filters (mobile)
            if (e.key === 'Escape') {
                const filtersPanel = document.querySelector('.filters-panel');
                if (filtersPanel && filtersPanel.classList.contains('open')) {
                    filtersPanel.classList.remove('open');
                    document.body.style.overflow = '';
                }
            }
        });
    }

    // ============================================================================
    // LIVE TOURNAMENT UPDATES (OPTIONAL)
    // ============================================================================
    
    function initLiveUpdates() {
        const liveTournaments = document.querySelectorAll('[data-tournament-status="RUNNING"]');
        
        if (liveTournaments.length === 0) return;

        // Poll for updates every 30 seconds
        setInterval(() => {
            liveTournaments.forEach(tournament => {
                const tournamentId = tournament.dataset.tournamentId;
                
                if (tournamentId) {
                    fetchTournamentStatus(tournamentId).then(data => {
                        updateTournamentCard(tournament, data);
                    });
                }
            });
        }, 30000);
    }

    async function fetchTournamentStatus(tournamentId) {
        try {
            const response = await fetch(`/api/tournaments/${tournamentId}/status/`);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Failed to fetch tournament status:', error);
        }
        return null;
    }

    function updateTournamentCard(cardElement, data) {
        if (!data) return;

        // Update participant count
        const participantCount = cardElement.querySelector('[data-participant-count]');
        if (participantCount && data.current_participants) {
            participantCount.textContent = data.current_participants;
        }

        // Update progress bar
        const progressBar = cardElement.querySelector('.progress-modern-bar');
        if (progressBar && data.capacity_percentage) {
            progressBar.style.width = `${data.capacity_percentage}%`;
        }

        // Update status badge
        if (data.status === 'COMPLETED') {
            const liveBadge = cardElement.querySelector('.status-badge-live');
            if (liveBadge) {
                liveBadge.remove();
            }
        }
    }

    // ============================================================================
    // UTILITIES
    // ============================================================================
    
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

    function throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    // ============================================================================
    // LOGGING
    // ============================================================================
    
    function logInitSuccess() {
        console.log('%c✓ Tournament Hub V5 Initialized', 
            'color: #00ff88; font-weight: bold; font-size: 14px;');
        console.log('%cFeatures loaded:', 
            'color: #cbd5e1; font-weight: normal;');
        console.log('  • Modern search bar with smooth interactions');
        console.log('  • Mobile-responsive filters panel');
        console.log('  • Dynamic sorting and filtering');
        console.log('  • Animated progress bars');
        console.log('  • Smooth scroll to top');
        console.log('  • Quick action overlays');
    }

    // ============================================================================
    // ERROR HANDLING
    // ============================================================================
    
    window.addEventListener('error', (e) => {
        console.error('Tournament Hub V5 Error:', e.error);
    });

    // ============================================================================
    // EXPORTS (if using modules)
    // ============================================================================
    
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = {
            initSearchBar,
            initFiltersPanel,
            initSortDropdown,
            initScrollToTop,
            initQuickActions,
            initProgressBars
        };
    }

})();
