# USER PROFILE REFACTOR ANALYSIS
**Generated:** 2026-01-08  
**Status:** Phase 0 Complete - Architecture Identified

---

## PHASE 0: ARCHITECTURE IDENTIFICATION

### 🎯 Entry Points

**Main Profile Page:**
- **Template:** `templates/user_profile/profile/public_profile.html` (4,027 lines!)
- **View:** `apps/user_profile/views/public_profile_views.py::public_profile_view()`
- **Route:** `/@<username>/` (namespace: `user_profile:public_profile`)
- **Context Builder:** `apps/user_profile/services/profile_context.py::build_public_profile_context()`

**Privacy/Permission System:**
- **Checker:** `apps/user_profile/services/profile_permissions.py::ProfilePermissionChecker`
- **Settings View:** `apps/user_profile/views_settings.py::settings_view()`
- **Privacy API:** `apps/user_profile/views/settings_api.py`

**Related Files:**
- Settings page: `templates/user_profile/profile/settings_control_deck.html` (4,000+ lines)
- Private profile template: `templates/user_profile/profile_private.html`
- Follow system: `apps/user_profile/services/follow_service.py`

### 📊 Current Tab Structure

**Confirmed Tabs (from line 360-380):**
1. **Overview** (active by default)
2. **Posts** (with count badge)
3. **Media** 
4. **Loadout** (gaming gear)
5. **Career**
6. **Stats**
7. **Highlights**
8. **Bounties** (with crosshair icon)
9. **Inventory**
10. **Economy/Wallet** (owner-only, gold color)

**Note:** "Game IDs" appears in sidebar but NOT as a tab - correctly identified as needing integration into Career section.

### 🏗️ Current Architecture

**Hero Section (Lines 180-360 approx):**
- Banner/cover image with holographic effects
- Avatar with animated ring
- Display name, username, verification badges
- Stats bar (followers, teams, tournaments, achievements)
- Action buttons (Follow/Edit Profile/Settings)
- ⚠️ **ISSUE:** Contains inline edit UI elements visible to owner

**Overview Tab (Current - Lines 385+):**
- ⚠️ **ISSUE:** Not properly implemented as dashboard
- ⚠️ **ISSUE:** Mixes content from other tabs
- ⚠️ **ISSUE:** No clear "About" block
- ⚠️ **ISSUE:** No summary cards for other sections

**Sidebar (Lines 388-500):**
- About card (country, join date)
- Game Passports/IDs (pinned + unpinned)
- Loadout preview (hardware gear)

**Backend Data Flow:**
```
Request → public_profile_view()
         → ProfilePermissionChecker (compute can_view_* flags)
         → build_public_profile_context() (fetch data)
         → Template rendering (with permissions)
```

**Privacy Enforcement:**
- ✅ Server-side via `ProfilePermissionChecker`
- ✅ Passes `can_view_*` flags to template
- ✅ Returns 'profile_private.html' if blocked
- ⚠️ Needs verification: Are all sections respecting flags?

---

## PHASE 1: ISSUE REPORT

### A) 🔁 DUPLICATE CODE / REPEATED MARKUP

**CRITICAL:**
1. **4,027 lines in single template** - Monolithic, unmaintainable
2. **Repeated card structures** - Every section has similar `.z-card` markup
3. **Duplicate permission checks** - Same `{% if is_owner %}` logic scattered everywhere
4. **Repeated modal structures** - Edit modals for About, Loadout, Game Passports all similar
5. **Duplicate stats display** - Stats shown in hero AND stats tab
6. **Repeated API call patterns** - Similar fetch() calls for different endpoints

**HIGH:**
7. **Tab switching logic** - `switchTab()` function likely duplicated/verbose
8. **Loading states** - Similar loading spinners/skeletons in multiple places
9. **Empty states** - "No data" messages repeated across sections
10. **Error handling** - Try-catch blocks with similar error messages

### B) 🔧 HARD-CODED FIELDS / UI LOGIC NOT TIED TO BACKEND

**CRITICAL:**
1. **Tab names hard-coded** - "Overview", "Posts", "Media" etc. not from config
2. **Sidebar sections hard-coded** - About, Game Passports, Loadout order not configurable
3. **Stats bar metrics hard-coded** - Followers, Teams, Tournaments, Achievements fixed
4. **Loadout categories hard-coded** - Mouse, Keyboard, Headset etc. not dynamic
5. **Game passport limit hard-coded** - `|slice:":2"` shows only 2 unpinned (line 463)

**HIGH:**
6. **Avatar ring animation timing** - `4s linear infinite` hard-coded (line 68)
7. **Tab icons hard-coded** - Font Awesome classes directly in markup
8. **Color scheme hard-coded** - CSS variables but not user-customizable
9. **Card order hard-coded** - Sidebar card sequence not reorderable
10. **Privacy labels hard-coded** - "Public", "Followers Only" etc. not from backend

### C) 🔒 PRIVACY/PERMISSIONS BUGS

**CRITICAL:**
1. **Hero edit buttons visible** - Violates requirement "Hero remains display-only"
2. **Unclear About section privacy** - Country/Join Date shown but no clear privacy flag
3. **Loadout visibility unclear** - `{% if has_loadout %}` but no privacy check
4. **Game passport privacy unclear** - Shows all pinned/unpinned without permission check
5. **Wallet tab privacy** - `{% if is_owner %}` but should also check settings

**HIGH:**
6. **Follow status privacy** - Followers/following counts shown without privacy check
7. **Team membership privacy** - Teams shown in stats bar without permission
8. **Achievement privacy** - Achievement count shown without can_view_achievements check
9. **Post count privacy** - Shows post count even if posts are private
10. **Media preview privacy** - Media tab accessible but no media privacy enforcement

**MEDIUM:**
11. **Join date always visible** - Should respect "show account age" setting
12. **Country always visible** - Should respect "show location" setting

### D) 🔄 STATE SYNC BUGS

**CRITICAL:**
1. **Settings changes require refresh** - Privacy toggle doesn't update profile immediately
2. **Avatar/cover update requires refresh** - Hero doesn't react to settings changes
3. **Game passport changes need refresh** - Added passport doesn't appear without reload
4. **Follow button state stale** - Follow/unfollow doesn't update follower count immediately

**HIGH:**
5. **Tab state not preserved in URL** - Refreshing page always returns to Overview
6. **Modal changes not reflected** - Editing About doesn't update sidebar without refresh
7. **Loadout changes not live** - Edit loadout modal updates don't show instantly
8. **Verification badge not reactive** - KYC verification doesn't update badge without refresh

### E) 🗂️ TAB/CARD NAVIGATION BUGS

**HIGH:**
1. **Overview not a dashboard** - Doesn't show summary cards as required
2. **No click-to-navigate** - Summary cards (if they existed) don't navigate
3. **Tab active state not in URL** - Can't share link to specific tab
4. **No deep linking** - Can't link to `/@user/career` directly
5. **Tab scroll position lost** - Switching tabs and back loses scroll position

**MEDIUM:**
6. **Mobile tab overflow** - Too many tabs, poor mobile UX
7. **No tab shortcuts** - No keyboard shortcuts for tab switching
8. **Tab order not configurable** - Can't reorder tabs per user preference

### F) 📡 DATA LOADING BUGS

**CRITICAL:**
1. **No loading states** - Content appears suddenly, no skeletons
2. **No error boundaries** - Failed API calls show nothing or crash
3. **Race conditions possible** - Multiple tab switches could cause overlapping requests
4. **Undefined data access** - `profile.country` could be None, no fallback

**HIGH:**
5. **Missing empty states** - No "No posts yet" message in Posts tab
6. **No retry logic** - Failed requests don't offer retry
7. **Optimistic updates missing** - Actions don't show immediate feedback
8. **Cache not utilized** - Same data fetched repeatedly on tab switch

### G) ⚡ PERFORMANCE ISSUES

**CRITICAL:**
1. **4,027-line template** - Slow initial render
2. **All tabs rendered at once** - DOM bloat, should lazy-load
3. **No code splitting** - All JS loaded upfront
4. **Repeated API calls** - Same data fetched when switching tabs

**HIGH:**
5. **Unoptimized images** - Avatar/banner not using responsive images
6. **Inline styles** - Large <style> block inline (lines 9-160)
7. **No pagination** - Posts/media loaded all at once
8. **Heavy animations** - Holographic ring, gradients could impact FPS

**MEDIUM:**
9. **Font loading** - Google Fonts loaded synchronously (line 8)
10. **Icon library** - Font Awesome loaded entirely (likely unused icons)

---

## PHASE 2: REQUIRED CHANGES (IMPLEMENTATION PLAN)

### 1️⃣ HERO SECTION CLEANUP

**Requirements:**
- ✅ Remove all inline edit UI
- ✅ Keep display-only elements
- ✅ Make reactive to backend changes

**Changes:**
1. Remove "Change Cover" button (if exists)
2. Remove "Update Avatar" button (if exists)
3. Remove any edit icons in hero section
4. Keep Follow/Edit Profile/Settings buttons (navigation only)
5. Add real-time listeners for avatar/cover updates from Settings
6. Ensure stats bar is read-only

**Files to modify:**
- `templates/user_profile/profile/public_profile.html` (hero section)

### 2️⃣ TABS - NO CHANGES

**Action:** None - tabs remain as-is per requirement.

### 3️⃣ OVERVIEW TAB REDESIGN

**Requirements:**
- Overview = dashboard summary
- About block (backend-driven, privacy-respecting)
- Live Feed block (backend-driven, privacy-respecting)
- Summary Cards for all sections

**Changes:**

**A) About Block:**
```html
<div class="z-card">
  <h3>About</h3>
  {% if can_view_bio %}
    <p>{{ profile.bio }}</p>
  {% endif %}
  {% if can_view_location and profile.country %}
    <div>Location: {{ profile.country }}</div>
  {% endif %}
  {% if can_view_join_date %}
    <div>Joined: {{ profile.created_at }}</div>
  {% endif %}
  <!-- Add more fields based on privacy settings -->
</div>
```

**B) Live Feed Block:**
```html
<div class="z-card">
  <h3>Recent Activity</h3>
  {% if can_view_activity %}
    {% for activity in recent_activity %}
      <div>{{ activity }}</div>
    {% empty %}
      <p>No recent activity</p>
    {% endfor %}
  {% else %}
    <p>Activity is private</p>
  {% endif %}
</div>
```

**C) Summary Cards (clickable):**
```html
<div class="grid grid-cols-2 gap-4">
  <a href="#career" onclick="switchTab('career')" class="summary-card">
    <h4>Career</h4>
    <div class="metric">{{ total_tournaments }} Tournaments</div>
    <div class="metric">{{ total_teams }} Teams</div>
  </a>
  
  <a href="#stats" onclick="switchTab('stats')" class="summary-card">
    <h4>Stats</h4>
    <div class="metric">{{ win_rate }}% Win Rate</div>
    <div class="metric">{{ matches_played }} Matches</div>
  </a>
  
  <a href="#highlights" onclick="switchTab('highlights')" class="summary-card">
    <h4>Highlights</h4>
    <div class="metric">{{ highlight_count }} Clips</div>
  </a>
  
  <a href="#bounties" onclick="switchTab('bounties')" class="summary-card">
    <h4>Bounties</h4>
    <div class="metric">{{ active_bounties }} Active</div>
    <div class="metric">{{ completed_bounties }} Completed</div>
  </a>
  
  <a href="#inventory" onclick="switchTab('inventory')" class="summary-card">
    <h4>Inventory</h4>
    <div class="metric">{{ inventory_items }} Items</div>
  </a>
  
  {% if is_owner %}
  <a href="#wallet" onclick="switchTab('wallet')" class="summary-card">
    <h4>Economy</h4>
    <div class="metric">{{ deltacoin_balance }} DC</div>
  </a>
  {% endif %}
  
  <a href="#media" onclick="switchTab('media')" class="summary-card">
    <h4>Media</h4>
    <div class="metric">{{ media_count }} Items</div>
  </a>
  
  <a href="#loadout" onclick="switchTab('loadout')" class="summary-card">
    <h4>Loadout</h4>
    <div class="metric">{{ loadout_items }} Gear</div>
  </a>
</div>
```

**Files to modify:**
- `templates/user_profile/profile/public_profile.html` (overview tab content)
- `apps/user_profile/views/public_profile_views.py` (add summary data)
- `apps/user_profile/services/profile_context.py` (build summary context)

### 4️⃣ GAME ID HANDLING

**Requirement:** Integrate Game IDs into Career tab (no new tab)

**Changes:**
1. Move Game Passports section from sidebar to Career tab
2. Add "Game Accounts" subsection in Career
3. Ensure backend includes game IDs in career payload
4. Keep sidebar Game Passports as preview (pinned only)
5. Link sidebar preview to Career tab

**Files to modify:**
- `templates/user_profile/profile/public_profile.html` (move passports to career)
- `apps/user_profile/views/public_profile_views.py` (ensure career includes passports)

---

## PHASE 3: BACKEND SYNCHRONIZATION PLAN

### Privacy Flag Verification

**Current flags from `ProfilePermissionChecker`:**
- `can_view_profile`
- `can_view_game_passports`
- `can_view_achievements`
- `can_view_teams`
- `can_view_social_links`
- `is_owner`
- `viewer_role`

**Missing flags needed:**
- `can_view_bio`
- `can_view_location`
- `can_view_join_date`
- `can_view_posts`
- `can_view_media`
- `can_view_loadout`
- `can_view_career`
- `can_view_stats`
- `can_view_highlights`
- `can_view_bounties`
- `can_view_inventory`
- `can_view_activity`

**Action:** Extend `ProfilePermissionChecker` to include all section flags.

### Backend Endpoints to Add/Modify

1. **Profile Summary Endpoint:**
   - `GET /@<username>/api/summary/`
   - Returns: Summary metrics for all sections
   - Used by: Overview tab summary cards

2. **Career with Game IDs Endpoint:**
   - `GET /@<username>/api/career/`
   - Returns: Tournament history, team history, game accounts
   - Used by: Career tab

3. **Live Feed Endpoint:**
   - `GET /@<username>/api/activity/`
   - Returns: Recent activity (posts, achievements, matches)
   - Used by: Overview tab live feed

**Files to create/modify:**
- `apps/user_profile/api/profile_summary_api.py` (NEW)
- `apps/user_profile/services/profile_permissions.py` (EXTEND)
- `apps/user_profile/views/public_profile_views.py` (MODIFY)

---

## PHASE 4: REFACTOR QUALITY REQUIREMENTS

### Component Extraction Plan

**Reusable Components to Create:**

1. **OverviewCard.html** (summary card template)
2. **ProfileHeroDisplay.html** (read-only hero partial)
3. **AboutBlock.html** (privacy-aware about section)
4. **LiveFeedBlock.html** (activity feed component)
5. **GamePassportCard.html** (single passport display)
6. **LoadingState.html** (skeleton loader)
7. **EmptyState.html** (no data message)
8. **ErrorBoundary.html** (error display)

**Directory structure:**
```
templates/user_profile/profile/components/
├── overview_card.html
├── hero_display.html
├── about_block.html
├── live_feed_block.html
├── game_passport_card.html
├── loading_state.html
├── empty_state.html
└── error_boundary.html
```

### Data Fetching Consolidation

**Create single source of truth:**

**File:** `static/js/profile/profile_data_manager.js`
```javascript
class ProfileDataManager {
  constructor(username) {
    this.username = username;
    this.cache = new Map();
  }
  
  async getSection(sectionName) {
    if (this.cache.has(sectionName)) {
      return this.cache.get(sectionName);
    }
    
    const data = await fetch(`/@${this.username}/api/${sectionName}/`);
    this.cache.set(sectionName, data);
    return data;
  }
  
  invalidate(sectionName) {
    this.cache.delete(sectionName);
  }
  
  invalidateAll() {
    this.cache.clear();
  }
}
```

### Loading/Error/Empty States

**Standardized approach:**

```html
<!-- Loading -->
{% include 'user_profile/profile/components/loading_state.html' with type='card' %}

<!-- Error -->
{% include 'user_profile/profile/components/error_boundary.html' with 
   message='Failed to load data' 
   action='retry' %}

<!-- Empty -->
{% include 'user_profile/profile/components/empty_state.html' with 
   message='No posts yet'
   icon='fa-image'
   cta='Create your first post' %}
```

---

## PHASE 5: VERIFICATION CHECKLIST

### Pre-Implementation Checklist

- [ ] All architecture files identified
- [ ] All issues documented
- [ ] Backend contract changes listed
- [ ] Component structure designed
- [ ] API endpoints planned

### Post-Implementation Checklist

#### Hero Section
- [ ] No "Change Cover" button visible
- [ ] No "Update Avatar" button visible
- [ ] No edit icons in hero section
- [ ] Hero displays avatar/cover from backend
- [ ] Hero reacts to Settings page changes
- [ ] Stats bar is read-only

#### Overview Tab
- [ ] Shows About block
- [ ] About respects privacy settings
- [ ] Shows Live Feed block
- [ ] Live Feed respects privacy settings
- [ ] Shows summary cards for all sections
- [ ] Summary cards are clickable
- [ ] Summary cards navigate to correct tabs
- [ ] Summary metrics from backend

#### Privacy/Permissions
- [ ] No hard-coded user data in template
- [ ] All sections check `can_view_*` flags
- [ ] Private sections show "Private" message
- [ ] Private sections don't render sensitive data
- [ ] Owner sees all sections regardless of privacy
- [ ] Privacy toggles update flags immediately
- [ ] Profile respects privacy without refresh

#### Game IDs
- [ ] Game IDs integrated into Career tab
- [ ] Sidebar shows preview (pinned passports)
- [ ] Sidebar links to Career tab
- [ ] Career tab shows all passports
- [ ] Backend includes passports in career payload

#### Tabs & Navigation
- [ ] All 10 tabs present and functional
- [ ] Tab active state correct
- [ ] Tab switching works smoothly
- [ ] No new tabs created
- [ ] Tab order unchanged
- [ ] Tab names unchanged

#### Backend Contract
- [ ] `ProfilePermissionChecker` extended
- [ ] Summary API endpoint created
- [ ] Career API includes game IDs
- [ ] Live Feed API created
- [ ] All APIs return privacy-filtered data
- [ ] APIs backward compatible

#### Code Quality
- [ ] Template under 2,000 lines
- [ ] Reusable components extracted
- [ ] No duplicate markup
- [ ] Single data fetching source
- [ ] Loading states for all async ops
- [ ] Error states for all async ops
- [ ] Empty states for all lists
- [ ] No repeated API calls

#### Performance
- [ ] Template loads in < 1s
- [ ] Tabs lazy-load content
- [ ] Images optimized
- [ ] No layout shift
- [ ] Smooth animations

---

## BACKEND CONTRACT CHANGES

### Extended `ProfilePermissionChecker`

**File:** `apps/user_profile/services/profile_permissions.py`

**New methods to add:**
```python
def can_view_bio(self) -> bool:
    """Check if viewer can see profile bio"""
    
def can_view_location(self) -> bool:
    """Check if viewer can see country/location"""
    
def can_view_join_date(self) -> bool:
    """Check if viewer can see account creation date"""
    
def can_view_posts(self) -> bool:
    """Check if viewer can see user's posts"""
    
def can_view_media(self) -> bool:
    """Check if viewer can see media gallery"""
    
def can_view_loadout(self) -> bool:
    """Check if viewer can see gaming loadout"""
    
def can_view_career(self) -> bool:
    """Check if viewer can see career/tournament history"""
    
def can_view_stats(self) -> bool:
    """Check if viewer can see gameplay statistics"""
    
def can_view_highlights(self) -> bool:
    """Check if viewer can see highlight clips"""
    
def can_view_bounties(self) -> bool:
    """Check if viewer can see bounty history"""
    
def can_view_inventory(self) -> bool:
    """Check if viewer can see inventory items"""
    
def can_view_activity(self) -> bool:
    """Check if viewer can see activity feed"""
```

### New API Endpoint: Profile Summary

**File:** `apps/user_profile/api/profile_summary_api.py` (CREATE)

**Endpoint:** `GET /@<username>/api/summary/`

**Response:**
```json
{
  "career": {
    "tournaments": 42,
    "teams": 5,
    "wins": 28
  },
  "stats": {
    "win_rate": 67.5,
    "matches_played": 156,
    "kda": 2.8
  },
  "highlights": {
    "count": 12,
    "latest": "2026-01-05"
  },
  "bounties": {
    "active": 3,
    "completed": 8,
    "total_earned": 1200
  },
  "inventory": {
    "items": 24,
    "rare_items": 5
  },
  "media": {
    "images": 18,
    "videos": 6
  },
  "loadout": {
    "items": 7,
    "complete": true
  },
  "economy": {
    "balance": 5420,
    "lifetime_earned": 12000
  }
}
```

### Modified Endpoint: Career with Game IDs

**File:** `apps/user_profile/views/public_profile_views.py` (MODIFY)

**Existing endpoint behavior:**
- Career data already returned in `build_public_profile_context()`

**Change:**
- Ensure `game_passports` included in career section
- Add `career_summary` to context

### New API Endpoint: Live Feed

**File:** `apps/user_profile/api/activity_feed_api.py` (CREATE)

**Endpoint:** `GET /@<username>/api/activity/`

**Response:**
```json
{
  "items": [
    {
      "type": "achievement",
      "title": "Tournament Victory",
      "timestamp": "2026-01-07T14:30:00Z",
      "icon": "trophy"
    },
    {
      "type": "post",
      "title": "New team announcement",
      "timestamp": "2026-01-06T10:15:00Z",
      "preview": "Excited to join..."
    }
  ],
  "has_more": true,
  "next_page": 2
}
```

---

## IMPLEMENTATION PRIORITY

### 🔴 Phase 1 (Critical - Do First)
1. Extract reusable components (reduce template size)
2. Remove hero edit buttons
3. Extend `ProfilePermissionChecker` with all flags
4. Add loading/error/empty states

### 🟡 Phase 2 (High Priority)
5. Redesign Overview tab with About block
6. Add summary cards to Overview
7. Create Profile Summary API
8. Integrate Game IDs into Career tab
9. Add Live Feed block to Overview

### 🟢 Phase 3 (Medium Priority)
10. Create single data fetching manager
11. Add reactive state sync
12. Optimize performance (lazy loading)
13. Add URL-based tab state

---

## ESTIMATED EFFORT

- **Phase 1:** 2-3 days
- **Phase 2:** 3-4 days
- **Phase 3:** 2-3 days
- **Total:** 7-10 days

---

## NEXT STEPS

1. ✅ Review this analysis document
2. ⬜ Approve implementation plan
3. ⬜ Begin Phase 1 (component extraction)
4. ⬜ Create backend endpoints (Phase 2)
5. ⬜ Implement Overview redesign (Phase 2)
6. ⬜ Final testing and verification (Phase 3)

---

**END OF ANALYSIS**
