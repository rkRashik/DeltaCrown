from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0034_alter_verificationrecord_id_document_back_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="GameOAuthConnection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        choices=[("RIOT", "Riot Games")],
                        db_index=True,
                        help_text="OAuth provider name",
                        max_length=32,
                    ),
                ),
                (
                    "provider_account_id",
                    models.CharField(
                        db_index=True,
                        help_text="Provider-side stable account identifier",
                        max_length=191,
                    ),
                ),
                (
                    "game_shard",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Provider shard/region identifier (for example ap, euw, na)",
                        max_length=32,
                    ),
                ),
                ("access_token", models.TextField(blank=True, default="")),
                ("refresh_token", models.TextField(blank=True, default="")),
                (
                    "token_type",
                    models.CharField(blank=True, default="Bearer", max_length=32),
                ),
                ("scopes", models.TextField(blank=True, default="")),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("connected_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "passport",
                    models.OneToOneField(
                        help_text="Linked game passport",
                        on_delete=models.deletion.CASCADE,
                        related_name="oauth_connection",
                        to="user_profile.gameprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "Game OAuth Connection",
                "verbose_name_plural": "Game OAuth Connections",
                "db_table": "user_profile_game_oauth_connection",
                "indexes": [
                    models.Index(
                        fields=["provider", "provider_account_id"],
                        name="user_profil_provide_1e2e3a_idx",
                    ),
                    models.Index(
                        fields=["passport", "provider"],
                        name="user_profil_passpor_b3b121_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("provider", "provider_account_id"),
                        name="uniq_game_oauth_provider_account",
                    )
                ],
            },
        ),
    ]
