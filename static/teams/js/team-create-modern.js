/**
 * DeltaCrown Modern Team Create - Version 2.0
 * Complete 4-step wizard with AJAX validation
 * Compatible with team_create_modern.html template
 */

class TeamCreateModern {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.formData = {
            name: '',
            tag: '',
            tagline: '',
            game: '',
            gameName: '',
            region: '',
            regionName: '',
            logo: null,
            banner: null,
            termsAccepted: false
        };
        this.config = window.TEAM_CREATE_CONFIG || {};
        this.validationTimers = {};
        this.init();
    }

    init() {
        this.setupStepNavigation();
        this.setupValidation();
        this.setupGameCards();
        this.setupFileUploads();
        this.setupLivePreview();
        this.setupTermsCheckbox();
        this.setupFormSubmission();
    }

    // ==================== STEP NAVIGATION ====================
    setupStepNavigation() {
        const prevButtons = document.querySelectorAll('.btn-prev');
        const nextButtons = document.querySelectorAll('.btn-next');

        prevButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const prevStep = parseInt(btn.dataset.prev);
                this.goToStep(prevStep);
            });
        });

        nextButtons.forEach(btn => {
            btn.addEventListener('click', async () => {
                const nextStep = parseInt(btn.dataset.next);
                const isValid = await this.validateCurrentStep();
                if (isValid) {
                    this.goToStep(nextStep);
                }
            });
        });
    }

    goToStep(stepNumber) {
        // Update progress bar
        document.querySelectorAll('.progress-step').forEach(step => {
            const num = parseInt(step.dataset.step);
            step.classList.remove('active', 'completed');
            if (num < stepNumber) {
                step.classList.add('completed');
            } else if (num === stepNumber) {
                step.classList.add('active');
            }
        });

        // Show current step
        document.querySelectorAll('.form-step').forEach(step => {
            step.classList.remove('active');
        });
        const currentFormStep = document.querySelector(`.form-step[data-step="${stepNumber}"]`);
        if (currentFormStep) {
            currentFormStep.classList.add('active');
        }

        this.currentStep = stepNumber;

        // Special actions per step
        if (stepNumber === 4) {
            this.populateSummary();
            this.updateFinalPreview();
        }

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    async validateCurrentStep() {
        switch (this.currentStep) {
            case 1:
                return await this.validateStep1();
            case 2:
                return await this.validateStep2();
            case 3:
                return true; // Step 3 is optional
            case 4:
                return this.validateStep4();
            default:
                return true;
        }
    }

    // ==================== STEP 1 VALIDATION ====================
    setupValidation() {
        const nameInput = document.getElementById('id_name');
        const tagInput = document.getElementById('id_tag');
        const taglineInput = document.getElementById('id_tagline');

        if (nameInput) {
            nameInput.addEventListener('input', () => {
                clearTimeout(this.validationTimers.name);
                this.validationTimers.name = setTimeout(() => {
                    this.validateTeamName(nameInput.value);
                }, 500);
                // Update preview immediately
                this.updatePreview('name', nameInput.value);
            });
        }

        if (tagInput) {
            tagInput.addEventListener('input', (e) => {
                // Auto-uppercase
                e.target.value = e.target.value.toUpperCase();
                
                clearTimeout(this.validationTimers.tag);
                this.validationTimers.tag = setTimeout(() => {
                    this.validateTeamTag(tagInput.value);
                }, 500);
                // Update preview immediately
                this.updatePreview('tag', tagInput.value);
            });
        }

        if (taglineInput) {
            taglineInput.addEventListener('input', (e) => {
                this.updatePreview('tagline', e.target.value);
            });
        }
    }

    async validateTeamName(name) {
        const input = document.getElementById('id_name');
        const feedback = input.closest('.form-group').querySelector('.validation-feedback');
        
        if (!name || name.length < 3) {
            this.setValidationState(feedback, 'invalid', 'Team name must be at least 3 characters');
            return false;
        }

        if (name.length > 50) {
            this.setValidationState(feedback, 'invalid', 'Team name cannot exceed 50 characters');
            return false;
        }

        this.setValidationState(feedback, 'checking', 'Checking availability...');

        try {
            const response = await fetch(`${this.config.validateNameUrl}?name=${encodeURIComponent(name)}`);
            const data = await response.json();

            if (data.valid) {
                this.setValidationState(feedback, 'valid', 'Team name is available');
                this.formData.name = name;
                return true;
            } else {
                this.setValidationState(feedback, 'invalid', 'This team name is already in use on DeltaCrown. Try a variation or add your region (e.g., "Dhaka Dragons BD").');
                return false;
            }
        } catch (error) {
            console.error('Name validation error:', error);
            this.setValidationState(feedback, 'valid', '');
            this.formData.name = name;
            return true;
        }
    }

    async validateTeamTag(tag) {
        const input = document.getElementById('id_tag');
        const feedback = input.closest('.form-group').querySelector('.validation-feedback');
        
        if (!tag || tag.length < 2) {
            this.setValidationState(feedback, 'invalid', 'Team tag must be at least 2 characters');
            return false;
        }

        if (tag.length > 10) {
            this.setValidationState(feedback, 'invalid', 'Team tag cannot exceed 10 characters');
            return false;
        }

        if (!/^[A-Z0-9]+$/.test(tag)) {
            this.setValidationState(feedback, 'invalid', 'Team tag can only contain letters and numbers');
            return false;
        }

        this.setValidationState(feedback, 'checking', 'Checking availability...');

        try {
            const response = await fetch(`${this.config.validateTagUrl}?tag=${encodeURIComponent(tag)}`);
            const data = await response.json();

            if (data.valid) {
                this.setValidationState(feedback, 'valid', 'Team tag is available');
                this.formData.tag = tag;
                return true;
            } else {
                this.setValidationState(feedback, 'invalid', 'That tag is already taken. Try another 2-5 letter tag that represents your team.');
                return false;
            }
        } catch (error) {
            console.error('Tag validation error:', error);
            this.setValidationState(feedback, 'valid', '');
            this.formData.tag = tag;
            return true;
        }
    }

    setValidationState(feedbackEl, state, message) {
        if (!feedbackEl) return;

        feedbackEl.classList.remove('is-checking', 'is-valid', 'is-invalid');
        
        switch (state) {
            case 'checking':
                feedbackEl.classList.add('is-checking');
                break;
            case 'valid':
                feedbackEl.classList.add('is-valid');
                break;
            case 'invalid':
                feedbackEl.classList.add('is-invalid');
                break;
        }

        const messageEl = feedbackEl.querySelector('.validation-message');
        if (messageEl) {
            messageEl.textContent = message;
        }
    }

    async validateStep1() {
        const name = document.getElementById('id_name').value.trim();
        const tag = document.getElementById('id_tag').value.trim();

        if (!name || name.length < 3) {
            this.showToast('Please enter a valid team name (min 3 characters)', 'error');
            return false;
        }

        if (!tag || tag.length < 2) {
            this.showToast('Please enter a valid team tag (min 2 characters)', 'error');
            return false;
        }

        // Validate uniqueness
        const nameValid = await this.validateTeamName(name);
        const tagValid = await this.validateTeamTag(tag);

        if (!nameValid || !tagValid) {
            this.showToast('Team name or tag already exists', 'error');
            return false;
        }

        return true;
    }

    // ==================== STEP 2: GAME & REGION ====================
    setupGameCards() {
        const container = document.getElementById('game-cards-container');
        if (!container) return;

        const games = this.config.gameConfigs || {};
        
        Object.keys(games).forEach(gameCode => {
            const game = games[gameCode];
            const cardHtml = this.createGameCard(gameCode, game);
            container.insertAdjacentHTML('beforeend', cardHtml);
        });

        // Setup click handlers
        container.addEventListener('click', (e) => {
            const card = e.target.closest('.game-card');
            if (card) {
                this.selectGame(card.dataset.game);
            }
        });
    }

    createGameCard(gameCode, game) {
        const cardImagePath = `${this.config.staticUrl}img/game_cards/${gameCode}.jpg`;
        
        return `
            <div class="game-card" data-game="${gameCode}">
                <img src="${cardImagePath}" alt="${game.display_name}" class="game-card-image" onerror="this.src='${this.config.staticUrl}img/game_cards/default_game_card.jpg'">
                <div class="game-card-content">
                    <div class="game-card-name">${game.display_name}</div>
                    <div class="game-card-meta">
                        <i class="fas fa-${this.getGameIcon(game.category)}"></i>
                        <span>${game.platform || 'PC'} • ${game.team_size || '5v5'}</span>
                    </div>
                </div>
                <div class="game-card-check">
                    <i class="fas fa-check"></i>
                </div>
            </div>
        `;
    }

    getGameIcon(category) {
        const icons = {
            'FPS': 'crosshairs',
            'MOBA': 'chess-knight',
            'Battle Royale': 'parachute-box',
            'Sports': 'futbol'
        };
        return icons[category] || 'gamepad';
    }

    async selectGame(gameCode) {
        // Remove previous selection
        document.querySelectorAll('.game-card').forEach(card => {
            card.classList.remove('selected');
        });

        // Select new game
        const selectedCard = document.querySelector(`.game-card[data-game="${gameCode}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }

        // Update hidden input
        document.getElementById('id_game').value = gameCode;
        this.formData.game = gameCode;

        const gameConfig = this.config.gameConfigs[gameCode];
        if (gameConfig) {
            this.formData.gameName = gameConfig.display_name;
            this.updatePreview('game', gameConfig.display_name);
        }

        // Check if user already has a team for this game
        await this.checkExistingTeam(gameCode);

        // Load regions for this game
        await this.loadGameRegions(gameCode);

        // Show game ID notice if needed
        this.showGameIdNoticeIfNeeded(gameCode);

        // Enable next button
        const nextBtn = document.querySelector('[data-step="2"] .btn-next');
        if (nextBtn && document.getElementById('id_region').value) {
            nextBtn.disabled = false;
        }
    }

    async checkExistingTeam(gameCode) {
        const alertBox = document.getElementById('already-in-team-alert');
        if (!alertBox) return;

        try {
            const response = await fetch(`${this.config.checkExistingTeamUrl}?game=${gameCode}`);
            const data = await response.json();

            if (data.has_team) {
                // Show alert
                const message = document.getElementById('already-in-team-message');
                const goToTeamBtn = document.getElementById('go-to-existing-team');
                
                if (message && goToTeamBtn) {
                    message.innerHTML = `You're already a member of <strong>${data.team.name}</strong> (${data.team.tag}) for <strong>${this.formData.gameName}</strong> on DeltaCrown. You can only belong to one active team per game. To create a new ${this.formData.gameName} team, you must leave your current team first.`;
                    goToTeamBtn.href = `/teams/${data.team.slug}/`;
                    goToTeamBtn.style.display = 'inline-flex';
                }
                
                alertBox.style.display = 'flex';
                
                // Disable form progression
                const nextBtn = document.querySelector('[data-step="2"] .btn-next');
                if (nextBtn) {
                    nextBtn.disabled = true;
                }
                
                // Disable region selector
                const regionSection = document.getElementById('region-section');
                if (regionSection) {
                    regionSection.style.display = 'none';
                }
            } else {
                // Hide alert
                alertBox.style.display = 'none';
            }
        } catch (error) {
            console.error('Error checking existing team:', error);
            // Don't block form if check fails
            alertBox.style.display = 'none';
        }
    }

    async loadGameRegions(gameCode) {
        const regionSection = document.getElementById('region-section');
        const container = document.getElementById('region-selector-container');
        
        if (!container || !regionSection) return;

        // Show loading
        container.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin"></i> Loading regions...</div>';
        regionSection.style.display = 'block';

        try {
            const response = await fetch(`${this.config.getGameRegionsUrl}${gameCode}/`);
            const data = await response.json();

            if (data.success && data.regions) {
                this.renderRegions(data.regions, container);
            } else {
                throw new Error('Failed to load regions');
            }
        } catch (error) {
            console.error('Error loading regions:', error);
            container.innerHTML = '<div class="loading-state" style="color: var(--error);"><i class="fas fa-exclamation-triangle"></i> Failed to load regions. Please try again.</div>';
        }
    }

    renderRegions(regions, container) {
        container.innerHTML = '';

        regions.forEach(([code, name]) => {
            const cardHtml = `
                <div class="region-card" data-region="${code}">
                    <div class="region-card-icon">
                        <i class="fas fa-globe"></i>
                    </div>
                    <div class="region-card-name">${name}</div>
                    <div class="region-card-check">
                        <i class="fas fa-check"></i>
                    </div>
                </div>
            `;
            container.insertAdjacentHTML('beforeend', cardHtml);
        });

        // Setup click handlers
        container.addEventListener('click', (e) => {
            const card = e.target.closest('.region-card');
            if (card) {
                this.selectRegion(card.dataset.region, card.querySelector('.region-card-name').textContent);
            }
        });
    }

    selectRegion(regionCode, regionName) {
        // Remove previous selection
        document.querySelectorAll('.region-card').forEach(card => {
            card.classList.remove('selected');
        });

        // Select new region
        const selectedCard = document.querySelector(`.region-card[data-region="${regionCode}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }

        // Update hidden input
        document.getElementById('id_region').value = regionCode;
        this.formData.region = regionCode;
        this.formData.regionName = regionName;
        this.updatePreview('region', regionName);

        // Enable next button
        const nextBtn = document.querySelector('[data-step="2"] .btn-next');
        if (nextBtn) {
            nextBtn.disabled = false;
        }
    }

    showGameIdNoticeIfNeeded(gameCode) {
        const notice = document.getElementById('game-id-notice');
        const noticeText = document.getElementById('game-id-notice-text');
        
        if (!notice || !noticeText) return;

        const gameConfig = this.config.gameConfigs[gameCode];
        if (!gameConfig) return;

        // Games that require game IDs
        const gamesNeedingId = ['VALORANT', 'CS2', 'DOTA2', 'MLBB'];
        
        if (gamesNeedingId.includes(gameCode)) {
            noticeText.textContent = `For ${gameConfig.display_name} teams, we require your ${gameConfig.player_id_label || 'game ID'} before you can create or join a team. You'll be asked to add it if it's missing.`;
            notice.style.display = 'flex';
        } else {
            notice.style.display = 'none';
        }
    }

    async validateStep2() {
        const game = document.getElementById('id_game').value;
        const region = document.getElementById('id_region').value;

        if (!game) {
            this.showToast('Please select a game', 'error');
            return false;
        }

        if (!region) {
            this.showToast('Please select a region', 'error');
            return false;
        }

        // Check if user has existing team
        try {
            const response = await fetch(`${this.config.checkExistingTeamUrl}?game=${game}`);
            const data = await response.json();

            if (data.has_team) {
                this.showToast(`You already have a team for this game: ${data.team.name}`, 'error');
                return false;
            }
        } catch (error) {
            console.error('Error checking team:', error);
        }

        return true;
    }

    // ==================== STEP 3: FILE UPLOADS ====================
    setupFileUploads() {
        this.setupUploadZone('logo-upload-zone', 'id_logo', 'logo-preview', 'logo');
        this.setupUploadZone('banner-upload-zone', 'id_banner_image', 'banner-preview', 'banner');
    }

    setupUploadZone(zoneId, inputId, previewId, type) {
        const zone = document.getElementById(zoneId);
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);

        if (!zone || !input || !preview) return;

        zone.addEventListener('click', () => {
            input.click();
        });

        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleFileUpload(file, preview, type);
            }
        });

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.style.borderColor = 'var(--primary-cyan)';
        });

        zone.addEventListener('dragleave', () => {
            zone.style.borderColor = '';
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.style.borderColor = '';
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                input.files = e.dataTransfer.files;
                this.handleFileUpload(file, preview, type);
            }
        });
    }

    handleFileUpload(file, previewEl, type) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            previewEl.innerHTML = `<img src="${e.target.result}" alt="${type} preview">`;
            previewEl.classList.add('active');
            
            // Update live preview
            if (type === 'logo') {
                this.updatePreview('logo', e.target.result);
                this.formData.logo = e.target.result;
            } else if (type === 'banner') {
                this.updatePreview('banner', e.target.result);
                this.formData.banner = e.target.result;
            }
        };

        reader.readAsDataURL(file);
    }

    // ==================== LIVE PREVIEW ====================
    setupLivePreview() {
        const descInput = document.getElementById('id_description');
        if (descInput) {
            descInput.addEventListener('input', (e) => {
                this.formData.description = e.target.value;
            });
        }
    }

    updatePreview(field, value) {
        // Update all preview instances
        const fields = {
            name: ['preview-name', 'preview-name-2'],
            tag: ['preview-tag', 'preview-tag-2'],
            tagline: ['preview-tagline', 'preview-tagline-2'],
            game: ['preview-game', 'preview-game-2'],
            region: ['preview-region', 'preview-region-2'],
            logo: ['preview-logo', 'preview-logo-2'],
            banner: ['preview-banner', 'preview-banner-2']
        };

        const elementIds = fields[field];
        if (!elementIds) return;

        elementIds.forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;

            switch (field) {
                case 'name':
                    el.textContent = value || 'Team Name';
                    break;
                case 'tag':
                    el.textContent = value ? `[${value}]` : '[TAG]';
                    break;
                case 'tagline':
                    el.textContent = value || 'Your team tagline';
                    break;
                case 'game':
                case 'region':
                    el.textContent = value || `Select ${field.charAt(0).toUpperCase() + field.slice(1)}`;
                    break;
                case 'logo':
                    if (value) {
                        el.style.backgroundImage = `url(${value})`;
                        el.innerHTML = '';
                    }
                    break;
                case 'banner':
                    if (value) {
                        el.style.backgroundImage = `url(${value})`;
                    }
                    break;
            }
        });
    }

    // ==================== STEP 4: TERMS & SUMMARY ====================
    setupTermsCheckbox() {
        const checkbox = document.querySelector('input[name="accept_terms"]');
        const termsError = document.getElementById('terms-error');

        if (checkbox && termsError) {
            checkbox.addEventListener('change', () => {
                this.formData.termsAccepted = checkbox.checked;
                if (checkbox.checked) {
                    termsError.style.display = 'none';
                }
            });
        }
    }

    populateSummary() {
        const summaryFields = {
            'summary-name': this.formData.name || '-',
            'summary-tag': this.formData.tag || '-',
            'summary-game': this.formData.gameName || '-',
            'summary-region': this.formData.regionName || '-'
        };

        Object.keys(summaryFields).forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = summaryFields[id];
            }
        });
    }

    updateFinalPreview() {
        // Ensure all preview fields are populated
        this.updatePreview('name', this.formData.name);
        this.updatePreview('tag', this.formData.tag);
        this.updatePreview('tagline', document.getElementById('id_tagline')?.value || '');
        this.updatePreview('game', this.formData.gameName);
        this.updatePreview('region', this.formData.regionName);
        if (this.formData.logo) {
            this.updatePreview('logo', this.formData.logo);
        }
        if (this.formData.banner) {
            this.updatePreview('banner', this.formData.banner);
        }
    }

    validateStep4() {
        const checkbox = document.querySelector('input[name="accept_terms"]');
        const termsError = document.getElementById('terms-error');

        if (!checkbox || !checkbox.checked) {
            if (termsError) {
                termsError.style.display = 'flex';
                termsError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            this.showToast('You must agree to the DeltaCrown Team Terms & Guidelines', 'error');
            return false;
        }

        return true;
    }

    // ==================== FORM SUBMISSION ====================
    setupFormSubmission() {
        const form = document.getElementById('team-create-form');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Final validation
            const termsValid = this.validateStep4();
            if (!termsValid) return;

            // Show loading
            this.showLoading();

            // Submit via AJAX
            const formData = new FormData(form);
            
            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': this.config.csrfToken
                    },
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    this.showToast(`Team "${this.formData.name}" created successfully!`, 'success');
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 1000);
                } else {
                    this.hideLoading();
                    this.handleFormErrors(data);
                }
            } catch (error) {
                this.hideLoading();
                console.error('Form submission error:', error);
                this.showToast('An error occurred. Please try again.', 'error');
            }
        });
    }

    handleFormErrors(data) {
        if (data.error) {
            this.showToast(data.error, 'error');
        }

        if (data.errors) {
            const firstField = Object.keys(data.errors)[0];
            const firstError = data.errors[firstField][0];
            this.showToast(firstError, 'error');
            
            // Go to step with error
            if (firstField === 'name' || firstField === 'tag' || firstField === 'tagline') {
                this.goToStep(1);
            } else if (firstField === 'game' || firstField === 'region') {
                this.goToStep(2);
            } else if (firstField === 'logo' || firstField === 'banner_image') {
                this.goToStep(3);
            }
        }
    }

    // ==================== UI HELPERS ====================
    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            padding: 1rem 1.5rem;
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 2px solid var(--border-color);
            border-left: 4px solid var(--${type === 'error' ? 'error' : type === 'success' ? 'success' : 'info'});
            border-radius: 12px;
            color: var(--text-primary);
            font-weight: 600;
            z-index: 10000;
            animation: slideIn 0.3s ease;
            max-width: 400px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        `;

        const icon = {
            success: 'fa-check-circle',
            error: 'fa-times-circle',
            info: 'fa-info-circle'
        }[type] || 'fa-info-circle';

        toast.innerHTML = `
            <i class="fas ${icon}" style="margin-right: 0.75rem; color: var(--${type === 'error' ? 'error' : type === 'success' ? 'success' : 'info'});"></i>
            <span>${message}</span>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    new TeamCreateModern();
});
