# tests/test_quick_action_remind_team.py
import pytest
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _mk_profile(user):
    from apps.user_profile.models import UserProfile
    return UserProfile.objects.get_or_create(user=user)[0]


def test_remind_team_emails_active_teammates(client, django_user_model, settings):
    # Console backend to avoid real emails
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    # Users
    captain = django_user_model.objects.create_user(username="cap", password="pw", email="cap@example.com")
    mate = django_user_model.objects.create_user(username="mate", password="pw", email="mate@example.com")
    _ = django_user_model.objects.create_user(username="out", password="pw", email="out@example.com")

    cap_p = _mk_profile(captain)
    mate_p = _mk_profile(mate)

    # Team + membership (captain membership is auto-created by your project rules)
    from apps.teams.models import Team, TeamMembership
    team = Team.objects.create(name="Alpha", tag="ALP", game="valorant", captain=cap_p)

    # Ensure captain membership exists but don't duplicate it
    TeamMembership.objects.get_or_create(team=team, profile=cap_p, defaults={"status": TeamMembership.Status.ACTIVE})
    TeamMembership.objects.get_or_create(team=team, profile=mate_p, defaults={"status": TeamMembership.Status.ACTIVE})

    # Tournament + match
    from apps.tournaments.models import Tournament, Match
    t = Tournament.objects.create(name="Test Cup", slug="test-cup")
    m = Match.objects.create(
        tournament=t,
        round_no=1, position=1, best_of=1,
        team_a=team, team_b=None,
        start_at=timezone.now() + timezone.timedelta(hours=2),
        state="SCHEDULED",
    )

    client.login(username="cap", password="pw")
    url = reverse("tournaments:match_quick_action", args=[m.id, "remind_team"])
    res = client.post(url, follow=True)
    assert res.status_code in (200, 302)

    # Verify a notification record exists if your app writes one
    from django.apps import apps
    Notification = apps.get_model("notifications", "Notification")
    assert Notification.objects.filter(event="match_reminder", match_id=m.id).exists()
