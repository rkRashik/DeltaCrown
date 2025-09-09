import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_homepage_has_all_sections(client):
    resp = client.get(reverse("homepage"))
    html = resp.content.decode()
    assert resp.status_code == 200

    # Hero (brand line present)
    assert "Where Champions Rise" in html

    # Timeline heading present (even if timeline is missing, heading renders)
    assert ">Timeline<" in html

    # Stats numbers appear (we default to numbers in SITE_CONTENT)
    assert "Registered Players" in html
    assert "Total Prize Pool" in html
    assert "Payout Accuracy" in html

    # Spotlight area always present: either spotlight card or fallback
    assert "Spotlight" in html
    assert ("No spotlight—discover tournaments" in html) or ("Featured tournament" in html) or ("Register" in html)

    # Split CTA & buttons
    assert "Compete & Win" in html
    assert "Join the Community" in html
    assert "See Tournaments" in html
    assert "Join Discord" in html
