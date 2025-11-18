# Specification Updates Needed

This file tracks updates needed to sync specification documents with implementation changes completed on 2025-11-18.

## API_CONTRACTS.md

### Add to Leave Team Endpoint

```markdown
#### POST /teams/{slug}/leave/

**AJAX Request (JSON):**
- Detects via `X-Requested-With: XMLHttpRequest` header
- Content-Type: application/json
- Body: `{"reason": "optional leave reason"}`

**JSON Response:**
Success:
```json
{
  "success": true,
  "message": "You have successfully left the team.",
  "redirect_url": "/teams/"
}
```

Error - Captain Cannot Leave:
```json
{
  "success": false,
  "error": "Team captain cannot leave without transferring captaincy first.",
  "code": "CAPTAIN_CANNOT_LEAVE"
}
```

Error - Roster Locked:
```json
{
  "success": false,
  "error": "Cannot leave team while roster is locked for active tournament.",
  "code": "ROSTER_LOCKED"
}
```
```

## MODELS_SPEC.md

### Add to Utilities Section

```markdown
### Game Mapping Utility

**File:** `apps/teams/utils/game_mapping.py`

**Purpose:** Normalize legacy game codes to current game codes for backward compatibility.

**LEGACY_GAME_CODES Dictionary:**
- 'pubg-mobile' → 'PUBG'
- 'pubgm' → 'PUBG'
- 'csgo' → 'CS2'
- 'cs:go' → 'CS2'
- 'mobile-legends' → 'MLBB'
- 'ml' → 'MLBB'
- 'call-of-duty-mobile' → 'CODM'
- 'cod-mobile' → 'CODM'
- 'efootball-2024' → 'EFOOTBALL'
- 'free-fire' → 'FREEFIRE'
- 'fc-24' → 'FC26'
- 'fifa-24' → 'FC26'

**Functions:**

`normalize_game_code(game_code: str) -> str`
- Converts legacy game codes to current codes
- Case-insensitive
- Handles hyphens, underscores, spaces
- Returns original code if not in legacy map

`get_game_config(game_code: str) -> dict`
- Wrapper around game_config.GAME_ROSTER_RULES
- Normalizes game code first
- Returns default config for unknown games:
  ```python
  {
      'min_players': 1,
      'max_players': 10,
      'roles': ['Player'],
      'regions': [],
      'supports_substitutes': False
  }
  ```
```

## FORMS_SPEC.md

### Update TeamCreationForm

Add field:

```markdown
**accept_terms** (BooleanField)
- Required: True
- Label: "I accept the Terms & Conditions"
- Error message: "You must accept the terms and conditions to create a team."
- Widget: CheckboxInput
- Validation: Must be checked (True) to submit form
```

## VIEWS_SPEC.md

### Update leave_team_view

```markdown
#### leave_team_view(request, slug)

**URL:** `/teams/{slug}/leave/`
**Methods:** GET, POST
**Permissions:** User must be team member

**Functionality:**
- GET: Display leave confirmation page (HTML)
- POST (HTML): Process leave request, redirect to team list
- POST (AJAX/JSON): Process leave request, return JSON response

**Validations:**
1. User must be active team member
2. Captain cannot leave without transferring captaincy first
3. Cannot leave if roster is locked for active tournament

**AJAX Detection:**
- Checks `request.headers.get('X-Requested-With') == 'XMLHttpRequest'`
- Returns JsonResponse with success/error structure

**Success Actions:**
- Delete TeamMembership record
- Fire team.member_left event
- Invalidate team caches
- Return JSON for AJAX or redirect for HTML

**Error Responses:**
- CAPTAIN_CANNOT_LEAVE: Captain must transfer or disband team first
- ROSTER_LOCKED: Cannot leave during active tournament
- NOT_A_MEMBER: User is not a member of this team
```

### Update game_config.py

```markdown
#### get_game_config(game)

**Changes:**
- Now uses `normalize_game_code()` from game_mapping utility
- Returns default config instead of raising KeyError for unknown games
- Graceful degradation for unsupported games

**Default Config:**
```python
{
    'min_players': 1,
    'max_players': 10,
    'roles': ['Player'],
    'regions': [],
    'supports_substitutes': False
}
```
```

## TEMPLATES_SPEC.md

### Update team_create_esports.html

**Step 2 - Game Selection:**
- Now uses explicit game card images via {% static %} tags
- Image paths map to `static/img/game_cards/{GameName}.jpg`
- Fallback icon (`<i class="fas fa-gamepad">`) for unknown games

**Game Card Mappings:**
```django-html
VALORANT → img/game_cards/Valorant.jpg
CS2 → img/game_cards/CS2.jpg
DOTA2 → img/game_cards/Dota2.jpg
MLBB → img/game_cards/MobileLegend.jpg
PUBG → img/game_cards/PUBG.jpeg
FREEFIRE → img/game_cards/FreeFire.jpeg
EFOOTBALL → img/game_cards/efootball.jpeg
FC26 → img/game_cards/FC26.jpg
CODM → img/game_cards/CallOfDutyMobile.jpg
```

**Step 4 - Terms & Conditions:**
- Added terms acceptance checkbox
- Links to Terms & Conditions and Privacy Policy pages
- Required field (blocks submission if unchecked)
- Error message displays if validation fails

### Update _team_hub.html

**URL Fix:**
- Changed: `<a href="/user/{{ username }}/">`
- To: `<a href="{% url 'user_profile:profile' username=request.user.username %}">`
- Impact: Uses Django URL resolution instead of hardcoded paths

## JAVASCRIPT_SPEC.md

### team-leave-modern.js

**Verification:**
- Already correctly calls `/teams/${teamSlug}/leave/` endpoint
- Already sends AJAX request with proper headers
- Already handles JSON responses
- Already includes CSRF token

**No changes needed** - JavaScript already matches updated backend API.

### team-list-premium.js

**Verification:**
- quickJoin function already exported globally via `window.quickJoin = showQuickJoinModal;` (line 738)
- Function is available to inline onclick handlers

**No changes needed** - Export already exists.

## WORKFLOWS.md

### Team Leave Workflow - Update

**Add AJAX Flow:**

```markdown
#### Leave Team via JavaScript Modal (AJAX)

1. **User Action:**
   - Clicks "Leave Team" button in member dashboard
   - `showLeaveTeamModal()` called from team-leave-modern.js

2. **Frontend:**
   - Displays modal with warnings, consequences, optional reason textarea
   - User confirms by clicking "Leave Team" button in modal

3. **AJAX Request:**
   - POST to `/teams/{slug}/leave/`
   - Headers: `X-Requested-With: XMLHttpRequest`, `Content-Type: application/json`
   - Body: `{"reason": "optional text"}`

4. **Backend Validation:**
   - Check user is team member
   - Check user is not captain (or is only member)
   - Check roster is not locked

5. **Backend Response:**
   - Success: `{"success": true, "message": "...", "redirect_url": "/teams/"}`
   - Error: `{"success": false, "error": "...", "code": "ERROR_CODE"}`

6. **Frontend Handling:**
   - Success: Show toast, close modal, redirect to team list after 1.5s
   - Error: Show toast with error message, keep modal open

**Error Codes:**
- CAPTAIN_CANNOT_LEAVE
- ROSTER_LOCKED
- NOT_A_MEMBER
```

### Team Create Workflow - Update

**Add to Step 2:**
- Game selection now displays game card images from `static/img/game_cards/`
- Visual feedback improves game selection UX

**Add to Step 4:**
- Terms & conditions checkbox required before submission
- Form validation prevents submission without acceptance
- Links open Terms and Privacy Policy in new tabs

## BUGS_FIXED.md (NEW)

Create new file documenting all bugs fixed:

```markdown
# Bugs Fixed - November 18, 2025

## 1. Duplicate clean_logo() Method
**File:** apps/teams/forms.py
**Lines:** 95-110 (removed)
**Issue:** Two clean_logo methods caused validation conflicts
**Fix:** Removed first occurrence, kept stricter 2MB version

## 2. Duplicate leave_team_view() Function
**File:** apps/teams/views/public.py
**Lines:** 1247-1264 (removed)
**Issue:** Two identical views caused routing confusion
**Fix:** Removed first occurrence, enhanced second for JSON support

## 3. Hardcoded User Profile URL
**File:** templates/teams/_team_hub.html
**Issue:** `/user/{{username}}/` hardcoded instead of URL tag
**Fix:** Changed to `{% url 'user_profile:profile' username=request.user.username %}`

## 4. Incorrect Membership Field Reference
**File:** apps/teams/views/public.py
**Line:** 1420
**Issue:** `membership.user` should be `membership.profile`
**Fix:** Changed to correct field reference

## 5. String Status Comparison Instead of Enum
**File:** apps/teams/views/public.py
**Issue:** `status='ACTIVE'` instead of `TeamMembership.Status.ACTIVE`
**Fix:** Standardized to enum usage throughout

## 6. Missing quickJoin Export
**File:** static/teams/js/team-list-premium.js
**Issue:** quickJoin function not accessible globally
**Status:** ✅ Already exported at line 738 - no fix needed

## 7. Unsupported Game Code Crashes
**Files:** apps/teams/game_config.py, apps/teams/utils/game_mapping.py
**Issue:** KeyError when using legacy codes like 'pubg-mobile'
**Fix:** Created game_mapping utility with normalization and fallback

## 8. Import Errors Blocking Django Commands
**File:** apps/teams/utils/__init__.py
**Issue:** Importing non-existent functions (get_cache_stats, CacheKey, etc.)
**Fix:** Removed all non-existent imports, kept only what exists

## 9. Missing Game Card Images
**File:** templates/teams/team_create_esports.html
**Issue:** Generic image path `images/games/{value}.png` doesn't exist
**Fix:** Added explicit mappings to actual game_cards/*.jpg files

## 10. Missing Terms Acceptance
**Files:** apps/teams/forms.py, templates/teams/team_create_esports.html
**Issue:** No terms & conditions acceptance requirement
**Fix:** Added required accept_terms BooleanField and checkbox in Step 4
```

---

## Summary

All specification documents should be updated to reflect:
1. New game_mapping utility and its usage
2. Enhanced leave_team_view with JSON support
3. Terms & conditions acceptance field
4. Game card image mappings
5. Fixed URL references and field names
6. Legacy game code support

These updates ensure specifications remain the single source of truth and match the actual implementation.
