import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_homepage_renders_and_contains_tagline(client, settings):
    url = reverse("homepage")
    resp = client.get(url)
    assert resp.status_code == 200
    # Tagline from SITE content layer:
    assert "From the Delta to the Crown — Where Champions Rise" in resp.content.decode()
