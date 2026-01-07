/**
 * Settings Controller (Vanilla JS - Alpine.js replacement)
 * UP-PHASE15 Session 3: Complete rewrite without Alpine dependency
 * 
 * Features:
 * - Hash-based section navigation
 * - Form state management
 * - API integration with fetch
 * - CSRF protection
 * - Optimistic UI updates
 * - Server validation error display
 */

class SettingsController {
    constructor() {
        this.activeSection = 'profile';
        this.loading = false;
        this.alert = { show: false, type: '', message: '', icon: '' };
        
        // State
        this.profile = {};
        this.notifications = { email: {}, platform: {} };
        this.platform = {};
        this.wallet = {};
        
        // DOM elements (cached for performance)
        this.navItems = null;
        this.sections = null;
        this.alertContainer = null;
        
        this.init();
    }
    
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }
    
    setup() {
        // Cache DOM elements
        this.navItems = document.querySelectorAll('.nav-item');
        this.sections = document.querySelectorAll('.content-section');
        this.alertContainer = document.querySelector('.alert-container');
        
        // Load initial data from JSON script tags
        this.loadInitialData();
        
        // Setup event listeners
        this.setupNavigation();
        this.setupForms();
        
        // Handle initial hash
        this.handleHashChange();
        window.addEventListener('hashchange', () => this.handleHashChange());
    }
    
    loadInitialData() {
        // Load from Django json_script tags
        const profileData = document.getElementById('profile-data');
        const notificationData = document.getElementById('notification-data');
        const platformData = document.getElementById('platform-data');
        const walletData = document.getElementById('wallet-data');
        
        if (profileData) {
            this.profile = JSON.parse(profileData.textContent);
        }
        if (notificationData) {
            this.notifications = JSON.parse(notificationData.textContent);
        }
        if (platformData) {
            this.platform = JSON.parse(platformData.textContent);
        }
        if (walletData) {
            this.wallet = JSON.parse(walletData.textContent);
        }
        
        // Bind data to form fields
        this.bindFormData();
    }
    
    bindFormData() {
        // Profile
        const displayNameInput = document.getElementById('display_name');
        const bioInput = document.getElementById('bio');
        const countrySelect = document.getElementById('country');
        const pronounsInput = document.getElementById('pronouns');
        
        if (displayNameInput && this.profile.display_name) {
            displayNameInput.value = this.profile.display_name;
        }
        if (bioInput && this.profile.bio) {
            bioInput.value = this.profile.bio;
        }
        if (countrySelect && this.profile.country) {
            countrySelect.value = this.profile.country;
        }
        if (pronounsInput && this.profile.pronouns) {
            pronounsInput.value = this.profile.pronouns;
        }
        
        // Platform
        const languageSelect = document.getElementById('preferred_language');
        const timezoneSelect = document.getElementById('timezone_pref');
        const timeFormatSelect = document.getElementById('time_format');
        const themeSelect = document.getElementById('theme_preference');
        
        if (languageSelect && this.platform.preferred_language) {
            languageSelect.value = this.platform.preferred_language;
        }
        if (timezoneSelect && this.platform.timezone_pref) {
            timezoneSelect.value = this.platform.timezone_pref;
        }
        if (timeFormatSelect && this.platform.time_format) {
            timeFormatSelect.value = this.platform.time_format;
        }
        if (themeSelect && this.platform.theme_preference) {
            themeSelect.value = this.platform.theme_preference;
        }
        
        // Wallet
        ['bkash', 'nagad', 'rocket'].forEach(method => {
            const enabledCheckbox = document.getElementById(`${method}_enabled`);
            const accountInput = document.getElementById(`${method}_account`);
            
            if (enabledCheckbox) {
                enabledCheckbox.checked = this.wallet[`${method}_enabled`] || false;
                this.updateWalletFieldVisibility(method);
            }
            if (accountInput && this.wallet[`${method}_account`]) {
                accountInput.value = this.wallet[`${method}_account`];
            }
        });
        
        // Notifications - handle toggles
        this.bindNotificationToggles();
    }
    
    bindNotificationToggles() {
        // Email notifications
        Object.keys(this.notifications.email || {}).forEach(key => {
            const checkbox = document.getElementById(`email_${key}`);
            if (checkbox) {
                checkbox.checked = this.notifications.email[key].value || false;
            }
        });
        
        // Platform notifications
        Object.keys(this.notifications.platform || {}).forEach(key => {
            const checkbox = document.getElementById(`notify_${key}`);
            if (checkbox) {
                checkbox.checked = this.notifications.platform[key].value || false;
            }
        });
    }
    
    setupNavigation() {
        this.navItems.forEach(navItem => {
            navItem.addEventListener('click', (e) => {
                const section = navItem.dataset.section;
                if (section) {
                    this.switchSection(section);
                }
            });
        });
    }
    
    setupForms() {
        // Profile form
        const profileForm = document.getElementById('profile-form');
        if (profileForm) {
            profileForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveProfile();
            });
        }
        
        // Notifications form
        const notificationsForm = document.getElementById('notifications-form');
        if (notificationsForm) {
            notificationsForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveNotifications();
            });
        }
        
        // Platform form
        const platformForm = document.getElementById('platform-form');
        if (platformForm) {
            platformForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.savePlatform();
            });
        }
        
        // Wallet form
        const walletForm = document.getElementById('wallet-form');
        if (walletForm) {
            walletForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveWallet();
            });
        }
        
        // Wallet enable/disable toggles
        ['bkash', 'nagad', 'rocket'].forEach(method => {
            const checkbox = document.getElementById(`${method}_enabled`);
            if (checkbox) {
                checkbox.addEventListener('change', () => {
                    this.updateWalletFieldVisibility(method);
                });
            }
        });
        
        // Delete account button
        const deleteBtn = document.getElementById('delete-account-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.deleteAccount());
        }
    }
    
    handleHashChange() {
        const hash = window.location.hash.slice(1); // Remove #
        const validSections = ['profile', 'privacy', 'notifications', 'platform', 'wallet', 'account', 'about', 'game-passports', 'kyc', 'security', 'social'];
        
        // Phase 9A-15 Section F: Smart tab persistence
        // If user explicitly navigated to a hash, use that
        if (hash && validSections.includes(hash)) {
            this.switchSection(hash);
            // Store as last visited for future persistence
            try {
                localStorage.setItem('settings_last_section', hash);
            } catch (e) {
                // Ignore localStorage errors
            }
        } else {
            // No hash provided - check if user previously navigated to a specific tab
            let targetSection = 'profile'; // Default for fresh visits
            
            try {
                const lastSection = localStorage.getItem('settings_last_section');
                // Only restore if:
                // 1. lastSection exists
                // 2. It's a valid section
                // 3. User is not being redirected with a forced hash (e.g., from teams)
                if (lastSection && validSections.includes(lastSection) && !hash) {
                    targetSection = lastSection;
                }
            } catch (e) {
                // localStorage not available - use default
            }
            
            this.switchSection(targetSection);
            window.location.hash = targetSection;
        }
    }
    
    switchSection(section) {
        this.activeSection = section;
        window.location.hash = section;
        
        // Phase 9A-15 Section F: Store last visited section for smart persistence
        try {
            localStorage.setItem('settings_last_section', section);
        } catch (e) {
            // Ignore localStorage errors
        }
        
        // Update nav active state
        this.navItems.forEach(item => {
            if (item.dataset.section === section) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
        
        // Show/hide sections
        let sectionFound = false;
        this.sections.forEach(sectionEl => {
            if (sectionEl.dataset.section === section) {
                sectionEl.classList.remove('hidden');
                sectionEl.style.display = 'block';
                sectionFound = true;
            } else {
                sectionEl.classList.add('hidden');
                sectionEl.style.display = 'none';
            }
        });
        
        // Task 1 Performance Fix: Lazy load game passports when tab is activated
        if (section === 'game-passports' && window.gamePassports && !window.gamePassports._initialized) {
            window.gamePassports.init();
            window.gamePassports._initialized = true;
        }
        
        // Error handling: If section not found in DOM, show alert
        if (!sectionFound) {
            console.warn(`Settings section "${section}" not found in DOM`);
            this.showAlert('warning', `Section "${section}" is not available.`);
        }
    }
    
    updateWalletFieldVisibility(method) {
        const checkbox = document.getElementById(`${method}_enabled`);
        const accountInput = document.getElementById(`${method}_account`);
        
        if (checkbox && accountInput) {
            if (checkbox.checked) {
                accountInput.parentElement.style.display = 'block';
                accountInput.required = true;
            } else {
                accountInput.parentElement.style.display = 'none';
                accountInput.required = false;
            }
        }
    }
    
    // Helper: Get CSRF token
    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    // Helper: Make API request
    async apiRequest(url, method = 'GET', data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            }
        };
        
        if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw error;
        }
        
        return response.json();
    }

    // API Methods
    async saveProfile() {
        this.setLoading(true);
        
        const formData = {
            display_name: document.getElementById('display_name')?.value,
            bio: document.getElementById('bio')?.value,
            country: document.getElementById('country')?.value,
            pronouns: document.getElementById('pronouns')?.value
        };
        
        try {
            const response = await this.apiRequest('/profile/me/settings/basic/', 'POST', formData);
            
            if (response.success) {
                this.showAlert('success', 'Profile saved successfully!');
                this.profile = { ...this.profile, ...formData };
            } else {
                this.showAlert('error', response.error || 'Failed to save profile');
                this.displayFieldErrors(response.errors);
            }
        } catch (error) {
            console.error('Profile save error:', error);
            this.showAlert('error', 'Network error. Please try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    async saveNotifications() {
        this.setLoading(true);
        
        const payload = {};
        
        // Collect email notification preferences
        Object.keys(this.notifications.email || {}).forEach(key => {
            const checkbox = document.getElementById(`email_${key}`);
            if (checkbox) {
                payload[`email_${key}`] = checkbox.checked;
            }
        });
        
        // Collect platform notification preferences
        Object.keys(this.notifications.platform || {}).forEach(key => {
            const checkbox = document.getElementById(`notify_${key}`);
            if (checkbox) {
                payload[`notify_${key}`] = checkbox.checked;
            }
        });
        
        try {
            const response = await this.apiRequest('/profile/api/notification-preferences/', 'POST', payload);
            
            if (response.success) {
                this.showAlert('success', 'Notification preferences saved!');
            } else {
                this.showAlert('error', response.error || 'Failed to save preferences');
            }
        } catch (error) {
            console.error('Notifications save error:', error);
            this.showAlert('error', 'Network error. Please try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    async savePlatform() {
        this.setLoading(true);
        
        const formData = {
            preferred_language: document.getElementById('preferred_language')?.value,
            timezone_pref: document.getElementById('timezone_pref')?.value,
            time_format: document.getElementById('time_format')?.value,
            theme_preference: document.getElementById('theme_preference')?.value
        };
        
        try {
            const response = await this.apiRequest('/profile/api/platform-preferences/', 'POST', formData);
            
            if (response.success) {
                this.showAlert('success', 'Platform preferences saved!');
                this.platform = { ...this.platform, ...formData };
            } else {
                this.showAlert('error', response.error || 'Failed to save preferences');
            }
        } catch (error) {
            console.error('Platform save error:', error);
            this.showAlert('error', 'Network error. Please try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    async saveWallet() {
        this.setLoading(true);
        
        const formData = {};
        ['bkash', 'nagad', 'rocket'].forEach(method => {
            const enabledCheckbox = document.getElementById(`${method}_enabled`);
            const accountInput = document.getElementById(`${method}_account`);
            
            formData[`${method}_enabled`] = enabledCheckbox?.checked || false;
            formData[`${method}_account`] = accountInput?.value || '';
        });
        
        try {
            const response = await this.apiRequest('/profile/api/wallet-settings/', 'POST', formData);
            
            if (response.success) {
                this.showAlert('success', 'Wallet settings saved!');
                this.wallet = { ...this.wallet, ...formData };
            } else {
                this.showAlert('error', response.error || 'Failed to save settings');
                this.displayFieldErrors(response.errors);
            }
        } catch (error) {
            console.error('Wallet save error:', error);
            this.showAlert('error', 'Network error. Please try again.');
        } finally {
            this.setLoading(false);
        }
    }
    
    deleteAccount() {
        if (confirm('⚠️ This action cannot be undone! Are you absolutely sure you want to delete your account?')) {
            if (confirm('Final confirmation: Delete your DeltaCrown account permanently?')) {
                this.showAlert('info', 'Account deletion requires admin approval. Please contact support@deltacrown.com');
            }
        }
    }
    
    // UI Helper Methods
    setLoading(isLoading) {
        this.loading = isLoading;
        
        // Update all submit buttons
        const submitButtons = document.querySelectorAll('button[type="submit"]');
        submitButtons.forEach(btn => {
            btn.disabled = isLoading;
            
            const normalText = btn.querySelector('.btn-text');
            const loadingText = btn.querySelector('.btn-loading');
            
            if (normalText && loadingText) {
                if (isLoading) {
                    normalText.style.display = 'none';
                    loadingText.style.display = 'inline';
                } else {
                    normalText.style.display = 'inline';
                    loadingText.style.display = 'none';
                }
            }
        });
    }
    
    showAlert(type, message) {
        this.alert = {
            show: true,
            type,
            message,
            icon: type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'
        };
        
        if (this.alertContainer) {
            this.alertContainer.className = `alert alert-${type}`;
            this.alertContainer.innerHTML = `
                <span class="alert-icon">${this.alert.icon}</span>
                <span class="alert-message">${message}</span>
            `;
            this.alertContainer.style.display = 'flex';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                this.alertContainer.style.display = 'none';
            }, 5000);
        }
    }
    
    displayFieldErrors(errors) {
        if (!errors) return;
        
        // Clear previous errors
        document.querySelectorAll('.field-error').forEach(el => el.remove());
        
        // Display new errors
        Object.keys(errors).forEach(fieldName => {
            const field = document.getElementById(fieldName);
            if (field) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'field-error text-red-500 text-sm mt-1';
                errorDiv.textContent = errors[fieldName];
                field.parentElement.appendChild(errorDiv);
            }
        });
    }
}

// Initialize controller when page loads
// Make it global for debugging
window.settingsController = null;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.settingsController = new SettingsController();
    });
} else {
    window.settingsController = new SettingsController();
}
