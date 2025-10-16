/**
 * USER PROFILE DASHBOARD INTERACTIONS
 * Professional JavaScript for profile page animations and interactions
 * Extracted from inline code for better maintainability
 */

document.addEventListener('DOMContentLoaded', function() {
    // Add smooth hover animations to cards
    document.querySelectorAll('.team-card, .dashboard-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Add click effects to buttons
    document.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
});