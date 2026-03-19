"""
Riot Match-V5 Fetcher — Phase 2 (AUTOMATED_TOURNAMENTS_ROADMAP.md)

Fetches a Valorant match from the Riot Match-V1 API and parses it into a
ParsedMatchResult for consumption by MatchIngestionService.

Usage::

    fetcher = RiotMatchV5Fetcher()
    payload = fetcher.fetch(cluster="ap", match_id="APAC1-12345")
    result  = fetcher.parse_valorant_result(
        payload=payload,
        p1_puuids={"puuid-a", "puuid-b", ...},
        p2_puuids={"puuid-c", "puuid-d", ...},
    )
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import requests
from django.conf import settings

from apps.tournament_ops.services.match_ingestion_service import ParsedMatchResult

logger = logging.getLogger(__name__)

_VAL_MATCH_URL = "https://{cluster}.api.riotgames.com/val/match/v1/matches/{match_id}"

# Supported Riot regional routing clusters for Valorant
VALID_CLUSTERS: frozenset[str] = frozenset({"ap", "br", "eu", "kr", "latam", "na"})


class RiotMatchFetchError(Exception):
    """Raised when the Riot API cannot be reached or returns unexpected data."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RiotMatchParseError(ValueError):
    """Raised when match payload cannot be parsed into a valid result."""


class RiotMatchV5Fetcher:
    """
    Fetches and parses a Valorant match from the Riot Match-V1 API.

    The Riot API key is read from ``settings.RIOT_API_KEY`` at call time.
    All network errors surface as ``RiotMatchFetchError`` so callers can
    decide whether to retry or escalate.
    """

    DEFAULT_TIMEOUT: int = 10

    # ------------------------------------------------------------------ #
    #  Public interface                                                    #
    # ------------------------------------------------------------------ #

    def fetch(self, cluster: str, match_id: str) -> dict[str, Any]:
        """
        Retrieve a Valorant match payload from the Riot Match-V1 endpoint.

        Args:
            cluster:  Regional routing cluster (``ap``, ``eu``, ``na``, etc.).
            match_id: Riot match identifier (e.g. ``"APAC1-12345"``).

        Returns:
            The raw JSON payload as a ``dict``.

        Raises:
            RiotMatchFetchError: On any HTTP or network error.
        """
        if cluster not in VALID_CLUSTERS:
            raise RiotMatchFetchError(
                f"Invalid Riot cluster '{cluster}'. Valid: {sorted(VALID_CLUSTERS)}"
            )
        if not match_id:
            raise RiotMatchFetchError("match_id must not be empty")

        riot_api_key = getattr(settings, "RIOT_API_KEY", "")
        if not riot_api_key:
            raise RiotMatchFetchError(
                "RIOT_API_KEY is not configured — cannot fetch match data",
                status_code=500,
            )

        url = _VAL_MATCH_URL.format(cluster=cluster, match_id=match_id)
        try:
            response = requests.get(
                url,
                headers={"X-Riot-Token": riot_api_key, "Accept": "application/json"},
                timeout=self.DEFAULT_TIMEOUT,
            )
        except requests.Timeout as exc:
            raise RiotMatchFetchError(
                f"Riot API timed out for match {match_id} on cluster {cluster}",
                status_code=504,
            ) from exc
        except requests.RequestException as exc:
            raise RiotMatchFetchError(
                f"Network error fetching Riot match {match_id}: {exc}",
                status_code=502,
            ) from exc

        if response.status_code == 404:
            raise RiotMatchFetchError(
                f"Riot match {match_id} not found on cluster {cluster}",
                status_code=404,
            )
        if response.status_code == 429:
            raise RiotMatchFetchError(
                "Riot API rate limit exceeded — back off and retry",
                status_code=429,
            )
        if response.status_code >= 400:
            raise RiotMatchFetchError(
                f"Riot API returned HTTP {response.status_code} for match {match_id}",
                status_code=response.status_code,
            )

        payload = response.json()
        if not isinstance(payload, dict):
            raise RiotMatchFetchError(
                f"Unexpected Riot API response type: {type(payload).__name__}",
                status_code=502,
            )

        return payload

    def parse_valorant_result(
        self,
        payload: dict[str, Any],
        p1_puuids: set[str],
        p2_puuids: set[str],
    ) -> ParsedMatchResult:
        """
        Parse a Riot Match-V1 payload into a ``ParsedMatchResult``.

        Algorithm:
        1. Build a ``{puuid → teamId}`` map from ``payload["players"]``.
        2. Resolve each participant's canonical teamId via majority vote among
           their known PUUIDs (tolerates partial roster overlap in scrimmages).
        3. Look up ``roundsWon`` and ``won`` from ``payload["teams"]``.
        4. ``winner_slot`` = 1 if participant1's team won, else 2.
        5. ``participant1_score`` / ``participant2_score`` = rounds won.

        Args:
            payload:   Raw Riot Match-V1 JSON dict (from :meth:`fetch`).
            p1_puuids: Set of PUUIDs for participant 1 (team or solo player).
            p2_puuids: Set of PUUIDs for participant 2.

        Returns:
            ``ParsedMatchResult`` with scores and winner_slot populated.

        Raises:
            RiotMatchParseError: If teams cannot be resolved or payload is
                structurally invalid.
        """
        raw_players: list[dict] = payload.get("players") or []
        raw_teams: list[dict] = payload.get("teams") or []

        if not raw_players:
            raise RiotMatchParseError(
                "Riot match payload contains no 'players' array"
            )
        if not raw_teams:
            raise RiotMatchParseError(
                "Riot match payload contains no 'teams' array"
            )

        # Map each known PUUID to its Valorant teamId ("Blue" / "Red")
        puuid_to_team: dict[str, str] = {
            p["puuid"]: p["teamId"]
            for p in raw_players
            if p.get("puuid") and p.get("teamId")
        }

        p1_team = self._resolve_team_id(puuid_to_team, p1_puuids, slot=1)
        p2_team = self._resolve_team_id(puuid_to_team, p2_puuids, slot=2)

        if p1_team == p2_team:
            raise RiotMatchParseError(
                f"Both participants resolved to the same Valorant team '{p1_team}'. "
                "PUUID sets may be incorrect."
            )

        # Build team stats lookup
        team_stats: dict[str, dict] = {
            t["teamId"]: t for t in raw_teams if t.get("teamId")
        }

        if p1_team not in team_stats:
            raise RiotMatchParseError(
                f"Participant 1 team '{p1_team}' not found in match teams"
            )
        if p2_team not in team_stats:
            raise RiotMatchParseError(
                f"Participant 2 team '{p2_team}' not found in match teams"
            )

        p1_stats = team_stats[p1_team]
        p2_stats = team_stats[p2_team]

        p1_score: int = int(p1_stats.get("roundsWon") or 0)
        p2_score: int = int(p2_stats.get("roundsWon") or 0)
        p1_won: bool = bool(p1_stats.get("won", False))

        # Validate that exactly one team won (guard against draw payload bugs)
        p2_won: bool = bool(p2_stats.get("won", False))
        if p1_won == p2_won:
            # Attempt score tiebreak before raising
            if p1_score != p2_score:
                p1_won = p1_score > p2_score
            else:
                raise RiotMatchParseError(
                    "Cannot determine winner: both teams have identical 'won' flags "
                    f"and equal round scores ({p1_score}–{p2_score})"
                )

        winner_slot = 1 if p1_won else 2

        game_scores = [
            {
                "game": 1,
                "p1": p1_score,
                "p2": p2_score,
                "winner_slot": winner_slot,
                "p1_team": p1_team,
                "p2_team": p2_team,
            }
        ]

        logger.info(
            "[RiotMatchV5Fetcher] Parsed Valorant result: p1=%s(%d) p2=%s(%d) winner_slot=%d",
            p1_team, p1_score, p2_team, p2_score, winner_slot,
        )

        return ParsedMatchResult(
            winner_slot=winner_slot,
            participant1_score=p1_score,
            participant2_score=p2_score,
            game_scores=game_scores,
        )

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _resolve_team_id(
        puuid_to_team: dict[str, str],
        puuids: set[str],
        slot: int,
    ) -> str:
        """
        Return the majority teamId for a set of PUUIDs.

        Uses a Counter vote so that a single missing PUUID (e.g., substitute
        player) doesn't break resolution.

        Raises:
            RiotMatchParseError: If no PUUIDs from the set appear in the match.
        """
        matched = [puuid_to_team[p] for p in puuids if p in puuid_to_team]
        if not matched:
            raise RiotMatchParseError(
                f"Participant {slot}: none of the provided PUUIDs appear in this "
                "Riot match. Verify lobby_info.riot_match_id and roster PUUIDs."
            )
        (team_id, _) = Counter(matched).most_common(1)[0]
        return team_id
