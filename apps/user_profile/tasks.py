"""Background sync tasks for API-synced game passports."""

from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.user_profile.models import GameOAuthConnection, GameProfile
from apps.user_profile.services.riot_match_service import (
    RiotMatchServiceError,
    fetch_match_details,
    fetch_recent_valorant_matches,
)

logger = logging.getLogger(__name__)


RIOT_SUBMISSION_SOURCE = "riot_api"


AGENT_ROLE_BY_KEYWORD = {
    "jett": "Duelist",
    "raze": "Duelist",
    "phoenix": "Duelist",
    "reyna": "Duelist",
    "yoru": "Duelist",
    "neon": "Duelist",
    "iso": "Duelist",
    "waylay": "Duelist",
    "brimstone": "Controller",
    "viper": "Controller",
    "omen": "Controller",
    "astra": "Controller",
    "harbor": "Controller",
    "clove": "Controller",
    "sova": "Initiator",
    "breach": "Initiator",
    "skye": "Initiator",
    "kayo": "Initiator",
    "gekko": "Initiator",
    "fade": "Initiator",
    "tejo": "Initiator",
    "sage": "Sentinel",
    "cypher": "Sentinel",
    "killjoy": "Sentinel",
    "chamber": "Sentinel",
    "deadlock": "Sentinel",
    "vyse": "Sentinel",
}


def _setting_int(name: str, default: int, minimum: int = 0) -> int:
    raw = getattr(settings, name, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _setting_float(name: str, default: float, minimum: float = 0.0) -> float:
    raw = getattr(settings, name, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _sleep(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def _candidate_passports():
    require_verified = bool(getattr(settings, "RIOT_SYNC_REQUIRE_VERIFIED", True))

    queryset = (
        GameProfile.objects.select_related("game", "oauth_connection")
        .filter(game__slug__iexact="valorant", status=GameProfile.STATUS_ACTIVE)
        .filter(
            Q(oauth_connection__provider=GameOAuthConnection.Provider.RIOT)
            | Q(metadata__api_synced=True)
            | Q(metadata__oauth_provider=GameOAuthConnection.Provider.RIOT)
        )
        .distinct()
    )

    if require_verified:
        queryset = queryset.filter(verification_status=GameProfile.VERIFICATION_VERIFIED)

    return queryset


def _resolve_puuid_and_region(passport: GameProfile) -> tuple[str, str]:
    metadata = passport.metadata if isinstance(passport.metadata, dict) else {}
    oauth_connection = getattr(passport, "oauth_connection", None)

    puuid = str(
        metadata.get("riot_puuid")
        or (oauth_connection.provider_account_id if oauth_connection else "")
        or ""
    ).strip()

    region = str(
        (oauth_connection.game_shard if oauth_connection else "")
        or metadata.get("riot_region")
        or metadata.get("riot_shard")
        or "ap"
    ).strip().lower() or "ap"

    return puuid, region


def _call_riot_with_retry(fetch_fn, *args, **kwargs) -> dict[str, Any]:
    max_attempts = _setting_int("RIOT_SYNC_MAX_RETRY_ATTEMPTS", 2, minimum=1)
    default_wait = _setting_float("RIOT_SYNC_RATE_LIMIT_BACKOFF_SECONDS", 1.0, minimum=0.0)

    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            return fetch_fn(*args, **kwargs)
        except RiotMatchServiceError as exc:
            is_rate_limited = exc.error_code == "RIOT_RATE_LIMITED"
            if not is_rate_limited:
                raise
            if attempt >= max_attempts:
                raise RiotMatchServiceError(
                    error_code="RIOT_RETRY_EXHAUSTED",
                    message=f"Riot API retries exhausted after {max_attempts} attempt(s)",
                    status_code=429,
                ) from exc

            retry_after_seconds = None
            if isinstance(exc.metadata, dict):
                retry_after_seconds = exc.metadata.get("retry_after_seconds")

            wait_seconds = default_wait
            try:
                if retry_after_seconds is not None:
                    wait_seconds = max(default_wait, float(retry_after_seconds))
            except (TypeError, ValueError):
                wait_seconds = default_wait

            logger.warning(
                "Riot rate limited; waiting %.2fs before retry (attempt %s/%s)",
                wait_seconds,
                attempt,
                max_attempts,
            )
            _sleep(wait_seconds)


def _extract_player_match_snapshot(match_payload: dict[str, Any], puuid: str) -> dict[str, Any] | None:
    scoreboard = match_payload.get("scoreboard") if isinstance(match_payload, dict) else []
    if not isinstance(scoreboard, list):
        return None

    player_row = None
    for row in scoreboard:
        if not isinstance(row, dict):
            continue
        if str(row.get("puuid") or "").strip() == puuid:
            player_row = row
            break

    if not player_row:
        return None

    teams = match_payload.get("teams") if isinstance(match_payload, dict) else []
    team_outcomes: dict[str, bool] = {}
    if isinstance(teams, list):
        for team in teams:
            if not isinstance(team, dict):
                continue
            team_id = str(team.get("teamId") or team.get("team_id") or "").strip()
            if not team_id:
                continue
            won = team.get("won")
            if isinstance(won, bool):
                team_outcomes[team_id] = won

    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    player_team_id = str(player_row.get("team_id") or "").strip()
    match_info = match_payload.get("match_info") if isinstance(match_payload, dict) else {}
    if not isinstance(match_info, dict):
        match_info = {}

    return {
        "match_id": str(match_payload.get("match_id") or "").strip(),
        "kills": _to_int(player_row.get("kills")),
        "deaths": _to_int(player_row.get("deaths")),
        "assists": _to_int(player_row.get("assists")),
        "character_id": str(player_row.get("character_id") or "").strip(),
        "won": team_outcomes.get(player_team_id),
        "duration_seconds": _to_int(match_info.get("game_length_millis")) // 1000,
        "game_start_millis": _to_int(match_info.get("game_start_millis")),
    }


def _resolve_role(agent_identifier: str, fallback_role: str = "") -> str:
    normalized = str(agent_identifier or "").strip().lower()
    for keyword, role in AGENT_ROLE_BY_KEYWORD.items():
        if keyword in normalized:
            return role
    return str(fallback_role or "").strip() or "Unknown"


def _aggregate_recent_metrics(
    passport: GameProfile,
    snapshots: list[dict[str, Any]],
    source_region: str,
) -> dict[str, Any]:
    match_count = len(snapshots)
    total_kills = sum(int(item.get("kills") or 0) for item in snapshots)
    total_deaths = sum(int(item.get("deaths") or 0) for item in snapshots)
    total_assists = sum(int(item.get("assists") or 0) for item in snapshots)
    wins = sum(1 for item in snapshots if item.get("won") is True)

    kd_ratio = round(total_kills / max(1, total_deaths), 3)
    win_rate_pct = round((wins * 100.0) / max(1, match_count), 2)

    agents = [item.get("character_id") for item in snapshots if item.get("character_id")]
    most_played_agent = ""
    if agents:
        most_played_agent = Counter(agents).most_common(1)[0][0]

    most_played_role = _resolve_role(most_played_agent, fallback_role=passport.main_role)

    analyzed_match_ids = [item.get("match_id") for item in snapshots if item.get("match_id")]

    return {
        "provider": "riot",
        "game": "valorant",
        "region": source_region,
        "sample_size": match_count,
        "wins": wins,
        "losses": max(0, match_count - wins),
        "kills": total_kills,
        "deaths": total_deaths,
        "assists": total_assists,
        "recent_kd_ratio": kd_ratio,
        "recent_win_rate_pct": win_rate_pct,
        "most_played_agent": most_played_agent,
        "most_played_role": most_played_role,
        "recent_match_ids": analyzed_match_ids,
        "synced_at": timezone.now().isoformat(),
    }


def _resolve_internal_match_for_snapshot(
    passport: GameProfile,
    snapshot: Dict[str, Any],
) -> Optional[Dict[str, int]]:
    """
    Correlate Riot snapshot to an internal match for canonical ingestion.

    Correlation priority:
    1. Explicit Riot match id in match.lobby_info.
    2. Solo fallback by participant user id and approximate time window.
    """
    from apps.tournaments.models import Match

    riot_match_id = str(snapshot.get("match_id") or "").strip()
    if not riot_match_id:
        return None

    base_qs = Match.objects.filter(tournament__game__slug__iexact="valorant")

    explicit_match = base_qs.filter(
        Q(lobby_info__riot_match_id=riot_match_id)
        | Q(lobby_info__external_match_id=riot_match_id)
        | Q(lobby_info__match_id=riot_match_id)
    ).order_by("-updated_at").first()

    match = explicit_match
    if match is None:
        candidate_states = [
            Match.LIVE,
            Match.PENDING_RESULT,
            Match.DISPUTED,
            Match.COMPLETED,
        ]
        fallback_qs = base_qs.filter(
            state__in=candidate_states,
        ).filter(
            Q(participant1_id=passport.user_id) | Q(participant2_id=passport.user_id)
        )

        game_start_millis = snapshot.get("game_start_millis")
        try:
            if game_start_millis is not None:
                game_start = datetime.fromtimestamp(
                    int(game_start_millis) / 1000.0,
                    tz=timezone.get_current_timezone(),
                )
                window_start = game_start - timedelta(hours=6)
                window_end = game_start + timedelta(hours=6)
                fallback_qs = fallback_qs.filter(
                    Q(scheduled_time__range=(window_start, window_end))
                    | Q(started_at__range=(window_start, window_end))
                )
        except (TypeError, ValueError, OSError):
            pass

        match = fallback_qs.order_by("-updated_at").first()

    if match is None:
        return None

    if not match.participant1_id or not match.participant2_id:
        return None

    player_is_p1 = match.participant1_id == passport.user_id
    player_is_p2 = match.participant2_id == passport.user_id
    if not (player_is_p1 or player_is_p2):
        return None

    opponent_id = match.participant2_id if player_is_p1 else match.participant1_id

    won = snapshot.get("won")
    if won is True:
        winner_team_id = passport.user_id
        loser_team_id = opponent_id
    elif won is False:
        winner_team_id = opponent_id
        loser_team_id = passport.user_id
    elif match.winner_id and match.loser_id:
        winner_team_id = match.winner_id
        loser_team_id = match.loser_id
    else:
        return None

    if not winner_team_id or not loser_team_id or winner_team_id == loser_team_id:
        return None

    return {
        "match_id": int(match.id),
        "winner_team_id": int(winner_team_id),
        "loser_team_id": int(loser_team_id),
    }


def _build_riot_submission_payload(
    snapshot: Dict[str, Any],
    correlation: Dict[str, int],
    source_region: str,
) -> Dict[str, Any]:
    """Build a schema-compatible payload for canonical result verification."""
    return {
        "winner_team_id": int(correlation["winner_team_id"]),
        "loser_team_id": int(correlation["loser_team_id"]),
        "score": "1-0",
        "duration_seconds": max(0, int(snapshot.get("duration_seconds") or 0)),
        "riot_match_id": str(snapshot.get("match_id") or ""),
        "riot_region": source_region,
        "player_stats": {
            "kills": int(snapshot.get("kills") or 0),
            "deaths": int(snapshot.get("deaths") or 0),
            "assists": int(snapshot.get("assists") or 0),
            "character_id": str(snapshot.get("character_id") or ""),
            "won": snapshot.get("won"),
        },
    }


def _ingest_riot_snapshot(
    passport: GameProfile,
    snapshot: Dict[str, Any],
    source_region: str,
    system_actor_id: int,
) -> Dict[str, Any]:
    """Create and finalize a canonical MatchResultSubmission from one Riot snapshot."""
    from apps.tournament_ops.adapters import ResultSubmissionAdapter
    from apps.tournament_ops.services.tournament_ops_service import get_tournament_ops_service
    from apps.tournaments.models import MatchResultSubmission

    correlation = _resolve_internal_match_for_snapshot(passport, snapshot)
    if not correlation:
        return {
            "status": "unmatched",
            "riot_match_id": snapshot.get("match_id"),
        }

    match_id = int(correlation["match_id"])
    riot_match_id = str(snapshot.get("match_id") or "").strip()
    fingerprint = f"riot:{source_region}:{riot_match_id}:{match_id}"

    existing = MatchResultSubmission.objects.filter(ingestion_fingerprint=fingerprint).first()
    if existing:
        return {
            "status": "duplicate",
            "submission_id": existing.id,
            "match_id": existing.match_id,
            "finalized": existing.status == MatchResultSubmission.STATUS_FINALIZED,
        }

    adapter = ResultSubmissionAdapter()
    submission_payload = _build_riot_submission_payload(snapshot, correlation, source_region)
    submitted_by_user_id = system_actor_id if system_actor_id > 0 else passport.user_id

    submission = adapter.create_submission(
        match_id=match_id,
        submitted_by_user_id=submitted_by_user_id,
        submitted_by_team_id=None,
        raw_result_payload=submission_payload,
        proof_screenshot_url="",
        submitter_notes="Auto-ingested from Riot API",
        source=RIOT_SUBMISSION_SOURCE,
        ingestion_fingerprint=fingerprint,
    )

    submission = adapter.update_submission_status(
        submission_id=submission.id,
        status='auto_confirmed',
        organizer_notes='Auto-confirmed via Riot ingestion policy',
    )

    try:
        finalized = get_tournament_ops_service().finalize_submission_with_verification(
            submission_id=submission.id,
            resolved_by_user_id=submitted_by_user_id,
        )
    except Exception:
        adapter.update_submission_status(
            submission_id=submission.id,
            status='rejected',
            organizer_notes='Riot ingestion verification failed; requires organizer review',
        )
        raise

    return {
        "status": "finalized",
        "submission_id": finalized.id,
        "match_id": finalized.match_id,
    }


def _persist_sync_result(passport: GameProfile, aggregates: dict[str, Any]) -> None:
    metadata = passport.metadata.copy() if isinstance(passport.metadata, dict) else {}
    live_stats = metadata.get("live_stats") if isinstance(metadata.get("live_stats"), dict) else {}
    live_stats["valorant"] = aggregates
    metadata["live_stats"] = live_stats

    # Keep metadata compatibility for existing selectors and filters.
    metadata["api_synced"] = True
    metadata["oauth_provider"] = GameOAuthConnection.Provider.RIOT
    metadata["riot_last_match_sync_at"] = aggregates.get("synced_at")

    passport.metadata = metadata
    passport.kd_ratio = float(aggregates.get("recent_kd_ratio") or 0.0)
    passport.win_rate = int(round(float(aggregates.get("recent_win_rate_pct") or 0.0)))
    passport.matches_played = int(aggregates.get("sample_size") or 0)

    update_fields = [
        "metadata",
        "kd_ratio",
        "win_rate",
        "matches_played",
        "updated_at",
    ]

    derived_role = str(aggregates.get("most_played_role") or "").strip()
    if derived_role and derived_role != "Unknown":
        passport.main_role = derived_role
        update_fields.append("main_role")

    with transaction.atomic():
        passport.save(update_fields=update_fields)

        oauth_connection = getattr(passport, "oauth_connection", None)
        if oauth_connection and oauth_connection.provider == GameOAuthConnection.Provider.RIOT:
            oauth_connection.last_synced_at = timezone.now()
            oauth_connection.save(update_fields=["last_synced_at", "updated_at"])


def _sync_single_passport(passport: GameProfile) -> dict[str, Any]:
    puuid, region = _resolve_puuid_and_region(passport)
    if not puuid:
        return {
            "status": "skipped",
            "passport_id": passport.id,
            "reason": "missing_puuid",
        }

    if not bool(getattr(settings, "RIOT_RESULT_INGESTION_ENABLED", True)):
        return {
            "status": "skipped",
            "passport_id": passport.id,
            "reason": "riot_ingestion_disabled",
        }

    max_matches = _setting_int("RIOT_SYNC_MAX_MATCHES", 10, minimum=1)
    per_match_delay = _setting_float("RIOT_SYNC_MATCH_DELAY_SECONDS", 0.25, minimum=0.0)

    history = _call_riot_with_retry(fetch_recent_valorant_matches, puuid=puuid, region=region)
    match_ids = history.get("match_ids") if isinstance(history, dict) else []
    if not isinstance(match_ids, list):
        match_ids = []

    selected_match_ids = [str(mid).strip() for mid in match_ids if str(mid).strip()][:max_matches]
    if not selected_match_ids:
        return {
            "status": "skipped",
            "passport_id": passport.id,
            "reason": "no_recent_matches",
        }

    snapshots: list[dict[str, Any]] = []
    finalized_snapshots: list[dict[str, Any]] = []
    ingestion_summary = {
        "finalized": 0,
        "duplicate": 0,
        "unmatched": 0,
        "failed": 0,
        "submission_ids": [],
    }
    system_actor_id = _setting_int("RIOT_SYNC_SYSTEM_USER_ID", passport.user_id, minimum=1)

    for index, match_id in enumerate(selected_match_ids):
        details = _call_riot_with_retry(fetch_match_details, match_id=match_id, region=region)
        snapshot = _extract_player_match_snapshot(details, puuid=puuid)
        if snapshot:
            snapshots.append(snapshot)

            try:
                ingestion_result = _ingest_riot_snapshot(
                    passport=passport,
                    snapshot=snapshot,
                    source_region=region,
                    system_actor_id=system_actor_id,
                )
                status = ingestion_result.get("status")

                if status == "finalized":
                    ingestion_summary["finalized"] += 1
                    ingestion_summary["submission_ids"].append(ingestion_result.get("submission_id"))
                    finalized_snapshots.append(snapshot)
                elif status == "duplicate":
                    ingestion_summary["duplicate"] += 1
                    if ingestion_result.get("finalized"):
                        finalized_snapshots.append(snapshot)
                elif status == "unmatched":
                    ingestion_summary["unmatched"] += 1
                else:
                    ingestion_summary["failed"] += 1
            except Exception as exc:  # pragma: no cover - defensive path
                ingestion_summary["failed"] += 1
                logger.warning(
                    "Riot canonical ingestion failed for passport=%s match_id=%s: %s",
                    passport.id,
                    snapshot.get("match_id"),
                    exc,
                )

        if index < len(selected_match_ids) - 1:
            _sleep(per_match_delay)

    if not snapshots:
        return {
            "status": "skipped",
            "passport_id": passport.id,
            "reason": "player_not_present_in_matches",
        }

    if not finalized_snapshots:
        return {
            "status": "skipped",
            "passport_id": passport.id,
            "reason": "no_finalized_submissions",
            "canonical_ingestion": ingestion_summary,
        }

    aggregates = _aggregate_recent_metrics(passport, finalized_snapshots, source_region=region)
    _persist_sync_result(passport, aggregates)

    return {
        "status": "synced",
        "passport_id": passport.id,
        "sample_size": aggregates["sample_size"],
        "recent_kd_ratio": aggregates["recent_kd_ratio"],
        "recent_win_rate_pct": aggregates["recent_win_rate_pct"],
        "most_played_agent": aggregates["most_played_agent"],
        "most_played_role": aggregates["most_played_role"],
        "canonical_ingestion": ingestion_summary,
    }


@shared_task(bind=True, name="user_profile.sync_single_riot_passport")
def sync_single_riot_passport(self, passport_id: int) -> dict[str, Any]:
    """Sync one Riot-linked Valorant passport by id."""
    try:
        passport = (
            GameProfile.objects.select_related("game", "oauth_connection")
            .get(id=passport_id, game__slug__iexact="valorant")
        )
    except GameProfile.DoesNotExist:
        return {
            "status": "missing",
            "passport_id": passport_id,
        }

    try:
        return _sync_single_passport(passport)
    except RiotMatchServiceError as exc:
        logger.warning(
            "Riot sync failed for passport %s: %s (%s)",
            passport_id,
            exc.message,
            exc.error_code,
        )
        return {
            "status": "failed",
            "passport_id": passport_id,
            "error_code": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code,
        }
    except Exception as exc:  # pragma: no cover - defensive path
        logger.exception("Unexpected Riot sync failure for passport %s", passport_id)
        return {
            "status": "failed",
            "passport_id": passport_id,
            "error_code": "UNEXPECTED_ERROR",
            "message": str(exc),
        }


@shared_task(bind=True, name="user_profile.sync_all_active_riot_passports")
def sync_all_active_riot_passports(self) -> dict[str, Any]:
    """Periodic sync for active Riot-linked Valorant passports."""
    started_at = timezone.now()
    per_passport_delay = _setting_float("RIOT_SYNC_PASSPORT_DELAY_SECONDS", 0.4, minimum=0.0)

    queryset = _candidate_passports()
    total_candidates = queryset.count()

    summary: dict[str, Any] = {
        "started_at": started_at.isoformat(),
        "total_candidates": total_candidates,
        "synced": 0,
        "skipped": 0,
        "failed": 0,
        "synced_passport_ids": [],
        "errors": [],
    }

    if total_candidates == 0:
        summary["finished_at"] = timezone.now().isoformat()
        return summary

    for passport in queryset.iterator(chunk_size=25):
        try:
            result = _sync_single_passport(passport)
        except RiotMatchServiceError as exc:
            summary["failed"] += 1
            if len(summary["errors"]) < 25:
                summary["errors"].append(
                    {
                        "passport_id": passport.id,
                        "error_code": exc.error_code,
                        "message": exc.message,
                        "status_code": exc.status_code,
                    }
                )
            logger.warning(
                "Riot sync failed for passport %s: %s (%s)",
                passport.id,
                exc.message,
                exc.error_code,
            )
        except Exception as exc:  # pragma: no cover - defensive path
            summary["failed"] += 1
            if len(summary["errors"]) < 25:
                summary["errors"].append(
                    {
                        "passport_id": passport.id,
                        "error_code": "UNEXPECTED_ERROR",
                        "message": str(exc),
                    }
                )
            logger.exception("Unexpected Riot sync failure for passport %s", passport.id)
        else:
            status = result.get("status")
            if status == "synced":
                summary["synced"] += 1
                summary["synced_passport_ids"].append(passport.id)
            elif status == "skipped":
                summary["skipped"] += 1
            elif status == "missing":
                summary["skipped"] += 1
            else:
                summary["failed"] += 1
                if len(summary["errors"]) < 25:
                    summary["errors"].append(
                        {
                            "passport_id": passport.id,
                            "error_code": result.get("error_code", "SYNC_FAILED"),
                            "message": result.get("message", "Sync failed"),
                        }
                    )

        _sleep(per_passport_delay)

    finished_at = timezone.now()
    summary["finished_at"] = finished_at.isoformat()
    summary["duration_seconds"] = round((finished_at - started_at).total_seconds(), 2)

    logger.info(
        "Riot passport sync finished: candidates=%s synced=%s skipped=%s failed=%s duration=%.2fs",
        summary["total_candidates"],
        summary["synced"],
        summary["skipped"],
        summary["failed"],
        summary["duration_seconds"],
    )

    return summary


@shared_task(bind=True, name="user_profile.sync_all_active_steam_passports")
def sync_all_active_steam_passports(self) -> dict[str, Any]:
    """Periodic sync: refresh Steam persona name and avatar for linked passports."""
    from apps.user_profile.services.oauth_steam_service import fetch_player_summary, SteamOpenIDError

    started_at = timezone.now()
    per_conn_delay = float(getattr(settings, "STEAM_SYNC_DELAY_SECONDS", 0.5))

    queryset = (
        GameOAuthConnection.objects
        .filter(provider=GameOAuthConnection.Provider.STEAM)
        .select_related("passport", "passport__game")
        .exclude(provider_account_id="")
    )
    total = queryset.count()

    summary: dict[str, Any] = {
        "started_at": started_at.isoformat(),
        "total_candidates": total,
        "synced": 0,
        "failed": 0,
        "errors": [],
    }

    if total == 0:
        summary["finished_at"] = timezone.now().isoformat()
        return summary

    for conn in queryset.iterator(chunk_size=25):
        steam_id = conn.provider_account_id
        try:
            player = fetch_player_summary(steam_id)
        except SteamOpenIDError as exc:
            summary["failed"] += 1
            if len(summary["errors"]) < 25:
                summary["errors"].append({
                    "connection_id": conn.id,
                    "steam_id": steam_id,
                    "error_code": exc.error_code,
                    "message": exc.message,
                })
            logger.warning(
                "Steam sync failed for connection %s (steam_id=%s): %s",
                conn.id, steam_id, exc.message,
            )
            _sleep(per_conn_delay)
            continue
        except Exception:
            summary["failed"] += 1
            if len(summary["errors"]) < 25:
                summary["errors"].append({
                    "connection_id": conn.id,
                    "steam_id": steam_id,
                    "error_code": "UNEXPECTED_ERROR",
                })
            logger.exception("Unexpected Steam sync error for connection %s", conn.id)
            _sleep(per_conn_delay)
            continue

        passport = conn.passport
        metadata = passport.metadata.copy() if isinstance(passport.metadata, dict) else {}
        metadata.update({
            "steam_persona_name": player.personaname,
            "steam_avatar": player.avatar,
            "steam_avatar_medium": player.avatar_medium,
            "steam_avatar_full": player.avatar_full,
            "steam_profile_url": player.profile_url,
        })

        # Fetch CS2 aggregate stats for CS2 passports (best-effort; non-fatal)
        game_slug = getattr(getattr(conn, "passport", None), "game", None)
        game_slug = getattr(game_slug, "slug", "").lower() if game_slug else ""
        cs2_stats = None
        if game_slug == "cs2":
            try:
                from apps.user_profile.services.steam_cs2_stats_service import fetch_cs2_stats, CS2StatsError
                cs2_stats = fetch_cs2_stats(steam_id)
                metadata["cs2_stats"] = cs2_stats
            except Exception:
                pass  # Stats are best-effort; persona sync still succeeds

        passport.ign = player.personaname
        passport.in_game_name = player.personaname
        passport.metadata = metadata
        if cs2_stats is not None:
            passport.kd_ratio = cs2_stats.get("kd_ratio")
            passport.win_rate = int(round(cs2_stats.get("win_rate", 0)))
            secs = cs2_stats.get("total_time_played_seconds") or 0
            passport.hours_played = (secs // 3600) or None
        update_fields = ["ign", "in_game_name", "metadata", "updated_at"]
        if cs2_stats is not None:
            update_fields += ["kd_ratio", "win_rate", "hours_played"]
        passport.save(update_fields=update_fields)

        conn.last_synced_at = timezone.now()
        conn.save(update_fields=["last_synced_at"])

        summary["synced"] += 1
        _sleep(per_conn_delay)

    finished_at = timezone.now()
    summary["finished_at"] = finished_at.isoformat()
    summary["duration_seconds"] = round((finished_at - started_at).total_seconds(), 2)
    logger.info(
        "Steam passport sync finished: candidates=%s synced=%s failed=%s duration=%.2fs",
        summary["total_candidates"], summary["synced"], summary["failed"], summary["duration_seconds"],
    )
    return summary


@shared_task(bind=True, name="user_profile.sync_all_active_epic_passports")
def sync_all_active_epic_passports(self) -> dict[str, Any]:
    """Periodic sync: proactively refresh Epic OAuth tokens before they expire."""
    from apps.user_profile.services.oauth_epic_service import refresh_epic_access_token, EpicOAuthError

    started_at = timezone.now()
    refresh_window_minutes = int(getattr(settings, "EPIC_TOKEN_REFRESH_WINDOW_MINUTES", 30))
    per_conn_delay = float(getattr(settings, "EPIC_SYNC_DELAY_SECONDS", 0.3))
    refresh_before = timezone.now() + timedelta(minutes=refresh_window_minutes)

    # Process connections expiring within the refresh window OR with unknown expiry
    queryset = (
        GameOAuthConnection.objects
        .filter(provider=GameOAuthConnection.Provider.EPIC)
        .filter(
            Q(expires_at__isnull=False, expires_at__lte=refresh_before)
            | Q(expires_at__isnull=True)
        )
        .select_related("passport")
        .exclude(refresh_token="")
    )
    total = queryset.count()

    summary: dict[str, Any] = {
        "started_at": started_at.isoformat(),
        "total_candidates": total,
        "refreshed": 0,
        "failed": 0,
        "requires_reauth": [],
        "errors": [],
    }

    if total == 0:
        summary["finished_at"] = timezone.now().isoformat()
        return summary

    for conn in queryset.iterator(chunk_size=25):
        try:
            conn = refresh_epic_access_token(conn)
            summary["refreshed"] += 1

            # Best-effort: refresh Epic display name via userinfo endpoint
            try:
                from apps.user_profile.services.epic_rl_stats_service import fetch_epic_profile
                profile = fetch_epic_profile(conn)
                display_name = profile.get("display_name", "")
                if display_name:
                    passport = conn.passport
                    metadata = passport.metadata.copy() if isinstance(passport.metadata, dict) else {}
                    metadata["epic_display_name"] = display_name
                    passport.ign = display_name
                    passport.in_game_name = display_name
                    passport.metadata = metadata
                    passport.save(update_fields=["ign", "in_game_name", "metadata", "updated_at"])
            except Exception:
                pass  # Display name refresh is best-effort; token refresh still counted
        except EpicOAuthError as exc:
            if exc.status_code == 401:
                # Refresh token invalid/expired — user must re-authenticate
                summary["requires_reauth"].append(conn.passport_id)
                logger.info(
                    "Epic refresh token expired for connection %s (passport_id=%s)",
                    conn.id, conn.passport_id,
                )
            else:
                summary["failed"] += 1
                if len(summary["errors"]) < 25:
                    summary["errors"].append({
                        "connection_id": conn.id,
                        "passport_id": conn.passport_id,
                        "error_code": exc.error_code,
                        "message": exc.message,
                    })
                logger.warning(
                    "Epic token refresh failed for connection %s: %s (%s)",
                    conn.id, exc.message, exc.error_code,
                )
        except Exception:
            summary["failed"] += 1
            if len(summary["errors"]) < 25:
                summary["errors"].append({
                    "connection_id": conn.id,
                    "passport_id": conn.passport_id,
                    "error_code": "UNEXPECTED_ERROR",
                })
            logger.exception("Unexpected Epic sync error for connection %s", conn.id)

        _sleep(per_conn_delay)

    finished_at = timezone.now()
    summary["finished_at"] = finished_at.isoformat()
    summary["duration_seconds"] = round((finished_at - started_at).total_seconds(), 2)
    logger.info(
        "Epic passport sync finished: candidates=%s refreshed=%s reauth_needed=%s failed=%s duration=%.2fs",
        summary["total_candidates"], summary["refreshed"], len(summary["requires_reauth"]),
        summary["failed"], summary["duration_seconds"],
    )
    return summary