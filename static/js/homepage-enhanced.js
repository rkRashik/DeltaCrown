/**
 * DeltaCrown Enhanced Homepage JavaScript
 * Premium E-sports Experience with Live Feed and Interactive Elements
 */

class DeltaCrownHomepage {
    constructor() {
        this.theme = this.getStoredTheme();
        this.liveFeedData = [];
        this.autoRefresh = true;
        this.autoRefreshInterval = null;
        this.init();
    }

    init() {
        this.setTheme(this.theme);
        this.initThemeToggle();
        this.initAccessibility();
        this.initAnimations();
        this.initInteractions();
        this.initLiveFeed();
        this.initGameCardEffects();
        this.bindEvents();
        this.injectStyles();
    }

    // Theme Management - Default to Dark for E-sports Experience
    getStoredTheme() {
        const stored = localStorage.getItem('deltacrown-theme');
        if (stored) return stored;
        
        // Default to dark theme for premium e-sports experience
        return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }

    setTheme(theme) {
        this.theme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('deltacrown-theme', theme);
        
        // Update meta theme-color for mobile browsers
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (metaThemeColor) {
            metaThemeColor.setAttribute('content', theme === 'dark' ? '#0f172a' : '#ffffff');
        }
        
        // Dispatch theme change event for other components
        window.dispatchEvent(new CustomEvent('themeChange', { detail: { theme } }));
    }

    toggleTheme() {
        const newTheme = this.theme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
        this.announceToScreenReader(`Switched to ${newTheme} mode`);
    }

    initThemeToggle() {
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
            
            // Update button state
            this.updateThemeToggleState(themeToggle);
        }
    }

    updateThemeToggleState(toggle) {
        const lightIcon = toggle.querySelector('.light-icon');
        const darkIcon = toggle.querySelector('.dark-icon');
        
        if (this.theme === 'dark') {
            lightIcon?.classList.add('active');
            darkIcon?.classList.remove('active');
        } else {
            lightIcon?.classList.remove('active');
            darkIcon?.classList.add('active');
        }
    }

    // Accessibility Features
    initAccessibility() {
        this.setupSkipLinks();
        this.setupKeyboardNavigation();
        this.setupScreenReaderSupport();
        this.setupFocusManagement();
    }

    setupSkipLinks() {
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.textContent = 'Skip to main content';
        skipLink.className = 'skip-link';
        document.body.insertBefore(skipLink, document.body.firstChild);
    }

    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
    }

    setupScreenReaderSupport() {
        // Add aria-live region for announcements
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        announcer.id = 'announcer';
        document.body.appendChild(announcer);
    }

    setupFocusManagement() {
        // Enhanced focus indicators for interactive elements
        const focusableElements = document.querySelectorAll(
            'a, button, input, textarea, select, details, [tabindex]:not([tabindex="-1"])'
        );

        focusableElements.forEach(element => {
            element.addEventListener('focus', () => {
                element.setAttribute('data-focused', 'true');
            });

            element.addEventListener('blur', () => {
                element.removeAttribute('data-focused');
            });
        });
    }

    announceToScreenReader(message) {
        const announcer = document.getElementById('announcer');
        if (announcer) {
            announcer.textContent = message;
            setTimeout(() => {
                announcer.textContent = '';
            }, 1000);
        }
    }

    // Animation System
    initAnimations() {
        this.setupScrollAnimations();
        this.setupCounterAnimations();
        this.setupIntersectionObserver();
    }

    setupScrollAnimations() {
        if ('IntersectionObserver' in window) {
            const animationObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animate-in');
                        
                        // Trigger counter animations for stat elements
                        if (entry.target.classList.contains('stat-number')) {
                            this.animateCounter(entry.target);
                        }
                    }
                });
            }, {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            });

            // Observe elements for animation
            const animatable = document.querySelectorAll(
                '.hero-section, .section-header, .game-card, .tournament-card, .team-card, .feature-card'
            );
            animatable.forEach(el => animationObserver.observe(el));
        }
    }

    setupCounterAnimations() {
        const counters = document.querySelectorAll('.stat-number');
        counters.forEach(counter => {
            counter.setAttribute('data-target', counter.textContent);
        });
    }

    animateCounter(element) {
        const target = element.getAttribute('data-target');
        const numericValue = parseInt(target.replace(/[^\d]/g, '')) || 0;
        const prefix = target.match(/^[^\d]*/)?.[0] || '';
        const suffix = target.match(/[^\d]*$/)?.[0] || '';

        let current = 0;
        const increment = numericValue / 50;
        const timer = setInterval(() => {
            current += increment;
            if (current >= numericValue) {
                current = numericValue;
                clearInterval(timer);
            }
            element.textContent = prefix + Math.floor(current).toLocaleString() + suffix;
        }, 40);
    }

    setupIntersectionObserver() {
        // Lazy loading for images
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.classList.add('loaded');
                            imageObserver.unobserve(img);
                        }
                    }
                });
            });

            const lazyImages = document.querySelectorAll('img[data-src]');
            lazyImages.forEach(img => imageObserver.observe(img));
        }
    }

    // Interactive Elements
    initInteractions() {
        this.setupButtonEffects();
        this.setupCardHovers();
        this.setupTooltips();
    }

    setupButtonEffects() {
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.createRippleEffect(button, e);
            });
        });
    }

    setupCardHovers() {
        const cards = document.querySelectorAll('.game-card, .tournament-card, .team-card');
        cards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.zIndex = '10';
            });

            card.addEventListener('mouseleave', () => {
                card.style.zIndex = '';
            });
        });
    }

    setupTooltips() {
        const tooltipElements = document.querySelectorAll('[data-tooltip]');
        tooltipElements.forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target, e.target.getAttribute('data-tooltip'));
            });

            element.addEventListener('mouseleave', () => {
                this.hideTooltip();
            });
        });
    }

    createRippleEffect(element, event) {
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        const ripple = document.createElement('span');
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            transform: scale(0);
            animation: ripple 0.6s linear;
            pointer-events: none;
        `;

        element.style.position = 'relative';
        element.style.overflow = 'hidden';
        element.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    showTooltip(element, text) {
        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = text;
        tooltip.setAttribute('role', 'tooltip');

        const rect = element.getBoundingClientRect();
        tooltip.style.cssText = `
            position: fixed;
            background: var(--color-surface);
            color: var(--color-text-primary);
            padding: var(--space-sm) var(--space-md);
            border-radius: var(--radius-md);
            font-size: var(--text-sm);
            z-index: var(--z-tooltip);
            left: ${rect.left + rect.width / 2}px;
            top: ${rect.top - 8}px;
            transform: translateX(-50%) translateY(-100%);
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--color-border);
        `;

        document.body.appendChild(tooltip);
        this.currentTooltip = tooltip;
    }

    hideTooltip() {
        if (this.currentTooltip) {
            this.currentTooltip.remove();
            this.currentTooltip = null;
        }
    }

    // Live Tournament Feed System
    initLiveFeed() {
        this.feedContainer = document.getElementById('live-feed');
        this.refreshButton = document.getElementById('refresh-feed');
        this.autoRefreshToggle = document.getElementById('auto-refresh-toggle');
        
        if (this.feedContainer) {
            this.setupFeedControls();
            this.loadInitialFeedData();
            this.startAutoRefresh();
        }
    }
    
    setupFeedControls() {
        if (this.refreshButton) {
            this.refreshButton.addEventListener('click', () => {
                this.refreshFeed();
            });
        }
        
        if (this.autoRefreshToggle) {
            this.autoRefreshToggle.addEventListener('click', () => {
                this.toggleAutoRefresh();
            });
        }
    }
    
    loadInitialFeedData() {
        // Simulate initial live feed data
        this.liveFeedData = [
            {
                id: 1,
                type: 'live',
                icon: 'fas fa-play-circle',
                title: 'Valorant Championship Finals - LIVE',
                description: 'DeltaElite vs Phoenix Rising - Map 3: Haven',
                time: 'Live now',
                game: 'Valorant',
                meta: 'Round 12-10'
            },
            {
                id: 2,
                type: 'update',
                icon: 'fas fa-trophy',
                title: 'Tournament Update',
                description: 'Thunder Bolts advances to Semi-Finals in CS2 Championship',
                time: '5 minutes ago',
                game: 'CS2',
                meta: '16-14 victory'
            },
            {
                id: 3,
                type: 'result',
                icon: 'fas fa-medal',
                title: 'Match Result',
                description: 'eFootball Pro League: Phoenix Rising defeats Storm Hawks',
                time: '12 minutes ago',
                game: 'eFootball',
                meta: '3-1 final score'
            },
            {
                id: 4,
                type: 'update',
                icon: 'fas fa-users',
                title: 'Team Registration',
                description: 'New team "Cyber Wolves" registered for upcoming PUBG tournament',
                time: '20 minutes ago',
                game: 'PUBG Mobile',
                meta: 'Registration open'
            },
            {
                id: 5,
                type: 'live',
                icon: 'fas fa-broadcast-tower',
                title: 'Stream Starting',
                description: 'CS2 Semi-Finals stream begins in 15 minutes',
                time: '25 minutes ago',
                game: 'CS2',
                meta: 'Twitch & YouTube'
            }
        ];
        
        this.renderFeedItems();
    }
    
    renderFeedItems() {
        if (!this.feedContainer) return;
        
        if (this.liveFeedData.length === 0) {
            this.feedContainer.innerHTML = `
                <div class="feed-loading">
                    <div class="loading-spinner"></div>
                    Loading live updates...
                </div>
            `;
            return;
        }
        
        this.feedContainer.innerHTML = this.liveFeedData.map(item => `
            <div class="feed-item ${item.type}" data-feed-id="${item.id}">
                <div class="feed-icon ${item.type}">
                    <i class="${item.icon}"></i>
                </div>
                <div class="feed-content">
                    <div class="feed-title">${this.escapeHtml(item.title)}</div>
                    <div class="feed-description">${this.escapeHtml(item.description)}</div>
                    <div class="feed-meta">
                        <div class="feed-time">
                            <i class="fas fa-clock"></i>
                            <span>${this.escapeHtml(item.time)}</span>
                        </div>
                        <div class="feed-game">
                            <i class="fas fa-gamepad"></i>
                            <span>${this.escapeHtml(item.game)}</span>
                        </div>
                        ${item.meta ? `<span class="feed-extra">${this.escapeHtml(item.meta)}</span>` : ''}
                    </div>
                </div>
            </div>
        `).join('');
        
        // Add click animations to feed items
        this.addFeedItemAnimations();
    }
    
    addFeedItemAnimations() {
        const feedItems = this.feedContainer.querySelectorAll('.feed-item');
        feedItems.forEach(item => {
            item.addEventListener('click', (e) => {
                // Add ripple effect
                this.createRippleEffect(e.currentTarget, e);
                
                // Announce to screen readers
                const title = item.querySelector('.feed-title').textContent;
                this.announceToScreenReader(`Selected: ${title}`);
            });
        });
    }
    
    refreshFeed() {
        if (!this.feedContainer) return;
        
        // Show loading state
        this.feedContainer.innerHTML = `
            <div class="feed-loading">
                <div class="loading-spinner"></div>
                Refreshing updates...
            </div>
        `;
        
        // Simulate API call delay
        setTimeout(() => {
            // Add a new item to simulate real-time updates
            const newItem = {
                id: Date.now(),
                type: Math.random() > 0.5 ? 'live' : 'update',
                icon: 'fas fa-bolt',
                title: 'Live Update',
                description: `New tournament activity detected at ${new Date().toLocaleTimeString()}`,
                time: 'Just now',
                game: ['Valorant', 'CS2', 'eFootball'][Math.floor(Math.random() * 3)],
                meta: 'Real-time'
            };
            
            this.liveFeedData.unshift(newItem);
            if (this.liveFeedData.length > 10) {
                this.liveFeedData = this.liveFeedData.slice(0, 10);
            }
            
            this.renderFeedItems();
            this.announceToScreenReader('Feed refreshed with latest updates');
        }, 1000);
    }
    
    toggleAutoRefresh() {
        this.autoRefresh = !this.autoRefresh;
        const toggle = this.autoRefreshToggle;
        
        if (this.autoRefresh) {
            toggle.innerHTML = '<i class="fas fa-pause"></i> Auto-Refresh: ON';
            toggle.classList.add('active');
            this.startAutoRefresh();
        } else {
            toggle.innerHTML = '<i class="fas fa-play"></i> Auto-Refresh: OFF';
            toggle.classList.remove('active');
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
            }
        }
        
        this.announceToScreenReader(`Auto-refresh ${this.autoRefresh ? 'enabled' : 'disabled'}`);
    }
    
    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        if (this.autoRefresh) {
            this.autoRefreshInterval = setInterval(() => {
                this.refreshFeed();
            }, 30000); // Refresh every 30 seconds
        }
    }

    // Enhanced Game Card Effects
    initGameCardEffects() {
        const gameCards = document.querySelectorAll('.game-card[data-hover-effect="true"]');
        
        gameCards.forEach(card => {
            this.addGameCardInteractions(card);
        });
    }
    
    addGameCardInteractions(card) {
        let tiltTimeout;
        
        card.addEventListener('mouseenter', (e) => {
            this.addCardTilt(card, e);
        });
        
        card.addEventListener('mousemove', (e) => {
            clearTimeout(tiltTimeout);
            tiltTimeout = setTimeout(() => {
                this.updateCardTilt(card, e);
            }, 10);
        });
        
        card.addEventListener('mouseleave', () => {
            clearTimeout(tiltTimeout);
            this.removeCardTilt(card);
        });
        
        // Add click ripple effect
        card.addEventListener('click', (e) => {
            this.createRippleEffect(card, e);
        });
        
        // Lazy load optimization
        const cardImages = card.querySelectorAll('img[loading="lazy"]');
        this.observeImageLoading(cardImages);
    }
    
    addCardTilt(card, e) {
        const rect = card.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        const deltaX = (e.clientX - centerX) / (rect.width / 2);
        const deltaY = (e.clientY - centerY) / (rect.height / 2);
        
        const rotateX = deltaY * -10;
        const rotateY = deltaX * 10;
        
        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
    }
    
    updateCardTilt(card, e) {
        this.addCardTilt(card, e);
    }
    
    removeCardTilt(card) {
        card.style.transform = '';
    }
    
    observeImageLoading(images) {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src || img.src;
                        img.classList.add('loaded');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            images.forEach(img => imageObserver.observe(img));
        }
    }

    // Event Binding
    bindEvents() {
        // Handle system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('deltacrown-theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });

        // Handle page visibility changes for performance
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Pause auto-refresh when page is hidden
                if (this.autoRefreshInterval) {
                    clearInterval(this.autoRefreshInterval);
                }
            } else {
                // Resume auto-refresh when page becomes visible
                if (this.autoRefresh) {
                    this.startAutoRefresh();
                }
            }
        });

        // Handle window resize for responsive adjustments
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.handleResize();
            }, 250);
        });
    }

    handleResize() {
        // Recalculate animations and layouts on resize
        this.setupScrollAnimations();
    }

    // Utility function for HTML escaping
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Inject additional styles
    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
            
            .custom-tooltip {
                opacity: 0;
                animation: fadeIn 0.2s ease forwards;
            }
            
            @keyframes fadeIn {
                to { opacity: 1; }
            }
            
            .skip-link {
                position: absolute;
                top: -40px;
                left: 6px;
                background: var(--color-primary);
                color: var(--color-text-inverse);
                padding: 8px;
                text-decoration: none;
                border-radius: 4px;
                z-index: 1000;
                opacity: 0;
                transition: all 0.2s;
            }
            
            .skip-link:focus {
                top: 6px;
                opacity: 1;
            }
            
            .sr-only {
                position: absolute !important;
                width: 1px !important;
                height: 1px !important;
                padding: 0 !important;
                margin: -1px !important;
                overflow: hidden !important;
                clip: rect(0, 0, 0, 0) !important;
                white-space: nowrap !important;
                border: 0 !important;
            }
            
            /* Ensure proper focus indicators */
            .keyboard-navigation *:focus-visible {
                outline: 2px solid var(--color-primary) !important;
                outline-offset: 2px !important;
                border-radius: var(--radius-sm);
            }
            
            [data-focused="true"] {
                box-shadow: 0 0 0 3px rgba(var(--color-primary), 0.4) !important;
            }
            
            .animate-in {
                animation: slideInUp 0.6s ease-out forwards;
            }
            
            @keyframes slideInUp {
                from {
                    opacity: 0;
                    transform: translateY(30px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.deltaCrownHomepage = new DeltaCrownHomepage();
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DeltaCrownHomepage;
}