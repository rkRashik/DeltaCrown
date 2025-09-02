import re

import pytest
from django.template import Context, Template
from django.test import RequestFactory


@pytest.mark.django_db
def test_meta_tags_renders_canonical_and_og(settings):
    rf = RequestFactory()
    req = rf.get("/dashboard/")
    tpl = Template("{% meta_tags title='Hello' description='World' %}")
    html = tpl.render(Context({"request": req}))

    assert '<link rel="canonical"' in html
    assert 'property="og:title"' in html
    assert 'content="Hello"' in html
    assert 'property="og:description"' in html
    assert 'content="World"' in html
