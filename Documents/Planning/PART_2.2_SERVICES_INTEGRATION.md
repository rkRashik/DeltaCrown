# PROPOSAL PART 2.2: SERVICES & INTEGRATION PATTERNS

---

**Navigation:**
- [← Previous: Part 2.1 - Architecture Foundations](PART_2.1_ARCHITECTURE_FOUNDATIONS.md)
- [↑ Master Index](INDEX_MASTER_NAVIGATION.md)
- [→ Next: Part 2.3 - Real-Time & Security](PART_2.3_REALTIME_SECURITY.md)

---

**Part 2.2 Table of Contents:**
- Section 4 (continued): Core Models - Bracket, Match, Dispute, Awards
- Section 5: Service Layer Architecture
- Section 6: Integration Patterns with Other Apps
- Section 7 (partial): Real-Time Architecture & Frontend System

---

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (GENERATED, 'Generated'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )
    
    # Metadata
    total_rounds = models.PositiveIntegerField(default=0)
    current_round = models.PositiveIntegerField(default=0)
    generated_at = models.DateTimeField(null=True, blank=True)
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['tournament']
    
    def __str__(self):
        return f"Bracket for {self.tournament.name}"
```

#### BracketNode Model

```python
class BracketNode(models.Model):
    """Individual position in bracket"""
    
    bracket = models.ForeignKey(
        Bracket,
        on_delete=models.CASCADE,
        related_name='nodes'
    )
    
    # Position
    round_number = models.PositiveIntegerField()
    position_in_round = models.PositiveIntegerField()
    node_identifier = models.CharField(
        max_length=50,
        help_text="e.g., 'W1.1', 'L2.3' for winners/losers bracket"
    )
    
    # Participants (team_id or user_id)
    participant1_team_id = models.PositiveIntegerField(null=True, blank=True)
    participant1_user_id = models.PositiveIntegerField(null=True, blank=True)
    participant2_team_id = models.PositiveIntegerField(null=True, blank=True)
    participant2_user_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Winner
    winner_team_id = models.PositiveIntegerField(null=True, blank=True)
    winner_user_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Match reference
    match = models.OneToOneField(
        'match.Match',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bracket_node'
    )
    
    # Navigation (for progression)
    next_node_winner = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_winner_nodes'
    )
    next_node_loser = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_loser_nodes',
        help_text="For double elimination"
    )
    
    # Status
    is_bye = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['round_number', 'position_in_round']
        unique_together = [['bracket', 'node_identifier']]
        indexes = [
            models.Index(fields=['bracket', 'round_number']),
        ]
    
    def __str__(self):
        return f"{self.bracket.tournament.name} - {self.node_identifier}"
```

### 4.4 Match Models (tournament_engine.match)

#### Match Model

```python
class Match(models.Model):
    """Individual match in tournament"""
    
    tournament = models.ForeignKey(
        'core.Tournament',
        on_delete=models.CASCADE,
        related_name='matches'
    )
    
    bracket = models.ForeignKey(
        'bracket.Bracket',
        on_delete=models.CASCADE,
        related_name='matches',
        null=True,
        blank=True
    )
    
    # Match info
    match_number = models.PositiveIntegerField()
    round_number = models.PositiveIntegerField()
    
    # Participants
    participant1_team_id = models.PositiveIntegerField(null=True, blank=True)
    participant1_user_id = models.PositiveIntegerField(null=True, blank=True)
    participant2_team_id = models.PositiveIntegerField(null=True, blank=True)
    participant2_user_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Schedule
    scheduled_time = models.DateTimeField(null=True, blank=True)
    
    # Check-in
    check_in_deadline = models.DateTimeField(null=True, blank=True)
    participant1_checked_in = models.BooleanField(default=False)
    participant2_checked_in = models.BooleanField(default=False)
    participant1_check_in_time = models.DateTimeField(null=True, blank=True)
    participant2_check_in_time = models.DateTimeField(null=True, blank=True)
    
    # State
    SCHEDULED = 'scheduled'
    CHECK_IN = 'check_in'
    READY = 'ready'
    LIVE = 'live'
    PENDING_RESULT = 'pending_result'
    COMPLETED = 'completed'
    DISPUTED = 'disputed'
    CANCELLED = 'cancelled'
    
    STATE_CHOICES = [
        (SCHEDULED, 'Scheduled'),
        (CHECK_IN, 'Check-in Period'),
        (READY, 'Ready to Start'),
        (LIVE, 'Live'),
        (PENDING_RESULT, 'Pending Result'),
        (COMPLETED, 'Completed'),
        (DISPUTED, 'Disputed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    state = models.CharField(
        max_length=20,
        choices=STATE_CHOICES,
        default=SCHEDULED,
        db_index=True
    )
    
    # Results
    participant1_score = models.PositiveIntegerField(null=True, blank=True)
    participant2_score = models.PositiveIntegerField(null=True, blank=True)
    winner_team_id = models.PositiveIntegerField(null=True, blank=True)
    winner_user_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Result submission
    participant1_submitted_score = models.BooleanField(default=False)
    participant2_submitted_score = models.BooleanField(default=False)
    scores_match = models.BooleanField(default=False)
    
    # Lobby info
    lobby_info = models.JSONField(
        default=dict,
        help_text="Discord link, lobby code, etc."
    )
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['tournament', 'round_number', 'match_number']
        indexes = [
            models.Index(fields=['tournament', 'state']),
            models.Index(fields=['scheduled_time']),
        ]
        verbose_name_plural = 'matches'
    
    def __str__(self):
        return f"Match #{self.match_number} - {self.tournament.name}"
    
    def get_participant1_name(self):
        """Get participant 1 display name"""
        from tournament_engine.utils.helpers import get_participant_name
        return get_participant_name(
            team_id=self.participant1_team_id,
            user_id=self.participant1_user_id
        )
    
    def get_participant2_name(self):
        """Get participant 2 display name"""
        from tournament_engine.utils.helpers import get_participant_name
        return get_participant_name(
            team_id=self.participant2_team_id,
            user_id=self.participant2_user_id
        )
```

#### MatchResult Model

```python
class MatchResult(models.Model):
    """Score submission for match"""
    
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name='result_submissions'
    )
    
    # Submitter
    submitted_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    is_participant1 = models.BooleanField()
    
    # Scores
    participant1_score = models.PositiveIntegerField()
    participant2_score = models.PositiveIntegerField()
    
    # Evidence
    screenshot = models.ImageField(
        upload_to='matches/results/',
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True)
    
    # Metadata
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Result for {self.match} by {self.submitted_by_user.username}"
```

### 4.5 Dispute Model (tournament_engine.dispute)

```python
class Dispute(models.Model):
    """Match dispute"""
    
    match = models.ForeignKey(
        'match.Match',
        on_delete=models.CASCADE,
        related_name='disputes'
    )
    
    # Initiator
    initiated_by_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='initiated_disputes'
    )
    
    # Dispute info
    SCORE_MISMATCH = 'score_mismatch'
    NO_SHOW = 'no_show'
    CHEATING = 'cheating'
    TECHNICAL_ISSUE = 'technical_issue'
    OTHER = 'other'
    
    REASON_CHOICES = [
        (SCORE_MISMATCH, 'Score Mismatch'),
        (NO_SHOW, 'No Show'),
        (CHEATING, 'Cheating Accusation'),
        (TECHNICAL_ISSUE, 'Technical Issue'),
        (OTHER, 'Other'),
    ]
    
    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES
    )
    description = models.TextField()
    
    # Evidence
    evidence_screenshot = models.ImageField(
        upload_to='disputes/evidence/',
        null=True,
        blank=True
    )
    evidence_video_url = models.URLField(blank=True)
    
    # Status
    OPEN = 'open'
    UNDER_REVIEW = 'under_review'
    RESOLVED = 'resolved'
    ESCALATED = 'escalated'
    
    STATUS_CHOICES = [
        (OPEN, 'Open'),
        (UNDER_REVIEW, 'Under Review'),
        (RESOLVED, 'Resolved'),
        (ESCALATED, 'Escalated to Admin'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=OPEN,
        db_index=True
    )
    
    # Resolution
    resolved_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_disputes'
    )
    resolution_notes = models.TextField(blank=True)
    final_participant1_score = models.PositiveIntegerField(null=True, blank=True)
    final_participant2_score = models.PositiveIntegerField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['match', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Dispute for {self.match} - {self.reason}"
```

### 4.6 Awards Models (tournament_engine.awards)

```python
class Certificate(models.Model):
    """Digital certificate"""
    
    tournament = models.ForeignKey(
        'core.Tournament',
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    
    # Recipient
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tournament_certificates'
    )
    team_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Certificate info
    CHAMPION = 'champion'
    RUNNER_UP = 'runner_up'
    THIRD_PLACE = 'third_place'
    PARTICIPANT = 'participant'
    MVP = 'mvp'
    
    CERTIFICATE_TYPE_CHOICES = [
        (CHAMPION, 'Champion'),
        (RUNNER_UP, 'Runner-up'),
        (THIRD_PLACE, 'Third Place'),
        (PARTICIPANT, 'Participant'),
        (MVP, 'MVP'),
    ]
    
    certificate_type = models.CharField(
        max_length=20,
        choices=CERTIFICATE_TYPE_CHOICES
    )
    placement = models.PositiveIntegerField(null=True, blank=True)
    
    # Certificate file
    pdf_file = models.FileField(
        upload_to='certificates/pdfs/',
        null=True,
        blank=True
    )
    
    # Verification
    verification_code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True
    )
    qr_code_image = models.ImageField(
        upload_to='certificates/qr/',
        null=True,
        blank=True
    )
    
    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['tournament', 'certificate_type']),
        ]
    
    def __str__(self):
        recipient = self.user.username if self.user else f"Team {self.team_id}"
        return f"{self.certificate_type} - {recipient}"
```

---

## 5. Service Layer Architecture

### 5.1 Service Layer Pattern

**Purpose:** Encapsulate complex business logic outside of models and views.

**Benefits:**
- Reusable across views, Celery tasks, management commands
- Easier to test (unit tests for services)
- Clean separation of concerns
- Integration point for cross-app communication

**Structure:**
```python
# tournament_engine/core/services.py

class TournamentService:
    """Service for tournament operations"""
    
    @staticmethod
    def create_tournament(organizer, tournament_data):
        """
        Create tournament with validation
        
        Args:
            organizer (User): Tournament organizer
            tournament_data (dict): Tournament configuration
            
        Returns:
            Tournament: Created tournament instance
            
        Raises:
            ValidationError: If data invalid
        """
        # Validation logic
        # Create tournament
        # Create audit log
        # Send notifications
        pass
    
    @staticmethod
    def publish_tournament(tournament_id, published_by):
        """Publish tournament and generate bracket"""
        pass
    
    @staticmethod
    def cancel_tournament(tournament_id, reason, cancelled_by):
        """Cancel tournament and process refunds"""
        pass
```

### 5.2 Key Service Methods

#### TournamentService (core/services.py)

- `create_tournament()` - Create with validation
- `update_tournament()` - Update configuration
- `publish_tournament()` - Make public + generate bracket
- `cancel_tournament()` - Cancel + refunds
- `archive_tournament()` - Move to archive
- `duplicate_tournament()` - Tournament templates

#### RegistrationService (registration/services.py)

- `register_participant()` - Register team/user
- `auto_fill_registration_data()` - Pull from UserProfile/Teams
- `check_registration_eligibility()` - Validate constraints
- `cancel_registration()` - Withdraw + refund
- `apply_fee_waiver()` - Auto-waiver for top teams

#### PaymentService (registration/services.py)

- `submit_payment()` - Payment proof submission
- `verify_payment()` - Organizer verification
- `process_deltacoin_payment()` - Integrate with apps.economy
- `process_refund()` - Handle cancellations
- `bulk_verify_payments()` - Bulk action

#### BracketService (bracket/services.py)

- `generate_bracket()` - Main entry point
- `apply_dynamic_seeding()` - Fetch rankings from apps.teams
- `update_bracket_after_match()` - Progress winners
- `manual_override_bracket()` - TO adjustments
- `recalculate_bracket()` - Regenerate if needed

#### MatchService (match/services.py)

- `create_matches_from_bracket()` - Generate matches
- `handle_check_in()` - Check-in logic
- `transition_state()` - State machine
- `submit_score()` - Score submission
- `confirm_result()` - Finalize match
- `trigger_dispute()` - Create dispute

#### DisputeService (dispute/services.py)

- `create_dispute()` - Initiate dispute
- `submit_evidence()` - Add evidence
- `resolve_dispute()` - TO decision
- `escalate_dispute()` - Admin escalation
- `apply_resolution()` - Update match result

#### CertificateService (awards/services.py)

- `generate_certificates()` - Batch generation
- `generate_certificate_pdf()` - PDF creation
- `generate_qr_code()` - Verification QR
- `verify_certificate()` - Public verification

#### ChallengeService (challenge/services.py)

- `create_challenge()` - Define challenge
- `track_progress()` - Update progress
- `verify_completion()` - Manual verify
- `award_challenge_prizes()` - DeltaCoin distribution

#### AnalyticsService (analytics/services.py)

- `calculate_tournament_stats()` - Post-tournament
- `update_player_stats()` - Cumulative stats
- `generate_leaderboard()` - Rankings
- `export_analytics()` - CSV/PDF export

#### AuditService (audit/services.py)

- `log_action()` - Record action
- `search_audit_logs()` - Query logs
- `export_audit_trail()` - Compliance export

---

## 6. Integration Patterns

### 6.1 Integration with apps.economy

**DeltaCoin Transactions:**

```python
# tournament_engine/registration/services.py

from apps.economy.services import award, deduct

class PaymentService:
    
    @staticmethod
    def process_deltacoin_payment(registration):
        """Deduct DeltaCoin for entry fee"""
        try:
            # Deduct entry fee
            deduct(
                user=registration.user,
                amount=registration.tournament.entry_fee_deltacoin,
                reason=f"Tournament entry: {registration.tournament.name}",
                idempotency_key=f"tournament_entry_{registration.id}"
            )
            
            # Update registration
            registration.status = Registration.CONFIRMED
            registration.save()
            
            return True
        except InsufficientBalanceError:
            return False
    
    @staticmethod
    def process_prize_distribution(tournament):
        """Distribute DeltaCoin prizes"""
        from tournament_engine.analytics.services import AnalyticsService
        
        # Get final standings
        standings = AnalyticsService.get_final_standings(tournament)
        
        for placement, (participant_id, is_team) in standings.items():
            # Calculate prize
            prize_amount = calculate_prize(
                tournament.prize_deltacoin,
                tournament.prize_distribution,
                placement
            )
            
            if prize_amount > 0:
                # Award prize
                if is_team:
                    # Award to team members
                    team_members = get_team_members(participant_id)
                    per_member = prize_amount // len(team_members)
                    
                    for member in team_members:
                        award(
                            user=member,
                            amount=per_member,
                            reason=f"Tournament prize: {tournament.name} (Placement: {placement})",
                            idempotency_key=f"tournament_prize_{tournament.id}_{member.id}_{placement}"
                        )
                else:
                    # Award to individual
                    user = User.objects.get(id=participant_id)
                    award(
                        user=user,
                        amount=prize_amount,
                        reason=f"Tournament prize: {tournament.name} (Placement: {placement})",
                        idempotency_key=f"tournament_prize_{tournament.id}_{user.id}_{placement}"
                    )
```

### 6.2 Integration with apps.teams

**Fetch Team Data:**

```python
# tournament_engine/utils/helpers.py

def get_team_name(team_id):
    """Fetch team name from apps.teams"""
    from apps.teams.models import Team
    try:
        team = Team.objects.get(id=team_id)
        return team.name
    except Team.DoesNotExist:
        return f"Team #{team_id}"

def get_team_roster(team_id, game_slug):
    """Fetch team roster for specific game"""
    from apps.teams.models import Team
    
    team = Team.objects.get(id=team_id)
    # Logic to get game-specific roster
    # (depends on apps.teams structure)
    pass

def get_team_ranking(team_id):
    """Fetch team ranking for seeding"""
    from apps.teams.services import ranking_service
    
    return ranking_service.get_team_rank(team_id)
```

**Update Team Rankings:**

```python
# tournament_engine/analytics/services.py

class AnalyticsService:
    
    @staticmethod
    def update_team_rankings(tournament):
        """Update team rankings after tournament"""
        from apps.teams.services import ranking_service
        
        standings = AnalyticsService.get_final_standings(tournament)
        
        for placement, (team_id, is_team) in standings.items():
            if is_team:
                # Calculate points based on placement
                points = calculate_ranking_points(placement, tournament.prize_pool)
                
                # Update via teams service
                ranking_service.add_tournament_result(
                    team_id=team_id,
                    tournament_name=tournament.name,
                    placement=placement,
                    points=points
                )
```

### 6.3 Integration with apps.user_profile

**Auto-fill Registration:**

```python
# tournament_engine/registration/services.py

class RegistrationService:
    
    @staticmethod
    def auto_fill_registration_data(user, tournament):
        """Pull data from UserProfile"""
        from apps.user_profile.models import UserProfile
        
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            return {}
        
        # Get game-specific ID
        game_id_field = tournament.game.profile_id_field
        game_id = getattr(profile, game_id_field, None)
        
        data = {
            'full_name': user.get_full_name(),
            'email': user.email,
            'discord_id': profile.discord_id,
            'game_id': game_id,
            # Add more fields as needed
        }
        
        return data
```

### 6.4 Integration with apps.notifications

**Tournament Notifications:**

```python
# tournament_engine/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from tournament_engine.core.models import Tournament
from apps.notifications.services import NotificationService

@receiver(post_save, sender=Tournament)
def tournament_published(sender, instance, created, **kwargs):
    """Notify when tournament published"""
    if not created and instance.status == Tournament.PUBLISHED:
        # Notify followers
        NotificationService.send_notification(
            notification_type='TOURNAMENT_PUBLISHED',
            recipients=get_game_followers(instance.game),
            context={
                'tournament_name': instance.name,
                'tournament_url': instance.get_absolute_url(),
            }
        )
```

### 6.5 Integration with apps.siteui (Community)

**Discussion Threads:**

```python
# tournament_engine/core/models.py

class Tournament(models.Model):
    # ... existing fields ...
    
    discussion_thread_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Reference to siteui discussion thread"
    )
    
    def get_discussion_thread(self):
        """Get associated discussion thread"""
        if self.discussion_thread_id:
            from apps.siteui.models import Post
            try:
                return Post.objects.get(id=self.discussion_thread_id)
            except Post.DoesNotExist:
                return None
        return None
```

### 6.6 Event Bus Architecture (Centralized Event Dispatch)

**Purpose:** Decouple cross-app event handling and enable clean subscription patterns.

**Event Bus Implementation:**

```python
# tournament_engine/events.py

from typing import Dict, List, Callable, Any
from django.dispatch import Signal
import logging

logger = logging.getLogger(__name__)

class TournamentEventBus:
    """Centralized event dispatcher for tournament engine"""
    
    # Define event signals
    TOURNAMENT_PUBLISHED = Signal()
    REGISTRATION_CONFIRMED = Signal()
    BRACKET_GENERATED = Signal()
    MATCH_STARTED = Signal()
    MATCH_COMPLETED = Signal()
    DISPUTE_CREATED = Signal()
    DISPUTE_RESOLVED = Signal()
    TOURNAMENT_CONCLUDED = Signal()
    CERTIFICATE_GENERATED = Signal()
    CHALLENGE_COMPLETED = Signal()
    
    _subscribers: Dict[str, List[Callable]] = {}
    
    @classmethod
    def subscribe(cls, event_type: str, handler: Callable):
        """Subscribe to an event type"""
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(handler)
        logger.info(f"Subscribed {handler.__name__} to {event_type}")
    
    @classmethod
    def dispatch(cls, event_type: str, payload: Dict[str, Any]):
        """Dispatch event to all subscribers"""
        logger.info(f"Dispatching event: {event_type}")
        
        # Call all subscribers
        handlers = cls._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                handler(payload)
            except Exception as e:
                logger.error(f"Error in {handler.__name__}: {e}")
        
        # Also emit Django signal (for backward compatibility)
        signal = getattr(cls, event_type.upper(), None)
        if signal:
            signal.send(sender=cls, payload=payload)
    
    @classmethod
    def dispatch_async(cls, event_type: str, payload: Dict[str, Any]):
        """Dispatch event asynchronously via Celery"""
        from tournament_engine.tasks import process_event_async
        process_event_async.delay(event_type, payload)


# Event Subscribers (auto-registered)

def subscribe_analytics_updates():
    """Register analytics listeners"""
    from tournament_engine.analytics.services import AnalyticsService
    
    def on_match_completed(payload):
        AnalyticsService.update_stats_after_match(payload['match_id'])
    
    def on_tournament_concluded(payload):
        AnalyticsService.calculate_tournament_stats(payload['tournament_id'])
    
    TournamentEventBus.subscribe('match_completed', on_match_completed)
    TournamentEventBus.subscribe('tournament_concluded', on_tournament_concluded)

def subscribe_notification_triggers():
    """Register notification listeners"""
    from apps.notifications.services import NotificationService
    
    def on_match_started(payload):
        NotificationService.send_match_start_notification(payload['match_id'])
    
    def on_dispute_created(payload):
        NotificationService.send_dispute_notification(payload['dispute_id'])
    
    TournamentEventBus.subscribe('match_started', on_match_started)
    TournamentEventBus.subscribe('dispute_created', on_dispute_created)

def subscribe_ranking_updates():
    """Register ranking system listeners"""
    from apps.teams.services import ranking_service
    
    def on_tournament_concluded(payload):
        ranking_service.update_rankings_from_tournament(payload['tournament_id'])
    
    TournamentEventBus.subscribe('tournament_concluded', on_tournament_concluded)

# Auto-register all subscribers on app ready
def register_all_event_subscribers():
    """Called from apps.py ready()"""
    subscribe_analytics_updates()
    subscribe_notification_triggers()
    subscribe_ranking_updates()
```

**Usage in Services:**

```python
# tournament_engine/match/services.py

class MatchService:
    
    @staticmethod
    def complete_match(match_id):
        """Complete match and trigger events"""
        match = Match.objects.get(id=match_id)
        match.state = Match.COMPLETED
        match.completed_at = timezone.now()
        match.save()
        
        # Dispatch event (triggers analytics, notifications, bracket update)
        TournamentEventBus.dispatch('match_completed', {
            'match_id': match.id,
            'tournament_id': match.tournament_id,
            'winner_team_id': match.winner_team_id,
            'winner_user_id': match.winner_user_id,
        })
```

**Benefits:**
- ✅ Decouples services (no direct imports between apps)
- ✅ Easy to add new subscribers without modifying existing code
- ✅ Clear event flow for debugging
- ✅ Async dispatch option for performance
- ✅ Testable (can mock event bus in tests)

---

## 7. Real-Time Architecture

### 7.1 Django Channels Setup

**Purpose:** Real-time updates for live brackets, scoreboards, notifications

**Channel Layers Configuration:**

```python
# deltacrown/settings.py

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

### 7.2 WebSocket Consumers

```python
# tournament_engine/consumers.py

from channels.generic.websocket import AsyncJsonWebsocketConsumer

class TournamentConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for tournament updates"""
    
    async def connect(self):
        self.tournament_id = self.scope['url_route']['kwargs']['tournament_id']
        self.room_group_name = f'tournament_{self.tournament_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from room group
    async def tournament_update(self, event):
        """Send tournament update to WebSocket"""
        await self.send_json({
            'type': event['update_type'],
            'data': event['data']
        })
```

### 7.3 Broadcasting Updates

```python
# tournament_engine/match/services.py

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class MatchService:
    
    @staticmethod
    def broadcast_match_update(match):
        """Broadcast match update to tournament room"""
        channel_layer = get_channel_layer()
        
        async_to_sync(channel_layer.group_send)(
            f'tournament_{match.tournament_id}',
            {
                'type': 'tournament_update',
                'update_type': 'match_update',
                'data': {
                    'match_id': match.id,
                    'state': match.state,
                    'participant1_score': match.participant1_score,
                    'participant2_score': match.participant2_score,
                }
            }
        )
```

---

## 7.4 Frontend System Architecture

**Purpose:** Bridge Part 1 UI/UX specifications with Part 2 technical architecture for frontend implementation

### Technology Stack

- **Template Engine:** Django Templates with inheritance
- **CSS Framework:** Tailwind CSS 3.x (utility-first)
- **JavaScript Enhancement:** HTMX (declarative AJAX) + Alpine.js (reactive components)
- **Icons:** Heroicons + custom tournament icons
- **Charts:** Chart.js for analytics visualizations

### Layout Structure

```
templates/
├── base.html                    # Root layout (navbar, footer, global scripts)
├── tournaments/
│   ├── base_tournament.html     # Tournament-specific layout (extends base.html)
│   ├── list.html                # Tournament listing
│   ├── detail.html              # Tournament detail page
│   ├── create.html              # Tournament creation wizard
│   ├── dashboard.html           # Organizer dashboard
│   ├── registration/
│   │   ├── form.html            # Registration form
│   │   ├── payment.html         # Payment submission
│   │   └── confirmation.html    # Registration success
│   ├── bracket/
│   │   ├── view.html            # Bracket visualization
│   │   └── match_card.html      # Match detail component (HTMX partial)
│   ├── matches/
│   │   ├── live_scoreboard.html # Live match scoreboard
│   │   └── result_form.html     # Result submission
│   └── partials/
│       ├── tournament_card.html # Reusable tournament card
│       ├── player_card.html     # Participant card
│       └── sponsor_logo.html    # Sponsor display
```

### Template Inheritance Pattern

```django
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}DeltaCrown{% endblock %}</title>
    
    <!-- Tailwind CSS -->
    <link href="{% static 'css/tailwind.output.css' %}" rel="stylesheet">
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    
    <!-- Alpine.js -->
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
    
    {% block extra_head %}{% endblock %}
</head>
<body class="bg-gray-900 text-white">
    {% include 'partials/navbar.html' %}
    
    <main class="container mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>
    
    {% include 'partials/footer.html' %}
    
    {% block extra_scripts %}{% endblock %}
</body>
</html>

<!-- templates/tournaments/base_tournament.html -->
{% extends 'base.html' %}

{% block content %}
<div class="tournament-layout">
    <!-- Tournament header -->
    <div class="tournament-header mb-6">
        {% block tournament_header %}{% endblock %}
    </div>
    
    <!-- Tournament content -->
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <!-- Sidebar -->
        <aside class="lg:col-span-1">
            {% block tournament_sidebar %}
                {% include 'tournaments/partials/sidebar.html' %}
            {% endblock %}
        </aside>
        
        <!-- Main content -->
        <section class="lg:col-span-3">
            {% block tournament_content %}{% endblock %}
        </section>
    </div>
</div>
{% endblock %}
```

### HTMX Integration Patterns

**1. Live Match Updates (WebSocket + HTMX)**

```django
<!-- templates/tournaments/matches/live_scoreboard.html -->
<div 
    hx-ext="ws"
    ws-connect="/ws/tournament/{{ tournament.id }}/"
    class="scoreboard"
>
    <div id="match-{{ match.id }}" class="match-card">
        <div class="team-score">
            <span class="team-name">{{ match.participant1_name }}</span>
            <span class="score" id="p1-score">{{ match.participant1_score }}</span>
        </div>
        <div class="vs">VS</div>
        <div class="team-score">
            <span class="team-name">{{ match.participant2_name }}</span>
            <span class="score" id="p2-score">{{ match.participant2_score }}</span>
        </div>
    </div>
</div>

<script>
    // Handle WebSocket updates
    document.body.addEventListener('tournament_update', function(event) {
        if (event.detail.type === 'match_update') {
            const data = event.detail.data;
            document.getElementById('p1-score').textContent = data.participant1_score;
            document.getElementById('p2-score').textContent = data.participant2_score;
        }
    });
</script>
```

**2. Dynamic Tournament Registration**

```django
<!-- templates/tournaments/registration/form.html -->
<form 
    hx-post="{% url 'tournament:register' tournament.id %}"
    hx-target="#registration-result"
    hx-swap="innerHTML"
    class="registration-form"
>
    {% csrf_token %}
    
    <!-- Auto-filled fields from user profile -->
    <input type="text" name="display_name" value="{{ user.display_name }}" readonly>
    
    <!-- Dynamic custom fields -->
    {% for field in tournament.custom_fields.all %}
        {% include 'tournaments/partials/custom_field.html' with field=field %}
    {% endfor %}
    
    <button type="submit" class="btn-primary">Register</button>
</form>

<div id="registration-result"></div>
```

**3. Bracket Node Interaction**

```django
<!-- templates/tournaments/bracket/view.html -->
<div class="bracket-container" x-data="{ selectedMatch: null }">
    {% for round in bracket_rounds %}
        <div class="bracket-round">
            {% for node in round.nodes %}
                <div 
                    class="bracket-node cursor-pointer"
                    @click="selectedMatch = {{ node.match_id }}"
                    hx-get="{% url 'tournament:match_detail' node.match_id %}"
                    hx-target="#match-modal"
                    hx-trigger="click"
                >
                    <div class="participant">{{ node.participant1_name }}</div>
                    <div class="participant">{{ node.participant2_name }}</div>
                </div>
            {% endfor %}
        </div>
    {% endfor %}
</div>

<!-- Match detail modal (populated by HTMX) -->
<div id="match-modal" class="modal"></div>
```

### Alpine.js Reactive Components

**Tournament Countdown Timer:**

```django
<div 
    x-data="{
        startTime: new Date('{{ tournament.start_time|date:'c' }}').getTime(),
        now: Date.now(),
        timeLeft: ''
    }"
    x-init="setInterval(() => {
        now = Date.now();
        const diff = startTime - now;
        if (diff > 0) {
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            timeLeft = `${days}d ${hours}h`;
        } else {
            timeLeft = 'Live Now!';
        }
    }, 1000)"
    class="countdown"
>
    <span x-text="timeLeft"></span>
</div>
```

### Component Organization

**Reusable Tournament Card:**

```django
<!-- templates/tournaments/partials/tournament_card.html -->
<div class="tournament-card bg-gray-800 rounded-lg overflow-hidden hover:shadow-xl transition">
    <!-- Banner -->
    <div class="relative h-48">
        <img src="{{ tournament.banner_image.url }}" alt="{{ tournament.title }}" class="w-full h-full object-cover">
        <div class="absolute top-2 right-2 bg-yellow-500 px-3 py-1 rounded text-sm font-bold">
            {{ tournament.get_status_display }}
        </div>
    </div>
    
    <!-- Content -->
    <div class="p-4">
        <h3 class="text-xl font-bold mb-2">{{ tournament.title }}</h3>
        <div class="flex items-center gap-4 text-sm text-gray-400 mb-4">
            <span>🎮 {{ tournament.game.name }}</span>
            <span>👥 {{ tournament.current_participants }}/{{ tournament.max_participants }}</span>
            <span>💰 {{ tournament.prize_pool }} BDT</span>
        </div>
        
        <!-- CTA -->
        <a href="{% url 'tournament:detail' tournament.id %}" class="btn-primary w-full text-center">
            View Details
        </a>
    </div>
</div>
```

### HTMX Event Naming Conventions

**Standard Events:**
- `htmx:configRequest` - Modify request before sending (add custom headers)
- `htmx:afterSwap` - After content is swapped
- `htmx:responseError` - Handle errors

**Custom Tournament Events:**
- `tournament:registered` - User registered for tournament
- `tournament:bracket_updated` - Bracket structure changed
- `match:started` - Match state changed to live
- `match:completed` - Match finished
- `dispute:created` - New dispute filed

**Example:**

```javascript
// Global event handlers
document.body.addEventListener('htmx:configRequest', (event) => {
    // Add CSRF token to all HTMX requests
    event.detail.headers['X-CSRFToken'] = getCookie('csrftoken');
});

document.body.addEventListener('tournament:registered', (event) => {
    // Show success notification
    showNotification('Registration successful!', 'success');
    
    // Update participant count
    htmx.trigger('#participant-count', 'refresh');
});
```

### Mobile-First Responsive Patterns

**Tailwind Responsive Utilities:**

```django
<!-- Desktop: 3-column grid, Mobile: 1-column -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {% for tournament in tournaments %}
        {% include 'tournaments/partials/tournament_card.html' %}
    {% endfor %}
</div>

<!-- Desktop: Horizontal layout, Mobile: Vertical stack -->
<div class="flex flex-col lg:flex-row gap-6">
    <div class="lg:w-2/3"><!-- Main content --></div>
    <div class="lg:w-1/3"><!-- Sidebar --></div>
</div>

<!-- Mobile: Hamburger menu, Desktop: Full navbar -->
<nav class="lg:flex hidden"><!-- Desktop nav --></nav>
<button class="lg:hidden" @click="mobileMenuOpen = true"><!-- Mobile toggle --></button>
```

### Static Asset Organization

```
static/
├── css/
│   ├── tailwind.config.js       # Tailwind configuration
│   ├── input.css                # Source CSS
│   └── tailwind.output.css      # Compiled CSS
├── js/
│   ├── tournament/
│   │   ├── bracket.js           # Bracket visualization logic
│   │   ├── match.js             # Match interactions
│   │   └── registration.js      # Registration flow
│   └── utils/
│       ├── notification.js      # Toast notifications
│       └── validation.js        # Client-side validation
└── img/
    └── tournaments/
        ├── placeholders/        # Default images
        └── icons/               # Game icons
```

**Key Benefits:**
- ✅ **Django Templates:** Server-side rendering for SEO and fast initial load
- ✅ **HTMX:** Partial updates without full page reload, minimal JavaScript
- ✅ **Alpine.js:** Reactive UI components for interactive elements
- ✅ **Tailwind CSS:** Rapid UI development with utility classes
- ✅ **Mobile-First:** Responsive design from smallest to largest screens
- ✅ **WebSocket Integration:** Real-time updates for live tournaments
- ✅ **Component Reusability:** DRY principle with partials and includes
- ✅ **Progressive Enhancement:** Works without JavaScript, enhanced with it

---

## 8. Security Architecture

### 8.1 Permission System

```python
# tournament_engine/permissions.py

from django.core.exceptions import PermissionDenied

class TournamentPermissions:
    
    @staticmethod
    def can_edit_tournament(user, tournament):
        """Check if user can edit tournament"""
        return (
            user.is_superuser or
            tournament.organizer == user
        )
    
    @staticmethod
    def can_verify_payments(user, tournament):
        """Check if user can verify payments"""
        return TournamentPermissions.can_edit_tournament(user, tournament)
    
    @staticmethod
    def can_resolve_disputes(user, tournament):
        """Check if user can resolve disputes"""
        return (
            user.is_superuser or
            tournament.organizer == user
        )
    
    @staticmethod

---

**Navigation:**
- [← Previous: Part 2.1 - Architecture Foundations](PART_2.1_ARCHITECTURE_FOUNDATIONS.md)
- [↑ Master Index](INDEX_MASTER_NAVIGATION.md)
- [→ Next: Part 2.3 - Real-Time & Security](PART_2.3_REALTIME_SECURITY.md)

---

**END OF PART 2.2**
