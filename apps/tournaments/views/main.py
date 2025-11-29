# FE-T-001: Tournament List Page
# Purpose: Public-facing tournament discovery and listing page with filters
# Source: Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md (Section 1.1)
# Source: Documents/ExecutionPlan/FrontEnd/Screens/FRONTEND_TOURNAMENT_SITEMAP.md (Section 1.1)

"""
Tournament Frontend Views (Main)

These views serve the tournament-focused frontend pages using Django templates.
All views integrate with existing backend APIs from apps/tournaments/api/

Sprint 1 Implementation (November 15, 2025):
- FE-T-001: Tournament List/Discovery Page
- FE-T-002: Tournament Detail Page  
- FE-T-003: Registration CTA States (integrated in detail view)
"""

from django.views.generic import ListView, DetailView
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from typing import Dict, Any
from apps.tournaments.models import Tournament, TournamentAnnouncement
from apps.tournaments.services.registration_service import RegistrationService
from django.core.exceptions import ValidationError
from apps.common.game_registry import get_game, normalize_slug
import requests


class TournamentListView(ListView):
    """
    FE-T-001: Tournament List/Discovery Page
    
    URL: /tournaments/
    Template: templates/tournaments/list_redesigned.html
    
    Features:
    - Tournament cards with key info (game, format, prize, date, slots)
    - Filters: Game, Status (upcoming, registration open, live, completed)
    - Search by tournament name
    - Pagination
    - Responsive design (mobile-first)
    
    Backend API: GET /api/tournaments/tournament-discovery/ (discovery_views.py)
    """
    template_name = 'tournaments/list_redesigned.html'
    context_object_name = 'tournament_list'
    paginate_by = 20
    
    def get_queryset(self):
        """
        Filter tournaments matching the discovery API parameters.
        Parameters mirror GET /api/tournaments/tournament-discovery/ (discovery_views.py)
        
        Supported filters (from planning docs):
        - game: Game slug or name filter (game is ForeignKey to Game model)
        - status: published, registration_open, live, completed
        - search: Full-text search on name, description
        - format: Tournament format filter
        - free_only: Boolean for free tournaments
        """
        from django.db.models import Count, Q
        from apps.tournaments.models import Registration
        
        # Optimize query with select_related for ForeignKey fields
        queryset = Tournament.objects.select_related('game', 'organizer').filter(
            status__in=['published', 'registration_open', 'live', 'completed']
        ).annotate(
            registration_count=Count(
                'registrations',
                filter=Q(
                    registrations__status__in=['pending', 'payment_submitted', 'confirmed'],
                    registrations__is_deleted=False
                )
            )
        ).order_by('-tournament_start')
        
        # Filter by game (match API param: ?game=<slug>)
        # Tournament.game is ForeignKey to Game model
        game_filter = self.request.GET.get('game')
        if game_filter:
            queryset = queryset.filter(game__slug=game_filter)
        
        # Filter by status (match API param: ?status=<status>)
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by format (match API param: ?format=<format>)
        format_filter = self.request.GET.get('format')
        if format_filter:
            queryset = queryset.filter(format=format_filter)  # NOTE: Model field is 'format' not 'tournament_format'
        
        # Search by name/description (match API param: ?search=<query>)
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # Free tournaments only (match API param: ?free_only=true)
        free_only = self.request.GET.get('free_only')
        if free_only and free_only.lower() in ['true', '1', 'yes']:
            queryset = queryset.filter(Q(entry_fee__isnull=True) | Q(entry_fee=0))
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add user registration status for each tournament (for dynamic buttons)
        from apps.tournaments.services.eligibility_service import RegistrationEligibilityService
        
        # Add eligibility check for each tournament (for both authenticated and non-authenticated users)
        tournament_eligibility = {}
        for tournament in context['tournament_list']:
            eligibility = RegistrationEligibilityService.check_eligibility(
                tournament, self.request.user if self.request.user.is_authenticated else None
            )
            tournament_eligibility[tournament.id] = eligibility
        context['tournament_eligibility'] = tournament_eligibility
        
        if self.request.user.is_authenticated:
            from apps.tournaments.models import Registration
            
            # Get user's registrations
            user_registrations = Registration.objects.filter(
                user=self.request.user,
                tournament__in=context['tournament_list'],
                is_deleted=False
            ).exclude(
                status__in=[Registration.CANCELLED, Registration.REJECTED]
            ).values_list('tournament_id', flat=True)
            context['user_registered_tournaments'] = set(user_registrations)
        else:
            context['user_registered_tournaments'] = set()
        
        # Add games for filter dropdown using Game Registry (unified game data)
        # Provides: display_name, icon, logo, banner, card, colors, category
        from apps.common.game_registry import get_all_games
        all_games = get_all_games()
        
        # Convert Game Registry specs to format expected by template
        context['games'] = [
            {
                'slug': game.slug,
                'name': game.display_name,
                'icon': game.icon,
                'card': game.card,
            }
            for game in all_games
        ]
        
        # Add current filter values (all parameters must be URL-synced)
        context['current_game'] = self.request.GET.get('game', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_search'] = self.request.GET.get('search', '')
        context['current_format'] = self.request.GET.get('format', '')
        context['current_free_only'] = self.request.GET.get('free_only', '')
        
        # Status options for filter tabs (from Sitemap Section 1.1)
        context['status_options'] = [
            {'value': '', 'label': 'All'},
            {'value': 'registration_open', 'label': 'Registration Open'},
            {'value': 'live', 'label': 'Live'},
            {'value': 'published', 'label': 'Upcoming'},
            {'value': 'completed', 'label': 'Completed'},
        ]
        
        # Format options for additional filtering
        context['format_options'] = [
            {'value': '', 'label': 'All Formats'},
            {'value': 'single_elimination', 'label': 'Single Elimination'},
            {'value': 'double_elimination', 'label': 'Double Elimination'},
            {'value': 'round_robin', 'label': 'Round Robin'},
            {'value': 'swiss', 'label': 'Swiss'},
        ]
        
        return context


class TournamentDetailView(DetailView):
    """
    FE-T-002: Tournament Detail Page
    
    URL: /tournaments/<slug>/
    Template: templates/tournaments/detailPages/detail.html
    
    Features:
    - Hero section with banner, game badge, status
    - Key info bar (format, date, prize, slots)
    - Tabs: Overview, Schedule, Prizes, Rules/FAQ
    - Registration CTA with dynamic states (FE-T-003)
    - Adapts based on tournament state (before/during/after)
    
    Backend APIs:
    - GET /api/tournaments/<id>/ (tournament_views.py)
    - GET /api/tournaments/registrations/status/ (registrations.py)
    """
    model = Tournament
    template_name = 'tournaments/detailPages/detail.html'
    context_object_name = 'tournament'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        user = self.request.user
        
        # Add Game Registry integration - unified game data
        # Provides: display_name, icon, logo, banner, colors, theme, roster config
        canonical_slug = normalize_slug(tournament.game.slug)
        game_spec = get_game(canonical_slug)
        context['game_spec'] = game_spec
        
        # Use centralized eligibility service (consistent with list page and registration form)
        from apps.tournaments.services.eligibility_service import RegistrationEligibilityService
        eligibility = RegistrationEligibilityService.check_eligibility(tournament, user)
        
        # Add eligibility data to context
        context['can_register'] = eligibility['can_register']
        context['registration_status_reason'] = eligibility['reason']
        context['is_registered'] = eligibility['registration'] is not None
        context['user_registration'] = eligibility['registration']
        context['eligibility_status'] = eligibility['status']
        
        # ALWAYS provide registration URL - let the registration form handle eligibility checks
        # This ensures users can always click "Register" and get proper feedback
        if tournament.participation_type == Tournament.TEAM:
            context['registration_action_url'] = f'/tournaments/{tournament.slug}/register/team/'
            context['registration_action_label'] = 'Register Team'
        else:
            context['registration_action_url'] = f'/tournaments/{tournament.slug}/register/'
            context['registration_action_label'] = 'Register Now'
        
        # Override with specific action if already registered
        if eligibility['registration'] is not None:
            context['registration_action_url'] = f'/tournaments/{tournament.slug}/lobby/'
            context['registration_action_label'] = 'Enter Lobby'
        
        # Calculate slots info (always visible)
        from apps.tournaments.models import Registration
        slots_filled = Registration.objects.filter(
            tournament=tournament,
            status__in=[Registration.PENDING, Registration.PAYMENT_SUBMITTED, Registration.CONFIRMED],
            is_deleted=False
        ).count()
        context['slots_filled'] = slots_filled
        context['slots_total'] = tournament.max_participants
        context['slots_percentage'] = (slots_filled / tournament.max_participants * 100) if tournament.max_participants > 0 else 0
        
        # Add announcements for this tournament
        announcements = TournamentAnnouncement.objects.filter(
            tournament=tournament
        ).select_related('created_by').order_by('-is_pinned', '-created_at')[:10]
        context['announcements'] = announcements
        
        # Add participants data for Participants tab
        context.update(self._get_participants_context(tournament, user))
        
        # Add bracket context (for all tournament types)
        from apps.tournaments.models import Bracket
        try:
            bracket = tournament.bracket  # OneToOneField relationship
            context['bracket'] = bracket
        except Bracket.DoesNotExist:
            context['bracket'] = None
        
        # Add multi-stage tournament context (GROUP_PLAYOFF format)
        if tournament.format == Tournament.GROUP_PLAYOFF:
            context['is_multi_stage'] = True
            current_stage = tournament.get_current_stage()
            context['current_stage'] = current_stage
            
            # Stage history from config
            config = tournament.config or {}
            context['stages'] = config.get('stages', [])
            
            # Always include groups data (useful for both group and knockout stages)
            from apps.tournaments.models import Group, GroupStanding
            
            groups = Group.objects.filter(
                tournament=tournament,
                is_deleted=False
            ).order_by('display_order')
            context['groups'] = groups
            
            # Build group standings dict: {group.id: [standings...]}
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
        
        # Add matches context for Matches tab
        context.update(self._get_matches_context(tournament))
        
        # Add standings context for Standings tab
        context.update(self._get_standings_context(tournament))
        
        # Add streams context for Streams & Media tab
        context.update(self._get_streams_context(tournament))
        
        return context
    
    def _get_registration_status(self, tournament, user):
        """
        Sprint 5 Helper: Get detailed registration validation status
        
        Returns dict with:
        - state: str (payment_pending, approval_pending, check_in_required, checked_in, confirmed)
        - reason: str (human-readable message)
        - check_in_window: dict (if applicable)
        - payment_status: str (if applicable)
        - approval_status: bool (if applicable)
        """
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
        
        # Check 1: Payment status (if tournament has entry fee)
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
        
        # Check 2: Approval status (if tournament requires approval)
        if hasattr(tournament, 'requires_approval') and tournament.requires_approval:
            if hasattr(registration, 'status'):
                if registration.status == Registration.PENDING:
                    return {
                        'state': 'approval_pending',
                        'reason': 'Your registration is awaiting organizer approval.',
                        'approval_status': 'pending',
                    }
        
        # Check 3: Check-in status (if check-in window open or closed)
        check_in_window = {
            'opens_at': CheckInService.get_check_in_opens_at(tournament),
            'closes_at': CheckInService.get_check_in_closes_at(tournament),
            'is_open': CheckInService.is_check_in_window_open(tournament),
        }
        
        now = timezone.now()
        
        # Already checked in
        if registration.checked_in:
            return {
                'state': 'checked_in',
                'reason': f'Checked in at {registration.checked_in_at.strftime("%b %d, %H:%M")}',
                'check_in_window': check_in_window,
            }
            
            # Check-in window is open, but not checked in yet
            if check_in_window['is_open']:
                return {
                    'state': 'check_in_required',
                    'reason': f'Check-in required before {check_in_window["closes_at"].strftime("%b %d, %H:%M")}',
                    'check_in_window': check_in_window,
                }
            
            # Check-in window not yet open (but tournament soon)
            if now < check_in_window['opens_at']:
                return {
                    'state': 'confirmed',
                    'reason': f'Registration confirmed. Check-in opens {check_in_window["opens_at"].strftime("%b %d, %H:%M")}',
                    'check_in_window': check_in_window,
                }
        
        # Default: Confirmed registration (no pending actions)
        return {
            'state': 'confirmed',
            'reason': 'Registration confirmed',
        }
    
    def _get_participants_context(self, tournament, user):
        """
        Get context data for Participants tab.
        
        Returns dict with:
        - participants: List of participant data (team or user)
        - participants_total: Total registered count
        - participants_confirmed: Confirmed count
        - participants_waitlist: Waitlist count
        - current_user_registration: Current user's registration (if any)
        - is_organizer: Whether user is organizer
        """
        from apps.tournaments.models import Registration
        from apps.teams.models import Team
        
        # Base queryset - only non-deleted, non-cancelled, non-rejected registrations
        registrations_qs = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).exclude(
            status__in=[Registration.CANCELLED, Registration.REJECTED]
        ).select_related('user', 'user__profile').order_by('registered_at')
        
        participants_list = []
        current_user_registration = None
        
        if tournament.participation_type == 'team':
            # Team-based tournament
            for reg in registrations_qs:
                if not reg.team_id:
                    continue
                
                # Get team data (Team model uses IntegerField for team_id)
                try:
                    team = Team.objects.select_related('captain').prefetch_related(
                        'memberships__profile'
                    ).get(id=reg.team_id)
                except Team.DoesNotExist:
                    continue
                
                # Build roster summary
                active_members = team.memberships.filter(
                    status='ACTIVE'
                ).select_related('profile', 'profile__user')
                
                roster_summary = []
                for membership in active_members[:3]:  # Show first 3 members
                    roster_summary.append({
                        'name': membership.profile.display_name or membership.profile.user.username,
                        'role': membership.get_role_display(),
                    })
                
                # Check if this is current user's team
                is_current_user_team = False
                if user.is_authenticated:
                    is_current_user_team = active_members.filter(
                        profile__user=user
                    ).exists()
                    if is_current_user_team:
                        current_user_registration = reg
                
                # Get team ranking (if available)
                team_rank = None
                try:
                    from apps.teams.models import TeamRankingBreakdown
                    ranking = TeamRankingBreakdown.objects.filter(team=team).first()
                    if ranking and ranking.final_total > 0:
                        # Calculate rank
                        teams_above = TeamRankingBreakdown.objects.filter(
                            team__game=team.game,
                            final_total__gt=ranking.final_total
                        ).count()
                        team_rank = teams_above + 1
                except:
                    pass
                
                participants_list.append({
                    'type': 'team',
                    'kind': 'team',  # Explicit type for template
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
            # Solo tournament
            for reg in registrations_qs:
                if not reg.user:
                    continue
                
                # Check if this is current user
                is_current_user = user.is_authenticated and reg.user.id == user.id
                if is_current_user:
                    current_user_registration = reg
                
                # Get player data
                profile = reg.user.profile if hasattr(reg.user, 'profile') else None
                display_name = profile.display_name if profile and profile.display_name else reg.user.username
                
                # Get game ID from registration_data if available
                game_id = ''
                if reg.registration_data and isinstance(reg.registration_data, dict):
                    game_id = reg.registration_data.get('game_id', '')
                
                region = profile.region if profile and hasattr(profile, 'region') else ''
                participants_list.append({
                    'type': 'solo',
                    'kind': 'player',  # Explicit type for template
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
        
        # Calculate stats
        confirmed_count = registrations_qs.filter(status=Registration.CONFIRMED).count()
        waitlist_count = 0  # TODO: Implement waitlist logic if needed
        
        # Check if user is organizer
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
        """
        Build matches context for Matches tab.
        
        Returns dict with:
        - matches: list of match dicts with UI-friendly attributes
        """
        from apps.tournaments.models import Match, Group
        from apps.teams.models import Team
        from django.utils import timezone
        
        # Fetch all matches for this tournament
        matches_qs = Match.objects.filter(
            tournament=tournament,
            is_deleted=False
        ).select_related('bracket').order_by(
            'scheduled_time',
            'round_number',
            'match_number'
        )
        
        # Preload team names for efficient lookup
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
        
        # Precompute UI attributes for each match
        matches_list = []
        now = timezone.now()
        
        for match in matches_qs:
            # Determine phase
            if tournament.format == tournament.GROUP_PLAYOFF:
                phase = 'group_stage' if match.bracket is None else 'knockout_stage'
            else:
                phase = 'knockout_stage'  # Single-stage tournaments
            
            # Determine UI status
            if match.state == 'live':
                ui_status = 'live'
            elif match.state in ['completed', 'forfeit', 'cancelled', 'disputed']:
                ui_status = 'completed'
            else:
                ui_status = 'upcoming'
            
            # Determine if live/completed
            is_live = match.state == 'live'
            is_completed = match.state in ['completed', 'forfeit', 'cancelled']
            
            # Show scores for live and completed matches
            show_scores = match.state in ['live', 'completed', 'pending_result', 'disputed']
            
            # Determine winner (1 or 2 or None)
            winner = None
            if match.winner_id:
                if match.winner_id == match.participant1_id:
                    winner = 1
                elif match.winner_id == match.participant2_id:
                    winner = 2
            
            # Group name for group stage (initialize early)
            group_name = ''
            if phase == 'group_stage':
                # Try to find group by checking match participants
                # This is a simple heuristic - you may need to adjust based on your data model
                try:
                    # If you have a direct group FK on Match, use that
                    # Otherwise, we'll leave it empty for now
                    pass
                except:
                    pass
            
            # Round label for knockout
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
            
            # Build stage label
            stage_label = ''
            if phase == 'group_stage' and group_name:
                stage_label = f"Group {group_name}"
                if match.round_number:
                    stage_label += f" – Round {match.round_number}"
            elif phase == 'knockout_stage' and round_label:
                stage_label = round_label
            elif match.round_number:
                stage_label = f"Round {match.round_number}"
            
            # Match label
            match_label = f"Match #{match.match_number}" if match.match_number else "Match"
            
            # Format start time
            start_time_display = ''
            if match.scheduled_time:
                start_time_display = match.scheduled_time.strftime('%b %d · %H:%M')
            
            # Resolve participant names and logos
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
            
            # Determine winners
            team1_is_winner = winner == 1
            team2_is_winner = winner == 2
            
            # Format times
            starts_at = match.scheduled_time
            starts_at_display = start_time_display
            
            # Calculate relative time (simplified - could be enhanced)
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
                    # Past time
                    hours = int(abs(delta.total_seconds()) // 3600)
                    if is_completed:
                        if hours > 24:
                            days = hours // 24
                            starts_at_relative = f"Finished {days}d ago"
                        elif hours > 0:
                            starts_at_relative = f"Finished {hours}h ago"
                        else:
                            starts_at_relative = "Finished recently"
            
            # Best of label (placeholder - extend if your model has this)
            best_of_label = ''  # e.g., 'BO3', 'BO5'
            
            # Extract lobby_info for template access
            lobby_info = match.lobby_info or {}
            
            # If lobby_info has best_of, use it for label
            if lobby_info.get('best_of'):
                best_of_label = f"BO{lobby_info['best_of']}"
            
            matches_list.append({
                'id': match.id,
                'participant1_name': p1_name,
                'participant2_name': p2_name,
                'participant1_score': match.participant1_score if show_scores else 0,
                'participant2_score': match.participant2_score if show_scores else 0,
                'state': match.state,
                'status': ui_status,  # Normalized status
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
                'starts_at_display': starts_at_display,
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
                'vod_url': None,  # Add if you have a vod_url field
                'participant1_logo': p1_logo,
                'participant2_logo': p2_logo,
                'lobby_info': lobby_info,  # Pass lobby_info to template for BR leaderboards and stage labels
                'round_number': match.round_number,  # For BR round display
                'winner_id': match.winner_id,  # For BR winner detection
            })
        
        return {
            'matches': matches_list,
        }
    
    def _get_standings_context(self, tournament: Tournament) -> Dict[str, Any]:
        """
        Build standings context for Standings tab.
        
        Returns unified standings data for both GROUP_PLAYOFF and single-stage tournaments:
        - standings_primary: main leaderboard table rows
        - standings_source: source description ("group_stage", "bracket", "mixed")
        - group_standings_summary: grouped advancers/others for GROUP_PLAYOFF (optional)
        
        Logic:
        - GROUP_PLAYOFF: Aggregate all group standings, rank by group position then points
        - Single-stage: Build from match results or registrations (simplified)
        """
        from apps.tournaments.models.group import Group, GroupStanding
        from django.db.models import Q, Count, Sum, F
        
        context = {
            'standings_primary': [],
            'standings_source': 'unknown',
            'group_standings_summary': None
        }
        
        # GROUP_PLAYOFF: Use group standings
        if tournament.format == 'group_playoff':
            groups = Group.objects.filter(
                tournament=tournament,
                is_deleted=False
            ).order_by('display_order')
            
            if not groups.exists():
                return context
            
            # Build primary standings: all participants from all groups
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
                    # Determine participant name
                    if standing.team:
                        participant_name = standing.team.name
                        participant_id = f"team-{standing.team.id}"
                    elif standing.user:
                        participant_name = standing.user.profile.display_name if hasattr(standing.user, 'profile') and standing.user.profile.display_name else standing.user.username
                        participant_id = f"user-{standing.user.id}"
                    else:
                        participant_name = "Unknown"
                        participant_id = "unknown"
                    
                    # Determine if advancing
                    is_advancing = idx <= group.advancement_count
                    
                    # Build row for primary table
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
                        # Game-specific stats (nullable)
                        'goal_difference': standing.goal_difference if standing.goal_difference != 0 else None,
                        'round_difference': standing.round_difference if standing.round_difference != 0 else None,
                        'kill_difference': standing.total_kills - standing.total_deaths if (standing.total_kills > 0 or standing.total_deaths > 0) else None,
                        'game_specific_label': None
                    }
                    
                    all_standings.append(row)
                    
                    # Build group summary entry
                    summary_entry = {
                        'rank': idx,
                        'name': participant_name
                    }
                    
                    if is_advancing:
                        advancers.append(summary_entry)
                    else:
                        others.append(summary_entry)
                
                # Add group summary
                group_summaries.append({
                    'name': group.name,
                    'advancers': advancers,
                    'others': others
                })
            
            # Sort primary standings: advancers first (by rank), then others
            all_standings.sort(key=lambda x: (
                not x['is_advancing'],  # False (advancing) sorts before True (not advancing)
                x['rank']  # Then by rank within each category
            ))
            
            # Reassign global ranks
            for idx, row in enumerate(all_standings, start=1):
                row['global_rank'] = idx
            
            context['standings_primary'] = all_standings
            context['standings_source'] = 'group_stage'
            context['group_standings_summary'] = group_summaries
            
        else:
            # Single-stage tournaments: Build simplified standings from matches or registrations
            # For now, use a basic aggregation from Registration model
            from apps.tournaments.models import Registration, Match
            from apps.teams.models import Team
            
            registrations = Registration.objects.filter(
                tournament=tournament,
                is_deleted=False,
                status__in=['confirmed', 'checked_in']
            ).select_related('user')
            
            if not registrations.exists():
                return context
            
            # Fetch all teams in one query (for team_id lookups)
            team_ids = [reg.team_id for reg in registrations if reg.team_id]
            teams_map = {team.id: team for team in Team.objects.filter(id__in=team_ids)} if team_ids else {}
            
            # Build standings from match results (simplified)
            standings_rows = []
            
            for reg in registrations:
                # Determine participant name and ID
                if reg.team_id:
                    team = teams_map.get(reg.team_id)
                    participant_name = team.name if team else f"Team #{reg.team_id}"
                    participant_id = f"team-{reg.team_id}"
                    participant_type = 'team'
                    pid = reg.team_id
                elif reg.user:
                    participant_name = reg.user.profile.display_name if hasattr(reg.user, 'profile') and reg.user.profile.display_name else reg.user.username
                    participant_id = f"user-{reg.user.id}"
                    participant_type = 'user'
                    pid = reg.user.id
                else:
                    continue
                
                # Count matches for this participant
                # Match model uses participant1_id/participant2_id as integers
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
                points = wins * 3  # Simple 3 points per win
                
                standings_rows.append({
                    'rank': 0,  # Will be assigned after sorting
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
            
            # Sort by points DESC, then wins DESC
            standings_rows.sort(key=lambda x: (-x['points'], -x['wins']))
            
            # Assign ranks
            for idx, row in enumerate(standings_rows, start=1):
                row['rank'] = idx
            
            context['standings_primary'] = standings_rows
            context['standings_source'] = 'bracket'
            context['group_standings_summary'] = None
        
        return context
    
    def _get_streams_context(self, tournament: Tournament) -> Dict[str, Any]:
        """
        Build streams and media context for Streams & Media tab.
        
        Returns:
        - featured_stream: Primary stream URL and metadata
        - additional_streams: List of secondary streams (other languages/POVs)
        - vods: List of past broadcasts
        - has_streams: Boolean indicating if any streams/VODs exist
        """
        context = {
            'featured_stream': None,
            'additional_streams': [],
            'vods': [],
            'has_streams': False
        }
        
        # Check if tournament has a primary stream URL
        if hasattr(tournament, 'stream_url') and tournament.stream_url:
            # Detect platform from URL
            stream_platform = 'other'
            embed_url = tournament.stream_url
            
            if 'youtube.com' in tournament.stream_url or 'youtu.be' in tournament.stream_url:
                stream_platform = 'youtube'
                # Extract video ID and create embed URL
                if 'watch?v=' in tournament.stream_url:
                    video_id = tournament.stream_url.split('watch?v=')[1].split('&')[0]
                    embed_url = f'https://www.youtube.com/embed/{video_id}'
                elif 'youtu.be/' in tournament.stream_url:
                    video_id = tournament.stream_url.split('youtu.be/')[1].split('?')[0]
                    embed_url = f'https://www.youtube.com/embed/{video_id}'
                    
            elif 'twitch.tv' in tournament.stream_url:
                stream_platform = 'twitch'
                # Extract channel name
                if '/videos/' in tournament.stream_url:
                    # VOD link
                    video_id = tournament.stream_url.split('/videos/')[1].split('?')[0]
                    embed_url = f'https://player.twitch.tv/?video={video_id}&parent={self.request.get_host()}'
                else:
                    # Live channel
                    channel = tournament.stream_url.split('twitch.tv/')[1].split('?')[0]
                    embed_url = f'https://player.twitch.tv/?channel={channel}&parent={self.request.get_host()}'
            
            context['featured_stream'] = {
                'url': tournament.stream_url,
                'embed_url': embed_url,
                'platform': stream_platform,
                'title': f"{tournament.name} - Live Stream",
                'is_live': tournament.status == 'live'
            }
            context['has_streams'] = True
        
        # Additional streams (if your model supports multiple streams)
        # This is a placeholder - extend based on your data model
        # if hasattr(tournament, 'additional_streams'):
        #     for stream in tournament.additional_streams.all():
        #         context['additional_streams'].append({
        #             'url': stream.url,
        #             'title': stream.title,
        #             'language': stream.language
        #         })
        
        # VODs (if your model supports VOD storage)
        # This is a placeholder - extend based on your data model
        # if hasattr(tournament, 'vods'):
        #     context['vods'] = [{
        #         'url': vod.url,
        #         'title': vod.title,
        #         'thumbnail': vod.thumbnail,
        #         'duration': vod.duration,
        #         'uploaded_at': vod.uploaded_at
        #     } for vod in tournament.vods.all()]
        
        return context


# ============================================================================
# Participant Check-in
# ============================================================================

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

@login_required
@require_POST
def participant_checkin(request, slug):
    """
    Allow participant to check themselves in during check-in window
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get user's registration
    from apps.tournaments.models import Registration
    try:
        registration = Registration.objects.get(
            tournament=tournament,
            user=request.user,
            is_deleted=False
        )
    except Registration.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Registration not found'}, status=404)
    
    # Check if registration is confirmed
    if registration.status != 'confirmed':
        return JsonResponse({'success': False, 'error': 'Registration must be confirmed before check-in'}, status=400)
    
    # Check if already checked in
    if registration.checked_in:
        return JsonResponse({'success': False, 'error': 'Already checked in'}, status=400)
    
    # Check if check-in window is open
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
    
    # Perform check-in
    registration.checked_in = True
    registration.checked_in_at = timezone.now()
    registration.checked_in_by = request.user  # Self check-in
    registration.save()
    
    return JsonResponse({
        'success': True, 
        'message': 'Successfully checked in!',
        'checked_in_at': registration.checked_in_at.isoformat()
    })
