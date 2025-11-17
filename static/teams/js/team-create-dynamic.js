# Team Create Dynamic Game Fields - JavaScript Implementation

This file provides the JavaScript functionality for team creation dynamic fields.
Place this in: static/teams/js/team-create-dynamic.js

"""
// Team Create - Dynamic Game Fields Handler
(function() {
    'use strict';
    
    // Game configurations (injected from backend)
    const gameConfigs = window.GAME_CONFIGS || {};
    
    // Initialize when page loads
    document.addEventListener('DOMContentLoaded', function() {
        const gameSelect = document.getElementById('id_game');
        const gameIdSection = document.getElementById('game-id-section');
        const gameIdFields = document.getElementById('game-id-fields');
        const existingTeamWarning = document.getElementById('existing-team-warning');
        
        if (!gameSelect || !gameIdSection || !gameIdFields) {
            console.error('Required elements not found');
            return;
        }
        
        // Handle game selection change
        gameSelect.addEventListener('change', function() {
            const selectedGame = this.value;
            
            if (!selectedGame) {
                gameIdSection.style.display = 'none';
                existingTeamWarning.style.display = 'none';
                return;
            }
            
            // Check if user already has team for this game
            checkExistingTeam(selectedGame);
            
            // Show game ID fields
            const config = gameConfigs[selectedGame];
            if (config && config.id_fields) {
                renderGameIdFields(config);
                gameIdSection.style.display = 'block';
            } else {
                gameIdSection.style.display = 'none';
            }
        });
    });
    
    function renderGameIdFields(config) {
        const container = document.getElementById('game-id-fields');
        container.innerHTML = '';
        
        config.id_fields.forEach(field => {
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'form-group';
            
            const label = document.createElement('label');
            label.className = 'form-label';
            label.textContent = field.label;
            if (field.required) {
                const required = document.createElement('span');
                required.className = 'required';
                required.textContent = ' *';
                label.appendChild(required);
            }
            
            const input = document.createElement('input');
            input.type = 'text';
            input.name = `game_id_${field.key}`;
            input.id = `id_game_id_${field.key}`;
            input.className = 'form-control';
            input.placeholder = field.placeholder || '';
            if (field.required) input.required = true;
            
            if (field.help_text) {
                const helpText = document.createElement('small');
                helpText.className = 'form-text';
                helpText.textContent = field.help_text;
                fieldDiv.appendChild(helpText);
            }
            
            fieldDiv.appendChild(label);
            fieldDiv.appendChild(input);
            container.appendChild(fieldDiv);
        });
    }
    
    function checkExistingTeam(gameCode) {
        fetch(`/teams/api/check-existing-team/?game=${gameCode}`)
            .then(response => response.json())
            .then(data => {
                const warning = document.getElementById('existing-team-warning');
                const info = document.getElementById('existing-team-info');
                
                if (data.has_team) {
                    info.innerHTML = `
                        <strong>${data.team_name}</strong> (${data.team_tag})
                        <br>
                        <a href="/teams/${data.team_slug}/" class="btn btn-sm btn-primary mt-2">
                            View Your Team
                        </a>
                    `;
                    warning.style.display = 'block';
                } else {
                    warning.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error checking existing team:', error);
            });
    }
})();
"""

# To implement, add this to your team_create.html template:
# <script src="{% static 'teams/js/team-create-dynamic.js' %}"></script>
# And ensure GAME_CONFIGS is injected via context
