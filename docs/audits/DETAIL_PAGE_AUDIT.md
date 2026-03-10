# Tournament Detail Page — Audit, Suggestions & Modernization Report

> **Date:** March 2026  
> **Scope:** `templates/tournaments/detailPages/detail.html` + `apps/tournaments/views/detail.py`  
> **Status:** Post-redesign of Participants & Bracket tabs

---

## 1. Current Architecture

### Template Structure (~1,800 lines monolith)

| Section | Lines | Description |
|---------|-------|-------------|
| Hero / Banner | ~180 | Animated banner, status badges, stats row, CTAs |
| Sticky Tab Nav | ~60 | 7 tabs with counts, right-side CTA + countdown |
| Overview Tab | ~250 | Timeline, config grid, briefing, prize podium, logistics |
| Participants Tab | ~90 | Compact card grid (redesigned) |
| Matches Tab | ~130 | Live-now cards + all-matches list |
| Bracket Tab | ~60 | Interactive bracket viewport (redesigned) |
| Standings Tab | ~80 | Sortable table with advance highlighting |
| Streams Tab | ~60 | Featured embed + additional cards |
| Rules Tab | ~60 | Collapsible rulebook + T&C + PDF links |
| Right Sidebar | ~180 | Registration card, game info, organizer, feature flags |
| Inline CSS | ~420 | Theme vars, orbs, tabs, bracket, scrollbars |
| Inline JS | ~230 | Tab switching, search, bracket renderer, zoom |

### View Structure (`TournamentDetailView`, ~1,200 lines)

- Phase-based routing (`PHASE_TEMPLATES`) with fallback to monolith
- Context methods: `_get_participants_context`, `_get_matches_context`, `_get_standings_context`, etc.
- Bracket data serialized server-side to `window.__detailBracketData`

---

## 2. What's Working Well

| Strength | Details |
|----------|---------|
| **Dark Esports Aesthetic** | True-black (#020204) base, glass-morphism cards, game-color accents — feels premium |
| **Game-Dynamic Theming** | CSS variables (`--game-color`, `--game-color-secondary`) per game, with 8 game overrides in external CSS |
| **Hero Section** | Animated banner pan (25s), ambient orbs, grid overlay, clear status badges — immediately communicates tournament state |
| **Visual Hierarchy** | Large prize pool, prominent date/team-size stats, color-coded statuses |
| **Responsive Layout** | 12-col grid, sidebar collapses on mobile, sticky nav + mobile CTA bar |
| **Participants (New)** | Compact 5-col card grid, search filter, status dots, slots progress bar — clean and scalable |
| **Bracket (New)** | Team logos, SVG connectors, zoom controls, double-elim UB/LB/GF sections — esports-standard |

---

## 3. Issues & Technical Debt

### 3.1 Architecture Issues

| Issue | Impact | Priority |
|-------|--------|----------|
| **Monolithic Template** | ~1,800 lines in one file — hard to maintain, review, or reuse | 🔴 High |
| **Monolithic View** | ~1,200 lines with 8+ context methods — complex class | 🟡 Medium |
| **Inline CSS/JS** | ~650 lines of inline code — no caching, no linting, no bundling | 🟡 Medium |
| **Global JS State** | `window.__detailBracketData` pollutes global scope | 🟢 Low |
| **Repeated Badge Logic** | `{% if tournament.status %}` checked 9+ times across sections | 🟡 Medium |

### 3.2 UX/Design Issues

| Issue | Details | Priority |
|-------|---------|----------|
| **No Loading States** | Content appears all at once — no skeletons or shimmer effects | 🟡 Medium |
| **No Real-Time Updates** | Live tournaments show static data until page refresh (Hub has WebSockets, detail page does not) | 🔴 High |
| **Mobile Bracket** | Bracket forces horizontal scroll; cramped on phones | 🟡 Medium |
| **Alert-Based Actions** | Some actions use `alert()` — should use toast notifications | 🟡 Medium |
| **No Blur-Up Images** | Banner and avatars load without placeholders — can flash on slow connections | 🟢 Low |
| **Hardcoded Prize Positions** | Podium assumes exactly 3 places — breaks for 1st-only or 4+ place prizes | 🟡 Medium |

### 3.3 Accessibility Issues

| Issue | WCAG Level | Priority |
|-------|------------|----------|
| **No `prefers-reduced-motion`** | Animations always run; impacts vestibular sensitivities | 🔴 High |
| **Color-Only Status Indicators** | Some statuses rely only on color (green dot = checked in) — needs text fallback | 🟡 Medium |
| **Limited ARIA** | Tabs lack `role="tablist"` / `aria-selected`; bracket has no screen-reader narrative | 🟡 Medium |
| **Keyboard Navigation** | Tab switching not keyboard-accessible; bracket zoom has no keyboard shortcuts | 🟡 Medium |
| **No Print Styles** | @media print not defined — players can't print brackets/schedules | 🟢 Low |

### 3.4 Performance Concerns

| Issue | Details |
|-------|---------|
| **Large DOM** | ~1,800 lines rendered even for hidden tabs — could lazy-load |
| **Inline CSS Blocks Caching** | 420+ lines of CSS embedded in HTML — never cached by browser |
| **CDN Dependencies** | Alpine.js + Lucide loaded from CDN — single points of failure |
| **Banner Animation** | Continuous 25s CSS animation may drain battery on mobile |
| **No Image Optimization** | Avatars/logos served at original size — should use responsive `srcset` |

---

## 4. Modernization Suggestions

### 4.1 Template Decomposition (High Impact)

Split the monolith into partials:

```
templates/tournaments/detailPages/
├── detail.html              (shell + tab nav + sidebar)
├── _hero.html               (banner, stats row, CTAs)
├── _tab_overview.html       (timeline, config, briefing, prizes)
├── _tab_participants.html   (card grid + search)
├── _tab_matches.html        (live cards + all matches)
├── _tab_bracket.html        (bracket viewport + zoom)
├── _tab_standings.html      (standings table)
├── _tab_streams.html        (embeds)
├── _tab_rules.html          (rulebook + T&C)
└── _sidebar.html            (registration, game info, organizer)
```

**Benefit:** Each partial is <200 lines, independently reviewed, version-controlled per-section.

### 4.2 Hero Section Enhancements

| Enhancement | Description |
|-------------|-------------|
| **Countdown Timer** | Live countdown to registration close or match start — already have the data, just needs JS interval |
| **Social Proof Bar** | Show "124 teams registered · 8.2K viewers · Trending #3" below stats |
| **Share Preview Card** | Auto-generate OpenGraph image from tournament data for link previews |
| **Parallax Depth** | Subtle parallax on scroll (banner moves slower than content) |
| **Tournament Trailer** | Optional embedded video trailer in hero (auto-muted) for premium events |

### 4.3 Overview Tab Modernization

| Enhancement | Description |
|-------------|-------------|
| **Interactive Timeline** | Replace static 5-node bar with animated timeline that highlights current phase |
| **Live Ticker** | Scrolling text bar showing recent results: "Team Alpha beat Team Beta 13-7 · Round 2 starting..." |
| **Dynamic Prize Pool** | If crowd-funded, show a filling animation + recent contributors |
| **Map Pool Display** | Visual map preview grid (map images + veto status) — large impact for FPS games |
| **Quick Match Previews** | Hover on upcoming matches in overview → tooltip with team logos + head-to-head stats |

### 4.4 Matches Tab Improvements

| Enhancement | Description |
|-------------|-------------|
| **Match Cards Redesign** | Follow the compact match result cards from the Hub page — scores in center, team logos flanking |
| **Round Grouping** | Group matches by round with collapsible headers: "Round 1 (8 matches)" |
| **Head-to-Head Flyout** | Click a match → slide-in panel showing team histories, past encounters |
| **Live Score Animation** | Numbers roll-up animation when scores change (WebSocket-driven) |

### 4.5 Standings Tab Improvements

| Enhancement | Description |
|-------------|-------------|
| **Movement Arrows** | Green/red arrows showing rank change since last round |
| **Row Hover Expansion** | Hover a row → show mini match history (W-L-W-W-L as dots) |
| **Advance Zone Highlighting** | Top N rows with green background ("Advancing"), bottom N with red ("Eliminated") |
| **Export to Image** | "Share Standings" button → generate PNG | 

### 4.6 Real-Time Features (High Impact)

The Hub page already has WebSocket-driven bracket updates. Mirror this for the detail page:

- **Live Score Updates** — Matches tab auto-updates without refresh
- **Bracket Progress** — Completed matches animate on bracket in real-time
- **Participant Activity** — "Team X just checked in" notifications
- **Viewer Count** — Live viewer count on streams tab

Implementation: Reuse Hub's `tournament_event` dispatcher from `apps/tournaments/consumers.py`.

### 4.7 Mobile-First Polish

| Area | Current | Proposed |
|------|---------|----------|
| **Bracket** | Horizontal scroll, cramped | Vertical layout on <768px, full-width match cards stacked by round |
| **Hero** | Text overflow on small screens | Truncate description, stack stats vertically |
| **Tab Nav** | Scrollable but unclear | Add scroll indicators (fade edges) + swipe gesture support |
| **Sidebar** | Hidden on mobile | Sticky bottom sheet (slide up) with registration CTA |
| **Touch Targets** | Some links <44px | Ensure all interactive elements ≥ 44×44px |

### 4.8 Micro-Interactions & Polish

| Interaction | Description |
|-------------|-------------|
| **Tab Switch Animation** | Slide content left/right on tab change (not just show/hide) |
| **Card Hover Effects** | Subtle lift + glow on participant/match cards (3D transform) |
| **Score Reveal** | When match completes, score animates in with a flash |
| **Skeleton Loaders** | Shimmer placeholders while content loads |
| **Toast Notifications** | Replace `alert()` with slide-in toasts (bottom-right) |
| **Confetti Effect** | On tournament winner announcement — subtle particle burst |
| **Scroll Progress** | Thin game-color progress bar at top of page |
| **Section Reveal** | Subtle fade-up as sections scroll into viewport (IntersectionObserver) |

### 4.9 CSS Architecture Cleanup

**Current:** 420 lines inline + external `tournament-detail.css` + Tailwind + tournaments.css

**Proposed:**
1. Extract all inline `<style>` to `static/tournaments/css/detail-page.css`
2. Consolidate glass effect variants into 2 Tailwind utilities: `glass-card`, `glass-card-light`
3. Replace magic numbers with CSS variables: `--hero-height`, `--nav-offset`, `--card-radius`
4. Add `@media (prefers-reduced-motion: reduce)` block disabling all animations
5. Add `@media print` block for clean bracket/standings printout

### 4.10 JS Architecture Cleanup

**Current:** ~230 lines inline in `<script>` tags

**Proposed:**
1. Extract to `static/tournaments/js/detail-page.js` (cached, lintable)
2. Wrap in IIFE or module — eliminate `window.__detailBracketData` global
3. Use `data-*` attributes for config instead of inline template tags
4. Add error boundaries to bracket renderer
5. Add keyboard shortcuts: `1-7` for tab switching, `+/-` for bracket zoom

---

## 5. Comparison with Industry Leaders

| Feature | DeltaCrown (Current) | FACEIT | Battlefy | Start.gg |
|---------|---------------------|--------|----------|-----------|
| Real-time scores | ❌ Static | ✅ WebSocket | ✅ Polling | ✅ WebSocket |
| Interactive bracket | ✅ Zoom + SVG | ✅ Full D3 | ✅ Canvas | ✅ React component |
| Team profiles flyout | ❌ | ✅ | ❌ | ✅ |
| Dark mode | ✅ Always dark | ✅ Toggle | ❌ Light only | ✅ Toggle |
| Mobile bracket | ⚠️ H-scroll | ✅ Vertical | ⚠️ Pinch zoom | ✅ Accordion |
| Game theming | ✅ Per-game colors | ✅ Per-game | ❌ Generic | ⚠️ Partial |
| Skeleton loaders | ❌ | ✅ | ❌ | ✅ |
| Live viewer count | ❌ | ✅ | ❌ | ❌ |
| Social share preview | ❌ | ✅ OG images | ✅ | ✅ |
| Print support | ❌ | ❌ | ✅ PDF export | ❌ |

**DeltaCrown's competitive advantage:** Game-dynamic theming is better than most competitors. The dark aesthetic + glass-morphism is unique in the space.

**Biggest gap vs competitors:** Lack of real-time updates on the public detail page (Hub has it, detail page doesn't).

---

## 6. Recommended Roadmap

### Phase 1 — Quick Wins (Low effort, high impact)

- [ ] Extract inline CSS to `detail-page.css`
- [ ] Add `prefers-reduced-motion` media query
- [ ] Add ARIA roles to tabs (`role="tablist"`, `aria-selected`)
- [ ] Replace `alert()` with toast notifications
- [ ] Add scroll fade indicators to mobile tab nav

### Phase 2 — Template Decomposition

- [ ] Split `detail.html` into 10 partials (see 4.1)
- [ ] Extract inline JS to `detail-page.js`
- [ ] Consolidate CSS glass variants
- [ ] Add skeleton loader placeholders

### Phase 3 — Real-Time & Interaction

- [ ] Connect detail page to WebSocket (reuse Hub's `tournament_event`)
- [ ] Add live score animations on matches + bracket
- [ ] Implement tab slide transitions
- [ ] Add card hover micro-interactions

### Phase 4 — Content Enhancements

- [ ] Interactive timeline for overview tab
- [ ] Map pool display for FPS tournaments
- [ ] Head-to-head flyout on match click
- [ ] Standings movement arrows + row expansion
- [ ] Social share preview (OpenGraph image generation)

### Phase 5 — Mobile Excellence

- [ ] Vertical bracket layout for <768px
- [ ] Bottom sheet registration CTA
- [ ] Swipe gesture for tab navigation
- [ ] Touch target audit (≥ 44×44px)

---

## 7. Summary

The detail page has a **strong visual foundation** — the dark esports aesthetic with game-dynamic theming puts it ahead of most competitors visually. The recent Participants and Bracket redesigns bring those tabs up to Hub-quality standards.

**Top 3 priorities for maximum impact:**

1. **Real-time updates** via WebSocket — transforms the detail page from a static info page to a live experience
2. **Template decomposition** — unblocks team velocity and enables component-level iteration
3. **Accessibility pass** — `prefers-reduced-motion`, ARIA roles, keyboard nav — legally and ethically necessary

The page doesn't need a full rewrite. The design language is modern and consistent. Focus effort on **architecture cleanup** and **live features** rather than visual overhaul.
