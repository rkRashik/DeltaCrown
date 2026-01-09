# Phase 3 Manual Testing Checklist

## 🧪 Testing Instructions

### Setup
1. Start development server: `python manage.py runserver`
2. Have two browser windows: Logged in (owner) + Incognito (visitor)
3. Test profile: `http://localhost:8000/@yourusername/`

---

## ✅ Owner View Testing (`/@me/` or your profile while logged in)

### Hero Section
- [ ] Avatar displays correctly
- [ ] Banner/cover image shows (if set)
- [ ] Display name appears in large text
- [ ] Username shows with @
- [ ] Level badge displays
- [ ] Team badge shows (if on team)
- [ ] Bio text displays
- [ ] **Owner Hint Visible**: "To edit your profile, go to Settings" with gear icon
- [ ] Settings link works (`/me/settings/`)
- [ ] Followers count displays (not locked)
- [ ] Following count displays (not locked)
- [ ] Team count shows
- [ ] Reputation score shows (if exists)
- [ ] Social links display
- [ ] "Edit Profile" button visible and works

### Tab Navigation
- [ ] All tabs visible: Overview, Posts, Media, Loadout, Career, Game IDs, Stats, Highlights, Bounties, Inventory
- [ ] **Wallet/Economy tab visible (owner only)**
- [ ] Tabs switch smoothly when clicked
- [ ] Active tab has gradient underline
- [ ] Tab icons display
- [ ] Post count badge shows

### Overview Tab (Dashboard)
- [ ] About section shows bio, pronouns, country
- [ ] **Career card** displays, shows team count
- [ ] **Stats card** displays, shows wins/win rate
- [ ] **Inventory card** displays, shows equipped items count
- [ ] **Media card** displays
- [ ] **Loadouts card** displays, shows hardware brands
- [ ] **Bounties card** displays, shows open/active counts
- [ ] **Game IDs card** displays, shows linked games count (NEW)
- [ ] Cards are clickable
- [ ] Cards have hover effects (border glow, lift)
- [ ] Clicking card switches to that tab
- [ ] Empty state shows if no data ("Welcome to Your Profile!")

### Game IDs Tab (NEW)
- [ ] "Add Game ID" button visible
- [ ] Game passports display in grid (if any)
- [ ] Game icons show
- [ ] In-game names display
- [ ] Ranks show
- [ ] Verification badges appear (if verified)
- [ ] Region displays
- [ ] Stats grid shows (if available)
- [ ] "Refresh" and "Delete" buttons visible on each passport
- [ ] Empty state shows if no passports
- [ ] "Add Your First Game ID" button works

### Other Tabs
- [ ] **Posts**: Shows activity feed or "coming soon" message
- [ ] **Media**: Shows gallery placeholder
- [ ] **Loadout**: Hardware gear displays with icons
- [ ] **Career**: Team history timeline shows
- [ ] **Stats**: Performance metrics display
- [ ] **Highlights**: Video thumbnails show (if any)
- [ ] **Bounties**: Active bounties list or empty state
- [ ] **Inventory**: Equipped cosmetics show
- [ ] **Wallet**: Balance displays, transaction history shows

### Sidebar (Left)
- [ ] About card shows country, joined date
- [ ] Game Passports widget shows pinned passports
- [ ] "Link New Account" button visible
- [ ] Loadout widget shows top 3 hardware items

---

## 👁️ Visitor View Testing (Incognito or different user)

### Hero Section
- [ ] Avatar displays
- [ ] Banner displays
- [ ] Display name shows
- [ ] Username shows
- [ ] Level badge shows
- [ ] Team badge shows (if applicable)
- [ ] Bio displays
- [ ] **NO "Edit Profile" hint or button visible**
- [ ] **NO Settings link**
- [ ] Followers: Shows count OR lock icon 🔒
- [ ] Following: Shows count OR lock icon 🔒
- [ ] Team count shows
- [ ] Reputation shows (if public)
- [ ] Social links display
- [ ] "Scout Player" button visible
- [ ] "Follow" button visible (if not following)
- [ ] "Following" button visible (if already following)
- [ ] Message and More buttons visible

### Tab Navigation
- [ ] All public tabs visible
- [ ] **Wallet/Economy tab NOT visible (owner only)**
- [ ] Tabs switch correctly
- [ ] No errors in console

### Overview Tab
- [ ] About section shows (if not hidden)
- [ ] Summary cards display
- [ ] Cards respect privacy (show public data only)
- [ ] Cards are clickable
- [ ] No edit buttons visible

### Game IDs Tab (Visitor Privacy Test)
- [ ] If public: Passports display
- [ ] If private: "Game IDs are private" message shows
- [ ] NO "Add Game ID" button for visitors
- [ ] NO edit/delete buttons on passports
- [ ] Lock icon or privacy message if data hidden

### Other Tabs (Visitor)
- [ ] Posts: Public posts show (if feature enabled)
- [ ] Media: Public media shows (or placeholder)
- [ ] Loadout: Public hardware shows (or "Setup is private")
- [ ] Career: Public team history shows
- [ ] Stats: Public stats show OR lock icon
- [ ] Highlights: Public videos show
- [ ] Bounties: Public bounties show
- [ ] Inventory: Public cosmetics show (or "Inventory is private")
- [ ] **Wallet: Tab completely hidden**

### Privacy Verification
- [ ] No private data visible in:
  - Page source (View Source)
  - DevTools → Elements
  - Network tab responses
- [ ] Hidden fields show 🔒 icon or "Hidden"/"Private" text
- [ ] NO "undefined" or "null" values displayed
- [ ] Graceful empty states for missing/hidden data

---

## 🔧 Technical Testing

### Console (F12)
- [ ] No JavaScript errors
- [ ] No 404 errors for missing files
- [ ] No CSRF token errors
- [ ] No "undefined" variable errors
- [ ] Tab switching logs work (if debugging enabled)

### Network Tab
- [ ] No failed requests (500, 404, 403)
- [ ] Images load correctly
- [ ] API calls succeed (if any)
- [ ] CSRF tokens present in POST requests

### Responsive Testing
- [ ] Mobile (375px): Layout doesn't break
- [ ] Tablet (768px): Cards stack properly
- [ ] Desktop (1920px): Max-width respected
- [ ] Tab navigation: Scrolls horizontally on mobile
- [ ] Hero: Stats bar wraps on small screens
- [ ] Overview cards: Grid responsive (1→2→3 columns)

### Accessibility (Basic)
- [ ] Tab key navigation works
- [ ] Buttons have visible focus states
- [ ] Images have alt text
- [ ] Icons have aria-labels or titles
- [ ] Color contrast is readable

---

## 🚨 Common Issues & Fixes

### Issue: Tabs don't switch
**Check**: 
- `switchTab()` JavaScript function exists
- Tab IDs match (`tab-overview`, `tab-career`, etc.)
- No console errors

**Fix**: Ensure all tab partials are included and have correct IDs

---

### Issue: Game IDs tab empty for owner
**Check**:
- `game_passports` context variable exists in view
- Database has GamePassport entries for user
- Template correctly checks `{% if game_passports %}`

**Fix**: Add test game passport in admin or via API

---

### Issue: Privacy not working (visitor sees private data)
**Check**:
- View passes `privacy` context
- Template uses `{% if privacy.show_X or is_owner %}`
- `is_owner` is correctly set in view

**Fix**: Verify view logic and template conditionals

---

### Issue: "To edit, go to Settings" link doesn't work
**Check**:
- `{% url 'user_profile:profile_settings' %}` resolves
- URL pattern exists in user_profile/urls.py
- Settings view is implemented

**Fix**: Check URL configuration

---

### Issue: Overview cards don't switch tabs
**Check**:
- Cards have `onclick="switchTab('tab-name')"`
- JavaScript is loaded
- Tab IDs match

**Fix**: Add onclick handlers or fix tab IDs

---

## ✅ Sign-Off Checklist

After completing all tests:

- [ ] All Owner tests pass
- [ ] All Visitor tests pass
- [ ] No console errors
- [ ] Privacy controls verified
- [ ] Responsive on 3+ screen sizes
- [ ] Game IDs integration works
- [ ] All tab files created and included
- [ ] Hero cleanup verified (no inline editing)
- [ ] Overview dashboard functional
- [ ] Documentation reviewed

**Tester Name**: _______________  
**Date**: _______________  
**Status**: ⬜ PASS | ⬜ NEEDS FIXES  
**Notes**: _______________

---

## 📝 Bug Report Template

If you find issues, report using this format:

```
**Issue**: Brief description
**Steps to Reproduce**:
1. Step 1
2. Step 2
3. Step 3

**Expected**: What should happen
**Actual**: What actually happens
**User Type**: Owner / Visitor
**Browser**: Chrome / Firefox / Safari
**Console Errors**: (paste errors)
**Screenshot**: (if applicable)
```

---

## 🎯 Phase 3 Testing Complete!

Once all checks pass:
1. Mark as ✅ PRODUCTION READY
2. Deploy to staging
3. User acceptance testing
4. Production deploy

**Good luck! 🚀**
