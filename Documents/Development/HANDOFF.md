# Continuation brief

Updated 2026-11-10. Read [STATUS](STATUS.md) first.

* Production is live on master `7afd6f68`; rollback target `044b9cfb`. Deploys are manual and owner-approved.
* Next safe work: owner decision on PR #77 (merge, then re-run the focused tests on the combined tree), an atomic PIN lockout follow-up, confirming a Supabase backup and the Render environment checklist ([deployment.md](../../docs/operations/deployment.md#environment-variables)), then the remaining OL-01/OL-13 acceptance items in [BACKLOG](BACKLOG.md).
* Do not touch PR #77 or Draft #47 without instruction. Do not run production tests, migrations, deploys, secret rotation or media changes without explicit authorization.
* Verification before any PR: targeted tests for the touched area, `python scripts/verify_ownlobby.py --collect-static` for template/URL changes, documentation and hygiene checks for docs.
