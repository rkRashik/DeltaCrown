/**
 * 🎮 VALORANT TOURNAMENT REGISTRATION INTERACTIONS 🎮
 * Professional JavaScript for Valorant tournament registration forms
 * Extracted from inline code for better maintainability and reusability
 */

let playerCount = 2; // Start with 2 since captain is player 1
const maxPlayers = 7; // 5 main + 2 substitutes

function addPlayer() {
    if (playerCount >= maxPlayers) {
        alert('Maximum 7 players allowed (5 main players + 2 substitutes)');
        return;
    }
    
    playerCount++;
    const isSubstitute = playerCount > 5;
    const playerRole = isSubstitute ? 'substitute' : 'main';
    const playerRoleText = isSubstitute ? 'Substitute' : 'Main';
    
    const playerCard = document.createElement('div');
    playerCard.className = 'player-card';
    playerCard.innerHTML = `
        <div class="player-card-header">
            <div class="flex items-center gap-3">
                <span class="player-role-badge ${playerRole}">${playerRoleText}</span>
                <span class="font-medium">Player ${playerCount}${isSubstitute ? ' (Substitute)' : ''}</span>
            </div>
            <button type="button" onclick="removePlayer(this)" class="text-red-400 hover:text-red-300">
                ✕
            </button>
        </div>
        
        <div class="form-grid form-grid-3">
            <div class="form-group">
                <label class="form-label">Full Name <span class="required">*</span></label>
                <input type="text" name="player_${playerCount}_name" class="form-input" required>
            </div>
            <div class="form-group">
                <label class="form-label">Riot ID & Tagline <span class="required">*</span></label>
                <input type="text" name="player_${playerCount}_riot_id" class="form-input" required>
            </div>
            <div class="form-group">
                <label class="form-label">Discord ID <span class="required">*</span></label>
                <input type="text" name="player_${playerCount}_discord" class="form-input" required>
            </div>
            <div class="form-group">
                <label class="form-label">Email <span class="required">*</span></label>
                <input type="email" name="player_${playerCount}_email" class="form-input" required>
            </div>
            <div class="form-group">
                <label class="form-label">Phone <span class="text-gray-400">(Optional)</span></label>
                <input type="tel" name="player_${playerCount}_phone" class="form-input">
            </div>
            <div class="form-group">
                <label class="form-label">Country <span class="required">*</span></label>
                <select name="player_${playerCount}_country" class="form-input form-select" required>
                    <option value="">Select Country</option>
                    <option value="BD">Bangladesh</option>
                    <option value="IN">India</option>
                    <option value="PK">Pakistan</option>
                    <option value="LK">Sri Lanka</option>
                    <option value="NP">Nepal</option>
                    <option value="OTHER">Other</option>
                </select>
            </div>
        </div>
    `;
    
    document.getElementById('player-roster').appendChild(playerCard);
    
    // Hide add button if max players reached
    if (playerCount >= maxPlayers) {
        document.querySelector('.add-player-btn').style.display = 'none';
    }
}

function removePlayer(button) {
    const playerCard = button.closest('.player-card');
    playerCard.remove();
    playerCount--;
    
    // Show add button if under max players
    if (playerCount < maxPlayers) {
        document.querySelector('.add-player-btn').style.display = 'flex';
    }
    
    // Renumber remaining players
    const playerCards = document.querySelectorAll('.player-card');
    playerCards.forEach((card, index) => {
        if (index === 0) return; // Skip captain card
        
        const playerNumber = index + 1;
        const isSubstitute = playerNumber > 5;
        const roleText = isSubstitute ? 'Substitute' : 'Main';
        
        // Update header
        const header = card.querySelector('.player-card-header span:last-child');
        header.textContent = `Player ${playerNumber}${isSubstitute ? ' (Substitute)' : ''}`;
        
        // Update badge
        const badge = card.querySelector('.player-role-badge');
        badge.textContent = roleText;
        badge.className = `player-role-badge ${isSubstitute ? 'substitute' : ''}`;
        
        // Update input names
        const inputs = card.querySelectorAll('input, select');
        inputs.forEach(input => {
            const name = input.name;
            if (name && name.startsWith('player_')) {
                const suffix = name.split('_').slice(2).join('_');
                input.name = `player_${playerNumber}_${suffix}`;
            }
        });
    });
}

// Enhanced form validation and user experience
document.addEventListener('DOMContentLoaded', function() {
    initializeFormValidation();
    initializeUserExperience();
    initializeAccessibility();
    initializeCaptainSync();
});

// Real-time form validation
function initializeFormValidation() {
    const form = document.querySelector('form[method="post"]');
    if (!form) return;
    
    // Riot ID validation for all fields
    const riotIdFields = document.querySelectorAll('input[name*="riot_id"]');
    riotIdFields.forEach(field => {
        addRealTimeValidation(field, validateRiotId, field.name + '-error');
    });
    
    // Discord ID validation  
    const discordFields = document.querySelectorAll('input[name*="discord"]');
    discordFields.forEach(field => {
        addRealTimeValidation(field, validateDiscordId, field.name + '-error');
    });
    
    // Email validation
    const emailFields = document.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        addRealTimeValidation(field, validateEmail, field.name + '-error');
    });
    
    // Phone validation
    const phoneFields = document.querySelectorAll('input[type="tel"]');
    phoneFields.forEach(field => {
        addRealTimeValidation(field, validatePhone, field.name + '-error');
    });
}

function addRealTimeValidation(field, validator, errorId) {
    let errorDiv = document.getElementById(errorId);
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = errorId;
        errorDiv.className = 'validation-error';
        field.parentNode.appendChild(errorDiv);
    }
    
    field.addEventListener('input', function() {
        clearTimeout(field.validationTimeout);
        field.validationTimeout = setTimeout(() => {
            const result = validator(field.value);
            showValidationResult(field, errorDiv, result);
        }, 300);
    });
    
    field.addEventListener('blur', function() {
        const result = validator(field.value);
        showValidationResult(field, errorDiv, result);
    });
}

function showValidationResult(field, errorDiv, result) {
    field.classList.remove('error', 'success');
    errorDiv.style.display = 'none';
    
    if (field.value && result.isValid) {
        field.classList.add('success');
    } else if (field.value && !result.isValid && result.message) {
        field.classList.add('error');
        errorDiv.textContent = result.message;
        errorDiv.style.display = 'block';
    }
}

// Validation functions
function validateRiotId(value) {
    if (!value) return { isValid: false, message: '' };
    
    const riotIdPattern = /^[a-zA-Z0-9\s]{3,16}#[a-zA-Z0-9]{3,5}$/;
    if (!riotIdPattern.test(value)) {
        return { isValid: false, message: '⚠️ Format: Username#TAG (e.g., PlayerName#NA1)' };
    }
    
    return { isValid: true };
}

function validateDiscordId(value) {
    if (!value) return { isValid: false, message: '' };
    
    const discordPattern = /^.{2,32}#[0-9]{4}$/;
    if (!discordPattern.test(value)) {
        return { isValid: false, message: '⚠️ Format: Username#1234' };
    }
    
    return { isValid: true };
}

function validateEmail(value) {
    if (!value) return { isValid: true }; // Optional field
    
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(value)) {
        return { isValid: false, message: '⚠️ Please enter a valid email address' };
    }
    
    return { isValid: true };
}

function validatePhone(value) {
    if (!value) return { isValid: true }; // Optional field
    
    const phonePattern = /^(\+?88)?01[3-9]\d{8}$/;
    if (!phonePattern.test(value.replace(/[\s-]/g, ''))) {
        return { isValid: false, message: '⚠️ Please enter a valid phone number' };
    }
    
    return { isValid: true };
}

// Enhanced user experience features
function initializeUserExperience() {
    // Auto-format input fields
    formatInputFields();
    
    // Form submission with validation
    const form = document.querySelector('form[method="post"]');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (!validateAllRequiredFields()) {
                e.preventDefault();
                showNotification('⚠️ Please fill in all required fields correctly', 'error');
                return false;
            }
            
            handleFormSubmission();
        });
    }
    
    // Progress tracking
    trackFormProgress();
}

function formatInputFields() {
    // Auto-format Riot ID
    const riotIdFields = document.querySelectorAll('input[name*="riot_id"]');
    riotIdFields.forEach(field => {
        field.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^a-zA-Z0-9#\s]/g, '');
            const hashCount = (value.match(/#/g) || []).length;
            if (hashCount > 1) {
                value = value.replace(/#.*#/, '#');
            }
            e.target.value = value;
        });
    });
    
    // Auto-format phone numbers
    const phoneFields = document.querySelectorAll('input[type="tel"]');
    phoneFields.forEach(field => {
        field.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.startsWith('88')) {
                value = '+' + value;
            } else if (value.startsWith('01')) {
                value = '+88' + value;
            }
            e.target.value = value;
        });
    });
}

function trackFormProgress() {
    const requiredFields = document.querySelectorAll('input[required]');
    let completedFields = 0;
    
    requiredFields.forEach(field => {
        field.addEventListener('input', function() {
            completedFields = Array.from(requiredFields).filter(f => f.value.trim()).length;
            const progress = (completedFields / requiredFields.length) * 100;
            updateProgressBar(progress);
        });
    });
}

function updateProgressBar(percentage) {
    let progressBar = document.querySelector('.form-progress-bar');
    if (!progressBar) {
        progressBar = createProgressBar();
    }
    
    progressBar.style.width = percentage + '%';
    
    const progressText = document.querySelector('.progress-text');
    if (progressText) {
        progressText.textContent = `${Math.round(percentage)}% Complete`;
    }
}

function createProgressBar() {
    const container = document.createElement('div');
    container.className = 'progress-container fixed top-0 left-0 right-0 z-50';
    container.innerHTML = `
        <div class="bg-gray-800 h-1">
            <div class="form-progress-bar bg-red-500 h-1 transition-all duration-300" style="width: 0%"></div>
        </div>
        <div class="progress-text text-xs text-gray-400 text-center py-1 bg-gray-900">0% Complete</div>
    `;
    
    document.body.insertBefore(container, document.body.firstChild);
    return container.querySelector('.form-progress-bar');
}

// Accessibility improvements
function initializeAccessibility() {
    const form = document.querySelector('form[method="post"]');
    if (form) {
        form.setAttribute('novalidate', ''); // Use custom validation
    }
    
    // Add keyboard navigation support
    addKeyboardSupport();
}

function addKeyboardSupport() {
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.target.type !== 'submit') {
            e.preventDefault();
            const nextField = getNextField(e.target);
            if (nextField) {
                nextField.focus();
            }
        }
    });
}

function getNextField(currentField) {
    const formFields = Array.from(document.querySelectorAll('input, select, textarea'));
    const currentIndex = formFields.indexOf(currentField);
    return formFields[currentIndex + 1];
}

function validateAllRequiredFields() {
    const requiredFields = document.querySelectorAll('input[required]');
    let allValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('error');
            allValid = false;
        } else {
            field.classList.remove('error');
        }
    });
    
    return allValid;
}

function handleFormSubmission() {
    const submitBtn = document.querySelector('.submit-button');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>⚡ Processing Registration...';
        submitBtn.classList.add('btn-loading');
        
        showNotification('🎮 Registering your Valorant team...', 'info');
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification fixed top-20 right-4 p-4 rounded-lg shadow-lg z-50 transform translate-x-full transition-transform ${
        type === 'error' ? 'bg-red-600' : 
        type === 'success' ? 'bg-green-600' : 'bg-blue-600'
    } text-white max-w-sm`;
    
    notification.innerHTML = `
        <div class="flex items-center justify-between">
            <span>${message}</span>
            <button onclick="this.parentElement.parentElement.remove()" class="ml-2 text-white hover:text-gray-200">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => notification.classList.remove('translate-x-full'), 100);
    setTimeout(() => {
        notification.classList.add('translate-x-full');
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

// Auto-populate captain fields and load team data
function initializeCaptainSync() {
    // Auto-populate captain fields to player 1
    const captainFields = ['full_name', 'email', 'riot_id', 'discord', 'phone', 'country'];
    
    captainFields.forEach(field => {
        const captainInput = document.querySelector(`input[name="captain_${field}"], select[name="captain_${field}"]`);
        const playerInput = document.querySelector(`input[name="player_1_${field}"], select[name="player_1_${field}"]`);
        
        if (captainInput && playerInput) {
            captainInput.addEventListener('input', function() {
                playerInput.value = this.value;
            });
        }
    });
}

// Make functions globally accessible
window.addPlayer = addPlayer;
window.removePlayer = removePlayer;