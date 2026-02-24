# TournamentOps Adapters

**Purpose**: Protocol-based adapters providing zero-coupling access to domain services (Teams, Users, Games, Economy) from the TournamentOps orchestration layer.

**Phase**: 1 (Core Foundation)  
**Epic**: 1.1 (Service Adapter Layer)

---

## Architecture Overview

The adapter pattern enforces **strict domain separation** by:

1. **Defining Protocol contracts** - Adapters are runtime-checkable Protocols with abstract method signatures
2. **Returning DTOs only** - All methods return data transfer objects (DTOs) instead of Django ORM models
3. **Zero cross-domain imports** - TournamentOps code NEVER imports from `apps.teams`, `apps.players`, etc.
4. **Dependency injection** - Services receive adapters via constructor injection

This architecture allows:

- **Independent deployments** - Teams app can be deployed separately without affecting TournamentOps
- **Testing without DB** - Services can be tested with fake adapters (no database needed)
- **Framework independence** - DTOs have no Django dependencies
- **Clear boundaries** - Prevents accidental tight coupling between domains

---

## Available Adapters

### 1. TeamAdapter (`team_adapter.py`)

**Responsibility**: Retrieve team data and verify team eligibility for tournaments.

**Methods**:

```python
def get_team(self, team_id: int) -> TeamDTO:
    """
    Get team data by ID.
    
    Args:
        team_id: Team primary key.
        
    Returns:
        TeamDTO with team information.
        
    Raises:
        TeamNotFoundError: If team does not exist.
    """
    
def check_team_eligibility(
    self, team_id: int, tournament_id: int, game_slug: str
) -> EligibilityResultDTO:
    """
    Check if a team is eligible for a tournament.
    
    Args:
        team_id: Team primary key.
        tournament_id: Tournament primary key.
        game_slug: Game identifier (e.g., "valorant").
        
    Returns:
        EligibilityResultDTO with is_eligible flag and reasons.
    """
```

**Usage Example**:

```python
from apps.tournament_ops.adapters.team_adapter import TeamAdapter
from apps.tournament_ops.dtos.team import TeamDTO

# In production, this would be an implementation that queries apps.teams models
team_adapter: TeamAdapter = get_team_adapter_impl()

try:
    team = team_adapter.get_team(team_id=10)
    print(f"Team: {team.name}, Captain: {team.captain_name}")
    
    eligibility = team_adapter.check_team_eligibility(
        team_id=10, tournament_id=100, game_slug="valorant"
    )
    if not eligibility.is_eligible:
        print(f"Ineligible: {', '.join(eligibility.reasons)}")
except TeamNotFoundError:
    print("Team not found")
```

---

### 2. UserAdapter (`user_adapter.py`)

**Responsibility**: Retrieve user profile data and game account identities.

**Methods**:

```python
def get_user_profile(self, user_id: int) -> UserProfileDTO:
    """
    Get user profile data including game account identities.
    
    Args:
        user_id: User primary key.
        
    Returns:
        UserProfileDTO with contact info and game IDs.
        
    Raises:
        UserNotFoundError: If user does not exist.
    """
    
def verify_game_identity(
    self, user_id: int, game_slug: str, identity_value: str
) -> bool:
    """
    Verify that a user owns a specific game account identity.
    
    Args:
        user_id: User primary key.
        game_slug: Game identifier (e.g., "valorant").
        identity_value: Value to verify (e.g., "Player#NA1").
        
    Returns:
        True if verified, False otherwise.
    """
```

**Usage Example**:

```python
user_adapter: UserAdapter = get_user_adapter_impl()

try:
    profile = user_adapter.get_user_profile(user_id=200)
    print(f"Email: {profile.email}, Riot ID: {profile.riot_id}")
    
    is_verified = user_adapter.verify_game_identity(
        user_id=200, game_slug="valorant", identity_value="Player#NA1"
    )
    if not is_verified:
        print("Identity verification failed")
except UserNotFoundError:
    print("User not found")
```

---

### 3. GameAdapter (`game_adapter.py`)

**Responsibility**: Retrieve game configuration and player identity requirements.

**Methods**:

```python
def get_game_config(self, game_slug: str) -> Dict[str, Any]:
    """
    Get game-specific configuration (team size, identity fields, etc.).
    
    Args:
        game_slug: Game identifier (e.g., "valorant").
        
    Returns:
        Game configuration dict.
        
    Raises:
        GameConfigNotFoundError: If game config does not exist.
    """
    
def get_player_identity_fields(
    self, game_slug: str
) -> List[GamePlayerIdentityConfigDTO]:
    """
    Get required player identity fields for a game.
    
    Args:
        game_slug: Game identifier.
        
    Returns:
        List of identity field configs (riot_id, steam_id, etc.).
    """
```

**Usage Example**:

```python
game_adapter: GameAdapter = get_game_adapter_impl()

config = game_adapter.get_game_config(game_slug="valorant")
print(f"Default team size: {config['default_team_size']}")

identity_fields = game_adapter.get_player_identity_fields(game_slug="valorant")
for field in identity_fields:
    if field.is_required:
        print(f"Required field: {field.display_label}")
```

---

### 4. EconomyAdapter (`economy_adapter.py`)

**Responsibility**: Process payments, refunds, and entry fees for tournaments.

**Methods**:

```python
def charge_entry_fee(
    self, user_id: int, tournament_id: int, amount: Decimal
) -> PaymentResultDTO:
    """
    Charge a user for tournament entry.
    
    Args:
        user_id: User primary key.
        tournament_id: Tournament primary key.
        amount: Entry fee amount.
        
    Returns:
        PaymentResultDTO with success flag and transaction_id.
        
    Raises:
        PaymentFailedError: If payment processing fails.
    """
    
def refund_entry_fee(
    self, user_id: int, tournament_id: int, original_transaction_id: str
) -> PaymentResultDTO:
    """
    Refund a tournament entry fee.
    
    Args:
        user_id: User primary key.
        tournament_id: Tournament primary key.
        original_transaction_id: Transaction ID from original charge.
        
    Returns:
        PaymentResultDTO with refund status.
        
    Raises:
        PaymentFailedError: If refund processing fails.
    """
```

**Usage Example**:

```python
from decimal import Decimal

economy_adapter: EconomyAdapter = get_economy_adapter_impl()

try:
    result = economy_adapter.charge_entry_fee(
        user_id=200, tournament_id=100, amount=Decimal("10.00")
    )
    if result.success:
        print(f"Payment successful: {result.transaction_id}")
    else:
        print(f"Payment failed: {result.error}")
except PaymentFailedError as e:
    print(f"Payment error: {e}")
```

---

## Exception Hierarchy

All adapters raise exceptions from `apps.tournament_ops.exceptions`:

```python
TournamentOpsError (base)
├── TeamNotFoundError
├── UserNotFoundError
├── GameConfigNotFoundError
├── PaymentFailedError
├── EligibilityCheckFailedError
└── AdapterHealthCheckError
```

**Example Error Handling**:

```python
from apps.tournament_ops.exceptions import TeamNotFoundError, EligibilityCheckFailedError

try:
    team = team_adapter.get_team(team_id=999)
except TeamNotFoundError:
    return Response({"error": "Team not found"}, status=404)
except EligibilityCheckFailedError as e:
    return Response({"error": str(e)}, status=500)
```

---

## Implementation Guidelines

### For Adapter Implementers

When creating concrete adapter implementations:

1. **Import domain models ONLY in the implementation**:

```python
# ✅ CORRECT - Implementation file (e.g., apps/teams/tournament_ops_integration.py)
from apps.teams.models import Team
from apps.tournament_ops.adapters.team_adapter import TeamAdapter
from apps.tournament_ops.dtos.team import TeamDTO

class TeamAdapterImpl(TeamAdapter):
    def get_team(self, team_id: int) -> TeamDTO:
        team = Team.objects.get(pk=team_id)
        return TeamDTO.from_model(team)
```

2. **Never import ORM models in adapter Protocol files**:

```python
# ❌ WRONG - apps/tournament_ops/adapters/team_adapter.py
from apps.teams.models import Team  # NEVER DO THIS

class TeamAdapter(Protocol):
    ...
```

3. **Use DTO.from_model() for conversion**:

```python
# ✅ CORRECT - Use from_model() classmethod
team = Team.objects.get(pk=team_id)
return TeamDTO.from_model(team)

# ❌ WRONG - Manual field mapping
return TeamDTO(
    id=team.id,
    name=team.name,
    ...
)
```

4. **Raise exceptions from `apps.tournament_ops.exceptions`**:

```python
from apps.tournament_ops.exceptions import TeamNotFoundError

def get_team(self, team_id: int) -> TeamDTO:
    try:
        team = Team.objects.get(pk=team_id)
    except Team.DoesNotExist:
        raise TeamNotFoundError(f"Team {team_id} not found")
    return TeamDTO.from_model(team)
```

---

### For Service Developers

When using adapters in TournamentOps services:

1. **Inject adapters via constructor**:

```python
class RegistrationService:
    def __init__(
        self,
        team_adapter: TeamAdapter,
        user_adapter: UserAdapter,
        game_adapter: GameAdapter,
        economy_adapter: EconomyAdapter,
    ):
        self.team_adapter = team_adapter
        self.user_adapter = user_adapter
        self.game_adapter = game_adapter
        self.economy_adapter = economy_adapter
```

2. **Call adapter methods in orchestration logic**:

```python
def register_team(self, team_id: int, tournament_id: int) -> RegistrationDTO:
    # Get team data via adapter
    team = self.team_adapter.get_team(team_id)
    
    # Check eligibility via adapter
    eligibility = self.team_adapter.check_team_eligibility(
        team_id=team_id,
        tournament_id=tournament_id,
        game_slug=team.game,
    )
    
    if not eligibility.is_eligible:
        raise InvalidRegistrationStateError(eligibility.reasons)
    
    # Charge entry fee via adapter
    payment = self.economy_adapter.charge_entry_fee(
        user_id=team.captain_id,
        tournament_id=tournament_id,
        amount=Decimal("10.00"),
    )
    
    if not payment.success:
        raise PaymentFailedError(payment.error)
    
    # Create registration (orchestration logic)
    return self._create_registration(team_id, tournament_id, payment.transaction_id)
```

3. **Test with fake adapters**:

```python
class FakeTeamAdapter:
    def get_team(self, team_id: int) -> TeamDTO:
        return TeamDTO(
            id=team_id,
            name="Fake Team",
            captain_id=100,
            captain_name="Fake Captain",
            member_ids=[100, 101],
            member_names=["Alice", "Bob"],
            game="valorant",
            is_verified=True,
            logo_url=None,
        )

# Test without DB
service = RegistrationService(
    team_adapter=FakeTeamAdapter(),
    user_adapter=FakeUserAdapter(),
    game_adapter=FakeGameAdapter(),
    economy_adapter=FakeEconomyAdapter(),
)
```

---

## Testing Strategy

### Unit Tests (No Database)

Test adapters in isolation using fake objects:

```python
def test_team_adapter_protocol():
    """Verify that adapter implements TeamAdapter protocol."""
    adapter = TeamAdapterImpl()
    assert isinstance(adapter, TeamAdapter)

def test_get_team_returns_dto():
    """Test that get_team() returns TeamDTO."""
    adapter = FakeTeamAdapter()
    team = adapter.get_team(team_id=10)
    assert isinstance(team, TeamDTO)
    assert team.id == 10
```

### Integration Tests (With Database)

Test adapter implementations against real models:

```python
@pytest.mark.django_db
def test_team_adapter_impl_get_team():
    """Test TeamAdapterImpl.get_team() with real DB."""
    from apps.teams.models import Team
    from apps.teams.tournament_ops_integration import TeamAdapterImpl
    
    # Create test team
    team = Team.objects.create(name="Test Team", ...)
    
    adapter = TeamAdapterImpl()
    dto = adapter.get_team(team_id=team.id)
    
    assert dto.name == "Test Team"
    assert isinstance(dto, TeamDTO)
```

---

## Runtime Behavior (Phase 1 Implementation)

### TeamAdapter

**Implemented Methods**:

- `get_team(team_id)` - Calls `TeamService.get_team_by_id()`, converts to TeamDTO
- `list_team_members(team_id)` - Returns team.member_ids from TeamDTO
- `validate_membership(team_id, user_id)` - Checks if user_id in member_ids
- `validate_team_eligibility(...)` - Validates team verification, size, and game match
- `check_tournament_permission(user_id, team_id)` - Verifies user is team captain
- `check_health()` - Tests Team model DB connectivity

**Error Handling**: Raises `TeamNotFoundError` when team doesn't exist

### UserAdapter

**Implemented Methods**:

- `get_user_profile(user_id)` - Fetches UserProfile model, converts to UserProfileDTO
- `is_user_eligible(user_id, tournament_id)` - Checks email_verified status (Phase 1 basic check)
- `is_user_banned(user_id)` - Placeholder (returns False, TODO: ModerationService integration)
- `check_health()` - Tests UserProfile model DB connectivity

**TODO**: Integration with ModerationService for ban status, age/region checks based on tournament config

### GameAdapter

**Implemented Methods**:

- `get_game_config(game_slug)` - Calls `GameService.get_game()`, returns config dict
- `get_identity_fields(game_slug)` - Queries GamePlayerIdentityConfig, returns field definitions
- `validate_game_identity(...)` - Validates identity payload against field requirements (regex, required fields)
- `get_supported_formats(game_slug)` - Returns default tournament formats (TODO: query GameTournamentConfig)
- `get_scoring_rules(game_slug)` - Returns default scoring config (TODO: query GameScoringRule)
- `check_health()` - Tests Game model DB connectivity

**TODO**: Wire to GameTournamentConfig and GameScoringRule models (Phase 2)

### EconomyAdapter

**Implemented Methods**:

- `charge_registration_fee(...)` - Mock implementation returning transaction dict (TODO: WalletService integration)
- `refund_registration_fee(...)` - Mock implementation returning refund dict (TODO: WalletService integration)
- `get_balance(user_id)` - Mock implementation returning balance dict (TODO: WalletService integration)
- `verify_payment(transaction_id)` - Validates UUID format (basic check)
- `check_health()` - Returns True (no economy service dependency yet)

**TODO**: Integration with WalletService (Phase 1, Epic 1.4)

---

## Roadmap Integration

### Phase 1 (Current)

- ✅ Define adapter Protocols
- ✅ Create DTO layer
- ✅ Implement adapter logic with domain service calls
- ✅ Wire adapters into services
- ✅ Add comprehensive unit tests (43 tests passing)

### Phase 2 (Next)

- ⏳ Implement real adapter logic in domain apps
- ⏳ Add adapter health checks
- ⏳ Add adapter circuit breakers

### Phase 3 (Future)

- ⏳ Add adapter caching
- ⏳ Add adapter metrics
- ⏳ Add adapter rate limiting

---

## References

- **Roadmap**: `docs/teams/ROADMAP_AND_EPICS_PART_4.md` - Phase 1, Epic 1.1
- **Testing**: `docs/teams/CLEANUP_AND_TESTING_PART_6.md` - §9.1
- **Exceptions**: `apps/tournament_ops/exceptions.py`
- **DTOs**: `apps/tournament_ops/dtos/`
- **Services**: `apps/tournament_ops/services/`
