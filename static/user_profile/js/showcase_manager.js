/**
 * UP-PHASE14C: Showcase Manager (Vanilla JS + Tailwind)
 * Facebook-style About section management for user profiles.
 * 
 * Features:
 * - Toggle showcase sections on/off
 * - Set featured team/passport
 * - Add/remove highlights
 * - Dynamic UI updates (no page reload)
 * 
 * Dependencies:
 * - api_client.js (APIClient)
 * - Tailwind CSS (styling only)
 * 
 * NO Alpine.js - Pure Vanilla JavaScript
 */

class ShowcaseManager {
    constructor(apiClient) {
        this.api = apiClient;
        this.showcase = null;
        this.availableTeams = [];
        this.availablePassports = [];
        
        // Bind methods
        this.init = this.init.bind(this);
        this.loadShowcase = this.loadShowcase.bind(this);
        this.toggleSection = this.toggleSection.bind(this);
        this.setFeaturedTeam = this.setFeaturedTeam.bind(this);
        this.setFeaturedPassport = this.setFeaturedPassport.bind(this);
        this.addHighlight = this.addHighlight.bind(this);
        this.removeHighlight = this.removeHighlight.bind(this);
        this.renderUI = this.renderUI.bind(this);
    }
    
    /**
     * Initialize showcase manager
     * Called on settings page load
     */
    async init() {
        try {
            await this.loadShowcase();
            this.attachEventListeners();
            this.renderUI();
        } catch (error) {
            console.error('[ShowcaseManager] Init failed:', error);
            this.api.showToast('Failed to load showcase settings', 'error');
        }
    }
    
    /**
     * Load showcase configuration from API
     * GET /api/profile/showcase/
     */
    async loadShowcase() {
        try {
            const response = await this.api.get('/api/profile/showcase/');
            if (response.success) {
                this.showcase = response.showcase;
                this.availableTeams = response.available_teams || [];
                this.availablePassports = response.available_passports || [];
                return true;
            } else {
                throw new Error(response.message || 'Failed to load showcase');
            }
        } catch (error) {
            console.error('[ShowcaseManager] Load failed:', error);
            throw error;
        }
    }
    
    /**
     * Toggle section visibility
     * POST /api/profile/showcase/toggle/
     * 
     * @param {string} sectionSlug - Section identifier (e.g., 'demographics')
     */
    async toggleSection(sectionSlug) {
        try {
            const response = await this.api.post('/api/profile/showcase/toggle/', {
                section: sectionSlug
            });
            
            if (response.success) {
                // Update local state
                this.showcase.enabled_sections = response.enabled_sections;
                
                // Update UI
                this.updateSectionToggleUI(sectionSlug, response.enabled_sections.includes(sectionSlug));
                
                this.api.showToast('Section updated', 'success');
                return true;
            } else {
                throw new Error(response.message || 'Toggle failed');
            }
        } catch (error) {
            console.error('[ShowcaseManager] Toggle failed:', error);
            this.api.showToast('Failed to update section', 'error');
            return false;
        }
    }
    
    /**
     * Set featured team
     * POST /api/profile/showcase/featured-team/
     * 
     * @param {number} teamId - Team ID to feature
     * @param {string} customRole - Optional custom role label
     */
    async setFeaturedTeam(teamId, customRole = '') {
        try {
            const response = await this.api.post('/api/profile/showcase/featured-team/', {
                team_id: teamId,
                role: customRole
            });
            
            if (response.success) {
                this.showcase.featured_team_id = teamId;
                this.showcase.featured_team_role = customRole;
                
                this.api.showToast('Featured team updated', 'success');
                return true;
            } else {
                throw new Error(response.message || 'Failed to set featured team');
            }
        } catch (error) {
            console.error('[ShowcaseManager] Set featured team failed:', error);
            this.api.showToast(error.message || 'Failed to update featured team', 'error');
            return false;
        }
    }
    
    /**
     * Set featured passport (game)
     * POST /api/profile/showcase/featured-passport/
     * 
     * @param {number} passportId - GameProfile ID to feature
     */
    async setFeaturedPassport(passportId) {
        try {
            const response = await this.api.post('/api/profile/showcase/featured-passport/', {
                passport_id: passportId
            });
            
            if (response.success) {
                this.showcase.featured_passport_id = passportId;
                
                this.api.showToast('Featured game updated', 'success');
                return true;
            } else {
                throw new Error(response.message || 'Failed to set featured passport');
            }
        } catch (error) {
            console.error('[ShowcaseManager] Set featured passport failed:', error);
            this.api.showToast(error.message || 'Failed to update featured game', 'error');
            return false;
        }
    }
    
    /**
     * Add highlight to showcase
     * POST /api/profile/showcase/highlights/add/
     * 
     * @param {Object} highlight - Highlight data
     * @param {string} highlight.type - Type: tournament, achievement, milestone, custom
     * @param {string} highlight.title - Display title
     * @param {string} highlight.description - Optional description
     * @param {Object} highlight.metadata - Optional metadata (placement, prize, etc.)
     */
    async addHighlight(highlight) {
        try {
            const response = await this.api.post('/api/profile/showcase/highlights/add/', highlight);
            
            if (response.success) {
                // Reload showcase to get updated highlights
                await this.loadShowcase();
                this.renderHighlights();
                
                this.api.showToast('Highlight added', 'success');
                return true;
            } else {
                throw new Error(response.message || 'Failed to add highlight');
            }
        } catch (error) {
            console.error('[ShowcaseManager] Add highlight failed:', error);
            this.api.showToast(error.message || 'Failed to add highlight', 'error');
            return false;
        }
    }
    
    /**
     * Remove highlight from showcase
     * POST /api/profile/showcase/highlights/remove/
     * 
     * @param {string} itemId - Highlight item ID
     */
    async removeHighlight(itemId) {
        try {
            const response = await this.api.post('/api/profile/showcase/highlights/remove/', {
                item_id: itemId
            });
            
            if (response.success) {
                // Reload showcase to get updated highlights
                await this.loadShowcase();
                this.renderHighlights();
                
                this.api.showToast('Highlight removed', 'success');
                return true;
            } else {
                throw new Error(response.message || 'Failed to remove highlight');
            }
        } catch (error) {
            console.error('[ShowcaseManager] Remove highlight failed:', error);
            this.api.showToast(error.message || 'Failed to remove highlight', 'error');
            return false;
        }
    }
    
    /**
     * Attach event listeners to UI elements
     * Uses event delegation for dynamic elements
     */
    attachEventListeners() {
        const container = document.getElementById('showcase-settings');
        if (!container) {
            console.warn('[ShowcaseManager] Showcase settings container not found');
            return;
        }
        
        // Section toggle checkboxes
        container.addEventListener('change', (e) => {
            if (e.target.classList.contains('section-toggle')) {
                const section = e.target.dataset.section;
                this.toggleSection(section);
            }
        });
        
        // Featured team dropdown
        const teamSelect = document.getElementById('featured-team-select');
        if (teamSelect) {
            teamSelect.addEventListener('change', (e) => {
                const teamId = parseInt(e.target.value);
                if (teamId) {
                    const customRole = document.getElementById('featured-team-role')?.value || '';
                    this.setFeaturedTeam(teamId, customRole);
                }
            });
        }
        
        // Featured passport dropdown
        const passportSelect = document.getElementById('featured-passport-select');
        if (passportSelect) {
            passportSelect.addEventListener('change', (e) => {
                const passportId = parseInt(e.target.value);
                if (passportId) {
                    this.setFeaturedPassport(passportId);
                }
            });
        }
        
        // Add highlight button
        const addHighlightBtn = document.getElementById('add-highlight-btn');
        if (addHighlightBtn) {
            addHighlightBtn.addEventListener('click', () => {
                this.showAddHighlightModal();
            });
        }
        
        // Remove highlight buttons (event delegation)
        container.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-highlight-btn')) {
                const itemId = e.target.dataset.itemId;
                if (confirm('Remove this highlight?')) {
                    this.removeHighlight(itemId);
                }
            }
        });
    }
    
    /**
     * Render showcase UI sections
     * Updates DOM with current showcase state
     */
    renderUI() {
        this.renderSectionToggles();
        this.renderFeaturedTeam();
        this.renderFeaturedPassport();
        this.renderHighlights();
    }
    
    /**
     * Render section toggle checkboxes
     */
    renderSectionToggles() {
        const container = document.getElementById('section-toggles');
        if (!container || !this.showcase) return;
        
        const sections = [
            { slug: 'demographics', label: '📊 Demographics', description: 'Gender, age, nationality' },
            { slug: 'location', label: '📍 Location', description: 'Country, region, city' },
            { slug: 'featured_team', label: '⭐ Featured Team', description: 'Highlight your main team' },
            { slug: 'featured_passport', label: '🎮 Featured Game', description: 'Showcase your best game' },
            { slug: 'highlights', label: '🏆 Highlights', description: 'Achievements and milestones' }
        ];
        
        container.innerHTML = sections.map(section => `
            <div class="flex items-center justify-between p-4 rounded-lg bg-slate-800/40 border border-slate-700/30">
                <div class="flex-1">
                    <p class="text-sm font-semibold text-white">${section.label}</p>
                    <p class="text-xs text-slate-400">${section.description}</p>
                </div>
                <label class="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" class="section-toggle sr-only peer" 
                           data-section="${section.slug}"
                           ${this.showcase.enabled_sections.includes(section.slug) ? 'checked' : ''}>
                    <div class="w-11 h-6 bg-slate-700 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
            </div>
        `).join('');
    }
    
    /**
     * Render featured team dropdown
     */
    renderFeaturedTeam() {
        const select = document.getElementById('featured-team-select');
        if (!select || !this.availableTeams) return;
        
        select.innerHTML = `
            <option value="">None</option>
            ${this.availableTeams.map(team => `
                <option value="${team.id}" ${team.id === this.showcase.featured_team_id ? 'selected' : ''}>
                    ${team.name}
                </option>
            `).join('')}
        `;
    }
    
    /**
     * Render featured passport dropdown
     */
    renderFeaturedPassport() {
        const select = document.getElementById('featured-passport-select');
        if (!select || !this.availablePassports) return;
        
        select.innerHTML = `
            <option value="">None</option>
            ${this.availablePassports.map(passport => `
                <option value="${passport.id}" ${passport.id === this.showcase.featured_passport_id ? 'selected' : ''}>
                    ${passport.game_name} - ${passport.rank || 'Unranked'}
                </option>
            `).join('')}
        `;
    }
    
    /**
     * Render highlights list
     */
    renderHighlights() {
        const container = document.getElementById('highlights-list');
        if (!container || !this.showcase) return;
        
        if (!this.showcase.highlights || this.showcase.highlights.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8 text-slate-400">
                    <p class="text-sm">No highlights added yet</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.showcase.highlights.map(highlight => `
            <div class="flex items-start gap-3 p-4 rounded-lg bg-slate-800/40 border border-slate-700/30">
                <span class="text-2xl">
                    ${highlight.type === 'tournament' ? '🏆' : 
                      highlight.type === 'achievement' ? '⭐' : 
                      highlight.type === 'milestone' ? '🎯' : '📌'}
                </span>
                <div class="flex-1">
                    <p class="text-sm font-semibold text-white">${highlight.title}</p>
                    ${highlight.description ? `<p class="text-xs text-slate-400 mt-1">${highlight.description}</p>` : ''}
                    ${highlight.metadata?.placement ? `<span class="inline-block px-2 py-0.5 rounded text-xs bg-yellow-500/20 text-yellow-300 mt-1">${highlight.metadata.placement} Place</span>` : ''}
                </div>
                <button class="remove-highlight-btn text-red-400 hover:text-red-300 transition-colors text-xs"
                        data-item-id="${highlight.item_id}">
                    Remove
                </button>
            </div>
        `).join('');
    }
    
    /**
     * Update section toggle UI after state change
     */
    updateSectionToggleUI(sectionSlug, isEnabled) {
        const checkbox = document.querySelector(`.section-toggle[data-section="${sectionSlug}"]`);
        if (checkbox) {
            checkbox.checked = isEnabled;
        }
    }
    
    /**
     * Show add highlight inline form
     */
    showAddHighlightModal() {
        // Remove any existing inline form
        const existingForm = document.getElementById('highlight-inline-form');
        if (existingForm) {
            existingForm.remove();
            return;
        }

        // Find the container to insert the form (next to the add button)
        const addBtn = document.querySelector('[data-action="add-highlight"]') ||
                       document.querySelector('.add-highlight-btn');
        const container = addBtn ? addBtn.closest('.showcase-section, .highlights-section, .card, div') : document.body;

        const form = document.createElement('div');
        form.id = 'highlight-inline-form';
        form.className = 'p-4 mt-3 rounded-lg border border-gray-600 bg-gray-800/50';
        form.innerHTML = `
            <h4 class="text-sm font-semibold text-gray-200 mb-3">Add Highlight</h4>
            <div class="space-y-3">
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Type</label>
                    <select id="highlight-type-input" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200">
                        <option value="tournament">Tournament</option>
                        <option value="achievement">Achievement</option>
                        <option value="milestone">Milestone</option>
                        <option value="custom">Custom</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Title <span class="text-red-400">*</span></label>
                    <input type="text" id="highlight-title-input" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200" placeholder="Enter highlight title" />
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1">Description (optional)</label>
                    <input type="text" id="highlight-desc-input" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-200" placeholder="Brief description" />
                </div>
                <div class="flex gap-2 justify-end">
                    <button type="button" id="highlight-cancel-btn" class="px-3 py-1.5 text-sm rounded bg-gray-600 hover:bg-gray-500 text-gray-200">Cancel</button>
                    <button type="button" id="highlight-save-btn" class="px-3 py-1.5 text-sm rounded bg-blue-600 hover:bg-blue-500 text-white">Save</button>
                </div>
            </div>
        `;

        container.appendChild(form);

        // Focus the title input
        const titleInput = document.getElementById('highlight-title-input');
        if (titleInput) titleInput.focus();

        // Cancel button
        document.getElementById('highlight-cancel-btn').addEventListener('click', () => form.remove());

        // Save button
        document.getElementById('highlight-save-btn').addEventListener('click', () => {
            const type = document.getElementById('highlight-type-input').value;
            const title = document.getElementById('highlight-title-input').value.trim();
            const description = document.getElementById('highlight-desc-input').value.trim();

            if (!title) {
                if (window.Toast) window.Toast.warning('Please enter a highlight title');
                return;
            }

            this.addHighlight({ type, title, description, metadata: {} });
            form.remove();
            if (window.Toast) window.Toast.success('Highlight added!');
        });
    }
}

// Export for use in settings page
if (typeof window !== 'undefined') {
    window.ShowcaseManager = ShowcaseManager;
}
