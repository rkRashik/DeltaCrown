/**
 * Tournament Registration Form V2
 * Professional Wizard Controller with Player Card System
 * Based on blueprint specifications
 */

// ===== Global State =====
const registrationState = {
  currentStep: 1,
  totalSteps: 0,
  gameConfig: null,
  playerData: {},
  rosterData: [],
  validation: {},
  autoSaveEnabled: true
};

// ===== Game-Specific Field Configurations =====
const gameFieldConfigs = {
  valorant: {
    roles: ['Duelist', 'Controller', 'Initiator', 'Sentinel', 'IGL (In-Game Leader)'],
    fields: [
      {
        name: 'displayName',
        label: 'Player Display Name',
        type: 'text',
        placeholder: "Enter player's name",
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'riotId',
        label: 'Riot ID',
        type: 'text',
        placeholder: 'Example: PlayerName#TAG',
        required: true,
        validation: (val) => /^[a-zA-Z0-9\s]+#[a-zA-Z0-9]+$/.test(val) && val.length >= 5,
        errorMsg: 'Riot ID must be in format: PlayerName#TAG'
      },
      {
        name: 'discordId',
        label: 'Discord ID',
        type: 'text',
        placeholder: 'Example: username',
        required: false
      }
    ]
  },
  cs2: {
    roles: ['IGL (In-Game Leader)', 'Entry Fragger', 'AWPer', 'Lurker', 'Support'],
    fields: [
      {
        name: 'displayName',
        label: 'Player Display Name',
        type: 'text',
        placeholder: "Enter player's name",
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'steamId',
        label: 'Steam ID',
        type: 'text',
        placeholder: 'e.g., STEAM_0:1:123456 or 7656119...',
        required: true,
        validation: (val) => /^(STEAM_|765)/.test(val) && val.length > 5,
        errorMsg: 'Steam ID must start with STEAM_ or 765',
        helpLink: 'https://www.steamidfinder.com/'
      },
      {
        name: 'discordId',
        label: 'Discord ID',
        type: 'text',
        placeholder: 'Example: username',
        required: false
      }
    ]
  },
  dota2: {
    roles: ['Hard Carry (Pos 1)', 'Midlaner (Pos 2)', 'Offlaner (Pos 3)', 'Soft Support (Pos 4)', 'Hard Support (Pos 5)'],
    fields: [
      {
        name: 'displayName',
        label: 'Player Display Name',
        type: 'text',
        placeholder: "Enter player's name",
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'steamId',
        label: 'Steam ID',
        type: 'text',
        placeholder: 'e.g., STEAM_0:1:123456 or 7656119...',
        required: true,
        validation: (val) => /^(STEAM_|765)/.test(val) && val.length > 5,
        errorMsg: 'Steam ID must start with STEAM_ or 765'
      },
      {
        name: 'dotaFriendId',
        label: 'Dota 2 Friend ID',
        type: 'text',
        placeholder: 'Find this in your Dota 2 profile',
        required: true,
        validation: (val) => /^\d+$/.test(val),
        errorMsg: 'Friend ID must be numbers only'
      },
      {
        name: 'discordId',
        label: 'Discord ID',
        type: 'text',
        placeholder: 'Example: username',
        required: false
      }
    ]
  },
  mlbb: {
    roles: ['Gold Laner', 'EXP Laner', 'Mid Laner', 'Jungler', 'Roamer'],
    fields: [
      {
        name: 'displayName',
        label: 'Player Display Name',
        type: 'text',
        placeholder: "Enter player's name",
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'inGameName',
        label: 'In-Game Name',
        type: 'text',
        placeholder: 'The exact name shown in MLBB',
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'mlbbUserId',
        label: 'MLBB User ID',
        type: 'text',
        placeholder: 'Example: 12345678 (1234)',
        required: true,
        validation: (val) => /^\d+/.test(val),
        errorMsg: 'User ID must contain numbers'
      },
      {
        name: 'discordId',
        label: 'Discord ID',
        type: 'text',
        placeholder: 'Example: username',
        required: false
      }
    ]
  },
  pubg: {
    roles: ['IGL / Shot Caller', 'Assaulter / Fragger', 'Support', 'Sniper / Scout'],
    fields: [
      {
        name: 'displayName',
        label: 'Player Display Name',
        type: 'text',
        placeholder: "Enter player's name",
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'characterName',
        label: 'PUBG Character Name',
        type: 'text',
        placeholder: 'The exact name shown in PUBG',
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'pubgId',
        label: 'PUBG ID',
        type: 'text',
        placeholder: 'Example: 5123456789',
        required: true,
        validation: (val) => /^[a-zA-Z0-9]+$/.test(val),
        errorMsg: 'PUBG ID must be alphanumeric'
      },
      {
        name: 'discordId',
        label: 'Discord ID',
        type: 'text',
        placeholder: 'Example: username',
        required: false
      }
    ]
  },
  freefire: {
    roles: ['Rusher', 'Flanker', 'Support', 'Shot Caller (IGL)'],
    fields: [
      {
        name: 'displayName',
        label: 'Player Display Name',
        type: 'text',
        placeholder: "Enter player's name",
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'inGameName',
        label: 'In-Game Name',
        type: 'text',
        placeholder: 'The exact name shown in Free Fire',
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'freeFireUid',
        label: 'Free Fire UID',
        type: 'text',
        placeholder: 'Example: 1234567890',
        required: true,
        validation: (val) => /^\d+$/.test(val),
        errorMsg: 'UID must be numbers only'
      },
      {
        name: 'discordId',
        label: 'Discord ID',
        type: 'text',
        placeholder: 'Example: username',
        required: false
      }
    ]
  },
  efootball: {
    roles: null, // Solo game
    fields: [
      {
        name: 'displayName',
        label: 'Player Display Name',
        type: 'text',
        placeholder: "Enter player's name",
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'efootballUsername',
        label: 'eFootball Username',
        type: 'text',
        placeholder: 'Your username in the game',
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'efootballUserId',
        label: 'eFootball User ID',
        type: 'text',
        placeholder: 'Example: 123456789',
        required: true,
        validation: (val) => /^\d+$/.test(val),
        errorMsg: 'User ID must be numbers only'
      }
    ]
  },
  fc26: {
    roles: null, // Solo game
    fields: [
      {
        name: 'displayName',
        label: 'Player Display Name',
        type: 'text',
        placeholder: "Enter player's name",
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'platform',
        label: 'Platform',
        type: 'select',
        options: ['PC (EA App)', 'PlayStation', 'Xbox'],
        required: true
      },
      {
        name: 'platformId',
        label: 'EA ID / PSN ID / Gamertag',
        type: 'text',
        placeholder: 'Enter your ID for the selected platform',
        required: true,
        validation: (val) => val.trim().length > 0
      },
      {
        name: 'fc26Username',
        label: 'FC 26 Username',
        type: 'text',
        placeholder: 'Your username in FC 26',
        required: true,
        validation: (val) => val.trim().length > 0
      }
    ]
  }
};

// ===== Wizard Controller =====
const wizardController = {
  init() {
    this.calculateTotalSteps();
    this.renderStepper();
    this.loadGameFields();
    this.autoFillFields();  // NEW: Auto-fill fields from profile
    this.setupAutoSave();
    this.restoreFromLocalStorage();
    
    console.log('✅ Wizard initialized:', {
      totalSteps: registrationState.totalSteps,
      game: window.tournamentData.game,
      isTeam: window.tournamentData.isTeam
    });
  },

  calculateTotalSteps() {
    let steps = window.tournamentData.isTeam ? 3 : 2; // Team: 3 steps, Solo: 2 steps
    if (window.tournamentData.isPaid) {
      steps++; // Add payment step for paid tournaments
    }
    registrationState.totalSteps = steps;
  },

  renderStepper() {
    const stepper = document.getElementById('wizardStepper');
    const steps = [];
    
    if (window.tournamentData.isTeam) {
      steps.push('TEAM INFO', 'ROSTER', 'REVIEW');
    } else {
      steps.push('PLAYER INFO', 'REVIEW');
    }
    
    if (window.tournamentData.isPaid) {
      steps.push('PAYMENT');
    }
    
    let html = '';
    steps.forEach((label, index) => {
      const stepNum = index + 1;
      const isActive = stepNum === registrationState.currentStep;
      const isCompleted = stepNum < registrationState.currentStep;
      
      html += `
        <div class="step-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}" data-step="${stepNum}">
          <div class="step-circle">
            ${isCompleted ? '<i class="fas fa-check"></i>' : stepNum}
          </div>
          <div class="step-label">${label}</div>
        </div>
      `;
    });
    
    stepper.innerHTML = html;
  },

  async loadGameFields() {
    const container = document.getElementById('playerFieldsContainer');
    const game = window.tournamentData.game;
    const config = gameFieldConfigs[game];
    
    if (!config) {
      container.innerHTML = `<p class="field-error">⚠️ Game configuration not found for: ${game}</p>`;
      return;
    }
    
    registrationState.gameConfig = config;
    
    // Render fields
    let html = '';
    config.fields.forEach(field => {
      html += this.renderField(field);
    });
    
    container.innerHTML = html;
    
    // Setup validation
    config.fields.forEach(field => {
      const input = document.getElementById(field.name);
      if (input) {
        input.addEventListener('blur', () => this.validateField(field.name));
        input.addEventListener('input', () => this.clearFieldError(field.name));
      }
    });
    
    // If team tournament, populate captain role dropdown
    if (window.tournamentData.isTeam && config.roles) {
      this.populateRoleDropdown('captainRole', config.roles);
    }
  },

  autoFillFields() {
    // Auto-fill fields from profile data
    if (!window.tournamentData.profileData) {
      console.warn('⚠️ No profile data available for auto-fill');
      return;
    }
    
    const profileData = window.tournamentData.profileData;
    const game = window.tournamentData.game;
    
    console.log('🔄 Auto-filling fields for', game, profileData);
    
    // Wait a bit for fields to render
    setTimeout(() => {
      // Auto-fill common fields
      this.setFieldValue('displayName', profileData.displayName);
      this.setFieldValue('discordId', profileData.discordId);
      this.setFieldValue('email', profileData.email);
      this.setFieldValue('phone', profileData.phone);
      
      // Auto-fill game-specific fields
      if (game === 'valorant') {
        this.setFieldValue('riotId', profileData.riotId);
      } else if (game === 'cs2') {
        this.setFieldValue('steamId', profileData.steamId);
      } else if (game === 'dota2') {
        this.setFieldValue('steamId', profileData.steamId);
        this.setFieldValue('dotaFriendId', profileData.dotaFriendId);
      } else if (game === 'mlbb') {
        this.setFieldValue('inGameName', profileData.inGameName);
        this.setFieldValue('mlbbUserId', profileData.mlbbUserId);
      } else if (game === 'pubg') {
        this.setFieldValue('characterName', profileData.characterName);
        this.setFieldValue('pubgId', profileData.pubgId);
      } else if (game === 'freefire') {
        this.setFieldValue('inGameName', profileData.inGameName);
        this.setFieldValue('freeFireUid', profileData.freeFireUid);
      } else if (game === 'efootball') {
        this.setFieldValue('efootballUsername', profileData.efootballUsername);
        this.setFieldValue('efootballUserId', profileData.efootballUserId);
      } else if (game === 'fc26') {
        this.setFieldValue('platform', profileData.platform);
        this.setFieldValue('platformId', profileData.platformId);
        this.setFieldValue('fc26Username', profileData.fc26Username);
      }
      
      console.log('✅ Auto-fill complete');
    }, 500);
  },

  setFieldValue(fieldName, value) {
    const input = document.getElementById(fieldName);
    if (input && value) {
      input.value = value;
      // Add a subtle visual indicator that field was auto-filled
      input.classList.add('auto-filled');
      setTimeout(() => input.classList.remove('auto-filled'), 2000);
    }
  },

  renderField(field) {
    const { name, label, type, placeholder, required, helpLink } = field;
    
    let inputHtml = '';
    
    if (type === 'select' && field.options) {
      inputHtml = `
        <select id="${name}" class="form-control" ${required ? 'required' : ''}>
          <option value="">-- Select ${label} --</option>
          ${field.options.map(opt => `<option value="${opt}">${opt}</option>`).join('')}
        </select>
      `;
    } else {
      inputHtml = `
        <input 
          type="${type}" 
          id="${name}" 
          class="form-control" 
          placeholder="${placeholder || ''}"
          ${required ? 'required' : ''}
        >
      `;
    }
    
    return `
      <div class="form-field">
        <label for="${name}">
          ${label} ${required ? '<span class="required">*</span>' : ''}
        </label>
        ${inputHtml}
        ${helpLink ? `<span class="field-hint"><a href="${helpLink}" target="_blank" style="color: var(--accent-primary);">How to find this?</a></span>` : ''}
        <span class="field-error" id="${name}-error" style="display: none;"></span>
      </div>
    `;
  },

  validateField(fieldName) {
    const config = registrationState.gameConfig.fields.find(f => f.name === fieldName);
    if (!config) return true;
    
    const input = document.getElementById(fieldName);
    const value = input.value.trim();
    
    // Check required
    if (config.required && !value) {
      this.showFieldError(fieldName, `${config.label} is required`);
      return false;
    }
    
    // Check validation function
    if (config.validation && value && !config.validation(value)) {
      this.showFieldError(fieldName, config.errorMsg || `Invalid ${config.label}`);
      return false;
    }
    
    // Valid
    this.clearFieldError(fieldName);
    this.showFieldSuccess(fieldName);
    return true;
  },

  showFieldError(fieldName, message) {
    const input = document.getElementById(fieldName);
    const errorSpan = document.getElementById(`${fieldName}-error`);
    
    if (input) input.classList.add('error');
    if (errorSpan) {
      errorSpan.textContent = message;
      errorSpan.style.display = 'block';
    }
    
    registrationState.validation[fieldName] = false;
  },

  clearFieldError(fieldName) {
    const input = document.getElementById(fieldName);
    const errorSpan = document.getElementById(`${fieldName}-error`);
    
    if (input) {
      input.classList.remove('error');
      input.classList.remove('success');
    }
    if (errorSpan) {
      errorSpan.style.display = 'none';
    }
  },

  showFieldSuccess(fieldName) {
    const input = document.getElementById(fieldName);
    if (input) {
      input.classList.remove('error');
      input.classList.add('success');
    }
    registrationState.validation[fieldName] = true;
  },

  validateStep(stepNum) {
    if (stepNum === 1) {
      // Validate player/captain fields
      const config = registrationState.gameConfig;
      if (!config) return false;
      
      let allValid = true;
      config.fields.forEach(field => {
        if (!this.validateField(field.name)) {
          allValid = false;
        }
      });
      
      return allValid;
    }
    
    if (stepNum === 2 && window.tournamentData.isTeam) {
      // Validate roster
      const minPlayers = window.tournamentData.minTeamSize || 5;
      if (registrationState.rosterData.length < minPlayers) {
        alert(`❌ You need at least ${minPlayers} players in your roster.`);
        return false;
      }
      
      // Validate each player has required fields
      // (This would be more complex in real implementation)
      return true;
    }
    
    if (stepNum === registrationState.totalSteps - (window.tournamentData.isPaid ? 1 : 0)) {
      // Review step - check rules agreement
      const agreeCheckbox = document.getElementById('agreeRules');
      if (!agreeCheckbox || !agreeCheckbox.checked) {
        alert('❌ You must agree to the tournament rules before proceeding.');
        return false;
      }
      return true;
    }
    
    return true;
  },

  nextStep() {
    if (!this.validateStep(registrationState.currentStep)) {
      return;
    }
    
    if (registrationState.currentStep < registrationState.totalSteps) {
      this.saveStepData(registrationState.currentStep);
      registrationState.currentStep++;
      this.showStep(registrationState.currentStep);
      this.renderStepper();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  },

  prevStep() {
    if (registrationState.currentStep > 1) {
      registrationState.currentStep--;
      this.showStep(registrationState.currentStep);
      this.renderStepper();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  },

  goToStep(stepNum) {
    if (stepNum >= 1 && stepNum <= registrationState.totalSteps) {
      registrationState.currentStep = stepNum;
      this.showStep(stepNum);
      this.renderStepper();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  },

  showStep(stepNum) {
    const allSteps = document.querySelectorAll('.wizard-step');
    allSteps.forEach(step => {
      step.classList.remove('active');
    });
    
    const activeStep = document.querySelector(`.wizard-step[data-step="${stepNum}"]`);
    if (activeStep) {
      activeStep.classList.add('active');
    }
    
    // Populate review if we're on review step
    if (stepNum === registrationState.totalSteps - (window.tournamentData.isPaid ? 1 : 0)) {
      this.populateReview();
    }
  },

  saveStepData(stepNum) {
    if (stepNum === 1) {
      // Save player/captain data
      const config = registrationState.gameConfig;
      config.fields.forEach(field => {
        const input = document.getElementById(field.name);
        if (input) {
          registrationState.playerData[field.name] = input.value;
        }
      });
      
      // Save to local storage
      if (registrationState.autoSaveEnabled) {
        this.saveToLocalStorage();
      }
    }
  },

  populateRoleDropdown(selectId, roles) {
    const select = document.getElementById(selectId);
    if (!select) return;
    
    select.innerHTML = '<option value="">Select role...</option>';
    roles.forEach(role => {
      const option = document.createElement('option');
      option.value = role;
      option.textContent = role;
      select.appendChild(option);
    });
  },

  populateReview() {
    // Populate player/team summary
    const config = registrationState.gameConfig;
    const summaryEl = document.getElementById(window.tournamentData.isTeam ? 'teamSummary' : 'playerSummary');
    
    if (summaryEl && config) {
      let html = '';
      config.fields.forEach(field => {
        const value = registrationState.playerData[field.name] || '-';
        html += `
          <div class="summary-row">
            <span class="summary-label">${field.label}:</span>
            <span class="summary-value">${value}</span>
          </div>
        `;
      });
      summaryEl.innerHTML = html;
    }
    
    // Populate roster summary if team
    if (window.tournamentData.isTeam) {
      const rosterEl = document.getElementById('rosterSummary');
      if (rosterEl) {
        let html = `
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Player Name</th>
                <th>Game ID</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
        `;
        
        registrationState.rosterData.forEach((player, index) => {
          html += `
            <tr>
              <td>${index + 1}</td>
              <td>${player.displayName || '-'}</td>
              <td>${player.gameId || '-'}</td>
              <td>${player.role || '-'}</td>
            </tr>
          `;
        });
        
        html += '</tbody></table>';
        rosterEl.innerHTML = html;
      }
    }
  },

  async submitRegistration() {
    const btn = document.getElementById('submitBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
    
    try {
      // Collect all data
      const formData = {
        tournament_slug: window.tournamentData.slug,
        player_data: registrationState.playerData,
        roster_data: window.tournamentData.isTeam ? registrationState.rosterData : null,
        save_to_profile: document.getElementById('saveToProfile')?.checked || false
      };
      
      // Submit via API
      const response = await fetch(`/tournaments/api/${window.tournamentData.slug}/register/submit/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(formData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.errors ? JSON.stringify(errorData.errors) : 'Registration failed');
      }
      
      const result = await response.json();
      
      // Clear local storage
      localStorage.removeItem(`registration_${window.tournamentData.slug}`);
      
      // Handle paid tournaments
      if (window.tournamentData.isPaid) {
        this.nextStep(); // Go to payment step
        startPaymentCountdown();
      } else {
        // Redirect to success page
        window.location.href = result.redirect_url || `/tournaments/t/${window.tournamentData.slug}/`;
      }
      
    } catch (error) {
      console.error('Registration error:', error);
      alert('❌ Registration failed. Please try again.\n\n' + error.message);
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-check-circle"></i> Complete Registration';
    }
  },

  setupAutoSave() {
    // Auto-save every 30 seconds
    if (registrationState.autoSaveEnabled) {
      setInterval(() => {
        this.saveToLocalStorage();
      }, 30000);
    }
  },

  saveToLocalStorage() {
    const data = {
      step: registrationState.currentStep,
      playerData: registrationState.playerData,
      rosterData: registrationState.rosterData,
      timestamp: Date.now()
    };
    localStorage.setItem(`registration_${window.tournamentData.slug}`, JSON.stringify(data));
  },

  restoreFromLocalStorage() {
    const saved = localStorage.getItem(`registration_${window.tournamentData.slug}`);
    if (saved) {
      try {
        const data = JSON.parse(saved);
        // Only restore if less than 24 hours old
        if (Date.now() - data.timestamp < 86400000) {
          registrationState.playerData = data.playerData || {};
          registrationState.rosterData = data.rosterData || [];
          // Restore form values
          Object.keys(data.playerData).forEach(key => {
            const input = document.getElementById(key);
            if (input) input.value = data.playerData[key];
          });
        }
      } catch (e) {
        console.warn('Failed to restore saved data:', e);
      }
    }
  }
};

// ===== Roster Manager (for team tournaments) =====
const rosterManager = {
  playerCount: 1, // Start with captain

  init() {
    if (!window.tournamentData.isTeam) return;
    
    // Auto-fill roster from team data
    this.autoFillRoster();
    
    // Update captain info
    this.updateCaptainCard();
    
    // Setup add player button
    const addBtn = document.getElementById('addPlayerBtn');
    if (addBtn) {
      addBtn.addEventListener('click', () => this.addPlayerCard());
    }
    
    // Update counter
    this.updateCounter();
  },

  autoFillRoster() {
    // Check if team roster data exists
    if (!window.tournamentData.teamRoster || window.tournamentData.teamRoster.length === 0) {
      console.warn('⚠️ No team roster data available');
      return;
    }
    
    const roster = window.tournamentData.teamRoster;
    console.log('🔄 Auto-filling roster with', roster.length, 'players');
    
    // Process each roster member except captain (who is in step 1)
    roster.forEach((member, index) => {
      if (member.isCaptain) {
        // Captain data is already in step 1
        console.log('  ✓ Captain:', member.displayName);
        return;
      }
      
      // Add player card for non-captain members
      this.addPlayerCard(member);
    });
    
    console.log('✅ Roster auto-fill complete');
  },

  addPlayerCard(playerData = null) {
    const maxPlayers = window.tournamentData.maxTeamSize || 7;
    if (this.playerCount >= maxPlayers) {
      alert(`❌ Maximum roster size is ${maxPlayers} players.`);
      return;
    }
    
    this.playerCount++;
    const container = document.getElementById('playerCardsContainer');
    const config = registrationState.gameConfig;
    
    const card = document.createElement('div');
    card.className = 'player-card';
    card.setAttribute('data-player-index', this.playerCount - 1);
    
    let fieldsHtml = '';
    config.fields.forEach(field => {
      const value = playerData ? (playerData[field.name] || '') : '';
      fieldsHtml += `
        <div class="form-field">
          <label>${field.label} ${field.required ? '<span class="required">*</span>' : ''}</label>
          <input 
            type="${field.type}" 
            class="form-control player-field ${playerData && value ? 'auto-filled' : ''}" 
            data-field="${field.name}"
            value="${value}"
            placeholder="${field.placeholder || ''}"
            ${field.required ? 'required' : ''}
          >
        </div>
      `;
    });
    
    const roleValue = playerData ? (playerData.role || '') : '';
    
    card.innerHTML = `
      <div class="card-header">
        <span class="player-number">PLAYER ${this.playerCount}</span>
        <button type="button" class="btn-remove-player" onclick="rosterManager.removePlayerCard(this)">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="card-body">
        ${fieldsHtml}
        <div class="form-field">
          <label>Role <span class="required">*</span></label>
          <select class="form-control player-role ${playerData && roleValue ? 'auto-filled' : ''}" required>
            <option value="">Select role...</option>
            ${config.roles.map(role => `<option value="${role}" ${role === roleValue ? 'selected' : ''}>${role}</option>`).join('')}
          </select>
        </div>
      </div>
    `;
    
    container.appendChild(card);
    this.updateCounter();
    
    // Remove auto-filled class after animation
    if (playerData) {
      setTimeout(() => {
        card.querySelectorAll('.auto-filled').forEach(el => el.classList.remove('auto-filled'));
      }, 2000);
    }
    
    // Scroll to new card only if not auto-filling
    if (!playerData) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  },

  updateCaptainCard() {
    // Populate captain info from step 1 data
    const captainName = document.getElementById('captainName');
    const captainGameId = document.getElementById('captainGameId');
    
    if (captainName) {
      captainName.textContent = registrationState.playerData.displayName || 'Loading...';
    }
    
    if (captainGameId) {
      const gameIdField = registrationState.gameConfig.fields.find(f => 
        f.name.includes('Id') && f.name !== 'discordId'
      );
      if (gameIdField) {
        captainGameId.textContent = registrationState.playerData[gameIdField.name] || 'Loading...';
      }
    }
  },

  removePlayerCard(button) {
    const card = button.closest('.player-card');
    if (card) {
      card.remove();
      this.playerCount--;
      this.updateCounter();
      this.renumberCards();
    }
  },

  renumberCards() {
    const cards = document.querySelectorAll('.player-card:not(.captain-card)');
    cards.forEach((card, index) => {
      const numberSpan = card.querySelector('.player-number');
      if (numberSpan) {
        numberSpan.textContent = `PLAYER ${index + 2}`; // +2 because captain is 1
      }
      card.setAttribute('data-player-index', index + 1);
    });
  },

  updateCounter() {
    const counter = document.getElementById('rosterCount');
    const minPlayers = window.tournamentData.minTeamSize || 5;
    if (counter) {
      counter.textContent = `${this.playerCount}/${minPlayers}`;
      
      // Change color based on meeting minimum
      if (this.playerCount >= minPlayers) {
        counter.style.color = 'var(--success)';
      } else {
        counter.style.color = 'var(--error)';
      }
    }
  },

  collectRosterData() {
    const roster = [];
    
    // Add captain
    const captainRole = document.getElementById('captainRole')?.value;
    roster.push({
      displayName: registrationState.playerData.displayName,
      gameId: registrationState.playerData.riotId || registrationState.playerData.steamId || '',
      role: captainRole,
      isCaptain: true
    });
    
    // Add other players
    const cards = document.querySelectorAll('.player-card:not(.captain-card)');
    cards.forEach(card => {
      const fields = card.querySelectorAll('.player-field');
      const roleSelect = card.querySelector('.player-role');
      
      const playerData = {};
      fields.forEach(field => {
        playerData[field.dataset.field] = field.value;
      });
      playerData.role = roleSelect?.value;
      playerData.isCaptain = false;
      
      roster.push(playerData);
    });
    
    registrationState.rosterData = roster;
  }
};

// ===== Modal Functions =====
function openRulesModal() {
  const modal = document.getElementById('rulesModal');
  if (modal) {
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }
}

function closeRulesModal() {
  const modal = document.getElementById('rulesModal');
  if (modal) {
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
  }
}

// ===== Payment Functions =====
function startPaymentCountdown() {
  let seconds = 5;
  const countdownEl = document.getElementById('countdown');
  
  const interval = setInterval(() => {
    seconds--;
    if (countdownEl) countdownEl.textContent = seconds;
    
    if (seconds <= 0) {
      clearInterval(interval);
      redirectToPayment();
    }
  }, 1000);
}

function redirectToPayment() {
  window.location.href = `/tournaments/payment/${window.tournamentData.slug}/`;
}

// ===== Utility Functions =====
function getCookie(name) {
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
}

// ===== Initialize on page load =====
document.addEventListener('DOMContentLoaded', () => {
  wizardController.init();
  
  // Initialize roster manager for team tournaments
  if (window.tournamentData.isTeam) {
    // Wait for step 2 to be visible
    const step2Observer = new MutationObserver(() => {
      if (document.querySelector('.wizard-step[data-step="2"].active')) {
        rosterManager.init();
        step2Observer.disconnect();
      }
    });
    
    step2Observer.observe(document.querySelector('.wizard-content'), {
      attributes: true,
      subtree: true,
      attributeFilter: ['class']
    });
  }
  
  console.log('✅ Registration Form V2 loaded successfully');
});
