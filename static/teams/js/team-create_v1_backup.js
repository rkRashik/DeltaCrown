// static/teams/js/team-create.js
// Production-ready Team Creation JavaScript
// Handles dynamic form behavior, validation, and live preview

(function() {
    'use strict';

    // State management
    const state = {
        selectedGame: null,
        invites: [],
        validationTimeouts: {}
    };

    // DOM elements
    const elements = {
        form: document.getElementById('teamCreateForm'),
        nameInput: document.getElementById('id_name'),
        tagInput: document.getElementById('id_tag'),
        gameSelect: document.getElementById('id_game'),
        descriptionInput: document.getElementById('id_description'),
        regionInput: document.getElementById('id_region'),
        logoInput: document.getElementById('id_logo'),
        bannerInput: document.getElementById('id_banner_image'),
        gameSelector: document.getElementById('gameSelector'),
        rosterInfo: document.getElementById('rosterInfo'),
        rosterInfoText: document.getElementById('rosterInfoText'),
        invitesList: document.getElementById('invitesList'),
        addInviteBtn: document.getElementById('addInviteBtn'),
        inviteCount: document.getElementById('inviteCount'),
        submitBtn: document.getElementById('submitBtn'),
        invitesJsonInput: document.getElementById('invites_json'),
        previewToggle: document.querySelector('.preview-toggle-btn'),
        previewPanel: document.querySelector('.preview-panel'),
        closePreview: document.querySelector('.close-preview-btn')
    };

    // Initialize
    function init() {
        renderGameCards();
        attachEventListeners();
        
        // Pre-select game if already set
        const preselectedGame = elements.gameSelect.value;
        if (preselectedGame && window.GAME_CONFIGS[preselectedGame]) {
            selectGame(preselectedGame);
        }
    }

    // Render game selection cards
    function renderGameCards() {
        const games = window.GAME_CONFIGS || {};
        const container = elements.gameSelector;
        
        container.innerHTML = '';
        
        Object.keys(games).forEach(gameCode => {
            const game = games[gameCode];
            const card = document.createElement('div');
            card.className = 'game-card bg-white border-2 border-gray-200 rounded-lg p-4 text-center transition-all cursor-pointer hover:shadow-md';
            card.dataset.game = gameCode;
            
            card.innerHTML = `
                <div class="flex flex-col items-center">
                    <div class="w-12 h-12 rounded-lg mb-2 flex items-center justify-center" style="background-color: ${game.color}15;">
                        <i class="fas fa-gamepad text-2xl" style="color: ${game.color};"></i>
                    </div>
                    <h4 class="font-semibold text-sm text-gray-900">${game.display_name}</h4>
                    <p class="text-xs text-gray-500 mt-1">${game.min_starters}v${game.min_starters}</p>
                </div>
            `;
            
            card.addEventListener('click', () => selectGame(gameCode));
            container.appendChild(card);
        });
    }

    // Select a game
    function selectGame(gameCode) {
        // Remove previous selection
        document.querySelectorAll('.game-card').forEach(card => {
            card.classList.remove('selected', 'border-indigo-600', 'bg-indigo-50');
        });
        
        // Select new game
        const selectedCard = document.querySelector(`[data-game="${gameCode}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected', 'border-indigo-600', 'bg-indigo-50');
        }
        
        elements.gameSelect.value = gameCode;
        state.selectedGame = gameCode;
        
        // Update roster info
        const game = window.GAME_CONFIGS[gameCode];
        if (game) {
            elements.rosterInfo.classList.remove('hidden');
            elements.rosterInfoText.textContent = `${game.display_name}: ${game.min_starters} starters + up to ${game.max_substitutes} substitutes (${game.max_roster} max total)`;
        }
        
        // Update preview
        updatePreview();
        
        // Update invite role dropdowns
        updateInviteRoles();
    }

    // Attach event listeners
    function attachEventListeners() {
        // Name validation (debounced)
        if (elements.nameInput) {
            elements.nameInput.addEventListener('input', debounce(() => {
                validateName(elements.nameInput.value);
                updatePreview();
            }, 500));
        }

        // Tag validation (debounced)
        if (elements.tagInput) {
            elements.tagInput.addEventListener('input', debounce(() => {
                const tag = elements.tagInput.value.toUpperCase();
                elements.tagInput.value = tag; // Auto-uppercase
                validateTag(tag);
                updatePreview();
            }, 500));
        }

        // Description update
        if (elements.descriptionInput) {
            elements.descriptionInput.addEventListener('input', updatePreview);
        }

        // Region update
        if (elements.regionInput) {
            elements.regionInput.addEventListener('input', updatePreview);
        }

        // Logo preview
        if (elements.logoInput) {
            elements.logoInput.addEventListener('change', (e) => {
                previewImage(e.target, 'logoPreview');
            });
        }

        // Banner preview
        if (elements.bannerInput) {
            elements.bannerInput.addEventListener('change', (e) => {
                previewImage(e.target, 'bannerPreview');
            });
        }

        // Add invite button
        if (elements.addInviteBtn) {
            elements.addInviteBtn.addEventListener('click', addInviteRow);
        }

        // Form submission
        if (elements.form) {
            elements.form.addEventListener('submit', handleSubmit);
        }

        // Mobile preview toggle
        if (elements.previewToggle) {
            elements.previewToggle.addEventListener('click', () => {
                elements.previewPanel.classList.add('active');
            });
        }

        if (elements.closePreview) {
            elements.closePreview.addEventListener('click', () => {
                elements.previewPanel.classList.remove('active');
            });
        }
    }

    // Validate team name (AJAX)
    async function validateName(name) {
        const validationDiv = document.getElementById('name-validation');
        
        if (!name || name.length < 3) {
            validationDiv.innerHTML = '';
            return;
        }

        validationDiv.innerHTML = '<span class="text-gray-500"><i class="fas fa-spinner fa-spin mr-1"></i> Checking...</span>';

        try {
            const response = await fetch('/teams/api/validate-name/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.CSRF_TOKEN
                },
                body: JSON.stringify({ 
                    name: name,
                    game: state.selectedGame 
                })
            });

            const data = await response.json();
            
            if (data.available) {
                validationDiv.innerHTML = '<span class="text-green-600"><i class="fas fa-check-circle mr-1"></i> Available</span>';
            } else {
                validationDiv.innerHTML = `<span class="text-red-600"><i class="fas fa-times-circle mr-1"></i> ${data.reason}</span>`;
            }
        } catch (error) {
            validationDiv.innerHTML = '<span class="text-gray-500">Unable to verify</span>';
        }
    }

    // Validate team tag (AJAX)
    async function validateTag(tag) {
        const validationDiv = document.getElementById('tag-validation');
        
        if (!tag || tag.length < 2) {
            validationDiv.innerHTML = '';
            return;
        }

        validationDiv.innerHTML = '<span class="text-gray-500"><i class="fas fa-spinner fa-spin mr-1"></i> Checking...</span>';

        try {
            const response = await fetch('/teams/api/validate-tag/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.CSRF_TOKEN
                },
                body: JSON.stringify({ 
                    tag: tag,
                    game: state.selectedGame 
                })
            });

            const data = await response.json();
            
            if (data.available) {
                validationDiv.innerHTML = '<span class="text-green-600"><i class="fas fa-check-circle mr-1"></i> Available</span>';
            } else {
                validationDiv.innerHTML = `<span class="text-red-600"><i class="fas fa-times-circle mr-1"></i> ${data.reason}</span>`;
            }
        } catch (error) {
            validationDiv.innerHTML = '<span class="text-gray-500">Unable to verify</span>';
        }
    }

    // Preview image upload
    function previewImage(input, previewId) {
        const preview = document.getElementById(previewId);
        const file = input.files[0];
        
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                if (previewId === 'logoPreview') {
                    preview.innerHTML = `<img src="${e.target.result}" class="w-full h-full object-cover rounded-lg">`;
                    document.getElementById('previewLogo').innerHTML = `<img src="${e.target.result}" class="w-full h-full object-cover rounded-lg">`;
                } else {
                    preview.innerHTML = `<img src="${e.target.result}" class="w-full h-full object-cover rounded-lg">`;
                    document.getElementById('previewBanner').style.backgroundImage = `url('${e.target.result}')`;
                    document.getElementById('previewBanner').style.backgroundSize = 'cover';
                    document.getElementById('previewBanner').style.backgroundPosition = 'center';
                }
            };
            reader.readAsDataURL(file);
        }
    }

    // Add invite row
    function addInviteRow() {
        const maxInvites = state.selectedGame ? 
            window.GAME_CONFIGS[state.selectedGame].max_roster - 1 : 7;
        
        if (state.invites.length >= maxInvites) {
            alert(`Maximum ${maxInvites} invites allowed for this game.`);
            return;
        }

        const inviteId = Date.now();
        const invite = {
            id: inviteId,
            identifier: '',
            role: 'PLAYER',
            message: ''
        };
        
        state.invites.push(invite);
        renderInviteRow(invite);
        updateInviteCount();
    }

    // Render single invite row
    function renderInviteRow(invite) {
        const row = document.createElement('div');
        row.className = 'invite-row bg-gray-50 rounded-lg p-4 border border-gray-200';
        row.dataset.inviteId = invite.id;
        
        const roles = state.selectedGame ? 
            window.GAME_CONFIGS[state.selectedGame].roles : 
            ['PLAYER', 'MANAGER', 'SUB'];
        
        const roleOptions = roles.map(role => 
            `<option value="${role}" ${invite.role === role ? 'selected' : ''}>${role}</option>`
        ).join('');
        
        row.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                    <label class="block text-xs font-medium text-gray-700 mb-1">Username or Email</label>
                    <input type="text" 
                           class="invite-identifier w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500" 
                           placeholder="username or email@example.com"
                           value="${invite.identifier}">
                    <div class="validation-msg mt-1 text-xs"></div>
                </div>
                <div class="flex items-end space-x-2">
                    <div class="flex-1">
                        <label class="block text-xs font-medium text-gray-700 mb-1">Role</label>
                        <select class="invite-role w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500">
                            ${roleOptions}
                        </select>
                    </div>
                    <button type="button" class="remove-invite-btn px-3 py-2 bg-red-100 text-red-600 rounded-md hover:bg-red-200 transition-colors">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
        
        // Attach event listeners
        const identifierInput = row.querySelector('.invite-identifier');
        const roleSelect = row.querySelector('.invite-role');
        const removeBtn = row.querySelector('.remove-invite-btn');
        
        identifierInput.addEventListener('input', debounce((e) => {
            updateInviteData(invite.id, 'identifier', e.target.value);
            validateUserIdentifier(invite.id, e.target.value, row.querySelector('.validation-msg'));
        }, 500));
        
        roleSelect.addEventListener('change', (e) => {
            updateInviteData(invite.id, 'role', e.target.value);
        });
        
        removeBtn.addEventListener('click', () => {
            removeInvite(invite.id);
        });
        
        elements.invitesList.appendChild(row);
    }

    // Update invite data in state
    function updateInviteData(inviteId, field, value) {
        const invite = state.invites.find(inv => inv.id === inviteId);
        if (invite) {
            invite[field] = value;
            updatePreview();
        }
    }

    // Validate user identifier (AJAX)
    async function validateUserIdentifier(inviteId, identifier, validationDiv) {
        if (!identifier) {
            validationDiv.innerHTML = '';
            return;
        }

        validationDiv.innerHTML = '<span class="text-gray-500"><i class="fas fa-spinner fa-spin mr-1"></i> Checking...</span>';

        try {
            const response = await fetch('/teams/api/validate-user/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.CSRF_TOKEN
                },
                body: JSON.stringify({ identifier })
            });

            const data = await response.json();
            
            if (data.valid) {
                validationDiv.innerHTML = `<span class="text-green-600"><i class="fas fa-check-circle mr-1"></i> ${data.user.display_name}</span>`;
            } else {
                validationDiv.innerHTML = `<span class="text-red-600"><i class="fas fa-times-circle mr-1"></i> ${data.reason}</span>`;
            }
        } catch (error) {
            validationDiv.innerHTML = '<span class="text-gray-500">Unable to verify</span>';
        }
    }

    // Remove invite
    function removeInvite(inviteId) {
        state.invites = state.invites.filter(inv => inv.id !== inviteId);
        const row = document.querySelector(`[data-invite-id="${inviteId}"]`);
        if (row) {
            row.remove();
        }
        updateInviteCount();
        updatePreview();
    }

    // Update invite count display
    function updateInviteCount() {
        elements.inviteCount.textContent = `${state.invites.length} invite${state.invites.length !== 1 ? 's' : ''}`;
    }

    // Update invite role options when game changes
    function updateInviteRoles() {
        if (!state.selectedGame) return;
        
        const roles = window.GAME_CONFIGS[state.selectedGame].roles;
        const roleSelects = document.querySelectorAll('.invite-role');
        
        roleSelects.forEach(select => {
            const currentValue = select.value;
            select.innerHTML = roles.map(role => 
                `<option value="${role}" ${role === currentValue ? 'selected' : ''}>${role}</option>`
            ).join('');
        });
    }

    // Update live preview
    function updatePreview() {
        // Team name
        const name = elements.nameInput.value || 'Team Name';
        document.getElementById('previewName').textContent = name;
        
        // Team tag
        const tag = elements.tagInput.value || 'TAG';
        document.getElementById('previewTag').textContent = '#' + tag.toUpperCase();
        
        // Game
        if (state.selectedGame) {
            const game = window.GAME_CONFIGS[state.selectedGame];
            document.getElementById('previewGame').innerHTML = `<i class="fas fa-gamepad mr-1"></i> ${game.display_name}`;
        } else {
            document.getElementById('previewGame').innerHTML = '<i class="fas fa-gamepad mr-1"></i> Select game';
        }
        
        // Region
        const region = elements.regionInput.value;
        const regionEl = document.getElementById('previewRegion');
        if (region) {
            regionEl.classList.remove('hidden');
            regionEl.querySelector('span').textContent = region;
        } else {
            regionEl.classList.add('hidden');
        }
        
        // Description
        const description = elements.descriptionInput.value || 'Team description will appear here...';
        document.getElementById('previewDescription').textContent = description;
        
        // Invites
        const invitesContainer = document.getElementById('previewInvites');
        invitesContainer.innerHTML = state.invites.map((invite, index) => `
            <div class="flex items-center text-sm">
                <div class="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center mr-2">
                    <span class="text-xs font-semibold text-gray-600">${index + 2}</span>
                </div>
                <div>
                    <p class="font-medium text-gray-900">${invite.identifier || 'Player ' + (index + 2)}</p>
                    <p class="text-xs text-gray-500">${invite.role}</p>
                </div>
            </div>
        `).join('');
    }

    // Handle form submission
    function handleSubmit(e) {
        e.preventDefault();
        
        // Validate required fields
        if (!elements.nameInput.value || elements.nameInput.value.length < 3) {
            alert('Please enter a valid team name (at least 3 characters)');
            elements.nameInput.focus();
            return;
        }
        
        if (!elements.tagInput.value || elements.tagInput.value.length < 2) {
            alert('Please enter a valid team tag (at least 2 characters)');
            elements.tagInput.focus();
            return;
        }
        
        if (!state.selectedGame) {
            alert('Please select a game for your team');
            elements.gameSelector.scrollIntoView({ behavior: 'smooth' });
            return;
        }
        
        // Prepare invites JSON
        const invitesData = state.invites
            .filter(inv => inv.identifier)
            .map(inv => ({
                identifier: inv.identifier,
                role: inv.role,
                message: inv.message || ''
            }));
        
        elements.invitesJsonInput.value = JSON.stringify(invitesData);
        
        // Show loading state
        elements.submitBtn.disabled = true;
        document.getElementById('submitBtnText').classList.add('hidden');
        document.getElementById('submitBtnLoading').classList.remove('hidden');
        
        // Submit form
        elements.form.submit();
    }

    // Utility: Debounce function
    function debounce(func, wait) {
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

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
