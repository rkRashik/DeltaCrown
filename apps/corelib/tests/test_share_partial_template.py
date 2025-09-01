import pytest
from django.test import RequestFactory
from django.template import Template, Context

pytestmark = pytest.mark.django_db

def test_share_partial_renders_bd_focused_links_no_gmail_or_native():
    rf = RequestFactory()
    req = rf.get("/sample/page/")
    tpl = Template(
        '{% include "partials/share_block_bd.html" with title="Sample Title" url="https://example.com/x" %}'
    )
    html = tpl.render(Context({"request": req}))

    # Present: Facebook, WhatsApp, Instagram button, Discord button, Copy
    assert "facebook.com/sharer/sharer.php" in html
    assert "api.whatsapp.com/send?text=" in html
    assert 'id="share-instagram"' in html
    assert 'id="share-discord"' in html
    assert 'id="copy-share-link"' in html

    # Absent: Gmail and Native Share and Twitter
    assert "mailto:" not in html
    assert 'id="native-share-btn"' not in html
    assert "twitter.com/intent/tweet" not in html
