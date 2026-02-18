/**
 * Tournament Detail Page - Dynamic Functionality
 * Game theme loader, lifecycle management, countdown timers
 * Created: November 20, 2025
 */

(function() {
    'use strict';

    // ==================== CONFIGURATION ====================
    const CONFIG = {
        countdownUpdateInterval: 1000, // 1 second
        lobbyPollInterval: 30000, // 30 seconds
        tabTransitionDuration: 300, // milliseconds
    };

    // ==================== STATE ====================
    const state = {
        currentTab: 'overview',
        countdownIntervals: {},
        lobbyPollTimer: null,
        tournamentData: null,
    };

    // ==================== INITIALIZATION ====================
    function init() {
        // Extract tournament data from DOM
        extractTournamentData();
        
        // Apply game theme
        applyGameTheme();
        
        // Initialize tabs
        initializeTabs();
        
        // Initialize countdowns
        initializeCountdowns();
        
        // Initialize lobby polling (if registered)
        initializeLobbyPolling();
        
        // Initialize action buttons
        initializeActionButtons();
        
        // Initialize share functionality
        initializeShareButtons();
        
        dcLog('Tournament detail page initialized');
    }

    // ==================== DATA EXTRACTION ====================
    function extractTournamentData() {
        const heroElement = document.querySelector('.tournament-hero');
        if (!heroElement) return;

        state.tournamentData = {
            slug: heroElement.dataset.tournamentSlug,
            gameSlug: heroElement.dataset.gameSlug,
            status: heroElement.dataset.status,
            isRegistered: heroElement.dataset.isRegistered === 'true',
            checkInOpens: heroElement.dataset.checkInOpens,
            checkInCloses: heroElement.dataset.checkInCloses,
            tournamentStart: heroElement.dataset.tournamentStart,
            registrationEnd: heroElement.dataset.registrationEnd,
        };
    }

    // ==================== GAME THEME ====================
    function applyGameTheme() {
        if (!state.tournamentData || !state.tournamentData.gameSlug) return;

        const gameSlug = state.tournamentData.gameSlug.toLowerCase();
        document.body.setAttribute('data-game', gameSlug);
        
        dcLog(`Applied game theme: ${gameSlug}`);
    }

    // ==================== TAB NAVIGATION ====================
    function initializeTabs() {
        const tabButtons = document.querySelectorAll('.tournament-nav__item');
        const tabContents = document.querySelectorAll('[data-tab-content]');

        if (!tabButtons.length || !tabContents.length) return;

        // Set initial active tab
        const initialTab = tabButtons[0];
        if (initialTab) {
            initialTab.classList.add('active');
            showTab(initialTab.dataset.tab);
        }

        // Tab click handlers
        tabButtons.forEach(button => {
            button.addEventListener('click', function() {
                const tabId = this.dataset.tab;
                
                // Update active button
                tabButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                
                // Show corresponding content
                showTab(tabId);
                
                state.currentTab = tabId;
            });
        });
    }

    function showTab(tabId) {
        const tabContents = document.querySelectorAll('[data-tab-content]');
        
        tabContents.forEach(content => {
            if (content.dataset.tabContent === tabId) {
                content.classList.remove('hidden');
                content.classList.add('fade-in-up');
            } else {
                content.classList.add('hidden');
            }
        });
    }

    // ==================== COUNTDOWN TIMERS ====================
    function initializeCountdowns() {
        const countdowns = document.querySelectorAll('[data-countdown]');
        
        countdowns.forEach(countdown => {
            const targetDate = countdown.dataset.countdown;
            const countdownId = countdown.dataset.countdownId || targetDate;
            
            if (targetDate) {
                startCountdown(countdown, new Date(targetDate), countdownId);
            }
        });
    }

    function startCountdown(element, targetDate, countdownId) {
        // Clear existing interval if any
        if (state.countdownIntervals[countdownId]) {
            clearInterval(state.countdownIntervals[countdownId]);
        }

        function updateCountdown() {
            const now = new Date();
            const diff = targetDate - now;

            if (diff <= 0) {
                // Countdown finished
                clearInterval(state.countdownIntervals[countdownId]);
                delete state.countdownIntervals[countdownId];
                element.innerHTML = '<div class="countdown__label">Event Started!</div>';
                
                // Reload page to update status
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
                return;
            }

            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);

            // Update display
            const daysEl = element.querySelector('[data-countdown-days]');
            const hoursEl = element.querySelector('[data-countdown-hours]');
            const minutesEl = element.querySelector('[data-countdown-minutes]');
            const secondsEl = element.querySelector('[data-countdown-seconds]');

            if (daysEl) daysEl.textContent = String(days).padStart(2, '0');
            if (hoursEl) hoursEl.textContent = String(hours).padStart(2, '0');
            if (minutesEl) minutesEl.textContent = String(minutes).padStart(2, '0');
            if (secondsEl) secondsEl.textContent = String(seconds).padStart(2, '0');
        }

        // Initial update
        updateCountdown();

        // Set interval
        state.countdownIntervals[countdownId] = setInterval(
            updateCountdown,
            CONFIG.countdownUpdateInterval
        );
    }

    // ==================== LOBBY POLLING ====================
    function initializeLobbyPolling() {
        if (!state.tournamentData || !state.tournamentData.isRegistered) return;
        if (state.tournamentData.status !== 'registration_closed' && 
            state.tournamentData.status !== 'live') return;

        // Poll lobby status for check-in updates
        pollLobbyStatus();
        state.lobbyPollTimer = setInterval(pollLobbyStatus, CONFIG.lobbyPollInterval);
    }

    function pollLobbyStatus() {
        if (!state.tournamentData) return;

        const lobbyUrl = `/tournaments/${state.tournamentData.slug}/lobby/api/status/`;
        
        fetch(lobbyUrl)
            .then(response => {
                if (!response.ok) return null;
                return response.json();
            })
            .then(data => {
                if (!data) return;
                
                // Update check-in status if changed
                if (data.checkInStatus && data.checkInStatus !== state.tournamentData.checkInStatus) {
                    dcLog('Check-in status changed, reloading...');
                    window.location.reload();
                }
                
                // Update bracket visibility if changed
                if (data.bracketVisible !== undefined) {
                    updateBracketVisibility(data.bracketVisible);
                }
            })
            .catch(error => {
                console.error('Lobby status poll failed:', error);
            });
    }

    function updateBracketVisibility(isVisible) {
        const bracketButton = document.querySelector('[data-action="view-bracket"]');
        if (bracketButton) {
            bracketButton.style.display = isVisible ? 'flex' : 'none';
        }
    }

    // ==================== ACTION BUTTONS ====================
    function initializeActionButtons() {
        // CTA button handler
        const ctaButton = document.querySelector('.cta-button');
        if (ctaButton && !ctaButton.classList.contains('cta-button--disabled')) {
            ctaButton.addEventListener('click', handleCtaClick);
        }

        // Action link handlers
        const actionLinks = document.querySelectorAll('[data-action]');
        actionLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                const action = this.dataset.action;
                const requiresConfirm = this.dataset.confirm === 'true';
                
                if (requiresConfirm) {
                    e.preventDefault();
                    confirmAction(action, this.href);
                }
            });
        });

        // Check-in button
        const checkInButton = document.querySelector('[data-action="check-in"]');
        if (checkInButton) {
            checkInButton.addEventListener('click', handleCheckIn);
        }
    }

    function handleCtaClick(e) {
        const button = e.currentTarget;
        const action = button.dataset.ctaAction;
        
        if (!action) return;

        // Show loading state
        const originalText = button.innerHTML;
        button.innerHTML = '<span>Loading...</span>';
        button.disabled = true;

        // Handle different actions
        switch (action) {
            case 'register':
                window.location.href = button.href;
                break;
            case 'login':
                window.location.href = button.href;
                break;
            default:
                window.location.href = button.href;
        }
    }

    function handleCheckIn(e) {
        e.preventDefault();
        const button = e.currentTarget;
        const checkInUrl = button.href;

        if (!confirm('Are you ready to check in for this tournament?')) {
            return;
        }

        // Show loading state
        button.innerHTML = '<span>Checking in...</span>';
        button.disabled = true;

        // Send check-in request
        fetch(checkInUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Check-in successful! Redirecting to lobby...');
                window.location.reload();
            } else {
                alert(data.message || 'Check-in failed. Please try again.');
                button.innerHTML = '<span>Check In</span>';
                button.disabled = false;
            }
        })
        .catch(error => {
            console.error('Check-in error:', error);
            alert('Check-in failed. Please try again.');
            button.innerHTML = '<span>Check In</span>';
            button.disabled = false;
        });
    }

    function confirmAction(action, url) {
        const messages = {
            'forfeit': 'Are you sure you want to forfeit this tournament? This action cannot be undone.',
            'leave': 'Are you sure you want to leave this tournament?',
            'cancel-registration': 'Are you sure you want to cancel your registration?',
        };

        const message = messages[action] || 'Are you sure you want to proceed?';
        
        if (confirm(message)) {
            window.location.href = url;
        }
    }

    // ==================== SHARE FUNCTIONALITY ====================
    function initializeShareButtons() {
        const shareButton = document.querySelector('[data-action="share"]');
        if (shareButton) {
            shareButton.addEventListener('click', handleShare);
        }

        const copyLinkButton = document.querySelector('[data-action="copy-link"]');
        if (copyLinkButton) {
            copyLinkButton.addEventListener('click', handleCopyLink);
        }
    }

    function handleShare(e) {
        e.preventDefault();
        
        const tournamentName = document.querySelector('.tournament-hero__title')?.textContent || 'Tournament';
        const url = window.location.href;

        // Check if Web Share API is available
        if (navigator.share) {
            navigator.share({
                title: tournamentName,
                text: `Check out this tournament: ${tournamentName}`,
                url: url,
            })
            .then(() => dcLog('Share successful'))
            .catch(error => dcLog('Share failed:', error));
        } else {
            // Fallback to copy link
            handleCopyLink(e);
        }
    }

    function handleCopyLink(e) {
        e.preventDefault();
        
        const url = window.location.href;
        
        // Copy to clipboard
        if (navigator.clipboard) {
            navigator.clipboard.writeText(url)
                .then(() => {
                    showToast('Link copied to clipboard!');
                })
                .catch(error => {
                    console.error('Copy failed:', error);
                    fallbackCopyToClipboard(url);
                });
        } else {
            fallbackCopyToClipboard(url);
        }
    }

    function fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            showToast('Link copied to clipboard!');
        } catch (error) {
            console.error('Fallback copy failed:', error);
            showToast('Failed to copy link');
        }
        
        document.body.removeChild(textArea);
    }

    // ==================== UTILITIES ====================
    function getCsrfToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    function showToast(message, duration = 3000) {
        // Check if toast container exists
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            `;
            document.body.appendChild(toastContainer);
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        toast.style.cssText = `
            background: rgba(0, 212, 255, 0.9);
            color: #000;
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            font-weight: 600;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
            animation: slideInRight 0.3s ease-out;
        `;

        toastContainer.appendChild(toast);

        // Remove after duration
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                toastContainer.removeChild(toast);
                if (toastContainer.children.length === 0) {
                    document.body.removeChild(toastContainer);
                }
            }, 300);
        }, duration);
    }

    // ==================== LIFECYCLE PHASE DETECTION ====================
    function detectLifecyclePhase() {
        if (!state.tournamentData) return null;

        const status = state.tournamentData.status;

        // Before tournament
        const beforeStatuses = [
            'draft',
            'pending_approval',
            'published',
            'registration_open',
            'registration_closed'
        ];

        // During tournament
        const duringStatuses = ['live'];

        // After tournament
        const afterStatuses = ['completed', 'archived'];

        if (beforeStatuses.includes(status)) return 'before';
        if (duringStatuses.includes(status)) return 'during';
        if (afterStatuses.includes(status)) return 'after';
        
        return null;
    }

    // ==================== CLEANUP ====================
    function cleanup() {
        // Clear all countdown intervals
        Object.values(state.countdownIntervals).forEach(interval => {
            clearInterval(interval);
        });
        state.countdownIntervals = {};

        // Clear lobby polling
        if (state.lobbyPollTimer) {
            clearInterval(state.lobbyPollTimer);
            state.lobbyPollTimer = null;
        }
    }

    // ==================== AUTO-INITIALIZATION ====================
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Cleanup on page unload
    window.addEventListener('beforeunload', cleanup);

    // Add animations to CSS
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);

})();
