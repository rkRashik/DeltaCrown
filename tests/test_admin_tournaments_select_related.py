# tests/test_admin_tournaments_select_related.py
import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_tournament_admin_changelist_loads(admin_client):
    url = reverse("admin:tournaments_tournament_changelist")
    r = admin_client.get(url)
    assert r.status_code == 200
