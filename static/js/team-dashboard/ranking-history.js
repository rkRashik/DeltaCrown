/**
 * Ranking History Manager
 * Visualizes team ranking progression over time
 */

class RankingHistoryManager {
  constructor(teamSlug) {
    this.teamSlug = teamSlug;
    this.rankingChart = null;
    this.init();
  }

  init() {
    this.loadRankingHistory();
    this.loadRankingBreakdown();
  }

  async loadRankingHistory() {
    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/ranking-history/`);
      const data = await response.json();
      
      if (data.success) {
        this.renderRankingChart(data.chart_data);
        if (data.current_breakdown) {
          this.displayRankingBreakdown(data.current_breakdown);
        }
      }
    } catch (error) {
      console.error('Error loading ranking history:', error);
    }
  }

  renderRankingChart(chartData) {
    const canvas = document.getElementById('rankingHistoryChart');
    if (!canvas || !window.Chart) return;

    // Destroy existing chart
    if (this.rankingChart) {
      this.rankingChart.destroy();
    }

    const ctx = canvas.getContext('2d');
    
    this.rankingChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: 'Total Points',
            data: chartData.points,
            borderColor: 'rgba(108, 92, 231, 1)',
            backgroundColor: 'rgba(108, 92, 231, 0.1)',
            yAxisID: 'y-points',
            tension: 0.4,
            fill: true,
            pointRadius: 4,
            pointHoverRadius: 6,
          },
          {
            label: 'Global Rank',
            data: chartData.global_rank,
            borderColor: 'rgba(46, 213, 115, 1)',
            backgroundColor: 'rgba(46, 213, 115, 0.1)',
            yAxisID: 'y-rank',
            tension: 0.4,
            fill: false,
            pointRadius: 4,
            pointHoverRadius: 6,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              color: '#e0e0e0',
              usePointStyle: true,
              padding: 15,
            }
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#ffffff',
            bodyColor: '#e0e0e0',
            borderColor: 'rgba(108, 92, 231, 0.5)',
            borderWidth: 1,
            padding: 12,
            displayColors: true,
          }
        },
        scales: {
          'y-points': {
            type: 'linear',
            position: 'left',
            beginAtZero: true,
            ticks: {
              color: '#b0b0b0'
            },
            grid: {
              color: 'rgba(255, 255, 255, 0.05)'
            },
            title: {
              display: true,
              text: 'Points',
              color: '#e0e0e0'
            }
          },
          'y-rank': {
            type: 'linear',
            position: 'right',
            beginAtZero: false,
            reverse: true, // Lower rank number is better
            ticks: {
              color: '#b0b0b0',
              precision: 0
            },
            grid: {
              display: false
            },
            title: {
              display: true,
              text: 'Global Rank',
              color: '#e0e0e0'
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

  displayRankingBreakdown(breakdown) {
    const container = document.getElementById('rankingBreakdownDisplay');
    if (!container) return;

    const total = breakdown.final_total;
    
    // Calculate percentages
    const tournamentPercent = ((breakdown.tournament_points / total) * 100).toFixed(1);
    const winLossPercent = ((breakdown.win_loss_points / total) * 100).toFixed(1);
    const activityPercent = ((breakdown.activity_bonus / total) * 100).toFixed(1);
    const adjustmentPercent = ((breakdown.adjustment_points / total) * 100).toFixed(1);

    container.innerHTML = `
      <div class="breakdown-item">
        <div class="breakdown-label">
          <i class="fa-solid fa-trophy"></i>
          Tournament Points
        </div>
        <div class="breakdown-bar">
          <div class="breakdown-fill" style="width: ${tournamentPercent}%; background: linear-gradient(90deg, rgba(255, 215, 0, 0.8), rgba(255, 215, 0, 0.4));"></div>
        </div>
        <div class="breakdown-value">${breakdown.tournament_points} pts (${tournamentPercent}%)</div>
      </div>

      <div class="breakdown-item">
        <div class="breakdown-label">
          <i class="fa-solid fa-gamepad"></i>
          Win/Loss Points
        </div>
        <div class="breakdown-bar">
          <div class="breakdown-fill" style="width: ${winLossPercent}%; background: linear-gradient(90deg, rgba(46, 213, 115, 0.8), rgba(46, 213, 115, 0.4));"></div>
        </div>
        <div class="breakdown-value">${breakdown.win_loss_points} pts (${winLossPercent}%)</div>
      </div>

      <div class="breakdown-item">
        <div class="breakdown-label">
          <i class="fa-solid fa-bolt"></i>
          Activity Bonus
        </div>
        <div class="breakdown-bar">
          <div class="breakdown-fill" style="width: ${activityPercent}%; background: linear-gradient(90deg, rgba(108, 92, 231, 0.8), rgba(108, 92, 231, 0.4));"></div>
        </div>
        <div class="breakdown-value">${breakdown.activity_bonus} pts (${activityPercent}%)</div>
      </div>

      ${breakdown.adjustment_points !== 0 ? `
        <div class="breakdown-item">
          <div class="breakdown-label">
            <i class="fa-solid fa-sliders"></i>
            Adjustments
          </div>
          <div class="breakdown-bar">
            <div class="breakdown-fill" style="width: ${Math.abs(adjustmentPercent)}%; background: linear-gradient(90deg, rgba(241, 196, 15, 0.8), rgba(241, 196, 15, 0.4));"></div>
          </div>
          <div class="breakdown-value">${breakdown.adjustment_points > 0 ? '+' : ''}${breakdown.adjustment_points} pts (${adjustmentPercent}%)</div>
        </div>
      ` : ''}

      <div class="breakdown-total">
        <div class="breakdown-label">
          <i class="fa-solid fa-equals"></i>
          Total Points
        </div>
        <div class="breakdown-value total-value">${breakdown.final_total} pts</div>
      </div>
    `;
  }

  async loadRankingBreakdown() {
    // Already loaded with ranking history
    // This method is kept for future separate loading if needed
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const dashboard = document.querySelector('.modern-dashboard');
  const teamDetail = document.querySelector('[data-team-slug]');
  
  if (dashboard || teamDetail) {
    const teamSlug = dashboard?.dataset.teamSlug || teamDetail?.dataset.teamSlug;
    if (teamSlug) {
      window.rankingHistoryManager = new RankingHistoryManager(teamSlug);
    }
  }
});
