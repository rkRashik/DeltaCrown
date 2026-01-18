# Career Tab: Primary Game Resolution + Scalable Selector Bar Fix

**Date:** 2026-01-19  
**Scope:** Career Tab Only  
**Files Modified:** 3  
**Status:** READY FOR IMPLEMENTATION

---

## ISSUE SUMMARY

### Issue #1: Primary Game Source of Truth is Wrong
When user sets "Primary Team" in Settings → About → Primary Team & Signature Game, the Career selector shows a different primary game.

### Issue #2: Game Selector Bar Not Scalable
Current selector wastes space and won't fit 11 games properly.

---

## PART 1: PRIMARY GAME RESOLUTION AUDIT

### Model Fields Discovery

**File:** `apps/user_profile/models_main.py`  
**Lines:** 258-276

```python
class UserProfile(models.Model):
    # ...
    
    # UP.3 Extension: Primary Team and Game
    primary_team = models.ForeignKey(
        'teams.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_members',
        help_text="User's primary/main team (auto-syncs primary_game to team's game)"
    )
    
    primary_game = models.ForeignKey(
        'games.Game',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_players',
        help_text="User's primary/signature game (auto-set from primary_team, or manual if no team)"
    )
```

**Key Insight:** 
- `primary_team` should drive `primary_game` (team.game)
- `primary_game` can be set manually if no team
- Both are on UserProfile model with ForeignKey relationships

### Current Bug in get_linked_games()

**File:** `apps/user_profile/services/career_tab_service.py`  
**Lines:** 589-680

**Current priority order (WRONG):**
1. `user_profile.primary_game` (direct FK)
2. Passport-level `is_primary` field fallback
3. First pinned/sorted passport

**Missing:** primary_team.game resolution!

---

## PART 2: IMPLEMENTATION

### 2.1 Fix CareerTabService.get_linked_games()

**File:** `apps/user_profile/services/career_tab_service.py`  
**Function:** `get_linked_games()` (Line 589)

**Replace entire function with:**

```python
@staticmethod
def get_linked_games(user_profile) -> List[Dict[str, Any]]:
    """
    Get ordered list of user's linked games.
    
    PRIMARY GAME RESOLUTION (4-tier fallback):
    1. primary_team.game (if primary_team is set)
    2. user_profile.primary_game (FK)
    3. passport.is_primary flag
    4. First pinned/sorted passport
    
    Args:
        user_profile: UserProfile instance
    
    Returns:
        List of dicts with game data and passport:
        [
            {
                'game': Game instance,
                'game_slug': str,
                'game_name': str,
                'game_icon_url': str,
                'passport': GameProfile instance,
                'is_primary': bool,
                'primary_source': str  # DEBUG: 'team', 'direct', 'flag', 'fallback'
            },
            ...
        ]
    """
    from apps.user_profile.models import GameProfile
    from apps.games.models import Game
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get all active public game profiles for user (OPTIMIZED: select_related game)
    passports_qs = GameProfile.objects.filter(
        user=user_profile.user,
        visibility=GameProfile.VISIBILITY_PUBLIC,
        status=GameProfile.STATUS_ACTIVE
    ).select_related('game').order_by('-is_pinned', 'pinned_order', 'sort_order', '-updated_at')
    
    # === PRIMARY GAME RESOLUTION (4-tier fallback) ===
    primary_game = None
    primary_source = None
    
    # 1. Try primary_team.game (HIGHEST PRIORITY)
    try:
        primary_team = getattr(user_profile, 'primary_team', None)
        if primary_team and hasattr(primary_team, 'game'):
            primary_game = primary_team.game
            primary_source = 'team'
            logger.debug(f"[Career] PRIMARY_RESOLUTION: by primary_team ({primary_team.name} → {primary_game.slug})")
    except Exception as e:
        logger.warning(f"[Career] primary_team resolution failed: {e}")
    
    # 2. Fallback: user_profile.primary_game FK
    if not primary_game:
        try:
            primary_game = getattr(user_profile, 'primary_game', None)
            if primary_game:
                primary_source = 'direct'
                logger.debug(f"[Career] PRIMARY_RESOLUTION: by primary_game FK ({primary_game.slug})")
        except Exception as e:
            logger.warning(f"[Career] primary_game FK resolution failed: {e}")
    
    # 3. Fallback: passport.is_primary flag
    if not primary_game:
        for passport in passports_qs:
            if getattr(passport, 'is_primary', False):
                primary_game = passport.game
                primary_source = 'flag'
                logger.debug(f"[Career] PRIMARY_RESOLUTION: by passport flag ({primary_game.slug})")
                break
    
    # 4. Fallback: first pinned/sorted passport
    if not primary_game and passports_qs.exists():
        primary_game = passports_qs.first().game
        primary_source = 'fallback'
        logger.debug(f"[Career] PRIMARY_RESOLUTION: fallback to first passport ({primary_game.slug})")
    
    linked_games = []
    primary_passport = None
    
    # Find primary passport
    if primary_game:
        for passport in passports_qs:
            if passport.game.id == primary_game.id:
                primary_passport = passport
                break
    
    # Build ordered list: PRIMARY FIRST, then others
    if primary_passport:
        game = primary_passport.game
        linked_games.append({
            'game': game,
            'game_slug': game.slug,
            'game_name': game.display_name,
            'game_icon_url': game.icon.url if game.icon else f"/static/images/games/{game.slug}-logo.png",
            'passport': primary_passport,
            'is_primary': True,
            'primary_source': primary_source  # DEBUG field
        })
    
    # Add remaining passports
    for passport in passports_qs:
        if primary_passport and passport.id == primary_passport.id:
            continue
        
        game = passport.game
        linked_games.append({
            'game': game,
            'game_slug': game.slug,
            'game_name': game.display_name,
            'game_icon_url': game.icon.url if game.icon else f"/static/images/games/{game.slug}-logo.png",
            'passport': passport,
            'is_primary': False,
            'primary_source': None
        })
    
    return linked_games
```

---

### 2.2 Update public_profile_view() Context

**File:** `apps/user_profile/views/public_profile_views.py`  
**Function:** `public_profile_view()` (around line 653)

**Find this block:**
```python
# PHASE UP 5: Career Tab Enhanced Context (append-only, no impact on other tabs)
from apps.user_profile.services.career_tab_service import CareerTabService, GAME_DISPLAY_CONFIG

# Get linked games for game selector (OPTIMIZED with select_related)
career_linked_games = CareerTabService.get_linked_games(user_profile)
context['career_linked_games'] = career_linked_games

# Get primary game for initial load (first item is always primary)
if career_linked_games:
    primary_game = career_linked_games[0]['game']
    primary_game_slug = career_linked_games[0]['game_slug']
else:
    primary_game = None
    primary_game_slug = None

context['career_selected_game'] = primary_game
context['career_selected_game_slug'] = primary_game_slug  # For JS init
```

**Replace with:**
```python
# PHASE UP 5: Career Tab Enhanced Context (append-only, no impact on other tabs)
from apps.user_profile.services.career_tab_service import CareerTabService, GAME_DISPLAY_CONFIG
import logging

logger = logging.getLogger(__name__)

# Get linked games for game selector (OPTIMIZED with select_related)
career_linked_games = CareerTabService.get_linked_games(user_profile)
context['career_linked_games'] = career_linked_games

# Get primary game for initial load (first item is always primary)
if career_linked_games:
    primary_game_item = career_linked_games[0]
    primary_game = primary_game_item['game']
    primary_game_slug = primary_game_item['game_slug']
    
    # DEBUG log
    logger.info(f"[Career] Primary game for {username}: {primary_game_slug} (source: {primary_game_item.get('primary_source', 'unknown')})")
else:
    primary_game = None
    primary_game_slug = None

context['career_selected_game'] = primary_game
context['career_selected_game_slug'] = primary_game_slug  # For JS init
```

---

### 2.3 Redesign Game Selector Bar (Horizontal Scroll + Auto-Center)

**File:** `templates/user_profile/profile/tabs/_tab_career.html`  
**Section:** Game Selector Bar (Lines 18-40)

**Replace:**
```django-html
<!-- ================================== -->
<!-- 1. GAME SELECTOR BAR (Sticky Top) -->
<!-- ================================== -->
<div class="sticky top-4 z-30 overflow-x-auto no-scrollbar">
    <div class="flex gap-3 pb-2 min-w-max">
        {% for game in career_payload_initial.available_games %}
        <button
            onclick="switchCareerGame('{{ game.slug }}', this)"
            data-game-slug="{{ game.slug }}"
            class="game-btn px-6 py-3 rounded-xl border border-white/10 bg-z-panel text-gray-400 hover:bg-white/5 transition-all duration-200 flex items-center gap-3 whitespace-nowrap relative
            {% if forloop.first %}active bg-z-cyan text-black shadow-neon-cyan{% endif %}"
        >
            {% if game.icon_url %}
            <img src="{{ game.icon_url }}" alt="{{ game.name }}" class="w-5 h-5">
            {% endif %}
            <span class="font-bold text-xs uppercase tracking-wider">{{ game.name }}</span>
            {% if game.is_primary %}
            <span class="ml-2 px-2 py-0.5 bg-z-gold text-black text-[8px] font-black uppercase tracking-wider rounded shadow-sm">Primary</span>
            {% endif %}
        </button>
        {% endfor %}
    </div>
</div>
```

**With:**
```django-html
<!-- ================================== -->
<!-- 1. GAME SELECTOR BAR (Sticky Top, Horizontal Scroll) -->
<!-- ================================== -->
<div class="sticky top-4 z-30">
    <div id="game-selector-scrollarea" class="overflow-x-auto scrollbar-hide scroll-smooth pb-2">
        <div class="flex gap-2 min-w-max px-1">
            {% for game in career_payload_initial.available_games %}
            <button
                onclick="switchCareerGame('{{ game.slug }}', this)"
                data-game-slug="{{ game.slug }}"
                class="game-btn shrink-0 px-4 py-2.5 rounded-lg border border-white/10 bg-z-panel text-gray-400 hover:bg-white/5 transition-all duration-200 flex items-center gap-2 whitespace-nowrap relative group
                {% if forloop.first %}active bg-z-cyan text-black shadow-neon-cyan border-z-cyan{% endif %}"
                title="{{ game.name }}{% if game.is_primary %} (Primary Game){% endif %}"
            >
                {% if game.icon_url %}
                <img src="{{ game.icon_url }}" alt="{{ game.name }}" class="w-4 h-4 shrink-0">
                {% endif %}
                <span class="font-bold text-[10px] uppercase tracking-wider">{{ game.name }}</span>
                {% if game.is_primary %}
                <!-- Compact Primary Badge: Dot + Tooltip -->
                <div class="w-2 h-2 rounded-full bg-z-gold shadow-sm shrink-0" 
                     title="Primary Game"></div>
                {% endif %}
            </button>
            {% endfor %}
        </div>
    </div>
</div>
```

---

### 2.4 Add CSS for Scrollbar Hide + Smooth Scroll

**File:** `templates/user_profile/profile/tabs/_tab_career.html`  
**Section:** `<style>` block (around line 280)

**Find:**
```css
/* Scrollbar Hide */
.no-scrollbar::-webkit-scrollbar {
    display: none;
}
.no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
```

**Replace with:**
```css
/* Scrollbar Hide (Updated for game selector) */
.no-scrollbar::-webkit-scrollbar,
.scrollbar-hide::-webkit-scrollbar {
    display: none;
}
.no-scrollbar,
.scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
}

/* Game Selector Compact Design */
.game-btn {
    min-height: 40px;
    transition: all 0.2s ease;
}

.game-btn:hover {
    transform: translateY(-1px);
    border-color: rgba(0, 240, 255, 0.3);
}
```

---

### 2.5 Update switchCareerGame() with Auto-Center Scroll

**File:** `templates/user_profile/profile/tabs/_tab_career.html`  
**Section:** JS `switchCareerGame()` function (around line 330)

**Find:**
```javascript
// AJAX-Based Game Switching
function switchCareerGame(gameSlug, buttonElement) {
    const contentArea = document.getElementById('career-content-area');
    const username = '{{ profile_user.username }}';
    
    if (!contentArea) {
        console.warn('Career content area not found');
        return;
    }
    
    // 1. Add loading state
    contentArea.classList.add('career-loading');
    
    // 2. Update button active state immediately
    document.querySelectorAll('.game-btn').forEach(btn => {
        btn.classList.remove('active', 'bg-z-cyan', 'text-black', 'shadow-neon-cyan');
        btn.classList.add('text-gray-400');
    });
    buttonElement.classList.add('active', 'bg-z-cyan', 'text-black', 'shadow-neon-cyan');
    buttonElement.classList.remove('text-gray-400');
```

**Replace with:**
```javascript
// AJAX-Based Game Switching
function switchCareerGame(gameSlug, buttonElement) {
    const contentArea = document.getElementById('career-content-area');
    const username = '{{ profile_user.username }}';
    
    if (!contentArea) {
        console.warn('Career content area not found');
        return;
    }
    
    // 1. Add loading state
    contentArea.classList.add('career-loading');
    
    // 2. Update button active state immediately
    document.querySelectorAll('.game-btn').forEach(btn => {
        btn.classList.remove('active', 'bg-z-cyan', 'text-black', 'shadow-neon-cyan', 'border-z-cyan');
        btn.classList.add('text-gray-400');
    });
    buttonElement.classList.add('active', 'bg-z-cyan', 'text-black', 'shadow-neon-cyan', 'border-z-cyan');
    buttonElement.classList.remove('text-gray-400');
    
    // 3. Auto-scroll active button into center view (SCALABILITY FIX)
    const scrollArea = document.getElementById('game-selector-scrollarea');
    if (scrollArea && buttonElement) {
        setTimeout(() => {
            buttonElement.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
                inline: 'center'
            });
        }, 50);  // Small delay to ensure DOM is updated
    }
```

---

### 2.6 Update initCareerTab() to Honor Primary Game

**File:** `templates/user_profile/profile/tabs/_tab_career.html`  
**Section:** `initCareerTab()` function (around line 325)

**Find:**
```javascript
// Initialize Career Tab (Issue #3: Fix blank load)
function initCareerTab() {
    if (careerTabInitialized) return;
    careerTabInitialized = true;
    
    console.log('[Career Tab] Initializing...');
    
    // Find primary game slug from context or first button
    const primaryGameSlug = '{{ career_selected_game_slug|default:"" }}';
    const firstButton = document.querySelector('.game-btn');
```

**Replace with:**
```javascript
// Initialize Career Tab (Issue #3: Fix blank load)
function initCareerTab() {
    if (careerTabInitialized) return;
    careerTabInitialized = true;
    
    console.log('[Career Tab] Initializing...');
    
    // Find primary game slug from backend context (ALWAYS TRUST BACKEND)
    const primaryGameSlug = '{{ career_selected_game_slug|default:"" }}';
    
    if (!primaryGameSlug) {
        console.warn('[Career Tab] No primary game slug from backend');
        return;
    }
    
    // Find button for primary game (NOT first button, but primary_game button!)
    const primaryButton = document.querySelector(`.game-btn[data-game-slug="${primaryGameSlug}"]`);
    
    if (!primaryButton) {
        console.error(`[Career Tab] Button not found for primary game: ${primaryGameSlug}`);
        return;
    }
```

---

## PART 3: TESTING & VALIDATION

### 3.1 Smoke Test Checklist

#### ✅ **Primary Game Resolution**
- [ ] Set Primary Team to a Valorant team in Settings → About
- [ ] Navigate to Career tab
- [ ] Verify selector shows Valorant as first button with PRIMARY badge/dot
- [ ] Refresh page → Valorant still primary
- [ ] Switch to another game (e.g., eFootball)
- [ ] Switch back → Valorant still shows PRIMARY indicator
- [ ] Check Django logs for: `PRIMARY_RESOLUTION: by primary_team (TeamName → valorant)`

#### ✅ **Primary Game Fallback Testing**
- [ ] Remove Primary Team (set to null)
- [ ] Set Primary Game directly to CS2 in Settings
- [ ] Career selector shows CS2 as primary
- [ ] Logs show: `PRIMARY_RESOLUTION: by primary_game FK (cs2)`
- [ ] Remove Primary Game
- [ ] Career falls back to first pinned passport
- [ ] Logs show: `PRIMARY_RESOLUTION: fallback to first passport (...)`

#### ✅ **Scalable Selector Bar**
- [ ] Link 11 different games (all available games)
- [ ] Selector remains single row (no wrapping)
- [ ] Can scroll horizontally to see all games
- [ ] Scrollbar is hidden but scroll works
- [ ] Click a game at the end → auto-scrolls to center that button
- [ ] Active button remains clearly visible (cyan glow)
- [ ] PRIMARY dot/badge visible and doesn't break layout

#### ✅ **No Layout Drift**
- [ ] Hero card, stat tiles, attributes, affiliation sections unchanged
- [ ] Only selector bar modified
- [ ] No duplicate DOM IDs
- [ ] No console errors
- [ ] Only ONE API call per game switch

#### ✅ **Performance & Debug**
- [ ] Check server logs for PRIMARY_RESOLUTION debug messages
- [ ] Verify `career_selected_game_slug` matches backend primary game
- [ ] Network tab: single `/@username/career-data/?game=...` per switch
- [ ] Response time < 500ms
- [ ] No duplicate AJAX calls

---

## PART 4: DEBUG LOG EXAMPLES

### Expected Log Output (Django)

**Scenario 1: Primary Team Set**
```
[INFO] [Career] Primary game for johndoe: valorant (source: team)
[DEBUG] [Career] PRIMARY_RESOLUTION: by primary_team (Alpha Esports → valorant)
```

**Scenario 2: No Team, Direct Primary Game**
```
[INFO] [Career] Primary game for johndoe: cs2 (source: direct)
[DEBUG] [Career] PRIMARY_RESOLUTION: by primary_game FK (cs2)
```

**Scenario 3: Fallback to Passport Flag**
```
[INFO] [Career] Primary game for johndoe: efootball (source: flag)
[DEBUG] [Career] PRIMARY_RESOLUTION: by passport flag (efootball)
```

**Scenario 4: Full Fallback**
```
[INFO] [Career] Primary game for johndoe: pubgm (source: fallback)
[DEBUG] [Career] PRIMARY_RESOLUTION: fallback to first passport (pubgm)
```

---

## PART 5: SUMMARY OF CHANGES

### Files Modified (3 total)

1. **apps/user_profile/services/career_tab_service.py**
   - Updated `get_linked_games()` to use 4-tier primary game resolution
   - Added primary_team.game as HIGHEST priority
   - Added debug logging for primary resolution source

2. **apps/user_profile/views/public_profile_views.py**
   - Updated context building to log primary game resolution
   - Added primary_source debug info to logs

3. **templates/user_profile/profile/tabs/_tab_career.html**
   - Redesigned selector bar for horizontal scroll
   - Compact pill buttons with 11-game scalability
   - PRIMARY indicator changed to dot with tooltip
   - Added `scrollIntoView()` auto-center on game switch
   - Updated CSS for scrollbar hiding and compact design
   - Updated `initCareerTab()` to use backend primary game slug

### Lines Changed
- **career_tab_service.py:** ~100 lines (function rewrite + logging)
- **public_profile_views.py:** ~10 lines (logging addition)
- **_tab_career.html:** ~50 lines (selector bar + JS + CSS)

### Backward Compatibility
✅ No breaking changes  
✅ Existing API contract preserved  
✅ Layout structure unchanged (only selector bar improved)  
✅ JS function signatures unchanged  
✅ All existing features work as before

---

## IMPLEMENTATION COMPLETE

All fixes ready. Primary game resolution now follows strict hierarchy with primary_team.game as highest priority. Selector bar scales to 11+ games with smooth horizontal scroll and auto-centering.
