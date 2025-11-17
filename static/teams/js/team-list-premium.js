// ========================================
// DELTACROWN PREMIUM TEAM LIST
// Feature-Rich Team Management System
// ========================================

(function() {
    'use strict';

    // ========================================
    // STATE MANAGEMENT
    // ========================================
    const state = {
        currentView: 'grid',
        currentGame: 'all',
        searchQuery: '',
        sortBy: 'rank',
        filters: {
            verified: false,
            recruiting: false,
            featured: false,
            region: '',
            minMembers: '',
            maxMembers: ''
        },
        page: 1,
        loading: false,
        hasMore: true
    };

    // ========================================
    // DOM ELEMENTS
    // ========================================
    const elements = {
        searchInput: document.getElementById('team-search-premium'),
        searchLoader: document.querySelector('.search-loader'),
        gameFilters: document.querySelectorAll('.game-filter-premium'),
        filterGameList: document.getElementById('filterGameList'),
        viewBtns: document.querySelectorAll('.view-btn'),
        teamsContainer: document.querySelector('.teams-container'),
        sortSelect: document.getElementById('sort-select-premium'),
        resultsCount: document.querySelector('.results-count'),
        filterToggle: document.querySelector('.btn-filters'),
        advancedFilters: document.getElementById('advanced-filters'),
        filterChips: document.querySelectorAll('.filter-chip'),
        regionSelect: document.getElementById('regionFilter'),
        minMembersInput: document.getElementById('minMembers'),
        maxMembersInput: document.getElementById('maxMembers'),
        applyFiltersBtn: document.querySelector('.apply-filters-btn'),
        resetFiltersBtn: document.querySelector('.reset-filters-btn'),
        activeFiltersContainer: document.querySelector('.active-filters-container'),
        loadMoreBtn: document.querySelector('.load-more-btn'),
        scrollLeftBtn: document.getElementById('scroll-left'),
        scrollRightBtn: document.getElementById('scroll-right'),
        gameFiltersScroll: document.getElementById('game-filters-scroll'),
        scrollToTopBtn: document.querySelector('.scroll-to-top')
    };

    // ========================================
    // INITIALIZATION
    // ========================================
    function init() {
        // Check if we're on the team list page
        if (!elements.teamsContainer) {
            return;
        }

        setupEventListeners();
        loadViewPreference();
        checkScrollButtons();
        updateActiveFilters();
        
        console.log('✅ Premium Team List initialized');
    }

    // ========================================
    // EVENT LISTENERS
    // ========================================
    function setupEventListeners() {
        // Search with debounce
        if (elements.searchInput) {
            let searchTimeout;
            elements.searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                showSearchLoader();
                
                searchTimeout = setTimeout(() => {
                    state.searchQuery = e.target.value.trim();
                    state.page = 1;
                    performSearch();
                }, 500);
            });
        }

        // Game filters - Use natural navigation since links have href
        // No need to prevent default or use AJAX, the links work fine
        elements.gameFilters.forEach(filter => {
            // Just add visual feedback on click
            filter.addEventListener('click', (e) => {
                // Let the link navigate naturally
                filter.classList.add('loading');
            });
        });

        // View switcher
        elements.viewBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const view = btn.dataset.view;
                switchView(view);
            });
        });

        // Sort dropdown
        if (elements.sortSelect) {
            elements.sortSelect.addEventListener('change', (e) => {
                state.sortBy = e.target.value;
                state.page = 1;
                loadTeams();
            });
        }

        // Filter toggle
        if (elements.filterToggle) {
            elements.filterToggle.addEventListener('click', () => {
                toggleAdvancedFilters();
            });
        }

        // Filter chips
        elements.filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                toggleFilterChip(chip);
            });
        });

        // Apply filters
        if (elements.applyFiltersBtn) {
            elements.applyFiltersBtn.addEventListener('click', () => {
                applyFilters();
            });
        }

        // Reset filters
        if (elements.resetFiltersBtn) {
            elements.resetFiltersBtn.addEventListener('click', () => {
                resetFilters();
            });
        }

        // Load more
        if (elements.loadMoreBtn) {
            elements.loadMoreBtn.addEventListener('click', () => {
                loadMoreTeams();
            });
        }

        // Horizontal scroll for game filters
        if (elements.scrollLeftBtn && elements.gameFiltersScroll) {
            elements.scrollLeftBtn.addEventListener('click', () => {
                elements.gameFiltersScroll.scrollBy({ left: -300, behavior: 'smooth' });
            });
        }

        if (elements.scrollRightBtn && elements.gameFiltersScroll) {
            elements.scrollRightBtn.addEventListener('click', () => {
                elements.gameFiltersScroll.scrollBy({ left: 300, behavior: 'smooth' });
            });
            
            elements.gameFiltersScroll.addEventListener('scroll', checkScrollButtons);
        }

        // Scroll to top
        if (elements.scrollToTopBtn) {
            window.addEventListener('scroll', handleScroll);
            elements.scrollToTopBtn.addEventListener('click', scrollToTop);
        }

        // Quick join buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('quick-join-btn')) {
                e.preventDefault();
                const teamId = e.target.dataset.teamId;
                showQuickJoinModal(teamId);
            }
        });
    }

    // ========================================
    // SEARCH FUNCTIONALITY
    // ========================================
    function performSearch() {
        hideSearchLoader();
        state.page = 1;
        loadTeams();
    }

    function showSearchLoader() {
        if (elements.searchLoader) {
            elements.searchLoader.style.display = 'block';
        }
    }

    function hideSearchLoader() {
        if (elements.searchLoader) {
            elements.searchLoader.style.display = 'none';
        }
    }

    // ========================================
    // GAME SELECTION
    // ========================================
    function selectGame(game) {
        // This function is no longer used - game filtering uses standard navigation
        // Keeping it here for potential future AJAX implementation
        return;
        
        // Update state
        state.currentGame = game;
        state.page = 1;

        // Update UI
        elements.gameFilters.forEach(filter => {
            if (filter.dataset.game === game) {
                filter.classList.add('active');
            } else {
                filter.classList.remove('active');
            }
        });

        // Load teams
        // loadTeams(); // Disabled - using standard navigation
    }

    // ========================================
    // VIEW SWITCHING
    // ========================================
    function switchView(view) {
        state.currentView = view;

        // Update buttons
        elements.viewBtns.forEach(btn => {
            if (btn.dataset.view === view) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Update container
        if (elements.teamsContainer) {
            if (view === 'grid') {
                elements.teamsContainer.classList.remove('list-view');
            } else {
                elements.teamsContainer.classList.add('list-view');
            }
        }

        // Save preference
        localStorage.setItem('teamListView', view);
    }

    function loadViewPreference() {
        const savedView = localStorage.getItem('teamListView') || 'grid';
        switchView(savedView);
    }

    // ========================================
    // ADVANCED FILTERS
    // ========================================
    function toggleAdvancedFilters() {
        if (elements.advancedFilters) {
            const isVisible = elements.advancedFilters.style.display === 'block';
            elements.advancedFilters.style.display = isVisible ? 'none' : 'block';
            
            if (elements.filterToggle) {
                const badge = elements.filterToggle.querySelector('.filter-badge');
                if (!isVisible && badge) {
                    badge.style.display = 'flex';
                }
            }
        }
    }

    function toggleFilterChip(chip) {
        chip.classList.toggle('active');
        const filterType = chip.dataset.filter;
        state.filters[filterType] = chip.classList.contains('active');
    }

    function applyFilters() {
        // Update filters from inputs
        if (elements.regionSelect) {
            state.filters.region = elements.regionSelect.value;
        }
        if (elements.minMembersInput) {
            state.filters.minMembers = elements.minMembersInput.value;
        }
        if (elements.maxMembersInput) {
            state.filters.maxMembers = elements.maxMembersInput.value;
        }

        // Reset page and load
        state.page = 1;
        loadTeams();
        updateActiveFilters();

        // Close filters panel
        if (elements.advancedFilters) {
            elements.advancedFilters.style.display = 'none';
        }

        showToast('Filters applied successfully', 'success');
    }

    function resetFilters() {
        // Reset state
        state.filters = {
            verified: false,
            recruiting: false,
            featured: false,
            region: '',
            minMembers: '',
            maxMembers: ''
        };

        // Reset UI
        elements.filterChips.forEach(chip => {
            chip.classList.remove('active');
        });

        if (elements.regionSelect) elements.regionSelect.value = '';
        if (elements.minMembersInput) elements.minMembersInput.value = '';
        if (elements.maxMembersInput) elements.maxMembersInput.value = '';

        // Reload
        state.page = 1;
        loadTeams();
        updateActiveFilters();

        showToast('Filters cleared', 'info');
    }

    function updateActiveFilters() {
        if (!elements.activeFiltersContainer) return;

        const activeFilters = [];

        // Check boolean filters
        if (state.filters.verified) activeFilters.push({ label: 'Verified', key: 'verified' });
        if (state.filters.recruiting) activeFilters.push({ label: 'Recruiting', key: 'recruiting' });
        if (state.filters.featured) activeFilters.push({ label: 'Featured', key: 'featured' });
        
        // Check other filters
        if (state.filters.region) activeFilters.push({ label: `Region: ${state.filters.region}`, key: 'region' });
        if (state.filters.minMembers) activeFilters.push({ label: `Min: ${state.filters.minMembers}`, key: 'minMembers' });
        if (state.filters.maxMembers) activeFilters.push({ label: `Max: ${state.filters.maxMembers}`, key: 'maxMembers' });

        // Render active filters
        if (activeFilters.length > 0) {
            elements.activeFiltersContainer.style.display = 'block';
            const filtersHtml = activeFilters.map(filter => `
                <span class="active-filter-tag">
                    ${filter.label}
                    <i class="fas fa-times" data-filter="${filter.key}"></i>
                </span>
            `).join('');
            
            elements.activeFiltersContainer.innerHTML = `
                <div class="active-filters-list">
                    ${filtersHtml}
                    <button class="clear-all-filters">Clear All</button>
                </div>
            `;

            // Add remove listeners
            elements.activeFiltersContainer.querySelectorAll('.fa-times').forEach(icon => {
                icon.addEventListener('click', () => {
                    const filterKey = icon.dataset.filter;
                    removeFilter(filterKey);
                });
            });

            elements.activeFiltersContainer.querySelector('.clear-all-filters')?.addEventListener('click', resetFilters);
        } else {
            elements.activeFiltersContainer.style.display = 'none';
        }

        // Update badge count
        if (elements.filterToggle) {
            const badge = elements.filterToggle.querySelector('.filter-badge');
            if (badge) {
                if (activeFilters.length > 0) {
                    badge.textContent = activeFilters.length;
                    badge.style.display = 'flex';
                } else {
                    badge.style.display = 'none';
                }
            }
        }
    }

    function removeFilter(key) {
        if (key === 'region' || key === 'minMembers' || key === 'maxMembers') {
            state.filters[key] = '';
            const inputMap = {
                region: elements.regionSelect,
                minMembers: elements.minMembersInput,
                maxMembers: elements.maxMembersInput
            };
            if (inputMap[key]) inputMap[key].value = '';
        } else {
            state.filters[key] = false;
            const chip = document.querySelector(`.filter-chip[data-filter="${key}"]`);
            if (chip) chip.classList.remove('active');
        }

        state.page = 1;
        loadTeams();
        updateActiveFilters();
    }

    // ========================================
    // LOAD TEAMS (AJAX)
    // ========================================
    function loadTeams() {
        if (state.loading) return;

        state.loading = true;
        showLoadingOverlay();

        // Build query params
        const params = new URLSearchParams({
            game: state.currentGame,
            search: state.searchQuery,
            sort: state.sortBy,
            page: state.page,
            verified: state.filters.verified,
            recruiting: state.filters.recruiting,
            featured: state.filters.featured
        });

        if (state.filters.region) params.append('region', state.filters.region);
        if (state.filters.minMembers) params.append('min_members', state.filters.minMembers);
        if (state.filters.maxMembers) params.append('max_members', state.filters.maxMembers);

        // Make request
        fetch(`/teams/api/list/?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                if (state.page === 1) {
                    renderTeams(data.teams);
                } else {
                    appendTeams(data.teams);
                }

                updateResultsCount(data.total);
                state.hasMore = data.has_more;
                updateLoadMoreButton();

                state.loading = false;
                hideLoadingOverlay();
            })
            .catch(error => {
                console.error('Error loading teams:', error);
                showToast('Failed to load teams', 'error');
                state.loading = false;
                hideLoadingOverlay();
            });
    }

    function loadMoreTeams() {
        if (!state.hasMore || state.loading) return;
        
        state.page++;
        loadTeams();
    }

    function renderTeams(teams) {
        if (!elements.teamsContainer) return;

        if (teams.length === 0) {
            elements.teamsContainer.innerHTML = `
                <div class="empty-state-premium">
                    <i class="fas fa-search"></i>
                    <h3>No Teams Found</h3>
                    <p>Try adjusting your search or filters</p>
                </div>
            `;
            return;
        }

        const teamsHtml = teams.map((team, index) => createTeamCard(team, index)).join('');
        elements.teamsContainer.innerHTML = teamsHtml;
        
        // Extract banner colors for dynamic gradient
        extractBannerColors();
    }

    function appendTeams(teams) {
        if (!elements.teamsContainer) return;

        const teamsHtml = teams.map((team, index) => createTeamCard(team, index + state.page * 20)).join('');
        elements.teamsContainer.insertAdjacentHTML('beforeend', teamsHtml);
        
        // Extract banner colors for dynamic gradient
        extractBannerColors();
    }

    function createTeamCard(team, index) {
        const isPodium = index < 3;
        const podiumClass = isPodium ? `podium-team podium-${index + 1}` : '';
        const rankBadge = isPodium ? getPodiumBadge(index) : `<div class="rank-badge-normal">#${team.rank || index + 1}</div>`;
        
        return `
            <div class="team-card-premium ${podiumClass}" data-team-id="${team.id}" data-banner="${team.banner || ''}">
                ${rankBadge}
                <div class="team-banner-advanced">
                    <img src="${team.banner || '/static/img/default-banner.jpg'}" alt="${team.name} Banner" class="banner-img" crossorigin="anonymous">
                    <div class="banner-overlay-gradient"></div>
                    ${getBannerBadges(team)}
                </div>
                <div class="team-logo-premium">
                    <div class="logo-container">
                        ${team.logo ? `<img src="${team.logo}" alt="${team.name}" class="logo-img">` : `<div class="logo-placeholder">${team.name[0]}</div>`}
                    </div>
                </div>
                <div class="team-info-premium">
                    <div class="team-name-section">
                        <div class="team-name">${team.name}</div>
                        <p class="team-tag-premium">${team.tag || ''}</p>
                        <p class="team-game-premium"><i class="fas fa-gamepad"></i> ${team.game}</p>
                    </div>
                </div>
                <div class="team-stats-premium">
                    <div class="stat-item">
                        <i class="fas fa-users"></i>
                        <div>
                            <span class="stat-value">${team.member_count || 0}</span>
                            <span class="stat-label">Members</span>
                        </div>
                    </div>
                    <div class="stat-item">
                        <i class="fas fa-trophy"></i>
                        <div>
                            <span class="stat-value">${team.tournaments_won || 0}</span>
                            <span class="stat-label">Wins</span>
                        </div>
                    </div>
                    <div class="stat-item">
                        <i class="fas fa-star"></i>
                        <div>
                            <span class="stat-value">${team.achievements || 0}</span>
                            <span class="stat-label">Achievements</span>
                        </div>
                    </div>
                    <div class="stat-item">
                        <i class="fas fa-chart-line"></i>
                        <div>
                            <span class="stat-value">${team.power_rank || 0}</span>
                            <span class="stat-label">Power</span>
                        </div>
                    </div>
                </div>
                <div class="team-actions-premium">
                    <a href="/teams/${team.id}/" class="btn-action primary-action">
                        <i class="fas fa-eye"></i>
                        View Team
                    </a>
                    ${team.is_recruiting ? `<button class="btn-action secondary-action quick-join-btn" data-team-id="${team.id}"><i class="fas fa-user-plus"></i> Quick Join</button>` : ''}
                </div>
                <div class="power-rank-indicator">
                    <div class="power-rank-fill" style="width: ${Math.min(team.power_rank || 0, 100)}%"></div>
                </div>
            </div>
        `;
    }
    
    // Extract dominant colors from banner images
    function extractBannerColors() {
        const teamCards = document.querySelectorAll('.team-card-premium');
        
        teamCards.forEach(card => {
            const bannerImg = card.querySelector('.banner-img');
            if (!bannerImg) return;
            
            // Wait for image to load
            if (bannerImg.complete) {
                setCardColors(card, bannerImg);
            } else {
                bannerImg.addEventListener('load', () => {
                    setCardColors(card, bannerImg);
                });
            }
        });
    }
    
    function setCardColors(card, img) {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = img.width;
            canvas.height = img.height;
            
            ctx.drawImage(img, 0, 0);
            
            // Sample colors from top portion of banner
            const imageData = ctx.getImageData(0, 0, canvas.width, Math.min(canvas.height, 50));
            const colors = extractDominantColors(imageData.data);
            
            // Set CSS variables for dynamic gradient
            card.style.setProperty('--banner-color-1', `rgba(${colors[0].r}, ${colors[0].g}, ${colors[0].b}, 0.4)`);
            card.style.setProperty('--banner-color-2', `rgba(${colors[1].r}, ${colors[1].g}, ${colors[1].b}, 0.3)`);
        } catch (e) {
            // CORS error or other issue, use defaults
            console.log('Could not extract banner colors:', e);
        }
    }
    
    function extractDominantColors(data) {
        const colorMap = {};
        
        // Sample every 4 pixels for performance
        for (let i = 0; i < data.length; i += 16) {
            const r = data[i];
            const g = data[i + 1];
            const b = data[i + 2];
            
            // Skip very dark or very light pixels
            const brightness = (r + g + b) / 3;
            if (brightness < 30 || brightness > 220) continue;
            
            const key = `${Math.floor(r / 10)},${Math.floor(g / 10)},${Math.floor(b / 10)}`;
            colorMap[key] = (colorMap[key] || 0) + 1;
        }
        
        // Get top 2 colors
        const sortedColors = Object.entries(colorMap)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 2)
            .map(([key]) => {
                const [r, g, b] = key.split(',').map(n => parseInt(n) * 10);
                return { r, g, b };
            });
        
        // Fallback colors
        if (sortedColors.length === 0) {
            return [
                { r: 0, g: 240, b: 255 },
                { r: 168, g: 85, b: 247 }
            ];
        }
        
        if (sortedColors.length === 1) {
            sortedColors.push({ r: 168, g: 85, b: 247 });
        }
        
        return sortedColors;
    }

    function getPodiumBadge(index) {
        const icons = ['crown', 'medal', 'award'];
        const labels = ['1st', '2nd', '3rd'];
        return `
            <div class="podium-badge podium-${index + 1}">
                <i class="fas fa-${icons[index]}"></i>
                <span>${labels[index]}</span>
            </div>
        `;
    }

    function getBannerBadges(team) {
        const badges = [];
        if (team.is_verified) badges.push('<span class="banner-badge verified"><i class="fas fa-check-circle"></i> Verified</span>');
        if (team.is_featured) badges.push('<span class="banner-badge featured"><i class="fas fa-star"></i> Featured</span>');
        if (team.is_recruiting) badges.push('<span class="banner-badge recruiting"><i class="fas fa-user-plus"></i> Recruiting</span>');
        
        return badges.length > 0 ? `<div class="banner-badges">${badges.join('')}</div>` : '';
    }

    function updateResultsCount(total) {
        if (elements.resultsCount) {
            elements.resultsCount.textContent = `${total} ${total === 1 ? 'team' : 'teams'}`;
        }
    }

    function updateLoadMoreButton() {
        if (elements.loadMoreBtn) {
            if (state.hasMore) {
                elements.loadMoreBtn.style.display = 'block';
            } else {
                elements.loadMoreBtn.style.display = 'none';
            }
        }
    }

    // ========================================
    // QUICK JOIN MODAL
    // ========================================
    function showQuickJoinModal(teamSlug) {
        const modalHtml = `
            <div class="modal-overlay active" id="quickJoinModal">
                <div class="modal-content">
                    <button class="modal-close"><i class="fas fa-times"></i></button>
                    <div class="modal-header">
                        <i class="fas fa-user-plus"></i>
                        <h3>Quick Join Request</h3>
                    </div>
                    <div class="modal-body">
                        <p style="margin-bottom: 1.5rem; color: rgba(255,255,255,0.8);">
                            Send a request to join this team. The team captain will review your application.
                        </p>
                        <textarea id="joinMessage" placeholder="Tell them why you want to join (optional)" 
                            style="width: 100%; min-height: 100px; padding: 1rem; background: var(--dark-elevated); 
                            border: 2px solid var(--dark-border); border-radius: var(--radius-lg); color: white; 
                            font-family: inherit; resize: vertical; margin-bottom: 1.5rem;"></textarea>
                        <div style="display: flex; gap: 1rem;">
                            <button class="btn-action primary-action" onclick="submitJoinRequest('${teamSlug}')" style="flex: 1;">
                                <i class="fas fa-paper-plane"></i> Send Request
                            </button>
                            <button class="btn-action secondary-action modal-close-btn" style="flex: 1;">Cancel</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // Close handlers
        const modal = document.getElementById('quickJoinModal');
        modal.querySelector('.modal-close')?.addEventListener('click', () => modal.remove());
        modal.querySelector('.modal-close-btn')?.addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    // Make quickJoin available globally
    window.quickJoin = showQuickJoinModal;
    window.closeQuickJoin = function() {
        const modal = document.getElementById('quick-join-modal');
        if (modal) modal.style.display = 'none';
        const quickModal = document.getElementById('quickJoinModal');
        if (quickModal) quickModal.remove();
    };

    window.submitJoinRequest = function(teamSlug) {
        const messageInput = document.getElementById('joinMessage');
        const message = messageInput ? messageInput.value : '';
        const submitBtn = document.querySelector('#quickJoinModal .modal-submit-btn');
        
        // Show loading state
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
        }
        
        fetch(`/teams/${teamSlug}/join/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ message })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Close modal
            const quickModal = document.getElementById('quickJoinModal');
            if (quickModal) quickModal.remove();
            const modal = document.getElementById('quick-join-modal');
            if (modal) modal.style.display = 'none';
            
            // Show feedback
            if (data.success) {
                showToast(data.message || 'Successfully joined the team!', 'success');
                
                // Update button state on the team card
                const teamCard = document.querySelector(`[data-team-slug="${teamSlug}"]`);
                if (teamCard) {
                    const joinBtn = teamCard.querySelector('.secondary-action');
                    if (joinBtn) {
                        joinBtn.innerHTML = '<i class="fas fa-check-circle"></i><span>Member</span>';
                        joinBtn.classList.remove('secondary-action');
                        joinBtn.classList.add('member-badge');
                        joinBtn.disabled = true;
                    }
                }
            } else {
                // Check if game ID is needed
                if (data.needs_game_id) {
                    showToast('Please set up your game ID first', 'info');
                    // Redirect to team detail page where they can set up game ID
                    setTimeout(() => {
                        window.location.href = `/teams/${teamSlug}/`;
                    }, 1500);
                } else {
                    showToast(data.error || 'Failed to join team', 'error');
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Connection error. Please try again.', 'error');
            
            // Re-enable button
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Request';
            }
        });
    };

    // ========================================
    // SCROLL FUNCTIONS
    // ========================================
    function checkScrollButtons() {
        if (!elements.gameFiltersScroll || !elements.scrollLeftBtn || !elements.scrollRightBtn) return;

        const { scrollLeft, scrollWidth, clientWidth } = elements.gameFiltersScroll;

        elements.scrollLeftBtn.style.display = scrollLeft > 0 ? 'flex' : 'none';
        elements.scrollRightBtn.style.display = scrollLeft < scrollWidth - clientWidth - 10 ? 'flex' : 'none';
    }

    function handleScroll() {
        if (elements.scrollToTopBtn) {
            if (window.scrollY > 500) {
                elements.scrollToTopBtn.classList.add('visible');
            } else {
                elements.scrollToTopBtn.classList.remove('visible');
            }
        }
    }

    function scrollToTop() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // ========================================
    // LOADING OVERLAY
    // ========================================
    function showLoadingOverlay() {
        let overlay = document.querySelector('.loading-overlay-premium');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'loading-overlay-premium';
            overlay.innerHTML = `
                <div class="loading-content">
                    <div class="loading-spinner-premium"></div>
                    <p>Loading teams...</p>
                </div>
            `;
            document.body.appendChild(overlay);
        }
        overlay.classList.add('active');
    }

    function hideLoadingOverlay() {
        const overlay = document.querySelector('.loading-overlay-premium');
        if (overlay) {
            overlay.classList.remove('active');
        }
    }

    // ========================================
    // TOAST NOTIFICATIONS
    // ========================================
    function showToast(message, type = 'info') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            info: 'info-circle'
        };

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-${icons[type]}"></i>
            </div>
            <div class="toast-content">
                <div class="toast-title">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close">
                <i class="fas fa-times"></i>
            </button>
        `;

        container.appendChild(toast);

        // Close button
        toast.querySelector('.toast-close').addEventListener('click', () => {
            toast.remove();
        });

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.animation = 'toastSlideIn 0.3s ease-out reverse';
                setTimeout(() => toast.remove(), 300);
            }
        }, 5000);
    }

    // ========================================
    // UTILITIES
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
    // MODERN JOIN INTEGRATION
    // ========================================
    function initModernJoinButtons() {
        // Wait for ModernTeamJoin to be available
        if (typeof ModernTeamJoin === 'undefined') {
            console.warn('ModernTeamJoin not loaded yet, retrying...');
            setTimeout(initModernJoinButtons, 100);
            return;
        }

        const joinButtons = document.querySelectorAll('.join-team-btn');
        joinButtons.forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const teamSlug = this.dataset.teamSlug;
                const teamName = this.dataset.teamName;
                const teamGame = this.dataset.teamGame;

                if (!teamSlug) {
                    console.error('No team slug found');
                    return;
                }

                // Initialize and trigger modern join flow
                const modernJoin = new ModernTeamJoin();
                modernJoin.initJoin(teamSlug, teamName, teamGame, teamGame ? teamGame.charAt(0).toUpperCase() + teamGame.slice(1) : 'Game');
            });
        });

        console.log(`✅ Modern join initialized for ${joinButtons.length} buttons`);
    }

    // ========================================
    // INITIALIZE ON DOM READY
    // ========================================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            init();
            // Initialize modern join after main init
            setTimeout(initModernJoinButtons, 200);
        });
    } else {
        init();
        setTimeout(initModernJoinButtons, 200);
    }

})();
