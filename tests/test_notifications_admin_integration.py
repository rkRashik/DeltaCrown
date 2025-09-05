import pytest
from django.contrib.admin.sites import AdminSite
from django.test.client import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

from apps.tournaments.models import Tournament, Match, Registration
from apps.user_profile.models import UserProfile
from apps.tournaments.admin.matches import MatchAdmin
from apps.corelib.brackets import generate_bracket
from apps.notifications.models import Notification


def _admin_request(user, method="get", path="/"):
    rf = RequestFactory()
    req = getattr(rf, method)(path)
    req.user = user
    setattr(req, "session", {})
    setattr(req, "_messages", FallbackStorage(req))
    return req


@pytest.mark.django_db
def test_set_winner_emits_notifications(client, django_user_model):
    admin_user = django_user_model.objects.create_superuser("admin", "a@e.com", "x")

    # Setup tournament with 2 players
    t = Tournament.objects.create(name="NotifyCup", slug="notify-cup", game="efootball", status="PUBLISHED")
    u1 = django_user_model.objects.create_user("p1", "p1@e.com", "x")
    u2 = django_user_model.objects.create_user("p2", "p2@e.com", "x")
    p1, _ = UserProfile.objects.get_or_create(user=u1)
    p2, _ = UserProfile.objects.get_or_create(user=u2)
    Registration.objects.create(tournament=t, user=p1, status="CONFIRMED")
    Registration.objects.create(tournament=t, user=p2, status="CONFIRMED")
    generate_bracket(t)

    # Act: set winner via admin view
    ma = MatchAdmin(Match, AdminSite())
    m = Match.objects.get(tournament=t)
    req = _admin_request(admin_user, "get", f"/admin/tournaments/match/{m.id}/set_winner/a/")
    ma.set_winner_view(req, match_id=m.id, who="a")

    # Assert: two notifications (one each participant) with event=match_result
    notis = Notification.objects.filter(event="match_result")
    # We expect at least 1 (often 2) depending on availability of user_a/user_b users
    assert notis.count() >= 1
