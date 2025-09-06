
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("teams", "0004_team_game"),
    ]

    operations = [
        # Team media & socials & slug
        migrations.AddField(
            model_name="team",
            name="banner_image",
            field=models.ImageField(blank=True, null=True, upload_to="teams/banners/"),
        ),
        migrations.AddField(
            model_name="team",
            name="roster_image",
            field=models.ImageField(blank=True, null=True, upload_to="teams/rosters/"),
        ),
        migrations.AddField(
            model_name="team",
            name="region",
            field=models.CharField(blank=True, default="", max_length=48),
        ),
        migrations.AddField(
            model_name="team",
            name="twitter",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="team",
            name="instagram",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="team",
            name="discord",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="team",
            name="youtube",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="team",
            name="twitch",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="team",
            name="linktree",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="team",
            name="slug",
            field=models.SlugField(blank=True, default="", max_length=64, help_text="Unique per game"),
        ),

        # Preset tables
        migrations.CreateModel(
            name="EfootballTeamPreset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("team_name", models.CharField(blank=True, default="", max_length=120)),
                ("team_logo", models.ImageField(blank=True, null=True, upload_to="presets/efootball/team_logos/")),
                ("captain_name", models.CharField(blank=True, default="", max_length=120)),
                ("captain_ign", models.CharField(blank=True, default="", max_length=120)),
                ("mate_name", models.CharField(blank=True, default="", max_length=120)),
                ("mate_ign", models.CharField(blank=True, default="", max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("profile", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="efootball_presets", to="user_profile.userprofile")),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "eFootball Team Preset", "verbose_name_plural": "eFootball Team Presets"},
        ),
        migrations.CreateModel(
            name="ValorantTeamPreset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("team_name", models.CharField(blank=True, default="", max_length=120)),
                ("team_tag", models.CharField(blank=True, default="", max_length=10)),
                ("team_logo", models.ImageField(blank=True, null=True, upload_to="presets/valorant/team_logos/")),
                ("banner_image", models.ImageField(blank=True, null=True, upload_to="presets/valorant/banners/")),
                ("region", models.CharField(blank=True, default="", max_length=48)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("profile", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="valorant_presets", to="user_profile.userprofile")),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Valorant Team Preset", "verbose_name_plural": "Valorant Team Presets"},
        ),
        migrations.CreateModel(
            name="ValorantPlayerPreset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("in_game_name", models.CharField(blank=True, default="", max_length=120)),
                ("riot_id", models.CharField(blank=True, default="", help_text="Riot ID#Tagline", max_length=120)),
                ("discord", models.CharField(blank=True, default="", max_length=120)),
                ("role", models.CharField(blank=True, default="PLAYER", help_text="CAPTAIN/PLAYER/SUB", max_length=24)),
                ("preset", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="players", to="teams.valorantteampreset")),
            ],
            options={"verbose_name": "Valorant Player Preset", "verbose_name_plural": "Valorant Player Presets"},
        ),
    ]
