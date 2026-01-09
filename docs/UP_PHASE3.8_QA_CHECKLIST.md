# Profile Frontend QA Checklist — Phase 3.8

**Purpose:** Systematic verification of profile page functionality, security, and visitor safety.  
**Scope:** Public profile page (`/@username/`) in both owner and visitor modes.  
**Last Updated:** 2026-01-09

---

## ✅ Pre-Test Setup

- [ ] Server running: `python manage.py runserver`
- [ ] Hard reload browser: Ctrl+Shift+R (clear cache)
- [ ] DevTools Console open (F12 → Console tab)
- [ ] Test users ready:
  - Owner account logged in
  - Visitor account (or logged out) ready

---

## 🎯 Build Verification

### BV-1: Build Stamp Appears
- [ ] Console shows: `[PROFILE] Build loaded: PROFILE_BUILD_2026-01-09_FIX4C` (or current build)
- [ ] No `SyntaxError` messages in console
- [ ] No `switchTab is not defined` errors

**Pass Criteria:** Build stamp appears within first 3 console lines.

---

## 🔄 Tab System Tests

### TAB-1: Tab Switching (Owner Mode)
- [ ] Click "Overview" → Overview panel shows
- [ ] Click "Posts" → Posts panel shows, Overview hides
- [ ] Click "Media" → Media panel shows
- [ ] Click "Loadout" → Loadout panel shows
- [ ] Click "Career" → Career panel shows
- [ ] Click "Game IDs" → Game IDs panel shows
- [ ] Click "Stats" → Stats panel shows
- [ ] Click "Highlights" → Highlights panel shows
- [ ] Click "Bounties" → Bounties panel shows
- [ ] Click "Inventory" → Inventory panel shows
- [ ] Click "Economy" (wallet) → Economy panel shows

**Pass Criteria:** Only one tab panel visible at a time. Active tab button highlighted.

### TAB-2: Tab Switching (Visitor Mode)
- [ ] Logout or use different account
- [ ] Navigate to `/@username/` (someone else's profile)
- [ ] Verify "Economy" tab is NOT visible
- [ ] Click all visible tabs (Overview through Inventory)
- [ ] All tabs switch correctly

**Pass Criteria:** Wallet tab hidden for visitors. All other tabs work.

### TAB-3: Hash Navigation
- [ ] Navigate to `/@username/#career`
- [ ] Page loads with Career tab open
- [ ] Change URL to `/@username/#stats`
- [ ] Stats tab opens automatically
- [ ] Click "Overview" tab
- [ ] URL updates to `/@username/#overview`

**Pass Criteria:** URL hash syncs with active tab.

### TAB-4: Overview Card Navigation
- [ ] From Overview tab, click "View Career" card (if exists)
- [ ] Career tab opens
- [ ] Return to Overview, click other quick-nav cards
- [ ] Corresponding tabs open

**Pass Criteria:** Overview cards trigger correct tab switches.

---

## 👥 Visitor/Owner Privacy Tests

### PRIV-1: Visitor Cannot Edit
**Test as Visitor (not owner):**
- [ ] Try clicking "Edit Bio" (if button visible) → Should show error or do nothing
- [ ] Try clicking "Add Game ID" → Should be hidden or show error
- [ ] Try clicking "Delete" on any item → Should be hidden or show error
- [ ] Check DevTools Network tab → No POST/DELETE requests sent

**Pass Criteria:** Visitors cannot trigger mutations. No unauthorized API calls.

### PRIV-2: Wallet Tab Hidden for Visitors
- [ ] Logout or use different account
- [ ] Navigate to `/@username/`
- [ ] Verify "Economy" tab NOT in navigation
- [ ] Try manually navigating to `/@username/#wallet`
- [ ] Verify wallet content NOT shown

**Pass Criteria:** Wallet tab completely hidden from visitors.

### PRIV-3: Owner Can Edit
**Test as Owner:**
- [ ] "Edit Bio" works
- [ ] "Add Game ID" works
- [ ] "Delete" buttons work on own items
- [ ] "Save" buttons work in modals
- [ ] "Economy" tab visible and accessible

**Pass Criteria:** All owner actions work.

---

## 🎨 Modal System Tests

### MOD-1: Modal Open/Close (Owner)
- [ ] Click "Edit Bio" → About modal opens
- [ ] Click modal backdrop → Modal closes
- [ ] Click "Edit Game IDs" → Game Passports modal opens
- [ ] Click X button → Modal closes
- [ ] Repeat for all modals:
  - [ ] About
  - [ ] Game Passports
  - [ ] Highlights
  - [ ] Social Links
  - [ ] Create Bounty
  - [ ] Followers (if visible)
  - [ ] Following (if visible)

**Pass Criteria:** All modals open and close cleanly. No console errors.

### MOD-2: Modal Forms (Owner)
- [ ] Open "Edit Bio" modal
- [ ] Change bio text
- [ ] Click "Save"
- [ ] Modal closes, bio updates on page
- [ ] Open "Add Game ID" modal
- [ ] Fill form, submit
- [ ] Game ID appears in list

**Pass Criteria:** Form submissions work, data persists.

### MOD-3: Visitor Modal Restrictions
**Test as Visitor:**
- [ ] "Edit" buttons hidden or disabled
- [ ] "Add" buttons hidden or disabled
- [ ] Opening owner-only modals shows error or does nothing

**Pass Criteria:** Visitors cannot access owner-only modals.

---

## 🛡️ Security & Error Handling Tests

### SEC-1: CSRF Protection
- [ ] Open DevTools → Network tab
- [ ] Perform owner action (e.g., edit bio)
- [ ] Check request headers → `X-CSRFToken` present
- [ ] Repeat for multiple actions

**Pass Criteria:** All POST/PUT/DELETE requests include CSRF token.

### SEC-2: Network Errors Gracefully Handled
- [ ] Open DevTools → Network tab
- [ ] Throttle to "Slow 3G"
- [ ] Try editing bio
- [ ] Verify friendly error message appears
- [ ] Restore normal network

**Pass Criteria:** No console crashes. User-friendly error shown.

### SEC-3: Invalid Data Handled
- [ ] Try submitting empty form
- [ ] Verify validation error appears
- [ ] Try submitting invalid data (if applicable)
- [ ] Verify server error handled gracefully

**Pass Criteria:** No uncaught exceptions. Errors shown to user.

---

## 🎮 Loadout Tab Tests

### LOAD-1: Hardware Subtab
- [ ] Navigate to Loadout tab
- [ ] Click "Hardware" subtab
- [ ] Hardware list displays
- [ ] (Owner) Click "Edit" → Form populates
- [ ] (Owner) Click "Delete" → Item removed

**Pass Criteria:** Hardware CRUD works for owner. Visitors see read-only.

### LOAD-2: Game Configs Subtab
- [ ] Click "Game Configs" subtab
- [ ] Config list displays
- [ ] (Owner) Edit/delete works

**Pass Criteria:** Game configs CRUD works for owner.

---

## 💰 Bounties Tab Tests

### BOUN-1: Bounty List Display
- [ ] Navigate to Bounties tab
- [ ] Bounty list displays (or "No bounties" message)
- [ ] Bounty cards show: title, game, stake, expiry

**Pass Criteria:** Bounties display correctly.

### BOUN-2: Create Bounty (Owner)
- [ ] Click "Create Bounty"
- [ ] Fill form: title, game, description, stake, expiry
- [ ] Submit
- [ ] Bounty appears in list

**Pass Criteria:** Bounty creation works. Data persists.

### BOUN-3: Accept Bounty (Visitor)
- [ ] As visitor, view bounty list
- [ ] Click "Accept" on active bounty
- [ ] Confirmation prompt appears
- [ ] Accept → Success message

**Pass Criteria:** Visitors can accept bounties (if feature enabled).

---

## 📸 Media Tab Tests

### MED-1: Media Display
- [ ] Navigate to Media tab
- [ ] Photos/videos display in grid
- [ ] Click thumbnail → Lightbox opens
- [ ] (Owner) Upload button visible

**Pass Criteria:** Media displays. Lightbox works.

### MED-2: Upload Media (Owner)
- [ ] Click "Upload"
- [ ] Select image file
- [ ] Submit
- [ ] Image appears in grid

**Pass Criteria:** Upload works. Image persists.

---

## 📊 Stats Tab Tests

### STAT-1: Stats Display
- [ ] Navigate to Stats tab
- [ ] Win/loss records display
- [ ] Performance metrics show
- [ ] Charts render (if present)

**Pass Criteria:** Stats display without errors.

---

## 🏆 Highlights Tab Tests

### HIGH-1: Highlights Display
- [ ] Navigate to Highlights tab
- [ ] Video embeds display
- [ ] (Owner) "Add Highlight" visible
- [ ] Play embedded video

**Pass Criteria:** Videos display and play.

---

## 📦 Inventory Tab Tests

### INV-1: Inventory Display
- [ ] Navigate to Inventory tab
- [ ] Items display in grid
- [ ] Item details show on hover/click

**Pass Criteria:** Inventory displays.

---

## 💳 Economy/Wallet Tab Tests (Owner Only)

### WAL-1: Wallet Tab Visibility
- [ ] As owner, "Economy" tab visible
- [ ] As visitor, "Economy" tab hidden
- [ ] Click "Economy" tab → Wallet content shows

**Pass Criteria:** Wallet only accessible to owner.

### WAL-2: Wallet Content
- [ ] DC balance displays
- [ ] Transaction history shows
- [ ] (If applicable) Withdrawal/deposit forms work

**Pass Criteria:** Wallet data displays correctly.

---

## 🔍 Console Health Check

### CON-1: Zero Errors in Production Mode
- [ ] Open Console
- [ ] Navigate through all tabs
- [ ] No `Uncaught ReferenceError`
- [ ] No `Uncaught TypeError`
- [ ] No `SyntaxError`
- [ ] Only expected warnings (e.g., third-party extensions)

**Pass Criteria:** Zero profile-related errors in console.

### CON-2: Debug Mode (Optional)
- [ ] Set `DEBUG_PROFILE = true` in profile.js
- [ ] Reload page
- [ ] Console shows `[PROFILE DEBUG]` messages
- [ ] Set back to `false`
- [ ] Reload → Debug messages gone

**Pass Criteria:** Debug mode toggles correctly.

---

## 📱 Responsive Design Tests (Optional)

### RESP-1: Mobile Layout
- [ ] Open DevTools → Device toolbar
- [ ] Switch to iPhone/Android view
- [ ] Tabs scroll horizontally
- [ ] All modals display correctly
- [ ] Forms are usable

**Pass Criteria:** Page usable on mobile.

### RESP-2: Tablet Layout
- [ ] Switch to iPad view
- [ ] Layout adapts correctly
- [ ] No horizontal scroll issues

**Pass Criteria:** Page usable on tablet.

---

## 🚀 Performance Tests (Optional)

### PERF-1: Page Load Time
- [ ] Hard reload page
- [ ] DevTools → Network → Check load time
- [ ] Should be < 3 seconds on normal connection

**Pass Criteria:** Page loads reasonably fast.

### PERF-2: Tab Switch Performance
- [ ] Switch between tabs rapidly
- [ ] No lag or jank
- [ ] Smooth transitions

**Pass Criteria:** Tab switching feels instant.

---

## ✅ Final Verification

### FINAL-1: Critical Path Works
- [ ] Visitor can view public profile
- [ ] Owner can edit their profile
- [ ] Tabs switch correctly
- [ ] No console errors
- [ ] Build stamp appears

**Pass Criteria:** All critical functionality works.

### FINAL-2: Documentation Updated
- [ ] Build stamp in code matches this document
- [ ] Known issues documented
- [ ] Test results recorded

---

## 📋 Test Results Template

**Date:** _____________  
**Tester:** _____________  
**Build:** _____________  
**Browser:** _____________  

**Summary:**
- Total Tests: ___
- Passed: ___
- Failed: ___
- Blocked: ___

**Failed Tests:**
1. _____________________________ (Severity: High/Medium/Low)
2. _____________________________ (Severity: High/Medium/Low)

**Notes:**
_____________________________________________________________
_____________________________________________________________

---

## 🐛 Common Issues & Fixes

### Issue: Tabs not switching
- **Symptom:** Clicking tab does nothing
- **Fix:** Hard reload (Ctrl+Shift+R), check console for errors

### Issue: Build stamp not appearing
- **Symptom:** No `[PROFILE] Build loaded:` in console
- **Fix:** Check Network tab → profile.js loaded? Status 200? Hard reload.

### Issue: switchTab is not defined
- **Symptom:** Console error when clicking tabs
- **Fix:** JS file not loading. Check static file path, hard reload.

### Issue: Modal won't close
- **Symptom:** Clicking backdrop does nothing
- **Fix:** Check modal event listeners, reload page.

---

**END OF CHECKLIST**

_For Phase 3.8.1+ tests, see updated checklist versions._
