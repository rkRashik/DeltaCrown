from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0036_oauth_provider_steam_support"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gameoauthconnection",
            name="provider",
            field=models.CharField(
                choices=[("riot", "Riot Games"), ("steam", "Steam"), ("epic", "Epic Games")],
                db_index=True,
                help_text="OAuth provider name",
                max_length=32,
            ),
        ),
    ]