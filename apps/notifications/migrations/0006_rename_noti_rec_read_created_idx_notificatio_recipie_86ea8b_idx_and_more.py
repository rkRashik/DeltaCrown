from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0005_rename_noti_rec_read_created_idx_notificatio_recipie_86ea8b_idx_and_more"),
    ]

    operations = [
        # State-only rename so Django's migration state matches your models,
        # without executing any DB SQL (avoids "relation does not exist").
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RenameIndex(
                    model_name="notification",
                    old_name="noti_rec_read_created_idx",
                    new_name="notificatio_recipie_86ea8b_idx",
                ),
                migrations.RenameIndex(
                    model_name="notification",
                    old_name="noti_rec_type_tour_match_idx",
                    new_name="notificatio_recipie_28df99_idx",
                ),
            ]
        ),
    ]
