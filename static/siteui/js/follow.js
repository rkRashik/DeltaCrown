// Follow/Unfollow System JavaScript
// Clean implementation with state persistence and live count updates

// Button styles shared by every follow state (brand primary = saffron; secondary states are neutral)
const FOLLOW_CLASS = {
    follow: 'bg-z-cyan text-black font-semibold px-6 py-2.5 rounded-xl hover:brightness-110 transition flex items-center justify-center gap-2 text-sm',
    following: 'bg-white/10 text-white font-semibold px-6 py-2.5 rounded-xl hover:bg-white/15 transition flex items-center justify-center gap-2 text-sm',
    requested: 'bg-white/10 text-white/80 font-semibold px-6 py-2.5 rounded-xl cursor-not-allowed flex items-center justify-center gap-2 text-sm'
};

// A button can carry extra layout classes (data-follow-extra-class, e.g. "w-full") that survive every restyle.
function followClass(button, kind) {
    return FOLLOW_CLASS[kind] + (button.dataset.followExtraClass ? ' ' + button.dataset.followExtraClass : '');
}

// Responses from a failed request can be HTML (CSRF/proxy errors); never let that surface as a JSON parse error.
async function readJson(response) {
    try {
        return await response.json();
    } catch (e) {
        return {};
    }
}

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
        
        // Reload current follow status from API (fixes state persistence bug). Visitors who are not signed in
        // have no follow state, so the request (always a 401) is skipped.
        if (serverState.viewer_is_authenticated) {
            reloadFollowStatus(serverState.profile_username);
        }
        
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
            const data = await readJson(response);
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
            button.className = followClass(button, 'following');
            button.innerHTML = '<i class="fa-solid fa-user-check"></i> Following';
            button.dataset.isFollowing = 'true';
            button.dataset.state = 'following';
            button.disabled = false;
            break;
            
        case 'requested':
            button.className = followClass(button, 'requested');
            button.innerHTML = '<i class="fa-solid fa-clock"></i> Requested';
            button.dataset.isFollowing = 'false';
            button.dataset.state = 'requested';
            // The backend has no "cancel request" endpoint (the unfollow API answers "not following" for a pending
            // request), so a pending request is shown as a disabled state instead of offering a cancel that cannot work.
            button.disabled = true;
            button.title = 'Waiting for approval';
            break;
            
        case 'none':
            if (isPrivateAccount) {
                button.className = followClass(button, 'follow');
                button.innerHTML = '<i class="fa-solid fa-lock"></i> Request to follow';
            } else {
                button.className = followClass(button, 'follow');
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

// Every follow button on the page (header, sidebar) shows the same relationship, so a change applies to all of them.
function syncAllButtons(state, isPrivate) {
    document.querySelectorAll('[data-follow-btn]').forEach(function (b) {
        updateButtonState(b, { relationship_state: state, is_private_account: !!isPrivate });
        b.dataset.followBusy = '0';
    });
}

function initializeFollowButton(button, serverState) {
    updateButtonState(button, serverState);

    // Attach the click handler once, even if initialisation is ever run again (for example after a bfcache restore)
    if (button.dataset.followBound === '1') return;
    button.dataset.followBound = '1';

    button.addEventListener('click', function() {
        if (button.disabled || button.dataset.followBusy === '1') return;
        const state = button.dataset.state;
        
        if (state === 'following') {
            unfollowUser(serverState.profile_username, button);
        } else if (state === 'requested') {
            return; // pending: nothing to do until the account approves or declines
        } else {
            followUser(serverState.profile_username, button);
        }
    });
}

async function followUser(username, button) {
    button.disabled = true;
    button.dataset.followBusy = '1';
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
        
        const data = await readJson(response);
        
        if (response.ok) {
            // Handle different follow actions
            if (data.action === 'request_sent') {
                // Follow request sent to private account
                syncAllButtons('requested', true);
                
                // Show toast notification
                followToast('Follow request sent!', 'success');
            } else {
                // Immediate follow (public account)
                syncAllButtons('following', false);
                
                // Update follower count live
                updateFollowerCount(1);
                
                // Show toast notification
                followToast('Now following user!', 'success');
            }
            
            console.log('Follow action successful:', data);
        } else {
            throw new Error(data.error || 'Failed to follow user');
        }
    } catch (error) {
        console.error('Follow error:', error);
        followToast(error.message || 'Failed to follow user', 'error');
        button.innerHTML = originalHTML;
        button.disabled = false;
    } finally {
        button.dataset.followBusy = '0';
    }
}

async function unfollowUser(username, button) {
    if (!confirm('Unfollow this user?')) {
        return;
    }
    
    button.disabled = true;
    button.dataset.followBusy = '1';
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
        
        const data = await readJson(response);
        
        if (response.ok) {
            syncAllButtons('none', button.dataset.isPrivate === 'true');
            
            // Update follower count live
            updateFollowerCount(-1);
            
            followToast('Unfollowed user', 'info');
            console.log('Unfollow successful:', data);
        } else {
            throw new Error(data.error || 'Failed to unfollow user');
        }
    } catch (error) {
        console.error('Unfollow error:', error);
        followToast(error.message || 'Failed to unfollow user', 'error');
        button.className = followClass(button, 'following');
        button.innerHTML = '<i class="fa-solid fa-user-check"></i> Following';
        button.disabled = false;
    } finally {
        button.dataset.followBusy = '0';
    }
}

/**
 * Show a toast. Several toast implementations exist on the site: toast.js / toast-modern.js take an options object
 * ({ type, message }), older page scripts take (message, type). One payload serves both: an object that carries
 * type/message and also stringifies to the message, plus the type as a second argument. If no implementation is
 * loaded, or it throws, a small polite live region shows the message so the result is still visible and announced.
 */
function followToast(message, type = 'info') {
    const payload = { type: type, message: message, toString: function () { return message; } };
    try {
        if (typeof window.showToast === 'function') {
            window.showToast(payload, type);
            return;
        }
    } catch (e) {
        console.warn('Toast implementation failed, using the fallback:', e);
    }
    let region = document.getElementById('follow-toast-region');
    if (!region) {
        region = document.createElement('div');
        region.id = 'follow-toast-region';
        region.setAttribute('role', 'status');
        region.setAttribute('aria-live', 'polite');
        region.style.cssText = 'position:fixed;bottom:1rem;right:1rem;z-index:9999;display:flex;flex-direction:column;gap:.5rem;';
        document.body.appendChild(region);
    }
    const item = document.createElement('div');
    item.textContent = message;
    item.style.cssText = 'padding:.6rem .9rem;border-radius:.75rem;background:#232427;color:#F6F1E7;border:1px solid #38332C;font-size:.875rem;';
    region.appendChild(item);
    setTimeout(function () { item.remove(); }, 4000);
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
    // 1. Best source: <meta name="csrf-token"> (works with CSRF_COOKIE_HTTPONLY=True)
    if (name === 'csrftoken') {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content && meta.content.length >= 32) return meta.content;
        const el = document.querySelector('[name=csrfmiddlewaretoken]');
        if (el && el.value) return el.value;
    }
    // 2. Fall back to document.cookie
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
