/**
 * DeltaCrown Tournament Hub V2 - Premium Edition
 * Enhanced JavaScript for Interactive Tournament Hub
 * 
 * Features:
 * - Tournament filtering
 * - Smooth scroll
 * - Scroll-to-top button
 * - Animations on scroll
 * - Mobile menu handling
 */

(function() {
    'use strict';

    // ============================================
    // INITIALIZATION
    // ============================================
    
    document.addEventListener('DOMContentLoaded', function() {
        initFilterButtons();
        initScrollToTop();
        initSmoothScroll();
        initAnimationsOnScroll();
        initLoadMore();
    });

    // ============================================
    // FILTER FUNCTIONALITY
    // ============================================
    
    function initFilterButtons() {
        const filterButtons = document.querySelectorAll('.filter-btn');
        const tournamentCards = document.querySelectorAll('.tournament-card');
        
        if (!filterButtons.length || !tournamentCards.length) return;
        
        filterButtons.forEach(button => {
            button.addEventListener('click', function() {
                const filter = this.dataset.filter;
                
                // Update active state
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                
                // Filter tournaments
                filterTournaments(filter, tournamentCards);
            });
        });
    }
    
    function filterTournaments(filter, cards) {
        let visibleCount = 0;
        
        cards.forEach(card => {
            const status = card.dataset.status;
            let shouldShow = false;
            
            switch(filter) {
                case 'all':
                    shouldShow = true;
                    break;
                case 'upcoming':
                    shouldShow = status === 'published';
                    break;
                case 'live':
                    shouldShow = status === 'running';
                    break;
                case 'registration':
                    shouldShow = status === 'published';
                    break;
                default:
                    shouldShow = true;
            }
            
            if (shouldShow) {
                card.style.display = '';
                // Animate in
                setTimeout(() => {
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, visibleCount * 50);
                visibleCount++;
            } else {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                setTimeout(() => {
                    card.style.display = 'none';
                }, 300);
            }
        });
        
        // Show empty state if no tournaments
        const grid = document.querySelector('.tournaments-grid');
        let emptyState = grid.querySelector('.tournaments-empty');
        
        if (visibleCount === 0 && !emptyState) {
            emptyState = document.createElement('div');
            emptyState.className = 'tournaments-empty';
            emptyState.innerHTML = `
                <div class="tournaments-empty-icon">🔍</div>
                <h3 class="tournaments-empty-title">No Tournaments Found</h3>
                <p class="tournaments-empty-text">Try a different filter or check back soon!</p>
            `;
            grid.appendChild(emptyState);
        } else if (visibleCount > 0 && emptyState) {
            emptyState.remove();
        }
    }

    // ============================================
    // SCROLL TO TOP BUTTON
    // ============================================
    
    function initScrollToTop() {
        const scrollBtn = document.getElementById('scrollToTop');
        if (!scrollBtn) return;
        
        // Show/hide button on scroll
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 500) {
                scrollBtn.classList.add('visible');
            } else {
                scrollBtn.classList.remove('visible');
            }
        });
        
        // Scroll to top on click
        scrollBtn.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // ============================================
    // SMOOTH SCROLL FOR ANCHOR LINKS
    // ============================================
    
    function initSmoothScroll() {
        const links = document.querySelectorAll('a[href^="#"]');
        
        links.forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href === '#') return;
                
                const target = document.querySelector(href);
                if (!target) return;
                
                e.preventDefault();
                
                const offsetTop = target.offsetTop - 80;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            });
        });
    }

    // ============================================
    // ANIMATIONS ON SCROLL (Intersection Observer)
    // ============================================
    
    function initAnimationsOnScroll() {
        // Check if Intersection Observer is supported
        if (!('IntersectionObserver' in window)) return;
        
        const animatedElements = document.querySelectorAll(
            '.tournament-card, .game-card, .how-it-works-step, .featured-card'
        );
        
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);
        
        animatedElements.forEach((element, index) => {
            // Initial state
            element.style.opacity = '0';
            element.style.transform = 'translateY(30px)';
            element.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
            
            observer.observe(element);
        });
    }

    // ============================================
    // LOAD MORE FUNCTIONALITY
    // ============================================
    
    function initLoadMore() {
        const loadMoreBtn = document.querySelector('.btn-load-more');
        if (!loadMoreBtn) return;
        
        loadMoreBtn.addEventListener('click', function() {
            // Add loading state
            const originalText = this.innerHTML;
            this.innerHTML = `
                <span>Loading...</span>
                <svg class="animate-spin" width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M10 2a8 8 0 108 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
            `;
            this.disabled = true;
            
            // Simulate API call (replace with actual AJAX request)
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
                
                // Show success message
                const message = document.createElement('div');
                message.textContent = 'No more tournaments to load';
                message.style.cssText = 'text-align: center; color: var(--color-text-muted); margin-top: 1rem;';
                this.parentElement.appendChild(message);
                this.style.display = 'none';
            }, 1500);
        });
    }

    // ============================================
    // HERO STATS COUNTER ANIMATION
    // ============================================
    
    function animateCounter(element, target, duration = 2000) {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current).toLocaleString();
        }, 16);
    }
    
    // Animate stats when they come into view
    const statsObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const value = entry.target.textContent.replace(/,/g, '');
                const target = parseInt(value);
                if (!isNaN(target)) {
                    animateCounter(entry.target, target);
                }
                statsObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    
    document.querySelectorAll('.hub-stat-value').forEach(stat => {
        statsObserver.observe(stat);
    });

    // ============================================
    // TOURNAMENT CARD HOVER EFFECTS
    // ============================================
    
    function initCardHoverEffects() {
        const cards = document.querySelectorAll('.tournament-card, .game-card');
        
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-6px)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    }
    
    // Initialize on load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCardHoverEffects);
    } else {
        initCardHoverEffects();
    }

    // ============================================
    // PARALLAX EFFECT FOR HERO
    // ============================================
    
    function initParallax() {
        const hero = document.querySelector('.hub-hero');
        if (!hero) return;
        
        window.addEventListener('scroll', function() {
            const scrolled = window.pageYOffset;
            const parallax = scrolled * 0.5;
            hero.style.transform = `translateY(${parallax}px)`;
        });
    }
    
    // Only enable on desktop
    if (window.innerWidth > 768) {
        initParallax();
    }

    // ============================================
    // MOBILE MENU HANDLING (if needed)
    // ============================================
    
    function initMobileFilters() {
        if (window.innerWidth <= 768) {
            const filterContainer = document.querySelector('.hub-filters');
            if (!filterContainer) return;
            
            // Make filters horizontally scrollable on mobile
            filterContainer.style.overflowX = 'auto';
            filterContainer.style.webkitOverflowScrolling = 'touch';
            filterContainer.style.scrollbarWidth = 'none';
            filterContainer.style.msOverflowStyle = 'none';
            
            // Hide scrollbar
            filterContainer.style.cssText += '::-webkit-scrollbar { display: none; }';
        }
    }
    
    initMobileFilters();
    window.addEventListener('resize', initMobileFilters);

    // ============================================
    // KEYBOARD NAVIGATION
    // ============================================
    
    document.addEventListener('keydown', function(e) {
        // Escape key to close modals/overlays
        if (e.key === 'Escape') {
            // Close any open modals
            const modals = document.querySelectorAll('.modal.open');
            modals.forEach(modal => modal.classList.remove('open'));
        }
        
        // Ctrl/Cmd + K to focus search (if search exists)
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.querySelector('.hub-search-input');
            if (searchInput) searchInput.focus();
        }
    });

    // ============================================
    // PERFORMANCE: LAZY LOAD IMAGES
    // ============================================
    
    function initLazyLoad() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver(function(entries) {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                        }
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }
    
    initLazyLoad();

    // ============================================
    // CONSOLE WELCOME MESSAGE
    // ============================================
    
    console.log('%c🎮 DeltaCrown Tournament Hub V2', 'color: #FF4655; font-size: 20px; font-weight: bold;');
    console.log('%cWelcome to Bangladesh\'s premier esports platform!', 'color: #00D4FF; font-size: 14px;');
    
})();

// ============================================
// CSS ANIMATIONS (added via JS)
// ============================================

// Add custom CSS for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    .animate-spin {
        animation: spin 1s linear infinite;
    }
    
    /* Smooth transitions for filtered items */
    .tournament-card,
    .game-card {
        transition: opacity 0.3s ease, transform 0.3s ease !important;
    }
`;
document.head.appendChild(style);
