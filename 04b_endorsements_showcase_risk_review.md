# Endorsements & Showcase Risk Review
**Date:** December 31, 2025  
**Reviewer:** Security & Abuse-Prevention Engineer  
**Type:** Risk Assessment & Mitigation Strategy  
**Scope:** Post-Match Skill Endorsements + Achievement-Based Trophy Showcase

---

## SECTION A — Endorsement System Risks

### Risk A.1: Endorsement Farming via Collusion
**Description:** Two players coordinate across multiple matches to always endorse each other, artificially inflating skill counts to appear highly skilled to scouts and team captains.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Behavioral detection: Flag pairs who endorse each other in 80%+ of shared matches (statistical anomaly)
- Admin review dashboard: "User X and User Y endorsed each other 15 times out of 18 shared matches"
- Reputation weight: Consider endorsement source diversity (50 endorsements from 50 unique players > 50 from 10 repeated players)
- Time distribution check: Endorsements clustered in short time periods (10 matches in 2 days) trigger review
- Anonymous attribution prevents explicit quid pro quo: Endorser identity hidden, reduces "you scratch my back" pressure

### Risk A.2: Team Captain / Admin Abuse (Match Manipulation)
**Description:** Team captain creates fake tournament matches with handpicked teammates, marks matches as COMPLETED without actual gameplay, generates endorsement opportunities to boost specific players' profiles.

**Severity:** 🔴 **High**

**Mitigation:**
- Match verification requirement: Matches must have completed state transition logged by tournament system (not manually set by admin)
- Match duration validation: Matches shorter than 10 minutes flagged as suspicious (no real gameplay occurred)
- Proof of gameplay: Require match result submission with screenshot/API verification before endorsements unlock
- Admin audit log: Track who marked match as COMPLETED, flag admin accounts with 10+ matches completed manually
- Tournament registration limits: Only matches in official tournaments (with public brackets) generate endorsement opportunities, exclude "practice matches" category

### Risk A.3: Duplicate Endorsements via Race Condition
**Description:** User submits endorsement request twice simultaneously (double-click, network retry), database inserts two endorsement records before unique constraint check completes, duplicate endorsements awarded.

**Severity:** 🟡 **Low**

**Mitigation:**
- Database unique constraint: `unique_together = ['match_id', 'endorser']` prevents duplicate inserts (constraint violation rollback)
- Service-level check: Query existing endorsement before insert: `if SkillEndorsement.objects.filter(match_id=X, endorser=Y).exists(): return existing`
- Idempotent API design: POST request with idempotency key `endorsement:{match_id}:{endorser_id}` returns existing record if duplicate request
- Frontend rate limiting: Disable submit button after first click, prevent double-submission UI pattern

### Risk A.4: Match Replay Abuse (Re-endorsing Same Match)
**Description:** Match record is duplicated or replayed (tournament format error), system creates multiple EndorsementOpportunity records for same gameplay instance, user endorses same teammates multiple times for identical match.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Match deduplication: Check for duplicate match records before creating endorsement opportunities (same participants, same timestamp, same tournament)
- Unique match identifier: Use match UUID (not sequential ID) to prevent accidental duplication
- Tournament system validation: Matches created via API must have unique constraint on `(tournament_id, round, team_a_id, team_b_id)` (prevents replay)
- Endorsement opportunity window: Only one opportunity per match per user (even if match record duplicated)
- Admin review: Flag matches with 10+ endorsement opportunities generated (should be max 10 participants per team match)

### Risk A.5: Match-Participant Verification Bypass
**Description:** User was not actually in match (spectator, sub who didn't play), but exploits verification logic bug to endorse participants anyway, gains endorsement privilege without earning it.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Strict participant list: Only users in `Match.participant1_id`, `Match.participant2_id` (1v1), or active TeamMembership roster at match time qualify
- Roster snapshot: Store team roster at match start (not current roster), prevents retroactive membership claims
- Service-level validation: `if endorser not in get_match_participants(match): raise PermissionDenied`
- Query verification: `TeamMembership.objects.filter(team_id=match.team_a_id, user=endorser, joined_at__lte=match.started_at, left_at__isnull_or_gte=match.started_at).exists()`
- Endorsement creation transaction: Atomic check-then-insert with `SELECT FOR UPDATE` on match (prevents TOCTOU race conditions)

### Risk A.6: Self-Endorsement via Account Switching
**Description:** User creates alt account, joins match as teammate via second account, endorses primary account from alt, circumvents "cannot endorse yourself" rule.

**Severity:** 🟡 **Low**

**Mitigation:**
- IP-based detection: Track IPs used by endorser and receiver, flag if same IP used for both accounts within 24 hours
- Device fingerprinting: Browser fingerprint matching across accounts (same device, high collusion probability)
- Behavioral patterns: Flag accounts that only endorse one specific user (100% endorsement rate to single target)
- Email verification: Require verified email for endorsement privilege (one endorsement per email domain family)
- Reputation requirement: Minimum 50 reputation to give endorsements (prevents throwaway alt accounts)

### Risk A.7: Expiry Window Bypass (Retroactive Endorsements)
**Description:** User manipulates system clock or database timestamps to extend 24-hour endorsement window, endorses matches from weeks ago to coordinate large-scale farming operation.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Server-side timestamp validation: Use `timezone.now()` (server time) for expiry checks, ignore client-provided timestamps
- Database constraint: `CHECK (created_at <= expires_at)` on EndorsementOpportunity (cannot backdate expiry)
- Endorsement creation validates: `if now() > match.completed_at + timedelta(hours=24): raise ValidationError("Window expired")`
- Immutable match completion time: `Match.completed_at` set by system on state transition (not user-editable)
- Audit log: Log endorsement timestamp and match completion time delta, flag endorsements created 23+ hours after match (suspicious timing)

### Risk A.8: Opponent Endorsement via Teammate Impersonation
**Description:** Bug in teammate verification allows user to endorse opponent by exploiting team ID confusion (e.g., both teams have same captain, system can't distinguish sides).

**Severity:** 🟠 **Medium**

**Mitigation:**
- Explicit team side validation: Store `endorser_team_side` (A or B) on endorsement record, validate receiver on same side
- Query logic: `endorser in match.team_a_members AND receiver in match.team_a_members` (both on same side)
- Service method: `get_user_team_in_match(user, match)` returns 'TEAM_A' or 'TEAM_B', not just team_id
- Test coverage: Unit test for 1v1 matches (cannot endorse opponent), team matches (cannot endorse opposing team member)
- Database trigger: Validate endorser and receiver are on same team before insert (fallback safety check)

### Risk A.9: Data Integrity — Orphaned Endorsements After Match Deletion
**Description:** Admin deletes match record (via admin panel or cleanup script), endorsements remain with orphaned match_id foreign key, profile shows inflated counts from non-existent matches.

**Severity:** 🟡 **Low**

**Mitigation:**
- Soft delete matches: Set `Match.deleted_at` timestamp instead of hard delete, endorsements remain queryable
- Cascade delete: Set `on_delete=models.CASCADE` on SkillEndorsement.match_id (deleting match deletes endorsements)
- Admin warning: "Deleting this match will remove X endorsements. Continue?"
- Orphan detection: Scheduled job queries endorsements with NULL or non-existent match_id, alerts admin
- Aggregation query excludes orphans: `SkillEndorsement.objects.filter(receiver=user, match__isnull=False).count()`

### Risk A.10: Uniqueness Constraint Violation (Skill + Match + Endorser)
**Description:** Database constraint set to `unique_together=['match_id', 'endorser']` allows user to endorse same teammate multiple times for different skills in one match, inflates counts.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Design decision: Enforce one endorsement per match per endorser (user picks ONE skill for ONE teammate)
- Constraint: `unique_together = ['match_id', 'endorser']` (prevents multiple skill awards per match)
- Frontend UX: Radio button selection (not checkboxes), user cannot select multiple skills
- Service validation: `if SkillEndorsement.objects.filter(match_id=X, endorser=Y).exists(): raise AlreadyEndorsed`
- Error message: "You've already recognized a teammate from this match. Endorsement cannot be changed."

### Risk A.11: Toxicity via Skill Mislabeling (Sarcastic Endorsements)
**Description:** User endorses terrible player as "Aim" sarcastically, endorsement shows on profile positively but was meant as insult, creates harassment vector.

**Severity:** 🟡 **Low**

**Mitigation:**
- No negative skills: System only has positive skill categories (no "Worst Aim" or "Toxic Player" tags)
- Anonymous endorsements: Receiver doesn't know who endorsed them (reduces targeted sarcasm)
- Skill aggregation: Single sarcastic endorsement lost in aggregate (89 genuine Aim endorsements drown out 1 sarcastic)
- Reporting system: User can report suspicious endorsements (e.g., "I never played with this person"), admin reviews
- Behavioral detection: Flag users whose endorsements are frequently reported, revoke endorsement privilege

---

## SECTION B — Trophy Showcase Risks

### Risk B.1: Unlock Spoofing (Client-Side Manipulation)
**Description:** User modifies frontend JavaScript to mark cosmetics as "unlocked" without earning badge, equips frames/banners they didn't legitimately earn, profile displays fake prestige.

**Severity:** 🔴 **High**

**Mitigation:**
- Server-side validation: All equip requests validate unlock status on backend: `if not UnlockedCosmetic.objects.filter(user=X, cosmetic_id=Y).exists(): raise PermissionDenied`
- Database-driven rendering: Profile template queries UserProfile.equipped_frame_id, fetches frame asset from database (not client-provided slug)
- No client-side unlock state: Frontend receives list of unlocked cosmetics from server, cannot modify list locally
- API endpoint protection: `/api/showcase/equip/{cosmetic_id}` checks unlock record before updating UserProfile
- Admin audit: Track equip requests that fail validation, flag users attempting to equip locked cosmetics (potential exploit attempt)

### Risk B.2: Incorrect Unlock Condition Logic (Auto-Grant Bug)
**Description:** Bug in badge award logic or UnlockedCosmetic creation triggers cosmetic unlock without user meeting requirement (e.g., unlock "100 Wins" frame after 10 wins due to typo).

**Severity:** 🟠 **Medium**

**Mitigation:**
- Unit tests for unlock triggers: Test `badge.save()` with `unlocks_frame_id` set, assert UnlockedCosmetic created only when badge earned
- Unlock requirement validation: Store unlock condition in ProfileFrame.unlock_requirement JSON: `{"badge_id": 123, "min_count": 100}`
- Double-check in unlock service: Before creating UnlockedCosmetic, re-validate user meets condition (not just badge existence)
- Admin review: Flag cosmetics unlocked within 1 hour of account creation (suspicious, likely bug or exploit)
- Rollback procedure: If incorrect unlock detected, soft-delete UnlockedCosmetic record, unequip frame, notify user of correction

### Risk B.3: Unlock Duplication (Same Cosmetic Multiple Times)
**Description:** User earns badge that unlocks frame, badge signal fires twice (retry logic bug), creates two UnlockedCosmetic records for same user-cosmetic pair.

**Severity:** 🟡 **Low**

**Mitigation:**
- Database unique constraint: `unique_together = ['user', 'cosmetic_type', 'cosmetic_id']` on UnlockedCosmetic model
- Idempotent unlock service: `UnlockedCosmetic.objects.get_or_create(user=X, cosmetic_id=Y)` returns existing if duplicate
- Signal idempotency: Badge award signal checks if cosmetic already unlocked before creating record
- Deduplication query: Scheduled job finds duplicate unlocks, deletes duplicates keeping earliest `unlocked_at` timestamp

### Risk B.4: Privacy — Forced Cosmetic Display Reveals Private Info
**Description:** User equips frame that reveals private information (e.g., "2024 Cancer Survivor Tournament Frame"), doesn't want public profile showing health status, no way to hide without unequipping.

**Severity:** 🟡 **Low**

**Mitigation:**
- Frame naming: Avoid frames tied to sensitive personal attributes (health, religion, political affiliation)
- Generic tournament naming: "Season 4 Champion" not "Pride Month Winner" or "Veterans Tournament Champion"
- Privacy setting: "Hide showcase customization" option (profile uses default frame/banner regardless of equipped state)
- Equip state is private: Only user sees what they have equipped in settings, public profile shows or hides based on privacy toggle
- Unlock history hidden: Visitors don't see list of all unlocked cosmetics (only equipped items visible)

### Risk B.5: Performance — Aggregation Query on Large Cosmetic Collections
**Description:** User unlocked 500+ cosmetics over years, profile loads slowly due to query fetching all unlocked items, sorting by rarity, rendering showcase grid.

**Severity:** 🟡 **Low**

**Mitigation:**
- Pagination: Showcase settings page shows 20 cosmetics per page (lazy load additional pages)
- Caching: Cache unlocked cosmetics list: `cache.get(f'unlocked_cosmetics:{user_id}')` with 1-hour TTL
- Database indexing: Index UnlockedCosmetic table on `user_id` and `cosmetic_type` for fast filtering
- Defer asset URL loading: Query only cosmetic IDs and names initially, load asset URLs on-demand when user hovers
- Public profile optimization: Only query equipped cosmetics (3-5 items max), not entire unlocked collection

### Risk B.6: Asset Injection (Malicious Frame Upload)
**Description:** Admin or attacker uploads malicious frame asset (e.g., PNG with embedded JavaScript, SVG with XSS payload), users who equip frame execute malicious code.

**Severity:** 🔴 **High**

**Mitigation:**
- File type whitelist: Only allow PNG and JPG uploads (no SVG, no GIF with executable frames, no HTML disguised as image)
- Content-Type validation: Verify uploaded file MIME type matches extension (not just check extension)
- Image processing: Re-encode uploaded images using Pillow/ImageMagick to strip metadata and potential payloads
- CSP headers: Set `Content-Security-Policy: img-src 'self' https://cdn.deltacrown.gg` (only load images from trusted domains)
- Sandboxed storage: Store frames in S3/CDN with restrictive CORS, serve with `Content-Disposition: inline` (not `attachment`)

### Risk B.7: Equipped State Desync (Frame Shows But Not Unlocked)
**Description:** Bug in equip logic allows UserProfile.equipped_frame_id to reference frame that user doesn't own in UnlockedCosmetic table, profile displays frame they didn't earn.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Foreign key constraint: UserProfile.equipped_frame_id references ProfileFrame with `on_delete=models.SET_NULL` (prevents orphan references)
- Validation on equip: Before setting equipped_frame_id, verify UnlockedCosmetic record exists: `if not user.unlocked_cosmetics.filter(cosmetic_id=X).exists(): raise PermissionDenied`
- Scheduled reconciliation: Nightly job queries users with equipped frames they don't own, resets to default frame
- Profile rendering fallback: If equipped_frame_id references non-existent or locked frame, render default frame (don't crash)
- Admin dashboard: "Users with mismatched equipped state" report for manual investigation

### Risk B.8: Rarity Inflation (Too Many Legendary Items)
**Description:** Too many badges unlock Legendary cosmetics, rarity tiers lose meaning, "Legendary" frame is common, prestige value collapses.

**Severity:** 🟡 **Low**

**Mitigation:**
- Strict unlock criteria: Legendary cosmetics require top 1% achievements (e.g., "Win 3 Season Championships", "Reach #1 Global Rank")
- Limited availability: Only 5-10 Legendary cosmetics total in system (scarce by design)
- Unlock rate monitoring: Track percentage of users who own each cosmetic, flag if Legendary ownership exceeds 5%
- Recalibration: If Legendary frame becomes too common, consider adding "Mythic" tier above Legendary for ultra-rare items
- Badge rarity review: Audit badge unlock requirements annually, ensure Legendary badges remain difficult

### Risk B.9: Showcase Completion Arms Race (FOMO Pressure)
**Description:** Completion percentage stat (80% of cosmetics unlocked) creates FOMO pressure, users grind unhealthily to "complete collection", toxic behavior to unlock all items.

**Severity:** 🟡 **Low**

**Mitigation:**
- Remove completion percentage: Don't show "80% complete" stat (reduces collection anxiety)
- Focus on equipped items: Showcase page emphasizes currently equipped cosmetics (what you choose to display), not total unlocked count
- Messaging: "Showcase your achievements, not collect everything" UX copy
- No time-limited cosmetics: Avoid "Season 1 exclusive" frames that lock out future players (perpetual FOMO)
- Alternative metric: Show "Rarest item owned" instead of completion percentage (quality over quantity)

### Risk B.10: Badge-Cosmetic Link Deletion Orphans Unlocks
**Description:** Admin deletes ProfileFrame record or changes Badge.unlocks_frame_id, users who previously unlocked via that badge now have orphaned UnlockedCosmetic records, profile shows cosmetic that shouldn't exist.

**Severity:** 🟡 **Low**

**Mitigation:**
- Soft delete cosmetics: Set ProfileFrame.deleted_at instead of hard delete, unlocks remain valid
- Cascade soft-delete: When frame deleted, mark all UnlockedCosmetic records for that frame as `cosmetic_deleted_at` (preserves history)
- Admin warning: "X users have unlocked this frame. Deleting will affect their showcases. Continue?"
- Migration script: If badge unlock mapping changes, backfill/remove UnlockedCosmetic records to match new logic
- Orphan cleanup: Scheduled job detects UnlockedCosmetic with NULL cosmetic_id or deleted cosmetic, removes record

### Risk B.11: Pinned Badge Limit Bypass (Equipping 10 Badges)
**Description:** User modifies API request to set `pinned_badge_4_id`, `pinned_badge_5_id` beyond 3-badge limit, profile displays more badges than intended, cluttered UI.

**Severity:** 🟡 **Low**

**Mitigation:**
- Schema enforcement: UserProfile model only has 3 pinned badge fields (pinned_badge_1/2/3_id), no field for 4th badge
- API validation: Equip endpoint rejects requests with more than 3 badge IDs: `if len(badge_ids) > 3: raise ValidationError("Max 3 badges")`
- Frontend validation: Showcase settings UI only allows selecting 3 badges (disabled after 3 selected)
- Database constraint: If using JSON array for pinned badges, add CHECK constraint: `jsonb_array_length(pinned_badges) <= 3`

### Risk B.12: Cosmetic Asset CDN Failure (All Frames Break)
**Description:** CDN hosting frame/banner assets goes down, all profiles show broken images, showcase system unusable until CDN restored.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Multi-CDN strategy: Host assets on primary CDN (Cloudflare) and fallback CDN (AWS CloudFront), template tries fallback if primary fails
- Local fallback: Keep default frame/banner in static files (served by Django), fallback if CDN unreachable
- Graceful degradation: If frame asset fails to load, show placeholder silhouette or user's profile photo without frame
- Asset URL validation: Store full CDN URL in database, not relative path (easier to switch CDNs)
- Monitoring: Alert if frame asset 404 rate exceeds 5%, indicates CDN issue or broken asset URL

---

## 3. Risk Prioritization Matrix

**Critical (Address Before Launch):**
- 🔴 Risk A.2: Team Captain / Admin Abuse (fake matches for endorsements)
- 🔴 Risk B.1: Unlock Spoofing (client-side manipulation)
- 🔴 Risk B.6: Asset Injection (malicious frame upload)

**High Priority (Address in MVP):**
- 🟠 Risk A.1: Endorsement Farming via Collusion
- 🟠 Risk A.4: Match Replay Abuse
- 🟠 Risk A.5: Match-Participant Verification Bypass
- 🟠 Risk A.7: Expiry Window Bypass
- 🟠 Risk A.8: Opponent Endorsement via Bug
- 🟠 Risk A.10: Uniqueness Constraint Violation
- 🟠 Risk B.2: Incorrect Unlock Condition Logic
- 🟠 Risk B.7: Equipped State Desync
- 🟠 Risk B.12: Cosmetic Asset CDN Failure

**Medium Priority (Address in Phase 2):**
- 🟡 Risk A.3: Duplicate Endorsements via Race Condition
- 🟡 Risk A.6: Self-Endorsement via Alt Accounts
- 🟡 Risk A.9: Orphaned Endorsements After Match Deletion
- 🟡 Risk A.11: Toxicity via Sarcastic Endorsements
- 🟡 Risk B.3: Unlock Duplication
- 🟡 Risk B.4: Privacy Concerns with Cosmetic Display
- 🟡 Risk B.5: Performance on Large Collections
- 🟡 Risk B.8: Rarity Inflation
- 🟡 Risk B.9: Showcase Completion FOMO
- 🟡 Risk B.10: Badge-Cosmetic Link Deletion
- 🟡 Risk B.11: Pinned Badge Limit Bypass

---

## 4. Security Checklist (Pre-Launch)

**Endorsement Security:**
- [ ] Match verification requires actual gameplay proof (duration, result submission)
- [ ] Database unique constraint: `unique_together = ['match_id', 'endorser']` enforced
- [ ] Participant verification via roster snapshot at match start time
- [ ] 24-hour expiry window validated server-side with `timezone.now()`
- [ ] Anonymous attribution implemented (endorser_id not exposed in API)
- [ ] Behavioral detection for collusion patterns (same pair endorsing repeatedly)
- [ ] Self-endorsement prevented with DB check constraint: `CHECK (endorser_id != receiver_id)`

**Showcase Security:**
- [ ] Server-side unlock validation on all equip requests
- [ ] Database unique constraint: `unique_together = ['user', 'cosmetic_type', 'cosmetic_id']` on UnlockedCosmetic
- [ ] Asset upload restricted to PNG/JPG, no SVG or executable formats
- [ ] Image re-encoding to strip metadata and potential payloads
- [ ] CSP headers set to restrict image sources to trusted CDN
- [ ] Equipped state validation ensures user owns cosmetic before equipping
- [ ] Multi-CDN failover for asset delivery

**Anti-Abuse:**
- [ ] Rate limiting on endorsement creation (max 50 endorsements per day per user)
- [ ] Reputation requirement for endorsement privilege (min 50 reputation)
- [ ] Admin audit log for manual match completion actions
- [ ] Orphan endorsement cleanup job scheduled (weekly)
- [ ] Collusion detection report generated (monthly, flagged pairs reviewed)

**Privacy:**
- [ ] Showcase privacy toggle: "Hide cosmetic customization from public profile"
- [ ] Unlock history only visible to user (not public)
- [ ] Badge pinning respects earned badge list (cannot pin unearned badges)
- [ ] Profile rendering falls back to default frame if equipped frame unavailable

**Operational Resilience:**
- [ ] CDN failover configured (primary + fallback)
- [ ] Asset 404 monitoring and alerting enabled
- [ ] Endorsement aggregation cached (1-hour TTL, invalidated on new endorsement)
- [ ] Nightly reconciliation job for equipped state vs unlocked cosmetics
- [ ] Database indexes on frequently queried fields (user_id, match_id, cosmetic_id)

---

**RISK REVIEW COMPLETE**

**Document Status:** ✅ Ready for Security Team Review  
**Next Steps:**
1. Schedule security review meeting with engineering and product teams
2. Implement critical mitigations for match verification and unlock spoofing
3. Design behavioral detection algorithm for endorsement collusion
4. Conduct penetration testing on showcase equip API
5. Review cosmetic asset upload workflow with DevSecOps
6. Create admin dashboard for endorsement fraud monitoring

---

**END OF ENDORSEMENTS & SHOWCASE RISK REVIEW**
