// DeltaCrown Profile JavaScript
// Auto-extracted from public_profile.html
// Phase 3.8.3 - DOM Safety: All queries use safe wrappers, defensive initialization
// Build: PROFILE_BUILD_2026-01-09_PHASE3.8.3_DOM_SAFETY
window.__PROFILE_BUILD__ = "PROFILE_BUILD_2026-01-09_PHASE3.8.3_DOM_SAFETY";
console.log("[PROFILE] Build loaded:", window.__PROFILE_BUILD__);

// ============================================================================
// GLOBAL PROFILE CONTEXT (Server-Rendered)
// ============================================================================
const DEBUG_PROFILE = false; // Set to true for debugging
const IS_VISITOR = !IS_AUTHENTICATED || !IS_OWN_PROFILE; // Phase 3.7: Visitor mode flag

// ============================================================================
// SAFETY UTILITIES (Phase 3.7)
// ============================================================================

/**
 * Safe DOM query - never throws errors on missing elements
 */
function safeQuery(selector, scope = document) {
    try {
        return scope.querySelector(selector);
    } catch (err) {
        debugLog('Query failed', { selector, err: err.message });
        return null;
    }
}

/**
 * Safe element by ID - never throws errors
 */
function safeGetById(id) {
    try {
        return document.getElementById(id);
    } catch (err) {
        debugLog('getElementById failed', { id, err: err.message });
        return null;
    }
}

/**
 * Safe querySelector within an element - never throws errors
 * Phase 3.8.3: For safeQueryIn(element, ) patterns
 */
function safeQueryIn(element, selector) {
    if (!element) {
        debugLog('safeQueryIn: element is null/undefined', { selector });
        return null;
    }
    try {
        return safeQueryIn(element, selector);
    } catch (err) {
        debugLog('safeQueryIn failed', { selector, err: err.message });
        return null;
    }
}

/**
 * Safe fetch with error handling, JSON parsing, and automatic CSRF
 * Phase 3.8: Enhanced with CSRF injection for mutations
 */
async function safeFetch(url, options = {}) {
    try {
        // Auto-inject CSRF for mutations
        const method = (options.method || 'GET').toUpperCase();
        const isMutation = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);
        
        const enhancedOptions = { ...options };
        if (isMutation && !enhancedOptions.headers?.['X-CSRFToken']) {
            enhancedOptions.headers = {
                ...enhancedOptions.headers,
                'X-CSRFToken': getCSRFToken()
            };
        }
        
        const res = await fetch(url, enhancedOptions);
        if (!res.ok) {
            const data = await res.json().catch(() => ({ error: 'Network error' }));
            debugLog('HTTP error', { status: res.status, url, data });
            throw { status: res.status, data };
        }
        return await res.json();
    } catch (err) {
        debugLog('Fetch failed', { url, err: err.message || err });
        // Show user-friendly message
        const errorMsg = err.data?.error || err.message || 'Something went wrong. Please try again.';
        showToast(errorMsg, 'error');
        return null;
    }
}

/**
 * Owner-only action guard - prevents visitors from triggering mutations
 * Phase 3.8: Enhanced with toast notification
 */
function requireOwner(actionName = 'this action') {
    if (IS_VISITOR) {
        debugLog('Blocked action for visitor', actionName);
        showToast('Only the profile owner can perform this action', 'error');
        return false;
    }
    return true;
}

/**
 * Debug logging helper - only logs when DEBUG_PROFILE is true
 * Phase 3.8: Conditional logging for production cleanliness
 */
function debugLog(...args) {
    if (DEBUG_PROFILE) {
        console.log('[PROFILE DEBUG]', ...args);
    }
}

/**
 * Toast notification helper (graceful fallback to alert)
 * Phase 3.8: Enhanced for better UX
 */
function showToast(message, type = 'info') {
    debugLog(`Toast ${type}:`, message);
    
    // For now, use alert for errors (can be upgraded to toast library later)
    if (type === 'error' && typeof alert !== 'undefined') {
        alert(message);
    } else if (type === 'success' && typeof alert !== 'undefined') {
        alert(message);
    }
    // info type: silent for now (could show as notification badge)
}

// ============================================================================
// URL HELPER FOR DYNAMIC IDS
// ============================================================================
/**
 * Safely replace placeholder ID in Django-generated URL with actual ID.
 * Handles trailing slashes and various URL formats.
 * 
 * @param {string} urlTemplate - URL with placeholder ID (e.g., /api/bounties/0/accept/)
 * @param {number|string} actualId - The real ID to substitute
 * @returns {string} URL with actual ID
 * 
 * Examples:
 *   urlWithId('/api/bounties/0/accept/', 123) => '/api/bounties/123/accept/'
 *   urlWithId('/api/hardware/0/', 456) => '/api/hardware/456/'
 */
function urlWithId(urlTemplate, actualId) {
    // Replace /0/ or /0 at end with actual ID, preserving trailing slash
    return urlTemplate.replace(/\/0(\/?)$/, `/${actualId}$1`);
}

// ============================================================================
// CSRF TOKEN HELPER
// ============================================================================
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

function getCSRFToken() {
    // Try cookie first
    let token = getCookie('csrftoken');
    
    // Fallback to meta tag or hidden input
    if (!token) {
        const meta = safeQuery('meta[name="csrf-token"]');
        if (meta) token = meta.getAttribute('content');
    }
    
    if (!token) {
        const input = safeQuery('[name=csrfmiddlewaretoken]');
        if (input) token = input.value;
    }
    
    if (!token && DEBUG_PROFILE) {
        console.error('CSRF token not found!');
    }
    
    return token;
}

// ============================================================================
// DEBUG LOGGER
// ============================================================================
function debugLog(message, data) {
    if (DEBUG_PROFILE) {
        console.log(`[Profile Debug] ${message}`, data || '');
    }
}

// ============================================================================
// TAB SWITCHING SYSTEM (PHASE 3.7.3 - Production-Ready)
// ============================================================================

/**
 * Production-ready tab switching with DOM-based discovery
/**
 * switchTab - Switches between profile tabs
 * Phase 3.8.2: Event-driven, works with data-tab-button/data-tab-panel attributes
 * No assumptions about tab names - discovers from actual DOM
 */
function switchTab(tabId) {
    console.log('[TAB] Switching to:', tabId);
    
    // Hide all tab contents
    const allTabs = document.querySelectorAll('.tab-content');
    allTabs.forEach(el => {
        el.classList.remove('active');
    });

    // Reset all tab buttons
    const allButtons = document.querySelectorAll('.z-tab-btn, [data-tab-button]');
    allButtons.forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected content
    const selectedContent = safeGetById('tab-' + tabId);
    if (selectedContent) {
        selectedContent.classList.add('active');
        console.log('[TAB] Activated content:', 'tab-' + tabId);
    } else {
        console.warn('[TAB] Content not found for:', 'tab-' + tabId);
    }

    // Highlight active button - check data-tab-button attribute (Phase 3.8.2)
    allButtons.forEach(btn => {
        const tabKey = btn.getAttribute('data-tab-button');
        if (tabKey === tabId) {
            btn.classList.add('active');
            console.log('[TAB] Activated button for:', tabId);
        }
    });
    
    // Update URL hash without page reload
    if (history.pushState) {
        history.pushState(null, null, '#' + tabId);
    }
}

// PHASE-3.7.1 FIX: Expose switchTab globally for backward compatibility
window.switchTab = switchTab;

// PHASE-3.8.2: Event delegation for tab switching
document.addEventListener('DOMContentLoaded', function() {
    console.log('[TAB] Phase 3.8.2 - Event-driven tabs initializing...');
    
    // Discover all tabs in DOM
    const allTabs = document.querySelectorAll('.tab-content');
    const allButtons = document.querySelectorAll('[data-tab-button]');
    console.log(`[TAB] Found ${allTabs.length} tab contents, ${allButtons.length} tab buttons`);
    
    // Log discovered tabs for debugging
    allTabs.forEach((tab, idx) => {
        console.log(`[TAB] Content ${idx + 1}:`, tab.id);
    });
    
    // ===== EVENT DELEGATION: Single click handler for all tab triggers =====
    document.addEventListener('click', function(e) {
        // Find the closest element with data-tab-button (supports nested elements)
        const tabTrigger = e.target.closest('[data-tab-button]');
        
        if (tabTrigger) {
            e.preventDefault();
            const tabKey = tabTrigger.getAttribute('data-tab-button');
            if (tabKey) {
                debugLog('Tab clicked via delegation', { tabKey });
                switchTab(tabKey);
            }
        }
    });
    
    // ===== KEYBOARD ACCESSIBILITY: Enter/Space on focusable tab triggers =====
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
            const tabTrigger = e.target.closest('[data-tab-button]');
            
            if (tabTrigger && (tabTrigger.getAttribute('role') === 'button' || tabTrigger.tagName === 'BUTTON')) {
                e.preventDefault();
                const tabKey = tabTrigger.getAttribute('data-tab-button');
                if (tabKey) {
                    debugLog('Tab activated via keyboard', { tabKey, key: e.key });
                    switchTab(tabKey);
                }
            }
        }
    });
    
    // ===== HASH NAVIGATION: Open tab from URL hash =====
    const hash = window.location.hash.slice(1); // Remove the '#'
    if (hash) {
        console.log('[TAB] Hash detected:', hash);
        switchTab(hash);
    } else {
        console.log('[TAB] No hash, defaulting to overview');
        switchTab('overview');
    }
    
    console.log('[TAB] Event delegation active - tabs work without inline onclick');
});

// Clipboard copy function for crosshair codes (UP-PHASE-2C2)
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        // Show success feedback
        const btn = event.target.closest('button');
        const originalHTML = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check mr-2"></i> Copied!';
        btn.classList.add('bg-green-500/20', 'border-green-500/30');
        
        setTimeout(function() {
            btn.innerHTML = originalHTML;
            btn.classList.remove('bg-green-500/20', 'border-green-500/30');
        }, 2000);
    }).catch(function(err) {
        console.error('Failed to copy: ', err);
        alert('Failed to copy to clipboard. Please copy manually.');
    });
}

// About Modal Functions
function openAboutModal() {
    if (!requireOwner('openAboutModal')) return;
    
    const modal = safeGetById('aboutModal');
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Update char counter
        const bioInput = safeGetById('bioInput');
        if (bioInput) {
            updateCharCount();
            bioInput.addEventListener('input', updateCharCount);
        }
    }
}

function closeAboutModal() {
    const modal = safeGetById('aboutModal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }
}

function updateCharCount() {
    const bioInput = safeGetById('bioInput');
    const charCount = safeGetById('bioCharCount');
    if (bioInput && charCount) {
        const count = bioInput.value.length;
        charCount.textContent = `${count} / 500`;
        if (count > 450) {
            charCount.classList.add('text-[var(--z-gold)]');
        } else {
            charCount.classList.remove('text-[var(--z-gold)]');
        }
    }
}

// Handle About form submission
document.addEventListener('DOMContentLoaded', function() {
    const aboutForm = safeGetById('aboutForm');
    if (aboutForm) {
        aboutForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            if (!requireOwner('submitAboutForm')) return;
            
            const bio = safeGetById('bioInput')?.value.trim() || '';
            const pronouns = safeGetById('pronounsInput')?.value.trim() || '';
            const country = safeGetById('countryInput')?.value.trim() || '';
            const city = safeGetById('cityInput')?.value.trim() || '';
            
            const data = await safeFetch('/actions/update-bio/', {
                method: 'POST',
                body: JSON.stringify({
                    bio: bio,
                    pronouns: pronouns,
                    country: country,
                    city: city
                })
            });
            
            if (data && data.success) {
                closeAboutModal();
                showToast('Profile updated successfully', 'success');
                location.reload(); // Refresh to show updated info
            }
        });
    }
});

// Game Passports Modal Functions
let availableGames = [];

async function openGamePassportsModal() {
    if (!requireOwner('openGamePassportsModal')) return;
    
    const modal = safeGetById('gamePassportsModal');
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Load available games and passports
        await loadAvailableGames();
        await loadGamePassports();
    }
}

function closeGamePassportsModal() {
    const modal = safeGetById('gamePassportsModal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
        const form = safeGetById('addPassportForm');
        if (form) form.reset();
    }
}

async function loadAvailableGames() {
    try {
        const data = await response.json();
        
        if (data.success && data.games) {
            availableGames = data.games;
            const select = safeGetById('passportGameSelect');
            if (!select) return;
            select.innerHTML = '<option value="">Select a game...</option>';
            
            data.games.forEach(game => {
                const option = document.createElement('option');
                option.value = game.id;
                option.textContent = `${game.icon} ${game.name}`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading games:', error);
    }
}

async function loadGamePassports() {
    try {
        const data = await response.json();
        
        const container = safeGetById('passportsList');
        if (!container) return;
        
        if (!data.success || !data.passports || data.passports.length === 0) {
            container.innerHTML = '<div class="text-center text-gray-500 py-8">No game IDs yet. Add one above!</div>';
            return;
        }
        
        container.innerHTML = '';
        data.passports.forEach(passport => {
            const passportEl = createPassportElement(passport);
            container.appendChild(passportEl);
        });
    } catch (error) {
        console.error('Error loading passports:', error);
        safeGetById('passportsList').innerHTML = '<div class="text-center text-red-500 py-8">Error loading passports</div>';
    }
}

function createPassportElement(passport) {
    const div = document.createElement('div');
    div.className = 'bg-white/5 border border-white/10 rounded-lg p-4 flex justify-between items-center hover:bg-white/10 transition';
    
    const infoDiv = document.createElement('div');
    infoDiv.className = 'flex-1';
    
    const titleRow = document.createElement('div');
    titleRow.className = 'flex items-center gap-2 mb-1';
    
    const gameIcon = document.createElement('span');
    gameIcon.textContent = passport.game.icon || '🎮';
    gameIcon.className = 'text-xl';
    
    const gameName = document.createElement('span');
    gameName.textContent = passport.game.name;
    gameName.className = 'font-bold text-white';
    
    if (passport.pinned) {
        const pinnedBadge = document.createElement('span');
        pinnedBadge.textContent = 'PINNED';
        pinnedBadge.className = 'text-[9px] bg-[var(--z-cyan)] text-black px-1.5 rounded font-bold uppercase';
        titleRow.appendChild(gameIcon);
        titleRow.appendChild(gameName);
        titleRow.appendChild(pinnedBadge);
    } else {
        titleRow.appendChild(gameIcon);
        titleRow.appendChild(gameName);
    }
    
    const ignRow = document.createElement('div');
    ignRow.className = 'text-sm font-mono text-gray-300';
    ignRow.textContent = passport.ign;
    
    if (passport.region || passport.rank) {
        const metaRow = document.createElement('div');
        metaRow.className = 'text-xs text-gray-500 mt-1';
        const parts = [];
        if (passport.region) parts.push(`Region: ${passport.region}`);
        if (passport.rank) parts.push(`Rank: ${passport.rank}`);
        metaRow.textContent = parts.join(' • ');
        infoDiv.appendChild(titleRow);
        infoDiv.appendChild(ignRow);
        infoDiv.appendChild(metaRow);
    } else {
        infoDiv.appendChild(titleRow);
        infoDiv.appendChild(ignRow);
    }
    
    const deleteBtn = document.createElement('button');
    deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
    deleteBtn.className = 'px-3 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition';
    deleteBtn.onclick = () => deletePassport(passport.id, passport.game.name);
    
    div.appendChild(infoDiv);
    div.appendChild(deleteBtn);
    
    return div;
}

async function deletePassport(passportId, gameName) {
    if (!requireOwner('deletePassport')) return;
    if (!confirm(`Delete ${gameName} game ID? This cannot be undone.`)) {
        return;
    }
    
    const data = await safeFetch(`/api/profile/${PROFILE_USERNAME}/game-passports/${passportId}/`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    
    if (data && data.success) {
        await loadGamePassports();
        setTimeout(() => location.reload(), 500);
    }
}

// Handle Add Passport form submission
document.addEventListener('DOMContentLoaded', function() {
    const addPassportForm = safeGetById('addPassportForm');
    if (addPassportForm) {
        addPassportForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!requireOwner('addPassport')) return;
            
            const gameId = safeGetById('passportGameSelect').value;
            const ign = safeGetById('passportIgnInput').value.trim();
            const region = safeGetById('passportRegionInput').value.trim() || null;
            const rank = safeGetById('passportRankInput').value.trim() || null;
            
            if (!gameId || !ign) {
                alert('Please select a game and enter your IGN');
                return;
            }
            
            const data = await safeFetch('/api/profile/add-passport/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    game_id: parseInt(gameId),
                    ign: ign,
                    region: region,
                    rank: rank,
                    pinned: false,
                    passport_data: {}
                })
            });
            
            if (data && data.success) {
                addPassportForm.reset();
                await loadGamePassports();
                setTimeout(() => location.reload(), 500);
            }
        });
    }
});

// Video Modal Functions
function openVideoModal(embedUrl, title, originalUrl) {
    const modal = safeGetById('videoModal');
    const iframe = safeGetById('videoModalIframe');
    const fallback = safeGetById('videoModalFallback');
    const externalLink = safeGetById('videoModalExternalLink');
    const titleEl = safeGetById('videoModalTitle');
    
    if (!modal || !iframe || !fallback || !titleEl) {
        debugLog('Video modal elements missing');
        return;
    }
    
    titleEl.textContent = title;
    
    const isFacebook = embedUrl && embedUrl.includes('facebook.com');

    // If embed URL is missing/invalid or Facebook blocks playback, show fallback
    if (!embedUrl || embedUrl.trim() === '' || isFacebook) {
        iframe.style.display = 'none';
        fallback.classList.remove('hidden');
        const linkTarget = originalUrl || embedUrl;
        if (linkTarget) {
            externalLink.href = linkTarget;
            externalLink.textContent = 'Open in Facebook';
        }
    } else {
        iframe.style.display = 'block';
        fallback.classList.add('hidden');
        iframe.src = embedUrl;
    }
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeVideoModal() {
    const modal = safeGetById('videoModal');
    const iframe = safeGetById('videoModalIframe');
    const fallback = safeGetById('videoModalFallback');
    
    if (!modal || !iframe || !fallback) return;
    
    iframe.src = '';  // Stop video playback
    iframe.style.display = 'block';
    fallback.classList.add('hidden');
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// Edit Highlights Modal Functions
function openEditHighlightsModal() {
    if (!requireOwner('openEditHighlightsModal')) return;
    
    const modal = safeGetById('editHighlightsModal');
    if (!modal) return;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeEditHighlightsModal() {
    const modal = safeGetById('editHighlightsModal');
    if (!modal) return;
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// Close modals on ESC key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeAboutModal();
        closeGamePassportsModal();
        closeVideoModal();
        closeEditHighlightsModal();
        closeFollowersModal();
        closeFollowingModal();
        closeSocialLinksModal();
    }
});

// Close modals on background click
safeGetById('aboutModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'aboutModal') {
        closeAboutModal();
    }
});

safeGetById('gamePassportsModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'gamePassportsModal') {
        closeGamePassportsModal();
    }
});

safeGetById('videoModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'videoModal') {
        closeVideoModal();
    }
});

safeGetById('editHighlightsModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'editHighlightsModal') {
        closeEditHighlightsModal();
    }
});

safeGetById('followersModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'followersModal') {
        closeFollowersModal();
    }
});

safeGetById('followingModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'followingModal') {
        closeFollowingModal();
    }
});

safeGetById('socialLinksModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'socialLinksModal') {
        closeSocialLinksModal();
    }
});

// Initialize Overview tab on page load
document.addEventListener('DOMContentLoaded', () => {
    switchTab('overview');
});

// ============================================================================
// UP-PHASE2D: Interactive Owner Flows
// ============================================================================

// Create Bounty Modal
function openCreateBountyModal() {
    if (!requireOwner('openCreateBountyModal')) return;
    
    const modal = safeGetById('createBountyModal');
    if (!modal) return;
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeCreateBountyModal() {
    const modal = safeGetById('createBountyModal');
    if (!modal) return;
    
    modal.classList.add('hidden');
    document.body.style.overflow = '';
    safeGetById('createBountyForm').reset();
    safeGetById('createBountyError').classList.add('hidden');
}

async function submitBounty() {
    if (!requireOwner('submitBounty')) return;
    
    const form = safeGetById('createBountyForm');
    const errorDiv = safeGetById('createBountyError');
    const submitBtn = safeGetById('submitBountyBtn');
    
    errorDiv.classList.add('hidden');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Creating...';
    
    const data = {
        title: form.title.value,
        game_id: form.game.value,
        description: form.description.value,
        stake_amount: parseInt(form.stake_amount.value),
        expires_in_hours: parseInt(form.expires_in_hours.value),
    };
    
    const result = await safeFetch('/api/bounties/create/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    });
    
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fa-solid fa-plus mr-2"></i> Create Bounty';
    
    if (result && result.success) {
        alert(`Bounty created! ${result.stake_amount} DC locked in escrow.`);
        closeCreateBountyModal();
        location.reload();
    } else if (result) {
        errorDiv.textContent = result.error || 'Failed to create bounty';
        errorDiv.classList.remove('hidden');
    }
}

// Accept Bounty
async function acceptBounty(bountyId, url) {
    if (!requireOwner('acceptBounty')) return;
    if (!confirm('Accept this bounty challenge?')) return;
    
    const btn = event.target.closest('button');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Accepting...';
    
    debugLog('Accept bounty', { bountyId, url });
    
    const data = await safeFetch(url, {
        method: 'POST'
    });
    
    if (data && data.success) {
        alert(data.message);
        location.reload();
    } else {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-handshake mr-2"></i> Accept';
    }
}

// ============================================================================
// LOADOUT EDIT MODAL (Phase 2F Part 5C)
// ============================================================================

let currentLoadoutTab = 'hardware';
let loadoutAvailableGames = [];

// Tab Switching
function switchLoadoutTab(tabId) {
    currentLoadoutTab = tabId;
    
    // Update tab buttons
    safeGetById('loadoutTabHardware').classList.toggle('text-white', tabId === 'hardware');
    safeGetById('loadoutTabHardware').classList.toggle('text-gray-400', tabId !== 'hardware');
    safeGetById('loadoutTabHardware').classList.toggle('border-[var(--z-cyan)]', tabId === 'hardware');
    safeGetById('loadoutTabHardware').classList.toggle('border-transparent', tabId !== 'hardware');
    
    safeGetById('loadoutTabGameConfigs').classList.toggle('text-white', tabId === 'gameconfigs');
    safeGetById('loadoutTabGameConfigs').classList.toggle('text-gray-400', tabId !== 'gameconfigs');
    safeGetById('loadoutTabGameConfigs').classList.toggle('border-[var(--z-cyan)]', tabId === 'gameconfigs');
    safeGetById('loadoutTabGameConfigs').classList.toggle('border-transparent', tabId !== 'gameconfigs');
    
    // Update content visibility
    safeGetById('loadoutContentHardware').classList.toggle('hidden', tabId !== 'hardware');
    safeGetById('loadoutContentGameConfigs').classList.toggle('hidden', tabId !== 'gameconfigs');
}

// Open Modal
async function openEditLoadoutModal() {
    if (!requireOwner('openEditLoadoutModal')) return;
    
    const modal = safeGetById('editLoadoutModal');
    if (!modal) return;
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Load available games for configs
    await loadAvailableGamesForConfigs();
    
    // Load current data
    await loadHardwareList();
    await loadGameConfigList();
}

// Close Modal
function closeEditLoadoutModal() {
    const modal = safeGetById('editLoadoutModal');
    if (!modal) return;
    
    modal.classList.add('hidden');
    document.body.style.overflow = '';
    resetHardwareForm();
    resetGameConfigForm();
}

// ============================================================================
// HARDWARE MANAGEMENT
// ============================================================================

// Load Hardware List
async function loadHardwareList() {
    const container = safeGetById('hardwareList');
    
    // Get hardware from JSON script tag
    const hardware = JSON.parse(safeGetById('hardwareData').textContent);
    
    container.innerHTML = '';
    
    const categories = {
        'MOUSE': { icon: 'fa-computer-mouse', label: 'Mouse' },
        'KEYBOARD': { icon: 'fa-keyboard', label: 'Keyboard' },
        'HEADSET': { icon: 'fa-headphones', label: 'Headset' },
        'MONITOR': { icon: 'fa-tv', label: 'Monitor' },
        'MOUSEPAD': { icon: 'fa-square', label: 'Mousepad' }
    };
    
    Object.entries(categories).forEach(([category, meta]) => {
        const item = hardware[category];
        
        if (item) {
            // Existing hardware
            const div = document.createElement('div');
            div.className = 'flex items-center justify-between bg-white/5 border border-white/10 rounded-lg p-3 hover:border-[var(--z-cyan)]/30 transition';
            div.innerHTML = `
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-[var(--z-cyan)]/10 flex items-center justify-center text-[var(--z-cyan)]">
                        <i class="fa-solid ${meta.icon}"></i>
                    </div>
                    <div>
                        <div class="text-xs text-gray-400">${meta.label}</div>
                        <div class="text-sm text-white font-bold">${item.brand} ${item.model}</div>
                        ${item.specs && Object.keys(item.specs).length > 0 ? 
                            `<div class="text-xs text-gray-500 mt-1">${JSON.stringify(item.specs)}</div>` : ''}
                    </div>
                </div>
                <div class="flex gap-2">
                    <button onclick='editHardware(${JSON.stringify(item).replace(/'/g, "&apos;")})' 
                        class="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded text-xs transition">
                        <i class="fa-solid fa-pen"></i>
                    </button>
                    <button onclick="deleteHardware(${item.id}, '${category}')" 
                        class="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded text-xs transition">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            `;
            container.appendChild(div);
        } else {
            // Empty slot
            const div = document.createElement('div');
            div.className = 'flex items-center justify-between bg-white/5 border border-white/10 border-dashed rounded-lg p-3 opacity-50';
            div.innerHTML = `
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center text-gray-600">
                        <i class="fa-solid ${meta.icon}"></i>
                    </div>
                    <div class="text-sm text-gray-500">No ${meta.label.toLowerCase()} added</div>
                </div>
            `;
            container.appendChild(div);
        }
    });
}

// Hardware Form Submit
safeGetById('hardwareForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!requireOwner('saveHardware')) return;
    
    const id = safeGetById('hardwareId').value;
    const category = safeGetById('hardwareCategory').value;
    const brand = safeGetById('hardwareBrand').value.trim();
    const model = safeGetById('hardwareModel').value.trim();
    const specsRaw = safeGetById('hardwareSpecs').value.trim();
    const isPublic = safeGetById('hardwareIsPublic').checked;
    
    // Parse specs JSON
    let specs = {};
    if (specsRaw) {
        try {
            specs = JSON.parse(specsRaw);
        } catch (err) {
            alert('Invalid JSON in specs field. Use format: {"key": "value"}');
            return;
        }
    }
    
    // Build payload
    const payload = {
        category,
        brand,
        model,
        specs,
        is_public: isPublic
    };
    
    if (id) {
        payload.id = parseInt(id);
    }
    
    // Submit
    const btn = e.safeQueryIn(target, 'button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i>Saving...';
    
    try {
        debugLog('Save hardware', payload);
        const data = await safeFetch('/api/profile/hardware/save/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-check mr-2"></i>Save Hardware';
        
        if (data && data.success) {
            alert(data.message || 'Hardware saved successfully!');
            resetHardwareForm();
            window.location.reload();
        }
    } catch (err) {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-check mr-2"></i>Save Hardware';
        alert('Network error: ' + err.message);
    }
});

// Edit Hardware
function editHardware(item) {
    safeGetById('hardwareId').value = item.id;
    safeGetById('hardwareCategory').value = item.category;
    safeGetById('hardwareBrand').value = item.brand;
    safeGetById('hardwareModel').value = item.model;
    safeGetById('hardwareSpecs').value = item.specs && Object.keys(item.specs).length > 0 
        ? JSON.stringify(item.specs, null, 2) : '';
    safeGetById('hardwareIsPublic').checked = item.is_public;
    
    safeGetById('hardwareFormTitle').textContent = 'Edit Hardware';
    
    // Scroll to form
    safeGetById('hardwareForm').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Delete Hardware
async function deleteHardware(id, category) {
    if (!requireOwner('deleteHardware')) return;
    if (!confirm(`Delete this ${category.toLowerCase()}? This cannot be undone.`)) return;
    
    const url = `/api/profile/hardware/${id}/delete/`;
    debugLog('Delete hardware', { id, url });
    
    const data = await safeFetch(url, { method: 'DELETE' });
    if (data && data.success) {
        alert(data.message || 'Hardware deleted successfully!');
        window.location.reload();
    }
}

// Reset Hardware Form
function resetHardwareForm() {
    safeGetById('hardwareForm').reset();
    safeGetById('hardwareId').value = '';
    safeGetById('hardwareFormTitle').textContent = 'Add Hardware';
    safeGetById('hardwareIsPublic').checked = true;
}

// ============================================================================
// GAME CONFIG MANAGEMENT
// ============================================================================

// Load Available Games
async function loadAvailableGamesForConfigs() {
    try {
        const data = await response.json();
        
        if (data.games) {
            loadoutAvailableGames = data.games;
            
            const select = safeGetById('gameConfigGame');
            select.innerHTML = '<option value="">Select Game...</option>';
            
            data.games.forEach(game => {
                const option = document.createElement('option');
                option.value = game.id;
                option.textContent = game.name;
                select.appendChild(option);
            });
        }
    } catch (err) {
        console.error('Failed to load games:', err);
    }
}

// Load Game Config List
async function loadGameConfigList() {
    const container = safeGetById('gameConfigList');
    
    // Get configs from JSON script tag
    const configs = JSON.parse(safeGetById('gameConfigsData').textContent);
    
    container.innerHTML = '';
    
    if (configs.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 py-8 border border-dashed border-white/10 rounded-lg">No game configs added yet</div>';
        return;
    }
    
    configs.forEach(config => {
        const div = document.createElement('div');
        div.className = 'flex items-center justify-between bg-white/5 border border-white/10 rounded-lg p-3 hover:border-[var(--z-cyan)]/30 transition';
        
        const dpi = config.settings?.dpi || config.dpi || '—';
        const sens = config.settings?.sensitivity || config.sensitivity || '—';
        const res = config.settings?.resolution || config.resolution || '—';
        
        div.innerHTML = `
            <div class="flex-1">
                <div class="text-sm text-white font-bold mb-1">${config.game}</div>
                <div class="flex gap-4 text-xs text-gray-400">
                    <span><i class="fa-solid fa-crosshairs mr-1"></i>DPI: ${dpi}</span>
                    <span><i class="fa-solid fa-sliders mr-1"></i>Sens: ${sens}</span>
                    <span><i class="fa-solid fa-tv mr-1"></i>${res}</span>
                </div>
                ${config.notes ? `<div class="text-xs text-gray-500 mt-1">${config.notes}</div>` : ''}
            </div>
            <div class="flex gap-2">
                <button onclick='editGameConfig(${JSON.stringify(config).replace(/'/g, "&apos;")})' 
                    class="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white rounded text-xs transition">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button onclick="deleteGameConfig(${config.id}, '${config.game}')" 
                    class="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded text-xs transition">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `;
        container.appendChild(div);
    });
}

// Game Config Form Submit
safeGetById('gameConfigForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!requireOwner('saveGameConfig')) return;
    
    const id = safeGetById('gameConfigId').value;
    const gameId = safeGetById('gameConfigGame').value;
    const dpi = safeGetById('gameConfigDPI').value.trim();
    const sens = safeGetById('gameConfigSens').value.trim();
    const res = safeGetById('gameConfigRes').value.trim();
    const settingsRaw = safeGetById('gameConfigSettings').value.trim();
    const notes = safeGetById('gameConfigNotes').value.trim();
    const isPublic = safeGetById('gameConfigIsPublic').checked;
    
    // Build settings object
    let settings = {};
    
    if (dpi) settings.dpi = parseInt(dpi);
    if (sens) settings.sensitivity = parseFloat(sens);
    if (res) settings.resolution = res;
    
    // Merge with additional settings JSON
    if (settingsRaw) {
        try {
            const additionalSettings = JSON.parse(settingsRaw);
            settings = { ...settings, ...additionalSettings };
        } catch (err) {
            alert('Invalid JSON in settings field. Use format: {"key": "value"}');
            return;
        }
    }
    
    // Build payload
    const payload = {
        game_id: parseInt(gameId),
        settings,
        notes,
        is_public: isPublic
    };
    
    if (id) {
        payload.id = parseInt(id);
    }
    
    // Submit
    const btn = e.safeQueryIn(target, 'button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i>Saving...';
    
    debugLog('Save game config', payload);
    const data = await safeFetch('/api/profile/game-config/save/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-check mr-2"></i>Save Config';
    
    if (data && data.success) {
        alert(data.message || 'Game config saved successfully!');
        resetGameConfigForm();
        window.location.reload();
    }
});

// Edit Game Config
function editGameConfig(config) {
    safeGetById('gameConfigId').value = config.id;
    
    // Find game ID from available games
    const game = loadoutAvailableGames.find(g => g.name === config.game || g.slug === config.game_slug);
    if (game) {
        safeGetById('gameConfigGame').value = game.id;
    }
    
    safeGetById('gameConfigDPI').value = config.settings?.dpi || config.dpi || '';
    safeGetById('gameConfigSens').value = config.settings?.sensitivity || config.sensitivity || '';
    safeGetById('gameConfigRes').value = config.settings?.resolution || config.resolution || '';
    
    // Extract non-standard settings for JSON field
    const standardKeys = ['dpi', 'sensitivity', 'resolution'];
    const additionalSettings = {};
    if (config.settings) {
        Object.keys(config.settings).forEach(key => {
            if (!standardKeys.includes(key)) {
                additionalSettings[key] = config.settings[key];
            }
        });
    }
    
    safeGetById('gameConfigSettings').value = Object.keys(additionalSettings).length > 0 
        ? JSON.stringify(additionalSettings, null, 2) : '';
    
    safeGetById('gameConfigNotes').value = config.notes || '';
    safeGetById('gameConfigIsPublic').checked = config.is_public;
    
    safeGetById('gameConfigFormTitle').textContent = 'Edit Game Config';
    
    // Switch to game configs tab if not already there
    if (currentLoadoutTab !== 'gameconfigs') {
        switchLoadoutTab('gameconfigs');
    }
    
    // Scroll to form
    safeGetById('gameConfigForm').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Delete Game Config
async function deleteGameConfig(id, gameName) {
    if (!requireOwner('deleteGameConfig')) return;
    if (!confirm(`Delete config for ${gameName}? This cannot be undone.`)) return;
    
    const url = `/api/profile/game-config/${id}/delete/`;
    debugLog('Delete game config', { id, url });
    
    const data = await safeFetch(url, { method: 'DELETE' });
    if (data && data.success) {
        alert(data.message || 'Game config deleted successfully!');
        window.location.reload();
    }
}

// Reset Game Config Form
function resetGameConfigForm() {
    safeGetById('gameConfigForm').reset();
    safeGetById('gameConfigId').value = '';
    safeGetById('gameConfigFormTitle').textContent = 'Add Game Config';
    safeGetById('gameConfigIsPublic').checked = true;
}

// ============================================================================
// END LOADOUT MODAL
// ============================================================================

// Manage Showcase Modal
function openManageShowcaseModal() {
    if (!requireOwner('openManageShowcaseModal')) return;
    
    const modal = safeGetById('manageShowcaseModal');
    if (!modal) return;
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeManageShowcaseModal() {
    const modal = safeGetById('manageShowcaseModal');
    if (!modal) return;
    
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// Close modals on ESC
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeCreateBountyModal();
        closeEditLoadoutModal();
        closeManageShowcaseModal();
        closeProofModal();
        closeDisputeModal();
    }
});

// ============================================================================
// UP-PHASE2E: MATCH PROGRESSION ACTIONS
// ============================================================================

// Start Match
async function startMatch(bountyId) {
    if (!requireOwner('startMatch')) return;
    if (!confirm('Start this match now? Both players should be ready.')) return;
    
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Starting...';
    
    const url = `/api/bounty/${bountyId}/start/`;
    debugLog('Start match', { bountyId, url });
    
    const data = await safeFetch(url, { method: 'POST' });
    
    if (data && data.success) {
        alert(data.message);
        location.reload();
    } else {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-play mr-2"></i> Start Match';
    }
}

// Proof Submission Modal
let currentProofBountyId = null;

function openProofModal(bountyId, bountyTitle, creatorId, creatorName, acceptorId, acceptorName) {
    if (!requireOwner('openProofModal')) return;
    
    currentProofBountyId = bountyId;
    const titleEl = safeGetById('proofBountyTitle');
    if (titleEl) titleEl.textContent = bountyTitle;
    
    // Populate winner dropdown
    const winnerSelect = safeGetById('proofWinner');
    winnerSelect.innerHTML = `
        <option value="">Select winner...</option>
        <option value="${creatorId}">${creatorName}</option>
        <option value="${acceptorId}">${acceptorName}</option>
    `;
    
    safeGetById('proofModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeProofModal() {
    currentProofBountyId = null;
    safeGetById('proofModal').classList.add('hidden');
    document.body.style.overflow = '';
    
    // Reset form
    safeGetById('proofWinner').value = '';
    safeGetById('proofUrl').value = '';
    safeGetById('proofType').value = 'screenshot';
    safeGetById('proofDescription').value = '';
}

async function submitProof() {
    if (!requireOwner('submitProof')) return;
    
    const winnerId = safeGetById('proofWinner').value;
    const proofUrl = safeGetById('proofUrl').value.trim();
    const proofType = safeGetById('proofType').value;
    const description = safeGetById('proofDescription').value.trim();
    
    if (!winnerId) {
        alert('Please select a winner');
        return;
    }
    
    if (!proofUrl) {
        alert('Please provide a proof URL');
        return;
    }
    
    const data = {
        claimed_winner_id: parseInt(winnerId),
        proof_url: proofUrl,
        proof_type: proofType,
        description: description
    };
    
    const url = `/api/bounty/${currentProofBountyId}/proof/`;
    debugLog('Submit proof', { bountyId: currentProofBountyId, url });
    
    const result = await safeFetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    if (result && result.success) {
        alert(result.message);
        closeProofModal();
        location.reload();
    }
}

// Confirm Result
async function confirmResult(bountyId) {
    if (!requireOwner('confirmResult')) return;
    if (!confirm('Confirm this result? Winner will receive 95% of stake (5% platform fee). This action cannot be undone.')) return;
    
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Confirming...';
    
    const url = `/api/bounty/${bountyId}/confirm/`;
    debugLog('Confirm result', { bountyId, url });
    
    const data = await safeFetch(url, { method: 'POST' });
    
    if (data && data.success) {
        alert(data.message);
        location.reload();
    } else {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-check mr-2"></i> Confirm Result';
    }
}

// Dispute Modal
let currentDisputeBountyId = null;

function openDisputeModal(bountyId, bountyTitle) {
    if (!requireOwner('openDisputeModal')) return;
    
    currentDisputeBountyId = bountyId;
    const titleEl = safeGetById('disputeBountyTitle');
    if (titleEl) titleEl.textContent = bountyTitle;
    
    const modal = safeGetById('disputeModal');
    if (!modal) return;
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    // Character counter
    const textarea = safeGetById('disputeReason');
    const counter = safeGetById('disputeCharCount');
    textarea.addEventListener('input', () => {
        counter.textContent = textarea.value.length;
    });
}

function closeDisputeModal() {
    currentDisputeBountyId = null;
    safeGetById('disputeModal').classList.add('hidden');
    document.body.style.overflow = '';
    
    // Reset form
    safeGetById('disputeReason').value = '';
    safeGetById('disputeCharCount').textContent = '0';
}

async function submitDispute() {
    if (!requireOwner('submitDispute')) return;
    
    const reason = safeGetById('disputeReason').value.trim();
    
    if (reason.length < 50) {
        alert('Dispute reason must be at least 50 characters');
        return;
    }
    
    const data = { reason: reason };
    const disputeUrl = `/api/bounty/${currentDisputeBountyId}/dispute/`;
    
    const result = await safeFetch(disputeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    if (result && result.success) {
        alert(result.message);
        closeDisputeModal();
        location.reload();
    }
}

// UP-PHASE2E-PART2: Endorsement Modal Functions
let currentEndorseBountyId = null;
let currentEndorseReceiverId = null;
let selectedSkills = new Set();

function openEndorseModal(bountyId, receiverId) {
    currentEndorseBountyId = bountyId;
    currentEndorseReceiverId = receiverId;
    selectedSkills.clear();
    
    // Reset skill buttons
    document.querySelectorAll('.skill-btn').forEach(btn => {
        btn.classList.remove('bg-[var(--z-gold)]', 'border-[var(--z-gold)]');
        btn.classList.add('bg-white/5', 'border-white/10');
    });
    
    // Skill button click handlers
    document.querySelectorAll('.skill-btn').forEach(btn => {
        btn.onclick = function() {
            const skill = this.dataset.skill;
            if (selectedSkills.has(skill)) {
                selectedSkills.delete(skill);
                this.classList.remove('bg-[var(--z-gold)]', 'border-[var(--z-gold)]');
                this.classList.add('bg-white/5', 'border-white/10');
            } else {
                selectedSkills.add(skill);
                this.classList.add('bg-[var(--z-gold)]', 'border-[var(--z-gold)]');
                this.classList.remove('bg-white/5', 'border-white/10');
            }
            
            // Update hint
            const hint = safeGetById('endorseSkillHint');
            if (selectedSkills.size > 0) {
                hint.textContent = `${selectedSkills.size} skill(s) selected`;
                hint.classList.add('text-[var(--z-gold)]');
            } else {
                hint.textContent = 'Click skills to select/deselect';
                hint.classList.remove('text-[var(--z-gold)]');
            }
        };
    });
    
    safeGetById('endorseModal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeEndorseModal() {
    currentEndorseBountyId = null;
    currentEndorseReceiverId = null;
    selectedSkills.clear();
    safeGetById('endorseModal').classList.add('hidden');
    document.body.style.overflow = '';
}

async function submitEndorsement() {
    if (!requireOwner('submitEndorsement')) return;
    if (selectedSkills.size === 0) {
        alert('Please select at least one skill to endorse');
        return;
    }
    
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Submitting...';
    
    // Backend supports one skill per endorsement
    const skill = Array.from(selectedSkills)[0];
    
    const data = {
        skill: skill,
        receiver_id: currentEndorseReceiverId
    };
    
    const endorseUrl = `/api/bounty/${currentEndorseBountyId}/endorse/`;
    const result = await safeFetch(endorseUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    if (result && result.success) {
        alert(result.message || 'Endorsement submitted!');
        closeEndorseModal();
        location.reload();
    } else {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-star mr-2"></i>Submit Endorsement';
    }
}

// UP-PHASE2F: Avatar and Cover Upload
document.addEventListener('DOMContentLoaded', function() {
    const avatarInput = safeGetById('avatarInput');
    const coverInput = safeGetById('coverInput');
    
    if (avatarInput) {
        avatarInput.addEventListener('change', function(e) {
            handleMediaUpload(e.target.files[0], 'avatar');
        });
    }
    
    if (coverInput) {
        coverInput.addEventListener('change', function(e) {
            handleMediaUpload(e.target.files[0], 'banner');
        });
    }
});

async function handleMediaUpload(file, mediaType) {
    if (!requireOwner('handleMediaUpload')) return;
    if (!file) return;
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
        alert('Please select an image file');
        return;
    }
    
    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
        alert('Image must be smaller than 5MB');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('media_type', mediaType);
    
    const data = await safeFetch('/api/profile/upload-media/', {
        method: 'POST',
        body: formData
        // NOTE: Do NOT set Content-Type - browser will set multipart/form-data with boundary
    });
    
    if (data && data.success) {
        alert(`${mediaType === 'avatar' ? 'Avatar' : 'Cover'} updated successfully!`);
        
        // Update preview
        if (mediaType === 'avatar') {
            const avatarPreview = safeGetById('avatarPreview');
            if (avatarPreview) {
                avatarPreview.src = data.url;
            }
        } else {
            location.reload();
        }
    }
}

// UP-PHASE2F: Follower/Following Modal System
function openFollowersModal() {
    if (!IS_OWN_PROFILE) {
        alert('This followers list is private');
        return;
    }
    
    const modal = safeGetById('followersModal');
    if (modal) {
        modal.classList.remove('hidden');
        loadFollowersList();
    }
}

// UP-PHASE2F-PART3: Social Links Management
function openSocialLinksModal() {
    if (!requireOwner('openSocialLinksModal')) return;
    
    const modal = safeGetById('socialLinksModal');
    if (modal) {
        modal.classList.remove('hidden');
        loadSocialLinks();
    }
}

function closeSocialLinksModal() {
    const modal = safeGetById('socialLinksModal');
    if (modal) modal.classList.add('hidden');
}

async function loadSocialLinks() {
    const container = safeGetById('socialLinksList');
    container.innerHTML = '<div class="text-center py-8"><i class="fas fa-spinner fa-spin text-2xl text-gray-500"></i></div>';
    
    const data = await safeFetch('/api/profile/social-links/');
    
    if (data && data.success) {
        if (data.links.length === 0) {
            container.innerHTML = '<div class="text-center py-8 text-gray-500">No social links yet. Add one above!</div>';
            return;
        }
        
        container.innerHTML = `
            <h3 class="text-sm font-bold text-white mb-3 uppercase tracking-wider">Your Links</h3>
            <div class="space-y-2">
                ${data.links.map(link => `
                    <div class="flex items-center gap-3 p-3 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition group">
                        <div class="w-10 h-10 rounded-lg bg-black/30 flex items-center justify-center text-gray-400">
                            <i class="fa-brands fa-${link.platform} text-lg"></i>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="font-bold text-white text-sm capitalize">${getPlatformName(link.platform)}</div>
                            <div class="text-xs text-gray-500 truncate">${link.url}</div>
                        </div>
                        <button onclick="deleteSocialLink(${link.id}, '${link.platform}')" 
                                class="opacity-0 group-hover:opacity-100 transition px-3 py-2 bg-red-500/20 hover:bg-red-500 text-red-500 hover:text-white rounded-lg text-sm">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                `).join('')}
            </div>
        `;
    } else {
        container.innerHTML = '<div class="text-center py-8 text-red-500">Failed to load links</div>';
    }
}

function getPlatformName(platform) {
    const names = {
        'twitch': 'Twitch',
        'youtube': 'YouTube',
        'twitter': 'Twitter/X',
        'discord': 'Discord',
        'instagram': 'Instagram',
        'tiktok': 'TikTok',
        'facebook': 'Facebook',
        'kick': 'Kick',
        'steam': 'Steam',
        'github': 'GitHub',
        'facebook_gaming': 'Facebook Gaming',
        'riot': 'Riot Games'
    };
    return names[platform] || platform;
}

async function addSocialLink() {
    if (!requireOwner('addSocialLink')) return;
    
    const platformSelect = safeGetById('newLinkPlatform');
    const urlInput = safeGetById('newLinkUrl');
    
    const platform = platformSelect.value.trim();
    const url = urlInput.value.trim();
    
    if (!platform || !url) {
        alert('Please select a platform and enter a URL');
        return;
    }
    
    // Basic URL validation
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        alert('Please enter a valid URL (must start with http:// or https://)');
        return;
    }
    
    const data = await safeFetch('/api/profile/social-links/add/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ platform, url })
    });
    
    if (data && data.success) {
        platformSelect.value = '';
        urlInput.value = '';
        loadSocialLinks();
        alert('Social link added successfully!');
    }
}

async function deleteSocialLink(linkId, platform) {
    if (!requireOwner('deleteSocialLink')) return;
    if (!confirm(`Delete your ${getPlatformName(platform)} link?`)) return;
    
    const data = await safeFetch(`/api/profile/social-links/${linkId}/delete/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: linkId })
    });
    
    if (data && data.success) {
        loadSocialLinks();
        setTimeout(() => location.reload(), 500);
    }
}

// UP-PHASE2F: Follower/Following Modal System (continued)
function openFollowersModal() {
    const modal = safeGetById('followersModal');
    if (modal) {
        modal.classList.remove('hidden');
        loadFollowersList();
    }
}

function openFollowingModal() {
        alert('This following list is private');
        return;
    
    const modal = safeGetById('followingModal');
    if (modal) {
        modal.classList.remove('hidden');
        loadFollowingList();
    }
}

function closeFollowersModal() {
    const modal = safeGetById('followersModal');
    if (modal) modal.classList.add('hidden');
}

function closeFollowingModal() {
    const modal = safeGetById('followingModal');
    if (modal) modal.classList.add('hidden');
}

async function loadFollowersList() {
    const container = safeGetById('followersList');
    
    container.innerHTML = '<div class="text-center py-8"><i class="fas fa-spinner fa-spin text-2xl text-gray-500"></i></div>';
    
    const data = await safeFetch(followersUrl);
    
    if (data && data.success) {
        if (data.followers.length === 0) {
            container.innerHTML = '<div class="text-center py-12 text-gray-500">No followers yet</div>';
            return;
        }
        
        container.innerHTML = data.followers.map(user => `
            <div class="flex items-center justify-between p-4 hover:bg-white/5 transition">
                <div class="flex items-center gap-3">
                    <img src="${user.avatar_url || ''}" 
                         alt="${user.display_name}" 
                         class="w-12 h-12 rounded-full border border-white/10">
                    <div>
                        <div class="font-bold text-white flex items-center gap-2">
                            ${user.display_name}
                            ${user.is_verified ? '<i class="fas fa-check-circle text-[var(--z-cyan)] text-sm"></i>' : ''}
                        </div>
                        <div class="text-sm text-gray-500">@${user.username}</div>
                    </div>
                </div>
                ${renderFollowButton(user)}
            </div>
        `).join('');
    } else {
        container.innerHTML = `<div class="text-center py-12 text-red-500">${data?.error || 'Failed to load followers'}</div>`;
    }
}

async function loadFollowingList() {
    const container = safeGetById('followingList');
    
    container.innerHTML = '<div class="text-center py-8"><i class="fas fa-spinner fa-spin text-2xl text-gray-500"></i></div>';
    
    const data = await safeFetch(followingUrl);
    
    if (data && data.success) {
        if (data.following.length === 0) {
            container.innerHTML = '<div class="text-center py-12 text-gray-500">Not following anyone yet</div>';
            return;
        }
        
        container.innerHTML = data.following.map(user => `
            <div class="flex items-center justify-between p-4 hover:bg-white/5 transition">
                <div class="flex items-center gap-3">
                    <img src="${user.avatar_url || ''}" 
                         alt="${user.display_name}" 
                         class="w-12 h-12 rounded-full border border-white/10">
                    <div>
                        <div class="font-bold text-white flex items-center gap-2">
                            ${user.display_name}
                            ${user.is_verified ? '<i class="fas fa-check-circle text-[var(--z-cyan)] text-sm"></i>' : ''}
                        </div>
                        <div class="text-sm text-gray-500">@${user.username}</div>
                    </div>
                </div>
                ${renderFollowButton(user)}
            </div>
        `).join('');
    } else {
        container.innerHTML = `<div class="text-center py-12 text-red-500">${data?.error || 'Failed to load following'}</div>`;
    }
}

function renderFollowButton(user) {
    
    if (isOwner || isSelf || !isLoggedIn) {
        return '';
    }
    
    if (user.is_following) {
        return `<button onclick="handleFollowAction('${user.username}', 'unfollow', this)" 
                       class="px-4 py-2 bg-white/10 hover:bg-red-500/20 text-white rounded-lg transition text-sm font-bold border border-white/20">
                    Following
                </button>`;
    } else {
        return `<button onclick="handleFollowAction('${user.username}', 'follow', this)" 
                       class="px-4 py-2 bg-gradient-to-r from-[var(--z-cyan)] to-[var(--z-purple)] hover:opacity-90 text-white rounded-lg transition text-sm font-bold">
                    Follow
                </button>`;
    }
}

async function handleFollowAction(username, action, button) {
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    
    const followUrl = action === 'follow' ? `/api/social/follow/${username}/` : `/api/social/unfollow/${username}/`;
    const data = await safeFetch(followUrl, { method: 'POST' });
    
    if (data && data.success) {
        // Reload the current list
        const followersModalOpen = !safeGetById('followersModal').classList.contains('hidden');
        if (followersModalOpen) {
            loadFollowersList();
        } else {
            loadFollowingList();
        }
        location.reload();
    } else {
        button.disabled = false;
        button.innerHTML = action === 'follow' ? 'Follow' : 'Following';
    }
}

