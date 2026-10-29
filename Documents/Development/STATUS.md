# OwnLobby current status

Last development review: **2026-10-30 04:35 +06:00 (Asia/Dhaka)**, OL-04-B local/Linux implementation verification. OL-01 checks retain their 2026-10-29 dates below; they were not repeated. No deployment or production configuration/data change occurred. Isolated optimization evidence does not establish production improvement or full acceptance.

## Repository and deployment

| Item | State / provenance |
|---|---|
| Product / repository | OwnLobby / [rkRashik/DeltaCrown](https://github.com/rkRashik/DeltaCrown), default branch `master` |
| Verified master baseline | [`f6a27d7cb3dc6f12938d30868f36bb187723d368`](https://github.com/rkRashik/DeltaCrown/commit/f6a27d7cb3dc6f12938d30868f36bb187723d368), merged PR #40; clean local master safely fast-forwarded before creating `perf/ol04-b-remove-legacy-home-context-20261030` |
| Application source | Master application remains `f1f8d185` (lifecycle/mobile changes, not a Render fix). Unmerged [PR #41](https://github.com/rkRashik/DeltaCrown/pull/41) removes the unused homepage builder; implementation `cb2a3185`, test follow-up `c1c6325d`. No deployment performed |
| Latest independently verified Render live deployment | [`f1f8d18566723aa4e62875c20f7f6bc8dc4794e1`](https://github.com/rkRashik/DeltaCrown/commit/f1f8d18566723aa4e62875c20f7f6bc8dc4794e1), Render deploy `dep-dbhelq67bikc73eeefsg` succeeded **2026-10-29 12:46:51 +06:00**; verified with read-only [Render service](https://dashboard.render.com/web/srv-d6eubkngi27c738ieao0) deploy listing later that day. The `b7eb47f0` commit in Issue #37 was the preceding deployment, not the current live SHA. A live deploy status does not prove application journey acceptance. |
| Production | [ownlobby.com](https://ownlobby.com): six public routes and two approved public images passed bounded HTTP checks at 23:13-23:15 +06:00. Read-only Render follow-up reconfirmed live `f1f8d185`, Free plan and auto-deploy OFF; authenticated/private-media acceptance remains open |
| Documentation delivery | PRs #38, #39 and [#40](https://github.com/rkRashik/DeltaCrown/pull/40) merged. Historical diagnosis is retained; PR #41 updates the four canonical tracking documents with actual implementation evidence |

Read-only Render observation on 2026-10-29: the service remained on the Free plan with auto-deploy OFF. In a sampled 2026-10-29 08:30–12:55 UTC log window, no application-level errors or HTTP 5xx request entries were returned; this is not a comprehensive availability test or a post-containment login/storage smoke. No production settings were changed.

## Completed work with bounded evidence

- PRs [#30](https://github.com/rkRashik/DeltaCrown/pull/30), [#31](https://github.com/rkRashik/DeltaCrown/pull/31), [#32](https://github.com/rkRashik/DeltaCrown/pull/32): merged media-throttle isolation, bounded S3 streaming, public Redis fallback and Community static-delivery guards. Merged code does not establish current latency or full media acceptance.
- PR [#33](https://github.com/rkRashik/DeltaCrown/pull/33): merged synthetic account/profile/launch QA coverage.
- PR [#35](https://github.com/rkRashik/DeltaCrown/pull/35): password-reset form/error fix merged. Issue #37 records owner-verified Google sign-in/password reset following the canonical-origin configuration update.
- PR [#36](https://github.com/rkRashik/DeltaCrown/pull/36): sanitized homepage phase telemetry and selected acceptance checks merged. Issue #37 reports Linux CI and public-route smoke passing at that time. These tests were not rerun in OL-DOC-01.
- The initial documentation task inspected lifecycle/mobile source and regression tests without a fresh test execution or deployed journey acceptance. The newer master merge adds documentation only; current OL-01 checks are recorded separately below.

## Active work and immediate next task

**[OL-01](BACKLOG.md#ol-01) remains P0, VERIFYING.** A 2026-10-29 audit established an externally reachable Data API authorization risk before containment. The owner subsequently reports manual containment applied: Dashboard Overview shows **Enable Data API = OFF**, and Settings shows **Data API is disabled**.

| OL-01 sub-gate | State |
|---|---|
| Containment configuration | Applied, owner-reported 2026-10-29; current provider toggle not independently re-read through available tools |
| External endpoint denial | Observed for both enabled credential types at 23:12 +06:00; HTTP 503 / API connection-schema-cache failure. Disabled-specific cause remains unconfirmed |
| Application compatibility smoke | Six public routes and two public images pass; existing-account and confidential-media browser checks pending |
| Permanent database privilege hardening | Pending separate reviewed approval, implementation and verification |
| Sensitive-data extraction / exploitation | Not established; no breach claim |

Prior source inspection found no required database Data API consumer. Django uses PostgreSQL connections; Supabase Storage APIs are separate. The constant-only direct DB check below adds scoped connectivity evidence, not proof of every authenticated feature or private Storage operation. Do not re-enable Data API or change RLS/grants.

**Security follow-up:** close remaining OL-01 provider-state/private-browser gaps and obtain separate approval for the [hardening proposal](BACKLOG.md#ol-01-permanent-hardening-proposal-not-executed). These gates remain open independently of the owner-requested performance investigation below.

## OL-03/04-A diagnosis 2026-10-30

[Evidence report and implementation proposal](tasks/OL-03-04-A.md): no source optimization, production DB/Redis command, HTTP load or service change. Render reads reconfirmed live `f1f8d185`, Free Singapore, one instance and Celery OFF.

- For 29 October 12:00-18:00 UTC, slow-only phase observations have medians context **1938 ms** (23), extras **2383 ms** (18), render **1787 ms** (39), hero **919 ms** (1). Counts/medians are thresholded above 500 ms, not full requests or percentiles.
- Returned memory samples peak at **312.4 MiB / 512 MiB**; CPU samples do not establish saturation of the **0.15-core** allocation. Short spikes remain unmeasured. Earlier health failures predate the current deploy; no returned event lies inside this window. No matching error/timeout entries were returned.
- Source plus isolated template/SQL-dispatch simulation confirms unused legacy view context, unused common homepage processor work and a navbar cached-False query. A synthetic 11-game/otherwise-empty scenario recorded **71 cold guest / 1 warm guest / 24 warm authenticated dispatches**. No SQL was executed; no local PostgreSQL service was available. Actual production query counts/time and Redis hit rate/RTT are unknown.
- **Historical first proposal: OL-04-B**, remove only the unused legacy view-builder invocation. All three synthetic output comparisons matched after fixed CSRF; seven existing mocked cache/telemetry tests passed. No optimization occurred during that diagnostic task. The later owner-authorized implementation/isolated verification follows; production benefit remains unmeasured.

## OL-04-B isolated verification 2026-10-30

**VERIFYING / PR review, no deployment.** Minimal view change: remove the legacy import/call, use a new `context = {}`, then retain all active builders. Legacy `context` telemetry disappears because that work no longer runs; extras/hero/sections/presentation/render timing remains. No replacement measurement is manufactured. No template, authentication or media policy changed.

Local environment: Windows, Python 3.13.15, Django 5.2.8, PostgreSQL 18.6, loopback-only disposable `ownlobby_test`, memory cache and synthetic fixtures. Owner `.env` loading disabled; QA settings reject remote databases. Combined rerun measurements at approximately **04:21 +06:00** compare the actual baseline `home()` extracted from immutable Git `f6a27d7c`, with the same fixture set and real ORM/templates/processors. Cold/warm mean data-cache state, not process wake-up or a new database connection. SQL time measures driver execution including loopback waits; no production data, remote Redis latency or SQL text is recorded.

| Fixture / role | Cold queries before → after | Cold SQL ms before → after | Warm queries before → after | Warm SQL ms before → after |
|---|---:|---:|---:|---:|
| Empty guest | 68 → 54 | 42.650 → 34.020 | 1 → 1 | 0.760 → 0.541 |
| Populated guest | 80 → 64 | 46.185 → 36.657 | 1 → 1 | 0.430 → 0.547 |
| Populated player | 105 → 89 | 60.400 → 50.087 | 21 → 21 | 8.027 → 7.434 |
| Populated organizer | 97 → 81 | 57.169 → 44.988 | 13 → 13 | 5.209 → 5.216 |
| Populated registered player | 98 → 82 | 56.242 → 44.577 | 14 → 14 | 5.460 → 5.584 |
| Populated team manager | 107 → 91 | 53.170 → 49.153 | 23 → 23 | 7.655 → 8.226 |

Six new regression tests PASS: full HTML byte equality after fixing only synthetic time/CSRF randomness; desktop/mobile sections, directory links, SEO/artwork and role-specific hero retained; zero legacy/singleton calls from the new view; no personalization of a shared extras object. Guarded cache read/write timeouts also preserve baseline output (15 cold queries removed in those populated fallback cases). This is simulated timeout handling, not a real Redis outage. The separate common processor has unguarded cache access; a whole-backend outage remains outside this change.

Cold populated extras remains 33 queries; render remains 31 guest / 36 player-manager / 37 organizer-registered. Warm extras is zero queries in both versions. The removed legacy phase contributed 16 queries / 8.878-10.574 ms driver time (25.268-28.124 ms wall time) in the populated normal-cache samples. Extras/render wall samples fluctuate in both directions, not a measured improvement in those phases; timings are single noisy observations. This does not prove production p50/p95 or predict a 16-query saving on every production request. Shared waits may shift phases. Expect reduced redundant work/allocation without additional services/cost; actual production benefit remains unmeasured.

**Combined local rerun: 161 tests PASS in 51.003 s** (new regressions, existing hero/presentation/phase/cache/governed-media/hybrid/private-profile suites). Existing-suite initial result was 154/155 PASS; one stale empty-state copy assertion failed identically using the original baseline view. Only its expectation was corrected to current approved desktop/mobile copy. An earlier parallel local setup caused a disposable migration collision; runners were stopped and migration setup resumed serially. No application schema/migration file or production DB was changed. QA-only local-filesystem warning `siteui.W001` is expected and does not describe production storage.

**Linux run [#61 PASS](https://github.com/rkRashik/DeltaCrown/actions/runs/40965238972)**, code head `c1c6325dbf5384d4baf51e021cd1960c33a1da39`, Ubuntu 24.04 / Python 3.12 / disposable PostgreSQL 16, completed approximately 04:34 +06:00. All job steps executed successfully, including 114 homepage tests (4.950 s), existing security/media/recovery/account/tournament suites, startup/native/HTTP-WebSocket checks, frontend build and static verification. Query counts match the local table; Linux populated guest SQL was 36.663→28.832 ms cold, 0.325→0.356 ms warm. These remain synthetic single observations. The unchanged six-route read-only live smoke also passed; it exercised the existing production version, not this unmerged optimization.

Separate CI correction `a9a87bc6` removes the obsolete named-branch allowlist; master-target PRs retain synthetic PostgreSQL, no production database secrets and existing security suites. The initial run #60 was superseded, not accepted as success. This documentation revision adds no application changes; inspect the latest PR #41 head check before merging. No skipped/pending run is PASS.

Rollback commits/order and next approval gate: [OL-04 backlog](BACKLOG.md#ol-04). Do not deploy automatically. OL-03 remains open; OL-04 remains VERIFYING; OL-01 is unchanged.

Documentation links/Development anchors pass (74 documents / 361 links, no active failures); 47 historical findings and the same three root-placement hygiene failures remain. Only the eight intended source/test/workflow/canonical-document paths are changed; ignore/publication policy and historical investigation remain untouched. Task-created temporary QA cluster/logs were removed after recording measurements; earlier investigation artifacts and the 435 protected owner Documents files remain. No real-device visual QA, production Redis failure, authenticated production journey or private Storage smoke was performed in this task.

## OL-01 verification 2026-10-29

Environment: local Windows read-only clients against owner-approved production targets; existing enabled public credential types and securely stored application database configuration. No real-user login, application-row SQL, modification probes, production writes, deployments or configuration changes. HTTP checks were sequential with spacing; no load/performance test.

| Acceptance item | Result | Evidence and limitation |
|---|---|---|
| A. Provider configuration disabled | BLOCKED for independent reinspection | Owner dashboard attestation remains OFF/disabled. Available project metadata does not expose the toggle; no fresh dashboard/management configuration read was possible. No missing-key response is used as proof |
| B. Previously reachable request denied | PASS, bounded observation | Both existing enabled legacy-anonymous and publishable credentials received HTTP 503 for the approved zero-row request; no request accepted. Category: API connection/schema-cache failure, not a disabled-specific message. Does not independently prove A or durable denial of every API surface |
| C. Public routes operational | PASS | Health returned 200 JSON with expected status; home, tournaments, teams, community and signup returned 200 HTML with expected document shape on the production host |
| D. No new attributable application errors | PASS, bounded observation | After workspace confirmation, read-only Render queries for 08:35-17:47:25 UTC returned no error-level app entries, targeted DB/PostgREST failure entries or HTTP 500/502/503/504 request entries. Recent app activity confirms logs are available. No disablement-attributable error observed; this is not comprehensive availability/causality proof |
| E. Django direct PostgreSQL connectivity | PASS, scoped | Existing application DB connection completed constant-only SELECT in an explicit read-only transaction at 23:15 +06:00; zero application rows. Local client, not Render process. Successful DB-backed public artwork delivery corroborates the source path; health alone does not check DB |
| F. Private Storage compatibility | BLOCKED / pending owner browser smoke | Public artwork succeeded; confidential-file reads, private-user authorization and Storage write paths were not tested. Previous private-media evidence remains historical |
| G. Permanent hardening separately gated | PASS, proposal only | BACKLOG covers table/sequence/default ACL scope, creator/application/provider roles, isolated migration tests and exact rollback. No permissions changed; implementation remains pending approval |

Public image evidence: a homepage-referenced brand SVG returned 206 and a valid signature; a previously approved public game artwork sample returned 200 PNG and a valid signature. Only 256 bytes per successful sample were inspected. The first game-image request used a restrictive Accept header and returned 406; a corrected supported header succeeded. No private image or signed URL was requested.

Render follow-up window: **2026-10-29 14:35-23:47:25 +06:00** (08:35-17:47:25 UTC), after the owner containment report; the exact disable timestamp was not independently recorded. Error-level, targeted failure-text and explicit request-status queries returned no matches and no further pages. A separate bounded 30-entry plain-text error sample included zero-error lifecycle summaries and client-request/probe warnings; that broad sample had more pages and is not an exhaustive warning audit. The sample did not establish a database/API failure. Raw logs, request details and identifiers are not published. Latest live deploy remains `dep-dbhelq67bikc73eeefsg` / `f1f8d185`; no deploy or setting change was performed.

The first constant-only DB check connected but the pooler did not retain the startup read-only option. It made no writes or application-row queries. A corrected explicit read-only transaction was verified before the final SELECT and passed. No Django startup/test suite was run against production.

The API error denotes a PostgREST connection/schema-cache failure ([official error reference](https://docs.postgrest.org/en/stable/references/errors.html)); refusal is therefore recorded separately from provider configuration. Raw responses, endpoint/object inventory, credentials and reproduction steps are absent. Detailed evidence remains owner-controlled; no approved private URL supplied.

Owner browser smoke still needed: manually use an existing account to confirm login and current profile/tournament/team views, read one existing authorized confidential file, and confirm an unrelated/guest session cannot read it. Do not create users, upload/delete files, submit forms or financial actions. Record only sanitized private results; keep Data API disabled.

## Other blockers and limitations

- OL-02: Issue #37 reports a Django signing-key warning; strength/disposition remains unverified. Never print/rotate the key merely to clear a warning. PR #41 fixes the [Linux workflow](../../.github/workflows/ownlobby-linux-smoke.yml) named-branch coverage gap; verify the actual head run, not historical/skipped results.
- OL-03/04: historical Render Free constraints are 512 MiB and 0.15 CPU in Issue #37. Homepage observations include context 2975 ms, extras 3147 ms and render 1945/3200/1900 ms from separate requests. They are not averages, a fresh baseline or proof of root cause.
- OL-05/07: slow image delivery is reported; complete root cause remains unverified. Existing bounded streaming is not an image-size/CDN solution. Private media must remain private.
- OL-06: R2 is not approved. Owner requires minimal costs, warnings near 8/9 GB and evaluation of upload blocking below the free allowance, including operations, backups and ongoing billing; no hard-cap guarantee.
- OL-08: Celery remains OFF by owner direction. Issue #37 reports a healthy authenticated five-minute lifecycle cron at its audit date; other async jobs and current cron health remain unverified.
- OL-09/10/13: complete eFootball journey, real mobile/accessibility acceptance, fresh verified signup and non-allowlisted Google sign-in remain open. Google publishing/branding and release acceptance need owner action.
- OL-11/12: rebrand/SEO code exists; full visual coverage, Search Console ownership/submission and indexing are not certified.
- Independent full provider/platform recovery and current restore objectives are not established by earlier local/application-schema restore evidence.

## Evidence provenance and confidentiality

| Reference | Use and limitation |
|---|---|
| Master SHA and source links above | Source-verified; not deployment proof |
| [Issue #37](https://github.com/rkRashik/DeltaCrown/issues/37) and linked PRs | Historical deployment/QA/telemetry and owner-action record; reviewed during OL-DOC-01 |
| Owner's OL-DOC-01 update, 2026-10-29 | Data API disabled dashboard attestation; no screenshot or secret copied into Git |
| Owner-held OL-01 audit, 2026-10-29 | Sanitized security conclusion only. Approved private evidence URL not supplied; request privately, never invent a link or attach reproduction details to this public repository |
| Older root engineering/release/media documents | Dated source/design/test history; superseded status claims must not be treated as present operations |

## Documentation verification baseline

Before OL-DOC-01 edits: documentation checker passed for 63 documents / 177 local links, with zero active failures and 47 historical findings. Hygiene already failed on three tracked root files absent from its allowlist: `OWNLOBBY_LAUNCH_CUTOVER.md`, `OWNLOBBY_RECOVERY_CANDIDATE_CHECKLIST.md`, `OWNLOBBY_RECOVERY_CUTOVER.md`. Preserve them; do not quietly broaden the root allowlist or move them to make this task green.

Initial OL-DOC-01 implementation checks: 73 documents / 343 local links, zero active failures, unchanged 47 historical findings; the same three baseline hygiene findings remained with no new violation. Development heading anchors and narrow ignore boundaries passed. All 435 pre-existing owner Documents files had unchanged aggregate content/path fingerprints. These are the original documentation-delivery checks, not the later Render observation or current OL-01 verification. No application test suite was run during OL-01; its bounded live checks are recorded above.
