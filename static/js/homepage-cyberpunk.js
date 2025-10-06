/**
 * DeltaCrown Cyberpunk Homepage
 * Interactive animations and effects
 */

(function() {
    'use strict';
    
    // ================================================================
    // PARTICLE SYSTEM
    // ================================================================
    
    const canvas = document.getElementById('particle-canvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        let particles = [];
        let animationId;
        
        // Set canvas size
        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        
        // Particle class
        class Particle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2 + 1;
                this.speedX = Math.random() * 0.5 - 0.25;
                this.speedY = Math.random() * 0.5 - 0.25;
                this.color = Math.random() > 0.5 ? 'rgba(0, 255, 136, 0.5)' : 'rgba(0, 216, 255, 0.5)';
            }
            
            update() {
                this.x += this.speedX;
                this.y += this.speedY;
                
                // Wrap around screen
                if (this.x > canvas.width) this.x = 0;
                if (this.x < 0) this.x = canvas.width;
                if (this.y > canvas.height) this.y = 0;
                if (this.y < 0) this.y = canvas.height;
            }
            
            draw() {
                ctx.fillStyle = this.color;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        
        // Initialize particles
        function initParticles() {
            particles = [];
            const particleCount = Math.min(100, Math.floor(canvas.width / 10));
            for (let i = 0; i < particleCount; i++) {
                particles.push(new Particle());
            }
        }
        
        // Animation loop
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            particles.forEach(particle => {
                particle.update();
                particle.draw();
            });
            
            // Draw connections
            particles.forEach((a, i) => {
                particles.slice(i + 1).forEach(b => {
                    const dx = a.x - b.x;
                    const dy = a.y - b.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    
                    if (distance < 100) {
                        ctx.strokeStyle = `rgba(0, 255, 136, ${0.2 * (1 - distance / 100)})`;
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.moveTo(a.x, a.y);
                        ctx.lineTo(b.x, b.y);
                        ctx.stroke();
                    }
                });
            });
            
            animationId = requestAnimationFrame(animate);
        }
        
        // Initialize
        resizeCanvas();
        initParticles();
        animate();
        
        // Handle resize
        window.addEventListener('resize', () => {
            resizeCanvas();
            initParticles();
        });
        
        // Pause animation when page is hidden
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                cancelAnimationFrame(animationId);
            } else {
                animate();
            }
        });
    }
    
    // ================================================================
    // STATS COUNTER ANIMATION
    // ================================================================
    
    function animateCounter(element, target, duration = 2000) {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                element.textContent = target.toLocaleString();
                clearInterval(timer);
            } else {
                element.textContent = Math.floor(current).toLocaleString();
            }
        }, 16);
    }
    
    // Intersection Observer for counters
    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting && !entry.target.dataset.animated) {
                const target = parseInt(entry.target.dataset.count);
                if (!isNaN(target)) {
                    animateCounter(entry.target, target);
                    entry.target.dataset.animated = 'true';
                }
            }
        });
    }, { threshold: 0.5 });
    
    document.querySelectorAll('.stat-value[data-count]').forEach(el => {
        counterObserver.observe(el);
    });
    
    // ================================================================
    // GAME CARDS PARALLAX EFFECT
    // ================================================================
    
    const gameCards = document.querySelectorAll('.game-card');
    
    gameCards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (y - centerY) / 20;
            const rotateY = (centerX - x) / 20;
            
            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px)`;
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });
    
    // ================================================================
    // TESTIMONIALS SLIDER (AUTO-ROTATE)
    // ================================================================
    
    const testimonialsTrack = document.querySelector('.testimonials-track');
    if (testimonialsTrack) {
        const testimonialCards = testimonialsTrack.querySelectorAll('.testimonial-card');
        let currentIndex = 0;
        
        function rotateTestimonials() {
            // Only rotate if there are multiple testimonials
            if (testimonialCards.length > 1) {
                currentIndex = (currentIndex + 1) % testimonialCards.length;
                
                // Add highlight to current testimonial
                testimonialCards.forEach((card, index) => {
                    if (index === currentIndex) {
                        card.style.transform = 'scale(1.05)';
                        card.style.border = '2px solid var(--cyan)';
                    } else {
                        card.style.transform = '';
                        card.style.border = '';
                    }
                });
            }
        }
        
        // Rotate every 5 seconds
        setInterval(rotateTestimonials, 5000);
    }
    
    // ================================================================
    // SMOOTH SCROLL FOR ANCHOR LINKS
    // ================================================================
    
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
    
    // ================================================================
    // SCROLL REVEAL FOR SECTIONS
    // ================================================================
    
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    });
    
    document.querySelectorAll('section').forEach(section => {
        revealObserver.observe(section);
    });
    
    // ================================================================
    // LIVE TOURNAMENT PULSE ANIMATION
    // ================================================================
    
    const liveIndicators = document.querySelectorAll('.live-indicator, .live-dot, .live-pulse');
    liveIndicators.forEach(indicator => {
        setInterval(() => {
            indicator.style.opacity = indicator.style.opacity === '0.3' ? '1' : '0.3';
        }, 1000);
    });
    
    // ================================================================
    // FEATURED TOURNAMENT CARD HOVER EFFECT
    // ================================================================
    
    const featuredCard = document.querySelector('.featured-tournament-card');
    if (featuredCard) {
        featuredCard.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-50%) scale(1.05)';
        });
        
        featuredCard.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(-50%) scale(1)';
        });
    }
    
    // ================================================================
    // BUTTON CLICK EFFECT
    // ================================================================
    
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            // Create ripple effect
            const ripple = document.createElement('span');
            ripple.classList.add('ripple');
            
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
    
    // Add ripple styles dynamically
    const style = document.createElement('style');
    style.textContent = `
        .ripple {
            position: absolute;
            width: 20px;
            height: 20px;
            background: rgba(255, 255, 255, 0.5);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            animation: ripple-animation 0.6s ease-out;
            pointer-events: none;
        }
        
        @keyframes ripple-animation {
            to {
                transform: translate(-50%, -50%) scale(15);
                opacity: 0;
            }
        }
        
        section {
            opacity: 0;
            transform: translateY(30px);
            transition: opacity 0.6s ease, transform 0.6s ease;
        }
        
        section.revealed {
            opacity: 1;
            transform: translateY(0);
        }
    `;
    document.head.appendChild(style);
    
    // ================================================================
    // PERFORMANCE OPTIMIZATION
    // ================================================================
    
    // Lazy load images
    const images = document.querySelectorAll('img[loading="lazy"]');
    if ('loading' in HTMLImageElement.prototype) {
        // Browser supports lazy loading natively
        images.forEach(img => {
            img.src = img.dataset.src || img.src;
        });
    } else {
        // Fallback for browsers that don't support lazy loading
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src || img.src;
                    imageObserver.unobserve(img);
                }
            });
        });
        
        images.forEach(img => imageObserver.observe(img));
    }
    
    // Reduce motion for users who prefer it
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        // Disable animations
        document.querySelectorAll('[data-aos]').forEach(el => {
            el.removeAttribute('data-aos');
        });
        
        // Stop particle animation
        if (animationId) {
            cancelAnimationFrame(animationId);
        }
    }
    
    // ================================================================
    // CONSOLE EASTER EGG
    // ================================================================
    
    console.log('%c🎮 DeltaCrown Gaming Platform', 'color: #00FF88; font-size: 24px; font-weight: bold;');
    console.log('%cWelcome to the source! Interested in joining our team?', 'color: #00D8FF; font-size: 14px;');
    console.log('%cCheck out our careers page or contact us!', 'color: #B8C5D6; font-size: 12px;');
    
})();
