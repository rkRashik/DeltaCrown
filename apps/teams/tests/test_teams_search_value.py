import pytest

pytestmark = pytest.mark.django_db

def test_teams_index_search_value_preserved(client):
    r = client.get("/teams/?q=abc")
    assert r.status_code == 200
    html = r.content.decode()
    assert 'name="q"' in html and 'value="abc"' in html
