import pytest
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db

@override_settings(DEBUG=False, ROOT_URLCONF="apps.corelib.tests.urls_403")
def test_permission_denied_403_renders_custom_template():
    # Don’t raise exceptions so we can assert on the 403 response
    c = Client(raise_request_exception=False)
    r = c.get("/forbidden/")
    assert r.status_code == 403
    body = r.content.decode()
    assert "Access denied" in body
    assert "Go home" in body

@override_settings(DEBUG=False, ROOT_URLCONF="apps.corelib.tests.urls_csrf")
def test_csrf_failure_renders_custom_403_csrf_template():
    # Enforce CSRF checks in the test client
    c = Client(enforce_csrf_checks=True, raise_request_exception=False)
    # POST without a CSRF token should 403
    r = c.post("/needs-csrf/", data={"x": "y"})
    assert r.status_code == 403
    body = r.content.decode()
    assert "CSRF verification failed" in body
