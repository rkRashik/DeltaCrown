import csv
import io
import pytest
from django.contrib.auth import get_user_model

from apps.teams.models import Team
from apps.user_profile.models import UserProfile
from apps.teams.admin import export_teams_csv

pytestmark = pytest.mark.django_db


def _mk_profile(username="cap", email="cap@example.com"):
    User = get_user_model()
    u = User.objects.create_user(username=username, email=email, password="x")
    # Be robust to auto-created profiles via signals
    p = getattr(u, "userprofile", None) or getattr(u, "profile", None)
    if not p:
        p = UserProfile.objects.create(user=u, display_name=username)
    return p


def test_export_teams_csv_function():
    captain = _mk_profile("captain1", "c1@example.com")
    t1 = Team.objects.create(name="Team Alpha", tag="ALPHA", captain=captain)
    t2 = Team.objects.create(name="Team Beta", tag="BETA", captain=captain)

    qs = Team.objects.filter(id__in=[t1.id, t2.id]).order_by("id")

    # Call the admin action directly; it does not rely on request/modeladmin
    resp = export_teams_csv(modeladmin=None, request=None, queryset=qs)

    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    assert "attachment; filename=" in resp["Content-Disposition"]

    rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8"))))

    # Header + 2 rows
    assert rows[0] == ["id", "name", "tag", "captain_id", "captain_username", "created_at"]

    # Verify names and tags appear; IDs in order
    assert rows[1][1] == "Team Alpha"
    assert rows[2][1] == "Team Beta"
    assert rows[1][2] == "ALPHA"
    assert rows[2][2] == "BETA"

    # Captain username present
    assert rows[1][4] == captain.user.username
    assert rows[2][4] == captain.user.username
