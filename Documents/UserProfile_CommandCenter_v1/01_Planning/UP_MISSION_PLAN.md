# USER PROFILE MODERNIZATION MISSION PLAN

**Platform:** DeltaCrown Esports Tournament Platform  
**Project:** User Profile System Modernization  
**Date:** December 22, 2025  
**Status:** READY FOR EXECUTION

---

## MISSION OVERVIEW

This document organizes the 30-item backlog into 6 implementation missions. Each mission is a complete, deployable unit that can be assigned to GitHub Copilot for implementation.

**Mission Strategy:**
- Each mission is self-contained (can be implemented independently after dependencies)
- Each mission includes tests, migrations, and documentation
- Each mission passes quality gates before next begins
- Missions follow dependency order (M0 → M1 → M2, then M3/M4/M5 parallel)

**Total Missions:** 6  
**Estimated Duration:** 6 weeks  
**Team Size:** 2-3 engineers + 1 QA

---

## MISSION UP-M0: REPOSITORY INVENTORY & SAFETY GATES

**Duration:** 2 days  
**Priority:** P0 (BLOCKING)  
**Dependencies:** None  
**Backlog Items:** UP-001, UP-002

### Scope

**In Scope:**
- Grep entire codebase for profile access patterns (`request.user.profile`, `.profile`, `User.objects.select_related('profile')`)
- Document all 47+ locations assuming profile exists without checks
- Categorize by risk level (direct access vs safe access)
- Create `get_profile_or_create(user)` utility function
- Create `@ensure_profile_exists` decorator for views
- Add atomic transaction wrapper with retry logic (3 attempts)
- Write comprehensive tests (100% coverage for safety utilities)
- Create inventory report (file paths, line numbers, risk assessment)

**Out of Scope:**
- Fixing the 47+ locations (done in later missions)
- Adding public_id field (Mission M1)
- Modifying any existing profile access code
- Database migrations

### Files Likely Touched

```
apps/user_profile/
  utils.py (NEW - safety utilities)
  decorators.py (NEW - @ensure_profile_exists)
  tests/test_safety.py (NEW)

Documents/UserProfile_v1/
  03_INVENTORY/PROFILE_ACCESS_PATTERNS.md (NEW - inventory report)
```

### Acceptance Criteria

- [ ] Complete inventory of profile access patterns (47+ locations documented)
- [ ] `get_profile_or_create()` function implemented with atomic transaction
- [ ] `@ensure_profile_exists` decorator implemented and documented
- [ ] Retry logic works (3 attempts with exponential backoff)
- [ ] Test coverage 100% for safety utilities (20+ test cases)
- [ ] Zero profile creation failures in 1000+ test runs
- [ ] Inventory report peer-reviewed and approved
- [ ] Usage examples documented in README

### Required Documentation Updates

- **Status Tracker:** Mark UP-001, UP-002 complete
- **Decision Log:** No new ADRs
- **New Document:** Profile Access Patterns Inventory

---

## MISSION UP-M1: PUBLIC ID + PROFILE PROVISIONING + PRIVACY DEFAULTS

**Duration:** 5 days  
**Priority:** P0 (BLOCKING)  
**Dependencies:** UP-M0  
**Backlog Items:** UP-003, UP-004, UP-005, UP-006, UP-007, UP-008, UP-009, UP-010

### Scope

**In Scope:**
- Add `public_id` field to UserProfile model (CharField, unique, indexed, max_length=15)
- Create PublicIDCounter model (year, counter, unique constraint)
- Implement PublicIDGenerator service (sequential allocation, DC-YY-NNNNNN format)
- Refactor `create_user_profile` signal to generate public_id atomically
- Create data migration to backfill existing users with public_ids
- Add `get_by_public_id()` QuerySet method
- Create PrivacySettings model (OneToOne with UserProfile)
- Implement PrivacyAwareProfileSerializer base class
- Add privacy template tags (`{% privacy_filter %}`)
- Update 12 API endpoints to use privacy-aware serializers
- Update all profile templates to use privacy tags
- Write comprehensive test suite (150+ tests)

**Out of Scope:**
- URL routing changes (keep for separate PR to minimize conflicts)
- OAuth flow changes (Mission M2)
- Profile view logic changes (only privacy enforcement)

### Files Likely Touched

```
apps/user_profile/
  models.py (add public_id, PrivacySettings)
  services/public_id_generator.py (NEW)
  services/privacy_service.py (NEW)
  signals.py (refactor profile creation)
  serializers.py (add PrivacyAwareProfileSerializer)
  querysets.py (add get_by_public_id)
  templatetags/privacy_tags.py (NEW)
  migrations/000X_add_public_id.py (NEW)
  migrations/000Y_add_privacy_settings.py (NEW)
  migrations/000Z_backfill_public_id.py (NEW - data migration)
  tests/ (add 150+ tests)

apps/api/
  v1/profile/serializers.py (update to use privacy base)

templates/user_profile/
  profile_detail.html (add privacy tags)
  profile_edit.html (add privacy settings form)
```

### Acceptance Criteria

- [ ] `public_id` field added with regex validation (^DC-\d{2}-\d{6}$)
- [ ] PublicIDGenerator generates sequential IDs (DC-25-000001, DC-25-000002, etc.)
- [ ] Zero duplicate public_ids in 10,000 concurrent generation tests
- [ ] Year rollover logic works (Dec 31 → Jan 1 resets counter)
- [ ] Profile creation signal 100% success rate (2000+ OAuth flows)
- [ ] All existing users have valid public_id after migration
- [ ] PrivacySettings created for all profiles (via signal)
- [ ] Privacy enforcement works in templates (owner sees all, public sees filtered)
- [ ] Privacy enforcement works in APIs (PII fields removed from response)
- [ ] Test coverage ≥90% for new code (150+ tests passing)

### Required Documentation Updates

- **Status Tracker:** Mark UP-003 through UP-010 complete, update progress metrics
- **Decision Log:** No new ADRs (already documented)
- **Backlog:** Mark 8 items complete

---

## MISSION UP-M2: GOOGLE OAUTH + PROFILE PROVISIONING GUARANTEE

**Duration:** 3 days  
**Priority:** P0 (SECURITY)  
**Dependencies:** UP-M1  
**Backlog Items:** UP-011, UP-012, UP-013

### Scope

**In Scope:**
- Audit all OAuth callback handlers (Google, future: Discord, Steam)
- Consolidate profile creation into single `ensure_profile_from_oauth()` function
- Add atomic transaction wrapper (User + UserProfile + PrivacySettings created together)
- Implement retry logic (3 attempts with exponential backoff)
- Handle edge cases (missing email, duplicate email, connection timeout)
- Add fallback: create profile with minimal data, prompt user completion
- Add comprehensive error logging (OAuth failures audited)
- Write 50+ integration test scenarios (success, failures, edge cases)
- Load test: 100 concurrent OAuth flows

**Out of Scope:**
- Adding new OAuth providers (Discord, Steam) - future work
- Profile completion UI (onboarding wizard) - separate ticket
- Email verification flow changes

### Files Likely Touched

```
apps/accounts/
  views/oauth.py (refactor callback handlers)
  services/oauth_service.py (NEW - ensure_profile_from_oauth)
  tests/test_oauth.py (add 50+ integration tests)

apps/user_profile/
  signals.py (ensure compatibility with OAuth flow)
  tests/test_oauth_integration.py (NEW)
```

### Acceptance Criteria

- [ ] Single `ensure_profile_from_oauth()` function (no duplicate logic)
- [ ] Atomic transaction guarantees (user + profile + privacy created together)
- [ ] Retry logic works (3 attempts on transient failures)
- [ ] Edge cases handled gracefully (missing email → prompt, duplicate → merge)
- [ ] OAuth completion rate ≥99.9% (down from 98.7%)
- [ ] Zero profile creation failures in 100 concurrent OAuth tests
- [ ] User sees clear error message on failure (not 500 page)
- [ ] Test coverage ≥95% for OAuth code (50+ scenarios)
- [ ] Load test passes (100 concurrent flows, all successful)

### Required Documentation Updates

- **Status Tracker:** Mark UP-011, UP-012, UP-013 complete
- **Decision Log:** Add ADR if new OAuth pattern decided
- **Backlog:** Mark 3 items complete

---

## MISSION UP-M3: ECONOMY SYNC + RECONCILIATION

**Duration:** 5 days  
**Priority:** P1 (HIGH)  
**Dependencies:** UP-M1  
**Backlog Items:** UP-014, UP-015, UP-016, UP-017, UP-018

### Scope

**In Scope:**
- Create `sync_wallet_balance` signal (transaction → wallet)
- Create `sync_profile_balance` signal (wallet → profile)
- Use F() expression for atomic balance updates (prevent race conditions)
- Add `skip_signal` flag for bulk operations
- Create `reconcile_balances` management command
- Implement drift detection (wallet vs ledger, profile vs wallet)
- Implement auto-correction (profile balance recalculated from wallet)
- Create transaction history API endpoint (`/api/profile/<public_id>/transactions/`)
- Create transaction history UI (table with search/filter)
- Add pagination (100 transactions per page)
- Write 80+ tests (unit, integration, load)
- Load test: 1000 concurrent transactions

**Out of Scope:**
- Transaction creation UI (admin-only for now)
- Prize distribution automation (tournaments integration - Mission M4)
- Wallet PIN/security features

### Files Likely Touched

```
apps/economy/
  signals.py (add sync_wallet_balance)
  models.py (add skip_signal support)
  tests/test_sync.py (NEW)

apps/user_profile/
  signals.py (add sync_profile_balance)
  tests/test_economy_sync.py (NEW)

apps/core/management/commands/
  reconcile_balances.py (NEW)

apps/api/v1/profile/
  views.py (add transaction history endpoint)
  serializers.py (add TransactionHistorySerializer)

templates/user_profile/
  transaction_history.html (NEW)

static/js/
  transaction_filter.js (NEW - search/filter logic)
```

### Acceptance Criteria

- [ ] Transaction creation updates wallet balance within 100ms (signal fires)
- [ ] Wallet update syncs to profile balance (cached aggregate)
- [ ] Zero balance drift in 1000 transaction test suite
- [ ] Atomic updates prevent race conditions (concurrent transactions tested)
- [ ] Reconciliation command completes in <5 minutes for 10K users
- [ ] Drift detected and logged (even 1 DC difference)
- [ ] Auto-correction rate ≥95% (remaining 5% alert for manual review)
- [ ] Transaction history API returns privacy-filtered data
- [ ] Transaction history UI responsive and accessible (WCAG 2.1 AA)
- [ ] Load test passes (1000 concurrent transactions, zero drift)

### Required Documentation Updates

- **Status Tracker:** Mark UP-014 through UP-018 complete, update economy metrics
- **Decision Log:** No new ADRs (ledger-first already documented)
- **Backlog:** Mark 5 items complete

---

## MISSION UP-M4: TOURNAMENT PARTICIPATION + STATS + HISTORY

**Duration:** 6 days  
**Priority:** P1 (HIGH)  
**Dependencies:** UP-M1  
**Backlog Items:** UP-019, UP-020, UP-021, UP-022, UP-023, UP-024

### Scope

**In Scope:**
- Create TournamentParticipation model (user, tournament, placement, stats, prize)
- Add placement_tier choices (winner, runner_up, top4, top8, top16, participant)
- Create participation creation signal (tournament status='completed' → create records)
- Create stats update signal (participation created → profile stats increment)
- Add stats fields to UserProfile (tournaments_played, tournaments_won, total_matches, etc.)
- Implement dispute handling (soft delete + recreate, decrement/increment stats)
- Create `reconcile_tournament_stats` management command
- Create participation history API endpoint (`/api/profile/<public_id>/tournaments/`)
- Create tournament history UI (timeline view with placement badges)
- Add achievement eligibility queries (future-proof for badge system)
- Write 100+ tests (unit, integration, reconciliation)

**Out of Scope:**
- Achievement/badge creation (separate feature)
- Leaderboard integration (separate feature)
- Match-level participation tracking (optional, future)

### Files Likely Touched

```
apps/user_profile/
  models.py (add TournamentParticipation, stats fields to UserProfile)
  signals.py (add participation creation, stats update signals)
  services/achievement_service.py (NEW - eligibility queries)
  migrations/000X_add_tournament_participation.py (NEW)
  migrations/000Y_add_stats_fields.py (NEW)
  tests/test_participation.py (NEW)
  tests/test_stats_sync.py (NEW)

apps/tournaments/
  signals.py (trigger participation creation on completion)
  tests/test_participation_integration.py (NEW)

apps/core/management/commands/
  reconcile_tournament_stats.py (NEW)

apps/api/v1/profile/
  views.py (add tournament history endpoint)
  serializers.py (add ParticipationHistorySerializer)

templates/user_profile/
  tournament_history.html (NEW - timeline view)

static/js/
  tournament_timeline.js (NEW)
```

### Acceptance Criteria

- [ ] TournamentParticipation records created within 1 minute of tournament completion
- [ ] 100% of participants have records (no missing entries)
- [ ] Placement tiers accurate (validated against tournament results)
- [ ] Profile stats update within 10 seconds of participation creation
- [ ] Stats accurate (match manual count of participation records)
- [ ] Dispute resolution works (soft delete → recalculate stats)
- [ ] Reconciliation completes in <10 minutes for 10K users
- [ ] Participation history API respects privacy settings
- [ ] Tournament history UI displays chronologically with placement badges
- [ ] Test coverage ≥95% for participation code (100+ tests)

### Required Documentation Updates

- **Status Tracker:** Mark UP-019 through UP-024 complete, update stats metrics
- **Decision Log:** No new ADRs (snapshot strategy already documented)
- **Backlog:** Mark 6 items complete

---

## MISSION UP-M5: AUDIT + ACTIVITY + SECURITY HARDENING

**Duration:** 6 days  
**Priority:** P0 (COMPLIANCE)  
**Dependencies:** None (can run parallel with M3/M4)  
**Backlog Items:** UP-025, UP-026, UP-027, UP-028, UP-029, UP-030

### Scope

**In Scope:**
- Create AuditEvent model (immutable, HMAC-signed, append-only)
- Implement signature generation (HMAC-SHA256)
- Enforce immutability (database permissions + application checks)
- Create AuditLogger service (helper functions: log_kyc_view, log_profile_edit, etc.)
- Add django-cryptography dependency
- Encrypt `id_number` field (EncryptedCharField)
- Implement file encryption (Fernet cipher for KYC documents)
- Create data migration to encrypt existing plaintext KYC data
- Add KYC access logging (every document view creates AuditEvent)
- Create UserActivity model (user-facing timeline)
- Add activity creation signals (tournament won, badge earned, etc.)
- Create activity feed UI (timeline with cards)
- Add django-ratelimit dependency
- Implement rate limiting (login: 5/15min, API: 60/min, password reset: 3/hour)
- Create audit log viewer (staff-only admin page)
- Write 120+ tests (unit, integration, security, penetration)

**Out of Scope:**
- Admin notification system (email on KYC access) - future enhancement
- SIEM integration (Splunk, Datadog logs) - operations work
- Key rotation automation (manual process for now)

### Files Likely Touched

```
apps/user_profile/
  models.py (add AuditEvent, UserActivity, encrypt VerificationRecord.id_number)
  services/audit_logger.py (NEW)
  services/kyc_encryption.py (NEW)
  migrations/000X_add_audit_event.py (NEW)
  migrations/000Y_add_user_activity.py (NEW)
  migrations/000Z_encrypt_kyc_data.py (NEW - data migration)
  tests/test_audit.py (NEW)
  tests/test_encryption.py (NEW)
  tests/test_immutability.py (NEW)

apps/accounts/
  views/login.py (add rate limiting)
  views/password_reset.py (add rate limiting)

apps/api/v1/
  views.py (add rate limiting decorators)

apps/admin/
  views/audit_log.py (NEW - staff-only viewer)

templates/user_profile/
  activity_feed.html (NEW)

settings.py (add AUDIT_SIGNING_KEY, ENCRYPTION_KEY to env vars)

requirements.txt (add django-cryptography, django-ratelimit)
```

### Acceptance Criteria

- [ ] AuditEvent model immutable (UPDATE/DELETE raises exception)
- [ ] Signature verification passes for all events
- [ ] All critical actions logged (KYC view, profile edit, balance adjust)
- [ ] `id_number` encrypted at rest (verified in database dump)
- [ ] KYC files encrypted (cannot open without decryption key)
- [ ] Every KYC view creates audit event (100% coverage)
- [ ] UserActivity feed displays user achievements
- [ ] Privacy controls work (user can hide activities)
- [ ] Rate limits enforced (6th login attempt blocked with 429 response)
- [ ] Staff bypass works (unlimited attempts for staff)
- [ ] Audit log viewer functional and usable
- [ ] Penetration test passed (zero vulnerabilities)
- [ ] Test coverage ≥95% for security code (120+ tests)

### Required Documentation Updates

- **Status Tracker:** Mark UP-025 through UP-030 complete, update security metrics
- **Decision Log:** No new ADRs (audit/encryption already documented)
- **Backlog:** Mark 6 items complete, ALL ITEMS COMPLETE
- **Readiness Gate:** Update checklist, mark security criteria complete

---

## MISSION DEPENDENCIES

```
UP-M0 (Safety)
  └─→ UP-M1 (Identity + Privacy)
       ├─→ UP-M2 (OAuth)
       ├─→ UP-M3 (Economy) [parallel]
       └─→ UP-M4 (Stats) [parallel]

UP-M5 (Security) [parallel to all, can start anytime]
```

**Critical Path:** M0 → M1 → M2  
**Parallel Tracks:** M3 and M4 can run simultaneously after M1  
**Independent:** M5 can run parallel to M3/M4 (different code areas)

---

## IMPLEMENTATION SEQUENCE

### Week 1: Foundation
- **Day 1-2:** Mission UP-M0 (Safety gates)
- **Day 3-5:** Mission UP-M1 (Identity + Privacy) - start

### Week 2: Identity Complete
- **Day 1-3:** Mission UP-M1 (Identity + Privacy) - finish
- **Day 4-5:** Mission UP-M2 (OAuth) - start

### Week 3: OAuth + Parallel Work Begins
- **Day 1:** Mission UP-M2 (OAuth) - finish
- **Day 2-5:** Mission UP-M3 (Economy) + Mission UP-M5 (Security) - start both

### Week 4: Parallel Implementation
- **Day 1-5:** Mission UP-M3 (Economy) + Mission UP-M4 (Stats) + Mission UP-M5 (Security) - continue

### Week 5: Finalization
- **Day 1-3:** Mission UP-M4 (Stats) + Mission UP-M5 (Security) - finish
- **Day 4-5:** Integration testing, bug fixes

### Week 6: Testing & Validation
- **Day 1-2:** Integration testing (all missions together)
- **Day 3:** Performance testing + Security audit
- **Day 4:** User acceptance testing (beta users)
- **Day 5:** Readiness gate review + Go/No-Go decision

---

## QUALITY GATES (Per Mission)

Each mission must pass these gates before marking complete:

### Code Quality
- [ ] Test coverage ≥90% for new code
- [ ] Code review approved (2+ senior engineers)
- [ ] Zero P0/P1 bugs
- [ ] Linting passes (pylint, eslint)

### Functionality
- [ ] All acceptance criteria met
- [ ] Manual QA passed (test scenarios documented)
- [ ] No regressions (existing tests still pass)

### Documentation
- [ ] Status tracker updated
- [ ] Backlog items marked complete
- [ ] API docs updated (if applicable)
- [ ] User guide updated (if applicable)

### Deployment
- [ ] Migrations tested on staging
- [ ] Feature flags configured (instant disable capability)
- [ ] Rollback plan documented
- [ ] Monitoring alerts configured

---

## MISSION COMPLETION TRACKER

| Mission | Status | Items | Tests | Migrations | Completion Date |
|---------|--------|-------|-------|------------|-----------------|
| UP-M0 | ⏸️ NOT STARTED | 2 | 0/20+ | 0/0 | - |
| UP-M1 | ⏸️ NOT STARTED | 8 | 0/150+ | 0/3 | - |
| UP-M2 | ⏸️ NOT STARTED | 3 | 0/50+ | 0/0 | - |
| UP-M3 | ⏸️ NOT STARTED | 5 | 0/80+ | 0/1 | - |
| UP-M4 | ⏸️ NOT STARTED | 6 | 0/100+ | 0/2 | - |
| UP-M5 | ⏸️ NOT STARTED | 6 | 0/120+ | 0/3 | - |

**Total Progress:** 0% (0/30 items complete)

---

## READINESS GATE MAPPING

**Readiness Gate Prerequisites → Missions:**

| Prerequisite | Mission(s) |
|--------------|------------|
| Public ID operational | UP-M1 |
| Profile creation guaranteed | UP-M0, UP-M1, UP-M2 |
| Privacy enforcement working | UP-M1 |
| Transaction sync functional | UP-M3 |
| Audit logging operational | UP-M5 |
| KYC encryption working | UP-M5 |
| GDPR compliance ≥60% | UP-M1 (privacy) + UP-M5 (audit/encryption) |

**Blocker:** All missions must complete before Tournament Phase 1 resumes.

---

## ROLLBACK STRATEGY (Per Mission)

Each mission is independently rollbackable:

**Mission M0:** No code changes, only inventory (no rollback needed)  
**Mission M1:** Feature flag `ENABLE_PUBLIC_ID` (disable → revert to username URLs)  
**Mission M2:** Feature flag `ENABLE_NEW_OAUTH` (disable → use old OAuth handler)  
**Mission M3:** Feature flag `ENABLE_ECONOMY_SYNC` (disable → manual balance updates)  
**Mission M4:** Feature flag `ENABLE_PARTICIPATION_TRACKING` (disable → no participation records)  
**Mission M5:** Cannot rollback encryption (one-way), but can disable audit logging

---

**END OF MISSION PLAN**

**Status:** Ready for Implementation  
**Total Missions:** 6  
**Estimated Duration:** 6 weeks  
**Next Step:** Begin Mission UP-M0 (Safety Gates)

---

*Document Version: 1.0*  
*Last Updated: December 22, 2025*  
*Author: Platform Architecture Team*
