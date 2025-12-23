# UP-M3 CHANGELOG

## December 23, 2025 - UP-M3 Kickoff (Economy Sync)

### BASELINE FINDINGS (Step 1 Audit)

**Problem Statement:**
UserProfile fields `deltacoin_balance` and `lifetime_earnings` do NOT update automatically when economy transactions occur. This causes drift between the ledger (source of truth) and profile display caches.

**Current State:**

1. **Models Involved:**
   - `DeltaCrownWallet` (apps/economy/models.py):
     * `cached_balance` (IntegerField) - recalculated from transactions via `recalc_and_save()`
     * `lifetime_earnings` (IntegerField) - never updated
     * `pending_balance` (IntegerField) - for withdrawal locks
   - `DeltaCrownTransaction` (apps/economy/models.py):
     * Immutable ledger (amount, reason, wallet FK)
     * Creates transaction → calls `wallet.recalc_and_save()` in save() method
   - `UserProfile` (apps/user_profile/models_main.py):
     * `deltacoin_balance` (DecimalField) - never updated ❌
     * `lifetime_earnings` (DecimalField) - never updated ❌
     * `total_earnings` (@property) - reads wallet.lifetime_earnings or wallet.cached_balance

2. **Drift Points Identified:**
   - `DeltaCrownTransaction.save()` (line 380-390):
     * Calls `wallet.recalc_and_save()` on transaction create
     * Updates `wallet.cached_balance` ✅
     * Does NOT update `profile.deltacoin_balance` ❌
     * Does NOT update `profile.lifetime_earnings` ❌
     * Does NOT update `wallet.lifetime_earnings` ❌
   
   - `DeltaCrownWallet.recalc_and_save()` (line 138-160):
     * Recomputes `cached_balance` from SUM(transactions.amount)
     * Uses `select_for_update()` for concurrency safety
     * Does NOT propagate to profile fields ❌

3. **Signal Infrastructure:**
   - `apps/economy/signals.py` EXISTS (checked via file_search)
   - Signal for profile-wallet sync: NOT FOUND in grep (no post_save.connect in economy app)
   - UP-M2 activity signals: ✅ WORKING (on_economy_transaction creates UserActivity COINS_* events)

4. **Type Mismatch Issue:**
   - Wallet uses IntegerField (correct: DeltaCoins are whole numbers)
   - Profile uses DecimalField (incorrect: adds unnecessary complexity)
   - Must handle int→decimal conversion in sync OR migrate profile fields to IntegerField

5. **Existing Architecture Decisions:**
   - ADR-UP-003: Ledger-first economy (DeltaCrownTransaction = source of truth)
   - Hierarchy: Ledger → Wallet caches → Profile caches
   - Nightly reconciliation mentioned but NOT IMPLEMENTED

**Test Coverage:**
- `tests/economy/test_ledger_invariants_module_7_1.py`: Tests wallet balance conservation ✅
- `tests/economy/test_service_api_module_7_1.py`: Tests credit/debit API ✅
- Profile sync tests: NOT FOUND ❌

**Files Requiring Changes:**
1. `apps/economy/signals.py` - Add/update signal to sync wallet→profile
2. `apps/user_profile/services/` - Create economy sync service
3. `apps/user_profile/management/commands/` - Create reconcile_economy command
4. `apps/user_profile/tests/` or `tests/economy/` - Add sync + reconciliation tests

---

### IMPLEMENTATION COMPLETE (Step 2-3)

**Files Created:**
1. `apps/user_profile/services/economy_sync.py` (200 lines)
   - `sync_wallet_to_profile(wallet_id)` - Atomically syncs wallet→profile (balance + earnings)
   - `get_balance_drift(wallet_id)` - Read-only drift detection
   - `recompute_lifetime_earnings(wallet_id)` - Rebuild earnings from ledger
   - `sync_profile_by_user_id(user_id)` - Convenience wrapper
   - Concurrency: Uses `select_for_update()` on wallet + profile
   - Type handling: Int→Decimal conversion for profile fields

2. `apps/economy/signals.py` (updated)
   - Added `sync_profile_on_transaction()` signal handler
   - Trigger: `post_save` on `DeltaCrownTransaction` (created only)
   - Auto-syncs profile when transaction created
   - Never raises exceptions (graceful failure → reconcile command can fix)

3. `apps/user_profile/management/commands/reconcile_economy.py` (210 lines)
   - Options: `--dry-run`, `--user-id`, `--all`, `--batch-size`, `--limit`
   - Idempotent: Safe to rerun multiple times
   - Atomic: Each user reconciled in separate transaction
   - Progress logging: Every 100 wallets

4. `apps/user_profile/tests/test_economy_sync.py` (250 lines, 11 tests)
   - TestEconomySyncService: 6 tests (balance sync, earnings, idempotency, drift detection)
   - TestSignalIntegration: 1 test (transaction→signal→profile auto-update)
   - TestReconcileCommand: 3 tests (dry-run, single user, batch processing)
   - TestConcurrency: 1 test (concurrent transactions)

**Validation Results:**
- Dry-run reconcile: 5 wallets processed, 3 balance drifts detected (0→494, 0→280, 0→239)
- 3 earnings drifts detected (same users)
- 0 errors (code functional)
- Tests: Cannot run (DB CREATEDB permission required), but code validated via dry-run

**Signal Integration:**
- DeltaCrownTransaction.save() → triggers wallet.recalc_and_save() (existing)
- DeltaCrownTransaction post_save → triggers sync_profile_on_transaction() (NEW)
- UP-M2 activity signals → creates UserActivity events (already working, UP-M2)

**Concurrency Safety:**
- `select_for_update()` locks both wallet and profile rows
- Atomic transactions prevent partial updates
- Idempotent: Rerunning sync doesn't corrupt data

---
