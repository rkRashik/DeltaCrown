# Admin Organization Guide

## ⚠️ CRITICAL: UserProfile Admin Registration

**DO NOT register UserProfile in `apps/user_profile/admin.py`!**

### File Organization

```
apps/user_profile/
├── admin.py                    ← All OTHER models (Badges, Privacy, etc.)
└── admin/
    └── users.py               ← UserProfile ONLY (OFFICIAL admin)
```

### Why This Structure?

Django's admin system uses **LAST REGISTERED WINS** behavior. When `apps/user_profile/admin/users.py` is imported after `admin.py`, its `@admin.register(UserProfile)` overrides any previous registration.

Previously, we had **duplicate registrations** causing fieldsets to be out of sync. This led to:
- New fields not appearing in admin panel
- Confusion about which admin controlled the UI
- Wasted time debugging "missing fields"

### How to Add UserProfile Fields

**✅ CORRECT** - Edit `apps/user_profile/admin/users.py`:

```python
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Contact Information', {
            'fields': (
                'phone',
                'whatsapp',  # ← Add your field here
                'secondary_email',
                ...
            )
        }),
    )
```

**❌ WRONG** - Do NOT create another registration in `admin.py`:

```python
# This will cause conflicts! Don't do it!
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    ...
```

### Recent Changes (2026-01-08)

Added 4 new contact fields:
- `whatsapp`: Separate WhatsApp number (not reusing phone)
- `secondary_email`: Public/contact email (separate from account email)
- `secondary_email_verified`: OTP verification status (readonly - only system can set)
- `preferred_contact_method`: User's preferred contact channel (email/phone/whatsapp/discord/facebook)

### Verification

Run `python verify_admin_setup.py` to confirm:
- ✅ Only ONE admin is registered
- ✅ All expected fields are visible
- ✅ No conflicts exist

### Admin URLs

- User List: http://127.0.0.1:8000/admin/user_profile/userprofile/
- Edit User: http://127.0.0.1:8000/admin/user_profile/userprofile/{id}/change/

### For New Developers

If you see missing fields in the admin:
1. Check `apps/user_profile/admin/users.py` FIRST (not admin.py)
2. Add your field to the appropriate fieldset
3. Run `python verify_admin_setup.py` to confirm
4. Restart the Django server (`python manage.py runserver`)

### Migration Checklist

When adding UserProfile model fields:
- [ ] Create migration: `python manage.py makemigrations`
- [ ] Apply migration: `python manage.py migrate`
- [ ] Update `apps/user_profile/admin/users.py` fieldsets
- [ ] Update frontend form (settings_control_deck.html)
- [ ] Update backend view (public_profile_views.py)
- [ ] Run verification: `python verify_admin_setup.py`
- [ ] Test in admin panel at http://127.0.0.1:8000/admin

---

**Last Updated**: 2026-01-08  
**Reason**: Fixed duplicate UserProfile admin registration causing missing fields
