# UP-GAME-PROFILE-FE-CONTRACT
## Frontend Data Contract for Game Profile System

**Status:** Design Review  
**Date:** 2024-12-24  
**Author:** AI Agent (supervised by RK Rashik)  
**Phase:** Frontend Contract Design (No UI Code)

---

## Executive Summary

Define **frontend data contract** for game profile rendering:
- What data FE receives (safe, privacy-filtered)
- What data FE must NEVER receive (PII, sensitive fields)
- How profiles render per game (game-specific badges, colors)
- How settings updates flow (POST endpoints)

**Key Principles:**
1. **Privacy-first:** FE receives filtered data based on viewer role
2. **Game-aware:** Per-game rendering (VALORANT ≠ MLBB ≠ CS2)
3. **Real-time validation:** Client-side + server-side IGN checks
4. **Audit-safe:** All mutations logged with context

---

## 1. Data Flow Architecture

### 1.1 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ USER PROFILE PAGE                                           │
│ (profile_public_v2, profile_settings_v2)                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ VIEW LAYER (Django)                                         │
│ apps/user_profile/views/fe_v2.py                            │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ CONTEXT BUILDER                                             │
│ build_public_profile_context(viewer, target_user)          │
│ - Calls ProfileVisibilityPolicy.filter_fields()            │
│ - Returns privacy-safe dict                                 │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ GAME PROFILE SERVICE                                        │
│ GameProfileService.get_public_game_profiles(user, viewer)  │
│ - Queries GameProfile model                                 │
│ - Filters fields based on viewer role                       │
│ - Returns List[Dict]                                        │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ TEMPLATE (Jinja2)                                           │
│ templates/user_profile/v2/*.html                            │
│ - Renders game profile cards                                │
│ - Per-game styling (Tailwind classes)                       │
│ - Client-side interactions (Vanilla JS)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Context Data Structure

### 2.1 Public Profile Context (Viewer: Public)

**Endpoint:** `GET /u/@username`

**Context Dictionary:**

```python
{
    # User Identity
    'display_name': 'PlayerOne',
    'username': 'playerone',
    'public_id': 'DC-25-000042',
    'avatar_url': '/media/user_avatars/123/avatar.jpg',
    'bio': 'Pro VALORANT player | Immortal 3',
    
    # Location (if show_country = True)
    'country': 'Bangladesh',
    'region': 'SA',
    
    # Social Links (if show_socials = True)
    'social_links': {
        'youtube': 'https://youtube.com/@playerone',
        'twitch': 'https://twitch.tv/playerone',
        'discord': 'PlayerOne#1234',
    },
    
    # Game Profiles (if show_game_profiles = True)
    'game_profiles': [
        {
            'game': 'valorant',
            'game_display_name': 'VALORANT',
            'ign': 'PlayerOne#1234',
            'rank_name': 'Immortal 3',
            'main_role': 'Duelist',
            'is_verified': True,
            # NO STATS for public viewers
        },
        {
            'game': 'cs2',
            'game_display_name': 'Counter-Strike 2',
            'ign': '76561198...',
            'rank_name': 'Global Elite',
            'main_role': 'AWPer',
            'is_verified': False,
        }
    ],
    
    # Profile Stats (public aggregates only)
    'stats': {
        'level': 42,
        'xp': 8500,
        'tournaments_played': 15,
        'tournaments_won': 3,
        'badges_count': 8,
    },
    
    # Visibility Context
    'is_owner': False,
    'can_view': True,
}
```

**Privacy Rules (Public Viewer):**
- ❌ NO `matches_played`, `win_rate`, `kd_ratio` (stats hidden)
- ❌ NO `email`, `phone`, `address` (PII hidden)
- ❌ NO `verification_method`, `verified_at` (admin metadata hidden)
- ✅ YES `ign`, `rank_name`, `main_role` (if `show_game_profiles = True`)

### 2.2 Owner Context (Viewer: Self)

**Endpoint:** `GET /me/settings/`

**Context Dictionary:**

```python
{
    # Everything from public context PLUS:
    
    # Full Game Profiles (with stats)
    'game_profiles': [
        {
            'game': 'valorant',
            'game_display_name': 'VALORANT',
            'ign': 'PlayerOne#1234',
            'rank_name': 'Immortal 3',
            'rank_tier': 8,
            'peak_rank': 'Radiant',
            'main_role': 'Duelist',
            'matches_played': 342,
            'win_rate': 58,
            'kd_ratio': 1.45,
            'is_verified': True,
            'verified_at': '2024-12-20T15:30:00Z',
            'verification_method': 'manual_admin',
            'created_at': '2024-01-15T10:00:00Z',
            'updated_at': '2024-12-20T15:30:00Z',
            'metadata': {
                'region': 'NA',
                'peak_episode': 'E7A3'
            }
        }
    ],
    
    # Privacy Settings
    'privacy_settings': {
        'show_game_profiles': True,
        'show_email': False,
        'show_phone': False,
        'show_socials': True,
    },
    
    # Available Games (for add profile form)
    'available_games': [
        {'slug': 'valorant', 'name': 'VALORANT', 'category': 'FPS'},
        {'slug': 'cs2', 'name': 'Counter-Strike 2', 'category': 'FPS'},
        {'slug': 'mlbb', 'name': 'Mobile Legends', 'category': 'MOBA'},
        # ... all 11 supported games
    ],
    
    'is_owner': True,
    'can_view': True,
}
```

**Privacy Rules (Owner Viewer):**
- ✅ YES ALL stats (`matches_played`, `win_rate`, `kd_ratio`)
- ✅ YES verification metadata (`verified_at`, `verification_method`)
- ✅ YES privacy settings (for editing)
- ✅ YES metadata (game-specific fields)

---

## 3. Per-Game Rendering Specs

### 3.1 VALORANT Profile Card

**Visual Design:**

```
┌────────────────────────────────────────────────────────────┐
│ VALORANT                                    [🔗] [✏️] [🗑️]│
├────────────────────────────────────────────────────────────┤
│  ┌─────┐                                                   │
│  │ VAL │  PlayerOne#1234                   ✅ Verified    │
│  │LOGO │  Immortal 3 · Duelist                            │
│  └─────┘                                                   │
│                                                            │
│  📊 Stats: 342 matches · 58% WR · 1.45 K/D                │
│  🏆 Peak: Radiant                                          │
│  🌍 Region: NA                                             │
└────────────────────────────────────────────────────────────┘
```

**HTML Structure:**

```html
<div class="game-profile-card" data-game="valorant">
    <div class="card-header bg-red-600">
        <img src="/static/games/valorant_logo.png" alt="VALORANT" class="game-logo">
        <h3>VALORANT</h3>
        <div class="card-actions">
            <button class="btn-share" data-action="share">🔗</button>
            <button class="btn-edit" data-action="edit">✏️</button>
            <button class="btn-delete" data-action="delete">🗑️</button>
        </div>
    </div>
    
    <div class="card-body">
        <div class="profile-ign">
            <span class="ign">PlayerOne#1234</span>
            <span class="verified-badge">✅ Verified</span>
        </div>
        
        <div class="profile-rank">
            <img src="/static/ranks/valorant_immortal.png" alt="Immortal 3" class="rank-badge">
            <span class="rank-name">Immortal 3</span>
            <span class="separator">·</span>
            <span class="role">Duelist</span>
        </div>
        
        <div class="profile-stats">
            <div class="stat-item">
                <span class="stat-label">Matches</span>
                <span class="stat-value">342</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Win Rate</span>
                <span class="stat-value">58%</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">K/D</span>
                <span class="stat-value">1.45</span>
            </div>
        </div>
        
        <div class="profile-meta">
            <div class="meta-item">
                <span>🏆 Peak: Radiant</span>
            </div>
            <div class="meta-item">
                <span>🌍 Region: NA</span>
            </div>
        </div>
    </div>
</div>
```

**Tailwind Classes:**

```css
.game-profile-card.valorant {
    @apply border-red-600 bg-gradient-to-br from-red-50 to-red-100;
}

.card-header {
    @apply flex items-center justify-between p-4 bg-red-600 text-white rounded-t-lg;
}

.ign {
    @apply text-lg font-bold text-gray-900;
}

.verified-badge {
    @apply text-sm text-green-600 font-semibold;
}

.rank-badge {
    @apply w-12 h-12 object-contain;
}

.stat-item {
    @apply flex flex-col items-center p-2 bg-white rounded-lg shadow-sm;
}

.stat-value {
    @apply text-2xl font-bold text-gray-900;
}

.stat-label {
    @apply text-xs text-gray-500 uppercase tracking-wide;
}
```

### 3.2 Mobile Legends (MLBB) Profile Card

**Visual Design:**

```
┌────────────────────────────────────────────────────────────┐
│ MOBILE LEGENDS                              [🔗] [✏️] [🗑️]│
├────────────────────────────────────────────────────────────┤
│  ┌─────┐                                                   │
│  │MLBB │  123456789 (1234)                                │
│  │LOGO │  Mythic Glory · Marksman                         │
│  └─────┘                                                   │
│                                                            │
│  📊 Stats: 1,245 matches · 62% WR                         │
│  🏆 Peak: Mythical Glory 800 pts                          │
│  🌍 Server: 1234                                           │
└────────────────────────────────────────────────────────────┘
```

**Data Contract:**

```python
{
    'game': 'mlbb',
    'game_display_name': 'Mobile Legends: Bang Bang',
    'ign': '123456789',
    'rank_name': 'Mythic Glory',
    'main_role': 'Marksman',
    'metadata': {
        'server_id': '1234',  # Required for MLBB
        'emblem_config': 'Marksman-Assassin'
    }
}
```

### 3.3 CS2 Profile Card

**Visual Design:**

```
┌────────────────────────────────────────────────────────────┐
│ COUNTER-STRIKE 2                            [🔗] [✏️] [🗑️]│
├────────────────────────────────────────────────────────────┤
│  ┌─────┐                                                   │
│  │ CS2 │  76561198012345678                                │
│  │LOGO │  Global Elite · AWPer                             │
│  └─────┘                                                   │
│                                                            │
│  📊 Stats: 2,450 matches · 54% WR                         │
│  🏆 Peak: Global Elite                                     │
│  🔗 Steam Profile                                          │
└────────────────────────────────────────────────────────────┘
```

**Data Contract:**

```python
{
    'game': 'cs2',
    'game_display_name': 'Counter-Strike 2',
    'ign': '76561198012345678',
    'rank_name': 'Global Elite',
    'main_role': 'AWPer',
    'metadata': {
        'steam_profile_url': 'https://steamcommunity.com/profiles/76561198012345678/'
    }
}
```

---

## 4. Game-Specific Styling

### 4.1 Color Palette (Tailwind)

**Game Brand Colors:**

```javascript
const GAME_COLORS = {
    valorant: {
        primary: 'red-600',      // #DC2626
        secondary: 'red-400',
        gradient: 'from-red-600 to-red-800'
    },
    cs2: {
        primary: 'yellow-500',   // #EAB308
        secondary: 'yellow-400',
        gradient: 'from-yellow-500 to-orange-600'
    },
    mlbb: {
        primary: 'blue-600',     // #2563EB
        secondary: 'blue-400',
        gradient: 'from-blue-600 to-purple-600'
    },
    dota2: {
        primary: 'red-700',
        secondary: 'red-500',
        gradient: 'from-red-700 to-gray-900'
    },
    pubgm: {
        primary: 'orange-600',
        secondary: 'orange-400',
        gradient: 'from-orange-600 to-yellow-600'
    },
    // ... etc for all 11 games
};
```

### 4.2 Dynamic Class Assignment

**Template Helper:**

```html
<!-- templates/user_profile/v2/_game_profile_card.html -->
{% macro render_game_card(game_profile) %}
<div class="game-profile-card {{ game_profile.game }}" 
     data-game="{{ game_profile.game }}"
     style="border-color: var(--{{ game_profile.game }}-primary);">
    
    <div class="card-header bg-{{ game_profile.game }}-primary">
        <img src="{{ game_logo_url(game_profile.game) }}" 
             alt="{{ game_profile.game_display_name }}" 
             class="game-logo">
        <h3>{{ game_profile.game_display_name }}</h3>
    </div>
    
    <!-- Body content -->
    ...
</div>
{% endmacro %}
```

---

## 5. Settings Form Contract

### 5.1 Add Game Profile Form

**Endpoint:** `POST /me/settings/game-profiles/add`

**Form Fields:**

```html
<form method="post" action="{% url 'user_profile:add_game_profile' %}" id="add-game-profile-form">
    {% csrf_token %}
    
    <!-- Game Selection -->
    <label for="game">Select Game *</label>
    <select name="game" id="game" required>
        <option value="">-- Choose a game --</option>
        {% for game in available_games %}
        <option value="{{ game.slug }}" data-category="{{ game.category }}">
            {{ game.name }}
        </option>
        {% endfor %}
    </select>
    
    <!-- IGN (dynamic placeholder per game) -->
    <label for="ign">In-Game Name *</label>
    <input 
        type="text" 
        name="ign" 
        id="ign" 
        placeholder="Select a game first"
        required
        data-validation-url="{% url 'user_profile:validate_ign' %}"
    >
    <span class="error-message" id="ign-error"></span>
    <span class="help-text" id="ign-help"></span>
    
    <!-- Rank (optional) -->
    <label for="rank">Current Rank</label>
    <input type="text" name="rank" id="rank" placeholder="e.g., Immortal 3">
    
    <!-- Role (optional) -->
    <label for="role">Main Role</label>
    <input type="text" name="role" id="role" placeholder="e.g., Duelist, AWPer">
    
    <!-- Game-Specific Fields (conditional) -->
    <div id="mlbb-fields" style="display: none;">
        <label for="server_id">Server ID *</label>
        <input type="text" name="server_id" id="server_id" placeholder="e.g., 1234">
    </div>
    
    <button type="submit" class="btn-primary">Add Profile</button>
</form>
```

**Client-Side Validation (JavaScript):**

```javascript
// Game selection changes placeholder
document.getElementById('game').addEventListener('change', function(e) {
    const game = e.target.value;
    const ignInput = document.getElementById('ign');
    const ignHelp = document.getElementById('ign-help');
    
    // Update placeholder and help text per game
    const placeholders = {
        valorant: 'PlayerName#TAG',
        cs2: '76561198012345678',
        mlbb: '123456789',
        // ... etc
    };
    
    const helpTexts = {
        valorant: 'Your Riot ID with tagline (e.g., TenZ#1234)',
        cs2: 'Your 17-digit Steam ID64',
        mlbb: 'Your MLBB Game ID (9-10 digits)',
        // ... etc
    };
    
    ignInput.placeholder = placeholders[game] || 'Enter your in-game name';
    ignHelp.textContent = helpTexts[game] || '';
    
    // Show/hide game-specific fields
    document.getElementById('mlbb-fields').style.display = 
        game === 'mlbb' ? 'block' : 'none';
});

// Real-time IGN validation (debounced)
let ignValidationTimeout;
document.getElementById('ign').addEventListener('input', function(e) {
    clearTimeout(ignValidationTimeout);
    
    ignValidationTimeout = setTimeout(async () => {
        const game = document.getElementById('game').value;
        const ign = e.target.value;
        
        if (!game || !ign) return;
        
        // Call validation endpoint
        const response = await fetch('/api/validate-ign/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ game, ign })
        });
        
        const result = await response.json();
        const errorEl = document.getElementById('ign-error');
        
        if (result.valid) {
            e.target.classList.remove('error');
            e.target.classList.add('valid');
            errorEl.textContent = '✓ Valid format';
            errorEl.classList.remove('error');
            errorEl.classList.add('success');
        } else {
            e.target.classList.add('error');
            e.target.classList.remove('valid');
            errorEl.textContent = result.error;
            errorEl.classList.add('error');
            errorEl.classList.remove('success');
        }
    }, 500);  // 500ms debounce
});
```

### 5.2 Edit Game Profile Form

**Endpoint:** `POST /me/settings/game-profiles/{game}/edit`

**Form Fields (Pre-Populated):**

```html
<form method="post" action="{% url 'user_profile:edit_game_profile' game=game_profile.game %}">
    {% csrf_token %}
    
    <!-- Game (read-only) -->
    <label>Game</label>
    <input type="text" value="{{ game_profile.game_display_name }}" readonly>
    <input type="hidden" name="game" value="{{ game_profile.game }}">
    
    <!-- IGN (editable) -->
    <label for="ign">In-Game Name *</label>
    <input 
        type="text" 
        name="ign" 
        id="ign" 
        value="{{ game_profile.ign }}"
        required
    >
    
    <!-- Rank (editable) -->
    <label for="rank">Current Rank</label>
    <input type="text" name="rank" id="rank" value="{{ game_profile.rank_name }}">
    
    <!-- Role (editable) -->
    <label for="role">Main Role</label>
    <input type="text" name="role" id="role" value="{{ game_profile.main_role }}">
    
    <button type="submit" class="btn-primary">Save Changes</button>
    <button type="button" class="btn-danger" onclick="confirmDelete()">Delete Profile</button>
</form>
```

### 5.3 Delete Game Profile

**Endpoint:** `POST /me/settings/game-profiles/{game}/delete`

**Confirmation Dialog:**

```javascript
function confirmDelete() {
    if (confirm('Are you sure you want to delete this game profile? This action cannot be undone.')) {
        document.getElementById('delete-form').submit();
    }
}
```

**Hidden Form:**

```html
<form id="delete-form" method="post" action="{% url 'user_profile:delete_game_profile' game=game_profile.game %}" style="display: none;">
    {% csrf_token %}
</form>
```

---

## 6. API Endpoints

### 6.1 Validation Endpoint

**Endpoint:** `POST /api/validate-ign/`

**Request:**

```json
{
    "game": "valorant",
    "ign": "PlayerOne#1234"
}
```

**Response (Valid):**

```json
{
    "valid": true,
    "ign": "PlayerOne#1234",
    "game": "valorant"
}
```

**Response (Invalid):**

```json
{
    "valid": false,
    "error": "Invalid VALORANT Riot ID. Format: Name#TAG (3-16 chars, #, 3-5 digit tag)",
    "game": "valorant"
}
```

**Implementation:**

```python
# apps/user_profile/views/api.py

@require_http_methods(["POST"])
@login_required
def validate_ign(request):
    """Validate IGN format for a specific game."""
    data = json.loads(request.body)
    game = data.get('game')
    ign = data.get('ign')
    
    if not game or not ign:
        return JsonResponse({'valid': False, 'error': 'Missing game or IGN'}, status=400)
    
    # Get validator
    from apps.user_profile.validators import GameValidators
    validator = GameValidators.get_validator(game)
    
    if validator.is_valid_ign(ign):
        return JsonResponse({'valid': True, 'ign': ign, 'game': game})
    else:
        return JsonResponse({
            'valid': False,
            'error': validator.get_error_message(),
            'game': game
        })
```

### 6.2 Game Profile CRUD Endpoints

**Add Profile:**
- `POST /me/settings/game-profiles/add`
- Payload: `game`, `ign`, `rank`, `role`, `metadata`
- Response: Redirect to settings with success message

**Edit Profile:**
- `POST /me/settings/game-profiles/{game}/edit`
- Payload: `ign`, `rank`, `role`
- Response: Redirect to settings with success message

**Delete Profile:**
- `POST /me/settings/game-profiles/{game}/delete`
- Payload: None (CSRF token only)
- Response: Redirect to settings with success message

---

## 7. Privacy Filtering

### 7.1 Service Layer Filter

**Implementation:**

```python
# apps/user_profile/services/game_profile_service.py

class GameProfileService:
    @staticmethod
    def get_public_game_profiles(user: User, viewer: User = None) -> List[Dict]:
        """
        Get game profiles with privacy filtering.
        
        Args:
            user: Target user
            viewer: Viewing user (None for anonymous)
        
        Returns:
            List of game profile dicts (privacy-filtered)
        """
        profile = user.profile
        
        # Check privacy setting
        if not profile.show_game_profiles and viewer != user:
            return []
        
        # Get all game profiles
        game_profiles = GameProfile.objects.filter(user=user).order_by('-updated_at')
        
        # Determine viewer role
        is_owner = viewer and viewer.id == user.id
        
        # Serialize with privacy filter
        result = []
        for gp in game_profiles:
            data = {
                'game': gp.game,
                'game_display_name': gp.game_display_name,
                'ign': gp.in_game_name,
                'rank_name': gp.rank_name,
                'main_role': gp.main_role,
                'is_verified': gp.is_verified,
            }
            
            # Owner gets full data
            if is_owner:
                data.update({
                    'matches_played': gp.matches_played,
                    'win_rate': gp.win_rate,
                    'kd_ratio': gp.kd_ratio,
                    'peak_rank': gp.peak_rank,
                    'verified_at': gp.verified_at.isoformat() if gp.verified_at else None,
                    'verification_method': gp.verification_method,
                    'created_at': gp.created_at.isoformat(),
                    'updated_at': gp.updated_at.isoformat(),
                    'metadata': gp.metadata,
                })
            
            result.append(data)
        
        return result
```

### 7.2 Template Usage

**Public Profile:**

```html
<!-- templates/user_profile/v2/profile_public.html -->
{% if game_profiles %}
<section class="game-profiles">
    <h2>Game Profiles</h2>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {% for gp in game_profiles %}
        <div class="game-profile-card {{ gp.game }}">
            <div class="card-header">
                <h3>{{ gp.game_display_name }}</h3>
            </div>
            <div class="card-body">
                <p class="ign">{{ gp.ign }}</p>
                {% if gp.rank_name %}
                <p class="rank">{{ gp.rank_name }}</p>
                {% endif %}
                {% if gp.is_verified %}
                <span class="badge-verified">✅ Verified</span>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    </div>
</section>
{% endif %}
```

**Settings Page (Owner):**

```html
<!-- templates/user_profile/v2/profile_settings.html -->
<section class="game-profiles-settings">
    <h2>My Game Profiles</h2>
    
    <div class="profiles-list">
        {% for gp in game_profiles %}
        <div class="profile-item">
            <div class="profile-info">
                <img src="{{ game_logo_url(gp.game) }}" alt="{{ gp.game_display_name }}">
                <div>
                    <h3>{{ gp.game_display_name }}</h3>
                    <p class="ign">{{ gp.ign }}</p>
                    <p class="rank">{{ gp.rank_name }} · {{ gp.main_role }}</p>
                    
                    <!-- Stats (owner only) -->
                    <div class="stats-mini">
                        <span>{{ gp.matches_played }} matches</span>
                        <span>{{ gp.win_rate }}% WR</span>
                    </div>
                </div>
            </div>
            
            <div class="profile-actions">
                <button class="btn-edit" onclick="editProfile('{{ gp.game }}')">Edit</button>
                <button class="btn-delete" onclick="deleteProfile('{{ gp.game }}')">Delete</button>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <button class="btn-add-profile" onclick="showAddForm()">+ Add Game Profile</button>
</section>
```

---

## 8. Error Handling

### 8.1 Client-Side Errors

**Invalid IGN Format:**

```javascript
// Show inline error
document.getElementById('ign-error').textContent = 
    'Invalid format. VALORANT Riot IDs must include #tagline (e.g., Player#1234)';
document.getElementById('ign').classList.add('border-red-500');
```

**Duplicate Game:**

```javascript
// Server returns 400 with error message
if (response.status === 400) {
    const error = await response.json();
    alert(error.message);  // "You already have a VALORANT profile"
}
```

### 8.2 Server-Side Errors

**View Error Handling:**

```python
# apps/user_profile/views/fe_v2.py

@login_required
def add_game_profile(request):
    if request.method != 'POST':
        return redirect('user_profile:profile_settings_v2')
    
    game = request.POST.get('game')
    ign = request.POST.get('ign')
    
    try:
        # Validate game
        if game not in SUPPORTED_GAMES:
            messages.error(request, f"Unsupported game: {game}")
            return redirect('user_profile:profile_settings_v2')
        
        # Check for duplicate
        if GameProfile.objects.filter(user=request.user, game=game).exists():
            messages.error(request, f"You already have a {SUPPORTED_GAMES[game]['name']} profile")
            return redirect('user_profile:profile_settings_v2')
        
        # Validate IGN format
        validator = GameValidators.get_validator(game)
        if not validator.is_valid_ign(ign):
            messages.error(request, validator.get_error_message())
            return redirect('user_profile:profile_settings_v2')
        
        # Create profile via service
        GameProfileService.save_game_profile(
            user=request.user,
            game=game,
            in_game_name=ign,
            rank_name=request.POST.get('rank', ''),
            main_role=request.POST.get('role', ''),
            metadata=extract_metadata(request.POST),
            actor_user_id=request.user.id
        )
        
        messages.success(request, f"✅ {SUPPORTED_GAMES[game]['name']} profile added successfully")
        return redirect('user_profile:profile_settings_v2')
    
    except Exception as e:
        logger.error(f"Error adding game profile: {e}")
        messages.error(request, "An error occurred. Please try again.")
        return redirect('user_profile:profile_settings_v2')
```

---

## 9. Performance Optimizations

### 9.1 Query Optimization

**Prefetch Game Profiles:**

```python
# In view
user = User.objects.select_related('profile').prefetch_related('game_profiles').get(username=username)
```

### 9.2 Caching Strategy

**Cache Public Game Profiles (5 min TTL):**

```python
from django.core.cache import cache

def get_public_game_profiles_cached(user: User, viewer: User = None) -> List[Dict]:
    """Get game profiles with caching."""
    
    # Cache key includes viewer ID for privacy
    viewer_id = viewer.id if viewer else 'anon'
    cache_key = f'gp_public_{user.id}_{viewer_id}'
    
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Fetch from DB
    profiles = GameProfileService.get_public_game_profiles(user, viewer)
    
    # Cache for 5 minutes
    cache.set(cache_key, profiles, 300)
    
    return profiles
```

**Invalidate Cache on Update:**

```python
# In GameProfileService.save_game_profile()
cache.delete(f'gp_public_{user.id}_*')
```

---

## 10. Accessibility

### 10.1 ARIA Labels

```html
<div class="game-profile-card" role="article" aria-labelledby="gp-valorant-title">
    <h3 id="gp-valorant-title">VALORANT Profile</h3>
    
    <div class="profile-ign" aria-label="In-game name">
        <span>PlayerOne#1234</span>
    </div>
    
    <div class="profile-rank" aria-label="Current rank">
        <img src="..." alt="Immortal 3 rank badge">
        <span>Immortal 3</span>
    </div>
    
    <button 
        class="btn-edit" 
        aria-label="Edit VALORANT profile"
        onclick="editProfile('valorant')">
        Edit
    </button>
</div>
```

### 10.2 Keyboard Navigation

**Tab Order:**
1. Game selection dropdown
2. IGN input field
3. Rank input field
4. Role input field
5. Submit button

**Keyboard Shortcuts:**
- `Enter`: Submit form
- `Escape`: Cancel/close modal
- `Tab`: Navigate between fields
- `Shift+Tab`: Navigate backward

---

## 11. Mobile Responsiveness

### 11.1 Breakpoints (Tailwind)

```css
/* Small devices (phones) */
@media (min-width: 640px) {
    .game-profiles-grid {
        @apply grid-cols-1;
    }
}

/* Medium devices (tablets) */
@media (min-width: 768px) {
    .game-profiles-grid {
        @apply grid-cols-2;
    }
}

/* Large devices (desktops) */
@media (min-width: 1024px) {
    .game-profiles-grid {
        @apply grid-cols-3;
    }
}
```

### 11.2 Touch Interactions

```javascript
// Swipe to delete gesture (mobile)
let startX = 0;

document.querySelectorAll('.profile-item').forEach(item => {
    item.addEventListener('touchstart', e => {
        startX = e.touches[0].clientX;
    });
    
    item.addEventListener('touchend', e => {
        const endX = e.changedTouches[0].clientX;
        const diffX = startX - endX;
        
        // Swipe left to reveal delete button
        if (diffX > 100) {
            item.classList.add('swiped-left');
        }
    });
});
```

---

## 12. Testing Checklist

### 12.1 Frontend Tests

**Manual Tests:**
- [ ] Add game profile (11 games)
- [ ] Edit game profile
- [ ] Delete game profile (with confirmation)
- [ ] IGN validation (per-game formats)
- [ ] Privacy filter (public vs owner view)
- [ ] Mobile responsiveness (3 breakpoints)
- [ ] Accessibility (keyboard navigation, screen reader)

**Automated Tests (Playwright):**

```javascript
// tests/e2e/game_profiles.spec.js

test('User can add VALORANT profile', async ({ page }) => {
    await page.goto('/me/settings/');
    
    // Click add profile button
    await page.click('button:has-text("Add Game Profile")');
    
    // Select VALORANT
    await page.selectOption('#game', 'valorant');
    
    // Enter IGN
    await page.fill('#ign', 'TestPlayer#1234');
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Verify success message
    await expect(page.locator('.message.success')).toContainText('VALORANT profile added');
});

test('Invalid IGN format shows error', async ({ page }) => {
    await page.goto('/me/settings/');
    await page.click('button:has-text("Add Game Profile")');
    
    await page.selectOption('#game', 'valorant');
    await page.fill('#ign', 'InvalidFormat');  // Missing #tagline
    
    // Check for error message
    await expect(page.locator('#ign-error')).toContainText('Invalid format');
});
```

---

## 13. Success Metrics

### 13.1 User Experience

**Target Metrics:**
- Time to add game profile: < 30 seconds
- Form validation accuracy: > 95%
- Mobile usability score: > 85/100
- Accessibility score (Lighthouse): > 90/100

### 13.2 Technical Performance

**Target Metrics:**
- Page load time (settings): < 2 seconds
- API response time (validation): < 200ms
- Cache hit rate: > 80%
- Mobile responsiveness: 100% (all breakpoints)

---

**Document Status:** ✅ READY FOR REVIEW  
**Next Phase:** Implementation (split into 3 missions)  
**Dependencies:** Architecture + Admin Design approval
