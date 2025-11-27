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
    try {
      // Fetch player data from correct API endpoint
      // Root-level mount of user_profile URLs means API lives at /api/profile/<id>/
      const apiUrl = `/api/profile/${profileId}/`;
      const response = await fetch(apiUrl, { headers: { 'Accept': 'application/json' }});
      
      if (!response.ok) {
        // If endpoint not found (404) fall back to rosterData (graceful degradation)
        if (response.status === 404) {
          console.warn(`[PlayerProfileModal] 404 for ${apiUrl} – falling back to roster data only`);
          if (rosterData) {
            this.currentPlayer = this.buildFallbackPlayer(profileId, rosterData);
            this.createModal(this.currentPlayer);
            return;
          }
        }
        throw new Error('Failed to load player profile');
      }
      
      const data = await response.json();
      
      // Handle both response formats (direct data or wrapped in success/profile)
      let player;
      if (data.success && data.profile) {
        // API response format: {success: true, profile: {...}}
        player = data.profile;
      } else if (data.display_name || data.username) {
        // Direct response format: {...}
        player = data;
      } else {
        throw new Error(data.error || 'Invalid response format');
      }
      
      // Merge roster data if provided (includes game_id from roster API)
      if (rosterData) {
        player.game_id = rosterData.game_id;
        player.game_id_label = rosterData.game_id_label;
        player.mlbb_server_id = rosterData.mlbb_server_id;
        player.player_role = rosterData.player_role;
        player.role = rosterData.role;
        player.is_captain = rosterData.is_captain;
      }
      
      this.currentPlayer = player;
      
      // Create and show modal
      this.createModal(player);
      
    } catch (error) {
      console.error('Error loading player profile:', error);
      // Graceful fallback: use rosterData if available instead of error modal
      if (rosterData) {
        const fallback = this.buildFallbackPlayer(profileId, rosterData);
        this.currentPlayer = fallback;
        this.createModal(fallback);
      } else {
        this.showError('Unable to load player profile. Please try again.');
      }
    }
  }

  /**
   * Build a minimal player object from roster data when API fails
   */
  buildFallbackPlayer(profileId, rosterData) {
    return {
      display_name: rosterData.display_name || rosterData.username || `Player${profileId}`,
      username: rosterData.username || `player${profileId}`,
      avatar_url: rosterData.avatar || null,
      game_id: rosterData.game_id || '',
      game_id_label: rosterData.game_id_label || 'IGN',
      mlbb_server_id: rosterData.mlbb_server_id || '',
      is_captain: rosterData.is_captain || false,
      role: rosterData.role || 'Player',
      player_role: rosterData.player_role || '',
      bio: 'Esports Player',
      matches_played: rosterData.matches_played || 0,
      wins: rosterData.wins || 0,
      rating: rosterData.rating || 0,
      win_rate: rosterData.win_rate || '0%',
      region: rosterData.region || 'Global',
      teams: [],
      joined_date: '2025',
    };
  }

  /**
   * Create modal element with Eclipse design
   */
  createModal(player) {
    // Remove existing modal if any
    this.close();
    
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'eclipse-modal-overlay';
    
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'eclipse-modal';
    modal.innerHTML = this.renderModalContent(player);
    
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    this.modal = overlay;
    
    // Bind events
    this.bindModalEvents(overlay);
    
    // Prevent body scroll
    document.body.style.overflow = 'hidden';
  }

  /**
   * Render Eclipse modal content
   */
  renderModalContent(player) {
    const isCaptain = player.is_captain || false;
    const teamRole = player.team_role || player.role || 'Player';
    const inGameRole = (player.player_role && player.player_role.trim() !== '') ? player.player_role : (player.in_game_role && player.in_game_role.trim() !== '' ? player.in_game_role : 'Not assigned');
    const roleClass = this.getRoleClass(teamRole);
    
    return `
      <!-- Close Button -->
      <button class="eclipse-modal-close" data-action="close" aria-label="Close modal">
        <i class="fas fa-times"></i>
      </button>
      
      <!-- Modal Header -->
      <div class="eclipse-modal-header">
        <div class="eclipse-modal-avatar-wrapper">
          <div class="eclipse-modal-avatar">
            <div class="eclipse-modal-avatar-inner">
              ${player.avatar_url || player.avatar ?
                `<img src="${player.avatar_url || player.avatar}" alt="${this.escapeHtml(player.display_name)}">` :
                `<div class="eclipse-modal-avatar-placeholder">${this.getInitials(player.display_name)}</div>`
              }
            </div>
          </div>
          ${isCaptain ? `
            <div class="eclipse-modal-captain-badge" title="Team Captain">
              <i class="fas fa-star"></i>
            </div>
          ` : ''}
        </div>
        
        <h2 class="eclipse-modal-player-name">${this.escapeHtml(player.display_name)}</h2>
        <p class="eclipse-modal-ign">${player.game_id ? this.escapeHtml(player.game_id) : '@' + this.escapeHtml(player.username)}</p>
      </div>
      
      <!-- Modal Body -->
      <div class="eclipse-modal-body">
        <div class="eclipse-modal-grid">
          <!-- Game Info Column -->
          <div class="eclipse-modal-section">
            <h3 class="eclipse-modal-section-title">Game Info</h3>
            
            ${player.game_id ? `
              <div class="eclipse-modal-info-row">
                <span class="eclipse-modal-info-label">${player.game_id_label || 'Game ID'}</span>
                <span class="eclipse-modal-info-value highlight">${this.escapeHtml(player.game_id)}</span>
              </div>
            ` : ''}
            
            ${player.mlbb_server_id ? `
              <div class="eclipse-modal-info-row">
                <span class="eclipse-modal-info-label">Server ID</span>
                <span class="eclipse-modal-info-value">${this.escapeHtml(player.mlbb_server_id)}</span>
              </div>
            ` : ''}
            
            ${!player.game_id && !player.mlbb_server_id ? `
              <div class="eclipse-modal-info-row">
                <span class="eclipse-modal-info-label" style="opacity: 0.6;">No game ID provided</span>
              </div>
            ` : ''}
          </div>
          
          <!-- Team Status Column -->
          <div class="eclipse-modal-section">
            <h3 class="eclipse-modal-section-title blue">Team Status</h3>
            
            <div class="eclipse-modal-info-row">
              <span class="eclipse-modal-info-label">Team Role</span>
              <span class="eclipse-modal-role-badge ${roleClass}">${this.formatRole(teamRole)}</span>
            </div>
            
            <div class="eclipse-modal-info-row">
              <span class="eclipse-modal-info-label">In-Game Role</span>
              <span class="eclipse-modal-info-value ${inGameRole !== 'Not assigned' && inGameRole.trim() !== '' ? 'success' : 'warning'}">
                ${this.escapeHtml(inGameRole)}
              </span>
            </div>
            
            ${player.game_id ? `
            <div class="eclipse-modal-info-row">
              <span class="eclipse-modal-info-label">IGN</span>
              <span class="eclipse-modal-info-value highlight">${this.escapeHtml(player.game_id)}</span>
            </div>
            ` : ''}
          </div>
        </div>
        
        ${player.bio ? `
          <div class="eclipse-modal-section" style="margin-top: 24px;">
            <h3 class="eclipse-modal-section-title">About Player</h3>
            <p style="color: #A0AEC0; line-height: 1.6; margin: 0;">
              ${this.escapeHtml(player.bio)}
            </p>
          </div>
        ` : ''}
      </div>
      
      <!-- Modal Footer -->
      <div class="eclipse-modal-footer">
        <button class="eclipse-modal-cta-btn" onclick="window.location.href='/u/${player.username}/'">
          View Full Profile
          <i class="fas fa-arrow-right"></i>
        </button>
      </div>
    `;
  }
  
  /**
   * Format role name
   */
  formatRole(role) {
    if (!role) return 'Player';
    const roleStr = role.toString().toLowerCase();
    return roleStr.charAt(0).toUpperCase() + roleStr.slice(1);
  }
  
  /**
   * Get role CSS class
   */
  getRoleClass(role) {
    if (!role) return 'player';
    const roleStr = role.toString().toLowerCase();
    const roleMap = {
      'owner': 'owner',
      'manager': 'manager',
      'coach': 'coach',
      'captain': 'player',
      'player': 'player',
      'substitute': 'substitute',
      'sub': 'substitute'
    };
    return roleMap[roleStr] || 'player';
  }

  /**
   * Render social links
   */
  renderSocialLinks(player) {
    const socials = [];
    
    if (player.twitter) socials.push({ name: 'Twitter', url: player.twitter, icon: 'twitter', class: 'twitter' });
    if (player.discord_id) socials.push({ name: 'Discord', url: `https://discord.com/users/${player.discord_id}`, icon: 'discord', class: 'discord' });
    if (player.youtube_link) socials.push({ name: 'YouTube', url: player.youtube_link, icon: 'youtube', class: 'youtube' });
    if (player.twitch_link) socials.push({ name: 'Twitch', url: player.twitch_link, icon: 'twitch', class: 'twitch' });
    if (player.instagram) socials.push({ name: 'Instagram', url: player.instagram, icon: 'instagram', class: 'instagram' });
    
    if (socials.length === 0) return '';
    
    return `
      <div class="player-info-section">
        <h3 class="player-info-title">
          <i class="fas fa-share-nodes"></i>
          Social Links
        </h3>
        <div class="player-social-links">
          ${socials.map(social => `
            <a href="${social.url}" target="_blank" rel="noopener noreferrer" class="player-social-link ${social.class}">
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
