import pytest
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.tournaments.models import Tournament, Registration

User = get_user_model()


def make_tournament(
    name="Event",
    slug="event",
    game="efootball",
    status="UPCOMING",
    start_in_hours=48,
    reg_window=(-72, 24),
    prize_pool_bdt=0,
    entry_fee_bdt=0,
    slot_size=16,
):
    """Factory for Tournament that matches your fields."""
    now = timezone.now()
    start_at = now + timedelta(hours=start_in_hours) if start_in_hours is not None else None
    reg_open_at = now + timedelta(hours=reg_window[0]) if reg_window else None
    reg_close_at = now + timedelta(hours=reg_window[1]) if reg_window else None

    return Tournament.objects.create(
        name=name,
        slug=slug,
        game=game,
        status=status,
        start_at=start_at,
        reg_open_at=reg_open_at,
        reg_close_at=reg_close_at,
        prize_pool_bdt=prize_pool_bdt,
        entry_fee_bdt=entry_fee_bdt,
        slot_size=slot_size,
        short_description="Test tournament",
    )


@pytest.mark.django_db
def test_hub_renders_and_lists_basic(client):
    t1 = make_tournament(name="Delta Clash", slug="delta-clash", game="valorant", prize_pool_bdt=5000)
    t2 = make_tournament(name="EF Open", slug="ef-open", game="efootball", prize_pool_bdt=2000)
    url = reverse("tournaments:hub")
    resp = client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "Tournaments" in content
    assert "Delta Clash" in content
    assert "EF Open" in content


@pytest.mark.django_db
def test_by_game_filters(client):
    make_tournament(name="EF Open", slug="ef-open", game="efootball")
    make_tournament(name="Valorant Cup", slug="valorant-cup", game="valorant")
    # Your URL name is by_game; param key may be <game> or <game_slug> depending on urls.py
    try:
        url = reverse("tournaments:by_game", kwargs={"game_slug": "efootball"})
    except Exception:
        url = reverse("tournaments:by_game", kwargs={"game": "efootball"})
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "EF Open" in html
    assert "Valorant Cup" not in html  # filtered out


@pytest.mark.django_db
def test_sort_by_prize_desc(client):
    make_tournament(name="Low Prize", slug="low-prize", prize_pool_bdt=1000)
    make_tournament(name="High Prize", slug="high-prize", prize_pool_bdt=10000)
    url = reverse("tournaments:hub")
    resp = client.get(url + "?sort=prize")
    assert resp.status_code == 200
    # The view passes object_list; confirm ordering by highest prize first.
    ol = list(resp.context["object_list"])
    assert len(ol) >= 2
    assert getattr(ol[0], "prize_total_anno", getattr(ol[0], "prize_pool_bdt", 0)) >= getattr(
        ol[1], "prize_total_anno", getattr(ol[1], "prize_pool_bdt", 0)
    )


@pytest.mark.django_db
def test_fee_filter_range(client):
    make_tournament(name="Free Cup", slug="free-cup", entry_fee_bdt=0)
    make_tournament(name="Paid Cup", slug="paid-cup", entry_fee_bdt=200)
    url = reverse("tournaments:hub")
    resp = client.get(url + "?fee_min=100")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Paid Cup" in html
    assert "Free Cup" not in html


@pytest.mark.django_db
def test_detail_renders_and_has_countdown_or_info(client):
    t = make_tournament(name="Soon Event", slug="soon-event", start_in_hours=6, prize_pool_bdt=1234)
    url = reverse("tournaments:detail", kwargs={"slug": t.slug})
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode()
    # At minimum shows title; often shows countdown element
    assert "Soon Event" in html
    assert ("id=\"countdown\"" in html) or ("Prize pool" in html)


@pytest.mark.django_db
def test_my_registrations_row_appears_for_logged_in_user(client):
    user = User.objects.create_user(username="alice", password="x")
    t = make_tournament(name="EF Open", slug="ef-open", game="efootball")
    Registration.objects.create(tournament=t, user=user)  # minimal fields
    client.login(username="alice", password="x")
    resp = client.get(reverse("tournaments:hub"))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "My registrations" in html
    assert "EF Open" in html


@pytest.mark.django_db
def test_detail_cta_for_registered_pending(client):
    """
    If a registration exists without a VERIFIED state, the CTA should be
    'Continue registration' or 'View receipt (Pending)'. We check for either label.
    """
    user = User.objects.create_user(username="bob", password="x")
    t = make_tournament(name="Delta Clash", slug="delta-clash", game="valorant", status="OPEN")
    Registration.objects.create(tournament=t, user=user)  # no state set -> treated as draft/pending
    client.login(username="bob", password="x")
    resp = client.get(reverse("tournaments:detail", kwargs={"slug": t.slug}))
    assert resp.status_code == 200
    text = resp.content.decode()
    assert ("Continue registration" in text) or ("View receipt" in text) or ("Registered" in text)


@pytest.mark.django_db
def test_check_in_and_ics_aliases_exist(client):
    """
    The redesigned templates link to /<slug>/check-in/ and /<slug>/ics/.
    Even if you haven't implemented those views, the aliases should resolve and return 200
    (falling back to detail).
    """
    t = make_tournament(name="Alias Cup", slug="alias-cup", game="valorant")
    # Resolve check-in
    resp1 = client.get(reverse("tournaments:check_in", kwargs={"slug": t.slug}))
    assert resp1.status_code == 200
    # Resolve ICS
    resp2 = client.get(reverse("tournaments:ics", kwargs={"slug": t.slug}))
    # ICS may redirect to detail; accept 200 or 302
    assert resp2.status_code in (200, 302)
