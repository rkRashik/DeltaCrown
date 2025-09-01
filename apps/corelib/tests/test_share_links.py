import pytest
from django.urls import reverse
from django.utils import timezone

from apps.tournaments.models import Tournament

pytestmark = pytest.mark.django_db

def test_tournament_detail_has_bd_share_links_corelib_mirror():
    from django.test import Client
    client = Client()

    now = timezone.now()
    t = Tournament.objects.create(
        name="Mirror Share Cup",
        reg_open_at=now, reg_close_at=now,
        start_at=now, end_at=now,
        slot_size=8,
        status="PUBLISHED",
    )
    url = reverse("tournaments:detail", kwargs={"slug": t.slug})
    r = client.get(url)
    assert r.status_code == 200
    html = r.content.decode()

    assert "facebook.com/sharer/sharer.php" in html
    assert "api.whatsapp.com/send?text=" in html
    assert 'id="share-instagram"' in html
    assert 'id="share-discord"' in html
    assert 'id="copy-share-link"' in html

    assert "mailto:" not in html
    assert 'id="native-share-btn"' not in html
    assert "twitter.com/intent/tweet" not in html
