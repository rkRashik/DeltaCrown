/**
 * UP-UI-REBIRTH-01: Settings Hub Interactions
 * Vanilla JavaScript for settings navigation and forms
 */

(function() {
    'use strict';
    
    // ========== API CLIENT ==========
    
    async function apiFetch(url, options = {}) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        
        const config = {
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                ...options.headers
            },
            credentials: 'same-origin',
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `Request failed with status ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }
    
    async function saveBasicInfo(formData) {
        // Backend expects JSON, not FormData
        const data = Object.fromEntries(formData.entries());
        return await apiFetch('/me/settings/basic/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    }
    
    async function saveSocialLinks(formData) {
        // Backend expects JSON, not FormData
        const data = Object.fromEntries(formData.entries());
        return await apiFetch('/me/settings/social/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
    }
    
    async function uploadMedia(formData) {
        return await apiFetch('/me/settings/media/', {
            method: 'POST',
            body: formData
        });
    }
    
    async function removeMedia(mediaType) {
        return await apiFetch('/me/settings/media/remove/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ media_type: mediaType })
        });
    }
    
    async function getPrivacySettings() {
        return await apiFetch('/me/settings/privacy/', {
            method: 'GET'
        });
    }
    
    async function savePrivacySettings(settings) {
        return await apiFetch('/me/settings/privacy/save/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
    }
    
    // ========== SECTION NAVIGATION ==========
    
    function initSectionNav() {
        const navItems = document.querySelectorAll('.settings-nav-item');
        const sections = document.querySelectorAll('.settings-section');
        
        navItems.forEach(item => {
            item.addEventListener('click', function() {
                const sectionId = this.getAttribute('data-section');
                
                // Update nav active state
                navItems.forEach(nav => nav.classList.remove('active'));
                this.classList.add('active');
                
                // Show corresponding section
                sections.forEach(section => {
                    section.classList.remove('active');
                    if (section.id === `section-${sectionId}`) {
                        section.classList.add('active');
                    }
                });
                
                // Update URL hash
                window.history.pushState(null, null, `#${sectionId}`);
            });
        });
        
        // Handle direct hash navigation
        const hash = window.location.hash.substring(1);
        if (hash) {
            const navItem = document.querySelector(`[data-section="${hash}"]`);
            if (navItem) {
                navItem.click();
            }
        }
    }
    
    // ========== TOGGLE SWITCHES ==========
    
    function initToggleSwitches() {
        const toggles = document.querySelectorAll('.toggle-switch');
        
        toggles.forEach(toggle => {
            toggle.addEventListener('click', async function() {
                const setting = this.getAttribute('data-toggle');
                const wasActive = this.classList.contains('active');
                const newValue = !wasActive;
                
                // Optimistic UI update
                this.classList.toggle('active');
                
                try {
                    await savePrivacySettings({ [setting]: newValue });
                    showToast(`Setting ${newValue ? 'enabled' : 'disabled'}`);
                } catch (error) {
                    // Rollback on failure
                    this.classList.toggle('active');
                    showToast(error.message || 'Failed to update setting', 'error');
                }
            });
        });
    }
    
    // ========== FORM VALIDATION ==========
    
    function initFormValidation() {
        const forms = document.querySelectorAll('form');
        
        forms.forEach(form => {
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                const submitBtn = this.querySelector('button[type="submit"]');
                const originalText = submitBtn?.textContent || 'Save';
                
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Saving...';
                }
                
                try {
                    let result;
                    const formId = this.id;
                    
                    // Route to appropriate API based on form ID
                    if (formId === 'basicInfoForm' || this.classList.contains('basic-info-form')) {
                        result = await saveBasicInfo(formData);
                    } else if (formId === 'socialLinksForm' || this.classList.contains('social-links-form')) {
                        result = await saveSocialLinks(formData);
                    } else {
                        // Generic form handler
                        const action = this.getAttribute('action') || window.location.href;
                        result = await apiFetch(action, {
                            method: 'POST',
                            body: formData
                        });
                    }
                    
                    showToast(result.message || 'Settings saved successfully!');
                    clearUnsavedIndicator(); // Clear dirty flag on success
                    
                    // Phase 5B Workstream 5: Show "View Profile" button after save
                    showViewProfileButton();
                } catch (error) {
                    showToast(error.message || 'Failed to save settings', 'error');
                    // Keep dirty flag on failure
                } finally {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = originalText;
                    }
                }
            });
        });
        
        // Real-time validation
        const inputs = document.querySelectorAll('.form-input');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.hasAttribute('required') && !this.value.trim()) {
                    this.style.borderColor = 'rgb(239, 68, 68)';
                } else {
                    this.style.borderColor = 'rgba(255, 255, 255, 0.05)';
                }
            });
        });
    }
    
    // ========== UTILITIES ==========
    
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-4 rounded-xl text-white font-semibold shadow-2xl z-50 ${
            type === 'error' ? 'bg-red-600' : 'bg-emerald-600'
        }`;
        toast.textContent = message;
        toast.style.animation = 'slideInUp 0.3s ease-out';
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutDown 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // ========== INITIALIZATION ==========
    
    async function loadPrivacySettings() {
        try {
            const settings = await getPrivacySettings();
            
            // Set toggle states based on loaded settings
            Object.keys(settings).forEach(key => {
                const toggle = document.querySelector(`[data-toggle="${key}"]`);
                if (toggle) {
                    if (settings[key]) {
                        toggle.classList.add('active');
                    } else {
                        toggle.classList.remove('active');
                    }
                }
            });
            
            console.log('Privacy settings loaded');
        } catch (error) {
            console.error('Failed to load privacy settings:', error);
        }
    }
    
    function initMediaUpload() {
        const avatarInput = document.getElementById('avatarInput');
        const bannerInput = document.getElementById('bannerInput');
        
        async function handleMediaUpload(input, mediaType) {
            const file = input.files[0];
            if (!file) return;
            
            const formData = new FormData();
            formData.append('media_type', mediaType);
            formData.append('file', file);
            
            try {
                const result = await uploadMedia(formData);
                
                // Update preview
                const previewImg = document.getElementById(`${mediaType}Preview`);
                if (previewImg) {
                    previewImg.src = result.preview_url || result.url;
                }
                
                showToast(`${mediaType === 'avatar' ? 'Avatar' : 'Banner'} updated successfully!`);
            } catch (error) {
                showToast(error.message || 'Failed to upload image', 'error');
            }
        }
        
        if (avatarInput) {
            avatarInput.addEventListener('change', () => handleMediaUpload(avatarInput, 'avatar'));
        }
        
        if (bannerInput) {
            bannerInput.addEventListener('change', () => handleMediaUpload(bannerInput, 'banner'));
        }
    }
    
    // ========== UNSAVED CHANGES WARNING ==========
    
    let isDirty = false;
    
    function initUnsavedWarning() {
        // Track changes to all form inputs
        const inputs = document.querySelectorAll('.form-input, .form-textarea, .form-select, input[type="text"], input[type="email"], input[type="tel"], textarea, select');
        
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                if (!isDirty) {
                    isDirty = true;
                    showUnsavedIndicator();
                }
            });
        });
        
        // Warn before leaving page
        window.addEventListener('beforeunload', (e) => {
            if (isDirty) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
                return e.returnValue;
            }
        });
    }
    
    function showUnsavedIndicator() {
        const indicator = document.getElementById('unsaved-indicator');
        if (indicator) {
            indicator.classList.remove('hidden');
            indicator.innerHTML = '<span class="inline-block w-2 h-2 bg-amber-500 rounded-full mr-2 animate-pulse"></span>Unsaved changes';
        } else {
            // Create indicator if it doesn't exist
            const header = document.querySelector('.settings-header');
            if (header) {
                const newIndicator = document.createElement('div');
                newIndicator.id = 'unsaved-indicator';
                newIndicator.className = 'text-sm text-amber-400 font-semibold flex items-center';
                newIndicator.innerHTML = '<span class="inline-block w-2 h-2 bg-amber-500 rounded-full mr-2 animate-pulse"></span>Unsaved changes';
                header.appendChild(newIndicator);
            }
        }
    }
    
    function clearUnsavedIndicator() {
        isDirty = false;
        const indicator = document.getElementById('unsaved-indicator');
        if (indicator) {
            indicator.classList.add('hidden');
        }
    }
    
    // ========== VIEW PROFILE BUTTON (Phase 5B Workstream 5) ==========
    function showViewProfileButton() {
        // Check if button already exists
        let viewProfileBtn = document.getElementById('view-profile-btn');
        if (viewProfileBtn) {
            viewProfileBtn.classList.remove('hidden');
            return;
        }
        
        // Get username from settings-wrapper data attribute
        const settingsWrapper = document.querySelector('.settings-wrapper');
        const username = settingsWrapper?.dataset.username;
        
        if (!username) {
            console.warn('Could not determine username for View Profile button');
            return;
        }
        
        // Create button
        viewProfileBtn = document.createElement('a');
        viewProfileBtn.id = 'view-profile-btn';
        viewProfileBtn.href = `/@${username}/`;
        viewProfileBtn.className = 'fixed bottom-6 right-6 z-50 px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold rounded-xl shadow-2xl transition-all duration-300 hover:scale-105 flex items-center gap-2';
        viewProfileBtn.innerHTML = `
            <span>View Profile</span>
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6"/>
            </svg>
        `;
        viewProfileBtn.style.animation = 'slideInUp 0.3s ease-out';
        
        document.body.appendChild(viewProfileBtn);
        
        // Auto-hide after 8 seconds
        setTimeout(() => {
            viewProfileBtn.style.animation = 'slideOutDown 0.3s ease-out';
            setTimeout(() => viewProfileBtn.remove(), 300);
        }, 8000);
    }
    
    async function init() {
        const settingsNav = document.querySelector('.settings-nav-item');
        if (!settingsNav) return;
        
        console.log('Initializing Settings Hub (UP-UI-REBIRTH-01)...');
        
        try {
            initSectionNav();
            initToggleSwitches();
            initFormValidation();
            initMediaUpload();
            initUnsavedWarning();
            
            // Load privacy settings on page load
            await loadPrivacySettings();
            
            console.log('✅ Settings Hub initialized with unsaved changes tracking');
        } catch (error) {
            console.error('Error initializing Settings:', error);
        }
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();

// CSS Animations
const style = document.createElement('style');
style.textContent = `
@keyframes slideInUp {
    from { transform: translateY(100%); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}

@keyframes slideOutDown {
    from { transform: translateY(0); opacity: 1; }
    to { transform: translateY(100%); opacity: 0; }
}
`;
document.head.appendChild(style);
