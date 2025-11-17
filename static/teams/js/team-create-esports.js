/**
 * MODERN ESPORTS TEAM CREATE
 * Version: 1.0 - 2025
 * Handles step navigation, validation, uploads, and submission
 */

class EsportsTeamCreate {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {
            name: '',
            tag: '',
            tagline: '',
            description: '',
            game: '',
            region: '',
            logo: null,
            banner: null,
            roster: []
        };
        
        this.init();
    }

    init() {
        this.setupStepNavigation();
        this.setupValidation();
        this.setupGameSelection();
        this.setupRegionSelection();
        this.setupUploadZones();
        this.setupRoster();
        this.setupFormSubmission();
        this.setupErrorHandling();
        // Step 1 is already active in HTML, don't call showStep
    }

    // ==================== ERROR HANDLING ====================
    setupErrorHandling() {
        // Scroll to error banner if it exists on page load
        const errorBanner = document.querySelector('.error-banner');
        if (errorBanner) {
            setTimeout(() => {
                errorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Jump to step with error
                this.jumpToErrorStep(errorBanner);
                
                // Enhanced toast notification
                this.showToast('Please review the errors below', 'error', 5000);
            }, 300);
        }
    }

    jumpToErrorStep(errorBanner) {
        // Check which fields have errors by looking at error messages
        const errorText = errorBanner.textContent.toLowerCase();
        
        if (errorText.includes('team name') || errorText.includes('tag') || 
            errorText.includes('tagline') || errorText.includes('description')) {
            this.showStep(1);
        } else if (errorText.includes('game') || errorText.includes('region') || 
                   errorText.includes('already a member')) {
            this.showStep(2);
        } else if (errorText.includes('logo') || errorText.includes('banner')) {
            this.showStep(3);
        } else if (errorText.includes('roster') || errorText.includes('member')) {
            this.showStep(4);
        }
        // If unclear, stay on step 1 (default)
    }

    // ==================== STEP NAVIGATION ====================
    setupStepNavigation() {
        const nextButtons = document.querySelectorAll('.btn-next');
        const prevButtons = document.querySelectorAll('.btn-prev');

        nextButtons.forEach(btn => {
            btn.addEventListener('click', () => this.nextStep());
        });

        prevButtons.forEach(btn => {
            btn.addEventListener('click', () => this.prevStep());
        });
    }

    showStep(stepNumber) {
        // Hide all steps
        document.querySelectorAll('.form-step').forEach(step => {
            step.classList.remove('active');
        });

        // Show current step using data-step attribute
        const currentStepEl = document.querySelector(`.form-step[data-step="${stepNumber}"]`);
        if (currentStepEl) {
            currentStepEl.classList.add('active');
        }

        // Update progress indicators
        document.querySelectorAll('.step[data-step]').forEach((step) => {
            const stepNum = parseInt(step.getAttribute('data-step'));
            step.classList.remove('active', 'completed');
            
            if (stepNum < stepNumber) {
                step.classList.add('completed');
            } else if (stepNum === stepNumber) {
                step.classList.add('active');
            }
        });

        this.currentStep = stepNumber;
        
        // Scroll to top of form
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    async nextStep() {
        // Validate current step before proceeding
        const isValid = await this.validateCurrentStep();
        
        if (!isValid) {
            this.showToast('Please complete all required fields', 'error');
            return;
        }

        if (this.currentStep < this.totalSteps) {
            this.showStep(this.currentStep + 1);
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.showStep(this.currentStep - 1);
        }
    }

    async validateCurrentStep() {
        switch (this.currentStep) {
            case 1:
                return await this.validateStep1();
            case 2:
                return this.validateStep2();
            case 3:
                return true; // Branding is optional
            case 4:
                return true; // Roster is optional
            default:
                return true;
        }
    }

    // ==================== STEP 1 VALIDATION ====================
    setupValidation() {
        const teamNameInput = document.getElementById('id_name');
        const teamTagInput = document.getElementById('id_tag');

        if (teamNameInput) {
            teamNameInput.addEventListener('input', this.debounce(() => {
                this.validateTeamName(teamNameInput.value);
            }, 500));
        }

        if (teamTagInput) {
            teamTagInput.addEventListener('input', this.debounce(() => {
                this.validateTeamTag(teamTagInput.value);
            }, 500));

            // Auto-uppercase
            teamTagInput.addEventListener('input', (e) => {
                e.target.value = e.target.value.toUpperCase();
            });
        }

        // Character counter for description
        const descInput = document.getElementById('id_description');
        const charCounter = document.getElementById('desc-count');
        
        if (descInput && charCounter) {
            descInput.addEventListener('input', (e) => {
                const length = e.target.value.length;
                charCounter.textContent = length;
                
                if (length > 500) {
                    charCounter.style.color = 'var(--error)';
                } else {
                    charCounter.style.color = 'var(--text-hint)';
                }
            });
        }
    }

    async validateTeamName(name) {
        const input = document.getElementById('id_name');
        const status = document.getElementById('name-status');

        if (!name || name.length < 3) {
            this.setFieldStatus(input, status, 'invalid');
            return false;
        }

        this.setFieldStatus(input, status, 'checking');

        try {
            // Check if name is available
            const response = await fetch('/teams/api/validate-name/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ name })
            });

            const data = await response.json();

            if (data.valid) {
                this.setFieldStatus(input, status, 'valid');
                this.formData.name = name;
                return true;
            } else {
                this.setFieldStatus(input, status, 'invalid');
                return false;
            }
        } catch (error) {
            console.error('Name validation error:', error);
            this.setFieldStatus(input, status, 'valid'); // Fallback to valid on error
            this.formData.name = name;
            return true;
        }
    }

    async validateTeamTag(tag) {
        const input = document.getElementById('id_tag');
        const status = document.getElementById('tag-status');

        if (!tag || tag.length < 2 || tag.length > 6) {
            this.setFieldStatus(input, status, 'invalid');
            return false;
        }

        this.setFieldStatus(input, status, 'checking');

        try {
            // Check if tag is available
            const response = await fetch('/teams/api/validate-tag/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ tag })
            });

            const data = await response.json();

            if (data.valid) {
                this.setFieldStatus(input, status, 'valid');
                this.formData.tag = tag;
                return true;
            } else {
                this.setFieldStatus(input, status, 'invalid');
                return false;
            }
        } catch (error) {
            console.error('Tag validation error:', error);
            this.setFieldStatus(input, status, 'valid'); // Fallback to valid on error
            this.formData.tag = tag;
            return true;
        }
    }

    async validateStep1() {
        const name = document.getElementById('id_name').value.trim();
        const tag = document.getElementById('id_tag').value.trim();
        const tagline = document.getElementById('id_tagline').value.trim();
        const description = document.getElementById('id_description').value.trim();

        if (!name || name.length < 3) {
            this.showToast('Team name must be at least 3 characters', 'error');
            return false;
        }

        if (!tag || tag.length < 2) {
            this.showToast('Team tag must be at least 2 characters', 'error');
            return false;
        }

        // Validate uniqueness
        const nameValid = await this.validateTeamName(name);
        const tagValid = await this.validateTeamTag(tag);

        if (!nameValid || !tagValid) {
            this.showToast('Team name or tag already exists', 'error');
            return false;
        }

        // Store data
        this.formData.tagline = tagline;
        this.formData.description = description;

        return true;
    }

    setFieldStatus(input, statusEl, state) {
        if (!input || !statusEl) return;

        // Remove all status classes
        input.classList.remove('is-valid', 'is-invalid');
        statusEl.classList.remove('checking', 'valid', 'invalid');

        // Add current state
        switch (state) {
            case 'checking':
                statusEl.classList.add('checking');
                statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                break;
            case 'valid':
                input.classList.add('is-valid');
                statusEl.classList.add('valid');
                statusEl.innerHTML = '<i class="fas fa-check-circle"></i>';
                break;
            case 'invalid':
                input.classList.add('is-invalid');
                statusEl.classList.add('invalid');
                statusEl.innerHTML = '<i class="fas fa-times-circle"></i>';
                break;
        }
    }

    // ==================== STEP 2: GAME & REGION ====================
    setupGameSelection() {
        const gameRadios = document.querySelectorAll('input[name="game"]');
        
        gameRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.formData.game = e.target.value;
            });
        });
    }

    setupRegionSelection() {
        const regionRadios = document.querySelectorAll('input[name="region"]');
        
        regionRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.formData.region = e.target.value;
            });
        });
    }

    validateStep2() {
        const game = document.querySelector('input[name="game"]:checked');
        const region = document.querySelector('input[name="region"]:checked');

        if (!game) {
            this.showToast('Please select a game', 'error');
            return false;
        }

        if (!region) {
            this.showToast('Please select a region', 'error');
            return false;
        }

        this.formData.game = game.value;
        this.formData.region = region.value;

        return true;
    }

    // ==================== STEP 3: UPLOADS ====================
    setupUploadZones() {
        this.setupUploadZone('logo-zone', 'id_logo', 'logo-preview', null, 'logo');
        this.setupUploadZone('banner-zone', 'id_banner_image', 'banner-preview', null, 'banner');
    }

    setupUploadZone(zoneId, inputId, previewId, clearBtnId, type) {
        const zone = document.getElementById(zoneId);
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);
        const clearBtn = clearBtnId ? document.querySelector(`[data-clear="${type}"]`) : null;

        if (!zone || !input || !preview) {
            console.warn(`Upload zone setup failed for ${type}: zone=${!!zone}, input=${!!input}, preview=${!!preview}`);
            return;
        }

        // Click to upload
        zone.addEventListener('click', (e) => {
            if (!e.target.closest('.btn-clear') && !e.target.closest('.btn-upload')) {
                input.click();
            }
        });
        
        // Upload button click
        const uploadBtn = zone.parentElement.querySelector('.btn-upload');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                input.click();
            });
        }

        // File input change
        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleFileUpload(file, preview, input, type);
            }
        });

        // Drag and drop
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });

        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');

            const file = e.dataTransfer.files[0];
            if (file) {
                // Set the file to the input so form submission works
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                input.files = dataTransfer.files;
                
                this.handleFileUpload(file, preview, input, type);
            }
        });

        // Clear button
        if (clearBtn) {
            clearBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.clearUpload(input, preview, type);
            });
        }
    }

    handleFileUpload(file, preview, input, type) {
        // Validate file
        if (!file.type.startsWith('image/')) {
            this.showToast('Please upload an image file', 'error');
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            this.showToast('File size must be less than 10MB', 'error');
            return;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            // Create or update preview image
            let img = preview.querySelector('img');
            if (!img) {
                img = document.createElement('img');
                img.style.width = '100%';
                img.style.height = '100%';
                img.style.objectFit = 'cover';
                img.style.borderRadius = '8px';
                preview.innerHTML = '';
                preview.appendChild(img);
            }
            img.src = e.target.result;
            preview.classList.add('active');
            preview.style.display = 'block';
            
            // Hide placeholder
            const placeholder = preview.previousElementSibling;
            if (placeholder && placeholder.classList.contains('upload-placeholder')) {
                placeholder.style.display = 'none';
            }
            
            // Show clear button
            const clearBtn = preview.closest('.upload-card').querySelector('.btn-clear');
            if (clearBtn) {
                clearBtn.style.display = 'inline-flex';
            }
        };
        reader.readAsDataURL(file);

        // Store file
        this.formData[type] = file;
        this.showToast(`${type.charAt(0).toUpperCase() + type.slice(1)} uploaded successfully`, 'success');
    }

    clearUpload(input, preview, type) {
        input.value = '';
        preview.classList.remove('active');
        preview.style.display = 'none';
        preview.innerHTML = '';
        
        // Show placeholder again
        const placeholder = preview.previousElementSibling;
        if (placeholder && placeholder.classList.contains('upload-placeholder')) {
            placeholder.style.display = 'flex';
        }
        
        // Hide clear button
        const clearBtn = preview.closest('.upload-card').querySelector('.btn-clear');
        if (clearBtn) {
            clearBtn.style.display = 'none';
        }
        const img = preview.querySelector('img');
        if (img) {
            img.src = '';
        }
        this.formData[type] = null;
    }

    // ==================== STEP 4: ROSTER ====================
    setupRoster() {
        const addBtn = document.getElementById('add-member-btn');
        const container = document.getElementById('roster-container');

        if (addBtn) {
            addBtn.addEventListener('click', () => this.addMemberCard());
        }

        // Setup template
        const template = document.getElementById('member-template');
        if (template) {
            this.memberTemplate = template.innerHTML;
        }
    }

    addMemberCard() {
        const container = document.getElementById('roster-container');
        if (!container) return;

        const memberCount = container.children.length;
        
        if (memberCount >= 10) {
            this.showToast('Maximum 10 members allowed', 'warning');
            return;
        }

        const memberCard = document.createElement('div');
        memberCard.className = 'member-card';
        memberCard.dataset.memberIndex = memberCount;
        memberCard.innerHTML = this.memberTemplate.replace(/\{index\}/g, memberCount);

        container.appendChild(memberCard);

        // Setup remove button
        const removeBtn = memberCard.querySelector('.btn-remove-member');
        if (removeBtn) {
            removeBtn.addEventListener('click', () => {
                memberCard.remove();
                this.updateRosterData();
            });
        }

        // Setup input listeners
        const identifierInput = memberCard.querySelector('.member-identifier');
        const roleSelect = memberCard.querySelector('.member-role');

        if (identifierInput) {
            identifierInput.addEventListener('change', () => this.updateRosterData());
        }

        if (roleSelect) {
            roleSelect.addEventListener('change', () => this.updateRosterData());
        }

        this.updateRosterData();
    }

    updateRosterData() {
        const members = [];
        const memberCards = document.querySelectorAll('.member-card');

        memberCards.forEach((card, index) => {
            const identifier = card.querySelector('.member-identifier').value.trim();
            const role = card.querySelector('.member-role').value;

            if (identifier) {
                members.push({
                    identifier,
                    role,
                    order: index
                });
            }
        });

        this.formData.roster = members;

        // Update hidden field
        const rosterInput = document.getElementById('roster-data');
        if (rosterInput) {
            rosterInput.value = JSON.stringify(members);
        }
    }

    // ==================== FORM SUBMISSION ====================
    setupFormSubmission() {
        const form = document.getElementById('team-create-form');
        const submitBtn = document.querySelector('.btn-submit');
        const confirmBtn = document.getElementById('confirm-submit');
        const cancelBtn = document.getElementById('cancel-confirm');
        const modalOverlay = document.getElementById('modal-overlay');

        if (submitBtn) {
            submitBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showConfirmationModal();
            });
        }

        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.showConfirmationModal();
            });
        }

        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                this.hideConfirmationModal();
                this.submitForm();
            });
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                this.hideConfirmationModal();
            });
        }

        if (modalOverlay) {
            modalOverlay.addEventListener('click', () => {
                this.hideConfirmationModal();
            });
        }
    }

    showConfirmationModal() {
        // Final validation
        if (!this.formData.name || !this.formData.tag) {
            this.showToast('Please complete required fields', 'error');
            this.showStep(1);
            return;
        }

        if (!this.formData.game || !this.formData.region) {
            this.showToast('Please select game and region', 'error');
            this.showStep(2);
            return;
        }

        // Game names mapping
        const gameChoices = {
            'VALORANT': 'Valorant',
            'CS2': 'Counter-Strike 2',
            'DOTA2': 'Dota 2',
            'MLBB': 'Mobile Legends',
            'PUBG': 'PUBG Mobile',
            'FREEFIRE': 'Free Fire',
            'EFOOTBALL': 'eFootball',
            'FC26': 'FC 26',
            'CODM': 'Call of Duty Mobile'
        };

        // Update preview card
        document.getElementById('preview-name').textContent = this.formData.name;
        document.getElementById('preview-tag').textContent = `[${this.formData.tag}]`;
        document.getElementById('preview-tagline').textContent = this.formData.tagline || 'No tagline set';
        document.getElementById('preview-game').textContent = gameChoices[this.formData.game] || this.formData.game;
        document.getElementById('preview-region').textContent = this.formData.region;
        document.getElementById('preview-roster').textContent = `${this.formData.roster.length + 1} members`;

        // Update logo preview
        const logoPreview = document.getElementById('preview-logo');
        if (this.formData.logo) {
            const logoUrl = URL.createObjectURL(this.formData.logo);
            logoPreview.style.backgroundImage = `url(${logoUrl})`;
            logoPreview.innerHTML = '';
        } else {
            logoPreview.style.backgroundImage = 'none';
            logoPreview.innerHTML = '<i class=\"fas fa-shield-alt\"></i>';
        }

        // Update banner preview
        const bannerPreview = document.querySelector('.team-preview-banner');
        if (this.formData.banner) {
            const bannerUrl = URL.createObjectURL(this.formData.banner);
            bannerPreview.style.backgroundImage = `linear-gradient(135deg, rgba(0, 217, 255, 0.3), rgba(139, 92, 246, 0.3)), url(${bannerUrl})`;
        }

        const modal = document.getElementById('confirmation-modal');
        modal.classList.add('active');
    }

    hideConfirmationModal() {
        const modal = document.getElementById('confirmation-modal');
        modal.classList.remove('active');
    }

    async submitForm() {
        // Final validation
        if (!this.formData.name || !this.formData.tag) {
            this.showToast('Please complete required fields', 'error');
            this.showStep(1);
            return;
        }

        if (!this.formData.game || !this.formData.region) {
            this.showToast('Please select game and region', 'error');
            this.showStep(2);
            return;
        }

        this.showLoading('Creating your team...');

        try {
            // Create FormData for file upload
            const formData = new FormData();
            formData.append('name', this.formData.name);
            formData.append('tag', this.formData.tag);
            formData.append('tagline', this.formData.tagline);
            formData.append('description', this.formData.description);
            formData.append('game', this.formData.game);
            formData.append('region', this.formData.region);
            
            if (this.formData.logo) {
                formData.append('logo', this.formData.logo);
            }
            
            if (this.formData.banner) {
                formData.append('banner_image', this.formData.banner);
            }
            
            formData.append('roster_data', JSON.stringify(this.formData.roster));

            const response = await fetch(window.location.href, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                this.showToast('Team created successfully!', 'success');
                
                // Redirect to team page
                setTimeout(() => {
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    } else {
                        window.location.href = '/teams/';
                    }
                }, 1500);
            } else {
                const errorData = await response.json();
                this.hideLoading();
                this.showToast(errorData.error || 'Failed to create team', 'error');
            }
        } catch (error) {
            console.error('Form submission error:', error);
            this.hideLoading();
            this.showToast('An error occurred. Please try again.', 'error');
        }
    }

    // ==================== UTILITIES ====================
    getCsrfToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    debounce(func, wait) {
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

    showLoading(message = 'Processing...') {
        const overlay = document.getElementById('loading-overlay');
        const text = document.getElementById('loading-text');
        
        if (overlay) {
            overlay.classList.add('active');
        }
        
        if (text) {
            text.textContent = message;
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('active');
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            warning: 'fa-exclamation-triangle',
            info: 'fa-info-circle'
        }[type] || 'fa-info-circle';

        toast.innerHTML = `
            <i class="fas ${icon}"></i>
            <span>${message}</span>
        `;

        container.appendChild(toast);

        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'toastSlideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new EsportsTeamCreate();
});
