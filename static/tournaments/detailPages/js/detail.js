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
    
    // Initialize tab navigation
    initializeTabs();
    
    // Initialize countdown timers
    initializeCountdowns();
    
    // Initialize animated counters (prize pool, etc.)
    initializeCounters();
    
    // Initialize hover effects
    initializeHoverEffects();
    
    // Initialize Participants tab filtering
    initializeParticipantsFilters();
    
    // Initialize stage selector for multi-stage tournaments
    initializeStageSelector();
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
 * Handles tab switching with smooth transitions and URL hash support
 */
function initializeTabs() {
    const tabNav = document.querySelector('.td-tabs-rail-nav');
    const tabButtons = document.querySelectorAll('.td-tab-rail-item');
    const tabPanels = document.querySelectorAll('.td-tab-panel');
    
    if (!tabNav || tabButtons.length === 0 || tabPanels.length === 0) {
        console.log('[Detail] Tab navigation elements not found');
        return;
    }
    
    // Function to switch to a specific tab
    const switchTab = (tabId) => {
        // Update buttons
        tabButtons.forEach(btn => {
            const isActive = btn.getAttribute('data-tab') === tabId;
            btn.classList.toggle('is-active', isActive);
        });
        
        // Update panels
        tabPanels.forEach(panel => {
            const isActive = panel.getAttribute('data-tab') === tabId;
            panel.classList.toggle('is-active', isActive);
        });
        
        // Update URL hash without triggering scroll
        if (history.replaceState) {
            history.replaceState(null, null, `#${tabId}`);
        } else {
            window.location.hash = tabId;
        }
        
        console.log(`[Detail] Switched to tab: ${tabId}`);
    };
    
    // Add click handlers to tab buttons
    tabButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = button.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
    
    // Check URL hash on load and switch to that tab if present
    const hashTab = window.location.hash.substring(1);
    if (hashTab) {
        const matchingButton = Array.from(tabButtons).find(
            btn => btn.getAttribute('data-tab') === hashTab
        );
        if (matchingButton) {
            switchTab(hashTab);
        } else {
            // Hash doesn't match any tab, show overview
            switchTab('overview');
        }
    } else {
        // No hash, show overview by default
        switchTab('overview');
    }
    
    // Listen for hash changes (browser back/forward buttons)
    window.addEventListener('hashchange', () => {
        const newHashTab = window.location.hash.substring(1);
        if (newHashTab) {
            const matchingButton = Array.from(tabButtons).find(
                btn => btn.getAttribute('data-tab') === newHashTab
            );
            if (matchingButton) {
                switchTab(newHashTab);
            }
        }
    });
    
    console.log(`[Detail] Initialized tab navigation with ${tabButtons.length} tabs`);
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
    // Animate prize amounts on Prizes tab
    const prizeElements = document.querySelectorAll('[data-amount]');
    
    if (prizeElements.length === 0) {
        console.log('[Detail] No counter elements found');
        return;
    }
    
    // Check if Prizes tab is visible
    const prizesTab = document.querySelector('[data-tab="prizes"]');
    if (!prizesTab || !prizesTab.classList.contains('is-active')) {
        // Set up observer to animate when tab becomes active
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.target.classList.contains('is-active')) {
                    animatePrizeCounters();
                    observer.disconnect();
                }
            });
        });
        
        if (prizesTab) {
            observer.observe(prizesTab, { attributes: true, attributeFilter: ['class'] });
        }
        return;
    }
    
    // Tab is already active, animate immediately
    animatePrizeCounters();
}

/**
 * Animate prize counter numbers
 */
function animatePrizeCounters() {
    const prizeElements = document.querySelectorAll('[data-amount]');
    
    prizeElements.forEach(element => {
        const targetAmount = parseFloat(element.getAttribute('data-amount'));
        if (isNaN(targetAmount)) return;
        
        const duration = 1500; // 1.5 seconds
        const startTime = performance.now();
        
        function updateCounter(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function (ease-out cubic)
            const eased = 1 - Math.pow(1 - progress, 3);
            const currentValue = Math.floor(targetAmount * eased);
            
            // Update the text content (preserve the rest of the HTML)
            const currentText = element.textContent;
            const numberMatch = currentText.match(/[\d,]+/);
            if (numberMatch) {
                const formattedValue = currentValue.toLocaleString();
                element.textContent = currentText.replace(/[\d,]+/, formattedValue);
            }
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        }
        
        requestAnimationFrame(updateCounter);
    });
    
    console.log(`[Detail] Animated ${prizeElements.length} prize counter(s)`);
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

/**
 * Initialize Participants Tab Filtering
 * Client-side filtering for search, status, and region
 */
function initializeParticipantsFilters() {
    const searchInput = document.getElementById('participantSearch');
    const statusFilter = document.getElementById('statusFilter');
    const regionFilter = document.getElementById('regionFilter');
    const clearButton = document.getElementById('clearFilters');
    const participantsGrid = document.getElementById('participantsGrid');
    
    if (!participantsGrid) {
        console.log('[Detail] Participants grid not found - skipping filter initialization');
        return;
    }
    
    console.log('[Detail] Initializing participants filters');
    
    // Get all participant cards
    const getAllCards = () => Array.from(participantsGrid.querySelectorAll('.td-participant-card'));
    
    // Filter function
    const applyFilters = () => {
        const cards = getAllCards();
        const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
        const selectedStatus = statusFilter ? statusFilter.value.toLowerCase() : '';
        const selectedRegion = regionFilter ? regionFilter.value.toUpperCase() : '';
        
        let visibleCount = 0;
        
        cards.forEach(card => {
            const name = card.getAttribute('data-name') || '';
            const status = card.getAttribute('data-status') || '';
            const checkedIn = card.getAttribute('data-checked-in') === 'true';
            const region = card.getAttribute('data-region') || '';
            
            // Search filter
            const matchesSearch = !searchTerm || name.includes(searchTerm);
            
            // Status filter
            let matchesStatus = !selectedStatus || status === selectedStatus;
            if (selectedStatus === 'checked-in') {
                matchesStatus = checkedIn;
            }
            
            // Region filter
            const matchesRegion = !selectedRegion || region === selectedRegion;
            
            // Show/hide card
            const isVisible = matchesSearch && matchesStatus && matchesRegion;
            card.classList.toggle('is-hidden', !isVisible);
            
            if (isVisible) visibleCount++;
        });
        
        console.log(`[Detail] Filtered: ${visibleCount} of ${cards.length} participants visible`);
        
        // Show empty state if no results
        showEmptyState(visibleCount === 0 && cards.length > 0);
    };
    
    // Show/hide empty state for no results
    const showEmptyState = (show) => {
        let emptyState = participantsGrid.parentElement.querySelector('.td-no-results-state');
        
        if (show && !emptyState) {
            emptyState = document.createElement('div');
            emptyState.className = 'td-empty-state td-no-results-state';
            emptyState.innerHTML = `
                <div class="td-empty-icon">🔍</div>
                <h3 class="td-empty-title">No Matches Found</h3>
                <p class="td-empty-message">
                    Try adjusting your filters or search terms.
                </p>
            `;
            participantsGrid.parentElement.insertBefore(emptyState, participantsGrid.nextSibling);
            participantsGrid.style.display = 'none';
        } else if (!show && emptyState) {
            emptyState.remove();
            participantsGrid.style.display = '';
        }
    };
    
    // Clear all filters
    const clearFilters = () => {
        if (searchInput) searchInput.value = '';
        if (statusFilter) statusFilter.value = '';
        if (regionFilter) regionFilter.value = '';
        applyFilters();
        console.log('[Detail] Filters cleared');
    };
    
    // Attach event listeners
    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', applyFilters);
    }
    
    if (regionFilter) {
        regionFilter.addEventListener('change', applyFilters);
    }
    
    if (clearButton) {
        clearButton.addEventListener('click', clearFilters);
    }
    
    console.log('[Detail] Participants filters initialized successfully');
}

/**
 * Initialize stage selector for multi-stage tournaments
 * Handles switching between group stage and knockout stage views
 */
function initializeStageSelector() {
    const selector = document.querySelector('.td-stage-selector');
    if (!selector) {
        console.debug('[Detail] No stage selector found - single-stage tournament or bracket tab not active');
        return;
    }
    
    const pills = selector.querySelectorAll('.td-stage-pill');
    const panels = document.querySelectorAll('.td-stage-panel');
    
    if (pills.length === 0 || panels.length === 0) {
        console.warn('[Detail] Stage selector found but pills or panels missing', {pills: pills.length, panels: panels.length});
        return;
    }
    
    pills.forEach((pill) => {
        pill.addEventListener('click', () => {
            const target = pill.getAttribute('data-stage-target');
            const disabled = pill.getAttribute('data-disabled-stage') === 'true';
            
            if (!target) {
                console.warn('[Detail] Stage pill missing data-stage-target attribute');
                return;
            }
            
            if (disabled) {
                console.debug('[Detail] Stage disabled:', target);
                return;
            }
            
            // Update active state on pills
            pills.forEach((p) => p.classList.remove('is-active'));
            pill.classList.add('is-active');
            
            // Update active state on panels
            panels.forEach((panel) => {
                if (panel.getAttribute('data-stage-panel') === target) {
                    panel.classList.add('is-active');
                } else {
                    panel.classList.remove('is-active');
                }
            });
            
            console.debug(`[Detail] Switched to stage: ${target}`);
        });
    });
    
    console.debug('[Detail] Stage selector initialized with', pills.length, 'stages');
}
