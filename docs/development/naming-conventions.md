# DeltaCrown Naming Conventions
**Last Updated:** December 2025  
**Scope:** Teams, Games, Rankings, Tournaments modules

---

## Overview

This document defines naming standards for the DeltaCrown codebase to ensure consistency, predictability, and maintainability across all modules.

---

## 1. Views

### Function-Based Views

**Pattern:** `{model}_{action}_view`

**Examples:**
```python
# Good
def team_list_view(request):
def team_create_view(request):
def team_edit_view(request, slug):
def game_leaderboard_view(request, game_slug):
def global_leaderboard_view(request):

# Bad
def TeamList(request)  # Use class-based view for this style
def create_team(request)  # Missing '_view' suffix
def editTeam(request)  # camelCase not allowed
```

### Class-Based Views

**Pattern:** `{Model}{Action}View`

**Examples:**
```python
# Good
class TeamListView(ListView):
class TeamCreateView(CreateView):
class TeamUpdateView(UpdateView):
class GameDetailView(DetailView):

# Bad
class team_list_view(ListView)  # Use function-based for snake_case
class TeamList(ListView)  # Missing 'View' suffix
class TeamViewList(ListView)  # Incorrect word order
```

### API Views (DRF)

**Pattern:** `{Model}{Action}APIView` or `{Model}ViewSet`

**Examples:**
```python
# Good
class TeamCreateAPIView(APIView):
class TeamViewSet(ModelViewSet):
class RankingReadOnlyViewSet(ReadOnlyModelViewSet):

# Bad
class TeamAPI(APIView)  # Missing 'APIView' suffix
class CreateTeamView(APIView)  # Not descriptive enough
```

---

## 2. Service Layer

### Service Classes

**Pattern:** `{Model}Service` (Singleton or utility class)

**Examples:**
```python
# Good
class TeamService:
    @staticmethod
    def create_team(data):
        
class GameService:
    @staticmethod
    def get_roster_config(game):

class GameRankingService:
    @staticmethod
    def award_tournament_points(team, tournament, placement):
```

### Service Methods

**CRUD Operations:**
- `create_{noun}(...)` - Create new record
- `update_{noun}(...)` - Update existing record
- `delete_{noun}(...)` - Delete record
- `get_{noun}(...)` - Retrieve single record
- `list_{noun}(...)` - Retrieve multiple records

**Examples:**
```python
# Good
def create_team(owner, data):
def update_team_roster(team, roster_data):
def delete_team_member(membership):
def get_team_by_slug(slug):
def list_active_teams(game=None):

# Bad
def team_create(owner, data)  # Wrong word order
def fetchTeamRoster(team)  # camelCase not allowed
def delete(membership)  # Not descriptive enough
```

**Validation Methods:**
- `validate_{noun}(...)` - Validate data
- `is_{condition}(...)` - Boolean check
- `has_{permission}(...)` - Permission check
- `can_{action}(...)` - Ability check

**Examples:**
```python
# Good
def validate_roster_size(game, total_players):
def is_captain(user, team):
def has_edit_permission(user, team):
def can_invite_members(team):

# Bad
def roster_valid(game, total_players)  # Not a verb
def captain_check(user, team)  # Use 'is_'
def check_permission(user, team)  # Not specific enough
```

---

## 3. Models

### Model Names

**Pattern:** Singular noun, PascalCase

**Examples:**
```python
# Good
class Team(models.Model):
class TeamMembership(models.Model):
class GameRosterConfig(models.Model):
class TeamGameRanking(models.Model):

# Bad
class Teams(models.Model)  # Should be singular
class team(models.Model)  # Should be PascalCase
class TeamMember(models.Model)  # Ambiguous (use TeamMembership)
```

### Model Methods

**Instance Methods:**
- `{verb}_{noun}()` - Actions
- `get_{noun}()` - Retrievals
- `{adjective}_{noun}` - Properties (use @property)

**Examples:**
```python
class Team(models.Model):
    # Good
    def add_member(self, user, role):
    def remove_member(self, user):
    def get_active_members(self):
    
    @property
    def active_members(self):
        return self.memberships.filter(status='ACTIVE')
    
    @property
    def is_full(self):
        return self.memberships.count() >= self.max_roster_size
    
    # Bad
    def addMember(self, user, role):  # camelCase
    def members_add(self, user, role):  # Wrong word order
    def active(self):  # Not descriptive (use 'is_active' or 'active_members')
```

### Boolean Fields/Methods

**Pattern:** `is_{condition}` or `has_{noun}`

**Examples:**
```python
# Good
is_active = models.BooleanField(default=True)
is_captain = models.BooleanField(default=False)
has_logo = models.BooleanField(default=False)

def is_owner(self, user):
def has_open_slots(self):
def can_accept_members(self):

# Bad
active = models.BooleanField()  # Ambiguous
captain = models.BooleanField()  # Use 'is_captain'
def owner(self, user):  # Use 'is_owner'
```

---

## 4. Templates

### Template File Names

**Pages:** `{model}_{action}.html`

**Components:** `_{component_name}.html` (prefix with underscore)

**Examples:**
```
templates/
├── teams/
│   ├── team_list.html              # Good: Page template
│   ├── team_detail.html            # Good: Page template
│   ├── team_create.html            # Good: Page template
│   ├── rankings/
│   │   ├── game_leaderboard.html   # Good: Page template
│   │   └── global_leaderboard.html # Good: Page template
│   └── components/
│       ├── _ranking_row.html       # Good: Component (underscore prefix)
│       ├── _tier_badge.html        # Good: Component
│       └── _team_card.html         # Good: Component
├── games/
│   ├── game_list.html
│   └── game_detail.html
```

**Bad Examples:**
```
TeamList.html           # Use snake_case
team.html               # Not descriptive
teams_listing.html      # Use team_list.html
ranking-row.html        # Component should start with _
```

### Template Block Names

**Pattern:** `{section}_{purpose}`

**Examples:**
```django
{% block page_title %}Team Rankings{% endblock %}
{% block main_content %}...{% endblock %}
{% block extra_css %}...{% endblock %}
{% block extra_js %}...{% endblock %}
{% block sidebar_content %}...{% endblock %}
```

---

## 5. URLs

### URL Names

**Pattern:** `{model}_{action}` or `{action}_{model}`

**Examples:**
```python
# Good
path("teams/", team_list, name="team_list"),
path("teams/<slug:slug>/", team_detail, name="team_detail"),
path("teams/create/", team_create, name="team_create"),
path("rankings/", global_leaderboard_view, name="global_rankings"),
path("rankings/<slug:game_slug>/", game_leaderboard_view, name="game_rankings"),

# Bad
path("teams/", team_list, name="list"),  # Not specific enough
path("teams/<slug:slug>/", team_detail, name="detail"),  # Ambiguous
path("create-team/", team_create, name="create-team"),  # Use underscores
```

### URL Patterns

**Good URL Structure:**
```
/teams/                          # List
/teams/create/                   # Create
/teams/<slug>/                   # Detail
/teams/<slug>/edit/              # Edit
/teams/<slug>/delete/            # Delete
/teams/<slug>/members/           # Related list
/teams/rankings/                 # Global rankings
/teams/rankings/<game_slug>/     # Per-game rankings
```

---

## 6. Variables

### General Rules

- **snake_case** for all variables
- **UPPER_CASE** for constants
- **Descriptive names** over abbreviations

**Examples:**
```python
# Good
team_members = Team.objects.filter(...)
active_count = memberships.filter(status='ACTIVE').count()
user_team_memberships = TeamMembership.objects.filter(user=user)

# Bad
tm = Team.objects.filter(...)  # Too abbreviated
ActiveCount = memberships.count()  # Use snake_case
user_tm_memb = TeamMembership.objects.filter(...)  # Too abbreviated
```

### Constants

**Pattern:** `{CATEGORY}_{NAME}`

**Examples:**
```python
# Good (in constants.py)
MAX_ROSTER_SIZE = 8
INVITE_EXPIRY_DAYS = 7
DIVISION_THRESHOLDS = {...}

class RankingConstants:
    DEFAULT_ELO = 1500
    K_FACTOR = 32
    BRONZE_THRESHOLD = 0
    SILVER_THRESHOLD = 1200

# Bad
maxRosterSize = 8  # Use UPPER_CASE for constants
max_roster = 8  # Not descriptive enough
ROSTER_SIZE = 8  # Add MAX_ prefix for clarity
```

---

## 7. Django-Specific

### Managers and QuerySets

**Pattern:** `{Model}Manager`, `{Model}QuerySet`

**Examples:**
```python
class TeamQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)
    
    def for_game(self, game):
        return self.filter(game=game)

class TeamManager(models.Manager):
    def get_queryset(self):
        return TeamQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()

class Team(models.Model):
    objects = TeamManager()
```

### Signals

**Pattern:** `{action}_{model}` or `{model}_{event}`

**Examples:**
```python
# Good
@receiver(post_save, sender=Team)
def team_created_handler(sender, instance, created, **kwargs):

@receiver(pre_delete, sender=TeamMembership)
def membership_deleted_handler(sender, instance, **kwargs):

# Bad
def handle_team(sender, instance, **kwargs):  # Not descriptive
def onTeamSave(sender, instance, **kwargs):  # camelCase
```

---

## 8. Backward Compatibility

When refactoring to meet these standards, maintain backward compatibility:

**Deprecation Pattern:**
```python
def fetch_team_roster(team):
    """DEPRECATED: Use get_team_members() instead."""
    warnings.warn(
        "fetch_team_roster is deprecated, use get_team_members",
        DeprecationWarning,
        stacklevel=2
    )
    return get_team_members(team)

def get_team_members(team):
    """Get active team members."""
    return team.memberships.filter(status='ACTIVE')
```

**Alias Pattern (URLs):**
```python
urlpatterns = [
    path("teams/", team_list, name="team_list"),
    path("teams/", team_list, name="list"),  # Alias for backward compat
]
```

---

## 9. Module Organization

### File Naming

**Pattern:** `{purpose}.py` (singular noun)

**Examples:**
```
apps/teams/
├── models/
│   ├── base.py
│   ├── ranking.py         # Good: Singular
│   └── _legacy.py         # Good: Internal/deprecated prefix
├── services/
│   ├── team_service.py    # Good: Descriptive
│   └── ranking_service.py
├── views/
│   ├── public.py
│   ├── dashboard.py
│   ├── rankings.py        # Good: Multiple related views
│   └── create.py
```

---

## 10. Common Patterns to Avoid

### Avoid These:

❌ **Redundant prefixes:**
```python
# Bad
class TeamTeamMembership(models.Model):  # Team prefix is redundant
def get_team_team_members(team):  # Redundant 'team'
```

❌ **Ambiguous names:**
```python
# Bad
def fetch(id):  # Fetch what?
def data():  # What data?
class Manager:  # Too generic (use TeamManager, GameManager, etc.)
```

❌ **Inconsistent verb tenses:**
```python
# Bad - mixing present/past tense
def created_team(data):  # Use 'create_team'
def updating_roster(team):  # Use 'update_roster'
```

❌ **Mixed conventions:**
```python
# Bad - mixing styles in same module
def team_list_view(request):  # Function-based
class CreateTeam(CreateView):  # Class-based should be TeamCreateView
```

---

## 11. Exceptions

Some legacy code may not follow these conventions. When working with legacy code:

1. **Add deprecation warnings** for widely-used functions
2. **Create new properly-named functions** that delegate to/from legacy
3. **Document migration path** in code comments
4. **Update call sites gradually** over multiple PRs

**Example:**
```python
# Legacy function (kept for backward compatibility)
def captain_check(user, team):
    """DEPRECATED: Use is_captain() instead."""
    warnings.warn("Use is_captain()", DeprecationWarning, stacklevel=2)
    return is_captain(user, team)

# New properly-named function
def is_captain(user, team):
    """Check if user is captain of team."""
    return team.get_captain() == user
```

---

## Summary Checklist

When writing new code, ensure:

- [ ] Views follow `{model}_{action}_view` or `{Model}{Action}View` pattern
- [ ] Services use `{Model}Service` with static/class methods
- [ ] Models are singular PascalCase with descriptive method names
- [ ] Boolean fields/methods use `is_` or `has_` prefix
- [ ] Templates use snake_case with `_component.html` for partials
- [ ] URLs use descriptive names like `team_detail` not just `detail`
- [ ] Variables are snake_case and descriptive
- [ ] Constants are UPPER_CASE
- [ ] Deprecation warnings added for renamed functions
- [ ] Code is consistent with existing patterns in the module

---

**References:**
- [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Django Coding Style](https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/)
- [Django REST Framework Style Guide](https://www.django-rest-framework.org/community/3.0-announcement/)

---

**Maintained by:** Development Team  
**Questions?** See team lead or open a discussion in `#dev-standards` channel
