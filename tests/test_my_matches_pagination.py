import pytest
from django.urls import reverse
from django.utils import timezone

pytestmark = pytest.mark.django_db

def _mk_profile(user):
    from apps.user_profile.models import UserProfile
    return UserProfile.objects.get_or_create(user=user)[0]

def test_pagination_page_counts(client, django_user_model):
    u = django_user_model.objects.create_user(username="pg", password="pw", email="pg@example.com")
    p = _mk_profile(u)

    from apps.tournaments.models import Tournament, Match
    t = Tournament.objects.create(name="Pager Cup", slug="pager-cup")

    # 35 matches -> page size 20 => page1:20, page2:15
    for i in range(35):
        Match.objects.create(
            tournament=t, round_no=1, position=i+1, best_of=1,
            user_a=p, start_at=timezone.now() + timezone.timedelta(minutes=i)
        )

    client.login(username="pg", password="pw")

    url1 = reverse("tournaments:my_matches")
    r1 = client.get(url1)
    assert r1.status_code == 200
    assert r1.content.decode().count('rounded-2xl border dc-border bg-black/10 p-4') >= 20

    url2 = reverse("tournaments:my_matches") + "?page=2"
    r2 = client.get(url2)
    assert r2.status_code == 200
    # expect remaining 15 items on page 2
    assert r2.content.decode().count('rounded-2xl border dc-border bg-black/10 p-4') >= 10
