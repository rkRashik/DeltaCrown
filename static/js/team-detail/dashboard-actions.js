/**
 * Team Dashboard Sidebar Actions
 * Handles quick actions from the Team Dashboard card in sidebar
 */

(function() {
  'use strict';

  // Wait for DOM to be ready
  document.addEventListener('DOMContentLoaded', function() {
    initDashboardActions();
  });

  function initDashboardActions() {
    // Manage Roster button
    const manageRosterBtn = document.getElementById('manage-roster-btn');
    if (manageRosterBtn) {
      manageRosterBtn.addEventListener('click', showRosterManagementModal);
    }

    // Team Settings button
    const teamSettingsBtn = document.getElementById('team-settings-btn');
    if (teamSettingsBtn) {
      teamSettingsBtn.addEventListener('click', showTeamSettingsModal);
    }
  }

  /**
   * Show Roster Management Modal
   */
  function showRosterManagementModal() {
    const teamSlug = getTeamSlug();
    
    const modal = createModal({
      title: 'Manage Team Roster',
      size: 'large',
      content: `
        <div class="roster-management-modal">
          <div class="modal-tabs">
            <button class="modal-tab active" data-tab="add-player">
              <i class="fa-solid fa-user-plus"></i>
              Add Player
            </button>
            <button class="modal-tab" data-tab="invitations">
              <i class="fa-solid fa-envelope"></i>
              Invitations
            </button>
            <button class="modal-tab" data-tab="requests">
              <i class="fa-solid fa-inbox"></i>
              Join Requests
            </button>
          </div>
          
          <div class="modal-tab-content">
            <!-- Add Player Tab -->
            <div class="tab-pane active" id="add-player-pane">
              <form id="add-player-form" class="form-vertical">
                <div class="form-group">
                  <label for="player-search">Search for Player</label>
                  <input type="text" id="player-search" class="form-control" 
                         placeholder="Enter username or email...">
                  <div id="player-search-results" class="search-results"></div>
                </div>
                
                <div class="form-group">
                  <label for="player-role">Role</label>
                  <select id="player-role" class="form-control">
                    <option value="player">Player</option>
                    <option value="substitute">Substitute</option>
                    <option value="coach">Coach</option>
                    <option value="manager">Manager</option>
                  </select>
                </div>
                
                <div class="form-actions">
                  <button type="submit" class="btn btn-primary">
                    <i class="fa-solid fa-paper-plane"></i>
                    Send Invitation
                  </button>
                </div>
              </form>
            </div>
            
            <!-- Invitations Tab -->
            <div class="tab-pane" id="invitations-pane">
              <div class="invitations-list">
                <p class="text-muted text-center">Loading invitations...</p>
              </div>
            </div>
            
            <!-- Join Requests Tab -->
            <div class="tab-pane" id="requests-pane">
              <div class="requests-list">
                <p class="text-muted text-center">Loading join requests...</p>
              </div>
            </div>
          </div>
        </div>
      `
    });

    // Handle tab switching
    modal.querySelectorAll('.modal-tab').forEach(tab => {
      tab.addEventListener('click', function() {
        const tabName = this.getAttribute('data-tab');
        switchModalTab(modal, tabName);
      });
    });

    // Handle player search
    const searchInput = modal.querySelector('#player-search');
    if (searchInput) {
      let searchTimeout;
      searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => searchPlayers(this.value), 300);
      });
    }
  }

  /**
   * Show Team Settings Modal
   */
  function showTeamSettingsModal() {
    const teamSlug = getTeamSlug();
    const teamData = getPageData();
    
    const modal = createModal({
      title: 'Team Settings',
      size: 'large',
      content: `
        <div class="team-settings-modal">
          <div class="modal-tabs">
            <button class="modal-tab active" data-tab="general">
              <i class="fa-solid fa-info-circle"></i>
              General
            </button>
            <button class="modal-tab" data-tab="branding">
              <i class="fa-solid fa-palette"></i>
              Branding
            </button>
            <button class="modal-tab" data-tab="privacy">
              <i class="fa-solid fa-lock"></i>
              Privacy
            </button>
            <button class="modal-tab" data-tab="danger">
              <i class="fa-solid fa-exclamation-triangle"></i>
              Danger Zone
            </button>
          </div>
          
          <div class="modal-tab-content">
            <!-- General Settings -->
            <div class="tab-pane active" id="general-pane">
              <form id="general-settings-form" class="form-vertical">
                <div class="form-group">
                  <label for="team-name">Team Name *</label>
                  <input type="text" id="team-name" class="form-control" 
                         value="${teamData.team.name}" required>
                </div>
                
                <div class="form-group">
                  <label for="team-tag">Team Tag</label>
                  <input type="text" id="team-tag" class="form-control" 
                         placeholder="Enter team tag (e.g., TSM)" maxlength="10">
                </div>
                
                <div class="form-group">
                  <label for="team-description">Description</label>
                  <textarea id="team-description" class="form-control" rows="4"
                            placeholder="Tell others about your team...">${teamData.team.description || ''}</textarea>
                </div>
                
                <div class="form-group">
                  <label for="team-tagline">Tagline</label>
                  <input type="text" id="team-tagline" class="form-control" 
                         placeholder="Enter a catchy tagline" maxlength="100">
                </div>
                
                <div class="form-actions">
                  <button type="submit" class="btn btn-primary">
                    <i class="fa-solid fa-save"></i>
                    Save Changes
                  </button>
                </div>
              </form>
            </div>
            
            <!-- Branding Settings -->
            <div class="tab-pane" id="branding-pane">
              <form id="branding-settings-form" class="form-vertical">
                <div class="form-group">
                  <label>Team Logo</label>
                  <div class="image-upload-preview">
                    <img id="logo-preview" src="/static/img/deltaCrown_logos/logo.svg" alt="Logo Preview">
                    <input type="file" id="logo-upload" accept="image/*" hidden>
                    <button type="button" class="btn btn-secondary" onclick="document.getElementById('logo-upload').click()">
                      <i class="fa-solid fa-upload"></i>
                      Upload Logo
                    </button>
                  </div>
                  <small class="form-text">Recommended: 500x500px, PNG or JPG</small>
                </div>
                
                <div class="form-group">
                  <label>Banner Image</label>
                  <div class="image-upload-preview banner">
                    <img id="banner-preview" src="/static/img/game_cards/VALORANT.jpg" alt="Banner Preview">
                    <input type="file" id="banner-upload" accept="image/*" hidden>
                    <button type="button" class="btn btn-secondary" onclick="document.getElementById('banner-upload').click()">
                      <i class="fa-solid fa-upload"></i>
                      Upload Banner
                    </button>
                  </div>
                  <small class="form-text">Recommended: 1920x400px, PNG or JPG</small>
                </div>
                
                <div class="form-actions">
                  <button type="submit" class="btn btn-primary">
                    <i class="fa-solid fa-save"></i>
                    Save Branding
                  </button>
                </div>
              </form>
            </div>
            
            <!-- Privacy Settings -->
            <div class="tab-pane" id="privacy-pane">
              <form id="privacy-settings-form" class="form-vertical">
                <div class="form-group">
                  <label class="checkbox-label">
                    <input type="checkbox" id="is-public" ${teamData.team.is_public ? 'checked' : ''}>
                    <span>Public Team</span>
                  </label>
                  <small class="form-text">Public teams are visible to everyone</small>
                </div>
                
                <div class="form-group">
                  <label class="checkbox-label">
                    <input type="checkbox" id="is-recruiting">
                    <span>Open for Recruitment</span>
                  </label>
                  <small class="form-text">Allow players to request to join your team</small>
                </div>
                
                <div class="form-actions">
                  <button type="submit" class="btn btn-primary">
                    <i class="fa-solid fa-save"></i>
                    Save Privacy Settings
                  </button>
                </div>
              </form>
            </div>
            
            <!-- Danger Zone -->
            <div class="tab-pane" id="danger-pane">
              <div class="danger-zone">
                <div class="danger-action">
                  <div class="danger-info">
                    <h4>Transfer Team Ownership</h4>
                    <p>Transfer captain role to another team member</p>
                  </div>
                  <button type="button" class="btn btn-warning">
                    <i class="fa-solid fa-exchange-alt"></i>
                    Transfer Ownership
                  </button>
                </div>
                
                <div class="danger-action">
                  <div class="danger-info">
                    <h4>Delete Team</h4>
                    <p>Permanently delete this team. This action cannot be undone.</p>
                  </div>
                  <button type="button" class="btn btn-danger" onclick="confirmDeleteTeam()">
                    <i class="fa-solid fa-trash"></i>
                    Delete Team
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      `
    });

    // Handle tab switching
    modal.querySelectorAll('.modal-tab').forEach(tab => {
      tab.addEventListener('click', function() {
        const tabName = this.getAttribute('data-tab');
        switchModalTab(modal, tabName);
      });
    });

    // Handle form submissions
    setupSettingsForms(modal);
  }

  /**
   * Create Modal
   */
  function createModal({ title, content, size = 'medium' }) {
    const existingModal = document.querySelector('.dashboard-modal-overlay');
    if (existingModal) {
      existingModal.remove();
    }

    const overlay = document.createElement('div');
    overlay.className = 'dashboard-modal-overlay';
    overlay.innerHTML = `
      <div class="dashboard-modal ${size}">
        <div class="dashboard-modal-header">
          <h3>${title}</h3>
          <button class="dashboard-modal-close">&times;</button>
        </div>
        <div class="dashboard-modal-body">
          ${content}
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    // Close handlers
    overlay.querySelector('.dashboard-modal-close').addEventListener('click', () => overlay.remove());
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.remove();
    });

    return overlay;
  }

  /**
   * Switch Modal Tab
   */
  function switchModalTab(modal, tabName) {
    // Update tab buttons
    modal.querySelectorAll('.modal-tab').forEach(tab => {
      tab.classList.toggle('active', tab.getAttribute('data-tab') === tabName);
    });

    // Update tab panes
    modal.querySelectorAll('.tab-pane').forEach(pane => {
      pane.classList.toggle('active', pane.id === `${tabName}-pane`);
    });
  }

  /**
   * Search Players
   */
  async function searchPlayers(query) {
    const resultsContainer = document.getElementById('player-search-results');
    if (!query || query.length < 2) {
      resultsContainer.innerHTML = '';
      return;
    }

    resultsContainer.innerHTML = '<div class="text-center"><i class="fa-solid fa-spinner fa-spin"></i> Searching...</div>';

    try {
      // TODO: Implement actual player search API
      setTimeout(() => {
        resultsContainer.innerHTML = `
          <div class="search-result-item">
            <img src="/static/img/user_avatar/default-avatar.png" alt="Player">
            <span>Example Player</span>
            <button class="btn btn-sm btn-primary">Select</button>
          </div>
        `;
      }, 500);
    } catch (error) {
      resultsContainer.innerHTML = '<div class="text-error">Failed to search players</div>';
    }
  }

  /**
   * Setup Settings Forms
   */
  function setupSettingsForms(modal) {
    const generalForm = modal.querySelector('#general-settings-form');
    if (generalForm) {
      generalForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        // TODO: Implement save general settings
        alert('General settings saved! (API integration pending)');
      });
    }

    const brandingForm = modal.querySelector('#branding-settings-form');
    if (brandingForm) {
      brandingForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        // TODO: Implement save branding
        alert('Branding saved! (API integration pending)');
      });
    }

    const privacyForm = modal.querySelector('#privacy-settings-form');
    if (privacyForm) {
      privacyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        // TODO: Implement save privacy settings
        alert('Privacy settings saved! (API integration pending)');
      });
    }
  }

  /**
   * Helper Functions
   */
  function getTeamSlug() {
    const pageData = getPageData();
    return pageData && pageData.team ? pageData.team.slug : null;
  }

  function getPageData() {
    const dataEl = document.getElementById('page-data');
    if (dataEl) {
      try {
        return JSON.parse(dataEl.textContent);
      } catch (e) {
        console.error('Failed to parse page data:', e);
      }
    }
    return null;
  }

  // Export for testing
  window.DashboardActions = {
    showRosterManagementModal,
    showTeamSettingsModal
  };
})();
