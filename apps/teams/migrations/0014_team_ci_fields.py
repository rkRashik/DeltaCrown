from django.db import migrations, models


def backfill_ci(apps, schema_editor):
    Team = apps.get_model("teams", "Team")
    # Iterate in chunks to avoid loading everything at once
    for t in Team.objects.all().only("id", "name", "tag").iterator(chunk_size=500):
        name = (t.name or "").strip().lower() or None
        tag = (t.tag or "").strip().lower() or None
        Team.objects.filter(id=t.id).update(name_ci=name, tag_ci=tag)


class Migration(migrations.Migration):

    dependencies = [
        # IMPORTANT: point to your actual latest migration (0013_rename_...and_more)
        ("teams", "0013_rename_teams_team_team_id_ach_idx_teams_teama_team_id_daea1e_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="name_ci",
            field=models.CharField(max_length=255, null=True, blank=True, db_index=True),
        ),
        migrations.AddField(
            model_name="team",
            name="tag_ci",
            field=models.CharField(max_length=255, null=True, blank=True, db_index=True),
        ),
        migrations.RunPython(backfill_ci, reverse_code=migrations.RunPython.noop),
    ]
