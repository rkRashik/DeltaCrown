# Visual Testing Checklist - Frontend Integration

## 📸 What to Look For

This guide shows you **exactly** what should appear on each page after integration.

---

## 1. Dashboard (`/dashboard/`)

### Expected Layout:
```
┌─────────────────────────────────────────────────────────┐
│  [Logo] DeltaCrown          [Tournaments] [Teams] [👤]  │ ← Global Navbar
├─────────────────────────────────────────────────────────┤
│  Welcome, [Your Name]        [+ Create Team] Button     │
├───────────────┬──────────────────┬──────────────────────┤
│ MY TEAMS      │ TEAM INVITES     │ UPCOMING MATCHES     │
│ View All →    │ View All →       │ View All →           │
│               │                  │                      │
│ [Logo] Team 1 │ [Card] Invite 1  │ Tournament A         │
│ Name          │ From: Captain    │ Oct 15, 10:00        │
│ Game • 3/5    │ [Accept][Decline]│                      │
│               │                  │ Tournament B         │
│ [Logo] Team 2 │ [Card] Invite 2  │ Oct 20, 14:00        │
│ Name          │ From: Manager    │                      │
│ Game • 5/5    │ [Accept][Decline]│                      │
├───────────────┴──────────────────┴──────────────────────┤
│ MY REGISTRATIONS              │ PAYOUTS                │
│ Browse Tournaments →          │                        │
│                               │                        │
│ Tournament X - [Confirmed]    │ No payouts yet.        │
│ Tournament Y - [Pending]      │ Keep competing!        │
└───────────────────────────────┴────────────────────────┘
```

### Visual Checks:
- ✅ **Header**: "Welcome, [Name]" + "Create Team" button (top right)
- ✅ **Grid Layout**: 3 columns on desktop, 1 column on mobile
- ✅ **Team Logos**: Circular images or colored initials (e.g., "TW")
- ✅ **Invite Cards**: Blue/accent border, 2 buttons (Accept/Decline)
- ✅ **Status Badges**: Color-coded pills (green=confirmed, yellow=pending)
- ✅ **Icons**: 
  - 👥 Users icon for "My Teams"
  - ✉️ Envelope for "Team Invites"
  - 📅 Calendar for "Upcoming Matches"
  - 🏆 Trophy for "My Registrations"

### Empty States:
If no data, should show:
```
┌──────────────────────┐
│   👥 (large icon)    │
│                      │
│ You're not part of   │
│  any teams yet.      │
│                      │
│ [+ Create Your First │
│      Team]           │
└──────────────────────┘
```

---

## 2. Teams Hub (`/teams/`)

### Expected Layout:
```
┌─────────────────────────────────────────────────────────┐
│  Teams Hub                              [+ Create Team] │
├─────────────────────────────────────────────────────────┤
│  [Search] [Filter: All Games ▾] [Sort: Recent ▾]       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐         │
│  │ [Logo]    │  │ [Logo]    │  │ [Logo]    │         │
│  │ Team Name │  │ Team Name │  │ Team Name │         │
│  │ Valorant  │  │ CS:GO     │  │ PUBG      │         │
│  │ ⭐1250 pts│  │ ⭐980 pts │  │ ⭐1100 pts│         │
│  │ 5/5 👥    │  │ 4/5 👥    │  │ 5/6 👥    │         │
│  └───────────┘  └───────────┘  └───────────┘         │
│                                                         │
│  [Load More Teams]                                     │
└─────────────────────────────────────────────────────────┘
```

### Visual Checks:
- ✅ **Team Cards**: Hover effect (lift/glow)
- ✅ **Logos**: Displayed if uploaded, initials if not
- ✅ **Game Badge**: Colored chip/tag (e.g., "Valorant" in red)
- ✅ **Points**: Star icon + number
- ✅ **Roster Count**: Users icon + "5/5" format
- ✅ **Grid**: 3 columns desktop, 2 tablet, 1 mobile

---

## 3. Create Team (`/teams/create/`)

### Expected Layout:
```
┌─────────────────────────────────────────────────────────┐
│  Create Professional Team                               │
│  Build your esports roster from scratch                 │
├─────────────────────────────────────────────────────────┤
│  Step 1 of 3: Basic Information                         │
│  ●─────○─────○                                          │
│                                                         │
│  Team Name *                                            │
│  ┌─────────────────────────────────────────────────┐  │
│  │ Enter team name...                              │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  Team Tag *                                             │
│  ┌─────────────────────────────────────────────────┐  │
│  │ e.g., DTC, TW, PRO...                           │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  Game *                                                 │
│  ┌─────────────────────────────────────────────────┐  │
│  │ Select game ▾                                    │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  [Cancel]                              [Next Step →]   │
└─────────────────────────────────────────────────────────┘
```

### Visual Checks:
- ✅ **Progress Indicator**: Dots or steps (1 of 3, 2 of 3, 3 of 3)
- ✅ **Form Fields**: Clear labels with asterisk (*) for required
- ✅ **Validation**: Red error messages under invalid fields
- ✅ **Buttons**: 
  - "Cancel" = secondary/gray
  - "Next Step" = primary/blue
  - "Create Team" = primary/green (final step)

### After Submit:
```
┌─────────────────────────────────────────────────────────┐
│  ✅ Success!                                            │
│                                                         │
│  Your team has been created successfully!              │
│                                                         │
│  [View Team Profile]  [Invite Members]                 │
└─────────────────────────────────────────────────────────┘
```
- ✅ **Toast Notification**: Green, top-right corner
- ✅ **Redirect**: To team detail page `/teams/{slug}/`

---

## 4. Team Detail (`/teams/{slug}/`)

### Expected Layout:
```
┌─────────────────────────────────────────────────────────┐
│  ╔═══════════════════════════════════════════════════╗ │
│  ║ [Full-width banner image with gradient overlay]  ║ │
│  ║                                                   ║ │
│  ║  [Logo]  TEAM NAME              [Follow][Manage] ║ │
│  ║          Valorant • 1250 Points                  ║ │
│  ╚═══════════════════════════════════════════════════╝ │
├─────────────────────────────────────────────────────────┤
│  [Overview] [Roster] [Matches] [Stats] [Discussions]   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  About Team                                            │
│  ───────────────────────────────────────────────────── │
│  [Team bio text here...]                               │
│                                                         │
│  Roster (5 Members)                                    │
│  ───────────────────────────────────────────────────── │
│  👑 [Avatar] CaptainName  • Captain  • IGN: Player1   │
│  👤 [Avatar] PlayerName   • Player   • IGN: Player2   │
│  👤 [Avatar] PlayerName   • Player   • IGN: Player3   │
│  👤 [Avatar] PlayerName   • Player   • IGN: Player4   │
│  👤 [Avatar] PlayerName   • Player   • IGN: Player5   │
│                                                         │
│  Recent Matches                                        │
│  ───────────────────────────────────────────────────── │
│  ✅ W  vs Team A  (2-1)  • Oct 8, 2025                │
│  ❌ L  vs Team B  (0-2)  • Oct 5, 2025                │
└─────────────────────────────────────────────────────────┘
```

### Visual Checks:
- ✅ **Hero Section**: Full-width banner with team logo overlay
- ✅ **Captain Badge**: Crown icon (👑) next to captain's name
- ✅ **Role Tags**: Colored pills (Captain=gold, Player=blue, Sub=gray)
- ✅ **Tab Navigation**: Underline on active tab
- ✅ **Match Results**: Green checkmark (W) or red X (L)

---

## 5. Tournament Registration (`/tournaments/{slug}/register/`)

### Expected Layout:
```
┌─────────────────────────────────────────────────────────┐
│  Tournaments › Valorant Masters › Register              │
├─────────────────────────────────────────────────────────┤
│  Valorant Masters 2025                                  │
│  ───────────────────────────────────────────────────────│
│  [👥 Team Tournament] [💰 ৳500 Entry] [🏆 ৳50,000 Prize]│
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Step 1: Select Team                                   │
│  ○─────●─────○─────○                                   │
│                                                         │
│  Choose Your Team                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │ [Logo] My Team Name (5/5 members) ▾            │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  Roster Preview:                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 👑 [Avatar] Captain  • Valorant ID: captain123 │  │
│  │ 👤 [Avatar] Player1  • Valorant ID: player456  │  │
│  │ 👤 [Avatar] Player2  • Valorant ID: player789  │  │
│  │ 👤 [Avatar] Player3  • Valorant ID: player012  │  │
│  │ 👤 [Avatar] Player4  • Valorant ID: player345  │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  [← Back]                        [Continue to Payment →]│
└─────────────────────────────────────────────────────────┘
```

### Visual Checks:
- ✅ **Breadcrumbs**: Clickable path to tournament detail
- ✅ **Info Chips**: Colored badges for entry fee, prize, type
- ✅ **Step Indicator**: Progress dots (filled/unfilled)
- ✅ **Team Dropdown**: Shows team logo + name + member count
- ✅ **Roster Preview**: Auto-populated from TeamMembership
- ✅ **IGNs Displayed**: Each player's in-game name shown

### After Submission:
```
┌─────────────────────────────────────────────────────────┐
│  🎉 Registration Successful!                            │
│                                                         │
│  Confirmation Number: #12345                           │
│                                                         │
│  Your team "My Team Name" has been registered for      │
│  Valorant Masters 2025.                                │
│                                                         │
│  Entry Fee: ৳500 (Paid via Wallet)                     │
│  Registration Date: Oct 10, 2025                       │
│                                                         │
│  [View Registration Status] [Return to Dashboard]      │
└─────────────────────────────────────────────────────────┘
```
- ✅ **Modal**: Centered, blur background
- ✅ **Confetti Animation**: (Optional) Celebratory effect
- ✅ **Confirmation Number**: Bold, large text
- ✅ **Action Buttons**: Two CTAs for next steps

---

## 6. Mobile Views (375px width)

### Dashboard Mobile:
```
┌─────────────────┐
│ ☰  DeltaCrown  │ ← Hamburger menu
├─────────────────┤
│ Welcome, Name   │
│ [+ Create Team] │
├─────────────────┤
│ MY TEAMS        │
│ View All →      │
│                 │
│ [Logo] Team 1   │
│ Game • 5/5      │
├─────────────────┤
│ TEAM INVITES    │
│ View All →      │
│                 │
│ [Card] Invite   │
│ [Accept][Decline│
├─────────────────┤
│ UPCOMING MATCHES│
│ View All →      │
│                 │
│ Tournament A    │
│ Oct 15, 10:00   │
└─────────────────┘
```

### Visual Checks:
- ✅ **Single Column**: All widgets stacked vertically
- ✅ **Touch Targets**: Buttons minimum 44x44px
- ✅ **Font Sizes**: Readable without zoom (16px+)
- ✅ **Spacing**: Adequate padding between elements
- ✅ **Overflow**: No horizontal scroll

---

## 7. Toast Notifications

### Success Toast:
```
┌─────────────────────────────┐
│ ✅ Team created successfully│  ← Green background
│                         [X] │
└─────────────────────────────┘
```

### Error Toast:
```
┌─────────────────────────────┐
│ ❌ Team name already exists │  ← Red background
│                         [X] │
└─────────────────────────────┘
```

### Info Toast:
```
┌─────────────────────────────┐
│ ℹ️  Invite sent to user@... │  ← Blue background
│                         [X] │
└─────────────────────────────┘
```

### Visual Checks:
- ✅ **Position**: Top-right or bottom-center
- ✅ **Icon**: Checkmark, X, or info symbol
- ✅ **Close Button**: X in top-right of toast
- ✅ **Animation**: Slide in from right/top
- ✅ **Auto-dismiss**: Fades out after 5 seconds
- ✅ **Stacking**: Multiple toasts stack vertically

---

## 8. Navigation Bar

### Desktop:
```
┌───────────────────────────────────────────────────────────┐
│ [Logo] DeltaCrown  [Tournaments] [Teams] [Players]  [👤]  │
└───────────────────────────────────────────────────────────┘
```

### Mobile:
```
┌─────────────────┐
│ ☰  DeltaCrown  │
└─────────────────┘

(When menu opened:)
┌─────────────────┐
│ ☰  DeltaCrown  │
├─────────────────┤
│ Home            │
│ Tournaments     │
│ Teams           │
│ Players         │
│ Dashboard       │
│ Profile         │
│ Logout          │
└─────────────────┘
```

### Visual Checks:
- ✅ **Active Link**: Underline or highlight on current page
- ✅ **Hover Effect**: Color change on desktop
- ✅ **Logo**: Clickable, returns to home
- ✅ **User Dropdown**: Avatar shows user picture
- ✅ **Mobile Menu**: Slides from left, overlay background

---

## 9. Form Validation

### Before Submit:
```
Team Name *
┌─────────────────────────────┐
│ [User typing...]            │
└─────────────────────────────┘
```

### After Invalid Submit:
```
Team Name *
┌─────────────────────────────┐
│ AB                          │  ← Red border
└─────────────────────────────┘
❌ Team name must be at least 3 characters.
```

### After Valid Input:
```
Team Name *
┌─────────────────────────────┐
│ Amazing Warriors ✅          │  ← Green border/checkmark
└─────────────────────────────┘
```

### Visual Checks:
- ✅ **Error State**: Red border + red text below
- ✅ **Success State**: Green border + checkmark (optional)
- ✅ **Focus State**: Blue glow/outline on active field
- ✅ **Disabled State**: Gray background, no cursor
- ✅ **Required Fields**: Asterisk (*) in label

---

## 10. Empty States

### No Teams:
```
┌─────────────────────────────┐
│        👥                   │
│     (large icon)            │
│                             │
│ You're not part of any      │
│ teams yet.                  │
│                             │
│ [+ Create Your First Team]  │
└─────────────────────────────┘
```

### No Invites:
```
┌─────────────────────────────┐
│        ✉️                   │
│                             │
│ No pending invites.         │
└─────────────────────────────┘
```

### No Matches:
```
┌─────────────────────────────┐
│        📅                   │
│                             │
│ No upcoming matches.        │
└─────────────────────────────┘
```

### Visual Checks:
- ✅ **Centered**: Content centered in widget
- ✅ **Large Icon**: 4xl size (64px+)
- ✅ **Muted Color**: Gray/low opacity
- ✅ **CTA Button**: Only if actionable
- ✅ **Helpful Text**: Clear, concise message

---

## 🎨 Color Palette Reference

```
Primary:   #3B82F6 (blue)
Accent:    #8B5CF6 (purple)
Success:   #10B981 (green)
Error:     #EF4444 (red)
Warning:   #F59E0B (yellow)
Info:      #3B82F6 (blue)

Text:      #E5E7EB (light gray)
Muted:     #9CA3AF (gray)
Background:#0A0A0F (dark)
Glass:     rgba(255,255,255,0.05) (translucent)
```

---

## ✅ Final Checklist

Print and check off as you visually inspect:

```
Dashboard:
[ ] Header displays with name and button
[ ] 4-6 widgets visible in grid
[ ] Team logos display or show initials
[ ] Status badges are color-coded
[ ] Empty states show helpful CTAs
[ ] All links clickable and styled

Team Hub:
[ ] Team cards in grid layout
[ ] Hover effects work
[ ] Game badges colored correctly
[ ] Search and filters visible

Create Team:
[ ] Form fields have labels and placeholders
[ ] Step indicator shows progress
[ ] Validation messages appear on error
[ ] Success modal shows after creation

Team Detail:
[ ] Hero banner displays with gradient
[ ] Team logo overlays banner
[ ] Roster shows with captain crown
[ ] Tabs are clickable and highlight active

Tournament Registration:
[ ] Breadcrumbs display at top
[ ] Info chips show entry fee and prize
[ ] Team dropdown populates
[ ] Roster preview auto-loads
[ ] Success modal appears on completion

Mobile:
[ ] All widgets stack vertically
[ ] Navigation collapses to hamburger
[ ] Buttons are tap-friendly (44px+)
[ ] Text is readable (16px+)
[ ] No horizontal scrolling

Toasts:
[ ] Appear in correct position
[ ] Show correct color for type
[ ] Display icon and message
[ ] Auto-dismiss after 5 seconds
[ ] Can be manually closed

Navigation:
[ ] Logo clickable
[ ] Active link highlighted
[ ] Dropdown works on click
[ ] Mobile menu slides in
```

---

**Visual Testing Complete?** ✅  
**Everything looks correct?** 🎉  
**Ready for production?** 🚀

If all checks pass, proceed to production deployment!
