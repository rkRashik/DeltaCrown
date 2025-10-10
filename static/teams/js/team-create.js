/**
 * TEAM CREATE V2 - MODERN ESPORTS THEME
 * Main JavaScript for Team Creation Page
 * Mobile-First Responsive Design
 */

// Main App Object
const TeamCreateApp = {
    // State
    state: {
        currentStep: 1,
        totalSteps: 3,
        selectedGame: null,
        gameConfig: null,
        gameConfigs: {},
        invites: [],
        rosterOrder: [],
        formData: {},
        isDirty: false
    },

    // DOM Cache
    dom: {},

    // Initialize
    init() {
        this.cacheDom();
        this.bindEvents();
        this.loadGameConfigs();
        this.updateProgress();
        this.updatePreview();
        console.log('TeamCreateApp initialized');
    },

    // Cache DOM elements
    cacheDom() {
        this.dom = {
            // Progress
            progressSteps: document.querySelectorAll('.progress-step'),
            
            // Sections
            sections: document.querySelectorAll('.form-section'),
            
            // Buttons
            btnNext: document.querySelectorAll('.btn-next'),
            btnPrev: document.querySelectorAll('.btn-prev'),
            btnSubmit: document.getElementById('btn-submit'),
            
            // Team Info (Section 1)
            inputName: document.getElementById('id_name'),
            inputTag: document.getElementById('id_tag'),
            inputRegion: document.getElementById('id_region'),
            inputDescription: document.getElementById('id_description'),
            feedbackName: document.getElementById('name-feedback'),
            feedbackTag: document.getElementById('tag-feedback'),
            charCount: document.getElementById('char-count'),
            
            // Game Selection (Section 2)
            gameGrid: document.getElementById('game-grid'),
            gameSelect: document.getElementById('id_game'),
            gameInfoPanel: document.getElementById('game-info-panel'),
            rolesPreview: document.getElementById('roles-preview'),
            
            // Roster (Section 2)
            statStarters: document.getElementById('startersCount'),
            statSubs: document.getElementById('subsCount'),
            statInvites: document.getElementById('invitesCount'),
            statTotal: document.getElementById('totalRoster'),
            invitesList: document.getElementById('invitesList'),
            btnAddInvite: document.getElementById('addInviteBtn'),
            
            // Media (Section 3)
            inputLogo: document.getElementById('id_logo'),
            inputBanner: document.getElementById('id_banner_image'),
            logoPreview: document.getElementById('logoPreview'),
            bannerPreview: document.getElementById('bannerPreview'),
            btnUploadLogo: document.getElementById('btn-upload-logo'),
            btnUploadBanner: document.getElementById('btn-upload-banner'),
            
            // Social Links
            optionalToggle: document.getElementById('optional-toggle'),
            socialLinksContent: document.getElementById('socialLinks'),
            
            // Preview
            previewName: document.getElementById('previewName'),
            previewTag: document.getElementById('previewTag'),
            previewGame: document.getElementById('previewGame'),
            previewRegion: document.getElementById('previewRegion'),
            previewDescription: document.getElementById('previewDescription'),
            previewLogo: document.getElementById('previewLogo'),
            previewBanner: document.getElementById('previewBanner'),
            previewSocials: document.getElementById('previewSocials'),
            previewRosterList: document.getElementById('previewRosterList'),
            
            // Modal
            helpBtn: document.querySelector('.help-btn'),
            helpModal: document.getElementById('help-modal'),
            modalClose: document.querySelector('.modal-close'),
            modalOverlay: document.querySelector('.modal-overlay'),
            
            // Mobile Preview
            mobilePreviewBtn: document.querySelector('.mobile-preview-toggle'),
            
            // Form
            form: document.getElementById('team-create-form')
        };
    },

    // Bind Events
    bindEvents() {
        // Navigation
        this.dom.btnNext.forEach(btn => {
            btn.addEventListener('click', () => this.nextStep());
        });
        this.dom.btnPrev.forEach(btn => {
            btn.addEventListener('click', () => this.prevStep());
        });
        this.dom.progressSteps.forEach((step, index) => {
            step.addEventListener('click', () => this.goToStep(index + 1));
        });

        // Team Info Validation
        if (this.dom.inputName) {
            this.dom.inputName.addEventListener('input', this.debounce(() => {
                this.validateName();
                this.updatePreview();
            }, 500));
        }
        
        if (this.dom.inputTag) {
            this.dom.inputTag.addEventListener('input', (e) => {
                // Auto-uppercase
                e.target.value = e.target.value.toUpperCase();
                this.debounce(() => {
                    this.validateTag();
                    this.updatePreview();
                }, 500)();
            });
        }

        if (this.dom.inputDescription) {
            this.dom.inputDescription.addEventListener('input', () => {
                this.updateCharCount();
                this.updatePreview();
            });
        }

        if (this.dom.inputRegion) {
            this.dom.inputRegion.addEventListener('change', () => {
                this.updatePreview();
            });
        }

        // Roster Management
        if (this.dom.btnAddInvite) {
            this.dom.btnAddInvite.addEventListener('click', () => this.addInvite());
        }

        // Media Uploads
        if (this.dom.btnUploadLogo) {
            this.dom.btnUploadLogo.addEventListener('click', () => {
                this.dom.inputLogo.click();
            });
        }
        
        if (this.dom.btnUploadBanner) {
            this.dom.btnUploadBanner.addEventListener('click', () => {
                this.dom.inputBanner.click();
            });
        }

        if (this.dom.inputLogo) {
            this.dom.inputLogo.addEventListener('change', (e) => {
                this.handleLogoUpload(e);
            });
        }

        if (this.dom.inputBanner) {
            this.dom.inputBanner.addEventListener('change', (e) => {
                this.handleBannerUpload(e);
            });
        }

        // Optional Section Toggle
        if (this.dom.optionalToggle) {
            this.dom.optionalToggle.addEventListener('click', () => {
                this.toggleOptionalSection();
            });
        }

        // Social Links
        const socialInputs = ['twitter', 'instagram', 'discord', 'youtube', 'twitch', 'linktree'];
        socialInputs.forEach(social => {
            const input = document.getElementById(`id_${social}`);
            if (input) {
                input.addEventListener('input', () => {
                    this.updatePreviewSocials();
                });
            }
        });

        // Help Modal
        if (this.dom.helpBtn) {
            this.dom.helpBtn.addEventListener('click', () => this.showHelpModal());
        }
        if (this.dom.modalClose) {
            this.dom.modalClose.addEventListener('click', () => this.closeModal());
        }
        if (this.dom.modalOverlay) {
            this.dom.modalOverlay.addEventListener('click', () => this.closeModal());
        }

        // Form Submit
        if (this.dom.form) {
            this.dom.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        // Mobile Preview Toggle
        if (this.dom.mobilePreviewBtn) {
            this.dom.mobilePreviewBtn.addEventListener('click', () => {
                this.toggleMobilePreview();
            });
        }

        // Warn before leaving if form is dirty
        window.addEventListener('beforeunload', (e) => {
            if (this.state.isDirty) {
                e.preventDefault();
                e.returnValue = '';
            }
        });

        // Mark form as dirty on any input
        if (this.dom.form) {
            this.dom.form.addEventListener('input', () => {
                this.state.isDirty = true;
            });
        }
    },

    // Navigation Functions
    nextStep() {
        if (!this.validateCurrentStep()) {
            return;
        }
        
        if (this.state.currentStep < this.state.totalSteps) {
            this.state.currentStep++;
            this.updateProgress();
            this.scrollToTop();
        }
    },

    prevStep() {
        if (this.state.currentStep > 1) {
            this.state.currentStep--;
            this.updateProgress();
            this.scrollToTop();
        }
    },

    goToStep(step) {
        if (step >= 1 && step <= this.state.totalSteps) {
            // Only allow going forward if previous steps are valid
            if (step > this.state.currentStep) {
                for (let i = this.state.currentStep; i < step; i++) {
                    if (!this.validateStep(i)) {
                        this.showError(`Please complete Step ${i} first.`);
                        return;
                    }
                }
            }
            this.state.currentStep = step;
            this.updateProgress();
            this.scrollToTop();
        }
    },

    updateProgress() {
        // Update step indicators
        this.dom.progressSteps.forEach((step, index) => {
            const stepNum = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNum === this.state.currentStep) {
                step.classList.add('active');
            } else if (stepNum < this.state.currentStep) {
                step.classList.add('completed');
            }
        });

        // Show/hide sections
        this.dom.sections.forEach((section, index) => {
            const stepNum = index + 1;
            section.classList.toggle('active', stepNum === this.state.currentStep);
        });
    },

    scrollToTop() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    // Validation Functions
    validateCurrentStep() {
        return this.validateStep(this.state.currentStep);
    },

    validateStep(step) {
        switch(step) {
            case 1:
                return this.validateTeamInfo();
            case 2:
                return this.validateGameSelection();
            case 3:
                return this.validateRoster();
            case 4:
                return true; // Media is optional
            default:
                return true;
        }
    },

    validateTeamInfo() {
        const name = this.dom.inputName?.value.trim();
        const tag = this.dom.inputTag?.value.trim();

        if (!name || name.length < 3) {
            this.showError('Team name must be at least 3 characters.');
            return false;
        }

        if (!tag || tag.length < 2) {
            this.showError('Team tag must be at least 2 characters.');
            return false;
        }

        return true;
    },

    validateGameSelection() {
        if (!this.state.selectedGame) {
            this.showError('Please select a game for your team.');
            return false;
        }
        return true;
    },

    validateRoster() {
        // Roster is optional for creation
        return true;
    },

    async validateName() {
        const name = this.dom.inputName.value.trim();
        
        if (!name) {
            this.dom.feedbackName.textContent = '';
            this.dom.feedbackName.className = 'validation-feedback';
            return;
        }

        if (name.length < 3) {
            this.dom.feedbackName.textContent = 'Name must be at least 3 characters';
            this.dom.feedbackName.className = 'validation-feedback invalid';
            return;
        }

        try {
            this.dom.feedbackName.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Checking...';
            this.dom.feedbackName.className = 'validation-feedback';

            const response = await fetch(`/teams/api/validate-name/?name=${encodeURIComponent(name)}`);
            const data = await response.json();

            if (data.valid) {
                this.dom.feedbackName.innerHTML = '<i class="fa fa-check"></i> Name available';
                this.dom.feedbackName.className = 'validation-feedback valid';
            } else {
                this.dom.feedbackName.innerHTML = '<i class="fa fa-times"></i> ' + data.message;
                this.dom.feedbackName.className = 'validation-feedback invalid';
            }
        } catch (error) {
            console.error('Name validation error:', error);
            this.dom.feedbackName.textContent = '';
            this.dom.feedbackName.className = 'validation-feedback';
        }
    },

    async validateTag() {
        const tag = this.dom.inputTag.value.trim();
        
        if (!tag) {
            this.dom.feedbackTag.textContent = '';
            this.dom.feedbackTag.className = 'validation-feedback';
            return;
        }

        if (tag.length < 2) {
            this.dom.feedbackTag.textContent = 'Tag must be at least 2 characters';
            this.dom.feedbackTag.className = 'validation-feedback invalid';
            return;
        }

        try {
            this.dom.feedbackTag.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Checking...';
            this.dom.feedbackTag.className = 'validation-feedback';

            const response = await fetch(`/teams/api/validate-tag/?tag=${encodeURIComponent(tag)}`);
            const data = await response.json();

            if (data.valid) {
                this.dom.feedbackTag.innerHTML = '<i class="fa fa-check"></i> Tag available';
                this.dom.feedbackTag.className = 'validation-feedback valid';
            } else {
                this.dom.feedbackTag.innerHTML = '<i class="fa fa-times"></i> ' + data.message;
                this.dom.feedbackTag.className = 'validation-feedback invalid';
            }
        } catch (error) {
            console.error('Tag validation error:', error);
            this.dom.feedbackTag.textContent = '';
            this.dom.feedbackTag.className = 'validation-feedback';
        }
    },

    updateCharCount() {
        if (this.dom.inputDescription && this.dom.charCount) {
            const length = this.dom.inputDescription.value.length;
            const max = 500;
            this.dom.charCount.textContent = `${length}/${max}`;
            
            if (length > max) {
                this.dom.charCount.style.color = 'var(--accent-danger)';
            } else {
                this.dom.charCount.style.color = 'var(--text-dim)';
            }
        }
    },

    // Game Functions
    loadGameConfigs() {
        try {
            // Try to get from window.GAME_CONFIGS (passed from Django template)
            if (window.GAME_CONFIGS) {
                this.state.gameConfigs = window.GAME_CONFIGS;
                this.setupGameDropdown();
                return;
            }
            
            // Fallback: Try to get from script tag
            const configElement = document.getElementById('game-configs');
            if (configElement) {
                const configs = JSON.parse(configElement.textContent);
                this.state.gameConfigs = configs;
                this.setupGameDropdown();
            }
        } catch (error) {
            console.error('Error loading game configs:', error);
        }
    },

    setupGameDropdown() {
        // Setup game dropdown change listener
        if (this.dom.gameSelect) {
            this.dom.gameSelect.addEventListener('change', (e) => this.handleGameChange(e));
            
            // If there's a preselected game, load its regions
            if (this.dom.gameSelect.value) {
                this.handleGameChange({ target: this.dom.gameSelect });
            }
        }
    },

    handleGameChange(event) {
        const gameCode = event.target.value;
        
        if (!gameCode) {
            this.state.selectedGame = null;
            this.state.gameConfig = null;
            this.updateRegionOptions(null);
            return;
        }

        this.state.selectedGame = gameCode;
        this.state.gameConfig = this.state.gameConfigs[gameCode];
        
        // Update region dropdown with game-specific regions
        this.updateRegionOptions(gameCode);
        
        // Update game info panel
        this.updateGameInfo();
        
        // Update role dropdowns for roster
        this.updateRoleDropdowns();
        
        // Update preview
        this.updatePreview();
    },

    updateRegionOptions(gameCode) {
        const regionSelect = document.getElementById('id_region');
        if (!regionSelect) return;

        // Clear existing options
        regionSelect.innerHTML = '<option value="">Select region...</option>';

        // If no game selected, leave it empty
        if (!gameCode || !this.state.gameConfigs[gameCode]) {
            regionSelect.disabled = true;
            return;
        }

        // Enable and populate with game-specific regions
        regionSelect.disabled = false;
        const regions = this.state.gameConfigs[gameCode].regions || [];
        
        regions.forEach(([code, name]) => {
            const option = document.createElement('option');
            option.value = code;
            option.textContent = name;
            regionSelect.appendChild(option);
        });
    },

    updateGameInfo() {
        if (!this.state.gameConfig) {
            if (this.dom.gameInfoPanel) {
                this.dom.gameInfoPanel.style.display = 'none';
            }
            return;
        }

        const config = this.state.gameConfig;
        
        if (this.dom.gameInfoPanel) {
            this.dom.gameInfoPanel.style.display = 'block';
            
            // Update game info text
            const gameInfoTitle = document.getElementById('gameInfoTitle');
            const gameInfoText = document.getElementById('gameInfoText');
            
            if (gameInfoTitle) {
                gameInfoTitle.textContent = config.name;
            }
            
            if (gameInfoText) {
                gameInfoText.textContent = `Team size: ${config.roster.min}-${config.roster.max} players`;
            }
        }

        // Update roles preview
        if (this.dom.rolesPreview) {
            this.dom.rolesPreview.innerHTML = '';
            config.roles.forEach(role => {
                const badge = document.createElement('span');
                badge.className = 'role-badge';
                badge.textContent = role;
                this.dom.rolesPreview.appendChild(badge);
            });
        }
    },

    updateRoleDropdowns() {
        if (!this.state.gameConfig) return;

        const roleSelects = document.querySelectorAll('.invite-role-select');
        roleSelects.forEach(select => {
            select.innerHTML = '<option value="">Select Role</option>';
            this.state.gameConfig.roles.forEach(role => {
                const option = document.createElement('option');
                option.value = role;
                option.textContent = role;
                select.appendChild(option);
            });
        });
    },

    // Roster Functions
    addInvite() {
        const id = Date.now();
        const invite = {
            id: id,
            identifier: '',
            role: '',
            is_sub: false
        };

        this.state.invites.push(invite);
        this.renderInviteCard(invite);
        this.updateRosterStats();
    },

    renderInviteCard(invite) {
        const card = document.createElement('div');
        card.className = 'invite-card';
        card.dataset.inviteId = invite.id;

        const roles = this.state.gameConfig ? this.state.gameConfig.roles : [];
        const roleOptions = roles.map(role => 
            `<option value="${role}" ${invite.role === role ? 'selected' : ''}>${role}</option>`
        ).join('');

        card.innerHTML = `
            <div class="invite-card-header">
                <span class="drag-handle"><i class="fa fa-grip-vertical"></i></span>
            </div>
            <div class="invite-card-body">
                <div class="form-group">
                    <input type="text" 
                           class="invite-identifier" 
                           placeholder="Username or Email"
                           value="${invite.identifier}"
                           data-invite-id="${invite.id}">
                </div>
                <div class="form-group">
                    <select class="invite-role-select" data-invite-id="${invite.id}">
                        <option value="">Select Role</option>
                        ${roleOptions}
                    </select>
                </div>
                <button type="button" class="btn-remove" data-invite-id="${invite.id}">
                    <i class="fa fa-times"></i>
                </button>
            </div>
            <label class="sub-toggle">
                <input type="checkbox" 
                       class="invite-sub-check" 
                       data-invite-id="${invite.id}"
                       ${invite.is_sub ? 'checked' : ''}>
                <span>Mark as Substitute</span>
            </label>
        `;

        // Bind events
        const identifierInput = card.querySelector('.invite-identifier');
        identifierInput.addEventListener('input', (e) => {
            this.updateInvite(invite.id, 'identifier', e.target.value);
        });

        const roleSelect = card.querySelector('.invite-role-select');
        roleSelect.addEventListener('change', (e) => {
            this.updateInvite(invite.id, 'role', e.target.value);
        });

        const subCheck = card.querySelector('.invite-sub-check');
        subCheck.addEventListener('change', (e) => {
            this.updateInvite(invite.id, 'is_sub', e.target.checked);
            this.updateRosterStats();
        });

        const removeBtn = card.querySelector('.btn-remove');
        removeBtn.addEventListener('click', () => {
            this.removeInvite(invite.id);
        });

        this.dom.invitesList.appendChild(card);
    },

    updateInvite(id, field, value) {
        const invite = this.state.invites.find(inv => inv.id === id);
        if (invite) {
            invite[field] = value;
            this.updatePreviewRoster();
        }
    },

    removeInvite(id) {
        const index = this.state.invites.findIndex(inv => inv.id === id);
        if (index !== -1) {
            this.state.invites.splice(index, 1);
            
            const card = document.querySelector(`[data-invite-id="${id}"]`);
            if (card) {
                card.remove();
            }
            
            this.updateRosterStats();
            this.updatePreviewRoster();
        }
    },

    updateRosterStats() {
        const starters = this.state.invites.filter(inv => !inv.is_sub).length;
        const subs = this.state.invites.filter(inv => inv.is_sub).length;
        const total = starters + subs + 1; // +1 for captain

        if (this.dom.statStarters) this.dom.statStarters.textContent = starters;
        if (this.dom.statSubs) this.dom.statSubs.textContent = subs;
        if (this.dom.statInvites) this.dom.statInvites.textContent = this.state.invites.length;
        if (this.dom.statTotal) this.dom.statTotal.textContent = total;
    },

    // Media Functions
    handleLogoUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        if (!this.validateImage(file, 2)) return;

        // Update both the upload preview and the team card preview
        this.previewImage(file, this.dom.logoPreview);
        this.previewImage(file, this.dom.previewLogo);
    },

    handleBannerUpload(e) {
        const file = e.target.files[0];
        if (!file) return;

        if (!this.validateImage(file, 2)) return;

        // Update both the upload preview and the team card preview
        const reader = new FileReader();
        reader.onload = (e) => {
            // Update banner preview in upload area
            if (this.dom.bannerPreview) {
                let img = this.dom.bannerPreview.querySelector('img');
                if (!img) {
                    img = document.createElement('img');
                    this.dom.bannerPreview.innerHTML = '';
                    this.dom.bannerPreview.appendChild(img);
                }
                img.src = e.target.result;
            }
            
            // Update team card preview banner
            if (this.dom.previewBanner) {
                this.dom.previewBanner.style.backgroundImage = `url(${e.target.result})`;
            }
        };
        reader.readAsDataURL(file);
    },

    validateImage(file, maxSizeMB) {
        const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
        
        if (!validTypes.includes(file.type)) {
            this.showError('Please upload a valid image (JPG, PNG, GIF, or WebP)');
            return false;
        }

        const maxSize = maxSizeMB * 1024 * 1024;
        if (file.size > maxSize) {
            this.showError(`Image must be under ${maxSizeMB}MB`);
            return false;
        }

        return true;
    },

    previewImage(file, container) {
        if (!container) return;
        
        const reader = new FileReader();
        
        reader.onload = (e) => {
            let img = container.querySelector('img');
            if (!img) {
                img = document.createElement('img');
                container.innerHTML = '';
                container.appendChild(img);
            }
            img.src = e.target.result;
        };

        reader.readAsDataURL(file);
    },

    toggleOptionalSection() {
        if (this.dom.socialLinksContent) {
            const isHidden = this.dom.socialLinksContent.style.display === 'none';
            this.dom.socialLinksContent.style.display = isHidden ? 'block' : 'none';
            
            // Toggle icon rotation
            if (this.dom.optionalToggle) {
                const icon = this.dom.optionalToggle.querySelector('.toggle-icon');
                if (icon) {
                    icon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
                }
            }
        }
    },

    // Preview Functions
    updatePreview() {
        this.updatePreviewName();
        this.updatePreviewMeta();
        this.updatePreviewDescription();
        this.updatePreviewSocials();
        this.updatePreviewRoster();
    },

    updatePreviewName() {
        const name = this.dom.inputName?.value.trim() || 'Your Team Name';
        const tag = this.dom.inputTag?.value.trim() || 'TAG';

        if (this.dom.previewName) {
            this.dom.previewName.textContent = name;
        }
        if (this.dom.previewTag) {
            this.dom.previewTag.textContent = `[${tag}]`;
        }
    },

    updatePreviewMeta() {
        const gameName = this.state.gameConfig ? this.state.gameConfig.name : 'Select a game';
        const region = this.dom.inputRegion?.value || 'No region';

        if (this.dom.previewGame) {
            this.dom.previewGame.textContent = gameName;
        }
        if (this.dom.previewRegion) {
            this.dom.previewRegion.textContent = region || 'No region';
        }
    },

    updatePreviewDescription() {
        const description = this.dom.inputDescription?.value.trim() || 'Add a team description...';
        if (this.dom.previewDescription) {
            this.dom.previewDescription.textContent = description;
        }
    },

    updatePreviewSocials() {
        if (!this.dom.previewSocials) return;

        const socials = [
            { id: 'twitter', icon: 'fa-twitter' },
            { id: 'instagram', icon: 'fa-instagram' },
            { id: 'discord', icon: 'fa-discord' },
            { id: 'youtube', icon: 'fa-youtube' },
            { id: 'twitch', icon: 'fa-twitch' },
            { id: 'linktree', icon: 'fa-link' }
        ];

        this.dom.previewSocials.innerHTML = '';

        socials.forEach(social => {
            const input = document.getElementById(`id_${social.id}`);
            if (input && input.value.trim()) {
                const icon = document.createElement('a');
                icon.className = 'social-icon';
                icon.href = input.value;
                icon.target = '_blank';
                icon.innerHTML = `<i class="fab ${social.icon}"></i>`;
                this.dom.previewSocials.appendChild(icon);
            }
        });
    },

    updatePreviewRoster() {
        if (!this.dom.previewRosterList) return;

        this.dom.previewRosterList.innerHTML = '';

        // Add captain
        const captainData = document.querySelector('.captain-card');
        if (captainData) {
            const captainName = captainData.querySelector('.player-name')?.textContent || 'You';
            const captainAvatar = captainData.querySelector('.player-avatar img')?.src || '';
            
            const captainMember = this.createRosterMember(captainName, 'Captain', captainAvatar, true);
            this.dom.previewRosterList.appendChild(captainMember);
        }

        // Add invites
        this.state.invites.forEach(invite => {
            if (invite.identifier) {
                const role = invite.role || 'Player';
                const subLabel = invite.is_sub ? ' (Sub)' : '';
                const member = this.createRosterMember(invite.identifier, role + subLabel, '', false);
                this.dom.previewRosterList.appendChild(member);
            }
        });
    },

    createRosterMember(name, role, avatarSrc, isCaptain) {
        const member = document.createElement('div');
        member.className = 'roster-member' + (isCaptain ? ' captain' : '');

        const avatarHTML = avatarSrc 
            ? `<img src="${avatarSrc}" alt="${name}">`
            : `<div class="avatar-placeholder"><i class="fa fa-user"></i></div>`;

        member.innerHTML = `
            <div class="member-avatar">${avatarHTML}</div>
            <div class="member-info">
                <div class="member-name">${name}</div>
                <div class="member-role">
                    ${isCaptain ? '<i class="fa fa-crown"></i>' : '<i class="fa fa-user"></i>'}
                    ${role}
                </div>
            </div>
        `;

        return member;
    },

    // Modal Functions
    showHelpModal() {
        if (this.dom.helpModal) {
            this.dom.helpModal.style.display = 'flex';
        }
    },

    closeModal() {
        if (this.dom.helpModal) {
            this.dom.helpModal.style.display = 'none';
        }
    },

    // Mobile Preview
    toggleMobilePreview() {
        const previewCol = document.querySelector('.preview-column');
        if (previewCol) {
            previewCol.classList.toggle('mobile-visible');
            
            if (previewCol.classList.contains('mobile-visible')) {
                previewCol.style.display = 'block';
                previewCol.style.position = 'fixed';
                previewCol.style.top = '0';
                previewCol.style.left = '0';
                previewCol.style.right = '0';
                previewCol.style.bottom = '0';
                previewCol.style.zIndex = '1100';
                previewCol.style.background = 'var(--bg-primary)';
                previewCol.style.padding = 'var(--space-lg)';
                previewCol.style.overflowY = 'auto';

                // Show close button
                const closeBtn = previewCol.querySelector('.preview-close');
                if (closeBtn) {
                    closeBtn.style.display = 'flex';
                    closeBtn.onclick = () => this.toggleMobilePreview();
                }
            } else {
                previewCol.style.display = '';
                previewCol.style.position = '';
                previewCol.style.top = '';
                previewCol.style.left = '';
                previewCol.style.right = '';
                previewCol.style.bottom = '';
                previewCol.style.zIndex = '';
                previewCol.style.background = '';
                previewCol.style.padding = '';
                previewCol.style.overflowY = '';

                const closeBtn = previewCol.querySelector('.preview-close');
                if (closeBtn) {
                    closeBtn.style.display = 'none';
                }
            }
        }
    },
    // Form Submission
    async handleSubmit(e) {
        e.preventDefault();

        // Final validation
        if (!this.validateForm()) {
            return;
        }

        // Mark form as clean to prevent "unsaved changes" warning
        this.state.isDirty = false;

        // Prepare roster data
        const rosterData = this.state.invites.map((invite, index) => ({
            identifier: invite.identifier,
            role: invite.role,
            is_sub: invite.is_sub,
            order: index
        }));

        // Add roster data to form
        const rosterInput = document.createElement('input');
        rosterInput.type = 'hidden';
        rosterInput.name = 'roster_data';
        rosterInput.value = JSON.stringify(rosterData);
        this.dom.form.appendChild(rosterInput);

        // Show loading
        this.showLoading();

        // Submit form
        try {
            this.dom.form.submit();
        } catch (error) {
            console.error('Submit error:', error);
            this.hideLoading();
            this.showError('An error occurred. Please try again.');
        }
    },

    validateForm() {
        for (let i = 1; i <= this.state.totalSteps; i++) {
            if (!this.validateStep(i)) {
                this.goToStep(i);
                return false;
            }
        }
        return true;
    },

    showLoading() {
        if (this.dom.btnSubmit) {
            this.dom.btnSubmit.disabled = true;
            this.dom.btnSubmit.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Creating Team...';
        }
    },

    hideLoading() {
        if (this.dom.btnSubmit) {
            this.dom.btnSubmit.disabled = false;
            this.dom.btnSubmit.innerHTML = '<i class="fa fa-check"></i> Create Team';
        }
    },

    // Utility Functions
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
    },

    showError(message) {
        // Create alert
        const messagesContainer = document.querySelector('.messages-container');
        if (!messagesContainer) return;

        const alert = document.createElement('div');
        alert.className = 'alert alert-error';
        alert.innerHTML = `
            <i class="fa fa-exclamation-circle"></i>
            <span>${message}</span>
            <button class="close-alert"><i class="fa fa-times"></i></button>
        `;

        const closeBtn = alert.querySelector('.close-alert');
        closeBtn.addEventListener('click', () => alert.remove());

        messagesContainer.appendChild(alert);

        // Auto-remove after 5 seconds
        setTimeout(() => alert.remove(), 5000);
    },

    showSuccess(message) {
        // Create alert
        const messagesContainer = document.querySelector('.messages-container');
        if (!messagesContainer) return;

        const alert = document.createElement('div');
        alert.className = 'alert alert-success';
        alert.innerHTML = `
            <i class="fa fa-check-circle"></i>
            <span>${message}</span>
            <button class="close-alert"><i class="fa fa-times"></i></button>
        `;

        const closeBtn = alert.querySelector('.close-alert');
        closeBtn.addEventListener('click', () => alert.remove());

        messagesContainer.appendChild(alert);

        // Auto-remove after 5 seconds
        setTimeout(() => alert.remove(), 5000);
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => TeamCreateApp.init());
} else {
    TeamCreateApp.init();
}

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TeamCreateApp;
}
