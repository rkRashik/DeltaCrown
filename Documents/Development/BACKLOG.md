# OwnLobby master backlog

Updated: 2026-10-29. This is the canonical task-state record. [STATUS](STATUS.md) supplies dated evidence provenance; [ROADMAP](ROADMAP.md) supplies milestone gates. All OL-01 through OL-13 IDs are permanent. None is DONE at initialization.

Owner for product/production decisions: repository owner. Implementers/reviewers are assigned when a task starts; none is implied by this list. OL-01 through OL-13 initially reference [Issue #37](https://github.com/rkRashik/DeltaCrown/issues/37); create narrower issues only when useful and authorized. Status vocabulary and completion workflow are in [README](README.md).

| ID | Task | Priority | Status | Main dependency / next action |
|---|---|---|---|---|
| [OL-01](#ol-01) | Supabase Data API security containment | P0 | VERIFYING | Owner disabled API; verify denial and compatibility, then separately approve permanent hardening |
| [OL-02](#ol-02) | Django secret-key warning and CI coverage | P0 | TODO | Safe warning diagnosis and current branch-coverage review |
| [OL-03](#ol-03) | Render stability, CPU and memory investigation | P1 | TODO | Establish current deployment/resource baseline |
| [OL-04](#ol-04) | Homepage, database and Redis performance | P1 | TODO | OL-03 baseline; isolate measured bottlenecks |
| [OL-05](#ol-05) | Public image and private media delivery audit | P1 | TODO | OL-01 verification priority; permission-safe delivery measurements |
| [OL-06](#ol-06) | Cloudflare R2 feasibility, cost and quota safeguards | P2 | DEFERRED | OL-05 measurements; compare retaining current providers |
| [OL-07](#ol-07) | Approved media delivery optimization | P1 | BLOCKED | OL-05 and owner-selected design; OL-06 only if migration considered |
| [OL-08](#ol-08) | Background jobs, scheduling and Celery alternatives | P1 | TODO | OL-03 capacity baseline; inventory while Celery stays OFF |
| [OL-09](#ol-09) | eFootball end-to-end tournament workflow QA | P1 | TODO | Isolated QA; OL-08 for async acceptance; security gates before live pilot |
| [OL-10](#ol-10) | Mobile UX and accessibility | P1 | TODO | Representative supported workflows and device matrix |
| [OL-11](#ol-11) | OwnLobby rebranding completion | P1 | TODO | Approved assets, preserved identifiers and source/browser audit |
| [OL-12](#ol-12) | Technical SEO and Google indexing | P1 | TODO | OL-11/public-page readiness and owner Search Console access |
| [OL-13](#ol-13) | Production/public launch acceptance | P1 | BLOCKED | Required OL-01 through OL-12 gates; optional R2 is not mandatory |

## OL-01

**Supabase Data API security containment — P0 / VERIFYING**

- Objective: close the sanitized authorization risk without breaking Django or private Storage access.
- Current state: owner reports containment configuration applied on 2026-10-29: Overview shows Enable Data API OFF; Settings shows Data API disabled. External endpoint denial, application compatibility smoke and permanent database privilege hardening remain pending. Sensitive-data extraction/exploitation has not been established.
- Dependencies: owner-controlled private evidence and an agreed bounded verification scope; separate approval for hardening. No dependency on documentation polish or R2.
- Relevant code: [Django settings](../../deltacrown/settings.py), [media configuration](../../apps/common/media/configuration.py), [governed media tests](../../apps/common/tests/test_governed_media.py). No sensitive endpoint/table inventory belongs in this public document.
- References/evidence: Issue #37 for overall handoff; owner-held OL-01 audit and owner dashboard attestation dated 2026-10-29. Private evidence URL not supplied. Source inspection found no required database Data API consumer; this is not a compatibility PASS.
- Acceptance: independently record API denial and approved compatibility checks without sensitive-row extraction; keep Data API disabled; review and separately authorize permanent least-privilege/future-object hardening and rollback; verify the approved change and non-regression before DONE.
- Next action: prepare/execute only the agreed read-only verification scope, then produce a concrete hardening proposal. No re-enablement, RLS/grant changes or production writes are authorized by OL-DOC-01.

## OL-02

**Django secret-key warning and CI coverage — P0 / TODO**

- Objective: establish the actual cause/disposition of the reported Django signing-key warning and ensure required tests run for new work.
- Dependencies: private configuration access under an approved diagnostic scope; owner approval for any key change. Coordinate with OL-01 without delaying containment verification.
- Relevant code: [settings](../../deltacrown/settings.py), [Render build](../../render_build.sh), [Linux QA workflow](../../.github/workflows/ownlobby-linux-smoke.yml), [release tests](../../apps/common/tests/test_release_readiness.py).
- References/evidence: Issue #37 reports `security.W009` after the 2026-10-28 deployment; key presence is not strength verification. Source shows the Linux smoke job is restricted to named PR branches, so a skipped job is not coverage.
- Acceptance: diagnose without revealing key values; document result and required action. If rotation is necessary, separately approve staged compatibility/rollback with sessions, reset tokens and any supported fallback behavior tested. Required CI must execute for the reviewed branch/SHA, with baseline failures/skips explicit.
- Next action: review sanitized warning evidence and workflow conditions; prepare the smallest diagnostic/CI proposal. No blind rotation or warning suppression.

## OL-03

**Render stability, CPU and memory investigation — P1 / TODO**

- Objective: determine current errors, cold-start behavior, CPU/RSS peaks and request/concurrency limits before claiming a hosting failure or buying capacity.
- Dependencies: authorized read-only Render metrics/config scope; OL-01 takes priority.
- Relevant code: [start script](../../bin/start_render.sh), [process supervision](../../scripts/render_processes.py), [ASGI](../../deltacrown/asgi.py), [Render blueprint](../../render.yaml).
- References/evidence: Issue #37 records Free Singapore, 512 MiB / 0.15 CPU and no new observed 500s in its sampled logs; this is historical, not current stability certification. [PR #31](https://github.com/rkRashik/DeltaCrown/pull/31) addressed media buffering, not all resource problems.
- Acceptance: record actual deployed SHA/plan, observation window, load profile, restart/error/latency/CPU/RSS findings and bottleneck hypothesis; define safe budgets and a reversible proposal. No load test on production without scope approval; no paid upgrade assumed.
- Next action: collect sanitized current deployment/metric evidence and distinguish memory, CPU, database, network and cold-start behavior.

## OL-04

**Homepage, database and Redis performance — P1 / TODO**

- Objective: reduce measured page-generation latency while preserving personalized/private responses.
- Dependencies: OL-03 baseline and an approved measurement/optimization scope.
- Relevant code: [homepage views](../../apps/siteui/views.py), [hero](../../apps/siteui/homepage_hero.py), [phase timing tests](../../apps/siteui/tests/test_homepage_phase_timing.py), [settings/cache configuration](../../deltacrown/settings.py).
- References/evidence: [PR #36](https://github.com/rkRashik/DeltaCrown/pull/36) and Issue #37 establish slow context/extras/render observations; [PR #32](https://github.com/rkRashik/DeltaCrown/pull/32) adds public Redis fallback. No complete root cause or percentile baseline exists here.
- Acceptance: isolate query counts/DB time, eager/N+1 reads, cache misses and template work; agree numerical budgets; compare cold/warm p50/p95 against baseline under the same profile; prove guest/user isolation and fallback behavior. No shared caching of personalized HTML.
- Next action: produce a sanitized phase/query/cache measurement plan, then optimize the demonstrated cause in a scoped change.

## OL-05

**Public image and private media delivery audit — P1 / TODO**

- Objective: explain slow images while preserving every private/conditional delivery boundary.
- Dependencies: approved read-only scope; OL-01 verification priority; OL-03/04 coordinate HTML-versus-image measurements.
- Relevant code: [media views](../../apps/common/media/views.py), [storage](../../apps/common/media/storage.py), [media policy](../../apps/common/media/policy.py), [media architecture history](../../OWNLOBBY_MEDIA_ARCHITECTURE.md).
- References/evidence: [PR #31](https://github.com/rkRashik/DeltaCrown/pull/31) adds bounded streaming; Issue #37 records earlier private-media checks and slow-image concerns. Neither establishes the complete image root cause or current privacy state.
- Acceptance: classify approved public artwork separately from confidential/conditional files; measure dimensions, bytes, TTFB/transfer, cache headers and repeat views with approved assets; document authorization and raw-access denial through safe synthetic checks; compare candidate fixes and rollback without publishing private inventories.
- Next action: audit only approved public assets/synthetic private fixtures; present a measured delivery recommendation. No copies, deletion or policy changes.

## OL-06

**Cloudflare R2 feasibility, cost and quota safeguards — P2 / DEFERRED**

- Objective: determine whether R2 improves cost/performance over existing Supabase/Cloudinary within owner constraints; retaining current providers is a valid outcome.
- Dependencies: OL-05 findings and current owner-approved usage/budget assumptions. No migration approval exists.
- Relevant references: [media architecture](../../OWNLOBBY_MEDIA_ARCHITECTURE.md), [storage configuration](../../apps/common/media/configuration.py), Issue #37. Historic pricing is not a current quote.
- Evidence: owner requires free/very low cost and avoidance of additional storage charges; no measured provider comparison or validated quota implementation yet.
- Acceptance: verify current provider pricing/entitlements; model storage, request classes, ongoing billing, backups, duplicates, growth and transfer; design warnings near 8 GB and 9 GB plus blocking safely below the applicable allowance; define units, concurrent upload reservations, reconciliation, failure/abuse behavior and owner recovery. State absence of a provider-enforced hard cap and residual billing risk; never claim warnings guarantee zero spend.
- Next action: after higher-priority blockers, prepare a dated comparison and quota design for owner decision. No account purchase, upload migration or automatic media deletion.

## OL-07

**Approved media delivery optimization — P1 / BLOCKED**

- Objective: implement only the selected, measured delivery improvement.
- Dependencies/blocker: OL-05 evidence and owner approval of a concrete design; OL-06 required only if choosing R2. Existing-provider optimization is allowed as a proposal.
- Relevant code: [media package](../../apps/common/media/), [game assets](../../apps/games/), [templates](../../templates/).
- References/evidence: Issue #37 and PR #31; no new optimization design or cutover approved by OL-DOC-01.
- Acceptance: approved public-only derivatives/cache policy, private denial and record authorization unchanged; measurable first/repeat-view improvement; bounded resource/cost use; verified rollback preserving originals/references. No source deletion or private publication without explicit separate safety review/approval.
- Next action: turn OL-05 recommendation into a scoped implementation/acceptance/rollback plan and request the concrete approval.

## OL-08

**Background jobs, scheduling and Celery alternatives — P1 / TODO**

- Objective: make required lifecycle, notification and other async work reliable within capacity/budget.
- Dependencies: OL-03 resource evidence; owner architecture/cost approval before activation.
- Relevant code: [Celery configuration](../../deltacrown/celery.py), [tournament operations tasks](../../apps/tournament_ops/tasks/), [notification tasks](../../apps/notifications/tasks.py), [start script](../../bin/start_render.sh).
- References/evidence: Issue #37 reports Celery OFF and a successful five-minute authenticated lifecycle cron; [launch handoff](../../OWNLOBBY_LAUNCH_CUTOVER.md) contains historical job work, not permission to activate it.
- Acceptance: inventory job producers/consumers and actual triggers; document missed/duplicate/retry semantics, timeouts, idempotency, after-commit dispatch, backlog monitoring and shutdown; compare separate worker/scheduler/other queue options and costs; test the selected design in isolation before approved production rollout.
- Next action: map required launch jobs and gaps while leaving Celery OFF. A cron HTTP success alone cannot close this task.

## OL-09

**eFootball end-to-end tournament workflow QA — P1 / TODO**

- Objective: prove the supported solo/team and organizer journey through tournament completion.
- Dependencies: isolated disposable QA, explicit game/format acceptance matrix and OL-08 for queued outcomes; OL-01/02 before any separately approved live pilot.
- Relevant code: [tournament services](../../apps/tournaments/services/), [TOC](../../apps/tournaments/api/toc/), [registration tests](../../apps/tournaments/tests/test_registration_dc_payment.py), [lifecycle regression](../../apps/tournaments/tests/test_toc_lifecycle_stepper.py).
- References/evidence: PR #36/Issue #37 report selected synthetic registration/bracket/result/notification tests; current master includes lifecycle completion corrections. Full eFootball end-to-end acceptance and latest-commit test execution remain unverified here.
- Acceptance: create/configure/publish, eligibility/entry, synthetic payment review, check-in, seeding/stages/brackets, match/lobby/result/evidence/dispute, advancement/completion and notifications; include wrong-role, duplicate/retry, cancellation and stale-state cases. Assert no duplicate financial effects and no private leakage.
- Next action: define fixtures/roles/formats and run isolated QA. No fake production tournament/payment or real-user manipulation.

## OL-10

**Mobile UX and accessibility — P1 / TODO**

- Objective: complete usable supported journeys across desktop, tablet and mobile.
- Dependencies: OL-09 workflow matrix; settings specification before any separately authorized settings redesign.
- Relevant code: [mobile tournament detail](../../templates/tournaments/detailPages/_detail_mobile.html), [settings template](../../templates/user_profile/profile/settings_control_deck.html), [static assets](../../static/).
- References/evidence: latest master includes mobile rich-text correction; [readiness report](../../OWNLOBBY_PRODUCTION_READINESS.md) retains earlier findings/fixes. No current comprehensive viewport or assistive-technology PASS.
- Acceptance: record tested widths/devices/browsers; no horizontal overflow; complete navigation, forms, validation/errors, modals, keyboard/focus/labels/contrast/reduced-motion checks; preserve save, CSRF, AJAX and passport contracts. Proposed accessibility target is in PRD, not a certification claim.
- Next action: audit actual representative pages and rank reproducible defects before scoped fixes.

## OL-11

**OwnLobby rebranding completion — P1 / TODO**

- Objective: finish public-facing identity consistently without renaming technical contracts or stored history.
- Dependencies: approved asset provenance and OL-10 representative review.
- Relevant code: [branding module](../../deltacrown/branding.py), [approved assets](../../branding/approved-assets.json), [verification script](../../scripts/verify_ownlobby.py), [rebrand history](../../OWNLOBBY_REBRAND.md).
- References/evidence: prior rebrand implementation/report and current master pass-logo fix; no new full asset/browser verification in OL-DOC-01.
- Acceptance: review shared/standalone pages, emails and future generated outputs; validate approved asset hashes and terminology; classify intentional technical/historical DeltaCrown references rather than blanket replacement. Provider branding/social ownership actions require owner evidence.
- Next action: refresh the display-reference/asset/browser checklist and identify remaining authored UI inconsistencies.

## OL-12

**Technical SEO and Google indexing — P1 / TODO**

- Objective: verify accurate discoverability of eligible public pages without indexing private content.
- Dependencies: public-page readiness/OL-11, current canonical configuration and owner-controlled Search Console access. Security/privacy gates remain prerequisites to promotion.
- Relevant code: [SEO policy](../../apps/common/seo.py), [robots/sitemaps](../../apps/common/seo_views.py), [technical SEO reference](../../OWNLOBBY_TECHNICAL_SEO.md), [domain reference](../../OWNLOBBY_DOMAIN_MIGRATION.md).
- References/evidence: SEO source exists; Issue #37 records a canonical-origin update. Current indexing, sitemap submission, Search Console verification and search-selected canonical state remain unverified.
- Acceptance: verify canonical/query/noindex/redirect/JSON-LD and sitemap eligibility; private/error pages excluded; owner confirms property verification/submission and records indexing observations. Do not promise rankings or completion solely from sitemap availability.
- Next action: review source and safe public metadata, then obtain owner Search Console status. No DNS/callback/redirect changes by default.

## OL-13

**Production/public launch acceptance — P1 / BLOCKED**

- Objective: record an explicit owner go/no-go for a defined supported launch scope.
- Dependencies/blockers: OL-01/02 security; required reliability/performance/media/job gates from OL-03/04/05/07/08; workflow/mobile/brand/SEO acceptance from OL-09/10/11/12. OL-06 migration is optional, not an artificial blocker. Required open items must be resolved or explicitly dispositioned by the owner; no silent risk acceptance.
- Relevant references: [PRD](PRD.md), [ROADMAP](ROADMAP.md), [readiness history](../../OWNLOBBY_PRODUCTION_READINESS.md), [runbook index](runbooks/README.md), Issue #37.
- Evidence: historical selected CI/live-route checks and owner Google/reset confirmation exist. Fresh signup/OTP, external non-allowlisted Google sign-in, current deployment/resource behavior, full supported journeys and independent recovery acceptance are incomplete here.
- Acceptance: exact release SHA/environment; required CI and isolated journeys pass; approved real signup/provider verification; private access and media boundaries remain intact; measured performance/cost budgets and recovery evidence; monitoring/rollback ownership; owner records scope and release decision separately from technical tests.
- Next action: maintain a release gate matrix as upstream tasks close. Do not infer approval from a healthy homepage or a merged documentation PR.

## OL-DOC-01

**Development management workspace — documentation / VERIFYING (owner review pending)**

- Objective/scope: the ten Development documents, narrow tracking exception, active-document policy and entry-point links; application/infrastructure changes excluded.
- Dependencies: owner review and Git delivery; does not block urgent approved OL-01 work.
- Evidence: [STATUS](STATUS.md) and [CHANGELOG](CHANGELOG.md) record local documentation checks and unchanged baseline failures; this branch/PR contains the reviewed source diff. No production changes or application tests.
- Acceptance: all ten documents tracked, only reviewed paths committed, private collections preserved, local links/anchors validated, public-safe evidence, dedicated branch/PR delivered and owner review recorded.
- Next action: review the documentation PR, resolve requested documentation corrections, and update this state after owner acceptance. Keep OL-01 unresolved independently.
