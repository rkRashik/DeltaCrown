# DeltaCrown

From the **Delta** to the **Crown** — *Where Champions Rise.*  
DeltaCrown is a Bangladesh‑born, globally oriented esports platform for running tournaments and leagues, managing teams and player profiles, handling payments and disputes, and building a culture around competition.

> **Stack:** Python 3.11 • Django 4.2 • MySQL • Redis • S3‑compatible object storage

---

## What is this project?

A modular Django web app that delivers:

- **Tournaments & Brackets:** single/double elimination, round robin, Swiss (progressive), check‑in windows, seeding, live brackets.
- **Registrations & Payments (MVP):** manual verification for bKash/Nagad/Rocket/bank with audit trail (API automation later).
- **Matches & Disputes:** result reporting, evidence attachments, referee workflows, adjudication.
- **Teams & Profiles:** team pages, captain flows, user profiles with avatars; XP/badges/coins are planned.
- **Notifications:** in‑app (and email-ready) notifications; mark one / mark all read.
- **Share & SEO:** share partial (Facebook/Instagram/Discord/WhatsApp/Copy); `{% raw %}{% meta_tags %}{% endraw %}` emits Open Graph + canonical.
- **Admin Ops:** CSV exports (Teams, Tournaments, Notifications, User Profiles), queues, and safer list displays.
- **Good Defaults:** pagination, sitemap/robots, custom error pages, footer partial.

**North Star metric:** *Completed, adjudicated matches per month (CAM).*

---

## Feature status

- ✅ Teams: public index `/teams/` (search + pagination), detail view, admin CSV.
- ✅ Tournaments: list/detail, timeline/events, dispute model & UI, shared partials.
- ✅ Matches & Disputes: creation, evidence, simple ruling flow.
- ✅ Profiles: edit page with avatar upload.
- ✅ Notifications: list with mark‑read/mark‑all; dashboard recent items.
- ✅ Share & SEO: reusable include; canonical + Open Graph.
- ✅ Admin CSV exports: Tournaments, Teams, Notifications, User Profiles (headers below).
- ✅ Modularization: apps split into **admin/**, **models/**, **views/** packages.
- 🟡 Payments: manual verification in admin (APIs/webhooks later).
- 🟡 Dynamic Seeding / ladders: phased after reliable ops.
- 🟡 Store / wallet: phase‑2.

---

## Tech & architecture (short)

- Django apps per domain (tournaments, teams, notifications, user_profile, corelib).
- MySQL 8 primary; Redis for background tasks/caching (ready).
- Object storage (S3/DO Spaces) for media; CDN in production.
- Admin actions for CSV; import‑time registrations via `admin/__init__.py`.
- Safe foreign keys (`'user_profile.UserProfile'`) to avoid circular imports.
- Defensive access patterns: `getattr(user, "profile", None)` / `getattr(user, "userprofile", None)`.

---

## Getting started

### 1) Prerequisites
- Python 3.11
- MySQL 8 (or SQLite for quick local dev)
- Redis (optional for MVP; recommended)
- pip / venv

### 2) Install
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # or: pip install django pytest
```

### 3) Configure
Create `.env` (or export env vars):
```bash
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=changeme
DATABASE_URL=sqlite:///db.sqlite3    # or mysql://user:pass@127.0.0.1:3306/deltacrown
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 4) Initialize DB & admin
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 5) Run
```bash
python manage.py runserver
```
Open http://127.0.0.1:8000/ and /admin

---

## Useful paths

- Teams index: `GET /teams/`
- Tournaments index: `GET /tournaments/`
- Notifications: `GET /notifications/`
- Profile edit: `GET /profile/`
- Admin CSV exports: `/admin/` → select rows → **Actions**

---

## CSV export headers (tests rely on these)

- **Teams**: `id,name,tag,captain_id,captain_username,created_at`
- **Notifications**: `id,user_id,user_username,is_read,created_at,text,url,kind`
- **User Profiles**: `id,username,email,display_name,created_at`

> Keep these stable. If you add/change fields, update tests first.

---

## Testing

We use `pytest`:
```bash
pytest -q
```
Recommended: smoke tests that import each app’s `admin`, `views`, and `urls` to protect the modular structure.

---

## Roadmap

- **M1 Foundations** — registration → manual payment verification → brackets → notifications.
- **M2 Ops Quality** — check‑in/no‑show control; dispute SLAs; CSV/report polish.
- **M3 Payments API** — bKash/Nagad/Rocket APIs + webhooks; automated reconciliation.
- **M4 Production** — streaming embeds, public leaderboards, sponsor placements.
- **M5 Growth** — academy/coaching tracks, ladders, store beta, DeltaCoins wallet.

---

## Notes for contributors

- Keep diffs **behavior‑preserving** unless explicitly requested.
- Avoid circular imports; use string FKs like `'user_profile.UserProfile'`.
- Prefer `select_related/prefetch_related`; be defensive in `list_display` access.
- Keep route ordering: specific > ID > catch‑all.
- Use the profile helpers: `getattr(user, "profile", None)` / `getattr(user, "userprofile", None)`.

---
