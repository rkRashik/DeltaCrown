# Module 5.4 Test Fixes Needed

## Current Status
- **17 passing tests** (up from 14)
- **14 failing tests** 
- **73% coverage** (target: ≥90%)

## Remaining Issues to Fix

### 1. Match Check Constraint: `chk_match_completed_has_winner`
**Error**: COMPLETED matches must have BOTH `winner_id` AND `loser_id`

**Location**: `test_happy_path_all_metrics`, `test_happy_path_multiple_tournaments`

**Fix**: Add `loser_id` to all Match.objects.create() with state=Match.COMPLETED:
```python
Match.objects.create(
    ...
    state=Match.COMPLETED,
    winner_id=registrations[0].id,
    loser_id=registrations[1].id,  # ADD THIS
)
```

**Files to fix**:
- `tests/test_analytics_service_module_5_4.py` lines ~154, ~450, ~460, ~470

### 2. PrizeTransaction.PROCESSED Does Not Exist
**Error**: `AttributeError: type object 'PrizeTransaction' has no attribute 'PROCESSED'`

**Location**: Multiple organizer analytics tests

**Fix**: Use `PrizeTransaction.Status.COMPLETED` instead of `PROCESSED`

**Files to fix**:
- `tests/test_analytics_service_module_5_4.py` - search for `PrizeTransaction.PROCESSED` and replace with `PrizeTransaction.Status.COMPLETED`

### 3. TournamentResult.rules_applied Required Field
**Error**: `ValidationError: {'rules_applied': ['This field cannot be blank.']}`

**Location**: `test_best_placement_only_runner_up`, `test_csv_with_placements_and_prizes`

**Fix**: Add `rules_applied={}` to TournamentResult.objects.create():
```python
TournamentResult.objects.create(
    tournament=tournament_completed,
    winner=regs[0],
    runner_up=regs[1],
    third_place=regs[2],
    determination_method='normal',
    rules_applied={},  # ADD THIS - required JSONField
)
```

**Files to fix**:
- `tests/test_analytics_service_module_5_4.py` lines ~583, ~688

### 4. Registration XOR Constraint: user_xor_team
**Error**: `IntegrityError: violates check constraint "registration_user_xor_team"`

**Location**: `test_csv_no_pii_display_names_only`, `test_get_participant_display_name_team`

**Root Cause**: Registration must have EITHER `user` OR `team_id`, NOT both

**Fix**: For team registrations, set `user=None`:
```python
# Team registration - user must be None
reg2 = Registration.objects.create(
    tournament=tournament_completed,
    user=None,  # CHANGE from users[1] to None
    team_id=team.id,
    status=Registration.CONFIRMED,
)
```

**Files to fix**:
- `tests/test_analytics_service_module_5_4.py` lines ~663, ~814

### 5. prefetch_related('payment_set') Invalid
**Error**: `AttributeError: Cannot find 'payment_set' on Registration object`

**Location**: AnalyticsService.export_tournament_csv()

**Root Cause**: Registration has no `payment_set` reverse relation

**Fix**: Remove `payment_set` from prefetch_related():
```python
# In analytics_service.py line ~395
registrations = Registration.objects.filter(
    tournament_id=tournament_id
).select_related(
    'user',
).order_by('id')  # REMOVE .prefetch_related('payment_set')
```

**Files to fix**:
- `apps/tournaments/services/analytics_service.py` line ~395

### 6. Logger Mock Path Incorrect
**Error**: `AttributeError: 'AnalyticsService' object has no attribute 'logger'`

**Location**: `test_performance_warning_threshold`

**Root Cause**: `logger` is a module-level variable, not a class attribute

**Fix**: Update monkeypatch path:
```python
# OLD (wrong):
monkeypatch.setattr('apps.tournaments.services.analytics_service.logger', mock_logger)

# NEW (correct):
import apps.tournaments.services.analytics_service as analytics_module
monkeypatch.setattr(analytics_module, 'logger', mock_logger)
```

**Files to fix**:
- `tests/test_analytics_service_module_5_4.py` line ~367

## Quick Fix Order

1. **Fix AnalyticsService.py** (Issue #5 - payment_set)
2. **Fix test fixtures** (Issues #1, #2, #3, #4, #6)
3. **Run tests** to verify ≥90% coverage

## Expected Coverage After Fixes
- All 31 tests passing
- Service coverage: **≥90%** (currently 73% with 17/31 tests)

## Next Steps After Tests Pass
1. Verify coverage ≥90%
2. Run all Module 5.4 tests
3. Create API views (3 endpoints)
4. Create integration tests (6 tests)
5. Write MODULE_5.4_COMPLETION_STATUS.md
6. Update MAP.md, trace.yml, verify_trace.py
7. Commit Module 5.4
