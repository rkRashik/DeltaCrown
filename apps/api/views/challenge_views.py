"""
Challenge & Bounty API views.

Phase 10: RESTful endpoints for the Challenge & Bounty competitive system.
All business logic delegated to ChallengeService / BountyService.
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.competition.models import Challenge, Bounty, BountyClaim
from apps.competition.services import ChallengeService, BountyService
from apps.api.serializers.challenge_serializers import (
    ChallengeListSerializer,
    ChallengeDetailSerializer,
    ChallengeCreateSerializer,
    ChallengeAcceptSerializer,
    ChallengeResultSerializer,
    ChallengeScheduleSerializer,
    ChallengeStatsSerializer,
    BountyListSerializer,
    BountyCreateSerializer,
    BountyClaimSerializer,
)
from apps.organizations.models import Team
from apps.games.models import Game

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  Challenge Views
# ═══════════════════════════════════════════════════════════════════════════

class ChallengeListCreateView(APIView):
    """
    GET  — List open/public challenges (optionally filtered by game).
    POST — Issue a new challenge.
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        game_id = request.query_params.get('game')
        game = None
        if game_id:
            game = get_object_or_404(Game, pk=game_id)

        challenges = ChallengeService.get_open_challenges(game=game, limit=50)
        serializer = ChallengeListSerializer(challenges, many=True)
        return Response(serializer.data)

    def post(self, request):
        ser = ChallengeCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        challenger_team = get_object_or_404(Team, pk=d['challenger_team_id'])
        game = get_object_or_404(Game, pk=d['game_id'])
        challenged_team = None
        if d.get('challenged_team_id'):
            challenged_team = get_object_or_404(Team, pk=d['challenged_team_id'])

        try:
            challenge = ChallengeService.create_challenge(
                created_by=request.user,
                challenger_team=challenger_team,
                challenged_team=challenged_team,
                game=game,
                title=d['title'],
                description=d.get('description', ''),
                challenge_type=d.get('challenge_type', 'DIRECT'),
                best_of=d.get('best_of', 1),
                game_config=d.get('game_config', {}),
                platform=d.get('platform', ''),
                server_region=d.get('server_region', ''),
                prize_type=d.get('prize_type', 'NONE'),
                prize_amount=d.get('prize_amount', 0),
                prize_description=d.get('prize_description', ''),
                scheduled_at=d.get('scheduled_at'),
                expires_at=d.get('expires_at'),
                is_public=d.get('is_public', True),
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ChallengeDetailSerializer(challenge).data,
            status=status.HTTP_201_CREATED,
        )


class ChallengeDetailView(APIView):
    """GET — Challenge detail by ID or reference code."""

    permission_classes = [AllowAny]

    def get(self, request, challenge_ref):
        # Try UUID first, then reference code
        try:
            challenge = Challenge.objects.select_related(
                'challenger_team', 'challenged_team', 'game'
            ).get(pk=challenge_ref)
        except (Challenge.DoesNotExist, ValueError):
            challenge = get_object_or_404(
                Challenge.objects.select_related(
                    'challenger_team', 'challenged_team', 'game'
                ),
                reference_code=challenge_ref,
            )

        return Response(ChallengeDetailSerializer(challenge).data)


class ChallengeAcceptView(APIView):
    """POST — Accept a challenge."""

    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        ser = ChallengeAcceptSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        accepting_team = None
        if ser.validated_data.get('accepting_team_id'):
            accepting_team = get_object_or_404(Team, pk=ser.validated_data['accepting_team_id'])

        try:
            challenge = ChallengeService.accept_challenge(
                challenge_id=challenge_id,
                accepted_by=request.user,
                accepting_team=accepting_team,
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ChallengeDetailSerializer(challenge).data)


class ChallengeDeclineView(APIView):
    """POST — Decline a challenge."""

    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        try:
            challenge = ChallengeService.decline_challenge(
                challenge_id=challenge_id,
                declined_by=request.user,
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Challenge declined.', 'status': challenge.status})


class ChallengeCancelView(APIView):
    """POST — Cancel a challenge (issuer only, before acceptance)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        try:
            challenge = ChallengeService.cancel_challenge(
                challenge_id=challenge_id,
                cancelled_by=request.user,
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Challenge cancelled.', 'status': challenge.status})


class ChallengeScheduleView(APIView):
    """POST — Schedule a challenge match time."""

    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        ser = ChallengeScheduleSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            challenge = ChallengeService.schedule_challenge(
                challenge_id=challenge_id,
                scheduled_at=ser.validated_data['scheduled_at'],
                scheduled_by=request.user,
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ChallengeDetailSerializer(challenge).data)


class ChallengeResultView(APIView):
    """POST — Submit the result of a completed challenge."""

    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        ser = ChallengeResultSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            challenge = ChallengeService.submit_result(
                challenge_id=challenge_id,
                submitted_by=request.user,
                result=ser.validated_data['result'],
                score_details=ser.validated_data.get('score_details', {}),
                evidence_url=ser.validated_data.get('evidence_url', ''),
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ChallengeDetailSerializer(challenge).data)


class ChallengeDisputeView(APIView):
    """POST — Dispute a challenge result."""

    permission_classes = [IsAuthenticated]

    def post(self, request, challenge_id):
        reason = request.data.get('reason', '')
        try:
            challenge = ChallengeService.dispute_challenge(
                challenge_id=challenge_id,
                disputed_by=request.user,
                reason=reason,
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'detail': 'Challenge disputed.', 'status': challenge.status})


class TeamChallengesView(APIView):
    """GET — List challenges for a specific team."""

    permission_classes = [AllowAny]

    def get(self, request, team_slug):
        team = get_object_or_404(Team, slug=team_slug)
        status_filter = request.query_params.get('status')

        challenges = ChallengeService.get_team_challenges(
            team=team,
            status_filter=status_filter,
            limit=int(request.query_params.get('limit', 20)),
        )
        serializer = ChallengeListSerializer(challenges, many=True)
        return Response(serializer.data)


class TeamChallengeStatsView(APIView):
    """GET — Challenge stats (wins/losses/earnings) for a team."""

    permission_classes = [AllowAny]

    def get(self, request, team_slug):
        team = get_object_or_404(Team, slug=team_slug)
        stats = ChallengeService.get_challenge_stats(team)
        return Response(ChallengeStatsSerializer(stats).data)


# ═══════════════════════════════════════════════════════════════════════════
#  Bounty Views
# ═══════════════════════════════════════════════════════════════════════════

class BountyListCreateView(APIView):
    """
    GET  — List active bounties (optionally filtered by game).
    POST — Create a new bounty.
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request):
        game_id = request.query_params.get('game')
        game = None
        if game_id:
            game = get_object_or_404(Game, pk=game_id)

        bounties = BountyService.get_active_bounties(game=game, limit=50)
        serializer = BountyListSerializer(bounties, many=True)
        return Response(serializer.data)

    def post(self, request):
        ser = BountyCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        issuer_team = get_object_or_404(Team, pk=d['issuer_team_id'])
        game = get_object_or_404(Game, pk=d['game_id'])

        try:
            bounty = BountyService.create_bounty(
                created_by=request.user,
                issuer_team=issuer_team,
                game=game,
                title=d['title'],
                description=d.get('description', ''),
                bounty_type=d.get('bounty_type', 'BEAT_US'),
                criteria=d.get('criteria', {}),
                reward_type=d.get('reward_type', 'CP'),
                reward_amount=d.get('reward_amount', 0),
                reward_description=d.get('reward_description', ''),
                max_claims=d.get('max_claims', 1),
                expires_at=d.get('expires_at'),
                is_public=d.get('is_public', True),
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            BountyListSerializer(bounty).data,
            status=status.HTTP_201_CREATED,
        )


class BountyClaimView(APIView):
    """POST — Submit a claim against a bounty."""

    permission_classes = [IsAuthenticated]

    def post(self, request, bounty_id):
        ser = BountyClaimSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        claiming_team = get_object_or_404(Team, pk=d['claiming_team_id'])

        challenge = None
        if d.get('challenge_id'):
            challenge = get_object_or_404(Challenge, pk=d['challenge_id'])

        match_report = None
        if d.get('match_report_id'):
            from apps.competition.models import MatchReport
            match_report = get_object_or_404(MatchReport, pk=d['match_report_id'])

        try:
            claim = BountyService.submit_claim(
                bounty_id=bounty_id,
                claimed_by=request.user,
                claiming_team=claiming_team,
                evidence_url=d.get('evidence_url', ''),
                evidence_notes=d.get('evidence_notes', ''),
                challenge=challenge,
                match_report=match_report,
            )
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {'detail': 'Claim submitted.', 'claim_id': str(claim.pk)},
            status=status.HTTP_201_CREATED,
        )


class TeamBountiesView(APIView):
    """GET — List bounties issued by a team."""

    permission_classes = [AllowAny]

    def get(self, request, team_slug):
        team = get_object_or_404(Team, slug=team_slug)
        bounties = BountyService.get_team_bounties(team, limit=20)
        serializer = BountyListSerializer(bounties, many=True)
        return Response(serializer.data)
