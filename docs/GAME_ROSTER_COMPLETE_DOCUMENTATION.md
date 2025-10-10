# 🎮 Game-Specific Roster Management System - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Database Schema](#database-schema)
4. [API Reference](#api-reference)
5. [Validation Rules](#validation-rules)
6. [Migration Guide](#migration-guide)
7. [Frontend Integration](#frontend-integration)
8. [Testing Strategy](#testing-strategy)
9. [Performance Optimization](#performance-optimization)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### Purpose
A flexible, game-aware roster management system supporting 9 esports titles (Valorant, CS2, Dota 2, MLBB, PUBG, Free Fire, eFootball, FC26, CODM) with varying team sizes, role requirements, and tournament regulations.

### Key Features
- ✅ **Multi-game support** with game-specific models and rules
- ✅ **Dynamic roster validation** based on game configuration
- ✅ **Database-level integrity** with unique constraints
- ✅ **Transaction-safe operations** preventing race conditions
- ✅ **Tournament roster locking** mechanism
- ✅ **Unique position enforcement** (Dota 2)
- ✅ **One team per player per game** rule
- ✅ **Automatic captain membership** creation

### Design Principles
1. **Configuration-driven**: Single source of truth in `game_config.py`
2. **Abstract base models**: Share common logic, extend for specifics
3. **Fail-fast validation**: Errors caught early with clear messages
4. **Atomic transactions**: All-or-nothing roster modifications
5. **Future-proof**: Easy to add new games without core changes

---

## System Architecture

### Component Diagram
```
┌────────────────────────────────────────────────────────────┐
│                     game_config.py                          │
│  - GameRosterConfig (named tuple)                          │
│  - GAME_CONFIGS (10 games)                                 │
│  - Utility functions (get_game_config, validate_role)     │
└─────────────────────┬──────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼──────┐            ┌───────▼────────┐
│ validators.py│            │ models/base.py │
│ (15 funcs)   │            │ - BaseTeam     │
│              │◄───────────│ - BaseMember   │
└───────┬──────┘            └───────┬────────┘
        │                           │
        │                  ┌────────▼──────────────┐
        │                  │ models/game_specific  │
        │                  │ - 9 Team models       │
        │                  │ - 9 Membership models │
        │                  └────────┬──────────────┘
        │                           │
┌───────▼───────────────────────────▼───────┐
│         roster_manager.py                  │
│  RosterManager (high-level API)           │
│  - add_player(), remove_player()          │
│  - promote/demote, transfer_captaincy()   │
│  - validate_for_tournament()              │
└───────────────────────────────────────────┘
```

### Data Flow

#### Adding a Player
```
1. User calls: manager.add_player(profile, role, is_starter, ...)
2. RosterManager validates:
   - Roster capacity (via validators.validate_roster_capacity)
   - Role validity (via validators.validate_role_for_team)
   - IGN uniqueness (via validators.validate_unique_ign_in_team)
   - Captain membership (via validators.validate_captain_is_member)
3. Create membership within atomic transaction
4. Call membership.clean() for model-level validation
5. Save membership
6. Return membership object or raise ValidationError
```

---

## Database Schema

### Abstract Models (Not in DB)

#### BaseTeam
```sql
-- Common fields for all game teams
Fields:
  - name (CharField, max 100) ✓ required
  - tag (CharField, max 20) ✓ required
  - slug (SlugField) ✓ unique per game
  - logo (ImageField) nullable
  - description (TextField) nullable
  - captain (FK to UserProfile) ✓ required
  - discord_server / twitter / instagram / youtube / website (URLs)
  - is_active (Boolean, default True)
  - status (CharField: ACTIVE/INACTIVE/DISBANDED)
  - region (CharField, max 50)
  - game_specific_data (JSONField) - for future extensibility
  - created_at / updated_at (DateTimeField)
```

#### BasePlayerMembership
```sql
-- Common fields for all player memberships
Fields:
  - profile (FK to UserProfile) ✓ required
  - team (FK to specific game team) ✓ required
  - role (CharField, max 50) ✓ required
  - secondary_role (CharField, max 50) nullable
  - is_starter (Boolean, default True)
  - is_captain (Boolean, default False)
  - ign (CharField, max 50) ✓ required
  - jersey_number (IntegerField) nullable
  - status (CharField: ACTIVE/INACTIVE/BENCHED/LEFT)
  - joined_at / left_at (DateTimeField)
```

### Concrete Models (In Database)

Each game has two models:

#### ValorantTeam (example)
```sql
Table: teams_valorant_team
Inherits: BaseTeam
Extra Fields:
  - average_rank (CharField, max 50) nullable

Constraints:
  - unique_valorant_team_slug: UNIQUE(slug)
  - unique_valorant_team_name: UNIQUE(name)
```

#### ValorantPlayerMembership
```sql
Table: teams_valorant_player_membership
Inherits: BasePlayerMembership
Extra Fields:
  - competitive_rank (CharField, max 50) nullable
  - agent_pool (JSONField) nullable - list of agents

Foreign Keys:
  - team → teams_valorant_team(id) CASCADE
  - profile → user_profile(id) CASCADE

Constraints:
  - one_captain_per_valorant_team: CHECK(
      CONSTRAINT ensures only 1 active captain per team
    )
  - unique_together: (team, profile)
```

### Special Case: Dota2

#### Dota2PlayerMembership
```sql
Table: teams_dota2_player_membership
Extra Fields:
  - mmr (IntegerField) nullable
  - hero_pool (JSONField) nullable

Unique Constraints:
  - unique_dota2_position_per_team: UNIQUE(team, role)
    ↳ Enforces unique positions (Position 1-5 cannot repeat)
```

### Index Strategy
```sql
-- Automatically created by Django ORM
CREATE INDEX idx_team_slug ON teams_valorant_team(slug);
CREATE INDEX idx_team_captain ON teams_valorant_team(captain_id);
CREATE INDEX idx_membership_profile ON teams_valorant_player_membership(profile_id);
CREATE INDEX idx_membership_team ON teams_valorant_player_membership(team_id);
CREATE INDEX idx_membership_status ON teams_valorant_player_membership(status);
```

---

## API Reference

### RosterManager Class

Location: `apps/teams/roster_manager.py`

#### Initialization
```python
from apps.teams.roster_manager import get_roster_manager

manager = get_roster_manager(team_instance)
```

#### Methods

##### `add_player(profile, role, is_starter, **extra_fields)`
Add a player to the team with full validation.

**Parameters:**
- `profile` (UserProfile) ✓ required - Player's profile
- `role` (str) ✓ required - Player's role (must be valid for game)
- `is_starter` (bool) - True for starter, False for substitute (default: True)
- `secondary_role` (str) - Optional secondary role
- `ign` (str) - In-game name (required)
- `jersey_number` (int) - Optional jersey number
- `**extra_fields` - Game-specific fields (competitive_rank, agent_pool, mmr, etc.)

**Returns:** PlayerMembership instance

**Raises:** `ValidationError` if validation fails

**Example:**
```python
membership = manager.add_player(
    profile=player_profile,
    role="Duelist",
    is_starter=True,
    ign="AlphaJett",
    competitive_rank="Immortal 2",
    agent_pool=["Jett", "Raze"]
)
```

**Validations:**
- ✓ Roster capacity check
- ✓ Role validity
- ✓ IGN uniqueness within team
- ✓ Player not in another active team (same game)
- ✓ Dota2: Position uniqueness for starters

---

##### `remove_player(profile)`
Remove a player from the team.

**Parameters:**
- `profile` (UserProfile) - Player to remove

**Returns:** None

**Raises:** 
- `ValidationError` if player is captain (transfer captaincy first)
- `ValidationError` if removing would violate minimum roster size

**Example:**
```python
manager.remove_player(player_profile)
```

---

##### `promote_to_starter(profile)`
Promote a substitute to starter position.

**Parameters:**
- `profile` (UserProfile) - Player to promote

**Returns:** PlayerMembership instance

**Raises:** 
- `ValidationError` if already starter
- `ValidationError` if max starters reached

**Example:**
```python
manager.promote_to_starter(sub_player)
```

---

##### `demote_to_substitute(profile)`
Demote a starter to substitute position.

**Parameters:**
- `profile` (UserProfile) - Player to demote

**Returns:** PlayerMembership instance

**Raises:**
- `ValidationError` if already substitute
- `ValidationError` if player is captain
- `ValidationError` if would violate minimum starters

**Example:**
```python
manager.demote_to_substitute(starter_player)
```

---

##### `transfer_captaincy(new_captain_profile)`
Transfer team captaincy to another player.

**Parameters:**
- `new_captain_profile` (UserProfile) - New captain

**Returns:** Team instance (updated)

**Raises:**
- `ValidationError` if new captain not in team
- `ValidationError` if new captain not active member

**Example:**
```python
manager.transfer_captaincy(new_captain)
```

**Atomic Operations:**
1. Set old captain's `is_captain=False`
2. Set new captain's `is_captain=True`
3. Update team's `captain` field
4. Save all in transaction

---

##### `change_player_role(profile, new_role, new_secondary_role=None)`
Change a player's role assignment.

**Parameters:**
- `profile` (UserProfile) - Player whose role to change
- `new_role` (str) - New primary role
- `new_secondary_role` (str) - Optional new secondary role

**Returns:** PlayerMembership instance

**Raises:**
- `ValidationError` if role invalid for game
- `ValidationError` (Dota2) if position already taken

**Example:**
```python
manager.change_player_role(
    profile=player,
    new_role="Controller",
    new_secondary_role="Sentinel"
)
```

---

##### `get_roster_status()`
Get current roster capacity and availability.

**Parameters:** None

**Returns:** Dictionary with:
```python
{
    'total_members': int,
    'max_total': int,
    'starters': int,
    'max_starters': int,
    'substitutes': int,
    'max_substitutes': int,
    'can_add_starter': bool,
    'can_add_substitute': bool,
    'is_complete': bool,  # Has all positions filled
}
```

**Example:**
```python
status = manager.get_roster_status()
if status['can_add_starter']:
    print("Can add more starters!")
```

---

##### `validate_for_tournament()`
Comprehensive validation for tournament registration.

**Parameters:** None

**Returns:** Dictionary with:
```python
{
    'is_valid': bool,
    'issues': List[str],  # Blocking issues
    'warnings': List[str],  # Non-blocking warnings
}
```

**Checks:**
- ✓ Minimum roster size (max_starters + 1 sub)
- ✓ All starters have valid roles
- ✓ Captain is active member
- ✓ (Dota2) All 5 positions filled
- ✓ No benched/inactive members counted

**Example:**
```python
validation = manager.validate_for_tournament()
if not validation['is_valid']:
    for issue in validation['issues']:
        print(f"Fix: {issue}")
```

---

##### `get_available_roles(exclude_taken=False)`
Get available roles for the game.

**Parameters:**
- `exclude_taken` (bool) - If True, exclude roles already assigned (Dota2 only)

**Returns:** List[str] of role names

**Example:**
```python
# All roles
roles = manager.get_available_roles()

# For Dota2, only available positions
available = manager.get_available_roles(exclude_taken=True)
```

---

### Validators Module

Location: `apps/teams/validators.py`

All validators raise `ValidationError` on failure.

#### `validate_roster_capacity(team, is_adding_starter=True)`
Check if team can add another member.

#### `validate_role_for_team(team, role)`
Validate role is allowed for the game.

#### `validate_starters_count(team, current_starters_count, is_adding_starter=True)`
Ensure starters count within limits.

#### `validate_minimum_roster(team, min_required)`
Check team has minimum members.

#### `validate_captain_is_member(team)`
Ensure captain is an active member.

#### `validate_unique_ign_in_team(team, ign, exclude_profile=None)`
Check IGN is unique within team.

#### `validate_player_not_in_other_team(profile, game_code, exclude_team=None)`
Ensure player not in another active team (same game).

#### `validate_dota2_unique_position(team, position, exclude_membership=None)`
(Dota2 only) Ensure position not already taken.

#### `validate_tournament_roster_lock(team)`
Check team not locked for tournament.

---

## Validation Rules

### Global Rules (All Games)

#### 1. Roster Capacity
```
total_members ≤ max_starters + max_substitutes
starters ≤ max_starters
substitutes ≤ max_substitutes
```

**Error Example:**
```
"Team already has maximum starters (5). Player must be set as substitute."
```

#### 2. Role Validation
```
role ∈ GAME_CONFIGS[game_code].roles
```

**Error Example:**
```
"Invalid role 'Tank' for Valorant. Valid roles: Duelist, Controller, Initiator, Sentinel, IGL, Flex"
```

#### 3. One Captain Rule
```
∀ team: COUNT(memberships WHERE is_captain=True AND status='ACTIVE') = 1
```

**Database Constraint:** `one_captain_per_[game]_team`

#### 4. Unique IGN
```
∀ team: IGNs must be unique within team
```

**Error Example:**
```
"IGN 'AlphaJett' is already taken by another member in this team."
```

#### 5. Captain Must Be Member
```
team.captain ∈ team.active_memberships
```

**Error Example:**
```
"Team captain must be an active member of the team."
```

#### 6. One Team Per Player Per Game
```
∀ player, game: COUNT(active_memberships) ≤ 1
```

**Error Example:**
```
"You are already in an active Valorant team. Leave your current team before joining another."
```

#### 7. Minimum Roster for Tournaments
```
For tournament registration:
active_members ≥ max_starters + 1
```

**Error Example:**
```
"Team must have at least 6 members (5 starters + 1 substitute) to register for tournaments."
```

### Game-Specific Rules

#### Dota 2: Unique Positions
```
For starters:
  ∀ position ∈ ["Position 1", "Position 2", "Position 3", "Position 4", "Position 5"]:
    COUNT(starters WHERE role=position) ≤ 1
```

**Database Constraint:** `unique_dota2_position_per_team`

**Error Example:**
```
"Position 'Position 1 (Carry)' is already taken by player X. Each position must be unique for starters."
```

### Validation Execution Points

1. **Model-level** (`BasePlayerMembership.clean()`):
   - Executed before save()
   - Validates role, IGN uniqueness, captain status
   
2. **Manager-level** (`RosterManager` methods):
   - Executed before database operations
   - Validates capacity, minimum roster, etc.

3. **Database-level** (Constraints):
   - Executed by PostgreSQL
   - Last line of defense (unique constraints, check constraints)

---

## Migration Guide

### Step 1: Apply Migration

```bash
# Review migration file first
cat apps/teams/migrations/0040_add_game_specific_team_models.py

# Apply to database
python manage.py migrate teams

# Expected output:
# Running migrations:
#   Applying teams.0040_add_game_specific_team_models... OK
```

### Step 2: Verify Migration

```bash
python manage.py check

# Expected output:
# System check identified no issues (0 silenced).
```

### Step 3: Create Test Data

```bash
# All games
python manage.py create_test_game_teams

# Specific game
python manage.py create_test_game_teams --game valorant --game cs2

# Cleanup old test data
python manage.py create_test_game_teams --cleanup
```

### Step 4: Test in Django Admin

1. Navigate to: `http://localhost:8000/admin/teams/`
2. Verify all 9 game team models appear:
   - Valorant teams
   - CS2 teams
   - Dota2 teams
   - etc.
3. Create a test team and add members via inline forms

### Step 5: Test RosterManager API

```python
from apps.teams.models import ValorantTeam
from apps.teams.roster_manager import get_roster_manager
from apps.user_profile.models import UserProfile

# Get or create test team
team = ValorantTeam.objects.first()
manager = get_roster_manager(team)

# Test operations
status = manager.get_roster_status()
print(f"Roster: {status['total_members']}/{status['max_total']}")

validation = manager.validate_for_tournament()
print(f"Tournament ready: {validation['is_valid']}")
```

### Rollback (if needed)

```bash
# Rollback migration
python manage.py migrate teams 0039  # Previous migration number

# Delete test data
python manage.py create_test_game_teams --cleanup
```

---

## Frontend Integration

### REST API Endpoints (Recommended)

#### Example DRF Serializers

```python
# apps/teams/serializers.py
from rest_framework import serializers
from apps.teams.models import ValorantTeam, ValorantPlayerMembership

class ValorantPlayerMembershipSerializer(serializers.ModelSerializer):
    profile_username = serializers.CharField(source='profile.user.username', read_only=True)
    profile_avatar = serializers.ImageField(source='profile.avatar', read_only=True)
    
    class Meta:
        model = ValorantPlayerMembership
        fields = [
            'id', 'profile', 'profile_username', 'profile_avatar',
            'role', 'secondary_role', 'is_starter', 'is_captain',
            'ign', 'jersey_number', 'status', 'competitive_rank',
            'agent_pool', 'joined_at'
        ]
        read_only_fields = ['joined_at', 'is_captain']

class ValorantTeamSerializer(serializers.ModelSerializer):
    captain_username = serializers.CharField(source='captain.user.username', read_only=True)
    roster = ValorantPlayerMembershipSerializer(source='get_memberships', many=True, read_only=True)
    roster_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ValorantTeam
        fields = [
            'id', 'name', 'tag', 'slug', 'logo', 'description',
            'captain', 'captain_username', 'region', 'average_rank',
            'is_active', 'status', 'discord_server', 'twitter',
            'roster', 'roster_status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']
    
    def get_roster_status(self, obj):
        from apps.teams.roster_manager import get_roster_manager
        manager = get_roster_manager(obj)
        return manager.get_roster_status()
```

#### Example ViewSets

```python
# apps/teams/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.teams.models import ValorantTeam
from apps.teams.serializers import ValorantTeamSerializer
from apps.teams.roster_manager import get_roster_manager

class ValorantTeamViewSet(viewsets.ModelViewSet):
    queryset = ValorantTeam.objects.filter(is_active=True)
    serializer_class = ValorantTeamSerializer
    lookup_field = 'slug'
    
    @action(detail=True, methods=['post'])
    def add_player(self, request, slug=None):
        """Add a player to the team."""
        team = self.get_object()
        manager = get_roster_manager(team)
        
        try:
            membership = manager.add_player(
                profile=request.user.profile,
                role=request.data.get('role'),
                is_starter=request.data.get('is_starter', True),
                ign=request.data.get('ign'),
                competitive_rank=request.data.get('competitive_rank'),
                agent_pool=request.data.get('agent_pool', [])
            )
            serializer = ValorantPlayerMembershipSerializer(membership)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def promote_player(self, request, slug=None):
        """Promote a substitute to starter."""
        team = self.get_object()
        manager = get_roster_manager(team)
        
        try:
            profile = UserProfile.objects.get(id=request.data.get('profile_id'))
            membership = manager.promote_to_starter(profile)
            serializer = ValorantPlayerMembershipSerializer(membership)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def validate_tournament(self, request, slug=None):
        """Check if team is ready for tournament."""
        team = self.get_object()
        manager = get_roster_manager(team)
        
        validation = manager.validate_for_tournament()
        return Response(validation)
```

#### URL Configuration

```python
# apps/teams/urls.py
from rest_framework.routers import DefaultRouter
from apps.teams.views import ValorantTeamViewSet

router = DefaultRouter()
router.register(r'valorant', ValorantTeamViewSet, basename='valorant-team')

urlpatterns = router.urls
```

### Frontend Example (React)

```jsx
// TeamRoster.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function TeamRoster({ teamSlug }) {
    const [team, setTeam] = useState(null);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        axios.get(`/api/teams/valorant/${teamSlug}/`)
            .then(res => {
                setTeam(res.data);
                setLoading(false);
            });
    }, [teamSlug]);
    
    const addPlayer = async (playerData) => {
        try {
            const res = await axios.post(
                `/api/teams/valorant/${teamSlug}/add_player/`,
                playerData
            );
            // Refresh team data
            setTeam(prev => ({
                ...prev,
                roster: [...prev.roster, res.data]
            }));
            alert('Player added successfully!');
        } catch (error) {
            alert(`Error: ${error.response.data.error}`);
        }
    };
    
    if (loading) return <div>Loading...</div>;
    
    return (
        <div>
            <h2>{team.name} ({team.tag})</h2>
            <p>Region: {team.region} | Rank: {team.average_rank}</p>
            
            <h3>Roster ({team.roster_status.total_members}/{team.roster_status.max_total})</h3>
            
            <div>
                <h4>Starters ({team.roster_status.starters}/{team.roster_status.max_starters})</h4>
                {team.roster.filter(m => m.is_starter && m.status === 'ACTIVE').map(member => (
                    <div key={member.id}>
                        <img src={member.profile_avatar} alt="" />
                        <strong>{member.ign}</strong>
                        <span>{member.role}</span>
                        {member.is_captain && <span>👑 Captain</span>}
                        <span>{member.competitive_rank}</span>
                    </div>
                ))}
            </div>
            
            <div>
                <h4>Substitutes ({team.roster_status.substitutes}/{team.roster_status.max_substitutes})</h4>
                {team.roster.filter(m => !m.is_starter && m.status === 'ACTIVE').map(member => (
                    <div key={member.id}>
                        <strong>{member.ign}</strong> - {member.role}
                    </div>
                ))}
            </div>
        </div>
    );
}
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_roster_management.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.teams.models import ValorantTeam, ValorantPlayerMembership
from apps.teams.roster_manager import get_roster_manager
from apps.user_profile.models import UserProfile

class RosterManagementTestCase(TestCase):
    
    def setUp(self):
        # Create test users
        self.players = [
            UserProfile.objects.create(user=User.objects.create(username=f'player{i}'))
            for i in range(10)
        ]
        
        # Create test team
        self.team = ValorantTeam.objects.create(
            name="Test Team",
            tag="TEST",
            captain=self.players[0]
        )
        
        self.manager = get_roster_manager(self.team)
    
    def test_add_player_success(self):
        """Test successfully adding a player."""
        membership = self.manager.add_player(
            profile=self.players[1],
            role="Duelist",
            is_starter=True,
            ign="TestPlayer1"
        )
        
        self.assertEqual(membership.team, self.team)
        self.assertEqual(membership.profile, self.players[1])
        self.assertTrue(membership.is_starter)
    
    def test_add_player_invalid_role(self):
        """Test adding player with invalid role raises error."""
        with self.assertRaises(ValidationError) as cm:
            self.manager.add_player(
                profile=self.players[1],
                role="Invalid Role",
                is_starter=True,
                ign="TestPlayer1"
            )
        
        self.assertIn("Invalid role", str(cm.exception))
    
    def test_max_starters_enforcement(self):
        """Test cannot exceed max starters."""
        # Add 5 starters
        for i in range(1, 6):
            self.manager.add_player(
                profile=self.players[i],
                role="Duelist",
                is_starter=True,
                ign=f"Player{i}"
            )
        
        # Try to add 6th starter
        with self.assertRaises(ValidationError) as cm:
            self.manager.add_player(
                profile=self.players[6],
                role="Controller",
                is_starter=True,
                ign="Player6"
            )
        
        self.assertIn("maximum starters", str(cm.exception))
    
    def test_unique_ign_enforcement(self):
        """Test IGN must be unique within team."""
        self.manager.add_player(
            profile=self.players[1],
            role="Duelist",
            is_starter=True,
            ign="DuplicateIGN"
        )
        
        with self.assertRaises(ValidationError):
            self.manager.add_player(
                profile=self.players[2],
                role="Controller",
                is_starter=True,
                ign="DuplicateIGN"  # Same IGN
            )
    
    def test_promote_substitute(self):
        """Test promoting substitute to starter."""
        # Add player as substitute
        sub = self.manager.add_player(
            profile=self.players[1],
            role="Sentinel",
            is_starter=False,
            ign="SubPlayer"
        )
        
        # Promote to starter
        promoted = self.manager.promote_to_starter(self.players[1])
        
        self.assertTrue(promoted.is_starter)
    
    def test_transfer_captaincy(self):
        """Test transferring captaincy."""
        # Add new player
        self.manager.add_player(
            profile=self.players[1],
            role="IGL",
            is_starter=True,
            ign="NewCaptain"
        )
        
        # Transfer captaincy
        self.manager.transfer_captaincy(self.players[1])
        
        self.team.refresh_from_db()
        self.assertEqual(self.team.captain, self.players[1])
        
        # Check membership flags
        old_captain = self.team.get_memberships().get(profile=self.players[0])
        new_captain = self.team.get_memberships().get(profile=self.players[1])
        
        self.assertFalse(old_captain.is_captain)
        self.assertTrue(new_captain.is_captain)
    
    def test_tournament_validation(self):
        """Test tournament validation."""
        # Team with only captain (insufficient)
        validation = self.manager.validate_for_tournament()
        self.assertFalse(validation['is_valid'])
        self.assertTrue(len(validation['issues']) > 0)
        
        # Add full roster (5 starters + 2 subs)
        for i in range(1, 8):
            self.manager.add_player(
                profile=self.players[i],
                role="Duelist" if i <= 5 else "Sentinel",
                is_starter=(i <= 5),
                ign=f"Player{i}"
            )
        
        # Now should be valid
        validation = self.manager.validate_for_tournament()
        self.assertTrue(validation['is_valid'])
        self.assertEqual(len(validation['issues']), 0)
```

### Integration Tests

```python
# tests/test_roster_integration.py
class RosterIntegrationTestCase(TestCase):
    
    def test_dota2_unique_positions(self):
        """Test Dota2 unique position enforcement."""
        from apps.teams.models import Dota2Team
        
        team = Dota2Team.objects.create(
            name="Dota Team",
            tag="DOTA",
            captain=self.players[0]
        )
        
        manager = get_roster_manager(team)
        
        # Add Position 1
        manager.add_player(
            profile=self.players[1],
            role="Position 1 (Carry)",
            is_starter=True,
            ign="Carry1"
        )
        
        # Try to add another Position 1 (should fail)
        with self.assertRaises(ValidationError):
            manager.add_player(
                profile=self.players[2],
                role="Position 1 (Carry)",
                is_starter=True,
                ign="Carry2"
            )
    
    def test_one_team_per_game_per_player(self):
        """Test player can't join multiple teams in same game."""
        team1 = ValorantTeam.objects.create(
            name="Team 1",
            tag="T1",
            captain=self.players[0]
        )
        
        team2 = ValorantTeam.objects.create(
            name="Team 2",
            tag="T2",
            captain=self.players[1]
        )
        
        manager1 = get_roster_manager(team1)
        manager2 = get_roster_manager(team2)
        
        # Player joins team 1
        manager1.add_player(
            profile=self.players[2],
            role="Duelist",
            is_starter=True,
            ign="Player2"
        )
        
        # Try to join team 2 (should fail)
        with self.assertRaises(ValidationError):
            manager2.add_player(
                profile=self.players[2],
                role="Controller",
                is_starter=True,
                ign="Player2Alt"
            )
```

### Run Tests

```bash
# All roster tests
python manage.py test tests.test_roster_management tests.test_roster_integration

# Specific test
python manage.py test tests.test_roster_management.RosterManagementTestCase.test_max_starters_enforcement

# With coverage
coverage run --source='apps/teams' manage.py test
coverage report
```

---

## Performance Optimization

### Query Optimization

#### Use `select_related` for ForeignKeys

```python
# BAD: N+1 queries
teams = ValorantTeam.objects.all()
for team in teams:
    print(team.captain.user.username)  # Extra query each iteration

# GOOD: 1 query
teams = ValorantTeam.objects.select_related('captain__user').all()
for team in teams:
    print(team.captain.user.username)
```

#### Use `prefetch_related` for reverse ForeignKeys

```python
# BAD: N+1 queries
teams = ValorantTeam.objects.all()
for team in teams:
    for member in team.valorant_memberships.all():  # Extra query
        print(member.ign)

# GOOD: 2 queries
teams = ValorantTeam.objects.prefetch_related('valorant_memberships').all()
for team in teams:
    for member in team.valorant_memberships.all():
        print(member.ign)
```

#### Combine for Complex Queries

```python
teams = ValorantTeam.objects.select_related(
    'captain__user'
).prefetch_related(
    'valorant_memberships__profile__user'
).filter(is_active=True)
```

### Caching Strategy

```python
from django.core.cache import cache

def get_team_roster_status(team_slug):
    """Cache roster status for 5 minutes."""
    cache_key = f'roster_status_{team_slug}'
    
    status = cache.get(cache_key)
    if status is None:
        team = ValorantTeam.objects.get(slug=team_slug)
        manager = get_roster_manager(team)
        status = manager.get_roster_status()
        cache.set(cache_key, status, 300)  # 5 minutes
    
    return status

# Invalidate cache when roster changes
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver([post_save, post_delete], sender=ValorantPlayerMembership)
def invalidate_roster_cache(sender, instance, **kwargs):
    cache_key = f'roster_status_{instance.team.slug}'
    cache.delete(cache_key)
```

### Database Indexing

Already handled by Django ORM for:
- ForeignKey fields (team_id, profile_id)
- Unique fields (slug)

Add custom indexes if needed:

```python
class ValorantTeam(BaseTeam):
    class Meta:
        indexes = [
            models.Index(fields=['region', 'is_active']),
            models.Index(fields=['status', 'created_at']),
        ]
```

---

## Troubleshooting

### Common Issues

#### Issue 1: "Player already in active team"

**Cause:** Player trying to join second team for same game.

**Solution:**
```python
# Option 1: Leave current team first
current_membership = ValorantPlayerMembership.objects.get(
    profile=player,
    status='ACTIVE'
)
old_manager = get_roster_manager(current_membership.team)
old_manager.remove_player(player)

# Option 2: Set status to 'LEFT' instead of deleting
current_membership.status = 'LEFT'
current_membership.left_at = timezone.now()
current_membership.save()
```

#### Issue 2: Migration Fails

**Error:** `django.db.utils.OperationalError: relation already exists`

**Solution:**
```bash
# Check current migration state
python manage.py showmigrations teams

# If 0040 partially applied, rollback and reapply
python manage.py migrate teams 0039
python manage.py migrate teams
```

#### Issue 3: "Position already taken" (Dota2)

**Cause:** Trying to assign duplicate position for starters.

**Solution:**
```python
# Check available positions
manager = get_roster_manager(dota_team)
available = manager.get_available_roles(exclude_taken=True)
print(f"Available positions: {available}")

# Use an available position or change existing player
```

#### Issue 4: Admin Shows No Roster

**Cause:** `get_memberships()` not implemented or incorrect.

**Solution:**
```python
# Ensure model has correct related_name
class ValorantPlayerMembership(BasePlayerMembership):
    team = models.ForeignKey(
        ValorantTeam,
        on_delete=models.CASCADE,
        related_name='valorant_memberships'  # Must match
    )

# Ensure team model returns correct queryset
class ValorantTeam(BaseTeam):
    def get_memberships(self):
        return self.valorant_memberships.all()  # Use related_name
```

#### Issue 5: Validation Not Triggered

**Cause:** Directly using `.save()` bypasses `.clean()`.

**Solution:**
```python
# BAD: Bypasses validation
membership = ValorantPlayerMembership(...)
membership.save()

# GOOD: Triggers validation
membership = ValorantPlayerMembership(...)
membership.full_clean()  # Raises ValidationError if invalid
membership.save()

# BEST: Use RosterManager (handles validation automatically)
manager.add_player(...)
```

### Debug Checklist

When encountering issues:

1. ✅ Check migration applied: `python manage.py showmigrations teams`
2. ✅ Verify model registered in admin: Check `admin.site.registered_models`
3. ✅ Check for validation errors: Run `team.clean()` and `membership.clean()`
4. ✅ Inspect database constraints: `\d teams_valorant_team` (PostgreSQL)
5. ✅ Review logs: Check Django logs for detailed error messages
6. ✅ Test in isolation: Use `python manage.py shell` to test specific operations

---

## Appendix

### Game Code Reference

| Game Code | Display Name | Roster Size |
|-----------|-------------|-------------|
| `valorant` | Valorant | 5+2 |
| `cs2` | Counter-Strike 2 | 5+2 |
| `dota2` | Dota 2 | 5+2 |
| `mlbb` | Mobile Legends | 5+2 |
| `pubg` | PUBG | 4+2 |
| `freefire` | Free Fire | 4+2 |
| `efootball` | eFootball | 2+1 |
| `fc26` | FC 26 | 1+1 |
| `codm` | Call of Duty Mobile | 5+2 |
| `csgo` | CS:GO (Legacy) | 5+2 |

### File Structure Reference

```
apps/teams/
├── __init__.py
├── game_config.py                    # Game configurations
├── validators.py                     # Validation functions
├── roster_manager.py                 # RosterManager class
├── models/
│   ├── __init__.py                   # Model exports
│   ├── base.py                       # BaseTeam, BasePlayerMembership
│   ├── game_specific.py              # Game-specific models
│   └── _legacy.py                    # Old models (deprecated)
├── admin/
│   ├── __init__.py
│   └── game_specific_admin.py        # Django admin registration
├── management/
│   └── commands/
│       └── create_test_game_teams.py # Test data generation
├── migrations/
│   ├── 0039_previous_migration.py
│   └── 0040_add_game_specific_team_models.py
└── examples/
    └── roster_management_examples.py
```

### Status Codes

#### Team Status
- `ACTIVE`: Team actively competing
- `INACTIVE`: Temporarily inactive
- `DISBANDED`: Team no longer exists

#### Membership Status
- `ACTIVE`: Currently playing
- `INACTIVE`: Temporarily inactive
- `BENCHED`: Benched but still on roster
- `LEFT`: Left the team

---

## Changelog

### Version 1.0.0 (2025)
- ✅ Initial implementation
- ✅ 9 game-specific models
- ✅ RosterManager API
- ✅ Comprehensive validation
- ✅ Django admin integration
- ✅ Test data generation command
- ✅ Migration 0040 created

---

**Questions or Issues?** Check the examples file or create a GitHub issue.

**Last Updated:** 2025  
**Migration:** `0040_add_game_specific_team_models.py`  
**Status:** ✅ Production Ready
