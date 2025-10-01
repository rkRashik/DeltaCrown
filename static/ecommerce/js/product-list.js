// Product List JavaScript

class ProductListManager {
    constructor() {
        this.currentView = 'grid';
        this.filters = {};
        this.sortBy = 'newest';
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeFilters();
        this.initializeViewToggle();
        this.initializeLazyLoading();
    }

    bindEvents() {
        // Filter changes
        document.addEventListener('change', (e) => {
            if (e.target.matches('[name="category"], [name="brand"], [name="type"], [name="rarity"]')) {
                this.handleFilterChange(e.target);
            }
        });

        // Price range changes
        document.addEventListener('input', (e) => {
            if (e.target.matches('[name="min_price"], [name="max_price"]')) {
                this.debounce(() => this.handlePriceRangeChange(), 500)();
            }
        });

        // Sort change
        document.addEventListener('change', (e) => {
            if (e.target.matches('[name="sort"]')) {
                this.handleSortChange(e.target.value);
            }
        });

        // View toggle
        document.addEventListener('click', (e) => {
            if (e.target.closest('.view-btn')) {
                this.handleViewToggle(e.target.closest('.view-btn'));
            }
        });

        // Clear filters
        document.addEventListener('click', (e) => {
            if (e.target.matches('.clear-filters')) {
                e.preventDefault();
                this.clearAllFilters();
            }
        });

        // Product actions
        document.addEventListener('click', (e) => {
            if (e.target.closest('.quick-view-btn')) {
                e.preventDefault();
                this.handleQuickView(e.target.closest('.quick-view-btn'));
            }
            
            if (e.target.closest('.compare-btn')) {
                e.preventDefault();
                this.handleCompare(e.target.closest('.compare-btn'));
            }
        });

        // Search form
        const searchForm = document.querySelector('.search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleSearch();
            });
        }

        // Infinite scroll for mobile
        if (window.innerWidth <= 768) {
            this.initializeInfiniteScroll();
        }
    }

    initializeFilters() {
        // Get current filters from URL
        const urlParams = new URLSearchParams(window.location.search);
        this.filters = {
            category: urlParams.get('category') || '',
            brand: urlParams.get('brand') || '',
            type: urlParams.get('type') || '',
            rarity: urlParams.get('rarity') || '',
            min_price: urlParams.get('min_price') || '',
            max_price: urlParams.get('max_price') || '',
            q: urlParams.get('q') || ''
        };
        this.sortBy = urlParams.get('sort') || 'newest';

        // Update filter UI
        this.updateFilterUI();
        this.updateActiveFiltersDisplay();
    }

    initializeViewToggle() {
        const viewButtons = document.querySelectorAll('.view-btn');
        const productsContainer = document.getElementById('products-container');
        
        // Restore saved view preference
        const savedView = localStorage.getItem('crownstore-view') || 'grid';
        this.currentView = savedView;
        
        // Apply saved view
        viewButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === savedView);
        });
        
        if (productsContainer) {
            productsContainer.className = savedView === 'list' ? 'products-list' : 'products-grid';
        }
    }

    initializeLazyLoading() {
        const productImages = document.querySelectorAll('.product-card img[data-src]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });

            productImages.forEach(img => imageObserver.observe(img));
        } else {
            // Fallback for older browsers
            productImages.forEach(img => {
                img.src = img.dataset.src;
            });
        }
    }

    initializeInfiniteScroll() {
        let loading = false;
        let page = 2; // Start from page 2 since page 1 is already loaded

        window.addEventListener('scroll', () => {
            if (loading) return;

            const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
            
            if (scrollTop + clientHeight >= scrollHeight - 1000) {
                loading = true;
                this.loadMoreProducts(page).then(hasMore => {
                    loading = false;
                    if (hasMore) {
                        page++;
                    }
                });
            }
        });
    }

    async loadMoreProducts(page) {
        try {
            const params = new URLSearchParams(this.filters);
            params.append('page', page);
            
            const response = await fetch(`${window.location.pathname}?${params}`);
            const html = await response.text();
            
            // Parse the response to extract products
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newProducts = doc.querySelectorAll('.product-item');
            
            if (newProducts.length > 0) {
                const productsContainer = document.getElementById('products-container');
                newProducts.forEach(product => {
                    productsContainer.appendChild(product);
                });
                
                // Initialize lazy loading for new images
                this.initializeLazyLoading();
                
                // Show loading animation
                this.showLoadingIndicator();
                
                return true;
            }
            
            return false;
        } catch (error) {
            console.error('Error loading more products:', error);
            return false;
        }
    }

    handleFilterChange(input) {
        const filterName = input.name;
        const filterValue = input.checked ? input.value : '';
        
        this.filters[filterName] = filterValue;
        this.updateActiveFiltersDisplay();
        this.applyFilters();
    }

    handlePriceRangeChange() {
        const minPrice = document.querySelector('[name="min_price"]')?.value || '';
        const maxPrice = document.querySelector('[name="max_price"]')?.value || '';
        
        this.filters.min_price = minPrice;
        this.filters.max_price = maxPrice;
        
        this.updateActiveFiltersDisplay();
        this.applyFilters();
    }

    handleSortChange(sortValue) {
        this.sortBy = sortValue;
        this.applyFilters();
    }

    handleViewToggle(button) {
        const view = button.dataset.view;
        const viewButtons = document.querySelectorAll('.view-btn');
        const productsContainer = document.getElementById('products-container');
        
        // Update active button
        viewButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        
        // Update container class
        if (productsContainer) {
            productsContainer.className = view === 'list' ? 'products-list' : 'products-grid';
        }
        
        // Save preference
        localStorage.setItem('crownstore-view', view);
        this.currentView = view;
        
        // Animate transition
        this.animateViewTransition(productsContainer);
    }

    animateViewTransition(container) {
        if (!container) return;
        
        container.style.opacity = '0.5';
        container.style.transform = 'scale(0.98)';
        
        setTimeout(() => {
            container.style.opacity = '1';
            container.style.transform = 'scale(1)';
        }, 150);
    }

    handleSearch() {
        const searchInput = document.querySelector('[name="q"]');
        if (searchInput) {
            this.filters.q = searchInput.value;
            this.applyFilters();
        }
    }

    handleQuickView(button) {
        const productId = button.dataset.productId;
        
        // Create and show quick view modal
        this.showQuickViewModal(productId);
    }

    async showQuickViewModal(productId) {
        // Check if modal already exists
        let modal = document.getElementById('quickViewModal');
        
        if (!modal) {
            // Create modal
            modal = document.createElement('div');
            modal.id = 'quickViewModal';
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Quick View</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body" id="quickViewContent">
                            <div class="text-center p-4">
                                <div class="crown-loader mb-3">
                                    <i class="fas fa-crown"></i>
                                </div>
                                <p>Loading product details...</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        try {
            // Load product quick view content
            const response = await fetch(`/ecommerce/api/product/${productId}/quick-view/`);
            const html = await response.text();
            
            document.getElementById('quickViewContent').innerHTML = html;
            
            // Initialize quick view functionality
            this.initializeQuickViewActions(modal);
            
        } catch (error) {
            console.error('Error loading quick view:', error);
            document.getElementById('quickViewContent').innerHTML = `
                <div class="text-center p-4">
                    <i class="fas fa-exclamation-triangle text-warning mb-3" style="font-size: 2rem;"></i>
                    <p>Error loading product details</p>
                </div>
            `;
        }
    }

    initializeQuickViewActions(modal) {
        // Quick view specific actions
        const addToCartForm = modal.querySelector('.add-to-cart-form');
        if (addToCartForm) {
            addToCartForm.addEventListener('submit', (e) => {
                e.preventDefault();
                window.crownStore.handleAddToCart(addToCartForm);
            });
        }

        const wishlistBtn = modal.querySelector('.wishlist-btn');
        if (wishlistBtn) {
            wishlistBtn.addEventListener('click', (e) => {
                e.preventDefault();
                window.crownStore.handleWishlistToggle(wishlistBtn);
            });
        }

        // Image gallery in quick view
        const thumbnails = modal.querySelectorAll('.thumbnail');
        const mainImage = modal.querySelector('#quickViewMainImage');
        
        thumbnails.forEach(thumb => {
            thumb.addEventListener('click', (e) => {
                e.preventDefault();
                const newImageSrc = thumb.dataset.image;
                if (mainImage && newImageSrc) {
                    mainImage.src = newImageSrc;
                    
                    // Update active thumbnail
                    thumbnails.forEach(t => t.classList.remove('active'));
                    thumb.classList.add('active');
                }
            });
        });
    }

    handleCompare(button) {
        const productId = button.dataset.productId;
        
        // Get compare list from storage
        let compareList = JSON.parse(localStorage.getItem('crownstore-compare') || '[]');
        
        if (compareList.includes(productId)) {
            // Remove from compare
            compareList = compareList.filter(id => id !== productId);
            button.classList.remove('active');
            button.setAttribute('title', 'Add to Compare');
            this.showNotification('Product removed from comparison', 'info');
        } else {
            // Add to compare (max 4 items)
            if (compareList.length >= 4) {
                this.showNotification('You can compare up to 4 products', 'warning');
                return;
            }
            
            compareList.push(productId);
            button.classList.add('active');
            button.setAttribute('title', 'Remove from Compare');
            this.showNotification('Product added to comparison', 'success');
        }
        
        // Save to storage
        localStorage.setItem('crownstore-compare', JSON.stringify(compareList));
        
        // Update compare counter
        this.updateCompareCounter(compareList.length);
    }

    updateCompareCounter(count) {
        const compareCounters = document.querySelectorAll('.compare-count');
        compareCounters.forEach(counter => {
            counter.textContent = count;
            counter.style.display = count > 0 ? 'inline' : 'none';
        });
    }

    clearAllFilters() {
        // Reset filters
        this.filters = {
            category: '',
            brand: '',
            type: '',
            rarity: '',
            min_price: '',
            max_price: '',
            q: ''
        };
        
        // Reset form inputs
        document.querySelectorAll('input[type="radio"]').forEach(input => {
            input.checked = false;
        });
        
        document.querySelectorAll('input[type="number"], input[type="text"]').forEach(input => {
            input.value = '';
        });
        
        // Reset sort
        const sortSelect = document.querySelector('[name="sort"]');
        if (sortSelect) {
            sortSelect.value = 'newest';
        }
        
        // Apply filters (which will redirect to clean URL)
        this.applyFilters();
    }

    applyFilters() {
        // Build URL with current filters
        const params = new URLSearchParams();
        
        Object.entries(this.filters).forEach(([key, value]) => {
            if (value) {
                params.append(key, value);
            }
        });
        
        if (this.sortBy && this.sortBy !== 'newest') {
            params.append('sort', this.sortBy);
        }
        
        // Navigate to new URL
        const newUrl = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
        window.location.href = newUrl;
    }

    updateFilterUI() {
        // Update radio buttons
        Object.entries(this.filters).forEach(([key, value]) => {
            if (value) {
                const input = document.querySelector(`[name="${key}"][value="${value}"]`);
                if (input) {
                    input.checked = true;
                }
            }
        });
        
        // Update text inputs
        ['min_price', 'max_price', 'q'].forEach(key => {
            const input = document.querySelector(`[name="${key}"]`);
            if (input && this.filters[key]) {
                input.value = this.filters[key];
            }
        });
        
        // Update sort select
        const sortSelect = document.querySelector('[name="sort"]');
        if (sortSelect) {
            sortSelect.value = this.sortBy;
        }
    }

    updateActiveFiltersDisplay() {
        // Create or update active filters display
        let activeFiltersContainer = document.querySelector('.active-filters');
        
        if (!activeFiltersContainer) {
            activeFiltersContainer = document.createElement('div');
            activeFiltersContainer.className = 'active-filters';
            
            const toolbar = document.querySelector('.products-toolbar');
            if (toolbar) {
                toolbar.insertAdjacentElement('afterend', activeFiltersContainer);
            }
        }
        
        const activeFilters = [];
        
        Object.entries(this.filters).forEach(([key, value]) => {
            if (value && key !== 'q') {
                let displayValue = value;
                
                // Get display name for filter values
                if (key === 'category' || key === 'brand') {
                    const option = document.querySelector(`[name="${key}"][value="${value}"]`);
                    if (option && option.nextElementSibling) {
                        displayValue = option.nextElementSibling.textContent.trim();
                    }
                } else if (key === 'min_price') {
                    displayValue = `Min: $${value}`;
                } else if (key === 'max_price') {
                    displayValue = `Max: $${value}`;
                }
                
                activeFilters.push({ key, value, displayValue });
            }
        });
        
        if (activeFilters.length === 0) {
            activeFiltersContainer.style.display = 'none';
            return;
        }
        
        activeFiltersContainer.style.display = 'block';
        activeFiltersContainer.innerHTML = `
            <div class="active-filters-content">
                <span class="active-filters-label">Active Filters:</span>
                <div class="filter-tags">
                    ${activeFilters.map(filter => `
                        <span class="filter-tag" data-filter="${filter.key}" data-value="${filter.value}">
                            ${filter.displayValue}
                            <button class="remove-filter" onclick="productListManager.removeFilter('${filter.key}')">
                                <i class="fas fa-times"></i>
                            </button>
                        </span>
                    `).join('')}
                </div>
            </div>
        `;
    }

    removeFilter(filterKey) {
        this.filters[filterKey] = '';
        this.updateFilterUI();
        this.updateActiveFiltersDisplay();
        this.applyFilters();
    }

    showLoadingIndicator() {
        const productsContainer = document.getElementById('products-container');
        
        let loadingIndicator = document.querySelector('.loading-more');
        if (!loadingIndicator) {
            loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'loading-more';
            loadingIndicator.innerHTML = `
                <div class="text-center p-4">
                    <div class="crown-loader">
                        <i class="fas fa-crown"></i>
                    </div>
                    <p>Loading more products...</p>
                </div>
            `;
            productsContainer.insertAdjacentElement('afterend', loadingIndicator);
        }
        
        setTimeout(() => {
            if (loadingIndicator && loadingIndicator.parentNode) {
                loadingIndicator.remove();
            }
        }, 2000);
    }

    showNotification(message, type) {
        if (window.crownStore) {
            window.crownStore.showNotification(message, type);
        }
    }

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
}

// Advanced Features
class ProductComparison {
    constructor() {
        this.compareList = JSON.parse(localStorage.getItem('crownstore-compare') || '[]');
        this.init();
    }

    init() {
        this.updateCompareCounter();
        this.addCompareButton();
    }

    addCompareButton() {
        if (this.compareList.length < 2) return;

        const compareButton = document.createElement('div');
        compareButton.className = 'floating-compare-btn';
        compareButton.innerHTML = `
            <button class="btn btn-primary" onclick="productComparison.showCompareModal()">
                <i class="fas fa-balance-scale"></i>
                Compare (${this.compareList.length})
            </button>
        `;
        
        document.body.appendChild(compareButton);
    }

    updateCompareCounter() {
        const compareCounters = document.querySelectorAll('.compare-count');
        compareCounters.forEach(counter => {
            counter.textContent = this.compareList.length;
            counter.style.display = this.compareList.length > 0 ? 'inline' : 'none';
        });
    }

    async showCompareModal() {
        // Implementation for comparison modal
        console.log('Show compare modal for products:', this.compareList);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.productListManager = new ProductListManager();
    window.productComparison = new ProductComparison();
});

// CSS for active filters and loading
const productListStyles = `
<style>
.active-filters {
    margin-bottom: 2rem;
    padding: 1rem 1.5rem;
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.active-filters-content {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
}

.active-filters-label {
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.9rem;
    font-weight: 500;
}

.filter-tags {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
}

.filter-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.3rem 0.8rem;
    background: var(--crown-gold);
    color: var(--crown-dark);
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
}

.remove-filter {
    background: none;
    border: none;
    color: inherit;
    cursor: pointer;
    padding: 0;
    font-size: 0.7rem;
    opacity: 0.7;
    transition: opacity 0.2s ease;
}

.remove-filter:hover {
    opacity: 1;
}

.loading-more {
    text-align: center;
    padding: 2rem;
    color: rgba(255, 255, 255, 0.7);
}

.floating-compare-btn {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 1000;
}

.floating-compare-btn .btn {
    border-radius: 50px;
    padding: 1rem 1.5rem;
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
}

@media (max-width: 768px) {
    .active-filters-content {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.8rem;
    }
    
    .floating-compare-btn {
        bottom: 80px;
    }
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', productListStyles);