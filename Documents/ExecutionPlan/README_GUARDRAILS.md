# DeltaCrown Implementation Guardrails

This directory contains scaffolding files that ensure implementation stays aligned with the execution plan.

## Files Created (Phase 0)

### Traceability
- **MAP.md** - Human-readable mapping of modules to planning documents
- **trace.yml** - Machine-checkable YAML mapping for CI verification
- **scripts/verify_trace.py** - CI script that validates traceability

### Code Quality
- **.pre-commit-config.yaml** - Pre-commit hooks (black, isort, flake8, mypy)
- **.flake8** - Flake8 linting configuration
- **pyproject.toml** - Black, isort, mypy, and pytest configuration

### CI/CD
- **.github/workflows/ci.yml** - CI workflow with linting, type checking, tests, and traceability verification
- **.github/PULL_REQUEST_TEMPLATE.md** - PR template enforcing plan adherence
- **.github/ISSUE_TEMPLATE/module_task.md** - Issue template for module implementation
- **.github/CODEOWNERS** - Code ownership configuration

## Workflow

### For Each Module

1. **Create Issue** - Use module_task.md template
2. **Create Branch** - Format: `phase-<n>/module-<n.n>-<shortname>`
3. **Write Tests First** (TDD)
4. **Implement Code** - Add doc headers with plan citations
5. **Update Traceability** - Update MAP.md and trace.yml
6. **Run Checks** - Pre-commit hooks + CI
7. **Open PR** - Use PR template, check all boxes
8. **One Module Per PR** - Never mix modules

### Doc Header Format

Every new/modified code file must include:

```python
"""
Implements:
- Documents/ExecutionPlan/00_MASTER_EXECUTION_PLAN.md#<phase-and-module-anchor>
- Documents/Planning/PART_X.Y_<document>.md#<section>
ADRs:
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#ADR-XXX
Notes:
- [Any implementation notes or plan deviations]
"""
```

### Commit Message Format

- `feat(module:X.Y): description`
- `test(module:X.Y): description`
- `chore(ci): description`

### Branch Format

- `phase-<n>/module-<n.n>-<shortname>`
- Example: `phase-1/module-1.1-base-models`

## Setup

### Install Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

### Run Checks Locally

```bash
# Format code
black .
isort .

# Lint
flake8 .

# Type check
mypy apps

# Test
pytest

# Verify traceability
python scripts/verify_trace.py
```

## Phase 0 Completion

✅ All scaffolding files created
✅ CI configured with comprehensive checks
✅ Traceability system in place
✅ Code quality tools configured
✅ PR/Issue templates ready

**Ready to begin Phase 1 implementation.**
