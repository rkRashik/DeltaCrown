# DeltaCrown Tournament Registration System - Complete Developer Guide

**Version:** 2.0  
**Last Updated:** October 13, 2025  
**Author:** DeltaCrown Development Team  
**Status:** Production-Ready

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture & Technology Stack](#2-architecture--technology-stack)
3. [Database Models & Schema](#3-database-models--schema)
4. [API Endpoints Reference](#4-api-endpoints-reference)
5. [Service Layer Architecture](#5-service-layer-architecture)
6. [Business Logic & Workflows](#6-business-logic--workflows)
7. [Frontend Integration Guide](#7-frontend-integration-guide)
8. [Payment Integration](#8-payment-integration)
9. [Game-Specific Configurations](#9-game-specific-configurations)
10. [Security & Validation](#10-security--validation)
11. [State Machine & Status Management](#11-state-machine--status-management)
12. [Testing Guide](#12-testing-guide)
13. [Deployment Checklist](#13-deployment-checklist)
14. [Migration Path](#14-migration-path)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. System Overview

### 1.1 Purpose

The DeltaCrown Tournament Registration System is a comprehensive, production-ready platform for managing esports tournament registrations across multiple games (Valorant, eFootball Mobile, etc.). It supports:

- **Solo Tournaments**: Individual player registration (1v1)
- **Team Tournaments**: Team-based registration with captain approval
- **Mixed Tournaments**: Both solo and team participants

### 1.2 Key Features

✅ **Multi-Step Registration Flow**
- Auto-fill from user profile and team data
- Real-time validation
- Progressive disclosure of form fields

✅ **Team Management Integration**
- Captain approval workflow
- Non-captain registration requests
- Team roster validation

✅ **Payment Processing**
- Multiple payment methods (bKash, Nagad, Rocket, Bank)
- Payment verification workflow
- Admin payment verification dashboard

✅ **Dynamic Form Configuration**
- Organizer-defined custom fields
- Game-specific fields (eFootball, Valorant)
- Conditional field display

✅ **Capacity Management**
- Real-time slot tracking
- Waitlist support
- Auto-close on full capacity

✅ **State Machine**
- Tournament lifecycle management
- Registration status tracking
- Automated transitions

### 1.3 User Roles

| Role | Permissions | Use Cases |
|------|-------------|-----------|
| **Anonymous User** | View tournaments | Browse available tournaments |
| **Authenticated User** | Register for tournaments | Solo tournament registration |
| **Team Captain** | Register team, Approve requests | Team tournament registration |
| **Team Member** | Request registration approval | Join captain's tournament registration |
| **Tournament Organizer** | Configure tournament, View registrations | Manage tournament settings |
| **Admin/Staff** | Verify payments, Manage registrations | Payment verification, Support |

---

## 2. Architecture & Technology Stack

### 2.1 Backend Stack

```yaml
Framework: Django 4.2.24
Database: PostgreSQL 15+
Cache: Redis (for real-time data)
Task Queue: Celery (for async processing)
API: Django REST Framework 3.14+
WebSocket: Django Channels (for live updates)
```

### 2.2 Frontend Stack

```yaml
Template Engine: Django Templates (Jinja2-style)
JavaScript: Vanilla JS (ES6+)
CSS Framework: Custom (Cyberpunk theme)
Icons: Font Awesome 6
Rich Text Editor: CKEditor 5
```

### 2.3 Project Structure

```
apps/tournaments/
├── models/                      # Database models
│   ├── __init__.py             # Model exports
│   ├── tournament.py           # Core Tournament model
│   ├── registration.py         # Registration model
│   ├── registration_request.py # Approval request model
│   ├── bracket.py              # Bracket/match models
│   ├── payment_verification.py # Payment tracking
│   ├── state_machine.py        # State machine logic
│   └── core/                   # Phase 1 refactored models
│       ├── schedule.py         # TournamentSchedule
│       ├── capacity.py         # TournamentCapacity
│       └── finance.py          # TournamentFinance
│
├── services/                    # Business logic layer
│   ├── registration_service.py # Main registration logic
│   ├── approval_service.py     # Captain approval logic
│   ├── enhanced_registration.py # Advanced features
│   └── registration_request.py # Request handling
│
├── views/                       # View controllers
│   ├── registration_modern.py  # Modern registration views
│   ├── detail_v8.py           # Tournament detail page
│   ├── hub_enhanced.py        # Tournament listing
│   └── api_dashboard.py       # Dashboard APIs
│
├── api/                        # API endpoints
│   └── features.py            # Advanced feature APIs
│
├── api_views.py               # REST API views
├── serializers.py             # DRF serializers
├── forms_registration.py      # Django forms
├── urls.py                    # URL routing
├── admin.py                   # Admin interface
└── tasks.py                   # Celery tasks
```

### 2.4 System Dependencies

**Required Django Apps:**
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party
    'rest_framework',
    'django_ckeditor_5',
    'channels',
    
    # DeltaCrown apps
    'apps.tournaments',
    'apps.teams',
    'apps.user_profile',
    'apps.ecommerce',  # For payment tracking
]
```

**External Services:**
- Payment gateways (bKash, Nagad, Rocket)
- Email service (SMTP or SendGrid)
- Cloud storage (for team logos, screenshots)

---

## 3. Database Models & Schema

### 3.1 Core Models Overview

The registration system consists of 3 primary models:

1. **Tournament** - The tournament entity
2. **Registration** - Confirmed registrations
3. **RegistrationRequest** - Pending approval requests (for non-captains)

### 3.2 Tournament Model

**File:** `apps/tournaments/models/tournament.py`

#### Fields

```python
class Tournament(models.Model):
    # ===== BASICS =====
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    short_description = CKEditor5Field(blank=True, null=True)
    description = CKEditor5Field(blank=True, null=True)
    
    # ===== CONFIGURATION =====
    game = models.CharField(
        max_length=20,
        choices=[
            ('valorant', 'Valorant'),
            ('efootball', 'eFootball Mobile')
        ]
    )
    
    status = models.CharField(
        max_length=16,
        choices=[
            ('DRAFT', 'Draft'),          # Hidden from public
            ('PUBLISHED', 'Published'),  # Visible, registration may be closed
            ('RUNNING', 'Running'),      # Tournament in progress
            ('COMPLETED', 'Completed')   # Tournament finished
        ],
        default='DRAFT'
    )
    
    tournament_type = models.CharField(
        max_length=32,
        choices=[
            ('SOLO', 'Solo'),           # Individual players only
            ('TEAM', 'Team'),           # Teams only
            ('MIXED', 'Mixed (Solo & Team)')  # Both allowed
        ],
        default='TEAM'
    )
    
    format = models.CharField(
        max_length=32,
        choices=[
            ('SINGLE_ELIM', 'Single Elimination'),
            ('DOUBLE_ELIM', 'Double Elimination'),
            ('ROUND_ROBIN', 'Round Robin'),
            ('SWISS', 'Swiss System'),
            ('GROUP_STAGE', 'Group Stage'),
            ('HYBRID', 'Hybrid (Groups + Bracket)')
        ],
        blank=True
    )
    
    platform = models.CharField(
        max_length=32,
        choices=[
            ('ONLINE', 'Online'),
            ('OFFLINE', 'Offline/LAN'),
            ('HYBRID', 'Hybrid')
        ],
        default='ONLINE'
    )
    
    region = models.CharField(max_length=64, blank=True)
    language = models.CharField(
        max_length=8,
        choices=[
            ('en', 'English'),
            ('bn', 'বাংলা (Bengali)'),
            ('hi', 'हिन्दी (Hindi)'),
            ('multi', 'Multilingual')
        ],
        default='en'
    )
    
    organizer = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organized_tournaments'
    )
    
    banner = models.ImageField(
        upload_to='tournaments/banners/%Y/%m/',
        blank=True,
        null=True
    )
    
    # ===== DEPRECATED FIELDS (use Phase 1 models instead) =====
    # These are kept for backward compatibility
    slot_size = models.PositiveIntegerField(null=True, blank=True)
    reg_open_at = models.DateTimeField(blank=True, null=True)
    reg_close_at = models.DateTimeField(blank=True, null=True)
    start_at = models.DateTimeField(blank=True, null=True)
    end_at = models.DateTimeField(blank=True, null=True)
    entry_fee_bdt = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prize_pool_bdt = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # ===== METADATA =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    groups_published = models.BooleanField(default=False)
```

#### Important Properties

```python
# Registration status
@property
def registration_open(self) -> bool:
    """Check if registration is currently open"""
    # Prefers TournamentSchedule.is_registration_open()
    # Falls back to reg_open_at/reg_close_at comparison

# Capacity tracking
@property
def slots_total(self) -> int:
    """Total slots (prefers TournamentCapacity.max_teams)"""

@property
def slots_taken(self) -> int:
    """Current registrations (prefers TournamentCapacity.current_teams)"""

@property
def is_full(self) -> bool:
    """Check if tournament is at capacity"""

# URL helpers
@property
def register_url(self) -> str:
    """URL to registration page"""
    return f"/tournaments/register-modern/{self.slug}/"

@property
def detail_url(self) -> str:
    """URL to tournament detail page"""
    return f"/tournaments/t/{self.slug}/"
```

#### Database Indexes

```python
class Meta:
    indexes = [
        models.Index(fields=["slug"]),
        models.Index(fields=["status"]),
        models.Index(fields=["game"]),
    ]
```

---

### 3.3 Registration Model

**File:** `apps/tournaments/models/registration.py`

#### Purpose
Represents a **confirmed** or **pending** tournament registration. Can be for either a solo user OR a team (mutually exclusive).

#### Fields

```python
class Registration(models.Model):
    # ===== PARENT =====
    tournament = models.ForeignKey(
        "Tournament",
        on_delete=models.CASCADE,
        related_name="registrations"
    )
    
    # ===== PARTICIPANT (Either user OR team, not both) =====
    user = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="solo_registrations"
    )
    
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="team_registrations"
    )
    
    # ===== PAYMENT INFO =====
    payment_method = models.CharField(
        max_length=32,
        blank=True,
        choices=[
            ('bkash', 'bKash'),
            ('nagad', 'Nagad'),
            ('rocket', 'Rocket'),
            ('bank', 'Bank Transfer')
        ]
    )
    
    payment_sender = models.CharField(
        max_length=64,
        blank=True,
        help_text="Sender's mobile number or account"
    )
    
    payment_reference = models.CharField(
        "Transaction ID",
        max_length=64,
        blank=True,
        help_text="Payment transaction ID"
    )
    
    payment_status = models.CharField(
        max_length=16,
        choices=[
            ('pending', 'Pending'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected')
        ],
        default='pending'
    )
    
    # ===== REGISTRATION STATUS =====
    status = models.CharField(
        max_length=16,
        choices=[
            ('PENDING', 'Pending'),        # Awaiting payment verification
            ('CONFIRMED', 'Confirmed'),    # Approved and active
            ('CANCELLED', 'Cancelled')     # Cancelled by user or admin
        ],
        default='PENDING'
    )
    
    # ===== VERIFICATION =====
    payment_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+"
    )
    
    payment_verified_at = models.DateTimeField(null=True, blank=True)
    
    # ===== TIMESTAMPS =====
    created_at = models.DateTimeField(auto_now_add=True)
```

#### Validation Rules

```python
def clean(self):
    # Rule 1: Must have either user OR team (not both, not neither)
    if not self.user and not self.team:
        raise ValidationError("Registration must have either a user or a team.")
    if self.user and self.team:
        raise ValidationError("Registration cannot have both a user and a team.")
    
    # Rule 2: No duplicate registrations
    # Database constraints enforce uniqueness:
    # - (tournament, user) when user is set
    # - (tournament, team) when team is set
```

#### Database Constraints

```python
class Meta:
    constraints = [
        # Prevent duplicate user registration
        UniqueConstraint(
            fields=["tournament", "user"],
            condition=Q(user__isnull=False),
            name="uq_registration_tournament_user_not_null"
        ),
        
        # Prevent duplicate team registration
        UniqueConstraint(
            fields=["tournament", "team"],
            condition=Q(team__isnull=False),
            name="uq_registration_tournament_team_not_null"
        ),
    ]
    
    indexes = [
        models.Index(fields=["tournament", "status"]),
        models.Index(fields=["payment_status"]),
    ]
```

#### Query Examples

```python
# Get all confirmed registrations for a tournament
confirmed_regs = Registration.objects.filter(
    tournament=tournament,
    status='CONFIRMED'
).select_related('user', 'team')

# Check if user is registered
is_registered = Registration.objects.filter(
    tournament=tournament,
    user=user_profile
).exists()

# Get pending payment verifications
pending_payments = Registration.objects.filter(
    payment_status='pending'
).select_related('tournament', 'user', 'team')

# Count team registrations
team_count = Registration.objects.filter(
    tournament=tournament,
    team__isnull=False,
    status='CONFIRMED'
).count()
```

---

### 3.4 RegistrationRequest Model

**File:** `apps/tournaments/models/registration_request.py`

#### Purpose
Handles the approval workflow when a **non-captain team member** wants to register their team for a tournament. The captain must approve before a `Registration` is created.

#### Fields

```python
class RegistrationRequest(models.Model):
    # ===== CORE REFERENCES =====
    tournament = models.ForeignKey(
        "Tournament",
        on_delete=models.CASCADE,
        related_name="registration_requests"
    )
    
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="tournament_requests"
    )
    
    requested_by = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="tournament_requests"
    )
    
    # ===== STATUS =====
    status = models.CharField(
        max_length=16,
        choices=[
            ('PENDING', 'Pending'),      # Awaiting captain approval
            ('APPROVED', 'Approved'),    # Captain approved
            ('REJECTED', 'Rejected'),    # Captain rejected
            ('EXPIRED', 'Expired')       # Auto-expired after deadline
        ],
        default='PENDING'
    )
    
    # ===== APPROVAL TRACKING =====
    approved_by = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_requests"
    )
    
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # ===== TIMESTAMPS =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### Database Constraints

```python
class Meta:
    constraints = [
        # One pending request per team per tournament
        UniqueConstraint(
            fields=["tournament", "team"],
            condition=Q(status='PENDING'),
            name="uq_pending_request_per_team"
        ),
    ]
    
    indexes = [
        models.Index(fields=["tournament", "status"]),
        models.Index(fields=["team", "status"]),
        models.Index(fields=["requested_by", "status"]),
    ]
```

#### Workflow Example

```python
# Step 1: Non-captain creates request
request = RegistrationRequest.objects.create(
    tournament=tournament,
    team=user_team,
    requested_by=user_profile,
    status='PENDING'
)

# Step 2: Captain approves
request.status = 'APPROVED'
request.approved_by = captain_profile
request.approved_at = timezone.now()
request.save()

# Step 3: System creates Registration
registration = Registration.objects.create(
    tournament=tournament,
    team=user_team,
    status='PENDING',
    # ... payment info from request
)
```

---


## 4. API Endpoints Reference

### 4.1 Registration Endpoints

Base URL: `/tournaments/`

#### 4.1.1 Modern Registration View (Primary)

**Endpoint:** `GET/POST /tournaments/register-modern/<slug>/`  
**Name:** `tournaments:modern_register`  
**Authentication:** Required (login_required)  
**Purpose:** Main registration page with multi-step form

**GET Response:**
Renders template with context object containing tournament data, user profile data, team data, and entry fee information.

**POST Request:** Form data includes display_name, email, phone, in_game credentials, payment information, and rule agreement.

**POST Success:** Redirects to tournament detail page with success message.

---

#### 4.1.2 Registration Context API

**Endpoint:** `GET /api/<slug>/register/context/`  
**Name:** `tournaments:registration_context_api`  
**Authentication:** Required  
**Purpose:** Get real-time registration context for UI state management

Returns JSON with can_register status, button state, messages, and user/team information.

---

#### 4.1.3 Validate Registration API

**Endpoint:** `POST /api/<slug>/register/validate/`  
**Name:** `tournaments:validate_registration_api`  
**Authentication:** Required  
**Purpose:** Real-time validation before submission

Returns validation result with field-specific errors if any.

---

#### 4.1.4 Submit Registration API

**Endpoint:** `POST /api/<slug>/register/submit/`  
**Name:** `tournaments:submit_registration_api`  
**Authentication:** Required  
**Purpose:** Submit final registration (creates Registration record)

Returns success with registration ID and redirect URL, or errors on validation failure.

---

#### 4.1.5 Request Approval API (Non-Captain)

**Endpoint:** `POST /api/<slug>/request-approval/`  
**Name:** `tournaments:request_approval_api`  
**Authentication:** Required  
**Purpose:** Create approval request for team captain

---

#### 4.1.6 Pending Requests API (Captain View)

**Endpoint:** `GET /api/registration-requests/pending/`  
**Name:** `tournaments:pending_requests_api`  
**Authentication:** Required (must be captain)  
**Purpose:** Get all pending approval requests for captain's teams

---

#### 4.1.7 Approve Request API

**Endpoint:** `POST /api/registration-requests/<request_id>/approve/`  
**Name:** `tournaments:approve_request_api`  
**Authentication:** Required (must be captain)  
**Purpose:** Approve team registration request

---

#### 4.1.8 Reject Request API

**Endpoint:** `POST /api/registration-requests/<request_id>/reject/`  
**Name:** `tournaments:reject_request_api`  
**Authentication:** Required (must be captain)  
**Purpose:** Reject team registration request

---

### 4.2 Tournament State API

**Endpoint:** `GET /api/<slug>/state/`  
**Name:** `tournaments:state_api`  
**Authentication:** Optional  
**Purpose:** Get real-time tournament state for live updates

Returns status, registration state, capacity, and user-specific status.

---

### 4.3 Tournament Detail APIs

#### 4.3.1 Teams API

**Endpoint:** `GET /api/t/<slug>/teams/`  
Supports filtering by status, search, and pagination.
Returns registered teams with member details.

#### 4.3.2 Matches API

**Endpoint:** `GET /api/<slug>/matches/`  
Returns match schedule and results with bracket information.

#### 4.3.3 Leaderboard API

**Endpoint:** `GET /api/t/<slug>/leaderboard/`  
Returns current tournament standings with stats and prizes.

#### 4.3.4 Registration Status API

**Endpoint:** `GET /api/t/<slug>/registration-status/`  
Returns user's registration status for a specific tournament.

#### 4.3.5 Live Stats API

**Endpoint:** `GET /api/tournaments/<slug>/live-stats/`  
Returns real-time tournament statistics for counters.

---

## 5. Service Layer Architecture

### 5.1 RegistrationService

**File:** `apps/tournaments/services/registration_service.py`

Core business logic layer for registration operations.

#### Key Methods:

##### get_registration_context(tournament, user) -> RegistrationContext
Determines if user can register and returns complete context with eligibility checks.

##### create_registration(tournament, user, data, team=None) -> Registration
Creates a new registration with full validation and capacity management.

##### validate_registration_data(tournament, user, data) -> Tuple[bool, Dict]
Validates registration data without creating record. Returns (is_valid, errors).

##### auto_fill_profile_data(user) -> Dict
Extracts user profile data for form auto-fill.

##### auto_fill_team_data(team) -> Dict
Extracts team data for form auto-fill.

---

### 5.2 ApprovalService

**File:** `apps/tournaments/services/approval_service.py`

Handles captain approval workflow for team registrations.

#### Key Methods:

##### create_approval_request(tournament, team, requested_by) -> RegistrationRequest
Creates approval request for team captain.

##### approve_request(request_id, captain, payment_data) -> Registration
Approves request and creates registration.

##### reject_request(request_id, captain, reason) -> RegistrationRequest
Rejects approval request with reason.

##### get_pending_requests_for_captain(captain) -> QuerySet
Gets all pending approval requests for captain's teams.

---

