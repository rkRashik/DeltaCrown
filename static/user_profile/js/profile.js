/**
 * UP-UI-REBIRTH-01: Profile Page Interactions
 * Vanilla JavaScript for modern esports profile
 */

(function() {
    'use strict';
    
    // ========== API CLIENT ==========
    
    async function apiFetch(url, options = {}) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        
        const config = {
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                ...options.headers
            },
            credentials: 'same-origin',
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `Request failed with status ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }
    
    // ========== PASSPORT API ==========
    
    async function createPassport(passportData) {
        return await apiFetch('/api/passports/create/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(passportData)
        });
    }
    
    async function togglePassportLFT(passportId) {
        return await apiFetch('/api/passports/toggle-lft/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ passport_id: passportId })
        });
    }
    
    async function setPassportVisibility(passportId, visibility) {
        return await apiFetch('/api/passports/set-visibility/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ passport_id: passportId, visibility })
        });
    }
    
    async function pinPassport(passportId) {
        return await apiFetch('/api/passports/pin/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ passport_id: passportId })
        });
    }
    
    async function deletePassport(passportId) {
        return await apiFetch(`/api/passports/${passportId}/delete/`, {
            method: 'DELETE'
        });
    }
    
    async function reorderPassports(order) {
        return await apiFetch('/api/passports/reorder/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order })
        });
    }
    
    // ========== FOLLOW API ==========
    
    async function followUser(username) {
        return await apiFetch(`/actions/follow-safe/${username}/`, {
            method: 'POST'
        });
    }
    
    async function unfollowUser(username) {
        return await apiFetch(`/actions/unfollow-safe/${username}/`, {
            method: 'POST'
        });
    }
    
    // Expose to global for onclick handlers
    window.createPassport = async function(passportData) {
        return await createPassport(passportData);
    };
    
    window.addPassportCard = function(passport) {
        const container = document.getElementById('passports-container');
        if (!container) return;
        
        // Remove empty state if exists
        const emptyState = container.querySelector('.text-center.py-12');
        if (emptyState) emptyState.remove();
        
        // Create new passport card (simplified version - in production, use template)
        const card = document.createElement('div');
        card.setAttribute('data-passport-id', passport.id);
        card.className = 'glass-card p-6 space-y-4 transform transition-all duration-300 hover:scale-105';
        card.style.animation = 'slideInUp 0.3s ease-out';
        
        card.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="text-3xl">${passport.game_emoji || '🎮'}</div>
                    <div>
                        <h4 class="text-white font-bold text-lg">${passport.game_name}</h4>
                        <p class="text-slate-400 text-sm">${passport.ign}${passport.discriminator ? '#' + passport.discriminator : ''}</p>
                    </div>
                </div>
                <div class="flex gap-2">
                    <button onclick="window.pinPassport(${passport.id})" class="pin-btn text-slate-500 hover:text-indigo-400 transition-colors">
                        <span class="pin-icon">📌</span>
                    </button>
                    <button onclick="window.deletePassport(${passport.id})" class="text-slate-500 hover:text-red-400 transition-colors">
                        🗑
                    </button>
                </div>
            </div>
            ${passport.rank ? `<div class="text-sm text-slate-400">Rank: ${passport.rank}</div>` : ''}
            <button onclick="window.togglePassportLFT(${passport.id})" class="lft-toggle-btn w-full px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white font-semibold transition-colors">
                Set Looking for Team
            </button>
        `;
        
        container.insertBefore(card, container.firstChild);
    };
    
    window.togglePassportLFT = async function(passportId) {
        const button = document.querySelector(`[data-passport-id="${passportId}"] .lft-toggle-btn`);
        const badge = document.querySelector(`[data-passport-id="${passportId}"] .lft-badge`);
        
        if (button) button.disabled = true;
        
        try {
            const result = await togglePassportLFT(passportId);
            const isEnabled = result.looking_for_team;
            
            showToast(isEnabled ? 'Looking for team enabled' : 'Looking for team disabled');
            
            // Update badge in real-time
            if (badge) {
                if (isEnabled) {
                    badge.classList.remove('hidden');
                    badge.textContent = '🔍 Looking for Team';
                } else {
                    badge.classList.add('hidden');
                }
            }
            
            // Update button text
            if (button) {
                button.textContent = isEnabled ? '✓ LFT Active' : 'Set Looking for Team';
                button.classList.toggle('bg-emerald-600', isEnabled);
                button.classList.toggle('bg-slate-700', !isEnabled);
            }
        } catch (error) {
            showToast(error.message || 'Failed to toggle LFT', 'error');
        } finally {
            if (button) button.disabled = false;
        }
    };
    
    window.pinPassport = async function(passportId) {
        const card = document.querySelector(`[data-passport-id="${passportId}"]`);
        const button = card?.querySelector('.pin-btn');
        const pinIcon = card?.querySelector('.pin-icon');
        
        if (button) button.disabled = true;
        
        try {
            const result = await pinPassport(passportId);
            const isPinned = result.is_pinned;
            
            showToast(isPinned ? 'Passport pinned' : 'Passport unpinned');
            
            // Update pin icon in real-time
            if (pinIcon) {
                pinIcon.textContent = isPinned ? '📌' : '📍';
                pinIcon.classList.toggle('text-indigo-400', isPinned);
                pinIcon.classList.toggle('text-slate-500', !isPinned);
            }
            
            // Update button text
            if (button) {
                button.textContent = isPinned ? 'Unpin' : 'Pin';
            }
            
            // Add visual emphasis if pinned
            if (card) {
                card.classList.toggle('ring-2', isPinned);
                card.classList.toggle('ring-indigo-500', isPinned);
            }
        } catch (error) {
            showToast(error.message || 'Failed to pin passport', 'error');
        } finally {
            if (button) button.disabled = false;
        }
    };
    
    window.deletePassport = async function(passportId) {
        if (!confirm('Are you sure you want to delete this game passport?')) return;
        
        const card = document.querySelector(`[data-passport-id="${passportId}"]`);
        
        try {
            // Optimistic UI - fade out card
            if (card) {
                card.style.opacity = '0.5';
                card.style.pointerEvents = 'none';
            }
            
            await deletePassport(passportId);
            showToast('Passport deleted');
            
            // Remove card with animation
            if (card) {
                card.style.transition = 'all 0.3s ease-out';
                card.style.transform = 'scale(0.9)';
                card.style.opacity = '0';
                
                setTimeout(() => {
                    card.remove();
                    
                    // Show empty state if no passports left
                    const container = document.getElementById('passports-container');
                    const remainingCards = container?.querySelectorAll('[data-passport-id]');
                    if (remainingCards?.length === 0) {
                        container.innerHTML = `
                            <div class="text-center py-12">
                                <p class="text-slate-500 text-lg">No game passports yet</p>
                                <p class="text-slate-600 text-sm mt-2">Add your first game to get started</p>
                            </div>
                        `;
                    }
                }, 300);
            }
        } catch (error) {
            // Rollback on failure
            if (card) {
                card.style.opacity = '1';
                card.style.pointerEvents = 'auto';
            }
            showToast(error.message || 'Failed to delete passport', 'error');
        }
    };
    
    window.followUser = async function(username) {
        const followBtn = document.getElementById('followBtn');
        const followerCount = document.getElementById('followerCount');
        
        if (followBtn) {
            followBtn.disabled = true;
            followBtn.textContent = 'Following...';
        }
        
        try {
            await followUser(username);
            showToast('Followed user');
            
            // Update button to unfollow state
            if (followBtn) {
                followBtn.textContent = '✓ Following';
                followBtn.classList.remove('bg-indigo-600', 'hover:bg-indigo-500');
                followBtn.classList.add('bg-slate-700', 'hover:bg-slate-600');
                followBtn.onclick = () => window.unfollowUser(username);
            }
            
            // Increment follower count
            if (followerCount) {
                const current = parseInt(followerCount.textContent) || 0;
                followerCount.textContent = (current + 1).toString();
            }
        } catch (error) {
            showToast(error.message || 'Failed to follow user', 'error');
            if (followBtn) {
                followBtn.textContent = 'Follow';
            }
        } finally {
            if (followBtn) followBtn.disabled = false;
        }
    };
    
    window.unfollowUser = async function(username) {
        const followBtn = document.getElementById('followBtn');
        const followerCount = document.getElementById('followerCount');
        
        if (followBtn) {
            followBtn.disabled = true;
            followBtn.textContent = 'Unfollowing...';
        }
        
        try {
            await unfollowUser(username);
            showToast('Unfollowed user');
            
            // Update button to follow state
            if (followBtn) {
                followBtn.textContent = 'Follow';
                followBtn.classList.remove('bg-slate-700', 'hover:bg-slate-600');
                followBtn.classList.add('bg-indigo-600', 'hover:bg-indigo-500');
                followBtn.onclick = () => window.followUser(username);
            }
            
            // Decrement follower count
            if (followerCount) {
                const current = parseInt(followerCount.textContent) || 0;
                followerCount.textContent = Math.max(0, current - 1).toString();
            }
        } catch (error) {
            showToast(error.message || 'Failed to unfollow user', 'error');
            if (followBtn) {
                followBtn.textContent = '✓ Following';
            }
        } finally {
            if (followBtn) followBtn.disabled = false;
        }
    };
    
    // ========== UTILITIES ==========
    
    function showToast(message, type = 'success') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `px-6 py-4 rounded-xl text-white font-semibold shadow-2xl transform transition-all duration-300 ${
            type === 'error' ? 'bg-red-600' : 'bg-emerald-600'
        }`;
        toast.textContent = message;
        toast.style.animation = 'slideInUp 0.3s ease-out';
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutDown 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    window.copyToClipboard = function(text) {
        if (!navigator.clipboard) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            
            try {
                document.execCommand('copy');
                showToast('Copied to clipboard!');
            } catch (err) {
                showToast('Failed to copy', 'error');
            }
            
            document.body.removeChild(textarea);
            return;
        }
        
        navigator.clipboard.writeText(text)
            .then(() => showToast('Copied to clipboard!'))
            .catch(() => showToast('Failed to copy', 'error'));
    };
    
    window.shareProfile = function() {
        const url = window.location.href;
        const title = document.querySelector('h1').textContent;
        
        if (navigator.share) {
            navigator.share({
                title: title,
                url: url
            }).catch(err => console.log('Share cancelled'));
        } else {
            copyToClipboard(url);
        }
    };
    
    function smoothScrollTo(targetId) {
        const target = document.getElementById(targetId);
        if (!target) return;
        
        const navHeight = 80;
        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight;
        
        window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
        });
    }
    
    // ========== DASHBOARD NAVIGATION ==========
    
    function initDashboardNav() {
        const navChips = document.querySelectorAll('.nav-chip');
        
        navChips.forEach(chip => {
            chip.addEventListener('click', function(e) {
                e.preventDefault();
                
                navChips.forEach(c => c.classList.remove('active'));
                this.classList.add('active');
                
                const targetId = this.getAttribute('href').substring(1);
                smoothScrollTo(targetId);
            });
        });
        
        // Intersection Observer for auto-highlighting
        const sections = Array.from(navChips).map(chip => {
            const targetId = chip.getAttribute('href').substring(1);
            return document.getElementById(targetId);
        }).filter(Boolean);
        
        const observerOptions = {
            root: null,
            rootMargin: '-100px 0px -66%',
            threshold: 0
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const activeChip = document.querySelector(`.nav-chip[href="#${entry.target.id}"]`);
                    if (activeChip) {
                        navChips.forEach(c => c.classList.remove('active'));
                        activeChip.classList.add('active');
                    }
                }
            });
        }, observerOptions);
        
        sections.forEach(section => {
            if (section) observer.observe(section);
        });
    }
    
    // ========== COLLAPSIBLE SECTIONS ==========
    
    function initCollapsible() {
        const toggleBtn = document.getElementById('toggleMoreGames');
        const content = document.getElementById('moreGamesContent');
        const icon = document.getElementById('expandIcon');
        
        if (!toggleBtn || !content) return;
        
        toggleBtn.addEventListener('click', function() {
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            
            this.setAttribute('aria-expanded', !isExpanded);
            content.setAttribute('aria-hidden', isExpanded);
            content.classList.toggle('expanded');
            
            if (icon) {
                icon.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(180deg)';
            }
        });
    }
    
    // ========== URL HASH SUPPORT ==========
    
    function handleUrlHash() {
        const hash = window.location.hash;
        if (hash && hash.length > 1) {
            const targetId = hash.substring(1);
            
            setTimeout(() => {
                smoothScrollTo(targetId);
                
                const activeChip = document.querySelector(`.nav-chip[href="${hash}"]`);
                if (activeChip) {
                    document.querySelectorAll('.nav-chip').forEach(c => c.classList.remove('active'));
                    activeChip.classList.add('active');
                }
            }, 300);
        }
    }
    
    // ========== KEYBOARD SHORTCUTS ==========
    
    function initKeyboardShortcuts() {
        const shortcuts = {
            '1': 'stats',
            '2': 'passports',
            '3': 'teams',
            '4': 'tournaments',
            '5': 'economy',
            '6': 'shop',
            '7': 'activity',
            '8': 'about'
        };
        
        document.addEventListener('keydown', function(e) {
            if (e.target.tagName === 'INPUT' || 
                e.target.tagName === 'TEXTAREA' || 
                e.target.isContentEditable) {
                return;
            }
            
            if (e.altKey && shortcuts[e.key]) {
                e.preventDefault();
                smoothScrollTo(shortcuts[e.key]);
                
                const chip = document.querySelector(`.nav-chip[href="#${shortcuts[e.key]}"]`);
                if (chip) {
                    document.querySelectorAll('.nav-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                }
            }
        });
    }
    
    // ========== INITIALIZATION ==========
    
    function init() {
        const bentoCard = document.querySelector('.bento-card');
        if (!bentoCard) return;
        
        console.log('Initializing Profile v3 (UP-UI-REBIRTH-01)...');
        
        try {
            initDashboardNav();
            initCollapsible();
            handleUrlHash();
            initKeyboardShortcuts();
            
            console.log('Profile initialized successfully');
        } catch (error) {
            console.error('Error initializing Profile:', error);
        }
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    window.addEventListener('hashchange', handleUrlHash);
    
})();

// CSS Animations
const style = document.createElement('style');
style.textContent = `
@keyframes slideInUp {
    from { transform: translateY(100%); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}

@keyframes slideOutDown {
    from { transform: translateY(0); opacity: 1; }
    to { transform: translateY(100%); opacity: 0; }
}
`;
document.head.appendChild(style);
