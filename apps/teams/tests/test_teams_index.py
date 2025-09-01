import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_teams_index_page(client):
    r = client.get("/teams/")
    assert r.status_code == 200
    html = r.content.decode()
    assert "<h1 class=\"mb-3\">Teams</h1>" in html
    assert "No teams found." in html or "View" in html  # empty vs populated
