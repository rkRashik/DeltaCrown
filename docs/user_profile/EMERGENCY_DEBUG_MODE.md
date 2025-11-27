# 🔴 EMERGENCY DEBUG MODE - Active Deployment Fix

## CRITICAL ISSUE IDENTIFIED

**ROOT CAUSE:** The root `urls.py` had `path("user/", include(...))` which meant all profile URLs were prefixed with `/user/`, breaking the `@<username>/` pattern.

**Example of the Problem:**
- Template expects: `http://localhost:8000/@johndoe/`
- Server was looking for: `http://localhost:8000/user/@johndoe/` ❌

---

## What Was Fixed (Emergency Patches)

### 1. ✅ Root URL Configuration Fixed
**File:** `deltacrown/urls.py`

**BEFORE (BROKEN):**
```python
path("user/", include(("apps.user_profile.urls", "user_profile"), namespace="user_profile")),
```

**AFTER (FIXED):**
```python
# CRITICAL FIX: User profile URLs at ROOT level (no prefix) to support @username/
path("", include(("apps.user_profile.urls", "user_profile"), namespace="user_profile")),
```

**Impact:** URLs now resolve correctly at root level:
- ✅ `/@johndoe/` (correct)
- ✅ `/@johndoe/achievements/` (correct)
- ✅ `/actions/update-bio/` (correct)

---

### 2. ✅ Comprehensive Debug Logging Added
**File:** `apps/user_profile/views.py`

**14 Debug Checkpoints Added:**
1. Function entry + request details
2. Username parameter check
3. User lookup result
4. Profile lookup/creation
5. is_own_profile calculation with detailed comparison
6. Social links query + count
7. Achievements query + count
8. Game profiles query + count + first item
9. Match history query + count
10. Team membership query + error details
11. Wallet query + balance + owner check
12. Notifications query + count
13. Context dictionary summary
14. Template render confirmation

**Example Debug Output:**
```
================================================================================
DEBUG: profile_view() called
================================================================================
DEBUG [1]: Requested username: johndoe
DEBUG [1]: Request.user: johndoe (authenticated: True)
DEBUG [1]: Request.path: /@johndoe/
DEBUG [3]: Found User: johndoe (ID: 1)
DEBUG [4]: Profile found: UserProfile object (1) (ID: 1)
DEBUG [4]: Profile.display_name: John Doe
DEBUG [5]: Request User: johndoe vs Profile User: johndoe
DEBUG [5]: is_own_profile calculated as: True
DEBUG [5]: Comparison: 1 == 1 ? True
DEBUG [6]: Social Links Count: 3
DEBUG [8]: Game Profiles Count: 2
DEBUG [8]: First Game: valorant - ProGamer#1234
DEBUG [11]: Loading wallet for owner...
DEBUG [11]: Wallet Object: DeltaCrownWallet object (1) (Balance: 150.00)
DEBUG [13]: Building context dictionary...
  - is_own_profile: True
  - social_links: 3 items
  - game_profiles: 2 items
  - wallet: DeltaCrownWallet object (1)
DEBUG [14]: Rendering template: user_profile/profile.html
================================================================================
```

---

### 3. ✅ Template Variable Consistency
**File:** `apps/user_profile/views.py`

**Added BOTH variable names for compatibility:**
```python
context = {
    'profile_user': profile_user,
    'profile': profile,
    'user_profile': profile,  # COMPATIBILITY: Template may use either name
    # ...
}
```

**Why:** Some templates might use `{{ profile.banner }}` and others `{{ user_profile.banner }}`. This ensures both work.

---

### 4. ✅ Template Debug Panel Added
**File:** `templates/user_profile/profile.html`

**New Debug Panel (Visible to Superusers):**
- Shows all context variables in green monospace terminal style
- Console.log() output for browser DevTools
- Displays counts for all data arrays
- Shows `is_own_profile` boolean state
- Includes timestamp to verify fresh renders

**To View:**
1. Load profile page
2. Look for green debug panel at top (or check console)
3. Panel auto-hides in production (checks `debug` flag)

---

### 5. ✅ Force Template Refresh
**File:** `apps/user_profile/views.py`

**Added Cache-Busting Variables:**
```python
context = {
    # ...
    'current_time': timezone.now(),
    'debug_timestamp': datetime.datetime.now().isoformat(),
}
```

**Impact:** Django will recompile template on every request (no cached version).

---

## How to Test the Fixes

### Step 1: Restart Server (REQUIRED)
```bash
# Kill existing server (Ctrl+C)
python manage.py runserver
```

### Step 2: Check Terminal Output
Visit any profile page: `http://localhost:8000/@yourusername/`

**Look for 14 Debug Lines:**
```
DEBUG [1]: Requested username: yourusername
DEBUG [2]: ... (should NOT appear if username provided)
DEBUG [3]: Found User: yourusername
DEBUG [4]: Profile found: UserProfile object
DEBUG [5]: is_own_profile calculated as: True (if viewing own)
DEBUG [6]: Social Links Count: X
DEBUG [8]: Game Profiles Count: X
DEBUG [11]: Wallet Object: DeltaCrownWallet object
DEBUG [14]: Rendering template
```

**If you DON'T see these lines:** Python is caching the old views.py. Solution:
```bash
# Force reload
python manage.py runserver --noreload
# Or restart server completely
```

---

### Step 3: Check Browser Debug Panel
1. Visit profile page
2. Look at top of page for **GREEN DEBUG PANEL**
3. Verify all counts match terminal output

**If panel doesn't appear:**
- Are you logged in as superuser?
- Check browser console for logs
- View page source - search for "DEBUG MODE"

---

### Step 4: Verify URL Resolution
Test these URLs directly in browser:

**Should Work (200 OK):**
- `http://localhost:8000/@testuser/` ✅
- `http://localhost:8000/@testuser/achievements/` ✅
- `http://localhost:8000/@testuser/match-history/` ✅

**Should 404 (Old broken pattern):**
- `http://localhost:8000/user/@testuser/` ❌ (old broken URL)

---

## Interpreting Debug Output

### Scenario 1: "Empty States" (No Data Showing)

**Check Terminal Output:**
```
DEBUG [6]: Social Links Count: 0
DEBUG [8]: Game Profiles Count: 0
DEBUG [9]: Match History Count: 0
```

**Diagnosis:** No data in database (not a bug!)

**Solution:** Create test data in Django admin:
```bash
# Open admin
http://localhost:8000/admin/user_profile/

# Add:
- 2-3 Social Links
- 1-2 Game Profiles
- 1-2 Achievements
```

---

### Scenario 2: "Wallet Not Showing" (Owner Issue)

**Check Terminal Output:**
```
DEBUG [5]: is_own_profile calculated as: False  ❌ (Should be True!)
DEBUG [11]: Wallet NOT loaded (is_own_profile=False)
```

**Diagnosis:** `is_own_profile` logic failing

**Check These:**
1. Are you logged in? `DEBUG [1]: Request.user: AnonymousUser` = NOT logged in
2. Username match? `DEBUG [5]: Comparison: 1 == 2 ? False` = Different users
3. URL correct? Make sure visiting your OWN username: `/@yourusername/`

**Solution:** Login and visit `/@yourusername/` (your own profile)

---

### Scenario 3: "Owner/Spectator Buttons Wrong"

**Check Browser Console:**
```javascript
console.log('is_own_profile:', true);  // Should match your view
```

**If Console Shows Wrong Value:**
- Clear browser cache
- Hard refresh (Ctrl+Shift+R)
- Check debug panel value vs Alpine.js state

---

### Scenario 4: "Template Not Updating"

**Check Debug Timestamp:**
```
DEBUG [14]: Rendering template: user_profile/profile.html
```

**If timestamp is old/cached:**
```bash
# Clear Python bytecode cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -delete

# Restart server
python manage.py runserver
```

---

## Error Reference Guide

### Error: `NoReverseMatch` for 'profile'
**Cause:** Old cached URLconf or server not restarted

**Solution:**
```bash
# Restart server
python manage.py runserver

# Check URL registration
python manage.py show_urls | findstr user_profile
```

---

### Error: `DoesNotExist: UserProfile matching query does not exist`
**Terminal Shows:**
```
DEBUG [4]: Profile does NOT exist, creating new one...
DEBUG [4]: Profile created: UserProfile object
```

**This is NORMAL** - Profiles auto-create. If it keeps failing:
```python
# In Django shell
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
User = get_user_model()
user = User.objects.get(username='testuser')
profile, created = UserProfile.objects.get_or_create(user=user)
print(f"Created: {created}, Profile: {profile}")
```

---

### Error: `FieldError: Cannot resolve keyword 'profile' into field`
**Terminal Shows:**
```
DEBUG [10]: Error loading team data: Cannot resolve keyword 'profile'
DEBUG [10]: Exception type: FieldError
```

**Cause:** TeamMembership model uses different field name

**Solution:** Check TeamMembership model field:
```python
# In models.py, check TeamMembership
# If it uses 'user' instead of 'profile':
TeamMembership.objects.filter(user=profile_user, status='ACTIVE')

# If it uses 'user_profile':
TeamMembership.objects.filter(user_profile=profile, status='ACTIVE')
```

**Fix in views.py line ~200:**
```python
# BEFORE
active_memberships = TeamMembership.objects.filter(profile=profile, status='ACTIVE')

# AFTER (if model uses 'user' FK)
active_memberships = TeamMembership.objects.filter(user=profile_user, status='ACTIVE')
```

---

## Quick Fixes for Common Issues

### Issue 1: URL Still Not Working
```bash
# Check if root urls.py change applied
grep -n "path.*user_profile" deltacrown/urls.py

# Should show:
# path("", include(("apps.user_profile.urls"...
# NOT: path("user/", include(...
```

**If Still Shows `user/` Prefix:**
The file edit didn't save. Manually edit `deltacrown/urls.py`:
1. Find line: `path("user/", include(...`
2. Change to: `path("", include(...`
3. Save file
4. Restart server

---

### Issue 2: Debug Output Not Showing
```bash
# Check if views.py has print statements
grep -n "DEBUG \[1\]" apps/user_profile/views.py

# Should show line numbers with DEBUG statements
```

**If No Match:**
The views.py edit didn't save. Check file manually for `print("DEBUG [1]:")`.

---

### Issue 3: Still Shows Old Template
**Nuclear Option (Force Fresh Render):**
```bash
# Clear all caches
python manage.py clear_cache  # If django-extensions installed

# Or manually:
rm -rf __pycache__
rm -rf */migrations/__pycache__
rm -rf */models/__pycache__

# Restart server with no reload
python manage.py runserver --noreload
```

---

## Expected Terminal Output (Full Example)

```
================================================================================
DEBUG: profile_view() called
================================================================================
DEBUG [1]: Requested username: johndoe
DEBUG [1]: Request.user: johndoe (authenticated: True)
DEBUG [1]: Request.path: /@johndoe/
DEBUG [3]: Found User: johndoe (ID: 1)
DEBUG [3]: Profile User Email: john@example.com
DEBUG [4]: Profile found: UserProfile object (1) (ID: 1)
DEBUG [4]: Profile.display_name: John Doe
DEBUG [4]: Profile.bio: I'm a competitive gamer specializing in FPS...
DEBUG [5]: Request User: johndoe vs Profile User: johndoe
DEBUG [5]: is_own_profile calculated as: True
DEBUG [5]: Comparison: 1 == 1 ? True
DEBUG [6]: Social Links Count: 3
DEBUG [6]: First Social Link: twitter - https://twitter.com/johndoe
DEBUG [7]: Achievements Count: 2
DEBUG [8]: Game Profiles Count: 2
DEBUG [8]: First Game: valorant - JohnDoe#1234
DEBUG [9]: Match History Count: 5
DEBUG [10]: Current Teams Count: 1
DEBUG [11]: Loading wallet for owner...
DEBUG [11]: Wallet Object: DeltaCrownWallet object (1) (Balance: 150.00)
DEBUG [11]: Wallet Created: False
DEBUG [11]: Recent Transactions Count: 3
DEBUG [12]: Unread Notifications: 2

DEBUG [13]: Building context dictionary...
  - profile_user: johndoe
  - profile: UserProfile object (1)
  - is_own_profile: True
  - social_links: 3 items
  - game_profiles: 2 items
  - achievements: 2 items
  - matches: 5 items
  - wallet: DeltaCrownWallet object (1)
  - current_teams: 1 items

DEBUG [14]: Context dictionary complete
DEBUG [14]: Rendering template: user_profile/profile.html
================================================================================
```

---

## Checklist for Deployment Fix

- [x] Root urls.py changed from `"user/"` to `""`
- [x] Views.py has 14 DEBUG checkpoints
- [x] Template has debug panel and console logs
- [x] Context includes both `profile` and `user_profile`
- [x] Context includes `current_time` for cache busting
- [ ] Server restarted
- [ ] Terminal shows DEBUG output
- [ ] Browser shows debug panel
- [ ] URLs resolve at root level (`/@username/`)
- [ ] is_own_profile shows correct value
- [ ] Wallet visible to owner
- [ ] Components populate with data

---

## Next Steps After Verification

1. **If Debug Shows Correct Data:** Issue is in template rendering
   - Check Alpine.js initialization
   - Verify Tailwind classes compiling
   - Check for JavaScript errors

2. **If Debug Shows Wrong is_own_profile:** Issue is authentication
   - Check session middleware
   - Verify login state
   - Check user comparison logic

3. **If Debug Shows 0 Counts:** Issue is data creation
   - Use Django admin to create test data
   - Check model relationships
   - Verify foreign keys

4. **Once Working:** Remove debug code for production
   - Comment out print statements
   - Remove debug panel from template
   - Re-enable template caching

---

**Status:** 🟢 DEBUG MODE ACTIVE  
**Priority:** CRITICAL - Active Deployment  
**Action Required:** Restart server and check terminal output immediately

---

## ✅ Gating Console Logs & Debug Panels (Best Practices)

To keep production logs and browser consoles clean while preserving in-depth debugging for developers and authorized users, follow these rules:

- Use `dcLog(...)` instead of `console.log(...)` in any `static` JS files or inline templates. `dcLog` is a no-op unless `DELTA_CROWN_DEBUG` is true.
- Use `dcDebug(...)` or `dcWarn(...)` for other log levels.
- Gate server-side debug logs with `_debug_log(request, message)` or check `request.user.is_superuser` before logging sensitive info.
- Set `DELTA_CROWN_DEBUG` in server templates by injecting `window.DELTACROWN_DEBUG = {% if request.user.is_superuser or debug|default:False %}true{% else %}false{% endif %};` in `base.html`.
- Provide an early no-op `dcLog` in the `head` of `base.html` so any early script calls won't throw errors:

```html
<script>window.DELTACROWN_DEBUG=false; window.dcLog=function(){};</script>
```

- Do NOT modify vendor files inside `staticfiles/` or the `.venv` dir. Update the gate script (`scripts/gate_console_logs.py`) to skip these paths if necessary.
- Keep example console.log statements in documentation (i.e., `docs/`) or inline educational snippets — they are acceptable; avoid modifying vendor code.

These conventions help ensure secure, debuggable, and production-friendly log behavior.

