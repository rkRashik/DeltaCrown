# DeltaCrown Bootstrap Guide

**Official setup guide for DeltaCrown platform**

---

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ (local for tests)
- Neon database account (for runtime)
- Git

---

## Environment Variables

### Required for Runtime

```bash
# Neon database (production-like)
DATABASE_URL='postgresql://neondb_owner:PASSWORD@ep-xxx.neon.tech/deltacrown?sslmode=require'

# Django settings
DJANGO_SECRET_KEY='your-secret-key-here'
DJANGO_DEBUG='1'  # Set to 0 in production
ALLOWED_HOSTS='localhost,127.0.0.1'

# Optional: Enable competition features
COMPETITION_APP_ENABLED='1'
```

### Required for Tests

```bash
# Local PostgreSQL only (tests refuse remote hosts)
DATABASE_URL_TEST='postgresql://localhost:5432/deltacrown_test'
```

---

## Quick Start (Fresh Neon Database)

### 1. Reset and Bootstrap Neon Database

```bash
# One command to reset schema, migrate, and seed
CONFIRM=1 python manage.py ops_reset_neon_schema

# Or interactive (will prompt for confirmation)
python manage.py ops_reset_neon_schema
```

**This command:**
- Drops and recreates Neon schema
- Runs all migrations
- Seeds games (11 games)
- Seeds passport schemas (11 schemas)
- Seeds competition configs (if COMPETITION_APP_ENABLED=1)

### 2. Create Superuser

```bash
python manage.py createsuperuser
# Username: admin
# Email: admin@example.local
# Password: (choose strong password)
```

### 3. Start Development Server

```bash
python manage.py runserver
```

Visit: http://localhost:8000/admin/

---

## Test Setup

### 1. Create Local Test Database

```bash
# One-time setup
createdb deltacrown_test
```

### 2. Set Test Environment Variable

```bash
# PowerShell
$env:DATABASE_URL_TEST='postgresql://localhost:5432/deltacrown_test'

# Bash/Linux
export DATABASE_URL_TEST='postgresql://localhost:5432/deltacrown_test'
```

### 3. Run Tests

```bash
pytest tests/
```

**Protection:** Tests will refuse to run if DATABASE_URL_TEST not set or points to remote host.

---

## Database Policy

### Runtime (runserver, shell, admin, migrate)
- **Always uses:** `DATABASE_URL` (Neon)
- **Environment:** Production-like
- **Migrations:** Allowed on Neon

### Tests (pytest)
- **Always uses:** `DATABASE_URL_TEST` (local postgres)
- **Environment:** Isolated test database
- **Protection:** Hard-fails on remote databases

**No auto-switching. No DATABASE_URL_DEV. Simple and predictable.**

---

## Troubleshooting

### "DATABASE_URL not set"

Add to your `.env` file or export:
```bash
DATABASE_URL='postgresql://neondb_owner:PASSWORD@ep-xxx.neon.tech/deltacrown?sslmode=require'
```

### "Tests cannot run on remote database"

Set DATABASE_URL_TEST to localhost:
```bash
export DATABASE_URL_TEST='postgresql://localhost:5432/deltacrown_test'
```

---

**Last Updated:** 2026-02-02  
**Main Command:** ops_reset_neon_schema
