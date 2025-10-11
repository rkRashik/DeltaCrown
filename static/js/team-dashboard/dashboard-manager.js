/**
 * Modern Dashboard Manager
 * Handles dynamic interactions and data updates
 */

class DashboardManager {
  constructor(teamSlug) {
    this.teamSlug = teamSlug;
    this.csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    this.init();
  }

  init() {
    this.bindEvents();
    this.startAutoRefresh();
    this.loadStatistics();
    this.loadMatchHistory();
  }

  bindEvents() {
    // Auto-refresh every 30 seconds for pending items
    this.refreshInterval = setInterval(() => {
      this.refreshPendingItems();
    }, 30000);
  }

  async refreshPendingItems() {
    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/pending-items/`);
      const data = await response.json();
      
      if (data.success) {
        this.updatePendingCount(data.count);
      }
    } catch (error) {
      console.error('Error refreshing pending items:', error);
    }
  }

  updatePendingCount(count) {
    const badge = document.querySelector('.stat-card-danger .stat-value');
    if (badge && parseInt(badge.textContent) !== count) {
      badge.textContent = count;
      this.showToast(`You have ${count} pending item(s)`, 'info');
    }
  }

  startAutoRefresh() {
    // Refresh activity feed every 2 minutes
    setInterval(() => {
      this.refreshActivityFeed();
    }, 120000);
  }

  async refreshActivityFeed() {
    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/recent-activity/`);
      const data = await response.json();
      
      if (data.success && data.activities) {
        this.updateActivityFeed(data.activities);
      }
    } catch (error) {
      console.error('Error refreshing activity feed:', error);
    }
  }

  updateActivityFeed(activities) {
    const feedContainer = document.querySelector('.activity-feed');
    if (!feedContainer) return;

    feedContainer.innerHTML = activities.map(activity => `
      <div class="activity-item">
        <div class="activity-icon activity-${activity.type}">
          <i class="fa-solid fa-${activity.icon}"></i>
        </div>
        <div class="activity-content">
          <div class="activity-description">${this.escapeHtml(activity.description)}</div>
          <div class="activity-time">${activity.time_ago}</div>
        </div>
      </div>
    `).join('');
  }

  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `dashboard-toast dashboard-toast-${type}`;
    toast.innerHTML = `
      <i class="fa-solid fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
      <span>${message}</span>
    `;

    const container = document.getElementById('dashboard-toast-container');
    if (container) {
      container.appendChild(toast);
      setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
      }, 4000);
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Load comprehensive statistics
  async loadStatistics() {
    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/statistics/`);
      const data = await response.json();
      
      if (data.success) {
        this.updateStatisticsDisplay(data.statistics);
        this.loadWinRateChart(data.statistics);
      }
    } catch (error) {
      console.error('Error loading statistics:', error);
    }
  }

  updateStatisticsDisplay(stats) {
    // Update win rate if element exists
    const winRateEl = document.querySelector('.stat-win-rate');
    if (winRateEl) {
      winRateEl.textContent = `${stats.win_rate.toFixed(1)}%`;
    }

    // Update total matches
    const matchesEl = document.querySelector('.stat-total-matches');
    if (matchesEl) {
      matchesEl.textContent = stats.total_matches;
    }

    // Update points
    const pointsEl = document.querySelector('.stat-total-points');
    if (pointsEl) {
      pointsEl.textContent = stats.total_points;
    }

    // Update current streak
    const streakEl = document.querySelector('.stat-current-streak');
    if (streakEl) {
      streakEl.textContent = stats.streak_text;
      streakEl.className = `stat-current-streak streak-${stats.streak_type}`;
    }

    // Update tournaments
    const tournamentsEl = document.querySelector('.stat-tournaments');
    if (tournamentsEl) {
      tournamentsEl.textContent = `${stats.tournaments_won}/${stats.tournaments_participated}`;
    }
  }

  async loadWinRateChart(stats) {
    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/charts/win-rate/`);
      const data = await response.json();
      
      if (data.success && data.chart_data) {
        this.renderWinRateChart(data.chart_data);
      }
    } catch (error) {
      console.error('Error loading chart data:', error);
    }
  }

  renderWinRateChart(chartData) {
    const canvas = document.getElementById('performanceChart');
    if (!canvas || !window.Chart) return;

    // Destroy existing chart if any
    if (this.performanceChart) {
      this.performanceChart.destroy();
    }

    const ctx = canvas.getContext('2d');
    this.performanceChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [{
          label: 'Win Rate %',
          data: chartData.win_rate,
          borderColor: 'rgba(46, 213, 115, 1)',
          backgroundColor: 'rgba(46, 213, 115, 0.1)',
          tension: 0.4,
          fill: true,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            labels: {
              color: '#e0e0e0'
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            ticks: {
              color: '#b0b0b0'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.05)'
            }
          },
          x: {
            ticks: {
              color: '#b0b0b0'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.05)'
            }
          }
        }
      }
    });
  }

  async loadMatchHistory() {
    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/match-history/`);
      const data = await response.json();
      
      if (data.success && data.matches) {
        this.updateMatchHistory(data.matches);
      }
    } catch (error) {
      console.error('Error loading match history:', error);
    }
  }

  updateMatchHistory(matches) {
    const container = document.querySelector('.match-history-list');
    if (!container || matches.length === 0) return;

    container.innerHTML = matches.slice(0, 5).map(match => `
      <div class="match-item match-${match.result}">
        <div class="match-date">${new Date(match.date).toLocaleDateString()}</div>
        <div class="match-opponent">
          ${match.opponent_logo ? `<img src="${match.opponent_logo}" alt="${match.opponent}" class="opponent-logo">` : ''}
          <span>${this.escapeHtml(match.opponent)}</span>
        </div>
        <div class="match-score ${match.result}">${match.score}</div>
        <div class="match-points ${match.points_earned >= 0 ? 'positive' : 'negative'}">
          ${match.points_earned >= 0 ? '+' : ''}${match.points_earned} pts
        </div>
      </div>
    `).join('');
  }

  showToast(message, type = 'info') {
    // Create toast notification
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('show');
    }, 100);

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Action Functions
async function approveRequest(requestId) {
  if (!confirm('Approve this join request?')) return;

  try {
    const response = await fetch(`/teams/api/join-requests/${requestId}/approve/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken()
      }
    });

    const data = await response.json();
    if (data.success) {
      location.reload();
    } else {
      alert('Error: ' + data.error);
    }
  } catch (error) {
    alert('Failed to approve request');
  }
}

async function rejectRequest(requestId) {
  if (!confirm('Reject this join request?')) return;

  try {
    const response = await fetch(`/teams/api/join-requests/${requestId}/reject/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken()
      }
    });

    const data = await response.json();
    if (data.success) {
      location.reload();
    } else {
      alert('Error: ' + data.error);
    }
  } catch (error) {
    alert('Failed to reject request');
  }
}

async function resendInvite(inviteId) {
  try {
    const response = await fetch(`/teams/api/invites/${inviteId}/resend/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken()
      }
    });

    const data = await response.json();
    if (data.success) {
      alert('Invitation resent successfully');
    } else {
      alert('Error: ' + data.error);
    }
  } catch (error) {
    alert('Failed to resend invitation');
  }
}

async function cancelInvite(inviteId) {
  if (!confirm('Cancel this invitation?')) return;

  try {
    const response = await fetch(`/teams/api/invites/${inviteId}/cancel/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken()
      }
    });

    const data = await response.json();
    if (data.success) {
      location.reload();
    } else {
      alert('Error: ' + data.error);
    }
  } catch (error) {
    alert('Failed to cancel invitation');
  }
}

function inviteMember() {
  const username = prompt('Enter username or email to invite:');
  if (username) {
    window.location.href = `/teams/${getTeamSlug()}/invite/?user=${encodeURIComponent(username)}`;
  }
}

function scheduleMatch() {
  window.location.href = `/teams/${getTeamSlug()}/matches/schedule/`;
}

function createPost() {
  window.location.href = `/teams/${getTeamSlug()}/posts/create/`;
}

function getCsrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

function getTeamSlug() {
  return document.querySelector('.modern-dashboard')?.dataset.teamSlug || '';
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const dashboard = document.querySelector('.modern-dashboard');
  if (dashboard) {
    const teamSlug = dashboard.dataset.teamSlug;
    if (teamSlug) {
      new DashboardManager(teamSlug);
    }
  }
});
