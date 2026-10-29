# OwnLobby development changelog

Append dated milestones; retain original event dates. Source changes, historical test reports, owner actions and fresh verification are distinct. Task status is maintained in [BACKLOG](BACKLOG.md). This is a selected evidence index, not a replacement for Git history.

## 2026-10-29

- **Owner-applied containment, OL-01:** owner reports Supabase Data API disabled in Dashboard Overview and Settings. External denial verification, application compatibility smoke and permanent database privilege hardening remain pending. OL-01 is not DONE. Sensitive-data extraction or exploitation has not been established. Detailed audit evidence stays private; no approved private evidence URL supplied.
- **Source milestone:** master [`f1f8d185`](https://github.com/rkRashik/DeltaCrown/commit/f1f8d18566723aa4e62875c20f7f6bc8dc4794e1) integrates [`a1b511ac`](https://github.com/rkRashik/DeltaCrown/commit/a1b511ac): lifecycle completion requires actual completed fixtures; mobile tournament rich text and pass logo corrected. Regression tests exist in [test_toc_lifecycle_stepper.py](../../apps/tournaments/tests/test_toc_lifecycle_stepper.py). Test execution/deployment of this commit was not verified during OL-DOC-01. This is not a Render failure fix.
- **Documentation preparation, OL-DOC-01:** create the Development management workspace, narrow Git publication exception and navigation/policy integration. Delivery is subject to documentation PR review; no production/app change. Check results and final documentation SHA/PR are recorded in the delivery report and Git history, not claimed as a production milestone.
- **Documentation validation, OL-DOC-01:** offline active-link checks pass (73 documents / 343 links); Development heading checks pass. The 47 historical findings and three pre-existing root-placement hygiene failures remain unchanged. Protected Documents fingerprints and narrow-ignore checks pass. No application test or production verification was performed.

## 2026-10-28

- [PR #36](https://github.com/rkRashik/DeltaCrown/pull/36), merge [`b7eb47f0`](https://github.com/rkRashik/DeltaCrown/commit/b7eb47f0d41e7baef447e65b1b0e15e91fe39981): sanitized homepage phase timing and selected launch QA. [Issue #37](https://github.com/rkRashik/DeltaCrown/issues/37) reports Linux CI, selected synthetic tournament/notification tests and public-route GET smoke PASS, and this deployed SHA. Historical results, not rerun here; isolated phase observations are not averages.
- [PR #35](https://github.com/rkRashik/DeltaCrown/pull/35): password-reset form field/error handling corrected. Synthetic success/mismatch/replay tests are described in the PR. Issue #37 separately records owner verification of Google sign-in and password reset after the origin update.
- [PR #33](https://github.com/rkRashik/DeltaCrown/pull/33): account/profile/branding readiness suites added to isolated Linux QA. This does not establish real mail delivery or mobile acceptance.
- [PR #32](https://github.com/rkRashik/DeltaCrown/pull/32): public-page Redis fallback and Community bundle validation merged; targeted failure-path tests added. No general private/session caching change is implied.
- [PR #31](https://github.com/rkRashik/DeltaCrown/pull/31): bounded asynchronous S3 streaming merged, retaining private authorization and safe response behavior. Mocked streaming tests are described; image sizes and full performance acceptance remain open.
- [PR #30](https://github.com/rkRashik/DeltaCrown/pull/30): media throttle no longer depends on intermittent Redis, with bounded process-local limits. Multiple-worker behavior requires a separate review.
- [PR #34](https://github.com/rkRashik/DeltaCrown/pull/34) was closed unmerged and superseded by #36; it is not a delivered change.

## 2026-10-27

- [Final engineering handoff](../../OWNLOBBY_FINAL_ENGINEERING_HANDOFF.md) records owner selection of existing Cloudinary plus private Supabase Storage and hybrid source implementation. It reports 32 targeted Windows/local/synthetic media tests across an initial run and one fixture-correction rerun. This date's report did not establish production cutover. Later operational evidence must be read separately.

## 2026-10-26

- [Release handoff](../../OWNLOBBY_RELEASE_HANDOFF.md) and [security closure](../../OWNLOBBY_SECURITY_CLOSURE.md) record the Twisted HTTP backport and OAuth corrections, with 47 OAuth passes and 238 upstream HTTP passes / five skips in their recorded environments. These are historical test results, not current dependency clearance.
- [Final engineering handoff](../../OWNLOBBY_FINAL_ENGINEERING_HANDOFF.md) records governed-media implementation at `8075d266fefe2d24932ec2ea8b87403c852b99af` and local/synthetic verification. Its unresolved Linux/cloud gates describe that point in time; later Issue #37 evidence supersedes specific operational claims without certifying all launch functions.

Earlier rebrand, SEO, dependency and recovery records retain their original provenance in the [documentation guide](../../OWNLOBBY_DOCUMENTATION_GUIDE.md). Do not assign a new completion date simply because a historical report was reviewed today.
