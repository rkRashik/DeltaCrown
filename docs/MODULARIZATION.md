# DeltaCrown — Modularization Runbook

> Django 4.2 • Python 3.11 • Admin/Models/Views split by concern  
> Behavior‑preserving refactor • Import‑safe • Test‑friendly

---

## App layout conventions

### Admin
Each app exposes a **package** that performs import‑time registrations:

```
apps/<app>/admin/
  __init__.py        # imports submodules so registrations run at import time
  <topic>.py         # ModelAdmin classes
  exports.py         # CSV export actions
  inlines.py         # TabularInline / StackedInline (when used)
  base.py            # (optional) compat shim → re‑export legacy symbols
```

**Do**
- Put `@admin.register(Model)` in the topical module (e.g., `teams.py`).
- Re‑export via `admin/__init__.py` to keep `import apps.<app>.admin` working.
- Use **defensive accessors** (avoid brittle `list_display` that depends on uncertain fields).
- CSV actions must keep **stable headers** (tests rely on them).

**Don’t**
- Keep a monolithic `admin.py` (except as a brief compat shim during migration).

---

### Models
Prefer a **package** with explicit public API:

```
apps/<app>/models/
  __init__.py        # re‑exports public symbols; defines __all__
  <domain>.py        # model groups (tournament.py, registration.py, etc.)
  helpers/*          # constants/enums/paths as needed
```

**Do**
- Use string FKs to avoid circulars: `"user_profile.UserProfile"`.
- Keep `__all__` in `models/__init__.py` so imports are stable for tests.
- Avoid logic in `models/__init__.py` beyond re‑exports.

---

### Views
Every app uses a **views package**:

```
apps/<app>/views/
  __init__.py        # re‑exports public + manage/dashboard symbols
  public.py          # public endpoints
  manage.py          # CRUD/member actions (teams)
  dashboard.py       # dashboard/admin‑like (tournaments)
```

**Do**
- Keep URLs importing from the package:  
  `from .views import public as views` or `from .views import dashboard as views`.
- Maintain route **ordering**: specific/static first; ID routes before tag/catch‑all.

**Compat aliases**
- `apps.teams.views.__init__` sets `team_index` → first found of (`team_index`, `team_list`, `teams_index`, `index`).
- `apps/teams/admin/base.py` re‑exports `export_teams_csv` for older import paths.

---

## Where things live (current)

- **Tournaments**
  - `admin/`: `__init__.py`, `base.py`, `components.py`, `exports.py`, `hooks.py`, `matches.py`, `registrations.py`, `tournaments.py`, `utils.py`
  - `models/`: `__init__.py` (`__all__`), `bracket.py`, `constants.py`, `dispute.py`, `enums.py`, `events.py`, `match.py`, `paths.py`, `registration.py`, `tournament.py`, `tournament_settings.py`
  - `views/`: `__init__.py`, `public.py`, `dashboard.py`
- **Teams**
  - `admin/`: `__init__.py`, `teams.py`, `inlines.py`, `exports.py`, `base.py` (compat shim)
  - `models`: currently a single `apps/teams/models.py` (OK). *Optional:* split into `models/{team.py,membership.py,invite.py}` later.
  - `views/`: `__init__.py`, `public.py`, `manage.py`
- **Notifications**
  - `admin/`: `__init__.py`, `notifications.py`, `exports.py` (header ends with `kind`)
- **User Profile**
  - `admin/`: `__init__.py`, `users.py`, `exports.py`

---

## CSV export contracts (tests rely on headers)

- **Teams**  
  `id,name,tag,captain_id,captain_username,created_at`

- **Notifications**  
  `id,user_id,user_username,is_read,created_at,text,url,kind`

- **User Profiles**  
  `id,username,email,display_name,created_at`

> When adding fields to CSVs, update tests first; otherwise keep these headers.

---

## Performance helpers

Use `apps/corelib/admin_utils.py`:

```python
from apps.corelib.admin_utils import _path_exists, _safe_select_related
```

- `_path_exists(model, "profile__user")` — validate a `select_related` path hop‑by‑hop.  
- `_safe_select_related(qs, "user", "profile__user")` — apply only valid paths.

These are already used by Notifications admin. Consider adopting in other admins.

---

## Adding a new admin for a model (recipe)

1. Create or reuse `apps/<app>/admin/<topic>.py`:

```python
# apps/foo/admin/items.py
from django.contrib import admin
from ..models import Item

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
```

2. Ensure `apps/<app>/admin/__init__.py` imports it:

```python
from .items import *  # noqa
```

3. (Optional) CSV action in `admin/exports.py`, then add to `actions = [...]`.

---

## Signals & import‑time side‑effects

- Keep signal imports inside `apps.py:AppConfig.ready()` or in `admin/__init__.py` (for admin registrations).
- Avoid side effects in `models/__init__.py` beyond symbol re‑exports.

---

## Testing guardrails (recommended)

- **Admin** import & registry smoke tests (model is in `admin.site._registry`).
- **Views** package import tests + compat alias check (`team_index` exposed).
- **URLConf** import tests (each has `urlpatterns`).
- **Models** public API `__all__` contract tests.

Run:
```bash
pytest -q
```

---

## FAQ

**Q: Where did `apps/teams/views_public.py` and `views_actions.py` go?**  
They were moved *verbatim* to `apps/teams/views/public.py` and `apps/teams/views/manage.py`. URLs now import from the package paths.

**Q: Why does `apps/teams/admin/base.py` still exist?**  
It’s a tiny **compat shim** re‑exporting `export_teams_csv` to keep older imports green. Safe to remove once all callers use `apps.teams.admin`.

**Q: What about `team_index`?**  
`apps.teams.views.__init__` exports `team_index` (alias to the actual public list view). Tests look for it.
