/**
 * TEAM CREATE - ENHANCED JAVASCRIPT
 * Separated JS file for better maintainability
 */

console.log('[TeamCreateEnhanced] Script loaded');

// Game ID configurations for all supported games
const GAME_ID_CONFIGS = {
    'valorant': {
        title: 'Enter Your Riot ID',
        fields: [
            { 
                name: 'riot_id', 
                label: 'Riot ID', 
                placeholder: 'YourName#TAG', 
                type: 'text', 
                required: true,
                help: 'Example: Shroud#NA1'
            }
        ]
    },
    'efootball': {
        title: 'Enter Your eFootball User ID',
        fields: [
            { 
                name: 'efootball_id', 
                label: 'User ID', 
                placeholder: 'Your eFootball User ID', 
                type: 'text', 
                required: true 
            }
        ]
    },
    'dota2': {
        title: 'Enter Your Steam ID',
        fields: [
            { 
                name: 'steam_id', 
                label: 'Steam ID', 
                placeholder: 'Your Steam ID', 
                type: 'text', 
                required: true,
                help: 'Example: 76561198123456789'
            }
        ]
    },
    'cs2': {
        title: 'Enter Your Steam ID',
        fields: [
            { 
                name: 'steam_id', 
                label: 'Steam ID', 
                placeholder: 'Your Steam ID', 
                type: 'text', 
                required: true,
                help: 'Example: 76561198123456789'
            }
        ]
    },
    'csgo': {
        title: 'Enter Your Steam ID',
        fields: [
            { 
                name: 'steam_id', 
                label: 'Steam ID', 
                placeholder: 'Your Steam ID', 
                type: 'text', 
                required: true,
                help: 'Example: 76561198123456789'
            }
        ]
    },
    'mlbb': {
        title: 'Enter Your Mobile Legends ID',
        fields: [
            { 
                name: 'mlbb_id', 
                label: 'Game ID', 
                placeholder: 'Your MLBB Game ID', 
                type: 'text', 
                required: true 
            },
            { 
                name: 'mlbb_server_id', 
                label: 'Server ID', 
                placeholder: 'Server ID', 
                type: 'text', 
                required: true 
            }
        ]
    },
    'pubg': {
        title: 'Enter Your PUBG Mobile Character ID',
        fields: [
            { 
                name: 'pubg_mobile_id', 
                label: 'Character ID', 
                placeholder: 'Your Character ID', 
                type: 'text', 
                required: true 
            }
        ]
    },
    'pubg_mobile': {
        title: 'Enter Your PUBG Mobile Character ID',
        fields: [
            { 
                name: 'pubg_mobile_id', 
                label: 'Character ID', 
                placeholder: 'Your Character ID', 
                type: 'text', 
                required: true 
            }
        ]
    },
    'free_fire': {
        title: 'Enter Your Free Fire Player ID',
        fields: [
            { 
                name: 'free_fire_id', 
                label: 'Player ID', 
                placeholder: 'Your Player ID', 
                type: 'text', 
                required: true 
            }
        ]
    },
    'fc24': {
        title: 'Enter Your EA ID',
        fields: [
            { 
                name: 'ea_id', 
                label: 'EA ID', 
                placeholder: 'Your EA ID', 
                type: 'text', 
                required: true 
            }
        ]
    },
    'codm': {
        title: 'Enter Your Call of Duty Mobile UID',
        fields: [
            { 
                name: 'codm_uid', 
                label: 'UID', 
                placeholder: 'Your UID', 
                type: 'text', 
                required: true 
            }
        ]
    }
};

// Application state
const TeamCreateApp = {
    // DOM Elements
    dom: {
        form: null,
        gameSelect: null,
        nameInput: null,
        tagInput: null,
        nameFeedback: null,
        tagFeedback: null,
        submitBtn: null,
        loadingOverlay: null,
        gameIdSection: null,
        gameIdTitle: null,
        gameIdFields: null,
        existingTeamWarning: null,
        existingTeamInfo: null
    },

    // State
    state: {
        nameValidTimer: null,
        tagValidTimer: null,
        currentGame: null,
        hasExistingTeam: false,
        gameIdData: {}
    },

    // Initialize
    init() {
        console.log('[TeamCreateEnhanced] Initializing...');
        this.cacheDom();
        this.bindEvents();
        console.log('[TeamCreateEnhanced] Initialized successfully');
    },

    // Cache DOM elements
    cacheDom() {
        this.dom.form = document.getElementById('team-create-form');
        this.dom.gameSelect = document.getElementById('id_game');
        this.dom.nameInput = document.getElementById('id_name');
        this.dom.tagInput = document.getElementById('id_tag');
        this.dom.nameFeedback = document.getElementById('name-feedback');
        this.dom.tagFeedback = document.getElementById('tag-feedback');
        this.dom.submitBtn = document.getElementById('submit-btn');
        this.dom.loadingOverlay = document.getElementById('loading-overlay');
        this.dom.gameIdSection = document.getElementById('game-id-section');
        this.dom.gameIdTitle = document.getElementById('game-id-title');
        this.dom.gameIdFields = document.getElementById('game-id-fields');
        this.dom.existingTeamWarning = document.getElementById('existing-team-warning');
        this.dom.existingTeamInfo = document.getElementById('existing-team-info');

        console.log('[TeamCreateEnhanced] DOM elements cached:', {
            form: !!this.dom.form,
            gameSelect: !!this.dom.gameSelect,
            nameInput: !!this.dom.nameInput,
            tagInput: !!this.dom.tagInput
        });
    },

    // Bind events
    bindEvents() {
        if (this.dom.nameInput) {
            this.dom.nameInput.addEventListener('input', () => this.validateName());
        }

        if (this.dom.tagInput) {
            this.dom.tagInput.addEventListener('input', () => this.validateTag());
        }

        if (this.dom.gameSelect) {
            this.dom.gameSelect.addEventListener('change', (e) => this.handleGameChange(e));
        }

        if (this.dom.form) {
            this.dom.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }

        console.log('[TeamCreateEnhanced] Events bound');
    },

    // ========== NAME VALIDATION ==========
    async validateName() {
        clearTimeout(this.state.nameValidTimer);
        const name = this.dom.nameInput.value.trim();
        
        if (!name || name.length < 3) {
            this.dom.nameFeedback.textContent = name ? 'Name must be at least 3 characters' : '';
            this.dom.nameFeedback.className = 'validation-feedback';
            this.dom.nameInput.classList.remove('is-valid', 'is-invalid');
            return;
        }

        this.dom.nameFeedback.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking availability...';
        this.dom.nameFeedback.className = 'validation-feedback checking';

        this.state.nameValidTimer = setTimeout(async () => {
            try {
                console.log('[TeamCreateEnhanced] Validating name:', name);
                const response = await fetch(`/teams/api/validate-name/?name=${encodeURIComponent(name)}`);
                const data = await response.json();

                console.log('[TeamCreateEnhanced] Name validation result:', data);

                if (data.valid) {
                    this.dom.nameFeedback.innerHTML = '<i class="fas fa-check"></i> Name available';
                    this.dom.nameFeedback.className = 'validation-feedback valid';
                    this.dom.nameInput.classList.remove('is-invalid');
                    this.dom.nameInput.classList.add('is-valid');
                } else {
                    this.dom.nameFeedback.innerHTML = '<i class="fas fa-times"></i> ' + data.message;
                    this.dom.nameFeedback.className = 'validation-feedback invalid';
                    this.dom.nameInput.classList.remove('is-valid');
                    this.dom.nameInput.classList.add('is-invalid');
                }
            } catch (error) {
                console.error('[TeamCreateEnhanced] Name validation error:', error);
                this.dom.nameFeedback.textContent = '';
                this.dom.nameFeedback.className = 'validation-feedback';
                this.dom.nameInput.classList.remove('is-valid', 'is-invalid');
            }
        }, 600);
    },

    // ========== TAG VALIDATION ==========
    async validateTag() {
        clearTimeout(this.state.tagValidTimer);
        const tag = this.dom.tagInput.value.trim();
        
        if (!tag || tag.length < 2) {
            this.dom.tagFeedback.textContent = tag ? 'Tag must be at least 2 characters' : '';
            this.dom.tagFeedback.className = 'validation-feedback';
            this.dom.tagInput.classList.remove('is-valid', 'is-invalid');
            return;
        }

        this.dom.tagFeedback.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking availability...';
        this.dom.tagFeedback.className = 'validation-feedback checking';

        this.state.tagValidTimer = setTimeout(async () => {
            try {
                console.log('[TeamCreateEnhanced] Validating tag:', tag);
                const response = await fetch(`/teams/api/validate-tag/?tag=${encodeURIComponent(tag)}`);
                const data = await response.json();

                console.log('[TeamCreateEnhanced] Tag validation result:', data);

                if (data.valid) {
                    this.dom.tagFeedback.innerHTML = '<i class="fas fa-check"></i> Tag available';
                    this.dom.tagFeedback.className = 'validation-feedback valid';
                    this.dom.tagInput.classList.remove('is-invalid');
                    this.dom.tagInput.classList.add('is-valid');
                } else {
                    this.dom.tagFeedback.innerHTML = '<i class="fas fa-times"></i> ' + data.message;
                    this.dom.tagFeedback.className = 'validation-feedback invalid';
                    this.dom.tagInput.classList.remove('is-valid');
                    this.dom.tagInput.classList.add('is-invalid');
                }
            } catch (error) {
                console.error('[TeamCreateEnhanced] Tag validation error:', error);
                this.dom.tagFeedback.textContent = '';
                this.dom.tagFeedback.className = 'validation-feedback';
                this.dom.tagInput.classList.remove('is-valid', 'is-invalid');
            }
        }, 600);
    },

    // ========== GAME CHANGE HANDLER ==========
    async handleGameChange(event) {
        const gameCode = event.target.value;
        console.log('[TeamCreateEnhanced] Game changed to:', gameCode);

        // Reset states
        this.dom.gameIdSection.classList.remove('show');
        this.dom.existingTeamWarning.classList.remove('show');
        this.state.hasExistingTeam = false;
        this.state.gameIdData = {};

        if (!gameCode) {
            this.state.currentGame = null;
            this.dom.submitBtn.disabled = false;
            return;
        }

        this.state.currentGame = gameCode;

        // 1. Check if user already has a team for this game
        await this.checkExistingTeam(gameCode);

        // 2. If no existing team, load game ID fields
        if (!this.state.hasExistingTeam) {
            await this.loadGameIdFields(gameCode);
        }
    },

    // ========== CHECK EXISTING TEAM ==========
    async checkExistingTeam(gameCode) {
        try {
            console.log('[TeamCreateEnhanced] Checking for existing team...');
            const response = await fetch(`/teams/api/check-existing-team/?game=${gameCode}`);
            const data = await response.json();

            console.log('[TeamCreateEnhanced] Existing team check result:', data);

            if (data.has_team) {
                this.state.hasExistingTeam = true;
                this.dom.existingTeamInfo.innerHTML = `
                    <strong>Team:</strong> ${data.team.name} [${data.team.tag}]<br>
                    <strong>Your Role:</strong> ${data.team.role}
                `;
                this.dom.existingTeamWarning.classList.add('show');
                this.dom.submitBtn.disabled = true;
            } else {
                this.dom.submitBtn.disabled = false;
            }
        } catch (error) {
            console.error('[TeamCreateEnhanced] Error checking existing team:', error);
            this.dom.submitBtn.disabled = false;
        }
    },

    // ========== LOAD GAME ID FIELDS ==========
    async loadGameIdFields(gameCode) {
        const config = GAME_ID_CONFIGS[gameCode];
        
        if (!config) {
            console.log('[TeamCreateEnhanced] No game ID config for:', gameCode);
            return;
        }

        try {
            console.log('[TeamCreateEnhanced] Loading game ID fields...');
            const response = await fetch(`/user/api/profile/get-game-id/?game=${gameCode}`);
            const data = await response.json();

            console.log('[TeamCreateEnhanced] Game ID data:', data);

            if (data.success) {
                // Set title
                this.dom.gameIdTitle.textContent = config.title;
                this.dom.gameIdFields.innerHTML = '';

                // Create fields
                config.fields.forEach(field => {
                    const fieldDiv = document.createElement('div');
                    fieldDiv.className = 'game-id-field';

                    const label = document.createElement('label');
                    label.textContent = field.label + (field.required ? ' *' : '');
                    
                    const input = document.createElement('input');
                    input.type = field.type;
                    input.name = `game_id_${field.name}`;
                    input.id = `game_id_${field.name}`;
                    input.placeholder = field.placeholder;
                    input.required = field.required;

                    // Auto-fill if user has it saved
                    if (data.has_game_id && data.game_ids && data.game_ids[field.name]) {
                        input.value = data.game_ids[field.name];
                        input.classList.add('autofilled');
                        input.title = '✓ Auto-filled from your profile';
                        this.state.gameIdData[field.name] = data.game_ids[field.name];
                        console.log('[TeamCreateEnhanced] Auto-filled:', field.name, '=', data.game_ids[field.name]);
                    }

                    // Save changes to gameIdData
                    input.addEventListener('input', () => {
                        this.state.gameIdData[field.name] = input.value;
                        if (input.value) {
                            input.classList.remove('is-invalid');
                        }
                    });

                    fieldDiv.appendChild(label);
                    fieldDiv.appendChild(input);
                    
                    // Add help text if available
                    if (field.help) {
                        const helpText = document.createElement('small');
                        helpText.className = 'form-text';
                        helpText.textContent = field.help;
                        fieldDiv.appendChild(helpText);
                    }

                    this.dom.gameIdFields.appendChild(fieldDiv);
                });

                // Show the section
                this.dom.gameIdSection.classList.add('show');
                console.log('[TeamCreateEnhanced] Game ID section shown');
            }
        } catch (error) {
            console.error('[TeamCreateEnhanced] Error loading game ID:', error);
        }
    },

    // ========== FORM SUBMISSION ==========
    async handleSubmit(event) {
        event.preventDefault();
        console.log('[TeamCreateEnhanced] Form submission started');

        // Check if user has existing team
        if (this.state.hasExistingTeam) {
            alert('You already have a team for this game. You can only have one team per game.');
            return;
        }

        // Validate game ID fields if shown
        if (this.dom.gameIdSection.classList.contains('show')) {
            const config = GAME_ID_CONFIGS[this.state.currentGame];
            let allValid = true;

            config.fields.forEach(field => {
                const input = document.getElementById(`game_id_${field.name}`);
                if (field.required && !input.value.trim()) {
                    input.classList.add('is-invalid');
                    allValid = false;
                }
            });

            if (!allValid) {
                alert('Please fill in all required game ID fields');
                return;
            }

            // Save game IDs to profile
            try {
                console.log('[TeamCreateEnhanced] Saving game IDs:', this.state.gameIdData);
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                
                const response = await fetch('/user/api/profile/update-game-id/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        game: this.state.currentGame,
                        game_ids: this.state.gameIdData
                    })
                });

                const data = await response.json();
                console.log('[TeamCreateEnhanced] Game ID save response:', data);


                if (!data.success) {
                    alert('Error saving game ID: ' + (data.message || 'Unknown error'));
                    return;
                }
            } catch (error) {
                console.error('[TeamCreateEnhanced] Error saving game ID:', error);
                alert('Error saving game ID. Please try again.');
                return;
            }
        }

        // Collect and save invite data
        this.collectInviteData();

        // Show loading
        this.dom.loadingOverlay.classList.add('active');
        this.dom.submitBtn.disabled = true;

        // Submit form
        console.log('[TeamCreateEnhanced] Submitting form...');
        this.dom.form.submit();
    },

    collectInviteData() {
        const invites = [];
        const inviteItems = document.querySelectorAll('.invite-item');
        
        inviteItems.forEach(item => {
            const identifier = item.querySelector('.invite-identifier').value.trim();
            const role = item.querySelector('.invite-role').value;
            
            if (identifier) {
                invites.push({ identifier, role, message: '' });
            }
        });

        // Store in hidden input
        document.getElementById('roster_data').value = JSON.stringify(invites);
        console.log('[TeamCreateEnhanced] Collected invites:', invites);
    }
};

// ========== FILE UPLOAD HANDLERS ==========
const FileUploadHandler = {
    init() {
        this.initLogoUpload();
        this.initBannerUpload();
    },

    initLogoUpload() {
        const uploadArea = document.getElementById('logo-upload-area');
        const fileInput = document.getElementById('id_logo');
        const placeholder = document.getElementById('logo-placeholder');
        const preview = document.getElementById('logo-preview');
        const previewImg = document.getElementById('logo-preview-img');
        const filename = document.getElementById('logo-filename');
        const removeBtn = document.getElementById('logo-remove');
        const changeBtn = document.getElementById('logo-change');

        if (!uploadArea || !fileInput) return;

        // Click to upload
        uploadArea.addEventListener('click', (e) => {
            if (!e.target.closest('.btn-preview-remove') && !e.target.closest('.btn-preview-change')) {
                fileInput.click();
            }
        });

        // Change button
        changeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });

        // Remove button
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.value = '';
            placeholder.style.display = 'flex';
            preview.style.display = 'none';
            previewImg.src = '';
        });

        // File selection
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0], previewImg, filename, placeholder, preview);
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
                this.handleFileSelect(file, previewImg, filename, placeholder, preview);
            }
        });
    },

    initBannerUpload() {
        const uploadArea = document.getElementById('banner-upload-area');
        const fileInput = document.getElementById('id_banner_image');
        const placeholder = document.getElementById('banner-placeholder');
        const preview = document.getElementById('banner-preview');
        const previewImg = document.getElementById('banner-preview-img');
        const filename = document.getElementById('banner-filename');
        const removeBtn = document.getElementById('banner-remove');
        const changeBtn = document.getElementById('banner-change');

        if (!uploadArea || !fileInput) return;

        // Click to upload
        uploadArea.addEventListener('click', (e) => {
            if (!e.target.closest('.btn-preview-remove') && !e.target.closest('.btn-preview-change')) {
                fileInput.click();
            }
        });

        // Change button
        changeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });

        // Remove button
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.value = '';
            placeholder.style.display = 'flex';
            preview.style.display = 'none';
            previewImg.src = '';
        });

        // File selection
        fileInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0], previewImg, filename, placeholder, preview);
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
                this.handleFileSelect(file, previewImg, filename, placeholder, preview);
            }
        });
    },

    handleFileSelect(file, previewImg, filenameEl, placeholder, preview) {
        if (!file) return;

        // Validate file size (10MB)
        if (file.size > 10 * 1024 * 1024) {
            alert('File size must be under 10MB');
            return;
        }

        // Validate file type
        if (!file.type.startsWith('image/')) {
            alert('Please select an image file');
            return;
        }

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            filenameEl.textContent = file.name;
            placeholder.style.display = 'none';
            preview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
};

// ========== INVITE HANDLERS ==========
const InviteHandler = {
    init() {
        this.addInviteBtn = document.getElementById('add-invite-btn');
        this.invitesContainer = document.getElementById('invites-container');
        this.inviteTemplate = document.querySelector('.invite-template');
        this.validationTimeout = null;

        if (!this.addInviteBtn || !this.invitesContainer) return;

        this.addInviteBtn.addEventListener('click', () => this.addInviteRow());

        // Add one initial row
        this.addInviteRow();
    },

    addInviteRow() {
        const template = this.inviteTemplate.querySelector('.invite-item');
        const clone = template.cloneNode(true);

        // Clear values
        const identifierInput = clone.querySelector('.invite-identifier');
        const roleSelect = clone.querySelector('.invite-role');
        identifierInput.value = '';
        roleSelect.value = 'PLAYER';

        // Create validation message element
        const validationMsg = document.createElement('div');
        validationMsg.className = 'validation-message';
        identifierInput.parentNode.appendChild(validationMsg);

        // Create user info element
        const userInfo = document.createElement('div');
        userInfo.className = 'user-info';
        identifierInput.parentNode.appendChild(userInfo);

        // Add email validation on input
        identifierInput.addEventListener('input', (e) => {
            this.handleIdentifierInput(e.target, validationMsg, userInfo);
        });

        // Add remove handler
        const removeBtn = clone.querySelector('.btn-remove-invite');
        removeBtn.addEventListener('click', () => {
            clone.remove();
            // If no invites left, add one
            if (this.invitesContainer.children.length === 0) {
                this.addInviteRow();
            }
        });

        this.invitesContainer.appendChild(clone);
    },

    handleIdentifierInput(input, validationMsg, userInfo) {
        const value = input.value.trim();
        
        // Clear previous timeout
        if (this.validationTimeout) {
            clearTimeout(this.validationTimeout);
        }

        // Reset states
        validationMsg.style.display = 'none';
        userInfo.classList.remove('visible');
        input.classList.remove('is-valid', 'is-invalid');

        if (!value) {
            return;
        }

        // Show loading state
        validationMsg.className = 'validation-message loading';
        validationMsg.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';
        validationMsg.style.display = 'flex';

        // Debounce the validation
        this.validationTimeout = setTimeout(() => {
            this.validateAndFetchUser(value, input, validationMsg, userInfo);
        }, 500);
    },

    async validateAndFetchUser(identifier, input, validationMsg, userInfo) {
        try {
            const isEmail = identifier.includes('@');
            
            // Validate email format if it's an email
            if (isEmail && !this.isValidEmail(identifier)) {
                input.classList.add('is-invalid');
                validationMsg.className = 'validation-message error';
                validationMsg.innerHTML = '<i class="fas fa-exclamation-circle"></i> Invalid email format';
                validationMsg.style.display = 'flex';
                return;
            }

            // Fetch user info from server
            const response = await fetch(`/teams/api/validate-invite/?identifier=${encodeURIComponent(identifier)}`);
            const data = await response.json();

            if (data.valid) {
                input.classList.add('is-valid');
                input.classList.remove('is-invalid');
                validationMsg.className = 'validation-message success';
                validationMsg.innerHTML = '<i class="fas fa-check-circle"></i> User found';
                validationMsg.style.display = 'flex';

                // Show user info (limited for privacy)
                if (data.user_info) {
                    userInfo.innerHTML = `
                        <i class="fas fa-user-circle"></i>
                        <span>Invitation will be sent to: <strong>${data.user_info.display_name || data.user_info.username}</strong></span>
                    `;
                    userInfo.classList.add('visible');
                }
            } else {
                input.classList.add('is-invalid');
                input.classList.remove('is-valid');
                validationMsg.className = 'validation-message error';
                validationMsg.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${data.message || 'User not found'}`;
                validationMsg.style.display = 'flex';
            }
        } catch (error) {
            console.error('[InviteHandler] Error validating user:', error);
            validationMsg.className = 'validation-message error';
            validationMsg.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error checking user';
            validationMsg.style.display = 'flex';
        }
    },

    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        TeamCreateApp.init();
        FileUploadHandler.init();
        InviteHandler.init();
    });
} else {
    TeamCreateApp.init();
    FileUploadHandler.init();
    InviteHandler.init();
}

// Export for debugging
window.TeamCreateApp = TeamCreateApp;
window.FileUploadHandler = FileUploadHandler;
window.InviteHandler = InviteHandler;
console.log('[TeamCreateEnhanced] Script initialized');

