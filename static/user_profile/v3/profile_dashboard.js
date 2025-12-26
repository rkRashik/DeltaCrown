/**
 * UP-UI-REDESIGN-01: Profile Dashboard v3 - Progressive Enhancement
 * Vanilla JavaScript for interactive dashboard features
 */

(function() {
    'use strict';
    
    // ========== UTILITIES ==========
    
    /**
     * Show toast notification
     */
    function showToast(message, type = 'success') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        
        if (type === 'error') {
            toast.style.background = 'rgba(239, 68, 68, 0.95)';
        }
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutDown 0.3s ease-in forwards';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    /**
     * Copy text to clipboard
     */
    window.copyToClipboard = function(text) {
        if (!navigator.clipboard) {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            
            try {
                document.execCommand('copy');
                showToast('Copied to clipboard!');
            } catch (err) {
                showToast('Failed to copy', 'error');
            }
            
            document.body.removeChild(textarea);
            return;
        }
        
        navigator.clipboard.writeText(text)
            .then(() => showToast('Copied to clipboard!'))
            .catch(() => showToast('Failed to copy', 'error'));
    };
    
    /**
     * Smooth scroll to section with offset for sticky nav
     */
    function smoothScrollTo(targetId) {
        const target = document.getElementById(targetId);
        if (!target) return;
        
        const navHeight = 80; // Approximate sticky nav height
        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight;
        
        window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
        });
    }
    
    // ========== DASHBOARD NAVIGATION ==========
    
    /**
     * Handle dashboard nav chip clicks
     */
    function initDashboardNav() {
        const navChips = document.querySelectorAll('.nav-chip');
        
        navChips.forEach(chip => {
            chip.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Remove active class from all chips
                navChips.forEach(c => c.classList.remove('active'));
                
                // Add active class to clicked chip
                this.classList.add('active');
                
                // Smooth scroll to section
                const targetId = this.getAttribute('href').substring(1);
                smoothScrollTo(targetId);
            });
        });
        
        // Update active chip on scroll (Intersection Observer)
        const sections = Array.from(navChips).map(chip => {
            const targetId = chip.getAttribute('href').substring(1);
            return document.getElementById(targetId);
        }).filter(Boolean);
        
        const observerOptions = {
            root: null,
            rootMargin: '-100px 0px -66%',
            threshold: 0
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const activeChip = document.querySelector(`.nav-chip[href="#${entry.target.id}"]`);
                    if (activeChip) {
                        navChips.forEach(c => c.classList.remove('active'));
                        activeChip.classList.add('active');
                    }
                }
            });
        }, observerOptions);
        
        sections.forEach(section => {
            if (section) observer.observe(section);
        });
    }
    
    // ========== COLLAPSIBLE SECTIONS ==========
    
    /**
     * Toggle collapsible "More Games" section
     */
    function initCollapsible() {
        const toggleBtn = document.getElementById('toggleMoreGames');
        const content = document.getElementById('moreGamesContent');
        const icon = document.getElementById('expandIcon');
        
        if (!toggleBtn || !content) return;
        
        toggleBtn.addEventListener('click', function() {
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            
            // Toggle state
            this.setAttribute('aria-expanded', !isExpanded);
            content.setAttribute('aria-hidden', isExpanded);
            content.classList.toggle('expanded');
            
            // Rotate icon
            if (icon) {
                icon.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(180deg)';
            }
        });
    }
    
    // ========== COPY BUTTONS ==========
    
    /**
     * Show copy buttons on passport card hover
     */
    function initCopyButtons() {
        const battleCards = document.querySelectorAll('.battle-card');
        
        battleCards.forEach(card => {
            const copyBtn = card.querySelector('.copy-btn');
            if (!copyBtn) return;
            
            card.addEventListener('mouseenter', function() {
                copyBtn.style.opacity = '1';
            });
            
            card.addEventListener('mouseleave', function() {
                copyBtn.style.opacity = '0';
            });
        });
    }
    
    // ========== URL HASH SUPPORT ==========
    
    /**
     * Handle direct links with hash (e.g., /profile#stats)
     */
    function handleUrlHash() {
        const hash = window.location.hash;
        if (hash && hash.length > 1) {
            const targetId = hash.substring(1);
            
            // Small delay to ensure page is fully loaded
            setTimeout(() => {
                smoothScrollTo(targetId);
                
                // Update active nav chip
                const activeChip = document.querySelector(`.nav-chip[href="${hash}"]`);
                if (activeChip) {
                    document.querySelectorAll('.nav-chip').forEach(c => c.classList.remove('active'));
                    activeChip.classList.add('active');
                }
            }, 300);
        }
    }
    
    // ========== KEYBOARD NAVIGATION ==========
    
    /**
     * Enable keyboard shortcuts for dashboard navigation
     */
    function initKeyboardShortcuts() {
        const shortcuts = {
            '1': 'overview',
            '2': 'passports',
            '3': 'teams',
            '4': 'tournaments',
            '5': 'stats',
            '6': 'economy',
            '7': 'shop',
            '8': 'activity',
            '9': 'about'
        };
        
        document.addEventListener('keydown', function(e) {
            // Only activate if not typing in an input/textarea
            if (e.target.tagName === 'INPUT' || 
                e.target.tagName === 'TEXTAREA' || 
                e.target.isContentEditable) {
                return;
            }
            
            // Alt + Number for quick navigation
            if (e.altKey && shortcuts[e.key]) {
                e.preventDefault();
                smoothScrollTo(shortcuts[e.key]);
                
                // Update active chip
                const chip = document.querySelector(`.nav-chip[href="#${shortcuts[e.key]}"]`);
                if (chip) {
                    document.querySelectorAll('.nav-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                }
            }
        });
    }
    
    // ========== FADE-IN ANIMATIONS ==========
    
    /**
     * Trigger fade-in animations as sections come into view
     */
    function initFadeAnimations() {
        const sections = document.querySelectorAll('.section-fade-in');
        
        const observerOptions = {
            root: null,
            rootMargin: '0px',
            threshold: 0.1
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);
        
        sections.forEach(section => {
            section.style.opacity = '0';
            section.style.transform = 'translateY(10px)';
            section.style.transition = 'opacity 0.5s ease-in-out, transform 0.5s ease-in-out';
            observer.observe(section);
        });
    }
    
    // ========== INITIALIZATION ==========
    
    /**
     * Initialize all dashboard features
     */
    function init() {
        // Check if we're on a profile page
        const dashboardContainer = document.querySelector('.dashboard-card');
        if (!dashboardContainer) return;
        
        console.log('Initializing Profile Dashboard v3...');
        
        try {
            initDashboardNav();
            initCollapsible();
            initCopyButtons();
            handleUrlHash();
            initKeyboardShortcuts();
            initFadeAnimations();
            
            console.log('Profile Dashboard v3 initialized successfully');
        } catch (error) {
            console.error('Error initializing Profile Dashboard v3:', error);
        }
    }
    
    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Also handle hashchange for SPA-like navigation
    window.addEventListener('hashchange', handleUrlHash);
    
})();
