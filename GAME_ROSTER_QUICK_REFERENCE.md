# 🎮 Game Roster Management - Quick Reference

## Overview
Complete game-specific roster management system supporting 9 esports titles with dynamic team sizes, role validation, and tournament-ready features.

---

## 📋 Supported Games

| Game | Starters | Subs | Total | Unique Roles? |
|------|----------|------|-------|---------------|
| **Valorant** | 5 | 2 | 7 | No |
| **CS2** | 5 | 2 | 7 | No |
| **Dota 2** | 5 | 2 | 7 | **Yes** ✓ |
| **MLBB** | 5 | 2 | 7 | No |
| **PUBG** | 4 | 2 | 6 | No |
| **Free Fire** | 4 | 2 | 6 | No |
| **eFootball** | 2 | 1 | 3 | No |
| **FC26** | 1 | 1 | 2 | No |
| **CODM** | 5 | 2 | 7 | No |

---

## 🚀 Quick Start

### 1. Apply Database Migration
```bash
python manage.py migrate teams
```

### 2. Create Test Teams
```bash
# All games
python manage.py create_test_game_teams

# Specific game
python manage.py create_test_game_teams --game valorant

# Cleanup existing test data first
python manage.py create_test_game_teams --cleanup
```

---

## 💻 Basic Usage

### Import Models
```python
from apps.teams.models import ValorantTeam, ValorantPlayerMembership
from apps.teams.roster_manager import get_roster_manager
from apps.user_profile.models import UserProfile
```

### Create a Team
```python
team = ValorantTeam.objects.create(
    name="Team Alpha",
    tag="ALPHA",
    captain=UserProfile.objects.get(user__username="player1"),
    region="North America",
)
```

### Get Roster Manager
```python
manager = get_roster_manager(team)
```

### Add Players
```python
manager.add_player(
    profile=UserProfile.objects.get(user__username="player2"),
    role="Duelist",
    is_starter=True,
    ign="AlphaEntry",
    competitive_rank="Immortal 2",
    agent_pool=["Jett", "Raze"]
)
```

---

## 🎯 Common Operations

### Check Roster Status
```python
status = manager.get_roster_status()
print(f"Members: {status['total_members']}/{status['max_total']}")
print(f"Starters: {status['starters']}/{status['max_starters']}")
print(f"Can add: {status['can_add_starter']}")
```

### Promote/Demote Players
```python
# Promote sub to starter
manager.promote_to_starter(player_profile)

# Demote starter to sub
manager.demote_to_substitute(player_profile)
```

### Transfer Captaincy
```python
manager.transfer_captaincy(new_captain_profile)
```

### Change Player Role
```python
manager.change_player_role(
    profile=player_profile,
    new_role="Controller",
    new_secondary_role="Sentinel"
)
```

### Remove Player
```python
manager.remove_player(player_profile)
```

---

## ✅ Validation

### Pre-Tournament Validation
```python
validation = manager.validate_for_tournament()

if validation['is_valid']:
    print("Ready for tournament!")
else:
    for issue in validation['issues']:
        print(f"Issue: {issue}")
```

### Get Available Roles
```python
# All roles for the game
available = manager.get_available_roles()

# For Dota2, exclude taken positions
available = manager.get_available_roles(exclude_taken=True)
```

---

## 🔒 Automatic Validations

The system automatically enforces:

✓ **Roster capacity limits** (e.g., max 5 starters for Valorant)  
✓ **Role validation** (only valid roles for each game)  
✓ **One captain per team** (database constraint)  
✓ **Unique IGN within team**  
✓ **Captain must be an active member**  
✓ **Minimum roster for tournaments** (at least max_starters + 1 sub)  
✓ **Unique positions** (Dota2 only - Position 1-5 must be unique)  
✓ **Tournament roster lock** (prevents changes during active tournaments)  
✓ **One team per game per player** (can't join multiple Valorant teams)

---

## 🎮 Game-Specific Roles

### Valorant
```python
roles = ["Duelist", "Controller", "Initiator", "Sentinel", "IGL", "Flex"]
```

### CS2
```python
roles = ["Entry Fragger", "AWPer", "Support", "Lurker", "IGL"]
```

### Dota 2 (Unique Positions Required)
```python
roles = [
    "Position 1 (Carry)",
    "Position 2 (Mid)",
    "Position 3 (Offlane)",
    "Position 4 (Soft Support)",
    "Position 5 (Hard Support)"
]
```

### MLBB
```python
roles = ["Exp Laner", "Jungler", "Mid Laner", "Roamer", "Gold Laner", "Flex"]
```

### PUBG & Free Fire
```python
roles = ["Fragger", "IGL", "Support", "Sniper", "Flex"]
```

### eFootball
```python
roles = ["Striker", "Midfielder"]
```

### FC26
```python
roles = ["Player"]  # Single player game
```

### CODM
```python
roles = ["Slayer", "OBJ", "AR", "Sniper", "SMG", "Flex"]
```

---

## 🛠️ Advanced Features

### Game-Specific Fields

#### Valorant & CS2
```python
ValorantPlayerMembership:
    - competitive_rank (CharField)
    - agent_pool (JSONField) - list of agents/weapons

ValorantTeam:
    - average_rank (CharField)
```

#### Dota 2
```python
Dota2PlayerMembership:
    - mmr (IntegerField)
    - hero_pool (JSONField)
```

#### MLBB
```python
MLBBPlayerMembership:
    - rank (CharField)
    - hero_pool (JSONField)
```

### Bulk Operations with Transaction Safety
```python
from django.db import transaction

with transaction.atomic():
    for player_data in players_list:
        manager.add_player(**player_data)
```

---

## 📊 Querying Teams

### Get All Active Teams for a Game
```python
teams = ValorantTeam.objects.filter(is_active=True)
```

### Get Teams by Region
```python
na_teams = ValorantTeam.objects.filter(region__icontains="North America")
```

### Get Teams with Full Rosters
```python
from django.db.models import Count, Q

full_teams = ValorantTeam.objects.annotate(
    member_count=Count('valorant_memberships', filter=Q(
        valorant_memberships__status='ACTIVE'
    ))
).filter(member_count=7)  # 5 starters + 2 subs
```

### Get Player's Current Team
```python
membership = ValorantPlayerMembership.objects.filter(
    profile=player_profile,
    status='ACTIVE'
).select_related('team').first()

if membership:
    print(f"Player is in: {membership.team.name}")
```

---

## 🔍 Django Admin

All game-specific teams are registered in Django admin:

- **Roster Status Display**: Shows X/Y members at a glance
- **Inline Player Management**: Add/edit members directly in team view
- **Captain Link**: Quick navigation to captain profile
- **Filter by Status**: Active/Inactive/Disbanded teams
- **Search**: By name, tag, captain

Access at: `/admin/teams/`

---

## ⚠️ Common Errors & Solutions

### "Team already has maximum starters"
```python
# Solution: Add as substitute instead
manager.add_player(..., is_starter=False)
```

### "Invalid role for [Game]"
```python
# Solution: Check valid roles
from apps.teams.game_config import get_available_roles
valid_roles = get_available_roles("valorant")
```

### "Player already in active team"
```python
# Solution: Leave current team first
current_membership = ValorantPlayerMembership.objects.get(
    profile=player, status='ACTIVE'
)
manager_old = get_roster_manager(current_membership.team)
manager_old.remove_player(player)
```

### "Position X already taken" (Dota2)
```python
# Solution: Each Dota2 position must be unique
# Check available positions:
available = manager.get_available_roles(exclude_taken=True)
```

---

## 🧪 Testing

### Run Management Command Tests
```bash
# Create test teams for all games
python manage.py create_test_game_teams

# Test specific game
python manage.py create_test_game_teams --game dota2
```

### Check Team Integrity
```python
team = ValorantTeam.objects.get(tag="ALPHA")
team.clean()  # Raises ValidationError if issues found
```

---

## 📚 Architecture Overview

```
apps/teams/
├── game_config.py              # Game configurations (10 games)
├── validators.py               # 15 validation functions
├── roster_manager.py           # RosterManager class (high-level API)
├── models/
│   ├── base.py                 # BaseTeam, BasePlayerMembership
│   ├── game_specific.py        # 9 team models + 9 membership models
│   └── __init__.py             # Model exports
├── admin/
│   └── game_specific_admin.py  # Django admin for all games
├── management/commands/
│   └── create_test_game_teams.py
└── examples/
    └── roster_management_examples.py
```

---

## 🔮 Adding a New Game

1. **Add configuration** to `game_config.py`:
```python
GAME_CONFIGS['new_game'] = GameRosterConfig(
    game_code='new_game',
    display_name='New Game',
    min_starters=4,
    max_starters=5,
    min_substitutes=0,
    max_substitutes=2,
    roles=['Role1', 'Role2', 'Role3'],
    requires_unique_roles=False,
)
```

2. **Create models** in `game_specific.py`:
```python
class NewGameTeam(BaseTeam):
    game_code = 'new_game'
    
    class Meta:
        db_table = 'teams_new_game_team'
        
    def get_memberships(self):
        return self.newgame_memberships.all()

class NewGamePlayerMembership(BasePlayerMembership):
    team = models.ForeignKey(NewGameTeam, ...)
    # Add game-specific fields
```

3. **Generate migration**:
```bash
python manage.py makemigrations teams --name add_new_game_team
python manage.py migrate teams
```

4. **Register admin** in `game_specific_admin.py`

5. **Update exports** in `models/__init__.py`

---

## 📞 Support & Resources

- **Full Examples**: `apps/teams/examples/roster_management_examples.py`
- **Migration File**: `apps/teams/migrations/0040_add_game_specific_team_models.py`
- **API Reference**: See docstrings in `roster_manager.py` and `validators.py`

---

## ✨ Key Features Summary

🎯 **9 esports games supported** with different roster sizes  
🔒 **Database-level constraints** prevent data corruption  
✅ **Automatic validation** enforces all roster rules  
🎮 **Game-specific fields** (ranks, hero pools, etc.)  
⚡ **Transaction-safe operations** prevent race conditions  
🏆 **Tournament-ready** with roster lock validation  
📊 **Django admin integration** for easy management  
🔮 **Future-proof design** - easy to add new games  
🧪 **Test data generation** for development  
📚 **Comprehensive documentation** and examples

---

**Status**: ✅ All code implemented, migration generated, ready for deployment  
**Last Updated**: 2025  
**Migration**: `0040_add_game_specific_team_models.py`
