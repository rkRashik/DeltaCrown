"""
GameMapPool — database-driven map pools per game.

Replaces the hardcoded DEFAULT_MAP_POOLS dict in match_room.py.
Each game can have multiple maps with ordering, active/inactive state,
and optional image assets.
"""

from django.db import models


class GameMapPool(models.Model):
    """A single map entry in a game's map pool."""

    game = models.ForeignKey(
        "games.Game",
        on_delete=models.CASCADE,
        related_name="map_pool",
        help_text="The game this map belongs to",
    )
    map_name = models.CharField(
        max_length=100,
        help_text="Display name of the map (e.g. 'Ascent', 'Mirage')",
    )
    map_code = models.SlugField(
        max_length=100,
        help_text="Internal code/slug for the map",
    )
    image = models.ImageField(
        upload_to="games/maps/",
        blank=True,
        null=True,
        help_text="Optional map thumbnail",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this map is in the current active pool",
    )
    is_competitive = models.BooleanField(
        default=True,
        help_text="Whether this map is in the competitive rotation",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the pool",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "games_map_pool"
        ordering = ["game", "order", "map_name"]
        unique_together = [["game", "map_code"]]
        verbose_name = "Game Map Pool Entry"
        verbose_name_plural = "Game Map Pool Entries"
        indexes = [
            models.Index(fields=["game", "is_active", "order"]),
        ]

    def __str__(self):
        status = "active" if self.is_active else "inactive"
        return f"{self.game.slug}: {self.map_name} ({status})"

    @classmethod
    def get_active_maps(cls, game) -> list:
        """Return active map names for a game, ordered by display order."""
        return list(
            cls.objects.filter(game=game, is_active=True)
            .order_by("order", "map_name")
            .values_list("map_name", flat=True)
        )

    @classmethod
    def get_active_maps_by_slug(cls, game_slug: str) -> list:
        """Return active map names for a game slug."""
        return list(
            cls.objects.filter(game__slug=game_slug, is_active=True)
            .order_by("order", "map_name")
            .values_list("map_name", flat=True)
        )
