/**
 * DeltaCrown API Client
 * Centralized fetch wrapper with CSRF handling, error handling, and toast notifications
 * 
 * Phase 14B: Replace scattered fetch calls with consistent API client
 * 
 * Usage:
 *   const api = new APIClient(csrfToken);
 *   const data = await api.post('/api/endpoint/', { key: 'value' });
 *   api.showToast('Success!', 'success');
 */

class APIClient {
    /**
     * @param {string} csrfToken - Django CSRF token
     * @param {Object} options - Optional configuration
     */
    constructor(csrfToken, options = {}) {
        this.csrfToken = csrfToken;
        this.baseURL = options.baseURL || '';
        this.timeout = options.timeout || 30000; // 30 seconds
        this.retries = options.retries || 1;
        this.toastContainer = null;
        this._initToastContainer();
    }

    /**
     * Initialize toast notification container
     * @private
     */
    _initToastContainer() {
        if (!document.getElementById('dc-toast-container')) {
            const container = document.createElement('div');
            container.id = 'dc-toast-container';
            container.className = 'dc-toast-container';
            container.setAttribute('aria-live', 'polite');
            container.setAttribute('aria-atomic', 'true');
            document.body.appendChild(container);
            this.toastContainer = container;
        } else {
            this.toastContainer = document.getElementById('dc-toast-container');
        }
    }

    /**
     * Core fetch method with timeout, retries, and error handling
     * @param {string} url - API endpoint URL
     * @param {Object} options - Fetch options
     * @param {number} attempt - Current retry attempt
     * @returns {Promise<any>}
     * @private
     */
    async _fetch(url, options = {}, attempt = 1) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(this.baseURL + url, {
                ...options,
                signal: controller.signal,
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                    ...options.headers
                },
                credentials: 'same-origin'
            });

            clearTimeout(timeoutId);

            // Handle non-2xx responses
            if (!response.ok) {
                const errorData = await this._parseErrorResponse(response);
                throw new APIError(response.status, response.statusText, errorData);
            }

            // Parse response based on content type
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            return await response.text();

        } catch (error) {
            clearTimeout(timeoutId);

            // Retry on network errors (not on client errors like 400, 403)
            if (error.name === 'AbortError' || error.name === 'TypeError') {
                if (attempt < this.retries) {
                    console.warn(`APIClient: Retry ${attempt}/${this.retries} for ${url}`);
                    await this._sleep(1000 * attempt); // Exponential backoff
                    return this._fetch(url, options, attempt + 1);
                }
            }

            throw error;
        }
    }

    /**
     * Parse error response body
     * @param {Response} response
     * @returns {Promise<Object>}
     * @private
     */
    async _parseErrorResponse(response) {
        try {
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            return { message: await response.text() };
        } catch {
            return { message: response.statusText };
        }
    }

    /**
     * Sleep utility for retries
     * @param {number} ms - Milliseconds to sleep
     * @returns {Promise<void>}
     * @private
     */
    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * GET request
     * @param {string} url - API endpoint
     * @param {Object} params - Query parameters
     * @returns {Promise<any>}
     */
    async get(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        
        return this._fetch(fullUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });
    }

    /**
     * POST request
     * @param {string} url - API endpoint
     * @param {Object|FormData} data - Request body
     * @returns {Promise<any>}
     */
    async post(url, data = {}) {
        const isFormData = data instanceof FormData;
        
        const options = {
            method: 'POST',
            body: isFormData ? data : JSON.stringify(data)
        };

        if (!isFormData) {
            options.headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            };
        }

        return this._fetch(url, options);
    }

    /**
     * PUT request
     * @param {string} url - API endpoint
     * @param {Object|FormData} data - Request body
     * @returns {Promise<any>}
     */
    async put(url, data = {}) {
        const isFormData = data instanceof FormData;
        
        const options = {
            method: 'PUT',
            body: isFormData ? data : JSON.stringify(data)
        };

        if (!isFormData) {
            options.headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            };
        }

        return this._fetch(url, options);
    }

    /**
     * PATCH request
     * @param {string} url - API endpoint
     * @param {Object|FormData} data - Request body
     * @returns {Promise<any>}
     */
    async patch(url, data = {}) {
        const isFormData = data instanceof FormData;
        
        const options = {
            method: 'PATCH',
            body: isFormData ? data : JSON.stringify(data)
        };

        if (!isFormData) {
            options.headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            };
        }

        return this._fetch(url, options);
    }

    /**
     * DELETE request
     * @param {string} url - API endpoint
     * @returns {Promise<any>}
     */
    async delete(url) {
        return this._fetch(url, {
            method: 'DELETE',
            headers: {
                'Accept': 'application/json'
            }
        });
    }

    /**
     * Show toast notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type ('success', 'error', 'warning', 'info')
     * @param {number} duration - Display duration in ms (0 = permanent)
     */
    showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `dc-toast dc-toast-${type}`;
        toast.setAttribute('role', 'alert');
        
        const icon = this._getToastIcon(type);
        toast.innerHTML = `
            <div class="dc-toast-icon">${icon}</div>
            <div class="dc-toast-content">${this._escapeHtml(message)}</div>
            <button class="dc-toast-close" aria-label="Close">×</button>
        `;

        const closeBtn = toast.querySelector('.dc-toast-close');
        closeBtn.addEventListener('click', () => this._removeToast(toast));

        this.toastContainer.appendChild(toast);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.classList.add('dc-toast-show');
        });

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => this._removeToast(toast), duration);
        }
    }

    /**
     * Get icon for toast type
     * @param {string} type
     * @returns {string}
     * @private
     */
    _getToastIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }

    /**
     * Remove toast with animation
     * @param {HTMLElement} toast
     * @private
     */
    _removeToast(toast) {
        toast.classList.remove('dc-toast-show');
        toast.classList.add('dc-toast-hide');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    /**
     * Escape HTML to prevent XSS in toast messages
     * @param {string} html
     * @returns {string}
     * @private
     */
    _escapeHtml(html) {
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }

    /**
     * Show loading indicator
     * @param {HTMLElement} element - Element to show loading on
     * @param {string} message - Loading message
     */
    showLoading(element, message = 'Loading...') {
        element.classList.add('dc-loading');
        element.setAttribute('aria-busy', 'true');
        const originalContent = element.innerHTML;
        element.dataset.originalContent = originalContent;
        element.innerHTML = `<span class="dc-spinner"></span> ${this._escapeHtml(message)}`;
    }

    /**
     * Hide loading indicator
     * @param {HTMLElement} element - Element to hide loading on
     */
    hideLoading(element) {
        element.classList.remove('dc-loading');
        element.removeAttribute('aria-busy');
        if (element.dataset.originalContent) {
            element.innerHTML = element.dataset.originalContent;
            delete element.dataset.originalContent;
        }
    }
}

/**
 * Custom API error class
 */
class APIError extends Error {
    constructor(status, statusText, data) {
        super(data.message || statusText);
        this.name = 'APIError';
        this.status = status;
        this.statusText = statusText;
        this.data = data;
    }

    /**
     * Check if error is a specific HTTP status
     * @param {number} status
     * @returns {boolean}
     */
    is(status) {
        return this.status === status;
    }

    /**
     * Check if error is a client error (4xx)
     * @returns {boolean}
     */
    isClientError() {
        return this.status >= 400 && this.status < 500;
    }

    /**
     * Check if error is a server error (5xx)
     * @returns {boolean}
     */
    isServerError() {
        return this.status >= 500 && this.status < 600;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { APIClient, APIError };
}
