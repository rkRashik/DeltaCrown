# Tournament Engine Development Proposal
## Part 2: Technical Architecture & System Design

**Date:** November 3, 2025  
**Project:** DeltaCrown Tournament Engine  
**Document Version:** 1.0  
**Status:** Design Specification

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Directory Structure](#2-directory-structure)
3. [App Breakdown & Responsibilities](#3-app-breakdown--responsibilities)
4. [Core Models & Database Schema](#4-core-models--database-schema)
5. [Service Layer Architecture](#5-service-layer-architecture)
6. [Integration Patterns](#6-integration-patterns)
7. [Real-Time Architecture](#7-real-time-architecture)
8. [Security Architecture](#8-security-architecture)
9. [Performance & Scalability](#9-performance--scalability)
10. [Testing Strategy](#10-testing-strategy)

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
        (PENDING, 'Pending'),
        (GENERATED, 'Generated'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )
    
    # Metadata
    total_rounds = models.PositiveIntegerField(default=0)
    current_round = models.PositiveIntegerField(default=0)
    generated_at = models.DateTimeField(null=True, blank=True)
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['tournament']
    
    def __str__(self):
        return f"Bracket for {self.tournament.name}"
```

#### BracketNode Model

```python
class BracketNode(models.Model):
    """Individual position in bracket"""
    
    bracket = models.ForeignKey(
        Bracket,
        on_delete=models.CASCADE,
        related_name='nodes'
    )
    
    # Position
    round_number = models.PositiveIntegerField()
    position_in_round = models.PositiveIntegerField()
    node_identifier = models.CharField(
        max_length=50,
        help_text="e.g., 'W1.1', 'L2.3' for winners/losers bracket"
    )
    
    # Participants (team_id or user_id)
    participant1_team_id = models.PositiveIntegerField(null=True, blank=True)
    participant1_user_id = models.PositiveIntegerField(null=True, blank=True)
    participant2_team_id = models.PositiveIntegerField(null=True, blank=True)
    participant2_user_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Winner
    winner_team_id = models.PositiveIntegerField(null=True, blank=True)
    winner_user_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Match reference
    match = models.OneToOneField(
        'match.Match',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bracket_node'
    )
    
    # Navigation (for progression)
    next_node_winner = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_winner_nodes'
    )
    next_node_loser = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_loser_nodes',
        help_text="For double elimination"
    )
    
    # Status
    is_bye = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['round_number', 'position_in_round']
        unique_together = [['bracket', 'node_identifier']]
        indexes = [
            models.Index(fields=['bracket', 'round_number']),
        ]
    
    def __str__(self):
        return f"{self.bracket.tournament.name} - {self.node_identifier}"
```

### 4.4 Match Models (tournament_engine.match)

#### Match Model

```python
class Match(models.Model):
    """Individual match in tournament"""
    
    tournament = models.ForeignKey(
        'core.Tournament',
        on_delete=models.CASCADE,
        related_name='matches'
    )
    
    bracket = models.ForeignKey(
        'bracket.Bracket',
        on_delete=models.CASCADE,
        related_name='matches',
        null=True,
        blank=True
    )
    
    # Match info
    match_number = models.PositiveIntegerField()
    round_number = models.PositiveIntegerField()
    
    # Participants
    participant1_team_id = models.PositiveIntegerField(null=True, blank=True)
    participant1_user_id = models.PositiveIntegerField(null=True, blank=True)
    participant2_team_id = models.PositiveIntegerField(null=True, blank=True)
    participant2_user_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Schedule
    scheduled_time = models.DateTimeField(null=True, blank=True)
    
    # Check-in
    check_in_deadline = models.DateTimeField(null=True, blank=True)
    participant1_checked_in = models.BooleanField(default=False)
    participant2_checked_in = models.BooleanField(default=False)
    participant1_check_in_time = models.DateTimeField(null=True, blank=True)
    participant2_check_in_time = models.DateTimeField(null=True, blank=True)
    
    # State
    SCHEDULED = 'scheduled'
    CHECK_IN = 'check_in'
    READY = 'ready'
    LIVE = 'live'
    PENDING_RESULT = 'pending_result'
    COMPLETED = 'completed'
    DISPUTED = 'disputed'
    CANCELLED = 'cancelled'
    
    STATE_CHOICES = [
        (SCHEDULED, 'Scheduled'),
        (CHECK_IN, 'Check-in Period'),
        (READY, 'Ready to Start'),
        (LIVE, 'Live'),
        (PENDING_RESULT, 'Pending Result'),
        (COMPLETED, 'Completed'),
        (DISPUTED, 'Disputed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default=SCHEDULED,
        db_index=True
    )
    
    # Results
    participant1_score = models.PositiveIntegerField(null=True, blank=True)
    participant2_score = models.PositiveIntegerField(null=True, blank=True)
    winner_team_id = models.PositiveIntegerField(null=True, blank=True)
    winner_user_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Result submission
    participant1_submitted_score = models.BooleanField(default=False)
    participant2_submitted_score = models.BooleanField(default=False)
    scores_match = models.BooleanField(default=False)
    
    # Lobby info
    lobby_info = models.JSONField(
        default=dict,
        help_text="Discord link, lobby code, etc."
    )
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['tournament', 'round_number', 'match_number']
        indexes = [
            models.Index(fields=['tournament', 'state']),
            models.Index(fields=['scheduled_time']),
        ]
        verbose_name_plural = 'matches'
    
    def __str__(self):
        return f"Match #{self.match_number} - {self.tournament.name}"
    
    def get_participant1_name(self):
        """Get participant 1 display name"""
        from tournament_engine.utils.helpers import get_participant_name
        return get_participant_name(
            team_id=self.participant1_team_id,
            user_id=self.participant1_user_id
        )
    
    def get_participant2_name(self):
        """Get participant 2 display name"""
        from tournament_engine.utils.helpers import get_participant_name
        return get_participant_name(
            team_id=self.participant2_team_id,
            user_id=self.participant2_user_id
        )
```

#### MatchResult Model

```python
class MatchResult(models.Model):
    """Score submission for match"""
    
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name='result_submissions'
    )
    
    # Submitter
    submitted_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    is_participant1 = models.BooleanField()
    
    # Scores
    participant1_score = models.PositiveIntegerField()
    participant2_score = models.PositiveIntegerField()
    
    # Evidence
    screenshot = models.ImageField(
        upload_to='matches/results/',
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)
    
    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Result for {self.match} by {self.submitted_by_user.username}"
```

### 4.5 Dispute Model (tournament_engine.dispute)

```python
class Dispute(models.Model):
    """Match dispute"""
    
    match = models.ForeignKey(
        'match.Match',
        on_delete=models.CASCADE,
        related_name='disputes'
    )
    
    # Initiator
    initiated_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='initiated_disputes'
    )
    
    # Dispute info
    SCORE_MISMATCH = 'score_mismatch'
    NO_SHOW = 'no_show'
    CHEATING = 'cheating'
    TECHNICAL_ISSUE = 'technical_issue'
    OTHER = 'other'
    
    REASON_CHOICES = [
        (SCORE_MISMATCH, 'Score Mismatch'),
        (NO_SHOW, 'No Show'),
        (CHEATING, 'Cheating Accusation'),
        (TECHNICAL_ISSUE, 'Technical Issue'),
        (OTHER, 'Other'),
    ]
    
    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES
    )
    description = models.TextField()
    
    # Evidence
    evidence_screenshot = models.ImageField(
        upload_to='disputes/evidence/',
        null=True,
        blank=True
    )
    evidence_video_url = models.URLField(blank=True)
    
    # Status
    OPEN = 'open'
    UNDER_REVIEW = 'under_review'
    RESOLVED = 'resolved'
    ESCALATED = 'escalated'
    
    STATUS_CHOICES = [
        (OPEN, 'Open'),
        (UNDER_REVIEW, 'Under Review'),
        (RESOLVED, 'Resolved'),
        (ESCALATED, 'Escalated to Admin'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=OPEN,
        db_index=True
    )
    
    # Resolution
    resolved_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_disputes'
    )
    resolution_notes = models.TextField(blank=True)
    final_participant1_score = models.PositiveIntegerField(null=True, blank=True)
    final_participant2_score = models.PositiveIntegerField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['match', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Dispute for {self.match} - {self.reason}"
```

### 4.6 Awards Models (tournament_engine.awards)

```python
class Certificate(models.Model):
    """Digital certificate"""
    
    tournament = models.ForeignKey(
        'core.Tournament',
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    
    # Recipient
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tournament_certificates'
    )
    team_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Certificate info
    CHAMPION = 'champion'
    RUNNER_UP = 'runner_up'
    THIRD_PLACE = 'third_place'
    PARTICIPANT = 'participant'
    MVP = 'mvp'
    
    CERTIFICATE_TYPE_CHOICES = [
        (CHAMPION, 'Champion'),
        (RUNNER_UP, 'Runner-up'),
        (THIRD_PLACE, 'Third Place'),
        (PARTICIPANT, 'Participant'),
        (MVP, 'MVP'),
    ]
    
    certificate_type = models.CharField(
        max_length=20,
        choices=CERTIFICATE_TYPE_CHOICES
    )
    placement = models.PositiveIntegerField(null=True, blank=True)
    
    # Certificate file
    pdf_file = models.FileField(
        upload_to='certificates/pdfs/',
        null=True,
        blank=True
    )
    
    # Verification
    verification_code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True
    )
    qr_code_image = models.ImageField(
        upload_to='certificates/qr/',
        null=True,
        blank=True
    )
    
    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['tournament', 'certificate_type']),
        ]
    
    def __str__(self):
        recipient = self.user.username if self.user else f"Team {self.team_id}"
        return f"{self.certificate_type} - {recipient}"
```

---

## 5. Service Layer Architecture

### 5.1 Service Layer Pattern

**Purpose:** Encapsulate complex business logic outside of models and views.

**Benefits:**
- Reusable across views, Celery tasks, management commands
- Easier to test (unit tests for services)
- Clean separation of concerns
- Integration point for cross-app communication

**Structure:**
```python
# tournament_engine/core/services.py

class TournamentService:
    """Service for tournament operations"""
    
    @staticmethod
    def create_tournament(organizer, tournament_data):
        """
        Create tournament with validation
        
        Args:
            organizer (User): Tournament organizer
            tournament_data (dict): Tournament configuration
            
        Returns:
            Tournament: Created tournament instance
            
        Raises:
            ValidationError: If data invalid
        """
        # Validation logic
        # Create tournament
        # Create audit log
        # Send notifications
        pass
    
    @staticmethod
    def publish_tournament(tournament_id, published_by):
        """Publish tournament and generate bracket"""
        pass
    
    @staticmethod
    def cancel_tournament(tournament_id, reason, cancelled_by):
        """Cancel tournament and process refunds"""
        pass
```

### 5.2 Key Service Methods

#### TournamentService (core/services.py)

- `create_tournament()` - Create with validation
- `update_tournament()` - Update configuration
- `publish_tournament()` - Make public + generate bracket
- `cancel_tournament()` - Cancel + refunds
- `archive_tournament()` - Move to archive
- `duplicate_tournament()` - Tournament templates

#### RegistrationService (registration/services.py)

- `register_participant()` - Register team/user
- `auto_fill_registration_data()` - Pull from UserProfile/Teams
- `check_registration_eligibility()` - Validate constraints
- `cancel_registration()` - Withdraw + refund
- `apply_fee_waiver()` - Auto-waiver for top teams

#### PaymentService (registration/services.py)

- `submit_payment()` - Payment proof submission
- `verify_payment()` - Organizer verification
- `process_deltacoin_payment()` - Integrate with apps.economy
- `process_refund()` - Handle cancellations
- `bulk_verify_payments()` - Bulk action

#### BracketService (bracket/services.py)

- `generate_bracket()` - Main entry point
- `apply_dynamic_seeding()` - Fetch rankings from apps.teams
- `update_bracket_after_match()` - Progress winners
- `manual_override_bracket()` - TO adjustments
- `recalculate_bracket()` - Regenerate if needed

#### MatchService (match/services.py)

- `create_matches_from_bracket()` - Generate matches
- `handle_check_in()` - Check-in logic
- `transition_state()` - State machine
- `submit_score()` - Score submission
- `confirm_result()` - Finalize match
- `trigger_dispute()` - Create dispute

#### DisputeService (dispute/services.py)

- `create_dispute()` - Initiate dispute
- `submit_evidence()` - Add evidence
- `resolve_dispute()` - TO decision
- `escalate_dispute()` - Admin escalation
- `apply_resolution()` - Update match result

#### CertificateService (awards/services.py)

- `generate_certificates()` - Batch generation
- `generate_certificate_pdf()` - PDF creation
- `generate_qr_code()` - Verification QR
- `verify_certificate()` - Public verification

#### ChallengeService (challenge/services.py)

- `create_challenge()` - Define challenge
- `track_progress()` - Update progress
- `verify_completion()` - Manual verify
- `award_challenge_prizes()` - DeltaCoin distribution

#### AnalyticsService (analytics/services.py)

- `calculate_tournament_stats()` - Post-tournament
- `update_player_stats()` - Cumulative stats
- `generate_leaderboard()` - Rankings
- `export_analytics()` - CSV/PDF export

#### AuditService (audit/services.py)

- `log_action()` - Record action
- `search_audit_logs()` - Query logs
- `export_audit_trail()` - Compliance export

---

## 6. Integration Patterns

### 6.1 Integration with apps.economy

**DeltaCoin Transactions:**

```python
# tournament_engine/registration/services.py

from apps.economy.services import award, deduct

class PaymentService:
    
    @staticmethod
    def process_deltacoin_payment(registration):
        """Deduct DeltaCoin for entry fee"""
        try:
            # Deduct entry fee
            deduct(
                user=registration.user,
                amount=registration.tournament.entry_fee_deltacoin,
                reason=f"Tournament entry: {registration.tournament.name}",
                idempotency_key=f"tournament_entry_{registration.id}"
            )
            
            # Update registration
            registration.status = Registration.CONFIRMED
            registration.save()
            
            return True
        except InsufficientBalanceError:
            return False
    
    @staticmethod
    def process_prize_distribution(tournament):
        """Distribute DeltaCoin prizes"""
        from tournament_engine.analytics.services import AnalyticsService
        
        # Get final standings
        standings = AnalyticsService.get_final_standings(tournament)
        
        for placement, (participant_id, is_team) in standings.items():
            # Calculate prize
            prize_amount = calculate_prize(
                tournament.prize_deltacoin,
                tournament.prize_distribution,
                placement
            )
            
            if prize_amount > 0:
                # Award prize
                if is_team:
                    # Award to team members
                    team_members = get_team_members(participant_id)
                    per_member = prize_amount // len(team_members)
                    
                    for member in team_members:
                        award(
                            user=member,
                            amount=per_member,
                            reason=f"Tournament prize: {tournament.name} (Placement: {placement})",
                            idempotency_key=f"tournament_prize_{tournament.id}_{member.id}_{placement}"
                        )
                else:
                    # Award to individual
                    user = User.objects.get(id=participant_id)
                    award(
                        user=user,
                        amount=prize_amount,
                        reason=f"Tournament prize: {tournament.name} (Placement: {placement})",
                        idempotency_key=f"tournament_prize_{tournament.id}_{user.id}_{placement}"
                    )
```

### 6.2 Integration with apps.teams

**Fetch Team Data:**

```python
# tournament_engine/utils/helpers.py

def get_team_name(team_id):
    """Fetch team name from apps.teams"""
    from apps.teams.models import Team
    try:
        team = Team.objects.get(id=team_id)
        return team.name
    except Team.DoesNotExist:
        return f"Team #{team_id}"

def get_team_roster(team_id, game_slug):
    """Fetch team roster for specific game"""
    from apps.teams.models import Team
    
    team = Team.objects.get(id=team_id)
    # Logic to get game-specific roster
    # (depends on apps.teams structure)
    pass

def get_team_ranking(team_id):
    """Fetch team ranking for seeding"""
    from apps.teams.services import ranking_service
    
    return ranking_service.get_team_rank(team_id)
```

**Update Team Rankings:**

```python
# tournament_engine/analytics/services.py

class AnalyticsService:
    
    @staticmethod
    def update_team_rankings(tournament):
        """Update team rankings after tournament"""
        from apps.teams.services import ranking_service
        
        standings = AnalyticsService.get_final_standings(tournament)
        
        for placement, (team_id, is_team) in standings.items():
            if is_team:
                # Calculate points based on placement
                points = calculate_ranking_points(placement, tournament.prize_pool)
                
                # Update via teams service
                ranking_service.add_tournament_result(
                    team_id=team_id,
                    tournament_name=tournament.name,
                    placement=placement,
                    points=points
                )
```

### 6.3 Integration with apps.user_profile

**Auto-fill Registration:**

```python
# tournament_engine/registration/services.py

class RegistrationService:
    
    @staticmethod
    def auto_fill_registration_data(user, tournament):
        """Pull data from UserProfile"""
        from apps.user_profile.models import UserProfile
        
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return {}
        
        # Get game-specific ID
        game_id_field = tournament.game.profile_id_field
        game_id = getattr(profile, game_id_field, None)
        
        data = {
            'full_name': user.get_full_name(),
            'email': user.email,
            'discord_id': profile.discord_id,
            'game_id': game_id,
            # Add more fields as needed
        }
        
        return data
```

### 6.4 Integration with apps.notifications

**Tournament Notifications:**

```python
# tournament_engine/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from tournament_engine.core.models import Tournament
from apps.notifications.services import NotificationService

@receiver(post_save, sender=Tournament)
def tournament_published(sender, instance, created, **kwargs):
    """Notify when tournament published"""
    if not created and instance.status == Tournament.PUBLISHED:
        # Notify followers
        NotificationService.send_notification(
            notification_type='TOURNAMENT_PUBLISHED',
            recipients=get_game_followers(instance.game),
            context={
                'tournament_name': instance.name,
                'tournament_url': instance.get_absolute_url(),
            }
        )
```

### 6.5 Integration with apps.siteui (Community)

**Discussion Threads:**

```python
# tournament_engine/core/models.py

class Tournament(models.Model):
    # ... existing fields ...
    
    discussion_thread_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Reference to siteui discussion thread"
    )
    
    def get_discussion_thread(self):
        """Get associated discussion thread"""
        if self.discussion_thread_id:
            from apps.siteui.models import Post
            try:
                return Post.objects.get(id=self.discussion_thread_id)
            except Post.DoesNotExist:
                return None
        return None
```

### 6.6 Event Bus Architecture (Centralized Event Dispatch)

**Purpose:** Decouple cross-app event handling and enable clean subscription patterns.

**Event Bus Implementation:**

```python
# tournament_engine/events.py

from typing import Dict, List, Callable, Any
from django.dispatch import Signal
import logging

logger = logging.getLogger(__name__)

class TournamentEventBus:
    """Centralized event dispatcher for tournament engine"""
    
    # Define event signals
    TOURNAMENT_PUBLISHED = Signal()
    REGISTRATION_CONFIRMED = Signal()
    BRACKET_GENERATED = Signal()
    MATCH_STARTED = Signal()
    MATCH_COMPLETED = Signal()
    DISPUTE_CREATED = Signal()
    DISPUTE_RESOLVED = Signal()
    TOURNAMENT_CONCLUDED = Signal()
    CERTIFICATE_GENERATED = Signal()
    CHALLENGE_COMPLETED = Signal()
    
    _subscribers: Dict[str, List[Callable]] = {}
    
    @classmethod
    def subscribe(cls, event_type: str, handler: Callable):
        """Subscribe to an event type"""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(handler)
        logger.info(f"Subscribed {handler.__name__} to {event_type}")
    
    @classmethod
    def dispatch(cls, event_type: str, payload: Dict[str, Any]):
        """Dispatch event to all subscribers"""
        logger.info(f"Dispatching event: {event_type}")
        
        # Call all subscribers
        handlers = cls._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                logger.error(f"Error in {handler.__name__}: {e}")
        
        # Also emit Django signal (for backward compatibility)
        signal = getattr(cls, event_type.upper(), None)
        if signal:
            signal.send(sender=cls, payload=payload)
    
    @classmethod
    def dispatch_async(cls, event_type: str, payload: Dict[str, Any]):
        """Dispatch event asynchronously via Celery"""
        from tournament_engine.tasks import process_event_async
        process_event_async.delay(event_type, payload)


# Event Subscribers (auto-registered)

def subscribe_analytics_updates():
    """Register analytics listeners"""
    from tournament_engine.analytics.services import AnalyticsService
    
    def on_match_completed(payload):
        AnalyticsService.update_stats_after_match(payload['match_id'])
    
    def on_tournament_concluded(payload):
        AnalyticsService.calculate_tournament_stats(payload['tournament_id'])
    
    TournamentEventBus.subscribe('match_completed', on_match_completed)
    TournamentEventBus.subscribe('tournament_concluded', on_tournament_concluded)

def subscribe_notification_triggers():
    """Register notification listeners"""
    from apps.notifications.services import NotificationService
    
    def on_match_started(payload):
        NotificationService.send_match_start_notification(payload['match_id'])
    
    def on_dispute_created(payload):
        NotificationService.send_dispute_notification(payload['dispute_id'])
    
    TournamentEventBus.subscribe('match_started', on_match_started)
    TournamentEventBus.subscribe('dispute_created', on_dispute_created)

def subscribe_ranking_updates():
    """Register ranking system listeners"""
    from apps.teams.services import ranking_service
    
    def on_tournament_concluded(payload):
        ranking_service.update_rankings_from_tournament(payload['tournament_id'])
    
    TournamentEventBus.subscribe('tournament_concluded', on_tournament_concluded)

# Auto-register all subscribers on app ready
def register_all_event_subscribers():
    """Called from apps.py ready()"""
    subscribe_analytics_updates()
    subscribe_notification_triggers()
    subscribe_ranking_updates()
```

**Usage in Services:**

```python
# tournament_engine/match/services.py

class MatchService:
    
    @staticmethod
    def complete_match(match_id):
        """Complete match and trigger events"""
        match = Match.objects.get(id=match_id)
        match.state = Match.COMPLETED
        match.completed_at = timezone.now()
        match.save()
        
        # Dispatch event (triggers analytics, notifications, bracket update)
        TournamentEventBus.dispatch('match_completed', {
            'match_id': match.id,
            'tournament_id': match.tournament_id,
            'winner_team_id': match.winner_team_id,
            'winner_user_id': match.winner_user_id,
        })
```

**Benefits:**
- ✅ Decouples services (no direct imports between apps)
- ✅ Easy to add new subscribers without modifying existing code
- ✅ Clear event flow for debugging
- ✅ Async dispatch option for performance
- ✅ Testable (can mock event bus in tests)

---

## 7. Real-Time Architecture

### 7.1 Django Channels Setup

**Purpose:** Real-time updates for live brackets, scoreboards, notifications

**Channel Layers Configuration:**

```python
# deltacrown/settings.py

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

### 7.2 WebSocket Consumers

```python
# tournament_engine/consumers.py

from channels.generic.websocket import AsyncJsonWebsocketConsumer

class TournamentConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for tournament updates"""
    
    async def connect(self):
        self.tournament_id = self.scope['url_route']['kwargs']['tournament_id']
        self.room_group_name = f'tournament_{self.tournament_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from room group
    async def tournament_update(self, event):
        """Send tournament update to WebSocket"""
        await self.send_json({
            'type': event['update_type'],
            'data': event['data']
        })
```

### 7.3 Broadcasting Updates

```python
# tournament_engine/match/services.py

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class MatchService:
    
    @staticmethod
    def broadcast_match_update(match):
        """Broadcast match update to tournament room"""
        channel_layer = get_channel_layer()
        
        async_to_sync(channel_layer.group_send)(
            f'tournament_{match.tournament_id}',
            {
                'type': 'tournament_update',
                'update_type': 'match_update',
                'data': {
                    'match_id': match.id,
                    'state': match.state,
                    'participant1_score': match.participant1_score,
                    'participant2_score': match.participant2_score,
                }
            }
        )
```

---

## 7.4 Frontend System Architecture

**Purpose:** Bridge Part 1 UI/UX specifications with Part 2 technical architecture for frontend implementation

### Technology Stack

- **Template Engine:** Django Templates with inheritance
- **CSS Framework:** Tailwind CSS 3.x (utility-first)
- **JavaScript Enhancement:** HTMX (declarative AJAX) + Alpine.js (reactive components)
- **Icons:** Heroicons + custom tournament icons
- **Charts:** Chart.js for analytics visualizations

### Layout Structure

```
templates/
├── base.html                    # Root layout (navbar, footer, global scripts)
├── tournaments/
│   ├── base_tournament.html     # Tournament-specific layout (extends base.html)
│   ├── list.html                # Tournament listing
│   ├── detail.html              # Tournament detail page
│   ├── create.html              # Tournament creation wizard
│   ├── dashboard.html           # Organizer dashboard
│   ├── registration/
│   │   ├── form.html            # Registration form
│   │   ├── payment.html         # Payment submission
│   │   └── confirmation.html    # Registration success
│   ├── bracket/
│   │   ├── view.html            # Bracket visualization
│   │   └── match_card.html      # Match detail component (HTMX partial)
│   ├── matches/
│   │   ├── live_scoreboard.html # Live match scoreboard
│   │   └── result_form.html     # Result submission
│   └── partials/
│       ├── tournament_card.html # Reusable tournament card
│       ├── player_card.html     # Participant card
│       └── sponsor_logo.html    # Sponsor display
```

### Template Inheritance Pattern

```django
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}DeltaCrown{% endblock %}</title>
    
    <!-- Tailwind CSS -->
    <link href="{% static 'css/tailwind.output.css' %}" rel="stylesheet">
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    
    <!-- Alpine.js -->
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
    
    {% block extra_head %}{% endblock %}
</head>
<body class="bg-gray-900 text-white">
    {% include 'partials/navbar.html' %}
    
    <main class="container mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>
    
    {% include 'partials/footer.html' %}
    
    {% block extra_scripts %}{% endblock %}
</body>
</html>

<!-- templates/tournaments/base_tournament.html -->
{% extends 'base.html' %}

{% block content %}
<div class="tournament-layout">
    <!-- Tournament header -->
    <div class="tournament-header mb-6">
        {% block tournament_header %}{% endblock %}
    </div>
    
    <!-- Tournament content -->
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <!-- Sidebar -->
        <aside class="lg:col-span-1">
            {% block tournament_sidebar %}
                {% include 'tournaments/partials/sidebar.html' %}
            {% endblock %}
        </aside>
        
        <!-- Main content -->
        <section class="lg:col-span-3">
            {% block tournament_content %}{% endblock %}
        </section>
    </div>
</div>
{% endblock %}
```

### HTMX Integration Patterns

**1. Live Match Updates (WebSocket + HTMX)**

```django
<!-- templates/tournaments/matches/live_scoreboard.html -->
<div 
    hx-ext="ws"
    ws-connect="/ws/tournament/{{ tournament.id }}/"
    class="scoreboard"
>
    <div id="match-{{ match.id }}" class="match-card">
        <div class="team-score">
            <span class="team-name">{{ match.participant1_name }}</span>
            <span class="score" id="p1-score">{{ match.participant1_score }}</span>
        </div>
        <div class="vs">VS</div>
        <div class="team-score">
            <span class="team-name">{{ match.participant2_name }}</span>
            <span class="score" id="p2-score">{{ match.participant2_score }}</span>
        </div>
    </div>
</div>

<script>
    // Handle WebSocket updates
    document.body.addEventListener('tournament_update', function(event) {
        if (event.detail.type === 'match_update') {
            const data = event.detail.data;
            document.getElementById('p1-score').textContent = data.participant1_score;
            document.getElementById('p2-score').textContent = data.participant2_score;
        }
    });
</script>
```

**2. Dynamic Tournament Registration**

```django
<!-- templates/tournaments/registration/form.html -->
<form 
    hx-post="{% url 'tournament:register' tournament.id %}"
    hx-target="#registration-result"
    hx-swap="innerHTML"
    class="registration-form"
>
    {% csrf_token %}
    
    <!-- Auto-filled fields from user profile -->
    <input type="text" name="display_name" value="{{ user.display_name }}" readonly>
    
    <!-- Dynamic custom fields -->
    {% for field in tournament.custom_fields.all %}
        {% include 'tournaments/partials/custom_field.html' with field=field %}
    {% endfor %}
    
    <button type="submit" class="btn-primary">Register</button>
</form>

<div id="registration-result"></div>
```

**3. Bracket Node Interaction**

```django
<!-- templates/tournaments/bracket/view.html -->
<div class="bracket-container" x-data="{ selectedMatch: null }">
    {% for round in bracket_rounds %}
        <div class="bracket-round">
            {% for node in round.nodes %}
                <div 
                    class="bracket-node cursor-pointer"
                    @click="selectedMatch = {{ node.match_id }}"
                    hx-get="{% url 'tournament:match_detail' node.match_id %}"
                    hx-target="#match-modal"
                    hx-trigger="click"
                >
                    <div class="participant">{{ node.participant1_name }}</div>
                    <div class="participant">{{ node.participant2_name }}</div>
                </div>
            {% endfor %}
        </div>
    {% endfor %}
</div>

<!-- Match detail modal (populated by HTMX) -->
<div id="match-modal" class="modal"></div>
```

### Alpine.js Reactive Components

**Tournament Countdown Timer:**

```django
<div 
    x-data="{
        startTime: new Date('{{ tournament.start_time|date:'c' }}').getTime(),
        now: Date.now(),
        timeLeft: ''
    }"
    x-init="setInterval(() => {
        now = Date.now();
        const diff = startTime - now;
        if (diff > 0) {
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            timeLeft = `${days}d ${hours}h`;
        } else {
            timeLeft = 'Live Now!';
        }
    }, 1000)"
    class="countdown"
>
    <span x-text="timeLeft"></span>
</div>
```

### Component Organization

**Reusable Tournament Card:**

```django
<!-- templates/tournaments/partials/tournament_card.html -->
<div class="tournament-card bg-gray-800 rounded-lg overflow-hidden hover:shadow-xl transition">
    <!-- Banner -->
    <div class="relative h-48">
        <img src="{{ tournament.banner_image.url }}" alt="{{ tournament.title }}" class="w-full h-full object-cover">
        <div class="absolute top-2 right-2 bg-yellow-500 px-3 py-1 rounded text-sm font-bold">
            {{ tournament.get_status_display }}
        </div>
    </div>
    
    <!-- Content -->
    <div class="p-4">
        <h3 class="text-xl font-bold mb-2">{{ tournament.title }}</h3>
        <div class="flex items-center gap-4 text-sm text-gray-400 mb-4">
            <span>🎮 {{ tournament.game.name }}</span>
            <span>👥 {{ tournament.current_participants }}/{{ tournament.max_participants }}</span>
            <span>💰 {{ tournament.prize_pool }} BDT</span>
        </div>
        
        <!-- CTA -->
        <a href="{% url 'tournament:detail' tournament.id %}" class="btn-primary w-full text-center">
            View Details
        </a>
    </div>
</div>
```

### HTMX Event Naming Conventions

**Standard Events:**
- `htmx:configRequest` - Modify request before sending (add custom headers)
- `htmx:afterSwap` - After content is swapped
- `htmx:responseError` - Handle errors

**Custom Tournament Events:**
- `tournament:registered` - User registered for tournament
- `tournament:bracket_updated` - Bracket structure changed
- `match:started` - Match state changed to live
- `match:completed` - Match finished
- `dispute:created` - New dispute filed

**Example:**

```javascript
// Global event handlers
document.body.addEventListener('htmx:configRequest', (event) => {
    // Add CSRF token to all HTMX requests
    event.detail.headers['X-CSRFToken'] = getCookie('csrftoken');
});

document.body.addEventListener('tournament:registered', (event) => {
    // Show success notification
    showNotification('Registration successful!', 'success');
    
    // Update participant count
    htmx.trigger('#participant-count', 'refresh');
});
```

### Mobile-First Responsive Patterns

**Tailwind Responsive Utilities:**

```django
<!-- Desktop: 3-column grid, Mobile: 1-column -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {% for tournament in tournaments %}
        {% include 'tournaments/partials/tournament_card.html' %}
    {% endfor %}
</div>

<!-- Desktop: Horizontal layout, Mobile: Vertical stack -->
<div class="flex flex-col lg:flex-row gap-6">
    <div class="lg:w-2/3"><!-- Main content --></div>
    <div class="lg:w-1/3"><!-- Sidebar --></div>
</div>

<!-- Mobile: Hamburger menu, Desktop: Full navbar -->
<nav class="lg:flex hidden"><!-- Desktop nav --></nav>
<button class="lg:hidden" @click="mobileMenuOpen = true"><!-- Mobile toggle --></button>
```

### Static Asset Organization

```
static/
├── css/
│   ├── tailwind.config.js       # Tailwind configuration
│   ├── input.css                # Source CSS
│   └── tailwind.output.css      # Compiled CSS
├── js/
│   ├── tournament/
│   │   ├── bracket.js           # Bracket visualization logic
│   │   ├── match.js             # Match interactions
│   │   └── registration.js      # Registration flow
│   └── utils/
│       ├── notification.js      # Toast notifications
│       └── validation.js        # Client-side validation
└── img/
    └── tournaments/
        ├── placeholders/        # Default images
        └── icons/               # Game icons
```

**Key Benefits:**
- ✅ **Django Templates:** Server-side rendering for SEO and fast initial load
- ✅ **HTMX:** Partial updates without full page reload, minimal JavaScript
- ✅ **Alpine.js:** Reactive UI components for interactive elements
- ✅ **Tailwind CSS:** Rapid UI development with utility classes
- ✅ **Mobile-First:** Responsive design from smallest to largest screens
- ✅ **WebSocket Integration:** Real-time updates for live tournaments
- ✅ **Component Reusability:** DRY principle with partials and includes
- ✅ **Progressive Enhancement:** Works without JavaScript, enhanced with it

---

## 8. Security Architecture

### 8.1 Permission System

```python
# tournament_engine/permissions.py

from django.core.exceptions import PermissionDenied

class TournamentPermissions:
    
    @staticmethod
    def can_edit_tournament(user, tournament):
        """Check if user can edit tournament"""
        return (
            user.is_superuser or
            tournament.organizer == user
        )
    
    @staticmethod
    def can_verify_payments(user, tournament):
        """Check if user can verify payments"""
        return TournamentPermissions.can_edit_tournament(user, tournament)
    
    @staticmethod
    def can_resolve_disputes(user, tournament):
        """Check if user can resolve disputes"""
        return (
            user.is_superuser or
            tournament.organizer == user
        )
    
    @staticmethod
    def can_register(user, tournament):
        """Check if user can register"""
        if not tournament.is_registration_open():
            return False
        
        # Check if already registered
        from tournament_engine.registration.models import Registration
        exists = Registration.objects.filter(
            tournament=tournament,
            user=user
        ).exists()
        
        return not exists

def permission_required(permission_check):
    """Decorator for permission checks"""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            tournament_id = kwargs.get('tournament_id')
            tournament = Tournament.objects.get(id=tournament_id)
            
            if not permission_check(request.user, tournament):
                raise PermissionDenied
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### 8.2 Rate Limiting

```python
# tournament_engine/middleware.py

from django.core.cache import cache
from django.http import HttpResponseForbidden

class RateLimitMiddleware:
    """Rate limit sensitive endpoints"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if self.is_rate_limited(request):
            return HttpResponseForbidden("Rate limit exceeded")
        
        return self.get_response(request)
    
    def is_rate_limited(self, request):
        """Check rate limit"""
        if request.path.startswith('/tournaments/register/'):
            key = f"rate_limit_register_{request.user.id}"
            count = cache.get(key, 0)
            
            if count > 10:  # 10 registrations per hour
                return True
            
            cache.set(key, count + 1, 3600)
        
        return False
```

### 8.3 Security Hardening

#### CSRF Protection for AJAX/HTMX

```python
# tournament_engine/middleware.py

from django.middleware.csrf import CsrfViewMiddleware
from django.conf import settings

class HTMXCsrfMiddleware(CsrfViewMiddleware):
    """Enhanced CSRF protection for HTMX requests"""
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        # HTMX sends requests with X-Requested-With header
        if request.headers.get('HX-Request'):
            # Ensure CSRF token is validated
            return super().process_view(request, callback, callback_args, callback_kwargs)
        
        return super().process_view(request, callback, callback_args, callback_kwargs)
```

**Settings Configuration:**
```python
# deltacrown/settings.py

MIDDLEWARE = [
    # ... other middleware
    'tournament_engine.middleware.HTMXCsrfMiddleware',
    # ...
]

# CSRF settings for AJAX
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_USE_SESSIONS = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True  # Production only
```

#### Media Upload Validation

```python
# tournament_engine/utils/validators.py

import magic
from django.core.exceptions import ValidationError
from django.conf import settings

class MediaValidator:
    """Validate uploaded media files"""
    
    ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm']
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB
    
    @staticmethod
    def validate_image(file):
        """Validate image upload"""
        # Check file size
        if file.size > MediaValidator.MAX_IMAGE_SIZE:
            raise ValidationError(f"Image size must be less than 5MB")
        
        # Check MIME type with python-magic (checks actual file content)
        mime = magic.from_buffer(file.read(1024), mime=True)
        file.seek(0)
        
        if mime not in MediaValidator.ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"Invalid image type: {mime}")
        
        return True
    
    @staticmethod
    def validate_video(file):
        """Validate video upload"""
        if file.size > MediaValidator.MAX_VIDEO_SIZE:
            raise ValidationError(f"Video size must be less than 50MB")
        
        mime = magic.from_buffer(file.read(1024), mime=True)
        file.seek(0)
        
        if mime not in MediaValidator.ALLOWED_VIDEO_TYPES:
            raise ValidationError(f"Invalid video type: {mime}")
        
        return True
    
    @staticmethod
    def validate_payment_proof(file):
        """Validate payment proof screenshot"""
        # More restrictive validation for payment proofs
        if file.size > 2 * 1024 * 1024:  # 2MB max
            raise ValidationError("Payment proof must be less than 2MB")
        
        mime = magic.from_buffer(file.read(1024), mime=True)
        file.seek(0)
        
        # Only allow JPEG/PNG for payment proofs
        if mime not in ['image/jpeg', 'image/png']:
            raise ValidationError("Payment proof must be JPEG or PNG")
        
        return True
```

#### Hash-Based Filename Storage

```python
# tournament_engine/utils/storage.py

import hashlib
import os
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

@deconstructible
class SecureMediaStorage(FileSystemStorage):
    """Secure file storage with hash-based filenames"""
    
    def get_available_name(self, name, max_length=None):
        """Generate hash-based filename"""
        ext = os.path.splitext(name)[1]
        
        # Generate hash from file content + timestamp
        hash_input = f"{name}{timezone.now().isoformat()}".encode()
        file_hash = hashlib.sha256(hash_input).hexdigest()[:16]
        
        # New filename: hash + extension
        new_name = f"{file_hash}{ext}"
        
        return super().get_available_name(new_name, max_length)

# Usage in models
from tournament_engine.utils.storage import SecureMediaStorage

class Tournament(models.Model):
    # ...
    banner_image = models.ImageField(
        upload_to='tournaments/banners/',
        storage=SecureMediaStorage(),
        validators=[MediaValidator.validate_image]
    )

class Payment(models.Model):
    # ...
    payment_proof = models.ImageField(
        upload_to='tournaments/payments/',
        storage=SecureMediaStorage(),
        validators=[MediaValidator.validate_payment_proof]
    )
```

#### SQL Injection Prevention

```python
# All queries use Django ORM (safe by default)
# For rare raw SQL cases:

from django.db import connection

def get_tournament_stats(tournament_id):
    """Example of safe raw SQL"""
    with connection.cursor() as cursor:
        # Use parameterized query
        cursor.execute(
            """
            SELECT COUNT(*) as total_registrations
            FROM tournament_registration
            WHERE tournament_id = %s AND status = %s
            """,
            [tournament_id, 'confirmed']  # Parameters passed separately
        )
        row = cursor.fetchone()
    
    return row[0]
```

#### Input Sanitization

```python
# tournament_engine/utils/sanitizers.py

import bleach
from django.utils.html import escape

class InputSanitizer:
    """Sanitize user inputs"""
    
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li', 'a']
    ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}
    
    @staticmethod
    def sanitize_html(html_content):
        """Clean HTML for tournament rules/descriptions"""
        return bleach.clean(
            html_content,
            tags=InputSanitizer.ALLOWED_TAGS,
            attributes=InputSanitizer.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @staticmethod
    def sanitize_plain_text(text):
        """Escape plain text"""
        return escape(text)
    
    @staticmethod
    def validate_url(url):
        """Validate external URLs"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        
        # Only allow http/https
        if parsed.scheme not in ['http', 'https']:
            raise ValidationError("Invalid URL scheme")
        
        # Block internal IPs (prevent SSRF)
        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
            raise ValidationError("Internal URLs not allowed")
        
        return url
```

**Usage in Views:**
```python
from tournament_engine.utils.sanitizers import InputSanitizer

def create_tournament(request):
    if request.method == 'POST':
        title = InputSanitizer.sanitize_plain_text(request.POST.get('title'))
        rules = InputSanitizer.sanitize_html(request.POST.get('rules'))
        discord_url = InputSanitizer.validate_url(request.POST.get('discord_url'))
        
        # ... create tournament
```

---

## 9. Performance & Scalability

### 9.1 Database Optimization

**Query Optimization:**
```python
# tournament_engine/core/managers.py

class TournamentQuerySet(models.QuerySet):
    """Optimized queries"""
    
    def with_related_data(self):
        """Prefetch all related data"""
        return self.select_related(
            'organizer',
            'game'
        ).prefetch_related(
            'registrations',
            'matches',
            'sponsors'
        )
    
    def published(self):
        """Only published tournaments"""
        return self.filter(status=Tournament.PUBLISHED)
    
    def live(self):
        """Currently live tournaments"""
        return self.filter(status=Tournament.LIVE)

class TournamentManager(models.Manager):
    def get_queryset(self):
        return TournamentQuerySet(self.model, using=self._db)
    
    def with_related_data(self):
        return self.get_queryset().with_related_data()
    
    def published(self):
        return self.get_queryset().published()
```

### 9.2 Caching Strategy

```python
# tournament_engine/utils/cache.py

from django.core.cache import cache

class TournamentCache:
    """Caching utilities"""
    
    CACHE_TTL = 300  # 5 minutes
    
    @staticmethod
    def get_tournament(tournament_id):
        """Get tournament from cache or DB"""
        key = f"tournament_{tournament_id}"
        tournament = cache.get(key)
        
        if not tournament:
            from tournament_engine.core.models import Tournament
            tournament = Tournament.objects.with_related_data().get(id=tournament_id)
            cache.set(key, tournament, TournamentCache.CACHE_TTL)
        
        return tournament
    
    @staticmethod
    def invalidate_tournament(tournament_id):
        """Clear tournament cache"""
        key = f"tournament_{tournament_id}"
        cache.delete(key)
    
    @staticmethod
    def get_bracket(tournament_id):
        """Get bracket from cache"""
        key = f"bracket_{tournament_id}"
        return cache.get(key)
    
    @staticmethod
    def set_bracket(tournament_id, bracket_data):
        """Cache bracket data"""
        key = f"bracket_{tournament_id}"
        cache.set(key, bracket_data, TournamentCache.CACHE_TTL)
```

### 9.3 Celery Tasks (Enhanced Reliability)

```python
# tournament_engine/tasks.py

from celery import shared_task, chain, group, chord
from celery.exceptions import SoftTimeLimitExceeded
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

# Task retry configuration
TASK_RETRY_KWARGS = {
    'max_retries': 3,
    'retry_backoff': True,
    'retry_backoff_max': 600,  # 10 minutes
    'retry_jitter': True
}

@shared_task(bind=True, **TASK_RETRY_KWARGS)
def generate_bracket_async(self, tournament_id):
    """Generate bracket in background with retry logic"""
    try:
        from tournament_engine.bracket.services import BracketService
        
        # Check if task already in progress (idempotency)
        lock_key = f"bracket_generation_{tournament_id}"
        if cache.get(lock_key):
            logger.warning(f"Bracket generation already in progress for tournament {tournament_id}")
            return
        
        # Acquire lock
        cache.set(lock_key, True, timeout=300)  # 5 minutes
        
        try:
            BracketService.generate_bracket(tournament_id)
            logger.info(f"Bracket generated successfully for tournament {tournament_id}")
        finally:
            cache.delete(lock_key)
    
    except SoftTimeLimitExceeded:
        logger.error(f"Bracket generation timed out for tournament {tournament_id}")
        raise
    except Exception as exc:
        logger.error(f"Bracket generation failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc)

@shared_task(bind=True, **TASK_RETRY_KWARGS)
def distribute_prizes_async(self, tournament_id):
    """Distribute prizes with failure handling"""
    try:
        from tournament_engine.registration.services import PaymentService
        from tournament_engine.core.models import Tournament
        
        tournament = Tournament.objects.get(id=tournament_id)
        
        # Idempotency check
        if tournament.prizes_distributed:
            logger.warning(f"Prizes already distributed for tournament {tournament_id}")
            return
        
        result = PaymentService.process_prize_distribution(tournament)
        
        if result['success']:
            logger.info(f"Prizes distributed for tournament {tournament_id}")
        else:
            raise Exception(f"Prize distribution failed: {result.get('error')}")
    
    except Exception as exc:
        logger.error(f"Prize distribution error: {exc}")
        raise self.retry(exc=exc)

@shared_task(bind=True, **TASK_RETRY_KWARGS)
def generate_certificates_async(self, tournament_id):
    """Generate certificates with retry"""
    try:
        from tournament_engine.awards.services import CertificateService
        
        certificates = CertificateService.generate_certificates(tournament_id)
        logger.info(f"Generated {len(certificates)} certificates for tournament {tournament_id}")
        
        return {
            'tournament_id': tournament_id,
            'certificates_generated': len(certificates)
        }
    
    except Exception as exc:
        logger.error(f"Certificate generation failed: {exc}")
        raise self.retry(exc=exc)

@shared_task
def send_match_reminders():
    """Send match reminders (periodic task)"""
    from django.utils import timezone
    from datetime import timedelta
    from tournament_engine.match.models import Match
    
    # Find matches starting in 1 hour
    upcoming = Match.objects.filter(
        state=Match.READY,
        scheduled_time__gte=timezone.now(),
        scheduled_time__lte=timezone.now() + timedelta(hours=1)
    ).select_related('tournament')
    
    for match in upcoming:
        send_match_notification.delay(match.id)
    
    logger.info(f"Sent reminders for {upcoming.count()} upcoming matches")

@shared_task(bind=True, max_retries=5)
def send_match_notification(self, match_id):
    """Send notification for a single match"""
    try:
        from tournament_engine.match.models import Match
        from apps.notifications.services import NotificationService
        
        match = Match.objects.get(id=match_id)
        
        # Send notifications to both participants
        NotificationService.notify_match_reminder(
            match.tournament_id,
            match.id,
            [match.participant1_id, match.participant2_id]
        )
    except Exception as exc:
        logger.error(f"Failed to send match notification: {exc}")
        raise self.retry(exc=exc, countdown=60)  # Retry after 1 minute


# Task Chaining Example: Tournament Conclusion Workflow
@shared_task
def conclude_tournament_workflow(tournament_id):
    """Chain tasks for tournament conclusion"""
    
    # Define task chain: Prizes -> Certificates -> Notifications
    workflow = chain(
        distribute_prizes_async.si(tournament_id),
        generate_certificates_async.si(tournament_id),
        send_conclusion_notifications.si(tournament_id)
    )
    
    workflow.apply_async()
    logger.info(f"Started conclusion workflow for tournament {tournament_id}")

@shared_task(bind=True, **TASK_RETRY_KWARGS)
def send_conclusion_notifications(self, tournament_id):
    """Send conclusion notifications to all participants"""
    try:
        from tournament_engine.core.models import Tournament
        from apps.notifications.services import NotificationService
        
        tournament = Tournament.objects.get(id=tournament_id)
        registrations = tournament.registrations.filter(status='confirmed')
        
        for reg in registrations:
            NotificationService.notify_tournament_concluded(
                tournament_id,
                reg.user_id if reg.user else None,
                reg.team_id
            )
        
        logger.info(f"Sent conclusion notifications for tournament {tournament_id}")
    
    except Exception as exc:
        logger.error(f"Failed to send conclusion notifications: {exc}")
        raise self.retry(exc=exc)


# Task Grouping Example: Parallel Match Result Processing
@shared_task
def process_round_completion(bracket_id, round_number):
    """Process all matches in a completed round"""
    from tournament_engine.match.models import Match
    
    matches = Match.objects.filter(
        bracket_id=bracket_id,
        round=round_number,
        state=Match.COMPLETED
    )
    
    # Process all match results in parallel
    job = group(
        update_rankings_for_match.s(match.id) for match in matches
    )
    
    result = job.apply_async()
    logger.info(f"Processing {len(matches)} matches in round {round_number}")
    
    return result

@shared_task(bind=True, **TASK_RETRY_KWARGS)
def update_rankings_for_match(self, match_id):
    """Update team rankings after match completion"""
    try:
        from tournament_engine.match.models import Match
        from apps.teams.services import RankingService
        
        match = Match.objects.get(id=match_id)
        
        # Update rankings for both teams
        if match.winner:
            RankingService.update_after_match_win(match.winner_id, match.game_id)
            RankingService.update_after_match_loss(match.loser_id, match.game_id)
    
    except Exception as exc:
        logger.error(f"Failed to update rankings for match {match_id}: {exc}")
        raise self.retry(exc=exc)


# Chord Example: Analytics Aggregation
@shared_task
def generate_tournament_analytics(tournament_id):
    """Generate comprehensive analytics using chord"""
    from tournament_engine.analytics.tasks import (
        calculate_engagement_metrics,
        calculate_financial_metrics,
        calculate_performance_metrics
    )
    
    # Run all calculations in parallel, then aggregate
    callback = aggregate_analytics.s(tournament_id)
    
    header = group(
        calculate_engagement_metrics.s(tournament_id),
        calculate_financial_metrics.s(tournament_id),
        calculate_performance_metrics.s(tournament_id)
    )
    
    result = chord(header)(callback)
    logger.info(f"Started analytics generation for tournament {tournament_id}")
    
    return result

@shared_task
def aggregate_analytics(results, tournament_id):
    """Aggregate analytics results"""
    from tournament_engine.analytics.models import TournamentAnalytics
    
    engagement, financial, performance = results
    
    TournamentAnalytics.objects.create(
        tournament_id=tournament_id,
        engagement_metrics=engagement,
        financial_metrics=financial,
        performance_metrics=performance
    )
    
    logger.info(f"Analytics aggregated for tournament {tournament_id}")


# Periodic Task Configuration (in celery.py)
"""
from celery.schedules import crontab

app.conf.beat_schedule = {
    'send-match-reminders': {
        'task': 'tournament_engine.tasks.send_match_reminders',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'cleanup-stale-registrations': {
        'task': 'tournament_engine.tasks.cleanup_stale_registrations',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
"""
```

### 9.4 Analytics Event Tracking (ML-Ready)

```python
# tournament_engine/analytics/models.py

class AnalyticsEvent(models.Model):
    """Fine-grained event tracking for ML/data warehouse"""
    
    # Event identification
    event_type = models.CharField(max_length=50, db_index=True)
    event_timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Context
    tournament_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    user_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    session_id = models.CharField(max_length=64, null=True, db_index=True)
    
    # Event payload (flexible schema)
    event_data = models.JSONField(default=dict)
    
    # Request metadata
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(null=True)
    referrer = models.URLField(null=True, blank=True)
    
    # A/B testing support
    experiment_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    variant = models.CharField(max_length=20, null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['event_type', 'event_timestamp']),
            models.Index(fields=['tournament_id', 'event_type']),
            models.Index(fields=['user_id', 'event_timestamp']),
        ]
        # Partition by month for efficient querying
        # db_table = 'analytics_event_partitioned'


# Event Types for ML Training
ANALYTICS_EVENTS = {
    # User behavior
    'tournament_viewed': 'User viewed tournament detail',
    'tournament_registered': 'User registered for tournament',
    'registration_abandoned': 'User started but did not complete registration',
    
    # Engagement
    'match_watched': 'User watched live match',
    'bracket_explored': 'User interacted with bracket',
    'comment_posted': 'User posted comment',
    
    # Conversion
    'payment_submitted': 'User submitted payment proof',
    'payment_verified': 'Payment verified by organizer',
    
    # Retention
    'return_visit': 'User returned to tournament page',
    'notification_clicked': 'User clicked notification',
}


# tournament_engine/analytics/services.py

class AnalyticsService:
    
    @staticmethod
    def track_event(event_type, user_id=None, tournament_id=None, event_data=None, request=None):
        """Track analytics event"""
        from tournament_engine.analytics.models import AnalyticsEvent
        
        event = AnalyticsEvent(
            event_type=event_type,
            user_id=user_id,
            tournament_id=tournament_id,
            event_data=event_data or {}
        )
        
        if request:
            event.ip_address = get_client_ip(request)
            event.user_agent = request.META.get('HTTP_USER_AGENT')
            event.referrer = request.META.get('HTTP_REFERER')
            event.session_id = request.session.session_key
        
        event.save()
        
        return event.id
    
    @staticmethod
    def get_conversion_funnel(tournament_id):
        """Calculate conversion funnel for ML models"""
        from django.db.models import Count
        
        events = AnalyticsEvent.objects.filter(tournament_id=tournament_id)
        
        funnel = {
            'viewed': events.filter(event_type='tournament_viewed').values('user_id').distinct().count(),
            'registered': events.filter(event_type='tournament_registered').values('user_id').distinct().count(),
            'payment_submitted': events.filter(event_type='payment_submitted').values('user_id').distinct().count(),
            'payment_verified': events.filter(event_type='payment_verified').values('user_id').distinct().count(),
        }
        
        # Calculate drop-off rates
        if funnel['viewed'] > 0:
            funnel['registration_rate'] = funnel['registered'] / funnel['viewed']
            funnel['payment_rate'] = funnel['payment_submitted'] / funnel['registered'] if funnel['registered'] > 0 else 0
        
        return funnel
    
    @staticmethod
    def export_for_ml(start_date, end_date, event_types=None):
        """Export event data for ML training"""
        from django.db.models import Q
        
        queryset = AnalyticsEvent.objects.filter(
            event_timestamp__gte=start_date,
            event_timestamp__lte=end_date
        )
        
        if event_types:
            queryset = queryset.filter(event_type__in=event_types)
        
        # Return as pandas-compatible format
        return queryset.values(
            'event_type',
            'event_timestamp',
            'tournament_id',
            'user_id',
            'event_data'
        )
```

**Usage in Views:**

```python
from tournament_engine.analytics.services import AnalyticsService

def tournament_detail(request, tournament_id):
    tournament = get_object_or_404(Tournament, id=tournament_id)
    
    # Track view event
    AnalyticsService.track_event(
        'tournament_viewed',
        user_id=request.user.id if request.user.is_authenticated else None,
        tournament_id=tournament_id,
        event_data={
            'tournament_status': tournament.status,
            'participants_count': tournament.current_participants,
            'time_to_start': (tournament.start_time - timezone.now()).total_seconds()
        },
        request=request
    )
    
    return render(request, 'tournaments/detail.html', {'tournament': tournament})
```

---

## 10. Developer Experience & Tooling

### 10.1 Development Environment Setup

**Prerequisites:**
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+ (for Tailwind CSS compilation)

**.env.example File:**

```bash
# .env.example - Copy to .env and configure

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://deltacrown_user:password@localhost:5432/deltacrown_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Django Channels
CHANNEL_LAYERS_BACKEND=channels_redis.core.RedisChannelLayer
CHANNEL_LAYERS_HOST=localhost
CHANNEL_LAYERS_PORT=6379

# Email (Development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Payment Gateways (Future)
SSLCOMMERZ_STORE_ID=
SSLCOMMERZ_STORE_PASSWORD=

# Storage (Production)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=

# Sentry (Error Tracking)
SENTRY_DSN=

# Analytics
GOOGLE_ANALYTICS_ID=
```

### 10.2 Makefile Commands

```makefile
# Makefile - Development automation

.PHONY: help install migrate run test lint format clean

help: ## Show this help message
	@echo "DeltaCrown Tournament Engine - Development Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt
	npm install
	@echo "✓ Dependencies installed"

migrate: ## Run database migrations
	python manage.py makemigrations
	python manage.py migrate
	@echo "✓ Migrations applied"

run: ## Start development server
	python manage.py runserver

run-celery: ## Start Celery worker
	celery -A deltacrown worker -l info

run-beat: ## Start Celery beat scheduler
	celery -A deltacrown beat -l info

run-channels: ## Start Django Channels (Daphne)
	daphne -b 0.0.0.0 -p 8000 deltacrown.asgi:application

run-all: ## Start all services (requires tmux or multiple terminals)
	@echo "Starting all services..."
	@echo "Run these in separate terminals:"
	@echo "  make run"
	@echo "  make run-celery"
	@echo "  make run-beat"

test: ## Run all tests
	pytest --cov=tournament_engine --cov-report=html
	@echo "✓ Tests completed. Coverage report: htmlcov/index.html"

test-fast: ## Run tests without coverage
	pytest -x --ff
	@echo "✓ Fast tests completed"

test-integration: ## Run integration tests only
	pytest tests/test_integration*.py -v
	@echo "✓ Integration tests completed"

lint: ## Run code quality checks
	flake8 tournament_engine/
	pylint tournament_engine/
	@echo "✓ Linting completed"

format: ## Format code with black
	black tournament_engine/
	isort tournament_engine/
	@echo "✓ Code formatted"

type-check: ## Run type checking with mypy
	mypy tournament_engine/
	@echo "✓ Type checking completed"

shell: ## Open Django shell with tournament_engine imported
	python manage.py shell_plus --ipython

db-reset: ## Reset database (WARNING: Deletes all data)
	python manage.py flush --no-input
	python manage.py migrate
	python manage.py loaddata fixtures/initial_data.json
	@echo "✓ Database reset"

db-backup: ## Backup database
	pg_dump deltacrown_db > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✓ Database backed up"

fixtures: ## Create fixtures from current data
	python manage.py dumpdata tournament_engine.core.Game --indent 2 > fixtures/games.json
	@echo "✓ Fixtures created"

css-build: ## Build Tailwind CSS
	npx tailwindcss -i static/css/input.css -o static/css/tailwind.output.css --minify
	@echo "✓ CSS compiled"

css-watch: ## Watch and rebuild Tailwind CSS
	npx tailwindcss -i static/css/input.css -o static/css/tailwind.output.css --watch

collectstatic: ## Collect static files
	python manage.py collectstatic --no-input
	@echo "✓ Static files collected"

clean: ## Clean temporary files
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage
	@echo "✓ Cleaned temporary files"

docker-up: ## Start Docker containers
	docker-compose up -d
	@echo "✓ Docker containers started"

docker-down: ## Stop Docker containers
	docker-compose down
	@echo "✓ Docker containers stopped"

docker-logs: ## View Docker logs
	docker-compose logs -f

seed: ## Seed database with sample data
	python manage.py seed_tournaments
	@echo "✓ Database seeded with sample data"
```

### 10.3 Pre-Commit Hooks

**.pre-commit-config.yaml:**

```yaml
# .pre-commit-config.yaml

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=500']
      - id: check-json
      - id: check-merge-conflict
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11
        args: ['--line-length=100']

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ['--profile=black']

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--extend-ignore=E203,W503']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [django-stubs]
        args: ['--config-file=mypy.ini']

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: ['-c', 'pyproject.toml']
        additional_dependencies: ['bandit[toml]']

  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: ['-x', '--ff', '--tb=short']
```

**Installation:**

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### 10.4 Docker Development Setup

**docker-compose.yml:**

```yaml
# docker-compose.yml - Local development environment

version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_DB: deltacrown_db
      POSTGRES_USER: deltacrown_user
      POSTGRES_PASSWORD: deltacrown_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://deltacrown_user:deltacrown_pass@db:5432/deltacrown_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery:
    build: .
    command: celery -A deltacrown worker -l info
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql://deltacrown_user:deltacrown_pass@db:5432/deltacrown_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A deltacrown beat -l info
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql://deltacrown_user:deltacrown_pass@db:5432/deltacrown_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  redis_data:
```

**Dockerfile:**

```dockerfile
# Dockerfile

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python manage.py collectstatic --no-input

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

### 10.5 VS Code Configuration

**.vscode/settings.json:**

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=100"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.tabSize": 4
  },
  "[html]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true
  }
}
```

**.vscode/launch.json:**

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Django: Run Server",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/manage.py",
      "args": ["runserver"],
      "django": true,
      "justMyCode": true
    },
    {
      "name": "Django: Test",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/manage.py",
      "args": ["test", "tournament_engine"],
      "django": true,
      "justMyCode": false
    },
    {
      "name": "Pytest: Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

### 10.6 Quick Start Guide

**1. Initial Setup:**

```bash
# Clone repository
git clone https://github.com/yourusername/deltacrown.git
cd deltacrown

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Copy environment file
cp .env.example .env
# Edit .env with your local settings

# Install dependencies
make install

# Setup pre-commit hooks
pre-commit install

# Run migrations
make migrate

# Load initial data (games, sample tournaments)
python manage.py loaddata fixtures/initial_data.json

# Create superuser
python manage.py createsuperuser
```

**2. Start Development:**

```bash
# Option A: Use Makefile (requires multiple terminals)
make run              # Terminal 1: Django server
make run-celery       # Terminal 2: Celery worker
make run-beat         # Terminal 3: Celery beat
make css-watch        # Terminal 4: Tailwind watch

# Option B: Use Docker
make docker-up
```

**3. Access Services:**

- **Django Admin:** http://localhost:8000/admin/
- **Tournament Engine:** http://localhost:8000/tournaments/
- **API Docs:** http://localhost:8000/docs/ (if added)
- **Flower (Celery Monitor):** http://localhost:5555/ (if configured)

**4. Development Workflow:**

```bash
# Create a new feature
git checkout -b feature/tournament-challenges

# Make changes, test locally
make test-fast

# Run full test suite with coverage
make test

# Format code
make format

# Check code quality
make lint

# Commit (pre-commit hooks will run automatically)
git commit -m "Add tournament challenges feature"
```

**5. Debugging:**

```python
# Use Django Debug Toolbar (already in requirements.txt)
# Add to INSTALLED_APPS and MIDDLEWARE in settings.py

# Or use ipdb for breakpoints
import ipdb; ipdb.set_trace()
```

---

## 11. Testing Strategy

### 10.1 Unit Tests

```python
# tournament_engine/core/tests/test_services.py

from django.test import TestCase
from tournament_engine.core.services import TournamentService
from tournament_engine.core.models import Tournament, Game

class TournamentServiceTest(TestCase):
    
    def setUp(self):
        self.game = Game.objects.create(name='Valorant', slug='valorant')
        self.user = User.objects.create_user(username='organizer')
    
    def test_create_tournament(self):
        """Test tournament creation"""
        tournament_data = {
            'name': 'Test Tournament',
            'game': self.game,
            'format': Tournament.SINGLE_ELIM,
            'max_participants': 16,
            # ... more fields
        }
        
        tournament = TournamentService.create_tournament(
            organizer=self.user,
            tournament_data=tournament_data
        )
        
        self.assertIsNotNone(tournament)
        self.assertEqual(tournament.name, 'Test Tournament')
        self.assertEqual(tournament.status, Tournament.DRAFT)
```

### 10.2 Integration Tests

```python
# tournament_engine/tests/test_integration.py

class TournamentFlowIntegrationTest(TestCase):
    """Test complete tournament flow"""
    
    def test_complete_tournament_lifecycle(self):
        """Test from creation to conclusion"""
        
        # 1. Create tournament
        tournament = create_test_tournament()
        
        # 2. Register participants
        registrations = register_test_participants(tournament, count=8)
        
        # 3. Verify payments
        for reg in registrations:
            verify_test_payment(reg)
        
        # 4. Generate bracket
        bracket = generate_test_bracket(tournament)
        self.assertIsNotNone(bracket)
        
        # 5. Play matches
        matches = tournament.matches.all()
        for match in matches:
            play_test_match(match)
        
        # 6. Check final standings
        standings = get_final_standings(tournament)
        self.assertEqual(len(standings), 3)  # Top 3
        
        # 7. Verify certificates generated
        certificates = tournament.certificates.all()
        self.assertGreaterEqual(certificates.count(), 3)
```

### 10.3 Performance Tests

```python
# tournament_engine/tests/test_performance.py

from django.test.utils import override_settings
import time

class PerformanceTest(TestCase):
    
    @override_settings(DEBUG=False)
    def test_bracket_generation_performance(self):
        """Test bracket generation with 64 participants"""
        tournament = create_test_tournament(max_participants=64)
        register_test_participants(tournament, count=64)
        
        start_time = time.time()
        BracketService.generate_bracket(tournament.id)
        end_time = time.time()
        
        duration = end_time - start_time
        self.assertLess(duration, 5.0)  # Should complete in < 5 seconds
```

---

## Summary

This technical architecture document provides:

✅ **Complete directory structure** with 10 modular apps
✅ **Detailed model definitions** for all core entities
✅ **Service layer architecture** for business logic
✅ **Integration patterns** with existing DeltaCrown apps
✅ **Real-time architecture** using Django Channels
✅ **Security architecture** with permissions and rate limiting
✅ **Performance optimization** strategies (caching, query optimization, Celery)
✅ **Testing strategy** (unit, integration, performance tests)

**Total Models:** 25+ core models defined
**Total Services:** 40+ service methods outlined
**Integration Points:** 5 existing apps (Economy, Teams, UserProfile, Notifications, SiteUI)
**Real-Time Features:** WebSocket support for live updates

This architecture ensures:
- **Modularity** - Each app is independently maintainable
- **Scalability** - Can handle 100+ concurrent tournaments
- **Performance** - Sub-200ms page loads with caching
- **Security** - Robust permission system and audit logging
- **Maintainability** - Clear separation of concerns and comprehensive tests

---

**End of Part 2: Technical Architecture**
