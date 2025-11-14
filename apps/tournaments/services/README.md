# Tournament Services Layer

This directory contains service layer implementations for tournament management, following ADR-001 (Service Layer Architecture).

## Services

### TournamentService (`tournament_service.py`)
Handles tournament CRUD operations, status transitions, and business logic enforcement.

**Key Methods**:
- `create_tournament()` - Create tournament with validation
- `update_tournament()` - Update tournament with permission checks
- `delete_tournament()` - Soft delete tournament
- `transition_status()` - Handle tournament status transitions
- `validate_tournament_data()` - Business rule validation

**Dependencies**: Module 2.1

### GameConfigService (`game_config_service.py`)
Manages game-specific configurations (allowed formats, team sizes, match settings).

**Key Methods**:
- `get_config(game_id)` - Retrieve game_config JSONB or default schema
- `create_or_update_config(game_id, config_data, user)` - Staff-only deep merge updates
- `validate_tournament_against_config(game_id, tournament_data)` - Enforce game rules
- `get_config_schema(game_id)` - Return JSON Schema (draft-07) for API docs
- `_deep_merge(base, updates)` - Recursive dict merging helper
- `_validate_config(config)` - Structure validation

**Storage**: Uses `Game.game_config` JSONB field (PostgreSQL)

**Permissions**: Staff-only for updates, public read

**Dependencies**: Module 2.2

### CustomFieldService (`custom_field_service.py`)
Manages tournament-specific custom fields with dynamic typing and validation.

**Supported Field Types** (7):
- `text` - String fields with min/max length, regex validation
- `number` - Numeric fields with min/max value constraints
- `dropdown` - Single-select fields with predefined options
- `url` - URL fields with format validation
- `toggle` - Boolean fields
- `date` - Date fields with ISO-8601 format
- `media` - File upload fields with extension validation

**Key Methods**:
- `create_field(tournament_id, user, field_data)` - Create custom field (organizer/staff only)
- `update_field(field_id, user, update_data)` - Update field configuration
- `delete_field(field_id, user)` - Delete custom field
- `validate_field_value(field, value)` - Type-specific validation
- `_validate_field_config(field_type, field_config)` - Validate field configuration

**Storage**: Uses `CustomField.field_config` and `field_value` JSONB fields

**Permissions**: Organizer or staff for modifications

**Dependencies**: Module 2.2

### TemplateService (`template_service.py`)
Manages tournament template creation, storage, and application (deep merge pattern).

**Key Methods**:
- `create_template(user, name, description, template_config, game_id, visibility)` - Create template with permission checks
- `update_template(template_id, user, update_data)` - Update template (owner/staff only)
- `get_template(template_id, user)` - Retrieve template with visibility checks
- `list_templates(user, game_id, visibility, is_active, created_by_id, organization_id)` - List templates with filtering and permission rules
- `apply_template(template_id, user, tournament_payload)` - Deep merge template config + tournament payload

**Visibility Levels**:
- `PRIVATE` - Only creator can view/use
- `ORG` - Organization members can view/use (simplified to creator-only)
- `GLOBAL` - Everyone can view/use (staff-only creation)

**Storage**: Uses `TournamentTemplate.template_config` JSONB field

**Permissions**: 
- Create: Authenticated (GLOBAL requires staff)
- Update/Delete: Owner or staff
- Apply: Authenticated + visibility rules

**Deep Merge Behavior**: 
- `apply_template()` returns merged config only (does NOT create tournament)
- Template config provides defaults, tournament_payload overrides
- Nested dictionaries merged recursively
- Updates usage tracking (usage_count, last_used_at)

**Dependencies**: Module 2.3 (Optional Backend Feature)

**Note**: This is an optional backend feature designed for future tournament config presets. No UI required.

## Design Patterns

### Service Layer Pattern (ADR-001)
All business logic resides in services, not models or views. This ensures:
- Testability (pure functions with clear inputs/outputs)
- Reusability (services can be called from API, admin, management commands)
- Maintainability (single source of truth for business rules)

### JSONB for Flexibility (ADR-004)
Game configurations and custom field schemas use PostgreSQL JSONB fields for:
- Schema flexibility (game-specific rules without schema migrations)
- Query performance (JSONB indexing, JSON operators)
- Type safety (validation at service layer)

### Permission Enforcement
All write operations check permissions:
- **Staff-only**: GameConfigService (game configs are system-wide)
- **Organizer or staff**: CustomFieldService (tournament-specific)
- **User-specific**: TournamentService (based on ownership and role)

## Testing

All services have comprehensive unit tests:
- `tests/test_tournament_service.py` - TournamentService tests
- `tests/test_game_config_service.py` - 25 tests (get, create/update, validation, schema)
- `tests/test_custom_field_service.py` - 18 tests (CRUD, validation for 7 types, permissions)
- `tests/test_template_service.py` - 38 tests (create, update, get, list, apply deep merge)
- `tests/test_template_api.py` - 20 tests (API integration tests for template endpoints)

**Coverage**: ≥85% across all services

## Usage Examples

### GameConfigService

```python
from apps.tournaments.services.game_config_service import GameConfigService

# Get game configuration
config = GameConfigService.get_config(game_id=1)
# Returns: {"schema_version": "1.0", "allowed_formats": [...], "team_size_range": [1, 5], ...}

# Update game configuration (staff only)
updated_config = GameConfigService.create_or_update_config(
    game_id=1,
    config_data={"allowed_formats": ["single_elimination", "double_elimination"]},
    user=request.user
)
# Deep merges with existing config, validates format whitelist

# Validate tournament against game config
GameConfigService.validate_tournament_against_config(
    game_id=1,
    tournament_data={"format": "single_elimination", "team_size": 5}
)
# Raises ValidationError if format not allowed or team_size out of range
```

### CustomFieldService

```python
from apps.tournaments.services.custom_field_service import CustomFieldService

# Create custom field (organizer/staff only)
field = CustomFieldService.create_field(
    tournament_id=1,
    user=request.user,
    field_data={
        "field_name": "Discord Server",
        "field_type": "url",
        "is_required": True,
        "field_config": {"pattern": "^https://discord\\.gg/"}
    }
)
# Auto-generates field_key="discord_server", validates field_type

# Validate field value
CustomFieldService.validate_field_value(
    field=field,
    value="https://discord.gg/abc123"
)
# Type-specific validation (url format + regex pattern)

# Update field (partial updates)
CustomFieldService.update_field(
    field_id=field.id,
    user=request.user,
    update_data={"is_required": False}
)
```

### TemplateService

```python
from apps.tournaments.services.template_service import TemplateService

# Create template (authenticated user, GLOBAL requires staff)
template = TemplateService.create_template(
    user=request.user,
    name="5v5 Valorant Tournament",
    description="Standard format for 5v5 Valorant tournaments",
    template_config={
        "format": "single_elimination",
        "max_participants": 16,
        "team_size": 5,
        "entry_fee_amount": "500.00"
    },
    game_id=1,  # Optional - if specified, validates game exists
    visibility=TournamentTemplate.PRIVATE  # or ORG, GLOBAL (staff only)
)
# Auto-generates slug, validates permissions

# List templates with filtering
templates = TemplateService.list_templates(
    user=request.user,  # Optional - enforces visibility rules if provided
    game_id=1,  # Filter by game
    visibility=TournamentTemplate.GLOBAL,  # Filter by visibility
    is_active=True  # Only active templates
)
# Returns: List[TournamentTemplate]

# Apply template (deep merge pattern)
merged_config = TemplateService.apply_template(
    template_id=template.id,
    user=request.user,
    tournament_payload={
        "name": "Summer Championship 2025",
        "entry_fee_amount": "1000.00"  # Override template value
    }
)
# Returns: {"format": "single_elimination", "max_participants": 16, "team_size": 5, 
#           "entry_fee_amount": "1000.00", "name": "Summer Championship 2025"}
# Note: Does NOT create tournament - just returns merged config
# Usage tracking: Increments template.usage_count, updates template.last_used_at

# Update template (owner or staff only)
updated_template = TemplateService.update_template(
    template_id=template.id,
    user=request.user,
    update_data={"max_participants": 32}  # Partial update
)
# Merges update_data with existing template_config

# Get template (with visibility checks)
template = TemplateService.get_template(
    template_id=1,
    user=request.user  # Enforces visibility rules
)
# Raises ValidationError if not found or PermissionDenied if visibility check fails
```

## Related Documentation

- [Module 2.1 Completion Status](../../../Documents/ExecutionPlan/MODULE_2.1_COMPLETION_STATUS.md)
- [Module 2.2 Completion Status](../../../Documents/ExecutionPlan/MODULE_2.2_COMPLETION_STATUS.md)
- [Module 2.3 Completion Status](../../../Documents/ExecutionPlan/MODULE_2.3_COMPLETION_STATUS.md) - Tournament Templates (Optional Feature)
- [ADR-001: Service Layer Architecture](../../../Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-001)
- [ADR-004: PostgreSQL JSONB](../../../Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-004)
- [BACKEND_ONLY_BACKLOG.md](../../../Documents/ExecutionPlan/BACKEND_ONLY_BACKLOG.md)
