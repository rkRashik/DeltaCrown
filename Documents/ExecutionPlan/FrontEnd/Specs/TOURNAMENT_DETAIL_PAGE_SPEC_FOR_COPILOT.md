# Tournament Detail Page – Frontend Spec (for Copilot)

This spec defines the **Tournament Detail Page** (`/tournaments/<slug>/`) as a **modular, esports-grade, stateful experience**.

Copilot: use this as your guide when updating templates, CSS, and JS.

---

## 0. Frontend Architecture & File Structure

### 0.1 Templates (HTML)

Use a **modular Django template structure** for the tournament detail page:

* `apps/tournaments/templates/tournaments/detail.html`

  * Main layout, extends global base.
  * Includes partials/blocks:

* Partials (can be `include`d into `detail.html`):

  * `tournaments/partials/detail/hero.html`
  * `tournaments/partials/detail/meta_strip.html`
  * `tournaments/partials/detail/tab_nav.html`
  * `tournaments/partials/detail/tab_overview.html`
  * `tournaments/partials/detail/tab_rules.html`
  * `tournaments/partials/detail/tab_prizes.html`
  * `tournaments/partials/detail/tab_participants.html`
  * `tournaments/partials/detail/tab_bracket.html`
  * `tournaments/partials/detail/tab_matches.html`
  * `tournaments/partials/detail/tab_standings.html`
  * `tournaments/partials/detail/tab_streams_media.html`
  * `tournaments/partials/detail/tab_challenges_fanvoting.html`
  * `tournaments/partials/detail/sidebar.html`

Keep each partial **focused on one logical area**.

### 0.2 Static Files (CSS, JS)

Organize assets under the tournaments app:

* CSS:

  * `apps/tournaments/static/tournaments/css/detail.css`

    * Layout, spacing, cards, tab layout, sidebar, basic responsive.
  * `apps/tournaments/static/tournaments/css/detail_theme.css`

    * **Esports themes & game-based color variables**.
  * (Optional) `apps/tournaments/static/tournaments/css/detail_animations.css`

    * Transitions, keyframes, hover effects.

* JS:

  * `apps/tournaments/static/tournaments/js/detail.js`

    * Handles tab switching, minor interactivity.
    * Applies theme based on game slug/data attributes.
    * Handles animated counters (prize pool, countdown), etc.
  * `apps/tournaments/static/tournaments/js/detail_live.js`

    * Handles WebSocket/HTMX polling for live parts (match list, announcements) if needed.

**Important style guidance:**

* Use **CSS variables** for theming (e.g. `--accent`, `--accent-soft`, `--bg-elevated`, `--text-primary`).
* Transitions:

  * Use smooth `transition: all 180ms ease-out;` (or similar) for hover/active states.
* Animations:

  * Subtle, not obnoxious. Think “premium esports broadcast”, not flashing casino.

---

## 1. State & Role Matrix (High-Level)

The page must adapt to **tournament status** + **user role**.

### 1.1 Tournament Status (from backend)

Key statuses (simplified for UI):

* `draft` / `pending_approval` → not public
* `published`
* `registration_open`
* `registration_closed`
* `live`
* `completed`
* `cancelled`
* `archived`

### 1.2 User Roles

* Guest (not logged in)
* Logged-in, not registered
* Registered:

  * Pending (e.g. payment submitted)
  * Confirmed, not checked-in
  * Confirmed & checked-in
* Organizer / Manager of this tournament
* Admin (superuser) – can mostly share organizer view

### 1.3 UX Modes (matrix summary)

You don’t need a full table in UI, but logic should behave like:

* **Guest / not registered**

  * If `published` or `registration_open`: CTA = “Login to Register” / “Register”.
* **Logged-in, not registered**

  * If `registration_open`: CTA = “Register Now”.
* **Registered (confirmed)**

  * Pre-start: CTA = “Enter Tournament Room”.
  * During live: CTA = “Go to Tournament Room” + “View Your Next Match”.
* **Organizer**

  * Always show an **Organizer Tools strip**; primary CTA: “Organizer Console” / “Open Lobby”.
* **Completed**

  * CTA = “View Results” and “View Bracket”.

All these are driven by existing context / status fields; you already have a `cta_state`, `cta_label`, etc. from the backend – use them, don’t reinvent.

---

## 2. Game-Themed Esports Skinning

### 2.1 Theme System

Use **CSS variables + a data attribute** on the `<body>` or on the root detail container:

```html
<body data-game-slug="{{ tournament.game.slug }}">
```

or

```html
<div class="tournament-detail" data-game-slug="{{ tournament.game.slug }}">
```

In `detail_theme.css`, define themes like:

```css
[data-game-slug="valorant"] {
  --accent: #ff4655;
  --accent-soft: #ff9aa4;
  --bg-elevated: #111823;
  --bg-surface: #0b1018;
}

[data-game-slug="efootball"] {
  --accent: #00b0ff;
  --accent-soft: #6fd0ff;
  --bg-elevated: #07101f;
  --bg-surface: #050b14;
}

/* etc for other games */
```

All main components (buttons, tabs, chips, highlights, progress bars) should use these variables.

### 2.2 Esports Vibe

Visual language:

* Dark backgrounds, vivid accent colors.
* Neon/glow “edges” on hover (subtle).
* Rounded cards, but not too bubbly – more “panel” than “pill”.
* Clean typography hierarchy:

  * Big bold H1 for tournament name.
  * All-caps small labels for metadata (game, region, format).
* Use layered backgrounds:

  * Gradient overlay, light diagonal lines, or faint noise texture.

Animations:

* Use **scale + shadow** on hover for cards.
* Smooth **fade/slide-in** on scroll (can be purely CSS with `animation` triggered by a class; JS can add the class on intersection if you want).

---

## 3. Page Layout – High-Level Wireframe

### 3.1 Overall Layout (Desktop)

Mental wireframe:

```text
[Global Navbar]

[HERO SECTION – full width]
  [Left: Banner + Title + Status + Game/Type]
  [Right: CTA + Entry Fee + Waiver Info + Countdown]

[Meta Strip – full width horizontal info bar]

[Main Content Wrapper]
  [Left: Tabs + Tab Content]
  [Right: Sidebar (user context, lobby, sponsors, social)]

[Footer]
```

On mobile: stack hero + meta strip, then tabs, then content, sidebar content moves below or above depending on priority.

---

## 4. Hero Section & Meta Strip

### 4.1 Hero Section

**Purpose:** Immediate impact, state awareness, primary action.

**Backend data used:**

* `tournament.name`, `subtitle`, `game.name`, `game.slug`, `game.icon`
* `tournament.banner_image` / `thumbnail_image`
* `tournament.status` + `get_status_display()`
* `tournament.registration_start`, `registration_end`
* `tournament.tournament_start`, `tournament.tournament_end`
* `has_entry_fee`, `entry_fee_amount`, `entry_fee_currency`, `entry_fee_deltacoin`
* `enable_fee_waiver`, `fee_waiver_top_n_teams`, (and whether the user’s team is eligible)
* `cta_state`, `cta_label`, `cta_disabled`, `cta_reason`
* For confirmed participants: check-in status & next match (if easily accessible)

**Wireframe (Desktop):**

```text
-----------------------------------------------------------
| HERO BACKGROUND (game-themed, banner image + overlay)  |
|                                                        |
| [Left 60%]                                             |
|  [Game badge + status pill + region chip]             |
|  [Tournament Title (H1)]                              |
|  [Subtitle/Tagline]                                   |
|  [Small info row: Format · Participation Type · Game] |
|                                                        |
| [Right 40%]                                            |
|  [Primary CTA button]                                 |
|   - text from cta_label                               |
|   - style changes by cta_state                        |
|  [Mini note if disabled: cta_reason]                  |
|                                                        |
|  [Entry fee block]                                    |
|   - “Entry Fee: 500 BDT + 100 ΔCoin”                  |
|                                                        |
|  [Fee waiver block (if enabled)]                      |
|   - “Top 8 ranked teams enter free.”                  |
|   - If user’s team in top N: “Your team qualifies ✅” |
|                                                        |
|  [Countdown chip]                                     |
|   - Before start: “Starts in 02d 13h 25m”             |
|   - During: “Live now · Round 2”                     |
|   - After: “Ended on Nov 21, 2025”                    |
-----------------------------------------------------------
```

Hero behavior by role:

* Guest/unregistered: CTA = “Login to Register” / “Register Now”.
* Registered (confirmed) pre-start: CTA = “Enter Tournament Room”.
* Registered during: CTA = “Go to Tournament Room” + maybe a secondary “View Next Match”.
* Organizer: CTA = “Organizer Console” or “Open Organizer Dashboard”.

### 4.2 Meta Strip

**Purpose:** Quick skim bar under hero.

Fields:

* Format (`single-elimination`, etc.)
* Participation type (team/solo)
* Max/min participants, slots filled (`slots_filled`, `slots_total`, `slots_percentage`)
* Prize pool and DeltaCoin
* Key dates (registration closes, event date)
* Live matches count (if `status=live`)

**Wireframe:**

```text
[Format & type] | [Prize pool + ΔCoin] | [Dates] | [Slots bar] | [Live status]
```

Visual idea:

* Each item as a pill/chip.
* Slots bar: progress bar with “19 / 32 slots filled”.

---

## 5. Tab Navigation

Tabs:

* Overview
* Rules
* Prizes
* Participants
* Bracket
* Matches
* Standings
* Streams & Media
* Challenges & Fan Voting (only if enabled)

Behavior:

* Sticky under meta strip when scrolling.
* On desktop: horizontal bar; on mobile: scrollable horizontal tabs or dropdown.

Implementation:

* Add data attribute or classes for active tab.
* JS (`detail.js`) handles switching by toggling `is-active` class and showing corresponding content panel.

---

## 6. Overview Tab

### 6.1 Purpose

Tell the story of the tournament and show the **journey** for this user.

### 6.2 Content Blocks

1. **Player Journey Timeline (top)**
   Visual stepper:

   ```text
   [Discover] → [Register] → [Check-In] → [Play] → [Finals] → [Rewards]
   ```

   * Highlight current step based on:

     * `status`
     * whether user is registered / checked-in / tournament completed.

2. **Description & Story**

   * Render `tournament.description` with headings, bullets, etc.

3. **Sponsor Highlight (if sponsors list not empty)**

   * “Presented by [LOGO]”
   * Show sponsor logos in a horizontal strip.

4. **Game & Format Summary Cards**

   * Game info (mode, platform).
   * Format (e.g. Single Elimination).
   * Participation type (solo/team).
   * Region/server.

5. **Custom Fields Summary**

   * If custom fields include important info (like Discord, server, etc.), show a compact list of “Requirements & Important Fields”.

### 6.3 Wireframe

```text
[Journey Stepper]

[Description card]

[If sponsored]
  [Sponsor card strip]

[Info cards grid]
  [Game] [Format] [Participation] [Region]

[Custom requirements card]
```

---

## 7. Rules Tab (Text + PDF + External)

### 7.1 Logic

Display in this priority:

1. If `rules_text` exists → show as main formatted text.
2. If `rules_pdf` exists → show embedded PDF viewer under a “Full Rulebook (PDF)” section.
3. If no PDF but `lobby.rules_url` exists → show external link button.
4. If neither → “Rules will be announced soon.”

If both text & PDF exist:

* Show “Primary Rules (Summary)” from text first.
* Then “Full Rulebook (PDF)” with inline preview.

### 7.2 Wireframe

```text
[Rules Tab]

[Primary Rules (if rules_text)]
  - formatted paragraphs, numbered lists, warning callouts

[Full Rulebook (if rules_pdf)]
  [PDF viewer frame] + Download button

[External Rules Link (if lobby.rules_url)]
  [Button: View Extended Rules Document]
```

---

## 8. Prizes Tab

### 8.1 Data

* `prize_pool`, `prize_currency`, `prize_deltacoin`
* `prize_distribution` JSON, parsed into placements.

### 8.2 Layout

1. **Total Prize Banner**

   * “🏆 1000 BDT + 100 ΔCoin Total Prize Pool”
2. **Podium**

   * 1st, 2nd, 3rd as three columns.
3. **Full Breakdown Table/List**

   * Each placement row:

     * Place badge
     * BDT amount
     * ΔCoin amount
     * Percentage, if available.

Animations:

* On load, animate podium bars “growing”.
* Use number counters (JS) for prize total, if desired.

### 8.3 Wireframe

```text
[Total prize banner]

[Podium row]
  [1st]   [2nd]   [3rd]

[Detailed list]
  1st – 600 BDT + 50 ΔCoin
  2nd – 300 BDT + 30 ΔCoin
  3rd – 100 BDT + 20 ΔCoin
  ...

[DeltaCoin info note]
```

---

## 9. Participants Tab (Team App Integration)

### 9.1 Purpose

Show all registered teams/players, with ranking info and fee waiver context.

### 9.2 Layout

Two modes:

* Team tournaments:

  * Cards with team logo, name, tag, ranking badge, “View Team” link.
* Solo tournaments:

  * List with avatar, username, ranking if available.

Fee waiver banner at top if `enable_fee_waiver`:

* “Top N ranked teams get free entry.”
* If user’s team eligible: small “Your team is eligible ✅”.

### 9.3 Wireframe

```text
[Fee waiver banner (if enabled)]

[Filter bar: All / Teams / My team / Search]

[Grid of team cards]
  [Logo] [Team Name (TAG)]
  [Rank badge] [Ranking points]
  [View Team button]

(For solo: similar list with avatars)
```

---

## 10. Bracket Tab

### 10.1 Purpose

Interactive bracket view, highlights path for players, read-only for spectators.

### 10.2 Content

* If bracket not generated yet: “Bracket will be generated soon.”
* Once generated:

  * Visualization of rounds and matches (use existing bracket JSON if available).
  * Each node shows participant names and seeds.

If dynamic seeding / ranking seeding enabled:

* Show a small info banner:

  * “Seeding is based on team rankings.”

### 10.3 Wireframe

```text
[If no bracket]
  "Bracket will be available after seeding."

[Bracket canvas]
  Round 1: [M1] [M2] ...
  Round 2: [M3] [M4] ...
  Finals: [M5]

[Legend / Info banner]
```

---

## 11. Matches Tab

### 11.1 Purpose

List matches with filters; highlight “My matches” for participants.

### 11.2 Layout

* Filter bar:

  * “All / My matches / Upcoming / Live / Completed”
* List of match cards:

  * Round, match number
  * Participants
  * Time / status
  * Result if completed
  * For players: “View Match Room” link
  * For spectators: “Watch” if `stream_url` exists.

### 11.3 Wireframe

```text
[Filter bar]

[Match card]
  [Round label]   [Status chip]
  [Participant 1 vs Participant 2]
  [Time or result]
  [Buttons: View details / Watch]
```

---

## 12. Standings Tab

* During group/league formats: standings table (points, W-L, etc.).
* After completion:

  * Final placements, with winners highlighted.
* Use the available TournamentResult + standings calculation logic.

Wireframe:

```text
[If completed]
  [Winner card – big]

[Standings table]
  Pos | Team/Player | W | L | Pts | etc.
```

---

## 13. Streams & Media Tab

* If `stream_youtube_url` / `stream_twitch_url`:

  * Embed main stream player.
* Grid of VODs/highlights if you have links or future plan.
* Link to organizer’s YouTube/Twitch from organizer/profile info as secondary.

Wireframe:

```text
[Main stream embed]

[Highlight clips grid]  (optional)

[Follow organizer / social links]
```

---

## 14. Challenges & Fan Voting Tab (Feature Flags)

Only show if respective toggles are enabled.

* Challenges:

  * Cards like “Most kills Day 1”, “Clutch King”.
* Fan voting:

  * Poll-style UI: “Who will win the finals?”, with progress bars and vote button.

If feature disabled: tab hidden entirely.

---

## 15. Sidebar

### 15.1 Blocks

From top to bottom:

1. **User Context Card**

   * Guest: “You’re viewing as a spectator” + Login/Register CTAs.
   * Registered: “You’re playing as [Team/Username]”, registration status, fee/payment status.
   * Organizer: “You’re managing this tournament” + Organizer actions.

2. **Tournament Room / Lobby Card**

   * If user is a confirmed participant OR organizer:

     * Button: “Enter Tournament Room”.
     * Check-in status / countdown.
   * If not eligible:

     * Text: “Tournament Room is available to registered participants only.”

3. **Organizer Info**

   * Organizer avatar, name, link to profile.

4. **Sponsor Block (if sponsors exist)**

   * Sponsor logos and link(s).

5. **Social / External Links**

   * Discord server link (`lobby.discord_server_url`).
   * Stream channel links (YouTube/Twitch).

6. **Quick Status Widgets**

   * Registration progress (“19/32 slots filled”).
   * Live matches count (when live).
   * Winners summary (after completion).

---

## 16. Animations & Micro-Interactions

Guidelines:

* Use **CSS transitions**:

  * Hover on cards/buttons: small scale up, drop shadow, accent glow.
* Journey stepper:

  * When page loads, steps fade in left-to-right.
* Prize podium:

  * Bars animate from 0 height to target height.
* Countdown:

  * Use JS to tick every second; smooth digits transition.

Avoid:

* Excessive flashing/blinking.
* Animations that interfere with readability.

---

## 17. Implementation Notes for Copilot

When you (Copilot) implement this:

1. **Respect existing backend contexts**

   * Use data already provided in `TournamentDetailView` and related models whenever possible.
2. **Add new HTML in modular partials**

   * Don’t dump everything into one massive template.
3. **Use CSS variables + `[data-game-slug]` for themes**

   * Do NOT hardcode colors directly into every component; rely on variables.
4. **Use unobtrusive JS**

   * Tab switching, counters, theme initialization, and live updates should be in `detail.js` / `detail_live.js`.
5. **Honor feature toggles**

   * Conditionals in templates based on boolean flags:

     * `enable_fee_waiver`, `enable_dynamic_seeding`, `enable_live_updates`, `enable_certificates`, `enable_challenges`, `enable_fan_voting`.

---
