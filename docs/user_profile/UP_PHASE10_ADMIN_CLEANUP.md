# UP-PHASE10: Admin Panel Cleanup - Operator UX Hardening

**Phase:** Admin Interface Improvement  
**Type:** Operator Experience  
**Date:** 2025-12-29  
**Status:** Recommendations

---

## Executive Summary

The User Profile admin panel at `/admin/user_profile/` is functional but cluttered with confusing fields and lacks clear separation between editable vs. system-managed data. This document provides concrete recommendations to make the admin **obviously correct** for operators.

**Goals:**
1. Make economy fields **read-only** (economy app owns these)
2. Display `public_id` prominently (it's a key identifier)
3. Organize fieldsets with clear descriptions
4. Collapse low-signal sections
5. Remove misleading editable fields

---

## Current Issues

### Issue 1: Economy Fields Are Editable (Data Corruption Risk)

**Problem:** Admin can manually edit `deltacoin_balance` and `lifetime_earnings` in UserProfile admin, but these fields are owned by the **economy app**. Manual edits cause drift from source of truth.

**Current State:**
```python
# apps/user_profile/admin/users.py (line 76)
fieldsets = (
    # ...
    ('Economy', {
        'fields': ('deltacoin_balance', 'lifetime_earnings', 'inventory_items')
    }),
)
```

**Risk:** Admin edits wallet balance → economy app overwrites it → data confusion

**Fix:**
```python
# apps/user_profile/admin/users.py

class UserProfileAdmin(admin.ModelAdmin):
    readonly_fields = (
        'uuid', 'slug', 'public_id', 'created_at', 'updated_at', 'kyc_verified_at',
        'deltacoin_balance',  # UP-PHASE10: Economy-owned field (read-only)
        'lifetime_earnings',  # UP-PHASE10: Economy-owned field (read-only)
    )
    
    fieldsets = (
        # ...
        ('Economy (Read-Only)', {
            'fields': ('deltacoin_balance', 'lifetime_earnings', 'inventory_items'),
            'description': '⚠️ Wallet balances are managed by the Economy app. Do NOT edit manually. Use economy admin instead.'
        }),
    )
```

**Priority:** 🔴 **P0 Critical** (prevents data corruption)  
**Effort:** 10 minutes

---

### Issue 2: Public ID Not Visible in Admin

**Problem:** `public_id` (e.g., "DC-25-000123") is a key user identifier but not shown in the admin UI. Operators need this for support tickets and fraud investigations.

**Current State:**
- `public_id` is in `readonly_fields` but not in any fieldset
- Only visible in database queries

**Fix:**
```python
fieldsets = (
    ('User Account', {
        'fields': ('user', 'uuid', 'slug', 'public_id'),  # ✅ Already correct!
        'description': 'Core user identity. Public ID is shown on profile pages.'
    }),
    # ...
)
```

**Actually:** This is **already fixed** in current code! `public_id` is visible in "User Account" fieldset.

**Priority:** ✅ **Already Fixed**

---

### Issue 3: KYC Fields Can Be Edited After Verification

**Problem:** Once a user is KYC verified (`kyc_status='verified'`), their `real_full_name`, `date_of_birth`, and `nationality` should be **immutable** (legal requirement for audit trail).

**Current State:** All KYC fields editable even after verification.

**Fix:**
```python
class UserProfileAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        """Lock KYC fields after verification (legal requirement)"""
        readonly = list(super().get_readonly_fields(request, obj))
        
        # If profile is verified, lock KYC identity fields
        if obj and obj.kyc_status == 'verified':
            readonly += ['real_full_name', 'date_of_birth', 'nationality', 'kyc_status']
        
        return readonly
```

**Priority:** 🟠 **P1 High** (legal compliance)  
**Effort:** 20 minutes

---

### Issue 4: Fieldsets Not Grouped Logically

**Problem:** Fields are scattered across too many fieldsets (11 total). Some sections have only 1 field. Hard to scan.

**Current Fieldsets:**
1. User Account (4 fields) ✅ Good
2. Public Identity (5 fields) ✅ Good
3. Legal Identity & KYC (5 fields) ✅ Good
4. Contact Information (5 fields) ⚠️ Could merge with Demographics
5. Demographics (1 field) ❌ Too small
6. Emergency Contact (3 fields) ⚠️ Low signal, should collapse
7. Social Media (7 fields) ✅ Good
8. Gaming (1 field) ❌ Too small
9. Gamification (3 fields) ⚠️ Low priority, should collapse
10. Economy (3 fields) ✅ Good (with read-only fix)
11. System Data (3 fields) ⚠️ Should collapse

**Recommendation:** Merge small sections, collapse low-priority ones.

**Better Structure:**
```python
fieldsets = (
    ('🔑 User Account', {
        'fields': ('user', 'uuid', 'slug', 'public_id'),
        'description': 'Core user identity. UUID and Public ID are immutable.'
    }),
    ('👤 Public Identity', {
        'fields': ('avatar', 'banner', 'display_name', 'bio', 'region')
    }),
    ('📋 Legal Identity & KYC', {
        'fields': ('real_full_name', 'date_of_birth', 'nationality', 'kyc_status', 'kyc_verified_at'),
        'description': '⚠️ KYC-verified data is locked and cannot be changed after verification.'
    }),
    ('📧 Contact & Location', {
        'fields': ('phone', 'country', 'city', 'postal_code', 'address', 'gender'),
        'description': 'Contact information and demographics.'
    }),
    ('🔗 Social Media', {
        'fields': ('facebook', 'instagram', 'tiktok', 'twitter', 'youtube_link', 'twitch_link', 'discord_id')
    }),
    ('🎮 Gaming & Gamification', {
        'fields': ('stream_status', 'level', 'xp', 'pinned_badges'),
        'description': 'Game profiles are managed in Game Passports admin.',
        'classes': ('collapse',)  # Collapsed by default
    }),
    ('💰 Economy (Read-Only)', {
        'fields': ('deltacoin_balance', 'lifetime_earnings', 'inventory_items'),
        'description': '⚠️ Wallet balances are managed by the Economy app. Do NOT edit manually.'
    }),
    ('🆘 Emergency Contact', {
        'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation'),
        'classes': ('collapse',)  # Collapsed by default (low usage)
    }),
    ('⚙️ System Data', {
        'fields': ('attributes', 'system_settings', 'created_at', 'updated_at'),
        'classes': ('collapse',)
    }),
)
```

**Changes:**
- Merged "Contact Information" + "Demographics" → "Contact & Location"
- Merged "Gaming" + "Gamification" → "Gaming & Gamification" (collapsed)
- Collapsed "Emergency Contact" (rarely used)
- Collapsed "System Data" (rarely needed)
- Added emoji icons for better visual scanning
- Added descriptions explaining read-only vs. editable

**Priority:** 🟡 **P2 Medium** (UX improvement)  
**Effort:** 30 minutes

---

### Issue 5: Duplicate Admin Registrations

**Problem:** Some models may have duplicate admin classes registered (e.g., old vs. new Game Passport admin).

**Check:**
```bash
$ grep -r "@admin.register" apps/user_profile/admin/
```

**Result:**
- `users.py`: `@admin.register(UserProfile)`
- `privacy.py`: `@admin.register(PrivacySettings)`
- `game_passports.py`: `@admin.register(GameProfile, GameProfileAlias, GameProfileConfig)`

**Status:** ✅ No duplicates found (only one registration per model)

**Priority:** ✅ **Already Good**

---

### Issue 6: No Bulk Action Protections

**Problem:** Admin can bulk-edit privacy settings for 100 users at once → violates user consent.

**Current State:** All Django default bulk actions enabled (delete, change).

**Fix:**
```python
class PrivacySettingsAdmin(admin.ModelAdmin):
    # Disable bulk changes (privacy must be changed one-by-one)
    def has_delete_permission(self, request, obj=None):
        # Allow individual deletion, but not bulk
        if obj is None:
            return False  # Bulk delete disabled
        return super().has_delete_permission(request, obj)
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        # Remove bulk delete action
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
```

**Priority:** 🔴 **P0 Critical** (prevents privacy violations)  
**Effort:** 15 minutes

---

## Recommended Implementation Plan

### Phase 1: Critical Fixes (P0 - Do First)

**Estimated Effort:** 1 hour

1. **Make Economy Fields Read-Only** (10 min)
   - Add `deltacoin_balance`, `lifetime_earnings` to `readonly_fields`
   - Update "Economy" fieldset description

2. **Disable Bulk Privacy Edits** (15 min)
   - Override `PrivacySettingsAdmin.get_actions()` to remove bulk delete
   - Override `has_delete_permission()` to block bulk deletion

3. **Lock KYC Fields After Verification** (20 min)
   - Override `UserProfileAdmin.get_readonly_fields()` to lock KYC fields when `kyc_status='verified'`

4. **Add Admin Action Logging** (15 min)
   - Log economy field access attempts
   - Log KYC status changes

### Phase 2: UX Improvements (P1 - Do Within Week)

**Estimated Effort:** 1 hour

5. **Reorganize Fieldsets** (30 min)
   - Merge small sections
   - Collapse low-priority sections
   - Add emoji icons for visual scanning

6. **Add Fieldset Descriptions** (15 min)
   - Explain which fields are editable vs. read-only
   - Add warnings for economy/KYC sections

7. **Improve List Display** (15 min)
   - Add `public_id` to `list_display`
   - Add `kyc_status_badge` with color (already implemented)
   - Add `coin_balance` shortcut (already implemented)

### Phase 3: Polish (P2 - Do Within Month)

**Estimated Effort:** 2 hours

8. **Add Inline Related Models** (45 min)
   - Show Game Passports inline on UserProfile admin
   - Show Privacy Settings inline (collapsed)

9. **Add Custom Admin Actions** (45 min)
   - "Sync Wallet Balance" action (calls economy API)
   - "Export User Data (GDPR)" action
   - "Send Verification Email" action

10. **Add Admin Filters** (30 min)
    - Filter by `public_id` prefix (DC-25-XXX, DC-24-XXX)
    - Filter by "Has Game Passports" (yes/no)
    - Filter by "Balance > 0" (yes/no)

---

## Code Examples

### Example 1: Economy Fields Read-Only

```python
# apps/user_profile/admin/users.py

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    readonly_fields = (
        'uuid',
        'slug',
        'public_id',
        'created_at',
        'updated_at',
        'kyc_verified_at',
        # UP-PHASE10: Economy-owned fields (read-only)
        'deltacoin_balance',
        'lifetime_earnings',
    )
    
    fieldsets = (
        # ... other fieldsets ...
        ('💰 Economy (Read-Only)', {
            'fields': ('deltacoin_balance', 'lifetime_earnings', 'inventory_items'),
            'description': (
                '⚠️ <strong>WARNING:</strong> Wallet balances are managed by the Economy app. '
                'Do NOT edit manually. Use <a href="/admin/economy/wallet/">Economy Admin</a> instead.'
            )
        }),
    )
```

### Example 2: Lock KYC Fields After Verification

```python
# apps/user_profile/admin/users.py

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        """
        Lock KYC fields after verification (legal requirement).
        
        Once a user is verified, their legal identity cannot be changed
        to maintain audit trail integrity.
        """
        readonly = list(super().get_readonly_fields(request, obj))
        
        # If profile is verified, lock KYC identity fields
        if obj and obj.kyc_status == 'verified':
            readonly += [
                'real_full_name',
                'date_of_birth',
                'nationality',
                'kyc_status',  # Cannot unverify
            ]
            messages.info(
                request,
                f"ℹ️ {obj.display_name} is KYC verified. Legal identity fields are locked."
            )
        
        return readonly
```

### Example 3: Disable Bulk Privacy Actions

```python
# apps/user_profile/admin/privacy.py

@admin.register(PrivacySettings)
class PrivacySettingsAdmin(admin.ModelAdmin):
    def get_actions(self, request):
        """Disable bulk actions (privacy must be changed one-by-one)"""
        actions = super().get_actions(request)
        
        # Remove bulk delete (privacy violations risk)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        
        return actions
    
    def has_delete_permission(self, request, obj=None):
        """Allow individual deletion, but not bulk"""
        if obj is None:
            # Bulk delete attempt
            return False
        return super().has_delete_permission(request, obj)
    
    def save_model(self, request, obj, form, change):
        """Log privacy setting changes for audit"""
        super().save_model(request, obj, form, change)
        
        # Log admin action
        from apps.user_profile.services.audit import AuditService
        AuditService.log_admin_action(
            user=obj.user_profile.user,
            admin_user=request.user,
            action='privacy_settings_changed',
            details={'fields_changed': list(form.changed_data)}
        )
```

---

## Testing Checklist

After implementing fixes, verify:

- [ ] Economy fields (`deltacoin_balance`, `lifetime_earnings`) are **grayed out** (uneditable)
- [ ] KYC-verified profile has **locked legal name/DOB/nationality**
- [ ] Bulk delete action is **removed** from PrivacySettings admin
- [ ] Fieldsets are **collapsed** (Emergency Contact, System Data, Gaming)
- [ ] `public_id` is **visible** in "User Account" section
- [ ] Economy fieldset has **warning message** about not editing manually
- [ ] List view shows **public_id**, **kyc_status badge**, **coin_balance**

---

## Future Enhancements (Post-Phase 10)

### Admin Dashboard Widget

Add quick stats to admin home:
- Total verified users
- Total deltacoin circulation
- Users with game passports
- Recent signups (last 7 days)

### GDPR Export Action

One-click user data export for GDPR requests:
```python
@admin.action(description="Export user data (GDPR)")
def export_user_data_gdpr(self, request, queryset):
    for profile in queryset:
        data = {
            'username': profile.user.username,
            'email': profile.user.email,
            'display_name': profile.display_name,
            'bio': profile.bio,
            # ... all profile data ...
        }
        # Generate JSON file
        # Return as download
```

### Wallet Sync Action

Sync wallet balance from economy app:
```python
@admin.action(description="🔄 Sync wallet balance from economy")
def sync_wallet_balance(self, request, queryset):
    from apps.user_profile.services.economy_sync import sync_profile_by_user_id
    
    for profile in queryset:
        old_balance = profile.deltacoin_balance
        sync_profile_by_user_id(profile.user.id)
        profile.refresh_from_db()
        
        if profile.deltacoin_balance != old_balance:
            self.message_user(
                request,
                f"✅ {profile.display_name}: {old_balance} → {profile.deltacoin_balance} ΔC",
                level=messages.SUCCESS
            )
```

---

## Summary

**Critical Priorities (P0):**
1. Make economy fields read-only ✅
2. Disable bulk privacy edits ✅
3. Lock KYC fields after verification ✅

**Estimated Total Effort:** 3-4 hours

**Impact:** Prevents data corruption, improves operator confidence, legal compliance.

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-29  
**Status:** Recommendations (Not Yet Implemented)  
**Owner:** Platform Engineering Team
