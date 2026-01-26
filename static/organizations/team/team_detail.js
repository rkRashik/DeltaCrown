/**
 * Team Detail Page - Vanilla JavaScript
 * 
 * Handles roster management, member add/remove/update, and settings.
 * Pure vanilla JS with fetch API for AJAX calls.
 * 
 * State management:
 * - window.TEAM_DATA: Team data from Django (team, members, invites)
 * - window.CAN_MANAGE: Permission flag from Django
 * - window.CSRF_TOKEN: CSRF token for POST requests
 */

// State object
const state = {
    teamSlug: null,
    teamData: null,
    canManage: false,
    currentMemberId: null,
    csrfToken: null,
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    // Load initial state from window variables
    state.teamData = window.TEAM_DATA;
    state.canManage = window.CAN_MANAGE;
    state.csrfToken = window.CSRF_TOKEN;
    state.teamSlug = state.teamData.team.slug;
    
    // Initialize tab switching
    initTabs();
    
    // Render initial roster
    renderRoster();
    
    // Initialize event listeners
    if (state.canManage) {
        initModals();
        initForms();
    }
});

// ============================================================================
// TAB SWITCHING
// ============================================================================

function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.id.replace('tab-', '');
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    // Update button states
    document.querySelectorAll('.tab-button').forEach(btn => {
        const btnTabId = btn.id.replace('tab-', '');
        if (btnTabId === tabId) {
            btn.classList.remove('border-transparent', 'text-gray-400');
            btn.classList.add('border-blue-500', 'text-blue-400');
        } else {
            btn.classList.remove('border-blue-500', 'text-blue-400');
            btn.classList.add('border-transparent', 'text-gray-400');
        }
    });
    
    // Update content visibility
    document.querySelectorAll('.tab-content').forEach(content => {
        const contentTabId = content.id.replace('content-', '');
        if (contentTabId === tabId) {
            content.classList.remove('hidden');
        } else {
            content.classList.add('hidden');
        }
    });
}

// ============================================================================
// ROSTER RENDERING
// ============================================================================

function renderRoster() {
    const rosterList = document.getElementById('roster-list');
    const members = state.teamData.members;
    
    if (members.length === 0) {
        rosterList.innerHTML = '<p class="text-gray-400">No members yet</p>';
        return;
    }
    
    rosterList.innerHTML = members.map(member => `
        <div class="bg-gray-700 rounded-lg p-4 flex items-center justify-between">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 bg-gray-600 rounded-full flex items-center justify-center text-xl font-bold">
                    ${member.username.charAt(0).toUpperCase()}
                </div>
                
                <div>
                    <div class="flex items-center gap-2">
                        <span class="font-semibold text-white">${escapeHtml(member.username)}</span>
                        ${member.is_tournament_captain ? '<span class="px-2 py-0.5 bg-yellow-600 text-white text-xs font-bold rounded">CAPTAIN</span>' : ''}
                    </div>
                    
                    <div class="flex items-center gap-2 mt-1 text-sm text-gray-400">
                        <span class="px-2 py-0.5 ${getRoleBadgeColor(member.role)} text-white text-xs font-bold rounded">${member.role}</span>
                        ${member.roster_slot ? `<span class="text-gray-500">•</span><span>${member.roster_slot}</span>` : ''}
                        <span class="text-gray-500">•</span>
                        <span>Joined ${formatDate(member.joined_date)}</span>
                    </div>
                </div>
            </div>
            
            ${state.canManage && member.role !== 'OWNER' ? `
                <div class="flex gap-2">
                    <button onclick="openChangeRoleModal(${member.id}, '${escapeHtml(member.username)}', '${member.role}', '${member.roster_slot || ''}')" class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded transition">
                        Change Role
                    </button>
                    <button onclick="openRemoveMemberModal(${member.id}, '${escapeHtml(member.username)}')" class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded transition">
                        Remove
                    </button>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function getRoleBadgeColor(role) {
    const colors = {
        'OWNER': 'bg-purple-600',
        'MANAGER': 'bg-blue-600',
        'COACH': 'bg-green-600',
        'PLAYER': 'bg-cyan-600',
        'SUBSTITUTE': 'bg-teal-600',
        'ANALYST': 'bg-orange-600',
        'SCOUT': 'bg-gray-600',
    };
    return colors[role] || 'bg-gray-600';
}

function formatDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'today';
    if (diffDays === 1) return 'yesterday';
    if (diffDays < 30) return `${diffDays} days ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================================================
// MODAL MANAGEMENT
// ============================================================================

function initModals() {
    // Add Member Modal
    document.getElementById('btn-add-member')?.addEventListener('click', openAddMemberModal);
    document.getElementById('close-add-member')?.addEventListener('click', closeAddMemberModal);
    document.getElementById('cancel-add-member')?.addEventListener('click', closeAddMemberModal);
    
    // Change Role Modal
    document.getElementById('close-change-role')?.addEventListener('click', closeChangeRoleModal);
    document.getElementById('cancel-change-role')?.addEventListener('click', closeChangeRoleModal);
    
    // Remove Member Modal
    document.getElementById('close-remove-member')?.addEventListener('click', closeRemoveMemberModal);
    document.getElementById('cancel-remove-member')?.addEventListener('click', closeRemoveMemberModal);
    
    // Click outside to close
    document.getElementById('modal-add-member')?.addEventListener('click', (e) => {
        if (e.target.id === 'modal-add-member') closeAddMemberModal();
    });
    document.getElementById('modal-change-role')?.addEventListener('click', (e) => {
        if (e.target.id === 'modal-change-role') closeChangeRoleModal();
    });
    document.getElementById('modal-remove-member')?.addEventListener('click', (e) => {
        if (e.target.id === 'modal-remove-member') closeRemoveMemberModal();
    });
}

function openAddMemberModal() {
    document.getElementById('modal-add-member').classList.remove('hidden');
    document.getElementById('form-add-member').reset();
}

function closeAddMemberModal() {
    document.getElementById('modal-add-member').classList.add('hidden');
}

function openChangeRoleModal(memberId, username, currentRole, currentSlot) {
    state.currentMemberId = memberId;
    document.getElementById('change-role-username').textContent = username;
    document.getElementById('input-new-role').value = currentRole;
    document.getElementById('input-new-slot').value = currentSlot || '';
    document.getElementById('modal-change-role').classList.remove('hidden');
}

function closeChangeRoleModal() {
    document.getElementById('modal-change-role').classList.add('hidden');
    state.currentMemberId = null;
}

function openRemoveMemberModal(memberId, username) {
    state.currentMemberId = memberId;
    document.getElementById('remove-member-username').textContent = username;
    document.getElementById('modal-remove-member').classList.remove('hidden');
}

function closeRemoveMemberModal() {
    document.getElementById('modal-remove-member').classList.add('hidden');
    state.currentMemberId = null;
}

// ============================================================================
// FORM HANDLERS
// ============================================================================

function initForms() {
    // Add Member Form
    document.getElementById('form-add-member')?.addEventListener('submit', handleAddMember);
    
    // Change Role Form
    document.getElementById('form-change-role')?.addEventListener('submit', handleChangeRole);
    
    // Remove Member Confirmation
    document.getElementById('confirm-remove-member')?.addEventListener('click', handleRemoveMember);
    
    // Settings Form
    document.getElementById('settings-form')?.addEventListener('submit', handleUpdateSettings);
}

async function handleAddMember(e) {
    e.preventDefault();
    
    const userLookup = document.getElementById('input-user-lookup').value.trim();
    const role = document.getElementById('input-role').value;
    const slot = document.getElementById('input-slot').value;
    
    if (!userLookup || !role) {
        showError('User and role are required');
        return;
    }
    
    try {
        const response = await fetch(`/api/vnext/teams/${state.teamSlug}/members/add/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': state.csrfToken,
            },
            body: JSON.stringify({
                user_lookup: userLookup,
                role: role,
                slot: slot || null,
                is_active: true,
            }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.message || 'Failed to add member');
            return;
        }
        
        // Update state with new member list
        state.teamData.members = data.members;
        
        // Re-render roster
        renderRoster();
        
        // Close modal and show success
        closeAddMemberModal();
        showSuccess('Member added successfully');
        
    } catch (error) {
        console.error('Error adding member:', error);
        showError('Network error. Please try again.');
    }
}

async function handleChangeRole(e) {
    e.preventDefault();
    
    const role = document.getElementById('input-new-role').value;
    const slot = document.getElementById('input-new-slot').value;
    
    try {
        const response = await fetch(`/api/vnext/teams/${state.teamSlug}/members/${state.currentMemberId}/role/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': state.csrfToken,
            },
            body: JSON.stringify({
                role: role,
                slot: slot || null,
            }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.message || 'Failed to update role');
            return;
        }
        
        // Update member in state
        const memberIndex = state.teamData.members.findIndex(m => m.id === state.currentMemberId);
        if (memberIndex !== -1) {
            state.teamData.members[memberIndex] = data.member;
        }
        
        // Re-render roster
        renderRoster();
        
        // Close modal and show success
        closeChangeRoleModal();
        showSuccess('Member role updated successfully');
        
    } catch (error) {
        console.error('Error updating role:', error);
        showError('Network error. Please try again.');
    }
}

async function handleRemoveMember() {
    try {
        const response = await fetch(`/api/vnext/teams/${state.teamSlug}/members/${state.currentMemberId}/remove/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': state.csrfToken,
            },
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.message || 'Failed to remove member');
            return;
        }
        
        // Update state with new member list
        state.teamData.members = data.members;
        
        // Re-render roster
        renderRoster();
        
        // Close modal and show success
        closeRemoveMemberModal();
        showSuccess('Member removed successfully');
        
    } catch (error) {
        console.error('Error removing member:', error);
        showError('Network error. Please try again.');
    }
}

async function handleUpdateSettings(e) {
    e.preventDefault();
    
    const region = document.getElementById('input-region').value.trim();
    const server = document.getElementById('input-server').value.trim();
    const description = document.getElementById('input-description').value.trim();
    
    try {
        const response = await fetch(`/api/vnext/teams/${state.teamSlug}/settings/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': state.csrfToken,
            },
            body: JSON.stringify({
                region: region,
                description: description,
                preferred_server: server,
            }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            showError(data.message || 'Failed to update settings');
            return;
        }
        
        // Update team data in state
        state.teamData.team = data.team;
        
        showSuccess('Settings updated successfully');
        
    } catch (error) {
        console.error('Error updating settings:', error);
        showError('Network error. Please try again.');
    }
}

// ============================================================================
// UI FEEDBACK
// ============================================================================

function showError(message) {
    const banner = document.getElementById('error-banner');
    const messageEl = document.getElementById('error-message');
    
    messageEl.textContent = message;
    banner.classList.remove('hidden');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        banner.classList.add('hidden');
    }, 5000);
}

function showSuccess(message) {
    const banner = document.getElementById('success-banner');
    const messageEl = document.getElementById('success-message');
    
    messageEl.textContent = message;
    banner.classList.remove('hidden');
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        banner.classList.add('hidden');
    }, 3000);
}
