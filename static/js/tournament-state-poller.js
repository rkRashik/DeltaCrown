/**
 * Tournament State Poller - Live Updates for Tournament Detail Page
 * 
 * Polls the tournament state API every 30 seconds to update:
 * - Registration state (open, closed, full, started, etc.)
 * - Time remaining until start
 * - Available slots
 * - Registration button state
 * 
 * Usage: Include this script on tournament detail pages with data-tournament-slug attribute
 */

class TournamentStatePoller {
    constructor(tournamentSlug) {
        this.slug = tournamentSlug;
        this.pollInterval = 30000; // 30 seconds
        this.intervalId = null;
        this.lastState = null;
        this.notificationSound = null;
        
        // DOM element selectors
        this.selectors = {
            registrationState: '[data-tournament-reg-state]',
            registrationButton: '[data-tournament-reg-button]',
            timeRemaining: '[data-tournament-time-remaining]',
            slotsInfo: '[data-tournament-slots]',
            statusBadge: '[data-tournament-status-badge]',
            phaseIndicator: '[data-tournament-phase]',
            participantCount: '[data-tournament-participants]'
        };
        
        // Initialize notification sound (optional)
        this.initNotificationSound();
    }

    /**
     * Initialize notification sound for capacity updates
     */
    initNotificationSound() {
        try {
            // Create a subtle notification sound (optional, can be disabled)
            this.notificationSound = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBTGH0fPTgjMGHm7A7+OZUQ4PVqjo8bVoHwU7k9n0yHkqBSl+zPDhlEILElyx6+yrWRUJR6Lh8rprIgUuhc70z4M0Bhxuv+/nmVEODlaE6PC1ah8FO5XZ9cp5KwUpfsrw4ZRCCxJcrunuq1kVCUek4vK6bCEFLoXO9c+DNQYcbr/w55lRDg5WhOjwtWofBTyV2vXKeSsFKn7K8OGVRA==');
            this.notificationSound.volume = 0.3;
        } catch (error) {
            console.warn('[TournamentPoller] Could not initialize notification sound:', error);
        }
    }

    /**
     * Play notification sound
     */
    playNotification() {
        if (this.notificationSound && document.hasFocus()) {
            try {
                this.notificationSound.currentTime = 0;
                this.notificationSound.play().catch(() => {
                    // Silently fail if audio playback is blocked
                });
            } catch (error) {
                // Ignore audio errors
            }
        }
    }

    /**
     * Start polling for state updates
     */
    start() {
        if (this.intervalId) {
            console.warn('[TournamentPoller] Already polling');
            return;
        }

        console.log(`[TournamentPoller] Starting poller for: ${this.slug}`);
        
        // Poll immediately, then every 30 seconds
        this.poll();
        this.intervalId = setInterval(() => this.poll(), this.pollInterval);
    }

    /**
     * Stop polling
     */
    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
            console.log('[TournamentPoller] Stopped polling');
        }
    }

    /**
     * Fetch current state from API
     */
    async poll() {
        try {
            const response = await fetch(`/tournaments/api/${this.slug}/state/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                console.error(`[TournamentPoller] API error: ${response.status}`);
                return;
            }

            const data = await response.json();
            this.handleStateUpdate(data);
        } catch (error) {
            console.error('[TournamentPoller] Fetch error:', error);
        }
    }

    /**
     * Handle state update from API
     */
    handleStateUpdate(data) {
        // Check if state changed
        const currentStateString = JSON.stringify(data);
        if (this.lastState === currentStateString) {
            console.log('[TournamentPoller] No state change');
            return;
        }

        // Check if capacity changed (for notifications)
        const previousState = this.lastState ? JSON.parse(this.lastState) : null;
        const capacityChanged = previousState && 
            (previousState.registered_count !== data.registered_count ||
             previousState.available_slots !== data.available_slots);

        console.log('[TournamentPoller] State changed:', data);
        this.lastState = currentStateString;

        // Update UI elements
        this.updateRegistrationState(data.registration_state);
        this.updateStatusBadge(data);
        this.updateTimeRemaining(data.time_until_start);
        this.updateSlotsInfo(data);
        this.updateRegistrationButton(data);
        this.updatePhaseIndicator(data.phase);
        this.updateParticipantCount(data);

        // Play notification if capacity changed
        if (capacityChanged) {
            this.playNotification();
            
            // Show browser notification if available slots are low
            if (data.available_slots > 0 && data.available_slots <= 5) {
                this.showBrowserNotification(data);
            }
        }

        // Dispatch custom event for other components
        document.dispatchEvent(new CustomEvent('tournamentStateChanged', {
            detail: {
                ...data,
                capacityChanged: capacityChanged
            }
        }));
    }

    /**
     * Update participant count display
     */
    updateParticipantCount(data) {
        const element = document.querySelector(this.selectors.participantCount);
        if (!element) return;

        const { registered_count, max_teams } = data;
        element.innerHTML = `<strong>${registered_count}</strong>/${max_teams}`;
    }

    /**
     * Show browser notification for low availability
     */
    showBrowserNotification(data) {
        // Check if notifications are supported and permitted
        if (!('Notification' in window)) return;

        // Request permission if not already granted
        if (Notification.permission === 'default') {
            Notification.requestPermission();
            return;
        }

        // Show notification if permitted
        if (Notification.permission === 'granted') {
            const { available_slots, dc_title } = data;
            new Notification(`${dc_title || 'Tournament'}`, {
                body: `Only ${available_slots} slot${available_slots === 1 ? '' : 's'} remaining!`,
                icon: '/static/logos/deltacrown-icon.png',
                tag: `tournament-${this.slug}`,
                requireInteraction: false
            });
        }
    }

    /**
     * Update registration state text
     */
    updateRegistrationState(state) {
        const element = document.querySelector(this.selectors.registrationState);
        if (!element) return;

        const stateMap = {
            'not_open': { text: 'Registration Not Open Yet', class: 'text-warning' },
            'open': { text: 'Registration Open', class: 'text-success' },
            'closed': { text: 'Registration Closed', class: 'text-danger' },
            'full': { text: 'Tournament Full', class: 'text-info' },
            'started': { text: 'Tournament Started', class: 'text-secondary' },
            'completed': { text: 'Tournament Completed', class: 'text-muted' }
        };

        const config = stateMap[state] || { text: state, class: '' };
        element.textContent = config.text;
        element.className = `tournament-state ${config.class}`;
    }

    /**
     * Update status badge
     */
    updateStatusBadge(data) {
        const element = document.querySelector(this.selectors.statusBadge);
        if (!element) return;

        const badgeMap = {
            'not_open': { text: 'Upcoming', class: 'badge-warning' },
            'open': { text: 'Open for Registration', class: 'badge-success' },
            'closed': { text: 'Registration Closed', class: 'badge-danger' },
            'full': { text: 'Full', class: 'badge-info' },
            'started': { text: 'In Progress', class: 'badge-primary' },
            'completed': { text: 'Completed', class: 'badge-secondary' }
        };

        const config = badgeMap[data.registration_state] || { text: data.phase, class: 'badge-light' };
        element.innerHTML = `<span class="badge ${config.class}">${config.text}</span>`;
    }

    /**
     * Update time remaining display
     */
    updateTimeRemaining(timeRemaining) {
        const element = document.querySelector(this.selectors.timeRemaining);
        if (!element || !timeRemaining) return;

        element.textContent = timeRemaining;
    }

    /**
     * Update slots information with animated capacity bar
     */
    updateSlotsInfo(data) {
        const element = document.querySelector(this.selectors.slotsInfo);
        if (!element) return;

        const { registered_count, max_teams, available_slots, is_full } = data;
        
        // Calculate fill percentage
        const fillPercentage = max_teams > 0 ? (registered_count / max_teams * 100) : 0;
        
        // Determine capacity state
        let capacityState = 'plenty';
        let capacityClass = 'capacity-plenty';
        if (is_full) {
            capacityState = 'full';
            capacityClass = 'capacity-full';
        } else if (fillPercentage >= 90) {
            capacityState = 'critical';
            capacityClass = 'capacity-critical';
        } else if (fillPercentage >= 75) {
            capacityState = 'low';
            capacityClass = 'capacity-low';
        }

        // Check if slots changed (for animation)
        const previousCount = parseInt(element.dataset.previousCount || '0');
        const slotsChanged = registered_count !== previousCount;
        
        // Build HTML with capacity bar
        const html = `
            <div class="capacity-info ${capacityClass}">
                <div class="capacity-text">
                    ${is_full 
                        ? `<span class="capacity-label">Full</span> <strong class="text-danger">${registered_count}/${max_teams}</strong>`
                        : `<span class="capacity-label">Slots:</span> <strong class="${available_slots <= 3 ? 'text-warning' : ''}">${available_slots}</strong> available (<span class="registered-count ${slotsChanged ? 'count-updated' : ''}">${registered_count}</span>/${max_teams})`
                    }
                </div>
                <div class="capacity-bar" role="progressbar" aria-valuenow="${fillPercentage}" aria-valuemin="0" aria-valuemax="100" aria-label="Tournament capacity">
                    <div class="capacity-fill" style="width: ${fillPercentage}%"></div>
                </div>
                ${available_slots > 0 && available_slots <= 3 
                    ? `<div class="capacity-warning"><i class="fa-solid fa-exclamation-triangle"></i> Only ${available_slots} slot${available_slots === 1 ? '' : 's'} left!</div>`
                    : ''
                }
            </div>
        `;
        
        element.innerHTML = html;
        element.dataset.previousCount = registered_count;
        
        // Add animation class if slots changed
        if (slotsChanged) {
            element.classList.add('slots-updated');
            setTimeout(() => {
                element.classList.remove('slots-updated');
                const countElement = element.querySelector('.registered-count');
                if (countElement) {
                    countElement.classList.remove('count-updated');
                }
            }, 1000);
        }
    }

    /**
     * Update registration button state
     */
    updateRegistrationButton(data) {
        const container = document.getElementById('hero-registration-btn');
        if (!container) return;

        const { button_state, button_text, user_registered } = data;

        // Re-render button using the existing renderer from tournament-detail-modern.js
        if (window.TournamentDetailModern && window.TournamentDetailModern.renderDetailButton) {
            const context = {
                button_state: button_state,
                button_text: button_text,
                message: data.time_until_start || ''
            };
            
            window.TournamentDetailModern.renderDetailButton(container, context, this.slug, 'large');
        } else {
            // Fallback: direct button update if renderer not available
            const button = container.querySelector('button, a');
            if (button) {
                // Update text
                const textNode = Array.from(button.childNodes).find(node => node.nodeType === Node.TEXT_NODE);
                if (textNode) {
                    textNode.textContent = ` ${button_text}`;
                } else {
                    button.innerHTML = `<i class="fa-solid fa-user-plus"></i> ${button_text}`;
                }

                // Update state classes
                const stateClasses = {
                    'register': 'btn-success',
                    'registered': 'btn-info',
                    'not_authenticated': 'btn-primary',
                    'closed': 'btn-secondary',
                    'started': 'btn-secondary',
                    'full': 'btn-secondary'
                };

                // Remove old classes
                Object.values(stateClasses).forEach(cls => button.classList.remove(cls));
                
                // Add new class
                if (stateClasses[button_state]) {
                    button.classList.add(stateClasses[button_state]);
                }

                // Handle disabled state
                button.disabled = !['register', 'not_authenticated', 'request_approval'].includes(button_state);
            }
        }

        // Add visual feedback class
        container.classList.add('state-updated');
        setTimeout(() => container.classList.remove('state-updated'), 500);
    }

    /**
     * Update tournament phase indicator
     */
    updatePhaseIndicator(phase) {
        const element = document.querySelector(this.selectors.phaseIndicator);
        if (!element) return;

        const phaseMap = {
            'draft': { text: 'Draft', class: 'phase-draft' },
            'registration': { text: 'Registration Phase', class: 'phase-registration' },
            'live': { text: 'Live Tournament', class: 'phase-live' },
            'completed': { text: 'Completed', class: 'phase-completed' }
        };

        const config = phaseMap[phase] || { text: phase, class: '' };
        element.textContent = config.text;
        element.className = `tournament-phase ${config.class}`;
    }
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const tournamentElement = document.querySelector('[data-tournament-slug]');
    
    if (tournamentElement) {
        const slug = tournamentElement.getAttribute('data-tournament-slug');
        const poller = new TournamentStatePoller(slug);
        
        // Start polling
        poller.start();

        // Stop polling when page is hidden (save resources)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                poller.stop();
            } else {
                poller.start();
            }
        });

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            poller.stop();
        });

        // Expose to global scope for debugging
        window.tournamentPoller = poller;
    }
});
