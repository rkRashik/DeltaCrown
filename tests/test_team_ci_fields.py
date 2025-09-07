import pytest

pytestmark = pytest.mark.django_db


def test_team_ci_fields_autofill(django_user_model):
    Team = __import__("apps.teams.models._legacy", fromlist=["Team"]).Team  # import legacy Team
    t = Team.objects.create(name="Alpha", tag="ALP", game="valorant")
    t.refresh_from_db()
    assert t.name_ci == "alpha"
    assert t.tag_ci == "alp"

    # Update name/tag -> ci refreshes
    t.name = "AlphaX"
    t.tag = "Alp"
    t.save()
    t.refresh_from_db()
    assert t.name_ci == "alphax"
    assert t.tag_ci == "alp"
