# Registration Backend Models Audit (Part 1/6)

**DeltaCrown Tournament System - Backend Model Analysis**  
Date: December 7, 2025  
Scope: Core models and data flow for tournament registration

---

## 1. Core Models Involved in Registration

### 1.1 Tournament (`apps.tournaments.models.Tournament`)

**Purpose**: Defines tournament configuration and rules.

**Key Fields**:
- `id` (PK) - Tournament identifier
- `name`, `slug` - Tournament identification
- `game` (FK) - References `tournaments.Game` (legacy model)
- `organizer` (FK) - References `accounts.User`
- `participation_type` - Choices: `SOLO`, `TEAM`
- `max_participants` - Registration capacity limit
- `registration_start`, `registration_end` - Registration window
- `status` - Workflow: `DRAFT` → `REGISTRATION_OPEN` → `LIVE` → `COMPLETED`
- `entry_fee` (Decimal) - Payment amount required
- `payment_methods` (ArrayField) - Allowed payment types

**Critical Issue**: Uses legacy `tournaments.Game` model instead of modern `apps.games.Game`.

---

### 1.2 Registration (`apps.tournaments.models.Registration`)

**Purpose**: Tracks individual/team participation in tournament.

**Key Fields**:
- `id` (PK)
- `tournament` (FK) → `Tournament`
- `user` (FK, nullable) → `accounts.User` (for solo tournaments or team captain)
- `team_id` (IntegerField, nullable) - **Not a ForeignKey**, stores Team ID as integer
- `registration_data` (JSONField) - Flexible storage for participant data
- `status` - Workflow: `pending` → `payment_submitted` → `confirmed` / `rejected` / `cancelled`
- `checked_in` (Boolean) - Tournament day check-in status
- `slot_number` (Integer, nullable) - Bracket position assignment
- `seed` (Integer, nullable) - Seeding for bracket generation

**XOR Constraint**: Either `user` OR `team_id` must be set (enforced via CHECK constraint).

**Registration Data JSON Structure**:
```json
{
  "game_id": "Player#TAG",           // In-game username/ID
  "phone": "+8801712345678",         // Contact number
  "notes": "Player notes",           // Optional notes
  "custom_fields": {...},            // Tournament-specific fields
  "team_roster": [...]               // For team registrations
}
```

---

### 1.3 Payment (`apps.tournaments.models.Payment`)

**Purpose**: Tracks payment proof submission and verification.

**Key Fields**:
- `registration` (FK) → `Registration`
- `payment_method` - Choices: `bkash`, `nagad`, `bank_transfer`, etc.
- `amount` (Decimal)
- `transaction_id` - Payment reference number
- `payment_proof` (ImageField) - Screenshot/receipt upload
- `status` - Workflow: `pending` → `verified` / `rejected`
- `verified_by` (FK, nullable) → `accounts.User` (admin who verified)
- `verified_at` (DateTime, nullable)

---

### 1.4 Related Models (Cross-App Dependencies)

#### User & UserProfile (`apps.accounts.User`, `apps.user_profile.UserProfile`)

**Registration Auto-fill Source**:
- `UserProfile.riot_id` - Valorant game ID
- `UserProfile.riot_tagline` - Riot tagline
- `UserProfile.steam_id` - Steam/CS2 ID
- `UserProfile.efootball_id` - eFootball ID
- `UserProfile.phone` - Contact phone
- `UserProfile.region` - Geographic region

**Usage**: Auto-fills `Registration.registration_data` during submission.

---

#### Team (`apps.teams.models.Team`)

**Referenced Via**: `Registration.team_id` (IntegerField, **not ForeignKey**)

**Key Fields**:
- `id` - Team identifier (stored in `Registration.team_id`)
- `name`, `tag` - Team identification
- `game` (CharField) - Which game team plays (uses string slugs)

**Permission Check**: TeamMembership validates registration authority.

---

#### TeamMembership (`apps.teams.models.TeamMembership`)

**Purpose**: Validates who can register team for tournaments.

**Key Fields**:
- `team` (FK) → `Team`
- `profile` (FK) → `UserProfile`
- `role` - Choices: `OWNER`, `MANAGER`, `PLAYER`, etc.
- `can_register_tournaments` (Boolean) - Explicit permission flag
- `status` - Must be `ACTIVE`

**Permission Logic**:
- `OWNER` role → Always can register
- `MANAGER` role → Always can register
- Other roles → Only if `can_register_tournaments=True`

---

#### Game Models (Dual Architecture Problem)

**Legacy Model**: `apps.tournaments.models.Game`
- Used by `Tournament.game` (ForeignKey)
- Stores: `name`, `slug`, `profile_id_field`, `default_team_size`

**Modern Model**: `apps.games.models.Game`
- Canonical game registry
- More comprehensive configuration (roster rules, tournament config)
- **Not integrated** with tournament registration flow

**Issue**: Two Game models exist, creating confusion and hardcoded game logic.

---

## 2. Registration Flow (Backend)

### 2.1 Solo Registration Flow

```
User clicks "Register" → RegistrationService.register_participant()
  ↓
1. Fetch Tournament (with game info)
2. Check Eligibility:
   - Tournament status = REGISTRATION_OPEN
   - Current time within registration window
   - Tournament not full (count existing registrations)
   - User not already registered
3. Auto-fill registration_data from UserProfile:
   - riot_id, steam_id, phone, etc. → JSONField
4. Create Registration record:
   - user = current_user
   - team_id = NULL
   - status = 'pending'
   - registration_data = {auto-filled + user-provided data}
5. Save to database
6. Return Registration object
```

**Key Service**: `apps.tournaments.services.registration_service.RegistrationService`

**Auto-fill Logic**: `RegistrationAutoFillService.get_autofill_data(user, tournament)`
- Reads `UserProfile` fields
- Maps to tournament's game requirements
- Returns dict with completion percentage

---

### 2.2 Team Registration Flow

```
Team Captain clicks "Register Team" → RegistrationService.register_participant()
  ↓
1. Fetch Tournament
2. Check Eligibility (same as solo, plus):
   - Participation type must be TEAM
   - User must be OWNER/MANAGER or have can_register_tournaments=True
   - Team not already registered (check team_id)
3. Auto-fill team roster data
4. Create Registration record:
   - user = NULL (XOR constraint)
   - team_id = team.id (IntegerField, not FK)
   - status = 'pending'
   - registration_data = {team_roster, contact info}
5. Save to database
```

**Permission Validation**: `_validate_team_registration_permission(team_id, user)`
- Queries `TeamMembership` for user's role
- Checks `can_register_tournaments` flag
- Raises `ValidationError` if unauthorized

---

### 2.3 Payment Flow (If Entry Fee Required)

```
Registration created (status='pending')
  ↓
User submits payment proof → PaymentService.submit_payment()
  ↓
1. Create Payment record:
   - registration (FK)
   - payment_method, amount, transaction_id
   - payment_proof (image upload)
   - status = 'pending'
2. Update Registration.status = 'payment_submitted'
3. Notify admins for verification
  ↓
Admin verifies → PaymentService.verify_payment()
  ↓
1. Update Payment.status = 'verified'
2. Set verified_by, verified_at
3. Update Registration.status = 'confirmed'
4. Notify user of confirmation
```

**Key Service**: `apps.tournaments.services.payment_service.PaymentService`

---

## 3. Database Relationships

### 3.1 Foreign Key Relationships

```
Tournament ←─[FK]─ Registration
    ↓
  Game (legacy)

User ←─[FK]─ Registration (nullable, for solo or captain)
User ←─[FK]─ Payment.verified_by (nullable, admin)

Registration ←─[FK]─ Payment
```

### 3.2 Non-FK Integer Relationships (Risk Area)

```
Registration.team_id (IntegerField)
    ↓ (manual lookup)
  Team (apps.teams)
    ↓
  TeamMembership → UserProfile
```

**Why IntegerField instead of ForeignKey?**
- Avoids circular dependency between `apps.tournaments` and `apps.teams`
- Allows loose coupling (teams can be deleted without breaking registrations)
- **Risk**: No referential integrity enforcement at database level

---

### 3.3 Cross-App Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    REGISTRATION FLOW                         │
└─────────────────────────────────────────────────────────────┘

apps.accounts.User
      │
      ├─> UserProfile (apps.user_profile)
      │       │
      │       └─> Auto-fill data (riot_id, steam_id, phone)
      │               ↓
      └───────> Registration (apps.tournaments)
                      │
                      ├─> registration_data (JSONField)
                      ├─> Tournament → Game (legacy)
                      └─> team_id (IntegerField) ──┐
                                                    │
apps.teams.Team <─────────────────────────────────┘
      │
      └─> TeamMembership
              └─> Validates registration permission
```

---

## 4. Key Observations

### 4.1 Architecture Issues

1. **Dual Game Model Problem**:
   - `tournaments.Game` (legacy) vs `apps.games.Game` (modern)
   - Tournament uses legacy model via FK
   - No integration with modern GameService

2. **Loose Coupling via IntegerField**:
   - `Registration.team_id` not a ForeignKey
   - Manual lookups required (`Team.objects.get(id=team_id)`)
   - No CASCADE delete protection

3. **Direct Model Imports**:
   - Services import `Team`, `TeamMembership` directly
   - No TeamService abstraction layer
   - Violates service-oriented architecture principles

### 4.2 Auto-fill Mechanism

**Current Implementation**:
- `RegistrationAutoFillService` reads UserProfile fields
- Maps game-specific IDs (riot_id for Valorant, steam_id for CS2)
- Calculates completion percentage
- Returns dict with `{field_name: {value, missing, source}}`

**Limitation**: Hardcoded game logic (if-else checks for game slugs).

### 4.3 Registration State Machine

```
pending → payment_submitted → confirmed
  ↓            ↓                  ↓
rejected   rejected          cancelled (soft delete)
  ↓            ↓
waitlisted  waitlisted
```

**Soft Delete**: Cancellations use `is_deleted=True` flag (preserves audit trail).

---

## 5. Data Validation Layers

### 5.1 Database Constraints

- **XOR Constraint**: `(user IS NOT NULL AND team_id IS NULL) OR (user IS NULL AND team_id IS NOT NULL)`
- **Unique Registration**: `(tournament, user)` unique together
- **Unique Team Registration**: `(tournament, team_id)` when team_id not null
- **Unique Slot**: `(tournament, slot_number)` when slot assigned

### 5.2 Service Layer Validation

**RegistrationService.check_eligibility()**:
1. Tournament status check
2. Registration window check
3. Capacity check (count existing registrations)
4. Duplicate registration check
5. Participation type match (solo vs team)
6. Team permission check (if team registration)

### 5.3 Model-Level Validation

**Registration.clean()**:
- Ensures XOR constraint (user OR team_id, not both)
- Validates slot_number > 0 if assigned

---

## 6. Missing Abstractions

### 6.1 No Service Contracts

**Current State**: Services directly import models from other apps.

**Missing**:
- `TeamService` - Should abstract Team/TeamMembership access
- `UserService` - Should abstract User/UserProfile access  
- `GameService` - Exists in `apps.games` but not integrated

### 6.2 No Event-Driven Architecture

**Current Flow**: Synchronous, procedural.

**Missing**:
- Registration events (RegistrationCreated, PaymentVerified)
- Cross-app event subscriptions
- Async notification triggers

---

## Summary

**Registration System Characteristics**:
- ✅ Well-structured service layer pattern
- ✅ Comprehensive validation and constraints
- ✅ Flexible JSONField for registration data
- ❌ Dual Game model architecture (legacy vs modern)
- ❌ Loose coupling via IntegerField (team_id)
- ❌ Direct cross-app model imports (no service abstraction)
- ❌ Hardcoded game logic in auto-fill

**Next Parts**:
- Part 2: Frontend/UI registration wizard flow
- Part 3: Payment verification workflow
- Part 4: Cross-app integration patterns
- Part 5: Data migration and legacy patterns
- Part 6: Recommendations for modernization

