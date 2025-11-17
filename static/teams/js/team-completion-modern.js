/**
 * MODERN TEAM COMPLETION WIDGET
 * Version: 1.0 - 2025
 * 
 * Features:
 * - Circular progress indicator with animation
 * - Category breakdown with icons
 * - Actionable suggestions
 * - Milestone celebrations
 * - Smooth animations and transitions
 */

class TeamCompletionWidget {
    constructor(containerId, completionData) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container ${containerId} not found`);
            return;
        }
        
        this.data = completionData;
        this.percentage = completionData.percentage || 0;
        this.breakdown = completionData.breakdown || {};
        this.suggestions = completionData.suggestions || [];
        this.nextMilestone = completionData.next_milestone || {};
        
        this.init();
    }
    
    init() {
        this.render();
        this.animate();
        this.setupEventListeners();
        
        // Celebrate if 100% complete
        if (this.percentage >= 100) {
            setTimeout(() => this.showCelebration(), 500);
        }
    }
    
    render() {
        const html = `
            <div class="completion-widget-modern">
                <!-- Progress Circle -->
                <div class="completion-circle-container">
                    <svg class="completion-circle" viewBox="0 0 200 200">
                        <!-- Background circle -->
                        <circle
                            class="circle-bg"
                            cx="100"
                            cy="100"
                            r="85"
                            fill="none"
                            stroke="rgba(255,255,255,0.1)"
                            stroke-width="12"
                        />
                        <!-- Progress circle -->
                        <circle
                            class="circle-progress"
                            cx="100"
                            cy="100"
                            r="85"
                            fill="none"
                            stroke="url(#gradient)"
                            stroke-width="12"
                            stroke-linecap="round"
                            stroke-dasharray="534"
                            stroke-dashoffset="534"
                            transform="rotate(-90 100 100)"
                        />
                        <!-- Gradient definition -->
                        <defs>
                            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" style="stop-color:#00d9ff;stop-opacity:1" />
                                <stop offset="100%" style="stop-color:#8b5cf6;stop-opacity:1" />
                            </linearGradient>
                        </defs>
                    </svg>
                    
                    <div class="completion-center">
                        <div class="completion-percentage" data-target="${this.percentage}">0</div>
                        <div class="completion-label">Complete</div>
                        ${this.getStatusBadge()}
                    </div>
                </div>
                
                <!-- Info Section -->
                <div class="completion-info">
                    <h3 class="completion-title">
                        <i class="fas fa-chart-line"></i>
                        Team Profile Completion
                    </h3>
                    
                    ${this.renderNextMilestone()}
                    
                    <!-- Category Breakdown -->
                    <div class="completion-categories">
                        ${this.renderCategories()}
                    </div>
                    
                    <!-- Suggestions -->
                    ${this.renderSuggestions()}
                </div>
            </div>
        `;
        
        this.container.innerHTML = html;
    }
    
    getStatusBadge() {
        if (this.percentage >= 100) {
            return '<div class="status-badge complete"><i class="fas fa-trophy"></i> Perfect!</div>';
        } else if (this.percentage >= 80) {
            return '<div class="status-badge good"><i class="fas fa-star"></i> Almost There</div>';
        } else if (this.percentage >= 60) {
            return '<div class="status-badge fair"><i class="fas fa-check"></i> Good Progress</div>';
        } else {
            return '<div class="status-badge needs-work"><i class="fas fa-flag"></i> Getting Started</div>';
        }
    }
    
    renderNextMilestone() {
        if (!this.nextMilestone || this.percentage >= 100) {
            return '';
        }
        
        return `
            <div class="next-milestone">
                <div class="milestone-icon">
                    <i class="fas fa-${this.nextMilestone.icon}"></i>
                </div>
                <div class="milestone-info">
                    <div class="milestone-title">Next: ${this.nextMilestone.title}</div>
                    <div class="milestone-progress-bar">
                        <div class="milestone-progress-fill" style="width: ${(this.percentage / this.nextMilestone.percentage) * 100}%"></div>
                    </div>
                    <div class="milestone-text">${Math.round(this.nextMilestone.remaining)}% to go</div>
                </div>
            </div>
        `;
    }
    
    renderCategories() {
        const categories = {
            'basic_info': { icon: 'info-circle', label: 'Basic Info', color: '#00d9ff' },
            'branding': { icon: 'image', label: 'Branding', color: '#8b5cf6' },
            'roster': { icon: 'users', label: 'Roster', color: '#f59e0b' },
            'social': { icon: 'share-alt', label: 'Social Links', color: '#ec4899' },
            'captain_game_id': { icon: 'gamepad', label: 'Game ID', color: '#10b981' },
        };
        
        return Object.entries(categories).map(([key, config]) => {
            const score = this.breakdown[key] || 0;
            return `
                <div class="category-item">
                    <div class="category-header">
                        <div class="category-icon" style="color: ${config.color}">
                            <i class="fas fa-${config.icon}"></i>
                        </div>
                        <div class="category-label">${config.label}</div>
                        <div class="category-score">${score}%</div>
                    </div>
                    <div class="category-bar">
                        <div class="category-fill" style="width: 0%; background: ${config.color}" data-width="${score}%"></div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    renderSuggestions() {
        if (!this.suggestions || this.suggestions.length === 0) {
            return `
                <div class="completion-success">
                    <div class="success-icon">
                        <i class="fas fa-check-circle"></i>
                    </div>
                    <h4>Team Profile Complete!</h4>
                    <p>Your team profile is fully optimized and ready for competition.</p>
                </div>
            `;
        }
        
        // Sort by priority
        const priorityOrder = { 'high': 0, 'medium': 1, 'low': 2 };
        const sorted = [...this.suggestions].sort((a, b) => 
            priorityOrder[a.priority] - priorityOrder[b.priority]
        );
        
        return `
            <div class="completion-suggestions">
                <h4 class="suggestions-title">
                    <i class="fas fa-lightbulb"></i>
                    Actions to Improve
                </h4>
                <div class="suggestions-list">
                    ${sorted.map(suggestion => this.renderSuggestion(suggestion)).join('')}
                </div>
            </div>
        `;
    }
    
    renderSuggestion(suggestion) {
        const priorityClass = `priority-${suggestion.priority}`;
        const priorityIcon = {
            'high': 'exclamation-circle',
            'medium': 'info-circle',
            'low': 'lightbulb'
        }[suggestion.priority] || 'info-circle';
        
        return `
            <div class="suggestion-card ${priorityClass}">
                <div class="suggestion-icon">
                    <i class="fas fa-${suggestion.icon}"></i>
                </div>
                <div class="suggestion-content">
                    <div class="suggestion-header">
                        <h5>${suggestion.title}</h5>
                        <span class="suggestion-priority">
                            <i class="fas fa-${priorityIcon}"></i>
                            ${suggestion.priority}
                        </span>
                    </div>
                    <p>${suggestion.description}</p>
                    <a href="${suggestion.url}" class="suggestion-action">
                        ${suggestion.action}
                        <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
            </div>
        `;
    }
    
    animate() {
        // Animate percentage counter
        const percentageEl = this.container.querySelector('.completion-percentage');
        if (percentageEl) {
            this.animateCounter(percentageEl, 0, this.percentage, 2000);
        }
        
        // Animate circle progress
        const circle = this.container.querySelector('.circle-progress');
        if (circle) {
            const circumference = 2 * Math.PI * 85;
            const offset = circumference - (this.percentage / 100) * circumference;
            
            setTimeout(() => {
                circle.style.strokeDashoffset = offset;
            }, 100);
        }
        
        // Animate category bars
        const categoryFills = this.container.querySelectorAll('.category-fill');
        categoryFills.forEach((fill, index) => {
            const width = fill.dataset.width;
            setTimeout(() => {
                fill.style.width = width;
            }, 300 + (index * 100));
        });
    }
    
    animateCounter(element, start, end, duration) {
        const startTime = performance.now();
        
        const updateCounter = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing function (easeOutCubic)
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = Math.floor(start + (end - start) * easeOut);
            
            element.textContent = `${current}%`;
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        };
        
        requestAnimationFrame(updateCounter);
    }
    
    setupEventListeners() {
        // Add smooth scrolling to suggestion links
        const suggestionLinks = this.container.querySelectorAll('.suggestion-action');
        suggestionLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                // Allow default navigation but add visual feedback
                link.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    link.style.transform = 'scale(1)';
                }, 150);
            });
        });
    }
    
    showCelebration() {
        const celebration = document.createElement('div');
        celebration.className = 'completion-celebration';
        celebration.innerHTML = `
            <div class="celebration-content">
                <div class="celebration-icon">
                    <i class="fas fa-trophy"></i>
                </div>
                <h3>Perfect Profile!</h3>
                <p>Your team profile is 100% complete</p>
                <div class="confetti"></div>
            </div>
        `;
        
        document.body.appendChild(celebration);
        
        // Trigger animation
        requestAnimationFrame(() => {
            celebration.classList.add('active');
        });
        
        // Create confetti effect
        this.createConfetti(celebration.querySelector('.confetti'));
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            celebration.classList.remove('active');
            setTimeout(() => celebration.remove(), 500);
        }, 3000);
    }
    
    createConfetti(container) {
        const colors = ['#00d9ff', '#8b5cf6', '#f59e0b', '#ec4899', '#10b981'];
        
        for (let i = 0; i < 50; i++) {
            const confetto = document.createElement('div');
            confetto.className = 'confetto';
            confetto.style.left = `${Math.random() * 100}%`;
            confetto.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            confetto.style.animationDelay = `${Math.random() * 0.5}s`;
            confetto.style.animationDuration = `${2 + Math.random() * 2}s`;
            container.appendChild(confetto);
        }
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if completion data exists
    const completionContainer = document.getElementById('team-completion-widget');
    if (completionContainer && window.teamCompletionData) {
        new TeamCompletionWidget('team-completion-widget', window.teamCompletionData);
    }
});
