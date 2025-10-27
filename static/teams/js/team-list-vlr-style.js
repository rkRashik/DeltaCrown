/**
 * VLR.gg Inspired Team List View
 * Groups teams by game with professional rankings-style layout
 */

(function() {
    'use strict';
    
    // Store original teams data
    let originalTeamsData = [];
    let currentView = 'grid';
    
    /**
     * Initialize VLR-style list view
     */
    function initVLRListView() {
        const container = document.getElementById('teams-container');
        if (!container) return;
        
        // Store original team cards data
        storeOriginalTeamsData();
        
        // Listen for view changes
        const viewButtons = document.querySelectorAll('.view-btn');
        viewButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                currentView = this.dataset.view;
                
                if (currentView === 'list') {
                    renderVLRStyleList();
                } else {
                    restoreOriginalView();
                }
            });
        });
        
        // Check if list view is already active
        if (container.classList.contains('list-view')) {
            currentView = 'list';
            renderVLRStyleList();
        }
    }
    
    /**
     * Store original team cards data
     */
    function storeOriginalTeamsData() {
        const container = document.getElementById('teams-container');
        const teamCards = container.querySelectorAll('.team-card-premium');
        
        console.log(`VLR List View: Found ${teamCards.length} team cards`);
        
        originalTeamsData = Array.from(teamCards).map(card => {
            // Extract game name from meta-badge
            const gameBadge = card.querySelector('.meta-badge.game span');
            let gameName = 'Other';
            if (gameBadge) {
                gameName = gameBadge.textContent.trim();
            }
            
            // Extract region name from meta-badge
            const regionBadge = card.querySelector('.meta-badge.region span');
            let regionName = 'Unknown';
            if (regionBadge) {
                regionName = regionBadge.textContent.trim();
            }
            
            // Get all stat values
            const statValues = card.querySelectorAll('.stat-value');
            
            const team = {
                element: card.cloneNode(true),
                id: card.dataset.teamId || '',
                rank: parseInt(card.dataset.rank) || 999,
                name: card.querySelector('.team-name')?.textContent.trim().replace(/\s+/g, ' ') || '',
                tag: card.querySelector('.team-tag-premium')?.textContent.trim().replace(/[\[\]]/g, '') || '',
                logo: card.querySelector('.logo-img')?.src || '',
                logoText: card.querySelector('.logo-placeholder')?.textContent.trim() || '',
                game: gameName,
                region: regionName,
                members: statValues[0]?.textContent.trim() || '0',
                points: statValues[1]?.textContent.trim() || '0',
                wins: statValues[2]?.textContent.trim() || '0',
                isVerified: card.querySelector('.verified-inline') !== null,
                isRecruiting: card.querySelector('.badge-recruiting') !== null || 
                             card.querySelector('.team-badge.recruiting') !== null,
                isMember: card.querySelector('.member-badge') !== null || 
                         card.querySelector('.btn-action.member-badge') !== null,
                url: card.querySelector('.btn-action.primary-action, .btn-action')?.href || '#'
            };
            
            // Debug log for first few teams
            if (originalTeamsData.length < 3) {
                console.log('VLR List View: Team data sample:', {
                    name: team.name,
                    game: team.game,
                    region: team.region
                });
            }
            
            return team;
        });
        
        console.log(`VLR List View: Stored ${originalTeamsData.length} teams`);
        
        // Log unique games found
        const uniqueGames = [...new Set(originalTeamsData.map(t => t.game))];
        console.log('VLR List View: Unique games found:', uniqueGames);
    }
    
    /**
     * Group teams by game
     */
    function groupTeamsByGame(teams) {
        const grouped = {};
        
        teams.forEach(team => {
            const game = team.game || 'Other';
            if (!grouped[game]) {
                grouped[game] = [];
            }
            grouped[game].push(team);
        });
        
        // Sort teams within each game by rank
        Object.keys(grouped).forEach(game => {
            grouped[game].sort((a, b) => a.rank - b.rank);
        });
        
        return grouped;
    }
    
    /**
     * Get game icon/logo
     */
    function getGameIcon(gameName) {
        const gameIcons = {
            'valorant': '<i class="fas fa-crosshairs"></i>',
            'efootball': '<i class="fas fa-futbol"></i>',
            'e-football': '<i class="fas fa-futbol"></i>',
            'pubg': '<i class="fas fa-crosshairs"></i>',
            'dota 2': '<i class="fas fa-dragon"></i>',
            'dota': '<i class="fas fa-dragon"></i>',
            'league of legends': '<i class="fas fa-chess-queen"></i>',
            'lol': '<i class="fas fa-chess-queen"></i>',
            'cs:go': '<i class="fas fa-bullseye"></i>',
            'cs2': '<i class="fas fa-bullseye"></i>',
            'counter-strike': '<i class="fas fa-bullseye"></i>',
            'overwatch': '<i class="fas fa-hat-wizard"></i>',
            'rocket league': '<i class="fas fa-car"></i>',
            'fortnite': '<i class="fas fa-parachute-box"></i>',
            'apex legends': '<i class="fas fa-mountain"></i>',
            'apex': '<i class="fas fa-mountain"></i>',
            'fifa': '<i class="fas fa-futbol"></i>',
            'fc': '<i class="fas fa-futbol"></i>',
            'mobile legends': '<i class="fas fa-mobile-alt"></i>',
            'ml': '<i class="fas fa-mobile-alt"></i>',
            'free fire': '<i class="fas fa-fire"></i>',
            'call of duty': '<i class="fas fa-crosshairs"></i>',
            'cod': '<i class="fas fa-crosshairs"></i>'
        };
        
        const normalizedName = gameName.toLowerCase().trim();
        return gameIcons[normalizedName] || '<i class="fas fa-gamepad"></i>';
    }
    
    /**
     * Render VLR-style list view
     */
    function renderVLRStyleList() {
        const container = document.getElementById('teams-container');
        if (!container || originalTeamsData.length === 0) {
            console.warn('VLR List View: No container or no teams data');
            return;
        }
        
        // Group teams by game
        const groupedTeams = groupTeamsByGame(originalTeamsData);
        
        // Debug: Log grouped teams
        console.log('VLR List View: Grouped teams by game:', groupedTeams);
        console.log('VLR List View: Total games:', Object.keys(groupedTeams).length);
        
        // Clear container
        container.innerHTML = '';
        
        // Sort games alphabetically
        const sortedGames = Object.keys(groupedTeams).sort();
        
        console.log('VLR List View: Rendering games:', sortedGames);
        
        // Render each game section
        sortedGames.forEach(gameName => {
            const teams = groupedTeams[gameName];
            console.log(`VLR List View: Rendering ${gameName} with ${teams.length} teams`);
            const gameSection = createGameSection(gameName, teams);
            container.appendChild(gameSection);
        });
        
        console.log('VLR List View: Rendering complete');
    }
    
    /**
     * Create a game section with teams table
     */
    function createGameSection(gameName, teams) {
        const section = document.createElement('div');
        section.className = 'game-section';
        
        // Game header
        const header = document.createElement('div');
        header.className = 'game-header';
        header.innerHTML = `
            <div class="game-header-icon">
                ${getGameIcon(gameName)}
            </div>
            <div class="game-header-title">
                <h2>${gameName}</h2>
            </div>
            <div class="game-header-count">
                ${teams.length} ${teams.length === 1 ? 'Team' : 'Teams'}
            </div>
        `;
        
        // Teams table
        const table = document.createElement('div');
        table.className = 'game-teams-table';
        
        // Team rows (no header, cleaner like VLR.gg)
        teams.forEach((team, index) => {
            const row = createTeamRow(team, index + 1);
            table.appendChild(row);
        });
        
        section.appendChild(header);
        section.appendChild(table);
        
        return section;
    }
    
    /**
     * Create a team row - clickable like VLR.gg
     */
    function createTeamRow(team, displayRank) {
        const row = document.createElement('a');
        row.className = 'team-row';
        row.href = team.url;
        
        // Add podium class for top 3
        if (displayRank <= 3) {
            row.classList.add(`podium-${displayRank}`);
        }
        
        // Rank cell
        const rankCell = document.createElement('div');
        rankCell.className = 'rank-cell';
        rankCell.textContent = displayRank;
        
        // Logo cell
        const logoCell = document.createElement('div');
        logoCell.className = 'logo-cell';
        if (team.logo) {
            logoCell.innerHTML = `<img src="${team.logo}" alt="${team.name}">`;
        } else {
            logoCell.innerHTML = `<div class="logo-placeholder">${team.logoText || team.name.charAt(0)}</div>`;
        }
        
        // Team info cell
        const infoCell = document.createElement('div');
        infoCell.className = 'team-info-cell';
        
        const nameBadges = [];
        if (team.isVerified) {
            nameBadges.push('<i class="fas fa-check-circle verified-icon"></i>');
        }
        
        const badges = [];
        if (team.isRecruiting) {
            badges.push('<span class="team-badge">Recruiting</span>');
        }
        if (team.isMember) {
            badges.push('<span class="team-badge" style="background: rgba(34, 197, 94, 0.15); border-color: rgba(34, 197, 94, 0.3); color: rgba(34, 197, 94, 1);">Member</span>');
        }
        
        const teamMetaRow = `
            <div class="team-meta-row">
                ${team.tag ? `<span class="team-tag-text">[${team.tag}]</span>` : ''}
                ${badges.length > 0 ? `<div class="team-badges">${badges.join('')}</div>` : ''}
            </div>
        `;
        
        infoCell.innerHTML = `
            <div class="team-name-row">
                <span class="team-name-text">${team.name}</span>
                ${nameBadges.join('')}
            </div>
            ${teamMetaRow}
        `;
        
        // Region cell
        const regionCell = document.createElement('div');
        regionCell.className = 'region-cell';
        regionCell.innerHTML = `
            <i class="fas fa-map-marker-alt"></i>
            <span>${team.region}</span>
        `;
        
        // Members cell
        const membersCell = document.createElement('div');
        membersCell.className = 'stat-cell';
        membersCell.innerHTML = `
            <div class="stat-value">${team.members}</div>
            <div class="stat-label">Members</div>
        `;
        
        // Wins cell
        const winsCell = document.createElement('div');
        winsCell.className = 'stat-cell';
        winsCell.innerHTML = `
            <div class="stat-value">${team.wins}</div>
            <div class="stat-label">Wins</div>
        `;
        
        // Append all cells
        row.appendChild(rankCell);
        row.appendChild(logoCell);
        row.appendChild(infoCell);
        row.appendChild(regionCell);
        row.appendChild(membersCell);
        row.appendChild(winsCell);
        
        return row;
    }
    
    /**
     * Restore original grid view
     */
    function restoreOriginalView() {
        const container = document.getElementById('teams-container');
        if (!container || originalTeamsData.length === 0) return;
        
        // Clear container
        container.innerHTML = '';
        
        // Restore original team cards
        originalTeamsData.forEach(team => {
            container.appendChild(team.element.cloneNode(true));
        });
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initVLRListView);
    } else {
        initVLRListView();
    }
    
})();
