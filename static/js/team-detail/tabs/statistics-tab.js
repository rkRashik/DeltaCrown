/**
 * Statistics Tab - Team Performance Analytics (REAL DATA ONLY)
 */

class StatisticsTab {
  constructor(api) {
    this.api = api;
  }

  /**
   * Render statistics tab content - NO FAKE DATA
   */
  async render(container, data) {
    container.innerHTML = `
      <div class="statistics-tab">
        <div class="stats-loading">
          <div class="spinner"></div>
          <p>Loading statistics...</p>
        </div>
      </div>
    `;

    try {
      // Fetch real statistics from API
      const stats = await this.api.getStatistics();
      
      // Check if we have any real data
      if (!stats || !stats.overview || stats.overview.total_matches === 0) {
        container.innerHTML = this.renderEmptyState(data);
        return;
      }

      // Render real statistics
      container.innerHTML = this.renderRealStatistics(stats, data);
      
    } catch (error) {
      console.error('[StatisticsTab] Error loading statistics:', error);
      container.innerHTML = this.renderErrorState(error.message);
    }
  }

  /**
   * Render empty state when no data exists
   */
  renderEmptyState(data) {
    return `
      <div class="statistics-tab">
        <div class="empty-state-large">
          <div class="empty-state-icon">
            <i class="fa-solid fa-chart-line"></i>
          </div>
          <h2>No Statistics Yet</h2>
          <p>Your team hasn't played any matches yet. Start competing in tournaments to build your statistics!</p>
          ${data.permissions.can_edit ? `
            <a href="/tournaments/" class="btn btn-primary btn-lg">
              <i class="fa-solid fa-magnifying-glass"></i>
              Find Tournaments
            </a>
          ` : ''}
        </div>
      </div>
    `;
  }

  /**
   * Render error state
   */
  renderErrorState(message) {
    return `
      <div class="statistics-tab">
        <div class="error-state-large">
          <div class="error-state-icon">
            <i class="fa-solid fa-exclamation-triangle"></i>
          </div>
          <h2>Failed to Load Statistics</h2>
          <p>${this.escapeHtml(message)}</p>
          <button class="btn btn-primary" onclick="window.location.reload()">
            <i class="fa-solid fa-refresh"></i>
            Retry
          </button>
        </div>
      </div>
    `;
  }

  /**
   * Render real statistics - ONLY IF DATA EXISTS
   */
  renderRealStatistics(stats, data) {
    const overview = stats.overview || {};
    
    return `
      <div class="statistics-tab">
        <!-- Overall Stats Summary - REAL DATA -->
        <section class="tab-section">
          <h2 class="section-title">
            <i class="fa-solid fa-chart-line"></i>
            Overall Statistics
          </h2>
          <div class="stats-overview-grid">
            ${this.renderOverviewCards(overview)}
          </div>
        </section>

        <!-- Recent Performance - REAL DATA -->
        ${stats.recentMatches && stats.recentMatches.length > 0 ? `
          <section class="tab-section">
            <h2 class="section-title">
              <i class="fa-solid fa-clock"></i>
              Recent Performance
            </h2>
            <div class="recent-matches-list">
              ${stats.recentMatches.map(match => this.renderMatchResult(match)).join('')}
            </div>
          </section>
        ` : ''}

        <!-- Player Performance - REAL DATA -->
        ${stats.playerStats && stats.playerStats.length > 0 ? `
          <section class="tab-section">
            <h2 class="section-title">
              <i class="fa-solid fa-users"></i>
              Player Performance
            </h2>
            <div class="player-stats-table">
              ${this.renderPlayerStatsTable(stats.playerStats)}
            </div>
          </section>
        ` : ''}
      </div>
    `;
  }

  /**
   * Render overview stat cards - REAL DATA ONLY
   */
  renderOverviewCards(overview) {
    return `
      <div class="stat-card-large">
        <div class="stat-icon-large">
          <i class="fa-solid fa-gamepad"></i>
        </div>
        <div class="stat-content-large">
          <div class="stat-value-large">${overview.total_matches || 0}</div>
          <div class="stat-label-large">Total Matches</div>
        </div>
      </div>

      <div class="stat-card-large stat-card-success">
        <div class="stat-icon-large">
          <i class="fa-solid fa-trophy"></i>
        </div>
        <div class="stat-content-large">
          <div class="stat-value-large">${overview.wins || 0}</div>
          <div class="stat-label-large">Wins</div>
        </div>
      </div>

      <div class="stat-card-large stat-card-danger">
        <div class="stat-icon-large">
          <i class="fa-solid fa-times-circle"></i>
        </div>
        <div class="stat-content-large">
          <div class="stat-value-large">${overview.losses || 0}</div>
          <div class="stat-label-large">Losses</div>
        </div>
      </div>

      <div class="stat-card-large stat-card-primary">
        <div class="stat-icon-large">
          <i class="fa-solid fa-percentage"></i>
        </div>
        <div class="stat-content-large">
          <div class="stat-value-large">${overview.win_rate ? overview.win_rate.toFixed(1) : 0}%</div>
          <div class="stat-label-large">Win Rate</div>
        </div>
      </div>

      ${overview.current_streak !== undefined ? `
        <div class="stat-card-large ${overview.current_streak > 0 ? 'stat-card-warning' : ''}">
          <div class="stat-icon-large">
            <i class="fa-solid fa-fire"></i>
          </div>
          <div class="stat-content-large">
            <div class="stat-value-large">${Math.abs(overview.current_streak)}</div>
            <div class="stat-label-large">${overview.current_streak > 0 ? 'Win' : overview.current_streak < 0 ? 'Loss' : ''} Streak</div>
          </div>
        </div>
      ` : ''}
    `;
  }

  /**
   * Render match result item - REAL DATA
   */
  renderMatchResult(match) {
    const isWin = match.result === 'win' || match.is_win;
    const resultClass = isWin ? 'win' : 'loss';
    
    return `
      <div class="match-result-item ${resultClass}">
        <div class="match-result-icon">
          <i class="fa-solid fa-${isWin ? 'check-circle' : 'times-circle'}"></i>
        </div>
        <div class="match-result-info">
          <div class="match-opponent">${this.escapeHtml(match.opponent_name || 'Unknown Opponent')}</div>
          <div class="match-date">${this.formatDate(match.date || match.played_at)}</div>
        </div>
        <div class="match-score">
          ${match.score || 'N/A'}
        </div>
      </div>
    `;
  }

  /**
   * Render player stats table - REAL DATA
   */
  renderPlayerStatsTable(playerStats) {
    return `
      <table class="stats-table">
        <thead>
          <tr>
            <th>Player</th>
            <th>Matches</th>
            <th>Win Rate</th>
            <th>MVPs</th>
          </tr>
        </thead>
        <tbody>
          ${playerStats.map(player => `
            <tr>
              <td class="player-name-cell">
                <img src="${player.avatar || '/static/img/user_avatar/default-avatar.png'}" 
                     alt="${this.escapeHtml(player.name)}" 
                     class="player-avatar-tiny">
                <span>${this.escapeHtml(player.name)}</span>
              </td>
              <td>${player.matches_played || 0}</td>
              <td>${player.win_rate ? player.win_rate.toFixed(1) : 0}%</td>
              <td>${player.mvp_count || 0}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  /**
   * Format date
   */
  formatDate(dateString) {
    if (!dateString) return 'Unknown';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: 'numeric' 
      });
    } catch (e) {
      return 'Unknown';
    }
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
