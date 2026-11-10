# OwnLobby documentation

OwnLobby is a Bangladesh-first competitive gaming platform (tournaments, teams, player identity, rankings, community) built with Django. Production: <https://ownlobby.com>. The Python package, apps, models and tables keep the original `deltacrown` identifiers for compatibility; do not rename them for appearance.

## Start here

| I want to... | Read |
|---|---|
| Understand how the system fits together | [architecture.md](architecture.md) |
| Know what each product area does | [features.md](features.md) |
| Run, build and test locally | [development.md](development.md) |
| Deploy, roll back or change the domain | [deployment.md](deployment.md) |
| Work on email, OAuth, Supabase, Redis or media | [integrations.md](integrations.md) |
| Understand authentication, permissions, CSP, wallet safety, dependency policy | [security.md](security.md) |
| Follow an operational procedure | [runbooks/](runbooks/README.md) |
| See current status, open tasks and decisions | [Documents/Development](../Documents/Development/README.md) (`STATUS`, `BACKLOG`, `DECISIONS`) |
| Agent and contributor rules | [AGENTS.md](../AGENTS.md) |

## Rules for these documents

* One topic, one document. Link instead of copying. If a fact is in code, link to the code and describe only the contract.
* Describe verified behaviour. Mark anything unproven as such. Do not record test output, session diaries or release logs here; Git history, PRs and `Documents/Development/STATUS.md` carry dated evidence.
* Dated operational state (what is deployed, which task is open) lives only in `Documents/Development/STATUS.md` and `BACKLOG.md`.
* Only reviewed files in this folder are tracked (see `.gitignore`); private notes and drafts stay out of Git. `Documents/DELTACROWN/` holds owner originals and is protected.
* Check links and placement with `python scripts/check_documentation.py --all` and `python scripts/ops/check_repo_hygiene.py`.
