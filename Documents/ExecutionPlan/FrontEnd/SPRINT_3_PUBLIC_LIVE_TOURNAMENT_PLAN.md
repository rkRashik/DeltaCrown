# Sprint 3: Public Live Tournament Experience - Implementation Plan

**Date:** November 15, 2025  
**Sprint:** Sprint 3 - Public Live Tournament Subsystem  
**Status:** Planning Complete - Ready for Implementation  
**Developer:** AI Assistant

---

## Executive Summary

Sprint 3 implements the complete **Public Live Tournament Experience** subsystem, covering the live tournament journey from bracket visualization through match watching to final results display. This subsystem is accessible to all users (authenticated and anonymous) and provides the core spectator and participant experience during and after tournament execution.

### Scope

Implements three interconnected FE-T items:

- **FE-T-008**: Live Bracket View - Tournament structure visualization
- **FE-T-009**: Match Watch / Match Detail Page - Individual match viewing
- **FE-T-018**: Tournament Results Page - Post-tournament final standings

### Success Criteria

✅ All three pages fully implemented and integrated  
✅ URLs match existing tournament URL structure  
✅ Query optimizations (select_related, prefetch_related)  
✅ Mobile-responsive (360px+)  
✅ Comprehensive test coverage (minimum 12 tests)  
✅ No regressions to Sprint 1 or Sprint 2  
✅ Accessible (WCAG 2.1 AA compliance)  
✅ Performance: <5 database queries per page (excluding counts)

---

## FE-T Items Analysis

### FE-T-008: Live Bracket / Schedule View

**Backlog Reference:** Section 2.1  
**Priority:** P0  
**Target Personas:** Player, Spectator

**Requirements:**
- Visual bracket display (tree structure for elimination formats)
- Match list view (fallback for complex formats)
- Round-by-round navigation
- Match status indicators (scheduled, live, completed)
- Winner/loser highlighting
- Mobile: horizontal scroll or stacked view
- Support formats: Single-elim, Double-elim, Round-robin, Swiss, Group Stage

**Backend APIs:**
- `GET /api/tournaments/{slug}/bracket/` - Bracket structure
- `GET /api/tournaments/{slug}/matches/` - Match list
- WebSocket: `spectator_ws.js` (out of scope - no real-time in Sprint 3)

**Edge Cases:**
- Bracket not yet generated (tournament in registration phase)
- Incomplete bracket (tournament cancelled mid-way)
- No matches yet (newly started tournament)
- Large brackets (>64 participants) - pagination or zoom controls

---

### FE-T-009: Match Watch / Match Detail Page

**Backlog Reference:** Section 2.2  
**Priority:** P0  
**Target Personas:** Player (participant), Spectator

**Requirements:**
- Match header: tournament name, round, status
- Participants: names, logos, scores
- Match state: scheduled, live, completed, forfeit
- Timeline: match events (start, score updates, end)
- Lobby info: Game lobby details (for participants only)
- Actions: Report score, dispute (participant-only, out of scope for Sprint 3)
- Stream link: Embed if provided (P2 - placeholder only)

**Backend APIs:**
- `GET /api/matches/{match_id}/` - Match detail
- `POST /api/matches/{match_id}/report-score/` (out of scope - Sprint 4)
- `POST /api/matches/{match_id}/dispute/` (out of scope - Sprint 4)

**Edge Cases:**
- Match with no participants assigned yet
- Match with bye (one participant null)
- Forfeit match (winner by forfeit)
- Disputed match (show dispute indicator)

---

### FE-T-018: Tournament Results Page

**Backlog Reference:** Section 3.1  
**Priority:** P0  
**Target Personas:** Player, Spectator

**Requirements:**
- Winners section: Podium visual (1st, 2nd, 3rd)
- Final leaderboard: Complete rankings table
- Match history: All matches with scores
- Stats summary: Total matches, participants, duration
- Prize distribution: Winner prizes (if configured)
- Links: Back to tournament detail, bracket, individual matches

**Backend APIs:**
- `GET /api/tournaments/{slug}/results/` - Final results
- Returns: TournamentResult model + rankings + match history

**Edge Cases:**
- No winner determined yet (tournament still live)
- Tournament cancelled before completion
- Tie for placements (show tie indicator)
- No third place match (some formats)

---

## URL Structure

Based on existing `apps/tournaments/urls.py` and Sprint 1/2 patterns:

```python
# Sprint 3 URLs (to be added)
path('<slug:slug>/bracket/', ..., name='bracket'),         # FE-T-008
path('<slug:slug>/matches/<int:match_id>/', ..., name='match_detail'),  # FE-T-009
path('<slug:slug>/results/', ..., name='results'),         # FE-T-018
```

**Full Tournament URL Hierarchy:**
```
/tournaments/                           # Sprint 1: List
/tournaments/<slug>/                    # Sprint 1: Detail
/tournaments/<slug>/register/           # Sprint 1: Registration
/tournaments/<slug>/bracket/            # Sprint 3: Bracket ✨ NEW
/tournaments/<slug>/matches/<id>/       # Sprint 3: Match Detail ✨ NEW
/tournaments/<slug>/results/            # Sprint 3: Results ✨ NEW
/tournaments/my/                        # Sprint 2: My Tournaments
/tournaments/my/matches/                # Sprint 2: My Matches
```

**Navigation Flow:**
```
Tournament Detail
    ├─> Bracket View  ────> Match Detail
    ├─> Match Detail (direct link)
    └─> Results Page ────> Match Detail
```

---

## Template Structure

Following File Structure & Trace conventions:

```
templates/tournaments/
├── live/                              # Sprint 3: Live views
│   ├── bracket.html                   # FE-T-008: Bracket page
│   ├── match_detail.html              # FE-T-009: Match detail
│   ├── results.html                   # FE-T-018: Results page
│   └── _partials/
│       ├── _bracket_round.html        # Bracket round section
│       ├── _bracket_match_card.html   # Compact match card for bracket
│       ├── _match_header.html         # Match header component
│       ├── _match_participants.html   # Participant vs display
│       ├── _match_timeline.html       # Match events timeline
│       ├── _results_podium.html       # Winners podium
│       └── _results_leaderboard.html  # Final rankings table
```

**Template Inheritance:**
- All extend `base.html`
- Reuse existing components from Sprint 1/2 where applicable
- Match status badges from Sprint 2 `_match_card.html`
- Tournament header pattern from Sprint 1 `detail.html`

---

## View Architecture

### Bracket View

```python
class TournamentBracketView(DetailView):
    """
    FE-T-008: Live Bracket View
    
    URL: /tournaments/<slug>/bracket/
    Template: tournaments/live/bracket.html
    """
    model = Tournament
    template_name = 'tournaments/live/bracket.html'
    context_object_name = 'tournament'
    
    def get_queryset(self):
        return Tournament.objects.filter(
            is_deleted=False
        ).select_related(
            'game',
            'organizer',
            'bracket'  # OneToOne relationship
        ).prefetch_related(
            Prefetch(
                'matches',
                queryset=Match.objects.filter(
                    is_deleted=False
                ).select_related(
                    'tournament'
                ).order_by('round_number', 'match_number')
            )
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Organize matches by round
        matches_by_round = {}
        for match in tournament.matches.all():
            round_num = match.round_number
            if round_num not in matches_by_round:
                matches_by_round[round_num] = []
            matches_by_round[round_num].append(match)
        
        context['matches_by_round'] = matches_by_round
        context['bracket'] = tournament.bracket if hasattr(tournament, 'bracket') else None
        context['bracket_available'] = hasattr(tournament, 'bracket') and tournament.bracket is not None
        
        return context
```

### Match Detail View

```python
class MatchDetailView(DetailView):
    """
    FE-T-009: Match Watch / Detail Page
    
    URL: /tournaments/<slug>/matches/<int:match_id>/
    Template: tournaments/live/match_detail.html
    """
    model = Match
    template_name = 'tournaments/live/match_detail.html'
    context_object_name = 'match'
    pk_url_kwarg = 'match_id'
    
    def get_queryset(self):
        # Filter by tournament slug for security
        tournament_slug = self.kwargs.get('slug')
        return Match.objects.filter(
            tournament__slug=tournament_slug,
            is_deleted=False
        ).select_related(
            'tournament',
            'tournament__game',
            'tournament__organizer'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.object
        
        # Add tournament context
        context['tournament'] = match.tournament
        
        # Participant details (user lookup for display)
        context['participant1'] = self._get_participant_details(match.participant1_id)
        context['participant2'] = self._get_participant_details(match.participant2_id)
        
        # Check if current user is participant
        if self.request.user.is_authenticated:
            context['is_participant'] = match.participant1_id == self.request.user.id or \
                                       match.participant2_id == self.request.user.id
        else:
            context['is_participant'] = False
        
        return context
    
    def _get_participant_details(self, user_id):
        if not user_id:
            return None
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
```

### Results View

```python
class TournamentResultsView(DetailView):
    """
    FE-T-018: Tournament Results Page
    
    URL: /tournaments/<slug>/results/
    Template: tournaments/live/results.html
    """
    model = Tournament
    template_name = 'tournaments/live/results.html'
    context_object_name = 'tournament'
    
    def get_queryset(self):
        return Tournament.objects.filter(
            is_deleted=False,
            status=Tournament.COMPLETED  # Only show results for completed tournaments
        ).select_related(
            'game',
            'organizer',
            'result',  # OneToOne TournamentResult
            'result__winner',
            'result__winner__user',
            'result__runner_up',
            'result__runner_up__user' if 'result__runner_up' else None,
            'result__third_place',
            'result__third_place__user' if 'result__third_place' else None
        ).prefetch_related(
            Prefetch(
                'registrations',
                queryset=Registration.objects.filter(
                    is_deleted=False
                ).select_related('user').order_by('-created_at')
            ),
            Prefetch(
                'matches',
                queryset=Match.objects.filter(
                    is_deleted=False,
                    state=Match.COMPLETED
                ).select_related('tournament').order_by('round_number', 'match_number')
            )
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Results
        context['result'] = tournament.result if hasattr(tournament, 'result') else None
        context['has_results'] = hasattr(tournament, 'result') and tournament.result is not None
        
        # All matches
        context['completed_matches'] = tournament.matches.filter(state=Match.COMPLETED)
        
        # Leaderboard (all registrations ordered by placement)
        context['leaderboard'] = tournament.registrations.all()
        
        return context
```

---

## Data Models Used

### Existing Models (No Changes)

**Tournament** (`apps/tournaments/models/tournament.py`)
- Used by all three views
- Fields: slug, name, status, game, organizer, tournament_start, tournament_end

**Match** (`apps/tournaments/models/match.py`)
- Used by Bracket and Match Detail views
- Fields: round_number, match_number, participant1_id, participant2_id, state, scores, scheduled_time, winner_id, loser_id

**Bracket** (`apps/tournaments/models/bracket.py`)
- Used by Bracket view
- Fields: format, seeding_method, bracket_structure (JSONB), is_generated

**TournamentResult** (`apps/tournaments/models/result.py`)
- Used by Results view
- Fields: winner, runner_up, third_place, determination_method, placements (JSONB)

**Registration** (`apps/tournaments/models/registration.py`)
- Used by Results view for leaderboard
- Fields: user, status, seed, slot_number

---

## State Machine & Business Logic

### Tournament States (from Tournament model)

```python
DRAFT = 'draft'                      # Not visible in public views
PENDING_APPROVAL = 'pending_approval'  # Not visible in public views
PUBLISHED = 'published'              # Bracket: "Not Ready"
REGISTRATION_OPEN = 'registration_open'  # Bracket: "Not Ready"
REGISTRATION_CLOSED = 'registration_closed'  # Bracket: "Generating..."
LIVE = 'live'                        # Bracket: Active, Match Detail: Active
COMPLETED = 'completed'              # Results: Available
CANCELLED = 'cancelled'              # All views: Show cancelled state
ARCHIVED = 'archived'                # Same as completed
```

### Bracket Availability Logic

```python
def bracket_available(tournament):
    """Determine if bracket can be displayed"""
    if tournament.status in ['draft', 'pending_approval', 'published', 'registration_open']:
        return False  # Too early
    if tournament.status == 'cancelled':
        return False  # Tournament cancelled
    if not hasattr(tournament, 'bracket') or not tournament.bracket:
        return False  # Bracket not generated
    if not tournament.bracket.is_generated:
        return False  # Generation in progress
    return True
```

### Match States (from Match model)

```python
SCHEDULED = 'scheduled'     # Badge: Gray "Upcoming"
CHECK_IN = 'check_in'       # Badge: Yellow "Check-In"
READY = 'ready'             # Badge: Blue "Ready"
LIVE = 'live'               # Badge: Red "Live" (pulsing)
PENDING_RESULT = 'pending_result'  # Badge: Orange "Pending"
COMPLETED = 'completed'     # Badge: Green "Completed"
FORFEIT = 'forfeit'         # Badge: Gray "Forfeit"
DISPUTED = 'disputed'       # Badge: Red "Disputed"
CANCELLED = 'cancelled'     # Badge: Gray "Cancelled"
```

---

## Component Reuse Strategy

### From Sprint 1 (Tournament Detail)

- Tournament header section (name, game, organizer, dates)
- Status badges (published, live, completed)
- Breadcrumb navigation
- Back to tournament link

### From Sprint 2 (My Tournaments / My Matches)

- Match card component (`_match_card.html`) - adapt for bracket
- Match status badges (scheduled, live, completed)
- Empty state messages
- Filter UI patterns (if needed)

### New Components (Sprint 3)

- Bracket round visualization (`_bracket_round.html`)
- Compact match card for bracket (`_bracket_match_card.html`)
- Match timeline (`_match_timeline.html`)
- Winners podium (`_results_podium.html`)
- Results leaderboard table (`_results_leaderboard.html`)

---

## Query Optimization Strategy

### Key Optimizations

1. **select_related()**: For FK/OneToOne relationships
   - `tournament__game`
   - `tournament__organizer`
   - `tournament__bracket`
   - `tournament__result`

2. **prefetch_related()**: For reverse FK/M2M
   - `matches` (with filter for is_deleted=False)
   - `registrations` (with select_related('user'))

3. **Prefetch()**: For filtered prefetches
   - Matches filtered by state
   - Registrations filtered by status

### Target Query Counts

- **Bracket View**: ~4 queries (tournament, matches, bracket, counts)
- **Match Detail**: ~3 queries (match, tournament, participants)
- **Results View**: ~5 queries (tournament, result, matches, registrations, counts)

---

## Mobile Responsiveness

### Breakpoints

- **Desktop**: 1024px+ - Full bracket tree, side-by-side layouts
- **Tablet**: 768px-1023px - Simplified bracket, stacked components
- **Mobile**: 360px-767px - List view, vertical stacking, horizontal scroll for wide tables

### Bracket Mobile Strategy

**Option 1**: Horizontal scroll (preferred for elimination brackets)
```html
<div class="overflow-x-auto">
  <!-- SVG or table-based bracket -->
</div>
```

**Option 2**: List view toggle (fallback for complex formats)
```html
<div class="bracket-view-toggle">
  <button data-view="tree">Tree View</button>
  <button data-view="list">List View</button>
</div>
```

### Match Detail Mobile

- Stacked participant cards (vertical)
- Full-width score display
- Timeline as vertical list
- Action buttons sticky at bottom (if participant)

### Results Mobile

- Podium: vertical stack (1st, 2nd, 3rd)
- Leaderboard: horizontal scroll
- Match history: card view instead of table

---

## Accessibility Requirements

### WCAG 2.1 AA Compliance

**Keyboard Navigation:**
- All interactive elements focusable (Tab order)
- Bracket navigation via arrow keys (if interactive)
- Skip links for long bracket views

**Screen Readers:**
- Semantic HTML (`<table>` for brackets if table-based, or `role="tree"` for SVG)
- Alt text for all images/icons
- ARIA labels for status badges
- ARIA live regions for score updates (future WebSocket integration)

**Color Contrast:**
- All text: minimum 4.5:1 contrast
- Status badges: AA compliant colors
- Winner/loser indicators: not color-only (use icons + text)

**Focus Indicators:**
- Visible focus outlines (2px solid)
- High contrast focus states

---

## Security Considerations

### Authorization

- **Bracket View**: Public (no auth required)
- **Match Detail**: Public (no auth required)
  - Lobby info: Visible only to participants (check user_id)
  - Actions (score reporting): Participants only (future Sprint 4)
- **Results View**: Public (no auth required)

### Data Filtering

- All queries filter `is_deleted=False`
- Match detail view validates tournament slug matches match.tournament
- No leaking of deleted/draft tournaments in public views

### Input Validation

- No user input in Sprint 3 (GET requests only)
- URL parameter validation (slug format, match_id integer)
- 404 errors for invalid slugs/IDs

---

## Edge Cases & Error Handling

### Bracket View

| Edge Case | Behavior |
|-----------|----------|
| Bracket not generated yet | Show "Bracket not available" message with expected date |
| Tournament in registration phase | Show "Registration in progress" with participant count |
| Tournament cancelled | Show cancelled badge + message |
| Empty bracket (no matches) | Show "No matches scheduled yet" |
| Large bracket (>64 participants) | Implement zoom controls OR list view fallback |

### Match Detail

| Edge Case | Behavior |
|-----------|----------|
| Match not found | 404 error page |
| Match with no participants | Show TBD placeholders |
| Bye match (one participant null) | Show "Bye" for empty slot |
| Forfeit match | Show forfeit badge + explanation |
| Disputed match | Show dispute indicator (no dispute details - Sprint 4) |

### Results View

| Edge Case | Behavior |
|-----------|----------|
| Tournament not completed | Redirect to bracket OR show "Tournament in progress" |
| No TournamentResult record | Show "Results not finalized yet" |
| Tie for placement | Show tied rank indicator |
| No third place match | Don't display third place section |

---

## Testing Strategy

### Test Module

File: `apps/tournaments/tests/test_sprint3_live_tournament_views.py`

### Test Cases (Minimum 12)

**Bracket View (4 tests)**
1. `test_bracket_page_loads_for_live_tournament`
2. `test_bracket_page_shows_not_ready_for_early_tournament`
3. `test_bracket_view_404_for_invalid_slug`
4. `test_bracket_view_organizes_matches_by_round`

**Match Detail (4 tests)**
5. `test_match_detail_page_loads`
6. `test_match_detail_404_for_invalid_match_id`
7. `test_match_detail_validates_tournament_slug`
8. `test_match_detail_shows_lobby_info_to_participants_only`

**Results View (4 tests)**
9. `test_results_page_loads_for_completed_tournament`
10. `test_results_page_redirects_for_live_tournament`
11. `test_results_page_shows_winner_podium`
12. `test_results_page_shows_final_leaderboard`

**Query Optimization (Bonus)**
13. `test_bracket_view_uses_prefetch_related`
14. `test_match_detail_uses_select_related`

---

## Implementation Timeline

### Phase 1: Foundation (Setup)
- Create view classes (bracket, match_detail, results)
- Add URL patterns to `apps/tournaments/urls.py`
- Create base templates (no styling yet)

### Phase 2: Bracket View
- Implement `TournamentBracketView`
- Create `bracket.html` template
- Create bracket partials (`_bracket_round.html`, `_bracket_match_card.html`)
- Handle edge cases (not generated, cancelled)

### Phase 3: Match Detail
- Implement `MatchDetailView`
- Create `match_detail.html` template
- Create match partials (`_match_header.html`, `_match_participants.html`, `_match_timeline.html`)
- Participant lookup logic

### Phase 4: Results Page
- Implement `TournamentResultsView`
- Create `results.html` template
- Create results partials (`_results_podium.html`, `_results_leaderboard.html`)
- Winners display logic

### Phase 5: Testing
- Write all 12+ test cases
- Run tests, fix failures
- Validate query counts

### Phase 6: Hardening
- Mobile responsive check (360px)
- Accessibility audit
- Query optimization verification
- Cross-browser testing (Chrome, Firefox, Safari)
- Sprint 1 & 2 regression testing

---

## Known Limitations & Future Enhancements

### Limitations (Sprint 3)

1. **No Real-Time Updates**
   - No WebSocket integration (planned for future)
   - Scores don't update live during matches
   - Manual refresh required

2. **No Score Reporting**
   - Match detail shows scores but no submission UI
   - Player actions (report, dispute, forfeit) deferred to Sprint 4

3. **No Interactive Bracket**
   - Bracket is read-only display
   - No zoom/pan controls for large brackets
   - No bracket printing/export

4. **No Streaming Integration**
   - Stream link placeholder only
   - No embedded video player

5. **Limited Match History**
   - Timeline shows basic events only
   - No detailed play-by-play

### Future Enhancements (Sprint 4+)

1. **Real-Time Updates (Module 7.1)**
   - WebSocket integration for live scores
   - Auto-refresh match status
   - Live leaderboard updates

2. **Player Actions (Module 5.1)**
   - Score reporting UI
   - Dispute submission form
   - Forfeit confirmation

3. **Advanced Bracket Features**
   - Interactive bracket (zoom, pan)
   - Bracket export (PDF, image)
   - Print-friendly bracket view

4. **Match History Details**
   - Detailed timeline events
   - Play-by-play stats (if game supports)
   - Match replay link (if available)

5. **Streaming Integration (Module 7.2)**
   - Embedded Twitch/YouTube player
   - Multi-stream support
   - VOD playback

---

## Success Metrics

### Feature Completeness

- ✅ Bracket view displays all tournament matches organized by round
- ✅ Match detail shows participants, scores, status, tournament context
- ✅ Results page shows winners, podium, final leaderboard
- ✅ All three views handle edge cases gracefully
- ✅ Mobile responsive at 360px+

### Code Quality

- ✅ All views use LoginRequiredMixin or public access correctly
- ✅ Query optimizations (select_related, prefetch_related) implemented
- ✅ <5 queries per page (excluding counts)
- ✅ DRY principles (reused components from Sprint 1/2)
- ✅ PEP 8 compliant

### Testing

- ✅ Minimum 12 test cases written
- ✅ All tests passing
- ✅ Test coverage >80% for new views
- ✅ Edge cases covered

### User Experience

- ✅ Clear navigation between views
- ✅ Consistent design with Sprint 1/2
- ✅ Accessible (WCAG 2.1 AA)
- ✅ Fast page loads (<2s)
- ✅ No JavaScript errors

### Integration

- ✅ No regressions in Sprint 1 tests
- ✅ No regressions in Sprint 2 tests
- ✅ URLs follow existing pattern
- ✅ Templates follow file structure

---

## Appendix: Bracket Visualization Approaches

### Option A: Table-Based Bracket (Recommended for Sprint 3)

**Pros:**
- Semantic HTML (`<table>`)
- Easy to style with CSS
- Screen reader friendly
- No JavaScript required

**Cons:**
- Limited visual customization
- Harder to do complex layouts (double-elim)

**Example Structure:**
```html
<table class="bracket-table">
  <thead>
    <tr>
      <th>Round 1</th>
      <th>Round 2</th>
      <th>Finals</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Match 1</td>
      <td rowspan="2">Match 5</td>
      <td rowspan="4">Match 7 (Finals)</td>
    </tr>
    <tr>
      <td>Match 2</td>
    </tr>
    <!-- etc -->
  </tbody>
</table>
```

### Option B: SVG-Based Bracket (Future Enhancement)

**Pros:**
- Full visual control
- Scales infinitely
- Professional appearance
- Can add animations

**Cons:**
- Requires JavaScript for interactivity
- More complex accessibility (ARIA labels needed)
- Harder to maintain

**Implementation:** Deferred to Sprint 4+

### Option C: List View (Fallback)

**Pros:**
- Simplest implementation
- Works for all formats
- Mobile-friendly

**Cons:**
- Not visually appealing
- Loses bracket structure

**Use Case:** Fallback for complex formats or mobile view

---

## Appendix: Backend API Contracts

### Bracket API (Module 3.1)

```
GET /api/tournaments/{slug}/bracket/
```

**Response:**
```json
{
  "id": 123,
  "format": "single-elimination",
  "seeding_method": "ranked",
  "is_generated": true,
  "bracket_structure": {
    "rounds": [
      {"round_number": 1, "round_name": "Quarter Finals", "matches": 4},
      {"round_number": 2, "round_name": "Semi Finals", "matches": 2},
      {"round_number": 3, "round_name": "Finals", "matches": 1}
    ]
  },
  "created_at": "2025-11-15T10:00:00Z"
}
```

### Matches API (Module 3.1)

```
GET /api/tournaments/{slug}/matches/
```

**Response:**
```json
{
  "count": 7,
  "results": [
    {
      "id": 456,
      "round_number": 1,
      "match_number": 1,
      "participant1_id": 789,
      "participant1_name": "Player1",
      "participant2_id": 790,
      "participant2_name": "Player2",
      "state": "completed",
      "participant1_score": 2,
      "participant2_score": 1,
      "winner_id": 789,
      "scheduled_time": "2025-11-16T14:00:00Z"
    }
  ]
}
```

### Results API (Module 5.1)

```
GET /api/tournaments/{slug}/results/
```

**Response:**
```json
{
  "id": 99,
  "tournament": 123,
  "winner": {
    "id": 789,
    "user": {"id": 1, "username": "Player1"},
    "placement": 1
  },
  "runner_up": {
    "id": 790,
    "user": {"id": 2, "username": "Player2"},
    "placement": 2
  },
  "third_place": {
    "id": 791,
    "user": {"id": 3, "username": "Player3"},
    "placement": 3
  },
  "determination_method": "normal",
  "placements": [...],
  "finalized_at": "2025-11-17T18:00:00Z"
}
```

---

## Sign-Off

**Planning Complete:** ✅  
**Ready for Implementation:** ✅  
**Estimated Implementation Time:** 6-8 hours  
**Estimated Lines of Code:** ~2000 (views, templates, tests)

**Next Step:** Begin Phase 1 - Foundation (view classes + URL patterns)
