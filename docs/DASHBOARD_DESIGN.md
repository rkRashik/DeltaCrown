# DeltaCrown Dashboard — Complete Design & Implementation Guide

> **Route:** `/dashboard/`  
> **Template:** `templates/dashboard/index.html`  
> **View:** `apps/dashboard/views.py → dashboard_index()`  
> **Audience:** This document is for UI/UX designers, frontend developers, and product stakeholders who need to understand, redesign, or extend the main user dashboard.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Current Implementation](#2-current-implementation)
3. [Design System](#3-design-system)
4. [Data Sources & Context](#4-data-sources--context)
5. [Current Layout Grid](#5-current-layout-grid)
6. [Section-by-Section Breakdown](#6-section-by-section-breakdown)
7. [Interactive Features](#7-interactive-features)
8. [Missing Features & Gaps](#8-missing-features--gaps)
9. [Proposed Enhancements](#9-proposed-enhancements)
10. [New Widget Ideas](#10-new-widget-ideas)
11. [Responsive Behavior](#11-responsive-behavior)
12. [Animation & Motion](#12-animation--motion)
13. [Empty States](#13-empty-states)
14. [Performance Considerations](#14-performance-considerations)
15. [Technical Implementation Notes](#15-technical-implementation-notes)

---

## 1. Architecture Overview

### How It Works

The dashboard is a **model-less aggregation layer** — it owns zero database tables. It pulls data from **13 different data sources** across **9 apps** in a single Django view, then renders a bento-grid layout.

```
User hits /dashboard/
        │
        ▼
dashboard_index()
        │
        ├── 1.  user_profile.UserProfile         → avatar, display_name, LFT status
        ├── 2.  organizations.TeamMembership      → teams, roles, member counts
        ├── 3.  organizations.TeamInvite           → pending invites (accept/decline)
        ├── 4.  competition.MatchReport            → recent match cards
        ├── 5.  competition.MatchReport            → W/L/D aggregate stats
        ├── 6.  tournaments.Registration + Match   → active tournaments, next match
        ├── 7.  leaderboards.LeaderboardEntry      → ranking position, points
        ├── 8.  economy.DeltaCrownWallet           → coin balance, recent txns
        ├── 9.  user_profile.UserBadge             → achievement badges
        ├── 10. notifications.Notification         → recent alerts, unread count
        ├── 11. user_profile.Follow                → follower/following counts
        ├── 12. ecommerce.Order                    → recent store orders
        └── 13. organizations.OrganizationMembership → org roles, verified status
                │
                ▼
        templates/dashboard/index.html
        (Bento grid, inline CSS/JS, ~706 lines)
```

### Key Architecture Decisions

- **Graceful degradation:** Every data section is wrapped in `try/except`. If any model is missing, schema changed, or DB is down, the dashboard still renders — that section simply shows an empty state.
- **Safe model loading:** `_safe_model("app.Model")` returns `None` instead of crashing if a model doesn't exist.
- **No external CSS/JS:** All styles and scripts are inline in the template. No dependencies on external dashboard-specific static files.
- **Login required:** Protected by `@login_required` — unauthenticated users are redirected to login.

---

## 2. Current Implementation

### Files

| File | Purpose | Lines |
|------|---------|-------|
| `apps/dashboard/__init__.py` | App config | 1 |
| `apps/dashboard/apps.py` | `DashboardConfig` | ~5 |
| `apps/dashboard/urls.py` | 3 URL patterns | ~12 |
| `apps/dashboard/views.py` | 2 views (504 lines) | ~504 |
| `apps/dashboard/forms.py` | `MyMatchesFilterForm` (legacy) | ~20 |
| `templates/dashboard/index.html` | Main bento dashboard | ~706 |
| `templates/dashboard/matches.html` | Legacy matches page | ~38 |
| `templates/dashboard/my_matches.html` | Extends matches.html | ~4 |

### URL Routes

| URL | View | Name | Status |
|-----|------|------|--------|
| `/dashboard/` | `dashboard_index` | `dashboard:index` | **Active** — main command center |
| `/my/matches/` | `my_matches_view` | `dashboard:my_matches` | Legacy compat — stub |
| `/dashboard/matches/` | `my_matches_view` | `dashboard:matches` | Preferred route — stub |

### Navigation Entry Points

The dashboard is linked from:
- Desktop navigation bar
- User profile dropdown menu
- Mobile hamburger menu
- Footer quick links

---

## 3. Design System

### Color Palette

The dashboard uses a **dark cosmic theme** with colored accent glows per section:

| Accent | Color | CSS Class | Used For |
|--------|-------|-----------|----------|
| Cyan | `#06b6d4` | `glow-cyan` | Teams, general actions |
| Amber | `#eab308` | `glow-amber` | Invites, wallet, rankings, DC coins |
| Purple | `#a855f7` | `glow-purple` | Tournaments, badges |
| Green | `#10b981` | `glow-green` | Win rate, accept actions |
| Blue | `#3b82f6` | `glow-blue` | Matches, record |
| Rose | `#f43e5e` | `glow-rose` | Notifications, LIVE matches, orders |
| Indigo | `#6366f1` | `glow-indigo` | Organizations, profile |

### CSS Variables

```css
--b-surface: rgba(255,255,255,0.025);   /* Tile background */
--b-border:  rgba(255,255,255,0.06);    /* Tile border */
--b-hover:   rgba(255,255,255,0.08);    /* Hover state */
--b-radius:  1.25rem;                    /* Border radius (20px) */
```

### Base Component: `.bt` (Bento Tile)

Every dashboard card uses the `.bt` class:
- Semi-transparent background (`rgba(255,255,255,0.025)`)
- Subtle border (`rgba(255,255,255,0.06)`)
- `border-radius: 1.25rem` (20px)
- On hover: border brightens, card lifts −2px, optional glow shadow appears

### Typography Scale

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Page title (Welcome) | `xl → 2xl` | Bold | White w/ cyan gradient |
| Stat value | `28px` | 900 (Black) | White or accent |
| Stat label | `10px` | 700 | `rgba(255,255,255,0.35)` uppercase |
| Tile title | `13px` | 700 | `rgba(255,255,255,0.75)` |
| Body text | `12px` | 600 | `rgba(255,255,255,0.55)` |
| Tertiary text | `10px` | Normal | `rgba(255,255,255,0.30)` |

### Iconography

- Primary icon library: **Font Awesome 6** (fa-solid, fa-regular)
- Icon containers: `28×28px` rounded-lg with accent-colored background (10–15% opacity)
- Icon size: `10–11px` inside containers

### Interaction States

| State | Visual |
|-------|--------|
| Default | Subtle border, dark surface |
| Hover | Border brightens, −2px lift, colored glow shadow |
| Active/Pressed | — (not styled) |
| Disabled | `opacity-50`, `pointer-events-none` |
| Loading | Pulse animation |
| LIVE | Red pulse, red border, red gradient background |

---

## 4. Data Sources & Context

### Context Variables Passed to Template

```python
context = {
    # Profile
    "profile": {
        "display_name": str,       # Resolved: member > profile > username
        "avatar_url": str | None,  # MEDIA_URL + path
        "slug": str,               # URL slug for profile page
        "lft_status": str | None,  # Looking For Team status
        "kyc_status": str,         # KYC verification status
    },

    # Teams
    "my_teams": [                  # Up to 8 teams
        {
            "id": int,
            "name": str,
            "slug": str,
            "logo_url": str | None,
            "role": str,           # OWNER, MANAGER, PLAYER, etc.
            "game_name": str,
            "member_count": int,
            "tag": str,            # Team tag / abbreviation
            "status": str,         # ACTIVE, etc.
        }
    ],
    "team_count": int,

    # Pending Invites
    "pending_invites": [           # Up to 5 invites
        {
            "id": int,
            "team_name": str,
            "team_slug": str,
            "team_logo": str | None,
            "role": str,           # Invited as what role
            "inviter": str,        # Username of whoever sent invite
            "created_at": datetime,
            "expires_at": datetime,
        }
    ],
    "invite_count": int,

    # Match History
    "recent_matches": [            # Up to 6 matches
        {
            "id": int,
            "team1_name": str,
            "team2_name": str,
            "result": str,         # WIN, LOSS, DRAW
            "match_type": str,
            "game_name": str,
            "created_at": datetime,
            "score_team1": int | None,
            "score_team2": int | None,
        }
    ],
    "match_stats": {
        "wins": int,
        "losses": int,
        "draws": int,
        "total": int,
        "win_rate": int,           # 0-100
    },

    # Tournaments
    "active_tournaments": [        # Up to 8 tournaments
        {
            "id": int,
            "name": str,
            "slug": str,
            "status": str,         # registration_open, live, completed
            "game_name": str,
            "game_icon": str | None,
            "scheduled_at": datetime | None,
            "tournament_start": datetime | None,
            "prize_pool": Decimal | None,
            "format": str,
            "reg_status": str,     # User's registration status
            "is_live": bool,
        }
    ],
    "tournament_count": int,       # Distinct tournaments

    # Next Match (urgent CTA — conditional)
    "next_match_info": {           # None if no upcoming match
        "match_id": int,
        "tournament_name": str,
        "tournament_slug": str,
        "opponent_name": str,
        "scheduled_time": datetime | None,
        "state": str,             # scheduled, check_in, ready, live
        "is_live": bool,
    } | None,

    # Leaderboard
    "leaderboard_data": [          # Up to 3 entries
        {
            "rank": int,
            "points": int,
            "leaderboard_type": str,
            "game_name": str,
            "wins": int,
            "losses": int,
            "win_rate": float,
        }
    ],

    # Economy
    "wallet": {
        "balance": float,
        "has_wallet": bool,
        "recent_txns": [           # Up to 5 transactions
            {
                "amount": float,   # Positive = credit, negative = debit
                "reason": str,
                "created_at": datetime,
            }
        ],
    },

    # Badges
    "badges": [                    # Up to 6 badges
        {
            "name": str,
            "icon": str,           # URL or icon class
            "description": str,
            "rarity": str,
            "awarded_at": datetime | None,
        }
    ],

    # Notifications
    "recent_notifications": [      # Up to 8 notifications
        {
            "id": int,
            "type": str,           # invite_sent, invite_accepted, match_result, etc.
            "title": str,
            "body": str,
            "url": str,
            "is_read": bool,
            "created_at": datetime,
            "action_type": str,
            "action_object_id": int | None,
        }
    ],
    "unread_notif_count": int,

    # Social
    "social_stats": {
        "followers": int,
        "following": int,
    },

    # E-commerce
    "recent_orders": [             # Up to 3 orders
        {
            "id": int,
            "status": str,        # COMPLETED, PENDING, etc.
            "total": float,       # In DC coins
            "created_at": datetime,
        }
    ],

    # Organizations
    "my_organizations": [          # Up to 5 orgs
        {
            "id": int,
            "name": str,
            "slug": str,
            "logo_url": str | None,
            "role": str,          # CEO, MANAGER, PLAYER, etc.
            "is_verified": bool,
            "team_count": int,    # Teams in this org
            "joined_at": datetime,
        }
    ],
    "org_count": int,

    # Game reference data
    "games": list[str],           # List of game names
}
```

---

## 5. Current Layout Grid

The dashboard uses a **12-column bento grid** system with responsive breakpoints:

```
┌──────────────────────────────────────────────────────────────┐
│                        HEADER                                │
│  [Avatar] Welcome back, {name}          [🔔] [🏪 Store] [⚙] │
├──────────────────────────────────────────────────────────────┤
│              PENDING INVITES BANNER (conditional)            │
│  [Invite Card →] [Invite Card →] [Invite Card →]  (scroll)  │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Teams (3)  │ Win Rate (3) │ Tourneys (3) │ DC Coins (3)  │
│     stat     │    stat      │     stat     │     stat       │
├──────────────┴──────────────┴──────────────┼────────────────┤
│                                            │                │
│            MY TEAMS (span-8)               │  PROFILE (4)   │
│   [Team][Team]   (2-col grid inside)       │  Avatar/stats  │
│   [Team][Team]                             │  Follow counts │
│                                            │                │
├─────────────┬──────────────────────────────┼────────────────┤
│ Record (3)  │    RECENT MATCHES (5)        │  WALLET (4)    │
│  W: 12      │  [match row]                 │  120 DC        │
│  L: 5       │  [match row]                 │  +5, -10, ...  │
│  D: 2       │  [match row]                 │                │
├─────────────┴──────────────────────────────┴────────────────┤
│         NEXT MATCH CTA (span-12, conditional)                │
│  ⚔ vs OpponentName · Tournament · Time    [Enter Match Room] │
├─────────────────────────────────────┬───────────────────────┤
│      TOURNAMENT ACTIVITY (7)       │  ORGANIZATIONS (5)    │
│  [Card][Card]  (2-col grid)        │  [Org row]            │
│  [Card][Card]                      │  [Org row]            │
├─────────────┬──────────────────────┼───────────────────────┤
│ Notifs (4)  │   Rankings (4)       │    Badges (4)         │
│ [alert]     │   #1 Championship   │  [🏅][🏅][🏅]         │
│ [alert]     │   #3 Regional       │  [🏅][🏅][🏅]         │
│ [alert]     │                      │                       │
├─────────────┴──────────────────────┴───────────────────────┤
│                    QUICK ACTIONS (span-12)                   │
│  [+ Create Team] [My Teams] [Tournaments] [Report Match]    │
│  [Crown Store] [Find Players] [Spectator] [Profile] [⚙]    │
├──────────────────────────────────────────────────────────────┤
│              RECENT ORDERS (span-12, conditional)            │
│  [Order #123: 50 DC] [Order #124: 120 DC]                   │
└──────────────────────────────────────────────────────────────┘
```

### Responsive Breakpoints

| Breakpoint | Columns | Behavior |
|------------|---------|----------|
| Desktop (≥1024px) | 12 columns, 16px gap | Full bento grid, all tiles visible |
| Tablet (640–1023px) | 6 columns, 16px gap | Tiles collapse: `span-3/4/5` → 3, `span-7/8` → 6 |
| Mobile (<640px) | 2 columns, 12px gap | All tiles span 2, stat tiles span 1 |

---

## 6. Section-by-Section Breakdown

### 6.1 Header
- **Content:** Avatar + "Welcome back, {display_name}" greeting + @username
- **Actions:** Notification bell (with unread badge), Store link, Settings gear
- **Design:** Flex row, responsive wrapping, gradient text for name

### 6.2 Pending Invites Banner
- **Conditional:** Only shown when `pending_invites` is non-empty
- **Layout:** Horizontal scrollable row of invite cards (260–300px min-width each)
- **Each card:** Team logo + name, inviter + role info, Accept/Decline buttons
- **Interaction:** AJAX accept/decline via `dashInvite(id, action)`, card fades out on success
- **API endpoint:** `POST /notifications/api/team-invite/{id}/{action}/`
- **Accent:** Amber (urgency)

### 6.3 Stat Tiles Row
Four `span-3` tiles showing key metrics:
1. **Teams** — `team_count` (cyan)
2. **Win Rate** — `match_stats.win_rate`% (green)
3. **Tournaments** — `tournament_count` (purple)
4. **DC Coins** — `wallet.balance` (amber)

### 6.4 My Teams
- **Span:** 8
- **Layout:** 2-column grid of team cards
- **Each card:** Logo → Team name [tag] → Role · Game · Member count → Chevron
- **Empty state:** "No teams yet" + Create Team CTA
- **Link:** Each card links to `/teams/{slug}/`

### 6.5 Profile Card
- **Span:** 4
- **Content:** Large avatar, display name, username
- **Stats:** 3-column grid (Teams, Followers, Following)
- **LFT Badge:** Green status indicator if LFT is active
- **CTA:** "View Public Profile →" button

### 6.6 Match Record
- **Span:** 3
- **Content:** Wins (green), Losses (red), Draws (amber), Total count
- **Visual:** Large bold numbers with colored accents

### 6.7 Recent Matches
- **Span:** 5
- **Layout:** Vertical list of match rows (max 200px height, scrollable)
- **Each row:** Team1 vs Team2 (with score if available), game name, time ago, result badge
- **Result badges:** `badge-win` (green), `badge-loss` (red), `badge-draw` (amber)
- **Empty state:** Gamepad icon + "No matches yet"

### 6.8 Wallet
- **Span:** 4
- **Hero stat:** Large balance number with "DC" suffix
- **Recent txns:** List of last 3 transactions with +/− amounts (green/red)
- **Accent:** Amber/gold

### 6.9 Next Match CTA
- **Conditional:** Only shown when `next_match_info` exists
- **Span:** 12 (full width)
- **Two states:**
  - **LIVE:** Red pulsing border, red gradient BG, bolt icon with `animate-pulse`, "🔴 Your match is LIVE!" text, "Enter Match Room" red button
  - **Upcoming:** Cyan border, swords icon, "⚔ Next Match" text, opponent + tournament + time, "Match Room" button
- **Link:** `/tournaments/{slug}/matches/{id}/room/`

### 6.10 Tournament Activity
- **Span:** 7
- **Layout:** 2-column grid (max 210px height, scrollable)
- **Each card:** Tournament name, status badge (LIVE/REGISTRATION_OPEN/COMPLETED), game icon + name, prize pool, date
- **Status colors:** LIVE = red pulse, Registration = cyan, Completed = green
- **Empty state:** Crown icon + "No tournament activity"

### 6.11 Organizations
- **Span:** 5
- **Layout:** Vertical list of org rows
- **Each row:** Logo → Org name (+ verified badge) → Role · Team count
- **Empty state:** Building icon + "No organization" + "Join or create" message

### 6.12 Notifications
- **Span:** 4
- **Layout:** Vertical list (max 200px, scrollable), 6 items max
- **Each item:** Type icon → Title → Time ago → Unread indicator (cyan dot + left border)
- **Type icons:** Envelope (invite), checkmark (accepted), flag (match result), bell (default)
- **Link:** "All →" links to `/notifications/`

### 6.13 Rankings
- **Conditional:** Only shown when `leaderboard_data` is non-empty
- **Span:** 4
- **Layout:** Stacked rank cards centered
- **Each card:** Large rank# (amber), leaderboard type, game name, points/W/L stats

### 6.14 Badges
- **Conditional:** Only shown when `badges` is non-empty
- **Span:** 4 (or 8 if no leaderboard data)
- **Layout:** 3-column grid
- **Each badge:** Icon (image or fallback medal), name text below
- **Hover:** Scale 110% on icon

### 6.15 Quick Actions
- **Span:** 12
- **Layout:** Flex wrap row of 9 action pills
- **Pills:** Create Team, My Teams, Tournaments, Report Match, Crown Store, Find Players, Spectator, My Profile, Settings
- **Style:** `.qa-pill` with cyan hover glow

### 6.16 Recent Orders
- **Conditional:** Only shown when `recent_orders` is non-empty
- **Span:** 12
- **Layout:** Horizontal scroll of order cards (180px min-width)
- **Each card:** Order ID, total in DC, time ago, status badge

---

## 7. Interactive Features

### Currently Implemented

1. **Invite Accept/Decline**
   - AJAX POST to `/notifications/api/team-invite/{id}/{action}/`
   - On success: Card fades out with opacity + scale + translateY animation
   - On error: Shows inline red error message for 5 seconds
   - CSRF token read from cookie

2. **Tile Hover Effects**
   - All `.bt` tiles lift −2px and brighten border on hover
   - Section-specific glow shadows appear on hover

3. **Staggered Load Animation**
   - `.bf` class with `bfade` keyframe (opacity + translateY)
   - 8 delay stages: `.bf1` through `.bf8` (30ms increments)

### Not Yet Implemented

- No real-time data updates (WebSocket/SSE)
- No drag-and-drop tile reordering
- No theme/layout customization
- No data refresh without full page reload (except invites)
- No skeleton loading states
- No toast notification system

---

## 8. Missing Features & Gaps

### Critical Gaps

| Gap | Impact | Priority |
|-----|--------|----------|
| No real-time updates | Stale data until page refresh | HIGH |
| No skeleton loading states | Blank tiles during initial load | HIGH |
| No "Mark all read" for notifications | Users must visit notifications page | MEDIUM |
| Match history is from MatchReport only | Doesn't include tournament bracket matches | HIGH |
| Wallet has no direct "Add Funds" CTA | Missed conversion opportunity | MEDIUM |
| No game passport summary | Users can't see their game identity at a glance | MEDIUM |
| No calendar/schedule widget | Match and tournament dates are scattered | HIGH |
| No activity graph (GitHub-style) | Hard to see engagement over time | LOW |
| Badges section has no "View All" link | Users may not know they have more | LOW |
| Profile card lacks edit CTA | Extra click to get to settings | LOW |
| No join request status (pending team applications) | Users can't track their status | HIGH |
| `/my/matches/` and `/dashboard/matches/` are stubs | Dead routes | LOW |

### Data Gaps

| Data Available But Not Shown | Source |
|------------------------------|--------|
| Game passport (IGN, rank, region) | `user_profile.GameProfile` |
| Join request status (pending applications) | `organizations.TeamJoinRequest` |
| User's upcoming scrimmages | `competition.Scrimmage` |
| Community feed/posts | `siteui.Post` |
| Achievement progress (partial badges) | `user_profile.UserBadge` |
| Team performance trends | `competition.MatchReport` aggregates |
| Notification preferences quick toggle | `notifications.NotificationPreference` |

---

## 9. Proposed Enhancements

### 9.1 Real-Time Dashboard (WebSocket/SSE)

**Problem:** Dashboard data is frozen at page load time.

**Solution:** Add a lightweight SSE (Server-Sent Events) endpoint that pushes incremental updates:
- New notification → update bell badge + notifications tile
- Match state change → update Next Match CTA (scheduled → check_in → live)
- Invite received → inject new invite card
- Wallet balance change → update coin counter with animation

**Implementation:**
```
GET /dashboard/stream/ → text/event-stream
Events: notification, match_update, invite, wallet_update
```

### 9.2 Game Passport Widget

**Problem:** Users can't see their in-game identity (IGN, rank, stats) from the dashboard.

**Proposal:** Add a "Game Passport" tile (span-4 or span-6) showing:
- Current game IGN + discriminator
- Rank badge + rank image
- Matches played, win rate, K/D
- Region flag
- Platform icon
- Multi-game tabs if user plays multiple games

### 9.3 Schedule / Calendar Widget

**Problem:** Match times and tournament dates are scattered across tiles.

**Proposal:** Add a "This Week" timeline tile (span-6 or span-8):
- Horizontal timeline showing next 7 days
- Match dots, tournament checkpoints, invite expirations
- "Today" highlighted
- Click to expand day → see all events

### 9.4 Join Request Tracker

**Problem:** Users who applied to teams can't see their application status.

**Proposal:** Add a "My Applications" card (span-4) or integrate into the Invites banner:
- Shows pending join requests with team name, when applied, status
- Ability to withdraw directly from dashboard
- Notification when application is accepted/declined

### 9.5 Quick Match Report

**Problem:** Users must navigate to `/competition/` to report a match result.

**Proposal:** Add a floating action button or a "Report Match" mini-form embedded in the Recent Matches tile:
- Select team → select opponent → enter score → submit
- Instant feedback without leaving dashboard

### 9.6 Activity Heatmap

**Problem:** No visual representation of user engagement over time.

**Proposal:** GitHub-style contribution graph (span-12 or span-8):
- Show matches played, tournaments entered, login streaks
- Color intensity = activity level
- Hover for daily breakdown

### 9.7 User Level / XP Progress Bar

**Problem:** No gamification beyond badges.

**Proposal:** Add an XP/Level system shown prominently in the header or profile card:
- XP earned from: matches played, tournaments completed, badges earned, daily login
- Level badge next to username
- Progress bar to next level
- "Level Up" celebration animation

### 9.8 Dashboard Customization

**Problem:** Users can't rearrange or hide tiles.

**Proposal (long-term):**
- Pin/unpin tiles
- Reorder via drag-and-drop
- Compact vs expanded tile modes
- Save layout preference in `UserProfile.dashboard_layout` (JSON field)

### 9.9 Team Activity Feed

**Problem:** No visibility into what's happening on user's teams.

**Proposal:** Add a "Team Activity" tile (span-6) showing:
- New member joins
- Match results
- Roster changes
- Tournament registrations
- Last 24-48 hours of activity across all teams

### 9.10 Skeleton Loading States

**Problem:** Dashboard is blank until all 13 queries finish.

**Proposal:**
- Render tile shells immediately with shimmer/skeleton placeholders
- Use `htmx` or `fetch` to load each tile asynchronously
- Progressive rendering: stat tiles first (fastest), then teams, then matches, etc.
- Each tile loads independently — no waterfall

---

## 10. New Widget Ideas

### Game-Specific Widgets

| Widget | Description | Game |
|--------|-------------|------|
| Map Stats | Win rate per map (Valorant, CS2) | FPS |
| Agent/Character Pool | Most played agents with win rates | Valorant, Apex |
| Formation Display | Team's preferred formation | eFootball, FIFA |
| Rank Progression | Line graph of rank over time | Any ranked game |

### Social Widgets

| Widget | Description |
|--------|-------------|
| LFT Matches | Players looking for team in same game/region |
| Friend Activity | What your followed players are doing |
| Community Posts | Latest posts from teams/players you follow |
| Scrimmage Finder | Quick scrimmage matchmaking |

### Competitive Widgets

| Widget | Description |
|--------|-------------|
| Upcoming Events | Community and official events calendar |
| Prize Earnings | Total prize money earned breakdown |
| Win Streak Indicator | Current streak (hot/cold indicator) |
| Rivalry Card | Most-played opponent, head-to-head record |
| Map Veto Prep | Upcoming match map preferences |

### Economy / E-Commerce

| Widget | Description |
|--------|-------------|
| Daily Rewards | Login streak + daily collectible |
| Flash Deals | Time-limited Crown Store offers |
| Gift Notifications | Someone sent you DC coins or items |

---

## 11. Responsive Behavior

### Current Implementation

```
Desktop (≥1024px):  12 columns, 16px gap
Tablet (640-1023):  6 columns,  16px gap  
Mobile (<640px):    2 columns,  12px gap
```

### Recommended Improvements

1. **Mobile priority ordering:** Use CSS `order` to push urgent tiles (Next Match, Invites) to top on mobile
2. **Collapsible sections:** Allow folding less-important tiles on mobile (badges, orders)
3. **Bottom nav on mobile:** Pin quick actions to bottom of viewport
4. **Swipeable tiles:** On mobile, allow left/right swipe between related tiles (matches ↔ record)
5. **Touch-optimized:** Increase tap targets to 44px minimum on mobile

---

## 12. Animation & Motion

### Current Animations

| Animation | Element | CSS |
|-----------|---------|-----|
| Fade-in stagger | All tiles | `bfade` keyframe, 30ms stagger per `.bf1`-`.bf8` |
| Hover lift | `.bt` tiles | `transform: translateY(-2px)` |
| Glow on hover | Sections | `box-shadow: 0 8px 32px rgba(accent, 0.08)` |
| Invite dismiss | Cards | `opacity: 0`, `scale(0.95)`, `translateY(-8px)` over 300ms |
| LIVE pulse | Next Match CTA | `animate-pulse` on bolt icon |

### Proposed Animation Additions

| Animation | Trigger | Effect |
|-----------|---------|--------|
| Counter roll-up | Page load | Stat values count from 0 to actual (300ms) |
| Badge sparkle | Page load | Brief sparkle on newest badge |
| Progress fill | Page load | Win rate / XP bar fills over 500ms |
| Card enter | AJAX load | Slide-in from right with opacity transition |
| Notification ping | New notification via SSE | Shake + glow on bell icon |
| Wallet +/- | Balance change | Flash green/red on amount |
| Streak fire | Active win streak | Fire particle on streak indicator |

---

## 13. Empty States

### Current Empty States

| Section | Visual | Text |
|---------|--------|------|
| My Teams | `fa-users` icon + CTA | "No teams yet" + "Create or join a team to start competing." + [Create Team] |
| Recent Matches | `fa-gamepad` icon | "No matches yet" |
| Tournaments | `fa-crown` icon | "No tournament activity" |
| Organizations | `fa-building` icon | "No organization" + "Join or create an organization" |
| Notifications | Text only | "No notifications" |

### Proposed Empty State Improvements

- Add **illustration SVGs** instead of plain icons (character art in brand style)
- Include **specific CTAs** for each empty state:
  - Matches: "Report a Match" button
  - Tournaments: "Browse Tournaments" button
  - Organizations: "Create Organization" button
- Add **onboarding checklist** for new users:
  - [ ] Complete your profile
  - [ ] Add a game passport
  - [ ] Create or join a team
  - [ ] Enter your first tournament
  - [ ] Report a match result

---

## 14. Performance Considerations

### Current Performance Profile

The `dashboard_index` view makes **13 sequential try/except blocks**, each hitting the database. With SQL query counting, this produces roughly:

| Query Group | Estimated Queries |
|------------|------------------|
| Profile lookup | 1 |
| Team memberships + teams | 1-2 |
| Member counts (per team) | N (up to 8) |
| Pending invites | 1 |
| Recent matches | 1 |
| Match stats aggregation | 1 |
| Tournament registrations | 1-2 |
| Next match | 1 |
| Leaderboard entries | 1 |
| Wallet + transactions | 2 |
| Badges | 1 |
| Notifications + count | 2 |
| Social stats (2 count queries) | 2 |
| Orders | 1 |
| Org memberships + team counts | N+1 |
| Games lookup | 1 |
| **Total** | **~20-30 queries** |

### Optimization Strategies

1. **Aggregate member/team counts with annotations** instead of per-team count queries
2. **Cache game_map** (rarely changes) with `@lru_cache` or Django cache
3. **Prefetch related objects** where possible (e.g., team logos, org logos)
4. **Async tile loading:** Render shell HTML server-side, load individual tile data via AJAX — this removes all queries from the main request
5. **Redis cache layer:** Cache entire dashboard context per user with 60s TTL
6. **Database views:** Create a materialized view for match stats aggregation

---

## 15. Technical Implementation Notes

### Adding a New Widget

1. **Add data source to view:** In `apps/dashboard/views.py`, add a new section between the existing try/except blocks:
   ```python
   # ── N. MY DATA ──
   my_data = []
   try:
       Model = _safe_model("app.Model")
       if Model:
           my_data = list(Model.objects.filter(user=user).values(...)[:10])
   except Exception:
       pass
   ```

2. **Add to context dict:** Include `"my_data": my_data` in the context assembly block.

3. **Add tile HTML:** In `templates/dashboard/index.html`, insert a new tile within the `.bento-grid`:
   ```html
   <div class="span-4 bt p-5 bf bf8 glow-cyan">
     <div class="tile-label">
       <div class="tile-icon bg-cyan-500/10"><i class="fa-solid fa-icon text-cyan-400 text-[11px]"></i></div>
       <span class="tile-title">My Widget</span>
     </div>
     {% if my_data %}
     <!-- render content -->
     {% else %}
     <div class="empty"><p class="text-[10px] text-white/30">No data</p></div>
     {% endif %}
   </div>
   ```

### Adding Interactivity (AJAX)

For any tile that needs user interaction:

1. Add an API endpoint in the relevant app (not in dashboard — keep dashboard read-only)
2. Add inline JS at the bottom of `index.html` inside `{% block extra_js %}`
3. Use the existing `_csrf()` function for CSRF tokens
4. Follow the `dashInvite()` pattern: disable buttons → fetch → animate result → cleanup

### Template Dependencies

The main template extends `base.html` and loads:
- `{% load static %}` — static file tags
- `{% load humanize %}` — `timesince`, `intcomma`, etc.

No other template tags are currently used (the `dashboard_widgets` tag library exists but is **not loaded** by the template).

### Testing

The dashboard view is largely untestable in isolation due to the 13-service dependency. Recommended approach:
- **Unit test** each data section independently (mock other models as `None`)
- **Integration test** with `_safe_model` returning `None` for all models — verify empty dashboard renders without errors
- **Smoke test** with a logged-in user — verify HTTP 200 response

---

## Appendix: Design Tokens Quick Reference

```css
/* Backgrounds */
Page BG:        #020005 → #080818 → #020005 (gradient)
Tile BG:        rgba(255,255,255,0.025)
Inner card BG:  rgba(255,255,255,0.02)

/* Borders */
Tile border:    rgba(255,255,255,0.06)
Hover border:   rgba(255,255,255,0.12)
Inner border:   rgba(255,255,255,0.04)

/* Text */
Primary:        #ffffff
Secondary:      rgba(255,255,255,0.75)
Tertiary:       rgba(255,255,255,0.45)
Muted:          rgba(255,255,255,0.30)
Ghost:          rgba(255,255,255,0.15)

/* Accent colors */
Cyan:           #06b6d4    (teams, general)
Emerald:        #10b981    (wins, positive)
Amber:          #eab308    (coins, urgency)
Purple:         #a855f7    (tournaments)
Blue:           #3b82f6    (matches)
Rose:           #f43e5e    (live, alerts)
Indigo:         #6366f1    (organizations)
Red:            #ef4444    (losses, errors)

/* Radius */
Tile:       20px (1.25rem)
Card:       12px (0.75rem)
Button:     10px (0.625rem)
Badge:      8px  (0.5rem)
Full:       9999px (pill)
```

---

*Last updated: March 2026*  
*Maintained by: DeltaCrown Engineering*
