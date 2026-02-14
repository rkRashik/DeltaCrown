# Report 3: Delta Analysis — What Changed Since the Plan Was Written

**Date:** February 14, 2026  
**Purpose:** Everything that changed in the other apps between December 2025 and now, and how those changes affect the tournament redevelopment plan

---

## Executive Summary

Between December 2025 (when the tournament redesign plan was written) and February 2026 (now), you updated **6 major apps**: teams, user_profile, notifications, economy, organizations, and leaderboards. These changes introduced **significant shifts** that the original plan didn't anticipate. This report maps every change and its impact.

**The biggest surprises:**
1. Teams app is **FROZEN** — new development moved to `apps/organizations`
2. User profile game IDs (riot_id, steam_id, etc.) were **REMOVED** — replaced by `GameProfile` model
3. A full **leaderboards app** was built with ELO ratings, match history, and event-driven updates
4. Economy FKs to tournaments were **converted to IntegerFields**
5. The notification system was **significantly enhanced** with 30+ notification types

---

## Change-by-Change Breakdown

### 1. Teams App → FROZEN (Migrating to Organizations)

#### What Changed
| Before (Dec 2025) | Now (Feb 2026) |
|-------------------|----------------|
| `apps/teams` was active development | `apps/teams` is **FROZEN** with `LegacyWriteEnforcementMixin` |
| Team model was the primary team entity | `apps/organizations` has a new Team model |
| No game-specific team ranking | `TeamGameRanking` model added (ELO per game) |
| Original plan assumed `apps.teams.Team` FK usage | `UserProfile.primary_team` now points to `organizations.Team` |

#### Impact on Tournament Plan
| Original Plan Assumed | Reality Now | What You Need To Do |
|----------------------|-------------|---------------------|
| `Registration.team_id` → `teams.Team` | `teams.Team` is read-only | Decide: keep legacy IntegerField or FK to `organizations.Team` |
| `TeamAdapter` → `apps.teams.models` | Teams app has `LegacyWriteEnforcementMixin` | Update `TeamAdapter` to source from `apps/organizations` for new teams |
| `TeamMembership` role checks | Still work (legacy read allowed) | Must support both legacy and new org membership models |
| Tournament team registration | Teams can't be created/modified | New team registrations must use organizations app |

#### Severity: 🔴 HIGH
The `TeamAdapter` in `tournament_ops` currently imports from `apps.teams.models`. This still works for reads but any new team-related tournament features need to use `apps.organizations`.

---

### 2. User Profile — Game IDs Removed, GameProfile Introduced

#### What Changed
| Before (Dec 2025) | Now (Feb 2026) |
|-------------------|----------------|
| `UserProfile.riot_id`, `.steam_id`, `.pubg_mobile_id`, etc. | **All removed** (migration `0011`) |
| Hardcoded game ID fields on profile | `GameProfile` model — FK to `games.Game`, per-game identity storage |
| `profile.riot_id` used in registration auto-fill | Must use `GameProfile.objects.filter(user=user, game=game)` |
| `UserProfile.primary_team` → `teams.Team` | Now → `organizations.Team` |
| No career/matchmaking models | `CareerProfile`, `MatchmakingPreferences` added |
| Social links on UserProfile | Extracted to separate `SocialLink` model |

#### Impact on Tournament Plan
| Original Plan Assumed | Reality Now | What You Need To Do |
|----------------------|-------------|---------------------|
| `auto_filled['game_id'] = profile.riot_id` | `profile.riot_id` doesn't exist anymore | Use `GameProfile` or `GamePassportService` for player identity |
| `GamePlayerIdentityConfig.field_name` maps to UserProfile fields | Field names no longer exist on UserProfile | Map to `GameProfile.ign` / `GameProfile.discriminator` instead |
| Registration wizard auto-fill from profile fields | Old auto-fill code will crash | Rewrite auto-fill to query `GameProfile` model |
| `UserProfile` had game-specific stats | Stats now in separate `UserProfileStats` model | Use `UserProfileStats` (event-driven, recomputed from `UserActivity`) |

#### Severity: 🔴 HIGH
This is a **breaking change** for the registration wizard. The current `registration_wizard.py` code that does `profile.riot_id` will throw `AttributeError` in production. The auto-fill service needs a complete rewrite.

---

### 3. Economy App — FK Cleanup

#### What Changed
| Before (Dec 2025) | Now (Feb 2026) |
|-------------------|----------------|
| `DeltaCrownTransaction.tournament` was FK to Tournament | Now `tournament_id = IntegerField` |
| `DeltaCrownTransaction.registration` was FK | Now `registration_id = IntegerField` |
| `DeltaCrownTransaction.match` was FK | Now `match_id = IntegerField` |
| `CoinPolicy.tournament` was FK | Now `tournament_id = IntegerField` |
| `award()` function used tournament FK | `award()` now deprecated, use `credit()`/`debit()` |

#### Impact on Tournament Plan
| Original Plan Assumed | Reality Now | What You Need To Do |
|----------------------|-------------|---------------------|
| Economy adapter would use `credit()` / `debit()` | ✅ Correct — API hasn't changed | Wire `EconomyAdapter.charge()` to `economy.services.debit()` |
| `award()` for tournament prizes | Deprecated — use `credit()` with proper reason | Replace any `award()` calls with `credit()` |
| FK-based transaction queries | Must use `filter(tournament_id=id)` not `filter(tournament=obj)` | Update queries in any reporting/admin views |

#### Severity: 🟡 MEDIUM
The core API (`credit`/`debit`/`transfer`/`get_balance`) is unchanged. The FK → IntegerField change mainly affects admin/reporting queries. The `EconomyAdapter` stub needs to be implemented using these exact functions.

---

### 4. Notifications App — Enhanced & Matured

#### What Changed
| Before (Dec 2025) | Now (Feb 2026) |
|-------------------|----------------|
| Basic notification model | 30+ notification types (REG_CONFIRMED, BRACKET_READY, MATCH_SCHEDULED, etc.) |
| Simple `notify()` | Enhanced with `category`, `bypass_user_prefs`, `dedupe`, `fingerprint`, email support |
| No preference system | `NotificationPreference` model with per-type channel control |
| No webhook support | `WebhookService` with HMAC signing, retries, circuit breaker |
| Tournament FK on notifications | `tournament_id = IntegerField` (same FK cleanup) |
| Signal-based auto-notifications | `subscribers.py` auto-creates notifications on Registration/Match post_save |

#### Impact on Tournament Plan
| Original Plan Assumed | Reality Now | What You Need To Do |
|----------------------|-------------|---------------------|
| `NotificationAdapter` would send notifications | Adapter is currently a no-op | Wire to `notifications.services.notify()` |
| Custom notification types needed | 30+ types already defined | Use existing `Notification.Type` choices |
| Category enforcement | Phase 5B enforcement exists | Pass `category` param in notify calls |
| Tournament FK queries | Use `tournament_id=<int>` | Already IntegerField |

#### Severity: 🟡 MEDIUM
The notification system is more capable than the plan anticipated. The `NotificationAdapter` just needs to call `notify()` with the right type and payload — the infrastructure is all there.

---

### 5. Leaderboards App — Fully Built (New)

#### What Changed
| Before (Dec 2025) | Now (Feb 2026) |
|-------------------|----------------|
| No dedicated leaderboards app | Full app with 6 models, V2 ranking engine |
| Stats lived in tournaments services | `UserStats`, `TeamStats`, `TeamRanking` models per game |
| No match history records | `UserMatchHistory` model with full match details |
| No ELO system | `TeamRanking.elo_rating` with peak tracking |
| No event-driven updates | `@event_handler("match.completed")` auto-updates everything |

#### Impact on Tournament Plan
| Original Plan Assumed | Reality Now | What You Need To Do |
|----------------------|-------------|---------------------|
| TournamentOps would own stats services | Leaderboards app handles stats via events | Publish `MatchCompletedEvent` — leaderboards does the rest |
| `UserStatsService` / `TeamStatsService` in tournament_ops | These exist but are parallel to leaderboards | Decide: use tournament_ops services OR leaderboards event handlers |
| Manual stats update calls | Event-driven auto-updates | Just emit events; don't manually call stats services |

#### Severity: 🟢 LOW (Actually Good News)
The leaderboards app does what Phase 8 of the original plan intended — automatically updating stats when matches complete. The tournament apps just need to publish the right events.

---

### 6. Organizations App — New Team System

#### What Changed
| Before (Dec 2025) | Now (Feb 2026) |
|-------------------|----------------|
| Only `apps/teams` existed | `apps/organizations` is the new team management app |
| No concept of organizations | Full org system with teams, members, roles, invites |
| Team → Tournament was via `team_id` IntegerField | Same pattern likely continues |

#### Impact on Tournament Plan
| Original Plan Assumed | Reality Now | What You Need To Do |
|----------------------|-------------|---------------------|
| Teams = `apps.teams.Team` | New teams = `apps.organizations.Team` | `TeamAdapter` needs dual-source support |
| Team membership checks against `TeamMembership` | New membership model in organizations | Update permission checks |
| Team capabilities/roles | New role system in organizations | Align tournament registration permissions |

#### Severity: 🔴 HIGH
Any new team-tournament integration must work with `apps/organizations`. But legacy tournament data still references `teams.Team` IDs. You need a strategy for both.

---

### 7. Event Bus — Working But Minimal

#### What Changed
| Before (Dec 2025) | Now (Feb 2026) |
|-------------------|----------------|
| Event bus designed but not tested | Working in-memory pub/sub with `EventLog` persistence |
| No consumers | `leaderboards/event_handlers.py` consumes `match.completed` |
| Celery integration planned | Still synchronous (TODO) |

#### Impact on Tournament Plan
| Original Plan Assumed | Reality Now | What You Need To Do |
|----------------------|-------------|---------------------|
| Async event processing via Celery | Still synchronous | For now, events process inline |
| `MatchCompletedEvent` would trigger cascading updates | Leaderboards handler already listens | Publish events and cascading happens |

#### Severity: 🟢 LOW
The event bus works for the current scale. Celery integration can be added later without changing the publishing code.

---

## Summary: The 7 Things That Changed Everything

| # | Change | Original Assumption | New Reality | Impact Level |
|---|--------|-------------------|-------------|-------------|
| 1 | Teams → Frozen | `apps.teams.Team` is active | It's read-only, new teams in `organizations` | 🔴 HIGH |
| 2 | Game IDs removed from UserProfile | `profile.riot_id` works | Doesn't exist, use `GameProfile` | 🔴 HIGH |
| 3 | Organizations app exists | N/A | New team system for all new features | 🔴 HIGH |
| 4 | Leaderboards app built | TournamentOps would handle stats | Event-driven stats already working | 🟢 GOOD |
| 5 | Notification system enhanced | Basic notifications | 30+ types, webhooks, preferences | 🟡 MEDIUM |
| 6 | Economy FKs → IntegerFields | FK-based queries | Integer-based queries | 🟡 MEDIUM |
| 7 | Event bus is live | Planned infrastructure | Working with one consumer already | 🟢 GOOD |

---

## What the Original Plan Documents Are Still Good For

Despite these changes, the original documents remain valuable:

| Document | Still Useful? | Why |
|----------|-------------|-----|
| `TOURNAMENT_CURRENT_IMPLEMENTATION_AUDIT.md` | ✅ Yes | Model and service inventory is still accurate |
| `CROSS_APP_INTEGRATION_AUDIT.md` | ⚠️ Partially | Integration patterns identified are still valid; specific code references may be stale |
| `REGISTRATION_BACKEND_MODELS_PART_1.md` | ⚠️ Partially | Registration model structure is unchanged; auto-fill section is outdated |
| `REGISTRATION_CROSS_APP_FLOW_PART_2.md` | ⚠️ Partially | Flow is correct; UserProfile field references are broken |
| `REGISTRATION_FRONTEND_UI_PART_3.md` | ✅ Yes | Template structure still matches reality |
| `REGISTRATION_ENDPOINTS_PART_4.md` | ✅ Yes | URL patterns and view contracts haven't changed |
| `TOURNAMENT_LIFECYCLE_PART_5.md` | ✅ Yes | Lifecycle stages and gaps are still relevant |
| `SMART_REGISTRATION_PART_6.md` | ✅ Yes | Architecture recommendations are still sound |
| `TOURNAMENT_OPS_DESIGN.md` | ⚠️ Partially | Service design is good; adapter targets need updating |
| `Workplan/ARCH_PLAN_PART_1.md` | ✅ Yes | Architecture vision is unchanged |
| `Workplan/LIFECYCLE_GAPS_PART_2.md` | ✅ Yes | Gap analysis is still accurate |
| `Workplan/SMART_REG_AND_RULES_PART_3.md` | ⚠️ Partially | Game rules section is good; profile field mapping is outdated |
| `Workplan/ROADMAP_AND_EPICS_PART_4.md` | ⚠️ Partially | Phase structure is good; specific tasks need updating |
| `Workplan/DEV_PROGRESS_TRACKER.md` | ✅ Reference | Historical record of what was done |
