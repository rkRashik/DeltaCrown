/**
 * ============================================================================
 * TOURNAMENT DETAIL V7 - POLISH & ANIMATIONS
 * Advanced interactions, loading states, and smooth UX enhancements
 * ============================================================================
 */

class TournamentPolish {
    constructor() {
        this.init();
    }

    init() {
        this.initScrollReveal();
        this.initMagneticButtons();
        this.initCounterAnimations();
        this.initTooltips();
        this.initLoadingStates();
        this.initSmoothScroll();
        this.initParallax();
        this.initCardAnimations();
    }

    /**
     * Scroll Reveal Animations
     * Reveals elements as user scrolls
     */
    initScrollReveal() {
        const revealElements = document.querySelectorAll('.scroll-reveal');
        
        if (!revealElements.length) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        revealElements.forEach(el => observer.observe(el));
    }

    /**
     * Magnetic Button Effect
     * Buttons follow cursor on hover
     */
    initMagneticButtons() {
        const magneticButtons = document.querySelectorAll('.btn-magnetic');
        
        magneticButtons.forEach(button => {
            button.addEventListener('mousemove', (e) => {
                const rect = button.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;
                
                const moveX = x * 0.2;
                const moveY = y * 0.2;
                
                button.style.transform = `translate(${moveX}px, ${moveY}px)`;
            });
            
            button.addEventListener('mouseleave', () => {
                button.style.transform = '';
            });
        });
    }

    /**
     * Counter Animations
     * Animate numbers counting up
     */
    initCounterAnimations() {
        const counters = document.querySelectorAll('[data-counter]');
        
        counters.forEach(counter => {
            const target = parseInt(counter.dataset.counter);
            const duration = 2000;
            const increment = target / (duration / 16);
            let current = 0;
            
            const updateCounter = () => {
                current += increment;
                if (current < target) {
                    counter.textContent = Math.floor(current).toLocaleString();
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = target.toLocaleString();
                }
            };
            
            // Start animation when visible
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        updateCounter();
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.5 });
            
            observer.observe(counter);
        });
    }

    /**
     * Enhanced Tooltips
     * Better tooltip positioning and timing
     */
    initTooltips() {
        const tooltipElements = document.querySelectorAll('[data-tooltip]');
        
        tooltipElements.forEach(el => {
            el.classList.add('tooltip-enhanced');
            
            // Adjust position if tooltip goes off-screen
            el.addEventListener('mouseenter', () => {
                const rect = el.getBoundingClientRect();
                const tooltip = window.getComputedStyle(el, '::before');
                
                if (rect.top < 60) {
                    el.style.setProperty('--tooltip-position', 'bottom');
                }
            });
        });
    }

    /**
     * Loading States
     * Show loading overlay for async operations
     */
    initLoadingStates() {
        // Create loading overlay if it doesn't exist
        if (!document.querySelector('.loading-overlay')) {
            const overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-content">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">Loading...</div>
                </div>
            `;
            document.body.appendChild(overlay);
        }
    }

    /**
     * Show loading overlay
     */
    showLoading(text = 'Loading...') {
        const overlay = document.querySelector('.loading-overlay');
        const loadingText = overlay.querySelector('.loading-text');
        loadingText.textContent = text;
        overlay.classList.add('active');
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        const overlay = document.querySelector('.loading-overlay');
        overlay.classList.remove('active');
    }

    /**
     * Smooth Scroll
     * Smooth scrolling for anchor links
     */
    initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                const href = anchor.getAttribute('href');
                if (href === '#') return;
                
                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    /**
     * Parallax Effect
     * Subtle parallax on scroll
     */
    initParallax() {
        const parallaxElements = document.querySelectorAll('.parallax');
        
        if (!parallaxElements.length) return;
        
        let ticking = false;
        
        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    const scrolled = window.pageYOffset;
                    
                    parallaxElements.forEach(el => {
                        const speed = el.dataset.parallaxSpeed || 0.5;
                        const yPos = -(scrolled * speed);
                        el.style.transform = `translateY(${yPos}px)`;
                    });
                    
                    ticking = false;
                });
                
                ticking = true;
            }
        });
    }

    /**
     * Card Animations
     * Stagger animation for cards
     */
    initCardAnimations() {
        const cardContainers = document.querySelectorAll('[data-stagger]');
        
        cardContainers.forEach(container => {
            const cards = container.children;
            Array.from(cards).forEach((card, index) => {
                card.classList.add('stagger-item');
                card.style.animationDelay = `${index * 0.1}s`;
            });
        });
    }

    /**
     * Ripple Effect
     * Material design ripple on click
     */
    createRipple(event) {
        const button = event.currentTarget;
        const rect = button.getBoundingClientRect();
        
        const ripple = document.createElement('span');
        ripple.classList.add('ripple');
        
        const diameter = Math.max(rect.width, rect.height);
        const radius = diameter / 2;
        
        ripple.style.width = ripple.style.height = `${diameter}px`;
        ripple.style.left = `${event.clientX - rect.left - radius}px`;
        ripple.style.top = `${event.clientY - rect.top - radius}px`;
        
        button.appendChild(ripple);
        
        setTimeout(() => ripple.remove(), 600);
    }

    /**
     * Number Change Animation
     * Highlight numbers when they change
     */
    animateNumberChange(element, newValue) {
        element.classList.add('number-changed');
        element.textContent = newValue;
        
        setTimeout(() => {
            element.classList.remove('number-changed');
        }, 800);
    }

    /**
     * Button Loading State
     * Show loading spinner on button
     */
    setButtonLoading(button, loading = true) {
        if (loading) {
            button.classList.add('btn-loading');
            button.disabled = true;
        } else {
            button.classList.remove('btn-loading');
            button.disabled = false;
        }
    }

    /**
     * Button Success State
     * Show success checkmark
     */
    setButtonSuccess(button) {
        button.classList.remove('btn-loading');
        button.classList.add('btn-success');
        
        setTimeout(() => {
            button.classList.remove('btn-success');
            button.disabled = false;
        }, 2000);
    }

    /**
     * Button Error State
     * Show error state with shake
     */
    setButtonError(button) {
        button.classList.remove('btn-loading');
        button.classList.add('btn-error');
        
        setTimeout(() => {
            button.classList.remove('btn-error');
            button.disabled = false;
        }, 2000);
    }

    /**
     * Toast Notification
     * Show temporary notification
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type} slide-up`;
        toast.textContent = message;
        
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            padding: 1rem 1.5rem;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: var(--radius);
            box-shadow: var(--shadow-lg);
            z-index: 10000;
            max-width: 400px;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * Lazy Load Images
     * Load images when they enter viewport
     */
    initLazyLoad() {
        const images = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('fade-in');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    }

    /**
     * Copy to Clipboard
     * Copy text with feedback
     */
    async copyToClipboard(text, button) {
        try {
            await navigator.clipboard.writeText(text);
            this.setButtonSuccess(button);
            this.showToast('Copied to clipboard!', 'success');
        } catch (err) {
            this.setButtonError(button);
            this.showToast('Failed to copy', 'error');
        }
    }

    /**
     * Confetti Animation
     * Celebration animation
     */
    triggerConfetti() {
        const colors = ['#00ff88', '#ff4655', '#FFD700', '#3b82f6', '#8b5cf6'];
        const confettiCount = 50;
        
        for (let i = 0; i < confettiCount; i++) {
            const confetti = document.createElement('div');
            confetti.style.cssText = `
                position: fixed;
                width: 10px;
                height: 10px;
                background: ${colors[Math.floor(Math.random() * colors.length)]};
                top: -10px;
                left: ${Math.random() * 100}vw;
                opacity: 1;
                transform: rotate(${Math.random() * 360}deg);
                pointer-events: none;
                z-index: 10001;
            `;
            
            document.body.appendChild(confetti);
            
            const animation = confetti.animate([
                { transform: `translateY(0) rotate(0deg)`, opacity: 1 },
                { transform: `translateY(100vh) rotate(${Math.random() * 720}deg)`, opacity: 0 }
            ], {
                duration: 2000 + Math.random() * 1000,
                easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
            });
            
            animation.onfinish = () => confetti.remove();
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.tournamentPolish = new TournamentPolish();
    });
} else {
    window.tournamentPolish = new TournamentPolish();
}
