# apps/teams/models/game_specific.py
"""
Concrete game-specific team and membership models.

Each game gets its own Team and PlayerMembership model that extends
the base classes with game-specific constraints and behaviors.
"""
from django.db import models
from django.core.exceptions import ValidationError

from .base import BaseTeam, BasePlayerMembership
from ..game_config import get_game_config, GAME_CONFIGS


# ═══════════════════════════════════════════════════════════════════════════
# VALORANT
# ═══════════════════════════════════════════════════════════════════════════

class ValorantTeam(BaseTeam):
    """Valorant-specific team model."""
    
    game = models.CharField(
        max_length=20,
        default="valorant",
        editable=False
    )
    
    # Valorant-specific fields
    average_rank = models.CharField(
        max_length=50,
        blank=True,
        help_text="Team average competitive rank"
    )
    
    class Meta:
        db_table = "teams_valorant_team"
        verbose_name = "Valorant Team"
        verbose_name_plural = "Valorant Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="unique_valorant_team_slug"
            ),
            models.UniqueConstraint(
                fields=["game", "name"],
                name="unique_valorant_team_name"
            ),
        ]
    
    def get_memberships(self):
        return self.valorant_memberships.all()


class ValorantPlayerMembership(BasePlayerMembership):
    """Valorant player membership."""
    
    team = models.ForeignKey(
        ValorantTeam,
        on_delete=models.CASCADE,
        related_name="valorant_memberships"
    )
    
    # Valorant-specific fields
    agent_pool = models.JSONField(
        default=list,
        blank=True,
        help_text="List of agents this player uses"
    )
    competitive_rank = models.CharField(
        max_length=50,
        blank=True,
        help_text="Player's competitive rank"
    )
    
    class Meta:
        db_table = "teams_valorant_membership"
        verbose_name = "Valorant Player"
        verbose_name_plural = "Valorant Players"
        unique_together = [("team", "profile")]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(is_captain=True, status="ACTIVE"),
                name="one_captain_per_valorant_team"
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# CS2 / CSGO
# ═══════════════════════════════════════════════════════════════════════════

class CS2Team(BaseTeam):
    """Counter-Strike 2 team model."""
    
    game = models.CharField(
        max_length=20,
        default="cs2",
        editable=False
    )
    
    class Meta:
        db_table = "teams_cs2_team"
        verbose_name = "CS2 Team"
        verbose_name_plural = "CS2 Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="unique_cs2_team_slug"
            ),
        ]
    
    def get_memberships(self):
        return self.cs2_memberships.all()


class CS2PlayerMembership(BasePlayerMembership):
    """CS2 player membership."""
    
    team = models.ForeignKey(
        CS2Team,
        on_delete=models.CASCADE,
        related_name="cs2_memberships"
    )
    
    faceit_elo = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="FaceIT ELO rating"
    )
    
    class Meta:
        db_table = "teams_cs2_membership"
        unique_together = [("team", "profile")]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(is_captain=True, status="ACTIVE"),
                name="one_captain_per_cs2_team"
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# DOTA 2
# ═══════════════════════════════════════════════════════════════════════════

class Dota2Team(BaseTeam):
    """Dota 2 team model."""
    
    game = models.CharField(
        max_length=20,
        default="dota2",
        editable=False
    )
    
    class Meta:
        db_table = "teams_dota2_team"
        verbose_name = "Dota 2 Team"
        verbose_name_plural = "Dota 2 Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="unique_dota2_team_slug"
            ),
        ]
    
    def get_memberships(self):
        return self.dota2_memberships.all()


class Dota2PlayerMembership(BasePlayerMembership):
    """Dota 2 player membership with position uniqueness."""
    
    team = models.ForeignKey(
        Dota2Team,
        on_delete=models.CASCADE,
        related_name="dota2_memberships"
    )
    
    mmr = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Matchmaking rating"
    )
    
    class Meta:
        db_table = "teams_dota2_membership"
        unique_together = [("team", "profile")]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(is_captain=True, status="ACTIVE"),
                name="one_captain_per_dota2_team"
            ),
            # Enforce unique positions for starters
            models.UniqueConstraint(
                fields=["team", "role"],
                condition=models.Q(status="ACTIVE", is_starter=True),
                name="unique_dota2_position_per_team"
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# MOBILE LEGENDS: BANG BANG
# ═══════════════════════════════════════════════════════════════════════════

class MLBBTeam(BaseTeam):
    """MLBB team model."""
    
    game = models.CharField(
        max_length=20,
        default="mlbb",
        editable=False
    )
    
    class Meta:
        db_table = "teams_mlbb_team"
        verbose_name = "MLBB Team"
        verbose_name_plural = "MLBB Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="unique_mlbb_team_slug"
            ),
        ]
    
    def get_memberships(self):
        return self.mlbb_memberships.all()


class MLBBPlayerMembership(BasePlayerMembership):
    """MLBB player membership."""
    
    team = models.ForeignKey(
        MLBBTeam,
        on_delete=models.CASCADE,
        related_name="mlbb_memberships"
    )
    
    server = models.CharField(
        max_length=50,
        blank=True,
        help_text="Game server (e.g., Asia, NA)"
    )
    
    class Meta:
        db_table = "teams_mlbb_membership"
        unique_together = [("team", "profile")]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(is_captain=True, status="ACTIVE"),
                name="one_captain_per_mlbb_team"
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# PUBG MOBILE
# ═══════════════════════════════════════════════════════════════════════════

class PUBGTeam(BaseTeam):
    """PUBG Mobile team model."""
    
    game = models.CharField(
        max_length=20,
        default="pubg",
        editable=False
    )
    
    class Meta:
        db_table = "teams_pubg_team"
        verbose_name = "PUBG Team"
        verbose_name_plural = "PUBG Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="unique_pubg_team_slug"
            ),
        ]
    
    def get_memberships(self):
        return self.pubg_memberships.all()


class PUBGPlayerMembership(BasePlayerMembership):
    """PUBG player membership."""
    
    team = models.ForeignKey(
        PUBGTeam,
        on_delete=models.CASCADE,
        related_name="pubg_memberships"
    )
    
    tier = models.CharField(
        max_length=50,
        blank=True,
        help_text="Player tier/rank"
    )
    
    class Meta:
        db_table = "teams_pubg_membership"
        unique_together = [("team", "profile")]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(is_captain=True, status="ACTIVE"),
                name="one_captain_per_pubg_team"
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# FREE FIRE
# ═══════════════════════════════════════════════════════════════════════════

class FreeFireTeam(BaseTeam):
    """Free Fire team model."""
    
    game = models.CharField(
        max_length=20,
        default="freefire",
        editable=False
    )
    
    class Meta:
        db_table = "teams_freefire_team"
        verbose_name = "Free Fire Team"
        verbose_name_plural = "Free Fire Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="unique_freefire_team_slug"
            ),
        ]
    
    def get_memberships(self):
        return self.freefire_memberships.all()


class FreeFirePlayerMembership(BasePlayerMembership):
    """Free Fire player membership."""
    
    team = models.ForeignKey(
        FreeFireTeam,
        on_delete=models.CASCADE,
        related_name="freefire_memberships"
    )
    
    class Meta:
        db_table = "teams_freefire_membership"
        unique_together = [("team", "profile")]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(is_captain=True, status="ACTIVE"),
                name="one_captain_per_freefire_team"
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# EFOOTBALL
# ═══════════════════════════════════════════════════════════════════════════

class EFootballTeam(BaseTeam):
    """eFootball team model (1-2 players)."""
    
    game = models.CharField(
        max_length=20,
        default="efootball",
        editable=False
    )
    
    class Meta:
        db_table = "teams_efootball_team"
        verbose_name = "eFootball Team"
        verbose_name_plural = "eFootball Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="unique_efootball_team_slug"
            ),
        ]
    
    def get_memberships(self):
        return self.efootball_memberships.all()


class EFootballPlayerMembership(BasePlayerMembership):
    """eFootball player membership."""
    
    team = models.ForeignKey(
        EFootballTeam,
        on_delete=models.CASCADE,
        related_name="efootball_memberships"
    )
    
    platform = models.CharField(
        max_length=50,
        blank=True,
        help_text="Gaming platform (PC, PS5, Xbox, Mobile)"
    )
    
    class Meta:
        db_table = "teams_efootball_membership"
        unique_together = [("team", "profile")]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(is_captain=True, status="ACTIVE"),
                name="one_captain_per_efootball_team"
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# FC 26
# ═══════════════════════════════════════════════════════════════════════════

class FC26Team(BaseTeam):
    """FC 26 team model (solo player)."""
    
    game = models.CharField(
        max_length=20,
        default="fc26",
        editable=False
    )
    
    class Meta:
        db_table = "teams_fc26_team"
        verbose_name = "FC 26 Team"
        verbose_name_plural = "FC 26 Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="unique_fc26_team_slug"
            ),
        ]
    
    def get_memberships(self):
        return self.fc26_memberships.all()


class FC26PlayerMembership(BasePlayerMembership):
    """FC 26 player membership."""
    
    team = models.ForeignKey(
        FC26Team,
        on_delete=models.CASCADE,
        related_name="fc26_memberships"
    )
    
    platform = models.CharField(
        max_length=50,
        blank=True,
        help_text="Gaming platform"
    )
    
    class Meta:
        db_table = "teams_fc26_membership"
        unique_together = [("team", "profile")]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(is_captain=True, status="ACTIVE"),
                name="one_captain_per_fc26_team"
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# CALL OF DUTY MOBILE
# ═══════════════════════════════════════════════════════════════════════════

class CODMTeam(BaseTeam):
    """Call of Duty Mobile team model."""
    
    game = models.CharField(
        max_length=20,
        default="codm",
        editable=False
    )
    
    class Meta:
        db_table = "teams_codm_team"
        verbose_name = "COD Mobile Team"
        verbose_name_plural = "COD Mobile Teams"
        constraints = [
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="unique_codm_team_slug"
            ),
        ]
    
    def get_memberships(self):
        return self.codm_memberships.all()


class CODMPlayerMembership(BasePlayerMembership):
    """CODM player membership."""
    
    team = models.ForeignKey(
        CODMTeam,
        on_delete=models.CASCADE,
        related_name="codm_memberships"
    )
    
    rank = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ranked mode tier"
    )
    
    class Meta:
        db_table = "teams_codm_membership"
        unique_together = [("team", "profile")]
        constraints = [
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(is_captain=True, status="ACTIVE"),
                name="one_captain_per_codm_team"
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# MODEL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════

GAME_TEAM_MODELS = {
    "valorant": ValorantTeam,
    "cs2": CS2Team,
    "dota2": Dota2Team,
    "mlbb": MLBBTeam,
    "pubg": PUBGTeam,
    "freefire": FreeFireTeam,
    "efootball": EFootballTeam,
    "fc26": FC26Team,
    "codm": CODMTeam,
}

GAME_MEMBERSHIP_MODELS = {
    "valorant": ValorantPlayerMembership,
    "cs2": CS2PlayerMembership,
    "dota2": Dota2PlayerMembership,
    "mlbb": MLBBPlayerMembership,
    "pubg": PUBGPlayerMembership,
    "freefire": FreeFirePlayerMembership,
    "efootball": EFootballPlayerMembership,
    "fc26": FC26PlayerMembership,
    "codm": CODMPlayerMembership,
}


def get_team_model_for_game(game_code: str):
    """Get the team model class for a specific game."""
    if game_code not in GAME_TEAM_MODELS:
        raise ValueError(f"No team model found for game: {game_code}")
    return GAME_TEAM_MODELS[game_code]


def get_membership_model_for_game(game_code: str):
    """Get the membership model class for a specific game."""
    if game_code not in GAME_MEMBERSHIP_MODELS:
        raise ValueError(f"No membership model found for game: {game_code}")
    return GAME_MEMBERSHIP_MODELS[game_code]
