/**
 * TOURNAMENT DETAIL V6 - INTERACTIVE FEATURES
 * Complete functionality for the redesigned detail page
 */

(function() {
    'use strict';

    // ============================================================================
    // INITIALIZATION
    // ============================================================================
    
    document.addEventListener('DOMContentLoaded', () => {
        initRulesTabs();
        initMediaGallery();
        initShareButtons();
        initWatchlistButton();
        initSmoothScrolling();
        logInitSuccess();
    });

    // ============================================================================
    // RULES TABS
    // ============================================================================
    
    function initRulesTabs() {
        const tabs = document.querySelectorAll('.rules-tab');
        const sections = document.querySelectorAll('.rules-section');
        
        if (tabs.length === 0 || sections.length === 0) return;

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetTab = tab.dataset.tab;
                
                // Update tabs
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // Update sections
                sections.forEach(section => {
                    section.classList.remove('active');
                    if (section.dataset.content === targetTab) {
                        section.classList.add('active');
                    }
                });
            });
        });
    }

    // ============================================================================
    // MEDIA GALLERY & LIGHTBOX
    // ============================================================================
    
    function initMediaGallery() {
        const galleryItems = document.querySelectorAll('.gallery-item');
        const lightbox = document.getElementById('lightboxModal');
        const lightboxImage = lightbox ? lightbox.querySelector('.lightbox-image') : null;
        const lightboxClose = lightbox ? lightbox.querySelector('.lightbox-close') : null;
        const lightboxPrev = lightbox ? lightbox.querySelector('.lightbox-prev') : null;
        const lightboxNext = lightbox ? lightbox.querySelector('.lightbox-next') : null;
        const lightboxBackdrop = lightbox ? lightbox.querySelector('.lightbox-backdrop') : null;
        
        if (!lightbox || galleryItems.length === 0) return;

        let currentIndex = 0;
        const images = Array.from(galleryItems).map(item => item.dataset.image);

        // Open lightbox
        galleryItems.forEach((item, index) => {
            item.addEventListener('click', () => {
                currentIndex = index;
                showLightbox(images[currentIndex]);
            });
        });

        // Close lightbox
        if (lightboxClose) {
            lightboxClose.addEventListener('click', closeLightbox);
        }

        if (lightboxBackdrop) {
            lightboxBackdrop.addEventListener('click', closeLightbox);
        }

        // Navigation
        if (lightboxPrev) {
            lightboxPrev.addEventListener('click', (e) => {
                e.stopPropagation();
                currentIndex = (currentIndex - 1 + images.length) % images.length;
                showLightbox(images[currentIndex]);
            });
        }

        if (lightboxNext) {
            lightboxNext.addEventListener('click', (e) => {
                e.stopPropagation();
                currentIndex = (currentIndex + 1) % images.length;
                showLightbox(images[currentIndex]);
            });
        }

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!lightbox.classList.contains('active')) return;

            if (e.key === 'Escape') {
                closeLightbox();
            } else if (e.key === 'ArrowLeft') {
                currentIndex = (currentIndex - 1 + images.length) % images.length;
                showLightbox(images[currentIndex]);
            } else if (e.key === 'ArrowRight') {
                currentIndex = (currentIndex + 1) % images.length;
                showLightbox(images[currentIndex]);
            }
        });

        function showLightbox(imageSrc) {
            if (lightboxImage) {
                lightboxImage.src = imageSrc;
            }
            lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function closeLightbox() {
            lightbox.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    // ============================================================================
    // SHARE BUTTONS
    // ============================================================================
    
    function initShareButtons() {
        const shareButtons = document.querySelectorAll('[data-share]');
        const shareCTAButton = document.querySelector('.share-btn');
        
        // Main share CTA button
        if (shareCTAButton) {
            shareCTAButton.addEventListener('click', () => {
                const url = shareCTAButton.dataset.url || window.location.href;
                const title = shareCTAButton.dataset.tournament || document.title;
                
                if (navigator.share) {
                    navigator.share({
                        title: title,
                        url: url
                    }).catch(err => console.log('Error sharing:', err));
                } else {
                    copyToClipboard(url);
                    showNotification('Link copied to clipboard!');
                }
            });
        }

        // Sidebar share buttons
        shareButtons.forEach(button => {
            button.addEventListener('click', () => {
                const platform = button.dataset.share;
                const url = encodeURIComponent(window.location.href);
                const title = encodeURIComponent(document.title);
                
                let shareUrl = '';
                
                switch(platform) {
                    case 'facebook':
                        shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${url}`;
                        break;
                    case 'twitter':
                        shareUrl = `https://twitter.com/intent/tweet?url=${url}&text=${title}`;
                        break;
                    case 'discord':
                        // Discord doesn't have a direct share URL, copy to clipboard
                        copyToClipboard(window.location.href);
                        showNotification('Link copied! Share in Discord.');
                        return;
                    case 'copy':
                        copyToClipboard(window.location.href);
                        showNotification('Link copied to clipboard!');
                        return;
                }
                
                if (shareUrl) {
                    window.open(shareUrl, '_blank', 'width=600,height=400');
                }
            });
        });
    }

    function copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
        }
    }

    function showNotification(message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'toast-notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #00ff88;
            color: #0a0e27;
            padding: 16px 24px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 700;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
            z-index: 10000;
            animation: slideInUp 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutDown 0.3s ease-in';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    // ============================================================================
    // WATCHLIST BUTTON
    // ============================================================================
    
    function initWatchlistButton() {
        const watchlistBtn = document.querySelector('.watchlist-btn');
        
        if (!watchlistBtn) return;

        const tournamentSlug = watchlistBtn.dataset.tournamentSlug;
        
        // Check if already in watchlist
        checkWatchlistStatus(tournamentSlug).then(isWatched => {
            updateWatchlistButton(watchlistBtn, isWatched);
        });

        watchlistBtn.addEventListener('click', async () => {
            const isWatched = watchlistBtn.classList.contains('watching');
            
            try {
                if (isWatched) {
                    await removeFromWatchlist(tournamentSlug);
                    updateWatchlistButton(watchlistBtn, false);
                    showNotification('Removed from watchlist');
                } else {
                    await addToWatchlist(tournamentSlug);
                    updateWatchlistButton(watchlistBtn, true);
                    showNotification('Added to watchlist');
                }
            } catch (error) {
                console.error('Watchlist error:', error);
                showNotification('Error updating watchlist');
            }
        });
    }

    async function checkWatchlistStatus(slug) {
        try {
            const response = await fetch(`/api/tournaments/${slug}/watchlist/status/`);
            if (response.ok) {
                const data = await response.json();
                return data.watching;
            }
        } catch (error) {
            console.error('Error checking watchlist:', error);
        }
        return false;
    }

    async function addToWatchlist(slug) {
        const response = await fetch(`/api/tournaments/${slug}/watchlist/add/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to add to watchlist');
        }
        
        return await response.json();
    }

    async function removeFromWatchlist(slug) {
        const response = await fetch(`/api/tournaments/${slug}/watchlist/remove/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to remove from watchlist');
        }
        
        return await response.json();
    }

    function updateWatchlistButton(button, isWatched) {
        const svg = button.querySelector('svg');
        
        if (isWatched) {
            button.classList.add('watching');
            button.innerHTML = `
                <svg width="20" height="20" fill="currentColor" stroke="none">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                </svg>
                Watching
            `;
            button.style.background = 'rgba(255, 70, 85, 0.12)';
            button.style.borderColor = 'rgba(255, 70, 85, 0.3)';
            button.style.color = '#ff4655';
        } else {
            button.classList.remove('watching');
            button.innerHTML = `
                <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                </svg>
                Add to Watchlist
            `;
            button.style.background = '';
            button.style.borderColor = '';
            button.style.color = '';
        }
    }

    // ============================================================================
    // SMOOTH SCROLLING
    // ============================================================================
    
    function initSmoothScrolling() {
        const links = document.querySelectorAll('a[href^="#"]');
        
        links.forEach(link => {
            link.addEventListener('click', (e) => {
                const href = link.getAttribute('href');
                
                if (href === '#' || href === '#!') return;
                
                const target = document.querySelector(href);
                
                if (target) {
                    e.preventDefault();
                    
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                    
                    // Update URL hash without jumping
                    history.pushState(null, null, href);
                }
            });
        });
    }

    // ============================================================================
    // UTILITIES
    // ============================================================================
    
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function debounce(func, wait) {
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

    // ============================================================================
    // LOGGING
    // ============================================================================
    
    function logInitSuccess() {
        console.log('%c✓ Tournament Detail V6 Initialized', 
            'color: #00ff88; font-weight: bold; font-size: 14px;');
        console.log('%cFeatures loaded:', 
            'color: #cbd5e1; font-weight: normal;');
        console.log('  • Rules tabs with smooth transitions');
        console.log('  • Media gallery with lightbox');
        console.log('  • Share buttons (Facebook, Twitter, Discord, Copy)');
        console.log('  • Watchlist functionality');
        console.log('  • Smooth scrolling');
    }

    // ============================================================================
    // ERROR HANDLING
    // ============================================================================
    
    window.addEventListener('error', (e) => {
        console.error('Tournament Detail V6 Error:', e.error);
    });

    // ============================================================================
    // EXPORTS (if using modules)
    // ============================================================================
    
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = {
            initRulesTabs,
            initMediaGallery,
            initShareButtons,
            initWatchlistButton
        };
    }

    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes slideOutDown {
            from {
                opacity: 1;
                transform: translateY(0);
            }
            to {
                opacity: 0;
                transform: translateY(20px);
            }
        }
    `;
    document.head.appendChild(style);

})();
