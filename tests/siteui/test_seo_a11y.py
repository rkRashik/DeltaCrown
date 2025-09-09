import json
import re
import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_homepage_seo_meta_and_jsonld(client):
    resp = client.get(reverse("homepage"))
    assert resp.status_code == 200
    html = resp.content.decode()

    # language + skip link baseline a11y (lang is on <html>, skip link exists)
    assert "<html" in html and 'lang="' in html
    assert "Skip to main content" in html

    # Canonical + OG + Twitter cards
    assert '<link rel="canonical"' in html
    assert 'property="og:title"' in html
    assert 'property="og:site_name"' in html
    assert 'name="twitter:card"' in html

    # JSON-LD presence and parseability
    scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert len(scripts) >= 2
    types = set()
    for s in scripts:
        data = json.loads(s.strip())
        if isinstance(data, dict) and "@type" in data:
            types.add(data["@type"])
    assert "Organization" in types
    assert "WebSite" in types

@pytest.mark.django_db
def test_robots_and_sitemap(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "Sitemap:" in r.content.decode()
    s = client.get("/sitemap.xml")
    assert s.status_code == 200
    text = s.content.decode()
    assert "<urlset" in text and "<loc>" in text and "</urlset>" in text
