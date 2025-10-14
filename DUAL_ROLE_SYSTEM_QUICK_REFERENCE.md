# Dual-Role System - Quick Reference

## Quick Start

```python
# 1. Import what you need
from apps.teams.models import Team, TeamMembership
from apps.teams.dual_role_system import get_player_roles_for_game, validate_roster_composition

# 2. Create a team with a game
team = Team.objects.create(
    name="Example Team",
    tag="EX",
    game="valorant",
    captain=user_profile
)

# 3. Add a member with both roles
membership = TeamMembership.objects.create(
    team=team,
    profile=another_user_profile,
    role=TeamMembership.Role.PLAYER,  # Organizational role
    player_role='Duelist',  # In-game tactical role
    status=TeamMembership.Status.ACTIVE
)

# 4. Display the member's role
print(membership.display_full_role)  # Output: "Player (Duelist)"
```

## Common Tasks

### Get Available Roles for a Game

```python
from apps.teams.dual_role_system import get_player_roles_for_game

roles = get_player_roles_for_game('valorant')
# Returns: [
#     {'value': 'Duelist', 'label': 'Duelist', 'description': 'Entry fragger...'},
#     {'value': 'Controller', 'label': 'Controller', 'description': '...'},
#     ...
# ]
```

### Check if Game Supports Player Roles

```python
from apps.teams.dual_role_system import game_supports_player_roles

if game_supports_player_roles('valorant'):
    # Show player role selector
    pass

if not game_supports_player_roles('efootball'):
    # Don't show role selector for eFootball
    pass
```

### Validate a Player Role

```python
from apps.teams.dual_role_system import validate_player_role

is_valid, error = validate_player_role('valorant', 'Duelist')
if is_valid:
    membership.player_role = 'Duelist'
    membership.save()
else:
    print(f"Error: {error}")
```

### Set Player Role with Validation

```python
# Using the model method (recommended)
membership.set_player_role('Controller')  # Validates automatically
membership.save()

# Or manually
from django.core.exceptions import ValidationError
try:
    membership.set_player_role('InvalidRole')
    membership.save()
except ValidationError as e:
    print(f"Validation error: {e}")
```

### Format Roster for Display

```python
from apps.teams.dual_role_system import format_roster_for_display

roster_data = format_roster_for_display(team)
# Returns list of dicts with formatted role info
for member in roster_data:
    print(f"{member['username']}: {member['display_role']}")
```

### Get Roster Organized by Roles

```python
from apps.teams.dual_role_system import get_roster_by_roles

roster_by_role = get_roster_by_roles(team)
# Returns: {
#     'Duelist': [membership1, membership2],
#     'Controller': [membership3],
#     'Unassigned': [membership4]
# }

for role, members in roster_by_role.items():
    print(f"\n{role}:")
    for member in members:
        print(f"  - {member.profile.user.username}")
```

### Validate Roster Composition

```python
from apps.teams.dual_role_system import validate_roster_composition

is_valid, errors = validate_roster_composition(team)
if not is_valid:
    for error in errors:
        print(f"ERROR: {error}")
```

## Template Usage

### Load the Template Tags

```django
{% load dual_role_tags %}
```

### Display Full Role

```django
<!-- Simple display -->
{{ membership|display_full_role }}

<!-- With fallback -->
{{ membership|display_full_role|default:"No role assigned" }}
```

### Role Badge with Color

```django
{% role_badge membership.player_role team.game %}
```

### Conditional Role Selection

```django
{% if team.game|supports_player_roles %}
    <select name="player_role">
        <option value="">Select a role</option>
        {% for role in team.game|get_player_roles %}
            <option value="{{ role.value }}">
                {{ role.label }} - {{ role.description }}
            </option>
        {% endfor %}
    </select>
{% else %}
    <!-- eFootball/FC 26 don't need role selection -->
    <p>This game doesn't use tactical roles.</p>
{% endif %}
```

### Display Roster by Roles

```django
{% get_roster_by_roles team as roster_by_role %}

{% for role, members in roster_by_role.items %}
    <div class="role-group">
        <h3>{{ role }}</h3>
        <ul>
            {% for member in members %}
                <li>
                    {{ member.profile.user.username }}
                    <span class="badge {{ member.player_role|role_badge_color:team.game }}">
                        {{ member.player_role }}
                    </span>
                </li>
            {% endfor %}
        </ul>
    </div>
{% endfor %}
```

### Check if Member Can Have Player Role

```django
{% if membership|can_have_player_role %}
    <!-- Show role selector for Players and Subs -->
    <select name="player_role">...</select>
{% else %}
    <!-- Captain, Manager, Coach don't have player roles -->
    <p>{{ membership.role }} doesn't need a player role</p>
{% endif %}
```

## API Usage

### Serialize Member with Roles

```python
from apps.teams.dual_role_system import serialize_member_with_roles

member_data = serialize_member_with_roles(membership)

return JsonResponse({
    'success': True,
    'member': member_data
})
```

### API Endpoint Example

```python
from django.http import JsonResponse
from apps.teams.dual_role_system import get_player_roles_for_game

def get_roles_for_game(request, game_code):
    """API endpoint to get available roles for a game."""
    try:
        roles = get_player_roles_for_game(game_code)
        return JsonResponse({
            'success': True,
            'game': game_code,
            'roles': roles
        })
    except KeyError:
        return JsonResponse({
            'success': False,
            'error': f'Unknown game: {game_code}'
        }, status=400)
```

## Form Usage

### Dynamic Role Choices

```python
from django import forms
from apps.teams.dual_role_system import get_player_roles_for_game, game_supports_player_roles

class TeamMemberForm(forms.ModelForm):
    class Meta:
        model = TeamMembership
        fields = ['profile', 'role', 'player_role']
    
    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
        
        # Dynamically set player role choices based on game
        if team and team.game and game_supports_player_roles(team.game):
            roles = get_player_roles_for_game(team.game)
            self.fields['player_role'].widget = forms.Select(
                choices=[('', '---')] + [(r['value'], r['label']) for r in roles]
            )
            self.fields['player_role'].help_text = 'Select tactical role for this player'
        else:
            # Hide player_role field if game doesn't support it
            self.fields['player_role'].widget = forms.HiddenInput()
            self.fields['player_role'].required = False
```

## Game-Specific Role Lists

### VALORANT
`Duelist, Controller, Initiator, Sentinel, IGL, Flex`

### CS2
`IGL, Entry Fragger, AWPer, Lurker, Support, Rifler`

### Dota 2 (Unique Roles Required)
`Position 1 (Carry), Position 2 (Mid), Position 3 (Offlane), Position 4 (Soft Support), Position 5 (Hard Support)`

### MLBB
`Gold Laner, EXP Laner, Mid Laner, Jungler, Roamer`

### PUBG Mobile
`IGL/Shot Caller, Assaulter/Fragger, Support, Sniper/Scout`

### Free Fire
`Rusher, Flanker, Support, Shot Caller`

### eFootball & FC 26
*No tactical roles needed*

### CODM
`IGL, Slayer, Anchor, Support, Objective Player`

## Testing

```python
# Test dual-role system
from apps.teams.models import Team, TeamMembership
from apps.teams.dual_role_system import *

# Setup
team = Team.objects.create(name="Test Team", tag="TEST", game="valorant")
membership = TeamMembership.objects.create(
    team=team,
    profile=user_profile,
    role=TeamMembership.Role.PLAYER
)

# Test role assignment
membership.set_player_role('Duelist')
assert membership.player_role == 'Duelist'
assert membership.display_full_role == 'Player (Duelist)'

# Test validation
is_valid, _ = validate_player_role('valorant', 'Duelist')
assert is_valid == True

is_valid, error = validate_player_role('valorant', 'InvalidRole')
assert is_valid == False
assert 'not valid' in error

# Test game support
assert game_supports_player_roles('valorant') == True
assert game_supports_player_roles('efootball') == False

# Test roster validation
is_valid, errors = validate_roster_composition(team)
print(f"Roster valid: {is_valid}, Errors: {errors}")
```

## Common Patterns

### Registration Form with Role Selection

```python
# In views.py
def team_registration(request):
    if request.method == 'POST':
        team_form = TeamForm(request.POST)
        if team_form.is_valid():
            team = team_form.save()
            
            # Create roster with roles
            roster_data = request.POST.getlist('roster')
            for data in roster_data:
                profile_id = data['profile_id']
                player_role = data['player_role']  # In-game role
                
                TeamMembership.objects.create(
                    team=team,
                    profile_id=profile_id,
                    role=TeamMembership.Role.PLAYER,
                    player_role=player_role  # Set in-game role
                )
```

### Update Member Role

```python
def update_member_role(request, team_slug, membership_id):
    membership = get_object_or_404(TeamMembership, id=membership_id)
    
    new_player_role = request.POST.get('player_role')
    
    try:
        membership.set_player_role(new_player_role)  # Validates automatically
        membership.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Role updated',
            'display_role': membership.display_full_role
        })
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
```

## Summary

**Key Points:**
1. Always use `membership.set_player_role()` for validation
2. Check `game_supports_player_roles()` before showing role selectors
3. Use `display_full_role` property for user-facing displays
4. Only Players and Substitutes can have player roles
5. eFootball and FC 26 don't need player roles
6. Dota 2 requires unique position roles

**For Full Documentation:**
See `DUAL_ROLE_SYSTEM_DOCUMENTATION.md`
