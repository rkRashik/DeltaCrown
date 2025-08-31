import pytest
from django.urls import reverse
from django.utils import timezone

from apps.tournaments.models import Tournament

pytestmark = pytest.mark.django_db

def test_tournament_detail_has_share_links(client):
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

    # Twitter and Facebook share endpoints present
    assert "twitter.com/intent/tweet" in html
    assert "facebook.com/sharer/sharer.php" in html

    # The page URL is embedded in links (encoded or plain as per template)
    assert url in html or url.replace(":", "%3A").replace("/", "%2F") in html

    # Copy button present
    assert 'id="copy-share-link"' in html
