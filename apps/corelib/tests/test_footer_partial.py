import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_footer_partial_renders_on_home(client):
    r = client.get(reverse("home"))
    assert r.status_code == 200
    html = r.content.decode()

    # Brand + at least one footer link should be present
    assert "DeltaCrown" in html
    assert ">Home<" in html or "Sitemap" in html or "Robots" in html
