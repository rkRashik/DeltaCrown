# Tournament REST APIs

This directory contains Django REST Framework (DRF) API implementations for tournament management.

## API Endpoints

### Tournament API

**Base URL**: `/api/tournaments/`

**ViewSet**: `TournamentViewSet` (`tournament_views.py`)

**Endpoints**:
- `GET /api/tournaments/` - List tournaments (public, filterable)
- `POST /api/tournaments/` - Create tournament (authenticated)
- `GET /api/tournaments/{id}/` - Retrieve tournament (public)
- `PATCH /api/tournaments/{id}/` - Update tournament (organizer/staff)
- `DELETE /api/tournaments/{id}/` - Delete tournament (organizer/staff)

**Serializers**: `tournament_serializers.py`
- `TournamentListSerializer` - Lightweight list view
- `TournamentDetailSerializer` - Full detail view with nested data
- `TournamentCreateSerializer` - Create with validation
- `TournamentUpdateSerializer` - Partial updates

**Permissions**: Authenticated users can create, organizer/staff can modify

**Dependencies**: Module 2.1

---

### GameConfig API

**Base URL**: `/api/games/{game_id}/config/`

**ViewSet**: `GameConfigViewSet` (`game_config_views.py`)

**Endpoints**:
- `GET /api/games/{id}/config/` - Retrieve game configuration (public)
- `PATCH /api/games/{id}/config/` - Update game configuration (staff only)
- `GET /api/games/{id}/config-schema/` - Get JSON Schema (public)

**Serializers**: `game_config_serializers.py`
- `GameConfigSerializer` - Read-only config representation
- `GameConfigUpdateSerializer` - Write-only updates with validation
- `GameConfigSchemaSerializer` - JSON Schema (draft-07) output

**Permissions**: Public read, staff-only write

**Example Response** (GET /api/games/1/config/):
```json
{
  "schema_version": "1.0",
  "allowed_formats": ["single_elimination", "double_elimination", "round_robin"],
  "team_size_range": [1, 5],
  "custom_field_schemas": [],
  "match_settings": {
    "default_best_of": 1,
    "available_maps": ["Summoner's Rift", "Howling Abyss"]
  }
}
```

**Example Request** (PATCH /api/games/1/config/):
```json
{
  "allowed_formats": ["single_elimination"],
  "team_size_range": [5, 5]
}
```
*Deep merges with existing config*

**Dependencies**: Module 2.2

---

### CustomField API

**Base URL**: `/api/tournaments/{tournament_id}/custom-fields/`

**ViewSet**: `CustomFieldViewSet` (`custom_field_views.py`)

**Endpoints**:
- `POST /api/tournaments/{tournament_id}/custom-fields/` - Create field (organizer/staff)
- `GET /api/tournaments/{tournament_id}/custom-fields/` - List fields (public)
- `GET /api/tournaments/{tournament_id}/custom-fields/{id}/` - Retrieve field (public)
- `PATCH /api/tournaments/{tournament_id}/custom-fields/{id}/` - Update field (organizer/staff)
- `DELETE /api/tournaments/{tournament_id}/custom-fields/{id}/` - Delete field (organizer/staff)

**Serializers**: `custom_field_serializers.py`
- `CustomFieldListSerializer` - Lightweight list view
- `CustomFieldDetailSerializer` - Full detail view with field_config
- `CustomFieldCreateSerializer` - Create with type validation
- `CustomFieldUpdateSerializer` - Partial updates

**Permissions**: Public read, organizer/staff write

**Nested Routing**: Uses `drf-nested-routers` for clean URL structure

**Example Request** (POST /api/tournaments/1/custom-fields/):
```json
{
  "field_name": "Discord Server",
  "field_type": "url",
  "is_required": true,
  "field_config": {
    "pattern": "^https://discord\\.gg/"
  },
  "help_text": "Your team's Discord server invite link"
}
```

**Example Response**:
```json
{
  "id": 1,
  "field_name": "Discord Server",
  "field_key": "discord_server",
  "field_type": "url",
  "is_required": true,
  "field_config": {
    "pattern": "^https://discord\\.gg/"
  },
  "help_text": "Your team's Discord server invite link",
  "order": 1,
  "created_at": "2025-01-15T10:00:00Z"
}
```

**Supported Field Types** (7):
- `text` - String fields (min/max length, regex)
- `number` - Numeric fields (min/max value)
- `dropdown` - Single-select (options list)
- `url` - URL fields (format validation)
- `toggle` - Boolean fields
- `date` - Date fields (ISO-8601)
- `media` - File upload fields (extension validation)

**Dependencies**: Module 2.2

---

## URL Configuration

**File**: `urls.py`

**Router Setup**:
```python
from rest_framework.routers import DefaultRouter
from drf_nested_routers import routers as nested_routers

router = DefaultRouter()
router.register(r'tournaments', TournamentViewSet, basename='tournament')
router.register(r'game-config', GameConfigViewSet, basename='game-config')

tournament_router = nested_routers.NestedDefaultRouter(
    router, r'tournaments', lookup='tournament'
)
tournament_router.register(
    r'custom-fields', CustomFieldViewSet, basename='tournament-custom-fields'
)

urlpatterns = router.urls + tournament_router.urls
```

---

## Authentication & Permissions

### Permission Classes

**Custom Permission**: `IsOwnerOrOrganizer` (tournament-specific)
- Read: Public
- Write: Tournament organizer or staff

**Custom Permission**: `IsOrganizerOrReadOnly` (tournament-specific)
- Read: Public
- Write: Tournament organizer or staff

**DRF Built-in**: `IsAuthenticatedOrReadOnly`
- Read: Public
- Write: Authenticated users

**DRF Built-in**: `IsAdminUser`
- Read/Write: Staff only (used for GameConfig updates)

### Permission Enforcement

All write operations check:
1. User authentication (authenticated users only)
2. Resource ownership (organizer) or staff status
3. Business rules (e.g., CustomField modifications only in DRAFT status)

---

## Testing

API integration tests:
- `tests/test_tournament_api.py` - TournamentViewSet tests
- `tests/test_game_config_custom_field_api.py` - 20 tests
  - GameConfig API: 8 tests (retrieve, update, schema, permissions)
  - CustomField API: 12 tests (CRUD, permissions, validation)

**Coverage**: ≥80% across all ViewSets

---

## Error Handling

### Standard HTTP Status Codes

- `200 OK` - Successful GET/PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Validation errors
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

### Validation Error Response

```json
{
  "field_name": ["This field is required."],
  "field_type": ["Invalid field type. Valid types: text, number, dropdown, url, toggle, date, media."]
}
```

---

## Related Documentation

- [Module 2.1 Completion Status](../../../Documents/ExecutionPlan/MODULE_2.1_COMPLETION_STATUS.md)
- [Module 2.2 Completion Status](../../../Documents/ExecutionPlan/MODULE_2.2_COMPLETION_STATUS.md)
- [Service Layer README](../services/README.md)
- [ADR-002: API Design Patterns](../../../Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-002)
- [BACKEND_ONLY_BACKLOG.md](../../../Documents/ExecutionPlan/BACKEND_ONLY_BACKLOG.md)
