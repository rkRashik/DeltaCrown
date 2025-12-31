# Bounty System Risk Review
**Date:** December 31, 2025  
**Reviewer:** Security & Abuse-Prevention Engineer  
**Type:** Risk Assessment & Mitigation Strategy  
**Scope:** Peer-to-Peer Challenge System (Bounty)

---

## 1. Money & Escrow Risks

### Risk 1.1: Double Refund on Expiry
**Description:** Expiry task runs concurrently with user cancellation, both trigger refund transaction, creator receives 2x stake amount.

**Severity:** 🔴 **High**

**Mitigation:**
- Use idempotency key pattern: `bounty:refund:{bounty.id}:{wallet.id}` on all refund transactions
- `DeltaCrownTransaction.idempotency_key` has unique constraint - second refund attempt returns existing transaction
- Database-level check constraint: `SELECT FOR UPDATE` on bounty during state transition (locks row)

### Risk 1.2: Race Condition on Acceptance During Expiry
**Description:** User accepts bounty at exact moment expiry task marks it expired, both transitions succeed, user's acceptance lost but they believe bounty is active.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Expiry task uses `SELECT FOR UPDATE` when querying bounties to expire (locks rows during check)
- Acceptance transaction checks bounty state after acquiring lock: `if bounty.status != 'OPEN': raise InvalidState`
- Database transaction isolation (READ COMMITTED) prevents dirty reads

### Risk 1.3: Pending Balance Desync
**Description:** Escrow debit succeeds but `pending_balance` increment fails (server crash mid-transaction), user's available balance incorrect, funds locked but not tracked.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Wrap debit + pending_balance increment in single `@transaction.atomic` block
- Use database-level triggers or constraints to validate `available_balance >= 0` at all times
- Scheduled reconciliation job (daily) compares `pending_balance` to active bounty stakes, alerts on mismatch

### Risk 1.4: Idempotency Key Collision
**Description:** Two bounties created simultaneously with same ID (unlikely but possible with UUID collisions or sequence resets), idempotency keys collide, second escrow fails silently.

**Severity:** 🟡 **Low**

**Mitigation:**
- Use UUID for bounty IDs (128-bit, collision probability negligible)
- Idempotency key format includes timestamp: `bounty:escrow:{bounty.id}:{wallet.id}:{created_at.timestamp()}`
- Monitor transaction creation failures, alert on idempotency key rejects

### Risk 1.5: Platform Fee Calculation Error
**Description:** Winner payout calculation error (typo: `stake * 1.05` instead of `* 0.95`), platform loses money or overcharges users.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Store platform fee percentage in database config (not hardcoded): `SiteSetting.objects.get(key='bounty_platform_fee')` = 0.05
- Validate payout calculation in tests: Assert `payout + platform_fee == stake_amount`
- Log all fee calculations with metadata: `{"stake": 5000, "fee_pct": 0.05, "payout": 4750, "fee": 250}`

### Risk 1.6: Insufficient Balance Check Bypass
**Description:** User creates bounty, balance check passes, but concurrent withdrawal depletes wallet before escrow debit executes.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Use `SELECT FOR UPDATE` on wallet during bounty creation (locks wallet row)
- Re-check balance after lock acquired: `if locked_wallet.available_balance < stake: raise InsufficientFunds`
- Database check constraint: `CHECK (cached_balance - pending_balance >= 0)`

### Risk 1.7: Orphaned Escrow on Bounty Delete
**Description:** Admin deletes bounty record (via admin panel) without releasing escrow, funds permanently locked in `pending_balance`.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Override `Bounty.delete()` method to release escrow before deletion: `self.refund_escrow(); super().delete()`
- Admin panel shows warning: "Deleting bounty will refund {stake_amount} DC to creator. Continue?"
- Soft-delete pattern: Set `deleted_at` timestamp instead of hard delete, escrow cleanup happens via signal

---

## 2. Abuse & Spam Risks

### Risk 2.1: Low-Stake Spam Flooding
**Description:** Malicious user creates 100 bounties at minimum stake (100 DC each), floods feed, drowns out legitimate bounties.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Rate limit: Max 10 bounties per user per 24 hours (enforced in `create_bounty()`)
- Cooldown: 1 hour between bounty creations (last_created_at check)
- Reputation requirement: Minimum 50 reputation to create bounties (prevents throwaway accounts)

### Risk 2.2: Bounty Hoarding (Acceptance Spam)
**Description:** User accepts 20 open bounties simultaneously, never completes any, locks out other users from accepting.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Limit active acceptances: User can accept max 3 bounties concurrently (check `BountyAcceptance.filter(acceptor=user, status__in=['ACCEPTED', 'IN_PROGRESS']).count()`)
- Auto-forfeit: If bounty in `ACCEPTED` state for 7+ days with no progress, auto-transition to `EXPIRED` and refund creator
- Reputation penalty: User loses 10 reputation points for each forfeited bounty

### Risk 2.3: Sybil Attack (Multiple Accounts)
**Description:** User creates 10 accounts, each creates bounties, accepts own bounties across accounts, manipulates win rate stats.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Email verification required before creating bounties (one bounty system access per verified email)
- IP-based rate limiting: Max 5 bounty creations per IP per day
- Behavioral analysis: Flag users who only accept bounties from same small group of users (collusion pattern)

### Risk 2.4: Reputation Farming via Fake Bounties
**Description:** Two colluding users create low-stake bounties, accept each other's bounties, submit fake proofs, win 95% of stake back repeatedly to inflate reputation.

**Severity:** 🟡 **Low**

**Mitigation:**
- Reputation gain from bounties capped: Max 10 reputation points per day from bounty wins
- Review suspicious patterns: Same two users completing 10+ bounties together in short period (flag for manual review)
- Minimum stake for reputation gain: Bounties below 500 DC don't award reputation (prevents penny farming)

### Risk 2.5: Blocked User List Abuse
**Description:** User blocks all high-skill players, only accepts bounties from weaker opponents, inflates win rate artificially.

**Severity:** 🟡 **Low**

**Mitigation:**
- Block list has limit: Max 50 blocked users per account (prevents mass blocking)
- Blocking requires reason (dropdown: Harassment, Cheating, Poor Sportsmanship) for audit trail
- Win rate stat shows caveat: "Win rate calculated from accepted bounties only" (transparency)

---

## 3. Dispute Abuse Risks

### Risk 3.1: False Dispute Spam
**Description:** User loses bounty fairly, disputes anyway with fake reason, forces moderator review, delays winner payout, wastes moderator time.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Dispute fee: User must pay 10% of stake to raise dispute (refunded if dispute upheld, forfeited if frivolous)
- Reputation penalty: Losing 3+ disputes in row results in -50 reputation and 7-day bounty suspension
- Auto-reject: If dispute reason is < 50 characters or contains only "fake" / "cheater" without evidence, auto-reject

### Risk 3.2: Moderator Queue Overload
**Description:** 100+ disputes raised per day, moderator team of 5 can't keep up, disputes sit unresolved for weeks, users frustrated.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Auto-resolution: If no moderator reviews dispute within 72 hours, default to original result (winner gets paid)
- Community moderation: High-reputation users (1000+) can vote on disputes, 3 consistent votes triggers resolution
- Dispute priority queue: High-stake disputes ($50+ equivalent) reviewed first

### Risk 3.3: Moderator Bias/Corruption
**Description:** Moderator friends with one participant, unfairly resolves dispute in their favor, ruins platform trust.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Moderator audit log: All dispute resolutions logged with moderator ID, decision, timestamp, reason
- Appeal system: Losing party can appeal dispute resolution once, reviewed by senior moderator
- Moderator performance metrics: Track resolution accuracy (overturned appeals), remove moderators with high overturn rate

### Risk 3.4: Evidence Tampering
**Description:** User submits fake screenshot (photoshopped scoreboard), opponent has no counter-evidence, fake proof accepted.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Proof requirement: Both participants must submit proof within 24 hours (not just winner)
- Timestamp validation: Screenshots must include game timestamp, cross-check with bounty start time
- Third-party integration: Prefer in-game API proof (Riot API for Valorant, Steam API for CS2) over manual screenshots

### Risk 3.5: Dispute Window Exploitation
**Description:** Loser waits 23 hours 59 minutes to dispute, winner already spent payout assuming auto-confirmation, now must reverse transaction.

**Severity:** 🟡 **Low**

**Mitigation:**
- Payout delayed: Winner receives payout only after 24-hour dispute window closes (no early payout)
- Clear messaging: "Payout pending dispute window (23 hours remaining)" shown to winner
- Dispute notification: Both parties notified immediately when dispute raised, no surprises

---

## 4. Privacy & Harassment Risks

### Risk 4.1: Targeted Harassment via Bounties
**Description:** User creates multiple bounties targeting specific player ("1v1 me, prove you're not trash"), spams notifications, harasses victim.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Target user opt-in: If bounty specifies `target_user_id`, target must accept notification before seeing bounty
- Block prevents targeting: If target has creator blocked, creator cannot create bounty targeting that user
- Harassment reporting: Target can report bounty as harassment, admin can disable creator's bounty privilege

### Risk 4.2: Profile Stalking via Bounty History
**Description:** Malicious user creates bounties targeting victim's teammates to gather info about victim's play schedule, team composition, stalking risk.

**Severity:** 🟡 **Low**

**Mitigation:**
- Privacy setting: "Hide bounty history from non-followers" option in profile settings
- Anonymous bounty mode: User can create bounties without revealing creator identity until accepted (pseudonym display)
- Team notifications respect privacy: If team member has private profile, don't notify team of their bounty activity

### Risk 4.3: Doxxing via Proof Submissions
**Description:** User submits screenshot containing personal information (Discord username, real name, location) as proof, exposes opponent's identity.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Proof moderation: Moderators blur/remove personal information before publishing proof to bounty detail page
- Proof guidelines: "Do not include personal information in screenshots. Focus on game scoreboard only."
- Automated PII detection: Scan uploaded images for text patterns (emails, phone numbers), flag for review

### Risk 4.4: Bounty Feed Leaking Private User Data
**Description:** Open bounty feed shows all active bounties, reveals which users are online/active, when they play, what games they prefer (privacy leak).

**Severity:** 🟡 **Low**

**Mitigation:**
- Bounty visibility respects profile privacy: If creator has private profile, bounty hidden from public feed
- "Incognito bounties": Creator can mark bounty as private (not shown in feed, only direct link access)
- Followers-only visibility: Creator can limit bounty visibility to followers only

### Risk 4.5: Team Notification Privacy Breach
**Description:** User doesn't want team to know about bounty loss, but team captain receives notification anyway, exposes poor performance.

**Severity:** 🟡 **Low**

**Mitigation:**
- Team notification opt-out: User can disable "Notify my team about bounty activity" in settings
- Captain-only notifications: Only team captain notified (not entire roster), respects player autonomy
- Aggregate notifications: Team sees "A team member competed in bounty" without naming specific player

---

## 5. Operational Risks

### Risk 5.1: Expiry Task Failure (Job Dies Mid-Run)
**Description:** Celery worker crashes while processing 100 expired bounties, 50 refunded, 50 stuck in limbo with locked escrow.

**Severity:** 🔴 **High**

**Mitigation:**
- Idempotent task design: Task can rerun without duplicating refunds (idempotency keys prevent double-refund)
- Task timeout: Set 10-minute timeout, if task hangs, Celery kills and retries
- Dead letter queue: Failed bounty IDs logged to DLQ, manual admin review triggers manual refund

### Risk 5.2: Event Bus Failure (Notifications Lost)
**Description:** Event bus (RabbitMQ/Redis) goes down during bounty acceptance, `BountyAcceptedEvent` never published, creator never notified.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Event persistence: Store events in database table before publishing, retry publishing on failure
- Notification fallback: Daily digest email shows all missed notifications (bounty accepted, completed, disputed)
- In-app notification sync: Poll database for new events if real-time notifications delayed > 5 minutes

### Risk 5.3: Database Deadlock on High-Concurrency Bounty Creation
**Description:** 50 users create bounties simultaneously, all lock wallet rows for escrow debit, circular wait, database deadlock, transactions rollback.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Lock ordering: Always acquire locks in consistent order (lock bounty, then wallet, then transaction)
- Deadlock retry: Wrap bounty creation in `_with_retry()` utility (retries on deadlock exception, max 3 attempts)
- Database timeout: Set statement timeout to 10 seconds, fail fast instead of indefinite wait

### Risk 5.4: Expiry Task Clock Skew
**Description:** Server clock drifts 10 minutes ahead, expiry task expires bounties prematurely, users complain "my bounty expired early".

**Severity:** 🟡 **Low**

**Mitigation:**
- NTP synchronization: Ensure all servers sync time via NTP (drift < 1 second)
- Grace period: Add 5-minute grace period to expiry check: `expires_at + timedelta(minutes=5) <= now()`
- Timezone handling: Use `timezone.now()` (UTC) consistently, never `datetime.now()` (local time)

### Risk 5.5: Wallet Recalculation Drift
**Description:** Wallet `cached_balance` drifts from transaction ledger due to bug, `recalc_and_save()` fixes drift but causes user balance to suddenly change.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Scheduled reconciliation: Nightly job recalculates all wallet balances, compares to cached value, logs discrepancies
- Audit trail: Before updating `cached_balance`, log old vs new value: `{"old": 10000, "new": 9500, "diff": -500}`
- User notification: If balance changes > 1000 DC during reconciliation, send email explaining correction

### Risk 5.6: Dispute Moderator Burnout
**Description:** Only 2 active moderators, dispute queue grows to 500+, moderators quit due to overwork, dispute system collapses.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Moderator recruitment: Promote high-reputation users (2000+) to community moderators with limited privileges
- Dispute batching: Moderators review 10 disputes at once (batch UI), faster processing
- Automated pre-filtering: Low-stake disputes (< 500 DC) auto-resolve via algorithm (OCR screenshot validation)

### Risk 5.7: Idempotency Key Cleanup
**Description:** Idempotency keys stored forever, database table grows to millions of rows, query performance degrades.

**Severity:** 🟡 **Low**

**Mitigation:**
- TTL on idempotency keys: Delete keys older than 90 days (bounties resolved long ago)
- Indexed idempotency_key column: Ensure fast lookup even with millions of rows
- Separate table: Store idempotency keys in dedicated table, not in main transaction table (easier cleanup)

---

## 6. Risk Prioritization Matrix

**Critical (Address Before Launch):**
- 🔴 Risk 1.1: Double Refund on Expiry
- 🔴 Risk 5.1: Expiry Task Failure

**High Priority (Address in MVP):**
- 🟠 Risk 1.2: Race Condition on Acceptance
- 🟠 Risk 1.3: Pending Balance Desync
- 🟠 Risk 1.5: Platform Fee Calculation Error
- 🟠 Risk 1.6: Insufficient Balance Check Bypass
- 🟠 Risk 2.1: Low-Stake Spam Flooding
- 🟠 Risk 2.2: Bounty Hoarding
- 🟠 Risk 3.1: False Dispute Spam
- 🟠 Risk 3.2: Moderator Queue Overload
- 🟠 Risk 4.1: Targeted Harassment
- 🟠 Risk 5.3: Database Deadlock

**Medium Priority (Address in Phase 2):**
- 🟠 Risk 1.7: Orphaned Escrow on Delete
- 🟠 Risk 2.3: Sybil Attack
- 🟠 Risk 3.3: Moderator Bias
- 🟠 Risk 3.4: Evidence Tampering
- 🟠 Risk 4.3: Doxxing via Proof
- 🟠 Risk 5.2: Event Bus Failure
- 🟠 Risk 5.5: Wallet Recalculation Drift
- 🟠 Risk 5.6: Moderator Burnout

**Low Priority (Monitor and Address if Occurs):**
- 🟡 Risk 1.4: Idempotency Key Collision
- 🟡 Risk 2.4: Reputation Farming
- 🟡 Risk 2.5: Blocked User List Abuse
- 🟡 Risk 3.5: Dispute Window Exploitation
- 🟡 Risk 4.2: Profile Stalking
- 🟡 Risk 4.4: Bounty Feed Data Leak
- 🟡 Risk 4.5: Team Notification Privacy
- 🟡 Risk 5.4: Expiry Task Clock Skew
- 🟡 Risk 5.7: Idempotency Key Cleanup

---

## 7. Security Checklist (Pre-Launch)

**Escrow Security:**
- [ ] All escrow operations wrapped in `@transaction.atomic`
- [ ] All wallet locks use `select_for_update()`
- [ ] All refund transactions have idempotency keys
- [ ] Balance validation has database check constraint
- [ ] Platform fee calculation has unit tests

**Anti-Abuse:**
- [ ] Rate limiting enforced on bounty creation (10/day)
- [ ] Cooldown period enforced (1 hour between creations)
- [ ] Reputation requirement enforced (min 50 to create)
- [ ] Active bounty limit enforced (max 3 accepted concurrently)
- [ ] Block list size limited (max 50 blocked users)

**Dispute Security:**
- [ ] Dispute fee implemented (10% of stake)
- [ ] Reputation penalty for false disputes (-50 rep after 3 losses)
- [ ] Moderator audit log enabled
- [ ] Auto-resolution after 72 hours implemented
- [ ] Appeal system planned (Phase 2)

**Privacy:**
- [ ] Bounty visibility respects profile privacy settings
- [ ] Team notifications have opt-out setting
- [ ] Proof submissions screened for PII
- [ ] Block prevents targeted bounties

**Operational Resilience:**
- [ ] Expiry task has idempotent design
- [ ] Event bus failures have fallback notifications
- [ ] Database deadlocks have retry logic
- [ ] NTP synchronization verified on all servers
- [ ] Nightly wallet reconciliation job scheduled

---

**RISK REVIEW COMPLETE**

**Document Status:** ✅ Ready for Security Team Review  
**Next Steps:**
1. Schedule security review meeting with engineering team
2. Prioritize critical risks for immediate mitigation
3. Create Jira tickets for each medium/high priority risk
4. Design penetration testing scenarios for escrow vulnerabilities
5. Plan disaster recovery procedures for expiry task failures
6. Review with legal team: Terms of Service updates for dispute handling

---

**END OF BOUNTY RISK REVIEW**
