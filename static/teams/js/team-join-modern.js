/**
 * MODERN TEAM JOIN SYSTEM
 * Version: 1.0 - 2025
 * 
 * Features:
 * - Inline game ID collection during join flow
 * - Modern modal with glassmorphism design
 * - Smart validation and error handling
 * - Smooth animations and transitions
 * - Progress indicators
 */

class ModernTeamJoin {
    constructor() {
        this.modal = null;
        this.currentStep = 1;
        this.teamSlug = null;
        this.teamData = null;
        this.gameCode = null;
        this.gameName = null;
        this.needsGameID = false;
    }

    /**
     * Initialize join flow for a team
     */
    async initJoin(teamSlug, teamName, gameCode, gameName) {
        this.teamSlug = teamSlug;
        this.teamData = { name: teamName };
        this.gameCode = gameCode;
        this.gameName = gameName;

        // Always show game ID modal first - user can enter or update their game ID
        this.needsGameID = true;
        this.showGameIDModal();
    }

    /**
     * Check if game ID is required
     */
    async checkGameIDRequired() {
        try {
            const response = await fetch(`/api/profile/check-game-id/${this.gameCode}/`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                return !data.has_game_id;
            }
        } catch (error) {
            console.error('Error checking game ID:', error);
        }
        return false;
    }

    /**
     * Show game ID collection modal
     */
    showGameIDModal() {
        this.modal = this.createModal('game-id');
        document.body.appendChild(this.modal);
        
        // Animate in
        requestAnimationFrame(() => {
            this.modal.classList.add('active');
        });

        // Set up event listeners
        this.setupGameIDForm();
    }

    /**
     * Show join confirmation modal
     */
    showConfirmModal() {
        this.modal = this.createModal('confirm');
        document.body.appendChild(this.modal);
        
        // Animate in
        requestAnimationFrame(() => {
            this.modal.classList.add('active');
        });

        // Set up event listeners
        this.setupConfirmForm();
    }

    /**
     * Create modal HTML
     */
    createModal(type) {
        const modal = document.createElement('div');
        modal.className = 'modern-join-modal';
        modal.id = 'teamJoinModal';

        if (type === 'game-id') {
            modal.innerHTML = this.getGameIDModalHTML();
        } else {
            modal.innerHTML = this.getConfirmModalHTML();
        }

        return modal;
    }

    /**
     * Get Game ID modal HTML
     */
    getGameIDModalHTML() {
        const gameIDField = this.getGameIDFieldHTML();
        
        return `
            <div class="modal-overlay" data-dismiss="modal"></div>
            <div class="modal-container">
                <div class="modal-header">
                    <div class="header-icon">
                        <i class="fas fa-id-card-alt"></i>
                    </div>
                    <div class="header-content">
                        <h2>Setup Your ${this.gameName} Profile</h2>
                        <p>We need your game ID to match you with teammates</p>
                    </div>
                    <button class="modal-close" data-dismiss="modal">
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <div class="modal-body">
                    <div class="info-card">
                        <div class="info-icon">
                            <i class="fas fa-shield-alt"></i>
                        </div>
                        <div class="info-text">
                            <strong>Privacy Protected</strong>
                            <p>Your game ID is only visible to your team captain and teammates</p>
                        </div>
                    </div>

                    <form id="gameIDForm" class="modern-form">
                        ${gameIDField}

                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">
                                <i class="fas fa-times"></i>
                                Cancel
                            </button>
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-arrow-right"></i>
                                Continue to Join
                            </button>
                        </div>
                    </form>
                </div>

                <div class="modal-progress">
                    <div class="progress-step active">
                        <div class="step-dot">1</div>
                        <span>Game ID</span>
                    </div>
                    <div class="progress-line"></div>
                    <div class="progress-step">
                        <div class="step-dot">2</div>
                        <span>Confirm</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get game-specific field HTML
     */
    getGameIDFieldHTML() {
        const gameFields = {
            'valorant': `
                <div class="form-group">
                    <label for="riot_id" class="form-label">
                        <i class="fas fa-gamepad"></i>
                        Riot ID (Name#Tag)
                        <span class="required">*</span>
                    </label>
                    <input 
                        type="text" 
                        id="riot_id" 
                        name="riot_id" 
                        class="form-control"
                        placeholder="PlayerName#1234"
                        required
                        pattern="^[^#]+#[^#]+$"
                    >
                    <small class="form-hint">
                        <i class="fas fa-info-circle"></i>
                        Example: ShroudGG#NA1
                    </small>
                </div>
            `,
            'csgo': `
                <div class="form-group">
                    <label for="steam_id" class="form-label">
                        <i class="fab fa-steam"></i>
                        Steam ID
                        <span class="required">*</span>
                    </label>
                    <input 
                        type="text" 
                        id="steam_id" 
                        name="steam_id" 
                        class="form-control"
                        placeholder="76561198012345678"
                        required
                    >
                    <small class="form-hint">
                        <i class="fas fa-info-circle"></i>
                        Find it at <a href="https://steamid.io/" target="_blank">steamid.io</a>
                    </small>
                </div>
            `,
            'pubg': `
                <div class="form-group">
                    <label for="pubg_id" class="form-label">
                        <i class="fas fa-gamepad"></i>
                        PUBG Username
                        <span class="required">*</span>
                    </label>
                    <input 
                        type="text" 
                        id="pubg_id" 
                        name="pubg_id" 
                        class="form-control"
                        placeholder="YourPUBGName"
                        required
                    >
                </div>
            `
        };

        return gameFields[this.gameCode] || `
            <div class="form-group">
                <label for="game_id" class="form-label">
                    <i class="fas fa-gamepad"></i>
                    Game ID
                    <span class="required">*</span>
                </label>
                <input 
                    type="text" 
                    id="game_id" 
                    name="game_id" 
                    class="form-control"
                    placeholder="Enter your game ID"
                    required
                >
            </div>
        `;
    }

    /**
     * Get confirmation modal HTML
     */
    getConfirmModalHTML() {
        return `
            <div class="modal-overlay" data-dismiss="modal"></div>
            <div class="modal-container">
                <div class="modal-header">
                    <div class="header-icon success">
                        <i class="fas fa-users"></i>
                    </div>
                    <div class="header-content">
                        <h2>Join ${this.teamData.name}?</h2>
                        <p>You're about to join this ${this.gameName} team</p>
                    </div>
                    <button class="modal-close" data-dismiss="modal">
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <div class="modal-body">
                    <div class="team-preview-card">
                        <div class="team-icon">
                            <i class="fas fa-shield-alt"></i>
                        </div>
                        <div class="team-info">
                            <h3>${this.teamData.name}</h3>
                            <span class="game-badge">
                                <i class="fas fa-gamepad"></i>
                                ${this.gameName}
                            </span>
                        </div>
                    </div>

                    <div class="benefits-list">
                        <div class="benefit-item">
                            <i class="fas fa-trophy"></i>
                            <span>Compete in tournaments</span>
                        </div>
                        <div class="benefit-item">
                            <i class="fas fa-users"></i>
                            <span>Team up with players</span>
                        </div>
                        <div class="benefit-item">
                            <i class="fas fa-chart-line"></i>
                            <span>Track team progress</span>
                        </div>
                    </div>

                    <form id="confirmJoinForm" class="modern-form">
                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">
                                <i class="fas fa-times"></i>
                                Cancel
                            </button>
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-check"></i>
                                Join Team
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }

    /**
     * Setup game ID form handlers
     */
    setupGameIDForm() {
        const form = this.modal.querySelector('#gameIDForm');
        const dismissButtons = this.modal.querySelectorAll('[data-dismiss="modal"]');

        // Form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.submitGameID(form);
        });

        // Dismiss handlers
        dismissButtons.forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });
    }

    /**
     * Setup confirm form handlers
     */
    setupConfirmForm() {
        const form = this.modal.querySelector('#confirmJoinForm');
        const dismissButtons = this.modal.querySelectorAll('[data-dismiss="modal"]');

        // Form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.submitJoinRequest();
        });

        // Dismiss handlers
        dismissButtons.forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });
    }

    /**
     * Submit game ID
     */
    async submitGameID(form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalHTML = submitBtn.innerHTML;
        
        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            const response = await fetch(`/api/profile/save-game-id/${this.gameCode}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                // Show success feedback
                this.showSuccessAnimation();
                
                // Wait a moment then proceed to confirmation
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Close current modal and show confirm
                this.closeModal();
                this.showConfirmModal();
            } else {
                throw new Error(result.error || 'Failed to save game ID');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showToast(error.message || 'Failed to save game ID', 'error');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalHTML;
        }
    }

    /**
     * Submit join request
     */
    async submitJoinRequest() {
        const form = this.modal.querySelector('#confirmJoinForm');
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalHTML = submitBtn.innerHTML;
        
        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Joining...';

            const response = await fetch(`/teams/${this.teamSlug}/join/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const result = await response.json();

            if (result.success) {
                this.showToast(result.message || 'Successfully joined the team!', 'success');
                this.closeModal();
                
                // Reload page to show updated membership
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                throw new Error(result.error || 'Failed to join team');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showToast(error.message || 'Failed to join team', 'error');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalHTML;
        }
    }

    /**
     * Show success animation
     */
    showSuccessAnimation() {
        const header = this.modal.querySelector('.modal-header');
        const icon = header.querySelector('.header-icon');
        
        icon.innerHTML = '<i class="fas fa-check-circle"></i>';
        icon.classList.add('success');
        
        // Add checkmark animation
        icon.style.animation = 'checkmarkPop 0.5s ease-out';
    }

    /**
     * Close modal
     */
    closeModal() {
        if (this.modal) {
            this.modal.classList.remove('active');
            setTimeout(() => {
                this.modal.remove();
                this.modal = null;
            }, 300);
        }
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        // Use existing toast system if available
        if (typeof showToast === 'function') {
            showToast(message, type);
            return;
        }

        // Fallback toast implementation
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            </div>
            <div class="toast-message">${message}</div>
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
     * Get cookie value
     */
    getCookie(name) {
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
}

// Initialize global instance
const modernTeamJoin = new ModernTeamJoin();

// Expose to window for easy access
window.modernTeamJoin = modernTeamJoin;
