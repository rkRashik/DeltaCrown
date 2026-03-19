"""
Match Polling Celery Tasks — Phase 1 (AUTOMATED_TOURNAMENTS_ROADMAP.md)

Task map:
  poll_pending_riot_matches    — Beat, every 2 min — finds Valorant matches needing fetch
  poll_pending_steam_matches   — Beat, every 5 min — finds CS2/Dota2 matches needing fetch
  fetch_riot_match_v5          — Per match — fetches & ingests one Riot match
  fetch_steam_match_result     — Per match — fetches & ingests one Steam match
  advance_bracket_after_match  — After ingest — triggers bracket progression

Redis rate-limit guard:
  _check_riot_rate_limit(region) — enforces 100 req / 2 min per routing region
  _check_steam_rate_limit()      — enforces ~1 req/s (3600/hr) for Steam Web API

Add to CELERYBEAT_SCHEDULE in settings:
    "poll-riot-matches": {
        "task": "apps.tournament_ops.tasks.match_polling.poll_pending_riot_matches",
        "schedule": crontab(minute="*/2"),
    },
    "poll-steam-matches": {
        "task": "apps.tournament_ops.tasks.match_polling.poll_pending_steam_matches",
        "schedule": crontab(minute="*/5"),
    },
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.db.models import Exists, OuterRef

logger = logging.getLogger(__name__)

# Maximum match fetches dispatched per poller cycle.
RIOT_POLL_MAX = getattr(settings, "RIOT_MATCH_POLL_MAX_PER_CYCLE", 20)
STEAM_POLL_MAX = getattr(settings, "STEAM_MATCH_POLL_MAX_PER_CYCLE", 10)

# Redis key prefixes
_RIOT_RL_PREFIX = "deltacrown:riot_ratelimit:"
_STEAM_RL_KEY = "deltacrown:steam_ratelimit"
_RIOT_RL_CAP = 95       # leave 5-request buffer below Riot's 100 req / 2 min
_STEAM_RL_CAP = 3500    # leave buffer below ~3600 req/hr Steam limit


# ---------------------------------------------------------------------------
# Rate-limit helpers
# ---------------------------------------------------------------------------

def _check_riot_rate_limit(region: str) -> bool:
    """
    Returns True if a Riot API call to ``region`` is within rate limits.

    Uses an atomic Redis INCR + EXPIRE (set only on first call in the window).
    Window: 120 seconds.  Cap: 95 requests per window per region.
    """
    try:
        from django_redis import get_redis_connection
        redis = get_redis_connection("default")
        key = f"{_RIOT_RL_PREFIX}{region.lower()}"
        count = redis.incr(key)
        if count == 1:
            redis.expire(key, 120)
        if count > _RIOT_RL_CAP:
            logger.warning(
                "[Polling] Riot rate limit reached for region '%s' (count=%s). Backing off.",
                region,
                count,
            )
            return False
        return True
    except Exception:
        # If Redis is unavailable, allow the call through rather than blocking
        # all automated ingestion.  A network error on the Riot side will handle
        # the 429 gracefully via task retry.
        logger.exception("[Polling] Redis rate-limit check failed — allowing through.")
        return True


def _check_steam_rate_limit() -> bool:
    """
    Returns True if a Steam Web API call is within rate limits.

    Window: 3600 seconds (1 hour).  Cap: 3500 requests per window.
    """
    try:
        from django_redis import get_redis_connection
        redis = get_redis_connection("default")
        count = redis.incr(_STEAM_RL_KEY)
        if count == 1:
            redis.expire(_STEAM_RL_KEY, 3600)
        if count > _STEAM_RL_CAP:
            logger.warning(
                "[Polling] Steam rate limit reached (count=%s). Backing off.", count
            )
            return False
        return True
    except Exception:
        logger.exception("[Polling] Redis rate-limit check (Steam) failed — allowing through.")
        return True


# ---------------------------------------------------------------------------
# Poller tasks
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def poll_pending_riot_matches(self):
    """
    Find all LIVE or PENDING_RESULT Valorant matches that have a riot_match_id
    in lobby_info but no AUTO_CONFIRMED / FINALIZED submission yet, then dispatch
    a fetch_riot_match_v5 task for each one.
    """
    from apps.tournaments.models.match import Match
    from apps.tournaments.models.result_submission import MatchResultSubmission

    qs = (
        Match.objects.filter(
            state__in=[Match.LIVE, Match.PENDING_RESULT],
            tournament__game__slug="valorant",
        )
        .exclude(lobby_info={})
        .annotate(
            has_auto_result=Exists(
                MatchResultSubmission.objects.filter(
                    match=OuterRef("pk"),
                    source=MatchResultSubmission.SOURCE_RIOT_API,
                    status__in=[
                        MatchResultSubmission.STATUS_AUTO_CONFIRMED,
                        MatchResultSubmission.STATUS_FINALIZED,
                    ],
                )
            )
        )
        .filter(has_auto_result=False)[:RIOT_POLL_MAX]
    )

    dispatched = 0
    skipped = 0
    for match in qs:
        riot_match_id = (match.lobby_info or {}).get("riot_match_id", "")
        if not riot_match_id:
            skipped += 1
            continue
        fetch_riot_match_v5.delay(match.pk, riot_match_id)
        dispatched += 1

    logger.info(
        "[Polling] poll_pending_riot_matches — dispatched=%d skipped=%d",
        dispatched,
        skipped,
    )
    return {"status": "ok", "dispatched": dispatched, "skipped": skipped}


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def poll_pending_steam_matches(self):
    """
    Find all LIVE or PENDING_RESULT CS2 / Dota 2 matches with a Steam match
    identifier in lobby_info but no automated submission yet, then dispatch
    fetch_steam_match_result for each one.

    Implementation note (Phase 3):
        - Filter by tournament.game.slug in ["cs2", "dota2"]
        - Dispatch fetch_steam_match_result.delay(match.pk, game_slug, identifier)
    """
    logger.info("[Polling] poll_pending_steam_matches — stub (implement in Phase 3)")
    # TODO (Phase 3): implement body
    return {"status": "stub", "dispatched": 0}


# ---------------------------------------------------------------------------
# Per-match fetch tasks
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def fetch_riot_match_v5(self, match_pk: int, riot_match_id: str):
    """
    Fetch one Valorant match from the Riot Match-V5 API and ingest the result.
    """
    from apps.tournaments.models.match import Match
    from apps.tournaments.models.result_submission import MatchResultSubmission
    from apps.tournament_ops.services.riot_result_fetcher import (
        RiotMatchFetchError,
        RiotMatchParseError,
        RiotMatchV5Fetcher,
    )
    from apps.tournament_ops.services.match_ingestion_service import (
        MatchIngestionService,
    )
    from apps.tournament_ops.services.integrity_check import (
        flag_integrity_failure,
        validate_participant_puuids,
    )
    from apps.user_profile.models import ProviderAccount

    try:
        match = Match.objects.select_related("tournament__game").get(pk=match_pk)
    except Match.DoesNotExist:
        logger.error("[Polling] fetch_riot_match_v5 — Match pk=%s not found.", match_pk)
        return {"status": "error", "reason": "match_not_found"}

    if match.state not in (Match.LIVE, Match.PENDING_RESULT):
        logger.info(
            "[Polling] fetch_riot_match_v5 — Match pk=%s state=%s, skipping.",
            match_pk,
            match.state,
        )
        return {"status": "skipped", "reason": "state_not_eligible"}

    lobby = match.lobby_info or {}
    region = lobby.get("region", "").lower().strip()
    if not region:
        logger.warning(
            "[Polling] fetch_riot_match_v5 — Match pk=%s has no region in lobby_info.",
            match_pk,
        )
        return {"status": "error", "reason": "no_region"}

    if not _check_riot_rate_limit(region):
        raise self.retry(countdown=120, exc=Exception("Riot rate limit reached"))

    fetcher = RiotMatchV5Fetcher()
    try:
        payload = fetcher.fetch(cluster=region, match_id=riot_match_id)
    except RiotMatchFetchError as exc:
        if exc.status_code == 429:
            raise self.retry(countdown=180, exc=exc)
        if exc.status_code == 404:
            logger.warning(
                "[Polling] Riot match %s not found (404) — will retry later.",
                riot_match_id,
            )
            raise self.retry(countdown=300, exc=exc)
        logger.exception(
            "[Polling] RiotMatchFetchError for match_pk=%s riot_id=%s",
            match_pk,
            riot_match_id,
        )
        raise self.retry(exc=exc)

    # Resolve PUUIDs for each participant via ProviderAccount
    def _resolve_puuids(participant_id):
        if not participant_id:
            return set()
        from apps.tournaments.models.registration import Registration
        try:
            reg = Registration.objects.get(
                pk=participant_id,
                tournament_id=match.tournament_id,
            )
        except Registration.DoesNotExist:
            return set()
        if reg.team_id:
            from apps.tournament_ops.services.integrity_check import (
                _get_team_member_user_ids,
            )
            user_ids = _get_team_member_user_ids(reg.team_id)
        else:
            user_ids = [reg.user_id] if reg.user_id else []
        return set(
            ProviderAccount.objects.filter(
                provider=ProviderAccount.Provider.RIOT,
                user_id__in=user_ids,
            ).values_list("provider_account_id", flat=True)
        )

    p1_puuids = _resolve_puuids(match.participant1_id)
    p2_puuids = _resolve_puuids(match.participant2_id)

    if not p1_puuids and not p2_puuids:
        logger.warning(
            "[Polling] No Riot PUUIDs found for match pk=%s — cannot parse.",
            match_pk,
        )
        return {"status": "error", "reason": "no_puuids"}

    try:
        parsed = fetcher.parse_valorant_result(payload, p1_puuids, p2_puuids)
    except RiotMatchParseError as exc:
        logger.exception(
            "[Polling] Parse failed for match_pk=%s riot_id=%s: %s",
            match_pk,
            riot_match_id,
            exc,
        )
        return {"status": "error", "reason": "parse_failed"}

    # Integrity check
    all_puuids = {
        p["puuid"]
        for p in (payload.get("players") or [])
        if p.get("puuid")
    }
    integrity_result = validate_participant_puuids(
        match,
        all_puuids,
        provider=ProviderAccount.Provider.RIOT,
    )

    fingerprint = f"riot:{riot_match_id}"
    submission = MatchIngestionService().ingest(
        match=match,
        parsed_result=parsed,
        raw_payload=payload,
        source=MatchResultSubmission.SOURCE_RIOT_API,
        ingestion_fingerprint=fingerprint,
    )

    if not integrity_result.passed:
        flag_integrity_failure(match, submission, integrity_result)
        logger.warning(
            "[Polling] Integrity check FAILED for match pk=%s — flagged.",
            match_pk,
        )

    logger.info(
        "[Polling] Ingested riot match pk=%s riot_id=%s winner_slot=%s integrity=%s",
        match_pk,
        riot_match_id,
        parsed.winner_slot,
        "PASS" if integrity_result.passed else "FAIL",
    )

    # Trigger bracket advancement
    advance_bracket_after_match.delay(match_pk)

    return {
        "status": "ok",
        "match_pk": match_pk,
        "riot_match_id": riot_match_id,
        "winner_slot": parsed.winner_slot,
        "integrity_passed": integrity_result.passed,
    }


@shared_task(bind=True, max_retries=5, default_retry_delay=120)
def fetch_steam_match_result(self, match_pk: int, game_slug: str, identifier: str):
    """
    Fetch one Steam match result (CS2 share code or Dota2 match ID) and ingest.

    Behaviour (Phase 3 full implementation):
    1. Load Match; verify still needs result.
    2. Call _check_steam_rate_limit(); if False, self.retry().
    3. Dispatch to game-specific fetcher:
         - cs2  → decode sharecode → GET GetSchemaForGame / CSGO protobuf
         - dota2 → GET IDOTA2Match_570/GetMatchDetails/v1?match_id={identifier}
    4. parse_steam_result(payload, p1_steam_ids, p2_steam_ids).
    5. validate_participant_puuids(match, payload_ids, provider=STEAM).
    6. MatchIngestionService().ingest(match, parsed_result, raw_payload,
           source=SOURCE_STEAM_API, fingerprint=f"{game_slug}:{identifier}").
    7. If integrity failed → flag_integrity_failure(match, submission, result).
    """
    logger.info(
        "[Polling] fetch_steam_match_result match_pk=%s game=%s id=%s — stub (Phase 3)",
        match_pk,
        game_slug,
        identifier,
    )
    # TODO (Phase 3): implement body
    return {"status": "stub", "match_pk": match_pk, "game_slug": game_slug}


# ---------------------------------------------------------------------------
# Bracket advancement
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def advance_bracket_after_match(self, match_pk: int):
    """
    Trigger bracket progression after a match is marked COMPLETED.

    Delegates to the existing MatchService / BracketService logic so bracket
    advancement behaviour (seeding next round, generating new matches) is not
    duplicated here.
    """
    from apps.tournaments.models.match import Match

    try:
        match = Match.objects.get(pk=match_pk)
    except Match.DoesNotExist:
        logger.error("[Polling] advance_bracket — Match pk=%s not found.", match_pk)
        return {"status": "error", "reason": "match_not_found"}

    if match.state != Match.COMPLETED:
        logger.info(
            "[Polling] advance_bracket — Match pk=%s state=%s, not yet completed.",
            match_pk,
            match.state,
        )
        return {"status": "skipped", "reason": "not_completed"}

    try:
        from apps.tournament_ops.services.match_service import MatchService
        MatchService().advance_bracket(match_pk)
        logger.info("[Polling] Bracket advanced for match pk=%s.", match_pk)
        return {"status": "ok", "match_pk": match_pk}
    except ImportError:
        logger.warning(
            "[Polling] MatchService not available — bracket advancement deferred.",
        )
        return {"status": "deferred", "match_pk": match_pk}
    except Exception as exc:
        logger.exception(
            "[Polling] Bracket advancement failed for match pk=%s: %s",
            match_pk,
            exc,
        )
        raise self.retry(exc=exc)
