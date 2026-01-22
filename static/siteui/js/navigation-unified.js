/**
 * Desktop Notification & Profile Dropdowns
 * Modern, professional dropdown system
 */
(function() {
  'use strict';

  const notifBtn = document.querySelector('[data-notif-toggle]');
  const profileBtn = document.querySelector('[data-profile-toggle]');
  let notifDropdown = null;
  let profileDropdown = null;

  // Create Notification Dropdown
  if (notifBtn) {
    notifDropdown = createNotificationDropdown();
    notifBtn.parentNode.appendChild(notifDropdown);

    notifBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      toggleDropdown(notifDropdown);
      closeDropdown(profileDropdown);
    });
  }

  // Create Profile Dropdown
  if (profileBtn) {
    profileDropdown = createProfileDropdown();
    profileBtn.parentNode.appendChild(profileDropdown);

    profileBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      toggleDropdown(profileDropdown);
      closeDropdown(notifDropdown);
    });
  }

  // Close on outside click
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.dc-desktop-dropdown')) {
      closeDropdown(notifDropdown);
      closeDropdown(profileDropdown);
    }
  });

  // Close on escape
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeDropdown(notifDropdown);
      closeDropdown(profileDropdown);
    }
  });

  // =================================================================
  // SCROLLING NAVBAR WITH GLASSY EFFECT
  // =================================================================
  
  const navbar = document.querySelector('.unified-nav-desktop');
  let lastScrollY = window.scrollY;
  let ticking = false;
  
  function updateNavbar() {
    const scrollY = window.scrollY;
    
    if (scrollY > 50) {
      navbar?.classList.add('scrolled');
    } else {
      navbar?.classList.remove('scrolled');
    }
    
    ticking = false;
  }
  
  function requestNavbarUpdate() {
    if (!ticking) {
      window.requestAnimationFrame(updateNavbar);
      ticking = true;
    }
  }
  
  window.addEventListener('scroll', requestNavbarUpdate, { passive: true });
  updateNavbar(); // Initial check

  // =================================================================
  // THEME TOGGLE SYSTEM
  // =================================================================
  
  const themeToggles = document.querySelectorAll('[data-theme-toggle]');
  
  // Load saved theme or default to dark
  const savedTheme = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  document.body.setAttribute('data-theme', savedTheme);
  
  // Set initial toggle states
  themeToggles.forEach(toggle => {
    toggle.checked = savedTheme === 'dark';
  });
  
  // Handle theme changes
  themeToggles.forEach(toggle => {
    toggle.addEventListener('change', function() {
      const newTheme = this.checked ? 'dark' : 'light';
      
      // Apply theme
      document.documentElement.setAttribute('data-theme', newTheme);
      document.body.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      
      // Sync all toggles
      themeToggles.forEach(t => {
        t.checked = this.checked;
      });
    });
  });

  /**
   * Create Notification Dropdown - Modern 2026 Design
   */
  function createNotificationDropdown() {
    const dropdown = document.createElement('div');
    dropdown.className = 'dc-desktop-dropdown dc-notif-dropdown';
    dropdown.innerHTML = `
      <div class="dc-notif-dropdown__header">
        <div class="dc-notif-dropdown__header-content">
          <div class="dc-notif-dropdown__icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
            </svg>
          </div>
          <div>
            <h3 class="dc-notif-dropdown__title">Notifications</h3>
            <p class="dc-notif-dropdown__subtitle">Stay updated with your activity</p>
          </div>
        </div>
        <button class="dc-notif-dropdown__mark-all" type="button">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <span>Mark all read</span>
        </button>
      </div>
      <div class="dc-notif-dropdown__list">
        <div class="dc-notif-dropdown__loading">
          <div class="dc-notif-dropdown__spinner"></div>
          <span>Loading notifications...</span>
        </div>
      </div>
      <div class="dc-notif-dropdown__footer">
        <a href="/notifications/" class="dc-notif-dropdown__view-all">
          <span>View all notifications</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        </a>
      </div>
    `;
    
    // Fetch notifications when dropdown is opened
    dropdown.addEventListener('transitionend', function(e) {
      if (e.propertyName === 'opacity' && dropdown.classList.contains('is-open')) {
        fetchNotifications(dropdown);
      }
    });
    
    // Mark all read handler
    const markAllBtn = dropdown.querySelector('.dc-notif-dropdown__mark-all');
    if (markAllBtn) {
      markAllBtn.addEventListener('click', function(e) {
        e.preventDefault();
        markAllNotificationsRead(dropdown);
      });
    }
    
    // Phase 4 Step 3: Event delegation for approve/reject buttons
    dropdown.addEventListener('click', function(e) {
      const btn = e.target.closest('[data-action][data-follow-request-id]');
      if (!btn) return;
      
      e.preventDefault();
      e.stopPropagation();
      
      const action = btn.getAttribute('data-action');
      const followRequestId = btn.getAttribute('data-follow-request-id');
      const notifId = btn.getAttribute('data-notif-id');
      
      handleFollowRequestAction(dropdown, action, followRequestId, notifId, btn);
    });
    
    return dropdown;
  }

  /**
   * Fetch notifications from API
   */
  async function fetchNotifications(dropdown) {
    const listEl = dropdown.querySelector('.dc-notif-dropdown__list');
    if (!listEl) return;
    
    try {
      const response = await fetch('/notifications/api/nav-preview/');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to load notifications');
      }
      
      renderNotifications(listEl, data.items);
      
    } catch (error) {
      console.error('Failed to fetch notifications:', error);
      listEl.innerHTML = `
        <div class="dc-notif-dropdown__error">
          <div class="dc-notif-dropdown__error-icon">
            <i class="fas fa-exclamation-circle"></i>
          </div>
          <div class="dc-notif-dropdown__error-text">Failed to load notifications</div>
        </div>
      `;
    }
  }

  /**
   * Render notification items - Modern 2026 Design
   */
  function renderNotifications(listEl, items) {
    if (!items || items.length === 0) {
      listEl.innerHTML = `
        <div class="dc-notif-dropdown__empty">
          <div class="dc-notif-dropdown__empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
              <line x1="10" y1="8" x2="14" y2="8"/>
            </svg>
          </div>
          <div class="dc-notif-dropdown__empty-text">No notifications yet</div>
          <div class="dc-notif-dropdown__empty-subtext">We'll notify you when something happens</div>
        </div>
      `;
      return;
    }
    
    listEl.innerHTML = items.map(item => {
      const unreadClass = !item.is_read ? 'is-unread' : '';
      
      // Check if this is a follow request notification
      const isFollowRequest = item.notification_type === 'follow_request';
      const linkUrl = isFollowRequest ? '/me/settings/#connections' : (item.url || '#');
      
      // Icon based on notification type
      let iconSvg = '';
      if (item.notification_type === 'follow_request') {
        iconSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>';
      } else if (item.notification_type === 'tournament_invite') {
        iconSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line></svg>';
      } else if (item.notification_type === 'team_invite') {
        iconSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path></svg>';
      } else {
        iconSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
      }
      
      const actionBtn = item.action_label && item.action_url ? `
        <a href="${item.action_url}" class="dc-notif-item__action-btn">
          ${escapeHtml(item.action_label)}
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </a>
      ` : '';
      
      return `
        <a href="${linkUrl}" class="dc-notif-item ${unreadClass}" data-notif-id="${item.id}">
          <div class="dc-notif-item__icon">
            ${iconSvg}
          </div>
          <div class="dc-notif-item__content">
            <div class="dc-notif-item__title">${escapeHtml(item.title)}</div>
            <div class="dc-notif-item__message">${escapeHtml(item.message)}</div>
            <div class="dc-notif-item__meta">
              <span class="dc-notif-item__time">${timeAgo(item.created_at)}</span>
              ${!item.is_read ? '<span class="dc-notif-item__unread-dot"></span>' : ''}
            </div>
          </div>
          ${actionBtn}
        </a>
      `;
    }).join('');
  }

  /**
   * Mark all notifications as read
   */
  async function markAllNotificationsRead(dropdown) {
    try {
      const response = await fetch('/notifications/mark-all-read/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      if (response.ok) {
        // Refresh notifications
        const listEl = dropdown.querySelector('.dc-notif-dropdown__list');
        if (listEl) {
          listEl.innerHTML = '<div class="dc-notif-dropdown__loading"><i class="fas fa-spinner fa-spin"></i></div>';
          await fetchNotifications(dropdown);
        }
        
        // Update badge
        const badge = document.querySelector('.unified-nav-desktop__badge');
        if (badge) {
          badge.style.display = 'none';
        }
        
        // Show toast if available
        if (window.showToast) {
          window.showToast({type: 'success', message: 'All notifications marked as read'});
        }
      }
    } catch (error) {
      console.error('Failed to mark all as read:', error);
    }
  }

  /**
   * Get CSRF token from cookie
   */
  function getCsrfToken() {
    const name = 'csrftoken';
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
    return cookieValue || '';
  }

  /**
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Format timestamp as "X minutes ago"
   */
  function timeAgo(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    return date.toLocaleDateString();
  }

  /**
   * Create Profile Dropdown
   */
  function createProfileDropdown() {
    const dropdown = document.createElement('div');
    dropdown.className = 'dc-desktop-dropdown dc-profile-dropdown';
    
    // Get user info from avatar button
    const avatarImg = profileBtn.querySelector('img');
    const username = avatarImg ? avatarImg.alt : 'User';
    const avatarUrl = avatarImg ? avatarImg.src : '/static/img/user_avatar/default-avatar.png';

    dropdown.innerHTML = `
      <div class="dc-profile-dropdown__header">
        <img src="${avatarUrl}" alt="${username}" class="dc-profile-dropdown__avatar">
        <div class="dc-profile-dropdown__info">
          <div class="dc-profile-dropdown__name">${username}</div>
          <div class="dc-profile-dropdown__username">@${username}</div>
        </div>
      </div>
      <div class="dc-profile-dropdown__menu">
        <a href="/u/${username}/" class="dc-profile-dropdown__item">
          <i class="fas fa-user dc-profile-dropdown__item-icon"></i>
          <span>My Profile</span>
        </a>
        <a href="/dashboard/" class="dc-profile-dropdown__item">
          <i class="fas fa-th-large dc-profile-dropdown__item-icon"></i>
          <span>Dashboard</span>
        </a>
        <a href="/user/me/settings/" class="dc-profile-dropdown__item">
          <i class="fas fa-cog dc-profile-dropdown__item-icon"></i>
          <span>Settings</span>
        </a>
        <a href="/notifications/" class="dc-profile-dropdown__item">
          <i class="fas fa-bell dc-profile-dropdown__item-icon"></i>
          <span>Notifications</span>
        </a>
        <div class="dc-profile-dropdown__divider"></div>
        <a href="/accounts/logout/" class="dc-profile-dropdown__item dc-profile-dropdown__item--danger">
          <i class="fas fa-sign-out-alt dc-profile-dropdown__item-icon"></i>
          <span>Sign Out</span>
        </a>
      </div>
    `;
    return dropdown;
  }

  /**
   * Toggle dropdown open/close
   */
  function toggleDropdown(dropdown) {
    if (!dropdown) return;
    const isOpen = dropdown.classList.contains('is-open');
    if (isOpen) {
      closeDropdown(dropdown);
    } else {
      openDropdown(dropdown);
    }
  }

  /**
   * Open dropdown
   */
  function openDropdown(dropdown) {
    if (!dropdown) return;
    dropdown.classList.add('is-open');
  }

  /**
   * Close dropdown
   */
  function closeDropdown(dropdown) {
    if (!dropdown) return;
    dropdown.classList.remove('is-open');
  }

})();
/**
 * UNIFIED NAVIGATION SYSTEM
 * Handles mobile drawer menu interactions
 */

(function() {
  'use strict';

  // Mobile menu elements
  const menuToggle = document.querySelector('[data-mobile-menu-toggle]');
  const menuClose = document.querySelector('[data-mobile-menu-close]');
  const drawer = document.querySelector('[data-mobile-drawer]');
  const backdrop = document.querySelector('[data-mobile-backdrop]');

  if (!menuToggle || !drawer || !backdrop) {
    return; // Exit if elements don't exist
  }

  /**
   * Open the mobile drawer menu
   */
  function openMenu() {
    drawer.classList.add('is-open');
    backdrop.classList.add('is-visible');
    document.body.style.overflow = 'hidden';
    
    // Update ARIA
    if (menuToggle) {
      menuToggle.setAttribute('aria-expanded', 'true');
      menuToggle.setAttribute('aria-label', 'Close menu');
    }
  }

  /**
   * Close the mobile drawer menu
   */
  function closeMenu() {
    drawer.classList.remove('is-open');
    backdrop.classList.remove('is-visible');
    document.body.style.overflow = '';
    
    // Update ARIA
    if (menuToggle) {
      menuToggle.setAttribute('aria-expanded', 'false');
      menuToggle.setAttribute('aria-label', 'Open menu');
    }
  }

  /**
   * Toggle menu open/closed
   */
  function toggleMenu() {
    if (drawer.classList.contains('is-open')) {
      closeMenu();
    } else {
      openMenu();
    }
  }

  // Event listeners
  if (menuToggle) {
    menuToggle.addEventListener('click', toggleMenu);
  }

  if (menuClose) {
    menuClose.addEventListener('click', closeMenu);
  }

  if (backdrop) {
    backdrop.addEventListener('click', closeMenu);
  }

  // Close menu on escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && drawer.classList.contains('is-open')) {
      closeMenu();
    }
  });

  // Close menu when navigation link is clicked (optional UX improvement)
  const drawerLinks = drawer.querySelectorAll('a');
  drawerLinks.forEach(function(link) {
    link.addEventListener('click', function() {
      // Small delay to allow navigation to start
      setTimeout(closeMenu, 150);
    });
  });

  // Handle window resize - close menu if switching to desktop
  let resizeTimer;
  window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
      if (window.innerWidth >= 1024 && drawer.classList.contains('is-open')) {
        closeMenu();
      }
    }, 250);
  });

  /**
   * Phase 4 Step 3: Handle approve/reject follow request actions in dropdown
   */
  async function handleFollowRequestAction(dropdown, action, followRequestId, notifId, btn) {
    // Disable all buttons in this notification item
    const notifItem = btn.closest('.dc-notif-dropdown__item');
    if (!notifItem) return;
    
    const allBtns = notifItem.querySelectorAll('[data-action]');
    allBtns.forEach(b => b.disabled = true);
    
    // Show loading state on clicked button
    const originalHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value 
      || document.querySelector('meta[name="csrf-token"]')?.content 
      || '';
    
    try {
      const response = await fetch(`/api/follow-requests/${followRequestId}/${action}/`, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken
        },
        credentials: 'same-origin'
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Action failed');
      }
      
      // Success - show toast
      const message = action === 'approve' 
        ? 'Follow request approved' 
        : 'Follow request rejected';
      
      if (window.showToast) {
        window.showToast({type: 'success', message: message});
      }
      
      // Refresh dropdown to update UI and counts
      if (window.DCNotifications && typeof window.DCNotifications.fetchPreview === 'function') {
        window.DCNotifications.fetchPreview(dropdown);
      }
      
    } catch (error) {
      console.error(`Error ${action}ing follow request:`, error);
      
      // Show error toast
      if (window.showToast) {
        window.showToast({
          type: 'error', 
          message: error.message || `Failed to ${action} request`
        });
      }
      
      // Re-enable buttons
      allBtns.forEach(b => b.disabled = false);
      btn.innerHTML = originalHtml;
    }
  }

})();

// ====================================
// Phase 4 Step 1.1: Public API for SSE Integration
// ====================================
window.DCNotifications = {
  /**
   * Refresh notification dropdown with latest data
   * Called by live_notifications.js when SSE updates counts
   */
  fetchPreview: function(dropdown) {
    if (!dropdown) return;
    
    // Find list element within dropdown
    const listEl = dropdown.querySelector('.dc-notif-dropdown__list');
    if (!listEl) return;
    
    // Show loading state
    listEl.innerHTML = '<div class="dc-notif-dropdown__loading">Refreshing...</div>';
    
    // Reuse getCsrfToken from the main module closure
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value 
      || document.querySelector('meta[name="csrf-token"]')?.content 
      || '';
    
    fetch('/notifications/api/nav-preview/', {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken
      },
      credentials: 'same-origin'
    })
      .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then(data => {
        if (!data.success) throw new Error(data.error || 'Unknown error');
        
        // Update pending count badge
        const pendingBadge = dropdown.querySelector('.dc-notif-dropdown__pending-badge');
        if (pendingBadge) {
          const count = data.pending_follow_requests || 0;
          pendingBadge.textContent = count;
          pendingBadge.style.display = count > 0 ? 'inline-flex' : 'none';
        }
        
        // Render items using same logic as main module
        if (!data.items || data.items.length === 0) {
          listEl.innerHTML = `
            <div class="dc-notif-dropdown__empty">
              <div class="dc-notif-dropdown__empty-icon">
                <i class="fas fa-bell-slash"></i>
              </div>
              <div class="dc-notif-dropdown__empty-text">No notifications yet</div>
            </div>
          `;
          return;
        }
        
        const escapeHtml = (str) => {
          const div = document.createElement('div');
          div.textContent = str;
          return div.innerHTML;
        };
        
        const timeAgo = (dateStr) => {
          const now = new Date();
          const then = new Date(dateStr);
          const seconds = Math.floor((now - then) / 1000);
          if (seconds < 60) return 'just now';
          const minutes = Math.floor(seconds / 60);
          if (minutes < 60) return `${minutes}m ago`;
          const hours = Math.floor(minutes / 60);
          if (hours < 24) return `${hours}h ago`;
          const days = Math.floor(hours / 24);
          if (days < 7) return `${days}d ago`;
          return `${Math.floor(days / 7)}w ago`;
        };
        
        listEl.innerHTML = data.items.map(item => {
          const unreadBg = !item.is_read ? 'bg-cyan-500/5 border-l-2 border-l-cyan-500' : '';
          
          // Phase 4 Step 4: Tailwind-first inline approve/reject for follow requests
          let actionBtn = '';
          if (item.type === 'follow_request' && item.follow_request_id) {
            actionBtn = `
              <div class="flex gap-2 mt-2 flex-wrap">
                <button class="px-3 py-1.5 text-sm font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:border-emerald-500/50 rounded-md transition-all disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-1.5" 
                        data-action="approve" 
                        data-follow-request-id="${item.follow_request_id}"
                        data-notif-id="${item.id}">
                  <i class="fas fa-check text-xs"></i> <span>Approve</span>
                </button>
                <button class="px-3 py-1.5 text-sm font-medium bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 hover:border-red-500/50 rounded-md transition-all disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-1.5" 
                        data-action="reject" 
                        data-follow-request-id="${item.follow_request_id}"
                        data-notif-id="${item.id}">
                  <i class="fas fa-times text-xs"></i> <span>Reject</span>
                </button>
              </div>
            `;
          } else if (item.action_label && item.action_url) {
            actionBtn = `
              <a href="${escapeHtml(item.action_url)}" class="mt-2 inline-flex items-center px-3 py-1.5 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-md text-sm font-medium transition-all">${escapeHtml(item.action_label)}</a>
            `;
          }
          
          return `
            <div class="p-4 border-b border-white/5 flex gap-3 items-start hover:bg-white/5 transition-colors ${unreadBg}" data-notif-id="${item.id}">
              <div class="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center bg-cyan-500/15 text-cyan-400">
                <i class="fas ${item.type === 'follow_request' ? 'fa-user-plus' : 'fa-bell'} text-sm"></i>
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-slate-100 mb-1 leading-snug">${escapeHtml(item.title)}</div>
                <div class="text-xs text-slate-300 mb-1.5 leading-relaxed line-clamp-2">${escapeHtml(item.message || item.body || '')}</div>
                <div class="text-xs text-slate-500">${timeAgo(item.created_at)}</div>
                ${actionBtn}
              </div>
            </div>
          `;
        }).join('');
      })
      .catch(error => {
        console.error('Error refreshing notification dropdown:', error);
        listEl.innerHTML = '<div class="dc-notif-dropdown__error">Failed to refresh</div>';
      });
  }
};
