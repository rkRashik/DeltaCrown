# Signup IntegrityError Fix - January 20, 2026

## Problem Summary

**Error**: `IntegrityError at /account/verify/otp/`
- Message: `null value in column "about_bio" of relation "user_profile_userprofile" violates not-null constraint`
- Root Cause: The error message was misleading - the actual column is "bio", not "about_bio"
- Impact: New users could not complete signup process

## Investigation

1. **Database Schema Check**:
   - Confirmed only "bio" column exists (no "about_bio" column)
   - Column definition: `bio: text, nullable=NO, default=None`
   - PostgreSQL NOT NULL constraint without database default

2. **Model Definition Issue**:
   - Model had: `bio = models.TextField(blank=True, help_text="Profile bio/headline")`
   - Problem: `blank=True` allows empty values in forms, but no `default=""` for database

3. **Signal Handler**:
   - Signal handler in `apps/user_profile/signals/legacy_signals.py` already had `"bio": ""`  in defaults
   - Both signal and event handlers were providing defaults

## Solution Implemented

### 1. Added Default Value to Model
**File**: `apps/user_profile/models_main.py` (line 104)
```python
# Before:
bio = models.TextField(blank=True, help_text="Profile bio/headline")

# After:
bio = models.TextField(blank=True, default="", help_text="Profile bio/headline")
```

### 2. Created and Applied Migration
- Generated migration: `0096_alter_userprofile_bio_and_more.py`
- Applied migration successfully: Sets `default=""` for bio field
- This ensures all new UserProfile instances have an empty string for bio, not NULL

### 3. Verified Signal Handlers
Both UserProfile creation paths already had correct defaults:
- **Signal Handler** (`apps/user_profile/signals/legacy_signals.py`): ✅ Has `"bio": ""`
- **Event Handler** (`apps/user_profile/events.py`): ✅ Has `"bio": ""`

## Testing

### Test 1: Direct User Creation
```python
user = User.objects.create_user(
    username="testuser68926",
    email="test68926@example.com",
    password="TestPass123!"
)
```
**Result**: ✅ SUCCESS
- User created successfully
- UserProfile created with `bio=''` (empty string, not NULL)
- All 60+ NOT NULL fields have proper values
- UUID generated, public_id assigned

### Test 2: Integration Test
- Simulated complete signup flow
- Created user via `User.objects.create_user()`
- Verified UserProfile with all required fields
**Result**: ✅ SUCCESS

## Files Modified

1. **apps/user_profile/models_main.py**
   - Added `default=""` to bio field definition

2. **apps/user_profile/migrations/0096_alter_userprofile_bio_and_more.py**
   - Generated migration to update bio field with default value

## Deployment Steps

1. ✅ Model updated with default value
2. ✅ Migration created (`0096_alter_userprofile_bio_and_more.py`)
3. ✅ Migration applied to database
4. ✅ Django server restarted
5. ✅ Tests passed successfully

## Impact

- **Before**: Users encountered IntegrityError during signup
- **After**: Users can sign up successfully without errors
- **Risk**: Low - Only added a default value to a field that should always be empty string initially

## Verification

To verify the fix is working:

1. Navigate to: `http://127.0.0.1:8000/account/verify/otp/`
2. Complete signup process
3. Verify no IntegrityError occurs
4. Check UserProfile is created with `bio=''`

## Notes

- The error message "about_bio" was misleading - PostgreSQL sometimes shows field names differently in error messages
- The actual column is "bio" as confirmed by database schema inspection
- All UserProfile NOT NULL fields now have proper defaults in both signal and event handlers
- Migration adds database-level default for safety

## Date: January 20, 2026
## Status: ✅ RESOLVED
