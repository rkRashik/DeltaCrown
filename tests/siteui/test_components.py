import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_ui_showcase_renders(client):
    resp = client.get(reverse("ui_showcase"))
    assert resp.status_code == 200
    html = resp.content.decode()

    # Buttons
    assert "Primary" in html and "Outline" in html and "Ghost" in html

    # Form field & select
    assert 'label="Email"' not in html  # we use <label>, aria-label is not used here
    assert 'for="email"' in html and 'name="email"' in html
    assert 'name="game"' in html and "<option value=" in html

    # Checkbox & radio controls
    assert 'type="checkbox"' in html
    assert 'type="radio"' in html

    # Tooltip presence
    assert 'role="tooltip"' in html

    # Modal & Drawer toggles
    assert 'data-open-modal="demo-modal"' in html
    assert 'data-open-drawer="demo-drawer"' in html

@pytest.mark.django_db
def test_modal_markup_accessible(client):
    resp = client.get(reverse("ui_showcase"))
    html = resp.content.decode()
    # Dialog must be hidden by default and have aria-modal, aria-labelledby
    assert 'id="demo-modal"' in html
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'hidden' in html

@pytest.mark.django_db
def test_drawer_markup_accessible(client):
    resp = client.get(reverse("ui_showcase"))
    html = resp.content.decode()
    assert 'data-drawer' in html
    assert 'aria-modal="true"' in html
    assert 'data-drawer-overlay' in html
