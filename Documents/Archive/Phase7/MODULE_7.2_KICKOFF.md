# Module 7.2 Kickoff: DeltaCoin Shop (Spend Flows)

**Date**: November 11, 2025  
**Status**: In Progress  
**Previous Module**: 7.1 - Coin System ✅ Complete (v7.1.0-economy)

---

## Executive Summary

Module 7.2 builds on the 7.1 ledger foundation to implement spend authorization flows:
- **Catalog**: Admin-only item model (SKU, price, active flag)
- **Spend Pipeline**: authorize → capture/release with atomic state transitions
- **Refunds**: Compensating credit transactions with partial refund support
- **Available Balance**: Computed balance accounting for active holds

**Approach**: Test-first, service layer only, minimal schema, strict idempotency

---

## Scope

### In Scope ✅
1. `ShopItem` model (sku, price, active) with lightweight admin
2. `ReservationHold` model (wallet FK, amount, sku, status, expires_at, idempotency_key)
3. Four spend pipeline services:
   - `authorize_spend()` - Create hold with status='authorized'
   - `capture()` - Convert hold to debit, mark 'captured'
   - `release()` - Void hold, mark 'released'
   - `refund()` - Compensating credit for captured transactions
4. `get_available_balance()` - Helper for balance minus active holds
5. Comprehensive test coverage (≥90% services, 100% state machine)

### Out of Scope ❌
- REST API endpoints (Module 7.3)
- Frontend UI (Module 7.4)
- Stock management/inventory
- Promotional codes (Module 7.5)
- Background expiry job (operational task)
- User-facing catalog browsing

---

## Planning Constraints

### Test-First Approach
- Scaffold all tests before implementation
- Mark tests xfail/skip until ready
- Remove markers as implementation completes
- Target: ~43 tests across 5 files

### Service Layer Only
- No views, serializers, or REST endpoints
- Pure business logic functions
- All state changes via service layer
- Admin models only for catalog management

### Minimal Schema
- 2 new models: `ShopItem`, `ReservationHold`
- Zero changes to Module 7.1 tables
- Available balance computed, not stored
- Indexes for query efficiency, cleanup jobs

### Strict Idempotency
- Derived keys for multi-phase operations:
  - `{key}_auth` for authorization
  - `{key}_capture` for capture
  - `{key}_release` for release
  - `{key}_refund` for refund
- Cross-operation key collision → `IdempotencyConflict`
- Payload validation on replay (amount/sku must match)
- DB unique constraint ensures single-apply

### PII Discipline
- No PII in models (wallet IDs only)
- No PII in service outputs (wallet_id, hold_id, amount)
- No PII in idempotency keys
- Logs use generic identifiers (hold_id, sku)

---

## Models Design

### ShopItem (Catalog)

```python
class ShopItem(models.Model):
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['sku']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['active', 'sku']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(price__gt=0), name='shop_item_price_positive'),
        ]
```

**Rationale**:
- `sku` unique for inventory identity
- `price` always positive (CHECK constraint)
- `active` flag for soft disable (no deletion)
- No stock, categories, descriptions (minimal scope)

### ReservationHold (Spend Authorization)

```python
class ReservationHold(models.Model):
    STATUS_CHOICES = [
        ('authorized', 'Authorized'),
        ('captured', 'Captured'),
        ('released', 'Released'),
        ('expired', 'Expired'),
    ]
    
    wallet = models.ForeignKey('economy.DeltaCrownWallet', on_delete=models.PROTECT, related_name='holds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=50)  # Denormalized for audit trail
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='authorized')
    expires_at = models.DateTimeField()
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['wallet', 'status']),
            models.Index(fields=['expires_at']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name='hold_amount_positive'),
            models.CheckConstraint(
                check=models.Q(status__in=['authorized', 'captured', 'released', 'expired']),
                name='hold_status_valid'
            ),
            models.CheckConstraint(
                check=models.Q(expires_at__gt=models.F('created_at')),
                name='hold_expires_after_created'
            ),
            models.UniqueConstraint(
                fields=['idempotency_key'],
                condition=models.Q(idempotency_key__isnull=False),
                name='hold_idempotency_key_unique'
            ),
        ]
```

**Rationale**:
- `wallet` FK with PROTECT (no cascade deletes)
- `amount` always positive (CHECK constraint)
- `sku` denormalized for audit trail (ShopItem may change/delete)
- `status` enum with CHECK constraint (state machine enforcement)
- `expires_at` for timeout logic (background job marks expired)
- `idempotency_key` partial unique (NULL allowed, unique when present)
- Indexes for efficient queries: active holds per wallet, expiry cleanup

---

## Service API

### authorize_spend()

```python
def authorize_spend(
    wallet: DeltaCrownWallet,
    amount: Decimal,
    sku: str,
    idempotency_key: Optional[str] = None,
    expires_in: timedelta = timedelta(minutes=15),
    meta: Optional[dict] = None,
) -> dict:
    """
    Create a reservation hold for a future purchase.
    
    Returns:
        {
            'hold_id': int,
            'wallet_id': int,
            'amount': Decimal,
            'sku': str,
            'status': 'authorized',
            'expires_at': datetime,
            'available_balance': Decimal,
        }
    
    Raises:
        InvalidAmount: amount <= 0
        InsufficientFunds: available_balance < amount
        InvalidWallet: wallet not found
        IdempotencyConflict: key exists with different payload
    """
```

**Logic**:
1. Validate amount > 0
2. Check available balance (balance - active holds) ≥ amount
3. Check idempotency (if key exists, validate payload and return existing)
4. Create `ReservationHold` with status='authorized', expires_at=now+expires_in
5. Return hold details with updated available_balance

### capture()

```python
def capture(
    wallet: DeltaCrownWallet,
    hold_id: int,
    idempotency_key: Optional[str] = None,
) -> dict:
    """
    Convert a hold to a debit transaction (finalize purchase).
    
    Returns:
        {
            'hold_id': int,
            'transaction_id': int,
            'wallet_id': int,
            'balance_after': Decimal,
            'captured_at': datetime,
        }
    
    Raises:
        HoldNotFound: hold_id doesn't exist
        InvalidStateTransition: hold not in 'authorized' state
        HoldExpired: hold past expires_at
        IdempotencyConflict: key exists with different payload
    """
```

**Logic**:
1. Lock hold row (SELECT FOR UPDATE)
2. Validate status='authorized', not expired
3. Check idempotency (if key exists, return original capture result)
4. Call `debit(wallet, amount, reason='PURCHASE', meta={'sku': sku, 'hold_id': hold_id})`
5. Update hold status='captured'
6. Return capture details

### release()

```python
def release(
    wallet: DeltaCrownWallet,
    hold_id: int,
    idempotency_key: Optional[str] = None,
) -> dict:
    """
    Void a hold without debiting (cancel authorization).
    
    Returns:
        {
            'hold_id': int,
            'wallet_id': int,
            'released_at': datetime,
            'available_balance': Decimal,
        }
    
    Raises:
        HoldNotFound: hold_id doesn't exist
        InvalidStateTransition: hold not in 'authorized' state
        IdempotencyConflict: key exists with different payload
    """
```

**Logic**:
1. Lock hold row (SELECT FOR UPDATE)
2. Validate status='authorized' (expired holds can be released)
3. Check idempotency (if key exists, return original release result)
4. Update hold status='released'
5. Return release details with updated available_balance

### refund()

```python
def refund(
    wallet: DeltaCrownWallet,
    transaction_id: int,
    amount: Decimal,
    idempotency_key: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict:
    """
    Issue a compensating credit for a captured transaction.
    
    Returns:
        {
            'refund_transaction_id': int,
            'original_transaction_id': int,
            'wallet_id': int,
            'balance_after': Decimal,
        }
    
    Raises:
        InvalidAmount: amount <= 0 or amount > original transaction
        TransactionNotFound: transaction_id doesn't exist
        InvalidTransaction: transaction not a debit or not PURCHASE reason
        IdempotencyConflict: key exists with different payload
    """
```

**Logic**:
1. Lock wallet (SELECT FOR UPDATE)
2. Fetch original transaction, validate it's a debit with reason='PURCHASE'
3. Validate amount ≤ original transaction amount
4. Check idempotency (if key exists, return original refund)
5. Call `credit(wallet, amount, reason='REFUND', meta={'original_transaction_id': transaction_id})`
6. Return refund details

### get_available_balance()

```python
def get_available_balance(wallet: DeltaCrownWallet) -> Decimal:
    """
    Calculate available balance accounting for active holds.
    
    Returns:
        wallet.cached_balance - SUM(holds.amount WHERE status='authorized')
    """
```

**Logic**:
1. Read wallet.cached_balance
2. Aggregate SUM(amount) from holds WHERE wallet_id=wallet.id AND status='authorized'
3. Return balance - held_total (can be negative if overdraft allowed)

---

## State Machine

```
┌────────────┐
│ authorized │ (initial state from authorize_spend)
└─────┬──────┘
      │
      ├──────► capture() ──────► ┌──────────┐ (terminal)
      │                          │ captured │
      │                          └──────────┘
      │
      ├──────► release() ─────── ┌──────────┐ (terminal)
      │                          │ released │
      │                          └──────────┘
      │
      └──────► timeout ──────────► ┌─────────┐ (terminal, background job)
                                   │ expired │
                                   └─────────┘
```

**Valid Transitions**:
- `authorized` → `captured` (via capture)
- `authorized` → `released` (via release)
- `authorized` → `expired` (via timeout, background job)

**Invalid Transitions** (raise `InvalidStateTransition`):
- `captured` → any (terminal state)
- `released` → any (terminal state)
- `expired` → `captured` (expired holds cannot be captured)

**Idempotency on Terminal States**:
- Replay of `capture()` on `captured` hold → returns original result
- Replay of `release()` on `released` hold → returns original result
- Replay with different operation → `IdempotencyConflict`

---

## Test Plan

### Test Files (~43 tests total)

1. **test_authorize_capture_release_module_7_2.py** (~20 tests)
   - `test_authorize_creates_hold_with_correct_status`
   - `test_authorize_reduces_available_balance`
   - `test_authorize_insufficient_funds_raises`
   - `test_authorize_idempotency_replay_returns_original`
   - `test_authorize_cross_op_collision_raises`
   - `test_capture_creates_debit_transaction`
   - `test_capture_transitions_hold_to_captured`
   - `test_capture_idempotency_replay_returns_original`
   - `test_capture_expired_hold_raises`
   - `test_capture_invalid_status_raises` (released, expired, captured)
   - `test_capture_updates_wallet_balance`
   - `test_release_transitions_hold_to_released`
   - `test_release_no_debit_transaction`
   - `test_release_increases_available_balance`
   - `test_release_idempotency_replay_returns_original`
   - `test_release_invalid_status_raises` (captured, released)
   - `test_release_expired_hold_succeeds` (idempotent no-op)
   - `test_hold_expiry_timestamp_correct`
   - `test_multiple_holds_reduce_available_balance`
   - `test_capture_then_release_fails`

2. **test_refund_module_7_2.py** (~8 tests)
   - `test_refund_creates_credit_transaction`
   - `test_refund_full_amount`
   - `test_refund_partial_amount`
   - `test_refund_amount_exceeds_original_raises`
   - `test_refund_non_purchase_transaction_raises`
   - `test_refund_idempotency_replay_returns_original`
   - `test_double_refund_with_different_key_succeeds` (partial refunds)
   - `test_refund_updates_wallet_balance`

3. **test_available_balance_module_7_2.py** (~6 tests)
   - `test_available_balance_no_holds`
   - `test_available_balance_single_hold`
   - `test_available_balance_multiple_holds`
   - `test_available_balance_after_capture` (hold removed from calculation)
   - `test_available_balance_after_release` (hold removed from calculation)
   - `test_available_balance_with_overdraft` (negative balance allowed)

4. **test_catalog_admin_module_7_2.py** (~5 tests)
   - `test_shop_item_creation`
   - `test_shop_item_sku_unique_constraint`
   - `test_shop_item_price_positive_constraint`
   - `test_shop_item_admin_registered`
   - `test_shop_item_active_filter`

5. **test_concurrency_module_7_2.py** (~4 tests)
   - `test_dual_capture_same_hold_one_wins`
   - `test_concurrent_authorize_different_keys`
   - `test_lock_ordering_prevents_deadlock` (capture hold A then B, reverse order in another thread)
   - `test_serialization_retry_succeeds` (mock transient error)

---

## Coverage Targets

| Component | Target | Notes |
|-----------|--------|-------|
| `apps/shop/services.py` | ≥90% | Core spend pipeline logic |
| State machine transitions | 100% | All authorized→captured/released/expired paths |
| Financial logic | 100% | Available balance, refund calculations |
| `apps/shop/models.py` | ≥85% | Model methods, constraints |
| `apps/shop/admin.py` | ≥75% | Admin registration, list view |
| `apps/shop/exceptions.py` | 100% | All custom exceptions raised |

**Coverage artifacts**: `Artifacts/coverage/module_7_2/index.html`

---

## Implementation Steps

### Step 1: Test Scaffolding (~2 hours)
- Create 5 test files in `tests/shop/`
- Scaffold ~43 tests, all marked `@pytest.mark.xfail` or `@pytest.mark.skip`
- Validate test discovery with `pytest --co tests/shop/`
- **Acceptance**: 43 tests collected, 0 run, 43 skipped/xfailed

### Step 2: Models & Migration (~1-2 hours)
- Create `apps/shop/models.py` with `ShopItem` and `ReservationHold`
- Create `apps/shop/admin.py` with `ShopItemAdmin`
- Generate migration: `python manage.py makemigrations shop`
- Apply migration: `python manage.py migrate shop`
- **Acceptance**: Migration applies cleanly, models importable, 5 catalog admin tests passing

### Step 3: Services (~3-4 hours)
- Create `apps/shop/services.py` with 4 spend pipeline functions + available balance helper
- Create `apps/shop/exceptions.py` with 3 custom exceptions
- Implement atomic transactions, row locks, stable ordering, idempotency
- Remove xfail markers from passing tests incrementally
- **Acceptance**: All 43 tests passing, 0 xfailed

### Step 4: Coverage & Hardening (~1-2 hours)
- Run `pytest tests/shop/ --cov=apps.shop --cov-report=html:Artifacts/coverage/module_7_2`
- Add property tests (2-3 fast tests) for invariants
- Add edge case coverage tests if gaps found
- Validate retry wrapper with mock transient errors
- **Acceptance**: All coverage targets met (≥90% services, 100% state machine)

### Step 5: Docs & Trace (~0.5 hours)
- Update `MODULE_7.2_COMPLETION_STATUS.md` with all steps, test results, coverage
- Update `Documents/ExecutionPlan/MAP.md` with Module 7.2 status
- Update `Documents/ExecutionPlan/trace.yml` with Module 7.2 completion event
- Run `python scripts/verify_trace.py`
- Single commit: "Module 7.2 – DeltaCoin Shop (Spend Flows) Complete"
- **Acceptance**: All docs updated, trace validated, commit ready (no push)

---

## Dependencies

### Module 7.1 (Complete)
- ✅ `DeltaCrownWallet` model
- ✅ `DeltaCrownTransaction` model
- ✅ `credit()`, `debit()` services
- ✅ `get_balance()` service
- ✅ Idempotency patterns (derived keys, cross-op collision)
- ✅ Exception hierarchy (`InvalidAmount`, `InsufficientFunds`, `InvalidWallet`, `IdempotencyConflict`)

### External Dependencies
- Django ORM (atomic transactions, SELECT FOR UPDATE)
- PostgreSQL (partial unique constraints, CHECK constraints)
- pytest, pytest-django (test framework)
- Hypothesis (property tests)

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Deadlock on concurrent operations** | Medium | Stable lock ordering (wallet by PK, then hold by PK), retry wrapper with exponential backoff + jitter |
| **Expired hold capture race** | Low | Lock hold row first, check expires_at before debit, terminal state transition |
| **Refund exceeds original** | Low | Validate amount ≤ original transaction, idempotency prevents double-refund |
| **Available balance computation overhead** | Low | Simple aggregate query, consider caching if performance issue (future optimization) |
| **State machine bugs** | Medium | 100% coverage on all transitions, integration tests for all paths, property tests for invariants |

---

## Success Criteria

- ✅ All 43 tests passing (100% pass rate on non-xfailed)
- ✅ Coverage targets met (≥90% services, 100% state machine, 100% financial logic)
- ✅ Zero regressions on Module 7.1 tests
- ✅ Migration applies cleanly and reversibly
- ✅ Idempotency hardened (derived keys, cross-op collision detection)
- ✅ PII discipline enforced (no PII in models, outputs, or logs)
- ✅ State machine validated (all transitions tested, invalid transitions raise exceptions)
- ✅ Documentation complete (kickoff, completion status, MAP, trace)

---

**Module 7.2 Status**: Step 1 - Test Scaffolding (In Progress)  
**Next Milestone**: 43 tests scaffolded, ready for Step 2 (Models & Migration)
