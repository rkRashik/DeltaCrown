"""Crown Royale service layer.

Slot reservation + payout for paid Battle Royale lobbies.  Match
running, brackets, and check-in stay in apps.tournaments.

Key flows:
  * reserve_slot(user, lobby) — atomic: lock entry fee + create entry row.
  * cancel_reservation(entry) — refund pre-match, forfeit during/after match.
  * record_scores(lobby, scores) — admin records final placements.
  * settle_lobby(lobby) — distribute pot per prize_distribution config.
  * cancel_lobby(lobby, reason) — refund every locked reservation.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.economy import escrow_service
from apps.economy.models import DeltaCrownWallet
from apps.economy.services import get_master_treasury

from .models import RoyaleEntry, RoyaleLobby


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

#: Anti-whale ceiling for Royale entry fees.
ROYALE_ENTRY_FEE_CAP_DC: int = 1_000

#: Platform fee taken from the prize pot when a lobby settles.
ROYALE_PLATFORM_FEE_PCT: int = 5


def _wallet_for_user(user) -> DeltaCrownWallet:
    if user is None:
        raise ValidationError("Cannot resolve wallet: user is None.")
    profile = getattr(user, "profile", None) or getattr(user, "user_profile", None)
    if profile is None:
        raise ValidationError(
            f"User '{getattr(user, 'username', user)}' has no profile."
        )
    try:
        return DeltaCrownWallet.objects.get(profile=profile)
    except DeltaCrownWallet.DoesNotExist as exc:
        raise ValidationError(
            f"User '{user.username}' has no DeltaCoin wallet."
        ) from exc


def _resolve_prize_amounts(lobby: RoyaleLobby, total_pot: int) -> dict:
    """Resolve a {placement:int → DC int} payout map from prize_distribution.

    Floors all amounts and clamps the sum to total_pot.  Anything left
    over is implicitly retained by the platform.
    """
    cfg = lobby.prize_distribution or {}
    mode = (cfg.get('mode') or 'PERCENT').upper()
    raw = cfg.get('splits') or {}

    payouts: dict[int, int] = {}
    if mode == 'PERCENT':
        for k, pct in raw.items():
            try:
                placement = int(k)
                pct_dec = Decimal(str(pct))
            except (TypeError, ValueError):
                continue
            amount = int(Decimal(str(total_pot)) * pct_dec / Decimal('100'))
            if amount > 0:
                payouts[placement] = amount
    elif mode == 'FIXED':
        for k, amt in raw.items():
            try:
                placement = int(k)
                amount = int(amt)
            except (TypeError, ValueError):
                continue
            if amount > 0:
                payouts[placement] = amount

    # Clamp to pot — never pay more than what was collected.
    running = 0
    clamped: dict[int, int] = {}
    for placement in sorted(payouts):
        share = min(payouts[placement], total_pot - running)
        if share <= 0:
            break
        clamped[placement] = share
        running += share
    return clamped


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class RoyaleService:
    """Lifecycle service for Crown Royale lobbies."""

    # ── Reservations ─────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def reserve_slot(*, user, lobby_id) -> RoyaleEntry:
        """Reserve one slot in ``lobby`` — locks the entry fee."""
        lobby = RoyaleLobby.objects.select_for_update().get(pk=lobby_id)

        if lobby.status not in ('ANNOUNCED', 'FILLING'):
            raise ValidationError("Lobby is not accepting reservations.")
        if lobby.entry_fee_dc > ROYALE_ENTRY_FEE_CAP_DC:
            raise ValidationError(
                f"Entry fee {lobby.entry_fee_dc} DC exceeds the anti-whale cap "
                f"of {ROYALE_ENTRY_FEE_CAP_DC} DC."
            )

        # Window-based gate (independent of lobby.status flips).
        now = timezone.now()
        if lobby.registration_opens_at and now < lobby.registration_opens_at:
            raise ValidationError("Reservations are not open yet.")
        if lobby.registration_closes_at and now > lobby.registration_closes_at:
            raise ValidationError("Reservations are closed.")

        if lobby.remaining_slots <= 0:
            raise ValidationError("Lobby is full.")

        # Unique-constraint guard (also enforced at the DB level).
        if RoyaleEntry.objects.filter(
            lobby=lobby, user=user,
            status__in=['RESERVED', 'CONFIRMED', 'SCORED']
        ).exists():
            raise ValidationError("You already have a reservation in this lobby.")

        entry = RoyaleEntry.objects.create(
            lobby=lobby,
            user=user,
            status='RESERVED',
        )

        if lobby.entry_fee_dc:
            wallet = _wallet_for_user(user)
            result = escrow_service.lock_funds(
                wallet,
                lobby.entry_fee_dc,
                reference_id=lobby.royale_ref_id(f"entry:{entry.pk}"),
                actor=user,
                note=f"Crown Royale {lobby.reference_code} entry fee",
            )
            entry.escrow_lock_txn = result.transactions[0]
            entry.save(update_fields=['escrow_lock_txn'])

        # Flip lobby state once the last slot is taken.
        if lobby.remaining_slots <= 0 and lobby.status == 'FILLING':
            lobby.status = 'FULL'
            lobby.save(update_fields=['status', 'updated_at'])

        logger.info(
            "Royale slot reserved: %s by %s (lobby=%s, fee=%s DC)",
            entry.pk, user.username, lobby.reference_code, lobby.entry_fee_dc,
        )
        return entry

    @staticmethod
    @transaction.atomic
    def cancel_reservation(*, entry_id, actor=None) -> RoyaleEntry:
        """Cancel a player's reservation and refund the entry fee.

        Only valid before the lobby goes LIVE.  Once the match starts,
        cancellation is treated as a NO_SHOW (no refund).
        """
        entry = RoyaleEntry.objects.select_for_update().select_related('lobby').get(pk=entry_id)
        lobby = entry.lobby

        if entry.status != 'RESERVED':
            raise ValidationError("Only reserved entries can be cancelled.")
        if lobby.status not in ('ANNOUNCED', 'FILLING', 'FULL'):
            raise ValidationError("Lobby is already underway; cannot refund.")

        if entry.escrow_lock_txn_id and lobby.entry_fee_dc:
            wallet = _wallet_for_user(entry.user)
            escrow_service.refund_funds(
                wallet,
                lobby.entry_fee_dc,
                reference_id=lobby.royale_ref_id(f"entry:{entry.pk}"),
                actor=actor,
                note=f"Royale {lobby.reference_code} entry-fee refund",
            )

        entry.status = 'REFUNDED'
        entry.closure_reason = 'REFUNDED_BY_USER'
        entry.resolved_at = timezone.now()
        entry.save(update_fields=[
            'status', 'closure_reason', 'resolved_at',
        ])

        # If we were FULL and now have a slot again, drop back to FILLING.
        if lobby.status == 'FULL' and lobby.remaining_slots > 0:
            lobby.status = 'FILLING'
            lobby.save(update_fields=['status', 'updated_at'])

        return entry

    # ── Scoring ──────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def record_scores(*, lobby_id, scores: Iterable[dict], actor=None) -> RoyaleLobby:
        """Record final placements/kills.

        ``scores`` is an iterable of ``{"entry_id": ..., "placement": int,
        "kills": int}`` dicts.  Entries not present are marked NO_SHOW.
        """
        lobby = RoyaleLobby.objects.select_for_update().get(pk=lobby_id)
        if lobby.status not in ('LIVE', 'FULL', 'SCORING'):
            raise ValidationError("Lobby is not in a scorable state.")

        scored_ids = set()
        for row in scores:
            entry = RoyaleEntry.objects.select_for_update().get(
                pk=row['entry_id'], lobby=lobby
            )
            entry.placement = row.get('placement')
            entry.kills = row.get('kills')
            entry.status = 'SCORED'
            entry.scored_at = timezone.now()
            entry.save(update_fields=['placement', 'kills', 'status', 'scored_at'])
            scored_ids.add(entry.pk)

        # Anyone NOT in the scores list is a no-show.
        no_shows = RoyaleEntry.objects.filter(
            lobby=lobby, status__in=['RESERVED', 'CONFIRMED'],
        ).exclude(pk__in=scored_ids)
        for entry in no_shows:
            entry.status = 'NO_SHOW'
            entry.closure_reason = 'FORFEIT_NO_SHOW'
            entry.scored_at = timezone.now()
            entry.save(update_fields=[
                'status', 'closure_reason', 'scored_at',
            ])

        lobby.status = 'SCORING'
        lobby.save(update_fields=['status', 'updated_at'])
        return lobby

    # ── Settlement ───────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def settle_lobby(*, lobby_id, actor=None) -> RoyaleLobby:
        """Distribute the prize pot per ``lobby.prize_distribution``.

        Forfeited (NO_SHOW) entry fees are transferred to the platform
        treasury before the prize pot is calculated.  The remainder of
        the pot (after placement payouts) is implicitly retained as
        platform revenue.
        """
        lobby = RoyaleLobby.objects.select_for_update().get(pk=lobby_id)
        if lobby.status != 'SCORING':
            raise ValidationError("Only SCORING lobbies can settle.")

        treasury = get_master_treasury()
        all_entries = list(
            RoyaleEntry.objects.select_for_update().filter(lobby=lobby)
        )
        total_pot_dc = lobby.entry_fee_dc * sum(
            1 for e in all_entries
            if e.status in ('SCORED', 'NO_SHOW') and e.escrow_lock_txn_id
        )

        # 1. Transfer NO_SHOW entry fees to treasury (forfeit).
        for entry in all_entries:
            if entry.status != 'NO_SHOW' or not entry.escrow_lock_txn_id:
                continue
            payout = escrow_service.payout_winner(
                treasury,
                lobby.entry_fee_dc,
                platform_fee_pct=0,
                reference_id=lobby.royale_ref_id(f"forfeit:{entry.pk}"),
                actor=actor,
                note=f"Royale {lobby.reference_code} no-show forfeit",
            )
            entry.payout_txn = payout.transactions[0]
            entry.resolved_at = timezone.now()
            entry.save(update_fields=['payout_txn', 'resolved_at'])

        # 2. Pay placement prizes per config.
        prize_map = _resolve_prize_amounts(lobby, total_pot_dc)
        scored_by_placement = {
            e.placement: e for e in all_entries
            if e.status == 'SCORED' and e.placement is not None
        }

        for placement, prize_dc in prize_map.items():
            entry = scored_by_placement.get(placement)
            if entry is None or prize_dc <= 0:
                continue
            wallet = _wallet_for_user(entry.user)
            payout = escrow_service.payout_winner(
                wallet,
                prize_dc,
                platform_fee_pct=ROYALE_PLATFORM_FEE_PCT,
                reference_id=lobby.royale_ref_id(f"prize:{entry.pk}"),
                actor=actor,
                note=f"Royale {lobby.reference_code} placement #{placement}",
            )
            entry.payout_txn = payout.transactions[0]
            entry.closure_reason = 'SETTLED_PRIZE'
            entry.resolved_at = timezone.now()
            entry.save(update_fields=[
                'payout_txn', 'closure_reason', 'resolved_at',
            ])

        # 3. Mark all remaining SCORED entries as out-of-prize.
        for entry in all_entries:
            if entry.status == 'SCORED' and not entry.closure_reason:
                entry.closure_reason = 'SETTLED_NO_PRIZE'
                entry.resolved_at = timezone.now()
                entry.save(update_fields=['closure_reason', 'resolved_at'])

        lobby.status = 'SETTLED'
        lobby.closure_reason = 'SETTLED_NORMAL'
        lobby.save(update_fields=['status', 'closure_reason', 'updated_at'])

        logger.info(
            "Royale lobby settled: %s (pot=%s DC, prizes=%s)",
            lobby.reference_code, total_pot_dc, prize_map,
        )
        return lobby

    # ── Cancellation ─────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def cancel_lobby(
        *, lobby_id, reason='CANCELLED_BY_ADMIN', note='', actor=None,
    ) -> RoyaleLobby:
        """Cancel a lobby and refund every locked reservation."""
        lobby = RoyaleLobby.objects.select_for_update().get(pk=lobby_id)
        if lobby.status in ('SETTLED', 'CANCELLED'):
            raise ValidationError("Lobby is already terminal.")

        valid_reasons = {
            'CANCELLED_BY_ADMIN', 'CANCELLED_INSUFFICIENT',
            'CANCELLED_GAME_OUTAGE', 'VOIDED_DISPUTE',
        }
        if reason not in valid_reasons:
            raise ValidationError(f"Invalid cancel reason: {reason}")

        for entry in RoyaleEntry.objects.select_for_update().filter(
            lobby=lobby,
            status__in=['RESERVED', 'CONFIRMED', 'SCORED', 'NO_SHOW'],
        ):
            if entry.escrow_lock_txn_id and lobby.entry_fee_dc:
                wallet = _wallet_for_user(entry.user)
                escrow_service.refund_funds(
                    wallet,
                    lobby.entry_fee_dc,
                    reference_id=lobby.royale_ref_id(f"entry:{entry.pk}"),
                    actor=actor,
                    note=f"Royale {lobby.reference_code} cancelled — refund",
                )
            entry.status = 'REFUNDED'
            entry.closure_reason = 'REFUNDED_LOBBY'
            entry.resolved_at = timezone.now()
            entry.save(update_fields=[
                'status', 'closure_reason', 'resolved_at',
            ])

        lobby.status = 'CANCELLED'
        lobby.closure_reason = reason
        lobby.closure_note = note or ''
        lobby.save(update_fields=[
            'status', 'closure_reason', 'closure_note', 'updated_at',
        ])

        logger.info(
            "Royale lobby cancelled: %s (reason=%s)",
            lobby.reference_code, reason,
        )
        return lobby
