// CrownStore Main JavaScript

class CrownStore {
    constructor() {
        this.init();
        this.bindEvents();
    }

    init() {
        this.loadingElement = this.createLoadingElement();
        this.cartCount = 0;
        this.wishlistItems = new Set();
        this.initializeCart();
        this.initializeWishlist();
    }

    createLoadingElement() {
        const loading = document.createElement('div');
        loading.className = 'loading-overlay';
        loading.innerHTML = `
            <div class="loading-spinner">
                <div class="crown-loader">
                    <i class="fas fa-crown"></i>
                </div>
                <p>Loading...</p>
            </div>
        `;
        return loading;
    }

    bindEvents() {
        // Add to cart events
        document.addEventListener('click', (e) => {
            if (e.target.closest('.add-to-cart-btn')) {
                e.preventDefault();
                this.handleAddToCart(e.target.closest('.add-to-cart-form'));
            }
        });

        // Wishlist events
        document.addEventListener('click', (e) => {
            if (e.target.closest('.wishlist-btn')) {
                e.preventDefault();
                this.handleWishlistToggle(e.target.closest('.wishlist-btn'));
            }
        });

        // Quick view events
        document.addEventListener('click', (e) => {
            if (e.target.closest('.quick-view-btn')) {
                e.preventDefault();
                this.handleQuickView(e.target.closest('.quick-view-btn'));
            }
        });

        // Search events
        const searchInputs = document.querySelectorAll('.search-input');
        searchInputs.forEach(input => {
            let timeout;
            input.addEventListener('input', (e) => {
                clearTimeout(timeout);
                timeout = setTimeout(() => {
                    this.handleSearch(e.target.value);
                }, 300);
            });
        });

        // Newsletter signup
        const newsletterForm = document.querySelector('.newsletter-form');
        if (newsletterForm) {
            newsletterForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleNewsletterSignup(newsletterForm);
            });
        }

        // Product image zoom
        document.addEventListener('click', (e) => {
            if (e.target.closest('.zoom-btn')) {
                this.handleImageZoom(e.target.closest('.zoom-btn'));
            }
        });

        // Social share
        document.addEventListener('click', (e) => {
            if (e.target.closest('.share-btn')) {
                e.preventDefault();
                this.handleSocialShare(e.target.closest('.share-btn'));
            }
        });
    }

    async handleAddToCart(form) {
        if (!form) return;

        const productId = form.dataset.productId;
        const formData = new FormData(form);
        
        // Show loading
        const button = form.querySelector('.add-to-cart-btn');
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
        button.disabled = true;

        try {
            const response = await fetch(`/ecommerce/cart/add/${productId}/`, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification(data.message, 'success');
                this.updateCartCount(data.cart_total);
                this.animateCartIcon();
                
                // Update button temporarily
                button.innerHTML = '<i class="fas fa-check"></i> Added!';
                button.classList.add('success');
                
                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.classList.remove('success');
                    button.disabled = false;
                }, 2000);
            } else {
                this.showNotification(data.message, 'error');
                button.innerHTML = originalText;
                button.disabled = false;
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            this.showNotification('Error adding to cart', 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    async handleWishlistToggle(button) {
        if (!button) return;

        const productId = button.dataset.productId;
        const icon = button.querySelector('i');
        const isInWishlist = this.wishlistItems.has(productId);

        try {
            const response = await fetch(`/ecommerce/wishlist/toggle/${productId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });

            const data = await response.json();

            if (data.success) {
                if (data.in_wishlist) {
                    this.wishlistItems.add(productId);
                    icon.className = 'fas fa-heart';
                    button.classList.add('active');
                    button.setAttribute('title', 'Remove from Wishlist');
                } else {
                    this.wishlistItems.delete(productId);
                    icon.className = 'far fa-heart';
                    button.classList.remove('active');
                    button.setAttribute('title', 'Add to Wishlist');
                }
                
                this.showNotification(data.message, 'success');
                this.animateWishlistButton(button);
            } else {
                this.showNotification(data.message, 'error');
            }
        } catch (error) {
            console.error('Error toggling wishlist:', error);
            this.showNotification('Error updating wishlist', 'error');
        }
    }

    async handleQuickView(button) {
        const productId = button.dataset.productId;
        
        try {
            // Show loading in modal
            const modal = document.getElementById('quickViewModal');
            const content = document.getElementById('quickViewContent');
            
            if (modal && content) {
                content.innerHTML = `
                    <div class="text-center p-4">
                        <div class="crown-loader mb-3">
                            <i class="fas fa-crown"></i>
                        </div>
                        <p>Loading product details...</p>
                    </div>
                `;
                
                // Show modal (assuming Bootstrap)
                const bsModal = new bootstrap.Modal(modal);
                bsModal.show();
                
                // Load product details (you'd implement this endpoint)
                const response = await fetch(`/ecommerce/api/product/${productId}/quick-view/`);
                const html = await response.text();
                content.innerHTML = html;
            }
        } catch (error) {
            console.error('Error loading quick view:', error);
            this.showNotification('Error loading product details', 'error');
        }
    }

    async handleSearch(query) {
        if (query.length < 2) return;

        try {
            const response = await fetch(`/ecommerce/api/search/?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            this.displaySearchResults(data.products);
        } catch (error) {
            console.error('Error searching:', error);
        }
    }

    displaySearchResults(products) {
        // Find or create search results dropdown
        let dropdown = document.querySelector('.search-dropdown');
        if (!dropdown) {
            dropdown = document.createElement('div');
            dropdown.className = 'search-dropdown';
            const searchContainer = document.querySelector('.search-input-group');
            if (searchContainer) {
                searchContainer.appendChild(dropdown);
            }
        }

        if (products.length === 0) {
            dropdown.innerHTML = '<div class="search-no-results">No products found</div>';
        } else {
            dropdown.innerHTML = products.map(product => `
                <div class="search-result-item">
                    <a href="/ecommerce/product/${product.slug}/">
                        ${product.image ? `<img src="${product.image}" alt="${product.name}">` : ''}
                        <div class="search-result-info">
                            <h6>${product.name}</h6>
                            <p class="search-result-category">${product.category}</p>
                            <p class="search-result-price">$${product.price}</p>
                        </div>
                    </a>
                </div>
            `).join('');
        }

        dropdown.style.display = 'block';
        
        // Hide dropdown when clicking outside
        setTimeout(() => {
            document.addEventListener('click', function hideDropdown(e) {
                if (!e.target.closest('.search-input-group')) {
                    dropdown.style.display = 'none';
                    document.removeEventListener('click', hideDropdown);
                }
            });
        }, 100);
    }

    async handleNewsletterSignup(form) {
        const email = form.querySelector('input[type="email"]').value;
        const button = form.querySelector('button');
        const originalText = button.innerHTML;

        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Subscribing...';
        button.disabled = true;

        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            this.showNotification('Successfully subscribed to newsletter!', 'success');
            form.reset();
            
            button.innerHTML = '<i class="fas fa-check"></i> Subscribed!';
            
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 3000);
        } catch (error) {
            console.error('Error subscribing:', error);
            this.showNotification('Error subscribing to newsletter', 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    handleImageZoom(button) {
        const mainImage = document.getElementById('mainProductImage');
        if (!mainImage) return;

        // Create zoom modal
        const zoomModal = document.createElement('div');
        zoomModal.className = 'image-zoom-modal';
        zoomModal.innerHTML = `
            <div class="zoom-overlay">
                <div class="zoom-container">
                    <img src="${mainImage.src}" alt="${mainImage.alt}">
                    <button class="zoom-close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(zoomModal);
        document.body.style.overflow = 'hidden';

        // Close zoom modal
        zoomModal.addEventListener('click', (e) => {
            if (e.target === zoomModal || e.target.closest('.zoom-close')) {
                document.body.removeChild(zoomModal);
                document.body.style.overflow = '';
            }
        });
    }

    handleSocialShare(button) {
        const platform = button.dataset.platform;
        const url = window.location.href;
        const title = document.title;
        
        let shareUrl = '';
        
        switch (platform) {
            case 'twitter':
                shareUrl = `https://twitter.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(title)}`;
                break;
            case 'facebook':
                shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
                break;
            case 'discord':
                // Copy to clipboard for Discord
                navigator.clipboard.writeText(`${title} - ${url}`);
                this.showNotification('Link copied to clipboard for Discord!', 'success');
                return;
        }
        
        if (shareUrl) {
            window.open(shareUrl, '_blank', 'width=600,height=400');
        }
    }

    initializeCart() {
        // Get cart count from server or localStorage
        const cartCountElement = document.querySelector('.cart-count');
        if (cartCountElement) {
            this.cartCount = parseInt(cartCountElement.textContent) || 0;
        }
    }

    initializeWishlist() {
        // Initialize wishlist items from DOM
        document.querySelectorAll('.wishlist-btn.active').forEach(btn => {
            this.wishlistItems.add(btn.dataset.productId);
        });
    }

    updateCartCount(count) {
        this.cartCount = count;
        const cartCountElements = document.querySelectorAll('.cart-count');
        cartCountElements.forEach(el => {
            el.textContent = count;
            if (count > 0) {
                el.style.display = 'inline';
            }
        });
    }

    animateCartIcon() {
        const cartIcon = document.querySelector('.cart-icon');
        if (cartIcon) {
            cartIcon.classList.add('cart-bounce');
            setTimeout(() => {
                cartIcon.classList.remove('cart-bounce');
            }, 600);
        }
    }

    animateWishlistButton(button) {
        button.classList.add('wishlist-pulse');
        setTimeout(() => {
            button.classList.remove('wishlist-pulse');
        }, 600);
    }

    showNotification(message, type = 'info') {
        // Remove existing notifications
        const existingNotifications = document.querySelectorAll('.crown-notification');
        existingNotifications.forEach(notification => {
            notification.remove();
        });

        // Create notification
        const notification = document.createElement('div');
        notification.className = `crown-notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
                <button class="notification-close">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.classList.add('fade-out');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 300);
            }
        }, 5000);

        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.classList.add('fade-out');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        });
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }

    showLoading() {
        document.body.appendChild(this.loadingElement);
    }

    hideLoading() {
        if (this.loadingElement.parentNode) {
            this.loadingElement.parentNode.removeChild(this.loadingElement);
        }
    }
}

// Utility Functions
function formatPrice(price) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(price);
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

// Initialize CrownStore when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.crownStore = new CrownStore();
    
    // Add some dynamic effects
    addParallaxEffect();
    addGlowEffects();
    addTypingEffect();
});

function addParallaxEffect() {
    const heroVideo = document.querySelector('.hero-video');
    if (heroVideo) {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const rate = scrolled * -0.5;
            heroVideo.style.transform = `translateY(${rate}px)`;
        });
    }
}

function addGlowEffects() {
    // Add glow effect to interactive elements
    document.querySelectorAll('.btn-primary, .category-card, .product-card').forEach(element => {
        element.addEventListener('mouseenter', function() {
            this.style.boxShadow = '0 0 30px rgba(255, 215, 0, 0.3)';
        });
        
        element.addEventListener('mouseleave', function() {
            this.style.boxShadow = '';
        });
    });
}

function addTypingEffect() {
    const typingElements = document.querySelectorAll('[data-typing]');
    typingElements.forEach(element => {
        const text = element.dataset.typing;
        element.textContent = '';
        
        let i = 0;
        const typeWriter = () => {
            if (i < text.length) {
                element.textContent += text.charAt(i);
                i++;
                setTimeout(typeWriter, 100);
            }
        };
        
        // Start typing when element comes into view
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    typeWriter();
                    observer.unobserve(entry.target);
                }
            });
        });
        
        observer.observe(element);
    });
}

// CSS for notifications and loading
const dynamicStyles = `
<style>
.crown-notification {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    max-width: 400px;
    background: rgba(26, 26, 26, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    transform: translateX(100%);
    animation: slideIn 0.3s ease forwards;
}

.crown-notification.success {
    border-left: 4px solid #10b981;
}

.crown-notification.error {
    border-left: 4px solid #ef4444;
}

.crown-notification.warning {
    border-left: 4px solid #f59e0b;
}

.crown-notification.info {
    border-left: 4px solid #3b82f6;
}

.notification-content {
    padding: 1rem 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
    color: white;
}

.notification-content i:first-child {
    font-size: 1.2rem;
    opacity: 0.9;
}

.notification-content span {
    flex: 1;
    font-size: 0.9rem;
}

.notification-close {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.6);
    cursor: pointer;
    padding: 0.2rem;
    border-radius: 4px;
    transition: all 0.2s ease;
}

.notification-close:hover {
    color: white;
    background: rgba(255, 255, 255, 0.1);
}

.crown-notification.fade-out {
    animation: slideOut 0.3s ease forwards;
}

@keyframes slideIn {
    to {
        transform: translateX(0);
    }
}

@keyframes slideOut {
    to {
        transform: translateX(100%);
    }
}

.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(13, 13, 13, 0.9);
    backdrop-filter: blur(5px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10001;
}

.loading-spinner {
    text-align: center;
    color: white;
}

.crown-loader {
    font-size: 3rem;
    color: var(--crown-gold);
    animation: crownSpin 2s ease-in-out infinite;
    margin-bottom: 1rem;
}

@keyframes crownSpin {
    0% { transform: rotate(0deg) scale(1); }
    50% { transform: rotate(180deg) scale(1.2); }
    100% { transform: rotate(360deg) scale(1); }
}

.cart-bounce {
    animation: cartBounce 0.6s ease;
}

@keyframes cartBounce {
    0%, 20%, 60%, 100% {
        transform: translateY(0);
    }
    40% {
        transform: translateY(-10px);
    }
    80% {
        transform: translateY(-5px);
    }
}

.wishlist-pulse {
    animation: wishlistPulse 0.6s ease;
}

@keyframes wishlistPulse {
    0% {
        transform: scale(1);
    }
    50% {
        transform: scale(1.2);
    }
    100% {
        transform: scale(1);
    }
}

.image-zoom-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 10002;
    background: rgba(0, 0, 0, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: zoom-out;
}

.zoom-container {
    position: relative;
    max-width: 90vw;
    max-height: 90vh;
}

.zoom-container img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}

.zoom-close {
    position: absolute;
    top: -40px;
    right: -40px;
    background: rgba(255, 255, 255, 0.2);
    border: none;
    color: white;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.2rem;
    transition: all 0.2s ease;
}

.zoom-close:hover {
    background: rgba(255, 255, 255, 0.3);
}

.search-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: rgba(26, 26, 26, 0.95);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    margin-top: 0.5rem;
    max-height: 400px;
    overflow-y: auto;
    z-index: 1000;
    display: none;
}

.search-result-item {
    padding: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.search-result-item:last-child {
    border-bottom: none;
}

.search-result-item a {
    display: flex;
    align-items: center;
    padding: 1rem;
    color: white;
    text-decoration: none;
    transition: all 0.2s ease;
}

.search-result-item a:hover {
    background: rgba(255, 255, 255, 0.1);
}

.search-result-item img {
    width: 50px;
    height: 50px;
    object-fit: cover;
    border-radius: 8px;
    margin-right: 1rem;
}

.search-result-info h6 {
    margin: 0 0 0.2rem 0;
    font-weight: 600;
}

.search-result-category {
    margin: 0;
    font-size: 0.8rem;
    color: rgba(255, 255, 255, 0.6);
}

.search-result-price {
    margin: 0;
    font-weight: 600;
    color: var(--crown-gold);
}

.search-no-results {
    padding: 1.5rem;
    text-align: center;
    color: rgba(255, 255, 255, 0.6);
}
</style>
`;

// Inject dynamic styles
document.head.insertAdjacentHTML('beforeend', dynamicStyles);