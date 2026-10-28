# OwnLobby validation report

Validation date: 2026-10-26. Baseline: `8270018c536df41dcd869c3f4412c3c62a1d685b`.

## Isolation and evidence

No tests used the configured production database. PostgreSQL 18 ran on loopback port 55432 with a new disposable `ownlobby_test` database. `deltacrown.settings_brand_qa` rejects non-loopback hosts and any other database name, uses local-memory mail/cache/Channels and a memory task broker, and stores QA output under ignored `Artifacts/ownlobby/`. Synthetic accounts, team and tournament fixtures existed only there. Browser analytics requests were blocked where used; no production payment or external-provider operation was exercised.

Screenshots and full local logs are retained in `Artifacts/ownlobby/`; session fixtures and database files are deliberately excluded from Git. Unchanged checkpoint source was extracted there to reproduce failures without modifying the implementation branch.

## Automated results

| Check | Result and limits |
| --- | --- |
| Focused Django suite | **158 passed**: new brand/privacy tests; homepage resolver/presentation; escrow cached balances; membership and leaderboard services. |
| Expanded settings suite | **159 passed, 1 failure, 14 errors** across 174 tests. All 15 unsuccessful cases reproduce on checkpoint source: missing required fixture email addresses, and an old settings test sending `Bangladesh` instead of supported ISO `BD`. A valid settings save passes in new tests and real browser CSRF testing. |
| Workflow pytest suite | **44 passed, 1 skipped, 8 failed**: CP pipeline, Game Passport schema, tournament registration and WebSocket integration modules. All eight failures reproduce on checkpoint source under identical restricted QA hosts; old WebSocket tests omit the required Origin. |
| Actual ASGI origins | Old-domain and enabled new-domain HTTPS origins accepted; an untrusted origin rejected. This is local ASGI evidence, not verification of production proxy configuration. |
| Domain configuration | Disabled, additive-host and new-canonical settings imports pass: old hosts/CSRF stay accepted, extra explicit CSRF origins survive, and canonical origin changes only with `SITE_URL`. |
| Django system check | No errors. Existing `siteui.W001` warning about local media storage remains. |
| Frontend build | `npm run build` succeeds: six community JSX outputs and minified Tailwind CSS. Community outputs were previously missing; the explicit esbuild step now produces the existing script paths. Browserslist reports outdated compatibility data. |
| JavaScript syntax | All 28 changed/new standalone JavaScript and build scripts checked with `node --check` pass. Browser runs also check rendered inline behavior on representative pages. |
| Dependency audit | Four moderate npm findings remain in the pre-existing Tailwind/PostCSS dependency chain. No unrelated automatic dependency upgrade was applied. |
| Template compile | **349 compile; five pre-existing failures**, reproduced from checkpoint: ecommerce cart expression; product detail `split`; economy dashboard `format_money_context`; Unfold crispy tag library; tournament group standings `attr`. No new compile failures. |
| Asset identity | All **69** installed approved files match kit SHA256 hashes; centralized brand asset paths resolve. Dark/light primary wordmarks preserve exact segment colors, symbol colors and 1000:220 proportions. |
| Static collection | Production storage completes and resolves the brand assets, but suppresses `Max post-process passes exceeded` for existing `css/design-tokens.css`. The same warning reproduces at the checkpoint. Treat this as an existing pipeline issue. |
| Compatibility | No migration files changed. Existing template URL tags preserved. Settings IDs, field names, hidden tab values, CSRF tags and inline behavior preserved apart from authored brand captions/icon paths. Active passport partial, profile URL module and linked-account JavaScript unchanged. |
| Financial behavior review | Normalized executable ASTs match the checkpoint in ten touched finance/registration service files; edits are authored captions and brand lookups. Existing escrow tests pass. No balances, ledger entries, payment enablement or currency identifiers were migrated. |

Core suite command, after creating/migrating an empty disposable local database and setting the local database environment variables. Do not reuse browser-fixture data for unit tests; a final rerun initially collided with those fixtures, then passed after resetting only the guarded disposable QA database:

```powershell
$env:COMPETITION_APP_ENABLED='1'
.venv/Scripts/python.exe manage.py test apps.siteui.tests.test_ownlobby_branding apps.siteui.tests.test_homepage_hero apps.siteui.tests.test_homepage_presentation apps.economy.tests.test_escrow_cached_balance apps.organizations.tests.test_membership apps.organizations.tests.test_leaderboard_service --settings=deltacrown.settings_brand_qa --keepdb --noinput
.venv/Scripts/python.exe scripts/verify_ownlobby.py
npm run build
```

Workflow modules: `apps/organizations/tests/test_cp_pipeline_e2e.py`, `apps/user_profile/tests/test_game_passport_service_schema.py`, `tests/tournaments/test_phase2_registration.py`, `tests/integration/test_websocket_realtime.py`, using `--ds=deltacrown.settings_brand_qa`.

## Browser and visual review

Chromium checked 39 page/viewport combinations at 360, 768 and 1440 pixels: public homepage, login, tournaments, teams, rankings, store and community; authenticated settings, wallet, Team HQ, profile, organizer console and participant hub. Responses were HTTP 200 with no page JavaScript errors or visible legacy brand names in that pass. The organizer's decorative offscreen glow caused horizontal overflow; removing that effect resolved all three widths on recheck. This is representative local coverage, not proof of every page, permission combination or browser.

Five genuine synthetic account states (captain, team member, solo, organizer and registered participant) showed the universal message first and transitioned once to their actual context, with **0-pixel heading height change**. Reduced-motion behavior, ordinary motion, stable focus and the no-JavaScript universal fallback were checked. No rotating actions, fabricated activity or private cross-user match data are used.

Automated axe-core 4.14.0 WCAG A/AA checks cover homepage, login and teams at desktop width and settings/wallet at mobile width. Findings in those pages were corrected with scoped contrast/accessible-name changes. This scan is limited to those rendered states; it is not an accessibility certification. The checker was loaded through a local same-origin QA route without weakening application CSP.

The browser performed a valid synthetic-account settings save with real CSRF handling (200, success true). Team HQ and organizer guide close controls still work. Passport schema tests and unchanged passport/modal source establish compatibility; real OAuth/provider linking was not performed. Financial transactions, real withdrawals and live provider callbacks were not exercised.

Representative local screenshots:

- `Artifacts/ownlobby/screenshots/home-1440.png` and `home-360.png`
- `Artifacts/ownlobby/screenshots/login-360.png`
- `Artifacts/ownlobby/screenshots/settings-360.png`
- `Artifacts/ownlobby/screenshots/team_hq-360.png`
- `Artifacts/ownlobby/screenshots/organizer-360.png`
- `Artifacts/ownlobby/screenshots/approved-dark-light-logos.png`

SVG master colors are also verified by automated XML assertions and unchanged-file hashes. Primary logos use supplied artwork; approved light masters are used on white certificate surfaces. Browser screenshots do not replace email-client testing or physical small-print/logo review.

## Release limits and existing issues

This implementation is **not declared ready for production deployment**. Existing failed tests/templates, static-processing warning, media persistence and dependency advisories require release-owner review. Existing settings risks in `Documents/DELTACROWN/SETTINGS_REDESIGN_SPEC.md` remain; this task preserves those workflows. The footer's pre-existing newsletter script still simulates success without a subscription backend. The ranking dashboard's 25,000-point Crown claim disagrees with the actual 30,000-point highest-tier threshold. Neither unrelated behavior was silently rewritten.

Stored CMS/legal content, historical artifacts, provider-owned identity, social accounts and domain/mail settings require operational review. The kit's release checklist still calls for external brand/similarity review and platform-specific social uploads. Full browser/device coverage, third-party email clients, load testing and live provider callback checks are outside the completed local QA.

`branding/legacy-references.json` records remaining source references with path, line, classification and reason. Intentional references include technical names, migrations, tests, source comments, historical records, legacy integration/API identifiers and compatibility assets. Later migration references are externally managed domains, mail and account destinations. Unexpected authored public branding must remain zero when regenerating `python scripts/audit_ownlobby.py`.
