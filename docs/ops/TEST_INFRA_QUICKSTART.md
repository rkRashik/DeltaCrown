# Test Infrastructure Quickstart

**Updated**: 2026-02-04  
**Status**: Active

---

## Quick Start (2 Commands)

### Option A: Docker Test DB (Recommended)

```bash
# 1. Start test database
docker compose -f ops/docker-compose.test.yml up -d

# 2. Run tests
pytest
```

**Connection**: `postgresql://dcadmin:dcpass123@localhost:54329/deltacrown_test`

---

### Option B: Local PostgreSQL

```bash
# 1. Set DATABASE_URL_TEST
$env:DATABASE_URL_TEST="postgresql://postgres:yourpass@localhost:5432/deltacrown_test"

# 2. Run tests
pytest
```

---

## Default Behavior (Phase 15)

**If DATABASE_URL_TEST not set**:
- ✅ Automatically defaults to docker DB (port 54329)
- ✅ Shows clear message if docker not running
- ✅ No manual env var setup needed

**Previous behavior** (before Phase 15):
- ❌ Failed with "DATABASE_URL_TEST required"
- ❌ Required manual env var setup every time

---

## Docker Test DB Details

**File**: `ops/docker-compose.test.yml`

**Configuration**:
```yaml
services:
  postgres_test:
    image: postgres:16-alpine
    container_name: deltacrown_test_db
    environment:
      POSTGRES_DB: deltacrown_test
      POSTGRES_USER: dcadmin
      POSTGRES_PASSWORD: dcpass123
    ports:
      - "54329:5432"  # Avoids conflict with local postgres
```

**Isolation**: Test DB runs on different port than production (5432)

---

## Running Specific Tests

```bash
# Single file
pytest tests/test_regression_owner_field_eradication.py -v

# Single test
pytest tests/test_rankings.py::test_zero_point_teams -v

# Quiet mode
pytest -q

# Stop on first failure
pytest -x
```

---

## Troubleshooting

### Error: "Cannot connect to docker test database"

**Cause**: Docker not running or container not started

**Fix**:
```bash
# Start Docker Desktop, then:
docker compose -f ops/docker-compose.test.yml up -d

# Verify running:
docker ps | findstr deltacrown_test_db
```

### Error: "Tests cannot run on remote database"

**Cause**: DATABASE_URL_TEST pointing to Neon or remote DB

**Fix**:
```bash
# Unset remote DB
$env:DATABASE_URL_TEST=""

# Let conftest default to docker DB
pytest
```

### Error: "Port 54329 already in use"

**Cause**: Another postgres instance or previous container

**Fix**:
```bash
# Stop existing container
docker compose -f ops/docker-compose.test.yml down

# Restart
docker compose -f ops/docker-compose.test.yml up -d
```

---

## CI/CD Integration

**GitHub Actions** (example):
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: deltacrown_test
          POSTGRES_USER: dcadmin
          POSTGRES_PASSWORD: dcpass123
        ports:
          - 54329:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: pytest -q
```

**No DATABASE_URL_TEST needed** - conftest defaults to localhost:54329

---

## Database Lifecycle

**Per Test Session**:
1. Conftest enforces DATABASE_URL_TEST (or defaults)
2. Django creates test database
3. Migrations run
4. Tests execute
5. Test database dropped (unless `--reuse-db`)

**Persistence**:
```bash
# Keep test DB between runs (faster)
pytest --reuse-db

# Force recreation
pytest --create-db
```

---

## Schema Isolation (Advanced)

**Feature**: Tests can run in production DB using separate schema

**Benefit**: No CREATEDB privilege needed

**Implementation**: `tests/conftest.py::setup_test_schema()`

**Not needed for docker DB** - full control available

---

## Migration Testing

```bash
# Test migrations from scratch
pytest --create-db

# Test specific migration
python manage.py migrate organizations 0042 --database test
pytest tests/test_organizations.py
```

---

## Related Documentation

- **Repo Hygiene**: [REPO_HYGIENE_CONTRACT.md](REPO_HYGIENE_CONTRACT.md)
- **Phase 15 Report**: [docs/vnext/PHASE_15_STABILITY_RELEASE.md](../vnext/PHASE_15_STABILITY_RELEASE.md)

---

**Status**: ✅ **No longer blocked** (Phase 15 fix)
