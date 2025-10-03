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
        
        // DOM element selectors
        this.selectors = {
            registrationState: '[data-tournament-reg-state]',
            registrationButton: '[data-tournament-reg-button]',
            timeRemaining: '[data-tournament-time-remaining]',
            slotsInfo: '[data-tournament-slots]',
            statusBadge: '[data-tournament-status-badge]',
            phaseIndicator: '[data-tournament-phase]'
        };
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

        console.log('[TournamentPoller] State changed:', data);
        this.lastState = currentStateString;

        // Update UI elements
        this.updateRegistrationState(data.registration_state);
        this.updateStatusBadge(data);
        this.updateTimeRemaining(data.time_until_start);
        this.updateSlotsInfo(data);
        this.updateRegistrationButton(data);
        this.updatePhaseIndicator(data.phase);

        // Dispatch custom event for other components
        document.dispatchEvent(new CustomEvent('tournamentStateChanged', {
            detail: data
        }));
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
     * Update slots information
     */
    updateSlotsInfo(data) {
        const element = document.querySelector(this.selectors.slotsInfo);
        if (!element) return;

        const { registered_count, max_teams, available_slots, is_full } = data;
        
        if (is_full) {
            element.innerHTML = `<strong class="text-danger">Full</strong> (${registered_count}/${max_teams})`;
        } else if (available_slots > 0) {
            element.innerHTML = `<strong>${available_slots}</strong> slots available (${registered_count}/${max_teams})`;
        } else {
            element.textContent = `${registered_count} registered`;
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
