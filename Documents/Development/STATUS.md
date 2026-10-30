# OwnLobby current status

Last development review: **2026-10-30 16:15 +06:00 (Asia/Dhaka)**, OL-INC-01 read-only incident investigation and isolated diagnostics. **Do not deploy master.** Production was rolled back by the owner; this investigation made no production changes. OL-01 and OL-04-B evidence below retains its original dates and limitations.

## Repository and deployment

| Item | State / provenance |
|---|---|
| Product / repository | OwnLobby / [rkRashik/DeltaCrown](https://github.com/rkRashik/DeltaCrown), default branch `master` |
| Verified master baseline | [`7e07d6835f92a39a7cc4fb9ef3666f008a241b12`](https://github.com/rkRashik/DeltaCrown/commit/7e07d6835f92a39a7cc4fb9ef3666f008a241b12), PR #41 merged 2026-10-30 06:19:08 +06:00; clean local master fast-forwarded before `docs/ol-inc-01-navigation-hang-20261030` |
| Application source | Merged [PR #41](https://github.com/rkRashik/DeltaCrown/pull/41) removes only the legacy homepage import/call from runtime code. Startup, dependencies, ASGI, database/cache configuration and teams view are unchanged from `f1f8d185`. Master is held from deployment pending incident review |
| Latest independently verified Render live deployment | [`f1f8d18566723aa4e62875c20f7f6bc8dc4794e1`](https://github.com/rkRashik/DeltaCrown/commit/f1f8d18566723aa4e62875c20f7f6bc8dc4794e1), rollback deploy `dep-dbhufde7bikc738137sg`, completed **2026-10-30 06:42:19 +06:00**. Read-only [Render service](https://dashboard.render.com/web/srv-d6eubkngi27c738ieao0) deployment/event evidence confirms the rollback; owner reports navigation recovered. This is not full journey acceptance |
| Production | [ownlobby.com](https://ownlobby.com): historical six-route/two-image smoke passed **2026-10-29** 23:13-23:15 +06:00. OL-INC-01 independently reconfirmed the rollback artifact, Free plan and auto-deploy OFF through provider reads; no fresh production HTTP smoke was run by this investigation. Authenticated/private-media acceptance remains open |
| Documentation delivery | PRs #38, #39 and [#40](https://github.com/rkRashik/DeltaCrown/pull/40) merged. Historical diagnosis is retained; PR #41 updates the four canonical tracking documents with actual implementation evidence |

Read-only Render observation on 2026-10-29: the service remained on the Free plan with auto-deploy OFF. In a sampled 2026-10-29 08:30–12:55 UTC log window, no application-level errors or HTTP 5xx request entries were returned; this is not a comprehensive availability test or a post-containment login/storage smoke. No production settings were changed.

## Completed work with bounded evidence

- PRs [#30](https://github.com/rkRashik/DeltaCrown/pull/30), [#31](https://github.com/rkRashik/DeltaCrown/pull/31), [#32](https://github.com/rkRashik/DeltaCrown/pull/32): merged media-throttle isolation, bounded S3 streaming, public Redis fallback and Community static-delivery guards. Merged code does not establish current latency or full media acceptance.
- PR [#33](https://github.com/rkRashik/DeltaCrown/pull/33): merged synthetic account/profile/launch QA coverage.
- PR [#35](https://github.com/rkRashik/DeltaCrown/pull/35): password-reset form/error fix merged. Issue #37 records owner-verified Google sign-in/password reset following the canonical-origin configuration update.
- PR [#36](https://github.com/rkRashik/DeltaCrown/pull/36): sanitized homepage phase telemetry and selected acceptance checks merged. Issue #37 reports Linux CI and public-route smoke passing at that time. These tests were not rerun in OL-DOC-01.
- The initial documentation task inspected lifecycle/mobile source and regression tests without a fresh test execution or deployed journey acceptance. Its then-current master merge added documentation only; subsequent PR #41 and OL-INC-01 release history are recorded separately.

## Active work and immediate next task

**OL-INC-01 is P0 / VERIFYING:** investigation complete, production attribution and remediation acceptance remain open. Review the evidence below, then authorize OL-INC-01-A: a narrowly scoped ASGI dependency correction and cancellation regression tests. No homepage revert or production change is justified automatically. OL-03 remains IN_PROGRESS and OL-04 VERIFYING; preserve independent OL-01 gates.

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

## OL-INC-01 incident investigation 2026-10-30

**Most likely mechanism: cancellation-triggered ASGI event-loop blockage while synchronous work remains outstanding; moderate confidence for this production incident.** The mechanism is reproduced locally in both releases. Production has no captured thread stack or correlated database wait evidence, so neither the exact blocking operation nor a permanent deadlock is proven. Owner clarification: page HTML did not arrive; cross-browser/device scope remains unclear. An image-only explanation is insufficient.

### Verified timeline and evidence

All event times below are **2026-10-30 Asia/Dhaka (+06:00)**. Read-only Render queries covered events 00:15-01:00 UTC, app logs 00:20-00:50 UTC and resource samples 00:15-00:55 UTC. Relevant embedded log timestamps were checked; buffered historical access lines were not treated as current requests.

| Time | Confirmed evidence / interpretation |
|---|---|
| 06:19:08 | GitHub PR #41 merged as `7e07d683`; final PR head was `c781e88a`, not the earlier code-only head |
| 06:24:27 / 06:27:20 | Deploy `dep-dbhu7euk1f9s73e8fmgg` started / succeeded. This was a runtime incident after a successful build/deploy |
| 06:27:34-36 | New process logged extras 5477 ms and render 1939 ms; later render phases also completed. These are slow-only phases, not request averages |
| 06:34:49.578 | Daphne warned that a disconnected `/teams/` application task took too long to shut down and cancelled it. This warning does not itself mean the OS process was killed |
| 06:35:30-06:39:00 | Returned 30-second CPU observations were near idle, at most 0.001382 cores. No sustained CPU saturation is established for the silent interval |
| 06:38:50.400 / .936 | Platform log reports instance restarted; provider event reports `server_failed`, internal port 10000 TCP timeout. Sub-second ingestion ordering is not a causal ordering guarantee |
| 06:39:02 / 06:39:35 / 06:39:39 | Same-release startup / listening / `server_available`, all before rollback began |
| 06:40:43-45 | Same `7e07d683` release logged extras 4507 ms and render 1992 ms after restart. Demonstrates application execution, not full navigation acceptance |
| 06:41:25 / 06:42:19 | Owner-triggered rollback started / became live at `f1f8d185`; owner subsequently reports working navigation |

Render remains Free/Singapore, one configured instance, auto-deploy OFF, Celery worker OFF. Actual start command is `bash start.sh`; live `healthCheckPath` is empty (TCP), not an independently verified HTTP `/healthz/` check. Startup logs confirm HTTP timeout 3600 s; source defaults application-close timeout to 5 s. Build logs confirm Django 5.2.18, asgiref 3.10.0 and Daphne 4.2.3. Same pins exist in both releases.

Returned memory series peak at **264.6 MiB for the incident instance**, 335.0 MiB for the preceding instance and 318.3 MiB for the rollback instance, versus 512 MiB. No OOM crossing is evidenced. CPU reaches the 0.15-core limit at one startup sample (06:27:30); sampled headroom later cannot rule out brief spikes. Samples are not instantaneous peaks or whole-request percentiles. HTTP latency/count series and request-log query returned no data; no traffic rate or p95 claim follows.

### Source findings and unresolved alternatives

- **Application regression:** only runtime diff is the three-line homepage removal. `/teams/`, middleware, scheduler, dependencies and startup are unchanged. No direct PR #41 regression was demonstrated; changed timing/cache state could still influence a trigger. Rollback also replaces the process, so recovery does not isolate code causality.
- **ASGI/sync boundaries:** Django runs sync views/ORM in request-scoped thread-sensitive executors. Ordinary synchronous SQL is not automatically event-loop blocking. However, pinned asgiref's async context exit performs a blocking executor shutdown. The upstream [fix](https://github.com/django/asgiref/pull/563) and [release history](https://github.com/django/asgiref/blob/main/CHANGELOG.txt) identify the corresponding cancellation/deadlock class. `ASGI_THREADS=2` in startup is not proof of a global two-request concurrency cap; inspected request executors are allocated per context.
- **PostgreSQL:** pooled defaults use `CONN_MAX_AGE=0`, health checks and 5 s connect timeout. No application-configured SQL statement deadline was found. Connect timeout does not bound an already-running query/lock/pooler wait. Historical production SQL, locks and pooler wait attribution were unavailable; no production queries were issued in this task.
- **Redis:** individual source defaults are 2 s connect/read timeouts with timeout retry; safe-cache cooldown is 60 s. Teams/global processors also use direct cache calls. No matching Redis exception was observed, but that does not rule out latency. No keys, flushes or live cache probes were used.
- **Scheduler:** reminder sweeps run in a daemon thread (60 s interval, 8 s initial delay), not directly on the ASGI loop; source and startup are identical. A sweep can query/update/send notifications normally. No incident sweep-duration/lock evidence identifies it as the culprit; it was disabled in isolated QA. The separate lifecycle cron must not be conflated with this thread.
- **Render/browser:** a confirmed restart explains recovery without changing application code. Startup delays are visible, but do not explain the later shutdown warning by themselves. Browser/network cancellation could be a trigger; a browser-only fault does not explain the provider's TCP failure. No HAR, production thread dump or browser/device comparison was available.

### Isolated verification and limits

Windows / Python 3.13.15 / **Django 5.2.18, asgiref 3.10.0, Daphne 4.2.3**, PostgreSQL 18.6 on loopback, memory cache, synthetic players/game/tournaments/team. Owner dotenv was disabled and non-loopback sockets rejected. Disposable QA migrations/fixtures are local only. Exact old/new `home()` functions were loaded from Git; all other runtime source is identical. This is not Linux/Render resource parity, real Redis/Supabase latency, private-media QA or a production performance measurement.

| Diagnostic | Observed result |
|---|---|
| Each release: six sequential requests and a four-request concurrent batch through Django ASGI/full middleware | All **20 responses HTTP 200** across home, teams, tournaments, community and health; no navigation hang. First/warm homepage observations: old 456.6/52.5 ms, new 347.2/44.3 ms; single synthetic samples, not an improvement estimate |
| Short synthetic query cancellation control, each release | Both completed; an initial short wait did not reproduce a hang |
| Real localhost Daphne, deliberately delayed synthetic query plus disconnected client | Both releases produced two unrelated health-request timeouts at a 2 s client bound, followed by recovery when finite work completed. New-release repeat reproduced the same result |
| Captured local stack during the stall | Event-loop thread in `ThreadSensitiveContext.__aexit__` -> executor `shutdown` -> thread `join`; synchronous work still outstanding. This proves local loop blockage, not the missing production stack or an infinite deadlock |
| Same delayed query with client remaining connected, new release | All five health probes HTTP 200, 4.8-19.0 ms; ordinary SQL waiting alone did not reproduce the stall |
| Separate ignored asgiref **3.12.1** diagnostic install, new release and same disconnect case | All five health probes HTTP 200 in each of two runs (3.4-22.4 ms / 3.8-16.6 ms); event-loop snapshot remained in normal polling. Tracked pins/application were not changed; this is not full candidate release acceptance |

Task-local synthetic harness/results are ignored under `Artifacts/ol-inc-01-20261030/` and unavailable in a fresh clone; no production logs or credentials are committed. The disposable database was stopped and its cluster/dependency copies removed after measurement; small synthetic evidence remains locally. Initial harness setup omitted CI's competition flag and was corrected before measurements. No production request load, database write, configuration change, deployment or rollback was performed by this investigation.

### Proposed next implementation and release gates

**OL-INC-01-A (proposal, not executed):** review a consistent asgiref pin containing the upstream fix (3.12.1 is the isolated tested candidate) in both requirements files, with bounded subprocess regression tests for slow sync work, disconnect/cancellation and unrelated request responsiveness. Do not rewrite the homepage, async-convert the ORM, lower timeouts blindly or increase workers as part of this fix. It should reduce the demonstrated cross-request blocking risk; it does not make slow SQL/Redis work fast or prove production causality.

- Require Linux/Python 3.11 parity, production-pinned Django/Daphne, isolated PostgreSQL, old/new and connected/disconnected controls; repeat bounded concurrent cancellation cases. Proposed local gate: no unrelated probe timeout at 2 s, no sustained event-loop lag above 250 ms, no stuck threads/connections after work completes. Calibrate on an idle runner; these are proposed gates, not newly measured production SLAs.
- Run existing homepage/hero/cache/auth/private-media/security/native/HTTP-WebSocket suites and ensure CI executes on the reviewed SHA. Verify bounded thread/RSS growth and cleanup; asynchronous shutdown can add executor/thread overhead, material on 512 MiB. No paid capacity assumed.
- Add only approved bounded observability if production attribution is required: loop lag, in-flight/cancelled request counts, route-name request IDs, aggregate DB execution/connection/cache wait time and scheduler duration. No SQL/params, raw URLs, user IDs, cache keys, signed URLs or stack locals. Existing slow-only homepage logs and warning-level request logs cannot locate the original wait.
- Keep master deployment on hold. After owner approval, test an immutable candidate artifact, prepare known-good `f1f8d185` rollback, and deploy only the reviewed SHA with low-frequency route/health and owner browser checks. A restart-only control requires separate approval; none was performed here. Provider [rollback semantics](https://render.com/docs/rollbacks) include process/configuration considerations, so privately compare non-secret settings rather than assuming a code-only rollback.
- Roll back the exact future dependency/test commit (record its SHA when created) and, only if approved, the release artifact. No migrations, cache deletion, Redis reset, media/secret changes or worker configuration changes are needed. `f1f8d185` also contains the reproduced risk; rollback is containment, not permanent correction.

## OL-03/04-A diagnosis 2026-10-30

[Evidence report and implementation proposal](tasks/OL-03-04-A.md): no source optimization, production DB/Redis command, HTTP load or service change. Render reads reconfirmed live `f1f8d185`, Free Singapore, one instance and Celery OFF.

- For 29 October 12:00-18:00 UTC, slow-only phase observations have medians context **1938 ms** (23), extras **2383 ms** (18), render **1787 ms** (39), hero **919 ms** (1). Counts/medians are thresholded above 500 ms, not full requests or percentiles.
- Returned memory samples peak at **312.4 MiB / 512 MiB**; CPU samples do not establish saturation of the **0.15-core** allocation. Short spikes remain unmeasured. Earlier health failures predate the current deploy; no returned event lies inside this window. No matching error/timeout entries were returned.
- Source plus isolated template/SQL-dispatch simulation confirms unused legacy view context, unused common homepage processor work and a navbar cached-False query. A synthetic 11-game/otherwise-empty scenario recorded **71 cold guest / 1 warm guest / 24 warm authenticated dispatches**. No SQL was executed; no local PostgreSQL service was available. Actual production query counts/time and Redis hit rate/RTT are unknown.
- **Historical first proposal: OL-04-B**, remove only the unused legacy view-builder invocation. All three synthetic output comparisons matched after fixed CSRF; seven existing mocked cache/telemetry tests passed. No optimization occurred during that diagnostic task. The later owner-authorized implementation/isolated verification follows; production benefit remains unmeasured.

## OL-04-B isolated verification 2026-10-30

**Historical pre-deployment verification; OL-04 remains VERIFYING.** PR #41 was subsequently merged/deployed and owner-rolled-back; OL-INC-01 above supersedes its release disposition, not these test results. Minimal view change: remove the legacy import/call, use a new `context = {}`, then retain all active builders. Legacy `context` telemetry disappears because that work no longer runs; extras/hero/sections/presentation/render timing remains. No replacement measurement is manufactured. No template, authentication or media policy changed.

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

Separate CI correction `a9a87bc6` removes the obsolete named-branch allowlist; master-target PRs retain synthetic PostgreSQL, no production database secrets and existing security suites. The initial run #60 was superseded, not accepted as success. Final pre-merge [run #62 passed](https://github.com/rkRashik/DeltaCrown/actions/runs/40967041787) at `c781e88a`; these checks did not include the newly investigated slow-work cancellation case. No skipped/pending run is PASS.

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

OL-INC-01: **74 documents / 373 local links, zero active failures**, 29 Development anchor references checked, and `git diff --check` passed. The 47 historical findings and three root-placement hygiene failures below are unchanged. Only BACKLOG, STATUS, CHANGELOG and HANDOFF are modified; no ignore/policy/application changes or protected-document publication. New dependency/regression CI is a future implementation gate, not a claimed result of this documentation PR.

Before OL-DOC-01 edits: documentation checker passed for 63 documents / 177 local links, with zero active failures and 47 historical findings. Hygiene already failed on three tracked root files absent from its allowlist: `OWNLOBBY_LAUNCH_CUTOVER.md`, `OWNLOBBY_RECOVERY_CANDIDATE_CHECKLIST.md`, `OWNLOBBY_RECOVERY_CUTOVER.md`. Preserve them; do not quietly broaden the root allowlist or move them to make this task green.

Initial OL-DOC-01 implementation checks: 73 documents / 343 local links, zero active failures, unchanged 47 historical findings; the same three baseline hygiene findings remained with no new violation. Development heading anchors and narrow ignore boundaries passed. All 435 pre-existing owner Documents files had unchanged aggregate content/path fingerprints. These are the original documentation-delivery checks, not the later Render observation or current OL-01 verification. No application test suite was run during OL-01; its bounded live checks are recorded above.
