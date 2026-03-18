# DeltaCrown — Rankings Page Design Brief
### For UI/UX Designer · Deliverable: Single-Page HTML Demo

---

## 1. Project Background

**DeltaCrown** is a competitive esports platform where teams register, challenge each other, compete in tournaments, and earn ranking points. The platform is dark-themed, esports-focused, and targets a young competitive audience.

**Page URL:** `http://127.0.0.1:8000/competition/rankings/`  
**Also renders as:** `http://127.0.0.1:8000/competition/rankings/<game_id>/` (same page, filtered to one game)  
**Purpose:** The global competitive leaderboard — the highest-prestige page on the site.

This document gives you everything you need to design a beautiful, modern, mobile-responsive **single-page HTML demo** from scratch. You have full creative freedom on layout, visuals, and new sections — just preserve the data fields and sections described here so that the developer can wire it up to the backend.

---

## 2. Brand & Design Identity

| Property | Value |
|---|---|
| Primary font | **Rajdhani** (Google Fonts) — used for all headings, rank numbers, scores |
| Body font | **Inter** or system-ui |
| Primary accent | Cyan `#06b6d4` |
| Background | Near-black `#05050A` |
| Surface cards | `rgba(255,255,255, 0.028)` — ultra-transparent glass |
| Border color | `rgba(255,255,255, 0.07)` |
| Success/Active | `#22c55e` |
| Warning/Yellow | `#facc15` |
| Purple | `#8b5cf6` |
| Text muted | `#94a3b8` (slate-400) |

**Aesthetic keywords:** Dark. Cinematic. Glassmorphism. Esports. Premium. Immersive.  
Think: Riot Games leaderboard meets Liquipedia meets a next-gen dashboard.

---

## 3. The Tier System

There are **6 competitive tiers**. Every team belongs to exactly one. These drive all visual color-coding on this page.

| # | Tier Name | Display | Color | Min Crown Points |
|---|---|---|---|---|
| 1 | **THE_CROWN** | 👑 THE CROWN | `#ffd700` (gold) | 30,000 CP |
| 2 | **LEGEND** | 🔥 LEGEND | `#f97316` (orange) | 8,000 CP |
| 3 | **MASTER** | 💎 MASTER | `#8b5cf6` (purple) | 2,000 CP |
| 4 | **ELITE** | 🥇 ELITE | `#3b82f6` (blue) | 500 CP |
| 5 | **CHALLENGER** | 🛡 CHALLENGER | `#22c55e` (green) | 100 CP |
| 6 | **ROOKIE** | 🌱 ROOKIE | `#9ca3af` (grey) | 0 CP |

Tier badges are pill-shaped labels with the tier's color (gradient) as background.

---

## 4. Data Available on the Page

This is everything the backend sends to the template. Design your sections around these fields.

### 4a. Per-Team Entry (`entry` in `entries` list)

Every team in the list has these fields:

| Field | Type | Example | Notes |
|---|---|---|---|
| `entry.rank` | Integer | `1`, `2`, `42` | Global rank position |
| `entry.team_name` | String | `"Alpha Wolves"` | Full team name |
| `entry.team_tag` | String | `"AWV"` | Short 2-5 char tag, shown in brackets |
| `entry.team_slug` | String | `"alpha-wolves"` | URL slug |
| `entry.team_url` | String | `"/teams/alpha-wolves/"` | Clickable link to team profile |
| `entry.team_logo_url` | String or null | `"/media/logos/team.png"` | May be null — show initials if missing |
| `entry.organization_name` | String or null | `"World Esports Club"` | Parent org; null = show "Independent" |
| `entry.score` | Integer | `12500` | Crown Points (CP) — main score |
| `entry.tier` | String | `"MASTER"` | One of the 6 tiers above |
| `entry.activity_score` | Integer | `0–100` | Activity index: ≥80 = high, ≥40 = mid, <40 = low |
| `entry.is_independent` | Boolean | `true/false` | True = no parent org |
| `entry.confidence_level` | String | `"STABLE"` | Data quality indicator |

### 4b. Page-Level Context

| Variable | Type | Example |
|---|---|---|
| `total_count` | Integer | `62` — total ranked teams |
| `max_score` | Integer | `28000` — highest CP (used for relative progress bars) |
| `tier_filter` | String or empty | `"MASTER"` — currently active tier filter |
| `verified_only` | Boolean | `false` |
| `selected_game` | String or null | `"valorant"` — null = global view |
| `selected_game_name` | String or null | `"Valorant"` — null = global view |
| `query_count` | Integer | `2` — debug info, can be shown small |

### 4c. Game Configs (for the game selector)

A list of games that have ranking configs. Each game:

| Field | Example |
|---|---|
| `config.game_id` | `"valorant"` |
| `config.game_name` | `"Valorant"` |
| `config.color` | `"#FF4655"` (the game's brand color) |

Example games: Valorant, CS2, League of Legends, Dota 2, Rocket League, PUBG, etc.

### 4d. Tier Details (for the Tier System explainer section)

A list of 6 items, each:

| Field | Example |
|---|---|
| `tier_info.name` | `"The Crown"` |
| `tier_info.icon` | `"fa-crown"` (FontAwesome class) |
| `tier_info.icon_color` | `"text-yellow-300"` (Tailwind class) |
| `tier_info.bg_class` | `"bg-yellow-400/10"` (Tailwind class) |
| `tier_info.threshold` | `"30,000"` |

### 4e. User Highlights (for logged-in users)

Shows the viewer's own teams in the rankings. May be null if user is not logged in.

```
user_highlights = {
  best_rank: 14,                        // best rank across all their teams
  teams: [
    { team_name: "My Team", team_slug: "my-team", rank: 14 },
    ...
  ]
}
```

---

## 5. Page Sections — Current Implementation

Here is every section the page currently has, top to bottom. Design your demo to include all of these (plus any new ones you want to add):

---

### Section 1: Ambient / Background Layer
**Type:** Visual / decorative  
**What it does:** Floating radial glow blobs that slowly drift — one cyan blob top-left, one purple blob bottom-right. Fixed position, behind all content, z-index 0.  
**Purpose:** Creates depth and immersion without distracting from content.

---

### Section 2: Hero / Page Header
**Type:** Content header  
**Position:** Top center of page  
**Contains:**
- A small pill badge: `● DeltaCrown Ranking System · DCRS [LIVE]`
- Large gradient title: **"Global Arena"** (or **"[Game Name] Rankings"** when filtered)
- Subtitle paragraph describing the rankings

**Design notes:**
- Title uses gradient text: cyan → purple → gold for the global view
- Animate in on page load (fade + slide up)

---

### Section 3: Stats / KPI Row
**Type:** Summary metrics  
**Layout:** 4 cards in a row (2×2 on mobile)  
**Cards:**
1. **Teams Ranked** — total_count (white number)
2. **Games Live** — number of games (gold number)
3. **Tier Levels** — always 6 (purple number)
4. **Top CP** — the #1 team's score (cyan number)

**Design notes:** Dark glass cards. Large bold number on top, small uppercase label below. No icons needed.

---

### Section 4: Sticky Filter Bar
**Type:** Interactive controls  
**Behavior:** Sticks to the top of the viewport while scrolling. Glass background + blur.  
**Contains:**
- **Game selector pills** — horizontal scrollable pill buttons: "All", then one per configured game (with a colored dot matching the game's color, and game name). Only one active at a time. Clicking navigates to the game-specific ranking URL.
- **Tier filter** — a `<select>` dropdown: "All Tiers", then each of the 6 tiers. On change = page reloads with `?tier=TIER_NAME`.
- **Live search input** — text input that instantly filters visible teams by name (client-side, no page reload).
- **"Policy" link** — small text link to the ranking explanation page.

**Design notes:** The active game pill should be highlighted with the page accent color. The bar darkens (shadow increases) as the user scrolls down.

---

### Section 5: "Your Standing" Band *(conditional — logged in users only)*
**Type:** Personalized callout  
**Behavior:** Only shown when the viewer is authenticated AND has at least one ranked team.  
**Contains:**
- Star/award icon + "Your Standing" label
- "Best rank: #14" subtitle
- Chips for each of their teams: team name + rank badge

**Design notes:** Gold left border accent. This should feel personal and motivating.

---

### Section 6: Podium — Top 3
**Type:** Visual hero section for the top 3 teams  
**Layout:** On desktop: 2nd (left, slightly lowered) | 1st (center, tallest) | 3rd (right, most lowered). On mobile: stacked vertically (1st, 2nd, 3rd order).  

**For each podium spot:**
- Rank number (large, colored gold/silver/bronze)
- Team logo (or initials-based avatar if no logo)
- Team name (clickable)
- Organization name (small, grey)
- Tier badge
- Crown Points score
- CP progress bar (full-width at bottom of card, % relative to max score)
- Activity indicator (only on 1st place: pulsing dot + "Activity 92")

**Card styling per rank:**
- **1st:** Gold border glow, star icon above rank, larger card. Gold shadow.
- **2nd:** Silver border, slightly smaller card.
- **3rd:** Bronze/copper border, smallest card, most offset.

---

### Section 7: Full Rankings Table (Rank 4 onwards)
**Type:** Data table  
**Header bar contains:** "Full Standings" title + team count chip + active tier chip + query count (debug, small) + "Clear filters" link (shown only when filters active).  

**Table columns:**
| Column | Hidden on mobile? | Description |
|---|---|---|
| `#` | No | Rank number, large bold |
| Team | No | Logo + name + team tag + org name; on mobile also shows tier badge |
| Tier | Hidden on mobile | Colored tier badge |
| Crown Points | No | Score value + mini progress bar below it |
| Activity | Hidden on tablet and below | Colored dot (green/yellow/grey) + number |

**Row behaviors:**
- Rows below #3 have a 3px colored left border (gold/silver/bronze for ranks 1-3, transparent for rest)
- Hover: subtle white background tint
- Rows animate in with staggered fade-up on scroll (IntersectionObserver)

**Table footer:** "Showing X of Y teams" + "How Rankings Work" link.

**Search behavior:** When the user types in the search box (Section 4), matching rows remain visible, non-matching rows get `display:none`. A "No teams match your search" empty state appears when 0 results.

---

### Section 8: Empty State *(shown only when `entries` list is empty)*
**Type:** Empty/zero state  
**Contains:** Icon, "No Teams Found" heading, message (varies based on whether tier filter is active), "All Tiers" + "Create Team" buttons.

---

### Section 9: Tier System Breakdown
**Type:** Informational / educational  
**Layout:** 6-card grid (6 columns on desktop, 3 on tablet, 2 on mobile)  
**Each card:**
- FontAwesome icon in a colored circular icon box
- Tier name
- CP threshold ("30,000+ CP")
- Hover: card lifts up slightly

**Purpose:** Helps new users understand how the ranking tiers work.

---

### Section 10: CTA / Call to Action
**Type:** Marketing / conversion  
**Contains:**
- "Start Competing" pill badge
- Large bold heading: "Your Name Belongs Up There"
- Short paragraph: explains the pathway (create team → compete → earn CP → reach The Crown)
- Two buttons: **"Create Team"** (primary, gold background) + **"Explore Teams"** (secondary, ghost)

**Design notes:** Gradient edge-glow background on the card. Should feel aspirational and exciting.

---

## 6. Interactions & Animations Summary

| Interaction | Behavior |
|---|---|
| Page load | All sections fade up (+18px Y) with staggered delays |
| Table row scroll-in | Each row fades + slides up when entering viewport (IntersectionObserver, 40ms stagger per row) |
| Activity indicator (high) | Green dot pulses continuously (scale oscillation) |
| Ambient background blobs | Slowly drift and scale in alternating directions (20–25s loop) |
| Game pill hover | Cyan tint background + border change |
| Tier card hover | Card lifts (translateY -3px) |
| Sticky bar scroll | Drop shadow deepens as user scrolls past 60px |
| Search input | Instantly filters all visible rows (podium cards + table rows) client-side |
| Tier select | Submits a form GET request, reloads with `?tier=` param |

---

## 7. Page States

The page has two major states:

1. **Global view** (`/competition/rankings/`)
   - Title: "Global Arena"
   - All games included
   - Game selector: "All" pill is active

2. **Per-game view** (`/competition/rankings/valorant/`)
   - Title: "Valorant Rankings"
   - Only that game's teams shown
   - That game's pill is active in the selector

Both use the **same template** — just different data.

---

## 8. Suggested New Sections to Design (Optional Enhancements)

These do not exist yet but would be valuable additions. You are encouraged to include these in your demo:

### A. Recent Movers / Trending
A compact section showing:
- **Biggest risers** this week: teams that gained the most rank positions (#↑ 12 up)
- **Biggest droppers**: teams that fell the most
- Could be a small horizontal scrollable card strip, or a 2-column "Risers | Fallers" layout

### B. Tier Distribution Chart
A visual breakdown of how many teams are in each tier. Could be:
- A horizontal stacked bar with 6 tier-colored segments
- A simple donut chart
- 6 small pills with count (e.g. "👑 THE CROWN · 3 teams")

### C. Season Banner / Timeline
A banner near the top showing:
- Current season name (e.g. "Season 3 · Spring 2026")
- Season end countdown: "Season ends in 42 days"
- Season rewards teaser: "Top 10 earn exclusive profile frame"

### D. Featured Team Spotlight
A larger promo card (sidebar or banner) highlighting the #1 team or the team with the biggest recent rise. Includes:
- Team banner/logo
- A quote or stat highlight ("Undefeated this month")
- Direct "View Profile" button

### E. Organization Leaderboard (side panel or tab)
A secondary ranking that groups teams by organization and shows the org with the highest combined CP or most teams in top tiers. Could be a collapsible side panel or a separate tab view.

### F. Rank History Sparkline
A tiny sparkline chart per row in the table showing the team's rank over the last 7 days. Just a simple line (green = improving, red = declining). Can be SVG inline.

### G. Filters Enhancement
Expand the filter bar to include:
- **Sort by:** Crown Points · Activity · Rank Change
- **Show:** All teams · Org teams only · Independent only
- **Region:** (if your data supports it)

---

## 9. Page Layout & Spacing Guidelines

**Max content width:** 1400px (centered)  
**Horizontal padding:** 16px mobile, 24px tablet, 32px desktop  
**Section spacing:** ~56px–64px vertical gap between major sections  
**Card border-radius:** 12px–20px (larger = more premium)

### Recommended vertical page order:
```
[Ambient Background — fixed, z:0]
[Hero / Title]
[Stats KPI Row]
───────── [STICKY FILTER BAR] ─────────
[Your Standing (conditional)]
[Season Banner (new)] 
[Trending / Movers (new)]
[Podium — Top 3]
[Full Standings Table]
[Tier Distribution Chart (new)]
[Tier System Breakdown]
[CTA Section]
```

---

## 10. Technical Spec for the HTML Deliverable

Please deliver a **single self-contained `.html` file** with:

- **Tailwind CSS** loaded from CDN: `https://cdn.tailwindcss.com`
- **Google Fonts** (Rajdhani, Inter): loaded in `<head>`
- **FontAwesome 6** from CDN for icons: `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css`
- All CSS in `<style>` blocks inside the HTML file (no separate `.css` file)
- All JS in `<script>` blocks inside the HTML file (no separate `.js` file, no frameworks — vanilla JS only)
- Use **static mock data** — hardcode realistic team names, scores, tiers, etc. in the JS or directly in HTML
- The file must open correctly in a browser without any server (just double-click or open in Chrome)

### Mock Data to Use

To make the demo realistic, use this mock data:

**Teams (use these 15 for the demo):**

| Rank | Team Name | Tag | Tier | CP | Activity | Org |
|---|---|---|---|---|---|---|
| 1 | Nova Sentinels | NSN | THE_CROWN | 34,200 | 94 | Nova Esports |
| 2 | Iron Wolves | IWV | LEGEND | 11,800 | 87 | Iron Corp |
| 3 | Phantom Rising | PHR | LEGEND | 9,100 | 72 | Independent |
| 4 | Apex Vanguard | APX | MASTER | 4,500 | 65 | Apex Academy |
| 5 | Steel Resolve | STR | MASTER | 3,200 | 58 | Steel Alliance |
| 6 | Crimson Order | CRO | MASTER | 2,900 | 44 | Independent |
| 7 | Silent Storm | SLS | ELITE | 1,800 | 88 | Silent Corp |
| 8 | Echo Protocol | EPR | ELITE | 1,450 | 61 | Independent |
| 9 | Dragon Forge | DRG | ELITE | 1,200 | 73 | Dragon Group |
| 10 | Bright Horizon | BRH | ELITE | 980 | 30 | Independent |
| 11 | Ghost Unit | GHU | CHALLENGER | 420 | 92 | Ghost Circuit |
| 12 | Neon Pulse | NEP | CHALLENGER | 310 | 55 | Neon Labs |
| 13 | Orbital Drift | ORB | CHALLENGER | 220 | 41 | Independent |
| 14 | Rust & Ruin | RNR | CHALLENGER | 185 | 18 | Independent |
| 15 | Last Circuit | LCT | ROOKIE | 55 | 5 | Independent |

**Games (use for the game selector pills):**

| ID | Name | Color |
|---|---|---|
| valorant | Valorant | `#FF4655` |
| csgo | CS2 | `#F0B040` |
| lol | League of Legends | `#C89B3C` |
| dota2 | Dota 2 | `#DF2020` |
| rl | Rocket League | `#3B82F6` |

**User Standing (hardcode as if logged in):**
- Best rank: #4
- Teams: "Apex Vanguard" → Rank #4

---

## 11. Things NOT to Change

These elements must remain functionally present (even if visually redesigned):

- The **6 tiers** and their exact names (THE_CROWN, LEGEND, MASTER, ELITE, CHALLENGER, ROOKIE)
- The **CP (Crown Points)** scoring system name
- The **activity score** concept (0–100)
- The **game filter pills** concept
- The **tier filter dropdown** concept
- The **live search** input
- The **podium top-3** section
- The **Your Standing** personalized band
- The **Tier System breakdown** at the bottom
- The **Create Team / Explore Teams** CTA

---

## 12. Inspiration References

For visual inspiration, look at:
- Riot Games (Valorant ranked profile pages)
- Liquipedia.net (match/standings tables)
- HLTV.org (CS2 world rankings)
- FIFA Ultimate Team rank pages
- Flashpoint esports platform
- Faceit leaderboards

**Key visual patterns to consider:**
- Particle/smoke background effects on hero
- Scanline overlays for a tech-game feel  
- Typing-effect on rank numbers (count up animation)
- Glitch animations on tier badge changes
- Subtle hexagonal grid patterns in backgrounds
- Neon stroke text for the page title

---

## 13. Questions to Answer in Your Design

Please communicate clearly in your design how you handle:

1. **What happens on mobile to the podium?** — Stack vertically, or a horizontal scroll strip?
2. **How do you show the top 3 as clearly different** from ranks 4–15?
3. **How do you integrate the new sections** (Rising/Trending, Tier Distribution)?
4. **What hover states** exist for table rows?
5. **How does the sticky filter bar look** when scrolled vs at the top?
6. **How does the empty state look** when search finds no results?

---

*Document prepared by: DeltaCrown Dev Team | March 2026*  
*Questions? Contact the lead developer before starting the design.*
