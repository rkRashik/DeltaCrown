"""Riot Valorant match history fetching helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class RiotMatchServiceError(Exception):
    error_code: str
    message: str
    status_code: int = 400
    metadata: dict[str, Any] | None = None


def _timeout_seconds() -> int:
    timeout = getattr(settings, "RIOT_MATCH_TIMEOUT_SECONDS", 10)
    try:
        return max(3, int(timeout))
    except (TypeError, ValueError):
        return 10


def _require_riot_api_key() -> str:
    api_key = str(getattr(settings, "RIOT_API_KEY", "")).strip()
    if not api_key:
        raise RiotMatchServiceError(
            error_code="RIOT_API_KEY_MISSING",
            message="RIOT_API_KEY is not configured",
            status_code=500,
        )
    return api_key


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_retry_after(response: requests.Response) -> int | None:
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        return int(retry_after)
    except (TypeError, ValueError):
        return None


def _riot_get(url: str, *, region: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    api_key = _require_riot_api_key()
    headers = {
        "X-Riot-Token": api_key,
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=_timeout_seconds(),
        )
    except requests.Timeout as exc:
        raise RiotMatchServiceError(
            error_code="RIOT_TIMEOUT",
            message="Riot match API request timed out",
            status_code=504,
            metadata={"region": region},
        ) from exc
    except requests.RequestException as exc:
        raise RiotMatchServiceError(
            error_code="RIOT_NETWORK_ERROR",
            message="Unable to reach Riot match API",
            status_code=502,
            metadata={"region": region},
        ) from exc

    if response.status_code == 429:
        raise RiotMatchServiceError(
            error_code="RIOT_RATE_LIMITED",
            message="Riot match API rate limit exceeded",
            status_code=429,
            metadata={
                "region": region,
                "retry_after_seconds": _parse_retry_after(response),
            },
        )

    if response.status_code >= 400:
        payload = _safe_json(response)
        raise RiotMatchServiceError(
            error_code="RIOT_HTTP_ERROR",
            message=payload.get("status", {}).get("message") or "Riot match API request failed",
            status_code=response.status_code,
            metadata={
                "region": region,
                "status_code": response.status_code,
                "riot_status": payload.get("status") if payload else None,
            },
        )

    payload = _safe_json(response)
    if not payload:
        raise RiotMatchServiceError(
            error_code="RIOT_INVALID_RESPONSE",
            message="Riot match API returned invalid JSON",
            status_code=502,
            metadata={"region": region},
        )
    return payload


def fetch_recent_valorant_matches(puuid: str, region: str = "ap") -> dict[str, Any]:
    """Fetch recent Valorant match ids for a player by puuid."""
    normalized_region = str(region or "ap").strip().lower() or "ap"
    normalized_puuid = str(puuid or "").strip()
    if not normalized_puuid:
        raise RiotMatchServiceError(
            error_code="MISSING_PUUID",
            message="puuid is required",
            status_code=400,
        )

    url = (
        f"https://{normalized_region}.api.riotgames.com/val/match/v1/"
        f"matchlists/by-puuid/{normalized_puuid}"
    )
    payload = _riot_get(url, region=normalized_region)

    history = payload.get("history", []) if isinstance(payload.get("history"), list) else []
    matches = []
    for item in history:
        if not isinstance(item, dict):
            continue
        match_id = item.get("matchId")
        if not match_id:
            continue
        matches.append(
            {
                "match_id": match_id,
                "game_start_time_millis": item.get("gameStartTimeMillis"),
                "queue_id": item.get("queueId"),
            }
        )

    return {
        "puuid": normalized_puuid,
        "region": normalized_region,
        "match_ids": [match["match_id"] for match in matches],
        "matches": matches,
    }


def fetch_match_details(match_id: str, region: str = "ap") -> dict[str, Any]:
    """Fetch detailed Valorant match data including scoreboard and rounds."""
    normalized_region = str(region or "ap").strip().lower() or "ap"
    normalized_match_id = str(match_id or "").strip()
    if not normalized_match_id:
        raise RiotMatchServiceError(
            error_code="MISSING_MATCH_ID",
            message="match_id is required",
            status_code=400,
        )

    url = f"https://{normalized_region}.api.riotgames.com/val/match/v1/matches/{normalized_match_id}"
    payload = _riot_get(url, region=normalized_region)

    match_info = payload.get("matchInfo", {}) if isinstance(payload.get("matchInfo"), dict) else {}
    players = payload.get("players", []) if isinstance(payload.get("players"), list) else []
    scoreboard = []
    for player in players:
        if not isinstance(player, dict):
            continue
        stats = player.get("stats", {}) if isinstance(player.get("stats"), dict) else {}
        scoreboard.append(
            {
                "puuid": player.get("puuid"),
                "game_name": player.get("gameName"),
                "tag_line": player.get("tagLine"),
                "team_id": player.get("teamId"),
                "character_id": player.get("characterId"),
                "score": stats.get("score"),
                "kills": stats.get("kills"),
                "deaths": stats.get("deaths"),
                "assists": stats.get("assists"),
                "rounds_played": stats.get("roundsPlayed"),
            }
        )

    return {
        "match_id": normalized_match_id,
        "region": normalized_region,
        "match_info": {
            "map_id": match_info.get("mapId"),
            "game_version": match_info.get("gameVersion"),
            "game_length_millis": match_info.get("gameLengthMillis"),
            "queue_id": match_info.get("queueId"),
            "season_id": match_info.get("seasonId"),
            "game_start_millis": match_info.get("gameStartMillis"),
        },
        "scoreboard": scoreboard,
        "teams": payload.get("teams", []) if isinstance(payload.get("teams"), list) else [],
        "round_results": payload.get("roundResults", []) if isinstance(payload.get("roundResults"), list) else [],
    }