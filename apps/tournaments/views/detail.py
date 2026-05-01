"""
Tournament Detail View — Public tournament detail page with tabs.

FE-T-002: Tournament Detail Page
FE-T-003: Registration CTA States
Extracted from main.py during Phase 3 restructure.
"""

import json
import re
from collections import defaultdict

from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.cache import cache
from django.db import DatabaseError
from django.db.models import Count
from datetime import timedelta
from typing import Dict, Any, List

from apps.tournaments.models import Tournament, TournamentAnnouncement, TournamentFanPredictionVote
from apps.tournaments.services.registration_service import RegistrationService
from apps.games.services import game_service


@method_decorator(ensure_csrf_cookie, name='dispatch')
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

        user_prefs = getattr(self.request, 'user_platform_prefs', {}) or {}
        detail_time_format = _normalize_time_format_preference(user_prefs.get('time_format', '12h'))
        context.update(_build_detail_time_context(detail_time_format))
        context['detail_time_zone'] = str(
            user_prefs.get('timezone') or timezone.get_current_timezone_name()
        )

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

        # Spectator preview toggle: organizers can view the page as a public user.
        # Activated via ?view_as=spectator; reverted via ?view_as=organizer.
        real_is_organizer = bool(context.get('viewer_can_manage'))
        view_as_spectator = (
            self.request.GET.get('view_as') == 'spectator'
            and real_is_organizer
        )
        context['real_is_organizer'] = real_is_organizer
        context['view_as_spectator'] = view_as_spectator
        if view_as_spectator:
            context['is_organizer'] = False
            context['viewer_can_manage'] = False
            context['can_manage_detail_widgets'] = False
            _sp_input = {**detail_action_input_context, 'viewer_can_manage': False, 'is_organizer': False}
            context.update(_build_detail_action_context(tournament, user, context=_sp_input))

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
        resolved_vanguard_socials = _resolve_default_vanguard_socials(tournament)
        context['has_social_links'] = any([
            resolved_vanguard_socials.get('discord'), tournament.social_twitter,
            resolved_vanguard_socials.get('instagram'), resolved_vanguard_socials.get('youtube'),
            resolved_vanguard_socials.get('facebook'), tournament.social_tiktok,
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

        detail_widgets = _get_tournament_detail_widgets(
            tournament,
            game_spec=game_spec,
        )
        detail_widgets = _with_poll_vote_snapshot(
            detail_widgets,
            tournament=tournament,
            viewer=user,
        )
        context['detail_widgets'] = detail_widgets
        context['can_manage_detail_widgets'] = _viewer_can_manage_tournament(tournament, user)
        context['detail_widgets_save_url'] = reverse(
            'tournaments:detail_widgets_save',
            kwargs={'slug': tournament.slug},
        )
        context['fan_prediction_vote_url'] = reverse(
            'tournaments:fan_prediction_vote',
            kwargs={'slug': tournament.slug},
        )

        return context

    def _get_phase_context(self, tournament, user):
        """Build phase-specific context for the dynamic detail view."""
        effective = getattr(tournament, 'get_effective_status', lambda: tournament.status)()
        # Auto-converge on detail page load — same rule as TOC/HUB. The
        # public detail page is the highest-traffic surface; if a tournament
        # has a winner but status drifted to LIVE, this collapses it to
        # 'completed' so the page renders the post-event experience.
        try:
            from apps.tournaments.services.completion_truth import (
                ensure_post_finalization,
            )
            completion_payload = ensure_post_finalization(tournament)
            if completion_payload.get('completed') and effective not in (
                'completed', 'archived',
            ):
                effective = 'completed'
        except Exception:
            pass
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
        # Format-aware Bracket / Standings visibility on the public detail page.
        # Round Robin and Battle Royale never have a bracket tree — those formats
        # surface their competition data in Standings (League Table / Leaderboard)
        # instead. Hiding the Bracket tab keeps the detail page coherent per format.
        _BRACKET_FORMATS = {'single_elimination', 'double_elimination', 'group_playoff', 'swiss'}
        _STANDINGS_FORMATS = {'group_playoff', 'round_robin', 'swiss', 'battle_royale'}
        _has_data_phase = status in ['live', 'completed', 'archived']
        phase_ctx['show_bracket']   = _has_data_phase and tournament.format in _BRACKET_FORMATS
        phase_ctx['show_matches']   = _has_data_phase
        phase_ctx['show_standings'] = _has_data_phase and tournament.format in _STANDINGS_FORMATS
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
        _tf = _normalize_time_format_preference(
            getattr(getattr(self, 'request', None), 'user_platform_prefs', {}).get('time_format', '12h')
            if hasattr(self, 'request')
            else '12h'
        )

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
            cache_key = f'detail_matches_v3_{tournament.id}'
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
        _tf = _normalize_time_format_preference(
            getattr(getattr(self, 'request', None), 'user_platform_prefs', {}).get('time_format', '12h')
            if hasattr(self, 'request')
            else '12h'
        )

        # Resolve the latest knockout round once so single-elimination labels
        # can be derived correctly (Final/Semi/Quarter) instead of hard-coding.
        knockout_round_numbers = []
        for row in matches_qs:
            if not row.round_number:
                continue
            if tournament.format == tournament.GROUP_PLAYOFF and row.bracket_id is None:
                continue
            knockout_round_numbers.append(row.round_number)
        knockout_round_max = max(knockout_round_numbers) if knockout_round_numbers else None

        def _normalize_round_label(label: str) -> str:
            value = str(label or '').strip()
            if not value:
                return ''

            replacements = {
                'Quarterfinals': 'Quarter Final',
                'Quarter Finals': 'Quarter Final',
                'Quarter-Finals': 'Quarter Final',
                'Quarterfinal': 'Quarter Final',
                'Quarter-Final': 'Quarter Final',
                'Semifinals': 'Semi Final',
                'Semi Finals': 'Semi Final',
                'Semi-Finals': 'Semi Final',
                'Semifinal': 'Semi Final',
                'Semi-Final': 'Semi Final',
                'Finals': 'Final',
            }
            for source, target in replacements.items():
                value = value.replace(source, target)
            return value

        # Canonical read model — bracket-node-aware stage + round label.
        from apps.tournaments.services.match_read_model import MatchReadModel
        from apps.tournaments.services.match_classification import (
            classify_stage as _classify_stage,
            compute_round_label as _compute_round_label,
            tournament_total_rounds as _tournament_total_rounds,
        )
        _canonical_read_model = MatchReadModel.for_tournament(tournament)
        _canonical_view_by_id = {v['match_id']: v for v in _canonical_read_model.list()}
        _canonical_total_rounds = _tournament_total_rounds(tournament)
        for match in matches_qs:
            _canonical_view = _canonical_view_by_id.get(match.id) or {}
            stage_value = _canonical_view.get('stage') or _classify_stage(tournament, match)
            phase = 'knockout_stage' if stage_value == 'knockout' else (
                'swiss' if stage_value == 'swiss' else 'group_stage'
            )
            # Canonical round_number from the read model — when the bracket
            # tree disagrees with Match.round_number, the tree wins.
            canonical_round_number = (
                _canonical_view.get('round_number')
                if _canonical_view.get('round_number') is not None
                else match.round_number
            )

            if match.state == 'live':
                ui_status = 'live'
            elif match.state in ['completed', 'forfeit', 'cancelled', 'disputed']:
                ui_status = 'completed'
            else:
                ui_status = 'upcoming'

            is_live = match.state == 'live'
            is_completed = match.state in ['completed', 'forfeit', 'cancelled']
            show_scores = match.state in ['live', 'completed', 'pending_result', 'disputed']

            # `winner` (1/2) is re-derived below using canonical participant IDs
            # so a match with node-sourced p1/p2 still highlights the right side.
            winner = None

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

            if phase == 'knockout_stage' and canonical_round_number:
                # Prefer the canonical label directly from the read model.
                round_label = (
                    _canonical_view.get('round_label')
                    or _compute_round_label(
                        tournament, match,
                        total_rounds=_canonical_total_rounds,
                    )
                    or f'Round {canonical_round_number}'
                )

            round_label = _normalize_round_label(round_label)

            stage_label = ''
            if phase == 'group_stage' and group_name:
                stage_label = f"Group Stage - {group_name}"
                if match.round_number:
                    stage_label += f" - Round {match.round_number}"
            elif phase == 'group_stage':
                stage_label = 'Group Stage'
            elif phase == 'knockout_stage' and round_label:
                stage_label = round_label
            elif phase == 'knockout_stage':
                stage_label = 'Knockout Stage'
            elif match.round_number:
                stage_label = f"Round {match.round_number}"

            match_label = f"Match #{match.match_number}" if match.match_number else "Match"

            start_time_display = ''
            if match.scheduled_time:
                start_time_display = _format_display_datetime(match.scheduled_time, _tf)

            # Canonical participant slots — node-first. When BracketNode has
            # participant data but the Match row is TBA, the bracket wins.
            _c_p1_id = _canonical_view.get('participant1_id') if _canonical_view else None
            _c_p2_id = _canonical_view.get('participant2_id') if _canonical_view else None
            _c_p1_name = _canonical_view.get('participant1_name') if _canonical_view else ''
            _c_p2_name = _canonical_view.get('participant2_name') if _canonical_view else ''
            canon_p1_id = _c_p1_id or match.participant1_id
            canon_p2_id = _c_p2_id or match.participant2_id
            canon_p1_name_raw = _c_p1_name or match.participant1_name or ''
            canon_p2_name_raw = _c_p2_name or match.participant2_name or ''

            p1_name = 'TBD'
            p2_name = 'TBD'
            p1_logo = None
            p2_logo = None

            if canon_p1_id:
                p1_name = teams_map.get(canon_p1_id) or canon_p1_name_raw or 'TBD'
                p1_logo = teams_logo_map.get(canon_p1_id)
            elif canon_p1_name_raw:
                p1_name = canon_p1_name_raw

            if canon_p2_id:
                p2_name = teams_map.get(canon_p2_id) or canon_p2_name_raw or 'TBD'
                p2_logo = teams_logo_map.get(canon_p2_id)
            elif canon_p2_name_raw:
                p2_name = canon_p2_name_raw

            # Canonical winner side derivation: use node-sourced winner_id if
            # available, else Match.winner_id. Match against canonical IDs.
            canon_winner_id = (
                _canonical_view.get('winner_id') if _canonical_view else None
            ) or match.winner_id
            if canon_winner_id:
                if canon_winner_id == canon_p1_id:
                    winner = 1
                elif canon_winner_id == canon_p2_id:
                    winner = 2

            team1_is_winner = winner == 1
            team2_is_winner = winner == 2
            winner_name = p1_name if team1_is_winner else p2_name if team2_is_winner else ''

            if ui_status == 'live':
                status_label = 'LIVE'
            elif ui_status == 'completed':
                status_label = 'FT'
            else:
                status_label = 'UPCOMING'

            score1_value = match.participant1_score if show_scores else None
            score2_value = match.participant2_score if show_scores else None
            scoreline_display = f"{score1_value if score1_value is not None else '-'}-{score2_value if score2_value is not None else '-'}"

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

            if starts_at:
                local_starts_at = timezone.localtime(starts_at)
                schedule_day_key = local_starts_at.date().isoformat()
                schedule_day_label = local_starts_at.strftime('%a, %b %d')
            else:
                schedule_day_key = 'tba'
                schedule_day_label = 'Date TBA'

            if phase == 'group_stage':
                schedule_phase_label = 'Group Stage'
            elif phase == 'knockout_stage':
                schedule_phase_label = 'Knockout Stage'
            else:
                schedule_phase_label = 'Match Stage'

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
                'round_number_canonical': canonical_round_number,
                'stage_label': stage_label,
                'stage': stage_value,
                'source': _canonical_view.get('source', 'match'),
                'bracket_node_id': _canonical_view.get('bracket_node_id'),
                'match_label': match_label,
                'group_name': group_name,
                'group_id': group_id,
                'schedule_day_key': schedule_day_key,
                'schedule_day_label': schedule_day_label,
                'schedule_phase_label': schedule_phase_label,
                'start_time_display': start_time_display,
                'starts_at': starts_at,
                'starts_at_display': start_time_display,
                'starts_at_relative': starts_at_relative,
                'team1_name': p1_name,
                'team2_name': p2_name,
                'team1_id': canon_p1_id,
                'team2_id': canon_p2_id,
                'raw_team1_id': match.participant1_id,
                'raw_team2_id': match.participant2_id,
                'team1_logo_url': p1_logo,
                'team2_logo_url': p2_logo,
                'team1_is_winner': team1_is_winner,
                'team2_is_winner': team2_is_winner,
                'score1': score1_value,
                'score2': score2_value,
                'scoreline_display': scoreline_display,
                'winner_name': winner_name,
                'status_label': status_label,
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

        bracket_matches = [
            m for m in matches_list
            if not (tournament.format == Tournament.GROUP_PLAYOFF and m.get('phase') != 'knockout_stage')
        ]

        sorted_bracket_matches = sorted(
            bracket_matches,
            key=lambda item: (
                item.get('round_number') is None,
                item.get('round_number') or 9999,
                item.get('match_number') is None,
                item.get('match_number') or 9999,
                item.get('id') or 0,
            )
        )

        bracket_rounds: List[Dict[str, Any]] = []
        round_lookup: Dict[str, Dict[str, Any]] = {}
        for match_row in sorted_bracket_matches:
            round_number = match_row.get('round_number')
            if round_number is None:
                round_key = f"stage:{match_row.get('stage_label') or match_row.get('match_label') or 'round'}"
            else:
                round_key = f"round:{round_number}"

            round_entry = round_lookup.get(round_key)
            if round_entry is None:
                round_label = _normalize_round_label(
                    match_row.get('round_label') or match_row.get('stage_label') or ''
                )
                if not round_label:
                    round_label = f"Round {round_number}" if round_number is not None else 'Bracket Round'

                round_entry = {
                    'round_key': round_key,
                    'round_number': round_number,
                    'round_label': round_label,
                    'matches': [],
                    'match_count': 0,
                    'status': 'upcoming',
                    'lane': 'main',
                    'is_final_round': False,
                }
                round_lookup[round_key] = round_entry
                bracket_rounds.append(round_entry)

            round_entry['matches'].append(match_row)

        for idx, round_entry in enumerate(bracket_rounds):
            round_entry['match_count'] = len(round_entry['matches'])

            live_count = sum(1 for item in round_entry['matches'] if item.get('ui_status') == 'live')
            completed_count = sum(1 for item in round_entry['matches'] if item.get('ui_status') == 'completed')
            if live_count:
                round_entry['status'] = 'live'
            elif round_entry['matches'] and completed_count == len(round_entry['matches']):
                round_entry['status'] = 'completed'
            else:
                round_entry['status'] = 'upcoming'

            round_label_key = str(round_entry.get('round_label') or '').lower().strip()
            is_named_final = (
                round_label_key in {'final', 'grand final', 'grand finals'}
                or 'grand final' in round_label_key
            )
            round_entry['is_final_round'] = idx == len(bracket_rounds) - 1 or is_named_final

            lane = 'main'
            if tournament.format == Tournament.DOUBLE_ELIM:
                lane = 'winners'
                if any(item.get('bracket_type') == 'losers' for item in round_entry['matches']):
                    lane = 'losers'
                if is_named_final:
                    lane = 'grand_final'
            round_entry['lane'] = lane

        has_bracket_rounds = len(bracket_rounds) > 0

        result = {
            'matches': matches_list,
            'matches_reversed': list(reversed(matches_list)),
            'bracket_matches': bracket_matches,
            'bracket_rounds': bracket_rounds,
            'has_bracket_rounds': has_bracket_rounds,
        }

        if tournament.status in ('completed', 'archived'):
            cache.set(f'detail_matches_v3_{tournament.id}', result, 3600)

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
                    'global_rank': None,
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
                row['global_rank'] = idx

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
DETAIL_WIDGETS_CONFIG_KEY = 'detail_widgets'
MAX_FAN_POLL_QUESTIONS = 8
MAX_FAN_POLL_OPTIONS = 6
FAN_POLL_THEME_IDS = {'cyber', 'tactical', 'glass', 'sport', 'native'}
OFFICIAL_VANGUARD_SOCIAL_DEFAULTS = {
    'facebook': 'https://www.facebook.com/DeltaCrownGG',
    'discord': 'https://discord.gg/UaHRC8Cd',
    'youtube': 'https://www.youtube.com/@DeltaCrownGG',
    'instagram': 'https://instagram.com/deltacrowngg',
}


def _slug_token(value, *, fallback='token', max_length=56):
    token = re.sub(r'[^a-z0-9]+', '-', str(value or '').strip().lower()).strip('-')
    if not token:
        token = str(fallback or 'token').strip().lower() or 'token'
    return token[:max_length]


def _normalize_poll_theme(value, *, fallback='cyber'):
    fallback_value = str(fallback or 'cyber').strip().lower() or 'cyber'
    if fallback_value not in FAN_POLL_THEME_IDS:
        fallback_value = 'cyber'

    theme = str(value or '').strip().lower()
    if theme in FAN_POLL_THEME_IDS:
        return theme

    return fallback_value


def _resolve_default_vanguard_socials(tournament):
    resolved = {
        'discord': str(getattr(tournament, 'social_discord', '') or '').strip(),
        'facebook': str(getattr(tournament, 'social_facebook', '') or '').strip(),
        'youtube': str(getattr(tournament, 'social_youtube', '') or '').strip(),
        'instagram': str(getattr(tournament, 'social_instagram', '') or '').strip(),
    }

    if getattr(tournament, 'is_official', False):
        for key, default_value in OFFICIAL_VANGUARD_SOCIAL_DEFAULTS.items():
            if not resolved.get(key):
                resolved[key] = default_value

    return resolved


def _normalize_poll_questions(poll_source, *, fallback_questions):
    normalized_questions = []
    question_ids = set()

    raw_questions = poll_source.get('questions') if isinstance(poll_source.get('questions'), list) else []
    if not raw_questions:
        raw_questions = [{
            'id': poll_source.get('id', 'poll-1'),
            'question': poll_source.get('question'),
            'options': poll_source.get('options'),
        }]

    for index, question_source in enumerate(raw_questions[:MAX_FAN_POLL_QUESTIONS]):
        if not isinstance(question_source, dict):
            continue

        fallback_question = fallback_questions[index] if index < len(fallback_questions) else {
            'id': f'poll-{index + 1}',
            'question': f'Prediction {index + 1}',
            'options': [{'id': 'option-a', 'name': 'Option A'}, {'id': 'option-b', 'name': 'Option B'}],
        }

        question_text = _widget_text(
            question_source.get('question', question_source.get('title')),
            fallback=fallback_question.get('question', f'Prediction {index + 1}'),
            max_length=180,
        )
        question_id = _slug_token(
            question_source.get('id') or question_text or f'poll-{index + 1}',
            fallback=f'poll-{index + 1}',
        )
        if question_id in question_ids:
            suffix = 2
            while f'{question_id}-{suffix}' in question_ids:
                suffix += 1
            question_id = f'{question_id}-{suffix}'
        question_ids.add(question_id)

        raw_options = question_source.get('options') if isinstance(question_source.get('options'), list) else []
        if not raw_options and index == 0 and isinstance(poll_source.get('options'), list):
            raw_options = poll_source.get('options')
        if not raw_options and isinstance(fallback_question.get('options'), list):
            raw_options = fallback_question.get('options')

        normalized_options = []
        option_ids = set()
        for option_index, option_source in enumerate(raw_options[:MAX_FAN_POLL_OPTIONS]):
            source = option_source if isinstance(option_source, dict) else {'name': option_source}
            option_name = _widget_text(
                source.get('name'),
                fallback=f'Option {chr(65 + option_index)}',
                max_length=80,
            )
            option_id = _slug_token(
                source.get('id') or option_name or f'option-{option_index + 1}',
                fallback=f'option-{option_index + 1}',
            )
            if option_id in option_ids:
                suffix = 2
                while f'{option_id}-{suffix}' in option_ids:
                    suffix += 1
                option_id = f'{option_id}-{suffix}'
            option_ids.add(option_id)

            normalized_options.append({
                'id': option_id,
                'name': option_name,
            })

        while len(normalized_options) < 2:
            option_index = len(normalized_options)
            option_name = f'Option {chr(65 + option_index)}'
            option_id = _slug_token(option_name, fallback=f'option-{option_index + 1}')
            if option_id in option_ids:
                option_id = f'{option_id}-{option_index + 1}'
            option_ids.add(option_id)
            normalized_options.append({
                'id': option_id,
                'name': option_name,
            })

        normalized_questions.append({
            'id': question_id,
            'question': question_text,
            'options': normalized_options,
        })

    if not normalized_questions:
        fallback = fallback_questions[0] if fallback_questions else {
            'id': 'poll-1',
            'question': 'Who will win?',
            'options': [{'id': 'option-a', 'name': 'Option A'}, {'id': 'option-b', 'name': 'Option B'}],
        }
        fallback_options = fallback.get('options') if isinstance(fallback.get('options'), list) else []
        first_option = fallback_options[0] if len(fallback_options) > 0 and isinstance(fallback_options[0], dict) else {}
        second_option = fallback_options[1] if len(fallback_options) > 1 and isinstance(fallback_options[1], dict) else {}
        normalized_questions = [{
            'id': _slug_token(fallback.get('id') or 'poll-1', fallback='poll-1'),
            'question': _widget_text(fallback.get('question'), fallback='Who will win?', max_length=180),
            'options': [
                {
                    'id': _slug_token(
                        first_option.get('id', 'option-a'),
                        fallback='option-a',
                    ),
                    'name': _widget_text(
                        first_option.get('name', 'Option A'),
                        fallback='Option A',
                        max_length=80,
                    ),
                },
                {
                    'id': _slug_token(
                        second_option.get('id', 'option-b'),
                        fallback='option-b',
                    ),
                    'name': _widget_text(
                        second_option.get('name', 'Option B'),
                        fallback='Option B',
                        max_length=80,
                    ),
                },
            ],
        }]

    return normalized_questions


def _with_poll_vote_snapshot(detail_widgets, *, tournament, viewer):
    if not isinstance(detail_widgets, dict):
        return detail_widgets

    poll_widget = detail_widgets.get('poll')
    if not isinstance(poll_widget, dict):
        return detail_widgets

    questions = poll_widget.get('questions') if isinstance(poll_widget.get('questions'), list) else []
    poll_ids = [
        str(question.get('id') or '').strip()
        for question in questions
        if isinstance(question, dict) and str(question.get('id') or '').strip()
    ]
    if not poll_ids:
        return detail_widgets

    option_counts = defaultdict(dict)
    viewer_votes = {}
    try:
        aggregate_rows = (
            TournamentFanPredictionVote.objects.filter(
                tournament=tournament,
                poll_id__in=poll_ids,
            )
            .values('poll_id', 'option_id')
            .annotate(total=Count('id'))
        )
        for row in aggregate_rows:
            poll_id = str(row.get('poll_id') or '').strip()
            option_id = str(row.get('option_id') or '').strip()
            if not poll_id or not option_id:
                continue
            option_counts[poll_id][option_id] = int(row.get('total') or 0)

        if viewer and getattr(viewer, 'is_authenticated', False):
            for row in TournamentFanPredictionVote.objects.filter(
                tournament=tournament,
                user=viewer,
                poll_id__in=poll_ids,
            ).values('poll_id', 'option_id'):
                poll_id = str(row.get('poll_id') or '').strip()
                option_id = str(row.get('option_id') or '').strip()
                if poll_id and option_id:
                    viewer_votes[poll_id] = option_id
    except DatabaseError:
        # Keep the page renderable if schema and code are briefly out of sync.
        return detail_widgets

    enriched_questions = []
    for question in questions:
        if not isinstance(question, dict):
            continue

        poll_id = str(question.get('id') or '').strip()
        option_map = option_counts.get(poll_id, {})
        raw_options = question.get('options') if isinstance(question.get('options'), list) else []
        total_votes = sum(int(option_map.get(str(option.get('id') or '').strip(), 0)) for option in raw_options if isinstance(option, dict))

        normalized_options = []
        accumulated_percent = 0
        for option_index, option in enumerate(raw_options):
            if not isinstance(option, dict):
                continue
            option_id = str(option.get('id') or '').strip()
            votes = int(option_map.get(option_id, 0))
            if total_votes > 0:
                if option_index == len(raw_options) - 1:
                    percent = max(0, 100 - accumulated_percent)
                else:
                    percent = int(round((votes / total_votes) * 100))
                    percent = max(0, min(100, percent))
                    accumulated_percent += percent
            else:
                percent = 0

            normalized_options.append({
                'id': option_id,
                'name': _widget_text(option.get('name'), fallback='Option', max_length=80),
                'votes': votes,
                'percent': percent,
            })

        user_choice_id = viewer_votes.get(poll_id, '')
        enriched_questions.append({
            'id': poll_id,
            'question': _widget_text(question.get('question'), fallback='Who will win?', max_length=180),
            'options': normalized_options,
            'total_votes': total_votes,
            'user_choice_id': user_choice_id,
            'has_user_voted': bool(user_choice_id),
        })

    normalized_poll = dict(poll_widget)
    normalized_poll['theme'] = _normalize_poll_theme(
        normalized_poll.get('theme'),
        fallback='cyber',
    )
    normalized_poll['questions'] = enriched_questions
    if enriched_questions:
        primary = enriched_questions[0]
        normalized_poll['question'] = primary.get('question', 'Who will win?')
        preview_options = []
        for option in primary.get('options', [])[:2]:
            preview_options.append({
                'name': option.get('name', 'Option'),
                'percent': int(option.get('percent', 0) or 0),
            })
        while len(preview_options) < 2:
            preview_options.append({
                'name': f'Option {chr(65 + len(preview_options))}',
                'percent': 0,
            })
        normalized_poll['options'] = preview_options

    merged = dict(detail_widgets)
    merged['poll'] = normalized_poll
    return merged


def _find_poll_question(poll_widget, poll_id):
    questions = poll_widget.get('questions') if isinstance(poll_widget.get('questions'), list) else []
    target_id = str(poll_id or '').strip()
    if not target_id:
        return None

    for question in questions:
        if not isinstance(question, dict):
            continue
        if str(question.get('id') or '').strip() == target_id:
            return question

    return None


def _normalize_time_format_preference(value):
    normalized = str(value or '').strip().lower()
    if normalized in {'24', '24h', '24hr', '24-hour', '24hours'}:
        return '24h'
    if normalized in {'12', '12h', '12hr', '12-hour', '12hours'}:
        return '12h'
    return '12h'


def _build_detail_time_context(time_format='12h'):
    normalized = _normalize_time_format_preference(time_format)
    is_24h = normalized == '24h'
    return {
        'detail_time_format': normalized,
        'detail_time_only_format': 'H:i' if is_24h else 'g:i A',
        'detail_datetime_format': 'M d, Y • H:i' if is_24h else 'M d, Y • g:i A',
        'detail_short_datetime_format': 'M d, H:i' if is_24h else 'M d, g:i A',
        'detail_ticker_datetime_format': 'M d • H:i' if is_24h else 'M d • g:i A',
    }


def _widget_text(value, *, fallback='', max_length=240):
    text_value = str(value or '').strip()
    if not text_value:
        return str(fallback or '')[:max_length]
    return text_value[:max_length]


def _widget_url(value, *, fallback='', max_length=500):
    url_value = str(value or '').strip()
    if not url_value:
        return str(fallback or '')[:max_length]
    return url_value[:max_length]


def _widget_bool(value, *, fallback=False):
    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'1', 'true', 'yes', 'on'}:
            return True
        if normalized in {'0', 'false', 'no', 'off'}:
            return False

    return bool(fallback)


def _widget_int(value, *, fallback=0, minimum=None, maximum=None):
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        parsed = int(fallback)

    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _build_default_detail_widgets(tournament, *, game_spec=None):
    resolved_socials = _resolve_default_vanguard_socials(tournament)
    has_social_links = any(
        str(value or '').strip() for value in resolved_socials.values()
    )
    fan_voting_enabled = bool(getattr(tournament, 'enable_fan_voting', False))

    default_poll_questions = [{
        'id': 'poll-1',
        'question': 'Who will win?',
        'options': [
            {'id': 'option-a', 'name': 'Option A'},
            {'id': 'option-b', 'name': 'Option B'},
        ],
    }]

    return {
        'sponsor': {
            'enabled': False,
            'title': '',
            'subtitle': '',
            'badge': 'SP',
            'logo_url': '',
        },
        'talent': {
            'enabled': False,
            'items': [],
        },
        'bounty': {
            'enabled': False,
            'title': '',
            'task': '',
            'reward': 0,
        },
        'poll': {
            'enabled': fan_voting_enabled,
            'active': fan_voting_enabled,
            'theme': 'cyber',
            'question': default_poll_questions[0]['question'],
            'options': [
                {'name': 'Option A', 'percent': 50},
                {'name': 'Option B', 'percent': 50},
            ],
            'questions': default_poll_questions,
        },
        'socials': {
            'enabled': has_social_links,
            'discord': resolved_socials['discord'],
            'facebook': resolved_socials['facebook'],
            'youtube': resolved_socials['youtube'],
            'instagram': resolved_socials['instagram'],
        },
        'bottom_board': {
            'enabled': False,
            'title': '',
            'banner_url': '',
            'logos': [],
        },
    }


def _normalize_detail_widgets_config(raw_widgets, *, tournament, game_spec=None):
    defaults = _build_default_detail_widgets(tournament, game_spec=game_spec)
    payload = raw_widgets if isinstance(raw_widgets, dict) else {}

    sponsor_source = payload.get('sponsor') if isinstance(payload.get('sponsor'), dict) else {}
    sponsor = {
        'enabled': _widget_bool(
            sponsor_source.get('enabled', sponsor_source.get('show')),
            fallback=defaults['sponsor']['enabled'],
        ),
        'title': _widget_text(
            sponsor_source.get('title'),
            fallback=defaults['sponsor']['title'],
            max_length=120,
        ),
        'subtitle': _widget_text(
            sponsor_source.get('subtitle'),
            fallback=defaults['sponsor']['subtitle'],
            max_length=180,
        ),
        'badge': _widget_text(
            sponsor_source.get('badge'),
            fallback=defaults['sponsor']['badge'],
            max_length=4,
        ).upper(),
        'logo_url': _widget_url(
            sponsor_source.get('logo_url', sponsor_source.get('logoUrl')),
            fallback=defaults['sponsor']['logo_url'],
            max_length=500,
        ),
    }

    if not sponsor['badge']:
        sponsor['badge'] = 'SP'

    talent_source = payload.get('talent') if isinstance(payload.get('talent'), dict) else {}
    raw_talent_items = talent_source.get('items') if isinstance(talent_source.get('items'), list) else []
    talent_items = []
    for item in raw_talent_items[:12]:
        if not isinstance(item, dict):
            continue
        name = _widget_text(item.get('name'), max_length=80)
        if not name:
            continue
        talent_items.append({
            'name': name,
            'role': _widget_text(item.get('role'), fallback='CAST', max_length=20).upper(),
            'avatar_url': _widget_url(
                item.get('avatar_url', item.get('avatar')),
                max_length=500,
            ),
        })

    talent = {
        'enabled': _widget_bool(
            talent_source.get('enabled', talent_source.get('show')),
            fallback=defaults['talent']['enabled'],
        ),
        'items': talent_items,
    }

    bounty_source = payload.get('bounty') if isinstance(payload.get('bounty'), dict) else {}
    bounty = {
        'enabled': _widget_bool(
            bounty_source.get('enabled', bounty_source.get('show')),
            fallback=defaults['bounty']['enabled'],
        ),
        'title': _widget_text(
            bounty_source.get('title'),
            fallback=defaults['bounty']['title'],
            max_length=120,
        ),
        'task': _widget_text(
            bounty_source.get('task', bounty_source.get('description')),
            fallback=defaults['bounty']['task'],
            max_length=420,
        ),
        'reward': _widget_int(
            bounty_source.get('reward'),
            fallback=defaults['bounty']['reward'],
            minimum=0,
            maximum=999999999,
        ),
    }

    poll_source = payload.get('poll') if isinstance(payload.get('poll'), dict) else {}
    poll_questions = _normalize_poll_questions(
        poll_source,
        fallback_questions=defaults['poll']['questions'],
    )

    raw_poll_options = poll_source.get('options') if isinstance(poll_source.get('options'), list) else []
    poll_preview_options = []
    if raw_poll_options:
        for idx in range(2):
            source_option = raw_poll_options[idx] if idx < len(raw_poll_options) and isinstance(raw_poll_options[idx], dict) else {}
            default_option = defaults['poll']['options'][idx]
            poll_preview_options.append({
                'name': _widget_text(
                    source_option.get('name'),
                    fallback=default_option['name'],
                    max_length=80,
                ),
                'percent': _widget_int(
                    source_option.get('percent'),
                    fallback=default_option['percent'],
                    minimum=0,
                    maximum=100,
                ),
            })

        poll_total = poll_preview_options[0]['percent'] + poll_preview_options[1]['percent']
        if poll_total <= 0:
            poll_preview_options[0]['percent'] = 50
            poll_preview_options[1]['percent'] = 50
        elif poll_total != 100:
            option_a = int(round((poll_preview_options[0]['percent'] / poll_total) * 100))
            poll_preview_options[0]['percent'] = option_a
            poll_preview_options[1]['percent'] = 100 - option_a
    else:
        primary_options = poll_questions[0]['options'] if poll_questions else defaults['poll']['questions'][0]['options']
        poll_preview_options = [
            {
                'name': _widget_text(
                    (primary_options[0] if len(primary_options) > 0 else {}).get('name'),
                    fallback='Option A',
                    max_length=80,
                ),
                'percent': 50,
            },
            {
                'name': _widget_text(
                    (primary_options[1] if len(primary_options) > 1 else {}).get('name'),
                    fallback='Option B',
                    max_length=80,
                ),
                'percent': 50,
            },
        ]

    poll = {
        'enabled': _widget_bool(
            poll_source.get('enabled', poll_source.get('show')),
            fallback=defaults['poll']['enabled'],
        ),
        'active': _widget_bool(
            poll_source.get('active', poll_source.get('poll_enabled')),
            fallback=defaults['poll']['active'],
        ),
        'theme': _normalize_poll_theme(
            poll_source.get('theme'),
            fallback=defaults['poll'].get('theme', 'cyber'),
        ),
        'question': _widget_text(
            poll_source.get('question', (poll_questions[0] if poll_questions else {}).get('question')),
            fallback=defaults['poll']['question'],
            max_length=180,
        ),
        'options': poll_preview_options,
        'questions': poll_questions,
    }

    socials_source = payload.get('socials') if isinstance(payload.get('socials'), dict) else {}
    socials = {
        'enabled': _widget_bool(
            socials_source.get('enabled', socials_source.get('show')),
            fallback=defaults['socials']['enabled'],
        ),
        'discord': _widget_url(
            socials_source.get('discord'),
            fallback=defaults['socials']['discord'],
            max_length=500,
        ),
        'facebook': _widget_url(
            socials_source.get('facebook'),
            fallback=defaults['socials']['facebook'],
            max_length=500,
        ),
        'youtube': _widget_url(
            socials_source.get('youtube'),
            fallback=defaults['socials']['youtube'],
            max_length=500,
        ),
        'instagram': _widget_url(
            socials_source.get('instagram'),
            fallback=defaults['socials']['instagram'],
            max_length=500,
        ),
    }

    bottom_board_source = payload.get('bottom_board') if isinstance(payload.get('bottom_board'), dict) else {}
    raw_bottom_logos = bottom_board_source.get('logos') if isinstance(bottom_board_source.get('logos'), list) else []
    bottom_logos = []
    for logo in raw_bottom_logos[:16]:
        cleaned_logo = _widget_text(logo, max_length=40)
        if cleaned_logo:
            bottom_logos.append(cleaned_logo)

    bottom_board = {
        'enabled': _widget_bool(
            bottom_board_source.get('enabled', bottom_board_source.get('show')),
            fallback=defaults['bottom_board']['enabled'],
        ),
        'title': _widget_text(
            bottom_board_source.get('title'),
            fallback=defaults['bottom_board']['title'],
            max_length=120,
        ),
        'banner_url': _widget_url(
            bottom_board_source.get('banner_url', bottom_board_source.get('bannerUrl')),
            fallback=defaults['bottom_board']['banner_url'],
            max_length=500,
        ),
        'logos': bottom_logos,
    }

    return {
        'sponsor': sponsor,
        'talent': talent,
        'bounty': bounty,
        'poll': poll,
        'socials': socials,
        'bottom_board': bottom_board,
    }


def _get_tournament_detail_widgets(tournament, *, game_spec=None):
    config = tournament.config if isinstance(tournament.config, dict) else {}
    raw_widgets = config.get(DETAIL_WIDGETS_CONFIG_KEY, {}) if isinstance(config, dict) else {}
    return _normalize_detail_widgets_config(
        raw_widgets,
        tournament=tournament,
        game_spec=game_spec,
    )


def _format_display_datetime(value, time_format='12h'):
    if not value:
        return 'TBD'
    try:
        value = timezone.localtime(value)
    except Exception:
        pass
    time_format = _normalize_time_format_preference(time_format)
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

    _tf = _normalize_time_format_preference(
        getattr(request, 'user_platform_prefs', {}).get('time_format', '12h')
    )

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
        _tf = _normalize_time_format_preference(
            getattr(request, 'user_platform_prefs', {}).get('time_format', '12h')
        )
        check_in_opens = tournament.tournament_start - timezone.timedelta(minutes=tournament.check_in_minutes_before or 60)
        check_in_closes = tournament.tournament_start - timezone.timedelta(minutes=tournament.check_in_closes_minutes_before or 0)

        if now < check_in_opens:
            return JsonResponse({
                'success': False,
                'error': f'Check-in opens at {_format_display_datetime(check_in_opens, _tf)}'
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


@login_required
@require_POST
def tournament_fan_prediction_vote(request, slug):
    """Persist a viewer fan prediction for a poll question."""
    tournament = get_object_or_404(Tournament.objects.only('id', 'slug', 'config'), slug=slug)

    try:
        body = request.body.decode('utf-8') if request.body else '{}'
        payload = json.loads(body or '{}')
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload.'}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({'success': False, 'error': 'Request body must be a JSON object.'}, status=400)

    poll_id = _widget_text(payload.get('poll_id'), max_length=64)
    option_id = _widget_text(payload.get('option_id'), max_length=64)
    if not poll_id or not option_id:
        return JsonResponse({'success': False, 'error': 'poll_id and option_id are required.'}, status=400)

    detail_widgets = _get_tournament_detail_widgets(tournament)
    poll_widget = detail_widgets.get('poll') if isinstance(detail_widgets.get('poll'), dict) else {}

    if not _widget_bool(poll_widget.get('enabled'), fallback=False) or not _widget_bool(poll_widget.get('active'), fallback=False):
        return JsonResponse({'success': False, 'error': 'Fan predictions are currently disabled.'}, status=400)

    question = _find_poll_question(poll_widget, poll_id)
    if not question:
        return JsonResponse({'success': False, 'error': 'Poll question not found.'}, status=404)

    option_ids = {
        str(option.get('id') or '').strip()
        for option in (question.get('options') if isinstance(question.get('options'), list) else [])
        if isinstance(option, dict)
    }
    if option_id not in option_ids:
        return JsonResponse({'success': False, 'error': 'Poll option is invalid.'}, status=400)

    try:
        TournamentFanPredictionVote.objects.update_or_create(
            tournament=tournament,
            user=request.user,
            poll_id=poll_id,
            defaults={'option_id': option_id},
        )

        enriched_widgets = _with_poll_vote_snapshot(
            detail_widgets,
            tournament=tournament,
            viewer=request.user,
        )
    except DatabaseError:
        return JsonResponse(
            {
                'success': False,
                'error': 'Fan predictions are temporarily unavailable. Please try again shortly.',
            },
            status=503,
        )
    enriched_poll = enriched_widgets.get('poll', {})
    enriched_question = _find_poll_question(enriched_poll, poll_id)

    return JsonResponse({
        'success': True,
        'message': 'Prediction saved.',
        'poll': enriched_question,
        'poll_widget': enriched_poll,
    })


@login_required
@require_POST
def tournament_detail_widgets_save(request, slug):
    """Persist organizer-managed detail-page widget configuration."""
    tournament = get_object_or_404(Tournament.objects.select_related('game', 'organizer'), slug=slug)

    if not _viewer_can_manage_tournament(tournament, request.user):
        return JsonResponse({'success': False, 'error': 'You are not allowed to edit widgets for this tournament.'}, status=403)

    try:
        body = request.body.decode('utf-8') if request.body else '{}'
        payload = json.loads(body or '{}')
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload.'}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({'success': False, 'error': 'Request body must be a JSON object.'}, status=400)

    canonical_slug = game_service.normalize_slug(tournament.game.slug)
    game_spec = game_service.get_game(canonical_slug)

    raw_widgets = payload.get('detail_widgets', payload)
    if not isinstance(raw_widgets, dict):
        return JsonResponse({'success': False, 'error': 'Widget payload is missing or invalid.'}, status=400)

    normalized_widgets = _normalize_detail_widgets_config(
        raw_widgets,
        tournament=tournament,
        game_spec=game_spec,
    )

    config = dict(tournament.config or {})
    config[DETAIL_WIDGETS_CONFIG_KEY] = normalized_widgets
    tournament.config = config
    tournament.save(update_fields=['config'])

    response_widgets = _with_poll_vote_snapshot(
        normalized_widgets,
        tournament=tournament,
        viewer=request.user,
    )

    # Keep detail polling cache fresh for organizer/public viewers.
    cache.delete(f'detail_mobile_state_v2_{tournament.id}_anon')
    cache.delete(f'detail_mobile_state_v2_{tournament.id}_{request.user.id}')

    return JsonResponse({
        'success': True,
        'message': 'Detail widgets saved.',
        'detail_widgets': response_widgets,
    })


def tournament_prize_overview(request, slug):
    """
    Public read-only prize overview for the tournament detail page.

    Returns the spectator-safe rewards read model. No auth required — this is
    the same data shown to public viewers on the detail page.
    """
    tournament = get_object_or_404(
        Tournament.objects.select_related('game', 'organizer'),
        slug=slug,
    )

    from apps.tournaments.services.completion_truth import (
        is_tournament_effectively_completed,
    )
    from apps.tournaments.services.rewards_read_model import (
        TournamentRewardsReadModel,
    )

    completed = is_tournament_effectively_completed(tournament)
    cache_key = f'public_prize_overview_v2_{tournament.id}'
    if completed:
        cache.delete(f'public_prize_overview_v1_{tournament.id}')
        cache.delete(cache_key)
        payload = TournamentRewardsReadModel.public_payload(tournament)
        response = JsonResponse(payload)
        response['Cache-Control'] = 'no-store, max-age=0'
        return response

    payload = cache.get(cache_key)
    if payload is None:
        payload = TournamentRewardsReadModel.public_payload(tournament)
        cache.set(cache_key, payload, timeout=30)

    return JsonResponse(payload)
