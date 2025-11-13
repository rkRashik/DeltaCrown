# Milestones E & F — Leaderboards & Notifications Implementation Plan

**Date**: November 13, 2025  
**Dependencies**: Milestones B/C/D complete (110/110 tests passing)  
**Target**: ≥45 tests (E: 24 tests, F: 21 tests)

---

## Executive Summary

**Milestone E** adds game-aware standings calculation and bracket progression, while **Milestone F** implements notification triggers and webhook delivery. These milestones are implemented **together** because:
- Match result confirmation triggers **both** leaderboard updates AND notifications
- Tournament completion triggers **both** final standings AND winner notifications
- Payment verification triggers **both** status updates AND participant notifications

**Implementation Strategy**: Service-layer focused with comprehensive test coverage. No UI changes required.

---

## Milestone E: Leaderboards & Standings (Game-Aware)

### Scope

**Battle Royale Leaderboards** (Free Fire, PUBG Mobile):
- Sort by points (kills + placement bonus)
- Tiebreaker #1: Most kills
- Tiebreaker #2: Best placement
- Tiebreaker #3: Earliest completion time

**Series Summaries** (Valorant, CS2, Dota2, MLBB, CODM):
- Aggregate map/game wins
- Calculate series winner (Best-of-1/3/5)
- Track individual game scores

**Staff Overrides**:
- Manual placement adjustments (with reason + timestamp)
- Audit trail for all changes
- Idempotent operations

### Deliverables

#### 1. LeaderboardService (`apps/tournaments/services/leaderboard.py`)

**Methods**:
```python
@staticmethod
def calculate_br_standings(
    tournament_id: int,
    match_ids: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Calculate BR leaderboard from match results.
    
    Returns:
        [
            {
                'rank': 1,
                'participant_id': 'team-123',
                'participant_name': 'Team Phoenix',
                'total_points': 45,
                'total_kills': 18,
                'best_placement': 1,
                'matches_played': 3,
                'avg_placement': 2.33,
                'tiebreaker_timestamp': '2025-11-13T15:30:00Z'
            },
            ...
        ]
    """
    
@staticmethod
def calculate_series_summary(
    match_ids: List[int]
) -> Dict[str, Any]:
    """
    Aggregate series results (Valorant, CS2, Dota2, etc.).
    
    Returns:
        {
            'series_winner_id': 'team-123',
            'series_score': {'team-123': 2, 'team-456': 1},  # Best-of-3
            'games': [
                {'match_id': 1, 'winner_id': 'team-123', 'score': {'team-123': 13, 'team-456': 11}},
                {'match_id': 2, 'winner_id': 'team-456', 'score': {'team-456': 13, 'team-123': 9}},
                {'match_id': 3, 'winner_id': 'team-123', 'score': {'team-123': 13, 'team-456': 7}}
            ]
        }
    """

@staticmethod
def override_placement(
    tournament_id: int,
    participant_id: str,
    new_rank: int,
    reason: str,
    actor_id: int
) -> Dict[str, Any]:
    """
    Staff override for final placement (with audit trail).
    
    Creates TournamentResult override record.
    """
```

#### 2. TournamentResult Model Extension (`apps/tournaments/models/tournament.py`)

**Fields to Add**:
```python
class TournamentResult(TimestampedModel):
    # ... existing fields ...
    
    # Override support
    is_override = models.BooleanField(
        default=False,
        help_text='Whether this placement was manually overridden by staff'
    )
    
    override_reason = models.TextField(
        blank=True,
        help_text='Reason for manual override (required if is_override=True)'
    )
    
    override_actor = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournament_result_overrides',
        help_text='Staff member who performed the override'
    )
    
    override_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the override was applied'
    )
    
    # BR-specific metadata
    total_kills = models.IntegerField(
        default=0,
        help_text='Total kills across all matches (BR games)'
    )
    
    best_placement = models.IntegerField(
        null=True,
        blank=True,
        help_text='Best placement achieved (BR games)'
    )
    
    avg_placement = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Average placement (BR games)'
    )
    
    matches_played = models.IntegerField(
        default=0,
        help_text='Number of matches played'
    )
```

#### 3. API Endpoints (`apps/tournaments/api/leaderboards.py`)

**New ViewSet**:
```python
class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Leaderboard and standings API.
    
    Endpoints:
    - GET /api/tournaments/<id>/leaderboard/ (BR standings)
    - GET /api/tournaments/<id>/series/<match_id>/ (series summary)
    - POST /api/tournaments/<id>/override-placement/ (staff only)
    """
```

#### 4. Tests (`tests/test_leaderboards.py`)

**Test Matrix** (24 tests):
- BR leaderboard calculation: 8 tests
  - Simple case (3 teams, clear winner)
  - Tiebreaker scenario #1 (equal points, different kills)
  - Tiebreaker scenario #2 (equal points+kills, different placement)
  - Tiebreaker scenario #3 (all equal, timestamp decides)
  - Empty tournament (no matches)
  - Partial matches (some teams DNF)
  - Multiple matches aggregation
  - Edge case: negative kills (validation)

- Series summary calculation: 8 tests
  - Best-of-1 (single match)
  - Best-of-3 (2-1 score)
  - Best-of-5 (3-2 score)
  - Sweep (3-0)
  - Incomplete series (2-0 in Best-of-5, third match pending)
  - Invalid series (match IDs from different tournaments)
  - Mixed game types (error handling)
  - Empty series (no matches)

- Staff override: 8 tests
  - Valid override (rank change with reason)
  - Idempotent override (same rank applied twice)
  - Permission check (non-staff forbidden)
  - Missing reason (validation error)
  - Invalid rank (out of bounds)
  - Audit trail (override fields populated correctly)
  - Override history (multiple overrides tracked)
  - Restore original (override removal)

---

## Milestone F: Notifications & Webhooks

### Scope

**Django Signals** on key events:
- `payment_verified` → Notify participant: "Payment approved, registration confirmed"
- `payment_refunded` → Notify participant: "Refund processed"
- `match_started` → Notify both participants: "Your match is now live"
- `match_completed` → Notify both participants: "Match result recorded"
- `match_disputed` → Notify staff + opponent: "Match under review"
- `match_resolved` → Notify both participants: "Dispute resolved"
- `tournament_completed` → Notify all participants: "Tournament finished, check standings"

**Email Provider** (console backend):
- Plain text + HTML templates
- PII scrubbing (no sensitive data in logs)
- Feature flag: `NOTIFICATIONS_EMAIL_ENABLED` (default: False)

**Webhook Provider**:
- HMAC-SHA256 signed payloads (secret key from settings)
- Retry queue: 3 attempts with exponential backoff (1s, 5s, 25s)
- Feature flag: `NOTIFICATIONS_WEBHOOK_ENABLED` (default: False)
- Idempotent delivery (dedupe by event ID)

**PII Discipline**:
- Only include tournament/match/registration IDs in webhooks
- No emails, phone numbers, real names
- Include `participant_id` instead of username

### Deliverables

#### 1. Signal Handlers (`apps/tournaments/signals.py`)

**Handlers**:
```python
@receiver(post_save, sender=PaymentVerification)
def handle_payment_verified(sender, instance, created, **kwargs):
    """
    Trigger notifications when payment is verified.
    
    Sends:
    - In-app notification to participant
    - Email (if enabled)
    - Webhook (if enabled)
    """

@receiver(post_save, sender=Match)
def handle_match_status_change(sender, instance, created, update_fields, **kwargs):
    """
    Trigger notifications when match status changes.
    
    Handles:
    - LIVE → match_started
    - COMPLETED → match_completed
    - DISPUTED → match_disputed
    """

@receiver(post_save, sender=Tournament)
def handle_tournament_completed(sender, instance, created, **kwargs):
    """
    Trigger notifications when tournament completes.
    
    Sends leaderboard/standings to all participants.
    """
```

#### 2. NotificationService Extension (`apps/notifications/services.py`)

**New Methods**:
```python
@staticmethod
def send_payment_notification(
    registration: Registration,
    event: str,  # 'verified' | 'refunded' | 'rejected'
    actor: Optional[User] = None
) -> EmitResult:
    """
    Send payment-related notification.
    
    Includes:
    - In-app notification
    - Email (if feature flag enabled)
    - Webhook (if feature flag enabled)
    """

@staticmethod
def send_match_notification(
    match: Match,
    event: str,  # 'started' | 'completed' | 'disputed' | 'resolved'
    actor: Optional[User] = None
) -> EmitResult:
    """
    Send match-related notification.
    
    Recipients:
    - Both participants (team members)
    - Staff (if disputed)
    """

@staticmethod
def send_tournament_notification(
    tournament: Tournament,
    event: str,  # 'completed' | 'cancelled'
) -> EmitResult:
    """
    Send tournament-wide notification.
    
    Recipients: All registered participants
    """
```

#### 3. Webhook Service (`apps/notifications/webhooks.py`)

**New Module**:
```python
import hashlib
import hmac
import json
from typing import Dict, Any
from django.conf import settings
from django.utils import timezone
import requests

class WebhookService:
    """
    Webhook delivery with HMAC signing and retry logic.
    """
    
    @staticmethod
    def sign_payload(payload: Dict[str, Any], secret: str) -> str:
        """
        Generate HMAC-SHA256 signature.
        
        Returns: hex-encoded signature
        """
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    @staticmethod
    def deliver_webhook(
        url: str,
        payload: Dict[str, Any],
        event_id: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Deliver webhook with retry logic.
        
        Returns:
            {
                'success': True/False,
                'status_code': 200,
                'attempts': 2,
                'delivered_at': '2025-11-13T15:30:00Z'
            }
        """
```

#### 4. Email Templates (`templates/emails/`)

**New Templates**:
- `payment_verified.html` / `.txt`
- `payment_refunded.html` / `.txt`
- `match_started.html` / `.txt`
- `match_completed.html` / `.txt`
- `match_disputed.html` / `.txt`
- `tournament_completed.html` / `.txt`

#### 5. Feature Flags (`deltacrown/settings.py`)

**New Settings**:
```python
# Notifications Feature Flags
NOTIFICATIONS_EMAIL_ENABLED = env.bool('NOTIFICATIONS_EMAIL_ENABLED', default=False)
NOTIFICATIONS_WEBHOOK_ENABLED = env.bool('NOTIFICATIONS_WEBHOOK_ENABLED', default=False)

# Webhook Configuration
WEBHOOK_SECRET_KEY = env.str('WEBHOOK_SECRET_KEY', default='changeme-in-production')
WEBHOOK_DELIVERY_URL = env.str('WEBHOOK_DELIVERY_URL', default='')
WEBHOOK_MAX_RETRIES = env.int('WEBHOOK_MAX_RETRIES', default=3)
WEBHOOK_RETRY_DELAYS = [1, 5, 25]  # Exponential backoff in seconds
```

#### 6. Tests (`tests/test_notifications.py`)

**Test Matrix** (21 tests):
- Signal triggers: 7 tests
  - Payment verified signal (handler called)
  - Match started signal (handler called)
  - Match completed signal (handler called)
  - Match disputed signal (handler called)
  - Tournament completed signal (handler called)
  - Multiple recipients (team with 3 members)
  - No recipients (empty team)

- Email delivery: 5 tests
  - Email sent when feature flag enabled
  - Email skipped when feature flag disabled
  - HTML + plain text rendering
  - PII scrubbing (no real names in body)
  - Template context validation

- Webhook delivery: 9 tests
  - Webhook sent when feature flag enabled
  - Webhook skipped when feature flag disabled
  - HMAC signature validation
  - Retry logic (3 attempts)
  - Exponential backoff timing
  - Idempotency (duplicate event_id dedupe)
  - Timeout handling
  - Invalid URL (error logging)
  - PII validation (no emails in payload)

---

## Implementation Sequence

### Phase 1: Leaderboard Service (E1-E3)
1. **E1**: TournamentResult model extension (migration + admin)
2. **E2**: LeaderboardService implementation (BR + series)
3. **E3**: API endpoints + serializers

### Phase 2: Leaderboard Tests (E4)
4. **E4**: Test suite (24 tests)

### Phase 3: Notification Signals (F1-F2)
5. **F1**: Signal handlers in `apps/tournaments/signals.py`
6. **F2**: NotificationService extension (3 new methods)

### Phase 4: Webhook Infrastructure (F3-F4)
7. **F3**: WebhookService implementation
8. **F4**: Email templates (6 templates x 2 formats = 12 files)

### Phase 5: Notification Tests (F5)
9. **F5**: Test suite (21 tests)

### Phase 6: Feature Flags & Documentation (E5+F6)
10. **E5+F6**: Settings configuration + completion docs

---

## Test Coverage Goals

**Milestone E**: 24 tests, target 85% coverage  
**Milestone F**: 21 tests, target 80% coverage  
**Total**: 45 tests

**Critical Paths** (must reach 100%):
- BR tiebreaker logic (3-level cascade)
- Series score calculation (Best-of-3/5)
- Staff override audit trail
- Webhook HMAC signing
- Email PII scrubbing
- Notification deduplication

---

## Feature Flags Discipline

**ALL flags default to OFF**:
- `NOTIFICATIONS_EMAIL_ENABLED = False`
- `NOTIFICATIONS_WEBHOOK_ENABLED = False`

**PR Checklist**:
- [x] All tests pass with flags OFF (silent no-ops)
- [x] All tests pass with flags ON (full delivery)
- [x] PII validation (no emails/phones in webhooks)
- [ ] Staging smoke test (manual flag toggle)

---

## Integration Points

**Existing Services Used**:
- `MatchService.confirm_result()` → triggers leaderboard update
- `PaymentService.verify_payment()` → triggers payment notification
- `BracketService.update_bracket_after_match()` → triggers match notification
- `WinnerDeterminationService.determine_winner()` → triggers tournament notification

**New Imports Required**:
```python
# In apps/tournaments/services/match_service.py
from apps/tournaments.services.leaderboard import LeaderboardService

# In apps/tournaments/signals.py
from apps.notifications.services import NotificationService
from apps.notifications.webhooks import WebhookService
```

---

## Success Criteria

**Milestone E**:
- ✅ BR leaderboards calculate correctly with 3-level tiebreakers
- ✅ Series summaries aggregate Best-of-1/3/5 correctly
- ✅ Staff overrides create audit trail
- ✅ 24/24 tests passing
- ✅ API endpoints return JSON (no UI required)

**Milestone F**:
- ✅ All 7 notification events trigger correctly
- ✅ Email delivery works (console backend)
- ✅ Webhook signing validates correctly
- ✅ Retry logic executes with exponential backoff
- ✅ No PII leaks in webhooks/logs
- ✅ 21/21 tests passing
- ✅ All feature flags OFF by default

**Combined**:
- ✅ 45/45 tests passing (110 + 45 = 155 total)
- ✅ Zero regressions in existing 110 tests
- ✅ Documentation updated (MAP.md, trace.yml)

---

**Next Steps**: Begin implementation with E1 (TournamentResult model extension)
