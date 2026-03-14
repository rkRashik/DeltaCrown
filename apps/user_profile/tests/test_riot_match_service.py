from unittest.mock import Mock, patch

import pytest

from apps.user_profile.services.riot_match_service import (
    RiotMatchServiceError,
    fetch_match_details,
    fetch_recent_valorant_matches,
)


def _mock_response(*, status_code=200, json_data=None, headers=None):
    response = Mock()
    response.status_code = status_code
    response.headers = headers or {}
    if json_data is None:
        response.json.side_effect = ValueError("bad json")
    else:
        response.json.return_value = json_data
    return response


def test_fetch_recent_valorant_matches_handles_429_retry_after(settings):
    settings.RIOT_API_KEY = "RGAPI-test-key"
    response = _mock_response(status_code=429, json_data={"status": {"message": "rate limited"}}, headers={"Retry-After": "17"})

    with patch("apps.user_profile.services.riot_match_service.requests.get", return_value=response):
        with pytest.raises(RiotMatchServiceError) as exc:
            fetch_recent_valorant_matches("puuid-123", region="ap")

    assert exc.value.error_code == "RIOT_RATE_LIMITED"
    assert exc.value.status_code == 429
    assert exc.value.metadata["retry_after_seconds"] == 17
    assert exc.value.metadata["region"] == "ap"


def test_fetch_match_details_handles_malformed_json(settings):
    settings.RIOT_API_KEY = "RGAPI-test-key"
    response = _mock_response(status_code=200, json_data=None)

    with patch("apps.user_profile.services.riot_match_service.requests.get", return_value=response):
        with pytest.raises(RiotMatchServiceError) as exc:
            fetch_match_details("match-123", region="ap")

    assert exc.value.error_code == "RIOT_INVALID_RESPONSE"
    assert exc.value.status_code == 502
