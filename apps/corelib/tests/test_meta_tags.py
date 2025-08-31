import pytest
from django.test import RequestFactory
from django.template import Context, Template

pytestmark = pytest.mark.django_db


def render_tpl(source, ctx):
    return Template(source).render(Context(ctx))


def test_meta_tags_renders_canonical_and_og():
    rf = RequestFactory()
    req = rf.get("/tournaments/summer-cup/")

    html = render_tpl(
        """
        {% load core_meta %}
        {% meta_tags request title="Summer Cup" description="A fun tourney" image="http://example.com/img.png" %}
        """,
        {"request": req},
    )

    assert 'rel="canonical"' in html
    assert 'property="og:title"' in html and "Summer Cup" in html
    assert 'property="og:description"' in html and "A fun tourney" in html
    assert 'property="og:image"' in html and "img.png" in html
    # No Twitter tags anymore


def test_meta_tags_defaults_safe():
    rf = RequestFactory()
    req = rf.get("/any/")
    html = render_tpl(
        """
        {% load core_meta %}
        {% meta_tags request %}
        """,
        {"request": req},
    )
    # Defaults present
    assert 'rel="canonical"' in html
    assert 'property="og:title"' in html
