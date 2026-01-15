# UP.3 HOTFIX #3 - Testing Checklist
**Date**: 2026-01-15  
**Test Environment**: Local Development  
**Tester**: _______________  

---

## Pre-Test Setup

### Database State
- [ ] Migration `0069_up3_hotfix3_competitive_goal.py` applied
- [ ] Run `python manage.py migrate user_profile` - Status: ______
- [ ] Verify migration in database:
  ```sql
  PRAGMA table_info(user_profile_userprofile);
  -- OR for PostgreSQL:
  \d user_profile_userprofile
  ```
  - [ ] Column `competitive_goal` exists (VARCHAR 160)

### Server State
- [ ] Run `python manage.py check` - Status: ______
- [ ] Server started: `python manage.py runserver`
- [ ] No startup errors in console
- [ ] Test user exists: `rkrashik` (or create one)

---

## P0 Tests (BLOCKING - Must Pass)

### Test 1: /me/settings/ Page Load
**Objective**: Verify GameProfile ImportError is fixed

**Steps**:
1. Navigate to: `http://127.0.0.1:8000/me/settings/`
2. Observe page load (should succeed, not crash)

**Expected Result**:
- [ ] HTTP 200 response
- [ ] Page renders completely
- [ ] No "ImportError: cannot import name 'GameProfile'" in console
- [ ] No error messages displayed to user

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

**If FAIL**: Check server logs for traceback

---

### Test 2: /@username/ Page Load
**Objective**: Verify NoReverseMatch error is fixed

**Steps**:
1. Navigate to: `http://127.0.0.1:8000/@rkrashik/` (or your test user)
2. Observe page load (should succeed, not crash)

**Expected Result**:
- [ ] HTTP 200 response
- [ ] Page renders completely
- [ ] No "NoReverseMatch: Reverse for 'team_detail'" in console
- [ ] Home Team displays (clickable link OR plain text)

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

**If FAIL**: Check server logs for URL resolution errors

---

## P1 Tests (IMPORTANT - Feature Verification)

### Test 3: Settings Page - Player Summary Counter
**Objective**: Verify counter format is "X / 320" (with spaces)

**Steps**:
1. Navigate to `/me/settings/`
2. Locate "Player Summary" section
3. Check character counter display

**Expected Result**:
- [ ] Counter shows "0 / 320" when empty (NOT "0/320 characters")
- [ ] Counter format: `<span id="summary-current">0</span> / 320`

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

---

### Test 4: Settings Page - Competitive Goal Section
**Objective**: Verify new Competitive Goal section exists

**Steps**:
1. Navigate to `/me/settings/`
2. Scroll to About section
3. Locate "Competitive Goal" panel (orange bullseye icon)

**Expected Result**:
- [ ] Section exists with heading "Competitive Goal"
- [ ] Bullseye icon (`<i class="fa-solid fa-bullseye">`)
- [ ] Textarea field with placeholder text
- [ ] Character counter showing "0 / 160"
- [ ] Helper text: "Be specific — what's your next milestone?"

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

---

### Test 5: Competitive Goal - Live Counter
**Objective**: Verify counter updates as user types

**Steps**:
1. Navigate to `/me/settings/`
2. Type in "Competitive Goal" textarea: "Reach Diamond rank this season"
3. Observe counter

**Expected Result**:
- [ ] Counter updates live (e.g., "30 / 160" for 30 chars)
- [ ] Counter turns yellow at ~112 chars (70%)
- [ ] Counter turns red at ~144 chars (90%)

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

**Browser Console Errors**: _______________________________________________

---

### Test 6: Competitive Goal - Form Saving
**Objective**: Verify competitive_goal saves to database

**Steps**:
1. Navigate to `/me/settings/`
2. Enter in "Competitive Goal": "Win a regional tournament by March"
3. Click "Save Changes"
4. Observe success message
5. Reload page (`Ctrl+R`)

**Expected Result**:
- [ ] Success message displays: "Profile updated successfully"
- [ ] After reload, textarea contains saved text
- [ ] Counter shows correct character count

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

**Database Verification**:
```python
# Run in Django shell: python manage.py shell
from apps.user_profile.models import UserProfile
from django.contrib.auth.models import User
user = User.objects.get(username='rkrashik')
profile = user.userprofile
print(profile.competitive_goal)  # Should print saved text
```
- [ ] Database contains saved value

---

### Test 7: Public Profile - Competitive Goal Display
**Objective**: Verify competitive_goal appears on public profile

**Steps**:
1. Set competitive_goal in settings (Test 6)
2. Navigate to `/@rkrashik/` (your test user)
3. Scroll to About section
4. Locate "Competitive Goal" card

**Expected Result**:
- [ ] Orange gradient card with bullseye icon
- [ ] Heading: "COMPETITIVE GOAL"
- [ ] Card contains: "Win a regional tournament by March"
- [ ] Card has border `border-orange-500/20`

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

---

### Test 8: Public Profile - Empty Competitive Goal
**Objective**: Verify section is hidden when competitive_goal is empty

**Steps**:
1. Navigate to `/me/settings/`
2. Clear "Competitive Goal" textarea (delete all text)
3. Save changes
4. Navigate to `/@rkrashik/`
5. Check About section

**Expected Result**:
- [ ] "Competitive Goal" card does NOT appear
- [ ] No empty orange boxes or placeholders

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

---

### Test 9: Home Team Link - Safe Rendering
**Objective**: Verify Home Team doesn't crash if URL missing

**Steps**:
1. Ensure test user has `primary_team` set (in admin or via form)
2. Navigate to `/@rkrashik/`
3. Locate "Home Team" in Competitive DNA section

**Expected Result**:
- [ ] Home Team displays (either as link or plain text)
- [ ] If clickable: `<a href="/teams/some-slug/">Team Name</a>`
- [ ] If plain: `<div>Team Name</div>`
- [ ] NO crash or "NoReverseMatch" error

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

**Link Behavior**: [ ] Clickable  [ ] Plain Text

---

### Test 10: Playstyle Badge Display
**Objective**: Verify Playstyle badge appears on public profile

**Prerequisites**: Set `play_style` field for test user (in admin)

**Steps**:
1. In admin: Set `play_style` to a value (e.g., "Aggressive")
2. Navigate to `/@rkrashik/`
3. Scroll to About section
4. Locate "Playstyle" section

**Expected Result**:
- [ ] Purple badge with gamepad icon
- [ ] Badge contains play_style value (e.g., "Aggressive")
- [ ] Badge styling: `bg-purple-500/10 border-purple-500/30`

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

---

## P2 Tests (POLISH - Nice to Have)

### Test 11: Competitive Goal - Validation
**Objective**: Verify 160 character limit enforced

**Steps**:
1. Navigate to `/me/settings/`
2. Enter 161+ characters in "Competitive Goal" (paste long text)
3. Attempt to save

**Expected Result**:
- [ ] Form validation error displays
- [ ] Error message: "Competitive Goal must be 160 characters or less (currently XXX)"
- [ ] Form does NOT save
- [ ] User stays on settings page

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

---

### Test 12: Admin Interface - Competitive Goal
**Objective**: Verify admin shows competitive_goal field

**Steps**:
1. Navigate to `/admin/user_profile/userprofile/1/change/`
2. Locate "Public Identity" fieldset
3. Check for "Competitive goal" field

**Expected Result**:
- [ ] Field appears after "Profile story"
- [ ] Textarea input (rows=1 or similar)
- [ ] Help text: "Short-term competitive goal or aspiration (120-160 characters)"
- [ ] Can edit and save from admin

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

---

### Test 13: Player Summary - Helper Text
**Objective**: Verify updated helper text

**Steps**:
1. Navigate to `/me/settings/`
2. Locate "Player Summary" section
3. Read helper text below textarea

**Expected Result**:
- [ ] Helper text: "Keep it short — this shows on your public profile."
- [ ] Icon: `<i class="fa-solid fa-info-circle text-cyan-400">`
- [ ] Bold emphasis on "Keep it short"

**Actual Result**: _______________________________________________

**Status**: [ ] PASS  [ ] FAIL

---

### Test 14: Label Updates
**Objective**: Verify label name changes throughout UI

**Steps**:
1. Check `/me/settings/` and `/@rkrashik/` for labels
2. Locate fields: Country, Home Team, Signature Game

**Expected Result**:

| Location | Old Label | New Label | Status |
|----------|-----------|-----------|--------|
| Settings | Nationality | Country | [ ] PASS |
| Settings | Primary Team | Home Team | [ ] PASS |
| Settings | Primary Game | Signature Game | [ ] PASS |
| Public Profile | Nationality | Country | [ ] PASS |
| Public Profile | Primary Team | Home Team | [ ] PASS |
| Public Profile | Primary Game | Signature Game | [ ] PASS |

**Actual Result**: _______________________________________________

**Overall Status**: [ ] PASS  [ ] FAIL

---

## Regression Tests

### Test 15: Existing Fields - No Breakage
**Objective**: Verify existing About fields still work

**Steps**:
1. Navigate to `/me/settings/`
2. Test editing:
   - [ ] Player Summary (profile_story) - Saves correctly
   - [ ] Pronouns - Saves correctly
   - [ ] Country - Saves correctly
   - [ ] Home Team - Saves correctly
   - [ ] Signature Game - Saves correctly

**Status**: [ ] PASS  [ ] FAIL

---

### Test 16: Public Profile - Other Sections
**Objective**: Verify no layout breakage in other sections

**Steps**:
1. Navigate to `/@rkrashik/`
2. Check all sections render correctly:
   - [ ] Hero section
   - [ ] Identity context (Country flag, etc.)
   - [ ] Stats context
   - [ ] Relationship context

**Status**: [ ] PASS  [ ] FAIL

---

## Cross-Browser Testing (Optional)

### Browsers Tested
- [ ] Chrome - Version: ______ - Status: ______
- [ ] Firefox - Version: ______ - Status: ______
- [ ] Safari - Version: ______ - Status: ______
- [ ] Edge - Version: ______ - Status: ______

---

## Performance Tests

### Page Load Times
- [ ] `/me/settings/` - Load Time: ______ms
- [ ] `/@rkrashik/` - Load Time: ______ms

**Threshold**: <2000ms acceptable

---

## Console Errors

### JavaScript Errors
- [ ] No errors in browser console (F12 → Console tab)
- Errors Found: _______________________________________________

### Network Errors
- [ ] No 500/404 errors in Network tab
- Errors Found: _______________________________________________

---

## Test Summary

### P0 Tests (2 total)
- Passed: ___ / 2
- Failed: ___ / 2
- Status: [ ] ALL PASS  [ ] BLOCKERS EXIST

### P1 Tests (8 total)
- Passed: ___ / 8
- Failed: ___ / 8
- Status: [ ] ALL PASS  [ ] ISSUES EXIST

### P2 Tests (4 total)
- Passed: ___ / 4
- Failed: ___ / 4
- Status: [ ] ALL PASS  [ ] POLISH NEEDED

### Overall Result
- Total Tests: 16
- Passed: ___ / 16
- Failed: ___ / 16
- **Final Status**: [ ] APPROVED FOR PRODUCTION  [ ] NEEDS FIXES

---

## Issues Found

### Critical Issues (Block Deployment)
1. _______________________________________________
2. _______________________________________________

### Non-Critical Issues (Can Deploy)
1. _______________________________________________
2. _______________________________________________

---

## Sign-Off

**Tester Name**: _______________  
**Date**: _______________  
**Time**: _______________  

**Recommendation**:
- [ ] APPROVE - Ready for production deployment
- [ ] APPROVE WITH CONDITIONS - Minor issues, can deploy with monitoring
- [ ] REJECT - Critical issues found, needs fixes before deployment

**Comments**: _______________________________________________

---

**END OF CHECKLIST**
