/**
 * DeltaCrown Settings - Modern 2025 Design
 * Complete redesign with drag & drop, glassy UI, responsive design
 */

// ========== MODERN TOAST SYSTEM ==========
const ModernToast = {
    container: null,
    
    init() {
        this.container = document.getElementById('toast-container');
    },
    
    show(title, message, type = 'success', duration = 4000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        toast.innerHTML = `
            <div class="toast-icon">${icons[type]}</div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">✕</button>
        `;
        
        this.container.appendChild(toast);
        
        // Auto remove after duration
        setTimeout(() => {
            toast.style.animation = 'toastSlideIn 0.3s reverse';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
};

// ========== NAVIGATION ==========
const Navigation = {
    init() {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = link.dataset.section;
                this.switchSection(section);
                
                // Update active state
                document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            });
        });
    },
    
    switchSection(sectionName) {
        // Hide all sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        
        // Show selected section
        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.classList.add('active');
        }
    }
};

// ========== DRAG & DROP MEDIA UPLOAD ==========
const MediaUpload = {
    init() {
        this.setupBannerUpload();
        this.setupAvatarUpload();
        this.setupRemoveButtons();
    },
    
    setupBannerUpload() {
        const dropZone = document.getElementById('banner-drop-zone');
        const fileInput = document.getElementById('banner-upload');
        const preview = document.getElementById('banner-preview');
        
        // Drag and drop events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-over');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-over');
            });
        });
        
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleBannerUpload(files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleBannerUpload(e.target.files[0]);
            }
        });
    },
    
    setupAvatarUpload() {
        const dropZone = document.getElementById('avatar-drop-zone');
        const fileInput = document.getElementById('avatar-upload');
        const preview = document.getElementById('avatar-preview');
        
        // Drag and drop events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-over');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-over');
            });
        });
        
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleAvatarUpload(files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleAvatarUpload(e.target.files[0]);
            }
        });
    },
    
    async handleBannerUpload(file) {
        // Validate file
        if (!file.type.startsWith('image/')) {
            ModernToast.show('Invalid File', 'Please upload an image file', 'error');
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) { // 10MB
            ModernToast.show('File Too Large', 'Maximum file size is 10MB', 'error');
            return;
        }
        
        // Show preview immediately
        const reader = new FileReader();
        reader.onload = (e) => {
            let preview = document.getElementById('banner-preview');
            if (!preview) {
                preview = document.createElement('img');
                preview.id = 'banner-preview';
                preview.className = 'banner-preview';
                document.getElementById('banner-drop-zone').appendChild(preview);
            }
            preview.src = e.target.result;
        };
        reader.readAsDataURL(file);
        
        // Upload to server
        const formData = new FormData();
        formData.append('media_type', 'banner');
        formData.append('file', file);
        
        try {
            const response = await fetch('/me/settings/media/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                ModernToast.show('Banner Uploaded', 'Your banner has been updated successfully', 'success');
                
                // Add remove button if it doesn't exist
                if (!document.getElementById('remove-banner')) {
                    const btnContainer = document.querySelector('#banner-drop-zone').nextElementSibling;
                    btnContainer.innerHTML = `
                        <button type="button" class="btn btn-primary" onclick="document.getElementById('banner-upload').click()">
                            <span>📤</span>
                            <span>Upload Banner</span>
                        </button>
                        <button type="button" class="btn btn-danger" id="remove-banner">
                            <span>🗑️</span>
                            <span>Remove</span>
                        </button>
                    `;
                    MediaUpload.setupRemoveButtons();
                }
            } else {
                ModernToast.show('Upload Failed', data.error || 'Failed to upload banner', 'error');
            }
        } catch (error) {
            console.error('Banner upload error:', error);
            ModernToast.show('Network Error', 'Failed to connect to server', 'error');
        }
    },
    
    async handleAvatarUpload(file) {
        // Validate file
        if (!file.type.startsWith('image/')) {
            ModernToast.show('Invalid File', 'Please upload an image file', 'error');
            return;
        }
        
        if (file.size > 5 * 1024 * 1024) { // 5MB
            ModernToast.show('File Too Large', 'Maximum file size is 5MB', 'error');
            return;
        }
        
        // Show preview immediately
        const reader = new FileReader();
        reader.onload = (e) => {
            let preview = document.getElementById('avatar-preview');
            if (!preview) {
                preview = document.createElement('img');
                preview.id = 'avatar-preview';
                preview.className = 'avatar-preview';
                document.getElementById('avatar-drop-zone').appendChild(preview);
            }
            preview.src = e.target.result;
        };
        reader.readAsDataURL(file);
        
        // Upload to server
        const formData = new FormData();
        formData.append('media_type', 'avatar');
        formData.append('file', file);
        
        try {
            const response = await fetch('/me/settings/media/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                ModernToast.show('Avatar Uploaded', 'Your profile photo has been updated', 'success');
                
                // Add remove button if it doesn't exist
                const avatarBtns = document.querySelector('.avatar-info').querySelector('div');
                if (!document.getElementById('remove-avatar')) {
                    avatarBtns.innerHTML = `
                        <button type="button" class="btn btn-secondary" onclick="document.getElementById('avatar-upload').click()">
                            Upload Photo
                        </button>
                        <button type="button" class="btn btn-danger" id="remove-avatar" style="padding: 0.75rem 1rem;">
                            🗑️
                        </button>
                    `;
                    MediaUpload.setupRemoveButtons();
                }
            } else {
                ModernToast.show('Upload Failed', data.error || 'Failed to upload avatar', 'error');
            }
        } catch (error) {
            console.error('Avatar upload error:', error);
            ModernToast.show('Network Error', 'Failed to connect to server', 'error');
        }
    },
    
    setupRemoveButtons() {
        const removeBannerBtn = document.getElementById('remove-banner');
        const removeAvatarBtn = document.getElementById('remove-avatar');
        
        if (removeBannerBtn) {
            removeBannerBtn.addEventListener('click', async () => {
                if (!confirm('Remove your banner image?')) return;
                
                try {
                    const response = await fetch('/me/settings/media/remove/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': CSRF_TOKEN
                        },
                        body: JSON.stringify({ media_type: 'banner' })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        ModernToast.show('Banner Removed', 'Your banner has been removed', 'success');
                        
                        // Replace with placeholder
                        const dropZone = document.getElementById('banner-drop-zone');
                        dropZone.innerHTML = `
                            <input type="file" id="banner-upload" accept="image/*" style="display: none;">
                            <div style="height: 100%; display: flex; align-items: center; justify-content: center; background: rgba(30, 41, 59, 0.5);">
                                <div style="text-align: center; color: #64748b;">
                                    <div style="font-size: 4rem; margin-bottom: 1rem;">🖼️</div>
                                    <div style="font-size: 1.125rem; font-weight: 600;">No banner set</div>
                                </div>
                            </div>
                            <div class="upload-overlay" onclick="document.getElementById('banner-upload').click()">
                                <div class="upload-icon">📤</div>
                                <div class="upload-text">Click or drag to upload</div>
                                <div class="upload-hint">1920x480px recommended, max 10MB</div>
                            </div>
                        `;
                        
                        // Remove the remove button
                        removeBannerBtn.remove();
                        
                        // Re-setup upload
                        MediaUpload.setupBannerUpload();
                    } else {
                        ModernToast.show('Remove Failed', data.error || 'Failed to remove banner', 'error');
                    }
                } catch (error) {
                    console.error('Banner remove error:', error);
                    ModernToast.show('Network Error', 'Failed to connect to server', 'error');
                }
            });
        }
        
        if (removeAvatarBtn) {
            removeAvatarBtn.addEventListener('click', async () => {
                if (!confirm('Remove your profile photo?')) return;
                
                try {
                    const response = await fetch('/me/settings/media/remove/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': CSRF_TOKEN
                        },
                        body: JSON.stringify({ media_type: 'avatar' })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        ModernToast.show('Avatar Removed', 'Your profile photo has been removed', 'success');
                        
                        // Replace with placeholder
                        const dropZone = document.getElementById('avatar-drop-zone');
                        dropZone.innerHTML = `
                            <input type="file" id="avatar-upload" accept="image/*" style="display: none;">
                            <div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: rgba(30, 41, 59, 0.5); color: #64748b; font-size: 3rem;">
                                👤
                            </div>
                            <div class="upload-overlay" style="border-radius: 50%;" onclick="document.getElementById('avatar-upload').click()">
                                <div style="font-size: 2rem;">📸</div>
                            </div>
                        `;
                        
                        // Remove the remove button
                        removeAvatarBtn.remove();
                        
                        // Re-setup upload
                        MediaUpload.setupAvatarUpload();
                    } else {
                        ModernToast.show('Remove Failed', data.error || 'Failed to remove avatar', 'error');
                    }
                } catch (error) {
                    console.error('Avatar remove error:', error);
                    ModernToast.show('Network Error', 'Failed to connect to server', 'error');
                }
            });
        }
    }
};

// ========== GAME PASSPORTS (INLINE, NO POPUP) ==========
const GamePassports = {
    init() {
        this.setupGameSelect();
        this.setupPassportForm();
        this.setupToggleButton();
        this.setupDeleteButtons();
    },
    
    setupToggleButton() {
        const toggleBtn = document.getElementById('toggle-passport-form');
        const form = document.getElementById('passport-form');
        const icon = document.getElementById('form-toggle-icon');
        const container = document.getElementById('passport-form-container');
        
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                const isCollapsed = form.style.display === 'none';
                form.style.display = isCollapsed ? 'block' : 'none';
                icon.textContent = isCollapsed ? '▼' : '▲';
                container.classList.toggle('collapsed', !isCollapsed);
            });
        }
    },
    
    setupGameSelect() {
        const select = document.getElementById('passport-game-select');
        if (!select) return;
        
        select.addEventListener('change', (e) => {
            const gameSlug = e.target.value;
            if (!gameSlug) {
                document.getElementById('passport-identity-fields').innerHTML = '';
                document.getElementById('passport-showcase-fields').style.display = 'none';
                return;
            }
            
            const schema = GAME_SCHEMAS[gameSlug];
            if (!schema) {
                ModernToast.show('Error', 'Game schema not found', 'error');
                return;
            }
            
            this.renderIdentityFields(schema.identity_schema);
            document.getElementById('passport-showcase-fields').style.display = 'block';
        });
    },
    
    renderIdentityFields(schema) {
        const container = document.getElementById('passport-identity-fields');
        container.innerHTML = '<h4 style="color: white; margin-bottom: 1rem; font-weight: 600;">Game Identity</h4>';
        
        const grid = document.createElement('div');
        grid.className = 'form-grid';
        
        schema.forEach(field => {
            const formGroup = document.createElement('div');
            formGroup.className = 'form-group';
            
            const label = document.createElement('label');
            label.className = 'form-label';
            label.textContent = field.label + (field.required ? ' *' : '');
            
            const input = document.createElement('input');
            input.type = 'text';
            input.name = field.key;
            input.className = 'form-input';
            input.placeholder = field.placeholder || '';
            if (field.required) input.required = true;
            
            formGroup.appendChild(label);
            formGroup.appendChild(input);
            grid.appendChild(formGroup);
        });
        
        container.appendChild(grid);
    },
    
    setupPassportForm() {
        const form = document.getElementById('passport-form');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const select = document.getElementById('passport-game-select');
            const gameSlug = select.value;
            const gameId = select.selectedOptions[0].dataset.gameId;
            
            if (!gameSlug) {
                ModernToast.show('Error', 'Please select a game', 'error');
                return;
            }
            
            // Collect identity fields
            const identityData = {};
            const identityFields = document.querySelectorAll('#passport-identity-fields input');
            identityFields.forEach(input => {
                if (input.value) {
                    identityData[input.name] = input.value;
                }
            });
            
            // Collect showcase fields
            const showcaseData = {};
            const showcaseFields = document.querySelectorAll('#passport-showcase-fields input');
            showcaseFields.forEach(input => {
                if (input.value) {
                    showcaseData[input.name] = input.value;
                }
            });
            
            const payload = {
                game_id: gameId,
                identity_data: identityData,
                showcase_data: showcaseData
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
                
                const data = await response.json();
                
                if (data.success) {
                    ModernToast.show('Passport Created', `Your ${select.selectedOptions[0].text} passport has been created`, 'success');
                    
                    // Reset form
                    form.reset();
                    document.getElementById('passport-identity-fields').innerHTML = '';
                    document.getElementById('passport-showcase-fields').style.display = 'none';
                    
                    // Reload passports list
                    setTimeout(() => location.reload(), 1500);
                } else {
                    ModernToast.show('Creation Failed', data.error || 'Failed to create passport', 'error');
                }
            } catch (error) {
                console.error('Passport creation error:', error);
                ModernToast.show('Network Error', 'Failed to connect to server', 'error');
            }
        });
    },
    
    setupDeleteButtons() {
        document.querySelectorAll('[data-action="delete"]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const passportId = btn.dataset.passportId;
                
                if (!confirm('Delete this game passport?')) return;
                
                try {
                    const response = await fetch(`/api/passports/${passportId}/delete/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': CSRF_TOKEN
                        }
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        ModernToast.show('Passport Deleted', 'Your passport has been removed', 'success');
                        btn.closest('.passport-card').remove();
                    } else {
                        ModernToast.show('Delete Failed', data.error || 'Failed to delete passport', 'error');
                    }
                } catch (error) {
                    console.error('Passport delete error:', error);
                    ModernToast.show('Network Error', 'Failed to connect to server', 'error');
                }
            });
        });
    }
};

// ========== SOCIAL LINKS ==========
const SocialLinks = {
    init() {
        this.loadLinks();
        document.getElementById('save-social-links').addEventListener('click', () => this.saveLinks());
    },
    
    async loadLinks() {
        try {
            const response = await fetch('/api/social-links/', {
                headers: {
                    'X-CSRFToken': CSRF_TOKEN
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Populate fields
                Object.entries(data.links).forEach(([platform, url]) => {
                    const input = document.querySelector(`[data-platform="${platform}"]`);
                    if (input) input.value = url || '';
                });
            }
        } catch (error) {
            console.error('Load social links error:', error);
        }
    },
    
    async saveLinks() {
        const links = {};
        
        document.querySelectorAll('[data-platform]').forEach(input => {
            const platform = input.dataset.platform;
            const url = input.value.trim();
            if (url) links[platform] = url;
        });
        
        try {
            const response = await fetch('/api/social-links/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': CSRF_TOKEN
                },
                body: JSON.stringify({ links })
            });
            
            const data = await response.json();
            
            if (data.success) {
                ModernToast.show('Links Saved', 'Your social links have been updated', 'success');
            } else {
                ModernToast.show('Save Failed', data.error || 'Failed to save social links', 'error');
            }
        } catch (error) {
            console.error('Save social links error:', error);
            ModernToast.show('Network Error', 'Failed to connect to server', 'error');
        }
    }
};

// ========== PRIVACY SETTINGS ==========
const PrivacySettings = {
    init() {
        this.loadSettings();
        document.getElementById('save-privacy-settings').addEventListener('click', () => this.saveSettings());
    },
    
    async loadSettings() {
        try {
            const response = await fetch('/me/settings/privacy/', {
                headers: {
                    'X-CSRFToken': CSRF_TOKEN
                }
            });
            
            const data = await response.json();
            
            if (data.success && data.settings) {
                // Populate toggles
                Object.entries(data.settings).forEach(([field, value]) => {
                    const toggle = document.querySelector(`[data-field="${field}"]`);
                    if (toggle) toggle.checked = value;
                });
            }
        } catch (error) {
            console.error('Load privacy settings error:', error);
        }
    },
    
    async saveSettings() {
        const settings = {};
        
        document.querySelectorAll('[data-field]').forEach(toggle => {
            const field = toggle.dataset.field;
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
            
            const data = await response.json();
            
            if (data.success) {
                ModernToast.show('Privacy Updated', 'Your privacy settings have been saved', 'success');
            } else {
                ModernToast.show('Save Failed', data.error || 'Failed to save privacy settings', 'error');
            }
        } catch (error) {
            console.error('Save privacy settings error:', error);
            ModernToast.show('Network Error', 'Failed to connect to server', 'error');
        }
    }
};

// ========== PROFILE FORM ==========
const ProfileForm = {
    init() {
        const form = document.querySelector('#profile-section form');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            
            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    ModernToast.show('Profile Updated', 'Your profile information has been saved', 'success');
                } else {
                    ModernToast.show('Update Failed', data.error || 'Failed to update profile', 'error');
                }
            } catch (error) {
                console.error('Profile update error:', error);
                ModernToast.show('Network Error', 'Failed to connect to server', 'error');
            }
        });
    }
};

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', () => {
    ModernToast.init();
    Navigation.init();
    MediaUpload.init();
    GamePassports.init();
    SocialLinks.init();
    PrivacySettings.init();
    ProfileForm.init();
    
    console.log('🚀 DeltaCrown Settings - Modern 2025 Loaded');
});
