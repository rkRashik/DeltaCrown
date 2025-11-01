# DeltaCrown Project Overview

**Document:** 01 - Project Overview  
**Date:** November 2, 2025  
**Purpose:** Complete overview of the DeltaCrown project structure, applications, and architecture

---

## 🎮 What is DeltaCrown?

**DeltaCrown** is a comprehensive esports tournament platform designed for Bangladesh and global markets. It enables:
- Tournament organization and management
- Team and player registration
- Payment processing (manual verification)
- Match scheduling and result reporting
- Dispute resolution workflows
- Real-time notifications
- Virtual economy (DeltaCoins)
- Multi-game support

**Tagline:** "From the Delta to the Crown — Where Champions Rise"

**Business Model:**
- Tournament entry fees (BDT/other currencies)
- Platform fees on transactions
- Sponsorship placements
- Future: Store/marketplace for gaming items

**Target Audience:**
- Tournament organizers
- Esports teams
- Individual players
- Sponsors and brands
- Gaming communities in Bangladesh and South Asia

---

## 📁 Project Structure

```
DeltaCrown/
├── manage.py                    # Django management script
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Python dependencies
├── README.md                    # Project README
│
├── deltacrown/                  # Project settings
│   ├── settings.py             # Main configuration
│   ├── urls.py                 # Root URL config
│   ├── wsgi.py                 # WSGI application
│   ├── asgi.py                 # ASGI for WebSockets
│   ├── celery.py               # Celery configuration
│   ├── test_runner.py          # Custom test runner
│   └── sitemaps.py             # SEO sitemap
│
├── apps/                        # Django applications
│   ├── accounts/               # User authentication
│   ├── common/                 # Shared utilities
│   ├── corelib/                # Core libraries
│   ├── corepages/              # Static pages
│   ├── dashboard/              # User dashboard
│   ├── ecommerce/              # Store (in development)
│   ├── economy/                # DeltaCoins system
│   ├── game_efootball/         # eFootball integration
│   ├── game_valorant/          # Valorant integration
│   ├── notifications/          # Notification system
│   ├── players/                # Player profiles
│   ├── search/                 # Search functionality
│   ├── siteui/                 # UI components
│   ├── support/                # Support system
│   ├── teams/                  # Team management
│   ├── tournaments/            # Tournament system (PRIMARY FOCUS)
│   └── user_profile/           # User profiles
│
├── templates/                   # Global templates
│   ├── base.html               # Base template
│   ├── home_modern.html        # Modern homepage
│   ├── home_cyberpunk.html     # Cyberpunk theme
│   ├── 403.html, 404.html, 500.html  # Error pages
│   ├── account/                # Account templates
│   ├── dashboard/              # Dashboard templates
│   ├── teams/                  # Team templates
│   ├── tournaments/            # Tournament templates
│   └── [other template dirs]
│
├── static/                      # Static files
│   ├── css/                    # Stylesheets
│   ├── js/                     # JavaScript
│   ├── img/                    # Images
│   └── [game-specific assets]
│
├── tests/                       # Test suite (94+ files)
│   ├── test_part1_tournament_core.py
│   ├── test_part2_game_configs.py
│   ├── test_part3_payments.py
│   ├── test_part4_teams.py
│   ├── test_part5_coin.py
│   └── [90+ more test files]
│
└── Documents/                   # Project documentation
    └── For_New_Tournament_design/  # This documentation package
```

---

## 🏗️ Application Architecture

### **Core Applications**

#### 1. **accounts** - User Authentication
- **Purpose:** Custom user model and authentication
- **Key Features:**
  - Custom `User` model extending Django's AbstractUser
  - Email or username login
  - Password reset functionality
  - Email/username backend authentication
  - Optional Google OAuth (django-allauth)

**Models:**
- `User` (custom AUTH_USER_MODEL)

**Dependencies:**
- Used by: ALL apps (authentication foundation)

---

#### 2. **tournaments** - Tournament Management (PRIMARY FOCUS)
- **Purpose:** Core tournament system
- **Size:** Largest app (~15,000+ lines of code)
- **Status:** Subject to complete redesign

**Key Features:**
- Tournament creation and lifecycle management
- Multiple game support (8 games)
- Registration system (team and solo)
- Payment verification workflow
- Match scheduling and management
- Bracket generation
- Dispute resolution
- Real-time updates via WebSockets
- State machine for tournament status
- Dynamic registration forms per game

**Models (20+):**
- `Tournament` - Main tournament model
- `TournamentSettings` - Configuration settings
- `TournamentSchedule` - Time management
- `TournamentCapacity` - Slot management
- `TournamentFinance` - Pricing and prizes
- `TournamentMedia` - Banners and media
- `TournamentRules` - Rules and regulations
- `TournamentArchive` - Historical data
- `Registration` - Team/player registrations
- `RegistrationRequest` - Registration queue
- `PaymentVerification` - Payment workflow
- `Bracket` - Tournament brackets
- `Match` - Individual matches
- `MatchAttendance` - Check-in tracking
- `MatchEvent` - Match timeline events
- `MatchComment` - Match comments
- `MatchDispute` - Dispute system
- `MatchDisputeEvidence` - Evidence uploads
- `GameConfiguration` - Dynamic game configs
- `GameFieldConfiguration` - Custom registration fields
- `PlayerRoleConfiguration` - Role requirements

**Structure:**
```
tournaments/
├── models/                      # Models split across files
│   ├── tournament.py
│   ├── registration.py
│   ├── match.py
│   ├── bracket.py
│   ├── dispute.py
│   ├── core/                   # Phase 1 refactored models
│   └── [15+ more model files]
├── admin/                       # Admin interfaces
│   ├── tournaments.py
│   ├── registrations.py
│   ├── matches.py
│   ├── brackets.py
│   └── [8+ more admin files]
├── views/                       # View layer
│   ├── detail_v8.py
│   ├── registration_unified.py
│   ├── hub_enhanced.py
│   └── [15+ more view files]
├── services/                    # Business logic
│   ├── registration_service.py
│   ├── game_config_service.py
│   └── [5+ more services]
├── validators/                  # Validation logic
├── api/                         # API endpoints
├── signals.py                   # Django signals (15+ handlers)
├── tasks.py                     # Celery tasks
├── consumers.py                 # WebSocket consumers
├── serializers.py               # DRF serializers
├── viewsets.py                  # DRF viewsets
└── [more files]
```

**Dependencies:**
- Depends on: `teams`, `user_profile`, `accounts`, `economy`, `notifications`
- Depends on: `game_valorant`, `game_efootball` (TIGHT COUPLING)
- Used by: `dashboard`, `search`

---

#### 3. **teams** - Team Management
- **Purpose:** Team creation and roster management
- **Key Features:**
  - Team creation and profiles
  - Captain and co-captain roles
  - Roster management
  - Team rankings
  - Game-specific configurations
  - Social media integration
  - Team analytics
  - Invitation system

**Models:**
- `Team` - Main team model
- `TeamMember` - Roster members
- `TeamInvite` - Invitation system
- `TeamRanking` - Ranking system
- `TeamSponsor` - Sponsorship
- Additional ranking and analytics models

**Structure:**
```
teams/
├── models/
│   ├── _legacy.py              # Main team model
│   ├── ranking.py
│   └── [other models]
├── admin.py                     # Admin interface
├── views/                       # Team views
├── forms.py                     # Team forms
├── services/                    # Business logic
├── signals/                     # Signal handlers
└── [more files]
```

**Dependencies:**
- Depends on: `accounts`, `user_profile`
- Used by: `tournaments`, `dashboard`, `search`

---

#### 4. **user_profile** - User Profiles
- **Purpose:** Extended user information and settings
- **Key Features:**
  - User profiles with avatars
  - Display names and bios
  - Profile customization
  - XP and badge system (planned)
  - User preferences

**Models:**
- `UserProfile` - Extended user information

**Dependencies:**
- Depends on: `accounts`
- Used by: `tournaments`, `teams`, `notifications`

---

#### 5. **economy** - Virtual Economy
- **Purpose:** DeltaCoins currency system
- **Key Features:**
  - Virtual currency (DeltaCoins)
  - Transaction tracking
  - Coin distribution on achievements
  - Wallet management
  - Transaction history

**Models:**
- `CoinTransaction` - Transaction records
- `Wallet` - User wallets
- Related models for coin management

**Dependencies:**
- Depends on: `accounts`, `user_profile`
- Used by: `tournaments` (payment rewards)

---

#### 6. **notifications** - Notification System
- **Purpose:** Multi-channel notification delivery
- **Key Features:**
  - In-app notifications
  - Email notifications (Gmail SMTP)
  - Discord webhook integration
  - Real-time push via Channels
  - Mark as read/unread
  - Notification preferences
  - Notification dashboard

**Notification Types:**
- Tournament registration
- Match results
- Team invitations
- Payment status
- Dispute updates
- System announcements

**Models:**
- `Notification` - Notification records
- `NotificationPreference` - User preferences

**Dependencies:**
- Depends on: `accounts`, `user_profile`, `teams`, `tournaments`
- Used by: All apps (notification consumers)

---

#### 7. **game_valorant** - Valorant Integration
- **Purpose:** Game-specific logic for Valorant
- **Key Features:**
  - Riot ID validation
  - Agent selection
  - Map pool configuration
  - Rank verification
  - Team composition rules
  - Match format (BO1, BO3, BO5)

**Models:**
- `ValorantConfig` - Per-tournament Valorant settings

**Validation Rules:**
- 5-player team requirement
- Riot ID format: `Username#TAG`
- Region-specific validation

**Dependencies:**
- Depends on: `tournaments` (TIGHT COUPLING)
- Used by: `tournaments`

**Problem:** Cannot add new games without creating similar apps

---

#### 8. **game_efootball** - eFootball Integration
- **Purpose:** Game-specific logic for eFootball
- **Key Features:**
  - Platform-specific player IDs
  - Team strength caps
  - Match duration settings
  - Extra time and penalty rules

**Models:**
- `EfootballConfig` - Per-tournament eFootball settings

**Dependencies:**
- Depends on: `tournaments` (TIGHT COUPLING)
- Used by: `tournaments`

**Problem:** Same tight coupling as Valorant

---

#### 9. **ecommerce** - E-commerce (In Development)
- **Purpose:** Store functionality
- **Key Features:**
  - Product management
  - Order processing
  - Bangladesh payment gateway integration (bKash/Nagad/Rocket)
  - Inventory management

**Models:**
- Product models
- Order models
- Payment configuration

**Status:** Partially implemented, not production-ready

---

#### 10. **dashboard** - User Dashboard
- **Purpose:** Centralized user interface
- **Key Features:**
  - Tournament overview
  - Team management shortcuts
  - Notification center
  - Quick actions
  - Statistics and analytics

**Dependencies:**
- Depends on: `tournaments`, `teams`, `notifications`, `economy`

---

#### 11. **common** - Shared Utilities
- **Purpose:** Reusable components across apps
- **Key Features:**
  - Template tags (SEO, assets, widgets)
  - Context processors
  - Utility functions
  - Shared validators

**Contents:**
- `templatetags/` - Custom template tags
- `context_processors.py` - Global context
- Shared utilities and helpers

---

#### 12. **siteui** - UI Components
- **Purpose:** Site-wide UI settings and components
- **Key Features:**
  - Navigation context
  - Site settings
  - Theme configuration
  - UI component library

---

#### 13. **corepages** - Static Pages
- **Purpose:** Marketing and informational pages
- **Pages:**
  - About Us
  - Community
  - Terms of Service
  - Privacy Policy
  - FAQ

---

#### 14. **search** - Search Functionality
- **Purpose:** Global search across entities
- **Key Features:**
  - Tournament search
  - Team search
  - Player search
  - Fuzzy matching

---

#### 15. **support** - Support System
- **Purpose:** Customer support and help
- **Key Features:**
  - Ticket system
  - FAQ management
  - Help center

---

#### 16. **players** - Player Profiles
- **Purpose:** Player-specific features
- **Key Features:**
  - Player statistics
  - Match history
  - Performance analytics

---

#### 17. **corelib** - Core Library
- **Purpose:** Low-level utilities and base classes
- **Contents:**
  - Base models
  - Common utilities
  - Framework extensions

---

## 🗄️ Database Architecture

**Database:** PostgreSQL  
**Version:** Compatible with PostgreSQL 12+  
**User:** `dc_user`  
**Database Name:** `deltacrown`  
**Timezone:** Asia/Dhaka

### Key Tables (Tournaments Focus)

| Table Name | Model | Rows (Est.) | Purpose |
|------------|-------|-------------|---------|
| tournaments_tournament | Tournament | 100+ | Main tournament records |
| tournaments_registration | Registration | 500+ | Team/player registrations |
| tournaments_match | Match | 1000+ | Match records |
| tournaments_bracket | Bracket | 200+ | Bracket structures |
| tournaments_tournamentsettings | TournamentSettings | 100+ | Tournament configurations |
| tournaments_paymentverification | PaymentVerification | 500+ | Payment workflow |
| game_valorant_valorantconfig | ValorantConfig | 50+ | Valorant-specific settings |
| game_efootball_efootballconfig | EfootballConfig | 50+ | eFootball-specific settings |
| teams_team | Team | 300+ | Team records |
| accounts_user | User | 1000+ | User accounts |

**Total Tables:** 100+ tables across all apps

---

## 🔐 Authentication System

**User Model:** Custom `accounts.User`  
**Authentication Backend:** `EmailOrUsernameBackend`

### Login Methods:
1. Username + Password
2. Email + Password
3. Google OAuth (optional, via django-allauth)

### User Flow:
```
1. Registration → Email verification (optional)
2. Login → Session creation
3. Profile creation → UserProfile auto-created
4. Team creation/joining → Team membership
5. Tournament registration → Registration record
```

### Permissions:
- Regular Users: Create teams, register for tournaments
- Staff: Access admin interface
- Superusers: Full system access

---

## 🌐 URL Structure

### Public URLs:
- `/` - Homepage
- `/tournaments/` - Tournament list
- `/tournaments/<slug>/` - Tournament detail
- `/teams/` - Team list
- `/teams/<slug>/` - Team detail
- `/profile/` - User profile

### Registration URLs:
- `/tournaments/register/<slug>/` - Legacy registration
- `/tournaments/register-enhanced/<slug>/` - Enhanced registration
- `/tournaments/register-modern/<slug>/` - Modern registration
- `/tournaments/register-unified/<slug>/` - Unified registration

**Problem:** Multiple registration endpoints showing evolution and lack of clarity

### API URLs:
- `/api/tournaments/` - Tournament API
- `/api/tournaments/<id>/schedule/` - Schedule API
- `/api/tournaments/<id>/capacity/` - Capacity API
- `/api/tournaments/<id>/finance/` - Finance API
- Many more RESTful endpoints

### Admin URL:
- `/admin/` - Django admin interface

---

## 📊 Key Metrics (Current System)

- **Lines of Code:** ~50,000+ (entire project)
- **Tournaments App:** ~15,000+ lines
- **Models:** 100+ models across all apps
- **Views:** 200+ view functions/classes
- **Templates:** 300+ template files
- **Tests:** 94+ test files
- **URL Patterns:** 150+ routes
- **Admin Interfaces:** 50+ admin classes
- **Signals:** 30+ signal handlers (15+ in tournaments alone)

---

## 🔄 Application Dependencies (Simplified)

```
accounts (User)
    ↓
user_profile (UserProfile)
    ↓
teams (Team) ←→ tournaments (Tournament) ←→ game_valorant
    ↓                    ↓                        ↓
economy             notifications           game_efootball
    ↓                    ↓
dashboard           (all apps)
```

**Problem:** Circular dependencies and tight coupling, especially around tournaments

---

## 🎯 Critical Integration Points

### 1. **Tournament → Teams**
- Teams register for tournaments
- Roster validation required
- Team game must match tournament game

### 2. **Tournament → Game Apps**
- ValorantConfig and EfootballConfig are OneToOne with Tournament
- Validation logic in game apps
- Cannot exist independently

### 3. **Tournament → Economy**
- Coins awarded on tournament participation
- Triggered via signals
- Payment processing tied to coin rewards

### 4. **Tournament → Notifications**
- Notifications sent on registration, match results, disputes
- Multi-channel delivery
- Real-time updates

### 5. **Tournament → User Profile**
- User profiles linked to registrations
- Captain/organizer roles
- Achievement tracking (planned)

---

## 📝 Configuration Files

### settings.py Highlights:
```python
AUTH_USER_MODEL = "accounts.User"
TIME_ZONE = "Asia/Dhaka"
DATABASES = PostgreSQL (dc_user)
CELERY_BROKER_URL = Redis
CHANNEL_LAYERS = InMemoryChannelLayer
```

### Key Settings:
- **DEBUG:** Configurable via environment
- **ALLOWED_HOSTS:** Supports ngrok for testing
- **INSTALLED_APPS:** 17 custom apps + Django/third-party
- **MIDDLEWARE:** Standard Django stack
- **TEMPLATES:** CKEditor 5 integration

---

## 🚀 Deployment Considerations

**Current Environment:** Development/Staging  
**Production Status:** Not fully production-ready

**Infrastructure Needs:**
- PostgreSQL database server
- Redis server (Celery + Channels)
- Static file serving (CDN recommended)
- Media file storage (S3-compatible)
- Email service (Gmail SMTP configured)
- WebSocket support (ASGI server)
- Background worker (Celery worker)

---

## 📖 Summary

DeltaCrown is a comprehensive Django application with 17 interconnected apps. The **tournaments** app is the core of the platform but suffers from tight coupling, signal complexity, and inflexible architecture. The current system works for MVP but cannot scale to support 50+ games or complex tournament formats without major refactoring.

**Next Document:** `02_CURRENT_TECH_STACK.md` - Detailed technology stack analysis
