import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_home_has_theme_toggle_and_data_theme(client):
    resp = client.get(reverse("homepage"))
    html = resp.content.decode()

    # page renders and includes data-theme attribute on the <html> element
    assert resp.status_code == 200
    assert 'data-theme=' in html

    # toggle button exists with expected attributes
    assert 'id="theme-toggle"' in html
    assert 'aria-label="Toggle color theme' in html
    assert 'data-state="system"' in html

@pytest.mark.django_db
def test_semantic_tokens_present(client):
    resp = client.get(reverse("homepage"))
    html = resp.content.decode()
    # Check a couple of tokens exist to ensure CSS is wired
    assert '--bg:' in html
    assert '--brand-1:' in html
