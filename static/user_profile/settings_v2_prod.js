/**
 * DeltaCrown User Profile Settings - Production Grade 2025  
 * Modern Esports Platform - Gen Z Design
 * Full Stack Implementation with Schema-Driven Forms
 */

// ==================== TOAST NOTIFICATION SYSTEM ====================
const Toast = {
    container: null,
    
    init() {
        if (!this.container) {
            this.container = document.getElementById('toast-container');
            if (!this.container) {
                this.container = document.createElement('div');
                this.container.id = 'toast-container';
                this.container.className = 'fixed top-4 right-4 z-[9999] space-y-2';
                document.body.appendChild(this.container);
            }
        }
    },
    
    show(message, type = 'success') {
        this.init();
        
        const toast = document.createElement('div');
        const bgColor = {
            success: 'bg-gradient-to-r from-green-600 to-emerald-600',
            error: 'bg-gradient-to-r from-red-600 to-rose-600',
            warning: 'bg-gradient-to-r from-yellow-600 to-orange-600',
            info: 'bg-gradient-to-r from-indigo-600 to-purple-600'
        }[type] || 'bg-gradient-to-r from-gray-600 to-gray-700';
        
        const icon = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        }[type] || 'ℹ️';
        
        toast.className = `${bgColor} px-6 py-4 rounded-xl shadow-2xl flex items-center gap-3 transform transition-all duration-300 backdrop-blur-sm border border-white/10`;
        toast.style.animation = 'slideInRight 0.3s ease-out';
        toast.innerHTML = `
            <span class="text-2xl">${icon}</span>
            <p class="text-white font-semibold text-sm">${message}</p>
        `;
        
        this.container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
};

// Add animation keyframes
if (!document.querySelector('#toast-animations')) {
    const style = document.createElement('style');
    style.id = 'toast-animations';
    style.textContent = `
        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(100%); }
            to { opacity: 1; transform: translateX(0); }
        }
    `;
    document.head.appendChild(style);
}

// ==================== SECTION NAVIGATION ====================
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
                    // Smooth scroll to top of section
                    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
            
            // Update URL hash without jumping
            history.pushState(null, null, `#${targetSection}`);
        });
    });
    
    // Handle initial hash
    const hash = window.location.hash.substring(1);
    if (hash) {
        const targetLink = document.querySelector(`[data-section="${hash}"]`);
        if (targetLink) {
            targetLink.click();
        }
    }
});

// ==================== MEDIA UPLOAD HANDLING ====================
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
        
        // Validate file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
            Toast.show('Banner must be under 10MB', 'error');
            this.value = '';
            return;
        }
        
        // Validate file type
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
            Toast.show('Banner must be JPEG, PNG, or WebP', 'error');
            this.value = '';
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
        this.value = '';
    });
    
    // Avatar Upload
    avatarUpload?.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Validate file size (5MB)
        if (file.size > 5 * 1024 * 1024) {
            Toast.show('Avatar must be under 5MB', 'error');
            this.value = '';
            return;
        }
        
        // Validate file type
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
            Toast.show('Avatar must be JPEG, PNG, or WebP', 'error');
            this.value = '';
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
        this.value = '';
    });
    
    // Remove Banner
    document.getElementById('remove-banner')?.addEventListener('click', async function(e) {
        e.stopPropagation();
        if (!confirm('Are you sure you want to remove your banner?')) return;
        await removeMedia('banner');
    });
    
    // Remove Avatar
    document.getElementById('remove-avatar')?.addEventListener('click', async function(e) {
        e.stopPropagation();
        if (!confirm('Are you sure you want to remove your avatar?')) return;
        await removeMedia('avatar');
    });
    
    // Upload Media Helper
    async function uploadMedia(file, mediaType) {
        const formData = new FormData();
        formData.append('media_type', mediaType);
        formData.append('file', file);
        
        try {
            const response = await fetch('/me/settings/media/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: formData
            });
            
            // Check for CSRF errors
            if (response.status === 403) {
                Toast.show('Session expired. Please refresh the page.', 'error');
                return;
            }
            
            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                console.error('Non-JSON response:', text);
                Toast.show('Server error: Expected JSON response', 'error');
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show(`${mediaType.charAt(0).toUpperCase() + mediaType.slice(1)} uploaded successfully!`, 'success');
                
                // Update preview with server URL
                if (data.url) {
                    if (mediaType === 'banner' && bannerPreview) {
                        bannerPreview.src = data.url;
                    } else if (mediaType === 'avatar' && avatarPreview) {
                        avatarPreview.src = data.url;
                    }
                }
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
            const response = await fetch('/me/settings/media/remove/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({ media_type: mediaType })
            });
            
            // Check for CSRF errors
            if (response.status === 403) {
                Toast.show('Session expired. Please refresh the page.', 'error');
                return;
            }
            
            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                console.error('Non-JSON response:', text);
                Toast.show('Server error: Expected JSON response', 'error');
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show(`${mediaType.charAt(0).toUpperCase() + mediaType.slice(1)} removed!`, 'success');
                
                // Clear preview
                if (mediaType === 'banner' && bannerContainer) {
                    bannerContainer.innerHTML = `
                        <div class="flex items-center justify-center h-full text-slate-500">
                            <span class="text-4xl">🖼️</span>
                            <p class="ml-3">No banner set</p>
                        </div>
                    `;
                } else if (mediaType === 'avatar' && avatarContainer) {
                    avatarContainer.innerHTML = `
                        <div class="flex items-center justify-center h-full text-slate-500 text-4xl">
                            👤
                        </div>
                    `;
                }
                
                // Reload page after a short delay to reflect changes
                setTimeout(() => location.reload(), 1000);
            } else {
                Toast.show(data.error || 'Remove failed', 'error');
            }
        } catch (error) {
            Toast.show('Network error', 'error');
            console.error('Remove error:', error);
        }
    }
})();

// ==================== GAME PASSPORT MODAL (SCHEMA-DRIVEN) ====================
(function() {
    const modal = document.getElementById('passport-modal');
    const openBtn = document.getElementById('add-passport-btn');
    const closeBtn = document.querySelectorAll('.modal-close');
    const gameSelect = document.getElementById('passport-game-select');
    const identityFieldsContainer = document.getElementById('passport-identity-fields');
    const passportForm = document.getElementById('passport-form');
    
    // Open modal
    openBtn?.addEventListener('click', function() {
        modal?.classList.remove('hidden');
        modal?.classList.add('flex');
    });
    
    // Close modal
    closeBtn.forEach(btn => {
        btn.addEventListener('click', function() {
            modal?.classList.add('hidden');
            modal?.classList.remove('flex');
            passportForm?.reset();
            identityFieldsContainer.innerHTML = '';
        });
    });
    
    // Close on backdrop click
    modal?.addEventListener('click', function(e) {
        if (e.target === this) {
            this.classList.add('hidden');
            this.classList.remove('flex');
            passportForm?.reset();
            identityFieldsContainer.innerHTML = '';
        }
    });
    
    // Game selection - Generate dynamic fields
    gameSelect?.addEventListener('change', function() {
        const gameSlug = this.value;
        const gameId = this.options[this.selectedIndex]?.getAttribute('data-game-id');
        
        if (!gameSlug || !gameId) {
            identityFieldsContainer.innerHTML = '';
            return;
        }
        
        // Get game schema
        const gameSchema = GAME_SCHEMAS && GAME_SCHEMAS[gameSlug];
        
        if (!gameSchema) {
            console.warn(`No schema found for game: ${gameSlug}`);
            identityFieldsContainer.innerHTML = '<p class="text-red-400">Game schema not found</p>';
            return;
        }
        
        // Generate identity fields from schema
        let fieldsHTML = '';
        const identityFields = gameSchema.identity_fields || [];
        
        identityFields.forEach(field => {
            const isRequired = field.required ? 'required' : '';
            const requiredMark = field.required ? '*' : '(optional)';
            const placeholder = field.placeholder || `Enter your ${field.label.toLowerCase()}`;
            const helpText = field.help_text || '';
            
            fieldsHTML += `
                <div class="schema-field">
                    <label class="block text-sm font-medium text-slate-300 mb-2">
                        ${field.label} ${requiredMark}
                    </label>
                    <input 
                        type="text" 
                        name="${field.name}" 
                        placeholder="${placeholder}"
                        ${isRequired}
                        class="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/50 transition-all"
                        data-field-type="identity"
                    >
                    ${helpText ? `<p class="schema-field-help text-xs text-slate-400 mt-1">${helpText}</p>` : ''}
                </div>
            `;
        });
        
        // Store game_id in hidden field
        fieldsHTML += `<input type="hidden" name="game_id" value="${gameId}">`;
        
        identityFieldsContainer.innerHTML = fieldsHTML;
    });
    
    // Form submission
    passportForm?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        const gameId = formData.get('game_id');
        
        if (!gameId) {
            Toast.show('Please select a game', 'error');
            return;
        }
        
        // Separate identity fields from metadata
        const payload = {
            game_id: parseInt(gameId),
            identity_fields: {},
            metadata: {}
        };
        
        const showcaseFields = ['display_name', 'current_rank', 'peak_rank', 'playstyle'];
        
        for (let [key, value] of formData.entries()) {
            if (key === 'game_id' || key === 'game') continue;
            
            if (value.trim()) {  // Only include non-empty values
                if (showcaseFields.includes(key)) {
                    payload.metadata[key] = value.trim();
                } else {
                    payload.identity_fields[key] = value.trim();
                }
            }
        }
        
        // Validation: Ensure at least one identity field is provided
        if (Object.keys(payload.identity_fields).length === 0) {
            Toast.show('Please fill at least one identity field', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/passports/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify(payload)
            });
            
            // Check for CSRF errors
            if (response.status === 403) {
                Toast.show('Session expired. Please refresh the page.', 'error');
                return;
            }
            
            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                console.error('Non-JSON response:', text);
                Toast.show('Server error: Expected JSON response', 'error');
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show('Game passport created successfully!', 'success');
                modal.classList.add('hidden');
                modal.classList.remove('flex');
                passportForm.reset();
                identityFieldsContainer.innerHTML = '';
                
                // Reload page to show new passport
                setTimeout(() => location.reload(), 1000);
            } else {
                Toast.show(data.error || 'Failed to create passport', 'error');
            }
        } catch (error) {
            Toast.show('Network error', 'error');
            console.error('Passport creation error:', error);
        }
    });
    
    // Passport Actions (Toggle LFT, Visibility, Pin, Delete)
    document.addEventListener('click', async function(e) {
        const target = e.target.closest('[data-action]');
        if (!target) return;
        
        const action = target.getAttribute('data-action');
        const passportId = target.getAttribute('data-passport-id');
        
        if (!passportId) return;
        
        if (action === 'toggle-lft') {
            await handlePassportToggleLFT(passportId);
        } else if (action === 'set-visibility') {
            const visibility = target.value;
            await handlePassportVisibility(passportId, visibility);
        } else if (action === 'pin') {
            await handlePassportPin(passportId);
        } else if (action === 'delete') {
            if (confirm('Are you sure you want to delete this game passport?')) {
                await handlePassportDelete(passportId);
            }
        }
    });
    
    async function handlePassportToggleLFT(passportId) {
        try {
            const response = await fetch(`/api/passports/toggle-lft/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({ passport_id: passportId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show('LFT status updated!', 'success');
                setTimeout(() => location.reload(), 500);
            } else {
                Toast.show(data.error || 'Update failed', 'error');
            }
        } catch (error) {
            Toast.show('Network error', 'error');
            console.error('LFT toggle error:', error);
        }
    }
    
    async function handlePassportVisibility(passportId, visibility) {
        try {
            const response = await fetch(`/api/passports/set-visibility/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({ passport_id: passportId, visibility })
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
    
    async function handlePassportPin(passportId) {
        try {
            const response = await fetch(`/api/passports/pin/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({ passport_id: passportId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show('Passport pinned!', 'success');
                setTimeout(() => location.reload(), 500);
            } else {
                Toast.show(data.error || 'Pin failed', 'error');
            }
        } catch (error) {
            Toast.show('Network error', 'error');
            console.error('Pin error:', error);
        }
    }
    
    async function handlePassportDelete(passportId) {
        try {
            const response = await fetch(`/api/passports/${passportId}/delete/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show('Passport deleted!', 'success');
                setTimeout(() => location.reload(), 500);
            } else {
                Toast.show(data.error || 'Delete failed', 'error');
            }
        } catch (error) {
            Toast.show('Network error', 'error');
            console.error('Delete error:', error);
        }
    }
})();

// ==================== SOCIAL LINKS ====================
document.getElementById('save-social-links')?.addEventListener('click', async function() {
    const socialInputs = document.querySelectorAll('[data-platform]');
    const socialLinks = {};
    const primaryLinkRadio = document.querySelector('input[name="primary_link"]:checked');
    
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
        const response = await fetch('/api/social-links/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            body: JSON.stringify({ 
                social_links: socialLinks,
                primary_link: primaryLinkRadio?.value || null
            })
        });
        
        // Check for CSRF errors
        if (response.status === 403) {
            Toast.show('Session expired. Please refresh the page.', 'error');
            return;
        }
        
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Non-JSON response:', text);
            Toast.show('Server error: Expected JSON response', 'error');
            return;
        }
        
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

// ==================== PRIVACY SETTINGS ====================
(function() {
    const presetCards = document.querySelectorAll('.preset-card');
    const privacyToggles = document.querySelectorAll('#privacy-section [data-field]');
    
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
            const response = await fetch('/me/settings/privacy/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({ privacy_settings: settings })
            });
            
            // Check for CSRF errors
            if (response.status === 403) {
                Toast.show('Session expired. Please refresh the page.', 'error');
                return;
            }
            
            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                console.error('Non-JSON response:', text);
                Toast.show('Server error: Expected JSON response', 'error');
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                Toast.show('Privacy settings saved successfully!', 'success');
            } else {
                Toast.show(data.error || 'Save failed', 'error');
            }
        } catch (error) {
            Toast.show('Network error', 'error');
            console.error('Privacy save error:', error);
        }
    });
})();

console.log('✅ DeltaCrown Settings V2 - Production Grade Loaded');
