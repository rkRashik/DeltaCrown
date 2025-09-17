from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0013_paymentverification_last_action_reason_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tournamentregistrationpolicy",
            name="allow_substitutes",
            field=models.BooleanField(default=False),
        ),
    ]
