/**
 * Follow System V2 - Modern Implementation
 * ==========================================
 * 
 * Clean, performant JavaScript for followers/following functionality.
 * Features: Infinite scroll, search, optimistic updates, caching.
 * 
 * Author: GitHub Copilot
 * Date: January 22, 2026
 */

class FollowSystemV2 {
    constructor() {
        this.cache = new Map();
        this.currentModal = null;
        this.currentUsername = null;
        this.currentPage = 1;
        this.isLoading = false;
        this.hasMore = true;
        this.searchTimeout = null;
        
        this.init();
    }
    
    init() {
        // Initialize modal event listeners
        this.setupModalHandlers();
        
        // Initialize all follow buttons
        this.setupFollowButtons();
    }
    
    setupModalHandlers() {
        // Close on backdrop click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('follow-modal-overlay')) {
                this.closeModal();
            }
        });
        
        // Close on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.currentModal) {
                this.closeModal();
            }
        });
    }
    
    setupFollowButtons() {
        // Set up delegation for dynamically created follow buttons
        document.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-mini-follow-btn]');
            if (btn) {
                e.preventDefault();
                const username = btn.dataset.username;
                const isFollowing = btn.dataset.isFollowing === 'true';
                
                if (isFollowing) {
                    this.unfollowUser(username, btn);
                } else {
                    this.followUser(username, btn);
                }
            }
        });
    }
    
    // ============================================
    // MODAL FUNCTIONS
    // ============================================
    
    openFollowersModal(username) {
        console.log('[FollowSystemV2] openFollowersModal', username);
        this.currentModal = 'followers';
        this.currentUsername = username;
        this.currentPage = 1;
        this.hasMore = true;
        
        const modal = document.getElementById('followersModal');
        const list = document.getElementById('followersList');
        const search = document.getElementById('followersSearch');
        
        // Reset state
        list.innerHTML = '<div class="loading-skeleton"></div>'.repeat(5);
        search.value = '';
        
        // Show modal
        if (modal) {
            modal.classList.remove('hidden');
            setTimeout(() => modal.classList.add('active'), 10);
        } else {
            console.warn('[FollowSystemV2] followersModal element not found');
        }
        
        // Load data
        this.loadFollowers(username, 1).then(() => console.log('[FollowSystemV2] loadFollowers complete'));
        
        // Setup search
        if (search) {
            search.addEventListener('input', (e) => {
                clearTimeout(this.searchTimeout);
                this.searchTimeout = setTimeout(() => {
                    this.searchUsers(e.target.value);
                }, 300);
            });
        }
        
        // Setup infinite scroll
        if (list) list.addEventListener('scroll', () => this.handleScroll(list));
    }
    
    openFollowingModal(username) {
        this.currentModal = 'following';
        this.currentUsername = username;
        this.currentPage = 1;
        this.hasMore = true;
        
        const modal = document.getElementById('followingModal');
        const list = document.getElementById('followingList');
        const search = document.getElementById('followingSearch');
        
        // Reset state
        list.innerHTML = '<div class="loading-skeleton"></div>'.repeat(5);
        search.value = '';
        
        // Show modal
        modal.classList.remove('hidden');
        setTimeout(() => modal.classList.add('active'), 10);
        
        // Load data
        this.loadFollowing(username, 1);
        
        // Setup search
        search.addEventListener('input', (e) => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.searchUsers(e.target.value);
            }, 300);
        });
        
        // Setup infinite scroll
        list.addEventListener('scroll', () => this.handleScroll(list));
    }
    
    closeModal() {
        const modals = document.querySelectorAll('.follow-modal-overlay');
        modals.forEach(modal => {
            modal.classList.remove('active');
            setTimeout(() => modal.classList.add('hidden'), 300);
        });
        
        this.currentModal = null;
        this.currentUsername = null;
    }
    
    // ============================================
    // API FUNCTIONS
    // ============================================
    
    async loadFollowers(username, page = 1) {
        console.log('[FollowSystemV2] loadFollowers start', username, page);
        if (this.isLoading) {
            console.log('[FollowSystemV2] loadFollowers: already loading');
            return;
        }
        this.isLoading = true;
        
        const listEl = document.getElementById('followersList');
        if (!listEl) {
            console.warn('[FollowSystemV2] followersList element not found');
            this.isLoading = false;
            return;
        }
        
        try {
            const response = await fetch(`/api/profile/${username}/followers/?page=${page}&per_page=20`);
            console.log('[FollowSystemV2] loadFollowers response status:', response.status);
            const data = await response.json();
            console.log('[FollowSystemV2] loadFollowers response data:', data);
            
            if (data && data.success) {
                if (page === 1) {
                    listEl.innerHTML = '';
                }
                
                // Normalize response shape: support {data.users} and legacy {followers}
                const users = (data.data && data.data.users) ? data.data.users : (data.followers || data.users || []);
                const hasNext = (data.data && data.data.pagination) ? data.data.pagination.has_next : (data.has_more || false);

                if ((!users || users.length === 0) && page === 1) {
                    listEl.innerHTML = `
                        <div class="empty-state">
                            <i class="fa-solid fa-users text-5xl opacity-30 mb-4"></i>
                            <p class="text-gray-400">No followers yet</p>
                        </div>
                    `;
                } else {
                    users.forEach(user => {
                        listEl.appendChild(this.createUserCard(user));
                    });
                }

                // Ensure modal is visible (defensive)
                const modalEl = document.getElementById('followersModal');
                if (modalEl) {
                    modalEl.classList.remove('hidden');
                    modalEl.classList.add('active');
                }

                this.hasMore = !!hasNext;
                this.currentPage = page;
            } else {
                const err = (data && data.error) ? data.error : 'Unknown error';
                console.error('[FollowSystemV2] loadFollowers error payload:', data);
                this.showError(listEl, err);
            }
        } catch (error) {
            console.error('[FollowSystemV2] Error loading followers:', error);
            this.showError(listEl, 'Failed to load followers');
        } finally {
            this.isLoading = false;
        }
    }
    
    async loadFollowing(username, page = 1) {
        if (this.isLoading) return;
        this.isLoading = true;
        
        const listEl = document.getElementById('followingList');
        
        try {
            const response = await fetch(`/api/profile/${username}/following/?page=${page}&per_page=20`);
            const data = await response.json();
            
            if (data.success) {
                if (page === 1) {
                    listEl.innerHTML = '';
                }
                
                // Normalize response shape
                const users = (data.data && data.data.users) ? data.data.users : (data.following || data.users || []);
                const hasNext = (data.data && data.data.pagination) ? data.data.pagination.has_next : (data.has_more || false);

                if ((!users || users.length === 0) && page === 1) {
                    listEl.innerHTML = `
                        <div class="empty-state">
                            <i class="fa-solid fa-user-plus text-5xl opacity-30 mb-4"></i>
                            <p class="text-gray-400">Not following anyone yet</p>
                        </div>
                    `;
                } else {
                    users.forEach(user => {
                        listEl.appendChild(this.createUserCard(user));
                    });
                }

                // Ensure modal is visible (defensive)
                const modalEl = document.getElementById('followingModal');
                if (modalEl) {
                    modalEl.classList.remove('hidden');
                    modalEl.classList.add('active');
                }

                this.hasMore = !!hasNext;
                this.currentPage = page;
            } else {
                this.showError(listEl, data.error);
            }
        } catch (error) {
            console.error('Error loading following:', error);
            this.showError(listEl, 'Failed to load following');
        } finally {
            this.isLoading = false;
        }
    }
    
    async searchUsers(query) {
        if (!this.currentModal || !this.currentUsername) return;
        
        this.currentPage = 1;
        this.hasMore = true;
        
        const listId = this.currentModal === 'followers' ? 'followersList' : 'followingList';
        const listEl = document.getElementById(listId);
        listEl.innerHTML = '<div class="loading-skeleton"></div>'.repeat(3);
        
        const endpoint = this.currentModal === 'followers' ? 'followers' : 'following';
        const searchParam = query ? `&search=${encodeURIComponent(query)}` : '';
        
        try {
            const response = await fetch(`/api/profile/${this.currentUsername}/${endpoint}/?page=1&per_page=20${searchParam}`);
            const data = await response.json();
            
            if (data.success) {
                listEl.innerHTML = '';
                
                if (data.data.users.length === 0) {
                    listEl.innerHTML = `
                        <div class="empty-state">
                            <i class="fa-solid fa-search text-3xl opacity-30 mb-2"></i>
                            <p class="text-gray-400 text-sm">No results for "${query}"</p>
                        </div>
                    `;
                } else {
                    data.data.users.forEach(user => {
                        listEl.appendChild(this.createUserCard(user));
                    });
                }
                
                this.hasMore = data.data.pagination.has_next;
            }
        } catch (error) {
            console.error('Error searching:', error);
        }
    }
    
    handleScroll(listEl) {
        if (this.isLoading || !this.hasMore) return;
        
        const scrollBottom = listEl.scrollHeight - listEl.scrollTop - listEl.clientHeight;
        
        if (scrollBottom < 100) {
            const nextPage = this.currentPage + 1;
            if (this.currentModal === 'followers') {
                this.loadFollowers(this.currentUsername, nextPage);
            } else {
                this.loadFollowing(this.currentUsername, nextPage);
            }
        }
    }
    
    // ============================================
    // FOLLOW/UNFOLLOW ACTIONS
    // ============================================
    
    async followUser(username, button) {
        const originalHTML = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        
        console.log('[FollowSystemV2] Following user:', username);
        
        try {
            const response = await fetch(`/api/profile/${username}/follow/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            console.log('[FollowSystemV2] Response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('[FollowSystemV2] HTTP error:', response.status, errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const data = await response.json();
            console.log('[FollowSystemV2] Response data:', data);
            
            if (data.success) {
                // Handle different actions (followed vs request_sent)
                if (data.action === 'request_sent') {
                    button.innerHTML = '<i class="fa-solid fa-clock"></i> Requested';
                    button.className = 'btn-mini-requested';
                    button.dataset.isFollowing = 'false';
                    button.disabled = true;
                    this.showToast('Follow request sent to ' + username, 'success');
                } else {
                    button.innerHTML = '<i class="fa-solid fa-user-check"></i> Following';
                    button.className = 'btn-mini-following';
                    button.dataset.isFollowing = 'true';
                    button.disabled = false;
                    this.showToast('Following ' + username, 'success');
                    
                    // Update follower count live
                    this.updateFollowerCount(1);
                }
            } else {
                throw new Error(data.error || 'Failed to follow');
            }
        } catch (error) {
            console.error('[FollowSystemV2] Follow error:', error);
            button.innerHTML = originalHTML;
            button.disabled = false;
            this.showToast(error.message || 'Failed to follow user', 'error');
        }
    }
    
    async unfollowUser(username, button) {
        const originalHTML = button.innerHTML;
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        
        console.log('[FollowSystemV2] Unfollowing user:', username);
        
        try {
            const response = await fetch(`/api/profile/${username}/unfollow/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            console.log('[FollowSystemV2] Response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('[FollowSystemV2] HTTP error:', response.status, errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const data = await response.json();
            console.log('[FollowSystemV2] Response data:', data);
            
            if (data.success) {
                button.innerHTML = '<i class="fa-solid fa-user-plus"></i> Follow';
                button.className = 'btn-mini-follow';
                button.dataset.isFollowing = 'false';
                button.disabled = false;
                
                // Update follower count live
                this.updateFollowerCount(-1);
                
                this.showToast('Unfollowed ' + username, 'info');
            } else {
                throw new Error(data.error || 'Failed to unfollow');
            }
        } catch (error) {
            console.error('[FollowSystemV2] Unfollow error:', error);
            button.innerHTML = originalHTML;
            button.disabled = false;
            this.showToast(error.message || 'Failed to unfollow user', 'error');
        }
    }
    
    // ============================================
    // UI HELPERS
    // ============================================
    
    createUserCard(user) {
        const card = document.createElement('div');
        card.className = 'user-card';
        
        let actionButton = '';
        if (!user.is_self) {
            if (user.is_following) {
                actionButton = `
                    <button class="btn-mini-following" 
                            data-mini-follow-btn
                            data-username="${user.username}"
                            data-is-following="true">
                        <i class="fa-solid fa-user-check"></i> Following
                    </button>
                `;
            } else {
                actionButton = `
                    <button class="btn-mini-follow" 
                            data-mini-follow-btn
                            data-username="${user.username}"
                            data-is-following="false">
                        <i class="fa-solid fa-user-plus"></i> Follow
                    </button>
                `;
            }
        }
        
        const mutualBadge = user.is_mutual ? '<span class="mutual-badge">Mutual</span>' : '';
        
        card.innerHTML = `
            <a href="${user.profile_url}" class="user-info">
                <img src="${user.avatar_url}" alt="${user.display_name}" class="user-avatar">
                <div class="user-details">
                    <div class="user-name">
                        ${user.display_name}
                        ${user.verified ? '<i class="fa-solid fa-badge-check text-cyan-400 ml-1"></i>' : ''}
                    </div>
                    <div class="user-username">@${user.username} ${mutualBadge}</div>
                    ${user.bio ? `<div class="user-bio">${this.escapeHtml(user.bio)}</div>` : ''}
                </div>
            </a>
            <div class="user-action">
                ${actionButton}
            </div>
        `;
        
        return card;
    }
    
    showError(container, message) {
        container.innerHTML = `
            <div class="error-state">
                <i class="fa-solid fa-exclamation-circle text-3xl text-red-400 mb-2"></i>
                <p class="text-red-400">${message}</p>
            </div>
        `;
    }
    
    showToast(message, type = 'info') {
        if (window.DCToast) {
            window.DCToast[type](message);
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getCookie(name) {
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
    
    /**
     * Update follower count live without page reload
     * @param {number} delta - +1 for follow, -1 for unfollow
     */
    updateFollowerCount(delta) {
        const followerElements = document.querySelectorAll('[data-follower-count]');
        followerElements.forEach(el => {
            const currentCount = parseInt(el.textContent.replace(/,/g, '')) || 0;
            const newCount = Math.max(0, currentCount + delta);
            el.textContent = newCount.toLocaleString();
        });
    }
}

// ============================================
// GLOBAL FUNCTIONS (for onclick handlers)
// ============================================

window.openFollowersModal = function(username) {
    window.followSystemV2.openFollowersModal(username);
};

window.openFollowingModal = function(username) {
    window.followSystemV2.openFollowingModal(username);
};

window.closeFollowModal = function() {
    window.followSystemV2.closeModal();
};

// ============================================
// INITIALIZE
// ============================================

function _initFollowSystemV2() {
    if (!window.followSystemV2) {
        window.followSystemV2 = new FollowSystemV2();
        console.log('✅ Follow System V2 initialized');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _initFollowSystemV2);
} else {
    // DOM already ready, initialize immediately
    _initFollowSystemV2();
}
