/**
 * Tournament Detail V8 - Interactive Features
 * Handles animations, counter effects, and user interactions
 */

(function() {
    'use strict';

    // ==========================================
    // INITIALIZATION
    // ==========================================
    
    document.addEventListener('DOMContentLoaded', function() {
        initCapacityAnimation();
        initScrollReveal();
        initSmoothScroll();
        initTimelineAnimation();
        initMatchTimeUpdates();
        initShareButtons();
    });

    // ==========================================
    // CAPACITY BAR ANIMATION
    // ==========================================
    
    function initCapacityAnimation() {
        const progressFill = document.querySelector('.capacity-progress-fill');
        if (!progressFill) return;
        
        const targetWidth = progressFill.style.width;
        progressFill.style.width = '0%';
        
        // Animate to target width after a small delay
        setTimeout(() => {
            progressFill.style.transition = 'width 1.5s cubic-bezier(0.4, 0, 0.2, 1)';
            progressFill.style.width = targetWidth;
        }, 300);
    }

    // ==========================================
    // SCROLL REVEAL ANIMATIONS
    // ==========================================
    
    function initScrollReveal() {
        const cards = document.querySelectorAll('.content-card, .sidebar-card');
        
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
        
        cards.forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(card);
        });
    }

    // ==========================================
    // SMOOTH SCROLL
    // ==========================================
    
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href === '#') return;
                
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // ==========================================
    // TIMELINE ANIMATION
    // ==========================================
    
    function initTimelineAnimation() {
        const timeline = document.querySelector('.timeline');
        if (!timeline) return;
        
        const items = timeline.querySelectorAll('.timeline-item');
        
        items.forEach((item, index) => {
            setTimeout(() => {
                item.style.opacity = '1';
                item.style.transform = 'translateX(0)';
            }, index * 100);
            
            item.style.opacity = '0';
            item.style.transform = 'translateX(-20px)';
            item.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        });
    }

    // ==========================================
    // MATCH TIME UPDATES
    // ==========================================
    
    function initMatchTimeUpdates() {
        const matchTimes = document.querySelectorAll('.match-time');
        if (matchTimes.length === 0) return;
        
        function updateMatchTimes() {
            matchTimes.forEach(timeEl => {
                const matchDate = new Date(timeEl.dataset.date);
                if (isNaN(matchDate)) return;
                
                const now = new Date();
                const diff = matchDate - now;
                
                if (diff < 0) {
                    // Match has started or passed
                    return;
                }
                
                // Update countdown
                const hours = Math.floor(diff / (1000 * 60 * 60));
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                
                if (hours < 24) {
                    if (hours > 0) {
                        timeEl.textContent = `Starts in ${hours}h ${minutes}m`;
                    } else {
                        timeEl.textContent = `Starts in ${minutes}m`;
                    }
                }
            });
        }
        
        // Update every minute
        updateMatchTimes();
        setInterval(updateMatchTimes, 60000);
    }

    // ==========================================
    // SHARE BUTTONS
    // ==========================================
    
    function initShareButtons() {
        // Share button hover effects
        const shareButtons = document.querySelectorAll('.share-btn');
        
        shareButtons.forEach(btn => {
            btn.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-4px) scale(1.05)';
            });
            
            btn.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
        });
    }

    // ==========================================
    // UTILITY: ANIMATE NUMBER
    // ==========================================
    
    function animateNumber(element, target, duration = 1000) {
        const start = 0;
        const increment = target / (duration / 16); // 60fps
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = Math.round(target);
                clearInterval(timer);
            } else {
                element.textContent = Math.round(current);
            }
        }, 16);
    }

    // ==========================================
    // UTILITY: FORMAT CURRENCY
    // ==========================================
    
    function formatCurrency(amount) {
        return '৳' + amount.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    // ==========================================
    // LOADING STATE MANAGEMENT
    // ==========================================
    
    function showLoading(element) {
        element.classList.add('skeleton-loading');
        element.setAttribute('aria-busy', 'true');
    }
    
    function hideLoading(element) {
        element.classList.remove('skeleton-loading');
        element.removeAttribute('aria-busy');
    }

    // ==========================================
    // TOAST NOTIFICATIONS
    // ==========================================
    
    function showToast(message, type = 'info') {
        // Check if toast container exists, create if not
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            `;
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            background: var(--bg-elevated);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-md);
            padding: 1rem 1.5rem;
            min-width: 300px;
            box-shadow: var(--shadow-lg);
            backdrop-filter: blur(10px);
            animation: slideInRight 0.3s ease;
            color: var(--text-primary);
        `;
        
        toast.textContent = message;
        toastContainer.appendChild(toast);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                toast.remove();
                if (toastContainer.children.length === 0) {
                    toastContainer.remove();
                }
            }, 300);
        }, 3000);
    }

    // ==========================================
    // PUBLIC API
    // ==========================================
    
    window.TournamentDetailV8 = {
        showToast: showToast,
        showLoading: showLoading,
        hideLoading: hideLoading,
        animateNumber: animateNumber,
        formatCurrency: formatCurrency
    };

})();

// ==========================================
// ANIMATIONS KEYFRAMES (Add to CSS if not present)
// ==========================================

// Add animation styles if they don't exist
if (!document.querySelector('#v8-animations-style')) {
    const style = document.createElement('style');
    style.id = 'v8-animations-style';
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}
