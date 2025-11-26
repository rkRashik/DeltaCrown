/**
 * Tournament Detail - Advanced Features JavaScript
 * Handles: Rules Drawer, Live Bracket, Prize Visualization, Match Scheduler
 */

class TournamentFeatures {
    constructor(tournamentSlug) {
        this.tournamentSlug = tournamentSlug;
        this.rulesDrawer = null;
        this.bracketZoom = 1;
        this.init();
    }

    init() {
        this.initRulesDrawer();
        this.initBracketViewer();
        this.initPrizeChart();
        this.initMatchScheduler();
    }

    // ========================================================================
    // RULES DRAWER
    // ========================================================================
    initRulesDrawer() {
        const triggerBtn = document.querySelector('.rules-trigger-btn');
        const overlay = document.querySelector('.rules-drawer-overlay');
        const drawer = document.querySelector('.rules-drawer');
        const closeBtn = document.querySelector('.rules-drawer-close');
        const searchInput = document.querySelector('.rules-search-input');

        if (triggerBtn) {
            triggerBtn.addEventListener('click', () => this.openRulesDrawer());
        }

        if (overlay) {
            overlay.addEventListener('click', () => this.closeRulesDrawer());
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeRulesDrawer());
        }

        // Accordion functionality
        const sectionHeaders = document.querySelectorAll('.rules-section-header');
        sectionHeaders.forEach(header => {
            header.addEventListener('click', () => this.toggleRulesSection(header));
        });

        // Search functionality
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.searchRules(e.target.value));
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && drawer?.classList.contains('active')) {
                this.closeRulesDrawer();
            }
            if (e.key === 'r' && e.ctrlKey) {
                e.preventDefault();
                this.openRulesDrawer();
            }
        });
    }

    openRulesDrawer() {
        const overlay = document.querySelector('.rules-drawer-overlay');
        const drawer = document.querySelector('.rules-drawer');
        
        if (overlay && drawer) {
            overlay.classList.add('active');
            drawer.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    closeRulesDrawer() {
        const overlay = document.querySelector('.rules-drawer-overlay');
        const drawer = document.querySelector('.rules-drawer');
        
        if (overlay && drawer) {
            overlay.classList.remove('active');
            drawer.classList.remove('active');
            document.body.style.overflow = '';
        }
    }

    toggleRulesSection(header) {
        const body = header.nextElementSibling;
        const isActive = header.classList.contains('active');

        // Close all sections
        document.querySelectorAll('.rules-section-header').forEach(h => {
            h.classList.remove('active');
            h.nextElementSibling.classList.remove('active');
        });

        // Open clicked section if it wasn't active
        if (!isActive) {
            header.classList.add('active');
            body.classList.add('active');
        }
    }

    searchRules(query) {
        const sections = document.querySelectorAll('.rules-section');
        const lowerQuery = query.toLowerCase();

        sections.forEach(section => {
            const content = section.textContent.toLowerCase();
            if (content.includes(lowerQuery) || query === '') {
                section.style.display = '';
            } else {
                section.style.display = 'none';
            }
        });
    }

    // ========================================================================
    // LIVE BRACKET VIEWER
    // ========================================================================
    initBracketViewer() {
        this.loadBracketData();
        this.initBracketControls();
        this.initBracketInteractions();
    }

    async loadBracketData() {
        try {
            const response = await fetch(`/api/tournaments/${this.tournamentSlug}/bracket/`);
            if (!response.ok) throw new Error('Failed to load bracket');
            
            const data = await response.json();
            this.renderBracket(data);
        } catch (error) {
            console.error('Bracket loading error:', error);
            this.showBracketError();
        }
    }

    renderBracket(data) {
        const container = document.querySelector('.bracket-grid');
        if (!container) return;

        container.innerHTML = '';

        // Render each round
        data.rounds.forEach((round, roundIndex) => {
            const roundEl = document.createElement('div');
            roundEl.className = 'bracket-round';
            
            const titleEl = document.createElement('div');
            titleEl.className = 'bracket-round-title';
            titleEl.textContent = round.name || `Round ${roundIndex + 1}`;
            roundEl.appendChild(titleEl);

            // Render matches in this round
            round.matches.forEach(match => {
                const matchEl = this.createMatchCard(match);
                roundEl.appendChild(matchEl);
            });

            container.appendChild(roundEl);
        });
    }

    createMatchCard(match) {
        const card = document.createElement('div');
        card.className = `bracket-match ${match.status}`;
        card.dataset.matchId = match.id;

        const status = match.status === 'LIVE' ? 'live' : 
                      match.status === 'COMPLETED' ? 'completed' : 'upcoming';

        card.innerHTML = `
            <div class="bracket-match-header">
                <span class="bracket-match-id">Match #${match.match_number || match.id}</span>
                <span class="bracket-match-status ${status}">${status}</span>
            </div>
            <div class="bracket-match-teams">
                ${this.renderBracketTeam(match.team_a, match.score_a, match.status === 'COMPLETED' && match.winner_id === match.team_a?.id)}
                ${this.renderBracketTeam(match.team_b, match.score_b, match.status === 'COMPLETED' && match.winner_id === match.team_b?.id)}
            </div>
        `;

        return card;
    }

    renderBracketTeam(team, score, isWinner) {
        if (!team) {
            return `
                <div class="bracket-team">
                    <div class="bracket-team-logo"></div>
                    <div class="bracket-team-info">
                        <div class="bracket-team-name">TBD</div>
                        <div class="bracket-team-seed">-</div>
                    </div>
                    <div class="bracket-team-score">-</div>
                </div>
            `;
        }

        const winnerClass = isWinner ? 'winner' : (score !== null && score !== undefined ? 'loser' : '');
        
        return `
            <div class="bracket-team ${winnerClass}">
                ${team.logo ? 
                    `<img src="${team.logo}" alt="${team.name}" class="bracket-team-logo">` :
                    `<div class="bracket-team-logo"></div>`
                }
                <div class="bracket-team-info">
                    <div class="bracket-team-name">${team.name}</div>
                    <div class="bracket-team-seed">Seed ${team.seed || '-'}</div>
                </div>
                <div class="bracket-team-score">${score !== null && score !== undefined ? score : '-'}</div>
            </div>
        `;
    }

    initBracketControls() {
        // View toggle
        const viewBtns = document.querySelectorAll('.bracket-view-btn');
        viewBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                viewBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.switchBracketView(btn.dataset.view);
            });
        });

        // Zoom controls
        const zoomInBtn = document.querySelector('[data-zoom="in"]');
        const zoomOutBtn = document.querySelector('[data-zoom="out"]');
        const resetBtn = document.querySelector('[data-zoom="reset"]');

        if (zoomInBtn) {
            zoomInBtn.addEventListener('click', () => this.zoomBracket(0.1));
        }
        if (zoomOutBtn) {
            zoomOutBtn.addEventListener('click', () => this.zoomBracket(-0.1));
        }
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetBracketZoom());
        }
    }

    switchBracketView(view) {
        const container = document.querySelector('.bracket-container');
        if (container) {
            container.dataset.view = view;
            // Re-render bracket based on view
            this.loadBracketData();
        }
    }

    zoomBracket(delta) {
        const grid = document.querySelector('.bracket-grid');
        if (!grid) return;

        this.bracketZoom = Math.max(0.5, Math.min(2, this.bracketZoom + delta));
        grid.style.transform = `scale(${this.bracketZoom})`;
        grid.style.transformOrigin = 'top left';
    }

    resetBracketZoom() {
        const grid = document.querySelector('.bracket-grid');
        if (!grid) return;

        this.bracketZoom = 1;
        grid.style.transform = 'scale(1)';
    }

    initBracketInteractions() {
        // Click on match to show details
        document.addEventListener('click', (e) => {
            const matchCard = e.target.closest('.bracket-match');
            if (matchCard) {
                this.showMatchDetails(matchCard.dataset.matchId);
            }
        });
    }

    showMatchDetails(matchId) {
        // Open modal or drawer with detailed match information
        dcLog('Show match details:', matchId);
        // TODO: Implement match details modal
    }

    showBracketError() {
        const container = document.querySelector('.bracket-grid');
        if (container) {
            container.innerHTML = `
                <div style="text-align: center; padding: 60px 20px; color: rgba(255,255,255,0.5);">
                    <svg width="64" height="64" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="margin: 0 auto 16px;">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="8" x2="12" y2="12"/>
                        <line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    <p style="font-size: 18px; font-weight: 600;">Bracket data not available</p>
                    <p style="font-size: 14px; margin-top: 8px;">The tournament bracket will be generated after registration closes.</p>
                </div>
            `;
        }
    }

    // ========================================================================
    // PRIZE VISUALIZATION
    // ========================================================================
    initPrizeChart() {
        const chartCanvas = document.getElementById('prizeChart');
        if (!chartCanvas) return;

        const prizeData = JSON.parse(chartCanvas.dataset.prizes || '[]');
        this.renderPrizeChart(chartCanvas, prizeData);
    }

    renderPrizeChart(canvas, data) {
        // Simple pie chart rendering (can be enhanced with Chart.js)
        const ctx = canvas.getContext('2d');
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 10;

        let currentAngle = -Math.PI / 2;
        const total = data.reduce((sum, item) => sum + item.amount, 0);

        const colors = ['#FFD700', '#C0C0C0', '#CD7F32', '#00ff88', '#ff4655', '#8b5cf6'];

        data.forEach((item, index) => {
            const sliceAngle = (item.amount / total) * 2 * Math.PI;
            
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
            ctx.closePath();
            
            ctx.fillStyle = colors[index % colors.length];
            ctx.fill();
            
            ctx.strokeStyle = '#14141f';
            ctx.lineWidth = 3;
            ctx.stroke();
            
            currentAngle += sliceAngle;
        });
    }

    // ========================================================================
    // MATCH SCHEDULER
    // ========================================================================
    initMatchScheduler() {
        const schedulerBtns = document.querySelectorAll('.add-to-calendar-btn');
        
        schedulerBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const matchId = btn.dataset.matchId;
                const matchDate = btn.dataset.matchDate;
                const matchTitle = btn.dataset.matchTitle;
                
                this.addToCalendar(matchTitle, matchDate);
            });
        });
    }

    addToCalendar(title, dateStr) {
        const date = new Date(dateStr);
        const endDate = new Date(date.getTime() + 2 * 60 * 60 * 1000); // +2 hours

        const formatDate = (d) => {
            return d.toISOString().replace(/-|:|\.\d+/g, '');
        };

        // Google Calendar URL
        const googleUrl = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(title)}&dates=${formatDate(date)}/${formatDate(endDate)}&details=${encodeURIComponent(`DeltaCrown Tournament Match`)}&location=${encodeURIComponent('Online')}`;

        // Open in new tab
        window.open(googleUrl, '_blank');
        
        this.showToast('Match added to calendar!', 'success');
    }

    // ========================================================================
    // UTILITIES
    // ========================================================================
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 16px 24px;
            background: ${type === 'success' ? 'rgba(0, 255, 136, 0.15)' : 'rgba(255, 255, 255, 0.1)'};
            border: 1px solid ${type === 'success' ? '#00ff88' : 'rgba(255, 255, 255, 0.2)'};
            border-radius: 12px;
            color: white;
            font-size: 14px;
            font-weight: 600;
            z-index: 10000;
            animation: slideInRight 0.3s ease;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
}

// Auto-initialize
document.addEventListener('DOMContentLoaded', () => {
    const tournamentSlug = document.querySelector('[data-tournament-slug]')?.dataset.tournamentSlug;
    if (tournamentSlug) {
        window.tournamentFeatures = new TournamentFeatures(tournamentSlug);
    }
});

// CSS Animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
