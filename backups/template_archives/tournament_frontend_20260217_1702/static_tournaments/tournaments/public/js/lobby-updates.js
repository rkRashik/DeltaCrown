/**
 * Tournament Lobby Real-Time Updates
 * 
 * Sprint 5: HTMX polling configuration and lobby interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check-in status polling (only if not checked in and window is open)
    const checkinWidget = document.getElementById('checkin-widget');
    if (checkinWidget && !checkinWidget.classList.contains('checked-in')) {
        // HTMX polling configured in template (every 10s)
        dcLog('[Lobby] Check-in status polling active');
    }
    
    // Roster polling (every 30s)
    const rosterWidget = document.getElementById('roster-widget');
    if (rosterWidget) {
        // HTMX polling configured in template (every 30s)
        dcLog('[Lobby] Roster polling active');
    }
    
    // Handle check-in button click
    document.addEventListener('htmx:beforeRequest', function(event) {
        if (event.detail.target.id === 'checkin-widget') {
            dcLog('[Lobby] Check-in request initiated');
        }
    });
    
    // Handle check-in success
    document.addEventListener('htmx:afterSwap', function(event) {
        if (event.detail.target.id === 'checkin-widget') {
            dcLog('[Lobby] Check-in widget updated');
            
            // Stop polling if checked in (check for success indicator)
            const newWidget = document.getElementById('checkin-widget');
            if (newWidget && newWidget.classList.contains('checked-in')) {
                dcLog('[Lobby] Check-in complete, stopping status polling');
            }
        }
    });
    
    // Handle roster filter
    window.filterRoster = function(searchTerm) {
        const items = document.querySelectorAll('.roster-item');
        const term = searchTerm.toLowerCase();
        
        items.forEach(item => {
            const name = item.getAttribute('data-name');
            if (name.includes(term)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    };
    
    // Accessibility: Announce roster updates to screen readers
    document.addEventListener('htmx:afterSwap', function(event) {
        if (event.detail.target.id === 'roster-widget') {
            const announcement = document.createElement('div');
            announcement.setAttribute('role', 'status');
            announcement.setAttribute('aria-live', 'polite');
            announcement.className = 'sr-only';
            announcement.textContent = 'Participant roster updated';
            document.body.appendChild(announcement);
            
            setTimeout(() => {
                document.body.removeChild(announcement);
            }, 1000);
        }
    });
});
