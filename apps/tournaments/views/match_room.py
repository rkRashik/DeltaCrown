"""
Match Room / Battlefield View

Interactive match room for participants during a match.
Extends existing MatchDetailView with participant-only features:
- Match-level check-in
- Lobby info display (game code, map, password)
- Countdown to match start
- Inline result submission
- Opponent info
- Match state awareness (pre-match → live → post-match)

URL: /tournaments/<slug>/matches/<match_id>/room/
"""

from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404, JsonResponse
from django.contrib import messages
from django.views import View
from django.utils import timezone
from django.db.models import Q

from apps.tournaments.models import Tournament, Match, Registration


class MatchRoomView(LoginRequiredMixin, DetailView):
    """
    Participant-exclusive match room.
    
    Shows different UI states based on match.state:
    - scheduled/check_in: Pre-match lobby with check-in, countdown, opponent info
    - ready/live: Active match with lobby info, scores, submit result CTA
    - pending_result/completed: Post-match with results, next match link
    - disputed: Dispute notice with timeline
    - forfeit/cancelled: Match ended notice
    """
    model = Match
    template_name = 'tournaments/match_room/room.html'
    context_object_name = 'match'
    pk_url_kwarg = 'match_id'

    def get_queryset(self):
        tournament_slug = self.kwargs.get('slug')
        return Match.objects.filter(
            tournament__slug=tournament_slug,
            is_deleted=False,
        ).select_related(
            'tournament',
            'tournament__game',
            'tournament__organizer',
        )

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        match_id = self.kwargs.get(self.pk_url_kwarg)
        try:
            return queryset.get(pk=match_id)
        except Match.DoesNotExist:
            raise Http404("Match not found.")

    def dispatch(self, request, *args, **kwargs):
        """Ensure only match participants can access the room."""
        self.object = self.get_object()
        match = self.object
        user = request.user

        if not user.is_authenticated:
            return self.handle_no_permission()

        # Check if user is a direct participant (solo tournaments)
        is_direct = (
            match.participant1_id == user.id or
            match.participant2_id == user.id
        )

        # Check if user is on a participating team (team tournaments)
        is_team_member = False
        if not is_direct:
            from apps.organizations.models import TeamMembership
            user_team_ids = set(
                TeamMembership.objects.filter(
                    user=user,
                    status=TeamMembership.Status.ACTIVE,
                ).values_list('team_id', flat=True)
            )
            if user_team_ids:
                is_team_member = (
                    match.participant1_id in user_team_ids or
                    match.participant2_id in user_team_ids
                )

        # Staff / organizer override
        is_staff = user.is_staff or match.tournament.organizer_id == user.id

        if not (is_direct or is_team_member or is_staff):
            messages.warning(request, "Only match participants can access the match room.")
            return redirect('tournaments:match_detail', slug=match.tournament.slug, match_id=match.id)

        self.user_side = None
        if match.participant1_id == user.id or (
            is_team_member and match.participant1_id in user_team_ids
        ):
            self.user_side = 1
        elif match.participant2_id == user.id or (
            is_team_member and match.participant2_id in user_team_ids
        ):
            self.user_side = 2

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # self.object already set in dispatch
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.object
        tournament = match.tournament
        user = self.request.user

        context['tournament'] = tournament
        context['user_side'] = self.user_side

        # Opponent info
        if self.user_side == 1:
            context['user_name'] = match.participant1_name
            context['opponent_name'] = match.participant2_name
            context['opponent_id'] = match.participant2_id
            context['user_checked_in'] = match.participant1_checked_in
            context['opponent_checked_in'] = match.participant2_checked_in
            context['user_score'] = match.participant1_score
            context['opponent_score'] = match.participant2_score
        elif self.user_side == 2:
            context['user_name'] = match.participant2_name
            context['opponent_name'] = match.participant1_name
            context['opponent_id'] = match.participant1_id
            context['user_checked_in'] = match.participant2_checked_in
            context['opponent_checked_in'] = match.participant1_checked_in
            context['user_score'] = match.participant2_score
            context['opponent_score'] = match.participant1_score
        else:
            # Staff observer
            context['user_name'] = 'Staff'
            context['opponent_name'] = None
            context['opponent_id'] = None
            context['user_checked_in'] = True
            context['opponent_checked_in'] = True
            context['user_score'] = 0
            context['opponent_score'] = 0

        # Lobby info structured
        lobby = match.lobby_info or {}
        context['lobby_code'] = lobby.get('lobby_code', '')
        context['lobby_password'] = lobby.get('password', '')
        context['lobby_map'] = lobby.get('map', '')
        context['lobby_server'] = lobby.get('server', '')
        context['lobby_game_mode'] = lobby.get('game_mode', '')
        context['lobby_raw'] = lobby

        # Match phase for template
        if match.state in (Match.SCHEDULED, Match.CHECK_IN):
            context['match_phase'] = 'pre_match'
        elif match.state in (Match.READY, Match.LIVE):
            context['match_phase'] = 'live'
        elif match.state in (Match.PENDING_RESULT, Match.COMPLETED):
            context['match_phase'] = 'post_match'
        else:
            context['match_phase'] = 'ended'

        # Countdown
        if match.scheduled_time:
            context['countdown_target'] = match.scheduled_time.isoformat()
        if match.check_in_deadline:
            context['checkin_deadline'] = match.check_in_deadline.isoformat()

        # Can submit result
        context['can_submit_result'] = (
            self.user_side in (1, 2) and
            match.state in (Match.LIVE, Match.PENDING_RESULT)
        )

        # Winner check
        if match.winner_id:
            context['is_winner'] = (
                (self.user_side == 1 and match.winner_id == match.participant1_id) or
                (self.user_side == 2 and match.winner_id == match.participant2_id)
            )
        else:
            context['is_winner'] = None

        # Next match in tournament for this participant
        if match.state == Match.COMPLETED and self.user_side:
            pid = match.participant1_id if self.user_side == 1 else match.participant2_id
            next_match = Match.objects.filter(
                tournament=tournament,
                is_deleted=False,
                state__in=[Match.SCHEDULED, Match.CHECK_IN, Match.READY],
            ).filter(
                Q(participant1_id=pid) | Q(participant2_id=pid)
            ).order_by('round_number', 'match_number').first()
            context['next_match'] = next_match

        # Game info for theming
        context['game'] = tournament.game
        game_colors = {
            'valorant': '#ff4655', 'pubg': '#f2a900', 'pubg-mobile': '#f2a900',
            'free-fire': '#ff5722', 'cod': '#1a1a2e', 'cod-mobile': '#1a1a2e',
            'fortnite': '#9d4dfa', 'csgo': '#de9b35', 'cs2': '#de9b35',
            'dota-2': '#c23c2a', 'league-of-legends': '#c89b3c',
            'apex-legends': '#cd3333', 'fifa': '#326295',
        }
        slug = ''
        if tournament.game:
            slug = getattr(tournament.game, 'slug', '') or ''
        context['game_color'] = game_colors.get(slug, '#06b6d4')

        return context


class MatchCheckInView(LoginRequiredMixin, View):
    """
    POST endpoint for per-match check-in.
    URL: /tournaments/<slug>/matches/<match_id>/room/check-in/
    """

    def post(self, request, slug, match_id):
        match = get_object_or_404(
            Match, id=match_id, tournament__slug=slug, is_deleted=False,
        )

        if match.state not in (Match.CHECK_IN, Match.SCHEDULED):
            messages.error(request, "Check-in is not available for this match.")
            return redirect('tournaments:match_room', slug=slug, match_id=match_id)

        user = request.user
        updated = False

        if match.participant1_id == user.id and not match.participant1_checked_in:
            match.participant1_checked_in = True
            updated = True
        elif match.participant2_id == user.id and not match.participant2_checked_in:
            match.participant2_checked_in = True
            updated = True
        else:
            # Check team membership
            from apps.organizations.models import TeamMembership
            user_team_ids = set(
                TeamMembership.objects.filter(
                    user=user, status=TeamMembership.Status.ACTIVE
                ).values_list('team_id', flat=True)
            )
            if match.participant1_id in user_team_ids and not match.participant1_checked_in:
                match.participant1_checked_in = True
                updated = True
            elif match.participant2_id in user_team_ids and not match.participant2_checked_in:
                match.participant2_checked_in = True
                updated = True

        if updated:
            # If both checked in, advance to READY
            if match.is_both_checked_in:
                match.state = Match.READY
            match.save(update_fields=[
                'participant1_checked_in', 'participant2_checked_in', 'state',
            ])
            messages.success(request, "Check-in successful!")
        else:
            messages.info(request, "Already checked in.")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'checked_in': True,
                'both_ready': match.is_both_checked_in,
            })

        return redirect('tournaments:match_room', slug=slug, match_id=match_id)
