# OwnLobby dependency validation

Executed locally 2026-10-26. Branch: `feature/ownlobby-dependency-security`. Baseline Phase 2: `00fa31d942386ca0e9d42fbd553d4ff7eb81cc83`. Empty pre-change checkpoint: `c797aeab7917cf258884954bdbad2ea3cea6078f`. No push, merge, deployment, DNS or live provider change.

Implementation commit: `e7d648e2c3cd294fc3895ad0feb846fe7770e049`. The handoff SHA is recorded in a separate documentation follow-up. Scanner: pip-audit 2.10.1; pytest 8.4.2.

## Environments and isolation

Host: Windows x64, CPython 3.13.15. Original `.venv` is untouched and retains Django 5.2.8/cryptography 46.0.3/PyJWT 2.10.1 for comparisons. The QA venv under ignored `Artifacts/dependencies/qa` installs upgraded packages locally and inherits unchanged packages/test tooling through a .pth pointing to original .venv. It is an overlay, not clean-production proof. Separate `Artifacts/dependencies/runtime` was created empty and clean-installed solely from requirements-prod.txt; its install report, pip check, import/system check and installed-package audit provide independent graph evidence.

Only loopback PostgreSQL 18 on port 55432 and disposable `ownlobby_test` were used. Guarded settings reject non-local/incorrect-name test DBs. Mail/cache/Channels/broker are in memory; synthetic users and files only. S3_TESTS=0 and AWS_EC2_METADATA_DISABLED=true for offline storage tests. No external financial operations, Supabase/Upstash connections, user accounts or provider tokens were used. Synthetic golden fixture is deliberately public QA-only material signed/encrypted with a fixed test key, not production secrets.

Full local logs, resolution/install reports, OSV/PyPI metadata, screenshots and audit JSON remain under ignored `Artifacts/dependencies/`. Committed matrix/inventory contain sanitized public dependency metadata. Do not commit raw package descriptions or environment dumps.

## Results

| Category | Actual result |
|---|---|
| Original focused suite | 197 passed before updates |
| Group 1 framework | 197 passed; pip check passed; allauth migration filenames unchanged (account 10/socialaccount 7) |
| Group 2 transport | 17 WebSocket tests passed; pip check passed |
| Group 3 network/auth | pip check passed; intermediate 30-test run had one new fixture/config failure: QA MD5-only hasher could not verify the intentionally old PBKDF2 fixture. Test now explicitly enables PBKDF2, leaving application settings unchanged. |
| Group 4 images/documents | pip check passed; intermediate 15 tests had one missing-native-Cairo error. Final test explicitly skips only Cairo import OSError and reports why; PDF generation/extraction/import/preview, JPEG/PNG/WebP transform, invalid file rejection and legacy auth tests pass. |
| Group 5 / final focused suite | **212 run: 211 passed, one skipped** (Cairo native DLL absent) |
| Final workflows | **60 passed, one existing skip**; trusted/untrusted/missing WS Origin, valid/invalid/inactive auth, private events, tournament registrations, competition pipeline, Game Passport and email sender |
| Expanded OAuth/offline certificate storage | **38 passed, seven failed, eight skipped** on upgraded environment; identical node outcomes in untouched original environment |
| Clean runtime install/pip check | passed; 132 runtime packages plus pip, no broken requirements |
| Production/development resolver | both succeeded; exact runtime pins aligned; initial duplicate typing-inspection conflict corrected |
| Final audit | six advisory entries, all Twisted 26.4.0; resolved 132-package scan and installed 133-distribution scan agree |
| Django check in QA and clean runtime | no errors; existing siteui.W001 ephemeral-media warning remains visible |
| Frontend | npm run build succeeds (community JSX + Tailwind); existing outdated Browserslist notice |
| Brand/static/template | 69 approved asset hashes match; 353 templates compile; one unchanged dormant optional crispy integration failure; settings contracts preserved; no new verifier failures; real hashed static collection succeeds |
| Deployment shell syntax | bash -n passes for render_build.sh, start.sh, bin/start_render.sh and bin/start_worker.sh |
| Linux CPython 3.12 | **Runtime not tested**; no Docker/WSL/Python 3.12 available. 129 manylinux CPython 3.12 wheels downloaded; Cloudinary/pycairo source builds and native runtime untested. |
| Local TLS | verified self-signed QA certificate; HTTPS 200 over TLS 1.3 using upgraded cryptography/pyOpenSSL/Twisted; loopback-only ephemeral server |
| Local network Daphne | HTTP 200, WS 101 and bounded 512-byte frame rejected under test-only 256-byte frame/message limit. No claim of production load testing. Bare CR/LF malformed headers accepted: **known P1 residual**, not a pass. |
| Browser | 12 guest page/viewport checks, all 200, no overflow or JS errors; widths 360/768/1440; home, login, teams, tournaments |
| Scoped accessibility | mobile login zero violations; mobile homepage two violations (color-contrast, scrollable-region-focusable, one node each). Not a certification; previous desktop scans did not establish mobile-home coverage. |

Existing seven failing nodes (same on both dependency versions):

- apps/user_profile/tests/test_oauth_api.py::test_riot_callback_success_creates_passport_and_oauth_connection
- apps/user_profile/tests/test_oauth_api.py::test_riot_callback_invalid_code_returns_structured_error
- apps/user_profile/tests/test_oauth_api.py::test_steam_callback_success_creates_cs2_passport_and_oauth_connection
- apps/user_profile/tests/test_oauth_api.py::test_steam_same_id_can_link_cs2_and_dota2_for_same_user
- apps/user_profile/tests/test_oauth_api.py::test_steam_callback_redirect_mode_returns_to_settings_passports_tab
- apps/user_profile/tests/test_oauth_api.py::test_epic_callback_success_creates_rocketleague_passport_and_oauth_connection
- tests/accounts/test_google_oauth.py::test_google_oauth_creates_user_and_logs_in

Observed baseline causes include tests expecting a JSON Riot login response where current route redirects (302), missing expected Steam/GameProfile and Epic OAuth rows, Steam status/error mismatch, and Google expected redirect `/account/profile/` versus actual `/`. These are verified baseline mismatches, not all proven harmless fixtures. No provider implementation or assertion was weakened to make them green. Existing live-S3 tests remain intentionally gated (eight skips); existing CP fixture skip remains because its synthetic Match lacks a required tournament FK. New Cairo skip is an environment limitation, not successful SVG rendering.

No previously passing regression was observed in the compared suites. This does not certify every application test, enabled provider or production topology. Full project test suite, real Redis/broker integration, worker load/retry behavior, private media ACL/persistence, Linux Cairo rendering, live auth/email delivery and production request-smuggling exposure through Render were not executed.

## Executed command recipe

Commands below reproduce the actual paths/arguments. PowerShell `*>` redirection stored logs; native pip notices may be rendered as NativeCommandError text even on exit 0, so success was checked from reports, audit JSON and pip check, not the presence of a red log line.

```powershell
# Initial inspection and isolation
git status --short
git branch --show-current
git log -6 --oneline
git merge-base --is-ancestor 8dff4da78162a986ca5e1c8d93d8a4a15f6c774d HEAD
git commit --allow-empty -m 'chore: checkpoint before OwnLobby dependency remediation'
git switch -c feature/ownlobby-dependency-security
& .venv/Scripts/python.exe -m venv Artifacts/dependencies/runtime
# QA venv uses the documented .pth overlay; audit tooling is separate.

# Baseline pinned and full-graph audits (baseline requirements were still unchanged)
& Artifacts/readiness/dependency-audit-venv/Scripts/python.exe -m pip_audit -r requirements-prod.txt --no-deps --disable-pip --format json --output Artifacts/dependencies/baseline-audit.json
& Artifacts/dependencies/runtime/Scripts/python.exe -m pip install --dry-run --ignore-installed --no-cache-dir -r requirements-prod.txt --report Artifacts/dependencies/baseline-resolved.json
& Artifacts/readiness/dependency-audit-venv/Scripts/python.exe -m pip_audit -r Artifacts/dependencies/baseline-resolved.txt --no-deps --disable-pip --format json --output Artifacts/dependencies/baseline-full-audit.json

# Group installs (N=1..5), run individually with recorded install reports
& Artifacts/dependencies/qa/Scripts/python.exe -m pip install --no-cache-dir -r Artifacts/dependencies/group1.txt --report Artifacts/dependencies/group1-install.json
& Artifacts/dependencies/qa/Scripts/python.exe -m pip check
# Same commands executed for group2.txt, group3.txt, group4.txt and group5.txt.

# Final independent install and graph resolution
& Artifacts/dependencies/runtime/Scripts/python.exe -m pip install --dry-run --ignore-installed --no-cache-dir -r requirements-prod.txt --report Artifacts/dependencies/final-resolved.json
& Artifacts/dependencies/runtime/Scripts/python.exe -m pip install --no-cache-dir -r requirements-prod.txt --report Artifacts/dependencies/clean-install.json
& Artifacts/dependencies/runtime/Scripts/python.exe -m pip check
& Artifacts/dependencies/runtime/Scripts/python.exe -m pip install --dry-run --ignore-installed --no-cache-dir -r requirements.txt --report Artifacts/dependencies/dev-resolved.json
# Generated full resolved manifests contain every distribution, not only root imports.
& Artifacts/readiness/dependency-audit-venv/Scripts/python.exe -m pip_audit -r Artifacts/dependencies/final-resolved.txt --no-deps --disable-pip --format json --output Artifacts/dependencies/final-audit.json
& Artifacts/readiness/dependency-audit-venv/Scripts/python.exe -m pip_audit --path Artifacts/dependencies/runtime/Lib/site-packages --format json --output Artifacts/dependencies/installed-audit.json

$env:DATABASE_URL='postgresql://ownlobby_qa@127.0.0.1:55432/ownlobby_unused'
$env:DATABASE_URL_TEST='postgresql://ownlobby_qa@127.0.0.1:55432/ownlobby_test'
$env:COMPETITION_APP_ENABLED='1'
$env:S3_TESTS='0'
$env:AWS_EC2_METADATA_DISABLED='true'
& Artifacts/dependencies/qa/Scripts/python.exe manage.py check --settings=deltacrown.settings_brand_qa
& Artifacts/dependencies/runtime/Scripts/python.exe manage.py check --settings=deltacrown.settings_brand_qa
& Artifacts/dependencies/qa/Scripts/python.exe manage.py test apps.common.tests.test_release_readiness apps.siteui.tests.test_ownlobby_branding apps.siteui.tests.test_homepage_hero apps.siteui.tests.test_homepage_presentation apps.economy.tests.test_escrow_cached_balance apps.organizations.tests.test_membership apps.organizations.tests.test_leaderboard_service apps.user_profile.tests.test_settings_control_deck_smoke apps.user_profile.tests.test_settings_endpoints_smoke apps.common.tests.test_dependency_compatibility --settings=deltacrown.settings_brand_qa --keepdb --noinput
& Artifacts/dependencies/qa/Scripts/python.exe -m pytest tests/integration/test_websocket_realtime.py apps/accounts/tests/test_email_sender.py apps/organizations/tests/test_cp_pipeline_e2e.py apps/user_profile/tests/test_game_passport_service_schema.py tests/tournaments/test_phase2_registration.py --ds=deltacrown.settings_brand_qa --tb=short --show-capture=no
& Artifacts/dependencies/qa/Scripts/python.exe -m pytest apps/user_profile/tests/test_oauth_api.py tests/accounts/test_google_oauth.py tests/accounts/test_google_oauth_linking.py tests/certificates/test_s3_storage_core.py --reuse-db --ds=deltacrown.settings_brand_qa --tb=short --show-capture=no
# Same expanded command executed with .venv/Scripts/python.exe for comparison.
& Artifacts/dependencies/qa/Scripts/python.exe scripts/verify_ownlobby.py --collect-static
npm run build
& 'C:/Program Files/Git/bin/bash.exe' -n render_build.sh start.sh bin/start_render.sh bin/start_worker.sh

# Packaging evidence only; NOT Linux execution. Input excludes pycairo/cloudinary source
# distributions and Python 3.13-only audioop-lts. No dependency checks are waived in audit.
& Artifacts/dependencies/runtime/Scripts/python.exe -m pip download --no-cache-dir --no-deps --only-binary=:all: --platform manylinux_2_28_x86_64 --platform manylinux2014_x86_64 --python-version 3.12 --implementation cp --abi cp312 -r Artifacts/dependencies/linux-wheel-input.txt --dest Artifacts/dependencies/linux-wheels
wsl --list --verbose
py -0p
# Local bounded transport and Playwright harnesses, retained with the evidence:
& Artifacts/dependencies/qa/Scripts/python.exe Artifacts/dependencies/transport_smoke.py
& Artifacts/dependencies/qa/Scripts/python.exe Artifacts/dependencies/browser_smoke.py
& Artifacts/dependencies/qa/Scripts/python.exe Artifacts/dependencies/tls_smoke.py
```

The audit intentionally exits nonzero for the six remaining findings. Cross-target wheel download initially failed with manylinux2014 alone; the corrected glibc-compatible tag set succeeded. An initial browser harness used Daphne without static serving and blocked CDN assets, producing invalid visual evidence; discarded and rerun with local runserver --insecure static serving, public static CDNs only, analytics/providers blocked. CSP rejected initial inline axe injection; switched to intercepted same-origin script without changing CSP. Only the final browser JSON/scope is counted above.

## Evidence and reproduction limits

`baseline-tests.log`, `group1-tests.log`, `group2-tests.log`, `group3-tests.log`, `group4-tests.log`, `final-tests.log`, `workflow-tests.log`, `oauth-storage-tests.log`, `baseline-oauth-storage-tests.log`, `clean-install.json`, `clean-pip-check.log`, `dev-resolved.json`, `installed-audit.json`, `transport-smoke.json`, `tls-smoke.json`, `linux-wheels.log`, `branding-static.log`, `frontend-build.log`, `browser.json` and `screenshots/` are local evidence, not deployable code or secrets. Browser screenshots cover guest mobile home/login. Prior Phase 2 screenshots remain historical evidence; no authenticated browser fixtures were reused here.

Golden compatibility fixture and 15 new tests are committed so future isolated environments can repeat auth, encrypted-field, upload, PDF and serialization regressions. Requirements and public inventory/matrix are committed so audits can be regenerated without relying on local artifacts. To repeat old-version comparisons, use a separate environment/check-out at the stated checkpoint rather than downgrading the secured environment. Source builds and exact wheel hashes need fresh Linux release validation.

**Release recommendation: No-Go.** Resolve the HTTP parser advisory, Linux/native-runtime checks and the unchanged infrastructure/provider/media/recovery gates. Seven baseline OAuth failures remain a release investigation, despite no observed dependency regression.
