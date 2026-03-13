/**
 * Command Center — Alpine.js State Engine v3
 * Reads Django-serialized JSON data, provides reactive UI methods,
 * and connects to SSE for real-time dashboard updates.
 */
document.addEventListener('alpine:init', () => {
  Alpine.data('dashboardEngine', () => {
    const el = document.getElementById('cc-data');
    const raw = el ? JSON.parse(el.textContent) : {};

    return {
      // ── Reactive State (hydrated from Django context) ──
      user:       raw.user       || { name: '', username: '', avatar: '', banner: '', isVerified: false, lftStatus: 'NOT_LOOKING', reputation: 0, level: 1, xp: 0 },
      wallet:     raw.wallet     || { balance: 0, pending: 0, currency: 'DC', bdtEquiv: 0, hasWallet: false, recentTxns: [] },
      actionItems: raw.actionItems || [],
      myOrgs:     raw.myOrgs     || [],
      teams:      raw.teams      || [],
      tournaments: raw.tournaments || [],
      inbox:      raw.inbox      || [],
      matches:    raw.matches    || [],
      matchStats: raw.matchStats || {},
      socialStats: raw.socialStats || {},
      unreadNotifCount: raw.unreadNotifCount || 0,

      // Extended state fields
      gamePassports:  raw.gamePassports  || [],
      badges:         raw.badges         || [],
      leaderboard:    raw.leaderboard    || [],
      lfpPositions:   raw.lfpPositions   || [],
      featuredProduct: raw.featuredProduct || null,
      recentOrders:   raw.recentOrders   || [],
      supportTickets: raw.supportTickets || [],
      inboxFilter:    raw.inboxFilter    || 'all',
      showLFT:        false,

      // Challenges & Bounties state
      challenges:     raw.challenges     || [],
      bounties:       raw.bounties       || [],

      // SSE state
      _sseSource: null,
      _sseRetryTimer: null,

      init() {
        this._startSSE();
      },

      destroy() {
        this._stopSSE();
      },

      // ── Computed ──

      get filteredInbox() {
        if (this.inboxFilter === 'all') return this.inbox;
        return this.inbox.filter(m => m.category === this.inboxFilter);
      },

      get activeChallengeCount() {
        return this.challenges.filter(c => ['OPEN', 'ACCEPTED', 'IN_PROGRESS'].includes(c.statusRaw)).length;
      },

      get activeBountyCount() {
        return this.bounties.filter(b => ['OPEN', 'ACCEPTED', 'IN_PROGRESS'].includes(b.statusRaw)).length;
      },

      // ── Methods ──

      dismissAction(id) {
        this.actionItems = this.actionItems.filter(item => item.id !== id);
      },

      markRead(id) {
        const msg = this.inbox.find(m => m.id === id);
        if (!msg) return;
        msg.unread = false;
        if (msg.notifId) {
          fetch('/notifications/' + msg.notifId + '/mark-read/', {
            method: 'POST',
            headers: { 'X-CSRFToken': this._csrf(), 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin',
          }).catch(e => console.warn('[CC] markRead failed', e));
        }
      },

      async handleInvite(inviteId, action) {
        try {
          const res = await fetch('/notifications/api/team-invite/' + inviteId + '/' + action + '/', {
            method: 'POST',
            headers: {
              'X-CSRFToken': this._csrf(),
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
          });
          const data = await res.json();
          if (data.success) {
            this.inbox = this.inbox.filter(m => m.inviteId != inviteId);
            this.actionItems = this.actionItems.filter(a => a.id !== 'inv-' + inviteId);
            if (window.showToast) {
              window.showToast({ type: 'success', message: 'Invite ' + action + 'ed successfully.' });
            }
          } else {
            if (window.showToast) {
              window.showToast({ type: 'error', message: data.error || 'Action failed.' });
            }
          }
        } catch (err) {
          console.error('[CC] handleInvite error:', err);
          if (window.showToast) {
            window.showToast({ type: 'error', message: 'Network error. Please try again.' });
          }
        }
      },

      async handleFollowRequest(requestId, action) {
        try {
          const res = await fetch('/notifications/api/follow-request/' + requestId + '/' + action + '/', {
            method: 'POST',
            headers: {
              'X-CSRFToken': this._csrf(),
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
          });
          const data = await res.json();
          if (data.success) {
            this.inbox = this.inbox.filter(m => m.followRequestId != requestId);
            if (window.showToast) {
              const verb = action === 'accept' ? 'accepted' : 'rejected';
              window.showToast({ type: 'success', message: 'Follow request ' + verb + '.' });
            }
          } else if (window.showToast) {
            window.showToast({ type: 'error', message: data.error || 'Action failed.' });
          }
        } catch (err) {
          console.error('[CC] handleFollowRequest error:', err);
          if (window.showToast) {
            window.showToast({ type: 'error', message: 'Network error. Please try again.' });
          }
        }
      },

      navigateAction(item) {
        if (item.btnUrl) {
          window.location.href = item.btnUrl;
        }
      },

      // ── SSE Real-time Updates ──

      _startSSE() {
        if (typeof EventSource === 'undefined') return;
        try {
          this._sseSource = new EventSource('/notifications/stream/');
          this._sseSource.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              if (typeof data.unread_notifications === 'number') {
                this.unreadNotifCount = data.unread_notifications;
              }
            } catch (e) {
              // ignore parse errors
            }
          };
          this._sseSource.onerror = () => {
            this._stopSSE();
            // Reconnect after 30s
            this._sseRetryTimer = setTimeout(() => this._startSSE(), 30000);
          };
        } catch (e) {
          console.warn('[CC] SSE init failed', e);
        }
      },

      _stopSSE() {
        if (this._sseSource) {
          this._sseSource.close();
          this._sseSource = null;
        }
        if (this._sseRetryTimer) {
          clearTimeout(this._sseRetryTimer);
          this._sseRetryTimer = null;
        }
      },

      _csrf() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.content;
        let v = '';
        document.cookie.split(';').forEach(c => {
          c = c.trim();
          if (c.startsWith('csrftoken=')) v = decodeURIComponent(c.substring(10));
        });
        return v;
      },
    };
  });
});
