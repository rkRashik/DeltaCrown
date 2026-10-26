# OwnLobby cleanup handoff

Completed locally on 2026-10-26. Cleanup introduces no new failure in the focused Phase 4 regression suites. **Production cutover remains No-Go; this task does not certify staging readiness.** No push, merge, deployment, DNS/provider change, production connection or storage migration occurred.

## Changes and preservation

- Replaced the product-oriented README with verified engineering setup, architecture, safe test/build commands, release boundaries and documentation navigation. Preserved the original README's exact Git bytes in [product history](reference/README_PRODUCT_HISTORY.md).
- Added the [documentation guide](OWNLOBBY_DOCUMENTATION_GUIDE.md), [repository audit](OWNLOBBY_REPOSITORY_AUDIT.md), [per-path cleanup manifest](OWNLOBBY_CLEANUP_MANIFEST.md) and [sanitized inventory](reference/repository-inventory.json). Historical reports retain their paths and evidence; technical/ops/audit introductions now distinguish historical advice from current setup.
- Added a blank local environment example, explicit root placement policy and offline documentation checker. Corrected the old hygiene tool's unsafe delete/move recommendations; ignored owner files remain inventoried separately.
- Guarded the legacy Riot diagnostic against import-time HTTP requests. Its explicit CLI body remains AST-equivalent to the original; it was not executed against a provider. Changed only the launcher's displayed brand name.
- Removed exactly one tracked file: `apps/user_profile/static_backup_20251231/admin/admin_game_passport.js` (8,406 bytes), identical to the retained active admin script. Actual Django static discovery and production-style collection still resolve the active asset. No technical folder/file was renamed.

All **26 protected files** under `Documents/DELTACROWN/` retain their paths, sizes and SHA-256 hashes. All **69 approved brand assets** pass the existing hash verifier. Owner documents, drafts, private uploads/evidence, existing ignored artifacts, environments and media remain in place. Application models/migrations, financial calculations, storage configuration, dependencies, Twisted backport, settings contracts and SEO/domain behavior are unchanged. The preserved README and retained active admin script were also checked byte-for-byte.

## Validation actually executed

Environment: Windows, Python 3.13.15; isolated local PostgreSQL on loopback port 55432 with guarded `ownlobby_test` database. QA Python: `Artifacts/dependencies/qa/Scripts/python.exe`; clean-runtime dependency check: `Artifacts/security-runtime/runtime/Scripts/python.exe`. Node 24.19.0/npm 11.17.0. No production database or live provider fixture was used.

| Check | Result |
|---|---|
| Core Django suites: release/domain/SEO, branding/homepage, escrow, memberships/rankings, settings, dependency/media/HTTP security | 219 passed, 1 existing native Cairo skip (220 tests run) |
| OAuth/provider ownership/Google redirect regressions | 47 passed; 2 existing Django migration deprecation warnings |
| WebSocket, email sender, competitive pipeline, Game Passport, registration, storage contract suites | 88 passed, 9 existing skips; 2 migration deprecation warnings |
| New standalone repository/import safety regressions | 6 passed |
| Django system checks | No errors; existing `siteui.W001` filesystem-media warning remains |
| Django reverse/resolve smoke checks | 12 passed, including auth/settings/tournament/team/ranking/wallet routes |
| OwnLobby verifier + real production-style hashed static collection | 69 approved assets unchanged; 353 templates compiled; 1 unchanged dormant optional-crispy template failure; no new failures; settings contracts preserved |
| Frontend build | Community JSX and Tailwind passed; existing Browserslist freshness notice |
| JavaScript syntax | 10 files passed, including active admin script and compiled community outputs |
| Launcher/build/start syntax | PowerShell parser: zero errors; shell scripts: `bash -n` passed; launcher not executed |
| Twisted backport integrity | Passed; unchanged SHA-256 `439da47560b0fd5d3ecbe5b027c54bd44864870cdcc2b81b016dee8f705ea8e6` |
| Clean-runtime `pip check` | Passed; dependency declarations and vendored bytes unchanged |
| Repository placement / active offline documentation links | Passed; no active missing targets/headings |
| Historical documentation links | 47 unresolved findings: 14 workspace-only, 6 missing, 27 outside-workspace; retained visibly for review |
| Protected files / original README / active admin bytes | Passed local pre/post comparisons |

The 9 workflow skips are the 8 live-S3 checks deliberately disabled and 1 existing competitive-pipeline fixture limitation. No test was deleted or security expectation relaxed. The optional template and Cairo limitations match Phase 4. Logs and structured reports remain ignored under `Artifacts/repository-cleanup/`; they are not portable public release artifacts. The manifest and inventory provide non-sensitive, tracked conclusions.

Final diff review has one intentional whitespace exception: the exact historical README snapshot retains three original Markdown hard-break lines flagged by `git diff --check`. Other staged files pass the whitespace check. A focused credential-pattern scan of changed/new files returned no matches; this is not a guarantee that all historical repository content is secret-free.

Reproducible entry points after configuring the README's guarded local test environment:

```powershell
python -m unittest tests.test_repository_tools
python scripts/ops/check_repo_hygiene.py
python scripts/check_documentation.py --all --output Artifacts/repository-cleanup/documentation-links.json
python scripts/build_twisted_backport.py
npm run build
python scripts/verify_ownlobby.py --collect-static
```

The core run used `manage.py test` with `deltacrown.settings_brand_qa`, `--keepdb --noinput`; OAuth used explicit mocked-provider targets and `--reuse-db`; workflows used explicit targets with the same guarded settings. See the existing [security closure](OWNLOBBY_SECURITY_CLOSURE.md) and [OAuth reliability](OWNLOBBY_OAUTH_RELIABILITY.md) for the Phase 4 suites. Broader production, live provider, native Linux/Cairo, browser/responsive, live Redis/Celery and full-project tests were **not rerun** during this cleanup. No fresh vulnerability scan was performed because dependency inputs are unchanged; the Phase 4 advisory dispositions remain applicable. A frontend build using existing installed packages is not a fresh `npm ci` reproducibility test.

## Deferred decisions and next work

The 51 other nonempty duplicate groups remain: approved role copies, game/art aliases, Python namespace markers, auth template aliases and owner drafts require their existing paths or further evidence. Historical documents, old technical identifiers, migration sketches, ignored media and research are not deleted. Review exact candidates in the manifest before any further operation; do not treat candidate status as approval.

The ignored root environment example contains a populated provider-key-shaped value. It remains local and untouched; assess privately whether it is active before future sharing. Use `config/development.env.example` instead. Repository-wide licensing terms also need owner clarification before redistribution. No secret value or private filename inventory is published by this cleanup.

Media-storage development can proceed as a **separately approved implementation** once the provider, budget, public/private delivery design and retention/recovery policy are agreed. All 53 upload fields, rich-text paths, storage helpers, fixtures and recovery evidence are preserved. Cleanup introduces no new prerequisite for that workstream. The previous proposed “Phase 5 media” is distinct from this Phase 5 repository task.

Release gates remain: actual Linux/Python 3.12/native Cairo execution; durable media with private authorization and migration/restore proof; backup recovery; isolated staging validation of workers/broker, authentication providers and email; then explicitly approved domain/provider/canonical cutover. See [media architecture](OWNLOBBY_MEDIA_ARCHITECTURE.md), [readiness](OWNLOBBY_PRODUCTION_READINESS.md) and [release handoff](OWNLOBBY_RELEASE_HANDOFF.md). No dashboard action is requested during cleanup. Do not push/deploy or change the Render hostname/DNS as a consequence of this handoff.

## Git and rollback

- Starting branch: `feature/ownlobby-security-runtime`.
- Starting reviewed HEAD: `8fc7c335f43709e91e64ea9dde8011c2a8ed26bd`.
- Empty safety checkpoint: `97bd94d882e42edb9ab0dfab87b6d27a69231c2a`.
- Cleanup branch: `feature/ownlobby-repository-cleanup`.
- Implementation commit: `338182e439c891d0a6cf0b0c0326b4084bbc2599` (`chore: organize OwnLobby repository and documentation`). This handoff's commit-reference follow-up is documentation-only; final HEAD is reported to the owner separately.

All Phase 1–4 implementation commits remain ancestors. For rollback, use a reviewed ordinary revert of the cleanup implementation, preserving later work and history. The one removed duplicate can be restored independently with the checkpoint command in the manifest. Git cannot restore ignored owner files, which is why none were removed. No force reset or history rewrite is needed.
