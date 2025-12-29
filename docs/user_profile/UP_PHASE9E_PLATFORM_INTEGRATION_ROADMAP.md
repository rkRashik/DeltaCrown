# UP-PHASE9E: Community & Platform Integration Roadmap

**Phase:** Post-Launch Readiness  
**Type:** Integration Strategy & Event Architecture  
**Date:** 2025-12-29  
**Status:** Roadmap Document (No Implementation)

---

## Executive Summary

This document defines how the user_profile system should integrate with DeltaCrown's other platform systems (Community, Teams, Tournaments, Economy) through events, signals, and API contracts **without implementing any code**.

**Goal:** Enable seamless cross-app data flow while maintaining user_profile as the source of truth for player identity.

---

## 1. Integration Philosophy

### 1.1 Source of Truth Principle

**User Profile = Identity Layer**

```
┌─────────────────────────────────────┐
│       USER_PROFILE (Identity)       │
│  - Display name, avatar, bio        │
│  - Game passports (gaming identity) │
│  - Privacy settings                 │
│  - Public profile data              │
└─────────────────────────────────────┘
         │        │        │        │
    ┌────┘        │        │        └────┐
    │             │        │             │
┌───▼────┐  ┌────▼───┐  ┌▼────┐  ┌─────▼─────┐
│Community│  │ Teams  │  │Tourn│  │  Economy  │
│(follows)│  │(roster)│  │(part)│  │ (wallet)  │
└─────────┘  └────────┘  └─────┘  └───────────┘
```

**Rules:**
- ❌ Teams cannot modify user display name (read-only from user_profile)
- ❌ Economy cannot modify user avatar (read-only from user_profile)
- ✅ Teams can link to user via ForeignKey (user_profile.user)
- ✅ Economy can sync balance → user_profile.deltacoin_balance (cached)

---

### 1.2 Event-Driven Architecture

**Pattern:** Domain events + signal handlers

```python
# Example (CONCEPTUAL - NOT IMPLEMENTED)
# When user updates profile
user_profile_updated.send(
    sender=UserProfile,
    user_id=profile.user.id,
    changed_fields=['display_name', 'avatar']
)

# Teams app listens
@receiver(user_profile_updated)
def sync_team_member_name(sender, user_id, changed_fields, **kwargs):
    if 'display_name' in changed_fields:
        TeamMembership.objects.filter(user_id=user_id).update(
            cached_display_name=UserProfile.objects.get(user_id=user_id).display_name
        )
```

**Benefits:**
- Loose coupling (apps don't import each other directly)
- Async processing (can queue events to Celery)
- Audit trail (event log for debugging)

---

## 2. Community App Integration

### 2.1 Follow System

**Current State:** ✅ Implemented in `apps/user_profile/models/Follow`

**Integration Points:**

#### Event: User Followed
```python
# apps/user_profile/signals/follow_signals.py (CONCEPTUAL)
user_followed = Signal(providing_args=['follower_id', 'followed_id'])

# Trigger when Follow.objects.create()
user_followed.send(
    sender=Follow,
    follower_id=follow.follower.id,
    followed_id=follow.following.id
)
```

**Community App Subscribes:**
- Create notification: "{follower} followed you"
- Update follower feed
- Increment follower_count (if cached)

---

#### Event: User Unfollowed
```python
user_unfollowed = Signal(providing_args=['follower_id', 'followed_id'])
```

**Community App Actions:**
- Remove follow notification (if recent)
- Update follower feed
- Decrement follower_count

---

### 2.2 Activity Feed Integration

**Current State:** ✅ Implemented in `UserActivity` model

**Integration Pattern:**

#### Events Community Should Emit
```python
# From community app → user_profile
new_post_created = Signal(providing_args=['user_id', 'post_id', 'content'])
post_liked = Signal(providing_args=['liker_id', 'post_id'])
post_commented = Signal(providing_args=['commenter_id', 'post_id', 'content'])
```

**User Profile Subscribes:**
```python
@receiver(new_post_created)
def log_post_activity(sender, user_id, post_id, content, **kwargs):
    UserActivity.objects.create(
        user_id=user_id,
        event_type='POST_CREATED',
        event_data={'post_id': post_id, 'preview': content[:100]},
        is_public=True  # Respect privacy settings
    )
```

---

### 2.3 Feed Algorithm Integration

**User Profile Provides:**
- Follow graph (who follows who)
- User interests (inferred from game passports)
- Engagement history (from UserActivity)

**Community App Consumes:**
```python
# Pseudo-query (CONCEPTUAL)
following_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)

# Show posts from followed users + similar interests
posts = Post.objects.filter(
    Q(author_id__in=following_ids) |  # Following
    Q(tags__in=user_interests)        # Similar interests
).order_by('-created_at')
```

---

## 3. Teams App Integration

### 3.1 Team Roster Syncing

**Current State:** ⚠️ TeamMembership exists but may duplicate user data

**Problem:** Team roster displays outdated display names/avatars

**Solution:** Teams app should NOT store display name/avatar

#### Correct Schema
```python
# apps/teams/models.py (CONCEPTUAL)
class TeamMembership(models.Model):
    team = models.ForeignKey(Team)
    user = models.ForeignKey(User)  # Link to User, not UserProfile
    role = models.CharField()  # 'CAPTAIN', 'PLAYER', 'SUB'
    joined_at = models.DateTimeField()
    
    # DO NOT STORE: display_name, avatar (read from user_profile)
    
    @property
    def display_name(self):
        return self.user.userprofile.display_name  # Read-only
    
    @property
    def avatar_url(self):
        profile = self.user.userprofile
        return profile.avatar.url if profile.avatar else None
```

---

#### Events to Emit

**User Profile → Teams:**
```python
# When user updates profile
profile_display_name_changed = Signal(providing_args=['user_id', 'old_name', 'new_name'])
profile_avatar_changed = Signal(providing_args=['user_id', 'new_avatar_url'])
```

**Teams App Action:**
- Invalidate team roster cache
- Re-render team page if user is member

---

**Teams → User Profile:**
```python
# When user joins team
user_joined_team = Signal(providing_args=['user_id', 'team_id', 'role'])

# When user leaves team
user_left_team = Signal(providing_args=['user_id', 'team_id'])
```

**User Profile Action:**
```python
@receiver(user_joined_team)
def log_team_join(sender, user_id, team_id, role, **kwargs):
    UserActivity.objects.create(
        user_id=user_id,
        event_type='TEAM_JOINED',
        event_data={'team_id': team_id, 'role': role},
        is_public=True  # Show on profile
    )
```

---

### 3.2 Team Invitation Flow

**Flow:**
1. Team captain sends invite → `TeamInvitation.objects.create()`
2. Teams app emits `team_invite_sent` signal
3. User Profile creates notification (if notifications enabled)
4. User accepts invite → `user_joined_team` signal
5. User Profile logs activity

**Privacy Consideration:** Respect `allow_team_invites` setting

---

### 3.3 Team Profile Page

**What Teams App Displays:**
- Roster (links to player profiles `/@username/`)
- Team stats (win/loss, tournaments)
- Team activity feed

**What User Profile Provides:**
- Player display names (via property)
- Player avatars (via property)
- Player game passports (for roster validation)

---

## 4. Tournaments App Integration

### 4.1 Tournament Registration

**Flow:**
1. User registers for tournament
2. Tournaments app queries: "Does user have required game passport?"

```python
# apps/tournaments/views.py (CONCEPTUAL)
def register_for_tournament(request, tournament_id):
    tournament = Tournament.objects.get(id=tournament_id)
    game_id_required = tournament.game.id
    
    # Check if user has game passport
    from apps.user_profile.services.game_passport_service import GamePassportService
    passport = GamePassportService.get_passport_for_game(
        user=request.user,
        game_id=game_id_required
    )
    
    if not passport:
        return JsonResponse({'error': 'Please add game passport first'})
    
    # Register user
    TournamentParticipant.objects.create(
        tournament=tournament,
        user=request.user,
        game_ign=passport.ign,  # Copy for immutability
        game_rank=passport.current_rank
    )
```

---

#### Events to Emit

**Tournaments → User Profile:**
```python
user_registered_for_tournament = Signal(providing_args=['user_id', 'tournament_id', 'game_id'])
tournament_match_completed = Signal(providing_args=['user_id', 'match_id', 'won'])
tournament_placement = Signal(providing_args=['user_id', 'tournament_id', 'placement'])
```

**User Profile Actions:**
```python
@receiver(user_registered_for_tournament)
def log_tournament_registration(sender, user_id, tournament_id, **kwargs):
    UserActivity.objects.create(
        user_id=user_id,
        event_type='TOURNAMENT_REGISTERED',
        event_data={'tournament_id': tournament_id}
    )

@receiver(tournament_placement)
def award_achievement(sender, user_id, placement, **kwargs):
    if placement <= 3:  # Top 3
        AchievementService.unlock(
            user_id=user_id,
            achievement_code=f'TOURNAMENT_TOP{placement}'
        )
```

---

### 4.2 Match History Integration

**Current State:** ⚠️ TODO (see line 204 in fe_v2.py)

**Schema Proposal:**
```python
# apps/tournaments/models.py (CONCEPTUAL)
class Match(models.Model):
    tournament = models.ForeignKey(Tournament)
    team_a = models.ForeignKey(Team)
    team_b = models.ForeignKey(Team)
    winner = models.ForeignKey(Team, null=True)
    played_at = models.DateTimeField()

class MatchParticipant(models.Model):
    match = models.ForeignKey(Match)
    user = models.ForeignKey(User)  # Link to User
    team = models.ForeignKey(Team)
    kills = models.IntegerField()
    deaths = models.IntegerField()
    assists = models.IntegerField()
```

**User Profile Queries:**
```python
# Show match history on profile
recent_matches = MatchParticipant.objects.filter(
    user=profile_user
).select_related('match', 'team').order_by('-match__played_at')[:10]
```

---

### 4.3 Tournament Stats Syncing

**What Tournaments App Provides:**
- Total tournaments played
- Total matches won/lost
- Average KDA (if applicable)

**How User Profile Consumes:**
```python
# apps/user_profile/services/stats_service.py (CONCEPTUAL)
def update_tournament_stats(user_id):
    from apps.tournaments.models import TournamentParticipant, MatchParticipant
    
    stats, _ = UserProfileStats.objects.get_or_create(user_id=user_id)
    
    stats.tournaments_played = TournamentParticipant.objects.filter(
        user_id=user_id
    ).count()
    
    stats.matches_won = MatchParticipant.objects.filter(
        user_id=user_id,
        match__winner__teammembership__user_id=user_id
    ).count()
    
    stats.save()
```

**Trigger:** Run nightly via Celery task

---

## 5. Economy App Integration

### 5.1 Wallet Balance Syncing

**Current State:** ✅ `UserProfile.deltacoin_balance` exists (read-only)

**Pattern:** Economy app is source of truth, user_profile caches

#### Event Flow
```python
# apps/economy/signals.py (CONCEPTUAL)
wallet_balance_changed = Signal(providing_args=['user_id', 'new_balance', 'transaction_id'])

# User profile subscribes
@receiver(wallet_balance_changed)
def sync_balance_to_profile(sender, user_id, new_balance, **kwargs):
    UserProfile.objects.filter(user_id=user_id).update(
        deltacoin_balance=new_balance
    )
```

**Benefits:**
- Profile page shows balance without querying economy DB
- Economy app remains authoritative

---

### 5.2 Transaction Events

**Economy → User Profile:**
```python
transaction_completed = Signal(providing_args=['user_id', 'type', 'amount', 'description'])

# Types: 'DEPOSIT', 'WITHDRAWAL', 'PRIZE', 'PURCHASE'
```

**User Profile Actions:**
```python
@receiver(transaction_completed)
def log_transaction_activity(sender, user_id, type, amount, **kwargs):
    if type == 'PRIZE':
        UserActivity.objects.create(
            user_id=user_id,
            event_type='PRIZE_EARNED',
            event_data={'amount': amount},
            is_public=True  # Show on profile
        )
    
    # Update lifetime_earnings
    if type == 'PRIZE':
        UserProfile.objects.filter(user_id=user_id).update(
            lifetime_earnings=F('lifetime_earnings') + amount
        )
```

---

### 5.3 Purchase Events

**Flow:**
1. User buys item (avatar frame, badge, etc.)
2. Economy app emits `item_purchased` signal
3. User Profile adds to inventory

```python
item_purchased = Signal(providing_args=['user_id', 'item_id', 'item_type'])

@receiver(item_purchased)
def add_to_inventory(sender, user_id, item_id, item_type, **kwargs):
    profile = UserProfile.objects.get(user_id=user_id)
    
    if item_type == 'BADGE':
        # Add to pinned_badges (JSONField)
        inventory = profile.inventory_items or {}
        inventory.setdefault('badges', []).append(item_id)
        profile.inventory_items = inventory
        profile.save()
```

---

## 6. Event Catalog

### 6.1 Events User Profile Emits

| Event | Args | Subscribers |
|-------|------|-------------|
| `profile_created` | user_id | Community (create default follow settings) |
| `profile_updated` | user_id, changed_fields | Teams (invalidate cache) |
| `display_name_changed` | user_id, old_name, new_name | Teams, Economy |
| `avatar_changed` | user_id, new_avatar_url | Teams, Community |
| `game_passport_added` | user_id, game_id, ign | Tournaments (notify eligible tournaments) |
| `game_passport_deleted` | user_id, game_id | Tournaments (unregister from game-specific events) |
| `user_followed` | follower_id, followed_id | Community (notification) |
| `user_unfollowed` | follower_id, followed_id | Community (update feed) |
| `achievement_unlocked` | user_id, achievement_code | Community (notification), Economy (rewards) |
| `privacy_changed` | user_id, setting_name, new_value | Community (update visibility) |

---

### 6.2 Events User Profile Subscribes To

| Event | Source | Action |
|-------|--------|--------|
| `user_joined_team` | Teams | Log activity, update stats |
| `user_left_team` | Teams | Log activity, update stats |
| `tournament_registered` | Tournaments | Log activity |
| `tournament_completed` | Tournaments | Update stats, award achievement |
| `match_won` | Tournaments | Update stats, log activity |
| `wallet_balance_changed` | Economy | Sync cached balance |
| `transaction_completed` | Economy | Update lifetime_earnings, log activity |
| `item_purchased` | Economy | Add to inventory |
| `level_up` | Gamification | Log activity, unlock badge |

---

## 7. API Contracts

### 7.1 Public API (Read-Only)

**Endpoint:** `/api/profiles/@<username>/`

**Purpose:** Allow other apps to query profile data

**Response:**
```json
{
  "username": "johndoe",
  "display_name": "John Doe",
  "avatar_url": "https://cdn.deltacrown.com/avatars/123.jpg",
  "bio": "Professional VALORANT player",
  "public_id": "DC-123456",
  "country": "BD",
  "game_passports": [
    {
      "game": "valorant",
      "ign": "JohnDoe#TAG",
      "current_rank": "Immortal 3",
      "is_lft": false
    }
  ],
  "stats": {
    "tournaments_played": 15,
    "matches_won": 42,
    "follower_count": 156
  },
  "privacy": {
    "can_view_game_ids": true,
    "can_view_achievements": true,
    "can_send_message": true
  }
}
```

**Usage:**
```python
# From teams app (CONCEPTUAL)
import requests
response = requests.get('https://api.deltacrown.com/api/profiles/@johndoe/')
profile_data = response.json()

# Check if user has game passport for team's game
has_passport = any(
    p['game'] == 'valorant' 
    for p in profile_data['game_passports']
)
```

---

### 7.2 Internal Service API

**Purpose:** Fast access for internal apps (no HTTP overhead)

```python
# apps/user_profile/services/profile_api.py (CONCEPTUAL)
class ProfileAPIService:
    @staticmethod
    def get_display_name(user_id):
        """Get user's display name"""
        return UserProfile.objects.values_list('display_name', flat=True).get(user_id=user_id)
    
    @staticmethod
    def get_avatar_url(user_id):
        """Get user's avatar URL"""
        profile = UserProfile.objects.get(user_id=user_id)
        return profile.avatar.url if profile.avatar else None
    
    @staticmethod
    def has_game_passport(user_id, game_id):
        """Check if user has passport for game"""
        from apps.user_profile.services.game_passport_service import GamePassportService
        return GamePassportService.get_passport_for_game(user_id, game_id) is not None
    
    @staticmethod
    def can_receive_team_invite(user_id):
        """Check if user allows team invites"""
        settings = PrivacySettings.objects.get(user_profile__user_id=user_id)
        return settings.allow_team_invites
```

**Usage:**
```python
# From teams app
from apps.user_profile.services.profile_api import ProfileAPIService

# Before sending invite
if not ProfileAPIService.can_receive_team_invite(user_id):
    return JsonResponse({'error': 'User has disabled team invites'})
```

---

## 8. Webhook Events (External Integrations)

### 8.1 Discord Bot Integration

**Use Case:** Notify Discord when user achieves milestone

**Webhook Payload:**
```json
{
  "event": "achievement_unlocked",
  "user": {
    "username": "johndoe",
    "display_name": "John Doe",
    "avatar_url": "https://cdn.deltacrown.com/avatars/123.jpg"
  },
  "achievement": {
    "code": "FIRST_TOURNAMENT_WIN",
    "title": "Tournament Champion",
    "description": "Won first tournament"
  },
  "timestamp": "2025-12-29T10:30:00Z"
}
```

**Discord Bot Action:**
- Post to #achievements channel
- Ping @everyone for major achievements

---

### 8.2 Stream Overlay Integration

**Use Case:** Display profile stats on Twitch/YouTube overlay

**Webhook Payload:**
```json
{
  "event": "stats_updated",
  "user": {
    "username": "johndoe",
    "display_name": "John Doe"
  },
  "stats": {
    "tournaments_played": 16,
    "matches_won": 45,
    "current_rank": "Immortal 3"
  }
}
```

**Overlay Action:**
- Update on-screen stats display

---

## 9. Data Consistency Guarantees

### 9.1 Read-After-Write Consistency

**Scenario:** User updates profile → immediately views team page

**Problem:** Team page shows old display name (cached)

**Solution:**
```python
# Option 1: Cache invalidation
@receiver(profile_updated)
def invalidate_team_cache(sender, user_id, **kwargs):
    cache.delete(f'team_roster:{team_id}')

# Option 2: Event-driven update
@receiver(profile_updated)
def update_team_roster(sender, user_id, changed_fields, **kwargs):
    if 'display_name' in changed_fields:
        # Force reload team rosters containing this user
        team_ids = TeamMembership.objects.filter(user_id=user_id).values_list('team_id', flat=True)
        for team_id in team_ids:
            cache.delete(f'team_roster:{team_id}')
```

---

### 9.2 Eventual Consistency (Acceptable Cases)

**Scenarios Where Stale Data is OK:**
- Follower count (off by 1-2 for a few seconds)
- Activity feed (new activities appear within 5 minutes)
- Tournament stats (updated nightly)

**Not Acceptable:**
- Privacy settings (must be immediate)
- Wallet balance (must be real-time)
- Game passport visibility (must respect LFT toggle immediately)

---

## 10. Monitoring & Debugging

### 10.1 Event Logging

**Log all events to database:**
```python
# apps/user_profile/models.py (CONCEPTUAL)
class EventLog(models.Model):
    event_type = models.CharField(max_length=50)
    user_id = models.IntegerField()
    payload = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
```

**Use Cases:**
- Debug integration issues
- Audit trail for compliance
- Analytics (event frequency, popular actions)

---

### 10.2 Integration Health Dashboard

**Metrics to Track:**
- Event delivery success rate (%)
- Average event processing time (ms)
- Failed event retries
- Dead letter queue size

**Alerts:**
- Event failure rate >5% (warning)
- Event queue depth >1000 (critical)

---

## 11. Implementation Priority

### 11.1 Phase 1 (Launch)

**Critical Integrations:**
1. ✅ Follow system (already implemented)
2. ✅ Activity logging (already implemented)
3. Teams roster display (read display name from user_profile)
4. Economy balance sync (cache wallet balance)

**Events Needed:**
- `profile_updated`
- `wallet_balance_changed`

**Effort:** 2-3 days

---

### 11.2 Phase 2 (First Month)

**Important Integrations:**
5. Tournament registration (check game passport)
6. Match history display
7. Achievement unlocking system
8. Team invite flow (respect privacy)

**Events Needed:**
- `game_passport_added`
- `tournament_registered`
- `match_completed`
- `achievement_unlocked`

**Effort:** 1 week

---

### 11.3 Phase 3 (First Quarter)

**Nice-to-Have:**
9. Discord webhook (achievement notifications)
10. Stream overlay API
11. Public API (/api/profiles/)
12. Event analytics dashboard

**Effort:** 2 weeks

---

## 12. Testing Strategy

### 12.1 Integration Tests

**Test Scenarios:**
```python
# Test: Profile update triggers team cache invalidation
def test_profile_update_invalidates_team_cache():
    user = create_user()
    team = create_team()
    TeamMembership.objects.create(user=user, team=team)
    
    # Cache team roster
    roster = get_team_roster(team.id)  # Caches
    
    # Update profile
    user.userprofile.display_name = 'New Name'
    user.userprofile.save()
    
    # Verify cache invalidated
    roster_after = get_team_roster(team.id)
    assert roster_after[0]['display_name'] == 'New Name'
```

---

### 12.2 Event Delivery Tests

```python
# Test: Event is logged and processed
def test_game_passport_added_event():
    user = create_user()
    
    # Add game passport
    GameProfile.objects.create(user=user, game_id=1, ign='TestIGN')
    
    # Verify event logged
    event = EventLog.objects.filter(
        event_type='game_passport_added',
        user_id=user.id
    ).first()
    assert event is not None
    
    # Verify activity created
    activity = UserActivity.objects.filter(
        user_id=user.id,
        event_type='GAME_PASSPORT_ADDED'
    ).first()
    assert activity is not None
```

---

## 13. Documentation Requirements

### 13.1 Integration Guide

**For Other App Developers:**
```markdown
# Integrating with User Profile

## Displaying User Data

DO:
- Use ProfileAPIService.get_display_name(user_id)
- Link to profile: /@{username}/

DON'T:
- Store display name in your model (use ForeignKey to User)
- Query UserProfile directly (use service layer)

## Listening to Events

from apps.user_profile.signals import profile_updated
from django.dispatch import receiver

@receiver(profile_updated)
def handle_profile_update(sender, user_id, changed_fields, **kwargs):
    # Your logic here
    pass
```

---

### 13.2 Event Documentation

**For Each Event:**
- Name (e.g., `user_followed`)
- Arguments (e.g., `follower_id`, `followed_id`)
- When it fires (e.g., "After Follow.objects.create()")
- Who should subscribe (e.g., "Community app for notifications")
- Example handler

---

## Final Recommendations

**Integration Readiness:** ⚠️ **Partially Ready**

**Current State:**
- ✅ Follow system ready for community integration
- ✅ Activity logging ready for cross-app events
- ⚠️ No event emitting yet (signals need implementation)
- ⚠️ No internal API service (teams/economy would benefit)

**Launch Blockers:** None (can launch without full integration)

**Post-Launch Priority:**
1. Implement `profile_updated` signal (for teams cache invalidation)
2. Implement `wallet_balance_changed` handler (economy sync)
3. Create ProfileAPIService for internal use

**Effort:** 3-4 days of work (can be done post-launch)

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-29  
**Status:** Roadmap Document - No Implementation Required  
**Owner:** Platform Architecture Team
