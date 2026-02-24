"""
TOC Sprint 8 — Game Configuration & Rulebook Models

§8.1  GameMatchConfig   — default match format, scoring rules per game
§8.2  MapPoolEntry      — map pool management with ordering
§8.3  MatchVetoSession  — ban/pick veto flow per match
§8.5  ServerRegion      — available server regions with ping endpoints
§8.6  RulebookVersion   — versioned rulebook with publish workflow
§8.7  RulebookConsent   — per-user consent tracking for rulebook versions
§8.10 BRScoringMatrix   — Battle Royale scoring (placement + kill points)
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# S8-M1: GameMatchConfig
# ---------------------------------------------------------------------------

class GameMatchConfig(models.Model):
    """
    Per-tournament game configuration: default match format, map pool,
    scoring rules, and integration settings.
    """

    class MatchFormat(models.TextChoices):
        BEST_OF_1 = "bo1", _("Best of 1")
        BEST_OF_3 = "bo3", _("Best of 3")
        BEST_OF_5 = "bo5", _("Best of 5")
        BEST_OF_7 = "bo7", _("Best of 7")
        ROUND_ROBIN = "rr", _("Round Robin")
        FFA = "ffa", _("Free for All")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="game_match_config",
        verbose_name=_("Tournament"),
    )
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match_configs",
        verbose_name=_("Game"),
    )

    default_match_format = models.CharField(
        max_length=10,
        choices=MatchFormat.choices,
        default=MatchFormat.BEST_OF_1,
        verbose_name=_("Default Match Format"),
    )

    # Free-form JSON blob for game-specific scoring rules
    scoring_rules = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Scoring Rules"),
        help_text=_("Game-specific scoring configuration (JSON)."),
    )

    # General match settings stored as JSON for flexibility
    match_settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Match Settings"),
        help_text=_("Overtime rules, map rotation, side-swap, etc."),
    )

    enable_veto = models.BooleanField(
        default=False,
        verbose_name=_("Enable Map/Ban Veto"),
    )
    veto_type = models.CharField(
        max_length=30,
        choices=[
            ("standard", _("Standard Ban/Pick")),
            ("blind_pick", _("Blind Pick")),
            ("captain_draft", _("Captain Draft")),
        ],
        default="standard",
        blank=True,
        verbose_name=_("Veto Type"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "toc_game_match_config"
        verbose_name = _("Game Match Config")
        verbose_name_plural = _("Game Match Configs")

    def __str__(self):
        return f"Config — {self.tournament}"


# ---------------------------------------------------------------------------
# S8-M2: MapPoolEntry
# ---------------------------------------------------------------------------

class MapPoolEntry(models.Model):
    """
    Single map inside a tournament's map pool. Ordered, toggleable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    config = models.ForeignKey(
        GameMatchConfig,
        on_delete=models.CASCADE,
        related_name="map_pool",
        verbose_name=_("Game Config"),
    )

    map_name = models.CharField(max_length=120, verbose_name=_("Map Name"))
    map_code = models.CharField(
        max_length=60,
        blank=True,
        default="",
        verbose_name=_("Map Code"),
        help_text=_("Internal/game code for the map."),
    )
    image = models.URLField(
        blank=True,
        default="",
        verbose_name=_("Map Image URL"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Order"))

    class Meta:
        db_table = "toc_map_pool_entry"
        verbose_name = _("Map Pool Entry")
        verbose_name_plural = _("Map Pool Entries")
        ordering = ["order", "map_name"]
        unique_together = [("config", "map_name")]

    def __str__(self):
        return f"{self.map_name} (#{self.order})"


# ---------------------------------------------------------------------------
# S8-M3: MatchVetoSession
# ---------------------------------------------------------------------------

class MatchVetoSession(models.Model):
    """
    Tracks a live ban/pick veto sequence for a match.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        IN_PROGRESS = "in_progress", _("In Progress")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    match = models.OneToOneField(
        "tournaments.Match",
        on_delete=models.CASCADE,
        related_name="veto_session",
        verbose_name=_("Match"),
    )
    veto_type = models.CharField(
        max_length=30,
        default="standard",
        verbose_name=_("Veto Type"),
    )

    # Sequence definition: [{"action":"ban","team":"A"},{"action":"pick","team":"B"}, ...]
    sequence = models.JSONField(
        default=list, blank=True,
        verbose_name=_("Veto Sequence"),
    )
    # Completed picks: [{"step":0,"action":"ban","team":"A","map":"Dust2"}, ...]
    picks = models.JSONField(
        default=list, blank=True,
        verbose_name=_("Picks"),
    )

    current_step = models.PositiveIntegerField(default=0, verbose_name=_("Current Step"))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status"),
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "toc_match_veto_session"
        verbose_name = _("Match Veto Session")
        verbose_name_plural = _("Match Veto Sessions")

    def __str__(self):
        return f"Veto — Match {self.match_id} ({self.status})"


# ---------------------------------------------------------------------------
# S8-M4: ServerRegion
# ---------------------------------------------------------------------------

class ServerRegion(models.Model):
    """
    Available server regions for match hosting.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="server_regions",
        verbose_name=_("Tournament"),
    )

    name = models.CharField(max_length=100, verbose_name=_("Region Name"))
    code = models.CharField(
        max_length=20,
        verbose_name=_("Region Code"),
        help_text=_('e.g. "us-east", "eu-west"'),
    )
    ping_endpoint = models.URLField(
        blank=True,
        default="",
        verbose_name=_("Ping Endpoint"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        db_table = "toc_server_region"
        verbose_name = _("Server Region")
        verbose_name_plural = _("Server Regions")
        ordering = ["name"]
        unique_together = [("tournament", "code")]

    def __str__(self):
        return f"{self.name} ({self.code})"


# ---------------------------------------------------------------------------
# S8-M5: RulebookVersion
# ---------------------------------------------------------------------------

class RulebookVersion(models.Model):
    """
    Versioned tournament rulebook with publish/draft workflow.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="rulebook_versions",
        verbose_name=_("Tournament"),
    )

    version = models.CharField(
        max_length=30,
        verbose_name=_("Version"),
        help_text=_('e.g. "1.0", "2.1-draft"'),
    )
    content = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Content"),
        help_text=_("Markdown or HTML content of the rulebook."),
    )
    changelog = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Changelog"),
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name=_("Active / Published"),
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        db_table = "toc_rulebook_version"
        verbose_name = _("Rulebook Version")
        verbose_name_plural = _("Rulebook Versions")
        ordering = ["-created_at"]
        unique_together = [("tournament", "version")]

    def publish(self):
        """Deactivate other versions and publish this one."""
        RulebookVersion.objects.filter(
            tournament=self.tournament, is_active=True,
        ).update(is_active=False)
        self.is_active = True
        self.published_at = timezone.now()
        self.save(update_fields=["is_active", "published_at"])

    def __str__(self):
        tag = " [ACTIVE]" if self.is_active else ""
        return f"Rulebook v{self.version}{tag} — {self.tournament}"


# ---------------------------------------------------------------------------
# S8-M6: RulebookConsent
# ---------------------------------------------------------------------------

class RulebookConsent(models.Model):
    """
    Tracks individual user consent to a specific rulebook version.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rulebook_consents",
        verbose_name=_("User"),
    )
    rulebook_version = models.ForeignKey(
        RulebookVersion,
        on_delete=models.CASCADE,
        related_name="consents",
        verbose_name=_("Rulebook Version"),
    )
    consented_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "toc_rulebook_consent"
        verbose_name = _("Rulebook Consent")
        verbose_name_plural = _("Rulebook Consents")
        unique_together = [("user", "rulebook_version")]

    def __str__(self):
        return f"{self.user} consented to {self.rulebook_version}"


# ---------------------------------------------------------------------------
# S8-M7: BRScoringMatrix
# ---------------------------------------------------------------------------

class BRScoringMatrix(models.Model):
    """
    Battle Royale scoring configuration — placement + kill points.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    config = models.OneToOneField(
        GameMatchConfig,
        on_delete=models.CASCADE,
        related_name="br_scoring",
        verbose_name=_("Game Config"),
    )

    # e.g. {1: 25, 2: 20, 3: 16, ...}
    placement_points = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Placement Points"),
        help_text=_("Map of placement position → points."),
    )

    kill_points = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=1,
        verbose_name=_("Points per Kill"),
    )

    # Optional tiebreaker rules
    tiebreaker_rules = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Tiebreaker Rules"),
        help_text=_("Ordered list of tiebreaker criteria."),
    )

    class Meta:
        db_table = "toc_br_scoring_matrix"
        verbose_name = _("BR Scoring Matrix")
        verbose_name_plural = _("BR Scoring Matrices")

    def __str__(self):
        return f"BR Scoring — {self.config.tournament}"
