/**
 * Dynamic Tournament Registration Form
 * 
 * Loads game configuration from API and renders fields dynamically
 * Handles validation, auto-fill, and roster management for team events
 */

class DynamicRegistrationForm {
  constructor(tournamentSlug, gameCode) {
    this.tournamentSlug = tournamentSlug;
    this.gameCode = gameCode;
    this.gameConfig = null;
    this.contextData = null;
    this.currentStep = 1;
    
    // Component modules
    this.configLoader = new GameConfigLoader(gameCode);
    this.fieldRenderer = new FieldRenderer();
    this.fieldValidator = new FieldValidator(gameCode);
    this.autoFillHandler = new AutoFillHandler();
    this.rosterManager = null; // Initialize if team event
    
    this.init();
  }
  
  async init() {
    try {
      // Show loading state
      this.showLoading();
      
      // Load game configuration and context
      await Promise.all([
        this.loadGameConfig(),
        this.loadRegistrationContext()
      ]);
      
      // Render dynamic fields
      this.renderDynamicFields();
      
      // Initialize validators
      this.initializeValidation();
      
      // Auto-fill if data available
      if (this.contextData.profile_data) {
        this.autoFillHandler.fillProfileFields(this.contextData.profile_data);
      }
      
      // Initialize roster manager for team events
      if (this.contextData.context.is_team_event) {
        this.rosterManager = new RosterManager(
          this.gameConfig.roles,
          this.gameCode
        );
        
        if (this.contextData.team_data) {
          this.rosterManager.fillTeamData(this.contextData.team_data);
        }
      }
      
      // Hide loading, show form
      this.hideLoading();
      
      console.log('✅ Dynamic registration form initialized');
    } catch (error) {
      console.error('❌ Failed to initialize form:', error);
      this.showError('Failed to load registration form. Please refresh the page.');
    }
  }
  
  async loadGameConfig() {
    this.gameConfig = await this.configLoader.load();
  }
  
  async loadRegistrationContext() {
    const response = await fetch(`/tournaments/api/${this.tournamentSlug}/register/context/`, {
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error(`Failed to load context: ${response.status}`);
    }
    
    this.contextData = await response.json();
  }
  
  renderDynamicFields() {
    const container = document.getElementById('dynamic-fields-container');
    
    if (!container) {
      console.warn('No dynamic fields container found');
      return;
    }
    
    // Clear existing content
    container.innerHTML = '';
    
    // Sort fields by display_order
    const sortedFields = [...this.gameConfig.fields].sort((a, b) => 
      a.display_order - b.display_order
    );
    
    // Render each field
    sortedFields.forEach(field => {
      const fieldElement = this.fieldRenderer.render(field);
      container.appendChild(fieldElement);
    });
    
    console.log(`✅ Rendered ${sortedFields.length} dynamic fields`);
  }
  
  initializeValidation() {
    const form = document.getElementById('registrationForm');
    
    if (!form) return;
    
    // Add real-time validation to dynamic fields
    this.gameConfig.fields.forEach(field => {
      const input = document.getElementById(field.field_name);
      
      if (!input) return;
      
      // Validate on blur
      input.addEventListener('blur', async () => {
        await this.validateField(field.field_name, input.value);
      });
      
      // Clear error on input
      input.addEventListener('input', () => {
        this.clearFieldError(field.field_name);
      });
    });
    
    // Form submission
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.handleSubmit();
    });
  }
  
  async validateField(fieldName, value) {
    const result = await this.fieldValidator.validate(fieldName, value);
    
    if (!result.is_valid) {
      this.showFieldError(fieldName, result.error);
      return false;
    } else {
      this.clearFieldError(fieldName);
      return true;
    }
  }
  
  showFieldError(fieldName, message) {
    const input = document.getElementById(fieldName);
    const fieldContainer = input?.closest('.form-field');
    
    if (!fieldContainer) return;
    
    // Add error class to input
    input.classList.add('error');
    
    // Find or create error message element
    let errorSpan = fieldContainer.querySelector('.field-error');
    
    if (!errorSpan) {
      errorSpan = document.createElement('span');
      errorSpan.className = 'field-error';
      fieldContainer.appendChild(errorSpan);
    }
    
    errorSpan.textContent = message;
    errorSpan.style.display = 'block';
  }
  
  clearFieldError(fieldName) {
    const input = document.getElementById(fieldName);
    const fieldContainer = input?.closest('.form-field');
    
    if (!fieldContainer) return;
    
    input.classList.remove('error');
    
    const errorSpan = fieldContainer.querySelector('.field-error');
    if (errorSpan) {
      errorSpan.style.display = 'none';
    }
  }
  
  async handleSubmit() {
    console.log('📝 Submitting registration form...');
    
    // Validate all fields
    const isValid = await this.validateAllFields();
    
    if (!isValid) {
      this.showError('Please fix all validation errors before submitting.');
      return;
    }
    
    // Validate roster if team event
    if (this.rosterManager) {
      const rosterValid = await this.rosterManager.validateRoster();
      
      if (!rosterValid) {
        this.showError('Please fix team roster errors before submitting.');
        return;
      }
    }
    
    // Submit form
    const form = document.getElementById('registrationForm');
    form.submit();
  }
  
  async validateAllFields() {
    let allValid = true;
    
    for (const field of this.gameConfig.fields) {
      if (!field.is_required) continue;
      
      const input = document.getElementById(field.field_name);
      if (!input) continue;
      
      const isValid = await this.validateField(field.field_name, input.value);
      
      if (!isValid) {
        allValid = false;
      }
    }
    
    return allValid;
  }
  
  showLoading() {
    const container = document.getElementById('dynamic-fields-container');
    if (container) {
      container.innerHTML = `
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Loading registration form...</p>
        </div>
      `;
    }
  }
  
  hideLoading() {
    // Loading state will be replaced by rendered fields
  }
  
  showError(message) {
    // Create error toast/notification
    const toast = document.createElement('div');
    toast.className = 'error-toast';
    toast.innerHTML = `
      <i class="fas fa-exclamation-circle"></i>
      <span>${message}</span>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
      toast.classList.add('show');
    }, 100);
    
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 5000);
  }
}


/**
 * Game Configuration Loader
 * Fetches and caches game configuration from API
 */
class GameConfigLoader {
  constructor(gameCode) {
    this.gameCode = gameCode;
    this.cache = null;
  }
  
  async load() {
    // Return cached if available
    if (this.cache) {
      console.log('✅ Using cached game config');
      return this.cache;
    }
    
    console.log(`📡 Fetching game config for: ${this.gameCode}`);
    
    const response = await fetch(`/tournaments/api/games/${this.gameCode}/config/`);
    
    if (!response.ok) {
      throw new Error(`Failed to load game config: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to load game config');
    }
    
    // Cache the config
    this.cache = data.config;
    
    console.log(`✅ Loaded config: ${this.cache.fields.length} fields, ${this.cache.roles.length} roles`);
    
    return this.cache;
  }
  
  getField(fieldName) {
    return this.cache?.fields.find(f => f.field_name === fieldName);
  }
  
  getRole(roleCode) {
    return this.cache?.roles.find(r => r.role_code === roleCode);
  }
}


/**
 * Field Renderer
 * Renders form fields based on configuration
 */
class FieldRenderer {
  render(fieldConfig) {
    const container = document.createElement('div');
    container.className = 'form-field';
    container.dataset.fieldName = fieldConfig.field_name;
    
    // Label
    const label = this.createLabel(fieldConfig);
    container.appendChild(label);
    
    // Input element
    const input = this.createInput(fieldConfig);
    container.appendChild(input);
    
    // Help text
    if (fieldConfig.help_text) {
      const hint = document.createElement('span');
      hint.className = 'field-hint';
      hint.textContent = fieldConfig.help_text;
      container.appendChild(hint);
    }
    
    // Error message container
    const error = document.createElement('span');
    error.className = 'field-error';
    error.style.display = 'none';
    container.appendChild(error);
    
    return container;
  }
  
  createLabel(fieldConfig) {
    const label = document.createElement('label');
    label.setAttribute('for', fieldConfig.field_name);
    
    // Label text
    const labelText = document.createTextNode(fieldConfig.field_label);
    label.appendChild(labelText);
    
    // Required indicator
    if (fieldConfig.is_required) {
      const required = document.createElement('span');
      required.className = 'required';
      required.textContent = ' *';
      label.appendChild(required);
    } else {
      const optional = document.createElement('span');
      optional.className = 'optional';
      optional.textContent = ' (Optional)';
      label.appendChild(optional);
    }
    
    // Info icon with tooltip
    if (fieldConfig.help_text) {
      const info = document.createElement('i');
      info.className = 'fas fa-info-circle tooltip-icon';
      info.title = fieldConfig.help_text;
      label.appendChild(info);
    }
    
    return label;
  }
  
  createInput(fieldConfig) {
    switch (fieldConfig.field_type) {
      case 'SELECT':
        return this.createSelect(fieldConfig);
      case 'TEXTAREA':
        return this.createTextarea(fieldConfig);
      case 'NUMBER':
        return this.createNumber(fieldConfig);
      case 'EMAIL':
        return this.createEmail(fieldConfig);
      case 'PHONE':
        return this.createPhone(fieldConfig);
      case 'TEXT':
      default:
        return this.createText(fieldConfig);
    }
  }
  
  createText(fieldConfig) {
    const input = document.createElement('input');
    input.type = 'text';
    input.id = fieldConfig.field_name;
    input.name = fieldConfig.field_name;
    
    if (fieldConfig.placeholder) {
      input.placeholder = fieldConfig.placeholder;
    }
    
    if (fieldConfig.is_required) {
      input.required = true;
    }
    
    if (fieldConfig.validation_regex) {
      input.dataset.validationRegex = fieldConfig.validation_regex;
    }
    
    return input;
  }
  
  createSelect(fieldConfig) {
    const select = document.createElement('select');
    select.id = fieldConfig.field_name;
    select.name = fieldConfig.field_name;
    
    if (fieldConfig.is_required) {
      select.required = true;
    }
    
    // Add placeholder option
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = fieldConfig.placeholder || `Select ${fieldConfig.field_label}`;
    select.appendChild(placeholder);
    
    // Add choices
    if (fieldConfig.choices) {
      const choices = JSON.parse(fieldConfig.choices);
      choices.forEach(choice => {
        const option = document.createElement('option');
        option.value = choice.value;
        option.textContent = choice.label;
        select.appendChild(option);
      });
    }
    
    return select;
  }
  
  createTextarea(fieldConfig) {
    const textarea = document.createElement('textarea');
    textarea.id = fieldConfig.field_name;
    textarea.name = fieldConfig.field_name;
    textarea.rows = 4;
    
    if (fieldConfig.placeholder) {
      textarea.placeholder = fieldConfig.placeholder;
    }
    
    if (fieldConfig.is_required) {
      textarea.required = true;
    }
    
    return textarea;
  }
  
  createNumber(fieldConfig) {
    const input = document.createElement('input');
    input.type = 'number';
    input.id = fieldConfig.field_name;
    input.name = fieldConfig.field_name;
    
    if (fieldConfig.placeholder) {
      input.placeholder = fieldConfig.placeholder;
    }
    
    if (fieldConfig.is_required) {
      input.required = true;
    }
    
    return input;
  }
  
  createEmail(fieldConfig) {
    const input = document.createElement('input');
    input.type = 'email';
    input.id = fieldConfig.field_name;
    input.name = fieldConfig.field_name;
    
    if (fieldConfig.placeholder) {
      input.placeholder = fieldConfig.placeholder;
    }
    
    if (fieldConfig.is_required) {
      input.required = true;
    }
    
    return input;
  }
  
  createPhone(fieldConfig) {
    const input = document.createElement('input');
    input.type = 'tel';
    input.id = fieldConfig.field_name;
    input.name = fieldConfig.field_name;
    
    if (fieldConfig.placeholder) {
      input.placeholder = fieldConfig.placeholder;
    }
    
    if (fieldConfig.is_required) {
      input.required = true;
    }
    
    // Add pattern for validation
    if (fieldConfig.validation_regex) {
      input.pattern = fieldConfig.validation_regex;
    }
    
    return input;
  }
}


/**
 * Field Validator
 * Validates fields using backend API
 */
class FieldValidator {
  constructor(gameCode) {
    this.gameCode = gameCode;
    this.validationCache = new Map();
  }
  
  async validate(fieldName, value) {
    // Check cache first (for same value)
    const cacheKey = `${fieldName}:${value}`;
    if (this.validationCache.has(cacheKey)) {
      return this.validationCache.get(cacheKey);
    }
    
    try {
      const response = await fetch(`/tournaments/api/games/${this.gameCode}/validate/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          field_name: fieldName,
          value: value
        })
      });
      
      const result = await response.json();
      
      // Cache the result
      this.validationCache.set(cacheKey, result);
      
      return result;
    } catch (error) {
      console.error('Validation error:', error);
      return {
        success: false,
        is_valid: false,
        error: 'Validation failed. Please try again.'
      };
    }
  }
  
  clearCache() {
    this.validationCache.clear();
  }
}


/**
 * Auto-Fill Handler
 * Pre-populates fields from profile/team data
 */
class AutoFillHandler {
  fillProfileFields(profileData) {
    Object.keys(profileData).forEach(fieldName => {
      const input = document.getElementById(fieldName);
      
      if (input && profileData[fieldName]) {
        input.value = profileData[fieldName];
        input.classList.add('auto-filled');
        
        console.log(`✅ Auto-filled: ${fieldName}`);
      }
    });
  }
  
  fillTeamFields(teamData) {
    if (teamData.team_name) {
      const teamNameInput = document.getElementById('team_name');
      if (teamNameInput) {
        teamNameInput.value = teamData.team_name;
        teamNameInput.classList.add('auto-filled');
      }
    }
  }
}


/**
 * Roster Manager
 * Manages team roster for team events
 */
class RosterManager {
  constructor(roles, gameCode) {
    this.roles = roles;
    this.gameCode = gameCode;
    this.roster = [];
    
    this.initializeUI();
  }
  
  initializeUI() {
    const container = document.getElementById('roster-container');
    
    if (!container) {
      console.warn('No roster container found');
      return;
    }
    
    // Render roster table
    container.innerHTML = `
      <div class="roster-table">
        <div class="roster-header">
          <h3><i class="fas fa-users"></i> Team Roster</h3>
          <button type="button" class="btn-add-player" onclick="rosterManager.addPlayer()">
            <i class="fas fa-plus"></i> Add Player
          </button>
        </div>
        
        <table>
          <thead>
            <tr>
              <th>Player</th>
              <th>Role</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="roster-tbody">
            <!-- Players will be added here -->
          </tbody>
        </table>
        
        <div class="roster-validation-error" style="display:none;"></div>
      </div>
    `;
  }
  
  fillTeamData(teamData) {
    if (!teamData.members) return;
    
    teamData.members.forEach(member => {
      this.addPlayer({
        name: member.display_name || member.username,
        role: member.role || ''
      });
    });
  }
  
  addPlayer(data = {}) {
    const tbody = document.getElementById('roster-tbody');
    
    if (!tbody) return;
    
    const playerIndex = this.roster.length;
    
    const row = document.createElement('tr');
    row.dataset.playerIndex = playerIndex;
    
    row.innerHTML = `
      <td>
        <input 
          type="text" 
          name="roster_player_${playerIndex}_name" 
          placeholder="Player name"
          value="${data.name || ''}"
          required
        />
      </td>
      <td>
        <select name="roster_player_${playerIndex}_role" required>
          <option value="">Select role</option>
          ${this.roles.map(role => `
            <option value="${role.role_code}" ${data.role === role.role_code ? 'selected' : ''}>
              ${role.role_name}
            </option>
          `).join('')}
        </select>
      </td>
      <td>
        <button 
          type="button" 
          class="btn-remove-player" 
          onclick="rosterManager.removePlayer(${playerIndex})"
        >
          <i class="fas fa-trash"></i>
        </button>
      </td>
    `;
    
    tbody.appendChild(row);
    
    this.roster.push(data);
  }
  
  removePlayer(index) {
    const row = document.querySelector(`tr[data-player-index="${index}"]`);
    
    if (row) {
      row.remove();
    }
    
    this.roster.splice(index, 1);
  }
  
  async validateRoster() {
    const roles = this.getRosterRoles();
    
    try {
      const response = await fetch(`/tournaments/api/games/${this.gameCode}/validate-roles/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ roles })
      });
      
      const result = await response.json();
      
      if (!result.is_valid) {
        this.showRosterError(result.errors.join(', '));
        return false;
      }
      
      this.clearRosterError();
      return true;
    } catch (error) {
      console.error('Roster validation error:', error);
      this.showRosterError('Failed to validate roster');
      return false;
    }
  }
  
  getRosterRoles() {
    const roles = [];
    const selects = document.querySelectorAll('select[name^="roster_player_"][name$="_role"]');
    
    selects.forEach(select => {
      if (select.value) {
        roles.push(select.value);
      }
    });
    
    return roles;
  }
  
  showRosterError(message) {
    const errorDiv = document.querySelector('.roster-validation-error');
    
    if (errorDiv) {
      errorDiv.textContent = message;
      errorDiv.style.display = 'block';
    }
  }
  
  clearRosterError() {
    const errorDiv = document.querySelector('.roster-validation-error');
    
    if (errorDiv) {
      errorDiv.style.display = 'none';
    }
  }
}


// Export for global access
window.DynamicRegistrationForm = DynamicRegistrationForm;
window.GameConfigLoader = GameConfigLoader;
window.FieldRenderer = FieldRenderer;
window.FieldValidator = FieldValidator;
window.AutoFillHandler = AutoFillHandler;
window.RosterManager = RosterManager;
