"""
Service layer for canonical Team HQ training operations.

Training operations are intentionally separate from competitive reward systems:
no DeltaCoin locking, escrow, settlement, or payout logic belongs here.
"""

from datetime import timedelta
import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.organizations.choices import MembershipRole, MembershipStatus
from apps.organizations.models import Team, TeamMembership
from apps.organizations.models.training import (
    PracticeSession,
    ScrimBooking,
    ScrimRequest,
    TrainingVisibility,
    TryoutApplication,
    TryoutSession,
    VodReview,
)
from apps.organizations.services.team_authority import (
    can_access_team_hq,
    can_manage_training,
)

logger = logging.getLogger(__name__)


class TeamTrainingService:
    """Business logic for Team HQ training workflows."""

    @staticmethod
    def has_team_ops_authority(user, team) -> bool:
        return can_manage_training(user, team)

    @staticmethod
    def verify_team_ops_authority(user, team, action="manage team training"):
        if not TeamTrainingService.has_team_ops_authority(user, team):
            raise PermissionDenied(
                f"Only the team owner, manager, or designated captain can {action}."
            )

    @staticmethod
    def user_can_view_team_ops(user, team) -> bool:
        return can_access_team_hq(user, team)

    @staticmethod
    def default_game_for_team(team):
        try:
            from apps.games.models import Game

            return Game.objects.filter(pk=team.game_id).first()
        except Exception:
            return None

    @staticmethod
    @transaction.atomic
    def create_scrim_request(
        *,
        team,
        actor,
        scheduled_at,
        title="",
        format=ScrimRequest.Format.BO3,
        skill_level="",
        server_region="",
        visibility=TrainingVisibility.PUBLIC,
        notes="",
        game=None,
    ):
        TeamTrainingService.verify_team_ops_authority(actor, team, "post scrim requests")
        if scheduled_at <= timezone.now():
            raise ValidationError("Scrim time must be in the future.")

        return ScrimRequest.objects.create(
            requesting_team=team,
            accepted_team=None,
            game=game or TeamTrainingService.default_game_for_team(team),
            created_by=actor,
            title=(title or f"{team.name} Scrim")[:120],
            format=format if format in ScrimRequest.Format.values else ScrimRequest.Format.BO3,
            skill_level=(skill_level or "")[:80],
            server_region=(server_region or "")[:80],
            scheduled_at=scheduled_at,
            visibility=visibility if visibility in TrainingVisibility.values else TrainingVisibility.PUBLIC,
            notes=(notes or "")[:1200],
        )

    @staticmethod
    @transaction.atomic
    def accept_scrim_request(*, scrim_request, accepting_team, actor, room_details=""):
        scrim_request = ScrimRequest.objects.select_for_update().select_related(
            "requesting_team", "accepted_team", "game"
        ).get(pk=scrim_request.pk)

        TeamTrainingService.verify_team_ops_authority(actor, accepting_team, "accept scrim requests")
        if scrim_request.status != ScrimRequest.Status.OPEN:
            raise ValidationError("This scrim request is not open.")
        if scrim_request.requesting_team_id == accepting_team.pk:
            raise ValidationError("A team cannot accept its own scrim request.")
        if scrim_request.game_id and accepting_team.game_id and scrim_request.game_id != accepting_team.game_id:
            raise ValidationError("Teams must belong to the same game to book this scrim.")

        scrim_request.accepted_team = accepting_team
        scrim_request.status = ScrimRequest.Status.ACCEPTED
        scrim_request.save(update_fields=["accepted_team", "status", "updated_at"])

        booking = ScrimBooking.objects.create(
            scrim_request=scrim_request,
            requesting_team=scrim_request.requesting_team,
            accepted_team=accepting_team,
            accepted_by=actor,
            scheduled_at=scrim_request.scheduled_at,
            room_details=(room_details or "")[:1000],
        )

        try:
            match = TeamTrainingService.spawn_scrim_match_room(booking, actor=actor)
            if match:
                booking.match = match
                booking.save(update_fields=["match", "updated_at"])
        except Exception:
            logger.exception(
                "Training scrim Match Room spawn failed for booking %s. Booking kept without match room.",
                booking.pk,
            )
        return booking

    @staticmethod
    def spawn_scrim_match_room(booking, *, actor=None):
        """Create a private synthetic tournament match room for an accepted scrim."""
        if booking.match_id:
            return booking.match
        if not booking.requesting_team_id or not booking.accepted_team_id:
            return None

        from apps.tournaments.models import Match, Tournament

        game = booking.scrim_request.game or TeamTrainingService.default_game_for_team(
            booking.requesting_team
        )
        if not game:
            return None

        organizer = actor or booking.accepted_by or booking.scrim_request.created_by
        if not organizer:
            return None

        now = timezone.now()
        slug_base = slugify(f"training-scrim-{booking.scrim_request_id}") or f"training-scrim-{booking.pk}"
        tournament, _ = Tournament.objects.get_or_create(
            slug=slug_base,
            defaults={
                "name": f"Scrim - {booking.requesting_team.name} vs {booking.accepted_team.name}",
                "description": "Private Team HQ scrim match room. No reward, escrow, or settlement.",
                "organizer": organizer,
                "game": game,
                "format": Tournament.SINGLE_ELIM,
                "participation_type": Tournament.TEAM,
                "platform": Tournament.PC,
                "mode": Tournament.ONLINE,
                "max_participants": 2,
                "min_participants": 2,
                "registration_start": now,
                "registration_end": now,
                "tournament_start": booking.scheduled_at or now + timedelta(hours=1),
                "is_official": False,
                "is_featured": False,
                "has_entry_fee": False,
            },
        )

        match, _ = Match.objects.get_or_create(
            tournament=tournament,
            bracket=None,
            round_number=1,
            match_number=1,
            defaults={
                "participant1_id": booking.requesting_team_id,
                "participant1_name": booking.requesting_team.name,
                "participant2_id": booking.accepted_team_id,
                "participant2_name": booking.accepted_team.name,
                "state": Match.SCHEDULED,
                "scheduled_time": booking.scheduled_at,
                "best_of": _best_of_from_format(booking.scrim_request.format),
                "lobby_info": {
                    "kind": "training_scrim",
                    "scrim_request_id": booking.scrim_request_id,
                    "scrim_booking_id": booking.pk,
                    "no_reward": True,
                },
            },
        )
        return match

    @staticmethod
    @transaction.atomic
    def apply_for_tryout(
        *,
        team,
        applicant,
        ign="",
        preferred_role="",
        rank_tier="",
        availability="",
        profile_links=None,
        notes="",
        game=None,
    ):
        if not applicant or not applicant.is_authenticated:
            raise PermissionDenied("Login required to apply for a tryout.")
        if team.vnext_memberships.filter(user=applicant, status=MembershipStatus.ACTIVE).exists():
            raise ValidationError("You are already a member of this team.")
        if TryoutApplication.objects.filter(
            team=team,
            applicant=applicant,
            status__in=[
                TryoutApplication.Status.PENDING,
                TryoutApplication.Status.REVIEWING,
                TryoutApplication.Status.INVITED,
                TryoutApplication.Status.SCHEDULED,
                TryoutApplication.Status.OBSERVATION,
            ],
        ).exists():
            raise ValidationError("There is already an active tryout application for this player.")

        return TryoutApplication.objects.create(
            team=team,
            applicant=applicant,
            game=game or TeamTrainingService.default_game_for_team(team),
            ign=(ign or "")[:100],
            preferred_role=(preferred_role or "")[:80],
            rank_tier=(rank_tier or "")[:80],
            availability=(availability or "")[:240],
            profile_links=_clean_links(profile_links),
            notes=(notes or "")[:1200],
        )

    @staticmethod
    @transaction.atomic
    def invite_for_tryout(
        *,
        team,
        applicant,
        actor,
        preferred_role="",
        notes="",
        game=None,
    ):
        TeamTrainingService.verify_team_ops_authority(actor, team, "invite players to tryouts")
        if team.vnext_memberships.filter(user=applicant, status=MembershipStatus.ACTIVE).exists():
            raise ValidationError("This player is already a member of the team.")
        if TryoutApplication.objects.filter(
            team=team,
            applicant=applicant,
            status__in=[
                TryoutApplication.Status.PENDING,
                TryoutApplication.Status.REVIEWING,
                TryoutApplication.Status.INVITED,
                TryoutApplication.Status.SCHEDULED,
                TryoutApplication.Status.OBSERVATION,
            ],
        ).exists():
            raise ValidationError("There is already an active tryout application for this player.")
        return TryoutApplication.objects.create(
            team=team,
            applicant=applicant,
            invited_by=actor,
            game=game or TeamTrainingService.default_game_for_team(team),
            preferred_role=(preferred_role or "")[:80],
            notes=(notes or "")[:1200],
            status=TryoutApplication.Status.INVITED,
        )

    @staticmethod
    @transaction.atomic
    def review_tryout_application(*, application, actor, status, review_notes=""):
        application = TryoutApplication.objects.select_for_update().select_related("team").get(
            pk=application.pk
        )
        TeamTrainingService.verify_team_ops_authority(actor, application.team, "review tryout applications")
        if status not in TryoutApplication.Status.values:
            raise ValidationError("Invalid tryout status.")
        if status == TryoutApplication.Status.WITHDRAWN:
            raise ValidationError("Managers cannot withdraw an applicant's tryout.")

        application.status = status
        application.review_notes = (review_notes or application.review_notes or "")[:1600]
        application.reviewed_by = actor
        application.save(update_fields=["status", "review_notes", "reviewed_by", "updated_at"])
        return application

    @staticmethod
    @transaction.atomic
    def schedule_tryout_session(
        *,
        application,
        actor,
        scheduled_at,
        format="",
        room_details="",
    ):
        application = TryoutApplication.objects.select_for_update().select_related("team", "applicant").get(
            pk=application.pk
        )
        TeamTrainingService.verify_team_ops_authority(actor, application.team, "schedule tryouts")
        if scheduled_at <= timezone.now():
            raise ValidationError("Tryout time must be in the future.")

        session = TryoutSession.objects.create(
            application=application,
            team=application.team,
            applicant=application.applicant,
            scheduled_by=actor,
            scheduled_at=scheduled_at,
            format=(format or "")[:80],
            room_details=(room_details or "")[:1000],
        )
        application.status = TryoutApplication.Status.SCHEDULED
        application.save(update_fields=["status", "updated_at"])
        try:
            from apps.notifications.services import notify

            notify(
                [application.applicant],
                event="tryout.scheduled",
                title=f"Tryout scheduled with {application.team.name}",
                body=f"Your tryout is scheduled for {timezone.localtime(scheduled_at).strftime('%b %d, %I:%M %p')}.",
                url=f"/teams/{application.team.slug}/",
                category="team",
                fingerprint=f"tryout-scheduled:{session.pk}",
            )
        except Exception:
            logger.exception("Failed to notify applicant about tryout session %s", session.pk)
        return session

    @staticmethod
    @transaction.atomic
    def move_tryout_to_join_pipeline(*, application, actor, notes=""):
        """Create or link a join-pipeline offer for a strong tryout.

        This does not create membership. The existing TeamJoinRequest offer/sign
        flow remains the roster source of truth.
        """
        application = (
            TryoutApplication.objects.select_for_update()
            .select_related("team", "applicant", "join_request")
            .get(pk=application.pk)
        )
        team = application.team
        TeamTrainingService.verify_team_ops_authority(actor, team, "send join offers")

        if team.vnext_memberships.filter(user=application.applicant, status=MembershipStatus.ACTIVE).exists():
            raise ValidationError("This player is already an active team member.")

        from apps.organizations.models.join_request import TeamJoinRequest

        active_statuses = [
            TeamJoinRequest.Status.PENDING,
            TeamJoinRequest.Status.TRYOUT_SCHEDULED,
            TeamJoinRequest.Status.TRYOUT_COMPLETED,
            TeamJoinRequest.Status.OFFER_SENT,
        ]
        join_request = application.join_request
        if join_request and join_request.status not in active_statuses:
            join_request = None
        if not join_request:
            join_request = (
                TeamJoinRequest.objects.select_for_update()
                .filter(team=team, user=application.applicant, status__in=active_statuses)
                .order_by("-created_at")
                .first()
            )

        offer_note = f"Moved from TryoutApplication #{application.pk}."
        if notes:
            offer_note = f"{offer_note} {notes[:900]}"

        if join_request:
            join_request.status = TeamJoinRequest.Status.OFFER_SENT
            if application.preferred_role and not join_request.applied_position:
                join_request.applied_position = application.preferred_role[:60]
            join_request.tryout_notes = offer_note[:1000]
            join_request.reviewed_by = actor
            join_request.reviewed_at = timezone.now()
            join_request.save(update_fields=[
                "status",
                "applied_position",
                "tryout_notes",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ])
        else:
            join_request = TeamJoinRequest.objects.create(
                team=team,
                user=application.applicant,
                message="Created from Team HQ tryout evaluation.",
                status=TeamJoinRequest.Status.OFFER_SENT,
                applied_position=(application.preferred_role or "")[:60],
                tryout_notes=offer_note[:1000],
                reviewed_by=actor,
                reviewed_at=timezone.now(),
            )

        application.join_request = join_request
        application.status = TryoutApplication.Status.ACCEPTED
        application.reviewed_by = actor
        if notes:
            application.review_notes = notes[:1600]
        application.save(update_fields=["join_request", "status", "reviewed_by", "review_notes", "updated_at"])

        try:
            from apps.notifications.models import Notification

            Notification.objects.create(
                recipient=application.applicant,
                type=Notification.Type.JOIN_REQUEST_ACCEPTED,
                title=f"Join offer from {team.name}",
                body=f"{team.name} moved your tryout into the roster offer pipeline.",
                url=f"/teams/{team.slug}/",
                action_label="View Team",
                action_url=f"/teams/{team.slug}/",
                category="team",
                action_object_id=join_request.pk,
                action_type="join_request",
            )
        except Exception:
            logger.exception("Failed to notify tryout applicant about join offer")

        return join_request, application

    @staticmethod
    @transaction.atomic
    def create_practice_session(
        *,
        team,
        actor,
        title,
        scheduled_at,
        duration_minutes=60,
        session_type="PRACTICE",
        focus="",
        goals="",
        participant_ids=None,
        game=None,
    ):
        TeamTrainingService.verify_team_ops_authority(actor, team, "schedule practice sessions")
        if scheduled_at <= timezone.now():
            raise ValidationError("Practice time must be in the future.")

        session = PracticeSession.objects.create(
            team=team,
            game=game or TeamTrainingService.default_game_for_team(team),
            created_by=actor,
            title=(title or "Practice Session")[:140],
            session_type=(session_type or "PRACTICE")[:40],
            scheduled_at=scheduled_at,
            duration_minutes=max(15, min(int(duration_minutes or 60), 480)),
            focus=(focus or "")[:160],
            goals=(goals or "")[:1200],
        )
        if participant_ids:
            allowed_ids = list(
                TeamMembership.objects.filter(
                    team=team,
                    status=MembershipStatus.ACTIVE,
                    user_id__in=participant_ids,
                ).values_list("user_id", flat=True)
            )
            session.participants.set(allowed_ids)
        return session

    @staticmethod
    @transaction.atomic
    def create_vod_review(
        *,
        team,
        actor,
        title,
        external_url,
        category="analysis",
        notes="",
        visibility=TrainingVisibility.TEAM_ONLY,
        assigned_player_ids=None,
        linked_match=None,
    ):
        TeamTrainingService.verify_team_ops_authority(actor, team, "create VOD reviews")
        review = VodReview.objects.create(
            team=team,
            reviewer=actor,
            title=(title or "VOD Review")[:160],
            external_url=(external_url or "")[:500],
            category=(category or "analysis")[:40],
            notes=(notes or "")[:2400],
            visibility=visibility if visibility in TrainingVisibility.values else TrainingVisibility.TEAM_ONLY,
            linked_match=linked_match,
        )
        if assigned_player_ids:
            allowed_ids = list(
                TeamMembership.objects.filter(
                    team=team,
                    status=MembershipStatus.ACTIVE,
                    user_id__in=assigned_player_ids,
                ).values_list("user_id", flat=True)
            )
            review.assigned_players.set(allowed_ids)
        return review


def models_q_ops_authority():
    from django.db.models import Q

    return Q(role__in=[MembershipRole.OWNER, MembershipRole.MANAGER]) | Q(
        is_tournament_captain=True
    )


def _best_of_from_format(format_value):
    return {
        ScrimRequest.Format.BO1: 1,
        ScrimRequest.Format.BO3: 3,
        ScrimRequest.Format.BO5: 5,
    }.get(format_value, 1)


def _clean_links(raw_links):
    if not raw_links:
        return []
    if isinstance(raw_links, str):
        raw_links = [line.strip() for line in raw_links.splitlines()]
    if not isinstance(raw_links, (list, tuple)):
        return []
    return [str(link).strip()[:300] for link in raw_links if str(link).strip()][:5]


def match_room_url(match):
    if not match or not match.pk or not getattr(match, "tournament_id", None):
        return None
    return reverse(
        "tournaments:match_room",
        kwargs={"slug": match.tournament.slug, "match_id": match.pk},
    )
