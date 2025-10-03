/**
 * Tournament Countdown Timer
 * Displays real-time countdown for registration opening/closing and tournament start
 * 
 * Features:
 * - Live countdown updates every second
 * - Multiple countdown types (registration, start, check-in)
 * - Automatic state changes when countdown reaches zero
 * - Mobile-friendly display
 * - Accessibility support
 * 
 * Usage:
 * <div class="countdown-timer" 
 *      data-countdown-type="registration-open"
 *      data-target-time="2025-10-05T14:00:00Z"
 *      data-tournament-slug="tournament-slug">
 * </div>
 */

class CountdownTimer {
    constructor(element) {
        this.element = element;
        this.type = element.dataset.countdownType;
        this.targetTime = new Date(element.dataset.targetTime);
        this.tournamentSlug = element.dataset.tournamentSlug;
        this.intervalId = null;
        this.isExpired = false;

        // Validate target time
        if (isNaN(this.targetTime.getTime())) {
            console.error('[CountdownTimer] Invalid target time:', element.dataset.targetTime);
            this.renderError('Invalid time');
            return;
        }

        this.init();
    }

    /**
     * Initialize timer
     */
    init() {
        // Add countdown-specific class
        this.element.classList.add(`countdown-${this.type}`);
        
        // Start countdown
        this.update();
        this.intervalId = setInterval(() => this.update(), 1000);

        // Stop countdown when page is hidden (save resources)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stop();
            } else if (!this.isExpired) {
                this.start();
            }
        });
    }

    /**
     * Update countdown display
     */
    update() {
        const now = new Date();
        const diff = this.targetTime - now;

        // Check if countdown expired
        if (diff <= 0) {
            this.handleExpiry();
            return;
        }

        // Calculate time units
        const time = this.calculateTime(diff);
        
        // Render countdown
        this.render(time, diff);
    }

    /**
     * Calculate time units from milliseconds
     */
    calculateTime(ms) {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        return {
            days: days,
            hours: hours % 24,
            minutes: minutes % 60,
            seconds: seconds % 60,
            totalHours: hours,
            totalMinutes: minutes,
            totalSeconds: seconds
        };
    }

    /**
     * Render countdown display
     */
    render(time, diff) {
        // Add urgency class if less than 1 hour remaining
        if (diff < 3600000) { // 1 hour in ms
            this.element.classList.add('countdown-urgent');
        } else {
            this.element.classList.remove('countdown-urgent');
        }

        // Add critical class if less than 5 minutes remaining
        if (diff < 300000) { // 5 minutes in ms
            this.element.classList.add('countdown-critical');
        } else {
            this.element.classList.remove('countdown-critical');
        }

        // Choose display format based on time remaining
        let html = '';
        
        if (time.days > 0) {
            // Show days and hours
            html = this.renderLongFormat(time);
        } else if (time.totalHours > 0) {
            // Show hours, minutes, seconds
            html = this.renderMediumFormat(time);
        } else {
            // Show minutes and seconds
            html = this.renderShortFormat(time);
        }

        this.element.innerHTML = html;
    }

    /**
     * Render long format (days + hours)
     */
    renderLongFormat(time) {
        const label = this.getLabel();
        return `
            <div class="countdown-wrapper">
                <div class="countdown-label">${label}</div>
                <div class="countdown-display countdown-display-long">
                    <div class="countdown-unit">
                        <span class="countdown-value">${time.days}</span>
                        <span class="countdown-unit-label">${time.days === 1 ? 'day' : 'days'}</span>
                    </div>
                    <div class="countdown-separator">:</div>
                    <div class="countdown-unit">
                        <span class="countdown-value">${String(time.hours).padStart(2, '0')}</span>
                        <span class="countdown-unit-label">hrs</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render medium format (hours:minutes:seconds)
     */
    renderMediumFormat(time) {
        const label = this.getLabel();
        return `
            <div class="countdown-wrapper">
                <div class="countdown-label">${label}</div>
                <div class="countdown-display countdown-display-medium">
                    <div class="countdown-unit">
                        <span class="countdown-value">${String(time.hours).padStart(2, '0')}</span>
                        <span class="countdown-unit-label">h</span>
                    </div>
                    <div class="countdown-separator">:</div>
                    <div class="countdown-unit">
                        <span class="countdown-value">${String(time.minutes).padStart(2, '0')}</span>
                        <span class="countdown-unit-label">m</span>
                    </div>
                    <div class="countdown-separator">:</div>
                    <div class="countdown-unit">
                        <span class="countdown-value">${String(time.seconds).padStart(2, '0')}</span>
                        <span class="countdown-unit-label">s</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render short format (minutes:seconds)
     */
    renderShortFormat(time) {
        const label = this.getLabel();
        return `
            <div class="countdown-wrapper">
                <div class="countdown-label">${label}</div>
                <div class="countdown-display countdown-display-short">
                    <div class="countdown-unit">
                        <span class="countdown-value">${String(time.minutes).padStart(2, '0')}</span>
                        <span class="countdown-unit-label">min</span>
                    </div>
                    <div class="countdown-separator">:</div>
                    <div class="countdown-unit">
                        <span class="countdown-value">${String(time.seconds).padStart(2, '0')}</span>
                        <span class="countdown-unit-label">sec</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get label text based on countdown type
     */
    getLabel() {
        const labels = {
            'registration-open': 'Registration opens in',
            'registration-close': 'Registration closes in',
            'tournament-start': 'Tournament starts in',
            'check-in-start': 'Check-in opens in',
            'check-in-end': 'Check-in closes in',
            'match-start': 'Match starts in'
        };

        return labels[this.type] || 'Time remaining';
    }

    /**
     * Handle countdown expiry
     */
    handleExpiry() {
        if (this.isExpired) return;
        
        this.isExpired = true;
        this.stop();

        // Show expired message
        const expiredLabels = {
            'registration-open': 'Registration is now open!',
            'registration-close': 'Registration has closed',
            'tournament-start': 'Tournament has started!',
            'check-in-start': 'Check-in is now open!',
            'check-in-end': 'Check-in has closed',
            'match-start': 'Match has started!'
        };

        const message = expiredLabels[this.type] || 'Time expired';
        
        this.element.innerHTML = `
            <div class="countdown-expired">
                <i class="fa-solid fa-bell"></i>
                <span>${message}</span>
            </div>
        `;

        this.element.classList.add('countdown-expired-state');

        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('countdownExpired', {
            detail: {
                type: this.type,
                tournamentSlug: this.tournamentSlug,
                element: this.element
            }
        }));

        // If this is a state-changing countdown, trigger state update
        if (this.shouldTriggerStateUpdate()) {
            this.triggerStateUpdate();
        }
    }

    /**
     * Check if countdown expiry should trigger state update
     */
    shouldTriggerStateUpdate() {
        const triggerTypes = [
            'registration-open',
            'registration-close',
            'tournament-start',
            'check-in-start',
            'check-in-end'
        ];
        return triggerTypes.includes(this.type);
    }

    /**
     * Trigger tournament state update
     */
    triggerStateUpdate() {
        // If tournament state poller exists, trigger immediate poll
        if (window.tournamentPoller) {
            console.log('[CountdownTimer] Triggering state update after countdown expiry');
            window.tournamentPoller.poll();
        }

        // Trigger page refresh after a short delay to show updated state
        setTimeout(() => {
            console.log('[CountdownTimer] Refreshing page to show updated state');
            window.location.reload();
        }, 3000);
    }

    /**
     * Render error message
     */
    renderError(message) {
        this.element.innerHTML = `
            <div class="countdown-error">
                <i class="fa-solid fa-exclamation-triangle"></i>
                <span>${message}</span>
            </div>
        `;
    }

    /**
     * Start countdown
     */
    start() {
        if (!this.intervalId && !this.isExpired) {
            this.update();
            this.intervalId = setInterval(() => this.update(), 1000);
        }
    }

    /**
     * Stop countdown
     */
    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    /**
     * Destroy countdown
     */
    destroy() {
        this.stop();
        this.element.innerHTML = '';
        this.element.className = 'countdown-timer';
    }
}

/**
 * Initialize all countdown timers on page
 */
function initCountdownTimers() {
    const timers = [];
    const elements = document.querySelectorAll('.countdown-timer[data-target-time]');
    
    console.log(`[CountdownTimer] Found ${elements.length} countdown timer(s)`);

    elements.forEach((element, index) => {
        try {
            const timer = new CountdownTimer(element);
            timers.push(timer);
            console.log(`[CountdownTimer] Initialized timer ${index + 1}:`, {
                type: element.dataset.countdownType,
                target: element.dataset.targetTime
            });
        } catch (error) {
            console.error(`[CountdownTimer] Failed to initialize timer ${index + 1}:`, error);
        }
    });

    return timers;
}

// Auto-initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    const timers = initCountdownTimers();
    
    // Expose to global scope for debugging
    window.countdownTimers = timers;
});

// Listen for countdown expiry events
document.addEventListener('countdownExpired', (event) => {
    console.log('[CountdownTimer] Countdown expired:', event.detail);
});

// Export for use in other scripts
window.CountdownTimer = CountdownTimer;
window.initCountdownTimers = initCountdownTimers;
