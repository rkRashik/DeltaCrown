# GP-2E Manual Verification Checklist

**Purpose:** Human verification of GP-2D/2E admin UX implementation before production deployment.

**When to use:** After GP-2D/2E code deployment, before marking as production-ready.

---

## Pre-Verification Setup

1. Ensure database has at least 3 passport-supported games:
   - Valorant (Riot Games)
   - CS2 (Steam)
   - MLBB (mobile MOBA)

2. Ensure GamePassportSchema exists for each game

3. Log in as staff user with admin access

---

## Test Scenarios

### ✅ Scenario 1: Valorant Passport Creation

1. Navigate to `/admin/user_profile/gameprofile/add/`
2. Select **Valorant** from game dropdown
3. **Expected behavior:**
   - ✅ IGN field label changes to "Riot ID" or "riot_name"
   - ✅ Discriminator field shows (for tagline)
   - ✅ Platform field is hidden (not needed for Riot)
   - ✅ Region dropdown appears with 6 options:
     - Americas
     - Europe
     - Asia-Pacific
     - Korea
     - LATAM
     - Brazil
   - ✅ Region is marked as required (red asterisk)
   - ✅ Role field is completely absent
4. Fill in identity:
   - IGN: `TestPlayer`
   - Discriminator: `NA1`
   - Region: `Americas`
5. Save
6. **Expected:**
   - ✅ Identity saved correctly
   - ✅ No JSON identity_data (uses columns)
   - ✅ Identity preview shows `testplayer#na1`

---

### ✅ Scenario 2: CS2 Passport Creation

1. Navigate to `/admin/user_profile/gameprofile/add/`
2. Select **CS2** from game dropdown
3. **Expected behavior:**
   - ✅ IGN field label changes to "Steam ID64" or "steam_id64"
   - ✅ Discriminator field is hidden (not needed)
   - ✅ Platform field is hidden (not needed)
   - ✅ Region dropdown does NOT appear (CS2 is global)
   - ✅ Role field is completely absent
4. Fill in identity:
   - IGN: `76561198012345678`
5. Save
6. **Expected:**
   - ✅ Identity saved correctly
   - ✅ Only steam_id64 populated (ign column)
   - ✅ discriminator, platform, region all NULL

---

### ✅ Scenario 3: MLBB Passport Creation

1. Navigate to `/admin/user_profile/gameprofile/add/`
2. Select **MLBB** from game dropdown
3. **Expected behavior:**
   - ✅ IGN field label changes to "User ID" or "mlbb_id"
   - ✅ Discriminator field shows (for zone_id)
   - ✅ Platform field is hidden
   - ✅ Region dropdown appears with 5 options:
     - Southeast Asia
     - North America
     - Europe
     - Latin America
     - South Asia
   - ✅ Region is marked as required
   - ✅ Role field is completely absent
4. Fill in identity:
   - IGN: `123456789`
   - Discriminator: `1234`
   - Region: `Southeast Asia`
5. Save
6. **Expected:**
   - ✅ Identity saved correctly
   - ✅ Identity preview shows `123456789(1234)`

---

### ✅ Scenario 4: Region Dropdown Validation

1. Create or edit any passport with regions (Valorant/MLBB)
2. Try to save without selecting region
3. **Expected:**
   - ❌ Form validation error
   - Message: "This field is required"

4. Try to manually submit invalid region via browser DevTools
5. **Expected:**
   - ❌ Server-side validation rejects it
   - Form does not save

---

### ✅ Scenario 5: Role Field Absence

1. Navigate to `/admin/user_profile/gameprofile/add/`
2. Inspect entire form
3. **Expected:**
   - ✅ No "role" or "main_role" field anywhere
   - ✅ Fieldset shows only: rank_name, rank_image, metadata
   - ✅ No role-related help text

4. View page source
5. **Expected:**
   - ✅ No `<input name="main_role">`
   - ✅ No `<select name="main_role">`

---

### ✅ Scenario 6: Identity Preview

1. Select any game
2. Fill in identity fields
3. **Expected:**
   - ✅ Identity preview box appears
   - ✅ Shows normalized identity_key (lowercase)
   - ✅ Format matches schema:
     - Valorant: `riot_name#tagline`
     - CS2: `steam_id64`
     - MLBB: `mlbb_id(zone_id)`

---

### ✅ Scenario 7: Game Dropdown Filtering

1. Navigate to `/admin/user_profile/gameprofile/add/`
2. Check game dropdown options
3. **Expected:**
   - ✅ Only games with `is_passport_supported=True` appear
   - ✅ No unsupported games visible
   - ✅ All 11 production games present (or 3 in test env):
     - Valorant
     - CS2
     - Dota 2
     - MLBB
     - COD Mobile
     - PUBG Mobile
     - Free Fire
     - EA FC
     - eFootball
     - R6 Siege
     - Rocket League

---

### ✅ Scenario 8: Schema Matrix Injection

1. Navigate to `/admin/user_profile/gameprofile/add/`
2. View page source (Ctrl+U)
3. Search for `gp-schema-matrix`
4. **Expected:**
   - ✅ `<script id="gp-schema-matrix" type="application/json">` exists
   - ✅ Contains JSON with all game schemas
   - ✅ Each game has:
     - `game_slug`
     - `game_name`
     - `region_choices` (array)
     - `identity_fields` (object)
     - `region_required` (boolean)

5. Open browser console
6. Run: `JSON.parse(document.getElementById('gp-schema-matrix').textContent)`
7. **Expected:**
   - ✅ Valid JSON object returns
   - ✅ No parse errors

---

### ✅ Scenario 9: JavaScript Loads Without Errors

1. Navigate to `/admin/user_profile/gameprofile/add/`
2. Open browser console (F12)
3. **Expected:**
   - ✅ No JavaScript errors
   - ✅ No 404 errors for `admin_game_passport.js`
   - ✅ Console log: "[GP-2D Admin] Schema matrix loaded: X games"

4. Select different games from dropdown
5. **Expected:**
   - ✅ Labels update immediately
   - ✅ Fields show/hide correctly
   - ✅ No console errors

---

### ✅ Scenario 10: Performance (Cached Schema)

1. Navigate to `/admin/user_profile/gameprofile/add/`
2. Note page load time
3. Refresh page 3-5 times
4. **Expected:**
   - ✅ Subsequent loads are faster (schema cached)
   - ✅ No database query for schema on repeat visits (check Django Debug Toolbar)

5. Wait 1+ hour, refresh again
6. **Expected:**
   - ✅ Cache expired, schema reloaded from DB
   - ✅ Page still works correctly

---

## Failure Scenarios to Test

### ❌ Test 1: Invalid Region Bypass Attempt

1. Edit passport with regions (Valorant)
2. Open browser DevTools → Elements
3. Add invalid region option: `<option value="FAKE">Fake Region</option>`
4. Select "Fake Region"
5. Try to save
6. **Expected:**
   - ❌ Server-side validation rejects
   - Form shows error: "Select a valid choice"

---

### ❌ Test 2: Missing Required Fields

1. Create new passport
2. Select game (Valorant)
3. Leave identity fields blank
4. Try to save
5. **Expected:**
   - ❌ Form validation errors
   - Required fields highlighted

---

## Post-Verification Checklist

After completing all scenarios:

- [ ] All 10 scenarios passed
- [ ] No JavaScript console errors
- [ ] No server errors in logs
- [ ] Schema matrix loads correctly
- [ ] Dynamic labels work for all games
- [ ] Region dropdowns populate correctly
- [ ] Role field completely absent
- [ ] Identity saved to columns (not JSON)
- [ ] Server-side validation works
- [ ] Performance acceptable (<500ms page load)

---

## Known Limitations

1. **Test DB Gaps:** Test environment may not have all 11 games
2. **Browser Cache:** Clear browser cache if labels don't update
3. **Django Cache:** Restart Redis/Memcached if schema changes not reflected

---

## Troubleshooting

**Problem:** Labels don't change when selecting game
- **Check:** Browser console for JavaScript errors
- **Check:** `admin_game_passport.js` loaded (Network tab)
- **Check:** Schema matrix element exists in page source

**Problem:** Region dropdown empty
- **Check:** GamePassportSchema exists for game
- **Check:** `region_choices` field populated in database
- **Check:** Browser console for errors

**Problem:** Role field still visible
- **Check:** Browser cache cleared
- **Check:** Correct template loaded (GP-2D override)
- **Check:** Static files collected (`python manage.py collectstatic`)

---

## Sign-Off

**Tester Name:** _________________

**Date:** _________________

**Environment:** [ ] Local [ ] Staging [ ] Production

**Result:** [ ] All tests passed [ ] Issues found (see notes)

**Notes:**
```
[Space for additional observations]
```

---

**Status:** ⏳ Ready for manual verification

**Next Step:** Assign to QA/operator for manual testing
