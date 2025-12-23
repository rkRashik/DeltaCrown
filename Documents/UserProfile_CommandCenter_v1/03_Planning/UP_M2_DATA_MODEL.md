# UP-M2: DATA MODEL SPECIFICATION

**Document:** Detailed models, fields, indexes, and relationships for User Stats & Activity system  
**Created:** December 23, 2025  
**Status:** 📝 Planning

---

## 1. USER ACTIVITY MODEL (Event Log)

### 1.1 Model Definition

```python
# apps/user_profile/models/activity.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class EventType(models.TextChoices):
    """Event type choices for UserActivity"""
    
    # Tournament Events (6)
    TOURNAMENT_REGISTERED = 'tournament_registered', _('Registered for Tournament')
    TOURNAMENT_JOINED = 'tournament_joined', _('Tournament Started')
    TOURNAMENT_COMPLETED = 'tournament_completed', _('Tournament Finished')
    TOURNAMENT_WON = 'tournament_won', _('Won Tournament (1st)')
    TOURNAMENT_RUNNER_UP = 'tournament_runner_up', _('Runner-Up (2nd)')
    TOURNAMENT_TOP4 = 'tournament_top4', _('Top 4 Placement')
    
    # Match Events (3)
    MATCH_PLAYED = 'match_played', _('Played Match')
    MATCH_WON = 'match_won', _('Won Match')
    MATCH_LOST = 'match_lost', _('Lost Match')
    
    # Economy Events (2)
    COINS_EARNED = 'coins_earned', _('Earned DeltaCoins')
    COINS_SPENT = 'coins_spent', _('Spent DeltaCoins')
    
    # Achievement Events (1)
    ACHIEVEMENT_UNLOCKED = 'achievement_unlocked', _('Unlocked Achievement')
    
    # Team Events (3) - Future: UP-M4
    TEAM_CREATED = 'team_created', _('Created Team')
    TEAM_JOINED = 'team_joined', _('Joined Team')
    TEAM_LEFT = 'team_left', _('Left Team')


class UserActivity(models.Model):
    """
    Immutable event log of all user actions.
    
    Design Principles:
    - Append-only: No updates or deletes allowed
    - Event-sourced: All stats derived from this ledger
    - Auditable: Complete history for compliance (GDPR, disputes)
    - Traceable: source_model + source_id link to origin
    
    Query Patterns:
    - Activity feed: WHERE user_id = X ORDER BY timestamp DESC LIMIT 50
    - Event count: COUNT(*) WHERE user_id = X AND event_type = Y
    - Time range: WHERE timestamp BETWEEN start AND end
    - Source lookup: WHERE source_model = 'Match' AND source_id = 123
    
    Scalability:
    - Estimated 500K events/month (6M/year)
    - Index strategy: Composite indexes for common filters
    - Archive strategy: Move events >2 years to cold storage
    """
    
    # WHO: User performing action
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,  # PROTECT: never cascade delete events
        related_name='activities',
        db_index=True,
        help_text="User who performed the action"
    )
    
    # WHAT: Event type
    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
        db_index=True,
        help_text="Type of event (tournament_won, match_played, etc.)"
    )
    
    # WHEN: Timestamp (auto-set on creation)
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the event occurred (immutable)"
    )
    
    # WHY/CONTEXT: Event-specific metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Event-specific data (tournament_id, match_id, amount, etc.)"
    )
    # Example metadata structures:
    # TOURNAMENT_WON: {"tournament_id": 42, "tournament_name": "...", "placement": 1, "prize": 1000}
    # MATCH_PLAYED: {"match_id": 123, "tournament_id": 42, "opponent_id": 456}
    # COINS_EARNED: {"amount": 500, "reason": "WINNER", "transaction_id": 789}
    
    # SOURCE: Traceability to origin model
    source_model = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        help_text="Model name that triggered event (Registration, Match, etc.)"
    )
    
    source_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Primary key of source model instance"
    )
    
    # IMMUTABILITY: No updated_at field (signals event is immutable)
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Event creation timestamp (same as timestamp for events)"
    )
    
    class Meta:
        db_table = 'user_profile_useractivity'
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']
        
        indexes = [
            # Most common query: activity feed for user
            models.Index(fields=['user', '-timestamp'], name='idx_activity_user_time'),
            
            # Filter by event type
            models.Index(fields=['event_type', '-timestamp'], name='idx_activity_type_time'),
            
            # User + event type combo (analytics)
            models.Index(fields=['user', 'event_type'], name='idx_activity_user_type'),
            
            # Source lookup (find events from specific model instance)
            models.Index(fields=['source_model', 'source_id'], name='idx_activity_source'),
            
            # Time range queries (leaderboards, monthly stats)
            models.Index(fields=['timestamp'], name='idx_activity_timestamp'),
        ]
        
        # Permissions: view only, no add/change/delete
        permissions = [
            ('view_activity_feed', 'Can view user activity feed'),
            ('export_activity_data', 'Can export activity data (GDPR)'),
        ]
        
        # Constraints
        constraints = [
            # Idempotency: prevent duplicate events from same source
            models.UniqueConstraint(
                fields=['source_model', 'source_id', 'event_type'],
                name='unique_source_event',
                condition=models.Q(source_model__isnull=False, source_id__isnull=False),
                violation_error_message="Event already exists for this source"
            ),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.event_type} at {self.timestamp}"
    
    def save(self, *args, **kwargs):
        """
        Override save to enforce immutability.
        Only allow creation (pk is None), no updates.
        """
        if self.pk is not None:
            raise ValueError("UserActivity events are immutable. Cannot update existing event.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Override delete to prevent deletion"""
        raise ValueError("UserActivity events are immutable. Cannot delete events.")
```

---

### 1.2 Metadata Schema by Event Type

**Tournament Events:**
```python
# TOURNAMENT_REGISTERED
{
    "tournament_id": 42,
    "tournament_name": "Winter Championship 2025",
    "registration_id": 123,
    "entry_fee": 100,  # DeltaCoins paid (0 if free)
    "team_id": null  # null for solo, ID for team tournaments
}

# TOURNAMENT_JOINED (check-in complete)
{
    "tournament_id": 42,
    "tournament_name": "Winter Championship 2025",
    "registration_id": 123,
    "checked_in_at": "2025-12-23T14:30:00Z"
}

# TOURNAMENT_COMPLETED (finished to end, any placement)
{
    "tournament_id": 42,
    "tournament_name": "Winter Championship 2025",
    "registration_id": 123,
    "final_placement": 5,  # 1=winner, 2=runner_up, 3-4=top4, 5+=participated
    "total_matches": 3
}

# TOURNAMENT_WON
{
    "tournament_id": 42,
    "tournament_name": "Winter Championship 2025",
    "registration_id": 123,
    "prize_amount": 1000,
    "participants_count": 16
}

# TOURNAMENT_RUNNER_UP / TOURNAMENT_TOP4
{
    "tournament_id": 42,
    "tournament_name": "Winter Championship 2025",
    "registration_id": 123,
    "placement": 2,  # 2 for runner_up, 3-4 for top4
    "prize_amount": 500
}
```

**Match Events:**
```python
# MATCH_PLAYED
{
    "match_id": 456,
    "tournament_id": 42,
    "opponent_user_id": 789,  # null if team vs team
    "opponent_team_id": null,
    "round_number": 2,
    "match_result": "won"  # "won", "lost", "forfeit"
}

# MATCH_WON
{
    "match_id": 456,
    "tournament_id": 42,
    "opponent_user_id": 789,
    "score": {"winner": 16, "loser": 14},
    "round_number": 2
}

# MATCH_LOST
{
    "match_id": 456,
    "tournament_id": 42,
    "opponent_user_id": 789,
    "score": {"winner": 16, "loser": 8},
    "round_number": 1
}
```

**Economy Events:**
```python
# COINS_EARNED
{
    "amount": 500,
    "reason": "WINNER",  # DeltaCrownTransaction.Reason
    "transaction_id": 789,
    "tournament_id": 42,  # if prize-related
    "balance_after": 1500
}

# COINS_SPENT
{
    "amount": -100,
    "reason": "ENTRY_FEE_DEBIT",
    "transaction_id": 790,
    "tournament_id": 43,
    "balance_after": 1400
}
```

**Achievement Events:**
```python
# ACHIEVEMENT_UNLOCKED
{
    "achievement_id": 12,
    "achievement_name": "First Blood",
    "achievement_tier": "rare",
    "trigger_event": "MATCH_WON",
    "trigger_count": 1
}
```

---

## 2. USER PROFILE STATS MODEL (Derived Projection)

### 2.1 Model Definition

```python
# apps/user_profile/models/stats.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class UserProfileStats(models.Model):
    """
    Derived projection of user stats computed from UserActivity events.
    
    Design Principles:
    - NEVER manually updated (only via StatsUpdateService)
    - Source of truth: UserActivity events
    - Can be recomputed from events (idempotent)
    - Uses F() expressions for atomic updates (race condition safe)
    
    Update Triggers:
    - Signal: post_save(UserActivity) → StatsUpdateService.increment_stat()
    - Command: python manage.py reconcile_user_stats (nightly)
    
    Performance:
    - Single row per user (fast lookup)
    - Indexed for leaderboards (tournaments_won DESC)
    - Computed properties cached in @property methods
    """
    
    # 1-to-1 with UserProfile
    profile = models.OneToOneField(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='stats',
        primary_key=True,
        help_text="User profile this stats record belongs to"
    )
    
    # ====================
    # TOURNAMENT STATS
    # ====================
    
    tournaments_registered = models.IntegerField(
        default=0,
        help_text="Count of tournament registrations (any status)"
    )
    
    tournaments_played = models.IntegerField(
        default=0,
        help_text="Count of tournaments actually participated in (checked-in)"
    )
    
    tournaments_completed = models.IntegerField(
        default=0,
        help_text="Count of tournaments finished to end (any placement)"
    )
    
    tournaments_won = models.IntegerField(
        default=0,
        help_text="Count of 1st place tournament wins"
    )
    
    tournaments_runner_up = models.IntegerField(
        default=0,
        help_text="Count of 2nd place tournament finishes"
    )
    
    tournaments_top4 = models.IntegerField(
        default=0,
        help_text="Count of 3rd/4th place tournament finishes"
    )
    
    # ====================
    # MATCH STATS
    # ====================
    
    matches_played = models.IntegerField(
        default=0,
        help_text="Count of matches played (any result)"
    )
    
    matches_won = models.IntegerField(
        default=0,
        help_text="Count of matches won"
    )
    
    matches_lost = models.IntegerField(
        default=0,
        help_text="Count of matches lost"
    )
    
    # ====================
    # ECONOMY STATS
    # ====================
    
    total_earned = models.IntegerField(
        default=0,
        help_text="Total DeltaCoins earned (all-time, positive transactions)"
    )
    
    total_spent = models.IntegerField(
        default=0,
        help_text="Total DeltaCoins spent (all-time, negative transactions)"
    )
    
    # ====================
    # ACHIEVEMENT STATS
    # ====================
    
    achievements_count = models.IntegerField(
        default=0,
        help_text="Count of achievements unlocked"
    )
    
    # ====================
    # TEAM STATS (Future: UP-M4)
    # ====================
    
    teams_created = models.IntegerField(
        default=0,
        help_text="Count of teams created by user"
    )
    
    teams_joined = models.IntegerField(
        default=0,
        help_text="Count of teams joined (excluding created)"
    )
    
    current_teams_count = models.IntegerField(
        default=0,
        help_text="Count of teams user is currently member of"
    )
    
    # ====================
    # METADATA
    # ====================
    
    last_activity_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of most recent UserActivity event"
    )
    
    stats_updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last time stats were recalculated"
    )
    
    class Meta:
        db_table = 'user_profile_userprofilestats'
        verbose_name = "User Profile Stats"
        verbose_name_plural = "User Profile Stats"
        
        indexes = [
            # Leaderboards: top tournament winners
            models.Index(
                fields=['-tournaments_won', '-tournaments_played'],
                name='idx_stats_tournament_leaders'
            ),
            
            # Leaderboards: best match win rate
            models.Index(
                fields=['-matches_won', '-matches_played'],
                name='idx_stats_match_leaders'
            ),
            
            # Leaderboards: top earners
            models.Index(
                fields=['-total_earned'],
                name='idx_stats_earnings_leaders'
            ),
            
            # Recent activity tracking
            models.Index(
                fields=['-last_activity_at'],
                name='idx_stats_recent_activity'
            ),
        ]
        
        # Constraints
        constraints = [
            # Logical constraints: counts cannot be negative
            models.CheckConstraint(
                check=models.Q(tournaments_registered__gte=0),
                name='check_tournaments_registered_nonnegative'
            ),
            models.CheckConstraint(
                check=models.Q(matches_played__gte=0),
                name='check_matches_played_nonnegative'
            ),
            models.CheckConstraint(
                check=models.Q(total_earned__gte=0),
                name='check_total_earned_nonnegative'
            ),
            models.CheckConstraint(
                check=models.Q(total_spent__gte=0),
                name='check_total_spent_nonnegative'
            ),
            
            # matches_won <= matches_played (can't win more than played)
            models.CheckConstraint(
                check=models.Q(matches_won__lte=models.F('matches_played')),
                name='check_matches_won_lte_played'
            ),
            
            # tournaments_won <= tournaments_played
            models.CheckConstraint(
                check=models.Q(tournaments_won__lte=models.F('tournaments_played')),
                name='check_tournaments_won_lte_played'
            ),
        ]
    
    def __str__(self):
        return f"Stats for {self.profile.display_name or self.profile.user.username}"
    
    # ====================
    # COMPUTED PROPERTIES
    # ====================
    
    @property
    def win_rate(self) -> Decimal:
        """
        Match win rate: matches_won / matches_played.
        Returns 0.00 if no matches played.
        """
        if self.matches_played == 0:
            return Decimal('0.00')
        return Decimal(self.matches_won) / Decimal(self.matches_played)
    
    @property
    def win_rate_percent(self) -> str:
        """Win rate as percentage string (e.g., "75.5%")"""
        return f"{self.win_rate * 100:.1f}%"
    
    @property
    def tournament_win_rate(self) -> Decimal:
        """
        Tournament win rate: tournaments_won / tournaments_played.
        Returns 0.00 if no tournaments played.
        """
        if self.tournaments_played == 0:
            return Decimal('0.00')
        return Decimal(self.tournaments_won) / Decimal(self.tournaments_played)
    
    @property
    def tournament_win_rate_percent(self) -> str:
        """Tournament win rate as percentage string"""
        return f"{self.tournament_win_rate * 100:.1f}%"
    
    @property
    def net_earnings(self) -> int:
        """Net earnings: total_earned - total_spent"""
        return self.total_earned - self.total_spent
    
    @property
    def podium_rate(self) -> Decimal:
        """
        Podium rate: (won + runner_up + top4) / tournaments_played.
        How often user places in top 4.
        """
        if self.tournaments_played == 0:
            return Decimal('0.00')
        podium_count = self.tournaments_won + self.tournaments_runner_up + self.tournaments_top4
        return Decimal(podium_count) / Decimal(self.tournaments_played)
    
    @property
    def podium_rate_percent(self) -> str:
        """Podium rate as percentage string"""
        return f"{self.podium_rate * 100:.1f}%"
    
    @property
    def avg_match_earnings(self) -> Decimal:
        """Average earnings per match (if matches_played > 0)"""
        if self.matches_played == 0:
            return Decimal('0.00')
        return Decimal(self.total_earned) / Decimal(self.matches_played)
    
    # ====================
    # HELPER METHODS
    # ====================
    
    def to_dict(self) -> dict:
        """
        Export stats as dictionary for API responses.
        Includes computed properties.
        """
        return {
            'profile_id': self.profile.id,
            'display_name': self.profile.display_name,
            'public_id': self.profile.public_id,
            
            # Tournament stats
            'tournaments': {
                'registered': self.tournaments_registered,
                'played': self.tournaments_played,
                'completed': self.tournaments_completed,
                'won': self.tournaments_won,
                'runner_up': self.tournaments_runner_up,
                'top4': self.tournaments_top4,
                'win_rate': str(self.tournament_win_rate_percent),
                'podium_rate': str(self.podium_rate_percent),
            },
            
            # Match stats
            'matches': {
                'played': self.matches_played,
                'won': self.matches_won,
                'lost': self.matches_lost,
                'win_rate': str(self.win_rate_percent),
            },
            
            # Economy stats
            'economy': {
                'total_earned': self.total_earned,
                'total_spent': self.total_spent,
                'net_earnings': self.net_earnings,
                'avg_per_match': float(self.avg_match_earnings),
            },
            
            # Other stats
            'achievements_count': self.achievements_count,
            'teams_created': self.teams_created,
            'teams_joined': self.teams_joined,
            'current_teams_count': self.current_teams_count,
            
            # Metadata
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'stats_updated_at': self.stats_updated_at.isoformat(),
        }
```

---

## 3. RELATIONSHIPS & FOREIGN KEYS

### 3.1 Database Diagram

```
┌────────────────────┐
│ accounts_user      │
│ ─────────────────  │
│ id (PK)           │
│ username          │
└─────┬──────────────┘
      │ 1
      │
      │ N
┌─────▼──────────────────┐
│ user_profile_useractivity │ (Immutable Event Log)
│ ────────────────────────  │
│ id (PK)                   │
│ user_id (FK)              │ ← PROTECT (never delete events)
│ event_type                │
│ timestamp                 │
│ metadata (JSON)           │
│ source_model              │
│ source_id                 │
│ created_at                │
└───────────────────────────┘
      │
      │ triggers signal
      │
      ▼
┌──────────────────────────┐
│ user_profile_userprofilestats │ (Derived Projection)
│ ─────────────────────────────  │
│ profile_id (PK, FK)            │ ← CASCADE (delete with profile)
│ tournaments_played             │
│ tournaments_won                │
│ matches_played                 │
│ matches_won                    │
│ total_earned                   │
│ total_spent                    │
│ last_activity_at               │
│ stats_updated_at               │
└────────────────────────────────┘
      ▲
      │ 1-to-1
      │
┌─────┴──────────────────┐
│ user_profile_userprofile │
│ ──────────────────────── │
│ id (PK)                  │
│ user_id (FK)             │
│ display_name             │
│ public_id                │
└──────────────────────────┘
```

---

### 3.2 Source Model Relationships

**UserActivity.source_model + source_id links to:**

| source_model | source_id points to | Example |
|--------------|---------------------|---------|
| Registration | tournaments.Registration.id | TOURNAMENT_REGISTERED event |
| Match | tournaments.Match.id | MATCH_PLAYED event |
| TournamentResult | tournaments.TournamentResult.id | TOURNAMENT_WON event |
| DeltaCrownTransaction | economy.DeltaCrownTransaction.id | COINS_EARNED event |
| Achievement | user_profile.Achievement.id | ACHIEVEMENT_UNLOCKED event |

**Why Generic Foreign Key (CharField + IntegerField)?**
- Avoids circular dependencies between apps
- Allows events from any model without migration
- Trade-off: No referential integrity (but events are immutable)

---

## 4. INDEXES & PERFORMANCE

### 4.1 Index Strategy

**UserActivity Indexes (5 total):**
```sql
-- 1. Activity feed query (most common)
CREATE INDEX idx_activity_user_time ON user_profile_useractivity(user_id, timestamp DESC);
-- Query: SELECT * FROM user_profile_useractivity WHERE user_id = 123 ORDER BY timestamp DESC LIMIT 50;
-- Cardinality: 10K users × 500 events = 5M rows → index covers WHERE + ORDER BY

-- 2. Filter by event type
CREATE INDEX idx_activity_type_time ON user_profile_useractivity(event_type, timestamp DESC);
-- Query: SELECT * FROM user_profile_useractivity WHERE event_type = 'MATCH_WON' ORDER BY timestamp DESC;
-- Use case: Global leaderboards, event type analytics

-- 3. User + event type combo (stats aggregation)
CREATE INDEX idx_activity_user_type ON user_profile_useractivity(user_id, event_type);
-- Query: SELECT COUNT(*) FROM user_profile_useractivity WHERE user_id = 123 AND event_type = 'TOURNAMENT_WON';
-- Use case: Stats recomputation, event count queries

-- 4. Source lookup (traceability)
CREATE INDEX idx_activity_source ON user_profile_useractivity(source_model, source_id);
-- Query: SELECT * FROM user_profile_useractivity WHERE source_model = 'Match' AND source_id = 456;
-- Use case: "Show all events from this match", audit trail

-- 5. Time range queries (partial index if needed)
CREATE INDEX idx_activity_timestamp ON user_profile_useractivity(timestamp);
-- Query: SELECT * FROM user_profile_useractivity WHERE timestamp >= '2025-01-01' AND timestamp < '2025-02-01';
-- Use case: Monthly stats, time-series analysis
```

**UserProfileStats Indexes (4 total):**
```sql
-- 1. Tournament leaderboard
CREATE INDEX idx_stats_tournament_leaders ON user_profile_userprofilestats(tournaments_won DESC, tournaments_played DESC);
-- Query: SELECT * FROM user_profile_userprofilestats ORDER BY tournaments_won DESC, tournaments_played DESC LIMIT 100;
-- Use case: "Top 100 Tournament Winners" page

-- 2. Match leaderboard
CREATE INDEX idx_stats_match_leaders ON user_profile_userprofilestats(matches_won DESC, matches_played DESC);
-- Query: SELECT * FROM user_profile_userprofilestats ORDER BY matches_won DESC LIMIT 100;
-- Use case: "Best Players" leaderboard

-- 3. Earnings leaderboard
CREATE INDEX idx_stats_earnings_leaders ON user_profile_userprofilestats(total_earned DESC);
-- Query: SELECT * FROM user_profile_userprofilestats ORDER BY total_earned DESC LIMIT 100;
-- Use case: "Top Earners" page

-- 4. Recent activity tracking
CREATE INDEX idx_stats_recent_activity ON user_profile_userprofilestats(last_activity_at DESC);
-- Query: SELECT * FROM user_profile_userprofilestats WHERE last_activity_at >= NOW() - INTERVAL '7 days';
-- Use case: "Active Users" report, retention metrics
```

---

### 4.2 Query Performance Benchmarks

| Query | Expected Time | Index Used |
|-------|---------------|------------|
| Activity feed (50 events) | <5ms | idx_activity_user_time |
| Stats lookup (single user) | <1ms | Primary key (profile_id) |
| Event count by type | <10ms | idx_activity_user_type |
| Tournament leaderboard (top 100) | <20ms | idx_stats_tournament_leaders |
| Source lookup (events from match) | <5ms | idx_activity_source |
| Time range query (30 days) | <50ms | idx_activity_timestamp |

**Optimization Notes:**
- All queries use covering indexes (no table scan)
- Pagination prevents large result sets
- Stats cached in UserProfileStats (no COUNT() on events)

---

## 5. MIGRATIONS

### 5.1 Migration Sequence

**Migration 1: Create UserActivity model**
```python
# Generated: python manage.py makemigrations user_profile --name add_user_activity
operations = [
    migrations.CreateModel(
        name='UserActivity',
        fields=[
            ('id', models.BigAutoField(primary_key=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='accounts.user')),
            ('event_type', models.CharField(max_length=50, choices=EventType.choices)),
            ('timestamp', models.DateTimeField(auto_now_add=True)),
            ('metadata', models.JSONField(default=dict)),
            ('source_model', models.CharField(max_length=50, null=True)),
            ('source_id', models.IntegerField(null=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ],
        options={
            'db_table': 'user_profile_useractivity',
            'ordering': ['-timestamp'],
        },
    ),
    # Add indexes
    migrations.AddIndex(...),
    # Add unique constraint
    migrations.AddConstraint(...),
]
```

**Migration 2: Create UserProfileStats model**
```python
# Generated: python manage.py makemigrations user_profile --name add_user_profile_stats
operations = [
    migrations.CreateModel(
        name='UserProfileStats',
        fields=[
            ('profile', models.OneToOneField(primary_key=True, on_delete=django.db.models.deletion.CASCADE, to='user_profile.userprofile')),
            ('tournaments_registered', models.IntegerField(default=0)),
            ('tournaments_played', models.IntegerField(default=0)),
            # ... all stat fields
            ('last_activity_at', models.DateTimeField(null=True)),
            ('stats_updated_at', models.DateTimeField(auto_now=True)),
        ],
        options={
            'db_table': 'user_profile_userprofilestats',
        },
    ),
    # Add indexes
    migrations.AddIndex(...),
    # Add check constraints
    migrations.AddConstraint(...),
]
```

**Migration 3: Backfill UserProfileStats for existing profiles**
```python
# apps/user_profile/migrations/0XXX_backfill_profile_stats.py
from django.db import migrations

def create_stats_for_existing_profiles(apps, schema_editor):
    UserProfile = apps.get_model('user_profile', 'UserProfile')
    UserProfileStats = apps.get_model('user_profile', 'UserProfileStats')
    
    profiles_without_stats = UserProfile.objects.filter(stats__isnull=True)
    stats_to_create = [
        UserProfileStats(profile=profile)
        for profile in profiles_without_stats
    ]
    UserProfileStats.objects.bulk_create(stats_to_create, batch_size=500)

class Migration(migrations.Migration):
    dependencies = [
        ('user_profile', '0XXX_add_user_profile_stats'),
    ]
    
    operations = [
        migrations.RunPython(create_stats_for_existing_profiles, reverse_code=migrations.RunPython.noop),
    ]
```

---

## 6. DATA VALIDATION

### 6.1 Model Constraints

**UserActivity Constraints:**
- ✅ source_model + source_id + event_type UNIQUE (idempotency)
- ✅ user_id NOT NULL
- ✅ event_type in EventType.choices
- ✅ timestamp NOT NULL (auto-set)

**UserProfileStats Constraints:**
- ✅ All count fields >= 0 (CHECK constraint)
- ✅ matches_won <= matches_played (logical constraint)
- ✅ tournaments_won <= tournaments_played (logical constraint)

**Django Model Validation:**
```python
# apps/user_profile/models/stats.py
def clean(self):
    """Additional validation beyond DB constraints"""
    if self.matches_won > self.matches_played:
        raise ValidationError("matches_won cannot exceed matches_played")
    
    if self.total_earned < 0:
        raise ValidationError("total_earned cannot be negative")
```

---

## 7. ADMIN INTERFACE

### 7.1 UserActivity Admin (Read-Only)

```python
# apps/user_profile/admin.py
from django.contrib import admin
from apps.user_profile.models import UserActivity

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'event_type', 'timestamp', 'source_model', 'source_id']
    list_filter = ['event_type', 'timestamp', 'source_model']
    search_fields = ['user__username', 'user__email', 'metadata']
    readonly_fields = ['user', 'event_type', 'timestamp', 'metadata', 'source_model', 'source_id', 'created_at']
    ordering = ['-timestamp']
    
    # Immutability: no add/change/delete
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
```

---

### 7.2 UserProfileStats Admin (Read-Only)

```python
@admin.register(UserProfileStats)
class UserProfileStatsAdmin(admin.ModelAdmin):
    list_display = ['profile', 'tournaments_won', 'matches_won', 'total_earned', 'last_activity_at']
    list_filter = ['last_activity_at']
    search_fields = ['profile__user__username', 'profile__display_name']
    readonly_fields = [
        'profile', 'tournaments_registered', 'tournaments_played', 'tournaments_won',
        'matches_played', 'matches_won', 'total_earned', 'total_spent',
        'last_activity_at', 'stats_updated_at'
    ]
    ordering = ['-tournaments_won', '-total_earned']
    
    # Read-only: stats updated via service only
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False  # No manual editing
    
    def has_delete_permission(self, request, obj=None):
        return True  # Allow delete (cascade with profile)
    
    # Custom admin actions
    actions = ['recompute_stats_action']
    
    @admin.action(description='Recompute stats from events')
    def recompute_stats_action(self, request, queryset):
        from apps.user_profile.services.stats_service import StatsUpdateService
        
        count = 0
        for stats in queryset:
            StatsUpdateService.recompute_stats_from_events(stats.profile.user)
            count += 1
        
        self.message_user(request, f"Recomputed stats for {count} users")
```

---

## DOCUMENT STATUS

**Review Checklist:**
- ✅ UserActivity model complete (fields, indexes, constraints)
- ✅ UserProfileStats model complete (fields, computed properties)
- ✅ Metadata schemas defined for all event types
- ✅ Index strategy documented with performance benchmarks
- ✅ Migration sequence planned
- ✅ Admin interface designed (read-only)

**Next Document:** UP_M2_EXECUTION_PLAN.md (step-by-step implementation)

---

**END OF DOCUMENT**
