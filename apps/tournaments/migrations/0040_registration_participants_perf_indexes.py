from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0039_alter_tournamentsponsor_options_hubsupportticket'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='registration',
            index=models.Index(
                fields=['tournament', 'is_deleted', '-registered_at'],
                name='reg_tour_del_regd_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='registration',
            index=models.Index(
                fields=['tournament', 'is_deleted', 'status'],
                name='reg_tour_del_stat_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='registration',
            index=models.Index(
                fields=['tournament', 'is_deleted', 'checked_in'],
                name='reg_tour_del_check_idx',
            ),
        ),
    ]
