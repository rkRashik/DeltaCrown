# Frontend Tournament Testing Strategy

**Date**: November 15, 2025  
**Purpose**: Define QA approach for tournament frontend implementation  
**Status**: Planning Complete

---

## Overview

This document outlines the testing strategy for tournament-focused frontend features. Given the complexity of tournament flows (registration, live updates, organizer controls), we need a multi-layered approach:

1. **Manual Testing** (P0 flows) - Immediate, covers critical paths
2. **Regression Testing** (Existing pages) - Ensures no breakage
3. **E2E Testing** (Future) - Automated user journeys via Playwright/Cypress
4. **Performance Testing** - Load, rendering, and real-time updates
5. **Accessibility Testing** - Keyboard, screen readers, WCAG compliance

---

## 1. Manual Testing (P0 Flows)

### 1.1 Discovery & Registration Flow

**Test Case**: User browses tournaments and registers for one

**Steps**:
1. Navigate to `/tournaments/`
2. Apply filters (Game: eFootball, Status: Registration Open)
3. Search for specific tournament by name
4. Click tournament card → View detail page
5. Verify tournament info loads correctly (name, game, format, prizes, rules, slots)
6. Click "Register" CTA button
7. Select authorized team from dropdown (verify only authorized teams shown)
8. Fill custom fields (if required)
9. Complete payment (if entry fee, test with mock payment gateway)
10. Confirm registration
11. Verify success page shows with confirmation details
12. Check user receives confirmation email (if configured)

**Expected Results**:
- ✅ Filters work correctly, tournament list updates
- ✅ Search returns relevant results
- ✅ Detail page renders correctly with all tournament info
- ✅ Registration wizard shows only authorized teams (backend validation ✅)
- ✅ Custom fields render based on tournament config
- ✅ Payment step skipped if no entry fee
- ✅ Success page displays confirmation number and next steps
- ✅ User redirected to lobby if tournament is active

**Error Cases**:
- ❌ Register for closed tournament → Error page with clear message
- ❌ Register for full tournament → Error page with waitlist option (P2)
- ❌ Register with unauthorized team → Error "You do not have permission to register [Team Name]"
- ❌ Double registration → Error "You are already registered"

---

### 1.2 Tournament Lobby (Participant Hub)

**Test Case**: Registered participant accesses lobby and checks in

**Steps**:
1. Log in as registered participant
2. Navigate to `/tournaments/<slug>/lobby/`
3. Verify participant-only access (non-participants redirected)
4. View tournament overview panel
5. Check countdown timer to tournament start
6. Click "Check In" button (within check-in window)
7. Verify check-in status updates (roster shows checkmark)
8. View participant roster (search/filter by team/player)
9. View match schedule once generated
10. Read organizer announcements
11. Test real-time updates (HTMX polling every 30s)

**Expected Results**:
- ✅ Non-participants redirected to detail page
- ✅ Countdown timer accurate, updates every second
- ✅ Check-in button enabled only within check-in window
- ✅ Roster updates in real-time (shows 28/32 checked in)
- ✅ Match schedule widget shows next match info
- ✅ Announcements panel displays organizer messages
- ✅ Page polls backend every 30s for updates

**Error Cases**:
- ❌ Check in too early → Button disabled, tooltip "Check-in opens [time]"
- ❌ Check in too late → Error "Check-in window closed"
- ❌ Non-participant tries to access → 403 Forbidden or redirect

---

### 1.3 Live Tournament Viewing

**Test Case**: User views live bracket and match details

**Steps**:
1. Navigate to `/tournaments/<slug>/bracket/`
2. Verify bracket tree renders correctly (single elimination, 32 participants)
3. Click match node → View match detail page
4. Verify match header (teams, time, status)
5. View match timeline widget (key events)
6. Check leaderboard updates in real-time
7. Switch between bracket tree and schedule list views

**Expected Results**:
- ✅ Bracket tree SVG renders without overlapping nodes
- ✅ Completed matches show final scores
- ✅ Live matches highlighted with "LIVE" badge
- ✅ Match detail page shows participants, time, status
- ✅ Timeline widget displays key events chronologically
- ✅ Leaderboard updates every 30s via HTMX polling
- ✅ Tree view and list view show same data

**Performance**:
- ⚡ Bracket renders in <2s for 64 participants
- ⚡ Match detail page loads in <1s
- ⚡ Real-time updates do not block UI

---

### 1.4 Match Result Reporting & Disputes

**Test Case**: Participant reports match score and disputes result

**Steps**:
1. Navigate to match detail page after match ends
2. Click "Report Score" button
3. Fill score form (Team A: 3, Team B: 1)
4. Upload screenshot evidence
5. Submit score report
6. Verify "Pending Approval" status shows
7. As opponent, view reported score
8. Click "Dispute" button
9. Fill dispute form (reason: "Incorrect score, we won 3-2")
10. Upload counter-evidence
11. Submit dispute
12. Verify dispute status shows "Under Review"

**Expected Results**:
- ✅ Score report modal renders with form fields
- ✅ Screenshot upload works (drag-drop or file picker)
- ✅ Score submission succeeds, match shows "Pending Approval"
- ✅ Opponent sees reported score and "Dispute" option
- ✅ Dispute form allows evidence upload
- ✅ Dispute submission succeeds, organizer notified
- ✅ 24-hour dispute window enforced (button disabled after)

**Error Cases**:
- ❌ Report score before match ends → Button disabled
- ❌ Submit without screenshot → Validation error "Evidence required"
- ❌ Dispute after 24 hours → Button disabled, tooltip "Dispute window closed"

---

### 1.5 Group Stages (When Backend Ready)

**Test Case**: Organizer configures groups and runs live draw

**Steps**:
1. Log in as organizer
2. Navigate to `/dashboard/organizer/tournaments/<slug>/groups/config/`
3. Configure groups (4 groups, top 2 advance, points: 3/1/0)
4. Click "Generate Groups" → Auto-assign participants
5. OR Click "Live Draw" → Navigate to `/groups/draw/`
6. Click "Draw Next" → Participant randomly assigned to group
7. Repeat until all participants assigned
8. Click "Confirm Draw" → Finalize groups
9. As spectator, navigate to `/tournaments/<slug>/groups/`
10. View group standings (tables per group)
11. Check match results per group

**Expected Results**:
- ✅ Config form saves correctly (groups count, points, advancement)
- ✅ Auto-generate assigns participants evenly across groups
- ✅ Live draw animates participant to group with sound effects
- ✅ Draw broadcast link allows spectators to watch (P1)
- ✅ Group standings page shows tables per group
- ✅ Standings update in real-time as matches complete
- ✅ Highlights advancing teams (green), eliminated teams (red)

**Multi-Game Support**:
- ✅ Test with eFootball (team-based)
- ✅ Test with Valorant (5v5 team-based)
- ✅ Test with PUBG Mobile (solo player)
- ✅ Test with Free Fire (duo/squad)

---

### 1.6 Organizer Tools

**Test Case**: Organizer manages tournament and resolves dispute

**Steps**:
1. Log in as organizer
2. Navigate to `/dashboard/organizer/`
3. View hosted tournaments list
4. Click tournament → View manage page
5. View participants table (search, filter by status)
6. Remove participant (refund payment if applicable)
7. View payments table (track entry fees)
8. View pending match scores
9. Approve match score → Score confirmed, bracket updates
10. OR Override score → Enter correct score, reason
11. Navigate to disputes page
12. View dispute detail (evidence from both parties)
13. Resolve dispute (Accept Team A, Override, Reject)
14. Verify resolution applied, parties notified

**Expected Results**:
- ✅ Organizer dashboard shows all hosted tournaments
- ✅ Manage page loads participant, payment, match data
- ✅ Participant removal works (with confirmation modal)
- ✅ Match approval updates bracket immediately
- ✅ Override score requires reason field
- ✅ Dispute detail shows evidence side-by-side
- ✅ Resolution action updates match status

**Access Control**:
- ❌ Non-organizer tries to access → 403 Forbidden
- ❌ Organizer tries to manage another user's tournament → 403 Forbidden

---

## 2. Regression Testing (Existing Pages)

### 2.1 Non-Tournament Pages (Smoke Test)

**Ensure tournament changes don't break existing pages**:

| Page | URL | Check |
|------|-----|-------|
| Home | `/` | Renders correctly, no JS errors |
| Teams List | `/teams/` | List loads, filters work |
| Team Detail | `/teams/<slug>/` | Detail page renders |
| Dashboard | `/dashboard/` | Dashboard loads, tournament widget appears (FE-T-005) |
| Profile | `/profile/<username>/` | Profile renders |
| Login/Signup | `/accounts/login/` | Auth flows work |

**Expected Results**:
- ✅ No JS errors in console
- ✅ No CSS conflicts (tournament styles isolated)
- ✅ Navigation works (navbar links functional)
- ✅ Dashboard tournament widget integrates smoothly

---

### 2.2 Mobile Responsiveness

**Test all tournament pages on mobile devices (360px width minimum)**:

- [ ] Discovery page (`/tournaments/`)
  - ✅ Cards stack vertically
  - ✅ Filters collapse into dropdown or bottom sheet
  - ✅ Search bar responsive
- [ ] Detail page (`/tournaments/<slug>/`)
  - ✅ Hero image scales correctly
  - ✅ Tabs convert to accordion or scrollable list
  - ✅ CTA button sticky at bottom
- [ ] Registration wizard (`/tournaments/<slug>/register/`)
  - ✅ Form inputs stack vertically
  - ✅ Progress bar visible at top
  - ✅ Back/Next buttons accessible
- [ ] Tournament lobby (`/tournaments/<slug>/lobby/`)
  - ✅ Panels stack vertically
  - ✅ Check-in button sticky at top
  - ✅ Roster converts to card view
- [ ] Bracket view (`/tournaments/<slug>/bracket/`)
  - ✅ Switches to schedule list view on mobile
  - ✅ Tree view scrolls horizontally (if shown)
- [ ] Organizer pages
  - ✅ Tables convert to cards
  - ✅ Actions accessible via dropdown menus

---

## 3. E2E Testing (Future - Playwright/Cypress)

### 3.1 Critical User Journeys

**Automate these flows once manual testing stabilizes**:

#### Journey 1: Register for Tournament
```javascript
test('User can register for tournament with team', async ({ page }) => {
  await page.goto('/tournaments/');
  await page.click('text=eFootball Tournament');
  await page.click('button:has-text("Register")');
  await page.selectOption('select[name="team"]', 'My Team');
  await page.fill('input[name="discord"]', 'user#1234');
  await page.click('button:has-text("Next")');
  await page.click('button:has-text("Confirm")');
  await expect(page).toHaveURL(/\/register\/success/);
  await expect(page.locator('h1')).toContainText('Registration Successful');
});
```

#### Journey 2: Participant Experience
```javascript
test('Participant can check in and view lobby', async ({ page }) => {
  await loginAsParticipant(page);
  await page.goto('/tournaments/my-tournament/lobby/');
  await page.click('button:has-text("Check In")');
  await expect(page.locator('.check-in-status')).toContainText('Checked In');
  await expect(page.locator('.roster-list')).toContainText('28/32');
});
```

#### Journey 3: Organizer Workflow
```javascript
test('Organizer can manage tournament and approve scores', async ({ page }) => {
  await loginAsOrganizer(page);
  await page.goto('/dashboard/organizer/');
  await page.click('text=My Tournament');
  await page.click('tab:has-text("Matches")');
  await page.click('button:has-text("Approve Score")');
  await expect(page.locator('.match-status')).toContainText('Confirmed');
});
```

### 3.2 Test Data Setup

**Seed data for E2E tests**:
- Tournaments (various states: registration open, live, completed)
- Teams with different permission levels (owner, manager, authorized player, regular player)
- Users (participant, organizer, spectator)
- Matches (scheduled, live, completed, disputed)
- Payments (mock gateway responses)

**Fixtures**:
```python
# tests/fixtures/tournament_data.py
@pytest.fixture
def tournament_registration_open(db):
    return Tournament.objects.create(
        name="Test Tournament",
        game=Game.objects.get(slug="efootball"),
        status=Tournament.Status.REGISTRATION_OPEN,
        max_participants=32,
        entry_fee=0,
    )

@pytest.fixture
def authorized_team(db, user):
    team = Team.objects.create(name="Test Team")
    TeamMembership.objects.create(
        team=team,
        profile=user.profile,
        role=TeamMembership.Role.MANAGER,
        can_register_tournaments=True,  # Backend validation ✅
        status=TeamMembership.Status.ACTIVE,
    )
    return team
```

---

## 4. Performance Testing

### 4.1 Page Load Times

**Target**: All pages load in <2 seconds on 3G connection

| Page | Target Load Time | Critical Metrics |
|------|------------------|------------------|
| Discovery | <1.5s | Time to interactive |
| Detail | <1.5s | LCP (hero image) |
| Registration | <1s | Form render time |
| Lobby | <2s | Real-time data fetch |
| Bracket | <2s | SVG rendering (64 participants) |
| Leaderboard | <1s | Table render time |

**Optimization Techniques**:
- Lazy load images (tournament banners)
- Defer non-critical JS (animations, analytics)
- Use CDN for static assets
- Compress CSS/JS (minify, gzip)
- Prefetch critical resources (fonts, icons)

### 4.2 Real-Time Updates

**Test HTMX polling under load**:
- 100 concurrent users on live bracket page
- Polling every 30s for leaderboard updates
- Measure server response time (<200ms target)
- Verify no memory leaks (long-running sessions)

**WebSocket Alternative** (P2):
- If polling causes load issues, consider WebSocket for live updates
- Test WebSocket connection stability (reconnect on disconnect)

### 4.3 Bracket Rendering

**Stress Test**: Render bracket with 128 participants
- SVG should render in <3s
- No overlapping nodes
- Zoom and pan work smoothly (60 FPS)

---

## 5. Accessibility Testing

### 5.1 Keyboard Navigation

**Test all interactive elements**:

- [ ] Discovery page filters (tab through game dropdown, status tabs)
- [ ] Tournament cards (focus visible, enter to navigate)
- [ ] Registration wizard (tab order logical, enter to submit)
- [ ] Modal dialogs (Esc to close, focus trapped)
- [ ] Bracket tree (keyboard navigation between matches)
- [ ] Organizer tables (arrow keys to navigate rows)

**Shortcuts** (P2):
- `Ctrl+K` to open search
- `Ctrl+/` to show keyboard shortcuts modal

### 5.2 Screen Reader Compatibility

**ARIA Labels**:
- Tournament status pills (`aria-label="Status: Registration Open"`)
- Match cards (`aria-label="Match between Team A and Team B"`)
- Check-in button (`aria-label="Check in for tournament"`)
- Dispute button (`aria-label="Dispute match result"`)

**Live Regions**:
- Leaderboard updates (`aria-live="polite"`)
- Match score updates (`aria-live="assertive"`)
- Error messages (`role="alert"`)

### 5.3 Color Contrast

**WCAG AA Compliance**:
- Status pills (green "Open", red "Closed", blue "Live") → Ensure 4.5:1 contrast
- CTA buttons (orange) → 4.5:1 contrast against background
- Bracket match nodes → 3:1 contrast (large text)

**Tools**:
- Use Lighthouse accessibility audit
- Verify with WAVE browser extension

---

## 6. Testing Workflow

### 6.1 Pre-Implementation

1. **Review specs**: Read BACKLOG and SITEMAP for page requirements
2. **Plan test cases**: Write manual test steps based on acceptance criteria
3. **Prepare test data**: Seed tournaments, teams, users

### 6.2 During Implementation

1. **Unit tests** (backend): Ensure APIs return correct data
2. **Manual testing**: Test each page as it's built
3. **Browser testing**: Test in Chrome, Firefox, Safari, Edge
4. **Mobile testing**: Test on real devices (iOS, Android)

### 6.3 Post-Implementation

1. **Regression testing**: Run smoke tests on existing pages
2. **Accessibility audit**: Lighthouse, keyboard nav, screen reader
3. **Performance testing**: Measure load times, optimize bottlenecks
4. **E2E tests** (future): Automate critical journeys

### 6.4 Continuous Testing

- Run E2E tests in CI/CD pipeline (on every commit to main)
- Monitor performance metrics in production (Core Web Vitals)
- Log frontend errors (Sentry, LogRocket)
- User feedback (bug reports, feature requests)

---

## 7. Bug Tracking

**Use GitHub Issues or similar**:

| Priority | Label | Response Time |
|----------|-------|---------------|
| P0 (Critical) | `bug-critical` | Fix within 24 hours |
| P1 (High) | `bug-high` | Fix within 3 days |
| P2 (Medium) | `bug-medium` | Fix within 1 week |
| P3 (Low) | `bug-low` | Fix in next sprint |

**Bug Report Template**:
```markdown
### Bug Description
[Clear description of the issue]

### Steps to Reproduce
1. Navigate to [URL]
2. Click [button]
3. Observe [unexpected behavior]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Environment
- Browser: Chrome 120
- Device: Desktop (Windows 11)
- User Role: Participant
- Tournament State: Live

### Screenshots
[Attach screenshots if applicable]
```

---

## 8. Acceptance Criteria

**Definition of Done** for each FE-T item:

1. ✅ **Functionality**: All features work as specified in BACKLOG
2. ✅ **Manual Testing**: Critical flows tested and pass
3. ✅ **Responsive**: Works on mobile (360px width minimum)
4. ✅ **Accessible**: Keyboard nav, screen reader compatible
5. ✅ **Performance**: Page loads <2s, real-time updates smooth
6. ✅ **Browser Compat**: Works in Chrome, Firefox, Safari, Edge
7. ✅ **Error Handling**: Graceful error messages, no JS errors in console
8. ✅ **Documentation**: README updated if new patterns introduced

---

## Next Steps

1. **Green-light Sprint 1**: Start with FE-T-001 (Tournament List Page)
2. **Manual test FE-T-001**: Follow test case in Section 1.1
3. **Fix bugs**: Address issues found during testing
4. **Iterate**: Move to FE-T-002, repeat testing process
5. **Plan E2E tests**: Once Sprint 1 stable, start writing Playwright tests

---

**Related Documents**:
- [Tournament Backlog](../Backlog/FRONTEND_TOURNAMENT_BACKLOG.md) - Feature specifications
- [Tournament Sitemap](../Screens/FRONTEND_TOURNAMENT_SITEMAP.md) - URL structure
- [Tournament Trace](FRONTEND_TOURNAMENT_TRACE.yml) - Traceability map
- [Implementation Checklist](FRONTEND_TOURNAMENT_CHECKLIST.md) - Task tracking
