/**
 * DeltaCrown Profile Page - Interactive Features
 * Smooth animations, tooltips, and dynamic interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // ===== Smooth Scroll to Top =====
    function scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
    
    // ===== Copy to Clipboard =====
    function copyToClipboard(text, button) {
        navigator.clipboard.writeText(text).then(() => {
            // Visual feedback
            const originalText = button.textContent;
            button.textContent = 'Copied!';
            button.style.background = 'rgba(16, 185, 129, 0.2)';
            
            setTimeout(() => {
                button.textContent = originalText;
                button.style.background = '';
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    }
    
    // Make game IGNs clickable to copy
    document.querySelectorAll('.game-ign').forEach(element => {
        element.style.cursor = 'pointer';
        element.title = 'Click to copy';
        
        element.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            copyToClipboard(this.textContent.trim(), this);
        });
    });
    
    // ===== Stats Counter Animation =====
    function animateCounter(element, target, duration = 1000) {
        const start = 0;
        const increment = target / (duration / 16); // 60fps
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current);
            }
        }, 16);
    }
    
    // Animate stat values on page load
    const observerOptions = {
        threshold: 0.5,
        rootMargin: '0px'
    };
    
    const statsObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const valueElement = entry.target.querySelector('.stat-value');
                if (valueElement && !valueElement.dataset.animated) {
                    valueElement.dataset.animated = 'true';
                    const text = valueElement.textContent;
                    const number = parseInt(text.replace(/\D/g, ''));
                    if (!isNaN(number) && number > 0) {
                        const prefix = text.match(/[^\d]/g)?.join('') || '';
                        valueElement.textContent = '0';
                        
                        let current = 0;
                        const increment = number / 60; // Animate over ~1 second at 60fps
                        
                        const timer = setInterval(() => {
                            current += increment;
                            if (current >= number) {
                                valueElement.textContent = prefix + number.toLocaleString();
                                clearInterval(timer);
                            } else {
                                valueElement.textContent = prefix + Math.floor(current).toLocaleString();
                            }
                        }, 16);
                    }
                }
                statsObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.stat-card').forEach(card => {
        statsObserver.observe(card);
    });
    
    // ===== XP Bar Animation =====
    const xpBar = document.querySelector('.xp-bar');
    if (xpBar) {
        const targetWidth = xpBar.style.width;
        xpBar.style.width = '0%';
        
        setTimeout(() => {
            xpBar.style.width = targetWidth;
        }, 300);
    }
    
    // ===== Badge Tooltips =====
    document.querySelectorAll('.badge-item').forEach(badge => {
        badge.addEventListener('mouseenter', function() {
            const tooltip = this.getAttribute('title');
            if (tooltip) {
                showTooltip(this, tooltip);
            }
        });
        
        badge.addEventListener('mouseleave', function() {
            hideTooltip();
        });
    });
    
    let tooltipElement = null;
    
    function showTooltip(element, text) {
        hideTooltip();
        
        tooltipElement = document.createElement('div');
        tooltipElement.className = 'custom-tooltip';
        tooltipElement.textContent = text;
        tooltipElement.style.cssText = `
            position: absolute;
            background: rgba(15, 23, 42, 0.95);
            color: #f1f5f9;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 0.875rem;
            z-index: 1000;
            pointer-events: none;
            max-width: 200px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(148, 163, 184, 0.2);
            backdrop-filter: blur(10px);
        `;
        
        document.body.appendChild(tooltipElement);
        
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltipElement.getBoundingClientRect();
        
        tooltipElement.style.left = `${rect.left + (rect.width - tooltipRect.width) / 2}px`;
        tooltipElement.style.top = `${rect.top - tooltipRect.height - 8}px`;
    }
    
    function hideTooltip() {
        if (tooltipElement) {
            tooltipElement.remove();
            tooltipElement = null;
        }
    }
    
    // ===== Parallax Banner Effect =====
    const banner = document.querySelector('.profile-banner');
    if (banner) {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const rate = scrolled * 0.5;
            banner.style.transform = `translateY(${rate}px)`;
        });
    }
    
    // ===== Social Link Tracking (Analytics ready) =====
    document.querySelectorAll('.social-link').forEach(link => {
        link.addEventListener('click', function(e) {
            const platform = this.dataset.platform;
            console.log(`Social link clicked: ${platform}`);
            // Add analytics tracking here
        });
    });
    
    // ===== Lazy Load Images =====
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
    
    // ===== Stagger Animation for Cards =====
    const cards = document.querySelectorAll('.content-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
    
    // ===== Mobile Touch Interactions =====
    if ('ontouchstart' in window) {
        document.querySelectorAll('.stat-card, .badge-item, .team-item').forEach(element => {
            element.addEventListener('touchstart', function() {
                this.style.transform = 'scale(0.98)';
            });
            
            element.addEventListener('touchend', function() {
                this.style.transform = '';
            });
        });
    }
    
    // ===== Print Preparation =====
    window.addEventListener('beforeprint', () => {
        document.querySelectorAll('.content-card').forEach(card => {
            card.style.breakInside = 'avoid';
        });
    });
    
    // ===== Keyboard Navigation Enhancement =====
    document.querySelectorAll('.team-item, .social-link').forEach(element => {
        element.setAttribute('tabindex', '0');
        
        element.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
    });
    
    // ===== Easter Egg: Konami Code =====
    let konamiCode = [];
    const konamiSequence = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
    
    document.addEventListener('keydown', (e) => {
        konamiCode.push(e.key);
        konamiCode = konamiCode.slice(-konamiSequence.length);
        
        if (konamiCode.join(',') === konamiSequence.join(',')) {
            activateEasterEgg();
        }
    });
    
    function activateEasterEgg() {
        // Add fun animation
        document.body.style.animation = 'rainbow 2s ease infinite';
        
        const style = document.createElement('style');
        style.textContent = `
            @keyframes rainbow {
                0% { filter: hue-rotate(0deg); }
                100% { filter: hue-rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
        
        setTimeout(() => {
            document.body.style.animation = '';
            style.remove();
        }, 5000);
        
        console.log('🎮 Konami Code activated! You are a true gamer!');
    }
    
    // ===== Performance Monitoring =====
    if (window.performance && window.performance.timing) {
        window.addEventListener('load', () => {
            const loadTime = window.performance.timing.domContentLoadedEventEnd - window.performance.timing.navigationStart;
            console.log(`Page loaded in ${loadTime}ms`);
        });
    }
    
});
