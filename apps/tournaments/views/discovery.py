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
            queryset = queryset.filter(Q(entry_fee__isnull=True) | Q(entry_fee=0))

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
        else:
            context['user_registered_tournaments'] = set()

        all_games = game_service.list_active_games()
        context['games'] = [
            {
                'slug': game.slug,
                'name': game.display_name,
                'icon': game.icon.url if game.icon else None,
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

        return context
