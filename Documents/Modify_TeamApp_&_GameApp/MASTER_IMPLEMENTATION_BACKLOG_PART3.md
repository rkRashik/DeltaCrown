# 🎯 DELTACROWN MASTER IMPLEMENTATION BACKLOG - PART 3
**Continuation of MASTER_IMPLEMENTATION_BACKLOG_PART2.md**

---

## 🔴 PHASE 3: GAME ARCHITECTURE CENTRALIZATION (Weeks 15-24)

**Goal:** Create centralized Game app and eliminate ALL hardcoded game logic

**Success Criteria:**
- Single Game app as source of truth
- Zero hardcoded game slugs in codebase
- Admin can add new games without code deployment
- All apps (Teams, Tournaments) use Game API

---

### 🎯 SPRINT 8-9: Game App Foundation (Week 15-18)

#### **TASK 8.1: Create Game App Structure**
**Priority:** 🔴 CRITICAL  
**Effort:** 8 hours  
**Source:** TOURNAMENT_GAME_DEPENDENCIES_AUDIT.md + TEAM_FOCUSED_AUDIT_REPORT.md

**What to Do:**

**1. Create App Structure:**
```bash
# Create new app
python manage.py startapp games apps/games

# Create directory structure
mkdir -p apps/games/{models,services,api,admin,migrations,tests,utils}
```

**2. Create Module Files:**
```
apps/games/
├── __init__.py
├── apps.py
├── models/
│   ├── __init__.py
│   ├── game.py                  # Core Game model
│   ├── roster_config.py         # Team roster specs
│   ├── tournament_config.py     # Tournament rules
│   ├── player_identity.py       # Player ID validation
│   ├── role.py                  # Game-specific roles (Duelist, IGL, etc.)
│   └── version.py               # Track spec changes
├── services/
│   ├── __init__.py
│   ├── game_service.py          # Business logic
│   └── validation_service.py   # Spec validation
├── api/
│   ├── __init__.py
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── admin/
│   ├── __init__.py
│   ├── game_admin.py
│   └── config_admin.py
├── utils/
│   ├── __init__.py
│   └── validators.py            # Game ID validators
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_services.py
    └── test_api.py
```

**3. Register App:**
```python
# settings.py
INSTALLED_APPS = [
    # ... existing apps ...
    'apps.games',  # ADD THIS
    'apps.teams',
    'apps.tournaments',
]
```

**Testing:**
- App created successfully ✓
- Django recognizes app ✓
- Can run migrations ✓

**Expected Outcome:**
- Clean app structure
- Ready for model development

---

#### **TASK 8.2: Design and Create Game Models**
**Priority:** 🔴 CRITICAL  
**Effort:** 16 hours  
**Source:** TEAM_FOCUSED_AUDIT_REPORT.md - Game Specs Section

**What to Do:**

**1. Create Core Game Model:**

```python
# apps/games/models/game.py

from django.db import models
from django.core.validators import RegexValidator
from apps.common.models import TimestampedModel

class Game(TimestampedModel):
    """
    Canonical game definition.
    THE SINGLE SOURCE OF TRUTH for all game configuration.
    """
    
    # === BASIC INFO ===
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, db_index=True)
    short_code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short identifier (e.g., 'VAL', 'CS2', 'PUBG')"
    )
    
    # === CLASSIFICATION ===
    CATEGORY_CHOICES = [
        ('FPS', 'First-Person Shooter'),
        ('MOBA', 'Multiplayer Online Battle Arena'),
        ('BR', 'Battle Royale'),
        ('SPORTS', 'Sports/Esports Simulation'),
        ('FIGHTING', 'Fighting Game'),
        ('STRATEGY', 'Strategy'),
        ('CCG', 'Card Game'),
        ('OTHER', 'Other'),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    
    TYPE_CHOICES = [
        ('TEAM_VS_TEAM', 'Team vs Team'),
        ('1V1', '1 vs 1'),
        ('BATTLE_ROYALE', 'Battle Royale'),
        ('FREE_FOR_ALL', 'Free-for-All'),
    ]
    game_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    
    platforms = models.JSONField(
        default=list,
        help_text="List of platforms: ['PC', 'Mobile', 'Console']"
    )
    
    # === MEDIA ===
    icon = models.ImageField(upload_to='games/icons/', null=True, blank=True)
    logo = models.ImageField(upload_to='games/logos/', null=True, blank=True)
    banner = models.ImageField(upload_to='games/banners/', null=True, blank=True)
    card_image = models.ImageField(upload_to='games/cards/', null=True, blank=True)
    
    # === BRANDING ===
    primary_color = models.CharField(
        max_length=7,
        default='#7c3aed',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$')]
    )
    secondary_color = models.CharField(
        max_length=7,
        default='#1e1b4b',
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$')]
    )
    accent_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$')]
    )
    
    # === STATUS ===
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    release_date = models.DateField(null=True, blank=True)
    
    # === METADATA ===
    description = models.TextField(blank=True)
    official_website = models.URLField(blank=True)
    developer = models.CharField(max_length=100, blank=True)
    publisher = models.CharField(max_length=100, blank=True)
    
    # === SYSTEM ===
    created_by = models.ForeignKey(
        'user_profile.UserProfile',
        null=True,
        on_delete=models.SET_NULL,
        related_name='created_games'
    )
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return self.display_name
    
    def get_roster_config(self):
        """Get roster configuration for this game."""
        return getattr(self, 'roster_config', None)
    
    def get_tournament_config(self):
        """Get tournament configuration for this game."""
        return getattr(self, 'tournament_config', None)
    
    def get_player_identity_config(self):
        """Get player identity configuration."""
        return getattr(self, 'player_identity', None)
```

**2. Create Roster Configuration Model:**

```python
# apps/games/models/roster_config.py

class GameRosterConfig(TimestampedModel):
    """
    Team roster specifications for a game.
    Defines how teams are structured.
    """
    game = models.OneToOneField(
        Game,
        on_delete=models.CASCADE,
        related_name='roster_config'
    )
    
    # === TEAM SIZE (players on field) ===
    min_team_size = models.IntegerField(
        default=1,
        help_text="Minimum players on field during match"
    )
    max_team_size = models.IntegerField(
        default=5,
        help_text="Maximum players on field during match"
    )
    
    # === SUBSTITUTES ===
    min_substitutes = models.IntegerField(default=0)
    max_substitutes = models.IntegerField(default=2)
    
    # === TOTAL ROSTER ===
    min_roster_size = models.IntegerField(
        default=1,
        help_text="Minimum total roster size (including subs)"
    )
    max_roster_size = models.IntegerField(
        default=10,
        help_text="Maximum total roster size (including subs)"
    )
    
    # === STAFF ===
    allow_coaches = models.BooleanField(default=True)
    max_coaches = models.IntegerField(default=2)
    
    allow_analysts = models.BooleanField(default=True)
    max_analysts = models.IntegerField(default=1)
    
    allow_managers = models.BooleanField(default=True)
    max_managers = models.IntegerField(default=2)
    
    # === ROLE SYSTEM ===
    has_roles = models.BooleanField(
        default=False,
        help_text="Does this game have defined roles (e.g., Duelist, Support)?"
    )
    require_unique_roles = models.BooleanField(
        default=False,
        help_text="Each role can only be filled by one player"
    )
    allow_multi_role = models.BooleanField(
        default=True,
        help_text="Can players have multiple roles?"
    )
    
    # === REGIONS ===
    has_regions = models.BooleanField(default=False)
    available_regions = models.JSONField(
        default=list,
        help_text="[{'code': 'NA', 'name': 'North America'}, ...]"
    )
    
    class Meta:
        db_table = 'games_roster_config'
        verbose_name = 'Roster Configuration'
    
    def __str__(self):
        return f"{self.game.name} - Roster Config"
    
    def get_team_size_display(self):
        """Get human-readable team size (e.g., '5v5')."""
        if self.min_team_size == self.max_team_size:
            return f"{self.max_team_size}v{self.max_team_size}"
        return f"{self.min_team_size}-{self.max_team_size}"
    
    def get_roster_size_display(self):
        """Get human-readable roster size (e.g., '5-10')."""
        if self.min_roster_size == self.max_roster_size:
            return str(self.max_roster_size)
        return f"{self.min_roster_size}-{self.max_roster_size}"
```

**3. Create Game Role Model:**

```python
# apps/games/models/role.py

class GameRole(TimestampedModel):
    """
    Defined roles for a game.
    Examples: Duelist, Controller (Valorant), AWPer, IGL (CS2)
    """
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='roles'
    )
    
    name = models.CharField(max_length=50)
    short_name = models.CharField(max_length=20, blank=True)
    slug = models.SlugField()
    
    description = models.TextField(blank=True)
    
    # === DISPLAY ===
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="Icon class or emoji"
    )
    color = models.CharField(
        max_length=7,
        blank=True,
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$')]
    )
    
    # === RULES ===
    is_required = models.BooleanField(
        default=False,
        help_text="Must team have at least one player in this role?"
    )
    max_per_team = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum players per team with this role (null = no limit)"
    )
    
    # === ORDERING ===
    display_order = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('game', 'slug')
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.game.short_code} - {self.name}"
```

**4. Create Player Identity Config:**

```python
# apps/games/models/player_identity.py

class GamePlayerIdentityConfig(TimestampedModel):
    """
    How players are identified in this game.
    Maps to UserProfile fields and validates IDs.
    """
    game = models.OneToOneField(
        Game,
        on_delete=models.CASCADE,
        related_name='player_identity'
    )
    
    # === PLAYER ID FIELD ===
    profile_field_name = models.CharField(
        max_length=50,
        default='game_id',
        help_text="UserProfile field name (e.g., 'riot_id', 'steam_id', 'mlbb_uid')"
    )
    
    # === DISPLAY LABELS ===
    player_id_label = models.CharField(
        max_length=50,
        default='Player ID',
        help_text="Label shown to users (e.g., 'Riot ID', 'Steam ID')"
    )
    
    player_id_format = models.CharField(
        max_length=100,
        blank=True,
        help_text="Format description (e.g., 'Username#TAG', '76561198XXXXXXXXX')"
    )
    
    player_id_placeholder = models.CharField(
        max_length=100,
        blank=True,
        help_text="Placeholder text (e.g., 'Player#1234')"
    )
    
    # === VALIDATION ===
    id_regex_pattern = models.CharField(
        max_length=200,
        blank=True,
        help_text="Regex pattern for validation"
    )
    id_min_length = models.IntegerField(null=True, blank=True)
    id_max_length = models.IntegerField(null=True, blank=True)
    
    validation_function = models.CharField(
        max_length=100,
        blank=True,
        help_text="Python function path (e.g., 'apps.games.utils.validators.validate_riot_id')"
    )
    
    # === EXTERNAL API ===
    has_official_api = models.BooleanField(default=False)
    api_endpoint_base = models.URLField(blank=True)
    api_requires_key = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'games_player_identity_config'
        verbose_name = 'Player Identity Configuration'
    
    def __str__(self):
        return f"{self.game.name} - Player ID Config"
    
    def validate_player_id(self, player_id):
        """Validate player ID using configured rules."""
        if not player_id:
            raise ValidationError("Player ID is required")
        
        # Length validation
        if self.id_min_length and len(player_id) < self.id_min_length:
            raise ValidationError(f"Minimum {self.id_min_length} characters")
        
        if self.id_max_length and len(player_id) > self.id_max_length:
            raise ValidationError(f"Maximum {self.id_max_length} characters")
        
        # Regex validation
        if self.id_regex_pattern:
            import re
            if not re.match(self.id_regex_pattern, player_id):
                raise ValidationError(f"Invalid format. Expected: {self.player_id_format}")
        
        # Custom validation function
        if self.validation_function:
            module_path, func_name = self.validation_function.rsplit('.', 1)
            import importlib
            module = importlib.import_module(module_path)
            validator = getattr(module, func_name)
            validator(player_id)
        
        return True
```

**5. Create Tournament Config Model:**

```python
# apps/games/models/tournament_config.py

class GameTournamentConfig(TimestampedModel):
    """
    Tournament-specific rules for a game.
    """
    game = models.OneToOneField(
        Game,
        on_delete=models.CASCADE,
        related_name='tournament_config'
    )
    
    # === MATCH STRUCTURE ===
    MATCH_TYPE_CHOICES = [
        ('best_of', 'Best of X'),
        ('map_score', 'Map Score (e.g., 2-1)'),
        ('point_based', 'Point-Based'),
        ('battle_royale', 'Battle Royale Placement'),
    ]
    match_type = models.CharField(
        max_length=20,
        choices=MATCH_TYPE_CHOICES,
        default='best_of'
    )
    
    default_match_format = models.CharField(
        max_length=20,
        default='bo3',
        help_text="'bo1', 'bo3', 'bo5', etc."
    )
    
    # === BRACKET TYPES ===
    supported_bracket_types = models.JSONField(
        default=list,
        help_text="['single_elimination', 'double_elimination', 'round_robin', 'swiss']"
    )
    
    # === MATCH SETTINGS ===
    default_map_count = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of maps per match"
    )
    
    available_maps = models.JSONField(
        default=list,
        help_text="List of map names"
    )
    
    # === TIME SETTINGS ===
    default_match_duration_minutes = models.IntegerField(
        null=True,
        blank=True
    )
    allow_overtime = models.BooleanField(default=True)
    
    # === SCORING ===
    win_points = models.IntegerField(default=3)
    draw_points = models.IntegerField(default=1)
    loss_points = models.IntegerField(default=0)
    
    # Tiebreaker logic (JSONB for flexibility)
    tiebreaker_rules = models.JSONField(
        default=dict,
        help_text="""
        {
            'primary': 'head_to_head',
            'secondary': 'round_difference',
            'tertiary': 'total_rounds_won'
        }
        """
    )
    
    # === CHECK-IN ===
    requires_checkin = models.BooleanField(default=True)
    checkin_window_minutes = models.IntegerField(default=30)
    
    # === RESULT SUBMISSION ===
    result_type = models.CharField(
        max_length=20,
        default='score',
        help_text="'score', 'placement', 'points'"
    )
    
    result_fields = models.JSONField(
        default=dict,
        help_text="""
        Fields required for result submission:
        {'score': True, 'screenshot': False, 'stats': ['kills', 'deaths']}
        """
    )
    
    class Meta:
        db_table = 'games_tournament_config'
        verbose_name = 'Tournament Configuration'
    
    def __str__(self):
        return f"{self.game.name} - Tournament Config"
```

**6. Create Version Tracking Model:**

```python
# apps/games/models/version.py

class GameSpecVersion(TimestampedModel):
    """
    Track changes to game specifications over time.
    Allows reverting if needed.
    """
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='spec_versions'
    )
    
    version_number = models.CharField(max_length=20)
    change_summary = models.TextField()
    
    changed_fields = models.JSONField(
        default=dict,
        help_text="{'min_team_size': {'old': 5, 'new': 6}, ...}"
    )
    
    # Full snapshot for rollback
    full_config_snapshot = models.JSONField(
        help_text="Complete copy of all specs at this version"
    )
    
    # Metadata
    changed_by = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.SET_NULL,
        null=True
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('game', 'version_number')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.game.name} v{self.version_number}"
```

**7. Create Initial Migration:**
```bash
python manage.py makemigrations games
python manage.py migrate games
```

**Testing:**
- All models created successfully ✓
- Relationships work correctly ✓
- Can create Game instance ✓
- Configs link to Game ✓

**Expected Outcome:**
- Complete game data model
- Flexible configuration system
- Audit trail capability
- Ready for data migration

---

#### **TASK 8.3: Migrate Existing Game Data**
**Priority:** 🔴 CRITICAL  
**Effort:** 12 hours  
**Source:** TOURNAMENT_GAME_DEPENDENCIES_AUDIT.md

**Problem:**
- Game model exists in `apps/tournaments/models/`
- Need to move to `apps/games/`
- Preserve all existing data
- Update foreign keys

**What to Do:**

**1. Backup Current Data:**
```bash
# Backup existing games
python manage.py dumpdata tournaments.Game > backup_games.json

# Backup tournaments (FK references)
python manage.py dumpdata tournaments.Tournament > backup_tournaments.json

# Backup teams (if has game FK)
python manage.py dumpdata teams.Team > backup_teams.json
```

**2. Create Data Migration:**

```python
# apps/games/migrations/0002_migrate_existing_games.py

from django.db import migrations

def migrate_games_from_tournaments(apps, schema_editor):
    """Copy Game data from tournaments app to games app."""
    
    OldGame = apps.get_model('tournaments', 'Game')
    NewGame = apps.get_model('games', 'Game')
    RosterConfig = apps.get_model('games', 'GameRosterConfig')
    TournamentConfig = apps.get_model('games', 'GameTournamentConfig')
    PlayerIdentity = apps.get_model('games', 'GamePlayerIdentityConfig')
    
    for old_game in OldGame.objects.all():
        # Create new Game with same ID
        new_game = NewGame.objects.create(
            id=old_game.id,  # Keep same ID!
            name=old_game.name,
            display_name=old_game.display_name or old_game.name,
            slug=old_game.slug,
            short_code=old_game.short_code or old_game.slug.upper()[:10],
            category=old_game.category or 'OTHER',
            game_type=old_game.game_type or 'TEAM_VS_TEAM',
            platforms=old_game.platforms or [],
            icon=old_game.icon,
            logo=old_game.logo,
            banner=old_game.banner,
            primary_color=old_game.primary_color or '#7c3aed',
            secondary_color=old_game.secondary_color or '#1e1b4b',
            is_active=old_game.is_active,
            description=old_game.description or '',
            # ... map other fields
        )
        
        # Create RosterConfig from old game_config JSONB
        if old_game.roster_rules:
            RosterConfig.objects.create(
                game=new_game,
                min_team_size=old_game.roster_rules.get('min_team_size', 1),
                max_team_size=old_game.roster_rules.get('max_team_size', 5),
                min_roster_size=old_game.roster_rules.get('min_roster', 1),
                max_roster_size=old_game.roster_rules.get('max_roster', 10),
                has_roles=old_game.roster_rules.get('has_roles', False),
                # ... extract other config
            )
        
        # Create TournamentConfig from result_logic JSONB
        if old_game.result_logic:
            TournamentConfig.objects.create(
                game=new_game,
                match_type=old_game.result_logic.get('type', 'best_of'),
                tiebreaker_rules=old_game.result_logic.get('tiebreakers', {}),
                # ... extract other config
            )
        
        # Create PlayerIdentityConfig from profile_id_field
        if old_game.profile_id_field:
            PlayerIdentity.objects.create(
                game=new_game,
                profile_field_name=old_game.profile_id_field,
                player_id_label=f"{old_game.name} ID",
                # ... set defaults
            )

def reverse_migration(apps, schema_editor):
    """Rollback: Copy data back to tournaments.Game."""
    # Implement reverse if needed
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('games', '0001_initial'),
        ('tournaments', 'latest_migration'),
    ]
    
    operations = [
        migrations.RunPython(
            migrate_games_from_tournaments,
            reverse_migration
        ),
    ]
```

**3. Update Foreign Key References:**

**Step 1: Add new FK field (nullable) to Tournament:**
```python
# apps/tournaments/migrations/0XXX_add_new_game_fk.py

class Migration(migrations.Migration):
    dependencies = [
        ('tournaments', 'previous_migration'),
        ('games', '0002_migrate_existing_games'),
    ]
    
    operations = [
        # Add new FK field (nullable first)
        migrations.AddField(
            model_name='tournament',
            name='game_new',
            field=models.ForeignKey(
                'games.Game',
                null=True,  # Nullable during migration
                on_delete=models.PROTECT,
                related_name='tournaments_new'
            ),
        ),
    ]
```

**Step 2: Copy FK values:**
```python
# apps/tournaments/migrations/0XXX_copy_game_fk.py

def copy_game_references(apps, schema_editor):
    Tournament = apps.get_model('tournaments', 'Tournament')
    
    for tournament in Tournament.objects.all():
        if tournament.game_id:
            # New Game has same ID as old Game
            tournament.game_new_id = tournament.game_id
            tournament.save()

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(copy_game_references),
    ]
```

**Step 3: Make new FK required, remove old FK:**
```python
# apps/tournaments/migrations/0XXX_finalize_game_fk.py

class Migration(migrations.Migration):
    operations = [
        # Rename: game_new → game
        migrations.RenameField(
            model_name='tournament',
            old_name='game',
            new_name='game_old',
        ),
        migrations.RenameField(
            model_name='tournament',
            old_name='game_new',
            new_name='game',
        ),
        # Make required
        migrations.AlterField(
            model_name='tournament',
            name='game',
            field=models.ForeignKey(
                'games.Game',
                on_delete=models.PROTECT,
                related_name='tournaments'
            ),
        ),
        # Delete old FK
        migrations.RemoveField(
            model_name='tournament',
            name='game_old',
        ),
    ]
```

**4. Repeat for Teams App (if applicable):**
- Same process for `Team.game` FK
- Update references to point to `games.Game`

**5. Verify Data Integrity:**
```python
# After migration, run checks
from apps.games.models import Game
from apps.tournaments.models import Tournament

# Check count matches
old_count = Tournament.objects.filter(game_old__isnull=False).count()
new_count = Tournament.objects.filter(game__isnull=False).count()
assert old_count == new_count, "FK migration failed!"

# Check specific tournament
tournament = Tournament.objects.first()
assert tournament.game is not None, "Game FK is null!"
assert tournament.game.name, "Game has no name!"
```

**Testing:**
- All games copied successfully ✓
- Game count matches ✓
- Tournament.game FK points to games.Game ✓
- Team.game FK points to games.Game ✓
- No data loss ✓
- Can query tournaments by game ✓

**Expected Outcome:**
- All game data in new Game app
- FKs updated successfully
- Zero data loss
- Old Game model can be safely deleted

---

### 🎯 SPRINT 10-11: Eliminate Hardcoded Logic (Week 19-22)

#### **TASK 9.1: Refactor Bracket Service Game Logic**
**Priority:** 🔴 CRITICAL  
**Effort:** 14 hours  
**Source:** TOURNAMENT_GAME_DEPENDENCIES_AUDIT.md - bracket_service.py

**Problem:**
```python
# apps/tournaments/services/bracket_service.py lines 263-300
# Hardcoded game-specific sorting logic

if game_slug in ['efootball', 'fc-mobile', 'fifa']:
    # Sort by goal_difference
    teams.sort(key=lambda t: t.stats.get('goal_difference', 0))
elif game_slug in ['valorant', 'cs2']:
    # Sort by round_difference
    teams.sort(key=lambda t: t.stats.get('round_difference', 0))
elif game_slug == 'pubg':
    # Sort by placement_points
    teams.sort(key=lambda t: t.stats.get('placement_points', 0))
```

**What to Do:**

**1. Move Logic to GameTournamentConfig:**

```python
# apps/games/models/tournament_config.py

class GameTournamentConfig(models.Model):
    # ... existing fields ...
    
    # ADD THIS:
    tiebreaker_rules = models.JSONField(
        default=dict,
        help_text="""
        Defines tiebreaker logic for standings.
        Example:
        {
            'fields': ['round_difference', 'total_rounds_won', 'head_to_head'],
            'stat_field_primary': 'round_difference',
            'stat_field_secondary': 'kills',
            'sort_order': 'desc'  # or 'asc'
        }
        """
    )
```

**2. Seed Tiebreaker Data for Existing Games:**

```python
# Data migration or management command
from apps.games.models import Game, GameTournamentConfig

# Valorant/CS2 - Round difference
for game_slug in ['valorant', 'cs2']:
    game = Game.objects.get(slug=game_slug)
    config, _ = GameTournamentConfig.objects.get_or_create(game=game)
    config.tiebreaker_rules = {
        'fields': ['round_difference', 'total_rounds_won', 'head_to_head'],
        'stat_field_primary': 'round_difference',
        'stat_field_secondary': 'kills',
        'sort_order': 'desc'
    }
    config.save()

# FIFA/eFootball - Goal difference
for game_slug in ['efootball', 'fc-mobile', 'fifa']:
    game = Game.objects.get(slug=game_slug)
    config, _ = GameTournamentConfig.objects.get_or_create(game=game)
    config.tiebreaker_rules = {
        'fields': ['goal_difference', 'goals_scored', 'head_to_head'],
        'stat_field_primary': 'goal_difference',
        'stat_field_secondary': 'goals_scored',
        'sort_order': 'desc'
    }
    config.save()

# PUBG - Placement points
game = Game.objects.get(slug='pubg')
config, _ = GameTournamentConfig.objects.get_or_create(game=game)
config.tiebreaker_rules = {
    'fields': ['placement_points', 'total_kills', 'average_survival_time'],
    'stat_field_primary': 'placement_points',
    'stat_field_secondary': 'total_kills',
    'sort_order': 'desc'
}
config.save()
```

**3. Refactor Bracket Service:**

Before:
```python
def sort_teams_by_tiebreaker(self, teams, game_slug):
    if game_slug in ['efootball', 'fc-mobile', 'fifa']:
        teams.sort(key=lambda t: t.stats.get('goal_difference', 0))
    elif game_slug in ['valorant', 'cs2']:
        teams.sort(key=lambda t: t.stats.get('round_difference', 0))
    # ... etc
```

After:
```python
def sort_teams_by_tiebreaker(self, teams, game):
    """Sort teams using game's configured tiebreaker rules."""
    config = game.get_tournament_config()
    
    if not config or not config.tiebreaker_rules:
        # Fallback to points
        teams.sort(key=lambda t: t.points, reverse=True)
        return teams
    
    rules = config.tiebreaker_rules
    primary_field = rules.get('stat_field_primary', 'points')
    secondary_field = rules.get('stat_field_secondary', 'wins')
    sort_order = rules.get('sort_order', 'desc')
    
    # Multi-level sort
    teams.sort(
        key=lambda t: (
            t.stats.get(primary_field, 0),
            t.stats.get(secondary_field, 0),
            t.points
        ),
        reverse=(sort_order == 'desc')
    )
    
    return teams
```

**4. Update All Callers:**
```bash
# Find all uses of sort_teams_by_tiebreaker
grep -r "sort_teams_by_tiebreaker" apps/tournaments/

# Update to pass Game object instead of game_slug
# Before: sort_teams_by_tiebreaker(teams, 'valorant')
# After: sort_teams_by_tiebreaker(teams, game_object)
```

**Testing:**
- Valorant teams sort by round_difference ✓
- FIFA teams sort by goal_difference ✓
- PUBG teams sort by placement_points ✓
- Can change tiebreaker via admin ✓
- No hardcoded game slugs ✓

**Expected Outcome:**
- Flexible tiebreaker system
- No hardcoded game logic
- Admin-configurable
- -100 lines of hardcoded logic

---

#### **TASK 9.2: Refactor Registration Wizard**
**Priority:** 🔴 CRITICAL  
**Effort:** 10 hours  
**Source:** TOURNAMENT_GAME_DEPENDENCIES_AUDIT.md - registration_wizard.py

**Problem:**
```python
# apps/tournaments/views/registration_wizard.py lines 465-478
# Hardcoded profile field mapping

if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id
elif game_slug == 'cs2':
    auto_filled['game_id'] = profile.steam_id
elif game_slug == 'mlbb':
    auto_filled['game_id'] = f"{profile.mlbb_uid}({profile.mlbb_zone})"
```

**But Game model ALREADY has `profile_id_field`!**

**What to Do:**

**1. Use Game.player_identity.profile_field_name:**

Before:
```python
def auto_fill_player_data(self, player, game_slug):
    auto_filled = {}
    
    if game_slug == 'valorant':
        auto_filled['game_id'] = player.profile.riot_id
    elif game_slug == 'cs2':
        auto_filled['game_id'] = player.profile.steam_id
    # ... 10+ more hardcoded checks
    
    return auto_filled
```

After:
```python
def auto_fill_player_data(self, player, game):
    """Auto-fill player data using game's configured profile field."""
    auto_filled = {}
    
    # Get player identity config
    identity_config = game.get_player_identity_config()
    if not identity_config:
        return auto_filled
    
    # Get value from UserProfile using configured field name
    field_name = identity_config.profile_field_name
    game_id = getattr(player.profile, field_name, None)
    
    if game_id:
        auto_filled['game_id'] = game_id
        auto_filled['game_id_label'] = identity_config.player_id_label
    
    return auto_filled
```

**2. Handle Special Cases (MLBB format):**

```python
# If game needs custom formatting, store in PlayerIdentityConfig

# For MLBB:
identity_config.format_function = 'apps.games.utils.formatters.format_mlbb_id'

# apps/games/utils/formatters.py
def format_mlbb_id(profile):
    """Format MLBB ID as 'UID(Zone)'."""
    return f"{profile.mlbb_uid}({profile.mlbb_zone})"

# In auto_fill_player_data:
if identity_config.format_function:
    module_path, func_name = identity_config.format_function.rsplit('.', 1)
    import importlib
    module = importlib.import_module(module_path)
    formatter = getattr(module, func_name)
    game_id = formatter(player.profile)
```

**3. Update All Registration Views:**
```bash
# Find all registration views
grep -r "if game_slug ==" apps/tournaments/views/
grep -r "elif game_slug ==" apps/tournaments/views/

# Replace with game object lookups
```

**Testing:**
- Valorant auto-fills Riot ID ✓
- CS2 auto-fills Steam ID ✓
- MLBB auto-fills UID(Zone) ✓
- New game works without code changes ✓
- No hardcoded game slugs ✓

**Expected Outcome:**
- Dynamic profile field mapping
- No hardcoded game checks
- Easy to add new games
- -200 lines of hardcoded logic

---

#### **TASK 9.3: Unify Registration Functions**
**Priority:** 🟠 HIGH  
**Effort:** 16 hours  
**Source:** TOURNAMENT_GAME_DEPENDENCIES_AUDIT.md - registrations.py

**Problem:**
- Separate registration functions per game:
  - `register_efootball_player()`
  - `register_valorant_team()`
  - `register_cs2_team()`
  - `register_pubg_squad()`
- Same logic, different implementations

**What to Do:**

**1. Create Generic Registration Function:**

```python
# apps/tournaments/services/registration_service.py

class TournamentRegistrationService:
    """Unified tournament registration service."""
    
    def register_team(self, tournament, team, registration_data):
        """
        Generic team registration for any game.
        
        Args:
            tournament: Tournament instance
            team: Team instance
            registration_data: dict with registration info
        
        Returns:
            TournamentRegistration instance
        """
        game = tournament.game
        roster_config = game.get_roster_config()
        
        # Validate team size
        team_size = team.active_members.count()
        if team_size < roster_config.min_team_size:
            raise ValidationError(
                f"Team must have at least {roster_config.min_team_size} players"
            )
        if team_size > roster_config.max_roster_size:
            raise ValidationError(
                f"Team cannot exceed {roster_config.max_roster_size} players"
            )
        
        # Validate captain designation (if required)
        if tournament.requires_captain:
            captain = team.get_tournament_captain()
            if not captain:
                raise ValidationError("Team must designate a captain")
            registration_data['captain_id'] = captain.id
        
        # Validate player IDs (game-specific)
        self._validate_player_ids(team, game)
        
        # Create registration
        registration = TournamentRegistration.objects.create(
            tournament=tournament,
            team=team,
            status='PENDING',
            registration_data=registration_data
        )
        
        # Create roster snapshot
        self._create_roster_snapshot(registration, team)
        
        return registration
    
    def _validate_player_ids(self, team, game):
        """Validate all team members have valid game IDs."""
        identity_config = game.get_player_identity_config()
        if not identity_config:
            return
        
        field_name = identity_config.profile_field_name
        
        for member in team.active_members:
            player_id = getattr(member.user.profile, field_name, None)
            if not player_id:
                raise ValidationError(
                    f"{member.user.display_name} is missing {identity_config.player_id_label}"
                )
            
            # Validate format
            try:
                identity_config.validate_player_id(player_id)
            except ValidationError as e:
                raise ValidationError(
                    f"{member.user.display_name}: {str(e)}"
                )
    
    def _create_roster_snapshot(self, registration, team):
        """Save roster snapshot at registration time."""
        roster_data = []
        for member in team.active_members:
            roster_data.append({
                'user_id': member.user.id,
                'username': member.user.username,
                'role': member.role,
                'is_captain': member.is_captain,
            })
        
        registration.roster_snapshot = roster_data
        registration.save()
```

**2. Delete Game-Specific Functions:**
```python
# DELETE these:
# def register_efootball_player(tournament, team):
# def register_valorant_team(tournament, team):
# def register_cs2_team(tournament, team):
# def register_pubg_squad(tournament, team):

# REPLACE with:
registration_service = TournamentRegistrationService()
registration = registration_service.register_team(tournament, team, data)
```

**3. Update All Callers:**
```bash
# Find all registration function calls
grep -r "register_valorant_team\|register_cs2_team" apps/

# Update to use unified service
```

**Testing:**
- Valorant team registration works ✓
- CS2 team registration works ✓
- PUBG team registration works ✓
- Validation enforces game rules ✓
- Can add new game without code ✓

**Expected Outcome:**
- Single registration function
- Game rules from database
- -400 lines of duplicate code
- Easier maintenance

---

**END OF PHASE 3 PREVIEW**

**Remaining Phase 3 Tasks (Week 23-24):**
- TASK 9.4: Update All game_registry Imports (12 hours)
- TASK 9.5: Create Game Service Layer (10 hours)
- TASK 9.6: Build Game REST API (12 hours)
- TASK 9.7: Create Django Admin for Games (8 hours)
- TASK 9.8: Delete Deprecated Code (6 hours)

**Phase 3 Summary:**
- ✅ Centralized Game app created
- ✅ All game data migrated
- ✅ Hardcoded logic eliminated
- ✅ Admin can manage games without code
- ✅ Teams and Tournaments use Game API

**Ready for Phase 4: Missing Team Features** →

