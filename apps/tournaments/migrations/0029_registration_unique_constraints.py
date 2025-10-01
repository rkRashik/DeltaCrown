from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0028_delete_tournamentregistrationpolicy"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="registration",
            constraint=models.UniqueConstraint(
                fields=("tournament", "user"),
                condition=Q(user__isnull=False),
                name="uq_registration_tournament_user_not_null",
            ),
        ),
        migrations.AddConstraint(
            model_name="registration",
            constraint=models.UniqueConstraint(
                fields=("tournament", "team"),
                condition=Q(team__isnull=False),
                name="uq_registration_tournament_team_not_null",
            ),
        ),
    ]
