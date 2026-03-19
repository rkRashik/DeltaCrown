"""OAuth connection models for game passport integrations."""

from django.conf import settings
from django.db import models

from apps.user_profile.fields import EncryptedTextField


class ProviderAccount(models.Model):
    """
    A verified identity anchor for a single external provider account.

    One Steam64 ID maps to one ProviderAccount, which can then link to multiple
    GameProfiles (e.g., CS2 and Dota 2) via GameOAuthConnection rows.
    This replaces the old Phase 1 OneToOne model where each GameProfile
    had its own disconnected OAuth link.
    """

    class Provider(models.TextChoices):
        RIOT = "riot", "Riot Games"
        STEAM = "steam", "Steam"
        EPIC = "epic", "Epic Games"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_accounts",
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
        help_text="Stable provider-side account identifier (Steam64 ID, Riot PUUID, etc.)",
    )
    provider_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw verified provider profile data (persona_name, avatar, etc.).",
    )

    connected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profile_provider_account"
        verbose_name = "Provider Account"
        verbose_name_plural = "Provider Accounts"
        unique_together = [("provider", "provider_account_id")]
        indexes = [
            models.Index(
                fields=["user", "provider"],
                name="user_profil_prov_user_prov_idx",
            ),
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_account_id} (user={self.user_id})"


class GameOAuthConnection(models.Model):
    """
    M2M link between a ProviderAccount and a GameProfile.

    One Steam ProviderAccount creates two rows here — one pointing at the CS2
    GameProfile and one pointing at the Dota 2 GameProfile.
    """

    class Provider(models.TextChoices):
        RIOT = "riot", "Riot Games"
        STEAM = "steam", "Steam"
        EPIC = "epic", "Epic Games"

    # ── Phase 2 fields (authoritative) ──────────────────────────────────
    provider_account = models.ForeignKey(
        ProviderAccount,
        on_delete=models.CASCADE,
        related_name="game_connections",
        null=True,
        blank=True,
        help_text="Provider identity anchor",
    )
    game_profile = models.ForeignKey(
        "user_profile.GameProfile",
        on_delete=models.CASCADE,
        related_name="oauth_connections",
        null=True,
        blank=True,
        help_text="Linked game passport (Phase 2+)",
    )

    # ── Phase 1 legacy field — kept nullable for migration compatibility ─
    passport = models.OneToOneField(
        "user_profile.GameProfile",
        on_delete=models.SET_NULL,
        related_name="oauth_connection",
        null=True,
        blank=True,
        help_text="DEPRECATED — use game_profile. Kept nullable for backward compatibility.",
    )

    provider = models.CharField(
        max_length=32,
        choices=Provider.choices,
        db_index=True,
        help_text="OAuth provider name (denormalized from ProviderAccount for fast filtering)",
    )
    game_shard = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Provider shard/region identifier (for example ap, euw, na)",
    )

    access_token = EncryptedTextField(blank=True, default="")
    refresh_token = EncryptedTextField(blank=True, default="")
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
        constraints = [
            models.UniqueConstraint(
                fields=["provider_account", "game_profile"],
                condition=models.Q(
                    provider_account__isnull=False,
                    game_profile__isnull=False,
                ),
                name="user_profil_prov_game_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["provider", "provider_account_id"],
                name="user_profil_provide_1e2e3a_idx",
            ),
        ]

    def __str__(self):
        pa_id = self.provider_account.provider_account_id if self.provider_account_id else None
        if pa_id:
            return f"{self.provider} → {pa_id}"
        return f"{self.provider} OAuth (legacy passport {self.passport_id})"
