# Phase UP 5: Career Tab Backend Wiring - Audit Report

**Date:** January 18, 2026  
**Scope:** Backend integration for Career Tab without touching other tabs  
**Purpose:** Identify data sources, recommend implementations, and provide safe integration paths

---

## Executive Summary

This audit identifies the backend sources and integration points needed to wire the Career Tab to real data. The Career Tab requires:

1. **Tournament Tier** - Currently NOT stored in Tournament model; recommend adding to `Tournament.attributes` JSON field
2. **Matches Played Count** - Query `Match` model filtered by user/team and game, count `COMPLETED` and `FORFEIT` states
3. **Team Ranking** - Use existing `TeamRanking` model in `apps/leaderboards` with ELO-based ranking system
4. **Public Profile Context** - Inject Career Tab data via `public_profile_view()` in `apps/user_profile/views/public_profile_views.py`

---

## 1. Tournament Tier Source

### Current State

**Finding:** The `Tournament` model does NOT have a dedicated tier/level/category field.

**File:** `apps/tournaments/models/tournament.py` (Lines 1-1011)

**Existing Fields:**
- `name` (CharField) - Tournament name
- `format` (CharField with choices) - single_elimination, double_elimination, round_robin, swiss, group_playoff
- `participation_type` (CharField) - team or solo
- `status` (CharField) - draft, published, registration_open, live, completed, etc.
- `is_official` (BooleanField) - Official DeltaCrown tournament flag
- `is_featured` (BooleanField) - Featured on homepage flag
- **`game.category`** (CharField on related Game model) - Game category (MOBA, FPS, etc.) - Line 125

**Game Model Fields:**
```python
# apps/tournaments/models/tournament.py:125
category = models.CharField(max_length=50, blank=True, null=True, help_text='Game category (MOBA, FPS, etc.)')
```

### Recommendation: Add Tournament Tier

#### Option A: Use JSON Field (Recommended - No Migration)
Store tier in the existing `Tournament` attributes or custom_data JSON field if available.

**Pros:**
- No database migration required
- Flexible schema
- Won't break existing pages

**Implementation:**
```python
# In Tournament model method or service
def get_tier(self):
    """Get tournament tier from attributes JSON."""
    return self.attributes.get('tier', 'OPEN')  # Default to OPEN

# Example tier values
TIER_CHOICES = ['OPEN', 'SILVER', 'GOLD', 'PLATINUM', 'DIAMOND', 'CROWN']
```

#### Option B: Add Database Field (Requires Migration)
Add a dedicated `tier` field to Tournament model.

**Pros:**
- Queryable via ORM filters
- Proper data validation
- Better for sorting/filtering

**Cons:**
- Requires migration
- Could affect existing tournament creation flows
- Need to update admin, forms, serializers

**Implementation:**
```python
# apps/tournaments/models/tournament.py (add to Tournament class)
tier = models.CharField(
    max_length=20,
    choices=[
        ('OPEN', 'Open'),
        ('SILVER', 'Silver'),
        ('GOLD', 'Gold'),
        ('PLATINUM', 'Platinum'),
        ('DIAMOND', 'Diamond'),
        ('CROWN', 'Crown'),
    ],
    default='OPEN',
    blank=True,
    db_index=True,
    help_text='Tournament skill tier/division'
)
```

**Migration Impact:**
- Add field with default value
- Backfill existing tournaments to 'OPEN' tier
- Update tournament creation forms
- Update tournament list/detail templates
- Update API serializers

#### Option C: Use Related TournamentTemplate (If Exists)
Check if `TournamentTemplate` model exists and use tier from template.

**Finding:** Not found in current audit scope. Tournament model does not have a `template` FK field.

### Recommended Approach: **Option A (JSON Field)**

For Phase UP 5, use the JSON field approach to avoid migrations and potential breakage:

```python
# In career_tab_service.py or tournament serializer
def get_tournament_tier(tournament):
    """
    Get tournament tier from attributes or infer from is_official/is_featured.
    
    Tier logic:
    - Crown: is_official=True and is_featured=True
    - Diamond: is_official=True
    - Gold: Large prize pool (if available)
    - Silver: Medium size
    - Open: Default
    """
    # Check JSON attributes first
    if hasattr(tournament, 'attributes') and tournament.attributes:
        tier = tournament.attributes.get('tier')
        if tier:
            return tier.upper()
    
    # Fallback inference
    if tournament.is_official and tournament.is_featured:
        return 'CROWN'
    elif tournament.is_official:
        return 'DIAMOND'
    else:
        return 'OPEN'
```

---

## 2. Matches Played Count Per Game

### Current State

**File:** `apps/tournaments/models/match.py` (Lines 1-580)

**Match Model Fields:**
```python
class Match(SoftDeleteModel, TimestampedModel):
    # Participants (IntegerField for external references)
    participant1_id = models.PositiveIntegerField(...)  # Team ID or User ID
    participant2_id = models.PositiveIntegerField(...)  # Team ID or User ID
    
    # Match state
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default=SCHEDULED
    )
    
    # States
    SCHEDULED = 'scheduled'
    CHECK_IN = 'check_in'
    READY = 'ready'
    LIVE = 'live'
    PENDING_RESULT = 'pending_result'
    COMPLETED = 'completed'      # ✅ Count this
    DISPUTED = 'disputed'
    FORFEIT = 'forfeit'          # ✅ Count this
    CANCELLED = 'cancelled'      # ❌ Do NOT count
    
    # Winner tracking
    winner_id = models.PositiveIntegerField(...)
    loser_id = models.PositiveIntegerField(...)
    
    # Related tournament
    tournament = models.ForeignKey('tournaments.Tournament', ...)
```

### Matches Played Logic

#### For SOLO Tournaments

**Query Pattern:**
```python
from django.db.models import Q
from apps.tournaments.models import Match

def count_user_matches_for_game(user_id, game_slug):
    """
    Count completed matches for a user in a specific game.
    
    Args:
        user_id: User primary key
        game_slug: Game identifier (e.g., 'valorant')
    
    Returns:
        int: Total matches played (completed or forfeited)
    """
    return Match.objects.filter(
        # User is participant1 OR participant2
        Q(participant1_id=user_id) | Q(participant2_id=user_id),
        # Tournament game matches
        tournament__game__slug=game_slug,
        # Only count finalized matches
        state__in=[Match.COMPLETED, Match.FORFEIT]
    ).count()
```

**States to Count:**
- ✅ `COMPLETED` - Match finished with result
- ✅ `FORFEIT` - Match ended due to forfeit (still counts as played)
- ❌ `CANCELLED` - Match cancelled (does NOT count)
- ❌ `DISPUTED` - Still in dispute (does NOT count until resolved)
- ❌ `PENDING_RESULT` - Awaiting result submission (does NOT count yet)

#### For TEAM Tournaments

**Query Pattern:**
```python
def count_team_matches_for_game(team_id, game_slug):
    """
    Count completed matches for a team in a specific game.
    
    Args:
        team_id: Team primary key
        game_slug: Game identifier
    
    Returns:
        int: Total team matches played
    """
    return Match.objects.filter(
        Q(participant1_id=team_id) | Q(participant2_id=team_id),
        tournament__game__slug=game_slug,
        tournament__participation_type='team',  # Verify it's team tournament
        state__in=[Match.COMPLETED, Match.FORFEIT]
    ).count()
```

**User → Team Mapping:**
```python
from apps.teams.models import TeamMembership

def get_user_team_for_game(user, game_slug):
    """
    Get user's active team for a specific game.
    
    Returns:
        Team instance or None
    """
    membership = TeamMembership.objects.filter(
        user=user,
        team__game=game_slug,
        status='ACTIVE'  # Or TeamMembership.Status.ACTIVE
    ).select_related('team').first()
    
    return membership.team if membership else None
```

### Service Function Signature

**File:** `apps/user_profile/services/career_tab_service.py` (recommended location)

```python
class CareerTabService:
    @staticmethod
    def get_matches_played_count(user_profile, game):
        """
        Count total matches played by user for a specific game.
        
        Handles both SOLO and TEAM tournaments:
        - SOLO: Count matches where user is participant
        - TEAM: Count matches where user's team is participant
        
        Args:
            user_profile: UserProfile instance
            game: Game instance
        
        Returns:
            int: Total matches played (completed or forfeited)
        """
        from django.db.models import Q
        from apps.tournaments.models import Match
        from apps.teams.models import TeamMembership
        
        user = user_profile.user
        game_slug = game.slug
        
        # Count SOLO matches
        solo_matches = Match.objects.filter(
            Q(participant1_id=user.id) | Q(participant2_id=user.id),
            tournament__game__slug=game_slug,
            tournament__participation_type='solo',
            state__in=[Match.COMPLETED, Match.FORFEIT]
        ).count()
        
        # Count TEAM matches
        team_matches = 0
        active_membership = TeamMembership.objects.filter(
            user=user,
            team__game=game_slug,
            status='ACTIVE'
        ).select_related('team').first()
        
        if active_membership:
            team_id = active_membership.team.id
            team_matches = Match.objects.filter(
                Q(participant1_id=team_id) | Q(participant2_id=team_id),
                tournament__game__slug=game_slug,
                tournament__participation_type='team',
                state__in=[Match.COMPLETED, Match.FORFEIT]
            ).count()
        
        return solo_matches + team_matches
```

### Alternative: Use UserStats Model (Cached)

**File:** `apps/leaderboards/models.py` (Lines 200-280)

```python
class UserStats(models.Model):
    """Pre-computed stats per user per game."""
    user = models.ForeignKey(User, ...)
    game_slug = models.CharField(max_length=100, db_index=True)
    matches_played = models.IntegerField(default=0)  # ✅ Use this
    matches_won = models.IntegerField(default=0)
    matches_lost = models.IntegerField(default=0)
    # ... more fields
```

**Usage:**
```python
def get_matches_played_from_stats(user, game_slug):
    """Get cached matches played from UserStats."""
    from apps.leaderboards.models import UserStats
    
    try:
        stats = UserStats.objects.get(user=user, game_slug=game_slug)
        return stats.matches_played
    except UserStats.DoesNotExist:
        return 0
```

**Pros:**
- Fast (pre-computed)
- No complex queries

**Cons:**
- Requires UserStats to be kept up-to-date via signals/events
- May not include team matches (depends on implementation)

**Recommendation:** Use **Match query** for accuracy, cache result in service if needed.

---

## 3. Team Ranking Source

### Current State

**File:** `apps/leaderboards/models.py` (Lines 350-430)

```python
class TeamRanking(models.Model):
    """
    Team ranking/ELO data for a specific game.
    
    Reference: Phase 8, Epic 8.3 - Team Ranking System
    """
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name="team_rankings")
    game_slug = models.CharField(max_length=100, db_index=True)
    
    # ELO rating system
    elo_rating = models.IntegerField(default=1200)
    peak_elo = models.IntegerField(default=1200)
    
    # Match record (denormalized)
    games_played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    
    # Ranking position (computed)
    rank = models.IntegerField(null=True, blank=True)  # 1 = top team
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["-elo_rating"]
        constraints = [
            models.UniqueConstraint(fields=["team", "game_slug"], name="unique_team_game_ranking")
        ]
```

### Tier System

**File:** `apps/leaderboards/models.py` (Lines 837-855) & `apps/tournament_ops/dtos/analytics.py` (Lines 442-485)

```python
# Tier boundaries
BRONZE: 0-1199
SILVER: 1200-1599
GOLD: 1600-1999
DIAMOND: 2000-2399
CROWN: 2400+

class TierBoundaries:
    @staticmethod
    def calculate_tier(elo_or_mmr: int) -> str:
        if elo_or_mmr >= 2400:
            return "crown"
        elif elo_or_mmr >= 2000:
            return "diamond"
        elif elo_or_mmr >= 1600:
            return "gold"
        elif elo_or_mmr >= 1200:
            return "silver"
        else:
            return "bronze"
```

### Get Current Team Ranking

**Service Function:**
```python
class CareerTabService:
    @staticmethod
    def get_team_ranking(user_profile, game):
        """
        Get user's current team ranking for a specific game.
        
        Args:
            user_profile: UserProfile instance
            game: Game instance
        
        Returns:
            dict or None: {
                'team': Team instance,
                'rank': int (position, 1 = top),
                'elo_rating': int,
                'tier': str ('bronze', 'silver', 'gold', 'diamond', 'crown'),
                'wins': int,
                'losses': int,
                'games_played': int
            }
        """
        from apps.teams.models import TeamMembership
        from apps.leaderboards.models import TeamRanking
        from apps.tournament_ops.dtos.analytics import TierBoundaries
        
        # Get user's active team for this game
        membership = TeamMembership.objects.filter(
            user=user_profile.user,
            team__game=game.slug,
            status='ACTIVE'
        ).select_related('team').first()
        
        if not membership:
            return None
        
        team = membership.team
        
        # Get team ranking
        try:
            ranking = TeamRanking.objects.get(team=team, game_slug=game.slug)
            
            return {
                'team': team,
                'rank': ranking.rank,
                'elo_rating': ranking.elo_rating,
                'tier': TierBoundaries.calculate_tier(ranking.elo_rating),
                'wins': ranking.wins,
                'losses': ranking.losses,
                'games_played': ranking.games_played,
            }
        except TeamRanking.DoesNotExist:
            # Team has no ranking yet
            return {
                'team': team,
                'rank': None,
                'elo_rating': 1200,  # Default ELO
                'tier': 'bronze',
                'wins': 0,
                'losses': 0,
                'games_played': 0,
            }
```

**Alternative: Use TeamRankingAdapter**

**File:** `apps/tournament_ops/adapters/team_ranking_adapter.py` (Lines 44-200)

```python
from apps.tournament_ops.adapters.team_ranking_adapter import TeamRankingAdapter

adapter = TeamRankingAdapter()
ranking_dto = adapter.get_team_ranking(team_id=team.id, game_slug=game.slug)

if ranking_dto:
    # ranking_dto.elo_rating, ranking_dto.rank, etc.
    pass
```

### Rank Calculation

**Current Implementation:** `TeamRanking.rank` is a nullable field that gets computed via queries.

**File:** `apps/tournament_ops/adapters/team_ranking_adapter.py` (Lines 203-230)

```python
def recalculate_ranks_for_game(self, game_slug: str) -> int:
    """
    Recalculate rank positions for all teams in a game.
    
    Orders teams by ELO rating (descending) and assigns rank=1,2,3...
    Updates TeamRanking.rank field for all teams.
    
    Returns:
        int: Number of teams updated
    """
    from apps.leaderboards.models import TeamRanking
    
    rankings = TeamRanking.objects.filter(
        game_slug=game_slug
    ).order_by('-elo_rating', 'created_at')
    
    for idx, ranking in enumerate(rankings, start=1):
        ranking.rank = idx
    
    TeamRanking.objects.bulk_update(rankings, ['rank'])
    return len(rankings)
```

**Usage in Career Tab:**
```python
# If rank is None, compute on-the-fly
if ranking.rank is None:
    # Count how many teams have higher ELO
    rank = TeamRanking.objects.filter(
        game_slug=game.slug,
        elo_rating__gt=ranking.elo_rating
    ).count() + 1
else:
    rank = ranking.rank
```

---

## 4. Public Profile View Context Injection

### Current State

**File:** `apps/user_profile/views/public_profile_views.py`

**Function:** `public_profile_view(request, username)` (Line 83)

**Existing Career Context:**
```python
# Line 448-453
from apps.user_profile.services.career_context import build_career_context, get_game_passports_for_career

career_data = build_career_context(user_profile, is_owner=permissions.get('is_owner', False))
context.update(career_data)  # Adds current_teams, team_history, career_timeline, has_teams

# Add game passports preview for Career tab (top 3)
context['career_passports'] = get_game_passports_for_career(profile_user, limit=3)
```

**Existing Context Keys:**
- `career_data` (dict from `build_career_context()`)
- `career_passports` (list of GameProfile instances)
- `current_teams` (via career_data)
- `team_history` (via career_data)
- `career_timeline` (via career_data)
- `has_teams` (boolean via career_data)

### Safe Integration Path

#### Step 1: Add Career Tab Enhanced Context

**Location:** After Line 453 in `public_profile_view()`

```python
# PHASE UP 5: Enhanced Career Tab Context
from apps.user_profile.services.career_tab_service import CareerTabService

# Get linked games for game selector
linked_games = []
all_passports = GameProfile.objects.filter(
    user=profile_user,
    visibility='PUBLIC'
).select_related('game').order_by('-is_primary', '-is_pinned', '-last_updated')

for passport in all_passports:
    linked_games.append({
        'game': passport.game,
        'game_slug': passport.game.slug,
        'passport': passport,
    })

context['career_linked_games'] = linked_games

# Get primary game for initial load
primary_game = user_profile.primary_game or (linked_games[0]['game'] if linked_games else None)

if primary_game:
    # Load full career summary for primary game
    career_summary = {
        'matches_played': CareerTabService.get_matches_played_count(user_profile, primary_game),
        'team_ranking': CareerTabService.get_team_ranking(user_profile, primary_game),
        'tournament_history': CareerTabService.get_tournament_history(user_profile, primary_game),
        'team_history': CareerTabService.get_team_affiliation_history(user_profile, primary_game),
    }
    context['career_summary'] = career_summary
    context['career_selected_game'] = primary_game
else:
    context['career_summary'] = None
    context['career_selected_game'] = None
```

#### Step 2: Create AJAX Endpoint for Game Switching

**File:** `apps/user_profile/views/public_profile_views.py` (add new function)

```python
def career_tab_data_api(request: HttpRequest, username: str) -> JsonResponse:
    """
    AJAX endpoint for loading Career Tab data for a specific game.
    
    GET /@username/career-data/?game=valorant
    
    Returns JSON with matches played, team ranking, tournament history.
    """
    from django.http import JsonResponse
    from apps.user_profile.services.career_tab_service import CareerTabService
    from apps.games.models import Game
    
    # Get user
    try:
        profile_user = User.objects.get(username=username)
        user_profile = profile_user.profile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        return JsonResponse({'error': 'User not found'}, status=404)
    
    # Get game from query param
    game_slug = request.GET.get('game')
    if not game_slug:
        return JsonResponse({'error': 'game parameter required'}, status=400)
    
    try:
        game = Game.objects.get(slug=game_slug)
    except Game.DoesNotExist:
        return JsonResponse({'error': 'Game not found'}, status=404)
    
    # Build career data
    career_data = {
        'matches_played': CareerTabService.get_matches_played_count(user_profile, game),
        'team_ranking': CareerTabService.get_team_ranking(user_profile, game),
        'tournament_history': CareerTabService.get_tournament_history(user_profile, game),
        'team_history': CareerTabService.get_team_affiliation_history(user_profile, game),
    }
    
    # Serialize team_ranking (convert Team instance to dict)
    if career_data['team_ranking']:
        ranking = career_data['team_ranking']
        ranking['team'] = {
            'id': ranking['team'].id,
            'name': ranking['team'].name,
            'tag': ranking['team'].tag,
            'slug': ranking['team'].slug,
        }
    
    return JsonResponse({'success': True, 'data': career_data})
```

**URL Pattern:**
```python
# apps/user_profile/urls.py
path('@<str:username>/career-data/', career_tab_data_api, name='career_tab_data_api'),
```

#### Step 3: Template Integration

**File:** `templates/user_profile/profile/tabs/_tab_career.html` (or similar)

**Game Selector:**
```django
{% if career_linked_games %}
<div class="game-selector">
    {% for item in career_linked_games %}
    <button class="game-btn" data-game-slug="{{ item.game_slug }}" onclick="loadCareerForGame('{{ item.game_slug }}')">
        <img src="{{ item.game.icon.url }}" alt="{{ item.game.name }}">
        <span>{{ item.game.name }}</span>
    </button>
    {% endfor %}
</div>
{% endif %}
```

**Matches Played Display:**
```django
{% if career_summary %}
<div class="stat-card">
    <div class="stat-value">{{ career_summary.matches_played }}</div>
    <div class="stat-label">Matches Played</div>
</div>
{% endif %}
```

**Team Ranking Display:**
```django
{% if career_summary.team_ranking %}
<div class="ranking-card">
    <div class="team-name">{{ career_summary.team_ranking.team.name }}</div>
    <div class="rank">Rank #{{ career_summary.team_ranking.rank|default:"Unranked" }}</div>
    <div class="elo">{{ career_summary.team_ranking.elo_rating }} ELO</div>
    <div class="tier tier-{{ career_summary.team_ranking.tier }}">{{ career_summary.team_ranking.tier|title }}</div>
</div>
{% endif %}
```

**JavaScript for AJAX Loading:**
```javascript
function loadCareerForGame(gameSlug) {
    const username = document.querySelector('[data-username]').dataset.username;
    
    fetch(`/@${username}/career-data/?game=${gameSlug}`)
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                updateCareerDisplay(data.data);
            }
        })
        .catch(err => console.error('Failed to load career data:', err));
}

function updateCareerDisplay(careerData) {
    // Update matches played
    document.querySelector('.matches-played').textContent = careerData.matches_played;
    
    // Update team ranking
    if (careerData.team_ranking) {
        const ranking = careerData.team_ranking;
        document.querySelector('.team-name').textContent = ranking.team.name;
        document.querySelector('.rank').textContent = `Rank #${ranking.rank || 'Unranked'}`;
        document.querySelector('.elo').textContent = `${ranking.elo_rating} ELO`;
        document.querySelector('.tier').textContent = ranking.tier.toUpperCase();
        document.querySelector('.tier').className = `tier tier-${ranking.tier}`;
    }
    
    // Update tournament history (loop and render)
    // ... similar pattern
}
```

---

## 5. Implementation Checklist

### Phase 1: Service Layer (No Breaking Changes)

- [ ] Create `apps/user_profile/services/career_tab_service.py`
- [ ] Implement `get_matches_played_count(user_profile, game)`
- [ ] Implement `get_team_ranking(user_profile, game)`
- [ ] Implement `get_tournament_history(user_profile, game)` (existing or new)
- [ ] Add unit tests for service methods

### Phase 2: View Layer (Safe Injection)

- [ ] Update `public_profile_view()` to add `career_linked_games`
- [ ] Update `public_profile_view()` to add `career_summary` for primary game
- [ ] Create `career_tab_data_api(request, username)` for AJAX
- [ ] Add URL pattern for career data API
- [ ] Test that existing tabs still work (Overview, Activity, Settings)

### Phase 3: Template Layer (Career Tab Only)

- [ ] Update `_tab_career.html` with game selector
- [ ] Add matches played display
- [ ] Add team ranking display with tier badges
- [ ] Add JavaScript for game switching (AJAX)
- [ ] Add loading states and error handling

### Phase 4: Tournament Tier (Optional - Future)

- [ ] Add `tier` field to Tournament model (or use JSON)
- [ ] Update tournament creation forms
- [ ] Backfill existing tournaments
- [ ] Update career tab to display tournament tier

---

## 6. Data Flow Diagram

```
User clicks Career Tab
    ↓
Template loads with career_linked_games (from public_profile_view context)
    ↓
JavaScript renders game selector buttons
    ↓
User clicks game button (e.g., VALORANT)
    ↓
JavaScript: fetch('/@username/career-data/?game=valorant')
    ↓
Backend: career_tab_data_api() receives request
    ↓
CareerTabService.get_matches_played_count(user_profile, game)
    ├─ Query Match model WHERE participant1_id=user.id OR participant2_id=user.id
    ├─ Filter by game_slug and state IN (COMPLETED, FORFEIT)
    └─ Return count
    ↓
CareerTabService.get_team_ranking(user_profile, game)
    ├─ Query TeamMembership to get user's active team for game
    ├─ Query TeamRanking to get team's ELO and rank
    ├─ Calculate tier from ELO using TierBoundaries.calculate_tier()
    └─ Return ranking dict
    ↓
JSON response: {matches_played: 42, team_ranking: {...}}
    ↓
JavaScript updates DOM with new data
    ↓
User sees updated Career Tab without page reload
```

---

## 7. File References

### Models
- **Tournament:** `apps/tournaments/models/tournament.py` (Lines 1-1011)
- **Match:** `apps/tournaments/models/match.py` (Lines 1-580)
- **Game:** `apps/tournaments/models/tournament.py` (Lines 34-149)
- **TeamRanking:** `apps/leaderboards/models.py` (Lines 350-430)
- **UserStats:** `apps/leaderboards/models.py` (Lines 200-280)
- **TeamMembership:** `apps/teams/models/` (not audited in detail)

### Services
- **CareerContextService:** `apps/user_profile/services/career_context.py`
- **TeamRankingAdapter:** `apps/tournament_ops/adapters/team_ranking_adapter.py`
- **TierBoundaries:** `apps/tournament_ops/dtos/analytics.py` (Lines 442-485)

### Views
- **Public Profile:** `apps/user_profile/views/public_profile_views.py` (Line 83+)

### Templates
- **Career Tab:** `templates/user_profile/profile/tabs/_tab_career.html`
- **Public Profile:** `templates/user_profile/profile/public_profile.html`

---

## 8. Related Documentation

- Phase 5 Implementation Summary: `docs/UP_PHASE_5_IMPLEMENTATION_SUMMARY.md`
- Phase 5 Complete Report: `docs/UP_PHASE_5_COMPLETE_REPORT.md`
- Career Audit: `docs/phase5_career_audit.md`
- Tournament Models Audit: `Documents/Audit/Tournament OPS dec19/01_MODELS_AUDIT.md`

---

## 9. Risk Assessment

### Low Risk (Safe)
- ✅ Adding context variables to `public_profile_view()` (append-only)
- ✅ Creating new service methods in `CareerTabService`
- ✅ Adding new AJAX endpoint (`career_tab_data_api`)
- ✅ Modifying Career Tab template only (isolated)

### Medium Risk (Requires Testing)
- ⚠️ Using `Match` queries (verify index performance)
- ⚠️ Using `TeamRanking.rank` field (may be NULL, need fallback)
- ⚠️ Game switching JavaScript (test with missing data)

### High Risk (Avoid for Now)
- ❌ Adding `tier` field to Tournament model (requires migration)
- ❌ Modifying Overview/Activity/Settings tabs (out of scope)
- ❌ Changing team ranking calculation logic (Phase 8 responsibility)

---

## 10. Testing Recommendations

### Unit Tests
- Test `get_matches_played_count()` with solo matches
- Test `get_matches_played_count()` with team matches
- Test `get_team_ranking()` with active team
- Test `get_team_ranking()` with no team (should return None)
- Test tier calculation with various ELO values

### Integration Tests
- Test `public_profile_view()` includes career context
- Test `career_tab_data_api()` returns valid JSON
- Test game switching updates displayed data
- Test Career Tab with user who has no matches
- Test Career Tab with user who has no team

### Manual Testing
- View Career Tab for user with multiple games
- Click different game buttons and verify data changes
- Check Network tab to verify AJAX calls
- Test with incognito mode (anonymous user)
- Test with owner vs visitor permissions

---

## Conclusion

The Career Tab can be safely wired to backend data without migrations or breaking changes:

1. **Tournament Tier:** Use JSON field or infer from `is_official`/`is_featured` flags
2. **Matches Played:** Query `Match` model filtering by user/team and `COMPLETED`/`FORFEIT` states
3. **Team Ranking:** Use existing `TeamRanking` model with ELO and tier calculation
4. **Context Injection:** Add data to `public_profile_view()` context and create AJAX endpoint

All changes are isolated to Career Tab and service layer. No impact on other tabs.

**Next Steps:** Implement `CareerTabService` methods and wire to view/template.

---

**End of Audit Report**
