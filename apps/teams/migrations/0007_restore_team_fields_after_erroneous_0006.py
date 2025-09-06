
# Generated corrective migration to restore Team fields after accidental removal in 0006
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0006_alter_team_options_remove_team_banner_image_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="captain",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="captain_teams", to="user_profile.userprofile"),
        ),
        migrations.AddField(
            model_name="team",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name="team",
            name="game",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
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
            field=models.SlugField(blank=True, default="", help_text="Unique per game", max_length=64),
        ),
        migrations.AddConstraint(
            model_name="team",
            constraint=models.UniqueConstraint(condition=~models.Q(slug=""), fields=("game", "slug"), name="uniq_team_slug_per_game"),
        ),
    ]
