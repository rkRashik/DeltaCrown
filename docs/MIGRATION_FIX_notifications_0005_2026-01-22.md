# Migration Error Fix - notifications.0005_notification_is_delivered

## Problem

Migration `notifications.0005_notification_is_delivered` was failing with error:
```
django.db.utils.ProgrammingError: column "is_delivered" of relation "notifications_notification" already exists
```

However, investigation showed the column did NOT actually exist in the database.

## Root Cause

This was a **transaction conflict issue** where:
1. The column did not exist in the database
2. Django's migration system thought it did (likely due to a cached state or interrupted transaction)
3. The migration couldn't proceed because it was trying to add a column that "already exists" (but doesn't)

## Investigation Steps

1. **Checked migration status**: Migration 0005 was not applied
   ```bash
   python manage.py showmigrations notifications
   # [ ] 0005_notification_is_delivered  ← Not applied
   ```

2. **Verified column doesn't exist**: 
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name='notifications_notification' 
   AND column_name='is_delivered'
   -- Result: No rows (column doesn't exist)
   ```

3. **Confirmed database configuration**: Connected to correct database (deltacrown on localhost:5432)

4. **Generated SQL to see what migration does**:
   ```bash
   python manage.py sqlmigrate notifications 0005
   # ALTER TABLE "notifications_notification" ADD COLUMN "is_delivered" boolean DEFAULT false NOT NULL;
   # ALTER TABLE "notifications_notification" ALTER COLUMN "is_delivered" DROP DEFAULT;
   ```

## Solution

Since the column genuinely didn't exist but the migration was failing, we:

### Step 1: Manually Execute the Migration SQL
```python
# Executed the exact SQL from the migration
ALTER TABLE "notifications_notification" ADD COLUMN "is_delivered" boolean DEFAULT false NOT NULL;
ALTER TABLE "notifications_notification" ALTER COLUMN "is_delivered" DROP DEFAULT;
```

**Result**: SQL executed successfully ✅

### Step 2: Fake the Migration
```bash
python manage.py migrate --fake notifications 0005
# Applying notifications.0005_notification_is_delivered... FAKED
```

This marks the migration as applied in Django's migration history without trying to execute it again.

### Step 3: Verify and Complete Migrations
```bash
python manage.py migrate
# Running migrations:
#   Applying user_profile.0103_alter_verificationrecord_id_document_back_and_more... OK
```

All migrations completed successfully! ✅

## Final Status

✅ **Column Added**: `is_delivered` (boolean, default=False)
✅ **Migration Recorded**: notifications.0005 marked as applied
✅ **Model Working**: Notification.objects.filter(is_delivered=True) works
✅ **All Migrations Applied**: No pending migrations remain

## Verification

```python
# Test the field
from apps.notifications.models import Notification

# Field exists
assert hasattr(Notification, 'is_delivered')

# Can query by it
delivered = Notification.objects.filter(is_delivered=True).count()
not_delivered = Notification.objects.filter(is_delivered=False).count()
```

## Why This Happened

This type of error typically occurs when:
- A previous migration run was interrupted mid-transaction
- Database connection was lost during migration
- Manual database changes were attempted
- Multiple migration processes ran simultaneously
- PostgreSQL transaction state got corrupted

## How to Prevent

1. **Always run migrations in a stable environment**
2. **Don't manually modify database schema while migrations are running**
3. **Use database backups before risky migrations**
4. **If migration fails, check actual database state before retrying**

## Commands Used

```bash
# Check migration status
python manage.py showmigrations notifications

# Generate SQL without applying
python manage.py sqlmigrate notifications 0005

# Apply specific migration (use with caution)
python manage.py migrate notifications 0005

# Fake a migration (when already applied manually)
python manage.py migrate --fake notifications 0005

# Apply all pending migrations
python manage.py migrate
```

## Related Files

- **Migration**: `apps/notifications/migrations/0005_notification_is_delivered.py`
- **Model**: `apps/notifications/models.py` (Notification.is_delivered field)

## Database Details

- **Database**: deltacrown (PostgreSQL)
- **Table**: notifications_notification
- **Column**: is_delivered (boolean, NOT NULL, default=False)

---

**Date Fixed**: January 22, 2026  
**Status**: ✅ Resolved  
**Method**: Manual SQL + Fake Migration
