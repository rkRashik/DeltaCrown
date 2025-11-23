/* ====================================
   DeltaCrown Tournament Hub V2.0
   Enhanced JavaScript with Cinematic Effects
   ==================================== */

(function() {
    'use strict';
    
    // ====================================
    // Initialize All Features
    // ====================================
    document.addEventListener('DOMContentLoaded', function() {
        initStatCounters();
        initLiveTicker();
        initSearch();
        initFilters();
        initSort();
        initMobileFilterPanel();
        initCardAnimations();
        initScrollToTop();
        initViewSwitcher();
        initCinematicEffects();
    });
    
    // ====================================
    // Animated Stat Counters
    // ====================================
    function initStatCounters() {
        const statCards = document.querySelectorAll('.stat-card');
        
        const observerOptions = {
            threshold: 0.5,
            rootMargin: '0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const statValue = entry.target.querySelector('.stat-value');
                    const targetCount = parseInt(statValue.dataset.count);
                    
                    if (targetCount && !isNaN(targetCount)) {
                        animateCounter(statValue, targetCount);
                    }
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);
        
        statCards.forEach(card => observer.observe(card));
    }
    
    function animateCounter(element, target) {
        let current = 0;
        const increment = target / 50;
        const duration = 1500;
        const stepTime = duration / 50;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, stepTime);
    }
    
    // ====================================
    // Live Ticker Animation
    // ====================================
    function initLiveTicker() {
        const ticker = document.getElementById('live-ticker');
        if (!ticker) return;
        
        const messages = [
            `${ticker.textContent.trim()}`,
            "🔥 50+ Tournaments Starting This Week • Register Now!",
            "🎮 New PUBG Mobile Tournament • ৳1L Prize Pool",
            "⚡ Valorant Championship Live • Watch Now!",
            "🏆 Free Fire Masters • Registration Closing Soon"
        ];
        
        let currentIndex = 0;
        
        setInterval(() => {
            currentIndex = (currentIndex + 1) % messages.length;
            
            ticker.style.opacity = '0';
            ticker.style.transform = 'translateY(10px)';
            
            setTimeout(() => {
                ticker.innerHTML = `<span>${messages[currentIndex]}</span>`;
                ticker.style.opacity = '1';
                ticker.style.transform = 'translateY(0)';
            }, 300);
        }, 5000);
        
        // Add transition styles
        ticker.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    }
    
    // ====================================
    // Debounced Search
    // ====================================
    function initSearch() {
        const searchInput = document.querySelector('.search-input-v2');
        if (!searchInput) return;
        
        let debounceTimer;
        const form = searchInput.closest('form');
        
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            
            debounceTimer = setTimeout(() => {
                if (searchInput.value.length >= 2 || searchInput.value.length === 0) {
                    form.submit();
                }
            }, 500);
        });
        
        // Add loading indicator
        const searchIcon = document.querySelector('.search-icon-wrapper i');
        searchInput.addEventListener('input', function() {
            if (this.value.length > 0) {
                searchIcon.className = 'fas fa-spinner fa-spin';
                setTimeout(() => {
                    searchIcon.className = 'fas fa-search';
                }, 600);
            }
        });
    }
    
    // ====================================
    // Auto-Submit Filters
    // ====================================
    function initFilters() {
        const filterForm = document.getElementById('filters-form-v2');
        if (!filterForm) return;
        
        const radioInputs = filterForm.querySelectorAll('input[type="radio"]');
        
        radioInputs.forEach(input => {
            input.addEventListener('change', function() {
                // Add visual feedback
                const option = this.closest('.filter-option-v2');
                option.style.transform = 'scale(0.95)';
                
                setTimeout(() => {
                    option.style.transform = 'scale(1)';
                    filterForm.submit();
                }, 150);
            });
        });
        
        // Reset filters button
        const resetBtn = document.getElementById('reset-filters');
        if (resetBtn) {
            resetBtn.addEventListener('click', function() {
                window.location.href = window.location.pathname;
            });
        }
    }
    
    // ====================================
    // Sort Dropdown
    // ====================================
    function initSort() {
        const sortSelect = document.getElementById('sort-select-v2');
        if (!sortSelect) return;
        
        sortSelect.addEventListener('change', function() {
            const url = new URL(window.location);
            url.searchParams.set('sort', this.value);
            
            // Add loading animation
            const grid = document.getElementById('tournaments-grid');
            if (grid) {
                grid.style.opacity = '0.5';
                grid.style.transform = 'scale(0.98)';
            }
            
            window.location.href = url.toString();
        });
    }
    
    // ====================================
    // Mobile Filter Panel
    // ====================================
    function initMobileFilterPanel() {
        const openBtn = document.getElementById('open-filters');
        const closeBtn = document.getElementById('close-filters');
        const panel = document.getElementById('filters-panel');
        
        if (!openBtn || !closeBtn || !panel) return;
        
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'filter-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(4px);
            z-index: 999;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
        `;
        document.body.appendChild(overlay);
        
        function openPanel() {
            panel.classList.add('active');
            overlay.style.opacity = '1';
            overlay.style.visibility = 'visible';
            document.body.style.overflow = 'hidden';
        }
        
        function closePanel() {
            panel.classList.remove('active');
            overlay.style.opacity = '0';
            overlay.style.visibility = 'hidden';
            document.body.style.overflow = '';
        }
        
        openBtn.addEventListener('click', openPanel);
        closeBtn.addEventListener('click', closePanel);
        overlay.addEventListener('click', closePanel);
    }
    
    // ====================================
    // Tournament Card Animations
    // ====================================
    function initCardAnimations() {
        const cards = document.querySelectorAll('.dc-tournament-card');
        if (cards.length === 0) return;
        
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        entry.target.style.animationDelay = `${index * 0.1}s`;
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }, index * 50);
                    
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);
        
        cards.forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(30px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(card);
        });
        
        // Add stagger animation for newly loaded cards
        addStaggerAnimation();
    }
    
    function addStaggerAnimation() {
        const cards = document.querySelectorAll('.dc-tournament-card');
        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.05}s`;
        });
    }
    
    // ====================================
    // Scroll to Top Button
    // ====================================
    function initScrollToTop() {
        const btn = document.getElementById('back-to-top');
        if (!btn) return;
        
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 500) {
                btn.classList.add('visible');
            } else {
                btn.classList.remove('visible');
            }
        });
        
        btn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
    
    // ====================================
    // View Switcher (Grid/List)
    // ====================================
    function initViewSwitcher() {
        const viewBtns = document.querySelectorAll('.view-btn');
        const grid = document.getElementById('tournaments-grid');
        
        if (!grid) return;
        
        viewBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                viewBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                
                const view = this.dataset.view;
                
                if (view === 'list') {
                    grid.style.gridTemplateColumns = '1fr';
                    grid.querySelectorAll('.dc-tournament-card').forEach(card => {
                        card.style.display = 'flex';
                        card.style.flexDirection = 'row';
                    });
                } else {
                    grid.style.gridTemplateColumns = '';
                    grid.querySelectorAll('.dc-tournament-card').forEach(card => {
                        card.style.display = '';
                        card.style.flexDirection = '';
                    });
                }
            });
        });
    }
    
    // ====================================
    // Cinematic Effects
    // ====================================
    function initCinematicEffects() {
        // Parallax scrolling for hero section
        initParallax();
        
        // Mouse move effects
        initMouseEffects();
        
        // Progress bar animations
        initProgressBars();
        
        // Glow effects on hover
        initGlowEffects();
    }
    
    function initParallax() {
        const hero = document.querySelector('.hero-cinematic');
        if (!hero) return;
        
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const rate = scrolled * 0.5;
            
            hero.style.transform = `translateY(${rate}px)`;
            hero.style.opacity = 1 - (scrolled / 600);
        });
    }
    
    function initMouseEffects() {
        const orbs = document.querySelectorAll('.orb');
        if (orbs.length === 0) return;
        
        let mouseX = 0;
        let mouseY = 0;
        
        document.addEventListener('mousemove', (e) => {
            mouseX = e.clientX / window.innerWidth;
            mouseY = e.clientY / window.innerHeight;
            
            orbs.forEach((orb, index) => {
                const speed = (index + 1) * 20;
                const x = mouseX * speed;
                const y = mouseY * speed;
                
                orb.style.transform = `translate(${x}px, ${y}px)`;
            });
        });
    }
    
    function initProgressBars() {
        const progressBars = document.querySelectorAll('.dc-progress-bar');
        if (progressBars.length === 0) return;
        
        const observerOptions = {
            threshold: 0.5
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const bar = entry.target;
                    const width = bar.style.width;
                    
                    bar.style.width = '0%';
                    
                    setTimeout(() => {
                        bar.style.width = width;
                    }, 100);
                    
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);
        
        progressBars.forEach(bar => observer.observe(bar));
    }
    
    function initGlowEffects() {
        const cards = document.querySelectorAll('.dc-tournament-card');
        
        cards.forEach(card => {
            card.addEventListener('mouseenter', function(e) {
                this.style.transition = 'all 0.3s ease';
            });
            
            card.addEventListener('mousemove', function(e) {
                const rect = this.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                this.style.setProperty('--mouse-x', x + 'px');
                this.style.setProperty('--mouse-y', y + 'px');
            });
        });
    }
    
    // ====================================
    // Dynamic Loading Skeleton
    // ====================================
    function showLoadingSkeleton() {
        const grid = document.getElementById('tournaments-grid');
        if (!grid) return;
        
        grid.innerHTML = Array(6).fill().map(() => `
            <div class="skeleton-card">
                <div class="skeleton-image"></div>
                <div class="skeleton-content">
                    <div class="skeleton-title"></div>
                    <div class="skeleton-meta"></div>
                    <div class="skeleton-meta"></div>
                    <div class="skeleton-actions"></div>
                </div>
            </div>
        `).join('');
    }
    
    // ====================================
    // Live Updates Simulation
    // ====================================
    function initLiveUpdates() {
        // This would connect to a WebSocket or polling mechanism
        // For now, it's a placeholder for future real-time features
        
        setInterval(() => {
            updateLiveBadges();
            updateStatCards();
        }, 30000); // Update every 30 seconds
    }
    
    function updateLiveBadges() {
        const liveBadges = document.querySelectorAll('.dc-badge-live');
        liveBadges.forEach(badge => {
            badge.style.animation = 'none';
            setTimeout(() => {
                badge.style.animation = '';
            }, 10);
        });
    }
    
    function updateStatCards() {
        // Placeholder for real-time stat updates
        const statValues = document.querySelectorAll('.stat-value[data-count]');
        statValues.forEach(stat => {
            const currentCount = parseInt(stat.dataset.count);
            // Simulate small changes
            const newCount = currentCount + Math.floor(Math.random() * 3);
            stat.dataset.count = newCount;
        });
    }
    
    // ====================================
    // Keyboard Navigation
    // ====================================
    document.addEventListener('keydown', function(e) {
        // Escape to close filter panel
        if (e.key === 'Escape') {
            const panel = document.getElementById('filters-panel');
            if (panel && panel.classList.contains('active')) {
                panel.classList.remove('active');
                const overlay = document.querySelector('.filter-overlay');
                if (overlay) {
                    overlay.style.opacity = '0';
                    overlay.style.visibility = 'hidden';
                }
            }
        }
        
        // Ctrl/Cmd + K to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.search-input-v2');
            if (searchInput) {
                searchInput.focus();
            }
        }
    });
    
    // ====================================
    // Performance Optimization
    // ====================================
    
    // Lazy load images
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    observer.unobserve(img);
                }
            });
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }
    
    // Debounce scroll events
    let scrollTimeout;
    window.addEventListener('scroll', function() {
        clearTimeout(scrollTimeout);
        scrollTimeout = setTimeout(() => {
            // Scroll-based animations here
        }, 50);
    }, { passive: true });
    
    // ====================================
    // Accessibility Enhancements
    // ====================================
    
    // Add focus indicators
    const interactiveElements = document.querySelectorAll('a, button, input, select');
    interactiveElements.forEach(element => {
        element.addEventListener('focus', function() {
            this.style.outline = '2px solid var(--dc-primary)';
            this.style.outlineOffset = '2px';
        });
        
        element.addEventListener('blur', function() {
            this.style.outline = '';
            this.style.outlineOffset = '';
        });
    });
    
    // Announce dynamic content changes
    function announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('role', 'status');
        announcement.setAttribute('aria-live', 'polite');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            announcement.remove();
        }, 1000);
    }
    
    // ====================================
    // Error Handling
    // ====================================
    window.addEventListener('error', function(e) {
        console.error('Tournament Hub Error:', e.error);
        // Could send to analytics or error tracking service
    });
    
    // ====================================
    // Analytics Tracking (Placeholder)
    // ====================================
    function trackEvent(category, action, label) {
        // Placeholder for analytics integration
        console.log('Event:', category, action, label);
        
        // Example: Google Analytics
        // if (typeof gtag !== 'undefined') {
        //     gtag('event', action, {
        //         'event_category': category,
        //         'event_label': label
        //     });
        // }
    }
    
    // Track filter usage
    document.querySelectorAll('input[type="radio"]').forEach(input => {
        input.addEventListener('change', function() {
            trackEvent('Filters', 'Change', this.name + ':' + this.value);
        });
    });
    
    // Track search usage
    const searchInput = document.querySelector('.search-input-v2');
    if (searchInput) {
        searchInput.addEventListener('blur', function() {
            if (this.value) {
                trackEvent('Search', 'Query', this.value);
            }
        });
    }
    
    // Track CTA clicks
    document.querySelectorAll('.cta-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            trackEvent('CTA', 'Click', this.textContent.trim());
        });
    });
    
})();
