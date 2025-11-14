# DeltaCrown

> **Where Champions Rise** — A comprehensive esports tournament platform for Bangladesh and beyond.

DeltaCrown is a Django-based esports platform for managing tournaments, teams, players, payments, and community engagement across multiple games.

---

## 📊 Status Badges

![Perf Smoke](https://github.com/rkRashik/DeltaCrown/actions/workflows/perf-smoke.yml/badge.svg)
![Perf Baseline](https://github.com/rkRashik/DeltaCrown/actions/workflows/perf-baseline.yml/badge.svg)
![Workflow Secrets Guard](https://github.com/rkRashik/DeltaCrown/actions/workflows/guard-workflow-secrets.yml/badge.svg)

**Performance Status**:
- 🚀 **PR Smoke Tests**: Fast feedback (50 samples, <2 min)
- 🌙 **Nightly Baseline**: Full harness (150 samples, 3 AM UTC)
- 🔒 **Secret Scanning**: Automated workflow lint

---

## 🏗️ Core Infrastructure (NEW!)

**DeltaCrown now has professional, industry-standard infrastructure!**

### Phase 1: Complete ✅ (23/23 tests passing)

The core infrastructure is implemented and tested:
- ✅ **Event Bus** - Replaces Django signals with explicit events
- ✅ **Service Registry** - Loose coupling between apps
- ✅ **Plugin Framework** - Extensible game system
- ✅ **API Gateway** - Internal APIs with versioning

### Quick Start:
- **Get Started in 5 mins:** [`QUICK_START_CORE_INFRASTRUCTURE.md`](QUICK_START_CORE_INFRASTRUCTURE.md)
- **Full Documentation:** [`apps/core/README.md`](apps/core/README.md)
- **Migration Guide:** [`MIGRATION_GUIDE_SIGNALS_TO_EVENTS.md`](MIGRATION_GUIDE_SIGNALS_TO_EVENTS.md)
- **Phase 1 Summary:** [`PHASE_1_COMPLETE.md`](PHASE_1_COMPLETE.md)

### What This Means:
- 🔧 **No more "Signal Hell"** - Explicit, traceable events
- 🔌 **Loosely coupled apps** - No direct imports between apps
- 🎮 **Add new games easily** - Plugin system
- 🧪 **Easy to test** - Can disable handlers, mock services
- 📊 **Full visibility** - Event history, statistics, monitoring

### Example Usage:
```python
# Publish an event
from apps.core.events.bus import event_bus
from apps.core.events.events import TournamentCreatedEvent

event = TournamentCreatedEvent(data={'tournament_id': 123})
event_bus.publish(event)

# Subscribe to events
event_bus.subscribe('tournament.created', handle_tournament_created)

# Use services (no direct imports!)
from apps.core.registry.service_registry import service_registry
tournament_service = service_registry.get('tournament_service')
```

---

## �📢 Tournament System Redesign Documentation

**For Development Teams:** Comprehensive documentation about the current tournament system has been prepared for redesign planning. See: [`Documents/For_New_Tournament_design/`](Documents/For_New_Tournament_design/)

**Start Here:** [`00_README_START_HERE.md`](Documents/For_New_Tournament_design/00_README_START_HERE.md)

The documentation package includes:
- Complete project overview and architecture
- Current technology stack analysis
- Tournament models and business logic reference
- Game integration system details
- Signal system analysis ("Signal Hell" problems)
- Current architectural problems and limitations
- Data flow diagrams and dependencies
- 15+ comprehensive documents for redesign planning

---

## 📋 Project Overview

**Tech Stack:**
- Python 3.11
- Django 4.2
- PostgreSQL
- Redis (Celery + Channels)
- Django REST Framework
- CKEditor 5

**Database:** PostgreSQL (configured with `dc_user`)  
**Time Zone:** Asia/Dhaka  
**Authentication:** Custom user model with email/username login

---

## 🎮 Core Features

### 1. **Tournament System**
- Multiple bracket types: Single/Double Elimination, Round Robin, Swiss
- Tournament registration and payment verification
- Match scheduling and result reporting
- Check-in system and attendance tracking
- Dispute resolution workflow
- Live brackets and timeline events
- Media management (banners, sponsors)
- CSV exports for tournament data

### 2. **Team Management**
- Team creation and roster management
- Captain and co-captain roles
- Team rankings and analytics
- Game-specific configurations (Valorant, eFootball)
- Team presets and quick setup
- Social media integration
- Team uniqueness validation
- Public team directory with search

### 3. **Game Integration**
- **Valorant**: Riot ID validation, agent selection, rank verification
- **eFootball**: Platform-specific player IDs, team setup
- Game-specific validators and configurations
- Cross-platform player tracking

### 4. **User System**
- Custom user model (`accounts.User`)
- User profiles with avatars
- Authentication via email or username
- Optional Google OAuth (django-allauth)
- Profile editing and management
- Player statistics and history

### 5. **Economy & Payments**
- DeltaCoins virtual currency system
- Payment processing (bKash/Nagad/Rocket/Bank - manual verification)
- Transaction history and audit trails
- Coin management and distribution
- Payment verification workflow

### 6. **E-commerce**
- Store functionality (planned)
- Bangladesh payment gateway configuration
- Product management
- Order processing

### 7. **Notifications**
- In-app notification system
- Email notifications (Gmail SMTP)
- Discord webhook integration
- Real-time notifications via Django Channels
- Notification preferences per user
- Mark as read/unread functionality
- Notification dashboard

### 8. **Real-time Features**
- WebSocket support via Django Channels
- Live tournament updates
- Real-time match results
- In-memory channel layer (production-ready)

### 9. **Background Tasks**
- Celery integration with Redis
- Async task processing
- Tournament notifications
- Email sending
- Task deduplication

### 10. **Admin & Management**
- Advanced Django Admin customizations
- CSV export functionality
- Batch operations
- Tournament management tools
- User and team moderation
- Payment verification tools

### 11. **SEO & Marketing**
- Custom SEO meta tags
- Open Graph integration
- Sitemap generation
- Social media sharing
- Canonical URLs
- Custom error pages (403, 404, 500)

### 12. **UI & Design**
- Multiple homepage themes (Cyberpunk, Modern)
- Responsive design
- Custom dashboard widgets
- Template tag libraries
- CKEditor 5 integration
- Asset management system

---

## 📁 Project Structure

```
DeltaCrown/
├── apps/
│   ├── accounts/          # Custom user authentication
│   ├── common/            # Shared utilities and context processors
│   ├── corelib/           # Core library functions
│   ├── corepages/         # Static pages (about, community, etc.)
│   ├── dashboard/         # User dashboard
│   ├── ecommerce/         # Store and products
│   ├── economy/           # DeltaCoins and transactions
│   ├── game_efootball/    # eFootball game integration
│   ├── game_valorant/     # Valorant game integration
│   ├── notifications/     # Notification system
│   ├── players/           # Player profiles and stats
│   ├── search/            # Search functionality
│   ├── siteui/            # UI settings and navigation
│   ├── support/           # Support and help system
│   ├── teams/             # Team management
│   ├── tournaments/       # Tournament system (modular)
│   └── user_profile/      # User profile management
├── deltacrown/            # Project settings
│   ├── settings.py        # Main configuration
│   ├── urls.py            # Root URL configuration
│   ├── celery.py          # Celery configuration
│   ├── asgi.py            # ASGI config for Channels
│   └── wsgi.py            # WSGI config
├── templates/             # Global templates
├── static/                # Static files (CSS, JS, images)
├── tests/                 # Comprehensive test suite (94+ test files)
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
└── pytest.ini             # Pytest configuration
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL
- Redis (for Celery and Channels)

### Installation

1. **Clone the repository**
```powershell
git clone <repository-url>
cd DeltaCrown
```

2. **Create virtual environment**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

3. **Install dependencies**
```powershell
pip install -r requirements.txt
```

4. **Configure environment variables**
Create a `.env` file or set these variables:
```bash
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=your-secret-key-here
DB_NAME=deltacrown
DB_USER=dc_user
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
CELERY_BROKER_URL=redis://localhost:6379/0
DISCORD_WEBHOOK_URL=your-webhook-url
```

5. **Setup database**
```powershell
python manage.py migrate
python manage.py createsuperuser
```

6. **Run development server**
```powershell
python manage.py runserver
```

Visit: `http://127.0.0.1:8000/`

### Running with Celery
```powershell
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A deltacrown worker -l info
```

---

## 🧪 Testing

The project includes 94+ comprehensive test files covering:
- Tournament core functionality
- Team management and rankings
- Payment processing
- Game integrations (Valorant, eFootball)
- Notification system
- Admin functionality
- API endpoints

**Run tests:**
```powershell
pytest
pytest -v  # verbose output
pytest tests/test_specific.py  # specific test file
```

---

## 🌐 Key URLs

- **Home**: `/`
- **Tournaments**: `/tournaments/`
- **Teams**: `/teams/`
- **Profile**: `/profile/`
- **Dashboard**: `/dashboard/`
- **Notifications**: `/notifications/`
- **Admin**: `/admin/`
- **API**: Various endpoints under each app

---

## 🔧 Configuration Highlights

### Authentication
- Custom `User` model: `accounts.User`
- Email or username login supported
- Optional Google OAuth integration
- Password reset via email

### Database
- PostgreSQL with user `dc_user`
- Timezone: Asia/Dhaka
- Migration support for all apps

### Notifications
- Channels: In-app, Email, Discord
- Configurable per notification type
- Real-time updates via WebSockets

### Static & Media
- Static files: `/static/`
- Media uploads: `/media/`
- CDN-ready configuration

---

## 📊 Feature Status

| Feature | Status |
|---------|--------|
| Tournament Management | ✅ Complete |
| Team System | ✅ Complete |
| User Authentication | ✅ Complete |
| Notifications | ✅ Complete |
| Payment Processing | ✅ Manual Verification |
| Game Integrations | ✅ Valorant + eFootball |
| Real-time Updates | ✅ WebSockets Active |
| E-commerce | 🟡 In Development |
| Mobile App | ❌ Planned |
| Payment Gateway API | 🟡 Planned |

---

## 📝 Development Notes

### Custom Template Tags
- `seo_tags` - Meta tags and Open Graph
- `assets` - Asset management
- `dashboard_widgets` - Dashboard components
- `string_utils` - String manipulation

### Context Processors
- Notification counts
- UI settings
- Game assets
- Homepage context
- Site navigation

### Middleware
Standard Django middleware + CSRF trusted origins for ngrok testing

---

## 🤝 Contributing

1. Maintain modular app structure
2. Write tests for new features
3. Follow Django best practices
4. Use string foreign keys to avoid circular imports
5. Keep migrations clean and reversible

---

## 📄 License

[Add your license here]

---

## 👥 Team

Developed by rkRashik and the DeltaCrown team.

---

**Last Updated:** November 2, 2025

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

## 📚 Documentation

**Backend V1 is now fully documented!**

### For Developers
- **Setup Guide**: [`docs/development/setup_guide.md`](docs/development/setup_guide.md) - Complete onboarding from clone to first contribution
- **Architecture**: [`docs/architecture/system_architecture.md`](docs/architecture/system_architecture.md) - System design, data flows, state machines
- **Planning Docs**: [`Documents/Planning/`](Documents/Planning/) - Original specifications (PART 2-5)
- **Execution Tracking**: [`Documents/ExecutionPlan/Core/MAP.md`](Documents/ExecutionPlan/Core/MAP.md) - Implementation progress

### For API Integration
- **API Catalog**: [`docs/api/endpoint_catalog.md`](docs/api/endpoint_catalog.md) - All REST & WebSocket endpoints with examples
- **Error Handling**: Consistent JSON error format (Module 9.5)
- **Health Checks**: `/healthz` (liveness), `/readyz` (readiness)

### For Operations
- **Deployment**: [`docs/runbooks/deployment.md`](docs/runbooks/deployment.md) - Step-by-step deployment procedures
- **Monitoring**: [`docs/runbooks/monitoring_setup.md`](Documents/Runbooks/monitoring_setup.md) - Observability setup
- **Runbooks**: [`Documents/Runbooks/`](Documents/Runbooks/) - Operational procedures

### Historical Documents
- **Archive**: [`Documents/Archive/`](Documents/Archive/) - Historical implementation docs (Phases 2-E)

---

## Testing

We use `pytest`:
```bash
pytest -q
```
Recommended: smoke tests that import each app's `admin`, `views`, and `urls` to protect the modular structure.

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
