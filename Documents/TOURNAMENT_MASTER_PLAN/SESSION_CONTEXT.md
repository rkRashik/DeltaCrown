# Session Context — For AI Continuity

*This file exists so that when we start a new conversation, the AI can quickly understand where we are, what's been decided, and what to do next.*

*Updated: February 14, 2026*

---

## Project Identity
- **Project:** DeltaCrown — Esports Tournament Platform
- **Stack:** Django 5.2.8, Python 3.12, PostgreSQL (Neon), Tailwind CSS, Celery/Redis
- **Workspace:** `g:\My Projects\WORK\DeltaCrown`

## What We're Doing
Rebuilding the tournament system (`apps/tournaments` + `apps/tournament_ops`) — removing legacy code, wiring adapters, consolidating services, creating clean views/templates, and implementing the full tournament lifecycle.

## Key Architecture Decisions
1. **Two-app split:** `tournaments` = data/models/views, `tournament_ops` = logic/services/adapters
2. **All cross-app communication through adapters** — never import models from other apps directly (exception: tournaments views can import tournament models)
3. **Event-driven for stats/notifications** — publish events, let leaderboards/notifications react
4. **FK → IntegerField** for all team references (teams app is frozen)
5. **Game identity via GameProfile** — no hardcoded riot_id/steam_id
6. **Phase 7 staff system** — capability-based, not boolean-flags
7. **DisputeRecord** — the canonical dispute model (not the old Dispute in match.py)

## Plan Documents
All in `Documents/TOURNAMENT_MASTER_PLAN/`:
- `00_THE_VISION.md` — Narrative vision of the complete system
- `01_EXECUTION_ROADMAP.md` — 7-phase execution plan with tasks
- `TRACKER.md` — Master progress tracker (update every session)
- `QUICK_REFERENCE.md` — Model/service/adapter/URL map
- `STABLE_APPS_CONTRACT.md` — What we can call from other apps
- `CLEANUP_INVENTORY.md` — Everything that needs to be deleted/fixed
- `SESSION_CONTEXT.md` — This file

## Previous Audit Documents
In `Documents/Tournament_Redevelopment_Audit_Feb2026/`:
- `01_CURRENT_STATE_AUDIT.md` — Feb 14 audit of both apps
- `02_ORIGINAL_PLAN_SUMMARY.md` — Original 10-phase plan summary
- `03_DELTA_ANALYSIS.md` — What changed since Dec 2025
- `04_EXECUTION_PLAN.md` — Earlier execution plan (superseded by TOURNAMENT_MASTER_PLAN)
- `05_RISKS_AND_DEPENDENCIES.md` — Risk analysis

## Stable Apps (Do Not Modify)
- `apps/games` — 7 models, GameService, GameRulesEngine, GameValidationService
- `apps/organizations` — Team, TeamMembership, TeamService, TeamAdapter
- `apps/economy` — DeltaCrownWallet, DeltaCrownTransaction, wallet_for(), award()
- `apps/notifications` — Notification, notify(), WebhookService
- `apps/leaderboards` — UserStats, TeamStats, event handler for match.completed
- `apps/user_profile` — UserProfile, GameProfile, GamePassportService
- `common/events` — EventBus, Event, @event_handler

## Current Phase
**Phase 0: Cleanup** — Not started yet.

## What To Do Next
Start Phase 0 by reading `CLEANUP_INVENTORY.md` and working through the items in order:
1. Remove legacy Game model from tournaments
2. Remove riot_id/steam_id references
3. Remove backup files
4. Consolidate duplicate services
5. Consolidate duplicate models
6. Fix cross-app FK violations
7. Fix adapter bugs

## Important Warnings
- The registration wizard WILL CRASH if tested — it references profile.riot_id which no longer exists
- The EconomyAdapter returns fake data — any payment operation silently succeeds without actually charging
- The NotificationAdapter is no-op — notifications through tournament_ops go nowhere
- Swiss bracket generator only works for Round 1 — Round 2+ are stubbed
- TournamentOpsService is 3,031 lines — don't add more methods to it, split instead
