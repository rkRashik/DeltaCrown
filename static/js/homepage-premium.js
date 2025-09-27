/**
 * DeltaCrown Premium Homepage JavaScript
 * Interactive Features & Animations
 */

class PremiumHomepage {
    constructor() {
        this.currentTestimonial = 0;
        this.testimonialInterval = null;
        this.particleCanvas = null;
        this.particleCtx = null;
        this.particles = [];
        this.theme = this.getStoredTheme();
        
        this.init();
    }

    init() {
        this.setTheme(this.theme);
        this.initParticles();
        this.initTestimonialCarousel();
        this.initCounters();
        this.initScrollAnimations();
        this.initThemeToggle();
        this.initGameCardInteractions();
        this.initTournamentTicker();
        this.initSmoothScrolling();
        this.bindEvents();
    }

    // Theme Management
    getStoredTheme() {
        const stored = localStorage.getItem('deltacrown-theme');
        if (stored) return stored;
        
        // Auto-detect system preference
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    setTheme(theme) {
        this.theme = theme;
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('deltacrown-theme', theme);
        
        // Update theme toggle icon
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            const lightIcon = themeToggle.querySelector('.light-icon');
            const darkIcon = themeToggle.querySelector('.dark-icon');
            
            if (theme === 'dark') {
                lightIcon.style.display = 'none';
                darkIcon.style.display = 'block';
            } else {
                lightIcon.style.display = 'block';
                darkIcon.style.display = 'none';
            }
        }
    }

    toggleTheme() {
        const newTheme = this.theme === 'light' ? 'dark' : 'light';
        this.setTheme(newTheme);
    }

    initThemeToggle() {
        const themeToggle = document.querySelector('.theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    // Particle Animation System
    initParticles() {
        const heroSection = document.querySelector('.hero-section');
        if (!heroSection) return;

        // Create canvas for particles
        this.particleCanvas = document.createElement('canvas');
        this.particleCanvas.style.position = 'absolute';
        this.particleCanvas.style.top = '0';
        this.particleCanvas.style.left = '0';
        this.particleCanvas.style.width = '100%';
        this.particleCanvas.style.height = '100%';
        this.particleCanvas.style.pointerEvents = 'none';
        this.particleCanvas.style.zIndex = '1';
        
        const heroBackground = heroSection.querySelector('.hero-background');
        if (heroBackground) {
            heroBackground.appendChild(this.particleCanvas);
        }

        this.particleCtx = this.particleCanvas.getContext('2d');
        this.resizeCanvas();
        this.createParticles();
        this.animateParticles();

        // Resize handler
        window.addEventListener('resize', () => this.resizeCanvas());
    }

    resizeCanvas() {
        if (!this.particleCanvas) return;
        
        const rect = this.particleCanvas.parentElement.getBoundingClientRect();
        this.particleCanvas.width = rect.width;
        this.particleCanvas.height = rect.height;
    }

    createParticles() {
        const particleCount = Math.min(50, Math.floor(window.innerWidth / 20));
        
        for (let i = 0; i < particleCount; i++) {
            this.particles.push({
                x: Math.random() * this.particleCanvas.width,
                y: Math.random() * this.particleCanvas.height,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                radius: Math.random() * 2 + 1,
                opacity: Math.random() * 0.5 + 0.1,
                color: this.getRandomParticleColor()
            });
        }
    }

    getRandomParticleColor() {
        const colors = ['#FF6B35', '#4ECDC4', '#45B7D1', '#00ffff', '#ff00ff'];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    animateParticles() {
        if (!this.particleCtx || !this.particleCanvas) return;

        this.particleCtx.clearRect(0, 0, this.particleCanvas.width, this.particleCanvas.height);

        this.particles.forEach(particle => {
            // Update position
            particle.x += particle.vx;
            particle.y += particle.vy;

            // Wrap around edges
            if (particle.x < 0) particle.x = this.particleCanvas.width;
            if (particle.x > this.particleCanvas.width) particle.x = 0;
            if (particle.y < 0) particle.y = this.particleCanvas.height;
            if (particle.y > this.particleCanvas.height) particle.y = 0;

            // Draw particle
            this.particleCtx.globalAlpha = particle.opacity;
            this.particleCtx.fillStyle = particle.color;
            this.particleCtx.beginPath();
            this.particleCtx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
            this.particleCtx.fill();
        });

        requestAnimationFrame(() => this.animateParticles());
    }

    // Testimonial Carousel
    initTestimonialCarousel() {
        const testimonials = document.querySelectorAll('.testimonial-card');
        const prevBtn = document.querySelector('.carousel-prev');
        const nextBtn = document.querySelector('.carousel-next');

        if (!testimonials.length) return;

        // Auto-rotate testimonials
        this.testimonialInterval = setInterval(() => {
            this.nextTestimonial();
        }, 5000);

        // Manual controls
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                this.prevTestimonial();
                this.resetCarouselInterval();
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                this.nextTestimonial();
                this.resetCarouselInterval();
            });
        }

        // Initial display
        this.showTestimonial(0);
    }

    showTestimonial(index) {
        const testimonials = document.querySelectorAll('.testimonial-card');
        const wrapper = document.querySelector('.testimonials-wrapper');
        
        if (!testimonials.length || !wrapper) return;

        this.currentTestimonial = index;
        const translateX = -index * 100;
        wrapper.style.transform = `translateX(${translateX}%)`;
    }

    nextTestimonial() {
        const testimonials = document.querySelectorAll('.testimonial-card');
        if (!testimonials.length) return;

        const nextIndex = (this.currentTestimonial + 1) % testimonials.length;
        this.showTestimonial(nextIndex);
    }

    prevTestimonial() {
        const testimonials = document.querySelectorAll('.testimonial-card');
        if (!testimonials.length) return;

        const prevIndex = this.currentTestimonial === 0 ? testimonials.length - 1 : this.currentTestimonial - 1;
        this.showTestimonial(prevIndex);
    }

    resetCarouselInterval() {
        if (this.testimonialInterval) {
            clearInterval(this.testimonialInterval);
        }
        this.testimonialInterval = setInterval(() => {
            this.nextTestimonial();
        }, 5000);
    }

    // Animated Counters
    initCounters() {
        const counters = document.querySelectorAll('.stat-number');
        const observerOptions = {
            threshold: 0.5,
            rootMargin: '0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        counters.forEach(counter => observer.observe(counter));
    }

    animateCounter(element) {
        const finalValue = element.textContent.replace(/[^0-9.]/g, '');
        const duration = 2000;
        const increment = finalValue / (duration / 16);
        let currentValue = 0;

        const updateCounter = () => {
            currentValue += increment;
            if (currentValue < finalValue) {
                element.textContent = this.formatNumber(Math.floor(currentValue));
                requestAnimationFrame(updateCounter);
            } else {
                element.textContent = this.formatNumber(finalValue);
            }
        };

        updateCounter();
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    // Scroll Animations
    initScrollAnimations() {
        // Initialize AOS (Animate On Scroll) if available
        if (typeof AOS !== 'undefined') {
            AOS.init({
                duration: 800,
                easing: 'ease-out-cubic',
                once: true,
                offset: 100
            });
        }

        // Custom scroll animations for elements without AOS
        const animatedElements = document.querySelectorAll('.game-card, .feature-card, .stat-card');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.1 });

        animatedElements.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(el);
        });
    }

    // Game Card Interactions
    initGameCardInteractions() {
        const gameCards = document.querySelectorAll('.game-card');
        
        gameCards.forEach(card => {
            card.addEventListener('mouseenter', (e) => {
                this.addCardGlow(e.currentTarget);
            });

            card.addEventListener('mouseleave', (e) => {
                this.removeCardGlow(e.currentTarget);
            });
        });
    }

    addCardGlow(card) {
        const gameColor = this.getGameColor(card);
        card.style.boxShadow = `0 20px 40px ${gameColor}30, 0 0 0 1px ${gameColor}20`;
    }

    removeCardGlow(card) {
        card.style.boxShadow = '';
    }

    getGameColor(card) {
        const gameTitle = card.querySelector('.game-title')?.textContent.toLowerCase();
        const colorMap = {
            'valorant': '#FF4654',
            'csgo': '#F5A623',
            'efootball': '#1A5490',
            'codm': '#FF6B35',
            'freefire': '#FF5722',
            'mlbb': '#4A90E2'
        };

        for (const [game, color] of Object.entries(colorMap)) {
            if (gameTitle && gameTitle.includes(game)) {
                return color;
            }
        }

        return '#FF6B35'; // Default color
    }

    // Tournament Ticker
    initTournamentTicker() {
        const ticker = document.querySelector('.ticker-scroll');
        if (!ticker) return;

        // Pause animation on hover
        ticker.addEventListener('mouseenter', () => {
            ticker.style.animationPlayState = 'paused';
        });

        ticker.addEventListener('mouseleave', () => {
            ticker.style.animationPlayState = 'running';
        });
    }

    // Smooth Scrolling
    initSmoothScrolling() {
        const scrollIndicator = document.querySelector('.hero-scroll-indicator');
        const smoothScrollLinks = document.querySelectorAll('a[href^="#"]');

        // Scroll indicator click
        if (scrollIndicator) {
            scrollIndicator.addEventListener('click', () => {
                const gamesSection = document.querySelector('.games-section');
                if (gamesSection) {
                    gamesSection.scrollIntoView({ behavior: 'smooth' });
                }
            });
        }

        // Smooth scroll for anchor links
        smoothScrollLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                const targetId = link.getAttribute('href');
                const targetElement = document.querySelector(targetId);
                
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
    }

    // Event Bindings
    bindEvents() {
        // Window resize
        window.addEventListener('resize', this.debounce(() => {
            this.resizeCanvas();
        }, 250));

        // System theme change detection
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('deltacrown-theme')) {
                this.setTheme(e.matches ? 'dark' : 'light');
            }
        });

        // Visibility change (pause animations when tab is not visible)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseAnimations();
            } else {
                this.resumeAnimations();
            }
        });

        // Keyboard navigation for carousel
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                this.prevTestimonial();
                this.resetCarouselInterval();
            } else if (e.key === 'ArrowRight') {
                this.nextTestimonial();
                this.resetCarouselInterval();
            }
        });
    }

    pauseAnimations() {
        if (this.testimonialInterval) {
            clearInterval(this.testimonialInterval);
        }
    }

    resumeAnimations() {
        this.initTestimonialCarousel();
    }

    // Utility function for debouncing
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Performance monitoring
    reportPerformance() {
        if ('performance' in window) {
            window.addEventListener('load', () => {
                const perfData = performance.getEntriesByType('navigation')[0];
                console.log('Page Load Time:', Math.round(perfData.loadEventEnd - perfData.loadEventStart));
            });
        }
    }

    // Accessibility enhancements
    enhanceAccessibility() {
        // Add focus indicators for keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });

        // Skip to content link
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.textContent = 'Skip to main content';
        skipLink.className = 'skip-link';
        skipLink.style.cssText = `
            position: absolute;
            top: -40px;
            left: 6px;
            background: var(--accent-primary);
            color: white;
            padding: 8px;
            text-decoration: none;
            transition: top 0.3s;
            z-index: 100000;
        `;

        skipLink.addEventListener('focus', () => {
            skipLink.style.top = '6px';
        });

        skipLink.addEventListener('blur', () => {
            skipLink.style.top = '-40px';
        });

        document.body.insertBefore(skipLink, document.body.firstChild);
    }
}

// Game Card Enhanced Interactions
class GameCardEnhancer {
    constructor() {
        this.init();
    }

    init() {
        this.addHoverEffects();
        this.addClickEffects();
        this.addFocusEffects();
    }

    addHoverEffects() {
        const gameCards = document.querySelectorAll('.game-card');
        
        gameCards.forEach(card => {
            card.addEventListener('mouseenter', (e) => {
                this.handleMouseEnter(e.currentTarget);
            });

            card.addEventListener('mouseleave', (e) => {
                this.handleMouseLeave(e.currentTarget);
            });

            card.addEventListener('mousemove', (e) => {
                this.handleMouseMove(e);
            });
        });
    }

    handleMouseEnter(card) {
        const gameImg = card.querySelector('.game-bg img');
        if (gameImg) {
            gameImg.style.transform = 'scale(1.1)';
        }

        // Add subtle rotation effect
        card.style.transform = 'translateY(-10px) rotateX(5deg)';
    }

    handleMouseLeave(card) {
        const gameImg = card.querySelector('.game-bg img');
        if (gameImg) {
            gameImg.style.transform = 'scale(1)';
        }

        card.style.transform = 'translateY(0) rotateX(0)';
    }

    handleMouseMove(e) {
        const card = e.currentTarget;
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        const rotateX = (y - centerY) / 10;
        const rotateY = (centerX - x) / 10;
        
        card.style.transform = `translateY(-10px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
    }

    addClickEffects() {
        const gameButtons = document.querySelectorAll('.btn-game');
        
        gameButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.createRippleEffect(e);
            });
        });
    }

    createRippleEffect(e) {
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
        `;

        button.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    addFocusEffects() {
        const focusableElements = document.querySelectorAll('.game-card, .btn, .carousel-btn');
        
        focusableElements.forEach(element => {
            element.addEventListener('focus', (e) => {
                e.currentTarget.style.outline = '2px solid var(--accent-primary)';
                e.currentTarget.style.outlineOffset = '2px';
            });

            element.addEventListener('blur', (e) => {
                e.currentTarget.style.outline = 'none';
            });
        });
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new PremiumHomepage();
    new GameCardEnhancer();
});

// Add CSS animations via JavaScript (for ripple effect)
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }

    .keyboard-navigation *:focus {
        outline: 2px solid var(--accent-primary) !important;
        outline-offset: 2px !important;
    }

    .skip-link:focus {
        top: 6px !important;
    }
`;
document.head.appendChild(style);

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PremiumHomepage, GameCardEnhancer };
}