import json
from django.urls import reverse


def test_urls_resolvable_healthz(client):
    # Should exist and return the exact JSON shape you aligned earlier
    resp = client.get(reverse("healthz"))
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("application/json")
    data = json.loads(resp.content.decode("utf-8"))
    assert data == {"ok": True}
