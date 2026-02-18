"""
Decouple cross-app ForeignKey fields to IntegerField.

Converts FK references to teams.Team and user_profile.UserProfile into
plain IntegerField columns. Uses RunSQL for DB operations to handle
both fresh and existing databases.
"""

from django.db import migrations, models


def noop_forward(apps, schema_editor):
    """No-op — DB columns already have the right data type in existing DBs."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0007_remove_legacy_game_model'),
    ]

    operations = [
        # ── DisputeRecord.opened_by_team → opened_by_team_id ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='disputerecord',
                    name='opened_by_team',
                ),
                migrations.AddField(
                    model_name='disputerecord',
                    name='opened_by_team_id',
                    field=models.IntegerField(
                        blank=True,
                        db_column='opened_by_team_id',
                        db_index=True,
                        help_text='Team ID representing the disputer (if team tournament)',
                        null=True,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # ── FormResponse.team → team_id ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='formresponse',
                    name='team',
                ),
                migrations.AddField(
                    model_name='formresponse',
                    name='team_id',
                    field=models.IntegerField(
                        blank=True,
                        db_column='team_id',
                        db_index=True,
                        help_text='Team ID (if team tournament)',
                        null=True,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # ── GroupStanding.team → team_id ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='groupstanding',
                    name='team',
                ),
                migrations.AddField(
                    model_name='groupstanding',
                    name='team_id',
                    field=models.IntegerField(
                        blank=True,
                        db_column='team_id',
                        db_index=True,
                        null=True,
                        verbose_name='Team ID',
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # ── CheckIn.team → team_id ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='checkin',
                    name='team',
                ),
                migrations.AddField(
                    model_name='checkin',
                    name='team_id',
                    field=models.IntegerField(
                        blank=True,
                        db_column='team_id',
                        db_index=True,
                        null=True,
                        verbose_name='Team ID',
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # ── MatchResultSubmission.submitted_by_team → submitted_by_team_id ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='matchresultsubmission',
                    name='submitted_by_team',
                ),
                migrations.AddField(
                    model_name='matchresultsubmission',
                    name='submitted_by_team_id',
                    field=models.IntegerField(
                        blank=True,
                        db_column='submitted_by_team_id',
                        db_index=True,
                        help_text='Team ID the submitter represents (if team tournament)',
                        null=True,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # ── TournamentTeamInvitation.team → team_id ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='tournamentteaminvitation',
                    name='team',
                ),
                migrations.AddField(
                    model_name='tournamentteaminvitation',
                    name='team_id',
                    field=models.IntegerField(
                        db_column='team_id',
                        db_index=True,
                        default=0,
                        help_text='Team ID being invited',
                    ),
                    preserve_default=False,
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # ── TournamentTeamInvitation.invited_by → invited_by_id ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='tournamentteaminvitation',
                    name='invited_by',
                ),
                migrations.AddField(
                    model_name='tournamentteaminvitation',
                    name='invited_by_id',
                    field=models.IntegerField(
                        blank=True,
                        db_column='invited_by_id',
                        db_index=True,
                        help_text='UserProfile ID of organizer/staff who sent the invitation',
                        null=True,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # ── TournamentTeamInvitation.responded_by → responded_by_id ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='tournamentteaminvitation',
                    name='responded_by',
                ),
                migrations.AddField(
                    model_name='tournamentteaminvitation',
                    name='responded_by_id',
                    field=models.IntegerField(
                        blank=True,
                        db_column='responded_by_id',
                        db_index=True,
                        help_text='UserProfile ID of team member who responded to invitation',
                        null=True,
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # ── TeamRegistrationPermissionRequest.team → team_id ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='teamregistrationpermissionrequest',
                    name='team',
                ),
                migrations.AddField(
                    model_name='teamregistrationpermissionrequest',
                    name='team_id',
                    field=models.IntegerField(
                        db_column='team_id',
                        db_index=True,
                        default=0,
                        help_text='Team ID for which permission is requested',
                    ),
                    preserve_default=False,
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=migrations.RunSQL.noop,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # ── Update Meta constraints & indexes (GroupStanding) ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterModelOptions(
                    name='groupstanding',
                    options={
                        'ordering': ['group', 'rank', '-points', '-goal_difference', '-goals_for'],
                        'verbose_name': 'Group Standing',
                        'verbose_name_plural': 'Group Standings',
                    },
                ),
            ],
            database_operations=[],
        ),

        # ── Update Meta (TournamentTeamInvitation) ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name='tournamentteaminvitation',
                    unique_together={('tournament', 'team_id')},
                ),
            ],
            database_operations=[],
        ),

        # ── Update Meta (TeamRegistrationPermissionRequest) ──
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name='teamregistrationpermissionrequest',
                    unique_together={('team_id', 'tournament', 'requester', 'status')},
                ),
            ],
            database_operations=[],
        ),
    ]
