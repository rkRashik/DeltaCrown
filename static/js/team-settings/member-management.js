/**
 * Member Management System for Team Settings
 * Allows captains to manage team roster
 */

class MemberManagement {
  constructor(teamSlug, csrfToken) {
    this.teamSlug = teamSlug;
    this.csrfToken = csrfToken;
    this.members = [];
    this.selectedMembers = new Set();
    this.init();
  }

  async init() {
    await this.loadMembers();
    this.render();
    this.bindEvents();
  }

  async loadMembers() {
    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/members/`, {
        headers: {
          'X-CSRFToken': this.csrfToken
        }
      });
      const data = await response.json();
      
      if (data.success) {
        this.members = data.members;
      } else {
        this.showError(data.error || 'Failed to load members');
      }
    } catch (error) {
      console.error('Error loading members:', error);
      this.showError('Network error. Please try again.');
    }
  }

  render() {
    const container = document.getElementById('member-management-container');
    if (!container) return;

    // Group members by status
    const activeMembers = this.members.filter(m => m.status === 'ACTIVE');
    const substituteMembers = this.members.filter(m => m.status === 'SUBSTITUTE');
    const inactiveMembers = this.members.filter(m => m.status === 'INACTIVE' || m.status === 'REMOVED');

    container.innerHTML = `
      <div class="member-management">
        <!-- Header -->
        <div class="mm-header">
          <div class="mm-title-row">
            <h2>
              <i class="fa-solid fa-users-gear"></i>
              Team Roster Management
            </h2>
            <div class="mm-stats">
              <span class="stat-badge">
                <i class="fa-solid fa-user-check"></i>
                ${activeMembers.length} Active
              </span>
              <span class="stat-badge">
                <i class="fa-solid fa-user-clock"></i>
                ${substituteMembers.length} Subs
              </span>
            </div>
          </div>

          <!-- Actions Bar -->
          <div class="mm-actions-bar">
            <div class="search-box">
              <i class="fa-solid fa-search"></i>
              <input type="text" id="member-search" placeholder="Search members..." />
            </div>
            <div class="action-buttons">
              <button class="btn btn-secondary" id="bulk-remove-btn" disabled>
                <i class="fa-solid fa-trash"></i>
                Remove Selected (<span id="selected-count">0</span>)
              </button>
              <button class="btn btn-primary" id="invite-member-btn">
                <i class="fa-solid fa-user-plus"></i>
                Invite Member
              </button>
            </div>
          </div>
        </div>

        <!-- Active Members -->
        ${activeMembers.length > 0 ? `
          <div class="mm-section">
            <h3 class="section-title">
              <i class="fa-solid fa-shield"></i>
              Active Roster
            </h3>
            <div class="members-grid">
              ${activeMembers.map(member => this.renderMemberCard(member)).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Substitute Members -->
        ${substituteMembers.length > 0 ? `
          <div class="mm-section">
            <h3 class="section-title">
              <i class="fa-solid fa-user-clock"></i>
              Substitutes
            </h3>
            <div class="members-grid">
              ${substituteMembers.map(member => this.renderMemberCard(member)).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Inactive/Removed Members -->
        ${inactiveMembers.length > 0 ? `
          <div class="mm-section collapsed">
            <h3 class="section-title clickable" data-toggle="inactive-section">
              <i class="fa-solid fa-user-slash"></i>
              Inactive Members (${inactiveMembers.length})
              <i class="fa-solid fa-chevron-down toggle-icon"></i>
            </h3>
            <div class="members-grid" id="inactive-section" style="display: none;">
              ${inactiveMembers.map(member => this.renderMemberCard(member)).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  renderMemberCard(member) {
    const isCaptain = member.is_captain;
    const canEdit = !isCaptain;

    return `
      <div class="member-card ${isCaptain ? 'captain-card' : ''} ${member.status.toLowerCase()}" data-member-id="${member.id}">
        ${canEdit ? `
          <div class="member-checkbox">
            <input type="checkbox" class="member-select" data-member-id="${member.id}" />
          </div>
        ` : ''}

        ${isCaptain ? '<div class="captain-ribbon"><i class="fa-solid fa-crown"></i> CAPTAIN</div>' : ''}

        <div class="member-avatar">
          <img src="${member.avatar_url || '/static/img/user_avatar/default-avatar.png'}" 
               alt="${member.display_name}" />
          ${member.is_starter ? '<div class="starter-badge">STARTER</div>' : ''}
        </div>

        <div class="member-info">
          <h4 class="member-name">${this.escapeHtml(member.display_name)}</h4>
          <p class="member-username">@${this.escapeHtml(member.username)}</p>
          
          ${member.in_game_name ? `
            <p class="member-ign">
              <i class="fa-solid fa-gamepad"></i>
              ${this.escapeHtml(member.in_game_name)}
            </p>
          ` : ''}

          <div class="member-meta">
            <span class="role-badge role-${member.role.toLowerCase()}">
              ${this.escapeHtml(member.role)}
            </span>
            ${member.jersey_number ? `
              <span class="jersey-badge">#${member.jersey_number}</span>
            ` : ''}
          </div>

          <div class="member-stats">
            <span><i class="fa-solid fa-calendar"></i> Joined ${this.formatDate(member.joined_at)}</span>
            ${member.games_played > 0 ? `
              <span><i class="fa-solid fa-trophy"></i> ${member.games_played} Games</span>
            ` : ''}
          </div>
        </div>

        ${canEdit ? `
          <div class="member-actions">
            <button class="btn-icon" data-action="edit" data-member-id="${member.id}" title="Edit Role">
              <i class="fa-solid fa-pen"></i>
            </button>
            ${!isCaptain ? `
              <button class="btn-icon btn-promote" data-action="promote" data-member-id="${member.id}" title="Make Captain">
                <i class="fa-solid fa-crown"></i>
              </button>
              <button class="btn-icon btn-danger" data-action="remove" data-member-id="${member.id}" title="Remove">
                <i class="fa-solid fa-trash"></i>
              </button>
            ` : ''}
          </div>
        ` : ''}
      </div>
    `;
  }

  bindEvents() {
    // Search functionality
    const searchInput = document.getElementById('member-search');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => this.filterMembers(e.target.value));
    }

    // Member selection
    document.querySelectorAll('.member-select').forEach(checkbox => {
      checkbox.addEventListener('change', (e) => {
        const memberId = e.target.dataset.memberId;
        if (e.target.checked) {
          this.selectedMembers.add(memberId);
        } else {
          this.selectedMembers.delete(memberId);
        }
        this.updateSelectionUI();
      });
    });

    // Bulk remove button
    const bulkRemoveBtn = document.getElementById('bulk-remove-btn');
    if (bulkRemoveBtn) {
      bulkRemoveBtn.addEventListener('click', () => this.bulkRemoveMembers());
    }

    // Edit buttons
    document.querySelectorAll('[data-action="edit"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const memberId = e.currentTarget.dataset.memberId;
        this.showEditModal(memberId);
      });
    });

    // Promote buttons
    document.querySelectorAll('[data-action="promote"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const memberId = e.currentTarget.dataset.memberId;
        this.showPromoteModal(memberId);
      });
    });

    // Remove buttons
    document.querySelectorAll('[data-action="remove"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const memberId = e.currentTarget.dataset.memberId;
        this.showRemoveModal(memberId);
      });
    });

    // Toggle sections
    document.querySelectorAll('[data-toggle]').forEach(toggle => {
      toggle.addEventListener('click', (e) => {
        const targetId = e.currentTarget.dataset.toggle;
        const target = document.getElementById(targetId);
        const icon = e.currentTarget.querySelector('.toggle-icon');
        
        if (target) {
          const isHidden = target.style.display === 'none';
          target.style.display = isHidden ? 'grid' : 'none';
          icon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
        }
      });
    });
  }

  filterMembers(query) {
    const searchTerm = query.toLowerCase();
    document.querySelectorAll('.member-card').forEach(card => {
      const memberName = card.querySelector('.member-name')?.textContent.toLowerCase() || '';
      const memberUsername = card.querySelector('.member-username')?.textContent.toLowerCase() || '';
      const memberIGN = card.querySelector('.member-ign')?.textContent.toLowerCase() || '';
      
      const matches = memberName.includes(searchTerm) || 
                     memberUsername.includes(searchTerm) || 
                     memberIGN.includes(searchTerm);
      
      card.style.display = matches ? 'flex' : 'none';
    });
  }

  updateSelectionUI() {
    const count = this.selectedMembers.size;
    document.getElementById('selected-count').textContent = count;
    document.getElementById('bulk-remove-btn').disabled = count === 0;
  }

  showEditModal(memberId) {
    const member = this.members.find(m => m.id == memberId);
    if (!member) return;

    // TODO: Implement edit modal
    alert(`Edit ${member.display_name}'s role and details`);
  }

  async showPromoteModal(memberId) {
    const member = this.members.find(m => m.id == memberId);
    if (!member) return;

    if (!confirm(`Are you sure you want to transfer team captaincy to ${member.display_name}?\n\nThis will make you a regular player.`)) {
      return;
    }

    const password = prompt('Please enter your password to confirm:');
    if (!password) return;

    await this.transferCaptaincy(memberId, password);
  }

  async showRemoveModal(memberId) {
    const member = this.members.find(m => m.id == memberId);
    if (!member) return;

    const confirmation = prompt(
      `Are you sure you want to remove ${member.display_name} from the team?\n\n` +
      `This action cannot be undone.\n\n` +
      `Type "${member.username}" to confirm:`
    );

    if (confirmation === member.username) {
      await this.removeMember(memberId, confirmation);
    }
  }

  async removeMember(memberId, confirmation) {
    try {
      const formData = new FormData();
      formData.append('confirmation', confirmation);

      const response = await fetch(`/teams/api/${this.teamSlug}/members/${memberId}/remove/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.csrfToken
        },
        body: formData
      });

      const data = await response.json();

      if (data.success) {
        this.showSuccess(data.message);
        await this.loadMembers();
        this.render();
        this.bindEvents();
      } else {
        this.showError(data.error);
      }
    } catch (error) {
      console.error('Error removing member:', error);
      this.showError('Failed to remove member');
    }
  }

  async transferCaptaincy(memberId, password) {
    try {
      const formData = new FormData();
      formData.append('new_captain_id', memberId);
      formData.append('password', password);

      const response = await fetch(`/teams/api/${this.teamSlug}/members/transfer-captain/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.csrfToken
        },
        body: formData
      });

      const data = await response.json();

      if (data.success) {
        this.showSuccess(data.message + '\n\nReloading page...');
        setTimeout(() => window.location.reload(), 2000);
      } else {
        this.showError(data.error);
      }
    } catch (error) {
      console.error('Error transferring captaincy:', error);
      this.showError('Failed to transfer captaincy');
    }
  }

  async bulkRemoveMembers() {
    if (this.selectedMembers.size === 0) return;

    if (!confirm(`Remove ${this.selectedMembers.size} selected member(s)?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      const response = await fetch(`/teams/api/${this.teamSlug}/members/bulk-remove/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken
        },
        body: JSON.stringify({
          membership_ids: Array.from(this.selectedMembers)
        })
      });

      const data = await response.json();

      if (data.success) {
        this.showSuccess(data.message);
        this.selectedMembers.clear();
        await this.loadMembers();
        this.render();
        this.bindEvents();
      } else {
        this.showError(data.error);
      }
    } catch (error) {
      console.error('Error removing members:', error);
      this.showError('Failed to remove members');
    }
  }

  formatDate(dateString) {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    } catch {
      return 'Recently';
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  showSuccess(message) {
    alert('✓ ' + message);
  }

  showError(message) {
    alert('✗ ' + message);
  }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('member-management-container');
  if (container) {
    const teamSlug = container.dataset.teamSlug;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    
    if (teamSlug && csrfToken) {
      new MemberManagement(teamSlug, csrfToken);
    }
  }
});
