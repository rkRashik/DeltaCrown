# DeltaCrown Test Suite

**Directory**: All new tests MUST go in this `tests/` directory at repo root.

**Policy** (enforced 2026-02-04):
- All vNext feature tests go here (no scattered tests in app subdirectories)
- Legacy app-specific tests can remain in `apps/*/tests/` but are not actively maintained
- Test factories and shared fixtures go in `tests/factories.py` and `tests/conftest.py`

---

## Running Tests

### Prerequisites

1. **Test Database**: Start Docker PostgreSQL test container
   ```powershell
   docker compose -f ops/docker-compose.test.yml up -d
   ```

2. **Environment Variable**: Set test database URL
   ```powershell
   $env:DATABASE_URL_TEST = 'postgresql://dcadmin:dcpass123@localhost:5433/deltacrown_test'
   ```

### Run All Tests
```powershell
pytest tests/ -v
```

### Run Specific Test File
```powershell
pytest tests/test_team_create_constraints.py -v
```

### Run with Coverage
```powershell
pytest tests/ --cov=apps --cov-report=html
```

### Quick Smoke Test (no verbose)
```powershell
pytest tests/ -q
```

---

## Test Organization

### Current Structure
```
tests/
├── conftest.py           # Shared fixtures (DB setup, user factories)
├── factories.py          # Test data factories (users, teams, orgs)
├── test_phase16_complete.py  # Phase 16 validation tests
└── README.md             # This file
```

### Naming Conventions

**Test Files**: `test_<feature>_<aspect>.py`
- `test_team_create_constraints.py` - Team creation constraint validation
- `test_team_detail_privacy_and_redirects.py` - Team detail access control
- `test_rankings_include_zero_point_teams_e2e.py` - Rankings end-to-end tests

**Test Classes**: `Test<Feature><Aspect>`
- `TestTeamCreateConstraints` - Groups related tests
- `TestHubShowsAllTeams` - Hub visibility tests

**Test Functions**: `test_<scenario>`
- `test_hub_shows_brand_new_team_immediately`
- `test_one_active_team_per_user_per_game`

---

## Test Fixtures

### Shared Fixtures (from `conftest.py`)
- `django_db` - Enable database access
- `client` - Django test client
- `admin_client` - Authenticated admin client
- `django_user_model` - User model

### Factory Functions (from `factories.py`)
```python
from tests.factories import create_user, create_independent_team, create_org_team

# Create user with email
user = create_user('testuser')  # Auto-generates email

# Create independent team
team, membership = create_independent_team('My Team', user, game_id=1)

# Create org-owned team
org = Organization.objects.create(name='Test Org', slug='test-org')
team, membership = create_org_team('Org Team', user, org, game_id=1)
```

---

## Test Database Configuration

**Container**: `deltacrown_test_db` (PostgreSQL 16 Alpine)  
**Port**: 5433 (host) → 5432 (container)  
**Database**: `deltacrown_test`  
**User**: `dcadmin`  
**Password**: `dcpass123`

**Default URL** (set in `conftest.py`):
```
postgresql://dcadmin:dcpass123@localhost:5433/deltacrown_test
```

**Safety**: Tests CANNOT run against production database. Hardcoded checks in `conftest.py` prevent this.

---

## Writing New Tests

### 1. Add Test File
```python
# tests/test_my_feature.py
import pytest
from django.urls import reverse
from tests.factories import create_user, create_independent_team

@pytest.mark.django_db
class TestMyFeature:
    def test_my_scenario(self, client):
        # Arrange
        user = create_user('testuser')
        team, membership = create_independent_team('Test Team', user)
        
        # Act
        response = client.get(reverse('organizations:team_detail', args=[team.slug]))
        
        # Assert
        assert response.status_code == 200
        assert team.name in response.content.decode('utf-8')
```

### 2. Run Test
```powershell
pytest tests/test_my_feature.py -v
```

### 3. Verify Coverage
```powershell
pytest tests/test_my_feature.py --cov=apps.organizations --cov-report=term-missing
```

---

## Common Issues

### Issue: `NoReverseMatch: 'hub' not found`
**Solution**: Use correct URL names from `apps/organizations/urls.py`:
- ✅ `reverse('organizations:vnext_hub')`
- ❌ `reverse('organizations:hub')`

### Issue: `ValueError: email address must be provided`
**Solution**: Use factory functions which auto-generate emails:
- ✅ `create_user('testuser')` (generates `testuser@example.com`)
- ❌ `User.objects.create_user(username='testuser')` (missing email)

### Issue: `Database access not allowed`
**Solution**: Add `@pytest.mark.django_db` decorator to test function/class

### Issue: `Cannot connect to docker test database`
**Solution**: Start Docker container:
```powershell
docker compose -f ops/docker-compose.test.yml up -d
```

---

## Maintenance

### Adding Shared Fixtures
Edit `tests/conftest.py`:
```python
@pytest.fixture
def my_fixture(db):
    # Setup code
    yield result
    # Teardown code
```

### Adding Factory Functions
Edit `tests/factories.py`:
```python
def create_my_model(name, **kwargs):
    return MyModel.objects.create(name=name, **kwargs)
```

---

## Integration with CI/CD

**GitHub Actions** (future):
```yaml
- name: Run Tests
  run: |
    docker compose -f ops/docker-compose.test.yml up -d
    export DATABASE_URL_TEST=postgresql://dcadmin:dcpass123@localhost:5433/deltacrown_test
    pytest tests/ -v --cov=apps --cov-report=xml
```

---

## Contact

**Issues**: Report test failures or infrastructure issues to Lead Architect  
**Tracker**: See `docs/vnext/TEAM_ORG_VNEXT_MASTER_TRACKER.md` for journey-specific test requirements
