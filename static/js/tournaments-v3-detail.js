/**
 * Tournament Detail Page V3 - Modern Professional Edition
 * Complete API integration with real-time updates
 * Optimized performance with caching and lazy loading
 */

class TournamentDetailV3 {
    constructor(config) {
        this.config = {
            tournamentSlug: config.tournamentSlug,
            currentTab: config.currentTab || 'overview',
            isRegistered: config.isRegistered || false,
            apiBaseUrl: '/api/t/',
            updateInterval: 60000, // 1 minute
            ...config
        };
        
        this.state = {
            currentTab: this.config.currentTab,
            teams: [],
            matches: [],
            leaderboard: [],
            loading: {},
            error: {},
            lastUpdate: {},
        };
        
        this.cache = new Map();
        this.updateTimers = new Map();
        
        this.init();
    }
    
    init() {
        console.log('[TournamentDetail] Initializing V3...');
        
        // Setup event listeners
        this.setupTabNavigation();
        this.setupRegistrationButton();
        this.setupShareButtons();
        this.setupStickyInfoBar();
        
        // Load initial data
        this.loadCurrentTab();
        
        // Start real-time updates
        this.startRealTimeUpdates();
        
        // Performance monitoring
        this.setupPerformanceMonitoring();
        
        console.log('[TournamentDetail] Initialization complete');
    }
    
    // ==========================================
    // TAB NAVIGATION
    // ==========================================
    
    setupTabNavigation() {
        const tabs = document.querySelectorAll('.detail-tab');
        const contents = document.querySelectorAll('.detail-tab-content');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = tab.dataset.tab;
                this.switchTab(tabName);
            });
        });
        
        // Keyboard shortcuts (1-6 for tabs)
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) return; // Ignore with modifier keys
            
            const key = parseInt(e.key);
            if (key >= 1 && key <= 6) {
                const tabs = ['overview', 'teams', 'matches', 'prizes', 'rules', 'standings'];
                if (tabs[key - 1]) {
                    this.switchTab(tabs[key - 1]);
                }
            }
        });
    }
    
    switchTab(tabName) {
        console.log(`[TournamentDetail] Switching to tab: ${tabName}`);
        
        // Update active states
        document.querySelectorAll('.detail-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });
        
        document.querySelectorAll('.detail-tab-content').forEach(content => {
            content.classList.toggle('active', content.dataset.tab === tabName);
        });
        
        // Update state
        this.state.currentTab = tabName;
        
        // Update URL without reload
        const url = new URL(window.location);
        url.searchParams.set('tab', tabName);
        window.history.pushState({}, '', url);
        
        // Load tab data
        this.loadCurrentTab();
        
        // Track analytics
        this.trackEvent('tab_switch', { tab: tabName });
    }
    
    loadCurrentTab() {
        const tab = this.state.currentTab;
        
        switch(tab) {
            case 'teams':
                this.loadTeams();
                break;
            case 'matches':
                this.loadMatches();
                break;
            case 'standings':
                this.loadLeaderboard();
                break;
            // Overview, prizes, rules are static - no need to load
        }
    }
    
    // ==========================================
    // API DATA LOADING
    // ==========================================
    
    async loadTeams(page = 1) {
        const cacheKey = `teams_${page}`;
        
        // Check cache (5 minute TTL)
        if (this.isCacheValid(cacheKey, 300000)) {
            return this.renderTeams(this.cache.get(cacheKey));
        }
        
        // Show loading state
        this.setLoading('teams', true);
        
        try {
            const response = await fetch(
                `${this.config.apiBaseUrl}${this.config.tournamentSlug}/teams/?page=${page}&limit=20`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            // Cache the response
            this.cache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
            
            // Update state
            this.state.teams = data.teams;
            this.state.lastUpdate.teams = new Date();
            
            // Render
            this.renderTeams(data);
            
        } catch (error) {
            console.error('[TournamentDetail] Error loading teams:', error);
            this.setError('teams', error.message);
            this.renderTeamsError(error);
        } finally {
            this.setLoading('teams', false);
        }
    }
    
    async loadMatches(filters = {}) {
        const queryString = new URLSearchParams(filters).toString();
        const cacheKey = `matches_${queryString}`;
        
        // Check cache (1 minute TTL for matches - they update frequently)
        if (this.isCacheValid(cacheKey, 60000)) {
            return this.renderMatches(this.cache.get(cacheKey));
        }
        
        this.setLoading('matches', true);
        
        try {
            const response = await fetch(
                `/api/${this.config.tournamentSlug}/matches/?${queryString}`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            // Cache
            this.cache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
            
            // Update state
            this.state.matches = data.matches;
            this.state.lastUpdate.matches = new Date();
            
            // Render
            this.renderMatches(data);
            
        } catch (error) {
            console.error('[TournamentDetail] Error loading matches:', error);
            this.setError('matches', error.message);
            this.renderMatchesError(error);
        } finally {
            this.setLoading('matches', false);
        }
    }
    
    async loadLeaderboard() {
        const cacheKey = 'leaderboard';
        
        // Check cache (2 minute TTL)
        if (this.isCacheValid(cacheKey, 120000)) {
            return this.renderLeaderboard(this.cache.get(cacheKey));
        }
        
        this.setLoading('leaderboard', true);
        
        try {
            const response = await fetch(
                `${this.config.apiBaseUrl}${this.config.tournamentSlug}/leaderboard/`
            );
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            // Cache
            this.cache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
            
            // Update state
            this.state.leaderboard = data.standings;
            this.state.lastUpdate.leaderboard = new Date();
            
            // Render
            this.renderLeaderboard(data);
            
        } catch (error) {
            console.error('[TournamentDetail] Error loading leaderboard:', error);
            this.setError('leaderboard', error.message);
            this.renderLeaderboardError(error);
        } finally {
            this.setLoading('leaderboard', false);
        }
    }
    
    async checkRegistrationStatus() {
        if (!this.config.isAuthenticated) {
            return null;
        }
        
        try {
            const response = await fetch(
                `${this.config.apiBaseUrl}${this.config.tournamentSlug}/registration-status/`
            );
            
            if (!response.ok) {
                return null;
            }
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('[TournamentDetail] Error checking registration:', error);
            return null;
        }
    }
    
    // ==========================================
    // RENDERING METHODS
    // ==========================================
    
    renderTeams(data) {
        const container = document.getElementById('teams-container');
        if (!container) return;
        
        if (!data.teams || data.teams.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">👥</div>
                    <h3 class="empty-state-title">No Teams Yet</h3>
                    <p class="empty-state-text">Be the first to register for this tournament!</p>
                </div>
            `;
            return;
        }
        
        const html = `
            <div class="teams-header">
                <h3 class="teams-title">Registered Teams (${data.pagination.total_count})</h3>
                <div class="teams-search">
                    <input type="text" 
                           class="teams-search-input" 
                           placeholder="Search teams..." 
                           id="teams-search">
                    <i class="fa-solid fa-search"></i>
                </div>
            </div>
            
            <div class="teams-grid">
                ${data.teams.map(team => this.renderTeamCard(team)).join('')}
            </div>
            
            ${data.pagination.has_next ? `
                <button class="btn btn-secondary load-more-teams" data-page="${data.pagination.page + 1}">
                    Load More Teams
                </button>
            ` : ''}
        `;
        
        container.innerHTML = html;
        
        // Setup search
        const searchInput = document.getElementById('teams-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.loadTeams(1, { search: e.target.value });
            }, 300));
        }
        
        // Setup load more
        const loadMoreBtn = container.querySelector('.load-more-teams');
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                const page = parseInt(loadMoreBtn.dataset.page);
                this.loadTeams(page);
            });
        }
    }
    
    renderTeamCard(team) {
        const teamInfo = team.team || {
            name: team.captain?.username || 'Solo Player',
            logo: team.captain?.avatar,
            members: []
        };
        
        return `
            <div class="team-card" data-team-id="${team.registration_id}">
                <div class="team-card-header">
                    <img src="${teamInfo.logo || '/static/images/default-team.png'}" 
                         alt="${teamInfo.name}" 
                         class="team-logo"
                         loading="lazy">
                    <div class="team-info">
                        <h4 class="team-name">${this.escapeHtml(teamInfo.name)}</h4>
                        ${teamInfo.tag ? `<span class="team-tag">${this.escapeHtml(teamInfo.tag)}</span>` : ''}
                    </div>
                    <span class="team-status team-status-${team.status.toLowerCase()}">
                        ${team.status}
                    </span>
                </div>
                
                ${teamInfo.members && teamInfo.members.length > 0 ? `
                    <div class="team-members">
                        <div class="team-members-label">Players:</div>
                        <div class="team-members-list">
                            ${teamInfo.members.slice(0, 5).map(member => `
                                <div class="team-member">
                                    <img src="${member.avatar || '/static/images/default-avatar.png'}" 
                                         alt="${member.username}"
                                         class="member-avatar"
                                         loading="lazy">
                                    <span class="member-name">${this.escapeHtml(member.username)}</span>
                                </div>
                            `).join('')}
                            ${teamInfo.members.length > 5 ? `
                                <div class="team-member-more">
                                    +${teamInfo.members.length - 5} more
                                </div>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}
                
                <div class="team-card-footer">
                    <span class="team-registered-date">
                        <i class="fa-solid fa-calendar"></i>
                        ${this.formatDate(team.registered_at)}
                    </span>
                    ${team.checked_in ? `
                        <span class="team-checked-in">
                            <i class="fa-solid fa-check-circle"></i>
                            Checked In
                        </span>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    renderMatches(data) {
        const container = document.querySelector('[data-tab="matches"]');
        if (!container) return;
        
        if (!data.matches || data.matches.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🎮</div>
                    <h3 class="empty-state-title">No Matches Scheduled</h3>
                    <p class="empty-state-text">Matches will appear here once the tournament begins.</p>
                </div>
            `;
            return;
        }
        
        // Group matches by round
        const matchesByRound = {};
        data.matches.forEach(match => {
            const round = match.round_name || `Round ${match.round_number}`;
            if (!matchesByRound[round]) {
                matchesByRound[round] = [];
            }
            matchesByRound[round].push(match);
        });
        
        const html = `
            <div class="matches-container">
                <div class="matches-header">
                    <h3 class="matches-title">Match Schedule</h3>
                    <div class="matches-filters">
                        <select class="match-filter-select" id="match-status-filter">
                            <option value="">All Matches</option>
                            <option value="SCHEDULED">Scheduled</option>
                            <option value="LIVE">Live</option>
                            <option value="COMPLETED">Completed</option>
                        </select>
                    </div>
                </div>
                
                ${Object.entries(matchesByRound).map(([round, matches]) => `
                    <div class="match-round">
                        <h4 class="match-round-title">${round}</h4>
                        <div class="matches-grid">
                            ${matches.map(match => this.renderMatchCard(match)).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        
        container.innerHTML = html;
        
        // Setup filters
        const statusFilter = document.getElementById('match-status-filter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.loadMatches({ status: e.target.value });
            });
        }
    }
    
    renderMatchCard(match) {
        const isLive = match.status === 'LIVE';
        const isCompleted = match.status === 'COMPLETED';
        
        return `
            <div class="match-card match-status-${match.status.toLowerCase()}" data-match-id="${match.id}">
                ${isLive ? '<div class="match-live-indicator">🔴 LIVE</div>' : ''}
                
                <div class="match-header">
                    <span class="match-number">Match #${match.match_number}</span>
                    <span class="match-format">Bo${match.best_of}</span>
                </div>
                
                <div class="match-teams">
                    <div class="match-team ${match.winner === match.team1?.id ? 'match-winner' : ''}">
                        <img src="${match.team1?.logo || '/static/images/default-team.png'}" 
                             alt="${match.team1?.name || 'TBD'}"
                             class="match-team-logo"
                             loading="lazy">
                        <span class="match-team-name">${this.escapeHtml(match.team1?.name || 'TBD')}</span>
                        ${isCompleted ? `<span class="match-team-score">${match.scores.team1}</span>` : ''}
                    </div>
                    
                    <div class="match-vs">VS</div>
                    
                    <div class="match-team ${match.winner === match.team2?.id ? 'match-winner' : ''}">
                        ${isCompleted ? `<span class="match-team-score">${match.scores.team2}</span>` : ''}
                        <span class="match-team-name">${this.escapeHtml(match.team2?.name || 'TBD')}</span>
                        <img src="${match.team2?.logo || '/static/images/default-team.png'}" 
                             alt="${match.team2?.name || 'TBD'}"
                             class="match-team-logo"
                             loading="lazy">
                    </div>
                </div>
                
                <div class="match-footer">
                    ${match.scheduled_time ? `
                        <span class="match-time">
                            <i class="fa-solid fa-clock"></i>
                            ${this.formatDateTime(match.scheduled_time)}
                        </span>
                    ` : ''}
                    
                    ${match.stream_url ? `
                        <a href="${match.stream_url}" target="_blank" class="match-stream-link">
                            <i class="fa-solid fa-tv"></i>
                            Watch Stream
                        </a>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    renderLeaderboard(data) {
        const container = document.querySelector('[data-tab="standings"]');
        if (!container) return;
        
        if (!data.standings || data.standings.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🏆</div>
                    <h3 class="empty-state-title">No Standings Yet</h3>
                    <p class="empty-state-text">Standings will appear once matches have been played.</p>
                </div>
            `;
            return;
        }
        
        const html = `
            <div class="leaderboard-container">
                <div class="leaderboard-header">
                    <h3 class="leaderboard-title">Tournament Standings</h3>
                    <span class="leaderboard-updated">
                        Last updated: ${this.formatDateTime(data.last_updated)}
                    </span>
                </div>
                
                <div class="leaderboard-table-wrapper">
                    <table class="leaderboard-table">
                        <thead>
                            <tr>
                                <th class="rank-col">Rank</th>
                                <th class="team-col">Team</th>
                                <th class="points-col">Points</th>
                                <th class="wins-col">W</th>
                                <th class="losses-col">L</th>
                                <th class="winrate-col">Win %</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.standings.map(standing => this.renderLeaderboardRow(standing)).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    renderLeaderboardRow(standing) {
        const rankClass = standing.rank <= 3 ? `rank-${standing.rank}` : '';
        const rankMedal = standing.rank === 1 ? '🥇' : standing.rank === 2 ? '🥈' : standing.rank === 3 ? '🥉' : '';
        
        return `
            <tr class="leaderboard-row ${rankClass}">
                <td class="rank-col">
                    <span class="rank-number">${rankMedal || standing.rank}</span>
                </td>
                <td class="team-col">
                    <div class="team-cell">
                        <img src="${standing.team_logo || '/static/images/default-team.png'}" 
                             alt="${standing.team_name}"
                             class="team-logo-small"
                             loading="lazy">
                        <span class="team-name">${this.escapeHtml(standing.team_name)}</span>
                    </div>
                </td>
                <td class="points-col">
                    <strong>${standing.points}</strong>
                </td>
                <td class="wins-col">${standing.wins}</td>
                <td class="losses-col">${standing.losses}</td>
                <td class="winrate-col">${standing.win_rate}%</td>
            </tr>
        `;
    }
    
    renderTeamsError(error) {
        const container = document.getElementById('teams-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="error-state">
                <div class="error-state-icon">❌</div>
                <h3 class="error-state-title">Failed to Load Teams</h3>
                <p class="error-state-text">${this.escapeHtml(error.message)}</p>
                <button class="btn btn-primary" onclick="window.TournamentDetail.loadTeams()">
                    Try Again
                </button>
            </div>
        `;
    }
    
    renderMatchesError(error) {
        // Similar to renderTeamsError
    }
    
    renderLeaderboardError(error) {
        // Similar to renderTeamsError
    }
    
    // ==========================================
    // REGISTRATION HANDLING
    // ==========================================
    
    setupRegistrationButton() {
        const btn = document.getElementById('registration-btn');
        if (!btn) return;
        
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            
            // Check if user is authenticated
            if (!this.config.isAuthenticated) {
                window.location.href = `/accounts/login/?next=${window.location.pathname}`;
                return;
            }
            
            // Check registration status
            const status = await this.checkRegistrationStatus();
            
            if (status && status.registered) {
                // User is already registered
                this.showRegistrationStatus(status);
            } else {
                // Redirect to registration page
                window.location.href = `/tournaments/register-modern/${this.config.tournamentSlug}/`;
            }
        });
    }
    
    showRegistrationStatus(status) {
        // Show modal or toast with registration info
        this.showModal({
            title: 'Registration Status',
            content: `
                <div class="registration-status-modal">
                    <div class="status-icon status-${status.registration.status.toLowerCase()}">
                        ${status.registration.status === 'CONFIRMED' ? '✅' : '⏳'}
                    </div>
                    <h4>Status: ${status.registration.status}</h4>
                    <p>You registered on ${this.formatDateTime(status.registration.registered_at)}</p>
                    ${status.registration.team ? `
                        <div class="team-info">
                            <img src="${status.registration.team.logo || '/static/images/default-team.png'}" 
                                 alt="${status.registration.team.name}">
                            <span>${status.registration.team.name}</span>
                        </div>
                    ` : ''}
                </div>
            `
        });
    }
    
    // ==========================================
    // SHARE FUNCTIONALITY
    // ==========================================
    
    setupShareButtons() {
        // Already implemented in template
    }
    
    // ==========================================
    // STICKY INFO BAR
    // ==========================================
    
    setupStickyInfoBar() {
        const infoBar = document.querySelector('.detail-info-bar');
        const hero = document.querySelector('.detail-hero');
        
        if (!infoBar || !hero) return;
        
        const observer = new IntersectionObserver(
            ([entry]) => {
                infoBar.classList.toggle('is-sticky', !entry.isIntersecting);
            },
            { threshold: 0 }
        );
        
        observer.observe(hero);
    }
    
    // ==========================================
    // REAL-TIME UPDATES
    // ==========================================
    
    startRealTimeUpdates() {
        // Update teams every 2 minutes
        this.updateTimers.set('teams', setInterval(() => {
            if (this.state.currentTab === 'teams') {
                this.loadTeams(1);
            }
        }, 120000));
        
        // Update matches every 1 minute
        this.updateTimers.set('matches', setInterval(() => {
            if (this.state.currentTab === 'matches') {
                this.loadMatches();
            }
        }, 60000));
        
        // Update leaderboard every 2 minutes
        this.updateTimers.set('leaderboard', setInterval(() => {
            if (this.state.currentTab === 'standings') {
                this.loadLeaderboard();
            }
        }, 120000));
    }
    
    stopRealTimeUpdates() {
        this.updateTimers.forEach((timer) => {
            clearInterval(timer);
        });
        this.updateTimers.clear();
    }
    
    // ==========================================
    // UTILITY METHODS
    // ==========================================
    
    isCacheValid(key, ttl) {
        if (!this.cache.has(key)) {
            return false;
        }
        
        const cached = this.cache.get(key);
        return (Date.now() - cached.timestamp) < ttl;
    }
    
    setLoading(key, loading) {
        this.state.loading[key] = loading;
    }
    
    setError(key, error) {
        this.state.error[key] = error;
    }
    
    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
    
    formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        const date = new Date(dateString);
        return date.toLocaleString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
    
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
    
    showModal(config) {
        // Simple modal implementation
        const modal = document.createElement('div');
        modal.className = 'detail-modal';
        modal.innerHTML = `
            <div class="detail-modal-overlay" onclick="this.parentElement.remove()"></div>
            <div class="detail-modal-content">
                <button class="detail-modal-close" onclick="this.closest('.detail-modal').remove()">
                    &times;
                </button>
                <h3 class="detail-modal-title">${config.title}</h3>
                <div class="detail-modal-body">${config.content}</div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    trackEvent(event, data) {
        // Analytics tracking (integrate with your analytics service)
        if (window.gtag) {
            window.gtag('event', event, data);
        }
        console.log('[Analytics]', event, data);
    }
    
    setupPerformanceMonitoring() {
        // Performance monitoring
        if (window.performance && window.performance.mark) {
            window.performance.mark('tournament-detail-init-complete');
            
            // Measure FCP, LCP, etc.
            if ('PerformanceObserver' in window) {
                const perfObserver = new PerformanceObserver((entryList) => {
                    for (const entry of entryList.getEntries()) {
                        console.log('[Performance]', entry.name, entry.duration);
                    }
                });
                
                perfObserver.observe({ entryTypes: ['measure', 'paint'] });
            }
        }
    }
    
    destroy() {
        // Cleanup
        this.stopRealTimeUpdates();
        this.cache.clear();
        console.log('[TournamentDetail] Destroyed');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const tournamentSlug = document.body.dataset.tournamentSlug;
    const isAuthenticated = document.body.dataset.authenticated === 'true';
    const isRegistered = document.body.dataset.registered === 'true';
    
    if (tournamentSlug) {
        window.TournamentDetail = new TournamentDetailV3({
            tournamentSlug,
            isAuthenticated,
            isRegistered,
            currentTab: new URLSearchParams(window.location.search).get('tab') || 'overview'
        });
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TournamentDetailV3;
}
