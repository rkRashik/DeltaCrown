# apps/tournaments/tests/test_groups_rendering.py
import pytest
from django.apps import apps
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db

def _mk_team(name="Alpha", tag="ALP", game="valorant"):
    Team = apps.get_model("teams", "Team")
    obj = Team.objects.create(name=name, tag=tag, slug=name.lower(), game=game)
    return obj

def _mk_tournament(name="Cup", slug="cup", game="valorant"):
    Tournament = apps.get_model("tournaments", "Tournament")
    try:
        return Tournament.objects.create(name=name, slug=slug, game=game)
    except Exception:
        return Tournament.objects.create(name=name, slug=slug)

def _mk_bracket(t, payload):
    Bracket = apps.get_model("tournaments", "Bracket")
    return Bracket.objects.create(tournament=t, data=payload)

def test_groups_inclusion_tag_renders_names():
    t1 = _mk_team("Alpha", "ALP")
    t2 = _mk_team("Bravo", "BRV")
    t = _mk_tournament()
    _mk_bracket(t, {"groups": [{"name": "Group A", "teams": [t1.id, t2.id]}]})
    # Call the inclusion template directly with pre-resolved teams
    html = render_to_string("tournaments/_groups.html", {"groups": [{"name": "Group A", "teams": [t1, t2]}]})
    assert "Group A" in html and "Alpha" in html and "Bravo" in html

def test_admin_validation_accepts_valid_payload():
    from apps.tournaments.admin.brackets import _validate_groups_payload
    _validate_groups_payload({"groups": [{"name": "Group A", "teams": [1,2,3]}]})

def test_admin_validation_rejects_bad_payload():
    from apps.tournaments.admin.brackets import _validate_groups_payload
    with pytest.raises(ValidationError):
        _validate_groups_payload({"groups": [{"name": "", "teams": [1]}]})
    with pytest.raises(ValidationError):
        _validate_groups_payload({"groups": [{"name": "A", "teams": ["x"]}]})
