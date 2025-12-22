# UP-04: Profile Economy Sync & Reconciliation

**Status:** Target Architecture  
**Owner:** Economy + UserProfile Apps  
**Last Updated:** 2025-12-22

---

## 1. Problem Statement

**Current State:**
- UserProfile has `deltacoin_balance` and `lifetime_earnings` fields
- DeltaCrownWallet has `cached_balance` and `lifetime_earnings` fields
- Economy app has transaction ledger (source of truth)
- **Profile fields NEVER update** - audit found 0% sync rate
- Wallet balance drifts from ledger over time
- No reconciliation exists - data diverges permanently

**Why This Happens:**
- No signal handlers link economy transactions to profile updates
- Profile updates happen manually (never)
- Wallet updates happen on transaction creation but can drift on failures
- No periodic recomputation from ledger
- Cached aggregates treated as authoritative (wrong)

**Impact:**
- Profile displays stale balance (user confusion)
- Leaderboards show incorrect wealth rankings
- Admin reports pull wrong data
- Audit trails incomplete
- No way to detect/fix drift

---

## 2. Source of Truth Declaration

**Ledger is Truth:**
- `EconomyTransaction` table = immutable source of truth
- Every DC movement MUST create a transaction record
- Balances/earnings = derived aggregates computed from ledger
- Never update aggregates without corresponding transaction

**Derived Caches (Two Layers):**

| Cache Location | Fields | Update Trigger | Purpose |
|----------------|--------|----------------|---------|
| DeltaCrownWallet | cached_balance, lifetime_earnings | Real-time (signals) | API queries, fast reads |
| UserProfile | deltacoin_balance, lifetime_earnings | Near real-time (signals) | Profile display, leaderboards |

**Hierarchy:**
- Ledger (EconomyTransaction) → Wallet caches → Profile caches
- Profile NEVER updates economy data directly
- Wallet updates only via transaction creation
- Nightly reconciliation recomputes all caches from ledger

---

## 3. Required Invariants

**MUST be true at all times:**

1. **Balance Integrity:**
   - `profile.deltacoin_balance == wallet.cached_balance`
   - Both must equal `SUM(transactions.amount WHERE status=COMPLETED)`

2. **Earnings Integrity:**
   - `profile.lifetime_earnings == wallet.lifetime_earnings`
   - Both must equal `SUM(transactions.amount WHERE type IN (PRIZE, AWARD, REFUND) AND status=COMPLETED)`

3. **Non-Negativity:**
   - Balance can never go below 0
   - Spending transactions must check available balance atomically

4. **Transaction Completeness:**
   - Every balance change MUST have corresponding transaction
   - No orphaned transactions (every tx links to wallet → profile)

5. **Monotonic Earnings:**
   - `lifetime_earnings` only increases (never decreases)
   - Even refunds/reversals don't reduce lifetime total

**Violation Handling:**
- Mismatches logged to `EconomyReconciliationLog`
- Auto-repair if drift < 5%
- Manual review alert if drift ≥ 5%
- Critical alert if balance goes negative

---

## 4. Update Flow (By Transaction Type)

### Deposit / Award / Prize
**Trigger:** User receives DC (tournament prize, admin award, referral bonus)

**Flow:**
1. Tournament/Admin service calls `economy.services.award_deltacoins(user, amount, reason)`
2. Service creates `EconomyTransaction` (type=AWARD, status=PENDING)
3. Transaction atomically updates `wallet.cached_balance += amount`
4. Transaction sets status=COMPLETED
5. Signal `transaction_completed` fires
6. Signal handler updates `profile.deltacoin_balance += amount`
7. Signal handler updates `profile.lifetime_earnings += amount`

**Atomicity:** Entire flow in single database transaction

---

### Spend / Purchase / Fee
**Trigger:** User spends DC (registration fee, shop purchase)

**Flow:**
1. Registration/Shop service calls `economy.services.charge_deltacoins(user, amount, reason)`
2. Service checks `wallet.cached_balance >= amount` (with SELECT FOR UPDATE)
3. If insufficient balance → raise InsufficientFundsError (rollback)
4. Creates `EconomyTransaction` (type=PURCHASE, status=PENDING)
5. Transaction atomically updates `wallet.cached_balance -= amount`
6. Transaction sets status=COMPLETED
7. Signal `transaction_completed` fires
8. Signal handler updates `profile.deltacoin_balance -= amount`
9. Lifetime earnings UNCHANGED (spending doesn't reduce earnings)

**Atomicity:** SELECT FOR UPDATE prevents race conditions

---

### Refund / Reversal
**Trigger:** Tournament cancelled, registration refunded, purchase returned

**Flow:**
1. Service calls `economy.services.refund_transaction(original_tx_id)`
2. Service creates `EconomyTransaction` (type=REFUND, references original tx)
3. Transaction atomically updates `wallet.cached_balance += refund_amount`
4. Transaction sets status=COMPLETED
5. Signal handler updates `profile.deltacoin_balance += refund_amount`
6. Signal handler updates `profile.lifetime_earnings += refund_amount` (refunds count as earnings)

**Edge Cases:**
- Partial refunds: create new transaction for refunded portion
- Double refunds: check original tx not already refunded
- Expired refunds: time limits enforced at service layer

---

## 5. Reconciliation Strategy

### Nightly Reconciliation Command

**Schedule:** 3:00 AM UTC daily (low traffic window)

**Process:**
1. For each active wallet:
   - Compute `actual_balance = SUM(transactions WHERE status=COMPLETED)`
   - Compute `actual_earnings = SUM(transactions WHERE type IN earnings_types)`
   - Compare to `wallet.cached_balance` and `profile.deltacoin_balance`

2. Mismatch Detection:
   - If wallet balance ≠ ledger balance → DRIFT detected
   - If profile balance ≠ wallet balance → SYNC FAILURE detected
   - If earnings ≠ ledger earnings → EARNINGS DRIFT detected

3. Repair Logic:
   - **Drift < 1 DC:** Auto-repair (update cache to match ledger), log as INFO
   - **Drift 1-100 DC:** Auto-repair, log as WARNING, Slack notification
   - **Drift > 100 DC:** DO NOT auto-repair, log as ERROR, page on-call
   - **Negative balance:** CRITICAL alert, freeze wallet, manual intervention

4. Reconciliation Log:
   - Every mismatch creates `EconomyReconciliationLog` entry
   - Fields: wallet_id, profile_id, expected_balance, actual_balance, drift_amount, action_taken, timestamp
   - Retention: 90 days
   - Dashboard displays drift trends

**Command:**
```
python manage.py reconcile_economy_caches --repair-threshold=100
```

---

### Manual Reconciliation

**When to Use:**
- User reports wrong balance
- After data migration
- After manual database fixes
- Before major releases

**Single User:**
```
python manage.py reconcile_economy_caches --user-id=42
```

**Dry Run (No Repairs):**
```
python manage.py reconcile_economy_caches --dry-run
```

---

## 6. Integration Points with UserProfile

**Cached Fields (Read-Only from Profile Perspective):**

1. **deltacoin_balance** (DecimalField)
   - Updated by: Economy signals only
   - Used by: Profile display, leaderboards, eligibility checks
   - Never update directly: Always use economy.services methods

2. **lifetime_earnings** (DecimalField)
   - Updated by: Economy signals only
   - Used by: Profile stats, achievement triggers, rankings
   - Never update directly: Always use economy.services methods

**Access Patterns:**

- **Profile View:** Read `profile.deltacoin_balance` (fast cached read)
- **Transaction History:** Query `EconomyTransaction.objects.filter(wallet__profile=profile)` (join to wallet)
- **Earnings Breakdown:** Query ledger with aggregations by transaction type
- **Balance Check Before Purchase:** Use `economy.services.can_afford(user, amount)` (checks wallet with lock)

**Signal Handlers (apps/user_profile/signals.py):**

- `@receiver(transaction_completed, sender=EconomyTransaction)`
  - Updates `profile.deltacoin_balance`
  - Updates `profile.lifetime_earnings` (if earning type)
  - Triggers XP gain if milestone reached
  - Logs profile cache update

**Anti-Patterns (Never Do This):**
- ❌ `profile.deltacoin_balance += 100; profile.save()`
- ❌ Direct SQL updates to balance fields
- ❌ Reading balance then spending without lock
- ❌ Updating profile without creating transaction

---

## 7. Acceptance Criteria

### Unit Tests
- [ ] Transaction creation updates wallet cache atomically
- [ ] Signal handler updates profile balance on transaction completion
- [ ] Insufficient balance raises error before transaction creation
- [ ] Refund transactions increase both balance and lifetime earnings
- [ ] Negative balance prevented by constraints and service logic
- [ ] Reconciliation command detects 1 DC drift
- [ ] Reconciliation command auto-repairs small drifts
- [ ] Reconciliation command alerts on large drifts

### Integration Tests
- [ ] Award 100 DC → profile shows +100, wallet shows +100, ledger shows +100
- [ ] Spend 50 DC → profile shows -50, wallet shows -50, lifetime earnings unchanged
- [ ] Refund 50 DC → profile shows +50, wallet shows +50, lifetime earnings +50
- [ ] Concurrent purchases with same user don't create negative balance (race condition)
- [ ] Nightly reconciliation repairs drift introduced by failed signal

### Manual Checks
- [ ] Profile balance matches wallet balance for all active users
- [ ] Leaderboard "Top Earners" pulls correct lifetime_earnings
- [ ] Economy reconciliation dashboard shows <1% drift rate
- [ ] Admin panel displays transaction history correctly
- [ ] User receives Slack notification on large drift detection

### Performance Checks
- [ ] Reconciliation command completes in <5 minutes for 10K users
- [ ] Signal overhead <10ms per transaction
- [ ] Balance check query with lock <50ms

---

## Implementation Notes

**Phase:** UP-3 (Economy Sync) in execution plan

**Dependencies:**
- UP-1 (Invariant enforcement) → profile creation guaranteed
- Economy app transaction ledger → must be stable
- Signal infrastructure → must handle failures gracefully

**Risk Mitigation:**
- Reconciliation runs in low-traffic window (3 AM)
- Large drifts require manual review (prevent bad auto-repairs)
- Wallet frozen on negative balance (prevent fraud)
- All repairs logged (audit trail)

**Monitoring:**
- Daily reconciliation report (Slack)
- Drift rate metric (Grafana)
- Negative balance alert (PagerDuty)
- Signal failure rate (Sentry)

---

**End of Document**
