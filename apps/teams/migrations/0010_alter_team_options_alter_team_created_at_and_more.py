from django.db import migrations, models
import django.utils.timezone


def fill_created_at(apps, schema_editor):
    Team = apps.get_model("teams", "Team")
    Team.objects.filter(created_at__isnull=True).update(created_at=django.utils.timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0009_readd_team_captain_game_and_media"),
    ]

    operations = [
        # 1) Backfill any NULL created_at safely
        migrations.RunPython(fill_created_at, migrations.RunPython.noop),

        # 2) Make created_at non-null, with auto_now_add=True (no DB default needed)
        migrations.AlterField(
            model_name="team",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),

        # 3) Keep your model options (ordering) as Django generated
        migrations.AlterModelOptions(
            name="team",
            options={"ordering": ("name",)},
        ),

        # 4) Ensure 'game' matches the current model (choices/blank/default)
        migrations.AlterField(
            model_name="team",
            name="game",
            field=models.CharField(
                max_length=20,
                choices=[("efootball", "eFootball"), ("valorant", "Valorant")],
                blank=True,
                default="",
            ),
        ),
    ]
