# Organizations Constants

This module contains canonical constants for the organizations app.

## Structure

```
constants/
├── __init__.py      # Public exports and legacy aliases
└── regions.py       # Country/region constants
```

## What Belongs Here

✅ **DO include:**
- Country/region lists
- Fixed enumerations (org types, roles, statuses)
- Canonical choice tuples for model fields
- API response constants

❌ **DO NOT include:**
- Business logic
- Database queries
- Computed values
- Mutable configuration

## Import Guidelines

### Preferred (Explicit)
```python
# Import directly from submodule for clarity
from apps.organizations.constants.regions import COUNTRIES, get_country_name
```

### Supported (Convenience)
```python
# Import from package root (re-exported in __init__.py)
from apps.organizations.constants import COUNTRIES, TEAM_COUNTRIES
```

### Forbidden
```python
# ❌ NEVER use wildcard imports
from apps.organizations.constants import *

# ❌ NEVER bypass the package structure
from apps.organizations.constants.regions import _internal_helper
```

## Legacy Aliases

- `TEAM_COUNTRIES`: Legacy alias for `COUNTRIES` (dict format vs tuple format)
  - **Deprecated:** Will be removed in v2
  - **Migration Path:** Use `COUNTRIES` directly and convert format if needed

## Adding New Constants

1. **Choose the right submodule:**
   - `regions.py` → Country/location data
   - Create new file if needed (e.g., `roles.py`, `statuses.py`)

2. **Define with clear naming:**
   ```python
   # Good: Clear, scoped, uppercase
   ORG_TYPES = [...]
   DEFAULT_ORG_TYPE = 'club'
   
   # Bad: Vague or not scoped
   TYPES = [...]
   default = 'club'
   ```

3. **Export in `__init__.py`:**
   ```python
   from .new_module import NEW_CONSTANT
   
   __all__ = [
       'NEW_CONSTANT',
       # ... existing exports
   ]
   ```

4. **Add tests** (see `tests/test_constants.py`)

## Testing

Run constant tests:
```bash
pytest apps/organizations/tests/test_constants.py -v
```

Tests verify:
- All `__all__` exports are importable
- No missing or broken imports
- No duplicate constant definitions
- Format consistency
