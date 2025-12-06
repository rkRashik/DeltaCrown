/**
 * DeltaCrown Team Create - Version 2.0
 * Complete client-side logic for 6-step team creation wizard
 * 
 * Features:
 * - Real-time AJAX validation
 * - Draft auto-save/restore
 * - Step navigation with validation
 * - File upload with preview
 * - Live preview updates
 * - One-team-per-game enforcement
 * - Mobile-optimized
 * 
 * Last Updated: November 19, 2025
 */

(function() {
    'use strict';

    /**
     * Logging utility
     */
    function dcLog(message, data) {
        if (console && console.log) {
            if (data) {
                console.log('[TeamCreate]', message, data);
            } else {
                console.log('[TeamCreate]', message);
            }
        }
    }

    /**
     * Main TeamCreateWizard class
     */
    class TeamCreateWizard {
        constructor() {
            this.currentStep = 1;
            this.totalSteps = 5;
            this.validationState = {
                name: false,
                tag: false,
                game: false,
                region: false,
                terms: false
            };
            this.formData = {
                name: '',
                tag: '',
                tagline: '',
                game: '',
                gameName: '',
                region: '',
                regionName: '',
                description: '',
                logoFile: null,
                bannerFile: null,
                social: {}
            };
            this.config = window.TEAM_CREATE_CONFIG || {};
            this.validationTimers = {};
            this.draftSaveTimer = null;
            
            this.init();
        }

        /**
         * Initialize the wizard
         */
        init() {
            dcLog('🚀 TeamCreateWizard initializing...');
            
            // Check for draft on load
            this.checkForDraft();
            
            // Setup all event listeners
            this.setupStepNavigation();
            this.setupValidation();
            this.setupGameCards();
            this.setupFileUploads();
            this.setupLivePreview();
            this.setupTermsCheckbox();
            this.setupFormSubmission();
            this.setupDraftAutoSave();
            this.setupModalHandlers();
            
            dcLog('✅ TeamCreateWizard initialized successfully');
        }

        /* ================================================
           DRAFT SYSTEM
           ================================================ */

        /**
         * Check if draft exists and prompt user
         */
        async checkForDraft() {
            if (!this.config.hasDraft) return;

            try {
                const response = await fetch(this.config.urls.loadDraft, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const data = await response.json();
                
                if (data.success && data.has_draft && data.draft) {
                    this.showDraftModal(data.draft);
                }
            } catch (error) {
                console.error('Failed to load draft:', error);
            }
        }

        /**
         * Show draft restore modal
         */
        showDraftModal(draft) {
            const modal = document.getElementById('draftModal');
            const btnLoad = document.getElementById('btnLoadDraft');
            
            if (!modal) return;

            // Populate modal info
            document.getElementById('draftName').textContent = draft.name || '-';
            document.getElementById('draftGame').textContent = draft.game || '-';
            document.getElementById('draftTimeAgo').textContent = draft.time_ago || 'recently';

            // Show modal
            modal.style.display = 'flex';

            // Show load draft button in header
            btnLoad.style.display = 'inline-flex';
        }

        /**
         * Restore draft data
         */
        restoreDraft() {
            if (!this.config.draftData) return;

            const draft = this.config.draftData;

            // Populate form fields
            if (draft.name) {
                document.getElementById('teamName').value = draft.name;
                this.validateTeamName(draft.name);
            }
            
            if (draft.tag) {
                document.getElementById('teamTag').value = draft.tag;
                this.validateTeamTag(draft.tag);
            }
            
            if (draft.tagline) {
                document.getElementById('teamTagline').value = draft.tagline;
            }
            
            if (draft.description) {
                document.getElementById('teamDescription').value = draft.description;
            }
            
            // Social links
            const socialFields = ['twitter', 'instagram', 'discord', 'youtube', 'twitch'];
            socialFields.forEach(field => {
                if (draft[field]) {
                    document.querySelector(`input[name="${field}"]`).value = draft[field];
                }
            });

            // Update live preview
            this.updateAllPreviews();

            // Show success toast
            this.showToast('Draft restored successfully!', 'success');
        }

        /**
         * Auto-save draft every 5 seconds
         */
        setupDraftAutoSave() {
            // Clear any existing timer
            if (this.draftSaveTimer) {
                clearInterval(this.draftSaveTimer);
            }

            // Save every 5 seconds
            this.draftSaveTimer = setInterval(() => {
                this.saveDraft();
            }, 5000);
        }

        /**
         * Save current form data as draft
         */
        async saveDraft() {
            // Don't save if on last step or if no data entered
            if (this.currentStep === 6 || !this.formData.name) return;

            try {
                const draftData = {
                    name: this.formData.name,
                    tag: this.formData.tag,
                    tagline: this.formData.tagline,
                    description: this.formData.description,
                    game: this.formData.game,
                    region: this.formData.region,
                    twitter: this.formData.social.twitter || '',
                    instagram: this.formData.social.instagram || '',
                    discord: this.formData.social.discord || '',
                    youtube: this.formData.social.youtube || '',
                    twitch: this.formData.social.twitch || ''
                };

                await fetch(this.config.urls.saveDraft, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.config.csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify(draftData)
                });
                
                dcLog('💾 Draft saved');
            } catch (error) {
                console.error('Failed to save draft:', error);
            }
        }

        /**
         * Clear draft from cache
         */
        async clearDraft() {
            try {
                await fetch(this.config.urls.clearDraft, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.config.csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
            } catch (error) {
                console.error('Failed to clear draft:', error);
            }
        }

        /* ================================================
           STEP NAVIGATION
           ================================================ */

        /**
         * Setup step navigation event listeners
         */
        setupStepNavigation() {
            // Next buttons
            document.querySelectorAll('.btn-next').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const nextStep = parseInt(btn.dataset.next);
                    const isValid = await this.validateCurrentStep();
                    
                    if (isValid) {
                        this.goToStep(nextStep);
                    }
                });
            });

            // Previous buttons
            document.querySelectorAll('.btn-prev').forEach(btn => {
                btn.addEventListener('click', () => {
                    const prevStep = parseInt(btn.dataset.prev);
                    this.goToStep(prevStep);
                });
            });

            // Quick edit links in summary
            document.querySelectorAll('.link-button[data-goto]').forEach(btn => {
                btn.addEventListener('click', () => {
                    const step = parseInt(btn.dataset.goto);
                    this.goToStep(step);
                });
            });
        }

        /**
         * Navigate to specific step
         */
        goToStep(stepNumber) {
            if (stepNumber < 1 || stepNumber > this.totalSteps) return;

            // Hide current step
            document.querySelectorAll('.form-step').forEach(step => {
                step.classList.remove('active');
            });

            // Show target step
            const targetStep = document.querySelector(`.form-step[data-step="${stepNumber}"]`);
            if (targetStep) {
                targetStep.classList.add('active');
            }

            // Update progress bar
            this.updateProgressBar(stepNumber);

            // Update current step
            this.currentStep = stepNumber;

            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });

            // Special actions for certain steps
            if (stepNumber === 3) {
                this.loadRegionsForSelectedGame();
            } else if (stepNumber === 5) {
                this.populateSummary();
            }

            dcLog(`📍 Navigated to step ${stepNumber}`);
        }

        /**
         * Update progress bar visual state
         */
        updateProgressBar(stepNumber) {
            // Update progress fill
            const progressPercentage = (stepNumber / this.totalSteps) * 100;
            document.getElementById('progressFill').style.width = `${progressPercentage}%`;

            // Update step circles
            document.querySelectorAll('.progress-step').forEach((step, index) => {
                const stepNum = index + 1;
                
                step.classList.remove('active', 'completed');
                
                if (stepNum < stepNumber) {
                    step.classList.add('completed');
                } else if (stepNum === stepNumber) {
                    step.classList.add('active');
                }
            });
        }

        /**
         * Validate current step before proceeding
         */
        async validateCurrentStep() {
            switch (this.currentStep) {
                case 1:
                    return this.validateStep1();
                case 2:
                    return this.validateStep2();
                case 3:
                    return this.validateStep3();
                case 4:
                    return true; // Optional fields
                case 5:
                    return true; // Preview only
                case 6:
                    return this.validateStep6();
                default:
                    return true;
            }
        }

        /**
         * Validate Step 1 (Identity)
         */
        validateStep1() {
            return this.validationState.name && this.validationState.tag;
        }

        /**
         * Validate Step 2 (Game Selection)
         */
        validateStep2() {
            return this.validationState.game;
        }

        /**
         * Validate Step 3 (Region Selection)
         */
        validateStep3() {
            return this.validationState.region;
        }

        /**
         * Validate Step 6 (Terms & Confirm)
         */
        validateStep6() {
            const termsCheckbox = document.getElementById('acceptTerms');
            const termsError = document.getElementById('termsErrorAlert');
            
            if (!termsCheckbox.checked) {
                termsError.style.display = 'flex';
                termsError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Shake animation
                termsError.style.animation = 'none';
                setTimeout(() => {
                    termsError.style.animation = 'shake 0.5s';
                }, 10);
                
                return false;
            }
            
            termsError.style.display = 'none';
            return true;
        }

        /* ================================================
           VALIDATION SYSTEM
           ================================================ */

        /**
         * Setup real-time validation
         */
        setupValidation() {
            // Team Name
            const nameInput = document.getElementById('teamName');
            const nameValidation = nameInput.closest('.input-with-validation').querySelector('.validation-icon');
            const nameFeedback = nameInput.closest('.form-group').querySelector('.validation-message');
            const nameCharCount = nameInput.closest('.form-group').querySelector('.char-count');

            nameInput.addEventListener('input', (e) => {
                const value = e.target.value.trim();
                
                // Update char count
                nameCharCount.textContent = `${value.length} / 50`;
                
                // Clear previous timer
                clearTimeout(this.validationTimers.name);
                
                // Show checking state
                nameValidation.className = 'validation-icon checking';
                nameFeedback.textContent = 'Checking availability...';
                nameFeedback.className = 'validation-message';
                
                // Validate after 500ms
                this.validationTimers.name = setTimeout(() => {
                    this.validateTeamName(value);
                }, 500);
                
                // Update live preview immediately
                this.formData.name = value;
                this.updatePreview('name', value);
            });

            // Team Tag
            const tagInput = document.getElementById('teamTag');
            const tagValidation = tagInput.closest('.input-with-validation').querySelector('.validation-icon');
            const tagFeedback = tagInput.closest('.form-group').querySelector('.validation-message');
            const tagCharCount = tagInput.closest('.form-group').querySelector('.char-count');

            tagInput.addEventListener('input', (e) => {
                // Auto-uppercase
                e.target.value = e.target.value.toUpperCase();
                const value = e.target.value.trim();
                
                // Update char count
                tagCharCount.textContent = `${value.length} / 10`;
                
                // Clear previous timer
                clearTimeout(this.validationTimers.tag);
                
                // Show checking state
                tagValidation.className = 'validation-icon checking';
                tagFeedback.textContent = 'Checking availability...';
                tagFeedback.className = 'validation-message';
                
                // Validate after 500ms
                this.validationTimers.tag = setTimeout(() => {
                    this.validateTeamTag(value);
                }, 500);
                
                // Update live preview immediately
                this.formData.tag = value;
                this.updatePreview('tag', value);
            });

            // Tagline
            const taglineInput = document.getElementById('teamTagline');
            const taglineCharCount = taglineInput.closest('.form-group').querySelector('.char-count');
            
            taglineInput.addEventListener('input', (e) => {
                const value = e.target.value;
                taglineCharCount.textContent = `${value.length} / 200`;
                this.formData.tagline = value;
                this.updatePreview('tagline', value);
            });

            // Description
            const descInput = document.getElementById('teamDescription');
            const descCharCount = descInput.closest('.form-group').querySelector('.char-count');
            
            descInput.addEventListener('input', (e) => {
                const value = e.target.value;
                descCharCount.textContent = `${value.length} / 500`;
                this.formData.description = value;
            });

            // Social links
            document.querySelectorAll('.social-input-group input').forEach(input => {
                input.addEventListener('input', (e) => {
                    const name = e.target.name;
                    const value = e.target.value;
                    this.formData.social[name] = value;
                    this.updatePreview('social', name);
                });
            });
        }

        /**
         * Validate team name via AJAX
         */
        async validateTeamName(name) {
            const nameInput = document.getElementById('teamName');
            const nameValidation = nameInput.closest('.input-with-validation').querySelector('.validation-icon');
            const nameFeedback = nameInput.closest('.form-group').querySelector('.validation-message');
            const suggestionsContainer = nameInput.closest('.form-group').querySelector('.suggestions-container');
            const nextBtn = document.querySelector('.form-step[data-step="1"] .btn-next');

            // Client-side validation
            if (name.length < 3) {
                nameValidation.className = 'validation-icon invalid';
                nameFeedback.textContent = 'Name must be at least 3 characters';
                nameFeedback.className = 'validation-message error';
                suggestionsContainer.style.display = 'none';
                this.validationState.name = false;
                nextBtn.disabled = true;
                dcLog('❌ Name too short');
                return;
            }

            if (name.length > 50) {
                nameValidation.className = 'validation-icon invalid';
                nameFeedback.textContent = 'Name must be 50 characters or less';
                nameFeedback.className = 'validation-message error';
                suggestionsContainer.style.display = 'none';
                this.validationState.name = false;
                nextBtn.disabled = true;
                dcLog('❌ Name too long');
                return;
            }

            try {
                const response = await fetch(`${this.config.urls.validateName}?name=${encodeURIComponent(name)}`, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const data = await response.json();
                
                dcLog(`🔍 Name validation result:`, data);

                if (data.valid) {
                    nameValidation.className = 'validation-icon valid';
                    nameFeedback.textContent = data.message || 'Perfect! This name is available.';
                    nameFeedback.className = 'validation-message success';
                    suggestionsContainer.style.display = 'none';
                    this.validationState.name = true;
                    dcLog('✅ Name is valid and available');
                } else {
                    nameValidation.className = 'validation-icon invalid';
                    nameFeedback.textContent = data.message || 'This name is already taken.';
                    nameFeedback.className = 'validation-message error';
                    
                    // Show suggestions
                    if (data.suggestions && data.suggestions.length > 0) {
                        this.showSuggestions(suggestionsContainer, data.suggestions, 'name');
                    }
                    
                    this.validationState.name = false;
                    dcLog('❌ Name is NOT available:', data.message);
                }
            } catch (error) {
                console.error('Name validation error:', error);
                nameValidation.className = 'validation-icon invalid';
                nameFeedback.textContent = 'Network error. Please try again.';
                nameFeedback.className = 'validation-message error';
                this.validationState.name = false;
                dcLog('❌ Network error during name validation');
            }

            // Update next button state
            this.updateStep1NextButton();
        }

        /**
         * Validate team tag via AJAX
         */
        async validateTeamTag(tag) {
            const tagInput = document.getElementById('teamTag');
            const tagValidation = tagInput.closest('.input-with-validation').querySelector('.validation-icon');
            const tagFeedback = tagInput.closest('.form-group').querySelector('.validation-message');
            const suggestionsContainer = tagInput.closest('.form-group').querySelector('.suggestions-container');
            const nextBtn = document.querySelector('.form-step[data-step="1"] .btn-next');

            // Client-side validation
            if (tag.length < 2) {
                tagValidation.className = 'validation-icon invalid';
                tagFeedback.textContent = 'Tag must be at least 2 characters';
                tagFeedback.className = 'validation-message error';
                suggestionsContainer.style.display = 'none';
                this.validationState.tag = false;
                nextBtn.disabled = true;
                return;
            }

            if (tag.length > 10) {
                tagValidation.className = 'validation-icon invalid';
                tagFeedback.textContent = 'Tag must be 10 characters or less';
                tagFeedback.className = 'validation-message error';
                suggestionsContainer.style.display = 'none';
                this.validationState.tag = false;
                nextBtn.disabled = true;
                return;
            }

            if (!/^[A-Z0-9]+$/.test(tag)) {
                tagValidation.className = 'validation-icon invalid';
                tagFeedback.textContent = 'Only letters and numbers allowed';
                tagFeedback.className = 'validation-message error';
                suggestionsContainer.style.display = 'none';
                this.validationState.tag = false;
                nextBtn.disabled = true;
                return;
            }

            try {
                const response = await fetch(`${this.config.urls.validateTag}?tag=${encodeURIComponent(tag)}`, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const data = await response.json();

                if (data.valid) {
                    tagValidation.className = 'validation-icon valid';
                    tagFeedback.textContent = data.message || 'Nice! This tag is available.';
                    tagFeedback.className = 'validation-message success';
                    suggestionsContainer.style.display = 'none';
                    this.validationState.tag = true;
                } else {
                    tagValidation.className = 'validation-icon invalid';
                    tagFeedback.textContent = data.message || 'This tag is already in use.';
                    tagFeedback.className = 'validation-message error';
                    
                    // Show suggestions
                    if (data.suggestions && data.suggestions.length > 0) {
                        this.showSuggestions(suggestionsContainer, data.suggestions, 'tag');
                    }
                    
                    this.validationState.tag = false;
                }
            } catch (error) {
                console.error('Tag validation error:', error);
                tagValidation.className = 'validation-icon invalid';
                tagFeedback.textContent = 'Network error. Please try again.';
                tagFeedback.className = 'validation-message error';
                this.validationState.tag = false;
            }

            // Update next button state
            this.updateStep1NextButton();
        }

        /**
         * Show validation suggestions
         */
        showSuggestions(container, suggestions, field) {
            const list = container.querySelector('.suggestions-list');
            list.innerHTML = '';
            
            suggestions.forEach(suggestion => {
                const chip = document.createElement('button');
                chip.type = 'button';
                chip.className = 'suggestion-chip';
                chip.textContent = suggestion;
                chip.addEventListener('click', () => {
                    const input = document.getElementById(field === 'name' ? 'teamName' : 'teamTag');
                    input.value = suggestion;
                    input.dispatchEvent(new Event('input'));
                    container.style.display = 'none';
                });
                list.appendChild(chip);
            });
            
            container.style.display = 'block';
        }

        /**
         * Update Step 1 next button state
         */
        updateStep1NextButton() {
            const nextBtn = document.querySelector('.form-step[data-step="1"] .btn-next');
            nextBtn.disabled = !(this.validationState.name && this.validationState.tag);
        }

        /* ================================================
           GAME SELECTION
           ================================================ */

        /**
         * Setup game cards
         */
        setupGameCards() {
            const grid = document.getElementById('gameCardsGrid');
            if (!grid) return;

            const games = this.config.gameConfigs || {};
            const existingTeams = this.config.existingTeams || {};
            
            dcLog('📋 Setting up game cards...');
            dcLog('Existing teams raw data:', existingTeams);
            dcLog('Game configs keys:', Object.keys(games));
            
            // Normalize game codes for comparison (handle variants like 'pubg-mobile' vs 'PUBG')
            const normalizedExistingTeams = {};
            Object.keys(existingTeams).forEach(code => {
                const normalized = this.normalizeGameCode(code);
                normalizedExistingTeams[normalized] = existingTeams[code];
                dcLog(`  Normalized ${code} -> ${normalized}`);
            });
            
            Object.keys(games).forEach(code => {
                const game = games[code];
                const normalized = this.normalizeGameCode(code);
                const hasTeam = normalizedExistingTeams[normalized] !== undefined;
                const teamInfo = normalizedExistingTeams[normalized];
                dcLog(`Game ${code} (normalized: ${normalized}): hasTeam = ${hasTeam}`, teamInfo);
                const card = this.createGameCard(code, game, hasTeam, teamInfo);
                grid.appendChild(card);
            });
        }

        /**
         * Normalize game codes to handle variants
         * Maps: 'pubg-mobile', 'PUBG', 'pubg' -> 'pubg'
         *       'VALORANT', 'valorant' -> 'valorant'
         *       'MLBB', 'mlbb' -> 'mlbb'
         */
        normalizeGameCode(code) {
            if (!code) return '';
            const lower = code.toLowerCase();
            // Handle common variants
            const variants = {
                'pubg-mobile': 'pubg',
                'pubgm': 'pubg',
                'pubg_mobile': 'pubg',
                'free-fire': 'freefire',
                'free_fire': 'freefire',
                'cs-2': 'cs2',
                'cs_2': 'cs2',
                'counter-strike-2': 'cs2',
                'mobile-legends': 'mlbb',
                'dota-2': 'dota2',
                'dota_2': 'dota2',
                'call-of-duty-mobile': 'codm',
                'cod-mobile': 'codm',
                'cod_mobile': 'codm',
            };
            return variants[lower] || lower;
        }

        /**
         * Create game card element
         */
        createGameCard(code, game, hasTeam = false, teamInfo = null) {
            const card = document.createElement('div');
            card.className = 'game-card';
            if (hasTeam) {
                card.classList.add('disabled');
                card.dataset.disabled = 'true';
            }
            card.dataset.game = code;
            
            let badgeHtml = '';
            if (hasTeam && teamInfo) {
                badgeHtml = `<div class="game-card-badge" title="You're in ${teamInfo.name}">Already Have Team</div>`;
            }
            
            card.innerHTML = `
                <img src="/static/${game.card_image}" alt="${game.name}" class="game-card-image">
                <div class="game-card-name">${game.name}</div>
                <div class="game-card-platform">${game.platform}</div>
                <div class="game-card-meta">${game.team_size} Team Size</div>
                ${badgeHtml}
            `;
            
            // ALWAYS add click handler with check - defensive programming
            card.addEventListener('click', (e) => {
                // Double-check if user has team for this game (normalize codes)
                const existingTeams = this.config.existingTeams || {};
                const normalizedCode = this.normalizeGameCode(code);
                
                // Build normalized existing teams map
                const normalizedExisting = {};
                Object.keys(existingTeams).forEach(key => {
                    const normalizedKey = this.normalizeGameCode(key);
                    normalizedExisting[normalizedKey] = existingTeams[key];
                });
                
                if (normalizedExisting[normalizedCode]) {
                    e.preventDefault();
                    e.stopPropagation();
                    dcLog(`🚫 Click blocked for ${code} (${normalizedCode}) - user has existing team`);
                    this.showExistingTeamWarning(code, normalizedExisting[normalizedCode]);
                    return false;
                }
                
                // No existing team, proceed with selection
                this.selectGame(code, game);
            });
            
            // Visual styling for disabled cards
            if (hasTeam) {
                card.style.cursor = 'not-allowed';
                card.style.opacity = '0.5';
                card.style.filter = 'grayscale(70%)';
                card.style.pointerEvents = 'all'; // Ensure events fire
            }
            
            return card;
        }

        /**
         * Show warning when user tries to select a game they already have a team for
         */
        showExistingTeamWarning(gameCode, teamInfo) {
            dcLog('showExistingTeamWarning called with:', gameCode, teamInfo);
            const gameName = this.config.gameConfigs[gameCode]?.name || gameCode;
            
            // Remove any existing modals
            const existingModal = document.getElementById('existingTeamModal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // Create modal container
            const modalContainer = document.createElement('div');
            modalContainer.id = 'existingTeamModal';
            modalContainer.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); z-index: 10000; display: flex; align-items: center; justify-content: center;';
            
            // Create modal content
            const modalContent = document.createElement('div');
            modalContent.style.cssText = 'background: rgba(0,0,0,0.95); backdrop-filter: blur(20px); padding: 40px; border-radius: 20px; border: 2px solid #f5576c; max-width: 500px; width: 90%; box-shadow: 0 20px 60px rgba(245, 87, 108, 0.4);';
            
            // Create content wrapper
            const contentWrapper = document.createElement('div');
            contentWrapper.style.cssText = 'text-align: center; color: white;';
            
            // Icon
            const icon = document.createElement('i');
            icon.className = 'fas fa-exclamation-triangle';
            icon.style.cssText = 'font-size: 48px; color: #f5576c; margin-bottom: 20px;';
            
            // Title
            const title = document.createElement('h3');
            title.style.cssText = 'font-size: 24px; margin-bottom: 15px; color: #f5576c; font-weight: 700;';
            title.textContent = 'Already in a Team';
            
            // Message 1
            const message1 = document.createElement('p');
            message1.style.cssText = 'font-size: 16px; line-height: 1.6; margin-bottom: 20px; color: rgba(255,255,255,0.9);';
            message1.innerHTML = `You're already a member of <strong style="color: #fff;">${teamInfo.name} [${teamInfo.tag}]</strong> for ${gameName}.`;
            
            // Message 2
            const message2 = document.createElement('p');
            message2.style.cssText = 'font-size: 14px; color: rgba(255,255,255,0.7); margin-bottom: 25px;';
            message2.textContent = 'You can only be in one team per game. Leave your current team to create a new one.';
            
            // Button container
            const buttonContainer = document.createElement('div');
            buttonContainer.style.cssText = 'display: flex; gap: 15px; justify-content: center;';
            
            // Leave Team button (link)
            const leaveBtn = document.createElement('a');
            leaveBtn.href = `/teams/${teamInfo.slug}/`;
            leaveBtn.style.cssText = 'background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 12px 24px; border-radius: 10px; text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; border: none; cursor: pointer;';
            leaveBtn.innerHTML = '<i class="fas fa-arrow-right"></i> View Team';
            leaveBtn.target = '_blank';
            
            // Close button
            const closeBtn = document.createElement('button');
            closeBtn.style.cssText = 'background: rgba(255,255,255,0.1); color: white; padding: 12px 24px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.2); font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px;';
            closeBtn.innerHTML = '<i class="fas fa-times"></i> Close';
            
            // Assemble the modal
            buttonContainer.appendChild(leaveBtn);
            buttonContainer.appendChild(closeBtn);
            contentWrapper.appendChild(icon);
            contentWrapper.appendChild(title);
            contentWrapper.appendChild(message1);
            contentWrapper.appendChild(message2);
            contentWrapper.appendChild(buttonContainer);
            modalContent.appendChild(contentWrapper);
            modalContainer.appendChild(modalContent);
            document.body.appendChild(modalContainer);
            
            dcLog('Modal appended, adding event listeners');
            
            // Add event listeners directly to the button element we created
            closeBtn.addEventListener('click', (e) => {
                dcLog('Close button clicked');
                e.preventDefault();
                e.stopPropagation();
                modalContainer.remove();
            });
            
            // Prevent backdrop clicks from closing when clicking on modal content
            modalContent.addEventListener('click', (e) => {
                e.stopPropagation();
            });
            
            // Close on backdrop click
            modalContainer.addEventListener('click', (e) => {
                if (e.target === modalContainer) {
                    dcLog('Backdrop clicked');
                    modalContainer.remove();
                }
            });
            
            // Close on ESC key
            const escHandler = (e) => {
                if (e.key === 'Escape') {
                    dcLog('ESC pressed');
                    modalContainer.remove();
                    document.removeEventListener('keydown', escHandler);
                }
            };
            document.addEventListener('keydown', escHandler);
        }

        /**
         * Handle game selection
         */
        async selectGame(code, game) {
            // Check if user already has a team for this game (normalize both codes)
            const existingTeams = this.config.existingTeams || {};
            const normalizedCode = this.normalizeGameCode(code);
            
            // Build normalized existing teams map
            const normalizedExisting = {};
            Object.keys(existingTeams).forEach(key => {
                const normalizedKey = this.normalizeGameCode(key);
                normalizedExisting[normalizedKey] = existingTeams[key];
            });
            
            if (normalizedExisting[normalizedCode]) {
                console.warn(`❌ Cannot select ${code} (normalized: ${normalizedCode}) - user already has team:`, normalizedExisting[normalizedCode]);
                this.showExistingTeamWarning(code, normalizedExisting[normalizedCode]);
                
                // Unselect any selected cards
                document.querySelectorAll('.game-card').forEach(card => {
                    card.classList.remove('selected');
                });
                
                // Show the built-in alert too
                const alert = document.getElementById('existingTeamAlert');
                const message = document.getElementById('existingTeamMessage');
                const viewBtn = document.getElementById('viewExistingTeamBtn');
                const leaveBtn = document.getElementById('leaveTeamBtn');
                
                if (alert && message) {
                    const gameName = this.config.gameConfigs[code]?.name || code;
                    message.textContent = `You're already a member of ${normalizedExisting[normalizedCode].name} [${normalizedExisting[normalizedCode].tag}] for ${gameName}. You can only have one team per game.`;
                    viewBtn.href = `/teams/${normalizedExisting[normalizedCode].slug}/`;
                    leaveBtn.href = `/teams/${normalizedExisting[normalizedCode].slug}/leave/`;
                    alert.style.display = 'flex';
                    alert.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                // Disable next button
                const nextBtn = document.querySelector('.form-step[data-step="2"] .btn-next');
                if (nextBtn) nextBtn.disabled = true;
                this.validationState.game = false;
                
                return; // STOP execution
            }
            
            // Update selected state
            document.querySelectorAll('.game-card').forEach(card => {
                card.classList.remove('selected');
            });
            document.querySelector(`.game-card[data-game="${code}"]`).classList.add('selected');

            // Store selection (convert to lowercase for backend)
            this.formData.game = code.toLowerCase();
            this.formData.gameName = game.name;
            document.getElementById('teamGame').value = code.toLowerCase();

            // Update preview
            this.updatePreview('game', game.name);

            // Check for existing team
            await this.checkExistingTeam(code);

            // Enable next button if no conflict
            const nextBtn = document.querySelector('.form-step[data-step="2"] .btn-next');
            nextBtn.disabled = !this.validationState.game;
        }

        /**
         * Check if user already has team for this game
         */
        async checkExistingTeam(gameCode) {
            const alert = document.getElementById('existingTeamAlert');
            const message = document.getElementById('existingTeamMessage');
            const viewBtn = document.getElementById('viewExistingTeamBtn');
            const leaveBtn = document.getElementById('leaveTeamBtn');
            const gameIdNotice = document.getElementById('gameIdNotice');
            const nextBtn = document.querySelector('.form-step[data-step="2"] .btn-next');

            try {
                const response = await fetch(`${this.config.urls.checkExistingTeam}?game=${gameCode}`, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const data = await response.json();

                if (data.has_team) {
                    // Show alert
                    message.textContent = data.message;
                    viewBtn.href = `/teams/${data.team.slug}/`;
                    leaveBtn.href = `/teams/${data.team.slug}/leave/`;
                    alert.style.display = 'flex';
                    
                    // Disable next button
                    nextBtn.disabled = true;
                    this.validationState.game = false;
                    
                    // Hide game ID notice
                    gameIdNotice.style.display = 'none';
                } else {
                    // Hide alert
                    alert.style.display = 'none';
                    
                    // Enable next button
                    nextBtn.disabled = false;
                    this.validationState.game = true;
                    
                    // Check for game ID requirement
                    this.checkGameIdRequirement(gameCode);
                }
            } catch (error) {
                console.error('Error checking existing team:', error);
                alert.style.display = 'none';
                nextBtn.disabled = false;
                this.validationState.game = true;
            }
        }

        /**
         * Check if game requires game ID and show input field
         */
        async checkGameIdRequirement(gameCode) {
            const gamesRequiringId = {
                'VALORANT': { field: 'riot_id', label: 'Riot ID (Name#TAG)', hint: 'Example: PlayerName#NA1' },
                'CS2': { field: 'steam_id', label: 'Steam ID', hint: 'Your Steam ID64 or profile URL' },
                'DOTA2': { field: 'steam_id', label: 'Steam ID', hint: 'Your Steam ID64 or profile URL' },
                'MLBB': { field: 'mlbb_id', label: 'Mobile Legends ID', hint: 'Your in-game user ID' },
                'PUBG': { field: 'pubg_mobile_id', label: 'PUBG Mobile ID', hint: 'Your character ID' },
                'FREEFIRE': { field: 'free_fire_id', label: 'Free Fire ID', hint: 'Your player ID' },
                'CODM': { field: 'codm_uid', label: 'Call of Duty Mobile UID', hint: 'Your UID from game' },
                'EFOOTBALL': { field: 'efootball_id', label: 'eFootball ID', hint: 'Your user ID' },
                'FC26': { field: 'ea_id', label: 'EA ID', hint: 'Your EA account username' }
            };

            const gameIdSection = document.getElementById('gameIdSection');
            const gameIdInput = document.getElementById('gameIdInput');
            const gameIdLabel = document.getElementById('gameIdLabel');
            const gameIdHint = document.getElementById('gameIdHint');

            if (gamesRequiringId[gameCode]) {
                const config = gamesRequiringId[gameCode];
                
                // Update labels
                gameIdLabel.textContent = config.label;
                gameIdHint.textContent = config.hint;
                gameIdInput.setAttribute('placeholder', config.hint);
                gameIdInput.dataset.field = config.field;
                
                // Try to autofill from user profile
                const profileGameId = this.config.userProfile?.[config.field];
                if (profileGameId) {
                    gameIdInput.value = profileGameId;
                    this.formData.gameId = profileGameId;
                } else {
                    gameIdInput.value = '';
                }
                
                gameIdSection.style.display = 'block';
                
                // Add validation
                gameIdInput.addEventListener('input', () => {
                    this.formData.gameId = gameIdInput.value.trim();
                    this.saveDraft();
                });
            } else {
                gameIdSection.style.display = 'none';
                this.formData.gameId = null;
            }
        }

        /* ================================================
           REGION SELECTION
           ================================================ */

        /**
         * Load regions for selected game
         */
        async loadRegionsForSelectedGame() {
            if (!this.formData.game) return;

            const loadingState = document.getElementById('regionLoadingState');
            const grid = document.getElementById('regionCardsGrid');

            loadingState.style.display = 'flex';
            grid.style.display = 'none';
            grid.innerHTML = '';

            try {
                const response = await fetch(`${this.config.urls.getRegions}${this.formData.game}/`, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const data = await response.json();

                if (data.success && data.regions) {
                    data.regions.forEach(([code, name]) => {
                        const card = this.createRegionCard(code, name);
                        grid.appendChild(card);
                    });
                    
                    loadingState.style.display = 'none';
                    grid.style.display = 'grid';
                } else {
                    throw new Error('Failed to load regions');
                }
            } catch (error) {
                console.error('Error loading regions:', error);
                loadingState.innerHTML = `
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to load regions. Please try again.</p>
                    <button class="btn btn-sm btn-primary" onclick="location.reload()">Retry</button>
                `;
            }
        }

        /**
         * Create region card element
         */
        createRegionCard(code, name) {
            const card = document.createElement('div');
            card.className = 'region-card';
            card.dataset.region = code;
            
            card.innerHTML = `
                <div class="region-card-icon">
                    <i class="fas fa-globe"></i>
                </div>
                <div class="region-card-name">${name}</div>
            `;
            
            card.addEventListener('click', () => this.selectRegion(code, name));
            
            return card;
        }

        /**
         * Handle region selection
         */
        selectRegion(code, name) {
            // Update selected state
            document.querySelectorAll('.region-card').forEach(card => {
                card.classList.remove('selected');
            });
            document.querySelector(`.region-card[data-region="${code}"]`).classList.add('selected');

            // Store selection
            this.formData.region = code;
            this.formData.regionName = name;
            document.getElementById('teamRegion').value = code;

            // Update preview
            this.updatePreview('region', name);

            // Enable next button
            this.validationState.region = true;
            document.querySelector('.form-step[data-step="3"] .btn-next').disabled = false;
        }

        /* ================================================
           FILE UPLOADS
           ================================================ */

        /**
         * Setup file upload zones
         */
        setupFileUploads() {
            this.setupFileUpload('logo', 'logoUploadZone', 'logoInput', 'logoPreview', 5);
            this.setupFileUpload('banner', 'bannerUploadZone', 'bannerInput', 'bannerPreview', 10);
        }

        /**
         * Setup individual file upload
         */
        setupFileUpload(type, zoneId, inputId, previewId, maxSizeMB) {
            const zone = document.getElementById(zoneId);
            const input = document.getElementById(inputId);
            const preview = document.getElementById(previewId);
            const removeBtn = zone.querySelector('.btn-remove-file');

            if (!zone || !input) return;

            // Click to upload
            zone.addEventListener('click', (e) => {
                if (!e.target.closest('.btn-remove-file')) {
                    input.click();
                }
            });

            // Drag and drop
            zone.addEventListener('dragover', (e) => {
                e.preventDefault();
                zone.classList.add('dragover');
            });

            zone.addEventListener('dragleave', () => {
                zone.classList.remove('dragover');
            });

            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                zone.classList.remove('dragover');
                
                const file = e.dataTransfer.files[0];
                if (file) {
                    this.handleFileSelect(file, type, zone, input, preview, maxSizeMB);
                }
            });

            // File input change
            input.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    this.handleFileSelect(file, type, zone, input, preview, maxSizeMB);
                }
            });

            // Remove file
            if (removeBtn) {
                removeBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.removeFile(type, zone, input, preview);
                });
            }
        }

        /**
         * Handle file selection
         */
        handleFileSelect(file, type, zone, input, preview, maxSizeMB) {
            // Validate file type
            const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif'];
            if (!validTypes.includes(file.type)) {
                this.showToast('Please select a valid image file (JPG, PNG, WEBP, GIF)', 'error');
                return;
            }

            // Validate file size
            const maxSize = maxSizeMB * 1024 * 1024; // Convert MB to bytes
            if (file.size > maxSize) {
                this.showToast(`File size must be under ${maxSizeMB}MB`, 'error');
                return;
            }

            // Read and preview file
            const reader = new FileReader();
            reader.onload = (e) => {
                preview.src = e.target.result;
                zone.querySelector('.upload-placeholder').style.display = 'none';
                zone.querySelector('.upload-preview').style.display = 'flex';
                
                // Store file reference
                if (type === 'logo') {
                    this.formData.logoFile = file;
                    this.updatePreview('logo', e.target.result);
                } else {
                    this.formData.bannerFile = file;
                    this.updatePreview('banner', e.target.result);
                }
            };
            reader.readAsDataURL(file);
        }

        /**
         * Remove uploaded file
         */
        removeFile(type, zone, input, preview) {
            input.value = '';
            preview.src = '';
            zone.querySelector('.upload-placeholder').style.display = 'block';
            zone.querySelector('.upload-preview').style.display = 'none';
            
            if (type === 'logo') {
                this.formData.logoFile = null;
                this.updatePreview('logo', null);
            } else {
                this.formData.bannerFile = null;
                this.updatePreview('banner', null);
            }
        }

        /* ================================================
           LIVE PREVIEW
           ================================================ */

        /**
         * Setup live preview updates
         */
        setupLivePreview() {
            // Preview updates handled in validation and input listeners
        }

        /**
         * Update specific preview element
         */
        updatePreview(field, value) {
            switch (field) {
                case 'name':
                    document.getElementById('previewName').textContent = value || 'Team Name';
                    break;
                case 'tag':
                    document.getElementById('previewTag').textContent = value ? `[${value}]` : '[TAG]';
                    break;
                case 'tagline':
                    const taglineEl = document.getElementById('previewTagline');
                    if (value) {
                        taglineEl.textContent = value;
                        taglineEl.style.display = 'block';
                    } else {
                        taglineEl.textContent = 'Your inspiring tagline...';
                        taglineEl.style.display = 'block';
                    }
                    break;
                case 'game':
                    document.getElementById('previewGame').innerHTML = `<i class="fas fa-gamepad"></i> ${value || 'Select game'}`;
                    break;
                case 'region':
                    document.getElementById('previewRegion').innerHTML = `<i class="fas fa-globe"></i> ${value || 'Select region'}`;
                    break;
                case 'logo':
                    const logoEl = document.getElementById('previewLogo');
                    if (value) {
                        logoEl.innerHTML = `<img src="${value}" alt="Logo">`;
                    } else {
                        logoEl.innerHTML = '<i class="fas fa-shield-alt"></i>';
                    }
                    break;
                case 'banner':
                    const bannerEl = document.getElementById('previewBanner');
                    if (value) {
                        bannerEl.style.backgroundImage = `url(${value})`;
                        bannerEl.classList.add('has-image');
                    } else {
                        bannerEl.style.backgroundImage = '';
                        bannerEl.classList.remove('has-image');
                    }
                    break;
                case 'social':
                    this.updateSocialPreview();
                    break;
            }
        }

        /**
         * Update all preview elements
         */
        updateAllPreviews() {
            this.updatePreview('name', this.formData.name);
            this.updatePreview('tag', this.formData.tag);
            this.updatePreview('tagline', this.formData.tagline);
            this.updatePreview('game', this.formData.gameName);
            this.updatePreview('region', this.formData.regionName);
            this.updateSocialPreview();
        }

        /**
         * Update social icons in preview
         */
        updateSocialPreview() {
            const container = document.getElementById('previewSocials');
            container.innerHTML = '';
            
            const socialIcons = {
                twitter: 'fab fa-twitter',
                instagram: 'fab fa-instagram',
                discord: 'fab fa-discord',
                youtube: 'fab fa-youtube',
                twitch: 'fab fa-twitch'
            };
            
            Object.keys(socialIcons).forEach(platform => {
                const value = this.formData.social[platform];
                if (value && value.trim()) {
                    const icon = document.createElement('i');
                    icon.className = socialIcons[platform];
                    container.appendChild(icon);
                }
            });
        }

        /* ================================================
           ROSTER PREVIEW
           ================================================ */

        /**
         * Update roster preview based on game
         */
        /* ================================================
           SUMMARY & REVIEW
           ================================================ */

        /**
         * Populate summary in Step 5
         */
        populateSummary() {
            document.getElementById('summaryName').textContent = this.formData.name || '-';
            document.getElementById('summaryTag').textContent = this.formData.tag ? `[${this.formData.tag}]` : '-';
            document.getElementById('summaryGame').textContent = this.formData.gameName || '-';
            document.getElementById('summaryRegion').textContent = this.formData.regionName || '-';
        }

        /* ================================================
           TERMS & CONDITIONS
           ================================================ */

        /**
         * Setup terms checkbox
         */
        setupTermsCheckbox() {
            const checkbox = document.getElementById('acceptTerms');
            const errorAlert = document.getElementById('termsErrorAlert');

            if (!checkbox) return;

            checkbox.addEventListener('change', () => {
                if (checkbox.checked) {
                    errorAlert.style.display = 'none';
                }
            });
        }

        /* ================================================
           FORM SUBMISSION
           ================================================ */

        /**
         * Setup form submission handler
         */
        setupFormSubmission() {
            const form = document.getElementById('teamCreateForm');
            
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                // Validate Step 6
                if (!this.validateStep6()) {
                    return;
                }

                await this.submitForm();
            });
        }

        /**
         * Submit form via AJAX
         */
        async submitForm() {
            const loadingOverlay = document.getElementById('loadingOverlay');
            const loadingMessage = document.getElementById('loadingMessage');
            
            // CRITICAL: Re-validate name and tag before submission
            const name = this.formData.name;
            const tag = this.formData.tag;
            
            if (!this.validationState.name || !this.validationState.tag) {
                this.showToast('Please ensure team name and tag are valid and available.', 'error');
                this.goToStep(1);
                return;
            }
            
            // Show loading overlay
            loadingOverlay.classList.add('active');
            loadingMessage.textContent = 'Creating your team...';

            try {
                // Prepare form data
                const formData = new FormData(document.getElementById('teamCreateForm'));

                // Submit via AJAX
                const response = await fetch(this.config.urls.submit, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json();

                if (data.success) {
                    // Success!
                    loadingMessage.textContent = '🎉 Team created successfully!';
                    
                    // Clear draft
                    await this.clearDraft();
                    
                    // Clear auto-save timer
                    if (this.draftSaveTimer) {
                        clearInterval(this.draftSaveTimer);
                    }
                    
                    // Show success toast
                    this.showToast(`Team "${this.formData.name}" created successfully!`, 'success');
                    
                    // Redirect after delay
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 1500);
                } else {
                    // Error
                    loadingOverlay.classList.remove('active');
                    
                    if (data.errors) {
                        // Show form errors
                        this.showFormErrors(data.errors);
                        
                        // Go to error step
                        if (data.error_step) {
                            this.goToStep(data.error_step);
                        }
                    }
                    
                    this.showToast(data.error || 'Failed to create team. Please try again.', 'error');
                }
            } catch (error) {
                console.error('Form submission error:', error);
                loadingOverlay.classList.remove('active');
                this.showToast('Network error. Please check your connection and try again.', 'error');
            }
        }

        /**
         * Show form validation errors
         */
        showFormErrors(errors) {
            // Log errors for debugging
            console.error('Form errors:', errors);
            
            // Show first error in toast
            const firstError = Object.values(errors)[0];
            if (firstError && firstError[0]) {
                this.showToast(firstError[0], 'error');
            }
        }

        /* ================================================
           MODAL HANDLERS
           ================================================ */

        /**
         * Setup modal event handlers
         */
        setupModalHandlers() {
            // Draft modal
            const draftModal = document.getElementById('draftModal');
            const btnRestoreDraft = document.getElementById('btnRestoreDraft');
            const btnLoadDraft = document.getElementById('btnLoadDraft');
            
            // Close modal buttons
            document.querySelectorAll('[data-modal-close]').forEach(btn => {
                btn.addEventListener('click', () => {
                    draftModal.style.display = 'none';
                });
            });

            // Restore draft
            if (btnRestoreDraft) {
                btnRestoreDraft.addEventListener('click', () => {
                    this.restoreDraft();
                    draftModal.style.display = 'none';
                });
            }

            // Load draft from header
            if (btnLoadDraft) {
                btnLoadDraft.addEventListener('click', () => {
                    draftModal.style.display = 'flex';
                });
            }

            // Click outside to close
            draftModal.addEventListener('click', (e) => {
                if (e.target === draftModal || e.target.classList.contains('modal-overlay')) {
                    draftModal.style.display = 'none';
                }
            });
        }

        /* ================================================
           TOAST NOTIFICATIONS
           ================================================ */

        /**
         * Show toast notification
         */
        showToast(message, type = 'info') {
            const container = document.getElementById('toastContainer');
            
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            
            const iconMap = {
                success: 'fa-check-circle',
                error: 'fa-exclamation-circle',
                info: 'fa-info-circle',
                warning: 'fa-exclamation-triangle'
            };
            
            toast.innerHTML = `
                <div class="toast-icon">
                    <i class="fas ${iconMap[type] || iconMap.info}"></i>
                </div>
                <div class="toast-message">${message}</div>
                <button class="toast-close">
                    <i class="fas fa-times"></i>
                </button>
            `;
            
            // Close button
            toast.querySelector('.toast-close').addEventListener('click', () => {
                toast.remove();
            });
            
            container.appendChild(toast);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                toast.remove();
            }, 5000);
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            new TeamCreateWizard();
        });
    } else {
        new TeamCreateWizard();
    }

})();
