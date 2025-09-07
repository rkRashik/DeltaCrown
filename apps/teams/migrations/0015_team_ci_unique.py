from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0014_team_ci_fields"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="team",
            constraint=models.UniqueConstraint(
                fields=["game", "name_ci"], name="uniq_team_game_name_ci"
            ),
        ),
        migrations.AddConstraint(
            model_name="team",
            constraint=models.UniqueConstraint(
                fields=["game", "tag_ci"], name="uniq_team_game_tag_ci"
            ),
        ),
    ]
