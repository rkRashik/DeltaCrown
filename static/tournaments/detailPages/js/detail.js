/**
 * Tournament Detail Page - Main JavaScript
 * 
 * Purpose: Tab switching, theme initialization, countdown timers, animated counters
 * Dependencies: None (vanilla JS)
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('[Detail] Tournament Detail Page - Main JS loaded');
    
    // Initialize game theme
    initializeTheme();
    
    // Initialize countdown timers
    initializeCountdowns();
    
    // Initialize animated counters (prize pool, etc.)
    initializeCounters();
    
    // Initialize hover effects
    initializeHoverEffects();
    
    // Tab navigation will be initialized when tabs are implemented
    // initializeTabs();
});

/**
 * Initialize game-based theme
 * Reads data-game-slug attribute and applies theme
 */
function initializeTheme() {
    const container = document.querySelector('[data-game-slug]');
    if (container) {
        const gameSlug = container.getAttribute('data-game-slug');
        console.log(`[Detail] Theme applied for game: ${gameSlug}`);
        
        // Theme is applied via CSS [data-game-slug] selector
        // No additional JS needed - CSS variables handle everything
    } else {
        console.log('[Detail] No data-game-slug found, using default theme');
    }
}

/**
 * Initialize tab navigation
 * Handles tab switching with smooth transitions
 */
function initializeTabs() {
    // Tab switching logic will be added here when tabs are implemented
    console.log('[Detail] Tab navigation initialization placeholder');
}

/**
 * Initialize countdown timers
 * Handles registration/tournament start countdowns
 */
function initializeCountdowns() {
    const countdownElements = document.querySelectorAll('.countdown-timer[data-target]');
    
    if (countdownElements.length === 0) {
        console.log('[Detail] No countdown timers found');
        return;
    }
    
    countdownElements.forEach(countdown => {
        const targetDate = new Date(countdown.getAttribute('data-target'));
        const valueSpan = countdown.querySelector('.countdown-value');
        
        if (!valueSpan) {
            console.warn('[Detail] Countdown timer missing .countdown-value element');
            return;
        }
        
        // Update countdown every second
        const updateCountdown = () => {
            const now = new Date();
            const diff = targetDate - now;
            
            if (diff <= 0) {
                valueSpan.textContent = 'Starting soon!';
                clearInterval(intervalId);
                return;
            }
            
            const time = getTimeRemaining(diff);
            valueSpan.textContent = formatTimeRemaining(time);
        };
        
        // Initial update
        updateCountdown();
        
        // Update every second
        const intervalId = setInterval(updateCountdown, 1000);
    });
    
    console.log(`[Detail] Initialized ${countdownElements.length} countdown timer(s)`);
}

/**
 * Initialize animated number counters
 * Animates prize pool and other numeric displays
 */
function initializeCounters() {
    // Number counter animation logic will be added here when prize pool is implemented
    console.log('[Detail] Counter animation initialization placeholder');
}

/**
 * Initialize hover effects
 * Adds interactive hover behaviors to cards and buttons
 */
function initializeHoverEffects() {
    // Add hover class to CTA button for potential animation hooks
    const ctaButtons = document.querySelectorAll('.hero-cta:not([disabled])');
    
    ctaButtons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.classList.add('is-hovering');
        });
        
        button.addEventListener('mouseleave', function() {
            this.classList.remove('is-hovering');
        });
    });
    
    console.log(`[Detail] Initialized hover effects for ${ctaButtons.length} interactive element(s)`);
}

/**
 * Helper: Calculate time remaining from milliseconds
 * @param {number} ms - Milliseconds until target time
 * @returns {Object} - Object with days, hours, minutes, seconds
 */
function getTimeRemaining(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    return {
        days: days,
        hours: hours % 24,
        minutes: minutes % 60,
        seconds: seconds % 60,
        total: ms
    };
}

/**
 * Helper: Format time remaining for display
 * @param {Object} time - Time object from getTimeRemaining
 * @returns {string} - Formatted time string
 */
function formatTimeRemaining(time) {
    if (time.days > 0) {
        return `${time.days}d ${time.hours}h ${time.minutes}m`;
    } else if (time.hours > 0) {
        return `${time.hours}h ${time.minutes}m`;
    } else if (time.minutes > 0) {
        return `${time.minutes}m ${time.seconds}s`;
    } else {
        return `${time.seconds}s`;
    }
}

/**
 * Helper: Animate number from start to end
 * @param {HTMLElement} element - Element to animate
 * @param {number} start - Starting value
 * @param {number} end - Ending value
 * @param {number} duration - Animation duration in ms
 */
function animateNumber(element, start, end, duration) {
    // Number animation logic will be added here when needed
    console.log('[Detail] Number animation placeholder');
}
