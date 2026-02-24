/**
 * Tournament Organizer Hub - Tab Management
 */

(function() {
    'use strict';

    function initTabs() {
        const tabButtons = document.querySelectorAll('.tab-button');
        const tabPanes = document.querySelectorAll('.tab-pane');

        if (!tabButtons.length || !tabPanes.length) return;

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetTab = button.getAttribute('data-tab');
                
                // Remove active from all buttons
                tabButtons.forEach(btn => btn.classList.remove('active'));
                
                // Add active to clicked button
                button.classList.add('active');
                
                // Hide all panes
                tabPanes.forEach(pane => pane.classList.remove('active'));
                
                // Show target pane
                const targetPane = document.getElementById(`${targetTab}-tab`);
                if (targetPane) {
                    targetPane.classList.add('active');
                }
            });
        });

        dcLog('✅ Organizer Hub tabs initialized');
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTabs);
    } else {
        initTabs();
    }
})();
