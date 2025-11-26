/**
 * Tournament Advanced Features JavaScript
 * Team Comparison, Live Stream, Chat, Match Predictions
 */

class TournamentAdvancedFeatures {
    constructor(tournamentSlug) {
        this.tournamentSlug = tournamentSlug;
        this.comparisonTeams = { teamA: null, teamB: null };
        this.chatMessages = [];
        this.chatWs = null;
        this.init();
    }

    init() {
        this.initTeamComparison();
        this.initLiveStream();
        this.initChat();
        this.initMatchPredictions();
    }

    // ========================================================================
    // TEAM COMPARISON TOOL
    // ========================================================================
    initTeamComparison() {
        const compareBtns = document.querySelectorAll('.compare-teams-btn');
        compareBtns.forEach(btn => {
            btn.addEventListener('click', () => this.openComparison());
        });

        // Close modal
        const overlay = document.querySelector('.comparison-modal-overlay');
        const closeBtn = document.querySelector('.comparison-close');
        
        if (overlay) {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) this.closeComparison();
            });
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeComparison());
        }

        // Team selection
        this.initTeamSelectors();
    }

    async openComparison() {
        const overlay = document.querySelector('.comparison-modal-overlay');
        if (overlay) {
            overlay.classList.add('active');
            await this.loadTeamsList();
        }
    }

    closeComparison() {
        const overlay = document.querySelector('.comparison-modal-overlay');
        if (overlay) {
            overlay.classList.remove('active');
        }
    }

    async loadTeamsList() {
        try {
            const response = await fetch(`/api/tournaments/${this.tournamentSlug}/participants/`);
            const data = await response.json();
            this.populateTeamDropdowns(data.teams);
        } catch (error) {
            console.error('Failed to load teams:', error);
        }
    }

    populateTeamDropdowns(teams) {
        const dropdowns = document.querySelectorAll('.team-dropdown');
        dropdowns.forEach(dropdown => {
            dropdown.innerHTML = teams.map(team => `
                <div class="team-dropdown-item" data-team-id="${team.id}">
                    ${team.logo ? 
                        `<img src="${team.logo}" alt="${team.name}" class="team-dropdown-logo">` :
                        `<div class="team-dropdown-logo"></div>`
                    }
                    <div>
                        <div style="font-weight: 600;">${team.name}</div>
                        <div style="font-size: 12px; color: rgba(255,255,255,0.5);">
                            ${team.players.length} players
                        </div>
                    </div>
                </div>
            `).join('');
        });
    }

    initTeamSelectors() {
        const selectBtns = document.querySelectorAll('.team-select-btn');
        
        selectBtns.forEach((btn, index) => {
            btn.addEventListener('click', () => {
                const dropdown = btn.nextElementSibling;
                if (dropdown) {
                    dropdown.classList.toggle('active');
                }
            });
        });

        // Team selection from dropdown
        document.addEventListener('click', (e) => {
            const item = e.target.closest('.team-dropdown-item');
            if (item) {
                const teamId = item.dataset.teamId;
                const dropdown = item.closest('.team-dropdown');
                const selectBox = dropdown.previousElementSibling;
                
                this.selectTeam(teamId, selectBox);
                dropdown.classList.remove('active');
            }
        });
    }

    async selectTeam(teamId, selectBtn) {
        try {
            const response = await fetch(`/api/tournaments/team/${teamId}/stats/`);
            const teamData = await response.json();
            
            // Update button display
            selectBtn.classList.add('selected');
            selectBtn.innerHTML = `
                ${teamData.logo ? 
                    `<img src="${teamData.logo}" alt="${teamData.name}" class="team-select-logo">` :
                    `<div class="team-select-logo"></div>`
                }
                <div class="team-select-info">
                    <div class="team-select-name">${teamData.name}</div>
                    <div class="team-select-players">${teamData.players.length} players</div>
                </div>
            `;
            
            // Store team data
            const side = selectBtn.dataset.side;
            this.comparisonTeams[side] = teamData;
            
            // If both teams selected, load comparison
            if (this.comparisonTeams.teamA && this.comparisonTeams.teamB) {
                await this.loadComparison();
            }
        } catch (error) {
            console.error('Failed to load team:', error);
        }
    }

    async loadComparison() {
        const teamA = this.comparisonTeams.teamA;
        const teamB = this.comparisonTeams.teamB;
        
        const statsContainer = document.querySelector('.comparison-stats');
        if (!statsContainer) return;

        // Calculate percentages for bar charts
        const stats = [
            { 
                label: 'Wins', 
                desc: 'Total victories',
                valueA: teamA.wins || 0, 
                valueB: teamB.wins || 0 
            },
            { 
                label: 'Win Rate', 
                desc: 'Overall win percentage',
                valueA: teamA.win_rate || 0, 
                valueB: teamB.win_rate || 0,
                isPercentage: true
            },
            { 
                label: 'Matches Played', 
                desc: 'Total tournament matches',
                valueA: teamA.matches_played || 0, 
                valueB: teamB.matches_played || 0 
            },
            { 
                label: 'Average Score', 
                desc: 'Points per match',
                valueA: teamA.avg_score || 0, 
                valueB: teamB.avg_score || 0 
            },
            { 
                label: 'Current Rank', 
                desc: 'Tournament standing',
                valueA: teamA.rank || '-', 
                valueB: teamB.rank || '-',
                invert: true
            }
        ];

        statsContainer.innerHTML = stats.map(stat => {
            const total = stat.valueA + stat.valueB;
            const percentA = total > 0 ? (stat.valueA / total) * 50 : 0;
            const percentB = total > 0 ? (stat.valueB / total) * 50 : 0;
            
            return `
                <div class="stat-row">
                    <div class="stat-value left">
                        ${stat.isPercentage ? stat.valueA + '%' : stat.valueA}
                    </div>
                    <div class="stat-label">
                        <div class="stat-label-title">${stat.label}</div>
                        <div class="stat-label-desc">${stat.desc}</div>
                    </div>
                    <div class="stat-value right">
                        ${stat.isPercentage ? stat.valueB + '%' : stat.valueB}
                    </div>
                    <div class="stat-bar-container">
                        <div class="stat-bar left" style="width: ${percentA}%;"></div>
                        <div class="stat-bar right" style="width: ${percentB}%;"></div>
                    </div>
                </div>
            `;
        }).join('');

        // Load head-to-head
        await this.loadHeadToHead(teamA.id, teamB.id);
    }

    async loadHeadToHead(teamAId, teamBId) {
        try {
            const response = await fetch(`/api/tournaments/h2h/${teamAId}/${teamBId}/`);
            const data = await response.json();
            
            const h2hSection = document.querySelector('.h2h-section');
            if (h2hSection && data.matches.length > 0) {
                h2hSection.style.display = 'block';
                
                // Update win counts
                document.querySelector('.h2h-wins-count.green').textContent = data.teamA_wins;
                document.querySelector('.h2h-wins-count.red').textContent = data.teamB_wins;
                
                // Update match history
                const historyContainer = document.querySelector('.match-history');
                historyContainer.innerHTML = data.matches.map(match => `
                    <div class="history-match">
                        <div class="history-team">
                            <span>${match.teamA_name}</span>
                            <span class="history-score ${match.winner_id === match.teamA_id ? 'winner' : ''}">
                                ${match.score_a}
                            </span>
                        </div>
                        <div style="color: rgba(255,255,255,0.3);">-</div>
                        <div class="history-team right">
                            <span class="history-score ${match.winner_id === match.teamB_id ? 'winner' : ''}">
                                ${match.score_b}
                            </span>
                            <span>${match.teamB_name}</span>
                        </div>
                    </div>
                `).join('');
            }
        } catch (error) {
            console.error('Failed to load H2H:', error);
        }
    }

    // ========================================================================
    // LIVE STREAM INTEGRATION
    // ========================================================================
    initLiveStream() {
        const streamPlayer = document.querySelector('.stream-player');
        const pipBtn = document.querySelector('.stream-btn.pip');
        const fullscreenBtn = document.querySelector('.stream-btn.fullscreen');
        
        if (pipBtn) {
            pipBtn.addEventListener('click', () => this.togglePictureInPicture());
        }
        
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', () => this.toggleFullscreen());
        }

        // Load stream if available
        this.loadStreamData();
        
        // Auto-refresh viewer count
        setInterval(() => this.updateViewerCount(), 30000);
    }

    async loadStreamData() {
        try {
            const response = await fetch(`/api/tournaments/${this.tournamentSlug}/stream/`);
            const data = await response.json();
            
            if (data.stream_url) {
                this.embedStream(data.stream_url, data.platform);
            }
            
            if (data.viewers) {
                document.querySelector('.stream-viewers').textContent = 
                    `${data.viewers.toLocaleString()} watching`;
            }
        } catch (error) {
            console.error('Failed to load stream:', error);
        }
    }

    embedStream(url, platform) {
        const playerWrapper = document.querySelector('.stream-player-wrapper');
        if (!playerWrapper) return;

        let embedUrl = url;
        
        // Convert to embed URLs
        if (platform === 'twitch') {
            const channel = url.split('/').pop();
            embedUrl = `https://player.twitch.tv/?channel=${channel}&parent=${window.location.hostname}`;
        } else if (platform === 'youtube') {
            const videoId = url.split('v=')[1];
            embedUrl = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
        }
        
        playerWrapper.innerHTML = `
            <iframe class="stream-player" 
                    src="${embedUrl}" 
                    allowfullscreen 
                    allow="autoplay; encrypted-media; picture-in-picture">
            </iframe>
        `;
        
        playerWrapper.classList.add('live');
    }

    async togglePictureInPicture() {
        const video = document.querySelector('.stream-player');
        if (!video) return;

        try {
            if (document.pictureInPictureElement) {
                await document.exitPictureInPicture();
            } else {
                await video.requestPictureInPicture();
            }
        } catch (error) {
            console.error('PIP failed:', error);
        }
    }

    toggleFullscreen() {
        const wrapper = document.querySelector('.stream-player-wrapper');
        if (!wrapper) return;

        if (!document.fullscreenElement) {
            wrapper.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }

    async updateViewerCount() {
        try {
            const response = await fetch(`/api/tournaments/${this.tournamentSlug}/stream/viewers/`);
            const data = await response.json();
            
            if (data.viewers) {
                document.querySelector('.stream-viewers').textContent = 
                    `${data.viewers.toLocaleString()} watching`;
            }
        } catch (error) {
            console.error('Failed to update viewer count:', error);
        }
    }

    // ========================================================================
    // TOURNAMENT CHAT
    // ========================================================================
    initChat() {
        const toggleBtn = document.querySelector('.chat-toggle-btn');
        const chatContainer = document.querySelector('.chat-container');
        
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                chatContainer.classList.toggle('active');
                if (chatContainer.classList.contains('active')) {
                    this.connectChatWebSocket();
                }
            });
        }

        // Send message
        const sendBtn = document.querySelector('.chat-send-btn');
        const input = document.querySelector('.chat-input');
        
        if (sendBtn && input) {
            sendBtn.addEventListener('click', () => this.sendMessage());
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
    }

    connectChatWebSocket() {
        if (this.chatWs) return; // Already connected

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/tournament/${this.tournamentSlug}/chat/`;
        
        this.chatWs = new WebSocket(wsUrl);
        
        this.chatWs.onopen = () => {
            dcLog('Chat connected');
            this.loadChatHistory();
        };
        
        this.chatWs.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleChatMessage(data);
        };
        
        this.chatWs.onerror = (error) => {
            console.error('Chat error:', error);
        };
        
        this.chatWs.onclose = () => {
            dcLog('Chat disconnected');
            this.chatWs = null;
            // Attempt reconnect after 5 seconds
            setTimeout(() => this.connectChatWebSocket(), 5000);
        };
    }

    async loadChatHistory() {
        try {
            const response = await fetch(`/api/tournaments/${this.tournamentSlug}/chat/history/`);
            const data = await response.json();
            
            const messagesContainer = document.querySelector('.chat-messages');
            messagesContainer.innerHTML = '';
            
            data.messages.forEach(msg => this.appendMessage(msg));
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } catch (error) {
            console.error('Failed to load chat history:', error);
        }
    }

    handleChatMessage(data) {
        if (data.type === 'chat_message') {
            this.appendMessage(data.message);
            
            // Update unread badge if chat is closed
            const chatContainer = document.querySelector('.chat-container');
            if (!chatContainer.classList.contains('active')) {
                this.incrementUnreadBadge();
            }
        } else if (data.type === 'user_count') {
            document.querySelector('.chat-online-count').textContent = 
                `${data.count} online`;
        }
    }

    appendMessage(message) {
        const messagesContainer = document.querySelector('.chat-messages');
        if (!messagesContainer) return;

        const messageEl = document.createElement('div');
        messageEl.className = 'chat-message';
        messageEl.innerHTML = `
            ${message.avatar ? 
                `<img src="${message.avatar}" alt="${message.username}" class="chat-avatar">` :
                `<div class="chat-avatar"></div>`
            }
            <div class="chat-message-content">
                <div class="chat-message-header">
                    <span class="chat-username">${message.username}</span>
                    ${message.team ? 
                        `<span class="chat-team-badge">${message.team}</span>` : ''
                    }
                    <span class="chat-timestamp">${this.formatTime(message.timestamp)}</span>
                </div>
                <div class="chat-message-text">${this.escapeHtml(message.text)}</div>
            </div>
        `;
        
        messagesContainer.appendChild(messageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    sendMessage() {
        const input = document.querySelector('.chat-input');
        const text = input.value.trim();
        
        if (!text || !this.chatWs) return;
        
        this.chatWs.send(JSON.stringify({
            type: 'chat_message',
            message: text
        }));
        
        input.value = '';
    }

    incrementUnreadBadge() {
        const badge = document.querySelector('.badge-unread');
        if (badge) {
            const current = parseInt(badge.textContent) || 0;
            badge.textContent = current + 1;
            badge.style.display = 'flex';
        }
    }

    // ========================================================================
    // MATCH PREDICTIONS
    // ========================================================================
    initMatchPredictions() {
        const predictionBtns = document.querySelectorAll('.predict-btn');
        
        predictionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const matchId = btn.dataset.matchId;
                const teamId = btn.dataset.teamId;
                this.submitPrediction(matchId, teamId);
            });
        });

        // Load current predictions
        this.loadPredictions();
    }

    async submitPrediction(matchId, teamId) {
        try {
            const response = await fetch(`/api/tournaments/match/${matchId}/predict/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify({ team_id: teamId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Prediction submitted!', 'success');
                this.updatePredictionDisplay(matchId, data.percentages);
            } else {
                this.showToast(data.error || 'Failed to submit prediction', 'error');
            }
        } catch (error) {
            console.error('Prediction failed:', error);
            this.showToast('Failed to submit prediction', 'error');
        }
    }

    async loadPredictions() {
        try {
            const response = await fetch(`/api/tournaments/${this.tournamentSlug}/predictions/`);
            const data = await response.json();
            
            data.predictions.forEach(pred => {
                this.updatePredictionDisplay(pred.match_id, pred.percentages);
            });
        } catch (error) {
            console.error('Failed to load predictions:', error);
        }
    }

    updatePredictionDisplay(matchId, percentages) {
        const predictionBar = document.querySelector(`[data-match-id="${matchId}"] .prediction-bar`);
        if (predictionBar) {
            predictionBar.style.width = `${percentages.teamA}%`;
            document.querySelector(`[data-match-id="${matchId}"] .prediction-percent-a`).textContent = 
                `${percentages.teamA}%`;
            document.querySelector(`[data-match-id="${matchId}"] .prediction-percent-b`).textContent = 
                `${percentages.teamB}%`;
        }
    }

    // ========================================================================
    // UTILITIES
    // ========================================================================
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
        return date.toLocaleDateString();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showToast(message, type = 'info') {
        // Reuse from tournament-features.js or create new
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 100px;
            right: 24px;
            padding: 16px 24px;
            background: ${type === 'success' ? 'rgba(0, 255, 136, 0.15)' : 'rgba(255, 70, 85, 0.15)'};
            border: 1px solid ${type === 'success' ? '#00ff88' : '#ff4655'};
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
        window.tournamentAdvancedFeatures = new TournamentAdvancedFeatures(tournamentSlug);
    }
});
