import re
from django.template import Context, Template
from django.test import override_settings, RequestFactory


def render(tpl_str: str):
    rf = RequestFactory()
    req = rf.get("/")
    tpl = Template(tpl_str)
    return tpl.render(Context({"request": req}))


def test_asset_from_src_has_version_query():
    html = render("{% asset 'src/js/helpers.js' %}")
    assert html.startswith("/static/src/js/helpers.js")
    assert "?v=" in html


@override_settings(USE_BUILD_ASSETS=True, STATIC_VERSION="abc123")
def test_asset_switches_to_build_when_enabled():
    html = render("{% asset 'src/css/tokens.css' %}")
    assert html.startswith("/static/build/css/tokens.css")
    assert html.endswith("?v=abc123")
