"""
Dashboard Command Center data builder.

Transforms the raw dashboard context dict into the Alpine.js-consumable
``cc_data`` payload for the Command Center frontend component.

Extracted from views.py to keep the God-class under control.
"""

from .helpers import _ts


def build_cc_data(context, user, now):
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
        scheduled_at = imminent.get('scheduled_time')
        scheduled_at_iso = scheduled_at.isoformat() if hasattr(scheduled_at, 'isoformat') else ''
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
            'scheduledAt': scheduled_at_iso,
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
        match_state = ''
        match_time = ''
        match_scheduled_at = ''
        lobby_status = ''
        if (
            slug
            and nmi
            and nmi.get('tournament_slug') == slug
            and nmi.get('match_id')
        ):
            match_state = nmi.get('state', '')
            if nmi.get('scheduled_time'):
                scheduled = nmi.get('scheduled_time')
                if hasattr(scheduled, 'isoformat'):
                    match_scheduled_at = scheduled.isoformat()
                elif scheduled:
                    match_scheduled_at = str(scheduled)
            if nmi.get('lobby_open'):
                lobby_status = 'open'
            elif nmi.get('lobby_status'):
                lobby_status = nmi.get('lobby_status')
            if match_state in ('check_in', 'ready', 'live'):
                match_lobby_url = '/tournaments/%s/matches/%s/room/' % (slug, nmi.get('match_id'))
        cur_stage_raw = tr.get('current_stage', '')
        cur_stage = str(cur_stage_raw).replace('_', ' ').title() if cur_stage_raw else ''
        pp = tr.get('prize_pool')
        try:
            prize_str = '{:,} DC'.format(int(pp)) if pp else '\u2014'
        except (ValueError, TypeError):
            prize_str = str(pp) if pp else '\u2014'
        tournaments.append({
            'id': 'tourney-%s' % tr['id'],
            'name': tr['name'],
            'slug': tr.get('slug', ''),
            'game': tr.get('game_name', ''),
            'gameIcon': tr.get('game_icon', ''),
            'banner': tr.get('banner_url', ''),
            'thumbnail': tr.get('thumbnail_url', ''),
            'status': (tr.get('status') or '').replace('_', ' ').title(),
            'regStatus': (tr.get('reg_status') or '').replace('_', ' ').title(),
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
            'currentStage': cur_stage,
            'matchState': match_state,
            'matchTime': match_time,
            'matchScheduledAt': match_scheduled_at,
            'lobbyStatus': lobby_status,
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
        score = '%s-%s' % (s1, s2) if s1 is not None and s2 is not None else '\u2014'
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
