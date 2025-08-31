import pytest
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db


def test_404_page(client):
    r = client.get("/this-does-not-exist-xyz/")
    assert r.status_code == 404
    body = r.content.decode()
    assert "Page not found" in body
    assert "Go to Home" in body


# A tiny URLConf only for this test to raise a 500
TEST_URLCONF = "apps.corelib.tests.urls_500"

@override_settings(DEBUG=False, ROOT_URLCONF=TEST_URLCONF)
def test_500_page_renders():
    # Use a Client that doesn't raise exceptions so we can assert 500 response
    c = Client(raise_request_exception=False)
    r = c.get("/boom/")
    assert r.status_code == 500
    body = r.content.decode()
    assert "Something went wrong" in body
