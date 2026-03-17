# DeltaCrown — user_profile Migration Squash Plan

**Prepared:** 2026-03-17
**Status:** PLAN ONLY — Do not execute until approved
**Author:** Claude Opus 4.6

---

## Problem Summary

`apps/user_profile/migrations/` contains 37 migrations. Of these, 21 are auto-generated
with identical names (`alter_verificationrecord_id_document_back_and_more`). Each contains
the same 3 `AlterField` operations on `VerificationRecord` image fields (id_document_back,
id_document_front, selfie_with_id) — caused by Django detecting the `upload_to` callable
as "changed" on every `makemigrations` run. These 21 migrations are **semantically no-ops**
that re-declare the same field definition over and over.

## Migration Inventory

### Total: 37 migrations

| # | Name | Type | Cross-App Deps | Notes |
|---|------|------|---------------|-------|
| 0001 | `initial` | CREATE (all models) | `games.0001`, `teams.0001`, `tournaments.0001`, AUTH_USER | Foundation |
| 0002 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0003 | `add_public_id_counter` | CREATE `PublicIDCounter` | — | + redundant VR fields |
| 0004 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0005 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0006 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0007 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0008 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0009 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0010 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0011 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0012 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0013 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0014 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0015 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0016 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0017 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0018 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0019 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0020 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0021 | `primary_team_fk_to_organizations_team` | ALTER FK | `organizations.0027` | **Critical**: switches primary_team FK from teams→organizations |
| 0022 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0023 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0024 | `switch_bounty_game_fk_to_games_app` | ALTER FK | `games.0002` | Switches Bounty.game FK |
| 0025 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0026 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0027 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0028 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0029 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0030 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0031 | `fix_tournament_field_defaults` | ALTER | — | + redundant VR fields |
| 0032 | `add_loadout_dpi_sensitivity_public` | ADD FIELDS | — | HardwareLoadout fields + redundant VR |
| 0033 | `add_team_bounty_support` | ADD FIELDS/FKs | `games.0003`, `organizations.0037`, `tournaments.0033`, AUTH_USER | Multi-app dependency |
| 0034 | `alter_verificationrecord...` | ALTER (no-op) | — | Redundant VR fields |
| 0035 | `gameoauthconnection` | CREATE model | — | **OAuth: GameOAuthConnection** |
| 0036 | `oauth_provider_steam_support` | ALTER + **DATA** | — | **DATA MIGRATION**: normalizes "RIOT"→"riot" |
| 0037 | `gameoauthconnection_epic_provider` | ALTER | — | Adds Epic provider choice |

### Cross-App Dependencies Found

| Migration | External Dependency |
|-----------|-------------------|
| 0001 | `games.0001_initial`, `teams.0001_initial`, `tournaments.0001_initial` |
| 0021 | `organizations.0027_discord_integration` |
| 0024 | `games.0002_initial` |
| 0033 | `games.0003`, `organizations.0037`, `tournaments.0033` |

### Data Migrations Found

| Migration | Operation | Reversible |
|-----------|----------|-----------|
| 0036 | `RunPython(normalize_oauth_provider_values)` — uppercases "RIOT"→"riot" | No (noop_reverse) |

## Root Cause

The `VerificationRecord` model uses `upload_to=apps.user_profile.models_main.kyc_document_path`
(a callable) for its ImageFields. Django computes the field's deconstructed state including the
callable's import path. If the callable's module or attributes change between runs (or if
Django simply re-evaluates the reference), `makemigrations` detects a "change" and generates
a new AlterField. Every other real migration also picks up these phantom changes.

## Squash Strategy

### Recommended Approach: `squashmigrations 0001 0034`

Squash range: **0001 through 0034** (the entire pre-OAuth block).

**Why this range:**
- 0001-0034 contains all 21 redundant VR AlterField migrations
- 0035-0037 are the recent OAuth additions (clean, well-structured, should stay separate)
- 0036 contains a data migration (`RunPython`) — keeping it outside the squash avoids complexity
- 0033 is the last migration with heavy cross-app dependencies
- Squashing 0001-0034 collapses 34 migrations → 1 squashed migration

**What the squash produces:**
- A single `0001_squashed_0034_...` migration with `replaces = [...]` list
- All 21 redundant VR AlterFields collapse to the final field state
- Cross-app dependencies are merged into one dependency list
- No data migrations are involved in this range

**Why NOT squash the whole range (0001-0037):**
- 0036 contains a `RunPython` data migration — squasher cannot optimize it away
- 0035-0037 are the OAuth chain — cleaner to keep them as-is
- The OAuth migrations are recent and well-structured

### Execution Steps (When Approved)

1. **Backup**: Copy `apps/user_profile/migrations/` to `backups/user_profile_migrations_pre_squash/`
2. **Verify DB is current**: Ensure all 37 migrations are applied in production
3. **Run squash**: `python manage.py squashmigrations user_profile 0001 0034`
4. **Review the generated squash**: Verify it has correct dependencies and `replaces` list
5. **Test locally**: Run `python manage.py migrate --check` to verify no changes detected
6. **Deploy**: Push squash migration — Django uses `replaces` to skip already-applied originals
7. **Cleanup (later)**: After all environments have run the squash, delete the 34 original files and remove `replaces`

### Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Cross-app FK dependencies broken | Squash merges all deps; verify in generated file |
| Production DB out of sync | Check django_migrations table before executing |
| Other apps depend on specific user_profile migration | Grep other apps' migrations for `("user_profile", "0NNN")` |
| Squash creates incorrect initial state | Test with `migrate --run-syncdb` on empty DB |

### Pre-Squash Checklist

- [ ] Backup current migrations directory
- [ ] Verify all 37 migrations applied in production (check `django_migrations` table)
- [ ] Grep all other apps for dependencies on user_profile migrations:
      `grep -r '"user_profile"' apps/*/migrations/ --include='*.py'`
- [ ] Run squash command
- [ ] Review generated squash migration
- [ ] Test on local DB
- [ ] Test on fresh DB (migrate from scratch)
- [ ] Deploy to staging
- [ ] Deploy to production

### Future Prevention

After squash, fix the root cause to prevent recurrence:

Add to `VerificationRecord` ImageField declarations:
```python
# Use a string path instead of callable to prevent migration churn
upload_to='kyc_documents/%Y/%m/'
```

Or register the callable path explicitly so Django sees a stable deconstruction.
