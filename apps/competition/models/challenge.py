"""
Challenge model — Team vs Team competitive challenge system.

Supports all 11 games across 4 game categories:
  FPS  (VAL, CS2, CODM, R6)  → Map-based BO series
  MOBA (DOTA, MLBB)          → BO series
  BR   (PUBGM, FF)           → Placement/kill-based scoring
  SPORTS (FC26, EFB, RL)     → Direct match / BO series, 1v1 or team

Challenge lifecycle:
  OPEN → ACCEPTED → SCHEDULED → IN_PROGRESS → COMPLETED → SETTLED
                  → DECLINED
                  → EXPIRED (auto after deadline)
                  → CANCELLED (by issuer before accept)
                  → DISPUTED → ADMIN_RESOLVED
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid


class Challenge(models.Model):
    """
    A competitive challenge between two teams for a specific game.
    
    The challenger_team issues the challenge; the challenged_team accepts/declines.
    Optionally includes a prize (Crown Points or USD wager) and custom
    game-specific format settings.
    """

    # ── Identifiers ──────────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Human-readable reference code (auto-generated)
    reference_code = models.CharField(
        max_length=16,
        unique=True,
        db_index=True,
        help_text="Short reference code, e.g. 'CH-VAL-A1B2C3'"
    )

    # ── Teams ────────────────────────────────────────────────────────────
    challenger_team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='competition_challenges_issued',
        help_text="Team that created and issued the challenge"
    )
    challenged_team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='competition_challenges_received',
        null=True,
        blank=True,
        help_text="Specific team challenged (null = open challenge)"
    )

    # ── Game ─────────────────────────────────────────────────────────────
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.PROTECT,
        related_name='competition_challenges',
        help_text="Game this challenge is played in"
    )

    # ── Status ───────────────────────────────────────────────────────────
    STATUS_CHOICES = [
        ('OPEN', 'Open — Awaiting opponent'),
        ('ACCEPTED', 'Accepted — Awaiting schedule'),
        ('SCHEDULED', 'Scheduled — Match time set'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed — Result submitted'),
        ('SETTLED', 'Settled — Result verified & rewards distributed'),
        ('DECLINED', 'Declined by opponent'),
        ('EXPIRED', 'Expired — Deadline passed'),
        ('CANCELLED', 'Cancelled by issuer'),
        ('DISPUTED', 'Disputed — Requires admin review'),
        ('ADMIN_RESOLVED', 'Admin Resolved'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='OPEN',
        db_index=True
    )

    # ── Challenge Type ───────────────────────────────────────────────────
    CHALLENGE_TYPE_CHOICES = [
        ('DIRECT', 'Direct Challenge — Named opponent'),
        ('OPEN', 'Open Challenge — Any team can accept'),
        ('RANKED', 'Ranked Challenge — Affects rankings'),
        ('WAGER', 'Wager Match — Prize pool at stake'),
        ('SCRIM', 'Scrim / Practice — No ranking impact'),
    ]
    challenge_type = models.CharField(
        max_length=20,
        choices=CHALLENGE_TYPE_CHOICES,
        default='DIRECT'
    )

    # ── Format / Rules ───────────────────────────────────────────────────
    BEST_OF_CHOICES = [
        (1, 'BO1 — Single game'),
        (3, 'BO3 — Best of 3'),
        (5, 'BO5 — Best of 5'),
        (7, 'BO7 — Best of 7'),
    ]
    best_of = models.PositiveSmallIntegerField(
        choices=BEST_OF_CHOICES,
        default=1,
        help_text="Series format (BO1/BO3/BO5/BO7)"
    )

    # Game-specific configuration (maps, mode, ruleset)
    game_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Game-specific format settings. Examples:\n"
            "FPS:    {\"map_pool\": [\"Ascent\", \"Bind\"], \"map_pick_ban\": true, \"overtime\": true}\n"
            "MOBA:   {\"pick_mode\": \"DRAFT\", \"ban_count\": 5}\n"
            "BR:     {\"scoring\": \"KILL_RACE\", \"num_rounds\": 3, \"placement_points\": true}\n"
            "SPORTS: {\"half_length\": 6, \"extra_time\": true}"
        )
    )

    # Platform / server requirements
    platform = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text="Required platform: PC, Mobile, Console, or blank for any"
    )
    server_region = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text="Preferred server region (e.g., 'NA-East', 'EU-West', 'SEA')"
    )

    # ── Prize / Wager ────────────────────────────────────────────────────
    PRIZE_TYPE_CHOICES = [
        ('NONE', 'No Prize'),
        ('CP', 'Crown Points'),
        ('USD', 'Cash (USD)'),
        ('GLORY', 'Glory / Bragging Rights'),
    ]
    prize_type = models.CharField(
        max_length=10,
        choices=PRIZE_TYPE_CHOICES,
        default='NONE'
    )
    prize_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Prize value (0 for no-prize challenges)"
    )
    prize_description = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional human-readable prize description"
    )

    # ── Content ──────────────────────────────────────────────────────────
    title = models.CharField(
        max_length=120,
        help_text="Challenge headline (e.g., 'Weekly Duel — BO3 Ascent')"
    )
    description = models.TextField(
        blank=True,
        help_text="Rules, trash talk, or additional context"
    )
    
    # ── Scheduling ───────────────────────────────────────────────────────
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the match is scheduled to take place"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Deadline to accept the challenge"
    )

    # ── Result ───────────────────────────────────────────────────────────
    RESULT_CHOICES = [
        ('PENDING', 'Pending'),
        ('CHALLENGER_WIN', 'Challenger won'),
        ('CHALLENGED_WIN', 'Challenged team won'),
        ('DRAW', 'Draw'),
        ('FORFEIT_CHALLENGER', 'Forfeit by challenger'),
        ('FORFEIT_CHALLENGED', 'Forfeit by challenged'),
        ('NO_SHOW', 'No-show — Neither team appeared'),
    ]
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        default='PENDING'
    )
    
    # Per-game scores (e.g., {"game_1": {"challenger": 13, "challenged": 7}, ...})
    score_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed per-game/round scores"
    )

    # Link to MatchReport(s) created from this challenge
    match_report = models.ForeignKey(
        'competition.MatchReport',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='competition_challenge_source',
        help_text="Generated MatchReport for ranking integration"
    )

    # ── Evidence ─────────────────────────────────────────────────────────
    evidence_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Screenshot, VOD, or match history link"
    )

    # ── Participants / Actions ───────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='competition_challenges_created',
        help_text="User who created the challenge"
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='competition_challenges_accepted',
        help_text="User who accepted on behalf of challenged team"
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='competition_challenges_resolved',
        help_text="Admin who resolved a dispute"
    )

    # ── Metadata ─────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    # ── Visibility ───────────────────────────────────────────────────────
    is_public = models.BooleanField(
        default=True,
        help_text="Whether this challenge appears in public feeds"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Staff-promoted highlight challenge"
    )

    class Meta:
        db_table = 'competition_challenge'
        verbose_name = 'Challenge'
        verbose_name_plural = 'Challenges'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['challenger_team', 'status']),
            models.Index(fields=['challenged_team', 'status']),
            models.Index(fields=['game', 'status', '-created_at']),
            models.Index(fields=['challenge_type', 'status']),
            models.Index(fields=['-expires_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(challenger_team=models.F('challenged_team')),
                name='challenge_teams_different',
            ),
        ]

    def __str__(self):
        opponent = self.challenged_team.name if self.challenged_team else 'OPEN'
        return f"[{self.reference_code}] {self.challenger_team.name} vs {opponent} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = self._generate_reference_code()
        super().save(*args, **kwargs)

    def _generate_reference_code(self):
        """Generate a short unique reference like CH-VAL-A1B2C3."""
        short = self.game.short_code if self.game_id else 'GEN'
        suffix = uuid.uuid4().hex[:6].upper()
        return f"CH-{short}-{suffix}"

    @property
    def is_expired(self):
        if self.expires_at and self.status == 'OPEN':
            return timezone.now() > self.expires_at
        return False

    @property
    def is_open_challenge(self):
        return self.challenged_team is None and self.status == 'OPEN'

    @property
    def winner(self):
        if self.result == 'CHALLENGER_WIN':
            return self.challenger_team
        elif self.result == 'CHALLENGED_WIN':
            return self.challenged_team
        return None

    @property
    def loser(self):
        if self.result == 'CHALLENGER_WIN':
            return self.challenged_team
        elif self.result == 'CHALLENGED_WIN':
            return self.challenger_team
        return None

    def get_game_type(self):
        """Convenience: returns game.game_type (TEAM_VS_TEAM / 1V1 / BATTLE_ROYALE / FREE_FOR_ALL)."""
        return self.game.game_type if self.game else None

    def get_default_format(self):
        """
        Return sensible defaults for game_config based on game category.
        
        FPS:    Map pick/ban BO1-BO5, maps from game config
        MOBA:   Draft mode BO1-BO3
        BR:     Kill race or placement, multi-round
        SPORTS: Direct match, regulation time
        """
        category = self.game.category if self.game else 'OTHER'
        defaults = {
            'FPS': {
                'map_pick_ban': True,
                'map_pool': [],
                'overtime': True,
                'knife_round': False,
            },
            'MOBA': {
                'pick_mode': 'DRAFT',
                'ban_count': 5,
                'all_chat': False,
            },
            'BR': {
                'scoring': 'KILL_RACE',
                'num_rounds': 3,
                'placement_points': True,
                'kill_points': 1,
                'placement_scale': [15, 12, 10, 8, 6, 5, 4, 3, 2, 1],
            },
            'SPORTS': {
                'half_length': 6,
                'extra_time': True,
                'penalties': True,
            },
            'FIGHTING': {
                'first_to': 3,
                'character_lock': False,
            },
        }
        return defaults.get(category, {})
