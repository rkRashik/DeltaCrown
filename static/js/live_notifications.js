/**
 * Live Notifications System with SSE and Polling Fallback
 * Automatically updates notification and follow request counts
 */

class LiveNotifications {
    constructor() {
        this.sseSource = null;
        this.pollingInterval = null;
        this.sseRetryCount = 0;
        this.maxSseRetries = 3;
        this.pollingRate = 5000; // 5 seconds
        this.isAuthenticated = document.body.dataset.userAuthenticated === 'true';
        
        if (this.isAuthenticated) {
            this.init();
        }
    }
    
    init() {
        // Try SSE first
        this.initSSE();
        
        // Set up fallback to polling if SSE fails
        setTimeout(() => {
            if (!this.sseSource || this.sseSource.readyState !== 1) {
                console.log('SSE not available, falling back to polling');
                this.initPolling();
            }
        }, 2000);
    }
    
    initSSE() {
        try {
            this.sseSource = new EventSource('/notifications/stream/');
            
            this.sseSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.updateCounts(data);
                    this.sseRetryCount = 0; // Reset retry count on success
                } catch (error) {
                    console.error('Error parsing SSE data:', error);
                }
            };
            
            this.sseSource.onerror = (error) => {
                console.error('SSE connection error:', error);
                this.sseSource.close();
                
                // Retry SSE up to max retries
                if (this.sseRetryCount < this.maxSseRetries) {
                    this.sseRetryCount++;
                    console.log(`Retrying SSE connection (${this.sseRetryCount}/${this.maxSseRetries})...`);
                    setTimeout(() => this.initSSE(), 3000);
                } else {
                    console.log('Max SSE retries reached, falling back to polling');
                    this.initPolling();
                }
            };
            
            this.sseSource.onopen = () => {
                console.log('SSE connection established');
            };
        } catch (error) {
            console.error('Error initializing SSE:', error);
            this.initPolling();
        }
    }
    
    initPolling() {
        // Clear any existing SSE connection
        if (this.sseSource) {
            this.sseSource.close();
            this.sseSource = null;
        }
        
        // Clear any existing polling
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
        }
        
        // Start polling
        this.pollingInterval = setInterval(() => {
            this.fetchCounts();
        }, this.pollingRate);
        
        // Initial fetch
        this.fetchCounts();
    }
    
    async fetchCounts() {
        try {
            // Fetch unread notifications count
            const notifResponse = await fetch('/notifications/unread_count/');
            if (notifResponse.ok) {
                const notifData = await notifResponse.json();
                
                // Fetch pending follow requests count
                const requestsResponse = await fetch('/me/follow-requests/?status=PENDING');
                if (requestsResponse.ok) {
                    const requestsData = await requestsResponse.json();
                    
                    this.updateCounts({
                        unread_notifications: notifData.count || 0,
                        pending_follow_requests: requestsData.count || 0
                    });
                }
            }
        } catch (error) {
            console.error('Error fetching counts:', error);
        }
    }
    
    updateCounts(data) {
        // Update notification bell badge
        const notifBadge = document.querySelector('#notification-bell-badge');
        if (notifBadge) {
            notifBadge.textContent = data.unread_notifications;
            if (data.unread_notifications > 0) {
                notifBadge.classList.remove('hidden');
            } else {
                notifBadge.classList.add('hidden');
            }
        }
        
        // Phase 4 Step 1.1: Refresh dropdown if open
        const openDropdown = document.querySelector('.dc-notif-dropdown.is-open');
        if (openDropdown && window.DCNotifications && typeof window.DCNotifications.fetchPreview === 'function') {
            window.DCNotifications.fetchPreview(openDropdown);
        }
        
        // Update follow requests badge (on notifications page)
        const requestBadge = document.getElementById('pending-badge');
        if (requestBadge) {
            requestBadge.textContent = data.pending_follow_requests;
            if (data.pending_follow_requests > 0) {
                requestBadge.classList.remove('hidden');
            } else {
                requestBadge.classList.add('hidden');
            }
        }
        
        // Update count badges in follow requests sub-tabs
        const pendingCountBadge = document.getElementById('count-pending');
        if (pendingCountBadge) {
            pendingCountBadge.textContent = data.pending_follow_requests;
            if (data.pending_follow_requests > 0) {
                pendingCountBadge.classList.remove('hidden');
            } else {
                pendingCountBadge.classList.add('hidden');
            }
        }
        
        // If on notifications page and follow requests tab is active, refresh the list
        if (window.location.pathname === '/notifications/') {
            const currentTab = window.currentRequestTab;
            if (currentTab === 'pending' && typeof window.loadFollowRequests === 'function') {
                // Only refresh if count changed
                const currentCount = parseInt(pendingCountBadge?.textContent || 0);
                if (currentCount !== data.pending_follow_requests) {
                    window.loadFollowRequests();
                }
            }
        }
    }
    
    destroy() {
        if (this.sseSource) {
            this.sseSource.close();
            this.sseSource = null;
        }
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }
}

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.liveNotifications = new LiveNotifications();
    });
} else {
    window.liveNotifications = new LiveNotifications();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.liveNotifications) {
        window.liveNotifications.destroy();
    }
});
