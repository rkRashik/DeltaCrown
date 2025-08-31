import csv
import io
import pytest
from django.contrib.auth import get_user_model

from apps.user_profile.models import UserProfile
from apps.user_profile.admin import export_userprofiles_csv

pytestmark = pytest.mark.django_db


def _get_or_create_profile(username="alice", email="alice@example.com"):
    User = get_user_model()
    u = User.objects.create_user(username=username, email=email, password="x")
    # Be robust to auto-create signals
    p = getattr(u, "userprofile", None) or getattr(u, "profile", None)
    if not p:
        p = UserProfile.objects.create(user=u, display_name=username)
    return p


def test_export_userprofiles_csv_function():
    p1 = _get_or_create_profile("alice", "alice@example.com")
    p2 = _get_or_create_profile("bob", "bob@example.com")

    qs = UserProfile.objects.filter(id__in=[p1.id, p2.id]).order_by("id")

    # Call the admin action directly to get the CSV
    resp = export_userprofiles_csv(modeladmin=None, request=None, queryset=qs)

    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert "attachment; filename=" in resp["Content-Disposition"]

    rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8"))))

    # Header + 2 rows
    assert rows[0] == ["id", "username", "email", "display_name", "created_at"]

    # Verify usernames line up with the queryset order
    assert rows[1][1] == p1.user.username
    assert rows[2][1] == p2.user.username
