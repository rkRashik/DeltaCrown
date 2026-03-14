from django.db import migrations, models


def normalize_oauth_provider_values(apps, schema_editor):
    GameOAuthConnection = apps.get_model("user_profile", "GameOAuthConnection")
    GameOAuthConnection.objects.filter(provider="RIOT").update(provider="riot")


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0035_gameoauthconnection"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="gameoauthconnection",
            name="uniq_game_oauth_provider_account",
        ),
        migrations.AlterField(
            model_name="gameoauthconnection",
            name="provider",
            field=models.CharField(
                choices=[("riot", "Riot Games"), ("steam", "Steam")],
                db_index=True,
                help_text="OAuth provider name",
                max_length=32,
            ),
        ),
        migrations.RunPython(normalize_oauth_provider_values, noop_reverse),
    ]
