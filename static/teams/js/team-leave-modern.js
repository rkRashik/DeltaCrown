/**
 * MODERN TEAM LEAVE SYSTEM
 * Version: 1.0 - 2025
 * 
 * Features:
 * - Beautiful confirmation modal
 * - Warning about consequences
 * - Smooth animations
 * - Alternative actions
 */

/**
 * Show leave team confirmation modal
 */
function showLeaveTeamModal(teamSlug, teamName, memberCount, isCaptain = false) {
    const modal = createLeaveModal(teamSlug, teamName, memberCount, isCaptain);
    document.body.appendChild(modal);
    
    // Animate in
    requestAnimationFrame(() => {
        modal.classList.add('active');
    });
    
    // Setup event listeners
    setupLeaveModalHandlers(modal, teamSlug);
}

/**
 * Create leave modal HTML
 */
function createLeaveModal(teamSlug, teamName, memberCount, isCaptain = false) {
    const modal = document.createElement('div');
    modal.className = 'modern-join-modal'; // Reuse join modal styles
    modal.id = 'leaveTeamModal';
    
    const willBecomeSolo = memberCount <= 2;
    
    modal.innerHTML = `
        <div class="modal-overlay" data-dismiss="modal"></div>
        <div class="modal-container">
            <div class="modal-header">
                <div class="header-icon warning">
                    <i class="fas fa-exclamation-triangle"></i>
                </div>
                <div class="header-content">
                    <h2>Leave ${escapeHtml(teamName)}?</h2>
                    <p>This action cannot be undone</p>
                </div>
                <button class="modal-close" data-dismiss="modal">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <div class="modal-body">
                ${isCaptain ? `
                <div class="info-card danger">
                    <div class="info-icon">
                        <i class="fas fa-crown"></i>
                    </div>
                    <div class="info-text">
                        <strong>⚠️ You are the Team Captain!</strong>
                        <p>Before leaving, you must either:</p>
                        <ul class="warning-list">
                            <li>Transfer captaincy to another member</li>
                            <li>Disband the team (if you're the last member)</li>
                        </ul>
                        <p class="mt-2">Go to <strong>Team Settings</strong> to manage this.</p>
                    </div>
                </div>
                ` : ''}
                
                <div class="warning-card">
                    <div class="warning-icon">
                        <i class="fas fa-info-circle"></i>
                    </div>
                    <div class="warning-text">
                        <strong>What happens when you leave?</strong>
                        <ul class="warning-list">
                            <li>You'll lose access to team resources</li>
                            <li>Your tournament history will remain</li>
                            <li>Team captain can re-invite you</li>
                            ${willBecomeSolo ? '<li class="highlight">⚠️ Team will have only 1 member left</li>' : ''}
                        </ul>
                    </div>
                </div>

                ${memberCount <= 2 && !isCaptain ? `
                <div class="info-card danger">
                    <div class="info-icon">
                        <i class="fas fa-users-slash"></i>
                    </div>
                    <div class="info-text">
                        <strong>Low Team Member Count</strong>
                        <p>This team will be left with minimal members. Consider discussing with your captain first.</p>
                    </div>
                </div>
                ` : ''}

                ${!isCaptain ? `
                <form id="leaveTeamForm" class="modern-form">
                    <div class="form-group">
                        <label for="leave_reason" class="form-label">
                            <i class="fas fa-comment"></i>
                            Reason for leaving (Optional)
                        </label>
                        <textarea 
                            id="leave_reason" 
                            name="leave_reason" 
                            class="form-control"
                            placeholder="Let your captain know why you're leaving..."
                            rows="3"
                            maxlength="500"></textarea>
                        <small class="form-hint">
                            <i class="fas fa-info-circle"></i>
                            This will be visible to your captain
                        </small>
                    </div>
                ` : ''}

                    <div class="alternative-actions">
                        <p class="alt-title">
                            <i class="fas fa-lightbulb"></i>
                            Instead of leaving, you could:
                        </p>
                        <div class="alt-buttons">
                            <button type="button" class="btn-alt" data-action="message">
                                <i class="fas fa-comments"></i>
                                <span>Talk to Captain</span>
                            </button>
                            <button type="button" class="btn-alt" data-action="inactive">
                                <i class="fas fa-pause"></i>
                                <span>Go Inactive</span>
                            </button>
                        </div>
                    </div>

                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary" data-dismiss="modal">
                            <i class="fas fa-times"></i>
                            Cancel
                        </button>
                        <button type="submit" class="btn btn-danger">
                            <i class="fas fa-sign-out-alt"></i>
                            Leave Team
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    return modal;
}

/**
 * Setup modal event handlers
 */
function setupLeaveModalHandlers(modal, teamSlug) {
    const form = modal.querySelector('#leaveTeamForm');
    const dismissButtons = modal.querySelectorAll('[data-dismiss="modal"]');
    const altButtons = modal.querySelectorAll('[data-action]');
    
    // Form submission (only if form exists - not captain)
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await submitLeaveRequest(form, teamSlug, modal);
        });
    }
    
    // Dismiss handlers
    dismissButtons.forEach(btn => {
        btn.addEventListener('click', () => closeModal(modal));
    });
    
    // Alternative action handlers
    altButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            handleAlternativeAction(action, teamSlug, modal);
        });
    });
}

/**
 * Submit leave team request
 */
async function submitLeaveRequest(form, teamSlug, modal) {
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalHTML = submitBtn.innerHTML;
    
    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Leaving...';
        
        const formData = new FormData(form);
        const reason = formData.get('leave_reason');
        
        const response = await fetch(`/teams/${teamSlug}/leave/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ reason })
        });
        
        const result = await response.json();
        
        if (result.success || response.ok) {
            showToast('You have left the team', 'success');
            closeModal(modal);
            
            // Wait a moment then reload or redirect
            setTimeout(() => {
                window.location.href = '/teams/';
            }, 1500);
        } else {
            throw new Error(result.error || 'Failed to leave team');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast(error.message || 'Failed to leave team', 'error');
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHTML;
    }
}

/**
 * Handle alternative actions
 */
function handleAlternativeAction(action, teamSlug, modal) {
    switch (action) {
        case 'message':
            closeModal(modal);
            // Redirect to team page with message section
            window.location.href = `/teams/${teamSlug}/#messages`;
            break;
            
        case 'inactive':
            closeModal(modal);
            showToast('Feature coming soon: Set inactive status', 'info');
            // TODO: Implement set inactive functionality
            break;
    }
}

/**
 * Close modal
 */
function closeModal(modal) {
    modal.classList.remove('active');
    setTimeout(() => {
        modal.remove();
    }, 300);
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Use existing toast system if available
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
        return;
    }
    
    // Fallback toast implementation
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const iconMap = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'info': 'info-circle',
        'warning': 'exclamation-triangle'
    };
    
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-${iconMap[type] || 'info-circle'}"></i>
        </div>
        <div class="toast-message">${escapeHtml(message)}</div>
    `;
    
    document.body.appendChild(toast);
    
    requestAnimationFrame(() => {
        toast.classList.add('active');
    });
    
    setTimeout(() => {
        toast.classList.remove('active');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Get CSRF cookie
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make function globally available
window.showLeaveTeamModal = showLeaveTeamModal;
