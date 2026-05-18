"""
Tournament Discovery View — Public tournament listing with filters.

FE-T-001: Tournament List/Discovery Page
Extracted from main.py during Phase 3 restructure.
"""

from django.views.generic import ListView
from django.db.models import Q, Count
from django.core.cache import cache
from apps.tournaments.models import Tournament
from apps.games.services import game_service
from apps.common.seo import breadcrumb_schema, build_seo


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
            status__in=['published', 'registration_open', 'registration_closed', 'live', 'completed']
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

        # T3-2: Annotate effective status efficiently — only GROUP_PLAYOFF
        # + completed need the method call; all others are identity.
        for t in context['tournament_list']:
            if t.format == Tournament.GROUP_PLAYOFF and t.status == Tournament.COMPLETED:
                t.effective_status = t.get_effective_status()
            else:
                t.effective_status = t.status

        from apps.tournaments.services.eligibility_service import RegistrationEligibilityService

        # Bulk: one batched fetch of every per-user dataset feeds all
        # tournament cards on this page. Replaces a ~5-10x per-tournament
        # query loop that was the dominant egress driver here.
        viewer = self.request.user if self.request.user.is_authenticated else None
        tournament_eligibility = RegistrationEligibilityService.check_eligibility_bulk(
            context['tournament_list'], viewer,
        )
        for tournament in context['tournament_list']:
            tournament.discovery_eligibility = tournament_eligibility.get(
                tournament.id, {'can_register': False, 'status': 'unknown'}
            )
        context['tournament_eligibility'] = tournament_eligibility

        if self.request.user.is_authenticated:
            from apps.tournaments.models import Registration
            from apps.user_profile.models import UserProfile
            from apps.organizations.models import TeamMembership

            # Single pass: fetch only the columns needed and build both the ID
            # set and status map in one iteration (was 2 duplicated queries).
            solo_regs = list(
                Registration.objects.filter(
                    user=self.request.user,
                    tournament__in=context['tournament_list'],
                    is_deleted=False,
                ).exclude(
                    status__in=[Registration.CANCELLED, Registration.REJECTED],
                ).order_by('-created_at').values_list('tournament_id', 'status')
            )
            user_registrations = {tid for tid, _ in solo_regs}
            user_registration_status_map = {}
            for tid, status in solo_regs:
                user_registration_status_map.setdefault(tid, status)

            team_registrations = set()
            user_profile = UserProfile.objects.filter(user=self.request.user).first()
            try:
                if user_profile:
                    user_team_ids = list(TeamMembership.objects.filter(
                        profile=user_profile,
                        status=TeamMembership.Status.ACTIVE
                    ).values_list('team_id', flat=True))

                    if user_team_ids:
                        # Single pass: same dedup as solo path above.
                        team_regs = list(
                            Registration.objects.filter(
                                team_id__in=user_team_ids,
                                tournament__in=context['tournament_list'],
                                tournament__participation_type=Tournament.TEAM,
                                is_deleted=False,
                            ).exclude(
                                status__in=[Registration.CANCELLED, Registration.REJECTED],
                            ).order_by('-created_at').values_list('tournament_id', 'status')
                        )
                        team_registrations = {tid for tid, _ in team_regs}
                        for tid, status in team_regs:
                            user_registration_status_map.setdefault(tid, status)
            except Exception:
                pass

            context['user_registered_tournaments'] = user_registrations | team_registrations
            context['user_registration_status_map'] = user_registration_status_map
            for tournament in context['tournament_list']:
                tournament.user_reg_status = user_registration_status_map.get(tournament.id)

            # Organizer tournaments — tournaments this user organizes (for "Manage" CTA)
            organizer_tournaments = set(
                Tournament.objects.filter(
                    organizer=self.request.user,
                    id__in=[t.id for t in context['tournament_list']]
                ).values_list('id', flat=True)
            )
            # Staff/superuser can manage all
            if self.request.user.is_staff or self.request.user.is_superuser:
                organizer_tournaments = set(t.id for t in context['tournament_list'])
            context['organizer_tournaments'] = organizer_tournaments

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
                        'status': getattr(t, 'effective_status', None) or t.status,
                        'game_name': t.game.display_name if t.game else '',
                        'game_logo': t.game.logo.url if t.game and t.game.logo else None,
                        'tournament_start': t.tournament_start,
                        'reg_status': reg.status,
                        'participation_type': t.participation_type,
                    })
            context['my_tournaments_sidebar'] = my_tournaments_sidebar[:8]
        else:
            context['user_registered_tournaments'] = set()
            context['organizer_tournaments'] = set()
            context['my_tournaments_sidebar'] = []
            context['user_registration_status_map'] = {}
            for tournament in context['tournament_list']:
                tournament.user_reg_status = None

        # Active-games list rarely changes; serve from cache to remove a
        # per-request DB hit and trim row egress on every page paint.
        def _games_payload():
            return [
                {
                    'slug': game.slug,
                    'name': game.display_name,
                    'icon': game.icon.url if game.icon else None,
                    'logo': game.logo.url if game.logo else None,
                    'banner': game.banner.url if game.banner else None,
                    'card': game.card_image.url if game.card_image else None,
                }
                for game in game_service.list_active_games()
            ]
        context['games'] = cache.get_or_set('discovery:games:v1', _games_payload, 900)

        context['current_game'] = self.request.GET.get('game', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_search'] = self.request.GET.get('search', '')
        context['current_format'] = self.request.GET.get('format', '')
        context['current_free_only'] = self.request.GET.get('free_only', '')
        has_low_value_filter = any([
            context['current_search'],
            self.request.GET.get('format'),
            self.request.GET.get('free_only'),
        ])
        context['seo'] = build_seo(
            title="Esports Tournaments | DeltaCrown",
            description=(
                "Discover DeltaCrown esports tournaments across Bangladesh and South Asia, "
                "with registration, Match Rooms, brackets, results, teams, and Crown Points progression."
            ),
            path="/tournaments/",
            noindex=bool(has_low_value_filter),
            schema=breadcrumb_schema([("Home", "/"), ("Tournaments", "/tournaments/")]),
        )

        context['status_options'] = [
            {'value': '', 'label': 'All'},
            {'value': 'registration_open', 'label': 'Registration Open'},
            {'value': 'registration_closed', 'label': 'Registration Closed'},
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

        # Featured tournaments for hero carousel (max 3, live or featured).
        # Cache the queryset (5 min) — featured set turns over slowly. Eligibility
        # is per-user so it stays out of the cache.
        def _featured_payload():
            return list(Tournament.objects.select_related('game').filter(
                status__in=['live', 'registration_open', 'published'],
                is_featured=True,
            ).order_by('-tournament_start')[:3])
        context['featured_tournaments'] = cache.get_or_set(
            'discovery:featured_tournaments:v1', _featured_payload, 300,
        )
        # Bulk-resolve eligibility for the featured set in one batched fetch.
        featured_eligibility = RegistrationEligibilityService.check_eligibility_bulk(
            context['featured_tournaments'], viewer,
        )
        for tournament in context['featured_tournaments']:
            tournament.discovery_eligibility = featured_eligibility.get(
                tournament.id, {'can_register': False, 'status': 'unknown'}
            )

        # Latest Winners — public, slow-changing. Build the dict payload once
        # and cache it (10 min). Avoids per-request joins on tournament/game/
        # winner/user + an extra Team lookup.
        def _latest_winners_payload():
            from apps.tournaments.models.result import TournamentResult
            from apps.organizations.models import Team
            results = list(TournamentResult.objects.select_related(
                'tournament', 'tournament__game', 'winner', 'winner__user'
            ).filter(
                tournament__status='completed',
                is_deleted=False,
            ).order_by('-created_at')[:5])

            team_ids_needed = [
                r.winner.team_id for r in results
                if r.winner and r.winner.team_id and not r.winner.user
            ]
            team_name_map = {}
            if team_ids_needed:
                team_name_map = dict(
                    Team.objects.filter(id__in=team_ids_needed).values_list('id', 'name')
                )

            payload = []
            for result in results:
                reg = result.winner
                if not reg:
                    continue
                if reg.user:
                    winner_name = reg.user.username
                elif reg.team_id:
                    winner_name = team_name_map.get(reg.team_id, 'Unknown Team')
                else:
                    winner_name = 'Unknown'
                payload.append({
                    'tournament_name': result.tournament.name,
                    'tournament_slug': result.tournament.slug,
                    'game_name': result.tournament.game.display_name if result.tournament.game else '',
                    'game_icon': result.tournament.game.icon.url if result.tournament.game and result.tournament.game.icon else None,
                    'winner_name': winner_name,
                    'prize_pool': result.tournament.prize_pool,
                    'completed_at': result.created_at,
                })
            return payload

        context['latest_winners'] = cache.get_or_set(
            'discovery:latest_winners:v1', _latest_winners_payload, 600,
        )

        return context
