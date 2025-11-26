/**
 * Tournament Admin Dynamic Field Visibility
 * Shows/hides game-specific configuration inlines based on selected game
 */

(function($, django) {
    'use strict';

    // Defensive check - ensure django.jQuery and django are available
    if (typeof django === 'undefined' || typeof django.jQuery === 'undefined') {
        console.warn('Django admin JavaScript not loaded. Tournament admin enhancements disabled.');
        return;
    }

    $(document).ready(function() {
        // Game-specific inline selectors
        const GAME_INLINES = {
            'valorant': [
                '.inline-group:has(h2:contains("Valorant Configuration"))',
                '.inline-group h2:contains("Valorant Configuration")'
            ],
            'efootball': [
                '.inline-group:has(h2:contains("eFootball Configuration"))',
                '.inline-group h2:contains("eFootball Configuration")'
            ]
        };
        
        // Get game field
        const $gameField = $('#id_game');
        
        if ($gameField.length) {
            // Function to toggle game-specific inlines
            function updateGameInlines() {
                const selectedGame = $gameField.val();
                
                // Hide all game-specific inlines first
                $('.inline-group').each(function() {
                    const $inline = $(this);
                    const headerText = $inline.find('h2').text();
                    
                    if (headerText.includes('Valorant Configuration')) {
                        $inline.toggle(selectedGame === 'valorant');
                    } else if (headerText.includes('eFootball Configuration')) {
                        $inline.toggle(selectedGame === 'efootball');
                    }
                });
                
                // Show appropriate inline
                if (selectedGame) {
                    dcLog('Selected game:', selectedGame);
                }
            }
            
            // Initial update
            updateGameInlines();
            
            // Update on change
            $gameField.on('change', updateGameInlines);
        }
        
        // Toggle deprecated fields visibility
        const $deprecatedSection = $('.field-slot_size, .field-reg_open_at, .field-reg_close_at, ' +
                                     '.field-start_at, .field-end_at, .field-entry_fee_bdt, ' +
                                     '.field-prize_pool_bdt').closest('.form-row');
        
        if ($deprecatedSection.length) {
            // Add warning style to deprecated fields
            $deprecatedSection.css({
                'background': '#fff3cd',
                'border-left': '4px solid #ffc107',
                'padding': '10px',
                'margin': '10px 0'
            });
            
            // Add warning icon to field labels
            $deprecatedSection.find('label').prepend('⚠️ ');
        }
        
        // Add helper tooltips
        function addTooltip(selector, text) {
            $(selector).attr('title', text).css('cursor', 'help');
        }
        
        addTooltip('#id_tournament_type', 'Solo: Individual players | Team: Fixed teams | Mixed: Both allowed');
        addTooltip('#id_format', 'Tournament bracket structure and format');
        addTooltip('#id_platform', 'Online: Internet-based | Offline: LAN event | Hybrid: Both');
        
        // Status badge styling in admin
        $('.field-status select').on('change', function() {
            const status = $(this).val();
            const colors = {
                'DRAFT': '#6c757d',
                'PUBLISHED': '#0d6efd',
                'RUNNING': '#198754',
                'COMPLETED': '#dc3545'
            };
            
            $(this).css({
                'background': colors[status] || '#fff',
                'color': status && status !== 'DRAFT' ? '#fff' : '#000',
                'font-weight': 'bold',
                'padding': '5px 10px',
                'border-radius': '4px'
            });
        }).trigger('change');
        
        // Archive warning for COMPLETED status
        $('#id_status').on('change', function() {
            const $warning = $('#archive-warning');
            
            if ($(this).val() === 'COMPLETED') {
                if (!$warning.length) {
                    $(this).after(
                        '<div id="archive-warning" style="margin-top: 10px; padding: 10px; ' +
                        'background: #f8d7da; border: 1px solid #dc3545; border-radius: 4px; color: #721c24;">' +
                        '<strong>⚠️ Warning:</strong> Setting status to COMPLETED will archive this tournament. ' +
                        'All fields will become read-only and the tournament cannot be deleted. ' +
                        'This action should only be taken when the tournament is fully finished.' +
                        '</div>'
                    );
                }
            } else {
                $warning.remove();
            }
        });
        
        // Validate date fields
        function validateDates() {
            const regOpen = new Date($('#id_tournamentschedule-0-reg_open_at').val());
            const regClose = new Date($('#id_tournamentschedule-0-reg_close_at').val());
            const start = new Date($('#id_tournamentschedule-0-start_at').val());
            const end = new Date($('#id_tournamentschedule-0-end_at').val());
            
            // Clear previous errors
            $('.date-validation-error').remove();
            
            // Validate registration window
            if (regOpen && regClose && regOpen >= regClose) {
                $('#id_tournamentschedule-0-reg_close_at').after(
                    '<p class="date-validation-error" style="color: #dc3545; font-size: 12px;">' +
                    '⚠️ Registration close must be after open time' +
                    '</p>'
                );
            }
            
            // Validate tournament window
            if (start && end && start >= end) {
                $('#id_tournamentschedule-0-end_at').after(
                    '<p class="date-validation-error" style="color: #dc3545; font-size: 12px;">' +
                    '⚠️ Tournament end must be after start time' +
                    '</p>'
                );
            }
            
            // Validate registration closes before tournament starts
            if (regClose && start && regClose > start) {
                $('#id_tournamentschedule-0-reg_close_at').after(
                    '<p class="date-validation-error" style="color: #dc3545; font-size: 12px;">' +
                    '⚠️ Registration should close before tournament starts' +
                    '</p>'
                );
            }
        }
        
        // Attach date validation
        $('#id_tournamentschedule-0-reg_open_at, #id_tournamentschedule-0-reg_close_at, ' +
          '#id_tournamentschedule-0-start_at, #id_tournamentschedule-0-end_at').on('change', validateDates);
        
        // Add "Quick Fill" buttons for common configurations
        if ($('#id_tournamentcapacity-0-min_team_size').length) {
            const $teamSizeFields = $('#id_tournamentcapacity-0-min_team_size').closest('.form-row');
            
            $teamSizeFields.append(
                '<div style="margin-top: 10px;">' +
                '<strong>Quick Fill:</strong> ' +
                '<button type="button" class="quick-fill" data-min="1" data-max="1">Solo</button> ' +
                '<button type="button" class="quick-fill" data-min="5" data-max="5">Valorant (5v5)</button> ' +
                '<button type="button" class="quick-fill" data-min="1" data-max="11">eFootball</button> ' +
                '</div>'
            );
            
            $('.quick-fill').on('click', function() {
                const min = $(this).data('min');
                const max = $(this).data('max');
                $('#id_tournamentcapacity-0-min_team_size').val(min);
                $('#id_tournamentcapacity-0-max_team_size').val(max);
                $(this).css({'background': '#28a745', 'color': '#fff'});
                setTimeout(() => {
                    $(this).css({'background': '', 'color': ''});
                }, 300);
            });
        }
        
        dcLog('Tournament Admin JS loaded successfully');
    });
})(django.jQuery, django);
