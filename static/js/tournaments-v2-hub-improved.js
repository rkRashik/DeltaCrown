/**
 * DeltaCrown Tournament Hub V2 - Improved & Polished
 * JavaScript for game filters, status filters, animations
 */

(function() {
    'use strict';

    // ============================================
    // STATE
    // ============================================
    const state = {
        currentGame: 'all',
        currentStatus: 'all',
        isScrolling: false
    };

    // ============================================
    // DOM ELEMENTS
    // ============================================
    const elements = {
        gameTabs: null,
        statusFilters: null,
        tournamentCards: null,
        scrollToTopBtn: null
    };

    // ============================================
    // INITIALIZATION
    // ============================================
    function init() {
        console.log('🎮 Initializing Tournament Hub V2 Improved...');
        
        // Cache DOM elements
        cacheElements();
        
        // Setup event listeners
        setupGameFilterListeners();
        setupStatusFilterListeners();
        setupScrollToTopButton();
        setupCardAnimations();
        
        // Initial filter
        filterTournaments();
        
        console.log('✅ Hub initialized successfully');
    }

    function cacheElements() {
        elements.gameTabs = document.querySelectorAll('.game-tab');
        elements.statusFilters = document.querySelectorAll('.status-filter');
        elements.tournamentCards = document.querySelectorAll('.tournament-card-modern');
        elements.scrollToTopBtn = document.querySelector('.scroll-to-top-btn');
    }

    // ============================================
    // GAME FILTER - Main Feature
    // ============================================
    function setupGameFilterListeners() {
        if (!elements.gameTabs || elements.gameTabs.length === 0) {
            console.warn('⚠️ No game filter tabs found');
            return;
        }

        elements.gameTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const gameSlug = this.getAttribute('data-game');
                console.log(`🎯 Switching to game filter: ${gameSlug}`);
                
                // Update active state
                elements.gameTabs.forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                // Update state and filter
                state.currentGame = gameSlug;
                filterTournaments();
            });
        });

        console.log(`✅ Game filter setup complete (${elements.gameTabs.length} tabs)`);
    }

    // ============================================
    // STATUS FILTER
    // ============================================
    function setupStatusFilterListeners() {
        if (!elements.statusFilters || elements.statusFilters.length === 0) {
            console.warn('⚠️ No status filters found');
            return;
        }

        elements.statusFilters.forEach(filter => {
            filter.addEventListener('click', function() {
                const status = this.getAttribute('data-status');
                console.log(`📊 Switching to status filter: ${status}`);
                
                // Update active state
                elements.statusFilters.forEach(f => f.classList.remove('active'));
                this.classList.add('active');
                
                // Update state and filter
                state.currentStatus = status;
                filterTournaments();
            });
        });

        console.log(`✅ Status filter setup complete (${elements.statusFilters.length} filters)`);
    }

    // ============================================
    // FILTER TOURNAMENTS - Core Logic
    // ============================================
    function filterTournaments() {
        if (!elements.tournamentCards || elements.tournamentCards.length === 0) {
            console.log('ℹ️ No tournament cards to filter');
            return;
        }

        let visibleCount = 0;

        elements.tournamentCards.forEach(card => {
            const cardGame = card.getAttribute('data-game');
            const cardStatus = card.getAttribute('data-status');
            
            // Check game filter
            const matchesGame = state.currentGame === 'all' || cardGame === state.currentGame;
            
            // Check status filter
            const matchesStatus = state.currentStatus === 'all' || cardStatus === state.currentStatus;
            
            // Show/hide card
            if (matchesGame && matchesStatus) {
                card.style.display = 'flex';
                card.style.animation = 'fadeInUp 0.4s ease-out';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });

        console.log(`🔍 Filter applied: ${visibleCount}/${elements.tournamentCards.length} tournaments visible`);
        
        // Show/hide empty state
        toggleEmptyState(visibleCount === 0);
    }

    // ============================================
    // EMPTY STATE
    // ============================================
    function toggleEmptyState(show) {
        const emptyState = document.querySelector('.empty-state-wrapper');
        const tournamentsGrid = document.querySelector('.tournaments-grid');
        
        if (!emptyState || !tournamentsGrid) return;

        if (show) {
            // Create empty state if it doesn't exist
            if (!tournamentsGrid.querySelector('.empty-state-wrapper')) {
                const emptyStateHTML = `
                    <div class="empty-state-wrapper">
                        <div class="empty-state-icon">🏆</div>
                        <h3 class="empty-state-title">No Tournaments Found</h3>
                        <p class="empty-state-text">Try adjusting your filters or check back later for new tournaments.</p>
                    </div>
                `;
                tournamentsGrid.insertAdjacentHTML('beforeend', emptyStateHTML);
            }
            emptyState.style.display = 'block';
        } else {
            if (emptyState) {
                emptyState.style.display = 'none';
            }
        }
    }

    // ============================================
    // SCROLL TO TOP BUTTON
    // ============================================
    function setupScrollToTopButton() {
        if (!elements.scrollToTopBtn) {
            console.warn('⚠️ Scroll to top button not found');
            return;
        }

        // Show/hide button on scroll
        let scrollTimeout;
        window.addEventListener('scroll', function() {
            clearTimeout(scrollTimeout);
            
            scrollTimeout = setTimeout(() => {
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                
                if (scrollTop > 500) {
                    elements.scrollToTopBtn.classList.add('visible');
                } else {
                    elements.scrollToTopBtn.classList.remove('visible');
                }
            }, 50);
        });

        // Click handler
        elements.scrollToTopBtn.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        console.log('✅ Scroll to top button setup complete');
    }

    // ============================================
    // CARD ANIMATIONS
    // ============================================
    function setupCardAnimations() {
        // Add CSS for card animations if not already present
        if (!document.getElementById('hub-card-animations')) {
            const style = document.createElement('style');
            style.id = 'hub-card-animations';
            style.textContent = `
                @keyframes fadeInUp {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                .tournament-card-modern {
                    animation: fadeInUp 0.4s ease-out;
                    animation-fill-mode: both;
                }
                
                .tournament-card-modern:nth-child(1) { animation-delay: 0s; }
                .tournament-card-modern:nth-child(2) { animation-delay: 0.1s; }
                .tournament-card-modern:nth-child(3) { animation-delay: 0.2s; }
                .tournament-card-modern:nth-child(4) { animation-delay: 0.3s; }
                .tournament-card-modern:nth-child(5) { animation-delay: 0.4s; }
                .tournament-card-modern:nth-child(6) { animation-delay: 0.5s; }
            `;
            document.head.appendChild(style);
        }

        console.log('✅ Card animations setup complete');
    }

    // ============================================
    // PROGRESS BAR ANIMATIONS
    // ============================================
    function animateProgressBars() {
        const progressBars = document.querySelectorAll('.progress-bar-fill');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const progressBar = entry.target;
                    const targetWidth = progressBar.getAttribute('style').match(/width:\s*(\d+)%/);
                    
                    if (targetWidth) {
                        progressBar.style.width = '0%';
                        setTimeout(() => {
                            progressBar.style.width = targetWidth[0];
                        }, 100);
                    }
                    
                    observer.unobserve(progressBar);
                }
            });
        }, { threshold: 0.5 });

        progressBars.forEach(bar => observer.observe(bar));
    }

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================
    
    /**
     * Debounce function for performance
     */
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

    /**
     * Smooth scroll to element
     */
    function smoothScrollTo(element, offset = 100) {
        const targetPosition = element.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
        });
    }

    // ============================================
    // KEYBOARD NAVIGATION
    // ============================================
    function setupKeyboardNavigation() {
        document.addEventListener('keydown', function(e) {
            // ESC key - reset filters
            if (e.key === 'Escape') {
                resetAllFilters();
            }
            
            // Number keys 1-9 for game tabs
            if (e.key >= '1' && e.key <= '9') {
                const index = parseInt(e.key) - 1;
                if (elements.gameTabs[index]) {
                    elements.gameTabs[index].click();
                }
            }
        });
    }

    /**
     * Reset all filters to default state
     */
    function resetAllFilters() {
        // Reset game filter
        state.currentGame = 'all';
        elements.gameTabs.forEach(tab => {
            if (tab.getAttribute('data-game') === 'all') {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // Reset status filter
        state.currentStatus = 'all';
        elements.statusFilters.forEach(filter => {
            if (filter.getAttribute('data-status') === 'all') {
                filter.classList.add('active');
            } else {
                filter.classList.remove('active');
            }
        });

        // Reapply filters
        filterTournaments();
        
        console.log('🔄 Filters reset to default');
    }

    // ============================================
    // URL PARAMETER HANDLING
    // ============================================
    function loadFiltersFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const gameParam = urlParams.get('game');
        const statusParam = urlParams.get('status');

        if (gameParam) {
            const gameTab = document.querySelector(`.game-tab[data-game="${gameParam}"]`);
            if (gameTab) {
                gameTab.click();
            }
        }

        if (statusParam) {
            const statusFilter = document.querySelector(`.status-filter[data-status="${statusParam}"]`);
            if (statusFilter) {
                statusFilter.click();
            }
        }
    }

    function updateURLWithFilters() {
        const url = new URL(window.location);
        
        if (state.currentGame !== 'all') {
            url.searchParams.set('game', state.currentGame);
        } else {
            url.searchParams.delete('game');
        }

        if (state.currentStatus !== 'all') {
            url.searchParams.set('status', state.currentStatus);
        } else {
            url.searchParams.delete('status');
        }

        window.history.replaceState({}, '', url);
    }

    // ============================================
    // PUBLIC API
    // ============================================
    window.TournamentHub = {
        init,
        filterTournaments,
        resetFilters: resetAllFilters,
        setGameFilter: (game) => {
            state.currentGame = game;
            filterTournaments();
        },
        setStatusFilter: (status) => {
            state.currentStatus = status;
            filterTournaments();
        },
        getState: () => ({ ...state })
    };

    // ============================================
    // INITIALIZATION
    // ============================================
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Load filters from URL after initialization
    window.addEventListener('load', function() {
        loadFiltersFromURL();
        animateProgressBars();
        setupKeyboardNavigation();
    });

})();
