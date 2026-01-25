/**
 * Organization Detail Page - Management UI
 * 
 * Handles tab switching, member management, and settings updates
 * using vanilla JavaScript + fetch API.
 * 
 * Performance: Optimized DOM updates, minimal reflows
 */

// ============================================================================
// STATE & CONFIGURATION
// ============================================================================

const state = {
    orgSlug: null,
    orgData: null,
    canManage: false,
    currentMemberId: null,
    csrfToken: null
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Load initial data
    state.orgData = window.ORG_DATA;
    state.canManage = window.CAN_MANAGE || false;
    state.orgSlug = state.orgData.org.slug;
    state.csrfToken = document.querySelector('meta[name="csrf-token"]').content;
    
    // Initialize UI
    initTabSwitching();
    initModals();
    renderMembers();
    renderTeams();
    initSettingsForm();
    
    // Event listeners
    if (state.canManage) {
        document.getElementById('addMemberBtn')?.addEventListener('click', showAddMemberModal);
        document.getElementById('addMemberForm').addEventListener('submit', handleAddMember);
        document.getElementById('changeRoleForm').addEventListener('submit', handleChangeRole);
        document.getElementById('confirmRemoveBtn').addEventListener('click', handleRemoveMember);
        document.getElementById('settingsForm').addEventListener('submit', handleUpdateSettings);
    }
});

// ============================================================================
// TAB SWITCHING
// ============================================================================

function initTabSwitching() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            
            // Update button states
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Show/hide content
            tabContents.forEach(content => {
                if (content.id === `${tabName}Tab`) {
                    content.classList.remove('hidden');
                } else {
                    content.classList.add('hidden');
                }
            });
        });
    });
}

// ============================================================================
// MEMBERS TAB
// ============================================================================

function renderMembers() {
    const tbody = document.getElementById('membersTableBody');
    if (!tbody) return;
    
    const members = state.orgData.members || [];
    
    if (members.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="px-6 py-8 text-center text-gray-400">
                    <i class="fas fa-users text-4xl mb-2 opacity-50"></i>
                    <p>No members yet</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = members.map(member => {
        const isCEO = member.role === 'CEO';
        const joinedDate = new Date(member.joined_at).toLocaleDateString();
        
        return `
            <tr class="hover:bg-gray-700/50 transition">
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center">
                        <div class="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center text-white font-bold">
                            ${member.username.charAt(0).toUpperCase()}
                        </div>
                        <div class="ml-4">
                            <div class="text-sm font-medium text-gray-100">${member.display_name}</div>
                            <div class="text-sm text-gray-400">@${member.username}</div>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleBadgeClass(member.role)}">
                        ${member.role}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                    ${joinedDate}
                </td>
                ${state.canManage ? `
                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    ${!isCEO ? `
                        <button onclick="showChangeRoleModal(${member.id}, '${member.role}')" class="text-cyan-400 hover:text-cyan-300 mr-3">
                            <i class="fas fa-edit"></i> Change Role
                        </button>
                        <button onclick="showRemoveMemberModal(${member.id}, '${member.username}')" class="text-red-400 hover:text-red-300">
                            <i class="fas fa-trash"></i> Remove
                        </button>
                    ` : `
                        <span class="text-gray-500 text-xs">
                            <i class="fas fa-lock"></i> Protected
                        </span>
                    `}
                </td>
                ` : ''}
            </tr>
        `;
    }).join('');
}

function getRoleBadgeClass(role) {
    const classes = {
        'CEO': 'bg-yellow-400/20 text-yellow-400 border border-yellow-400/30',
        'MANAGER': 'bg-purple-400/20 text-purple-400 border border-purple-400/30',
        'SCOUT': 'bg-blue-400/20 text-blue-400 border border-blue-400/30',
        'ANALYST': 'bg-green-400/20 text-green-400 border border-green-400/30'
    };
    return classes[role] || 'bg-gray-400/20 text-gray-400 border border-gray-400/30';
}

// ============================================================================
// TEAMS TAB
// ============================================================================

function renderTeams() {
    const grid = document.getElementById('teamsGrid');
    if (!grid) return;
    
    const teams = state.orgData.teams || [];
    
    if (teams.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full text-center py-12">
                <i class="fas fa-shield-alt text-gray-600 text-5xl mb-4"></i>
                <p class="text-gray-400 text-lg">No teams yet</p>
                <p class="text-gray-500 text-sm mt-2">Create your first team to get started!</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = teams.map(team => `
        <div class="bg-gray-800 rounded-lg p-6 hover:bg-gray-750 transition shadow-lg border border-gray-700">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-semibold text-white">${team.name}</h3>
                <span class="text-xs font-mono text-gray-400">[${team.tag}]</span>
            </div>
            <div class="space-y-2 text-sm">
                <div class="flex items-center text-gray-400">
                    <i class="fas fa-gamepad w-5"></i>
                    <span>${team.game_name}</span>
                </div>
                <div class="flex items-center text-gray-400">
                    <i class="fas fa-map-marker-alt w-5"></i>
                    <span>${team.region}</span>
                </div>
                <div class="flex items-center text-gray-400">
                    <i class="fas fa-users w-5"></i>
                    <span>${team.member_count} members</span>
                </div>
            </div>
            <a href="/teams/${team.slug}/" class="mt-4 block w-full text-center px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition">
                View Team
            </a>
        </div>
    `).join('');
}

// ============================================================================
// MODAL MANAGEMENT
// ============================================================================

function initModals() {
    // Close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[id$="Modal"]').forEach(modal => {
                modal.classList.add('hidden');
            });
        });
    });
    
    // Click outside to close
    document.querySelectorAll('[id$="Modal"]').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });
    });
}

function showAddMemberModal() {
    document.getElementById('addMemberModal').classList.remove('hidden');
    document.getElementById('newMemberUserId').value = '';
    document.getElementById('newMemberRole').value = 'MANAGER';
}

function showChangeRoleModal(memberId, currentRole) {
    document.getElementById('changeRoleModal').classList.remove('hidden');
    document.getElementById('changeMemberId').value = memberId;
    document.getElementById('changeRoleSelect').value = currentRole;
    state.currentMemberId = memberId;
}

function showRemoveMemberModal(memberId, username) {
    document.getElementById('confirmRemoveModal').classList.remove('hidden');
    document.getElementById('removeMemberName').textContent = username;
    state.currentMemberId = memberId;
}

// ============================================================================
// API CALLS
// ============================================================================

async function handleAddMember(e) {
    e.preventDefault();
    
    const userId = document.getElementById('newMemberUserId').value;
    const role = document.getElementById('newMemberRole').value;
    
    try {
        showLoading('Adding member...');
        
        const response = await fetch(`/api/vnext/orgs/${state.orgSlug}/members/add/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': state.csrfToken
            },
            body: JSON.stringify({ user_id: parseInt(userId), role })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to add member');
        }
        
        // Update state
        state.orgData.members = data.members;
        
        // Re-render
        renderMembers();
        
        // Close modal
        document.getElementById('addMemberModal').classList.add('hidden');
        
        showSuccess('Member added successfully!');
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

async function handleChangeRole(e) {
    e.preventDefault();
    
    const memberId = document.getElementById('changeMemberId').value;
    const newRole = document.getElementById('changeRoleSelect').value;
    
    try {
        showLoading('Updating role...');
        
        const response = await fetch(`/api/vnext/orgs/${state.orgSlug}/members/${memberId}/role/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': state.csrfToken
            },
            body: JSON.stringify({ role: newRole })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to update role');
        }
        
        // Update state
        const memberIndex = state.orgData.members.findIndex(m => m.id === parseInt(memberId));
        if (memberIndex !== -1) {
            state.orgData.members[memberIndex] = data.member;
        }
        
        // Re-render
        renderMembers();
        
        // Close modal
        document.getElementById('changeRoleModal').classList.add('hidden');
        
        showSuccess('Role updated successfully!');
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

async function handleRemoveMember() {
    const memberId = state.currentMemberId;
    
    try {
        showLoading('Removing member...');
        
        const response = await fetch(`/api/vnext/orgs/${state.orgSlug}/members/${memberId}/remove/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': state.csrfToken
            }
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to remove member');
        }
        
        // Update state
        state.orgData.members = data.members;
        
        // Re-render
        renderMembers();
        
        // Close modal
        document.getElementById('confirmRemoveModal').classList.add('hidden');
        
        showSuccess('Member removed successfully!');
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

// ============================================================================
// SETTINGS FORM
// ============================================================================

function initSettingsForm() {
    if (!state.canManage) return;
    
    // Populate form with current values
    const org = state.orgData.org;
    document.getElementById('logoUrl').value = org.logo_url || '';
    document.getElementById('bannerUrl').value = org.banner_url || '';
    document.getElementById('primaryColor').value = org.primary_color || '#667eea';
    document.getElementById('primaryColorHex').value = org.primary_color || '#667eea';
    document.getElementById('tagline').value = org.tagline || '';
    
    // Sync color inputs
    document.getElementById('primaryColor').addEventListener('input', (e) => {
        document.getElementById('primaryColorHex').value = e.target.value;
    });
    
    document.getElementById('primaryColorHex').addEventListener('input', (e) => {
        document.getElementById('primaryColor').value = e.target.value;
    });
}

async function handleUpdateSettings(e) {
    e.preventDefault();
    
    const formData = {
        logo_url: document.getElementById('logoUrl').value || null,
        banner_url: document.getElementById('bannerUrl').value || null,
        primary_color: document.getElementById('primaryColor').value || null,
        tagline: document.getElementById('tagline').value || null
    };
    
    try {
        showLoading('Saving settings...');
        
        const response = await fetch(`/api/vnext/orgs/${state.orgSlug}/settings/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': state.csrfToken
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'Failed to update settings');
        }
        
        // Update state
        state.orgData.org = data.org;
        
        showSuccess('Settings updated successfully!');
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

// ============================================================================
// UI FEEDBACK
// ============================================================================

function showError(message) {
    const banner = document.getElementById('errorBanner');
    document.getElementById('errorMessage').textContent = message;
    banner.classList.remove('hidden');
    setTimeout(() => banner.classList.add('hidden'), 5000);
}

function showSuccess(message) {
    const banner = document.getElementById('successBanner');
    document.getElementById('successMessage').textContent = message;
    banner.classList.remove('hidden');
    setTimeout(() => banner.classList.add('hidden'), 3000);
}

function showLoading(message) {
    // Could add a loading overlay here
    console.log('Loading:', message);
}

function hideLoading() {
    // Hide loading overlay
    console.log('Loading complete');
}

// Make functions globally accessible for onclick handlers
window.showChangeRoleModal = showChangeRoleModal;
window.showRemoveMemberModal = showRemoveMemberModal;
