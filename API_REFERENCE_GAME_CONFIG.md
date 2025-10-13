# Game Configuration API Reference

Quick reference guide for the dynamic tournament registration API endpoints.

## Base URL
`/tournaments/api/`

## Endpoints

### 1. Get All Games
**Get list of all available games**

- **URL**: `/games/`
- **Method**: `GET`
- **Auth**: Not required
- **Cache**: 1 hour

**Response**:
```json
{
  "success": true,
  "count": 8,
  "games": [
    {
      "game_code": "valorant",
      "display_name": "VALORANT",
      "icon": "valorant.png",
      "team_size": 5,
      "sub_count": 2,
      "total_roster_size": 7,
      "roster_description": "5 starters + 2 subs",
      "description": "Riot Games tactical shooter",
      "is_solo": false,
      "is_team": true
    }
  ]
}
```

---

### 2. Get Game Configuration
**Get complete configuration for a specific game**

- **URL**: `/games/<game_code>/config/`
- **Method**: `GET`
- **Auth**: Not required
- **Cache**: 1 hour

**Parameters**:
- `game_code` (path): Game identifier (valorant, cs2, dota2, mlbb, pubg, freefire, efootball, fc26)

**Response**:
```json
{
  "success": true,
  "game_code": "valorant",
  "config": {
    "game": {
      "game_code": "valorant",
      "display_name": "VALORANT",
      "icon": "valorant.png",
      "team_size": 5,
      "sub_count": 2,
      "total_roster_size": 7,
      "roster_description": "5 starters + 2 subs",
      "is_solo": false,
      "is_team": true,
      "description": "Riot Games tactical shooter"
    },
    "fields": [
      {
        "field_name": "riot_id",
        "field_label": "Riot ID",
        "field_type": "TEXT",
        "is_required": true,
        "validation_regex": "^.+#[a-zA-Z0-9]{3,5}$",
        "placeholder": "Username#TAG",
        "help_text": "Your Riot Games account ID (e.g., Player#1234)",
        "display_order": 1,
        "choices": null,
        "show_condition": null,
        "icon": ""
      },
      {
        "field_name": "discord_id",
        "field_label": "Discord ID",
        "field_type": "TEXT",
        "is_required": false,
        "validation_regex": "^.+#\\d{4}$",
        "placeholder": "username#1234",
        "help_text": "Your Discord username for communication",
        "display_order": 2,
        "choices": null,
        "show_condition": null,
        "icon": ""
      }
    ],
    "roles": [
      {
        "role_code": "duelist",
        "role_name": "Duelist",
        "role_abbreviation": "DUE",
        "is_unique": false,
        "is_required": false,
        "max_per_team": 2,
        "description": "Entry fragger and aggressive player",
        "display_order": 1,
        "icon": ""
      },
      {
        "role_code": "controller",
        "role_name": "Controller",
        "role_abbreviation": "CTL",
        "is_unique": false,
        "is_required": false,
        "max_per_team": 2,
        "description": "Smoke specialist and area denial",
        "display_order": 2,
        "icon": ""
      }
    ]
  }
}
```

**Error Response** (Game not found):
```json
{
  "success": false,
  "error": "Game 'invalid_game' not found or is inactive",
  "game_code": "invalid_game"
}
```

---

### 3. Validate Field
**Validate a single field value in real-time**

- **URL**: `/games/<game_code>/validate/`
- **Method**: `POST`
- **Auth**: Not required
- **Content-Type**: `application/json`

**Parameters**:
- `game_code` (path): Game identifier

**Request Body**:
```json
{
  "field_name": "riot_id",
  "value": "Player#1234"
}
```

**Response** (Valid):
```json
{
  "success": true,
  "is_valid": true,
  "error": null,
  "field_name": "riot_id"
}
```

**Response** (Invalid):
```json
{
  "success": true,
  "is_valid": false,
  "error": "Riot ID must be in format: Username#TAG (e.g., Player#1234)",
  "field_name": "riot_id"
}
```

**Error Response** (Missing data):
```json
{
  "success": false,
  "error": "field_name and value are required"
}
```

---

### 4. Validate Team Roles
**Validate team roster role assignments**

- **URL**: `/games/<game_code>/validate-roles/`
- **Method**: `POST`
- **Auth**: Not required
- **Content-Type**: `application/json`

**Parameters**:
- `game_code` (path): Game identifier

**Request Body**:
```json
{
  "roles": ["duelist", "duelist", "controller", "sentinel", "igl"]
}
```

**Response** (Valid):
```json
{
  "success": true,
  "is_valid": true,
  "errors": [],
  "game_code": "valorant"
}
```

**Response** (Invalid):
```json
{
  "success": true,
  "is_valid": false,
  "errors": [
    "Role 'duelist' can appear at most 2 times (found 3)"
  ],
  "game_code": "valorant"
}
```

**Error Response** (Missing data):
```json
{
  "success": false,
  "error": "roles array is required"
}
```

---

### 5. Registration Context
**Get complete registration context including game config and auto-fill data**

- **URL**: `/<tournament_slug>/register/context/`
- **Method**: `GET`
- **Auth**: **Required** (user must be logged in)

**Parameters**:
- `tournament_slug` (path): Tournament slug

**Response**:
```json
{
  "success": true,
  "context": {
    "eligibility": {
      "is_eligible": true,
      "blocked_reasons": [],
      "warnings": []
    },
    "registration_button": {
      "text": "Register Now",
      "enabled": true,
      "css_class": "btn-primary"
    },
    "user_team": {
      "team_id": 123,
      "team_name": "Pro Esports",
      "is_captain": true
    }
  },
  "game_config": {
    "game": { /* Game details */ },
    "fields": [ /* Field configurations */ ],
    "roles": [ /* Role configurations */ ]
  },
  "profile_data": {
    "riot_id": "SavedPlayer#1234",
    "discord_id": "player#1234",
    "phone": "01712345678"
  },
  "team_data": {
    "team_name": "Pro Esports",
    "members": [
      {
        "user_id": 1,
        "username": "captain",
        "role": "igl"
      }
    ]
  }
}
```

---

## Field Types

| Type | Description | Example |
|------|-------------|---------|
| `TEXT` | Single-line text input | "Player#1234" |
| `TEXTAREA` | Multi-line text input | "Long description..." |
| `SELECT` | Dropdown selection | "option1" |
| `NUMBER` | Numeric input | "12345" |
| `PHONE` | Phone number | "01712345678" |
| `EMAIL` | Email address | "player@example.com" |

---

## Game Codes

| Code | Game Name |
|------|-----------|
| `valorant` | VALORANT |
| `cs2` | Counter-Strike 2 |
| `dota2` | Dota 2 |
| `mlbb` | Mobile Legends: Bang Bang |
| `pubg` | PUBG: Battlegrounds |
| `freefire` | Free Fire |
| `efootball` | eFootball |
| `fc26` | FC 26 (EA Sports) |

---

## Validation Rules

### VALORANT
- **Riot ID**: Username#TAG format, TAG must be 3-5 alphanumeric characters
- **Discord ID**: Optional, username#1234 or @username format

### CS2 / Dota 2
- **Steam ID**: 17-digit number starting with 7656119
- **Dota Friend ID**: 9-10 digit number (Dota 2 only)

### Mobile Legends
- **MLBB User ID**: 6-12 digit number
- **MLBB Server ID**: Server identifier

### PUBG
- **PUBG ID**: 3-50 characters, letters/numbers/underscores only

### Free Fire
- **Free Fire UID**: 9-12 digit number

### eFootball
- **eFootball User ID**: 8-12 digit number

### FC 26
- **EA/Origin ID**: 3-50 characters, letters/numbers/underscores/hyphens

---

## Common Fields (All Games)
- **Discord ID**: Optional communication field
- **Phone Number**: Bangladesh format (01XXXXXXXXX)

---

## Error Codes

| Status | Meaning |
|--------|---------|
| 200 | Success (check `success` and `is_valid` fields) |
| 400 | Bad request (missing required fields) |
| 404 | Game not found |
| 405 | Method not allowed (wrong HTTP method) |

---

## Caching

All GET endpoints are cached for **1 hour**:
- `/games/` - All games list
- `/games/<game_code>/config/` - Game configuration

POST endpoints are not cached (validation is stateless).

To clear cache programmatically:
```python
from apps.tournaments.services import GameConfigService

# Clear specific game
GameConfigService.clear_cache('valorant')

# Clear all games
GameConfigService.clear_cache()
```

---

## Frontend Integration Examples

### React/JavaScript

```javascript
// Fetch game config
const fetchGameConfig = async (gameCode) => {
  const response = await fetch(`/tournaments/api/games/${gameCode}/config/`);
  return await response.json();
};

// Validate field
const validateField = async (gameCode, fieldName, value) => {
  const response = await fetch(`/tournaments/api/games/${gameCode}/validate/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field_name: fieldName, value })
  });
  return await response.json();
};

// Get registration context
const getRegistrationContext = async (slug) => {
  const response = await fetch(`/tournaments/api/${slug}/register/context/`);
  return await response.json();
};
```

### jQuery

```javascript
// Real-time field validation
$('#riot-id-input').on('blur', function() {
  const value = $(this).val();
  
  $.post('/tournaments/api/games/valorant/validate/', 
    JSON.stringify({
      field_name: 'riot_id',
      value: value
    }),
    function(data) {
      if (!data.is_valid) {
        showError('#riot-id-input', data.error);
      } else {
        clearError('#riot-id-input');
      }
    },
    'json'
  );
});
```

---

## Testing

Run test suite:
```bash
# All Phase 2 tests
python -m pytest tests/test_game_validators.py tests/test_game_config_api.py -v

# Validator tests only
python -m pytest tests/test_game_validators.py -v

# API tests only
python -m pytest tests/test_game_config_api.py -v
```

**Test Coverage**: 47 tests, 100% passing ✅

---

## Support

For issues or questions:
1. Check test files for usage examples
2. Review `PHASE2_COMPLETION_SUMMARY.md`
3. See service layer docs: `apps/tournaments/services/game_config_service.py`
4. See validator docs: `apps/tournaments/validators/game_validators.py`
