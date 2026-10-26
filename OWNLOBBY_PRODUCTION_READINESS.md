# OwnLobby production readiness

Audit date: 2026-10-26. Rebrand baseline: `ece37c2fa5fc9f81305375684d2c8e606c9e2c88`. Readiness checkpoint: `c525ffb7be6ebca1c17d3bdd07e6650b6d738ffb`. Branch: `feature/ownlobby-production-readiness`.

## Release decision

**No-Go for production deployment or domain cutover today.** Local corrections and automated results support an isolated staging candidate. Production Python dependency remediation, durable/private media delivery, actual Render configuration, recoverable backups, mail delivery and provider callbacks remain release gates. No residual production risk has been accepted on the owner's behalf.

No production database was queried or changed. No secrets were printed, rotated or committed. No remote configuration, DNS, push or deployment occurred. Approved artwork, business identifiers and schemas are retained.

## Findings and disposition

| Priority | Evidence and impact | Correction / remaining action |
| --- | --- | --- |
| P0 | `apps/common/seo.py` serialized authored names/descriptions directly into a `safe` JSON-LD script. A closing script tag could escape the data block. | Fixed: escape HTML-significant characters and Unicode separators while retaining valid JSON; malicious-text round-trip/render regression added. |
| P0 | Tournament detail queries exposed draft/pending records, and the tournament WebSocket accepted every authenticated spectator. Sensitive dispute, registration and payment detail events were delivered without recipient authorization. | Fixed: existing organizer/staff rules guard unpublished reads; private event delivery requires relevant organizer capability, the registration owner/team, or a registered match participant. Missing/deleted rooms are denied. Public score/bracket formats and routes remain compatible. Local positive/negative regressions exercise these boundaries. |
| P0 conditional | Local configuration has **no Cloudinary configuration** and uses `FileSystemStorage`. Render filesystem storage cannot establish durable uploads. KYC, payment and match evidence fields also use the default backend. The live backend/ACLs are unavailable for verification. | **Open release gate:** verify production storage, backups, private-file authorization and restart persistence before deployment. New `siteui.E001` deploy check prevents a Render release with filesystem default storage. Do not silence it instead of fixing storage. |
| P1 | Static processing parsed a self-import in a comment in `static/css/design-tokens.css`, causing a hash cycle; `RobustStaticFilesStorage` suppressed the error. | Fixed source comment and removed suppression. Production storage collection now finishes without the cycle, and an actual cyclic-file regression confirms errors remain visible. Existing `manifest_strict=False` missing-manifest compatibility is retained; it is not permission to ignore missing assets. |
| P1 | `render.yaml` bypassed frontend builds, referenced a Render database instead of the existing external database, and declared `SECRET_KEY` / `DEBUG` although code reads **`DJANGO_SECRET_KEY` / `DJANGO_DEBUG`**. The other build script used `npm install` and ran migrations. | Local blueprint corrected to the combined locked build, existing dashboard-managed Supabase and secret bindings, and actual setting names. Build no longer migrates. Actual dashboard commands/env/plan must be compared manually; local YAML is not proof of the live configuration. No secret value should change. |
| P1 | Four reachable templates could not compile: store cart, product detail, wallet dashboard and tournament standings. Additional missing arithmetic/date helpers were hidden behind the first parser errors. | Fixed filter/tag loading and syntax; added decimal display helpers only. No checkout, pricing, balance or ledger algorithm changed. Regression compilation passes. |
| P1 | Profile sitemap excluded PRIVATE presets but included private-account profiles; dynamic sections silently truncated and swallowed exceptions. | Fixed conservative public eligibility, 1,000-record pagination, discoverable sitemap pages, stable ordering and visible backend failures. No user email/contact fields are serialized. |
| P1 | PostgreSQL rejected wallet-profile cache synchronization because `FOR UPDATE` locked a nullable outer join. Exceptions were logged/swallowed despite passing escrow assertions. | Fixed by removing the unnecessary joined read; wallet and profile are still locked individually. Repeated synchronization test verifies exact ledger records and balance preservation. No reconciliation against production data was run. |
| P1 | A synchronous dispute service called an async broadcast without awaiting it. | Fixed with the existing `async_to_sync` bridge, after adding recipient privacy guards. No financial mutation behavior changed. |
| P1 | Canonical/filter policy could be bypassed by view-supplied metadata; reset links depended on a potentially stale Django Sites domain; OTP text linked to an unrelated old `.com` origin. | Fixed shared rendered canonical/query policy, sensitive-endpoint `X-Robots-Tag`, canonical-origin mail links and OwnLobby reset subject. Sender mailbox stays unchanged. Old callbacks remain available. |
| P1 | Deployment, live SMTP verification, DNS/TLS, callback registration, Redis/worker behavior and backup restoration are not verifiable from local source. | **Open operational gates.** Complete the staged checklist in `OWNLOBBY_DOMAIN_MIGRATION.md`; do not infer success from local tests. |
| P1 | A separate read-only audit of pinned `requirements-prod.txt` reports **308 advisory entries in 29 packages**, including Django, Daphne, DRF, JWT/crypto, image/PDF parsing and HTTP libraries. These are scanner entries, not 308 confirmed exploitable application defects. | **Open security-maintenance gate.** Inventory is committed in `branding/production-dependency-audit.json`. No broad framework/crypto/PDF upgrade was silently applied. Triage reachability, select supported compatible fixes, align both requirements files and rerun full tests plus Linux/Python 3.12 staging before deployment. This gate cannot be waived by focused test success. |
| P2 | Existing settings tests recreated signal-created privacy rows, omitted a required email and used a country name instead of ISO `BD`. Older WebSocket tests omitted Origin, hid users in uncommitted transactions, omitted `await`, misunderstood the diagnostic close handshake and cancelled consumers with a timeout. | Corrected fixtures and assertions against the real contracts. Missing/untrusted Origin and invalid/expired JWT are still denied. No security middleware was disabled. |
| P2 | Newsletter UI and backend simulated successful subscription and logged submitted addresses. | Fixed: unavailable UI collects nothing; existing POST endpoint returns an honest 503 with `success=false`. A real consent-aware subscriber system remains future work. |
| P2 | The Crown dashboard caption said 25,000; actual ranking services use 30,000. | Caption corrected to 30,000. `THE_CROWN`, thresholds, scoring and history unchanged. |
| P2 | Four moderate npm findings arise from the existing PostCSS selector parser dependency chain, advisory GHSA-rj75-hqrm-r3gf. Fix suggestions include a Tailwind major upgrade/downgrade. | Not automatically upgraded. Build-only CPU-exhaustion exposure from crafted selector input, not a demonstrated runtime exploit. Builds consume trusted source. Schedule a compatible dependency upgrade; no owner risk acceptance is assumed. |
| P2 | Base pages still use Tailwind Play CDN plus compiled CSS and several font/icon/CDN resources. CSP permits broad HTTPS images and `ws:` / `wss:` connections. | Retained for interaction compatibility. Audit dynamic class generation and asset self-hosting separately before removing runtime styling. ASGI and consumer origin restrictions remain enforced. CSP tightening needs a feature/third-party inventory. No synthetic performance score is claimed. |
| P2 | Existing settings workflow risks remain documented in `Documents/DELTACROWN/SETTINGS_REDESIGN_SPEC.md`. | No settings redesign or contract reorganization performed. Existing save/CSRF and passport sources verified. |
| P2 | Legacy tournament WebSocket privileged command branches include acknowledgement placeholders, including `force_refund`. No active template/client reference to that command was found; actual organizer financial controls use existing services/API paths. | Not activated or implemented as a financial feature here. Do not treat its acknowledgement as a ledger transaction. Review/deprecate that legacy protocol separately; real financial execution was not tested. |
| P2 | Expanded tournament accessibility checks found incorrect desktop tablist semantics, unnamed mobile back/share controls, low-contrast mobile text and a CSP-blocked inline share handler. | Fixed with native grouped section controls, accessible labels, scoped muted colors and a nonce-authorized share listener. Desktop section activation and mobile share keyboard activation are checked; no navigation/form IDs changed. |
| P3 | One optional `unfold_crispy/layout/table_inline_formset.html` template still requires uninstalled crispy libraries. No active view, form helper, settings entry or dependency references it. | Dormant optional integration; not installed merely to make a compile counter green. Keep disabled. If enabled later, install/configure the actual integration and test its included templates/JavaScript. |
| P3 | Browserslist compatibility data and Django migration deprecation warnings remain. | Documented; no unrelated framework/toolchain upgrade. |

## Infrastructure evidence and limits

The local environment's database hostname classifies as Supabase; Redis is configured. No production connection was made. Local mail uses the console backend, has no Resend configuration, and retains the configured old-domain sender address. Google, Discord, Riot and Epic credentials and Steam API enrichment are present locally; presence does not verify live applications, scopes, sender ownership or callbacks.

Read-only DNS on the audit date resolved `ownlobby.com` to `162.255.119.53`; `www.ownlobby.com` did not resolve. This is consistent with an incomplete cutover, not proof of exact Namecheap record types. The supplied Render targets were rechecked against [Render's Namecheap guide](https://render.com/docs/configure-namecheap-dns). Dashboard verification is still required before execution.

`render.yaml` says Starter while an older infrastructure document says Free and automatic deployments. The checked-in start scripts run **Daphne only**; worker/Beat/bot toggles do not prove a separate worker exists. The blueprint has `autoDeploy: false`. Confirm the live plan, build/start commands, auto-deploy setting, external worker and cron-job.org configuration manually.

Free Render services can spin down after inactivity and cannot attach persistent disks; an uptime ping is not a service-level availability guarantee. A separate paid staging web service/worker adds recurring compute costs. Current Starter compute is listed from approximately USD 7/month per instance; storage, database, Redis and transfer are separate. Verify pricing before purchase. [Free-service behavior](https://render.com/docs/free), [Render pricing](https://render.com/pricing).

## Media decision required

Avatars, team logos, tournament art, match/payment evidence and KYC documents use default storage. Certificates also have default-storage fields; the separate certificate S3 feature flags do not migrate every upload. Django serves local media only in DEBUG; WhiteNoise serves static assets, not production user media.

Cloudinary is already supported for public media, but default public image delivery is insufficient evidence of confidential KYC/payment access control. A private object store with expiring authorized delivery may be needed for sensitive documents. A paid Render disk alone also needs an appropriate serving/access-control design and backup plan. Inspect real object ACLs and any existing uploads, export recoverable backups, choose public/private storage policies, test a restart/redeploy and unauthorized raw URLs. Do not backfill, buy storage, change model fields or move files without a separate reviewed plan. Storage cost depends on retained data, requests, bandwidth and provider tier; no purchase was made.

## Production dependency gate

`pip-audit` ran in a separate ignored virtual environment; the application environment and requirements were not upgraded. The scan covers explicitly pinned production requirements with `--no-deps --disable-pip`; it does not prove complete transitive coverage, deduplicated CVE counts, severity or runtime exploitability. Raw vendor descriptions stay in ignored local evidence; the committed inventory contains public IDs/aliases/fix versions only.

Representative actionable findings include Daphne header-parser and unbounded WebSocket-frame advisories (fixed-version metadata lists 4.2.2), Django PostgreSQL/serializer advisories, and Pillow crafted-image decoder/resource-exhaustion advisories. Public uploads and websocket handling make parser/server findings important to evaluate. Reachability of every reported crypto/XML/PDF issue has not been established. Multiple supported release trains appear in fix metadata; choosing the numerically largest version is not a compatibility plan. In particular, PyPDF2's reported 3.9.0 fix refers to the successor pypdf ecosystem; do not pin an unavailable PyPDF2 version.

Start a separate, fully tested security-maintenance change with Django's supported 5.2 security train, Daphne and image-processing entry points, then handle authentication/crypto/network/parser compatibility and transitive constraints. Update both production and development pins consistently, run dependency resolution and `pip check`, repeat the audit, and exercise OAuth/JWT, uploads/PDF/certificates, Channels and financial regression tests on production-equivalent Linux/Python 3.12. The readiness fixes can be reviewed independently, but the combined release remains blocked until this remediation is complete or each residual finding is explicitly justified by the release owner. No such acceptance occurred here.

Vendor context was checked against [Django's security release notes](https://docs.djangoproject.com/en/6.0/releases/5.2.18/), [Daphne's changelog](https://github.com/django/daphne/blob/main/CHANGELOG.txt) and [PyPDF2's package history](https://pypi.org/project/PyPDF2/). Recheck current supported fixes when implementing the upgrade; scanner fix metadata can lag vendor releases.

## Validation record

Executed commands and final counts are summarized in `OWNLOBBY_RELEASE_HANDOFF.md`; full machine-local evidence is under ignored `Artifacts/readiness/`. Tests use guarded `deltacrown.settings_brand_qa`, loopback PostgreSQL port 55432, disposable `ownlobby_test`, memory mail/Channels/cache/broker and synthetic users only. Browser fixtures and sessions are not committed. No real transaction or live provider call was used for validation.

The previous reports remain historical evidence. In particular, their abbreviated explanation of all settings failures missed the duplicate privacy-row fixture; the actual trace was inspected and corrected here. Existing test shims and skips are disclosed rather than treated as production certification.

### Reproduce locally

Use a new local PostgreSQL database named `ownlobby_test`, apply the existing migrations with the guarded QA settings, and keep browser fixtures separate from unit-test data. Supply only local credentials. The QA module rejects a remote database or a different database name; never substitute production URLs.

```powershell
$env:DATABASE_URL='postgresql://<local-qa-user>@127.0.0.1:55432/ownlobby_unused'
$env:DATABASE_URL_TEST='postgresql://<local-qa-user>@127.0.0.1:55432/ownlobby_test'
$env:COMPETITION_APP_ENABLED='1'
$releaseTests=@(
  'apps.common.tests.test_release_readiness',
  'apps.siteui.tests.test_ownlobby_branding',
  'apps.siteui.tests.test_homepage_hero',
  'apps.siteui.tests.test_homepage_presentation',
  'apps.economy.tests.test_escrow_cached_balance',
  'apps.organizations.tests.test_membership',
  'apps.organizations.tests.test_leaderboard_service',
  'apps.user_profile.tests.test_settings_control_deck_smoke',
  'apps.user_profile.tests.test_settings_endpoints_smoke'
)
.venv/Scripts/python.exe manage.py test @releaseTests --settings=deltacrown.settings_brand_qa --keepdb --noinput
.venv/Scripts/python.exe -m pytest tests/integration/test_websocket_realtime.py apps/accounts/tests/test_email_sender.py apps/organizations/tests/test_cp_pipeline_e2e.py apps/user_profile/tests/test_game_passport_service_schema.py tests/tournaments/test_phase2_registration.py --ds=deltacrown.settings_brand_qa
npm ci --include=dev
npm run build
.venv/Scripts/python.exe scripts/verify_ownlobby.py --collect-static
```

The last command validates approved assets, route/settings contracts, syntax and templates, then exercises the real production static storage solely under ignored local QA output. It does not use production settings or run migrations. Browser logs/screenshots are local evidence, not a deploy step.
