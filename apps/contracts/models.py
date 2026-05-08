"""Crown Contracts — admin-curated self-challenges.

ContractTemplate is the catalog row (admin-configurable mission spec).
ContractEnrollment is one user's attempt against a template, with its
own escrow lock + audit trail.

Lifecycle:
    ACTIVE  → COMPLETED    (goal met, reward paid)
            → FAILED       (deadline passed without completion)
            → EXPIRED      (alias of FAILED for deadline-miss)
            → CANCELLED    (user opt-out, entry fee forfeited)
            → VOIDED       (admin remediation, entry fee refunded)
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# Template — admin-curated mission catalog
# ─────────────────────────────────────────────────────────────────────────────

class ContractTemplate(models.Model):
    """A reusable mission definition that players can enroll in."""

    GOAL_TYPE_CHOICES = [
        ('TOP_N_FINISH',    'Top-N finishes within window'),
        ('WIN_STREAK',      'Win streak'),
        ('MATCHES_PLAYED',  'Number of matches played'),
        ('KILL_THRESHOLD',  'Total kills threshold'),
        ('CUSTOM',          'Custom (free-form goal_spec)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(
        max_length=120,
        help_text="Display title (e.g. 'The Survivor's Path')."
    )
    description = models.TextField(
        blank=True,
        help_text="Player-facing description of the mission and rules."
    )

    game = models.ForeignKey(
        'games.Game',
        on_delete=models.PROTECT,
        related_name='contract_templates',
        help_text="Game this contract applies to."
    )

    # ── Economy ──────────────────────────────────────────────────────────
    entry_fee_dc = models.PositiveIntegerField(
        default=0,
        help_text="DeltaCoins the player locks at enrollment.  Forfeited on failure."
    )
    reward_dc = models.PositiveIntegerField(
        default=0,
        help_text="DeltaCoins paid on successful completion."
    )

    # ── Goal specification (machine-readable) ────────────────────────────
    goal_type = models.CharField(
        max_length=24,
        choices=GOAL_TYPE_CHOICES,
        default='CUSTOM',
        help_text="Hint for the verification engine on how to read goal_spec."
    )
    goal_spec = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Machine-readable goal.  Example for 'TOP_N_FINISH':\n"
            '  {"metric": "top_n_finish", "n": 5, "count": 3, "window_hours": 24}'
        )
    )

    # ── Reward extras ────────────────────────────────────────────────────
    badge_slug = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Optional badge slug awarded on completion (e.g. 'survivor')."
    )

    # ── Time-window ──────────────────────────────────────────────────────
    duration_hours = models.PositiveIntegerField(
        default=24,
        help_text="Hours the player has to complete the goal after enrollment."
    )

    # ── Visibility / availability ────────────────────────────────────────
    is_active = models.BooleanField(default=True, db_index=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'contracts_template'
        verbose_name = 'Contract Template'
        verbose_name_plural = 'Contract Templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'game']),
        ]

    def __str__(self) -> str:
        return f"[CT] {self.title} ({self.game_id})"

    @property
    def is_currently_available(self) -> bool:
        """True when the template can be enrolled in right now."""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Enrollment — one user's attempt against a template
# ─────────────────────────────────────────────────────────────────────────────

class ContractEnrollment(models.Model):
    """A single player's attempt at a ContractTemplate."""

    STATUS_CHOICES = [
        ('ACTIVE',    'Active — In progress'),
        ('COMPLETED', 'Completed — Reward paid'),
        ('FAILED',    'Failed — Goal not met'),
        ('EXPIRED',   'Expired — Deadline passed'),
        ('CANCELLED', 'Cancelled — User opted out'),
        ('VOIDED',    'Voided — Admin remediation'),
    ]

    CLOSURE_REASON_CHOICES = [
        ('',           'Not closed'),
        ('COMPLETED',  'Goal met — reward paid'),
        ('FAILED',     'Goal missed within deadline'),
        ('EXPIRED',    'Deadline passed without resolution'),
        ('CANCELLED',  'Cancelled by user (entry fee forfeited)'),
        ('VOIDED',     'Voided by admin (entry fee refunded)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    reference_code = models.CharField(
        max_length=24,
        unique=True,
        db_index=True,
        help_text="Stable reference (e.g. 'CT-PUBGM-A1B2C3')."
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contract_enrollments',
    )
    template = models.ForeignKey(
        ContractTemplate,
        on_delete=models.PROTECT,
        related_name='enrollments',
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        db_index=True,
    )

    # ── Verification state (mutable) ─────────────────────────────────────
    progress = models.JSONField(
        default=dict,
        blank=True,
        help_text="Running counters for the verification engine."
    )

    # ── Time-window ──────────────────────────────────────────────────────
    enrolled_at = models.DateTimeField(auto_now_add=True)
    deadline_at = models.DateTimeField(
        help_text="UTC timestamp by which the goal must be completed."
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    # ── Escrow audit trail ───────────────────────────────────────────────
    escrow_lock_txn = models.ForeignKey(
        'economy.DeltaCrownTransaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        help_text="Player's entry-fee lock transaction (set at enrollment)."
    )
    reward_payout_txn = models.ForeignKey(
        'economy.DeltaCrownTransaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        help_text="Reward payout transaction (set on COMPLETED)."
    )

    # ── Closure (UI: never rely on a generic countdown) ──────────────────
    closure_reason = models.CharField(
        max_length=24,
        choices=CLOSURE_REASON_CHOICES,
        blank=True,
        default='',
        db_index=True,
        help_text="Why the contract closed.  UI must surface this rather than a bare countdown."
    )
    closure_note = models.TextField(
        blank=True,
        default='',
        help_text="Free-form admin/system note for the closure."
    )

    class Meta:
        db_table = 'contracts_enrollment'
        verbose_name = 'Contract Enrollment'
        verbose_name_plural = 'Contract Enrollments'
        ordering = ['-enrolled_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'deadline_at']),
            models.Index(fields=['template', 'status']),
        ]
        constraints = [
            # One ACTIVE enrollment per (user, template) at a time.
            models.UniqueConstraint(
                fields=['user', 'template'],
                condition=models.Q(status='ACTIVE'),
                name='one_active_enrollment_per_user_template',
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.reference_code}] {self.user_id} → {self.template.title} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = self._generate_reference_code()
        super().save(*args, **kwargs)

    def _generate_reference_code(self) -> str:
        short = getattr(self.template.game, 'short_code', 'GEN') if self.template_id else 'GEN'
        return f"CT-{short}-{uuid.uuid4().hex[:6].upper()}"

    def contract_ref_id(self, suffix: str = '') -> str:
        """Stable escrow reference_id for this enrollment."""
        base = self.reference_code
        return f"{base}_{suffix}" if suffix else base

    @property
    def is_expired(self) -> bool:
        return self.status == 'ACTIVE' and timezone.now() > self.deadline_at
