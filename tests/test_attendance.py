import pytest
from django.urls import reverse
from django.utils import timezone

from apps.tournaments.models import Match, Tournament
from apps.tournaments.models.attendance import MatchAttendance


@pytest.mark.django_db
def test_attendance_toggle(client, django_user_model):
    # Minimal objects
    user = django_user_model.objects.create_user(username="p", email="p@example.com", password="x")
    client.login(username="p", password="x")

    # Unique-ish slug to avoid clashes if tests run in parallel
    t = Tournament.objects.create(
        name="T1",
        slug=f"t1-{int(timezone.now().timestamp())}",
        game="valorant",
        start_at=timezone.now(),
    )

    # IMPORTANT: your Match requires non-null round_no (and likely position)
    m = Match.objects.create(
        tournament=t,
        start_at=timezone.now(),
        round_no=1,
        position=1,
        best_of=1,  # harmless even if default exists
    )

    url = reverse("tournaments:match_attendance_toggle", args=[m.id, "confirm"])
    r = client.post(url, {"next": reverse("tournaments:my_matches")})
    assert r.status_code in (302, 303)

    obj = MatchAttendance.objects.get(user=user, match=m)
    assert obj.status == "confirmed"

    # flip to decline
    url2 = reverse("tournaments:match_attendance_toggle", args=[m.id, "decline"])
    r2 = client.post(url2)
    assert r2.status_code in (302, 303)
    obj.refresh_from_db()
    assert obj.status == "declined"
