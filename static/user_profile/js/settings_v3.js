/**
 * Settings Page Controller (Vanilla JS - No Alpine)
 * Phase 14B: Complete Alpine.js removal
 * 
 * Handles tab navigation, form submissions, dynamic content loading
 * Uses APIClient for all server communication
 */

class SettingsController {
    constructor(apiClient) {
        this.api = apiClient;
        this.activeSection = 'profile';
        this.loading = false;
        this.formData = {};
        
        this._initElements();
        this._initEventListeners();
        this._loadInitialSection();
    }

    /**
     * Cache DOM elements
     * @private
     */
    _initElements() {
        this.navItems = document.querySelectorAll('[data-section]');
        this.sections = document.querySelectorAll('[data-settings-section]');
        this.forms = document.querySelectorAll('[data-settings-form]');
    }

    /**
     * Initialize event listeners
     * @private
     */
    _initEventListeners() {
        // Tab navigation
        this.navItems.forEach(nav => {
            nav.addEventListener('click', (e) => {
                e.preventDefault();
                const section = nav.dataset.section;
                this.switchSection(section);
            });
        });

        // Form submissions
        this.forms.forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const formType = form.dataset.settingsForm;
                await this.handleFormSubmit(form, formType);
            });
        });

        // Avatar/banner upload
        const avatarInput = document.getElementById('avatar-upload');
        const bannerInput = document.getElementById('banner-upload');
        
        if (avatarInput) {
            avatarInput.addEventListener('change', (e) => this.handleMediaUpload(e, 'avatar'));
        }
        if (bannerInput) {
            bannerInput.addEventListener('change', (e) => this.handleMediaUpload(e, 'banner'));
        }

        // Remove media buttons
        document.querySelectorAll('[data-remove-media]').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const mediaType = btn.dataset.removeMedia;
                await this.handleMediaRemove(mediaType);
            });
        });

        // Dynamic game passport creation
        const addPassportBtn = document.getElementById('add-passport-btn');
        if (addPassportBtn) {
            addPassportBtn.addEventListener('click', () => this.showPassportModal());
        }

        // Social link addition
        const addSocialBtn = document.getElementById('add-social-btn');
        if (addSocialBtn) {
            addSocialBtn.addEventListener('click', () => this.showSocialModal());
        }
    }

    /**
     * Load initial section from URL hash or default
     * @private
     */
    _loadInitialSection() {
        const hash = window.location.hash.replace('#', '');
        const initialSection = hash || 'profile';
        this.switchSection(initialSection);

        // Update URL hash on section switch
        window.addEventListener('hashchange', () => {
            const newHash = window.location.hash.replace('#', '');
            if (newHash && newHash !== this.activeSection) {
                this.switchSection(newHash);
            }
        });
    }

    /**
     * Switch to a different settings section
     * @param {string} sectionName
     */
    switchSection(sectionName) {
        // Update active nav item
        this.navItems.forEach(nav => {
            if (nav.dataset.section === sectionName) {
                nav.classList.add('active');
            } else {
                nav.classList.remove('active');
            }
        });

        // Show/hide sections
        this.sections.forEach(section => {
            if (section.dataset.settingsSection === sectionName) {
                section.classList.remove('hidden');
                section.setAttribute('aria-hidden', 'false');
            } else {
                section.classList.add('hidden');
                section.setAttribute('aria-hidden', 'true');
            }
        });

        this.activeSection = sectionName;
        window.location.hash = sectionName;
    }

    /**
     * Handle form submission
     * @param {HTMLFormElement} form
     * @param {string} formType - 'basic', 'privacy', 'notifications', etc.
     */
    async handleFormSubmit(form, formType) {
        if (this.loading) return;

        const submitBtn = form.querySelector('button[type="submit"]');
        this.loading = true;
        
        try {
            this.api.showLoading(submitBtn, 'Saving...');

            const formData = new FormData(form);
            const endpoint = form.action || this._getEndpointForFormType(formType);

            const response = await this.api.post(endpoint, formData);

            if (response.success || response.status === 'success') {
                this.api.showToast(response.message || 'Settings saved successfully!', 'success');
                
                // Update UI with new data if provided
                if (response.data) {
                    this._updateUIWithData(formType, response.data);
                }
            } else {
                throw new Error(response.message || 'Failed to save settings');
            }

        } catch (error) {
            console.error('Form submission error:', error);
            let errorMessage = 'Failed to save settings. Please try again.';
            
            if (error instanceof APIError) {
                if (error.is(400)) {
                    errorMessage = error.data.message || 'Invalid data. Please check your inputs.';
                } else if (error.is(403)) {
                    errorMessage = 'You do not have permission to modify these settings.';
                } else if (error.isServerError()) {
                    errorMessage = 'Server error. Please try again later.';
                }
            }

            this.api.showToast(errorMessage, 'error');
        } finally {
            this.api.hideLoading(submitBtn);
            this.loading = false;
        }
    }

    /**
     * Get API endpoint for form type
     * @param {string} formType
     * @returns {string}
     * @private
     */
    _getEndpointForFormType(formType) {
        const endpoints = {
            'basic': '/me/settings/basic/',
            'privacy': '/me/settings/privacy/save/',
            'notifications': '/api/notification-preferences/update/',
            'platform': '/api/platform-preferences/update/',
            'wallet': '/api/wallet-settings/update/',
            'social': '/api/social-links/update/'
        };
        return endpoints[formType] || '/me/settings/basic/';
    }

    /**
     * Update UI elements with response data
     * @param {string} formType
     * @param {Object} data
     * @private
     */
    _updateUIWithData(formType, data) {
        // Update profile display if basic info changed
        if (formType === 'basic' && data.display_name) {
            const displayNameElements = document.querySelectorAll('[data-display-name]');
            displayNameElements.forEach(el => {
                el.textContent = data.display_name;
            });
        }

        // Update avatar/banner previews
        if (data.avatar_url) {
            const avatarElements = document.querySelectorAll('[data-avatar]');
            avatarElements.forEach(el => {
                el.src = data.avatar_url;
            });
        }

        if (data.banner_url) {
            const bannerElements = document.querySelectorAll('[data-banner]');
            bannerElements.forEach(el => {
                el.src = data.banner_url;
            });
        }
    }

    /**
     * Handle media upload (avatar/banner)
     * @param {Event} event
     * @param {string} mediaType - 'avatar' or 'banner'
     */
    async handleMediaUpload(event, mediaType) {
        const file = event.target.files[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            this.api.showToast('Please select an image file', 'error');
            return;
        }

        // Validate file size (5MB max)
        if (file.size > 5 * 1024 * 1024) {
            this.api.showToast('Image must be smaller than 5MB', 'error');
            return;
        }

        const formData = new FormData();
        formData.append(mediaType, file);

        try {
            const uploadBtn = event.target.closest('.upload-btn') || event.target.parentElement;
            this.api.showLoading(uploadBtn, 'Uploading...');

            const response = await this.api.post('/me/settings/media/', formData);

            if (response.success) {
                this.api.showToast(`${mediaType} updated successfully!`, 'success');
                
                // Update preview
                const previewEl = document.getElementById(`${mediaType}-preview`);
                if (previewEl && response[`${mediaType}_url`]) {
                    previewEl.src = response[`${mediaType}_url`];
                }
            }

        } catch (error) {
            console.error('Media upload error:', error);
            this.api.showToast(`Failed to upload ${mediaType}`, 'error');
        }
    }

    /**
     * Handle media removal (avatar/banner)
     * @param {string} mediaType - 'avatar' or 'banner'
     */
    async handleMediaRemove(mediaType) {
        if (!confirm(`Are you sure you want to remove your ${mediaType}?`)) {
            return;
        }

        try {
            const response = await this.api.post('/me/settings/media/remove/', {
                media_type: mediaType
            });

            if (response.success) {
                this.api.showToast(`${mediaType} removed successfully!`, 'success');
                
                // Reset preview to default
                const previewEl = document.getElementById(`${mediaType}-preview`);
                if (previewEl && response[`default_${mediaType}_url`]) {
                    previewEl.src = response[`default_${mediaType}_url`];
                }
            }

        } catch (error) {
            console.error('Media removal error:', error);
            this.api.showToast(`Failed to remove ${mediaType}`, 'error');
        }
    }

    /**
     * Show game passport creation modal
     */
    async showPassportModal() {
        const modal = document.getElementById('passport-modal');
        if (!modal) {
            console.error('Passport modal not found');
            return;
        }

        // Load available games dynamically
        try {
            const games = await this.api.get('/api/games/');
            this._populateGameSelect(games);
        } catch (error) {
            console.error('Failed to load games:', error);
            this.api.showToast('Failed to load games list', 'error');
        }

        modal.classList.add('show');
        modal.setAttribute('aria-hidden', 'false');
    }

    /**
     * Populate game select dropdown
     * @param {Array} games
     * @private
     */
    _populateGameSelect(games) {
        const select = document.getElementById('passport-game-select');
        if (!select) return;

        select.innerHTML = '<option value="">Select a game...</option>';
        games.forEach(game => {
            const option = document.createElement('option');
            option.value = game.id;
            option.textContent = game.name;
            select.appendChild(option);
        });
    }

    /**
     * Show social link addition modal
     */
    async showSocialModal() {
        const modal = document.getElementById('social-modal');
        if (!modal) {
            console.error('Social modal not found');
            return;
        }

        // Load available platforms dynamically
        try {
            const platforms = await this.api.get('/api/social-links/platforms/');
            this._populatePlatformSelect(platforms);
        } catch (error) {
            console.error('Failed to load platforms:', error);
            this.api.showToast('Failed to load platforms list', 'error');
        }

        modal.classList.add('show');
        modal.setAttribute('aria-hidden', 'false');
    }

    /**
     * Populate platform select dropdown
     * @param {Array} platforms
     * @private
     */
    _populatePlatformSelect(platforms) {
        const select = document.getElementById('social-platform-select');
        if (!select) return;

        select.innerHTML = '<option value="">Select a platform...</option>';
        platforms.forEach(platform => {
            const option = document.createElement('option');
            option.value = platform.value;
            option.textContent = platform.label;
            select.appendChild(option);
        });
    }

    /**
     * Close modal
     * @param {string} modalId
     */
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden', 'true');
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    if (!csrfToken) {
        console.error('CSRF token not found');
        return;
    }

    const apiClient = new APIClient(csrfToken);
    window.settingsController = new SettingsController(apiClient);
});
