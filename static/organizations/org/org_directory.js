/**
 * Organization Directory - Interactive Search and Filters
 * 
 * Phase B: Real search behavior using query params (server-rendered)
 * No fetch API - keeps it simple by redirecting with query params
 */

(function() {
    'use strict';

    // Debounce helper
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

    // Build URL with current filters
    function buildFilterURL() {
        const searchInput = document.getElementById('org-search');
        const regionFilter = document.getElementById('region-filter');
        
        const params = new URLSearchParams();
        
        const q = searchInput ? searchInput.value.trim() : '';
        const region = regionFilter ? regionFilter.value : '';
        
        if (q) params.set('q', q);
        if (region) params.set('region', region);
        params.set('page', '1'); // Reset to page 1 on filter change
        
        return `/orgs/?${params.toString()}`;
    }

    // Redirect to filtered URL
    function applyFilters() {
        window.location.href = buildFilterURL();
    }

    // Initialize event listeners
    function init() {
        // Search input - debounced redirect
        const searchInput = document.getElementById('org-search');
        if (searchInput) {
            const debouncedSearch = debounce(applyFilters, 300);
            searchInput.addEventListener('input', debouncedSearch);
        }

        // Region filter - immediate redirect
        const regionFilter = document.getElementById('region-filter');
        if (regionFilter) {
            regionFilter.addEventListener('change', applyFilters);
        }

        console.log('✅ Organization Directory filters initialized (Phase B)');
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
