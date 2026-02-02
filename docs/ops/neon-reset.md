# Neon Database Reset Guide

**When to use:** Fresh start needed, corrupted migrations, or schema drift

**Data Loss:** ⚠️  All data will be deleted except what's re-seeded

---

## Prerequisites

- Neon account access: https://console.neon.tech/
- DATABASE_URL set to your Neon database
- Admin credentials ready (you'll create new superuser)

---

## Reset Process

### 1. Backup Important Data (Optional)

If you have data you want to keep:

```bash
# Export specific data
python manage.py dumpdata auth.User --indent 2 > users_backup.json
python manage.py dumpdata games --indent 2 > games_backup.json
```

### 2. Connect to Neon Console

Go to: https://console.neon.tech/

Select your project → Database → SQL Editor

### 3. Drop and Recreate Schema

**⚠️  DESTRUCTIVE - All data will be lost**

```sql
-- Drop everything
DROP SCHEMA public CASCADE;

-- Recreate clean schema
CREATE SCHEMA public;

-- Grant permissions (replace 'neondb_owner' with your role)
GRANT ALL ON SCHEMA public TO neondb_owner;
GRANT ALL ON SCHEMA public TO PUBLIC;
```

Click **Run** to execute.

### 4. Verify Clean State

In SQL Editor:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
```

Expected: Empty result (no tables)

### 5. Run Migrations

Back in your local terminal:

```bash
# Ensure DATABASE_URL is set
echo $DATABASE_URL  # Should show your Neon URL

# Run all migrations
python manage.py migrate

# Verify success
python manage.py showmigrations
```

Expected: All migrations should have `[X]` marks

### 6. Seed Core Data

```bash
# 1. Seed games (includes roles and identity configs)
python manage.py seed_games

# 2. Seed game passport schemas
python manage.py seed_game_passport_schemas

# 3. (Optional) Seed competition ranking configs
# Only if COMPETITION_APP_ENABLED=1
python manage.py seed_game_ranking_configs
```

**Expected Output:**
- seed_games: `✓ Successfully seeded 11 games`
- seed_game_passport_schemas: `🎉 Seeding complete! Created: 11`
- seed_game_ranking_configs: `Seed complete: 11 created`

### 7. Create Superuser

```bash
python manage.py createsuperuser

# Follow prompts:
# Username: admin
# Email: admin@deltacrown.local
# Password: (choose secure password)
```

**Or create via shell:**
```bash
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@deltacrown.local', 'admin123')" | python manage.py shell
```

### 8. Verify Setup

```bash
# Start server
python manage.py runserver

# Visit http://127.0.0.1:8000/admin/
# Login with your superuser credentials
# Verify admin loads without errors
```

---

## Verification Checklist

After reset, verify:

- [ ] All migrations applied: `python manage.py showmigrations`
- [ ] Games seeded: Check /admin/games/game/ (should show 11 games)
- [ ] Competition configs seeded: Check /admin/competition/gamerankingconfig/ (if enabled)
- [ ] Superuser works: Can login to /admin/
- [ ] No migration errors on startup
- [ ] No missing table errors in admin

---

## Common Issues

### Issue: Permission denied on DROP SCHEMA

**Solution:** Use Neon web UI SQL Editor with owner role

### Issue: ALLOW_PROD_MIGRATE blocking migrations

**Solution:** 
```bash
ALLOW_PROD_MIGRATE=1 python manage.py migrate
```

### Issue: Tables still exist after DROP SCHEMA

**Solution:** Drop specific schema:
```sql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
```

### Issue: Migration conflicts after reset

**Solution:** Database is clean, so this shouldn't happen. If it does:
```bash
# Delete local migration records cache
find . -path "*/migrations/*.pyc" -delete
find . -path "*/migrations/__pycache__" -delete

# Try again
python manage.py migrate
```

---

## Alternative: Reset via psql

If you prefer command-line:

```bash
# Get connection string from Neon dashboard
# Format: postgresql://user:password@host/database

# Connect
psql "postgresql://neondb_owner:YOUR_PASSWORD@ep-ancient-recipe-a1m0hazw.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

# In psql:
\c neondb
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
\q

# Back to shell - continue with step 5 (migrations)
```

---

## Quick Reset Script (Advanced)

**⚠️  Use with caution - this is destructive!**

```bash
#!/bin/bash
# reset_neon.sh - Quick Neon database reset

set -e  # Exit on error

echo "⚠️  This will DELETE ALL DATA in your Neon database!"
read -p "Are you sure? (type 'yes'): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Aborted"
    exit 1
fi

echo "1. Dropping schema..."
psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "2. Running migrations..."
python manage.py migrate

echo "3. Seeding games..."
python manage.py seed_games

echo "4. Seeding passport schemas..."
python manage.py seed_game_passport_schemas

if [ "$COMPETITION_APP_ENABLED" = "1" ]; then
    echo "5. Seeding competition configs..."
    python manage.py seed_game_ranking_configs
fi

echo "6. Creating superuser..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@deltacrown.local', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

echo "✅ Reset complete!"
echo "   Username: admin"
echo "   Password: admin123"
echo "   ⚠️  Change password immediately!"
```

Save as `scripts/reset_neon.sh`, make executable:
```bash
chmod +x scripts/reset_neon.sh
./scripts/reset_neon.sh
```

---

## After Reset

### What's Preserved
- Game configurations (11 games) ✅
- Competition ranking configs (if enabled) ✅

### What Needs Recreation
- Users/superuser ❌
- Teams ❌
- Tournaments ❌
- Matches ❌
- User profiles ❌

### Re-importing Data

If you have backups:

```bash
# Import users
python manage.py loaddata users_backup.json

# Import other data
python manage.py loaddata games_backup.json
```

---

## Verification

After completing the reset, verify everything works:

### 1. Database Tables Exist

```bash
python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT COUNT(*) FROM games_game'); print('Games:', cursor.fetchone()[0])"
```

**Expected:** `Games: 11`

### 2. Admin Access

```bash
python manage.py runserver
```

Visit http://localhost:8000/admin/ and login with admin credentials.

**Must work:**
- `/admin/` - Dashboard loads
- `/admin/games/game/` - Shows 11 games
- `/admin/user_profile/gamepassportschema/` - Shows 11 schemas
- `/admin/competition/gamerankingconfig/` - Shows 11 configs (if seeded)
- `/admin/organizations/team/` - Loads (empty initially, no errors)

### 3. Frontend Pages

Visit these URLs (should load without DB errors):
- `/` - Home page
- `/teams/vnext/` - Teams list (may be empty)
- `/teams/protocol-v/` - Legacy teams page
- `/competition/ranking/about/` - Competition about page (if enabled)

**Expected:** No "relation does not exist" errors

### 4. System Check

```bash
python manage.py check --deploy
```

**Expected:** `System check identified 119 issues (0 silenced).` (warnings only, no critical errors)

---

## Troubleshooting

### "relation organizations_team does not exist"

**Not an error.** The codebase uses `teams_team` (legacy) as authoritative. The `organizations_team` model exists but isn't actively queried in most views.

**Fix if needed:** Run `python manage.py migrate organizations`

### "relation competition_gamerankingconfig does not exist"

**Cause:** Competition migrations not applied or configs not seeded

**Fix:**
```bash
python manage.py migrate competition
python manage.py seed_game_ranking_configs
```

### "No module named 'seed_core_data'"

**Cause:** Old documentation reference. That command was deleted.

**Fix:** Use `seed_games` instead

---

**Last Updated:** 2026-02-02  
**Related:** [bootstrap.md](bootstrap.md), [PROOF.md](PROOF.md)

---

## See Also

- `docs/vnext/cleanup-and-db-normalization.md` - Database configuration
- `README_TECHNICAL.md` - Setup guide
- Neon documentation: https://neon.tech/docs/

---

**Last Updated:** 2026-02-02
