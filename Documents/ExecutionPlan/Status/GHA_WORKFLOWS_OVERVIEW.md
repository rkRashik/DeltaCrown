# GitHub Actions Workflows Overview

**Last Updated**: 2025-11-14  
**Status**: All workflows fixed and operational

---

## Workflow Inventory

### 1. **CI** (`.github/workflows/ci.yml`)

**Purpose**: Main continuous integration pipeline - runs tests on every code push

**Triggers**:
- `push` to `master` or `main` branches
- `pull_request` targeting `master` or `main` branches

**Jobs**:
1. **test** - Run Django test suite with coverage
   - Spins up PostgreSQL 16 and Redis 7 service containers
   - Installs dependencies from `requirements.txt`
   - Runs migrations
   - Executes pytest with coverage reporting
   - Uploads coverage to Codecov

2. **traceability** - Verify planning trace headers
   - Runs `scripts/verify_trace.py` to check for planning document references
   - Non-blocking (warnings only)

**Environment Variables**:
- `DATABASE_URL`: PostgreSQL connection (service container)
- `REDIS_URL`: Redis connection (service container)
- `DJANGO_SETTINGS_MODULE`: `deltacrown.settings`
- `EMAIL_BACKEND`: `django.core.mail.backends.locmem.EmailBackend` (in-memory for tests)

**Pass Criteria**:
- All tests pass (`pytest` exit code 0)
- Migrations apply successfully
- Coverage report generated

**Fail Criteria**:
- Test failures
- Migration errors
- Python syntax/import errors

**Local Equivalent**:
```powershell
# Set up test environment
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/deltatest"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:DJANGO_SETTINGS_MODULE = "deltacrown.settings"

# Run migrations
python manage.py migrate --noinput

# Run tests
pytest --reuse-db --maxfail=5 -q --cov=apps --cov-report=term

# Check traceability
python scripts/verify_trace.py
```

---

### 2. **Guard Workflow Secrets** (`.github/workflows/guard-workflow-secrets.yml`)

**Purpose**: Security scanner for hardcoded credentials in workflow files

**Triggers**:
- `pull_request` with changes to `.github/workflows/**`
- `push` to `master`/`main` with changes to `.github/workflows/**`

**Path Filter**: Only runs when workflow files are modified

**Jobs**:
1. **lint-workflows** - Scan for security violations
   - Checks for hardcoded passwords/secrets
   - Verifies all credentials use `${{ secrets.* }}` syntax
   - Checks for exposed database credentials
   - Warns about unnecessary port mappings

**Pass Criteria**:
- No hardcoded passwords/secrets found
- All credentials properly reference GitHub secrets

**Fail Criteria**:
- Patterns like `PASSWORD: actual_password` (not using secrets)
- Database URLs with embedded credentials
- Common/weak password values

**Behavior**: 
- If no workflow files changed: Shows "No jobs were run" (expected)
- This is cosmetic - the workflow correctly skips when path filter doesn't match

**Local Equivalent**:
```powershell
# Check for hardcoded secrets in workflows
Select-String -Path ".github\workflows\*.yml" -Pattern "PASSWORD:\s*[^$]" -CaseSensitive:$false
Select-String -Path ".github\workflows\*.yml" -Pattern "SECRET:\s*[^$]" -CaseSensitive:$false

# Check for database URLs with credentials
Select-String -Path ".github\workflows\*.yml" -Pattern "postgres(ql)?://[^:]+:[^@]+@"
```

---

### 3. **Performance Baseline** (`.github/workflows/perf-baseline.yml`)

**Purpose**: Runs performance benchmarks to establish baseline metrics

**Triggers**:
- `schedule`: Nightly at 3 AM UTC (`cron: '0 3 * * *'`)
- `workflow_dispatch`: Manual trigger via GitHub UI
- `push` to `master` branch

**Job Conditions**:
- Never runs on pull requests (`if: github.event_name != 'pull_request'`)
- Protects against fork attacks

**Jobs**:
1. **perf-baseline** - Run performance harness
   - Spins up PostgreSQL 14 and Redis 7 service containers
   - Runs `tests/perf/perf_harness.py` with 150 samples
   - Generates `artifacts/performance/baseline.json`
   - Uploads artifact to GitHub (90-day retention)
   - OPTIONAL: Uploads to S3 if `PERF_BASELINE_S3_BUCKET` secret configured
   - OPTIONAL: Sends Slack notification if `PERF_BASELINE_SLACK_WEBHOOK` secret configured

**Required Secrets**:
- None (uses default password if `PERF_DB_PASSWORD` not set)

**Optional Secrets**:
- `PERF_DB_PASSWORD`: PostgreSQL password (defaults to `'perf_test_password'`)
- `PERF_BASELINE_S3_BUCKET`: S3 bucket for baseline storage
- `PERF_BASELINE_SLACK_WEBHOOK`: Slack webhook URL for notifications

**Pass Criteria**:
- Performance harness runs successfully
- Baseline JSON generated
- Artifact uploaded

**Fail Criteria**:
- Harness script errors
- Database connection failures
- JSON generation errors

**Local Equivalent**:
```powershell
# Set up performance environment
$env:PERF_DATABASE_URL = "postgresql://deltacrown:password@localhost:5432/deltacrown_perf"
$env:PERF_REDIS_URL = "redis://localhost:6379/0"

# Run performance harness
python tests/perf/perf_harness.py --samples 150 --json artifacts/performance/baseline.json
```

**Manual Trigger**:
1. Go to: `https://github.com/rkRashik/DeltaCrown/actions/workflows/perf-baseline.yml`
2. Click "Run workflow"
3. Select branch (usually `master`)
4. Click "Run workflow" button

---

### 4. **PII Scan** (`.github/workflows/pii-scan.yml`)

**Purpose**: Scans code for personally identifiable information (PII) leaks

**Triggers**:
- `pull_request` with changes to `tests/**`, `apps/**`, or `deltacrown/**`
- `push` to `master` branch

**Jobs**:
1. **scan-pii** - Pattern-based PII detection
   - Scans for real email addresses
   - Scans for IP addresses (warnings only)
   - Scans for username patterns (warnings only)
   - Checks observability code for PII logging

**Allowed Patterns** (won't fail):
- `example.com`, `example.org`, `test.local` emails
- `deltacrownhq@gmail.com` (project email)
- `@localhost`, `@faker` emails
- Email field definitions in models/serializers
- Localhost IPs: `127.0.0.1`, `0.0.0.0`
- Private IPs: `192.168.*`, `10.*`

**Excluded Locations**:
- `tests/fixtures/` (test data)
- `__pycache__/` (compiled Python)
- Lines with `# PII: safe` comments

**Pass Criteria**:
- No real email addresses found (except allowed patterns)
- No PII logging in observability code
- Missing observability directories handled gracefully

**Fail Criteria**:
- Real email addresses without exclusion comments
- User emails/usernames logged in observability modules
- `request.META["REMOTE_ADDR"]` without hashing in observability code

**Local Equivalent**:
```powershell
# Scan for real email addresses
Select-String -Path "tests\*", "apps\*", "deltacrown\*" -Pattern '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' -Exclude "*example.com*", "*test.local*", "*deltacrownhq@gmail.com*"

# Check observability code
if (Test-Path "apps\observability") {
    Select-String -Path "apps\observability\*" -Pattern 'user\.email|user\.username|request\.META\["REMOTE_ADDR"\]'
}
```

---

## Viewing Workflow Logs

### GitHub UI
1. Navigate to: `https://github.com/rkRashik/DeltaCrown/actions`
2. Click on a workflow run to see details
3. Click on a job name to see logs
4. Expand steps to see individual command output

### GitHub CLI
```powershell
# List recent workflow runs
gh run list

# View specific run
gh run view <run-id>

# View run logs
gh run view <run-id> --log

# Watch a running workflow
gh run watch <run-id>
```

---

## Workflow Status Badges

Add these to `README.md` to display workflow status:

```markdown
[![CI](https://github.com/rkRashik/DeltaCrown/actions/workflows/ci.yml/badge.svg)](https://github.com/rkRashik/DeltaCrown/actions/workflows/ci.yml)
[![PII Scan](https://github.com/rkRashik/DeltaCrown/actions/workflows/pii-scan.yml/badge.svg)](https://github.com/rkRashik/DeltaCrown/actions/workflows/pii-scan.yml)
```

---

## Common Issues and Solutions

### "No jobs were run"

**Cause**: Path filter excluded the workflow

**Examples**:
- `guard-workflow-secrets.yml` only runs when `.github/workflows/**` files change
- If you push code changes but no workflow changes, it shows "No jobs were run"

**Solution**: This is expected behavior. The workflow correctly skipped.

---

### "All jobs have failed" on PII Scan

**Cause**: False positive pattern match

**Common Culprits**:
- Project email in settings/docs
- Example emails in test files
- Email field definitions in models

**Solution**: 
1. Add exclusion comment: `# PII: safe`
2. Ensure using allowed email domains: `example.com`, `test.local`
3. Check if pattern is in `__pycache__` (git ignore it)

---

### Performance Baseline Skipped

**Cause**: Missing secrets or pull request trigger

**Solution**:
- Performance baseline never runs on PRs (security)
- Configure `PERF_DB_PASSWORD` secret (optional but recommended)
- Manually trigger via GitHub UI if needed

---

### Test Failures in CI

**Debug Steps**:
1. Check if tests pass locally:
   ```powershell
   pytest --reuse-db --maxfail=5 -q
   ```

2. Check environment variables:
   ```powershell
   python -c "import os; print(os.environ.get('DATABASE_URL'))"
   ```

3. Check service health:
   - Logs show "Waiting for services to be healthy"
   - PostgreSQL: `pg_isready -U postgres`
   - Redis: `redis-cli ping`

4. Check migrations:
   ```powershell
   python manage.py migrate --noinput
   python manage.py showmigrations
   ```

---

## Secrets Configuration

### Required Secrets
None - all workflows have fallback defaults

### Optional Secrets
| Secret Name | Used By | Purpose | Default |
|------------|---------|---------|---------|
| `PERF_DB_PASSWORD` | perf-baseline | PostgreSQL password | `'perf_test_password'` |
| `PERF_BASELINE_S3_BUCKET` | perf-baseline | S3 bucket for baselines | (skip if not set) |
| `PERF_BASELINE_SLACK_WEBHOOK` | perf-baseline | Slack notifications | (skip if not set) |

### Setting Secrets
1. Go to: `https://github.com/rkRashik/DeltaCrown/settings/secrets/actions`
2. Click "New repository secret"
3. Enter name and value
4. Click "Add secret"

---

## Workflow Permissions

All workflows use **least-privilege permissions**:

| Workflow | Permissions |
|----------|-------------|
| CI | `contents: read` |
| Guard | `contents: read` |
| Perf | `contents: read`, `id-token: write` (for future AWS OIDC) |
| PII Scan | `contents: read` |

**Security**: No workflows have write access to repository contents.

---

## Related Documentation

- **Planning**: `Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md`
- **Standards**: `Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md#ci-cd-standards`
- **Setup Guide**: `docs/development/setup_guide.md`
- **Deployment**: `docs/runbooks/deployment.md`

---

## Maintenance

### Adding New Workflows

1. Create `.github/workflows/<name>.yml`
2. Follow existing patterns for permissions and triggers
3. Add documentation to this file
4. Test with `act` locally or push to test branch

### Modifying Existing Workflows

1. Make changes in `.github/workflows/<workflow>.yml`
2. Push changes - `guard-workflow-secrets.yml` will automatically scan
3. Verify workflow runs successfully in GitHub Actions UI
4. Update this documentation if behavior changes

### Workflow Testing Locally

Use [act](https://github.com/nektos/act) to run workflows locally:

```powershell
# Install act
choco install act-cli

# List workflows
act -l

# Run workflow
act -W .github/workflows/ci.yml

# Run specific job
act -j test
```

**Note**: `act` requires Docker Desktop running.
