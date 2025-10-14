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
      // First, try to use roster data from page data (faster, no API call needed)
      let rosterData;
      if (data.roster && Array.isArray(data.roster) && data.roster.length > 0) {
        this.logger.info('Using roster data from page data');
        rosterData = {
          members: data.roster,
          game_name: data.team?.game || null
        };
        this.members = rosterData.members;
      } else {
        // Fall back to API calls
        try {
          rosterData = await this.api.getRosterWithGameIds();
          this.logger.info('Roster data with game IDs received:', rosterData);
        } catch (error) {
          // If 403 (not a member), fall back to basic roster
          if (error.message.includes('403') || error.message.includes('Forbidden') || error.message.includes('member')) {
            this.logger.info('Not a team member, fetching basic roster');
            rosterData = await this.api.getRoster();
            // Transform to expected format
            rosterData = {
              members: rosterData.active_players || [],
              game_name: null
            };
          } else {
            throw error;
          }
        }
        this.members = rosterData.members || rosterData.active_players || [];
      }
      
      const isMember = data.permissions?.is_member || false;
      const showGameIds = isMember && rosterData.members; // Only show if we got game IDs from API
      
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

          <!-- Members Grid - Eclipse Design -->
          ${this.members.length > 0 ? `
            <div class="roster-grid-eclipse">
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
   * Render Eclipse member card with dynamic content based on role
   */
  renderMemberCardModern(member, showGameId = false) {
    const isCaptain = member.role === 'CAPTAIN' || member.role === 'captain' || member.is_captain;
    const gameId = member.game_id || 'Not provided';
    const hasGameId = member.game_id && member.game_id !== 'Not provided';
    
    // Handle both new API (profile_id) and old API (id) formats
    const profileId = member.profile_id || member.id;
    const displayName = member.display_name || member.in_game_name || member.username;
    const avatar = member.avatar || member.avatar_url;
    const username = member.username || displayName;
    
    // Get membership role and player role (dual-role system)
    const membershipRole = member.role_display || this.formatRole(member.role);
    const playerRole = member.player_role || member.in_game_role || '';
    const hasPlayerRole = playerRole && playerRole !== '';
    
    // Get role class for styling
    const roleClass = this.getRoleClass(member.role);
    
    // Determine if this is a player/substitute (show in-game details)
    // Also show for owners/managers/coaches if they have assigned in-game roles
    const isPlayingRole = ['PLAYER', 'SUBSTITUTE', 'player', 'substitute'].includes(member.role) || 
                         (hasPlayerRole && ['OWNER', 'MANAGER', 'COACH', 'owner', 'manager', 'coach'].includes(member.role));
    
    // Create a data attribute with roster data for the modal
    const rosterDataJson = JSON.stringify({
      game_id: member.game_id,
      game_id_label: member.game_id_label,
      mlbb_server_id: member.mlbb_server_id,
      player_role: playerRole,
      role: member.role,
      is_captain: member.is_captain
    }).replace(/"/g, '&quot;');
    
    return `
      <div class="eclipse-roster-card ${isCaptain ? 'is-captain' : ''}" 
           data-profile-id="${profileId}"
           data-roster-data="${rosterDataJson}"
           role="button"
           tabindex="0"
           aria-label="View ${this.escapeHtml(displayName)}'s profile">
        
        <!-- Card Header -->
        <div class="eclipse-card-header">
          <div class="eclipse-avatar-wrapper">
            <div class="eclipse-avatar">
              <div class="eclipse-avatar-inner">
                ${avatar ? 
                  `<img src="${avatar}" alt="${this.escapeHtml(displayName)}" loading="lazy">` :
                  `<div class="eclipse-avatar-placeholder">${this.getInitials(displayName)}</div>`
                }
              </div>
            </div>
            <div class="eclipse-status-dot ${member.is_online ? '' : 'offline'}"></div>
          </div>
          
          <div class="eclipse-player-info">
            <h3 class="eclipse-player-name">
              ${isCaptain ? '<i class="eclipse-captain-star fas fa-star"></i>' : ''}
              ${this.escapeHtml(displayName)}
            </h3>
            <p class="eclipse-username">
              <i class="fas fa-at"></i>${this.escapeHtml(username)}
            </p>
          </div>
        </div>
        
        <!-- Roles Section -->
        <div class="eclipse-roles-section">
          <div class="eclipse-team-role-badge ${roleClass}">
            <i class="${this.getRoleIcon(member.role)}"></i>
            ${membershipRole}
          </div>
        </div>
        
        <!-- In-Game Details (Only for Players/Substitutes) -->
        ${isPlayingRole ? `
          <div class="eclipse-divider"></div>
          <div class="eclipse-ingame-section">
            ${hasGameId && showGameId ? `
              <div class="eclipse-ingame-row">
                <span class="eclipse-ingame-label">${member.game_id_label || 'IGN'}</span>
                <span class="eclipse-ingame-value">${this.escapeHtml(gameId)}</span>
              </div>
            ` : ''}
            ${hasPlayerRole ? `
              <div class="eclipse-ingame-row">
                <span class="eclipse-ingame-label">In-Game Role</span>
                <span class="eclipse-ingame-role-badge">${this.escapeHtml(playerRole)}</span>
              </div>
            ` : ''}
            ${member.mlbb_server_id ? `
              <div class="eclipse-ingame-row">
                <span class="eclipse-ingame-label">Server ID</span>
                <span class="eclipse-ingame-value">${this.escapeHtml(member.mlbb_server_id)}</span>
              </div>
            ` : ''}
          </div>
        ` : ''}
        
        <!-- Card Footer -->
        <div class="eclipse-card-footer">
          <span class="eclipse-joined-date">
            <i class="fas fa-calendar"></i>
            Joined ${this.formatDateRelative(member.joined_at || member.join_date)}
          </span>
          <span class="eclipse-view-profile">
            View Profile <i class="fas fa-arrow-right"></i>
          </span>
        </div>
      </div>
    `;
  }
  
  /**
   * Get role CSS class for styling
   */
  getRoleClass(role) {
    if (!role) return 'role-player';
    const roleStr = role.toString().toLowerCase();
    const roleMap = {
      'owner': 'role-owner',
      'manager': 'role-manager',
      'coach': 'role-coach',
      'captain': 'role-player',
      'player': 'role-player',
      'substitute': 'role-substitute',
      'sub': 'role-substitute'
    };
    return roleMap[roleStr] || 'role-player';
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
    
    if (profileId && window.playerModal) {
      try {
        const rosterData = rosterDataStr ? JSON.parse(rosterDataStr) : null;
        window.playerModal.show(profileId, rosterData);
      } catch (error) {
        console.error('Error opening player modal:', error);
        window.playerModal.show(profileId);
      }
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
    
    // Bind eclipse roster card click events
    const rosterCards = container.querySelectorAll('.eclipse-roster-card');
    rosterCards.forEach(card => {
      card.addEventListener('click', (e) => this.openPlayerModal(e, card));
      card.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.openPlayerModal(e, card);
        }
      });
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
   * Get player role color (dual-role system)
   * Maps tactical roles to colors
   */
  getPlayerRoleColor(playerRole) {
    if (!playerRole) return '#6b7280';
    
    const role = playerRole.toLowerCase();
    
    // Aggressive/Entry roles
    if (role.includes('duelist') || role.includes('entry') || role.includes('rusher') || 
        role.includes('assaulter') || role.includes('slayer') || role.includes('fragger')) {
      return '#ef4444'; // Red
    }
    
    // Leadership roles
    if (role.includes('igl') || role.includes('shot caller') || role.includes('caller')) {
      return '#fbbf24'; // Yellow/Gold
    }
    
    // Support roles
    if (role.includes('controller') || role.includes('support') || role.includes('roamer') ||
        role.includes('position 4') || role.includes('position 5')) {
      return '#10b981'; // Green
    }
    
    // Defensive roles
    if (role.includes('sentinel') || role.includes('anchor')) {
      return '#3b82f6'; // Blue
    }
    
    // Utility roles
    if (role.includes('initiator') || role.includes('lurker') || role.includes('flanker')) {
      return '#f97316'; // Orange
    }
    
    // Specialist roles
    if (role.includes('awper') || role.includes('sniper') || role.includes('scout')) {
      return '#ec4899'; // Pink
    }
    
    // Position-based (Dota 2)
    if (role.includes('position 1') || role.includes('carry')) {
      return '#dc2626'; // Dark Red
    }
    if (role.includes('position 2') || role.includes('mid')) {
      return '#f59e0b'; // Amber
    }
    if (role.includes('position 3') || role.includes('offlane')) {
      return '#3b82f6'; // Blue
    }
    
    // MLBB specific
    if (role.includes('gold laner')) {
      return '#fbbf24'; // Gold
    }
    if (role.includes('exp laner')) {
      return '#3b82f6'; // Blue
    }
    if (role.includes('mid laner')) {
      return '#a855f7'; // Purple
    }
    if (role.includes('jungler')) {
      return '#10b981'; // Green
    }
    
    // Generic/Flex
    if (role.includes('flex') || role.includes('rifler')) {
      return '#6b7280'; // Gray
    }
    
    return '#6b7280'; // Default gray
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
