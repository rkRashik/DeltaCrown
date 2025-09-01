import pytest
from django.test import override_settings

pytestmark = pytest.mark.django_db

@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver"])
def test_custom_404_template_renders(client):
    r = client.get("/this-page-does-not-exist-xyz/")
    assert r.status_code == 404
    assert "404" in r.content.decode()  # adjust to a unique string in your error template
