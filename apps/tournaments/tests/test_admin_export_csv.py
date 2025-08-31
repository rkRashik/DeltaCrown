import csv
import io
import pytest
from django.utils import timezone

from apps.tournaments.models import Tournament
from apps.tournaments.admin import export_tournaments_csv

pytestmark = pytest.mark.django_db


def test_export_tournaments_csv_function():
    now = timezone.now()
    t1 = Tournament.objects.create(
        name="Export Cup A",
        status="PUBLISHED",
        slot_size=8,
        reg_open_at=now, reg_close_at=now,
        start_at=now, end_at=now,
    )
    t2 = Tournament.objects.create(
        name="Export Cup B",
        status="DRAFT",
        slot_size=16,
        reg_open_at=now, reg_close_at=now,
        start_at=now, end_at=now,
    )

    qs = Tournament.objects.filter(id__in=[t1.id, t2.id]).order_by("id")

    # Call the admin action directly; it doesn't use modeladmin/request
    resp = export_tournaments_csv(modeladmin=None, request=None, queryset=qs)

    # Should return a CSV file
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert "attachment; filename=" in resp["Content-Disposition"]

    # Parse CSV content
    content = resp.content.decode("utf-8")
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    # Header + 2 rows
    assert rows[0] == [
        "id",
        "name",
        "slug",
        "status",
        "slot_size",
        "reg_open_at",
        "reg_close_at",
        "start_at",
        "end_at",
    ]

    # Check names present, and IDs match queryset order
    assert rows[1][1] == t1.name
    assert rows[2][1] == t2.name
    assert [int(rows[1][0]), int(rows[2][0])] == list(qs.values_list("id", flat=True))
