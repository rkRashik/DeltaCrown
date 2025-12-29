# UP_PHASE5B_PROFILE_CONTEXT.md

**Workstream:** 2 - Profile View Context & Privacy Enforcement  
**Date:** December 28, 2025  
**Status:** ✅ **COMPLETE**

---

## 🎯 OBJECTIVE

Update profile view to compute viewer-role permissions and pass explicit can_view_* flags to template for server-side privacy enforcement.

---

## ✅ ACTIONS COMPLETED

### 1. Permission Checker Service Created

**File:** `apps/user_profile/services/profile_permissions.py` (NEW - 168 lines)

**Class:** `ProfilePermissionChecker`

**Computed Permissions:**
| Permission Flag | Purpose | Logic |
|-----------------|---------|-------|
| `viewer_role` | String: owner/follower/visitor/anonymous | Computed from authentication and follow status |
| `is_own_profile` | Viewing own profile | `viewer.id == profile.user.id` |
| `can_view_profile` | Profile visible at all | Checks `PrivacySettings.profile_visibility` |
| `can_view_game_passports` | Show game passports | Checks `show_game_ids` setting |
| `can_view_wallet` | Show DeltaCoin balance | Owner only (always private) |
| `can_view_achievements` | Show badges/achievements | Checks `show_achievements` setting |
| `can_view_match_history` | Show match records | Checks `show_match_history` setting |
| `can_view_teams` | Show team memberships | Checks `show_teams` setting |
| `can_view_social_links` | Show social media | Checks `show_social_links` setting |
| `can_send_message` | Can send DM | Checks `allow_direct_messages` setting |
| `can_send_team_invite` | Can invite to team | Checks `allow_team_invites` setting |

**Viewer Roles:**
```python
# owner: viewing own profile (full access)
if viewer.id == profile.user.id:
    viewer_role = 'owner'

# follower: following the profile (follower-only access)
elif FollowService.is_following(viewer, profile.user):
    viewer_role = 'follower'

# visitor: logged in but not following (public access)
elif viewer.is_authenticated:
    viewer_role = 'visitor'

# anonymous: not logged in (public access)
else:
    viewer_role = 'anonymous'
```

**Privacy Enforcement:**
```python
# Example: Game Passports
def can_view_game_passports(self) -> bool:
    if self.is_owner:
        return True  # Owner always sees own passports
    if not self.privacy.show_game_ids:
        return False  # Setting disabled
    return self.can_view_profile()  # Profile not private
```

### 2. Profile View Updated

**File:** `apps/user_profile/views/fe_v2.py`

**Changes:**
1. **Import ProfilePermissionChecker** (Line 31)
2. **Compute permissions on every request** (Lines 68-73):
   ```python
   permission_checker = ProfilePermissionChecker(
       viewer=request.user if request.user.is_authenticated else None,
       profile=user_profile
   )
   permissions = permission_checker.get_all_permissions()
   ```
3. **Block private profiles** (Lines 75-81):
   ```python
   if not permissions['can_view_profile']:
       return render(request, 'user_profile/profile_private.html', {
           'profile_user': profile_user,
           'profile': user_profile,
           'viewer_role': permissions['viewer_role'],
       })
   ```
4. **Add permissions to context** (Line 92):
   ```python
   context.update(permissions)
   ```

**Template Now Receives:**
```python
{
    # Existing context from build_public_profile_context
    'display_name': 'JohnDoe',
    'avatar': '/media/avatars/...',
    'bio': 'Pro Valorant player',
    
    # NEW: Phase 5B permission flags
    'viewer_role': 'follower',
    'is_own_profile': False,
    'can_view_profile': True,
    'can_view_game_passports': True,
    'can_view_wallet': False,  # Owner only
    'can_view_achievements': True,
    'can_view_match_history': False,  # User disabled
    'can_view_teams': True,
    'can_view_social_links': True,
    'can_send_message': True,
    'can_send_team_invite': False,  # User disabled
}
```

---

## 📊 PRIVACY MATRIX

| Viewer Role | Profile Private | Profile Followers-Only | Profile Public |
|-------------|-----------------|------------------------|----------------|
| Owner | ✅ Full Access | ✅ Full Access | ✅ Full Access |
| Follower | ❌ Blocked | ✅ See Content* | ✅ See Content* |
| Visitor | ❌ Blocked | ❌ Blocked | ✅ See Content* |
| Anonymous | ❌ Blocked | ❌ Blocked | ✅ See Content* |

*Content visibility further controlled by individual show_* settings

| Section | Setting | Default | Owner Access |
|---------|---------|---------|--------------|
| Game Passports | `show_game_ids` | True | Always visible |
| Achievements | `show_achievements` | True | Always visible |
| Match History | `show_match_history` | True | Always visible |
| Teams | `show_teams` | True | Always visible |
| Social Links | `show_social_links` | True | Always visible |
| Wallet | (none) | N/A | **Always private** |

---

## 🔒 ENFORCEMENT MECHANISM

### Server-Side (View Level)

```python
# Phase 5B enforcement
permissions = ProfilePermissionChecker(viewer, profile).get_all_permissions()

if not permissions['can_view_profile']:
    return render('profile_private.html')  # Block access

context.update(permissions)  # Pass flags to template
```

### Template Level

```django-html
{% if can_view_game_passports %}
    <!-- Render passport cards -->
    {% for passport in game_profiles %}
        <div class="passport-card">...</div>
    {% endfor %}
{% else %}
    <div class="locked">🔒 Game Passports are Private</div>
{% endif %}

{% if can_view_wallet %}
    <!-- Only owner sees this -->
    <div class="wallet">{{ deltacoin_balance }} DC</div>
{% endif %}
```

**NO CSS-Only Privacy:**
```django-html
<!-- ❌ WRONG (Phase 4 and earlier) -->
<div class="wallet" :class="{ 'blurred': !isOwner }">
    {{ deltacoin_balance }} DC
</div>

<!-- ✅ CORRECT (Phase 5B) -->
{% if can_view_wallet %}
    <div class="wallet">{{ deltacoin_balance }} DC</div>
{% endif %}
```

---

## ⚠️ TEMPLATE UPDATES REQUIRED

Templates must be updated to check permission flags. Example checklist:

### profile.html / profile/public.html

| Section | Check Required | Status |
|---------|---------------|--------|
| Banner/Avatar | None (always visible if profile viewable) | ✅ OK |
| Display Name | None (always visible) | ✅ OK |
| Bio | None (always visible) | ✅ OK |
| Game Passports | `{% if can_view_game_passports %}` | ⚠️ TODO |
| Achievements | `{% if can_view_achievements %}` | ⚠️ TODO |
| Match History | `{% if can_view_match_history %}` | ⚠️ TODO |
| Teams | `{% if can_view_teams %}` | ⚠️ TODO |
| Social Links | `{% if can_view_social_links %}` | ⚠️ TODO |
| Wallet | `{% if can_view_wallet %}` | ⚠️ TODO |
| Follow Button | `{% if not is_own_profile %}` | ⚠️ TODO (+ wire to real API) |
| Message Button | `{% if can_send_message %}` | ⚠️ TODO |
| Team Invite | `{% if can_send_team_invite %}` | ⚠️ TODO |

---

## 🚀 WHAT'S NOW IMPOSSIBLE TO BREAK

1. **No CSS-only privacy** - Sections not rendered at all if private
2. **No client-side permission logic** - All computed server-side
3. **No dual privacy sources** - ProfilePermissionChecker uses PrivacySettings only
4. **No permission guessing** - Explicit can_view_* flags for every section
5. **No role confusion** - viewer_role clearly identified (owner/follower/visitor/anonymous)

---

## 📝 INTEGRATION NOTES

### For Template Developers

Always check permission before rendering sensitive content:

```django-html
{% if can_view_social_links %}
    <div class="social-links">
        {% if profile.youtube_link %}
            <a href="{{ profile.youtube_link }}">YouTube</a>
        {% endif %}
    </div>
{% else %}
    <p class="text-muted">Social links are private.</p>
{% endif %}
```

### For Backend Developers

To add new privacy settings:

1. Add field to `PrivacySettings` model
2. Add `can_view_new_feature()` method to `ProfilePermissionChecker`
3. Include in `get_all_permissions()` return dict
4. Update template with `{% if can_view_new_feature %}`

---

## ⏭️ NEXT STEPS

**Remaining Work:**
- Workstream 3: Fix follow button (remove fake setTimeout, wire real API)
- Workstream 4: Update profile.html template with permission checks
- Workstream 5: Add "View Profile" button to settings page

**Status:** Workstream 2 complete. Server-side permission enforcement ready. Template updates pending in Workstream 4.
