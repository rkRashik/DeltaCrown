/**
 * Command Center — Alpine.js State Engine v3
 * Reads Django-serialized JSON data, provides reactive UI methods,
 * and polls lightweight notification counts for near-real-time updates.
 */
document.addEventListener('alpine:init', () => {
  Alpine.data('dashboardEngine', () => {
    const el = document.getElementById('cc-data');
    const raw = el ? JSON.parse(el.textContent) : {};

    return {
      // ── Reactive State (hydrated from Django context) ──
      user:       raw.user       || { name: '', username: '', avatar: '', banner: '', isVerified: false, lftStatus: 'NOT_LOOKING', reputation: 0, level: 1, xp: 0 },
      wallet:     raw.wallet     || { balance: 0, pending: 0, currency: 'DC', bdtEquiv: 0, hasWallet: false, recentTxns: [] },
      matchLobbyAlert: raw.matchLobbyAlert || null,
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

      // Competitive intelligence state
      challenges:     raw.challenges     || [],
      bounties:       raw.bounties       || [],
      myOperations:   raw.myOperations   || [],
      competitiveLoading: false,
      competitiveError: '',
      teamApplications: raw.teamApplications || [],
      teamApplicationsLoading: false,
      teamApplicationsError: '',

      // Polling state
      _notifPollTimer: null,
      _clockTimer: null,

      init() {
        this._refreshRelativeTimes();
        this._startClockUpdates();
        this._startNotifPolling();
        this.loadCompetitiveOperations();
        this.loadTeamApplications();
      },

      destroy() {
        this._stopClockUpdates();
        this._stopNotifPolling();
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

      get competitiveNeedsAction() {
        return this._operationsByState('needs_action');
      },

      get competitiveUnderReview() {
        return this._operationsByState('review');
      },

      get competitiveWaiting() {
        return this._operationsByState('waiting');
      },

      get competitiveCompleted() {
        return this._operationsByState('completed');
      },

      get competitivePriority() {
        const seen = new Set();
        const ordered = [
          ...this.competitiveNeedsAction,
          ...this.competitiveUnderReview,
          ...this._operationsByState('upcoming'),
          ...this.competitiveWaiting,
          ...this.competitiveCompleted,
        ];
        return ordered.filter((op) => {
          const key = `${op.type || 'op'}:${op.id}`;
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });
      },

      get competitiveGuidance() {
        if (this.competitiveLoading && this.myOperations.length === 0) {
          return 'Loading your current competitive priorities.';
        }
        if (this.competitiveNeedsAction.length) {
          return `${this.competitiveNeedsAction.length} operation${this.competitiveNeedsAction.length === 1 ? '' : 's'} need action now.`;
        }
        if (this.competitiveUnderReview.length) {
          return 'Some results or proof are under review. Track progress from the Dispute Center.';
        }
        if (this.competitivePriority.length) {
          return 'Your active operations are stable. Keep an eye on Match Room and proof deadlines.';
        }
        if (this.teams.length) {
          return 'No active competitive operations. Start with a Showdown, Mission, Bounty, or Dropzone reservation.';
        }
        return 'Join or create a team to unlock team-based competitive operations.';
      },

      // ── Methods ──

      dismissAction(id) {
        this.actionItems = this.actionItems.filter(item => item.id !== id);
      },

      dismissMatchLobbyAlert() {
        this.matchLobbyAlert = null;
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

      navigateTo(url) {
        if (url) window.location.href = url;
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

      async loadTeamApplications() {
        this.teamApplicationsLoading = true;
        this.teamApplicationsError = '';
        try {
          const res = await fetch('/api/vnext/me/team-applications/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin',
          });
          const data = await res.json();
          if (!res.ok || !data.success) {
            throw new Error(data.error || 'Unable to load team applications.');
          }
          this.teamApplications = Array.isArray(data.results) ? data.results : [];
        } catch (err) {
          console.warn('[CC] team applications failed', err);
          this.teamApplicationsError = err && err.message ? err.message : 'Unable to load team applications.';
        } finally {
          this.teamApplicationsLoading = false;
        }
      },

      async loadCompetitiveOperations() {
        this.competitiveLoading = true;
        this.competitiveError = '';
        try {
          const res = await fetch('/api/v1/competitive/my-operations/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin',
          });
          const data = await res.json();
          if (!res.ok) {
            throw new Error(data.detail || data.error || 'Unable to load competitive operations.');
          }
          const results = Array.isArray(data.results) ? data.results : (Array.isArray(data.operations) ? data.operations : []);
          this.myOperations = results;
        } catch (err) {
          console.warn('[CC] competitive operations failed', err);
          this.competitiveError = err && err.message ? err.message : 'Unable to load competitive operations.';
        } finally {
          this.competitiveLoading = false;
        }
      },

      competitiveTypeMeta(type) {
        const key = String(type || '').toLowerCase();
        if (key === 'showdown') return { label: 'Showdown', icon: 'fa-solid fa-bolt', tone: 'text-cyan-300', bg: 'bg-cyan-400/10 border-cyan-300/20' };
        if (key === 'mission') return { label: 'Mission', icon: 'fa-solid fa-flag-checkered', tone: 'text-violet-300', bg: 'bg-violet-400/10 border-violet-300/20' };
        if (key === 'bounty') return { label: 'Bounty', icon: 'fa-solid fa-crosshairs', tone: 'text-rose-300', bg: 'bg-rose-400/10 border-rose-300/20' };
        if (key === 'dropzone') return { label: 'Dropzone', icon: 'fa-solid fa-parachute-box', tone: 'text-amber-300', bg: 'bg-amber-400/10 border-amber-300/20' };
        return { label: 'Team Ops', icon: 'fa-solid fa-shield-halved', tone: 'text-emerald-300', bg: 'bg-emerald-400/10 border-emerald-300/20' };
      },

      competitiveStatusClass(op) {
        const bucket = this._operationBucket(op);
        if (bucket === 'needs_action') return 'bg-cyan-400/10 text-cyan-100 border border-cyan-300/20';
        if (bucket === 'review') return 'bg-amber-400/10 text-amber-100 border border-amber-300/20';
        if (bucket === 'completed') return 'bg-emerald-400/10 text-emerald-100 border border-emerald-300/20';
        return 'bg-white/[0.05] text-slate-200 border border-white/[0.08]';
      },

      competitiveActionUrl(op) {
        if (!op) return '/dashboard/competitive/';
        return op.next_action_url || op.detail_url || op.match_room_url || '/dashboard/competitive/';
      },

      competitiveTime(op) {
        if (!op) return '';
        const value = op.starts_at || op.scheduled_at || op.created_at || '';
        return value ? this.formatDateTime(value) : '';
      },

      _operationsByState(state) {
        return (this.myOperations || []).filter((op) => this._operationBucket(op) === state);
      },

      _operationBucket(op) {
        if (!op) return 'waiting';
        const status = String(op.status || '').toLowerCase();
        const label = String(op.next_action_label || '').toLowerCase();
        if (op.is_action_required || /submit|accept|decline|confirm|reserve|claim|review needed/.test(label)) return 'needs_action';
        if (/review|dispute|proof|confirmation|pending/.test(status) || /review|confirmation|proof/.test(label)) return 'review';
        if (/complete|settled|signed|accepted|closed|refunded|failed|rejected|declined/.test(status) || /result/.test(label)) return 'completed';
        if (/scheduled|starts|upcoming|room|match/.test(label) || op.starts_at || op.scheduled_at) return 'upcoming';
        return 'waiting';
      },

      async handleTeamApplicationAction(item, action) {
        if (!action || !action.url || !action.action) return;
        try {
          const res = await fetch(action.url, {
            method: 'POST',
            headers: {
              'X-CSRFToken': this._csrf(),
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
            body: JSON.stringify({ action: action.action }),
          });
          const data = await res.json();
          if (!res.ok || !data.success) {
            throw new Error(data.error || 'Action failed.');
          }
          if (window.showToast) {
            window.showToast({ type: 'success', message: data.message || 'Application updated.' });
          }
          await this.loadTeamApplications();
        } catch (err) {
          console.error('[CC] team application action failed', err);
          if (window.showToast) {
            window.showToast({ type: 'error', message: err && err.message ? err.message : 'Action failed.' });
          }
        }
      },

      teamApplicationStatusClass(item) {
        const status = item && item.status ? item.status : '';
        if (status === 'Offer Sent') return 'bg-dc-warning/10 text-dc-warning border border-dc-warning/20';
        if (status === 'Accepted / Signed') return 'bg-dc-success/10 text-dc-success border border-dc-success/20';
        if (status === 'Declined / Not Selected' || status === 'Withdrawn / Closed') return 'bg-white/[0.04] text-dc-textMuted border border-white/[0.08]';
        if (status === 'Tryout Scheduled') return 'bg-dc-accent/10 text-dc-accent border border-dc-accent/20';
        return 'bg-white/[0.06] text-white border border-white/[0.1]';
      },

      teamApplicationIcon(item) {
        if (!item || item.source_type !== 'tryout') return 'fa-solid fa-user-plus';
        if (item.status === 'Tryout Scheduled') return 'fa-solid fa-calendar-check';
        if (item.status === 'Offer Sent') return 'fa-solid fa-file-signature';
        return 'fa-solid fa-crosshairs';
      },

      formatDateTime(value) {
        const date = this._parseIsoDate(value);
        if (!date) return '';
        return date.toLocaleString([], {
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
        });
      },

      navigateAction(item) {
        if (item.btnUrl) {
          window.location.href = item.btnUrl;
        }
      },

      orgLogoSrc(org) {
        if (org && org.logo) return org.logo;
        return this.logoFallbackSvg(org && org.name ? org.name : 'Organization', 64);
      },

      teamLogoSrc(team) {
        if (team && team.logo) return team.logo;
        if (team && team.org && team.org.logo) return team.org.logo;
        return this.logoFallbackSvg(team && team.name ? team.name : 'Team', 80);
      },

      handleOrgLogoError(org, event) {
        if (org) {
          org.logo = '';
        }
        if (event && event.target) {
          event.target.src = this.logoFallbackSvg(org && org.name ? org.name : 'Organization', 64);
        }
      },

      handleTeamLogoError(team, event) {
        if (!event || !event.target) return;

        const orgLogo = team && team.org && team.org.logo ? team.org.logo : '';

        if (team && team.logo) {
          team.logo = '';
          if (orgLogo) {
            event.target.src = orgLogo;
            return;
          }
        }

        if (team && team.org) {
          team.org.logo = '';
        }
        event.target.src = this.logoFallbackSvg(team && team.name ? team.name : 'Team', 80);
      },

      _initials(value, fallback = 'DC') {
        const source = String(value || '').trim();
        if (!source) return fallback;

        const parts = source.split(/\s+/).filter(Boolean);
        const letters = (parts.length > 1 ? parts.slice(0, 2) : [source.slice(0, 2)])
          .map((part) => part.charAt(0))
          .join('')
          .toUpperCase();

        return letters || fallback;
      },

      logoFallbackSvg(name, size = 96) {
        const initials = this._initials(name, 'DC');
        const fontSize = Math.max(20, Math.round(size * 0.34));
        const svg = `
          <svg xmlns='http://www.w3.org/2000/svg' width='${size}' height='${size}' viewBox='0 0 ${size} ${size}'>
            <defs>
              <linearGradient id='bg' x1='0%' y1='0%' x2='100%' y2='100%'>
                <stop offset='0%' stop-color='#101828'/>
                <stop offset='100%' stop-color='#0b1120'/>
              </linearGradient>
            </defs>
            <rect width='100%' height='100%' rx='14' fill='url(#bg)'/>
            <text x='50%' y='52%' dominant-baseline='middle' text-anchor='middle' fill='#e2e8f0' font-family='Inter,Arial,sans-serif' font-size='${fontSize}' font-weight='700' letter-spacing='1'>${initials}</text>
          </svg>
        `.trim();
        return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
      },

      _refreshRelativeTimes() {
        this._refreshTournamentMatchTimes();
        this._refreshMatchLobbyAlertTime();
      },

      _refreshTournamentMatchTimes() {
        if (!Array.isArray(this.tournaments)) return;
        for (const tourney of this.tournaments) {
          const scheduledAt = tourney && tourney.matchScheduledAt ? tourney.matchScheduledAt : '';
          if (!scheduledAt) {
            tourney.matchTime = '';
            continue;
          }
          tourney.matchTime = this._relativeTimeLabel(scheduledAt);
        }
      },

      _refreshMatchLobbyAlertTime() {
        if (!this.matchLobbyAlert || !this.matchLobbyAlert.scheduledAt) return;

        const startsInMinutes = this._minutesUntil(this.matchLobbyAlert.scheduledAt);
        this.matchLobbyAlert.startsInMinutes = startsInMinutes;

        const tournament = this.matchLobbyAlert.tournament || 'Your match';
        const opponent = this.matchLobbyAlert.opponent || 'TBD';

        if (startsInMinutes <= 0) {
          this.matchLobbyAlert.startsInLabel = 'Now';
          this.matchLobbyAlert.message = `${tournament} vs ${opponent} is live now.`;
          return;
        }

        this.matchLobbyAlert.startsInLabel = `${startsInMinutes} min`;
        this.matchLobbyAlert.message = `${tournament} vs ${opponent} starts in about ${startsInMinutes} minutes.`;
      },

      _startClockUpdates() {
        this._stopClockUpdates();
        this._refreshRelativeTimes();
        this._clockTimer = setInterval(() => this._refreshRelativeTimes(), 30000);
      },

      _stopClockUpdates() {
        if (this._clockTimer) {
          clearInterval(this._clockTimer);
          this._clockTimer = null;
        }
      },

      _parseIsoDate(value) {
        if (!value) return null;
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) return null;
        return parsed;
      },

      _minutesUntil(value) {
        const target = this._parseIsoDate(value);
        if (!target) return 0;
        return Math.max(0, Math.ceil((target.getTime() - Date.now()) / 60000));
      },

      _relativeTimeLabel(value) {
        const target = this._parseIsoDate(value);
        if (!target) return '';

        const diffMs = target.getTime() - Date.now();
        const isFuture = diffMs >= 0;
        const absMinutes = Math.round(Math.abs(diffMs) / 60000);

        if (absMinutes <= 0) return isFuture ? 'Now' : 'Just now';
        if (absMinutes < 60) return isFuture ? `in ${absMinutes}m` : `${absMinutes}m ago`;

        const absHours = Math.floor(absMinutes / 60);
        if (absHours < 24) {
          const remMinutes = absMinutes % 60;
          const hourLabel = remMinutes ? `${absHours}h ${remMinutes}m` : `${absHours}h`;
          return isFuture ? `in ${hourLabel}` : `${hourLabel} ago`;
        }

        const absDays = Math.floor(absHours / 24);
        if (absDays < 7) return isFuture ? `in ${absDays}d` : `${absDays}d ago`;

        const absWeeks = Math.floor(absDays / 7);
        const remDays = absDays % 7;
        const weekLabel = remDays ? `${absWeeks}w ${remDays}d` : `${absWeeks}w`;
        return isFuture ? `in ${weekLabel}` : `${weekLabel} ago`;
      },

      // ── Live Count Polling ──

      async _pollUnreadCount() {
        try {
          const res = await fetch('/notifications/api/unread-count/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin',
          });
          if (!res.ok) return;
          const data = await res.json();
          if (typeof data.count === 'number') {
            this.unreadNotifCount = data.count;
          }
        } catch (e) {
          console.warn('[CC] unread count poll failed', e);
        }
      },

      _startNotifPolling() {
        this._stopNotifPolling();
        this._pollUnreadCount();
        this._notifPollTimer = setInterval(() => this._pollUnreadCount(), 15000);
      },

      _stopNotifPolling() {
        if (this._notifPollTimer) {
          clearInterval(this._notifPollTimer);
          this._notifPollTimer = null;
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
