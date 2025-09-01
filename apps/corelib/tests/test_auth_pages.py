import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db

def test_login_logout_flow(client):
    User = get_user_model()
    User.objects.create_user(username="demo", password="pass12345", email="demo@example.com")

    # Login page renders
    r = client.get("/accounts/login/")
    assert r.status_code == 200
    assert "Sign in" in r.content.decode()

    # Login works
    r = client.post("/accounts/login/", {"username": "demo", "password": "pass12345"}, follow=True)
    assert r.status_code == 200  # redirected to home

    # Logout works
    r = client.get("/accounts/logout/", follow=True)
    assert r.status_code == 200
