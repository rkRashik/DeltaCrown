/**
 * Overview Tab - Team Overview Content
 */

class OverviewTab {
  constructor(api) {
    this.api = api;
  }

  /**
   * Render overview tab content - REAL DATA ONLY
   */
  async render(container, data) {
    container.innerHTML = `
      <div class="overview-tab">
        <!-- Hero Stats Cards - REAL DATA -->
        <div class="overview-stats-grid">
          <div class="stat-card highlight">
            <div class="stat-icon">
              <i class="fa-solid fa-trophy"></i>
            </div>
            <div class="stat-info">
              <div class="stat-value">${data.team.wins || 0}</div>
              <div class="stat-label">Total Wins</div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-icon">
              <i class="fa-solid fa-users"></i>
            </div>
            <div class="stat-info">
              <div class="stat-value">${data.team.members_count || 0}</div>
              <div class="stat-label">Team Members</div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-icon">
              <i class="fa-solid fa-heart"></i>
            </div>
            <div class="stat-info">
              <div class="stat-value">${data.team.followers_count || 0}</div>
              <div class="stat-label">Followers</div>
            </div>
          </div>
          
          <div class="stat-card">
            <div class="stat-icon">
              <i class="fa-solid fa-calendar"></i>
            </div>
            <div class="stat-info">
              <div class="stat-value">${data.team.tournaments_count || 0}</div>
              <div class="stat-label">Tournaments</div>
            </div>
          </div>
        </div>

        <!-- About Team Section - Modern & Beautiful Design -->
        <section class="tab-section">
          <div class="about-card-modern">
            <div class="about-header-modern">
              <div class="about-icon-wrapper">
                <i class="fa-solid fa-book-open"></i>
              </div>
              <div class="about-title-section">
                <h2 class="about-title-modern">About ${this.escapeHtml(data.team.name)}</h2>
                <p class="about-subtitle">Discover our story, mission, and what makes us unique</p>
              </div>
              ${data.permissions.can_edit ? `
                <button class="btn-edit-modern" onclick="editDescription()">
                  <i class="fa-solid fa-pen"></i>
                  <span>Edit</span>
                </button>
              ` : ''}
            </div>
            <div class="about-body-modern">
              ${data.team.description ? `
                <div class="about-content-wrapper">
                  <div class="description-decorator"></div>
                  <p class="team-description-modern">${this.escapeHtml(data.team.description)}</p>
                  <div class="description-stats">
                    <div class="stat-pill">
                      <i class="fa-solid fa-calendar"></i>
                      <span>Established ${this.formatDate(data.team.created_at)}</span>
                    </div>
                    ${data.team.is_verified ? `
                      <div class="stat-pill verified-pill">
                        <i class="fa-solid fa-badge-check"></i>
                        <span>Verified Team</span>
                      </div>
                    ` : ''}
                    ${data.team.is_recruiting ? `
                      <div class="stat-pill recruiting-pill">
                        <i class="fa-solid fa-user-plus"></i>
                        <span>Recruiting Now</span>
                      </div>
                    ` : ''}
                  </div>
                </div>
              ` : `
                <div class="about-empty-state">
                  <div class="empty-icon-circle">
                    <i class="fa-solid fa-pen-fancy"></i>
                  </div>
                  <h3 class="empty-title">No Story Yet</h3>
                  <p class="empty-message">${data.permissions.can_edit ? 'Share your team\'s journey, goals, and what makes you stand out from the competition!' : 'This team hasn\'t added their story yet.'}</p>
                  ${data.permissions.can_edit ? '<button class="btn-primary-modern" onclick="editDescription()"><i class="fa-solid fa-sparkles"></i>Write Your Story</button>' : ''}
                </div>
              `}
            </div>
          </div>
        </section>

        <!-- Team Information & Social - Modern Grid Layout -->
        <div class="modern-info-grid">
          <!-- Team Details Card -->
          <div class="modern-info-card">
            <div class="card-header-modern">
              <div class="header-icon-wrapper">
                <i class="fa-solid fa-info-circle"></i>
              </div>
              <h3 class="section-title-modern">Team Information</h3>
            </div>
            <div class="card-body-modern">
              <div class="info-grid-modern">
                <div class="info-item-modern">
                  <div class="info-icon">
                    <i class="fa-solid fa-shield-halved"></i>
                  </div>
                  <div class="info-content">
                    <span class="info-label-modern">Game</span>
                    <span class="info-value-modern">${this.getGameName(data.team.game)}</span>
                  </div>
                </div>
                <div class="info-item-modern">
                  <div class="info-icon">
                    <i class="fa-solid fa-globe-americas"></i>
                  </div>
                  <div class="info-content">
                    <span class="info-label-modern">Region</span>
                    <span class="info-value-modern">${this.escapeHtml(data.team.region || 'Global')}</span>
                  </div>
                </div>
                <div class="info-item-modern">
                  <div class="info-icon">
                    <i class="fa-solid fa-calendar-check"></i>
                  </div>
                  <div class="info-content">
                    <span class="info-label-modern">Founded</span>
                    <span class="info-value-modern">${this.formatDate(data.team.created_at)}</span>
                  </div>
                </div>
                <div class="info-item-modern">
                  <div class="info-icon">
                    <i class="fa-solid fa-eye"></i>
                  </div>
                  <div class="info-content">
                    <span class="info-label-modern">Visibility</span>
                    <span class="info-value-modern ${data.team.is_public ? 'status-public' : 'status-private'}">
                      ${data.team.is_public ? 'Public' : 'Private'}
                    </span>
                  </div>
                </div>
                ${data.team.is_recruiting ? `
                  <div class="info-item-modern highlight-recruiting">
                    <div class="info-icon">
                      <i class="fa-solid fa-bullhorn"></i>
                    </div>
                    <div class="info-content">
                      <span class="info-label-modern">Status</span>
                      <span class="info-value-modern recruiting-badge-inline">Recruiting Players</span>
                    </div>
                  </div>
                ` : ''}
              </div>
              
              <!-- Social Links Integrated -->
              ${data.social_links && data.social_links.length > 0 ? `
                <div class="social-section-modern">
                  <div class="social-header-modern">
                    <i class="fa-solid fa-share-nodes"></i>
                    <span>Connect With Us</span>
                  </div>
                  <div class="social-grid-modern">
                    ${data.social_links.map(link => `
                      <a href="${this.escapeHtml(link.url)}" 
                         target="_blank" 
                         rel="noopener noreferrer" 
                         class="social-btn-modern social-${this.escapeHtml(link.icon)}"
                         title="${this.escapeHtml(link.name)}">
                        <i class="fa-brands fa-${this.escapeHtml(link.icon)}"></i>
                        <span>${this.escapeHtml(link.name)}</span>
                      </a>
                    `).join('')}
                  </div>
                </div>
              ` : ''}
            </div>
          </div>

          <!-- Captain Information - Modern Design -->
          ${data.team.captain ? `
            <div class="modern-info-card captain-card-modern">
              <div class="card-header-modern">
                <div class="header-icon-wrapper captain-icon">
                  <i class="fa-solid fa-crown"></i>
                </div>
                <h3 class="section-title-modern">Team Captain</h3>
              </div>
              <div class="card-body-modern">
                <div class="captain-profile-modern">
                  <div class="captain-avatar-wrapper">
                    <img src="${data.team.captain.avatar || '/static/img/user_avatar/default-avatar.png'}" 
                         alt="${this.escapeHtml(data.team.captain.username)}" 
                         class="captain-avatar-modern">
                    <div class="captain-status-indicator"></div>
                  </div>
                  <div class="captain-info-modern">
                    <h4 class="captain-name">${this.escapeHtml(data.team.captain.username)}</h4>
                    <p class="captain-ign">
                      <i class="fa-solid fa-gamepad"></i>
                      ${this.escapeHtml(data.team.captain.in_game_name || data.team.captain.username)}
                    </p>
                    <div class="captain-badge">
                      <i class="fa-solid fa-shield-halved"></i>
                      <span>Team Leader</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ` : ''}
        </div>

        <!-- Recent Matches Section - REAL DATA ONLY -->
        ${data.recent_matches && data.recent_matches.length > 0 ? `
          <section class="tab-section">
            <div class="section-header">
              <h2 class="section-title">
                <i class="fa-solid fa-gamepad"></i>
                Recent Matches
              </h2>
              <a href="#" class="btn btn-sm btn-secondary" onclick="switchTab('tournaments')">View All</a>
            </div>
            <div class="matches-grid">
              ${data.recent_matches.map(match => this.renderMatchCard(match)).join('')}
            </div>
          </section>
        ` : `
          <section class="tab-section">
            <div class="overview-card empty">
              <div class="empty-state-lg">
                <i class="fa-solid fa-gamepad"></i>
                <h3>No Matches Yet</h3>
                <p>Start competing in tournaments to see your match history here</p>
                <a href="/tournaments/" class="btn btn-primary">
                  <i class="fa-solid fa-magnifying-glass"></i>
                  Browse Tournaments
                </a>
              </div>
            </div>
          </section>
        `}

        <!-- Latest Posts Section - REAL DATA ONLY -->
        ${data.posts && data.posts.length > 0 ? `
          <section class="tab-section">
            <div class="section-header">
              <h2 class="section-title">
                <i class="fa-solid fa-newspaper"></i>
                Latest Updates
              </h2>
              <a href="#" class="btn btn-sm btn-secondary" onclick="switchTab('posts')">View All Posts</a>
            </div>
            <div class="posts-grid">
              ${data.posts.slice(0, 3).map(post => this.renderPostCard(post)).join('')}
            </div>
          </section>
        ` : `
          <section class="tab-section">
            <div class="overview-card empty">
              <div class="empty-state-lg">
                <i class="fa-solid fa-newspaper"></i>
                <h3>No Posts Yet</h3>
                <p>Share updates, announcements, and news with your followers</p>
                ${data.permissions.can_post ? `
                  <button class="btn btn-primary" onclick="createPost()">
                    <i class="fa-solid fa-plus"></i>
                    Create Post
                  </button>
                ` : ''}
              </div>
            </div>
          </section>
        `}

        <!-- Recent Activity - REAL DATA ONLY -->
        ${data.activity && data.activity.length > 0 ? `
          <section class="tab-section">
            <div class="overview-card">
              <div class="card-header">
                <h2 class="section-title">
                  <i class="fa-solid fa-clock-rotate-left"></i>
                  Recent Activity
                </h2>
              </div>
              <div class="card-body">
                <div class="activity-feed">
                  ${data.activity.map(activity => this.renderActivity(activity)).join('')}
                </div>
              </div>
            </div>
          </section>
        ` : ''}
      </div>
    `;

    // Bind event listeners
    this.bindEvents(container);
  }

  /**
   * Get game display name
   */
  getGameName(gameCode) {
    const games = {
      'valorant': 'VALORANT',
      'cs2': 'Counter-Strike 2',
      'dota2': 'Dota 2',
      'mlbb': 'Mobile Legends: Bang Bang',
      'pubg': 'PUBG',
      'freefire': 'Free Fire',
      'efootball': 'eFootball',
      'fc26': 'EA Sports FC 26',
      'codm': 'Call of Duty: Mobile'
    };
    return games[gameCode] || this.escapeHtml(gameCode);
  }

  /**
   * Render match card
   */
  renderMatchCard(match) {
    const isWin = match.winner_id === match.our_team_id;
    const resultClass = isWin ? 'win' : 'loss';
    
    return `
      <div class="match-card ${resultClass}">
        <div class="match-header">
          <span class="match-date">${this.formatDate(match.start_at)}</span>
          <span class="match-result ${resultClass}">${isWin ? 'VICTORY' : 'DEFEAT'}</span>
        </div>
        <div class="match-teams">
          <div class="team team-a ${match.our_team_id === match.team_a_id ? 'our-team' : ''}">
            <img src="${match.team_a_logo || '/static/img/default-team.png'}" alt="${match.team_a_name}" class="team-logo-small">
            <span class="team-name">${match.team_a_name}</span>
          </div>
          <div class="match-score">
            <span class="score">${match.team_a_score || 0}</span>
            <span class="vs">VS</span>
            <span class="score">${match.team_b_score || 0}</span>
          </div>
          <div class="team team-b ${match.our_team_id === match.team_b_id ? 'our-team' : ''}">
            <img src="${match.team_b_logo || '/static/img/default-team.png'}" alt="${match.team_b_name}" class="team-logo-small">
            <span class="team-name">${match.team_b_name}</span>
          </div>
        </div>
        ${match.tournament_name ? `
          <div class="match-footer">
            <i class="fa-solid fa-trophy"></i>
            <span>${match.tournament_name}</span>
          </div>
        ` : ''}
      </div>
    `;
  }

  /**
   * Render post card
   */
  renderPostCard(post) {
    return `
      <article class="post-card-preview" data-post-id="${post.id}">
        ${post.media && post.media.length > 0 ? `
          <div class="post-thumbnail">
            <img src="${post.media[0].file_url}" alt="${post.title || 'Post'}" loading="lazy">
          </div>
        ` : ''}
        <div class="post-content-preview">
          <div class="post-meta">
            <img src="${post.author.avatar_url}" alt="${post.author.display_name}" class="author-avatar-tiny">
            <span class="author-name">${post.author.display_name}</span>
            <span class="post-date">${this.timeAgo(post.created_at)}</span>
          </div>
          ${post.title ? `<h3 class="post-title">${this.escapeHtml(post.title)}</h3>` : ''}
          <p class="post-excerpt">${this.truncate(this.escapeHtml(post.content), 120)}</p>
          <div class="post-engagement-preview">
            <span><i class="fa-solid fa-heart"></i> ${post.engagement.likes_count}</span>
            <span><i class="fa-solid fa-comment"></i> ${post.engagement.comments_count}</span>
          </div>
        </div>
      </article>
    `;
  }



  /**
   * Render activity item
   */
  renderActivity(activity) {
    const icon = this.getActivityIcon(activity.activity_type);
    return `
      <div class="activity-item">
        <div class="activity-icon">
          <i class="${icon}"></i>
        </div>
        <div class="activity-content">
          <p class="activity-text">${this.formatActivityText(activity)}</p>
          <span class="activity-time">${this.timeAgo(activity.created_at)}</span>
        </div>
      </div>
    `;
  }

  /**
   * Get activity icon
   */
  getActivityIcon(type) {
    const icons = {
      'member_joined': 'fa-solid fa-user-plus',
      'member_left': 'fa-solid fa-user-minus',
      'match_won': 'fa-solid fa-trophy',
      'match_lost': 'fa-solid fa-times',
      'tournament_registered': 'fa-solid fa-calendar-plus',
      'post_created': 'fa-solid fa-newspaper',
      'achievement_earned': 'fa-solid fa-award',
    };
    return icons[type] || 'fa-solid fa-circle-info';
  }

  /**
   * Format activity text
   */
  formatActivityText(activity) {
    // This will be customized based on activity type
    return this.escapeHtml(activity.description || activity.text || 'Activity occurred');
  }

  /**
   * Get placement badge
   */
  getPlacementBadge(placement) {
    const badges = {
      1: '🥇 1st Place',
      2: '🥈 2nd Place',
      3: '🥉 3rd Place',
    };
    return badges[placement] || `#${placement}`;
  }

  /**
   * Bind event listeners
   */
  bindEvents(container) {
    // Post card click
    container.querySelectorAll('.post-card-preview').forEach(card => {
      card.addEventListener('click', (e) => {
        const postId = card.dataset.postId;
        this.openPostModal(postId);
      });
    });
  }

  /**
   * Open post detail modal
   */
  async openPostModal(postId) {
    const modal = Modal.create({
      title: 'Post Details',
      content: '<div class="text-center"><i class="fa-solid fa-spinner fa-spin fa-2x"></i></div>',
      size: 'large'
    });

    try {
      const post = await this.api.getPost(postId);
      modal.updateContent(this.renderPostDetail(post));
    } catch (error) {
      modal.updateContent(`<p class="text-error">Failed to load post: ${error.message}</p>`);
    }
  }

  /**
   * Render full post detail
   */
  renderPostDetail(post) {
    return `
      <article class="post-detail">
        <div class="post-header">
          <img src="${post.author.avatar_url}" alt="${post.author.display_name}" class="author-avatar">
          <div class="author-info">
            <h4 class="author-name">${post.author.display_name}</h4>
            <time class="post-time">${this.formatDate(post.created_at)}</time>
          </div>
        </div>
        ${post.title ? `<h2 class="post-title-detail">${this.escapeHtml(post.title)}</h2>` : ''}
        <div class="post-content-full">${this.escapeHtml(post.content)}</div>
        ${post.media && post.media.length > 0 ? `
          <div class="post-media-gallery">
            ${post.media.map(m => `<img src="${m.file_url}" alt="${m.caption || ''}" loading="lazy">`).join('')}
          </div>
        ` : ''}
        <div class="post-engagement-full">
          <button class="engagement-btn ${post.engagement.user_liked ? 'liked' : ''}" data-action="like">
            <i class="fa-solid fa-heart"></i> ${post.engagement.likes_count}
          </button>
          <button class="engagement-btn" data-action="comment">
            <i class="fa-solid fa-comment"></i> ${post.engagement.comments_count}
          </button>
          <button class="engagement-btn" data-action="share">
            <i class="fa-solid fa-share"></i> Share
          </button>
        </div>
      </article>
    `;
  }

  /**
   * Utility: Escape HTML
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Utility: Truncate text
   */
  truncate(text, length) {
    return text.length > length ? text.substring(0, length) + '...' : text;
  }

  /**
   * Utility: Format date
   */
  formatDate(dateString) {
    if (!dateString) return 'Not specified';
    
    try {
      const date = new Date(dateString);
      
      // Check if date is valid
      if (isNaN(date.getTime())) {
        return 'Not specified';
      }
      
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric' 
      });
    } catch (error) {
      console.error('Error formatting date:', error);
      return 'Not specified';
    }
  }

  /**
   * Utility: Time ago
   */
  timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    const intervals = {
      year: 31536000,
      month: 2592000,
      week: 604800,
      day: 86400,
      hour: 3600,
      minute: 60
    };

    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
      const interval = Math.floor(seconds / secondsInUnit);
      if (interval >= 1) {
        return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
      }
    }

    return 'Just now';
  }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = OverviewTab;
}
