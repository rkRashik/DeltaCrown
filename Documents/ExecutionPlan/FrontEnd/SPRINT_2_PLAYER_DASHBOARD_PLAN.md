# Sprint 2: Player Dashboard Subsystem - Implementation Plan

**Date:** November 15, 2025  
**Scope:** Player-facing "My Tournaments" dashboard subsystem  
**Status:** Planning Complete, Ready to Implement

---

## Executive Summary

This sprint implements the **player-facing tournament dashboard subsystem** - allowing logged-in players to view and manage their tournament registrations and matches. 

**Scope Determination:**
Based on analysis of planning documents, the player dashboard subsystem currently consists of:
- **FE-T-005**: My Tournaments Dashboard Widget (P1, Sprint 2)
- **FE-T-007**: Tournament Lobby/Participant Hub (P0, Sprint 2) - **BLOCKED** on backend API

Since FE-T-007 requires new backend APIs that don't exist yet, this sprint will focus on what CAN be implemented with existing backend infrastructure.

---

## Identified Features for Implementation

### ✅ Ready to Implement (Sprint 2)

#### 1. FE-T-005: My Tournaments Dashboard Widget
**Backlog Reference:** Section 1.5  
**Sitemap URL:** Component within `/dashboard/` (existing dashboard page)  
**Priority:** P1  
**Backend APIs:** Use existing Registration model queries

**Description:**  
Dashboard card showing user's registered/active tournaments with quick links.

**User Stories:**
- As a player, I want to see my upcoming tournaments on my dashboard
- As a player, I want to see my tournament status (registered, checked-in, eliminated, winner)
- As a player, I want quick links to tournament detail or lobby

**Implementation:**
- Add tournament card to existing `templates/dashboard/index.html`
- Query: `Registration.objects.filter(user=request.user, is_deleted=False).select_related('tournament', 'tournament__game')`
- Display max 5 tournaments with "View All" link
- Show: tournament name, game badge, status, next match time (if available)

**Components:**
- Dashboard card (reuse existing card pattern)
- Tournament mini-card (compact version)
- Status badge (registered, checked-in, live, eliminated, completed)

---

#### 2. My Tournaments Full Page (Expanded FE-T-005)
**Sitemap URL:** `/dashboard/tournaments/` or `/tournaments/my/`  
**Priority:** P2 (but implementing now as part of subsystem)  
**Backend APIs:** Same as widget, with pagination

**Description:**  
Full-page view of all user's tournament registrations with filters and pagination.

**User Stories:**
- As a player, I want to see ALL my tournament registrations (not just 5)
- As a player, I want to filter by status (active, upcoming, completed)
- As a player, I want to see detailed registration info (team, custom fields, payment status)

**Implementation:**
- New view: `TournamentPlayerDashboardView` (ListView)
- Template: `templates/tournaments/player/my_tournaments.html`
- URL: `/tournaments/my/` (simpler than `/dashboard/tournaments/`)
- Filters: All, Active, Upcoming, Completed
- Pagination: 20 per page

**Query Optimization:**
```python
Registration.objects.filter(
    user=request.user,
    is_deleted=False
).select_related(
    'tournament',
    'tournament__game',
    'tournament__organizer',
    'team'
).prefetch_related(
    'tournament__matches'  # For showing next match
).order_by('-tournament__tournament_start')
```

---

#### 3. My Upcoming Matches View
**Sitemap URL:** `/tournaments/my/matches/` or component within my tournaments  
**Priority:** P1  
**Backend APIs:** Match model queries

**Description:**  
View showing player's upcoming/recent matches across all tournaments.

**User Stories:**
- As a player, I want to see my next matches across all tournaments
- As a player, I want to see opponent, tournament, date/time for each match
- As a player, I want quick access to match lobby/detail

**Implementation:**
- Component within My Tournaments page (tab or section)
- Query matches where user is participant (via Registration → Tournament → Matches)
- Show: tournament name, opponent, date/time, round, status
- Filter: Upcoming, Live, Completed

**Query:**
```python
# Get tournaments where user is registered
user_tournaments = Tournament.objects.filter(
    registrations__user=request.user,
    registrations__is_deleted=False
)

# Get matches in those tournaments involving user's registration
Match.objects.filter(
    tournament__in=user_tournaments,
    # Additional filtering based on match participant logic
).select_related(
    'tournament',
    'tournament__game'
).order_by('scheduled_time')
```

---

### ⏸️ Blocked (Cannot Implement Yet)

#### FE-T-007: Tournament Lobby / Participant Hub
**Status:** BLOCKED - Requires new backend APIs

**Required Backend APIs (Don't Exist):**
- `GET /api/tournaments/<slug>/lobby/` - Participant-only hub data
- `POST /api/tournaments/<slug>/check-in/` - Check-in functionality
- `GET /api/tournaments/<slug>/lobby/roster/` - Participant roster
- `GET /api/tournaments/<slug>/lobby/announcements/` - Organizer announcements

**Decision:** Skip for this sprint, implement when backend APIs are ready.

---

## Technical Implementation Plan

### Phase 1: Data Layer & Views

#### View Classes to Create

1. **`TournamentPlayerDashboardView`** (ListView)
   - File: `apps/tournaments/views/player.py`
   - URL: `/tournaments/my/`
   - Context: `my_tournaments`, filters, pagination
   - Auth: `LoginRequiredMixin`

2. **`TournamentPlayerMatchesView`** (ListView)
   - File: `apps/tournaments/views/player.py`
   - URL: `/tournaments/my/matches/`
   - Context: `my_matches`, filters
   - Auth: `LoginRequiredMixin`

3. **Dashboard Widget Helper**
   - Update: `apps/dashboard/views.py` (or context processor)
   - Add `user_tournaments` to dashboard context
   - Limit to 5 most recent/upcoming

#### URL Routing

```python
# apps/tournaments/urls.py
urlpatterns = [
    # ... existing URLs ...
    
    # Player dashboard URLs
    path('my/', views.TournamentPlayerDashboardView.as_view(), name='my_tournaments'),
    path('my/matches/', views.TournamentPlayerMatchesView.as_view(), name='my_matches'),
]
```

---

### Phase 2: Templates

#### Templates to Create

1. **`templates/tournaments/player/my_tournaments.html`**
   - Extends `base.html`
   - Page title: "My Tournaments"
   - Filter tabs: All, Active, Upcoming, Completed
   - Tournament cards with status badges
   - Pagination

2. **`templates/tournaments/player/my_matches.html`**
   - Extends `base.html`
   - Page title: "My Matches"
   - Match cards with opponent, time, tournament
   - Filter: Upcoming, Live, Completed

3. **`templates/tournaments/player/_tournament_card.html`** (partial)
   - Reusable tournament card for dashboard/my tournaments
   - Shows: name, game, status, CTA button

4. **`templates/tournaments/player/_match_card.html`** (partial)
   - Reusable match card
   - Shows: opponent, tournament, time, round

#### Templates to Update

1. **`templates/dashboard/index.html`**
   - Add "My Tournaments" card section
   - Include widget with 5 latest tournaments
   - "View All" link to `/tournaments/my/`

---

### Phase 3: Navigation Integration

#### Update Global Navigation

1. **User dropdown menu** (already exists in base template)
   - Add "My Tournaments" link
   - Add "My Matches" link (if separate page)

2. **Dashboard sidebar** (if exists)
   - Add "My Tournaments" nav item

---

### Phase 4: Queryset Optimization

**Critical Optimizations:**

1. **My Tournaments Query:**
```python
Registration.objects.filter(
    user=request.user,
    is_deleted=False
).select_related(
    'tournament',              # FK
    'tournament__game',        # FK through tournament
    'tournament__organizer',   # FK through tournament
    'team'                     # FK (nullable)
).annotate(
    # Annotate next match if needed
).order_by('-tournament__tournament_start')
```

2. **My Matches Query:**
```python
# Implementation depends on Match model structure
# Need to determine how participants are linked to matches
```

---

### Phase 5: Testing

#### Test Files to Create

**`apps/tournaments/tests/test_player_dashboard.py`**

Test Cases:
1. `test_my_tournaments_page_loads_for_logged_in_user`
   - Create user, tournaments, registrations
   - Login
   - GET `/tournaments/my/`
   - Assert 200, tournaments in context

2. `test_my_tournaments_redirects_for_anonymous_user`
   - Anonymous GET `/tournaments/my/`
   - Assert 302 redirect to login

3. `test_my_tournaments_filters_by_status`
   - Create active and completed tournaments
   - Test filter query params
   - Assert correct tournaments shown

4. `test_my_tournaments_pagination`
   - Create 25 registrations
   - Assert pagination works (20 per page)

5. `test_dashboard_widget_shows_latest_5_tournaments`
   - Create 10 registrations
   - GET `/dashboard/`
   - Assert only 5 shown in widget

6. `test_my_matches_page_loads`
   - Create matches for user's tournaments
   - Assert matches displayed correctly

---

## Design & UI Considerations

### Status Badges

**Tournament Status:**
- `registered` - Blue "Registered" pill
- `checked_in` - Green "Checked In" pill
- `live` - Orange "Live" pill with pulsing dot
- `eliminated` - Gray "Eliminated" pill
- `completed` - Gray "Completed" pill
- `winner` - Gold "Winner" pill with trophy icon

### Empty States

1. **No Tournaments Registered**
   - Icon: Trophy outline
   - Message: "You haven't registered for any tournaments yet"
   - CTA: "Browse Tournaments" → `/tournaments/`

2. **No Upcoming Matches**
   - Icon: Calendar
   - Message: "No upcoming matches scheduled"
   - Subtitle: "Check back when your tournaments start"

### Mobile Responsiveness

- Cards stack vertically on mobile
- Filters convert to dropdown on narrow screens
- Tournament cards maintain minimum 320px width
- Swipe gestures for filter tabs

---

## Backend Integration Points

### Existing Models Used

1. **Registration Model**
   - `apps/tournaments/models/registration.py`
   - Fields: `user`, `tournament`, `team`, `status`, `registration_data`, `created_at`

2. **Tournament Model**
   - `apps/tournaments/models/tournament.py`
   - Fields: `name`, `slug`, `game`, `status`, `tournament_start`, etc.

3. **Match Model** (for matches view)
   - Need to investigate structure
   - Likely in `apps/tournaments/models/match.py`

### No New Backend APIs Needed

All functionality can be implemented with direct model queries using existing Django ORM.

---

## Known Limitations & Future Work

### Current Sprint Limitations

1. **No Tournament Lobby** (FE-T-007)
   - Blocked on backend API
   - Will show "Lobby Coming Soon" placeholder if needed

2. **Match Details Limited**
   - Match result submission (FE-T-014) blocked on backend
   - Will show basic match info only

3. **No Real-Time Updates**
   - Live status updates require WebSocket (future work)
   - Will use page refresh for now

### Future Enhancements (Not This Sprint)

1. **Filters & Search**
   - Filter by game
   - Search by tournament name
   - Sort by date/status

2. **Calendar Integration**
   - "Add to Calendar" button for matches
   - iCal export

3. **Notifications**
   - Toast notifications for match updates
   - Email reminders

---

## Success Criteria

### Definition of Done

- [x] Planning document created (this document)
- [ ] Views implemented with proper auth
- [ ] Templates created with responsive design
- [ ] Navigation links added
- [ ] Querysets optimized with select_related
- [ ] All tests passing (5+ new tests)
- [ ] No regressions in Sprint 1 tests
- [ ] Manual testing complete (logged-in and anonymous)
- [ ] Empty states working
- [ ] Mobile responsive (360px+)
- [ ] Final report document created

### Test Success Criteria

- All new tests pass (5/5 minimum)
- No regressions in existing tests
- `python manage.py check` passes with no errors
- Pages load without errors for both logged-in and anonymous users

---

## Implementation Timeline

**Estimated Effort:** 4-6 hours

**Phase Breakdown:**
1. Data Layer & Views: 1.5 hours
2. Templates: 1.5 hours
3. Navigation & Integration: 0.5 hours
4. Testing: 1.5 hours
5. Bug fixes & polish: 1 hour

**Order of Implementation:**
1. Create player views module
2. Implement My Tournaments view
3. Create templates
4. Add dashboard widget
5. Implement My Matches view (if time permits)
6. Write tests
7. Manual testing & fixes
8. Final report

---

## Files to Create/Modify

### New Files (7)
- `apps/tournaments/views/player.py` - Player-specific views
- `templates/tournaments/player/my_tournaments.html` - Main page
- `templates/tournaments/player/my_matches.html` - Matches page
- `templates/tournaments/player/_tournament_card.html` - Card partial
- `templates/tournaments/player/_match_card.html` - Card partial
- `templates/tournaments/player/_empty_state.html` - Empty state partial
- `apps/tournaments/tests/test_player_dashboard.py` - Test suite

### Modified Files (3)
- `apps/tournaments/urls.py` - Add new URLs
- `apps/tournaments/views/__init__.py` - Export new views
- `templates/dashboard/index.html` - Add tournament widget

---

## Next Steps

1. ✅ Create this planning document
2. Implement Phase 1: Data Layer & Views
3. Implement Phase 2: Templates
4. Implement Phase 3: Navigation
5. Implement Phase 4: Testing
6. Create final report

**Ready to begin implementation.**
