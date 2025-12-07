/**
 * Admin Ranking Controls for Team Admin Change Form
 * Provides inline ranking adjustment functionality
 */

(function() {
    'use strict';

    /**
     * Get CSRF token from Django cookie
     */
    function getCsrfToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookieValue ? cookieValue.split('=')[1] : '';
    }

    /**
     * Show temporary message to user
     */
    function showMessage(message, type = 'success') {
        const messagesDiv = document.getElementById('adjustment-messages');
        if (!messagesDiv) {
            console.warn('Messages container not found');
            return;
        }

        const messageClass = type === 'success' ? 'success-message' : 'error-message';
        messagesDiv.innerHTML = `<div class="${messageClass}">${message}</div>`;

        // Auto-hide after 5 seconds
        setTimeout(() => {
            messagesDiv.innerHTML = '';
        }, 5000);
    }

    /**
     * Update points display on page
     */
    function updatePointsDisplay(newPoints) {
        const pointsElement = document.getElementById('current-points');
        if (pointsElement) {
            pointsElement.textContent = newPoints;
        }
    }

    /**
     * Show points preview before applying
     */
    function showPreview(adjustment, reason) {
        const currentPoints = parseInt(document.getElementById('current-points')?.textContent || '0');
        const newPoints = currentPoints + adjustment;
        const previewDiv = document.getElementById('points-preview');
        const previewText = document.getElementById('preview-text');

        if (!previewDiv || !previewText) {
            console.warn('Preview elements not found');
            return;
        }

        previewText.innerHTML = `${currentPoints} ${adjustment >= 0 ? '+' : ''}${adjustment} = <strong>${newPoints}</strong> (${reason})`;
        previewDiv.style.display = 'block';

        // Auto-hide preview after 3 seconds
        setTimeout(() => {
            previewDiv.style.display = 'none';
        }, 3000);
    }

    /**
     * Adjust team points via AJAX
     * @param {number} adjustment - Points to add/subtract
     * @param {string} reason - Reason for adjustment
     */
    window.adjustPoints = function(adjustment, reason) {
        // Extract team ID from URL (e.g., /admin/teams/team/123/change/)
        const urlParts = window.location.pathname.split('/');
        const teamId = urlParts[urlParts.indexOf('team') + 1];

        if (!teamId || isNaN(teamId)) {
            showMessage('Unable to determine team ID', 'error');
            return;
        }

        showPreview(adjustment, reason);

        // Confirm adjustment
        if (!confirm(`Adjust points by ${adjustment >= 0 ? '+' : ''}${adjustment}?\n\nReason: ${reason}`)) {
            return;
        }

        // Send AJAX request
        fetch(`/admin/teams/team/${teamId}/adjust-points/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({
                points_adjustment: adjustment,
                reason: reason
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updatePointsDisplay(data.new_total);
                showMessage(`Successfully adjusted points by ${adjustment >= 0 ? '+' : ''}${adjustment}. New total: ${data.new_total}`);

                // Refresh the page after 2 seconds to show updated breakdown
                setTimeout(() => {
                    location.reload();
                }, 2000);
            } else {
                showMessage(data.error || 'Failed to adjust points', 'error');
            }
        })
        .catch(error => {
            showMessage('Error communicating with server', 'error');
            console.error('Error:', error);
        });
    };

    /**
     * Adjust custom points with user-provided value
     */
    window.adjustCustomPoints = function() {
        const pointsInput = document.getElementById('custom-points');
        const reasonInput = document.getElementById('custom-reason');

        if (!pointsInput || !reasonInput) {
            showMessage('Custom input fields not found', 'error');
            return;
        }

        const adjustment = parseInt(pointsInput.value);
        const reason = reasonInput.value.trim();

        if (isNaN(adjustment) || adjustment === 0) {
            showMessage('Please enter a valid point adjustment (not zero)', 'error');
            return;
        }

        if (!reason) {
            showMessage('Please provide a reason for the adjustment', 'error');
            return;
        }

        adjustPoints(adjustment, reason);

        // Clear inputs
        pointsInput.value = '';
        reasonInput.value = '';
    };

    /**
     * Recalculate all points for team
     */
    window.recalculatePoints = function() {
        // Extract team ID from URL
        const urlParts = window.location.pathname.split('/');
        const teamId = urlParts[urlParts.indexOf('team') + 1];

        if (!teamId || isNaN(teamId)) {
            showMessage('Unable to determine team ID', 'error');
            return;
        }

        if (!confirm('Recalculate all points for this team? This will update points based on current criteria.')) {
            return;
        }

        fetch(`/admin/teams/team/${teamId}/recalculate-points/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updatePointsDisplay(data.new_total);
                showMessage(`Points recalculated! Change: ${data.points_change >= 0 ? '+' : ''}${data.points_change}. New total: ${data.new_total}`);

                // Refresh the page after 2 seconds
                setTimeout(() => {
                    location.reload();
                }, 2000);
            } else {
                showMessage(data.error || 'Failed to recalculate points', 'error');
            }
        })
        .catch(error => {
            showMessage('Error communicating with server', 'error');
            console.error('Error:', error);
        });
    };

    // Log that script has loaded
    console.log('Admin ranking controls initialized');

})();
