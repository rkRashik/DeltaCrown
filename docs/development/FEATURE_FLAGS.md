# Feature Flags

This document describes environment-based feature flags used in the DeltaCrown platform.

## Competition App Feature Flag

### `COMPETITION_APP_ENABLED`

**Type**: Boolean (string "0" or "1")  
**Default**: `"0"` (disabled)  
**Location**: Environment variable or `.env` file  
**Added**: Phase 3A-C0 (vNext Competition System)

**Purpose**: Controls whether the `apps.competition` app is loaded into Django's `INSTALLED_APPS`. This flag provides a safety gate for production environments where the competition database schema may not yet be applied.

**Usage**:

```bash
# In .env file (not tracked in git)
COMPETITION_APP_ENABLED=1  # Enable competition app
COMPETITION_APP_ENABLED=0  # Disable competition app (default)
```

**Implementation**:

```python
# deltacrown/settings.py
COMPETITION_APP_ENABLED = os.getenv("COMPETITION_APP_ENABLED", "0") == "1"

# Conditional app registration
if COMPETITION_APP_ENABLED:
    INSTALLED_APPS.append("apps.competition")
```

**When to Enable**:

- ✅ **Local development**: Set to `1` after running migrations
- ✅ **Staging**: Set to `1` after applying competition migrations
- ✅ **Production**: Set to `1` ONLY after:
  1. Database migrations applied successfully
  2. Game ranking configs seeded (11 games)
  3. Initial ranking snapshots computed (if needed)
  4. Smoke tests completed

**When to Disable**:

- ❌ Fresh production deployments where schema doesn't exist
- ❌ Environments without competition tables
- ❌ During migration rollbacks or debugging

**Safety Guarantees**:

- When disabled (`0`), the competition app is NOT loaded
- No competition models are registered with Django
- No competition URLs are accessible
- No competition migrations are checked
- System check passes cleanly in both enabled and disabled states

**Verification**:

```bash
# Verify flag status
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Enabled' if os.getenv('COMPETITION_APP_ENABLED', '0') == '1' else 'Disabled')"

# Verify system check passes
python manage.py check  # Must pass in both states
```

**Related Documentation**:

- See `VNEXT_PHASE_3A_C_IMPLEMENTATION_REPORT.md` for Phase 3A-C0 implementation details
- See `VNEXT_PHASE_3A_AB_IMPLEMENTATION_REPORT.md` for competition app architecture

---

## Adding New Feature Flags

When adding new feature flags, follow this pattern:

1. **Environment Variable**: Use `FEATURE_NAME_ENABLED` naming convention
2. **Default**: Always default to safe/disabled state (`"0"`)
3. **Documentation**: Add entry to this file with usage instructions
4. **Validation**: Ensure `python manage.py check` passes in both states
5. **Testing**: Write tests that verify both enabled and disabled behavior
