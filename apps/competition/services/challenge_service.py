"""
Challenge & Bounty service layer.

All business logic for creating, accepting, declining, completing, and settling
challenges and bounties lives here. Views and API endpoints delegate to this service.

Game-awareness:
  - FPS  (VAL, CS2, CODM, R6)  → Map pool, pick/ban, BO series
  - MOBA (DOTA, MLBB)          → Draft mode, BO series
  - BR   (PUBGM, FF)           → Kill race / placement scoring
  - SPORTS (FC26, EFB, RL)     → Direct match, 1v1 support
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, Count, Sum, Case, When, Value, IntegerField
from django.utils import timezone

from apps.competition.models import Challenge, Bounty, BountyClaim, MatchReport

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  Challenge Service
# ═══════════════════════════════════════════════════════════════════════════

class ChallengeService:
    """
    Business logic for the Challenge lifecycle.
    """

    # ── Creation ─────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def create_challenge(
        *,
        created_by,
        challenger_team,
        game,
        title,
        challenge_type='DIRECT',
        challenged_team=None,
        best_of=1,
        game_config=None,
        platform='',
        server_region='',
        prize_type='NONE',
        prize_amount=0,
        prize_description='',
        description='',
        scheduled_at=None,
        expires_at=None,
        is_public=True,
    ):
        """
        Create and issue a new challenge.

        Raises:
            PermissionDenied: If user lacks authority on challenger_team.
            ValidationError: If parameters are invalid.
        """
        # Validate team authority
        ChallengeService._verify_team_authority(created_by, challenger_team)

        # Cannot challenge yourself
        if challenged_team and challenger_team.pk == challenged_team.pk:
            raise ValidationError("A team cannot challenge itself.")

        # Both teams must play the same game
        if challenged_team:
            # Soft check — we don't enforce roster game lock at this stage
            pass

        # Validate game_config or apply defaults
        if not game_config:
            challenge_obj = Challenge(game=game)
            game_config = challenge_obj.get_default_format()

        # Default expiration: 72 hours for direct, 7 days for open
        if not expires_at:
            if challenge_type == 'OPEN':
                expires_at = timezone.now() + timedelta(days=7)
            else:
                expires_at = timezone.now() + timedelta(hours=72)

        challenge = Challenge.objects.create(
            challenger_team=challenger_team,
            challenged_team=challenged_team,
            game=game,
            title=title,
            description=description,
            challenge_type=challenge_type,
            status='OPEN',
            best_of=best_of,
            game_config=game_config,
            platform=platform,
            server_region=server_region,
            prize_type=prize_type,
            prize_amount=Decimal(str(prize_amount)),
            prize_description=prize_description,
            scheduled_at=scheduled_at,
            expires_at=expires_at,
            is_public=is_public,
            created_by=created_by,
        )

        logger.info(
            "Challenge created: %s by %s (team=%s, game=%s, type=%s)",
            challenge.reference_code, created_by.username,
            challenger_team.name, game.short_code, challenge_type,
        )
        return challenge

    # ── Accept / Decline / Cancel ────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def accept_challenge(*, challenge_id, accepted_by, accepting_team=None):
        """
        Accept a challenge on behalf of a team.
        
        For DIRECT challenges, accepting_team is the challenged_team.
        For OPEN challenges, accepting_team must be provided.
        """
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status != 'OPEN':
            raise ValidationError(f"Challenge is {challenge.get_status_display()}, not open for acceptance.")

        if challenge.is_expired:
            challenge.status = 'EXPIRED'
            challenge.save(update_fields=['status', 'updated_at'])
            raise ValidationError("This challenge has expired.")

        # Determine accepting team
        if challenge.challenge_type == 'DIRECT' or challenge.challenge_type == 'RANKED':
            accepting_team = challenge.challenged_team
        elif accepting_team is None:
            raise ValidationError("Must specify accepting_team for open challenges.")

        # Verify authority
        ChallengeService._verify_team_authority(accepted_by, accepting_team)

        # Cannot accept your own challenge
        if accepting_team.pk == challenge.challenger_team_id:
            raise ValidationError("Cannot accept your own challenge.")

        # For open challenges, set the challenged_team
        if challenge.challenged_team is None:
            challenge.challenged_team = accepting_team

        challenge.status = 'ACCEPTED'
        challenge.accepted_by = accepted_by
        challenge.accepted_at = timezone.now()
        challenge.save(update_fields=[
            'status', 'challenged_team', 'accepted_by', 'accepted_at', 'updated_at'
        ])

        logger.info(
            "Challenge accepted: %s by %s (team=%s)",
            challenge.reference_code, accepted_by.username, accepting_team.name,
        )
        return challenge

    @staticmethod
    @transaction.atomic
    def decline_challenge(*, challenge_id, declined_by):
        """Decline a challenge."""
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status != 'OPEN':
            raise ValidationError("Challenge is not open.")

        ChallengeService._verify_team_authority(declined_by, challenge.challenged_team)

        challenge.status = 'DECLINED'
        challenge.save(update_fields=['status', 'updated_at'])

        logger.info("Challenge declined: %s by %s", challenge.reference_code, declined_by.username)
        return challenge

    @staticmethod
    @transaction.atomic
    def cancel_challenge(*, challenge_id, cancelled_by):
        """Cancel a challenge (only by issuer, before acceptance)."""
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status not in ('OPEN',):
            raise ValidationError("Only open challenges can be cancelled.")

        ChallengeService._verify_team_authority(cancelled_by, challenge.challenger_team)

        challenge.status = 'CANCELLED'
        challenge.save(update_fields=['status', 'updated_at'])

        logger.info("Challenge cancelled: %s by %s", challenge.reference_code, cancelled_by.username)
        return challenge

    # ── Schedule ─────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def schedule_challenge(*, challenge_id, scheduled_at, scheduled_by):
        """Set a scheduled date/time for an accepted challenge."""
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status != 'ACCEPTED':
            raise ValidationError("Only accepted challenges can be scheduled.")

        # Either team can propose a schedule
        is_challenger = ChallengeService._has_team_authority(scheduled_by, challenge.challenger_team)
        is_challenged = ChallengeService._has_team_authority(scheduled_by, challenge.challenged_team)
        if not (is_challenger or is_challenged):
            raise PermissionDenied("You are not part of this challenge.")

        if scheduled_at <= timezone.now():
            raise ValidationError("Scheduled time must be in the future.")

        challenge.scheduled_at = scheduled_at
        challenge.status = 'SCHEDULED'
        challenge.save(update_fields=['status', 'scheduled_at', 'updated_at'])

        logger.info("Challenge scheduled: %s at %s", challenge.reference_code, scheduled_at)
        return challenge

    # ── Complete / Submit Result ──────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def submit_result(
        *,
        challenge_id,
        submitted_by,
        result,
        score_details=None,
        evidence_url='',
    ):
        """
        Submit the result of a completed challenge.
        
        Creates a MatchReport linked to this challenge for ranking integration.
        """
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status not in ('ACCEPTED', 'SCHEDULED', 'IN_PROGRESS'):
            raise ValidationError(f"Cannot submit result for {challenge.get_status_display()} challenge.")

        # Verify participant
        is_challenger = ChallengeService._has_team_authority(submitted_by, challenge.challenger_team)
        is_challenged = ChallengeService._has_team_authority(submitted_by, challenge.challenged_team)
        if not (is_challenger or is_challenged):
            raise PermissionDenied("You are not part of this challenge.")

        # Map challenge result to MatchReport result
        mr_result_map = {
            'CHALLENGER_WIN': 'WIN',
            'CHALLENGED_WIN': 'LOSS',
            'DRAW': 'DRAW',
        }
        mr_result = mr_result_map.get(result)
        if not mr_result:
            raise ValidationError(f"Invalid result: {result}")

        # Create linked MatchReport
        match_report = MatchReport.objects.create(
            game_id=challenge.game.short_code,
            match_type='CHALLENGE',
            team1=challenge.challenger_team,
            team2=challenge.challenged_team,
            result=mr_result,
            evidence_url=evidence_url,
            evidence_notes=f"Challenge {challenge.reference_code}",
            submitted_by=submitted_by,
            played_at=timezone.now(),
        )

        challenge.result = result
        challenge.score_details = score_details or {}
        challenge.evidence_url = evidence_url
        challenge.match_report = match_report
        challenge.status = 'COMPLETED'
        challenge.completed_at = timezone.now()
        challenge.save(update_fields=[
            'result', 'score_details', 'evidence_url', 'match_report',
            'status', 'completed_at', 'updated_at',
        ])

        logger.info(
            "Challenge completed: %s result=%s (reported by %s)",
            challenge.reference_code, result, submitted_by.username,
        )
        return challenge

    # ── Settle (distribute rewards) ──────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def settle_challenge(*, challenge_id, settled_by=None):
        """
        Settle a completed challenge — mark as settled, distribute prizes.
        
        Can be called automatically after verification, or manually by admin.
        """
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status != 'COMPLETED':
            raise ValidationError("Only completed challenges can be settled.")

        challenge.status = 'SETTLED'
        challenge.settled_at = timezone.now()
        challenge.resolved_by = settled_by
        challenge.save(update_fields=['status', 'settled_at', 'resolved_by', 'updated_at'])

        # TODO: Integrate with economy app for Crown Points distribution
        # if challenge.prize_type == 'CP' and challenge.winner:
        #     EconomyService.award_crown_points(challenge.winner, challenge.prize_amount)

        logger.info("Challenge settled: %s", challenge.reference_code)
        return challenge

    # ── Dispute ──────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def dispute_challenge(*, challenge_id, disputed_by, reason=''):
        """Dispute a completed challenge result."""
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status != 'COMPLETED':
            raise ValidationError("Only completed challenges can be disputed.")

        is_challenger = ChallengeService._has_team_authority(disputed_by, challenge.challenger_team)
        is_challenged = ChallengeService._has_team_authority(disputed_by, challenge.challenged_team)
        if not (is_challenger or is_challenged):
            raise PermissionDenied("You are not part of this challenge.")

        challenge.status = 'DISPUTED'
        challenge.save(update_fields=['status', 'updated_at'])

        logger.info("Challenge disputed: %s by %s", challenge.reference_code, disputed_by.username)
        return challenge

    # ── Queries ──────────────────────────────────────────────────────────

    @staticmethod
    def get_team_challenges(team, status_filter=None, limit=10):
        """Get challenges involving a team (issued or received)."""
        qs = Challenge.objects.filter(
            Q(challenger_team=team) | Q(challenged_team=team)
        ).select_related('challenger_team', 'challenged_team', 'game')

        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs[:limit]

    @staticmethod
    def get_open_challenges(game=None, limit=20):
        """Get all open challenges available for acceptance."""
        qs = Challenge.objects.filter(
            status='OPEN',
            is_public=True,
        ).select_related('challenger_team', 'challenged_team', 'game')

        if game:
            qs = qs.filter(game=game)

        # Exclude expired
        qs = qs.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )

        return qs[:limit]

    @staticmethod
    def get_challenge_stats(team):
        """
        Get challenge win/loss/earnings stats for a team.
        
        Returns dict: {wins, losses, draws, total_earned, win_rate}
        """
        challenges = Challenge.objects.filter(
            Q(challenger_team=team) | Q(challenged_team=team),
            status__in=['COMPLETED', 'SETTLED'],
        )

        wins = challenges.filter(
            Q(challenger_team=team, result='CHALLENGER_WIN') |
            Q(challenged_team=team, result='CHALLENGED_WIN')
        ).count()

        losses = challenges.filter(
            Q(challenger_team=team, result='CHALLENGED_WIN') |
            Q(challenged_team=team, result='CHALLENGER_WIN')
        ).count()

        draws = challenges.filter(result='DRAW').count()

        total = wins + losses + draws
        win_rate = round((wins / total * 100), 1) if total > 0 else 0.0

        # Calculate earnings (only CP/USD prizes where this team won)
        earned = challenges.filter(
            Q(challenger_team=team, result='CHALLENGER_WIN') |
            Q(challenged_team=team, result='CHALLENGED_WIN'),
            prize_type__in=['CP', 'USD'],
        ).aggregate(total=Sum('prize_amount'))['total'] or Decimal('0')

        return {
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'total': total,
            'win_rate': win_rate,
            'total_earned': earned,
        }

    # ── Expiry (called by periodic task) ─────────────────────────────────

    @staticmethod
    def expire_stale_challenges():
        """
        Bulk-expire challenges past their deadline.
        Called by Celery beat or management command.
        """
        expired = Challenge.objects.filter(
            status='OPEN',
            expires_at__lt=timezone.now(),
        ).update(status='EXPIRED', updated_at=timezone.now())

        if expired:
            logger.info("Expired %d stale challenges", expired)
        return expired

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _verify_team_authority(user, team):
        """Verify user has OWNER or MANAGER role on team."""
        if team is None:
            raise ValidationError("Team is required.")
        if not ChallengeService._has_team_authority(user, team):
            raise PermissionDenied(
                f"You do not have authority to act for {team.name}."
            )

    @staticmethod
    def _has_team_authority(user, team):
        """Check if user has OWNER or MANAGER role on team."""
        if team is None:
            return False
        return team.vnext_memberships.filter(
            user=user,
            status='ACTIVE',
            role__in=['OWNER', 'MANAGER', 'CAPTAIN'],
        ).exists()


# ═══════════════════════════════════════════════════════════════════════════
#  Bounty Service
# ═══════════════════════════════════════════════════════════════════════════

class BountyService:
    """
    Business logic for the Bounty lifecycle.
    """

    @staticmethod
    @transaction.atomic
    def create_bounty(
        *,
        created_by,
        issuer_team,
        game,
        title,
        bounty_type='BEAT_US',
        description='',
        criteria=None,
        reward_type='CP',
        reward_amount=0,
        reward_description='',
        max_claims=1,
        expires_at=None,
        is_public=True,
    ):
        """Create a new bounty."""
        ChallengeService._verify_team_authority(created_by, issuer_team)

        if not criteria:
            criteria = {}

        if not expires_at:
            expires_at = timezone.now() + timedelta(days=30)

        bounty = Bounty.objects.create(
            issuer_team=issuer_team,
            game=game,
            title=title,
            description=description,
            bounty_type=bounty_type,
            criteria=criteria,
            reward_type=reward_type,
            reward_amount=Decimal(str(reward_amount)),
            reward_description=reward_description,
            max_claims=max_claims,
            expires_at=expires_at,
            is_public=is_public,
            created_by=created_by,
        )

        logger.info(
            "Bounty created: %s by %s (team=%s, game=%s)",
            bounty.reference_code, created_by.username,
            issuer_team.name, game.short_code,
        )
        return bounty

    @staticmethod
    @transaction.atomic
    def submit_claim(
        *,
        bounty_id,
        claimed_by,
        claiming_team,
        evidence_url='',
        evidence_notes='',
        challenge=None,
        match_report=None,
    ):
        """Submit a claim against a bounty."""
        bounty = Bounty.objects.select_for_update().get(pk=bounty_id)

        if not bounty.is_claimable:
            raise ValidationError("This bounty is not claimable.")

        ChallengeService._verify_team_authority(claimed_by, claiming_team)

        # Cannot claim your own bounty
        if claiming_team.pk == bounty.issuer_team_id:
            raise ValidationError("Cannot claim your own bounty.")

        # Check existing claim
        existing = BountyClaim.objects.filter(
            bounty=bounty,
            claiming_team=claiming_team,
            status__in=['PENDING', 'VERIFIED'],
        ).exists()
        if existing:
            raise ValidationError("Your team already has a pending or verified claim.")

        claim = BountyClaim.objects.create(
            bounty=bounty,
            claiming_team=claiming_team,
            evidence_url=evidence_url,
            evidence_notes=evidence_notes,
            challenge=challenge,
            match_report=match_report,
            claimed_by=claimed_by,
        )

        logger.info(
            "Bounty claim: %s claimed by %s (team=%s)",
            bounty.reference_code, claimed_by.username, claiming_team.name,
        )
        return claim

    @staticmethod
    @transaction.atomic
    def verify_claim(*, claim_id, verified_by, approved=True, notes=''):
        """Verify or reject a bounty claim."""
        claim = BountyClaim.objects.select_for_update().select_related('bounty').get(pk=claim_id)

        if claim.status != 'PENDING':
            raise ValidationError("Claim is not pending.")

        if approved:
            claim.status = 'VERIFIED'
            claim.verified_at = timezone.now()
            claim.verified_by = verified_by

            # Update bounty claim count
            claim.bounty.claim_count += 1
            if claim.bounty.claim_count >= claim.bounty.max_claims:
                claim.bounty.status = 'CLAIMED'
            claim.bounty.save(update_fields=['claim_count', 'status', 'updated_at'])
        else:
            claim.status = 'REJECTED'

        claim.admin_notes = notes
        claim.save(update_fields=['status', 'verified_at', 'verified_by', 'admin_notes'])

        logger.info(
            "Bounty claim %s: %s (by %s)",
            'verified' if approved else 'rejected',
            claim.bounty.reference_code, verified_by.username,
        )
        return claim

    @staticmethod
    def get_team_bounties(team, status_filter=None, limit=10):
        """Get bounties issued by a team."""
        qs = Bounty.objects.filter(
            issuer_team=team
        ).select_related('game')

        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs[:limit]

    @staticmethod
    def get_active_bounties(game=None, limit=20):
        """Get all claimable bounties."""
        qs = Bounty.objects.filter(
            status='ACTIVE',
            is_public=True,
        ).select_related('issuer_team', 'game').filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )

        if game:
            qs = qs.filter(game=game)

        return qs[:limit]

    @staticmethod
    def expire_stale_bounties():
        """Bulk-expire bounties past their deadline."""
        expired = Bounty.objects.filter(
            status='ACTIVE',
            expires_at__lt=timezone.now(),
        ).update(status='EXPIRED', updated_at=timezone.now())

        if expired:
            logger.info("Expired %d stale bounties", expired)
        return expired
