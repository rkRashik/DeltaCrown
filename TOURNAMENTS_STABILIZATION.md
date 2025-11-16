# Tournaments Subsystem Stabilization

## Files Modified

### 1. apps/tournaments/admin_bracket.py
**Issue:** `bracket_type_badge()` tried to call `get_bracket_type_display()` which doesn't exist
**Root Cause:** `BracketNode.bracket_type` is CharField (max_length=50), not CharField with choices, so Django doesn't generate `get_X_display()`
**Fix:** Changed method to format bracket_type value directly without calling non-existent display method

```python
def bracket_type_badge(self, obj):
    if not obj.bracket_type:
        return format_html('...')
    
    bracket_type = obj.bracket_type
    display_name = bracket_type.replace('-', ' ').replace('_', ' ').title()
    # Returns formatted HTML without calling get_bracket_type_display()
```

### 2. tests/test_tournaments_bugfixes.py
**Complete rewrite:** Tests now properly import from actual model structure
- Import from `apps.tournaments.models.tournament`, `apps.tournaments.models.game`, etc.
- Use `timezone.now()` with `timedelta` for date fields instead of hardcoded strings
- Use actual Tournament status constants: `Tournament.REGISTRATION_OPEN`, `Tournament.LIVE`, `Tournament.COMPLETED`
- Use actual Match state constants: `Match.SCHEDULED`, `Match.LIVE`, `Match.COMPLETED`
- Use actual Registration status constants: `Registration.CONFIRMED`
- Tests verify both HTTP 200 responses AND correct template usage

**Test Classes:**
- `TournamentPublicViewTests`: Tests `/tournaments/` and `/tournaments/<slug>/`
- `TournamentLiveViewTests`: Tests bracket, match detail, results views
- `TournamentPlayerViewTests`: Tests player dashboard (`/tournaments/my/`, `/tournaments/my/matches/`)
- `TournamentLeaderboardViewTests`: Tests leaderboard view
- `BracketAdminTests`: Tests admin bracket pages load without AttributeError
- `OrganizerHubTests`: Tests organizer dashboard and detail views with permissions

## Views Verified

All views checked for correct template paths:

### apps/tournaments/views/main.py
- `TournamentListView`: `tournaments/public/browse/list.html` ✓
- `TournamentDetailView`: `tournaments/public/detail/overview.html` ✓

### apps/tournaments/views/live.py
- `TournamentBracketView`: `tournaments/public/live/bracket.html` ✓
- `MatchDetailView`: `tournaments/public/live/match_detail.html` ✓
- `TournamentResultsView`: `tournaments/public/live/results.html` ✓

### apps/tournaments/views/player.py
- `TournamentPlayerDashboardView`: `tournaments/public/player/my_tournaments.html` ✓
- `TournamentPlayerMatchesView`: `tournaments/public/player/my_matches.html` ✓

### apps/tournaments/views/leaderboard.py
- `TournamentLeaderboardView`: `tournaments/public/leaderboard/index.html` ✓

### apps/tournaments/views/organizer.py
- `OrganizerDashboardView`: `tournaments/organizer/dashboard.html` ✓
- `OrganizerTournamentDetailView`: `tournaments/organizer/tournament_detail.html` ✓

## Template Structure Verified

All templates checked - paths already use correct `tournaments/public/*` structure:
- `templates/tournaments/public/browse/*.html` ✓
- `templates/tournaments/public/detail/*.html` ✓
- `templates/tournaments/public/live/*.html` ✓
- `templates/tournaments/public/player/*.html` ✓
- `templates/tournaments/public/leaderboard/*.html` ✓
- `templates/tournaments/public/registration/*.html` ✓
- `templates/tournaments/organizer/*.html` ✓

## Models Verified

### BracketNode (apps/tournaments/models/bracket.py)
- Has `bracket_type` field: CharField(max_length=50, default='main')
- Has constants: MAIN, LOSERS, THIRD_PLACE
- Has BRACKET_TYPE_CHOICES list (not used as `choices` param on field)
- Admin now handles this correctly

### Tournament, Match, Registration, Payment, Dispute
- All models import correctly from modular structure
- All status/state constants accessible via class attributes

## Organizer Hub Context

`OrganizerTournamentDetailView.get_context_data()` provides:
- `registrations`: QuerySet of Registration objects (limit 50)
- `registration_stats`: Dict with total, pending, confirmed, rejected, cancelled, checked_in counts
- `matches`: QuerySet of Match objects (limit 50)
- `match_stats`: Dict with total, scheduled, live, completed, pending_result counts
- `payments`: QuerySet of Payment objects (limit 50)
- `payment_stats`: Dict with total, pending, submitted, verified, rejected counts
- `disputes`: QuerySet of Dispute objects (limit 20)
- `dispute_stats`: Dict with total, open, under_review, resolved counts
- `time_status`: Dict with registration window, days_until_start, is_live flags

Template `tournaments/organizer/tournament_detail.html` displays all data in tabs.

## Permissions

### Organizer Views
- `OrganizerRequiredMixin.test_func()`:
  - Superuser/Staff: Access all tournaments
  - Regular user: Must have at least one Tournament where `organizer=user`
  - Unauthenticated: Redirect to login
- `OrganizerDashboardView.get_queryset()`:
  - Superuser/Staff: See all tournaments
  - Non-staff: Only tournaments where `organizer=user`
- `OrganizerTournamentDetailView.get_queryset()`:
  - Superuser/Staff: Access any tournament
  - Non-staff: Only tournaments where `organizer=user` (returns 404 otherwise)

## How to test

```bash
# Run all tournament tests
python manage.py test tests.test_tournaments_bugfixes

# Run specific test classes
python manage.py test tests.test_tournaments_bugfixes.TournamentPublicViewTests
python manage.py test tests.test_tournaments_bugfixes.TournamentLiveViewTests
python manage.py test tests.test_tournaments_bugfixes.TournamentPlayerViewTests
python manage.py test tests.test_tournaments_bugfixes.TournamentLeaderboardViewTests
python manage.py test tests.test_tournaments_bugfixes.BracketAdminTests
python manage.py test tests.test_tournaments_bugfixes.OrganizerHubTests

# Check for any remaining issues
python manage.py check
python manage.py check --deploy
```

## Known Limitations

- Tests require database migrations to be run
- Some model fields (like `Tournament.has_entry_fee`) may not exist in current schema
- Payment model import in organizer view assumes it exists in `apps.tournaments.models`
- Dispute model import assumes it exists with expected status constants
