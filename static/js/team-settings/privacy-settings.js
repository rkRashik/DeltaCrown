/**
 * Privacy Settings Manager for Team Settings
 * Handles all privacy-related settings with live updates
 */

class PrivacySettingsManager {
  constructor(teamSlug, csrfToken) {
    this.teamSlug = teamSlug;
    this.csrfToken = csrfToken;
    this.settings = {};
    this.init();
  }

  async init() {
    await this.loadSettings();
    this.bindEvents();
  }

  async loadSettings() {
    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/privacy-settings/`, {
        headers: {
          'X-CSRFToken': this.csrfToken
        }
      });
      const data = await response.json();
      
      if (data.success) {
        this.settings = data.settings;
        this.updateUI();
      }
    } catch (error) {
      console.error('Error loading privacy settings:', error);
    }
  }

  updateUI() {
    // Update all toggle switches based on loaded settings
    Object.keys(this.settings).forEach(key => {
      const toggle = document.querySelector(`[name="${key}"]`);
      if (toggle && toggle.type === 'checkbox') {
        toggle.checked = this.settings[key];
      } else if (toggle) {
        toggle.value = this.settings[key];
      }
    });
  }

  bindEvents() {
    // Content Privacy Toggles
    this.bindToggle('is_public', 'Public Profile');
    this.bindToggle('show_roster_publicly', 'Public Roster');
    this.bindToggle('show_statistics_publicly', 'Public Statistics');
    this.bindToggle('show_tournaments_publicly', 'Public Tournaments');
    this.bindToggle('show_achievements_publicly', 'Public Achievements');

    // Member Permissions
    this.bindToggle('members_can_post', 'Members Can Post');
    this.bindToggle('require_post_approval', 'Require Post Approval');
    this.bindToggle('members_can_invite', 'Members Can Invite');

    // Join Settings
    this.bindToggle('allow_join_requests', 'Allow Join Requests');
    this.bindToggle('auto_accept_join_requests', 'Auto-Accept Requests');
    this.bindToggle('require_application_message', 'Require Application Message');

    // Display Settings
    this.bindToggle('hide_member_stats', 'Hide Member Stats');
    this.bindToggle('hide_social_links', 'Hide Social Links');
    this.bindToggle('show_captain_only', 'Show Captain Only');

    // Text inputs
    this.bindInput('min_rank_requirement', 'Minimum Rank');

    // Save all button
    const saveAllBtn = document.getElementById('save-all-privacy-settings');
    if (saveAllBtn) {
      saveAllBtn.addEventListener('click', () => this.saveAllSettings());
    }
  }

  bindToggle(settingName, displayName) {
    const toggle = document.querySelector(`[name="${settingName}"]`);
    if (!toggle) return;

    toggle.addEventListener('change', async (e) => {
      const newValue = e.target.checked;
      await this.updateSetting(settingName, newValue, displayName);
    });
  }

  bindInput(settingName, displayName) {
    const input = document.querySelector(`[name="${settingName}"]`);
    if (!input) return;

    // Debounced save on input
    let timeout;
    input.addEventListener('input', (e) => {
      clearTimeout(timeout);
      timeout = setTimeout(async () => {
        await this.updateSetting(settingName, e.target.value, displayName);
      }, 1000);
    });
  }

  async updateSetting(settingName, value, displayName) {
    try {
      const formData = new FormData();
      formData.append(settingName, value);

      const response = await fetch(`/teams/api/${this.teamSlug}/update-privacy/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.csrfToken
        },
        body: formData
      });

      const data = await response.json();

      if (data.success) {
        this.settings[settingName] = value;
        this.showSuccess(`${displayName} updated`);
      } else {
        this.showError(data.error || `Failed to update ${displayName}`);
        // Revert toggle
        const toggle = document.querySelector(`[name="${settingName}"]`);
        if (toggle && toggle.type === 'checkbox') {
          toggle.checked = this.settings[settingName];
        }
      }
    } catch (error) {
      console.error('Error updating setting:', error);
      this.showError(`Failed to update ${displayName}`);
    }
  }

  async saveAllSettings() {
    const formData = new FormData();
    
    // Collect all settings from form
    document.querySelectorAll('[data-privacy-setting]').forEach(input => {
      const name = input.name;
      const value = input.type === 'checkbox' ? input.checked : input.value;
      formData.append(name, value);
    });

    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/update-privacy/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.csrfToken
        },
        body: formData
      });

      const data = await response.json();

      if (data.success) {
        this.showSuccess('All privacy settings saved successfully');
        await this.loadSettings();
      } else {
        this.showError(data.error || 'Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving all settings:', error);
      this.showError('Failed to save settings');
    }
  }

  showSuccess(message) {
    this.showToast(message, 'success');
  }

  showError(message) {
    this.showToast(message, 'error');
  }

  showToast(message, type) {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = `privacy-toast privacy-toast-${type}`;
    toast.innerHTML = `
      <i class="fa-solid fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
      <span>${message}</span>
    `;
    
    const container = document.getElementById('privacy-toast-container');
    if (container) {
      container.appendChild(toast);
      
      // Auto-remove after 3 seconds
      setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
      }, 3000);
    } else {
      // Fallback to alert
      if (type === 'success') {
        dcLog('✓', message);
      } else {
        console.error('✗', message);
      }
    }
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const privacyContainer = document.getElementById('privacy-settings-container');
  if (privacyContainer) {
    const teamSlug = privacyContainer.dataset.teamSlug;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    if (teamSlug && csrfToken) {
      new PrivacySettingsManager(teamSlug, csrfToken);
    }
  }
});
