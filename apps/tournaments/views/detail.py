"""
Tournament Detail View — Public tournament detail page with tabs.

FE-T-002: Tournament Detail Page
FE-T-003: Registration CTA States
Extracted from main.py during Phase 3 restructure.
"""

from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.cache import cache
from datetime import timedelta
from typing import Dict, Any

from apps.tournaments.models import Tournament, TournamentAnnouncement
from apps.tournaments.services.registration_service import RegistrationService
from apps.games.services import game_service


class TournamentDetailView(DetailView):
    """
    FE-T-002: Tournament Detail Page — Unified Master Template

    URL: /tournaments/<slug>/
    Template: tournaments/detailPages/detail.html

    View state and section visibility are still status-aware via context flags,
    but rendering now always uses one canonical template.
    """
    model = Tournament
    template_name = 'tournaments/detailPages/detail.html'
    context_object_name = 'tournament'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return super().get_queryset().select_related('game', 'organizer')

    def dispatch(self, request, *args, **kwargs):
        """Cache entire response for anonymous users on completed tournaments."""
        self.object = self.get_object()
        effective = getattr(self.object, 'get_effective_status', lambda: self.object.status)()
        if not request.user.is_authenticated and effective in ('completed', 'archived'):
            from django.views.decorators.cache import cache_page
            from django.utils.decorators import method_decorator
            cached_view = cache_page(3600, key_prefix='detail_page')(
                super().dispatch
            )
            return cached_view(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Cache get_object to avoid double queries from dispatch + get."""
        if hasattr(self, '_cached_object'):
            return self._cached_object
        self._cached_object = super().get_object(queryset)
        return self._cached_object

    def get_template_names(self):
        """Render the unified detail page for all tournament phases."""
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        user = self.request.user

        # GameService integration
        canonical_slug = game_service.normalize_slug(tournament.game.slug)
        game_spec = game_service.get_game(canonical_slug)
        context['game_spec'] = game_spec

        # Eligibility check — skip expensive service for completed/archived
        effective_status = getattr(tournament, 'get_effective_status', lambda: tournament.status)()
        context['effective_status'] = effective_status
        context['effective_status_display'] = dict(Tournament.STATUS_CHOICES).get(
            effective_status, tournament.get_status_display()
        )
        if effective_status in ('completed', 'archived'):
            context['can_register'] = False
            context['registration_status_reason'] = 'This tournament has ended.'
            context['is_registered'] = False
            context['user_registration'] = None
            context['eligibility_status'] = 'completed'
            context['registration_action_url'] = f'/tournaments/{tournament.slug}/'
            context['registration_action_label'] = 'View Details'
        else:
            from apps.tournaments.services.eligibility_service import RegistrationEligibilityService
            eligibility = RegistrationEligibilityService.check_eligibility(tournament, user)
            context['can_register'] = eligibility['can_register']
            context['registration_status_reason'] = eligibility['reason']
            context['is_registered'] = eligibility['registration'] is not None
            context['user_registration'] = eligibility['registration']
            context['eligibility_status'] = eligibility['status']

            # Use centralized eligibility action contract to keep CTA state consistent
            # across full/waitlist/open/locked states.
            default_label = 'Register Team' if tournament.participation_type == Tournament.TEAM else 'Register Now'
            context['registration_action_url'] = eligibility.get('action_url') or f'/tournaments/{tournament.slug}/register/'
            context['registration_action_label'] = eligibility.get('action_label') or default_label

        if context.get('user_registration') is not None:
            context['registration_action_url'] = reverse('tournaments:tournament_hub', kwargs={'slug': tournament.slug})
            context['registration_action_label'] = 'Go to HUB'

        # Slots info
        from apps.tournaments.models import Registration, Match
        slots_filled = Registration.objects.filter(
            tournament=tournament,
            status__in=[Registration.PENDING, Registration.PAYMENT_SUBMITTED, Registration.CONFIRMED],
            is_deleted=False
        ).count()
        context['slots_filled'] = slots_filled
        context['slots_total'] = tournament.max_participants
        context['slots_percentage'] = (slots_filled / tournament.max_participants * 100) if tournament.max_participants > 0 else 0
        context['organizer_pending_count'] = Registration.objects.filter(
            tournament=tournament,
            status__in=[Registration.PENDING, Registration.PAYMENT_SUBMITTED],
            is_deleted=False
        ).count()
        context['organizer_issue_count'] = Match.objects.filter(
            tournament=tournament,
            state='disputed',
            is_deleted=False
        ).count()

        # Announcements
        announcements = TournamentAnnouncement.objects.filter(
            tournament=tournament
        ).select_related('created_by').order_by('-is_pinned', '-created_at')[:10]
        context['announcements'] = announcements

        # Participants tab
        context.update(self._get_participants_context(tournament, user))

        # Bracket context
        from apps.tournaments.models import Bracket
        try:
            bracket = tournament.bracket
            context['bracket'] = bracket
        except Bracket.DoesNotExist:
            context['bracket'] = None

        # Multi-stage tournament context
        if tournament.format == Tournament.GROUP_PLAYOFF:
            context['is_multi_stage'] = True
            current_stage = tournament.get_current_stage()
            context['current_stage'] = current_stage
            context['current_stage_label'] = (
                current_stage.replace('_', ' ').title() if current_stage else ''
            )
            config = tournament.config or {}
            context['stages'] = config.get('stages', [])

            from apps.tournaments.models import Group, GroupStanding
            groups = list(Group.objects.filter(
                tournament=tournament,
                is_deleted=False
            ).order_by('display_order'))
            context['groups'] = groups

            # Batch-load all group standings in 1 query (not N+1 per group)
            all_gs = GroupStanding.objects.filter(
                group__in=groups,
                is_deleted=False
            ).order_by('group_id', 'rank').select_related('group', 'user')
            group_standings = {}
            for gs in all_gs:
                group_standings.setdefault(gs.group_id, []).append(gs)
            context['group_standings'] = group_standings
        else:
            context['is_multi_stage'] = False
            context['current_stage'] = None
            context['current_stage_label'] = ''

        # Matches tab
        context.update(self._get_matches_context(tournament))

        # Standings tab
        context.update(self._get_standings_context(tournament))

        # Streams tab
        context.update(self._get_streams_context(tournament))

        # Phase-specific context
        context.update(self._get_phase_context(tournament, user))

        # Unified hero/sidebar/runtime CTA inputs (single source of truth for viewer state).
        detail_action_input_context = _build_detail_action_input_context(
            tournament,
            user,
            base_context=context,
            now=timezone.now(),
        )
        context.update(detail_action_input_context)
        context.update(_build_detail_action_context(tournament, user, context=detail_action_input_context))

        # Detailed registration status (wire up the dead code at _get_registration_status)
        if user.is_authenticated and context.get('is_registered'):
            try:
                context['registration_detail_status'] = self._get_registration_status(tournament, user)
            except Exception:
                context['registration_detail_status'] = None
        else:
            context['registration_detail_status'] = None

        # CoinPolicy — DeltaCoin rewards for this tournament
        try:
            from apps.economy.models import CoinPolicy
            coin_policy = CoinPolicy.objects.filter(
                tournament_id=tournament.id, enabled=True
            ).first()
            context['coin_policy'] = coin_policy
        except Exception:
            context['coin_policy'] = None

        # Social links presence flag (avoids empty card rendering)
        context['has_social_links'] = any([
            tournament.social_discord, tournament.social_twitter,
            tournament.social_instagram, tournament.social_youtube,
            tournament.social_facebook, tournament.social_tiktok,
            tournament.social_website, tournament.contact_email,
        ])

        # Spectator page link (for live/completed tournaments)
        if effective_status in ['live', 'completed', 'archived']:
            context['spectator_url'] = f'/tournaments/{tournament.slug}/spectate/'

        # Lightweight mobile polling endpoint for real-time header/slots/match updates.
        context['mobile_state_url'] = reverse('tournaments:detail_mobile_state', kwargs={'slug': tournament.slug})

        # Match settings and tournament info for format/rules display
        # Match settings — flatten nested 'values' dict into display-friendly pairs
        raw_ms = tournament.match_settings or {}
        formatted_settings = []
        skip_keys = {'available_maps', 'game_key', 'schema_version', 'version'}
        # If match_settings has a 'values' sub-dict, flatten it
        values_dict = raw_ms.get('values', {}) if isinstance(raw_ms.get('values'), dict) else {}
        source = values_dict or raw_ms
        for k, v in source.items():
            if k in skip_keys:
                continue
            # Skip nested dicts/lists
            if isinstance(v, (dict, list)):
                continue
            label = k.replace('_', ' ').title()
            # Format boolean values
            if isinstance(v, bool):
                display_val = 'On' if v else 'Off'
            else:
                display_val = str(v)
            formatted_settings.append({'label': label, 'value': display_val})
        context['match_settings'] = raw_ms
        context['match_settings_display'] = formatted_settings
        context['tournament_config'] = tournament.config or {}
        context['tournament_format_label'] = tournament.get_format_display()
        context['tournament_platform_label'] = tournament.get_platform_display()
        context['tournament_mode_label'] = tournament.get_mode_display()
        context['tournament_participation_label'] = tournament.get_participation_type_display()
        context['is_group_playoff'] = tournament.format == Tournament.GROUP_PLAYOFF

        return context

    def _get_phase_context(self, tournament, user):
        """Build phase-specific context for the dynamic detail view."""
        effective = getattr(tournament, 'get_effective_status', lambda: tournament.status)()
        if effective in ('completed', 'archived'):
            cache_key = f'detail_phase_{tournament.id}'
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        now = timezone.now()
        status = effective

        phase_ctx = {
            'tournament_phase': status,
            'is_registration_phase': status in [
                'draft', 'pending_approval', 'published',
                'registration_open', 'registration_closed'
            ],
            'is_live_phase': status == 'live',
            'is_completed_phase': status in ['completed', 'archived'],
            'is_cancelled': status == 'cancelled',
        }

        # ── State-based section visibility flags ─────────────────────────
        # These control which sections render in the templates.
        phase_ctx['show_participants'] = status not in ['draft', 'pending_approval']
        phase_ctx['show_registration_cta'] = status == 'registration_open'
        phase_ctx['show_countdown'] = status in [
            'registration_open', 'registration_closed', 'published',
        ]
        phase_ctx['show_schedule'] = True  # always visible
        phase_ctx['show_prizes'] = True    # always visible
        phase_ctx['show_rules'] = True     # always visible
        phase_ctx['show_announcements'] = status not in ['draft', 'pending_approval']
        phase_ctx['show_bracket'] = status in ['live', 'completed', 'archived']
        phase_ctx['show_matches'] = status in ['live', 'completed', 'archived']
        phase_ctx['show_standings'] = status in ['live', 'completed', 'archived']
        phase_ctx['show_streams'] = status in ['live']
        phase_ctx['show_checkin_info'] = status == 'registration_closed'
        phase_ctx['is_pre_registration'] = status in ['draft', 'pending_approval', 'published']

        phase_ctx.update({
            'user_next_match': None,
            'user_next_match_lobby_open': False,
            'user_next_match_lobby_opens_at': None,
            'user_next_match_lobby_closes_at': None,
            'user_next_match_lobby_state': None,
            'viewer_participant_ids': [],
            'viewer_is_registered_participant': False,
        })

        if status not in ['completed', 'archived', 'cancelled']:
            phase_ctx.update(_resolve_user_next_match_context(tournament, user, now=now))

        # Registration phase extras
        if phase_ctx['is_registration_phase']:
            # Countdown targets
            if tournament.status == 'registration_open' and tournament.registration_end:
                phase_ctx['countdown_target'] = tournament.registration_end.isoformat()
                phase_ctx['countdown_label'] = 'Registration closes in'
            elif tournament.status in ['registration_closed', 'published'] and tournament.tournament_start:
                phase_ctx['countdown_target'] = tournament.tournament_start.isoformat()
                phase_ctx['countdown_label'] = 'Tournament starts in'
            elif tournament.status == 'registration_open' and not tournament.registration_end and tournament.tournament_start:
                phase_ctx['countdown_target'] = tournament.tournament_start.isoformat()
                phase_ctx['countdown_label'] = 'Tournament starts in'
            else:
                phase_ctx['countdown_target'] = None
                phase_ctx['countdown_label'] = None

            # Check-in info
            phase_ctx['is_checkin_phase'] = tournament.status == 'registration_closed'
            phase_ctx['checkin_enabled'] = getattr(tournament, 'enable_check_in', False)

            # Registration window info
            phase_ctx['registration_is_open'] = tournament.status == 'registration_open'
            phase_ctx['registration_opens_at'] = tournament.registration_start.isoformat() if tournament.registration_start else None
            phase_ctx['registration_closes_at'] = tournament.registration_end.isoformat() if tournament.registration_end else None

        # Live phase extras
        if phase_ctx['is_live_phase']:
            from apps.tournaments.models import Match
            live_matches = Match.objects.filter(
                tournament=tournament,
                state='live',
                is_deleted=False
            ).order_by('round_number', 'match_number')

            phase_ctx['live_match_count'] = live_matches.count()

            total_matches = Match.objects.filter(
                tournament=tournament,
                is_deleted=False
            ).exclude(state='cancelled').count()
            completed_matches = Match.objects.filter(
                tournament=tournament,
                state__in=['completed', 'forfeit'],
                is_deleted=False
            ).count()

            # ── Group-playoff stage-aware progress ───────────────────
            # When group stage is complete (knockout_stage active), the
            # cancelled group matches still represent completed work.
            # Use GroupStanding records as evidence of group completion.
            is_gp = tournament.format == Tournament.GROUP_PLAYOFF
            current_stage = getattr(tournament, 'get_current_stage', lambda: None)()
            group_stage_done = False
            group_match_count = 0
            knockout_total = total_matches
            knockout_completed = completed_matches

            if is_gp and current_stage == 'knockout_stage':
                from apps.tournaments.models.group import GroupStanding
                group_stage_done = GroupStanding.objects.filter(
                    group__tournament=tournament, is_deleted=False
                ).exists()
                if group_stage_done:
                    group_match_count = Match.objects.filter(
                        tournament=tournament, is_deleted=False,
                        bracket__isnull=True
                    ).count()
                    knockout_total = Match.objects.filter(
                        tournament=tournament, is_deleted=False,
                        bracket__isnull=False
                    ).count()
                    knockout_completed = Match.objects.filter(
                        tournament=tournament, is_deleted=False,
                        bracket__isnull=False,
                        state__in=['completed', 'forfeit']
                    ).count()

            phase_ctx['group_stage_done'] = group_stage_done
            phase_ctx['group_match_count'] = group_match_count
            phase_ctx['knockout_total'] = knockout_total
            phase_ctx['knockout_completed'] = knockout_completed

            if group_stage_done:
                eff_total = group_match_count + knockout_total
                eff_completed = group_match_count + knockout_completed
            else:
                eff_total = total_matches
                eff_completed = completed_matches

            phase_ctx['total_match_count'] = eff_total
            phase_ctx['completed_match_count'] = eff_completed
            phase_ctx['match_progress_pct'] = (
                round(eff_completed / eff_total * 100) if eff_total > 0 else 0
            )

            # Current round
            current_round = live_matches.values_list('round_number', flat=True).first()
            phase_ctx['current_round'] = current_round

            # Bracket info
            try:
                bracket = tournament.bracket
                phase_ctx['total_rounds'] = bracket.total_rounds
            except Exception:
                phase_ctx['total_rounds'] = None

        # Completed phase extras
        if phase_ctx['is_completed_phase']:
            from apps.tournaments.models.result import TournamentResult
            try:
                result = TournamentResult.objects.select_related(
                    'winner', 'runner_up', 'third_place',
                ).get(tournament=tournament, is_deleted=False)

                from types import SimpleNamespace
                from apps.tournaments.models.prize import PrizeTransaction

                # Build prize lookup  {registration_id: amount}
                prize_lookup = dict(
                    PrizeTransaction.objects.filter(
                        tournament=tournament,
                    ).values_list('participant_id', 'amount')
                )

                podium = []
                for reg in [result.winner, result.runner_up, result.third_place]:
                    if reg is None:
                        continue
                    podium.append(SimpleNamespace(
                        team=reg.team,           # Registration.team @property resolves team_id -> Team
                        player=reg.user if reg.user_id else None,
                        prize_amount=prize_lookup.get(reg.id),
                    ))
                phase_ctx['podium'] = podium
            except TournamentResult.DoesNotExist:
                phase_ctx['podium'] = []
            except Exception:
                phase_ctx['podium'] = []

            from apps.tournaments.models import Match
            total = Match.objects.filter(
                tournament=tournament, is_deleted=False
            ).exclude(state='cancelled').count()
            phase_ctx['total_matches_played'] = total

        if effective in ('completed', 'archived'):
            cache.set(f'detail_phase_{tournament.id}', phase_ctx, 3600)

        return phase_ctx

    def _get_registration_status(self, tournament, user):
        """Get detailed registration validation status."""
        from apps.tournaments.models import Registration
        from apps.tournaments.services.check_in_service import CheckInService

        try:
            registration = Registration.objects.get(
                tournament=tournament,
                user=user,
                is_deleted=False
            )
        except Registration.DoesNotExist:
            return {'state': 'not_registered', 'reason': 'Not registered'}

        if hasattr(tournament, 'has_entry_fee') and tournament.has_entry_fee:
            if hasattr(registration, 'payment_status'):
                if registration.payment_status == Registration.PAYMENT_PENDING:
                    return {
                        'state': 'payment_pending',
                        'reason': f'Payment required: ${tournament.entry_fee}. Please submit payment proof.',
                        'payment_status': 'pending',
                    }
                elif registration.payment_status == Registration.PAYMENT_SUBMITTED:
                    return {
                        'state': 'approval_pending',
                        'reason': 'Payment submitted. Waiting for organizer approval.',
                        'payment_status': 'submitted',
                    }

        if hasattr(tournament, 'requires_approval') and tournament.requires_approval:
            if hasattr(registration, 'status'):
                if registration.status == Registration.PENDING:
                    return {
                        'state': 'approval_pending',
                        'reason': 'Your registration is awaiting organizer approval.',
                        'approval_status': 'pending',
                    }

        check_in_window = {
            'opens_at': CheckInService.get_check_in_opens_at(tournament),
            'closes_at': CheckInService.get_check_in_closes_at(tournament),
            'is_open': CheckInService.is_check_in_window_open(tournament),
        }

        now = timezone.now()
        _tf = getattr(getattr(self, 'request', None), 'user_platform_prefs', {}).get('time_format', '12h') if hasattr(self, 'request') else '12h'

        if registration.checked_in:
            return {
                'state': 'checked_in',
                'reason': f'Checked in at {_format_display_datetime(registration.checked_in_at, _tf)}',
                'check_in_window': check_in_window,
            }

        if check_in_window['is_open']:
            return {
                'state': 'check_in_required',
                'reason': f'Check-in required before {_format_display_datetime(check_in_window["closes_at"], _tf)}',
                'check_in_window': check_in_window,
            }

        if check_in_window['opens_at'] and now < check_in_window['opens_at']:
            return {
                'state': 'confirmed',
                'reason': f'Registration confirmed. Check-in opens {_format_display_datetime(check_in_window["opens_at"], _tf)}',
                'check_in_window': check_in_window,
            }

        return {
            'state': 'confirmed',
            'reason': 'Registration confirmed',
        }

    def _get_participants_context(self, tournament, user):
        """Get context data for Participants tab."""
        if tournament.status in ('completed', 'archived'):
            cache_user_key = user.id if user.is_authenticated else 'anon'
            cache_key = f'detail_participants_{tournament.id}_{cache_user_key}'
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        from apps.tournaments.models import Registration
        from apps.organizations.models import Team

        registrations_qs = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).exclude(
            status__in=[Registration.CANCELLED, Registration.REJECTED]
        ).select_related('user', 'user__profile').order_by('registered_at')

        participants_list = []
        current_user_registration = None

        if tournament.participation_type == 'team':
            # Batch-load all teams + memberships in 2 queries (not N+1)
            team_ids = [reg.team_id for reg in registrations_qs if reg.team_id]
            teams_map = {}
            if team_ids:
                teams_qs = Team.objects.filter(
                    id__in=team_ids
                ).prefetch_related('vnext_memberships__user__profile')
                teams_map = {t.id: t for t in teams_qs}

            # Batch-load rankings in 1 query
            rankings_map = {}
            try:
                from apps.leaderboards.models import TeamRanking as LBTeamRanking
                rankings = LBTeamRanking.objects.filter(
                    team_id__in=team_ids
                ).values('team_id', 'elo_rating')
                ranked_list = sorted(rankings, key=lambda r: r['elo_rating'], reverse=True)
                for idx, r in enumerate(ranked_list, 1):
                    if r['elo_rating'] > 0:
                        rankings_map[r['team_id']] = idx
            except Exception:
                pass

            for reg in registrations_qs:
                if not reg.team_id:
                    continue

                team = teams_map.get(reg.team_id)
                if not team:
                    continue

                # Use prefetched memberships (no extra queries)
                active_members = [
                    m for m in team.vnext_memberships.all() if m.status == 'ACTIVE'
                ]

                roster_summary = []
                roster_avatars = []
                for membership in active_members[:5]:
                    m_profile = membership.user.profile if hasattr(membership.user, 'profile') else None
                    m_name = m_profile.display_name if m_profile and m_profile.display_name else membership.user.username
                    roster_summary.append({
                        'name': m_name,
                        'role': membership.get_role_display(),
                    })
                    roster_avatars.append({
                        'name': m_name,
                        'avatar': m_profile.avatar.url if m_profile and m_profile.avatar else None,
                    })

                is_current_user_team = False
                if user.is_authenticated:
                    is_current_user_team = any(m.user_id == user.id for m in active_members)
                    if is_current_user_team:
                        current_user_registration = reg

                member_count = len(active_members)
                team_rank = rankings_map.get(team.id)

                participants_list.append({
                    'type': 'team',
                    'kind': 'team',
                    'badge_label': 'TEAM',
                    'id': team.id,
                    'name': team.name,
                    'display_name': team.name,
                    'tag': team.tag,
                    'slug': team.slug,
                    'logo': team.logo.url if team.logo else None,
                    'region': team.region,
                    'game': team.game,
                    'rank': team_rank,
                    'roster_count': member_count,
                    'roster_summary': roster_summary,
                    'roster_avatars': roster_avatars,
                    'sub_label': f"{member_count} players" + (f" · {team.region}" if team.region else ""),
                    'status': reg.status,
                    'checked_in': reg.checked_in,
                    'registered_at': reg.registered_at,
                    'is_current_user': is_current_user_team,
                    'registration_id': reg.id,
                })
        else:
            for reg in registrations_qs:
                if not reg.user:
                    continue

                is_current_user = user.is_authenticated and reg.user.id == user.id
                if is_current_user:
                    current_user_registration = reg

                profile = reg.user.profile if hasattr(reg.user, 'profile') else None
                display_name = profile.display_name if profile and profile.display_name else reg.user.username

                game_id = ''
                if reg.registration_data and isinstance(reg.registration_data, dict):
                    game_id = reg.registration_data.get('game_id', '')

                region = profile.region if profile and hasattr(profile, 'region') else ''
                participants_list.append({
                    'type': 'solo',
                    'kind': 'player',
                    'badge_label': 'PLAYER',
                    'id': reg.user.id,
                    'name': display_name,
                    'display_name': display_name,
                    'username': reg.user.username,
                    'avatar': profile.avatar.url if profile and profile.avatar else None,
                    'game_id': game_id,
                    'region': region,
                    'sub_label': region if region else "",
                    'status': reg.status,
                    'checked_in': reg.checked_in,
                    'registered_at': reg.registered_at,
                    'is_current_user': is_current_user,
                    'registration_id': reg.id,
                })

        confirmed_count = registrations_qs.filter(status=Registration.CONFIRMED).count()
        waitlist_count = 0

        result = {
            'participants': participants_list,
            'participants_total': len(participants_list),
            'participants_confirmed': confirmed_count,
            'participants_waitlist': waitlist_count,
            'current_user_registration': current_user_registration,
        }

        if tournament.status in ('completed', 'archived'):
            cache_user_key = user.id if user.is_authenticated else 'anon'
            cache.set(f'detail_participants_{tournament.id}_{cache_user_key}', result, 3600)

        return result

    def _get_matches_context(self, tournament):
        """Build matches context for Matches tab."""
        if tournament.status in ('completed', 'archived'):
            cache_key = f'detail_matches_{tournament.id}'
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        from apps.tournaments.models import Match, Group
        from apps.organizations.models import Team

        matches_qs = Match.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).exclude(
            state='cancelled'
        ).select_related('bracket').order_by(
            'scheduled_time',
            'round_number',
            'match_number'
        )

        all_participant_ids = set()
        for match in matches_qs:
            if match.participant1_id:
                all_participant_ids.add(match.participant1_id)
            if match.participant2_id:
                all_participant_ids.add(match.participant2_id)

        teams_map = {}
        teams_logo_map = {}
        if tournament.participation_type == 'team' and all_participant_ids:
            teams = Team.objects.filter(id__in=all_participant_ids)
            teams_map = {team.id: team.name for team in teams}
            teams_logo_map = {team.id: team.logo.url if team.logo else None for team in teams}
        elif tournament.participation_type == 'solo' and all_participant_ids:
            # Fetch user avatars for solo tournaments
            from apps.user_profile.models_main import UserProfile
            for up in UserProfile.objects.filter(user_id__in=all_participant_ids).select_related('user').only('user_id', 'avatar'):
                try:
                    teams_logo_map[up.user_id] = up.avatar.url if up.avatar else None
                except Exception:
                    teams_logo_map[up.user_id] = None

        # Pre-fetch group names for group_playoff format
        groups_map = {}
        if tournament.format == 'group_playoff':
            for g in Group.objects.filter(tournament=tournament, is_deleted=False):
                groups_map[g.id] = g.name

        matches_list = []
        now = timezone.now()
        _tf = getattr(getattr(self, 'request', None), 'user_platform_prefs', {}).get('time_format', '12h') if hasattr(self, 'request') else '12h'

        for match in matches_qs:
            if tournament.format == tournament.GROUP_PLAYOFF:
                phase = 'group_stage' if match.bracket is None else 'knockout_stage'
            else:
                phase = 'knockout_stage'

            if match.state == 'live':
                ui_status = 'live'
            elif match.state in ['completed', 'forfeit', 'cancelled', 'disputed']:
                ui_status = 'completed'
            else:
                ui_status = 'upcoming'

            is_live = match.state == 'live'
            is_completed = match.state in ['completed', 'forfeit', 'cancelled']
            show_scores = match.state in ['live', 'completed', 'pending_result', 'disputed']

            winner = None
            if match.winner_id:
                if match.winner_id == match.participant1_id:
                    winner = 1
                elif match.winner_id == match.participant2_id:
                    winner = 2

            group_name = ''
            group_id = None
            round_label = ''

            # Resolve group name from lobby_info for group stage matches
            if phase == 'group_stage':
                lobby = match.lobby_info or {}
                gid = lobby.get('group_id')
                if gid:
                    group_id = gid
                    group_name = groups_map.get(gid, '')

            if phase == 'knockout_stage' and match.round_number:
                # For double-elimination, round_number maps sequentially:
                # UB-R1=1, UB-QF=2, UB-SF=3, UB-F=4, LB-R1=5..LB-F=10, GF=11
                # For single-elimination: round 1=R1, last=Final
                if tournament.format == 'double_elimination':
                    de_round_labels = {
                        1: 'UB Round 1', 2: 'UB Quarter-Final', 3: 'UB Semi-Final', 4: 'UB Final',
                        5: 'LB Round 1', 6: 'LB Round 2', 7: 'LB Round 3', 8: 'LB Round 4',
                        9: 'LB Semi-Final', 10: 'LB Final', 11: 'Grand Final',
                    }
                    round_label = de_round_labels.get(match.round_number, f'Round {match.round_number}')
                else:
                    # Single-elim: highest round_number = final
                    if match.round_number == 1:
                        round_label = 'Final'
                    elif match.round_number == 2:
                        round_label = 'Semi-Finals'
                    elif match.round_number == 3:
                        round_label = 'Quarter-Finals'
                    else:
                        round_label = f'Round of {2 ** match.round_number}'

            stage_label = ''
            if phase == 'group_stage' and group_name:
                stage_label = group_name
                if match.round_number:
                    stage_label += f" — Round {match.round_number}"
            elif phase == 'knockout_stage' and round_label:
                stage_label = round_label
            elif match.round_number:
                stage_label = f"Round {match.round_number}"

            match_label = f"Match #{match.match_number}" if match.match_number else "Match"

            start_time_display = ''
            if match.scheduled_time:
                start_time_display = _format_display_datetime(match.scheduled_time, _tf)

            p1_name = 'TBD'
            p2_name = 'TBD'
            p1_logo = None
            p2_logo = None

            if match.participant1_id:
                p1_name = teams_map.get(match.participant1_id) or match.participant1_name or 'TBD'
                p1_logo = teams_logo_map.get(match.participant1_id)
            elif match.participant1_name:
                p1_name = match.participant1_name

            if match.participant2_id:
                p2_name = teams_map.get(match.participant2_id) or match.participant2_name or 'TBD'
                p2_logo = teams_logo_map.get(match.participant2_id)
            elif match.participant2_name:
                p2_name = match.participant2_name

            team1_is_winner = winner == 1
            team2_is_winner = winner == 2

            starts_at = match.scheduled_time
            starts_at_relative = ''
            if starts_at:
                delta = starts_at - now
                if delta.total_seconds() > 0:
                    hours = int(delta.total_seconds() // 3600)
                    minutes = int((delta.total_seconds() % 3600) // 60)
                    if hours > 24:
                        days = hours // 24
                        starts_at_relative = f"Starts in {days}d"
                    elif hours > 0:
                        starts_at_relative = f"Starts in {hours}h {minutes}m"
                    else:
                        starts_at_relative = f"Starts in {minutes}m"
                else:
                    hours = int(abs(delta.total_seconds()) // 3600)
                    if is_completed:
                        if hours > 24:
                            days = hours // 24
                            starts_at_relative = f"Finished {days}d ago"
                        elif hours > 0:
                            starts_at_relative = f"Finished {hours}h ago"
                        else:
                            starts_at_relative = "Finished recently"

            lobby_info = match.lobby_info or {}
            best_of_label = ''
            if match.best_of and match.best_of > 1:
                best_of_label = f"BO{match.best_of}"
            elif lobby_info.get('best_of'):
                best_of_label = f"BO{lobby_info['best_of']}"

            # Parse per-map scores from game_scores
            map_scores = []
            gs = match.game_scores or {}
            gs_maps = gs.get('maps', []) if isinstance(gs, dict) else gs if isinstance(gs, list) else []
            for gm in gs_maps:
                map_scores.append({
                    'map_name': gm.get('map', gm.get('map_name', '')),
                    'p1_score': gm.get('p1', gm.get('p1_score', gm.get('team1_rounds', 0))),
                    'p2_score': gm.get('p2', gm.get('p2_score', gm.get('team2_rounds', 0))),
                    'winner_side': gm.get('winner_side', gm.get('winner_slot', 0)),
                })

            matches_list.append({
                'id': match.id,
                'match_number': match.match_number,
                'participant1_name': p1_name,
                'participant2_name': p2_name,
                'participant1_score': match.participant1_score if show_scores else 0,
                'participant2_score': match.participant2_score if show_scores else 0,
                'state': match.state,
                'status': ui_status,
                'ui_status': ui_status,
                'phase': phase,
                'is_live': is_live,
                'is_completed': is_completed,
                'show_scores': show_scores,
                'winner': winner,
                'round_label': round_label,
                'stage_label': stage_label,
                'match_label': match_label,
                'group_name': group_name,
                'group_id': group_id,
                'start_time_display': start_time_display,
                'starts_at': starts_at,
                'starts_at_display': start_time_display,
                'starts_at_relative': starts_at_relative,
                'team1_name': p1_name,
                'team2_name': p2_name,
                'team1_id': match.participant1_id,
                'team2_id': match.participant2_id,
                'team1_logo_url': p1_logo,
                'team2_logo_url': p2_logo,
                'team1_is_winner': team1_is_winner,
                'team2_is_winner': team2_is_winner,
                'score1': match.participant1_score if show_scores else None,
                'score2': match.participant2_score if show_scores else None,
                'best_of_label': best_of_label,
                'stream_url': match.stream_url,
                'vod_url': None,
                'participant1_logo': p1_logo,
                'participant2_logo': p2_logo,
                'lobby_info': lobby_info,
                'round_number': match.round_number,
                'winner_id': match.winner_id,
                'map_scores': map_scores,
                'best_of': match.best_of,
                'bracket_type': 'losers' if (tournament.format == 'double_elimination' and match.round_number and 5 <= match.round_number <= 10) else 'main',
            })

        # Enrich matches with MVP info + per-player scoreboard from MatchPlayerStat
        try:
            from apps.tournaments.models.match_player_stats import MatchPlayerStat, MatchMapPlayerStat
            match_ids = [m['id'] for m in matches_list]

            # MVP lookup
            mvps = MatchPlayerStat.objects.filter(
                match_id__in=match_ids, is_mvp=True
            ).select_related('player').values_list('match_id', 'player__username')
            mvp_map = {mid: uname for mid, uname in mvps}

            # Full per-player stats grouped by match
            all_stats = MatchPlayerStat.objects.filter(
                match_id__in=match_ids
            ).select_related('player').order_by('-acs')

            stats_by_match = {}
            for s in all_stats:
                stats_by_match.setdefault(s.match_id, []).append({
                    'player_name': s.player.username if s.player else '?',
                    'display_name': getattr(s.player, 'first_name', '') or s.player.username,
                    'team_id': s.team_id,
                    'agent': s.agent,
                    'kills': s.kills,
                    'deaths': s.deaths,
                    'assists': s.assists,
                    'kd_ratio': float(s.kd_ratio) if s.kd_ratio else 0,
                    'acs': float(s.acs) if s.acs else 0,
                    'adr': float(s.adr) if s.adr else 0,
                    'hs_pct': float(s.headshot_pct) if s.headshot_pct else 0,
                    'first_kills': s.first_kills,
                    'first_deaths': s.first_deaths,
                    'clutches': s.clutches,
                    'is_mvp': s.is_mvp,
                })

            # Per-map stats
            all_map_stats = MatchMapPlayerStat.objects.filter(
                match_id__in=match_ids
            ).select_related('player').order_by('map_number', '-acs')

            map_stats_by_match = {}
            for ms in all_map_stats:
                key = ms.match_id
                map_stats_by_match.setdefault(key, {})
                map_stats_by_match[key].setdefault(ms.map_number, []).append({
                    'player_name': ms.player.username if ms.player else '?',
                    'display_name': getattr(ms.player, 'first_name', '') or ms.player.username,
                    'team_id': ms.team_id,
                    'agent': ms.agent,
                    'map_name': ms.map_name,
                    'kills': ms.kills,
                    'deaths': ms.deaths,
                    'assists': ms.assists,
                    'acs': float(ms.acs) if ms.acs else 0,
                    'adr': float(ms.adr) if ms.adr else 0,
                    'hs_pct': float(ms.headshot_pct) if ms.headshot_pct else 0,
                    'first_kills': ms.first_kills,
                    'first_deaths': ms.first_deaths,
                })

            for m in matches_list:
                mid = m['id']
                m['mvp_name'] = mvp_map.get(mid, '')
                m['player_stats'] = stats_by_match.get(mid, [])
                # Split player stats by team for template rendering
                t1_stats = [s for s in m['player_stats'] if s.get('team_id') == m.get('team1_id')]
                t2_stats = [s for s in m['player_stats'] if s.get('team_id') == m.get('team2_id')]
                # If team_id matching fails, split by order (first 5 = team1, next 5 = team2)
                if not t1_stats and not t2_stats and m['player_stats']:
                    half = len(m['player_stats']) // 2
                    t1_stats = m['player_stats'][:half]
                    t2_stats = m['player_stats'][half:]
                m['team1_stats'] = t1_stats
                m['team2_stats'] = t2_stats
                # Map-level stats as ordered list of dicts
                match_maps = map_stats_by_match.get(mid, {})
                m['map_player_stats'] = [
                    {'map_number': mn, 'players': match_maps[mn]}
                    for mn in sorted(match_maps.keys())
                ]
        except Exception:
            for m in matches_list:
                m['mvp_name'] = ''
                m['player_stats'] = []
                m['team1_stats'] = []
                m['team2_stats'] = []
                m['map_player_stats'] = []

        result = {'matches': matches_list, 'matches_reversed': list(reversed(matches_list))}

        if tournament.status in ('completed', 'archived'):
            cache.set(f'detail_matches_{tournament.id}', result, 3600)

        return result

    def _get_standings_context(self, tournament: Tournament) -> Dict[str, Any]:
        """Build standings context for Standings tab."""
        if tournament.status in ('completed', 'archived'):
            cache_key = f'detail_standings_{tournament.id}'
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        from apps.tournaments.models.group import Group, GroupStanding
        from django.db.models import Q

        context = {
            'standings_primary': [],
            'standings_source': 'unknown',
            'group_standings_summary': None
        }

        if tournament.format == 'group_playoff':
            groups = Group.objects.filter(
                tournament=tournament,
                is_deleted=False
            ).order_by('display_order')

            if not groups.exists():
                return context

            # Pre-fetch team names for all group standings with team_id
            all_group_standings = GroupStanding.objects.filter(
                group__tournament=tournament,
                is_deleted=False,
            ).exclude(team_id__isnull=True).values_list('team_id', flat=True)
            team_ids = list(set(all_group_standings))
            team_name_map = {}
            team_logo_map = {}
            if team_ids:
                from apps.organizations.models import Team as OrgTeam
                for t in OrgTeam.objects.filter(id__in=team_ids).only('id', 'name', 'logo'):
                    team_name_map[t.id] = t.name
                    try:
                        team_logo_map[t.id] = t.logo.url if t.logo else ''
                    except Exception:
                        team_logo_map[t.id] = ''

            all_standings = []
            group_summaries = []

            for group in groups:
                group_standings = GroupStanding.objects.filter(
                    group=group,
                    is_deleted=False
                ).select_related('user').order_by('rank')

                advancers = []
                others = []

                for idx, standing in enumerate(group_standings, start=1):
                    if standing.team_id:
                        participant_name = team_name_map.get(standing.team_id, f"Team {standing.team_id}")
                        participant_id = f"team-{standing.team_id}"
                    elif standing.user:
                        participant_name = standing.user.profile.display_name if hasattr(standing.user, 'profile') and standing.user.profile.display_name else standing.user.username
                        participant_id = f"user-{standing.user.id}"
                    else:
                        participant_name = "Unknown"
                        participant_id = "unknown"

                    is_advancing = idx <= group.advancement_count

                    # Resolve logo/avatar for standings row
                    if standing.team_id:
                        row_logo = team_logo_map.get(standing.team_id, '')
                    elif standing.user:
                        try:
                            profile = standing.user.profile if hasattr(standing.user, 'profile') else None
                            row_logo = profile.avatar.url if profile and profile.avatar else ''
                        except Exception:
                            row_logo = ''
                    else:
                        row_logo = ''

                    row = {
                        'rank': standing.rank or idx,
                        'name': participant_name,
                        'participant_id': participant_id,
                        'logo_url': row_logo,
                        'group_name': group.name,
                        'matches_played': standing.matches_played,
                        'wins': standing.matches_won,
                        'draws': standing.matches_drawn,
                        'losses': standing.matches_lost,
                        'points': int(standing.points),
                        'is_advancing': is_advancing,
                        'goal_difference': standing.goal_difference if standing.goal_difference != 0 else None,
                        'round_difference': standing.round_difference if standing.round_difference != 0 else None,
                        'kill_difference': standing.total_kills - standing.total_deaths if (standing.total_kills > 0 or standing.total_deaths > 0) else None,
                        'game_specific_label': None
                    }

                    all_standings.append(row)

                    # Get logo for summary
                    summary_logo = ''
                    if standing.team_id:
                        summary_logo = team_logo_map.get(standing.team_id, '')
                    elif standing.user:
                        try:
                            profile = standing.user.profile if hasattr(standing.user, 'profile') else None
                            summary_logo = profile.avatar.url if profile and profile.avatar else ''
                        except Exception:
                            summary_logo = ''

                    summary_entry = {
                        'rank': idx,
                        'name': participant_name,
                        'logo_url': summary_logo
                    }

                    if is_advancing:
                        advancers.append(summary_entry)
                    else:
                        others.append(summary_entry)

                group_summaries.append({
                    'name': group.name,
                    'advancers': advancers,
                    'others': others
                })

            # Sort by group display order, then rank within group
            # This keeps groups contiguous for template regroup
            group_order = {g.name: g.display_order for g in groups}
            all_standings.sort(key=lambda x: (
                group_order.get(x['group_name'], 999),
                x['rank']
            ))

            for idx, row in enumerate(all_standings, start=1):
                row['global_rank'] = idx

            context['standings_primary'] = all_standings
            context['standings_source'] = 'group_stage'
            context['group_standings_summary'] = group_summaries

        else:
            from apps.tournaments.models import Registration, Match
            from apps.organizations.models import Team
            from apps.tournaments.models.prize import PrizeTransaction

            registrations = Registration.objects.filter(
                tournament=tournament,
                is_deleted=False,
                status__in=['confirmed', 'checked_in']
            ).select_related('user')

            if not registrations.exists():
                return context

            team_ids = [reg.team_id for reg in registrations if reg.team_id]
            teams_map = {team.id: team for team in Team.objects.filter(id__in=team_ids)} if team_ids else {}

            # Prize lookup: participant_id (Registration.id) → amount
            prize_lookup = dict(
                PrizeTransaction.objects.filter(
                    tournament=tournament,
                ).values_list('participant_id', 'amount')
            )
            # Build reg_id → team mapping for prize resolution
            reg_prize_map = {}
            for reg in registrations:
                if reg.id in prize_lookup:
                    pid = reg.team_id or (reg.user_id if reg.user else None)
                    if pid:
                        reg_prize_map[pid] = prize_lookup[reg.id]

            standings_rows = []

            # Batch-load all completed matches once (not per participant)
            all_matches = list(Match.objects.filter(
                tournament=tournament,
                is_deleted=False,
                state__in=['completed', 'forfeit']
            ))

            for reg in registrations:
                if reg.team_id:
                    team = teams_map.get(reg.team_id)
                    participant_name = team.name if team else f"Team {reg.team_id}"
                    participant_id = f"team-{reg.team_id}"
                    pid = reg.team_id
                    try:
                        logo_url = team.logo.url if team and team.logo else ''
                    except Exception:
                        logo_url = ''
                elif reg.user:
                    participant_name = reg.user.profile.display_name if hasattr(reg.user, 'profile') and reg.user.profile.display_name else reg.user.username
                    participant_id = f"user-{reg.user.id}"
                    pid = reg.user.id
                    logo_url = ''
                else:
                    continue

                # Filter in Python from pre-loaded matches
                matches = [m for m in all_matches if m.participant1_id == pid or m.participant2_id == pid]
                winner_matches = [m for m in matches if m.winner_id == pid]

                matches_played = len(matches)
                wins = len(winner_matches)
                losses = matches_played - wins
                points = wins * 3

                # Compute map differential from game_scores
                maps_won = 0
                maps_lost = 0
                for m in matches:
                    gs = m.game_scores or {}
                    gs_maps = gs.get('maps', []) if isinstance(gs, dict) else gs if isinstance(gs, list) else []
                    for gm in gs_maps:
                        ws = gm.get('winner_side', gm.get('winner_slot', 0))
                        is_p1 = (m.participant1_id == pid)
                        if (ws == 1 and is_p1) or (ws == 2 and not is_p1):
                            maps_won += 1
                        else:
                            maps_lost += 1
                map_diff = maps_won - maps_lost

                prize_amount = reg_prize_map.get(pid)

                standings_rows.append({
                    'rank': 0,
                    'name': participant_name,
                    'participant_id': participant_id,
                    'logo_url': logo_url,
                    'group_name': None,
                    'matches_played': matches_played,
                    'wins': wins,
                    'draws': 0,
                    'losses': losses,
                    'points': points,
                    'is_advancing': False,
                    'goal_difference': None,
                    'round_difference': None,
                    'kill_difference': None,
                    'map_differential': map_diff,
                    'prize_amount': prize_amount,
                    'game_specific_label': None
                })

            standings_rows.sort(key=lambda x: (-x['points'], -x['wins']))

            for idx, row in enumerate(standings_rows, start=1):
                row['rank'] = idx

            context['standings_primary'] = standings_rows
            context['standings_source'] = 'bracket'
            context['group_standings_summary'] = None

        if tournament.status in ('completed', 'archived'):
            cache.set(f'detail_standings_{tournament.id}', context, 3600)

        return context

    def _get_streams_context(self, tournament: Tournament) -> Dict[str, Any]:
        """Build streams and media context for Streams & Media tab."""
        context = {
            'featured_stream': None,
            'additional_streams': [],
            'vods': [],
            'has_streams': False
        }

        # Pick primary stream URL from actual model fields
        stream_url = tournament.stream_youtube_url or tournament.stream_twitch_url or ''

        if stream_url:
            stream_platform = 'other'
            embed_url = stream_url

            if 'youtube.com' in stream_url or 'youtu.be' in stream_url:
                stream_platform = 'youtube'
                if 'watch?v=' in stream_url:
                    video_id = stream_url.split('watch?v=')[1].split('&')[0]
                    embed_url = f'https://www.youtube.com/embed/{video_id}'
                elif 'youtu.be/' in stream_url:
                    video_id = stream_url.split('youtu.be/')[1].split('?')[0]
                    embed_url = f'https://www.youtube.com/embed/{video_id}'

            elif 'twitch.tv' in stream_url:
                stream_platform = 'twitch'
                if '/videos/' in stream_url:
                    video_id = stream_url.split('/videos/')[1].split('?')[0]
                    embed_url = f'https://player.twitch.tv/?video={video_id}&parent={self.request.get_host()}'
                else:
                    channel = stream_url.split('twitch.tv/')[1].split('?')[0]
                    embed_url = f'https://player.twitch.tv/?channel={channel}&parent={self.request.get_host()}'

            context['featured_stream'] = {
                'url': stream_url,
                'embed_url': embed_url,
                'platform': stream_platform,
                'title': f"{tournament.name} - Live Stream",
                'is_live': tournament.status == 'live'
            }
            context['has_streams'] = True

            # Add secondary stream if both YouTube and Twitch are provided
            secondary_url = ''
            if tournament.stream_youtube_url and tournament.stream_twitch_url:
                secondary_url = tournament.stream_twitch_url if stream_url == tournament.stream_youtube_url else tournament.stream_youtube_url

            if secondary_url:
                sec_platform = 'twitch' if 'twitch.tv' in secondary_url else 'youtube'
                context['additional_streams'].append({
                    'url': secondary_url,
                    'platform': sec_platform,
                    'title': f"{tournament.name} - {sec_platform.title()} Stream",
                })

        return context


_DETAIL_STATUS_LABELS = {
    'draft': 'Upcoming',
    'pending_approval': 'Upcoming',
    'published': 'Upcoming',
    'registration_open': 'Registration Open',
    'registration_closed': 'Registration Closed',
    'live': 'Live',
    'completed': 'Completed',
    'archived': 'Completed',
    'cancelled': 'Cancelled',
}

MATCH_LOBBY_OPEN_LEAD_MINUTES = 30
MATCH_LOBBY_CLOSE_GRACE_MINUTES = 15


def _format_display_datetime(value, time_format='12h'):
    if not value:
        return 'TBD'
    try:
        value = timezone.localtime(value)
    except Exception:
        pass
    if time_format == '24h':
        return value.strftime('%b %d · %H:%M')
    return value.strftime('%b %d · %I:%M %p')


def _relative_match_time(scheduled_time, now, is_completed):
    if not scheduled_time:
        return ''

    delta = scheduled_time - now
    if delta.total_seconds() > 0:
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        if hours > 24:
            return f"Starts in {hours // 24}d"
        if hours > 0:
            return f"Starts in {hours}h {minutes}m"
        return f"Starts in {minutes}m"

    if is_completed:
        hours = int(abs(delta.total_seconds()) // 3600)
        if hours > 24:
            return f"Finished {hours // 24}d ago"
        if hours > 0:
            return f"Finished {hours}h ago"
        return 'Finished recently'

    return ''


def _resolve_match_lobby_window(match, *, now=None):
    """Resolve detail-page lobby access with detail-specific close grace (+15 min)."""
    from apps.tournaments.services.match_lobby_service import (
        FORCED_OPEN_MATCH_STATES,
        TERMINAL_MATCH_STATES,
        resolve_lobby_state,
    )

    now = now or timezone.now()
    lobby = resolve_lobby_state(match, now=now)

    match_state = str(getattr(match, 'state', '') or '').lower()
    scheduled_time = getattr(match, 'scheduled_time', None)

    opens_at = None
    closes_at = None
    if scheduled_time:
        opens_at = scheduled_time - timedelta(minutes=MATCH_LOBBY_OPEN_LEAD_MINUTES)
        closes_at = scheduled_time + timedelta(minutes=MATCH_LOBBY_CLOSE_GRACE_MINUTES)

    if match_state in TERMINAL_MATCH_STATES:
        is_open = False
    elif match_state in FORCED_OPEN_MATCH_STATES:
        is_open = True
    elif not scheduled_time:
        is_open = False
    elif str(lobby.get('state') or '') == 'forfeit_review':
        is_open = False
    else:
        is_open = bool(opens_at and closes_at and opens_at <= now < closes_at)

    if is_open:
        if match_state in FORCED_OPEN_MATCH_STATES:
            lobby_state = str(lobby.get('state') or 'live_grace_or_ready')
        else:
            lobby_state = 'lobby_open'
    else:
        if not scheduled_time or (opens_at and now < opens_at):
            lobby_state = 'upcoming_not_open'
        elif str(lobby.get('state') or '') == 'forfeit_review':
            lobby_state = 'forfeit_review'
        elif match_state in TERMINAL_MATCH_STATES:
            lobby_state = 'completed'
        else:
            lobby_state = 'lobby_closed'

    return {
        'is_open': is_open,
        'opens_at': opens_at,
        'closes_at': closes_at,
        'lobby_state': lobby_state,
        'policy_summary': (
            f'Lobby opens {MATCH_LOBBY_OPEN_LEAD_MINUTES} min before match time '
            f'and closes {MATCH_LOBBY_CLOSE_GRACE_MINUTES} min after.'
        ),
    }


def _viewer_can_manage_tournament(tournament, user):
    """Return True only for organizer/staff/superuser of the current viewer."""
    if not user or not user.is_authenticated:
        return False

    user_id = getattr(user, 'id', None)
    organizer_id = getattr(tournament, 'organizer_id', None)
    if user_id is not None and organizer_id is not None and int(user_id) == int(organizer_id):
        return True

    return bool(getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False))


def _resolve_user_registration_for_detail(tournament, user):
    """Return viewer registration row when one exists for this tournament."""
    if not user or not user.is_authenticated:
        return None

    from apps.tournaments.models import Registration

    return (
        Registration.objects.filter(
            tournament=tournament,
            user=user,
            is_deleted=False,
        )
        .exclude(
            status__in=[Registration.CANCELLED, Registration.REJECTED, Registration.NO_SHOW]
        )
        .first()
    )


def _resolve_viewer_participant_ids_for_detail(tournament, user, *, registration=None):
    """Resolve match participant ids that represent the current viewer."""
    participant_ids = set()
    if not user or not user.is_authenticated:
        return participant_ids

    if tournament.participation_type == Tournament.TEAM:
        if registration is not None and getattr(registration, 'team_id', None):
            participant_ids.add(int(registration.team_id))

        try:
            from apps.organizations.models import TeamMembership

            member_team_ids = set(
                TeamMembership.objects.filter(
                    user=user,
                    status=TeamMembership.Status.ACTIVE,
                ).values_list('team_id', flat=True)
            )
        except Exception:
            member_team_ids = set()

        if member_team_ids:
            from apps.tournaments.models import Registration

            registered_team_ids = set(
                Registration.objects.filter(
                    tournament=tournament,
                    team_id__in=member_team_ids,
                    is_deleted=False,
                )
                .exclude(
                    status__in=[Registration.CANCELLED, Registration.REJECTED, Registration.NO_SHOW]
                )
                .values_list('team_id', flat=True)
            )
            participant_ids.update(int(team_id) for team_id in registered_team_ids if team_id)
    elif registration is not None and getattr(user, 'id', None):
        participant_ids.add(int(user.id))

    return participant_ids


def _resolve_user_next_match_context(tournament, user, *, now=None):
    """Resolve viewer participant identity + next match lobby state for detail CTAs."""
    result = {
        'user_next_match': None,
        'user_next_match_lobby_open': False,
        'user_next_match_lobby_opens_at': None,
        'user_next_match_lobby_closes_at': None,
        'user_next_match_lobby_state': None,
        'viewer_participant_ids': [],
        'viewer_is_registered_participant': False,
    }

    if not user or not user.is_authenticated:
        return result

    from django.db.models import Q
    from apps.tournaments.models import Match

    now = now or timezone.now()
    registration = _resolve_user_registration_for_detail(tournament, user)
    participant_ids = _resolve_viewer_participant_ids_for_detail(
        tournament,
        user,
        registration=registration,
    )

    result['viewer_participant_ids'] = sorted(participant_ids)
    result['viewer_is_registered_participant'] = bool(participant_ids)
    if not participant_ids:
        return result

    user_next_match = (
        Match.objects.filter(
            tournament=tournament,
            is_deleted=False,
            state__in=['scheduled', 'check_in', 'ready', 'live', 'pending_result'],
        )
        .filter(
            Q(participant1_id__in=participant_ids) | Q(participant2_id__in=participant_ids)
        )
        .order_by('scheduled_time', 'round_number', 'match_number')
        .first()
    )
    if user_next_match is None:
        return result

    lobby_window = _resolve_match_lobby_window(user_next_match, now=now)
    result.update({
        'user_next_match': user_next_match,
        'user_next_match_lobby_open': bool(lobby_window['is_open']),
        'user_next_match_lobby_opens_at': lobby_window['opens_at'],
        'user_next_match_lobby_closes_at': lobby_window['closes_at'],
        'user_next_match_lobby_state': lobby_window['lobby_state'],
    })
    return result


def _build_detail_action_input_context(tournament, user, *, base_context=None, now=None):
    """Build canonical viewer-state inputs reused by all detail CTA surfaces."""
    base_context = dict(base_context or {})
    now = now or timezone.now()

    effective_status = str(
        base_context.get('effective_status')
        or getattr(tournament, 'get_effective_status', lambda: tournament.status)()
        or tournament.status
    ).lower()

    viewer_can_manage = _viewer_can_manage_tournament(tournament, user)
    registration = _resolve_user_registration_for_detail(tournament, user)

    from apps.tournaments.services.eligibility_service import RegistrationEligibilityService

    try:
        eligibility = RegistrationEligibilityService.check_eligibility(tournament, user)
    except Exception:
        eligibility = {
            'can_register': False,
            'reason': 'Registration is currently closed.',
            'action_url': '',
            'action_label': '',
        }

    default_label = 'Register Team' if tournament.participation_type == Tournament.TEAM else 'Register Now'
    registration_action_url = eligibility.get('action_url') or f'/tournaments/{tournament.slug}/register/'
    registration_action_label = eligibility.get('action_label') or default_label
    if registration is not None:
        registration_action_url = reverse('tournaments:tournament_hub', kwargs={'slug': tournament.slug})
        registration_action_label = 'Go to HUB'

    action_context = {
        'effective_status': effective_status,
        'viewer_can_manage': viewer_can_manage,
        'is_organizer': viewer_can_manage,
        'is_registered': registration is not None,
        'user_registration': registration,
        'can_register': bool(eligibility.get('can_register')),
        'registration_status_reason': eligibility.get('reason') or 'Registration is currently closed.',
        'registration_action_url': registration_action_url,
        'registration_action_label': registration_action_label,
        'slots_percentage': float(base_context.get('slots_percentage') or 0),
    }
    action_context.update(_resolve_user_next_match_context(tournament, user, now=now))
    return action_context


def _build_detail_action_context(tournament, user, *, context):
    """Build shared CTA payload for both hero and sidebar surfaces."""

    def _action(*, label, url='', icon='arrow-right', tone='muted', disabled=False, kind=''):
        return {
            'label': label,
            'url': url,
            'icon': icon,
            'tone': tone,
            'disabled': bool(disabled),
            'kind': kind,
        }

    status = str(context.get('effective_status') or tournament.status or '').lower()
    is_organizer = bool(
        context.get('viewer_can_manage')
        if 'viewer_can_manage' in context
        else context.get('is_organizer')
    )
    is_registered = bool(context.get('is_registered'))
    viewer_is_participant = bool(context.get('viewer_is_registered_participant')) or is_registered
    can_register = bool(context.get('can_register'))

    user_next_match = context.get('user_next_match')
    lobby_open = bool(context.get('user_next_match_lobby_open'))

    registration_action_url = str(context.get('registration_action_url') or '')
    registration_action_label = str(context.get('registration_action_label') or 'Register Now')
    registration_status_reason = str(
        context.get('registration_status_reason') or 'Registration is currently closed.'
    )

    state = 'closed'
    heading = 'Registration Closed'
    note = registration_status_reason
    primary = _action(
        label='Registration Closed',
        icon='lock',
        tone='closed',
        disabled=True,
        kind='closed',
    )
    secondary = None

    if user_next_match is not None and lobby_open:
        state = 'lobby_open'
        heading = 'Lobby Open'
        note = 'Your match lobby is open now. Enter before the access window closes.'
        primary = _action(
            label='Enter Lobby',
            url=reverse('tournaments:match_room', kwargs={'slug': tournament.slug, 'match_id': user_next_match.id}),
            icon='door-open',
            tone='urgent',
            kind='enter_lobby',
        )
        if is_organizer:
            secondary = _action(
                label='Manage',
                url=f'/toc/{tournament.slug}/',
                icon='settings',
                tone='manage',
                kind='manage',
            )
        elif viewer_is_participant:
            secondary = _action(
                label='Open HUB',
                url=reverse('tournaments:tournament_hub', kwargs={'slug': tournament.slug}),
                icon='layout-dashboard',
                tone='hub',
                kind='hub',
            )
    elif is_organizer:
        state = 'organizer'
        heading = 'Organizer Access'
        note = 'Management controls are available for this tournament.'
        primary = _action(
            label='Manage',
            url=f'/toc/{tournament.slug}/',
            icon='settings',
            tone='manage',
            kind='manage',
        )
        secondary = _action(
            label='Open HUB',
            url=reverse('tournaments:tournament_hub', kwargs={'slug': tournament.slug}),
            icon='layout-dashboard',
            tone='hub',
            kind='hub',
        )
    elif viewer_is_participant:
        state = 'hub'
        heading = 'Participant Access'
        if user_next_match is not None and context.get('user_next_match_lobby_opens_at'):
            note = 'Your next match is scheduled. Lobby access will unlock at the correct runtime window.'
        else:
            note = 'You are registered for this tournament. Open HUB for match and check-in updates.'
        primary = _action(
            label='Open HUB',
            url=reverse('tournaments:tournament_hub', kwargs={'slug': tournament.slug}),
            icon='layout-dashboard',
            tone='hub',
            kind='hub',
        )
    elif can_register:
        state = 'register'
        heading = 'Registration Open'
        slots_percentage = float(context.get('slots_percentage') or 0)
        if slots_percentage >= 85:
            note = 'Slots are nearly full. Register now to secure entry.'
        else:
            note = registration_status_reason or 'Registration is currently open.'
        primary = _action(
            label=registration_action_label,
            url=registration_action_url,
            icon='rocket',
            tone='register',
            kind='register',
        )
    else:
        closed_label = 'Registration Closed'
        if status in ('completed', 'archived'):
            closed_label = 'Tournament Completed'
        elif status == 'cancelled':
            closed_label = 'Tournament Cancelled'
        primary = _action(
            label=closed_label,
            icon='lock',
            tone='closed',
            disabled=True,
            kind='closed',
        )

    return {
        'detail_cta_state': state,
        'detail_cta_heading': heading,
        'detail_cta_note': note,
        'detail_cta_primary': primary,
        'detail_cta_secondary': secondary,
    }


def _detail_status_context(tournament, slots_filled, slots_total, live_match_count, time_format='12h'):
    status = tournament.status
    if status == 'live':
        return f'{live_match_count} matches live now' if live_match_count > 0 else 'Bracket is in progress'

    if status == 'registration_open':
        if slots_total > 0:
            remaining = max(slots_total - slots_filled, 0)
            if remaining == 0:
                return 'Slots are full. Waitlist may open.'
            return f'{remaining} slots remaining'
        return 'Registration is currently open'

    if status == 'registration_closed':
        return 'Registration closed. Seeding and check-in are active.'

    if status in ('completed', 'archived'):
        return 'Final results are now available.'

    if status == 'cancelled':
        return 'Tournament cancelled by organizer.'

    if tournament.tournament_start:
        return f"Starts {_format_display_datetime(tournament.tournament_start, time_format)}"

    return 'Awaiting schedule details.'


def _mobile_cta_payload(tournament, user, *, action_context=None):
    action_context = action_context or _build_detail_action_input_context(
        tournament,
        user,
        now=timezone.now(),
    )
    detail_cta = _build_detail_action_context(tournament, user, context=action_context)
    primary = detail_cta.get('detail_cta_primary') or {
        'label': 'Registration Closed',
        'url': '',
        'disabled': True,
        'kind': 'disabled',
    }
    return {
        'label': primary.get('label') or 'Registration Closed',
        'url': primary.get('url') or '',
        'disabled': bool(primary.get('disabled')),
        'kind': primary.get('kind') or 'disabled',
    }


def tournament_detail_mobile_state(request, slug):
    """Lightweight state payload for mobile detail polling."""
    tournament = get_object_or_404(
        Tournament.objects.select_related('game', 'organizer'),
        slug=slug,
    )

    effective_status = getattr(tournament, 'get_effective_status', lambda: tournament.status)()

    cache_user_key = request.user.id if request.user.is_authenticated else 'anon'
    cache_key = f'detail_mobile_state_v2_{tournament.id}_{cache_user_key}'
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return JsonResponse(cached_payload)

    from apps.tournaments.models import Registration, Match

    slots_filled = Registration.objects.filter(
        tournament=tournament,
        status__in=[Registration.PENDING, Registration.PAYMENT_SUBMITTED, Registration.CONFIRMED],
        is_deleted=False,
    ).count()

    slots_total = tournament.max_participants or 0
    slots_percentage = round((slots_filled / slots_total) * 100) if slots_total > 0 else 0
    slots_filling_fast = slots_total > 0 and slots_percentage >= 85 and tournament.status == 'registration_open'

    live_match_count = Match.objects.filter(
        tournament=tournament,
        state='live',
        is_deleted=False,
    ).count()

    now = timezone.now()
    match_rows = Match.objects.filter(
        tournament=tournament,
        is_deleted=False,
    ).order_by('scheduled_time', 'round_number', 'match_number').values(
        'id',
        'state',
        'participant1_score',
        'participant2_score',
        'scheduled_time',
    )[:30]

    _tf = getattr(request, 'user_platform_prefs', {}).get('time_format', '12h')

    matches_payload = []
    for row in match_rows:
        state = row['state']
        if state == 'live':
            status_key = 'live'
        elif state in ('completed', 'forfeit', 'cancelled', 'disputed'):
            status_key = 'completed'
        else:
            status_key = 'upcoming'

        show_scores = state in ('live', 'completed', 'pending_result', 'disputed', 'forfeit')
        score_text = (
            f"{row['participant1_score'] or 0} - {row['participant2_score'] or 0}"
            if show_scores
            else 'VS'
        )

        scheduled_time = row['scheduled_time']
        matches_payload.append({
            'id': row['id'],
            'status': status_key,
            'status_label': 'Live' if status_key == 'live' else ('Completed' if status_key == 'completed' else 'Upcoming'),
            'score_text': score_text,
            'starts_at_display': _format_display_datetime(scheduled_time, _tf) if scheduled_time else '',
            'starts_at_relative': _relative_match_time(scheduled_time, now, status_key == 'completed'),
        })

    action_input_context = _build_detail_action_input_context(
        tournament,
        request.user,
        base_context={
            'effective_status': effective_status,
            'slots_percentage': slots_percentage,
        },
        now=now,
    )
    detail_cta = _build_detail_action_context(tournament, request.user, context=action_input_context)

    payload = {
        'status_key': effective_status,
        'status_label': _DETAIL_STATUS_LABELS.get(effective_status, 'Upcoming'),
        'status_context': _detail_status_context(tournament, slots_filled, slots_total, live_match_count, _tf),
        'slots_filled': slots_filled,
        'slots_total': slots_total,
        'slots_percentage': slots_percentage,
        'slots_filling_fast': slots_filling_fast,
        'start_display': _format_display_datetime(tournament.tournament_start, _tf),
        'live_match_count': live_match_count,
        'cta': _mobile_cta_payload(tournament, request.user, action_context=action_input_context),
        'detail_cta': detail_cta,
        'matches': matches_payload,
        'updated_at': timezone.now().isoformat(),
    }

    cache.set(cache_key, payload, 15)
    return JsonResponse(payload)


@login_required
@require_POST
def participant_checkin(request, slug):
    """Allow participant to check themselves in during check-in window."""
    tournament = get_object_or_404(Tournament, slug=slug)

    from apps.tournaments.models import Registration
    try:
        registration = Registration.objects.get(
            tournament=tournament,
            user=request.user,
            is_deleted=False
        )
    except Registration.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Registration not found'}, status=404)

    if registration.status != 'confirmed':
        return JsonResponse({'success': False, 'error': 'Registration must be confirmed before check-in'}, status=400)

    if registration.checked_in:
        return JsonResponse({'success': False, 'error': 'Already checked in'}, status=400)

    if tournament.enable_check_in:
        now = timezone.now()
        check_in_opens = tournament.tournament_start - timezone.timedelta(minutes=tournament.check_in_minutes_before or 60)
        check_in_closes = tournament.tournament_start - timezone.timedelta(minutes=tournament.check_in_closes_minutes_before or 0)

        if now < check_in_opens:
            return JsonResponse({
                'success': False,
                'error': f'Check-in opens at {_format_display_datetime(check_in_opens, getattr(request, "user_platform_prefs", {}).get("time_format", "12h"))}'
            }, status=400)

        if now > check_in_closes:
            return JsonResponse({
                'success': False,
                'error': 'Check-in window has closed'
            }, status=400)

    registration.checked_in = True
    registration.checked_in_at = timezone.now()
    registration.checked_in_by = request.user
    registration.save()

    return JsonResponse({
        'success': True,
        'message': 'Successfully checked in!',
        'checked_in_at': registration.checked_in_at.isoformat()
    })
