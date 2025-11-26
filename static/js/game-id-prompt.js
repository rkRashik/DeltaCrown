/**
 * Game ID Prompt System
 * Shows modal to collect game IDs from users during team creation/joining
 */

class GameIDPrompt {
    constructor() {
        this.modal = null;
        this.currentGame = null;
        this.resolve = null;
        this.reject = null;
    }

    /**
     * Show game ID prompt modal for specific game
     * @param {string} gameCode - Game code (valorant, efootball, etc.)
     * @returns {Promise<boolean>} - Returns true if saved successfully, false if cancelled
     */
    async prompt(gameCode) {
        this.currentGame = gameCode;
        
        return new Promise((resolve, reject) => {
            this.resolve = resolve;
            this.reject = reject;
            this.showModal(gameCode);
        });
    }

    /**
     * Show the modal
     */
    showModal(gameCode) {
        const config = this.getGameConfig(gameCode);
        
        // Remove existing modal if any
        this.closeModal();
        
        // Create modal
        this.modal = document.createElement('div');
        this.modal.className = 'game-id-modal-overlay';
        this.modal.innerHTML = `
            <div class="game-id-modal">
                <button class="game-id-modal-close" aria-label="Close">&times;</button>
                
                <div class="game-id-modal-header">
                    <div class="game-id-modal-icon">
                        <i class="fas fa-gamepad"></i>
                    </div>
                    <h2 class="game-id-modal-title">${config.title}</h2>
                    <p class="game-id-modal-subtitle">${config.subtitle}</p>
                </div>
                
                <div class="game-id-modal-body">
                    ${this.renderGameFields(config)}
                    
                    <div class="game-id-privacy-notice">
                        <i class="fas fa-shield-alt"></i>
                        <p><strong>Privacy:</strong> Your game ID will only be visible to your team captain and members. It will never be displayed publicly.</p>
                    </div>
                </div>
                
                <div class="game-id-modal-footer">
                    <button type="button" class="game-id-btn game-id-btn-cancel">
                        Cancel
                    </button>
                    <button type="button" class="game-id-btn game-id-btn-save">
                        <i class="fas fa-check"></i>
                        Save & Continue
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.modal);
        
        // Add animation class after a brief delay
        setTimeout(() => this.modal.classList.add('active'), 10);
        
        // Bind events
        this.bindEvents();
        
        // Focus first input
        const firstInput = this.modal.querySelector('input');
        if (firstInput) {
            firstInput.focus();
        }
    }

    /**
     * Render game-specific input fields
     */
    renderGameFields(config) {
        let html = '<div class="game-id-fields">';
        
        config.fields.forEach(field => {
            html += `
                <div class="game-id-field">
                    <label class="game-id-label">
                        ${field.label}
                        ${field.required ? '<span class="required">*</span>' : ''}
                    </label>
                    <input 
                        type="text" 
                        class="game-id-input" 
                        data-field="${field.name}"
                        placeholder="${field.placeholder}"
                        ${field.required ? 'required' : ''}
                    >
                    ${field.hint ? `<p class="game-id-hint">${field.hint}</p>` : ''}
                </div>
            `;
        });
        
        html += '</div>';
        return html;
    }

    /**
     * Get game-specific configuration
     */
    getGameConfig(gameCode) {
        const configs = {
            'valorant': {
                title: 'Enter Your Riot ID',
                subtitle: 'We need your Riot ID to register your team for Valorant tournaments',
                fields: [
                    {
                        name: 'riot_id',
                        label: 'Riot ID (Name#TAG)',
                        placeholder: 'Professor#TAG',
                        hint: 'Include both your name and tagline (e.g., YourName#1234)',
                        required: true
                    }
                ]
            },
            'efootball': {
                title: 'Enter Your eFootball User ID',
                subtitle: 'We need your User ID to register your team for eFootball tournaments',
                fields: [
                    {
                        name: 'efootball_id',
                        label: 'User ID',
                        placeholder: '123456789',
                        hint: 'Your eFootball User ID (numbers only)',
                        required: true
                    }
                ]
            },
            'dota2': {
                title: 'Enter Your Steam ID',
                subtitle: 'We need your Steam ID to register your team for Dota 2 tournaments',
                fields: [
                    {
                        name: 'steam_id',
                        label: 'Steam ID',
                        placeholder: '76561198012345678',
                        hint: 'Your Steam ID (17-digit number)',
                        required: true
                    }
                ]
            },
            'cs2': {
                title: 'Enter Your Steam ID',
                subtitle: 'We need your Steam ID to register your team for Counter-Strike 2 tournaments',
                fields: [
                    {
                        name: 'steam_id',
                        label: 'Steam ID',
                        placeholder: '76561198012345678',
                        hint: 'Your Steam ID (17-digit number)',
                        required: true
                    }
                ]
            },
            'mlbb': {
                title: 'Enter Your Mobile Legends ID',
                subtitle: 'We need your Game ID and Server ID to register your team for MLBB tournaments',
                fields: [
                    {
                        name: 'mlbb_id',
                        label: 'Game ID',
                        placeholder: '123456789',
                        hint: 'Your Mobile Legends Game ID',
                        required: true
                    },
                    {
                        name: 'mlbb_server_id',
                        label: 'Server ID',
                        placeholder: '1234',
                        hint: 'Your server ID (4 digits)',
                        required: true
                    }
                ]
            },
            'pubg': {
                title: 'Enter Your PUBG Mobile ID',
                subtitle: 'We need your Character ID to register your team for PUBG Mobile tournaments',
                fields: [
                    {
                        name: 'pubg_mobile_id',
                        label: 'Character ID / Player ID',
                        placeholder: '5123456789',
                        hint: 'Your PUBG Mobile Character ID',
                        required: true
                    }
                ]
            },
            'freefire': {
                title: 'Enter Your Free Fire ID',
                subtitle: 'We need your Player ID to register your team for Free Fire tournaments',
                fields: [
                    {
                        name: 'free_fire_id',
                        label: 'User ID / Player ID',
                        placeholder: '123456789',
                        hint: 'Your Free Fire User ID',
                        required: true
                    }
                ]
            },
            'fc24': {
                title: 'Enter Your EA ID',
                subtitle: 'We need your EA ID to register your team for FC 24 tournaments',
                fields: [
                    {
                        name: 'ea_id',
                        label: 'EA ID',
                        placeholder: 'YourEAUsername',
                        hint: 'Your EA account username',
                        required: true
                    }
                ]
            },
            'codm': {
                title: 'Enter Your Call of Duty Mobile UID',
                subtitle: 'We need your UID to register your team for CODM tournaments',
                fields: [
                    {
                        name: 'codm_uid',
                        label: 'UID (Unique ID)',
                        placeholder: '6912345678901',
                        hint: 'Your Call of Duty Mobile UID',
                        required: true
                    }
                ]
            }
        };
        
        return configs[gameCode] || {
            title: 'Enter Your Game ID',
            subtitle: 'We need your game ID to register your team for tournaments',
            fields: [
                {
                    name: 'game_id',
                    label: 'Game ID',
                    placeholder: 'Your game ID',
                    required: true
                }
            ]
        };
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Close button
        const closeBtn = this.modal.querySelector('.game-id-modal-close');
        closeBtn.addEventListener('click', () => this.cancel());
        
        // Cancel button
        const cancelBtn = this.modal.querySelector('.game-id-btn-cancel');
        cancelBtn.addEventListener('click', () => this.cancel());
        
        // Save button
        const saveBtn = this.modal.querySelector('.game-id-btn-save');
        saveBtn.addEventListener('click', () => this.save());
        
        // Click outside to close
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.cancel();
            }
        });
        
        // ESC key to close
        this.escHandler = (e) => {
            if (e.key === 'Escape') {
                this.cancel();
            }
        };
        document.addEventListener('keydown', this.escHandler);
        
        // Enter key to submit
        const inputs = this.modal.querySelectorAll('input');
        inputs.forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.save();
                }
            });
        });
    }

    /**
     * Validate and save game ID
     */
    async save() {
        const inputs = this.modal.querySelectorAll('input[required]');
        const data = {
            game: this.currentGame
        };
        
        // Validate all required fields
        let isValid = true;
        inputs.forEach(input => {
            const fieldName = input.dataset.field;
            const value = input.value.trim();
            
            if (!value) {
                isValid = false;
                input.classList.add('error');
                input.focus();
            } else {
                input.classList.remove('error');
                data[fieldName] = value;
            }
        });
        
        if (!isValid) {
            this.showError('Please fill in all required fields');
            return;
        }
        
        // Show loading state
        const saveBtn = this.modal.querySelector('.game-id-btn-save');
        const originalText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        
        try {
            // Save to profile via API
            const response = await fetch('/user/api/profile/update-game-id/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken()
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                // Success!
                this.closeModal();
                this.resolve(true);
            } else {
                throw new Error(result.error || 'Failed to save game ID');
            }
        } catch (error) {
            console.error('Error saving game ID:', error);
            this.showError(error.message || 'Failed to save. Please try again.');
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
    }

    /**
     * Cancel and close modal
     */
    cancel() {
        this.closeModal();
        this.resolve(false);
    }

    /**
     * Close modal
     */
    closeModal() {
        if (this.modal) {
            this.modal.classList.remove('active');
            setTimeout(() => {
                if (this.modal && this.modal.parentNode) {
                    this.modal.parentNode.removeChild(this.modal);
                }
                this.modal = null;
            }, 300);
            
            // Remove ESC handler
            if (this.escHandler) {
                document.removeEventListener('keydown', this.escHandler);
                this.escHandler = null;
            }
        }
    }

    /**
     * Show error message
     */
    showError(message) {
        // Remove existing error
        const existingError = this.modal.querySelector('.game-id-error');
        if (existingError) {
            existingError.remove();
        }
        
        // Add new error
        const errorDiv = document.createElement('div');
        errorDiv.className = 'game-id-error';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-circle"></i>
            ${message}
        `;
        
        const footer = this.modal.querySelector('.game-id-modal-footer');
        footer.parentNode.insertBefore(errorDiv, footer);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }

    /**
     * Get CSRF token
     */
    getCsrfToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookieValue ? cookieValue.split('=')[1] : '';
    }
}

// Initialize global instance
window.gameIDPrompt = new GameIDPrompt();

dcLog('[GameIDPrompt] System initialized');
