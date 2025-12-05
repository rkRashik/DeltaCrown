# Complete Implementation Task List
**Project:** DeltaCrown Platform Optimization  
**Date:** December 4, 2025  
**Goal:** Fix all issues, eliminate technical debt, achieve industry-standard code quality

---

## 🎯 PROJECT OVERVIEW

### Objectives
1. **Create centralized Game app** - Single source of truth for all game data
2. **Eliminate hardcoded logic** - All game-specific code → configurable
3. **Fix role management confusion** - Clear OWNER system, esports roles
4. **Implement game-specific rankings** - Per-game leaderboards with tiers
5. **Add critical missing features** - Scrim scheduler, practice management
6. **Zero breaking changes** - Incremental, tested migrations
7. **Industry-standard code** - Clean, documented, future-proof

### Success Criteria
- ✅ Zero hardcoded game configurations
- ✅ All apps use centralized Game API
- ✅ Admin can add new games without code deployment
- ✅ Clear role hierarchy (no OWNER/CAPTAIN confusion)
- ✅ Game-specific rankings with rank tiers
- ✅ All tests passing (>90% coverage)
- ✅ Zero production bugs
- ✅ < 100ms API response times

### Timeline
**Total Duration:** 40 weeks (10 months)  
**Milestones:** 10 major milestones  
**Sprints:** 2-week sprints

---

## 📋 MASTER TASK LIST

### PHASE 1: FOUNDATION - GAME APP (Weeks 1-10)

---

#### **MILESTONE 1: Game App Setup (Week 1-2)**

**Goal:** Create foundation for centralized game management

##### Task 1.1: Create Game App Structure
**Priority:** 🔴 CRITICAL  
**Effort:** 4 hours  
**Dependencies:** None

**Steps:**
1. Create directory structure:
   ```bash
   mkdir -p apps/games/{models,services,api,admin,migrations,tests}
   touch apps/games/__init__.py
   touch apps/games/apps.py
   touch apps/games/models/__init__.py
   touch apps/games/services/__init__.py
   touch apps/games/api/__init__.py
   touch apps/games/admin.py
   touch apps/games/urls.py
   ```

2. Create `apps/games/apps.py`:
   ```python
   from django.apps import AppConfig
   
   class GamesConfig(AppConfig):
       default_auto_field = 'django.db.models.BigAutoField'
       name = 'apps.games'
       verbose_name = 'Game Management'
       
       def ready(self):
           # Import signals if any
           pass
   ```

3. Add to `INSTALLED_APPS` in `settings.py`:
   ```python
   INSTALLED_APPS = [
       # ...
       'apps.games',  # Add before apps.teams and apps.tournaments
       'apps.teams',
       'apps.tournaments',
       # ...
   ]
   ```

4. Create initial `__init__.py` files

**Deliverables:**
- ✅ `apps/games/` directory exists
- ✅ App registered in Django settings
- ✅ Can run `python manage.py check` without errors

**Testing:**
```bash
python manage.py check
python manage.py makemigrations games
# Should output "No changes detected"
```

---

##### Task 1.2: Design Game Model Schema
**Priority:** 🔴 CRITICAL  
**Effort:** 8 hours  
**Dependencies:** Task 1.1

**Steps:**

1. Create `apps/games/models/game.py`:
   ```python
   """
   Core Game model - Single source of truth for all game data.
   """
   from django.db import models
   from django.core.validators import RegexValidator
   from apps.common.models import TimestampedModel
   
   
   class Game(TimestampedModel):
       """
       Canonical game definition.
       
       This is THE SINGLE SOURCE OF TRUTH for all game configuration
       across the entire platform (teams, tournaments, etc.).
       """
       
       # ═══════════════════════════════════════════════════════════
       # IDENTITY FIELDS
       # ═══════════════════════════════════════════════════════════
       
       name = models.CharField(
           max_length=100,
           unique=True,
           help_text="Official game name (e.g., 'Valorant')"
       )
       
       display_name = models.CharField(
           max_length=150,
           help_text="Display name with branding (e.g., 'VALORANT')"
       )
       
       slug = models.SlugField(
           max_length=120,
           unique=True,
           db_index=True,
           help_text="URL-safe identifier (e.g., 'valorant')"
       )
       
       short_code = models.CharField(
           max_length=10,
           unique=True,
           validators=[RegexValidator(r'^[A-Z0-9]+$', 'Only uppercase letters and numbers')],
           help_text="Short code for UI (e.g., 'VAL', 'CS2')"
       )
       
       # ═══════════════════════════════════════════════════════════
       # CLASSIFICATION
       # ═══════════════════════════════════════════════════════════
       
       CATEGORY_CHOICES = [
           ('fps', 'First-Person Shooter'),
           ('moba', 'Multiplayer Online Battle Arena'),
           ('battle_royale', 'Battle Royale'),
           ('sports', 'Sports'),
           ('fighting', 'Fighting'),
           ('strategy', 'Real-Time Strategy'),
           ('card', 'Card Game'),
           ('racing', 'Racing'),
           ('other', 'Other'),
       ]
       
       category = models.CharField(
           max_length=50,
           choices=CATEGORY_CHOICES,
           help_text="Game genre category"
       )
       
       GAME_TYPE_CHOICES = [
           ('team_vs_team', 'Team vs Team'),
           ('1v1', '1v1'),
           ('battle_royale', 'Battle Royale'),
           ('free_for_all', 'Free-for-All'),
       ]
       
       game_type = models.CharField(
           max_length=50,
           choices=GAME_TYPE_CHOICES,
           default='team_vs_team',
           help_text="Match format type"
       )
       
       platforms = models.JSONField(
           default=list,
           help_text="Supported platforms: ['PC', 'Mobile', 'Console']"
       )
       
       # ═══════════════════════════════════════════════════════════
       # MEDIA & BRANDING
       # ═══════════════════════════════════════════════════════════
       
       icon = models.ImageField(
           upload_to='games/icons/',
           help_text="Small icon (32x32 or 64x64)"
       )
       
       logo = models.ImageField(
           upload_to='games/logos/',
           null=True,
           blank=True,
           help_text="Full logo image"
       )
       
       banner = models.ImageField(
           upload_to='games/banners/',
           null=True,
           blank=True,
           help_text="Banner image for hero sections"
       )
       
       card_image = models.ImageField(
           upload_to='games/cards/',
           null=True,
           blank=True,
           help_text="Card/thumbnail image (16:9 ratio recommended)"
       )
       
       primary_color = models.CharField(
           max_length=7,
           default='#7c3aed',
           validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Must be hex color')],
           help_text="Primary brand color (hex)"
       )
       
       secondary_color = models.CharField(
           max_length=7,
           default='#1e1b4b',
           validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Must be hex color')],
           help_text="Secondary brand color (hex)"
       )
       
       accent_color = models.CharField(
           max_length=7,
           null=True,
           blank=True,
           validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Must be hex color')],
           help_text="Accent color (optional)"
       )
       
       # ═══════════════════════════════════════════════════════════
       # STATUS & METADATA
       # ═══════════════════════════════════════════════════════════
       
       is_active = models.BooleanField(
           default=True,
           db_index=True,
           help_text="Is this game currently supported?"
       )
       
       is_featured = models.BooleanField(
           default=False,
           help_text="Feature prominently on homepage"
       )
       
       release_date = models.DateField(
           null=True,
           blank=True,
           help_text="Official game release date"
       )
       
       description = models.TextField(
           blank=True,
           help_text="Game description for public display"
       )
       
       official_website = models.URLField(
           blank=True,
           help_text="Official game website"
       )
       
       developer = models.CharField(
           max_length=100,
           blank=True,
           help_text="Game developer company"
       )
       
       publisher = models.CharField(
           max_length=100,
           blank=True,
           help_text="Game publisher company"
       )
       
       # ═══════════════════════════════════════════════════════════
       # AUDIT TRAIL
       # ═══════════════════════════════════════════════════════════
       
       created_by = models.ForeignKey(
           'auth.User',
           on_delete=models.SET_NULL,
           null=True,
           blank=True,
           related_name='games_created',
           help_text="User who added this game"
       )
       
       # created_at and updated_at inherited from TimestampedModel
       
       class Meta:
           db_table = 'games_game'
           verbose_name = 'Game'
           verbose_name_plural = 'Games'
           ordering = ['name']
           indexes = [
               models.Index(fields=['slug']),
               models.Index(fields=['is_active', 'is_featured']),
               models.Index(fields=['category']),
           ]
       
       def __str__(self):
           return self.display_name
       
       def get_roster_config(self):
           """Get roster configuration for this game."""
           return self.roster_config
       
       def get_tournament_config(self):
           """Get tournament configuration for this game."""
           return self.tournament_config
       
       def get_all_roles(self):
           """Get all defined roles for this game."""
           return self.roles.all().order_by('display_order')
   ```

2. Create `apps/games/models/roster_config.py`:
   ```python
   """
   Roster configuration model - Team structure rules per game.
   """
   from django.db import models
   from django.core.validators import MinValueValidator, MaxValueValidator
   
   
   class GameRosterConfig(models.Model):
       """
       Team roster specifications for a game.
       Defines min/max players, substitutes, coaches, etc.
       """
       
       game = models.OneToOneField(
           'games.Game',
           on_delete=models.CASCADE,
           related_name='roster_config',
           primary_key=True
       )
       
       # ═══════════════════════════════════════════════════════════
       # TEAM SIZE
       # ═══════════════════════════════════════════════════════════
       
       min_team_size = models.PositiveIntegerField(
           default=1,
           validators=[MinValueValidator(1)],
           help_text="Minimum active players on field/match"
       )
       
       max_team_size = models.PositiveIntegerField(
           default=5,
           validators=[MinValueValidator(1)],
           help_text="Maximum active players on field/match"
       )
       
       # ═══════════════════════════════════════════════════════════
       # SUBSTITUTES
       # ═══════════════════════════════════════════════════════════
       
       min_substitutes = models.PositiveIntegerField(
           default=0,
           help_text="Minimum substitute players required"
       )
       
       max_substitutes = models.PositiveIntegerField(
           default=2,
           help_text="Maximum substitute players allowed"
       )
       
       # ═══════════════════════════════════════════════════════════
       # TOTAL ROSTER
       # ═══════════════════════════════════════════════════════════
       
       min_roster_size = models.PositiveIntegerField(
           default=1,
           help_text="Minimum total roster size (players + subs)"
       )
       
       max_roster_size = models.PositiveIntegerField(
           default=10,
           validators=[MinValueValidator(1), MaxValueValidator(50)],
           help_text="Maximum total roster size"
       )
       
       # ═══════════════════════════════════════════════════════════
       # STAFF
       # ═══════════════════════════════════════════════════════════
       
       allow_coaches = models.BooleanField(
           default=True,
           help_text="Are coaches allowed for this game?"
       )
       
       max_coaches = models.PositiveIntegerField(
           default=2,
           validators=[MaxValueValidator(10)],
           help_text="Maximum number of coaches"
       )
       
       allow_analysts = models.BooleanField(
           default=True,
           help_text="Are analysts allowed?"
       )
       
       max_analysts = models.PositiveIntegerField(
           default=1,
           validators=[MaxValueValidator(5)],
           help_text="Maximum number of analysts"
       )
       
       # ═══════════════════════════════════════════════════════════
       # ROLE SYSTEM
       # ═══════════════════════════════════════════════════════════
       
       has_roles = models.BooleanField(
           default=False,
           help_text="Does this game have defined in-game roles?"
       )
       
       require_unique_roles = models.BooleanField(
           default=False,
           help_text="Must each role be assigned to different players?"
       )
       
       allow_multi_role = models.BooleanField(
           default=True,
           help_text="Can players have multiple roles?"
       )
       
       # ═══════════════════════════════════════════════════════════
       # REGIONS
       # ═══════════════════════════════════════════════════════════
       
       has_regions = models.BooleanField(
           default=False,
           help_text="Does this game have regional servers/leagues?"
       )
       
       available_regions = models.JSONField(
           default=list,
           help_text="List of region dicts: [{'code': 'NA', 'name': 'North America'}]"
       )
       
       class Meta:
           db_table = 'games_roster_config'
           verbose_name = 'Game Roster Configuration'
           verbose_name_plural = 'Game Roster Configurations'
       
       def __str__(self):
           return f"{self.game.name} Roster Config"
       
       def get_roster_size_display(self):
           """Human-readable roster size (e.g., '5-7')."""
           if self.min_roster_size == self.max_roster_size:
               return str(self.max_roster_size)
           return f"{self.min_roster_size}-{self.max_roster_size}"
       
       def get_team_size_display(self):
           """Team size display (e.g., '5v5')."""
           if self.min_team_size == self.max_team_size:
               return f"{self.max_team_size}v{self.max_team_size}"
           return f"{self.min_team_size}-{self.max_team_size}"
   ```

3. Create more models (GameRole, PlayerIdentityConfig, TournamentConfig, GameVersion)

**Deliverables:**
- ✅ Complete Game model with all fields
- ✅ GameRosterConfig model
- ✅ GameRole model
- ✅ PlayerIdentityConfig model
- ✅ TournamentConfig model
- ✅ GameVersion model (audit trail)

**Testing:**
```bash
python manage.py makemigrations games
python manage.py migrate games
python manage.py shell
>>> from apps.games.models import Game
>>> Game.objects.count()  # Should be 0
```

---

##### Task 1.3: Migrate Game Model from Tournament App
**Priority:** 🔴 CRITICAL  
**Effort:** 16 hours  
**Dependencies:** Task 1.2

**CRITICAL:** This task involves moving the Game model from `apps/tournaments` to `apps/games`.  
**Risk:** HIGH - Can break existing data if not done carefully.

**Steps:**

1. **Backup database:**
   ```bash
   python manage.py dumpdata tournaments.Game > backup_games.json
   python manage.py dumpdata tournaments.Tournament > backup_tournaments.json
   python manage.py dumpdata teams.Team > backup_teams.json
   ```

2. **Create data migration in games app:**
   ```python
   # apps/games/migrations/0002_copy_data_from_tournaments.py
   from django.db import migrations
   
   def copy_game_data(apps, schema_editor):
       """Copy data from tournaments.Game to games.Game"""
       OldGame = apps.get_model('tournaments', 'Game')
       NewGame = apps.get_model('games', 'Game')
       
       for old_game in OldGame.objects.all():
           NewGame.objects.create(
               id=old_game.id,  # Keep same ID!
               name=old_game.name,
               display_name=old_game.name,  # Default to same as name
               slug=old_game.slug,
               short_code=old_game.slug.upper()[:5],  # Generate short code
               category='other',  # Default, update manually later
               game_type='team_vs_team',
               platforms=old_game.game_config.get('platforms', ['PC']),
               icon=old_game.icon,
               logo=old_game.logo,
               banner=old_game.banner,
               card_image=old_game.card_image,
               primary_color=old_game.primary_color or '#7c3aed',
               secondary_color=old_game.secondary_color or '#1e1b4b',
               is_active=old_game.is_active,
               description=old_game.description,
               created_at=old_game.created_at,
           )
   
   class Migration(migrations.Migration):
       dependencies = [
           ('games', '0001_initial'),
           ('tournaments', 'xxxx_previous_migration'),
       ]
       
       operations = [
           migrations.RunPython(copy_game_data),
       ]
   ```

3. **Update FK references:**
   ```python
   # apps/tournaments/migrations/0xxx_update_game_fk.py
   from django.db import migrations, models
   import django.db.models.deletion
   
   class Migration(migrations.Migration):
       dependencies = [
           ('games', '0002_copy_data_from_tournaments'),
           ('tournaments', 'xxxx_previous_migration'),
       ]
       
       operations = [
           # Rename old FK field
           migrations.RenameField(
               model_name='tournament',
               old_name='game',
               new_name='game_old',
           ),
           # Add new FK to games.Game
           migrations.AddField(
               model_name='tournament',
               name='game',
               field=models.ForeignKey(
                   null=True,  # Temporarily nullable
                   on_delete=django.db.models.deletion.PROTECT,
                   to='games.game'
               ),
           ),
       ]
   ```

4. **Data migration to populate new FK:**
   ```python
   # apps/tournaments/migrations/0xxx_populate_new_game_fk.py
   def populate_game_fk(apps, schema_editor):
       Tournament = apps.get_model('tournaments', 'Tournament')
       for tournament in Tournament.objects.all():
           tournament.game_id = tournament.game_old_id
           tournament.save(update_fields=['game'])
   
   class Migration(migrations.Migration):
       dependencies = [
           ('tournaments', 'xxxx_update_game_fk'),
       ]
       
       operations = [
           migrations.RunPython(populate_game_fk),
       ]
   ```

5. **Remove old Game model:**
   ```python
   # apps/tournaments/migrations/0xxx_remove_old_game.py
   class Migration(migrations.Migration):
       dependencies = [
           ('tournaments', 'xxxx_populate_new_game_fk'),
       ]
       
       operations = [
           # Remove old FK field
           migrations.RemoveField(
               model_name='tournament',
               name='game_old',
           ),
           # Delete old Game model
           migrations.DeleteModel(
               name='Game',
           ),
       ]
   ```

6. **Update Teams app FK:**
   - Repeat similar process for `apps/teams/models/Team.game` FK

**Deliverables:**
- ✅ All Game data migrated to apps.games
- ✅ Tournament.game points to apps.games.Game
- ✅ Team.game points to apps.games.Game
- ✅ Old tournaments.Game model deleted
- ✅ All FK relationships intact
- ✅ Zero data loss

**Testing:**
```bash
# Run migrations
python manage.py migrate

# Verify data
python manage.py shell
>>> from apps.games.models import Game
>>> from apps.tournaments.models import Tournament
>>> from apps.teams.models import Team
>>> 
>>> Game.objects.count()  # Should match old count
>>> Tournament.objects.select_related('game').first().game
>>> Team.objects.select_related('game').first().game
```

---

[TASK LIST CONTINUES - This is getting very long. Should I continue with the full 40-week task list, or would you like me to:

1. Continue with all tasks in detail (will be 10,000+ lines)
2. Create a summary version with high-level tasks only
3. Create separate files for each phase?

Let me know how you'd like me to proceed!]
