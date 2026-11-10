# Testing

Purpose: how to run the right tests, what the harnesses are, and which failures already exist. Setup first: [setup](../getting-started/setup.md). Workflow: [feature workflow](../getting-started/workflow.md).

## Rules

* Use a disposable local PostgreSQL database for tests (`DATABASE_URL_TEST`, different from `DATABASE_URL`). Never test against production or real user data.
* `pytest.ini` sets `DJANGO_SETTINGS_MODULE = deltacrown.settings_test`, `--reuse-db`, `--import-mode=importlib` and `--continue-on-collection-errors`. Plain `pytest` collects a broad legacy suite with known failures, so run explicit targets.
* Tests live next to apps (`apps/<app>/tests/`) and in `tests/` (cross-app: `tests/accounts`, `tests/ui`, `tests/ops`, `tests/integration`, `tests/e2e`, ...).

## Commands

```powershell
$env:DATABASE_URL_TEST='postgresql://<user>:<password>@127.0.0.1:5432/ownlobby_test'

python -m pytest tests/accounts -q -p no:cacheprovider               # one area
python -m pytest apps/notifications/tests/test_notifications_ui_behavior.py -q   # Chromium behaviour tests
python -m pytest tests/ops tests/ui -q                               # repository/verifier and template checks
python manage.py test apps.common.tests.test_release_readiness --settings=deltacrown.settings_brand_qa --keepdb --noinput
python manage.py check
```

Release verifier (compiles every template, checks `{% url %}` contracts, approved assets, static collection). It needs a loopback database literally named `ownlobby_test` and refuses production settings:

```powershell
$env:DJANGO_SETTINGS_MODULE='deltacrown.settings_brand_qa'
$env:DATABASE_URL='postgresql://<user>:<password>@127.0.0.1:5432/ownlobby_unused'   # must differ from the test URL
$env:DATABASE_URL_TEST='postgresql://<user>:<password>@127.0.0.1:5432/ownlobby_test'
npm run build
python scripts/verify_ownlobby.py --collect-static     # prints "new_failures": [] on success
```

Documentation and repository checks: `python scripts/check_documentation.py --all`, `python scripts/ops/check_repo_hygiene.py`, `python -m unittest tests.test_repository_tools`.

## Settings variants

| Settings module | Use |
|---|---|
| `deltacrown.settings_test` | Default for pytest; PostgreSQL |
| `deltacrown.settings_brand_qa` | Release verifier and brand QA; loopback `ownlobby_test` only; locmem email |
| `deltacrown.settings_media_qa`, `deltacrown.settings_smoke`, `deltacrown.settings_sqlite_test`, `deltacrown.settings_test_pg` | CI and focused variants |

## Browser (Playwright) tests

Pattern: serve the real templates/JS in a small harness page, route every API call, count requests and assert behaviour (see `apps/user_profile/tests/test_follow_js_behavior.py` and `apps/notifications/tests/test_notifications_ui_behavior.py`). Install Chromium with `playwright install chromium`; tests skip when it is missing. On Windows set `asyncio.WindowsProactorEventLoopPolicy()` and `DJANGO_ALLOW_ASYNC_UNSAFE=true` for that module (the package's autouse DB fixtures are synchronous).

## Gotchas

* Login and password-reset views rate-limit per IP in the shared cache; tests that make many requests clear the cache in an autouse fixture (`tests/accounts/test_batch_e_auth_pages.py`).
* Do not hard-code credentials in tests: generate throwaway passwords at runtime (`secrets.token_urlsafe`), because secret scanners flag literals in Git history.
* Templates with inline scripts need the CSP nonce; test harnesses that render a template without a request will not have one.
* The first run on a new test database applies all migrations (minutes); later runs reuse it.

## CI

`.github/workflows/ownlobby-linux-smoke.yml` runs on pull requests to `master`: migrations on a disposable database, targeted tournament/registration/results/notification suites, a reliability pytest set, `npm ci` + `npm run build`, then `verify_ownlobby.py --collect-static`. `.github/workflows/asgi-shutdown.yml` runs the gated ASGI shutdown contracts on Python 3.11.9 and 3.12. Master itself has no separate run, so a green PR is the evidence.

## Known baseline failures

These fail on `master` independent of your change; compare against master before investigating:

* `tests/accounts/test_email_otp.py::test_email_signup_and_verify_flow` (asserts a brand string no longer rendered).
* `apps/notifications/tests/` nav-preview serialization tests in `test_nav_preview.py`, `test_dropdown_follow_actions.py`, `test_inline_follow_actions.py` (11 failures).
* `tests/ui/test_homepage.py`, `tests/ui/test_templates_exist.py`, `tests/ui/test_teams_dashboard_templates_exist.py` (legacy template expectations).
* `apps/siteui/tests/test_homepage_context_removal.py` setup errors.
