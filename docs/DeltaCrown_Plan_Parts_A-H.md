# DeltaCrown — Registration, Teams & Tournaments Plan (Parts A–H)

**Date:** September 06, 2025  
**Scope:** Implement end-to-end esports-ready flows for registration, payments, teams, rosters, public pages, admin ops, and UX polish across `game_efootball`, `game_valorant`, `teams`, and `tournaments` apps.

---

## Executive Summary
We will deliver a professional tournament platform experience:
- Seamless **registration** with **auto-prefill** from profile and **auto-use of active team** by game.
- **Payments** with mandatory fields when fee > 0, admin bulk actions (email pending payers, bulk-verify).
- **Teams** with one active team per game, team media (banner GIF, roster poster), public team pages, captain-only management, presets for fast registration, and strict roster rules (Valorant 5–7, eFootball Duo = 2).
- **Participants & Schedule** rendering after registration closes; optional **Groups** rendering from bracket JSON (then upgradable to models).
- **My Matches** page with filters.
- **Security & privacy** for profiles; unique constraints for email/username and team name/tag per game.
- **Robust tests** covering rules, flows, and rendering.

---

## Part A — “My Teams by Game” + Auto-use Team on Registration
**Goal:** One active team per game and zero-friction registration.

**Key Changes**
- Profile shows “**My Teams by Game**” (cards for eFootball + Valorant).
- Registration auto-binds to **active team for the game**, no long dropdowns.
- If user has no team, inline **Create Team** (game preselected).

**Rules**
- **One ACTIVE team per game** enforced at `TeamMembership.clean()`.
- Helper: `get_active_team(profile, game)`.

**Success**
- Visiting eFootball/Valorant registration uses the user’s **active team** and shows a roster preview.

---

## Part B (Revised) — Team Presets + Media (Pro-ready) & Profile Hooks
**Goal:** Speed-up registration; upgrade team media quality.

**Team Media (Team model)**
- `banner_image` (GIF allowed), `roster_image`, `logo`, `region`, socials (`twitter`, `instagram`, `discord`, `youtube`, `twitch`, `linktree` optional), `slug` (unique per game).

**Presets (Teams app)**
- `EfootballTeamPreset` (captain + mate snapshot).
- `ValorantTeamPreset` + `ValorantPlayerPreset` (up to 7 players with role).

**Registration Integration**
- “**Save as my [Game] Team**” checkbox persists preset.
- Prefill order: **Active Team → Preset → Profile → Empty**.

**Profile Hooks**
- “**My Team Presets**” list with CRUD for both games.

**Tests**
- Preset CRUD, media validations, prefill correctness.

---

## Part C (Revised) — Team Management (Captain) & Public Team Pages
**Goal:** Pro team pages and captain console.

**Public Page** `/teams/<game>/<slug>/`
- **Hero** (banner/logo/name/tag/region/socials).
- **Current Roster** (links to profiles; role badges).
- **Stats** (W/L, win rate, streak).
- **Achievements** (`TeamAchievement`), **Upcoming** and **Recent Results**.
- SEO: OG tags, canonical.

**Captain Manage** `/profile/teams/<game>/manage/`
- Edit team metadata + **banner GIF/roster poster**.
- Roster management (Valorant 5–7, eFootball Duo = 2; invites; remove; transfer captain).
- Achievements CRUD.
- Stats rebuild button.
- Presets shortcuts.

**Models**
- `TeamAchievement`, `TeamStats` (denormalized snapshot).

**Tests**
- Public page sections; permissions; constraints enforced.

---

## Part D — Payments Admin: Email PENDING Payers & Bulk Verify
**Goal:** Improve operations; nudge payers.

**Admin Actions**
- **Email all PENDING payers** (preview + dry-run; batched).
- **Bulk verify** with optional note; audit trail (who/when).

**Templates**
- `payments/pending_notice.(txt|html)` and `payments/verified_receipt.(txt|html)`.

**Tests**
- Action works; sends emails; status updated; audit recorded.

---

## Part E — Groups Rendering (fast JSON first, schema later)
**Goal:** Show group stages publicly after reg close.

**Option 1 (Now)**: Store in `Bracket.data` JSON:
```json
{ "groups": [{"name":"Group A","teams":[team_ids]}] }
```
Render on the tournament page; add small admin JSON editor with validation.

**Option 2 (Later)**: `Group`/`GroupMembership` models.

**Tests**
- JSON parsing & render; admin validation errors surface cleanly.

---

## Part F — “My Matches” Page with Filters
**Goal:** Single pane for players.

**Filters**
- Game, State (Scheduled/Reported/Verified), Date range, Tournament.

**Card**
- Opponent, time, BoX, score, check-in window, actions (Report/Confirm/Dispute).

**Perf**
- Prefetch team/user/tournament; indexes on `Match` fields.

**Tests**
- Filter results; empty states; permission scoping.

---

## Part G — Autofill Everywhere (Profile → Forms → Snapshots)
**Goal:** Consistent automation.

**Mapping**
- eFootball Solo: name/email/phone/IGN.
- eFootball Duo: captain + mate from **active team**, else preset, else profile.
- Valorant: captain team + roster from **active team**; per-player Riot ID#Tagline/Discord; allow adding subs up to 2.

**Snapshot**
- Keep exact submitted values in `*Info` models for history.

**Tests**
- Prefill priority order; overrides persist.

---

## Part H — UX Polish, Constraints, Security
**Form UX**
- Sticky summary (tournament name, fee, receiving numbers), inline validation, success toasts.
- Idempotency token to prevent double-submit.

**Constraints**
- Unique: `username`, **email (CI)**, `team.name` per game (CI), `team.tag` per game (CI).
- Valorant roster 5–7; captain-only; no member appears in two teams for same tournament.
- Duo IGN duplicate protections across solo/duo.

**Privacy & Security**
- Profile: `is_private`, `show_email`, `show_phone`, `show_socials`.
- Public profiles at `/u/<username>/` respecting privacy toggles.

**Emails**
- Clear localized copy; footer contact.

**Tests**
- Uniqueness, privacy visibility, duplicate protection, idempotency.

---

## Data Model Summary
**Users/Profiles**
- Unique username; **unique email (case-insensitive)** via index/constraint.
- Profile: `ign`, `efootball_id`, `riot_id`, `discord_id`, socials, privacy toggles.

**Teams**
- `game` (choice), unique `(Lower(name), game)`, unique `(Lower(tag), game)`, `slug` unique per game.
- Media: `banner_image`, `roster_image`, `logo`; `region`, socials.
- `TeamMembership(profile FK, role, status)`; **one ACTIVE per game** rule.

**Presets (teams app)**
- `EfootballTeamPreset`, `ValorantTeamPreset`, `ValorantPlayerPreset`.

**Tournaments**
- Participants & schedule render post reg-close.
- Groups via `Bracket.data` (JSON) initially.

---

## Admin Operations
- Bulk email pending payers; bulk verify payments.
- CSV exports (participants, payments, matches) — optional later.
- Discord webhooks — optional later.

---

## Rollout & Migrations
1. Add constraints (email CI, team name/tag CI). Pre-clean duplicates.
2. Add media/presets models; run migrations.
3. Ship Part A (auto-use team), then B, C, D, E, F, G, H incrementally.
4. Run tests & QA; enable features per game.

---

## Acceptance Criteria (high level)
- Registration is auto-prefilled & auto-binds team; payments required when fee > 0.
- Public tournament pages show participants & schedule after reg-close.
- Teams have pro public pages; captains manage roster/media/achievements.
- Admins can email pending payers & bulk-verify safely.
- My Matches gives each player a clear schedule view.
- Privacy & uniqueness rules enforced across the stack.

---

*Prepared for DeltaCrown — end-to-end esports tournament improvements.*
