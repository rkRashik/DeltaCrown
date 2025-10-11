/**
 * Roster Tab Component - Complete Rebuild
 * Displays team members with proper data fetching
 */

class RosterTab {
  constructor(api) {
    this.api = api;
    this.logger = new Logger('RosterTab');
    this.members = [];
  }

  /**
   * Render roster tab content
   */
  async render(container, data) {
    this.logger.info('Rendering roster tab');
    
    // Show loading state
    container.innerHTML = `
      <div class="roster-loading">
        <div class="spinner"></div>
        <p>Loading team roster...</p>
      </div>
    `;

    try {
      // Fetch basic roster data (works for everyone)
      this.logger.info('Fetching roster data');
      const rosterResponse = await this.api.getRoster();
      this.logger.info('Roster response received:', rosterResponse);
      
      // Transform to expected format
      const rosterData = {
        members: rosterResponse.active_players || [],
        game_name: null
      };
      
      this.members = rosterData.members;
      this.logger.info(`Loaded ${this.members.length} members`);
      const isMember = data.permissions?.is_member || false;
      const showGameIds = false; // Will be enabled later with member-only API
      
      // Render the roster
      container.innerHTML = `
        <div class="roster-tab">
          <!-- Header -->
          <div class="roster-header-section">
            <h2 class="roster-title">
              <i class="fa-solid fa-users"></i>
              Team Roster
              <span class="roster-count-badge">${this.members.length} ${this.members.length === 1 ? 'Member' : 'Members'}</span>
            </h2>
            ${rosterData.game_name ? `
              <p class="roster-subtitle">In-game identities for ${rosterData.game_name}</p>
            ` : ''}
          </div>

          <!-- Members Grid -->
          ${this.members.length > 0 ? `
            <div class="roster-grid-modern">
              ${this.members.map(member => this.renderMemberCardModern(member, showGameIds)).join('')}
            </div>
          ` : `
            <div class="roster-empty-state">
              <div class="roster-empty-icon">
                <i class="fas fa-users-slash"></i>
              </div>
              <h3 class="roster-empty-title">No Roster Members Yet</h3>
              <p class="roster-empty-message">This team hasn't added any members to their roster yet.</p>
            </div>
          `}
        </div>
      `;

      // Bind events
      this.bindEvents(container, data);
      
    } catch (error) {
      this.logger.error('Failed to load roster:', error);
      container.innerHTML = `
        <div class="error-state">
          <i class="fa-solid fa-exclamation-triangle"></i>
          <h3>Failed to Load Roster</h3>
          <p>${error.message}</p>
          <button class="btn btn-primary" onclick="window.location.reload()">
            <i class="fa-solid fa-refresh"></i>
            Retry
          </button>
        </div>
      `;
    }
  }

  /**
   * Render modern member card with game ID
   */
  renderMemberCardModern(member, showGameId = false) {
    const isCaptain = member.role === 'CAPTAIN' || member.role === 'captain' || member.is_captain;
    const gameId = member.game_id || 'Not provided';
    const hasGameId = member.game_id && member.game_id !== 'Not provided';
    
    // Handle both new API (profile_id) and old API (id) formats
    const profileId = member.profile_id || member.id;
    const realName = member.real_name || member.display_name || member.username;
    const inGameName = member.in_game_name || member.display_name || member.username;
    const avatar = member.avatar || member.avatar_url;
    const username = member.username || realName;
    
    // Format display name as "RealName (InGameName)" if they differ
    let displayNameFormatted = realName;
    if (inGameName && inGameName !== realName) {
      displayNameFormatted = `${realName} (${inGameName})`;
    }
    
    // Create a data attribute with roster data for the modal
    const rosterDataJson = JSON.stringify({
      game_id: member.game_id,
      game_id_label: member.game_id_label,
      mlbb_server_id: member.mlbb_server_id
    }).replace(/"/g, '&quot;');
    
    return `
      <div class="roster-card-modern ${isCaptain ? 'captain' : ''}" 
           data-profile-id="${profileId}"
           data-roster-data="${rosterDataJson}"
           role="button"
           tabindex="0"
           aria-label="View ${this.escapeHtml(displayNameFormatted)}'s profile">
        
        <div class="roster-card-header">
          <div class="roster-avatar-wrapper">
            ${avatar ? 
              `<img src="${avatar}" class="roster-avatar" alt="${this.escapeHtml(displayNameFormatted)}" loading="lazy">` :
              `<div class="roster-avatar-placeholder">${this.getInitials(realName)}</div>`
            }
            <div class="roster-status-dot ${member.is_online ? '' : 'offline'}" 
                 title="${member.is_online ? 'Online' : 'Offline'}"></div>
          </div>
          
          <div class="roster-player-info">
            <h3 class="roster-player-name">
              ${isCaptain ? '<i class="fas fa-crown captain-crown" title="Team Captain"></i>' : ''}
              ${this.escapeHtml(displayNameFormatted)}
            </h3>
            <p class="roster-player-username">
              <i class="fas fa-at"></i>${this.escapeHtml(username)}
            </p>
          </div>
        </div>
        
        <div class="roster-role-badge">
          <i class="${this.getRoleIcon(member.role)}"></i>
          ${member.role_display || this.formatRole(member.role)}
        </div>
        
        ${showGameId ? `
          <div class="roster-game-id-section">
            <span class="roster-game-id-label">${member.game_id_label || 'Game ID'}</span>
            <div class="roster-game-id-value ${!hasGameId ? 'not-provided' : ''}">
              <i class="fas fa-${hasGameId ? 'gamepad' : 'exclamation-circle'}"></i>
              ${this.escapeHtml(gameId)}
            </div>
            ${member.mlbb_server_id ? `
              <div class="roster-game-id-value" style="margin-top: 0.5rem;">
                <i class="fas fa-server"></i>
                Server: ${this.escapeHtml(member.mlbb_server_id)}
              </div>
            ` : ''}
          </div>
        ` : ''}
        
        <div class="roster-card-footer">
          <span class="roster-joined-date">
            <i class="fas fa-calendar"></i>
            Joined ${this.formatDateRelative(member.joined_at || member.join_date)}
          </span>
          <span class="roster-view-profile-btn">
            <i class="fas fa-user"></i>
            View Profile
          </span>
        </div>
      </div>
    `;
  }

  /**
   * Render member card - ESPORTS STYLE DESIGN
   */
  renderMemberCard(member, permissions) {
    const isCaptain = member.role === 'CAPTAIN' || member.role === 'captain' || member.is_captain;
    const roleDisplay = this.formatRole(member.role);
    const roleColor = this.getRoleColor(member.role);
    const profileUrl = `/profile/${member.username}/`;
    
    return `
      <a href="${profileUrl}" class="esports-player-card" data-member-id="${member.id}">
        ${isCaptain ? '<div class="captain-badge-ribbon"><i class="fa-solid fa-crown"></i></div>' : ''}
        
        <div class="player-card-backdrop"></div>
        
        <div class="player-card-content">
          <div class="player-avatar-section">
            <div class="avatar-glow" style="background: ${roleColor}20;"></div>
            <img src="${member.avatar_url || '/static/img/user_avatar/default-avatar.png'}" 
                 alt="${this.escapeHtml(member.in_game_name || member.username)}" 
                 class="player-avatar-lg">
          </div>
          
          <div class="player-identity">
            <div class="player-ign">${this.escapeHtml(member.in_game_name || member.username)}</div>
            <div class="player-handle">@${this.escapeHtml(member.username)}</div>
            <div class="player-role-tag" style="background: ${roleColor}15; border-color: ${roleColor}; color: ${roleColor}">
              <i class="${this.getRoleIcon(member.role)}"></i>
              <span>${roleDisplay}</span>
            </div>
          </div>

          ${member.stats && member.stats.matches_played > 0 ? `
            <div class="player-stats-row">
              <div class="stat-box">
                <div class="stat-value">${member.stats.matches_played}</div>
                <div class="stat-label">MATCHES</div>
              </div>
              <div class="stat-box highlight">
                <div class="stat-value">${member.stats.win_rate || 0}%</div>
                <div class="stat-label">WIN RATE</div>
              </div>
              <div class="stat-box">
                <div class="stat-value">${member.stats.mvp_count || 0}</div>
                <div class="stat-label">MVPs</div>
              </div>
            </div>
          ` : `
            <div class="player-stats-empty">
              <i class="fa-solid fa-hourglass-start"></i>
              <span>NO MATCHES YET</span>
            </div>
          `}

          <div class="player-card-footer">
            <div class="join-info">
              <i class="fa-solid fa-calendar-check"></i>
              <span>JOINED ${this.formatDateShort(member.join_date)}</span>
            </div>
            <div class="view-profile-hint">
              <i class="fa-solid fa-arrow-right"></i>
            </div>
          </div>
        </div>
      </a>
    `;
  }

  /**
   * Format date - short version for cards
   */
  formatDateShort(dateString) {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }).toUpperCase();
    } catch (e) {
      return 'RECENTLY';
    }
  }

  /**
   * Open player profile modal (called from roster card)
   */
  openPlayerModal(event, cardElement) {
    const card = cardElement || event.currentTarget;
    const profileId = card.dataset.profileId;
    const rosterDataStr = card.dataset.rosterData;
    
    this.logger.info('Opening player modal - Profile ID:', profileId);
    this.logger.info('Roster data string:', rosterDataStr);
    
    if (!profileId) {
      this.logger.error('No profile ID found on card!');
      alert('Error: No profile ID found');
      return;
    }
    
    if (!window.playerModal) {
      this.logger.error('window.playerModal not found!');
      alert('Error: Player modal not initialized');
      return;
    }
    
    try {
      const rosterData = rosterDataStr ? JSON.parse(rosterDataStr) : null;
      this.logger.info('Parsed roster data:', rosterData);
      window.playerModal.show(profileId, rosterData);
    } catch (error) {
      this.logger.error('Error opening player modal:', error);
      window.playerModal.show(profileId);
    }
  }

  /**
   * Bind event listeners
   */
  bindEvents(container, data) {
    // Add member button
    const addBtn = container.querySelector('#add-member-btn');
    if (addBtn) {
      addBtn.addEventListener('click', () => this.showAddMemberModal());
    }

    const addFirstBtn = container.querySelector('#add-first-member-btn');
    if (addFirstBtn) {
      addFirstBtn.addEventListener('click', () => this.showAddMemberModal());
    }
    
    // Bind roster card click events
    const rosterCards = container.querySelectorAll('.roster-card-modern');
    rosterCards.forEach(card => {
      card.addEventListener('click', (e) => this.openPlayerModal(e, card));
    });
  }

  /**
   * Show add member modal
   */
  showAddMemberModal() {
    alert('Add member functionality will be implemented with full backend integration');
  }

  /**
   * Format role
   */
  formatRole(role) {
    if (!role) return 'Player';
    const roleStr = role.toString().toLowerCase();
    return roleStr.charAt(0).toUpperCase() + roleStr.slice(1);
  }

  /**
   * Get role icon
   */
  getRoleIcon(role) {
    const roleStr = role ? role.toString().toLowerCase() : 'player';
    const icons = {
      captain: 'fa-solid fa-crown',
      player: 'fa-solid fa-user',
      sub: 'fa-solid fa-user-clock',
      substitute: 'fa-solid fa-user-clock',
      manager: 'fa-solid fa-user-tie',
      coach: 'fa-solid fa-chalkboard-user'
    };
    return icons[roleStr] || 'fa-solid fa-user';
  }

  /**
   * Get role color
   */
  getRoleColor(role) {
    const roleStr = role ? role.toString().toLowerCase() : 'player';
    const colors = {
      captain: '#fbbf24',
      player: '#3b82f6',
      sub: '#8b5cf6',
      substitute: '#8b5cf6',
      manager: '#ef4444',
      coach: '#10b981'
    };
    return colors[roleStr] || '#6b7280';
  }

  /**
   * Format date
   */
  formatDate(dateString) {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    } catch (e) {
      return 'Recently';
    }
  }

  /**
   * Format date relative (for roster cards)
   */
  formatDateRelative(dateString) {
    if (!dateString) return 'Unknown';
    
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffTime = Math.abs(now - date);
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays < 30) {
        return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
      } else if (diffDays < 365) {
        const months = Math.floor(diffDays / 30);
        return `${months} month${months !== 1 ? 's' : ''} ago`;
      } else {
        return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      }
    } catch (error) {
      return 'Unknown';
    }
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
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
