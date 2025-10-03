/**
 * UI/UX Phase C: Mobile Enhancements JavaScript
 * 
 * Features:
 * - Swipe gesture detection
 * - Pull-to-refresh
 * - Touch feedback
 * - Mobile menu management
 * - Bottom sheet handling
 * - Responsive utilities
 * 
 * Browser Support: iOS Safari 12+, Chrome Mobile 90+, Samsung Internet
 * 
 * @version 1.0.0
 * @author DeltaCrown Dev Team
 */

(function() {
    'use strict';

    /* ============================================
       1. Swipe Gesture Handler
       ============================================ */

    class SwipeHandler {
        constructor(element, options = {}) {
            this.element = element;
            this.options = {
                threshold: options.threshold || 50,      // Min distance for swipe
                restraint: options.restraint || 100,     // Max distance perpendicular
                allowedTime: options.allowedTime || 300, // Max time for swipe
                onSwipeLeft: options.onSwipeLeft || null,
                onSwipeRight: options.onSwipeRight || null,
                onSwipeUp: options.onSwipeUp || null,
                onSwipeDown: options.onSwipeDown || null,
            };

            this.startX = 0;
            this.startY = 0;
            this.distX = 0;
            this.distY = 0;
            this.startTime = 0;

            this.init();
        }

        init() {
            this.element.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
            this.element.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
            this.element.addEventListener('touchend', (e) => this.handleTouchEnd(e));
        }

        handleTouchStart(e) {
            const touch = e.touches[0];
            this.startX = touch.pageX;
            this.startY = touch.pageY;
            this.startTime = new Date().getTime();
        }

        handleTouchMove(e) {
            // Prevent default only if swiping horizontally
            const touch = e.touches[0];
            this.distX = touch.pageX - this.startX;
            this.distY = touch.pageY - this.startY;

            if (Math.abs(this.distX) > Math.abs(this.distY)) {
                e.preventDefault();
            }
        }

        handleTouchEnd(e) {
            const elapsedTime = new Date().getTime() - this.startTime;

            if (elapsedTime <= this.options.allowedTime) {
                // Horizontal swipe
                if (Math.abs(this.distX) >= this.options.threshold && Math.abs(this.distY) <= this.options.restraint) {
                    const direction = this.distX < 0 ? 'left' : 'right';
                    this.triggerSwipe(direction);
                }
                // Vertical swipe
                else if (Math.abs(this.distY) >= this.options.threshold && Math.abs(this.distX) <= this.options.restraint) {
                    const direction = this.distY < 0 ? 'up' : 'down';
                    this.triggerSwipe(direction);
                }
            }

            // Reset
            this.startX = 0;
            this.startY = 0;
            this.distX = 0;
            this.distY = 0;
        }

        triggerSwipe(direction) {
            const callback = this.options[`onSwipe${direction.charAt(0).toUpperCase() + direction.slice(1)}`];
            if (callback && typeof callback === 'function') {
                callback(this.element);
            }

            // Dispatch custom event
            const event = new CustomEvent('swipe', {
                detail: { direction, element: this.element }
            });
            this.element.dispatchEvent(event);
        }
    }

    /* ============================================
       2. Swipeable Carousel
       ============================================ */

    class SwipeableCarousel {
        constructor(container, options = {}) {
            this.container = container;
            this.track = container.querySelector('.swipeable-track');
            this.items = Array.from(this.track.children);
            this.currentIndex = 0;

            this.options = {
                autoplay: options.autoplay || false,
                autoplayInterval: options.autoplayInterval || 5000,
                showIndicators: options.showIndicators !== false,
                loop: options.loop !== false,
            };

            if (this.items.length > 0) {
                this.init();
            }
        }

        init() {
            // Add swipe handler
            new SwipeHandler(this.container, {
                onSwipeLeft: () => this.next(),
                onSwipeRight: () => this.prev(),
            });

            // Create indicators
            if (this.options.showIndicators) {
                this.createIndicators();
            }

            // Start autoplay
            if (this.options.autoplay) {
                this.startAutoplay();
            }

            // Update on load
            this.updatePosition();
        }

        createIndicators() {
            const indicators = document.createElement('div');
            indicators.className = 'swipe-indicators';

            this.items.forEach((item, index) => {
                const indicator = document.createElement('button');
                indicator.className = 'swipe-indicator';
                indicator.setAttribute('aria-label', `Go to slide ${index + 1}`);
                indicator.addEventListener('click', () => this.goTo(index));
                indicators.appendChild(indicator);
            });

            this.container.appendChild(indicators);
            this.indicators = indicators.querySelectorAll('.swipe-indicator');
        }

        updatePosition(animated = true) {
            if (!animated) {
                this.track.classList.add('swiping');
            }

            const offset = -this.currentIndex * 100;
            this.track.style.transform = `translateX(${offset}%)`;

            // Update indicators
            if (this.indicators) {
                this.indicators.forEach((indicator, index) => {
                    indicator.classList.toggle('active', index === this.currentIndex);
                });
            }

            if (!animated) {
                setTimeout(() => this.track.classList.remove('swiping'), 50);
            }
        }

        next() {
            if (this.currentIndex < this.items.length - 1) {
                this.currentIndex++;
            } else if (this.options.loop) {
                this.currentIndex = 0;
            }
            this.updatePosition();
            this.resetAutoplay();
        }

        prev() {
            if (this.currentIndex > 0) {
                this.currentIndex--;
            } else if (this.options.loop) {
                this.currentIndex = this.items.length - 1;
            }
            this.updatePosition();
            this.resetAutoplay();
        }

        goTo(index) {
            this.currentIndex = Math.max(0, Math.min(index, this.items.length - 1));
            this.updatePosition();
            this.resetAutoplay();
        }

        startAutoplay() {
            this.autoplayTimer = setInterval(() => this.next(), this.options.autoplayInterval);
        }

        stopAutoplay() {
            if (this.autoplayTimer) {
                clearInterval(this.autoplayTimer);
                this.autoplayTimer = null;
            }
        }

        resetAutoplay() {
            if (this.options.autoplay) {
                this.stopAutoplay();
                this.startAutoplay();
            }
        }
    }

    /* ============================================
       3. Mobile Menu Manager
       ============================================ */

    class MobileMenu {
        constructor() {
            this.toggle = document.querySelector('.mobile-menu-toggle');
            this.menu = document.querySelector('.mobile-menu');
            this.overlay = document.querySelector('.mobile-menu-overlay');
            this.closeBtn = document.querySelector('.mobile-menu-close');
            this.isOpen = false;

            if (this.toggle && this.menu) {
                this.init();
            }
        }

        init() {
            this.toggle.addEventListener('click', () => this.toggleMenu());
            
            if (this.overlay) {
                this.overlay.addEventListener('click', () => this.close());
            }

            if (this.closeBtn) {
                this.closeBtn.addEventListener('click', () => this.close());
            }

            // Close on ESC key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.isOpen) {
                    this.close();
                }
            });

            // Prevent body scroll when menu is open
            this.menu.addEventListener('touchmove', (e) => {
                if (this.isOpen) {
                    e.stopPropagation();
                }
            });
        }

        toggleMenu() {
            if (this.isOpen) {
                this.close();
            } else {
                this.open();
            }
        }

        open() {
            this.isOpen = true;
            this.toggle.classList.add('active');
            this.menu.classList.add('active');
            if (this.overlay) {
                this.overlay.classList.add('active');
            }
            document.body.style.overflow = 'hidden';
        }

        close() {
            this.isOpen = false;
            this.toggle.classList.remove('active');
            this.menu.classList.remove('active');
            if (this.overlay) {
                this.overlay.classList.remove('active');
            }
            document.body.style.overflow = '';
        }
    }

    /* ============================================
       4. Pull-to-Refresh
       ============================================ */

    class PullToRefresh {
        constructor(container, onRefresh) {
            this.container = container;
            this.onRefresh = onRefresh;
            this.startY = 0;
            this.currentY = 0;
            this.isDragging = false;
            this.threshold = 80;

            this.init();
        }

        init() {
            // Create indicator
            this.indicator = document.createElement('div');
            this.indicator.className = 'pull-to-refresh-indicator';
            this.indicator.innerHTML = '<div class="pull-to-refresh-spinner"></div>';
            this.container.insertBefore(this.indicator, this.container.firstChild);

            // Add touch handlers
            this.container.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
            this.container.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: false });
            this.container.addEventListener('touchend', (e) => this.handleTouchEnd(e));
        }

        handleTouchStart(e) {
            if (this.container.scrollTop === 0) {
                this.startY = e.touches[0].pageY;
                this.isDragging = true;
            }
        }

        handleTouchMove(e) {
            if (!this.isDragging) return;

            this.currentY = e.touches[0].pageY;
            const distance = this.currentY - this.startY;

            if (distance > 0 && this.container.scrollTop === 0) {
                e.preventDefault();
                const pullDistance = Math.min(distance, this.threshold);
                this.indicator.style.top = `${pullDistance - 60}px`;

                if (pullDistance >= this.threshold) {
                    this.indicator.classList.add('pulling');
                } else {
                    this.indicator.classList.remove('pulling');
                }
            }
        }

        handleTouchEnd(e) {
            if (!this.isDragging) return;

            const distance = this.currentY - this.startY;
            
            if (distance >= this.threshold) {
                this.refresh();
            } else {
                this.reset();
            }

            this.isDragging = false;
        }

        async refresh() {
            this.indicator.classList.add('refreshing');
            
            try {
                await this.onRefresh();
            } catch (error) {
                console.error('[PullToRefresh] Error:', error);
            }

            setTimeout(() => this.reset(), 500);
        }

        reset() {
            this.indicator.classList.remove('pulling', 'refreshing');
            this.indicator.style.top = '';
        }
    }

    /* ============================================
       5. Bottom Sheet Manager
       ============================================ */

    class BottomSheet {
        constructor(element, options = {}) {
            this.element = element;
            this.isOpen = false;
            this.startY = 0;
            this.currentY = 0;

            this.options = {
                dismissThreshold: options.dismissThreshold || 100,
                onOpen: options.onOpen || null,
                onClose: options.onClose || null,
            };

            this.init();
        }

        init() {
            const dialog = this.element.querySelector('.modal-dialog');
            if (!dialog) return;

            // Add drag handle interaction
            dialog.addEventListener('touchstart', (e) => {
                this.startY = e.touches[0].pageY;
            }, { passive: true });

            dialog.addEventListener('touchmove', (e) => {
                if (!this.isOpen) return;

                this.currentY = e.touches[0].pageY;
                const distance = this.currentY - this.startY;

                if (distance > 0) {
                    dialog.style.transform = `translateY(${distance}px)`;
                }
            }, { passive: true });

            dialog.addEventListener('touchend', (e) => {
                if (!this.isOpen) return;

                const distance = this.currentY - this.startY;

                if (distance > this.options.dismissThreshold) {
                    this.close();
                } else {
                    dialog.style.transform = '';
                }

                this.startY = 0;
                this.currentY = 0;
            });
        }

        open() {
            this.isOpen = true;
            this.element.classList.add('show');
            document.body.style.overflow = 'hidden';

            if (this.options.onOpen) {
                this.options.onOpen();
            }
        }

        close() {
            this.isOpen = false;
            this.element.classList.remove('show');
            document.body.style.overflow = '';

            if (this.options.onClose) {
                this.options.onClose();
            }
        }
    }

    /* ============================================
       6. Touch Feedback
       ============================================ */

    function addTouchFeedback() {
        const elements = document.querySelectorAll('.touch-feedback:not([data-touch-initialized])');

        elements.forEach(element => {
            element.setAttribute('data-touch-initialized', 'true');

            element.addEventListener('touchstart', function(e) {
                // Haptic feedback (if available)
                if (window.navigator && window.navigator.vibrate) {
                    window.navigator.vibrate(10);
                }
            });
        });
    }

    /* ============================================
       7. Mobile Table Enhancement
       ============================================ */

    function enhanceMobileTables() {
        if (window.innerWidth <= 768) {
            const tables = document.querySelectorAll('table:not(.table-mobile-cards):not([data-mobile-enhanced])');

            tables.forEach(table => {
                table.setAttribute('data-mobile-enhanced', 'true');
                table.classList.add('table-mobile-cards');

                const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());

                table.querySelectorAll('tbody tr').forEach(row => {
                    Array.from(row.querySelectorAll('td')).forEach((cell, index) => {
                        if (headers[index]) {
                            cell.setAttribute('data-label', headers[index]);
                        }
                    });
                });
            });
        }
    }

    /* ============================================
       8. Viewport Height Fix (iOS)
       ============================================ */

    function setViewportHeight() {
        // Fix for iOS viewport height issue
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    }

    /* ============================================
       9. Detect Mobile Device
       ============================================ */

    function isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    function isTouchDevice() {
        return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    }

    /* ============================================
       10. Initialize All Mobile Enhancements
       ============================================ */

    function initMobileEnhancements() {
        console.log('[MobileEnhancements] Initializing...');

        // Set viewport height
        setViewportHeight();
        window.addEventListener('resize', setViewportHeight);
        window.addEventListener('orientationchange', setViewportHeight);

        // Initialize mobile menu
        if (document.querySelector('.mobile-menu-toggle')) {
            new MobileMenu();
            console.log('[MobileEnhancements] Mobile menu initialized');
        }

        // Initialize swipeable carousels
        document.querySelectorAll('.swipeable-container:not([data-swipe-initialized])').forEach(container => {
            container.setAttribute('data-swipe-initialized', 'true');
            new SwipeableCarousel(container);
            console.log('[MobileEnhancements] Carousel initialized:', container);
        });

        // Add touch feedback
        if (isTouchDevice()) {
            addTouchFeedback();
            document.body.classList.add('touch-device');
            console.log('[MobileEnhancements] Touch feedback enabled');
        }

        // Enhance mobile tables
        enhanceMobileTables();
        window.addEventListener('resize', enhanceMobileTables);

        // Initialize bottom sheets
        document.querySelectorAll('.modal:not([data-bottomsheet-initialized])').forEach(modal => {
            if (window.innerWidth <= 768) {
                modal.setAttribute('data-bottomsheet-initialized', 'true');
                new BottomSheet(modal);
            }
        });

        console.log('[MobileEnhancements] Initialization complete');
    }

    /* ============================================
       11. Export to Global Scope
       ============================================ */

    window.MobileEnhancements = {
        SwipeHandler,
        SwipeableCarousel,
        MobileMenu,
        PullToRefresh,
        BottomSheet,
        isMobileDevice,
        isTouchDevice,
        init: initMobileEnhancements,
    };

    /* ============================================
       12. Auto-Initialize
       ============================================ */

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMobileEnhancements);
    } else {
        initMobileEnhancements();
    }

})();
