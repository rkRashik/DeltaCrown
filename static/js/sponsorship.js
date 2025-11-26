/**
 * Sponsorship API Client
 * Frontend JavaScript for sponsorship features
 */

const SponsorshipAPI = {
    baseUrl: '/teams/sponsorship/api/',
    
    /**
     * Get CSRF token from cookie
     */
    getCsrfToken() {
        const name = 'csrftoken';
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
    },
    
    /**
     * Make API request
     */
    async request(action, data = {}) {
        try {
            const response = await fetch(this.baseUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                },
                body: JSON.stringify({
                    action: action,
                    ...data
                })
            });
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            return { success: false, error: 'Network error' };
        }
    },
    
    /**
     * Track sponsor impression
     */
    async trackSponsorImpression(sponsorId) {
        return await this.request('track_sponsor_impression', {
            sponsor_id: sponsorId
        });
    },
    
    /**
     * Track promotion impression
     */
    async trackPromotionImpression(promotionId) {
        return await this.request('track_promotion_impression', {
            promotion_id: promotionId
        });
    },
    
    /**
     * Get active sponsors for a team
     */
    async getSponsors(teamSlug, tier = null) {
        return await this.request('get_sponsors', {
            team_slug: teamSlug,
            tier: tier
        });
    },
    
    /**
     * Get merchandise for a team
     */
    async getMerchandise(teamSlug, category = null) {
        return await this.request('get_merchandise', {
            team_slug: teamSlug,
            category: category
        });
    }
};

/**
 * Initialize impression tracking on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    // Track sponsor impressions
    const sponsorElements = document.querySelectorAll('[data-sponsor-id]');
    sponsorElements.forEach(element => {
        const sponsorId = element.dataset.sponsorId;
        if (sponsorId) {
            // Track impression after element is visible for 1 second
            setTimeout(() => {
                if (isElementInViewport(element)) {
                    SponsorshipAPI.trackSponsorImpression(sponsorId);
                }
            }, 1000);
        }
    });
    
    // Track promotion impressions
    const promotionElements = document.querySelectorAll('[data-promotion-id]');
    promotionElements.forEach(element => {
        const promotionId = element.dataset.promotionId;
        if (promotionId) {
            setTimeout(() => {
                if (isElementInViewport(element)) {
                    SponsorshipAPI.trackPromotionImpression(promotionId);
                }
            }, 1000);
        }
    });
});

/**
 * Check if element is in viewport
 */
function isElementInViewport(el) {
    const rect = el.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Sponsor Inquiry Form Handler
 */
class SponsorInquiryForm {
    constructor(formId) {
        this.form = document.getElementById(formId);
        if (this.form) {
            this.init();
        }
    }
    
    init() {
        this.form.addEventListener('submit', this.handleSubmit.bind(this));
        this.setupValidation();
    }
    
    setupValidation() {
        // Message length validation
        const messageField = this.form.querySelector('#message');
        if (messageField) {
            messageField.addEventListener('input', () => {
                const length = messageField.value.length;
                const counter = this.form.querySelector('#message-counter');
                if (counter) {
                    counter.textContent = `${length} / 2000 characters`;
                    if (length < 50) {
                        counter.style.color = '#e74c3c';
                    } else {
                        counter.style.color = '#27ae60';
                    }
                }
            });
        }
    }
    
    async handleSubmit(e) {
        // Form validation is handled by HTML5 and backend
        // This is just for additional UX improvements
        const submitBtn = this.form.querySelector('[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Submitting...';
        }
    }
}

/**
 * Merchandise Filter Handler
 */
class MerchandiseFilter {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (this.container) {
            this.init();
        }
    }
    
    init() {
        const filterButtons = this.container.querySelectorAll('[data-category]');
        filterButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                this.filterItems(button.dataset.category);
            });
        });
    }
    
    filterItems(category) {
        const items = document.querySelectorAll('[data-item-category]');
        items.forEach(item => {
            if (category === 'all' || item.dataset.itemCategory === category) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
        
        // Update active button
        const buttons = this.container.querySelectorAll('[data-category]');
        buttons.forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');
    }
}

/**
 * Analytics Dashboard
 */
class SponsorshipDashboard {
    constructor(dashboardId) {
        this.dashboard = document.getElementById(dashboardId);
        if (this.dashboard) {
            this.init();
        }
    }
    
    init() {
        this.loadDashboardData();
        // Refresh every 5 minutes
        setInterval(() => this.loadDashboardData(), 300000);
    }
    
    async loadDashboardData() {
        // Implementation for real-time dashboard updates
        dcLog('Loading dashboard data...');
        // This can be expanded to fetch real-time analytics
    }
    
    renderChart(elementId, data) {
        // Placeholder for chart rendering
        // Can be implemented with Chart.js or similar
        dcLog('Rendering chart:', elementId, data);
    }
}

/**
 * Auto-initialize components
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize sponsor inquiry form
    if (document.getElementById('inquiry-form')) {
        new SponsorInquiryForm('inquiry-form');
    }
    
    // Initialize merchandise filter
    if (document.getElementById('merchandise-filter')) {
        new MerchandiseFilter('merchandise-filter');
    }
    
    // Initialize dashboard
    if (document.getElementById('sponsorship-dashboard')) {
        new SponsorshipDashboard('sponsorship-dashboard');
    }
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        SponsorshipAPI,
        SponsorInquiryForm,
        MerchandiseFilter,
        SponsorshipDashboard
    };
}
