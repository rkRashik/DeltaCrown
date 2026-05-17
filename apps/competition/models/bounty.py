"""
Bounty model — Standing rewards for specific competitive achievements.

A bounty is posted by a team (or the platform) offering a reward to any team
that can accomplish a specific feat — e.g., "Beat our team in a BO3" or
"Win 5 consecutive ranked matches in Valorant."

Bounties differ from Challenges:
  - Challenge: Direct 1-on-1 invitation/offer to play
  - Bounty: Open reward available to anyone who meets the criteria

Bounty lifecycle:
  ACTIVE → CLAIMED (someone reached the criteria) → VERIFIED → PAID
         → EXPIRED (deadline passed, nobody claimed)
         → CANCELLED (issuer withdrew)
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid

from apps.common.models import SoftDeleteModel
from apps.common.managers import SoftDeleteManager


class Bounty(SoftDeleteModel):
    """
    A standing reward for achieving a specific competitive goal.
    """
    
    # ── Identifiers ──────────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    reference_code = models.CharField(
        max_length=16,
        unique=True,
        db_index=True,
        help_text="Short reference code, e.g. 'BN-VAL-X1Y2Z3'"
    )

    # ── Issuer ───────────────────────────────────────────────────────────
    issuer_team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='competition_bounties_issued',
        help_text="Team that posted this bounty"
    )
    
    # ── Game ─────────────────────────────────────────────────────────────
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.PROTECT,
        related_name='competition_bounties',
        help_text="Game this bounty applies to"
    )

    # ── Status ───────────────────────────────────────────────────────────
    STATUS_CHOICES = [
        ('ACTIVE', 'Active — Open for claims'),
        ('CLAIMED', 'Claimed — Awaiting verification'),
        ('VERIFIED', 'Verified — Claim confirmed'),
        ('PAID', 'Paid — Reward distributed'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled by issuer'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE',
        db_index=True
    )

    # ── Bounty Type ──────────────────────────────────────────────────────
    BOUNTY_TYPE_CHOICES = [
        ('BEAT_US', 'Beat Us — Defeat the issuer team'),
        ('WIN_STREAK', 'Win Streak — Win N consecutive matches'),
        ('FIRST_BLOOD', 'First Blood — First team to complete a task'),
        ('TOURNAMENT_WIN', 'Tournament Win — Win a specific tournament'),
        ('CUSTOM', 'Custom — Free-form achievement criteria'),
    ]
    bounty_type = models.CharField(
        max_length=20,
        choices=BOUNTY_TYPE_CHOICES,
        default='BEAT_US'
    )

    # ── Content ──────────────────────────────────────────────────────────
    title = models.CharField(
        max_length=120,
        help_text="Bounty headline (e.g., 'Can You Beat the Kings?')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed criteria, rules, and context"
    )
    
    # ── Criteria (machine-readable) ──────────────────────────────────────
    criteria = models.JSONField(
        default=dict,
        help_text=(
            "Machine-readable achievement criteria. Examples:\n"
            "BEAT_US:       {\"format\": \"BO3\", \"must_win\": true}\n"
            "WIN_STREAK:    {\"streak_count\": 5, \"match_type\": \"RANKED\"}\n"
            "FIRST_BLOOD:   {\"task\": \"ace_round\", \"game\": \"VAL\"}\n"
            "TOURNAMENT_WIN:{\"tournament_id\": \"uuid\"}\n"
            "CUSTOM:        {\"description\": \"Score 50 kills in a BR lobby\"}"
        )
    )

    # ── Reward ───────────────────────────────────────────────────────────
    REWARD_TYPE_CHOICES = [
        ('CP', 'Crown Points'),
        ('USD', 'Cash (USD)'),
        ('BADGE', 'Exclusive Badge'),
        ('GLORY', 'Glory / Reputation'),
    ]
    reward_type = models.CharField(
        max_length=10,
        choices=REWARD_TYPE_CHOICES,
        default='CP'
    )
    reward_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Reward value (0 for non-monetary rewards)"
    )
    reward_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Human-readable reward description"
    )

    # ── Limits ───────────────────────────────────────────────────────────
    max_claims = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of teams that can claim this bounty"
    )
    claim_count = models.PositiveIntegerField(
        default=0,
        help_text="Current number of successful claims"
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Bounty expiration date"
    )

    # ── Visibility ───────────────────────────────────────────────────────
    is_public = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # ── Metadata ─────────────────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='competition_bounties_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Economy / Escrow ─────────────────────────────────────────────────
    # Integer DC equivalent of reward_amount — used by the escrow engine.
    # reward_amount (Decimal) is kept for display/legacy purposes.
    reward_amount_dc = models.PositiveIntegerField(
        default=0,
        help_text="DeltaCoins locked in escrow by the bounty issuer. 0 = non-DC reward."
    )
    escrow_locked = models.BooleanField(
        default=False,
        help_text="True once the issuer's DC have been locked into escrow."
    )

    # ── Bounty Board ─────────────────────────────────────────────────────
    # When is_hitlist is True, this bounty acts as a skill-based team challenge
    # match.  Challenger teams pay challenger_entry_fee_dc per claim attempt.
    is_hitlist = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this bounty is published on the Bounty board."
    )
    challenger_entry_fee_dc = models.PositiveIntegerField(
        default=0,
        help_text="DC each challenger team locks per Bounty claim attempt."
    )

    # Audit trail link to issuer's reward lock transaction.
    issuer_lock_txn = models.ForeignKey(
        'economy.DeltaCrownTransaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        help_text="Issuer's escrow lock transaction (set when reward_amount_dc > 0)."
    )
    funded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        help_text="User whose personal wallet funded the bounty reward."
    )

    # ── Lobby Closure (UI: never rely on a generic countdown) ────────────
    CLOSURE_REASON_CHOICES = [
        ('', 'Not closed'),
        ('CLAIMED', 'Claimed — reward paid out'),
        ('CANCELLED_BY_ISSUER', 'Cancelled by issuer'),
        ('EXPIRED', 'Expired before claim'),
        ('ADMIN_VOID', 'Voided by admin'),
    ]
    closure_reason = models.CharField(
        max_length=24,
        choices=CLOSURE_REASON_CHOICES,
        blank=True,
        default='',
        db_index=True,
        help_text="Why the bounty closed. UI must surface this rather than a bare countdown."
    )
    closure_note = models.TextField(
        blank=True,
        default='',
        help_text="Free-form admin/system note for the closure (e.g. dispute outcome)."
    )

    # Managers — default excludes soft-deleted rows
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'competition_bounty'
        verbose_name = 'Bounty'
        verbose_name_plural = 'Bounties'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['issuer_team', 'status']),
            models.Index(fields=['game', 'status']),
            models.Index(fields=['bounty_type', 'status']),
            models.Index(fields=['-expires_at']),
        ]

    def __str__(self):
        return f"[{self.reference_code}] {self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = self._generate_reference_code()
        super().save(*args, **kwargs)

    def _generate_reference_code(self):
        short = self.game.short_code if self.game_id else 'GEN'
        suffix = uuid.uuid4().hex[:6].upper()
        return f"BN-{short}-{suffix}"

    @property
    def is_expired(self):
        if self.expires_at and self.status == 'ACTIVE':
            return timezone.now() > self.expires_at
        return False

    @property
    def is_claimable(self):
        return (
            self.status == 'ACTIVE'
            and not self.is_expired
            and self.claim_count < self.max_claims
        )

    def hitlist_ref_id(self, suffix: str = '') -> str:
        """Stable escrow reference_id for this Bounty.

        ``suffix`` allows per-side or per-claim distinction:
            ''            → issuer reward lock / settlement
            'issuer'      → issuer reward lock
            'claim:<pk>'  → challenger entry-fee lock for that claim
            'payout:<pk>' → settlement reference for a specific claim
        """
        base = f"HL-{self.reference_code}"
        return f"{base}_{suffix}" if suffix else base


class BountyClaim(SoftDeleteModel):
    """
    A team's claim against a bounty, with evidence and verification.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    bounty = models.ForeignKey(
        Bounty,
        on_delete=models.CASCADE,
        related_name='claims'
    )
    
    claiming_team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='competition_bounty_claims'
    )

    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('VERIFIED', 'Verified — Criteria met'),
        ('REJECTED', 'Rejected — Criteria not met'),
        ('PAID', 'Paid — Reward distributed'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )
    
    # Evidence
    evidence_url = models.URLField(max_length=500, blank=True)
    evidence_notes = models.TextField(blank=True)
    
    # Link to challenge/match if applicable
    challenge = models.ForeignKey(
        'competition.Challenge',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='competition_bounty_claims',
        help_text="Challenge that triggered this bounty claim"
    )
    match_report = models.ForeignKey(
        'competition.MatchReport',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='competition_bounty_claims'
    )

    # Meta
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='competition_bounty_claims_submitted'
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='competition_bounty_claims_verified'
    )
    
    claimed_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    # ── Bounty escrow audit ──────────────────────────────────────────────
    entry_fee_lock_txn = models.ForeignKey(
        'economy.DeltaCrownTransaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        help_text="Challenger's entry-fee lock transaction (Bounty board only)."
    )
    outcome_txn = models.ForeignKey(
        'economy.DeltaCrownTransaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        help_text="Settlement transaction — payout or refund — recorded on resolution."
    )
    funded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        help_text="User whose personal wallet funded the challenger entry fee."
    )
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        help_text="Match Room spawned when this Bounty claim was submitted."
    )

    # ── Closure (UI: never rely on a generic countdown) ──────────────────
    CLOSURE_REASON_CHOICES = [
        ('', 'Not closed'),
        ('VERIFIED_PAID', 'Challenger won — reward paid'),
        ('REJECTED', 'Challenger lost — entry fee forfeited'),
        ('VOIDED', 'Voided by admin'),
        ('EXPIRED', 'Expired before verification'),
    ]
    closure_reason = models.CharField(
        max_length=24,
        choices=CLOSURE_REASON_CHOICES,
        blank=True,
        default='',
        db_index=True,
        help_text="Why the claim closed.  UI surfaces this on the claim card."
    )
    closure_note = models.TextField(
        blank=True,
        default='',
        help_text="Free-form admin/system note for the claim closure."
    )

    class Meta:
        db_table = 'competition_bounty_claim'
        verbose_name = 'Bounty Claim'
        verbose_name_plural = 'Bounty Claims'
        ordering = ['-claimed_at']
        indexes = [
            models.Index(fields=['bounty', 'status']),
            models.Index(fields=['claiming_team', '-claimed_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['bounty', 'claiming_team'],
                name='unique_bounty_claim_per_team',
                condition=models.Q(status__in=['PENDING', 'VERIFIED']),
            ),
        ]

    def __str__(self):
        return f"{self.claiming_team.name} → {self.bounty.title} ({self.get_status_display()})"
