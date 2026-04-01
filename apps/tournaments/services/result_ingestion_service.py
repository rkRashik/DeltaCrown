"""
Phase 5 §5.4–5.5: Automated Result Ingestion Service.

Adapter-based service that fetches match results from external game APIs
(Riot Games, Steam/Valve) and compares them against player-submitted scores.

Architecture:
  AutomatedResultIngestionService
    ├─ RiotApiAdapter    (Valorant)
    ├─ SteamApiAdapter   (CS2, Dota 2)
    └─ (future adapters)

Mismatch handling:
  1. Compute field-level diff between manual and API payloads.
  2. If ANY score field differs → status = MISMATCH.
  3. Publish ``match.integrity_flagged`` event to the event bus.
  4. Admin receives alert in the moderation dashboard.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone as dt_timezone
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("deltacrown.ingestion")


# ---------------------------------------------------------------------------
# Abstract adapter interface
# ---------------------------------------------------------------------------

class BaseApiAdapter(ABC):
    """Interface every game API adapter must implement."""

    name: str = ""

    @abstractmethod
    def fetch_match_result(
        self, match_external_id: str, **kwargs
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Fetch the official match result from the external API.

        Returns:
            (success: bool, payload: dict)
            On failure, payload should contain {"error": "..."}.
        """

    @abstractmethod
    def normalize_payload(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize raw API response into our canonical stat schema so it
        can be compared field-by-field against the manual submission.

        Canonical keys: participant1_score, participant2_score, winner_id,
        plus per-player stat dicts keyed by player external ID.
        """


# ---------------------------------------------------------------------------
# Riot Games adapter (Valorant, future: LoL)
# ---------------------------------------------------------------------------

class RiotApiAdapter(BaseApiAdapter):
    """Adapter for Riot Games API (Valorant match-v1 endpoint)."""

    name = "riot"

    def __init__(self):
        self.api_key = getattr(settings, "RIOT_API_KEY", "")
        self.base_url = getattr(
            settings,
            "RIOT_API_BASE_URL",
            "https://api.henrikdev.xyz/valorant/v4",
        )

    def fetch_match_result(
        self, match_external_id: str, **kwargs
    ) -> Tuple[bool, Dict[str, Any]]:
        if not self.api_key:
            return False, {"error": "RIOT_API_KEY not configured"}

        import urllib.request
        import json

        url = f"{self.base_url}/match/{match_external_id}"
        req = urllib.request.Request(url)
        req.add_header("Authorization", self.api_key)
        req.add_header("Accept", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            return True, data
        except Exception as exc:
            logger.warning("Riot API fetch failed for %s: %s", match_external_id, exc)
            return False, {"error": str(exc)}

    def normalize_payload(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        data = raw.get("data", raw)
        teams = data.get("teams", [])
        p1_score = teams[0].get("rounds", {}).get("won", 0) if len(teams) > 0 else 0
        p2_score = teams[1].get("rounds", {}).get("won", 0) if len(teams) > 1 else 0

        players = {}
        for p in data.get("players", []):
            pid = p.get("puuid", p.get("name", ""))
            stats = p.get("stats", {})
            players[pid] = {
                "kills": stats.get("kills", 0),
                "deaths": stats.get("deaths", 0),
                "assists": stats.get("assists", 0),
                "acs": stats.get("score", 0),
            }

        return {
            "participant1_score": p1_score,
            "participant2_score": p2_score,
            "players": players,
        }


# ---------------------------------------------------------------------------
# Steam / Valve adapter (CS2, Dota 2)
# ---------------------------------------------------------------------------

class SteamApiAdapter(BaseApiAdapter):
    """Adapter for Steam Web API (CS2, Dota 2 match history)."""

    name = "steam"

    def __init__(self):
        self.api_key = getattr(settings, "STEAM_API_KEY", "")

    def fetch_match_result(
        self, match_external_id: str, **kwargs
    ) -> Tuple[bool, Dict[str, Any]]:
        if not self.api_key:
            return False, {"error": "STEAM_API_KEY not configured"}

        import urllib.request
        import json

        game = kwargs.get("game_slug", "dota2")
        if game == "dota2":
            url = (
                f"https://api.steampowered.com/IDOTA2Match_570/"
                f"GetMatchDetails/v1/?key={self.api_key}&match_id={match_external_id}"
            )
        else:
            # CS2 — uses a different endpoint pattern
            url = (
                f"https://api.steampowered.com/ICSGOServers_730/"
                f"GetGameServersStatus/v1/?key={self.api_key}"
            )
            return False, {"error": "CS2 match detail endpoint requires GCPD data — manual review needed"}

        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            return True, data
        except Exception as exc:
            logger.warning("Steam API fetch failed for %s: %s", match_external_id, exc)
            return False, {"error": str(exc)}

    def normalize_payload(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        result = raw.get("result", raw)
        radiant_win = result.get("radiant_win", False)

        players = {}
        for p in result.get("players", []):
            pid = str(p.get("account_id", ""))
            players[pid] = {
                "kills": p.get("kills", 0),
                "deaths": p.get("deaths", 0),
                "assists": p.get("assists", 0),
                "gpm": p.get("gold_per_min", 0),
                "xpm": p.get("xp_per_min", 0),
                "hero_damage": p.get("hero_damage", 0),
                "tower_damage": p.get("tower_damage", 0),
            }

        return {
            "participant1_score": 1 if radiant_win else 0,
            "participant2_score": 0 if radiant_win else 1,
            "players": players,
        }


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

_ADAPTER_REGISTRY: Dict[str, type] = {
    "riot": RiotApiAdapter,
    "steam": SteamApiAdapter,
}


def get_adapter(source: str) -> Optional[BaseApiAdapter]:
    """Get an adapter instance by source name."""
    cls = _ADAPTER_REGISTRY.get(source)
    return cls() if cls else None


def register_adapter(source: str, adapter_cls: type):
    """Register a custom adapter at runtime."""
    _ADAPTER_REGISTRY[source] = adapter_cls


# ---------------------------------------------------------------------------
# Core ingestion service
# ---------------------------------------------------------------------------

# Map game slugs to their API source
_GAME_SOURCE_MAP: Dict[str, str] = {
    "valorant": "riot",
    "cs2": "steam",
    "dota2": "steam",
}


class AutomatedResultIngestionService:
    """
    Orchestrates automated result fetching and integrity checking.

    Usage:
        result = AutomatedResultIngestionService.verify_match(match)
        # result: MatchIntegrityCheck instance
    """

    @staticmethod
    def get_source_for_game(game_slug: str) -> Optional[str]:
        """Map game slug to API adapter source."""
        return _GAME_SOURCE_MAP.get(game_slug)

    @staticmethod
    def verify_match(match, *, external_match_id: str = "") -> "MatchIntegrityCheck":
        """
        Main entry point: fetch API data, compare, and store integrity check.

        1. Determine the API source from the match's game.
        2. Fetch official result via the adapter.
        3. Build the manual payload from the Match model.
        4. Compute diff → decide MATCH or MISMATCH.
        5. Persist MatchIntegrityCheck.
        6. If mismatch, fire event bus alert.
        """
        from apps.tournaments.models.result_ingestion import MatchIntegrityCheck

        game = getattr(match.tournament, "game", None)
        game_slug = getattr(game, "slug", "") if game else ""
        source_key = AutomatedResultIngestionService.get_source_for_game(game_slug)

        # Create or get the integrity check record
        check, _created = MatchIntegrityCheck.objects.get_or_create(
            match=match,
            defaults={"source": source_key or "manual"},
        )

        # No API adapter available — mark as skipped
        if not source_key:
            check.status = MatchIntegrityCheck.Status.SKIPPED
            check.save(update_fields=["status", "updated_at"])
            return check

        adapter = get_adapter(source_key)
        if not adapter:
            check.status = MatchIntegrityCheck.Status.API_ERROR
            check.diff = {"error": f"No adapter for source '{source_key}'"}
            check.save(update_fields=["status", "diff", "updated_at"])
            return check

        # Resolve external match ID
        ext_id = external_match_id or (match.lobby_info or {}).get("external_match_id", "")
        if not ext_id:
            check.status = MatchIntegrityCheck.Status.API_ERROR
            check.diff = {"error": "No external_match_id available"}
            check.save(update_fields=["status", "diff", "updated_at"])
            return check

        # Fetch from API
        success, raw_payload = adapter.fetch_match_result(ext_id, game_slug=game_slug)
        check.fetched_at = timezone.now()

        if not success:
            check.status = MatchIntegrityCheck.Status.API_ERROR
            check.api_payload = raw_payload
            check.save(update_fields=["status", "api_payload", "fetched_at", "updated_at"])
            return check

        # Normalize
        api_normalized = adapter.normalize_payload(raw_payload)
        check.api_payload = raw_payload

        # Build manual payload from model
        manual = {
            "participant1_score": match.participant1_score,
            "participant2_score": match.participant2_score,
        }
        check.manual_payload = manual

        # Compute diff
        diff = AutomatedResultIngestionService._compute_diff(manual, api_normalized)
        check.diff = diff

        # Decide verdict
        if diff.get("score_mismatch"):
            check.status = MatchIntegrityCheck.Status.MISMATCH
            logger.warning(
                "INTEGRITY MISMATCH — Match %s: manual=%s vs api=%s",
                match.pk, manual, api_normalized,
            )
            AutomatedResultIngestionService._fire_mismatch_event(match, diff)
        else:
            check.status = MatchIntegrityCheck.Status.MATCH

        check.save(update_fields=[
            "status", "manual_payload", "api_payload", "diff",
            "fetched_at", "updated_at",
        ])
        return check

    @staticmethod
    def _compute_diff(
        manual: Dict[str, Any], api: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare score fields and return a structured diff."""
        diff: Dict[str, Any] = {}
        score_mismatch = False

        for key in ("participant1_score", "participant2_score"):
            m_val = manual.get(key, 0)
            a_val = api.get(key, 0)
            if int(m_val) != int(a_val):
                diff[key] = {"manual": m_val, "api": a_val}
                score_mismatch = True

        diff["score_mismatch"] = score_mismatch
        return diff

    @staticmethod
    def _fire_mismatch_event(match, diff: Dict[str, Any]):
        """Publish integrity mismatch event to the event bus."""
        try:
            from common.events.event_bus import get_event_bus, Event
            bus = get_event_bus()
            bus.publish(Event(
                name="match.integrity_flagged",
                payload={
                    "match_id": match.pk,
                    "tournament_id": match.tournament_id,
                    "diff": diff,
                },
            ))
        except Exception as exc:
            logger.debug("Event bus publish skipped: %s", exc)
