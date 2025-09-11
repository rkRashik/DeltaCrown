import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_dashboard_my_matches_exists(client):
    User = get_user_model()
    u = User.objects.create_user(username="bob", password="x")
    client.force_login(u)
    resp = client.get("/dashboard/matches/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_economy_wallet_exists(client):
    User = get_user_model()
    u = User.objects.create_user(username="alice", password="x")
    client.force_login(u)
    resp = client.get("/wallet/")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_ecommerce_pages_exist(client):
    # log in to avoid anonymous checkout profile access
    User = get_user_model()
    u = User.objects.create_user(username="shopper", password="x")
    client.force_login(u)
    r1 = client.get("/ecommerce/")
    assert r1.status_code == 200
    r2 = client.get("/ecommerce/checkout/", follow=True)
    assert r2.status_code == 200
