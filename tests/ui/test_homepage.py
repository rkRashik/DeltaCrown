import pytest
from django.template.loader import get_template

@pytest.mark.django_db
def test_homepage_renders(client):
    resp = client.get("/")
    assert resp.status_code in (200, 302)  # allow redirect to /home if configured
    # Rendered content should at least include brand headline (if 200)
    if resp.status_code == 200:
        assert "From the Delta to the Crown" in resp.content.decode()

def test_core_templates_exist():
    required = [
        "base.html",
        "home.html",
        "partials/nav.html",
        "partials/footer.html",
        "partials/toasts.html",
        "partials/seo_meta.html",
        "sections/hero.html",
        "sections/pillars.html",
        "sections/timeline.html",
        "sections/stats.html",
        "sections/spotlight.html",
        "sections/split_cta.html",
        "pages/about.html",
        "pages/community.html",
    ]
    for name in required:
        get_template(name)
