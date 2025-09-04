# apps/teams/admin/exports.py
from __future__ import annotations

import csv
from django.http import HttpResponse


def export_teams_csv(modeladmin, request, queryset):
    """
    Simple CSV export (ID, Name, Tag, Captain, Members).
    """
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="teams.csv"'
    writer = csv.writer(response)
    writer.writerow(["ID", "Name", "Tag", "Captain", "Members"])

    for t in queryset:
        captain = getattr(t, "captain", None)
        cap_username = getattr(getattr(captain, "user", None), "username", "") if captain else ""
        writer.writerow([t.id, t.name, t.tag, cap_username, t.members_count])

    return response

export_teams_csv.short_description = "Export selected teams to CSV"
