/**
 * DeltaCrown Settings Page - Complete Implementation
 * Professional settings management with full backend integration
 */

// ============================================================================
// UTILITY FUNCTIONS & HELPERS
// ============================================================================

const getCookie = (name) => {
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
};

const csrfToken = getCookie('csrftoken');

// ============================================================================
// TOAST NOTIFICATION SYSTEM
// ============================================================================

const Toast = {
    container: null,

    init() {
        this.container = document.getElementById('toast-container');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'fixed top-4 right-4 z-50 space-y-3';
            document.body.appendChild(this.container);
        }
    },

    show(message, type = 'info', duration = 4000) {
        if (!this.container) this.init();

        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };

        const colors = {
            success: 'from-green-900/90 to-emerald-900/90 border-green-500/50',
            error: 'from-red-900/90 to-rose-900/90 border-red-500/50',
            warning: 'from-orange-900/90 to-amber-900/90 border-orange-500/50',
            info: 'from-blue-900/90 to-cyan-900/90 border-blue-500/50'
        };

        const toast = document.createElement('div');
        toast.className = `toast-notification bg-gradient-to-r ${colors[type]} backdrop-blur-xl border-2 rounded-xl p-4 shadow-2xl transform transition-all duration-300 ease-out max-w-md`;
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';

        toast.innerHTML = `
            <div class="flex items-start gap-3">
                <span class="text-2xl flex-shrink-0">${icons[type]}</span>
                <p class="text-white font-medium leading-relaxed flex-1">${message}</p>
                <button onclick="this.parentElement.parentElement.remove()" class="text-white/70 hover:text-white transition-colors">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;

        this.container.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        }, 10);

        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
    },

    success(message) { this.show(message, 'success'); },
    error(message) { this.show(message, 'error'); },
    warning(message) { this.show(message, 'warning'); },
    info(message) { this.show(message, 'info'); }
};

// ============================================================================
// NAVIGATION SYSTEM
// ============================================================================

const Navigation = {
    init() {
        const navItems = document.querySelectorAll('.nav-item');
        const sections = document.querySelectorAll('.content-section');

        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = item.getAttribute('data-section') + '-section';

                // Update active states
                navItems.forEach(nav => nav.classList.remove('active'));
                item.classList.add('active');

                // Show target section
                sections.forEach(section => {
                    section.classList.remove('active');
                    if (section.id === targetId) {
                        section.classList.add('active');
                        // Smooth scroll to top of section
                        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });

                // Update URL hash
                window.location.hash = item.getAttribute('data-section');
            });
        });

        // Handle initial hash
        const hash = window.location.hash.substring(1);
        if (hash) {
            const targetNav = document.querySelector(`[data-section="${hash}"]`);
            if (targetNav) {
                targetNav.click();
            }
        }
    }
};

// ============================================================================
// PROFILE FORM MODULE
// ============================================================================

const ProfileForm = {
    form: null,

    init() {
        this.form = document.getElementById('profile-form');
        if (!this.form) return;

        this.form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Character counter for bio
        const bioTextarea = this.form.querySelector('[name="bio"]');
        if (bioTextarea) {
            const charCount = document.createElement('div');
            charCount.className = 'text-right text-slate-500 text-xs mt-1';
            bioTextarea.parentElement.appendChild(charCount);

            bioTextarea.addEventListener('input', () => {
                const remaining = 500 - bioTextarea.value.length;
                charCount.textContent = `${remaining} characters remaining`;
                charCount.style.color = remaining < 50 ? '#ef4444' : '#64748b';
            });
            bioTextarea.dispatchEvent(new Event('input'));
        }
    },

    async handleSubmit(e) {
        e.preventDefault();

        const formData = new FormData(this.form);
        const data = {
            display_name: formData.get('display_name'),
            country: formData.get('country'),
            bio: formData.get('bio')
        };

        try {
            const response = await fetch('/me/settings/basic/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                Toast.success('Profile updated successfully! 🎉');
            } else {
                Toast.error(result.error || 'Failed to update profile');
            }
        } catch (error) {
            console.error('Profile update error:', error);
            Toast.error('Network error. Please try again.');
        }
    }
};

// ============================================================================
// MEDIA UPLOAD MODULE
// ============================================================================

const MediaUpload = {
    init() {
        this.initBannerUpload();
        this.initAvatarUpload();
        this.initRemoveButtons();
    },

    initBannerUpload() {
        const dropZone = document.getElementById('banner-drop-zone');
        const fileInput = document.getElementById('banner-input');
        if (!dropZone || !fileInput) return;

        this.setupDropZone(dropZone, fileInput, 'banner', 10 * 1024 * 1024); // 10MB
    },

    initAvatarUpload() {
        const dropZone = document.getElementById('avatar-drop-zone');
        const fileInput = document.getElementById('avatar-input');
        if (!dropZone || !fileInput) return;

        this.setupDropZone(dropZone, fileInput, 'avatar', 5 * 1024 * 1024); // 5MB
    },

    setupDropZone(dropZone, fileInput, type, maxSize) {
        // Click to upload
        dropZone.addEventListener('click', (e) => {
            if (!e.target.closest('button')) {
                fileInput.click();
            }
        });

        // Drag & Drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.borderColor = '#3b82f6';
                dropZone.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.borderColor = '';
                dropZone.style.backgroundColor = '';
            });
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFile(files[0], type, maxSize);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFile(e.target.files[0], type, maxSize);
            }
        });
    },

    handleFile(file, type, maxSize) {
        // Validate file type
        if (!file.type.startsWith('image/')) {
            Toast.error('Please upload an image file');
            return;
        }

        // Validate file size
        if (file.size > maxSize) {
            const maxMB = maxSize / (1024 * 1024);
            Toast.error(`File size must be less than ${maxMB}MB`);
            return;
        }

        this.uploadFile(file, type);
    },

    async uploadFile(file, type) {
        const formData = new FormData();
        formData.append(type, file);

        try {
            Toast.info(`Uploading ${type}...`);

            const response = await fetch('/me/settings/media/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                Toast.success(`${type === 'banner' ? 'Banner' : 'Avatar'} updated! 🎨`);
                
                // Update preview
                if (type === 'banner' && result.banner_url) {
                    const bannerPreview = document.querySelector('#banner-drop-zone img');
                    if (bannerPreview) {
                        bannerPreview.src = result.banner_url;
                    }
                } else if (type === 'avatar' && result.avatar_url) {
                    const avatarPreview = document.querySelector('#avatar-drop-zone img');
                    if (avatarPreview) {
                        avatarPreview.src = result.avatar_url;
                    }
                }
            } else {
                Toast.error(result.error || `Failed to upload ${type}`);
            }
        } catch (error) {
            console.error('Upload error:', error);
            Toast.error('Upload failed. Please try again.');
        }
    },

    initRemoveButtons() {
        document.querySelectorAll('[data-remove-media]').forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const mediaType = button.getAttribute('data-remove-media');
                this.removeMedia(mediaType);
            });
        });
    },

    async removeMedia(type) {
        if (!confirm(`Are you sure you want to remove your ${type}?`)) return;

        try {
            const response = await fetch('/me/settings/media/remove/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ type })
            });

            const result = await response.json();

            if (response.ok) {
                Toast.success(`${type === 'banner' ? 'Banner' : 'Avatar'} removed`);
                location.reload(); // Reload to show default image
            } else {
                Toast.error(result.error || 'Failed to remove media');
            }
        } catch (error) {
            console.error('Remove error:', error);
            Toast.error('Failed to remove media');
        }
    }
};

// ============================================================================
// GAME PASSPORTS MODULE (CRITICAL)
// ============================================================================

const GamePassports = {
    games: [],
    modal: null,
    selectedGame: null,

    init() {
        this.modal = document.getElementById('passport-modal');
        if (!this.modal) return;

        // Load games and existing passports
        this.loadGames();
        this.loadPassports();

        // Setup modal controls
        this.setupModalControls();
        this.setupGameSelection();
        this.setupPassportForm();
        this.setupDeleteButtons();
    },

    async loadGames() {
        try {
            const response = await fetch('/api/games/');
            if (response.ok) {
                this.games = await response.json();
                this.populateGameDropdown();
            }
        } catch (error) {
            console.error('Failed to load games:', error);
        }
    },

    populateGameDropdown() {
        const select = document.getElementById('game-select');
        if (!select) return;

        select.innerHTML = '<option value="">Select a game...</option>';
        
        this.games.forEach(game => {
            const option = document.createElement('option');
            option.value = game.id;
            option.textContent = `${game.display_name} (${game.category})`;
            select.appendChild(option);
        });
    },

    setupModalControls() {
        // Open modal - main button
        document.getElementById('add-passport-btn')?.addEventListener('click', () => {
            this.openModal();
        });

        // Open modal - empty state button
        document.getElementById('add-first-passport-btn')?.addEventListener('click', () => {
            this.openModal();
        });

        // Close modal
        document.getElementById('close-modal-btn')?.addEventListener('click', () => {
            this.closeModal();
        });

        document.getElementById('cancel-passport-btn')?.addEventListener('click', () => {
            this.closeModal();
        });

        // Close on overlay click
        this.modal?.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.closeModal();
            }
        });
    },

    openModal() {
        if (this.modal) {
            this.modal.classList.remove('hidden');
            this.modal.style.display = 'flex';
            this.resetForm();
        }
    },

    closeModal() {
        if (this.modal) {
            this.modal.classList.add('hidden');
            this.modal.style.display = 'none';
        }
    },

    setupGameSelection() {
        const select = document.getElementById('game-select');
        if (!select) return;

        select.addEventListener('change', async (e) => {
            const gameId = e.target.value;
            if (!gameId) {
                this.selectedGame = null;
                this.clearGamePreview();
                this.clearDynamicFields();
                return;
            }

            this.selectedGame = this.games.find(g => g.id == gameId);
            if (this.selectedGame) {
                this.updateGamePreview(this.selectedGame);
                await this.loadGameSchema(gameId);
            }
        });
    },

    updateGamePreview(game) {
        const preview = document.getElementById('game-preview');
        if (!preview) return;

        preview.classList.remove('hidden');
        preview.innerHTML = `
            <div class="flex items-center gap-4">
                ${game.logo ? 
                    `<img src="${game.logo}" alt="${game.display_name}" class="w-16 h-16 rounded-lg object-cover">` :
                    '<div class="w-16 h-16 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-2xl">🎮</div>'
                }
                <div>
                    <h4 class="text-white font-bold text-lg">${game.display_name}</h4>
                    <p class="text-slate-400 text-sm">${game.category} • ${game.game_type || 'Competitive'}</p>
                </div>
            </div>
        `;
    },

    clearGamePreview() {
        const preview = document.getElementById('game-preview');
        if (preview) preview.classList.add('hidden');
    },

    async loadGameSchema(gameId) {
        try {
            const response = await fetch(`/api/games/${gameId}/schema/`);
            if (response.ok) {
                const schema = await response.json();
                this.renderDynamicFields(schema.fields);
            }
        } catch (error) {
            console.error('Failed to load game schema:', error);
            Toast.error('Failed to load game fields');
        }
    },

    renderDynamicFields(fields) {
        const container = document.getElementById('dynamic-fields');
        if (!container) return;

        container.innerHTML = '';

        fields.forEach(field => {
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'mb-4';

            const label = document.createElement('label');
            label.className = 'block text-slate-300 font-semibold mb-2';
            label.textContent = field.label + (field.required ? ' *' : '');

            let input;
            if (field.type === 'select' && field.choices) {
                input = document.createElement('select');
                input.className = 'form-input';
                
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = `Select ${field.label}...`;
                input.appendChild(defaultOption);

                field.choices.forEach(choice => {
                    const option = document.createElement('option');
                    option.value = choice.value;
                    option.textContent = choice.label;
                    input.appendChild(option);
                });
            } else if (field.type === 'textarea') {
                input = document.createElement('textarea');
                input.className = 'form-input';
                input.rows = 3;
            } else {
                input = document.createElement('input');
                input.type = field.type || 'text';
                input.className = 'form-input';
            }

            input.name = field.field_name;
            input.required = field.required;
            if (field.placeholder) input.placeholder = field.placeholder;
            if (field.validation) input.pattern = field.validation;
            if (field.immutable) input.readOnly = true;
            if (field.min_length) input.minLength = field.min_length;
            if (field.max_length) input.maxLength = field.max_length;

            fieldDiv.appendChild(label);
            fieldDiv.appendChild(input);

            if (field.help_text) {
                const help = document.createElement('p');
                help.className = 'text-slate-500 text-xs mt-1';
                help.textContent = field.help_text;
                fieldDiv.appendChild(help);
            }

            // Show validation error if pattern is set
            if (field.validation && field.validation_error) {
                input.addEventListener('invalid', () => {
                    input.setCustomValidity(field.validation_error);
                });
                input.addEventListener('input', () => {
                    input.setCustomValidity('');
                });
            }

            container.appendChild(fieldDiv);
        });
    },

    clearDynamicFields() {
        const container = document.getElementById('dynamic-fields');
        if (container) container.innerHTML = '';
    },

    setupPassportForm() {
        const form = document.getElementById('passport-form');
        if (!form) return;

        form.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    async handleSubmit(e) {
        e.preventDefault();

        if (!this.selectedGame) {
            Toast.error('Please select a game');
            return;
        }

        const data = {
            game_id: this.selectedGame.id,
            metadata: {}
        };

        // Collect all dynamic field values
        const dynamicFields = document.querySelectorAll('#dynamic-fields input, #dynamic-fields select, #dynamic-fields textarea');
        dynamicFields.forEach(field => {
            if (field.value.trim()) {
                // Map common field names to backend expected names
                const fieldName = field.name;
                if (fieldName === 'ign' || fieldName === 'in_game_name') {
                    data.ign = field.value.trim();
                } else if (fieldName === 'discriminator' || fieldName === 'tag') {
                    data.discriminator = field.value.trim();
                } else if (fieldName === 'platform') {
                    data.platform = field.value.trim();
                } else if (fieldName === 'region' || fieldName === 'server') {
                    data.metadata.region = field.value.trim();
                } else if (fieldName === 'rank' || fieldName === 'tier') {
                    data.metadata.rank = field.value.trim();
                } else {
                    // Store other fields in metadata
                    data.metadata[fieldName] = field.value.trim();
                }
            }
        });

        // Validate required fields
        if (!data.ign) {
            Toast.error('Please provide your in-game name');
            return;
        }

        try {
            Toast.info('Creating game passport...');

            const response = await fetch('/api/passports/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                Toast.success(`${this.selectedGame.display_name} passport created! 🎮`);
                this.closeModal();
                this.loadPassports(); // Reload passports
            } else {
                Toast.error(result.error || 'Failed to create passport');
            }
        } catch (error) {
            console.error('Passport creation error:', error);
            Toast.error('Failed to create passport');
        }
    },

    resetForm() {
        document.getElementById('passport-form')?.reset();
        this.selectedGame = null;
        this.clearGamePreview();
        this.clearDynamicFields();
    },

    async loadPassports() {
        // This would load existing passports from the backend
        // For now, passports are rendered server-side in the template
    },

    setupDeleteButtons() {
        document.querySelectorAll('[data-delete-passport]').forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                const passportId = button.getAttribute('data-delete-passport');
                this.deletePassport(passportId);
            });
        });
    },

    async deletePassport(passportId) {
        if (!confirm('Are you sure you want to delete this game passport?')) return;

        try {
            const response = await fetch(`/api/passports/${passportId}/delete/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });

            if (response.ok) {
                Toast.success('Passport deleted');
                location.reload();
            } else {
                Toast.error('Failed to delete passport');
            }
        } catch (error) {
            console.error('Delete error:', error);
            Toast.error('Failed to delete passport');
        }
    }
};

// ============================================================================
// SOCIAL LINKS MODULE
// ============================================================================

const SocialLinks = {
    init() {
        const saveBtn = document.getElementById('save-social');
        if (!saveBtn) return;

        saveBtn.addEventListener('click', () => this.save());
        this.load();
    },

    async load() {
        try {
            const response = await fetch('/api/social-links/');
            if (response.ok) {
                const links = await response.json();
                this.populateForm(links);
            }
        } catch (error) {
            console.error('Failed to load social links:', error);
        }
    },

    populateForm(links) {
        const form = document.getElementById('social-form');
        if (!form) return;

        links.forEach(link => {
            const input = form.querySelector(`[name="${link.platform}"]`);
            if (input) {
                input.value = link.handle || link.url || '';
            }
        });
    },

    async save() {
        const form = document.getElementById('social-form');
        if (!form) return;

        const formData = new FormData(form);
        const data = {};

        for (let [key, value] of formData.entries()) {
            if (key !== 'csrfmiddlewaretoken' && value.trim()) {
                data[key] = value.trim();
            }
        }

        try {
            const response = await fetch('/api/social-links/update/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                Toast.success('Social links updated! 🔗');
            } else {
                Toast.error('Failed to update social links');
            }
        } catch (error) {
            console.error('Social links error:', error);
            Toast.error('Failed to save changes');
        }
    }
};

// ============================================================================
// PRIVACY SETTINGS MODULE
// ============================================================================

const Privacy = {
    init() {
        this.setupPresets();
        this.setupToggles();
        this.setupSaveButton();
        this.load();
    },

    setupPresets() {
        document.querySelectorAll('.preset-card').forEach(card => {
            card.addEventListener('click', () => {
                const preset = card.getAttribute('data-preset');
                this.applyPreset(preset);
                
                // Update active state
                document.querySelectorAll('.preset-card').forEach(c => c.classList.remove('active'));
                card.classList.add('active');
            });
        });
    },

    applyPreset(preset) {
        const toggles = {
            public: {
                'privacy-profile': true,
                'privacy-real-name': false,
                'privacy-age': true,
                'privacy-country': true,
                'privacy-passports': true,
                'privacy-matches': true,
                'privacy-tournaments': true,
                'privacy-stats': true,
                'privacy-teams': true,
                'privacy-team-invites': true,
                'privacy-friend-requests': true,
                'privacy-messages': true
            },
            protected: {
                'privacy-profile': true,
                'privacy-real-name': false,
                'privacy-age': false,
                'privacy-country': true,
                'privacy-passports': true,
                'privacy-matches': true,
                'privacy-tournaments': true,
                'privacy-stats': true,
                'privacy-teams': true,
                'privacy-team-invites': true,
                'privacy-friend-requests': true,
                'privacy-messages': false
            },
            private: {
                'privacy-profile': false,
                'privacy-real-name': false,
                'privacy-age': false,
                'privacy-country': false,
                'privacy-passports': false,
                'privacy-matches': false,
                'privacy-tournaments': false,
                'privacy-stats': false,
                'privacy-teams': false,
                'privacy-team-invites': false,
                'privacy-friend-requests': false,
                'privacy-messages': false
            }
        };

        const settings = toggles[preset];
        if (settings) {
            Object.entries(settings).forEach(([id, value]) => {
                const toggle = document.getElementById(id);
                if (toggle) toggle.checked = value;
            });
            Toast.info(`Applied ${preset} preset`);
        }
    },

    setupToggles() {
        // Toggles are already functional via HTML
    },

    setupSaveButton() {
        const saveBtn = document.getElementById('save-privacy');
        if (!saveBtn) return;

        saveBtn.addEventListener('click', () => this.save());
    },

    async load() {
        try {
            const response = await fetch('/me/settings/privacy/');
            if (response.ok) {
                const settings = await response.json();
                this.populateToggles(settings);
            }
        } catch (error) {
            console.error('Failed to load privacy settings:', error);
        }
    },

    populateToggles(settings) {
        Object.entries(settings).forEach(([key, value]) => {
            const toggle = document.getElementById(`privacy-${key.replace(/_/g, '-')}`);
            if (toggle) toggle.checked = value;
        });
    },

    async save() {
        const data = {};
        
        document.querySelectorAll('[id^="privacy-"]').forEach(toggle => {
            const key = toggle.id.replace('privacy-', '').replace(/-/g, '_');
            data[key] = toggle.checked;
        });

        try {
            const response = await fetch('/me/settings/privacy/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                Toast.success('Privacy settings saved! 🔒');
            } else {
                Toast.error('Failed to save privacy settings');
            }
        } catch (error) {
            console.error('Privacy save error:', error);
            Toast.error('Failed to save settings');
        }
    }
};

// ============================================================================
// PLATFORM SETTINGS MODULE
// ============================================================================

const PlatformSettings = {
    init() {
        const form = document.getElementById('platform-form');
        if (!form) return;

        form.addEventListener('submit', (e) => this.handleSubmit(e));
    },

    async handleSubmit(e) {
        e.preventDefault();

        const formData = new FormData(e.target);
        const data = {};

        for (let [key, value] of formData.entries()) {
            if (key !== 'csrfmiddlewaretoken') {
                if (e.target.elements[key].type === 'checkbox') {
                    data[key] = e.target.elements[key].checked;
                } else {
                    data[key] = value;
                }
            }
        }

        try {
            const response = await fetch('/me/settings/platform/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                Toast.success('Platform settings updated! ⚙️');
            } else {
                Toast.error('Failed to update settings');
            }
        } catch (error) {
            console.error('Platform settings error:', error);
            Toast.error('Failed to save changes');
        }
    }
};

// ============================================================================
// SECURITY MODULE
// ============================================================================

const Security = {
    init() {
        this.initPasswordForm();
        this.init2FA();
        this.initSessions();
        this.initLoginHistory();
    },

    initPasswordForm() {
        const form = document.getElementById('password-form');
        if (!form) return;

        form.addEventListener('submit', (e) => this.handlePasswordChange(e));
    },

    async handlePasswordChange(e) {
        e.preventDefault();

        const formData = new FormData(e.target);
        const data = {
            current_password: formData.get('current_password'),
            new_password: formData.get('new_password'),
            confirm_password: formData.get('confirm_password')
        };

        if (data.new_password !== data.confirm_password) {
            Toast.error('Passwords do not match');
            return;
        }

        try {
            const response = await fetch('/me/settings/security/password/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                Toast.success('Password updated successfully! 🔐');
                e.target.reset();
            } else {
                Toast.error(result.error || 'Failed to update password');
            }
        } catch (error) {
            console.error('Password change error:', error);
            Toast.error('Failed to update password');
        }
    },

    init2FA() {
        const enableBtn = document.getElementById('enable-2fa');
        if (!enableBtn) return;

        enableBtn.addEventListener('click', () => {
            Toast.info('2FA setup coming soon...');
            // This would open a modal with QR code for 2FA setup
        });
    },

    initSessions() {
        const refreshBtn = document.getElementById('refresh-sessions');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadSessions());
        }
        
        this.loadSessions();
    },

    async loadSessions() {
        try {
            const response = await fetch('/me/settings/security/sessions/');
            if (response.ok) {
                const sessions = await response.json();
                this.renderSessions(sessions);
            }
        } catch (error) {
            console.error('Failed to load sessions:', error);
        }
    },

    renderSessions(sessions) {
        const container = document.getElementById('sessions-list');
        if (!container || !sessions.length) return;

        // Keep the current session display, append others
        // This would be implemented based on your backend session structure
    },

    initLoginHistory() {
        const viewBtn = document.getElementById('view-full-history');
        if (viewBtn) {
            viewBtn.addEventListener('click', () => {
                Toast.info('Full login history coming soon...');
            });
        }
    }
};

// ============================================================================
// DANGER ZONE MODULE
// ============================================================================

const DangerZone = {
    init() {
        this.initLogoutAll();
        this.initDeleteAccount();
    },

    initLogoutAll() {
        const btn = document.getElementById('logout-all');
        if (!btn) return;

        btn.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to logout from all other devices? You will remain logged in on this device.')) {
                return;
            }

            try {
                const response = await fetch('/me/settings/security/logout-all/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken
                    }
                });

                if (response.ok) {
                    Toast.success('Logged out from all other devices');
                } else {
                    Toast.error('Failed to logout from other devices');
                }
            } catch (error) {
                console.error('Logout all error:', error);
                Toast.error('Failed to logout from other devices');
            }
        });
    },

    initDeleteAccount() {
        const btn = document.getElementById('delete-account');
        if (!btn) return;

        btn.addEventListener('click', async () => {
            // Double confirmation
            if (!confirm('⚠️ WARNING: This will permanently delete your account and all data. This action CANNOT be undone.\n\nAre you absolutely sure?')) {
                return;
            }

            const confirmation = prompt('Type "DELETE" to confirm account deletion:');
            if (confirmation !== 'DELETE') {
                Toast.warning('Account deletion cancelled');
                return;
            }

            try {
                const response = await fetch('/me/settings/danger/delete-account/', {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': csrfToken
                    }
                });

                if (response.ok) {
                    Toast.success('Account deleted. Redirecting...');
                    setTimeout(() => {
                        window.location.href = '/';
                    }, 2000);
                } else {
                    Toast.error('Failed to delete account');
                }
            } catch (error) {
                console.error('Delete account error:', error);
                Toast.error('Failed to delete account');
            }
        });
    }
};

// ============================================================================
// MAIN INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize all modules
    Toast.init();
    Navigation.init();
    ProfileForm.init();
    MediaUpload.init();
    GamePassports.init(); // Critical module
    SocialLinks.init();
    Privacy.init();
    PlatformSettings.init();
    Security.init();
    DangerZone.init();

    console.log('✅ DeltaCrown Settings - All modules initialized');
});
