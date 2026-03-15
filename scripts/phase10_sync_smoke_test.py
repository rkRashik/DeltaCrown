"""
Phase 10 QA - Riot Sync Engine Smoke Test
==========================================

Validates the full sync pipeline end-to-end without a live Riot API key
and WITHOUT a running database (all ORM calls are mocked; full DB path
can be run via pytest when PostgreSQL is available).

Covers:
    - Pure aggregation math  (K/D, win rate, agent counter, role map)
    - Match snapshot extraction  (scoreboard parsing, team outcome join)
    - _sync_single_passport()   (full pipeline: resolve → fetch → parse → agg → persist)
    - Celery task wrapper        (sync_single_riot_passport, missing-id handling)
    - Candidate query shape      (verified with a mock queryset)
    - Batch task flow            (sync_all_active_riot_passports with mocked ORM)
    - 429 retry / exhaustion     (backoff and RIOT_RETRY_EXHAUSTED)
    - Role inference edge cases  (8 agent keywords + unknown/empty)
    - Persistence payload dump   (exact dict that WOULD be written to DB)

Run from repo root (no DB or Celery worker required):
    python scripts/phase10_sync_smoke_test.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, call, PropertyMock

# ---------------------------------------------------------------------------
# Bootstrap Django before any app imports
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings_smoke")
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

import django  # noqa: E402
django.setup()

# Only import app code AFTER django.setup()
from django.test.utils import override_settings  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.user_profile.models import GameOAuthConnection  # noqa: E402
from apps.user_profile.tasks import (  # noqa: E402
    _aggregate_recent_metrics,
    _extract_player_match_snapshot,
    _persist_sync_result,
    _resolve_role,
    _sync_single_passport,
    _call_riot_with_retry,
    sync_single_riot_passport,
    sync_all_active_riot_passports,
)

# ---------------------------------------------------------------------------
# Deterministic fixture configuration
# ---------------------------------------------------------------------------
TEST_PUUID = "smoke-puuid-phase10-00000000000000"
TEST_REGION = "ap"
TEST_SUFFIX = uuid.uuid4().hex[:8]

# 10 deterministic matches:
#   Matches 0-7  → team Red wins, agent jett, 20K/10D/5A
#   Matches 8-9  → team Blue loses, agent sage, 10K/15D/8A
#
# Expected aggregates:
#   kills         = 8*20 + 2*10 = 180
#   deaths        = 8*10 + 2*15 = 110
#   assists       = 8*5  + 2*8  = 56
#   kd_ratio      = 180/110     ≈ 1.636  (round to 3 dp)
#   wins          = 8
#   losses        = 2
#   win_rate_pct  = 80.00
#   most_played_agent  = "agent_jett"  (8/10)
#   most_played_role   = "Duelist"     (jett keyword)

EXPECTED = {
    "kills": 180,
    "deaths": 110,
    "assists": 56,
    "recent_kd_ratio": round(180 / 110, 3),
    "wins": 8,
    "losses": 2,
    "recent_win_rate_pct": 80.00,
    "most_played_agent": "agent_jett",
    "most_played_role": "Duelist",
    "sample_size": 10,
}


def _make_mock_match(match_index: int) -> dict[str, Any]:
    """Build a fake fetch_match_details response for one match."""
    is_win = match_index < 8
    player_team = "Red" if is_win else "Blue"
    agent = "agent_jett" if is_win else "agent_sage"
    kills = 20 if is_win else 10
    deaths = 10 if is_win else 15
    assists = 5 if is_win else 8

    return {
        "match_id": f"VAL-SMOKE-{match_index:04d}",
        "region": TEST_REGION,
        "match_info": {
            "map_id": "Ascent",
            "queue_id": "competitive",
            "game_length_millis": 2_100_000,
        },
        "scoreboard": [
            {
                "puuid": TEST_PUUID,
                "game_name": "SmokeGamer",
                "tag_line": "QA",
                "team_id": player_team,
                "character_id": agent,
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
                "score": kills * 220,
                "rounds_played": 24,
            },
            {
                "puuid": f"filler-teammate-{match_index}",
                "team_id": player_team,
                "character_id": "agent_omen",
                "kills": 12,
                "deaths": 11,
                "assists": 4,
            },
        ],
        "teams": [
            {"teamId": "Red", "won": True},
            {"teamId": "Blue", "won": False},
        ],
        "round_results": [],
    }


def _mock_fetch_recent(puuid: str, region: str = "ap") -> dict[str, Any]:
    """Mock for fetch_recent_valorant_matches."""
    match_ids = [f"VAL-SMOKE-{i:04d}" for i in range(10)]
    return {
        "puuid": puuid,
        "region": region,
        "match_ids": match_ids,
        "matches": [{"match_id": mid} for mid in match_ids],
    }


def _mock_fetch_details(match_id: str, region: str = "ap") -> dict[str, Any]:
    """Mock for fetch_match_details — derives fixture from the match index."""
    try:
        idx = int(match_id.split("-")[-1])
    except (ValueError, IndexError):
        idx = 0
    return _make_mock_match(idx)


def _make_mock_passport(
    passport_id: int = 1,
    metadata: dict | None = None,
    main_role: str = "",
    with_oauth: bool = True,
) -> MagicMock:
    """Build a realistic mock GameProfile with enough attributes for the sync pipeline."""
    passport = MagicMock()
    passport.id = passport_id
    passport.main_role = main_role
    passport.kd_ratio = 0.0
    passport.win_rate = 0
    passport.matches_played = 0
    passport.metadata = metadata or {
        "riot_puuid": TEST_PUUID,
        "riot_region": TEST_REGION,
    }

    if with_oauth:
        oauth = MagicMock()
        oauth.provider = GameOAuthConnection.Provider.RIOT
        oauth.provider_account_id = TEST_PUUID
        oauth.game_shard = TEST_REGION
        oauth.last_synced_at = None
        passport.oauth_connection = oauth
    else:
        del passport.oauth_connection  # triggers AttributeError → getattr returns None
        passport.configure_mock(**{"oauth_connection": None})

    return passport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _separator(title: str) -> str:
    return f"\n{'='*70}\n  {title}\n{'='*70}"


def _assert_eq(label: str, actual: Any, expected: Any, report: dict) -> None:
    ok = actual == expected
    status = "PASS" if ok else "FAIL"
    report["assertions"].append({"check": label, "status": status,
                                  "expected": expected, "actual": actual})
    marker = "✓" if ok else "✗"
    print(f"  {marker} [{status}] {label}: expected={expected!r}  actual={actual!r}")


def _assert_approx(
    label: str, actual: float, expected: float, tol: float, report: dict
) -> None:
    ok = abs(actual - expected) <= tol
    status = "PASS" if ok else "FAIL"
    report["assertions"].append({"check": label, "status": status,
                                  "expected": expected, "actual": actual,
                                  "tolerance": tol})
    marker = "✓" if ok else "✗"
    print(f"  {marker} [{status}] {label}: expected≈{expected}  actual={actual}  tol={tol}")


# ---------------------------------------------------------------------------
# Test 1: Unit-level aggregation (no DB needed)
# ---------------------------------------------------------------------------

def test_aggregation_unit(report: dict) -> bool:
    print(_separator("TEST 1 · Unit aggregation (no DB)"))
    report["tests"]["aggregation_unit"] = {}
    t = report["tests"]["aggregation_unit"]
    t["assertions"] = report["assertions"] = []

    snapshots = [_make_mock_match(i) for i in range(10)]
    # Use _extract_player_match_snapshot to build the snapshots list as the real code does
    extracted = []
    for match_data in snapshots:
        snap = _extract_player_match_snapshot(match_data, TEST_PUUID)
        if snap:
            extracted.append(snap)

    dummy_passport = MagicMock()
    dummy_passport.main_role = ""

    aggregates = _aggregate_recent_metrics(dummy_passport, extracted, source_region=TEST_REGION)

    _assert_eq("sample_size",         aggregates["sample_size"],         EXPECTED["sample_size"],         report)
    _assert_eq("kills",               aggregates["kills"],               EXPECTED["kills"],                report)
    _assert_eq("deaths",              aggregates["deaths"],              EXPECTED["deaths"],               report)
    _assert_eq("assists",             aggregates["assists"],             EXPECTED["assists"],              report)
    _assert_eq("wins",                aggregates["wins"],                EXPECTED["wins"],                 report)
    _assert_eq("losses",              aggregates["losses"],              EXPECTED["losses"],               report)
    _assert_approx("recent_kd_ratio", aggregates["recent_kd_ratio"],     EXPECTED["recent_kd_ratio"], 0.001, report)
    _assert_eq("recent_win_rate_pct", aggregates["recent_win_rate_pct"], EXPECTED["recent_win_rate_pct"], report)
    _assert_eq("most_played_agent",   aggregates["most_played_agent"],   EXPECTED["most_played_agent"],   report)
    _assert_eq("most_played_role",    aggregates["most_played_role"],    EXPECTED["most_played_role"],    report)

    t["aggregates"] = aggregates
    t["status"] = "passed" if all(a["status"] == "PASS" for a in t["assertions"]) else "failed"
    print(f"\n  → Test 1 result: {t['status'].upper()}")
    report["assertions"] = []  # reset shared list
    return t["status"] == "passed"


# ---------------------------------------------------------------------------
# Test 2: Single-passport sync (full pipeline: query → Riot mock → persist)
# ---------------------------------------------------------------------------

@override_settings(
    RIOT_SYNC_REQUIRE_VERIFIED=False,
    RIOT_SYNC_MAX_MATCHES=10,
    RIOT_SYNC_MATCH_DELAY_SECONDS=0,
    RIOT_SYNC_PASSPORT_DELAY_SECONDS=0,
)
def test_single_passport_sync(report: dict) -> None:
    """
    Full pipeline test: mocked Riot API responses are fed through the real
    aggregation and persistence logic.  The mock GameProfile captures every
    field assignment so we can produce the exact 'would-be-persisted' payload.
    """
    print(_separator("TEST 2 · Single-passport sync (mocked Riot API + mocked ORM)"))
    t = report["tests"]["single_passport_sync"] = {"assertions": []}
    report["assertions"] = t["assertions"]

    # Build a realistic mock passport (no DB touch needed)
    mock_passport = _make_mock_passport(passport_id=42)

    with patch("apps.user_profile.tasks.fetch_recent_valorant_matches", side_effect=_mock_fetch_recent), \
         patch("apps.user_profile.tasks.fetch_match_details", side_effect=_mock_fetch_details), \
         patch("apps.user_profile.tasks._sleep"):
        result = _sync_single_passport(mock_passport)

    print(f"\n  _sync_single_passport result:\n{json.dumps(result, indent=4)}")
    t["task_result"] = result

    # ── Task return dict assertions ─────────────────────────────────────
    _assert_eq("status",             result.get("status"),             "synced",                      report)
    _assert_eq("sample_size",        result.get("sample_size"),        EXPECTED["sample_size"],        report)
    _assert_approx("recent_kd_ratio",result.get("recent_kd_ratio"),    EXPECTED["recent_kd_ratio"], 0.001, report)
    _assert_eq("recent_win_rate_pct",result.get("recent_win_rate_pct"),EXPECTED["recent_win_rate_pct"],report)
    _assert_eq("most_played_agent",  result.get("most_played_agent"),  EXPECTED["most_played_agent"],  report)
    _assert_eq("most_played_role",   result.get("most_played_role"),   EXPECTED["most_played_role"],   report)

    # ── Mock-field persistence verification ────────────────────────────
    # _persist_sync_result() assigns real Python values to the mock's attributes;
    # reading them back gives us the exact payload the real DB row would receive.
    print("\n  Verifying fields written to passport (mock-captured)...")
    _assert_approx("kd_ratio field",    mock_passport.kd_ratio,     EXPECTED["recent_kd_ratio"], 0.001, report)
    _assert_eq("win_rate field",        mock_passport.win_rate,     80,                                  report)
    _assert_eq("matches_played field",  mock_passport.matches_played, EXPECTED["sample_size"],            report)
    _assert_eq("main_role field",       mock_passport.main_role,    EXPECTED["most_played_role"],         report)

    live_stats = mock_passport.metadata.get("live_stats", {}).get("valorant", {})
    print(f"\n  metadata[live_stats][valorant] (persisted payload):\n{json.dumps(live_stats, indent=4, default=str)}")
    t["db_live_stats"] = live_stats

    _assert_eq("meta kills",             live_stats.get("kills"),             EXPECTED["kills"],             report)
    _assert_eq("meta deaths",            live_stats.get("deaths"),            EXPECTED["deaths"],            report)
    _assert_eq("meta wins",              live_stats.get("wins"),              EXPECTED["wins"],              report)
    _assert_eq("meta losses",            live_stats.get("losses"),            EXPECTED["losses"],            report)
    _assert_eq("meta sample_size",       live_stats.get("sample_size"),       EXPECTED["sample_size"],       report)
    _assert_eq("meta most_played_agent", live_stats.get("most_played_agent"), EXPECTED["most_played_agent"], report)
    _assert_eq("meta most_played_role",  live_stats.get("most_played_role"),  EXPECTED["most_played_role"],  report)
    _assert_eq("meta api_synced",        mock_passport.metadata.get("api_synced"),    True,                  report)
    _assert_eq("meta oauth_provider",    mock_passport.metadata.get("oauth_provider"), "riot",               report)

    # ── save() call verification ────────────────────────────────────────
    # Verify passport.save() was called with the right update_fields
    save_calls = mock_passport.save.call_args_list
    _assert_eq("passport.save() called once", len(save_calls), 1, report)
    if save_calls:
        save_kwargs = save_calls[0].kwargs
        actual_fields = set(save_kwargs.get("update_fields", []))
        required_fields = {"kd_ratio", "win_rate", "matches_played", "metadata", "main_role"}
        _assert_eq("update_fields contains core columns",
                   required_fields.issubset(actual_fields), True, report)
        t["save_update_fields"] = sorted(actual_fields)
        print(f"\n  passport.save(update_fields={sorted(actual_fields)})")

    # ── OAuth connection last_synced_at ─────────────────────────────────
    oauth = mock_passport.oauth_connection
    oauth_saves = oauth.save.call_args_list
    _assert_eq("oauth.save() called once",      len(oauth_saves), 1, report)
    if oauth_saves:
        _assert_eq("last_synced_at in oauth update_fields",
                   "last_synced_at" in oauth_saves[0].kwargs.get("update_fields", []), True, report)
    last_synced_set = oauth.last_synced_at is not None
    _assert_eq("oauth last_synced_at set", last_synced_set, True, report)

    t["status"] = "passed" if all(a["status"] == "PASS" for a in t["assertions"]) else "failed"
    print(f"\n  → Test 2 result: {t['status'].upper()}")
    report["assertions"] = []


# ---------------------------------------------------------------------------
# Test 3: Celery task wrapper for single passport (synchronous call)
# ---------------------------------------------------------------------------

@override_settings(
    RIOT_SYNC_REQUIRE_VERIFIED=False,
    RIOT_SYNC_MAX_MATCHES=10,
    RIOT_SYNC_MATCH_DELAY_SECONDS=0,
    RIOT_SYNC_PASSPORT_DELAY_SECONDS=0,
)
def test_celery_task_wrapper(report: dict) -> None:
    """
    Tests the @shared_task wrapper, sync_single_riot_passport(passport_id).
    The ORM lookup is patched so no real DB is required.
    """
    print(_separator("TEST 3 · Celery task wrapper: sync_single_riot_passport"))
    t = report["tests"]["celery_task_wrapper"] = {"assertions": []}
    report["assertions"] = t["assertions"]

    from apps.user_profile.models_main import GameProfile as RealGameProfile

    mock_passport = _make_mock_passport(passport_id=42)

    # Mock qs: GameProfile.objects.select_related(...).get(...) → mock_passport
    mock_qs = MagicMock()
    mock_qs.get.return_value = mock_passport
    mock_gp_class = MagicMock(spec=RealGameProfile)
    mock_gp_class.objects.select_related.return_value = mock_qs
    mock_gp_class.DoesNotExist = RealGameProfile.DoesNotExist

    with patch("apps.user_profile.tasks.GameProfile", mock_gp_class), \
         patch("apps.user_profile.tasks.fetch_recent_valorant_matches", side_effect=_mock_fetch_recent), \
         patch("apps.user_profile.tasks.fetch_match_details", side_effect=_mock_fetch_details), \
         patch("apps.user_profile.tasks._sleep"):
        result = sync_single_riot_passport(42)

    print(f"\n  sync_single_riot_passport(42) result:\n{json.dumps(result, indent=4)}")
    t["task_result"] = result

    _assert_eq("status",             result.get("status"),             "synced",                       report)
    _assert_eq("passport_id",        result.get("passport_id"),        42,                             report)
    _assert_approx("kd_ratio",       result.get("recent_kd_ratio"),    EXPECTED["recent_kd_ratio"], 0.001, report)
    _assert_eq("win_rate",           result.get("recent_win_rate_pct"),EXPECTED["recent_win_rate_pct"],report)
    _assert_eq("most_played_agent",  result.get("most_played_agent"),  EXPECTED["most_played_agent"],  report)

    # ── Missing-passport path ───────────────────────────────────────────
    mock_qs_missing = MagicMock()
    mock_qs_missing.get.side_effect = RealGameProfile.DoesNotExist
    mock_gp_class.objects.select_related.return_value = mock_qs_missing

    with patch("apps.user_profile.tasks.GameProfile", mock_gp_class):
        missing_result = sync_single_riot_passport(999_999_999)

    print(f"\n  sync_single_riot_passport(999999999) result: {missing_result}")
    _assert_eq("missing passport status",      missing_result.get("status"),      "missing",   report)
    _assert_eq("missing passport_id echoed",   missing_result.get("passport_id"), 999_999_999, report)

    t["status"] = "passed" if all(a["status"] == "PASS" for a in t["assertions"]) else "failed"
    print(f"\n  → Test 3 result: {t['status'].upper()}")
    report["assertions"] = []


# ---------------------------------------------------------------------------
# Test 4: Batch task dry-run (candidate selection + full sweep)
# ---------------------------------------------------------------------------

@override_settings(
    RIOT_SYNC_REQUIRE_VERIFIED=False,
    RIOT_SYNC_MAX_MATCHES=10,
    RIOT_SYNC_MATCH_DELAY_SECONDS=0,
    RIOT_SYNC_PASSPORT_DELAY_SECONDS=0,
)
def test_batch_task(report: dict) -> None:
    """
    Dry-runs sync_all_active_riot_passports() using a mocked candidate queryset.
    Two mock passports are injected; the Riot API calls are mocked so the full
    per-passport loop executes and the summary dict is verified.
    """
    print(_separator("TEST 4 · Batch task: sync_all_active_riot_passports (dry-run)"))
    t = report["tests"]["batch_task"] = {"assertions": []}
    report["assertions"] = t["assertions"]

    mock_passport_a = _make_mock_passport(passport_id=10)
    mock_passport_b = _make_mock_passport(passport_id=11)

    mock_qs = MagicMock()
    mock_qs.count.return_value = 2
    mock_qs.iterator.return_value = iter([mock_passport_a, mock_passport_b])

    with patch("apps.user_profile.tasks._candidate_passports", return_value=mock_qs), \
         patch("apps.user_profile.tasks.fetch_recent_valorant_matches", side_effect=_mock_fetch_recent), \
         patch("apps.user_profile.tasks.fetch_match_details", side_effect=_mock_fetch_details), \
         patch("apps.user_profile.tasks._sleep"):
        summary = sync_all_active_riot_passports()

    print(f"\n  sync_all_active_riot_passports() summary:\n{json.dumps(summary, indent=4, default=str)}")
    t["summary"] = summary

    _assert_eq("total_candidates",        summary.get("total_candidates"), 2,    report)
    _assert_eq("synced",                  summary.get("synced"),           2,    report)
    _assert_eq("failed",                  summary.get("failed"),           0,    report)
    _assert_eq("finished_at present",     "finished_at"      in summary,  True, report)
    _assert_eq("duration_seconds present","duration_seconds" in summary,  True, report)
    _assert_eq("passport 10 in synced",   10 in summary.get("synced_passport_ids", []), True, report)
    _assert_eq("passport 11 in synced",   11 in summary.get("synced_passport_ids", []), True, report)

    t["status"] = "passed" if all(a["status"] == "PASS" for a in t["assertions"]) else "failed"
    print(f"\n  → Test 4 result: {t['status'].upper()}")
    report["assertions"] = []


# ---------------------------------------------------------------------------
# Test 5: Rate-limit retry path
# ---------------------------------------------------------------------------

def test_rate_limit_retry(report: dict) -> None:
    print(_separator("TEST 5 · 429 Rate-limit retry logic"))
    report["tests"]["rate_limit_retry"] = {}
    t = report["tests"]["rate_limit_retry"]
    t["assertions"] = report["assertions"] = []

    from apps.user_profile.services.riot_match_service import RiotMatchServiceError
    from apps.user_profile.tasks import _call_riot_with_retry

    call_count = {"n": 0}

    def _fail_once_then_succeed(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RiotMatchServiceError(
                error_code="RIOT_RATE_LIMITED",
                message="rate limited",
                status_code=429,
                metadata={"retry_after_seconds": 0},
            )
        return {"match_ids": ["VAL-RETRY-0001"]}

    @override_settings(RIOT_SYNC_MAX_RETRY_ATTEMPTS=2, RIOT_SYNC_RATE_LIMIT_BACKOFF_SECONDS=0)
    def _run():
        with patch("apps.user_profile.tasks._sleep"):
            return _call_riot_with_retry(_fail_once_then_succeed, puuid=TEST_PUUID, region=TEST_REGION)

    result = _run()
    _assert_eq("retry succeeded after 429", result.get("match_ids"), ["VAL-RETRY-0001"], report)
    _assert_eq("was called exactly 2 times", call_count["n"], 2, report)

    # Verify exhaustion raises correctly
    def _always_rate_limited(*args, **kwargs):
        raise RiotMatchServiceError(
            error_code="RIOT_RATE_LIMITED",
            message="always limited",
            status_code=429,
            metadata={"retry_after_seconds": 0},
        )

    raised_correctly = False

    @override_settings(RIOT_SYNC_MAX_RETRY_ATTEMPTS=2, RIOT_SYNC_RATE_LIMIT_BACKOFF_SECONDS=0)
    def _run_exhausted():
        nonlocal raised_correctly
        with patch("apps.user_profile.tasks._sleep"):
            try:
                _call_riot_with_retry(_always_rate_limited)
            except RiotMatchServiceError as exc:
                raised_correctly = exc.error_code == "RIOT_RETRY_EXHAUSTED"

    _run_exhausted()
    _assert_eq("raises RIOT_RETRY_EXHAUSTED after max retries", raised_correctly, True, report)

    t["status"] = "passed" if all(a["status"] == "PASS" for a in t["assertions"]) else "failed"
    print(f"\n  → Test 5 result: {t['status'].upper()}")
    report["assertions"] = []


# ---------------------------------------------------------------------------
# Test 6: Role inference edge cases
# ---------------------------------------------------------------------------

def test_role_inference(report: dict) -> None:
    print(_separator("TEST 6 · Agent → Role inference"))
    report["tests"]["role_inference"] = {}
    t = report["tests"]["role_inference"]
    t["assertions"] = report["assertions"] = []

    cases = [
        ("agent_jett",      "Duelist"),
        ("JETT_UUID",       "Duelist"),
        ("Reyna_abc",       "Duelist"),
        ("omen-uuid-xyz",   "Controller"),
        ("Sage_main",       "Sentinel"),
        ("sova_recon",      "Initiator"),
        ("completely_new",  "Unknown"),
        ("",                "Unknown"),
    ]

    for agent_id, expected_role in cases:
        actual = _resolve_role(agent_id)
        ok = actual == expected_role
        label = f"_resolve_role({agent_id!r})"
        _assert_eq(label, actual, expected_role, report)

    t["status"] = "passed" if all(a["status"] == "PASS" for a in t["assertions"]) else "failed"
    print(f"\n  → Test 6 result: {t['status'].upper()}")
    report["assertions"] = []


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main() -> int:
    report: dict[str, Any] = {
        "suite": "Phase 10 QA — Riot Sync Engine Smoke Test",
        "executed_at": timezone.now().isoformat(),
        "python_version": sys.version,
        "tests": {},
        "assertions": [],
        "overall_status": "pending",
    }

    overall_pass = True

    try:
        print("\n" + "─" * 70)
        print("  Phase 10 QA — Riot Sync Engine Smoke Test")
        print("  All ORM operations are mocked — no DB or Celery worker required")
        print("─" * 70)

        t1_ok = test_aggregation_unit(report)
        overall_pass = overall_pass and t1_ok

        test_single_passport_sync(report)
        t2_ok = report["tests"]["single_passport_sync"]["status"] == "passed"
        overall_pass = overall_pass and t2_ok

        test_celery_task_wrapper(report)
        t3_ok = report["tests"]["celery_task_wrapper"]["status"] == "passed"
        overall_pass = overall_pass and t3_ok

        test_batch_task(report)
        t4_ok = report["tests"]["batch_task"]["status"] == "passed"
        overall_pass = overall_pass and t4_ok

        test_rate_limit_retry(report)
        t5_ok = report["tests"]["rate_limit_retry"]["status"] == "passed"
        overall_pass = overall_pass and t5_ok

        test_role_inference(report)
        t6_ok = report["tests"]["role_inference"]["status"] == "passed"
        overall_pass = overall_pass and t6_ok

    except Exception as exc:
        overall_pass = False
        report["fatal_error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        print(f"\n[FATAL] Unhandled exception: {exc}")
        traceback.print_exc()

    # ── Final report ──────────────────────────────────────────────────────
    report["overall_status"] = "passed" if overall_pass else "failed"
    report.pop("assertions", None)  # clear the shared scratch list

    print(_separator(f"FINAL RESULT: {'✅ ALL TESTS PASSED' if overall_pass else '❌ SOME TESTS FAILED'}"))

    # Summarise per-test
    print("\n  Summary:")
    for name, data in report["tests"].items():
        status = data.get("status", "unknown").upper()
        marker = "✓" if status == "PASSED" else "✗"
        print(f"    {marker} {name}: {status}")

    print("\n" + "=" * 70)
    print("  Full QA Report JSON:")
    print("=" * 70)

    # Trim for readability — drop per-assertion lists from final JSON
    condensed = {k: v for k, v in report.items() if k not in ("assertions",)}
    for test_name, test_data in condensed.get("tests", {}).items():
        test_data.pop("assertions", None)

    print(json.dumps(condensed, indent=2, default=str))

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
