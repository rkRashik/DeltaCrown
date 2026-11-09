"""Regression tests for audit F6: two URL patterns shared the name ``economy:pin_setup``.

The HTML page keeps ``economy:pin_setup``; the POST-only JSON API is ``economy:pin_setup_api``
at its unchanged path. Synthetic users only; no balances or transactions are touched.
"""
import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.economy.models import DeltaCrownWallet
from apps.user_profile.models import UserProfile

pytestmark = pytest.mark.django_db
User = get_user_model()
HTML_PATH, API_PATH = '/pin/setup/', '/api/wallet/pin/setup/'


@pytest.fixture
def player():
    user = User.objects.create_user(username='pin_route_user', email='pin_route@example.test', password='pw-12345!')
    profile, _ = UserProfile.objects.get_or_create(user=user)
    DeltaCrownWallet.objects.get_or_create(profile=profile)
    return user


@pytest.fixture
def signed_in(player):
    client = Client()
    client.force_login(player)
    return client


def test_url_names_resolve_to_distinct_paths():
    assert reverse('economy:pin_setup') == HTML_PATH
    assert reverse('economy:pin_setup_api') == API_PATH


def test_html_page_renders_for_signed_in_player_and_requires_login(signed_in):
    response = signed_in.get(HTML_PATH, secure=True)
    assert response.status_code == 200
    assert 'economy/pin_setup.html' in [t.name for t in response.templates]
    anonymous = Client().get(HTML_PATH, secure=True)
    assert anonymous.status_code == 302 and '/login' in anonymous['Location']


def test_withdrawal_without_a_pin_redirects_to_the_html_page(signed_in):
    response = signed_in.get('/withdrawal/request/', secure=True)
    assert response.status_code == 302 and response['Location'] == HTML_PATH
    assert signed_in.get(response['Location'], secure=True).status_code == 200


def test_wallet_dashboard_pin_link_targets_the_html_page(signed_in):
    html = signed_in.get('/wallet/dashboard/', secure=True).content.decode()
    assert f'href="{HTML_PATH}"' in html
    assert f'href="{API_PATH}"' not in html


def test_api_stays_post_only_and_login_protected(signed_in):
    assert signed_in.get(API_PATH, secure=True).status_code == 405
    anonymous = Client().post(API_PATH, {'pin': '123456', 'confirm_pin': '123456'}, secure=True)
    assert anonymous.status_code == 302 and '/login' in anonymous['Location']


def test_api_post_contract_is_unchanged(signed_in, player):
    bad = signed_in.post(API_PATH, {'pin': '123', 'confirm_pin': '123'}, secure=True)
    assert bad.status_code == 400 and 'exactly 6 digits' in json.dumps(bad.json())
    ok = signed_in.post(API_PATH, {'pin': '123456', 'confirm_pin': '123456'}, secure=True)
    assert ok.status_code == 200 and ok.json().get('success') is True
    assert DeltaCrownWallet.objects.get(profile__user=player).has_pin()


def test_api_still_enforces_csrf(player):
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(player)
    assert strict.post(API_PATH, {'pin': '123456', 'confirm_pin': '123456'}, secure=True).status_code == 403
    assert not DeltaCrownWallet.objects.get(profile__user=player).has_pin()
