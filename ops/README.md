# DeltaCrown Ops - Test Infrastructure

This directory contains operational tooling for DeltaCrown testing infrastructure.

## Files

- **docker-compose.test.yml** - Dockerized PostgreSQL for tests
  - Database: `deltacrown_test`
  - User: `dcadmin` / Password: `dcpass123`
  - Port: `54329` (avoids conflicts with local PostgreSQL on 5432)
  - Volume: `deltacrown_test_db_data` (persistent)

## Quick Start

### Run All Tests
```powershell
.\scripts\run_tests.ps1
```

### Run Specific Test File
```powershell
.\scripts\run_tests.ps1 tests/test_team_creation_regression.py
```

### Using Makefile (if GNU Make installed)
```bash
make test              # Run all tests
make test-phase11      # Run Phase 11 regression tests
make test-admin        # Run admin stability tests
make docker-up         # Start test DB (keeps running)
make docker-down       # Stop test DB
make docker-clean      # Remove DB volume (reset)
```

## Manual Docker Management

### Start Test Database
```powershell
cd ops
docker-compose -f docker-compose.test.yml up -d
```

### Check Status
```powershell
docker ps | Select-String deltacrown_test_db
docker logs deltacrown_test_db
```

### Stop and Remove
```powershell
cd ops
docker-compose -f docker-compose.test.yml down     # Stop only
docker-compose -f docker-compose.test.yml down -v  # Stop + remove volume
```

## Database Connection

When test database is running, connect with:
```powershell
$env:DATABASE_URL_TEST='postgresql://dcadmin:dcpass123@localhost:54329/deltacrown_test'
```

Or use `psql`:
```bash
psql -h localhost -p 54329 -U dcadmin -d deltacrown_test
# Password: dcpass123
```

## CI/CD Integration

For CI pipelines, use the test runner script:
```yaml
# Example GitHub Actions
- name: Run Tests
  run: .\scripts\run_tests.ps1
```

The script automatically:
1. Starts Docker container
2. Waits for database to be ready
3. Runs migrations
4. Executes tests
5. Stops container (unless --KeepAlive flag used)

## Troubleshooting

### Docker not running
```
ERROR: Docker is not running. Please start Docker Desktop.
```
Solution: Start Docker Desktop application.

### Port 54329 already in use
```
ERROR: Failed to start test database container
```
Solution: Stop conflicting container or change port in `docker-compose.test.yml`.

### Database migrations fail
```
ERROR: Migrations failed
```
Solution: Reset database volume:
```powershell
cd ops
docker-compose -f docker-compose.test.yml down -v
```

### Tests timeout waiting for DB
Check container health:
```powershell
docker inspect deltacrown_test_db --format '{{.State.Health.Status}}'
```
Should show `healthy`. If not, check logs:
```powershell
docker logs deltacrown_test_db
```

## Performance Notes

- **First run**: ~30-60 seconds (downloads PostgreSQL image, creates volume)
- **Subsequent runs**: ~5-10 seconds (reuses existing image/volume)
- **Test execution**: Varies by test suite
- **Cleanup**: ~5 seconds

## Security Notes

Test database credentials are hardcoded for local development:
- User: `dcadmin`
- Password: `dcpass123`
- Database: `deltacrown_test`

These are **SAFE** for local testing. They match `settings_test.py` expectations and are never used in production.

## Architecture

```
┌─────────────────────────────────────────┐
│  scripts/run_tests.ps1                  │
│  (Test orchestration)                   │
└──────────────┬──────────────────────────┘
               │
               ├─► Docker Compose (ops/docker-compose.test.yml)
               │   └─► PostgreSQL 16 container
               │       ├─► localhost:54329
               │       └─► Volume: deltacrown_test_db_data
               │
               ├─► Django Migrations
               │   └─► Applies schema to test DB
               │
               └─► Pytest Execution
                   └─► Uses DATABASE_URL_TEST
```
