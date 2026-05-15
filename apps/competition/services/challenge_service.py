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

from apps.competition.models import (
    Bounty,
    BountyClaim,
    Challenge,
    ChallengeResultSubmission,
    MatchReport,
)
from apps.economy import escrow_service
from apps.economy.exceptions import InsufficientFunds
from apps.economy.models import DeltaCrownWallet

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Crown Clash escrow constants
# ─────────────────────────────────────────────────────────────────────────────

#: Anti-whale ceiling: maximum DC each side may stake on a single Crown Clash.
#: Mirrors the spirit of escrow_service.NON_API_WAGER_CAP_DC but applies to
#: every Crown Clash regardless of game-result verification mode.
CROWN_CLASH_ENTRY_FEE_CAP_DC: int = 1_000

#: Platform fee taken from the prize pot on a normal settlement.
CROWN_CLASH_PLATFORM_FEE_PCT: int = 5

#: Anti-whale ceiling for Hitlist challenger entry fees per claim.
HITLIST_CHALLENGER_ENTRY_FEE_CAP_DC: int = 1_000

#: Platform fee on Hitlist payouts (applied to "winnings" portion only).
HITLIST_PLATFORM_FEE_PCT: int = 5


def _wallet_for_user(user) -> DeltaCrownWallet:
    """Return the DeltaCrownWallet for ``user`` or raise ValidationError."""
    if user is None:
        raise ValidationError("Cannot resolve wallet: user is None.")
    profile = getattr(user, "profile", None) or getattr(user, "user_profile", None)
    if profile is None:
        raise ValidationError(
            f"User '{getattr(user, 'username', user)}' has no profile; "
            "cannot participate in a Crown Clash."
        )
    try:
        return DeltaCrownWallet.objects.get(profile=profile)
    except DeltaCrownWallet.DoesNotExist as exc:
        raise ValidationError(
            f"User '{user.username}' has no DeltaCoin wallet."
        ) from exc


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
        entry_fee_dc=0,
    ):
        """
        Create and issue a new challenge.

        When ``entry_fee_dc`` is positive, this is a Crown Clash: the
        challenger's wallet is debited that many DC and locked into escrow.
        The opponent's matching lock happens on accept.  Refunded on
        decline / cancel / expire; paid out on settle.

        Raises:
            PermissionDenied:  If user lacks authority on challenger_team.
            ValidationError:   If parameters are invalid or entry fee
                               exceeds CROWN_CLASH_ENTRY_FEE_CAP_DC.
            InsufficientFunds: If the challenger cannot cover entry_fee_dc.
        """
        # Validate team authority
        ChallengeService._verify_team_authority(
            created_by, challenger_team, action='issue a Crown Clash',
        )

        # Cannot challenge yourself
        if challenged_team and challenger_team.pk == challenged_team.pk:
            raise ValidationError("A team cannot challenge itself.")

        # Both teams must play the same game
        if challenged_team:
            # Soft check — we don't enforce roster game lock at this stage
            pass

        # Crown Clash entry-fee gate: anti-whale ceiling check
        if entry_fee_dc and entry_fee_dc > CROWN_CLASH_ENTRY_FEE_CAP_DC:
            raise ValidationError(
                f"Crown Clash entry fee {entry_fee_dc} DC exceeds the "
                f"anti-whale cap of {CROWN_CLASH_ENTRY_FEE_CAP_DC} DC per side."
            )
        if entry_fee_dc < 0:
            raise ValidationError("Entry fee cannot be negative.")

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
            entry_fee_dc=entry_fee_dc or 0,
        )

        # Crown Clash: lock the challenger's stake immediately so the offer
        # is funded.  Opponent's matching lock occurs on accept.
        if entry_fee_dc:
            wallet = _wallet_for_user(created_by)
            result = escrow_service.lock_funds(
                wallet,
                entry_fee_dc,
                reference_id=challenge.clash_ref_id('challenger'),
                actor=created_by,
                note=f"Crown Clash {challenge.reference_code} challenger stake "
                     f"(funded by {created_by.username})",
            )
            challenge.challenger_lock_txn = result.transactions[0]
            challenge.funded_by_challenger = created_by
            challenge.save(update_fields=[
                'challenger_lock_txn', 'funded_by_challenger', 'updated_at',
            ])

        logger.info(
            "Challenge created: %s by %s (team=%s, game=%s, type=%s, entry_fee=%s)",
            challenge.reference_code, created_by.username,
            challenger_team.name, game.short_code, challenge_type, entry_fee_dc,
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
        ChallengeService._verify_team_authority(
            accepted_by, accepting_team, action='accept this Crown Clash',
        )

        # Cannot accept your own challenge
        if accepting_team.pk == challenge.challenger_team_id:
            raise ValidationError("Cannot accept your own challenge.")

        # For open challenges, set the challenged_team
        if challenge.challenged_team is None:
            challenge.challenged_team = accepting_team

        # Crown Clash: opponent locks matching stake at accept time.
        # Once both sides are locked, escrow_locked = True (full pot funded).
        update_fields = [
            'status', 'challenged_team', 'accepted_by', 'accepted_at', 'updated_at'
        ]
        if challenge.entry_fee_dc:
            wallet = _wallet_for_user(accepted_by)
            result = escrow_service.lock_funds(
                wallet,
                challenge.entry_fee_dc,
                reference_id=challenge.clash_ref_id('challenged'),
                actor=accepted_by,
                note=f"Crown Clash {challenge.reference_code} challenged stake "
                     f"(funded by {accepted_by.username})",
            )
            challenge.challenged_lock_txn = result.transactions[0]
            challenge.funded_by_challenged = accepted_by
            challenge.escrow_locked = True
            update_fields += [
                'challenged_lock_txn', 'funded_by_challenged', 'escrow_locked',
            ]

        challenge.status = 'ACCEPTED'
        challenge.accepted_by = accepted_by
        challenge.accepted_at = timezone.now()
        challenge.save(update_fields=update_fields)

        # ── Spawn the Match Room (synthetic tournament-backed lobby) ────
        try:
            match = ChallengeService._spawn_clash_match_room(
                challenge, actor=accepted_by,
            )
            if match is not None:
                challenge.match = match
                challenge.save(update_fields=['match', 'updated_at'])
        except Exception:
            logger.exception(
                "Match Room spawn failed for clash %s — challenge accepted but "
                "no lobby created. Admins can re-spawn via management command.",
                challenge.reference_code,
            )

        logger.info(
            "Challenge accepted: %s by %s (team=%s, pot=%s DC, match=%s)",
            challenge.reference_code, accepted_by.username, accepting_team.name,
            challenge.prize_pot_dc, getattr(challenge.match, 'pk', None),
        )
        return challenge

    @staticmethod
    @transaction.atomic
    def decline_challenge(*, challenge_id, declined_by):
        """Decline a challenge.  Refunds the challenger's locked stake."""
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status != 'OPEN':
            raise ValidationError("Challenge is not open.")

        ChallengeService._verify_team_authority(
            declined_by, challenge.challenged_team, action='decline this Crown Clash',
        )

        ChallengeService._refund_challenger_if_locked(
            challenge, actor=declined_by, note="Challenge declined by opponent"
        )

        challenge.status = 'DECLINED'
        challenge.closure_reason = 'DECLINED_BY_OPPONENT'
        challenge.save(update_fields=['status', 'closure_reason', 'updated_at'])

        logger.info("Challenge declined: %s by %s", challenge.reference_code, declined_by.username)
        return challenge

    @staticmethod
    @transaction.atomic
    def cancel_challenge(*, challenge_id, cancelled_by):
        """Cancel a challenge (only by issuer, before acceptance)."""
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status not in ('OPEN',):
            raise ValidationError("Only open challenges can be cancelled.")

        ChallengeService._verify_team_authority(
            cancelled_by, challenge.challenger_team, action='cancel this Crown Clash',
        )

        ChallengeService._refund_challenger_if_locked(
            challenge, actor=cancelled_by, note="Challenge cancelled by issuer"
        )

        challenge.status = 'CANCELLED'
        challenge.closure_reason = 'CANCELLED_BY_ISSUER'
        challenge.save(update_fields=['status', 'closure_reason', 'updated_at'])

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

        # Either team's owner / manager / tournament-captain can propose a schedule.
        is_challenger = ChallengeService._has_team_authority(scheduled_by, challenge.challenger_team)
        is_challenged = ChallengeService._has_team_authority(scheduled_by, challenge.challenged_team)
        if not (is_challenger or is_challenged):
            raise PermissionDenied(
                "Only the team owner, manager, or designated tournament captain "
                "of either team can schedule this match."
            )

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
        submitting_team=None,
    ):
        """
        Submit or confirm a Showdown result.

        One authorized user from each team must submit the same winner and
        score. Matching submissions settle through ``settle_challenge``.
        Conflicting submissions move the challenge to DISPUTED.
        """
        challenge = (
            Challenge.objects
            .select_for_update()
            .select_related('challenger_team', 'challenged_team', 'game')
            .get(pk=challenge_id)
        )

        if challenge.status in ('SETTLED', 'DISPUTED', 'ADMIN_RESOLVED'):
            raise ValidationError(f"Challenge is already {challenge.get_status_display()}.")
        if challenge.status not in ('ACCEPTED', 'SCHEDULED', 'IN_PROGRESS', 'PENDING_CONFIRMATION', 'COMPLETED'):
            raise ValidationError(f"Cannot submit result for {challenge.get_status_display()} challenge.")

        submitting_team = ChallengeService._resolve_result_submitting_team(
            submitted_by, challenge, submitting_team=submitting_team
        )

        if result not in ('CHALLENGER_WIN', 'CHALLENGED_WIN', 'DRAW'):
            raise ValidationError(f"Invalid result: {result}")

        score_details = score_details or {}
        existing = ChallengeResultSubmission.objects.filter(
            challenge=challenge,
            team=submitting_team,
        ).first()
        if existing:
            if (
                existing.result == result
                and existing.score_details == score_details
                and (existing.evidence_url or '') == (evidence_url or '')
            ):
                return challenge
            raise ValidationError("This team has already submitted a result for this Showdown.")

        submission = ChallengeResultSubmission.objects.create(
            challenge=challenge,
            team=submitting_team,
            submitted_by=submitted_by,
            result=result,
            score_details=score_details,
            evidence_url=evidence_url or '',
        )

        submissions = list(
            ChallengeResultSubmission.objects
            .filter(challenge=challenge)
            .select_related('team', 'submitted_by')
            .order_by('created_at')
        )

        if len(submissions) < 2:
            challenge.result = result
            challenge.score_details = score_details
            challenge.evidence_url = evidence_url or ''
            challenge.status = 'PENDING_CONFIRMATION'
            challenge.save(update_fields=[
                'result', 'score_details', 'evidence_url',
                'status', 'updated_at',
            ])
            logger.info(
                "Challenge result submitted: %s result=%s team=%s by=%s",
                challenge.reference_code, result, submitting_team.name, submitted_by.username,
            )
            return challenge

        first, second = submissions[0], submissions[1]
        if first.result != second.result or first.score_details != second.score_details:
            challenge.status = 'DISPUTED'
            challenge.closure_note = (
                "Showdown result submissions did not match. "
                "The result is pending admin review."
            )
            challenge.save(update_fields=['status', 'closure_note', 'updated_at'])
            logger.info(
                "Challenge result disputed: %s first=%s second=%s",
                challenge.reference_code, first.result, second.result,
            )
            return challenge

        match_report = ChallengeService._create_confirmed_match_report(
            challenge,
            result=first.result,
            score_details=first.score_details,
            evidence_url=first.evidence_url or second.evidence_url or '',
            submitted_by=submitted_by,
        )
        challenge.result = first.result
        challenge.score_details = first.score_details
        challenge.evidence_url = first.evidence_url or second.evidence_url or ''
        challenge.match_report = match_report
        challenge.status = 'COMPLETED'
        if not challenge.completed_at:
            challenge.completed_at = timezone.now()
        challenge.save(update_fields=[
            'result', 'score_details', 'evidence_url', 'match_report',
            'status', 'completed_at', 'updated_at',
        ])

        logger.info(
            "Challenge result confirmed: %s result=%s (confirmed by %s)",
            challenge.reference_code, first.result, submitted_by.username,
        )
        return ChallengeService.settle_challenge(
            challenge_id=challenge.pk,
            settled_by=submitted_by,
        )

    # ── Settle (distribute rewards) ──────────────────────────────────────

    @staticmethod
    def _resolve_result_submitting_team(user, challenge, *, submitting_team=None):
        participant_teams = [challenge.challenger_team, challenge.challenged_team]
        participant_ids = {team.pk for team in participant_teams if team is not None}

        if submitting_team is not None:
            if submitting_team.pk not in participant_ids:
                raise ValidationError("Submitting team is not part of this Showdown.")
            ChallengeService._verify_team_authority(
                user, submitting_team, action='submit the Showdown result',
            )
            return submitting_team

        authorized = [
            team for team in participant_teams
            if team is not None and ChallengeService._has_team_authority(user, team)
        ]
        if not authorized:
            raise PermissionDenied(
                "Only the team owner, manager, or designated tournament captain "
                "of either team can submit the match result."
            )
        if len(authorized) > 1:
            raise ValidationError("submitting_team_id is required when you manage both teams.")
        return authorized[0]

    @staticmethod
    def _create_confirmed_match_report(
        challenge,
        *,
        result,
        score_details=None,
        evidence_url='',
        submitted_by=None,
    ):
        mr_result_map = {
            'CHALLENGER_WIN': 'WIN',
            'CHALLENGED_WIN': 'LOSS',
            'DRAW': 'DRAW',
        }
        mr_result = mr_result_map.get(result)
        if not mr_result:
            raise ValidationError(f"Invalid result: {result}")

        return MatchReport.objects.create(
            game_id=challenge.game.short_code,
            match_type='CHALLENGE',
            team1=challenge.challenger_team,
            team2=challenge.challenged_team,
            result=mr_result,
            evidence_url=evidence_url or '',
            evidence_notes=f"Showdown {challenge.reference_code} confirmed result",
            submitted_by=submitted_by,
            played_at=timezone.now(),
        )

    @staticmethod
    @transaction.atomic
    def settle_challenge(*, challenge_id, settled_by=None):
        """
        Settle a completed challenge — distribute the Crown Clash prize pot.

        Outcome handling (when entry_fee_dc > 0 and both sides locked):
          * CHALLENGER_WIN / FORFEIT_CHALLENGED → pay challenger's user
          * CHALLENGED_WIN / FORFEIT_CHALLENGER → pay challenged's user
          * DRAW                                 → refund both sides
          * NO_SHOW                              → refund both, BOTH_NO_SHOW

        Closure reason recorded on the challenge so the UI never has to
        guess why the lobby finished.
        """
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status != 'COMPLETED':
            raise ValidationError("Only completed challenges can be settled.")

        result = challenge.result
        update_fields = ['status', 'settled_at', 'resolved_by', 'updated_at']

        # ── Crown Clash payout/refund path ───────────────────────────
        if challenge.entry_fee_dc and challenge.escrow_locked:
            winner_user = ChallengeService._resolve_winner_user(challenge)
            if winner_user is not None:
                wallet = _wallet_for_user(winner_user)
                payout = escrow_service.payout_winner(
                    wallet,
                    challenge.prize_pot_dc,
                    platform_fee_pct=CROWN_CLASH_PLATFORM_FEE_PCT,
                    reference_id=challenge.clash_ref_id(),
                    actor=settled_by,
                    note=f"Crown Clash {challenge.reference_code} settlement",
                )
                challenge.payout_txn = payout.transactions[0]
                challenge.closure_reason = 'NORMAL'
                update_fields.append('payout_txn')
            elif result == 'NO_SHOW':
                ChallengeService._refund_both_sides(
                    challenge,
                    actor=settled_by,
                    note=f"Crown Clash {challenge.reference_code} no-show refund",
                )
                challenge.closure_reason = 'BOTH_NO_SHOW'
            else:
                # DRAW (or any other non-winning result with locked pot)
                ChallengeService._refund_both_sides(
                    challenge,
                    actor=settled_by,
                    note=f"Crown Clash {challenge.reference_code} draw refund",
                )
                challenge.closure_reason = 'NORMAL'
            update_fields.append('closure_reason')
        elif challenge.entry_fee_dc and not challenge.escrow_locked:
            # Asymmetric lock (only challenger staked).  Refund them.
            ChallengeService._refund_challenger_if_locked(
                challenge,
                actor=settled_by,
                note=f"Crown Clash {challenge.reference_code} asymmetric refund",
            )
            challenge.closure_reason = challenge.closure_reason or 'NORMAL'
            update_fields.append('closure_reason')

        challenge.status = 'SETTLED'
        challenge.settled_at = timezone.now()
        challenge.resolved_by = settled_by
        challenge.save(update_fields=update_fields)

        logger.info(
            "Challenge settled: %s (result=%s, pot=%s DC, closure=%s)",
            challenge.reference_code, result, challenge.prize_pot_dc,
            challenge.closure_reason,
        )
        return challenge

    @staticmethod
    @transaction.atomic
    def admin_settle_confirmed_showdown(*, challenge_id, resolved_by, note=''):
        """Admin/operator settlement path for an already confirmed Showdown."""
        challenge = ChallengeService.settle_challenge(
            challenge_id=challenge_id,
            settled_by=resolved_by,
        )
        if note:
            challenge.closure_note = note
            challenge.save(update_fields=['closure_note', 'updated_at'])
        ChallengeService._log_showdown_admin_action(
            'showdown.admin_settled',
            challenge,
            actor=resolved_by,
            note=note,
        )
        return challenge

    @staticmethod
    @transaction.atomic
    def admin_resolve_disputed_showdown(
        *,
        challenge_id,
        resolved_by,
        result,
        score_details=None,
        note='',
    ):
        """Resolve a disputed Showdown with an admin-selected result, then settle."""
        challenge = (
            Challenge.objects
            .select_for_update()
            .select_related('challenger_team', 'challenged_team', 'game')
            .get(pk=challenge_id)
        )

        if challenge.status != 'DISPUTED':
            raise ValidationError("Only disputed Showdowns can be resolved by this action.")
        if challenge.payout_txn_id or challenge.status == 'SETTLED':
            raise ValidationError("This Showdown has already been settled.")
        if result not in ('CHALLENGER_WIN', 'CHALLENGED_WIN', 'DRAW'):
            raise ValidationError(f"Invalid result: {result}")

        if not challenge.match_report_id:
            challenge.match_report = ChallengeService._create_confirmed_match_report(
                challenge,
                result=result,
                score_details=score_details or challenge.score_details or {},
                evidence_url=challenge.evidence_url or '',
                submitted_by=resolved_by,
            )
        challenge.result = result
        challenge.score_details = score_details or challenge.score_details or {}
        challenge.status = 'COMPLETED'
        challenge.completed_at = challenge.completed_at or timezone.now()
        challenge.resolved_by = resolved_by
        challenge.closure_reason = 'DISPUTE_RESOLVED'
        challenge.closure_note = note or f"Dispute resolved by {resolved_by.username}."
        challenge.save(update_fields=[
            'result', 'score_details', 'status', 'completed_at', 'resolved_by',
            'closure_reason', 'closure_note', 'match_report', 'updated_at',
        ])

        settled = ChallengeService.settle_challenge(
            challenge_id=challenge.pk,
            settled_by=resolved_by,
        )
        settled.closure_reason = 'DISPUTE_RESOLVED'
        settled.closure_note = challenge.closure_note
        settled.save(update_fields=['closure_reason', 'closure_note', 'updated_at'])
        ChallengeService._log_showdown_admin_action(
            'showdown.dispute_resolved',
            settled,
            actor=resolved_by,
            note=settled.closure_note,
            extra={'result': result},
        )
        return settled

    @staticmethod
    @transaction.atomic
    def admin_void_refund_showdown(*, challenge_id, resolved_by, note=''):
        """Void a Showdown and refund locked entry fees through escrow service."""
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)

        if challenge.status == 'SETTLED' or challenge.payout_txn_id:
            raise ValidationError("Settled Showdowns cannot be voided by bulk admin action.")
        if challenge.status in ('DECLINED', 'EXPIRED', 'CANCELLED', 'ADMIN_RESOLVED'):
            raise ValidationError(f"Showdown is already closed as {challenge.get_status_display()}.")

        if challenge.entry_fee_dc:
            if challenge.escrow_locked:
                ChallengeService._refund_both_sides(
                    challenge,
                    actor=resolved_by,
                    note=note or f"Admin void refund for {challenge.reference_code}",
                )
            else:
                ChallengeService._refund_challenger_if_locked(
                    challenge,
                    actor=resolved_by,
                    note=note or f"Admin void refund for {challenge.reference_code}",
                )

        challenge.status = 'ADMIN_RESOLVED'
        challenge.result = 'PENDING'
        challenge.escrow_locked = False
        challenge.resolved_by = resolved_by
        challenge.settled_at = timezone.now()
        challenge.closure_reason = 'ADMIN_VOID'
        challenge.closure_note = note or f"Voided and refunded by {resolved_by.username}."
        challenge.save(update_fields=[
            'status', 'result', 'escrow_locked', 'resolved_by', 'settled_at',
            'closure_reason', 'closure_note', 'updated_at',
        ])
        ChallengeService._log_showdown_admin_action(
            'showdown.admin_void_refund',
            challenge,
            actor=resolved_by,
            note=challenge.closure_note,
        )
        return challenge

    @staticmethod
    @transaction.atomic
    def admin_respawn_match_room(*, challenge_id, actor):
        """Respawn a missing synthetic match room if the Showdown is accepted."""
        challenge = (
            Challenge.objects
            .select_for_update()
            .select_related('challenger_team', 'challenged_team', 'game')
            .get(pk=challenge_id)
        )
        if challenge.match_id:
            return challenge.match
        if challenge.status not in ('ACCEPTED', 'SCHEDULED', 'IN_PROGRESS', 'PENDING_CONFIRMATION', 'COMPLETED'):
            raise ValidationError("Only accepted or active Showdowns can have match rooms.")
        match = ChallengeService._spawn_clash_match_room(challenge, actor=actor)
        if match is None:
            raise ValidationError("Could not create a match room for this Showdown.")
        challenge.match = match
        challenge.save(update_fields=['match', 'updated_at'])
        ChallengeService._log_showdown_admin_action(
            'showdown.match_room_respawned',
            challenge,
            actor=actor,
            extra={'match_id': match.pk},
        )
        return match

    @staticmethod
    def _log_showdown_admin_action(event_name, challenge, *, actor=None, note='', extra=None):
        """Persist a lightweight operator audit event without blocking the action."""
        try:
            from apps.common.events.models import EventLog

            EventLog.objects.create(
                name=event_name,
                payload={
                    'challenge_id': str(challenge.pk),
                    'reference_code': challenge.reference_code,
                    'status': challenge.status,
                    'result': challenge.result,
                    'note': note,
                    **(extra or {}),
                },
                occurred_at=timezone.now(),
                user_id=getattr(actor, 'pk', None),
                correlation_id=challenge.reference_code,
                metadata={'source': 'competition.admin'},
                status=EventLog.STATUS_PROCESSED,
            )
        except Exception:
            logger.exception(
                "Failed to write Showdown admin audit event %s for %s",
                event_name,
                getattr(challenge, 'reference_code', challenge),
            )

    @staticmethod
    def _resolve_winner_user(challenge):
        """Return the User whose wallet should receive the payout, or None.

        Crown Clash funds are locked from ``created_by`` (challenger side)
        and ``accepted_by`` (challenged side).  The winning user is the
        same one who funded that side.
        """
        result = challenge.result
        if result in ('CHALLENGER_WIN', 'FORFEIT_CHALLENGED'):
            return challenge.created_by
        if result in ('CHALLENGED_WIN', 'FORFEIT_CHALLENGER'):
            return challenge.accepted_by
        return None

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
            raise PermissionDenied(
                "Only the team owner, manager, or designated tournament captain "
                "of either team can raise a dispute on this match."
            )

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
        Expire OPEN challenges past their deadline.

        Walks per-row so any Crown Clash challenger lock is refunded as
        each row transitions to EXPIRED.  Each row is its own atomic block
        so a single bad row never blocks the rest.
        """
        stale_qs = Challenge.objects.filter(
            status='OPEN',
            expires_at__lt=timezone.now(),
        ).only('id', 'reference_code')

        count = 0
        for challenge_stub in stale_qs.iterator():
            try:
                with transaction.atomic():
                    challenge = (
                        Challenge.objects
                        .select_for_update()
                        .get(pk=challenge_stub.pk)
                    )
                    if challenge.status != 'OPEN':
                        continue
                    ChallengeService._refund_challenger_if_locked(
                        challenge, actor=None, note="Challenge expired before acceptance"
                    )
                    challenge.status = 'EXPIRED'
                    challenge.closure_reason = 'EXPIRED'
                    challenge.save(update_fields=['status', 'closure_reason', 'updated_at'])
                count += 1
            except Exception:
                logger.exception(
                    "expire_stale_challenges: failed on %s",
                    challenge_stub.reference_code,
                )

        if count:
            logger.info("Expired %d stale challenges", count)
        return count

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _verify_team_authority(user, team, *, action='act'):
        """Verify the user has authority to ``action`` on behalf of ``team``.

        Authority = ACTIVE membership AND (role IN OWNER/MANAGER OR
        is_tournament_captain=True).  Anything else raises PermissionDenied
        with a clear, copy-ready message for the API layer.
        """
        if team is None:
            raise ValidationError("Team is required.")
        if not ChallengeService._has_team_authority(user, team):
            raise PermissionDenied(
                f"Only the team owner, manager, or designated tournament captain "
                f"can {action} on behalf of {team.name}."
            )

    @staticmethod
    def _has_team_authority(user, team):
        """True iff user is OWNER/MANAGER or the team's tournament captain.

        Performs the check via two ORed clauses so a player who is BOTH a
        captain AND has the OWNER role still matches once.
        """
        if team is None or user is None or not getattr(user, 'is_authenticated', True):
            return False
        return team.vnext_memberships.filter(
            user=user,
            status='ACTIVE',
        ).filter(
            Q(role__in=['OWNER', 'MANAGER']) | Q(is_tournament_captain=True)
        ).exists()

    # ── Crown Clash escrow helpers ───────────────────────────────────────

    @staticmethod
    def _refund_challenger_if_locked(challenge, *, actor=None, note=""):
        """Refund the challenger's escrow lock if one exists.  Idempotent.

        Called from decline / cancel / expire paths where only the
        challenger has staked (opponent never locked).  Updates the
        challenge fields in-memory; caller is responsible for save().
        """
        if not challenge.entry_fee_dc or not challenge.challenger_lock_txn_id:
            return None
        wallet = _wallet_for_user(challenge.created_by)
        result = escrow_service.refund_funds(
            wallet,
            challenge.entry_fee_dc,
            reference_id=challenge.clash_ref_id('challenger'),
            actor=actor,
            note=note or f"Refund {challenge.reference_code} challenger stake",
        )
        return result

    @staticmethod
    def _spawn_clash_match_room(challenge, *, actor=None):
        """Create a synthetic Tournament + Match for a Crown Clash.

        Re-uses the existing tournaments.Match infrastructure (lobby_state,
        chat, dispute, phase pipeline) by binding the clash to a private,
        non-bracket Tournament that exists solely to host the match row.
        Idempotent: a clash that already has ``challenge.match`` set does
        nothing.
        """
        if challenge.match_id:
            return challenge.match

        from apps.tournaments.models import Match, Tournament

        challenger = challenge.challenger_team
        challenged = challenge.challenged_team
        if challenger is None or challenged is None:
            return None
        organizer = (
            challenge.created_by
            or challenge.accepted_by
            or actor
        )
        if organizer is None:
            return None

        now = timezone.now()
        scheduled_at = challenge.scheduled_at or (now + timedelta(hours=1))
        slug = f"showdown-{challenge.reference_code.lower()}"

        tournament, created = Tournament.objects.get_or_create(
            slug=slug,
            defaults=dict(
                name=f"Showdown - {challenger.name} vs {challenged.name}",
                description=(
                    f"Auto-generated match room host for Showdown "
                    f"{challenge.reference_code}. Hidden from public listings."
                ),
                organizer=organizer,
                game=challenge.game,
                format='SINGLE_ELIM',
                participation_type='TEAM',
                max_participants=2,
                min_participants=2,
                registration_start=now,
                registration_end=now,
                tournament_start=scheduled_at,
                is_official=False,
                is_featured=False,
            ),
        )
        if created:
            tournament.name = f"Showdown - {challenger.name} vs {challenged.name}"
            tournament.description = (
                f"Auto-generated match room host for Showdown "
                f"{challenge.reference_code}. Hidden from public listings."
            )
            tournament.save(update_fields=['name', 'description'])

        match, _ = Match.objects.get_or_create(
            tournament=tournament,
            bracket=None,
            round_number=1,
            match_number=1,
            defaults=dict(
                participant1_id=challenger.pk,
                participant1_name=challenger.name,
                participant2_id=challenged.pk,
                participant2_name=challenged.name,
                state=Match.SCHEDULED,
                scheduled_time=scheduled_at,
                lobby_info={
                    'kind': 'showdown',
                    'showdown_ref': challenge.reference_code,
                    'clash_ref': challenge.reference_code,
                    'best_of': challenge.best_of,
                    'entry_fee_dc': challenge.entry_fee_dc,
                    'prize_pot_dc': challenge.prize_pot_dc,
                },
            ),
        )
        return match

    @staticmethod
    def _spawn_hitlist_match_room(bounty, claim, *, actor=None):
        """Create a synthetic Tournament + Match for a Hitlist claim.

        Each claim gets its own match-room so multiple challengers don't
        clash inside the same lobby.  Idempotent on ``claim.match``.
        """
        if claim.match_id:
            return claim.match

        from apps.tournaments.models import Match, Tournament

        issuer = bounty.issuer_team
        challenger = claim.claiming_team
        if issuer is None or challenger is None:
            return None
        organizer = (
            bounty.created_by
            or claim.claimed_by
            or actor
        )
        if organizer is None:
            return None

        now = timezone.now()
        slug = f"bounty-{bounty.reference_code.lower()}-claim-{str(claim.pk)[:8]}"

        tournament, created = Tournament.objects.get_or_create(
            slug=slug,
            defaults=dict(
                name=f"Bounty - {challenger.name} vs {issuer.name}",
                description=(
                    f"Auto-generated match room host for Bounty claim "
                    f"{bounty.reference_code}. Hidden from public listings."
                ),
                organizer=organizer,
                game=bounty.game,
                format='SINGLE_ELIM',
                participation_type='TEAM',
                max_participants=2,
                min_participants=2,
                registration_start=now,
                registration_end=now,
                tournament_start=now + timedelta(hours=1),
                is_official=False,
                is_featured=False,
            ),
        )
        if created:
            tournament.name = f"Bounty - {challenger.name} vs {issuer.name}"
            tournament.description = (
                f"Auto-generated match room host for Bounty claim "
                f"{bounty.reference_code}. Hidden from public listings."
            )
            tournament.save(update_fields=['name', 'description'])

        match, _ = Match.objects.get_or_create(
            tournament=tournament,
            bracket=None,
            round_number=1,
            match_number=1,
            defaults=dict(
                participant1_id=issuer.pk,
                participant1_name=issuer.name,
                participant2_id=challenger.pk,
                participant2_name=challenger.name,
                state=Match.SCHEDULED,
                scheduled_time=now + timedelta(hours=1),
                lobby_info={
                    'kind': 'bounty',
                    'bounty_ref': bounty.reference_code,
                    'claim_id': str(claim.pk),
                    'reward_amount_dc': bounty.reward_amount_dc,
                    'challenger_entry_fee_dc': bounty.challenger_entry_fee_dc,
                },
            ),
        )
        return match

    @staticmethod
    def _refund_both_sides(challenge, *, actor=None, note=""):
        """Refund BOTH locked stakes — for draws, no-shows, admin voids."""
        if not challenge.entry_fee_dc:
            return
        if challenge.challenger_lock_txn_id:
            ch_wallet = _wallet_for_user(challenge.created_by)
            escrow_service.refund_funds(
                ch_wallet,
                challenge.entry_fee_dc,
                reference_id=challenge.clash_ref_id('challenger'),
                actor=actor,
                note=note or f"Refund {challenge.reference_code} challenger stake",
            )
        if challenge.challenged_lock_txn_id:
            op_wallet = _wallet_for_user(challenge.accepted_by)
            escrow_service.refund_funds(
                op_wallet,
                challenge.entry_fee_dc,
                reference_id=challenge.clash_ref_id('challenged'),
                actor=actor,
                note=note or f"Refund {challenge.reference_code} challenged stake",
            )


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
        is_hitlist=False,
        reward_amount_dc=0,
        challenger_entry_fee_dc=0,
    ):
        """Create a new bounty.

        When ``is_hitlist`` is True the issuer's ``reward_amount_dc`` is
        locked into escrow up front, and challengers will be required
        to lock ``challenger_entry_fee_dc`` per claim attempt.
        """
        ChallengeService._verify_team_authority(
            created_by, issuer_team,
            action='post a Hitlist bounty' if is_hitlist else 'post a bounty',
        )

        if not criteria:
            criteria = {}

        if not expires_at:
            expires_at = timezone.now() + timedelta(days=30)

        # Hitlist guards: anti-whale + non-zero reward + max_claims=1
        if is_hitlist:
            if reward_amount_dc <= 0:
                raise ValidationError("Hitlist bounties require a non-zero reward_amount_dc.")
            if challenger_entry_fee_dc <= 0:
                raise ValidationError("Hitlist bounties require a non-zero challenger_entry_fee_dc.")
            if challenger_entry_fee_dc > HITLIST_CHALLENGER_ENTRY_FEE_CAP_DC:
                raise ValidationError(
                    f"Hitlist challenger entry fee {challenger_entry_fee_dc} DC exceeds "
                    f"the anti-whale cap of {HITLIST_CHALLENGER_ENTRY_FEE_CAP_DC} DC."
                )
            max_claims = 1  # Hitlist reward is consumed on first verified win

        bounty = Bounty.objects.create(
            issuer_team=issuer_team,
            game=game,
            title=title,
            description=description,
            bounty_type=bounty_type,
            criteria=criteria,
            reward_type=reward_type,
            reward_amount=Decimal(str(reward_amount)),
            reward_amount_dc=reward_amount_dc or 0,
            reward_description=reward_description,
            max_claims=max_claims,
            expires_at=expires_at,
            is_public=is_public,
            created_by=created_by,
            is_hitlist=is_hitlist,
            challenger_entry_fee_dc=challenger_entry_fee_dc or 0,
        )

        # Lock the issuer's reward immediately (Hitlist only).
        if is_hitlist and reward_amount_dc > 0:
            wallet = _wallet_for_user(created_by)
            result = escrow_service.lock_funds(
                wallet,
                reward_amount_dc,
                reference_id=bounty.hitlist_ref_id('issuer'),
                actor=created_by,
                note=f"Hitlist {bounty.reference_code} issuer reward "
                     f"(funded by {created_by.username})",
            )
            bounty.issuer_lock_txn = result.transactions[0]
            bounty.funded_by = created_by
            bounty.escrow_locked = True
            bounty.save(update_fields=[
                'issuer_lock_txn', 'funded_by', 'escrow_locked', 'updated_at',
            ])

        logger.info(
            "Bounty created: %s by %s (team=%s, game=%s, hitlist=%s, reward=%s DC)",
            bounty.reference_code, created_by.username,
            issuer_team.name, game.short_code, is_hitlist, reward_amount_dc,
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

        ChallengeService._verify_team_authority(
            claimed_by, claiming_team, action='submit a bounty claim',
        )

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

        # Hitlist: lock the challenger's entry fee.  The fee is held until
        # verify_claim either pays it back (challenger wins) or transfers
        # it to the issuer minus a 5% platform fee (challenger loses).
        if bounty.is_hitlist and bounty.challenger_entry_fee_dc > 0:
            wallet = _wallet_for_user(claimed_by)
            result = escrow_service.lock_funds(
                wallet,
                bounty.challenger_entry_fee_dc,
                reference_id=bounty.hitlist_ref_id(f"claim:{claim.pk}"),
                actor=claimed_by,
                note=f"Hitlist {bounty.reference_code} challenger entry fee "
                     f"(funded by {claimed_by.username})",
            )
            claim.entry_fee_lock_txn = result.transactions[0]
            claim.funded_by = claimed_by
            claim.save(update_fields=['entry_fee_lock_txn', 'funded_by'])

        # ── Spawn the Hitlist Match Room ──────────────────────────────
        if bounty.is_hitlist:
            try:
                match = ChallengeService._spawn_hitlist_match_room(
                    bounty, claim, actor=claimed_by,
                )
                if match is not None:
                    claim.match = match
                    claim.save(update_fields=['match'])
            except Exception:
                logger.exception(
                    "Match Room spawn failed for hitlist claim %s on bounty %s "
                    "— claim accepted but no lobby created.",
                    claim.pk, bounty.reference_code,
                )

        logger.info(
            "Bounty claim: %s claimed by %s (team=%s, entry_fee=%s DC, match=%s)",
            bounty.reference_code, claimed_by.username, claiming_team.name,
            bounty.challenger_entry_fee_dc if bounty.is_hitlist else 0,
            getattr(claim.match, 'pk', None),
        )
        return claim

    @staticmethod
    @transaction.atomic
    def verify_claim(*, claim_id, verified_by, approved=True, notes=''):
        """Verify or reject a bounty claim.

        Hitlist payout matrix (when ``bounty.is_hitlist`` is True):

          approved (challenger won):
              - refund challenger's entry-fee lock
              - payout the issuer's locked reward to the challenger
                (winnings minus HITLIST_PLATFORM_FEE_PCT)
              - mark bounty CLAIMED, refund OTHER pending claims
          rejected (challenger lost):
              - payout the challenger's entry-fee to the issuer
                (winnings minus HITLIST_PLATFORM_FEE_PCT)
              - issuer's reward stays locked for the next challenger
        """
        claim = BountyClaim.objects.select_for_update().select_related('bounty').get(pk=claim_id)

        if claim.status != 'PENDING':
            raise ValidationError("Claim is not pending.")

        bounty = claim.bounty
        is_hitlist = bounty.is_hitlist

        if approved:
            claim.status = 'VERIFIED'
            claim.verified_at = timezone.now()
            claim.verified_by = verified_by
            claim.closure_reason = 'VERIFIED_PAID'

            # Hitlist: pay challenger their winnings + refund their entry fee.
            if is_hitlist:
                BountyService._hitlist_payout_to_challenger(
                    bounty, claim, actor=verified_by
                )

            # Update bounty claim count + close bounty if maxed.
            bounty.claim_count += 1
            bounty_update_fields = ['claim_count', 'updated_at']
            if bounty.claim_count >= bounty.max_claims:
                bounty.status = 'CLAIMED'
                bounty.closure_reason = 'CLAIMED'
                bounty.escrow_locked = False
                bounty_update_fields += ['status', 'closure_reason', 'escrow_locked']
            bounty.save(update_fields=bounty_update_fields)

            # Auto-void any other PENDING claims (refund their entry fees).
            if bounty.status == 'CLAIMED':
                BountyService._refund_other_pending_claims(
                    bounty, except_pk=claim.pk, actor=verified_by
                )
        else:
            claim.status = 'REJECTED'
            claim.closure_reason = 'REJECTED'

            # Hitlist: pay the challenger's entry fee to the issuer (minus 5%).
            if is_hitlist:
                BountyService._hitlist_payout_to_issuer(
                    bounty, claim, actor=verified_by
                )

        claim.admin_notes = notes
        claim.save(update_fields=[
            'status', 'verified_at', 'verified_by', 'admin_notes',
            'closure_reason', 'outcome_txn',
        ])

        logger.info(
            "Bounty claim %s: %s (hitlist=%s, by %s)",
            'verified' if approved else 'rejected',
            bounty.reference_code, is_hitlist, verified_by.username,
        )
        return claim

    # ── Hitlist escrow helpers ───────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def admin_verify_claim(*, claim_id, verified_by, notes=''):
        """Service-backed admin path for approving a pending Bounty claim."""
        claim = BountyService.verify_claim(
            claim_id=claim_id,
            verified_by=verified_by,
            approved=True,
            notes=notes,
        )
        BountyService._log_bounty_admin_action(
            'bounty.claim_verified',
            claim.bounty,
            claim=claim,
            actor=verified_by,
            note=notes,
        )
        return claim

    @staticmethod
    @transaction.atomic
    def admin_reject_claim(*, claim_id, verified_by, notes=''):
        """Service-backed admin path for rejecting a pending Bounty claim."""
        claim = BountyService.verify_claim(
            claim_id=claim_id,
            verified_by=verified_by,
            approved=False,
            notes=notes,
        )
        BountyService._log_bounty_admin_action(
            'bounty.claim_rejected',
            claim.bounty,
            claim=claim,
            actor=verified_by,
            note=notes,
        )
        return claim

    @staticmethod
    @transaction.atomic
    def admin_void_refund_bounty(*, bounty_id, resolved_by, note=''):
        """Void an active Bounty and refund any locked Bounty funds safely."""
        bounty = Bounty.objects.select_for_update().get(pk=bounty_id)

        if bounty.status in ('CLAIMED', 'VERIFIED', 'PAID'):
            raise ValidationError("Settled or consumed Bounties cannot be voided by bulk admin action.")
        if bounty.status in ('EXPIRED', 'CANCELLED'):
            raise ValidationError(f"Bounty is already closed as {bounty.get_status_display()}.")

        if bounty.is_hitlist and bounty.escrow_locked and bounty.issuer_lock_txn_id and bounty.reward_amount_dc:
            wallet = _wallet_for_user(bounty.funded_by or bounty.created_by)
            escrow_service.refund_funds(
                wallet,
                bounty.reward_amount_dc,
                reference_id=bounty.hitlist_ref_id('issuer'),
                actor=resolved_by,
                note=note or f"Admin void refund for Bounty {bounty.reference_code}",
            )
            bounty.escrow_locked = False

        if bounty.is_hitlist:
            BountyService._refund_other_pending_claims(
                bounty, except_pk=0, actor=resolved_by
            )
        else:
            BountyService._close_pending_claims_without_escrow(
                bounty,
                closure_reason='VOIDED',
                closure_note='Bounty voided by admin.',
            )

        bounty.status = 'CANCELLED'
        bounty.closure_reason = 'ADMIN_VOID'
        bounty.closure_note = note or f"Voided by {resolved_by.username}."
        bounty.save(update_fields=[
            'status', 'escrow_locked', 'closure_reason', 'closure_note',
            'updated_at',
        ])
        BountyService._log_bounty_admin_action(
            'bounty.admin_void_refund',
            bounty,
            actor=resolved_by,
            note=bounty.closure_note,
        )
        return bounty

    @staticmethod
    @transaction.atomic
    def admin_expire_bounty(*, bounty_id, actor=None, note=''):
        """Expire a selected stale Bounty through the same refund path as the job."""
        bounty = Bounty.objects.select_for_update().get(pk=bounty_id)

        if bounty.status != 'ACTIVE':
            raise ValidationError("Only active Bounties can be expired.")
        if not bounty.expires_at or bounty.expires_at >= timezone.now():
            raise ValidationError("Only stale Bounties past their deadline can be expired.")

        if bounty.is_hitlist and bounty.escrow_locked and bounty.issuer_lock_txn_id and bounty.reward_amount_dc:
            wallet = _wallet_for_user(bounty.funded_by or bounty.created_by)
            escrow_service.refund_funds(
                wallet,
                bounty.reward_amount_dc,
                reference_id=bounty.hitlist_ref_id('issuer'),
                actor=actor,
                note=note or f"Bounty {bounty.reference_code} expired refund",
            )
            bounty.escrow_locked = False

        if bounty.is_hitlist:
            BountyService._refund_other_pending_claims(
                bounty, except_pk=0, actor=actor
            )
        else:
            BountyService._close_pending_claims_without_escrow(
                bounty,
                closure_reason='EXPIRED',
                closure_note='Bounty expired before verification.',
            )

        bounty.status = 'EXPIRED'
        bounty.closure_reason = 'EXPIRED'
        bounty.closure_note = note or bounty.closure_note
        bounty.save(update_fields=[
            'status', 'escrow_locked', 'closure_reason', 'closure_note',
            'updated_at',
        ])
        BountyService._log_bounty_admin_action(
            'bounty.admin_expired',
            bounty,
            actor=actor,
            note=bounty.closure_note,
        )
        return bounty

    @staticmethod
    @transaction.atomic
    def admin_respawn_claim_match_room(*, claim_id, actor):
        """Respawn a missing Bounty claim match room when the claim supports one."""
        claim = (
            BountyClaim.objects
            .select_for_update()
            .select_related('bounty', 'bounty__issuer_team', 'bounty__game', 'claiming_team')
            .get(pk=claim_id)
        )
        if claim.match_id:
            return claim.match
        if claim.status != 'PENDING':
            raise ValidationError("Only pending Bounty claims can have match rooms respawned.")
        if not claim.bounty.is_hitlist:
            raise ValidationError("This Bounty claim does not use a match room.")

        match = ChallengeService._spawn_hitlist_match_room(
            claim.bounty, claim, actor=actor,
        )
        if match is None:
            raise ValidationError("Could not create a match room for this Bounty claim.")
        claim.match = match
        claim.save(update_fields=['match'])
        BountyService._log_bounty_admin_action(
            'bounty.claim_match_room_respawned',
            claim.bounty,
            claim=claim,
            actor=actor,
            extra={'match_id': match.pk},
        )
        return match

    @staticmethod
    def _hitlist_payout_to_challenger(bounty, claim, *, actor=None):
        """Approved-claim path: refund challenger's entry-fee + transfer reward."""
        # Refund challenger entry-fee (their stake comes back).
        if claim.entry_fee_lock_txn_id:
            wallet = _wallet_for_user(claim.claimed_by)
            escrow_service.refund_funds(
                wallet,
                bounty.challenger_entry_fee_dc,
                reference_id=bounty.hitlist_ref_id(f"claim:{claim.pk}"),
                actor=actor,
                note=f"Hitlist {bounty.reference_code} entry-fee refund (winner)",
            )
        # Transfer issuer's locked reward to challenger (5% fee on winnings).
        if bounty.issuer_lock_txn_id and bounty.reward_amount_dc > 0:
            wallet = _wallet_for_user(claim.claimed_by)
            payout = escrow_service.payout_winner(
                wallet,
                bounty.reward_amount_dc,
                platform_fee_pct=HITLIST_PLATFORM_FEE_PCT,
                reference_id=bounty.hitlist_ref_id(f"payout:{claim.pk}"),
                actor=actor,
                note=f"Hitlist {bounty.reference_code} reward to {claim.claiming_team.name}",
            )
            claim.outcome_txn = payout.transactions[0]

    @staticmethod
    def _hitlist_payout_to_issuer(bounty, claim, *, actor=None):
        """Rejected-claim path: transfer challenger entry-fee to issuer (5% fee)."""
        if not claim.entry_fee_lock_txn_id or not bounty.challenger_entry_fee_dc:
            return
        wallet = _wallet_for_user(bounty.created_by)
        payout = escrow_service.payout_winner(
            wallet,
            bounty.challenger_entry_fee_dc,
            platform_fee_pct=HITLIST_PLATFORM_FEE_PCT,
            reference_id=bounty.hitlist_ref_id(f"payout:{claim.pk}"),
            actor=actor,
            note=f"Hitlist {bounty.reference_code} entry-fee to issuer",
        )
        claim.outcome_txn = payout.transactions[0]

    @staticmethod
    def _refund_other_pending_claims(bounty, *, except_pk, actor=None):
        """Refund entry-fees on any OTHER PENDING claims (bounty consumed)."""
        if not bounty.is_hitlist:
            return
        others = BountyClaim.objects.select_for_update().filter(
            bounty=bounty, status='PENDING'
        ).exclude(pk=except_pk)
        for other in others:
            try:
                if other.entry_fee_lock_txn_id and bounty.challenger_entry_fee_dc:
                    wallet = _wallet_for_user(other.claimed_by)
                    escrow_service.refund_funds(
                        wallet,
                        bounty.challenger_entry_fee_dc,
                        reference_id=bounty.hitlist_ref_id(f"claim:{other.pk}"),
                        actor=actor,
                        note=f"Hitlist {bounty.reference_code} bounty consumed — refund",
                    )
                other.status = 'REJECTED'
                other.closure_reason = 'VOIDED'
                other.closure_note = 'Bounty consumed by another verified claim.'
                other.save(update_fields=[
                    'status', 'closure_reason', 'closure_note',
                ])
            except Exception:
                logger.exception(
                    "_refund_other_pending_claims: failed on claim=%s", other.pk
                )

    @staticmethod
    def _close_pending_claims_without_escrow(bounty, *, closure_reason, closure_note):
        """Close pending non-escrow claims when their parent Bounty closes."""
        BountyClaim.objects.select_for_update().filter(
            bounty=bounty,
            status='PENDING',
        ).update(
            status='REJECTED',
            closure_reason=closure_reason,
            closure_note=closure_note,
        )

    @staticmethod
    def _log_bounty_admin_action(event_name, bounty, *, claim=None, actor=None, note='', extra=None):
        """Persist a lightweight Bounty operator audit event without blocking the action."""
        try:
            from apps.common.events.models import EventLog

            EventLog.objects.create(
                name=event_name,
                payload={
                    'bounty_id': str(bounty.pk),
                    'reference_code': bounty.reference_code,
                    'bounty_status': bounty.status,
                    'claim_id': str(claim.pk) if claim else None,
                    'claim_status': claim.status if claim else None,
                    'note': note,
                    **(extra or {}),
                },
                occurred_at=timezone.now(),
                user_id=getattr(actor, 'pk', None),
                correlation_id=bounty.reference_code,
                metadata={'source': 'competition.admin'},
                status=EventLog.STATUS_PROCESSED,
            )
        except Exception:
            logger.exception(
                "Failed to write Bounty admin audit event %s for %s",
                event_name,
                getattr(bounty, 'reference_code', bounty),
            )

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
        """Expire ACTIVE bounties past their deadline.

        Per-row processing so any locked Hitlist reward is refunded to
        the issuer as the bounty transitions to EXPIRED.  In-flight
        PENDING claims also get their entry-fees refunded.
        """
        stale_qs = Bounty.objects.filter(
            status='ACTIVE',
            expires_at__lt=timezone.now(),
        ).only('id', 'reference_code')

        count = 0
        for stub in stale_qs.iterator():
            try:
                with transaction.atomic():
                    bounty = Bounty.objects.select_for_update().get(pk=stub.pk)
                    if bounty.status != 'ACTIVE':
                        continue
                    # Refund issuer's reward lock (Hitlist only).
                    if bounty.is_hitlist and bounty.issuer_lock_txn_id:
                        wallet = _wallet_for_user(bounty.created_by)
                        escrow_service.refund_funds(
                            wallet,
                            bounty.reward_amount_dc,
                            reference_id=bounty.hitlist_ref_id('issuer'),
                            actor=None,
                            note=f"Hitlist {bounty.reference_code} expired — refund issuer",
                        )
                        bounty.escrow_locked = False
                    # Refund any in-flight challenger entry-fees.
                    BountyService._refund_other_pending_claims(
                        bounty, except_pk=0, actor=None
                    )
                    bounty.status = 'EXPIRED'
                    bounty.closure_reason = 'EXPIRED'
                    bounty.save(update_fields=[
                        'status', 'closure_reason', 'escrow_locked', 'updated_at',
                    ])
                count += 1
            except Exception:
                logger.exception(
                    "expire_stale_bounties: failed on %s", stub.reference_code,
                )

        if count:
            logger.info("Expired %d stale bounties", count)
        return count

