"""
Tournament Discovery View — Public tournament listing with filters.

FE-T-001: Tournament List/Discovery Page
Extracted from main.py during Phase 3 restructure.
"""

from django.views.generic import ListView
from django.db.models import Q, Count
from apps.tournaments.models import Tournament
from apps.games.services import game_service


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
    """
    template_name = 'tournaments/list.html'
    context_object_name = 'tournament_list'
    paginate_by = 20

    def get_queryset(self):
        """
        Filter tournaments matching the discovery API parameters.
        Supported filters: game, status, format, search, free_only.
        """
        from apps.tournaments.models import Registration

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

        game_filter = self.request.GET.get('game')
        if game_filter:
            queryset = queryset.filter(game__slug=game_filter)

        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        format_filter = self.request.GET.get('format')
        if format_filter:
            queryset = queryset.filter(format=format_filter)

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        free_only = self.request.GET.get('free_only')
        if free_only and free_only.lower() in ['true', '1', 'yes']:
            queryset = queryset.filter(Q(has_entry_fee=False) | Q(entry_fee_amount__isnull=True) | Q(entry_fee_amount=0))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from apps.tournaments.services.eligibility_service import RegistrationEligibilityService

        tournament_eligibility = {}
        for tournament in context['tournament_list']:
            eligibility = RegistrationEligibilityService.check_eligibility(
                tournament, self.request.user if self.request.user.is_authenticated else None
            )
            tournament_eligibility[tournament.id] = eligibility
        context['tournament_eligibility'] = tournament_eligibility

        if self.request.user.is_authenticated:
            from apps.tournaments.models import Registration
            from apps.user_profile.models import UserProfile
            from apps.organizations.models import TeamMembership

            user_registrations = Registration.objects.filter(
                user=self.request.user,
                tournament__in=context['tournament_list'],
                is_deleted=False
            ).exclude(
                status__in=[Registration.CANCELLED, Registration.REJECTED]
            ).values_list('tournament_id', flat=True)

            team_registrations = set()
            try:
                user_profile = UserProfile.objects.filter(user=self.request.user).first()
                if user_profile:
                    user_team_ids = TeamMembership.objects.filter(
                        profile=user_profile,
                        status=TeamMembership.Status.ACTIVE
                    ).values_list('team_id', flat=True)

                    team_registrations = set(Registration.objects.filter(
                        team_id__in=user_team_ids,
                        tournament__in=context['tournament_list'],
                        tournament__participation_type=Tournament.TEAM,
                        is_deleted=False
                    ).exclude(
                        status__in=[Registration.CANCELLED, Registration.REJECTED]
                    ).values_list('tournament_id', flat=True))
            except Exception:
                pass

            context['user_registered_tournaments'] = set(user_registrations) | team_registrations

            # Also get ALL user registered tournaments (not just current page)
            all_solo_regs = Registration.objects.filter(
                user=self.request.user, is_deleted=False
            ).exclude(
                status__in=[Registration.CANCELLED, Registration.REJECTED]
            ).select_related('tournament', 'tournament__game').order_by('-created_at')[:10]

            all_team_regs = []
            try:
                if user_profile:
                    all_team_ids = TeamMembership.objects.filter(
                        profile=user_profile,
                        status=TeamMembership.Status.ACTIVE
                    ).values_list('team_id', flat=True)
                    all_team_regs = Registration.objects.filter(
                        team_id__in=all_team_ids,
                        tournament__participation_type=Tournament.TEAM,
                        is_deleted=False
                    ).exclude(
                        status__in=[Registration.CANCELLED, Registration.REJECTED]
                    ).select_related('tournament', 'tournament__game').order_by('-created_at')[:10]
            except Exception:
                pass

            # Build my_tournaments list for sidebar
            seen_ids = set()
            my_tournaments_sidebar = []
            for reg in list(all_solo_regs) + list(all_team_regs):
                t = reg.tournament
                if t.id not in seen_ids:
                    seen_ids.add(t.id)
                    my_tournaments_sidebar.append({
                        'id': t.id,
                        'name': t.name,
                        'slug': t.slug,
                        'status': t.status,
                        'game_name': t.game.display_name if t.game else '',
                        'game_logo': t.game.logo.url if t.game and t.game.logo else None,
                        'tournament_start': t.tournament_start,
                        'reg_status': reg.status,
                        'participation_type': t.participation_type,
                    })
            context['my_tournaments_sidebar'] = my_tournaments_sidebar[:8]
        else:
            context['user_registered_tournaments'] = set()
            context['my_tournaments_sidebar'] = []

        all_games = game_service.list_active_games()
        context['games'] = [
            {
                'slug': game.slug,
                'name': game.display_name,
                'icon': game.icon.url if game.icon else None,
                'logo': game.logo.url if game.logo else None,
                'banner': game.banner.url if game.banner else None,
                'card': game.card_image.url if game.card_image else None,
            }
            for game in all_games
        ]

        context['current_game'] = self.request.GET.get('game', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_search'] = self.request.GET.get('search', '')
        context['current_format'] = self.request.GET.get('format', '')
        context['current_free_only'] = self.request.GET.get('free_only', '')

        context['status_options'] = [
            {'value': '', 'label': 'All'},
            {'value': 'registration_open', 'label': 'Registration Open'},
            {'value': 'live', 'label': 'Live'},
            {'value': 'published', 'label': 'Upcoming'},
            {'value': 'completed', 'label': 'Completed'},
        ]

        context['format_options'] = [
            {'value': '', 'label': 'All Formats'},
            {'value': 'single_elimination', 'label': 'Single Elimination'},
            {'value': 'double_elimination', 'label': 'Double Elimination'},
            {'value': 'round_robin', 'label': 'Round Robin'},
            {'value': 'swiss', 'label': 'Swiss'},
        ]

        # Featured tournaments for hero carousel (max 3, live or featured)
        context['featured_tournaments'] = Tournament.objects.select_related('game').filter(
            status__in=['live', 'registration_open', 'published'],
            is_featured=True,
        ).order_by('-tournament_start')[:3]

        # Latest Winners — from TournamentResult for completed tournaments
        from apps.tournaments.models.result import TournamentResult
        latest_results = TournamentResult.objects.select_related(
            'tournament', 'tournament__game', 'winner', 'winner__user'
        ).filter(
            tournament__status='completed',
            is_deleted=False,
        ).order_by('-created_at')[:5]

        # Pre-fetch team names for winner registrations that have team_id
        from apps.organizations.models import Team
        team_ids_needed = [
            r.winner.team_id for r in latest_results
            if r.winner and r.winner.team_id and not r.winner.user
        ]
        team_name_map = {}
        if team_ids_needed:
            team_name_map = dict(
                Team.objects.filter(id__in=team_ids_needed).values_list('id', 'name')
            )

        latest_winners = []
        for result in latest_results:
            reg = result.winner
            if not reg:
                continue
            if reg.user:
                winner_name = reg.user.username
            elif reg.team_id:
                winner_name = team_name_map.get(reg.team_id, 'Unknown Team')
            else:
                winner_name = 'Unknown'
            latest_winners.append({
                'tournament_name': result.tournament.name,
                'tournament_slug': result.tournament.slug,
                'game_name': result.tournament.game.display_name if result.tournament.game else '',
                'game_icon': result.tournament.game.icon.url if result.tournament.game and result.tournament.game.icon else None,
                'winner_name': winner_name,
                'prize_pool': result.tournament.prize_pool,
                'completed_at': result.created_at,
            })
        context['latest_winners'] = latest_winners

        return context
