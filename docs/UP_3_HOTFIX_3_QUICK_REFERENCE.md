# UP.3 HOTFIX #3 - Quick Reference Guide

## What Changed

### 🐛 Bug Fixes
1. **GameProfile Import** - Changed from `apps.games.models` to dynamic `apps.get_model()`
2. **Team URL Crash** - Added safe URL generation with try/except wrapper

### ✨ New Features
- **competitive_goal** field (160 chars) - Short-term competitive aspiration

### 🎨 UX Improvements
- Counter format: "X / 320" (with spaces)
- Label updates: Country, Home Team, Signature Game
- Improved helper text
- Playstyle badge display

---

## Files Modified

### Backend (3 files)
```
apps/user_profile/models_main.py         (Lines 236-249)
apps/user_profile/views/public_profile_views.py  (Lines 1050-1062, 1515-1517)
apps/user_profile/forms.py               (Lines 488-524, 563-569)
```

### Frontend (2 files)
```
templates/user_profile/profile/public_profile.html  (Lines 515-530, 647-682)
templates/user_profile/profile/settings_control_deck.html  (Lines 879-917, 2423-2436)
```

### Admin (1 file)
```
apps/user_profile/admin/users.py         (Line 169)
```

### Migration (1 file)
```
apps/user_profile/migrations/0069_up3_hotfix3_competitive_goal.py
```

---

## Code Snippets

### Using competitive_goal in Templates
```django
{% if user_profile.competitive_goal %}
<div class="competitive-goal-card">
    {{ user_profile.competitive_goal }}
</div>
{% endif %}
```

### Using competitive_goal in Views
```python
from apps.user_profile.models import UserProfile

profile = UserProfile.objects.get(user=request.user)
goal = profile.competitive_goal  # Returns "" if not set
```

### Safe Team URL Pattern
```python
# View
primary_team_url = None
if user_profile.primary_team:
    try:
        primary_team_url = reverse('teams:team_detail', kwargs={'slug': user_profile.primary_team.slug})
    except Exception:
        pass

# Template
{% if primary_team_url %}
<a href="{{ primary_team_url }}">{{ team.name }}</a>
{% else %}
{{ team.name }}
{% endif %}
```

---

## Database Schema

```sql
-- competitive_goal column
ALTER TABLE user_profile_userprofile ADD COLUMN competitive_goal VARCHAR(160) DEFAULT '';
```

**Field Properties**:
- Type: CharField
- Max Length: 160
- Blank: True
- Default: "" (empty string)
- Null: False

---

## Form Validation

**Max Length**: 160 characters  
**Validation Method**: `clean_competitive_goal()`  
**Error Message**: "Competitive Goal must be 160 characters or less (currently XXX)"

---

## Character Counters

### Player Summary
- **Max**: 320 characters
- **Format**: "X / 320"
- **JS Function**: `updateCharCount(input, 320, 'summary')`

### Competitive Goal
- **Max**: 160 characters
- **Format**: "X / 160"
- **JS Function**: `updateCharCount(input, 160, 'goal')`

---

## Admin Configuration

**Fieldset**: Public Identity  
**Position**: After `profile_story`  
**Description**: "Competitive goal is a short-term aspiration."

---

## Testing Commands

```bash
# Verify migration
python manage.py showmigrations user_profile

# Check for errors
python manage.py check

# Run dev server
python manage.py runserver

# Test endpoints
curl http://127.0.0.1:8000/me/settings/
curl http://127.0.0.1:8000/@rkrashik/
```

---

## Django Shell Testing

```python
python manage.py shell

# Test competitive_goal field
from apps.user_profile.models import UserProfile
from django.contrib.auth.models import User

user = User.objects.get(username='rkrashik')
profile = user.userprofile

# Set goal
profile.competitive_goal = "Reach Diamond rank this season"
profile.save()

# Verify
print(profile.competitive_goal)
# Output: "Reach Diamond rank this season"

# Test GameProfile import fix
from django.apps import apps
GameProfile = apps.get_model("user_profile", "GameProfile")
print(GameProfile)  # Should not raise ImportError
```

---

## Common Issues & Solutions

### Issue: "ImportError: cannot import name 'GameProfile'"
**Solution**: Use dynamic import:
```python
from django.apps import apps
GameProfile = apps.get_model("user_profile", "GameProfile")
```

### Issue: "NoReverseMatch: Reverse for 'team_detail'"
**Solution**: Generate URL in view with try/except:
```python
try:
    team_url = reverse('teams:team_detail', kwargs={'slug': team.slug})
except Exception:
    team_url = None
```

### Issue: Counter not updating
**Solution**: Check JS initialization:
```javascript
const goalInput = document.getElementById('competitive-goal-input');
if (goalInput) {
    updateCharCount(goalInput, 160, 'goal');
}
```

---

## API Usage (if applicable)

```python
# GET /api/profiles/{username}/
{
    "username": "rkrashik",
    "competitive_goal": "Win a regional tournament by March",
    "profile_story": "Professional player with 5 years experience...",
    ...
}

# PATCH /api/profiles/{username}/
{
    "competitive_goal": "Reach Diamond rank this season"
}
```

---

## Related Documentation

- [UP_3_HOTFIX_3_DELIVERY_REPORT.md](UP_3_HOTFIX_3_DELIVERY_REPORT.md) - Full delivery report
- [UP_3_HOTFIX_3_TESTING_CHECKLIST.md](UP_3_HOTFIX_3_TESTING_CHECKLIST.md) - Testing guide
- [HOMEPAGE_V3_DOCUMENTATION.md](HOMEPAGE_V3_DOCUMENTATION.md) - Profile system overview
- [ADMIN_ORGANIZATION.md](ADMIN_ORGANIZATION.md) - Admin structure

---

## Git Commands

```bash
# View changes
git status
git diff apps/user_profile/

# Commit changes
git add apps/user_profile/
git add templates/user_profile/
git add docs/UP_3_HOTFIX_3*
git commit -m "UP.3 HOTFIX #3: Fix GameProfile import + team_detail crash + About UX improvements"

# Push to remote
git push origin main
```

---

## Rollback Plan (if needed)

```bash
# Rollback migration
python manage.py migrate user_profile 0068

# Revert code changes
git revert HEAD

# Or restore previous version
git checkout HEAD~1 -- apps/user_profile/
```

---

## Support Contacts

**Technical Issues**: UP.3 Development Team  
**Bug Reports**: GitHub Issues  
**Questions**: Project documentation or team chat

---

**Last Updated**: 2026-01-15  
**Version**: 1.0
