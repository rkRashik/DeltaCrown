# OwnLobby product requirements

Planning baseline: 2026-10-29. Operational state lives in [STATUS](STATUS.md); execution state lives in [BACKLOG](BACKLOG.md). This document is not a launch-completion claim.

## Vision and audience

OwnLobby is a Bangladesh-first gaming and esports platform where players find credible competition, build a competitive identity, form teams and participate in communities. Organizers need reliable tournament operations and evidence-backed results on affordable infrastructure. Players, captains, organization managers, tournament staff, moderators and spectators have different permissions and information needs.

The immediate product goal is a safe, usable, measured launch of the existing workflows. Broad growth features and infrastructure migrations follow verified launch needs and owner budget decisions.

## Core workflows and implementation maturity

“Implemented in source” means relevant code exists and was inspected; it does not mean every path has passed production acceptance. Partial workflows require the listed acceptance work.

| Area | Required behavior | Current evidence/maturity | Tracking |
|---|---|---|---|
| Accounts and player identity | Signup, verification, login/reset, Google sign-in, profile and Game Passport with correct ownership | Implemented in [accounts](../../apps/accounts/) and [user_profile](../../apps/user_profile/). Owner-verified Google/reset history is recorded in Issue #37; fresh signup/public Google acceptance remains partial | OL-01, OL-02, OL-13 |
| Tournament discovery and entry | Discover published tournaments, understand rules/eligibility, enter solo/as a team, handle payment and check-in without duplicate financial effects | Implemented in [tournaments](../../apps/tournaments/); targeted synthetic registration evidence exists. Complete eFootball journey remains partial | OL-09 |
| Organizer match operations | Configure stages, seed/generate brackets, progress lifecycle, handle lobbies, submissions, disputes and final results with role checks | Implemented in [TOC](../../apps/tournaments/api/toc/) and domain services. Latest source corrects lifecycle completion evidence; full operational acceptance pending | OL-08, OL-09 |
| Teams and organizations | Manage membership, roles, roster and competitive settings; prevent cross-team modification | Implemented in [organizations](../../apps/organizations/); full role/device matrix remains partial | OL-09, OL-13 |
| Community and spectators | Discover public activity, post/comment/react where authorized, receive relevant notifications; respect private content | Implemented in [siteui](../../apps/siteui/) and [notifications](../../apps/notifications/). Static-delivery fixes exist; end-to-end async delivery remains partial | OL-08, OL-10, OL-13 |
| Economy and trust | Preserve Coins wallet/escrow/ledger integrity, payment review and restricted evidence access | Implemented in [economy](../../apps/economy/) and tournament services. Selected tests are not blanket financial acceptance | OL-01, OL-05, OL-09, OL-13 |
| Branding and discovery | Consistent OwnLobby presentation and accurate public metadata/indexing without technical-ID renames | Implemented in [branding](../../deltacrown/branding.py), [SEO](../../apps/common/seo.py) and [sitemaps](../../apps/common/seo_views.py). Visual completion and Google indexing unverified | OL-11, OL-12 |
| Showdown, Missions, Bounty, Dropzone and Store | Retain existing permission/configuration boundaries; document supported journeys before promotion | Source modules exist; supported launch scope and full acceptance are not established here | OL-13 scope review |

## Functional acceptance requirements

- Player journey: account creation and delivery of verification mail, verified login, correct profile/privacy behavior, eligible entry, notifications and result visibility. No fake success states.
- Team journey: captain/member permissions, roster validation, registration ownership, team changes and private team content must remain consistent.
- Organizer journey: create/configure/publish, registration/payment decisions, check-in, bracket/stage progression, dispute review, completion and awards. Status must derive from actual completed fixtures, not stale pointers or rounded percentages.
- Community journey: public/private visibility, author/moderator controls, safe attachment delivery and working mobile navigation.
- Failed/duplicate/retried requests must not duplicate entries, charge twice or publish uncommitted results. Preserve financial and historical records.
- Account deletion, private evidence and administrative actions require explicit permissions and auditable outcomes. No cosmetic work may change backend contracts implicitly.

## Quality requirements and gates

| Requirement | Acceptance direction |
|---|---|
| Security/privacy | Close OL-01 with denial and compatibility evidence plus reviewed permanent hardening. Verify account/role boundaries and private media denial. No secret or sensitive evidence in public Git |
| Performance | Separate HTML/context/DB/cache/template and image timings; measure cold/warm and p50/p95 on representative Bangladesh connections. Agree numeric budgets before optimization; no invented SLA or score |
| Reliability | Measure latency, failures, CPU/RSS and connection behavior under an approved load profile. Document degraded Redis/storage behavior and recovery; health alone does not prove readiness |
| Scalability | Respect current low-resource hosting. Test connection/concurrency budgets and job semantics before adding workers/instances; do not assume local caches coordinate across instances |
| Cost | Free/very low-cost operation is an owner constraint. Storage, requests, backups, transfer and ongoing billing all count; no provider change without approved budget |
| Usability/accessibility | Complete desktop/tablet/mobile workflows without horizontal overflow; readable forms, keyboard/focus/labels and actual save/modal behavior. Proposed target: WCAG 2.2 AA review, not current conformance certification |
| Recovery | Independent metadata/object recovery with access controls and owner-approved RPO/RTO. Historical local restore evidence does not prove full provider/platform recovery |
| Maintainability | Stable task IDs, current handoff, explicit acceptance evidence and preserved history; safe isolated tests and documented baseline failures |

## Proposed, not approved or complete

- R2 migration or other provider cutover (OL-06/OL-07).
- A storage-budget design with warnings near 8 GB and 9 GB, upload blocking below the applicable free allowance, concurrency reservations and reconciliation. Exact thresholds/units/entitlements require review; warnings are not a billing hard cap.
- A new worker service, Celery activation or alternative async architecture (OL-08).
- New CDN/public derivatives, broad media retirement, richer editor publication, newsletter subscription or additional growth features.
- Numeric performance SLOs, paid scaling and full disaster-recovery targets until cost and operational feasibility are approved.

## Scope boundaries

Existing feature code is not permission to advertise it as launch-ready. [OL-13](BACKLOG.md#ol-13) selects the supported launch journey set and requires owner acceptance. Preserve Django package/app/model/route/currency identifiers, original assets and user history. Technical details and prior verification remain in linked reports, not duplicated here.
