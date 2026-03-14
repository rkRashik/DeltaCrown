"""OAuth connection models for game passport integrations."""

from django.db import models


class GameOAuthConnection(models.Model):
    """
    OAuth token linkage for a single game passport.

    This is intentionally one-to-one with GameProfile so each passport can have
    at most one active provider connection in Phase 1.
    """

    class Provider(models.TextChoices):
        RIOT = "riot", "Riot Games"
        STEAM = "steam", "Steam"
        EPIC = "epic", "Epic Games"

    passport = models.OneToOneField(
        "user_profile.GameProfile",
        on_delete=models.CASCADE,
        related_name="oauth_connection",
        help_text="Linked game passport",
    )
    provider = models.CharField(
        max_length=32,
        choices=Provider.choices,
        db_index=True,
        help_text="OAuth provider name",
    )
    provider_account_id = models.CharField(
        max_length=191,
        db_index=True,
        help_text="Provider-side stable account identifier",
    )
    game_shard = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Provider shard/region identifier (for example ap, euw, na)",
    )

    access_token = models.TextField(blank=True, default="")
    refresh_token = models.TextField(blank=True, default="")
    token_type = models.CharField(max_length=32, blank=True, default="Bearer")
    scopes = models.TextField(blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profile_game_oauth_connection"
        verbose_name = "Game OAuth Connection"
        verbose_name_plural = "Game OAuth Connections"
        indexes = [
            models.Index(
                fields=["provider", "provider_account_id"],
                name="user_profil_provide_1e2e3a_idx",
            ),
            models.Index(
                fields=["passport", "provider"],
                name="user_profil_passpor_b3b121_idx",
            ),
        ]

    def __str__(self):
        return f"{self.provider} OAuth for passport {self.passport_id}"
