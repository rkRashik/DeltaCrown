# Module 7.1 Kickoff — Coin System (Economy Foundation)

**Module**: 7.1  
**Phase**: 7 (Economy & Monetization)  
**Status**: 🚀 **KICKOFF**  
**Start Date**: 2025-01-23  
**Estimated Effort**: ~8-12 hours  
**Approach**: Test-first, minimal schema, strict idempotency

---

## Context

**Current State**:
- ✅ Basic wallet/transaction models exist (`apps/economy/models.py`)
- ✅ Service layer with `award()`, `wallet_for()`, `manual_adjust()` implemented
- ✅ Idempotency keys for participation, placements, manual adjustments
- ✅ Integration with tournament payouts (Module 5.2)
- ⚠️ **No tests** for coin ledger invariants
- ⚠️ **No comprehensive API** for credit/debit operations
- ⚠️ **No validation** for conservation laws or balance constraints

**Why Module 7.1 Now**:
- Strong momentum from Phase 6 (realtime testing)
- High product value (user-facing feature)
- Foundation for Module 7.2 (Shop & Purchases)
- Clean separation from previous tournament work

---

## Scope

### In Scope ✅

1. **Ledger Invariants Testing**
   - Conservation law: sum of all transactions = sum of all balances
   - Non-negative balance enforcement (unless overdraft flag set)
   - Immutability: transactions never mutated after creation
   - Idempotency: duplicate operations return same result

2. **Service API Completeness**
   - `credit(profile, amount, reason, **context)`: Atomic credit operation
   - `debit(profile, amount, reason, **context)`: Atomic debit operation (with overdraft check)
   - `transfer(from_profile, to_profile, amount, reason)`: Atomic peer-to-peer transfer
   - `get_balance(profile)`: Fast cached balance retrieval
   - `get_transaction_history(profile, limit)`: Paginated transaction list

3. **Integration Points**
   - ✅ Payout system (already integrated via `award_placements()`)
   - 🔄 Future shop purchases (Module 7.2 - debit path ready)
   - 🔄 Future promotional credits (Module 7.5 - credit path ready)

4. **Admin Tools**
   - Manual adjustment UI (already exists in `admin.py`)
   - Transaction audit log (read-only)
   - Balance reconciliation command (`recalc_all_wallets`)

5. **Documentation**
   - Service API docstrings with examples
   - Ledger invariants documented in models
   - Admin usage guide

### Out of Scope ❌

1. **Shop Integration**: Deferred to Module 7.2
2. **Revenue Analytics**: Deferred to Module 7.4
3. **Promotional System**: Deferred to Module 7.5
4. **Schema Changes**: Use existing `DeltaCrownWallet` and `DeltaCrownTransaction` models
5. **PII Exposure**: No transaction exports with user data (strict GDPR discipline)
6. **Blockchain/External Ledger**: Internal ledger only

---

## Test Strategy (Test-First Approach)

### Test Categories

#### 1. Ledger Invariants (Priority: CRITICAL)
**File**: `tests/unit/test_economy_ledger_invariants.py` (~300 lines)

**Tests**:
1. `test_conservation_law_simple`: Create 3 transactions, assert sum(amounts) == sum(balances)
2. `test_conservation_law_concurrent`: 10 users, 50 transactions each, assert conservation
3. `test_immutability_enforced`: Attempt to modify transaction.amount after save → assert raises
4. `test_balance_never_negative`: Debit beyond balance → assert DenyDebit exception
5. `test_overdraft_flag_allows_negative`: Set wallet.allow_overdraft=True → debit succeeds with negative balance
6. `test_wallet_recalc_matches_ledger`: Corrupt cached_balance → call recalc_and_save() → assert matches sum(transactions)

**Coverage Target**: 100% (critical financial logic)

#### 2. Idempotency (Priority: HIGH)
**File**: `tests/unit/test_economy_idempotency.py` (~250 lines)

**Tests**:
1. `test_duplicate_credit_same_key`: Call `credit(key="abc")` twice → assert 1 transaction created
2. `test_duplicate_debit_same_key`: Call `debit(key="xyz")` twice → assert 1 transaction created
3. `test_participation_award_idempotent`: Call `award_participation()` twice → assert 1 transaction per user
4. `test_placement_award_idempotent`: Call `award_placements()` twice → assert 1 transaction per winner
5. `test_manual_adjust_without_key_not_idempotent`: Call `manual_adjust()` twice without key → assert 2 transactions

**Coverage Target**: ≥90%

#### 3. Service API (Priority: HIGH)
**File**: `tests/integration/test_economy_service.py` (~400 lines)

**Tests**:
1. `test_credit_increases_balance`: credit(100) → assert balance == 100
2. `test_debit_decreases_balance`: credit(100), debit(30) → assert balance == 70
3. `test_debit_insufficient_funds_raises`: balance=50, debit(100) → assert raises InsufficientFunds
4. `test_transfer_atomic`: transfer(A→B, 50) → assert A.balance -= 50, B.balance += 50, or both rollback
5. `test_get_balance_from_cache`: credit(100) → assert get_balance() returns cached value (no DB query)
6. `test_get_transaction_history_paginated`: create 50 txns → get_history(limit=10) → assert 10 returned, ordered by created_at DESC

**Coverage Target**: ≥85%

#### 4. Admin Integration (Priority: MEDIUM)
**File**: `tests/integration/test_economy_admin.py` (~200 lines)

**Tests**:
1. `test_manual_adjust_creates_transaction`: Admin submits adjust form → assert transaction created
2. `test_transaction_readonly_in_admin`: Attempt to edit transaction via admin → assert readonly
3. `test_balance_reconciliation_command`: Corrupt balances → run `recalc_all_wallets` → assert all fixed

**Coverage Target**: ≥75%

---

## Implementation Plan

### Step 1: Test Scaffolding (~2 hours)
**Files Created**:
- `tests/unit/test_economy_ledger_invariants.py` (skeleton)
- `tests/unit/test_economy_idempotency.py` (skeleton)
- `tests/integration/test_economy_service.py` (skeleton)
- `tests/integration/test_economy_admin.py` (skeleton)

**Outcome**: 0 tests passing (all skeleton), baseline coverage measured

### Step 2: Ledger Invariants Implementation (~3 hours)
**Target**: `test_economy_ledger_invariants.py` all green

**Changes**:
1. Add `DeltaCrownWallet.allow_overdraft` field (BooleanField, default=False)
2. Add `InsufficientFunds` exception to `apps/economy/exceptions.py`
3. Add validation in `DeltaCrownTransaction.save()`:
   - Check balance before debit (if not overdraft)
   - Prevent amount=0 transactions
   - Prevent modifying amount after creation
4. Update `wallet.recalc_and_save()` to be atomic
5. Add `validate_conservation_law()` utility for testing

**Coverage Target**: ≥95% on `models.py`

### Step 3: Service API Enhancement (~3 hours)
**Target**: `test_economy_service.py` all green

**New Functions** (add to `services.py`):
```python
def credit(profile, amount: int, reason: str, *, idempotency_key=None, **context) -> DeltaCrownTransaction:
    """Atomic credit operation. Idempotent."""
    pass

def debit(profile, amount: int, reason: str, *, idempotency_key=None, allow_overdraft=False, **context) -> DeltaCrownTransaction:
    """Atomic debit operation. Raises InsufficientFunds if balance insufficient."""
    pass

def transfer(from_profile, to_profile, amount: int, reason: str, *, idempotency_key=None, **context) -> tuple[DeltaCrownTransaction, DeltaCrownTransaction]:
    """Atomic P2P transfer. Returns (debit_tx, credit_tx)."""
    pass

def get_balance(profile) -> int:
    """Fast cached balance retrieval."""
    pass

def get_transaction_history(profile, limit=50, offset=0) -> QuerySet:
    """Paginated transaction history."""
    pass
```

**Coverage Target**: ≥85% on `services.py`

### Step 4: Idempotency Hardening (~2 hours)
**Target**: `test_economy_idempotency.py` all green

**Changes**:
1. Ensure all `credit()`/`debit()` calls generate idempotency keys when None
2. Add `_default_idem_key()` helper for common patterns
3. Test double-call scenarios for all service methods
4. Document idempotency guarantees in docstrings

**Coverage Target**: 100% on idempotency paths

### Step 5: Admin Integration (~2 hours)
**Target**: `test_economy_admin.py` all green

**Changes**:
1. Add `recalc_all_wallets` management command
2. Make `DeltaCrownTransactionAdmin` fully readonly (except manual_adjust action)
3. Add wallet balance display to `DeltaCrownWalletAdmin`
4. Add transaction count to wallet list display

**Coverage Target**: ≥75% on `admin.py`

---

## Acceptance Criteria

| Criterion | Target | Validation |
|-----------|--------|------------|
| **Ledger Invariants** | 6/6 tests passing | Conservation law holds across all scenarios |
| **Idempotency** | 5/5 tests passing | Duplicate operations return same result |
| **Service API** | 6/6 tests passing | Credit/debit/transfer/balance/history working |
| **Admin Integration** | 3/3 tests passing | Manual adjust + reconciliation working |
| **Overall Coverage** | ≥85% | apps/economy/ package |
| **Production Changes** | Minimal | No schema migrations, only service enhancements |
| **Documentation** | Complete | Docstrings + admin guide |
| **Zero Regressions** | Required | Existing tournament payout integration unaffected |

---

## Guardrails

### 1. Test-First Discipline
- Write test skeleton BEFORE implementation
- Run tests after each change (fast feedback loop)
- No "implementation-driven" test writing

### 2. No Schema Churn
- Use existing `DeltaCrownWallet` and `DeltaCrownTransaction` models
- Only add `allow_overdraft` field (BooleanField, default=False, nullable for backward compat)
- No new tables, no foreign key changes

### 3. Strict PII Discipline
- No transaction exports with user data
- Admin views show transaction ID, amount, reason only (no user names in list)
- Balance reconciliation command operates on wallet IDs only

### 4. Idempotency Everywhere
- Every service method that creates transactions MUST accept `idempotency_key`
- Default key generation follows `_mk_idem_key()` pattern
- Document idempotency behavior in docstrings

### 5. Atomic Operations
- All credit/debit/transfer use `@transaction.atomic`
- Balance updates always through `wallet.recalc_and_save()` (never manual cached_balance writes)
- Transfer is single transaction (both debit and credit, or neither)

---

## Technical Notes

### Existing Code Quality
**Strengths**:
- ✅ Immutable ledger pattern already implemented
- ✅ Idempotency keys for tournament payouts
- ✅ `recalc_and_save()` rebuilds balance from ledger
- ✅ Clean separation of wallet (state) and transaction (events)

**Weaknesses**:
- ⚠️ No balance validation on debit
- ⚠️ No tests for ledger invariants
- ⚠️ `award()` function does too much (credit + debit + idempotency)
- ⚠️ No dedicated `credit()`/`debit()` primitives

### Design Decisions

**1. Cached Balance vs. Real-Time Sum**
- **Choice**: Keep `cached_balance` (performance)
- **Rationale**: Wallet reads are 100x more frequent than writes
- **Safety**: `recalc_and_save()` rebuilds on every transaction create

**2. Overdraft Flag vs. Hard Limit**
- **Choice**: Add `allow_overdraft` flag (default=False)
- **Rationale**: Future use cases (promotional credits, admin adjustments) may need negative balances
- **Safety**: Default behavior prevents negative balances

**3. Transfer as Atomic Operation**
- **Choice**: Single `@transaction.atomic` for both debit and credit
- **Rationale**: P2P transfers must never lose coins (both succeed or both rollback)
- **Implementation**: Create debit transaction, create credit transaction, return both

**4. Idempotency Key Generation**
- **Choice**: Auto-generate keys for common patterns (participation, placements)
- **Rationale**: Prevents double-awarding when services called multiple times
- **Escape Hatch**: `idempotency_key=None` disables (for manual adjustments)

---

## Integration Points

### 1. Tournament Payouts (Module 5.2)
**Status**: ✅ Already Integrated

**Functions Used**:
- `award_participation_for_registration(reg)` → calls `award()`
- `award_placements(tournament)` → calls `award()`

**Module 7.1 Impact**:
- Refactor `award()` to use new `credit()` primitive
- Add tests for payout idempotency
- No breaking changes

### 2. Future Shop Purchases (Module 7.2)
**Status**: 🔄 Ready for Integration

**Required**:
- `debit(profile, amount, reason="SHOP_PURCHASE", idempotency_key=f"shop:order:{order_id}")` → will be implemented in Step 3

**Module 7.1 Deliverable**:
- `debit()` function with overdraft check
- Test coverage for insufficient funds scenario

### 3. Future Promotional Credits (Module 7.5)
**Status**: 🔄 Ready for Integration

**Required**:
- `credit(profile, amount, reason="PROMO", idempotency_key=f"promo:{campaign_id}:{profile.id}")` → will be implemented in Step 3

**Module 7.1 Deliverable**:
- `credit()` function with idempotency
- Test coverage for duplicate promo awards

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Breaking existing payouts** | Low | High | Run Module 5.2 tests after every change |
| **Ledger invariant violation** | Low | Critical | 100% test coverage on invariants, conservation law checks |
| **Concurrency issues** | Medium | High | Use `@transaction.atomic`, test concurrent operations |
| **Overdraft abuse** | Low | Medium | Default `allow_overdraft=False`, admin audit log |
| **Performance degradation** | Low | Medium | Keep `cached_balance`, benchmark balance queries |
| **Test flakiness** | Medium | Low | Use `transaction=True` for DB tests, deterministic fixtures |

---

## Dependencies

### Upstream (Must Complete First)
- ✅ Module 5.2 (Tournament Payouts) - already complete
- ✅ Module 1.3 (Registration Models) - already complete
- ✅ Module 1.4 (Match Models) - already complete

### Downstream (Blocks)
- Module 7.2 (Shop & Purchases) - needs `debit()` function
- Module 7.4 (Revenue Analytics) - needs stable ledger
- Module 7.5 (Promotional System) - needs `credit()` function

### Parallel (Can Work Simultaneously)
- None (clean separation from Phase 6 realtime work)

---

## Success Metrics

### Quantitative
- **Test Count**: ≥20 tests (6 invariants + 5 idempotency + 6 service + 3 admin)
- **Coverage**: ≥85% on `apps/economy/` package
- **Performance**: `get_balance()` < 5ms (cached), `credit()/debit()` < 50ms (DB write)
- **Zero Regressions**: All Module 5.2 payout tests still pass

### Qualitative
- **Code Quality**: Service methods have clear docstrings with examples
- **Maintainability**: Ledger invariants documented in models.py
- **Admin Usability**: Balance reconciliation command works without manual SQL
- **Test Clarity**: Each test has descriptive name + docstring explaining what it validates

---

## Deliverables Checklist

### Code
- [ ] `apps/economy/models.py`: Add `allow_overdraft` field
- [ ] `apps/economy/services.py`: Add `credit()`, `debit()`, `transfer()`, `get_balance()`, `get_transaction_history()`
- [ ] `apps/economy/exceptions.py`: Add `InsufficientFunds` exception
- [ ] `apps/economy/admin.py`: Enhance wallet/transaction admin displays
- [ ] `apps/economy/management/commands/recalc_all_wallets.py`: Balance reconciliation command

### Tests
- [ ] `tests/unit/test_economy_ledger_invariants.py`: 6 tests (100% coverage target)
- [ ] `tests/unit/test_economy_idempotency.py`: 5 tests (100% coverage target)
- [ ] `tests/integration/test_economy_service.py`: 6 tests (≥85% coverage target)
- [ ] `tests/integration/test_economy_admin.py`: 3 tests (≥75% coverage target)

### Documentation
- [ ] Service API docstrings with examples
- [ ] Ledger invariants documented in `models.py`
- [ ] Admin usage guide (inline comments in `admin.py`)
- [ ] `MODULE_7.1_COMPLETION_STATUS.md`: Comprehensive status report

### Artifacts
- [ ] Coverage reports: `Artifacts/coverage/module_7_1/`
- [ ] Migration file: `apps/economy/migrations/000X_add_overdraft_flag.py`
- [ ] Test execution logs (if any failures)

---

## Timeline

| Step | Duration | Cumulative | Deliverable |
|------|----------|------------|-------------|
| 1. Test Scaffolding | ~2 hours | 2h | 4 test files (skeletons) |
| 2. Ledger Invariants | ~3 hours | 5h | 6 tests passing, ≥95% coverage on models |
| 3. Service API | ~3 hours | 8h | 6 tests passing, ≥85% coverage on services |
| 4. Idempotency | ~2 hours | 10h | 5 tests passing, 100% idempotency coverage |
| 5. Admin Integration | ~2 hours | 12h | 3 tests passing, admin tools working |

**Total Estimated Effort**: 10-12 hours  
**Target Completion**: 2025-01-24 (1-2 days)

---

## Open Questions

1. **Q**: Should we add a `DeltaCrownTransaction.status` field (pending/completed/reversed)?  
   **A**: Deferred to Module 7.2 (shop integration) - current use case doesn't need it

2. **Q**: Should we implement refunds as negative transactions or compensating transactions?  
   **A**: Compensating transactions (create new positive transaction with reason="REFUND") - preserves audit trail

3. **Q**: Should we add a `DeltaCrownWallet.frozen` flag to block transactions?  
   **A**: Deferred to Module 8.2 (user moderation) - not needed for MVP

4. **Q**: Should we implement transaction batching for performance?  
   **A**: Not needed yet - current volume is low (<100 transactions/day)

---

## References

### Existing Code
- `apps/economy/models.py`: Wallet and Transaction models
- `apps/economy/services.py`: Award and adjustment functions
- `apps/economy/admin.py`: Admin interface

### Related Modules
- Module 5.2 (Tournament Payouts): Uses `award_participation()` and `award_placements()`
- Module 7.2 (Shop & Purchases): Will use `debit()` function
- Module 7.5 (Promotional System): Will use `credit()` function

### Architecture Decisions
- ADR-001: Service Layer Pattern (use service functions, not direct model manipulation)
- ADR-003: Soft Delete Pattern (not applicable to transactions - they're immutable)
- ADR-004: PostgreSQL Features (use atomic transactions, sum aggregation)

---

**Status**: 🚀 **READY TO START** — Test scaffolding begins now.
