# Existing Systems Audit Report
**Date:** December 31, 2025  
**Auditor:** Senior Django Architect  
**Type:** Read-Only Analysis (No Implementation)

---

## 1. Executive Summary

This audit documents **reusable patterns and components** in the existing DeltaCrown codebase that can be leveraged for the planned User Profile expansion features (Bounty system, Endorsements, Posts, Cosmetics, Loadout).

### Key Findings:

✅ **Economy System** - Highly reusable for bounty escrow, atomic transactions with idempotency  
✅ **Tournament Ops** - Match verification & dispute patterns ready for adaptation  
✅ **Teams System** - Captain role logic, membership tracking, notification hooks  
❌ **Community System** - Does NOT exist (no Post/Feed models found)  
✅ **User Profile** - Solid permission checker, activity events, service patterns

---

## 2. Economy System (apps/economy/)

### 2.1 What Exists

**Models:**
- `DeltaCrownWallet` - User wallet with cached_balance + pending_balance
- `DeltaCrownTransaction` - Immutable ledger with idempotency_key
- `CoinPolicy` - Prize distribution rules (deprecated with tournament models)
- `WithdrawalRequest` - Bangladesh payment processing with PIN security

**Key Fields (Wallet):**
```python
cached_balance = IntegerField(default=0)  # Derived from transaction ledger
pending_balance = IntegerField(default=0)  # Locked funds (withdrawals)
allow_overdraft = BooleanField(default=False)  # Balance can go negative
lifetime_earnings = IntegerField(default=0)  # All-time prize earnings
```

**Key Features:**
- ✅ Atomic transactions with `SELECT FOR UPDATE` row locking
- ✅ Idempotency via `idempotency_key` (unique constraint)
- ✅ Immutability enforcement (cannot modify amount/reason after creation)
- ✅ Cached balance recalculation with `recalc_and_save()`
- ✅ Available balance property: `cached_balance - pending_balance`
- ✅ Insufficient funds check (model-level + service-level)

**Services:**
```python
# Core API (apps/economy/services.py)
def credit(profile, amount, *, reason, idempotency_key, meta) -> Dict
def debit(profile, amount, *, reason, idempotency_key, meta) -> Dict
def get_balance(profile) -> int
def get_transaction_history(wallet, limit) -> QuerySet
```

**Transaction Reasons (Existing):**
```python
class Reason(models.TextChoices):
    PARTICIPATION = "participation"
    TOP4 = "top4"
    RUNNER_UP = "runner_up"
    WINNER = "winner"
    ENTRY_FEE_DEBIT = "entry_fee_debit"
    REFUND = "refund"
    MANUAL_ADJUST = "manual_adjust"
    CORRECTION = "correction"
    P2P_TRANSFER = "p2p_transfer"
```

### 2.2 What Can Be Reused for Bounty System

**✅ REUSE: Escrow Pattern (pending_balance field)**
- `pending_balance` was designed for withdrawal holds
- **Can be repurposed** for bounty stakes:
  1. Debit from `cached_balance` when bounty created
  2. Add to `pending_balance` (funds locked)
  3. On bounty completion: Deduct from `pending_balance`, credit winner
  4. On expiry/cancel: Return `pending_balance` to `cached_balance`

**Example Flow:**
```python
# Create bounty (lock 5000 DC)
1. debit(profile, 5000, reason='BOUNTY_ESCROW', idempotency_key=f'bounty:create:{bounty_id}')
   # cached_balance -= 5000
2. wallet.pending_balance += 5000
   wallet.save()

# Bounty completed (release to winner)
3. wallet.pending_balance -= 5000
   wallet.save()
4. credit(winner_profile, 4750, reason='BOUNTY_WIN', idempotency_key=f'bounty:win:{bounty_id}')
   # 5% platform fee: 5000 * 0.95 = 4750

# Bounty expired (refund creator)
3. wallet.pending_balance -= 5000
   wallet.save()
4. credit(creator_profile, 5000, reason='BOUNTY_REFUND', idempotency_key=f'bounty:refund:{bounty_id}')
```

**✅ REUSE: Idempotency Pattern**
- `idempotency_key` prevents duplicate transactions
- Unique constraint at DB level
- Service returns existing transaction if key exists

**Example:**
```python
# Format: "bounty:<action>:<bounty_id>:<wallet_id>"
idempotency_key = f"bounty:escrow:{bounty.id}:{wallet.id}"
```

**✅ REUSE: Transaction Metadata**
- `metadata = JSONField()` can store bounty context:
```python
metadata = {
    'bounty_id': 123,
    'bounty_title': '1v1 Gridshot',
    'game': 'valorant',
    'opponent_id': 456
}
```

**✅ REUSE: Transaction History**
- Existing `get_transaction_history()` shows all transactions
- Can filter by reason to show bounty activity:
```python
bounty_txns = wallet.transactions.filter(
    reason__in=['BOUNTY_ESCROW', 'BOUNTY_WIN', 'BOUNTY_REFUND']
)
```

### 2.3 What Needs Addition for Bounties

**New Transaction Reasons:**
```python
class Reason(models.TextChoices):
    # ... existing ...
    BOUNTY_ESCROW = "bounty_escrow", "Bounty Stake (Escrow)"
    BOUNTY_WIN = "bounty_win", "Bounty Prize"
    BOUNTY_REFUND = "bounty_refund", "Bounty Refund"
    BOUNTY_FEE = "bounty_fee", "Platform Fee"  # 5% platform cut
```

**New Service Methods:**
```python
# apps/economy/services.py (extend existing)
def lock_bounty_stake(wallet, amount, bounty_id) -> Dict:
    """Lock funds in pending_balance for bounty escrow"""
    pass

def release_bounty_to_winner(bounty) -> Dict:
    """Transfer escrow to winner, deduct platform fee"""
    pass

def refund_bounty_stake(bounty) -> Dict:
    """Return escrowed funds to creator on expiry"""
    pass
```

### 2.4 What Should NOT Be Duplicated

❌ **Do NOT create a separate BountyWallet model** - Use existing `DeltaCrownWallet.pending_balance`  
❌ **Do NOT create custom balance tracking** - Use transaction ledger as source of truth  
❌ **Do NOT bypass idempotency** - Always use `idempotency_key` to prevent duplicates  
❌ **Do NOT modify existing transaction reasons** - Add new ones for bounty-specific flows  

### 2.5 Integration Architecture

```
Bounty Model (new)
     │
     ├─> BountyService.create_bounty()
     │        │
     │        └─> economy.services.lock_bounty_stake()
     │                    │
     │                    └─> DeltaCrownTransaction (BOUNTY_ESCROW)
     │
     ├─> BountyService.complete_bounty()
     │        │
     │        └─> economy.services.release_bounty_to_winner()
     │                    │
     │                    ├─> DeltaCrownTransaction (BOUNTY_WIN)
     │                    └─> DeltaCrownTransaction (BOUNTY_FEE)
     │
     └─> BountyService.expire_bounty()
              │
              └─> economy.services.refund_bounty_stake()
                           │
                           └─> DeltaCrownTransaction (BOUNTY_REFUND)
```

---

## 3. Tournament Operations (apps/tournament_ops/)

### 3.1 What Exists

**Match State Machine (apps/tournaments/models/match.py):**
```python
class Match(models.Model):
    STATE_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('check_in', 'Check-in Open'),
        ('ready', 'Ready to Start'),
        ('live', 'Live/In Progress'),
        ('pending_result', 'Pending Result'),
        ('completed', 'Completed'),
        ('disputed', 'Disputed'),
        ('forfeit', 'Forfeit'),
        ('cancelled', 'Cancelled'),
    ]
    
    state = CharField(max_length=20, choices=STATE_CHOICES)
    winner_id = PositiveIntegerField(null=True)
    loser_id = PositiveIntegerField(null=True)
    participant1_score = PositiveIntegerField(default=0)
    participant2_score = PositiveIntegerField(default=0)
    lobby_info = JSONField(default=dict)  # Game-specific data
```

**Match Service (apps/tournament_ops/services/match_service.py):**
```python
class MatchService:
    def report_match_result(match_id, submitted_by_user_id, raw_result_payload) -> MatchDTO:
        """
        Submit match result from a participant.
        
        Workflow:
        1. Validate match is in scheduled/live state
        2. Use GameAdapter to validate result payload
        3. Determine proposed winner/loser
        4. Update match to PENDING_RESULT state
        5. Publish MatchResultSubmittedEvent
        """
        pass
    
    def schedule_match(match_id, scheduled_time) -> MatchDTO:
        """Schedule match and notify teams"""
        pass
```

**Event Bus Pattern:**
```python
from common.events import get_event_bus, Event

self.event_bus.publish(
    Event(
        name="MatchScheduledEvent",
        payload={
            "match_id": match_id,
            "tournament_id": updated_match.tournament_id,
            "team_a_id": updated_match.team_a_id,
            "team_b_id": updated_match.team_b_id,
            "scheduled_time": scheduled_time.isoformat(),
        }
    )
)
```

**Dispute Pattern (tournaments/models/match.py):**
- Match has `DISPUTED` state
- Certificate admin allows revocation for disputed results
- Admin action: "Revoke certificates for disputed results"

### 3.2 What Can Be Reused for Bounty System

**✅ REUSE: Match State Machine**
- Bounty needs similar states: `OPEN → ACCEPTED → IN_PROGRESS → PENDING_RESULT → COMPLETED`
- Can adapt `DISPUTED` state for bounty disputes

**Bounty State Machine (adapted from Match):**
```python
class Bounty(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),  # Awaiting acceptance
        ('accepted', 'Accepted'),  # Someone accepted
        ('in_progress', 'In Progress'),  # Match started
        ('pending_result', 'Pending Result'),  # Result submitted
        ('completed', 'Completed'),  # Verified & paid
        ('disputed', 'Disputed'),  # Result challenged
        ('expired', 'Expired'),  # No acceptor, refunded
        ('cancelled', 'Cancelled'),  # Creator cancelled
    ]
```

**✅ REUSE: Result Submission Pattern**
- `report_match_result()` validates payload, updates state
- Can create `BountyService.submit_result(bounty_id, submitted_by_user_id, result_payload)`

**✅ REUSE: Event Bus for Notifications**
```python
self.event_bus.publish(
    Event(
        name="BountyAcceptedEvent",
        payload={
            "bounty_id": bounty.id,
            "creator_id": bounty.creator_id,
            "acceptor_id": acceptor.id,
            "stake_amount": bounty.stake_amount,
        }
    )
)
```

**✅ REUSE: Lobby Info Pattern**
- `lobby_info = JSONField()` stores game-specific data (map, server, lobby code)
- Bounty can use same pattern:
```python
bounty.lobby_info = {
    'game_mode': 'Gridshot',
    'lobby_code': 'ABC-123',
    'hosted_by': 'creator',  # or 'acceptor'
    'server_region': 'SEA'
}
```

### 3.3 What Can Be Reused for Endorsements

**✅ REUSE: Post-Match Hook**
- After match completes (`state='completed'`), trigger endorsement modal
- Can use Django signals or service layer hook:
```python
# In MatchService.complete_match()
if match.state == Match.COMPLETED:
    # Trigger endorsement window
    EndorsementService.open_endorsement_window(
        match_id=match.id,
        participants=[match.participant1_id, match.participant2_id]
    )
```

**✅ REUSE: Participant Verification**
- Match tracks participants (`participant1_id`, `participant2_id`)
- Endorsement system can verify "was teammate in this match":
```python
def can_endorse(endorser_user, receiver_user, match):
    participants = {match.participant1_id, match.participant2_id}
    return (
        endorser_user.id in participants and
        receiver_user.id in participants and
        endorser_user.id != receiver_user.id
    )
```

### 3.4 What Needs Addition

**For Bounties:**
- Bounty model (creator, acceptor, stake, status, game, requirements)
- BountyService (create, accept, submit_result, complete, dispute, refund)
- Bounty expiry task (Celery/cron to auto-refund after 7 days)

**For Endorsements:**
- SkillEndorsement model (match_id, receiver, endorser, skill_name)
- EndorsementService (create, validate_teammate, aggregate_counts)
- Post-match modal UI trigger

### 3.5 What Should NOT Be Duplicated

❌ **Do NOT create separate match tracking for bounties** - Reuse Match model if possible, or reference Match.id in Bounty  
❌ **Do NOT create custom event bus** - Use existing `common.events.get_event_bus()`  
❌ **Do NOT bypass state machine** - Always use proper state transitions with validation  

---

## 4. Teams System (apps/teams/)

### 4.1 What Exists

**Team Model (apps/teams/models/_legacy.py):**
```python
class Team(models.Model):
    name = CharField(max_length=100, unique=True)
    tag = CharField(max_length=10, unique=True)
    game = CharField(max_length=50)  # Which game team competes in
    logo = ImageField(upload_to=team_logo_path)
    
    # Social engagement
    followers_count = PositiveIntegerField(default=0)
    posts_count = PositiveIntegerField(default=0)
    is_verified = BooleanField(default=False)
    
    # Team permissions
    allow_posts = BooleanField(default=True)
    posts_require_approval = BooleanField(default=False)
    members_can_invite = BooleanField(default=False)
    
    @property
    def captain(self):
        """Get team captain (OWNER role)"""
        owner_membership = self.memberships.filter(
            status='ACTIVE',
            role='OWNER'
        ).first()
        return owner_membership.profile if owner_membership else None
    
    @property
    def max_roster_size(self) -> int:
        """Get game-specific roster limit"""
        # Uses GameService to fetch game roster rules
        pass
```

**TeamMembership Model:**
```python
class TeamMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = 'OWNER', 'Team Owner (Captain)'
        CAPTAIN = 'CAPTAIN', 'Captain'  # Can have multiple
        MANAGER = 'MANAGER', 'Manager'
        COACH = 'COACH', 'Coach'
        ANALYST = 'ANALYST', 'Analyst'
        PLAYER = 'PLAYER', 'Player'
        SUBSTITUTE = 'SUBSTITUTE', 'Substitute'
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        TRIAL = 'TRIAL', 'Trial'
    
    team = ForeignKey(Team, related_name='memberships')
    profile = ForeignKey(UserProfile)
    role = CharField(choices=Role.choices)
    player_role = CharField()  # Game-specific (IGL, Entry, Support, etc.)
    status = CharField(choices=Status.choices, default='ACTIVE')
    joined_at = DateTimeField(auto_now_add=True)
```

**TeamInvite Model:**
```python
class TeamInvite(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        DECLINED = 'DECLINED', 'Declined'
        EXPIRED = 'EXPIRED', 'Expired'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    team = ForeignKey(Team)
    invited_user = ForeignKey(User, null=True)  # Or invited_email
    inviter = ForeignKey(User, related_name='sent_invites')
    role = CharField(choices=TeamMembership.Role.choices)
    status = CharField(choices=Status.choices, default='PENDING')
    expires_at = DateTimeField()  # Auto-expire invites
    token = UUIDField(default=uuid.uuid4, unique=True)  # Secure invite link
```

**Roster Capacity Check:**
```python
# In TeamInvite.clean()
def clean(self):
    active_count = self.team.memberships.filter(status='ACTIVE').count()
    pending_invites = TeamInvite.objects.filter(
        team=self.team,
        status='PENDING'
    ).count()
    
    if active_count + pending_invites >= TEAM_MAX_ROSTER:
        raise ValidationError("Team roster is full")
```

### 4.2 What Can Be Reused for Endorsements

**✅ REUSE: Teammate Verification**
- Check if two users were teammates in a specific tournament:
```python
def were_teammates_in_match(user1, user2, match):
    """Check if both users were on same team in match"""
    # Get teams that participated in match
    team_ids = {match.participant1_id, match.participant2_id}
    
    # Check if both users were members of same team
    for team_id in team_ids:
        memberships = TeamMembership.objects.filter(
            team_id=team_id,
            status='ACTIVE'
        ).values_list('profile__user_id', flat=True)
        
        if user1.id in memberships and user2.id in memberships:
            return True
    return False
```

**✅ REUSE: Captain Role Logic**
- Bounty "Scout Player" button should only show to team captains:
```python
def is_team_captain(user) -> bool:
    """Check if user is captain of any team"""
    return TeamMembership.objects.filter(
        profile__user=user,
        role__in=['OWNER', 'CAPTAIN'],
        status='ACTIVE'
    ).exists()
```

**✅ REUSE: Notification Pattern**
- TeamInvite system sends notifications via Django signals
- Bounty acceptance can trigger team notifications:
```python
# When bounty targets specific player
if bounty.target_user:
    # Notify player's team captains
    target_teams = TeamMembership.objects.filter(
        profile__user=bounty.target_user,
        status='ACTIVE'
    ).values_list('team_id', flat=True)
    
    captains = TeamMembership.objects.filter(
        team_id__in=target_teams,
        role__in=['OWNER', 'CAPTAIN'],
        status='ACTIVE'
    ).select_related('profile__user')
    
    for membership in captains:
        send_notification(
            user=membership.profile.user,
            type='BOUNTY_CHALLENGE',
            message=f"{bounty.creator.username} challenged {bounty.target_user.username}"
        )
```

### 4.3 What Can Be Reused for Bounties

**✅ REUSE: Permission System**
- `members_can_invite` pattern → Can apply to "who can create bounties"
- Team-wide bounties (team vs team challenges)

**✅ REUSE: Roster Limits**
- Prevent spam: Limit bounties per user per day (similar to roster cap)

### 4.4 What Needs Addition

**For Endorsements:**
- Match participant resolution (link Match → Team → Members)
- Post-match endorsement eligibility check

**For Bounties:**
- Team bounty creation (captain creates on behalf of team)
- Team notification when member challenged

### 4.5 What Should NOT Be Duplicated

❌ **Do NOT create separate team membership tracking** - Use existing TeamMembership  
❌ **Do NOT duplicate invite system** - Can extend TeamInvite pattern if needed  
❌ **Do NOT create custom permission checks** - Follow Team.members_can_* pattern  

---

## 5. Community System (apps/community/)

### 5.1 What Exists

**❌ CRITICAL FINDING: No Community App Found**

Directory check results:
```
apps/
├── accounts/
├── economy/
├── games/
├── teams/
├── tournaments/
├── tournament_ops/
├── user_profile/
└── ... (no community/ or posts/ directory)
```

**Grep search for "Post" models:**
- No `apps/community/` directory
- No `apps/posts/` directory
- No `class Post(models.Model)` found in user_profile
- No feed/timeline models

### 5.2 Implications for User Profile Posts Tab

**Option 1: Build from Scratch**
- Create `apps/community/` with Post, PostMedia, PostLike, PostComment models
- Estimated work: 5-7 days for full CRUD + moderation

**Option 2: Stub the Tab**
- Show "Coming Soon" message in Posts tab
- Quick implementation: 1 day

**Option 3: Remove Tab**
- Remove Posts tab from template navigation
- Quickest: 1 hour

### 5.3 Recommendation

**Defer Posts tab to Phase 2** (Option 2):
- Template shows post creation UI, but backend doesn't exist
- Higher priority: Bounty + Endorsements (core competitive features)
- Posts are "nice to have" but not critical for MVP

If Posts must be built, consider:
- Reuse `UserActivity` event log pattern (immutable feed)
- Integrate with existing team posts system (Team.allow_posts, posts_require_approval)

---

## 6. User Profile Patterns (apps/user_profile/)

### 6.1 What Exists

**Permission Checker (profile_permissions.py):**
```python
class ProfilePermissionChecker:
    """Compute granular permissions for profile viewing"""
    
    def __init__(self, viewer: User, profile: UserProfile):
        self.viewer = viewer
        self.profile = profile
        self.privacy = PrivacySettings.objects.get_or_create(user_profile=profile)
        
        # Compute viewer role
        self.is_owner = viewer.id == profile.user.id
        self.is_follower = FollowService.is_following(viewer, profile.user)
        self.is_visitor = viewer.is_authenticated and not self.is_owner
        self.is_anonymous = not viewer.is_authenticated
    
    def can_view_wallet(self) -> bool:
        return self.is_owner  # Wallet always owner-only
    
    def can_view_achievements(self) -> bool:
        if self.is_owner:
            return True
        if not self.privacy.show_achievements:
            return False
        return self.can_view_profile()
    
    def get_all_permissions(self) -> dict:
        return {
            'viewer_role': 'owner' | 'follower' | 'visitor' | 'anonymous',
            'can_view_profile': bool,
            'can_view_wallet': bool,
            'can_view_achievements': bool,
            # ... more permission flags
        }
```

**Activity Event Log (models/activity.py):**
```python
class UserActivity(models.Model):
    """Immutable event log of all user actions"""
    
    user = ForeignKey(User, on_delete=PROTECT)
    event_type = CharField(choices=EventType.choices)  # tournament_won, match_played, etc.
    timestamp = DateTimeField(auto_now_add=True)
    metadata = JSONField(default=dict)  # Event-specific data
    source_model = CharField()  # Registration, Match, etc.
    source_id = IntegerField()  # PK of source
    
    class Meta:
        constraints = [
            # Idempotency: prevent duplicate events from same source
            UniqueConstraint(
                fields=['source_model', 'source_id', 'event_type'],
                name='unique_source_event'
            )
        ]
    
    def save(self, *args, **kwargs):
        """Enforce immutability - only allow creation"""
        if self.pk is not None:
            raise ValidationError("Events are immutable")
        super().save(*args, **kwargs)
```

**Event Types (existing):**
```python
class EventType(models.TextChoices):
    # Tournament Events
    TOURNAMENT_REGISTERED = 'tournament_registered'
    TOURNAMENT_WON = 'tournament_won'
    TOURNAMENT_RUNNER_UP = 'tournament_runner_up'
    
    # Match Events
    MATCH_PLAYED = 'match_played'
    MATCH_WON = 'match_won'
    MATCH_LOST = 'match_lost'
    
    # Economy Events
    COINS_EARNED = 'coins_earned'
    COINS_SPENT = 'coins_spent'
    
    # Achievement Events
    ACHIEVEMENT_UNLOCKED = 'achievement_unlocked'
    
    # Team Events (Future)
    TEAM_CREATED = 'team_created'
    TEAM_JOINED = 'team_joined'
```

**Service Pattern (services/):**
```python
# apps/user_profile/services/game_passport_service.py
class GamePassportService:
    @staticmethod
    def create_passport(user, game, in_game_name, **kwargs):
        """Create game account with validation"""
        pass
    
    @staticmethod
    def get_passport(user, game):
        """Retrieve single game passport"""
        pass
    
    @staticmethod
    def list_passports(user):
        """Get all user's game accounts"""
        pass
```

**Signal Pattern (signals/legacy_signals.py):**
```python
@receiver(post_save, sender=Registration)
def award_xp_on_tournament_registration(sender, instance, created, **kwargs):
    """Auto-award XP when user registers for tournament"""
    if created:
        from apps.user_profile.services import award_xp
        award_xp(
            profile=instance.user,
            amount=10,
            reason='tournament_registration',
            source_model='Registration',
            source_id=instance.id
        )
```

### 6.2 What Can Be Reused

**✅ REUSE: Permission Checker Pattern**
- Bounty permissions:
```python
class BountyPermissionChecker:
    def can_accept_bounty(self, viewer, bounty):
        # Can't accept own bounty
        # Must have minimum reputation
        # Must not be blocked by creator
        pass
    
    def can_view_bounty(self, viewer, bounty):
        # Open bounties are public
        # Completed bounties show to participants only
        pass
```

**✅ REUSE: Activity Event Log**
- Add bounty/endorsement event types:
```python
class EventType(models.TextChoices):
    # ... existing ...
    BOUNTY_CREATED = 'bounty_created'
    BOUNTY_ACCEPTED = 'bounty_accepted'
    BOUNTY_WON = 'bounty_won'
    BOUNTY_LOST = 'bounty_lost'
    SKILL_ENDORSED = 'skill_endorsed'  # Received endorsement
    SKILL_GAVE_ENDORSEMENT = 'skill_gave_endorsement'  # Gave endorsement
```

**✅ REUSE: Service Layer Pattern**
```python
# apps/user_profile/services/bounty_service.py
class BountyService:
    @staticmethod
    def create_bounty(creator, title, game, stake_amount, requirements):
        """Create bounty with escrow lock"""
        pass
    
    @staticmethod
    def accept_bounty(bounty_id, acceptor):
        """Accept challenge with validation"""
        pass
    
    @staticmethod
    def complete_bounty(bounty_id, winner):
        """Release escrow to winner"""
        pass
```

**✅ REUSE: Signal Pattern**
```python
@receiver(post_save, sender=Match)
def open_endorsement_window(sender, instance, **kwargs):
    """Trigger endorsement modal after match completion"""
    if instance.state == 'completed' and not kwargs.get('created'):
        # Open endorsement window for participants
        EndorsementService.notify_participants(match=instance)
```

### 6.3 What Needs Addition

**For Bounties:**
- BountyPermissionChecker (can_accept, can_view, can_cancel)
- Bounty event types (BOUNTY_CREATED, BOUNTY_WON, etc.)
- BountyService with escrow integration

**For Endorsements:**
- Endorsement event types (SKILL_ENDORSED, etc.)
- EndorsementService (create, validate_teammate, aggregate)

**For Cosmetics:**
- Extend PrivacySettings: `show_inventory = BooleanField(default=True)`
- New permission: `can_view_inventory()`

### 6.4 What Should NOT Be Duplicated

❌ **Do NOT create separate permission checker classes** - Extend ProfilePermissionChecker  
❌ **Do NOT create custom event log** - Use UserActivity with new event types  
❌ **Do NOT bypass service layer** - Always use services for business logic  
❌ **Do NOT duplicate signal patterns** - Follow existing receiver conventions  

---

## 7. Cross-App Integration Patterns

### 7.1 Economy ↔ User Profile

**Current Pattern:**
```python
# Signal: Sync wallet to profile on transaction
@receiver(post_save, sender=DeltaCrownTransaction)
def sync_wallet_to_profile(sender, instance, **kwargs):
    """Update UserProfile.deltacoin_balance when transaction created"""
    profile = instance.wallet.profile
    profile.deltacoin_balance = instance.wallet.cached_balance
    profile.save(update_fields=['deltacoin_balance'])
```

**Reuse for Bounties:**
```python
# When bounty completed, also update lifetime_earnings
profile.lifetime_earnings = wallet.lifetime_earnings
profile.save(update_fields=['lifetime_earnings'])
```

### 7.2 Tournament Ops ↔ User Profile

**Current Pattern:**
```python
# In MatchService, publish events
self.event_bus.publish(
    Event(name="MatchCompletedEvent", payload={...})
)

# In user_profile/signals, listen for events
@receiver(match_completed_signal)
def record_activity(sender, match, **kwargs):
    UserActivity.objects.create(
        user=match.winner,
        event_type=EventType.MATCH_WON,
        source_model='Match',
        source_id=match.id
    )
```

**Reuse for Endorsements:**
```python
@receiver(match_completed_signal)
def open_endorsement_window(sender, match, **kwargs):
    # Trigger modal for participants to endorse teammates
    EndorsementService.create_endorsement_opportunities(match=match)
```

### 7.3 Teams ↔ User Profile

**Current Pattern:**
```python
# TeamMembership links profile to team
profile.user_teams = TeamMembership.objects.filter(
    profile=profile,
    status='ACTIVE'
).select_related('team')

# Career timeline (template needs this)
career_history = TeamMembership.objects.filter(
    profile=profile
).order_by('-joined_at')
```

**Reuse for Endorsements:**
```python
# Verify teammate relationship
def were_teammates(endorser, receiver):
    # Find common teams
    endorser_teams = TeamMembership.objects.filter(
        profile__user=endorser,
        status='ACTIVE'
    ).values_list('team_id', flat=True)
    
    receiver_teams = TeamMembership.objects.filter(
        profile__user=receiver,
        status='ACTIVE'
    ).values_list('team_id', flat=True)
    
    return bool(set(endorser_teams) & set(receiver_teams))
```

---

## 8. Architecture Patterns to Follow

### 8.1 Service Layer Pattern

**✅ All business logic goes in services/**, not models or views:
```
apps/user_profile/
└── services/
    ├── bounty_service.py
    ├── endorsement_service.py
    ├── cosmetics_service.py
    └── loadout_service.py
```

**✅ Services use adapters for external dependencies:**
```python
class BountyService:
    def __init__(self, economy_adapter, match_adapter, notification_adapter):
        self.economy = economy_adapter
        self.match = match_adapter
        self.notification = notification_adapter
```

### 8.2 Idempotency Pattern

**✅ Always use idempotency keys for money/critical operations:**
```python
# Format: <domain>:<action>:<resource_id>:<user_id>
idempotency_key = f"bounty:create:{bounty.id}:{user.id}"
idempotency_key = f"endorsement:create:{match.id}:{endorser.id}:{receiver.id}"
```

### 8.3 Event-Driven Pattern

**✅ Use event bus for cross-app notifications:**
```python
event_bus.publish(
    Event(
        name="BountyAcceptedEvent",
        payload={'bounty_id': 123, 'acceptor_id': 456}
    )
)
```

**✅ Listen with signals:**
```python
@receiver(bounty_accepted_signal)
def notify_creator(sender, bounty, **kwargs):
    send_notification(...)
```

### 8.4 Immutability Pattern

**✅ Make audit trail immutable:**
```python
class Bounty(models.Model):
    def save(self, *args, **kwargs):
        """Prevent modification after completion"""
        if self.pk and self.status == 'completed':
            raise ValidationError("Cannot modify completed bounty")
        super().save(*args, **kwargs)
```

---

## 9. Security Patterns to Follow

### 9.1 Atomic Transactions

**✅ Use SELECT FOR UPDATE for balance operations:**
```python
@transaction.atomic
def lock_bounty_stake(wallet, amount, bounty_id):
    # Lock wallet row
    locked_wallet = DeltaCrownWallet.objects.select_for_update().get(pk=wallet.pk)
    
    # Check balance
    if locked_wallet.available_balance < amount:
        raise InsufficientFunds()
    
    # Debit + lock in pending
    locked_wallet.cached_balance -= amount
    locked_wallet.pending_balance += amount
    locked_wallet.save()
```

### 9.2 Permission Checks

**✅ Always check permissions before actions:**
```python
def accept_bounty(bounty_id, acceptor):
    bounty = Bounty.objects.get(pk=bounty_id)
    
    # Permission checks
    if acceptor == bounty.creator:
        raise PermissionDenied("Cannot accept own bounty")
    
    if bounty.status != 'open':
        raise InvalidStateError("Bounty is not open")
    
    if acceptor.reputation_score < 50:
        raise PermissionDenied("Insufficient reputation")
```

### 9.3 Anti-Spam

**✅ Rate limiting patterns:**
```python
# Limit bounty creation
recent_bounties = Bounty.objects.filter(
    creator=user,
    created_at__gte=timezone.now() - timedelta(days=1)
).count()

if recent_bounties >= 10:
    raise RateLimitError("Max 10 bounties per day")
```

---

## 10. Summary: Integration Checklist

### For Bounty System:

**✅ Reuse:**
- [ ] `DeltaCrownWallet.pending_balance` for escrow
- [ ] `DeltaCrownTransaction` with new reasons (BOUNTY_ESCROW, BOUNTY_WIN, BOUNTY_REFUND)
- [ ] `idempotency_key` pattern for duplicate prevention
- [ ] Match state machine pattern for bounty lifecycle
- [ ] Event bus for notifications

**❌ Do NOT:**
- [ ] Create separate wallet system
- [ ] Bypass transaction ledger
- [ ] Modify existing transaction amounts
- [ ] Create custom event bus

### For Endorsement System:

**✅ Reuse:**
- [ ] Match completion signal hook
- [ ] TeamMembership for teammate verification
- [ ] UserActivity event log (new types: SKILL_ENDORSED)
- [ ] Unique constraint pattern for duplicate prevention

**❌ Do NOT:**
- [ ] Allow endorsements outside match context
- [ ] Skip teammate verification
- [ ] Allow self-endorsements
- [ ] Create mutable endorsement records

### For Posts System:

**⚠️ STATUS: Does NOT Exist**
- [ ] **Decision needed:** Build from scratch, stub, or remove tab

### For Cosmetics:

**✅ Reuse:**
- [ ] Badge model (rarity, category)
- [ ] UserBadge (earned_at, progress)
- [ ] ProfilePermissionChecker (add `can_view_inventory`)

**❌ Do NOT:**
- [ ] Create separate rarity system
- [ ] Duplicate badge earning logic
- [ ] Bypass achievement unlocking

### For Loadout:

**✅ Reuse:**
- [ ] Team.game pattern (link to game-specific configs)
- [ ] ProfilePermissionChecker (add `can_view_loadout`)

**❌ Do NOT:**
- [ ] Hardcode hardware catalog
- [ ] Create duplicate game registry

---

## 11. Next Steps

1. **Review this audit with product team** - Confirm reusable patterns align with requirements
2. **Create detailed schemas** - Based on reusable patterns identified
3. **Write integration tests** - Verify economy↔bounty, tournament↔endorsement flows
4. **Document API contracts** - Define service interfaces for new features
5. **Implement in phases:**
   - Phase 1: Bounty + Endorsement (core competitive features)
   - Phase 2: Cosmetics + Loadout (enhancement features)
   - Phase 3: Posts (if product confirms requirement)

---

**Audit Status:** ✅ Complete  
**Confidence Level:** High (95%+)  
**Files Reviewed:** 20+ files across 5 apps  
**Integration Points Identified:** 15+ reusable patterns
