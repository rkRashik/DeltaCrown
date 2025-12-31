# Profile Backend Contract
**Date:** December 31, 2025  
**Owner:** Backend Architect  
**Type:** Frontend-Backend Data Contract  
**Purpose:** Define minimal context variables needed to render user_profile.html

---

## A. PROFILE PAGE SECTIONS & REQUIRED CONTEXT

### SECTION 1: HERO / HEADER (Identity & Status)

**Template Location:** Top of page, `.hero-section`

**Context Keys Required:**

**`profile` (UserProfile object):**
- `profile.user.username` (str) - Gamertag/display name
- `profile.bio` (str, max 500 chars) - User biography
- `profile.avatar.url` (str) - Profile photo URL
- `profile.cover_photo.url` (str) - Hero background banner URL
- `profile.nationality` (str) - Country name
- `profile.location` (str) - City/region (privacy-filtered)
- `profile.level` (int) - User level (1-100)
- `profile.is_verified_pro` (bool) - Shows verified badge
- `profile.reputation_score` (int, 0-100) - Reputation display
- `profile.joined_at` (datetime) - Account creation date

**`social_links` (QuerySet[SocialLink]):**
- List of `{platform: str, url: str, icon: str}` for Discord/Twitter/YouTube
- Used to render social icon row in hero

**`follower_stats` (dict):**
- `followers_count` (int) - Total followers
- `following_count` (int) - Total following
- `is_following` (bool) - True if current user follows profile owner (for Follow button state)

**`active_teams` (QuerySet[TeamMembership]):**
- `teams.count()` - "Enrolled in X teams" stat
- Used in hero stats HUD

**`is_owner` (bool):**
- True if `request.user == profile.user` (shows Edit buttons, hides Follow button)

**`view_mode` (str):**
- One of: `'owner'`, `'friend'`, `'public'`
- Determines visibility of personal info (real name, location)

**Privacy Rules:**
- **Public:** Shows gamertag, bio, nationality, avatar, cover photo, verified status
- **Friend:** + Shows location, real name (if set)
- **Owner:** + Shows "Edit Profile" button, "Change Cover" button, visibility toggles

**Source Models:**
- ✅ **Existing:** `UserProfile`, `SocialLink`, `User`
- ✅ **Existing:** Follower relationship (via Follow system)
- ✅ **Existing:** `TeamMembership`

**Query (High-Level):**
```python
profile = UserProfile.objects.select_related('user').get(user__username=username)
social_links = profile.social_links.all()
follower_stats = {
    'followers_count': profile.followers.count(),
    'following_count': profile.following.count(),
    'is_following': request.user in profile.followers.all() if request.user.is_authenticated else False
}
active_teams = TeamMembership.objects.filter(user=profile.user, status='ACTIVE')
```

---

### SECTION 2: NAVIGATION STRIP (Sticky Tabs)

**Template Location:** Below hero, `.z-tab-nav`

**Context Keys Required:**

**`tab_badges` (dict):**
- `posts_count` (int) - New posts count (shows badge notification)
- `bounties_count` (int) - Active bounties count
- `highlights_count` (int) - Total clips count

**`wallet_visible` (bool):**
- True only if `is_owner=True` (hides Wallet tab for non-owners)

**Privacy Rules:**
- **Public:** Sees all tabs except Wallet
- **Owner:** Sees all tabs including Wallet (highlighted in gold)

**Source Models:**
- ❌ **Missing:** `Post` model (community app doesn't exist)
- ❌ **New:** `Bounty` model
- ❌ **New:** `HighlightClip` model

---

### SECTION 3: LEFT SIDEBAR (Identity & Specs)

**Template Location:** Left column (desktop) / top stack (mobile), `.left-sidebar`

#### 3.1 Personal Info Module

**Context Keys Required:**

**`profile.real_name` (str, nullable):**
- Privacy-filtered: Only visible if `view_mode in ['owner', 'friend']`

**`profile.date_joined` (datetime):**
- Displayed as "Member since Jan 2025"

**Privacy Rules:**
- **Public:** Shows nationality, join date only
- **Friend:** + Shows real name, location
- **Owner:** + Shows visibility toggle icon

**Source Models:**
- ✅ **Existing:** `UserProfile`

#### 3.2 Game Passports (Linked IDs)

**Context Keys Required:**

**`game_passports` (QuerySet[GamePassport]):**
- `game_name` (str) - "Valorant", "PUBG", "CS2"
- `in_game_id` (str) - Player ID (e.g., "Viper#NA1")
- `rank_tier` (str) - "Immortal 3", "Diamond II"
- `is_main` (bool) - Highlights with cyan border (primary game)

**Privacy Rules:**
- **Public:** Shows all linked game IDs and ranks
- **Owner:** + Shows "+ Link New ID" button

**Source Models:**
- ✅ **Existing:** `GamePassport` (from games app)

**Query:**
```python
game_passports = GamePassport.objects.filter(user=profile.user).select_related('game')
```

#### 3.3 Gear Setup (Loadout)

**Context Keys Required:**

**`user_hardware` (QuerySet[UserHardware]):**
- `category` (str) - "MOUSE", "KEYBOARD", "HEADSET", "MONITOR"
- `product.name` (str) - "Logitech G Pro X Superlight"
- `product.brand` (str) - "Logitech"
- `custom_settings.dpi` (int) - 800
- `product.affiliate_url` (str, nullable) - Link to store

**Privacy Rules:**
- **Public:** Shows hardware list with affiliate links (click → DeltaCrown Store)
- **Owner:** + Shows "Edit" icon to modify gear

**Source Models:**
- ❌ **New:** `HardwareProduct`, `UserHardware`

**Query:**
```python
user_hardware = UserHardware.objects.filter(user=profile.user).select_related('product').order_by('category')
```

---

### SECTION 4: CENTER COMMAND (Dynamic Tabs)

**Template Location:** Center column, `.tab-content` divs

#### 4.1 TAB: Overview (Default)

**Context Keys Required:**

**`pinned_clip` (HighlightClip object or None):**
- `video_id` (str) - YouTube/Twitch video ID
- `platform` (str) - "youtube", "twitch", "medal"
- `embed_url` (str) - Pre-constructed iframe URL
- `title` (str, max 100 chars) - Clip title
- `thumbnail_url` (str) - Video thumbnail for preview

**`active_bounty` (Bounty object or None):**
- `title` (str) - "1v1 Gridshot Challenge"
- `game` (str) - "Valorant"
- `stake_amount` (int) - 5000 (DeltaCoins)
- `requirements` (str) - "First to 100k score"
- `expires_at` (datetime) - Expiry countdown
- `status` (str) - "OPEN", "IN_PROGRESS", "COMPLETED"

**`endorsement_summary` (dict):**
- `total_count` (int) - Total endorsements received
- `skills` (list of dicts) - `[{'name': 'Aim', 'count': 89, 'percentage': 35}, ...]`
- `top_skill` (str) - "Aim" (most endorsed skill)

**Privacy Rules:**
- **Public:** Shows pinned clip (if set), endorsements (if profile not private), active bounty (if OPEN)
- **Owner:** + Shows "Edit" buttons, "Pin different clip" option

**Source Models:**
- ❌ **New:** `HighlightClip` (pinned via UserProfile FK)
- ❌ **New:** `Bounty`
- ❌ **New:** `SkillEndorsement`

**Query:**
```python
pinned_clip = profile.pinned_clip  # UserProfile.pinned_clip FK
active_bounty = Bounty.objects.filter(creator=profile.user, status='OPEN').first()
endorsement_summary = SkillEndorsement.objects.filter(receiver=profile.user).values('skill_name').annotate(count=Count('id')).order_by('-count')
```

#### 4.2 TAB: Wallet (Economy Dashboard)

**Context Keys Required:**

**`wallet` (DeltaCrownWallet object or dict):**
- `cached_balance` (int) - Current balance (in DeltaCoins)
- `pending_balance` (int) - Locked funds (withdrawals, bounties)
- `lifetime_earnings` (int) - All-time earnings
- `available_balance` (int) - Computed: `cached_balance - pending_balance`

**`wallet_transactions` (QuerySet[DeltaCrownTransaction]):**
- Last 10 transactions for ledger display
- `amount` (int) - Transaction amount
- `reason` (str) - "TOURNAMENT_WIN", "BOUNTY_WIN", "REFUND"
- `created_at` (datetime) - Transaction timestamp
- `metadata` (dict) - Additional context (tournament name, bounty ID)

**`bdt_conversion_rate` (float):**
- DeltaCoin → BDT exchange rate (for "≈ 50,420 BDT" display)

**Privacy Rules:**
- **Owner ONLY:** Full wallet access (balance, transactions, deposit/withdraw buttons)
- **Public:** Tab hidden entirely OR shows only `lifetime_earnings` (no current balance)

**Source Models:**
- ✅ **Existing:** `DeltaCrownWallet`, `DeltaCrownTransaction`

**Query:**
```python
if is_owner:
    wallet = profile.user.wallet
    wallet_transactions = wallet.transactions.order_by('-created_at')[:10]
else:
    wallet = {'lifetime_earnings': profile.user.wallet.lifetime_earnings}  # Limited public data
    wallet_transactions = None
```

#### 4.3 TAB: Career (Timeline)

**Context Keys Required:**

**`career_history` (QuerySet[TeamMembership]):**
- `team.name` (str) - Team name
- `team.logo.url` (str) - Team logo
- `role` (str) - "IGL", "Entry Fragger", "Support"
- `joined_at` (datetime) - Start date
- `left_at` (datetime, nullable) - End date (null if current)
- `is_active` (bool) - True for current teams

**Privacy Rules:**
- **Public:** Shows all past and current teams
- **Owner:** + Shows "Edit Role" option

**Source Models:**
- ✅ **Existing:** `TeamMembership`, `Team`

**Query:**
```python
career_history = TeamMembership.objects.filter(user=profile.user).select_related('team').order_by('-joined_at')
```

#### 4.4 TAB: Stats (Combat Data)

**Context Keys Required:**

**`game_stats` (dict or QuerySet):**
- `kd_ratio` (float) - Kill/Death ratio
- `win_rate` (float) - Win percentage
- `headshot_percentage` (float) - Headshot %
- `matches_played` (int) - Total matches
- `mvp_count` (int) - MVP awards

**`advanced_stats_locked` (bool):**
- True if user doesn't have Premium (shows lock icon)
- False if Premium user (shows heatmaps, analytics)

**Privacy Rules:**
- **Public:** Shows basic stats (K/D, Win Rate)
- **Owner:** + Shows advanced stats if Premium

**Source Models:**
- ✅ **Existing:** Game-specific stats models (if they exist)
- ❌ **Assumed:** Stats aggregated from match results

#### 4.5 TAB: Inventory (Vault)

**Context Keys Required:**

**`unlocked_cosmetics` (QuerySet[UnlockedCosmetic]):**
- `cosmetic_type` (str) - "FRAME", "BANNER", "BADGE"
- `cosmetic.name` (str) - "Dragon Fire Frame"
- `cosmetic.rarity` (str) - "COMMON", "RARE", "LEGENDARY"
- `cosmetic.asset_url` (str) - Image/asset URL
- `is_equipped` (bool) - True if currently equipped

**`equipped_frame` (ProfileFrame object or None):**
- Currently equipped avatar frame

**`equipped_banner` (ProfileBanner object or None):**
- Currently equipped profile banner/theme

**Privacy Rules:**
- **Public:** Shows equipped cosmetics only (not full unlocked collection)
- **Owner:** + Shows full inventory, equip/unequip buttons

**Source Models:**
- ❌ **New:** `ProfileFrame`, `ProfileBanner`, `UnlockedCosmetic`

**Query:**
```python
if is_owner:
    unlocked_cosmetics = UnlockedCosmetic.objects.filter(user=profile.user).select_related('cosmetic')
else:
    unlocked_cosmetics = None  # Public sees only equipped items
equipped_frame = profile.equipped_frame
equipped_banner = profile.equipped_banner
```

#### 4.6 TAB: Highlights (Gallery)

**Context Keys Required:**

**`highlight_clips` (QuerySet[HighlightClip]):**
- `video_id` (str) - YouTube/Twitch video ID
- `platform` (str) - "youtube", "twitch", "medal"
- `title` (str, max 100 chars) - Clip title
- `description` (str, max 500 chars) - Clip description
- `thumbnail_url` (str) - Video thumbnail
- `embed_url` (str) - Pre-constructed iframe URL
- `position` (int) - Ordering position
- `added_at` (datetime) - Upload timestamp

**`can_add_more_clips` (bool):**
- True if `highlight_clips.count() < 20` (max limit)

**Privacy Rules:**
- **Public:** Shows all clips (grid view)
- **Owner:** + Shows "Add Clip" button, "Reorder" controls, "Pin" option

**Source Models:**
- ❌ **New:** `HighlightClip`

**Query:**
```python
highlight_clips = HighlightClip.objects.filter(user=profile.user).order_by('position')[:20]
can_add_more_clips = highlight_clips.count() < 20
```

#### 4.7 TAB: Bounties

**Context Keys Required:**

**`user_bounties` (dict):**
- `created` (QuerySet[Bounty]) - Bounties created by user
- `accepted` (QuerySet[BountyAcceptance]) - Bounties user accepted
- `completed` (QuerySet[Bounty]) - Completed bounty history

**`bounty_stats` (dict):**
- `total_created` (int) - Total bounties created
- `total_won` (int) - Bounties won
- `win_rate` (float) - Win percentage
- `total_earnings` (int) - DeltaCoins earned from bounties

**Privacy Rules:**
- **Public:** Shows completed bounties only (history)
- **Owner:** + Shows active/pending bounties, creation form

**Source Models:**
- ❌ **New:** `Bounty`, `BountyAcceptance`

**Query:**
```python
user_bounties = {
    'created': Bounty.objects.filter(creator=profile.user).select_related('game', 'acceptor'),
    'accepted': BountyAcceptance.objects.filter(acceptor=profile.user).select_related('bounty'),
    'completed': Bounty.objects.filter(Q(creator=profile.user) | Q(acceptor=profile.user), status='COMPLETED')
}
```

#### 4.8 TAB: Endorsements

**Context Keys Required:**

**`endorsement_stats` (dict):**
- `total_endorsements` (int) - Total received
- `skills` (list) - `[{'name': 'Aim', 'count': 89, 'percentage': 35}, ...]`
- `top_skill` (str) - "Aim"
- `unique_endorsers` (int) - Count of distinct teammates who endorsed
- `unique_matches` (int) - Count of distinct matches with endorsements

**`recent_endorsement_matches` (QuerySet):**
- Last 5 matches where user was endorsed
- `match.tournament_name` (str)
- `match.completed_at` (datetime)
- `endorsement_count` (int) - How many endorsements from that match

**Privacy Rules:**
- **Public:** Shows aggregated stats (skill breakdown, total count)
- **Owner:** + Shows endorser details (admin view only, for collusion detection)

**Source Models:**
- ❌ **New:** `SkillEndorsement`, `EndorsementOpportunity`
- ✅ **Existing:** `Match` (via match_id FK)

**Query:**
```python
endorsement_stats = SkillEndorsement.objects.filter(receiver=profile.user).aggregate(
    total=Count('id'),
    unique_endorsers=Count('endorser', distinct=True),
    unique_matches=Count('match', distinct=True)
)
skills = SkillEndorsement.objects.filter(receiver=profile.user).values('skill_name').annotate(count=Count('id')).order_by('-count')
```

#### 4.9 TAB: Loadout

**Context Keys Required:**

**`user_hardware` (dict):**
- Same as Left Sidebar (see Section 3.3)

**`game_configs` (QuerySet[GameConfig]):**
- `game.name` (str) - "Valorant", "CS2"
- `settings_json` (dict) - `{'sensitivity': 0.45, 'dpi': 800, 'crosshair': 'small_dot'}`
- `last_updated` (datetime) - Last edit timestamp

**`hardware_catalog` (QuerySet[HardwareProduct]):**
- Available products for selection (cached, only if owner viewing)
- `name` (str), `brand` (str), `category` (str), `specs_json` (dict)

**Privacy Rules:**
- **Public:** Shows hardware + game configs (if profile not private)
- **Owner:** + Shows edit forms, hardware catalog selection

**Source Models:**
- ❌ **New:** `HardwareProduct`, `UserHardware`, `GameConfig`

**Query:**
```python
user_hardware = UserHardware.objects.filter(user=profile.user).select_related('product')
game_configs = GameConfig.objects.filter(user=profile.user).select_related('game')
hardware_catalog = HardwareProduct.objects.all() if is_owner else None  # Cached for 24h
```

#### 4.10 TAB: Posts (COMMUNITY FEATURE)

**Status:** ❌ **apps/community DOES NOT EXIST**

**Proposed Behavior:**
- **Option A (Recommended):** Hide Posts tab entirely from navigation until community app implemented
- **Option B:** Show "Coming Soon" placeholder card in tab content
- **Option C:** Create minimal `Post` model in `apps/user_profile/` as temporary solution (not recommended, violates separation of concerns)

**If Posts Tab Shown:**

**Context Keys Required:**

**`user_posts` (QuerySet[Post] or None):**
- `content` (str) - Post text
- `media_url` (str, nullable) - Attached image/video
- `created_at` (datetime)
- `likes_count` (int)
- `comments_count` (int)

**Privacy Rules:**
- **Public:** Shows public posts only
- **Friend:** + Shows friend-only posts
- **Owner:** + Shows all posts, draft posts

**Recommendation:** **Defer Posts tab to Phase 3** (after Bounty/Endorsements/Loadout/Highlights implemented)

---

### SECTION 5: RIGHT SIDEBAR (Status & Assets)

**Template Location:** Right column, `.right-sidebar`

#### 5.1 Live Tournament Widget

**Context Keys Required:**

**`live_match` (dict or None):**
- `tournament_name` (str) - "Season 2 Playoffs"
- `game` (str) - "Valorant"
- `opponent_name` (str) - "Team Phoenix" or "@username"
- `match_url` (str) - Link to match detail page
- `started_at` (datetime) - Match start time (for "Started 15 min ago" display)
- `round` (str) - "Semifinals", "Best of 3"

**`stream_url` (str or None):**
- If user streaming, Twitch/YouTube embed URL
- Only shown if user has `stream_config.is_live_override=True` OR has live tournament match

**Privacy Rules:**
- **Public:** Shows live match banner if match is public (`Match.is_public=True`)
- **Private Profiles:** Hides live status from visitors (only owner sees)

**Source Models:**
- ✅ **Existing:** `Match` (from tournament_ops)
- ❌ **New:** Stream config fields (extend `UserProfile` or `SocialLink`)

**Query:**
```python
live_match = Match.objects.filter(
    Q(participant1=profile.user) | Q(participant2=profile.user) | Q(team_a__members=profile.user) | Q(team_b__members=profile.user),
    state='LIVE',
    is_public=True
).select_related('tournament', 'team_a', 'team_b').first()
```

#### 5.2 Affiliations (Current Teams)

**Context Keys Required:**

**`active_teams` (QuerySet[TeamMembership]):**
- Same as Hero section (see Section 1)
- `team.name` (str), `team.logo.url` (str), `role` (str)

**Privacy Rules:**
- **Public:** Shows all active teams

**Source Models:**
- ✅ **Existing:** `TeamMembership`, `Team`

#### 5.3 Trophy Cabinet

**Context Keys Required:**

**`tournament_trophies` (QuerySet or list):**
- `tournament_name` (str) - "Season 1 Winter Cup"
- `placement` (str) - "1st Place", "Runner-Up"
- `medal_icon` (str) - Trophy image URL
- `date_won` (datetime)

**Privacy Rules:**
- **Public:** Shows all earned trophies

**Source Models:**
- ✅ **Existing:** Tournament results (if tracked)
- ❌ **Assumed:** Aggregated from match/tournament wins

---

## B. CONTEXT VARIABLE SUMMARY (All Sections)

### Profile Identity & Meta
```python
{
    'profile': UserProfile,              # ✅ Existing model
    'is_owner': bool,                    # Computed
    'view_mode': str,                    # Computed ('owner'/'friend'/'public')
    'social_links': QuerySet[SocialLink], # ✅ Existing model
    'follower_stats': {                  # Computed from Follow system
        'followers_count': int,
        'following_count': int,
        'is_following': bool,
    },
}
```

### Teams & Career
```python
{
    'active_teams': QuerySet[TeamMembership],      # ✅ Existing
    'career_history': QuerySet[TeamMembership],    # ✅ Existing
}
```

### Games & Loadout
```python
{
    'game_passports': QuerySet[GamePassport],      # ✅ Existing
    'user_hardware': QuerySet[UserHardware],       # ❌ NEW MODEL
    'game_configs': QuerySet[GameConfig],          # ❌ NEW MODEL
    'hardware_catalog': QuerySet[HardwareProduct], # ❌ NEW MODEL (cached)
}
```

### Bounties
```python
{
    'active_bounty': Bounty or None,               # ❌ NEW MODEL
    'user_bounties': {                             # ❌ NEW MODEL
        'created': QuerySet[Bounty],
        'accepted': QuerySet[BountyAcceptance],
        'completed': QuerySet[Bounty],
    },
    'bounty_stats': {                              # Computed
        'total_created': int,
        'total_won': int,
        'win_rate': float,
        'total_earnings': int,
    },
}
```

### Endorsements
```python
{
    'endorsement_summary': {                       # ❌ NEW MODEL (aggregated)
        'total_count': int,
        'skills': list[dict],  # [{'name': 'Aim', 'count': 89, 'percentage': 35}]
        'top_skill': str,
        'unique_endorsers': int,
        'unique_matches': int,
    },
    'recent_endorsement_matches': QuerySet,        # Computed
}
```

### Highlights
```python
{
    'pinned_clip': HighlightClip or None,          # ❌ NEW MODEL (via UserProfile FK)
    'highlight_clips': QuerySet[HighlightClip],    # ❌ NEW MODEL
    'can_add_more_clips': bool,                    # Computed
}
```

### Showcase / Inventory
```python
{
    'unlocked_cosmetics': QuerySet[UnlockedCosmetic] or None,  # ❌ NEW MODEL
    'equipped_frame': ProfileFrame or None,                    # ❌ NEW MODEL (via UserProfile FK)
    'equipped_banner': ProfileBanner or None,                  # ❌ NEW MODEL (via UserProfile FK)
}
```

### Wallet / Economy
```python
{
    'wallet': DeltaCrownWallet or dict,            # ✅ Existing (owner-only full access)
    'wallet_transactions': QuerySet[DeltaCrownTransaction], # ✅ Existing (owner-only)
    'bdt_conversion_rate': float,                  # Computed or cached
}
```

### Live Status & Streaming
```python
{
    'live_match': dict or None,                    # ✅ Existing Match model (computed)
    'stream_url': str or None,                     # ❌ NEW (stream config fields)
}
```

### Stats & Achievements
```python
{
    'game_stats': dict,                            # ✅ Assumed (aggregated from matches)
    'tournament_trophies': QuerySet or list,       # ✅ Assumed (tournament results)
    'advanced_stats_locked': bool,                 # Computed (Premium check)
}
```

### Tab Badges & Notifications
```python
{
    'tab_badges': {                                # Computed
        'posts_count': int,       # ❌ Requires community app
        'bounties_count': int,    # ❌ NEW
        'highlights_count': int,  # ❌ NEW
    },
    'wallet_visible': bool,                        # Computed (is_owner check)
}
```

---

## C. PRIVACY RULES MATRIX

| Section | Public View | Friend View | Owner View |
|---------|------------|-------------|------------|
| **Hero Identity** | Gamertag, bio, nationality, avatar, verified badge | + Real name, location | + Edit buttons, visibility toggles |
| **Follower Stats** | Followers/following counts, Follow button | Same | "Edit Profile" instead of Follow |
| **Game Passports** | All linked IDs + ranks | Same | + "Link New ID" button |
| **Gear Setup** | Hardware list + affiliate links | Same | + Edit icon |
| **Pinned Clip** | Visible (if set) | Same | + "Pin different clip" option |
| **Bounties** | Completed history only | Same | + Active/pending bounties, creation form |
| **Endorsements** | Aggregated stats (skill breakdown) | Same | + Endorser details (admin only) |
| **Loadout** | Hardware + game configs | Same | + Edit forms, hardware catalog |
| **Highlights** | All clips (grid view) | Same | + Add/reorder/pin controls |
| **Showcase** | Equipped frame/banner only | Same | + Full inventory, equip/unequip |
| **Wallet** | **HIDDEN** or lifetime_earnings only | Same | **FULL ACCESS** (balance, transactions, deposit/withdraw) |
| **Career** | All teams (past + current) | Same | + "Edit Role" option |
| **Stats** | Basic stats (K/D, Win Rate) | Same | + Advanced stats (if Premium) |
| **Live Match** | Visible (if match is public) | Same | Visible (always, even if match private) |
| **Posts** | Public posts only | + Friend-only posts | + All posts, drafts |

---

## D. MISSING COMMUNITY APP - PROPOSED BEHAVIOR

**Status:** ❌ **apps/community/ DOES NOT EXIST**

**Impact:**
- Posts tab cannot be implemented
- User-generated content feed unavailable
- Profile "activity stream" incomplete

**Proposed Solution (3 Options):**

### Option 1: Hide Posts Tab (Recommended)
```python
# In template
{% if posts_tab_enabled %}  <!-- Set to False in view context -->
    <button class="z-tab-btn" onclick="switchTab('posts')">Posts</button>
{% endif %}
```
- **Pros:** Clean, no broken functionality shown
- **Cons:** Users don't know feature is planned
- **Implementation:** Set `posts_tab_enabled=False` in view context

### Option 2: Show "Coming Soon" Placeholder
```python
# In view
context['posts_tab_enabled'] = True
context['user_posts'] = None  # Signals "coming soon" state

# In template
{% if user_posts is None %}
    <div class="z-card text-center py-12">
        <i class="fa-solid fa-rocket text-6xl text-z-purple mb-4"></i>
        <h3 class="text-xl font-bold text-white mb-2">Posts Coming Soon</h3>
        <p class="text-gray-400">We're building a community feed. Stay tuned!</p>
    </div>
{% endif %}
```
- **Pros:** Communicates future feature, maintains tab structure
- **Cons:** Slight UX disappointment (tab exists but empty)
- **Implementation:** Render tab, show placeholder card

### Option 3: Minimal Post Model in user_profile (NOT Recommended)
```python
# apps/user_profile/models/post.py (temporary)
class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    # Minimal fields only, migrate to apps/community later
```
- **Pros:** Posts tab functional immediately
- **Cons:** Violates separation of concerns, tech debt, migration headache
- **Implementation:** NOT RECOMMENDED (defer to Phase 3)

**Final Recommendation:** **Option 1 (Hide Posts Tab)** until `apps/community/` implemented in Phase 3

---

## E. QUERY OPTIMIZATION NOTES

### Critical N+1 Prevention
```python
# ✅ Correct: Eager load related objects
profile = UserProfile.objects.select_related('user', 'pinned_clip', 'equipped_frame', 'equipped_banner').get(user__username=username)
social_links = profile.social_links.all()
game_passports = GamePassport.objects.filter(user=profile.user).select_related('game')
user_hardware = UserHardware.objects.filter(user=profile.user).select_related('product')
highlight_clips = HighlightClip.objects.filter(user=profile.user).order_by('position')[:20]

# ❌ Wrong: Lazy loading causes N+1 queries
for clip in profile.highlight_clips.all():  # N queries for thumbnails
    print(clip.thumbnail_url)
```

### Caching Strategy
```python
# Cache expensive aggregations (1-hour TTL)
cache_key = f'endorsement_stats:{profile.user.id}'
endorsement_summary = cache.get(cache_key)
if not endorsement_summary:
    endorsement_summary = aggregate_endorsements(profile.user)
    cache.set(cache_key, endorsement_summary, 3600)

# Cache live match status (1-minute TTL)
cache_key = f'live_match:{profile.user.id}'
live_match = cache.get(cache_key)
if not live_match:
    live_match = get_live_match(profile.user)
    cache.set(cache_key, live_match, 60)
```

### Database Indexes Required
```python
# Bounty queries
- Index on (creator_id, status)
- Index on (acceptor_id, status)

# Endorsement queries
- Index on (receiver_id)
- Composite index on (match_id, endorser)

# Highlight queries
- Composite index on (user_id, position)

# Match queries
- Index on (state) for live match detection
```

---

## F. IMPLEMENTATION PRIORITY

### P0 - Render Basic Profile (Week 1)
- ✅ Hero section (existing UserProfile data)
- ✅ Navigation strip (without Posts tab)
- ✅ Left sidebar (existing GamePassport, SocialLink)
- ✅ Career tab (existing TeamMembership)
- ✅ Wallet tab (existing DeltaCrownWallet, owner-only)
- ✅ Right sidebar (existing Team affiliations)

**Blockers:** None (all models exist)

### P1 - New Feature Tabs (Week 2-4)
- ❌ Overview tab → Requires Bounty, SkillEndorsement, HighlightClip models
- ❌ Bounties tab → Requires Bounty, BountyAcceptance models
- ❌ Endorsements tab → Requires SkillEndorsement model
- ❌ Highlights tab → Requires HighlightClip model
- ❌ Loadout tab → Requires HardwareProduct, UserHardware, GameConfig models
- ❌ Showcase/Inventory tab → Requires ProfileFrame, ProfileBanner, UnlockedCosmetic models

**Blockers:** All new models must be created first

### P2 - Advanced Features (Week 5+)
- ❌ Live match widget → Requires stream config fields, Match.is_public
- ❌ Stats tab → Requires stats aggregation (if not already tracked)
- ❌ Posts tab → Requires apps/community/ (defer to Phase 3)

---

**END OF BACKEND CONTRACT**

**Status:** ✅ Ready for Backend Implementation  
**Next Steps:**
1. Create missing models (Bounty, Endorsement, Loadout, Highlight, Showcase)
2. Implement view context builders for each tab
3. Add privacy filters to queries (view_mode-based)
4. Set up caching for expensive aggregations
5. Hide Posts tab until community app exists
