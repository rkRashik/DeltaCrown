# Game Lookup Resolution Proposal

**Document Version:** 1.0  
**Date:** 2026-01-30  
**Status:** ANALYTICAL ONLY - NO CODE CHANGES YET  
**Purpose:** Design solution for Team.game_id → Game model lookup

---

## EXECUTIVE SUMMARY

**Problem Status:** ✅ **RESOLVED** (Solution Already Exists)

**Original Concern:**  
Team model stores `game_id` as IntegerField (not ForeignKey), requiring manual lookup to display game data (name, logo, colors).

**Discovered Reality:**  
`GameService.get_game_by_id(game_id: int)` **ALREADY EXISTS** in production codebase at `apps/games/services/game_service.py` line 38-45.

**Recommendation:**  
Use existing service. No migration needed. Just integrate into context builder.

---

## SECTION 1 — PROBLEM STATEMENT

### 1.1 Current Schema

**Team Model** (`apps/organizations/models/team.py`):
```python
class Team(models.Model):
    game_id = models.IntegerField(db_index=True, help_text="Foreign key to Game model")
    # ... other fields
```

**Constraint:** NOT a ForeignKey - manual lookup required.

### 1.2 Contract Requirements

**Team Detail Page Contract** expects `team.game` with:
```python
{
    'id': int,
    'name': str,           # Display name (e.g., "VALORANT™")
    'slug': str,           # URL identifier
    'logo_url': str,       # Logo image URL
    'primary_color': str,  # Hex color for branding
}
```

**Used by template:** Hero section game badge, color theming, stats context.

---

## SECTION 2 — DISCOVERED SOLUTION

### 2.1 GameService Exists

**File:** `apps/games/services/game_service.py`  
**Lines:** 38-45

**Implementation:**
```python
@staticmethod
def get_game_by_id(game_id: int) -> Optional[Game]:
    """
    Get a game by its ID.
    
    Args:
        game_id: The game ID
        
    Returns:
        The game or None if not found/inactive
    """
    try:
        return Game.objects.select_related(
            'roster_config',
            'tournament_config'
        ).get(id=game_id, is_active=True)
    except Game.DoesNotExist:
        return None
```

**Features:**
- ✅ Returns Game model instance
- ✅ Includes select_related for roster/tournament config
- ✅ Filters out inactive games (is_active=True)
- ✅ Returns None for missing/invalid game_id
- ✅ Uses try/except for safe error handling

---

### 2.2 Game Model Schema

**File:** `apps/games/models/game.py`

**Available Fields (Verified):**
```python
class Game(models.Model):
    # Identity
    name = CharField(100)                 # e.g., "Valorant"
    display_name = CharField(150)         # e.g., "VALORANT™"
    slug = SlugField(unique=True)         # e.g., "valorant"
    short_code = CharField(10, unique=True)  # e.g., "VAL"
    
    # Branding
    icon = ImageField(blank=True)
    logo = ImageField(blank=True)
    banner = ImageField(blank=True)
    card_image = ImageField(blank=True)
    primary_color = CharField(7, default='#7c3aed')    # Hex with validator
    secondary_color = CharField(7, default='#1e1b4b')  # Hex with validator
    
    # Classification
    category = CharField(50)              # FPS, MOBA, BR, etc.
    game_type = CharField(50)             # TEAM_VS_TEAM, 1V1, etc.
    platforms = JSONField(default=list)   # ["PC", "Console", etc.]
```

**All Contract Requirements Satisfied:** ✅ id, name, slug, logo, primary_color

---

## SECTION 3 — INTEGRATION APPROACH

### 3.1 Context Builder Modification

**File:** `apps/organizations/services/team_detail_context.py`

**Current State (Line ~350):**
```python
def _safe_game_context(self, team: Team) -> Dict[str, Any]:
    """Get game info safely."""
    return {
        'id': team.game_id if hasattr(team, 'game_id') else None,
        'name': None,  # TODO: Resolve game_id to Game model
    }
```

**Proposed Change:**
```python
from apps.games.services import GameService

def _safe_game_context(self, team: Team) -> Dict[str, Any]:
    """Get game info safely."""
    if not team.game_id:
        return {'id': None, 'name': 'Unknown Game', 'slug': None, 'logo_url': None, 'primary_color': '#7c3aed'}
    
    game = GameService.get_game_by_id(team.game_id)
    
    if game:
        return {
            'id': game.id,
            'name': game.display_name,          # Use display_name for branding
            'slug': game.slug,
            'logo_url': game.logo.url if game.logo else None,
            'primary_color': game.primary_color,
        }
    
    # Fallback for invalid game_id
    return {
        'id': team.game_id,
        'name': f'Game #{team.game_id}',
        'slug': None,
        'logo_url': None,
        'primary_color': '#7c3aed',
    }
```

**Safety Features:**
- ✅ Handles missing game_id (None)
- ✅ Handles invalid game_id (returns fallback)
- ✅ Handles missing logo (None fallback)
- ✅ Always returns dict with required keys

---

### 3.2 Performance Analysis

**Query Cost:**
- **+1 Query per page view:** `Game.objects.get(id=game_id)`
- **select_related included:** roster_config, tournament_config (efficient)
- **Acceptable:** Game data rarely changes, perfect caching candidate

**Optimization Strategy:**
```python
from django.core.cache import cache

def _safe_game_context(self, team: Team) -> Dict[str, Any]:
    if not team.game_id:
        return {...}  # Fallback dict
    
    # Try cache first (24-hour TTL)
    cache_key = f'game_context:{team.game_id}'
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Fetch from database
    game = GameService.get_game_by_id(team.game_id)
    
    if game:
        result = {
            'id': game.id,
            'name': game.display_name,
            'slug': game.slug,
            'logo_url': game.logo.url if game.logo else None,
            'primary_color': game.primary_color,
        }
        cache.set(cache_key, result, 86400)  # 24 hours
        return result
    
    return {...}  # Fallback dict
```

**Cache Invalidation:**
- Game data changes infrequently (new games/updates are rare)
- 24-hour TTL is safe (stale data acceptable)
- Can invalidate on Game model save signal if needed

---

### 3.3 Query Count Impact

**Before (Tier 1 Only):**
```
Query 1: Team.objects.select_related('organization').get(slug=slug)
Query 2: TeamMembership.objects.filter(team=team, user=viewer)  [if authenticated]
Total: 2 queries
```

**After (Tier 1 + Game Lookup):**
```
Query 1: Team.objects.select_related('organization').get(slug=slug)
Query 2: TeamMembership.objects.filter(team=team, user=viewer)  [if authenticated]
Query 3: Game.objects.select_related(...).get(id=team.game_id)
Total: 3 queries
```

**With Caching (Expected 99% Cache Hit Rate):**
```
Total: 2 queries (Game data from cache)
```

**Contract Budget:** Max 6 queries allowed  
**Status:** ✅ Within budget

---

## SECTION 4 — TESTING STRATEGY

### 4.1 Unit Tests

**File:** `apps/organizations/tests/test_team_detail_contract.py`

**Required Test Cases:**

1. **Valid Game ID:**
```python
def test_game_context_with_valid_game_id(self):
    """Game data resolved correctly for valid game_id."""
    game = GameFactory(
        display_name='VALORANT™',
        slug='valorant',
        primary_color='#ff4655'
    )
    team = TeamFactory(game_id=game.id)
    
    context = TeamDetailContext(team=team, viewer=None).get_context()
    
    assert context['team']['game']['id'] == game.id
    assert context['team']['game']['name'] == 'VALORANT™'
    assert context['team']['game']['slug'] == 'valorant'
    assert context['team']['game']['primary_color'] == '#ff4655'
```

2. **Invalid Game ID:**
```python
def test_game_context_with_invalid_game_id(self):
    """Fallback for invalid game_id."""
    team = TeamFactory(game_id=99999)  # Non-existent game
    
    context = TeamDetailContext(team=team, viewer=None).get_context()
    
    assert context['team']['game']['id'] == 99999
    assert context['team']['game']['name'] == 'Game #99999'
    assert context['team']['game']['logo_url'] is None
```

3. **None Game ID:**
```python
def test_game_context_with_none_game_id(self):
    """Handles teams with NULL game_id."""
    team = TeamFactory(game_id=None)
    
    context = TeamDetailContext(team=team, viewer=None).get_context()
    
    assert context['team']['game']['id'] is None
    assert context['team']['game']['name'] == 'Unknown Game'
```

4. **Missing Logo:**
```python
def test_game_context_with_missing_logo(self):
    """Handles games without logo uploaded."""
    game = GameFactory(logo='')  # No logo
    team = TeamFactory(game_id=game.id)
    
    context = TeamDetailContext(team=team, viewer=None).get_context()
    
    assert context['team']['game']['logo_url'] is None
```

---

### 4.2 Caching Tests

**File:** `apps/organizations/tests/test_team_detail_performance.py`

**Cache Hit Test:**
```python
from django.core.cache import cache

def test_game_context_uses_cache(self):
    """Verify game data cached to reduce queries."""
    game = GameFactory(display_name='VALORANT™')
    team = TeamFactory(game_id=game.id)
    
    # First call - cache miss
    with self.assertNumQueries(3):  # Team + Membership + Game
        context1 = TeamDetailContext(team=team, viewer=None).get_context()
    
    # Second call - cache hit
    with self.assertNumQueries(2):  # Team + Membership (no Game query)
        context2 = TeamDetailContext(team=team, viewer=None).get_context()
    
    assert context1['team']['game'] == context2['team']['game']
```

**Cache Invalidation Test:**
```python
def test_game_context_cache_invalidates_on_update(self):
    """Verify cache invalidates when game updated."""
    game = GameFactory(display_name='VALORANT™')
    team = TeamFactory(game_id=game.id)
    
    # Prime cache
    context1 = TeamDetailContext(team=team, viewer=None).get_context()
    assert context1['team']['game']['name'] == 'VALORANT™'
    
    # Update game
    game.display_name = 'VALORANT 2024™'
    game.save()  # Should trigger cache invalidation signal
    
    # Fetch again
    context2 = TeamDetailContext(team=team, viewer=None).get_context()
    assert context2['team']['game']['name'] == 'VALORANT 2024™'
```

---

## SECTION 5 — TEMPLATE IMPACT

### 5.1 Current Template Usage

**File:** `templates/organizations/team/partials/_head_assets.html`

**Line 10 (Document Title):**
```django
<title>{{ team_name|default:"Team" }} | DeltaCrown Esports</title>
```

**Proposed Enhancement (After Wiring):**
```django
<title>{{ team_name|default:"Team" }}{% if team.game.name %} — {{ team.game.name }}{% endif %} | DeltaCrown</title>
```

---

**File:** `templates/organizations/team/partials/_body.html`

**Line 68 (Hero Section - Game Badge):**
```django
{% if team.game.name %}
<div class="game-badge">
    {% if team.game.logo_url %}
    <img src="{{ team.game.logo_url }}" alt="{{ team.game.name }}" class="game-icon">
    {% endif %}
    <span>{{ team.game.name }}</span>
</div>
{% endif %}
```

**Fallback Behavior:**
- If `team.game.name` is None → Badge hidden (no visual artifact)
- If `team.game.logo_url` is None → Only text shown (no broken image)

---

### 5.2 CSS Theming Opportunity

**Primary Color Usage:**
```django
<style>
.team-header {
    border-bottom: 3px solid {{ team.game.primary_color|default:"#7c3aed" }};
}

.stats-card.highlight {
    background: linear-gradient(135deg, {{ team.game.primary_color|default:"#7c3aed" }}20, transparent);
}
</style>
```

**Benefit:** Teams inherit game branding automatically (Valorant teams get red theme, CS2 teams get orange, etc.)

---

## SECTION 6 — MIGRATION REQUIREMENTS

### 6.1 Schema Changes

**Required Migrations:** ✅ **NONE**

**Reason:**  
- Team.game_id already exists as IntegerField
- Game model already exists with all required fields
- GameService already exists with lookup method
- No schema changes needed

---

### 6.2 Data Integrity Check

**Verify game_id Validity:**
```sql
-- Find teams with invalid game_id
SELECT t.id, t.name, t.game_id
FROM organizations_team t
LEFT JOIN games_game g ON t.game_id = g.id
WHERE g.id IS NULL;
```

**Action if invalid rows found:**
1. Identify affected teams
2. Assign to default game OR set game_id=NULL
3. Log discrepancy for investigation

---

## SECTION 7 — ROLLOUT PLAN

### Phase 1: Integration (No UI Change)

**Files to Modify:** 1 file only
- `apps/organizations/services/team_detail_context.py`

**Changes:**
1. Import GameService at top
2. Modify `_safe_game_context()` method
3. Add caching logic (optional but recommended)

**Validation:**
- Run existing 22 contract tests (should still pass)
- Add 4 new tests for game lookup (valid, invalid, None, missing logo)

**Exit Criteria:**
- ✅ All 26 tests passing
- ✅ Context dict includes game.name, game.logo_url, game.primary_color
- ✅ No template changes yet (data available but not displayed)

---

### Phase 2: UI Activation (Separate PR)

**Files to Modify:** 1-2 template files
- `templates/organizations/team/partials/_body.html` (hero section)
- `templates/organizations/team/partials/_head_assets.html` (title tag - optional)

**Changes:**
1. Add game badge to hero section (lines 65-75)
2. Update title tag with game name (optional)

**Validation:**
- Visual regression test (screenshot comparison)
- Manual QA with multiple games
- Check fallback behavior (missing logo, invalid game_id)

**Exit Criteria:**
- ✅ Game badge displays for all teams with valid game_id
- ✅ Fallback handles missing data gracefully
- ✅ No layout shift or visual artifacts

---

## SECTION 8 — RISK ASSESSMENT

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Invalid game_id in production data | MEDIUM | LOW | Fallback dict returns safe values, query finds affected rows |
| GameService query adds latency | LOW | LOW | Caching reduces to negligible cost (cache hit 99%+) |
| Game model changes break context builder | LOW | MEDIUM | Use service abstraction (GameService) not direct model access |
| Missing logo breaks image display | LOW | LOW | Template checks `if team.game.logo_url` before rendering |

---

## SECTION 9 — FINAL RECOMMENDATIONS

### ✅ IMMEDIATE ACTIONS (Approved for Wiring)

1. **Integrate GameService.get_game_by_id() into context builder**
   - Method: Modify `_safe_game_context()` in `team_detail_context.py`
   - Safety: Full fallback handling for None/invalid game_id
   - Performance: Add 24-hour cache (99%+ hit rate expected)

2. **Add test coverage for game lookup**
   - 4 new tests: valid, invalid, None, missing logo
   - Verify contract tests still pass (26 total)

3. **Data integrity check**
   - Run SQL query to find invalid game_id rows
   - Fix any orphaned game_id references

---

### ⏸️ HOLD FOR PHASE 2 (After Tier 1 Complete)

1. **Template modifications** (display game badge)
   - Add hero section game badge
   - Update title tag with game name
   - **DO NOT proceed until Phase 1 verified**

2. **CSS theming with game colors**
   - Use `team.game.primary_color` for branding
   - Fallback to default purple (#7c3aed)

---

### 🚫 OUT OF SCOPE (Deferred)

1. **Convert game_id to ForeignKey**
   - Would require migration and breaking changes
   - Current IntegerField approach works fine
   - Not worth migration risk

2. **Preload all games into context**
   - Wasteful (team only needs 1 game)
   - Caching solves same problem more efficiently

---

## SECTION 10 — SUCCESS METRICS

### Phase 1 (Integration) Success Criteria

- ✅ GameService imported without errors
- ✅ `_safe_game_context()` returns all 5 required keys
- ✅ Fallback handling tested for edge cases
- ✅ 26/26 tests passing (22 existing + 4 new)
- ✅ Query count ≤3 without caching, ≤2 with caching
- ✅ No console errors or exceptions in logs

### Phase 2 (UI) Success Criteria

- ✅ Game badge visible on team detail page
- ✅ Game logo displays (or gracefully omitted if missing)
- ✅ Game name displays correctly
- ✅ No layout shift or broken images
- ✅ Title tag includes game name
- ✅ Visual regression test passes

---

## APPENDIX A — ALTERNATIVE APPROACHES (REJECTED)

### Option 1: Convert game_id to ForeignKey

**Approach:**
```python
game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='teams')
```

**Pros:**
- Native Django relationship
- Automatic reverse lookup (`game.teams.all()`)

**Cons:**
- ❌ Requires migration with potential data loss
- ❌ Breaking change for existing codebase
- ❌ High risk, low benefit

**Decision:** ❌ REJECTED (too risky)

---

### Option 2: Add game field to Team.objects.select_related()

**Approach:**
```python
team = Team.objects.select_related('organization', 'game').get(slug=slug)
```

**Cons:**
- ❌ Can't select_related on IntegerField (not FK)
- ❌ Doesn't work with current schema

**Decision:** ❌ REJECTED (impossible without FK migration)

---

### Option 3: Prefetch all games into context

**Approach:**
```python
games = Game.objects.all()
context['games_lookup'] = {g.id: g for g in games}
game = context['games_lookup'].get(team.game_id)
```

**Cons:**
- ❌ Wasteful (fetches all games when only 1 needed)
- ❌ Doesn't solve query cost (still +1 query)
- ❌ More complex than direct lookup

**Decision:** ❌ REJECTED (caching is better solution)

---

## APPENDIX B — SAMPLE GAME DATA

**Production Games (Expected):**
```
ID | short_code | display_name       | primary_color
---|------------|-------------------|---------------
1  | VAL        | VALORANT™         | #ff4655
2  | CS2        | Counter-Strike 2  | #f89b28
3  | LOL        | League of Legends | #0397ab
4  | DOTA       | Dota 2            | #c23c2a
5  | APEX       | Apex Legends      | #d9413e
```

**Fallback Color:** `#7c3aed` (DeltaCrown purple)

---

## CHANGELOG

**v1.0 (2026-01-30):**
- Initial proposal based on discovered GameService
- Changed from "blocker resolution" to "integration guide"
- Added caching strategy
- Added test plan
- Status: READY TO IMPLEMENT (Phase 1)

---

**APPROVAL STATUS:** ⏸️ **PENDING USER REVIEW**

**Next Steps After Approval:**
1. Implement Phase 1 (context builder integration)
2. Run tests (expect 26/26 passing)
3. Data integrity check (verify no invalid game_id)
4. Hold for Phase 2 approval (UI display)

---

**END OF PROPOSAL**
