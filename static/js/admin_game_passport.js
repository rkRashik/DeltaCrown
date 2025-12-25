/**
 * Game Passport Admin Dynamic Form (GP-2D: Schema-Driven Smart Fields)
 * 
 * Features:
 * - Dynamic field labels based on selected game (schema-driven, not hardcoded)
 * - Hide/show discriminator and platform fields per game
 * - Region dropdown populated server-side from schema
 * - Real-time identity_key preview
 * - Form validation hints
 * - NO ROLE (moved to Team context per GP-2D)
 * 
 * This is UX-only - server-side validation remains authoritative.
 * Schema matrix is injected via #gp-schema-matrix element (see change_form.html).
 */

(function($) {
    'use strict';

    // Schema matrix loaded from template (GP-2D: no hardcoded games)
    let schemaMatrix = {};
    let currentGameSlug = null;

    /**
     * Load schema matrix from template-injected JSON
     * GP-2D: Schema comes from server, not hardcoded in JS
     */
    function loadSchemaMatrix() {
        const schemaElement = document.getElementById('gp-schema-matrix');
        if (schemaElement) {
            try {
                schemaMatrix = JSON.parse(schemaElement.textContent);
                console.log('[GP-2D Admin] Schema matrix loaded:', Object.keys(schemaMatrix).length, 'games');
            } catch (e) {
                console.error('[GP-2D Admin] Failed to parse schema matrix:', e);
            }
        } else {
            console.warn('[GP-2D Admin] Schema matrix element not found - form will use default labels');
        }
    }

    /**
     * Get field configuration from schema matrix (GP-2D: schema-driven)
     */
    function getFieldConfig(gameSlug) {
        const schema = schemaMatrix[gameSlug];
        if (!schema) {
            return {
                ign_label: 'IGN / Username',
                ign_help: 'In-game name or username',
                discriminator_visible: true,
                discriminator_label: 'Tag / Zone',
                discriminator_help: 'Tag, zone, or discriminator (if applicable)',
                platform_visible: false,
                platform_label: 'Platform',
                platform_help: 'Platform identifier',
            };
        }
        
        // Parse identity_fields from schema to determine labels
        const identityFields = schema.identity_fields || {};
        const config = {
            ign_label: 'IGN / Username',
            ign_help: 'In-game name or username',
            discriminator_visible: false,
            discriminator_label: 'Discriminator',
            discriminator_help: '',
            platform_visible: schema.platform_specific || false,
            platform_label: 'Platform',
            platform_help: schema.platform_specific ? 'Select your platform' : '',
        };
        
        // Map identity fields to UI fields (schema uses field names, we need UI labels)
        if (identityFields.riot_name) {
            config.ign_label = 'Riot ID';
            config.ign_help = identityFields.riot_name.help_text || 'Your Riot ID name';
        }
        if (identityFields.tagline) {
            config.discriminator_visible = true;
            config.discriminator_label = 'Tagline';
            config.discriminator_help = identityFields.tagline.help_text || 'Tagline without #';
        }
        if (identityFields.steam_id64) {
            config.ign_label = 'Steam ID64';
            config.ign_help = '17-digit Steam ID';
        }
        if (identityFields.numeric_id) {
            config.ign_label = 'Player ID';
            config.ign_help = identityFields.numeric_id.help_text || 'Numeric player ID';
        }
        if (identityFields.zone_id) {
            config.discriminator_visible = true;
            config.discriminator_label = 'Zone ID';
            config.discriminator_help = identityFields.zone_id.help_text || 'Server zone ID';
        }
        
        return config;
    }

    /**
     * Update field labels and visibility based on selected game (GP-2D: schema-driven)
     */
    function updateFieldLabelsAndVisibility(gameSlug) {
        if (!gameSlug) {
            return;
        }

        currentGameSlug = gameSlug;
        const config = getFieldConfig(gameSlug);

        // Update IGN field
        const ignField = $('.field-ign');
        const ignLabel = ignField.find('label');
        const ignInput = ignField.find('input');
        const ignHelp = ignField.find('.help');

        if (ignLabel.length) {
            ignLabel.text(config.ign_label + ':');
        }
        if (ignInput.length) {
            ignInput.attr('placeholder', config.ign_help);
        }
        if (ignHelp.length) {
            ignHelp.text(config.ign_help);
        } else {
            ignInput.after(`<div class="help">${config.ign_help}</div>`);
        }

        // Update discriminator field visibility
        const discriminatorField = $('.field-discriminator');
        if (config.discriminator_visible) {
            discriminatorField.show().removeClass('gp-hidden-field');
            const discLabel = discriminatorField.find('label');
            const discInput = discriminatorField.find('input');
            const discHelp = discriminatorField.find('.help');

            if (discLabel.length) {
                discLabel.text(config.discriminator_label + ':');
            }
            if (discInput.length) {
                discInput.attr('placeholder', config.discriminator_help);
            }
            if (discHelp.length) {
                discHelp.text(config.discriminator_help);
            } else if (config.discriminator_help) {
                discInput.after(`<div class="help">${config.discriminator_help}</div>`);
            }
        } else {
            discriminatorField.hide().addClass('gp-hidden-field');
        }

        // Update platform field visibility
        const platformField = $('.field-platform');
        if (config.platform_visible) {
            platformField.show().removeClass('gp-hidden-field');
            const platformLabel = platformField.find('label');
            const platformHelp = platformField.find('.help');
            if (platformLabel.length) {
                platformLabel.text(config.platform_label + ':');
            }
            if (platformHelp.length) {
                platformHelp.text(config.platform_help);
            } else if (config.platform_help) {
                platformField.find('input').after(`<div class="help">${config.platform_help}</div>`);
            }
        } else {
            platformField.hide().addClass('gp-hidden-field');
        }

        // Update region field - mark as required if needed (GP-2D: dropdown handled server-side)
        const schema = schemaMatrix[gameSlug];
        if (schema && schema.region_required) {
            $('.field-region').addClass('gp-required-field');
        } else {
            $('.field-region').removeClass('gp-required-field');
        }

        // Update identity preview
        updateIdentityPreview();
    }

    /**
     * Update identity preview (display what identity_key will be)
     */
    function updateIdentityPreview() {
        const ign = $('#id_ign').val() || '';
        const discriminator = $('#id_discriminator').val() || '';
        const platform = $('#id_platform').val() || '';
        const region = $('#id_region').val() || '';

        if (!ign) {
            return; // No preview without IGN
        }

        let preview = ign.toLowerCase();
        if (discriminator) {
            // Check if it's a Riot game or MLBB
            if (currentGameSlug && ['valorant', 'lol', 'tft'].includes(currentGameSlug)) {
                preview += '#' + discriminator.toLowerCase();
            } else if (currentGameSlug === 'mlbb') {
                preview += '_' + discriminator;
            } else {
                preview += '#' + discriminator.toLowerCase();
            }
        }
        if (platform) {
            preview += ':' + platform.toLowerCase();
        }

        // Update or create preview box
        let previewBox = $('#gp-identity-preview');
        if (previewBox.length === 0) {
            $('.field-identity_key').before(`
                <div id="gp-identity-preview">
                    <span class="label">Identity Key Preview:</span>
                    <span class="value"></span>
                </div>
            `);
            previewBox = $('#gp-identity-preview');
        }

        previewBox.find('.value').text(preview);
    }

    /**
     * Initialize form behavior
     */
    function initializeForm() {
        // Load schema matrix from template
        loadSchemaMatrix();

        // Get current game selection
        const gameSelect = $('#id_game');
        if (gameSelect.length === 0) {
            return;
        }

        // Apply initial configuration if game is already selected
        const selectedGameSlug = gameSelect.find('option:selected').data('slug');
        if (selectedGameSlug) {
            updateFieldLabelsAndVisibility(selectedGameSlug);
        }

        // Listen to game selection changes
        gameSelect.on('change', function() {
            const selectedOption = $(this).find('option:selected');
            const gameSlug = selectedOption.data('slug') || selectedOption.text().toLowerCase().replace(/\s+/g, '-');
            updateFieldLabelsAndVisibility(gameSlug);
        });

        // Listen to identity field changes for preview
        $('#id_ign, #id_discriminator, #id_platform, #id_region').on('input change', function() {
            updateIdentityPreview();
        });

        // Initial preview update
        updateIdentityPreview();
    }

    // Initialize on DOM ready
    $(document).ready(function() {
        initializeForm();
    });

})(django.jQuery || jQuery);
