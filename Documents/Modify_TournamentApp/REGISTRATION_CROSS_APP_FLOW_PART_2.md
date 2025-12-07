# Registration Cross-App Flow Audit (Part 2/6)

**DeltaCrown Tournament System - Cross-App Integration Analysis**  
Date: December 7, 2025  
Scope: How registration flows across apps and legacy patterns

---

## 1. Cross-App Data Flow in Registration

### 1.1 Games App Integration

#### Current Usage Pattern

**Legacy Tournament.Game Model (Direct FK)**:
```python
# apps/tournaments/models/tournament.py
class Tournament:
    game = models.ForeignKey('Game', ...)  # Points to tournaments.Game (legacy)
```

**Modern apps.games.Game (Not Integrated)**:
- `apps.games.models.Game` exists with comprehensive config (GameRosterConfig, GameTournamentConfig)
- **NOT USED** in registration flow
- Only referenced in newer services via `game_service` imports

---

#### Hardcoded Game Logic (Critical Issue)

**Location**: `registration_wizard.py` lines 479-491

```python
# HARDCODED game slug checks
if game_slug == 'valorant':
    auto_filled['riot_id'] = profile.riot_id or ''
elif game_slug == 'pubg-mobile':
    auto_filled['pubg_mobile_id'] = profile.pubg_mobile_id or ''
elif game_slug == 'mobile-legends':
    auto_filled['mobile_legends_id'] = profile.mlbb_id or ''
elif game_slug == 'free-fire':
    auto_filled['free_fire_id'] = profile.free_fire_id or ''
elif game_slug == 'cod-mobile':
    auto_filled['cod_mobile_id'] = profile.codm_uid or ''
elif game_slug == 'dota-2' or game_slug == 'cs2':
    auto_filled['steam_id'] = profile.steam_id or ''
elif game_slug == 'efootball' or game_slug == 'ea-fc':
    auto_filled['efootball_id'] = profile.efootball_id or ''
```

**Problem**: Adding a new game requires code changes in multiple places.

---

**Location**: `leaderboard.py` lines 109-111

```python
if game_slug == 'free-fire':
    # Free Fire specific scoring
elif game_slug == 'pubg-mobile':
    # PUBG Mobile specific scoring
```

**Impact**: Game-specific business logic scattered across codebase.

---

#### Modern GameService (Partially Used)

**Import Found**:
```python
# registration_service.py line 325
from apps.games.services import game_service
```

**Usage**:
```python
# registration_wizard.py line 479 onwards
identity_configs = game_service.get_identity_validation_rules(tournament.game)
```

**Status**: GameService exists but only used sporadically. Most code still uses hardcoded checks.

---

### 1.2 Teams App Integration

#### Direct Model Imports (No Service Abstraction)

**Pattern Found in 6+ Files**:
```python
from apps.teams.models import Team, TeamMembership
```

**Files Affected**:
- `registration_service.py` (line 274)
- `registration_eligibility.py` (line 10)
- `registration_autofill.py` (lines 286, 320)
- Multiple view files

---

#### Team Permission Validation

**Flow**:
```python
# registration_service.py lines 274-307
from apps.teams.models import TeamMembership, Team

def _validate_team_registration_permission(team_id: int, user):
    # Get team (manual lookup via IntegerField)
    team = Team.objects.get(id=team_id)
    
    # Get user's membership
    membership = TeamMembership.objects.get(
        team=team,
        profile=user.profile,
        status=TeamMembership.Status.ACTIVE
    )
    
    # Check permission flag
    if not membership.can_register_tournaments:
        raise ValidationError("You do not have permission...")
```

**Issues**:
1. Direct model import violates service layer pattern
2. No `TeamService` abstraction
3. Permission logic duplicated across services

---

#### Team Data Auto-Fill

**Registration Auto-Fill Service** (`registration_autofill.py` lines 286-320):
```python
from apps.teams.models import TeamMember  # Direct import

def _get_team_autofill(user, team, tournament):
    # Team Name, Tag, Logo
    data['team_name'] = AutoFillField(value=team.name, ...)
    data['team_tag'] = AutoFillField(value=team.tag, ...)
    
    # Team Roster (queries TeamMembership directly)
    from apps.teams.models import TeamMembership
    roster = TeamMembership.objects.filter(
        team=team,
        status=TeamMembership.Status.ACTIVE
    )
    # Build roster list
```

**Pattern**: Services directly query Team models instead of using TeamService API.

---

#### IntegerField Team Reference (High Risk)

**Registration Model**:
```python
team_id = models.IntegerField(null=True, blank=True, db_index=True)
```

**Usage in Payment Flow** (`registration_service.py` lines 492-500):
```python
# Team registration - user must be team captain
from apps.teams.models import Team
try:
    team = Team.objects.get(id=registration.team_id)  # Manual lookup
    if team.captain.user_id != user.id:
        raise ValidationError("Only the team captain can pay...")
except Team.DoesNotExist:
    raise ValidationError("Team not found...")
```

**Risks**:
1. No foreign key constraint - team can be deleted, leaving orphaned registrations
2. Manual lookups required everywhere (`Team.objects.get(id=team_id)`)
3. No CASCADE behavior on team deletion
4. Data integrity depends on application logic, not database

---

### 1.3 User/UserProfile Integration

#### UserProfile Field Mapping (Hardcoded)

**Auto-Fill Service** (`registration_autofill.py` lines 100-250):

```python
# Direct UserProfile field access
profile = user.profile

# Hardcoded field mappings
data['phone'] = AutoFillField(value=profile.phone, ...)
data['country'] = AutoFillField(value=profile.country, ...)
data['discord'] = AutoFillField(value=profile.discord_id, ...)

# Game-specific ID fields (hardcoded per game)
auto_filled['riot_id'] = profile.riot_id or ''
auto_filled['steam_id'] = profile.steam_id or ''
auto_filled['efootball_id'] = profile.efootball_id or ''
auto_filled['pubg_mobile_id'] = profile.pubg_mobile_id or ''
auto_filled['mobile_legends_id'] = profile.mlbb_id or ''
# ... 10+ more game-specific fields
```

**Problem**: UserProfile must have dedicated field for every game's ID system.

---

#### UserProfile Schema Bloat

**Consequence of Direct Field Access**:
- `riot_id`, `riot_tagline` - Valorant
- `steam_id` - CS2, Dota 2
- `efootball_id` - eFootball
- `pubg_mobile_id` - PUBG Mobile
- `mlbb_id` - Mobile Legends
- `free_fire_id` - Free Fire
- `codm_uid` - COD Mobile
- `epic_id` - Fortnite (if added)
- ... infinitely growing list

**Modern Approach (Not Used)**: `apps.players.models.PlayerGameAccount` exists but registration doesn't use it.

---

#### No UserService Abstraction

**Current Pattern**:
```python
# Everywhere in tournaments app
profile = user.profile
if profile and profile.riot_id:
    # Use riot_id
```

**Missing**: Centralized `UserService.get_game_identity(user, game)` API.

---

### 1.4 Economy App Integration

#### DeltaCoin Payment Flow

**Service Import** (`registration_service.py` lines 476-477):
```python
from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.economy.exceptions import InsufficientFunds
```

**Payment Flow** (`registration_service.py` lines 460-550):

```python
def pay_with_deltacoin(registration_id, user):
    # Direct wallet model access (no EconomyService)
    wallet = DeltaCrownWallet.objects.select_for_update().get(profile=user.profile)
    
    # Check balance
    if wallet.cached_balance < entry_fee_dc:
        raise InsufficientFunds(...)
    
    # Create transaction directly
    dc_transaction = DeltaCrownTransaction.objects.create(
        wallet=wallet,
        amount=-entry_fee_dc,
        reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT,
        tournament_id=registration.tournament_id,
        registration_id=registration_id,
        idempotency_key=f"tournament_entry_{tournament_id}_reg_{registration_id}"
    )
    
    # Update wallet balance (manual calculation)
    wallet.cached_balance -= entry_fee_dc
    wallet.save()
```

**Issues**:
1. Direct model manipulation (no service layer)
2. Manual balance calculation (prone to race conditions despite `select_for_update`)
3. No abstraction - tournament service knows economy implementation details

---

#### Economy Service Pattern (Good Example)

**From Previous Audit**: `apps.economy.services.PaymentService` exists with clean API:
```python
PaymentService.credit(user_id, amount, reason)
PaymentService.debit(user_id, amount, reason)
```

**But**: Registration services don't use it! They directly manipulate wallet models.

---

#### Payment Proof Verification

**Manual Payment Flow** (Separate from DeltaCoin):
```python
# Payment model stores proof
payment = Payment.objects.create(
    registration=registration,
    payment_method='bkash',
    amount=entry_fee,
    transaction_id='TXN123',
    payment_proof='path/to/screenshot.jpg'  # ImageField upload
)
```

**No Integration**: Economy app not involved in manual payment verification.

---

### 1.5 Cross-App Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     REGISTRATION DATA FLOW                        │
└──────────────────────────────────────────────────────────────────┘

User Action: "Register for Tournament"
    ↓
┌─────────────────────────┐
│ RegistrationWizardView  │ (tournaments/views/registration_wizard.py)
│  └─> Manual game slug   │ ← HARDCODED: if game_slug == 'valorant'
│      if-else checks     │
└──────────┬──────────────┘
           ↓
┌──────────────────────────────────────────────────────────────────┐
│ RegistrationAutoFillService (tournaments/services)               │
│  ├─> Direct import: from apps.user_profile.models import ...     │ ← NO SERVICE
│  ├─> Direct field access: profile.riot_id, profile.steam_id     │
│  └─> Direct import: from apps.teams.models import Team          │ ← NO TeamService
└──────────┬───────────────────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────────────────────────────┐
│ RegistrationService.register_participant()                       │
│  ├─> Check eligibility                                           │
│  │    ├─> Direct Team.objects.get(id=team_id) ← IntegerField    │ ← HIGH RISK
│  │    └─> Direct TeamMembership query for permissions           │
│  ├─> Auto-fill from UserProfile (hardcoded field mapping)       │
│  └─> Create Registration (team_id as IntegerField)              │
└──────────┬───────────────────────────────────────────────────────┘
           ↓
┌──────────────────────────────────────────────────────────────────┐
│ PaymentService.pay_with_deltacoin() [if entry fee]              │
│  ├─> Direct import: DeltaCrownWallet, DeltaCrownTransaction     │ ← NO EconomyService
│  ├─> wallet.cached_balance -= amount (manual calculation)       │
│  └─> DeltaCrownTransaction.objects.create(...) directly         │
└──────────┬───────────────────────────────────────────────────────┘
           ↓
      Registration CONFIRMED
```

**Key Observation**: Registration orchestrates 4 apps but does it all via direct model imports.

---

## 2. Legacy / Risky Patterns

### 2.1 Dual Game Model Architecture

**Problem**: Two Game models exist simultaneously.

| Model | Location | Used By | Status |
|-------|----------|---------|--------|
| `Game` | `apps.tournaments.models` | `Tournament.game` (FK) | **ACTIVE** (legacy) |
| `Game` | `apps.games.models` | Modern GameService | **UNUSED** in registration |

**Impact**:
- Confusion about which model to use
- Duplicate data (game configs defined twice)
- Modern GameService features unavailable to registration

**Evidence**:
```python
# tournament.py
class Tournament:
    game = models.ForeignKey('Game', ...)  # Legacy tournaments.Game

# But game_service exists:
from apps.games.services import game_service  # Modern, comprehensive
```

---

### 2.2 Hardcoded Game Logic

#### Pattern 1: Game Slug If-Else Chains

**Locations**:
1. `registration_wizard.py` (lines 479-491) - 7 hardcoded game checks
2. `leaderboard.py` (lines 109-111) - Game-specific scoring
3. `group_stage_service.py` (line 487) - MOBA category check

**Example**:
```python
if game_slug == 'valorant':
    field = 'riot_id'
elif game_slug == 'cs2' or game_slug == 'dota-2':
    field = 'steam_id'
elif game_slug == 'pubg-mobile':
    field = 'pubg_mobile_id'
# ... 10 more conditions
```

**Maintenance Cost**: Every new game requires editing 3-5 files.

---

#### Pattern 2: Profile Field Name Assumptions

**Hardcoded UserProfile Field Names**:
```python
# Assumes UserProfile has these exact field names
profile.riot_id
profile.steam_id
profile.efootball_id
profile.pubg_mobile_id
profile.mlbb_id
profile.free_fire_id
```

**Risk**: Renaming a field breaks registration. No migration path.

---

### 2.3 IntegerField Foreign Keys (High Risk)

**Pattern Found**:
```python
# Registration model
team_id = models.IntegerField(null=True, blank=True)  # NOT ForeignKey
```

**Problems**:

1. **No Referential Integrity**:
   ```python
   # Team can be deleted, registration.team_id becomes orphaned
   Team.objects.filter(id=123).delete()
   # registration.team_id = 123 still exists (dangling reference)
   ```

2. **Manual Lookups Everywhere**:
   ```python
   # Every service must do:
   try:
       team = Team.objects.get(id=registration.team_id)
   except Team.DoesNotExist:
       # Handle orphaned reference
   ```

3. **No Database-Level Constraints**:
   - No ON DELETE CASCADE
   - No ON DELETE SET NULL
   - Application must handle cleanup manually

**Why This Pattern Exists**: Avoid circular dependency between `tournaments` and `teams` apps.

**Better Alternatives**:
- Use GenericForeignKey (Django's ContentType framework)
- Use service layer abstraction (don't import Team model directly)
- Store team data snapshot in Registration.registration_data (JSONB)

---

### 2.4 Direct Model Imports (No Service Contracts)

#### Cross-App Imports Found

**Teams Models** (12 occurrences):
```python
from apps.teams.models import Team, TeamMembership
```

**Economy Models** (3 occurrences):
```python
from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
```

**UserProfile** (assumed everywhere):
```python
user.profile  # No UserService wrapper
```

---

#### Missing Service Abstractions

**Should Exist**:
```python
# teams/services.py (MISSING)
class TeamService:
    @staticmethod
    def get_team_roster(team_id):
        """Get team roster without exposing Team model"""
    
    @staticmethod
    def validate_registration_permission(team_id, user):
        """Check if user can register team"""
```

**Should Exist**:
```python
# accounts/services.py (MISSING)
class UserService:
    @staticmethod
    def get_game_identity(user, game):
        """Get user's identity for specific game"""
    
    @staticmethod
    def get_contact_info(user):
        """Get email, phone without exposing profile"""
```

**Should Exist**:
```python
# economy/services.py (EXISTS but NOT USED)
class PaymentService:
    @staticmethod
    def credit(user_id, amount, reason):
        """Already exists!"""
    
    @staticmethod
    def debit(user_id, amount, reason):
        """Already exists!"""
```

**Current Reality**: Registration services bypass PaymentService and manipulate wallet models directly.

---

### 2.5 JSONB as Workaround for Rigid Schema

**Pattern**:
```python
# Registration.registration_data (JSONField)
{
    "game_id": "Player#TAG",
    "phone": "+880...",
    "custom_fields": {...},
    "team_roster": [...]
}
```

**Use Case**: Flexible storage for tournament-specific data.

**Problem**: No validation, schema varies per tournament, difficult to query.

**Better Approach**: Proper relational models with service layer.

---

### 2.6 Payment Flow Inconsistency

**Two Payment Paths**:

1. **DeltaCoin** (Automated):
   - Direct wallet manipulation
   - Immediate CONFIRMED status
   - No Payment record created (uses DeltaCrownTransaction)

2. **Manual (bkash, nagad, etc.)** (Manual):
   - Payment record with proof upload
   - PAYMENT_SUBMITTED status
   - Admin verification required
   - No economy app involvement

**Issue**: Inconsistent data models for different payment methods.

---

## 3. Summary of Cross-App Dependencies

### 3.1 Dependency Map

```
tournaments/services/registration_service.py
    ├─> apps.teams.models.Team (DIRECT)
    ├─> apps.teams.models.TeamMembership (DIRECT)
    ├─> apps.economy.models.DeltaCrownWallet (DIRECT)
    ├─> apps.economy.models.DeltaCrownTransaction (DIRECT)
    ├─> apps.games.services.game_service (via import, rarely used)
    └─> user.profile (assumed, no service)

tournaments/views/registration_wizard.py
    ├─> Hardcoded game slug checks (7 games)
    ├─> user.profile.riot_id, .steam_id, etc. (DIRECT)
    └─> apps.teams.models.Team (DIRECT)

tournaments/services/registration_autofill.py
    ├─> user.profile.* (DIRECT field access)
    └─> apps.teams.models.TeamMembership (DIRECT)
```

**Coupling Score**: 🔴 **High** - Direct model imports across 4 apps.

---

### 3.2 Risk Assessment

| Risk | Severity | Impact | Mitigation Needed |
|------|----------|--------|-------------------|
| Dual Game models | 🔴 High | Confusion, duplicate logic | Deprecate legacy tournaments.Game |
| Hardcoded game slugs | 🔴 High | Maintenance burden | Use GameService config |
| IntegerField team_id | 🟠 Medium | Data integrity | Service abstraction or GenericFK |
| No service contracts | 🔴 High | Tight coupling | Create TeamService, UserService |
| Direct wallet manipulation | 🟠 Medium | Race conditions, bugs | Use PaymentService.debit() |
| UserProfile field bloat | 🟡 Low | Schema growth | Use PlayerGameAccount model |

---

### 3.3 Modernization Path (Future)

**Phase 1**: Create service abstractions
- `TeamService` - Abstract Team/TeamMembership access
- `UserService` - Abstract UserProfile access
- Use existing `PaymentService` (economy.services)

**Phase 2**: Replace hardcoded game logic
- Use `GameService.get_identity_validation_rules(game)`
- Use `GameService.get_roster_config(game)`
- Remove if-else game slug chains

**Phase 3**: Fix data integrity
- Migrate `team_id` IntegerField → GenericForeignKey or service-only access
- Deprecate legacy `tournaments.Game` model
- Consolidate on `apps.games.Game`

---

## Next Steps

**Part 3/6**: Frontend registration UI/UX flow analysis  
**Part 4/6**: Payment verification and admin workflows  
**Part 5/6**: Match, bracket, and result processing  
**Part 6/6**: Recommendations and modernization roadmap

