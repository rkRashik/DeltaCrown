# UP-M2: User Stats, History & Activity Ledger - TARGET ARCHITECTURE

**Mission:** Transform UserProfile into a true "user memory" by introducing an immutable activity/event layer and derived stats that auto-update from real actions.

**Status:** 📝 Planning  
**Created:** December 23, 2025  
**Author:** GitHub Copilot Agent

---

## 1. PROBLEM STATEMENT

### 1.1 Current State (What's Broken)

**Missing: Historical Activity Trail**
- ❌ No record of "User X played Tournament Y on Date Z"
- ❌ Match history lives in Match model (not user-centric)
- ❌ Tournament participation is Registration model (not outcome-focused)
- ❌ Economy transactions exist but not linked to events

**Missing: Authoritative Stats**
- ❌ No `tournaments_played` count
- ❌ No `tournaments_won` count
- ❌ No `matches_played` / `matches_won` stats
- ❌ `total_earnings` exists but not synced with ledger
- ❌ Win rate must be computed live every time (expensive)

**Current Workarounds (Anti-Patterns):**
```python
# SLOW: Count tournaments user registered for
tournaments_played = Registration.objects.filter(user=user).count()

# WRONG: Doesn't account for no-shows/cancellations
tournaments_completed = Registration.objects.filter(
    user=user, 
    status='confirmed'
).count()

# EXPENSIVE: Aggregation query every page load
total_earnings = DeltaCrownTransaction.objects.filter(
    wallet__profile__user=user,
    reason__in=['WINNER', 'RUNNER_UP', 'TOP4', 'PARTICIPATION']
).aggregate(Sum('amount'))['amount__sum'] or 0
```

**Data Flow Diagram (Current - Broken):**
```
Tournament ends
  ↓
TournamentResult created (winner = Registration X)
  ↓
❌ NOTHING updates user's tournament count
❌ NOTHING records "User played this tournament"
❌ Stats remain zero forever
```

---

## 2. TARGET ARCHITECTURE

### 2.1 Event-Sourced Activity Model

**Philosophy:** Every significant user action creates an immutable event record.

**UserActivity Model (Append-Only Event Log):**
```python
class UserActivity(models.Model):
    """
    Immutable audit trail of all user actions.
    Event-sourced architecture: all stats derived from this ledger.
    """
    # WHO
    user = ForeignKey(User, on_delete=PROTECT, db_index=True)
    
    # WHAT (Event Type)
    event_type = CharField(choices=EventType.choices, max_length=50, db_index=True)
    # Examples: TOURNAMENT_JOINED, TOURNAMENT_COMPLETED, MATCH_PLAYED, 
    #           MATCH_WON, MATCH_LOST, COINS_EARNED, COINS_SPENT,
    #           ACHIEVEMENT_UNLOCKED, TEAM_CREATED, TEAM_JOINED
    
    # WHEN
    timestamp = DateTimeField(auto_now_add=True, db_index=True)
    
    # WHY / CONTEXT
    metadata = JSONField(default=dict, help_text="Event-specific data")
    # Example for TOURNAMENT_JOINED:
    # {
    #   "tournament_id": 42,
    #   "tournament_name": "Winter Championship",
    #   "registration_id": 123,
    #   "entry_fee": 100
    # }
    
    # SOURCE (Traceability)
    source_model = CharField(max_length=50, null=True, blank=True)
    source_id = IntegerField(null=True, blank=True, db_index=True)
    # Example: source_model='Registration', source_id=123
    
    # IMMUTABILITY
    created_at = DateTimeField(auto_now_add=True)
    # NO updated_at field (append-only, never modify)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['source_model', 'source_id']),
        ]
        permissions = [
            ('view_activity_feed', 'Can view activity feed'),
        ]
```

**EventType Choices (Initial Set - 15 Types):**
```python
class EventType(models.TextChoices):
    # Tournament Events (6)
    TOURNAMENT_REGISTERED = 'tournament_registered', 'Registered for Tournament'
    TOURNAMENT_JOINED = 'tournament_joined', 'Tournament Started (Check-in Complete)'
    TOURNAMENT_COMPLETED = 'tournament_completed', 'Tournament Finished'
    TOURNAMENT_WON = 'tournament_won', 'Won Tournament (1st Place)'
    TOURNAMENT_RUNNER_UP = 'tournament_runner_up', 'Tournament Runner-Up (2nd)'
    TOURNAMENT_TOP4 = 'tournament_top4', 'Tournament Top 4 Placement'
    
    # Match Events (3)
    MATCH_PLAYED = 'match_played', 'Played Match'
    MATCH_WON = 'match_won', 'Won Match'
    MATCH_LOST = 'match_lost', 'Lost Match'
    
    # Economy Events (2)
    COINS_EARNED = 'coins_earned', 'Earned DeltaCoins'
    COINS_SPENT = 'coins_spent', 'Spent DeltaCoins'
    
    # Achievement Events (1)
    ACHIEVEMENT_UNLOCKED = 'achievement_unlocked', 'Unlocked Achievement'
    
    # Team Events (3)
    TEAM_CREATED = 'team_created', 'Created Team'
    TEAM_JOINED = 'team_joined', 'Joined Team'
    TEAM_LEFT = 'team_left', 'Left Team'
```

**Why Immutable Events (Not Mutable Stats)?**
1. **Audit Trail:** Can replay history to verify stats
2. **Debugging:** "Why is user's tournament count 42?" → Query events
3. **Compliance:** GDPR requires ability to export user history
4. **Analytics:** Can aggregate events by time period (monthly stats)
5. **Dispute Resolution:** "I won but stats say 0" → Check events
6. **Idempotent Recomputation:** Can recalculate stats from events anytime

---

### 2.2 Derived Stats Projection

**UserProfileStats Model (1-to-1 with UserProfile):**
```python
class UserProfileStats(models.Model):
    """
    Derived projection of user stats computed from UserActivity events.
    NEVER manually mutated - always updated via signals/services.
    """
    profile = OneToOneField(UserProfile, on_delete=CASCADE, related_name='stats')
    
    # Tournament Stats (Authoritative Counts)
    tournaments_registered = IntegerField(default=0)  # Registered but not started
    tournaments_played = IntegerField(default=0)      # Actually participated
    tournaments_completed = IntegerField(default=0)   # Finished to end
    tournaments_won = IntegerField(default=0)         # 1st place
    tournaments_runner_up = IntegerField(default=0)   # 2nd place
    tournaments_top4 = IntegerField(default=0)        # 3rd/4th place
    
    # Match Stats (Authoritative Counts)
    matches_played = IntegerField(default=0)
    matches_won = IntegerField(default=0)
    matches_lost = IntegerField(default=0)
    
    # Economy Stats (Authoritative Aggregates)
    total_earned = IntegerField(default=0)  # Sum of COINS_EARNED events
    total_spent = IntegerField(default=0)   # Sum of COINS_SPENT events
    
    # Achievement Stats
    achievements_count = IntegerField(default=0)
    
    # Team Stats
    teams_created = IntegerField(default=0)
    teams_joined = IntegerField(default=0)
    current_teams_count = IntegerField(default=0)
    
    # Computed Properties (NOT stored)
    @property
    def win_rate(self) -> Decimal:
        """Computed: matches_won / matches_played (0 if no matches)"""
        if self.matches_played == 0:
            return Decimal('0.00')
        return Decimal(self.matches_won) / Decimal(self.matches_played)
    
    @property
    def tournament_win_rate(self) -> Decimal:
        """Computed: tournaments_won / tournaments_played"""
        if self.tournaments_played == 0:
            return Decimal('0.00')
        return Decimal(self.tournaments_won) / Decimal(self.tournaments_played)
    
    @property
    def net_earnings(self) -> int:
        """Computed: total_earned - total_spent"""
        return self.total_earned - self.total_spent
    
    # Metadata
    last_activity_at = DateTimeField(null=True, blank=True)
    stats_updated_at = DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Profile Stats"
        indexes = [
            models.Index(fields=['tournaments_won', '-tournaments_played']),
            models.Index(fields=['matches_won', '-matches_played']),
        ]
```

---

### 2.3 Source Models (Where Events Come From)

**Tournament Participation Tracking:**
```python
# apps/tournaments/models/registration.py (EXISTING)
class Registration(models.Model):
    tournament = ForeignKey(Tournament)
    user = ForeignKey(User)
    status = CharField(choices=STATUS_CHOICES)  # confirmed, no_show, etc.
    checked_in = BooleanField(default=False)
    
    # Events to generate:
    # - On create: TOURNAMENT_REGISTERED (if status=confirmed)
    # - On checked_in=True: TOURNAMENT_JOINED
    # - When tournament ends: TOURNAMENT_COMPLETED
```

**Match Participation Tracking:**
```python
# apps/tournaments/models/match.py (EXISTING)
class Match(models.Model):
    tournament = ForeignKey(Tournament)
    participant1_id = IntegerField()  # Registration ID (can be user or team)
    participant2_id = IntegerField()
    winner_id = IntegerField(null=True)
    loser_id = IntegerField(null=True)
    state = CharField(choices=STATE_CHOICES)  # completed, forfeit, etc.
    
    # Events to generate:
    # - On state='completed': 
    #   - MATCH_PLAYED (both participants)
    #   - MATCH_WON (winner)
    #   - MATCH_LOST (loser)
```

**Tournament Result Tracking:**
```python
# apps/tournaments/models/result.py (EXISTING)
class TournamentResult(models.Model):
    tournament = ForeignKey(Tournament)
    winner = ForeignKey(Registration, related_name='won_tournaments')
    runner_up = ForeignKey(Registration, null=True)
    third_place = ForeignKey(Registration, null=True)
    
    # Events to generate:
    # - On create:
    #   - TOURNAMENT_WON (winner.user)
    #   - TOURNAMENT_RUNNER_UP (runner_up.user)
    #   - TOURNAMENT_TOP4 (third_place.user + semi-final losers)
```

**Economy Transaction Tracking:**
```python
# apps/economy/models.py (EXISTING)
class DeltaCrownTransaction(models.Model):
    wallet = ForeignKey(DeltaCrownWallet)
    amount = IntegerField()  # Positive = earn, Negative = spend
    reason = CharField(choices=Reason.choices)
    
    # Events to generate:
    # - On create:
    #   - COINS_EARNED (if amount > 0)
    #   - COINS_SPENT (if amount < 0)
```

---

### 2.4 Data Flow (Event-Sourced Architecture)

**Example: Tournament Completion Flow**

```
1. Tournament State Machine: tournament.status = 'COMPLETED'
   ↓
2. WinnerDeterminationService.determine_winner() runs
   ↓
3. TournamentResult.objects.create(
      tournament=t,
      winner=reg_winner,
      runner_up=reg_runner_up
   )
   ↓
4. SIGNAL: post_save(TournamentResult) fires
   ↓
5. UserActivityService.record_tournament_result(result) called
   ↓
6. Events created (3-5 events):
   - UserActivity.objects.create(
       user=reg_winner.user,
       event_type='TOURNAMENT_WON',
       metadata={'tournament_id': t.id, 'placement': 1},
       source_model='TournamentResult',
       source_id=result.id
     )
   - UserActivity.objects.create(
       user=reg_runner_up.user,
       event_type='TOURNAMENT_RUNNER_UP',
       metadata={'tournament_id': t.id, 'placement': 2}
     )
   - UserActivity.objects.create(
       user=all_participants[...],
       event_type='TOURNAMENT_COMPLETED',
       metadata={'tournament_id': t.id}
     )
   ↓
7. SIGNAL: post_save(UserActivity) fires
   ↓
8. StatsUpdateService.increment_stat(user, 'tournaments_won', delta=1)
   ↓
9. UserProfileStats.objects.filter(profile__user=user).update(
      tournaments_won=F('tournaments_won') + 1
   )
   ↓
10. ✅ Stats updated atomically, events recorded immutably
```

**Key Guarantees:**
- ✅ Every stat change has corresponding event
- ✅ Events never deleted (immutable audit trail)
- ✅ Stats can be recomputed from events (idempotent)
- ✅ F() expressions prevent race conditions
- ✅ Signals fire transactionally (all-or-nothing)

---

## 3. SCALABILITY ANALYSIS

### 3.1 Event Volume Projections

**Assumptions:**
- 10,000 active users
- Each user plays 2 tournaments/month
- Each tournament has 4 matches average
- 50% economy transaction rate

**Monthly Event Volume:**
```
Tournament Events:
- TOURNAMENT_REGISTERED: 10K users × 2 = 20,000/month
- TOURNAMENT_JOINED: 90% check-in rate = 18,000/month
- TOURNAMENT_COMPLETED: Same as joined = 18,000/month
- TOURNAMENT_WON/RUNNER_UP/TOP4: 2K + 2K + 4K = 8,000/month

Match Events:
- MATCH_PLAYED: 20K tournaments × 4 matches × 2 participants = 160,000/month
- MATCH_WON/LOST: 80,000 + 80,000 = 160,000/month

Economy Events:
- COINS_EARNED: 20K tournaments × 2 participants = 40,000/month
- COINS_SPENT: 50% × 10K users = 5,000/month

TOTAL: ~500,000 events/month (~6M events/year)
```

**Database Impact:**
- Event table size: 6M rows/year × 500 bytes/row = 3 GB/year
- With indexes: ~10 GB/year
- **Verdict: EASILY scalable** (PostgreSQL handles 100M+ rows)

---

### 3.2 Query Performance

**Critical Query Patterns:**

1. **Activity Feed (Last 50 events)**
```sql
SELECT * FROM user_profile_useractivity
WHERE user_id = <user_id>
ORDER BY timestamp DESC
LIMIT 50;

-- Index used: (user_id, timestamp DESC)
-- Query time: <5ms (indexed, small result set)
```

2. **Stats Lookup (Cached in UserProfileStats)**
```sql
SELECT tournaments_won, matches_won, total_earned
FROM user_profile_userprofilestats
WHERE profile_id = <profile_id>;

-- Query time: <1ms (single row, primary key lookup)
```

3. **Event Count by Type (Analytics)**
```sql
SELECT event_type, COUNT(*)
FROM user_profile_useractivity
WHERE user_id = <user_id>
  AND timestamp >= NOW() - INTERVAL '30 days'
GROUP BY event_type;

-- Index used: (user_id, event_type, timestamp)
-- Query time: <10ms (composite index covers query)
```

**Performance Strategy:**
- ✅ Pre-aggregate stats in UserProfileStats (avoid COUNT() queries)
- ✅ Use composite indexes for common filters
- ✅ Paginate activity feed (50 events per page)
- ✅ Archive events older than 2 years (move to cold storage)

---

### 3.3 Write Performance

**Bottleneck Analysis:**
- Event creation: ~500K writes/month = ~200 writes/hour average
- Peak load (tournament end): 500 events in 1 minute = 8.3 writes/second
- **Verdict: NO BOTTLENECK** (PostgreSQL handles 10K+ writes/sec)

**Optimization Strategies:**
1. **Batch Event Creation:**
```python
UserActivity.objects.bulk_create([
    UserActivity(user=u1, event_type='MATCH_PLAYED', ...),
    UserActivity(user=u2, event_type='MATCH_PLAYED', ...),
    # ... 100 events
], batch_size=100)
```

2. **Async Event Processing (Optional):**
```python
# If real-time not required, use Celery task
@shared_task
def record_tournament_completion(tournament_id):
    # Create events asynchronously
    # Update stats in background
    pass
```

3. **Deferred Stats Update (Optional):**
```python
# Update stats every 5 minutes instead of real-time
# Trade-off: Slight delay vs reduced DB load
```

**Recommended Approach (UP-M2):**
- ✅ Synchronous event creation (real-time accuracy)
- ✅ Immediate stats update (F() expressions are fast)
- ⏸️ Defer async optimization to UP-M4 (if needed)

---

## 4. ARCHITECTURAL DECISIONS

### ADR-UP-011: Event-Sourced User Activity Model

**Context:**
- Current stats (tournaments_played, matches_won) don't exist
- No historical record of user actions
- Expensive aggregation queries on every page load
- Cannot audit "how did user's stats become X?"

**Decision:**
Implement event-sourced architecture with:
1. **UserActivity:** Immutable event log (append-only)
2. **UserProfileStats:** Derived projection (updated via signals)
3. **Idempotent Recomputation:** Can rebuild stats from events

**Alternatives Considered:**

**Alternative 1: Direct Stats Mutation (NO EVENTS)**
```python
# On tournament win:
profile.tournaments_won += 1
profile.save()
```
**Pros:** Simple, fast  
**Cons:** No audit trail, can't verify correctness, lost data if bug  
**Rejected:** Cannot debug or recover from errors

**Alternative 2: Denormalized Stats on Registration/Match Models**
```python
# Add fields to Match model:
class Match(models.Model):
    participant1_wins = IntegerField()
    participant2_wins = IntegerField()
```
**Pros:** No new models  
**Cons:** Data scattered, hard to aggregate, violates normalization  
**Rejected:** Unmaintainable, poor query performance

**Alternative 3: Event Sourcing + CQRS (Full Microservice)**
```python
# Separate read/write models with event store
# Eventual consistency with message queue
```
**Pros:** Industry best practice, infinite scalability  
**Cons:** Too complex for current scale, operational overhead  
**Rejected:** Over-engineering for 10K users

**Chosen: Pragmatic Event Sourcing (Middle Ground)**
- ✅ Events stored in same database (no microservice complexity)
- ✅ Synchronous stats update (no eventual consistency issues)
- ✅ Can add async processing later if needed
- ✅ Scales to 1M users without changes

---

### ADR-UP-012: Stats as Derived Projection (Not Source)

**Context:**
- Stats fields exist on UserProfile but never updated
- Unclear if stats are source of truth or cache
- No sync mechanism between events and stats

**Decision:**
UserProfileStats fields are **DERIVED PROJECTIONS** (not source):
- Source of truth: UserActivity events
- Stats = materialized view of event aggregates
- Stats NEVER manually updated (only via signals)
- Can rebuild stats by re-aggregating events

**Implementation Rules:**
```python
# ✅ CORRECT: Update via service
StatsUpdateService.increment_stat(user, 'tournaments_won', delta=1)

# ❌ WRONG: Direct mutation
profile.stats.tournaments_won += 1  # FORBIDDEN

# ✅ CORRECT: Recompute from events
stats = recompute_stats_from_events(user)
UserProfileStats.objects.update_or_create(
    profile=user.profile,
    defaults=stats
)
```

**Benefits:**
- ✅ Stats always verifiable (compare to event aggregates)
- ✅ Can fix incorrect stats by recomputation
- ✅ No "stats drift" problem (economy sync issue avoided)
- ✅ Audit trail for compliance (GDPR data export)

---

## 5. INTEGRATION POINTS

### 5.1 Tournament System Integration

**Signals to Hook:**
```python
# apps/tournaments/signals.py
from django.db.models.signals import post_save
from apps.tournaments.models import Registration, Match, TournamentResult
from apps.user_profile.services.activity_service import UserActivityService

@receiver(post_save, sender=Registration)
def on_registration_confirmed(sender, instance, created, **kwargs):
    if created and instance.status == Registration.CONFIRMED:
        UserActivityService.record_tournament_registration(instance)

@receiver(post_save, sender=Match)
def on_match_completed(sender, instance, created, **kwargs):
    if instance.state == Match.COMPLETED and not created:
        UserActivityService.record_match_result(instance)

@receiver(post_save, sender=TournamentResult)
def on_tournament_result_created(sender, instance, created, **kwargs):
    if created:
        UserActivityService.record_tournament_result(instance)
```

---

### 5.2 Economy System Integration

**Signal Hook:**
```python
# apps/economy/signals.py
from django.db.models.signals import post_save
from apps.economy.models import DeltaCrownTransaction
from apps.user_profile.services.activity_service import UserActivityService

@receiver(post_save, sender=DeltaCrownTransaction)
def on_transaction_created(sender, instance, created, **kwargs):
    if created:
        UserActivityService.record_economy_transaction(instance)
```

---

### 5.3 Team System Integration (Future)

**Deferred to UP-M4 (Team Stats):**
- TEAM_CREATED event
- TEAM_JOINED event
- TEAM_LEFT event

---

## 6. DATA INTEGRITY GUARANTEES

### 6.1 Event Immutability

**Constraints:**
```python
# Model design prevents updates
class UserActivity(models.Model):
    # NO updated_at field (signal would be: only created_at)
    # NO soft delete (is_deleted field)
    # NO admin edit permission
    
    class Meta:
        permissions = [
            ('view_activity_feed', 'Can view activity feed'),
            # INTENTIONALLY NO 'change_activity' or 'delete_activity'
        ]
```

**Admin Configuration:**
```python
# apps/user_profile/admin.py
@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'event_type', 'timestamp']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['user__username', 'metadata']
    readonly_fields = ['user', 'event_type', 'timestamp', 'metadata', 'source_model', 'source_id']
    
    def has_add_permission(self, request):
        return False  # No manual creation
    
    def has_change_permission(self, request, obj=None):
        return False  # No editing
    
    def has_delete_permission(self, request, obj=None):
        return False  # No deletion
```

---

### 6.2 Stats Consistency Checks

**Reconciliation Command:**
```python
# apps/user_profile/management/commands/reconcile_user_stats.py
class Command(BaseCommand):
    help = "Verify UserProfileStats matches UserActivity events"
    
    def handle(self, *args, **options):
        for profile in UserProfile.objects.all():
            # Compute expected stats from events
            expected = self.compute_stats_from_events(profile.user)
            
            # Compare with current stats
            current = profile.stats
            
            # Detect drift
            if expected != current:
                self.stdout.write(self.style.WARNING(
                    f"DRIFT DETECTED: {profile.user.username}"
                ))
                self.stdout.write(f"  Expected: {expected}")
                self.stdout.write(f"  Current: {current}")
                
                # Auto-repair (optional flag)
                if options['fix']:
                    current.tournaments_won = expected['tournaments_won']
                    # ... update all fields
                    current.save()
                    self.stdout.write(self.style.SUCCESS("  FIXED"))
```

**Scheduled Reconciliation:**
```python
# Run nightly at 3 AM UTC
# crontab: 0 3 * * * cd /app && python manage.py reconcile_user_stats --fix
```

---

## 7. PRIVACY & COMPLIANCE

### 7.1 GDPR Considerations

**Data Export (Article 15):**
```python
# apps/user_profile/services/data_export.py
def export_user_activity(user):
    """
    Export all user events for GDPR data portability request.
    """
    events = UserActivity.objects.filter(user=user).values(
        'event_type', 'timestamp', 'metadata'
    )
    
    return {
        'user_id': user.id,
        'username': user.username,
        'events_count': events.count(),
        'events': list(events),
        'stats': {
            'tournaments_played': user.profile.stats.tournaments_played,
            'tournaments_won': user.profile.stats.tournaments_won,
            # ... all stats
        }
    }
```

**Data Deletion (Article 17 - Right to be Forgotten):**
```python
# When user requests account deletion:
# 1. Anonymize UserActivity events (replace user_id with AnonymousUser)
# 2. Delete UserProfileStats (cascade delete)
# 3. Keep events for audit trail (anonymized)

UserActivity.objects.filter(user=user).update(
    user=AnonymousUser.get_or_create(),
    metadata=F('metadata').update({'user_anonymized': True})
)
```

---

## 8. TESTING STRATEGY

### 8.1 Event Creation Tests (8 tests)

```python
# tests/test_activity_service.py
def test_tournament_registration_creates_event():
    """TOURNAMENT_REGISTERED event created on confirmed registration"""
    
def test_match_completion_creates_three_events():
    """MATCH_PLAYED, MATCH_WON, MATCH_LOST events for both participants"""
    
def test_tournament_result_creates_placement_events():
    """TOURNAMENT_WON, RUNNER_UP, TOP4 events based on placements"""
    
def test_economy_transaction_creates_earn_or_spend_event():
    """COINS_EARNED or COINS_SPENT based on transaction amount"""
    
def test_event_immutability():
    """Events cannot be modified after creation"""
    
def test_duplicate_event_prevention():
    """Idempotency: same source_model + source_id = no duplicate events"""
    
def test_event_metadata_contains_required_fields():
    """All events have tournament_id/match_id/amount in metadata"""
    
def test_concurrent_event_creation_no_conflicts():
    """10 threads creating events simultaneously = no deadlocks"""
```

---

### 8.2 Stats Update Tests (12 tests)

```python
# tests/test_stats_service.py
def test_tournament_won_increments_stat():
    """TOURNAMENT_WON event → tournaments_won += 1"""
    
def test_match_won_increments_two_stats():
    """MATCH_WON event → matches_played += 1, matches_won += 1"""
    
def test_f_expression_prevents_race_condition():
    """10 concurrent updates → final count = 10 (not lost updates)"""
    
def test_stats_recomputation_matches_events():
    """recompute_stats_from_events() = current stats value"""
    
def test_win_rate_computed_property_accurate():
    """win_rate = matches_won / matches_played (0% to 100%)"""
    
def test_total_earned_matches_economy_ledger():
    """total_earned = sum(COINS_EARNED event amounts)"""
    
def test_zero_matches_played_win_rate_zero():
    """Edge case: 0 matches → win_rate = 0% (not division error)"""
    
def test_stats_update_atomic_with_event_creation():
    """Event + Stats update in single transaction (all-or-nothing)"""
    
def test_multiple_tournaments_cumulative_count():
    """3 tournaments → tournaments_played = 3 (not 1)"""
    
def test_negative_stats_impossible():
    """tournaments_won cannot go negative (constraint violation)"""
    
def test_stats_drift_detection():
    """Reconciliation command detects mismatched stats"""
    
def test_stats_auto_repair():
    """reconcile_user_stats --fix corrects drifted stats"""
```

---

### 8.3 Integration Tests (10 tests)

```python
# tests/test_integration_tournament.py
def test_end_to_end_tournament_completion():
    """
    Full workflow:
    1. User registers (TOURNAMENT_REGISTERED)
    2. Tournament starts (TOURNAMENT_JOINED)
    3. User plays matches (MATCH_PLAYED × 4)
    4. User wins tournament (TOURNAMENT_WON)
    5. User earns coins (COINS_EARNED)
    
    Assert:
    - 7 events created
    - tournaments_won = 1
    - matches_won = 4
    - total_earned = prize amount
    """
    
def test_backfill_historical_tournaments():
    """
    Given: 10 completed tournaments (before UP-M2)
    When: Run backfill_user_activity command
    Then: 10 TOURNAMENT_COMPLETED events created
    """
    
def test_concurrent_tournament_completions():
    """
    2 tournaments complete simultaneously
    → 2 TOURNAMENT_WON events, no conflicts
    """
    
def test_economy_sync_with_activity():
    """
    Prize awarded → COINS_EARNED event → total_earned updated
    """
    
def test_no_show_registration_no_events():
    """
    Registration with status=NO_SHOW → no TOURNAMENT_JOINED event
    """
    
def test_forfeit_match_creates_played_not_won():
    """
    Match forfeit → MATCH_PLAYED event (no MATCH_WON)
    """
    
def test_disputed_match_result_handled():
    """
    Match result disputed → original events remain (immutable)
    → Resolution creates new events (if result changes)
    """
    
def test_team_tournament_events_include_all_members():
    """
    Team wins tournament → TOURNAMENT_WON event for all 5 members
    """
    
def test_stats_query_performance_under_load():
    """
    1000 users × 50 events each = 50K events
    → stats lookup < 10ms (cached in UserProfileStats)
    """
    
def test_activity_feed_pagination():
    """
    User has 1000 events → paginate 50 per page, no N+1 queries
    """
```

---

## 9. ROLLOUT PLAN

### Phase 1: Models & Migrations (Day 1)
- ✅ Create UserActivity model
- ✅ Create UserProfileStats model
- ✅ Generate migrations
- ✅ Apply to dev database

### Phase 2: Event Recording Service (Day 1)
- ✅ Create UserActivityService
- ✅ Implement record_tournament_registration()
- ✅ Implement record_match_result()
- ✅ Implement record_tournament_result()
- ✅ Implement record_economy_transaction()
- ✅ Unit tests for service methods

### Phase 3: Stats Update Service (Day 2)
- ✅ Create StatsUpdateService
- ✅ Implement increment_stat(user, field, delta)
- ✅ Implement recompute_stats_from_events(user)
- ✅ Connect signals to services
- ✅ Unit tests for stats updates

### Phase 4: Backfill Historical Data (Day 2)
- ✅ Create backfill_user_activity management command
- ✅ Scan Registration model → TOURNAMENT_REGISTERED events
- ✅ Scan Match model → MATCH_PLAYED/WON/LOST events
- ✅ Scan TournamentResult → TOURNAMENT_WON/RUNNER_UP events
- ✅ Scan DeltaCrownTransaction → COINS_EARNED/SPENT events
- ✅ Recompute all UserProfileStats from events
- ✅ Test idempotency (run twice = same result)

### Phase 5: Query Helpers & APIs (Day 3)
- ✅ Implement last_50_activities(user)
- ✅ Implement lifetime_stats(user)
- ✅ Implement tournament_history(user)
- ✅ Implement economy_summary(user)
- ✅ Add views for activity feed page
- ✅ Update profile template to show stats

### Phase 6: Reconciliation & Monitoring (Day 3)
- ✅ Create reconcile_user_stats command
- ✅ Schedule nightly cron job
- ✅ Add Grafana dashboard for event volume
- ✅ Add alerts for stats drift

---

## 10. SUCCESS METRICS

**Code Quality:**
- ✅ 95%+ test coverage on new code
- ✅ All tests pass (30+ new tests)
- ✅ No regressions in existing tests

**Data Quality:**
- ✅ 100% of users have UserProfileStats record
- ✅ 100% of completed tournaments have events
- ✅ 0 stats drift errors after reconciliation

**Performance:**
- ✅ Stats lookup < 10ms (cached)
- ✅ Activity feed < 50ms (paginated)
- ✅ Event creation < 20ms (batch inserts)

**Operational:**
- ✅ Backfill completes in < 10 minutes
- ✅ Reconciliation runs nightly without errors
- ✅ Zero manual stat corrections needed

---

## 11. FUTURE ENHANCEMENTS (UP-M4+)

**UP-M4: Advanced Analytics**
- Monthly/yearly stats (time-series aggregation)
- Skill rating trends over time
- Performance heatmaps (win rate by game/day)

**UP-M5: Social Features**
- Activity feed for followed users
- Achievement unlocks in feed
- Social sharing of milestones

**UP-M6: Machine Learning**
- Predict tournament performance from history
- Recommend tournaments based on past participation
- Detect skill progression patterns

---

## DOCUMENT STATUS

**Review Checklist:**
- ✅ Event model design complete
- ✅ Stats model design complete
- ✅ Integration points identified
- ✅ Scalability analysis complete
- ✅ Testing strategy defined
- ✅ Rollout plan documented

**Approvals Required:**
- [ ] Engineering Manager (architecture review)
- [ ] Product Owner (feature scope approval)
- [ ] DBA (database schema review)

**Next Steps:**
1. Create UP_M2_DATA_MODEL.md (detailed schema)
2. Create UP_M2_EXECUTION_PLAN.md (step-by-step implementation)
3. Create UP_M2_RISKS_AND_MITIGATIONS.md (risk analysis)
4. Begin implementation after approval

---

**END OF DOCUMENT**
