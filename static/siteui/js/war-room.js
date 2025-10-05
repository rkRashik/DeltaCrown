/**
 * WAR ROOM - Tournament Command Center
 * Interactive features for registered participants
 */

class WarRoom {
    constructor() {
        this.tournamentSlug = document.querySelector('[data-tournament-slug]')?.dataset.tournamentSlug;
        this.teamId = document.querySelector('[data-team-id]')?.dataset.teamId;
        this.init();
    }

    init() {
        this.setupCheckIn();
        this.setupQuickActions();
        this.setupAutoRefresh();
        this.loadMatches();
        this.loadNews();
        this.setupActivityFeed();
    }

    /**
     * Check-In Functionality
     */
    setupCheckIn() {
        const checkinBtn = document.querySelector('.checkin-btn');
        if (!checkinBtn) return;

        checkinBtn.addEventListener('click', async () => {
            try {
                checkinBtn.disabled = true;
                checkinBtn.innerHTML = `
                    <div class="spinner" style="width: 16px; height: 16px; border-width: 2px;"></div>
                    <span>Checking In...</span>
                `;

                const response = await fetch(`/api/tournaments/${this.tournamentSlug}/checkin/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCsrfToken()
                    }
                });

                if (response.ok) {
                    this.showToast('Check-in successful!', 'success');
                    
                    // Update UI
                    checkinBtn.classList.remove('warning');
                    checkinBtn.classList.add('success');
                    checkinBtn.innerHTML = `
                        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        <span>Checked In</span>
                    `;
                    checkinBtn.disabled = true;
                } else {
                    throw new Error('Check-in failed');
                }
            } catch (error) {
                console.error('Check-in error:', error);
                this.showToast('Failed to check in. Please try again.', 'error');
                
                checkinBtn.disabled = false;
                checkinBtn.innerHTML = `
                    <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <span>Check In Now</span>
                `;
            }
        });
    }

    /**
     * Quick Action Buttons
     */
    setupQuickActions() {
        const actions = {
            'view-matches': () => this.scrollToSection('matches-section'),
            'view-bracket': () => this.openBracket(),
            'view-standings': () => this.openStandings(),
            'view-rules': () => this.openRules()
        };

        Object.entries(actions).forEach(([id, handler]) => {
            const btn = document.getElementById(id);
            if (btn) {
                btn.addEventListener('click', handler);
            }
        });
    }

    /**
     * Load Matches
     */
    async loadMatches() {
        const matchesSection = document.querySelector('#matches-section .section-content');
        if (!matchesSection) return;

        try {
            const response = await fetch(`/api/tournaments/${this.tournamentSlug}/matches/?team=${this.teamId}`);
            const data = await response.json();

            if (data.matches && data.matches.length > 0) {
                const matchList = document.createElement('div');
                matchList.className = 'match-list';

                data.matches.slice(0, 5).forEach(match => {
                    matchList.appendChild(this.createMatchCard(match));
                });

                matchesSection.innerHTML = '';
                matchesSection.appendChild(matchList);
            }
        } catch (error) {
            console.error('Failed to load matches:', error);
            // Keep the empty state or loading placeholder
        }
    }

    /**
     * Create Match Card
     */
    createMatchCard(match) {
        const card = document.createElement('div');
        card.className = 'match-card';
        card.innerHTML = `
            <div class="match-header">
                <span class="match-round">${match.round || 'Round 1'}</span>
                <span class="match-time">${this.formatMatchTime(match.scheduled_at)}</span>
            </div>
            <div class="match-teams">
                <div class="match-team">
                    <img src="${match.team_a_logo || '/static/images/default-team.png'}" alt="${match.team_a_name}">
                    <span>${match.team_a_name}</span>
                    ${match.team_a_score !== null ? `<strong>${match.team_a_score}</strong>` : ''}
                </div>
                <div class="match-vs">VS</div>
                <div class="match-team">
                    <img src="${match.team_b_logo || '/static/images/default-team.png'}" alt="${match.team_b_name}">
                    <span>${match.team_b_name}</span>
                    ${match.team_b_score !== null ? `<strong>${match.team_b_score}</strong>` : ''}
                </div>
            </div>
            ${match.status === 'live' ? '<div class="match-status live">LIVE NOW</div>' : ''}
        `;
        return card;
    }

    /**
     * Load News
     */
    async loadNews() {
        const newsSection = document.querySelector('#news-section .section-content');
        if (!newsSection) return;

        try {
            const response = await fetch(`/api/tournaments/${this.tournamentSlug}/news/`);
            const data = await response.json();

            if (data.news && data.news.length > 0) {
                const newsList = document.createElement('div');
                newsList.className = 'news-list';

                data.news.slice(0, 5).forEach(newsItem => {
                    newsList.appendChild(this.createNewsCard(newsItem));
                });

                newsSection.innerHTML = '';
                newsSection.appendChild(newsList);
            }
        } catch (error) {
            console.error('Failed to load news:', error);
            // Keep the empty state
        }
    }

    /**
     * Create News Card
     */
    createNewsCard(newsItem) {
        const card = document.createElement('div');
        card.className = 'news-card';
        card.innerHTML = `
            <div class="news-icon">
                <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                </svg>
            </div>
            <div class="news-content">
                <h4>${newsItem.title}</h4>
                <p>${newsItem.excerpt}</p>
                <span class="news-time">${this.formatTime(newsItem.created_at)}</span>
            </div>
        `;
        return card;
    }

    /**
     * Activity Feed Updates
     */
    setupActivityFeed() {
        // Simulate live activity updates
        setInterval(() => {
            this.checkForNewActivity();
        }, 30000); // Every 30 seconds
    }

    async checkForNewActivity() {
        try {
            const response = await fetch(`/api/tournaments/${this.tournamentSlug}/activity/`);
            const data = await response.json();

            if (data.new_activities) {
                data.new_activities.forEach(activity => {
                    this.addActivityItem(activity);
                });
            }
        } catch (error) {
            console.error('Failed to check activity:', error);
        }
    }

    addActivityItem(activity) {
        const feed = document.querySelector('.activity-feed');
        if (!feed) return;

        const item = document.createElement('div');
        item.className = 'activity-item';
        item.innerHTML = `
            <div class="activity-icon ${activity.type === 'success' ? 'success' : ''}">
                ${this.getActivityIcon(activity.type)}
            </div>
            <div class="activity-content">
                <p class="activity-text">${activity.text}</p>
                <span class="activity-time">Just now</span>
            </div>
        `;
        
        feed.insertBefore(item, feed.firstChild);
        
        // Keep only last 10 items
        while (feed.children.length > 10) {
            feed.removeChild(feed.lastChild);
        }
    }

    getActivityIcon(type) {
        const icons = {
            success: '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
            info: '<svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>',
            warning: '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>'
        };
        return icons[type] || icons.info;
    }

    /**
     * Auto Refresh for Live Tournaments
     */
    setupAutoRefresh() {
        const statusPill = document.querySelector('.status-pill.live');
        if (!statusPill) return;

        // Refresh every 30 seconds during live tournaments
        this.refreshInterval = setInterval(() => {
            this.refreshLiveData();
        }, 30000);
    }

    async refreshLiveData() {
        try {
            await Promise.all([
                this.loadMatches(),
                this.checkForNewActivity()
            ]);
        } catch (error) {
            console.error('Failed to refresh data:', error);
        }
    }

    /**
     * Navigation Helpers
     */
    scrollToSection(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    openBracket() {
        window.location.href = `/tournaments/t/${this.tournamentSlug}/bracket/`;
    }

    openStandings() {
        window.location.href = `/tournaments/t/${this.tournamentSlug}/standings/`;
    }

    openRules() {
        window.location.href = `/tournaments/t/${this.tournamentSlug}/#rules`;
    }

    /**
     * Utility Functions
     */
    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
    }

    formatMatchTime(timestamp) {
        if (!timestamp) return 'TBD';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = date - now;
        
        if (diff < 0) return 'In Progress';
        if (diff < 3600000) return `In ${Math.ceil(diff / 60000)} min`;
        if (diff < 86400000) return `In ${Math.ceil(diff / 3600000)}h`;
        
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    formatTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;
        
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    /**
     * Toast Notifications
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div class="toast-icon">
                    ${this.getToastIcon(type)}
                </div>
                <div class="toast-message">${message}</div>
            </div>
        `;

        container.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    getToastIcon(type) {
        const icons = {
            success: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
            error: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
            info: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
        };
        return icons[type] || icons.info;
    }

    /**
     * Cleanup
     */
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new WarRoom());
} else {
    new WarRoom();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.warRoom) {
        window.warRoom.destroy();
    }
});
