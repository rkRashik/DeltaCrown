/**
 * Team Invites Dashboard - vNext
 * 
 * Handles loading and managing team invitations (membership-based and email-based).
 * Uses vNext API endpoints for all operations.
 * 
 * Config provided via window.VNEXT_INVITES_CONFIG
 */

let currentTab = 'membership';
let invitesData = null;

// Get URL from config or fallback to hardcoded
function getConfig() {
    return window.VNEXT_INVITES_CONFIG || {
        listUrl: '/api/vnext/teams/invites/',
        acceptMembershipUrlTemplate: '/api/vnext/teams/invites/membership/{id}/accept/',
        declineMembershipUrlTemplate: '/api/vnext/teams/invites/membership/{id}/decline/',
        acceptEmailUrlTemplate: '/api/vnext/teams/invites/email/{token}/accept/',
        declineEmailUrlTemplate: '/api/vnext/teams/invites/email/{token}/decline/'
    };
}

function switchTab(tab) {
    currentTab = tab;
    
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`.tab-button[data-tab="${tab}"]`).classList.add('active');
    
    // Update tab content
    document.getElementById('membershipTab').classList.toggle('hidden', tab !== 'membership');
    document.getElementById('emailTab').classList.toggle('hidden', tab !== 'email');
}

function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') return value;
    }
    return '';
}

async function loadInvites() {
    const config = getConfig();
    
    try {
        const response = await fetch(config.listUrl, {
            headers: {
                'Accept': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (!data.ok) {
            showError('Failed to load invitations');
            return;
        }
        
        invitesData = data.data;
        renderMembershipInvites(invitesData.membership_invites);
        renderEmailInvites(invitesData.email_invites);
        
        // Update counts
        document.getElementById('membershipCount').textContent = invitesData.membership_invites.length;
        document.getElementById('emailCount').textContent = invitesData.email_invites.length;
        
    } catch (error) {
        console.error('Load invites error:', error);
        showError('Network error loading invitations');
    }
}

function renderMembershipInvites(invites) {
    const loading = document.getElementById('membershipLoading');
    const empty = document.getElementById('membershipEmpty');
    const list = document.getElementById('membershipList');
    
    loading.classList.add('hidden');
    
    if (invites.length === 0) {
        empty.classList.remove('hidden');
        list.classList.add('hidden');
    } else {
        empty.classList.add('hidden');
        list.classList.remove('hidden');
        list.innerHTML = invites.map(invite => createMembershipCard(invite)).join('');
    }
}

function renderEmailInvites(invites) {
    const loading = document.getElementById('emailLoading');
    const empty = document.getElementById('emailEmpty');
    const list = document.getElementById('emailList');
    
    loading.classList.add('hidden');
    
    if (invites.length === 0) {
        empty.classList.remove('hidden');
        list.classList.add('hidden');
    } else {
        empty.classList.add('hidden');
        list.classList.remove('hidden');
        list.innerHTML = invites.map(invite => createEmailCard(invite)).join('');
    }
}

function createMembershipCard(invite) {
    const createdDate = new Date(invite.created_at).toLocaleDateString();
    
    return `
        <div class="invite-card glass-panel rounded-xl p-5" id="membership-${invite.id}">
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <div class="flex items-center gap-3 mb-2">
                        <h3 class="text-xl font-bold text-white">${escapeHtml(invite.team_name)}</h3>
                        <span class="badge badge-pending">${escapeHtml(invite.role)}</span>
                    </div>
                    <div class="space-y-1 text-sm text-gray-400">
                        <p><i class="fas fa-gamepad mr-2"></i>${escapeHtml(invite.game_name)}</p>
                        ${invite.inviter_name ? `<p><i class="fas fa-user mr-2"></i>Invited by ${escapeHtml(invite.inviter_name)}</p>` : ''}
                        <p><i class="fas fa-calendar mr-2"></i>Invited on ${createdDate}</p>
                    </div>
                </div>
                <div class="flex gap-2">
                    <button 
                        onclick="acceptMembershipInvite(${invite.id})"
                        class="px-4 py-2 bg-gradient-to-r from-[#6C00FF] to-[#00E5FF] text-white rounded-lg hover:opacity-90 transition"
                    >
                        <i class="fas fa-check mr-2"></i>Accept
                    </button>
                    <button 
                        onclick="declineMembershipInvite(${invite.id})"
                        class="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
                    >
                        <i class="fas fa-times mr-2"></i>Decline
                    </button>
                </div>
            </div>
        </div>
    `;
}

function createEmailCard(invite) {
    const createdDate = new Date(invite.created_at).toLocaleDateString();
    const expiresDate = invite.expires_at ? new Date(invite.expires_at).toLocaleDateString() : null;
    
    return `
        <div class="invite-card glass-panel rounded-xl p-5" id="email-${invite.token}">
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <div class="flex items-center gap-3 mb-2">
                        <h3 class="text-xl font-bold text-white">${escapeHtml(invite.team_name)}</h3>
                        <span class="badge badge-pending">${escapeHtml(invite.role)}</span>
                    </div>
                    <div class="space-y-1 text-sm text-gray-400">
                        <p><i class="fas fa-gamepad mr-2"></i>${escapeHtml(invite.game_name)}</p>
                        <p><i class="fas fa-envelope mr-2"></i>${escapeHtml(invite.invited_email)}</p>
                        ${invite.inviter_name ? `<p><i class="fas fa-user mr-2"></i>Invited by ${escapeHtml(invite.inviter_name)}</p>` : ''}
                        <p><i class="fas fa-calendar mr-2"></i>Invited on ${createdDate}</p>
                        ${expiresDate ? `<p><i class="fas fa-clock mr-2"></i>Expires on ${expiresDate}</p>` : ''}
                    </div>
                </div>
                <div class="flex gap-2">
                    <button 
                        onclick="acceptEmailInvite('${invite.token}')"
                        class="px-4 py-2 bg-gradient-to-r from-[#6C00FF] to-[#00E5FF] text-white rounded-lg hover:opacity-90 transition"
                    >
                        <i class="fas fa-check mr-2"></i>Accept
                    </button>
                    <button 
                        onclick="declineEmailInvite('${invite.token}')"
                        class="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
                    >
                        <i class="fas fa-times mr-2"></i>Decline
                    </button>
                </div>
            </div>
        </div>
    `;
}

async function acceptMembershipInvite(id) {
    const config = getConfig();
    const card = document.getElementById(`membership-${id}`);
    const buttons = card.querySelectorAll('button');
    buttons.forEach(btn => btn.disabled = true);
    
    try {
        const url = config.acceptMembershipUrlTemplate.replace('{id}', id);
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.ok) {
            card.classList.add('fade-out');
            setTimeout(() => {
                // Redirect to team page
                window.location.href = data.data.team_url;
            }, 500);
        } else {
            alert(data.safe_message || 'Failed to accept invitation');
            buttons.forEach(btn => btn.disabled = false);
        }
    } catch (error) {
        console.error('Accept error:', error);
        alert('Network error. Please try again.');
        buttons.forEach(btn => btn.disabled = false);
    }
}

async function declineMembershipInvite(id) {
    if (!confirm('Are you sure you want to decline this invitation?')) {
        return;
    }
    
    const config = getConfig();
    const card = document.getElementById(`membership-${id}`);
    const buttons = card.querySelectorAll('button');
    buttons.forEach(btn => btn.disabled = true);
    
    try {
        const url = config.declineMembershipUrlTemplate.replace('{id}', id);
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.ok) {
            card.classList.add('fade-out');
            setTimeout(() => {
                card.remove();
                // Update count
                const count = document.querySelectorAll('#membershipList .invite-card').length - 1;
                document.getElementById('membershipCount').textContent = count;
                if (count === 0) {
                    document.getElementById('membershipEmpty').classList.remove('hidden');
                    document.getElementById('membershipList').classList.add('hidden');
                }
            }, 500);
        } else {
            alert(data.safe_message || 'Failed to decline invitation');
            buttons.forEach(btn => btn.disabled = false);
        }
    } catch (error) {
        console.error('Decline error:', error);
        alert('Network error. Please try again.');
        buttons.forEach(btn => btn.disabled = false);
    }
}

async function acceptEmailInvite(token) {
    const config = getConfig();
    const card = document.getElementById(`email-${token}`);
    const buttons = card.querySelectorAll('button');
    buttons.forEach(btn => btn.disabled = true);
    
    try {
        const url = config.acceptEmailUrlTemplate.replace('{token}', token);
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.ok) {
            card.classList.add('fade-out');
            setTimeout(() => {
                window.location.href = data.data.team_url;
            }, 500);
        } else {
            alert(data.safe_message || 'Failed to accept invitation');
            buttons.forEach(btn => btn.disabled = false);
        }
    } catch (error) {
        console.error('Accept error:', error);
        alert('Network error. Please try again.');
        buttons.forEach(btn => btn.disabled = false);
    }
}

async function declineEmailInvite(token) {
    if (!confirm('Are you sure you want to decline this invitation?')) {
        return;
    }
    
    const config = getConfig();
    const card = document.getElementById(`email-${token}`);
    const buttons = card.querySelectorAll('button');
    buttons.forEach(btn => btn.disabled = true);
    
    try {
        const url = config.declineEmailUrlTemplate.replace('{token}', token);
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.ok) {
            card.classList.add('fade-out');
            setTimeout(() => {
                card.remove();
                const count = document.querySelectorAll('#emailList .invite-card').length - 1;
                document.getElementById('emailCount').textContent = count;
                if (count === 0) {
                    document.getElementById('emailEmpty').classList.remove('hidden');
                    document.getElementById('emailList').classList.add('hidden');
                }
            }, 500);
        } else {
            alert(data.safe_message || 'Failed to decline invitation');
            buttons.forEach(btn => btn.disabled = false);
        }
    } catch (error) {
        console.error('Decline error:', error);
        alert('Network error. Please try again.');
        buttons.forEach(btn => btn.disabled = false);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    alert(message);
}

// Load invites on page load
document.addEventListener('DOMContentLoaded', loadInvites);
