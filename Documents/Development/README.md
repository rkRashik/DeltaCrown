# OwnLobby development workspace

This is the public, Git-tracked entry point for ongoing engineering management. It records scope, priorities, evidence and safe continuation; it does not authorize production operations. Historical technical reports remain at their existing paths.

## Start a session

1. Read [agent instructions](../../AGENTS.md) and the latest owner instructions.
2. Read [STATUS](STATUS.md), then [HANDOFF](HANDOFF.md). Recheck the actual branch, commit and working tree before acting.
3. Select a stable task ID in [BACKLOG](BACKLOG.md); read its dependencies, acceptance criteria and next action.
4. Read [DECISIONS](DECISIONS.md), the relevant [PRD](PRD.md) requirements and [ROADMAP](ROADMAP.md) gate.
5. Follow the linked technical references and [runbook index](runbooks/README.md). Use [TASK_TEMPLATE](tasks/TASK_TEMPLATE.md) for a substantial approved task.
6. Review [CHANGELOG](CHANGELOG.md), [Issue #37](https://github.com/rkRashik/DeltaCrown/issues/37), and newer relevant commits/PRs. A historical instruction or passing test is not current operational evidence.

## Sources of truth

| Document | Owns |
|---|---|
| [PRD](PRD.md) | Product requirements and implementation maturity, not release approval |
| [ROADMAP](ROADMAP.md) | Phase order, dependencies and acceptance gates |
| [BACKLOG](BACKLOG.md) | Canonical task IDs, status, acceptance criteria and next actions |
| [STATUS](STATUS.md) | Dated repository/operational snapshot and evidence provenance |
| [DECISIONS](DECISIONS.md) | Accepted decisions versus unapproved proposals |
| [CHANGELOG](CHANGELOG.md) | Dated milestones and verification evidence |
| [HANDOFF](HANDOFF.md) | Short continuation brief derived from BACKLOG and STATUS |
| [TASK_TEMPLATE](tasks/TASK_TEMPLATE.md) | Task-specific scope, plan, verification and rollback |
| [Runbooks](runbooks/README.md) | Index of existing procedures and their limits |

BACKLOG is authoritative for task state. STATUS and HANDOFF summarize it and must be updated together. Task notes carry detailed evidence, not a competing backlog. Existing reports retain their original dates and evidence; new facts supersede their current-status implications only when explicitly dated and sourced.

Evidence labels: **source-verified** (code/config inspected), **historical evidence** (dated PR/report/run), **owner-reported** (owner attestation), **verified now** (check actually executed in this task), **unverified**, and **proposed**. Never equate source existence, a merged PR, CI success and a live deployment.

## References

- Repository: [rkRashik/DeltaCrown](https://github.com/rkRashik/DeltaCrown), default branch `master`.
- Production: [ownlobby.com](https://ownlobby.com); a public URL is not proof of full launch acceptance.
- Technical coordination: [Issue #37](https://github.com/rkRashik/DeltaCrown/issues/37).
- [Documentation guide](../../OWNLOBBY_DOCUMENTATION_GUIDE.md), [repository policy](../../config/repository-policy.json), [local setup](../../README.md).
- [Final engineering handoff](../../OWNLOBBY_FINAL_ENGINEERING_HANDOFF.md), [release handoff](../../OWNLOBBY_RELEASE_HANDOFF.md), [production readiness](../../OWNLOBBY_PRODUCTION_READINESS.md): dated technical evidence, not substitutes for STATUS.

## Safety and public information

- OL-01 is urgent and unresolved. The owner reports Data API containment applied; denial/compatibility verification and permanent privilege hardening remain pending. Do not re-enable it. This workspace does not authorize RLS/grant changes.
- Do not publish vulnerability reproduction steps, affected endpoint/table inventories, credentials, private user/media data, signed URLs or raw operational logs. Keep security evidence owner-controlled; link only an approved private location. No such evidence URL has been supplied for OL-01.
- No production tests, migrations, data writes, deployments, secret rotation, provider changes, media deletion/publication or paid services without the applicable explicit authorization. Read-only checks must also respect their approved data scope.
- Preserve private media, existing IDs, financial history, auth boundaries and settings contracts. Read the owner-local settings specification named in AGENTS before settings redesign; do not publish it.
- R2 is a proposal, not an approved migration. Celery remains OFF pending capacity/architecture review. Verification flags require real evidence.
- All other owner collections remain protected. Never use `git add .`, broad unignore rules or force-add private documents. The sole new publication exception is the explicitly reviewed Development documents in the repository policy and `.gitignore`.
- Urgent owner-approved containment/verification takes priority over documentation polish.

## Daily task and completion workflow

1. Select an existing task ID; never renumber OL-01 through OL-13. Reserve a new ID before adding distinct work. Record owner, scope and evidence date. Subtasks may use suffixes without replacing the parent ID.
2. Inspect current source and baseline checks. Mark unverified assumptions; confirm production scope separately. Use a task branch and explicitly stage reviewed paths.
3. Keep BACKLOG current while work proceeds. `TODO` = not started; `IN_PROGRESS` = active; `VERIFYING` = change applied but acceptance incomplete; `BLOCKED` = named unmet prerequisite; `DEFERRED` = deliberately later; `DONE` = all criteria supported by evidence.
4. Before completing a task, update BACKLOG status/evidence, STATUS summary/timestamp, CHANGELOG with the actual event date, any relevant DECISIONS entry, and HANDOFF next action in the same PR. Reuse links rather than copy technical reports.
5. Record exact code SHA, environment, commands, results, skips, baseline failures and limits. Do not mark a production-dependent task DONE from local tests alone. Keep failed/superseded attempts distinguishable from completed changes.
6. Review public-content safety, local links, tracking boundaries and staged diff. Run `python scripts/check_documentation.py --all`, `python scripts/ops/check_repo_hygiene.py`, and `git diff --cached --check`. Compare against the recorded baseline; no blind cleanup to force green.
7. Add future public task/runbook files deliberately to the narrow ignore exceptions and `active_documents`; then check their links and anchors. The current checker skips heading checks inside `Documents/`, so review those anchors separately. Ignored evidence stays outside this workspace.
8. Commit and open the authorized review PR. Record its URL in the handoff response; merge/deploy only if separately authorized. A document cannot contain its own final commit SHA; use the PR/Git history for the documentation revision.

Use Asia/Dhaka with explicit offset for new status timestamps. Preserve historical event dates; record review dates separately.
