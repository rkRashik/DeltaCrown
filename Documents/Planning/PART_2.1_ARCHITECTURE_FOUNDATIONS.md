# Part 2.1: Technical Architecture - Foundations & Core Models

**DeltaCrown Tournament Engine**  
**Date:** November 6, 2025  
**Document Version:** 1.0  
**Status:** Design Specification

---

## Navigation

- **← Previous:** [Part 1: Executive Summary](./PROPOSAL_PART_1_EXECUTIVE_SUMMARY.md)
- **↑ Index:** [Master Navigation](./INDEX_MASTER_NAVIGATION.md)
- **→ Next:** [Part 2.2: Service Layer & Integration](./PART_2.2_SERVICE_LAYER_INTEGRATION.md)

---

## Table of Contents (Part 2.1)

1. [Architecture Overview](#1-architecture-overview)
2. [Directory Structure](#2-directory-structure)
3. [App Breakdown & Responsibilities](#3-app-breakdown--responsibilities)
4. [Core Models & Database Schema (First Half)](#4-core-models--database-schema)

---

## 1. Architecture Overview

### 1.1 Design Principles

The DeltaCrown Tournament Engine follows these core principles:

**1. Modularity First**
- Each app has a single, well-defined responsibility
- Loose coupling between apps via service layers
- Easy to test, extend, and maintain

**2. Integration Over Isolation**
- Deep integration with existing DeltaCrown apps (Economy, Teams, UserProfile, Notifications, SiteUI)
- No REST API overhead (service layer communication)
- Leverages existing infrastructure (Celery, Redis, Channels)

**3. Django Best Practices**
- Fat models, thin views
- Service layer for complex business logic
- Signals for cross-app communication
- Manager methods for common queries

**4. Performance Conscious**
- select_related and prefetch_related everywhere
- Redis caching for frequently accessed data
- Celery for async operations
- Database indexes on foreign keys and query fields

**5. Future-Proof**
- JSONField for flexible custom data
- Versioning strategy for tournament configs
- Audit logs for all critical operations
- Clean migration path for future enhancements

### 1.2 Technology Stack

**Backend Framework:**
- Django 4.2+ (Python 3.11+)
- Django ORM (no raw SQL unless performance critical)
- Django Admin (customized for tournament management)

**Database:**
- PostgreSQL 14+ (primary database)
- JSONB fields for flexible data
- Full-text search capabilities
- Partitioning strategy for large tables (future)

**Caching & Async:**
- Redis 7+ (cache + Celery broker + Channels layer)
- Celery for background tasks
- Django Channels for WebSocket (real-time updates)

**Frontend:**
- Django Templates (not SPA)
- Tailwind CSS for styling
- HTMX for dynamic updates
- Alpine.js for lightweight interactivity
- Recharts via CDN for analytics

**File Storage:**
- Django's FileField/ImageField
- Cloud storage ready (S3-compatible)
- Local storage for development

### 1.3 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         DeltaCrown Platform                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Existing   │  │   Existing   │  │   Existing   │          │
│  │     Apps     │  │     Apps     │  │     Apps     │          │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤          │
│  │ • Economy    │  │ • Teams      │  │ • UserProfile│          │
│  │ • Notif.     │  │ • SiteUI     │  │ • Accounts   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
│         └──────────────────┼──────────────────┘                   │
│                            │                                      │
│         ┌──────────────────▼──────────────────┐                  │
│         │   Tournament Engine (Service Layer) │                  │
│         └──────────────────┬──────────────────┘                  │
│                            │                                      │
│  ┌─────────────────────────┼─────────────────────────┐          │
│  │         tournament_engine/ Directory               │          │
│  ├────────────────────────────────────────────────────┤          │
│  │                                                     │          │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │          │
│  │  │ Core     │  │ Bracket  │  │ Match    │         │          │
│  │  │ (Base)   │  │ (Logic)  │  │ (Flow)   │         │          │
│  │  └──────────┘  └──────────┘  └──────────┘         │          │
│  │                                                     │          │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │          │
│  │  │ Payment  │  │ Dispute  │  │ Certif.  │         │          │
│  │  │ (Verify) │  │ (Resolve)│  │ (Awards) │         │          │
│  │  └──────────┘  └──────────┘  └──────────┘         │          │
│  │                                                     │          │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │          │
│  │  │ Sponsor  │  │ Challenge│  │ Analytics│         │          │
│  │  │ (Manage) │  │ (Track)  │  │ (Stats)  │         │          │
│  │  └──────────┘  └──────────┘  └──────────┘         │          │
│  └─────────────────────────────────────────────────────┘          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
    ┌──────────┐         ┌──────────┐        ┌──────────┐
    │PostgreSQL│         │  Redis   │        │  Celery  │
    │ Database │         │  Cache   │        │  Workers │
    └──────────┘         └──────────┘        └──────────┘
```

---

## 2. Directory Structure

### 2.1 tournament_engine/ Organization

```
tournament_engine/
├── __init__.py
├── README.md                          # Overview of the engine
│
├── core/                              # Core tournament models and base logic
│   ├── __init__.py
│   ├── README.md                      # App documentation
│   ├── models.py                      # Tournament, Game, TournamentConfig
│   ├── services.py                    # Tournament creation, validation
│   ├── managers.py                    # Custom QuerySet managers
│   ├── admin.py                       # Django admin customization
│   ├── views.py                       # Tournament CRUD views
│   ├── urls.py
│   ├── forms.py                       # Tournament creation forms
│   ├── templatetags/
│   │   └── tournament_tags.py         # Template filters/tags
│   ├── migrations/
│   └── tests/
│       ├── test_models.py
│       ├── test_services.py
│       └── test_views.py
│
├── registration/                      # Registration and payment
│   ├── __init__.py
│   ├── README.md
│   ├── models.py                      # Registration, Payment, PaymentProof
│   ├── services.py                    # Registration logic, payment verification
│   ├── admin.py
│   ├── views.py                       # Registration flow, payment submission
│   ├── urls.py
│   ├── forms.py
│   ├── migrations/
│   └── tests/
│
├── bracket/                           # Bracket generation and structure
│   ├── __init__.py
│   ├── README.md
│   ├── models.py                      # Bracket, BracketNode, Seeding
│   ├── services.py                    # Bracket algorithms
│   ├── generators/                    # Bracket generation algorithms
│   │   ├── __init__.py
│   │   ├── single_elimination.py
│   │   ├── double_elimination.py
│   │   ├── round_robin.py
│   │   ├── swiss.py
│   │   └── group_playoff.py
│   ├── admin.py
│   ├── views.py                       # Bracket display, manual override
│   ├── urls.py
│   ├── migrations/
│   └── tests/
│
├── match/                             # Match management and state
│   ├── __init__.py
│   ├── README.md
│   ├── models.py                      # Match, MatchParticipant, MatchResult
│   ├── services.py                    # Match flow, state transitions
│   ├── state_machine.py               # Match state machine logic
│   ├── admin.py
│   ├── views.py                       # Match detail, score submission
│   ├── urls.py
│   ├── forms.py
│   ├── migrations/
│   └── tests/
│
├── dispute/                           # Dispute resolution
│   ├── __init__.py
│   ├── README.md
│   ├── models.py                      # Dispute, DisputeEvidence, DisputeResolution
│   ├── services.py                    # Dispute workflow
│   ├── admin.py
│   ├── views.py                       # Dispute submission, TO review
│   ├── urls.py
│   ├── forms.py
│   ├── migrations/
│   └── tests/
│
├── awards/                            # Certificates and achievements
│   ├── __init__.py
│   ├── README.md
│   ├── models.py                      # Certificate, Achievement, Badge
│   ├── services.py                    # Certificate generation
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── certificate_pdf.py         # PDF generation logic
│   │   └── templates/                 # Certificate templates
│   ├── admin.py
│   ├── views.py                       # Certificate display, download
│   ├── urls.py
│   ├── migrations/
│   └── tests/
│
├── sponsor/                           # Sponsor management
│   ├── __init__.py
│   ├── README.md
│   ├── models.py                      # Sponsor, TournamentSponsor, SponsorClick
│   ├── services.py                    # Sponsor analytics
│   ├── admin.py
│   ├── views.py                       # Sponsor tracking (click through)
│   ├── urls.py
│   ├── migrations/
│   └── tests/
│
├── challenge/                         # Custom challenges
│   ├── __init__.py
│   ├── README.md
│   ├── models.py                      # Challenge, ChallengeProgress, ChallengeCompletion
│   ├── services.py                    # Challenge tracking, verification
│   ├── admin.py
│   ├── views.py                       # Challenge leaderboard
│   ├── urls.py
│   ├── migrations/
│   └── tests/
│
├── analytics/                         # Stats and analytics
│   ├── __init__.py
│   ├── README.md
│   ├── models.py                      # TournamentStats, PlayerStats
│   ├── services.py                    # Analytics calculations
│   ├── admin.py
│   ├── views.py                       # Analytics dashboards
│   ├── urls.py
│   ├── migrations/
│   └── tests/
│
├── audit/                             # Audit logging
│   ├── __init__.py
│   ├── README.md
│   ├── models.py                      # AuditLog
│   ├── services.py                    # Logging utilities
│   ├── middleware.py                  # Request tracking
│   ├── admin.py
│   ├── views.py                       # Audit log viewer
│   ├── urls.py
│   ├── migrations/
│   └── tests/
│
├── utils/                             # Shared utilities
│   ├── __init__.py
│   ├── constants.py                   # Enums, choices
│   ├── validators.py                  # Custom validators
│   ├── decorators.py                  # Permission decorators
│   ├── exceptions.py                  # Custom exceptions
│   └── helpers.py                     # Helper functions
│
├── tasks.py                           # Celery tasks (all apps)
├── signals.py                         # Django signals
├── permissions.py                     # Permission classes
└── urls.py                            # URL routing (includes all app urls)
```

### 2.2 Naming Rationale

**Why `tournament_engine/` instead of `tournaments/`?**
- Distinguishes from legacy `apps/tournaments` (now in `legacy_backup/`)
- Emphasizes it's a complete engine, not just models
- Organizes multiple related apps under one namespace

**App Naming Logic:**
- **core**: Foundation models (Tournament, Game, Config)
- **registration**: Player/team joining process
- **bracket**: Structure and generation
- **match**: Live gameplay tracking
- **dispute**: Post-match resolution
- **awards**: Recognition system
- **sponsor**: Brand integration
- **challenge**: Bonus objectives
- **analytics**: Insights and stats
- **audit**: Security and compliance

Each app is **independently deployable** (loose coupling) but **deeply integrated** (via service layers).

---

## 3. App Breakdown & Responsibilities

### 3.1 Core App (`tournament_engine.core`)

**Purpose:** Central tournament management and configuration

**Key Models:**
- `Tournament` - Main tournament entity
- `Game` - Game definitions (Valorant, PUBG Mobile, etc.)
- `TournamentConfig` - JSON-based flexible configuration
- `CustomField` - User-defined tournament fields
- `OrganizerProfile` - Extended organizer information

**Key Services:**
- `TournamentService.create_tournament()` - Tournament creation with validation
- `TournamentService.publish_tournament()` - Approval and publishing
- `TournamentService.cancel_tournament()` - Cancellation with refunds
- `ConfigService.validate_config()` - Config validation
- `CustomFieldService.render_field()` - Dynamic field rendering

**Responsibilities:**
- Tournament CRUD operations
- Custom field management
- Tournament state transitions (Draft → Published → Live → Completed → Archived)
- Organizer verification
- Tournament search and filtering

**Integration Points:**
- `apps.accounts` - Organizer user references
- `apps.notifications` - Tournament announcements
- `tournament_engine.registration` - Link registration to tournaments

### 3.2 Registration App (`tournament_engine.registration`)

**Purpose:** Handle participant registration and payment verification

**Key Models:**
- `Registration` - Participant registration record
- `Payment` - Payment submission
- `PaymentProof` - Screenshot/reference storage
- `FeeWaiver` - Automatic waivers for top teams

**Key Services:**
- `RegistrationService.register_team()` - Team registration with roster validation
- `RegistrationService.register_individual()` - Solo tournament registration
- `PaymentService.submit_payment()` - Payment proof submission
- `PaymentService.verify_payment()` - Organizer verification
- `PaymentService.process_refund()` - Handle cancellations
- `WaiverService.check_eligibility()` - Auto-waiver for top teams

**Responsibilities:**
- Registration form auto-fill from UserProfile
- Team roster fetching from `apps.teams`
- Payment method handling (DeltaCoin, bKash, Nagad, Rocket, Bank)
- Payment verification workflow
- Registration status management

**Integration Points:**
- `apps.user_profile` - Auto-fill game IDs and personal info
- `apps.teams` - Fetch team roster and validate captain permissions
- `apps.economy` - DeltaCoin payment deduction
- `apps.notifications` - Registration confirmations
- `tournament_engine.core` - Link to tournament

### 3.3 Bracket App (`tournament_engine.bracket`)

**Purpose:** Generate and manage tournament brackets

**Key Models:**
- `Bracket` - Bracket container
- `BracketNode` - Individual bracket positions
- `Seeding` - Seeding configuration
- `Round` - Round tracking

**Key Services:**
- `BracketService.generate_bracket()` - Main generation entry point
- `BracketService.apply_seeding()` - Dynamic seeding from team rankings
- `BracketService.update_bracket()` - Progress bracket after match completion
- `GeneratorFactory.get_generator()` - Return appropriate algorithm

**Bracket Generators:**
- `SingleEliminationGenerator` - Standard knockout
- `DoubleEliminationGenerator` - Winners + Losers brackets
- `RoundRobinGenerator` - Everyone plays everyone
- `SwissGenerator` - Pairing based on standings
- `GroupPlayoffGenerator` - Groups → knockout

**Responsibilities:**
- Bracket algorithm implementation
- Dynamic seeding integration with `apps.teams.ranking_service`
- Manual bracket override for organizers
- Bracket state management
- Bye handling for odd participant counts

**Integration Points:**
- `apps.teams` - Ranking data for seeding
- `tournament_engine.registration` - Participant list
- `tournament_engine.match` - Create matches from bracket
- `tournament_engine.core` - Tournament configuration

### 3.4 Match App (`tournament_engine.match`)

**Purpose:** Manage match lifecycle and score tracking

**Key Models:**
- `Match` - Match entity
- `MatchParticipant` - Team/player in match
- `MatchResult` - Score submission
- `CheckIn` - Pre-match check-in
- `MatchLobby` - Discord/coordination info

**Key Services:**
- `MatchService.create_match()` - Match initialization
- `MatchService.check_in()` - Handle check-ins
- `MatchService.start_match()` - Begin match
- `MatchService.submit_score()` - Score submission
- `MatchService.confirm_match()` - Result confirmation
- `StateMachine.transition()` - State validation

**Match States:**
```
SCHEDULED → CHECK_IN → READY → LIVE → PENDING_RESULT → COMPLETED
                                              ↓
                                          DISPUTED
```

**Responsibilities:**
- Match state machine enforcement
- Check-in tracking (prevent no-shows)
- Score submission and validation
- Score mismatch detection
- Match progression trigger to bracket
- Live match tracking

**Integration Points:**
- `tournament_engine.bracket` - Bracket progression
- `tournament_engine.dispute` - Trigger disputes
- `tournament_engine.challenge` - Track challenge progress
- `apps.notifications` - Match notifications (start, end, dispute)
- Django Channels - Real-time updates

### 3.5 Dispute App (`tournament_engine.dispute`)

**Purpose:** Handle match disputes and resolution

**Key Models:**
- `Dispute` - Dispute entity
- `DisputeEvidence` - Screenshots, descriptions
- `DisputeResolution` - TO decision
- `DisputeComment` - Discussion thread

**Key Services:**
- `DisputeService.create_dispute()` - Initiate dispute
- `DisputeService.submit_evidence()` - Add evidence
- `DisputeService.resolve_dispute()` - TO decision
- `DisputeService.escalate()` - Admin escalation

**Responsibilities:**
- Dispute workflow management
- Evidence collection (screenshots, descriptions)
- TO review interface
- Dispute resolution with audit trail
- Auto-notification to all parties
- Escalation path for complex disputes

**Integration Points:**
- `tournament_engine.match` - Link to disputed match
- `tournament_engine.audit` - Full audit trail
- `apps.notifications` - Notify participants and TOs
- `apps.accounts` - TO/Admin permissions

### 3.6 Awards App (`tournament_engine.awards`)

**Purpose:** Generate certificates and track achievements

**Key Models:**
- `Certificate` - Digital certificate
- `Achievement` - Achievement definition
- `Badge` - Visual badge
- `AchievementProgress` - Progress tracking

**Key Services:**
- `CertificateService.generate()` - Create certificate PDF
- `CertificateService.verify()` - QR code verification
- `AchievementService.check_unlock()` - Unlock achievements
- `BadgeService.award_badge()` - Give badge to user

**Responsibilities:**
- PDF certificate generation (ReportLab)
- Certificate template management
- QR code generation for verification
- Achievement tracking (tournament-based, challenge-based)
- Badge awarding
- Profile integration

**Integration Points:**
- `tournament_engine.core` - Tournament completion trigger
- `tournament_engine.challenge` - Challenge completion
- `apps.user_profile` - Badge display on profiles
- `apps.notifications` - Achievement unlock notifications

### 3.7 Sponsor App (`tournament_engine.sponsor`)

**Purpose:** Manage tournament sponsors

**Key Models:**
- `Sponsor` - Sponsor entity
- `TournamentSponsor` - Link to tournament with tier
- `SponsorClick` - Click tracking

**Key Services:**
- `SponsorService.add_sponsor()` - Associate sponsor with tournament
- `SponsorService.track_click()` - Click-through tracking
- `SponsorService.generate_report()` - Sponsor ROI report

**Responsibilities:**
- Sponsor CRUD
- Tournament-sponsor association
- Tier management (Title, Platinum, Gold, Silver)
- Click tracking and analytics
- Sponsor visibility rules
- Report generation for sponsors

**Integration Points:**
- `tournament_engine.core` - Tournament association
- `tournament_engine.analytics` - Sponsor performance metrics

### 3.8 Challenge App (`tournament_engine.challenge`)

**Purpose:** Custom tournament challenges

**Key Models:**
- `Challenge` - Challenge definition
- `ChallengeProgress` - Per-participant progress
- `ChallengeCompletion` - Completion record

**Key Services:**
- `ChallengeService.create_challenge()` - Define challenge
- `ChallengeService.track_progress()` - Update progress
- `ChallengeService.verify_completion()` - Manual verification
- `ChallengeService.award_prizes()` - Distribute DeltaCoin

**Challenge Types:**
- `AUTOMATIC` - Tracked via stats integration
- `MANUAL` - Requires TO verification
- `HYBRID` - System flags, TO confirms

**Responsibilities:**
- Challenge definition and configuration
- Progress tracking per participant
- Evidence submission (for manual challenges)
- TO verification interface
- Prize distribution via `apps.economy`
- Leaderboard generation

**Integration Points:**
- `tournament_engine.match` - Match completion triggers
- `apps.economy` - DeltaCoin rewards
- `apps.notifications` - Challenge completion notifications

### 3.9 Analytics App (`tournament_engine.analytics`)

**Purpose:** Statistics and insights

**Key Models:**
- `TournamentStats` - Aggregated tournament metrics
- `PlayerStats` - Per-player performance
- `TeamStats` - Per-team performance
- `PlatformStats` - Platform-wide metrics

**Key Services:**
- `AnalyticsService.calculate_tournament_stats()` - Post-tournament analysis
- `AnalyticsService.update_player_stats()` - Cumulative player data
- `AnalyticsService.generate_leaderboard()` - Rankings
- `AnalyticsService.export_report()` - CSV/PDF export

**Responsibilities:**
- Statistics calculation and aggregation
- Performance tracking (wins, losses, placements)
- Leaderboard generation (global, per-game, seasonal)
- Organizer analytics (conversion rates, engagement)
- Platform analytics (admin dashboards)
- Data export for external tools

**Integration Points:**
- `tournament_engine.match` - Match results
- `tournament_engine.registration` - Participation data
- `apps.teams` - Team rankings integration
- All tournament apps - Data aggregation source

### 3.10 Audit App (`tournament_engine.audit`)

**Purpose:** Audit logging and compliance

**Key Models:**
- `AuditLog` - Audit record
- `ActionType` - Action enumeration

**Key Services:**
- `AuditService.log_action()` - Record action
- `AuditService.search_logs()` - Query audit trail
- `AuditService.export_logs()` - Compliance export

**Logged Actions:**
- Tournament creation, modification, deletion
- Score changes
- Prize adjustments
- Payment verifications
- Dispute resolutions
- Bracket manual overrides
- Permission changes

**Responsibilities:**
- Comprehensive action logging
- Searchable audit trail
- Compliance reporting
- Security monitoring
- Data retention policies

**Integration Points:**
- All tournament apps - Log critical actions
- Middleware - Automatic request tracking

---

## 4. Core Models & Database Schema

### 4.0 Base Mixins & Abstract Models

#### SoftDeleteMixin

```python
# tournament_engine/utils/mixins.py

from django.db import models
from django.utils import timezone

class SoftDeleteMixin(models.Model):
    """Mixin for soft deletion support"""
    
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deletions'
    )
    
    class Meta:
        abstract = True
    
    def soft_delete(self, user=None):
        """Soft delete the instance"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
    
    def restore(self):
        """Restore soft-deleted instance"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted objects by default"""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def with_deleted(self):
        """Include soft-deleted objects"""
        return super().get_queryset()
    
    def deleted_only(self):
        """Only soft-deleted objects"""
        return super().get_queryset().filter(is_deleted=True)


class TimestampedMixin(models.Model):
    """Mixin for automatic timestamp tracking"""
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
```

### 4.1 Core Models (tournament_engine.core)

#### Tournament Model

```python
from django.db import models
from django.contrib.postgres.fields import ArrayField
from apps.accounts.models import User
from tournament_engine.utils.mixins import SoftDeleteMixin, TimestampedMixin, SoftDeleteManager

class Tournament(SoftDeleteMixin, TimestampedMixin, models.Model):
    """Main tournament entity"""
    
    # Status choices
    DRAFT = 'draft'
    PENDING_APPROVAL = 'pending_approval'
    PUBLISHED = 'published'
    REGISTRATION_OPEN = 'registration_open'
    REGISTRATION_CLOSED = 'registration_closed'
    LIVE = 'live'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    ARCHIVED = 'archived'
    
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PENDING_APPROVAL, 'Pending Approval'),
        (PUBLISHED, 'Published'),
        (REGISTRATION_OPEN, 'Registration Open'),
        (REGISTRATION_CLOSED, 'Registration Closed'),
        (LIVE, 'Live'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (ARCHIVED, 'Archived'),
    ]
    
    # Basic info
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, db_index=True)
    description = models.TextField()
    
    # Organizer
    organizer = models.ForeignKey(
        User, 
        on_delete=models.PROTECT,
        related_name='organized_tournaments'
    )
    is_official = models.BooleanField(default=False)  # DeltaCrown official
    
    # Game
    game = models.ForeignKey(
        'Game', 
        on_delete=models.PROTECT,
        related_name='tournaments'
    )
    
    # Tournament format
    SINGLE_ELIM = 'single_elimination'
    DOUBLE_ELIM = 'double_elimination'
    ROUND_ROBIN = 'round_robin'
    SWISS = 'swiss'
    GROUP_PLAYOFF = 'group_playoff'
    
    FORMAT_CHOICES = [
        (SINGLE_ELIM, 'Single Elimination'),
        (DOUBLE_ELIM, 'Double Elimination'),
        (ROUND_ROBIN, 'Round Robin'),
        (SWISS, 'Swiss'),
        (GROUP_PLAYOFF, 'Group Stage + Playoff'),
    ]
    
    format = models.CharField(
        max_length=50, 
        choices=FORMAT_CHOICES,
        default=SINGLE_ELIM
    )
    
    # Participation
    TEAM = 'team'
    SOLO = 'solo'
    
    PARTICIPATION_TYPE_CHOICES = [
        (TEAM, 'Team'),
        (SOLO, 'Solo/Individual'),
    ]
    
    participation_type = models.CharField(
        max_length=20,
        choices=PARTICIPATION_TYPE_CHOICES,
        default=TEAM
    )
    
    # Capacity
    max_participants = models.PositiveIntegerField()
    min_participants = models.PositiveIntegerField(default=2)
    
    # Dates
    registration_start = models.DateTimeField()
    registration_end = models.DateTimeField()
    tournament_start = models.DateTimeField()
    tournament_end = models.DateTimeField(null=True, blank=True)
    
    # Prize
    prize_pool = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=0
    )
    prize_currency = models.CharField(
        max_length=10, 
        default='BDT'
    )
    prize_deltacoin = models.PositiveIntegerField(default=0)
    prize_distribution = models.JSONField(default=dict)  # {1: 50%, 2: 30%, 3: 20%}
    
    # Entry fee
    has_entry_fee = models.BooleanField(default=False)
    entry_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    entry_fee_currency = models.CharField(max_length=10, default='BDT')
    entry_fee_deltacoin = models.PositiveIntegerField(default=0)
    
    # Payment methods
    DELTACOIN = 'deltacoin'
    BKASH = 'bkash'
    NAGAD = 'nagad'
    ROCKET = 'rocket'
    BANK_TRANSFER = 'bank_transfer'
    
    PAYMENT_METHOD_CHOICES = [
        (DELTACOIN, 'DeltaCoin'),
        (BKASH, 'bKash'),
        (NAGAD, 'Nagad'),
        (ROCKET, 'Rocket'),
        (BANK_TRANSFER, 'Bank Transfer'),
    ]
    
    payment_methods = ArrayField(
        models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES),
        default=list,
        blank=True
    )
    
    # Fee waiver
    enable_fee_waiver = models.BooleanField(default=False)
    fee_waiver_top_n_teams = models.PositiveIntegerField(default=0)
    
    # Media
    banner_image = models.ImageField(
        upload_to='tournaments/banners/',
        null=True,
        blank=True
    )
    thumbnail_image = models.ImageField(
        upload_to='tournaments/thumbnails/',
        null=True,
        blank=True
    )
    rules_pdf = models.FileField(
        upload_to='tournaments/rules/',
        null=True,
        blank=True
    )
    promo_video_url = models.URLField(blank=True)
    
    # Streaming
    stream_youtube_url = models.URLField(blank=True)
    stream_twitch_url = models.URLField(blank=True)
    
    # Features
    enable_check_in = models.BooleanField(default=True)
    check_in_minutes_before = models.PositiveIntegerField(default=15)
    enable_dynamic_seeding = models.BooleanField(default=False)
    enable_live_updates = models.BooleanField(default=True)
    enable_certificates = models.BooleanField(default=True)
    enable_challenges = models.BooleanField(default=False)
    enable_fan_voting = models.BooleanField(default=False)
    
    # Rules
    rules_text = models.TextField(blank=True)
    
    # Status
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=DRAFT,
        db_index=True
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Stats (denormalized for performance)
    total_registrations = models.PositiveIntegerField(default=0)
    total_matches = models.PositiveIntegerField(default=0)
    completed_matches = models.PositiveIntegerField(default=0)
    
    # SEO
    meta_description = models.TextField(blank=True)
    meta_keywords = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True
    )
    
    class Meta:
        ordering = ['-tournament_start']
        indexes = [
            models.Index(fields=['status', 'tournament_start']),
            models.Index(fields=['game', 'status']),
            models.Index(fields=['organizer', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.game.name})"
    
    def is_registration_open(self):
        """Check if registration is currently open"""
        from django.utils import timezone
        now = timezone.now()
        return (
            self.status == self.REGISTRATION_OPEN and
            self.registration_start <= now <= self.registration_end
        )
    
    def spots_remaining(self):
        """Calculate remaining spots"""
        return max(0, self.max_participants - self.total_registrations)
```

#### Game Model

```python
class Game(models.Model):
    """Game definitions"""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    icon = models.ImageField(upload_to='games/icons/')
    
    # Team structure
    TEAM_SIZE_CHOICES = [
        (1, '1v1'),
        (2, '2v2'),
        (3, '3v3'),
        (4, '4v4'),
        (5, '5v5'),
        (0, 'Variable'),
    ]
    
    default_team_size = models.PositiveIntegerField(
        choices=TEAM_SIZE_CHOICES,
        default=5
    )
    
    # Game ID field in UserProfile
    profile_id_field = models.CharField(
        max_length=50,
        help_text="Field name in UserProfile (e.g., 'riot_id', 'steam_id')"
    )
    
    # Result types
    MAP_SCORE = 'map_score'
    BEST_OF = 'best_of'
    POINT_BASED = 'point_based'
    
    RESULT_TYPE_CHOICES = [
        (MAP_SCORE, 'Map Score (e.g., 13-11)'),
        (BEST_OF, 'Best of X'),
        (POINT_BASED, 'Point Based'),
    ]
    
    default_result_type = models.CharField(
        max_length=20,
        choices=RESULT_TYPE_CHOICES,
        default=MAP_SCORE
    )
    
    # Active status
    is_active = models.BooleanField(default=True)
    
    # Metadata
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
```

#### CustomField Model

```python
class CustomField(models.Model):
    """User-defined tournament fields"""
    
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='custom_fields'
    )
    
    # Field definition
    field_name = models.CharField(max_length=100)
    field_key = models.SlugField(max_length=120)  # For form field name
    
    TEXT = 'text'
    NUMBER = 'number'
    MEDIA = 'media'
    TOGGLE = 'toggle'
    DATE = 'date'
    URL = 'url'
    DROPDOWN = 'dropdown'
    
    FIELD_TYPE_CHOICES = [
        (TEXT, 'Text'),
        (NUMBER, 'Number'),
        (MEDIA, 'Media Upload'),
        (TOGGLE, 'Toggle (Yes/No)'),
        (DATE, 'Date'),
        (URL, 'URL'),
        (DROPDOWN, 'Dropdown'),
    ]
    
    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default=TEXT
    )
    
    # Field configuration
    field_config = models.JSONField(default=dict)  # {min_length, max_length, options, etc.}
    
    # Value
    field_value = models.JSONField(default=dict)  # Stores the actual value
    
    # Display
    order = models.PositiveIntegerField(default=0)
    is_required = models.BooleanField(default=False)
    help_text = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['order', 'field_name']
        unique_together = [['tournament', 'field_key']]
    
    def __str__(self):
        return f"{self.tournament.name} - {self.field_name}"
```

#### TournamentVersion Model

```python
from django.utils import timezone

class TournamentVersion(models.Model):
    """Stores configuration snapshots for rollback capability"""
    
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    
    # Snapshot of tournament configuration
    version_data = models.JSONField(
        help_text="Complete tournament config at this version"
    )
    
    # Change tracking
    change_summary = models.TextField(
        help_text="Human-readable summary of changes"
    )
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    # Rollback tracking
    is_active = models.BooleanField(default=True)
    rolled_back_at = models.DateTimeField(null=True, blank=True)
    rolled_back_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tournament_rollbacks'
    )
    
    class Meta:
        ordering = ['-version_number']
        unique_together = [('tournament', 'version_number')]
        indexes = [
            models.Index(fields=['tournament', '-version_number']),
            models.Index(fields=['changed_at']),
        ]
    
    def __str__(self):
        return f"{self.tournament.title} - v{self.version_number}"
```

**Usage in TournamentService:**

```python
@staticmethod
def create_version(tournament_id, changed_by, change_summary):
    """Create a new version snapshot"""
    from tournament_engine.core.models import Tournament, TournamentVersion
    
    tournament = Tournament.objects.get(id=tournament_id)
    latest_version = tournament.versions.order_by('-version_number').first()
    
    new_version_number = (latest_version.version_number + 1) if latest_version else 1
    
    # Serialize tournament config
    version_data = {
        'title': tournament.title,
        'format': tournament.format,
        'team_size': tournament.team_size,
        'max_participants': tournament.max_participants,
        'entry_fee': tournament.entry_fee,
        'prize_pool': tournament.prize_pool,
        'rules': tournament.rules,
        'config': tournament.config,
        'payment_methods': tournament.payment_methods,
        # ... other critical fields
    }
    
    TournamentVersion.objects.create(
        tournament=tournament,
        version_number=new_version_number,
        version_data=version_data,
        change_summary=change_summary,
        changed_by=changed_by
    )
    
    return new_version_number

@staticmethod
def rollback_to_version(tournament_id, version_number, rolled_back_by):
    """Rollback tournament to a specific version"""
    from tournament_engine.core.models import Tournament, TournamentVersion
    
    version = TournamentVersion.objects.get(
        tournament_id=tournament_id,
        version_number=version_number
    )
    
    tournament = Tournament.objects.get(id=tournament_id)
    
    # Restore from version_data
    for field, value in version.version_data.items():
        if hasattr(tournament, field):
            setattr(tournament, field, value)
    
    tournament.save()
    
    # Mark rollback in version history
    version.rolled_back_at = timezone.now()
    version.rolled_back_by = rolled_back_by
    version.save()
    
    # Create new version after rollback
    TournamentService.create_version(
        tournament_id,
        rolled_back_by,
        f"Rolled back to version {version_number}"
    )
```

### 4.2 Registration Models (tournament_engine.registration)

#### Registration Model

```python
class Registration(models.Model):
    """Tournament registration record"""
    
    tournament = models.ForeignKey(
        'core.Tournament',
        on_delete=models.CASCADE,
        related_name='registrations'
    )
    
    # Participant (either user or team, not both)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tournament_registrations'
    )
    team_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Reference to apps.teams.Team"
    )
    
    # Registration data (auto-filled + manual)
    registration_data = models.JSONField(default=dict)  # Name, game IDs, etc.
    
    # Status
    PENDING = 'pending'
    PAYMENT_PENDING = 'payment_pending'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'
    WAITLISTED = 'waitlisted'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAYMENT_PENDING, 'Payment Pending'),
        (CONFIRMED, 'Confirmed'),
        (REJECTED, 'Rejected'),
        (CANCELLED, 'Cancelled'),
        (WAITLISTED, 'Waitlisted'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True
    )
    
    # Payment
    payment_required = models.BooleanField(default=False)
    has_fee_waiver = models.BooleanField(default=False)
    waiver_reason = models.CharField(max_length=200, blank=True)
    
    # Timestamps
    registered_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['registered_at']
        unique_together = [['tournament', 'user'], ['tournament', 'team_id']]
        indexes = [
            models.Index(fields=['tournament', 'status']),
            models.Index(fields=['team_id']),
        ]
    
    def __str__(self):
        participant = self.user.username if self.user else f"Team {self.team_id}"
        return f"{self.tournament.name} - {participant}"
    
    def get_participant_name(self):
        """Get display name of participant"""
        if self.user:
            return self.user.get_full_name() or self.user.username
        else:
            # Fetch from teams app via service
            from tournament_engine.utils.helpers import get_team_name
            return get_team_name(self.team_id)
```

#### Payment Model

```python
class Payment(models.Model):
    """Payment submission for tournament entry"""
    
    registration = models.OneToOneField(
        Registration,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    
    # Payment method
    method = models.CharField(
        max_length=20,
        choices=Tournament.PAYMENT_METHOD_CHOICES
    )
    
    # Amount
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='BDT')
    deltacoin_amount = models.PositiveIntegerField(default=0)
    
    # Transaction details
    transaction_reference = models.CharField(
        max_length=200,
        blank=True,
        help_text="Transaction ID or reference number"
    )
    transaction_screenshot = models.ImageField(
        upload_to='payments/proofs/',
        null=True,
        blank=True
    )
    
    # Status
    SUBMITTED = 'submitted'
    VERIFIED = 'verified'
    REJECTED = 'rejected'
    REFUNDED = 'refunded'
    
    STATUS_CHOICES = [
        (SUBMITTED, 'Submitted'),
        (VERIFIED, 'Verified'),
        (REJECTED, 'Rejected'),
        (REFUNDED, 'Refunded'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=SUBMITTED,
        db_index=True
    )
    
    # Verification
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    user_notes = models.TextField(blank=True)
    organizer_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status', 'submitted_at']),
        ]
    
    def __str__(self):
        return f"Payment for {self.registration}"
```

### 4.3 Bracket Models (tournament_engine.bracket)

#### Bracket Model

```python
class Bracket(models.Model):
    """Bracket container for tournament"""
    
    tournament = models.OneToOneField(
        'core.Tournament',
        on_delete=models.CASCADE,
        related_name='bracket'
    )
    
    # Configuration
    format = models.CharField(max_length=50)  # Same as tournament format
    seeding_method = models.CharField(
        max_length=50,
        choices=[
            ('random', 'Random'),
            ('ranked', 'Ranked'),
            ('manual', 'Manual'),
        ],
        default='random'
    )
    
    # Structure
    bracket_structure = models.JSONField(
        default=dict,
        help_text="Complete bracket tree structure"
    )
    
    # Status
    PENDING = 'pending'
    GENERATED = 'generated'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    
    STATUS_CHOICES = [
```