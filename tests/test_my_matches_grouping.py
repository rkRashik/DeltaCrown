import pytest
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db

def _mk_profile(user):
    from apps.user_profile.models import UserProfile
    return UserProfile.objects.get_or_create(user=user)[0]

def test_group_by_tournament_renders_headings(client, django_user_model):
    u = django_user_model.objects.create_user(username="u", password="pw", email="u@example.com")
    p = _mk_profile(u)

    from apps.tournaments.models import Tournament, Match
    ta = Tournament.objects.create(name="Alpha Cup", slug="alpha-cup")
    tb = Tournament.objects.create(name="Beta Cup", slug="beta-cup")

    now = timezone.now()
    Match.objects.create(tournament=ta, round_no=1, position=1, best_of=1, user_a=p, start_at=now)
    Match.objects.create(tournament=tb, round_no=1, position=2, best_of=1, user_a=p, start_at=now)

    client.login(username="u", password="pw")
    url = reverse("tournaments:my_matches") + "?group=tournament"
    res = client.get(url)
    assert res.status_code == 200
    content = res.content.decode()
    assert "Alpha Cup" in content and "Beta Cup" in content

def test_group_by_date_renders_headings(client, django_user_model):
    u = django_user_model.objects.create_user(username="u2", password="pw", email="u2@example.com")
    p = _mk_profile(u)

    from apps.tournaments.models import Tournament, Match
    t = Tournament.objects.create(name="Gamma", slug="gamma")
    day1 = timezone.now()
    day2 = day1 + timezone.timedelta(days=1)

    Match.objects.create(tournament=t, round_no=1, position=1, best_of=1, user_a=p, start_at=day1)
    Match.objects.create(tournament=t, round_no=1, position=2, best_of=1, user_a=p, start_at=day2)

    client.login(username="u2", password="pw")
    url = reverse("tournaments:my_matches") + "?group=date"
    res = client.get(url)
    assert res.status_code == 200
    content = res.content.decode()
    assert day1.date().isoformat() in content
    assert day2.date().isoformat() in content
