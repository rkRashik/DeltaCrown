# 🎯 DELTACROWN MASTER IMPLEMENTATION BACKLOG - PART 2
**Continuation of MASTER_IMPLEMENTATION_BACKLOG.md**

---

## 🟠 PHASE 2: HIGH PRIORITY IMPROVEMENTS (Weeks 9-14)

**Goal:** Fix architectural issues and improve code quality

**Success Criteria:**
- Standardized naming conventions
- Clean template structure
- Accessibility compliant
- No hardcoded configuration

---

### 🎯 SPRINT 5: Configuration & Standards (Week 9-10)

#### **TASK 5.1: Extract All Hardcoded Configuration**
**Priority:** 🟠 HIGH  
**Effort:** 8 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #10

**Problem:**
- Magic numbers scattered everywhere
- Same constant defined in 3 places with DIFFERENT values
- Cannot change configuration without code search-and-replace

**Examples:**
```python
# TEAM_MAX_ROSTER defined differently!
apps/teams/models/_legacy.py:16  → TEAM_MAX_ROSTER = 8
apps/teams/views/create.py:40    → MAX_ROSTER_SIZE = 10
apps/teams/validators.py:12      → ROSTER_LIMIT = 12

# More magic numbers:
if team.memberships.count() >= 8:  # What is 8?
if tag_length < 2 or tag_length > 10:  # Why 2 and 10?
if timezone.now() - created_at > timedelta(days=30):  # Why 30?
```

**What to Do:**

**1. Create `apps/teams/constants.py`:**
```python
"""
Team app configuration constants.
SINGLE SOURCE OF TRUTH for all team-related configuration.
"""

class TeamConstants:
    """Team management constants."""
    
    # === ROSTER LIMITS ===
    MIN_ROSTER_SIZE = 1
    MAX_ROSTER_SIZE = 8  # Default maximum
    MIN_SUBSTITUTES = 0
    MAX_SUBSTITUTES = 2
    
    # === NAME/TAG CONSTRAINTS ===
    # (Already defined in Task 1.3, ensure consistency)
    NAME_MIN_LENGTH = 3
    NAME_MAX_LENGTH = 100
    TAG_MIN_LENGTH = 2
    TAG_MAX_LENGTH = 10
    
    # === INVITE SYSTEM ===
    INVITE_EXPIRY_DAYS = 7
    MAX_PENDING_INVITES_PER_TEAM = 10
    MAX_PENDING_INVITES_PER_USER = 5
    
    # === JOIN REQUESTS ===
    JOIN_REQUEST_EXPIRY_DAYS = 14
    MAX_PENDING_JOIN_REQUESTS = 20
    
    # === TEAM CREATION ===
    DRAFT_TTL_MINUTES = 30
    MIN_TEAM_DESCRIPTION_LENGTH = 10
    MAX_TEAM_DESCRIPTION_LENGTH = 2000
    
    # === MEDIA UPLOADS ===
    MAX_LOGO_SIZE_MB = 5
    MAX_BANNER_SIZE_MB = 10
    ALLOWED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'webp']
    
    # === CACHE TTLs ===
    TEAM_CACHE_TTL = 300  # 5 minutes
    TEAM_LIST_CACHE_TTL = 180  # 3 minutes
    STATS_CACHE_TTL = 600  # 10 minutes
    RANKING_CACHE_TTL = 900  # 15 minutes
    
    # === PAGINATION ===
    TEAMS_PER_PAGE = 20
    MEMBERS_PER_PAGE = 50
    MATCHES_PER_PAGE = 15
    
    # === ACTIVITY TRACKING ===
    INACTIVE_THRESHOLD_DAYS = 90
    DISBANDED_AFTER_DAYS = 180  # Auto-disband if inactive
    
    # === PERMISSIONS ===
    OWNER_TRANSFER_COOLDOWN_DAYS = 7
    KICK_COOLDOWN_HOURS = 24  # Can't kick same user twice in 24h
    
    # === NOTIFICATIONS ===
    NOTIFY_CAPTAIN_ON_JOIN_REQUEST = True
    NOTIFY_MEMBERS_ON_ROSTER_CHANGE = True
    NOTIFY_ON_ACHIEVEMENT = True


class RankingConstants:
    """Team ranking constants."""
    
    # === POINT MULTIPLIERS ===
    TOURNAMENT_WIN_MULTIPLIER = 1.5
    TOURNAMENT_RUNNER_UP_MULTIPLIER = 1.2
    
    # === DECAY ===
    DECAY_RATE_PER_MONTH = 0.05  # 5% per month
    MAX_DECAY_PERCENTAGE = 0.5  # Max 50% total
    INACTIVITY_THRESHOLD_MONTHS = 1
    
    # === POINT CAPS ===
    MAX_ACHIEVEMENT_BONUS = 1000
    MAX_MEMBER_BONUS = 500


class MatchConstants:
    """Match/tournament constants."""
    
    CHECK_IN_WINDOW_MINUTES = 30
    DEFAULT_MATCH_DURATION_MINUTES = 90
    FORFEIT_TIMEOUT_MINUTES = 15
```

**2. Replace All Magic Numbers:**

Before:
```python
if team.memberships.count() >= 8:
    raise ValidationError("Team roster is full")
```

After:
```python
from apps.teams.constants import TeamConstants

if team.memberships.count() >= TeamConstants.MAX_ROSTER_SIZE:
    raise ValidationError(f"Team roster is full (max {TeamConstants.MAX_ROSTER_SIZE})")
```

**3. Find and Replace All Occurrences:**
```bash
# Find magic numbers
grep -r "if.*>= 8\|if.*<= 8" apps/teams/
grep -r "timedelta(days=30)" apps/teams/
grep -r "timedelta(days=7)" apps/teams/

# Replace systematically
# Document each change in commit message
```

**4. Add Settings Override (Optional):**
```python
# settings.py
TEAMS_CONFIG = {
    'MAX_ROSTER_SIZE': 10,  # Override default
    'INVITE_EXPIRY_DAYS': 14,
}

# constants.py
from django.conf import settings

class TeamConstants:
    MAX_ROSTER_SIZE = getattr(settings, 'TEAMS_CONFIG', {}).get(
        'MAX_ROSTER_SIZE', 8  # Default
    )
```

**Testing:**
- No hardcoded numbers in views ✓
- All constants used correctly ✓
- Easy to change configuration ✓
- Settings override works ✓

**Expected Outcome:**
- Single source of truth for config
- Easy to adjust values
- Self-documenting code
- Faster onboarding

---

#### **TASK 5.2: Standardize Naming Conventions**
**Priority:** 🟡 MEDIUM  
**Effort:** 12 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issue #14

**Problem:**
- Inconsistent naming across codebase
- `team_list_view` vs `TeamListView` (function vs class)
- `get_team_members` vs `fetch_team_roster` (same thing!)
- `is_captain` vs `has_captain_role` vs `captain_check`

**What to Do:**

**1. Define Naming Standards:**

**Views:**
- Function-based views: `{model}_{action}_view`
  - Examples: `team_list_view`, `team_create_view`, `team_edit_view`
- Class-based views: `{Model}{Action}View`
  - Examples: `TeamListView`, `TeamCreateView`, `TeamEditView`

**Service Functions:**
- Actions: `{verb}_{noun}` 
  - Examples: `create_team`, `update_team`, `delete_team`
- Queries: `get_{noun}` or `fetch_{noun}`
  - Examples: `get_team_members`, `get_active_memberships`
- Checkers: `is_{condition}` or `has_{permission}`
  - Examples: `is_captain`, `has_edit_permission`

**Model Methods:**
- Actions: `{verb}_{noun}`
  - Examples: `team.add_member()`, `team.remove_member()`
- Properties: `{noun}` or `{adjective}_{noun}`
  - Examples: `team.active_members`, `team.total_points`
- Boolean checks: `is_{condition}` or `has_{noun}`
  - Examples: `team.is_active`, `team.has_open_slots`

**2. Create Naming Reference Document:**
```markdown
# docs/development/naming-conventions.md

## Naming Conventions

### Views
- Function views: `{model}_{action}_view`
- Class views: `{Model}{Action}View`

### Services
- CRUD: create_, update_, delete_, get_
- Actions: {verb}_{noun}
- Checks: is_, has_, can_

### Models
- Methods: {verb}_{noun}
- Properties: {noun} or {adjective}_{noun}
- Booleans: is_, has_

### Variables
- Lowercase with underscores: team_members, active_count
- Descriptive names: user_team_memberships (not utm)
```

**3. Rename Inconsistent Functions:**

**High Priority (Frequently Used):**
- `fetch_team_roster` → `get_team_members` (pick one, stick with it)
- `captain_check` → `is_captain`
- `has_captain_role` → `is_captain`
- `TeamMember` → `TeamMembership` (model naming confusion)

**Create Aliases During Transition:**
```python
# Temporary backward compatibility
def fetch_team_roster(*args, **kwargs):
    """DEPRECATED: Use get_team_members() instead."""
    warnings.warn(
        "fetch_team_roster is deprecated, use get_team_members",
        DeprecationWarning,
        stacklevel=2
    )
    return get_team_members(*args, **kwargs)
```

**4. Update All Callers:**
```bash
# Find all uses of old name
grep -r "fetch_team_roster" apps/

# Update to new name
# Remove aliases after 2 sprints
```

**Testing:**
- All renamed functions work ✓
- No import errors ✓
- Deprecated warnings appear ✓
- Documentation updated ✓

**Expected Outcome:**
- Consistent naming
- Predictable function names
- Easier code navigation
- Better IDE autocomplete

---

#### **TASK 5.3: Frontend Template Cleanup**
**Priority:** 🟡 MEDIUM  
**Effort:** 14 hours  
**Source:** TEAM_APP_AUDIT_REPORT.md - Issues #12, #19, #20, #22

**Problem:**
- Duplicate HTML blocks (member card in 3 templates)
- 500+ lines of inline JavaScript
- Duplicate CSS definitions
- Missing CSRF tokens
- Hard-coded URLs

**What to Do:**

**1. Extract Reusable Components:**

Create `templates/teams/components/`:
```html
<!-- templates/teams/components/member_card.html -->
{% load static %}

<div class="member-card" data-member-id="{{ member.id }}">
    <div class="member-avatar">
        <img src="{{ member.avatar.url|default:'/static/img/default-avatar.png' }}" 
             alt="{{ member.name }} avatar">
    </div>
    <div class="member-info">
        <h4 class="member-name">{{ member.name }}</h4>
        <p class="member-role">{{ member.get_role_display }}</p>
        {% if member.is_captain %}
            <span class="badge badge-captain">Captain</span>
        {% endif %}
    </div>
    {% if show_actions %}
        <div class="member-actions">
            {% include "teams/components/member_actions.html" %}
        </div>
    {% endif %}
</div>
```

**Usage in other templates:**
```html
<!-- templates/teams/detail.html -->
{% for member in team.members %}
    {% include "teams/components/member_card.html" with member=member show_actions=False %}
{% endfor %}
```

**2. Move Inline JavaScript to Static Files:**

Before (in template):
```html
<script>
function filterTeams() { /* 200 lines */ }
function sortTeams() { /* 150 lines */ }
function loadMore() { /* 100 lines */ }
</script>
```

After:
```html
<!-- templates/teams/list.html -->
{% block extra_js %}
    <script src="{% static 'js/teams/list.js' %}"></script>
{% endblock %}
```

Create `static/js/teams/list.js`:
```javascript
// Team list functionality
class TeamList {
    constructor() {
        this.currentFilter = 'all';
        this.currentSort = 'newest';
        this.page = 1;
        this.initEventListeners();
    }
    
    initEventListeners() {
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleFilter(e));
        });
        // ... more event listeners
    }
    
    handleFilter(event) {
        // Filter logic
    }
    
    sortTeams(sortBy) {
        // Sort logic
    }
    
    loadMore() {
        // Load more logic
    }
}

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    new TeamList();
});
```

**3. Consolidate CSS:**

Remove inline styles:
```html
<!-- BAD -->
<div style="margin-top: 20px; padding: 15px; background: #f5f5f5;">
    ...
</div>

<!-- GOOD -->
<div class="info-card">
    ...
</div>
```

Update `static/css/teams.css`:
```css
.info-card {
    margin-top: 20px;
    padding: 15px;
    background: #f5f5f5;
}
```

**4. Fix Security Issues:**

Add CSRF tokens to all POST forms:
```html
<!-- Before -->
<form method="POST" action="{% url 'teams:invite' %}">
    <input name="email" type="email">
    <button>Send</button>
</form>

<!-- After -->
<form method="POST" action="{% url 'teams:invite' %}">
    {% csrf_token %}  <!-- ADDED -->
    <input name="email" type="email">
    <button>Send</button>
</form>
```

**5. Replace Hard-coded URLs:**

```html
<!-- Before -->
<a href="/teams/{{ team.id }}/manage/">Manage</a>

<!-- After -->
<a href="{% url 'teams:manage' team.id %}">Manage</a>
```

**6. Add Accessibility:**

```html
<!-- Before -->
<button onclick="deleteTeam()">Delete</button>
<img src="{{ team.logo }}">

<!-- After -->
<button onclick="deleteTeam()" 
        aria-label="Delete {{ team.name }}"
        role="button">
    Delete
</button>
<img src="{{ team.logo }}" 
     alt="{{ team.name }} logo"
     loading="lazy">
```

**Testing:**
- All templates render correctly ✓
- No inline styles ✓
- JavaScript works (no console errors) ✓
- All forms have CSRF tokens ✓
- URLs generated correctly ✓
- Accessibility checker passes ✓

**Expected Outcome:**
- Reusable template components
- Cleaner HTML
- Better performance (cached JS/CSS)
- Improved security
- Better accessibility

---

### 🎯 SPRINT 6: Role System Overhaul (Week 11-12)

#### **TASK 6.1: Fix Owner/Captain Confusion**
**Priority:** 🔴 CRITICAL  
**Effort:** 16 hours  
**Source:** TEAM_FOCUSED_AUDIT_REPORT.md - Role Management Section

**Problem:**
- Three overlapping concepts:
  - `TeamMembership.role = 'OWNER'` (team ownership)
  - `TeamMembership.role = 'CAPTAIN'` (similar to owner?)
  - `Team.captain` ForeignKey (points to UserProfile)
  - `TeamMembership.is_captain` boolean (tournament designation)
- Users confused about hierarchy
- Permission checks inconsistent

**Current Chaos:**
```python
# Is this user the captain?
# Three different checks!!!

# Check 1: Team.captain
if team.captain == user.profile:
    # Can edit team

# Check 2: Role-based
if membership.role == 'CAPTAIN':
    # Can also edit team?

# Check 3: Boolean flag
if membership.is_captain:
    # Is this for tournaments only?
```

**What to Do:**

**1. Define Clear Role Hierarchy:**

**OWNER** - Full control (cannot be removed, transfers ownership)
- Can do everything
- Can transfer ownership
- Can disband team
- One per team (enforced)

**CAPTAIN** - Tournament designation (set by owner for specific tournament)
- `is_captain` boolean flag
- Used for tournament registration
- Can change per tournament
- Optional (some games require captain ID)

**Remove `CAPTAIN` from role choices** - It's redundant with OWNER

**2. Database Changes:**

```python
# apps/teams/models/membership.py

class TeamMembership(models.Model):
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),  # Keep - team ownership
        # ('CAPTAIN', 'Captain'),  # REMOVE - use is_captain instead
        ('MANAGER', 'Manager'),
        ('PLAYER', 'Player'),
        ('SUBSTITUTE', 'Substitute'),
        ('COACH', 'Coach'),
        ('ANALYST', 'Analyst'),
    ]
    
    role = CharField(max_length=20, choices=ROLE_CHOICES, default='PLAYER')
    
    # Tournament captain designation (separate from ownership)
    is_captain = BooleanField(
        default=False,
        help_text="Designated captain for tournament registration (game-specific)"
    )
    
    class Meta:
        constraints = [
            # Only ONE owner per team
            models.UniqueConstraint(
                fields=['team'],
                condition=Q(role='OWNER'),
                name='unique_team_owner'
            ),
        ]
```

**3. Data Migration:**

```python
# Migration: Convert CAPTAIN role to OWNER

def migrate_captains_to_owners(apps, schema_editor):
    TeamMembership = apps.get_model('teams', 'TeamMembership')
    
    # Find all CAPTAIN memberships
    captains = TeamMembership.objects.filter(role='CAPTAIN')
    
    for membership in captains:
        # Check if team already has OWNER
        has_owner = TeamMembership.objects.filter(
            team=membership.team,
            role='OWNER'
        ).exists()
        
        if has_owner:
            # Team has owner, convert captain to MANAGER
            membership.role = 'MANAGER'
            membership.is_captain = True  # Keep tournament captain designation
        else:
            # No owner, convert captain to OWNER
            membership.role = 'OWNER'
        
        membership.save()
```

**4. Remove Team.captain Field:**

```python
# apps/teams/models/team.py

class Team(models.Model):
    # Remove this field (redundant)
    # captain = ForeignKey(UserProfile, ...)  # DELETE
    
    # Add property for backward compatibility
    @property
    def captain(self):
        """Get team owner (backward compatibility)."""
        owner_membership = self.memberships.filter(role='OWNER').first()
        return owner_membership.user if owner_membership else None
    
    def get_tournament_captain(self, tournament=None):
        """Get designated tournament captain."""
        captain_membership = self.memberships.filter(
            is_captain=True,
            status='ACTIVE'
        ).first()
        return captain_membership.user if captain_membership else self.captain
```

**5. Update Permission Checks:**

```python
# apps/teams/permissions.py

class TeamPermissions:
    @staticmethod
    def is_owner(user, team):
        """Check if user is team owner."""
        return team.memberships.filter(
            user=user,
            role='OWNER',
            status='ACTIVE'
        ).exists()
    
    @staticmethod
    def can_edit_team(user, team):
        """Owner and Manager can edit."""
        return team.memberships.filter(
            user=user,
            role__in=['OWNER', 'MANAGER'],
            status='ACTIVE'
        ).exists()
    
    @staticmethod
    def can_manage_roster(user, team):
        """Owner and Manager can manage roster."""
        return TeamPermissions.can_edit_team(user, team)
    
    @staticmethod
    def can_transfer_ownership(user, team):
        """Only owner can transfer ownership."""
        return TeamPermissions.is_owner(user, team)
    
    @staticmethod
    def can_disband_team(user, team):
        """Only owner can disband."""
        return TeamPermissions.is_owner(user, team)
```

**6. Update UI/UX:**

```html
<!-- Show clear role badges -->
{% if member.role == 'OWNER' %}
    <span class="badge badge-owner">👑 Owner</span>
{% endif %}

{% if member.is_captain %}
    <span class="badge badge-captain">Ⓒ Captain</span>
{% endif %}

<!-- Tooltip to explain -->
<i class="info-icon" 
   data-tooltip="Captain is designated for tournament registration only">
   ℹ️
</i>
```

**Testing:**
- Only one owner per team (constraint works) ✓
- Owner can do everything ✓
- Captain designation separate from ownership ✓
- Permission checks use correct logic ✓
- UI shows correct badges ✓
- Migration converts all CAPTAIN to OWNER/MANAGER ✓

**Expected Outcome:**
- Clear role hierarchy
- No confusion between owner and captain
- is_captain used only for tournaments
- Better permission management

---

#### **TASK 6.2: Add Esports Professional Roles**
**Priority:** 🟡 MEDIUM  
**Effort:** 10 hours  
**Source:** TEAM_FOCUSED_AUDIT_REPORT.md - Role Management Section

**Problem:**
- Only basic roles (Owner, Player, Substitute)
- Missing professional esports roles:
  - Head Coach, Assistant Coach
  - Team Manager, General Manager
  - Analyst, Performance Coach
  - Content Creator, Social Media Manager

**What to Do:**

**1. Expand Role Choices:**

```python
# apps/teams/models/membership.py

class TeamMembership(models.Model):
    ROLE_CHOICES = [
        # === Core Team ===
        ('OWNER', 'Owner'),
        ('PLAYER', 'Player'),
        ('SUBSTITUTE', 'Substitute'),
        
        # === Coaching Staff ===
        ('HEAD_COACH', 'Head Coach'),
        ('ASSISTANT_COACH', 'Assistant Coach'),
        ('PERFORMANCE_COACH', 'Performance Coach'),
        ('ANALYST', 'Analyst'),
        ('STRATEGIST', 'Strategist'),
        
        # === Management ===
        ('GENERAL_MANAGER', 'General Manager'),
        ('TEAM_MANAGER', 'Team Manager'),
        
        # === Support Staff ===
        ('CONTENT_CREATOR', 'Content Creator'),
        ('SOCIAL_MEDIA_MANAGER', 'Social Media Manager'),
        ('GRAPHIC_DESIGNER', 'Graphic Designer'),
    ]
    
    role = CharField(max_length=30, choices=ROLE_CHOICES, default='PLAYER')
```

**2. Create Role Categories:**

```python
# apps/teams/constants.py

class RoleCategories:
    """Categorize roles for permissions and UI display."""
    
    PLAYING_ROLES = ['PLAYER', 'SUBSTITUTE']
    
    COACHING_ROLES = [
        'HEAD_COACH',
        'ASSISTANT_COACH',
        'PERFORMANCE_COACH',
        'STRATEGIST',
        'ANALYST',
    ]
    
    MANAGEMENT_ROLES = [
        'OWNER',
        'GENERAL_MANAGER',
        'TEAM_MANAGER',
    ]
    
    SUPPORT_ROLES = [
        'CONTENT_CREATOR',
        'SOCIAL_MEDIA_MANAGER',
        'GRAPHIC_DESIGNER',
    ]
    
    # Permission groups
    CAN_EDIT_TEAM = ['OWNER', 'GENERAL_MANAGER', 'TEAM_MANAGER']
    CAN_MANAGE_ROSTER = ['OWNER', 'GENERAL_MANAGER', 'HEAD_COACH']
    CAN_SCHEDULE_PRACTICE = MANAGEMENT_ROLES + COACHING_ROLES
    CAN_VIEW_ANALYTICS = MANAGEMENT_ROLES + COACHING_ROLES + ['ANALYST']
```

**3. Add Role Limits:**

```python
# apps/teams/models/team.py

class Team(models.Model):
    # ...existing fields...
    
    def get_role_limit(self, role):
        """Get maximum allowed for each role."""
        ROLE_LIMITS = {
            'OWNER': 1,  # Only one owner
            'HEAD_COACH': 1,  # One head coach
            'GENERAL_MANAGER': 1,
            'TEAM_MANAGER': 2,
            'ASSISTANT_COACH': 3,
            # No limit for players/subs (handled by roster size)
        }
        return ROLE_LIMITS.get(role, None)  # None = no limit
    
    def can_add_role(self, role):
        """Check if can add another member with this role."""
        limit = self.get_role_limit(role)
        if limit is None:
            return True
        
        current_count = self.memberships.filter(
            role=role,
            status='ACTIVE'
        ).count()
        
        return current_count < limit
```

**4. Update UI:**

**Group by Category:**
```html
<!-- templates/teams/roster.html -->
<div class="roster-section">
    <h3>Players</h3>
    {% for member in team.get_members_by_category.playing %}
        {% include "teams/components/member_card.html" %}
    {% endfor %}
</div>

<div class="roster-section">
    <h3>Coaching Staff</h3>
    {% for member in team.get_members_by_category.coaching %}
        {% include "teams/components/member_card.html" %}
    {% endfor %}
</div>

<div class="roster-section">
    <h3>Management</h3>
    {% for member in team.get_members_by_category.management %}
        {% include "teams/components/member_card.html" %}
    {% endfor %}
</div>
```

**Add Role Icons:**
```python
# apps/teams/utils/role_display.py

ROLE_ICONS = {
    'OWNER': '👑',
    'PLAYER': '🎮',
    'SUBSTITUTE': '🔄',
    'HEAD_COACH': '📋',
    'ANALYST': '📊',
    'GENERAL_MANAGER': '💼',
    # ... etc
}

ROLE_COLORS = {
    'OWNER': '#FFD700',  # Gold
    'HEAD_COACH': '#4A90E2',  # Blue
    'ANALYST': '#7B68EE',  # Purple
    # ... etc
}
```

**5. Update Permissions:**

```python
# apps/teams/permissions.py

def can_edit_team(user, team):
    """Check if user can edit team settings."""
    from apps.teams.constants import RoleCategories
    
    return team.memberships.filter(
        user=user,
        role__in=RoleCategories.CAN_EDIT_TEAM,
        status='ACTIVE'
    ).exists()
```

**Testing:**
- All roles selectable ✓
- Role limits enforced ✓
- Permissions work with new roles ✓
- UI groups roles correctly ✓
- Icons/colors display ✓

**Expected Outcome:**
- Professional esports role structure
- Clear role categorization
- Better permission management
- More realistic team organization

---

### 🎯 SPRINT 7: Ranking System Enhancement (Week 13-14)

#### **TASK 7.1: Add Game-Specific Rankings**
**Priority:** 🟡 MEDIUM  
**Effort:** 12 hours  
**Source:** TEAM_FOCUSED_AUDIT_REPORT.md - Ranking System Section

**Problem:**
- All teams ranked together regardless of game
- Valorant team #1 (5000 points) vs PUBG team #1 (1200 points) in same leaderboard
- Cannot compare teams within same game fairly

**What to Do:**

**1. Create TeamGameRanking Model:**

```python
# apps/teams/models/ranking.py

class TeamGameRanking(models.Model):
    """Per-game ranking for teams."""
    
    team = ForeignKey(Team, on_delete=CASCADE, related_name='game_rankings')
    game = CharField(max_length=20)  # 'valorant', 'cs2', etc.
    
    # Game-specific ranking
    game_points = IntegerField(default=0)
    game_rank = IntegerField(null=True, blank=True)
    division = CharField(max_length=20, null=True, blank=True)
    # 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Master', 'Champion'
    
    # Global cross-game ranking (normalized ELO)
    global_elo = IntegerField(default=1000)
    
    # Streak tracking
    win_streak = IntegerField(default=0)
    tournament_streak = IntegerField(default=0)
    
    # Statistics
    tournaments_entered = IntegerField(default=0)
    tournaments_won = IntegerField(default=0)
    top_4_finishes = IntegerField(default=0)
    
    # Timestamps
    last_tournament_date = DateTimeField(null=True, blank=True)
    updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('team', 'game')
        indexes = [
            Index(fields=['game', '-game_points']),  # Per-game leaderboard
            Index(fields=['-global_elo']),  # Global leaderboard
            Index(fields=['game', 'division', '-game_points']),
        ]
        ordering = ['-game_points']
    
    def __str__(self):
        return f"{self.team.name} - {self.game} ({self.game_points} pts)"
```

**2. Create Rank Tier System:**

```python
# apps/teams/constants.py

class RankTiers:
    """Rank tier thresholds per game."""
    
    VALORANT_TIERS = [
        {'name': 'Bronze', 'min': 0, 'max': 999, 'color': '#CD7F32'},
        {'name': 'Silver', 'min': 1000, 'max': 2499, 'color': '#C0C0C0'},
        {'name': 'Gold', 'min': 2500, 'max': 4999, 'color': '#FFD700'},
        {'name': 'Platinum', 'min': 5000, 'max': 7499, 'color': '#E5E4E2'},
        {'name': 'Diamond', 'min': 7500, 'max': 9999, 'color': '#B9F2FF'},
        {'name': 'Master', 'min': 10000, 'max': 14999, 'color': '#9370DB'},
        {'name': 'Champion', 'min': 15000, 'max': None, 'color': '#FF4500'},
    ]
    
    CS2_TIERS = [
        # Different thresholds for CS2
        {'name': 'Bronze', 'min': 0, 'max': 1499, 'color': '#CD7F32'},
        {'name': 'Silver', 'min': 1500, 'max': 3499, 'color': '#C0C0C0'},
        # ... etc
    ]
    
    @classmethod
    def get_tier(cls, game, points):
        """Get tier for given game and points."""
        tiers = getattr(cls, f'{game.upper()}_TIERS', cls.VALORANT_TIERS)
        
        for tier in tiers:
            if tier['max'] is None or points <= tier['max']:
                return tier
        
        return tiers[0]  # Default to lowest tier
```

**3. Update Ranking Service:**

```python
# apps/teams/services/ranking_service.py

class TeamRankingService:
    def award_tournament_points(self, team, tournament, placement):
        """Award points for tournament placement."""
        
        # Get or create game-specific ranking
        game_ranking, _ = TeamGameRanking.objects.get_or_create(
            team=team,
            game=tournament.game,
            defaults={'global_elo': 1000}
        )
        
        # Calculate points
        points = self._calculate_placement_points(tournament, placement)
        
        # Update game-specific points
        game_ranking.game_points += points
        game_ranking.tournaments_entered += 1
        
        if placement == 1:
            game_ranking.tournaments_won += 1
            game_ranking.win_streak += 1
        else:
            game_ranking.win_streak = 0
        
        if placement <= 4:
            game_ranking.top_4_finishes += 1
        
        # Update division
        tier = RankTiers.get_tier(tournament.game, game_ranking.game_points)
        game_ranking.division = tier['name']
        
        game_ranking.last_tournament_date = timezone.now()
        game_ranking.save()
        
        # Update global ELO
        self._update_global_elo(team, tournament, placement)
```

**4. Create Leaderboard Views:**

```python
# apps/teams/views/rankings.py

def game_rankings_view(request, game_slug):
    """Show rankings for specific game."""
    
    rankings = TeamGameRanking.objects.filter(
        game=game_slug,
        team__is_active=True
    ).select_related('team').order_by('-game_points')[:100]
    
    # Add rank numbers
    for i, ranking in enumerate(rankings, 1):
        ranking.display_rank = i
    
    return render(request, 'teams/rankings.html', {
        'game': game_slug,
        'rankings': rankings,
        'tiers': RankTiers.get_tier(game_slug, 0),  # Get tier list
    })


def global_rankings_view(request):
    """Show cross-game rankings using ELO."""
    
    # Get best ranking per team
    rankings = TeamGameRanking.objects.filter(
        team__is_active=True
    ).values('team').annotate(
        max_elo=Max('global_elo')
    ).order_by('-max_elo')[:100]
    
    return render(request, 'teams/global_rankings.html', {
        'rankings': rankings,
    })
```

**5. Update UI:**

```html
<!-- templates/teams/rankings.html -->
<div class="leaderboard">
    <h2>{{ game|title }} Rankings</h2>
    
    <div class="tier-filters">
        <button data-tier="all" class="active">All</button>
        {% for tier in tiers %}
            <button data-tier="{{ tier.name }}" 
                    style="border-color: {{ tier.color }}">
                {{ tier.name }}
            </button>
        {% endfor %}
    </div>
    
    <table class="ranking-table">
        <thead>
            <tr>
                <th>Rank</th>
                <th>Team</th>
                <th>Division</th>
                <th>Points</th>
                <th>Tournaments</th>
                <th>Win Rate</th>
            </tr>
        </thead>
        <tbody>
            {% for ranking in rankings %}
            <tr>
                <td class="rank">#{{ ranking.display_rank }}</td>
                <td>
                    <a href="{% url 'teams:detail' ranking.team.slug %}">
                        <img src="{{ ranking.team.logo.url }}" alt="">
                        {{ ranking.team.name }}
                    </a>
                </td>
                <td>
                    <span class="badge badge-{{ ranking.division|lower }}"
                          style="background: {{ ranking.get_tier_color }}">
                        {{ ranking.division }}
                    </span>
                </td>
                <td>{{ ranking.game_points }}</td>
                <td>{{ ranking.tournaments_entered }}</td>
                <td>{{ ranking.win_rate }}%</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

**Testing:**
- Separate leaderboards per game ✓
- Tier badges display correctly ✓
- Points calculated correctly ✓
- Global ELO works ✓
- Streaks tracked ✓

**Expected Outcome:**
- Fair game-specific rankings
- Visual rank progression (tiers)
- Global cross-game comparison
- Better competitive experience

---

**END OF PHASE 2**

**Phase 2 Summary:**
- ✅ All hardcoded config centralized
- ✅ Naming conventions standardized
- ✅ Templates cleaned up
- ✅ Role system clarified (Owner vs Captain)
- ✅ Professional esports roles added
- ✅ Game-specific rankings implemented

**Ready for Phase 3: Game Architecture Centralization** →

