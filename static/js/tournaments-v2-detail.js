/**
 * DeltaCrown Tournament Detail Page V2 - JavaScript
 * Modern Esports Tournament Detail with Tabbed Interface
 * 
 * Features:
 * - Tab navigation
 * - Dynamic content loading
 * - Registration state management
 * - Share functionality
 * - Smooth scrolling
 * - Phase B integration (countdown + capacity)
 */

(function() {
    'use strict';

    // ============================================
    // STATE MANAGEMENT
    // ============================================
    
    const DetailState = {
        currentTab: 'overview',
        tournamentSlug: null,
        registrationStatus: null,
        isRegistered: false
    };

    // ============================================
    // DOM ELEMENTS
    // ============================================
    
    const elements = {
        tabs: null,
        tabContents: null,
        registrationBtn: null,
        shareButtons: null,
        infoBar: null
    };

    // ============================================
    // INITIALIZATION
    // ============================================
    
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', setupDetail);
        } else {
            setupDetail();
        }
    }

    function setupDetail() {
        console.log('[Detail V2] Initializing tournament detail...');
        
        // Cache DOM elements
        cacheElements();
        
        // Get tournament slug from page
        const tournamentElement = document.querySelector('[data-tournament-slug]');
        if (tournamentElement) {
            DetailState.tournamentSlug = tournamentElement.dataset.tournamentSlug;
        }
        
        // Setup event listeners
        setupEventListeners();
        
        // Load initial tab from URL hash
        loadTabFromHash();
        
        // Setup scroll effects
        setupScrollEffects();
        
        // Initialize countdown timers (Phase B integration)
        if (typeof window.initializeCountdownTimers === 'function') {
            window.initializeCountdownTimers();
        }
        
        // Load registration status if user is logged in
        if (document.querySelector('[data-user-authenticated]')) {
            loadRegistrationStatus();
        }
        
        console.log('[Detail V2] Detail page initialized successfully');
    }

    function cacheElements() {
        elements.tabs = document.querySelectorAll('.detail-tab');
        elements.tabContents = document.querySelectorAll('.detail-tab-content');
        elements.registrationBtn = document.getElementById('detail-registration-btn');
        elements.shareButtons = document.querySelectorAll('.detail-share-btn');
        elements.infoBar = document.querySelector('.detail-info-bar');
    }

    // ============================================
    // EVENT LISTENERS
    // ============================================
    
    function setupEventListeners() {
        // Tab navigation
        if (elements.tabs) {
            elements.tabs.forEach(tab => {
                tab.addEventListener('click', handleTabClick);
            });
        }
        
        // Registration button
        if (elements.registrationBtn) {
            elements.registrationBtn.addEventListener('click', handleRegistrationClick);
        }
        
        // Share buttons
        if (elements.shareButtons) {
            elements.shareButtons.forEach(btn => {
                btn.addEventListener('click', handleShareClick);
            });
        }
        
        // Hash change for tab navigation
        window.addEventListener('hashchange', loadTabFromHash);
        
        // Keyboard shortcuts
        document.addEventListener('keydown', handleKeyboardShortcuts);
    }

    // ============================================
    // TAB NAVIGATION
    // ============================================
    
    function handleTabClick(event) {
        const tab = event.currentTarget;
        const tabId = tab.dataset.tab;
        
        if (tabId) {
            switchTab(tabId);
            
            // Update URL hash
            window.history.replaceState(null, null, `#${tabId}`);
        }
    }

    function switchTab(tabId) {
        console.log('[Detail V2] Switching to tab:', tabId);
        
        // Update tab buttons
        elements.tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabId);
        });
        
        // Update tab content
        elements.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `tab-${tabId}`);
        });
        
        // Update state
        DetailState.currentTab = tabId;
        
        // Scroll to top of content
        const contentElement = document.getElementById(`tab-${tabId}`);
        if (contentElement) {
            smoothScrollTo(contentElement, -120);
        }
    }

    function loadTabFromHash() {
        const hash = window.location.hash.slice(1); // Remove #
        if (hash && document.getElementById(`tab-${hash}`)) {
            switchTab(hash);
        } else {
            switchTab('overview'); // Default tab
        }
    }

    // ============================================
    // REGISTRATION
    // ============================================
    
    function loadRegistrationStatus() {
        if (!DetailState.tournamentSlug) return;
        
        const apiUrl = `/tournaments/api/${DetailState.tournamentSlug}/register/context/`;
        
        fetch(apiUrl, {
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            console.log('[Detail V2] Registration status:', data);
            DetailState.registrationStatus = data;
            DetailState.isRegistered = data.already_registered || false;
            
            updateRegistrationUI(data);
        })
        .catch(error => {
            console.error('[Detail V2] Failed to load registration status:', error);
        });
    }

    function updateRegistrationUI(data) {
        if (!elements.registrationBtn) return;
        
        if (data.already_registered) {
            elements.registrationBtn.textContent = '✓ Registered';
            elements.registrationBtn.disabled = true;
            elements.registrationBtn.style.background = 'var(--color-success)';
            
            // Show registration status message
            const statusDiv = document.querySelector('.detail-registration-status');
            if (statusDiv) {
                statusDiv.style.display = 'block';
            }
        } else if (data.can_register === false) {
            elements.registrationBtn.textContent = data.reason || 'Registration Closed';
            elements.registrationBtn.disabled = true;
            elements.registrationBtn.style.background = 'rgba(255, 255, 255, 0.1)';
        }
    }

    function handleRegistrationClick(event) {
        event.preventDefault();
        
        if (!DetailState.tournamentSlug) {
            console.error('[Detail V2] No tournament slug found');
            return;
        }
        
        // Check if user is authenticated
        const isAuthenticated = document.querySelector('[data-user-authenticated]');
        if (!isAuthenticated) {
            // Redirect to login
            window.location.href = `/accounts/login/?next=/tournaments/${DetailState.tournamentSlug}/register/`;
            return;
        }
        
        // Redirect to registration page
        window.location.href = `/tournaments/${DetailState.tournamentSlug}/register/`;
    }

    // ============================================
    // SHARE FUNCTIONALITY
    // ============================================
    
    function handleShareClick(event) {
        const btn = event.currentTarget;
        const platform = btn.dataset.platform;
        const url = window.location.href;
        const title = document.querySelector('.detail-hero-title')?.textContent || 'Tournament';
        
        let shareUrl = '';
        
        switch(platform) {
            case 'twitter':
                shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(url)}`;
                break;
            case 'facebook':
                shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
                break;
            case 'linkedin':
                shareUrl = `https://www.linkedin.com/shareArticle?mini=true&url=${encodeURIComponent(url)}&title=${encodeURIComponent(title)}`;
                break;
            case 'copy':
                copyToClipboard(url);
                showToast('Link copied to clipboard!');
                return;
        }
        
        if (shareUrl) {
            window.open(shareUrl, '_blank', 'width=600,height=400');
        }
    }

    function copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        }
    }

    function showToast(message) {
        // Use existing toast system if available (Phase D)
        if (typeof window.Toast !== 'undefined') {
            new window.Toast(message, 'success').show();
        } else {
            // Simple fallback
            alert(message);
        }
    }

    // ============================================
    // SCROLL EFFECTS
    // ============================================
    
    function setupScrollEffects() {
        let lastScroll = 0;
        
        window.addEventListener('scroll', () => {
            const currentScroll = window.pageYOffset;
            
            // Add shadow to info bar on scroll
            if (elements.infoBar) {
                if (currentScroll > 100) {
                    elements.infoBar.style.boxShadow = 'var(--shadow-md)';
                } else {
                    elements.infoBar.style.boxShadow = 'none';
                }
            }
            
            lastScroll = currentScroll;
        });
    }

    // ============================================
    // KEYBOARD SHORTCUTS
    // ============================================
    
    function handleKeyboardShortcuts(event) {
        // Number keys 1-5 for tab switching
        if (event.key >= '1' && event.key <= '5') {
            const tabIndex = parseInt(event.key) - 1;
            const tabs = Array.from(elements.tabs);
            if (tabs[tabIndex]) {
                tabs[tabIndex].click();
            }
        }
        
        // Arrow keys for tab navigation
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
            const currentIndex = Array.from(elements.tabs).findIndex(tab => 
                tab.classList.contains('active')
            );
            
            let nextIndex;
            if (event.key === 'ArrowLeft') {
                nextIndex = currentIndex > 0 ? currentIndex - 1 : elements.tabs.length - 1;
            } else {
                nextIndex = currentIndex < elements.tabs.length - 1 ? currentIndex + 1 : 0;
            }
            
            elements.tabs[nextIndex].click();
        }
    }

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================
    
    function smoothScrollTo(element, offset = 0) {
        if (!element) return;
        
        const elementPosition = element.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset + offset;
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }

    // ============================================
    // DYNAMIC CONTENT LOADING
    // ============================================
    
    function loadTeams() {
        if (!DetailState.tournamentSlug) return;
        
        const teamsContainer = document.querySelector('.teams-grid');
        if (!teamsContainer || teamsContainer.dataset.loaded === 'true') return;
        
        const apiUrl = `/api/tournaments/${DetailState.tournamentSlug}/teams/`;
        
        console.log('[Detail V2] Loading teams...');
        
        fetch(apiUrl, {
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(teams => {
            console.log('[Detail V2] Loaded teams:', teams.length);
            renderTeams(teams, teamsContainer);
            teamsContainer.dataset.loaded = 'true';
        })
        .catch(error => {
            console.error('[Detail V2] Failed to load teams:', error);
        });
    }

    function renderTeams(teams, container) {
        if (teams.length === 0) {
            container.innerHTML = `
                <div class="hub-empty" style="grid-column: 1 / -1;">
                    <div class="hub-empty-icon">👥</div>
                    <h3 class="hub-empty-title">No Teams Registered Yet</h3>
                    <p class="hub-empty-text">Be the first to register!</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = teams.map(team => `
            <article class="team-card">
                <div class="team-card-header">
                    ${team.logo ? 
                        `<img src="${team.logo}" alt="${team.name}" class="team-card-logo">` :
                        `<div class="team-card-logo-placeholder">${team.name.charAt(0)}</div>`
                    }
                    <div>
                        <div class="team-card-name">${team.name}</div>
                        <div class="team-card-captain">Captain: ${team.captain}</div>
                    </div>
                </div>
                <ul class="team-card-players">
                    ${team.players.map(player => `
                        <li class="team-card-player">${player}</li>
                    `).join('')}
                </ul>
            </article>
        `).join('');
    }

    // ============================================
    // PUBLIC API
    // ============================================
    
    window.TournamentDetailV2 = {
        init,
        switchTab,
        loadRegistrationStatus,
        loadTeams,
        getState: () => ({ ...DetailState }),
        setState: (newState) => {
            Object.assign(DetailState, newState);
        }
    };

    // Auto-initialize
    init();

})();
