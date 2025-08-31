import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from apps.tournaments.models import Tournament

pytestmark = pytest.mark.django_db


def _t(name, **over):
    now = timezone.now()
    base = dict(
        name=name,
        slug=name.lower().replace(" ", "-"),
        game="valorant",
        short_description="demo",
        reg_open_at=now - timedelta(days=2),
        reg_close_at=now + timedelta(days=2),
        start_at=now + timedelta(days=3),
        end_at=now + timedelta(days=4),
        slot_size=8,
        entry_fee_bdt=0,
    )
    base.update(over)
    return Tournament.objects.create(**base)


def test_search_and_game_filter(client):
    a = _t("Valorant Alpha", game="valorant")
    b = _t("Efootball Beta", game="efootball")

    url = reverse("tournaments:list")
    # search
    r = client.get(url, {"q": "Alpha"})
    assert a.name in r.content.decode()
    assert b.name not in r.content.decode()

    # game
    r = client.get(url, {"game": "efootball"})
    html = r.content.decode()
    assert b.name in html and a.name not in html


def test_status_filters(client):
    now = timezone.now()
    up = _t("Up Next", start_at=now + timedelta(days=5), end_at=now + timedelta(days=6))
    on = _t("On Going", start_at=now - timedelta(hours=1), end_at=now + timedelta(hours=1))
    dn = _t("Done", start_at=now - timedelta(days=3), end_at=now - timedelta(days=2))

    url = reverse("tournaments:list")

    r = client.get(url, {"status": "upcoming"})
    h = r.content.decode()
    assert up.name in h and on.name not in h and dn.name not in h

    r = client.get(url, {"status": "ongoing"})
    h = r.content.decode()
    assert on.name in h and up.name not in h and dn.name not in h

    r = client.get(url, {"status": "completed"})
    h = r.content.decode()
    assert dn.name in h and up.name not in h and on.name not in h


def test_entry_filters(client):
    paid = _t("Paid Cup", entry_fee_bdt=100)
    free = _t("Free Cup", entry_fee_bdt=0)

    url = reverse("tournaments:list")

    r = client.get(url, {"entry": "paid"})
    html = r.content.decode()
    assert paid.name in html and free.name not in html

    r = client.get(url, {"entry": "free"})
    html = r.content.decode()
    assert free.name in html and paid.name not in html
