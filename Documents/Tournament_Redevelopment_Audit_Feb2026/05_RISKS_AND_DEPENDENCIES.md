# Report 5: Risks, Dependencies & Migration Concerns

**Date:** February 14, 2026  
**Purpose:** Everything that could go wrong during the tournament redevelopment, and how to prevent it

---

## Risk Category 1: Breaking Changes (Severity: HIGH)

### Risk 1.1 — Registration Auto-Fill Field Crash
**What:** All hardcoded `profile.riot_id`, `profile.steam_id`, etc. references in the registration wizard will raise `AttributeError` because those fields were removed from UserProfile in migration 0011.

**Impact:** Registration completely broken for any tournament.

**Mitigation:**
- This must be fixed in **Wave 0** before any other work
- Replace with `GameProfile` queries
- Test by registering for a tournament of each game type

**Detection:** Any template or view referencing `profile.riot_id`, `profile.steam_id`, `profile.epic_id`, `profile.activision_id`, `profile.ea_id`

---

### Risk 1.2 — EconomyAdapter Silently Succeeds
**What:** The EconomyAdapter returns hardcoded success for every payment operation. If you wire up registration fees through tournament_ops before fixing the adapter, users will be "charged" without actually paying.

**Impact:** Revenue loss; data integrity issues; registrations confirmed without payment.

**Mitigation:**
- Fix in **Wave 0**, item 0.2
- Add assertion/logging to catch any adapter method still returning hardcoded values
- Create a test: call `charge()`, then `get_balance()` and verify the amount decreased

---

### Risk 1.3 — Notification Silence
**What:** The NotificationAdapter is no-op. Users won't receive any tournament notifications through tournament_ops flows.

**Impact:** Bad UX; users miss match schedules, result deadlines, bracket updates.

**Mitigation:**
- Fix in **Wave 0**, item 0.3
- Test each notification type by triggering the corresponding tournament_ops action

---

## Risk Category 2: Data Integrity (Severity: HIGH)

### Risk 2.1 — team_id Orphaning
**What:** Registration records store `team_id` as an `IntegerField` (not FK). If the referenced team is in `apps.teams` but the adapter is reading from `apps.organizations`, lookups will return no results.

**Impact:** Registered teams appear as "unknown" in brackets and match pages.

**Mitigation:**
- Use dual-source `TeamAdapter` (try organizations, fall back to legacy teams)
- Add a data validation script: for all Registration records with a `team_id`, verify the team exists in at least one of the two team tables
- Do NOT delete legacy team records until you've verified all references

### Risk 2.2 — Match Result → Stats Pipeline Integrity
**What:** When a match completes, the leaderboards app listens for `match.completed` events. If tournament_ops processes a match result but doesn't publish the event, stats won't update. If it publishes twice, stats will be doubled.

**Impact:** Incorrect leaderboard rankings; player stats drift.

**Mitigation:**
- Ensure event publishing happens exactly once per match completion
- Use idempotency keys on the event (match_id + result_hash)
- Verify: the `EventLog` should have exactly one entry per match completion

### Risk 2.3 — Swiss Bracket Incompleteness
**What:** The Swiss bracket generator only completes Round 1. Rounds 2+ are stubbed with `pass`.

**Impact:** Any Swiss-format tournament will get stuck after Round 1.

**Mitigation:**
- If you plan to support Swiss format: implement Rounds 2+ in Wave 2
- If you don't need Swiss yet: disable it in the tournament creation form
- Add a guard: Tournament creation with `format=swiss` should show a warning or be blocked until implemented

---

## Risk Category 3: Architectural Risks (Severity: MEDIUM)

### Risk 3.1 — TournamentOpsService God Object
**What:** The facade service is 3,031 lines with 60 methods. Adding more methods during the rewire will make it worse.

**Impact:** Difficult to test; hard to find bugs; merge conflicts when multiple features touch the same file.

**Mitigation:**
- Do NOT add new methods to the facade during the rewire
- Instead, call the domain services directly from views (e.g., `RegistrationService`, `MatchService`)
- The facade is useful for cross-cutting orchestration, but not every action needs it
- Consider splitting into sub-facades per domain (registration_facade, match_facade)

### Risk 3.2 — Dual Service Problem
**What:** After Wave 2 rewiring, some views will use tournament_ops services and others will still use old tournament services. If both paths modify the same data without coordination, you'll get race conditions and inconsistent state.

**Impact:** Registration confirmed through old path doesn't trigger ops events; match completed through new path doesn't run old signals.

**Mitigation:**
- Track which views have been rewired
- Use a feature flag or environment variable: `USE_OPS_SERVICE = True/False`
- During transition, have the old services emit events too (belt and suspenders)
- Never have both paths active for the same action

### Risk 3.3 — Dual Dispute Systems
**What:** Phase 6 added `DisputeRecord` model in tournaments. Phase 7/tournament_ops also has a `DisputeService`. They don't connect.

**Impact:** Disputes filed through one system won't appear in the other.

**Mitigation:**
- Pick ONE dispute system (recommendation: tournament_ops `DisputeService` backed by the `DisputeRecord` model)
- Make sure the dispute adapter writes to `DisputeRecord` as the single source of truth
- Remove or deprecate any parallel dispute handling code

### Risk 3.4 — Dual Staffing Systems
**What:** Phase 7 added staffing models (`StaffRole`, `TournamentStaffAssignment`, `MatchRefereeAssignment`). Tournament_ops also has a `StaffingService`. Again, they might not connect.

**Impact:** Staff assigned through one system invisible to the other.

**Mitigation:**
- The tournament_ops `StaffingService` should use the Phase 7 models via an adapter
- Verify: Does `StaffingAdapter` write to `TournamentStaffAssignment`?

---

## Risk Category 4: User Experience (Severity: MEDIUM)

### Risk 4.1 — Template Confusion
**What:** Multiple template variants exist (`solo_step1.html`, `solo_step1_new.html`, `solo_step1_enhanced.html`). It's unclear which is active.

**Impact:** Developers modify the wrong template; users see outdated UI.

**Mitigation:**
- Before starting Wave 3, map every URL pattern to its actual template
- Create a template manifest: "This URL renders this template"
- Archive old variants immediately

### Risk 4.2 — Hardcoded Game Colors Breaking
**What:** Multiple templates have `{% if game_spec.slug == 'valorant' %}` blocks for game-specific styling. If a new game is added without updating every template, it gets no styling.

**Impact:** New games look unstyled/broken; adding a game requires touching 10+ templates.

**Mitigation:**
- Wave 5 replaces hardcoded colors with `Game.primary_color` from the database
- Until then, new games need manual template updates

### Risk 4.3 — Registration Wizard State Loss
**What:** Current wizard uses sessions for state. If the server restarts or times out, users lose progress.

**Impact:** Users abandon registration; partial data in weird states.

**Mitigation:**
- Smart Registration (Wave 3) fixes this with persistent `RegistrationDraft`
- Until Wave 3 is complete, this risk remains

---

## Risk Category 5: Operational Risks (Severity: MEDIUM)

### Risk 5.1 — Celery Tasks Not Scheduled
**What:** Three tournament_ops tasks exist but are NOT in `CELERY_BEAT_SCHEDULE`:
- `opponent_response_reminder_task`
- `dispute_escalation_task`
- `auto_confirm_submission_task`

**Impact:** Opponents never get reminded to verify results; disputes never auto-escalate; submissions never auto-confirm.

**Mitigation:**
- Add to `deltacrown/celery.py` beat schedule
- Set reasonable intervals (e.g., reminder every 1h, escalation check every 4h, auto-confirm after 24h)

### Risk 5.2 — Event Bus Is Synchronous
**What:** The `common/events` EventBus is in-memory and synchronous. If an event handler is slow, it blocks the HTTP request.

**Impact:** Slow tournament pages when events have expensive handlers (stats recalculation, notification sending).

**Mitigation:**
- For now, keep event handlers fast (queue expensive work to Celery)
- Plan: Migrate to async event bus (Celery tasks or Redis pubsub) after MVP
- Monitor: Add timing logs to event handlers

### Risk 5.3 — No Migration Plan for Live Data
**What:** If you change model fields or relationships, existing tournament data might become inconsistent.

**Impact:** Active tournaments could break mid-event.

**Mitigation:**
- The current plan does NOT add/remove model fields (Wave 0–2 are adapter/service/view changes only)
- If you DO need model changes in later waves, always:
  1. Add new field with `null=True, default=...`
  2. Backfill data
  3. Make field required only after backfill

---

## Dependency Chain

This shows what blocks what:

```
Nothing depends on ← Wave 0 (Critical Fixes)
  ↓
Wave 0 ← Wave 1 (Adapter Alignment)
  ↓
Wave 1 ← Wave 2 (Service Wiring)
  ↓
Wave 2 ← Wave 3 (Smart Registration)  [also depends on Wave 1]
  ↓
Wave 2 ← Wave 4 (Organizer Console)   [also depends on Wave 1]
  ↓
Wave 3 + Wave 4 ← Wave 5 (Frontend Polish)
  ↓
All Waves ← Wave 6 (Testing)  [can start in parallel from Wave 1]
```

### External Dependencies (Outside Your Control)

| Dependency | Status | Risk |
|---|---|---|
| `apps/games` data | ✅ Stable | None — 7 models, tested, game data seeded |
| `apps/organizations` models | ✅ Exists | Low — may still evolve, but core Team model is stable |
| `apps/economy` services | ✅ Exists | Low — `credit()`/`debit()`/`get_balance()` API stable |
| `apps/notifications` `notify()` | ✅ Exists | None — well-tested, 30+ types |
| `apps/leaderboards` event handler | ✅ Working | Low — single consumer for `match.completed` |
| `apps/user_profile` GameProfile | ✅ Exists | Low — model stable, new fields possible but backward-compatible |
| PostgreSQL (Neon) | ✅ Production | None |
| Celery/Redis | ✅ Configured | None |
| Django 5.2.8 | ✅ Stable | None for this work |

### Internal Dependencies (Within Tournament Apps)

| Component | Depends On | Risk Level |
|---|---|---|
| Registration views | UserAdapter, TeamAdapter, GameAdapter, EconomyAdapter | HIGH until adapters fixed |
| Match result views | MatchAdapter, Event bus | MEDIUM |
| Bracket generation | BracketEngineService, TournamentAdapter | LOW (works) |
| Organizer console | All adapters, all ops services | HIGH (last to build) |
| Tournament creation | GameAdapter, EconomyAdapter | MEDIUM |
| Dispute handling | DisputeService, NotificationAdapter | MEDIUM |
| Stats display | LeaderboardAdapter or event bus | LOW (exists) |

---

## Pre-Flight Checklist

Before you start coding, verify these:

- [ ] Can you run `manage.py test apps.tournaments` without errors?
- [ ] Can you run `manage.py test apps.tournament_ops` without errors?
- [ ] Does the registration wizard load at all? (Or does it crash from missing fields?)
- [ ] Is `GameProfile` data seeded for at least one test user?
- [ ] Is the `organizations.Team` model populated with test data?
- [ ] Is the event bus handler for `match.completed` active?
- [ ] Are the Celery workers running in your dev environment?

---

## Summary of All 5 Reports

| Report | File | What It Covers |
|---|---|---|
| 1 | `01_CURRENT_STATE_AUDIT.md` | What exists right now in both apps — models, services, views, gaps |
| 2 | `02_ORIGINAL_PLAN_SUMMARY.md` | The 10-phase plan from Dec 2025 and what was actually built |
| 3 | `03_DELTA_ANALYSIS.md` | 7 major changes in other apps that affect the plan |
| 4 | `04_EXECUTION_PLAN.md` | The updated execution plan: 6 waves, 8-11 weeks |
| 5 | `05_RISKS_AND_DEPENDENCIES.md` | This file — everything that could go wrong and how to prevent it |

**Start with Wave 0. It's 2-3 days of work that fixes active bugs.**
