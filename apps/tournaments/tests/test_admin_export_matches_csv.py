import csv
import io
import pytest

from apps.tournaments.admin import export_matches_csv
from apps.tournaments.models import Tournament

pytestmark = pytest.mark.django_db


def test_export_matches_csv_header_only():
    """
    Call the admin action with an empty queryset to assert headers and CSV shape,
    without relying on the exact Match schema or required fields.
    We reuse Tournament.objects.none() to supply a valid QuerySet.
    """
    qs = Tournament.objects.none()
    resp = export_matches_csv(modeladmin=None, request=None, queryset=qs)

    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert "attachment; filename=" in resp["Content-Disposition"]

    rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8"))))
    # Only header row for empty queryset
    assert rows[0] == [
        "id",
        "tournament_id",
        "tournament_name",
        "round_no",
        "state",
        "participant_a",
        "participant_b",
        "scheduled_at",
        "reported_score_a",
        "reported_score_b",
        "winner_id",
        "created_at",
    ]
    assert len(rows) == 1
