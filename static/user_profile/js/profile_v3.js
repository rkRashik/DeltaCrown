/**
 * Profile V3 Controller - Vanilla JavaScript
 * Handles follow button, bio expand, and dynamic interactions
 * NO Alpine.js, NO hardcoded data
 */

class ProfileV3Controller {
    constructor() {
        this.isFollowing = false;
        this.followerCount = 0;
        this.isLoading = false;
        this.username = '';
        
        this.init();
    }
    
    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }
    
    setup() {
        this.setupFollowButton();
        this.setupBioToggle();
        this.setupCopyButtons();
    }
    
    setupFollowButton() {
        const followBtn = document.getElementById('follow-btn');
        if (!followBtn) return;
        
        this.isFollowing = followBtn.dataset.following === 'true';
        this.username = followBtn.dataset.username;
        const followerCountEl = document.getElementById('follower-count');
        this.followerCount = followerCountEl ? parseInt(followerCountEl.textContent) : 0;
        
        followBtn.addEventListener('click', () => this.toggleFollow());
    }
    
    async toggleFollow() {
        if (this.isLoading) return;
        
        const followBtn = document.getElementById('follow-btn');
        const followText = document.getElementById('follow-text');
        const followIconAdd = document.getElementById('follow-icon-add');
        const followIconCheck = document.getElementById('follow-icon-check');
        const followerCountEl = document.getElementById('follower-count');
        
        if (!followBtn || !followText) return;
        
        this.isLoading = true;
        followBtn.disabled = true;
        followText.textContent = 'Loading...';
        
        const wasFollowing = this.isFollowing;
        const originalCount = this.followerCount;
        
        // Optimistic update
        this.isFollowing = !this.isFollowing;
        this.followerCount = this.isFollowing ? originalCount + 1 : Math.max(0, originalCount - 1);
        
        if (followerCountEl) {
            followerCountEl.textContent = this.followerCount;
        }
        this.updateFollowUI();
        
        try {
            const endpoint = this.isFollowing 
                ? `/actions/follow-safe/${this.username}/` 
                : `/actions/unfollow-safe/${this.username}/`;
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) throw new Error('Failed to toggle follow');
        } catch (error) {
            // Rollback on error
            console.error('Follow error:', error);
            this.isFollowing = wasFollowing;
            this.followerCount = originalCount;
            
            if (followerCountEl) {
                followerCountEl.textContent = this.followerCount;
            }
            this.updateFollowUI();
        } finally {
            this.isLoading = false;
            followBtn.disabled = false;
        }
    }
    
    updateFollowUI() {
        const followBtn = document.getElementById('follow-btn');
        const followText = document.getElementById('follow-text');
        const followIconAdd = document.getElementById('follow-icon-add');
        const followIconCheck = document.getElementById('follow-icon-check');
        
        if (!followBtn || !followText) return;
        
        if (this.isFollowing) {
            followBtn.classList.remove('btn-primary');
            followBtn.classList.add('btn-secondary');
            followText.textContent = 'Following';
            
            if (followIconAdd) followIconAdd.classList.add('hidden');
            if (followIconCheck) followIconCheck.classList.remove('hidden');
        } else {
            followBtn.classList.remove('btn-secondary');
            followBtn.classList.add('btn-primary');
            followText.textContent = 'Follow';
            
            if (followIconAdd) followIconAdd.classList.remove('hidden');
            if (followIconCheck) followIconCheck.classList.add('hidden');
        }
    }
    
    setupBioToggle() {
        const bioToggle = document.getElementById('bio-toggle');
        const bioText = document.getElementById('bio-text');
        
        if (!bioToggle || !bioText) return;
        
        let expanded = false;
        
        bioToggle.addEventListener('click', () => {
            expanded = !expanded;
            
            if (expanded) {
                bioText.classList.remove('line-clamp-3');
                bioToggle.textContent = 'Show less';
            } else {
                bioText.classList.add('line-clamp-3');
                bioToggle.textContent = 'Read more';
            }
        });
    }
    
    setupCopyButtons() {
        // Copy public ID
        const copyPublicIdBtn = document.getElementById('copy-public-id');
        if (copyPublicIdBtn) {
            copyPublicIdBtn.addEventListener('click', () => {
                const publicId = copyPublicIdBtn.dataset.publicId;
                this.copyToClipboard(publicId, copyPublicIdBtn);
            });
        }
        
        // Copy profile URL
        const copyUrlBtn = document.getElementById('copy-profile-url');
        if (copyUrlBtn) {
            copyUrlBtn.addEventListener('click', () => {
                const url = window.location.href;
                this.copyToClipboard(url, copyUrlBtn);
            });
        }
    }
    
    async copyToClipboard(text, button) {
        try {
            await navigator.clipboard.writeText(text);
            
            const originalText = button.textContent;
            button.textContent = '✓ Copied!';
            button.classList.add('bg-green-600');
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('bg-green-600');
            }, 2000);
        } catch (error) {
            console.error('Copy failed:', error);
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            
            button.textContent = '✓ Copied!';
            setTimeout(() => {
                button.textContent = 'Copy';
            }, 2000);
        }
    }
    
    getCsrfToken() {
        const cookie = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        
        return cookie ? cookie.split('=')[1] : '';
    }
}

// Initialize controller
window.profileV3Controller = new ProfileV3Controller();
