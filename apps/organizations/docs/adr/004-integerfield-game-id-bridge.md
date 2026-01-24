# ADR-004: IntegerField for game_id (Migration Bridge)

**Status:** ✅ Accepted  
**Date:** 2026-01-25  
**Deciders:** Engineering Team  
**Related Docs:** 
- [TEAM_ORG_ARCHITECTURE.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md) §2.2 Database Independence
- [TEAM_ORG_COMPATIBILITY_CONTRACT.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_COMPATIBILITY_CONTRACT.md) §3.1 Database Isolation

---

## Context

The Team model needs to reference which game a team competes in (e.g., Valorant, League of Legends, CS:GO). The platform has an existing `apps.games.models.Game` model that stores game metadata.

**Ideal Solution:** ForeignKey to Game model
```python
game = models.ForeignKey('games.Game', on_delete=models.PROTECT)
```

**Problem During Strangler Fig Migration:**

1. **Legacy Dependency:** `apps.teams.models.Team` already has FK to `games.Game`
2. **Migration Conflict:** If both systems reference same Game model:
   - Circular migration dependencies
   - Risk of constraint violations during data migration (Phase 5-7)
   - Cannot modify legacy `games.Game` without affecting legacy teams

3. **Strangler Fig Principle:** vNext system MUST be fully decoupled from legacy system
   - Reference in [ARCHITECTURE.md §2.2 Database Independence](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md):
     > "Legacy tables (`teams_team`, `teams_membership`) remain untouched until Phase 8."
     > "vNext tables (`organizations_organization`, `organizations_team`) use proper FK relationships."

4. **Phase 8 Cleanup:** Once legacy system archived, can safely add FKs to shared models

---

## Decision

**We will store game_id as IntegerField (not ForeignKey) during Phases 1-7, then convert to FK in Phase 8.**

Implementation in `apps/organizations/models/team.py`:

```python
class Team(models.Model):
    game_id = models.IntegerField(
        db_index=True,
        help_text="Game title ID (FK to games.Game - avoiding direct FK for now)"
    )
    
    # Phase 8 migration will convert to:
    # game = models.ForeignKey('games.Game', on_delete=models.PROTECT)
```

**Validation in Service Layer (Phase 2):**
```python
# In apps/organizations/services/team_service.py
from apps.games.models import Game

def validate_game_id(game_id: int) -> bool:
    """Validate game_id references valid Game."""
    return Game.objects.filter(id=game_id).exists()

def create_team(name: str, game_id: int, **kwargs) -> Team:
    if not validate_game_id(game_id):
        raise ValidationError(f"Invalid game_id: {game_id}")
    
    return Team.objects.create(name=name, game_id=game_id, **kwargs)
```

---

## Consequences

### Positive

✅ **Complete Decoupling:** Zero FK dependencies between vNext and legacy/shared models  
✅ **Migration Safety:** No risk of constraint violations during Phase 5-7 data migration  
✅ **Strangler Fig Compliance:** Follows architecture principle of system independence  
✅ **Flexible Rollback:** Can rollback vNext without affecting games.Game table

### Negative

❌ **Loss of DB Referential Integrity:** Database can't prevent invalid game_id values  
❌ **Service Layer Validation Required:** Must validate game_id in all creation/update methods  
❌ **Join Inefficiency:** Cannot use `select_related('game')` - must use manual joins or raw queries  
❌ **Migration Debt:** Phase 8 requires data migration to convert IntegerField → ForeignKey

### Neutral

🔶 **Temporary Constraint:** IntegerField is transitional (Phases 1-7), not permanent  
🔶 **Performance:** Index on game_id provides same lookup speed as FK index

---

## Alternatives Considered

### Alternative 1: ForeignKey to games.Game Immediately ❌

**Approach:** Standard Django FK relationship from day one.

**Pros:**
- Database referential integrity enforced
- Django ORM benefits (`select_related`, cascading deletes)
- No migration debt in Phase 8

**Cons:**
- **Migration dependency:** vNext migrations depend on games app
- **Circular risk:** If games app references teams, creates circular dependency
- **Rollback complexity:** Cannot rollback vNext independently
- **Legacy conflict:** Both systems touching same Game model increases risk

**Rejection Reason:** Violates Strangler Fig independence principle. Risk too high during transition.

---

### Alternative 2: Separate TeamGameMap Lookup Table ❌

**Approach:** Create separate mapping table similar to TeamMigrationMap.

```python
class TeamGameMap(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    game_id = models.IntegerField()  # Still no FK
    
    class Meta:
        unique_together = [('team', 'game_id')]
```

**Pros:**
- Keeps Team model "clean" of game references
- Could support multi-game teams (team competes in 2+ games)

**Cons:**
- **Unnecessary complexity:** 99% of teams compete in single game
- **Join overhead:** Every team query requires additional table join
- **YAGNI:** Building for multi-game case we don't currently need

**Rejection Reason:** Over-engineering for hypothetical multi-game scenario. IntegerField simpler.

---

### Alternative 3: CharField for Game Slug ❌

**Approach:** Store game slug string instead of ID (e.g., "valorant", "lol").

```python
game_slug = models.CharField(max_length=50)
```

**Pros:**
- Human-readable in database
- No integer ID dependency

**Cons:**
- **String comparison overhead:** Slower than integer lookups
- **Typo risk:** "valorent" vs "valorant" - IntegerField prevents this
- **Storage waste:** VARCHAR(50) vs INT(4)
- **Still needs validation:** Must validate slug exists in games.Game

**Rejection Reason:** No advantages over IntegerField, worse performance.

---

### Alternative 4: Generic ForeignKey ❌

**Approach:** Use Django's GenericForeignKey to "soft reference" Game model.

**Pros:**
- No hard FK in migrations
- Django ORM still aware of relationship

**Cons:**
- **GenericForeignKey anti-pattern:** Loses database integrity, slow queries
- **Type safety loss:** Can accidentally point to wrong model
- **ORM complexity:** Hard to debug, confusing for team

**Rejection Reason:** GenericForeignKey considered code smell. IntegerField clearer intent.

---

## Implementation Notes

### Service Layer Validation (Phase 2)

**All team creation/update methods MUST validate game_id:**

```python
# apps/organizations/services/team_service.py
from django.core.exceptions import ValidationError
from apps.games.models import Game

class TeamService:
    @staticmethod
    def validate_game_id(game_id: int) -> bool:
        """Validate game_id references valid Game."""
        return Game.objects.filter(id=game_id, is_active=True).exists()
    
    @staticmethod
    def create_team(name: str, game_id: int, organization=None, owner=None, **kwargs) -> Team:
        """Create new team with game_id validation."""
        if not TeamService.validate_game_id(game_id):
            raise ValidationError(f"Invalid game_id: {game_id}. Game does not exist.")
        
        return Team.objects.create(
            name=name,
            game_id=game_id,
            organization=organization,
            owner=owner,
            **kwargs
        )
```

### Manual Joins (When Needed)

```python
# apps/organizations/services/team_service.py
from apps.games.models import Game

def get_team_with_game_details(team_id: int) -> dict:
    """Fetch team with game details via manual join."""
    team = Team.objects.get(id=team_id)
    game = Game.objects.get(id=team.game_id)
    
    return {
        'team': team,
        'game': {
            'id': game.id,
            'name': game.name,
            'slug': game.slug,
            'icon_url': game.icon_url
        }
    }
```

### Phase 8 Migration Path

**Step 1: Add FK field (nullable):**
```python
# apps/organizations/migrations/0015_add_game_fk.py
operations = [
    migrations.AddField(
        model_name='team',
        name='game',
        field=models.ForeignKey(
            'games.Game',
            on_delete=models.PROTECT,
            null=True,
            db_column='game_id_fk'
        )
    )
]
```

**Step 2: Data migration (copy game_id → game FK):**
```python
# apps/organizations/migrations/0016_populate_game_fk.py
def populate_game_fk(apps, schema_editor):
    Team = apps.get_model('organizations', 'Team')
    Game = apps.get_model('games', 'Game')
    
    for team in Team.objects.all():
        try:
            game = Game.objects.get(id=team.game_id)
            team.game = game
            team.save(update_fields=['game'])
        except Game.DoesNotExist:
            # Log invalid game_id for manual resolution
            print(f"Team {team.id} has invalid game_id: {team.game_id}")
```

**Step 3: Remove old IntegerField, make FK non-nullable:**
```python
# apps/organizations/migrations/0017_finalize_game_fk.py
operations = [
    migrations.RemoveField(model_name='team', name='game_id'),
    migrations.AlterField(
        model_name='team',
        name='game',
        field=models.ForeignKey('games.Game', on_delete=models.PROTECT)
    )
]
```

### Testing

**Current Tests (Phase 1):**
```python
# apps/organizations/tests/test_team.py
def test_create_team_with_game_id():
    """Team can be created with integer game_id."""
    team = TeamFactory.create(game_id=1)
    assert team.game_id == 1
```

**Future Tests (Phase 8):**
```python
def test_create_team_with_game_fk():
    """Team requires valid Game FK."""
    game = GameFactory.create()
    team = TeamFactory.create(game=game)
    assert team.game == game
```

---

## Monitoring & Validation

### Invalid game_id Detection

**Periodic Check (cron job):**
```python
# apps/organizations/management/commands/validate_game_ids.py
from django.core.management.base import BaseCommand
from apps.organizations.models import Team
from apps.games.models import Game

class Command(BaseCommand):
    def handle(self, *args, **options):
        valid_game_ids = set(Game.objects.values_list('id', flat=True))
        invalid_teams = Team.objects.exclude(game_id__in=valid_game_ids)
        
        if invalid_teams.exists():
            self.stdout.write(self.style.ERROR(
                f"Found {invalid_teams.count()} teams with invalid game_id"
            ))
            for team in invalid_teams:
                self.stdout.write(f"  Team {team.id}: game_id={team.game_id}")
```

---

## References

**Planning Documents:**
- [TEAM_ORG_ARCHITECTURE.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md) - Section 2.2 Database Independence, Section 1.3 Migration Phases
- [TEAM_ORG_COMPATIBILITY_CONTRACT.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_COMPATIBILITY_CONTRACT.md) - Section 3.1 Database Isolation Rules
- [TEAM_ORG_VNEXT_MASTER_PLAN.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_VNEXT_MASTER_PLAN.md) - Phase 8: Cleanup & Archive

**Related Code:**
- `apps/organizations/models/team.py` - Team model with game_id IntegerField
- `apps/organizations/services/team_service.py` (Phase 2) - game_id validation
- `apps/games/models.py` - Game model (shared between legacy and vNext)

**Migration Strategy:**
- Phase 8 migration plan (docs/migrations/phase8_game_fk_conversion.md) - To be written

---

**Last Updated:** 2026-01-25  
**Status:** Active - IntegerField in use, FK conversion planned for Phase 8  
**Review Date:** Phase 7 completion (before Phase 8 migration)
