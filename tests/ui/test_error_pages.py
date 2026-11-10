"""Batch E: 403 / 404 / 500 are plain recovery pages with the right status, noindex and no invented detail."""
import pytest
from django.test import RequestFactory
from django.views.defaults import permission_denied, server_error


def _body(resp):
    return resp.content.decode()


@pytest.mark.django_db
def test_404_is_a_recovery_page(client):
    resp = client.get("/definitely-not-a-page-xyz/")
    html = _body(resp)
    assert resp.status_code == 404
    assert 'name="robots" content="noindex, nofollow"' in html
    assert "We could not find that page" in html and 'href="/"' in html
    assert html.count("<h1") == 1
    for fake in ("REF: DC-", "TIMESTAMP", "err-orb", "err-grid", "document.write", "javascript:history"):
        assert fake not in html, fake


@pytest.mark.django_db
def test_403_offers_sign_in_only_to_guests():
    request = RequestFactory().get("/private/?x=1")
    from django.contrib.auth.models import AnonymousUser
    request.user = AnonymousUser()
    resp = permission_denied(request, Exception("nope"))
    html = _body(resp)
    assert resp.status_code == 403
    assert "You do not have access to this page" in html
    assert 'name="robots" content="noindex, nofollow"' in html
    assert "/account/login/?next=/private/%3Fx%3D1" in html
    assert "nope" not in html  # exception text never reaches the page


@pytest.mark.django_db
def test_403_hides_sign_in_for_members(django_user_model):
    user = django_user_model.objects.create_user(username="e403", email="e403@example.test", password="S3curePassw0rd!x")
    request = RequestFactory().get("/private/")
    request.user = user
    html = _body(permission_denied(request, Exception("x")))
    assert "/account/login/?next=" not in html


def test_500_is_standalone_and_honest():
    resp = server_error(RequestFactory().get("/boom/"))
    html = _body(resp)
    assert resp.status_code == 500
    assert "<h1" in html and "Something went wrong on our side" in html
    assert 'name="robots" content="noindex, nofollow"' in html
    # renders without the site base template, request context or database
    assert "dc-navbar" not in html and "csrf" not in html.lower()
    for claim in ("team has been notified", "REF:", "TIMESTAMP", "document.write"):
        assert claim not in html
