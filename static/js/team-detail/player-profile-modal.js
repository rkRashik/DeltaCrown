/**
 * Player Profile Modal
 * Shows detailed player information when clicking on roster card
 */

class PlayerProfileModal {
  constructor() {
    this.modal = null;
    this.currentPlayer = null;
  }

  /**
   * Show player profile modal
   * @param {string} profileId - The profile ID
   * @param {object} rosterData - Optional roster data with game ID (from roster card)
   */
  async show(profileId, rosterData = null) {
    console.log('[PlayerModal] Opening modal for profile ID:', profileId);
    console.log('[PlayerModal] Roster data:', rosterData);
    
    try {
      // Fetch player data
      const url = `/user/api/profile/${profileId}/`;
      console.log('[PlayerModal] Fetching from:', url);
      
      const response = await fetch(url);
      
      console.log('[PlayerModal] Response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('[PlayerModal] API Error:', response.status, errorText);
        throw new Error(`Failed to load player profile (${response.status})`);
      }
      
      const player = await response.json();
      console.log('[PlayerModal] Player data received:', player);
      
      // Merge roster data if provided (includes game_id from roster API)
      if (rosterData) {
        player.game_id = rosterData.game_id;
        player.game_id_label = rosterData.game_id_label;
        player.mlbb_server_id = rosterData.mlbb_server_id;
        console.log('[PlayerModal] Merged roster data into player object');
      }
      
      this.currentPlayer = player;
      
      // Create and show modal
      this.createModal(player);
      
    } catch (error) {
      console.error('[PlayerModal] Error loading player profile:', error);
      this.showError(`Unable to load player profile. Please try again. (${error.message})`);
    }
  }

  /**
   * Create modal element
   */
  createModal(player) {
    // Remove existing modal if any
    this.close();
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'player-profile-modal';
    modal.innerHTML = this.renderModalContent(player);
    
    document.body.appendChild(modal);
    this.modal = modal;
    
    // Trigger animation
    setTimeout(() => modal.classList.add('active'), 10);
    
    // Bind events
    this.bindModalEvents(modal);
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
  }

  /**
   * Render modal content
   */
  renderModalContent(player) {
    // Extract in-game name from game_id if it exists (for display in header)
    const inGameName = player.game_id ? player.game_id : null;
    
    return `
      <div class="player-profile-content">
        <button class="modal-close-btn" data-action="close">
          <i class="fas fa-times"></i>
        </button>
        
        <div class="player-modal-header">
          ${player.avatar_url || player.avatar ?
            `<img src="${player.avatar_url || player.avatar}" class="player-modal-avatar-large" alt="${this.escapeHtml(player.display_name)}">` :
            `<div class="player-modal-avatar-placeholder">${this.getInitials(player.display_name)}</div>`
          }
          <h2 class="player-modal-name">${this.escapeHtml(player.display_name)}</h2>
          ${inGameName ? `
            <p class="player-modal-ingame-name">
              <i class="fas fa-gamepad"></i>
              ${this.escapeHtml(inGameName)}
            </p>
          ` : ''}
          <p class="player-modal-username">@${this.escapeHtml(player.username)}</p>
        </div>
        
        <div class="player-modal-body">
          ${player.bio ? `
            <div class="player-info-section">
              <h3 class="player-info-title">
                <i class="fas fa-user"></i>
                About
              </h3>
              <p class="player-bio">${this.escapeHtml(player.bio)}</p>
            </div>
          ` : ''}
          
          ${player.game_id ? `
            <div class="player-info-section">
              <h3 class="player-info-title">
                <i class="fas fa-gamepad"></i>
                Game Identity
              </h3>
              <div class="player-game-id-display">
                <span class="player-game-id-label">${player.game_id_label || 'In-Game ID'}</span>
                <div class="player-game-id-text">
                  <i class="fas fa-id-card"></i>
                  ${this.escapeHtml(player.game_id)}
                </div>
              </div>
              ${player.mlbb_server_id ? `
                <div class="player-game-id-display" style="margin-top: 0.75rem;">
                  <span class="player-game-id-label">Server ID</span>
                  <div class="player-game-id-text">
                    <i class="fas fa-server"></i>
                    ${this.escapeHtml(player.mlbb_server_id)}
                  </div>
                </div>
              ` : ''}
            </div>
          ` : ''}
          
          ${this.renderSocialLinks(player)}
          
          ${this.renderStats(player)}
          
          ${player.teams && player.teams.length > 0 ? `
            <div class="player-info-section">
              <h3 class="player-info-title">
                <i class="fas fa-users"></i>
                Teams
              </h3>
              <div class="player-teams-list">
                ${player.teams.map(team => `
                  <div class="player-team-item">
                    <i class="fas fa-shield-alt"></i>
                    <span class="team-name">${this.escapeHtml(team.name)}</span>
                    <span class="team-role">${team.role}</span>
                    ${team.game ? `<span class="team-game">${team.game}</span>` : ''}
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
          
          <a href="/user/u/${player.username}/" class="player-view-full-profile">
            <i class="fas fa-external-link-alt"></i>
            View Full Profile
          </a>
        </div>
      </div>
    `;
  }

  /**
   * Render social links
   */
  renderSocialLinks(player) {
    const socials = [];
    
    // Add social links that exist in the profile model
    if (player.discord_id) {
      socials.push({ 
        name: 'Discord', 
        url: player.discord_id.startsWith('http') ? player.discord_id : `https://discord.com/users/${player.discord_id}`, 
        icon: 'discord', 
        class: 'discord' 
      });
    }
    if (player.youtube_link) {
      socials.push({ 
        name: 'YouTube', 
        url: player.youtube_link, 
        icon: 'youtube', 
        class: 'youtube' 
      });
    }
    if (player.twitch_link) {
      socials.push({ 
        name: 'Twitch', 
        url: player.twitch_link, 
        icon: 'twitch', 
        class: 'twitch' 
      });
    }
    
    // These fields don't exist in the model yet, but handle them if they're added later
    if (player.twitter) {
      socials.push({ 
        name: 'Twitter', 
        url: player.twitter.startsWith('http') ? player.twitter : `https://twitter.com/${player.twitter}`, 
        icon: 'twitter', 
        class: 'twitter' 
      });
    }
    if (player.instagram) {
      socials.push({ 
        name: 'Instagram', 
        url: player.instagram.startsWith('http') ? player.instagram : `https://instagram.com/${player.instagram}`, 
        icon: 'instagram', 
        class: 'instagram' 
      });
    }
    
    if (socials.length === 0) return '';
    
    return `
      <div class="player-info-section">
        <h3 class="player-info-title">
          <i class="fas fa-share-nodes"></i>
          Social Links
        </h3>
        <div class="player-social-links">
          ${socials.map(social => `
            <a href="${this.escapeHtml(social.url)}" target="_blank" rel="noopener noreferrer" class="player-social-link ${social.class}">
              <i class="fab fa-${social.icon}"></i>
              <span>${social.name}</span>
            </a>
          `).join('')}
        </div>
      </div>
    `;
  }

  /**
   * Render player stats
   */
  renderStats(player) {
    if (!player.matches_played || player.matches_played === 0) return '';
    
    return `
      <div class="player-info-section">
        <h3 class="player-info-title">
          <i class="fas fa-chart-line"></i>
          Performance Stats
        </h3>
        <div class="player-stats-grid">
          <div class="player-stat-box">
            <div class="stat-value">${player.matches_played}</div>
            <div class="stat-label">Matches</div>
          </div>
          <div class="player-stat-box">
            <div class="stat-value">${player.wins || 0}</div>
            <div class="stat-label">Wins</div>
          </div>
          <div class="player-stat-box highlight">
            <div class="stat-value">${player.win_rate || '0%'}</div>
            <div class="stat-label">Win Rate</div>
          </div>
          ${player.rating ? `
            <div class="player-stat-box">
              <div class="stat-value">${player.rating}</div>
              <div class="stat-label">Rating</div>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  /**
   * Bind modal events
   */
  bindModalEvents(modal) {
    // Close button
    const closeBtn = modal.querySelector('[data-action="close"]');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.close());
    }
    
    // Click outside to close
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        this.close();
      }
    });
    
    // Escape key to close
    this.escapeHandler = (e) => {
      if (e.key === 'Escape') {
        this.close();
      }
    };
    document.addEventListener('keydown', this.escapeHandler);
  }

  /**
   * Close modal
   */
  close() {
    if (this.modal) {
      this.modal.classList.remove('active');
      
      setTimeout(() => {
        if (this.modal && this.modal.parentNode) {
          this.modal.parentNode.removeChild(this.modal);
        }
        this.modal = null;
      }, 300);
      
      // Restore body scroll
      document.body.style.overflow = '';
      
      // Remove escape listener
      if (this.escapeHandler) {
        document.removeEventListener('keydown', this.escapeHandler);
        this.escapeHandler = null;
      }
    }
  }

  /**
   * Show error message
   */
  showError(message) {
    // Create simple error modal
    const modal = document.createElement('div');
    modal.className = 'player-profile-modal active';
    modal.innerHTML = `
      <div class="player-profile-content">
        <button class="modal-close-btn" onclick="this.closest('.player-profile-modal').remove()">
          <i class="fas fa-times"></i>
        </button>
        <div class="player-modal-body" style="text-align: center; padding: 4rem 2rem;">
          <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #ef4444; margin-bottom: 1rem;"></i>
          <h3 style="font-size: 1.5rem; margin-bottom: 0.5rem;">Error</h3>
          <p style="color: var(--text-muted);">${message}</p>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
    setTimeout(() => modal.remove(), 3000);
  }

  /**
   * Get initials from name
   */
  getInitials(name) {
    if (!name) return '?';
    
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.substring(0, 2).toUpperCase();
  }

  /**
   * Escape HTML
   */
  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Initialize global instance
window.playerModal = new PlayerProfileModal();
