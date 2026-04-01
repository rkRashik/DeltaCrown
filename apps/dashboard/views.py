from __future__ import annotations
from datetime import datetime, timedelta
from typing import Iterable, Optional
from urllib.parse import quote

from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Q, Count, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .forms import MyMatchesFilterForm

from django.utils.timesince import timesince as _timesince

logger = __import__("logging").getLogger(__name__)


# ─── Helper: safe model fetcher ─────────────────────────────────────────────
def _safe_model(label: str):
    """Return model class or None — never raises."""
    try:
        return apps.get_model(*label.split("."))
    except Exception:
        return None


def _safe_qs(fn):
    """Run a queryset lambda, return [] on any error."""
    try:
        return fn()
    except Exception:
        return []


def _safe_int(fn, default=0):
    try:
        return fn()
    except Exception:
        return default


# ═══════════════════════════════════════════════════════════════════════════
# MATCH FILTERING (legacy — kept for /my/matches/ route)
# ═══════════════════════════════════════════════════════════════════════════

def _filter_matches_for_user(user, form: MyMatchesFilterForm):
    if not hasattr(form, "cleaned_data") or form.cleaned_data is None:
        form.is_valid()
    if not hasattr(form, "cleaned_data"):
        form.cleaned_data = {}
    # Tournament Match model is unavailable in vNext
    return None, [], []


@login_required
def my_matches_view(request: HttpRequest) -> HttpResponse:
    form = MyMatchesFilterForm(request.GET or None)
    form.is_valid()
    context = {"form": form, "matches": [], "team_fields": [], "tchoices": []}
    return render(request, "dashboard/my_matches.html", context)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD — COMPREHENSIVE COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════════════

def _build_game_lookup():
    """Build {game_id: game_name} lookup from games.Game."""
    Game = _safe_model("games.Game")
    if not Game:
        return {}
    try:
        return {g.id: g.name for g in Game.objects.all().only("id", "name")}
    except Exception:
        return {}


def _logo_url(obj, field="logo"):
    try:
        f = getattr(obj, field, None)
        return f.url if f else None
    except Exception:
        return None


def _ts(dt, now):
    """Format datetime as '2h ago' or empty string."""
    if not dt:
        return ''
    try:
        return _timesince(dt, now) + ' ago'
    except Exception:
        return ''


def _img_url(obj, field="logo"):
    """Safely extract image URL from a model field."""
    try:
        f = getattr(obj, field, None)
        return f.url if f else None
    except Exception:
        return None


def _avatar_fallback(name: str, background: str = '222222') -> str:
    """Build a stable UI avatar fallback URL."""
    display = quote((name or 'User')[:40])
    return f'https://ui-avatars.com/api/?name={display}&background={background}&color=fff&size=96'


def _build_cc_data(context, user, now):
    """Transform dashboard context into Command Center Alpine state dict.

    Returns a JSON-serialisable dict consumed by ``command-center.js``.
    """
    profile = context['profile']

    # --- Action Items (dynamic, not hardcoded) ---
    action_items = []
    nmi = context.get('next_match_info')
    lobby_alert = None
    imminent = context.get('imminent_lobby_alert')
    if isinstance(imminent, dict) and imminent.get('match_id') and imminent.get('match_room_url'):
        try:
            starts_in_minutes = int(imminent.get('starts_in_minutes', 0) or 0)
        except (TypeError, ValueError):
            starts_in_minutes = 0
        starts_in_minutes = max(starts_in_minutes, 0)
        lobby_alert = {
            'id': 'lobby-alert-%s' % imminent.get('match_id'),
            'title': 'Enter Match Lobby',
            'message': '%s vs %s starts in about %s minutes.' % (
                imminent.get('tournament_name', 'Your match'),
                imminent.get('opponent_name', 'TBD'),
                starts_in_minutes,
            ),
            'btnText': 'Enter Match Lobby',
            'btnUrl': imminent.get('match_room_url'),
            'tournament': imminent.get('tournament_name', ''),
            'opponent': imminent.get('opponent_name', 'TBD'),
            'lobbyCode': imminent.get('lobby_code', ''),
            'startsInLabel': '%s min' % starts_in_minutes,
            'startsInMinutes': starts_in_minutes,
            'gameIcon': imminent.get('game_icon', ''),
        }
    if nmi:
        if nmi.get('is_live'):
            action_items.append({
                'id': 'nm-%s' % nmi['match_id'],
                'type': 'danger',
                'title': 'Live Match In Progress',
                'description': '%s vs %s' % (nmi.get('tournament_name', ''), nmi.get('opponent_name', 'TBD')),
                'icon': 'fa-solid fa-triangle-exclamation',
                'btnText': 'Enter Room',
                'btnUrl': '/tournaments/%s/matches/%s/room/' % (nmi.get('tournament_slug', ''), nmi['match_id']),
                'timeRemaining': 'LIVE NOW',
                'game': nmi.get('tournament_name', ''),
                'gameIcon': nmi.get('game_icon', ''),
            })
        elif nmi.get('state') in ('check_in', 'ready'):
            action_items.append({
                'id': 'nm-%s' % nmi['match_id'],
                'type': 'warning',
                'title': 'Tournament Check-in',
                'description': 'Check-in is open for %s.' % nmi.get('tournament_name', ''),
                'icon': 'fa-solid fa-ticket',
                'btnText': 'Check In Now',
                'btnUrl': '/tournaments/%s/bracket/' % nmi.get('tournament_slug', ''),
                'timeRemaining': 'Action Required',
                'game': nmi.get('tournament_name', ''),
                'gameIcon': nmi.get('game_icon', ''),
            })

    # Pending invites as action items
    for inv in context.get('pending_invites', []):
        action_items.append({
            'id': 'inv-action-%s' % inv['id'],
            'type': 'info',
            'title': 'Team Invite',
            'description': '%s invited you to %s as %s.' % (inv['inviter'], inv['team_name'], inv['role']),
            'icon': 'fa-solid fa-envelope-open-text',
            'btnText': 'View Invite',
            'btnUrl': '/teams/invites/',
            'timeRemaining': _ts(inv.get('created_at'), now),
            'game': '',
            'gameIcon': '',
        })

    # --- Organizations ---
    my_orgs = []
    for org in context.get('my_organizations', []):
        my_orgs.append({
            'id': 'org-%s' % org['id'],
            'name': org['name'],
            'slug': org.get('slug', ''),
            'logo': org.get('logo_url', ''),
            'role': org['role'],
            'cp': '%s teams' % org.get('team_count', 0),
            'verified': org.get('is_verified', False),
        })

    # --- Teams ---
    ms = context.get('match_stats', {})
    teams_out = []
    for t in context.get('my_teams', []):
        gn = (t.get('game_name') or '').lower()
        if 'valorant' in gn:
            gc = 'val'
        elif 'football' in gn or 'efootball' in gn:
            gc = 'ef'
        else:
            gc = 'other'

        roster = []
        for r in t.get('roster', []):
            roster.append({
                'name': r.get('name', ''),
                'isCaptain': r.get('isCaptain', False),
                'avatar': r.get('avatar', ''),
            })

        org_data = t.get('org')
        if org_data:
            org_data['logo'] = org_data.get('logo', '') or ''

        teams_out.append({
            'id': 't-%s' % t['id'],
            'name': t['name'],
            'slug': t.get('slug', ''),
            'logo': t.get('logo_url', ''),
            'tag': t.get('tag', ''),
            'org': org_data,
            'game': t.get('game_name', ''),
            'gameIcon': t.get('game_icon', ''),
            'gameCode': gc,
            'role': t.get('role', 'Member'),
            'winRate': '%s%%' % ms.get('win_rate', 0),
            'matches': ms.get('total', 0),
            'tier': 'Unranked',
            'memberCount': t.get('member_count', 0),
            'roster': roster,
            'pendingJR': t.get('pending_jr_count', 0),
        })

    # --- Tournaments ---
    tournaments = []
    for tr in context.get('active_tournaments', []):
        slug = tr.get('slug', '')
        opponent = 'TBD'
        if nmi and nmi.get('tournament_slug') == slug:
            opponent = nmi.get('opponent_name', 'TBD')
        match_lobby_url = ''
        if (
            slug
            and nmi
            and nmi.get('tournament_slug') == slug
            and nmi.get('match_id')
            and nmi.get('state') in ('check_in', 'ready', 'live')
        ):
            match_lobby_url = '/tournaments/%s/matches/%s/room/' % (slug, nmi.get('match_id'))
        pp = tr.get('prize_pool')
        try:
            prize_str = '{:,} DC'.format(int(pp)) if pp else '—'
        except (ValueError, TypeError):
            prize_str = str(pp) if pp else '—'
        tournaments.append({
            'id': 'tourney-%s' % tr['id'],
            'name': tr['name'],
            'slug': tr.get('slug', ''),
            'game': tr.get('game_name', ''),
            'gameIcon': tr.get('game_icon', ''),
            'banner': tr.get('banner_url', ''),
            'thumbnail': tr.get('thumbnail_url', ''),
            'status': (tr.get('reg_status') or tr.get('status') or '').replace('_', ' ').title(),
            'opponent': opponent,
            'prizePool': prize_str,
            'format': (tr.get('format') or '').replace('_', ' ').title(),
            'isLive': tr.get('is_live', False),
            'startDate': _ts(tr.get('tournament_start'), now) if tr.get('tournament_start') else '',
            'platform': tr.get('platform', ''),
            'maxParticipants': tr.get('max_participants', 0),
            'manageUrl': '/toc/%s/' % slug if slug else '',
            'canManage': bool(tr.get('can_manage', False)),
            'hubUrl': '/tournaments/%s/hub/' % slug if slug else '',
            'canEnterHub': True,
            'matchLobbyUrl': match_lobby_url,
            'hasMatchLobby': bool(match_lobby_url),
        })

    # --- Inbox (invites + notifications merged) ---
    inbox = []
    for inv in context.get('pending_invites', []):
        initials = ''.join([w[0] for w in inv['team_name'].split()[:2]]).upper() or 'TM'
        inbox.append({
            'id': 'inv-%s' % inv['id'],
            'category': 'INVITE',
            'color': 'text-dc-accent border-dc-accent/30 bg-dc-accent/10',
            'icon': 'fa-solid fa-user-plus',
            'sender': inv['team_name'],
            'avatar': inv.get('team_logo') or 'https://ui-avatars.com/api/?name=%s&background=6366F1&color=fff' % initials,
            'text': '%s invited you to join as %s.' % (inv['inviter'], inv['role']),
            'time': _ts(inv.get('created_at'), now),
            'unread': True,
            'hasAction': True,
            'actionKind': 'team_invite',
            'inviteId': inv['id'],
            'url': '/teams/invites/',
        })

    cat_map = {
        'team_invite': ('INVITE', 'text-dc-accent border-dc-accent/30 bg-dc-accent/10'),
        'invite_sent': ('INVITE', 'text-dc-accent border-dc-accent/30 bg-dc-accent/10'),
        'invite_accepted': ('INVITE', 'text-dc-accent border-dc-accent/30 bg-dc-accent/10'),
        'match_scheduled': ('MATCH', 'text-dc-danger border-dc-danger/30 bg-dc-danger/10'),
        'match_result': ('MATCH', 'text-dc-danger border-dc-danger/30 bg-dc-danger/10'),
        'bracket_ready': ('MATCH', 'text-dc-danger border-dc-danger/30 bg-dc-danger/10'),
        'checkin_open': ('MATCH', 'text-dc-warning border-dc-warning/30 bg-dc-warning/10'),
        'result_verified': ('MATCH', 'text-dc-success border-dc-success/30 bg-dc-success/10'),
        'reg_confirmed': ('TOURNAMENT', 'text-dc-warning border-dc-warning/30 bg-dc-warning/10'),
        'tournament_registered': ('TOURNAMENT', 'text-dc-warning border-dc-warning/30 bg-dc-warning/10'),
        'payment_verified': ('FINANCE', 'text-dc-success border-dc-success/30 bg-dc-success/10'),
        'payout_received': ('FINANCE', 'text-dc-warning border-dc-warning/30 bg-dc-warning/10'),
        'achievement_earned': ('ACHIEVEMENT', 'text-dc-warning border-dc-warning/30 bg-dc-warning/10'),
        'user_followed': ('SOCIAL', 'text-purple-400 border-purple-400/30 bg-purple-400/10'),
        'follow_request': ('SOCIAL', 'text-purple-400 border-purple-400/30 bg-purple-400/10'),
        'roster_changed': ('TEAM', 'text-dc-accent border-dc-accent/30 bg-dc-accent/10'),
        'join_request_received': ('TEAM', 'text-dc-accent border-dc-accent/30 bg-dc-accent/10'),
        'join_request_accepted': ('TEAM', 'text-dc-success border-dc-success/30 bg-dc-success/10'),
        'ranking_changed': ('RANK', 'text-dc-warning border-dc-warning/30 bg-dc-warning/10'),
        'system': ('SYSTEM', 'text-gray-400 border-gray-400/30 bg-gray-400/10'),
        'order': ('ORDER', 'text-dc-warning border-dc-warning/30 bg-dc-warning/10'),
        'wallet': ('FINANCE', 'text-dc-warning border-dc-warning/30 bg-dc-warning/10'),
    }
    icon_map = {
        'team_invite': 'fa-solid fa-user-plus',
        'invite_sent': 'fa-solid fa-user-plus',
        'invite_accepted': 'fa-solid fa-circle-check',
        'match_scheduled': 'fa-solid fa-calendar-check',
        'match_result': 'fa-solid fa-bolt',
        'bracket_ready': 'fa-solid fa-diagram-project',
        'checkin_open': 'fa-solid fa-ticket',
        'result_verified': 'fa-solid fa-shield-check',
        'reg_confirmed': 'fa-solid fa-flag-checkered',
        'tournament_registered': 'fa-solid fa-flag-checkered',
        'payment_verified': 'fa-solid fa-wallet',
        'payout_received': 'fa-solid fa-coins',
        'achievement_earned': 'fa-solid fa-trophy',
        'user_followed': 'fa-solid fa-user-check',
        'follow_request': 'fa-solid fa-user-clock',
        'follow_request_approved': 'fa-solid fa-user-check',
        'follow_request_rejected': 'fa-solid fa-user-minus',
        'roster_changed': 'fa-solid fa-users',
        'join_request_received': 'fa-solid fa-user-group',
        'join_request_accepted': 'fa-solid fa-user-group',
        'ranking_changed': 'fa-solid fa-chart-line',
        'system': 'fa-solid fa-bell',
        'order': 'fa-solid fa-bag-shopping',
        'wallet': 'fa-solid fa-wallet',
    }
    for n in context.get('recent_notifications', [])[:8]:
        ntype = n.get('type', '')
        cat, color = cat_map.get(ntype, ('SYSTEM', 'text-gray-400 border-gray-400/30 bg-gray-400/10'))
        is_follow_request = ntype == 'follow_request' and bool(n.get('follow_request_pending')) and bool(n.get('action_object_id'))
        inbox.append({
            'id': 'notif-%s' % n['id'],
            'category': cat,
            'color': color,
            'icon': icon_map.get(ntype, 'fa-solid fa-bell'),
            'sender': n.get('actor_name') or n.get('title', 'DeltaCrown'),
            'avatar': n.get('actor_avatar', ''),
            'text': n.get('body', ''),
            'time': _ts(n.get('created_at'), now),
            'unread': not n.get('is_read', True),
            'hasAction': is_follow_request,
            'actionKind': 'follow_request' if is_follow_request else '',
            'followRequestId': n.get('action_object_id') if is_follow_request else None,
            'notifId': n.get('id'),
            'url': n.get('url', ''),
        })

    # --- Competitive Ledger ---
    ledger = []
    for m in context.get('recent_matches', []):
        result_raw = str(m.get('result', '')).upper()
        if result_raw in ('WIN', 'W'):
            rc = 'W'
        elif result_raw in ('LOSS', 'L'):
            rc = 'L'
        else:
            rc = 'D'
        s1, s2 = m.get('score_team1'), m.get('score_team2')
        score = '%s-%s' % (s1, s2) if s1 is not None and s2 is not None else '—'
        ledger.append({
            'id': 'M-%s' % m['id'],
            'date': _ts(m.get('created_at'), now),
            'game': m.get('game_name', ''),
            'gameIcon': m.get('game_icon', ''),
            'type': (m.get('match_type') or 'Match').replace('_', ' ').title(),
            'opponent': m.get('team2_name', 'Unknown'),
            'result': rc,
            'score': score,
            'rating': '',
            'hasVod': False,
            'status': 'Verified',
        })

    # --- User ---
    uname = profile.get('display_name', user.username)
    initials = ''.join([w[0] for w in uname.split()[:2]]).upper() or 'U'

    # --- Wallet recent transactions ---
    recent_txns = []
    for txn in context.get('wallet', {}).get('recent_txns', []):
        recent_txns.append({
            'amount': int(txn.get('amount', 0)),
            'reason': str(txn.get('reason', '')).replace('_', ' ').title(),
            'time': _ts(txn.get('created_at'), now),
        })

    # --- Game passports ---
    passports = []
    for gp in context.get('game_passports', []):
        passports.append({
            'id': gp.get('id', ''),
            'game': gp.get('game_name', ''),
            'gameIcon': gp.get('game_icon', ''),
            'gameColor': gp.get('game_color', '#6366F1'),
            'ign': gp.get('ign', ''),
            'isLinked': bool(gp.get('ign')),
            'isLft': gp.get('is_lft', False),
        })

    # --- Badges ---
    badges_out = []
    for b in context.get('badges', []):
        badges_out.append({
            'name': b.get('name', ''),
            'icon': b.get('icon', ''),
            'rarity': b.get('rarity', 'common'),
            'description': b.get('description', ''),
        })

    # --- Leaderboard ---
    lb_data = []
    for lb in context.get('leaderboard_data', []):
        lb_data.append({
            'rank': lb.get('rank', 0),
            'points': lb.get('points', 0),
            'type': lb.get('leaderboard_type', ''),
            'game': lb.get('game_name', ''),
        })

    # --- Recruitment positions (LFP) ---
    lfp_positions = []
    for pos in context.get('recruitment_positions', []):
        lfp_positions.append({
            'id': pos.get('id', ''),
            'team': pos.get('team_name', ''),
            'teamSlug': pos.get('team_slug', ''),
            'teamLogo': pos.get('team_logo', ''),
            'title': pos.get('title', ''),
            'role': pos.get('role_category', ''),
            'game': pos.get('game_name', ''),
            'gameIcon': pos.get('game_icon', ''),
        })

    # --- Featured product ---
    featured_product = context.get('featured_product')

    # --- Recent orders ---
    orders_out = []
    for o in context.get('recent_orders', []):
        orders_out.append({
            'id': o.get('id', ''),
            'status': str(o.get('status', '')).replace('_', ' ').title(),
            'total': o.get('total', 0),
            'time': _ts(o.get('created_at'), now),
        })

    # --- Support tickets ---
    tickets = []
    for t in context.get('support_tickets', []):
        tickets.append({
            'id': t.get('id', ''),
            'subject': t.get('subject', ''),
            'status': str(t.get('status', '')).replace('_', ' ').title(),
            'priority': t.get('priority', 'MEDIUM'),
            'time': _ts(t.get('created_at'), now),
        })

    # --- Challenges ---
    challenges_out = []
    for c in context.get('active_challenges', []):
        ctype = str(c.get('type', 'SCRIM')).upper()
        type_icons = {'WAGER': 'fa-solid fa-coins', 'BOUNTY': 'fa-solid fa-crosshairs', 'SCRIM': 'fa-solid fa-swords', 'DUEL': 'fa-solid fa-hand-fist'}
        type_colors = {'WAGER': 'text-dc-warning', 'BOUNTY': 'text-dc-danger', 'SCRIM': 'text-dc-accent', 'DUEL': 'text-purple-400'}
        status_raw = str(c.get('status', '')).upper()
        challenges_out.append({
            'id': c.get('id', ''),
            'title': c.get('title', ''),
            'type': ctype,
            'typeIcon': type_icons.get(ctype, 'fa-solid fa-swords'),
            'typeColor': type_colors.get(ctype, 'text-dc-accent'),
            'status': status_raw.replace('_', ' ').title(),
            'statusRaw': status_raw,
            'format': c.get('format', 'BO1'),
            'prize': c.get('prize', 0),
            'currency': c.get('currency', 'DC'),
            'team': c.get('team_name', ''),
            'opponent': c.get('opponent', 'Open'),
            'game': c.get('game_name', ''),
            'gameIcon': c.get('game_icon', ''),
            'time': _ts(c.get('created_at'), now),
            'expiresAt': _ts(c.get('expires_at'), now),
        })

    # --- Bounties ---
    bounties_out = []
    for b in context.get('active_bounties', []):
        status_raw = str(b.get('status', '')).upper()
        bounties_out.append({
            'id': b.get('id', ''),
            'title': b.get('title', ''),
            'status': status_raw.replace('_', ' ').title(),
            'statusRaw': status_raw,
            'stake': b.get('stake', 0),
            'payout': b.get('payout', 0),
            'game': b.get('game_name', ''),
            'gameIcon': b.get('game_icon', ''),
            'creator': b.get('creator', ''),
            'isMine': b.get('is_mine', False),
            'opponent': b.get('opponent', 'Open'),
            'time': _ts(b.get('created_at'), now),
            'expiresAt': _ts(b.get('expires_at'), now),
        })

    return {
        'user': {
            'name': uname,
            'username': user.username,
            'slug': profile.get('slug', user.username),
            'avatar': profile.get('avatar_url') or 'https://ui-avatars.com/api/?name=%s&background=6366F1&color=fff&bold=true&size=200' % initials,
            'banner': profile.get('banner_url', ''),
            'isVerified': str(profile.get('kyc_status', '')).lower() in ('approved', 'verified'),
            'lftStatus': profile.get('lft_status', 'NOT_LOOKING'),
            'reputation': profile.get('reputation_score', 100),
            'level': profile.get('level', 1),
            'xp': profile.get('xp', 0),
        },
        'wallet': {
            'balance': int(context['wallet'].get('balance', 0)),
            'pending': int(context['wallet'].get('pending_balance', 0)),
            'currency': 'DC',
            'bdtEquiv': round(context['wallet'].get('balance', 0) * 0.1, 2),
            'hasWallet': context['wallet'].get('has_wallet', False),
            'recentTxns': recent_txns,
        },
        'matchLobbyAlert': lobby_alert,
        'actionItems': action_items,
        'myOrgs': my_orgs,
        'teams': teams_out,
        'tournaments': tournaments,
        'inbox': inbox,
        'inboxFilter': 'all',
        'matches': ledger,
        'matchStats': {
            'wins': ms.get('wins', 0),
            'losses': ms.get('losses', 0),
            'draws': ms.get('draws', 0),
            'total': ms.get('total', 0),
            'win_rate': ms.get('win_rate', 0),
        },
        'socialStats': context.get('social_stats', {}),
        'unreadNotifCount': context.get('unread_notif_count', 0),
        'gamePassports': passports,
        'badges': badges_out,
        'leaderboard': lb_data,
        'lfpPositions': lfp_positions,
        'featuredProduct': featured_product,
        'recentOrders': orders_out,
        'supportTickets': tickets,
        'challenges': challenges_out,
        'bounties': bounties_out,
    }


@login_required
def dashboard_index(request: HttpRequest) -> HttpResponse:
    """
    Comprehensive Dashboard — the user's command center.

    Pulls data from every major subsystem with graceful degradation:
    teams, invites, tournaments, matches, leaderboards, economy,
    notifications, profile, achievements.
    """
    from apps.organizations.models import Team
    from apps.organizations.models.membership import TeamMembership
    from apps.organizations.models.team_invite import TeamInvite
    from apps.organizations.choices import MembershipStatus
    from apps.notifications.models import Notification

    user = request.user
    now = timezone.now()
    game_map = _build_game_lookup()

    # Detailed game lookup with icons/colors
    game_detail_map = {}
    try:
        Game = _safe_model("games.Game")
        if Game:
            for g in Game.objects.all().only("id", "name", "icon", "logo", "primary_color", "short_code"):
                game_detail_map[g.id] = {
                    "name": g.name,
                    "icon": _img_url(g, "icon"),
                    "logo": _img_url(g, "logo"),
                    "color": getattr(g, "primary_color", "#6366F1") or "#6366F1",
                    "code": getattr(g, "short_code", "") or "",
                }
    except Exception:
        pass

    # ── 1. USER PROFILE ─────────────────────────────────────────────────
    profile = None
    profile_data = {}
    try:
        Profile = _safe_model("user_profile.UserProfile")
        if Profile:
            profile = Profile.objects.filter(user=user).first()
        if profile:
            avatar = None
            banner = None
            try:
                avatar = profile.avatar.url if profile.avatar else None
            except Exception:
                pass
            try:
                banner = profile.banner.url if profile.banner else None
            except Exception:
                pass
            profile_data = {
                "display_name": getattr(profile, "display_name", "") or user.get_full_name() or user.username,
                "avatar_url": avatar,
                "banner_url": banner,
                "slug": getattr(profile, "slug", user.username),
                "lft_status": getattr(profile, "lft_status", None) or getattr(profile, "LFTStatus", None),
                "kyc_status": getattr(profile, "kyc_status", ""),
                "reputation_score": getattr(profile, "reputation_score", 100),
                "level": getattr(profile, "level", 1),
                "xp": getattr(profile, "xp", 0),
            }
        else:
            profile_data = {
                "display_name": user.get_full_name() or user.username,
                "avatar_url": None,
                "slug": user.username,
                "lft_status": None,
                "kyc_status": "",
            }
    except Exception:
        profile_data = {
            "display_name": user.get_full_name() or user.username,
            "avatar_url": None,
            "slug": user.username,
            "lft_status": None,
            "kyc_status": "",
        }

    # ── 2. MY TEAMS ─────────────────────────────────────────────────────
    my_teams = []
    try:
        memberships = (
            TeamMembership.objects.filter(user=user, status=MembershipStatus.ACTIVE)
            .select_related("team", "team__organization")
            .order_by("-joined_at")[:8]
        )
        for m in memberships:
            t = m.team
            member_ct = _safe_int(
                lambda: TeamMembership.objects.filter(team=t, status=MembershipStatus.ACTIVE).count()
            )
            # Pending join request count for admins/owners
            jr_count = 0
            if m.role in ('OWNER', 'MANAGER'):
                try:
                    from apps.organizations.models.join_request import TeamJoinRequest
                    jr_count = TeamJoinRequest.objects.filter(
                        team=t,
                        status__in=['PENDING', 'TRYOUT_SCHEDULED', 'TRYOUT_COMPLETED', 'OFFER_SENT'],
                    ).count()
                except Exception:
                    pass
            # Organization association
            org_obj = getattr(t, 'organization', None)
            team_org = None
            if org_obj:
                team_org = {
                    "name": org_obj.name,
                    "slug": getattr(org_obj, "slug", ""),
                    "logo": _img_url(org_obj),
                    "verified": getattr(org_obj, "is_verified", False),
                }
            gd = game_detail_map.get(t.game_id, {})
            my_teams.append({
                "id": t.id, "name": t.name, "slug": t.slug,
                "logo_url": _img_url(t),
                "role": m.role,
                "game_name": game_map.get(t.game_id, ""),
                "game_icon": gd.get("icon", ""),
                "game_color": gd.get("color", "#6366F1"),
                "member_count": member_ct,
                "tag": getattr(t, "tag", "") or "",
                "status": getattr(t, "status", ""),
                "pending_jr_count": jr_count,
                "org": team_org,
            })
    except Exception:
        logger.debug("Dashboard: teams query failed", exc_info=True)

    # Batch-fetch roster data for team cards
    try:
        if my_teams:
            team_id_list = [t["id"] for t in my_teams]
            roster_qs = (
                TeamMembership.objects.filter(
                    team_id__in=team_id_list,
                    status=MembershipStatus.ACTIVE,
                )
                .select_related("user")
                .order_by("team_id", "joined_at")
            )

            # Batch-load user avatars
            member_user_ids = [rm.user_id for rm in roster_qs]
            Profile = _safe_model("user_profile.UserProfile")
            avatar_map = {}
            if Profile and member_user_ids:
                for p in Profile.objects.filter(user_id__in=member_user_ids).only("user_id", "avatar"):
                    avatar_map[p.user_id] = _img_url(p, "avatar")

            roster_data = {}
            for rm in roster_qs:
                lst = roster_data.setdefault(rm.team_id, [])
                if len(lst) < 5:
                    uname = rm.user.username
                    initials = ''.join([w[0] for w in uname.split()[:2]]).upper() or 'U'
                    avatar = avatar_map.get(rm.user_id) or (
                        'https://ui-avatars.com/api/?name=%s&background=222&color=fff&size=64' % initials
                    )
                    lst.append({
                        "name": "You" if rm.user_id == user.id else uname,
                        "isCaptain": rm.role in ("OWNER", "CAPTAIN"),
                        "avatar": avatar,
                        "role": rm.role,
                    })
            for t in my_teams:
                t["roster"] = roster_data.get(t["id"], [])
    except Exception:
        logger.debug("Dashboard: roster query failed", exc_info=True)

    # ── 3. PENDING INVITES ──────────────────────────────────────────────
    pending_invites = []
    try:
        invites = (
            TeamInvite.objects.filter(
                invited_user=user, status="PENDING", expires_at__gt=now,
            )
            .select_related("team", "inviter")
            .order_by("-created_at")[:5]
        )
        for inv in invites:
            pending_invites.append({
                "id": inv.id,
                "team_name": inv.team.name,
                "team_slug": inv.team.slug,
                "team_logo": _logo_url(inv.team),
                "role": inv.role,
                "inviter": inv.inviter.username if inv.inviter else "Unknown",
                "created_at": inv.created_at,
                "expires_at": inv.expires_at,
            })
    except Exception:
        logger.debug("Dashboard: invites query failed", exc_info=True)

    # ── 4. RECENT MATCHES (competition.MatchReport) ─────────────────────
    recent_matches = []
    try:
        MatchReport = _safe_model("competition.MatchReport")
        if MatchReport:
            team_ids = [t["id"] for t in my_teams]
            if team_ids:
                reports = (
                    MatchReport.objects.filter(
                        Q(team1_id__in=team_ids) | Q(team2_id__in=team_ids)
                    )
                    .select_related("team1", "team2")
                    .order_by("-created_at")[:6]
                )
                for r in reports:
                    t1_name = getattr(r.team1, "name", "TBD") if r.team1 else "TBD"
                    t2_name = getattr(r.team2, "name", "TBD") if r.team2 else "TBD"
                    recent_matches.append({
                        "id": r.id,
                        "team1_name": t1_name,
                        "team2_name": t2_name,
                        "result": getattr(r, "result", ""),
                        "match_type": getattr(r, "match_type", ""),
                        "game_name": game_map.get(getattr(r, "game_id", None), ""),
                        "game_icon": game_detail_map.get(getattr(r, "game_id", None), {}).get("icon", ""),
                        "created_at": r.created_at,
                        "score_team1": getattr(r, "score_team1", None),
                        "score_team2": getattr(r, "score_team2", None),
                    })
    except Exception:
        logger.debug("Dashboard: matches query failed", exc_info=True)

    # ── 5. MATCH STATS (W / L / D) ──────────────────────────────────────
    match_stats = {"wins": 0, "losses": 0, "draws": 0, "total": 0, "win_rate": 0}
    try:
        MatchReport = _safe_model("competition.MatchReport")
        if MatchReport and my_teams:
            team_ids = [t["id"] for t in my_teams]
            all_reports = MatchReport.objects.filter(
                Q(team1_id__in=team_ids) | Q(team2_id__in=team_ids)
            )
            for r in all_reports:
                result = str(getattr(r, "result", "")).upper()
                is_team1 = r.team1_id in team_ids
                if result == "WIN":
                    if is_team1:
                        match_stats["wins"] += 1
                    else:
                        match_stats["losses"] += 1
                elif result == "LOSS":
                    if is_team1:
                        match_stats["losses"] += 1
                    else:
                        match_stats["wins"] += 1
                elif result == "DRAW":
                    match_stats["draws"] += 1
                match_stats["total"] += 1
            if match_stats["total"] > 0:
                match_stats["win_rate"] = round(
                    match_stats["wins"] / match_stats["total"] * 100
                )
    except Exception:
        logger.debug("Dashboard: match stats query failed", exc_info=True)

    # ── 6. TOURNAMENTS ───────────────────────────────────────────────────
    active_tournaments = []
    tournament_count = 0
    next_match_info = None  # User's upcoming match with room link
    imminent_lobby_alert = None
    try:
        Registration = _safe_model("tournaments.Registration")
        Tournament = _safe_model("tournaments.Tournament")
        Match = _safe_model("tournaments.Match")
        TournamentStaffAssignment = _safe_model("tournaments.TournamentStaffAssignment")
        if Registration and Tournament:
            excluded_statuses = ["cancelled", "rejected", "draft"]
            reg_filter = Q(is_deleted=False)
            reg_filter &= ~Q(status__in=excluded_statuses)
            reg_filter &= (Q(user=user) | Q(team_id__in=[t["id"] for t in my_teams])) if my_teams else Q(user=user)

            regs = list(
                Registration.objects.filter(reg_filter)
                .select_related("tournament", "tournament__game")
                .order_by("-created_at")[:8]
            )
            tournament_ids = [r.tournament_id for r in regs if getattr(r, "tournament_id", None)]
            vnext_staff_tournament_ids = set()

            if tournament_ids and TournamentStaffAssignment:
                try:
                    vnext_staff_tournament_ids = set(
                        TournamentStaffAssignment.objects.filter(
                            user=user,
                            is_active=True,
                            tournament_id__in=tournament_ids,
                        ).values_list("tournament_id", flat=True)
                    )
                except Exception:
                    vnext_staff_tournament_ids = set()

            for reg in regs:
                t = reg.tournament
                if t:
                    can_manage = bool(
                        user.is_staff
                        or getattr(t, "organizer_id", None) == user.id
                        or t.id in vnext_staff_tournament_ids
                    )
                    active_tournaments.append({
                        "id": t.id,
                        "name": t.name,
                        "slug": getattr(t, "slug", ""),
                        "status": getattr(t, "status", ""),
                        "game_name": t.game.display_name if t.game else game_map.get(getattr(t, "game_id", None), ""),
                        "game_icon": _img_url(t.game, "icon") if t.game else None,
                        "banner_url": _img_url(t, "banner_image"),
                        "thumbnail_url": _img_url(t, "thumbnail_image"),
                        "scheduled_at": getattr(t, "scheduled_at", None),
                        "tournament_start": getattr(t, "tournament_start", None),
                        "prize_pool": getattr(t, "prize_pool", None),
                        "format": getattr(t, "format", ""),
                        "reg_status": getattr(reg, "status", ""),
                        "is_live": getattr(t, "status", "") == "live",
                        "platform": getattr(t, "platform", ""),
                        "max_participants": getattr(t, "max_participants", 0),
                        "can_manage": can_manage,
                    })
            tournament_count = (
                Registration.objects.filter(reg_filter)
                .values("tournament").distinct().count()
            )

        # Find user's next upcoming match across all tournaments
        if Match:
            upcoming_states = ["scheduled", "check_in", "ready", "live"]
            user_team_ids = [t["id"] for t in my_teams]
            q_participant = Q(participant1_id=user.id) | Q(participant2_id=user.id)
            if user_team_ids:
                q_participant |= Q(participant1_id__in=user_team_ids) | Q(participant2_id__in=user_team_ids)
            nm = (
                Match.objects.filter(q_participant, state__in=upcoming_states, is_deleted=False)
                .select_related("tournament")
                .order_by("scheduled_time", "round_number", "match_number")
                .first()
            )
            if nm:
                nm_lobby_info = nm.lobby_info if isinstance(nm.lobby_info, dict) else {}
                nm_lobby_code = (nm_lobby_info.get('lobby_code') or nm_lobby_info.get('code') or '').strip()
                nm_lobby_status = str(nm_lobby_info.get('status') or '').strip().lower()
                nm_lobby_open = bool(nm_lobby_code) and nm_lobby_status not in {'closed', 'completed', 'cancelled'}
                next_match_info = {
                    "match_id": nm.id,
                    "tournament_name": nm.tournament.name if nm.tournament else "",
                    "tournament_slug": nm.tournament.slug if nm.tournament else "",
                    "opponent_name": nm.participant2_name if nm.participant1_id == user.id or nm.participant1_id in user_team_ids else nm.participant1_name,
                    "scheduled_time": nm.scheduled_time,
                    "state": nm.state,
                    "is_live": nm.state == "live",
                    "match_room_url": '/tournaments/%s/matches/%s/room/' % (nm.tournament.slug, nm.id) if nm.tournament else '',
                    "lobby_code": nm_lobby_code,
                    "lobby_status": nm_lobby_status,
                    "lobby_open": nm_lobby_open,
                    "game_icon": _img_url(nm.tournament.game, "icon") if nm.tournament and nm.tournament.game else None,
                }

            window_start = now + timedelta(minutes=15)
            window_end = now + timedelta(minutes=60)
            window_matches = (
                Match.objects.filter(
                    q_participant,
                    state__in=["scheduled", "check_in", "ready"],
                    is_deleted=False,
                    scheduled_time__gte=window_start,
                    scheduled_time__lte=window_end,
                )
                .select_related("tournament", "tournament__game")
                .order_by("scheduled_time", "round_number", "match_number")[:8]
            )
            for wm in window_matches:
                lobby_info = wm.lobby_info if isinstance(wm.lobby_info, dict) else {}
                lobby_code = (lobby_info.get('lobby_code') or lobby_info.get('code') or '').strip()
                lobby_status = str(lobby_info.get('status') or '').strip().lower()
                lobby_open = bool(lobby_code) and lobby_status not in {'closed', 'completed', 'cancelled'}
                if not lobby_open:
                    continue

                starts_in_minutes = max(int((wm.scheduled_time - now).total_seconds() // 60), 0)
                if starts_in_minutes < 15 or starts_in_minutes > 60:
                    continue

                imminent_lobby_alert = {
                    "match_id": wm.id,
                    "tournament_name": wm.tournament.name if wm.tournament else "",
                    "tournament_slug": wm.tournament.slug if wm.tournament else "",
                    "opponent_name": wm.participant2_name if wm.participant1_id == user.id or wm.participant1_id in user_team_ids else wm.participant1_name,
                    "scheduled_time": wm.scheduled_time,
                    "starts_in_minutes": starts_in_minutes,
                    "lobby_code": lobby_code,
                    "lobby_status": lobby_status,
                    "match_room_url": '/tournaments/%s/matches/%s/room/' % (wm.tournament.slug, wm.id) if wm.tournament else '',
                    "game_icon": _img_url(wm.tournament.game, "icon") if wm.tournament and wm.tournament.game else None,
                }
                break
    except Exception:
        logger.debug("Dashboard: tournaments query failed", exc_info=True)

    # ── 7. LEADERBOARD POSITION ──────────────────────────────────────────
    leaderboard_data = []
    try:
        LeaderboardEntry = _safe_model("leaderboards.LeaderboardEntry")
        if LeaderboardEntry:
            entries = (
                LeaderboardEntry.objects.filter(player=user)
                .order_by("rank")[:3]
            )
            for e in entries:
                leaderboard_data.append({
                    "rank": e.rank,
                    "points": getattr(e, "points", 0),
                    "leaderboard_type": getattr(e, "leaderboard_type", ""),
                    "game_name": game_map.get(getattr(e, "game_id", None), ""),
                    "wins": getattr(e, "wins", 0),
                    "losses": getattr(e, "losses", 0),
                    "win_rate": getattr(e, "win_rate", 0),
                })
    except Exception:
        logger.debug("Dashboard: leaderboard query failed", exc_info=True)

    # ── 8. WALLET / ECONOMY ──────────────────────────────────────────────
    wallet_data = {"balance": 0, "has_wallet": False, "recent_txns": []}
    try:
        Wallet = _safe_model("economy.DeltaCrownWallet")
        Transaction = _safe_model("economy.DeltaCrownTransaction")
        if Wallet and profile:
            wallet = Wallet.objects.filter(profile=profile).first()
            if wallet:
                wallet_data["has_wallet"] = True
                wallet_data["balance"] = float(getattr(wallet, "cached_balance", 0) or 0)
                if Transaction:
                    txns = Transaction.objects.filter(wallet=wallet).order_by("-created_at")[:5]
                    for txn in txns:
                        wallet_data["recent_txns"].append({
                            "amount": float(txn.amount),
                            "reason": str(getattr(txn, "reason", "")),
                            "created_at": txn.created_at,
                        })
    except Exception:
        logger.debug("Dashboard: wallet query failed", exc_info=True)

    # ── 9. BADGES / ACHIEVEMENTS ─────────────────────────────────────────
    badges = []
    try:
        UserBadge = _safe_model("user_profile.UserBadge")
        if UserBadge and profile:
            ubadges = UserBadge.objects.filter(profile=profile).select_related("badge").order_by("-awarded_at")[:6]
            for ub in ubadges:
                b = ub.badge
                badges.append({
                    "name": getattr(b, "name", ""),
                    "icon": getattr(b, "icon", "") or getattr(b, "icon_url", ""),
                    "description": getattr(b, "description", ""),
                    "rarity": getattr(b, "rarity", ""),
                    "awarded_at": getattr(ub, "awarded_at", None),
                })
    except Exception:
        logger.debug("Dashboard: badges query failed", exc_info=True)

    # ── 10. NOTIFICATIONS ────────────────────────────────────────────────
    recent_notifications = []
    unread_notif_count = 0
    try:
        notifs = Notification.objects.filter(recipient=user).order_by("-created_at")[:8]

        follow_request_meta = {}
        follow_request_ids = [
            n.action_object_id
            for n in notifs
            if n.type == 'follow_request' and getattr(n, 'action_object_id', None)
        ]
        if follow_request_ids:
            FollowRequest = _safe_model("user_profile.FollowRequest")
            if FollowRequest:
                for req in FollowRequest.objects.filter(id__in=follow_request_ids).select_related("requester", "requester__user"):
                    requester_name = getattr(req.requester, 'display_name', '') or req.requester.user.username
                    follow_request_meta[req.id] = {
                        'actor_name': requester_name,
                        'actor_avatar': _img_url(req.requester, 'avatar') or _avatar_fallback(requester_name, '0f3460'),
                        'is_pending': req.status == FollowRequest.STATUS_PENDING,
                    }

        for n in notifs:
            follow_meta = follow_request_meta.get(getattr(n, 'action_object_id', None), {}) if n.type == 'follow_request' else {}
            recent_notifications.append({
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "body": getattr(n, "body", "") or getattr(n, "message", ""),
                "url": n.url,
                "is_read": n.is_read,
                "created_at": n.created_at,
                "action_type": getattr(n, "action_type", ""),
                "action_object_id": getattr(n, "action_object_id", None),
                "actor_name": follow_meta.get('actor_name', ''),
                "actor_avatar": follow_meta.get('actor_avatar', ''),
                "follow_request_pending": follow_meta.get('is_pending', False),
            })
        unread_notif_count = _safe_int(
            lambda: Notification.objects.filter(recipient=user, is_read=False).count()
        )
    except Exception:
        logger.debug("Dashboard: notifications query failed", exc_info=True)

    # ── 11. SOCIAL STATS (followers / following) ─────────────────────────
    social_stats = {"followers": 0, "following": 0}
    try:
        Follow = _safe_model("user_profile.Follow")
        if Follow and profile:
            social_stats["followers"] = _safe_int(
                lambda: Follow.objects.filter(following=profile).count()
            )
            social_stats["following"] = _safe_int(
                lambda: Follow.objects.filter(follower=profile).count()
            )
    except Exception:
        pass

    # ── 12. RECENT ORDERS (ecommerce) ────────────────────────────────────
    recent_orders = []
    try:
        Order = _safe_model("ecommerce.Order")
        if Order:
            orders = Order.objects.filter(user=user).order_by("-created_at")[:3]
            for o in orders:
                recent_orders.append({
                    "id": o.id,
                    "status": getattr(o, "status", ""),
                    "total": float(getattr(o, "total", 0) or 0),
                    "created_at": o.created_at,
                })
    except Exception:
        pass

    # ── 13. ORGANIZATION MEMBERSHIPS ─────────────────────────────────────
    my_organizations = []
    try:
        OrgMembership = _safe_model("organizations.OrganizationMembership")
        if OrgMembership:
            org_memberships = (
                OrgMembership.objects.filter(user=user)
                .select_related("organization")
                .order_by("-joined_at")[:5]
            )
            for om in org_memberships:
                org = om.organization
                team_count_in_org = 0
                try:
                    team_count_in_org = Team.objects.filter(
                        organization=org, status="ACTIVE"
                    ).count()
                except Exception:
                    pass
                my_organizations.append({
                    "id": org.id,
                    "name": org.name,
                    "slug": org.slug,
                    "logo_url": _logo_url(org),
                    "role": om.role,
                    "is_verified": getattr(org, "is_verified", False),
                    "team_count": team_count_in_org,
                    "joined_at": om.joined_at,
                })
    except Exception:
        logger.debug("Dashboard: organizations query failed", exc_info=True)

    # ── 14. GAME PASSPORTS (linked game accounts) ────────────────────────
    game_passports = []
    try:
        GameProfile = _safe_model("user_profile.GameProfile")
        if GameProfile:
            gps = GameProfile.objects.filter(user=user).select_related("game").order_by("game__name")
            for gp in gps:
                game_passports.append({
                    "id": gp.id,
                    "game_name": gp.game.name if gp.game else "",
                    "game_icon": _img_url(gp.game, "icon") if gp.game else "",
                    "game_color": getattr(gp.game, "primary_color", "#6366F1") if gp.game else "#6366F1",
                    "ign": getattr(gp, "ign", "") or getattr(gp, "game_display_name", ""),
                    "is_lft": getattr(gp, "is_lft", False),
                })
    except Exception:
        logger.debug("Dashboard: game passports query failed", exc_info=True)

    # ── 15. RECRUITMENT POSITIONS (LFP) ──────────────────────────────────
    recruitment_positions = []
    try:
        RecruitmentPosition = _safe_model("organizations.RecruitmentPosition")
        if RecruitmentPosition and my_teams:
            team_ids = [t["id"] for t in my_teams]
            positions = (
                RecruitmentPosition.objects.filter(team_id__in=team_ids, is_active=True)
                .select_related("team")
                .order_by("-id")[:5]
            )
            for pos in positions:
                gd = game_detail_map.get(getattr(pos.team, "game_id", None), {})
                recruitment_positions.append({
                    "id": pos.id,
                    "team_name": pos.team.name if pos.team else "",
                    "team_slug": pos.team.slug if pos.team else "",
                    "team_logo": _img_url(pos.team) if pos.team else "",
                    "title": getattr(pos, "title", ""),
                    "role_category": getattr(pos, "role_category", ""),
                    "game_name": gd.get("name", ""),
                    "game_icon": gd.get("icon", ""),
                })
    except Exception:
        logger.debug("Dashboard: recruitment positions query failed", exc_info=True)

    # ── 16. FEATURED PRODUCT (store) ─────────────────────────────────────
    featured_product = None
    try:
        Product = _safe_model("ecommerce.Product")
        if Product:
            prod = Product.objects.filter(is_featured=True, stock__gt=0).order_by("-created_at").first()
            if prod:
                featured_product = {
                    "id": prod.id,
                    "name": prod.name,
                    "slug": getattr(prod, "slug", ""),
                    "price": float(getattr(prod, "price", 0) or 0),
                    "original_price": float(getattr(prod, "original_price", 0) or 0),
                    "image": _img_url(prod, "featured_image"),
                    "rarity": getattr(prod, "rarity", "common"),
                    "product_type": getattr(prod, "product_type", ""),
                    "is_limited": getattr(prod, "is_limited_edition", False),
                }
    except Exception:
        logger.debug("Dashboard: featured product query failed", exc_info=True)

    # ── 17. SUPPORT TICKETS ──────────────────────────────────────────────
    support_tickets = []
    try:
        ContactMessage = _safe_model("support.ContactMessage")
        if ContactMessage:
            tickets = (
                ContactMessage.objects.filter(user=user)
                .exclude(status="CLOSED")
                .order_by("-created_at")[:3]
            )
            for t in tickets:
                support_tickets.append({
                    "id": t.id,
                    "subject": getattr(t, "subject", ""),
                    "status": getattr(t, "status", ""),
                    "priority": getattr(t, "priority", "MEDIUM"),
                    "created_at": t.created_at,
                })
    except Exception:
        logger.debug("Dashboard: support tickets query failed", exc_info=True)

    # ── 18. CHALLENGES ───────────────────────────────────────────────────
    active_challenges = []
    try:
        Challenge = _safe_model("challenges.Challenge")
        if Challenge:
            team_ids = [t["id"] for t in my_teams]
            c_filter = Q(created_by=user)
            if team_ids:
                c_filter |= Q(team_id__in=team_ids)
            challenges_qs = (
                Challenge.objects.filter(c_filter)
                .exclude(status__in=["CANCELLED", "EXPIRED"])
                .select_related("team", "created_by")
                .order_by("-created_at")[:6]
            )
            for c in challenges_qs:
                gd = game_detail_map.get(getattr(c, "game_id", None), {})
                active_challenges.append({
                    "id": c.id,
                    "title": c.title,
                    "type": getattr(c, "challenge_type", "SCRIM"),
                    "status": c.status,
                    "format": getattr(c, "format", "BO1"),
                    "prize": getattr(c, "prize_amount", 0) or 0,
                    "currency": getattr(c, "prize_currency", "DC"),
                    "team_name": c.team.name if c.team else "",
                    "opponent": getattr(c.opponent_team, "name", "Open") if getattr(c, "opponent_team", None) else "Open",
                    "game_name": gd.get("name", ""),
                    "game_icon": gd.get("icon", ""),
                    "created_at": c.created_at,
                    "expires_at": getattr(c, "expires_at", None),
                })
    except Exception:
        logger.debug("Dashboard: challenges query failed", exc_info=True)

    # ── 19. BOUNTIES ─────────────────────────────────────────────────────
    active_bounties = []
    try:
        Bounty = _safe_model("user_profile.Bounty")
        if Bounty:
            b_filter = Q(creator=user) | Q(acceptor=user)
            bounties_qs = (
                Bounty.objects.filter(b_filter)
                .exclude(status__in=["cancelled", "expired"])
                .select_related("game", "creator", "acceptor")
                .order_by("-created_at")[:6]
            )
            for b in bounties_qs:
                active_bounties.append({
                    "id": b.id,
                    "title": b.title,
                    "status": b.status,
                    "stake": b.stake_amount,
                    "payout": b.payout_amount or 0,
                    "game_name": b.game.name if b.game else "",
                    "game_icon": _img_url(b.game, "icon") if b.game else "",
                    "creator": b.creator.username if b.creator else "",
                    "is_mine": b.creator_id == user.id,
                    "opponent": b.acceptor.username if b.acceptor else "Open",
                    "created_at": b.created_at,
                    "expires_at": b.expires_at,
                })
    except Exception:
        logger.debug("Dashboard: bounties query failed", exc_info=True)

    # ── ASSEMBLE CONTEXT ─────────────────────────────────────────────────
    context = {
        # Profile
        "profile": profile_data,
        # Teams
        "my_teams": my_teams,
        "team_count": len(my_teams),
        # Invites
        "pending_invites": pending_invites,
        "invite_count": len(pending_invites),
        # Matches
        "recent_matches": recent_matches,
        "match_stats": match_stats,
        # Tournaments
        "active_tournaments": active_tournaments,
        "tournament_count": tournament_count,
        "next_match_info": next_match_info,
        "imminent_lobby_alert": imminent_lobby_alert,
        # Leaderboard
        "leaderboard_data": leaderboard_data,
        # Economy
        "wallet": wallet_data,
        # Badges
        "badges": badges,
        # Notifications
        "recent_notifications": recent_notifications,
        "unread_notif_count": unread_notif_count,
        # Social
        "social_stats": social_stats,
        # Orders
        "recent_orders": recent_orders,
        # Organizations
        "my_organizations": my_organizations,
        "org_count": len(my_organizations),
        # Game Passports
        "game_passports": game_passports,
        # Recruitment
        "recruitment_positions": recruitment_positions,
        # Featured Product
        "featured_product": featured_product,
        # Support Tickets
        "support_tickets": support_tickets,
        # Challenges & Bounties
        "active_challenges": active_challenges,
        "active_bounties": active_bounties,
        # Games map (for template use)
        "games": list(game_map.values()),
    }

    # ── BUILD COMMAND CENTER DATA ────────────────────────────────────────
    context["cc_data"] = _build_cc_data(context, user, now)

    return render(request, "dashboard/index.html", context)
