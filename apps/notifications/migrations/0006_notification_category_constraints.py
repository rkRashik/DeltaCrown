from django.db import migrations, models


ALLOWED_NOTIFICATION_TYPES = [
    "TOURNAMENT",
    "ECONOMY",
    "SOCIAL",
    "TEAM",
    "SYSTEM",
    "WARNING",
]


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0005_notification_structured_fields"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.CheckConstraint(
                name="notifications_category_allowed_values",
                check=models.Q(category__in=ALLOWED_NOTIFICATION_TYPES),
            ),
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.CheckConstraint(
                name="notifications_notification_type_allowed_values",
                check=models.Q(notification_type__in=ALLOWED_NOTIFICATION_TYPES),
            ),
        ),
    ]
