# Dual-Role System Documentation

## Overview

The DeltaCrown platform implements a **Dual-Role System** for team management, separating organizational roles from in-game tactical roles.

## The Two Role Types

### 1. Team Membership Role (Organizational)

**Purpose**: Defines a user's official status and permissions within the team on the platform.

**Values**:
- `CAPTAIN`: Team leader with full management permissions
- `PLAYER`: Active player on the roster
- `SUB` (Substitute): Reserve player who can fill in
- `MANAGER`: Team manager (administrative role)

**Characteristics**:
- Universal and game-agnostic
- Determines platform permissions (who can invite, manage settings, etc.)
- Affects team hierarchy and decision-making
- One person can only be in one team per game

### 2. In-Game Role (Tactical)

**Purpose**: Defines a player's specific tactical function during a match for a particular game.

**Values**: Dynamic based on the game (see Game-Specific Roles below)

**Characteristics**:
- Game-specific
- Only applies to members with PLAYER or SUB membership role
- Describes tactical function in matches
- Optional but recommended for competitive teams

## Why Both Are Needed

The dual-role system solves a fundamental problem:

**Before (Single Role)**:
- ❌ Confusion: Is "Substitute" a role like "Duelist"? No, they're different concepts.
- ❌ Limitation: A substitute can't have a tactical role assigned
- ❌ Poor UX: Mixing organizational status with gameplay function

**After (Dual Role)**:
- ✅ Clear separation: "Substitute (Duelist)" - organizational status + tactical role
- ✅ Flexibility: Substitutes can have defined roles for when they play
- ✅ Better analytics: Track player performance by tactical role
- ✅ Professional structure: Mirrors real esports team organization

## Game-Specific Roles

### VALORANT
- **Duelist**: Primary fraggers, create space
- **Controller**: Smoke specialists, map control
- **Initiator**: Information gatherers, setup plays
- **Sentinel**: Defensive anchors, site holders
- **IGL**: In-Game Leader, shot caller
- **Flex**: Multi-role player

### Counter-Strike 2 (CS2)
- **IGL**: In-Game Leader, strategist
- **Entry Fragger**: First contact, opens sites
- **AWPer**: Sniper specialist
- **Lurker**: Late-round player, flanks
- **Support**: Utility user, team support
- **Rifler**: Versatile gunner

### Dota 2
- **Position 1 (Carry)**: Main damage dealer, farm priority
- **Position 2 (Mid)**: Mid lane, tempo controller
- **Position 3 (Offlane)**: Offlane, space creator
- **Position 4 (Soft Support)**: Roaming support, playmaker
- **Position 5 (Hard Support)**: Ward buyer, protector

*Note: Dota 2 requires unique roles (no duplicates)*

### Mobile Legends: Bang Bang (MLBB)
- **Gold Laner**: Bot lane farmer, marksman
- **EXP Laner**: Top lane, tank/fighter
- **Mid Laner**: Mid lane mage/assassin
- **Jungler**: Jungle core, ganker
- **Roamer**: Support, rotator

### PUBG Mobile
- **IGL/Shot Caller**: Team leader, strategy
- **Assaulter/Fragger**: Aggressive pusher
- **Support**: Utility user, healer
- **Sniper/Scout**: Long-range specialist

### Free Fire
- **Rusher**: Aggressive entry
- **Flanker**: Side attacker, rotator
- **Support**: Team support, utility
- **Shot Caller**: Leader, strategist

### eFootball & FC 26
- **Note**: These games are primarily 1v1 or 2v2 and do not require tactical role selection
- Players only need their membership role (Player/Substitute)

### Call of Duty Mobile (CODM)
- **IGL**: In-game leader
- **Slayer**: High-kill fragger
- **Anchor**: Defensive holder
- **Support**: Team utility
- **Objective Player**: OBJ focused

## Usage in Code

### Model Layer

```python
from apps.teams.models import TeamMembership

# Create a membership with both roles
membership = TeamMembership.objects.create(
    team=team,
    profile=user_profile,
    role=TeamMembership.Role.PLAYER,  # Membership role
    player_role='Duelist',  # In-game role
    status=TeamMembership.Status.ACTIVE
)

# Access roles
print(membership.role)  # 'PLAYER'
print(membership.player_role)  # 'Duelist'
print(membership.display_full_role)  # 'Player (Duelist)'

# Validate and set player role
membership.set_player_role('Controller')  # Validates against game
membership.save()

# Get available roles for the team's game
available_roles = membership.get_available_player_roles()
```

### View Layer

```python
from apps.teams.dual_role_system import (
    get_player_roles_for_game,
    validate_roster_composition,
    format_roster_for_display,
)

# Get roles for form dropdown
roles = get_player_roles_for_game('valorant')
# Returns: [{'value': 'Duelist', 'label': 'Duelist', 'description': '...'}, ...]

# Validate roster composition
is_valid, errors = validate_roster_composition(team)
if not is_valid:
    for error in errors:
        messages.error(request, error)

# Format roster for display
roster_data = format_roster_for_display(team)
```

### Template Layer

```django
{% load dual_role_tags %}

<!-- Display full role -->
{{ membership|display_full_role }}  {# Output: "Player (Duelist)" #}

<!-- Role badge with color -->
{% role_badge membership.player_role team.game %}

<!-- Check if game supports player roles -->
{% if team.game|supports_player_roles %}
    <div class="role-selector">
        {% for role in team.game|get_player_roles %}
            <option value="{{ role.value }}">{{ role.label }}</option>
        {% endfor %}
    </div>
{% endif %}

<!-- Get roster organized by roles -->
{% get_roster_by_roles team as roster_by_role %}
{% for role, members in roster_by_role.items %}
    <h3>{{ role }}</h3>
    {% for member in members %}
        {{ member.profile.user.username }}
    {% endfor %}
{% endfor %}
```

## API Serialization

```python
from apps.teams.dual_role_system import serialize_member_with_roles

# Serialize for API response
member_data = serialize_member_with_roles(membership)
# Returns:
{
    'id': 123,
    'user': {...},
    'membership_role': {
        'value': 'PLAYER',
        'display': 'Player'
    },
    'player_role': {
        'value': 'Duelist',
        'display': 'Duelist',
        'description': 'Primary fragger...'
    },
    'display_full_role': 'Player (Duelist)',
    'is_captain': False,
    'is_player_or_sub': True,
    ...
}
```

## Migration Path

The new `player_role` field has been added to the `TeamMembership` model:

```python
player_role = models.CharField(
    max_length=50,
    blank=True,
    default='',
    help_text="In-game tactical role (e.g., Duelist, IGL, AWPer). Game-specific.",
    verbose_name="In-Game Role"
)
```

**Backwards Compatibility**: 
- Existing memberships will have empty `player_role` (blank=True, default='')
- Templates and views handle empty player roles gracefully
- No data migration required

## Best Practices

1. **Always validate player roles** against the team's game before saving
2. **Only assign player roles to Players and Substitutes**
3. **For eFootball and FC 26**, don't show player role selection
4. **Display both roles** when showing team rosters for clarity
5. **Use helper functions** instead of direct field access for validation
6. **Cache role lists** in forms to avoid repeated lookups

## Future Enhancements

- Role-based statistics and analytics
- Role-specific performance metrics
- Auto-suggest roles based on player history
- Role preference system for substitutes
- Multi-role support for flex players
- Role history tracking

## Support

For questions or issues with the dual-role system:
- See `apps/teams/dual_role_system.py` for utility functions
- Check `apps/teams/game_config.py` for game-specific configurations
- Review `apps/teams/models/_legacy.py` for model methods
