# DeltaCrown Design Improvement Report

**Date:** April 2026  
**Scope:** Hub (Matches, Schedule, Participants, Overview), Match Room, TOC Participant View  
**Audit:** Visual quality, UX consistency, mobile responsiveness, avatar/media reliability

---

## Executive Summary

The current design foundation is solid — cinematic glass-morphism theme, tone-reactive match cards, and a functional mobile dock. However, several areas need refinement to reach a polished, competitive-grade esports UI. The key issues are:

1. **Avatar/Photo Reliability** — Root-cause fixed (see §1)
2. **Match Card Visual Hierarchy** — Score/status not prominent enough
3. **Schedule Tab Layout** — Needs stronger visual differentiation between match states
4. **Participant Cards** — Missing bio depth and visual richness
5. **Match Room Hero Section** — Mobile cramping issues, VS pill too small
6. **Typography & Spacing Consistency** — Mixed tailwind utilities vs CSS classes
7. **Mobile-First Polish** — Several tap-target and overflow issues

---

## §1 — Avatar/Photo Root-Cause Fix (DONE ✅)

### Problem
- TOC participants page (`/toc/{slug}/#participants`) shows user photos correctly
- Hub pages (participants, matches, schedule, standings, match room) showed broken photos or initials for team participants

### Root Cause
**No user-avatar fallback for team participants.** The TOC API returns both `team_logo_url` and `profile_avatar_url`, allowing the frontend to fall back from team logo → user photo. The Hub API only returned the team logo; when a team had no logo uploaded, the card showed initials instead of the registering user's actual photo.

Additionally, several raw `.url` calls in `hub.py` bypassed the `_normalize_media_url()` function, which can cause issues in local dev environments (FileSystemStorage → MediaProxyMiddleware redirect chain).

### What Was Fixed
| File | Change |
|------|--------|
| `hub.py` `_build_participant()` | Added user avatar fallback for teams: `logo_url or user_avatar`. Added `profile_avatar_url` field. |
| `hub.py` `_build_participant_media_map()` | For teams without logos, loads registrant's avatar from Registration → user.profile.avatar |
| `hub.py` overview / standings / sponsors | Normalized all raw `.url` calls through `_normalize_media_url()` |
| `hub.py` team member avatars prefetch | Normalized through `_normalize_media_url()` |
| `match_room.py` `_participant_media_map()` | Added registrant avatar fallback for teams without logos |
| `matches_service.py` `_build_media_map()` | Added registrant avatar fallback for teams without logos |
| `hub-engine.js` `_renderParticipants()` | Uses `p.logo_url \|\| p.profile_avatar_url` for avatar source |
| `hub-engine.js` `_renderMobileStandingsParticipants()` | Same fallback chain |

---

## §2 — Hub Match Cards (Matches Tab)

### Current State
- Match cards use `hub-match-priority-card` with tone classes (live/ready/review/scheduled)
- VS grid: 3-column layout with `3.2rem` avatars, `2.6rem` VS pill
- Score display: `1.08rem` font size (monospace)
- CTA buttons row at bottom

### Issues
1. **Score too subtle** — The `1.08rem` scoreline font at the center of the VS grid is hard to read at a glance. Competitive users need to see scores instantly.
2. **Avatar size inconsistency** — Side avatars are `3.2rem` but feel small relative to the card's visual weight; the card has large padding and heavy gradients but the actual content (names + avatars) is undersized.
3. **Side labels ("Side 1", "Side 2")** — Default labels like "Side 1" / "Side 2" are meaningless. Should show "Team A" / "Team B" or dynamically assign based on bracket position (e.g., "Upper Bracket", "Seed #3").
4. **Kicker text too small** — `0.62rem` (9.3px) with `0.15em` letter spacing is borderline unreadable on mobile.
5. **Meta chips crowd the bottom** — Calendar, lobby code, and group info chips are all `0.62rem` in a horizontal row; on narrow screens these wrap badly.
6. **No match time prominence** — Scheduled matches should show the match time larger than it currently appears (buried in a meta chip).
7. **CTA button hit target** — Buttons have adequate padding but are in a flex row; on mobile, two buttons side by side can be hard to tap accurately.

### Recommendations
- **Score**: Increase scoreline font to `1.4rem`+ with Outfit font, add very subtle glow for live matches.
- **Avatars**: Increase side avatars to `3.6rem`, add team-color border ring when team colors are available.
- **Side labels**: Replace "Side 1/2" with seed number, bracket position, or "Home/Away" based on context.
- **Kicker**: Increase to `0.7rem` minimum. Remove excess letter-spacing on mobile.
- **Match time**: For scheduled matches, show time in the center column (where VS pill sits) with larger typography.
- **CTA buttons**: On mobile (< 640px), stack buttons vertically instead of row.

---

## §3 — Hub Schedule Tab

### Current State
- Card-based VS layout with 3-column grid
- Left side: `w-9 h-9` avatar + name
- Center: Score or time
- Right side: Name + avatar (reversed)
- `border-left: 3px solid {stateColor}` for state indication
- Day-group headers separate matches chronologically

### Issues
1. **Avatars too small** — `w-9 h-9` (2.25rem) is too small for a primary content card. They look like tiny thumbnails.
2. **No visual prominence for "your" matches** — Unlike the matches tab which shows "You" / "Opponent" labels, the schedule mixes all matches without visual distinction for the participant's own matches.
3. **Score typography mismatch** — Completed match scores use `text-lg font-black` with Outfit font, but the `:` separator uses `text-xs text-gray-600`, creating an unbalanced look.
4. **No match room CTA** — Schedule cards don't have "Join Match" / "Go to Lobby" buttons; users must navigate to the Matches tab to enter the match room.
5. **Winner badge placement** — The winner badge appears below the score grid (`mt-2.5 flex items-center justify-center`) as a separate element, which feels disconnected from the score context.
6. **Day headers weak** — Day section headers (`text-[10px] font-black text-gray-600 uppercase`) are easily overlooked.
7. **Participant breakdown grid** — For completed own-matches, the You/Opponent score boxes add 2 extra rows below the card, making completed cards much taller than scheduled ones, disrupting visual rhythm.

### Recommendations
- **Avatars**: Increase to `w-11 h-11` (2.75rem) minimum, with rounded-xl.
- **Own match highlight**: Add a subtle left border accent (`border-l-2 border-[#00F0FF]`) or background tint for `is_my_match` cards.
- **CTA row**: Add a "Go to Match" button for live/lobby-open matches directly on the schedule card.
- **Score formatting**: Use a single VS-pill style element (like the matches tab) instead of separate score elements for consistency.
- **Winner badge**: Move inline with the score display, as a small medal icon next to the winner's score.
- **Day headers**: Increase to `text-xs` with a horizontal rule (`<hr class="border-white/10">`), add leading icon (calendar icon).
- **Card height normalization**: Use CSS grid or min-height to keep completed and scheduled cards at consistent heights.

---

## §4 — Hub Participants Tab

### Current State
- Glass card grid with `p-5 rounded-xl` cards
- `w-12 h-12 rounded-lg` logo/avatar container
- Team mode: stacked member avatar strip (-space-x-2, up to 3 shown)
- Meta pills: Region, Role, Platform, Seed

### Issues
1. **No game-specific identity** — Participants don't show their in-game name (IGN), which is the primary identifier in esports.
2. **Member avatar strip detached** — The stacked avatars appear below the main content with `mt-3`, creating visual separation from the team name/logo.
3. **No click-through to match history** — Clicking a participant card goes to their profile page, but there's no quick way to see their tournament performance/match history.
4. **Checked-in indicator too subtle** — A `w-2 h-2` green dot in the top-right of the header row is easy to miss.
5. **Status label rendering** — Pending participants show status labels ("Pending", "Payment Review") but these are text-only, with no color coding.
6. **Member count text style** — `text-[10px] text-gray-500 uppercase tracking-widest` with Space Grotesk is over-styled for secondary information.
7. **"You" badge alignment** — The "You" badge is `ml-1` next to the name, but when the name wraps, the badge drops to the next line awkwardly.

### Recommendations
- **IGN display**: Add the participant's game-specific IGN below their name (fetch from GameProfile).
- **Member avatars**: Move the avatar strip inline with the team name (right-aligned in the header row) instead of below.
- **Checked-in indicator**: Replace the tiny dot with a pill badge like `✓ Checked In` in green.
- **Status labels**: Use colored pill badges matching the existing status color scheme (pending=amber, review=blue, blocked=red).
- **"You" badge**: Use `shrink-0` to prevent wrapping; alternatively, place it as a corner ribbon on the card.

---

## §5 — Match Room

### Current State
- Hero VS section with `w-11 h-11`←`w-16 h-16` (mobile←desktop) logos
- Phase tracker: horizontal dots with connecting lines, overflow-x-auto on mobile
- Glass panel sidebar (chat + rules) on desktop, overlay on mobile
- Score input: `w-[4.5rem] h-[4.5rem]` cards
- Waiting overlay with radar spinner animation

### Issues
1. **Mobile hero cramping** — On mobile, the hero section with both team logos + names + VS pill + meta text gets cramped. The `gap-2.5` with `w-11 h-11` logos leaves little room for team names.
2. **Phase tracker horizontal scroll** — On mobile, the phase tracker scrolls horizontally with `justify-start`, but there's no visual indicator that scrolling is possible (no fade gradient at edges).
3. **VS pill too small on mobile** — `w-7 h-7 text-[10px]` makes the VS barely visible.
4. **Chat panel empty state** — When no messages exist, the chat area shows a small icon + text, but the empty state takes up the full panel height with nothing interesting.
5. **Score input accessibility** — The `4.5rem × 4.5rem` score input cards don't have visible increment/decrement buttons; users must type. On mobile, the numeric keypad may not auto-open.
6. **No-show timer visibility** — The no-show countdown is in an amber badge in the waiting overlay, but if a user is multitasking (another tab), they won't see it.
7. **Mobile bottom nav overlap** — The 3-button mobile nav can overlap with the engine content if the viewport is short (e.g., landscape mobile).

### Recommendations
- **Mobile hero**: Reduce logo to `w-10 h-10` on very small screens (`< 380px`), increase `gap-3` between logo and name, truncate long names to 15 characters.
- **Phase tracker scroll indicator**: Add a fade-out gradient on the right edge when scrollable content overflows.
- **VS pill mobile**: Increase to `w-8 h-8 text-xs` minimum.
- **Chat empty state**: Show a cinematic "Match hasn't started yet" illustration or animated "connecting…" state.
- **Score input**: Add `inputmode="numeric"` and `+/-` stepper buttons for mobile.
- **No-show timer**: Fire a browser notification if the tab is not focused (using Notification API if permissions granted).
- **Mobile nav**: Add `pb-safe` / `margin-bottom: env(safe-area-inset-bottom)` for iOS devices.

---

## §6 — Typography & Visual Consistency

### Issues
1. **Mixed font sizing approach** — Some elements use Tailwind utility classes (`text-sm`, `text-[10px]`), others use CSS classes with `rem` values. This creates maintenance burden.
2. **Three monospace fonts** — `Space Grotesk` is used as "monospace" in some places, but it's not a monospace font. `font-family: 'Space Grotesk', monospace` will use Space Grotesk for most characters but fall back to system monospace for others, creating visual inconsistency.
3. **Font weight escalation** — Many elements use `font-black` (900 weight) for small text (8–10px), which can look blurry on low-DPI screens.
4. **Color proliferation** — The palette includes `#00F0FF`, `#00FF66`, `#FF2A55`, `#FFB800`, `#66FFAE`, `#FF93A8`, `#FF8AA0` plus grayscale variants. Several of these are too close in hue (e.g., `#00FF66` vs `#66FFAE`, `#FF2A55` vs `#FF93A8`).

### Recommendations
- **Design tokens**: Define a token system in CSS variables for font sizes: `--text-nano` (9px), `--text-micro` (10px), `--text-caption` (11px), `--text-body` (13px), `--text-title` (16px), `--text-heading` (20px).
- **Monospace**: Use `'JetBrains Mono', 'Fira Code', monospace` for actual monospace needs (scores, codes, timers). Use Space Grotesk only as a display font.
- **Font weight**: Reserve `font-black` (900) for headings 16px+. Use `font-bold` (700) for body text and `font-extrabold` (800) for emphasis.
- **Color palette**: Reduce to 5 core semantic colors: primary (cyan), success (green), danger (red), warning (amber), info (blue). Use opacity variants (`/20`, `/40`, `/80`, etc.) instead of separate hex values.

---

## §7 — Global UX Improvements

### Tab Transitions
Currently tabs switch with a hard `display: none → block` toggle. Adding a subtle fade-in (`opacity 0→1` over 150ms) would make navigation feel more polished.

### Loading Skeletons
The skeleton loaders (for matches, schedule, participants) use basic placeholder shapes. Adding a shimmer animation (moving gradient) would indicate active loading.

### Error States
When API calls fail, no visible error state is shown — the skeleton just stays forever. Add a retry-able error card: "Couldn't load matches. [Retry]".

### Offline/Reconnect Flow
The WebSocket status indicator (`socket-pill`) shows connection state, but there's no "Reconnecting…" banner when the connection drops temporarily.

### Scroll-to-Top
Long lists (participants with 100+ entries) have no quick scroll-to-top mechanism. Add a floating "↑" button that appears after scrolling.

---

## Priority Matrix

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| P0 (Done) | Avatar/photo root-cause fix | ✅ Done | High — photos now show everywhere |
| P1 | Score prominence in match cards | Small | High — primary user action is checking scores |
| P1 | Schedule tab "own match" highlight + CTA | Medium | High — users need to find and join their matches fast |
| P1 | Match room mobile hero cramping | Small | Medium — affects all mobile users |
| P2 | Participant IGN display | Medium | Medium — improves identity recognition |
| P2 | Typography token system | Medium | Medium — improves long-term maintainability |
| P2 | Loading/error states | Medium | Medium — prevents confusion during slow loads |
| P3 | Tab transitions & animations | Small | Low — polish item |
| P3 | Color palette consolidation | Small | Low — maintenance debt reduction |
| P3 | Scroll-to-top button | Small | Low — convenience feature |

---

## Summary

The avatar fix resolves the most visible bug. The remaining improvements are incremental design refinements that can be tackled in themed sprints. The highest-impact items are score prominence, schedule match CTA, and mobile match room ergonomics.
