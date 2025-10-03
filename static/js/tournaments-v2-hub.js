/**
 * DeltaCrown Tournament Hub V2 - JavaScript
 * Modern Esports Tournament Hub with Advanced Features
 * 
 * Features:
 * - Real-time search and filtering
 * - Game tab navigation
 * - Smooth animations
 * - Lazy loading
 * - State management
 */

(function() {
    'use strict';

    // ============================================
    // STATE MANAGEMENT
    // ============================================
    
    const HubState = {
        currentGame: 'all',
        currentStatus: 'all',
        searchQuery: '',
        currentPage: 1,
        tournaments: [],
        filteredTournaments: []
    };

    // ============================================
    // DOM ELEMENTS
    // ============================================
    
    const elements = {
        searchInput: null,
        gameTabsContainer: null,
        gameTabs: null,
        statusFilters: null,
        tournamentsGrid: null,
        emptyState: null,
        pagination: null
    };

    // ============================================
    // INITIALIZATION
    // ============================================
    
    function init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupHub);
        } else {
            setupHub();
        }
    }

    function setupHub() {
        console.log('[Hub V2] Initializing tournament hub...');
        
        // Cache DOM elements
        cacheElements();
        
        // Setup event listeners
        setupEventListeners();
        
        // Load initial tournaments
        loadTournaments();
        
        // Setup animations
        setupAnimations();
        
        // Initialize countdown timers (Phase B integration)
        if (typeof window.initializeCountdownTimers === 'function') {
            window.initializeCountdownTimers();
        }
        
        console.log('[Hub V2] Hub initialized successfully');
    }

    function cacheElements() {
        elements.searchInput = document.getElementById('hub-search');
        elements.gameTabsContainer = document.querySelector('.hub-game-tabs');
        elements.gameTabs = document.querySelectorAll('.game-tab');
        elements.statusFilters = document.querySelectorAll('.filter-pill');
        elements.tournamentsGrid = document.querySelector('.tournament-grid');
        elements.emptyState = document.querySelector('.hub-empty');
        elements.pagination = document.querySelector('.hub-pagination');
    }

    // ============================================
    // EVENT LISTENERS
    // ============================================
    
    function setupEventListeners() {
        // Search input
        if (elements.searchInput) {
            elements.searchInput.addEventListener('input', debounce(handleSearch, 300));
        }
        
        // Game tabs
        if (elements.gameTabs) {
            elements.gameTabs.forEach(tab => {
                tab.addEventListener('click', handleGameTabClick);
            });
        }
        
        // Status filters
        if (elements.statusFilters) {
            elements.statusFilters.forEach(filter => {
                filter.addEventListener('click', handleStatusFilterClick);
            });
        }
        
        // Tournament cards - delegate event
        if (elements.tournamentsGrid) {
            elements.tournamentsGrid.addEventListener('click', handleTournamentCardClick);
        }
        
        // Pagination
        setupPaginationListeners();
        
        // Window resize for responsive adjustments
        window.addEventListener('resize', debounce(handleResize, 300));
        
        // Keyboard shortcuts
        document.addEventListener('keydown', handleKeyboardShortcuts);
    }

    // ============================================
    // SEARCH FUNCTIONALITY
    // ============================================
    
    function handleSearch(event) {
        const query = event.target.value.trim().toLowerCase();
        HubState.searchQuery = query;
        
        console.log('[Hub V2] Search query:', query);
        
        // Filter tournaments
        filterTournaments();
        
        // Update URL with query parameter
        updateURLParams();
    }

    // ============================================
    // GAME TAB NAVIGATION
    // ============================================
    
    function handleGameTabClick(event) {
        event.preventDefault();
        
        const tab = event.currentTarget;
        const game = tab.dataset.game || 'all';
        
        // Update active state
        elements.gameTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Update state
        HubState.currentGame = game;
        HubState.currentPage = 1;
        
        console.log('[Hub V2] Game tab clicked:', game);
        
        // Filter tournaments
        filterTournaments();
        
        // Update URL
        updateURLParams();
        
        // Scroll to grid
        smoothScrollTo(elements.tournamentsGrid, -100);
    }

    // ============================================
    // STATUS FILTERS
    // ============================================
    
    function handleStatusFilterClick(event) {
        const filter = event.currentTarget;
        const status = filter.dataset.status || 'all';
        
        // Toggle active state
        elements.statusFilters.forEach(f => f.classList.remove('active'));
        filter.classList.add('active');
        
        // Update state
        HubState.currentStatus = status;
        HubState.currentPage = 1;
        
        console.log('[Hub V2] Status filter clicked:', status);
        
        // Filter tournaments
        filterTournaments();
        
        // Update URL
        updateURLParams();
    }

    // ============================================
    // TOURNAMENT LOADING
    // ============================================
    
    function loadTournaments() {
        console.log('[Hub V2] Loading tournaments...');
        
        // Get tournaments from DOM or fetch from API
        const tournamentCards = document.querySelectorAll('.tournament-card-v2');
        
        HubState.tournaments = Array.from(tournamentCards).map(card => ({
            element: card,
            id: card.dataset.tournamentId,
            title: card.dataset.title?.toLowerCase() || '',
            game: card.dataset.game?.toLowerCase() || '',
            status: card.dataset.status?.toLowerCase() || '',
            startDate: card.dataset.startDate || '',
            prizePool: card.dataset.prizePool || ''
        }));
        
        console.log('[Hub V2] Loaded tournaments:', HubState.tournaments.length);
        
        // Initial filter
        filterTournaments();
    }

    // ============================================
    // FILTERING LOGIC
    // ============================================
    
    function filterTournaments() {
        const { searchQuery, currentGame, currentStatus } = HubState;
        
        console.log('[Hub V2] Filtering:', { searchQuery, currentGame, currentStatus });
        
        HubState.filteredTournaments = HubState.tournaments.filter(tournament => {
            // Search filter
            const matchesSearch = !searchQuery || 
                tournament.title.includes(searchQuery) ||
                tournament.game.includes(searchQuery);
            
            // Game filter
            const matchesGame = currentGame === 'all' || 
                tournament.game === currentGame;
            
            // Status filter
            const matchesStatus = currentStatus === 'all' || 
                tournament.status === currentStatus;
            
            return matchesSearch && matchesGame && matchesStatus;
        });
        
        console.log('[Hub V2] Filtered tournaments:', HubState.filteredTournaments.length);
        
        // Update display
        updateTournamentDisplay();
    }

    function updateTournamentDisplay() {
        const { filteredTournaments } = HubState;
        
        // Hide all tournaments first
        HubState.tournaments.forEach(t => {
            t.element.style.display = 'none';
            t.element.classList.remove('fade-in-up');
        });
        
        // Show filtered tournaments with animation
        if (filteredTournaments.length > 0) {
            filteredTournaments.forEach((tournament, index) => {
                setTimeout(() => {
                    tournament.element.style.display = 'block';
                    tournament.element.classList.add('fade-in-up');
                }, index * 50); // Stagger animation
            });
            
            // Hide empty state
            if (elements.emptyState) {
                elements.emptyState.style.display = 'none';
            }
        } else {
            // Show empty state
            if (elements.emptyState) {
                elements.emptyState.style.display = 'block';
            }
        }
        
        // Update pagination
        updatePagination();
    }

    // ============================================
    // TOURNAMENT CARD INTERACTIONS
    // ============================================
    
    function handleTournamentCardClick(event) {
        // Check if clicked element is a button or link
        if (event.target.closest('.tournament-card-btn') || 
            event.target.closest('a')) {
            return; // Let default behavior happen
        }
        
        // Navigate to tournament detail
        const card = event.target.closest('.tournament-card-v2');
        if (card) {
            const tournamentId = card.dataset.tournamentId;
            const detailUrl = card.dataset.detailUrl;
            
            if (detailUrl) {
                window.location.href = detailUrl;
            } else if (tournamentId) {
                window.location.href = `/tournaments/${tournamentId}/`;
            }
        }
    }

    // ============================================
    // PAGINATION
    // ============================================
    
    function setupPaginationListeners() {
        const prevBtn = document.querySelector('[data-pagination="prev"]');
        const nextBtn = document.querySelector('[data-pagination="next"]');
        
        if (prevBtn) {
            prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                if (HubState.currentPage > 1) {
                    HubState.currentPage--;
                    filterTournaments();
                    smoothScrollTo(elements.tournamentsGrid, -100);
                }
            });
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                const maxPage = Math.ceil(HubState.filteredTournaments.length / 12);
                if (HubState.currentPage < maxPage) {
                    HubState.currentPage++;
                    filterTournaments();
                    smoothScrollTo(elements.tournamentsGrid, -100);
                }
            });
        }
    }

    function updatePagination() {
        if (!elements.pagination) return;
        
        const totalTournaments = HubState.filteredTournaments.length;
        const totalPages = Math.ceil(totalTournaments / 12);
        const currentPage = HubState.currentPage;
        
        const paginationInfo = elements.pagination.querySelector('.hub-pagination-info');
        const prevBtn = elements.pagination.querySelector('[data-pagination="prev"]');
        const nextBtn = elements.pagination.querySelector('[data-pagination="next"]');
        
        if (paginationInfo) {
            const start = (currentPage - 1) * 12 + 1;
            const end = Math.min(currentPage * 12, totalTournaments);
            paginationInfo.textContent = `${start}-${end} of ${totalTournaments}`;
        }
        
        if (prevBtn) {
            prevBtn.classList.toggle('disabled', currentPage === 1);
        }
        
        if (nextBtn) {
            nextBtn.classList.toggle('disabled', currentPage === totalPages);
        }
    }

    // ============================================
    // URL MANAGEMENT
    // ============================================
    
    function updateURLParams() {
        const params = new URLSearchParams();
        
        if (HubState.searchQuery) {
            params.set('q', HubState.searchQuery);
        }
        
        if (HubState.currentGame !== 'all') {
            params.set('game', HubState.currentGame);
        }
        
        if (HubState.currentStatus !== 'all') {
            params.set('status', HubState.currentStatus);
        }
        
        if (HubState.currentPage > 1) {
            params.set('page', HubState.currentPage);
        }
        
        const newURL = params.toString() ? 
            `${window.location.pathname}?${params.toString()}` : 
            window.location.pathname;
        
        window.history.replaceState({}, '', newURL);
    }

    function loadStateFromURL() {
        const params = new URLSearchParams(window.location.search);
        
        HubState.searchQuery = params.get('q') || '';
        HubState.currentGame = params.get('game') || 'all';
        HubState.currentStatus = params.get('status') || 'all';
        HubState.currentPage = parseInt(params.get('page')) || 1;
        
        // Update UI to match state
        if (elements.searchInput && HubState.searchQuery) {
            elements.searchInput.value = HubState.searchQuery;
        }
        
        // Update active game tab
        if (elements.gameTabs) {
            elements.gameTabs.forEach(tab => {
                tab.classList.toggle('active', 
                    tab.dataset.game === HubState.currentGame);
            });
        }
        
        // Update active status filter
        if (elements.statusFilters) {
            elements.statusFilters.forEach(filter => {
                filter.classList.toggle('active', 
                    filter.dataset.status === HubState.currentStatus);
            });
        }
    }

    // ============================================
    // ANIMATIONS
    // ============================================
    
    function setupAnimations() {
        // Observe tournament cards for lazy loading
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('fade-in-up');
                        observer.unobserve(entry.target);
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '50px'
            });
            
            // Observe all tournament cards
            document.querySelectorAll('.tournament-card-v2').forEach(card => {
                observer.observe(card);
            });
        }
    }

    // ============================================
    // KEYBOARD SHORTCUTS
    // ============================================
    
    function handleKeyboardShortcuts(event) {
        // Ctrl/Cmd + K = Focus search
        if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
            event.preventDefault();
            if (elements.searchInput) {
                elements.searchInput.focus();
            }
        }
        
        // ESC = Clear search
        if (event.key === 'Escape' && elements.searchInput === document.activeElement) {
            elements.searchInput.value = '';
            elements.searchInput.blur();
            HubState.searchQuery = '';
            filterTournaments();
        }
    }

    // ============================================
    // RESPONSIVE HANDLING
    // ============================================
    
    function handleResize() {
        console.log('[Hub V2] Window resized');
        // Add any responsive adjustments here
    }

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================
    
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

    function smoothScrollTo(element, offset = 0) {
        if (!element) return;
        
        const elementPosition = element.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset + offset;
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }

    // ============================================
    // PUBLIC API
    // ============================================
    
    window.TournamentHubV2 = {
        init,
        filterTournaments,
        updateTournamentDisplay,
        getState: () => ({ ...HubState }),
        setState: (newState) => {
            Object.assign(HubState, newState);
            filterTournaments();
        }
    };

    // Auto-initialize
    init();

})();
