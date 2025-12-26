/**
 * DeltaCrown User Profile Settings - Production Grade 2025
 * Schema-Driven, Modern, Esports-Ready
 */

// Toast Notification System
const Toast = {
    show: function(message, type = 'success') {
        const toastContainer = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast px-6 py-4 rounded-lg shadow-xl flex items-center gap-3 ${
            type === 'success' ? 'bg-green-600' : 
            type === 'error' ? 'bg-red-600' : 
            type === 'warning' ? 'bg-yellow-600' : 
            'bg-indigo-600'
        }`;
        
        const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️';
        toast.innerHTML = `
            <span class="text-2xl">${icon}</span>
            <p class="text-white font-medium">${message}</p>
        `;
        
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
};

// Section Navigation
document.addEventListener('DOMContentLoaded', function() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.settings-section');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Update nav state
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            // Update section visibility
            const targetSection = this.getAttribute('data-section');
            sections.forEach(section => {
                section.classList.remove('active');
                if (section.id === `${targetSection}-section`) {
                    section.classList.add('active');
                }
            });
        });
    });
});

// Media Upload Handling with Live Preview
(function() {
    const bannerUpload = document.getElementById('banner-upload');
    const avatarUpload = document.getElementById('avatar-upload');
    const bannerPreview = document.getElementById('banner-preview-img');
    const avatarPreview = document.getElementById('avatar-preview-img');
    const bannerContainer = document.getElementById('banner-preview');
    const avatarContainer = document.getElementById('avatar-preview');
    
    // Banner Upload
    bannerUpload?.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Validate file size
        if (file.size > 10 * 1024 * 1024) {
            Toast.show('Banner must be under 10MB', 'error');
            return;
        }
        
        // Validate file type
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
            Toast.show('Banner must be JPEG, PNG, or WebP', 'error');
            return;
        }
        
        // Show live preview
        const reader = new FileReader();
        reader.onload = function(event) {
            if (bannerPreview) {
                bannerPreview.src = event.target.result;
            } else {
                bannerContainer.innerHTML = `<img src="${event.target.result}" alt="Banner Preview" class="w-full h-full object-cover" id="banner-preview-img">`;
            }
        };
        reader.readAsDataURL(file);
        
        // Upload to server
        await uploadMedia(file, 'banner');
    });
    
    // Avatar Upload
    avatarUpload?.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Validate file size
        if (file.size > 5 * 1024 * 1024) {
            Toast.show('Avatar must be under 5MB', 'error');
            return;
        }
        
        // Validate file type
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
            Toast.show('Avatar must be JPEG, PNG, or WebP', 'error');
            return;
        }
        
        // Show live preview
        const reader = new FileReader();
        reader.onload = function(event) {
            if (avatarPreview) {
                avatarPreview.src = event.target.result;
            } else {
                avatarContainer.innerHTML = `<img src="${event.target.result}" alt="Avatar Preview" class="w-full h-full object-cover" id="avatar-preview-img">`;
            }
        };
        reader.readAsDataURL(file);
        
        // Upload to server
        await uploadMedia(file, 'avatar');
    });
    
    // Remove Banner
    document.getElementById('remove-banner')?.addEventListener('click', async function() {
        if (!confirm('Are you sure you want to remove your banner?')) return;
        await removeMedia('banner');
    });
    
    // Remove Avatar
    document.getElementById('remove-avatar')?.addEventListener('click', async function() {
        if (!confirm('Are you sure you want to remove your avatar?')) return;
        await removeMedia('avatar');
    });
    
    // Upload Media Helper
    async function uploadMedia(file, mediaType) {
        const formData = new FormData();
        formData.append('media_type', mediaType);
        formData.append('file', file);
        
        try {
            const response = await fetch('/profile/settings/upload-media/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show(`${mediaType.charAt(0).toUpperCase() + mediaType.slice(1)} uploaded successfully!`, 'success');
            } else {
                Toast.show(data.error || 'Upload failed', 'error');
            }
        } catch (error) {
            Toast.show('Network error during upload', 'error');
            console.error('Upload error:', error);
        }
    }
    
    // Remove Media Helper
    async function removeMedia(mediaType) {
        try {
            const response = await fetch('/profile/settings/remove-media/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({ media_type: mediaType })
            });
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show(`${mediaType.charAt(0).toUpperCase() + mediaType.slice(1)} removed successfully!`, 'success');
                
                // Reset preview
                if (mediaType === 'banner') {
                    document.getElementById('banner-preview').innerHTML = `
                        <div class="flex items-center justify-center h-full text-slate-500">
                            <span class="text-4xl">🖼️</span>
                            <p class="ml-3">No banner set</p>
                        </div>
                    `;
                } else {
                    document.getElementById('avatar-preview').innerHTML = `
                        <div class="flex items-center justify-center h-full text-slate-500 text-4xl">
                            👤
                        </div>
                    `;
                }
            } else {
                Toast.show(data.error || 'Removal failed', 'error');
            }
        } catch (error) {
            Toast.show('Network error during removal', 'error');
            console.error('Remove error:', error);
        }
    }
})();

// Game Passport Modal - Schema-Driven Dynamic Fields
(function() {
    const modal = document.getElementById('passport-modal');
    const openBtn = document.getElementById('add-passport-btn');
    const closeButtons = document.querySelectorAll('.modal-close');
    const gameSelect = document.getElementById('passport-game-select');
    const identityFieldsContainer = document.getElementById('passport-identity-fields');
    const passportForm = document.getElementById('passport-form');
    
    // Open Modal
    openBtn?.addEventListener('click', function() {
        modal?.classList.remove('hidden');
    });
    
    // Close Modal
    closeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            modal?.classList.add('hidden');
            passportForm?.reset();
            identityFieldsContainer.innerHTML = '';
        });
    });
    
    // Close on backdrop click
    modal?.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.classList.add('hidden');
            passportForm?.reset();
            identityFieldsContainer.innerHTML = '';
        }
    });
    
    // Game Selection -> Generate Schema-Driven Fields
    gameSelect?.addEventListener('change', function() {
        const gameSlug = this.value;
        if (!gameSlug) {
            identityFieldsContainer.innerHTML = '';
            return;
        }
        
        // Use injected GAME_SCHEMAS from template (game_schemas_json)
        const gameSchemas = typeof GAME_SCHEMAS !== 'undefined' ? GAME_SCHEMAS : window.gameSchemas || {};
        const schema = gameSchemas[gameSlug];
        
        if (!schema) {
            identityFieldsContainer.innerHTML = '<p class="text-red-400">Schema not found for this game</p>';
            return;
        }
        
        generateSchemaFields(schema, gameSlug);
    });
    
    // Generate Fields Based on Game Schema from Backend
    function generateSchemaFields(schema, gameSlug) {
        identityFieldsContainer.innerHTML = '';
        
        const fields = schema.fields || [];
        
        if (fields.length === 0) {
            identityFieldsContainer.innerHTML = '<p class="text-gray-400">No identity fields configured for this game</p>';
            return;
        }
        
        fields.forEach(fieldConfig => {
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'schema-field';
            
            let inputHTML = '';
            const fieldName = fieldConfig.field_name;
            const displayName = fieldConfig.display_name;
            const fieldType = fieldConfig.field_type || 'text';
            const isRequired = fieldConfig.is_required || false;
            const placeholder = fieldConfig.placeholder || '';
            const helpText = fieldConfig.help_text || '';
            const validationRegex = fieldConfig.validation_regex || '';
            
            // Map field types to HTML inputs
            if (fieldType === 'select' && fieldConfig.choices) {
                const choices = JSON.parse(fieldConfig.choices || '[]');
                inputHTML = `
                    <select 
                        name="${fieldName}" 
                        id="passport-${fieldName}" 
                        ${isRequired ? 'required' : ''}
                        class="form-select">
                        <option value="">Select ${displayName}...</option>
                        ${choices.map(choice => `<option value="${choice}">${choice}</option>`).join('')}
                    </select>
                `;
            } else {
                const inputType = fieldType === 'number' ? 'text' : 'text'; // Use text for all, validate with pattern
                inputHTML = `
                    <input 
                        type="${inputType}" 
                        name="${fieldName}" 
                        id="passport-${fieldName}" 
                        placeholder="${placeholder}"
                        ${isRequired ? 'required' : ''}
                        ${validationRegex ? `pattern="${validationRegex}"` : ''}
                        class="form-input"
                    >
                `;
            }
            
            fieldDiv.innerHTML = `
                <label for="passport-${fieldName}" class="form-label">
                    ${displayName} ${isRequired ? '<span class="text-red-400">*</span>' : ''}
                </label>
                ${inputHTML}
                ${helpText ? `<p class="text-xs text-gray-400 mt-1">${helpText}</p>` : ''}
            `;
            
            identityFieldsContainer.appendChild(fieldDiv);
        });
        
        // Add platform selector if game has multiple platforms
        if (schema.platforms && schema.platforms.length > 1) {
            const platformDiv = document.createElement('div');
            platformDiv.className = 'schema-field';
            platformDiv.innerHTML = `
                <label for="passport-platform" class="form-label">Platform</label>
                <select name="platform" id="passport-platform" class="form-select">
                    <option value="">Select platform...</option>
                    ${schema.platforms.map(p => `<option value="${p}">${p}</option>`).join('')}
                </select>
                <p class="text-xs text-gray-400 mt-1">Choose your gaming platform for this game</p>
            `;
            identityFieldsContainer.appendChild(platformDiv);
        }
    }
    
    // Form Submission - Create Game Passport
    passportForm?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const gameSlug = formData.get('game');
        
        // Build identity_data from all form fields except 'game'
        const identityData = {};
        for (let [key, value] of formData.entries()) {
            if (key !== 'game' && value) {
                identityData[key] = value;
            }
        }
        
        const payload = {
            game: gameSlug,
            identity_data: identityData
        };
        
        try {
            const response = await fetch('/api/passports/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                Toast.show('Game passport created successfully!', 'success');
                modal?.classList.add('hidden');
                passportForm.reset();
                identityFieldsContainer.innerHTML = '';
                
                // Reload passports list
                setTimeout(() => location.reload(), 1500);
            } else {
                // Show field-level errors if available
                if (result.errors && typeof result.errors === 'object') {
                    Object.entries(result.errors).forEach(([field, message]) => {
                        const fieldInput = document.getElementById(`passport-${field}`);
                        if (fieldInput) {
                            fieldInput.classList.add('border-red-500');
                            const errorMsg = document.createElement('p');
                            errorMsg.className = 'text-red-400 text-xs mt-1';
                            errorMsg.textContent = message;
                            fieldInput.parentElement.appendChild(errorMsg);
                        }
                    });
                    Toast.show('Please fix the errors in the form', 'error');
                } else {
                    Toast.show(result.error || 'Failed to create passport', 'error');
                }
            }
        } catch (error) {
            Toast.show('Network error', 'error');
            console.error('Passport creation error:', error);
        }
    });
})();

// Game Passport Actions (Toggle LFT, Pin, Visibility, Delete)
(function() {
    document.querySelectorAll('.passport-action').forEach(btn => {
        btn.addEventListener('click', async function() {
            const action = this.getAttribute('data-action');
            const passportId = this.getAttribute('data-id');
            
            if (action === 'delete') {
                if (!confirm('Are you sure you want to delete this game passport?')) return;
            }
            
            await handlePassportAction(action, passportId);
        });
    });
    
    document.querySelectorAll('.passport-visibility').forEach(select => {
        select.addEventListener('change', async function() {
            const passportId = this.getAttribute('data-id');
            const visibility = this.value;
            
            await handlePassportVisibility(passportId, visibility);
        });
    });
    
    async function handlePassportAction(action, passportId) {
        const endpoints = {
            'toggle-lft': `/profile/passports/${passportId}/toggle-lft/`,
            'toggle-pin': `/profile/passports/${passportId}/toggle-pin/`,
            'delete': `/profile/passports/${passportId}/delete/`
        };
        
        try {
            const response = await fetch(endpoints[action], {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show(`Passport ${action} successful!`, 'success');
                if (action === 'delete') {
                    setTimeout(() => location.reload(), 1000);
                } else {
                    // Toggle visual state
                    location.reload();
                }
            } else {
                Toast.show(data.error || 'Action failed', 'error');
            }
        } catch (error) {
            Toast.show('Network error', 'error');
            console.error('Passport action error:', error);
        }
    }
    
    async function handlePassportVisibility(passportId, visibility) {
        try {
            const response = await fetch(`/profile/passports/${passportId}/set-visibility/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({ visibility })
            });
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show('Visibility updated!', 'success');
            } else {
                Toast.show(data.error || 'Update failed', 'error');
            }
        } catch (error) {
            Toast.show('Network error', 'error');
            console.error('Visibility update error:', error);
        }
    }
})();

// Social Links - Save with Validation
document.getElementById('save-social-links')?.addEventListener('click', async function() {
    const socialInputs = document.querySelectorAll('[data-platform]');
    const socialLinks = {};
    
    let hasError = false;
    
    socialInputs.forEach(input => {
        const platform = input.getAttribute('data-platform');
        const url = input.value.trim();
        
        if (url) {
            // Validate URL format
            if (!url.startsWith('http://') && !url.startsWith('https://')) {
                Toast.show(`${platform}: URL must start with http:// or https://`, 'error');
                hasError = true;
                return;
            }
            
            socialLinks[platform] = url;
        }
    });
    
    if (hasError) return;
    
    try {
        const response = await fetch('/profile/settings/save-social-links/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify({ social_links: socialLinks })
        });
        
        const data = await response.json();
        
        if (data.success) {
            Toast.show('Social links saved successfully!', 'success');
        } else {
            Toast.show(data.error || 'Save failed', 'error');
        }
    } catch (error) {
        Toast.show('Network error', 'error');
        console.error('Social links save error:', error);
    }
});

// Privacy Presets
(function() {
    const presetCards = document.querySelectorAll('.preset-card');
    const privacyToggles = document.querySelectorAll('[data-field]');
    
    const presets = {
        public: {
            show_real_name: false,
            show_email: false,
            show_bio: true,
            show_passports: true,
            show_tournaments: true,
            show_socials: true
        },
        protected: {
            show_real_name: false,
            show_email: false,
            show_bio: true,
            show_passports: true,
            show_tournaments: false,
            show_socials: true
        },
        private: {
            show_real_name: false,
            show_email: false,
            show_bio: false,
            show_passports: false,
            show_tournaments: false,
            show_socials: false
        }
    };
    
    presetCards.forEach(card => {
        card.addEventListener('click', function() {
            const preset = this.getAttribute('data-preset');
            
            // Update UI
            presetCards.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            
            // Apply preset
            applyPrivacyPreset(presets[preset]);
        });
    });
    
    function applyPrivacyPreset(settings) {
        privacyToggles.forEach(toggle => {
            const field = toggle.getAttribute('data-field');
            if (settings.hasOwnProperty(field)) {
                toggle.checked = settings[field];
            }
        });
        
        Toast.show('Privacy preset applied!', 'info');
    }
    
    // Save Privacy Settings
    document.getElementById('save-privacy-settings')?.addEventListener('click', async function() {
        const settings = {};
        
        privacyToggles.forEach(toggle => {
            const field = toggle.getAttribute('data-field');
            settings[field] = toggle.checked;
        });
        
        try {
            const response = await fetch('/profile/settings/save-privacy/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({ privacy_settings: settings })
            });
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show('Privacy settings saved!', 'success');
            } else {
                Toast.show(data.error || 'Save failed', 'error');
            }
        } catch (error) {
            Toast.show('Network error', 'error');
            console.error('Privacy save error:', error);
        }
    });
})();

// Platform Settings - Save
document.getElementById('save-platform-settings')?.addEventListener('click', async function() {
    const settingsToggles = document.querySelectorAll('#platform-section [data-field]');
    const settings = {};
    
    settingsToggles.forEach(toggle => {
        const field = toggle.getAttribute('data-field');
        settings[field] = toggle.checked;
    });
    
    try {
        const response = await fetch('/profile/settings/save-platform/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify({ platform_settings: settings })
        });
        
        const data = await response.json();
        
        if (data.success) {
            Toast.show('Platform settings saved!', 'success');
        } else {
            Toast.show(data.error || 'Save failed', 'error');
        }
    } catch (error) {
        Toast.show('Network error', 'error');
        console.error('Platform settings save error:', error);
    }
});

console.log('✅ DeltaCrown Settings - Production Grade Loaded');
