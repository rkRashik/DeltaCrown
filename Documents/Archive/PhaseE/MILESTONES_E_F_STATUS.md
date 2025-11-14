# Milestones E & F — Implementation Status

**Date**: November 13, 2025  
**Status**: Phase 1 Complete (Model Extension), Phases 2-6 Ready for Implementation

---

## ✅ COMPLETED: Phase 1 - TournamentResult Model Extension

### Migration Applied: `0013_add_leaderboard_fields`

**New Fields Added to TournamentResult**:

1. **Staff Override Support**:
   - `is_override` (Boolean) - Manual placement flag
   - `override_reason` (TextField) - Reason for override
   - `override_actor` (ForeignKey to User) - Staff who performed override
   - `override_timestamp` (DateTimeField) - When override occurred

2. **BR Leaderboard Metadata** (Free Fire, PUBG Mobile):
   - `total_kills` (Integer) - Total kills across all matches
   - `best_placement` (Integer) - Best placement achieved (1=1st)
   - `avg_placement` (Decimal) - Average placement across matches
   - `matches_played` (Integer) - Number of matches played

3. **Series Metadata** (Valorant, CS2, Dota2, MLBB, CODM):
   - `series_score` (JSONField) - Series winner breakdown `{"team-123": 2, "team-456": 1}`
   - `game_results` (JSONField) - Individual game results `[{"match_id": 1, "winner_id": "team-123"}, ...]`

**Database Status**: ✅ Migration applied successfully

---

## 📋 REMAINING IMPLEMENTATION (Phases 2-6)

### Phase 2: LeaderboardService Implementation

**File**: `apps/tournaments/services/leaderboard.py` (NEW)

**Methods to Implement**:

```python
class LeaderboardService:
    @staticmethod
    def calculate_br_standings(tournament_id: int, match_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        Calculate BR leaderboard from match results.
        
        Algorithm:
        1. Fetch all matches for tournament (or specific matches)
        2. Parse lobby_info JSON for kills/placement per team
        3. Calculate points using calc_ff_points() or calc_pubgm_points()
        4. Aggregate by participant_id
        5. Sort by: total_points DESC, total_kills DESC, best_placement ASC, earliest_completion ASC
        6. Return list with ranks
        
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
        pass
    
    @staticmethod
    def calculate_series_summary(match_ids: List[int]) -> Dict:
        """
        Aggregate series results (Best-of-1/3/5).
        
        Algorithm:
        1. Fetch matches by IDs
        2. Count wins per participant
        3. Determine series winner (first to reach majority)
        4. Return series score + game-by-game breakdown
        
        Returns:
            {
                'series_winner_id': 'team-123',
                'series_score': {'team-123': 2, 'team-456': 1},
                'games': [
                    {'match_id': 1, 'winner_id': 'team-123', 'score': {...}},
                    {'match_id': 2, 'winner_id': 'team-456', 'score': {...}},
                    {'match_id': 3, 'winner_id': 'team-123', 'score': {...}}
                ]
            }
        """
        pass
    
    @staticmethod
    @transaction.atomic
    def override_placement(
        tournament_id: int,
        participant_id: str,
        new_rank: int,
        reason: str,
        actor_id: int
    ) -> Dict:
        """
        Staff override for final placement (with audit trail).
        
        Algorithm:
        1. Validate tournament exists and completed
        2. Fetch existing TournamentResult
        3. Update placement fields
        4. Set is_override=True, override_reason, override_actor, override_timestamp
        5. Save result
        6. Log audit event
        
        Returns:
            {
                'success': True,
                'result_id': 123,
                'old_rank': 2,
                'new_rank': 1,
                'override_timestamp': '2025-11-13T15:30:00Z'
            }
        """
        pass
```

**Test File**: `tests/test_leaderboards.py` (NEW)
- 8 BR leaderboard tests (tiebreaker scenarios, empty tournaments, partial matches)
- 8 series summary tests (Best-of-1/3/5, sweeps, incomplete series)
- 8 staff override tests (permissions, idempotency, audit trail)
- **Total**: 24 tests

---

### Phase 3: Leaderboard API Endpoints

**File**: `apps/tournaments/api/leaderboards.py` (NEW)

**ViewSet**:

```python
class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Leaderboard and standings API.
    
    Endpoints:
    - GET /api/tournaments/<id>/leaderboard/ (BR standings)
    - GET /api/tournaments/<id>/series/<match_id>/ (series summary)
    - POST /api/tournaments/<id>/override-placement/ (staff only)
    """
    
    @action(detail=True, methods=['get'])
    def leaderboard(self, request, pk=None):
        """
        Get BR leaderboard for tournament.
        
        Query params:
        - match_ids (optional): Comma-separated match IDs to include
        
        Returns: LeaderboardSerializer(many=True)
        """
        pass
    
    @action(detail=True, methods=['get'], url_path='series/(?P<match_id>[^/.]+)')
    def series(self, request, pk=None, match_id=None):
        """
        Get series summary for match.
        
        Returns: SeriesSummarySerializer
        """
        pass
    
    @action(detail=True, methods=['post'], url_path='override-placement')
    def override_placement(self, request, pk=None):
        """
        Staff override for placement (requires IsStaffOrAdmin permission).
        
        Body:
        {
            "participant_id": "team-123",
            "new_rank": 1,
            "reason": "Correction after manual review"
        }
        
        Returns: TournamentResultSerializer
        """
        pass
```

**Serializers** (`apps/tournaments/api/serializers_leaderboards.py`):
- `LeaderboardEntrySerializer`
- `SeriesSummarySerializer`
- `PlacementOverrideSerializer`

---

### Phase 4: Notification Signal Handlers

**File**: `apps/tournaments/signals.py` (EXTEND EXISTING)

**Handlers to Add**:

```python
@receiver(post_save, sender=PaymentVerification)
def handle_payment_verified(sender, instance, created, **kwargs):
    """
    Trigger notifications when payment is verified.
    
    Sends:
    - In-app notification to participant
    - Email (if NOTIFICATIONS_EMAIL_ENABLED)
    - Webhook (if NOTIFICATIONS_WEBHOOK_ENABLED)
    """
    if instance.status == 'VERIFIED':
        NotificationService.send_payment_notification(
            registration=instance.payment.registration,
            event='verified',
            actor=instance.verified_by
        )

@receiver(post_save, sender=Match)
def handle_match_status_change(sender, instance, created, update_fields, **kwargs):
    """
    Trigger notifications when match status changes.
    
    Handles:
    - state=LIVE → match_started
    - state=COMPLETED → match_completed
    - state=DISPUTED → match_disputed
    """
    if not created and update_fields and 'state' in update_fields:
        if instance.state == Match.LIVE:
            NotificationService.send_match_notification(
                match=instance,
                event='started'
            )
        elif instance.state == Match.COMPLETED:
            NotificationService.send_match_notification(
                match=instance,
                event='completed'
            )
        elif instance.state == Match.DISPUTED:
            NotificationService.send_match_notification(
                match=instance,
                event='disputed'
            )

@receiver(post_save, sender=Tournament)
def handle_tournament_completed(sender, instance, created, **kwargs):
    """
    Trigger notifications when tournament completes.
    
    Sends leaderboard/standings to all participants.
    """
    if not created and instance.status == Tournament.COMPLETED:
        NotificationService.send_tournament_notification(
            tournament=instance,
            event='completed'
        )
```

**Test File**: `tests/test_notification_signals.py` (NEW)
- 7 signal trigger tests
- **Total**: 7 tests

---

### Phase 5: Webhook Service Implementation

**File**: `apps/notifications/webhooks.py` (NEW)

**Class**:

```python
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
        
        Retry delays: [1s, 5s, 25s] (exponential backoff)
        
        Returns:
            {
                'success': True/False,
                'status_code': 200,
                'attempts': 2,
                'delivered_at': '2025-11-13T15:30:00Z'
            }
        """
        attempts = 0
        last_error = None
        
        for delay in settings.WEBHOOK_RETRY_DELAYS[:max_retries]:
            attempts += 1
            try:
                # Sign payload
                signature = WebhookService.sign_payload(payload, settings.WEBHOOK_SECRET_KEY)
                
                # Send HTTP POST
                response = requests.post(
                    url,
                    json=payload,
                    headers={
                        'X-DeltaCrown-Signature': signature,
                        'X-DeltaCrown-Event-ID': event_id,
                        'Content-Type': 'application/json'
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    return {
                        'success': True,
                        'status_code': 200,
                        'attempts': attempts,
                        'delivered_at': timezone.now().isoformat()
                    }
                
                last_error = f"HTTP {response.status_code}"
                
            except requests.exceptions.RequestException as e:
                last_error = str(e)
            
            # Wait before retry (except on last attempt)
            if attempts < max_retries:
                time.sleep(delay)
        
        # All retries failed
        return {
            'success': False,
            'attempts': attempts,
            'last_error': last_error
        }
```

**Test File**: `tests/test_webhooks.py` (NEW)
- 9 webhook tests (signing, retry logic, idempotency, PII validation)
- **Total**: 9 tests

---

### Phase 6: Email Templates & Feature Flags

**Email Templates** (`templates/emails/`):

Create 6 notification templates (HTML + plain text):
1. `payment_verified.html` / `.txt`
2. `payment_refunded.html` / `.txt`
3. `match_started.html` / `.txt`
4. `match_completed.html` / `.txt`
5. `match_disputed.html` / `.txt`
6. `tournament_completed.html` / `.txt`

**Feature Flags** (`deltacrown/settings.py`):

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

**Test File**: `tests/test_email_notifications.py` (NEW)
- 5 email delivery tests
- **Total**: 5 tests

---

## Test Coverage Summary

| Phase | Test File | Tests | Focus |
|-------|-----------|-------|-------|
| 2 | `test_leaderboards.py` | 24 | BR/Series/Override |
| 4 | `test_notification_signals.py` | 7 | Signal triggers |
| 5 | `test_webhooks.py` | 9 | Signing/Retry/PII |
| 6 | `test_email_notifications.py` | 5 | Email delivery |
| **TOTAL** | | **45** | **E: 24, F: 21** |

**Current Status**: 0/45 tests (awaiting implementation)  
**Combined Total**: 110 (existing) + 45 (new) = **155 tests**

---

## Implementation Order

### Week 1: Milestone E (Leaderboards)
1. **Day 1-2**: LeaderboardService implementation + 24 tests
2. **Day 3**: API endpoints + serializers
3. **Day 4**: Integration testing + documentation

### Week 2: Milestone F (Notifications)
1. **Day 1**: Signal handlers + 7 tests
2. **Day 2**: WebhookService + 9 tests
3. **Day 3**: Email templates + 5 tests
4. **Day 4**: Feature flags + integration testing

### Week 3: Integration & Documentation
1. **Day 1**: End-to-end testing (match completion → leaderboard update + notifications)
2. **Day 2**: Staging smoke tests
3. **Day 3**: Documentation (MAP.md, trace.yml, completion reports)
4. **Day 4**: PR preparation

---

## Next Immediate Steps

1. ✅ **Implement LeaderboardService.calculate_br_standings()** (highest priority)
2. ✅ **Create test_leaderboards.py with first 8 BR tests**
3. ✅ **Implement LeaderboardService.calculate_series_summary()**
4. ✅ **Add remaining 16 tests (series + override)**
5. ⏳ **Create API endpoints** (after service layer tested)
6. ⏳ **Implement notification signals** (after API tested)
7. ⏳ **Create WebhookService** (after signals tested)
8. ⏳ **Add email templates** (after webhooks tested)

---

## Integration Points

**Existing Services to Call**:
- `apps/tournaments/games/points.py` - `calc_ff_points()`, `calc_pubgm_points()`
- `apps/tournaments/models/match.py` - Match.lobby_info field (BR kills/placement)
- `apps/tournaments/models/result.py` - TournamentResult (now has leaderboard fields)
- `apps/notifications/services.py` - NotificationService (existing, extend with 3 methods)

**New Services Created**:
- `apps/tournaments/services/leaderboard.py` - LeaderboardService (Phase 2)
- `apps/notifications/webhooks.py` - WebhookService (Phase 5)

---

## Success Criteria

**Milestone E**:
- ✅ TournamentResult model extended (10 new fields)
- ⏳ LeaderboardService with 3 methods
- ⏳ API endpoints (3 actions)
- ⏳ 24/24 tests passing

**Milestone F**:
- ⏳ Signal handlers (3 events)
- ⏳ WebhookService with HMAC signing
- ⏳ Email templates (6 templates × 2 formats)
- ⏳ Feature flags (all OFF by default)
- ⏳ 21/21 tests passing

**Combined**:
- ✅ Migration applied (0013_add_leaderboard_fields)
- ⏳ 45/45 tests passing
- ⏳ Zero regressions in existing 110 tests
- ⏳ Documentation updated (MAP.md, trace.yml, completion reports)

---

**Current Phase**: Phase 1 Complete ✅  
**Next Phase**: Phase 2 - LeaderboardService Implementation  
**ETA**: 2-3 weeks for full E+F implementation
