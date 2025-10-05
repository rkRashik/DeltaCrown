/**
 * Tournament Dashboard V8 - Interactive Features
 */

class TournamentDashboard {
    constructor() {
        this.tournamentSlug = document.querySelector('[data-tournament-slug]')?.dataset.tournamentSlug;
        this.teamId = document.querySelector('[data-team-id]')?.dataset.teamId;
        this.init();
    }

    init() {
        this.setupCheckIn();
        this.setupNotifications();
        this.setupAutoRefresh();
        this.animateStats();
    }

    /**
     * Setup check-in functionality
     */
    setupCheckIn() {
        const checkInBtn = document.getElementById('check-in-btn');
        if (!checkInBtn) return;

        checkInBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            
            if (!confirm('Are you sure you want to check in?')) return;

            try {
                checkInBtn.disabled = true;
                checkInBtn.innerHTML = `
                    <svg class="animate-spin" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
                    </svg>
                    Checking in...
                `;

                const response = await fetch(`/tournaments/${this.tournamentSlug}/check-in/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    }
                });

                const data = await response.json();

                if (data.success) {
                    this.showNotification('✓ Checked in successfully!', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    throw new Error(data.message || 'Check-in failed');
                }
            } catch (error) {
                this.showNotification('✗ ' + error.message, 'error');
                checkInBtn.disabled = false;
                checkInBtn.innerHTML = `
                    <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <path d="M22 4L12 14.01l-3-3"/>
                    </svg>
                    Check In
                `;
            }
        });
    }

    /**
     * Setup notification system
     */
    setupNotifications() {
        const notificationItems = document.querySelectorAll('[data-notification-id]');
        
        notificationItems.forEach(item => {
            item.addEventListener('click', async () => {
                const notificationId = item.dataset.notificationId;
                
                try {
                    await fetch(`/api/notifications/${notificationId}/mark-read/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': this.getCSRFToken()
                        }
                    });
                    
                    item.classList.add('read');
                    this.updateNotificationCount();
                } catch (error) {
                    console.error('Error marking notification as read:', error);
                }
            });
        });
    }

    /**
     * Auto-refresh dashboard data
     */
    setupAutoRefresh() {
        // Refresh every 30 seconds if tournament is running
        const status = document.querySelector('[data-tournament-status]')?.dataset.tournamentStatus;
        
        if (status === 'RUNNING') {
            setInterval(() => {
                this.refreshDashboardData();
            }, 30000);
        }
    }

    /**
     * Refresh dashboard data via AJAX
     */
    async refreshDashboardData() {
        try {
            const response = await fetch(`/api/tournaments/${this.tournamentSlug}/dashboard-data/`);
            const data = await response.json();
            
            // Update stats
            this.updateStats(data.stats);
            
            // Update matches if any
            if (data.upcoming_matches_count !== undefined) {
                const matchCount = document.querySelector('[data-stat="upcoming-matches"]');
                if (matchCount) {
                    matchCount.textContent = data.upcoming_matches_count;
                }
            }
        } catch (error) {
            console.error('Error refreshing dashboard data:', error);
        }
    }

    /**
     * Update stat values
     */
    updateStats(stats) {
        Object.entries(stats).forEach(([key, value]) => {
            const element = document.querySelector(`[data-stat="${key}"]`);
            if (element && element.textContent !== String(value)) {
                this.animateValueChange(element, value);
            }
        });
    }

    /**
     * Animate value changes
     */
    animateValueChange(element, newValue) {
        element.style.transform = 'scale(1.1)';
        element.style.color = 'var(--primary)';
        
        setTimeout(() => {
            element.textContent = newValue;
            element.style.transform = 'scale(1)';
        }, 150);
        
        setTimeout(() => {
            element.style.color = '';
        }, 500);
    }

    /**
     * Animate stats on load
     */
    animateStats() {
        const statValues = document.querySelectorAll('.stat-card-value');
        
        statValues.forEach((stat, index) => {
            const finalValue = parseInt(stat.textContent) || 0;
            stat.textContent = '0';
            
            setTimeout(() => {
                this.countUp(stat, 0, finalValue, 1000);
            }, index * 100);
        });
    }

    /**
     * Count up animation
     */
    countUp(element, start, end, duration) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= end) {
                element.textContent = end;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, 16);
    }

    /**
     * Show notification toast
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'success' ? 'var(--success)' : type === 'error' ? 'var(--danger)' : 'var(--primary)'};
            color: white;
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-lg);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    /**
     * Update notification count
     */
    updateNotificationCount() {
        const unreadCount = document.querySelectorAll('[data-notification-id]:not(.read)').length;
        const badge = document.querySelector('.notification-badge');
        
        if (badge) {
            badge.textContent = unreadCount;
            badge.style.display = unreadCount > 0 ? 'flex' : 'none';
        }
    }

    /**
     * Get CSRF token
     */
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new TournamentDashboard());
} else {
    new TournamentDashboard();
}

// Add slide animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .animate-spin {
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);
