import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_healthz_ok(client):
    url = reverse("healthz")
    res = client.get(url)
    assert res.status_code == 200
    assert res.headers.get("Content-Type", "").startswith("application/json")
    assert res.json().get("status") == "ok"
