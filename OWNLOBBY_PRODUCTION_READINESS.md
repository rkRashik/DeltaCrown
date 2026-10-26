# OwnLobby production readiness

> Current media disposition: [final engineering handoff](OWNLOBBY_FINAL_ENGINEERING_HANDOFF.md). All 53 concrete upload fields now have opt-in governed routing, validation and authorized delivery. `siteui.E002`?`E006` additionally enforce governed configuration, distinct private origins, verification and field-policy coverage. Actual cloud ACLs/persistence, recovery and Linux/Cairo are still unverified; production remains No-Go.


Audit date: 2026-10-26. Rebrand baseline: `ece37c2fa5fc9f81305375684d2c8e606c9e2c88`. Readiness checkpoint: `c525ffb7be6ebca1c17d3bdd07e6650b6d738ffb`. Branch: `feature/ownlobby-production-readiness`.

## Release decision

**No-Go for production deployment or domain cutover today.** Local corrections and automated results support an isolated staging candidate. Linux/runtime validation of the implemented Twisted HTTP backport, durable/private media delivery, actual Render configuration, recoverable backups, mail delivery and provider callbacks remain release gates. No residual production risk has been accepted on the owner's behalf.

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
| P1 | Phase 3 fixed 191 underlying dependency advisories. Phase 4 packages the official HTTP security hunk on stable Twisted 26.4.0+ownlobby.1; six base-version findings remain visible, one addressed by backport and five affecting unconfigured protocols. | **HTTP correction locally validated; Linux/runtime gate open.** Clean install/pip check, five parser tests, real Daphne checks, 238 upstream HTTP tests pass. Normal scanner skips the local version; mandatory base scan covers every distribution. See OWNLOBBY_SECURITY_CLOSURE.md. |
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

## Phase 4 security/runtime/OAuth update (2026-10-26)

Current local branch: feature/ownlobby-security-runtime, based on a7f3e3c0063db8487b98a0baf84a42f39067c1c8. No remote push/deployment occurred under the latest owner instruction.

- Official Twisted CR/LF header patch is reproducibly packaged on the stable base and passes local byte/network/upstream tests. Five unused-protocol vulnerabilities remain installed and disclosed. No unsupported runtime monkeypatch or prerelease. Full details: [security closure](OWNLOBBY_SECURITY_CLOSURE.md).
- **All seven baseline OAuth failures are resolved.** Corrected stale fixtures/relationships, a real Steam redirect defect, unsafe Google next handling, Steam signed assertion/nonce binding and a provider-ownership race. Final OAuth/ownership suite **47 pass**, including three PostgreSQL races and Discord state negatives. See [root causes](OWNLOBBY_OAUTH_RELIABILITY.md).
- Final focused set **219 pass/one Cairo skip**; workflow/offline storage **88 pass/nine existing skips**; upstream HTTP **238 pass/five skips**. No observed passing-test regressions. 69 approved assets unchanged; frontend/static builds and template baseline preserved.
- **Linux/Python 3.12/native Cairo gate remains open.** No Docker/WSL/VM execution environment was available; native smoke command fails in Windows cairocffi loading. Wheel availability is not parity. See [real environment evidence](OWNLOBBY_LINUX_PARITY.md).
- Full media audit: **55 registered/53 concrete fields plus rich-text uploads**; shared default backend does not prove private delivery. Safe MIME, Docker-context and stream-reading prerequisites implemented, but provider selection, upload-path enforcement, private authorization, durable objects and tested restoration remain release blockers. See [Phase 5 plan](OWNLOBBY_MEDIA_ARCHITECTURE.md).
- New deploy-check evidence: QA policy produces 385 warnings (379 schema-generation, five test-security, one media). Synthetic production policy retains **siteui.E001**/W001 and the 379 schema warnings. No suppression. Schema-warning baseline was not compared; schedule triage, not a claimed regression or false-green deploy check.

The older Phase 3 section below is historical evidence; its open HTTP and seven-OAuth work instructions are superseded by this implemented result. Native-runtime, storage/recovery, actual staging/provider/mail/worker and separate infrastructure/cutover approval gates remain. Production: **No-Go**. Local code is a candidate for review and approved isolated Linux validation, not a certified staging release.

## Production dependency gate - Phase 3 historical baseline (2026-10-26)

Targeted upgrades are now implemented locally. Both requirements sources resolve; a separate clean production install passes pip check and Django imports. Full resolved and clean installed audits agree: **308 raw entries / 197 underlying advisories / 29 packages reduced to six advisories in Twisted 26.4.0; 191 underlying advisories fixed.** No suppression or production changes occurred. See [security decisions and matrix](OWNLOBBY_DEPENDENCY_SECURITY.md) and [executed validation](OWNLOBBY_DEPENDENCY_VALIDATION.md).

**P1 still open:** GHSA-q7qq-6mhp-9rc4 / CVE-2026-115877 is a public HTTP parser risk; bare CR/LF headers remain accepted in a bounded local Daphne transport test. Latest verified stable Twisted is 26.4.0; metadata lists only 26.10.0rc1 as fixed. No prerelease or unreviewed monkeypatch was adopted. Obtain and test a stable upstream fix or a separately reviewed minimal backport before deployment. Five other installed Twisted findings affect unconfigured Telnet/IMAP/IRC/XMPP services and remain explicitly tracked; they are not scanner-suppressed.

**P1 runtime evidence still missing:** Linux/Python 3.12 execution and Cairo native rendering. 129 Linux CPython 3.12 wheels are available; Cloudinary/pycairo need source builds. Windows results do not establish Linux parity. Final focused suite: 211 pass/one Cairo skip; workflow suite 60 pass/one existing fixture skip. Expanded OAuth/offline storage: 38 pass/seven failures/eight gated skips on both original and upgraded libraries, with identical failing node IDs. Those baseline OAuth failures require investigation before release. No observed previously passing regression in compared suites.

The table above is updated for this Phase 3 result; historical Phase 2 audit evidence is preserved in the original inventory. The dependency gate is **not resolved**, and no owner risk acceptance is implied. All media, recovery, staging, mail/provider and cutover blockers elsewhere in this document remain in force. Two mobile homepage accessibility violations found in Phase 3 (contrast and scrollable-region focus) remain P2; no visual redesign was included.

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
