import io
import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_audit_detects_and_fixes_duplicates(django_user_model):
    Team = __import__("apps.teams.models._legacy", fromlist=["Team"]).Team

    Team.objects.create(name="Alpha", tag="ALP", game="valorant")
    Team.objects.create(name="alpha", tag="alp", game="valorant")  # duplicate in different case
    Team.objects.create(name="Bravo", tag="BRV", game="valorant")

    # Dry run shows duplicates
    out = io.StringIO()
    err = io.StringIO()
    code = call_command("audit_uniqueness", stdout=out, stderr=err)
    assert "Duplicates detected" in out.getvalue()

    # Now fix
    out = io.StringIO()
    call_command("audit_uniqueness", "--fix", stdout=out)
    fixed = Team.objects.values_list("name", "tag").order_by("name")
    # One of the Alpha rows should have a suffix added
    assert any(n != "Alpha" and n.startswith("Alpha-") for n, _ in fixed) or any(t != "ALP" and t.startswith("ALP") for _, t in fixed)
