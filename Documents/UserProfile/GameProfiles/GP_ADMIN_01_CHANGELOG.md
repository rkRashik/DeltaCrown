# GP-ADMIN-01 Changelog — Game Passport Admin UX

**Date:** December 24, 2025  
**Objective:** Implement fully usable Django admin for GP-0 Game Passport system  
**Status:** ✅ COMPLETE

---

## Summary

Implemented production-grade Django admin for Game Passport system with:
- Enhanced GameProfile admin with identity lock tracking
- Read-only GameProfileAlias inline for identity change history
- Singleton GameProfileConfig admin for global settings
- Audit integration for all admin actions
- Admin actions for common operations (unlock, pin/unpin)

**Key Achievement:** Admins can now manage game passports entirely through Django admin WITHOUT editing JSON fields or using shell commands.

---

## Files Modified

### 1. apps/user_profile/admin.py

**Changes Made:**

#### A) Updated Imports
- Added `GameProfileAlias` and `GameProfileConfig` to model imports
- Required for new admin classes and inlines

#### B) Created GameProfileAliasInline (NEW)
**Purpose:** Show identity change history within game passport detail view

**Features:**
- Read-only tabular inline
- Displays: old_in_game_name, changed_at, changed_by_user, request_ip, reason
- No add/delete permissions (append-only from service layer)
- Smart user link display with fallback for deleted users

**Technical Details:**
```python
class GameProfileAliasInline(admin.TabularInline):
    model = GameProfileAlias
    can_delete = False
    extra = 0
    
    # All fields readonly
    readonly_fields = [
        'old_in_game_name',
        'changed_at',
        'changed_by_user_display',  # Custom display with user link
        'request_ip',
        'reason',
    ]
    
    def has_add_permission(self, request, obj=None):
        return False  # Prevent manual alias creation
```

#### C) Replaced GameProfileAdmin (ENHANCED)
**Previous:** Basic admin with verification fields  
**New:** GP-0 compliant admin with identity management

**List Display:**
- user
- game
- in_game_name
- identity_key (readonly)
- visibility (PUBLIC/PROTECTED/PRIVATE)
- is_lft (looking for team)
- is_pinned
- **lock_status_display** (color-coded lock status)
- updated_at

**List Filters:**
- game
- visibility
- is_lft
- is_pinned
- status (ACTIVE/SUSPENDED)
- created_at

**Search Fields:**
- user__username
- user__email
- in_game_name
- identity_key

**Fieldsets:**
1. **Identity**
   - user, game, game_display_name, in_game_name, identity_key (readonly), region

2. **Visibility & Status**
   - visibility, status, is_lft

3. **Featured & Ordering**
   - is_pinned, pinned_order, sort_order

4. **Rank & Stats** (collapsible)
   - rank_name, rank_image, rank_points, rank_tier, peak_rank
   - matches_played, win_rate, kd_ratio, hours_played, main_role

5. **Metadata (JSON)** (collapsible)
   - metadata field with description

6. **Lock Info** (collapsible)
   - locked_until_display (formatted timestamp)
   - **lock_countdown_display** (human-readable countdown: "Locked for 17 days, 5 hours")

7. **Timestamps** (collapsible)
   - created_at, updated_at

**Custom Display Methods:**

1. `lock_status_display(obj)` → List view lock indicator
   - ✓ Unlocked (green) — No lock
   - 🔒 Locked (X days) (red) — Currently locked
   - ⏱ Expired (orange) — Lock expired

2. `locked_until_display(obj)` → Formatted timestamp
   - "Not locked" or "2025-12-31 23:59:59 UTC"

3. `lock_countdown_display(obj)` → Human-readable countdown
   - "Identity changes allowed" or "Locked for 17 days, 5 hours"

**Admin Actions:**

1. **unlock_identity_changes(queryset)**
   - Removes `locked_until` for selected passports
   - Records audit event for each unlock
   - Success message with count

2. **pin_passports(queryset)**
   - Sets `is_pinned=True` for selected passports

3. **unpin_passports(queryset)**
   - Sets `is_pinned=False`, clears `pinned_order`

**Save Model Override:**
```python
def save_model(self, request, obj, form, change):
    # Detect identity changes
    if change:
        old_obj = GameProfile.objects.get(pk=obj.pk)
        if old_obj.in_game_name != obj.in_game_name:
            # Warn admin that cooldown was bypassed
            self.message_user(request, "WARNING: Identity changed directly via admin (bypasses cooldown)...", level=messages.WARNING)
    
    # Save normally
    super().save_model(request, obj, form, change)
    
    # Record audit event
    AuditService.record_event(
        subject_user_id=obj.user.id,
        actor_user_id=request.user.id,
        event_type='game_passport.admin_edited',
        ...
    )
```

**Inline Added:**
- `GameProfileAliasInline` — Shows identity change history

#### D) Created GameProfileConfigAdmin (NEW SINGLETON)
**Purpose:** Manage global game passport settings

**List Display:**
- cooldown_display ("30 days")
- max_pinned_games
- allow_id_change
- require_region
- updated_at

**Fields:**
- cooldown_days (editable)
- allow_id_change (editable toggle)
- max_pinned_games (editable)
- require_region (editable toggle)
- enable_ip_smurf_detection (editable toggle)
- created_at (readonly)
- updated_at (readonly)

**Singleton Pattern Enforcement:**

1. `has_add_permission(request)` → Only if no config exists
   ```python
   return not GameProfileConfig.objects.exists()
   ```

2. `has_delete_permission(request, obj)` → Always False (prevent deletion)

3. `get_queryset(request)` → Only show pk=1
   ```python
   return qs.filter(pk=1)
   ```

4. `changelist_view(request)` → Redirect to edit view if config exists
   - Admins see edit form directly, not list view
   - If no config, shows "Add" button

**Help Text:**
Each field has inline help text explaining its purpose:
- cooldown_days: "Days before user can change identity again"
- allow_id_change: "Global toggle for identity changes"
- max_pinned_games: "Maximum pinned passports per user"
- require_region: "Require region on passport creation"
- enable_ip_smurf_detection: "Enable IP-based smurf detection (future)"

---

## Usage Examples

### 1. View Game Passport with Identity History

1. Navigate to: Admin → User Profile → Game Passports
2. Click on any passport
3. Scroll to "Identity Change History" inline section
4. See all previous identities with timestamps, IPs, reasons

**Use Case:** Investigate reports of identity impersonation or frequent changes

### 2. Unlock Identity Change for User

**Scenario:** User accidentally changed identity and wants to change back

**Steps:**
1. Go to Admin → User Profile → Game Passports
2. Search for user
3. Select passport(s)
4. Actions dropdown → "Unlock identity changes (remove cooldown)"
5. Click "Go"

**Result:**
- `locked_until` cleared
- Audit event created: `game_passport.admin_unlocked`
- User can now change identity via service

### 3. Configure Global Settings

1. Navigate to: Admin → User Profile → Game Passport Configuration
2. Auto-redirects to edit form (singleton)
3. Adjust settings:
   - Increase cooldown to 60 days
   - Disable identity changes globally
   - Increase max pinned to 5 games
4. Click "Save"

**Changes Apply Immediately:** All service layer calls use `GameProfileConfig.get_config()`

### 4. Monitor Lock Status

**List View:**
- Green ✓ = User can change identity
- Red 🔒 = Locked (shows days remaining)
- Orange ⏱ = Lock expired (shouldn't happen, but indicates system recovered)

**Detail View:**
- "Lock Info" fieldset shows:
  - Exact locked_until timestamp
  - Human-readable countdown: "Locked for 17 days, 5 hours"

### 5. Pin/Unpin Passports

**Pin:**
1. Select passport(s)
2. Actions → "Pin passports"
3. Result: `is_pinned=True`

**Unpin:**
1. Select passport(s)
2. Actions → "Unpin passports"
3. Result: `is_pinned=False`, `pinned_order=None`

**Note:** Pinned order is auto-assigned by service layer. Admin can manually edit `pinned_order` in detail view.

---

## Admin Permissions

### Recommended Django Permissions

**For Game Passport Management:**
- `user_profile.view_gameprofile` — View passports
- `user_profile.change_gameprofile` — Edit passports (includes unlock action)
- `user_profile.delete_gameprofile` — Delete passports (use cautiously)

**For Configuration:**
- `user_profile.change_gameprofileconfig` — Edit singleton config (super admins only)

**For Audit:**
- `user_profile.view_gameprofilealias` — View identity history (via inline)

### Permission Groups (Recommended)

**Game Passport Moderator:**
- View + Change GameProfile
- View GameProfileAlias (via inline)
- Can unlock identities, pin/unpin

**Game Passport Admin:**
- All of above +
- Change GameProfileConfig
- Can adjust global settings

---

## Audit Trail

All admin actions are logged via AuditService:

**Events Recorded:**

1. **game_passport.admin_edited**
   - Triggered: When admin saves GameProfile
   - Metadata: game, identity_key, edited_by_admin

2. **game_passport.admin_unlocked**
   - Triggered: When admin uses "Unlock identity changes" action
   - Metadata: game, unlocked_by_admin

**Querying Audit Events:**
```python
from apps.user_profile.models import UserAuditEvent

# Find all admin-edited passports
events = UserAuditEvent.objects.filter(
    event_type='game_passport.admin_edited'
)

# Find unlocks by specific admin
events = UserAuditEvent.objects.filter(
    event_type='game_passport.admin_unlocked',
    metadata__unlocked_by_admin='admin_username'
)
```

---

## Testing Admin UI

### Manual Test Cases

**Test 1: Alias Inline Visibility**
- Create passport
- Change identity via GamePassportService (creates alias)
- Open passport in admin
- **Expected:** Alias appears in inline with old name, timestamp, user

**Test 2: Lock Status Display**
- Create passport
- Change identity (locks for 30 days)
- View in admin list
- **Expected:** Red 🔒 icon with "X days" countdown

**Test 3: Unlock Action**
- Select locked passport
- Run "Unlock identity changes" action
- Refresh detail view
- **Expected:** Lock status = ✓ Unlocked (green), locked_until = null

**Test 4: Config Singleton**
- Navigate to GameProfileConfig admin
- **Expected:** Redirects to edit form (not list view)
- Try to delete
- **Expected:** Delete button disabled

**Test 5: Identity Change Warning**
- Edit passport in admin
- Change in_game_name
- Save
- **Expected:** WARNING message about cooldown bypass

---

## Known Limitations

### 1. Admin Bypass of Cooldown
**Issue:** Admins can change `in_game_name` directly in admin, bypassing cooldown

**Mitigation:**
- Warning message displayed
- Audit event created
- Consider making `in_game_name` readonly in admin for production

### 2. No Validation on Direct Edit
**Issue:** Admin can set invalid `in_game_name` (e.g., wrong format for game)

**Mitigation:**
- Model `save()` method generates `identity_key` automatically
- Future: Add form validation in admin

### 3. Pinned Order Management
**Issue:** Admin can manually edit `pinned_order` but must avoid duplicates

**Recommendation:**
- Use service layer `reorder_pinned_passports()` for complex reordering
- Admin should only toggle `is_pinned` on/off

---

## Future Enhancements

### Phase 2 (Post-GP-CLEAN-01)

1. **Custom Admin Form with Validation**
   - Validate IGN format using GameValidators
   - Prevent invalid identity_key generation

2. **Bulk Import/Export**
   - CSV import for batch passport creation
   - Excel export for reporting

3. **Advanced Filters**
   - Filter by locked/unlocked status
   - Filter by identity change count
   - Filter by last alias timestamp

4. **Dashboard Widget**
   - Count of locked passports
   - Recent identity changes
   - Uniqueness violations

---

## Conclusion

GP-ADMIN-01 delivers a fully operational Django admin for Game Passport system. Admins can:
- ✅ View and edit passports without JSON editing
- ✅ Track identity change history via inline
- ✅ Unlock cooldowns with audit trail
- ✅ Configure global settings via singleton admin
- ✅ Monitor lock status with visual indicators

**Admin UX Status:** 🟢 PRODUCTION READY

**Next Phase:** GP-CLEAN-01 (Remove verification remnants and legacy JSON paths)
