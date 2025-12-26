# UP-UI-REDESIGN-01: Information Architecture

**Version:** 3.0  
**Date:** December 25, 2025  
**Goal:** Transform User Profile + Settings into a modern esports platform dashboard

---

## Profile Page Layout (/@username/)

### Module Hierarchy & Ordering

#### **1. HERO HEADER** (Always Visible)
- **Identity Block:**
  - Banner image (fullbleed, gradient fallback)
  - Avatar (rounded, verification badge overlay)
  - Display name (bold, uppercase)
  - Username (@username)
  - Level badge (optional)
  - Rank/Tier styling (border color based on rank)
  - Status indicator (Online/Offline/Away - if available)
  
- **Badge Pills:**
  - Verified ✓
  - Pro membership ⭐
  - Staff/Admin 🛡️
  - Tournament organizer 🎯
  
#### **2. DASHBOARD NAV** (Sticky, Below Hero)
- **Chip-style navigation:**
  - Overview (default scroll position)
  - Game Passports
  - Teams
  - Tournaments
  - Stats
  - Economy (owner only)
  - Shop (owner only)
  - Activity
  - About
- **Smooth scroll to sections**
- **Mobile:** Horizontal scroll with swipe

#### **3. QUICK ACTIONS ROW** (Right-aligned in nav bar)
- **Owner View:**
  - Edit Profile (indigo CTA)
  - Settings (icon button)
  - Share Profile (icon button)
  
- **Spectator View:**
  - Follow/Unfollow (emerald CTA)
  - Message (icon button)
  - Report (icon button, subtle)
  
- **Admin View (if flagged):**
  - All spectator actions +
  - Admin Tools (icon button) - links to admin panel

#### **4. OVERVIEW SECTION** (Grid Layout)

**4a. Quick Stats Strip** (4-6 metrics)
- Tournaments Played
- Win Rate
- Current Rank/Rating
- Reputation Score
- Active Since (account age)
- Last Active (if owner/admin)

**4b. Featured Achievements** (3-card carousel)
- Top 3 achievements with icons
- "View all" link

**4c. Current Status Card**
- Currently playing (if integrated)
- Tournament registrations (count)
- Team invitations pending (owner only)
- Notifications count (owner only)

#### **5. GAME PASSPORTS MODULE**
- **Featured Passports (Pinned):**
  - "Battle Card" design (from UP-UI-POLISH-04)
  - Game icon + name
  - IGN with copy button
  - Region, Rank, LFT badge
  - Team badge (or "Free Agent")
  - Visibility indicator (owner only)
  - Pin star indicator
  
- **More Games (Collapsible):**
  - Compact 2-column grid
  - Game icon + IGN + region
  - Quick stats (if available)
  
- **Empty State (No Passports):**
  - CTA: "Add Your First Game Passport" (owner)
  - Message: "No games added yet" (spectator)

#### **6. TEAMS MODULE**
- **Current Teams per Game:**
  - Team logo + name
  - Game badge
  - Role/Position
  - Team rank/tier
  - Status (Active, Bench, Trial)
  - Quick stats (team record if available)
  
- **Team Invitations (Owner only):**
  - Pending invites count
  - Accept/Decline actions
  
- **Free Agent Status:**
  - Per-game "Free Agent" card
  - LFT badge (if enabled in game passport)
  - "Looking for [Role]" indicator
  
- **Empty State:**
  - "Not on any teams yet" (spectator)
  - "Join your first team" CTA (owner)

#### **7. TOURNAMENTS MODULE**

**7a. Upcoming Tournaments**
- Registered tournaments (owner sees all, spectator sees public)
- Tournament banner + name
- Game badge
- Start date + time
- Prize pool
- Status badge (Registered, Check-in Required, etc.)

**7b. Recent Results**
- Last 5 tournaments
- Placement + prize earned
- Win/Loss record
- Link to tournament page

**7c. Quick Stats**
- Total tournaments: X
- Top placements: Y
- Total earnings: $Z
- Favorite game: [Game]

**Empty State:**
- "No tournaments yet" (spectator)
- "Find a tournament" CTA (owner)

#### **8. STATS MODULE**

**8a. Platform Stats** (Aggregate across all games)
- Overall win rate
- Total matches played
- Total tournament wins
- Platform rank (if exists)
- Reputation score trend

**8b. Per-Game Stats** (Tabs or carousel)
- Game selector
- Game-specific metrics (K/D, win rate, rank history, etc.)
- Match history preview (last 5)
- Rank progression graph (if data available)

**Empty State:**
- "No stats yet" + guidance

#### **9. ECONOMY MODULE** (Owner View + Public if explicitly shared)

**9a. Wallet Balances**
- DC Coins (platform currency)
- Cash balance (if payment system exists)
- Pending withdrawals
- Last transaction date

**9b. Lifetime Earnings**
- Tournament prizes
- Shop sales (if marketplace exists)
- Referral bonuses
- Total earned vs withdrawn

**9c. Recent Transactions** (Last 5)
- Transaction type (Prize, Purchase, Withdrawal, etc.)
- Amount
- Date
- Status
- "View all" link → full transaction history

**Spectator View:**
- Hidden by default
- Show "Earnings private" message
- If user has public earnings enabled, show lifetime earnings only (no balances)

**Empty State:**
- "No transactions yet"
- Link to shop/tournaments

#### **10. SHOP/ORDERS MODULE** (Owner Only)

**10a. Active Orders**
- Order number + date
- Items (name + quantity)
- Status (Processing, Shipped, Delivered)
- Tracking link (if available)

**10b. Recent Purchases** (Last 5)
- Item thumbnail
- Name + category
- Purchase date
- Price
- Download/View button (for digital goods)

**10c. Inventory/Owned Items**
- Digital goods count
- Membership status
- Active subscriptions

**10d. Shop Quick Actions**
- Browse shop
- View wishlist
- Manage subscriptions

**Empty State:**
- "No orders yet"
- "Browse shop" CTA

#### **11. ACTIVITY MODULE**

**11a. Recent Activity Feed** (Last 10 events)
- Event icon + type
- Event message
- Timestamp
- Related entity link (tournament, match, team, etc.)

**11b. Activity Types:**
- Tournament joined/completed
- Match won/lost
- Team joined/left
- Achievement earned
- Badge earned
- Level up
- Shop purchase
- Profile updated

**11c. "View All Activity" Link** → /activity/ page

**Empty State:**
- "No recent activity"

#### **12. ABOUT + SOCIAL + CONNECTIONS**

**12a. About Section**
- Bio (multi-line text)
- Location (country + region)
- Pronouns
- Languages spoken
- Favorite games
- Playing since (year)

**12b. Social Links**
- Discord
- Twitch
- YouTube
- Twitter/X
- Instagram
- Steam
- Epic Games
- Custom links

**12c. Connections** (If social graph exists)
- Friends count
- Followers count
- Following count
- Recent connections (avatars)

**Empty States:**
- "No bio yet" (with edit CTA for owner)
- "No social links"
- "No connections yet"

---

## Settings Hub Layout (/me/settings/)

### Navigation Structure

#### **Desktop Layout:**
- **Left Sidebar (fixed, 20% width):**
  - Navigation menu with icons
  - Active section highlighted
  - Collapsible groups
  
- **Main Content (80% width):**
  - Section header with breadcrumb
  - Content area
  - Save/Cancel actions at bottom

#### **Mobile Layout:**
- **Top Tabs:**
  - Horizontal scroll tabs
  - Active tab underlined
  - Content below tabs

### Settings Sections

#### **1. PROFILE DETAILS**
- **Basic Information:**
  - Display name
  - Bio (textarea, markdown preview)
  - Location (country + region dropdowns)
  - Pronouns (dropdown + custom)
  - Languages (multi-select)
  - Date of birth (privacy-aware)
  
- **Avatar & Banner:**
  - Avatar upload (drag & drop + file picker)
  - Banner upload
  - Crop/resize tool
  - Remove buttons
  
- **Public Profile URL:**
  - Custom slug (if available)
  - Copy profile link button
  
- **Visibility:**
  - Profile visibility (Public, Friends Only, Private)
  - Show online status toggle
  - Show activity feed toggle

#### **2. GAME PASSPORTS**
- **Passport List:**
  - All game passports (pinned at top)
  - Game icon + name
  - IGN
  - Region
  - Rank
  - Actions: Edit | Pin/Unpin | Delete
  
- **Add New Passport:**
  - Game selector (dropdown with search)
  - IGN input
  - Region selector
  - Rank/Tier selector
  - Visibility (Public, Friends, Private)
  - Looking for Team toggle
  - Preferred role/position (if game supports)
  
- **Bulk Actions:**
  - Pin/Unpin multiple
  - Change visibility for multiple
  - Delete multiple (with confirmation)
  
- **Passport Settings:**
  - Max pinned passports (display limit: 6)
  - Auto-update rank from APIs (if available)
  - Show passport stats on profile

#### **3. PRIVACY**
- **Profile Visibility:**
  - Who can view profile (Everyone, Friends, Only Me)
  - Who can see stats
  - Who can see economy data
  - Who can see activity feed
  
- **Game Passports:**
  - Default visibility for new passports
  - Override per-passport visibility
  
- **Social:**
  - Who can send friend requests
  - Who can message me
  - Who can see my connections
  
- **Activity:**
  - Show activity on profile
  - Show online status
  - Show last active time
  
- **Search & Discovery:**
  - Appear in player search
  - Appear in team search (LFT)
  - Allow tournament organizers to contact

#### **4. NOTIFICATIONS** (Stub OK)
- **Email Notifications:**
  - Tournament reminders
  - Team invitations
  - Match results
  - Shop order updates
  - Platform announcements
  
- **Push Notifications:**
  - Enable/disable toggle
  - Per-category toggles
  
- **In-App Notifications:**
  - Notification preferences
  - Sound/badge settings

#### **5. SECURITY** (Stub OK)
- **Password:**
  - Change password form
  - Show password strength
  
- **Two-Factor Authentication:**
  - Enable/disable 2FA
  - Setup QR code
  - Backup codes
  
- **Active Sessions:**
  - List of active sessions
  - Device + location + last active
  - "Sign out all other sessions" button
  
- **Login History:**
  - Recent logins with timestamps
  - IP addresses
  - Suspicious activity alerts

#### **6. ECONOMY/PAYMENTS** (Stub OK)
- **Wallet:**
  - View balances
  - Add funds (link to payment page)
  - Withdraw funds
  - Transaction history (full view)
  
- **Payment Methods:**
  - Saved cards/PayPal
  - Add/remove payment methods
  - Default payment method
  
- **Payouts:**
  - Payout preferences
  - Bank account info (secure)
  - Tax information (if required)
  
- **Billing History:**
  - Invoices
  - Receipts
  - Download buttons

#### **7. SHOP/ORDERS** (Stub OK)
- **Order History:**
  - All orders with filters (status, date)
  - Order details
  - Download invoices
  - Request refund
  
- **Inventory:**
  - Digital goods
  - Membership status
  - Active subscriptions
  
- **Wishlist:**
  - Items saved for later
  - Price alerts
  
- **Subscriptions:**
  - Active subscriptions
  - Cancel/modify buttons
  - Billing cycle info

#### **8. INTEGRATIONS** (Future)
- **Connected Accounts:**
  - Link Discord, Steam, Epic, etc.
  - OAuth connections
  - Permissions management
  
- **API Access:**
  - Developer API keys
  - Webhooks
  - Rate limits

---

## Role-Based Visibility Matrix

| Section/Module | Owner | Spectator | Admin | Notes |
|----------------|-------|-----------|-------|-------|
| **Profile Page** |
| Hero Header | ✅ Full | ✅ Full | ✅ Full + Admin badge | Everyone sees identity |
| Quick Actions | Edit/Settings | Follow/Message | Admin Tools | Role-specific buttons |
| Overview Stats | ✅ All metrics | ✅ Public only | ✅ All + debug info | Respects privacy |
| Game Passports | ✅ All (+ private) | ✅ Public only | ✅ All | Visibility per passport |
| Teams | ✅ All teams + invites | ✅ Active teams only | ✅ All | Pending invites owner-only |
| Tournaments | ✅ All registered | ✅ Completed public | ✅ All | Upcoming owner-only |
| Stats | ✅ Full stats | ✅ Public stats | ✅ Full | Controlled by privacy |
| **Economy** | ✅ Full wallet + history | ❌ Hidden (or public earnings if enabled) | ✅ Full + admin notes | Sensitive data |
| **Shop/Orders** | ✅ Full history | ❌ Hidden | ✅ Full + admin tools | Owner-only section |
| Activity | ✅ All events | ✅ Public events only | ✅ All | Privacy-filtered |
| About/Social | ✅ All fields + edit | ✅ Public fields | ✅ All | Location may be hidden |
| **Settings Hub** |
| All Settings | ✅ Full access | ❌ No access (404) | ✅ Read-only + override | Settings are owner-only |

### Visibility Rules

**Public by Default:**
- Display name, username, avatar, banner
- Public game passports
- Active team memberships
- Completed tournament results
- Public achievements
- Public activity events
- Social links

**Owner-Only by Default:**
- Email, phone, date of birth
- Private game passports
- Pending team invitations
- Registered upcoming tournaments
- Economy data (wallet, transactions)
- Shop orders & inventory
- Privacy settings
- Notification preferences
- Security settings

**Privacy-Controlled:**
- Bio, location, pronouns
- Overall stats (can be hidden)
- Activity feed (can be disabled)
- Online status
- Last active time

**Admin-Only Additions:**
- User flags (verified, banned, etc.)
- Moderation notes
- Account creation date
- Login history
- Admin action buttons

---

## Component Library

### Dashboard Card
```html
<div class="dashboard-card bg-slate-900/60 backdrop-blur-lg rounded-2xl p-6 border border-white/10 shadow-2xl">
    <div class="card-header flex items-center justify-between mb-5">
        <h2 class="text-xl font-black text-white uppercase flex items-center gap-2">
            <svg>...</svg>
            <span>Section Title</span>
        </h2>
        <a href="#" class="card-action">View All</a>
    </div>
    <div class="card-content">
        <!-- Content here -->
    </div>
</div>
```

### Stat Pill
```html
<div class="stat-pill text-center p-4 bg-slate-800/40 rounded-xl border border-white/10 hover:border-indigo-500/30 transition-colors">
    <div class="stat-value text-3xl md:text-4xl font-black text-indigo-400">123</div>
    <div class="stat-label text-xs text-slate-400 uppercase mt-2 font-semibold">Label</div>
</div>
```

### Section Header
```html
<div class="section-header flex items-center justify-between mb-6">
    <h2 class="text-2xl font-black text-white uppercase">Section</h2>
    <button class="btn-secondary">Action</button>
</div>
```

### Empty State
```html
<div class="empty-state text-center py-12 opacity-60 hover:opacity-100 transition-opacity">
    <div class="text-6xl mb-4">🎮</div>
    <h3 class="text-xl font-bold text-white mb-2">No Data Yet</h3>
    <p class="text-slate-400 mb-6">Description text here</p>
    <button class="btn-primary">Call to Action</button>
</div>
```

### Team Badge
```html
<div class="team-badge flex items-center gap-3 p-3 bg-slate-800/40 rounded-lg border border-white/10 hover:border-indigo-500/30 transition-colors">
    <img src="..." class="w-12 h-12 rounded-lg">
    <div class="flex-1 min-w-0">
        <p class="text-sm font-bold text-white truncate">Team Name</p>
        <p class="text-xs text-slate-400">Role • Game</p>
    </div>
    <span class="badge">Active</span>
</div>
```

### Tournament Card
```html
<div class="tournament-card p-4 bg-gradient-to-r from-indigo-600/20 to-purple-600/20 rounded-xl border border-indigo-500/30">
    <div class="flex items-start justify-between mb-3">
        <div class="flex-1">
            <h4 class="text-lg font-black text-white">Tournament Name</h4>
            <p class="text-sm text-indigo-300">Game • Region</p>
        </div>
        <span class="badge badge-success">Registered</span>
    </div>
    <div class="flex items-center gap-4 text-xs text-slate-300">
        <span>📅 Jan 15, 2025</span>
        <span>💰 $5,000</span>
        <span>👥 32 teams</span>
    </div>
</div>
```

---

## Design Tokens

### Colors (Esports Theme)
- **Background:** `slate-950` (page), `slate-900/60` (cards with blur)
- **Text:** `white` (primary), `slate-300` (secondary), `slate-400` (tertiary)
- **Borders:** `white/10` (default), `white/20` (hover), `indigo-500/30` (featured)
- **Accents:**
  - Primary CTA: `indigo-600` (hover: `indigo-700`)
  - Success: `emerald-600`
  - Warning: `amber-500`
  - Danger: `red-600`
  - Info: `blue-500`

### Typography
- **Display:** `font-black uppercase` (section headers)
- **Heading:** `font-bold` (subsections)
- **Body:** `font-normal` (content)
- **Label:** `text-xs uppercase tracking-wider` (form labels, pill labels)

### Spacing
- **Card padding:** `p-6` (desktop), `p-4` (mobile)
- **Section gap:** `gap-6` (desktop), `gap-4` (mobile)
- **Grid gaps:** `gap-4`

### Responsive Breakpoints
- **Mobile:** `< 768px` (sm:)
- **Tablet:** `768px - 1023px` (md:)
- **Desktop:** `≥ 1024px` (lg:)
- **Large:** `≥ 1280px` (xl:)

---

## Interaction Patterns

### Progressive Disclosure
- **More Games:** Collapsed by default, "Show X more games" button
- **Transaction History:** Show last 5, "View all" link
- **Activity Feed:** Show last 10, "View all activity" link
- **Achievements:** Show top 3, "View all" link

### Loading States
- **Skeleton loaders** for async content
- **Shimmer effect** on cards
- **Spinner** for actions (save, load more)

### Feedback
- **Toast notifications:** Success, error, info
- **Inline validation:** Form fields show errors immediately
- **Action confirmation:** Modals for destructive actions (delete passport, etc.)

### Animations
- **Smooth scroll:** 0.5s ease-in-out
- **Card hover:** Scale 1.02, translateY(-2px)
- **Collapse/expand:** max-height transition 0.4s
- **Toast slide-in:** slideInUp animation

---

## Mobile Optimizations

### Navigation
- **Dashboard nav:** Horizontal scroll with snap points
- **Settings tabs:** Horizontal scroll
- **Collapsible sections:** Accordion-style on mobile

### Layout
- **Grid → Stack:** 2-col grids become 1-col on mobile
- **Sidebar → Top:** Settings sidebar becomes top tabs
- **Fixed actions:** Quick actions stick to top

### Touch Targets
- **Minimum size:** 44x44px (WCAG AAA)
- **Spacing:** 8px between interactive elements
- **Swipe gestures:** Support for carousel navigation

### Performance
- **Lazy load images:** Load below fold after interaction
- **Infinite scroll:** For long lists (activity, transactions)
- **Code splitting:** Load JS per section as needed

---

## Accessibility

### Keyboard Navigation
- **Tab order:** Logical flow (hero → nav → sections)
- **Skip links:** "Skip to main content"
- **Focus traps:** Modals/dialogs contain focus
- **Keyboard shortcuts:** Optional (e.g., "/" for search)

### Screen Readers
- **Semantic HTML:** Proper heading hierarchy
- **ARIA labels:** Icon buttons, collapsible sections
- **Live regions:** Announcements for dynamic content
- **Alt text:** All images and icons

### Color Contrast
- **Text:** Minimum 4.5:1 (AA), target 7:1 (AAA)
- **Interactive elements:** 3:1 (AA)
- **Focus indicators:** High contrast, visible

### Forms
- **Labels:** All inputs have labels
- **Errors:** Clear, actionable error messages
- **Autocomplete:** Proper autocomplete attributes
- **Validation:** Both client and server-side

---

## Implementation Priority

### Phase 1 (MVP) - Current Sprint
- ✅ Hero header
- ✅ Dashboard nav
- ✅ Quick actions
- ✅ Game Passports module
- ✅ Activity module (basic)
- ✅ About + Social
- ✅ Settings hub (Profile + Game Passports + Privacy)

### Phase 2 - Next Sprint
- Teams module (with API integration)
- Tournaments module (with API integration)
- Stats module (per-game stats)
- Settings: Notifications, Security

### Phase 3 - Future
- Economy module (full wallet integration)
- Shop/Orders module
- Advanced stats (graphs, trends)
- Social graph (friends, followers)
- Settings: Economy/Payments, Integrations

---

## Technical Notes

### Backend Assumptions
- **Context variables** from `build_public_profile_context()`:
  - `profile` (safe dict)
  - `stats` (dict, may be None)
  - `activities` (list, may be empty)
  - `pinned_passports` (list)
  - `unpinned_passports` (list)
  - `social` (list, may be empty)
  - `is_owner` (bool)
  - `can_view` (bool)

- **Missing data handled gracefully:**
  - Check for None/empty before rendering
  - Show empty states with CTAs
  - Don't assume all fields exist

### URL Routing
- All URLs use `user_profile:*` namespace
- No hardcoded paths
- NoReverseMatch handled with try/except in template if needed

### Performance
- **Lazy load:** Images, heavy sections
- **Pagination:** Long lists (transactions, activity)
- **Caching:** Profile data cached for X minutes
- **CDN:** Static assets served from CDN

---

## Success Metrics

### User Experience
- **Page load time:** < 2s (initial), < 1s (cached)
- **Time to interactive:** < 3s
- **Mobile performance:** > 90 Lighthouse score
- **Accessibility:** > 95 Lighthouse score

### Engagement
- **Profile completeness:** Track % of fields filled
- **Settings usage:** Track which settings are most used
- **Module interaction:** Track which modules are expanded/clicked

### Quality
- **Bug rate:** < 1% of sessions encounter errors
- **Cross-browser:** Works in Chrome, Firefox, Safari, Edge (latest 2 versions)
- **Test coverage:** > 80% for critical paths

---

**Last Updated:** December 25, 2025  
**Version:** 3.0  
**Status:** APPROVED - Ready for Implementation
