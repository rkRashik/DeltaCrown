/**
 * Player Statistics Modal Manager
 * Handles displaying detailed player performance stats
 */

class PlayerStatsManager {
  constructor(teamSlug) {
    this.teamSlug = teamSlug;
    this.playerStats = null;
    this.init();
  }

  init() {
    this.loadAllPlayerStats();
    this.bindEvents();
  }

  bindEvents() {
    // Listen for player card clicks
    document.addEventListener('click', (e) => {
      const playerCard = e.target.closest('[data-player-id]');
      if (playerCard) {
        const playerId = playerCard.dataset.playerId;
        this.showPlayerStatsModal(playerId);
      }
    });

    // Close modal on background click
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-overlay')) {
        this.closeModal();
      }
    });

    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeModal();
      }
    });
  }

  async loadAllPlayerStats() {
    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/player-stats/`);
      const data = await response.json();
      
      if (data.success) {
        this.playerStats = data.player_stats;
        this.updateRosterWithStats();
      }
    } catch (error) {
      console.error('Error loading player stats:', error);
    }
  }

  updateRosterWithStats() {
    if (!this.playerStats) return;

    // Add click handlers and stats preview to roster cards
    this.playerStats.forEach(player => {
      const cards = document.querySelectorAll(`[data-player-username="${player.username}"]`);
      cards.forEach(card => {
        card.dataset.playerId = player.player_id;
        card.style.cursor = 'pointer';
        card.title = 'Click to view detailed statistics';
        
        // Add quick stats badge if not already present
        if (!card.querySelector('.player-quick-stats')) {
          const quickStats = document.createElement('div');
          quickStats.className = 'player-quick-stats';
          quickStats.innerHTML = `
            <span class="quick-stat" title="Win Rate">
              <i class="fa-solid fa-trophy"></i> ${player.win_rate.toFixed(1)}%
            </span>
            <span class="quick-stat" title="Matches">
              <i class="fa-solid fa-gamepad"></i> ${player.matches_played}
            </span>
          `;
          card.appendChild(quickStats);
        }
      });
    });
  }

  showPlayerStatsModal(playerId) {
    const player = this.playerStats?.find(p => p.player_id == playerId);
    if (!player) return;

    const modal = this.createModal(player);
    document.body.appendChild(modal);
    
    // Trigger animation
    setTimeout(() => modal.classList.add('active'), 10);
    
    // Render charts
    setTimeout(() => this.renderPlayerCharts(player), 100);
  }

  createModal(player) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'playerStatsModal';
    
    const avatarHtml = player.avatar 
      ? `<img src="${player.avatar}" alt="${player.display_name}" class="modal-player-avatar">`
      : `<div class="modal-player-avatar-placeholder">${player.display_name.charAt(0).toUpperCase()}</div>`;
    
    modal.innerHTML = `
      <div class="modal-container player-stats-modal">
        <div class="modal-header">
          <div class="modal-header-content">
            ${avatarHtml}
            <div>
              <h2>${this.escapeHtml(player.display_name)}</h2>
              <p class="modal-subtitle">${this.escapeHtml(player.role)}</p>
            </div>
          </div>
          <button class="modal-close" onclick="document.getElementById('playerStatsModal').remove()">
            <i class="fa-solid fa-times"></i>
          </button>
        </div>
        
        <div class="modal-body">
          <!-- Stats Grid -->
          <div class="player-stats-grid">
            <div class="stat-box">
              <div class="stat-icon">
                <i class="fa-solid fa-trophy"></i>
              </div>
              <div class="stat-content">
                <div class="stat-label">Win Rate</div>
                <div class="stat-value-large">${player.win_rate.toFixed(1)}%</div>
              </div>
            </div>
            
            <div class="stat-box">
              <div class="stat-icon">
                <i class="fa-solid fa-gamepad"></i>
              </div>
              <div class="stat-content">
                <div class="stat-label">Matches Played</div>
                <div class="stat-value-large">${player.matches_played}</div>
              </div>
            </div>
            
            <div class="stat-box">
              <div class="stat-icon">
                <i class="fa-solid fa-chart-line"></i>
              </div>
              <div class="stat-content">
                <div class="stat-label">Rating</div>
                <div class="stat-value-large">${player.individual_rating.toFixed(0)}</div>
              </div>
            </div>
            
            <div class="stat-box">
              <div class="stat-icon">
                <i class="fa-solid fa-star"></i>
              </div>
              <div class="stat-content">
                <div class="stat-label">MVP Awards</div>
                <div class="stat-value-large">${player.mvp_count}</div>
              </div>
            </div>
          </div>

          <!-- Detailed Stats -->
          <div class="stats-section">
            <h3><i class="fa-solid fa-chart-bar"></i> Performance Metrics</h3>
            <div class="stats-table">
              <div class="stats-row">
                <span class="stats-label">Tournaments Played</span>
                <span class="stats-value">${player.tournaments_played}</span>
              </div>
              <div class="stats-row">
                <span class="stats-label">Matches Won</span>
                <span class="stats-value">${player.matches_won}</span>
              </div>
              <div class="stats-row">
                <span class="stats-label">Attendance Rate</span>
                <span class="stats-value">${player.attendance_rate.toFixed(1)}%</span>
              </div>
              <div class="stats-row">
                <span class="stats-label">Contribution Score</span>
                <span class="stats-value">${player.contribution_score.toFixed(2)}</span>
              </div>
              <div class="stats-row">
                <span class="stats-label">Status</span>
                <span class="stats-value">
                  ${player.is_active 
                    ? '<span class="badge-success">Active</span>' 
                    : '<span class="badge-inactive">Inactive</span>'}
                </span>
              </div>
              ${player.last_active ? `
              <div class="stats-row">
                <span class="stats-label">Last Active</span>
                <span class="stats-value">${new Date(player.last_active).toLocaleDateString()}</span>
              </div>
              ` : ''}
            </div>
          </div>

          <!-- Performance Chart -->
          <div class="stats-section">
            <h3><i class="fa-solid fa-radar"></i> Performance Overview</h3>
            <canvas id="playerPerformanceChart" height="250"></canvas>
          </div>

          <!-- Game-Specific Stats -->
          ${this.renderGameSpecificStats(player.game_specific_stats)}
        </div>
        
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="document.getElementById('playerStatsModal').remove()">
            <i class="fa-solid fa-times"></i> Close
          </button>
          <button class="btn btn-primary" onclick="window.playerStatsManager?.comparePlayer(${player.player_id})">
            <i class="fa-solid fa-balance-scale"></i> Compare
          </button>
        </div>
      </div>
    `;
    
    return modal;
  }

  renderGameSpecificStats(stats) {
    if (!stats || Object.keys(stats).length === 0) {
      return '';
    }

    let html = '<div class="stats-section"><h3><i class="fa-solid fa-gamepad"></i> Game-Specific Stats</h3><div class="stats-table">';
    
    for (const [key, value] of Object.entries(stats)) {
      const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      html += `
        <div class="stats-row">
          <span class="stats-label">${this.escapeHtml(label)}</span>
          <span class="stats-value">${this.escapeHtml(String(value))}</span>
        </div>
      `;
    }
    
    html += '</div></div>';
    return html;
  }

  renderPlayerCharts(player) {
    const canvas = document.getElementById('playerPerformanceChart');
    if (!canvas || !window.Chart) return;

    const ctx = canvas.getContext('2d');
    
    // Create radar chart for performance metrics
    new Chart(ctx, {
      type: 'radar',
      data: {
        labels: ['Win Rate', 'Attendance', 'Contribution', 'Rating', 'MVP Rate'],
        datasets: [{
          label: player.display_name,
          data: [
            player.win_rate,
            player.attendance_rate,
            Math.min(player.contribution_score / 10, 100), // Normalize to 0-100
            Math.min(player.individual_rating / 20, 100), // Normalize to 0-100
            player.matches_played > 0 ? (player.mvp_count / player.matches_played * 100) : 0
          ],
          backgroundColor: 'rgba(108, 92, 231, 0.2)',
          borderColor: 'rgba(108, 92, 231, 1)',
          borderWidth: 2,
          pointBackgroundColor: 'rgba(108, 92, 231, 1)',
          pointBorderColor: '#fff',
          pointHoverBackgroundColor: '#fff',
          pointHoverBorderColor: 'rgba(108, 92, 231, 1)'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          r: {
            beginAtZero: true,
            max: 100,
            ticks: {
              color: '#b0b0b0',
              backdropColor: 'transparent'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            pointLabels: {
              color: '#e0e0e0',
              font: {
                size: 12
              }
            }
          }
        }
      }
    });
  }

  comparePlayer(playerId) {
    // TODO: Implement player comparison feature
    alert('Player comparison feature coming soon!');
  }

  closeModal() {
    const modal = document.getElementById('playerStatsModal');
    if (modal) {
      modal.classList.remove('active');
      setTimeout(() => modal.remove(), 300);
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Initialize player stats manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const dashboard = document.querySelector('.modern-dashboard');
  const teamDetail = document.querySelector('[data-team-slug]');
  
  if (dashboard || teamDetail) {
    const teamSlug = dashboard?.dataset.teamSlug || teamDetail?.dataset.teamSlug;
    if (teamSlug) {
      window.playerStatsManager = new PlayerStatsManager(teamSlug);
    }
  }
});
