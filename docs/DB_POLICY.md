# Database Environment Policy

## Overview

DeltaCrown enforces a **strict multi-environment database policy** to prevent accidental production migrations and data loss. The system automatically selects the correct database based on the command context.

## Three Environments

| Environment | Variable | Purpose | Migration Guard |
|------------|----------|---------|-----------------|
| **PROD** | `DATABASE_URL` | Production Neon database | ✅ Blocked by default |
| **DEV** | `DATABASE_URL_DEV` | Development Neon branch or local | ✅ Safe to migrate |
| **TEST** | `DATABASE_URL_TEST` | Local Postgres for pytest | ✅ Safe to migrate |

## Automatic Database Selection

The system automatically chooses the correct database based on context:

### Test Context → DATABASE_URL_TEST
```bash
pytest                           # Uses TEST database
python manage.py test            # Uses TEST database
```

### Development Commands → DATABASE_URL_DEV (if set)
```bash
# These automatically use DATABASE_URL_DEV when it's set:
python manage.py migrate         # Uses DEV database
python manage.py runserver       # Uses DEV database
python manage.py shell           # Uses DEV database
python manage.py dbshell         # Uses DEV database
python manage.py createsuperuser # Uses DEV database
```

**No extra flags needed!** Just set `DATABASE_URL_DEV` in your environment once:
```bash
export DATABASE_URL_DEV=postgresql://localhost:5432/deltacrown_dev
```

### Production Context → DATABASE_URL (Guarded)
```bash
# Requires explicit override
ALLOW_PROD_MIGRATE=1 python manage.py migrate
```

All other commands (that aren't dev-related) use the production database by default.

## Environment Variables

### Required Variables

```bash
# Production (Neon cloud - deltacrown database)
DATABASE_URL=postgresql://user:pass@host.neon.tech/deltacrown

# Development (Neon branch or local Postgres)
DATABASE_URL_DEV=postgresql://user:pass@dev-branch.neon.tech/deltacrown

# Test (Local Postgres)
DATABASE_URL_TEST=postgresql://localhost:5432/deltacrown_test
```

### Optional Override Variables

```bash
# Force dev database for any command (rarely needed)
USE_DEV_DB=1

# Allow production migrations (DANGEROUS - use with extreme caution)
ALLOW_PROD_MIGRATE=1
```

**Normal usage:** You typically only need to set `DATABASE_URL_DEV` once in your shell profile or `.env` file. The system handles the rest automatically.

## Migration Guard

The migration guard is implemented in `apps/core/management/commands/migrate.py` as a custom command wrapper.

### Guard Logic

1. Check `DB_ENVIRONMENT` from settings
2. If `DB_ENVIRONMENT == 'PROD'`:
   - Check for `ALLOW_PROD_MIGRATE=1`
   - If not set: **BLOCK** and exit with error (printed once)
   - If set: **ALLOW** migration to proceed with warning

### Example: Blocked Migration

```bash
$ python manage.py migrate

================================================================================
MIGRATION BLOCKED: Connected to PRODUCTION database
================================================================================
You are attempting to run migrations on the production database.
This is blocked by default to prevent accidental data loss.

Database: deltacrown
Host: ep-some-hash.us-east-2.aws.neon.tech

If you REALLY need to migrate production:
  1. Verify you have backups
  2. Set environment variable: ALLOW_PROD_MIGRATE=1
  3. Run migrate again

For development work:
  Set DATABASE_URL_DEV in your environment and run migrate normally.
  Example: export DATABASE_URL_DEV=postgresql://localhost:5432/deltacrown_dev

See docs/DB_POLICY.md for details.
================================================================================
```

**Key improvement:** The guard executes only once at command startup, not in AppConfig.ready(), preventing duplicate messages.

## Safe Commands Reference

### Development (Safe on DEV database)

```bash
# Set DATABASE_URL_DEV once (in .bashrc, .zshrc, or .env)
export DATABASE_URL_DEV=postgresql://localhost:5432/deltacrown_dev

# Then use commands normally - they automatically use DEV:
python manage.py migrate
python manage.py makemigrations
python manage.py showmigrations
python manage.py runserver
python manage.py createsuperuser
python manage.py shell
python manage.py dbshell
python manage.py print_db_identity
python manage.py check
```

**No inline variables needed!** Once `DATABASE_URL_DEV` is set, all dev commands use it automatically.

### Testing (Safe on TEST database)

```bash
# Pytest
pytest
pytest tests/unit/
pytest tests/integration/

# Django test runner
python manage.py test
python manage.py test apps.teams
```

### Production (Requires Override)

```bash
# Verify connection (read-only)
python manage.py print_db_identity

# DANGEROUS: Production migration (requires explicit override)
ALLOW_PROD_MIGRATE=1 python manage.py migrate

# DANGEROUS: Production data operations
# Use Django admin or carefully tested management commands
```

## Verifying Database Connection

Use the `print_db_identity` command to see which database you're connected to:

```bash
$ python manage.py print_db_identity

======================================================================
DATABASE CONNECTION IDENTITY [DEV]
======================================================================

[From DATABASE_URL_DEV]
  Engine:   postgresql
  Host:     dev-branch.neon.tech
  Port:     5432
  Database: deltacrown
  User:     username

[Django DATABASES['default']]
  Engine:   django.db.backends.postgresql
  Name:     deltacrown
  Host:     dev-branch.neon.tech
  Port:     5432
  User:     username

[Live Database Connection]
  current_database():    deltacrown
  current_user:          username
  inet_server_addr():    10.0.1.123
  inet_server_port():    5432
  current_schema():      public
  search_path:           "$user", public
  version:               PostgreSQL 16.0

======================================================================
✓ DEV DATABASE: deltacrown
  (Neon development branch)
======================================================================
```

## Setting Up Environments

### 1. Production (Neon Cloud)

```bash
# Add to .env.production
DATABASE_URL=postgresql://username:password@ep-hash.us-east-2.aws.neon.tech/deltacrown
```

### 2. Development (Neon Branch)

Create a Neon branch for development:

```bash
# In Neon console: Create branch "dev" from main
# Add to .env.dev
DATABASE_URL_DEV=postgresql://username:password@ep-hash-dev.neon.tech/deltacrown
```

Or use local Postgres:

```bash
# Create local database
createdb deltacrown_dev

# Add to .env.dev
DATABASE_URL_DEV=postgresql://localhost:5432/deltacrown_dev
```

### 3. Test (Local Postgres)

```bash
# Create test database
createdb deltacrown_test

# Add to .env.test or pytest.ini
DATABASE_URL_TEST=postgresql://localhost:5432/deltacrown_test
```

## Pytest Configuration

Ensure pytest always uses the TEST database:

**Option 1: pytest.ini**
```ini
[pytest]
env =
    DATABASE_URL_TEST=postgresql://localhost:5432/deltacrown_test
```

**Option 2: conftest.py**
```python
import os
import pytest

@pytest.fixture(scope='session', autouse=True)
def set_test_database():
    """Ensure test database is used for all tests."""
    os.environ['DATABASE_URL_TEST'] = 'postgresql://localhost:5432/deltacrown_test'
```

## Troubleshooting

### "MIGRATION BLOCKED" when I want to use DEV

**Solution:** Set `DATABASE_URL_DEV` in your environment:

```bash
export DATABASE_URL_DEV=postgresql://localhost:5432/deltacrown_dev
python manage.py migrate  # Now automatically uses DEV
```

Add to your `.bashrc` or `.zshrc` for permanent setup.

### Pytest using wrong database

**Solution:** Verify `DATABASE_URL_TEST` is set:

```bash
echo $DATABASE_URL_TEST
# If not set:
export DATABASE_URL_TEST=postgresql://localhost:5432/deltacrown_test
```

### Need to migrate production (rare)

**Solution:** Use explicit override:

```bash
# 1. Verify backups exist
# 2. Set override flag
export ALLOW_PROD_MIGRATE=1

# 3. Run migration
python manage.py migrate

# 4. Unset flag immediately
unset ALLOW_PROD_MIGRATE
```

### Unknown database environment

**Solution:** Check which database is selected:

```bash
python manage.py print_db_identity
```

Look for `[PROD]`, `[DEV]`, or `[TEST]` label in the output.

## Implementation Details

### Smart Selection Logic (settings.py)

```python
def get_database_environment():
    """Determine which database based on context."""
    import sys
    
    # Test context
    if 'test' in sys.argv or 'pytest' in sys.argv[0]:
        return os.getenv('DATABASE_URL_TEST'), 'TEST'
    
    # Dev commands - automatically use DEV if DATABASE_URL_DEV is set
    is_dev_command = (
        'migrate' in sys.argv or 
        'runserver' in sys.argv or
        'shell' in sys.argv or
        'dbshell' in sys.argv or
        'createsuperuser' in sys.argv
    )
    
    db_url_dev = os.getenv('DATABASE_URL_DEV')
    if db_url_dev and (is_dev_command or os.getenv('USE_DEV_DB') == '1'):
        return db_url_dev, 'DEV'
    
    # Default to production
    return os.getenv('DATABASE_URL'), 'PROD'
```

### Migration Guard (apps/core/management/commands/migrate.py)

```python
class Command(MigrateCommand):
    """Wrap Django's migrate with production guard."""
    
    def handle(self, *args, **options):
        db_environment = getattr(settings, 'DB_ENVIRONMENT', 'UNKNOWN')
        
        if db_environment == 'PROD':
            if os.getenv('ALLOW_PROD_MIGRATE') != '1':
                # Print error once and exit
                sys.exit(1)
        
        # Call parent migrate
        return super().handle(*args, **options)
```

**Key design:** The guard is in the management command, not AppConfig.ready(), ensuring it executes exactly once.

## Best Practices

1. **Set DATABASE_URL_DEV once** in your shell profile (`.bashrc`, `.zshrc`) or project `.env` file
2. **Use commands normally** - no inline variables needed for dev work
3. **Never run migrations on production** without explicit override
4. **Always verify database** with `print_db_identity` before risky operations
5. **Use Neon branches** for development to match production schema
6. **Keep test database local** for fast test execution
7. **Unset ALLOW_PROD_MIGRATE** immediately after production migrations
8. **Document any production migrations** in a deployment log

### Recommended Setup

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# DeltaCrown database configuration
export DATABASE_URL_DEV=postgresql://localhost:5432/deltacrown_dev
export DATABASE_URL_TEST=postgresql://localhost:5432/deltacrown_test
```

Then reload your shell or run `source ~/.bashrc`. After this, all development commands work normally without extra flags.

## See Also

- [DELTACROWN_PLATFORM_GUIDE.md](../DELTACROWN_PLATFORM_GUIDE.md) - Platform overview
- [README_TECHNICAL.md](../README_TECHNICAL.md) - Technical documentation
- [apps/core/apps.py](../apps/core/apps.py) - Migration guard implementation
- [deltacrown/settings.py](../deltacrown/settings.py) - Database selection logic
