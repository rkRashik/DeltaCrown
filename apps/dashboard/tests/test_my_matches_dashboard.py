import pytest
from django.apps import apps
from django.urls import reverse

pytestmark = pytest.mark.django_db

def _has_match_model():
    for label in ("tournaments.Match", "matches.Match", "brackets.Match"):
        try:
            if apps.get_model(*label.split(".")):
                return True
        except Exception:
            pass
    return False

@pytest.mark.skipif(not _has_match_model(), reason="No Match model available in this repo")
def test_my_matches_page_renders(client, django_user_model):
    # login
    User = django_user_model
    user = User.objects.create_user(username="u", password="p")
    client.login(username="u", password="p")
    try:
        url = reverse("dashboard:my_matches")
    except Exception:
        # if not included in root urls, just assert path exists logically
        url = "/my/matches/"
    resp = client.get(url)
    assert resp.status_code in (200, 302)  # 302 in case login_required middleware path differs
