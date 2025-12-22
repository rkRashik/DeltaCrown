# USER PROFILE ECONOMY & STATS ARCHITECTURE

**Platform:** DeltaCrown Esports Tournament Platform  
**Scope:** Economy Integration & Tournament Statistics  
**Date:** December 22, 2025  
**Status:** APPROVED FOR IMPLEMENTATION

---

## DOCUMENT PURPOSE

This document extends the main User Profile Target Architecture with detailed specifications for:
1. Economy system integration (wallet, transactions, balance sync)
2. Tournament participation tracking (participation records, match history)
3. User stats snapshot strategy (cached aggregates, performance metrics)

**Related Documents:**
- [User Profile Target Architecture](USER_PROFILE_TARGET_ARCHITECTURE.md) - Core identity and privacy
- [User Profile Audit Part 2](../../Audit/UserProfile/USER_PROFILE_AUDIT_PART_2_ECONOMY_AND_STATS.md) - Problem analysis

---

## 1. ECONOMY ARCHITECTURE

### 1.1 Core Principles

#### Principle 1: Ledger is Source of Truth

**The DeltaCrownTransaction table is the ONLY source of truth for balance.**

```
User's Real Balance = SUM(transactions.amount WHERE wallet_id = user.wallet.id)
```

**Why This Matters:**
- ✅ Auditable: Every balance change has a record
- ✅ Immutable: Transactions cannot be edited (only compensating entries)
- ✅ Provable: Can reconstruct balance at any point in time
- ✅ Compliant: Financial regulations require transaction logs

**What This Means:**
- ❌ NEVER store balance as the only record
- ❌ NEVER update balance without creating transaction
- ❌ NEVER delete transactions (even for corrections)
- ✅ ALWAYS create new transaction for adjustments

---

#### Principle 2: Aggregates are Performance Cache

**Cached values exist ONLY for performance, not as source of truth.**

| Aggregate Field | Source of Truth | Purpose |
|-----------------|-----------------|---------|
| `wallet.cached_balance` | SUM(transactions.amount) | Fast balance checks without JOIN |
| `profile.lifetime_earnings` | SUM(transactions.amount WHERE amount > 0) | Show total prizes won |
| `profile.total_spent` | SUM(transactions.amount WHERE amount < 0 AND reason=PURCHASE) | Analytics |
| `profile.transaction_count` | COUNT(transactions) | Display "42 transactions" |
| `profile.last_transaction_at` | MAX(transactions.created_at) | Activity tracking |

**Cache Invalidation:**
- Updated immediately when transaction created (via signal)
- Reconciled nightly via background job (detect drift)
- Rebuildable from ledger (if cache corrupted)

---

### 1.2 Current Sync Problem Analysis

#### Why Sync Breaks

**Problem 1: UserProfile has duplicate balance field**

```
UserProfile.deltacoin_balance (DecimalField, default=0)
  ↓
DeltaCrownWallet.cached_balance (IntegerField)
  ↓
SUM(DeltaCrownTransaction.amount)  ← ACTUAL SOURCE
```

**What Happens:**
1. Transaction created → Wallet.cached_balance updated ✅
2. Profile.deltacoin_balance NOT updated ❌
3. Template checks Profile.deltacoin_balance → Shows 0 ❌
4. User thinks they have no coins ❌

**Root Cause:** No signal connecting wallet updates to profile field.

---

**Problem 2: Type Mismatch**

```
Wallet.cached_balance = IntegerField (coins as integer)
Profile.deltacoin_balance = DecimalField (coins as decimal??)
```

**Why Decimal is Wrong:**
- DeltaCoins have no fractional units (can't have 0.5 coins)
- DecimalField adds unnecessary complexity
- Creates conversion issues (int → decimal → int)

**Correct Type:** IntegerField everywhere (coins are whole numbers)

---

**Problem 3: Lifetime Earnings Never Updated**

```python
# Tournament awards prize
DeltaCrownTransaction.objects.create(
    wallet=winner_wallet,
    amount=1000,
    reason=DeltaCrownTransaction.Reason.WINNER
)
# Wallet recalculates cached_balance ✅
# Profile.lifetime_earnings stays 0 ❌
```

**Root Cause:** No signal to sum positive transactions into profile field.

---

### 1.3 Correct Economy Integration Flow

#### Flow 1: Transaction Creation

```
User Action (e.g., wins tournament)
  ↓
Service Layer: economy.services.credit_wallet()
  ↓
Create DeltaCrownTransaction:
  - wallet = user.wallet
  - amount = +1000
  - reason = WINNER
  - tournament_id = 123
  - idempotency_key = "tournament-123-winner-user-456"
  ↓
Signal: post_save(DeltaCrownTransaction)
  ↓
1. Update Wallet.cached_balance
   locked_wallet = DeltaCrownWallet.objects.select_for_update().get(pk=wallet.pk)
   locked_wallet.cached_balance = SUM(transactions.amount)
   locked_wallet.save()
  ↓
2. Update Profile Aggregates (NEW)
   profile = wallet.profile
   
   # Sync current balance
   profile.deltacoin_balance = locked_wallet.cached_balance
   
   # Update lifetime earnings (only for credits)
   if transaction.amount > 0:
       profile.lifetime_earnings += transaction.amount
   
   # Update counters
   profile.transaction_count += 1
   profile.last_transaction_at = transaction.created_at
   
   profile.save(update_fields=[
       'deltacoin_balance',
       'lifetime_earnings',
       'transaction_count',
       'last_transaction_at',
       'updated_at'
   ])
```

**Key Improvements:**
1. ✅ Atomic: Wallet and profile updated in same transaction
2. ✅ Selective: Only updates changed fields (performance)
3. ✅ Auditable: Transaction log has full context
4. ✅ Idempotent: Duplicate transactions prevented by idempotency_key

---

#### Flow 2: Balance Reconciliation (Nightly)

**Purpose:** Detect and fix drift between wallet and profile

```
Management Command: reconcile_balances.py (runs nightly)
  ↓
FOR EACH wallet:
  1. Calculate true balance from ledger:
     true_balance = wallet.transactions.aggregate(Sum('amount'))['amount__sum']
  
  2. Check wallet cache:
     if wallet.cached_balance != true_balance:
         LOG ERROR: "Wallet {wallet.id} drift detected"
         wallet.cached_balance = true_balance
         wallet.save()
  
  3. Check profile cache:
     if wallet.profile.deltacoin_balance != true_balance:
         LOG ERROR: "Profile {profile.id} balance drift detected"
         wallet.profile.deltacoin_balance = true_balance
         wallet.profile.save()
  
  4. Recalculate lifetime earnings:
     true_earnings = wallet.transactions.filter(amount__gt=0).aggregate(Sum('amount'))
     if wallet.profile.lifetime_earnings != true_earnings:
         LOG ERROR: "Profile {profile.id} earnings drift detected"
         wallet.profile.lifetime_earnings = true_earnings
         wallet.profile.save()
```

**Drift Causes:**
- Signal failure (exception during update)
- Race condition (concurrent transactions)
- Manual database edit (admin correction)
- Bug in signal logic

**Handling Drift:**
- Log all discrepancies (for investigation)
- Auto-correct (use ledger as truth)
- Alert if drift > 1% of users (systemic issue)

---

### 1.4 Economy Model Specifications

#### DeltaCrownWallet (Unchanged)

**Responsibilities:**
- Store cached balance (performance optimization)
- Store payment methods (bKash, Nagad, bank)
- Store PIN hash (withdrawal security)

**Key Fields:**
```
- profile (OneToOne → UserProfile)
- cached_balance (IntegerField, default=0)
- lifetime_earnings (IntegerField, default=0)  ← NEW FIELD
- pending_balance (IntegerField, default=0)  ← For locked withdrawals
- created_at, updated_at
```

**Methods:**
```python
@property
def available_balance():
    """Balance available for spending (excludes pending withdrawals)"""
    return cached_balance - pending_balance

@transaction.atomic
def recalc_and_save():
    """Recalculate cached_balance from ledger with row lock"""
    locked_wallet = DeltaCrownWallet.objects.select_for_update().get(pk=self.pk)
    total = locked_wallet.transactions.aggregate(Sum('amount'))['amount__sum'] or 0
    locked_wallet.cached_balance = int(total)
    locked_wallet.save(update_fields=['cached_balance', 'updated_at'])
    return total
```

---

#### DeltaCrownTransaction (Unchanged)

**Responsibilities:**
- Immutable ledger of ALL balance changes
- Audit trail for compliance
- Source of truth for balance

**Key Fields:**
```
- wallet (ForeignKey → DeltaCrownWallet)
- amount (IntegerField, CHECK amount != 0)
- reason (CharField, choices=[WINNER, PARTICIPATION, PURCHASE, REFUND, ...])
- tournament_id (IntegerField, nullable)
- registration_id (IntegerField, nullable)
- idempotency_key (CharField, unique, nullable)
- metadata (JSONField, default=dict)
- created_at (auto_now_add)
```

**Constraints:**
```sql
CHECK (amount != 0)  -- No zero-value transactions
UNIQUE (idempotency_key)  -- Prevent duplicates
INDEX (wallet_id, created_at)  -- Fast user transaction history
INDEX (reason, created_at)  -- Analytics queries
```

---

#### UserProfile Economy Fields (Updated)

**Remove:**
- ❌ `deltacoin_balance` (use property instead)
- ❌ `lifetime_earnings` (moved to wallet or profile stats)

**Add:**
```python
# Option A: Remove balance field, use property
@property
def deltacoin_balance(self):
    """Current balance (read from wallet)"""
    if hasattr(self, 'dc_wallet'):
        return self.dc_wallet.cached_balance
    return 0

# Option B: Keep field but mark as cache (RECOMMENDED)
deltacoin_balance = models.IntegerField(
    default=0,
    editable=False,
    help_text="Cached balance (synced from wallet via signal)"
)

# Stats fields (cached aggregates)
lifetime_earnings = models.IntegerField(
    default=0,
    editable=False,
    help_text="Total DeltaCoins earned (all time)"
)
total_spent = models.IntegerField(
    default=0,
    editable=False,
    help_text="Total DeltaCoins spent (all time)"
)
transaction_count = models.IntegerField(
    default=0,
    editable=False,
    help_text="Total number of transactions"
)
last_transaction_at = models.DateTimeField(
    null=True,
    blank=True,
    editable=False,
    help_text="Last transaction timestamp"
)
```

**Rationale for Option B (Keep Cached Field):**
- ✅ Fast profile queries (no JOIN to wallet)
- ✅ Enables ORDER BY balance (leaderboards)
- ✅ Reduces database load (no wallet lookup per profile)
- ⚠️ Requires sync discipline (signal must work)
- ⚠️ Requires reconciliation (nightly job)

---

### 1.5 Transaction History Access

**Current Problem:** Users cannot see their transaction history.

**Solution: Add Transaction History to Profile View**

**URL Pattern:**
```
/u/{public_id}/transactions/
/u/DC-25-000042/transactions/
```

**View Logic:**
```python
def transaction_history(request, public_id):
    profile = get_object_or_404(UserProfile, public_id=public_id)
    
    # Privacy check
    if profile.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Cannot view transaction history")
    
    # Get wallet
    wallet = profile.dc_wallet
    
    # Paginate transactions
    transactions = wallet.transactions.order_by('-created_at')
    paginator = Paginator(transactions, 25)
    page = paginator.get_page(request.GET.get('page'))
    
    # Add running balance
    for tx in page:
        # Calculate balance after this transaction
        tx.balance_after = wallet.transactions.filter(
            created_at__lte=tx.created_at
        ).aggregate(Sum('amount'))['amount__sum']
    
    return render(request, 'user_profile/transactions.html', {
        'profile': profile,
        'transactions': page,
    })
```

**Template Display:**
```
Date          | Description              | Amount    | Balance After
--------------------------------------------------------------------------
Dec 20, 2025  | Tournament Winner        | +1,000 DC | 1,500 DC
Dec 19, 2025  | Entry Fee                | -50 DC    | 500 DC
Dec 18, 2025  | Participation Reward     | +25 DC    | 550 DC
Dec 17, 2025  | Prize (Runner-up)        | +500 DC   | 525 DC
Dec 15, 2025  | Registration Fee         | -25 DC    | 25 DC
Dec 10, 2025  | Welcome Bonus            | +50 DC    | 50 DC
```

**Privacy Considerations:**
- Transaction history is HIGHLY SENSITIVE (financial data)
- Only owner and staff can view
- No public API endpoint (even with privacy toggle)
- Consider adding export feature (CSV download)

---

## 2. TOURNAMENT PARTICIPATION MODEL

### 2.1 The Missing Link Problem

**Current State:**
- ✅ Registration exists (user signs up for tournament)
- ✅ TournamentResult exists (winner recorded)
- ❌ NO record linking user → tournament → outcome for ALL participants

**Consequences:**
- Cannot answer "How many tournaments did user play?"
- Cannot show "User finished 4th in 12 tournaments"
- Cannot calculate win rate
- Cannot build user tournament history page
- Cannot generate achievements ("Played 50 tournaments")

---

### 2.2 TournamentParticipation Model

**Purpose:** Record that user ACTUALLY PARTICIPATED in a tournament (after completion)

**Schema:**

```
Table: tournament_participation
----------------------------------------
id (PK)
user_id (FK → User, indexed)
tournament_id (FK → Tournament, indexed)
registration_id (FK → Registration, nullable)

# Placement
placement (Integer, 1=first, 2=second, etc.)
placement_tier (VARCHAR: winner/runner_up/top4/top8/top16/participant)

# Performance Stats
matches_played (Integer, default=0)
matches_won (Integer, default=0)
kills (Integer, default=0)  # For BR games
deaths (Integer, default=0)  # For death-tracked games

# Rewards
prize_amount (Integer, default=0)  # DeltaCoins won
xp_earned (Integer, default=0)
badges_earned (JSONField, default=[])  # Badge IDs

# Metadata
created_at (timestamp)
recorded_by (FK → User, nullable)  # Staff who recorded result

UNIQUE (user_id, tournament_id)  -- One participation per tournament
INDEX (user_id, created_at DESC)  -- Fast user history
INDEX (tournament_id, placement)  -- Fast tournament standings
INDEX (user_id, placement_tier)   -- Fast achievement queries
```

**Placement Tiers Rationale:**

| Tier | Placement Range | Purpose |
|------|-----------------|---------|
| `winner` | 1 | Achievements: "Win 10 tournaments" |
| `runner_up` | 2 | Achievements: "50 runner-up finishes" |
| `top4` | 3-4 | Achievements: "100 top-4 finishes" |
| `top8` | 5-8 | Display: "Frequently places top-8" |
| `top16` | 9-16 | Large tournaments (64+ participants) |
| `participant` | 17+ or unknown | Completed but didn't place |

**Why Tiers Matter:**
- Enables fast achievement queries: `WHERE placement_tier IN ('winner', 'runner_up')`
- Better than complex range queries: `WHERE placement BETWEEN 1 AND 4`
- Supports different tournament sizes (4-player vs 64-player)

---

### 2.3 When Participation Records Are Created

**Trigger:** Tournament status changes to `COMPLETED`

**Signal:**
```python
@receiver(post_save, sender=Tournament)
def create_participation_records(sender, instance, **kwargs):
    """
    When tournament completes, create participation records for all
    checked-in participants.
    """
    if instance.status != 'completed':
        return
    
    # Skip if already processed
    if instance.participations.exists():
        return
    
    # Get all registrations that checked in
    registrations = instance.registrations.filter(
        status='confirmed',
        checked_in=True
    ).exclude(status='no_show')
    
    # Get tournament result (if exists)
    try:
        result = instance.result
    except TournamentResult.DoesNotExist:
        logger.warning(f"Tournament {instance.id} completed but has no result")
        return
    
    # Create participation for each registrant
    for reg in registrations:
        # Determine placement
        placement = get_placement_for_registration(result, reg)
        tier = get_placement_tier(placement)
        
        # Calculate stats
        stats = calculate_participant_stats(instance, reg)
        
        # Create record
        TournamentParticipation.objects.create(
            user=reg.user,
            tournament=instance,
            registration=reg,
            placement=placement,
            placement_tier=tier,
            matches_played=stats['matches_played'],
            matches_won=stats['matches_won'],
            kills=stats.get('kills', 0),
            deaths=stats.get('deaths', 0),
            prize_amount=calculate_prize(instance, placement),
            xp_earned=calculate_xp(instance, placement),
            recorded_by=instance.organizer
        )
```

**Helper Functions:**
```python
def get_placement_for_registration(result, registration):
    """Determine final placement for registration."""
    if result.winner_id == registration.id:
        return 1
    elif result.runner_up_id == registration.id:
        return 2
    elif result.third_place_id == registration.id:
        return 3
    else:
        # Get from bracket or return default
        return registration.final_placement or 999

def get_placement_tier(placement):
    """Convert numeric placement to tier."""
    if placement == 1:
        return 'winner'
    elif placement == 2:
        return 'runner_up'
    elif placement <= 4:
        return 'top4'
    elif placement <= 8:
        return 'top8'
    elif placement <= 16:
        return 'top16'
    else:
        return 'participant'
```

---

### 2.4 MatchParticipation Model (Optional)

**Purpose:** Track individual match results within tournaments

**When Needed:**
- Platform wants detailed match history (not just tournament outcomes)
- Win rate calculation requires match-level data
- Game-specific stats (K/D ratio, objective score)

**Schema:**

```
Table: match_participation
----------------------------------------
id (PK)
user_id (FK → User, indexed)
tournament_match_id (FK → Tournament.Match, nullable)
tournament_id (FK → Tournament, indexed)

# Match Details
game_name (VARCHAR)
mode (VARCHAR: Ranked/Casual/Competitive)
result (VARCHAR: win/loss/draw)

# Stats
score (VARCHAR, nullable)  # "13-7" for Valorant
kda (VARCHAR, nullable)    # "12/5/8" kills/deaths/assists
duration (Integer, nullable)  # Match duration in seconds

# Context
played_at (timestamp)
metadata (JSONField)  # Game-specific stats

INDEX (user_id, played_at DESC)  -- Fast user match history
INDEX (user_id, result)  -- Win rate calculation
```

**Integration with Profile:**
```python
# UserProfile methods
def get_match_history(self, limit=50):
    """Get recent matches."""
    return MatchParticipation.objects.filter(
        user=self.user
    ).order_by('-played_at')[:limit]

def calculate_win_rate(self):
    """Calculate overall win rate."""
    total = MatchParticipation.objects.filter(user=self.user).count()
    if total == 0:
        return 0
    wins = MatchParticipation.objects.filter(user=self.user, result='win').count()
    return int((wins / total) * 100)
```

---

### 2.5 Why Profile Cannot Rely on Live Queries

**Anti-Pattern (Current):**
```python
# BAD: Live query on every page load
@property
def tournament_participations(self):
    return TournamentParticipation.objects.filter(user=self.user)

# Template uses:
{{ profile.tournament_participations.count }}  ← Database query!
```

**Problems:**
1. **Performance:** Every profile view hits database
2. **Scaling:** 1000 profile views = 1000 queries
3. **Caching:** Cannot cache querysets reliably
4. **N+1:** If showing 10 profiles, 10 separate queries

---

**Correct Pattern (Cached Aggregate):**
```python
# UserProfile model
tournaments_played = models.IntegerField(
    default=0,
    editable=False,
    help_text="Total tournaments participated in (cached)"
)
tournaments_won = models.IntegerField(
    default=0,
    editable=False,
    help_text="Total tournaments won (cached)"
)
top3_finishes = models.IntegerField(
    default=0,
    editable=False,
    help_text="Total top-3 finishes (cached)"
)

# Signal updates after participation created
@receiver(post_save, sender=TournamentParticipation)
def update_profile_tournament_stats(sender, instance, created, **kwargs):
    if not created:
        return
    
    profile = instance.user.profile
    
    # Increment counters
    profile.tournaments_played += 1
    
    if instance.placement_tier == 'winner':
        profile.tournaments_won += 1
    
    if instance.placement_tier in ['winner', 'runner_up', 'top4']:
        profile.top3_finishes += 1
    
    profile.save(update_fields=[
        'tournaments_played',
        'tournaments_won',
        'top3_finishes',
        'updated_at'
    ])
```

**Benefits:**
- ✅ No query needed (field already in table)
- ✅ Fast: Simple integer read
- ✅ Cacheable: Can cache entire profile object
- ✅ Scalable: No JOIN, no COUNT()

**Trade-off:**
- ⚠️ Requires sync discipline (signal must work)
- ⚠️ Requires reconciliation (if drift occurs)
- ⚠️ Eventual consistency (slight delay after match)

**When to Use Live Query:**
- Detailed match list (pagination needed)
- Admin pages (staff needs real-time data)
- Analytics dashboards (aggregated views)

**When to Use Cached Aggregate:**
- Profile display (tournaments_played: 42)
- Leaderboards (ORDER BY tournaments_won DESC)
- Achievement checks (IF tournaments_won >= 10)

---

## 3. USER STATS SNAPSHOT

### 3.1 Stats Snapshot Philosophy

**Core Idea:** Profile stores a "snapshot" of user performance at current time.

**Snapshot vs Live:**

| Approach | Pros | Cons | Use Case |
|----------|------|------|----------|
| **Live Query** | Always accurate, no sync | Slow, doesn't scale | Admin pages, analytics |
| **Cached Snapshot** | Fast, scalable | Can drift, needs sync | Public profiles, leaderboards |

**Hybrid Approach (Recommended):**
- Profile stores cached snapshot (fast display)
- Background job refreshes periodically (detect drift)
- Critical stats have live fallback (if cache suspected wrong)

---

### 3.2 Stats Fields to Store in UserProfile

#### Category 1: Tournament Performance

```python
# Participation Counts
tournaments_played = models.IntegerField(default=0)
tournaments_won = models.IntegerField(default=0)
tournaments_runner_up = models.IntegerField(default=0)
top3_finishes = models.IntegerField(default=0)
top8_finishes = models.IntegerField(default=0)

# Performance Metrics
average_placement = models.DecimalField(
    max_digits=5,
    decimal_places=2,
    default=0,
    help_text="Average tournament placement (lower is better)"
)
best_placement = models.IntegerField(
    default=999,
    help_text="Best tournament finish (1=won)"
)
```

**Update Trigger:** TournamentParticipation created  
**Recalc Logic:**
```python
avg_placement = TournamentParticipation.objects.filter(
    user=user
).aggregate(Avg('placement'))['placement__avg']
```

---

#### Category 2: Match Performance

```python
# Match Counts
matches_played = models.IntegerField(default=0)
matches_won = models.IntegerField(default=0)
matches_lost = models.IntegerField(default=0)
matches_drawn = models.IntegerField(default=0)

# Derived Stats (calculated)
@property
def win_rate(self):
    """Calculate win rate percentage."""
    total = self.matches_played
    if total == 0:
        return 0
    return int((self.matches_won / total) * 100)

@property
def total_games(self):
    """Alias for matches_played (user-facing term)."""
    return self.matches_played
```

**Update Trigger:** MatchParticipation created  
**Recalc Logic:** COUNT(WHERE result='win')

---

#### Category 3: Economy Stats

```python
# Already covered in Section 1.4
deltacoin_balance = models.IntegerField(default=0)
lifetime_earnings = models.IntegerField(default=0)
total_spent = models.IntegerField(default=0)
transaction_count = models.IntegerField(default=0)
last_transaction_at = models.DateTimeField(null=True, blank=True)
```

**Update Trigger:** DeltaCrownTransaction created  
**Source:** SUM(transactions.amount)

---

#### Category 4: Platform Activity

```python
# Engagement
level = models.IntegerField(default=1)
xp = models.IntegerField(default=0)
reputation_score = models.IntegerField(
    default=100,
    help_text="Fair play karma (0-200)"
)

# Timestamps
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)
last_active_at = models.DateTimeField(
    null=True,
    blank=True,
    help_text="Last time user performed any action"
)
```

**Update Trigger:** Any user action  
**Recalc Logic:** Most recent activity timestamp

---

### 3.3 Update Triggers & Signal Flow

#### Trigger 1: Tournament Completes

```
Tournament.status → COMPLETED
  ↓
create_participation_records() signal
  ↓
FOR EACH participant:
  1. Create TournamentParticipation
  2. post_save signal fires
  3. Update Profile:
     - tournaments_played += 1
     - tournaments_won += 1 (if winner)
     - top3_finishes += 1 (if top 3)
     - average_placement recalculated
     - best_placement updated (if better)
```

**Signal Implementation:**
```python
@receiver(post_save, sender=TournamentParticipation)
def update_tournament_stats(sender, instance, created, **kwargs):
    if not created:
        return
    
    profile = instance.user.profile
    
    # Increment counters
    profile.tournaments_played += 1
    
    # Placement-based updates
    if instance.placement_tier == 'winner':
        profile.tournaments_won += 1
    elif instance.placement_tier == 'runner_up':
        profile.tournaments_runner_up += 1
    
    if instance.placement <= 3:
        profile.top3_finishes += 1
    if instance.placement <= 8:
        profile.top8_finishes += 1
    
    # Best placement
    if instance.placement < profile.best_placement:
        profile.best_placement = instance.placement
    
    # Average placement (recalculate)
    avg = TournamentParticipation.objects.filter(
        user=instance.user
    ).aggregate(Avg('placement'))['placement__avg']
    profile.average_placement = avg or 0
    
    profile.save(update_fields=[
        'tournaments_played',
        'tournaments_won',
        'tournaments_runner_up',
        'top3_finishes',
        'top8_finishes',
        'best_placement',
        'average_placement',
        'updated_at'
    ])
```

---

#### Trigger 2: Match Completes

```
Match.result recorded
  ↓
create_match_participation() service
  ↓
MatchParticipation created
  ↓
post_save signal fires
  ↓
Update Profile:
  - matches_played += 1
  - matches_won += 1 (if won)
  - win_rate recalculated
```

---

#### Trigger 3: Transaction Posted

```
DeltaCrownTransaction created
  ↓
post_save signal fires
  ↓
Update Wallet:
  - cached_balance recalculated
  ↓
Update Profile:
  - deltacoin_balance synced
  - lifetime_earnings += amount (if credit)
  - transaction_count += 1
```

---

### 3.4 Handling Disputes and Overrides

#### Dispute Scenario 1: Tournament Result Changed

**Problem:**
```
Tournament completed → Participation records created
  ↓
User disputes result → Organizer reviews
  ↓
Winner changed (User A → User B)
  ↓
Need to update participation records AND profile stats
```

**Solution: Soft Delete + Recreate**
```python
def change_tournament_winner(tournament, old_winner_reg, new_winner_reg):
    """
    Change tournament winner after result dispute.
    Updates participation records and profile stats.
    """
    with transaction.atomic():
        # 1. Soft delete old participations
        TournamentParticipation.objects.filter(
            tournament=tournament
        ).update(is_deleted=True)
        
        # 2. Decrement old winner stats
        old_winner_profile = old_winner_reg.user.profile
        old_winner_profile.tournaments_won -= 1
        old_winner_profile.save()
        
        # 3. Create new participations with correct winner
        create_participation_records(tournament, force=True)
        
        # 4. Log dispute resolution
        AuditEvent.objects.create(
            event_type='tournament_result_changed',
            actor=request.user,
            tournament=tournament,
            changes={
                'old_winner': old_winner_reg.user_id,
                'new_winner': new_winner_reg.user_id,
                'reason': 'Dispute resolved'
            }
        )
```

---

#### Dispute Scenario 2: User Stats Incorrect

**Problem:**
```
User reports: "I won 5 tournaments but profile shows 3"
Admin investigates: Signal failed during 2 tournaments
```

**Solution: Manual Recalculation**
```python
# Management command: recalc_user_stats.py
def recalculate_user_stats(user):
    """Recalculate all stats from source of truth."""
    profile = user.profile
    
    # Tournament stats
    participations = TournamentParticipation.objects.filter(user=user)
    profile.tournaments_played = participations.count()
    profile.tournaments_won = participations.filter(
        placement_tier='winner'
    ).count()
    profile.top3_finishes = participations.filter(
        placement__lte=3
    ).count()
    profile.average_placement = participations.aggregate(
        Avg('placement')
    )['placement__avg'] or 0
    
    # Match stats
    matches = MatchParticipation.objects.filter(user=user)
    profile.matches_played = matches.count()
    profile.matches_won = matches.filter(result='win').count()
    
    # Economy stats
    wallet = profile.dc_wallet
    profile.deltacoin_balance = wallet.cached_balance
    profile.lifetime_earnings = wallet.transactions.filter(
        amount__gt=0
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    profile.save()
    
    logger.info(f"Recalculated stats for user {user.id}")
```

**When to Run:**
- User disputes stats
- After data migration
- After bug fix (if signal was broken)
- Monthly reconciliation (background job)

---

#### Override Scenario: Admin Adjustment

**Problem:**
```
Tournament has 100 participants
System creates 100 TournamentParticipation records
One record has wrong placement (typo in bracket)
Admin needs to correct WITHOUT triggering signal spam
```

**Solution: Update with skip_signal flag**
```python
# In TournamentParticipation model
class TournamentParticipation(models.Model):
    # ... fields ...
    
    def save(self, *args, skip_signal=False, **kwargs):
        self._skip_signal = skip_signal
        super().save(*args, **kwargs)

# In signal
@receiver(post_save, sender=TournamentParticipation)
def update_stats(sender, instance, created, **kwargs):
    if getattr(instance, '_skip_signal', False):
        return  # Skip update
    # ... normal logic ...

# Admin action
participation.placement = 4  # Fix typo
participation.save(skip_signal=True)  # Don't trigger profile update
```

---

### 3.5 Stats Reconciliation Strategy

#### Daily Reconciliation Job

**Purpose:** Detect drift between cached stats and source of truth

**Command:** `python manage.py reconcile_user_stats`

**Logic:**
```python
def reconcile_all_users():
    """
    Check all users for stat drift.
    Runs nightly via cron.
    """
    drift_detected = 0
    
    for profile in UserProfile.objects.iterator(chunk_size=1000):
        # Check tournament stats
        actual_tournaments = TournamentParticipation.objects.filter(
            user=profile.user
        ).count()
        
        if profile.tournaments_played != actual_tournaments:
            logger.warning(
                f"User {profile.user.id} tournament drift: "
                f"cached={profile.tournaments_played}, "
                f"actual={actual_tournaments}"
            )
            recalculate_user_stats(profile.user)
            drift_detected += 1
        
        # Check economy stats
        actual_balance = profile.dc_wallet.cached_balance
        if profile.deltacoin_balance != actual_balance:
            logger.warning(
                f"User {profile.user.id} balance drift: "
                f"cached={profile.deltacoin_balance}, "
                f"actual={actual_balance}"
            )
            profile.deltacoin_balance = actual_balance
            profile.save()
            drift_detected += 1
    
    logger.info(f"Reconciliation complete. Drift detected: {drift_detected}")
    
    # Alert if drift > 1% of users
    total_users = UserProfile.objects.count()
    drift_percentage = (drift_detected / total_users) * 100
    if drift_percentage > 1.0:
        send_alert_to_ops(
            f"High stat drift detected: {drift_percentage:.2f}% of users"
        )
```

**Schedule:** Run at 3 AM daily (low traffic)  
**Duration:** ~5 minutes for 100K users  
**Alert Threshold:** > 1% drift = investigate signal issues

---

### 3.6 Profile Stats Summary

**What to Cache:**
- ✅ Counts (tournaments_played, matches_won)
- ✅ Simple aggregates (lifetime_earnings, average_placement)
- ✅ Last update timestamps (last_transaction_at, last_active_at)

**What NOT to Cache:**
- ❌ Complex calculations (percentile rankings)
- ❌ Time-dependent data (weekly leaderboard position)
- ❌ Cross-user comparisons (vs platform average)

**When to Recalculate:**
- ⏱️ Real-time: Simple increments (count += 1)
- 🌙 Nightly: Complex aggregates (average, sum)
- 📅 Weekly: Leaderboards and rankings
- 🔧 On-demand: Dispute resolution, data fixes

---

## IMPLEMENTATION CHECKLIST

### Economy Integration (UP-3)
- [ ] Add economy stats fields to UserProfile
- [ ] Create signal: transaction → update profile
- [ ] Create management command: reconcile_balances
- [ ] Create view: transaction_history
- [ ] Add transaction privacy controls
- [ ] Test: Balance sync after transaction
- [ ] Test: Reconciliation fixes drift

### Tournament Stats (UP-4)
- [ ] Create TournamentParticipation model
- [ ] Create MatchParticipation model (optional)
- [ ] Create signal: tournament completion → participation records
- [ ] Create signal: participation → update profile stats
- [ ] Create management command: recalc_tournament_stats
- [ ] Add tournament history page
- [ ] Test: Participation created after tournament
- [ ] Test: Stats increment correctly
- [ ] Test: Dispute resolution updates stats

### Stats Reconciliation (UP-5)
- [ ] Create management command: reconcile_user_stats
- [ ] Add cron job: Run nightly at 3 AM
- [ ] Add monitoring: Alert if >1% drift
- [ ] Add admin action: Recalculate single user
- [ ] Test: Reconciliation detects drift
- [ ] Test: Reconciliation fixes incorrect stats
- [ ] Document: When to run reconciliation

---

**END OF ECONOMY & STATS ARCHITECTURE**

**Status:** Ready for Implementation  
**Next Step:** Create UP_EXECUTION_PLAN.md with detailed phases

---

*Document Version: 1.0*  
*Last Updated: December 22, 2025*  
*Author: Platform Architecture Team*  
*Review Status: Approved*
