// ========================================
// MODERN TEAM LIST - JAVASCRIPT
// ========================================

(function() {
    'use strict';

    // DOM Elements
    const teamSearch = document.getElementById('team-search');
    const searchClear = document.getElementById('search-clear');
    const sortSelect = document.getElementById('sort-select');
    const loadMoreBtn = document.getElementById('load-more-btn');
    const teamsGrid = document.getElementById('teams-grid');
    const loadingOverlay = document.getElementById('loading-overlay');

    // State
    let currentPage = 1;
    let isLoading = false;
    let searchTimeout = null;

    // ========================================
    // INITIALIZATION
    // ========================================

    function init() {
        setupEventListeners();
        setupAnimations();
        setupCardIndexes();
    }

    // ========================================
    // EVENT LISTENERS
    // ========================================

    function setupEventListeners() {
        // Search input
        if (teamSearch) {
            teamSearch.addEventListener('input', handleSearch);
            teamSearch.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    performSearch();
                }
            });
        }

        // Search clear button
        if (searchClear) {
            searchClear.addEventListener('click', clearSearch);
        }

        // Sort select
        if (sortSelect) {
            sortSelect.addEventListener('change', handleSort);
        }

        // Load more button
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', loadMoreTeams);
        }

        // Team cards click
        setupCardClicks();
    }

    // ========================================
    // SEARCH FUNCTIONALITY
    // ========================================

    function handleSearch() {
        const query = teamSearch.value.trim();
        
        // Show/hide clear button
        if (searchClear) {
            searchClear.style.display = query ? 'block' : 'none';
        }

        // Debounce search
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            performSearch();
        }, 500);
    }

    function performSearch() {
        const query = teamSearch.value.trim();
        const activeGame = getActiveGame();
        const sort = sortSelect ? sortSelect.value : '';

        // Build URL
        const params = new URLSearchParams();
        if (query) params.append('q', query);
        if (activeGame) params.append('game', activeGame);
        if (sort) params.append('sort', sort);

        // Navigate to filtered results
        window.location.href = `?${params.toString()}`;
    }

    function clearSearch() {
        if (teamSearch) {
            teamSearch.value = '';
            teamSearch.focus();
        }
        if (searchClear) {
            searchClear.style.display = 'none';
        }
        performSearch();
    }

    // ========================================
    // SORT FUNCTIONALITY
    // ========================================

    function handleSort() {
        const sort = sortSelect.value;
        const query = teamSearch ? teamSearch.value.trim() : '';
        const activeGame = getActiveGame();

        // Build URL
        const params = new URLSearchParams();
        if (query) params.append('q', query);
        if (activeGame) params.append('game', activeGame);
        if (sort) params.append('sort', sort);

        // Show loading
        showLoading();

        // Navigate to sorted results
        window.location.href = `?${params.toString()}`;
    }

    // ========================================
    // LOAD MORE FUNCTIONALITY
    // ========================================

    function loadMoreTeams() {
        if (isLoading) return;

        isLoading = true;
        const nextPage = loadMoreBtn.dataset.nextPage;

        // Show loading state
        loadMoreBtn.disabled = true;
        loadMoreBtn.innerHTML = '<span>Loading...</span><i class="fas fa-spinner fa-spin"></i>';

        // Build URL with params
        const params = new URLSearchParams(window.location.search);
        params.set('page', nextPage);

        // Fetch next page
        fetch(`?${params.toString()}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.text())
        .then(html => {
            // Parse HTML
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Get new team cards
            const newCards = doc.querySelectorAll('.team-card');
            
            if (newCards.length > 0) {
                // Append new cards
                newCards.forEach((card, index) => {
                    card.style.setProperty('--index', teamsGrid.children.length + index);
                    teamsGrid.insertBefore(card, loadMoreBtn.parentElement);
                });

                // Update page number
                currentPage = parseInt(nextPage);
                
                // Check if there are more pages
                const nextPageBtn = doc.getElementById('load-more-btn');
                if (nextPageBtn) {
                    loadMoreBtn.dataset.nextPage = nextPageBtn.dataset.nextPage;
                    loadMoreBtn.disabled = false;
                    loadMoreBtn.innerHTML = '<span>Load More Teams</span><i class="fas fa-chevron-down"></i>';
                } else {
                    // No more pages
                    loadMoreBtn.parentElement.remove();
                }

                // Setup clicks for new cards
                setupCardClicks();
            } else {
                // No more results
                loadMoreBtn.parentElement.remove();
            }
        })
        .catch(error => {
            console.error('Error loading more teams:', error);
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerHTML = '<span>Load More Teams</span><i class="fas fa-chevron-down"></i>';
            showNotification('Failed to load more teams', 'error');
        })
        .finally(() => {
            isLoading = false;
        });
    }

    // ========================================
    // ANIMATIONS
    // ========================================

    function setupAnimations() {
        // Intersection Observer for scroll animations
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animationPlayState = 'running';
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1
        });

        // Observe team cards
        document.querySelectorAll('.team-card').forEach(card => {
            card.style.animationPlayState = 'paused';
            observer.observe(card);
        });
    }

    function setupCardIndexes() {
        // Set animation delay index for each card
        document.querySelectorAll('.team-card').forEach((card, index) => {
            card.style.setProperty('--index', index);
        });
    }

    // ========================================
    // CARD INTERACTIONS
    // ========================================

    function setupCardClicks() {
        document.querySelectorAll('.team-card').forEach(card => {
            // Remove previous listeners to avoid duplicates
            const newCard = card.cloneNode(true);
            card.parentNode.replaceChild(newCard, card);

            // Add click listener
            newCard.addEventListener('click', function(e) {
                // Don't navigate if clicking on action buttons
                if (e.target.closest('.team-actions')) {
                    return;
                }
                
                const url = this.getAttribute('onclick');
                if (url) {
                    eval(url);
                }
            });
        });
    }

    // ========================================
    // UTILITY FUNCTIONS
    // ========================================

    function getActiveGame() {
        const params = new URLSearchParams(window.location.search);
        return params.get('game') || '';
    }

    function showLoading() {
        if (loadingOverlay) {
            loadingOverlay.classList.add('active');
        }
    }

    function hideLoading() {
        if (loadingOverlay) {
            loadingOverlay.classList.remove('active');
        }
    }

    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            z-index: 10000;
            animation: slideInRight 0.3s ease-out;
        `;

        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // ========================================
    // GLOBAL FUNCTIONS (for onclick handlers)
    // ========================================

    window.joinTeam = function(teamSlug) {
        // Check if user is authenticated
        const isAuthenticated = document.body.dataset.authenticated === 'true';
        
        if (!isAuthenticated) {
            window.location.href = '/admin/login/?next=/teams/' + teamSlug + '/';
            return;
        }

        // Show loading
        showLoading();

        // Send join request
        fetch(`/teams/${teamSlug}/join/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            hideLoading();
            if (data.success) {
                showNotification('Join request sent successfully!', 'success');
                setTimeout(() => {
                    window.location.href = `/teams/${teamSlug}/`;
                }, 1500);
            } else {
                showNotification(data.message || 'Failed to send join request', 'error');
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error:', error);
            showNotification('An error occurred', 'error');
        });
    };

    // ========================================
    // HELPERS
    // ========================================

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // ========================================
    // INITIALIZE ON DOM READY
    // ========================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Hide loading overlay when page fully loads
    window.addEventListener('load', hideLoading);

})();

// ========================================
// CSS ANIMATIONS (inject into page)
// ========================================

const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
