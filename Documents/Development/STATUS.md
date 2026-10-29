# OwnLobby current status

Last OL-01 verification review: **2026-10-29 23:49 +06:00 (Asia/Dhaka)**. Bounded live HTTP/DB checks ran at 23:12-23:15 +06:00; a read-only Render follow-up used the owner-confirmed workspace at 23:47-23:49. Earlier evidence retains its dates below. These observations do not constitute full production acceptance; recheck before acting.

## Repository and deployment

| Item | State / provenance |
|---|---|
| Product / repository | OwnLobby / [rkRashik/DeltaCrown](https://github.com/rkRashik/DeltaCrown), default branch `master` |
| Verified master baseline | [`e1ef7372fcbd3552ff3b5df8caa852b96cfcf362`](https://github.com/rkRashik/DeltaCrown/commit/e1ef7372fcbd3552ff3b5df8caa852b96cfcf362), remote verified and clean local master safely fast-forwarded during this task |
| Latest application source change | `f1f8d185`: tournament lifecycle/mobile rich text/pass logo; not a Render failure fix. Newer master work is documentation-only |
| Latest independently verified Render live deployment | [`f1f8d18566723aa4e62875c20f7f6bc8dc4794e1`](https://github.com/rkRashik/DeltaCrown/commit/f1f8d18566723aa4e62875c20f7f6bc8dc4794e1), Render deploy `dep-dbhelq67bikc73eeefsg` succeeded **2026-10-29 12:46:51 +06:00**; verified with read-only [Render service](https://dashboard.render.com/web/srv-d6eubkngi27c738ieao0) deploy listing later that day. The `b7eb47f0` commit in Issue #37 was the preceding deployment, not the current live SHA. A live deploy status does not prove application journey acceptance. |
| Production | [ownlobby.com](https://ownlobby.com): six public routes and two approved public images passed bounded HTTP checks at 23:13-23:15 +06:00. Read-only Render follow-up reconfirmed live `f1f8d185`, Free plan and auto-deploy OFF; authenticated/private-media acceptance remains open |
| Documentation delivery | [PR #38](https://github.com/rkRashik/DeltaCrown/pull/38) merged 2026-10-29 at 19:05:48 +06:00, final head `418ec5d2`, four commits. OL-01 prepares a separate documentation-only evidence PR; no deployment |

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

**Next safe task:** close remaining provider-state/private-browser evidence gaps, then obtain separate owner approval for the [minimal permanent-hardening proposal](BACKLOG.md#ol-01-permanent-hardening-proposal-not-executed). The bounded Render log review is complete; documentation review must not delay urgent approved work.

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

- OL-02: Issue #37 reports a Django signing-key warning; strength/disposition remains unverified. Never print/rotate the key merely to clear a warning. The [Linux workflow](../../.github/workflows/ownlobby-linux-smoke.yml) is limited to named PR branches; new branches must not assume full smoke coverage.
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
