import pytest

pytestmark = pytest.mark.django_db

def test_teams_index_out_of_range_page_renders(client):
    r = client.get("/teams/?page=999")
    assert r.status_code == 200
    # Pagination container is present even if there is only one/zero pages
    assert 'data-testid="pagination"' in r.content.decode()
