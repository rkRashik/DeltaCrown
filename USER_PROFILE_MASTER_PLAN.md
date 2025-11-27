# USER PROFILE MASTER PLAN
## DeltaCrown Esports Platform - 2025 Modern Standard

**Document Version:** 1.0  
**Date:** November 26, 2025  
**Status:** Phase 1 - Architecture & Planning  
**Lead Architect:** Senior Product Team

---

## 🎯 EXECUTIVE SUMMARY

This document defines the complete frontend architecture for the DeltaCrown User Profile system. We are building a **Data-Dense Esports Command Center** that serves two distinct user experiences while maintaining visual excellence and performance.

**Core Philosophy:**
- **For Owners:** A dashboard for management, privacy control, and economy tracking
- **For Spectators:** A portfolio showcasing achievements, trustworthiness, and competitive stats
- **Design Language:** Glassmorphic Cyberpunk 2025 - where form meets function

---

## 📋 SECTION 1: USER EXPERIENCE (UX) STRATEGY

### 1.1 The Two Core View Modes

#### **MODE A: OWNER VIEW (Logged-In User Viewing Their Own Profile)**

**Primary User Goal:** "I want to manage my esports identity and track my assets."

**Mental Model:** This is my **Command Center** - a control panel where I:
- Monitor my reputation and trust score
- Manage game accounts across 9+ titles
- Control what others see (Privacy Matrix)
- Track my DeltaCoin wallet and transaction history
- Upload KYC documents for tournament eligibility
- Pin my best achievements to showcase

**Key UI Elements (Owner-Specific):**
1. **Floating Action Bar (Hero Section)**
   - `⚙ Settings` - Opens unified settings modal
   - `↗ Share` - Web Share API or copy link
   - `✏ Edit Profile` - Quick edit mode (inline)

2. **Enhanced Controls Throughout:**
   - **Privacy Toggles:** Eye icons next to sensitive fields (Phone, Wallet, Real Name)
   - **Game ID Management:** `[+ Add Game]` button in Game Passport section
   - **Wallet Actions:** `[+ Deposit]` `[↗ Withdraw]` `[📊 History]`
   - **KYC Banner:** If not verified, show prominent "Verify Identity" CTA

3. **Owner-Only Sections:**
   - **Transaction Timeline:** Last 30 days of DeltaCoin activity
   - **Privacy Matrix Dashboard:** Visual grid showing what's public/private
   - **Draft Achievements:** Unpinned badges in a separate "Vault" view

**Information Hierarchy (Owner):**
```
Critical → Actionable → Contextual → Vanity
    ↓           ↓            ↓          ↓
  Wallet    Settings    Team Roster  Trophies
```

---

#### **MODE B: SPECTATOR VIEW (Public or Other Users)**

**Primary User Goal:** "I want to evaluate this player's skill, trustworthiness, and potential as teammate/opponent."

**Mental Model:** This is a **Player Card** in a trading card game - I need to:
- Quickly assess skill level (Game Ranks)
- Verify identity (Trust Score, KYC Badge, Certificates)
- See team affiliation and role
- Decide if I want to interact (Challenge/Follow/Message)
- Compare stats with my own profile (future feature)

**Key UI Elements (Spectator-Specific):**
1. **Floating Action Bar (Hero Section)**
   - `👤 Follow` - Toggle button (green when following)
   - `⚔ Challenge` - Opens 1v1 challenge modal
   - `💬 Message` - Direct message (if privacy allows)

2. **Privacy-Aware Display:**
   - **Hidden Fields:** Show lock icon + "Hidden by Privacy Settings"
   - **Partial Data:** Phone shows as `(+880) ******` if masked
   - **Conditional Sections:** Wallet entirely hidden if private

3. **Comparison Tools (Future Phase):**
   - `[⚖ Compare with Me]` button in Game Passport
   - Side-by-side rank comparison modal

**Information Hierarchy (Spectator):**
```
Trust → Skill → Availability → Personality
  ↓       ↓         ↓            ↓
Score  Ranks   Team/Status   Trophies
```

---

### 1.2 Shared UX Principles

**Universal Navigation Rules:**
- **Sticky Header:** User avatar + quick nav bar stays at top on scroll
- **Breadcrumb Context:** Always show "Viewing: @username" in corner
- **Loading States:** Skeleton screens (not spinners) for all async data
- **Error States:** Friendly messages ("Oops! Game servers are down. Try again?")

**Micro-Interaction Standards:**
- **Hover:** 300ms transition, lift effect (transform: translateY(-4px))
- **Click Feedback:** Ripple effect on buttons (Tailwind ring classes)
- **Success Actions:** Toast notifications (top-right, auto-dismiss 3s)
- **Destructive Actions:** Confirmation modals with "Are you sure?" text

---

## 🎨 SECTION 2: THE "ESPORTS HUD" DESIGN SYSTEM

### 2.1 Color Palette (Semantic Tokens)

**Base Colors:**
```css
--bg-primary: rgb(2, 6, 23);        /* slate-950 - Deep space */
--bg-glass: rgba(15, 23, 42, 0.6); /* slate-900/60 - Glass panels */
--border-glass: rgba(255, 255, 255, 0.1); /* Frosted edge */

--brand-primary: #6366f1;   /* indigo-500 - Call-to-action */
--brand-glow: #818cf8;      /* indigo-400 - Hover state */

--accent-win: #10b981;      /* emerald-500 - Victory */
--accent-loss: #e11d48;     /* rose-600 - Defeat */
--accent-gold: #fbbf24;     /* amber-400 - Trophies */
--accent-verified: #3b82f6; /* blue-500 - Trust badge */

--text-primary: #f8fafc;    /* slate-50 - Headings */
--text-secondary: #94a3b8;  /* slate-400 - Body */
--text-muted: #64748b;      /* slate-500 - Labels */
```

**Gradient Definitions:**
```css
--gradient-hero: linear-gradient(to top, 
  rgb(2, 6, 23) 0%, 
  rgba(2, 6, 23, 0.8) 60%, 
  transparent 100%
);

--gradient-wallet: linear-gradient(135deg, 
  #6366f1 0%, 
  #8b5cf6 50%, 
  #a855f7 100%
);

--gradient-rank: linear-gradient(135deg, 
  #a855f7 0%, 
  #ec4899 100%
);
```

---

### 2.2 Typography System

**Font Stack:**
```css
--font-display: 'Inter', -apple-system, sans-serif;
--font-mono: 'JetBrains Mono', 'Courier New', monospace;
```

**Type Scale (Desktop):**
```
Hero Title:      text-6xl (60px) font-black uppercase tracking-tight
Section Header:  text-2xl (24px) font-bold uppercase tracking-wide
Card Title:      text-lg (18px) font-semibold
Body Text:       text-sm (14px) font-normal
Metadata:        text-xs (12px) font-medium text-slate-400
Data Values:     text-xl (20px) font-mono font-bold (e.g., "5,400 DC")
```

**Mobile Adjustments:**
- Hero Title: `text-4xl` (36px)
- Section Header: `text-xl` (20px)

---

### 2.3 Component Anatomy (The Glass Card Standard)

**Base Glass Card:**
```html
<div class="glass-card">
  <!-- Content -->
</div>

/* CSS */
.glass-card {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 1rem; /* 16px */
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}
```

**Card Variants:**
- **Default:** Neutral glass (slate-900/60)
- **Accent:** Colored border on hover (indigo-500/50)
- **Elevated:** Higher blur + shadow for sticky sections
- **Nested:** Darker glass (slate-800/60) for sub-cards

---

### 2.4 Micro-Interactions & Animations

**Animation Registry:**

1. **`pulse-border`** - Avatar Green Glow
   ```css
   @keyframes pulse-border {
     0%, 100% { box-shadow: 0 0 20px rgba(16, 185, 129, 0.6); }
     50% { box-shadow: 0 0 35px rgba(16, 185, 129, 0.9); }
   }
   animation: pulse-border 2s ease-in-out infinite;
   ```

2. **`spin-slow`** - DeltaCoin Icon Rotation
   ```css
   @keyframes spin-slow {
     from { transform: rotate(0deg); }
     to { transform: rotate(360deg); }
   }
   animation: spin-slow 3s linear infinite;
   ```

3. **`pulse-glow`** - Live Streaming Indicator
   ```css
   @keyframes pulse-glow {
     0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
     50% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
   }
   ```

4. **`hover-lift`** - Interactive Card Hover
   ```css
   .hover-lift {
     transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
   }
   .hover-lift:hover {
     transform: translateY(-4px);
     box-shadow: 0 20px 25px -5px rgba(99, 102, 241, 0.3);
   }
   ```

5. **`shimmer`** - Loading Skeleton
   ```css
   @keyframes shimmer {
     0% { background-position: -200% 0; }
     100% { background-position: 200% 0; }
   }
   background: linear-gradient(90deg, 
     rgba(51, 65, 85, 0.4) 25%, 
     rgba(71, 85, 105, 0.4) 50%, 
     rgba(51, 65, 85, 0.4) 75%
   );
   background-size: 200% 100%;
   animation: shimmer 1.5s infinite;
   ```

---

### 2.5 Iconography Guidelines

**Icon System:** Heroicons v2 (Outline for actions, Solid for status)

**Standard Icon Sizes:**
- Inline (text): `w-4 h-4` (16px)
- Card icons: `w-6 h-6` (24px)
- Feature icons: `w-8 h-8` (32px)
- Hero section: `w-12 h-12` (48px)

**Emoji Usage (Approved for Esports Context):**
- 🏆 Trophies/Achievements
- 🎮 Gaming/Platform
- 📍 Location
- 🎂 Age/Birthday
- 📞 Phone/Contact
- 💳 Wallet/Payment
- 📄 Certificate/Document
- ⚔ Challenge/Battle
- 🤺 Role: Duelist
- 🛡 Role: Tank/Defender

---

## 🏗 SECTION 3: STRUCTURAL BLUEPRINTS

### 3.1 Desktop Layout (1280px+): The Command Center

**Grid System:**
```
[ NAVBAR - Full Width, Fixed Top ]
+-----------------------------------------------------------+
|  HERO BANNER (Full Width, 280px Height)                   |
|  [ Cinematic Background Image with Gradient Fade ]        |
|  [ Floating Command Deck: Top-Right ]                     |
+-----------------------------------------------------------+
|                                                           |
| [ LEFT COLUMN ]    [ MIDDLE COLUMN ]    [ RIGHT COLUMN ]  |
|   (col-span-3)       (col-span-6)         (col-span-3)    |
|   Sticky Top         Scrollable           Sticky Top      |
|                                                           |
| +-------------+    +----------------+    +-------------+  |
| | IDENTITY    |    | TROPHY SHELF   |    | TEAM CARD   |  |
| | CARD        |    +----------------+    +-------------+  |
| +-------------+    | GAME PASSPORT  |    | WALLET      |  |
| | VITAL STATS |    | (Tabbed)       |    +-------------+  |
| +-------------+    +----------------+    | CERTIFICATES|  |
| | SOCIALS     |    | MATCH HISTORY  |    +-------------+  |
| +-------------+    +----------------+    |             |  |
|                                                           |
+-----------------------------------------------------------+
[ FOOTER - Full Width ]
```

**Spacing Standards:**
- Container: `max-w-7xl mx-auto px-4 md:px-6`
- Column Gap: `gap-6` (24px)
- Card Padding: `p-6` (24px)
- Section Spacing: `space-y-6` (24px vertical)

---

#### 3.1.1 Hero Banner (Full-Width, 280px)

**Structure:**
```html
<section class="relative w-full h-[280px] overflow-hidden">
  <!-- Background Layer -->
  <img src="{{ profile.banner }}" class="absolute inset-0 w-full h-full object-cover" />
  
  <!-- Gradient Overlay (Bottom 120px) -->
  <div class="absolute bottom-0 left-0 right-0 h-32 hero-fade"></div>
  
  <!-- Content Layer (Bottom Aligned) -->
  <div class="absolute bottom-0 left-0 right-0 container mx-auto px-6 pb-6">
    <div class="flex items-end justify-between">
      <!-- Left: Avatar + Name -->
      <div class="flex items-end gap-6">
        <img src="{{ avatar }}" class="w-40 h-40 rounded-full border-[6px] border-slate-950 animate-pulse-border" />
        <div class="pb-2">
          <h1 class="text-5xl font-black text-white uppercase">{{ display_name }}</h1>
          <p class="text-slate-400">@{{ username }} • Lvl {{ level }}</p>
        </div>
      </div>
      
      <!-- Right: Floating Command Deck -->
      <div class="pb-2 flex gap-3">
        {% if is_owner %}
          <button class="glass-card px-5 py-3">⚙ Settings</button>
          <button class="glass-card px-5 py-3">↗ Share</button>
        {% else %}
          <button class="bg-emerald-600 px-6 py-3">👤 Follow</button>
          <button class="bg-gradient-to-r from-rose-600 to-pink-600 px-6 py-3">⚔ Challenge</button>
        {% endif %}
      </div>
    </div>
  </div>
</section>
```

**Owner vs Spectator Differences:**
| Element | Owner View | Spectator View |
|---------|------------|----------------|
| Action Buttons | Settings, Share | Follow, Challenge, Message |
| Wallet Visibility | Full access | Blurred if private |
| Edit Icons | Visible on hover | Hidden |

---

#### 3.1.2 Left Column: Identity (Sticky, col-span-3)

**Card Stack (Top to Bottom):**

**A. Identity Card**
```
+---------------------------+
| [ 128px Avatar ]          |
| (Pulsing Green Border)    |
|                           |
| VIPER ✔                   |
| @viper_bd • Lvl 42        |
|                           |
| [  Edit  ] [ Message ]    |
+---------------------------+
```

**B. Vital Statistics**
```
+---------------------------+
| VITAL STATISTICS          |
|---------------------------|
| 📍 Bangladesh, Dhaka      |
| 🎂 22 years old           |
| 📞 (+880) ****** [🔒]     |
|                           |
| Reputation Score          |
| [████████░░] 85%          |
| ✓ High Trust              |
+---------------------------+
```

**C. Connected Socials**
```
+---------------------------+
| CONNECTED SOCIALS         |
|---------------------------|
| 🎮 Discord                |
|    viper#001  [Online]    |
|                           |
| 📺 Twitch  [LIVE]         |
|    /viper_streams         |
|                           |
| 👥 Facebook               |
|    /official.viper        |
+---------------------------+
```

**Data Requirements:**
- Fields: `avatar`, `display_name`, `username`, `level`, `country`, `city`, `age`, `phone`, `reputation_score`, `is_kyc_verified`
- Social Links: JSON array `[{platform, handle, url, is_live}]`
- Privacy Checks: `privacy_settings.show_phone`, `privacy_settings.show_age`, etc.

---

#### 3.1.3 Middle Column: Performance Feed (Scrollable, col-span-6)

**Section Stack:**

**A. Trophy Shelf (Horizontal Scroll)**
```
+-----------------------------------------------------+
| 🏆 FEATURED TROPHIES                                 |
|-----------------------------------------------------|
| [ 🏆 ]    [ 🥇 ]    [ 🎙️ ]    [ 🏅 ]    [ 🎖️ ]    |
| S1 Champ   MVP     Caster   Top 10    Verified     |
+-----------------------------------------------------+
```
- Data: `pinned_badges` (max 5)
- Interaction: Click to expand achievement details modal

**B. Game Passport (Tabbed Interface)**
```
+-----------------------------------------------------+
| 🎮 GAME PASSPORT                                     |
|-----------------------------------------------------|
| [VALORANT] [CS2] [PUBG] [eFootball]                |
|                                                     |
| +-----------------------------------------------+   |
| | [ Rank Icon ]  ASCENDANT 2                    |   |
| |                (Top 4.2% of Region)           |   |
| |                                               |   |
| | Riot ID: Viper#BD1  [ 📋 Copy ]               |   |
| |                                               |   |
| | Main Roles:                                   |   |
| | [🤺 Duelist] [🎮 Initiator]                   |   |
| +-----------------------------------------------+   |
+-----------------------------------------------------+
```
- Data: `game_profiles` (JSON array)
- Schema per game:
  ```json
  {
    "game": "Valorant",
    "rank": "Ascendant 2",
    "ign": "Viper#BD1",
    "role": "Duelist",
    "platform": "PC"
  }
  ```

**C. Match History Stream**
```
+-----------------------------------------------------+
| 📊 MATCH HISTORY                                     |
|-----------------------------------------------------|
| [ ✓ WIN ] vs Team Phoenix (Valorant)                |
| Map: Ascent • 13-9 • 2h ago                         |
| Stats: 24/12/5 (KDA)                                |
|-----------------------------------------------------|
| [ ✗ LOSS ] vs Team Shadow (CS2)                     |
| Map: Mirage • 12-16 • Yesterday                     |
| Stats: 18/20/4 (KDA)                                |
+-----------------------------------------------------+
```
- Data: `match_history` (paginated, last 10)
- Visual: Green left-border for wins, red for losses

---

#### 3.1.4 Right Column: Meta Data (Sticky, col-span-3)

**Card Stack:**

**A. Current Team**
```
+---------------------+
| CURRENT TEAM        |
|---------------------|
| [ Team Logo 96px ]  |
|                     |
| TEAM DELTA          |
| Role: Captain (IGL) |
|                     |
| Roster:             |
| [😊][😎][🤠] +2     |
|                     |
| [ View Team Page ]  |
+---------------------+
```

**B. Wallet (Private - Owner Only)**
```
+---------------------+
| 💳 DELTACOIN WALLET |
|---------------------|
| [ 💰 Spinning Coin ]|
|                     |
| Balance:            |
| 5,400 DC            |
|                     |
| Earnings (30d):     |
| [Sparkline Graph]   |
|                     |
| [+ Deposit Funds]   |
+---------------------+
```
- Animation: Coin spins 360° every 3s
- Privacy: If spectator, show blurred + lock icon

**C. Certificate Vault**
```
+---------------------+
| 📄 CERTIFICATES     |
|---------------------|
| Season 1 Champion   |
| [ ⬇ Download ]      |
|                     |
| MVP Award 2024      |
| [ ⬇ Download ]      |
|                     |
| [ View Vault > ]    |
+---------------------+
```

---

### 3.2 Mobile Layout (< 768px): The Native App Feel

**Strategy:** Convert 3-column grid into tabbed interface with sticky navigation.

**Structure:**
```
[ NAVBAR - Fixed Top ]
+-------------------------+
| HERO BANNER (Compact)   |
| 220px Height            |
+-------------------------+
| STICKY TAB NAV          |
| [ INFO ] [ GAMES ] [ CAREER ] |
+-------------------------+
|                         |
| TAB CONTENT             |
| (Scrollable)            |
|                         |
+-------------------------+
| FLOATING ACTION BAR     |
| [Follow] [Challenge]    |
+-------------------------+
```

**Tab Mapping:**
| Tab | Content |
|-----|---------|
| INFO | Identity Card + Vital Stats + Trophy Shelf + Socials |
| GAMES | Game Passport + Match History |
| CAREER | Team Card + Wallet + Certificates |

**Sticky Tab Navigation:**
```html
<div class="sticky top-0 z-50 bg-slate-950/90 backdrop-blur-xl border-b border-white/10">
  <div class="flex">
    <button @click="tab='info'" :class="tab==='info' ? 'border-b-2 border-indigo-500' : ''">
      INFO
    </button>
    <button @click="tab='games'" :class="tab==='games' ? 'border-b-2 border-indigo-500' : ''">
      GAMES
    </button>
    <button @click="tab='career'" :class="tab==='career' ? 'border-b-2 border-indigo-500' : ''">
      CAREER
    </button>
  </div>
</div>
```

**Floating Action Bar (Fixed Bottom):**
```html
<div class="fixed bottom-0 left-0 right-0 z-50 mobile-action-bar p-4">
  <div class="flex gap-3">
    <button class="flex-1 bg-emerald-600">Follow</button>
    <button class="flex-1 bg-gradient-to-r from-rose-600 to-pink-600">Challenge</button>
    <button class="glass-card">💬</button>
  </div>
</div>
```

---

## ⚙ SECTION 4: FEATURE SPECIFICATION

### 4.1 The Game Passport (Pluggable Engine)

**Problem:** We support 9+ games (Valorant, CS2, PUBG, MLBB, Free Fire, eFootball, Dota 2, COD Mobile, EA FC). Creating a database column for each game's rank/ID is unsustainable.

**Solution:** JSON-based flexible schema stored in `UserProfile.game_profiles` (JSONField).

**Data Structure:**
```json
{
  "valorant": {
    "rank": "Ascendant 2",
    "rank_tier": "A2",
    "ign": "Viper#BD1",
    "region": "AP",
    "role": "Duelist",
    "last_updated": "2025-11-26T12:00:00Z"
  },
  "cs2": {
    "rank": "Global Elite",
    "rank_rating": 25000,
    "steam_id": "76561198012345678",
    "faceit_elo": 2800,
    "role": "AWPer"
  },
  "pubg_mobile": {
    "rank": "Conqueror",
    "tier": "Top 500",
    "ign": "ViperBD",
    "server": "Asia"
  }
}
```

**UI Implementation:**
- **Tab Generator:** Loop through `game_profiles.keys()` to create tabs dynamically
- **Default State:** If empty, show "No games added" with `[+ Add Your First Game]` button
- **Owner Actions:** Each tab has `[✏ Edit]` `[🗑 Remove]` buttons
- **Validation:** Client-side checks for valid Riot ID format (name#TAG), Steam ID length, etc.

---

### 4.2 The Privacy Matrix (Granular Control)

**Model:** `PrivacySettings` (OneToOne with UserProfile)

**Fields:**
```python
class PrivacySettings(models.Model):
    # Profile Fields
    show_real_name = models.CharField(choices=VISIBILITY_CHOICES, default='PUBLIC')
    show_age = models.CharField(choices=VISIBILITY_CHOICES, default='PUBLIC')
    show_phone = models.CharField(choices=VISIBILITY_CHOICES, default='PRIVATE')
    show_country = models.CharField(choices=VISIBILITY_CHOICES, default='PUBLIC')
    
    # Social Links
    show_social_links = models.CharField(choices=VISIBILITY_CHOICES, default='PUBLIC')
    
    # Economy
    show_wallet_balance = models.CharField(choices=VISIBILITY_CHOICES, default='FRIENDS')
    show_transaction_history = models.CharField(choices=VISIBILITY_CHOICES, default='PRIVATE')
    
    # Gaming
    show_match_history = models.CharField(choices=VISIBILITY_CHOICES, default='PUBLIC')
    show_game_ids = models.CharField(choices=VISIBILITY_CHOICES, default='PUBLIC')

VISIBILITY_CHOICES = [
    ('PUBLIC', 'Everyone'),
    ('FRIENDS', 'Friends Only'),
    ('PRIVATE', 'Only Me')
]
```

**UI Representation (Owner Settings Page):**
```
PRIVACY MATRIX
+------------------------------------------+
| Field              | Visibility          |
|--------------------|---------------------|
| Real Name          | [👁 Everyone ▾]     |
| Age                | [👁 Everyone ▾]     |
| Phone Number       | [🔒 Only Me ▾]      |
| Wallet Balance     | [👥 Friends ▾]      |
| Game IDs           | [👁 Everyone ▾]     |
+------------------------------------------+
```

**Template Logic:**
```django
{% if privacy_settings.show_phone == 'PUBLIC' or is_owner %}
  <p>📞 {{ profile.phone }}</p>
{% elif privacy_settings.show_phone == 'FRIENDS' and is_friend %}
  <p>📞 {{ profile.phone }}</p>
{% else %}
  <p>📞 ******** 🔒 Hidden</p>
{% endif %}
```

---

### 4.3 DeltaCoin Economy Visualization

**Wallet Card Components:**

1. **Balance Display**
   - Large monospace font: `text-4xl font-mono font-black`
   - Animated counter (numbers increment on page load)
   - Blur toggle button for privacy

2. **Spinning Coin Icon**
   - SVG or emoji (💰) with `animate-spin-slow`
   - Positioned absolute top-right of balance card

3. **Sparkline Graph (Last 30 Days)**
   - SVG path showing earnings trend
   - Green if net positive, red if negative
   - Tooltip on hover showing exact amounts

4. **Quick Actions**
   - `[+ Deposit]` - Opens payment modal
   - `[↗ Withdraw]` - Opens bank transfer form
   - `[📊 Full History]` - Links to transactions page

**Transaction Timeline (Separate Page):**
```
+--------------------------------------------------------+
| TRANSACTION HISTORY                                     |
|---------------------------------------------------------|
| Nov 26 • 14:30                           +500 DC        |
| Tournament Entry Fee Refund              [Receipt]     |
|---------------------------------------------------------|
| Nov 25 • 09:15                           -1,200 DC      |
| Team Registration: Winter Cup 2025       [Receipt]     |
|---------------------------------------------------------|
```

---

### 4.4 Team Integration (Cross-App Linking)

**Team Card Interaction:**
- **Click Behavior:** `onclick="window.location.href='/teams/{{ team.slug }}/'"` 
- **Hover Effect:** `hover-lift` + border color changes to team's brand color
- **Facepile Logic:** Show first 3 members, then "+N" for remaining

**Data Flow:**
```python
# In views.py
from apps.teams.models import TeamMembership

team_memberships = TeamMembership.objects.filter(
    profile=profile, 
    status='ACTIVE'
).select_related('team')

current_team = team_memberships.first()
```

**Template:**
```django
{% if current_team %}
  <div class="team-card hover-lift cursor-pointer" 
       onclick="window.location.href='{% url 'teams:detail' current_team.team.slug %}'">
    <img src="{{ current_team.team.logo.url }}" class="w-24 h-24" />
    <h4>{{ current_team.team.name }}</h4>
    <p>Role: {{ current_team.get_role_display }}</p>
  </div>
{% endif %}
```

---

## 🚀 SECTION 5: IMPLEMENTATION ROADMAP

### Phase 2: Foundation (Week 1)
- [ ] Create base template structure (HTML skeleton)
- [ ] Build CSS design system (profile.css with all animations)
- [ ] Implement responsive grid (Desktop 3-col, Mobile tabs)
- [ ] Set up Alpine.js for reactive components

### Phase 3: Core Features (Week 2)
- [ ] Hero section with owner/spectator mode switching
- [ ] Left column: Identity + Vitals + Socials
- [ ] Middle column: Trophy shelf + Game Passport tabs
- [ ] Right column: Team card + Wallet + Certificates

### Phase 4: Interactivity (Week 3)
- [ ] Copy-to-clipboard for Game IDs
- [ ] Privacy toggle buttons (inline editing)
- [ ] Follow/Unfollow AJAX
- [ ] Challenge modal system
- [ ] Toast notification system

### Phase 5: Data Integration (Week 4)
- [ ] Connect to real match history API
- [ ] Transaction timeline from economy app
- [ ] Badge system integration
- [ ] Certificate PDF generation

### Phase 6: Polish & Testing (Week 5)
- [ ] Loading skeletons for all sections
- [ ] Error state handling
- [ ] Mobile optimization (thumb zones)
- [ ] Cross-browser testing
- [ ] Performance audit (Lighthouse 90+ score)

---

## 📊 SUCCESS METRICS

**Performance Targets:**
- Initial Load: < 2s (on 4G)
- Time to Interactive: < 3s
- Lighthouse Score: 90+ (Performance, Accessibility, Best Practices)

**User Experience Metrics:**
- Bounce Rate: < 30% (spectator view)
- Avg. Session Duration: > 2 minutes
- Click-Through Rate (Follow button): > 15%
- Privacy Settings Adoption: > 60% of users customize at least one field

---

## 🔐 SECURITY & PRIVACY CONSIDERATIONS

1. **CSRF Protection:** All AJAX requests must include Django's CSRF token
2. **Privacy Enforcement:** Server-side checks (never trust client-side visibility logic)
3. **Rate Limiting:** Follow/Challenge actions limited to 10/minute per user
4. **Data Sanitization:** All user inputs (display name, bio) must be escaped (XSS prevention)
5. **Wallet Display:** Always blur balance by default on public view (opt-in to show)

---

## ⚠️ CRITICAL IMPLEMENTATION NOTES (Added Nov 26, 2025)

### 🛡️ Data Validation & UX Safety

#### 1. JSON Data Validation (Game Profiles)
**Problem:** Users typing "iron-one" instead of "Iron 1" will break UI icon mapping.

**Solution:**
```python
# In forms.py or modals
VALORANT_RANKS = [
    ('iron_1', 'Iron 1'),
    ('iron_2', 'Iron 2'),
    ('iron_3', 'Iron 3'),
    ('bronze_1', 'Bronze 1'),
    # ... all ranks
    ('radiant', 'Radiant'),
]

VALORANT_ROLES = [
    ('duelist', 'Duelist'),
    ('controller', 'Controller'),
    ('initiator', 'Initiator'),
    ('sentinel', 'Sentinel'),
]
```

**UI Implementation:**
- **"Add Game" Modal:** Use `<select>` dropdowns (NOT text inputs) for Rank and Role
- **IGN Field:** Only this field should be free text (with validation regex)
- **Platform:** Radio buttons (PC, Console, Mobile)
- **Validation:** Client-side checks before JSON save

**Template Example:**
```django
<!-- Add Game Modal -->
<select name="rank" class="glass-input">
    <option value="">Select Rank...</option>
    <option value="iron_1">Iron 1</option>
    <option value="bronze_1">Bronze 1</option>
    <!-- ... -->
</select>
```

#### 2. Inline Editing vs. Modals
**Problem:** True inline editing (click-to-edit text) is fragile in glassmorphic designs and causes layout shifts.

**Decision for V1:** **Use Modals ONLY**

**Rationale:**
- Cleaner visual hierarchy (no sudden input fields appearing)
- Better validation UX (can show all errors in one place)
- No layout thrashing on mobile
- Easier to implement loading states

**Implementation:**
```html
<!-- AVOID: Inline Edit (V1) -->
<h1 contenteditable @blur="saveName()">{{ name }}</h1> ❌

<!-- USE: Modal Edit (V1) -->
<h1>{{ name }}</h1>
<button @click="openEditModal()">✏ Edit</button> ✅
```

**Modal Structure:**
- Edit Profile Modal (Avatar, Banner, Display Name, Bio)
- Add Game Modal (Game, IGN, Rank, Role, Platform)
- Privacy Settings Modal (Checkboxes for all privacy flags)

#### 3. Mobile Performance (Backdrop Blur Fallback)
**Problem:** `backdrop-filter: blur(24px)` can lag on older Android devices (< 2020 models).

**Solution:** Progressive enhancement with fallback

**CSS Implementation:**
```css
.glass-card {
    /* Fallback: Solid opaque background */
    background: rgba(15, 23, 42, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
    
    /* Enhancement: Blur for modern devices */
    @supports (backdrop-filter: blur(24px)) or (-webkit-backdrop-filter: blur(24px)) {
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
    }
}
```

**Performance Budget:**
- Max 3 glass cards visible at once on mobile
- Disable blur on scroll (optional optimization for low-end devices)
- Use `will-change: transform` sparingly (only on hover states)

---

### 🎨 Empty States Design

#### Empty State 1: No Game Profiles
**Trigger:** `game_profiles` is empty list or null

**Design:**
```html
<div class="text-center py-16">
    <!-- Icon -->
    <div class="w-32 h-32 mx-auto mb-6 rounded-full bg-slate-800/50 border-2 border-dashed border-slate-700 flex items-center justify-center text-6xl animate-pulse">
        🎮
    </div>
    
    <!-- Headline -->
    <h3 class="text-2xl font-bold text-white mb-3">
        Ready to Showcase Your Skills?
    </h3>
    
    <!-- Description -->
    <p class="text-slate-400 max-w-md mx-auto mb-8">
        Link your game accounts to display ranks, stats, and prove your competitive prowess. 
        Supports 9+ games including Valorant, CS2, PUBG Mobile, and more.
    </p>
    
    <!-- CTA Button (Owner Only) -->
    {% if is_own_profile %}
    <button @click="openAddGameModal()" 
            class="inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-lg font-bold rounded-xl shadow-2xl shadow-indigo-500/50 transform hover:scale-105 transition-all duration-300">
        <span class="text-2xl">🔗</span>
        <span>Link Your First Game</span>
    </button>
    {% else %}
    <p class="text-slate-500 text-sm italic">
        User hasn't added any games yet
    </p>
    {% endif %}
</div>
```

#### Empty State 2: No Pinned Badges
**Trigger:** `pinned_badges` is empty

**Design:**
```html
<div class="text-center py-12">
    <div class="inline-flex items-center gap-3 px-6 py-3 rounded-full bg-slate-800/50 border border-slate-700">
        <span class="text-3xl">🏆</span>
        <span class="text-slate-400">No featured trophies yet. {% if is_own_profile %}Earn badges to pin them here!{% endif %}</span>
    </div>
</div>
```

#### Empty State 3: No Team
**Trigger:** `current_teams` is empty

**Design:**
```html
<div class="text-center py-8">
    <div class="w-20 h-20 mx-auto mb-4 rounded-xl bg-slate-800/50 border-2 border-dashed border-slate-700 flex items-center justify-center text-4xl">
        🛡
    </div>
    <p class="text-slate-400 text-sm mb-4">
        {% if is_own_profile %}
            You're not part of any team yet
        {% else %}
            Solo player
        {% endif %}
    </p>
    {% if is_own_profile %}
    <a href="{% url 'teams:create' %}" 
       class="inline-block text-indigo-400 hover:text-indigo-300 text-sm font-semibold">
        Create or Join a Team →
    </a>
    {% endif %}
</div>
```

---

### 🔔 Notification Indicator System

#### Bell Icon in Hero Action Bar

**Position:** Add to floating command deck (between Share and Profile dropdown)

**Desktop Layout:**
```html
<!-- Owner View -->
<div class="flex gap-3 pb-2">
    <a href="{% url 'user_profile:settings' %}" class="glass-card px-5 py-3">⚙ Settings</a>
    <button @click="shareProfile()" class="glass-card px-5 py-3">↗ Share</button>
    
    <!-- NEW: Notification Bell -->
    <button @click="openNotifications()" 
            class="glass-card px-5 py-3 relative">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
        </svg>
        
        <!-- Badge: Unread Count (Conditional) -->
        <span x-show="notificationCount > 0" 
              class="absolute -top-1 -right-1 w-5 h-5 bg-rose-600 text-white text-xs font-bold rounded-full flex items-center justify-center animate-pulse-glow"
              x-text="notificationCount"></span>
    </button>
</div>
```

**Notification Types to Show:**
1. **Friend Requests** (👤)
2. **Team Invites** (🛡)
3. **Challenge Requests** (⚔)
4. **Match Results** (🏆)
5. **System Announcements** (📢)

**Dropdown Menu (on click):**
```html
<div x-show="showNotifications" 
     @click.away="showNotifications = false"
     class="absolute top-full right-0 mt-2 w-96 max-h-[500px] overflow-y-auto glass-card border border-slate-700 rounded-xl shadow-2xl z-50">
    
    <!-- Header -->
    <div class="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
        <h3 class="text-white font-bold">Notifications</h3>
        <button class="text-indigo-400 hover:text-indigo-300 text-sm font-semibold">
            Mark all read
        </button>
    </div>
    
    <!-- Notification List -->
    <div class="divide-y divide-slate-700">
        {% for notification in notifications %}
        <div class="px-4 py-3 hover:bg-slate-800/50 transition-colors cursor-pointer {% if not notification.is_read %}bg-indigo-500/5{% endif %}">
            <div class="flex items-start gap-3">
                <span class="text-2xl">{{ notification.icon }}</span>
                <div class="flex-1 min-w-0">
                    <p class="text-white text-sm font-semibold mb-1">{{ notification.title }}</p>
                    <p class="text-slate-400 text-xs">{{ notification.time_ago }}</p>
                </div>
                {% if not notification.is_read %}
                <span class="w-2 h-2 bg-indigo-500 rounded-full"></span>
                {% endif %}
            </div>
        </div>
        {% empty %}
        <div class="px-4 py-8 text-center">
            <p class="text-slate-500 text-sm">All caught up! 🎉</p>
        </div>
        {% endfor %}
    </div>
    
    <!-- Footer -->
    <div class="px-4 py-3 border-t border-slate-700 text-center">
        <a href="{% url 'notifications:all' %}" class="text-indigo-400 hover:text-indigo-300 text-sm font-semibold">
            View All Notifications →
        </a>
    </div>
</div>
```

**Alpine.js State:**
```javascript
{
    notificationCount: {{ unread_notification_count|default:0 }},
    showNotifications: false,
    
    openNotifications() {
        this.showNotifications = !this.showNotifications;
        // Optionally: Mark as read on open
        if (this.showNotifications && this.notificationCount > 0) {
            // AJAX call to mark notifications as seen
        }
    }
}
```

**Backend Context (views.py):**
```python
# Add to profile_view context
from apps.notifications.models import Notification

unread_notifications = Notification.objects.filter(
    recipient=profile,
    is_read=False
).order_by('-created_at')[:5]

unread_count = unread_notifications.count()

context = {
    # ... existing context
    'unread_notifications': unread_notifications,
    'unread_notification_count': unread_count,
}
```

---

### 📋 Updated Implementation Checklist

**Before Writing Code:**
- [x] Add JSON validation rules to master plan
- [x] Document modal-first approach (no inline editing in V1)
- [x] Add backdrop-blur fallback CSS
- [x] Design empty states for all major sections
- [x] Add notification bell to hero action bar

**During Implementation:**
- [ ] Create dropdown options for all game ranks/roles
- [ ] Build 3 modals: Edit Profile, Add Game, Privacy Settings
- [ ] Add `@supports` queries for backdrop-filter
- [ ] Implement empty state templates for each section
- [ ] Add notification bell with Alpine.js state management

**Testing Checklist:**
- [ ] Test on Android Chrome (2019 device) - check blur performance
- [ ] Try submitting "iron-one" in Add Game modal - should be impossible
- [ ] Verify empty states show for new user profile
- [ ] Check notification bell updates in real-time

---

## 📝 APPENDIX A: TEMPLATE FILE STRUCTURE

```
templates/user_profile/
├── profile.html              # Main profile page (this is THE file)
├── components/
│   ├── _identity_card.html
│   ├── _vital_stats.html
│   ├── _social_links.html
│   ├── _trophy_shelf.html
│   ├── _game_passport.html
│   ├── _match_history.html
│   ├── _team_card.html
│   ├── _wallet_card.html
│   └── _certificates.html
└── modals/
    ├── _edit_profile_modal.html
    ├── _challenge_modal.html
    └── _privacy_settings_modal.html
```

---

## 📝 APPENDIX B: JAVASCRIPT ARCHITECTURE

**Core Libraries:**
- **Alpine.js 3.x** - Reactive components (tabs, toggles)
- **Vanilla JS** - Copy-to-clipboard, AJAX, animations
- **NO jQuery** - Modern ES6+ only

**File Structure:**
```
static/js/
├── profile.js              # Main orchestrator
├── profile/
│   ├── clipboard.js        # Copy IGN functionality
│   ├── privacy.js          # Toggle visibility
│   ├── wallet.js           # Balance blur/animation
│   ├── challenge.js        # Challenge modal logic
│   └── follow.js           # Follow/unfollow AJAX
```

---

## ✅ PHASE 1 COMPLETE - AWAITING APPROVAL

**Next Steps:**
1. **Review this Master Plan** - Provide feedback on any section
2. **Approve to Proceed** - Once confirmed, we move to Phase 2 (Frontend Development)
3. **Backend Adjustments** - Identify any model fields we need to add/modify

**Questions for Product Owner:**
- Should we add "Compare with Me" feature now or defer to Phase 7?
- What's the priority: Mobile polish or Desktop feature completeness?
- Do we need real-time updates (WebSockets) for "Live" status or polling is fine?

---

**Document Status:** ✅ READY FOR REVIEW  
**Prepared By:** Lead UX/UI Architect  
**Approval Required From:** Product Owner, Tech Lead
