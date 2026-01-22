// Follow/Unfollow System JavaScript
// Clean implementation with state persistence and live count updates

// Initialize follow button state from server and reload on page load
document.addEventListener('DOMContentLoaded', function() {
    const stateScript = document.getElementById('profile-follow-state');
    if (!stateScript) return; // Not on profile page
    
    try {
        const serverState = JSON.parse(stateScript.textContent);
        const followButtons = document.querySelectorAll('[data-follow-btn]');
        
        // Initialize all follow buttons
        followButtons.forEach(button => {
            initializeFollowButton(button, serverState);
        });
        
        // Reload current follow status from API (fixes state persistence bug)
        reloadFollowStatus(serverState.profile_username);
        
    } catch (e) {
        console.error('Failed to parse follow state:', e);
    }
});

/**
 * Reload follow status from API after page load
 * Fixes bug where "Requested" reverts to "Follow" after refresh
 */
async function reloadFollowStatus(username) {
    try {
        const response = await fetch(`/api/profile/${username}/follow/status/`, {
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            const data = await response.json();
            const followButtons = document.querySelectorAll('[data-follow-btn]');
            
            followButtons.forEach(button => {
                updateButtonState(button, data);
            });
        }
    } catch (error) {
        console.error('Failed to reload follow status:', error);
    }
}

/**
 * Update button appearance based on server state
 */
function updateButtonState(button, data) {
    const state = data.relationship_state || data.state;
    const isPrivateAccount = data.is_private_account || false;
    
    switch(state) {
        case 'following':
            button.className = 'bg-white/10 text-white font-bold uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-red-500/20 hover:text-red-400 transition flex items-center justify-center gap-2';
            button.innerHTML = '<i class="fa-solid fa-user-check"></i> Following';
            button.dataset.isFollowing = 'true';
            button.dataset.state = 'following';
            button.disabled = false;
            break;
            
        case 'requested':
            button.className = 'bg-yellow-500/30 text-yellow-200 font-bold uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-yellow-500/50 transition flex items-center justify-center gap-2';
            button.innerHTML = '<i class="fa-solid fa-clock"></i> Requested';
            button.dataset.isFollowing = 'false';
            button.dataset.state = 'requested';
            button.disabled = false; // Allow canceling request
            button.title = 'Click to cancel follow request';
            break;
            
        case 'none':
            if (isPrivateAccount) {
                button.className = 'bg-z-cyan text-black font-black font-display uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-white hover:scale-105 transition shadow-neon-cyan flex items-center justify-center gap-2';
                button.innerHTML = '<i class="fa-solid fa-lock"></i> Request Follow';
            } else {
                button.className = 'bg-z-cyan text-black font-black font-display uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-white hover:scale-105 transition shadow-neon-cyan flex items-center justify-center gap-2';
                button.innerHTML = '<i class="fa-solid fa-user-plus"></i> Follow';
            }
            button.dataset.isFollowing = 'false';
            button.dataset.state = 'none';
            button.dataset.isPrivate = isPrivateAccount;
            button.disabled = false;
            break;
            
        case 'self':
            button.style.display = 'none';
            break;
    }
}

function initializeFollowButton(button, serverState) {
    updateButtonState(button, serverState);
    
    // Attach click handler
    button.addEventListener('click', function() {
        const state = button.dataset.state;
        
        if (state === 'following') {
            unfollowUser(serverState.profile_username, button);
        } else if (state === 'requested') {
            cancelFollowRequest(serverState.profile_username, button);
        } else {
            followUser(serverState.profile_username, button);
        }
    });
}

async function followUser(username, button) {
    button.disabled = true;
    const originalHTML = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    
    try {
        const response = await fetch(`/api/profile/${username}/follow/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Handle different follow actions
            if (data.action === 'request_sent') {
                // Follow request sent to private account
                button.className = 'bg-yellow-500/30 text-yellow-200 font-bold uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-yellow-500/50 transition flex items-center justify-center gap-2';
                button.innerHTML = '<i class="fa-solid fa-clock"></i> Requested';
                button.dataset.isFollowing = 'false';
                button.dataset.state = 'requested';
                button.disabled = false;
                button.title = 'Click to cancel follow request';
                
                // Show toast notification
                showToast('Follow request sent!', 'success');
            } else {
                // Immediate follow (public account)
                button.className = 'bg-white/10 text-white font-bold uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-red-500/20 hover:text-red-400 transition flex items-center justify-center gap-2';
                button.innerHTML = '<i class="fa-solid fa-user-check"></i> Following';
                button.dataset.isFollowing = 'true';
                button.dataset.state = 'following';
                button.disabled = false;
                
                // Update follower count live
                updateFollowerCount(1);
                
                // Show toast notification
                showToast('Now following user!', 'success');
            }
            
            console.log('Follow action successful:', data);
        } else {
            throw new Error(data.error || 'Failed to follow user');
        }
    if (!confirm('Unfollow this user?')) {
        return;
    }
    
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Unfollowing...';
    
    try {
        const response = await fetch(`/api/profile/${username}/unfollow/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            const isPrivate = button.dataset.isPrivate === 'true';
            button.className = 'bg-z-cyan text-black font-black font-display uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-white hover:scale-105 transition shadow-neon-cyan flex items-center justify-center gap-2';
            button.innerHTML = isPrivate ? '<i class="fa-solid fa-lock"></i> Request Follow' : '<i class="fa-solid fa-user-plus"></i> Follow';
            button.dataset.isFollowing = 'false';
            button.dataset.state = 'none';
            button.disabled = false;
            
            // Update follower count live
            updateFollowerCount(-1);
            
            showToast('Unfollowed user', 'info');
            console.log('Unfollow successful:', data);
        } else {
            throw new Error(data.error || 'Failed to unfollow user');
        }
    } catch (error) {
        console.error('Unfollow error:', error);
        showToast(error.message || 'Failed to unfollow user', 'error');
        button.className = 'bg-white/10 text-white font-bold uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-red-500/20 hover:text-red-400 transition flex items-center justify-center gap-2';
        button.innerHTML = '<i class="fa-solid fa-user-check"></i> Following';
        button.disabled = false;
    }
}

/**
 * Show toast notification (fallback if toast system not available)
 */
function showToast(message, type = 'info') {
    if (typeof window.ToastManager !== 'undefined' && window.toastManager) {
        window.toastManager.show(message, type);
    } else {
        console.log(`[Toast ${type}]:`, message);
            
            showToast('Follow request canceled', 'info');
            console.log('Cancel request successful:', data);
        } else {
            throw new Error(data.error || 'Failed to cancel request');
        }
    } catch (error) {
        console.error('Cancel request error:', error);
        showToast(error.message || 'Failed to cancel request', 'error');
        button.className = 'bg-yellow-500/30 text-yellow-200 font-bold uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-yellow-500/50 transition flex items-center justify-center gap-2';
        button.innerHTML = '<i class="fa-solid fa-clock"></i> Requested';
        button.disabled = false;
    }
}

async function unfollowUser(username, button) {
    button.disabled = true;
    button.textContent = 'Unfollowing...';
    
    try {
        const response = await fetch(`/api/profile/${username}/unfollow/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            button.className = 'bg-z-cyan text-black font-black font-display uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-white hover:scale-105 transition shadow-neon-cyan flex items-center justify-center gap-2';
            button.innerHTML = '<i class="fa-solid fa-user-plus"></i> Follow';
            button.dataset.isFollowing = 'false';
            button.disabled = false;
            
            // Update follower count live
            updateFollowerCount(-1);
            
            console.log('Unfollow successful:', data);
        } else {
            throw new Error(data.error || 'Failed to unfollow user');
        }
    } catch (error) {
        console.error('Unfollow error:', error);
        alert(error.message);
        button.className = 'bg-white/10 text-white font-bold uppercase tracking-wider px-10 py-4 rounded-xl hover:bg-red-500/20 hover:text-red-400 transition flex items-center justify-center gap-2';
        button.innerHTML = '<i class="fa-solid fa-user-check"></i> Following';
        button.disabled = false;
    }
}

/**
 * Update follower count live without page reload
 * @param {number} delta - +1 for follow, -1 for unfollow
 */
function updateFollowerCount(delta) {
    const followerElements = document.querySelectorAll('[data-follower-count]');
    followerElements.forEach(el => {
        const currentCount = parseInt(el.textContent.replace(/,/g, '')) || 0;
        const newCount = Math.max(0, currentCount + delta);
        el.textContent = newCount.toLocaleString();
    });
}

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
