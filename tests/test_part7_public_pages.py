# tests/test_part7_public_pages.py
import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_register_page_renders(client):
    # Minimal tournament object
    from apps.tournaments.models import Tournament
    t = Tournament.objects.create(name="Reg Cup", slug="reg-cup", game="efootball")
    url = reverse("tournaments:register", kwargs={"slug": t.slug})
    resp = client.get(url)
    assert resp.status_code == 200
    # Template shows standard text regardless of settings existence
    assert b"How to pay" in resp.content

@pytest.mark.django_db
def test_detail_page_renders(client):
    from apps.tournaments.models import Tournament
    t = Tournament.objects.create(name="Detail Cup", slug="detail-cup", game="valorant")
    url = reverse("tournaments:detail", kwargs={"slug": t.slug})
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"How to pay" in resp.content
