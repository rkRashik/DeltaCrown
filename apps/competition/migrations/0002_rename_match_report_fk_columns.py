# Generated manually to fix incorrect FK field naming from 0001
# 
# Problem: Migration 0001 created ForeignKey fields named "team1_id" and "team2_id"
# This caused Django to create database columns as "team1_id_id" and "team2_id_id"
# (Django automatically appends _id to ForeignKey field names)
#
# Solution: This migration:
# 1. Renames database columns: team1_id_id → team1_id, team2_id_id → team2_id
# 2. Updates Django state to use correct field names: team1_id → team1, team2_id → team2
#    (with db_column parameter pointing to the renamed columns)
#
# This is safe for production as it only renames columns (no data loss).

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('competition', '0001_add_competition_models'),
        ('organizations', '0012_alter_membership_invite_team_fk'),
    ]

    operations = [
        # Step 1: Rename database columns (actual SQL column renames)
        migrations.RenameField(
            model_name='matchreport',
            old_name='team1_id',
            new_name='team1',
        ),
        migrations.RenameField(
            model_name='matchreport',
            old_name='team2_id',
            new_name='team2',
        ),
    ]
