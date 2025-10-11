/**
 * Sponsors Tab Component
 * Team sponsor management and display
 */

class SponsorsTab {
  constructor(api) {
    this.api = api;
    this.container = document.getElementById('sponsors-content');
    this.sponsors = [];
    this.currentFilter = 'all'; // all, gold, silver, bronze
    this.editMode = false;
  }

  async render() {
    if (!this.container) {
      console.error('Sponsors container not found');
      return;
    }

    // Show loading state
    this.container.innerHTML = this.getLoadingState();

    try {
      // Load sponsors data
      this.sponsors = await this.api.getSponsors();

      // Render the tab content
      this.container.innerHTML = this.getTabContent();

      // Attach event listeners
      this.attachEventListeners();
    } catch (error) {
      console.error('Error loading sponsors:', error);
      this.container.innerHTML = this.getErrorState();
    }
  }

  getTabContent() {
    const permissions = this.api.permissions;
    const filteredSponsors = this.getFilteredSponsors();
    
    return `
      <div class="sponsors-layout">
        <!-- Header -->
        <div class="sponsors-header">
          <div class="sponsors-header-left">
            <h2>
              <i class="fas fa-handshake"></i>
              Team Sponsors
            </h2>
            <p class="sponsors-subtitle">
              Our valued partners and supporters
            </p>
          </div>

          ${permissions.is_captain ? `
            <div class="sponsors-actions">
              ${!this.editMode ? `
                <button class="btn btn-secondary" data-action="toggle-edit">
                  <i class="fas fa-edit"></i>
                  Manage Sponsors
                </button>
                <button class="btn btn-primary" data-action="add-sponsor">
                  <i class="fas fa-plus"></i>
                  Add Sponsor
                </button>
              ` : `
                <button class="btn btn-success" data-action="toggle-edit">
                  <i class="fas fa-check"></i>
                  Done
                </button>
              `}
            </div>
          ` : ''}
        </div>

        <!-- Tier Filter -->
        ${this.sponsors.length > 0 ? `
          <div class="sponsors-filters">
            <button class="tier-filter ${this.currentFilter === 'all' ? 'active' : ''}" data-filter="all">
              All Sponsors
              <span class="filter-count">${this.sponsors.length}</span>
            </button>
            <button class="tier-filter tier-gold ${this.currentFilter === 'gold' ? 'active' : ''}" data-filter="gold">
              <i class="fas fa-trophy"></i>
              Gold
              <span class="filter-count">${this.sponsors.filter(s => s.tier === 'gold').length}</span>
            </button>
            <button class="tier-filter tier-silver ${this.currentFilter === 'silver' ? 'active' : ''}" data-filter="silver">
              <i class="fas fa-medal"></i>
              Silver
              <span class="filter-count">${this.sponsors.filter(s => s.tier === 'silver').length}</span>
            </button>
            <button class="tier-filter tier-bronze ${this.currentFilter === 'bronze' ? 'active' : ''}" data-filter="bronze">
              <i class="fas fa-award"></i>
              Bronze
              <span class="filter-count">${this.sponsors.filter(s => s.tier === 'bronze').length}</span>
            </button>
          </div>
        ` : ''}

        <!-- Sponsors Grid -->
        <div class="sponsors-grid">
          ${filteredSponsors.length > 0 
            ? this.renderSponsorsByTier(filteredSponsors)
            : this.getEmptyState()
          }
        </div>

        <!-- Stats Section -->
        ${this.sponsors.length > 0 ? `
          <div class="sponsors-stats">
            <div class="stat-card">
              <i class="fas fa-handshake"></i>
              <div class="stat-content">
                <span class="stat-value">${this.sponsors.length}</span>
                <span class="stat-label">Total Sponsors</span>
              </div>
            </div>
            <div class="stat-card">
              <i class="fas fa-trophy"></i>
              <div class="stat-content">
                <span class="stat-value">${this.sponsors.filter(s => s.tier === 'gold').length}</span>
                <span class="stat-label">Gold Partners</span>
              </div>
            </div>
            <div class="stat-card">
              <i class="fas fa-calendar"></i>
              <div class="stat-content">
                <span class="stat-value">${this.calculateTotalMonths()}</span>
                <span class="stat-label">Months Sponsored</span>
              </div>
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  getFilteredSponsors() {
    if (this.currentFilter === 'all') {
      return this.sponsors;
    }
    return this.sponsors.filter(s => s.tier === this.currentFilter);
  }

  renderSponsorsByTier(sponsors) {
    const tiers = ['gold', 'silver', 'bronze'];
    let html = '';

    tiers.forEach(tier => {
      const tierSponsors = sponsors.filter(s => s.tier === tier);
      
      if (tierSponsors.length > 0 || this.currentFilter === 'all') {
        html += `
          <div class="tier-section tier-${tier}">
            <div class="tier-header">
              <h3 class="tier-title">
                ${this.getTierIcon(tier)}
                ${this.getTierLabel(tier)} Sponsors
              </h3>
              <span class="tier-count">${tierSponsors.length}</span>
            </div>
            
            <div class="tier-sponsors ${this.getTierLayout(tier)}">
              ${tierSponsors.map(sponsor => this.renderSponsorCard(sponsor)).join('')}
            </div>
          </div>
        `;
      }
    });

    return html;
  }

  renderSponsorCard(sponsor) {
    const permissions = this.api.permissions;
    const startDate = new Date(sponsor.start_date);
    const endDate = sponsor.end_date ? new Date(sponsor.end_date) : null;
    const isActive = !endDate || endDate > new Date();
    
    return `
      <div class="sponsor-card tier-${sponsor.tier} ${isActive ? 'active' : 'expired'}" data-sponsor-id="${sponsor.id}">
        ${this.editMode && permissions.is_captain ? `
          <div class="sponsor-edit-controls">
            <button class="edit-btn" data-action="edit-sponsor" data-id="${sponsor.id}" title="Edit">
              <i class="fas fa-edit"></i>
            </button>
            <button class="delete-btn" data-action="delete-sponsor" data-id="${sponsor.id}" title="Remove">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        ` : ''}

        <div class="sponsor-logo-wrapper">
          ${sponsor.logo_url ? `
            <img src="${sponsor.logo_url}" 
                 alt="${this.escapeHtml(sponsor.name)}" 
                 class="sponsor-logo"
                 loading="lazy">
          ` : `
            <div class="sponsor-logo-placeholder">
              <i class="fas fa-building"></i>
            </div>
          `}
        </div>

        <div class="sponsor-info">
          <h4 class="sponsor-name">${this.escapeHtml(sponsor.name)}</h4>
          
          ${sponsor.description ? `
            <p class="sponsor-description">${this.escapeHtml(sponsor.description)}</p>
          ` : ''}

          <div class="sponsor-meta">
            <span class="sponsor-tier-badge tier-${sponsor.tier}">
              ${this.getTierIcon(sponsor.tier)}
              ${this.getTierLabel(sponsor.tier)}
            </span>
            
            <span class="sponsor-status ${isActive ? 'active' : 'expired'}">
              <i class="fas fa-circle"></i>
              ${isActive ? 'Active' : 'Expired'}
            </span>
          </div>

          ${sponsor.website ? `
            <a href="${sponsor.website}" 
               target="_blank" 
               rel="noopener noreferrer" 
               class="sponsor-website">
              <i class="fas fa-external-link-alt"></i>
              Visit Website
            </a>
          ` : ''}

          <div class="sponsor-dates">
            <span class="sponsor-date">
              <i class="fas fa-calendar-check"></i>
              Since ${startDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
            </span>
            ${endDate ? `
              <span class="sponsor-date">
                <i class="fas fa-calendar-xmark"></i>
                Until ${endDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
              </span>
            ` : `
              <span class="sponsor-date">
                <i class="fas fa-infinity"></i>
                Ongoing
              </span>
            `}
          </div>

          ${sponsor.benefits && sponsor.benefits.length > 0 ? `
            <div class="sponsor-benefits">
              <strong>Benefits:</strong>
              <ul>
                ${sponsor.benefits.map(benefit => `
                  <li>${this.escapeHtml(benefit)}</li>
                `).join('')}
              </ul>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  getTierIcon(tier) {
    const icons = {
      gold: '<i class="fas fa-trophy"></i>',
      silver: '<i class="fas fa-medal"></i>',
      bronze: '<i class="fas fa-award"></i>'
    };
    return icons[tier] || '<i class="fas fa-star"></i>';
  }

  getTierLabel(tier) {
    const labels = {
      gold: 'Gold',
      silver: 'Silver',
      bronze: 'Bronze'
    };
    return labels[tier] || tier;
  }

  getTierLayout(tier) {
    // Gold sponsors get larger cards
    if (tier === 'gold') return 'tier-layout-large';
    return 'tier-layout-normal';
  }

  calculateTotalMonths() {
    let total = 0;
    const now = new Date();
    
    this.sponsors.forEach(sponsor => {
      const start = new Date(sponsor.start_date);
      const end = sponsor.end_date ? new Date(sponsor.end_date) : now;
      const months = Math.floor((end - start) / (1000 * 60 * 60 * 24 * 30));
      total += months;
    });
    
    return total;
  }

  attachEventListeners() {
    const permissions = this.api.permissions;

    // Filter buttons
    this.container.querySelectorAll('[data-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.currentFilter = btn.dataset.filter;
        this.render();
      });
    });

    // Captain actions
    if (permissions.is_captain) {
      // Toggle edit mode
      const editToggle = this.container.querySelector('[data-action="toggle-edit"]');
      if (editToggle) {
        editToggle.addEventListener('click', () => {
          this.editMode = !this.editMode;
          this.render();
        });
      }

      // Add sponsor
      const addBtn = this.container.querySelector('[data-action="add-sponsor"]');
      if (addBtn) {
        addBtn.addEventListener('click', () => this.showAddSponsorModal());
      }

      // Edit sponsor (event delegation)
      this.container.querySelectorAll('[data-action="edit-sponsor"]').forEach(btn => {
        btn.addEventListener('click', () => {
          const sponsorId = btn.dataset.id;
          this.showEditSponsorModal(sponsorId);
        });
      });

      // Delete sponsor (event delegation)
      this.container.querySelectorAll('[data-action="delete-sponsor"]').forEach(btn => {
        btn.addEventListener('click', () => {
          const sponsorId = btn.dataset.id;
          this.deleteSponsor(sponsorId);
        });
      });
    }
  }

  showAddSponsorModal() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-content modal-large">
        <div class="modal-header">
          <h2>Add New Sponsor</h2>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <form id="add-sponsor-form">
            <div class="form-row">
              <div class="form-group">
                <label for="sponsor-name">Sponsor Name *</label>
                <input type="text" id="sponsor-name" class="form-control" 
                       placeholder="Company Name" required>
              </div>

              <div class="form-group">
                <label for="sponsor-tier">Tier *</label>
                <select id="sponsor-tier" class="form-control" required>
                  <option value="gold">Gold - Premium Partner</option>
                  <option value="silver">Silver - Major Partner</option>
                  <option value="bronze">Bronze - Supporting Partner</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label for="sponsor-description">Description</label>
              <textarea id="sponsor-description" class="form-control" rows="3" 
                        placeholder="Brief description of the sponsor..."></textarea>
            </div>

            <div class="form-group">
              <label for="sponsor-logo">Logo URL</label>
              <input type="url" id="sponsor-logo" class="form-control" 
                     placeholder="https://example.com/logo.png">
              <small class="form-help">Or upload an image file</small>
            </div>

            <div class="form-group">
              <label for="sponsor-website">Website</label>
              <input type="url" id="sponsor-website" class="form-control" 
                     placeholder="https://example.com">
            </div>

            <div class="form-row">
              <div class="form-group">
                <label for="sponsor-start-date">Start Date *</label>
                <input type="date" id="sponsor-start-date" class="form-control" 
                       value="${new Date().toISOString().split('T')[0]}" required>
              </div>

              <div class="form-group">
                <label for="sponsor-end-date">End Date</label>
                <input type="date" id="sponsor-end-date" class="form-control">
                <small class="form-help">Leave empty for ongoing</small>
              </div>
            </div>

            <div class="form-group">
              <label for="sponsor-benefits">Benefits (one per line)</label>
              <textarea id="sponsor-benefits" class="form-control" rows="4" 
                        placeholder="Logo on team jersey&#10;Social media mentions&#10;Tournament exposure"></textarea>
            </div>

            <div class="form-actions">
              <button type="button" class="btn btn-secondary modal-cancel">Cancel</button>
              <button type="submit" class="btn btn-primary">
                <i class="fas fa-plus"></i>
                Add Sponsor
              </button>
            </div>
          </form>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Event listeners
    const closeModal = () => modal.remove();
    
    modal.querySelector('.modal-close').addEventListener('click', closeModal);
    modal.querySelector('.modal-cancel').addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });

    modal.querySelector('#add-sponsor-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.handleAddSponsor(modal);
    });
  }

  showEditSponsorModal(sponsorId) {
    const sponsor = this.sponsors.find(s => s.id == sponsorId);
    if (!sponsor) return;

    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-content modal-large">
        <div class="modal-header">
          <h2>Edit Sponsor</h2>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <form id="edit-sponsor-form" data-sponsor-id="${sponsor.id}">
            <div class="form-row">
              <div class="form-group">
                <label for="edit-sponsor-name">Sponsor Name *</label>
                <input type="text" id="edit-sponsor-name" class="form-control" 
                       value="${this.escapeHtml(sponsor.name)}" required>
              </div>

              <div class="form-group">
                <label for="edit-sponsor-tier">Tier *</label>
                <select id="edit-sponsor-tier" class="form-control" required>
                  <option value="gold" ${sponsor.tier === 'gold' ? 'selected' : ''}>Gold</option>
                  <option value="silver" ${sponsor.tier === 'silver' ? 'selected' : ''}>Silver</option>
                  <option value="bronze" ${sponsor.tier === 'bronze' ? 'selected' : ''}>Bronze</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label for="edit-sponsor-description">Description</label>
              <textarea id="edit-sponsor-description" class="form-control" rows="3">${this.escapeHtml(sponsor.description || '')}</textarea>
            </div>

            <div class="form-group">
              <label for="edit-sponsor-website">Website</label>
              <input type="url" id="edit-sponsor-website" class="form-control" 
                     value="${sponsor.website || ''}">
            </div>

            <div class="form-actions">
              <button type="button" class="btn btn-secondary modal-cancel">Cancel</button>
              <button type="submit" class="btn btn-primary">
                <i class="fas fa-save"></i>
                Save Changes
              </button>
            </div>
          </form>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Event listeners
    const closeModal = () => modal.remove();
    
    modal.querySelector('.modal-close').addEventListener('click', closeModal);
    modal.querySelector('.modal-cancel').addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });

    modal.querySelector('#edit-sponsor-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.handleEditSponsor(modal);
    });
  }

  async handleAddSponsor(modal) {
    const form = modal.querySelector('#add-sponsor-form');
    const submitBtn = form.querySelector('button[type="submit"]');
    
    const data = {
      name: form.querySelector('#sponsor-name').value.trim(),
      tier: form.querySelector('#sponsor-tier').value,
      description: form.querySelector('#sponsor-description').value.trim(),
      logo_url: form.querySelector('#sponsor-logo').value.trim(),
      website: form.querySelector('#sponsor-website').value.trim(),
      start_date: form.querySelector('#sponsor-start-date').value,
      end_date: form.querySelector('#sponsor-end-date').value || null,
      benefits: form.querySelector('#sponsor-benefits').value
        .split('\n')
        .map(b => b.trim())
        .filter(b => b.length > 0)
    };

    try {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';

      await this.api.addSponsor(data);
      
      modal.remove();
      this.render(); // Reload sponsors
    } catch (error) {
      console.error('Error adding sponsor:', error);
      alert('Failed to add sponsor. Please try again.');
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-plus"></i> Add Sponsor';
    }
  }

  async handleEditSponsor(modal) {
    const form = modal.querySelector('#edit-sponsor-form');
    const sponsorId = form.dataset.sponsorId;
    const submitBtn = form.querySelector('button[type="submit"]');
    
    const data = {
      name: form.querySelector('#edit-sponsor-name').value.trim(),
      tier: form.querySelector('#edit-sponsor-tier').value,
      description: form.querySelector('#edit-sponsor-description').value.trim(),
      website: form.querySelector('#edit-sponsor-website').value.trim()
    };

    try {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

      await this.api.updateSponsor(sponsorId, data);
      
      modal.remove();
      this.render(); // Reload sponsors
    } catch (error) {
      console.error('Error updating sponsor:', error);
      alert('Failed to update sponsor. Please try again.');
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
    }
  }

  async deleteSponsor(sponsorId) {
    const sponsor = this.sponsors.find(s => s.id == sponsorId);
    if (!sponsor) return;

    if (!confirm(`Are you sure you want to remove ${sponsor.name} as a sponsor?`)) {
      return;
    }

    try {
      await this.api.deleteSponsor(sponsorId);
      this.render(); // Reload sponsors
    } catch (error) {
      console.error('Error deleting sponsor:', error);
      alert('Failed to remove sponsor. Please try again.');
    }
  }

  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  getLoadingState() {
    return SkeletonLoaders.list(3, SkeletonLoaders.sponsorCard());
  }

  getEmptyState() {
    const permissions = this.api.permissions;
    return `
      <div class="empty-state">
        <i class="fas fa-handshake"></i>
        <h3>No sponsors yet</h3>
        <p>This team doesn't have any sponsors at the moment.</p>
        ${permissions.is_captain ? `
          <button class="btn btn-primary" data-action="add-sponsor">
            <i class="fas fa-plus"></i>
            Add First Sponsor
          </button>
        ` : ''}
      </div>
    `;
  }

  getErrorState() {
    return `
      <div class="error-state">
        <i class="fas fa-exclamation-circle"></i>
        <h3>Failed to load sponsors</h3>
        <p>Please try again later.</p>
        <button class="btn btn-primary" onclick="location.reload()">
          <i class="fas fa-refresh"></i>
          Retry
        </button>
      </div>
    `;
  }
}
