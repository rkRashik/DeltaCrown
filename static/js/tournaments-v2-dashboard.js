/**
 * DeltaCrown Tournament Dashboard V2
 * Participant Dashboard JavaScript
 * 
 * Features:
 * - Tab navigation
 * - Bracket visualization
 * - Match updates (polling)
 * - News feed
 * - Calendar view
 * - Statistics display
 * - Real-time updates
 */

(function() {
    'use strict';

    // ============================================
    // STATE MANAGEMENT
    // ============================================

    const state = {
        currentTab: 'bracket',
        tournamentSlug: null,
        teamId: null,
        matches: [],
        news: [],
        bracket: null,
        updateInterval: null,
        currentMonth: new Date().getMonth(),
        currentYear: new Date().getFullYear()
    };

    // ============================================
    // INITIALIZATION
    // ============================================

    function init() {
        // Get tournament slug from page
        const dashboardElement = document.querySelector('.tournament-dashboard-v2');
        if (dashboardElement) {
            state.tournamentSlug = dashboardElement.dataset.tournamentSlug;
            state.teamId = dashboardElement.dataset.teamId;
        }

        // Initialize components
        initTabs();
        initBracket();
        initMatches();
        initNews();
        initCalendar();
        initStatistics();
        initKeyboardShortcuts();

        // Start auto-updates
        startAutoUpdates();

        console.log('Tournament Dashboard V2 initialized', state);
    }

    // ============================================
    // TAB NAVIGATION
    // ============================================

    function initTabs() {
        const tabs = document.querySelectorAll('.dashboard-tab');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = tab.dataset.tab;
                switchTab(tabName);
            });
        });

        // Check URL hash
        const hash = window.location.hash.substring(1);
        if (hash) {
            switchTab(hash);
        }
    }

    function switchTab(tabName) {
        // Update state
        state.currentTab = tabName;

        // Update URL
        history.replaceState(null, null, `#${tabName}`);

        // Update tab buttons
        document.querySelectorAll('.dashboard-tab').forEach(tab => {
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // Update tab content
        document.querySelectorAll('.dashboard-tab-content').forEach(content => {
            if (content.id === `tab-${tabName}`) {
                content.classList.add('active');
                
                // Load tab data if needed
                loadTabData(tabName);
            } else {
                content.classList.remove('active');
            }
        });
    }

    function loadTabData(tabName) {
        switch(tabName) {
            case 'bracket':
                loadBracket();
                break;
            case 'matches':
                loadMatches();
                break;
            case 'news':
                loadNews();
                break;
            case 'calendar':
                renderCalendar();
                break;
            case 'stats':
                loadStatistics();
                break;
        }
    }

    // ============================================
    // BRACKET VISUALIZATION
    // ============================================

    function initBracket() {
        // Bracket is loaded on first tab switch
    }

    function loadBracket() {
        if (state.bracket) {
            // Already loaded
            return;
        }

        const container = document.getElementById('bracket-content');
        if (!container) return;

        // Show loading state
        container.innerHTML = '<div class="loading">Loading bracket...</div>';

        // Fetch bracket data
        fetch(`/api/tournaments/${state.tournamentSlug}/bracket/`)
            .then(response => response.json())
            .then(data => {
                state.bracket = data;
                renderBracket(data);
            })
            .catch(error => {
                console.error('Error loading bracket:', error);
                renderEmptyBracket();
            });
    }

    function renderBracket(bracketData) {
        const container = document.getElementById('bracket-content');
        if (!container) return;

        if (!bracketData || !bracketData.rounds || bracketData.rounds.length === 0) {
            renderEmptyBracket();
            return;
        }

        let html = '<div class="bracket-rounds">';

        bracketData.rounds.forEach((round, roundIndex) => {
            html += `
                <div class="bracket-round">
                    <div class="bracket-round-title">${round.name}</div>
            `;

            round.matches.forEach(match => {
                html += renderBracketMatch(match);
            });

            html += '</div>';
        });

        html += '</div>';
        container.innerHTML = html;
    }

    function renderBracketMatch(match) {
        const team1 = match.team1 || { name: 'TBD', score: '-' };
        const team2 = match.team2 || { name: 'TBD', score: '-' };
        
        const team1Winner = match.winner_id === team1.id;
        const team2Winner = match.winner_id === team2.id;
        
        return `
            <div class="bracket-match">
                <div class="bracket-match-teams">
                    <div class="bracket-team ${team1Winner ? 'winner' : ''} ${team2Winner ? 'loser' : ''}">
                        <span class="bracket-team-name">${team1.name}</span>
                        <span class="bracket-team-score">${team1.score}</span>
                    </div>
                    <div class="bracket-team ${team2Winner ? 'winner' : ''} ${team1Winner ? 'loser' : ''}">
                        <span class="bracket-team-name">${team2.name}</span>
                        <span class="bracket-team-score">${team2.score}</span>
                    </div>
                </div>
                <div class="bracket-match-status ${match.status}">${getMatchStatusText(match.status)}</div>
            </div>
        `;
    }

    function renderEmptyBracket() {
        const container = document.getElementById('bracket-content');
        if (!container) return;

        container.innerHTML = `
            <div class="bracket-empty">
                <div class="bracket-empty-icon">🏆</div>
                <h3 class="bracket-empty-title">Bracket Not Ready</h3>
                <p class="bracket-empty-text">The tournament bracket will be available once the registration period ends and teams are seeded.</p>
            </div>
        `;
    }

    // ============================================
    // MATCHES
    // ============================================

    function initMatches() {
        // Matches are loaded on first tab switch
    }

    function loadMatches() {
        const container = document.getElementById('matches-list');
        if (!container) return;

        // Show loading state
        container.innerHTML = '<div class="loading">Loading matches...</div>';

        // Fetch matches
        fetch(`/api/tournaments/${state.tournamentSlug}/matches/?team_id=${state.teamId}`)
            .then(response => response.json())
            .then(data => {
                state.matches = data.results || data;
                renderMatches(state.matches);
            })
            .catch(error => {
                console.error('Error loading matches:', error);
                container.innerHTML = '<div class="error">Failed to load matches.</div>';
            });
    }

    function renderMatches(matches) {
        const container = document.getElementById('matches-list');
        if (!container) return;

        if (!matches || matches.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No matches scheduled yet.</p>
                </div>
            `;
            return;
        }

        let html = '';
        matches.forEach(match => {
            html += renderMatchCard(match);
        });

        container.innerHTML = html;
    }

    function renderMatchCard(match) {
        const isLive = match.status === 'live';
        const isCompleted = match.status === 'completed';
        const isUpcoming = match.status === 'upcoming';

        return `
            <div class="match-card ${match.status}">
                <div class="match-header">
                    <span class="match-round">${match.round || 'Round 1'}</span>
                    <span class="match-status ${match.status}">${getMatchStatusText(match.status)}</span>
                </div>
                <div class="match-teams">
                    <div class="match-team ${match.winner_id === match.team1.id ? 'winner' : ''}">
                        <img src="${match.team1.logo || '/static/images/default-team.png'}" alt="${match.team1.name}" class="match-team-logo">
                        <div class="match-team-info">
                            <div class="match-team-name">${match.team1.name}</div>
                            ${match.team1.record ? `<div class="match-team-record">${match.team1.record}</div>` : ''}
                        </div>
                        ${isCompleted ? `<div class="match-score">${match.team1.score || 0}</div>` : ''}
                    </div>
                    <div class="match-vs">VS</div>
                    <div class="match-team ${match.winner_id === match.team2.id ? 'winner' : ''}">
                        ${isCompleted ? `<div class="match-score">${match.team2.score || 0}</div>` : ''}
                        <div class="match-team-info">
                            <div class="match-team-name">${match.team2.name}</div>
                            ${match.team2.record ? `<div class="match-team-record">${match.team2.record}</div>` : ''}
                        </div>
                        <img src="${match.team2.logo || '/static/images/default-team.png'}" alt="${match.team2.name}" class="match-team-logo">
                    </div>
                </div>
                <div class="match-footer">
                    <span class="match-date">${formatMatchDate(match.scheduled_at)}</span>
                    <div class="match-actions">
                        ${isLive ? '<button class="match-action-btn">Watch Live</button>' : ''}
                        <button class="match-action-btn">Details</button>
                    </div>
                </div>
            </div>
        `;
    }

    function getMatchStatusText(status) {
        const statusMap = {
            'live': '● LIVE',
            'upcoming': 'Upcoming',
            'completed': 'Completed',
            'scheduled': 'Scheduled'
        };
        return statusMap[status] || status;
    }

    function formatMatchDate(dateString) {
        if (!dateString) return 'TBD';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = date - now;
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffHours / 24);

        if (diffDays > 7) {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        } else if (diffDays > 0) {
            return `In ${diffDays} day${diffDays > 1 ? 's' : ''}`;
        } else if (diffHours > 0) {
            return `In ${diffHours} hour${diffHours > 1 ? 's' : ''}`;
        } else if (diffMs > 0) {
            const diffMins = Math.floor(diffMs / (1000 * 60));
            return `In ${diffMins} minute${diffMins > 1 ? 's' : ''}`;
        } else {
            return date.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
        }
    }

    // ============================================
    // NEWS FEED
    // ============================================

    function initNews() {
        // News is loaded on first tab switch
    }

    function loadNews() {
        const container = document.getElementById('news-feed');
        if (!container) return;

        // Show loading state
        container.innerHTML = '<div class="loading">Loading news...</div>';

        // Fetch news
        fetch(`/api/tournaments/${state.tournamentSlug}/news/`)
            .then(response => response.json())
            .then(data => {
                state.news = data.results || data;
                renderNews(state.news);
            })
            .catch(error => {
                console.error('Error loading news:', error);
                container.innerHTML = '<div class="error">Failed to load news.</div>';
            });
    }

    function renderNews(newsItems) {
        const container = document.getElementById('news-feed');
        if (!container) return;

        if (!newsItems || newsItems.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No news or announcements yet.</p>
                </div>
            `;
            return;
        }

        let html = '';
        newsItems.forEach(item => {
            html += renderNewsItem(item);
        });

        container.innerHTML = html;
    }

    function renderNewsItem(item) {
        return `
            <div class="news-item">
                <div class="news-header">
                    <span class="news-badge">${item.category || 'Announcement'}</span>
                    <span class="news-date">${formatNewsDate(item.created_at)}</span>
                </div>
                <h3 class="news-title">${item.title}</h3>
                <p class="news-content">${item.content}</p>
                ${item.tags && item.tags.length > 0 ? `
                    <div class="news-footer">
                        ${item.tags.map(tag => `<span class="news-tag">${tag}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }

    function formatNewsDate(dateString) {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 60) {
            return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        } else if (diffDays < 7) {
            return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
        } else {
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }
    }

    // ============================================
    // CALENDAR
    // ============================================

    function initCalendar() {
        // Set up navigation
        const prevBtn = document.getElementById('calendar-prev');
        const nextBtn = document.getElementById('calendar-next');
        const todayBtn = document.getElementById('calendar-today');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                state.currentMonth--;
                if (state.currentMonth < 0) {
                    state.currentMonth = 11;
                    state.currentYear--;
                }
                renderCalendar();
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                state.currentMonth++;
                if (state.currentMonth > 11) {
                    state.currentMonth = 0;
                    state.currentYear++;
                }
                renderCalendar();
            });
        }

        if (todayBtn) {
            todayBtn.addEventListener('click', () => {
                const now = new Date();
                state.currentMonth = now.getMonth();
                state.currentYear = now.getFullYear();
                renderCalendar();
            });
        }
    }

    function renderCalendar() {
        const titleElement = document.getElementById('calendar-title');
        const gridElement = document.getElementById('calendar-grid');
        
        if (!titleElement || !gridElement) return;

        // Update title
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        titleElement.textContent = `${monthNames[state.currentMonth]} ${state.currentYear}`;

        // Get calendar data
        const firstDay = new Date(state.currentYear, state.currentMonth, 1);
        const lastDay = new Date(state.currentYear, state.currentMonth + 1, 0);
        const prevLastDay = new Date(state.currentYear, state.currentMonth, 0);
        
        const firstDayOfWeek = firstDay.getDay();
        const lastDate = lastDay.getDate();
        const prevLastDate = prevLastDay.getDate();

        let html = '';

        // Day headers
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        dayNames.forEach(day => {
            html += `<div class="calendar-day-header">${day}</div>`;
        });

        // Previous month days
        for (let i = firstDayOfWeek; i > 0; i--) {
            html += `<div class="calendar-day other-month">${prevLastDate - i + 1}</div>`;
        }

        // Current month days
        const today = new Date();
        const isCurrentMonth = today.getMonth() === state.currentMonth && today.getFullYear() === state.currentYear;
        
        for (let day = 1; day <= lastDate; day++) {
            const isToday = isCurrentMonth && day === today.getDate();
            const hasMatch = checkMatchOnDate(state.currentYear, state.currentMonth, day);
            
            html += `
                <div class="calendar-day ${isToday ? 'today' : ''} ${hasMatch ? 'has-match' : ''}"
                     data-date="${state.currentYear}-${state.currentMonth + 1}-${day}">
                    ${day}
                </div>
            `;
        }

        // Next month days
        const remainingDays = 42 - (firstDayOfWeek + lastDate);
        for (let day = 1; day <= remainingDays; day++) {
            html += `<div class="calendar-day other-month">${day}</div>`;
        }

        gridElement.innerHTML = html;
    }

    function checkMatchOnDate(year, month, day) {
        // Check if any match is scheduled on this date
        if (!state.matches || state.matches.length === 0) return false;
        
        return state.matches.some(match => {
            if (!match.scheduled_at) return false;
            const matchDate = new Date(match.scheduled_at);
            return matchDate.getFullYear() === year &&
                   matchDate.getMonth() === month &&
                   matchDate.getDate() === day;
        });
    }

    // ============================================
    // STATISTICS
    // ============================================

    function initStatistics() {
        // Statistics are loaded on first tab switch
    }

    function loadStatistics() {
        const container = document.getElementById('stats-container');
        if (!container) return;

        // Fetch statistics
        fetch(`/api/tournaments/${state.tournamentSlug}/statistics/?team_id=${state.teamId}`)
            .then(response => response.json())
            .then(data => {
                renderStatistics(data);
            })
            .catch(error => {
                console.error('Error loading statistics:', error);
            });
    }

    function renderStatistics(stats) {
        // Statistics rendering is handled by backend template
        // This function can be extended for dynamic updates
        console.log('Statistics loaded:', stats);
    }

    // ============================================
    // AUTO-UPDATES
    // ============================================

    function startAutoUpdates() {
        // Poll for updates every 30 seconds
        state.updateInterval = setInterval(() => {
            // Only update if on matches or bracket tab
            if (state.currentTab === 'matches') {
                loadMatches();
            } else if (state.currentTab === 'bracket') {
                loadBracket();
            }
        }, 30000); // 30 seconds
    }

    function stopAutoUpdates() {
        if (state.updateInterval) {
            clearInterval(state.updateInterval);
            state.updateInterval = null;
        }
    }

    // ============================================
    // KEYBOARD SHORTCUTS
    // ============================================

    function initKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger if typing in input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            // 1-5: Switch tabs
            if (e.key >= '1' && e.key <= '5') {
                const tabNames = ['bracket', 'matches', 'news', 'calendar', 'stats'];
                const index = parseInt(e.key) - 1;
                if (tabNames[index]) {
                    switchTab(tabNames[index]);
                }
            }

            // R: Refresh current tab
            if (e.key === 'r' || e.key === 'R') {
                e.preventDefault();
                loadTabData(state.currentTab);
            }
        });
    }

    // ============================================
    // CLEANUP
    // ============================================

    window.addEventListener('beforeunload', () => {
        stopAutoUpdates();
    });

    // ============================================
    // PUBLIC API
    // ============================================

    window.TournamentDashboardV2 = {
        init,
        switchTab,
        loadMatches,
        loadBracket,
        loadNews,
        renderCalendar,
        getState: () => ({ ...state })
    };

    // Auto-initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
