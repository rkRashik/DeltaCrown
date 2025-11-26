// ============================================
// MODULE 1: GLOBAL UTILITIES
// ============================================

/**
 * Copy to Clipboard with Toast Notification
 */
function copyToClipboard(text, elementId) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('✓ Copied to Clipboard!');
        
        // Visual feedback on the button
        const btn = document.getElementById(elementId);
        if (btn) {
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg> Copied!';
            btn.classList.add('bg-emerald-600');
            btn.classList.remove('bg-indigo-600');
            
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.classList.remove('bg-emerald-600');
                btn.classList.add('bg-indigo-600');
            }, 2000);
        }
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('⚠ Copy failed', true);
    });
}

/**
 * Show Toast Notification
 */
function showToast(message, isError = false) {
    // Remove existing toast if any
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    
    if (isError) {
        toast.style.borderColor = 'rgba(225, 29, 72, 0.5)';
        toast.style.color = '#e11d48';
    }
    
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Share Profile (Web Share API or Fallback)
 */
function shareProfile() {
    const url = window.location.href;
    const title = document.title;
    
    if (navigator.share) {
        navigator.share({
            title: title,
            url: url
        }).catch(() => {
            // User cancelled or error - fallback to copy
            copyToClipboardFallback(url);
        });
    } else {
        copyToClipboardFallback(url);
    }
}

function copyToClipboardFallback(url) {
    navigator.clipboard.writeText(url).then(() => {
        showToast('✓ Profile Link Copied!');
    }).catch(() => {
        showToast('⚠ Unable to copy link', true);
    });
}

/**
 * Follow/Unfollow User
 */
function toggleFollow(userId) {
    const btn = document.getElementById('followBtn');
    if (!btn) return;
    
    const isFollowing = btn.dataset.following === 'true';
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    if (!csrfToken) {
        showToast('⚠ Authentication error', true);
        return;
    }
    
    // Optimistic UI update
    if (isFollowing) {
        btn.innerHTML = `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/>
            </svg>
            Follow
        `;
        btn.classList.remove('bg-slate-700');
        btn.classList.add('bg-emerald-600');
        btn.dataset.following = 'false';
    } else {
        btn.innerHTML = `
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
            Following
        `;
        btn.classList.remove('bg-emerald-600');
        btn.classList.add('bg-slate-700');
        btn.dataset.following = 'true';
    }
    
    // Make API call
    fetch(`/api/users/${userId}/follow/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast(data.following ? '✓ Now Following!' : '✓ Unfollowed');
        } else {
            // Revert UI on error
            throw new Error(data.error || 'Failed to update follow status');
        }
    })
    .catch(error => {
        console.error('Follow error:', error);
        showToast('⚠ Action failed', true);
        // Revert the optimistic update
        toggleFollow(userId);
    });
}

/**
 * Download Certificate
 */
function downloadCertificate(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('✓ Downloading Certificate...');
}

/**
 * Toggle Wallet Blur (Privacy)
 */
function toggleWalletBlur() {
    const balanceEl = document.getElementById('walletBalance');
    const iconEl = document.getElementById('walletEyeIcon');
    
    if (!balanceEl || !iconEl) return;
    
    if (balanceEl.classList.contains('wallet-blur')) {
        balanceEl.classList.remove('wallet-blur');
        iconEl.innerHTML = `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
            </svg>
        `;
    } else {
        balanceEl.classList.add('wallet-blur');
        iconEl.innerHTML = `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
            </svg>
        `;
    }
}

/**
 * Navigate to Match Details
 */
function goToMatch(matchId) {
    window.location.href = `/matches/${matchId}/`;
}

/**
 * Navigate to Team Page
 */
function goToTeam(teamSlug) {
    window.location.href = `/teams/${teamSlug}/`;
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Animate reputation bar on page load
    const repBar = document.getElementById('reputationBar');
    if (repBar) {
        setTimeout(() => {
            const targetWidth = repBar.dataset.score || '85';
            repBar.style.width = targetWidth + '%';
        }, 500);
    }
    
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(el => {
        el.classList.add('tooltip');
    });
});
