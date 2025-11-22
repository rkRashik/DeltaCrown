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

    // Initialize matches tab filters
    initializeMatchesFilters();
    
    // Initialize match details modal
    initializeMatchModal();
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

/**
 * Initialize Matches tab filters
 * Handles status (live/upcoming/completed) and phase (group_stage/knockout_stage) filtering
 */
function initializeMatchesFilters() {
    const filtersContainer = document.getElementById('tdMatchesFilters');
    const matchesList = document.getElementById('tdMatchesList');
    
    if (!filtersContainer || !matchesList) {
        console.debug('[Detail] Matches filters not found - tab may not be active');
        return;
    }

    // Track active filters
    let activeStatus = 'all';
    let activePhase = 'all';

    // Get all filter chips
    const statusChips = filtersContainer.querySelectorAll('[data-filter-group="status"] .td-chip');
    const phaseChips = filtersContainer.querySelectorAll('[data-filter-group="phase"] .td-chip');
    
    // Get all match cards
    const matchCards = matchesList.querySelectorAll('.td-match-card');

    console.debug('[Detail] Matches filters found:', {
        statusChips: statusChips.length,
        phaseChips: phaseChips.length,
        matchCards: matchCards.length
    });

    /**
     * Apply filters to match cards
     */
    function applyFilters() {
        let visibleCount = 0;
        
        matchCards.forEach(card => {
            const cardStatus = card.getAttribute('data-status');
            const cardPhase = card.getAttribute('data-phase');
            
            const statusMatch = activeStatus === 'all' || cardStatus === activeStatus;
            const phaseMatch = activePhase === 'all' || cardPhase === activePhase;
            
            if (statusMatch && phaseMatch) {
                card.classList.remove('is-hidden');
                visibleCount++;
            } else {
                card.classList.add('is-hidden');
            }
        });

        console.debug('[Detail] Filters applied:', {
            activeStatus,
            activePhase,
            visibleCount,
            totalCards: matchCards.length
        });
    }

    /**
     * Handle status chip clicks
     */
    statusChips.forEach(chip => {
        chip.addEventListener('click', function() {
            const newStatus = this.getAttribute('data-status');
            
            // Toggle active state
            statusChips.forEach(c => c.classList.remove('is-active'));
            this.classList.add('is-active');
            
            // Update filter and apply
            activeStatus = newStatus;
            applyFilters();
            
            console.debug('[Detail] Status filter changed:', newStatus);
        });
    });

    /**
     * Handle phase chip clicks
     */
    phaseChips.forEach(chip => {
        chip.addEventListener('click', function() {
            const newPhase = this.getAttribute('data-phase');
            
            // Toggle active state
            phaseChips.forEach(c => c.classList.remove('is-active'));
            this.classList.add('is-active');
            
            // Update filter and apply
            activePhase = newPhase;
            applyFilters();
            
            console.debug('[Detail] Phase filter changed:', newPhase);
        });
    });

    console.debug('[Detail] Matches filters initialized');
}

/**
 * Initialize Match Details Modal
 * Handles opening/closing the modal and populating match data
 */
function initializeMatchModal() {
    const backdrop = document.getElementById('tdMatchModalBackdrop');
    const modal = backdrop ? backdrop.querySelector('.td-match-modal') : null;
    const closeBtn = modal ? modal.querySelector('.td-modal-close') : null;
    const matchCards = document.querySelectorAll('.td-match-card[data-match-json]');
    
    if (!backdrop || !modal || matchCards.length === 0) {
        console.debug('[Detail] Match modal elements not found');
        return;
    }
    
    console.debug('[Detail] Match modal found, initializing...', { matchCards: matchCards.length });
    
    /**
     * Open modal with match data
     */
    function openModal(matchData) {
        // Populate modal header
        document.getElementById('tdMatchModalTitle').textContent = matchData.stage_label || 'Match Details';
        document.getElementById('tdModalSubtitle').textContent = matchData.match_label || '';
        
        // Populate status pill
        const statusPill = document.getElementById('tdModalStatusPill');
        statusPill.textContent = matchData.status.toUpperCase();
        statusPill.className = 'td-modal-status-pill';
        if (matchData.is_live) {
            statusPill.classList.add('td-status-live');
        } else if (matchData.is_completed) {
            statusPill.classList.add('td-status-completed');
        } else {
            statusPill.classList.add('td-status-upcoming');
        }
        
        // Populate team 1
        const team1 = document.getElementById('tdModalTeam1');
        const team1Logo = document.getElementById('tdModalTeam1Logo');
        const team1Name = document.getElementById('tdModalTeam1Name');
        const team1Score = document.getElementById('tdModalTeam1Score');
        
        if (matchData.team1_logo) {
            team1Logo.innerHTML = `<img src="${matchData.team1_logo}" alt="${matchData.team1_name}">`;
        } else {
            const initials = matchData.team1_name.slice(0, 2).toUpperCase();
            team1Logo.innerHTML = `<div class="td-logo-placeholder">${initials}</div>`;
        }
        team1Name.textContent = matchData.team1_name;
        team1Score.textContent = matchData.score1 !== null ? matchData.score1 : '-';
        
        if (matchData.team1_is_winner) {
            team1.classList.add('is-winner');
        } else {
            team1.classList.remove('is-winner');
        }
        
        // Populate team 2
        const team2 = document.getElementById('tdModalTeam2');
        const team2Logo = document.getElementById('tdModalTeam2Logo');
        const team2Name = document.getElementById('tdModalTeam2Name');
        const team2Score = document.getElementById('tdModalTeam2Score');
        
        if (matchData.team2_logo) {
            team2Logo.innerHTML = `<img src="${matchData.team2_logo}" alt="${matchData.team2_name}">`;
        } else {
            const initials = matchData.team2_name.slice(0, 2).toUpperCase();
            team2Logo.innerHTML = `<div class="td-logo-placeholder">${initials}</div>`;
        }
        team2Name.textContent = matchData.team2_name;
        team2Score.textContent = matchData.score2 !== null ? matchData.score2 : '-';
        
        if (matchData.team2_is_winner) {
            team2.classList.add('is-winner');
        } else {
            team2.classList.remove('is-winner');
        }
        
        // Populate metadata
        const scheduleItem = document.getElementById('tdModalSchedule');
        if (matchData.starts_at) {
            scheduleItem.innerHTML = `<strong>📅 Schedule:</strong><br>${matchData.starts_at}`;
            if (matchData.starts_at_relative) {
                scheduleItem.innerHTML += `<br><em>${matchData.starts_at_relative}</em>`;
            }
        } else {
            scheduleItem.innerHTML = '<strong>📅 Schedule:</strong><br>TBD';
        }
        
        const bestOfItem = document.getElementById('tdModalBestOf');
        if (matchData.best_of) {
            bestOfItem.innerHTML = `<strong>🎮 Format:</strong><br>${matchData.best_of}`;
        } else {
            bestOfItem.innerHTML = '<strong>🎮 Format:</strong><br>Standard Match';
        }
        
        // Populate footer with stream/VOD links
        const footer = document.getElementById('tdModalFooter');
        footer.innerHTML = '';
        
        if (matchData.is_live && matchData.stream_url) {
            footer.innerHTML = `
                <a href="${matchData.stream_url}" class="td-link-watch" target="_blank" rel="noopener noreferrer">
                    <span class="td-link-icon">📺</span>
                    Watch Live Stream
                </a>
            `;
        } else if (matchData.is_completed && matchData.vod_url) {
            footer.innerHTML = `
                <a href="${matchData.vod_url}" class="td-link-vod" target="_blank" rel="noopener noreferrer">
                    <span class="td-link-icon">🎬</span>
                    Watch Replay
                </a>
            `;
        }
        
        // Show modal
        backdrop.removeAttribute('hidden');
        document.body.style.overflow = 'hidden'; // Prevent body scroll
        
        console.debug('[Detail] Modal opened for match:', matchData.id);
    }
    
    /**
     * Close modal
     */
    function closeModal() {
        backdrop.setAttribute('hidden', '');
        document.body.style.overflow = ''; // Restore body scroll
        console.debug('[Detail] Modal closed');
    }
    
    // Attach click handlers to match cards
    matchCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // Don't open modal if clicking on a link
            if (e.target.tagName === 'A' || e.target.closest('a')) {
                return;
            }
            
            try {
                const matchJson = card.getAttribute('data-match-json');
                const matchData = JSON.parse(matchJson);
                openModal(matchData);
            } catch (error) {
                console.error('[Detail] Failed to parse match data:', error);
            }
        });
    });
    
    // Close button handler
    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }
    
    // Backdrop click handler (click outside modal)
    backdrop.addEventListener('click', function(e) {
        if (e.target === backdrop) {
            closeModal();
        }
    });
    
    // Escape key handler
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !backdrop.hasAttribute('hidden')) {
            closeModal();
        }
    });
    
    console.debug('[Detail] Match modal initialized');
}

/**
 * Initialize sidebar share functionality
 * Handles copy link button
 */
function initializeSidebarShare() {
    const copyBtn = document.querySelector('.td-share-copy');
    
    if (!copyBtn) {
        return;
    }
    
    copyBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        
        const url = this.getAttribute('data-url') || window.location.href;
        const originalLabel = this.querySelector('.td-share-label').textContent;
        
        try {
            await navigator.clipboard.writeText(url);
            
            // Visual feedback
            this.classList.add('copied');
            this.querySelector('.td-share-icon').textContent = '✓';
            this.querySelector('.td-share-label').textContent = 'Link Copied!';
            
            // Reset after 2 seconds
            setTimeout(() => {
                this.classList.remove('copied');
                this.querySelector('.td-share-icon').textContent = '🔗';
                this.querySelector('.td-share-label').textContent = originalLabel;
            }, 2000);
            
            console.debug('[Detail] Link copied to clipboard:', url);
        } catch (error) {
            console.error('[Detail] Failed to copy link:', error);
            
            // Fallback: select text
            const tempInput = document.createElement('input');
            tempInput.value = url;
            document.body.appendChild(tempInput);
            tempInput.select();
            document.execCommand('copy');
            document.body.removeChild(tempInput);
            
            this.classList.add('copied');
            this.querySelector('.td-share-label').textContent = 'Link Copied!';
            setTimeout(() => {
                this.classList.remove('copied');
                this.querySelector('.td-share-label').textContent = originalLabel;
            }, 2000);
        }
    });
    
    console.debug('[Detail] Sidebar share initialized');
}

// Initialize sidebar share when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeSidebarShare);
} else {
    initializeSidebarShare();
}

/**
 * Initialize scroll-based animations for elements
 * Uses IntersectionObserver for performance
 */
function initializeScrollAnimations() {
    const animatedElements = document.querySelectorAll('.animate-fade-in');
    
    if (animatedElements.length === 0) {
        return;
    }
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.animationPlayState = 'running';
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '50px'
    });
    
    animatedElements.forEach(el => {
        el.style.animationPlayState = 'paused';
        observer.observe(el);
    });
    
    console.debug('[Detail] Scroll animations initialized for', animatedElements.length, 'elements');
}

// Initialize scroll animations
document.addEventListener('DOMContentLoaded', initializeScrollAnimations);

/**
 * Enhanced "Read More" functionality for expandable text
 */
document.addEventListener('click', function(e) {
    if (e.target.matches('[data-read-more]')) {
        e.preventDefault();
        const targetId = e.target.getAttribute('data-read-more');
        const targetElement = document.getElementById(targetId);
        
        if (targetElement) {
            targetElement.style.maxHeight = 'none';
            e.target.style.display = 'none';
        }
    }
});

console.log('[Detail] Enhanced tournament detail page JavaScript loaded successfully');
