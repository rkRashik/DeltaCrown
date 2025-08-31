import pytest
from django.urls import reverse
from django.utils import timezone

from apps.tournaments.models import Tournament

pytestmark = pytest.mark.django_db


def test_tournament_detail_has_share_links():
    """
    Corelib mirror: ensure tournament detail exposes BD-favored share options.
    """
    from django.test import Client
    client = Client()

    now = timezone.now()
    t = Tournament.objects.create(
        name="Shareable Cup",
        reg_open_at=now, reg_close_at=now,
        start_at=now, end_at=now,
        slot_size=8,
        status="PUBLISHED",
    )
    url = reverse("tournaments:detail", kwargs={"slug": t.slug})
    r = client.get(url)
    assert r.status_code == 200
    html = r.content.decode()

    # Bangladesh-favored share options:
    assert "api.whatsapp.com/send?text=" in html      # WhatsApp
    assert "facebook.com/sharer/sharer.php" in html   # Facebook
    assert "mailto:" in html                          # Gmail (mailto)
    assert 'id="native-share-btn"' in html            # Native Share button exists

    # Ensure Twitter/X is NOT present anymore
    assert "twitter.com/intent/tweet" not in html

    # Page URL appears (plain or encoded)
    assert url in html or url.replace(":", "%3A").replace("/", "%2F") in html

    # Copy button present
    assert 'id="copy-share-link"' in html
