# Task 4: Architecture & File Structure

## 📊 Complete File Tree

```
DeltaCrown/
│
├── apps/teams/
│   ├── views/
│   │   ├── dashboard.py                 ✨ NEW (560 lines)
│   │   │   ├── team_dashboard_view()
│   │   │   ├── team_profile_view()
│   │   │   ├── follow_team()
│   │   │   ├── unfollow_team()
│   │   │   ├── update_roster_order()
│   │   │   └── resend_invite()
│   │   ├── public.py
│   │   ├── ajax.py
│   │   └── ...
│   │
│   └── urls.py                          ✏️ UPDATED
│       ├── /teams/<slug>/               → team_profile_view
│       ├── /teams/<slug>/dashboard/     → team_dashboard_view
│       ├── /teams/<slug>/follow/        → follow_team
│       ├── /teams/<slug>/unfollow/      → unfollow_team
│       └── ...
│
├── templates/teams/
│   ├── team_dashboard.html              ✨ NEW (850 lines)
│   │   ├── Team Header with Banner
│   │   ├── Team Info Section
│   │   ├── Roster Management (Drag-and-Drop)
│   │   ├── Pending Invites
│   │   ├── Activity Feed
│   │   ├── Settings Toggles
│   │   ├── Achievements Preview
│   │   ├── Upcoming Matches
│   │   └── Recent Posts
│   │
│   ├── team_profile.html                ✨ NEW (900 lines)
│   │   ├── Hero Banner Section
│   │   ├── Tab Navigation
│   │   ├── Overview Tab
│   │   │   ├── About Section
│   │   │   ├── Statistics Grid
│   │   │   └── Posts Feed
│   │   ├── Roster Tab
│   │   │   └── Player Profile Cards
│   │   ├── Achievements Tab
│   │   │   └── Timeline by Year
│   │   ├── Matches Tab
│   │   │   ├── Upcoming Matches
│   │   │   └── Recent Matches
│   │   ├── Media Tab
│   │   └── Sidebar
│   │       ├── Social Links
│   │       ├── Activity Stream
│   │       └── Team Info
│   │
│   └── ... (existing templates)
│
├── static/teams/
│   ├── css/
│   │   ├── team-dashboard.css           ✨ NEW (1,200 lines)
│   │   │   ├── Dashboard Layout
│   │   │   ├── Card Components
│   │   │   ├── Roster Grid
│   │   │   ├── Player Cards
│   │   │   ├── Activity Feed
│   │   │   ├── Toggle Switches
│   │   │   ├── Badges & Stats
│   │   │   └── Responsive Breakpoints
│   │   │
│   │   ├── team-profile.css             ✨ NEW (1,200 lines)
│   │   │   ├── Hero Section
│   │   │   ├── Tab Navigation
│   │   │   ├── Profile Cards
│   │   │   ├── Stats Grid
│   │   │   ├── Posts Feed
│   │   │   ├── Player Cards
│   │   │   ├── Achievement Timeline
│   │   │   ├── Match Cards
│   │   │   └── Responsive Layouts
│   │   │
│   │   └── ... (existing styles)
│   │
│   └── js/
│       ├── team-dashboard.js            ✨ NEW (240 lines)
│       │   ├── Drag-and-Drop Roster
│       │   ├── Settings Toggles
│       │   ├── Player Management
│       │   ├── Invite Actions
│       │   ├── Activity Filters
│       │   └── Notifications
│       │
│       ├── team-profile.js              ✨ NEW (250 lines)
│       │   ├── Tab Navigation
│       │   ├── Follow/Unfollow
│       │   ├── Share Profile
│       │   ├── Join Requests
│       │   └── Notifications
│       │
│       └── ... (existing scripts)
│
├── docs/
│   ├── TASK4_IMPLEMENTATION_COMPLETE.md ✨ NEW (Full documentation)
│   ├── TASK4_SUMMARY.md                 ✨ NEW (Quick overview)
│   └── TEAM_DASHBOARD_QUICK_REFERENCE.md ✨ NEW (User guide)
│
└── setup_task4.ps1                      ✨ NEW (Setup script)
```

---

## 🔄 Data Flow Architecture

### Dashboard View Flow
```
User Request
    ↓
/teams/<slug>/dashboard/
    ↓
team_dashboard_view()
    ↓
Permission Check (Captain/Manager)
    ↓
Database Queries (8 optimized queries)
    ├── Team data
    ├── Roster (select_related profile__user)
    ├── Pending Invites (select_related invited_user, inviter)
    ├── Team Stats
    ├── Achievements (top 5)
    ├── Activities (last 20)
    ├── Social Metrics
    └── Matches (upcoming)
    ↓
Render team_dashboard.html
    ↓
JavaScript Initializes
    ├── Drag-and-Drop
    ├── Toggle Switches
    └── Event Listeners
    ↓
User Interaction
```

### Profile View Flow
```
User Request
    ↓
/teams/<slug>/
    ↓
team_profile_view()
    ↓
Privacy Check (is_public or is_member)
    ↓
Database Queries (6 optimized queries)
    ├── Team data
    ├── Roster
    ├── Stats (if allowed)
    ├── Achievements (all, grouped by year)
    ├── Posts (based on visibility)
    └── Activities (public only)
    ↓
Render team_profile.html
    ↓
JavaScript Initializes
    ├── Tab Navigation
    ├── Follow Button
    └── Share Button
    ↓
User Interaction
```

### Follow/Unfollow Flow
```
User clicks Follow/Unfollow
    ↓
JavaScript function (followTeam/unfollowTeam)
    ↓
AJAX POST to /teams/<slug>/follow/ or /unfollow/
    ↓
follow_team() or unfollow_team() view
    ↓
Authentication Check
    ↓
TeamFollower.objects.create() or .delete()
    ↓
Update team.followers_count
    ↓
JSON Response
    ↓
JavaScript updates UI
    ├── Button text/style
    └── Followers count
```

### Roster Ordering Flow
```
Captain drags player card
    ↓
JavaScript drag events
    ↓
Visual reorder in DOM
    ↓
saveRosterOrder() called
    ↓
AJAX POST to /teams/<slug>/update-roster-order/
    ↓
update_roster_order() view
    ↓
Permission Check (Captain only)
    ↓
TeamMembership.objects.filter().update(display_order=X)
    ↓
JSON Response
    ↓
Success notification
```

---

## 🗄️ Database Schema

### Models Used

```python
# Core Team Model
Team
├── id (PK)
├── name
├── tag
├── slug (unique per game)
├── game
├── logo
├── banner
├── captain (FK → UserProfile)
├── is_public (bool)
├── allow_followers (bool)
├── show_statistics (bool)
├── allow_join_requests (bool)
└── followers_count (int)

# Roster Model
TeamMembership
├── id (PK)
├── team (FK → Team)
├── profile (FK → UserProfile)
├── role (choices)
├── is_captain (bool)
├── is_starter (bool)
├── status (choices)
├── display_order (int)  ← Used for drag-and-drop
└── joined_at

# Invite Model
TeamInvite
├── id (PK)
├── team (FK → Team)
├── invited_user (FK → User, nullable)
├── invited_email
├── inviter (FK → UserProfile)
├── role
├── status (choices)
├── expires_at
└── created_at

# Stats Model
TeamStats
├── id (PK)
├── team (FK → Team)
├── matches_played
├── wins
├── losses
├── win_rate
├── streak
└── updated_at

# Achievement Model
TeamAchievement
├── id (PK)
├── team (FK → Team)
├── title
├── placement (choices)
├── year
├── notes
└── tournament (FK → Tournament, nullable)

# Activity Model
TeamActivity
├── id (PK)
├── team (FK → Team)
├── activity_type (choices)
├── actor (FK → UserProfile, nullable)
├── description
├── related_post (FK → TeamPost, nullable)
├── related_user (FK → UserProfile, nullable)
├── metadata (JSON)
├── is_public (bool)
└── created_at

# Follower Model
TeamFollower
├── id (PK)
├── team (FK → Team)
├── follower (FK → UserProfile)
├── notify_posts (bool)
├── notify_matches (bool)
├── notify_achievements (bool)
└── followed_at

# Post Model
TeamPost
├── id (PK)
├── team (FK → Team)
├── author (FK → UserProfile)
├── post_type (choices)
├── title
├── content
├── visibility (choices)
├── is_pinned (bool)
├── is_featured (bool)
├── likes_count
├── comments_count
├── shares_count
├── published_at
└── created_at
```

---

## 🔐 Permission Matrix

| Action | Captain | Manager | Member | Follower | Guest |
|--------|---------|---------|--------|----------|-------|
| **Dashboard** |
| Access dashboard | ✅ | ✅ | ❌ | ❌ | ❌ |
| View team info | ✅ | ✅ | ❌ | ❌ | ❌ |
| Edit team info | ✅ | ❌ | ❌ | ❌ | ❌ |
| Reorder roster | ✅ | ❌ | ❌ | ❌ | ❌ |
| Remove player | ✅ | ❌ | ❌ | ❌ | ❌ |
| Invite player | ✅ | ✅* | ❌ | ❌ | ❌ |
| Resend invite | ✅ | ❌ | ❌ | ❌ | ❌ |
| Toggle settings | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Profile** |
| View public profile | ✅ | ✅ | ✅ | ✅ | ✅ |
| View private profile | ✅ | ✅ | ✅ | ❌ | ❌ |
| View statistics | ✅ | ✅ | ✅ | ✅** | ✅** |
| Follow team | ✅ | ✅ | ✅ | ✅ | ✅*** |
| Request join | ❌ | ❌ | ❌ | ✅**** | ✅**** |

\* Manager can invite if team allows  
\** Only if `show_statistics=True`  
\*** Requires authentication  
\**** Only if eligible (not in same game team)

---

## 🎯 Component Hierarchy

### Dashboard Page Structure
```
team_dashboard.html
├── Header
│   ├── Breadcrumb
│   ├── Banner Image
│   └── Team Header Card
│       ├── Logo
│       ├── Team Info (name, tag, meta)
│       └── Quick Stats (followers, members, posts)
│
├── Alerts Section
│   └── Alert Cards (warnings, errors)
│
└── Dashboard Content
    ├── Main Column
    │   ├── Team Info Card
    │   │   ├── Info Grid (name, tag, game, region)
    │   │   ├── Edit Button
    │   │   └── Stats Overview (wins, losses, win rate)
    │   │
    │   ├── Roster Card
    │   │   ├── Header (title, capacity, invite button)
    │   │   └── Player Grid (drag-sortable)
    │   │       └── Player Cards
    │   │           ├── Captain Badge (if captain)
    │   │           ├── Avatar
    │   │           ├── Name & IGN
    │   │           ├── Role Badge
    │   │           └── Actions (edit, remove)
    │   │
    │   ├── Pending Invites Card
    │   │   └── Invite Items
    │   │       ├── User/Email
    │   │       ├── Meta (inviter, time, expiry)
    │   │       └── Actions (resend, cancel)
    │   │
    │   └── Activity Feed Card
    │       └── Activity Items
    │           ├── Icon
    │           ├── Description
    │           └── Timestamp
    │
    └── Sidebar Column
        ├── Settings Card
        │   ├── Toggle Switches
        │   └── Advanced Settings Link
        │
        ├── Achievements Card
        │   ├── Achievement Items (top 5)
        │   └── Add Button
        │
        ├── Upcoming Matches Card
        │   └── Match Items
        │
        └── Recent Posts Card
            └── Post Items
```

### Profile Page Structure
```
team_profile.html
├── Hero Section
│   ├── Banner Image
│   ├── Team Logo
│   ├── Identity
│   │   ├── Badges (verified, featured)
│   │   ├── Name & Tagline
│   │   ├── Quick Info Chips
│   │   └── Stats Bar
│   └── Actions
│       ├── Manage/Member/Join Button
│       ├── Follow/Following Button
│       └── Share Button
│
├── Navigation Tabs
│   ├── Overview
│   ├── Roster
│   ├── Achievements
│   ├── Matches
│   └── Media
│
└── Content Grid
    ├── Main Content
    │   ├── Overview Tab
    │   │   ├── About Card
    │   │   ├── Statistics Card
    │   │   └── Posts Feed
    │   │
    │   ├── Roster Tab
    │   │   └── Player Profile Cards
    │   │
    │   ├── Achievements Tab
    │   │   └── Timeline by Year
    │   │       └── Achievement Cards
    │   │
    │   ├── Matches Tab
    │   │   ├── Upcoming Matches
    │   │   └── Recent Matches
    │   │
    │   └── Media Tab
    │       └── Gallery (placeholder)
    │
    └── Sidebar
        ├── Social Links Card
        ├── Activity Stream Card
        └── Team Info Card
```

---

## 🎨 CSS Architecture

### Dashboard Stylesheet Structure
```css
team-dashboard.css
├── CSS Variables (colors, spacing)
├── Dashboard Layout (.team-dashboard)
├── Header Components
│   ├── .dashboard-header
│   ├── .team-banner-section
│   └── .team-header-card
├── Content Layout
│   ├── .dashboard-grid
│   ├── .main-column
│   └── .sidebar-column
├── Card Components
│   ├── .dashboard-card
│   ├── .card-header
│   └── .card-body
├── Roster Components
│   ├── .roster-grid
│   ├── .player-card
│   ├── .captain-badge
│   └── .role-badge
├── Activity Components
│   ├── .activity-feed
│   ├── .activity-item
│   └── .activity-icon
├── UI Elements
│   ├── .toggle-label (switches)
│   ├── .badge (various)
│   └── .btn (buttons)
└── Responsive Breakpoints
    ├── @media (max-width: 1200px)
    ├── @media (max-width: 768px)
    └── @media (max-width: 480px)
```

### Profile Stylesheet Structure
```css
team-profile.css
├── CSS Variables
├── Profile Layout (.team-profile)
├── Hero Components
│   ├── .profile-hero
│   ├── .hero-banner
│   └── .team-header
├── Navigation
│   ├── .profile-nav
│   └── .nav-tabs
├── Content Layout
│   ├── .content-grid
│   ├── .main-content
│   └── .sidebar-content
├── Tab Content
│   ├── .tab-content
│   └── .profile-card
├── Stats Components
│   ├── .stats-grid
│   └── .stat-box
├── Posts Components
│   ├── .posts-feed
│   ├── .post-card
│   └── .post-engagement
├── Roster Components
│   ├── .roster-grid
│   ├── .player-profile-card
│   └── .captain-crown
├── Achievement Components
│   ├── .achievements-timeline
│   ├── .achievement-card
│   └── .achievement-medal
├── Match Components
│   ├── .matches-list
│   ├── .match-card
│   └── .match-result-badge
└── Responsive Breakpoints
```

---

## 📡 API Endpoints

### Endpoint Summary

| Endpoint | Method | View Function | Response Type |
|----------|--------|---------------|---------------|
| `/teams/<slug>/dashboard/` | GET | `team_dashboard_view` | HTML |
| `/teams/<slug>/` | GET | `team_profile_view` | HTML |
| `/teams/<slug>/follow/` | POST | `follow_team` | JSON |
| `/teams/<slug>/unfollow/` | POST | `unfollow_team` | JSON |
| `/teams/<slug>/update-roster-order/` | POST | `update_roster_order` | JSON |
| `/teams/<slug>/resend-invite/<id>/` | POST | `resend_invite` | JSON |

### Response Formats

**Success Response**:
```json
{
    "success": true,
    "message": "Action completed successfully",
    "data": {...}  // optional
}
```

**Error Response**:
```json
{
    "error": "Error description",
    "details": {...}  // optional
}
```

---

## 📈 Performance Optimization

### Backend Optimizations
1. ✅ `select_related()` for single FK lookups
2. ✅ `prefetch_related()` for many relationships
3. ✅ Aggregation queries for counts
4. ✅ Indexed database fields (slug, created_at)
5. ✅ Atomic transactions for data integrity

### Frontend Optimizations
1. ✅ CSS Grid/Flexbox (no heavy framework)
2. ✅ Native lazy loading for images
3. ✅ Debounced AJAX requests
4. ✅ Event delegation for dynamic content
5. ✅ Minimal JavaScript (no jQuery/React)

### Asset Optimization
1. ✅ Single CSS file per page
2. ✅ Single JS file per page
3. ✅ Inline critical CSS (optional)
4. ✅ Defer non-critical scripts
5. ✅ Compress/minify for production

---

## 🔄 Integration Points

### With Existing Systems

**Teams App**:
- ✅ Reuses existing Team, TeamMembership models
- ✅ Integrates with invite system
- ✅ Uses game_config for validation

**User Profile App**:
- ✅ Links to user profiles
- ✅ Displays avatars and display names

**Tournaments App**:
- ✅ Shows match history
- ✅ Links to tournament pages

**Social Features**:
- ✅ TeamPost integration
- ✅ TeamFollower system
- ✅ TeamActivity tracking

---

*Complete architecture for Task 4 implementation*
