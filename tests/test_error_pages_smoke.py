import pytest
from django.template.loader import render_to_string

pytestmark = pytest.mark.django_db


def test_error_templates_exist_and_render():
    # These should render without missing blocks even if DEBUG=True in tests.
    for tmpl in ("403.html", "404.html", "500.html"):
        html = render_to_string(tmpl, {})
        assert "<html" in html.lower() or "<div" in html.lower()
