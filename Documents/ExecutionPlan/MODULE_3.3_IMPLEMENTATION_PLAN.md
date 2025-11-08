# Module 3.3: Team Management - Implementation Plan

**Status**: Planning Phase (Not Yet Implemented)  
**Date**: November 8, 2025  
**Dependencies**: Module 1.1 (Models), Module 2.1 (Services), Module 2.3 (WebSocket)

---

## 1. Overview

Module 3.3 implements comprehensive team management features for tournaments supporting team participation. This includes team creation, roster management, member invitations, captain transfers, and team dissolution workflows.

### Source Documents

- **Primary**: `Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md`
- **Supporting**:
  - `Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md` (Team/Membership models)
  - `Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md` (Service layer patterns)
  - `Documents/Planning/PART_2.3_REALTIME_SECURITY.md` (Team WebSocket channels)

---

## 2. Entities & Relationships

### Models (Already Exist - Extend Functionality)

#### Team Model (`apps/teams/models/team.py`)
```python
class Team(models.Model):
    name = CharField(max_length=100, unique=True)
    slug = SlugField(unique=True)
    captain = ForeignKey(User, related_name='captained_teams')
    game = ForeignKey(Game, related_name='teams')
    logo = ImageField(upload_to='team_logos/')
    description = TextField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    
    # Already implemented - extend with:
    # - Roster lock mechanism
    # - Captain transfer workflow
    # - Team dissolution rules
```

#### TeamMembership Model (`apps/teams/models/membership.py`)
```python
class TeamMembership(models.Model):
    team = ForeignKey(Team, related_name='memberships')
    user = ForeignKey(User, related_name='team_memberships')
    role = CharField(max_length=20, choices=ROLE_CHOICES)  # captain, player, substitute
    joined_at = DateTimeField(auto_now_add=True)
    is_active = BooleanField(default=True)
    
    class Meta:
        unique_together = ('team', 'user')
    
    # Already implemented - extend with:
    # - Role transition workflows
    # - Inactive/removal timestamps
```

#### TeamInvite Model (`apps/teams/models/invite.py`)
```python
class TeamInvite(models.Model):
    team = ForeignKey(Team, related_name='invites')
    invited_user = ForeignKey(User, related_name='team_invites')
    invited_by = ForeignKey(User, related_name='sent_team_invites')
    status = CharField(max_length=20, choices=STATUS_CHOICES)  # pending, accepted, declined, expired
    message = TextField(blank=True)
    expires_at = DateTimeField()
    created_at = DateTimeField(auto_now_add=True)
    responded_at = DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('team', 'invited_user', 'status')  # Prevent duplicate pending invites
    
    # Already implemented - extend with:
    # - Auto-expiration after 72 hours
    # - Notification integration
```

### Anchors Referenced

- `PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-creation` - Team creation workflow
- `PART_4.5_TEAM_MANAGEMENT_FLOW.md#roster-management` - Adding/removing members
- `PART_4.5_TEAM_MANAGEMENT_FLOW.md#invitations` - Invite system
- `PART_4.5_TEAM_MANAGEMENT_FLOW.md#captain-transfer` - Captain handoff
- `PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-dissolution` - Disbanding teams
- `PART_3.1_DATABASE_DESIGN_ERD.md#team-schema` - Data model
- `PART_2.3_REALTIME_SECURITY.md#team-channels` - WebSocket channels

---

## 3. Proposed Endpoints

### Base URL
```
/api/teams/
```

### Endpoint Specifications

#### 1. Create Team
**POST** `/api/teams/`

**Auth**: Authenticated user

**Body**:
```json
{
  "name": "Phoenix Squad",
  "game_id": 5,
  "description": "Competitive Valorant team",
  "logo": "<file upload>"
}
```

**Response** (201):
```json
{
  "id": 42,
  "name": "Phoenix Squad",
  "slug": "phoenix-squad",
  "captain": {
    "id": 10,
    "username": "player1"
  },
  "game": "Valorant",
  "members_count": 1,
  "created_at": "2025-11-08T15:00:00Z"
}
```

**Permissions**: Any authenticated user (becomes captain automatically)

---

#### 2. Get Team Details
**GET** `/api/teams/{team_id}/`

**Auth**: Public (read-only) OR Team member (full details)

**Response** (200):
```json
{
  "id": 42,
  "name": "Phoenix Squad",
  "slug": "phoenix-squad",
  "captain": {...},
  "game": "Valorant",
  "description": "Competitive Valorant team",
  "logo": "/media/team_logos/phoenix.jpg",
  "members": [
    {"id": 10, "username": "player1", "role": "captain"},
    {"id": 11, "username": "player2", "role": "player"}
  ],
  "is_active": true,
  "created_at": "2025-11-08T15:00:00Z"
}
```

**Permissions**: Public read access

---

#### 3. Update Team
**PATCH** `/api/teams/{team_id}/`

**Auth**: Team captain only

**Body** (partial):
```json
{
  "description": "Updated description",
  "logo": "<file upload>"
}
```

**Response** (200): Updated team object

**Permissions**: Team captain

---

#### 4. Invite Player
**POST** `/api/teams/{team_id}/invite/`

**Auth**: Team captain

**Body**:
```json
{
  "invited_user_id": 15,
  "message": "Join us for the upcoming tournament!"
}
```

**Response** (201):
```json
{
  "id": 8,
  "team_id": 42,
  "invited_user": {...},
  "status": "pending",
  "expires_at": "2025-11-11T15:00:00Z"
}
```

**Permissions**: Team captain

---

#### 5. Respond to Invite
**POST** `/api/teams/invites/{invite_id}/respond/`

**Auth**: Invited user only

**Body**:
```json
{
  "action": "accept"  // or "decline"
}
```

**Response** (200):
```json
{
  "message": "Invite accepted. You are now a member of Phoenix Squad.",
  "membership": {...}
}
```

**Permissions**: Invited user

---

#### 6. Remove Member
**DELETE** `/api/teams/{team_id}/members/{user_id}/`

**Auth**: Team captain (cannot remove self)

**Response** (204): No content

**Permissions**: Team captain

---

#### 7. Transfer Captain
**POST** `/api/teams/{team_id}/transfer-captain/`

**Auth**: Current captain only

**Body**:
```json
{
  "new_captain_id": 11
}
```

**Response** (200):
```json
{
  "message": "Captain role transferred successfully",
  "team": {...},
  "new_captain": {...}
}
```

**Permissions**: Current captain

---

#### 8. Leave Team
**POST** `/api/teams/{team_id}/leave/`

**Auth**: Team member (not captain)

**Response** (200):
```json
{
  "message": "You have left Phoenix Squad"
}
```

**Permissions**: Team member (captain must transfer or disband)

---

#### 9. Disband Team
**DELETE** `/api/teams/{team_id}/`

**Auth**: Team captain only

**Response** (204): No content

**Business Rules**:
- Cannot disband if team has active tournament registrations
- All members receive WebSocket notification
- Team marked `is_active=False` (soft delete)

**Permissions**: Team captain

---

## 4. Service Methods

### TeamService (`apps/teams/services/team_service.py`)

Create new service file with methods:

#### Core Operations
```python
class TeamService:
    @staticmethod
    def create_team(name: str, captain: User, game: Game, **kwargs) -> Team:
        """
        Create team with captain as first member.
        
        - Validates name uniqueness
        - Generates slug
        - Creates TeamMembership for captain (role='captain')
        - Triggers audit log (Module 2.4)
        - Broadcasts team_created event (Module 2.3)
        """
    
    @staticmethod
    def invite_player(team: Team, invited_user: User, invited_by: User, message: str = '') -> TeamInvite:
        """
        Send team invitation.
        
        - Validates team member count < game.default_team_size
        - Checks if user already invited (pending) - raises ValidationError
        - Sets expires_at = now() + 72 hours
        - Triggers notification (Module 2.5)
        - Returns TeamInvite object
        """
    
    @staticmethod
    def accept_invite(invite: TeamInvite, user: User) -> TeamMembership:
        """
        Accept invitation and join team.
        
        - Validates invite not expired
        - Validates team not full
        - Creates TeamMembership (role='player')
        - Updates invite status='accepted', responded_at=now()
        - Triggers audit log
        - Broadcasts member_joined event
        - Returns TeamMembership
        """
    
    @staticmethod
    def decline_invite(invite: TeamInvite, user: User):
        """
        Decline invitation.
        
        - Updates invite status='declined', responded_at=now()
        - Triggers audit log
        - No WebSocket event (silent decline)
        """
    
    @staticmethod
    def remove_member(team: Team, user: User, removed_by: User):
        """
        Remove team member.
        
        - Validates removed_by is captain
        - Validates user != captain
        - Updates TeamMembership is_active=False
        - Triggers audit log
        - Broadcasts member_removed event
        - Notifies removed user
        """
    
    @staticmethod
    def transfer_captain(team: Team, new_captain: User, current_captain: User):
        """
        Transfer captain role.
        
        - Validates new_captain is team member
        - Updates team.captain = new_captain
        - Updates new_captain membership role='captain'
        - Updates current_captain membership role='player'
        - Triggers audit log
        - Broadcasts captain_transferred event
        """
    
    @staticmethod
    def disband_team(team: Team, user: User):
        """
        Disband team (soft delete).
        
        - Validates user is captain
        - Validates no active tournament registrations
        - Updates team.is_active=False
        - Updates all memberships is_active=False
        - Triggers audit log
        - Broadcasts team_disbanded event
        - Notifies all members
        """
```

---

## 5. Tests (Acceptance Matrix)

### Test File: `tests/test_team_api.py` (~800 lines)

#### TeamCreationTestCase (5 tests)
- `test_create_team_success` - Valid team creation
- `test_create_team_duplicate_name` - Name uniqueness validation
- `test_create_team_invalid_game` - Game FK validation
- `test_create_team_unauthenticated` - Auth requirement
- `test_creator_becomes_captain` - Auto-captain assignment

#### TeamInviteTestCase (8 tests)
- `test_invite_player_success` - Valid invitation
- `test_invite_player_not_captain` - Permission check
- `test_invite_duplicate_pending` - Prevent duplicate invites
- `test_invite_team_full` - Roster size limit
- `test_accept_invite_success` - Invite acceptance
- `test_accept_expired_invite` - Expiration validation
- `test_decline_invite_success` - Invite decline
- `test_cannot_accept_others_invite` - Permission check

#### TeamMembershipTestCase (7 tests)
- `test_remove_member_success` - Captain removes player
- `test_remove_member_not_captain` - Permission check
- `test_cannot_remove_captain` - Business rule
- `test_leave_team_success` - Player leaves
- `test_captain_cannot_leave` - Must transfer first
- `test_transfer_captain_success` - Captain transfer
- `test_transfer_to_non_member` - Validation

#### TeamDisbandTestCase (4 tests)
- `test_disband_team_success` - Soft delete
- `test_disband_not_captain` - Permission check
- `test_cannot_disband_with_active_registrations` - Business rule
- `test_all_members_notified` - WebSocket broadcasts

#### TeamUpdateTestCase (3 tests)
- `test_update_team_description` - Captain can update
- `test_update_team_not_captain` - Permission check
- `test_update_team_logo` - File upload

**Total**: 27 tests

### Integration Tests: `tests/integration/test_team_websocket_events.py` (~300 lines)

- `test_team_created_event` - WebSocket broadcast on creation
- `test_member_joined_event` - Broadcast when user accepts invite
- `test_member_removed_event` - Broadcast on removal
- `test_captain_transferred_event` - Broadcast on captain change
- `test_team_disbanded_event` - Broadcast on disbanding

**Total**: 5 integration tests

---

## 6. Traceability Entries

### MAP.md Addition

```markdown
| Module 3.3 | Team Management | `apps/teams/services/team_service.py`<br>`apps/teams/api/views.py`<br>`apps/teams/api/serializers.py` | `tests/test_team_api.py` (27)<br>`tests/integration/test_team_websocket_events.py` (5) | PART_4.5 (Team Flow)<br>PART_3.1 (Team Models)<br>ADR-009 (Service Layer) | Complete (Pending Review) |
```

### trace.yml Population

```yaml
phase_3:
  module_3_3:
    name: "Team Management"
    status: "complete"
    implements:
      - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-creation
      - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#roster-management
      - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#invitations
      - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#captain-transfer
      - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-dissolution
      - Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md#team-schema
      - Documents/Planning/PART_2.3_REALTIME_SECURITY.md#team-channels
      - Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md#service-layer
      - Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#adr-009
      - Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md#api-design
    files:
      - apps/teams/services/team_service.py  # New service file (9 methods)
      - apps/teams/api/views.py  # TeamViewSet with 9 endpoints
      - apps/teams/api/serializers.py  # 5 serializers (Team, Invite, Member, CaptainTransfer, Disband)
      - apps/teams/api/urls.py  # Router registration
      - apps/teams/realtime/consumers.py  # 5 team event handlers (extend existing)
    tests:
      - tests/test_team_api.py  # 27 API tests
      - tests/integration/test_team_websocket_events.py  # 5 WebSocket integration tests
```

---

## 7. Implementation Checklist

### Phase 1: Service Layer (2-3 hours)
- [ ] Create `apps/teams/services/team_service.py`
- [ ] Implement 9 service methods (create_team, invite_player, accept_invite, decline_invite, remove_member, transfer_captain, disband_team, leave_team, update_team)
- [ ] Add validation logic (roster size, permissions, business rules)
- [ ] Integrate Module 2.4 audit logging
- [ ] Add docstrings with traceability comments

### Phase 2: API Layer (3-4 hours)
- [ ] Create/extend `apps/teams/api/serializers.py` (5 serializers)
- [ ] Create/extend `apps/teams/api/views.py` (TeamViewSet with 9 endpoints)
- [ ] Add permission classes (IsTeamCaptain, IsTeamMember, IsInvitedUser)
- [ ] Register router in `apps/teams/api/urls.py`

### Phase 3: WebSocket Integration (1-2 hours)
- [ ] Extend `apps/teams/realtime/consumers.py` with 5 event handlers
- [ ] Add team channel subscription logic (`team_{team_id}`)
- [ ] Test event broadcasts (team_created, member_joined, member_removed, captain_transferred, team_disbanded)

### Phase 4: Testing (4-5 hours)
- [ ] Write 27 API tests in `tests/test_team_api.py`
- [ ] Write 5 WebSocket integration tests
- [ ] Achieve ≥80% coverage for team service + API
- [ ] Validate all business rules (roster limits, permission checks, expiration logic)

### Phase 5: Documentation (1 hour)
- [ ] Update MAP.md with Module 3.3 row
- [ ] Populate trace.yml module_3_3 section
- [ ] Create MODULE_3.3_COMPLETION_STATUS.md
- [ ] Add endpoint quickstart (cURL examples + WebSocket payloads)

**Estimated Total**: 11-15 hours

---

## 8. Known Dependencies & Blockers

### Prerequisites
- ✅ Module 1.1: Team/TeamMembership/TeamInvite models exist
- ✅ Module 2.1: Service layer patterns established
- ✅ Module 2.3: WebSocket infrastructure operational
- ✅ Module 2.4: Audit logging system available
- ⏳ Module 2.5: Notification system (will integrate if available)

### Potential Blockers
- **Team-Tournament Integration**: Need to validate team roster locks when registered for tournaments (may require coordination with Module 4.x bracket generation)
- **Game-Specific Roster Sizes**: Currently using `Game.default_team_size` - may need per-tournament overrides
- **Captain Transfer Edge Cases**: What if captain is only member? (Solution: Auto-disband if last member leaves)

---

## 9. Success Criteria

- [ ] All 32 tests passing (27 API + 5 WebSocket)
- [ ] Coverage ≥80% for team service and API
- [ ] All 9 endpoints documented with cURL examples
- [ ] WebSocket events confirmed broadcasting to team channels
- [ ] traceability validation passes (`verify_trace.py` Module 3.3)
- [ ] Manual smoke test: Create team → Invite player → Accept → Transfer captain → Disband

---

## 10. Follow-Up Enhancements (Deferred)

### P1: Security Enhancements
- Rate limiting on invite endpoint (prevent spam invites)
- Blacklist/whitelist for team invitations
- Captain handoff cooldown (prevent rapid captain churn)

### P2: Feature Enhancements
- Team application system (reverse invites - players apply to join)
- Team rankings/statistics integration
- Team chat/discussion boards
- Team achievements/badges

### P3: Admin Features
- Admin team management dashboard
- Bulk invite expiration cleanup
- Inactive team pruning (after 90 days with no activity)

---

**Module Status**: ⏳ Planning Complete - Awaiting Implementation Approval  
**Next Step**: Obtain user approval, then begin Phase 1 (Service Layer)  
**Estimated Completion**: 2-3 days (accounting for testing + review cycles)
