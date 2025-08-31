import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_healthz_ok(client):
    r = client.get(reverse("healthz"))
    assert r.status_code == 200
    data = r.json()
    assert data == {"ok": True}
