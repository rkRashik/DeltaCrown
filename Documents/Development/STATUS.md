# OwnLobby current status

Last source/status review: **2026-10-29 18:16 +06:00 (Asia/Dhaka)**. This is a documentation review timestamp, not a fresh production health check. Recheck before acting.

## Repository and deployment

| Item | State / provenance |
|---|---|
| Product / repository | OwnLobby / [rkRashik/DeltaCrown](https://github.com/rkRashik/DeltaCrown), default branch `master` |
| Verified master baseline | [`f1f8d18566723aa4e62875c20f7f6bc8dc4794e1`](https://github.com/rkRashik/DeltaCrown/commit/f1f8d18566723aa4e62875c20f7f6bc8dc4794e1), local and GitHub master checked on 2026-10-29 |
| Latest source change | Tournament lifecycle completion evidence, mobile rich text and OwnLobby pass logo; not a Render failure fix |
| Latest known deployed SHA | `b7eb47f0d41e7baef447e65b1b0e15e91fe39981`, reported in [Issue #37](https://github.com/rkRashik/DeltaCrown/issues/37) on 2026-10-28; not reverified against Render during OL-DOC-01 |
| Production | [ownlobby.com](https://ownlobby.com) is the owner-designated live site; current deployed SHA/health and full launch acceptance remain unverified here |
| Documentation delivery | OL-DOC-01 prepares a review branch/PR only. See Git/PR history for its revision; no merge or deployment is authorized |

## Completed work with bounded evidence

- PRs [#30](https://github.com/rkRashik/DeltaCrown/pull/30), [#31](https://github.com/rkRashik/DeltaCrown/pull/31), [#32](https://github.com/rkRashik/DeltaCrown/pull/32): merged media-throttle isolation, bounded S3 streaming, public Redis fallback and Community static-delivery guards. Merged code does not establish current latency or full media acceptance.
- PR [#33](https://github.com/rkRashik/DeltaCrown/pull/33): merged synthetic account/profile/launch QA coverage.
- PR [#35](https://github.com/rkRashik/DeltaCrown/pull/35): password-reset form/error fix merged. Issue #37 records owner-verified Google sign-in/password reset following the canonical-origin configuration update.
- PR [#36](https://github.com/rkRashik/DeltaCrown/pull/36): sanitized homepage phase telemetry and selected acceptance checks merged. Issue #37 reports Linux CI and public-route smoke passing at that time. These tests were not rerun in OL-DOC-01.
- Latest master source includes lifecycle/mobile corrections and regression tests; this task inspected the code, not a fresh test execution or deployed acceptance result.

## Active work and immediate next task

**[OL-01](BACKLOG.md#ol-01) remains P0, VERIFYING.** A 2026-10-29 audit established an externally reachable Data API authorization risk before containment. The owner subsequently reports manual containment applied: Dashboard Overview shows **Enable Data API = OFF**, and Settings shows **Data API is disabled**.

| OL-01 sub-gate | State |
|---|---|
| Containment configuration | Applied, owner-reported 2026-10-29; not independently re-read in this documentation task |
| External endpoint denial | Pending verification |
| Application compatibility smoke | Pending verification |
| Permanent database privilege hardening | Pending separate reviewed approval, implementation and verification |
| Sensitive-data extraction / exploitation | Not established; no breach claim |

Code inspection found no required database Data API consumer. Django uses PostgreSQL connections; Supabase Storage APIs are separate. This supports a containment compatibility assessment, not a passed smoke test. Do not re-enable the Data API or change RLS/grants as part of documentation.

**Next safe task:** obtain a bounded read-only OL-01 verification scope, verify owner-applied containment and application compatibility without sensitive-row extraction, then prepare permanent-hardening scope/rollback for separate approval. Documentation review must not delay that work.

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

OL-DOC-01 post-change local checks: 73 documents / 343 local links, zero active failures, unchanged 47 historical findings; the same three baseline hygiene findings remain with no new violation. Development heading anchors and narrow ignore boundaries pass. All 435 pre-existing owner Documents files have unchanged aggregate content/path fingerprints. Final staged-file/commit/PR evidence belongs in the delivery report and Git history. No application tests or production checks were run in this documentation task.
