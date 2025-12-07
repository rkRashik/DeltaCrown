# DeltaCrown Workplan Recap

**Created**: December 8, 2025  
**Purpose**: High-level summary of the 5-part workplan and current legacy state

---

## Workplan Summary (Parts 1-5)

### Architecture Vision (Part 1)
DeltaCrown is a multi-game esports platform supporting **11 games** (Valorant, PUBG, CS2, MLBB, etc.) with **7 core domain areas**: Games (config layer), Teams (roster management), Tournaments (core logic), TournamentOps (orchestration), Economy (DeltaCoin), User/Profile (identity), and Leaderboards (stats/rankings). The vision emphasizes **service boundaries**, **DTOs for cross-domain communication**, **adapter layers** for external integrations, and an **event bus** for decoupled domain events. Key principles: configuration over code (game rules in DB), domain-driven design, progressive enhancement (HTML-first, JS-enhanced UI), and no direct cross-domain model imports.

### Tournament Lifecycle & Gaps (Part 2)
Documents the **6-stage tournament lifecycle**: Discovery & Browsing → Registration & Payment → Bracket & Seeding → Match Operations → Tournament Completion → Post-Tournament Stats. Identified **300+ missing features** including: countdown timers, featured tournament badges, advanced filters (region, price range), registration draft auto-save, game identity verification (Riot API, Steam API), multi-stage tournaments (groups → playoffs), bracket editing (drag-drop seeding), result dispute resolution, organizer results inbox, manual match scheduling, payout automation, and comprehensive stats/leaderboards. Current state has basic listing, registration, and bracket generation but lacks orchestration, verification pipelines, and organizer tooling.

### Game Rules & Smart Registration (Part 3)
Defines a **database-driven game configuration system** to eliminate hardcoded game logic. New models: `GamePlayerIdentityConfig` (identity fields per game), `GameTournamentConfig` (formats, scoring), `GameScoringRule` (points calculation), `GameMatchResultSchema` (result structure). **Smart Registration** includes: 5-step wizard (Team Selection → Identity/Game Accounts → Tournament Questions → Documents → Payment), auto-fill from verified profiles, locked verified fields, real-time validation (game ID format checks), conditional questions (show rank field only if tournament requires it), draft persistence with auto-save, and document upload requirements. Supports **6-step result input pipeline**: Player submits → Opponent confirms/disputes → Organizer reviews → Resolution → Match advances → Stats updated.

### Development Roadmap (Part 4)
**10-phase roadmap spanning 48 weeks (12 months)**: Phase 1 (Weeks 1-4): Architecture Foundations (service adapters, event bus, DTOs). Phase 2 (Weeks 5-7): Game Rules & Configuration (config models, rules engine, schema validation). Phase 3 (Weeks 8-12): Universal Tournament Format Engine (bracket generators for SE/DE/RR/Swiss, group stage editor, stage transitions). Phase 4 (Weeks 13-16): TournamentOps Core Workflows (registration orchestration, result verification). Phase 5 (Weeks 17-21): Smart Registration System (draft persistence, auto-fill, conditional fields). Phase 6 (Weeks 22-25): Result Pipeline & Dispute Resolution. Phase 7 (Weeks 26-30): Organizer Console (results inbox, dispute handling, staff roles, audit log). Phase 8 (Weeks 31-36): Event-Driven Stats & History. Phase 9 (Weeks 37-40): Frontend Developer Support (API docs, JSON schemas). Phase 10 (Weeks 41-48): Advanced Features (notifications, Discord bot, achievements, mobile app).

### Frontend Specification (Part 5)
**Tech stack**: Django templates (server-rendered), Tailwind CSS, Vanilla JS + progressive enhancement (optional HTMX/Alpine.js). **16 screens documented**: 8 player-facing (Discover Tournaments, Tournament Detail, Registration Wizard, My Tournaments, Match Details, Dispute Form, Profile), 8 organizer (Dashboard, Registration Management, Bracket & Groups Management, Match Operations, Results Inbox, Dispute Handling, Settings, Payouts). **20+ reusable components** defined: layout (navbar, sidebar, modal, card), forms (text input, select, file upload, game identity field, team roster editor), tournament (tournament card, match card, group standings table, bracket view), organizer (filter bar, sortable table, result inbox item, audit log entry). **7 JSON data contracts** provided. **3 detailed user flows**: Smart Registration (5-step wizard with auto-fill and validation), Match Result Submission (player submit → opponent confirm/dispute → organizer resolve), Organizer Bracket & Group Management (create groups, drag-drop editing, stage transitions). **9-phase implementation checklist** with 150+ tasks.

---

## Current Legacy Areas & Testing Situation (High-Level)

### Legacy / Messy Code Areas

**1. Game Configuration (Hardcoded Logic)**
- **Location**: `apps/tournaments/models/tournament.py` - `Game` model embedded in tournaments app
- **Issue**: Game definitions live in tournaments instead of dedicated Games app
- **Evidence**: `Game.profile_id_field` (hardcoded field names like 'riot_id', 'steam_id')
- **Impact**: Adding new games requires code changes; no dynamic configuration

**2. Direct Cross-Domain Model Imports**
- **Location**: Scattered across `apps/user_profile/`, `apps/teams/`, `apps/tournaments/`
- **Evidence**: `from apps.tournaments.models import Registration` in user_profile, `from apps.teams.models import TeamMembership` in multiple apps
- **Issue**: Violates service boundary principle (20+ instances found)
- **Impact**: Tight coupling between domains; circular dependencies risk

**3. Scoring Logic (Likely Hardcoded)**
- **Location**: Suspected in `apps/tournaments/models/result.py`, `apps/tournaments/services/`
- **Evidence**: `TournamentResult` model exists but no dynamic scoring rules
- **Issue**: Game-specific scoring (K/D for FPS, goals for FIFA) likely in if-else chains
- **Impact**: Cannot support new game scoring without code deployment

**4. Registration Flow (No Orchestration)**
- **Location**: `apps/tournaments/models/registration.py` - `Registration`, `Payment` models exist
- **Evidence**: No TournamentOps service layer; likely direct model manipulation in views
- **Issue**: Registration logic scattered in views/forms instead of service layer
- **Impact**: No draft persistence, no auto-fill, no verification pipeline

**5. Bracket Generation (Limited Formats)**
- **Location**: `apps/tournaments/models/bracket.py` - `Bracket`, `BracketNode` models exist
- **Evidence**: Existing bracket models but no pluggable format generators
- **Issue**: Likely supports only single/double elimination; no Swiss, no group stages
- **Impact**: Cannot run multi-stage tournaments (groups → playoffs)

**6. Result Input (No Dispute Pipeline)**
- **Location**: `apps/tournaments/models/match.py` - `Match`, `Dispute` models exist
- **Evidence**: Models exist but no orchestration service
- **Issue**: No opponent confirmation workflow, no organizer results inbox
- **Impact**: Manual result verification requires direct DB edits

**7. Admin/Organizer UI (Likely Minimal)**
- **Location**: Django admin customizations in `apps/tournaments/admin*.py` files
- **Evidence**: Multiple admin files (admin_bracket.py, admin_match.py, etc.)
- **Issue**: Organizer workflows likely use default Django admin (not custom console)
- **Impact**: Poor UX for tournament organizers; no guided workflows

**8. Old Backup Code**
- **Location**: `apps/tournaments/views_old_backup.py`
- **Evidence**: Backup file with old view logic
- **Issue**: Dead code or deprecated patterns still in codebase
- **Impact**: Code clutter; unclear which patterns are current

---

### Testing Situation

**Test Files Exist**: ✅ **213 test files** found (comprehensive test coverage)

**Test Organization**:
- Root-level test files: `test_team_fixes.py`, `test_team_create_fix.py`, `test_team_autofill.py` (likely ad-hoc bug fixes)
- Structured tests: `tests/` directory with modular organization (test_api_*, test_analytics_*, test_certificate_*, test_bracket_*)
- Domain-specific tests: `tests/leaderboards/` subdirectory (test_leaderboard_contract.py, test_leaderboards_service.py)

**Test Infrastructure**:
- **Framework**: pytest (pytest.ini configured with `DJANGO_SETTINGS_MODULE = deltacrown.settings_test`)
- **Test DB Strategy**: `--reuse-db -q` (reuse database for speed)
- **Test Markers**: Custom markers for S3 tests, observability, smoke tests, ops/DR tests
- **Async Support**: pytest-asyncio installed (for WebSocket tests)

**Test Coverage Levels** (inferred):
- **Service Layer Tests**: Likely exists (test_analytics_service_module_5_4.py, test_certificate_service_module_5_3.py, test_dashboard_service.py)
- **API Tests**: Likely exists (test_api_polish_module_4_6.py, test_bracket_api_module_4_1.py, test_certificate_api_module_5_3.py)
- **Model Tests**: Likely exists (test_certificate_model_module_5_3.py)
- **Integration Tests**: Exists (test_core_infrastructure.py, test_echo_wiring.py)
- **E2E/Smoke Tests**: Planned (marker exists but unclear if tests implemented)

**Testing Gaps** (suspected):
- No clear test coverage for cross-domain service boundaries (TournamentOps → Teams, TournamentOps → Games)
- Uncertain if registration flow has end-to-end tests (draft → auto-fill → verification → payment)
- No evidence of bracket generation tests for multi-stage tournaments (groups → playoffs)
- Result dispute pipeline tests unclear (player submit → opponent dispute → organizer resolve)

**Test Quality Indicators**:
- ✅ Modular test organization (by module/feature: analytics, certificates, brackets, leaderboards)
- ✅ Test infrastructure configured (pytest.ini, markers, async support)
- ⚠️ Some ad-hoc test files at root level (test_team_fixes.py) suggest reactive bug fixing
- ⚠️ Unclear test coverage % (no coverage report referenced)

---

## Key Takeaways

**Strengths**:
- Existing models for core domains (Tournament, Match, Bracket, Registration, Payment, Dispute)
- Comprehensive test infrastructure (pytest, 213 test files, async support)
- Some service layer separation exists (analytics_service, certificate_service, dashboard_service)

**Major Refactoring Needed**:
1. **Extract Games domain** from tournaments app → Create dedicated Games app with config models
2. **Remove direct model imports** → Implement service adapters + DTOs (20+ violations to fix)
3. **Build TournamentOps orchestration layer** → Registration workflow, result verification, dispute resolution
4. **Implement pluggable bracket generators** → Support Swiss, Round Robin, multi-stage tournaments
5. **Create Organizer Console UI** → Results inbox, dispute handling, bracket editing (not just Django admin)
6. **Add smart registration features** → Draft persistence, auto-fill, conditional fields, real-time validation
7. **Build event-driven stats pipeline** → Match completion events → Update user/team stats automatically

**Migration Path**: Follow 10-phase roadmap starting with Phase 1 (Architecture Foundations) to establish service boundaries, adapters, and DTOs before tackling domain-specific features. Incrementally refactor legacy patterns while maintaining existing functionality (strangler fig pattern).

---

**End of Recap**
