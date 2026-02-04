# Repo Hygiene Contract

**Enforced**: 2026-02-04  
**Status**: Active

---

## File Placement Rules

### ✅ Allowed Locations

| Type | Location | Examples |
|------|----------|----------|
| **vNext Documentation** | `docs/vnext/` | PHASE_*.md, *_TRACKER.md, technical specs |
| **Operations Documentation** | `docs/ops/` | *_ERADICATION.md, *_FIX.md, runbooks |
| **General Documentation** | `docs/` | Architecture, guides, contracts |
| **Tests** | `tests/` | test_*.py, conftest.py |
| **Operations Scripts** | `scripts/ops/` | scan_*.py, check_*.py, fix_*.py |
| **Dev Tooling** | `tools/` | Build scripts, dev utilities |

### ❌ FORBIDDEN in Project Root

**Never commit these to root**:
- Additional `.md` files (except README.md, README_TECHNICAL.md)
- Test files (`test_*.py`, `*_test.py`)
- Scripts (`scan_*.py`, `check_*.py`, `fix_*.py`, etc.)
- SQL files (`*.sql`)
- Database files (`*.sqlite3`, `*.db`)
- Phase summaries
- Tracker files

**Only standard project files allowed in root**:
- `manage.py` (Django)
- `pyproject.toml` (Python package config)
- `pytest.ini` (Test config)
- `Makefile` (Build automation)
- `Dockerfile`, `docker-compose*.yml` (Containerization)
- `.env*`, `.gitignore`, etc. (Configuration)

---

## Naming Conventions

### Documentation Files

**vNext Work** (`docs/vnext/`):
- Phase reports: `PHASE_<N>_<DESCRIPTION>.md`
- Trackers: `TEAM_ORG_VNEXT_CANONICAL_TRACKER.md` (singular, canonical)
- Technical specs: `<FEATURE>_SPECIFICATION.md`

**Operations** (`docs/ops/`):
- Fix summaries: `<ISSUE>_ERADICATION.md`, `<ISSUE>_FIX_SUMMARY.md`
- Runbooks: `<PROCESS>_RUNBOOK.md`
- Incident reports: `INCIDENT_<DATE>_<DESCRIPTION>.md`

### Scripts

**Operations Scripts** (`scripts/ops/`):
- Scanning: `scan_<target>_<issue>.py`
- Checking: `check_<what>.py`
- Fixing: `fix_<issue>.py`
- All scripts must be executable standalone (include docstring with usage)

### Tests

**Test Files** (`tests/`):
- Unit tests: `test_<module>_<feature>.py`
- Integration tests: `test_<flow>_integration.py`
- Regression tests: `test_regression_<issue>.py`
- Fixtures: `conftest.py`

---

## Enforcement

### Automated Guard

**Script**: `scripts/ops/check_repo_hygiene.py`

**Usage**:
```bash
python scripts/ops/check_repo_hygiene.py
```

**Exit Codes**:
- `0`: Clean (no violations)
- `1`: Violations found

**CI Integration**: Add to existing CI workflow (e.g., `.github/workflows/test.yml`):
```yaml
- name: Check repo hygiene
  run: python scripts/ops/check_repo_hygiene.py
```

### Pre-commit Hook (Recommended)

Add to `.pre-commit-config.yaml`:
```yaml
- repo: local
  hooks:
    - id: repo-hygiene
      name: Check repo hygiene
      entry: python scripts/ops/check_repo_hygiene.py
      language: system
      pass_filenames: false
      always_run: true
```

**Install pre-commit**:
```bash
pip install pre-commit
pre-commit install
```

---

## Migration Guide

**If you created files in root** (enforcement started 2026-02-04):

1. **Identify file type**:
   - Documentation? → `docs/vnext/` or `docs/ops/`
   - Test? → `tests/`
   - Script? → `scripts/ops/`

2. **Move file**:
   ```bash
   # Example: move phase doc
   git mv PHASE_15_STABILITY_RELEASE.md docs/vnext/
   
   # Example: move script
   git mv scan_owner_violations.py scripts/ops/
   ```

3. **Fix internal references**:
   - Update all `[link](OLDPATH.md)` → `[link](NEWPATH.md)`
   - Update all `python script.py` → `python scripts/ops/script.py`

4. **Update imports** (if applicable):
   ```python
   # Scripts may need path adjustments
   from pathlib import Path
   PROJECT_ROOT = Path(__file__).parent.parent.parent  # From scripts/ops/
   ```

---

## Cleanup History

**Date**: 2026-02-04

**Files Moved**:
- `OWNER_FIELD_ERADICATION.md` → `docs/ops/OWNER_FIELD_ERADICATION.md`
- `PHASE_15_STABILITY_RELEASE.md` → `docs/vnext/PHASE_15_STABILITY_RELEASE.md`
- `TEAM_ORG_VNEXT_CANONICAL_TRACKER.md` → `docs/vnext/TEAM_ORG_VNEXT_CANONICAL_TRACKER.md`
- `scan_owner_violations.py` → `scripts/ops/scan_owner_violations.py`

**Files Deleted**:
- `PHASE_9_COMPLETE.md` (obsolete)
- `test_phase11_flows.py` (moved to tests/ in previous phase)
- `test_deltacrown.sqlite3` (test artifact)

**References Updated**:
- All internal doc links
- All script execution commands
- Canonical tracker authoritative header added

---

## Benefits

**Why enforce this**:
1. **Discoverability**: Files are where you expect them
2. **Maintainability**: Clear structure prevents clutter
3. **CI/CD**: Automation knows where to find things
4. **Onboarding**: New devs understand conventions immediately
5. **Git History**: Cleaner diffs, easier to track changes

---

## Violation Resolution

**If hygiene check fails**:

1. **Run checker**:
   ```bash
   python scripts/ops/check_repo_hygiene.py
   ```

2. **Review violations** (script suggests locations)

3. **Move files** to proper locations

4. **Update references** in docs/code

5. **Re-run checker** to verify

6. **Commit** with message: `chore: enforce repo hygiene - move <file> to <location>`

---

## Exceptions

**Rare cases requiring approval**:
- New standard project files (e.g., `setup.cfg` for package distribution)
- Framework requirements (e.g., `conftest.py` in root for pytest discovery)

**Process**:
1. Justify in PR description
2. Update `ALLOWED_ROOT_FILES` in `check_repo_hygiene.py`
3. Document in this contract

---

## Related Documentation

- **Canonical Tracker**: [docs/vnext/TEAM_ORG_VNEXT_CANONICAL_TRACKER.md](../vnext/TEAM_ORG_VNEXT_CANONICAL_TRACKER.md)
- **Phase 15 Report**: [docs/vnext/PHASE_15_STABILITY_RELEASE.md](../vnext/PHASE_15_STABILITY_RELEASE.md)

---

**Maintained by**: Development Team  
**Review Frequency**: Quarterly or when adding new file categories
