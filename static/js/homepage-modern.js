/**
 * DeltaCrown Modern Homepage JavaScript
 * Accessible, Performance-Optimized, Mobile-First
 */

class ModernHomepage {
    constructor() {
        this.theme = this.getStoredTheme();
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
    }

    // Theme Management - Default to Dark for E-sports Experience
    getStoredTheme() {
        const stored = localStorage.getItem('deltacrown-theme');
        if (stored) return stored;
        
        // Default to dark theme for premium e-sports experience
        // Only use light if explicitly preferred
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
        
        // Announce theme change for screen readers
        this.announceToScreenReader(`Switched to ${newTheme} mode`);
    }

    initThemeToggle() {
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
            
            // Add keyboard support
            themeToggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleTheme();
                }
            });
        }
    }

    // Accessibility Enhancements
    initAccessibility() {
        this.addSkipLink();
        this.enhanceKeyboardNavigation();
        this.addScreenReaderAnnouncements();
        this.improveButtonAccessibility();
    }

    addSkipLink() {
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.textContent = 'Skip to main content';
        skipLink.className = 'skip-link';
        skipLink.setAttribute('aria-label', 'Skip to main content');
        
        skipLink.addEventListener('focus', () => {
            skipLink.style.top = '6px';
        });
        
        skipLink.addEventListener('blur', () => {
            skipLink.style.top = '-40px';
        });
        
        document.body.insertBefore(skipLink, document.body.firstChild);
    }

    enhanceKeyboardNavigation() {
        // Track keyboard vs mouse navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });

        // Improve focus management for cards
        const cards = document.querySelectorAll('.game-card, .tournament-card, .team-card');
        cards.forEach(card => {
            card.setAttribute('tabindex', '0');
            card.setAttribute('role', 'button');
            
            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const link = card.querySelector('a');
                    if (link) link.click();
                }
            });
        });
    }

    addScreenReaderAnnouncements() {
        // Create live region for announcements
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        liveRegion.style.cssText = `
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        `;
        document.body.appendChild(liveRegion);
        this.liveRegion = liveRegion;
    }

    announceToScreenReader(message) {
        if (this.liveRegion) {
            this.liveRegion.textContent = message;
            setTimeout(() => {
                this.liveRegion.textContent = '';
            }, 1000);
        }
    }

    improveButtonAccessibility() {
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            // Ensure minimum touch target size (44x44px)
            const rect = button.getBoundingClientRect();
            if (rect.height < 44) {
                button.style.minHeight = '44px';
            }
            
            // Add better focus indicators
            button.addEventListener('focus', () => {
                button.setAttribute('data-focused', 'true');
            });
            
            button.addEventListener('blur', () => {
                button.removeAttribute('data-focused');
            });
        });
    }

    // Animations and Visual Effects
    initAnimations() {
        this.initScrollAnimations();
        this.initCounterAnimations();
        this.initParallaxEffects();
    }

    initScrollAnimations() {
        // Only add animations if user hasn't opted out
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Animate sections on scroll
        const animatedElements = document.querySelectorAll(
            '.section-header, .game-card, .tournament-card, .team-card, .feature-card'
        );
        
        animatedElements.forEach((el, index) => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
            observer.observe(el);
        });
    }

    initCounterAnimations() {
        const counters = document.querySelectorAll('.stat-number');
        const counterObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                    counterObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.5 });

        counters.forEach(counter => counterObserver.observe(counter));
    }

    animateCounter(element) {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        const finalText = element.textContent;
        const numberMatch = finalText.match(/[\d,]+/);
        if (!numberMatch) return;

        const finalValue = parseInt(numberMatch[0].replace(/,/g, ''));
        const prefix = finalText.substring(0, numberMatch.index);
        const suffix = finalText.substring(numberMatch.index + numberMatch[0].length);
        
        const duration = 2000;
        const increment = finalValue / (duration / 16);
        let currentValue = 0;

        const updateCounter = () => {
            currentValue += increment;
            if (currentValue < finalValue) {
                const displayValue = Math.floor(currentValue).toLocaleString();
                element.textContent = prefix + displayValue + suffix;
                requestAnimationFrame(updateCounter);
            } else {
                element.textContent = finalText;
            }
        };

        updateCounter();
    }

    initParallaxEffects() {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        // Subtle parallax for hero section
        const hero = document.querySelector('.hero-section');
        if (hero) {
            let ticking = false;
            
            const updateParallax = () => {
                const scrolled = window.pageYOffset;
                const rate = scrolled * -0.2;
                hero.style.transform = `translateY(${rate}px)`;
                ticking = false;
            };

            const requestTick = () => {
                if (!ticking) {
                    requestAnimationFrame(updateParallax);
                    ticking = true;
                }
            };

            window.addEventListener('scroll', requestTick, { passive: true });
        }
    }

    // Interactive Elements
    initInteractions() {
        this.initCardHovers();
        this.initButtonEffects();
        this.initTooltips();
    }

    initCardHovers() {
        const cards = document.querySelectorAll('.game-card, .tournament-card, .team-card');
        
        cards.forEach(card => {
            card.addEventListener('mouseenter', (e) => {
                this.enhanceCardHover(e.currentTarget);
            });

            card.addEventListener('mouseleave', (e) => {
                this.resetCardHover(e.currentTarget);
            });

            // Touch support for mobile
            card.addEventListener('touchstart', (e) => {
                this.enhanceCardHover(e.currentTarget);
            }, { passive: true });

            card.addEventListener('touchend', (e) => {
                setTimeout(() => {
                    this.resetCardHover(e.currentTarget);
                }, 300);
            }, { passive: true });
        });
    }

    enhanceCardHover(card) {
        const gameCard = card.classList.contains('game-card');
        if (gameCard) {
            const gameColor = this.getGameColor(card);
            card.style.borderColor = gameColor;
            card.style.boxShadow = `0 20px 40px ${gameColor}20, 0 0 0 1px ${gameColor}10`;
        }
    }

    resetCardHover(card) {
        card.style.borderColor = '';
        card.style.boxShadow = '';
    }

    getGameColor(card) {
        const gameSlug = card.dataset.game;
        const colorMap = {
            'valorant': '#ff4654',
            'cs2': '#f5a623',
            'efootball': '#1a5490',
            'pubg': '#ff6b35',
            'mlbb': '#4a90e2',
            'freefire': '#ff5722'
        };
        return colorMap[gameSlug] || '#3b82f6';
    }

    initButtonEffects() {
        const buttons = document.querySelectorAll('.btn');
        
        buttons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.createRippleEffect(e);
            });
        });
    }

    createRippleEffect(e) {
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        const button = e.currentTarget;
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
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
            z-index: 1;
        `;

        // Ensure button has relative positioning
        if (getComputedStyle(button).position === 'static') {
            button.style.position = 'relative';
        }
        button.style.overflow = 'hidden';

        button.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    initTooltips() {
        const elementsWithTooltips = document.querySelectorAll('[title]');
        
        elementsWithTooltips.forEach(element => {
            const title = element.getAttribute('title');
            element.removeAttribute('title');
            element.setAttribute('aria-label', title);
            
            // Add custom tooltip on hover for non-touch devices
            if (!('ontouchstart' in window)) {
                element.addEventListener('mouseenter', (e) => {
                    this.showTooltip(e.target, title);
                });
                
                element.addEventListener('mouseleave', (e) => {
                    this.hideTooltip();
                });
            }
        });
    }

    showTooltip(element, text) {
        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = text;
        tooltip.style.cssText = `
            position: absolute;
            background: var(--color-text-primary);
            color: var(--color-background);
            padding: 0.5rem 0.75rem;
            border-radius: var(--radius-md);
            font-size: var(--text-sm);
            z-index: var(--z-tooltip);
            pointer-events: none;
            white-space: nowrap;
            box-shadow: var(--shadow-lg);
        `;
        
        document.body.appendChild(tooltip);
        
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        tooltip.style.left = rect.left + (rect.width - tooltipRect.width) / 2 + 'px';
        tooltip.style.top = rect.top - tooltipRect.height - 8 + 'px';
        
        this.currentTooltip = tooltip;
    }

    hideTooltip() {
        if (this.currentTooltip) {
            this.currentTooltip.remove();
            this.currentTooltip = null;
        }
    }

    // Event Bindings
    bindEvents() {
        // Window resize handler
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.handleResize();
            }, 250);
        }, { passive: true });

        // System theme change detection
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('deltacrown-theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });

        // Visibility change handling
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseAnimations();
            } else {
                this.resumeAnimations();
            }
        });

        // Smooth scroll for anchor links
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a[href^="#"]');
            if (link) {
                e.preventDefault();
                const targetId = link.getAttribute('href');
                const targetElement = document.querySelector(targetId);
                
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // Focus management for accessibility
                    targetElement.focus();
                }
            }
        });
    }

    handleResize() {
        // Recalculate any size-dependent features
        this.hideTooltip(); // Hide tooltips on resize
    }

    pauseAnimations() {
        document.body.style.animationPlayState = 'paused';
    }

    resumeAnimations() {
        document.body.style.animationPlayState = 'running';
    }

    // Performance monitoring
    reportPerformance() {
        if ('performance' in window && 'PerformanceObserver' in window) {
            // Monitor loading performance
            window.addEventListener('load', () => {
                const perfData = performance.getEntriesByType('navigation')[0];
                if (perfData) {
                    dcLog('Page Load Time:', Math.round(perfData.loadEventEnd - perfData.loadEventStart));
                }
            });

            // Monitor layout shifts
            const observer = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    if (entry.value > 0.1) {
                        console.warn('Layout shift detected:', entry.value);
                    }
                }
            });
            
            observer.observe({ entryTypes: ['layout-shift'] });
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const homepage = new ModernHomepage();
    
    // Optional performance monitoring in development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        homepage.reportPerformance();
    }
});

// Add CSS for ripple animation
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
    
    /* Ensure proper focus indicators */
    .keyboard-navigation *:focus-visible {
        outline: 2px solid var(--color-primary) !important;
        outline-offset: 2px !important;
        border-radius: var(--radius-sm);
    }
    
    [data-focused="true"] {
        box-shadow: 0 0 0 3px var(--color-primary)40 !important;
    }
`;
document.head.appendChild(style);
    }

    // Live Tournament Feed System
    initLiveFeed() {
        this.liveFeedData = [];
        this.autoRefresh = true;
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
    
    // Utility function for HTML escaping
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ModernHomepage;
}
