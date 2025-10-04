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
    // TAB NAVIGATION
    // ============================================
    
    const TabNavigation = {
        init() {
            this.tabLinks = utils.$$('.tab-link');
            this.tabPanels = utils.$$('.tab-panel');
            
            if (this.tabLinks.length === 0) return;
            
            // Handle tab clicks
            this.tabLinks.forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const tabName = link.dataset.tab;
                    this.switchTab(tabName);
                });
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
        },
        
        switchTab(tabName, updateHistory = true) {
            // Remove active from all tabs
            this.tabLinks.forEach(link => link.classList.remove('active'));
            this.tabPanels.forEach(panel => panel.classList.remove('active'));
            
            // Add active to selected tab
            const activeLink = utils.$(`.tab-link[data-tab="${tabName}"]`);
            const activePanel = utils.$(`#tab-${tabName}`);
            
            if (activeLink && activePanel) {
                activeLink.classList.add('active');
                activePanel.classList.add('active');
                
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
    // MODAL MANAGEMENT
    // ============================================
    
    const ModalManager = {
        init() {
            this.modals = utils.$$('.modal');
            if (this.modals.length === 0) return;
            
            // Close modal on backdrop click
            this.modals.forEach(modal => {
                const backdrop = utils.$('.modal-backdrop', modal);
                const closeBtn = utils.$('.modal-close', modal);
                
                if (backdrop) {
                    backdrop.addEventListener('click', () => this.close(modal));
                }
                
                if (closeBtn) {
                    closeBtn.addEventListener('click', () => this.close(modal));
                }
            });
            
            // Close modal on Escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    const activeModal = utils.$('.modal.active');
                    if (activeModal) this.close(activeModal);
                }
            });
        },
        
        open(modalId) {
            const modal = utils.$(`#${modalId}`);
            if (modal) {
                modal.classList.add('active');
                document.body.style.overflow = 'hidden';
            }
        },
        
        close(modal) {
            if (typeof modal === 'string') {
                modal = utils.$(`#${modal}`);
            }
            if (modal) {
                modal.classList.remove('active');
                document.body.style.overflow = '';
            }
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
            
            console.log('✅ Tournament Detail V7 - Ready!');
        } catch (error) {
            console.error('❌ Tournament Detail V7 - Initialization error:', error);
        }
    }
    
    // Start initialization
    init();

})();
