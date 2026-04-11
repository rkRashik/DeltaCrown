# Repo Cleanup Audit — Session 4

**Date:** 2026-04-11  
**Scope:** Generated helper tools, scripts, reports, artifacts, and stale docs

---

## Deletion Summary

| Category | Files Deleted | Files Kept/Reviewed |
|----------|--------------|-------------------|
| Root probe/report files | 8 | 0 |
| `tools/` one-time scripts | 25 | 2 (REVIEW) |
| `scripts/` one-time scripts | 22 | 15 (KEEP/REVIEW) |
| `Artifacts/` outputs | 8 | 0 |
| `reports/` | 3 | 0 |
| `logs/` | 4 | 0 |
| `evidence/` | 6 | 0 |
| `docs/` generated reports | ~90 | ~30 (KEEP) |
| **Total** | **~166** | **~47** |

---

## Files Deleted

### Root Directory
- `phase10_test_probe.txt` — test probe
- `riot.txt` — UUID probe
- `CSP_RUNTIME_INTERACTION_FIX_REPORT.md` — generated report
- `LOCAL_PRECOMMIT_VALIDATION_REPORT.md` — generated report
- `LOCAL_RUNTIME_STABILIZATION_REPORT.md` — generated report
- `NOTIFICATION_REBUILD_TRACKER.md` — stale tracker
- `TOURNAMENT_AUDIT_TRACKER.md` — stale tracker
- `TOURNAMENT_LIFECYCLE_AUDIT_REPORT.md` — generated report

### `tools/` (entire directory except REVIEW items)
All 25 one-time conversion/fix scripts deleted. Two files flagged REVIEW:
- `generate_frontend_types.py` — may be useful for SDK regen
- `verify_schema.py` — possibly reusable

### `scripts/` (one-time items only)
22 files deleted. Kept: `seed_all.py`, `seed_realistic_data.py`, `Seed_Game/`, test runners, and 10 REVIEW items.

### `Artifacts/` (all contents)
All benchmark outputs, DB dump, rehearsal logs, test matrix files.

### `reports/`, `logs/`, `evidence/` (all contents)
Canary reports, OOM analysis, dev logs, test outputs, validation artifacts.

### `docs/` (generated/stale items)
- 15 root-level generated reports (CSP audits, sprint trackers, launch reports)
- `docs/audits/` — 9 completed audit files
- `docs/cleanup/` — 3 completed cleanup docs
- `docs/guides/` — 2 historical fix docs
- `docs/migrations/` — 6 completed migration repair docs
- `docs/ops/` — 15 stale ops artifacts
- `docs/organizations/` — 2 completed phase reports
- `docs/profile_rebuild/` — 2 stale items
- `docs/runbooks/` — 10 completed/stale runbook items
- `docs/settings/` — 2 completed audits
- `docs/team/` — 5 completed items
- `docs/teams/` — 2 completed phase reports
- `docs/testing/` — 1 verification doc
- `docs/user_profile/` — ~40 completed phase/audit docs (kept `README.md`)
- `docs/vnext/` — 14 historical docs + `archive/` dir
- `docs/architecture/FINAL_COMPLETION_AUDIT.md`
- `docs/admin/WEBHOOKS_ADMIN_READONLY.md`
- `docs/ci/perf-secrets-hotfix.md`
- `docs/prototypes/` — empty dir

---

## Files Kept (Active)

### Core Design Docs
- `docs/AUTOMATED_TOURNAMENTS_ROADMAP.md`
- `docs/COMPETITIVE_SYSTEM_DESIGN.md`
- `docs/DASHBOARD_DESIGN.md`
- `docs/DB_POLICY.md`
- `docs/MANUAL_TESTING_GUIDE.md`
- `docs/RANKING_PAGE_DESIGN_BRIEF.md`
- `docs/TOURNAMENT_SEEDING_MODEL_REFERENCE.md`
- `docs/DEPLOYMENT_CHECKLIST.md`
- `docs/SOFT_LAUNCH_GO_LIVE_CHECKLIST.md`

### Active Architecture/Feature Docs
- `docs/architecture/HUB_INTEGRATION_CONTRACT.md`
- `docs/architecture/LIVE_DRAW_DIRECTOR.md`
- `docs/architecture/system_architecture.md`
- `docs/architecture/URL_ROUTING_STRATEGY_FINALIZED.md`
- `docs/api/endpoint_catalog.md`
- `docs/admin/leaderboards.md`, `tournament_ops.md`
- `docs/development/FEATURE_FLAGS.md`, `naming-conventions.md`
- `docs/integration/leaderboards_examples.md`
- `docs/leaderboards/` (all)
- `docs/specs/` (all)
- `docs/spectator/README.md`
- `docs/security/SECURITY.md`
- `docs/profile_rebuild/SETTINGS_PAGE_UI_UX_DESIGN_SPEC.md`
- `docs/user_profile/README.md`

### Active Runbooks/Ops
- `docs/runbooks/canary_deployment.md`
- `docs/runbooks/database_reset.md`
- `docs/runbooks/deployment.md`
- `docs/runbooks/monitoring_setup.md`
- `docs/runbooks/ONCALL_HANDOFF.md`
- `docs/runbooks/webhook_receiver_setup.md`
- `docs/ops/COST_GUARDRAILS.md`
- `docs/ops/TEST_INFRA_QUICKSTART.md`
- `docs/ci/BRANCH_PROTECTION_CONFIG.md`

### Active Scripts
- `scripts/seed_all.py`, `scripts/seed_realistic_data.py`
- `scripts/Seed_Game/seed_2025_games.py`

---

## REVIEW Items (Need Human Decision)

| File | Reason |
|------|--------|
| `tools/generate_frontend_types.py` | SDK type gen — may need again |
| `tools/verify_schema.py` | Schema validation — reusable? |
| `scripts/canary_smoke_tests.py` | Active canary test? |
| `scripts/detailed_smoke_test.py` | Active smoke test? |
| `scripts/run_tests.ps1/py/sh` | Active test runners? |
| `scripts/reset_test_db.py` | Reusable test DB reset |
| `scripts/setup_test_db.py` | Reusable test DB setup |
| `scripts/list_api_routes.py` | Reusable API route lister |
| `scripts/supabase_enable_rls_all_tables.sql` | DB setup ref |
| `synthetics/uptime_checks.yml` | Active monitoring config? |
| `docs/FULL_PLATFORM_TEST_PLAN.md` | Active test plan? |
| `docs/PRODUCT_IMPROVEMENT_PLAN.md` | Active roadmap? |
| `docs/canary/webhooks_runbook.md` | Active runbook? |
| `docs/MyTesting/` (2 files) | Manual testing refs |
| `docs/ops/REPO_HYGIENE_CONTRACT.md` | Active policy? |
| `migrations_new/add_is_passport_supported.py` | Orphaned migration? |
