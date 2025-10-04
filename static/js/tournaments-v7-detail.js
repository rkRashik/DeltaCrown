/**
 * DELTACROWN - TOURNAMENT DETAIL PAGE V7
 * Interactive Features & Functionality
 * 
 * Features:
 * - Tab Navigation with URL fragment support
 * - Modal Management (Registration, Share)
 * - Registration Timer Countdown
 * - Share Functionality (Social + Copy Link)
 * - FAQ Accordion
 * - Sticky CTA on scroll
 * - Add to Calendar
 * - Image Lightbox (if media exists)
 */

(function() {
    'use strict';

    // ============================================
    // UTILITY FUNCTIONS
    // ============================================
    
    const utils = {
        /**
         * Get element(s) safely
         */
        $(selector, context = document) {
            return context.querySelector(selector);
        },
        
        $$(selector, context = document) {
            return Array.from(context.querySelectorAll(selector));
        },
        
        /**
         * Add event listener with delegation support
         */
        on(element, event, selector, handler) {
            if (typeof selector === 'function') {
                handler = selector;
                element.addEventListener(event, handler);
            } else {
                element.addEventListener(event, (e) => {
                    const target = e.target.closest(selector);
                    if (target) handler.call(target, e);
                });
            }
        },
        
        /**
         * Format time remaining
         */
        formatTimeRemaining(distance) {
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            if (days > 0) {
                return `${days}d ${hours}h ${minutes}m`;
            } else if (hours > 0) {
                return `${hours}h ${minutes}m ${seconds}s`;
            } else if (minutes > 0) {
                return `${minutes}m ${seconds}s`;
            } else {
                return `${seconds}s`;
            }
        },
        
        /**
         * Copy text to clipboard
         */
        async copyToClipboard(text) {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch (err) {
                // Fallback for older browsers
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                const success = document.execCommand('copy');
                document.body.removeChild(textarea);
                return success;
            }
        },
        
        /**
         * Show toast notification
         */
        showToast(message, type = 'success') {
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            toast.style.cssText = `
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                padding: 1rem 1.5rem;
                background: ${type === 'success' ? '#10b981' : '#ef4444'};
                color: white;
                border-radius: 0.5rem;
                font-weight: 600;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
                z-index: 1100;
                animation: slideInRight 0.3s ease-out;
            `;
            
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.style.animation = 'slideOutRight 0.3s ease-in';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        }
    };

    // ============================================
    // TAB NAVIGATION (Enhanced with Keyboard Support)
    // ============================================
    
    const TabNavigation = {
        init() {
            this.tabLinks = utils.$$('.tab-link');
            this.tabPanels = utils.$$('.tab-panel');
            
            if (this.tabLinks.length === 0) return;
            
            // Add ARIA attributes
            this.tabLinks.forEach((link, index) => {
                link.setAttribute('role', 'tab');
                link.setAttribute('aria-controls', `tab-${link.dataset.tab}`);
                link.setAttribute('tabindex', index === 0 ? '0' : '-1');
            });
            
            this.tabPanels.forEach(panel => {
                panel.setAttribute('role', 'tabpanel');
                panel.setAttribute('aria-labelledby', `tab-link-${panel.id}`);
            });
            
            // Handle tab clicks
            this.tabLinks.forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const tabName = link.dataset.tab;
                    this.switchTab(tabName);
                });
                
                // Keyboard navigation
                link.addEventListener('keydown', (e) => this.handleKeyboard(e, link));
            });
            
            // Handle URL hash on load
            const hash = window.location.hash.slice(1);
            if (hash) {
                const validTabs = ['overview', 'rules', 'prizes', 'schedule', 'brackets', 'participants', 'media', 'faq'];
                if (validTabs.includes(hash)) {
                    this.switchTab(hash);
                }
            }
            
            // Handle browser back/forward
            window.addEventListener('popstate', () => {
                const hash = window.location.hash.slice(1);
                if (hash) this.switchTab(hash, false);
            });
            
            console.log(`📑 TabNavigation initialized with ${this.tabLinks.length} tabs (Keyboard accessible)`);
        },
        
        handleKeyboard(e, currentLink) {
            const key = e.key;
            const currentIndex = Array.from(this.tabLinks).indexOf(currentLink);
            let newIndex = currentIndex;
            
            switch(key) {
                case 'ArrowLeft':
                case 'ArrowUp':
                    e.preventDefault();
                    newIndex = currentIndex > 0 ? currentIndex - 1 : this.tabLinks.length - 1;
                    break;
                case 'ArrowRight':
                case 'ArrowDown':
                    e.preventDefault();
                    newIndex = currentIndex < this.tabLinks.length - 1 ? currentIndex + 1 : 0;
                    break;
                case 'Home':
                    e.preventDefault();
                    newIndex = 0;
                    break;
                case 'End':
                    e.preventDefault();
                    newIndex = this.tabLinks.length - 1;
                    break;
                case 'Enter':
                case ' ':
                    e.preventDefault();
                    this.switchTab(currentLink.dataset.tab);
                    return;
                default:
                    return;
            }
            
            // Focus and activate new tab
            const newLink = this.tabLinks[newIndex];
            newLink.focus();
            this.switchTab(newLink.dataset.tab);
        },
        
        switchTab(tabName, updateHistory = true) {
            // Remove active from all tabs
            this.tabLinks.forEach(link => {
                link.classList.remove('active');
                link.setAttribute('aria-selected', 'false');
                link.setAttribute('tabindex', '-1');
            });
            this.tabPanels.forEach(panel => {
                panel.classList.remove('active');
                panel.setAttribute('aria-hidden', 'true');
            });
            
            // Add active to selected tab
            const activeLink = utils.$(`.tab-link[data-tab="${tabName}"]`);
            const activePanel = utils.$(`#tab-${tabName}`);
            
            if (activeLink && activePanel) {
                activeLink.classList.add('active');
                activeLink.setAttribute('aria-selected', 'true');
                activeLink.setAttribute('tabindex', '0');
                
                activePanel.classList.add('active');
                activePanel.setAttribute('aria-hidden', 'false');
                
                // Update URL hash
                if (updateHistory) {
                    history.pushState(null, '', `#${tabName}`);
                }
                
                // Scroll to tab navigation
                const tabNav = utils.$('.tab-navigation');
                if (tabNav) {
                    const offset = tabNav.offsetTop - 80; // Account for sticky header
                    window.scrollTo({ top: offset, behavior: 'smooth' });
                }
            }
        }
    };

    // ============================================
    // MODAL MANAGEMENT (Enhanced with Focus Trap & Accessibility)
    // ============================================
    
    const ModalManager = {
        activeModal: null,
        previousFocus: null,
        
        init() {
            this.modals = utils.$$('.modal');
            if (this.modals.length === 0) return;
            
            // Add ARIA attributes
            this.modals.forEach(modal => {
                modal.setAttribute('role', 'dialog');
                modal.setAttribute('aria-modal', 'true');
                modal.setAttribute('aria-hidden', 'true');
                
                const backdrop = utils.$('.modal-backdrop', modal);
                const closeBtn = utils.$('.modal-close', modal);
                
                if (backdrop) {
                    backdrop.addEventListener('click', () => this.close(modal));
                }
                
                if (closeBtn) {
                    closeBtn.addEventListener('click', () => this.close(modal));
                    closeBtn.setAttribute('aria-label', 'Close modal');
                }
            });
            
            // Close modal on Escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.activeModal) {
                    this.close(this.activeModal);
                }
            });
            
            console.log('🎭 ModalManager initialized (Focus trap enabled)');
        },
        
        open(modalId) {
            const modal = utils.$(`#${modalId}`);
            if (modal) {
                // Save current focus
                this.previousFocus = document.activeElement;
                
                modal.classList.add('active');
                modal.setAttribute('aria-hidden', 'false');
                document.body.style.overflow = 'hidden';
                this.activeModal = modal;
                
                // Focus first focusable element
                setTimeout(() => {
                    const firstFocusable = this.getFocusableElements(modal)[0];
                    if (firstFocusable) firstFocusable.focus();
                }, 100);
                
                // Setup focus trap
                this.setupFocusTrap(modal);
            }
        },
        
        close(modal) {
            if (typeof modal === 'string') {
                modal = utils.$(`#${modal}`);
            }
            if (modal) {
                modal.classList.remove('active');
                modal.setAttribute('aria-hidden', 'true');
                document.body.style.overflow = '';
                this.activeModal = null;
                
                // Restore focus
                if (this.previousFocus) {
                    this.previousFocus.focus();
                    this.previousFocus = null;
                }
            }
        },
        
        getFocusableElements(container) {
            const selectors = [
                'button:not([disabled])',
                'a[href]',
                'input:not([disabled])',
                'select:not([disabled])',
                'textarea:not([disabled])',
                '[tabindex]:not([tabindex="-1"])'
            ];
            return Array.from(container.querySelectorAll(selectors.join(', ')));
        },
        
        setupFocusTrap(modal) {
            const focusableElements = this.getFocusableElements(modal);
            if (focusableElements.length === 0) return;
            
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];
            
            // Trap focus
            modal.addEventListener('keydown', (e) => {
                if (e.key !== 'Tab') return;
                
                if (e.shiftKey) {
                    // Shift + Tab
                    if (document.activeElement === firstElement) {
                        e.preventDefault();
                        lastElement.focus();
                    }
                } else {
                    // Tab
                    if (document.activeElement === lastElement) {
                        e.preventDefault();
                        firstElement.focus();
                    }
                }
            });
        }
    };

    // ============================================
    // CTA ACTIONS
    // ============================================
    
    const CTAActions = {
        init() {
            // Register button
            const registerBtn = utils.$('[data-action="register"]');
            if (registerBtn) {
                registerBtn.addEventListener('click', () => {
                    ModalManager.open('registrationModal');
                });
            }
            
            // Share button
            const shareBtn = utils.$('[data-action="share"]');
            if (shareBtn) {
                shareBtn.addEventListener('click', () => {
                    ModalManager.open('shareModal');
                });
            }
            
            // Follow button
            const followBtn = utils.$('[data-action="follow"]');
            if (followBtn) {
                followBtn.addEventListener('click', () => {
                    this.toggleFollow(followBtn);
                });
            }
            
            // Payment button
            const paymentBtn = utils.$('[data-action="payment"]');
            if (paymentBtn) {
                paymentBtn.addEventListener('click', () => {
                    // Redirect to payment page
                    window.location.href = `/tournaments/payment/${window.location.pathname.split('/')[3]}/`;
                });
            }
        },
        
        toggleFollow(btn) {
            const isFollowing = btn.classList.contains('following');
            
            if (isFollowing) {
                btn.classList.remove('following');
                btn.innerHTML = `
                    <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                    </svg>
                    Follow
                `;
                utils.showToast('Unfollowed tournament');
            } else {
                btn.classList.add('following');
                btn.innerHTML = `
                    <svg width="18" height="18" fill="currentColor" stroke="currentColor" stroke-width="2">
                        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                    </svg>
                    Following
                `;
                utils.showToast('Following tournament! You\'ll receive updates.');
            }
            
            // TODO: Send AJAX request to backend
        }
    };

    // ============================================
    // REGISTRATION TIMER
    // ============================================
    
    const RegistrationTimer = {
        init() {
            this.timerElement = utils.$('#regTimer');
            if (!this.timerElement) return;
            
            const endDate = this.timerElement.dataset.end;
            if (!endDate) return;
            
            this.endTime = new Date(endDate).getTime();
            this.update();
            this.interval = setInterval(() => this.update(), 1000);
        },
        
        update() {
            const now = new Date().getTime();
            const distance = this.endTime - now;
            
            if (distance < 0) {
                clearInterval(this.interval);
                this.timerElement.textContent = 'Registration Closed';
                this.timerElement.style.color = '#ef4444';
                return;
            }
            
            this.timerElement.textContent = utils.formatTimeRemaining(distance);
        }
    };

    // ============================================
    // SHARE FUNCTIONALITY
    // ============================================
    
    const ShareManager = {
        init() {
            const shareButtons = utils.$$('.share-btn');
            const copyBtn = utils.$('.btn-copy');
            const shareLink = utils.$('#shareLink');
            
            if (shareButtons.length === 0) return;
            
            const url = shareLink ? shareLink.value : window.location.href;
            const title = document.querySelector('.hero-title')?.textContent || 'Tournament';
            
            shareButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    const platform = btn.dataset.share;
                    this.share(platform, url, title);
                });
            });
            
            if (copyBtn && shareLink) {
                copyBtn.addEventListener('click', async () => {
                    const success = await utils.copyToClipboard(shareLink.value);
                    if (success) {
                        copyBtn.innerHTML = `
                            <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="20 6 9 17 4 12"/>
                            </svg>
                            Copied!
                        `;
                        setTimeout(() => {
                            copyBtn.innerHTML = `
                                <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                                </svg>
                                Copy
                            `;
                        }, 2000);
                        utils.showToast('Link copied to clipboard!');
                    }
                });
            }
        },
        
        share(platform, url, title) {
            const encodedUrl = encodeURIComponent(url);
            const encodedTitle = encodeURIComponent(title);
            let shareUrl;
            
            switch (platform) {
                case 'facebook':
                    shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`;
                    break;
                case 'twitter':
                    shareUrl = `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}`;
                    break;
                case 'discord':
                    // Discord doesn't have a direct share URL, copy to clipboard
                    utils.copyToClipboard(url);
                    utils.showToast('Link copied! Paste it in Discord.');
                    return;
                case 'whatsapp':
                    shareUrl = `https://wa.me/?text=${encodedTitle}%20${encodedUrl}`;
                    break;
            }
            
            if (shareUrl) {
                window.open(shareUrl, '_blank', 'width=600,height=400');
            }
        }
    };

    // ============================================
    // FAQ ACCORDION
    // ============================================
    
    const FAQAccordion = {
        init() {
            const faqQuestions = utils.$$('.faq-question');
            if (faqQuestions.length === 0) return;
            
            faqQuestions.forEach(question => {
                question.addEventListener('click', () => {
                    const faqItem = question.closest('.faq-item');
                    const isActive = faqItem.classList.contains('active');
                    
                    // Close all other FAQs
                    utils.$$('.faq-item').forEach(item => item.classList.remove('active'));
                    
                    // Toggle current FAQ
                    if (!isActive) {
                        faqItem.classList.add('active');
                    }
                });
            });
        }
    };

    // ============================================
    // ADD TO CALENDAR
    // ============================================
    
    const CalendarManager = {
        init() {
            const calendarBtn = utils.$('.btn-add-calendar');
            if (!calendarBtn) return;
            
            calendarBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.generateICS();
            });
        },
        
        generateICS() {
            // Get tournament details
            const title = utils.$('.hero-title')?.textContent || 'Tournament';
            const description = utils.$('.hero-subtitle')?.textContent || '';
            
            // Get start date from data attribute or parse from DOM
            // This is a simplified version - you'd get actual dates from the page
            const startDate = new Date();
            const endDate = new Date(startDate.getTime() + 3 * 60 * 60 * 1000); // +3 hours
            
            const icsContent = this.createICSContent(title, description, startDate, endDate);
            this.downloadICS(icsContent, `${title.replace(/\s+/g, '_')}.ics`);
            
            utils.showToast('Calendar event downloaded!');
        },
        
        createICSContent(title, description, startDate, endDate) {
            const formatDate = (date) => {
                return date.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
            };
            
            return [
                'BEGIN:VCALENDAR',
                'VERSION:2.0',
                'PRODID:-//DeltaCrown//Tournament//EN',
                'BEGIN:VEVENT',
                `UID:${Date.now()}@deltacrown.com`,
                `DTSTAMP:${formatDate(new Date())}`,
                `DTSTART:${formatDate(startDate)}`,
                `DTEND:${formatDate(endDate)}`,
                `SUMMARY:${title}`,
                `DESCRIPTION:${description}`,
                'END:VEVENT',
                'END:VCALENDAR'
            ].join('\r\n');
        },
        
        downloadICS(content, filename) {
            const blob = new Blob([content], { type: 'text/calendar;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    };

    // ============================================
    // QUICK ACTIONS
    // ============================================
    
    const QuickActions = {
        init() {
            // Report Issue
            const reportBtn = utils.$('[data-action="report-issue"]');
            if (reportBtn) {
                reportBtn.addEventListener('click', () => {
                    // TODO: Open report modal or redirect to support
                    utils.showToast('Report feature coming soon!', 'info');
                });
            }
            
            // Download Rules
            const downloadRulesBtn = utils.$('[data-action="download-rules"]');
            if (downloadRulesBtn) {
                downloadRulesBtn.addEventListener('click', () => {
                    // Check if rules PDF exists
                    const rulesLink = utils.$('.btn-download-pdf');
                    if (rulesLink) {
                        rulesLink.click();
                    } else {
                        utils.showToast('Rules PDF not available', 'error');
                    }
                });
            }
            
            // Contact Support
            const contactBtn = utils.$('[data-action="contact-support"]');
            if (contactBtn) {
                contactBtn.addEventListener('click', () => {
                    // TODO: Open contact modal or redirect
                    utils.showToast('Contact feature coming soon!', 'info');
                });
            }
        }
    };

    // ============================================
    // STICKY CTA BEHAVIOR
    // ============================================
    
    const StickyCTA = {
        init() {
            this.ctaSection = utils.$('.cta-section');
            this.heroSection = utils.$('.hero-section');
            
            if (!this.ctaSection || !this.heroSection) return;
            
            this.observer = new IntersectionObserver(
                (entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            this.ctaSection.style.opacity = '0';
                            this.ctaSection.style.pointerEvents = 'none';
                        } else {
                            this.ctaSection.style.opacity = '1';
                            this.ctaSection.style.pointerEvents = 'all';
                        }
                    });
                },
                { threshold: 0.1 }
            );
            
            this.observer.observe(this.heroSection);
        }
    };

    // ============================================
    // PARTICIPANTS FILTER
    // ============================================
    
    const ParticipantsFilter = {
        init() {
            const filterSelect = utils.$('#sortParticipants');
            if (!filterSelect) return;
            
            filterSelect.addEventListener('change', (e) => {
                const sortBy = e.target.value;
                // TODO: Implement sorting logic when participants list is loaded
                console.log('Sort participants by:', sortBy);
            });
        }
    };

    // ============================================
    // SMOOTH SCROLL FOR ANCHOR LINKS
    // ============================================
    
    const SmoothScroll = {
        init() {
            utils.on(document, 'click', 'a[href^="#"]', function(e) {
                const href = this.getAttribute('href');
                if (href === '#') return;
                
                e.preventDefault();
                const target = utils.$(href);
                
                if (target) {
                    const offset = 100; // Account for sticky headers
                    const targetPosition = target.offsetTop - offset;
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            });
        }
    };

    // ============================================
    // ENHANCED COUNTDOWN TIMERS (V7 Production)
    // ============================================
    
    const CountdownManager = {
        timers: [],
        
        init() {
            // Initialize all countdown elements
            const countdownElements = utils.$$('[data-countdown-target]');
            
            countdownElements.forEach(element => {
                const targetDate = element.dataset.countdownTarget;
                const format = element.dataset.countdownFormat || 'full'; // 'full', 'compact', 'minimal'
                
                if (targetDate) {
                    const timer = new CountdownTimer(element, targetDate, format);
                    this.timers.push(timer);
                    timer.start();
                }
            });
            
            console.log(`⏱️  Initialized ${this.timers.length} countdown timer(s)`);
        },
        
        stopAll() {
            this.timers.forEach(timer => timer.stop());
        }
    };
    
    class CountdownTimer {
        constructor(element, targetDate, format = 'full') {
            this.element = element;
            this.targetDate = new Date(targetDate);
            this.format = format;
            this.interval = null;
            this.isExpired = false;
        }
        
        start() {
            this.update(); // Initial update
            this.interval = setInterval(() => this.update(), 1000);
        }
        
        stop() {
            if (this.interval) {
                clearInterval(this.interval);
                this.interval = null;
            }
        }
        
        update() {
            const now = new Date();
            const distance = this.targetDate - now;
            
            if (distance <= 0 && !this.isExpired) {
                this.handleExpired();
                return;
            }
            
            if (distance > 0) {
                const time = this.calculateTime(distance);
                this.render(time);
                
                // Add urgency styling if less than 24 hours
                if (distance < 86400000) { // 24 hours in milliseconds
                    this.element.classList.add('countdown-urgent');
                }
                
                // Add critical styling if less than 1 hour
                if (distance < 3600000) { // 1 hour in milliseconds
                    this.element.classList.add('countdown-critical');
                }
            }
        }
        
        calculateTime(distance) {
            return {
                days: Math.floor(distance / (1000 * 60 * 60 * 24)),
                hours: Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
                minutes: Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60)),
                seconds: Math.floor((distance % (1000 * 60)) / 1000),
                total: distance
            };
        }
        
        render(time) {
            let html = '';
            
            switch (this.format) {
                case 'full':
                    html = `
                        <div class="countdown-timer">
                            ${time.days > 0 ? `
                                <div class="time-unit">
                                    <span class="time-value">${time.days}</span>
                                    <span class="time-label">Day${time.days !== 1 ? 's' : ''}</span>
                                </div>
                                <span class="time-separator">:</span>
                            ` : ''}
                            <div class="time-unit">
                                <span class="time-value">${String(time.hours).padStart(2, '0')}</span>
                                <span class="time-label">Hours</span>
                            </div>
                            <span class="time-separator">:</span>
                            <div class="time-unit">
                                <span class="time-value">${String(time.minutes).padStart(2, '0')}</span>
                                <span class="time-label">Min</span>
                            </div>
                            <span class="time-separator">:</span>
                            <div class="time-unit">
                                <span class="time-value">${String(time.seconds).padStart(2, '0')}</span>
                                <span class="time-label">Sec</span>
                            </div>
                        </div>
                    `;
                    break;
                    
                case 'compact':
                    if (time.days > 0) {
                        html = `<span class="countdown-compact">${time.days}d ${time.hours}h ${time.minutes}m</span>`;
                    } else if (time.hours > 0) {
                        html = `<span class="countdown-compact">${time.hours}h ${time.minutes}m ${time.seconds}s</span>`;
                    } else {
                        html = `<span class="countdown-compact">${time.minutes}m ${time.seconds}s</span>`;
                    }
                    break;
                    
                case 'minimal':
                    if (time.days > 0) {
                        html = `<span class="countdown-minimal">${time.days}d ${time.hours}h</span>`;
                    } else if (time.hours > 0) {
                        html = `<span class="countdown-minimal">${time.hours}h ${time.minutes}m</span>`;
                    } else {
                        html = `<span class="countdown-minimal">${time.minutes}m</span>`;
                    }
                    break;
            }
            
            this.element.innerHTML = html;
        }
        
        handleExpired() {
            this.isExpired = true;
            this.stop();
            
            this.element.classList.add('countdown-expired');
            this.element.innerHTML = '<span class="countdown-expired-text">Expired</span>';
            
            // Trigger custom event
            const event = new CustomEvent('countdownExpired', {
                detail: { element: this.element }
            });
            document.dispatchEvent(event);
        }
    }
    
    // ============================================
    // PROGRESS BAR ANIMATIONS (V7 Production)
    // ============================================
    
    const ProgressBarManager = {
        init() {
            const progressBars = utils.$$('[data-progress]');
            
            progressBars.forEach(bar => {
                const targetPercent = parseFloat(bar.dataset.progress) || 0;
                this.animateProgress(bar, targetPercent);
            });
            
            console.log(`📊 Initialized ${progressBars.length} progress bar(s)`);
        },
        
        animateProgress(element, targetPercent) {
            const fill = utils.$('.progress-fill', element);
            if (!fill) return;
            
            let currentPercent = 0;
            const increment = targetPercent / 50; // 50 frames
            const duration = 1500; // 1.5 seconds
            const intervalTime = duration / 50;
            
            // Determine color based on percentage
            const color = this.getProgressColor(targetPercent);
            fill.style.backgroundColor = color;
            
            const animate = () => {
                if (currentPercent < targetPercent) {
                    currentPercent += increment;
                    if (currentPercent > targetPercent) currentPercent = targetPercent;
                    
                    fill.style.width = `${currentPercent}%`;
                    setTimeout(animate, intervalTime);
                } else {
                    // Add completion animation
                    if (targetPercent >= 100) {
                        fill.classList.add('progress-complete');
                    }
                }
            };
            
            // Delay animation until element is visible
            this.whenVisible(element, () => {
                setTimeout(animate, 100);
            });
        },
        
        getProgressColor(percent) {
            if (percent >= 100) return '#ef4444'; // Red - Full
            if (percent >= 80) return '#f59e0b'; // Orange - Almost full
            if (percent >= 50) return '#3b82f6'; // Blue - Half
            return '#10b981'; // Green - Available
        },
        
        whenVisible(element, callback) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        callback();
                        observer.disconnect();
                    }
                });
            }, { threshold: 0.1 });
            
            observer.observe(element);
        }
    };
    
    // ============================================
    // ANIMATED COUNTERS (V7 Production)
    // ============================================
    
    const CounterManager = {
        init() {
            const counters = utils.$$('[data-counter-target]');
            
            counters.forEach(counter => {
                const target = parseFloat(counter.dataset.counterTarget) || 0;
                const duration = parseInt(counter.dataset.counterDuration) || 2000;
                this.animateCounter(counter, target, duration);
            });
            
            console.log(`🔢 Initialized ${counters.length} animated counter(s)`);
        },
        
        animateCounter(element, target, duration) {
            const startValue = 0;
            const increment = target / (duration / 16); // 60fps
            let currentValue = startValue;
            
            const animate = () => {
                currentValue += increment;
                
                if (currentValue < target) {
                    element.textContent = Math.floor(currentValue).toLocaleString();
                    requestAnimationFrame(animate);
                } else {
                    element.textContent = Math.floor(target).toLocaleString();
                }
            };
            
            // Start animation when element is visible
            this.whenVisible(element, animate);
        },
        
        whenVisible(element, callback) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        callback();
                        observer.disconnect();
                    }
                });
            }, { threshold: 0.1 });
            
            observer.observe(element);
        }
    };
    
    // ============================================
    // STATUS BADGE ANIMATIONS (V7 Production)
    // ============================================
    
    const BadgeAnimator = {
        init() {
            // Animate pulse badges
            const pulseBadges = utils.$$('.badge-pulse, .pulse');
            pulseBadges.forEach(badge => {
                this.addPulseAnimation(badge);
            });
            
            // Animate status changes
            const statusBadges = utils.$$('[data-status-badge]');
            statusBadges.forEach(badge => {
                this.animateStatusBadge(badge);
            });
            
            console.log(`🎨 Initialized ${pulseBadges.length + statusBadges.length} badge animation(s)`);
        },
        
        addPulseAnimation(element) {
            if (!element.style.animation) {
                element.style.animation = 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite';
            }
        },
        
        animateStatusBadge(element) {
            // Add entrance animation
            element.style.opacity = '0';
            element.style.transform = 'scale(0.8)';
            
            setTimeout(() => {
                element.style.transition = 'all 0.3s ease-out';
                element.style.opacity = '1';
                element.style.transform = 'scale(1)';
            }, 100);
        }
    };

    // ============================================
    // INITIALIZATION
    // ============================================
    
    function init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeComponents);
        } else {
            initializeComponents();
        }
    }
    
    function initializeComponents() {
        console.log('🎮 Tournament Detail V7 - Initializing...');
        
        try {
            TabNavigation.init();
            ModalManager.init();
            CTAActions.init();
            RegistrationTimer.init();
            ShareManager.init();
            FAQAccordion.init();
            CalendarManager.init();
            QuickActions.init();
            StickyCTA.init();
            ParticipantsFilter.init();
            SmoothScroll.init();
            
            // V7 Production Enhancements
            CountdownManager.init();
            ProgressBarManager.init();
            CounterManager.init();
            BadgeAnimator.init();
            
            console.log('✅ Tournament Detail V7 - Ready!');
        } catch (error) {
            console.error('❌ Tournament Detail V7 - Initialization error:', error);
        }
    }
    
    // Start initialization
    init();

})();
