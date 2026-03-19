# Automated Match Result Fetching — Architecture Roadmap

**Project:** DeltaCrown  
**Scope:** 100% automated match result ingestion via Riot Match-V5 and Steam Web API  
**Status:** Planning / Pre-implementation  
**Last Updated:** 2026

---

## Table of Contents

1. [Overview & Goals](#1-overview--goals)
2. [Existing Model Inventory](#2-existing-model-inventory)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Riot Match-V5 Integration (Valorant)](#4-riot-match-v5-integration-valorant)
5. [Steam API Integration (CS2 & Dota 2)](#5-steam-api-integration-cs2--dota-2)
6. [Automated Ingestion Flow (Common)](#6-automated-ingestion-flow-common)
7. [Anti-Smurfing & Integrity Checks](#7-anti-smurfing--integrity-checks)
8. [Dispute Escalation & Manual Override](#8-dispute-escalation--manual-override)
9. [Celery Task Architecture](#9-celery-task-architecture)
10. [New Model Fields Required](#10-new-model-fields-required)
11. [Implementation Phases](#11-implementation-phases)

---

## 1. Overview & Goals

### Current State
Match results are submitted **manually** by players via `MatchResultSubmission` with `source=MANUAL`. The opponent must confirm within 24 hours or the system auto-confirms. Disputes are handled by organizers.

### Target State
For supported games (Valorant, CS2, Dota 2), the system fetches match results **directly from official game APIs** after a match ends:

- `source=RIOT_API` for Valorant matches fetched from Riot Match-V5
- `source=STEAM_API` for CS2/Dota 2 matches fetched from Steam Web API
- Results are auto-confirmed without requiring opponent confirmation
- Participant PUUIDs/Steam IDs are validated against registered `ProviderAccount` records
- Mismatches trigger `DisputeRecord` with `reason=CHEATING_SUSPICION`

### Non-Goals (this roadmap)
- Real-time in-match overlays (separate spectator scope)
- Riot RSO (Riot Sign-On) for League of Legends / TFT (expandable later via `RIOT_SUPPORTED_GAMES`)
- Steam matchmaking integration (only result fetching)

---

## 2. Existing Model Inventory

### `Match` (`tournament_engine_match_match`)
| Field | Type | Notes |
|---|---|---|
| `state` | CharField | `SCHEDULED → CHECK_IN → READY → LIVE → PENDING_RESULT → COMPLETED / DISPUTED / FORFEIT` |
| `participant1_id / participant2_id` | PositiveIntegerField | Registration PK |
| `participant1_score / participant2_score` | PositiveIntegerField | Series wins |
| `winner_id / loser_id` | PositiveIntegerField | Set on COMPLETED |
| `best_of` | SmallPositiveIntegerField | 1 / 3 / 5 |
| `game_scores` | JSONField | `[{"game": 1, "p1": 13, "p2": 8, "winner_slot": 1}]` |
| `lobby_info` | JSONField | `{"lobby_code": "ABC123", "match_id": "...", "region": "ap"}` |
| `scheduled_time` | DateTimeField | Start time for polling trigger |

### `MatchResultSubmission` (`tournament_engine_match_resultsubmission` or similar)
| Field | Type | Notes |
|---|---|---|
| `status` | CharField | `PENDING / CONFIRMED / AUTO_CONFIRMED / FINALIZED / REJECTED` |
| `source` | CharField | **`MANUAL / RIOT_API / ADMIN_OVERRIDE`** — `STEAM_API` needs adding |
| `raw_result_payload` | JSONField | Full API response stored verbatim |
| `ingestion_fingerprint` | CharField(255, unique) | Deduplication key |
| `ingested_at` | DateTimeField | Timestamp of automated ingestion |

### `ProviderAccount` (`user_profile_provider_account`)
| Field | Type | Notes |
|---|---|---|
| `provider` | CharField | `riot / steam / epic` |
| `provider_account_id` | CharField | PUUID (Riot) or Steam64 ID (Steam) |
| `provider_data` | JSONField | Full verified identity data |

### `GameOAuthConnection` (`user_profile_game_oauth_connection`)
Links `ProviderAccount → GameProfile` for verified players. Used to look up a tournament participant's PUUID/SteamID.

### `Registration` (tournaments domain)
Links a user/team to a `Tournament`. The `participant1_id / participant2_id` in `Match` are `Registration` PKs.

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Match reaches LIVE state                               │
│  lobby_info["match_id"] populated (or scheduled_time)   │
└───────────────────────┬─────────────────────────────────┘
                        │
          ┌─────────────▼──────────────┐
          │  Celery Beat Scheduler      │
          │  poll_pending_matches()     │
          │  every 2 minutes            │
          └─────────────┬──────────────┘
                        │
          ┌─────────────▼──────────────┐
          │  Provider Router           │
          │  game.slug → fetcher class  │
          ├────────────┬───────────────┤
          │ valorant   │ cs2 / dota2   │
          └─────┬──────┴───────┬───────┘
                │              │
   ┌────────────▼──┐    ┌──────▼────────────┐
   │ RiotMatchV5   │    │ SteamResultFetcher  │
   │ Fetcher       │    │ (CS2 / Dota2)       │
   └────────────┬──┘    └──────┬─────────────┘
                │              │
                └──────┬───────┘
                       │
          ┌────────────▼────────────────────┐
          │  MatchIngestionService           │
          │  1. Validate participant PUUIDs  │
          │  2. Extract scores / winner      │
          │  3. Write Match + game_scores    │
          │  4. Create MatchResultSubmission │
          │     source=RIOT_API / STEAM_API  │
          │     status=AUTO_CONFIRMED        │
          │  5. Advance bracket              │
          └────────────┬────────────────────┘
                       │
          ┌────────────▼────────────────────┐
          │  Anti-Smurfing Gate              │
          │  Cross-check puuids in payload   │
          │  vs registered participants      │
          │  Unregistered player → flag      │
          │  DisputeRecord(CHEATING_SUSPICION)│
          └─────────────────────────────────┘
```

---

## 4. Riot Match-V5 Integration (Valorant)

### 4.1 Lobby → Match ID Flow

Before the system can fetch a match, it needs the Riot match ID. There are two paths:

**Path A — Organizer provides match ID (recommended for MVP)**  
The organizer pastes the Riot match ID into the lobby panel. This is stored in:
```python
match.lobby_info["riot_match_id"] = "APAC1-12345"
```

**Path B — Automated discovery via Riot Account API (future)**  
After `match.completed_at` is set (or scheduled_time + buffer), poll:
```
GET https://{region}.api.riotgames.com/val/match/v1/matchlists/by-puuid/{puuid}
```
to discover the most recent match and verify it occurred within the expected time window.

### 4.2 Riot Match-V5 Endpoint

```
GET https://{cluster}.api.riotgames.com/val/match/v1/matches/{matchId}

Headers:
  X-Riot-Token: {RIOT_API_KEY}
```

Where `{cluster}` is derived from `match.lobby_info["region"]` (e.g., `ap`, `eu`, `na`). Allowed values mirror the `_account_clusters()` helper in `oauth_riot_service.py`.

**Response structure (relevant fields):**
```json
{
  "matchInfo": {
    "matchId": "APAC1-12345",
    "gameStartMillis": 1700000000000,
    "gameLengthMillis": 2400000,
    "gameMode": "Competitive",
    "isCompleted": true
  },
  "players": [
    {
      "puuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "teamId": "Red",
      "stats": { "kills": 22, "deaths": 14, "assists": 5, "score": 5820 }
    }
  ],
  "teams": [
    { "teamId": "Red", "won": true, "roundsPlayed": 24, "roundsWon": 13 },
    { "teamId": "Blue", "won": false, "roundsPlayed": 24, "roundsWon": 11 }
  ],
  "roundResults": [ ... ]
}
```

### 4.3 PUUID Resolution for Participants

Each `Registration` links to a `user` who has a `ProviderAccount(provider="riot")`. The system resolves participant PUUIDs as follows:

```python
def get_puuids_for_registration(registration) -> list[str]:
    """Return all Riot PUUIDs for players in this registration (solo or team)."""
    if registration.team:
        user_ids = registration.team.members.values_list("user_id", flat=True)
    else:
        user_ids = [registration.user_id]

    return list(
        ProviderAccount.objects.filter(
            provider=ProviderAccount.Provider.RIOT,
            user_id__in=user_ids,
        ).values_list("provider_account_id", flat=True)
    )
```

### 4.4 Winner & Score Extraction

```python
def parse_valorant_result(payload: dict, p1_puuids: list[str], p2_puuids: list[str]):
    """
    Given the Match-V5 response and participant PUUID sets, determine:
    - Which teamId each participant belongs to
    - Which team won
    - Round scores
    """
    players = payload.get("players", [])
    teams = payload.get("teams", [])

    p1_team_ids = set()
    p2_team_ids = set()
    for player in players:
        if player["puuid"] in p1_puuids:
            p1_team_ids.add(player["teamId"])
        elif player["puuid"] in p2_puuids:
            p2_team_ids.add(player["teamId"])

    # A participant team should have exactly one teamId (Red or Blue)
    if len(p1_team_ids) != 1 or len(p2_team_ids) != 1:
        raise IngestionError("PARTICIPANT_TEAM_MISMATCH", ...)

    p1_team_id = p1_team_ids.pop()
    p2_team_id = p2_team_ids.pop()

    p1_rounds = next((t["roundsWon"] for t in teams if t["teamId"] == p1_team_id), 0)
    p2_rounds = next((t["roundsWon"] for t in teams if t["teamId"] == p2_team_id), 0)
    p1_won = next((t["won"] for t in teams if t["teamId"] == p1_team_id), False)

    return {
        "participant1_score": 1 if p1_won else 0,   # series wins (BO1 = 1 game)
        "participant2_score": 0 if p1_won else 1,
        "winner_slot": 1 if p1_won else 2,
        "game_scores": [
            {
                "game": 1,
                "p1": p1_rounds,
                "p2": p2_rounds,
                "winner_slot": 1 if p1_won else 2,
            }
        ],
        "raw_team_p1": p1_team_id,
        "raw_team_p2": p2_team_id,
    }
```

For **BO3/BO5 series**, the task runs after each game ends and accumulates results in `match.game_scores`. The match is marked `COMPLETED` when one participant reaches `ceil(best_of / 2)` wins.

### 4.5 Rate Limits

Riot Development key: 100 requests per 2 minutes per routing value. Production key: consult Riot developer portal.

Strategy:
- Batch at most 20 match fetches per Celery beat cycle
- Use Django-redis to store per-route request counters with 120s TTL
- Back off with exponential retry if HTTP 429 received

---

## 5. Steam API Integration (CS2 & Dota 2)

### 5.1 CS2 — Game Result via ShareCode

CS2 (Counter-Strike 2) uses **match sharing codes** that players receive after a competitive match. The organizer (or player) submits this code. The system resolves it via:

```
GET https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1
  ?key={STEAM_API_KEY}
  &steamid={STEAM64_ID}
  &steamidkey={AUTH_CODE}
  &knowncode={sharecode}
```

This returns the next code in the chain. To decode a share code into a match ID, use the share-code decoder:
- Share code format: `CSGO-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX`
- Decodes to: `{matchId, outcomeId, tokenId}` (open-source decoder available)

Once the matchId is known, fetch full match data:
```
GET https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/
    (or via protobuf / GCPD protocol — see Valve documentation)
```

**MVP Alternative**: Use `GetRecentlyPlayedGames` + time-window matching to find the match, combined with `GetPlayerSummaries` to verify participation.

### 5.2 Dota 2 — GetMatchDetails

Dota 2 exposes a direct match ID via the game lobby. Store it in `match.lobby_info["dota2_match_id"]`.

```
GET https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/v1
  ?key={STEAM_API_KEY}
  &match_id={MATCH_ID}
```

**Response (relevant fields):**
```json
{
  "result": {
    "match_id": 7654321098,
    "radiant_win": true,
    "duration": 2647,
    "players": [
      { "account_id": 12345678, "player_slot": 0, "kills": 10 }
    ]
  }
}
```

`account_id` in Dota 2 = `steam64_id - 76561197960265728`. Convert back to Steam64 for lookup against `ProviderAccount.provider_account_id`.

### 5.3 Steam PUUID Resolution

```python
def get_steam_ids_for_registration(registration) -> list[str]:
    if registration.team:
        user_ids = registration.team.members.values_list("user_id", flat=True)
    else:
        user_ids = [registration.user_id]

    return list(
        ProviderAccount.objects.filter(
            provider=ProviderAccount.Provider.STEAM,
            user_id__in=user_ids,
        ).values_list("provider_account_id", flat=True)
    )
```

### 5.4 Rate Limits

Steam Web API: 100,000 calls per day (default). Throttle to ~1 request/second per key. Use the same Redis counter strategy as Riot.

---

## 6. Automated Ingestion Flow (Common)

### 6.1 `MatchIngestionService.ingest(match, payload, source)`

This is the central service that handles all automated result ingestion, regardless of provider.

```python
class MatchIngestionService:
    """
    Validate, write, and finalize an automated match result.
    Called by provider-specific fetchers after retrieving raw API data.
    """

    def ingest(
        self,
        match: Match,
        parsed_result: ParsedMatchResult,
        raw_payload: dict,
        source: str,  # MatchResultSubmission.SOURCE_RIOT_API | SOURCE_STEAM_API
        ingestion_fingerprint: str,
    ) -> MatchResultSubmission:

        with transaction.atomic():
            # 1. Idempotency guard — skip if already ingested
            if MatchResultSubmission.objects.filter(
                ingestion_fingerprint=ingestion_fingerprint
            ).exists():
                return MatchResultSubmission.objects.get(
                    ingestion_fingerprint=ingestion_fingerprint
                )

            # 2. Write scores to Match
            match.participant1_score = parsed_result.participant1_score
            match.participant2_score = parsed_result.participant2_score
            match.winner_id = (
                match.participant1_id
                if parsed_result.winner_slot == 1
                else match.participant2_id
            )
            match.loser_id = (
                match.participant2_id
                if parsed_result.winner_slot == 1
                else match.participant1_id
            )
            match.game_scores = parsed_result.game_scores
            match.state = Match.COMPLETED
            match.completed_at = timezone.now()
            match.save(update_fields=[
                "participant1_score", "participant2_score",
                "winner_id", "loser_id", "game_scores",
                "state", "completed_at", "updated_at",
            ])

            # 3. Create an AUTO_CONFIRMED MatchResultSubmission
            submission = MatchResultSubmission.objects.create(
                match=match,
                submitted_by_user=get_system_user(),   # sentinel bot user
                raw_result_payload=raw_payload,
                status=MatchResultSubmission.STATUS_AUTO_CONFIRMED,
                source=source,
                ingestion_fingerprint=ingestion_fingerprint,
                ingested_at=timezone.now(),
                auto_confirm_deadline=timezone.now(),  # already confirmed
            )

            # 4. Advance bracket (queue async to avoid deadlock under load)
            advance_bracket_after_match.delay(match.pk)

        return submission
```

### 6.2 Ingestion Fingerprint

The fingerprint uniquely identifies the automated source record and prevents double-ingestion:

| Source | Fingerprint Format |
|---|---|
| Riot Match-V5 | `riot:{matchId}` |
| Dota 2 | `dota2:{match_id}` |
| CS2 | `cs2:{match_token_id}` |

---

## 7. Anti-Smurfing & Integrity Checks

### 7.1 PUUID Roster Validation

After parsing the raw API payload, cross-reference every PUUID found in the match against the registered participants:

```python
def validate_participant_puuids(
    match: Match,
    payload_puuids: set[str],
    registration1_puuids: set[str],
    registration2_puuids: set[str],
) -> list[str]:
    """
    Returns a list of unregistered PUUIDs found in the match payload.
    An empty list means the match is clean.
    """
    registered = registration1_puuids | registration2_puuids
    unregistered = payload_puuids - registered
    return list(unregistered)
```

### 7.2 Flagging Procedure

If `unregistered_puuids` is non-empty:

```python
with transaction.atomic():
    # Flag the submission
    submission.status = MatchResultSubmission.STATUS_DISPUTED

    # Create a DisputeRecord for organizer review
    DisputeRecord.objects.create(
        submission=submission,
        reason=DisputeRecord.CHEATING_SUSPICION,
        notes=(
            f"Automated integrity check: {len(unregistered_puuids)} unregistered "
            f"PUUID(s) found in match payload: {', '.join(unregistered_puuids[:5])}..."
        ),
        flagged_by_system=True,
    )

    # Hold the match in DISPUTED state rather than COMPLETED
    match.state = Match.DISPUTED
    match.save(update_fields=["state", "updated_at"])
```

### 7.3 Player Count Threshold

A tolerance threshold is configurable to handle coach/observer slots (Valorant 5v5 = expect exactly 10 PUUIDs):

```python
INTEGRITY_STRICT_GAMES = {"valorant"}          # exact player count enforced
INTEGRITY_RELAXED_GAMES = {"cs2", "dota2"}     # allow ±1 for coach/observer slots
```

### 7.4 Team Composition Mismatch

Beyond unregistered PUUIDs, also check:
- A player appears on **both** teams in the payload (impossible in fair play)
- A registered player is **absent** from the payload entirely (substitution without pre-approval)

These also raise `DisputeRecord(reason=SCORE_MISMATCH)` and hold the match for review.

---

## 8. Dispute Escalation & Manual Override

### 8.1 Dispute Resolution Paths

```
AUTO_CONFIRMED submission → all clear
DISPUTED submission       → one of:
  a) Organizer reviews DisputeRecord
     → marks RESOLVED + approves original result
     → creates new MatchResultSubmission(source=ADMIN_OVERRIDE, status=FINALIZED)
  b) Organizer rejects disputed result
     → MatchResultSubmission.status = REJECTED
     → Match.state returns to PENDING_RESULT for manual re-entry
  c) Organizer confirms cheating
     → DisputeRecord escalated to moderation team
     → Tournament.status may be set to SUSPENDED pending investigation
```

### 8.2 Admin Override Path

An organizer or superadmin can always write a result directly:

```python
# views/organizer_match_ops_views.py — existing MatchOps endpoint
POST /api/toc/matches/{match_pk}/result/override/
{
  "winner_slot": 1,
  "participant1_score": 2,
  "participant2_score": 0,
  "game_scores": [...],
  "reason": "Correcting API data error"
}
```

This creates a new `MatchResultSubmission(source=ADMIN_OVERRIDE, status=FINALIZED)` and supersedes any prior automated submission.

---

## 9. Celery Task Architecture

### 9.1 Task Map

| Task | Trigger | Frequency |
|---|---|---|
| `poll_pending_riot_matches` | Celery Beat | Every 2 minutes |
| `poll_pending_steam_matches` | Celery Beat | Every 5 minutes |
| `fetch_riot_match_v5` | Called by poller | Per match |
| `fetch_steam_match_result` | Called by poller | Per match |
| `ingest_match_result` | After fetch | Per match |
| `advance_bracket_after_match` | After ingest | Per match |
| `auto_confirm_manual_submissions` | Celery Beat | Every 15 minutes |

### 9.2 Poller Task Example

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def poll_pending_riot_matches(self):
    """
    Find all LIVE or PENDING_RESULT Valorant matches that have a riot_match_id
    in lobby_info but no AUTO_CONFIRMED submission yet.
    """
    matches = (
        Match.objects
        .filter(
            state__in=[Match.LIVE, Match.PENDING_RESULT],
            tournament__game__slug="valorant",
        )
        .annotate(
            has_auto_result=models.Exists(
                MatchResultSubmission.objects.filter(
                    match=models.OuterRef("pk"),
                    source=MatchResultSubmission.SOURCE_RIOT_API,
                    status__in=[
                        MatchResultSubmission.STATUS_AUTO_CONFIRMED,
                        MatchResultSubmission.STATUS_FINALIZED,
                    ],
                )
            )
        )
        .filter(has_auto_result=False)
        .select_related("tournament__game")[:20]   # cap per cycle
    )

    for match in matches:
        riot_match_id = (match.lobby_info or {}).get("riot_match_id")
        if not riot_match_id:
            continue
        fetch_riot_match_v5.delay(match.pk, riot_match_id)
```

### 9.3 Redis Rate-Limit Guard

```python
from django_redis import get_redis_connection

def _check_riot_rate_limit(region: str) -> bool:
    """Returns True if the request is allowed under Riot's 100 req/2min limit."""
    redis = get_redis_connection("default")
    key = f"riot_ratelimit:{region}"
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, 120)
    return count <= 95   # 5-request safety buffer
```

---

## 10. New Model Fields Required

### `MatchResultSubmission.source` — Add `STEAM_API`

```python
# apps/tournaments/models/result_submission.py
SOURCE_STEAM_API = 'steam_api'

SOURCE_CHOICES = [
    (SOURCE_MANUAL, 'Manual Submission'),
    (SOURCE_RIOT_API, 'Riot API Ingestion'),
    (SOURCE_STEAM_API, 'Steam API Ingestion'),   # ← NEW
    (SOURCE_ADMIN_OVERRIDE, 'Admin Override'),
]
```

### `DisputeRecord` — Verify `CHEATING_SUSPICION` reason exists

Check `apps/tournaments/models/dispute.py` to confirm `CHEATING_SUSPICION` and `SCORE_MISMATCH` are already reason choices. Add `flagged_by_system = models.BooleanField(default=False)` if not present, for distinguishing automated flags from player-raised disputes.

### `Match.lobby_info` — Structured doc conventions

Document expected keys per game:

```python
# Valorant
lobby_info = {
    "riot_match_id": "APAC1-12345678901",
    "region": "ap",          # ap | eu | na | kr | latam | br
    "map": "Haven",
    "game_mode": "Competitive",
}

# CS2
lobby_info = {
    "cs2_sharecode": "CSGO-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX",
    "cs2_match_token": "...",
    "steam_server_ip": "...",
}

# Dota 2
lobby_info = {
    "dota2_match_id": "7654321098",
    "game_mode": "AllPick",
    "lobby_type": "Tournament",
}
```

---

## 11. Implementation Phases

### Phase 1 — Infrastructure (Sprint 30)
- [ ] Add `SOURCE_STEAM_API` to `MatchResultSubmission.source` choices + migration
- [ ] Add `flagged_by_system` to `DisputeRecord` + migration
- [ ] Create `apps/tournament_ops/services/match_ingestion_service.py` with `MatchIngestionService`
- [ ] Create `apps/tournament_ops/services/integrity_check.py` with PUUID validation
- [ ] Create `apps/tournament_ops/tasks/match_polling.py` with skeleton Celery tasks
- [ ] Add `RIOT_API_KEY` and `STEAM_API_KEY` to settings + `.env.example`
- [ ] Write unit tests for `parse_valorant_result` and `validate_participant_puuids`

### Phase 2 — Riot Match-V5 (Sprint 31)
- [ ] Implement `RiotMatchV5Fetcher` in `apps/tournament_ops/services/riot_result_fetcher.py`
- [ ] Implement `poll_pending_riot_matches` Celery task
- [ ] Implement `fetch_riot_match_v5` Celery task with retry + rate-limit guard
- [ ] Wire `MatchIngestionService.ingest()` for Riot source
- [ ] Add `riot_match_id` input field to organizer match lobby panel (UI)
- [ ] Integration test against Riot sandbox / recorded fixture payloads
- [ ] Load test: 50 concurrent matches, verify no duplicate submissions

### Phase 3 — Steam API (Sprint 32)
- [ ] Implement Dota 2 result fetcher via `GetMatchDetails`
- [ ] Implement CS2 result fetcher via share code decoder
- [ ] Implement `poll_pending_steam_matches` task
- [ ] Wire `MatchIngestionService.ingest()` for Steam source
- [ ] Add `dota2_match_id` / `cs2_sharecode` input fields to lobby panel

### Phase 4 — Anti-Smurfing Hardening (Sprint 33)
- [ ] Enable `INTEGRITY_STRICT_GAMES` enforcement for Valorant
- [ ] Add organizer notification when `DisputeRecord(flagged_by_system=True)` is created
- [ ] Dashboard view: "Pending Integrity Reviews" queue
- [ ] Alerts: Slack/Discord webhook notification for flagged matches

### Phase 5 — Full Automation (Sprint 34)
- [ ] Remove manual confirmation requirement for API-sourced results
- [ ] Audit log: every automated ingestion writes to `MatchOperationLog`
- [ ] Reporting: weekly automated-vs-manual ingestion ratio report
- [ ] Monitoring: Grafana dashboard for ingestion success rate, API error rate, dispute rate

---

## Appendix A — PUUID Lookup Query

```python
from apps.user_profile.models import ProviderAccount
from apps.tournaments.models import Registration

def get_riot_puuids_for_match(match: Match) -> tuple[list[str], list[str]]:
    """
    Returns (p1_puuids, p2_puuids) for a Match by resolving Registrations
    → Users → ProviderAccounts.
    """
    def puuids_for_participant(participant_id: int) -> list[str]:
        try:
            reg = Registration.objects.select_related("user", "team").get(
                pk=participant_id,
                tournament=match.tournament,
            )
        except Registration.DoesNotExist:
            return []

        if reg.team:
            user_ids = list(reg.team.members.values_list("user_id", flat=True))
        else:
            user_ids = [reg.user_id]

        return list(
            ProviderAccount.objects.filter(
                provider=ProviderAccount.Provider.RIOT,
                user_id__in=user_ids,
            ).values_list("provider_account_id", flat=True)
        )

    return (
        puuids_for_participant(match.participant1_id),
        puuids_for_participant(match.participant2_id),
    )
```

## Appendix B — Key Settings

```python
# settings.py additions

# Riot
RIOT_API_KEY = env("RIOT_API_KEY", default="")
RIOT_ACCOUNT_API_CLUSTERS = ["americas", "asia", "europe"]
RIOT_MATCH_POLL_MAX_PER_CYCLE = 20
RIOT_MATCH_GRACE_PERIOD_MINUTES = 15   # buffer after scheduled_time before polling

# Steam
STEAM_API_KEY = env("STEAM_API_KEY", default="")
STEAM_MATCH_POLL_MAX_PER_CYCLE = 10

# Integrity
MATCH_INTEGRITY_STRICT_GAMES = ["valorant"]
MATCH_INTEGRITY_RELAXED_GAMES = ["cs2", "dota2"]
```
