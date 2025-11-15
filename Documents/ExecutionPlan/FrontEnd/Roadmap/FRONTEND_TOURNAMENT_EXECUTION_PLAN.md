# Frontend Tournament Execution Plan

**Date**: November 15, 2025  
**Scope**: Phased execution plan for tournament-focused frontend implementation  
**Status**: Planning phase

---

## Overview

This document defines **how** and **when** to implement tournament frontend features, breaking work into manageable phases with clear objectives, dependencies, and acceptance criteria.

**Implementation Strategy**:
- **Phase-based**: 6 major phases (FE-T1 through FE-T6)
- **Tournament-first**: Focus on tournament lifecycle before refactoring existing pages
- **Incremental**: Each phase delivers working features
- **Backend-dependent**: Some phases blocked until backend APIs available

**Total Estimated Timeline**: 8-10 weeks (1 phase per 1-2 weeks)

---

## Phase Structure

Each phase includes:
- **Objectives**: What we're building
- **Screens/Features**: Specific pages/components
- **Dependencies**: Backend APIs, previous phases
- **Acceptance Criteria**: Definition of done
- **Estimated Effort**: Story points or days
- **Risks**: Potential blockers

---

## Phase FE-T1: Before Tournament (Discovery & Detail)

**Duration**: 1-2 weeks  
**Priority**: P0 (Critical for MVP)

### Objectives

Implement tournament discovery and detail pages allowing players to browse and learn about tournaments before registering.

### Screens & Features

1. **Tournament List Page** (`/tournaments/`)
   - Tournament cards grid/list
   - Filter bar (game, status)
   - Search functionality
   - Pagination
   - Empty state

2. **Tournament Detail Page** (`/tournaments/<slug>/`)
   - Hero section with tournament info
   - Tab navigation (Overview, Schedule, Prizes, Rules)
   - Registration entry point (button with states)
   - Organizer info sidebar
   - Participant count display

3. **Registration Entry Point**
   - Dynamic registration button (6 states)
   - Countdown timer (if registration opens soon)
   - "Already registered" state
   - Login prompt (if not authenticated)

### Backend APIs Needed

- ✅ `GET /api/tournaments/discovery/` (Module 9.1)
- ✅ `GET /api/tournaments/<slug>/` (Module 9.1)
- ✅ `GET /api/tournaments/<slug>/registration-status/` (Module 4.1)

### Dependencies

- **Backend**: Module 9.1 (Discovery service) must be complete
- **Design**: Design tokens already exist (`tokens.css`)
- **Components**: Card, badge, button components (reuse existing)

### Acceptance Criteria

- [ ] Tournament list loads in <2s on 3G mobile
- [ ] Filters work (game, status) with URL params
- [ ] Search returns relevant results
- [ ] Tournament detail page shows all required info
- [ ] Registration button states update based on backend API
- [ ] Mobile responsive (360px to 428px tested)
- [ ] Accessibility: Keyboard navigation, ARIA labels, color contrast
- [ ] Empty states show when no tournaments available

### Technical Implementation

**Templates**:
- Enhance `templates/spectator/tournament_list.html`
- Enhance `templates/spectator/tournament_detail.html`

**Static Assets**:
- Reuse `static/siteui/js/filter-orb.js` for filters
- Add `static/tournaments/js/registration-button.js` for button states
- Reuse `static/css/tokens.css` for styling

**Real-Time**: Not required (static data)

### Risks & Mitigation

**Risk 1**: Backend API not ready (Module 9.1)
- **Mitigation**: Use mock data for frontend development, swap to real API when ready

**Risk 2**: Tournament detail page too complex (many tabs)
- **Mitigation**: Start with Overview tab only, add others incrementally

**Risk 3**: Performance issues on large tournament lists
- **Mitigation**: Implement pagination (50 per page), lazy load images

---

## Phase FE-T2: Registration Flow

**Duration**: 1-2 weeks  
**Priority**: P0 (Critical for MVP)

### Objectives

Implement multi-step registration wizard allowing players to register for tournaments with team selection, custom fields, and payment.

### Screens & Features

1. **Registration Wizard** (`/tournaments/<slug>/register/`)
   - Step 1: Eligibility check (auto)
   - Step 2: Team/Solo selection (conditional)
   - Step 3: Custom fields (dynamic form)
   - Step 4: Payment info (conditional)
   - Step 5: Review & Confirm
   - Stepper component (progress indicator)
   - Back/Next navigation
   - Form validation (client-side)

2. **Success Page** (`/tournaments/<slug>/register/success/`)
   - Confirmation message
   - Receipt (if paid)
   - Next steps
   - CTAs (View Tournament, View Dashboard)

3. **Error Page** (`/tournaments/<slug>/register/error/`)
   - Error message
   - Retry or contact support CTAs

### Backend APIs Needed

- ✅ `GET /api/tournaments/<slug>/registration-form/` (Module 4.1)
- ✅ `POST /api/tournaments/<slug>/register/` (Module 4.1)
- ✅ `GET /api/payments/methods/` (Module 3.1)
- ⚠️ Payment gateway integration (Module 3.1, external redirect)

### Dependencies

- **Phase FE-T1**: Tournament detail page must show registration button
- **Backend**: Module 4.1 (Registration service) complete
- **Backend**: Module 3.1 (Payment service) complete for paid tournaments
- **Teams Module**: User must have teams if team tournament (existing feature)

### Acceptance Criteria

- [ ] Wizard navigates between steps correctly (back/next)
- [ ] Stepper shows current step visually
- [ ] Team selector shows only user's eligible teams
- [ ] Custom fields render dynamically based on tournament config
- [ ] Form validation works (inline errors on blur)
- [ ] Payment method selection works (radio cards)
- [ ] Payment redirect works (external gateway, SSLCommerz)
- [ ] Success page shows after free registration
- [ ] Success page shows after payment callback
- [ ] Error page shows on failure with clear message
- [ ] Mobile: Full-screen wizard, sticky Next button
- [ ] Registration state persists on refresh (localStorage, P1)

### Technical Implementation

**Templates**:
- Create `templates/tournaments/register.html` (wizard)
- Create `templates/tournaments/register_success.html`
- Create `templates/tournaments/register_error.html`

**Static Assets**:
- Reuse `static/siteui/js/reg_wizard.js` (existing wizard logic)
- Enhance `static/js/dynamic-registration.js` (custom fields)
- Add `static/tournaments/js/registration-flow.js` (new logic)
- Reuse `static/siteui/js/form-validator.js`

**Real-Time**: Not required

### Risks & Mitigation

**Risk 1**: Payment gateway integration complex
- **Mitigation**: Read-only UI (frontend just shows payment methods, backend handles redirect)

**Risk 2**: Custom fields vary widely per tournament
- **Mitigation**: Use dynamic form builder based on JSON schema from backend

**Risk 3**: Tournament fills up during registration
- **Mitigation**: Backend validates on submit, show error modal if full

---

## Phase FE-T3: During Tournament (Spectator & Player Views)

**Duration**: 2 weeks  
**Priority**: P0 (Critical for MVP)

### Objectives

Implement live tournament views showing bracket, matches, and leaderboard with real-time updates.

### Screens & Features

1. **Live Bracket View** (`/tournaments/<slug>/bracket/`)
   - Bracket tree visualization (SVG, consider d3-bracket library)
   - Schedule/list view toggle
   - Match cards (click to view detail)
   - Real-time score updates
   - "My Matches" filter (if participant)

2. **Match Detail Page** (`/tournaments/<slug>/matches/<id>/`)
   - Match info (participants, round, status)
   - Score display (large, centered)
   - Match timeline (events)
   - Lobby info (for participants, if upcoming/live)
   - Actions (for participants):
     - Report score (modal)
     - Dispute score (modal)

3. **Tournament Leaderboard** (`/tournaments/<slug>/leaderboard/`)
   - Rankings table (rank, team, stats)
   - Real-time updates
   - Highlight current user's row
   - Top 3 with medal icons

4. **Tournament Detail (Live State)**
   - Adapt existing detail page for live state
   - Tabs: Bracket, Leaderboard, Matches, Overview
   - Real-time updates via WebSocket + HTMX fallback

### Backend APIs Needed

- ✅ `GET /api/tournaments/<slug>/bracket/` (Module 5.1)
- ✅ `GET /api/tournaments/<slug>/matches/` (Module 5.1)
- ✅ `GET /api/matches/<match_id>/` (Module 5.2)
- ✅ `POST /api/matches/<match_id>/report-score/` (Module 5.4)
- ✅ `POST /api/matches/<match_id>/dispute/` (Module 5.5)
- ✅ `GET /api/tournaments/<slug>/leaderboard/` (Module 5.3)
- ✅ WebSocket: `/ws/tournaments/<slug>/` (live updates)

### Dependencies

- **Phase FE-T1**: Tournament detail page exists
- **Backend**: Modules 5.1-5.5 (Match & Bracket services) complete
- **WebSocket**: Real-time infrastructure ready (exists: `spectator_ws.js`)

### Acceptance Criteria

- [ ] Bracket view renders correctly (single-elim, double-elim, round-robin)
- [ ] Bracket updates in real-time (<3s after backend change)
- [ ] Schedule view shows all matches with filters
- [ ] Match detail shows scores and timeline
- [ ] Report score modal works (participants only)
- [ ] Dispute modal works (participants only, within 24h)
- [ ] Leaderboard updates in real-time
- [ ] Leaderboard highlights current user's row
- [ ] WebSocket connection stable, reconnects on disconnect
- [ ] HTMX fallback works if WebSocket unavailable
- [ ] Mobile: Bracket scrolls horizontally or prefer list view
- [ ] Mobile: Match detail actions sticky at bottom

### Technical Implementation

**Templates**:
- Create `templates/tournaments/bracket.html`
- Create `templates/tournaments/match_detail.html`
- Create `templates/tournaments/leaderboard.html`
- Enhance `templates/spectator/tournament_detail.html` (live state)

**Static Assets**:
- Add `static/tournaments/js/bracket-renderer.js` (SVG bracket)
  - Consider using `d3-bracket` library (CDN or npm)
- Enhance `static/spectator/js/spectator_ws.js` (WebSocket client)
- Add `static/tournaments/js/match-actions.js` (report, dispute)
- Reuse `templates/spectator/_leaderboard_table.html` (partial)

**Real-Time**: **CRITICAL**
- WebSocket primary, HTMX fallback
- Throttle updates (max 1 per 500ms)
- Toast notifications for match updates (if participant)

### Risks & Mitigation

**Risk 1**: Bracket rendering complex for different formats
- **Mitigation**: Use existing library (d3-bracket) for MVP, custom later

**Risk 2**: Real-time performance issues (many concurrent users)
- **Mitigation**: Throttle updates, batch messages, use Redis Pub/Sub (backend)

**Risk 3**: WebSocket disconnects frequently
- **Mitigation**: Exponential backoff reconnect, fall back to HTMX polling

---

## Phase FE-T4: After Tournament (Results & Recap)

**Duration**: 3-5 days  
**Priority**: P0 (Critical for MVP)

### Objectives

Implement final results page showing winners, complete rankings, and match history.

### Screens & Features

1. **Results Page** (`/tournaments/<slug>/results/`)
   - Winners section (podium, top 3)
   - Final leaderboard (complete rankings)
   - Match history (all matches, expandable)
   - Stats summary (total matches, duration, upsets)
   - Prize distribution (who won what)

2. **Tournament Detail (Completed State)**
   - Adapt existing detail page for completed state
   - Tabs: Results, Final Bracket, Overview

3. **Certificate Download** (P2, optional)
   - `/tournaments/<slug>/certificate/<username>/`
   - PDF download link
   - Social share buttons

### Backend APIs Needed

- ✅ `GET /api/tournaments/<slug>/results/` (Module 6.5)
- ⚠️ `GET /api/tournaments/<slug>/certificate/<user_id>/` (Module 6.6, P2)

### Dependencies

- **Phase FE-T3**: Bracket and leaderboard components reused
- **Backend**: Module 6.5 (Results service) complete
- **Backend**: Module 6.6 (Certificate service) for P2 feature

### Acceptance Criteria

- [ ] Results page shows top 3 winners prominently
- [ ] Final leaderboard shows complete rankings
- [ ] Match history expandable (accordion or modal)
- [ ] Stats summary accurate
- [ ] Prize distribution clear (if configured)
- [ ] Results page accessible after tournament ends
- [ ] Certificate download works (if P2 implemented)
- [ ] Social share buttons work (Open Graph, Twitter Card)
- [ ] Mobile: Podium stacks vertically, readable

### Technical Implementation

**Templates**:
- Create `templates/tournaments/results.html`
- Enhance `templates/spectator/tournament_detail.html` (completed state)

**Static Assets**:
- Add `static/tournaments/js/results.js` (minimal logic)
- Add `static/tournaments/css/podium.css` (podium visual)
- Optional: Confetti animation (canvas-confetti library, P2)

**Real-Time**: Not required (static results)

### Risks & Mitigation

**Risk 1**: Certificate generation slow (PDF backend)
- **Mitigation**: Show loading spinner, download when ready

**Risk 2**: Large match history (100+ matches)
- **Mitigation**: Pagination or "Load More" button

---

## Phase FE-T5: Organizer Dashboard & Management

**Duration**: 1-2 weeks  
**Priority**: P0 (Critical for MVP)

### Objectives

Implement organizer dashboard and tournament management interfaces.

### Screens & Features

1. **Organizer Dashboard** (`/dashboard/organizer/`)
   - Summary metrics (total tournaments, participants, revenue)
   - Tournament list table (name, game, status, actions)
   - Filters (status, game, date range)
   - "Create Tournament" CTA

2. **Manage Tournament** (`/dashboard/organizer/tournaments/<slug>/`)
   - Tab 1: Overview (status, actions: start, pause, cancel)
   - Tab 2: Participants (list, approve, remove)
   - Tab 3: Matches (list, reschedule, override score, forfeit)
   - Tab 4: Payments (revenue summary, export CSV)
   - Tab 5: Disputes (list, resolve)
   - Tab 6: Health (metrics, P2 optional)

3. **Dispute Resolution** (`/dashboard/organizer/tournaments/<slug>/disputes/<id>/`)
   - Dispute detail (match info, parties, evidence)
   - Timeline
   - Resolution actions (accept A, accept B, override, reject)

### Backend APIs Needed

- ✅ `GET /api/organizer/tournaments/` (Module 9.3)
- ✅ `GET /api/organizer/tournaments/<slug>/` (Module 8.1)
- ✅ `POST /api/organizer/tournaments/<slug>/start/` (Module 8.1)
- ✅ `POST /api/organizer/tournaments/<slug>/pause/` (Module 8.1)
- ✅ `POST /api/organizer/tournaments/<slug>/cancel/` (Module 8.1)
- ✅ `GET /api/organizer/tournaments/<slug>/participants/` (Module 4.2)
- ✅ `POST /api/organizer/tournaments/<slug>/participants/<id>/remove/` (Module 4.2)
- ✅ `GET /api/organizer/tournaments/<slug>/payments/` (Module 3.1)
- ✅ `PATCH /api/organizer/matches/<match_id>/reschedule/` (Module 8.1)
- ✅ `POST /api/organizer/matches/<match_id>/override-score/` (Module 8.1)
- ✅ `GET /api/disputes/<dispute_id>/` (Module 5.5)
- ✅ `POST /api/disputes/<dispute_id>/resolve/` (Module 5.5)
- ⚠️ `GET /api/health/tournament/<slug>/` (Module 2.5, P2)

### Dependencies

- **Backend**: Modules 8.1, 9.3 (Organizer services) complete
- **Backend**: Module 8.1 (Admin lock enforcement) ensures permissions
- **Dashboard**: Existing `templates/dashboard/index.html` (adapt)

### Acceptance Criteria

- [ ] Organizer dashboard shows only if user has organizer role
- [ ] Dashboard metrics accurate
- [ ] Tournament list shows only organizer's tournaments
- [ ] Manage tournament page tabs work correctly
- [ ] Start/pause/cancel actions require confirmation modal
- [ ] Participant management: approve/remove work
- [ ] Match management: reschedule/override/forfeit work
- [ ] Dispute resolution: all actions work (accept, override, reject)
- [ ] Payments tab is read-only (no transaction actions)
- [ ] Health tab shows metrics (if P2 implemented)
- [ ] All actions logged in audit trail (backend handles)
- [ ] Mobile: Tables convert to cards, modals full-screen

### Technical Implementation

**Templates**:
- Create `templates/dashboard/organizer_index.html`
- Create `templates/dashboard/organizer_tournament_detail.html`
- Create `templates/dashboard/organizer_dispute_detail.html`

**Static Assets**:
- Add `static/dashboard/js/organizer.js` (dashboard logic)
- Add `static/tournaments/js/organizer-actions.js` (start, pause, etc.)
- Reuse existing table/modal components

**Real-Time**: Optional (for health metrics, P2)

### Risks & Mitigation

**Risk 1**: Permissions not enforced (frontend shows actions user can't do)
- **Mitigation**: Backend enforces all permissions (Module 8.1), frontend hides based on API response

**Risk 2**: Complex management UI (many tabs, actions)
- **Mitigation**: Progressive disclosure (start with Overview, add tabs incrementally)

**Risk 3**: Dispute resolution requires nuanced judgment
- **Mitigation**: Show all evidence clearly, require reason for all actions

---

## Phase FE-T6: Polish, Animations & Integrations

**Duration**: 3-5 days  
**Priority**: P1 (Important for good UX)

### Objectives

Add polish, animations, and integrate tournament features with existing dashboard/profile.

### Features

1. **Animations**
   - Page transitions (fade-in + slide-up, 300ms)
   - Card hover effects (lift + glow)
   - Button interactions (scale on active)
   - "Live" badge pulse animation
   - Modal enter/exit animations
   - Success states (checkmark animation)
   - Winner celebration (confetti, subtle, P2)

2. **Dashboard Integration**
   - Add "My Tournaments" card to `/dashboard/`
   - Show upcoming matches
   - Show check-in reminders
   - If organizer: Add "My Hosted Tournaments" card

3. **Profile Integration** (P2, optional)
   - Add "Tournament History" section to user profile
   - Show past tournaments, placements, W/L record

4. **Loading & Error States**
   - Skeleton loaders for list views
   - Spinners for button actions
   - Error messages with retry CTAs
   - Empty states for all pages

5. **Accessibility Final Pass**
   - Keyboard navigation audit
   - Screen reader testing
   - Color contrast verification
   - ARIA attributes complete
   - Focus management in modals

### Dependencies

- **All previous phases**: Features implemented
- **Design**: Animation guidelines from PART_4.6

### Acceptance Criteria

- [ ] All animations <300ms, smooth (60fps)
- [ ] `prefers-reduced-motion` respected
- [ ] Dashboard tournament card shows user's tournaments
- [ ] Profile tournament history shows (if P2)
- [ ] All pages have loading states (skeletons/spinners)
- [ ] All pages have error states with retry
- [ ] All pages have empty states
- [ ] Keyboard navigation works on all interactive elements
- [ ] Screen reader announces important updates
- [ ] Color contrast meets WCAG 2.1 AA (4.5:1 minimum)
- [ ] Focus visible on all interactive elements

### Technical Implementation

**CSS Animations**:
- Add `static/tournaments/css/animations.css`
- Use CSS `@keyframes` for all animations
- GPU-accelerated (`transform`, `opacity` only)

**Dashboard Integration**:
- Modify `templates/dashboard/index.html`
- Add tournament cards (reuse existing card component)

**Accessibility**:
- Audit all templates for ARIA attributes
- Add `visually-hidden` class for screen reader text
- Test with NVDA/JAWS screen readers

### Risks & Mitigation

**Risk 1**: Animations cause jank on low-end devices
- **Mitigation**: Test on low-end Android (Chrome DevTools throttling), disable if FPS <30

**Risk 2**: Accessibility issues discovered late
- **Mitigation**: Use automated tools (axe DevTools) throughout development

---

## Phase FE-T7: Refactor Existing Pages (Post-MVP)

**Duration**: 1-2 weeks  
**Priority**: P2 (Nice to have, post-MVP)

### Objectives

Refactor existing non-tournament pages to match new design system and tournament quality.

### Pages to Refactor

1. **Teams Module**
   - `/teams/` (team list)
   - `/teams/<slug>/` (team detail)
   - `/teams/create/` (team creation)
   - Align with tournament design (cards, buttons, colors)

2. **Dashboard**
   - `/dashboard/` (main dashboard)
   - Redesign layout, add more widgets
   - Align with tournament design

3. **Profile**
   - `/profile/<username>/` (user profile)
   - Add tournament history section
   - Align with tournament design

4. **Home Page**
   - `/` (home page)
   - Promote tournaments prominently
   - Align with tournament branding

5. **Community, Arena, CrownStore** (Future)
   - Deferred to later phases (not in scope now)

### Acceptance Criteria

- [ ] Teams pages use design tokens (`tokens.css`)
- [ ] Teams pages match tournament component patterns
- [ ] Dashboard redesigned, more useful
- [ ] Profile shows tournament achievements
- [ ] Home page highlights tournaments
- [ ] All pages responsive, accessible

### Notes

- This phase is **not** part of tournament MVP
- Can be tackled after tournament features stable
- May be split into multiple sub-phases

---

## Build Pipeline Integration (Cross-Cutting)

**When**: Introduce during or after Phase FE-T3  
**Priority**: P1 (Important for maintainability)

### Current State (MVP)

- **CSS**: Tailwind CDN (quick but not optimal)
- **JS**: Vanilla JS, no bundling
- **No Build Step**: Direct file serving

### Recommended Migration (Hybrid Approach)

**Phase 1: Add Build Pipeline**
- Install Node.js dependencies: `npm init`
- Add Tailwind CLI: `npm install -D tailwindcss`
- Configure `tailwind.config.js` (purge unused classes)
- Add build script: `npm run build:css`

**Phase 2: Add Vite (Optional)**
- Install Vite: `npm install -D vite`
- Configure for Django integration
- Bundle JavaScript modules
- TypeScript support (optional)

**Phase 3: Keep Django Templates**
- Do NOT migrate to SPA (React/Vue)
- Keep SSR with Django templates
- Use build pipeline for assets only

### Benefits

- **Performance**: Remove unused Tailwind classes (500KB → 50KB)
- **Maintainability**: Organized JS modules, no global scope pollution
- **Developer Experience**: Hot reload, TypeScript, linting
- **Production-Ready**: Minification, source maps, cache busting

### Implementation Plan

1. **Week 1**: Add Tailwind CLI, build CSS
2. **Week 2**: Add Vite, bundle JS
3. **Week 3**: Migrate existing JS to modules
4. **Week 4**: TypeScript (optional)

### Notes

- Can be done in parallel with Phase FE-T3+
- Does NOT block tournament MVP
- Recommended before Phase FE-T6 (refactoring existing pages)

---

## Testing Strategy (All Phases)

### Unit Tests (JavaScript)

- **Framework**: Jest or Vitest (if Vite added)
- **Coverage**: 70%+ for critical paths
- **Test Files**: `static/tournaments/js/__tests__/`

**Examples**:
- Bracket renderer: Test different tournament formats
- Registration wizard: Test step navigation, validation
- WebSocket client: Test connect, disconnect, reconnect

### Integration Tests (Django)

- **Framework**: pytest + Django test client
- **Coverage**: 80%+ for views
- **Test Files**: `tests/test_tournaments_frontend.py`

**Examples**:
- Tournament list view renders correctly
- Tournament detail view shows correct data
- Registration wizard redirects to success page

### E2E Tests (Optional P2)

- **Framework**: Playwright or Cypress
- **Coverage**: Critical user flows only
- **Test Files**: `e2e/tournaments/`

**Examples**:
- User browses tournaments, registers, views match
- Organizer creates tournament, manages participants

### Visual Regression Tests (Optional P2)

- **Framework**: Percy or Chromatic
- **Coverage**: Key pages (list, detail, bracket, dashboard)
- **Purpose**: Catch unintended visual changes

### Manual Testing Checklist (Each Phase)

**Browsers**:
- [ ] Chrome 90+ (desktop, mobile)
- [ ] Firefox 88+ (desktop, mobile)
- [ ] Safari 14+ (desktop, iOS)
- [ ] Edge 90+ (desktop)

**Devices**:
- [ ] Desktop (1920x1080, 1280x720)
- [ ] Tablet (iPad, 768x1024)
- [ ] Mobile (iPhone SE 360x667, iPhone 12 390x844)

**Accessibility**:
- [ ] Keyboard navigation (Tab, Enter, Esc)
- [ ] Screen reader (NVDA on Windows, VoiceOver on macOS)
- [ ] Color contrast (axe DevTools)
- [ ] Focus visible on all interactive elements

**Performance**:
- [ ] Lighthouse score >85 (Performance, Accessibility)
- [ ] Load time <2s on 3G mobile (tournament list)
- [ ] Real-time updates <3s latency (bracket, leaderboard)

---

## Risk Management

### High-Risk Items

**Risk 1: Backend APIs delayed**
- **Impact**: Critical (blocks all frontend work)
- **Mitigation**: Use mock data, develop frontend independently
- **Owner**: Backend team + Product

**Risk 2: Real-time infrastructure unstable**
- **Impact**: High (live views don't update)
- **Mitigation**: HTMX fallback, exponential backoff, monitoring
- **Owner**: Backend team + DevOps

**Risk 3: Bracket rendering complex**
- **Impact**: Medium (bracket may not render correctly)
- **Mitigation**: Use existing library (d3-bracket), extensive testing
- **Owner**: Frontend team

**Risk 4: Payment integration issues**
- **Impact**: Medium (registration fails for paid tournaments)
- **Mitigation**: External gateway handles transactions (read-only frontend)
- **Owner**: Backend team + Payment gateway vendor

### Medium-Risk Items

**Risk 5: Mobile performance poor**
- **Impact**: Medium (bad UX on mobile)
- **Mitigation**: Lazy load images, pagination, skeleton loaders
- **Owner**: Frontend team

**Risk 6: Accessibility issues discovered late**
- **Impact**: Medium (delays launch or poor experience for disabled users)
- **Mitigation**: Automated tools (axe), manual testing each phase
- **Owner**: Frontend team + QA

---

## Success Metrics (Post-Launch)

### User Engagement

- **Tournament Discovery**: 70%+ of users browse tournaments within first session
- **Registration Rate**: 50%+ of users who view detail page register (if eligible)
- **Completion Rate**: 80%+ of started registrations complete successfully

### Performance

- **Page Load Time**: <2s on 3G mobile (P50)
- **Real-Time Latency**: <3s for live updates (bracket, leaderboard)
- **Error Rate**: <1% of API calls fail

### Quality

- **Lighthouse Scores**: Performance >85, Accessibility >95
- **Bug Rate**: <5 critical bugs per phase
- **Regression Rate**: <2 visual regressions per release

### Business

- **Tournament Creation**: 30%+ increase in tournaments hosted
- **Participant Growth**: 50%+ increase in tournament participants
- **Revenue**: 40%+ increase in tournament entry fees (if monetized)

---

## Timeline Summary

| Phase | Duration | Priority | Start | End |
|-------|----------|----------|-------|-----|
| FE-T1: Discovery & Detail | 1-2 weeks | P0 | Week 1 | Week 2 |
| FE-T2: Registration | 1-2 weeks | P0 | Week 3 | Week 4 |
| FE-T3: Live Views | 2 weeks | P0 | Week 5 | Week 6 |
| FE-T4: Results | 3-5 days | P0 | Week 7 | Week 7 |
| FE-T5: Organizer | 1-2 weeks | P0 | Week 7 | Week 8 |
| FE-T6: Polish | 3-5 days | P1 | Week 9 | Week 9 |
| **MVP Complete** | **~9 weeks** | - | - | **Week 9** |
| FE-T7: Refactor (Post-MVP) | 1-2 weeks | P2 | Week 10+ | Week 11+ |
| Build Pipeline | Ongoing | P1 | Week 5+ | Week 8 |

**Total MVP Timeline**: 8-10 weeks (depending on backend readiness and team velocity)

---

## Open Questions

1. **Q: Should we implement build pipeline before or during Phase FE-T3?**
   - **A**: During FE-T3 (parallel work, doesn't block MVP)

2. **Q: Is certificate download (P2) in MVP scope?**
   - **A**: Optional, can defer to post-MVP if time-constrained

3. **Q: Should we refactor existing pages (FE-T7) or build new features first?**
   - **A**: Build tournament features first (FE-T1 through FE-T6), refactor later

4. **Q: How to handle organizer permissions if user is not organizer?**
   - **A**: Backend validates, frontend hides/disables based on user role (from session/API)

---

**End of Execution Plan**
