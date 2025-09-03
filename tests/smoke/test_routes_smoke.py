import pytest
from django.urls import reverse, resolve

@pytest.mark.django_db
def test_healthz(client):
    # Assuming /healthz exists per project conventions
    res = client.get("/healthz")
    assert res.status_code in (200, 204)

@pytest.mark.django_db
def test_styleguide_route(client):
    # If not wired yet, we'll add a tiny URL hook (see below)
    res = client.get("/ui/styleguide/")
    assert res.status_code in (200, 301, 302) or res.status_code == 200
