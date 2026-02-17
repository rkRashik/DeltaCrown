"""
Decouple cross-app ForeignKey fields to IntegerField.

Converts FK references to teams.Team and user_profile.UserProfile into
plain IntegerField columns. The underlying DB columns (team_id, etc.)
already exist and already hold integer IDs, so this migration uses
RunSQL with state_operations to avoid any destructive column drop/add.
"""

from django.db import migrations, models
import django.db.models.deletion


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
            database_operations=[],  # Column already exists as team_id
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
            database_operations=[],
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
            database_operations=[],
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
            database_operations=[],
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
            database_operations=[],
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
            database_operations=[],
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
            database_operations=[],
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
            database_operations=[],
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
            database_operations=[],
        ),

        # ── Update Meta constraints & indexes (GroupStanding) ──
        migrations.AlterModelOptions(
            name='groupstanding',
            options={
                'ordering': ['group', 'rank', '-points', '-goal_difference', '-goals_for'],
                'verbose_name': 'Group Standing',
                'verbose_name_plural': 'Group Standings',
            },
        ),

        # ── Update Meta (TournamentTeamInvitation) ──
        migrations.AlterUniqueTogether(
            name='tournamentteaminvitation',
            unique_together={('tournament', 'team_id')},
        ),

        # ── Update Meta (TeamRegistrationPermissionRequest) ──
        migrations.AlterUniqueTogether(
            name='teamregistrationpermissionrequest',
            unique_together={('team_id', 'tournament', 'requester', 'status')},
        ),
    ]
