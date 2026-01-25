/**
 * Team/Organization Creation UI
 * 
 * Vanilla JavaScript for managing the 2-step creation flow:
 * - Step 1: Choose between creating an organization or team
 * - Step 2: Fill out the relevant form
 * 
 * Uses fetch() API to call vNext REST endpoints.
 * Handles loading states, validation errors, and success messages.
 */

(function() {
    'use strict';

    // State
    let currentStep = 1;
    let creationType = null; // 'organization' or 'team'

    // DOM Elements
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step1Indicator = document.getElementById('step1-indicator');
    const step2Indicator = document.getElementById('step2-indicator');
    const stepConnector = document.getElementById('step-connector');
    
    const btnCreateOrganization = document.getElementById('btn-create-organization');
    const btnCreateTeam = document.getElementById('btn-create-team');
    
    const organizationForm = document.getElementById('organization-form');
    const teamForm = document.getElementById('team-form');
    
    const btnOrgBack = document.getElementById('btn-org-back');
    const btnTeamBack = document.getElementById('btn-team-back');
    const btnOrgSubmit = document.getElementById('btn-org-submit');
    const btnTeamSubmit = document.getElementById('btn-team-submit');
    
    const successState = document.getElementById('success-state');
    const successMessage = document.getElementById('success-message');
    const successLink = document.getElementById('success-link');
    
    const errorState = document.getElementById('error-state');
    const errorMessage = document.getElementById('error-message');

    // Get CSRF token from cookie
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

    const csrftoken = getCookie('csrftoken');

    // Step Navigation
    function goToStep(step) {
        currentStep = step;

        if (step === 1) {
            step1.classList.remove('hidden');
            step2.classList.add('hidden');
            
            step1Indicator.classList.remove('opacity-50');
            step2Indicator.classList.add('opacity-50');
            stepConnector.classList.remove('bg-blue-600');
            stepConnector.classList.add('bg-gray-300');
            
            hideErrors();
        } else if (step === 2) {
            step1.classList.add('hidden');
            step2.classList.remove('hidden');
            
            step1Indicator.classList.add('opacity-50');
            step2Indicator.classList.remove('opacity-50');
            stepConnector.classList.remove('bg-gray-300');
            stepConnector.classList.add('bg-blue-600');
            
            // Show appropriate form
            if (creationType === 'organization') {
                organizationForm.classList.remove('hidden');
                teamForm.classList.add('hidden');
            } else if (creationType === 'team') {
                teamForm.classList.remove('hidden');
                organizationForm.classList.add('hidden');
                loadGames();
            }
            
            hideErrors();
        }
    }

    // Error Handling
    function showError(message) {
        errorState.classList.remove('hidden');
        errorMessage.textContent = message;
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function hideErrors() {
        errorState.classList.add('hidden');
        
        // Clear field-specific errors
        document.querySelectorAll('[id$="-error"]').forEach(el => {
            el.classList.add('hidden');
            el.textContent = '';
        });
    }

    function showFieldError(fieldId, message) {
        const errorEl = document.getElementById(fieldId + '-error');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.remove('hidden');
        }
    }

    // Success Handling
    function showSuccess(message, link) {
        step2.classList.add('hidden');
        successState.classList.remove('hidden');
        successMessage.textContent = message;
        successLink.href = link;
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // Loading State
    function setLoading(button, isLoading) {
        if (isLoading) {
            button.disabled = true;
            button.dataset.originalText = button.textContent;
            button.textContent = 'Creating...';
            button.classList.add('opacity-75', 'cursor-not-allowed');
        } else {
            button.disabled = false;
            button.textContent = button.dataset.originalText;
            button.classList.remove('opacity-75', 'cursor-not-allowed');
        }
    }

    // Load Games for Team Form
    async function loadGames() {
        const gameSelect = document.getElementById('team-game');
        
        try {
            const response = await fetch('/api/games/');
            if (!response.ok) {
                console.error('Failed to load games');
                return;
            }
            
            const games = await response.json();
            
            // Clear existing options (keep placeholder)
            while (gameSelect.options.length > 1) {
                gameSelect.remove(1);
            }
            
            // Add game options
            games.forEach(game => {
                const option = document.createElement('option');
                option.value = game.id;
                option.textContent = game.name;
                gameSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading games:', error);
            // Don't block form if games fail to load - user can still try to submit
        }
    }

    // Event Listeners: Step 1
    btnCreateOrganization.addEventListener('click', function() {
        creationType = 'organization';
        goToStep(2);
    });

    btnCreateTeam.addEventListener('click', function() {
        creationType = 'team';
        goToStep(2);
    });

    // Event Listeners: Back Buttons
    btnOrgBack.addEventListener('click', function() {
        goToStep(1);
    });

    btnTeamBack.addEventListener('click', function() {
        goToStep(1);
    });

    // Event Listeners: Form Submissions
    organizationForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        hideErrors();
        
        const formData = {
            name: document.getElementById('org-name').value.trim(),
            slug: document.getElementById('org-slug').value.trim() || undefined,
        };

        setLoading(btnOrgSubmit, true);

        try {
            const response = await fetch('/api/vnext/organizations/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                credentials: 'same-origin',
                body: JSON.stringify(formData),
            });

            const data = await response.json();

            if (response.ok) {
                showSuccess(
                    `Organization "${formData.name}" created successfully!`,
                    `/organizations/${data.organization_slug}/`
                );
            } else {
                // Handle validation errors
                if (data.error_code === 'validation_error' && data.details) {
                    // Show field-specific errors
                    Object.keys(data.details).forEach(field => {
                        const errorMsg = Array.isArray(data.details[field])
                            ? data.details[field].join(', ')
                            : data.details[field];
                        showFieldError('org-' + field, errorMsg);
                    });
                    showError('Please fix the errors below');
                } else {
                    // Show general error
                    showError(data.safe_message || data.message || 'Failed to create organization');
                    console.error('API Error:', data.error_code, data);
                }
            }
        } catch (error) {
            console.error('Network error:', error);
            showError('Network error. Please check your connection and try again.');
        } finally {
            setLoading(btnOrgSubmit, false);
        }
    });

    teamForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        hideErrors();
        
        const formData = {
            name: document.getElementById('team-name').value.trim(),
            game_id: parseInt(document.getElementById('team-game').value),
            region: document.getElementById('team-region').value || undefined,
        };

        // Validate game_id
        if (!formData.game_id || isNaN(formData.game_id)) {
            showFieldError('team-game', 'Please select a game');
            showError('Please fix the errors below');
            return;
        }

        setLoading(btnTeamSubmit, true);

        try {
            const response = await fetch('/api/vnext/teams/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                credentials: 'same-origin',
                body: JSON.stringify(formData),
            });

            const data = await response.json();

            if (response.ok) {
                showSuccess(
                    `Team "${formData.name}" created successfully!`,
                    data.team_url
                );
            } else {
                // Handle validation errors
                if (data.error_code === 'validation_error' && data.details) {
                    // Show field-specific errors
                    Object.keys(data.details).forEach(field => {
                        const errorMsg = Array.isArray(data.details[field])
                            ? data.details[field].join(', ')
                            : data.details[field];
                        showFieldError('team-' + field.replace('_', '-'), errorMsg);
                    });
                    showError('Please fix the errors below');
                } else {
                    // Show general error
                    showError(data.safe_message || data.message || 'Failed to create team');
                    console.error('API Error:', data.error_code, data);
                }
            }
        } catch (error) {
            console.error('Network error:', error);
            showError('Network error. Please check your connection and try again.');
        } finally {
            setLoading(btnTeamSubmit, false);
        }
    });

    // Initialize
    goToStep(1);
})();
