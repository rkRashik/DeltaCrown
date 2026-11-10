# Development workspace

Current status, open tasks and decisions. Technical documentation (architecture, features, setup, deployment, integrations, security, runbooks) is in [docs/](../../docs/index.md); this folder only tracks what is happening now.

| File | Owns |
|---|---|
| [STATUS](STATUS.md) | Dated snapshot: what is live, what is open, standing constraints |
| [BACKLOG](BACKLOG.md) | Canonical task IDs (OL-xx), status, acceptance criteria, next action |
| [DECISIONS](DECISIONS.md) | Accepted vs proposed architecture/operations decisions |
| [HANDOFF](HANDOFF.md) | Short continuation brief for the next session |

## Working rules

1. Read [AGENTS.md](../../AGENTS.md), STATUS and HANDOFF, then pick a task ID from BACKLOG. Recheck the real branch, commit and working tree; a historical note or a passing test is not current evidence.
2. Never equate source existence, a merged PR, green CI and a live deployment. Production changes (deploys, migrations, secrets, provider settings, media) need explicit owner approval and a rollback target.
3. Keep STATUS, BACKLOG and HANDOFF current in the PR that changes them; keep them short. Evidence belongs in Git history and PRs, not copied here.
4. Do not publish credentials, private user/media data, signed URLs, raw logs or vulnerability reproduction steps. Never use `git add .`; stage reviewed paths.
5. Verify before committing: `python scripts/check_documentation.py --all`, `python scripts/ops/check_repo_hygiene.py`, `git diff --check`.

Coordination issue: [#37](https://github.com/rkRashik/DeltaCrown/issues/37). Repository: [rkRashik/DeltaCrown](https://github.com/rkRashik/DeltaCrown), default branch `master`. Production: <https://ownlobby.com>.
