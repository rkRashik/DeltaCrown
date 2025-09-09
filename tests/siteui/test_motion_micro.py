import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_home_includes_reveal_and_count_attributes(client):
    resp = client.get(reverse("homepage"))
    html = resp.content.decode()
    assert resp.status_code == 200

    # Reveal markers present
    assert 'data-reveal' in html

    # Count-up markers present
    assert 'data-count-to="' in html

    # Countdown marker present if configured
    assert 'data-countdown-to="' in html or 'Next event begins in:' not in html  # either configured, or line omitted

@pytest.mark.django_db
def test_nav_drawer_markup_present(client):
    resp = client.get(reverse("homepage"))
    html = resp.content.decode()
    assert 'data-open-drawer="main-drawer"' in html
    assert 'id="main-drawer"' in html
    assert 'data-drawer' in html

@pytest.mark.django_db
def test_toast_container_present(client):
    resp = client.get(reverse("homepage"))
    html = resp.content.decode()
    assert 'id="dc-toasts"' in html
    assert 'aria-live="polite"' in html
