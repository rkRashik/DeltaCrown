# tests/test_my_matches_bulk_actions.py
import pytest
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db


def _mk_profile(user):
    from apps.user_profile.models import UserProfile
    return UserProfile.objects.get_or_create(user=user)[0]


def _participant_qc(match, profile):
    # Helper to check attendance for (user/profile, match)
    from apps.tournaments.models.attendance import MatchAttendance
    rel_model = MatchAttendance._meta.get_field("user").remote_field.model
    subject = profile if isinstance(profile, rel_model) else getattr(profile, "user", profile)
    return MatchAttendance.objects.filter(user=subject, match=match)


def test_bulk_confirm_then_decline_selected_matches(client, django_user_model):
    user = django_user_model.objects.create_user(username="r", password="pw", email="r@example.com")
    prof = _mk_profile(user)

    # Create two matches where the profile participates (solo)
    from apps.tournaments.models import Tournament, Match
    t = Tournament.objects.create(name="DeltaCup", slug="delta-cup")

    m1 = Match.objects.create(
        tournament=t, round_no=1, position=1, best_of=1,
        user_a=prof, user_b=None, state="SCHEDULED",
        start_at=timezone.now() + timezone.timedelta(days=1),
    )
    m2 = Match.objects.create(
        tournament=t, round_no=1, position=2, best_of=1,
        user_a=prof, user_b=None, state="SCHEDULED",
        start_at=timezone.now() + timezone.timedelta(days=2),
    )

    client.login(username="r", password="pw")

    bulk_url = reverse("tournaments:my_matches_bulk")

    # Confirm both
    res = client.post(bulk_url, {"action": "confirm", "match_ids": [m1.id, m2.id]}, follow=True)
    assert res.status_code in (200, 302)
    from apps.tournaments.models.attendance import MatchAttendance
    assert MatchAttendance.objects.filter(match=m1).exists()
    assert MatchAttendance.objects.filter(match=m2).exists()
    assert _participant_qc(m1, prof).first().status == "confirmed"
    assert _participant_qc(m2, prof).first().status == "confirmed"

    # Decline one
    res = client.post(bulk_url, {"action": "decline", "match_ids": [m2.id]}, follow=True)
    assert res.status_code in (200, 302)
    assert _participant_qc(m1, prof).first().status == "confirmed"
    assert _participant_qc(m2, prof).first().status == "declined"


def test_bulk_ignores_matches_not_participated(client, django_user_model):
    # Two users; only first participates
    u1 = django_user_model.objects.create_user(username="a", password="pw", email="a@example.com")
    u2 = django_user_model.objects.create_user(username="b", password="pw", email="b@example.com")
    p1 = _mk_profile(u1)
    _mk_profile(u2)

    from apps.tournaments.models import Tournament, Match
    t = Tournament.objects.create(name="Test", slug="test")

    m_p = Match.objects.create(tournament=t, round_no=1, position=1, best_of=1, user_a=p1, state="SCHEDULED")
    m_np = Match.objects.create(tournament=t, round_no=1, position=2, best_of=1, user_a=None, user_b=None, state="SCHEDULED")

    client.login(username="a", password="pw")
    url = reverse("tournaments:my_matches_bulk")
    res = client.post(url, {"action": "confirm", "match_ids": [m_p.id, m_np.id]}, follow=True)
    assert res.status_code in (200, 302)

    from apps.tournaments.models.attendance import MatchAttendance
    # only the participated match got an attendance row
    assert MatchAttendance.objects.filter(match=m_p).exists()
    assert not MatchAttendance.objects.filter(match=m_np).exists()
