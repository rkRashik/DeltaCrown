# Generated manually to fix missing total_points and adjust_points fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0028_add_team_points_fields'),
    ]

    operations = [
        # First, try to remove fields if they exist (to handle inconsistent state)
        migrations.RunSQL(
            sql="ALTER TABLE teams_team DROP COLUMN IF EXISTS total_points CASCADE;",
            reverse_sql="-- No reverse operation needed"
        ),
        migrations.RunSQL(
            sql="ALTER TABLE teams_team DROP COLUMN IF EXISTS adjust_points CASCADE;",
            reverse_sql="-- No reverse operation needed"
        ),
        # Then add them back
        migrations.RunSQL(
            sql="""
            ALTER TABLE teams_team ADD COLUMN total_points INTEGER DEFAULT 0 CHECK (total_points >= 0);
            ALTER TABLE teams_team ADD COLUMN adjust_points INTEGER DEFAULT 0;
            """,
            reverse_sql="""
            ALTER TABLE teams_team DROP COLUMN total_points;
            ALTER TABLE teams_team DROP COLUMN adjust_points;
            """
        ),
    ]