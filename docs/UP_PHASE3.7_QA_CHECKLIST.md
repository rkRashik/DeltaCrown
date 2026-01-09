# Phase 3.7 QA Checklist — JavaScript Hardening & Visitor Safety

**Status**: 🟡 In Progress  
**Mandatory Before**: Phase 4 (Activity Feed & Social Features)  
**Purpose**: Ensure profile.js never throws uncaught errors, blocks unauthorized actions, and fails gracefully

---

## ✅ **ACCEPTANCE CRITERIA**

All items must pass before Phase 3.7 is considered complete:

- [ ] **No uncaught JavaScript errors** in visitor mode (logged-out, incognito)
- [ ] **No uncaught JavaScript errors** in owner mode (logged-in as profile owner)
- [ ] **All mutation operations** guarded with `requireOwner()` check
- [ ] **All fetch calls** wrapped with `safeFetch()` for error handling
- [ ] **All DOM access** uses `safeGetById()` or `safeQuery()` helpers
- [ ] **No private data leakage** in console logs or HTML for visitors
- [ ] **No unauthorized network calls** initiated by visitors
- [ ] **Graceful degradation** when backend returns errors or missing data

---

## 🧪 **TEST SUITE**

### **1. Visitor Mode Tests** (Logged-Out / Different User)

**Setup**: Open profile in incognito mode OR log in as a different user  
**Browser Console**: Open DevTools Console (F12)  
**Expected Result**: **ZERO JavaScript errors** throughout all tests

#### Test 1.1: Basic Navigation
- [ ] Load profile page
- [ ] Check console for errors → **Should be clean**
- [ ] Click each tab: About, Overview, Career, Roster, Loadout
- [ ] Verify tab switching works without errors

#### Test 1.2: Modal Interactions (Should Block or Fail Gracefully)
- [ ] Attempt to open "Edit About" modal → Should be blocked/hidden for visitors
- [ ] Attempt to open "Manage Game Passports" modal → Should be blocked
- [ ] Attempt to open "Edit Highlights" modal → Should be blocked
- [ ] Attempt to open "Create Bounty" modal → Should be blocked
- [ ] Attempt to open "Edit Loadout" modal → Should be blocked
- [ ] Attempt to open "Manage Showcase" modal → Should be blocked
- [ ] Open "Video" modal (if video exists) → Should work, read-only
- [ ] Open "Followers" modal → Should work, read-only
- [ ] Open "Following" modal → Should work, read-only

#### Test 1.3: Network Activity Inspection
- [ ] Open DevTools Network tab
- [ ] Navigate through all tabs
- [ ] Click all visible interactive elements
- [ ] **Verify NO unauthorized POST/PUT/DELETE requests** initiated
- [ ] GET requests for public data (followers, highlights, etc.) are OK

#### Test 1.4: Console Log Inspection
- [ ] Check console for any logged sensitive data:
  - [ ] No wallet balances visible
  - [ ] No API keys or tokens visible
  - [ ] No private user IDs or emails visible
  - [ ] No backend error details exposed

#### Test 1.5: Rapid Interaction Stress Test
- [ ] Rapidly click between tabs (10+ times)
- [ ] Rapidly hover/click interactive elements
- [ ] Check console for errors → **Should be clean**

---

### **2. Owner Mode Tests** (Logged-In As Profile Owner)

**Setup**: Log in as the profile owner  
**Browser Console**: Open DevTools Console (F12)  
**Expected Result**: **ZERO JavaScript errors**, all features functional

#### Test 2.1: Modal Open/Close Operations
- [ ] Open About modal → No errors, form loads
- [ ] Close About modal → No errors
- [ ] Open Game Passports modal → No errors, list loads
- [ ] Close Game Passports modal → No errors
- [ ] Open Edit Highlights modal → No errors
- [ ] Close Edit Highlights modal → No errors
- [ ] Open Create Bounty modal → No errors, form loads
- [ ] Close Create Bounty modal → No errors
- [ ] Open Edit Loadout modal → No errors, hardware/configs load
- [ ] Close Edit Loadout modal → No errors
- [ ] Open Manage Showcase modal → No errors
- [ ] Close Manage Showcase modal → No errors

#### Test 2.2: Form Submissions (Create Operations)
- [ ] Add new game passport → Success toast, no errors
- [ ] Add new hardware item → Success toast, no errors
- [ ] Add new game config → Success toast, no errors
- [ ] Add new social link → Success toast, no errors
- [ ] Create new bounty → Success toast, no errors

#### Test 2.3: Form Submissions (Update Operations)
- [ ] Edit bio/about info → Save successfully, no errors
- [ ] Edit existing hardware item → Save successfully
- [ ] Edit existing game config → Save successfully

#### Test 2.4: Delete Operations
- [ ] Delete game passport → Confirm, deletes successfully
- [ ] Delete hardware item → Confirm, deletes successfully
- [ ] Delete game config → Confirm, deletes successfully
- [ ] Delete social link → Confirm, deletes successfully

#### Test 2.5: Match Progression Actions
- [ ] Start new match → No errors
- [ ] Submit proof → No errors
- [ ] Confirm result (accept) → No errors
- [ ] Confirm result (reject) → No errors
- [ ] Submit dispute → No errors

#### Test 2.6: Social Actions
- [ ] Follow a user → Success toast, no errors
- [ ] Unfollow a user → Success toast, no errors
- [ ] View followers list → Loads correctly, no errors
- [ ] View following list → Loads correctly, no errors

#### Test 2.7: Tab Switching with Hash URLs
- [ ] Navigate to `#about` → Tab switches, no errors
- [ ] Navigate to `#career` → Tab switches, no errors
- [ ] Navigate to `#loadout` → Tab switches, no errors
- [ ] Reload page with hash → Tab persists, no errors

#### Test 2.8: Clipboard Copy Operations
- [ ] Copy profile link → Success feedback, no errors
- [ ] Copy social link → Success feedback, no errors

---

### **3. Error Handling Tests** (Simulated Failures)

**Setup**: Use browser DevTools to throttle network or mock failed responses

#### Test 3.1: Network Offline Simulation
- [ ] Set browser to "Offline" mode (DevTools Network tab)
- [ ] Attempt to load game passports → Should show user-friendly error
- [ ] Attempt to submit form → Should show "Network error" message
- [ ] **No uncaught promise rejections** in console

#### Test 3.2: Backend 500 Error Simulation
- [ ] Mock backend endpoint to return 500 error
- [ ] Attempt fetch operation → Should show error alert/toast
- [ ] **No uncaught errors** in console

#### Test 3.3: Missing DOM Elements Test
- [ ] Manually remove a modal element from DOM (via DevTools)
- [ ] Attempt to open that modal → Should fail gracefully, log to `debugLog`
- [ ] **No "Cannot read property of null" errors**

#### Test 3.4: Malformed JSON Response Test
- [ ] Mock backend endpoint to return invalid JSON
- [ ] Attempt fetch operation → Should catch parse error, show user-friendly message
- [ ] **No uncaught JSON parse errors**

---

### **4. Security Tests**

#### Test 4.1: CSRF Token Validation
- [ ] Verify all POST/PUT/DELETE requests include `X-CSRFToken` header
- [ ] Check `safeFetch()` helper automatically adds CSRF token

#### Test 4.2: Visitor Mutation Blocking
- [ ] As visitor, attempt to call mutation function via browser console:
  - `submitBounty()` → Should be blocked by `requireOwner()`
  - `deletePassport()` → Should be blocked
  - `addSocialLink()` → Should be blocked
- [ ] Verify `requireOwner()` logs blocked actions to console (for debugging)

#### Test 4.3: HTML Inspection for Data Leaks
- [ ] View page source / inspect HTML as visitor
- [ ] Verify no sensitive data in `<script>` tags:
  - [ ] No wallet balances embedded
  - [ ] No private email addresses
  - [ ] No API tokens or keys
  - [ ] No unguarded backend URLs with sensitive params

---

### **5. Performance Tests**

#### Test 5.1: Large Data Sets
- [ ] Load profile with 50+ game passports → No errors, renders quickly
- [ ] Load profile with 100+ followers → No errors, list loads
- [ ] Rapid tab switching with large data → No lag or errors

#### Test 5.2: Memory Leaks Check
- [ ] Open/close modals 50+ times
- [ ] Check DevTools Memory tab for growing heap size
- [ ] Should not leak event listeners or DOM nodes

---

## 📋 **CODE REVIEW CHECKLIST**

Manual audit of profile.js code:

- [ ] **All `getElementById` calls replaced** with `safeGetById()`
- [ ] **All `querySelector` calls wrapped** with `safeQuery()`
- [ ] **All `fetch()` calls replaced** with `safeFetch()`
- [ ] **All mutation functions include** `if (!requireOwner()) return;` guard
- [ ] **All modal open functions check** `IS_VISITOR` constant
- [ ] **`IS_VISITOR` constant defined** at top of file
- [ ] **`safeFetch()` helper includes**:
  - [ ] `response.ok` check
  - [ ] JSON parse error handling
  - [ ] User-friendly error alerts
  - [ ] Returns `null` on failure
- [ ] **`requireOwner()` helper includes**:
  - [ ] `IS_VISITOR` check
  - [ ] Debug log for blocked actions
  - [ ] Returns `false` if visitor
- [ ] **`showToast()` helper includes**:
  - [ ] Fallback to `alert()` if toast UI missing

---

## 🐛 **KNOWN ISSUES & BLOCKERS**

Document any issues discovered during QA:

| Issue ID | Description | Severity | Status | Notes |
|----------|-------------|----------|--------|-------|
| *Example* | *About form fetch call missing URL* | **Critical** | 🟡 In Progress | *Line 253: fetch() missing endpoint* |
| | | | | |
| | | | | |

---

## 📊 **METRICS & LINE COUNT**

**Before Phase 3.7**:
- profile.js: **1,837 lines**
- Safety utilities: **0 lines**
- Unsafe `getElementById` calls: **~50 instances**
- Unguarded mutation functions: **~20 functions**
- Raw `fetch()` calls: **~30 calls**

**After Phase 3.7 (Target)**:
- profile.js: **~1,900-2,000 lines** (safety code adds ~100-150 lines)
- Safety utilities: **~75 lines** (helpers at top of file)
- Unsafe `getElementById` calls: **0 instances**
- Unguarded mutation functions: **0 functions**
- Raw `fetch()` calls: **0 calls**

**Estimated Work**:
- ✅ Safety utilities created (~75 lines)
- ⚠️ Modal guards applied (~18 functions, partial)
- 🔴 `safeFetch()` wrappers needed (~30 replacements)
- 🔴 Remaining `getElementById` → `safeGetById()` (~30+ replacements)
- 🔴 Form handler safety improvements
- 🔴 Visitor mode testing
- 🔴 Final QA pass

---

## ✅ **SIGN-OFF**

| Role | Name | Date | Signature |
|------|------|------|-----------|
| **Developer** | GitHub Copilot | *Pending* | ✅ Code complete, tests passed |
| **QA Tester** | *User* | *Pending* | ✅ All checklist items verified |
| **Product Owner** | *User* | *Pending* | ✅ Approved for Phase 4 |

---

## 📌 **NEXT STEPS AFTER PHASE 3.7 COMPLETION**

Once all checklist items pass:

1. ✅ Mark Phase 3.7 as **COMPLETE** in UP_TRACKER_STATUS.md
2. 📝 Document completion metrics (line count delta, replacements made)
3. 🚀 Begin Phase 4: Activity Feed & Social Features
4. 📚 Reference this QA checklist for future JavaScript hardening work

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-XX  
**Phase**: 3.7 — JavaScript Hardening & Visitor Safety  
**Status**: 🟡 In Progress → 🟢 Complete (pending sign-off)
