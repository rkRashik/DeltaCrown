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

function initialsFrom(name) {
    const text = (name || '').trim();
    if (!text) return 'TM';
    return text
        .split(/\s+/)
        .slice(0, 2)
        .map((part) => part.charAt(0).toUpperCase())
        .join('');
}

function formatTimeAgo(isoDate) {
    if (!isoDate) return '';
    const time = new Date(isoDate).getTime();
    if (!time) return '';

    const seconds = Math.max(1, Math.floor((Date.now() - time) / 1000));
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

function showToast(message, type = 'success') {
    const host = document.getElementById('inviteToastHost');
    if (!host) {
        alert(message);
        return;
    }

    const toast = document.createElement('div');
    toast.className = 'invite-toast invite-toast-' + type;
    toast.textContent = message;
    host.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('visible'));
    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 220);
    }, 2600);
}

function setCardBusy(card, busy) {
    if (!card) return;
    const buttons = card.querySelectorAll('button');
    buttons.forEach((btn) => {
        btn.disabled = busy;
        btn.classList.toggle('opacity-60', busy);
        btn.classList.toggle('cursor-not-allowed', busy);
    });
}

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
    const teamInitials = initialsFrom(invite.team_name);
    const teamLogo = invite.team_logo || `https://ui-avatars.com/api/?name=${encodeURIComponent(teamInitials)}&background=151530&color=E5E7EB&size=88&bold=true`;
    const gameLine = invite.game_name ? `
                        <div class="inline-flex items-center gap-2 rounded-full bg-white/5 px-2.5 py-1 border border-white/10 text-[11px] text-gray-300">
                            ${invite.game_icon ? `<img src="${escapeHtml(invite.game_icon)}" class="w-3.5 h-3.5 rounded" alt="${escapeHtml(invite.game_name)}">` : '<i class="fas fa-gamepad text-[10px] text-cyan-300"></i>'}
                            <span>${escapeHtml(invite.game_name)}</span>
                        </div>` : '';
    
    return `
        <div class="invite-card glass-panel rounded-2xl p-5" id="membership-${invite.id}">
            <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-5">
                <div class="flex-1 min-w-0">
                    <div class="flex items-start gap-4">
                        <img src="${teamLogo}" alt="${escapeHtml(invite.team_name)}" class="w-14 h-14 rounded-xl object-cover border border-white/15 bg-black/30 shrink-0">
                        <div class="min-w-0 flex-1">
                            <div class="flex flex-wrap items-center gap-2 mb-2">
                                <h3 class="text-xl font-bold text-white truncate">${escapeHtml(invite.team_name)}</h3>
                                <span class="badge badge-pending">${escapeHtml(invite.role)}</span>
                            </div>
                            <div class="flex flex-wrap items-center gap-2.5 text-sm text-gray-400">
                                ${gameLine}
                                ${invite.inviter_name ? `<span class="inline-flex items-center gap-1.5"><i class="fas fa-user text-[11px] text-cyan-300"></i> Invited by <strong class="text-gray-200 font-semibold">${escapeHtml(invite.inviter_name)}</strong></span>` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="mt-3 text-xs text-gray-500 flex items-center gap-2">
                        <i class="far fa-clock text-[11px]"></i>
                        <span>${formatTimeAgo(invite.created_at)} · ${createdDate}</span>
                    </div>
                </div>
                <div class="flex items-center gap-2 md:pt-1">
                    <button 
                        onclick="acceptMembershipInvite(${invite.id})"
                        class="action-btn action-btn-primary px-4 py-2 rounded-lg"
                    >
                        <i class="fas fa-check mr-2"></i>Accept Invite
                    </button>
                    <button 
                        onclick="declineMembershipInvite(${invite.id})"
                        class="action-btn action-btn-ghost px-4 py-2 rounded-lg"
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
    const teamInitials = initialsFrom(invite.team_name);
    const teamLogo = invite.team_logo || `https://ui-avatars.com/api/?name=${encodeURIComponent(teamInitials)}&background=25182f&color=E5E7EB&size=88&bold=true`;
    const gameLine = invite.game_name ? `
                        <div class="inline-flex items-center gap-2 rounded-full bg-white/5 px-2.5 py-1 border border-white/10 text-[11px] text-gray-300">
                            ${invite.game_icon ? `<img src="${escapeHtml(invite.game_icon)}" class="w-3.5 h-3.5 rounded" alt="${escapeHtml(invite.game_name)}">` : '<i class="fas fa-gamepad text-[10px] text-pink-300"></i>'}
                            <span>${escapeHtml(invite.game_name)}</span>
                        </div>` : '';
    
    return `
        <div class="invite-card glass-panel rounded-2xl p-5" id="email-${invite.token}">
            <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-5">
                <div class="flex-1 min-w-0">
                    <div class="flex items-start gap-4">
                        <img src="${teamLogo}" alt="${escapeHtml(invite.team_name)}" class="w-14 h-14 rounded-xl object-cover border border-white/15 bg-black/30 shrink-0">
                        <div class="min-w-0 flex-1">
                            <div class="flex flex-wrap items-center gap-2 mb-2">
                                <h3 class="text-xl font-bold text-white truncate">${escapeHtml(invite.team_name)}</h3>
                                <span class="badge badge-pending">${escapeHtml(invite.role)}</span>
                                <span class="badge badge-email">Email Invite</span>
                            </div>
                            <div class="flex flex-wrap items-center gap-2.5 text-sm text-gray-400 mb-2">
                                ${gameLine}
                                <span class="inline-flex items-center gap-1.5"><i class="fas fa-envelope text-[11px] text-pink-300"></i> ${escapeHtml(invite.invited_email)}</span>
                            </div>
                            <div class="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                                ${invite.inviter_name ? `<span><i class="fas fa-user mr-1"></i>Invited by ${escapeHtml(invite.inviter_name)}</span>` : ''}
                                <span><i class="far fa-clock mr-1"></i>${formatTimeAgo(invite.created_at)} · ${createdDate}</span>
                                ${expiresDate ? `<span class="text-amber-300"><i class="fas fa-hourglass-half mr-1"></i>Expires ${expiresDate}</span>` : ''}
                            </div>
                        </div>
                    </div>
                </div>
                <div class="flex items-center gap-2 md:pt-1">
                    <button 
                        onclick="acceptEmailInvite('${invite.token}')"
                        class="action-btn action-btn-primary px-4 py-2 rounded-lg"
                    >
                        <i class="fas fa-check mr-2"></i>Accept Invite
                    </button>
                    <button 
                        onclick="declineEmailInvite('${invite.token}')"
                        class="action-btn action-btn-ghost px-4 py-2 rounded-lg"
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
    setCardBusy(card, true);
    
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
            showToast('Invite accepted. Redirecting to team hub.', 'success');
            card.classList.add('fade-out');
            setTimeout(() => {
                // Redirect to team page
                window.location.href = data.data.team_url;
            }, 500);
        } else {
            showToast(data.safe_message || 'Failed to accept invitation', 'error');
            setCardBusy(card, false);
        }
    } catch (error) {
        console.error('Accept error:', error);
        showToast('Network error. Please try again.', 'error');
        setCardBusy(card, false);
    }
}

async function declineMembershipInvite(id) {
    if (!confirm('Are you sure you want to decline this invitation?')) {
        return;
    }
    
    const config = getConfig();
    const card = document.getElementById(`membership-${id}`);
    setCardBusy(card, true);
    
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
            showToast('Invite declined.', 'info');
            card.classList.add('fade-out');
            setTimeout(() => {
                card.remove();
                // Update count
                const count = document.querySelectorAll('#membershipList .invite-card').length;
                document.getElementById('membershipCount').textContent = count;
                if (count === 0) {
                    document.getElementById('membershipEmpty').classList.remove('hidden');
                    document.getElementById('membershipList').classList.add('hidden');
                }
            }, 500);
        } else {
            showToast(data.safe_message || 'Failed to decline invitation', 'error');
            setCardBusy(card, false);
        }
    } catch (error) {
        console.error('Decline error:', error);
        showToast('Network error. Please try again.', 'error');
        setCardBusy(card, false);
    }
}

async function acceptEmailInvite(token) {
    const config = getConfig();
    const card = document.getElementById(`email-${token}`);
    setCardBusy(card, true);
    
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
            showToast('Invite accepted. Redirecting to team hub.', 'success');
            card.classList.add('fade-out');
            setTimeout(() => {
                window.location.href = data.data.team_url;
            }, 500);
        } else {
            showToast(data.safe_message || 'Failed to accept invitation', 'error');
            setCardBusy(card, false);
        }
    } catch (error) {
        console.error('Accept error:', error);
        showToast('Network error. Please try again.', 'error');
        setCardBusy(card, false);
    }
}

async function declineEmailInvite(token) {
    if (!confirm('Are you sure you want to decline this invitation?')) {
        return;
    }
    
    const config = getConfig();
    const card = document.getElementById(`email-${token}`);
    setCardBusy(card, true);
    
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
            showToast('Invite declined.', 'info');
            card.classList.add('fade-out');
            setTimeout(() => {
                card.remove();
                const count = document.querySelectorAll('#emailList .invite-card').length;
                document.getElementById('emailCount').textContent = count;
                if (count === 0) {
                    document.getElementById('emailEmpty').classList.remove('hidden');
                    document.getElementById('emailList').classList.add('hidden');
                }
            }, 500);
        } else {
            showToast(data.safe_message || 'Failed to decline invitation', 'error');
            setCardBusy(card, false);
        }
    } catch (error) {
        console.error('Decline error:', error);
        showToast('Network error. Please try again.', 'error');
        setCardBusy(card, false);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    showToast(message, 'error');
}

// Load invites on page load
document.addEventListener('DOMContentLoaded', loadInvites);
