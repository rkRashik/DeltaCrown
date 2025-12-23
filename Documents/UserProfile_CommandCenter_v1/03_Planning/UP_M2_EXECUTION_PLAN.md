# UP-M2: EXECUTION PLAN

**Document:** Step-by-step implementation order with verification gates  
**Created:** December 23, 2025  
**Estimated Duration:** 3 days

---

## PHASE 1: MODELS & MIGRATIONS (Day 1, Morning - 4 hours)

### Step 1.1: Create UserActivity Model
**File:** `apps/user_profile/models/activity.py`
**Tasks:**
- Define EventType choices (15 event types)
- Create UserActivity model with fields (user, event_type, timestamp, metadata, source_model/id)
- Add indexes (5 indexes for common query patterns)
- Add unique constraint (source_model + source_id + event_type)
- Override save() to enforce immutability
- Override delete() to prevent deletion

**Verification:**
```bash
python manage.py check
python manage.py makemigrations user_profile --name add_user_activity --dry-run
```

### Step 1.2: Create UserProfileStats Model  
**File:** `apps/user_profile/models/stats.py`
**Tasks:**
- Create UserProfileStats model (1-to-1 with UserProfile)
- Add 17 stat fields (tournaments, matches, economy, achievements, teams)
- Add 7 computed @property methods (win_rate, net_earnings, etc.)
- Add check constraints (non-negative, logical constraints)
- Add 4 indexes for leaderboards
- Implement to_dict() method for API serialization

**Verification:**
```bash
python manage.py makemigrations user_profile --name add_user_profile_stats --dry-run
```

### Step 1.3: Generate & Apply Migrations
```bash
python manage.py makemigrations user_profile
python manage.py migrate user_profile
```

**Verification SQL:**
```sql
-- Verify tables created
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('user_profile_useractivity', 'user_profile_userprofilestats');

-- Verify indexes
SELECT indexname FROM pg_indexes 
WHERE tablename = 'user_profile_useractivity';
```

### Step 1.4: Create Stats for Existing Profiles
```bash
python manage.py shell
>>> from apps.user_profile.models import UserProfile, UserProfileStats
>>> UserProfileStats.objects.bulk_create([
...     UserProfileStats(profile=p) for p in UserProfile.objects.filter(stats__isnull=True)
... ])
```

**Gate 1: Models Created**
- ✅ UserActivity table exists
- ✅ UserProfileStats table exists
- ✅ All indexes created
- ✅ All constraints applied
- ✅ Every UserProfile has stats record

---

## PHASE 2: EVENT RECORDING SERVICE (Day 1, Afternoon - 4 hours)

### Step 2.1: Create UserActivityService
**File:** `apps/user_profile/services/activity_service.py`

**Methods to implement:**
```python
class UserActivityService:
    @staticmethod
    def record_event(user, event_type, metadata, source_model=None, source_id=None):
        """Base method for event creation with idempotency"""
    
    @staticmethod
    def record_tournament_registration(registration):
        """TOURNAMENT_REGISTERED event"""
    
    @staticmethod
    def record_tournament_start(registration):
        """TOURNAMENT_JOINED event (when checked-in)"""
    
    @staticmethod
    def record_tournament_completion(tournament, all_registrations):
        """TOURNAMENT_COMPLETED events for all participants"""
    
    @staticmethod
    def record_tournament_result(tournament_result):
        """TOURNAMENT_WON, RUNNER_UP, TOP4 events"""
    
    @staticmethod
    def record_match_result(match):
        """MATCH_PLAYED, MATCH_WON, MATCH_LOST events"""
    
    @staticmethod
    def record_economy_transaction(transaction):
        """COINS_EARNED or COINS_SPENT events"""
```

**Verification (Unit Tests):**
```bash
pytest apps/user_profile/tests/test_activity_service.py -v
```

**Tests to create (8 tests):**
- test_record_event_creates_activity
- test_idempotency_prevents_duplicate_events
- test_tournament_registration_event
- test_match_completion_creates_three_events
- test_tournament_result_creates_placement_events
- test_economy_transaction_creates_earn_spend_events
- test_immutability_prevents_update
- test_concurrent_event_creation_no_conflicts

**Gate 2: Event Service Complete**
- ✅ All 7 service methods implemented
- ✅ 8/8 unit tests passing
- ✅ Idempotency verified
- ✅ No duplicate events created

---

## PHASE 3: STATS UPDATE SERVICE (Day 2, Morning - 4 hours)

### Step 3.1: Create StatsUpdateService
**File:** `apps/user_profile/services/stats_service.py`

**Methods to implement:**
```python
class StatsUpdateService:
    @staticmethod
    def increment_stat(user, field_name, delta=1):
        """Atomically increment stat field using F() expression"""
    
    @staticmethod
    def update_last_activity(user, timestamp):
        """Update last_activity_at field"""
    
    @staticmethod
    def recompute_stats_from_events(user):
        """Recompute all stats by aggregating UserActivity events"""
    
    @staticmethod
    def handle_tournament_registered_event(event):
        """tournaments_registered += 1"""
    
    @staticmethod
    def handle_tournament_joined_event(event):
        """tournaments_played += 1"""
    
    @staticmethod
    def handle_tournament_completed_event(event):
        """tournaments_completed += 1"""
    
    @staticmethod
    def handle_tournament_won_event(event):
        """tournaments_won += 1"""
    
    @staticmethod
    def handle_match_played_event(event):
        """matches_played += 1"""
    
    @staticmethod
    def handle_match_won_event(event):
        """matches_won += 1, matches_played += 1"""
    
    @staticmethod
    def handle_match_lost_event(event):
        """matches_lost += 1"""
    
    @staticmethod
    def handle_coins_earned_event(event):
        """total_earned += amount"""
    
    @staticmethod
    def handle_coins_spent_event(event):
        """total_spent += abs(amount)"""
```

### Step 3.2: Connect Signals
**File:** `apps/user_profile/signals.py`

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.user_profile.models import UserActivity
from apps.user_profile.services.stats_service import StatsUpdateService

@receiver(post_save, sender=UserActivity)
def on_activity_created(sender, instance, created, **kwargs):
    """Update stats when new activity event created"""
    if not created:
        return  # Only process new events
    
    # Route to appropriate handler based on event_type
    handler_map = {
        'tournament_registered': StatsUpdateService.handle_tournament_registered_event,
        'tournament_joined': StatsUpdateService.handle_tournament_joined_event,
        'tournament_won': StatsUpdateService.handle_tournament_won_event,
        'match_played': StatsUpdateService.handle_match_played_event,
        'match_won': StatsUpdateService.handle_match_won_event,
        # ... all event types
    }
    
    handler = handler_map.get(instance.event_type)
    if handler:
        handler(instance)
    
    # Update last_activity_at
    StatsUpdateService.update_last_activity(instance.user, instance.timestamp)
```

**Verification (Unit Tests):**
```bash
pytest apps/user_profile/tests/test_stats_service.py -v
```

**Tests to create (12 tests):**
- test_increment_stat_uses_f_expression
- test_tournament_won_increments_stat
- test_match_won_increments_two_stats
- test_recompute_stats_matches_events
- test_f_expression_prevents_race_condition
- test_stats_update_atomic_with_event
- test_win_rate_computed_correctly
- test_zero_matches_win_rate_zero
- test_negative_stats_impossible
- test_concurrent_updates_no_lost_writes
- test_multiple_tournaments_cumulative
- test_stats_drift_detection

**Gate 3: Stats Service Complete**
- ✅ All 12 service methods implemented
- ✅ 12/12 unit tests passing
- ✅ Signal connected and working
- ✅ F() expressions used (no race conditions)
- ✅ Stats update transactionally with events

---

## PHASE 4: INTEGRATION WITH EXISTING SYSTEMS (Day 2, Afternoon - 4 hours)

### Step 4.1: Hook Tournament System
**File:** `apps/tournaments/signals.py`

```python
from apps.user_profile.services.activity_service import UserActivityService

@receiver(post_save, sender=Registration)
def on_registration_created(sender, instance, created, **kwargs):
    if created and instance.status == Registration.CONFIRMED:
        UserActivityService.record_tournament_registration(instance)

@receiver(post_save, sender=Registration)
def on_registration_checked_in(sender, instance, created, **kwargs):
    if not created and instance.checked_in:
        UserActivityService.record_tournament_start(instance)

@receiver(post_save, sender=Match)
def on_match_completed(sender, instance, created, **kwargs):
    if instance.state == Match.COMPLETED and not created:
        UserActivityService.record_match_result(instance)

@receiver(post_save, sender=TournamentResult)
def on_tournament_result_created(sender, instance, created, **kwargs):
    if created:
        UserActivityService.record_tournament_result(instance)
```

### Step 4.2: Hook Economy System
**File:** `apps/economy/signals.py`

```python
from apps.user_profile.services.activity_service import UserActivityService

@receiver(post_save, sender=DeltaCrownTransaction)
def on_transaction_created(sender, instance, created, **kwargs):
    if created:
        UserActivityService.record_economy_transaction(instance)
```

**Verification (Integration Tests):**
```bash
pytest tests/integration/test_user_profile_integration.py -v
```

**Tests to create (10 tests):**
- test_end_to_end_tournament_completion
- test_registration_creates_event
- test_match_completion_creates_events
- test_tournament_result_creates_events
- test_economy_transaction_creates_events
- test_stats_updated_after_tournament_win
- test_concurrent_tournament_completions
- test_no_show_registration_no_events
- test_forfeit_match_handled
- test_team_tournament_all_members_events

**Gate 4: Integration Complete**
- ✅ Tournament signals connected
- ✅ Economy signals connected
- ✅ 10/10 integration tests passing
- ✅ End-to-end flow verified

---

## PHASE 5: BACKFILL HISTORICAL DATA (Day 3, Morning - 4 hours)

### Step 5.1: Create Backfill Command
**File:** `apps/user_profile/management/commands/backfill_user_activity.py`

```python
class Command(BaseCommand):
    help = "Backfill UserActivity events from historical data"
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--batch-size', type=int, default=500)
    
    def handle(self, *args, **options):
        # 1. Backfill tournament registrations
        self.backfill_registrations(options)
        
        # 2. Backfill matches
        self.backfill_matches(options)
        
        # 3. Backfill tournament results
        self.backfill_tournament_results(options)
        
        # 4. Backfill economy transactions
        self.backfill_economy_transactions(options)
        
        # 5. Recompute all stats from events
        self.recompute_all_stats(options)
```

**Backfill Logic:**
```python
def backfill_registrations(self, options):
    # Scan all confirmed registrations
    registrations = Registration.objects.filter(status=Registration.CONFIRMED)
    
    events_to_create = []
    for reg in registrations:
        # Skip if event already exists (idempotency)
        exists = UserActivity.objects.filter(
            source_model='Registration',
            source_id=reg.id,
            event_type='tournament_registered'
        ).exists()
        
        if not exists:
            events_to_create.append(UserActivity(
                user=reg.user,
                event_type='tournament_registered',
                timestamp=reg.created_at,
                metadata={'tournament_id': reg.tournament_id, ...},
                source_model='Registration',
                source_id=reg.id
            ))
    
    if not options['dry_run']:
        UserActivity.objects.bulk_create(events_to_create, batch_size=options['batch_size'])
    
    self.stdout.write(self.style.SUCCESS(f"Created {len(events_to_create)} registration events"))
```

**Verification:**
```bash
# Dry run first
python manage.py backfill_user_activity --dry-run

# Apply backfill
python manage.py backfill_user_activity

# Verify idempotency (run again = 0 new events)
python manage.py backfill_user_activity
```

**SQL Verification:**
```sql
-- Check event counts by type
SELECT event_type, COUNT(*) FROM user_profile_useractivity GROUP BY event_type ORDER BY COUNT(*) DESC;

-- Verify all completed tournaments have events
SELECT COUNT(*) FROM tournaments_tournament WHERE status = 'COMPLETED';
SELECT COUNT(DISTINCT metadata->>'tournament_id') FROM user_profile_useractivity WHERE event_type = 'tournament_completed';

-- Verify stats recomputed
SELECT AVG(tournaments_played), AVG(matches_played) FROM user_profile_userprofilestats WHERE tournaments_played > 0;
```

**Gate 5: Backfill Complete**
- ✅ All historical registrations → events
- ✅ All historical matches → events
- ✅ All historical tournaments → events
- ✅ All historical transactions → events
- ✅ All stats recomputed from events
- ✅ Idempotency verified (run twice = same result)

---

## PHASE 6: QUERY HELPERS & VIEWS (Day 3, Afternoon - 4 hours)

### Step 6.1: Create Query Helper Functions
**File:** `apps/user_profile/services/activity_query_service.py`

```python
class ActivityQueryService:
    @staticmethod
    def last_50_activities(user):
        """Recent activity feed for user profile page"""
        return UserActivity.objects.filter(user=user).select_related('user')[:50]
    
    @staticmethod
    def lifetime_stats(user):
        """Get cached stats from UserProfileStats"""
        return user.profile.stats.to_dict()
    
    @staticmethod
    def tournament_history(user, limit=20):
        """All tournament-related events with details"""
        return UserActivity.objects.filter(
            user=user,
            event_type__startswith='tournament_'
        ).order_by('-timestamp')[:limit]
    
    @staticmethod
    def economy_summary(user):
        """Aggregated economy stats with recent transactions"""
        stats = user.profile.stats
        recent_transactions = UserActivity.objects.filter(
            user=user,
            event_type__in=['coins_earned', 'coins_spent']
        ).order_by('-timestamp')[:10]
        
        return {
            'total_earned': stats.total_earned,
            'total_spent': stats.total_spent,
            'net_earnings': stats.net_earnings,
            'recent_transactions': list(recent_transactions.values())
        }
```

### Step 6.2: Create Activity Feed View
**File:** `apps/user_profile/views.py`

```python
class ActivityFeedView(LoginRequiredMixin, ListView):
    model = UserActivity
    template_name = 'user_profile/activity_feed.html'
    context_object_name = 'activities'
    paginate_by = 50
    
    def get_queryset(self):
        return ActivityQueryService.last_50_activities(self.request.user)
```

### Step 6.3: Update Profile Template
**File:** `templates/user_profile/profile.html`

```django
<!-- Stats Summary -->
<div class="stats-grid">
    <div class="stat-card">
        <h3>{{ profile.stats.tournaments_won }}</h3>
        <p>Tournaments Won</p>
        <small>{{ profile.stats.tournament_win_rate_percent }} win rate</small>
    </div>
    <div class="stat-card">
        <h3>{{ profile.stats.matches_won }}</h3>
        <p>Matches Won</p>
        <small>{{ profile.stats.win_rate_percent }} win rate</small>
    </div>
    <div class="stat-card">
        <h3>{{ profile.stats.total_earned|intcomma }} DC</h3>
        <p>Total Earned</p>
        <small>{{ profile.stats.net_earnings|intcomma }} net</small>
    </div>
</div>

<!-- Recent Activity Feed -->
<h2>Recent Activity</h2>
<ul class="activity-feed">
    {% for activity in activities %}
        <li class="activity-item">
            <span class="icon">{% if activity.event_type == 'tournament_won' %}🏆{% endif %}</span>
            <span class="event">{{ activity.get_event_type_display }}</span>
            <span class="time">{{ activity.timestamp|naturaltime }}</span>
        </li>
    {% endfor %}
</ul>
```

**Verification:**
- ✅ Activity feed page loads < 50ms
- ✅ Stats display correctly
- ✅ Pagination works
- ✅ No N+1 queries (verified with django-debug-toolbar)

**Gate 6: Views Complete**
- ✅ 4 query helper methods implemented
- ✅ Activity feed view created
- ✅ Profile template updated with stats
- ✅ Performance benchmarks met

---

## PHASE 7: RECONCILIATION & MONITORING (Day 3, Evening - 2 hours)

### Step 7.1: Create Reconciliation Command
**File:** `apps/user_profile/management/commands/reconcile_user_stats.py`

```python
class Command(BaseCommand):
    help = "Verify and fix stats drift by recomputing from events"
    
    def add_arguments(self, parser):
        parser.add_argument('--fix', action='store_true')
        parser.add_argument('--user-id', type=int)
    
    def handle(self, *args, **options):
        if options['user_id']:
            users = [User.objects.get(id=options['user_id'])]
        else:
            users = User.objects.all()
        
        drift_count = 0
        for user in users:
            expected = StatsUpdateService.recompute_stats_from_events(user)
            current = user.profile.stats
            
            if self.has_drift(expected, current):
                drift_count += 1
                self.stdout.write(self.style.WARNING(f"DRIFT: {user.username}"))
                
                if options['fix']:
                    self.apply_fix(current, expected)
        
        self.stdout.write(self.style.SUCCESS(f"Total drift: {drift_count} users"))
```

### Step 7.2: Schedule Nightly Cron Job
```bash
# crontab -e
0 3 * * * cd /app && python manage.py reconcile_user_stats --fix >> /var/log/stats_reconciliation.log 2>&1
```

### Step 7.3: Add Monitoring Dashboard
**Metrics to track:**
- Event volume per day (by event_type)
- Stats drift count (errors detected by reconciliation)
- Query performance (activity feed P95 latency)
- Backfill progress (events created per run)

**Gate 7: Monitoring Complete**
- ✅ Reconciliation command works
- ✅ Scheduled nightly via cron
- ✅ Grafana dashboard created
- ✅ Alerts configured for drift > 1%

---

## ROLLBACK PLAN

### Rollback Scenarios

**Scenario 1: Models created but not working**
```bash
# Safe rollback: migrations are reversible
python manage.py migrate user_profile 0XXX_before_up_m2
```
**Data Loss:** None (no data in new tables yet)

**Scenario 2: Events created but stats wrong**
```bash
# Keep events, recompute stats
python manage.py shell
>>> from apps.user_profile.models import UserProfileStats
>>> UserProfileStats.objects.all().update(
...     tournaments_played=0,
...     matches_played=0,
...     # ... reset all fields
... )
>>> from apps.user_profile.services.stats_service import StatsUpdateService
>>> for user in User.objects.all():
...     StatsUpdateService.recompute_stats_from_events(user)
```
**Data Loss:** None (events preserved, stats recomputed)

**Scenario 3: Production issue, need to disable**
```python
# Comment out signals in apps/user_profile/signals.py
# @receiver(post_save, sender=UserActivity)
# def on_activity_created(...):
#     pass  # Temporarily disabled
```
**Data Loss:** Events created but stats not updated (drift accumulates, fixable via reconciliation)

---

## DEFINITION OF DONE

**Code Quality:**
- ✅ All 30+ tests passing (8 unit + 12 stats + 10 integration)
- ✅ Test coverage ≥ 95% on new code
- ✅ No pylint/flake8 warnings
- ✅ Type hints on all public methods

**Data Quality:**
- ✅ 100% of users have UserProfileStats record
- ✅ Backfill creates events for all historical data
- ✅ 0 stats drift after reconciliation
- ✅ Idempotency verified (run twice = same result)

**Performance:**
- ✅ Activity feed < 50ms (P95)
- ✅ Stats lookup < 10ms (cached)
- ✅ Event creation < 20ms (batch inserts)
- ✅ Backfill completes < 10 minutes

**Operational:**
- ✅ Reconciliation runs nightly without errors
- ✅ Monitoring dashboard shows event volume
- ✅ Alerts configured for drift/errors
- ✅ Documentation complete (4 docs)

---

## ESTIMATED TIMELINE

| Phase | Duration | Completion Criteria |
|-------|----------|---------------------|
| Phase 1: Models & Migrations | 4 hours | Tables created, all profiles have stats |
| Phase 2: Event Service | 4 hours | 8/8 tests passing, idempotency verified |
| Phase 3: Stats Service | 4 hours | 12/12 tests passing, signals connected |
| Phase 4: Integration | 4 hours | 10/10 integration tests passing |
| Phase 5: Backfill | 4 hours | All historical data → events, stats recomputed |
| Phase 6: Views | 4 hours | Activity feed working, profile shows stats |
| Phase 7: Monitoring | 2 hours | Reconciliation scheduled, dashboard live |
| **TOTAL** | **26 hours (~3 days)** | All gates passed, production-ready |

---

**END OF DOCUMENT**
