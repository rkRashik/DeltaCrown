# PART 4.5: SPECTATOR, MOBILE & ACCESSIBILITY

**Navigation:**
- [← Previous: PART_4.4 - Registration & Payment Flow](PART_4.4_REGISTRATION_PAYMENT_FLOW.md)
- [→ Next: PART_4.6 - Animation Patterns & Conclusion](PART_4.6_ANIMATION_PATTERNS_CONCLUSION.md)
- [↑ Back to Index](INDEX_MASTER_NAVIGATION.md)

---

1. **Eligible Recipients** (auto-populated)
   - List of placements (1st, 2nd, 3rd, Top 8, etc.)
   - Select which placements receive certificates
   - Checkbox: Include all participants (participation certificate)

2. **Certificate Template Selection & Preview**
   
   **Preview Screen Layout:**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ Preview Certificate                         [× Close]   │
   ├────────────────────────────────────────────────────────┤
   │ ┌──────────────────────┬─────────────────────────────┐ │
   │ │ Configuration        │ Live Certificate Preview    │ │
   │ │                      │                             │ │
   │ │ Template:            │ ╔═══════════════════════╗   │ │
   │ │ ○ Gold (1st Place)   │ ║  DeltaCrown          ║   │ │
   │ │ ● Silver (2nd Place) │ ║  Certificate         ║   │ │
   │ │ ○ Bronze (3rd)       │ ║                      ║   │ │
   │ │ ○ Standard           │ ║  [Team Name]         ║   │ │
   │ │                      │ ║  2nd Place           ║   │ │
   │ │ Logo Placement:      │ ║  Tournament Name     ║   │ │
   │ │ [Upload Logo]        │ ║  ৳10,000 Prize       ║   │ │
   │ │ Preview: [logo.png]  │ ║                      ║   │ │
   │ │ Position: Top-Center │ ║  [Organizer Logo]    ║   │ │
   │ │                      │ ║  [Signature]         ║   │ │
   │ │ Signature:           │ ║  [QR Code] CERT-123  ║   │ │
   │ │ [Upload Signature]   │ ╚═══════════════════════╝   │ │
   │ │ Preview: [sign.png]  │                             │ │
   │ │ Position: Bottom-Right│ [Download Sample PDF]      │ │
   │ │                      │                             │ │
   │ │ Achievement Text:    │                             │ │
   │ │ ┌──────────────────┐ │                             │ │
   │ │ │ has achieved     │ │                             │ │
   │ │ │ 2nd Place in...  │ │                             │ │
   │ │ └──────────────────┘ │                             │ │
   │ │                      │                             │ │
   │ │ Additional Notes:    │                             │ │
   │ │ ┌──────────────────┐ │                             │ │
   │ │ │ Outstanding...   │ │                             │ │
   │ │ └──────────────────┘ │                             │ │
   │ └──────────────────────┴─────────────────────────────┘ │
   ├────────────────────────────────────────────────────────┤
   │                   [Cancel] [Apply to All Certificates] │
   └────────────────────────────────────────────────────────┘
   ```
   
   **Preview Features:**
   - **Real-time Updates:** Certificate preview refreshes as you type/upload
   - **Template Themes:**
     - Gold: Gold border, trophy icon, #FFD700 accents
     - Silver: Silver border, medal icon, #C0C0C0 accents
     - Bronze: Bronze border, ribbon icon, #CD7F32 accents
     - Standard: Blue brand color, participation trophy
   - **Logo Placement Options:**
     - Top-Center (above title)
     - Top-Left (corner)
     - Watermark (centered, semi-transparent background)
     - None (DeltaCrown branding only)
   - **Signature Options:**
     - Upload image (PNG with transparency, max 500KB)
     - Use text signature (typed name in script font)
     - None (DeltaCrown official only)
     - Position: Bottom-Right, Bottom-Center, Bottom-Left
   - **Download Sample PDF:** Generate one certificate PDF to review before bulk issuance
   - **Zoom Controls:** 50%, 75%, 100%, 150% (to inspect details)
   
   **Customization Options:**
   - Achievement description (text, 200 char max)
   - Organizer signature (upload image or use typed name)
   - Organizer logo (upload, positioned as selected)
   - Additional notes (appears at bottom, 100 char max)
   - Certificate dimensions: A4 landscape (297x210mm, 1920x1080px at 150 DPI)

3. **Featured Winners** (toggle for each placement)
   - Mark winners as "Featured" (displays on public tournament page)
   - Featured certificates appear in platform-wide "Hall of Fame"

4. **Bulk Actions:**
   - **"Preview All"** — Generate PDF previews for review
   - **"Issue Certificates"** — Sends certificates to all recipients
   - Auto-notification to recipients (email + platform notification)
   - Certificates appear in player "Tournament History"

5. **Post-Issuance:**
   - View issued certificates list
   - Revoke certificate (rare, requires reason, notifies recipient)
   - Re-issue (if corrections needed)

### 8.4 Profile Integration

**Purpose:** Display tournament stats and achievements on user profile.

**Location:** `/profile/<username>` (existing DeltaCrown profile page)

**New Sections Added:**

**Tournament Stats Card:**
- Tournaments participated: 24
- Wins / Losses: 8 / 16
- Best placement: 🥇 Champion
- Total prizes: ৳15,000
- Favorite game: VALORANT

**Achievements & Badges:**
- Grid of unlocked badges
- Examples:
  - "First Tournament" 🎮
  - "Champion" 🏆 (with count if multiple)
  - "Perfect Attendance" ✅
  - "Community Champion" 💬 (for active participants)
- Hover for description and unlock date

**Recent Tournaments:**
- List of 5 most recent tournaments
- Quick stats (placement, date)
- "View All" link to tournament history

**Certificates Showcase:**
- Carousel of earned certificates
- Only featured certificates shown publicly
- Click to view full certificate

---

## 9. Spectator & Community Screens

### 9.1 Spectator View

**Purpose:** Engaging view for non-participants to follow tournament action.

**URL:** `/tournaments/<slug>/spectate` or `/tournaments/<slug>/live`

**Features:**

**Live Tournament Hub:**
- **Hero Section:** Featured stream embed (largest ongoing match)
- **Live Matches Grid:** All currently live matches with thumbnails
- **Upcoming Matches:** Schedule with countdown timers
- **Bracket Overview:** Mini bracket with live match highlights
- **Leaderboard:** Current standings (for round robin or group stages)

**Match Cards (Spectator View):**
- Current score (real-time)
- Team names and logos
- "Watch" button (opens match page)
- Viewer count
- Game time elapsed

**Engagement Features:**

1. **Match Predictions with Lock Timers** (Fan Vote Widget)
   
   **Widget Layout:**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ 🔮 Predict the Winner                                  │
   ├────────────────────────────────────────────────────────┤
   │ ⏱️ Predictions lock in: 05:32                          │  ← Countdown timer
   │                                                         │
   │ ┌────────────────────┐  ┌────────────────────┐        │
   │ │  Team Alpha        │  │  Team Beta          │        │
   │ │  [Logo]            │  │  [Logo]             │        │
   │ │  65% (1,234 votes) │  │  35% (654 votes)    │        │
   │ │  [Vote ▶]          │  │  [Vote ▶]           │        │
   │ └────────────────────┘  └────────────────────┘        │
   │                                                         │
   │ Your Prediction: None yet · Earn 5 DC if correct! 🪙   │
   └────────────────────────────────────────────────────────┘
   ```
   
   **After Voting:**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ 🔮 Your Prediction                                      │
   ├────────────────────────────────────────────────────────┤
   │ ⏱️ Predictions locked · Match starting soon            │
   │                                                         │
   │ ┌────────────────────┐  ┌────────────────────┐        │
   │ │  Team Alpha ✓      │  │  Team Beta          │        │  ← Checkmark on voted team
   │ │  [Logo]            │  │  [Logo]             │        │
   │ │  68% (1,456 votes) │  │  32% (680 votes)    │        │
   │ │  YOUR VOTE         │  │                     │        │
   │ └────────────────────┘  └────────────────────┘        │
   │                                                         │
   │ ✓ Locked in! Results revealed after match              │
   └────────────────────────────────────────────────────────┘
   ```
   
   **Countdown Timer Features:**
   - **Live countdown:** Updates every second using JavaScript
   - **Lock time:** 5 minutes before match start (configurable by organizer)
   - **Color coding:**
     - Green (> 10 min): Plenty of time
     - Yellow (5-10 min): Hurry up!
     - Red (< 5 min): Closing soon!
     - Locked: Gray with lock icon 🔒
   - **Animation:** Timer pulses when < 1 minute remaining
   - **Auto-lock:** Predictions auto-close at 00:00, voting buttons disabled
   - **WebSocket sync:** Countdown synced across all spectators
   
   **Post-Match Results:**
   - Reveal correct prediction with green highlight
   - Wrong prediction: Red highlight (friendly)
   - Display: "You earned 5 DC! 🎉" or "Better luck next time!"
   - Update leaderboard: "Top Predictors" with accuracy %
   - Streak tracking: "🔥 5-match prediction streak!"

2. **MVP Voting Widget**
   
   **Widget Layout (During/After Match):**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ 🏆 Vote for MVP                                        │
   ├────────────────────────────────────────────────────────┤
   │ ⏱️ Voting closes in: 02:15 after match ends            │  ← Countdown (15 min window)
   │                                                         │
   │ ┌──────────────────────────────────────────────────┐   │
   │ │ [Avatar] PlayerOne        Team Alpha    [Vote]   │   │
   │ │          453 votes (32%) ████░░░░                 │   │  ← Progress bar
   │ └──────────────────────────────────────────────────┘   │
   │                                                         │
   │ ┌──────────────────────────────────────────────────┐   │
   │ │ [Avatar] PlayerTwo        Team Alpha    [Vote] ✓ │   │  ← Voted
   │ │          689 votes (49%) ████████░                │   │
   │ └──────────────────────────────────────────────────┘   │
   │                                                         │
   │ ┌──────────────────────────────────────────────────┐   │
   │ │ [Avatar] PlayerThree      Team Beta     [Vote]   │   │
   │ │          268 votes (19%) ███░░░░░                 │   │
   │ └──────────────────────────────────────────────────┘   │
   │                                                         │
   │ Your Vote: PlayerTwo · Total Votes: 1,410              │
   └────────────────────────────────────────────────────────┘
   ```
   
   **MVP Announcement (Post-Voting):**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ 🏆 MATCH MVP                                            │
   ├────────────────────────────────────────────────────────┤
   │         ╔════════════════════════╗                      │
   │         ║   [Avatar - Large]     ║                      │
   │         ║                        ║                      │
   │         ║   PlayerTwo            ║                      │
   │         ║   Team Alpha           ║                      │
   │         ║                        ║                      │
   │         ║   689 votes (49%)      ║                      │
   │         ║   +50 DC Bonus 🪙       ║                      │
   │         ╚════════════════════════╝                      │
   │                                                         │
   │ 🎊 Confetti animation plays 🎊                          │  ← Confetti trigger
   └────────────────────────────────────────────────────────┘
   ```
   
   **Features:**
   - **Vote Weight System:**
     - Verified match participants: 3x weight
     - Logged-in spectators: 1x weight
     - Anonymous viewers: Cannot vote (must log in)
   - **Live Updates:** Vote counts update in real-time (WebSocket)
   - **One Vote Per User:** Cannot change vote after submission
   - **Voting Window:** Opens when match ends, closes 15 minutes later
   - **Countdown Timer:** Shows time remaining to vote (same styling as predictions)
   - **MVP Bonus:** Winner earns 50 DC automatically credited
   - **MVP Badge:** "🏆 MVP" badge appears on player profile for this tournament

3. **Live Reactions**
   - Emoji reactions: 🔥 Fire, 👏 Applause, 😱 Shocked, ⚡ Clutch
   - Reactions float up on screen (like live stream reactions)
   - Aggregated count: "🔥 245 reactions"
   - Rate limit: 1 reaction per 5 seconds

4. **Highlight Reels** (post-match)
   - Curated clips section on tournament page
   - Organizer or community uploads highlights
   - Timestamp links to VOD (if stream archived)
   - Upvote best highlights
   - Filter: Best Plays, Funny Moments, Clutches, Upsets

5. **Confetti Animation** (Result Publish Celebration)
   
   **Triggers:**
   - Match result published (winner announced)
   - MVP voting result revealed
   - Tournament champion crowned (finals)
   - Perfect game achieved (13-0, 3-0 sweep)
   
   **Animation Specification:**
   - **Library:** canvas-confetti.js (lightweight, 6KB gzipped)
   - **Duration:** 1.5 seconds
   - **Particle Count:** 150 pieces
   - **Colors:** Brand colors (#3B82F6, #8B5CF6, #F59E0B, #10B981)
   - **Origin:** Center-top of widget/screen
   - **Spread:** 70° cone angle
   - **Gravity:** 1 (realistic fall)
   - **Shapes:** Squares, circles (no custom shapes to keep performance)
   - **Performance:** Uses requestAnimationFrame, GPU-accelerated
   
   **Code Example:**
   ```javascript
   // Trigger confetti on MVP announcement
   function celebrateMVP() {
       confetti({
           particleCount: 150,
           spread: 70,
           origin: { y: 0.3 },
           colors: ['#3B82F6', '#8B5CF6', '#F59E0B', '#10B981']
       });
       
       // Second burst after 300ms for extra flair
       setTimeout(() => {
           confetti({
               particleCount: 100,
               angle: 60,
               spread: 55,
               origin: { x: 0 }
           });
           confetti({
               particleCount: 100,
               angle: 120,
               spread: 55,
               origin: { x: 1 }
           });
       }, 300);
   }
   ```
   
   **User Control:**
   - **Reduced Motion:** Respects `prefers-reduced-motion: reduce` (no animation)
   - **Disable Option:** User settings > "Disable celebration animations"
   - **Mobile:** Reduced particle count (75 pieces) for performance

6. **Shareable Result Cards** (auto-generated OG images)
   - After each match: Generate shareable card
   - Design: Team logos, final score, tournament branding
   - Templates for:
     - Match Results (standard)
     - **Upsets** (lower seed beats higher seed) → **Confetti animation on page load**
     - **Finals Results** (champion announcement) → **Double confetti burst**
     - **Perfect Game** (13-0, 3-0, etc.) → **Gold confetti**
   - One-click share to Twitter/Facebook/Instagram Stories
   - Cards include: "View Tournament on DeltaCrown [link]"

6. **Share Tournament**
   - Social media buttons with pre-filled text
   - Copy tournament link with tracking (referral stats)
   - Embed code for tournament widget (iframe)

### 9.2 Community Discussions

**Purpose:** Forum-style discussions for each tournament with rich interaction features.

**URL:** `/tournaments/<slug>/discussions`

**Features:**
- **Discussion threads** for tournament
- Categories: General, Match Predictions, Highlights, Disputes
- Create new thread (requires login)
- Reply to threads (nested comments, up to 5 levels deep)
- Upvote/downvote system
- Organizer/Admin badges on posts
- Report inappropriate content

**Rich Text Features (HTMX-powered):**

1. **@Mentions**
   - Type `@username` to mention users
   - Autocomplete dropdown appears after typing `@`
   - Shows avatars + usernames of participants/organizers
   - Mentioned users receive notification
   - Mention styling: Blue highlight, clickable to user profile
   - **Implementation:** HTMX autocomplete endpoint `/api/mentions?q=username`
   
   **Example:**
   ```
   Hey @PlayerOne, did you see that clutch play? 🔥
   ```

2. **Rich Media Embeds** (Link Previews)
   - Paste URL → Auto-generates preview card
   - **Supported:**
     - YouTube/Twitch videos: Embed player
     - Twitter posts: Embedded tweet
     - Images (direct links): Inline image
     - DeltaCrown tournament links: Rich tournament card
   - **Implementation:** HTMX triggers `/api/link-preview?url=...` on paste
   - Preview loads asynchronously (doesn't block post submission)
   - **Lazy Loading:** Preview renders only when comment is visible
   
   **Example Preview Card:**
   ```
   ┌────────────────────────────────────────┐
   │ 🎥 YouTube Video Preview               │
   │ ┌──────────────────────────────────┐   │
   │ │  [Thumbnail]                     │   │
   │ │  ▶️ Best VALORANT Plays          │   │
   │ └──────────────────────────────────┘   │
   │ 5:32 · 12K views                       │
   └────────────────────────────────────────┘
   ```

3. **GIF Support**
   - GIF picker button in comment editor
   - **Integration:** Tenor API or GIPHY
   - Search GIFs by keyword
   - Inline GIF display in comments
   - Max size: 5MB, auto-resize if larger
   - **Lazy Loading:** GIFs load on scroll
   - **Accessibility:** Alt text required for GIFs

4. **Emoji Reactions** (Quick Responses)
   - React to comments without replying
   - Common reactions: 👍 👎 😂 ❤️ 🔥 💀
   - Hover shows who reacted
   - One reaction per user per comment
   - Aggregated count: "👍 23"

**Comment Editor UI:**

```
┌────────────────────────────────────────────────────────┐
│ Write a Comment...                                      │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Hey @PlayerOne, great match! Check this out:       │ │  ← @mention autocomplete
│ │ https://youtube.com/...                            │ │
│ │                                                     │ │
│ │ [YouTube Preview Card Renders Here]                │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ [😊 Emoji] [🎬 GIF] [📎 Attach] [**B** *I*]          │  ← Formatting toolbar
│                                      [Cancel] [Post]   │
└────────────────────────────────────────────────────────┘
```

**Formatting Toolbar:**
- **Bold:** `**text**` → **text**
- **Italic:** `*text*` → *text*
- **Link:** Auto-detects URLs, renders as hyperlinks
- **Code:** `` `code` `` → `code` (inline)
- **Quote:** `> text` → Blockquote style

**Moderation & Content Filtering:**

1. **Auto-Moderation Rules:**
   - **Profanity Filter:** Blocks/flags common slurs and offensive words
   - **Spam Detection:** 
     - Same message posted > 3 times = auto-hide
     - External links from new accounts = require approval
     - Rate limit: Max 10 comments per 5 minutes per user
   - **Link Whitelist:** 
     - Allow: YouTube, Twitch, Twitter, DeltaCrown, imgur
     - Block: Suspicious domains, phishing links
     - Unknown domains: Require organizer approval

2. **Manual Moderation Actions** (Organizer/Admin):**
   - **Edit Comment:** Organizer can edit inappropriate content (logged)
   - **Hide Comment:** Visible only to author and mods
   - **Delete Comment:** Permanent removal (requires reason)
   - **Ban User:** From tournament discussions (temporary or permanent)
   - **Lock Thread:** Prevent new comments (for resolved disputes)
   - **Pin Comment:** Sticky comment at top (for announcements)

3. **Moderation Queue:**
   - Flagged comments appear in organizer dashboard
   - Actions: Approve, Hide, Delete, Ban User
   - Bulk moderation: Select multiple comments
   - Mod log: All actions timestamped with moderator name

4. **User Reporting:**
   - **Report Comment** button on each comment
   - Report reasons:
     - Spam or misleading
     - Harassment or hate speech
     - Inappropriate content
     - Violates tournament rules
   - Report goes to moderation queue
   - Reporters remain anonymous

**Thread Card (Enhanced):**
- Thread title (clickable)
- Author avatar, name, organizer/admin badge
- Posted time (relative: "2 hours ago")
- Reply count, upvote count
- **Emoji Reactions Bar:** 👍23 🔥15 💬8 (quick response without replying)
- Latest reply preview (first 100 chars)
- Tags (if applicable): #highlights #dispute
- **Rich Media Indicator:** 🎥 (if video), 🖼️ (if image), 🎬 (if GIF)
- **Pinned Indicator:** 📌 (if moderator pinned)

**Reactions Feature (Quick Responses):**

```
┌────────────────────────────────────────────────────────┐
│ Comment by PlayerOne · 2 hours ago                      │
├────────────────────────────────────────────────────────┤
│ That clutch play was insane! Best moment of the match. │
├────────────────────────────────────────────────────────┤
│ Reactions:  👍 23  🔥 15  😂 5  ❤️ 8  💀 3             │  ← Reaction bar
│                                                         │
│ [Add Reaction ➕]  [Reply]  [Report]                   │
└────────────────────────────────────────────────────────┘
```

**Reaction Options:**
- 👍 Thumbs Up (like, agree)
- 👎 Thumbs Down (disagree)
- 😂 Laugh (funny)
- ❤️ Heart (love it)
- 🔥 Fire (amazing, lit)
- 💀 Skull (dead from laughing, brutal)

**Reaction Behavior:**
- **One Reaction Per User:** Can react once per comment, can change reaction
- **Hover Shows Users:** Hover over reaction count shows list of users who reacted
- **Real-time Updates:** New reactions appear immediately (WebSocket)
- **Sorting:** Comments can be sorted by "Most Reacted"
- **Analytics:** `data-analytics-id="comment_reaction_[emoji]"`

**Pinned Comments (Moderator Feature):**

**Pin Action** (Organizer/Admin only):
- Right-click comment → "Pin Comment" option
- Or three-dot menu → "📌 Pin to Top"
- Confirmation: "This comment will appear at the top of the discussion."

**Pinned Comment Display:**
```
┌────────────────────────────────────────────────────────┐
│ 📌 PINNED BY ORGANIZER                                 │  ← Yellow banner
├────────────────────────────────────────────────────────┤
│ Comment by TournamentOrganizer · Pinned 1 day ago      │
│                                                         │
│ Important Update: Match schedule changed to 6 PM BST   │
│ due to technical issues. All teams notified via email. │
│                                                         │
│ Reactions:  👍 45  ❤️ 12                               │
│ [Reply]                                                 │
└────────────────────────────────────────────────────────┘
```

**Pinned Comment Features:**
- **Yellow/Gold Background:** Stands out visually (bg: `#FFFBEB`)
- **Pin Icon:** 📌 prefix on title
- **Always at Top:** Appears above all other comments (even when sorted)
- **Multiple Pins:** Support up to 3 pinned comments per thread
- **Unpin Action:** Moderator can unpin (removes from top, returns to timeline)
- **Notification:** Thread participants get notification when comment is pinned
- **Analytics:** `data-analytics-id="comment_pin_action"`

### 9.3 Social Features

**Purpose:** Enhance community engagement and shareability.

**Features Throughout Platform:**

**Social Sharing:**
- Tournament cards: Share button
- Match results: Share scoreboard image
- Certificates: Auto-generate social media posts
- Achievements: Share badge unlocks

**Social Media Integration:**
- **Facebook:** Auto-post tournament announcements
- **Twitter:** Share match updates
- **Instagram:** Stories integration for highlights
- **Discord:** Rich embeds for tournament links

**Team Finder:**
- "/tournaments/<slug>/team-finder"
- Players looking for teams
- Post availability (game, role, rank)
- Message interested players
- Public teammate search

**Invitations:**
- Send tournament invites to friends
- Generate referral links (track registrations)
- Group registration discounts (if configured)

---

## 10. Mobile Design Patterns

### Internationalization & Bengali Support

**Language Switcher:**
- Location: Top-right corner of navbar (next to profile)
- Icon: Globe 🌐 with current language code (EN/বাং)
- Dropdown: English, বাংলা (Bengali)
- Persists selection in localStorage + user profile
- Reload page or use i18n library (Django i18n) for dynamic switching

**Bengali Font Verification:**
- Primary Bengali font: **Noto Sans Bengali** (Google Fonts)
- Verify font includes **Bengali numerals** (০১২৩৪৫৬৭৮৯)
- Test counters, progress bars, scores with Bengali numerals
- Fallback: Use Western numerals if Bengali numerals cause layout issues

**Localization Scope (Strings to Translate):**

Priority 1 (Must translate):
- Navigation menu items
- Button labels (Register, Submit, Cancel, etc.)
- Form field labels and placeholders
- Error messages and validation text
- Status badges (Live, Pending, Completed, etc.)
- Tournament state labels

Priority 2 (Should translate):
- Tournament descriptions (user-generated, optional)
- Help text and tooltips
- Empty state messages
- Success/confirmation messages
- Email notifications

Priority 3 (Nice to have):
- Admin panel strings
- Advanced settings descriptions
- Legal text (Terms, Privacy)

**Date & Time Localization:**
- Format: DD MMM, YYYY (e.g., "15 Dec, 2025" / "১৫ ডিসে, ২০২৫")
- Time: 12-hour with AM/PM (e.g., "10:00 AM" / "সকাল ১০:০০")
- Timezone: Always show "BST" (Bangladesh Standard Time)

**Currency Display:**
- Always prefix with ৳ symbol (Taka)
- Number format: Bangladeshi style with commas (৳50,000 or ৳৫০,০০০)
- DeltaCoin: "DC" suffix (500 DC / ৫০০ DC)

**Game Name Translation:**
- Keep English game names by default (VALORANT, CS2, etc.)
- Bengali descriptions optional (user-preference)

### Mobile-First Approach

**Principle:** Design for mobile, enhance for desktop.

**Key Patterns:**

**1. Bottom Sheet Navigation**
- Filters, actions slide up from bottom
- Easier thumb reach
- Example: Tournament filters (replaces sidebar)

**2. Sticky CTAs**
- Registration button always visible at bottom
- Fixed position, above navbar
- Example: "Register Now" floats on tournament detail page

**3. Collapsible Sections**
- Accordion pattern for long content
- Tournament details, rules, participants
- Default: First section expanded

**4. Swipe Gestures**
- Swipe between tabs (tournament detail tabs)
- Swipe to dismiss modals
- Pull-to-refresh for live updates

**5. Touch-Optimized Controls**
- Minimum tap target: 44x44px
- Spacing between tappable elements: 8px
- Large, thumb-friendly buttons

**6. Mobile Navigation**
- Hamburger menu for main nav
- Bottom navigation bar for primary actions:
  - Home | Tournaments | Matches | Profile
- Max 5 items in bottom nav

**7. Card-Based Layouts**
- Stack cards vertically on mobile
- Full-bleed images
- Swipeable carousels for multiple items

**8. Optimized Forms**
- One field per row
- Large input fields
- Native keyboards (number, email, phone)
- Auto-advance on completion (OTP inputs)

**9. Condensed Information**
- Hide less critical data on mobile
- "Show More" expand buttons
- Prioritize essential info above fold

**10. Offline Capabilities**
- Cache tournament details
- Queue actions (result submissions) when offline
- Sync when connection restored

**11. iOS Safe Areas (Notch Compatibility)**
- Sticky bottom CTAs respect safe area insets
- Use `env(safe-area-inset-bottom)` for padding
- Test on iPhone 14 Pro (Dynamic Island), iPhone SE (no notch)
- Example:
  ```css
  .sticky-cta {
      padding-bottom: calc(16px + env(safe-area-inset-bottom));
  }
  ```

**12. Payment Number Copy Buttons (Thumb-Optimized)**
- Large copy buttons (min 48x48px) next to payment numbers
- Success feedback: Button text changes to "Copied! ✓" for 2 seconds
- Haptic feedback (if supported)
- Numeric keyboard automatically opens when tapping payment field
- Example layout:
  ```
  bKash: 01712345678  [Copy 📋]
          └─ 44px tall button, right-aligned
  ```

**13. Keyboard Overlap Prevention**
- Auto-scroll active input field above keyboard
- Ensure "Next" button visible when keyboard open
- Use `scrollIntoView()` with `behavior: 'smooth'`
- "Next" button advances to next field automatically
- "Done" on last field submits form or closes keyboard
- Test on iOS Safari (keyboard toolbar) and Android Chrome

---

## 10. Staff & Moderator Tools

### 10.1 Admin Activity Log Panel

**Purpose:** Provide staff and moderators with comprehensive audit trail of all administrative actions for transparency, compliance, and troubleshooting.

**Access:** Staff members with "can_view_activity_log" permission

**Location:** 
- URL: `/admin/activity-log`
- Navigation: Admin panel sidebar → "Activity Log"
- Also: Dashboard widget showing recent 10 activities

**Panel Layout:**

```
┌────────────────────────────────────────────────────────┐
│ 🔒 AUDIT MODE ACTIVE - All actions are logged          │
└────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────┐
│ Activity Log                                    [Export CSV] │
├────────────────────────────────────────────────────────┤
│ Filters:                                                │
│ [User ▼] [Action Type ▼] [Date Range ▼] [Search...]   │
├────────────────────────────────────────────────────────┤
│ Table (Paginated - 50 per page)                        │
│ ┌──────────┬────────────┬────────┬──────────────────┐ │
│ │ Date/Time│ User       │ Action │ Details          │ │
│ ├──────────┼────────────┼────────┼──────────────────┤ │
│ │ 2m ago   │ Admin_John │ ✓ PAY  │ Approved payment │ │
│ │          │            │        │ for Team Alpha   │ │
│ ├──────────┼────────────┼────────┼──────────────────┤ │
│ │ 15m ago  │ Mod_Sara   │ ✗ PAY  │ Rejected payment │ │
│ │          │            │        │ (Invalid proof)  │ │
│ ├──────────┼────────────┼────────┼──────────────────┤ │
│ │ 1h ago   │ Admin_John │ 🏆 CERT│ Issued certif.   │ │
│ │          │            │        │ to 16 players    │ │
│ ├──────────┼────────────┼────────┼──────────────────┤ │
│ │ 2h ago   │ Mod_Ali    │ 🔨 BAN │ Banned user      │ │
│ │          │            │        │ PlayerX (reason) │ │
│ ├──────────┼────────────┼────────┼──────────────────┤ │
│ │ 3h ago   │ Admin_John │ ⚙️ SET │ Changed max      │ │
│ │          │            │        │ teams: 32→64     │ │
│ └──────────┴────────────┴────────┴──────────────────┘ │
├────────────────────────────────────────────────────────┤
│ Pagination: [< Prev] Page 1 of 45 [Next >]            │
└────────────────────────────────────────────────────────┘
```

**Audit Mode Banner:**

When staff performs sensitive actions (payment verification, user ban, etc.), banner appears:

```
┌────────────────────────────────────────────────────────┐
│ 🔒 AUDIT MODE ACTIVE - All actions are logged          │
│ Your activity is being recorded for compliance.        │
└────────────────────────────────────────────────────────┘
```

**Banner Styling:**
- Background: `#374151` (gray-700)
- Text color: White with 90% opacity
- Icon: 🔒 lock
- Position: Sticky at top of admin panel
- Height: 48px
- Animation: Slide down on first sensitive action (300ms ease-out)
- Dismiss: "Got it" button (hides banner for session)

**Logged Action Types:**

1. **Payment Verification** (`PAY`)
   - Action: Approved, Rejected, Refunded, Fee Waived
   - Details: Team name, tournament, amount, reason (if rejected)
   - Logged Fields: Previous state → New state

2. **Match Result Modification** (`MATCH`)
   - Action: Result edited, Result disputed, Score corrected
   - Details: Match ID, teams, old score → new score
   - Logged Fields: Who submitted original, edit reason

3. **User Moderation** (`USER`)
   - Action: User banned, User unbanned, Warning issued
   - Details: Username, reason, duration (if temporary ban)
   - Logged Fields: Moderator notes

4. **Certificate Management** (`CERT`)
   - Action: Certificate issued, Certificate revoked
   - Details: Tournament, recipient count, batch ID
   - Logged Fields: Template used

5. **Tournament Settings** (`SET`)
   - Action: Setting changed (max teams, check-in time, fee, etc.)
   - Details: Setting name, old value → new value
   - Logged Fields: Tournament slug

6. **Registration Override** (`REG`)
   - Action: Manual registration, Waitlist override, Slot reserved
   - Details: Team/player, tournament, reason
   - Logged Fields: Override type

**Activity Log Table Columns:**

1. **Date/Time:**
   - Format: "2m ago", "15m ago", "1h ago", "Nov 3, 10:30 AM" (for older)
   - Tooltip on hover shows exact timestamp
   - Sortable (default: newest first)

2. **User:**
   - Staff member who performed action
   - Link to user profile
   - Avatar thumbnail (24x24px)
   - Badge: "Admin", "Moderator", "Organizer"

3. **Action:**
   - Icon + category badge
   - Color-coded: Green (✓), Red (✗), Blue (ℹ️), Gold (🏆)
   - Tooltip shows full action name

4. **Details:**
   - Summary of action (1-2 lines)
   - "View Details" link opens modal with full context
   - Related object link (tournament, user, match)

5. **IP Address** (optional column, admin-only):
   - Shows IP address of staff member
   - Privacy: Only visible to super admins

**Filters:**

1. **User Filter:**
   - Dropdown: All staff members
   - Autocomplete search
   - Option: "My Actions Only"

2. **Action Type Filter:**
   - Multi-select dropdown
   - Options: Payment, Match, User, Certificate, Settings, Registration
   - Badge count: Shows # of actions per type

3. **Date Range Filter:**
   - Presets: Today, Last 7 days, Last 30 days, Custom range
   - Date picker for custom range

4. **Search Box:**
   - Search by: Team name, user, tournament, keyword
   - Real-time search (debounced)

**Export CSV:**
- Button: "Export CSV" (top-right)
- Exports filtered results (respects current filters)
- CSV Columns: Date, Time, User, Action, Details, IP (if admin)
- Filename: `activity-log-YYYY-MM-DD.csv`
- Analytics: `data-analytics-id="admin_activity_log_export"`

**Details Modal:**

Clicking "View Details" opens modal:

```
┌────────────────────────────────────────────────────────┐
│ Activity Details                              [X Close] │
├────────────────────────────────────────────────────────┤
│ Action: Payment Approved                                │
│ Performed by: Admin_John (admin@deltacrown.com)        │
│ Date: Nov 3, 2025 - 10:30:45 AM BST                    │
│ IP Address: 103.15.xxx.xxx (Dhaka, Bangladesh)         │
├────────────────────────────────────────────────────────┤
│ Action Details:                                         │
│  - Payment ID: PAY-12345                                │
│  - Team: Team Alpha                                     │
│  - Tournament: DeltaCrown Valorant Cup 2025            │
│  - Amount: ৳500                                         │
│  - Previous Status: Pending Verification                │
│  - New Status: Approved                                 │
│  - Verification Note: "Valid bKash transaction"         │
├────────────────────────────────────────────────────────┤
│ Related Links:                                          │
│  [View Payment] [View Tournament] [Contact Admin]      │
└────────────────────────────────────────────────────────┘
```

**Real-Time Updates:**

- **WebSocket Integration:** New activities appear without refresh
- **Live Indicator:** Green dot on Activity Log menu item when new activity
- **Toast Notification:** "New activity logged" (dismissible)
- **Auto-Refresh:** Table updates every 30 seconds (if WebSocket unavailable)

**Retention Policy:**

- **Activity logs retained for:** 2 years
- **After 2 years:** Archived (not deleted)
- **Super admin access:** Can view archived logs
- **Compliance:** GDPR-compliant (user can request their logged actions)

**Permissions:**

- **View Activity Log:** Staff, Moderators, Admins
- **Export CSV:** Admins only
- **View IP Addresses:** Super Admins only
- **Delete Logs:** No one (immutable audit trail)

**Dashboard Widget:**

Compact version shown on admin dashboard:

```
┌────────────────────────────────────────────────────────┐
│ Recent Activity (Last 24h)                    [View All]│
├────────────────────────────────────────────────────────┤
│ • 2m ago - Admin_John approved payment (Team Alpha)    │
│ • 15m ago - Mod_Sara rejected payment (Invalid proof)  │
│ • 1h ago - Admin_John issued 16 certificates           │
│ • 2h ago - Mod_Ali banned user PlayerX                 │
│ • 3h ago - Admin_John changed tournament settings      │
├────────────────────────────────────────────────────────┤
│ [View Full Activity Log →]                             │
└────────────────────────────────────────────────────────┘
```

**Analytics:**
- `data-analytics-id="admin_activity_log_view"`
- `data-analytics-id="admin_activity_log_filter"`
- `data-analytics-id="admin_activity_log_export"`
- `data-analytics-id="admin_activity_log_detail_view"`

---

## 11. Accessibility Guidelines

### WCAG 2.1 Level AA Compliance

**Color Contrast:**
- Text on background: Minimum 4.5:1 ratio
- Large text (18pt+): Minimum 3:1 ratio
- Interactive elements: 3:1 contrast with adjacent colors
- Test all color combinations with contrast checker

**Keyboard Navigation:**
- All interactive elements accessible via Tab
- Tab order follows logical reading order
- Focus indicators clearly visible (2px outline, brand color)
- Escape key closes modals/dropdowns
- Arrow keys navigate lists/menus
- Enter/Space activates buttons

**Screen Reader Support:**
- Semantic HTML (nav, main, article, aside)
- ARIA labels for icons and buttons
  ```html
  <button aria-label="Close modal">
    <svg><!-- X icon --></svg>
  </button>
  ```
- ARIA live regions for dynamic updates
  ```html
  <div aria-live="polite" aria-atomic="true">
    Match score updated: Team Alpha 13 - Team Beta 8
  </div>
  ```
- ARIA roles for custom widgets (tabs, modals)
- Alt text for all images (descriptive, not redundant)

**Focus Management:**

**Critical Rule: Focus Return Pattern**

When a modal, drawer, dropdown, or any overlay closes, keyboard focus **MUST** return to the element that triggered it. This ensures:
- Keyboard users don't lose their place
- Screen reader users maintain context
- Meets WCAG 2.1 Success Criterion 2.4.3 (Focus Order)

**Implementation:**

```javascript
// Store triggering element reference
let triggerElement = null;

// On modal open
function openModal(event) {
    triggerElement = event.target; // Store the button that opened modal
    modal.showModal();
    trapFocus(modal); // Focus first interactive element in modal
}

// On modal close
function closeModal() {
    modal.close();
    if (triggerElement) {
        triggerElement.focus(); // Return focus to trigger
        triggerElement = null;
    }
}

// Example with ESC key
modal.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal(); // Handles focus return automatically
    }
});
```

**HTML Pattern:**

```html
<!-- Trigger button -->
<button id="register-btn" 
        onclick="openModal(event)" 
        data-analytics-id="dc-btn-register">
    Register Now
</button>

<!-- Modal -->
<dialog id="registration-modal" 
        aria-labelledby="modal-title" 
        aria-describedby="modal-description">
    <!-- Modal content -->
    <button onclick="closeModal()" 
            data-analytics-id="dc-modal-close">
        Close
    </button>
</dialog>
```

**Focus Return Checklist:**

| Component | Trigger Example | Focus Return Target |
|-----------|----------------|---------------------|
| Modal | "Register Now" button | Same button |
| Dropdown | "Game Filter ▼" | Dropdown toggle button |
| Drawer | "☰ Menu" (mobile) | Menu icon button |
| Tooltip | Icon button (hover/focus) | Same icon button |
| Dialog | "Delete Tournament" | Delete button (or cancel if deleted) |

**Additional Focus Rules:**
- **Focus Trap:** Within modals, Tab cycles only through focusable modal elements (no escape to background)
- **First Focus:** When modal opens, focus moves to first interactive element (Close button or primary input)
- **Skip Links:** Provide "Skip to main content" link (visible on focus) for keyboard users
- **Logical Order:** Tab order follows visual reading order (left-to-right, top-to-bottom)

**Heading Hierarchy:**
- Single H1 per page
- Logical H2-H6 nesting (no skipping levels)
- Use headings for structure, not styling

**Form Accessibility:**
- Labels explicitly associated with inputs
  ```html
  <label for="tournament-name">Tournament Name</label>
  <input id="tournament-name" type="text" required aria-required="true">
  ```
- Error messages linked via aria-describedby
- Required fields indicated (*, aria-required)
- Fieldsets for grouped inputs (radio buttons)

**Mobile Form Optimization:**

Use the `inputmode` attribute to trigger the optimal mobile keyboard layout for each input type. This improves user experience on touch devices without changing the input's semantic type.

**`inputmode` Reference Table:**

| Field Type | `inputmode` Value | Keyboard Layout | Example |
|------------|-------------------|-----------------|---------|
| Phone Number | `numeric` | Numeric keypad (0-9, +, -, *, #) | `<input type="tel" inputmode="numeric">` |
| Email Address | `email` | Email keyboard (@, .com shortcuts) | `<input type="email" inputmode="email">` |
| URL/Website | `url` | URL keyboard (.com, /, :) | `<input type="url" inputmode="url">` |
| Search Field | `search` | Search keyboard (Go/Search button) | `<input type="search" inputmode="search">` |
| Decimal Number | `decimal` | Numeric with decimal point | `<input type="text" inputmode="decimal">` |
| Integer | `numeric` | Numeric only (no decimal) | `<input type="text" inputmode="numeric">` |
| Text (default) | `text` | Full QWERTY keyboard | `<input type="text" inputmode="text">` |

**Implementation Examples:**

```html
<!-- Tournament Registration Form -->

<!-- Player Phone (Bangladesh format: +880XXXXXXXXXX) -->
<label for="player-phone">Phone Number</label>
<input type="tel" 
       id="player-phone" 
       inputmode="numeric" 
       placeholder="+880XXXXXXXXXX"
       pattern="[+]?[0-9]{11,14}"
       data-analytics-id="dc-input-phone">

<!-- Player Email -->
<label for="player-email">Email Address</label>
<input type="email" 
       id="player-email" 
       inputmode="email" 
       placeholder="player@example.com"
       required
       data-analytics-id="dc-input-email">

<!-- In-Game ID (alphanumeric) -->
<label for="game-id">VALORANT In-Game ID</label>
<input type="text" 
       id="game-id" 
       inputmode="text" 
       placeholder="PlayerName#TAG"
       pattern="[A-Za-z0-9]+#[A-Za-z0-9]+"
       data-analytics-id="dc-input-game-id">

<!-- Team Fee (entry fee amount) -->
<label for="entry-fee">Entry Fee (৳)</label>
<input type="text" 
       id="entry-fee" 
       inputmode="numeric" 
       placeholder="500"
       pattern="[0-9]+"
       data-analytics-id="dc-input-fee">

<!-- Discord Server URL -->
<label for="discord-url">Discord Server</label>
<input type="url" 
       id="discord-url" 
       inputmode="url" 
       placeholder="https://discord.gg/xxxxx"
       data-analytics-id="dc-input-discord">

<!-- Tournament Search -->
<label for="tournament-search">Search Tournaments</label>
<input type="search" 
       id="tournament-search" 
       inputmode="search" 
       placeholder="VALORANT, CS2, PUBG..."
       data-analytics-id="dc-search-tournament">
```

**Mobile Keyboard Best Practices:**

1. **Always use `inputmode` for numeric inputs** (phone, age, rank, score, fee)
2. **Pair with `pattern` attribute** for client-side validation
3. **Use `type="tel"` with `inputmode="numeric"`** for phone numbers (enables numeric keyboard on all devices)
4. **Avoid `type="number"`** for non-arithmetic values (ID, phone) — it adds spinner buttons and breaks formatting
5. **Test on iOS Safari and Android Chrome** — keyboard layouts vary slightly

**Mobile Form UX Enhancements:**

```html
<!-- Auto-scroll active input above keyboard -->
<script>
document.querySelectorAll('input, textarea, select').forEach(input => {
    input.addEventListener('focus', () => {
        setTimeout(() => {
            input.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
        }, 300); // Wait for keyboard animation
    });
});
</script>

<!-- Disable zoom on input focus (iOS Safari fix) -->
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<!-- Note: Only use if inputs have font-size >= 16px to prevent auto-zoom -->
```

**Form Field Sizing for Mobile:**

- **Input Height:** Minimum 44px (iOS touch target guideline)
- **Font Size:** Minimum 16px (prevents auto-zoom on iOS)
- **Padding:** 12px vertical, 16px horizontal
- **Tap Target Spacing:** 8px between clickable elements

**Motion & Animation:**
- Respect prefers-reduced-motion
  ```css
  @media (prefers-reduced-motion: reduce) {
    * {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
  ```
- Pause/stop controls for auto-playing content
- No flashing content >3 times per second

**Content Accessibility:**
- Plain language, avoid jargon
- Instructions don't rely solely on color ("Click the blue button" → "Click the Register button")
- Sufficient line height (1.5 for body text)
- Text resizable up to 200% without loss of functionality

**Testing Checklist:**
- ✅ Test with screen reader (NVDA, JAWS, VoiceOver)
- ✅ Test keyboard-only navigation
- ✅ Test with browser zoom at 200%
- ✅ Test with color blindness simulators
- ✅ Automated testing (axe, Lighthouse)

---

## 12. Animation & Interaction Patterns

### Animation Principles

**Purpose of Animation:**
1. **Feedback:** Confirm user actions (button click, form submit)
2. **Attention:** Draw eye to important elements (live badge, new message)
3. **Relationship:** Show how elements connect (modal from button)
4. **Continuity:** Smooth transitions between states

**Duration Guidelines:**

```css
/* Instant feedback (hover, focus) */
--duration-instant: 100ms;

/* Quick interactions (dropdowns, tooltips) */
--duration-fast: 150ms;

/* Standard transitions (page elements) */
--duration-base: 250ms;

/* Complex animations (modals, slides) */
--duration-slow: 350ms;

/* Page transitions */
--duration-slower: 500ms;
```

**Easing Functions:**

```css
/* Natural deceleration (exiting) */
--ease-out: cubic-bezier(0, 0, 0.2, 1);

/* Natural acceleration (entering) */
--ease-in: cubic-bezier(0.4, 0, 1, 1);

/* Standard (most interactions) */
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);

/* Bouncy (playful interactions) */
--ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
```

### Specific Animations

**1. Button Click**
```css
.btn:active {
    transform: scale(0.98);
    transition: transform 100ms ease-out;
}
```

**2. Card Hover**
```css
.card {
    transition: all 250ms ease-out;
}
.card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}
```

**3. Modal Appear**
```css
.modal {
    animation: modal-appear 300ms ease-out;
}

@keyframes modal-appear {
    from {
        opacity: 0;
        transform: scale(0.95) translateY(-20px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}
```

**4. Toast Notification**
```css
.toast {
    animation: toast-slide-in 250ms ease-out;
}

@keyframes toast-slide-in {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}
```

**5. Live Badge Pulse**
```css
.badge-live {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.5;
    }
}
```

**6. Skeleton Loading**
```css
.skeleton {
    animation: skeleton-loading 1.5s ease-in-out infinite;
}

@keyframes skeleton-loading {
    0% {
        background-position: 200% 0;
    }
    100% {
        background-position: -200% 0;
    }
}
```

**7. Page Transition (HTMX)**
```css
.htmx-swapping {
    opacity: 0;
    transition: opacity 200ms ease-out;
}

.htmx-settling {
    opacity: 1;
    transition: opacity 200ms ease-in;
}
```

**8. Success Checkmark**
```css
.checkmark {
    animation: checkmark-pop 400ms cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

@keyframes checkmark-pop {
    0% {
        transform: scale(0);
        opacity: 0;
    }
    50% {
        transform: scale(1.1);
    }
    100% {
        transform: scale(1);
        opacity: 1;
    }
}
```

---

### Real-Time Flow Animations

**Purpose:** Smooth, non-disruptive transitions for live data updates (scores, brackets, notifications).

**9. Score Update (Live Match)**
```css

---

**Navigation:**
- [← Previous: PART_4.4 - Registration & Payment Flow](PART_4.4_REGISTRATION_PAYMENT_FLOW.md)
- [→ Next: PART_4.6 - Animation Patterns & Conclusion](PART_4.6_ANIMATION_PATTERNS_CONCLUSION.md)
- [↑ Back to Index](INDEX_MASTER_NAVIGATION.md)
