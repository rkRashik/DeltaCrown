import csv
import io
import pytest

from apps.notifications.models import Notification
from apps.notifications.admin import export_notifications_csv

pytestmark = pytest.mark.django_db


def test_export_notifications_csv_header_only():
    """
    Call the admin action with an empty queryset to assert headers and CSV shape
    without depending on concrete Notification required fields.
    """
    qs = Notification.objects.none()
    resp = export_notifications_csv(modeladmin=None, request=None, queryset=qs)

    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert "attachment; filename=" in resp["Content-Disposition"]

    rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8"))))
    # Only header row when queryset is empty
    assert rows[0] == [
        "id",
        "user_id",
        "user_username",
        "is_read",
        "created_at",
        "text",
        "url",
        "kind",
    ]
    assert len(rows) == 1
