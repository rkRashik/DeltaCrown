# Bounty System Technical Design
**Date:** December 31, 2025  
**Architect:** Principal Backend Architect  
**Type:** Technical Design (No Implementation)  
**Scope:** Peer-to-Peer Challenge System

---

## 1. System Intent

The Bounty System is a peer-to-peer, escrow-backed challenge platform where any DeltaCrown user can create competitive 1v1 challenges across all 11 supported games (Valorant, PUBG, CS2, MLBB, Free Fire, etc.), lock their stake using the existing `DeltaCrownWallet.pending_balance` escrow mechanism, and allow other users to browse and accept open challenges. When a bounty is completed, the winner receives the escrowed stake (minus platform fee), and if no one accepts within the expiry window (default 72 hours), the creator's stake is automatically refunded. This system extends DeltaCrown's competitive ecosystem beyond tournament brackets to spontaneous, player-driven matchmaking with financial incentives, while reusing existing economy escrow patterns, match result submission workflows, and team notification infrastructure.

---

## 2. Bounty Lifecycle (State Machine)

The bounty follows this state progression:

```
OPEN
  ├─> ACCEPTED (user accepts challenge)
  │     └─> IN_PROGRESS (match started/lobby created)
  │           └─> PENDING_RESULT (participant submits result + proof)
  │                 ├─> COMPLETED (result verified, winner paid)
  │                 └─> DISPUTED (result challenged by opponent)
  │                       ├─> COMPLETED (moderator resolves, winner paid)
  │                       └─> CANCELLED (moderator cancels, refunds both)
  │
  ├─> EXPIRED (no acceptor within 72 hours, auto-refund creator)
  │
  └─> CANCELLED (creator cancels before acceptance, instant refund)
```

**Valid State Transitions:**
- `OPEN` → `ACCEPTED` (when user accepts challenge)
- `OPEN` → `EXPIRED` (auto-transition by expiry task after 72 hours)
- `OPEN` → `CANCELLED` (creator cancels before acceptance)
- `ACCEPTED` → `IN_PROGRESS` (participants confirm match start)
- `IN_PROGRESS` → `PENDING_RESULT` (winner submits proof)
- `PENDING_RESULT` → `COMPLETED` (auto-verify or admin approves)
- `PENDING_RESULT` → `DISPUTED` (loser disputes within 24 hours)
- `DISPUTED` → `COMPLETED` (moderator confirms winner)
- `DISPUTED` → `CANCELLED` (moderator voids match, refunds both)

**Terminal States (no further transitions):**
- `COMPLETED` - Winner paid, escrow released
- `EXPIRED` - Refunded to creator
- `CANCELLED` - Refunded to creator (or both parties if post-acceptance)

---

## 3. Expiry Mechanism (High-Level)

**Expiry Trigger:**
- Bounties in `OPEN` state automatically expire after 72 hours (default, configurable per bounty)
- A scheduled background task (Celery periodic task or Django management command via cron) runs every 15 minutes
- Query: `Bounty.objects.filter(status='OPEN', expires_at__lte=now())`
- For each expired bounty:
  1. Transition state from `OPEN` → `EXPIRED`
  2. Call `economy.services.refund_bounty_stake(bounty)` to:
     - Deduct `pending_balance` on creator's wallet
     - Credit `cached_balance` back to creator (BOUNTY_REFUND transaction)
  3. Publish `BountyExpiredEvent` to notify creator via event bus
  4. Log event to `UserActivity` with `event_type='BOUNTY_EXPIRED'`

**Expiry Extension:**
- If bounty moves to `ACCEPTED` state before expiry, the `expires_at` timestamp is cleared (no longer applicable)
- If creator cancels (`OPEN` → `CANCELLED`), same refund flow applies immediately without waiting for expiry task

**Edge Cases:**
- If expiry task runs while user is accepting bounty (race condition), database transaction isolation prevents double-transition
- Use `select_for_update()` on bounty row during acceptance to lock state
- Idempotency key on refund transaction prevents duplicate refunds if task retries

---

## 4. Models Required

**Core Models:**

- **Bounty** - Main challenge entity tracking creator, stake amount, game, requirements, status, and timestamps
- **BountyAcceptance** - Records when a user accepts a bounty (acceptor, accepted_at, proof links)
- **BountyProof** - Stores proof submissions (screenshot/video URLs, submitted_by, submission_timestamp)
- **BountyDispute** - Tracks disputes raised by participants (disputer, reason, moderator assignment, resolution)

**Supporting Models (Optional/Consider):**

- **BountyRequirement** - Structured game-specific requirements (e.g., "First to 100k in Gridshot", "Best of 3 rounds")
- **BountyNotification** - Tracks notification delivery to creator/acceptor/team members (sent_at, read_at)

**Models NOT Needed (Reuse Existing):**

- ❌ **BountyWallet** - Use existing `DeltaCrownWallet.pending_balance`
- ❌ **BountyTransaction** - Use existing `DeltaCrownTransaction` with new reasons
- ❌ **BountyActivity** - Use existing `UserActivity` with new event types
- ❌ **BountyMatch** - Link to existing `Match` model from tournaments app (optional reference)

---

## 5. BountyService Responsibilities

**Service Layer Pattern:**
- All business logic lives in `apps/user_profile/services/bounty_service.py` (not views or models)
- Services coordinate between Bounty models and economy app using adapter pattern

**Core Methods:**

- **create_bounty(creator, title, game, stake_amount, requirements)**
  - Validates creator has sufficient available balance (`cached_balance - pending_balance >= stake_amount`)
  - Creates Bounty record with `status='OPEN'` and `expires_at = now() + 72 hours`
  - Calls `economy.services.lock_bounty_stake()` to debit `cached_balance` and increment `pending_balance`
  - Publishes `BountyCreatedEvent` to event bus for notification system

- **accept_bounty(bounty_id, acceptor)**
  - Validates bounty is in `OPEN` state and not expired
  - Checks acceptor eligibility (not creator, meets reputation threshold, not blocked)
  - Creates BountyAcceptance record linking acceptor to bounty
  - Transitions bounty from `OPEN` → `ACCEPTED`, clears `expires_at`
  - Publishes `BountyAcceptedEvent` to notify creator and acceptor's team (if team-game)

- **submit_result(bounty_id, submitted_by, winner_id, proof_urls)**
  - Validates bounty is in `IN_PROGRESS` state
  - Creates BountyProof record with screenshot/video links
  - Transitions bounty to `PENDING_RESULT` state
  - Starts 24-hour dispute window timer
  - Publishes `BountyResultSubmittedEvent` to notify opponent

- **complete_bounty(bounty_id, winner_id)**
  - Validates bounty is in `PENDING_RESULT` state and dispute window expired
  - Calls `economy.services.release_bounty_to_winner()` to unlock escrow and pay winner
  - Transitions bounty to `COMPLETED` state
  - Records UserActivity events (`BOUNTY_WON` for winner, `BOUNTY_LOST` for loser)

- **raise_dispute(bounty_id, disputer, reason)**
  - Validates bounty is in `PENDING_RESULT` state and within 24-hour window
  - Creates BountyDispute record with reason and assigns moderator queue
  - Transitions bounty to `DISPUTED` state
  - Publishes `BountyDisputedEvent` to notify moderators and opponent

- **resolve_dispute(dispute_id, moderator, decision)**
  - Validates moderator has permission and dispute is unresolved
  - If decision confirms winner: Calls `complete_bounty()`
  - If decision voids match: Calls `refund_bounty_stake()` for both parties
  - Closes dispute record with resolution timestamp

- **expire_bounty(bounty_id)**
  - Called by scheduled task for bounties in `OPEN` state past `expires_at`
  - Transitions bounty to `EXPIRED` state
  - Calls `economy.services.refund_bounty_stake()` to return funds to creator
  - Publishes `BountyExpiredEvent` to notify creator

- **cancel_bounty(bounty_id, cancelled_by)**
  - Validates bounty is in `OPEN` state (only pre-acceptance cancellation allowed)
  - Validates `cancelled_by` is the creator
  - Transitions bounty to `CANCELLED` state
  - Calls `economy.services.refund_bounty_stake()` to return funds
  - Publishes `BountyCancelledEvent`

---

## 6. Economy Integration (Escrow Pattern)

**Reusing DeltaCrownWallet.pending_balance:**

The existing `apps/economy/models.py` wallet already has a `pending_balance` field designed for locking funds during withdrawals. We repurpose this same mechanism for bounty escrow:

- **On Bounty Creation (`OPEN` state):**
  - Call `economy.services.debit(profile, stake_amount, reason='BOUNTY_ESCROW', idempotency_key=f'bounty:escrow:{bounty.id}')`
  - This creates a `DeltaCrownTransaction` debit entry and reduces `cached_balance`
  - Simultaneously increment `wallet.pending_balance += stake_amount` using atomic transaction with `select_for_update()`
  - Net effect: `available_balance = cached_balance - pending_balance` reflects locked funds

- **On Bounty Completion (`COMPLETED` state):**
  - Decrement creator's `pending_balance -= stake_amount` (release escrow lock)
  - Calculate winner payout: `payout = stake_amount * 0.95` (5% platform fee)
  - Call `economy.services.credit(winner_profile, payout, reason='BOUNTY_WIN', idempotency_key=f'bounty:win:{bounty.id}')`
  - Call `economy.services.credit(platform_wallet, platform_fee, reason='BOUNTY_FEE', idempotency_key=f'bounty:fee:{bounty.id}')`
  - Both transactions use idempotency keys to prevent duplicate payouts if task retries

- **On Bounty Expiry/Cancellation (`EXPIRED`/`CANCELLED` state):**
  - Decrement creator's `pending_balance -= stake_amount` (release escrow lock)
  - Call `economy.services.credit(creator_profile, stake_amount, reason='BOUNTY_REFUND', idempotency_key=f'bounty:refund:{bounty.id}')`
  - Net effect: Creator gets full refund, `available_balance` returns to pre-bounty amount

**Why This Works:**
- `pending_balance` already prevents users from spending locked funds (wallet balance checks subtract it)
- Existing `DeltaCrownTransaction` immutability ensures audit trail
- `select_for_update()` row locking prevents race conditions during balance updates
- Idempotency keys prevent duplicate transactions if Celery tasks retry

---

## 7. Expiry Refund Flow (Conceptual)

**Scheduled Task (Celery Periodic Task or Cron):**

- Runs every 15 minutes (configurable interval)
- Queries: `Bounty.objects.filter(status='OPEN', expires_at__lte=timezone.now()).select_for_update()`
- For each expired bounty in transaction:
  1. Lock bounty row to prevent concurrent acceptance
  2. Verify status is still `OPEN` (double-check after lock acquired)
  3. Transition `status` from `OPEN` → `EXPIRED`
  4. Call `BountyService.expire_bounty(bounty.id)` which:
     - Decrements `pending_balance` on creator's wallet
     - Credits `cached_balance` with refund transaction (`BOUNTY_REFUND` reason)
     - Publishes `BountyExpiredEvent` to event bus
     - Creates `UserActivity` record: `event_type='BOUNTY_EXPIRED'`

**Race Condition Handling:**

- If a user accepts bounty while expiry task is running:
  - `select_for_update()` ensures only one transaction wins the lock
  - If acceptance wins: Bounty transitions to `ACCEPTED`, task sees wrong state and skips
  - If expiry wins: Acceptance sees `EXPIRED` state and rejects request with error
- Idempotency key on refund transaction: `bounty:refund:{bounty.id}:{creator_wallet.id}`
  - If task crashes and retries, duplicate refund attempt returns existing transaction
  - No risk of double-refunding creator

**Expiry Notification:**

- `BountyExpiredEvent` triggers notification service to send:
  - In-app notification: "Your bounty '{title}' expired with no takers. Stake refunded."
  - Email notification (if user has email notifications enabled)
  - Push notification to mobile app (future)

---

## 8. Permissions & Anti-Abuse Rules

**Who Can Create Bounties:**

- Any authenticated user with verified email
- Must have `available_balance >= stake_amount` (cached_balance - pending_balance)
- Minimum reputation score: 50 (prevents new account spam)
- Rate limit: Maximum 10 bounties per user per 24 hours
- Minimum stake: 100 DC (prevents spam with trivial amounts)
- Maximum stake: 50,000 DC (risk management, subject to adjustment)

**Who Can Accept Bounties:**

- Any authenticated user except the bounty creator
- Must meet minimum reputation threshold: 50
- Must not be blocked by bounty creator
- If bounty has `target_user_id`, only that user can accept (private challenge)
- If bounty is team-game type, acceptor must be member of target team
- Must not have 3+ active bounties already (prevents hoarding)

**Who Can Submit Results:**

- Only the two participants (creator or acceptor) can submit proof
- First submission transitions bounty to `PENDING_RESULT` state
- Opponent has 24 hours to dispute or result auto-confirms
- Must include at least one proof URL (screenshot or video link)

**Who Can Raise Disputes:**

- Only the participant who did NOT submit the result (the opponent)
- Must dispute within 24 hours of result submission
- Can only dispute once per bounty (no re-disputing after resolution)
- Must provide written reason (minimum 50 characters)

**Who Can Resolve Disputes:**

- Only staff users with `is_staff=True` permission
- Moderator assigned via admin queue (FIFO or priority-based)
- Moderator sees both proof submissions and dispute reason
- Decision options: Confirm winner, Reverse winner, Void match (refund both)

**Who Can Cancel Bounties:**

- Only the creator can cancel
- Only allowed in `OPEN` state (before acceptance)
- After acceptance, cannot cancel (prevents escrow manipulation)
- Instant refund on cancellation

**Anti-Abuse Measures:**

- Reputation decay if user loses 3+ disputes in a row (prevents false result claims)
- Cooldown period: 1 hour between creating bounties (prevents spam)
- Blocked users list: Creators can block specific users from accepting their bounties
- Automatic flag for review: If bounty has 3+ disputes across lifetime, flag creator account
- Stake lockout: If user has 5+ pending bounties, cannot create more until some complete

---

## 9. Team Notifications (Team-Game Bounties)

**When Team Notifications Trigger:**

- Bounties can be flagged as "team-game" type (e.g., Valorant 5v5, CS2 5v5)
- If `bounty.game.is_team_game = True` and bounty has `target_user_id`, notify target's team

**Notification Flow on Bounty Creation:**

- Query target user's active team memberships: `TeamMembership.objects.filter(profile__user=target_user, status='ACTIVE')`
- For each team, notify captain(s): `memberships.filter(role__in=['OWNER', 'CAPTAIN'])`
- Notification message: "{creator.username} challenged {target.username} to {game.name} - {stake_amount} DC on the line"
- Notification includes "View Bounty" link to bounty detail page
- Captain can see if their player accepted or needs encouragement/advice

**Notification Flow on Bounty Acceptance:**

- If acceptor is member of a team for that game, notify their team captain
- Notification message: "{acceptor.username} accepted {creator.username}'s bounty - {game.name} for {stake_amount} DC"
- Allows team to coordinate practice or spectate the match

**Notification Flow on Bounty Completion:**

- If winner is team member, notify team captain and all active members
- Notification message: "{winner.username} won bounty against {loser.username} - earned {payout} DC!"
- Boosts team morale and visibility of member performance

**Team Feed Integration (Future):**

- If `apps/community/` Post system exists, bounty acceptance/completion can auto-post to team feed
- "Challenge accepted! Watch {player.username} take on {opponent.username} live!" with match link
- Increases engagement and spectator interest

---

## 10. Profile Context Variables Required

**For Profile Overview Tab (public_v3.html):**

- `user_bounties_stats` (dict):
  - `created_count` - Total bounties created by user
  - `accepted_count` - Total bounties accepted by user
  - `won_count` - Bounties won (completed as winner)
  - `lost_count` - Bounties lost (completed as loser)
  - `win_rate` - Percentage: `won_count / (won_count + lost_count)` if > 0 else 0
  - `total_earnings` - Sum of all `BOUNTY_WIN` transactions
  - `total_wagered` - Sum of all `BOUNTY_ESCROW` transactions

**For Bounties Tab (new tab in profile navigation):**

- `active_bounties` (QuerySet):
  - Bounties where user is creator OR acceptor
  - Status in `['OPEN', 'ACCEPTED', 'IN_PROGRESS', 'PENDING_RESULT', 'DISPUTED']`
  - Ordered by `created_at` descending
  - Includes: title, game, stake_amount, status, expires_at, opponent (if accepted)

- `completed_bounties` (QuerySet):
  - Bounties where user is creator OR acceptor
  - Status in `['COMPLETED', 'EXPIRED', 'CANCELLED']`
  - Ordered by `completed_at` descending
  - Paginated: 20 per page
  - Includes: title, game, stake_amount, winner_id, completed_at, payout

- `open_bounties_feed` (QuerySet):
  - All bounties with `status='OPEN'` and `expires_at > now()`
  - Filtered by game if user has game preference set
  - Exclude bounties created by current user
  - Exclude bounties where current user is in creator's blocked list
  - Ordered by `created_at` descending
  - Paginated: 50 per page

**For Bounty Detail Page (bounty_detail.html):**

- `bounty` (Bounty object): Full bounty details
- `creator_profile` (UserProfile): Creator's profile data
- `acceptor_profile` (UserProfile or None): Acceptor's profile if bounty accepted
- `proofs` (QuerySet of BountyProof): All proof submissions for this bounty
- `dispute` (BountyDispute or None): Active dispute if bounty in DISPUTED state
- `can_accept` (bool): Permission check for current viewer
- `can_submit_result` (bool): Permission check for participants
- `can_dispute` (bool): Permission check for opponent after result submission
- `can_cancel` (bool): Permission check for creator (only if status=OPEN)
- `time_until_expiry` (timedelta or None): If status=OPEN, time remaining until auto-refund
- `time_until_auto_confirm` (timedelta or None): If status=PENDING_RESULT, time until dispute window closes

**For Wallet Tab (existing, needs extension):**

- `bounty_transactions` (QuerySet):
  - Filter `DeltaCrownTransaction` by `reason__in=['BOUNTY_ESCROW', 'BOUNTY_WIN', 'BOUNTY_REFUND', 'BOUNTY_FEE']`
  - Show bounty-specific transaction history
  - Include `metadata` field showing bounty title and opponent

- `pending_bounty_escrow` (int):
  - Sum of all active bounty stakes: `Bounty.objects.filter(creator=user, status__in=['OPEN', 'ACCEPTED', 'IN_PROGRESS', 'PENDING_RESULT']).aggregate(Sum('stake_amount'))`
  - Display as "Locked in Bounties: {amount} DC" below available balance

**For Community Feed (Challenge Cards - Conceptual):**

- `recent_bounties` (QuerySet):
  - Recent bounties from followed users or popular/high-stake bounties
  - Status `OPEN` or recently completed (`COMPLETED` within last 24 hours)
  - Card displays: creator avatar, game icon, stake amount, "Accept Challenge" button
  - If completed: Show winner, payout, "View Replay" link

**Permission Context Variables (for all bounty pages):**

- `user_reputation_score` (int): Current user's reputation (required for creating/accepting)
- `user_available_balance` (int): `wallet.cached_balance - wallet.pending_balance`
- `user_blocked_by_creator` (bool): Check if current user in bounty creator's block list
- `user_daily_bounty_count` (int): Bounties created by user today (for rate limit display)

---

## 11. Open Questions & Design Decisions Needed

**Question 1: Should bounties integrate with existing Match model?**
- Option A: Create Match record when bounty accepted, reuse result submission workflow
- Option B: Keep bounties separate, lighter-weight system without full match infrastructure
- **Recommendation**: Option B initially (simpler), migrate to Option A if we want tournament integration

**Question 2: What games should support bounties initially?**
- All 11 games or start with subset (Valorant, CS2, PUBG)?
- Team-game bounties (5v5) or solo-only initially?
- **Recommendation**: Start with solo 1v1 games (Aim Lab, Gridshot), expand after MVP validation

**Question 3: How are proof submissions validated?**
- Manual review by moderators for all bounties?
- Auto-verify if no dispute raised within 24 hours?
- Require specific proof format (e.g., screenshot with timestamp)?
- **Recommendation**: Auto-verify after 24 hours, manual review only if disputed

**Question 4: Should creators be able to set custom expiry times?**
- Default 72 hours, allow creators to choose 24h / 48h / 72h / 7d?
- Or fixed 72 hours for all bounties?
- **Recommendation**: Fixed 72 hours for MVP, add custom expiry in Phase 2

**Question 5: Platform fee structure?**
- Fixed 5% fee on all bounties?
- Tiered fee (higher stakes = lower percentage)?
- No fee initially to encourage adoption?
- **Recommendation**: 5% flat fee (aligns with tournament prize fees), clearly displayed at creation

**Question 6: Should team-game bounties support team vs team (not just 1v1)?**
- 5v5 team bounties with pooled stakes?
- Requires team wallet system (complex)?
- **Recommendation**: Defer to Phase 2, MVP is 1v1 only (including for team-game titles)

**Question 7: What happens if user deletes account with active bounty?**
- Auto-cancel all open bounties with refunds?
- Auto-forfeit all accepted bounties (opponent wins)?
- Block account deletion if active bounties exist?
- **Recommendation**: Block deletion if status in `['ACCEPTED', 'IN_PROGRESS', 'PENDING_RESULT', 'DISPUTED']`, auto-cancel `OPEN` bounties

---

## 12. Implementation Priority (Phased Rollout)

**Phase 1 (MVP - Week 1-2):**
- Bounty model with basic state machine (OPEN → ACCEPTED → COMPLETED)
- BountyService: create, accept, complete (no disputes yet)
- Escrow integration using pending_balance
- Expiry task with refund flow
- Profile context: active_bounties, completed_bounties, stats
- Admin panel for manual dispute resolution

**Phase 2 (Enhanced - Week 3-4):**
- BountyProof model and proof submission flow
- BountyDispute model with moderator queue
- Dispute resolution workflow (confirm/reverse/void)
- Team notifications for team-game bounties
- Anti-abuse: reputation system, rate limits, blocked users
- Community feed integration (Challenge Cards)

**Phase 3 (Advanced - Week 5+):**
- Custom expiry times
- Team vs team bounties (pooled stakes)
- Match integration (create Match record on acceptance)
- Advanced proof validation (OCR timestamp detection)
- Leaderboard: Top bounty hunters, biggest wins
- Mobile push notifications

---

**DESIGN COMPLETE**

**Document Status:** ✅ Ready for Technical Review  
**Next Steps:**
1. Review with product team for open questions
2. Create detailed model schemas (fields, constraints, indexes)
3. Write service method signatures and error handling specs
4. Design API endpoints (REST or GraphQL)
5. Create migration plan and rollout strategy

---

**END OF BOUNTY SYSTEM DESIGN**
