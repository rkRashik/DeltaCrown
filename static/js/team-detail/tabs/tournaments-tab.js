/**
 * Tournaments Tab - Tournament Registration & History
 */

class TournamentsTab {
  constructor(api) {
    this.api = api;
    this.logger = new Logger('TournamentsTab');
  }

  /**
   * Render tournaments tab content
   */
  async render(container, data) {
    container.innerHTML = `
      <div class="tournaments-tab">
        <!-- Active Tournaments Section -->
        <section class="tab-section">
          <div class="section-header">
            <h2 class="section-title">
              <i class="fa-solid fa-trophy"></i>
              Active Tournaments
            </h2>
            ${data.permissions.can_edit ? `
              <a href="/tournaments/" class="btn btn-primary btn-sm">
                <i class="fa-solid fa-magnifying-glass"></i> Search for Tournament
              </a>
            ` : ''}
          </div>
          <div id="active-tournaments-content" class="tournaments-loading">
            ${this.renderLoading()}
          </div>
        </section>

        <!-- Upcoming Matches Section -->
        <section class="tab-section" id="upcoming-matches-section" style="display: none;">
          <h2 class="section-title">
            <i class="fa-solid fa-calendar-days"></i>
            Upcoming Matches
          </h2>
          <div id="upcoming-matches-content"></div>
        </section>

        <!-- Tournament History Section -->
        <section class="tab-section">
          <div class="section-header">
            <h2 class="section-title">
              <i class="fa-solid fa-clock-rotate-left"></i>
              Tournament History
            </h2>
            <div class="filter-controls">
              <select id="history-filter-year" class="form-control form-control-sm">
                <option value="">All Years</option>
                <option value="2025" selected>2025</option>
                <option value="2024">2024</option>
                <option value="2023">2023</option>
              </select>
            </div>
          </div>
          <div id="tournament-history-content" class="tournaments-loading">
            ${this.renderLoading()}
          </div>
        </section>
      </div>
    `;

    // Load tournament data
    await this.loadTournaments(data);

    // Bind events
    this.bindEvents(data);
  }

  /**
   * Load tournaments from API
   */
  async loadTournaments(data) {
    try {
      const tournaments = await this.api.getTournaments();
      
      // Render active tournaments
      this.renderActiveTournaments(tournaments.active);
      
      // Render upcoming matches
      if (tournaments.upcomingMatches && tournaments.upcomingMatches.length > 0) {
        this.renderUpcomingMatches(tournaments.upcomingMatches);
        document.getElementById('upcoming-matches-section').style.display = 'block';
      }
      
      // Render tournament history
      this.renderTournamentHistory(tournaments.history);

    } catch (error) {
      this.logger.error('Error loading tournaments:', error);
      if (window.Toast) {
        Toast.error('Failed to load tournaments: ' + error.message);
      }
    }
  }

  /**
   * Render active tournaments
   */
  renderActiveTournaments(tournaments) {
    const container = document.getElementById('active-tournaments-content');
    
    if (!tournaments || tournaments.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon"><i class="fa-solid fa-trophy"></i></div>
          <h3 class="empty-state-title">No Active Tournaments</h3>
          <p class="empty-state-message">Your team is not currently registered for any tournaments.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="tournaments-grid">
        ${tournaments.map(tournament => this.renderTournamentCard(tournament, true)).join('')}
      </div>
    `;
  }

  /**
   * Render tournament card
   */
  renderTournamentCard(tournament, isActive = false) {
    const statusClass = this.getStatusClass(tournament.status);
    const statusIcon = this.getStatusIcon(tournament.status);
    
    return `
      <div class="tournament-card ${isActive ? 'tournament-card-active' : ''}">
        <!-- Tournament Header -->
        <div class="tournament-card-header">
          ${tournament.banner_url ? `
            <img src="${tournament.banner_url}" alt="${tournament.name}" class="tournament-banner">
          ` : `
            <div class="tournament-banner-placeholder">
              <i class="fa-solid fa-trophy"></i>
            </div>
          `}
          <span class="tournament-status ${statusClass}">
            <i class="${statusIcon}"></i>
            ${this.formatStatus(tournament.status)}
          </span>
        </div>

        <!-- Tournament Body -->
        <div class="tournament-card-body">
          <h3 class="tournament-name">${this.escapeHtml(tournament.name)}</h3>
          
          ${tournament.organizer ? `
            <p class="tournament-organizer">
              <i class="fa-solid fa-building"></i>
              ${this.escapeHtml(tournament.organizer)}
            </p>
          ` : ''}

          <div class="tournament-meta">
            <div class="tournament-meta-item">
              <i class="fa-solid fa-calendar"></i>
              <span>${this.formatDateRange(tournament.start_date, tournament.end_date)}</span>
            </div>
            
            ${tournament.prize_pool ? `
              <div class="tournament-meta-item">
                <i class="fa-solid fa-dollar-sign"></i>
                <span>${this.formatPrizePool(tournament.prize_pool)}</span>
              </div>
            ` : ''}

            ${tournament.team_count ? `
              <div class="tournament-meta-item">
                <i class="fa-solid fa-users"></i>
                <span>${tournament.team_count} Teams</span>
              </div>
            ` : ''}

            ${tournament.format ? `
              <div class="tournament-meta-item">
                <i class="fa-solid fa-diagram-project"></i>
                <span>${tournament.format}</span>
              </div>
            ` : ''}
          </div>

          ${tournament.placement ? `
            <div class="tournament-placement">
              <i class="fa-solid fa-medal"></i>
              <span class="placement-text">${this.getPlacementText(tournament.placement)}</span>
            </div>
          ` : ''}

          ${tournament.matches_played !== undefined ? `
            <div class="tournament-progress">
              <div class="progress-label">
                <span>Matches: ${tournament.matches_won || 0}W - ${tournament.matches_lost || 0}L</span>
                <span>${tournament.matches_played}/${tournament.total_matches || '?'}</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" style="width: ${this.calculateProgress(tournament.matches_played, tournament.total_matches)}%"></div>
              </div>
            </div>
          ` : ''}
        </div>

        <!-- Tournament Footer -->
        <div class="tournament-card-footer">
          <button class="btn btn-sm btn-secondary" data-action="view-tournament" data-tournament-id="${tournament.id}">
            <i class="fa-solid fa-eye"></i> View Details
          </button>
          ${isActive && tournament.bracket_url ? `
            <a href="${tournament.bracket_url}" target="_blank" class="btn btn-sm btn-secondary">
              <i class="fa-solid fa-diagram-project"></i> Bracket
            </a>
          ` : ''}
        </div>
      </div>
    `;
  }

  /**
   * Render upcoming matches
   */
  renderUpcomingMatches(matches) {
    const container = document.getElementById('upcoming-matches-content');
    
    container.innerHTML = `
      <div class="upcoming-matches-list">
        ${matches.map(match => this.renderUpcomingMatchCard(match)).join('')}
      </div>
    `;
  }

  /**
   * Render upcoming match card
   */
  renderUpcomingMatchCard(match) {
    return `
      <div class="upcoming-match-card">
        <div class="match-tournament-info">
          <h4 class="match-tournament-name">${this.escapeHtml(match.tournament_name)}</h4>
          <span class="match-round">${match.round || 'Round TBD'}</span>
        </div>
        
        <div class="match-teams-upcoming">
          <div class="match-team our-team">
            ${match.our_team_logo ? `
              <img src="${match.our_team_logo}" alt="${match.our_team_name}" class="team-logo-medium">
            ` : `
              <div class="team-logo-placeholder"><i class="fa-solid fa-shield"></i></div>
            `}
            <span class="team-name-large">${this.escapeHtml(match.our_team_name)}</span>
          </div>

          <div class="match-vs">
            <span class="vs-text">VS</span>
            ${match.scheduled_time ? `
              <div class="match-time">
                <i class="fa-solid fa-clock"></i>
                ${this.formatMatchTime(match.scheduled_time)}
              </div>
            ` : '<span class="text-muted">Time TBD</span>'}
          </div>

          <div class="match-team opponent-team">
            ${match.opponent_logo ? `
              <img src="${match.opponent_logo}" alt="${match.opponent_name}" class="team-logo-medium">
            ` : `
              <div class="team-logo-placeholder"><i class="fa-solid fa-shield"></i></div>
            `}
            <span class="team-name-large">${this.escapeHtml(match.opponent_name)}</span>
          </div>
        </div>

        ${match.stream_url ? `
          <div class="match-actions">
            <a href="${match.stream_url}" target="_blank" class="btn btn-sm btn-primary">
              <i class="fa-solid fa-tv"></i> Watch Live
            </a>
          </div>
        ` : ''}
      </div>
    `;
  }

  /**
   * Render tournament history
   */
  renderTournamentHistory(history) {
    const container = document.getElementById('tournament-history-content');
    
    if (!history || history.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon"><i class="fa-solid fa-clock-rotate-left"></i></div>
          <h3 class="empty-state-title">No Tournament History</h3>
          <p class="empty-state-message">Your team hasn't participated in any tournaments yet.</p>
        </div>
      `;
      return;
    }

    // Group by year
    const byYear = this.groupByYear(history);
    
    container.innerHTML = `
      <div class="tournament-history-timeline">
        ${Object.entries(byYear)
          .sort(([yearA], [yearB]) => yearB - yearA)
          .map(([year, tournaments]) => `
            <div class="history-year-group">
              <h3 class="history-year">${year}</h3>
              <div class="tournaments-grid">
                ${tournaments.map(t => this.renderTournamentCard(t, false)).join('')}
              </div>
            </div>
          `).join('')}
      </div>
    `;
  }

  /**
   * Bind event listeners
   */
  bindEvents(data) {
    const container = document.querySelector('.tournaments-tab');

    // Register tournament button
    container.querySelectorAll('[data-action="register-tournament"]').forEach(btn => {
      btn.addEventListener('click', () => this.showRegisterModal());
    });

    // View tournament details
    container.querySelectorAll('[data-action="view-tournament"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tournamentId = e.currentTarget.dataset.tournamentId;
        this.showTournamentModal(tournamentId);
      });
    });

    // History filter
    const yearFilter = document.getElementById('history-filter-year');
    if (yearFilter) {
      yearFilter.addEventListener('change', async (e) => {
        const year = e.target.value;
        await this.filterHistory(year);
      });
    }
  }

  /**
   * Show register tournament modal
   */
  showRegisterModal() {
    const modal = Modal.create({
      title: 'Register for Tournament',
      content: `
        <form id="register-tournament-form" class="form">
          <div class="form-group">
            <label for="tournament-search">Search Tournament</label>
            <input type="text" id="tournament-search" class="form-control" placeholder="Search by name..." required>
            <div id="tournament-search-results" class="search-results"></div>
          </div>

          <div class="alert alert-info">
            <i class="fa-solid fa-info-circle"></i>
            Registration will be processed by the team captain and tournament organizers.
          </div>

          <div class="form-actions">
            <button type="button" class="btn btn-secondary" data-action="cancel">Cancel</button>
            <button type="submit" class="btn btn-primary">Register</button>
          </div>
        </form>
      `,
      size: 'medium'
    });

    // Bind form
    const form = document.getElementById('register-tournament-form');
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      Toast.info('Tournament registration will be implemented with backend API');
      modal.close();
    });

    form.querySelector('[data-action="cancel"]').addEventListener('click', () => modal.close());
  }

  /**
   * Show tournament details modal
   */
  async showTournamentModal(tournamentId) {
    const modal = Modal.create({
      title: 'Tournament Details',
      content: '<div class="text-center"><i class="fa-solid fa-spinner fa-spin fa-2x"></i></div>',
      size: 'large'
    });

    try {
      const tournament = await this.api.getTournamentDetails(tournamentId);
      modal.updateContent(this.renderTournamentDetail(tournament));
    } catch (error) {
      modal.updateContent(`<p class="text-error">Failed to load tournament: ${error.message}</p>`);
    }
  }

  /**
   * Render tournament detail view
   */
  renderTournamentDetail(tournament) {
    return `
      <div class="tournament-detail">
        <div class="tournament-detail-header">
          ${tournament.banner_url ? `
            <img src="${tournament.banner_url}" alt="${tournament.name}" class="tournament-banner-large">
          ` : ''}
          <h2>${this.escapeHtml(tournament.name)}</h2>
          <p class="tournament-detail-organizer">${this.escapeHtml(tournament.organizer || 'Unknown Organizer')}</p>
        </div>

        <div class="tournament-detail-body">
          <div class="tournament-info-grid">
            <div class="info-item">
              <strong>Status:</strong>
              <span class="tournament-status ${this.getStatusClass(tournament.status)}">
                ${this.formatStatus(tournament.status)}
              </span>
            </div>
            <div class="info-item">
              <strong>Dates:</strong>
              <span>${this.formatDateRange(tournament.start_date, tournament.end_date)}</span>
            </div>
            ${tournament.prize_pool ? `
              <div class="info-item">
                <strong>Prize Pool:</strong>
                <span>${this.formatPrizePool(tournament.prize_pool)}</span>
              </div>
            ` : ''}
            <div class="info-item">
              <strong>Format:</strong>
              <span>${tournament.format || 'Single Elimination'}</span>
            </div>
          </div>

          ${tournament.description ? `
            <div class="tournament-description">
              <h3>About</h3>
              <p>${this.escapeHtml(tournament.description)}</p>
            </div>
          ` : ''}

          ${tournament.rules ? `
            <div class="tournament-rules">
              <h3>Rules</h3>
              <div>${tournament.rules}</div>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  /**
   * Filter history by year
   */
  async filterHistory(year) {
    const container = document.getElementById('tournament-history-content');
    container.innerHTML = this.renderLoading();
    
    try {
      const tournaments = await this.api.getTournaments({ year });
      this.renderTournamentHistory(tournaments.history);
    } catch (error) {
      Toast.error('Failed to filter tournaments');
    }
  }

  /**
   * Group tournaments by year
   */
  groupByYear(tournaments) {
    return tournaments.reduce((acc, tournament) => {
      const year = new Date(tournament.start_date).getFullYear();
      if (!acc[year]) acc[year] = [];
      acc[year].push(tournament);
      return acc;
    }, {});
  }

  /**
   * Get status class
   */
  getStatusClass(status) {
    const classes = {
      'active': 'status-active',
      'upcoming': 'status-upcoming',
      'completed': 'status-completed',
      'cancelled': 'status-cancelled',
    };
    return classes[status] || 'status-default';
  }

  /**
   * Get status icon
   */
  getStatusIcon(status) {
    const icons = {
      'active': 'fa-solid fa-play',
      'upcoming': 'fa-solid fa-clock',
      'completed': 'fa-solid fa-check',
      'cancelled': 'fa-solid fa-times',
    };
    return icons[status] || 'fa-solid fa-circle';
  }

  /**
   * Format status text
   */
  formatStatus(status) {
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  /**
   * Format date range
   */
  formatDateRange(startDate, endDate) {
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    const startStr = start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const endStr = end.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    
    return `${startStr} - ${endStr}`;
  }

  /**
   * Format prize pool
   */
  formatPrizePool(amount) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0
    }).format(amount);
  }

  /**
   * Format match time
   */
  formatMatchTime(dateTime) {
    const date = new Date(dateTime);
    const now = new Date();
    const diffMs = date - now;
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 24) {
      return `In ${diffHours} hours`;
    } else {
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      });
    }
  }

  /**
   * Get placement text
   */
  getPlacementText(placement) {
    const suffixes = ['th', 'st', 'nd', 'rd'];
    const value = placement % 100;
    return placement + (suffixes[(value - 20) % 10] || suffixes[value] || suffixes[0]) + ' Place';
  }

  /**
   * Calculate progress percentage
   */
  calculateProgress(played, total) {
    if (!total || total === 0) return 0;
    return Math.round((played / total) * 100);
  }

  /**
   * Render loading state
   */
  renderLoading() {
    return `
      <div class="text-center py-4">
        <i class="fa-solid fa-spinner fa-spin fa-2x text-muted"></i>
        <p class="text-muted mt-2">Loading tournaments...</p>
      </div>
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
}

// Export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TournamentsTab;
}
