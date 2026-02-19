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
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from typing import Dict, Any

from apps.tournaments.models import Tournament, TournamentAnnouncement
from apps.tournaments.services.registration_service import RegistrationService
from apps.games.services import game_service


class TournamentDetailView(DetailView):
    """
    FE-T-002: Tournament Detail Page — Dynamic Status-Aware Routing

    URL: /tournaments/<slug>/
    Template: Routes to phase-specific templates based on tournament.status:
        - draft/pending_approval/published → detail_registration.html
        - registration_open              → detail_registration.html (CTA active)
        - registration_closed            → detail_registration.html (check-in mode)
        - live                           → detail_live.html
        - completed/archived             → detail_completed.html
        - cancelled                      → detail_cancelled.html

    Fallback: tournaments/detailPages/detail.html (original monolith)
    """
    model = Tournament
    template_name = 'tournaments/detailPages/detail.html'  # fallback
    context_object_name = 'tournament'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    # Status → template mapping
    PHASE_TEMPLATES = {
        'draft':               'tournaments/detailPages/detail_registration.html',
        'pending_approval':    'tournaments/detailPages/detail_registration.html',
        'published':           'tournaments/detailPages/detail_registration.html',
        'registration_open':   'tournaments/detailPages/detail_registration.html',
        'registration_closed': 'tournaments/detailPages/detail_registration.html',
        'live':                'tournaments/detailPages/detail_live.html',
        'completed':           'tournaments/detailPages/detail_completed.html',
        'archived':            'tournaments/detailPages/detail_completed.html',
        'cancelled':           'tournaments/detailPages/detail_cancelled.html',
    }

    def get_template_names(self):
        """Route to phase-specific template based on tournament status."""
        tournament = self.object
        if tournament and tournament.status in self.PHASE_TEMPLATES:
            phase_template = self.PHASE_TEMPLATES[tournament.status]
            # Try phase template first, fall back to monolith
            from django.template.loader import get_template
            from django.template import TemplateDoesNotExist
            try:
                get_template(phase_template)
                return [phase_template]
            except TemplateDoesNotExist:
                pass
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        user = self.request.user

        # GameService integration
        canonical_slug = game_service.normalize_slug(tournament.game.slug)
        game_spec = game_service.get_game(canonical_slug)
        context['game_spec'] = game_spec

        # Eligibility check
        from apps.tournaments.services.eligibility_service import RegistrationEligibilityService
        eligibility = RegistrationEligibilityService.check_eligibility(tournament, user)

        context['can_register'] = eligibility['can_register']
        context['registration_status_reason'] = eligibility['reason']
        context['is_registered'] = eligibility['registration'] is not None
        context['user_registration'] = eligibility['registration']
        context['eligibility_status'] = eligibility['status']

        # Registration action URL
        if tournament.participation_type == Tournament.TEAM:
            context['registration_action_url'] = f'/tournaments/{tournament.slug}/register/team/'
            context['registration_action_label'] = 'Register Team'
        else:
            context['registration_action_url'] = f'/tournaments/{tournament.slug}/register/'
            context['registration_action_label'] = 'Register Now'

        if eligibility['registration'] is not None:
            context['registration_action_url'] = f'/tournaments/{tournament.slug}/lobby/'
            context['registration_action_label'] = 'Enter Lobby'

        # Slots info
        from apps.tournaments.models import Registration
        slots_filled = Registration.objects.filter(
            tournament=tournament,
            status__in=[Registration.PENDING, Registration.PAYMENT_SUBMITTED, Registration.CONFIRMED],
            is_deleted=False
        ).count()
        context['slots_filled'] = slots_filled
        context['slots_total'] = tournament.max_participants
        context['slots_percentage'] = (slots_filled / tournament.max_participants * 100) if tournament.max_participants > 0 else 0

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
            config = tournament.config or {}
            context['stages'] = config.get('stages', [])

            from apps.tournaments.models import Group, GroupStanding
            groups = Group.objects.filter(
                tournament=tournament,
                is_deleted=False
            ).order_by('display_order')
            context['groups'] = groups

            group_standings = {}
            for g in groups:
                group_standings[g.id] = GroupStanding.objects.filter(
                    group=g,
                    is_deleted=False
                ).order_by('rank').select_related('team', 'user')
            context['group_standings'] = group_standings
        else:
            context['is_multi_stage'] = False
            context['current_stage'] = None

        # Matches tab
        context.update(self._get_matches_context(tournament))

        # Standings tab
        context.update(self._get_standings_context(tournament))

        # Streams tab
        context.update(self._get_streams_context(tournament))

        # Phase-specific context
        context.update(self._get_phase_context(tournament, user))

        return context

    def _get_phase_context(self, tournament, user):
        """Build phase-specific context for the dynamic detail view."""
        now = timezone.now()
        status = tournament.status

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
            phase_ctx['total_match_count'] = total_matches
            phase_ctx['completed_match_count'] = completed_matches
            phase_ctx['match_progress_pct'] = (
                round(completed_matches / total_matches * 100) if total_matches > 0 else 0
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

            # User's next match (if participant)
            if user.is_authenticated:
                from apps.tournaments.models import Registration
                user_reg = Registration.objects.filter(
                    tournament=tournament, user=user, is_deleted=False,
                    status__in=['confirmed', 'pending', 'payment_submitted']
                ).first()
                if user_reg:
                    from django.db.models import Q
                    pid = user_reg.team_id or user.id
                    user_next = Match.objects.filter(
                        tournament=tournament, is_deleted=False,
                        state__in=['scheduled', 'check_in', 'ready', 'live']
                    ).filter(
                        Q(participant1_id=pid) | Q(participant2_id=pid)
                    ).order_by('round_number', 'match_number').first()
                    phase_ctx['user_next_match'] = user_next
                else:
                    phase_ctx['user_next_match'] = None
            else:
                phase_ctx['user_next_match'] = None

        # Completed phase extras
        if phase_ctx['is_completed_phase']:
            from apps.tournaments.models.result import TournamentResult
            try:
                results = TournamentResult.objects.filter(
                    tournament=tournament, is_deleted=False
                ).order_by('placement')[:3]
                phase_ctx['podium'] = list(results)
            except Exception:
                phase_ctx['podium'] = []

            from apps.tournaments.models import Match
            total = Match.objects.filter(
                tournament=tournament, is_deleted=False
            ).exclude(state='cancelled').count()
            phase_ctx['total_matches_played'] = total

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

        if registration.checked_in:
            return {
                'state': 'checked_in',
                'reason': f'Checked in at {registration.checked_in_at.strftime("%b %d, %H:%M")}',
                'check_in_window': check_in_window,
            }

        if check_in_window['is_open']:
            return {
                'state': 'check_in_required',
                'reason': f'Check-in required before {check_in_window["closes_at"].strftime("%b %d, %H:%M")}',
                'check_in_window': check_in_window,
            }

        if check_in_window['opens_at'] and now < check_in_window['opens_at']:
            return {
                'state': 'confirmed',
                'reason': f'Registration confirmed. Check-in opens {check_in_window["opens_at"].strftime("%b %d, %H:%M")}',
                'check_in_window': check_in_window,
            }

        return {
            'state': 'confirmed',
            'reason': 'Registration confirmed',
        }

    def _get_participants_context(self, tournament, user):
        """Get context data for Participants tab."""
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
            for reg in registrations_qs:
                if not reg.team_id:
                    continue

                try:
                    team = Team.objects.prefetch_related(
                        'vnext_memberships__user__profile'
                    ).get(id=reg.team_id)
                except Team.DoesNotExist:
                    continue

                active_members = team.vnext_memberships.filter(
                    status='ACTIVE'
                ).select_related('user', 'user__profile')

                roster_summary = []
                for membership in active_members[:3]:
                    roster_summary.append({
                        'name': membership.user.profile.display_name if hasattr(membership.user, 'profile') else membership.user.username,
                        'role': membership.get_role_display(),
                    })

                is_current_user_team = False
                if user.is_authenticated:
                    is_current_user_team = active_members.filter(user=user).exists()
                    if is_current_user_team:
                        current_user_registration = reg

                team_rank = None
                try:
                    from apps.teams.models import TeamRankingBreakdown
                    ranking = TeamRankingBreakdown.objects.filter(team=team).first()
                    if ranking and ranking.final_total > 0:
                        teams_above = TeamRankingBreakdown.objects.filter(
                            team__game_id=team.game_id,
                            final_total__gt=ranking.final_total
                        ).count()
                        team_rank = teams_above + 1
                except Exception:
                    pass

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
                    'roster_count': active_members.count(),
                    'roster_summary': roster_summary,
                    'sub_label': f"{active_members.count()} players" + (f" · {team.region}" if team.region else ""),
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
                    'sub_label': "Solo player" + (f" · {region}" if region else ""),
                    'status': reg.status,
                    'checked_in': reg.checked_in,
                    'registered_at': reg.registered_at,
                    'is_current_user': is_current_user,
                    'registration_id': reg.id,
                })

        confirmed_count = registrations_qs.filter(status=Registration.CONFIRMED).count()
        waitlist_count = 0

        is_organizer = user.is_authenticated and (
            user == tournament.organizer or
            user.is_staff or
            user.is_superuser
        )

        return {
            'participants': participants_list,
            'participants_total': len(participants_list),
            'participants_confirmed': confirmed_count,
            'participants_waitlist': waitlist_count,
            'current_user_registration': current_user_registration,
            'is_organizer': is_organizer,
        }

    def _get_matches_context(self, tournament):
        """Build matches context for Matches tab."""
        from apps.tournaments.models import Match, Group
        from apps.organizations.models import Team

        matches_qs = Match.objects.filter(
            tournament=tournament,
            is_deleted=False
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

        matches_list = []
        now = timezone.now()

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
            round_label = ''
            if phase == 'knockout_stage' and match.round_number:
                if match.round_number == 1:
                    round_label = 'Final'
                elif match.round_number == 2:
                    round_label = 'Semi-Finals'
                elif match.round_number == 3:
                    round_label = 'Quarter-Finals'
                else:
                    round_label = f'Round {match.round_number}'

            stage_label = ''
            if phase == 'group_stage' and group_name:
                stage_label = f"Group {group_name}"
                if match.round_number:
                    stage_label += f" — Round {match.round_number}"
            elif phase == 'knockout_stage' and round_label:
                stage_label = round_label
            elif match.round_number:
                stage_label = f"Round {match.round_number}"

            match_label = f"Match #{match.match_number}" if match.match_number else "Match"

            start_time_display = ''
            if match.scheduled_time:
                start_time_display = match.scheduled_time.strftime('%b %d · %H:%M')

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
            if lobby_info.get('best_of'):
                best_of_label = f"BO{lobby_info['best_of']}"

            matches_list.append({
                'id': match.id,
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
                'start_time_display': start_time_display,
                'starts_at': starts_at,
                'starts_at_display': start_time_display,
                'starts_at_relative': starts_at_relative,
                'team1_name': p1_name,
                'team2_name': p2_name,
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
            })

        return {
            'matches': matches_list,
        }

    def _get_standings_context(self, tournament: Tournament) -> Dict[str, Any]:
        """Build standings context for Standings tab."""
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

            all_standings = []
            group_summaries = []

            for group in groups:
                group_standings = GroupStanding.objects.filter(
                    group=group,
                    is_deleted=False
                ).select_related('team', 'user').order_by('rank')

                advancers = []
                others = []

                for idx, standing in enumerate(group_standings, start=1):
                    if standing.team:
                        participant_name = standing.team.name
                        participant_id = f"team-{standing.team.id}"
                    elif standing.user:
                        participant_name = standing.user.profile.display_name if hasattr(standing.user, 'profile') and standing.user.profile.display_name else standing.user.username
                        participant_id = f"user-{standing.user.id}"
                    else:
                        participant_name = "Unknown"
                        participant_id = "unknown"

                    is_advancing = idx <= group.advancement_count

                    row = {
                        'rank': standing.rank or idx,
                        'name': participant_name,
                        'participant_id': participant_id,
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

                    summary_entry = {
                        'rank': idx,
                        'name': participant_name
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

            all_standings.sort(key=lambda x: (
                not x['is_advancing'],
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

            registrations = Registration.objects.filter(
                tournament=tournament,
                is_deleted=False,
                status__in=['confirmed', 'checked_in']
            ).select_related('user')

            if not registrations.exists():
                return context

            team_ids = [reg.team_id for reg in registrations if reg.team_id]
            teams_map = {team.id: team for team in Team.objects.filter(id__in=team_ids)} if team_ids else {}

            standings_rows = []

            for reg in registrations:
                if reg.team_id:
                    team = teams_map.get(reg.team_id)
                    participant_name = team.name if team else f"Team #{reg.team_id}"
                    participant_id = f"team-{reg.team_id}"
                    pid = reg.team_id
                elif reg.user:
                    participant_name = reg.user.profile.display_name if hasattr(reg.user, 'profile') and reg.user.profile.display_name else reg.user.username
                    participant_id = f"user-{reg.user.id}"
                    pid = reg.user.id
                else:
                    continue

                matches = Match.objects.filter(
                    tournament=tournament,
                    is_deleted=False,
                    state__in=['completed', 'forfeit']
                ).filter(
                    Q(participant1_id=pid) | Q(participant2_id=pid)
                )
                winner_matches = matches.filter(winner_id=pid)

                matches_played = matches.count()
                wins = winner_matches.count()
                losses = matches_played - wins
                points = wins * 3

                standings_rows.append({
                    'rank': 0,
                    'name': participant_name,
                    'participant_id': participant_id,
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
                    'game_specific_label': None
                })

            standings_rows.sort(key=lambda x: (-x['points'], -x['wins']))

            for idx, row in enumerate(standings_rows, start=1):
                row['rank'] = idx

            context['standings_primary'] = standings_rows
            context['standings_source'] = 'bracket'
            context['group_standings_summary'] = None

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
                'error': f'Check-in opens at {check_in_opens.strftime("%b %d, %H:%M")}'
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
