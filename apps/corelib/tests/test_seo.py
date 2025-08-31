import pytest
from django.urls import reverse
from django.utils import timezone
from apps.tournaments.models import Tournament

@pytest.mark.django_db
def test_robots_txt(client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    assert b"Sitemap:" in resp.content

@pytest.mark.django_db
def test_sitemap_has_home_and_tournament(client):
    # create a published tournament
    now = timezone.now()
    t = Tournament.objects.create(
        name="Sitemap Cup",
        reg_open_at=now, reg_close_at=now, start_at=now, end_at=now,
        slot_size=8, status="PUBLISHED"
    )
    resp = client.get("/sitemap.xml")
    assert resp.status_code == 200
    body = resp.content.decode()
    assert reverse("home") in body
    assert reverse("tournaments:detail", kwargs={"slug": t.slug}) in body

@pytest.mark.django_db
def test_canonical_present_on_tournament_detail(client):
    now = timezone.now()
    t = Tournament.objects.create(
        name="Canonical Cup",
        reg_open_at=now, reg_close_at=now, start_at=now, end_at=now,
        slot_size=8, status="PUBLISHED"
    )
    resp = client.get(reverse("tournaments:detail", kwargs={"slug": t.slug}))
    assert resp.status_code == 200
    assert b'rel="canonical"' in resp.content
