# Feature development workflow

Purpose: the usual path from an idea to a reviewed PR, with the checks this repository actually enforces. Setup first: [setup](setup.md).

## 1. Orient

* Read [AGENTS.md](../../AGENTS.md) (contracts you must not break, e.g. the settings page guardrails) and `Documents/Development/STATUS.md` and `BACKLOG.md` for current constraints.
* Find the owning app in [architecture overview](../architecture/overview.md#application-modules-apps). Business rules live in services (`apps/<app>/services/`), not in views or templates; start from the service that already does something similar.
* Find the URL: `deltacrown/urls.py` includes each app's `urls.py`. Reverse names are namespaced (`account:login`, `tournaments:...`).

## 2. Branch and change

```powershell
git switch -c feat/<short-topic> origin/master
```

* Smallest correct diff; reuse existing helpers and components. Do not rename `deltacrown` packages, apps, models, tables, routes or currency identifiers.
* Model change: edit the model, `python manage.py makemigrations <app>`, review the migration, run it on your local database. Production migrations are a separate approved release step.
* Template/UI change: use the OwnLobby foundation (`static/ownlobby/foundation.css`, `--ol-*` tokens), accessible names on every control, 44 px touch targets, visible focus, no invented numbers. Inline scripts need `nonce="{{ request.csp_nonce }}"`. See the existing pages under `templates/` for patterns.
* New `{% url %}` tags in templates that `scripts/verify_ownlobby.py` guards must be intentional; see the reviewed list in that script.
* API change: add/extend the serializer and view, document the route in [API reference](../reference/api.md) only if it is a new group.

## 3. Test

Write the narrowest test that proves the behaviour (pytest next to the app, or `tests/`): a Django `client` test for views, a service test for rules, a Playwright harness for JS behaviour. Run only the touched area plus the neighbours, then the release verifier when you changed templates or URLs. Commands: [testing guide](../guides/testing.md).

## 4. Check and open the PR

```powershell
python manage.py check
python scripts/check_documentation.py --all      # if you touched docs
python scripts/ops/check_repo_hygiene.py         # root placement
git diff --check
```

Stage reviewed paths explicitly (never `git add .`), commit with a clear message, push and open a PR against `master`. CI (`ownlobby-linux-smoke`, `asgi-shutdown`) runs on the PR, not on `master`. Compare any failure with master before blaming your change: [known baseline failures](../guides/testing.md#known-baseline-failures).

## 5. Release

Merging does not deploy. Deploys are manual and owner-approved: [deployment](../operations/deployment.md). Update `Documents/Development/STATUS.md` and `BACKLOG.md` in the PR that changes task state.
