# Sprint 4: Leaderboards & Standings Subsystem - Implementation Plan

**Date**: November 15, 2025  
**Sprint**: 4 of Tournament Frontend Implementation  
**Status**: Planning → Implementation → Testing  
**Scope**: FE-T-010 (Tournament Leaderboard Page)

---

## Executive Summary

Sprint 4 implements the **Leaderboards & Standings subsystem** for the DeltaCrown tournament platform. This sprint delivers real-time tournament leaderboard functionality with live ranking updates, participant standings, and comprehensive test coverage.

**Backlog Item**: FE-T-010 - Tournament Leaderboard Page  
**Priority**: P0 (Critical for tournament MVP)  
**Complexity**: Medium  
**Estimated Lines**: ~400 lines (views) + ~350 lines (templates) + ~450 lines (tests)

---

## Feature Identification

### From FRONTEND_TOURNAMENT_BACKLOG.md

**Primary Feature**:
- **FE-T-010**: Tournament Leaderboard Page
  - Priority: P0
  - Persona: Player, Spectator (public)
  - Auth: Not required (public)
  - Real-time: WebSocket + HTMX fallback

**Description** (from backlog):
> Real-time ranking of participants based on wins/losses, points, or tournament format rules. Displays table with rank, team/player, games played, wins, losses, points. Highlights current user's row if logged in as participant. Updates live as matches conclude.

**Related Features** (deferred to future sprints):
- FE-T-013: Group Standings Page (group stage tournaments) - **Not in Sprint 4**
- Dashboard leaderboard widgets - **Not in Sprint 4**
- Global leaderboard (across tournaments) - **Not in Sprint 4**

---

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│  Tournament Leaderboard Page (/tournaments/<slug>/leaderboard/)  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Tournament Header (Name, Game, Status)          │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Leaderboard Table                               │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │ Rank │ Player/Team │ Played │ W │ L │ Pts │  │  │
│  │  ├────────────────────────────────────────────┤  │  │
│  │  │  🥇  │ Team Alpha  │   5    │ 5 │ 0 │ 15  │  │  │
│  │  │  🥈  │ Team Beta   │   5    │ 4 │ 1 │ 12  │  │  │
│  │  │  🥉  │ Team Gamma  │   5    │ 3 │ 2 │  9  │  │  │
│  │  │  4   │ Team Delta  │   5    │ 2 │ 3 │  6  │  │  │
│  │  │ ...  │ ...         │  ...   │...│...│ ... │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  │                                                  │  │
│  │  [Highlight: Current User's Row - if logged in] │  │
│  │  [Empty State: "No standings yet"]              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Real-Time Updates                               │  │
│  │  • WebSocket: Live rank changes                  │  │
│  │  • HTMX Polling: Fallback every 10s              │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Component Breakdown

**1. View Layer** (`apps/tournaments/views/leaderboard.py`):
- `TournamentLeaderboardView` (DetailView-based)
- Query optimization with select_related/prefetch_related
- Context: tournament, standings data, current user participation status

**2. Template Layer** (`templates/tournaments/leaderboard/`):
- `index.html` - Main leaderboard page
- `_leaderboard_table.html` - Standings table partial
- `_leaderboard_row.html` - Individual row component
- `_empty_state.html` - No standings state

**3. URL Layer** (`apps/tournaments/urls.py`):
- `/tournaments/<slug>/leaderboard/` - Main leaderboard page

**4. Real-Time Layer**:
- HTMX polling: `hx-get` with `hx-trigger="every 10s"`
- WebSocket (future enhancement): Live updates
- Toast notifications on rank changes

---

## URL Structure

### From FRONTEND_TOURNAMENT_SITEMAP.md

**Primary URL**:
```
/tournaments/<slug>/leaderboard/
```

**Properties**:
- **Method**: GET
- **Auth**: Not required (public)
- **Personas**: Player, Spectator
- **Navbar Path**: Tournaments → [Tournament Name] → Leaderboard

**Query Parameters** (future enhancement, not in Sprint 4):
- `?group=<num>` - Filter by group (for group stage tournaments)
- `?round=<num>` - Show standings after specific round

---

## Data Sources

### Backend Models Used

**1. Tournament Model** (`apps/tournaments/models/tournament.py`):
- `slug` - URL identifier
- `name` - Tournament name
- `game` - ForeignKey to Game
- `status` - Tournament status (for validation)
- `format` - Tournament format (SINGLE_ELIM, DOUBLE_ELIM, etc.)

**2. Registration Model** (`apps/tournaments/models/registration.py`):
- Participant data (user_id OR team_id)
- Registration status (CONFIRMED participants only)
- Linked to matches for win/loss calculation

**3. Match Model** (`apps/tournaments/models/match.py`):
- Match results for calculating wins/losses
- `winner_id`, `loser_id` - Match outcome
- `status` - COMPLETED matches only
- Linked to participants via `participant1_id`, `participant2_id`

**4. Bracket Model** (`apps/tournaments/models/bracket.py`):
- Bracket structure (optional, for context)
- `is_finalized` - Whether bracket is generated

### Data Calculation Logic

**Leaderboard Metrics**:
- **Rank**: Calculated based on points (DESC), then wins (DESC), then games played (ASC)
- **Games Played**: Count of completed matches for participant
- **Wins**: Count of matches where participant is winner_id
- **Losses**: Count of matches where participant is loser_id
- **Points**: Calculated as `Wins * 3` (standard tournament scoring)

**Query Strategy**:
```python
# Pseudo-code for leaderboard calculation
standings = []
for registration in tournament.registrations.filter(status=Registration.CONFIRMED):
    participant = registration.user or registration.team
    
    completed_matches = Match.objects.filter(
        tournament=tournament,
        status=Match.COMPLETED,
        Q(participant1_id=registration.id) | Q(participant2_id=registration.id)
    )
    
    wins = completed_matches.filter(winner_id=registration.id).count()
    losses = completed_matches.filter(loser_id=registration.id).count()
    games_played = completed_matches.count()
    points = wins * 3
    
    standings.append({
        'rank': 0,  # Calculated after sorting
        'participant': participant,
        'registration': registration,
        'games_played': games_played,
        'wins': wins,
        'losses': losses,
        'points': points,
        'is_current_user': request.user == participant (if user tournament)
    })

# Sort by points DESC, wins DESC, games_played ASC
standings.sort(key=lambda x: (-x['points'], -x['wins'], x['games_played']))

# Assign ranks
for idx, standing in enumerate(standings):
    standing['rank'] = idx + 1
```

---

## Success Criteria

### Functional Requirements

✅ **Must Have**:
1. Display tournament leaderboard with rank, participant, stats
2. Sort by points (DESC), then wins (DESC), then games played (ASC)
3. Highlight current user's row (if logged in as participant)
4. Show top 3 with medal icons (🥇, 🥈, 🥉)
5. Handle empty state (no matches completed yet)
6. Return 404 for non-existent tournaments
7. Public access (no authentication required)
8. Real-time updates via HTMX polling (10s interval)
9. Query optimization (select_related/prefetch_related)
10. Mobile responsive (360px width)

❌ **Explicitly NOT in Sprint 4**:
- Group stage standings (FE-T-013)
- Filtering by round or group
- Advanced statistics (KDA, kill counts, etc.)
- Export to CSV
- Global leaderboard (cross-tournament)
- Social sharing features
- Prize pool integration

### Non-Functional Requirements

**Performance**:
- Page load: < 2s on 3G mobile
- Query count: ≤ 8 queries (including sidebar context processor)
- Database: Use select_related for tournament, game, registrations
- Caching: Not required for Sprint 4

**Accessibility**:
- WCAG 2.1 AA compliance
- Keyboard navigation (tab through table rows)
- Screen reader support (proper table headers, ARIA labels)
- Color contrast: 4.5:1 minimum

**Mobile**:
- Responsive table (horizontal scroll or card view fallback)
- Touch-friendly (44px minimum tap targets)
- Works at 360px width

**Browser Support**:
- Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

---

## Implementation Checklist

### Phase 1: Planning (Current)
- [x] Read FRONTEND_TOURNAMENT_BACKLOG.md
- [x] Read FRONTEND_TOURNAMENT_SITEMAP.md
- [x] Read FRONTEND_TOURNAMENT_FILE_STRUCTURE.md
- [x] Identify FE-T-010 as primary feature
- [x] Create SPRINT_4_LEADERBOARDS_PLAN.md

### Phase 2: Implementation
- [ ] Create `apps/tournaments/views/leaderboard.py`
  - [ ] TournamentLeaderboardView class
  - [ ] Leaderboard calculation logic
  - [ ] Query optimization
- [ ] Create templates in `templates/tournaments/leaderboard/`
  - [ ] `index.html` (main page)
  - [ ] `_leaderboard_table.html` (table partial)
  - [ ] `_leaderboard_row.html` (row component)
  - [ ] `_empty_state.html` (no standings)
- [ ] Update `apps/tournaments/urls.py`
  - [ ] Add leaderboard URL pattern
- [ ] Create CSS: `static/tournaments/css/leaderboard.css` (if needed)

### Phase 3: Testing
- [ ] Create `apps/tournaments/tests/test_leaderboards.py`
  - [ ] test_leaderboard_page_loads
  - [ ] test_leaderboard_404_missing_tournament
  - [ ] test_leaderboard_displays_standings
  - [ ] test_leaderboard_sorted_by_points
  - [ ] test_leaderboard_highlights_current_user
  - [ ] test_leaderboard_handles_no_matches
  - [ ] test_leaderboard_query_optimization
  - [ ] test_leaderboard_medal_icons_top3
  - [ ] test_leaderboard_empty_state
  - [ ] test_leaderboard_mobile_responsive
- [ ] Run all tests: `python manage.py test apps.tournaments --verbosity=2`
- [ ] Fix any failures
- [ ] Verify Sprint 1-3 tests still pass

### Phase 4: Hardening
- [ ] Query optimization review
- [ ] Mobile layout testing (360px)
- [ ] Accessibility audit (keyboard, screen reader)
- [ ] URL alignment check (matches Sitemap)
- [ ] Template structure check (matches File Structure)
- [ ] Browser compatibility testing

### Phase 5: Documentation
- [ ] Create SPRINT_4_LEADERBOARDS_REPORT.md
- [ ] Document any deviations from plan
- [ ] Record test results
- [ ] Note any technical debt

---

## Risk Assessment

### Low Risk
- ✅ Simple data model (no new models needed)
- ✅ Clear backend API (existing models)
- ✅ Established patterns from Sprint 2 & 3

### Medium Risk
- ⚠️ Real-time updates: HTMX polling may cause performance issues with many users
- ⚠️ Query performance: Aggregating match results could be slow for large tournaments
- ⚠️ Mobile table rendering: Wide tables may require horizontal scroll or card view fallback

### Mitigation Strategies
1. **Query Performance**: Use select_related/prefetch_related, test with 100+ participants
2. **Real-Time**: Implement HTMX polling with 10s interval (configurable), defer WebSocket to future
3. **Mobile UX**: Test table rendering at 360px, implement horizontal scroll with sticky rank column

---

## Dependencies

### Backend APIs Required
- **Existing APIs** (already available):
  - `GET /api/tournaments/<slug>/` - Tournament detail (if API exists)
  - Django ORM queries on Tournament, Registration, Match models

- **New APIs** (not required for Sprint 4):
  - Leaderboard will be calculated in Django view layer
  - Future optimization: Dedicated API endpoint for standings calculation

### Frontend Dependencies
- HTMX (existing): For polling updates
- Alpine.js (existing): For interactive components
- Existing CSS components: tables, cards, badges

### Backend Model Verification
All required models exist and were verified in Sprint 3:
- ✅ Tournament model (698 lines)
- ✅ Registration model (402 lines)
- ✅ Match model (507 lines)
- ✅ Bracket model (452 lines)

---

## Timeline Estimate

**Total Effort**: ~6-8 hours (spread across multiple sessions)

- **Planning**: 1 hour (current)
- **View Implementation**: 2 hours
- **Template Creation**: 1.5 hours
- **URL Integration**: 0.5 hours
- **Test Suite**: 2 hours
- **Debugging & Fixes**: 1-2 hours
- **Hardening & Report**: 1 hour

---

## Template Structure

### From FRONTEND_TOURNAMENT_FILE_STRUCTURE.md

**Directory**: `templates/tournaments/leaderboard/`

**Files**:
```
templates/tournaments/leaderboard/
├── index.html                      # Main leaderboard page (extends base.html)
├── _leaderboard_table.html         # Standings table partial
├── _leaderboard_row.html           # Individual row component
└── _empty_state.html               # No standings state
```

### Template Hierarchy

**`index.html`** (Main Page):
```django
{% extends "base.html" %}
{% load static %}

{% block title %}{{ tournament.name }} - Leaderboard{% endblock %}

{% block content %}
<div class="tournament-leaderboard">
  <!-- Tournament Header -->
  <div class="tournament-header">
    <h1>{{ tournament.name }}</h1>
    <span class="game-badge">{{ tournament.game.name }}</span>
    <span class="status-pill">{{ tournament.get_status_display }}</span>
  </div>
  
  <!-- Leaderboard Table or Empty State -->
  {% if standings %}
    {% include "tournaments/leaderboard/_leaderboard_table.html" %}
  {% else %}
    {% include "tournaments/leaderboard/_empty_state.html" %}
  {% endif %}
</div>
{% endblock %}
```

**`_leaderboard_table.html`** (Table Partial):
```django
<div class="leaderboard-table-container" 
     hx-get="{% url 'tournaments:leaderboard' tournament.slug %}" 
     hx-trigger="every 10s"
     hx-swap="outerHTML">
  <table class="leaderboard-table">
    <thead>
      <tr>
        <th>Rank</th>
        <th>Player/Team</th>
        <th>Played</th>
        <th>Wins</th>
        <th>Losses</th>
        <th>Points</th>
      </tr>
    </thead>
    <tbody>
      {% for standing in standings %}
        {% include "tournaments/leaderboard/_leaderboard_row.html" with standing=standing %}
      {% endfor %}
    </tbody>
  </table>
</div>
```

**`_leaderboard_row.html`** (Row Component):
```django
<tr class="leaderboard-row {% if standing.is_current_user %}highlight-current-user{% endif %}">
  <td class="rank">
    {% if standing.rank == 1 %}🥇{% elif standing.rank == 2 %}🥈{% elif standing.rank == 3 %}🥉{% else %}{{ standing.rank }}{% endif %}
  </td>
  <td class="participant">
    <div class="participant-info">
      <img src="{{ standing.participant.avatar_url }}" alt="{{ standing.participant.name }}" class="avatar">
      <span class="name">{{ standing.participant.name }}</span>
    </div>
  </td>
  <td class="games-played">{{ standing.games_played }}</td>
  <td class="wins">{{ standing.wins }}</td>
  <td class="losses">{{ standing.losses }}</td>
  <td class="points">{{ standing.points }}</td>
</tr>
```

**`_empty_state.html`** (No Standings):
```django
<div class="empty-state">
  <img src="{% static 'tournaments/img/empty-state.svg' %}" alt="No standings yet">
  <h3>No Standings Yet</h3>
  <p>The leaderboard will be available once matches begin.</p>
  <a href="{% url 'tournaments:detail' tournament.slug %}" class="btn btn-primary">View Tournament Details</a>
</div>
```

### CSS Structure

**File**: `static/tournaments/css/leaderboard.css` (optional, if needed)

**Key Classes**:
- `.tournament-leaderboard` - Container
- `.leaderboard-table` - Table styles
- `.leaderboard-row` - Row styles
- `.highlight-current-user` - Highlighted row for current user
- `.rank` - Medal icons and rank display
- `.empty-state` - Empty state styling

---

## State Diagrams

### Leaderboard Display States

```
┌─────────────────────────────────────────────────────┐
│  Tournament Leaderboard Page State Machine          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Tournament Not Found]                             │
│         │                                           │
│         ├──→ 404 Error Page                         │
│                                                     │
│  [Tournament Found]                                 │
│         │                                           │
│         ├──→ [No Matches Completed]                 │
│         │         │                                 │
│         │         └──→ Empty State View             │
│         │              "No standings yet"           │
│         │                                           │
│         ├──→ [Matches In Progress]                  │
│         │         │                                 │
│         │         └──→ Leaderboard Table            │
│         │              - Live Updates (HTMX)        │
│         │              - Partial Rankings           │
│         │                                           │
│         └──→ [Tournament Completed]                 │
│                   │                                 │
│                   └──→ Final Leaderboard            │
│                        - Static Rankings            │
│                        - No live updates            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### User Authentication States

```
┌─────────────────────────────────────────────────────┐
│  User Context in Leaderboard                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Anonymous User]                                   │
│         │                                           │
│         └──→ View leaderboard (public)              │
│              - No row highlighting                  │
│              - No personalized features             │
│                                                     │
│  [Authenticated User - Not Participant]             │
│         │                                           │
│         └──→ View leaderboard (public)              │
│              - No row highlighting                  │
│              - Can see all standings                │
│                                                     │
│  [Authenticated User - Participant]                 │
│         │                                           │
│         └──→ View leaderboard with highlight        │
│              - Current user's row highlighted       │
│              - Personalized rank display            │
│              - "Your Rank: #X" indicator            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Real-Time Update Flow

```
┌─────────────────────────────────────────────────────┐
│  HTMX Polling Update Cycle                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  [Initial Page Load]                                │
│         │                                           │
│         └──→ Render leaderboard table               │
│              - Calculate standings                  │
│              - Add hx-trigger="every 10s"           │
│                                                     │
│  [10 seconds later]                                 │
│         │                                           │
│         └──→ HTMX triggers GET request              │
│              - Same URL: /tournaments/<slug>/leaderboard/ │
│              - Server recalculates standings        │
│              - Returns updated HTML                 │
│                                                     │
│  [HTMX Swaps Content]                               │
│         │                                           │
│         └──→ Replace table with new data            │
│              - Smooth swap animation                │
│              - Preserve scroll position             │
│              - Highlight rank changes (optional)    │
│                                                     │
│  [Repeat every 10s while page open]                 │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Edge Cases & Error Handling

### Edge Case 1: Tournament Not Found
**Scenario**: User navigates to `/tournaments/invalid-slug/leaderboard/`  
**Handling**: Return 404 error page  
**Implementation**: Use `get_object_or_404(Tournament, slug=slug)`  
**Test**: `test_leaderboard_404_missing_tournament`

### Edge Case 2: No Matches Completed
**Scenario**: Tournament exists but no matches have been played yet  
**Handling**: Display empty state with message "No standings yet"  
**Implementation**: Check `if standings:` in template, show `_empty_state.html`  
**Test**: `test_leaderboard_empty_state`

### Edge Case 3: Tied Participants
**Scenario**: Two participants have same points and wins  
**Handling**: Sort by games played (ASC), then by registration ID (stable sort)  
**Implementation**: 
```python
standings.sort(key=lambda x: (-x['points'], -x['wins'], x['games_played'], x['registration_id']))
```
**Test**: `test_leaderboard_handles_ties` (bonus test)

### Edge Case 4: Solo vs Team Tournaments
**Scenario**: Leaderboard must handle both user and team participants  
**Handling**: Use `registration.user or registration.team` to get participant  
**Implementation**: 
```python
participant = registration.user if registration.user_id else registration.team
```
**Test**: Covered in `test_leaderboard_displays_standings` (both types)

### Edge Case 5: Tournament in DRAFT Status
**Scenario**: Organizer views leaderboard before tournament is published  
**Handling**: Allow access (public view), show empty state if no matches  
**Implementation**: No status restriction on view  
**Test**: `test_leaderboard_draft_tournament` (bonus test)

### Edge Case 6: Large Tournaments (100+ participants)
**Scenario**: Leaderboard with many participants causes performance issues  
**Handling**: Query optimization with select_related/prefetch_related  
**Implementation**: 
```python
registrations = tournament.registration_set.select_related('user', 'team').filter(status=Registration.CONFIRMED)
```
**Test**: `test_leaderboard_query_optimization`

### Edge Case 7: Match Status Changes During Load
**Scenario**: Match completes while user is viewing leaderboard  
**Handling**: HTMX polling updates leaderboard within 10 seconds  
**Implementation**: Automatic via `hx-trigger="every 10s"`  
**Test**: Manual testing (difficult to unit test timing)

### Edge Case 8: User Leaves Tournament Mid-Competition
**Scenario**: Participant disqualified or removed after playing matches  
**Handling**: Continue showing their stats with "(Disqualified)" indicator  
**Implementation**: Check registration status, add indicator in template  
**Test**: `test_leaderboard_disqualified_participant` (bonus test)

---

## Accessibility Requirements

### WCAG 2.1 AA Compliance

**1. Semantic HTML**:
- Use `<table>` for leaderboard (not divs styled as table)
- Use `<thead>`, `<tbody>`, `<th>`, `<td>` properly
- Use `<caption>` for table title: "Tournament Leaderboard"

**2. ARIA Labels**:
```html
<table class="leaderboard-table" role="table" aria-label="Tournament standings">
  <thead>
    <tr role="row">
      <th role="columnheader" scope="col">Rank</th>
      <th role="columnheader" scope="col">Player/Team</th>
      <!-- ... -->
    </tr>
  </thead>
</table>
```

**3. Keyboard Navigation**:
- Table rows must be focusable with Tab key
- Arrow keys navigate between rows (optional enhancement)
- Enter key on row links to participant profile (future)

**4. Screen Reader Support**:
- Medal emojis must have `aria-label`: `<span aria-label="Gold medal">🥇</span>`
- Current user's row: `<tr aria-current="true">` for highlighted row
- Empty state: Proper heading hierarchy (H3 for "No Standings Yet")

**5. Color Contrast**:
- Highlighted row background: Minimum 4.5:1 contrast ratio
- Text on highlighted row: Ensure readability
- Medal emojis: Supplement with text for colorblind users

**6. Focus Indicators**:
- Visible focus outline on interactive elements
- `:focus-visible` for keyboard-only focus styles

**7. Responsive Tables**:
- On mobile: Horizontal scroll container with `tabindex="0"` for keyboard scroll
- Alternative: Card view for narrow screens (optional)

---

## Mobile Responsiveness

### Breakpoints

**Desktop (≥768px)**:
- Full table layout
- All columns visible
- Standard padding

**Tablet (≥480px, <768px)**:
- Condensed table layout
- Reduce padding
- Abbreviate column headers (P, W, L, Pts)

**Mobile (<480px)**:
- **Option 1**: Horizontal scroll table
  - Sticky rank column (position: sticky)
  - Scrollable content area
  - Touch-friendly (44px minimum tap targets)
  
- **Option 2**: Card view (future enhancement)
  - Stack participants vertically
  - Each card shows rank, name, stats
  - Easier to read on small screens

### Mobile Layout Example

```html
<!-- Mobile: Horizontal scroll wrapper -->
<div class="table-scroll-wrapper" tabindex="0" role="region" aria-label="Scrollable leaderboard table">
  <table class="leaderboard-table mobile">
    <!-- Rank column sticky left -->
    <thead>
      <tr>
        <th class="sticky-col">Rank</th>
        <th>Player/Team</th>
        <th>P</th>
        <th>W</th>
        <th>L</th>
        <th>Pts</th>
      </tr>
    </thead>
    <tbody>
      <!-- Rows scroll horizontally -->
    </tbody>
  </table>
</div>
```

### Touch Interactions

- **Swipe**: Horizontal scroll on table
- **Tap**: Row expands to show more details (future)
- **Pull-to-refresh**: Manual refresh (optional, currently auto-updates)

---

## Testing Strategy

### Test Categories

**1. Unit Tests** (View Logic):
- Leaderboard calculation accuracy
- Sorting algorithm correctness
- Current user detection
- Query optimization

**2. Integration Tests** (View + Template):
- Page rendering
- Context data passing
- Template inheritance
- Partial includes

**3. Functional Tests** (End-to-End):
- Navigation from tournament detail
- HTMX polling behavior (manual)
- Mobile responsive layout (manual)

**4. Performance Tests**:
- Query count (≤8 queries)
- Page load time (<2s)
- Large dataset handling (100+ participants)

### Test Coverage Goals

- **Line Coverage**: ≥95% for views/leaderboard.py
- **Branch Coverage**: ≥90% for conditional logic
- **Template Coverage**: All templates rendered in at least one test

### Test Data Fixtures

**Minimum Test Data**:
- 1 tournament (LIVE status)
- 8 registrations (4 users, 4 teams, all CONFIRMED)
- 12 completed matches (various win/loss combinations)
- 1 authenticated user (participant)

**Edge Case Test Data**:
- Tournament with 0 matches
- Tournament with tied participants
- Tournament with disqualified participants
- Large tournament (100+ registrations)

---

## Implementation Notes

### Code Style

**Python** (PEP 8):
- Class names: PascalCase (`TournamentLeaderboardView`)
- Function names: snake_case (`get_leaderboard_data`)
- Line length: ≤120 characters
- Docstrings: Google style

**Django Templates**:
- Indentation: 2 spaces
- Template tags: `{% load static %}` at top
- Comments: `{# Comment #}` for complex logic

**CSS** (BEM):
- Blocks: `.leaderboard-table`
- Elements: `.leaderboard-table__row`
- Modifiers: `.leaderboard-table--mobile`

### Performance Optimizations

**1. Query Optimization**:
```python
# Bad: N+1 queries
for registration in tournament.registration_set.all():
    participant = registration.user or registration.team  # Extra query each loop

# Good: Eager loading
registrations = tournament.registration_set.select_related('user', 'team').filter(status=Registration.CONFIRMED)
```

**2. Caching** (future):
```python
# Cache leaderboard for 5 seconds (future enhancement)
cache_key = f'leaderboard:{tournament.slug}'
standings = cache.get(cache_key)
if not standings:
    standings = calculate_leaderboard(tournament)
    cache.set(cache_key, standings, timeout=5)
```

**3. Database Indexing** (backend responsibility):
- Index on `Match.winner_id`, `Match.loser_id`
- Index on `Registration.status`
- Composite index on `Match(tournament_id, status)`

---

**End of Part 2/6**

✅ Planning document extended with:
- Template structure (4 files)
- State diagrams (3 flows)
- Edge cases (8 scenarios)
- Accessibility requirements (WCAG 2.1 AA)
- Mobile responsiveness strategy
- Testing strategy details

**Next**: Part 3/6 will implement views and URL patterns.
