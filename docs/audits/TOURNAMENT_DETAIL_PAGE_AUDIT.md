# Tournament Detail Page — Comprehensive Audit Report

## Executive Summary

DeltaCrown's tournament detail page (`templates/tournaments/detailPages/detail.html`, ~1,692 lines) is a visually ambitious, glassmorphism-heavy single-page design built entirely with Django templates, Tailwind CSS (CDN), and vanilla JavaScript. The page demonstrates strong visual identity — dynamic game-color theming, ambient glow orbs, noise textures, and a rich hero section — but has significant functional gaps when measured against the industry leaders (Toornament, Battlefy, FACEIT, Start.gg).

**Key Strengths:**
- Exceptional visual design with game-dynamic CSS variables (`--game-color`, `--game-color-secondary`)
- Comprehensive status system covering 8+ tournament states with unique visual treatments
- Well-structured registration flow with entry fee, DeltaCoin, and fee-waiver support
- Multi-stage format support (group stage → knockout)
- Streams tab with embedded player and live indicators
- Mobile sticky CTA bar for registration
- Feature flags sidebar (check-in, live updates, certificates, seeding, challenges, fan voting)
- Phase timeline with animated progress bar

**Key Weaknesses:**
- No live stream embed on the overview/main tab (buried in a tab)
- No social sharing beyond a basic clipboard copy
- No follow/favorite functionality
- No countdown timer to tournament start
- No interactive bracket visualization
- No sponsor section
- Missing `og:description`, `og:url`, `og:image` overrides for tournament-specific sharing
- No structured data (JSON-LD) for events
- No accessibility considerations (ARIA labels, focus management, screen reader support)
- All CSS is inline in the template (~160 lines of `<style>`) rather than in an external stylesheet

---

## Current Feature Inventory

### 1. Hero Section (Lines 161–310)
| Feature | Details |
|---|---|
| Banner image | Full-bleed with `cover`, slow pan animation (25s), brightness/saturate/contrast filters, HiDPI overrides |
| Grid lines overlay | Subtle 40px grid with mask-image fade |
| Gradient overlay | Multi-layer radial + linear gradient for text readability |
| Status badges | 8 distinct states: Live, Registration Open, Registration Closed, Completed, Cancelled, Archived, Pending Approval, Published, Draft |
| Game badge | Dynamic game-color styled with icon |
| Platform badge | PC / Mobile / PS5 / Xbox with context-appropriate icon |
| Mode badge | LAN/Hybrid only (online hidden) |
| Official badge | Gold "Official" badge for platform-sanctioned events |
| Participation type badge | Solo / Team indicator |
| Tournament title | Uppercase, responsive 4xl→8xl font with drop shadow |
| Short description | Truncated to 30 words with game-color left border |
| Prize pool stat | Gold glow with BDT currency (৳) |
| Start date stat | Month/day with time |
| Team size stat | Conditional on team-mode tournaments |
| Organizer stat | Clickable with underline hover effect |
| Organizer tools | Manage Tournament + Hub buttons (organizer-only) |
| Action buttons | Share (clipboard), Stream link, Report |

### 2. Sticky Tab Navigation (Lines 313–406)
| Feature | Details |
|---|---|
| Tabs | Overview, Participants (with count badge), Matches (with count), Bracket, Standings, Streams (conditional, with live dot), Rules |
| Sticky behavior | `position: sticky; top: 64px` with blur backdrop |
| Registration countdown | Shown in nav bar when reg is open |
| Quick register CTA | Shown on desktop in the nav bar |

### 3. Overview Tab (Lines 420–1005)
| Section | Details |
|---|---|
| Phase Timeline | 5-step progress: Published → Registration → Check-In → Live → Complete; animated gradient bar; active/completed/pending states |
| Match Configuration | 4-column grid: Format, Match Type, Game, Capacity; secondary row: Scoring, Duration, Draws, Check-In |
| Event Briefing | Rich HTML description with read more/less toggle (collapsed at 180px) |
| Prize Pool Breakdown | Podium layout (1st/2nd/3rd) with champion trophy icon, gold glow; DeltaCoin bonus display |
| Entry & Logistics | Registration fee card (BDT/DeltaCoin/Free), payment methods (bKash, Nagad, Rocket, Bank Transfer, DeltaCoin), team entry info, check-in info, fee waiver info |
| Register CTA card | Status-aware: register/registered/closed states; date timeline (reg opens, closes, starts) |
| Security badge | "DeltaCrown Secured" with escrow/fair-play messaging |
| Venue section | Conditional (LAN/Hybrid only): venue name, city, address, Google Maps link |
| Multi-stage info | Group Stage + Knockout cards with active indicator; group standings summary with advancers |
| Announcements | Pinned support, author + timestamp |

### 4. Participants Tab (Lines 1007–1105)
| Feature | Details |
|---|---|
| Header bar | Count badge (filled/total), sort indicator |
| Participant cards | 2-column grid; team logos or player avatars; roster summary (first 3 + overflow count); status indicators (Checked In, Ready, Payment Review, Pending); "You" badge; rank display |
| Empty state | CTA to register |

### 5. Matches Tab (Lines 1108–1195)
| Feature | Details |
|---|---|
| Live matches section | Red pulsing border + indicator; team logos, scores, stream link |
| All matches list | Stage label, best-of badge, scores or "vs", completed opacity reduction, time display |
| Empty state | Message about bracket generation |

### 6. Bracket Tab (Lines 1198–1215)
| Feature | Details |
|---|---|
| Bracket container | Placeholder `<div>` for bracket visualization |
| Empty state | "Bracket Not Generated" message |
| **Note** | No actual interactive bracket rendering — just a placeholder div |

### 7. Standings Tab (Lines 1218–1275)
| Feature | Details |
|---|---|
| Table columns | Rank, Name, Group (conditional), MP, W, D, L, Pts; game-specific: GD, RD, KD |
| Visual indicators | Gold rank for top 3, green highlight for advancing teams, "ADV" badge |
| Responsive | Horizontal scroll on mobile |

### 8. Streams Tab (Lines 1278–1320)
| Feature | Details |
|---|---|
| Featured stream | Embedded iframe (aspect-video), live indicator, link to external platform |
| Additional streams | 2-column grid with platform-specific styling (Twitch purple, YouTube red) |
| Conditional rendering | Only shown when `has_streams` is true; tab includes live dot indicator |

### 9. Rules Tab (Lines 1323–1385)
| Feature | Details |
|---|---|
| Rulebook | Rich HTML with read more/less; PDF download link |
| Terms & Conditions | Separate section with PDF download |

### 10. Right Sidebar (Lines 1390–1595)
| Feature | Details |
|---|---|
| Registration status card | Game-color top border; status with animated indicators; slot progress bar (gradient fill); quick details (fee, format, mode, platform, dates); CTA button; terms agreement notice |
| Game info card | Game icon, name, category, platform |
| Organizer card | Official events: DeltaCrown branding with gold accents. Community events: organizer avatar, name, username, link to profile |
| Feature flags | 2-column grid: Check-In, Live Updates, Certificates, Rank Seeding, Challenges, Fan Voting |
| Share/Report buttons | Copy link + Report |
| Organizer tools | Management hub link, participants/brackets shortcuts (organizer-only) |

### 11. Mobile Sticky CTA (Lines 1598–1612)
| Feature | Details |
|---|---|
| Bottom bar | Entry fee display + Register/Manage button; hidden on `lg:` breakpoint |

### 12. JavaScript (Lines 1617–1692)
| Feature | Details |
|---|---|
| Tab switching | `switchTab()` with hash-based URL updates |
| Read more/less | `toggleDescription()` and `toggleRules()` |
| Auto-hide toggle | Hides "Read More" if content fits within 180px |
| Hash routing | Restores tab from URL hash on page load |

---

## Competitive Benchmark Analysis

### Toornament

Toornament is widely regarded as the most feature-complete tournament platform for organizers and participants.

| Feature | Toornament | DeltaCrown |
|---|---|---|
| Interactive bracket visualization | ✅ SVG/Canvas bracket with zoom/pan, clickable matches | ❌ Placeholder div only |
| Match detail modals | ✅ Click match → detailed popup with maps, VODs, stats | ❌ No match detail view |
| Participant seeding display | ✅ Seed numbers visible in participant list and bracket | ⚠️ Rank shown but no seeding context |
| Stage/phase navigation | ✅ Dedicated sub-navigation per stage | ⚠️ Multi-stage info exists but no per-stage navigation |
| Match scheduling calendar | ✅ Calendar view for upcoming matches | ❌ Not present |
| Participant statistics | ✅ Per-participant win rate, match history | ❌ Not present |
| Embeddable widgets | ✅ Bracket/standings embed code for external sites | ❌ Not present |
| Multi-language support | ✅ 10+ languages | ❌ English only |
| Custom fields / metadata | ✅ Organizer-defined custom fields | ❌ Not present |
| API-driven real-time updates | ✅ WebSocket-powered live scores | ❌ Page requires refresh |

### Battlefy

Battlefy focuses on community-driven grassroots esports with strong organizer tools.

| Feature | Battlefy | DeltaCrown |
|---|---|---|
| Discord integration | ✅ Auto-role assignment, check-in via Discord | ❌ Not present |
| Team roster management on detail page | ✅ Full roster with roles visible | ⚠️ Roster summary exists (3 names + overflow) |
| Map pool / pick-ban display | ✅ Visible per-match map selection | ❌ Not present |
| Social sharing (Twitter, Facebook, Discord) | ✅ Native share buttons with preview cards | ⚠️ Clipboard copy only |
| Follow tournament notifications | ✅ Follow button → email/push notifications | ❌ Not present |
| Chat / discussion thread | ✅ Built-in tournament chat | ❌ Not present (announcements only) |
| Check-in countdown | ✅ Visual countdown timer for check-in window | ⚠️ Check-in minutes shown but no live countdown |
| Registration waitlist | ✅ Automatic waitlist when slots are full | ❌ Not indicated |
| Match dispute system | ✅ Dispute button with screenshot upload | ❌ Not present |
| Organizer contact / support | ✅ Direct message organizer | ❌ Only "Report" button |

### FACEIT

FACEIT specializes in competitive matchmaking with anti-cheat and ranking integration.

| Feature | FACEIT | DeltaCrown |
|---|---|---|
| Player ELO / ranking integration | ✅ FACEIT Level shown on participant cards | ⚠️ Rank field exists but no ELO context |
| Anti-cheat status indicator | ✅ Mandatory anti-cheat badge | ❌ Not present |
| Match room with live chat | ✅ Dedicated match room per game | ❌ Not present |
| VOD / replay links per match | ✅ Post-match VOD links | ❌ Not present |
| Player stats overlay | ✅ Hover for recent performance | ❌ Not present |
| Premium queue / subscription indicator | ✅ Premium badge for subscribers | ❌ Not present |
| Automated server assignment | ✅ Server region / IP displayed | ❌ Not present |
| Toxicity / report history | ✅ Player reputation visible | ❌ Not present |
| In-page live match tracker | ✅ Real-time score updates via WebSocket | ❌ Requires page refresh |
| Countdown timer to match | ✅ Precise countdown per scheduled match | ❌ Not present |

### Start.gg (formerly Smash.gg)

Start.gg dominates the FGC and multi-game event space with sophisticated event management.

| Feature | Start.gg | DeltaCrown |
|---|---|---|
| Event series context | ✅ "Part of [Series Name]" with link to series page | ❌ Not present |
| Multi-event hub | ✅ Single page for tournament with multiple game events | ❌ Single tournament only |
| Attendee / spectator registration | ✅ Separate spectator/competitor registration | ❌ Competitor-only |
| Seed display in bracket | ✅ Seed numbers on bracket + participant list | ❌ Bracket not interactive |
| Phase pools visualization | ✅ Interactive pool/wave assignment | ❌ Group info exists but not interactive |
| Social sharing + OG previews | ✅ Rich cards with banner image, prize, date | ⚠️ `og:title` set but no `og:description`, `og:url`, or `og:image` override |
| Shop / merch integration | ✅ Event shop for merchandise | ❌ Not present on detail page |
| Sponsor display | ✅ Sponsor logos in header and sidebar | ❌ Not present |
| Travel / accommodation info | ✅ For LAN events, hotel/travel links | ❌ Not present |
| Historical results | ✅ "Previous editions" with links | ❌ Not present |
| JSON-LD structured data | ✅ Event schema for Google rich results | ❌ Not present |
| Qualification pathways | ✅ "Qualifies for [Major]" display | ❌ Not present |

---

## Gap Analysis: Missing Features

### Critical (Must Have)

#### 1. Interactive Bracket Visualization
- **What:** A zoomable, pannable bracket diagram (SVG or Canvas) showing all rounds, matchups, scores, and progression paths.
- **Why:** The bracket is the centerpiece of any elimination tournament. Without it, participants and spectators must mentally reconstruct the tournament state. Every major competitor renders interactive brackets. The current placeholder at [line ~1198](templates/tournaments/detailPages/detail.html#L1198) is a dead zone.
- **Suggested approach:** Integrate a JS library (e.g., `bracket-visualizer`, custom D3.js, or the existing `toc-brackets.js` in `static/tournaments/toc/js/`) into the public detail page. Consume bracket data from a JSON endpoint. Support single/double elimination and group-stage pools.

#### 2. Real-Time Score Updates (WebSocket / Polling)
- **What:** Live score updates on the matches tab and bracket without full page refreshes.
- **Why:** During live tournaments, spectators and participants refresh constantly. Real-time updates are table stakes for platforms like FACEIT and Toornament. The existing `enable_live_updates` feature flag (sidebar, [line ~1564](templates/tournaments/detailPages/detail.html#L1564)) exists but has no frontend implementation.
- **Suggested approach:** Implement Django Channels WebSocket or a lightweight polling endpoint (`/api/tournaments/<slug>/live/`). Update match scores and bracket state via JS.

#### 3. Social Sharing with Rich Previews
- **What:** Share buttons for Twitter/X, Facebook, Discord, WhatsApp with proper Open Graph and Twitter Card meta tags including tournament-specific banner image, description, and URL.
- **Why:** Tournament growth depends on viral sharing. The current implementation ([line ~304](templates/tournaments/detailPages/detail.html#L304)) only copies the URL to clipboard. The OG tags in `base.html` ([line 20-23](templates/base.html#L20)) use a generic default image and have no `og:description` or `og:url`. The detail page overrides `og_title` ([line 5](templates/tournaments/detailPages/detail.html#L5)) but not `og:image` (should use `tournament.banner_image`) or `og:description` (should use truncated description).
- **Suggested approach:** Override `og_image` and add `og_description` blocks in the detail template. Add share buttons using Web Share API with fallback to platform-specific share URLs. Generate tournament-specific OG images.

#### 4. Countdown Timer to Tournament Start
- **What:** A live countdown (days:hours:minutes:seconds) to the next significant event — registration close, check-in window, tournament start.
- **Why:** Creates urgency and reduces "when does it start?" questions. Every competitor platform features this prominently.
- **Suggested approach:** Add a JavaScript countdown component reading `tournament.tournament_start` (already available in the hero section at [line ~270](templates/tournaments/detailPages/detail.html#L270)). Display in the sidebar status card and optionally in the hero.

#### 5. Tournament-Specific Structured Data (JSON-LD)
- **What:** `Event` schema markup for Google rich results, including name, date, location, organizer, offers (entry fee), and image.
- **Why:** Improves SEO discoverability, enables Google event cards in search results. The platform already has a `seo_meta.html` partial ([line 1-9](templates/partials/seo_meta.html#L1)) but it's generic.
- **Suggested approach:** Add a `{% block json_ld %}` in the detail template outputting `<script type="application/ld+json">` with tournament data.

### Important (Should Have)

#### 6. Follow / Favorite Tournament Button
- **What:** A persistent "Follow" or "Favorite" (★) button allowing logged-in users to save the tournament and receive notifications for updates, announcements, and schedule changes.
- **Why:** Increases return visits and engagement. Battlefy and Start.gg both support this.
- **Suggested approach:** Add a toggle button in the hero action row ([line ~303](templates/tournaments/detailPages/detail.html#L303)). Use AJAX POST to a `/api/tournaments/<slug>/follow/` endpoint. Store in a `UserFavorite` model.

#### 7. Discord Server Link / Community Integration
- **What:** A prominent Discord invite link in the sidebar or overview tab, optionally with member count and online status.
- **Why:** Discord is the de facto communication channel for esports communities. Battlefy's deep Discord integration is a major competitive advantage. Currently the only community feature is one-way announcements ([line ~981](templates/tournaments/detailPages/detail.html#L981)).
- **Suggested approach:** Add a `discord_invite_url` field to the Tournament model. Display as a sidebar card with Discord branding.

#### 8. Sponsor Logos Section
- **What:** A dedicated area (hero footer or sidebar card) displaying sponsor/partner logos with optional links.
- **Why:** Tournaments rely on sponsorship revenue. Displaying sponsors prominently encourages future sponsorships and adds legitimacy. Start.gg and Toornament both feature sponsor sections.
- **Suggested approach:** Add a `TournamentSponsor` model (logo, name, URL, tier). Render in a sidebar card or below the hero.

#### 9. Recent Match Results on Overview Tab
- **What:** A "Recent Matches" mini-feed on the Overview tab showing the last 3-5 completed matches.
- **Why:** Users shouldn't have to switch to the Matches tab to see what happened recently. This is default on FACEIT and Start.gg.
- **Suggested approach:** Pass `recent_matches` (last 5) from the view context. Render compact match cards in the Overview tab after the phase timeline.

#### 10. Match Detail View / Modal
- **What:** Clicking a match opens a detailed view with map scores, individual stats, VOD links, and dispute options.
- **Why:** Match detail is critical for transparency and competitive integrity. Currently matches are flat cards with no drill-down.
- **Suggested approach:** Either a modal overlay or a dedicated URL (`/tournaments/<slug>/matches/<match_id>/`). Include per-map scores, MVP stats, and proof screenshots.

#### 11. Map / Veto System Display
- **What:** Visualization of map pick-ban process and map pool for applicable games.
- **Why:** Map veto is integral to CS2, Valorant, R6. Showing which maps were played/banned adds competitive context.
- **Suggested approach:** Add `map_pool` and `map_veto_sequence` to match data. Render inline on match cards or in match detail modal.

#### 12. Check-In Status Display
- **What:** When check-in is active, show a prominent check-in countdown, list of checked-in vs. not-checked-in participants, and personal check-in button.
- **Why:** Check-in is a pain point in esports. The `enable_check_in` flag exists ([line ~742](templates/tournaments/detailPages/detail.html#L742)) and check-in status appears on participant cards, but there's no dedicated check-in UI or live countdown.
- **Suggested approach:** Add a check-in banner at the top of the page when the check-in window is open. Include a live countdown and a one-click check-in button for registered participants.

### Nice to Have (Could Have)

#### 13. Tournament Series Context
- **What:** "This is Week 3 of [DeltaCrown Pro League Season 2]" with links to the series page and past editions.
- **Why:** Contextualizes one-off tournaments within larger competitive ecosystems. Start.gg excels at this.
- **Suggested approach:** Add optional `series` ForeignKey on Tournament model. Display as a breadcrumb or banner above the hero.

#### 14. Historical Data / Past Editions
- **What:** "Previous Editions" section showing past iterations of the same tournament with links and winners.
- **Why:** Builds brand equity for recurring tournaments. Start.gg and Toornament both support series history.
- **Suggested approach:** Query tournaments with the same `series` FK. Display as a compact timeline in a sidebar card.

#### 15. Spectator Mode / Observer Slots
- **What:** Separate registration tier for spectators (especially relevant for LAN events) with observer slot management for online events.
- **Why:** LAN events need headcounts beyond competitors. Online events benefit from showing a "spectators watching" count.
- **Suggested approach:** Add `spectator_registration` option to Tournament model; allow spectator-type registration.

#### 16. Qualification Pathway Display
- **What:** "Winner qualifies for [Major Tournament]" badge with link to the qualifying event.
- **Why:** Raises stakes and attracts competitive players. Common on FACEIT and Start.gg for circuit events.
- **Suggested approach:** Add optional `qualifies_for` ForeignKey. Display as a prominent badge in the hero section.

#### 17. Embeddable Widgets
- **What:** "Embed this bracket" / "Embed standings" with copy-paste HTML code for external websites and social media.
- **Why:** Increases platform reach. Toornament's embeddable widgets are a key differentiator.
- **Suggested approach:** Create standalone embed views with minimal CSS. Provide embed code generator in sidebar.

#### 18. Prize Distribution Chart
- **What:** A visual bar chart or pie chart showing prize distribution beyond top 3.
- **Why:** For larger tournaments with prize distributions beyond 3 places, the current podium layout ([line ~689](templates/tournaments/detailPages/detail.html#L689)) is insufficient.
- **Suggested approach:** Use Chart.js or a simple CSS bar chart. Loop through `tournament.prize_distribution` (currently only `.1`, `.2`, `.3` are accessed).

#### 19. Player / Team Profile Previews
- **What:** Hover or click on a participant to see a popup with their platform stats, recent results, and team info.
- **Why:** Adds depth to the participant list and helps gauge competition level.
- **Suggested approach:** AJAX-loaded popover or tooltip using participant profile data.

#### 20. Multi-Language Support
- **What:** i18n support for tournament content and UI strings.
- **Why:** DeltaCrown targets Bangladesh (detected from BDT currency ৳ and bKash/Nagad payment methods). Bangla language support would be valuable.
- **Suggested approach:** Django's built-in i18n framework with `{% trans %}` tags and `.po` files.

---

## UI/UX Observations

### Strengths

1. **Game-dynamic theming** — The CSS variable system (`--game-color`, `--game-color-secondary`) at [lines 10-18](templates/tournaments/detailPages/detail.html#L10) is excellent. Each tournament inherits visual identity from its game, creating unique feel per-page without custom code.

2. **Glassmorphism consistency** — Three tiers of glass (`.glass`, `.glass-strong`, `.glass-panel`) at [lines 95-109](templates/tournaments/detailPages/detail.html#L95) create visual hierarchy. The `hover` border-color transitions are subtle and effective.

3. **Status badges** — Comprehensive treatment of 8+ tournament states ([lines 175-226](templates/tournaments/detailPages/detail.html#L175)) with appropriate color coding (red = live, green = registration open, gray = completed, etc.).

4. **Typography system** — Good use of three font families (Inter for body, Space Grotesk for display, Rajdhani for gaming/UI). The `font-gaming` and `font-display` utilities are used consistently.

5. **Mobile sticky CTA** ([lines 1598-1612](templates/tournaments/detailPages/detail.html#L1598)) — Smart pattern hiding on desktop (`lg:hidden`) and showing a persistent registration bar on mobile.

6. **Prize pool podium** ([lines 689-726](templates/tournaments/detailPages/detail.html#L689)) — Creative CSS-only podium with 1st elevated higher than 2nd and 3rd, gold glow animations, and trophy icon.

### Weaknesses

1. **No loading states** — Tab switching shows/hides content instantly. For tabs that might load data asynchronously in the future (matches, bracket), there are no skeleton screens or loading indicators.

2. **No transition animations between tabs** — Content appears/disappears with `hidden`/`block` class toggle ([line ~1618](templates/tournaments/detailPages/detail.html#L1618)). Consider fade/slide transitions.

3. **Inline styles** — ~160 lines of CSS in a `<style>` block ([lines 8-157](templates/tournaments/detailPages/detail.html#L8)). This increases page weight, prevents browser caching, and makes maintenance harder. Should be extracted to `static/tournaments/css/detail.css`.

4. **Repeated UI patterns** — The registration CTA appears in 4 places (hero, nav bar, overview tab, sidebar, mobile sticky bar). While intentional for conversion, the extensive duplication makes updates error-prone.

5. **Fixed 64px top offset** — Sticky nav at `top: 64px` ([line 83](templates/tournaments/detailPages/detail.html#L83)) assumes the main navbar is exactly 64px tall. This will break if the main nav changes height or has an announcement banner.

6. **Color contrast concerns** — Several text elements use `text-gray-600` and `text-gray-500` on dark backgrounds (e.g., `#111111`), which may not meet WCAG AA contrast requirements (~3:1 ratio instead of required 4.5:1).

7. **No focus indicators** — Tab buttons and interactive elements are `<button>` and `<a>` elements with no visible focus ring beyond browser defaults (which are often invisible on dark backgrounds).

8. **`alert()` for share feedback** — The share button at [line 304](templates/tournaments/detailPages/detail.html#L304) uses `alert('Link copied!')` which is jarring. Should use a toast notification (Toastify is already loaded in `base.html`).

9. **No empty state illustrations** — Empty states for tabs (matches, participants, bracket, standings) use generic Lucide icons. Custom illustrations would add personality.

10. **Sidebar scroll behavior** — The sidebar uses `sticky top-24` ([line 1392](templates/tournaments/detailPages/detail.html#L1392)). If sidebar content exceeds viewport height, the bottom cards will be inaccessible. Need `max-height: calc(100vh - 6rem); overflow-y: auto;`.

---

## Performance Considerations

### CSS

| Issue | Impact | Location |
|---|---|---|
| ~160 lines of inline `<style>` | Not cached between page loads; increases HTML payload | Lines 8–157 |
| `backdrop-filter: blur()` used on 10+ elements | GPU-intensive; causes jank on low-end devices | `.glass`, `.glass-strong`, `.glass-panel`, `.sticky-nav-wrapper` |
| 3 fixed-position ambient orbs with `filter: blur(60-80px)` and continuous animations | Constant GPU compositing; battery drain on mobile | Lines 35–52 |
| `color-mix()` CSS function | Not supported in browsers < 2023 (Chrome 111, Firefox 113, Safari 16.2). No fallback. | Throughout |
| Inline SVG noise texture (data URI) | ~500 byte embedded SVG in CSS; acceptable but could be external | Lines 53–59 |

### Images

| Issue | Impact |
|---|---|
| No `loading="lazy"` on participant avatars/logos | All images load immediately, even in hidden tabs (Participants, Matches) |
| No `srcset` / responsive images for banner | Single image at full resolution for all devices |
| No `width`/`height` attributes on images | Causes layout shift (CLS) |
| No WebP/AVIF format | Likely serving PNG/JPEG without modern format alternatives |

### JavaScript

| Issue | Impact | Location |
|---|---|---|
| Lucide icons loaded from unpkg CDN (`lucide@latest`) | Unversioned CDN; could break. ~50KB+ library. | `base.html` (tournament base) |
| `lucide.createIcons()` called on every tab switch | Re-scans entire DOM; should scope to changed tab | Line 1624 |
| No JS bundle — all inline | Not minified, not cached | Lines 1617–1692 |
| All tab content present in DOM but hidden | Full HTML for all tabs loaded on initial render, increasing DOM size | All `tab-content` divs |

### Recommendations for Performance

1. Extract inline CSS to `static/tournaments/css/detail.css` — enables caching.
2. Add `loading="lazy"` to all images in hidden tabs.
3. Add `width` and `height` attributes to prevent CLS.
4. Pin Lucide version (e.g., `lucide@0.344.0`).
5. Scope `lucide.createIcons()` to the activated tab's container.
6. Consider lazy-loading tab content (HTMX or fetch-on-demand) to reduce initial DOM size.
7. Add `will-change: transform` to ambient orbs and remove animations on `prefers-reduced-motion`.
8. Provide `color-mix()` fallbacks for older browsers.
9. Reduce `backdrop-filter` usage on mobile or behind a `@supports` gate.

---

## Recommendations Summary

**Top 10 Prioritized Improvements:**

| Priority | Improvement | Effort | Impact |
|---|---|---|---|
| 1 | **Interactive bracket visualization** — Replace placeholder with actual rendered bracket | High | Critical — defines tournament experience |
| 2 | **Rich OG/Twitter meta tags** — Override `og:image` with banner, add `og:description`, `og:url` | Low | Critical — enables viral sharing |
| 3 | **Real-time live score updates** — WebSocket or polling for matches tab | High | Critical — expected by live tournament audiences |
| 4 | **Countdown timer** — JS countdown to registration close / tournament start | Low | High — creates urgency and reduces support questions |
| 5 | **Social share buttons** — Twitter/X, Facebook, WhatsApp, Discord with Web Share API | Low | High — growth multiplier |
| 6 | **Follow/Favorite button** — Save tournament + notification subscription | Medium | High — drives repeat engagement |
| 7 | **Extract inline CSS/JS** — Move to external cached files | Low | Medium — performance + maintainability |
| 8 | **Discord community link** — Sidebar card with invite URL | Low | Medium — community building |
| 9 | **Accessibility pass** — ARIA labels, focus indicators, contrast fixes, `prefers-reduced-motion` | Medium | Medium — legal compliance + inclusion |
| 10 | **JSON-LD structured data** — `Event` schema for Google rich results | Low | Medium — SEO improvement |

---

*Audit Date: March 5, 2026*
*Auditor: DeltaCrown Engineering*
*Template: `templates/tournaments/detailPages/detail.html` (1,692 lines)*
*Base: `templates/tournaments/base.html` → `templates/base.html`*
