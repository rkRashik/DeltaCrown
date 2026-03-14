import json
from unittest.mock import Mock, patch

import pytest
from django.urls import reverse

from apps.games.models import Game
from apps.user_profile.models import GameOAuthConnection, GameProfile


@pytest.fixture(autouse=True)
def _seed_games(ensure_common_games):
    pass


def _mock_response(*, status_code=200, json_data=None, text="", headers=None):
    response = Mock()
    response.status_code = status_code
    response.text = text
    response.headers = headers or {}
    if json_data is None:
        response.json.side_effect = ValueError("no json")
    else:
        response.json.return_value = json_data
    return response


def _get_riot_state(client):
    response = client.get(reverse("user_profile:riot_oauth_login"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    return payload["data"]["state"]


def _get_steam_state(client, game_slug):
    response = client.get(reverse("user_profile:steam_openid_login"), {"game": game_slug})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    return payload["data"]["state"]


def _get_epic_state(client):
    response = client.get(reverse("user_profile:epic_oauth_login"))
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    return payload["data"]["state"]


def _ensure_rocketleague_game():
    Game.objects.get_or_create(
        slug="rocketleague",
        defaults={
            "name": "Rocket League",
            "display_name": "Rocket League",
            "short_code": "RL",
            "is_active": True,
            "category": "SPORTS",
        },
    )


@pytest.mark.django_db
def test_riot_callback_success_creates_passport_and_oauth_connection(authenticated_client, user, settings):
    settings.RIOT_CLIENT_ID = "riot-client"
    settings.RIOT_CLIENT_SECRET = "riot-secret"
    settings.RIOT_REDIRECT_URI = "http://testserver/profile/api/oauth/riot/callback/"
    settings.RIOT_API_KEY = "RGAPI-test-key"

    state = _get_riot_state(authenticated_client)

    token_response = _mock_response(
        json_data={
            "access_token": "access-123",
            "refresh_token": "refresh-123",
            "expires_in": 3600,
            "scope": "openid offline_access",
            "token_type": "Bearer",
        }
    )
    userinfo_response = _mock_response(json_data={"sub": "puuid-123"})
    account_response = _mock_response(json_data={"gameName": "PlayerOne", "tagLine": "TAG"})

    with patch("apps.user_profile.services.oauth_riot_service.requests.post", return_value=token_response) as mock_post:
        with patch(
            "apps.user_profile.services.oauth_riot_service.requests.get",
            side_effect=[userinfo_response, account_response],
        ) as mock_get:
            response = authenticated_client.post(
                reverse("user_profile:riot_oauth_callback"),
                data=json.dumps({"code": "good-code", "state": state}),
                content_type="application/json",
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    passport = GameProfile.objects.get(user=user, game__slug="valorant")
    assert passport.ign == "PlayerOne"
    assert passport.discriminator == "#TAG"
    assert passport.identity_key == "PlayerOne#TAG"

    oauth_connection = GameOAuthConnection.objects.get(passport=passport)
    assert oauth_connection.provider == GameOAuthConnection.Provider.RIOT
    assert oauth_connection.provider_account_id == "puuid-123"
    assert oauth_connection.access_token == "access-123"
    assert oauth_connection.refresh_token == "refresh-123"

    mock_post.assert_called_once()
    assert mock_get.call_count == 2


@pytest.mark.django_db
def test_riot_callback_invalid_code_returns_structured_error(authenticated_client, settings):
    settings.RIOT_CLIENT_ID = "riot-client"
    settings.RIOT_CLIENT_SECRET = "riot-secret"
    settings.RIOT_REDIRECT_URI = "http://testserver/profile/api/oauth/riot/callback/"

    state = _get_riot_state(authenticated_client)

    token_response = _mock_response(
        status_code=400,
        json_data={
            "error": "invalid_grant",
            "error_description": "Invalid authorization code",
        },
    )

    with patch("apps.user_profile.services.oauth_riot_service.requests.post", return_value=token_response):
        response = authenticated_client.get(
            reverse("user_profile:riot_oauth_callback"),
            {"code": "bad-code", "state": state},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error_code"] == "RIOT_INVALID_CODE"
    assert GameOAuthConnection.objects.count() == 0


@pytest.mark.django_db
def test_steam_callback_success_creates_cs2_passport_and_oauth_connection(authenticated_client, user, settings):
    settings.STEAM_API_KEY = "steam-api-key"

    state = _get_steam_state(authenticated_client, "cs2")
    verification_response = _mock_response(text="ns:http://specs.openid.net/auth/2.0\nis_valid:true\n")
    summary_response = _mock_response(
        json_data={
            "response": {
                "players": [
                    {
                        "steamid": "76561198012345678",
                        "personaname": "SteamUser",
                        "avatar": "https://cdn.example/avatar.jpg",
                        "avatarmedium": "https://cdn.example/avatar_medium.jpg",
                        "avatarfull": "https://cdn.example/avatar_full.jpg",
                        "profileurl": "https://steamcommunity.com/id/steamuser/",
                    }
                ]
            }
        }
    )

    with patch("apps.user_profile.services.oauth_steam_service.requests.post", return_value=verification_response) as mock_post:
        with patch("apps.user_profile.services.oauth_steam_service.requests.get", return_value=summary_response) as mock_get:
            response = authenticated_client.get(
                reverse("user_profile:steam_openid_callback"),
                {
                    "state": state,
                    "game": "cs2",
                    "openid.ns": "http://specs.openid.net/auth/2.0",
                    "openid.mode": "id_res",
                    "openid.claimed_id": "https://steamcommunity.com/openid/id/76561198012345678",
                    "openid.identity": "https://steamcommunity.com/openid/id/76561198012345678",
                },
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    passport = GameProfile.objects.get(user=user, game__slug="cs2")
    assert passport.ign == "SteamUser"
    assert passport.identity_key == "76561198012345678"

    oauth_connection = GameOAuthConnection.objects.get(passport=passport)
    assert oauth_connection.provider == GameOAuthConnection.Provider.STEAM
    assert oauth_connection.provider_account_id == "76561198012345678"

    post_payload = mock_post.call_args.kwargs["data"]
    assert post_payload["openid.mode"] == "check_authentication"
    mock_get.assert_called_once()


@pytest.mark.django_db
def test_steam_same_id_can_link_cs2_and_dota2_for_same_user(authenticated_client, user, settings):
    settings.STEAM_API_KEY = "steam-api-key"

    verification_response = _mock_response(text="ns:http://specs.openid.net/auth/2.0\nis_valid:true\n")
    summary_response = _mock_response(
        json_data={
            "response": {
                "players": [
                    {
                        "steamid": "76561198012345678",
                        "personaname": "SteamUser",
                        "avatar": "https://cdn.example/avatar.jpg",
                        "avatarmedium": "https://cdn.example/avatar_medium.jpg",
                        "avatarfull": "https://cdn.example/avatar_full.jpg",
                        "profileurl": "https://steamcommunity.com/id/steamuser/",
                    }
                ]
            }
        }
    )

    with patch(
        "apps.user_profile.services.oauth_steam_service.requests.post",
        side_effect=[verification_response, verification_response],
    ):
        with patch(
            "apps.user_profile.services.oauth_steam_service.requests.get",
            side_effect=[summary_response, summary_response],
        ):
            cs2_state = _get_steam_state(authenticated_client, "cs2")
            cs2_response = authenticated_client.get(
                reverse("user_profile:steam_openid_callback"),
                {
                    "state": cs2_state,
                    "game": "cs2",
                    "openid.claimed_id": "https://steamcommunity.com/openid/id/76561198012345678",
                },
            )
            assert cs2_response.status_code == 200

            dota2_state = _get_steam_state(authenticated_client, "dota2")
            dota2_response = authenticated_client.get(
                reverse("user_profile:steam_openid_callback"),
                {
                    "state": dota2_state,
                    "game": "dota2",
                    "openid.claimed_id": "https://steamcommunity.com/openid/id/76561198012345678",
                },
            )
            assert dota2_response.status_code == 200

    passports = GameProfile.objects.filter(user=user, game__slug__in=["cs2", "dota2"]).order_by("game__slug")
    assert passports.count() == 2
    assert {passport.game.slug for passport in passports} == {"cs2", "dota2"}

    steam_links = GameOAuthConnection.objects.filter(
        passport__user=user,
        provider=GameOAuthConnection.Provider.STEAM,
        provider_account_id="76561198012345678",
    )
    assert steam_links.count() == 2


@pytest.mark.django_db
def test_epic_callback_success_creates_rocketleague_passport_and_oauth_connection(authenticated_client, user, settings):
    _ensure_rocketleague_game()
    settings.EPIC_CLIENT_ID = "epic-client"
    settings.EPIC_CLIENT_SECRET = "epic-secret"

    state = _get_epic_state(authenticated_client)

    token_response = _mock_response(
        json_data={
            "access_token": "epic-access-123",
            "refresh_token": "epic-refresh-123",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "basic_profile",
            "account_id": "epic-account-123",
            "displayName": "EpicUser",
        }
    )

    with patch("apps.user_profile.services.oauth_epic_service.requests.post", return_value=token_response) as mock_post:
        response = authenticated_client.post(
            reverse("user_profile:epic_oauth_callback"),
            data=json.dumps({"code": "good-code", "state": state}),
            content_type="application/json",
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True

    passport = GameProfile.objects.get(user=user, game__slug="rocketleague")
    assert passport.ign == "EpicUser"
    assert passport.identity_key == "epic-account-123"

    oauth_connection = GameOAuthConnection.objects.get(passport=passport)
    assert oauth_connection.provider == GameOAuthConnection.Provider.EPIC
    assert oauth_connection.provider_account_id == "epic-account-123"
    assert oauth_connection.access_token == "epic-access-123"
    assert oauth_connection.refresh_token == "epic-refresh-123"

    mock_post.assert_called_once()


@pytest.mark.django_db
def test_epic_callback_invalid_code_returns_structured_error(authenticated_client, settings):
    _ensure_rocketleague_game()
    settings.EPIC_CLIENT_ID = "epic-client"
    settings.EPIC_CLIENT_SECRET = "epic-secret"

    state = _get_epic_state(authenticated_client)

    token_response = _mock_response(
        status_code=400,
        json_data={
            "error": "invalid_grant",
            "error_description": "Invalid authorization code",
        },
    )

    with patch("apps.user_profile.services.oauth_epic_service.requests.post", return_value=token_response):
        response = authenticated_client.get(
            reverse("user_profile:epic_oauth_callback"),
            {"code": "bad-code", "state": state},
        )

    assert response.status_code == 400
    payload = response.json()
    assert payload["success"] is False
    assert payload["error_code"] == "EPIC_TOKEN_EXCHANGE_FAILED"
    assert GameOAuthConnection.objects.filter(provider=GameOAuthConnection.Provider.EPIC).count() == 0