import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.user_profile.models import UserProfile
from apps.teams.models import Team

pytestmark = pytest.mark.django_db


def _get_or_create_profile(user, display_name="Alice"):
    """
    Be robust to projects that auto-create a profile via signals.
    Prefer attribute access, then fallback to get_or_create.
    """
    # Common reverse relations depending on your OneToOneField config
    prof = getattr(user, "userprofile", None) or getattr(user, "profile", None)
    if prof:
        return prof
    prof, _ = UserProfile.objects.get_or_create(
        user=user, defaults={"display_name": display_name}
    )
    return prof


def test_sitemap_includes_profile_and_team(client):
    User = get_user_model()
    u = User.objects.create_user(username="alice", password="x", email="alice@example.com")

    # Use existing profile if a signal already created it; otherwise create one
    p = _get_or_create_profile(u, display_name="Alice")

    # Create a team where that profile is captain
    team = Team.objects.create(name="Alpha Team", tag="ALPHA", captain=p)

    # Fetch sitemap
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    body = r.content.decode()

    # Expected URLs
    profile_url = reverse("user_profile:profile", kwargs={"username": u.username})
    team_url = reverse("teams:team_detail", kwargs={"team_id": team.id})

    assert profile_url in body
    assert team_url in body
