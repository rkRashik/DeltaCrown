/* apps/teams/admin/js/team_points_widget.js */
/* Team Points Calculator Widget JavaScript */

(function() {
    'use strict';
    
    function TeamPointsCalculator() {
        this.init();
    }
    
    TeamPointsCalculator.prototype = {
        init: function() {
            this.bindEvents();
            this.updateDisplay();
        },
        
        bindEvents: function() {
            const self = this;
            
            // Handle Add/Subtract button clicks
            document.addEventListener('click', function(e) {
                if (e.target.closest('.btn-add-points') || e.target.closest('.btn-subtract-points')) {
                    e.preventDefault();
                    self.handleCalculation(e.target.closest('button'));
                }
            });
            
            // Handle input changes for preview
            document.addEventListener('input', function(e) {
                if (e.target.classList.contains('team-points-input')) {
                    self.updatePreview(e.target);
                }
            });
            
            // Clear input after calculation
            document.addEventListener('keydown', function(e) {
                if (e.target.classList.contains('team-points-input') && e.key === 'Enter') {
                    e.preventDefault();
                    const addBtn = e.target.closest('.team-points-calculator').querySelector('.btn-add-points');
                    if (addBtn) {
                        self.handleCalculation(addBtn);
                    }
                }
            });
        },
        
        handleCalculation: function(button) {
            const calculator = button.closest('.team-points-calculator');
            const input = calculator.querySelector('.team-points-input');
            const action = button.getAttribute('data-action');
            
            const value = parseInt(input.value) || 0;
            if (value === 0) {
                this.showMessage(calculator, 'Please enter a points value', 'error');
                return;
            }
            
            // Add loading state
            calculator.classList.add('loading');
            
            // Simulate API call (in real implementation, this would be an AJAX request)
            setTimeout(() => {
                this.processPointsChange(calculator, action, value);
            }, 500);
        },
        
        processPointsChange: function(calculator, action, value) {
            const totalField = this.getTotalPointsField();
            const adjustField = calculator.querySelector('.team-points-input');
            
            if (!totalField) {
                this.showMessage(calculator, 'Could not find total points field', 'error');
                calculator.classList.remove('loading');
                return;
            }
            
            const currentTotal = parseInt(totalField.value) || 0;
            const adjustment = action === 'add' ? value : -value;
            const newTotal = Math.max(0, currentTotal + adjustment); // Prevent negative totals
            
            // Update the total points field
            totalField.value = newTotal;
            
            // Update adjust points field (this tracks the last adjustment made)
            const currentAdjust = parseInt(adjustField.getAttribute('data-current-adjust')) || 0;
            const newAdjust = currentAdjust + adjustment;
            
            // Find and update the adjust_points field in the form
            const adjustPointsField = document.querySelector('input[name="adjust_points"]');
            if (adjustPointsField) {
                adjustPointsField.value = newAdjust;
            }
            
            // Clear the input
            adjustField.value = '';
            adjustField.setAttribute('data-current-adjust', newAdjust);
            
            // Update display
            this.updateDisplay();
            
            // Show success message
            const actionText = action === 'add' ? 'Added' : 'Subtracted';
            this.showMessage(calculator, `${actionText} ${value} points successfully!`, 'success');
            
            // Remove loading state
            calculator.classList.remove('loading');
            
            // Trigger Django's change detection
            this.triggerFormChange(totalField);
            if (adjustPointsField) {
                this.triggerFormChange(adjustPointsField);
            }
        },
        
        updateDisplay: function() {
            const calculators = document.querySelectorAll('.team-points-calculator');
            const totalField = this.getTotalPointsField();
            const totalValue = totalField ? (parseInt(totalField.value) || 0) : 0;
            
            calculators.forEach(calculator => {
                const totalSpan = calculator.querySelector('.total-value');
                if (totalSpan) {
                    totalSpan.textContent = totalValue.toLocaleString();
                }
            });
        },
        
        updatePreview: function(input) {
            const calculator = input.closest('.team-points-calculator');
            const preview = calculator.querySelector('.calculation-preview');
            const value = parseInt(input.value) || 0;
            
            if (value === 0) {
                preview.style.display = 'none';
                return;
            }
            
            const totalField = this.getTotalPointsField();
            const currentTotal = totalField ? (parseInt(totalField.value) || 0) : 0;
            
            preview.style.display = 'inline';
            preview.textContent = `Preview: ${currentTotal} → ${currentTotal + value} (+${value})`;
            preview.className = 'calculation-preview positive';
        },
        
        getTotalPointsField: function() {
            return document.querySelector('input[name="total_points"]') || 
                   document.querySelector('#id_total_points');
        },
        
        showMessage: function(calculator, message, type) {
            // Remove existing messages
            const existingMsg = calculator.querySelector('.calculator-message');
            if (existingMsg) {
                existingMsg.remove();
            }
            
            // Create new message
            const messageDiv = document.createElement('div');
            messageDiv.className = `calculator-message ${type}`;
            messageDiv.textContent = message;
            messageDiv.style.cssText = `
                position: absolute;
                top: -30px;
                left: 50%;
                transform: translateX(-50%);
                background: ${type === 'success' ? '#28a745' : '#dc3545'};
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                white-space: nowrap;
                z-index: 1000;
            `;
            
            calculator.style.position = 'relative';
            calculator.appendChild(messageDiv);
            
            // Remove message after 3 seconds
            setTimeout(() => {
                if (messageDiv.parentNode) {
                    messageDiv.remove();
                }
                calculator.classList.remove('success', 'error');
            }, 3000);
            
            calculator.classList.add(type);
        },
        
        triggerFormChange: function(field) {
            // Trigger Django's unsaved changes detection
            const event = new Event('change', { bubbles: true });
            field.dispatchEvent(event);
            
            // Also trigger input event for better compatibility
            const inputEvent = new Event('input', { bubbles: true });
            field.dispatchEvent(inputEvent);
        }
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            new TeamPointsCalculator();
        });
    } else {
        new TeamPointsCalculator();
    }
    
    // Re-initialize after Django admin inline additions
    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).on('formset:added', function() {
            new TeamPointsCalculator();
        });
    }
})();
