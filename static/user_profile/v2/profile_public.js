/**
 * UP-UI-POLISH-04: Profile Public Page - Progressive Enhancements
 * 
 * Features:
 * - Expand/collapse "More Games" section
 * - Copy-to-clipboard for IGN with toast feedback
 * - Smooth scroll to sections from quick nav
 * 
 * Requirements:
 * - Must work without breaking if JS disabled (progressive enhancement)
 * - Accessible keyboard navigation
 * - Mobile-friendly interactions
 */

(function() {
    'use strict';
    
    // ========================================
    // 1. EXPAND/COLLAPSE "MORE GAMES"
    // ========================================
    
    const toggleMoreGamesBtn = document.getElementById('toggleMoreGames');
    const moreGamesContent = document.getElementById('moreGamesContent');
    const expandIcon = document.getElementById('expandIcon');
    
    if (toggleMoreGamesBtn && moreGamesContent) {
        toggleMoreGamesBtn.addEventListener('click', function() {
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            
            // Toggle expansion
            if (isExpanded) {
                // Collapse
                moreGamesContent.classList.remove('expanded');
                this.setAttribute('aria-expanded', 'false');
                moreGamesContent.setAttribute('aria-hidden', 'true');
                
                // Rotate icon back
                if (expandIcon) {
                    expandIcon.style.transform = 'rotate(0deg)';
                }
            } else {
                // Expand
                moreGamesContent.classList.add('expanded');
                this.setAttribute('aria-expanded', 'true');
                moreGamesContent.setAttribute('aria-hidden', 'false');
                
                // Rotate icon 180deg
                if (expandIcon) {
                    expandIcon.style.transform = 'rotate(180deg)';
                }
            }
        });
        
        // Keyboard support: Space and Enter keys
        toggleMoreGamesBtn.addEventListener('keydown', function(e) {
            if (e.key === ' ' || e.key === 'Enter') {
                e.preventDefault();
                this.click();
            }
        });
    }
    
    // ========================================
    // 2. COPY-TO-CLIPBOARD FOR IGN
    // ========================================
    
    /**
     * Copy text to clipboard and show toast notification
     * @param {string} text - Text to copy
     * @param {string} elementId - ID of element that triggered copy (for visual feedback)
     */
    window.copyToClipboard = function(text, elementId) {
        // Modern clipboard API (with fallback)
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text)
                .then(function() {
                    showToast('✓ IGN copied to clipboard!', 'success');
                    flashCopyFeedback(elementId);
                })
                .catch(function(err) {
                    console.error('Failed to copy:', err);
                    // Fallback to legacy method
                    legacyCopyToClipboard(text, elementId);
                });
        } else {
            // Fallback for older browsers
            legacyCopyToClipboard(text, elementId);
        }
    };
    
    /**
     * Legacy clipboard copy method (for older browsers)
     * @param {string} text - Text to copy
     * @param {string} elementId - ID of element for visual feedback
     */
    function legacyCopyToClipboard(text, elementId) {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.top = '0';
        textarea.style.left = '0';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                showToast('✓ IGN copied to clipboard!', 'success');
                flashCopyFeedback(elementId);
            } else {
                showToast('Failed to copy. Please copy manually.', 'error');
            }
        } catch (err) {
            console.error('Legacy copy failed:', err);
            showToast('Failed to copy. Please copy manually.', 'error');
        }
        
        document.body.removeChild(textarea);
    }
    
    /**
     * Flash visual feedback on the copied element
     * @param {string} elementId - ID of element to flash
     */
    function flashCopyFeedback(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        // Add temporary highlight class
        const originalColor = element.style.color;
        element.style.color = 'rgb(167, 243, 208)'; // emerald-300
        element.style.transition = 'color 0.3s ease-in-out';
        
        setTimeout(function() {
            element.style.color = originalColor;
        }, 600);
    }
    
    /**
     * Show toast notification
     * @param {string} message - Toast message
     * @param {string} type - Toast type ('success' or 'error')
     */
    function showToast(message, type) {
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) return;
        
        // Create toast element
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'polite');
        
        // Style based on type
        if (type === 'error') {
            toast.style.background = 'rgba(239, 68, 68, 0.95)'; // red-500
        }
        
        // Add to container
        toastContainer.appendChild(toast);
        
        // Remove after 3 seconds
        setTimeout(function() {
            toast.style.animation = 'slideInUp 0.3s ease-out reverse';
            setTimeout(function() {
                toastContainer.removeChild(toast);
            }, 300);
        }, 3000);
    }
    
    // ========================================
    // 3. SMOOTH SCROLL TO SECTIONS
    // ========================================
    
    const navLinks = document.querySelectorAll('a[href^="#"]');
    
    navLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            
            // Skip if it's just "#" or external link
            if (!targetId || targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                e.preventDefault();
                
                // Smooth scroll to target
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // Update URL hash without jumping
                if (history.pushState) {
                    history.pushState(null, null, targetId);
                } else {
                    // Fallback for older browsers
                    window.location.hash = targetId;
                }
                
                // Focus target for accessibility (after scroll completes)
                setTimeout(function() {
                    targetElement.focus({preventScroll: true});
                }, 500);
            }
        });
    });
    
    // ========================================
    // 4. INIT: HANDLE HASH ON PAGE LOAD
    // ========================================
    
    // If user lands on page with hash, scroll to it
    if (window.location.hash) {
        setTimeout(function() {
            const targetElement = document.querySelector(window.location.hash);
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }, 100); // Small delay to ensure page is fully loaded
    }
    
    // ========================================
    // 5. KEYBOARD NAVIGATION ENHANCEMENTS
    // ========================================
    
    // Add focus-visible polyfill behavior for older browsers
    document.body.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            document.body.classList.add('keyboard-nav');
        }
    });
    
    document.body.addEventListener('mousedown', function() {
        document.body.classList.remove('keyboard-nav');
    });
    
    // ========================================
    // 6. MOBILE: CLOSE EXPANDED SECTIONS ON SCROLL
    // ========================================
    
    let lastScrollTop = 0;
    const scrollThreshold = 200; // pixels
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // If user scrolls down more than threshold, collapse expanded sections
        if (Math.abs(scrollTop - lastScrollTop) > scrollThreshold) {
            if (moreGamesContent && moreGamesContent.classList.contains('expanded')) {
                // Auto-collapse on mobile during scroll (UX improvement)
                if (window.innerWidth < 768) {
                    toggleMoreGamesBtn.click();
                }
            }
        }
        
        lastScrollTop = scrollTop;
    });
    
    // ========================================
    // 7. PERFORMANCE: LAZY LOAD IMAGES IN "MORE GAMES"
    // ========================================
    
    // Observe "More Games" section and lazy load images when expanded
    if ('IntersectionObserver' in window && moreGamesContent) {
        const imageObserver = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        imageObserver.unobserve(img);
                    }
                }
            });
        });
        
        // Observe all images with data-src in More Games section
        const lazyImages = moreGamesContent.querySelectorAll('img[data-src]');
        lazyImages.forEach(function(img) {
            imageObserver.observe(img);
        });
    }
    
    // ========================================
    // 8. ACCESSIBILITY: ANNOUNCE DYNAMIC CONTENT
    // ========================================
    
    // Create live region for screen reader announcements
    const liveRegion = document.createElement('div');
    liveRegion.setAttribute('role', 'status');
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'sr-only'; // Visually hidden but accessible
    liveRegion.style.position = 'absolute';
    liveRegion.style.left = '-10000px';
    liveRegion.style.width = '1px';
    liveRegion.style.height = '1px';
    liveRegion.style.overflow = 'hidden';
    document.body.appendChild(liveRegion);
    
    /**
     * Announce message to screen readers
     * @param {string} message - Message to announce
     */
    window.announceToScreenReader = function(message) {
        liveRegion.textContent = message;
        
        // Clear after 1 second
        setTimeout(function() {
            liveRegion.textContent = '';
        }, 1000);
    };
    
    // Announce when "More Games" is expanded/collapsed
    if (toggleMoreGamesBtn) {
        toggleMoreGamesBtn.addEventListener('click', function() {
            const isExpanded = this.getAttribute('aria-expanded') === 'true';
            const message = isExpanded 
                ? 'More games section expanded' 
                : 'More games section collapsed';
            
            window.announceToScreenReader(message);
        });
    }
    
    console.log('[UP-UI-POLISH-04] Profile public enhancements loaded');
    
})();
