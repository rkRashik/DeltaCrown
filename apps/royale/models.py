"""Dropzone — scheduled Battle Royale custom lobbies.

A RoyaleLobby is a thin reservation/reward layer wrapping a real
``apps.tournaments.Tournament`` row, which provides the admin UI,
brackets, and check-in flow. Players reserve slots with a DeltaCoin
entry fee; rewards are distributed by admin-configurable placement
splits when the lobby settles.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# RoyaleLobby — the scheduled paid lobby
# ─────────────────────────────────────────────────────────────────────────────

class RoyaleLobby(models.Model):
    """A scheduled paid BR lobby.  One per Tournament row."""

    STATUS_CHOICES = [
        ('ANNOUNCED', 'Announced — Reservations not yet open'),
        ('FILLING',   'Filling — Reservations open'),
        ('FULL',      'Full — All slots reserved'),
        ('LIVE',      'Live — Match in progress'),
        ('SCORING',   'Scoring — Awaiting placement results'),
        ('SETTLED',   'Settled — Prizes paid'),
        ('CANCELLED', 'Cancelled — Refunded all reservations'),
    ]

    CLOSURE_REASON_CHOICES = [
        ('',                       'Not closed'),
        ('SETTLED_NORMAL',         'Match completed and prizes paid'),
        ('CANCELLED_BY_ADMIN',     'Cancelled by admin'),
        ('CANCELLED_INSUFFICIENT', 'Cancelled — insufficient reservations'),
        ('CANCELLED_GAME_OUTAGE',  'Cancelled — upstream game outage'),
        ('VOIDED_DISPUTE',         'Voided — unresolved scoring dispute'),
    ]

    PRIZE_MODE_CHOICES = [
        ('PERCENT', 'Percent of pot'),
        ('FIXED',   'Fixed DC amounts'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reference_code = models.CharField(
        max_length=24,
        unique=True,
        db_index=True,
        help_text="Stable reference (e.g. 'RY-FF-A1B2C3')."
    )

    # ── Backing tournament ───────────────────────────────────────────────
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.PROTECT,
        related_name='royale_lobby',
        help_text="The Tournament row that owns the bracket / check-in flow."
    )
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.PROTECT,
        related_name='royale_lobbies',
    )

    title = models.CharField(
        max_length=120,
        help_text="Player-facing lobby title (e.g. 'Friday Night Bermuda Drop')."
    )

    # ── Capacity & economy ───────────────────────────────────────────────
    slot_capacity = models.PositiveIntegerField(
        help_text="Maximum number of paid slots in this lobby."
    )
    entry_fee_dc = models.PositiveIntegerField(
        default=0,
        help_text="DeltaCoins each player locks to reserve a slot."
    )

    # Admin-configurable prize distribution.  Two modes:
    #   PERCENT: {"mode": "PERCENT", "splits": {"1": 50, "2": 25, "3": 10}}
    #   FIXED:   {"mode": "FIXED",   "splits": {"1": 500, "2": 250, "3": 100}}
    # Keys are placement strings ('1', '2', ...); values are integers.
    prize_distribution = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-placement payout config.  See model docstring."
    )

    # ── Schedule ─────────────────────────────────────────────────────────
    scheduled_at = models.DateTimeField(
        help_text="UTC time the match begins (room ID is revealed at this time)."
    )
    registration_opens_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When slot reservations open."
    )
    registration_closes_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When slot reservations close (typically scheduled_at)."
    )

    # ── Custom-room credentials (revealed at scheduled_at) ───────────────
    room_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="Custom-room ID, surfaced to confirmed entries at match time."
    )
    room_password = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="Custom-room password (treat as semi-secret)."
    )

    # ── State ────────────────────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ANNOUNCED',
        db_index=True,
    )

    closure_reason = models.CharField(
        max_length=32,
        choices=CLOSURE_REASON_CHOICES,
        blank=True,
        default='',
        db_index=True,
        help_text="Why the lobby closed.  UI must surface this rather than a bare countdown."
    )
    closure_note = models.TextField(
        blank=True,
        default='',
        help_text="Free-form admin/system note for the closure."
    )

    # ── Visibility ───────────────────────────────────────────────────────
    is_public = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='royale_lobbies_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'royale_lobby'
        verbose_name = 'Royale Lobby'
        verbose_name_plural = 'Royale Lobbies'
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['game', 'status', '-scheduled_at']),
        ]

    def __str__(self) -> str:
        return f"[{self.reference_code}] {self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = self._generate_reference_code()
        super().save(*args, **kwargs)

    def _generate_reference_code(self) -> str:
        short = getattr(self.game, 'short_code', 'GEN') if self.game_id else 'GEN'
        return f"RY-{short}-{uuid.uuid4().hex[:6].upper()}"

    # ── Helpers ──────────────────────────────────────────────────────────

    def royale_ref_id(self, suffix: str = '') -> str:
        """Stable escrow reference_id for this lobby."""
        base = self.reference_code
        return f"{base}_{suffix}" if suffix else base

    @property
    def reserved_count(self) -> int:
        return self.entries.filter(
            status__in=['RESERVED', 'CONFIRMED', 'SCORED', 'NO_SHOW']
        ).count()

    @property
    def remaining_slots(self) -> int:
        return max(0, self.slot_capacity - self.reserved_count)

    @property
    def total_pot_dc(self) -> int:
        """Total DC currently locked across all paid reservations."""
        return self.entries.filter(
            status__in=['RESERVED', 'CONFIRMED', 'SCORED', 'NO_SHOW']
        ).count() * self.entry_fee_dc


# ─────────────────────────────────────────────────────────────────────────────
# RoyaleEntry — one player's paid reservation
# ─────────────────────────────────────────────────────────────────────────────

class RoyaleEntry(models.Model):
    """One player's paid slot reservation in a RoyaleLobby."""

    STATUS_CHOICES = [
        ('RESERVED',  'Reserved — Slot held, entry fee locked'),
        ('CONFIRMED', 'Confirmed — Player checked in for the match'),
        ('SCORED',    'Scored — Final placement recorded'),
        ('NO_SHOW',   'No-show — Did not check in'),
        ('REFUNDED',  'Refunded — Reservation cancelled'),
        ('VOIDED',    'Voided — Admin remediation'),
    ]

    CLOSURE_REASON_CHOICES = [
        ('',                  'Not closed'),
        ('SETTLED_PRIZE',     'Settled — placement prize paid'),
        ('SETTLED_NO_PRIZE',  'Settled — placement out of prize tier'),
        ('REFUNDED_BY_USER',  'Cancelled by user — refunded'),
        ('REFUNDED_LOBBY',    'Lobby cancelled — refunded'),
        ('FORFEIT_NO_SHOW',   'No-show — entry fee forfeited'),
        ('VOIDED_DISPUTE',    'Voided — unresolved scoring dispute'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    lobby = models.ForeignKey(
        RoyaleLobby,
        on_delete=models.CASCADE,
        related_name='entries',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='royale_entries',
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='RESERVED',
        db_index=True,
    )

    # ── Result ───────────────────────────────────────────────────────────
    placement = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Final placement (1 = winner).  Set during scoring."
    )
    kills = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Kill count from the match (used for tie-breakers)."
    )

    # ── Escrow audit trail ───────────────────────────────────────────────
    escrow_lock_txn = models.ForeignKey(
        'economy.DeltaCrownTransaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        help_text="Player's entry-fee lock transaction."
    )
    payout_txn = models.ForeignKey(
        'economy.DeltaCrownTransaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        help_text="Settlement transaction (payout or refund)."
    )

    # ── Closure ──────────────────────────────────────────────────────────
    closure_reason = models.CharField(
        max_length=32,
        choices=CLOSURE_REASON_CHOICES,
        blank=True,
        default='',
        db_index=True,
        help_text="Why the entry closed.  UI surfaces this on the entry card."
    )
    closure_note = models.TextField(
        blank=True,
        default='',
        help_text="Free-form admin/system note for the entry closure."
    )

    # ── Timestamps ───────────────────────────────────────────────────────
    reserved_at = models.DateTimeField(auto_now_add=True)
    scored_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'royale_entry'
        verbose_name = 'Royale Entry'
        verbose_name_plural = 'Royale Entries'
        ordering = ['lobby', 'placement', 'reserved_at']
        indexes = [
            models.Index(fields=['lobby', 'status']),
            models.Index(fields=['user', '-reserved_at']),
            models.Index(fields=['lobby', 'placement']),
        ]
        constraints = [
            # One non-terminal reservation per (user, lobby).
            models.UniqueConstraint(
                fields=['lobby', 'user'],
                condition=models.Q(status__in=['RESERVED', 'CONFIRMED', 'SCORED']),
                name='one_open_entry_per_user_lobby',
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} → {self.lobby.reference_code} ({self.status})"
