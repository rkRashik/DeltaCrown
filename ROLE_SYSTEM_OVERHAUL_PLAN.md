# Team App Role & Permission System Overhaul

## Executive Summary

This document outlines the complete overhaul of the Team App's role and permission system, transitioning from a simplistic "Captain-led" model to a professional, hierarchical system that mirrors modern esports organization structures.

## Current System Analysis

### Existing Roles
- **CAPTAIN**: Team creator with full admin + in-game leadership
- **MANAGER**: Limited administrative capabilities
- **PLAYER**: Active roster member
- **SUB**: Substitute player

### Key Limitations
1. **Overloaded Captain Role**: Merges administrative and tactical leadership
2. **Inflexibility**: Best IGL may not be best administrator
3. **Outdated Model**: Doesn't reflect professional esports structure

## New Professional Role Hierarchy

### Role Structure

| Role | Count | Assignment | Key Permissions |
|------|-------|------------|-----------------|
| **OWNER** | 1 | Team creator | Root admin, full control, can transfer ownership, delete team |
| **MANAGER** | Multiple | Appointed by Owner | Roster management, tournament registration, team profile editing |
| **COACH** | Multiple | Appointed by Owner/Manager | View-only access, strategic planning tools |
| **CAPTAIN** (Title) | 1 | Special badge for Player/Sub | In-game leadership indicator, minor match permissions |
| **PLAYER** | Multiple | Active roster | Team member, can view and leave |
| **SUBSTITUTE** | Multiple | Backup roster | Same as Player |

### Permission Matrix

| Action | Owner | Manager | Coach | Captain* | Player | Sub |
|--------|-------|---------|-------|----------|--------|-----|
| Delete Team | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Transfer Ownership | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Assign/Remove Managers | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Assign/Remove Coach | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Assign Captain Title | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Edit Team Profile | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Invite Members | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Kick Members | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Register for Tournaments | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| View Roster | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Leave Team | ❌** | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ready Up in Match | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |

*Captain is a title, not a role. Permissions based on underlying role (Player/Sub)
**Owner must transfer ownership before leaving

## Implementation Phases

### Phase 1: Backend Foundation (Priority: CRITICAL)

#### 1.1 Database Schema Updates

**New Fields for TeamMembership Model:**
```python
class TeamMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Team Owner"
        MANAGER = "MANAGER", "Manager"
        COACH = "COACH", "Coach"
        PLAYER = "PLAYER", "Player"
        SUBSTITUTE = "SUBSTITUTE", "Substitute"
    
    # Existing fields
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PLAYER)
    
    # NEW: Captain indicator (boolean flag)
    is_captain = models.BooleanField(
        default=False,
        help_text="In-game leader badge (can only be true for PLAYER or SUBSTITUTE)"
    )
    
    # NEW: Team-level permissions cache (for performance)
    can_manage_roster = models.BooleanField(default=False)
    can_edit_team = models.BooleanField(default=False)
    can_register_tournaments = models.BooleanField(default=False)
```

**Database Constraints:**
- Only ONE OWNER per team (unique constraint)
- Only ONE is_captain=True per team (unique constraint)
- is_captain can only be True for PLAYER or SUBSTITUTE roles

#### 1.2 Data Migration Script

**Migration Strategy:**
```python
# Migration: 0XXX_role_system_overhaul.py

def migrate_captain_to_owner(apps, schema_editor):
    """
    Migrate all existing CAPTAIN roles to OWNER
    """
    TeamMembership = apps.get_model('teams', 'TeamMembership')
    
    # Find all captain memberships
    captains = TeamMembership.objects.filter(role='CAPTAIN')
    
    for captain in captains:
        # Update to OWNER
        captain.role = 'OWNER'
        captain.can_manage_roster = True
        captain.can_edit_team = True
        captain.can_register_tournaments = True
        captain.save()
    
    print(f"Migrated {captains.count()} captains to owners")
```

#### 1.3 Permission System Implementation

**New Permission Checker Utility:**
```python
# apps/teams/permissions.py

class TeamPermissions:
    """Centralized permission checking for team operations"""
    
    @staticmethod
    def can_delete_team(membership):
        """Only OWNER can delete team"""
        return membership.role == TeamMembership.Role.OWNER
    
    @staticmethod
    def can_transfer_ownership(membership):
        """Only OWNER can transfer ownership"""
        return membership.role == TeamMembership.Role.OWNER
    
    @staticmethod
    def can_manage_roster(membership):
        """OWNER and MANAGER can manage roster"""
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]
    
    @staticmethod
    def can_edit_team_profile(membership):
        """OWNER and MANAGER can edit profile"""
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]
    
    @staticmethod
    def can_assign_captain_title(membership):
        """OWNER and MANAGER can assign captain title"""
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]
    
    @staticmethod
    def can_register_tournaments(membership):
        """OWNER and MANAGER can register for tournaments"""
        return membership.role in [
            TeamMembership.Role.OWNER,
            TeamMembership.Role.MANAGER
        ]
```

### Phase 2: API & Backend Logic (Priority: HIGH)

#### 2.1 Update All View Functions

**Example: Team Profile Editing**
```python
@login_required
def edit_team_profile(request, slug):
    team = get_object_or_404(Team, slug=slug)
    membership = get_object_or_404(
        TeamMembership, 
        team=team, 
        profile=request.user.profile
    )
    
    # Permission check
    if not TeamPermissions.can_edit_team_profile(membership):
        return JsonResponse(
            {"error": "Only team Owner or Manager can edit profile"}, 
            status=403
        )
    
    # Proceed with edit...
```

#### 2.2 New API Endpoints

**Ownership Transfer:**
```python
@login_required
@require_POST
def transfer_ownership(request, slug):
    """Transfer team ownership to another member"""
    team = get_object_or_404(Team, slug=slug)
    current_owner = get_object_or_404(
        TeamMembership,
        team=team,
        profile=request.user.profile,
        role=TeamMembership.Role.OWNER
    )
    
    data = json.loads(request.body)
    new_owner_profile_id = data.get('new_owner_id')
    
    # Validation and transfer logic
    # ...
```

**Captain Title Assignment:**
```python
@login_required
@require_POST
def assign_captain_title(request, slug):
    """Assign or remove captain title"""
    team = get_object_or_404(Team, slug=slug)
    membership = get_object_or_404(
        TeamMembership,
        team=team,
        profile=request.user.profile
    )
    
    if not TeamPermissions.can_assign_captain_title(membership):
        return JsonResponse({"error": "Permission denied"}, status=403)
    
    data = json.loads(request.body)
    target_profile_id = data.get('profile_id')
    
    # Logic to set is_captain flag
    # ...
```

### Phase 3: Frontend UI/UX (Priority: HIGH)

#### 3.1 Roster Card Components

**Public Roster Card Specification:**
```javascript
// PublicRosterCard.jsx

const PublicRosterCard = ({ member }) => {
  // Hide administrative roles from public view
  if (['OWNER', 'MANAGER', 'COACH'].includes(member.teamRole)) {
    return null;
  }
  
  return (
    <div className="roster-card public">
      <img src={member.avatarUrl} alt={member.inGameName} />
      <div className="player-info">
        {member.isCaptain && <span className="captain-badge">⭐</span>}
        <h3>{member.inGameName}</h3>
        <p className="in-game-role">{member.inGameRole || 'No role assigned'}</p>
        <span className="status-tag">{member.teamRole}</span>
      </div>
    </div>
  );
};
```

**Team Member Roster Card Specification:**
```javascript
// TeamMemberRosterCard.jsx

const TeamMemberRosterCard = ({ member, viewerPermissions }) => {
  return (
    <div className="roster-card team-view">
      <img src={member.avatarUrl} alt={member.displayName} />
      <div className="player-info">
        {member.isCaptain && <span className="captain-badge">⭐</span>}
        <h3>{member.displayName}</h3>
        <p className="team-role"><strong>{member.teamRole}</strong></p>
        {member.inGameRole && (
          <p className="in-game-role">In-Game: {member.inGameRole}</p>
        )}
      </div>
      
      {viewerPermissions.canManageRoster && (
        <div className="action-buttons">
          <button onClick={() => openRoleManager(member)}>
            Change Role
          </button>
          {member.teamRole !== 'OWNER' && (
            <button onClick={() => kickMember(member)}>
              Remove
            </button>
          )}
        </div>
      )}
    </div>
  );
};
```

#### 3.2 Team Management Dashboard

**Role Assignment Interface:**
```javascript
// RoleManagementPanel.jsx

const RoleManagementPanel = ({ team, currentUserRole }) => {
  const canAssignRoles = ['OWNER', 'MANAGER'].includes(currentUserRole);
  
  return (
    <div className="role-management-panel">
      <h2>Team Hierarchy</h2>
      
      {/* Owner Section */}
      <div className="role-section owner">
        <h3>👑 Team Owner</h3>
        <MemberCard member={team.owner} />
        {currentUserRole === 'OWNER' && (
          <button onClick={openOwnershipTransfer}>
            Transfer Ownership
          </button>
        )}
      </div>
      
      {/* Managers Section */}
      <div className="role-section managers">
        <h3>📋 Managers</h3>
        {team.managers.map(manager => (
          <MemberCard 
            key={manager.id} 
            member={manager}
            actions={canAssignRoles && (
              <button onClick={() => removeRole(manager, 'MANAGER')}>
                Remove Manager
              </button>
            )}
          />
        ))}
        {canAssignRoles && (
          <button onClick={() => openAddManager()}>
            + Add Manager
          </button>
        )}
      </div>
      
      {/* Captain Section */}
      <div className="role-section captain">
        <h3>⭐ In-Game Captain</h3>
        {team.captain ? (
          <MemberCard 
            member={team.captain}
            actions={canAssignRoles && (
              <button onClick={() => removeCaptainTitle()}>
                Remove Title
              </button>
            )}
          />
        ) : (
          <p>No captain assigned</p>
        )}
        {canAssignRoles && (
          <button onClick={() => openAssignCaptain()}>
            Assign Captain Title
          </button>
        )}
      </div>
      
      {/* Players Section */}
      <div className="role-section players">
        <h3>🎮 Active Roster</h3>
        {team.players.map(player => (
          <MemberCard key={player.id} member={player} />
        ))}
      </div>
    </div>
  );
};
```

#### 3.3 Conditional Rendering Logic

**Permission-Based Button Display:**
```javascript
// TeamActions.jsx

const TeamActions = ({ team, userMembership }) => {
  const permissions = {
    canEditProfile: ['OWNER', 'MANAGER'].includes(userMembership.role),
    canManageRoster: ['OWNER', 'MANAGER'].includes(userMembership.role),
    canRegisterTournaments: ['OWNER', 'MANAGER'].includes(userMembership.role),
    canDeleteTeam: userMembership.role === 'OWNER',
    canLeaveTeam: userMembership.role !== 'OWNER'
  };
  
  return (
    <div className="team-actions">
      {permissions.canEditProfile && (
        <button onClick={editTeamProfile}>
          <EditIcon /> Edit Team
        </button>
      )}
      
      {permissions.canManageRoster && (
        <button onClick={openInviteMember}>
          <UserPlusIcon /> Invite Member
        </button>
      )}
      
      {permissions.canRegisterTournaments && (
        <button onClick={registerForTournament}>
          <TrophyIcon /> Register for Tournament
        </button>
      )}
      
      {permissions.canDeleteTeam && (
        <button onClick={deleteTeam} className="danger">
          <TrashIcon /> Delete Team
        </button>
      )}
      
      {permissions.canLeaveTeam && (
        <button onClick={leaveTeam} className="warning">
          <LogoutIcon /> Leave Team
        </button>
      )}
    </div>
  );
};
```

### Phase 4: Enhanced API Responses (Priority: MEDIUM)

#### 4.1 Roster API Endpoint

```python
@api_view(['GET'])
def get_team_roster(request, slug):
    """
    Enhanced roster endpoint with viewer context
    """
    team = get_object_or_404(Team, slug=slug)
    
    # Check if viewer is a team member
    viewer_is_member = False
    viewer_permissions = {}
    
    if request.user.is_authenticated:
        try:
            membership = TeamMembership.objects.get(
                team=team,
                profile=request.user.profile
            )
            viewer_is_member = True
            viewer_permissions = {
                'can_edit_profile': TeamPermissions.can_edit_team_profile(membership),
                'can_manage_roster': TeamPermissions.can_manage_roster(membership),
                'can_delete_team': TeamPermissions.can_delete_team(membership),
                'role': membership.role
            }
        except TeamMembership.DoesNotExist:
            pass
    
    # Get roster
    memberships = team.memberships.filter(
        status=TeamMembership.Status.ACTIVE
    ).select_related('profile__user')
    
    roster_data = []
    for m in memberships:
        # Get game ID
        game_id = m.profile.get_game_id(team.game) if team.game else None
        
        member_data = {
            'id': m.id,
            'profile_id': m.profile.id,
            'display_name': m.profile.display_name or m.profile.user.username,
            'in_game_name': game_id or m.profile.user.username,
            'avatar_url': m.profile.avatar.url if m.profile.avatar else None,
            'team_role': m.role,
            'in_game_role': m.player_role,
            'is_captain': m.is_captain,
            'joined_at': m.joined_at.isoformat(),
            'game_id': game_id
        }
        
        roster_data.append(member_data)
    
    return Response({
        'team': {
            'name': team.name,
            'tag': team.tag,
            'slug': team.slug,
            'game': team.game
        },
        'viewer_is_member': viewer_is_member,
        'viewer_permissions': viewer_permissions,
        'roster': roster_data
    })
```

### Phase 5: Testing & Validation (Priority: HIGH)

#### 5.1 Test Cases

**Permission Tests:**
```python
# tests/test_team_permissions.py

def test_owner_can_delete_team():
    """Test that only owner can delete team"""
    owner_membership = create_team_membership(role='OWNER')
    assert TeamPermissions.can_delete_team(owner_membership) == True
    
    manager_membership = create_team_membership(role='MANAGER')
    assert TeamPermissions.can_delete_team(manager_membership) == False

def test_manager_cannot_transfer_ownership():
    """Test that managers cannot transfer ownership"""
    manager_membership = create_team_membership(role='MANAGER')
    assert TeamPermissions.can_transfer_ownership(manager_membership) == False

def test_only_one_captain_per_team():
    """Test captain uniqueness constraint"""
    team = create_team()
    player1 = create_membership(team=team, role='PLAYER', is_captain=True)
    
    with pytest.raises(ValidationError):
        player2 = create_membership(team=team, role='PLAYER', is_captain=True)
```

**Migration Tests:**
```python
# tests/test_role_migration.py

def test_captain_to_owner_migration():
    """Test that captains are properly migrated to owners"""
    # Create old-style captain
    old_captain = create_membership(role='CAPTAIN')
    
    # Run migration
    run_migration('0XXX_role_system_overhaul')
    
    # Verify
    updated = TeamMembership.objects.get(pk=old_captain.pk)
    assert updated.role == 'OWNER'
    assert updated.can_manage_roster == True
    assert updated.can_edit_team == True
```

### Phase 6: Documentation & User Onboarding (Priority: MEDIUM)

#### 6.1 User-Facing Documentation

**Help Text & Tooltips:**
- Owner: "Ultimate authority. Can delete team and transfer ownership."
- Manager: "Handles roster and tournaments. Cannot delete team."
- Coach: "Strategic guidance. View-only access to roster."
- Captain: "In-game leader. Special badge for team's tactical leader."

#### 6.2 Migration Announcement

**In-App Banner:**
```
🎉 Team System Upgrade!
We've enhanced our team management system! Your team's Captain has been 
upgraded to Team Owner with full administrative control. Learn more →
```

## Implementation Timeline

### Week 1: Backend Foundation
- [ ] Day 1-2: Database schema updates and migration script
- [ ] Day 3-4: Permission system implementation
- [ ] Day 5: Testing permission logic

### Week 2: API & Backend
- [ ] Day 1-2: Update all existing views with permission checks
- [ ] Day 3-4: Implement new API endpoints
- [ ] Day 5: API testing and validation

### Week 3: Frontend Development
- [ ] Day 1-2: Roster card components (public + team view)
- [ ] Day 3-4: Team management dashboard
- [ ] Day 5: Conditional rendering and permission-based UI

### Week 4: Integration & Testing
- [ ] Day 1-2: End-to-end testing
- [ ] Day 3: Bug fixes and refinements
- [ ] Day 4: Documentation and help content
- [ ] Day 5: Deployment preparation

## Rollback Plan

In case of critical issues:

1. **Database Rollback**: Revert migration, restore CAPTAIN role
2. **Code Rollback**: Deploy previous version from git tag
3. **Data Integrity**: Backup before migration, can restore if needed
4. **User Communication**: Clear announcement if rollback occurs

## Success Metrics

- [ ] Zero permission bypass incidents
- [ ] All existing teams successfully migrated
- [ ] User satisfaction score >4.5/5
- [ ] Admin task completion time reduced by 30%
- [ ] Zero data loss during migration

## Dependencies

- Django 4.2.24
- Current TeamMembership model
- User authentication system
- Frontend framework (React/Vue)
- API framework (Django REST Framework)

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Data loss during migration | HIGH | Full database backup, staged rollout |
| Permission bypass bugs | HIGH | Comprehensive testing, security audit |
| User confusion | MEDIUM | Clear documentation, in-app guides |
| Performance impact | LOW | Database indexing, caching strategy |

## Conclusion

This overhaul transforms the Team App from a basic captain-led system to a professional, flexible hierarchy that matches industry standards. The phased approach ensures stability while delivering significant value to users managing competitive esports teams.
