/**
 * GP-2A/2B: Game Passport Admin Dynamic Fields
 * 
 * This script makes identity fields (ign, discriminator, platform, region) 
 * dynamically change labels and visibility based on selected game.
 * 
 * Schema Config Mapping:
 * - Valorant/LoL/TFT: IGN="Riot ID Name", Discriminator="Tag Line"
 * - MLBB: IGN="Numeric ID", Discriminator="Zone ID"
 * - CS2/Dota2: IGN="Steam ID64", hide discriminator/platform
 * - EA FC/eFootball/R6: Show platform field
 * - Generic: IGN="Player ID / Username"
 */

(function() {
    'use strict';
    
    // Game-specific field configurations
    const GAME_CONFIGS = {
        'valorant': {
            ign: { label: 'Riot ID Name', required: true, hidden: false, help: 'Your Riot ID without the # tag (e.g., "Player123")' },
            discriminator: { label: 'Tag Line', required: true, hidden: false, help: 'Your Riot tag without the # (e.g., "NA1")' },
            platform: { hidden: true },
            region: { hidden: false }
        },
        'lol': {
            ign: { label: 'Riot ID Name', required: true, hidden: false, help: 'Your Riot ID without the # tag' },
            discriminator: { label: 'Tag Line', required: true, hidden: false, help: 'Your Riot tag without the #' },
            platform: { hidden: true },
            region: { hidden: false }
        },
        'tft': {
            ign: { label: 'Riot ID Name', required: true, hidden: false, help: 'Your Riot ID without the # tag' },
            discriminator: { label: 'Tag Line', required: true, hidden: false, help: 'Your Riot tag without the #' },
            platform: { hidden: true },
            region: { hidden: false }
        },
        'mlbb': {
            ign: { label: 'Numeric ID', required: true, hidden: false, help: 'Your Mobile Legends numeric user ID' },
            discriminator: { label: 'Zone ID', required: true, hidden: false, help: 'Your server/zone identifier' },
            platform: { hidden: true },
            region: { hidden: false }
        },
        'cs2': {
            ign: { label: 'Steam ID64', required: true, hidden: false, help: 'Your 17-digit Steam ID64 (e.g., "76561198012345678")' },
            discriminator: { hidden: true },
            platform: { hidden: true },
            region: { hidden: false }
        },
        'dota2': {
            ign: { label: 'Steam ID64', required: true, hidden: false, help: 'Your 17-digit Steam ID64' },
            discriminator: { hidden: true },
            platform: { hidden: true },
            region: { hidden: false }
        },
        'eafc': {
            ign: { label: 'EA ID', required: true, hidden: false, help: 'Your EA account ID or username' },
            discriminator: { hidden: true },
            platform: { label: 'Platform', required: true, hidden: false, help: 'Your gaming platform (PC, PS5, Xbox, etc.)' },
            region: { hidden: false }
        },
        'efootball': {
            ign: { label: 'Konami ID', required: true, hidden: false, help: 'Your Konami account ID' },
            discriminator: { hidden: true },
            platform: { label: 'Platform', required: true, hidden: false, help: 'Your gaming platform' },
            region: { hidden: false }
        },
        'r6': {
            ign: { label: 'Ubisoft Username', required: true, hidden: false, help: 'Your Ubisoft Connect username' },
            discriminator: { hidden: true },
            platform: { label: 'Platform', required: false, hidden: false, help: 'Your gaming platform (PC, PS5, Xbox)' },
            region: { hidden: false }
        },
        'fortnite': {
            ign: { label: 'Epic ID', required: true, hidden: false, help: 'Your Epic Games account ID or display name' },
            discriminator: { hidden: true },
            platform: { hidden: true },
            region: { hidden: false }
        },
        'rocketleague': {
            ign: { label: 'Epic ID', required: true, hidden: false, help: 'Your Epic Games account ID' },
            discriminator: { hidden: true },
            platform: { hidden: true },
            region: { hidden: false }
        }
    };
    
    // Default config for unknown games
    const DEFAULT_CONFIG = {
        ign: { label: 'IGN / Username', required: true, hidden: false, help: 'Your in-game name or player ID' },
        discriminator: { label: 'Discriminator / Tag', required: false, hidden: false, help: 'Optional discriminator or tag (if applicable)' },
        platform: { label: 'Platform', required: false, hidden: false, help: 'Your gaming platform (if applicable)' },
        region: { label: 'Region', required: false, hidden: false, help: 'Your player region' }
    };
    
    /**
     * Update field labels and visibility based on selected game
     */
    function updateFieldsForGame(gameSlug) {
        const config = GAME_CONFIGS[gameSlug] || DEFAULT_CONFIG;
        
        // Update IGN field
        updateField('id_ign', config.ign);
        
        // Update Discriminator field
        updateField('id_discriminator', config.discriminator);
        
        // Update Platform field
        updateField('id_platform', config.platform);
        
        // Update Region field (usually always visible)
        updateField('id_region', config.region);
    }
    
    /**
     * Update a single field's label, required status, visibility, and help text
     */
    function updateField(fieldId, fieldConfig) {
        const fieldInput = document.getElementById(fieldId);
        if (!fieldInput) return;
        
        // Get field row (parent container)
        const fieldRow = fieldInput.closest('.form-row') || fieldInput.closest('div.field-' + fieldId.replace('id_', ''));
        
        if (!fieldRow) return;
        
        // Update visibility
        if (fieldConfig.hidden) {
            fieldRow.style.display = 'none';
            fieldInput.required = false;
        } else {
            fieldRow.style.display = '';
            fieldInput.required = fieldConfig.required || false;
        }
        
        // Update label
        if (fieldConfig.label) {
            const label = fieldRow.querySelector('label');
            if (label) {
                // Preserve required asterisk if needed
                const requiredAsterisk = fieldConfig.required ? '<span class="required">*</span>' : '';
                label.innerHTML = fieldConfig.label + ':' + requiredAsterisk;
            }
        }
        
        // Update help text
        if (fieldConfig.help) {
            let helpText = fieldRow.querySelector('.help, .helptext');
            if (!helpText) {
                helpText = document.createElement('div');
                helpText.className = 'help';
                fieldInput.parentNode.appendChild(helpText);
            }
            helpText.textContent = fieldConfig.help;
        }
    }
    
    /**
     * Initialize on page load
     */
    function init() {
        const gameField = document.getElementById('id_game');
        if (!gameField) return;
        
        // Get game slug from selected option
        function getSelectedGameSlug() {
            const selectedOption = gameField.options[gameField.selectedIndex];
            if (!selectedOption || !selectedOption.value) return null;
            
            // Get game slug from data attribute or option text
            // Assumes option has data-slug attribute or we extract from value
            return selectedOption.getAttribute('data-slug') || selectedOption.text.toLowerCase().replace(/\s+/g, '');
        }
        
        // Apply initial config if game already selected
        const initialSlug = getSelectedGameSlug();
        if (initialSlug) {
            updateFieldsForGame(initialSlug);
        }
        
        // Listen for game changes
        gameField.addEventListener('change', function() {
            const gameSlug = getSelectedGameSlug();
            if (gameSlug) {
                updateFieldsForGame(gameSlug);
            }
        });
    }
    
    // Run init when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
