# UP-PHASE-0: IMPLEMENTATION CHECKLIST

**Platform:** DeltaCrown Esports Tournament Platform  
**Project:** User Profile Modernization  
**Date:** December 22, 2025  
**Status:** AUTHORITATIVE CHECKLIST (LOCKED)

---

## 1. PURPOSE & NON-GOALS

**Purpose:**
This checklist consolidates all User Profile modernization architecture decisions, execution plan, and quality gates into ONE authoritative document. Use this as the single source of truth for implementation tracking. All architectural decisions documented here are LOCKED and require formal ADR amendment to change.

**Non-Goals:**
- Not a detailed design document (see 00_TargetArchitecture/*.md for technical details)
- Not an implementation guide (see code files for patterns)
- Not a tutorial (assumes team has reviewed architecture docs)
- Not code (documentation only, no executable content)

**Context:**
User Profile audit found critical gaps (0% stat accuracy, no economy sync, broken APIs, privacy bypasses). Tournament Phase 1 PAUSED to stabilize User Profile foundation. Resume conditions defined in Section 5.

---

## 2. LOCKED DECISIONS (ADR SUMMARY)

All decisions below are APPROVED and LOCKED. Changes require formal ADR amendment.

| Decision Area | Chosen Strategy | Alternative Rejected | Rationale | ADR Ref |
|---------------|-----------------|----------------------|-----------|---------|
| **Public ID Format** | Sequential DC-YY-NNNNNN | UUID (not memorable), Hashid (not branded) | Human-memorable, branded, non-PII | ADR-UP-001 |
| **Profile Provisioning** | Atomic signal + safety accessor | Lazy creation, middleware-only | Guarantee invariant (100% User→Profile) | ADR-UP-002 |
| **Privacy Default** | Opt-in (PII hidden by default) | Opt-out, public by default | GDPR compliance, user control | ADR-UP-003 |
| **Economy Source of Truth** | Ledger-first (EconomyTransaction) | Wallet-first, profile-first | Immutable audit trail, reconciliation | ADR-UP-004 |
| **Stats Ownership** | Source apps own, profile caches | Profile owns stats | Queryable, filterable, auditable | ADR-UP-005 |
| **Audit Log Semantics** | Actor (who) + User (target) fields | Single user field, activity log pattern | Clear responsibility, compliance | ADR-UP-006 |
| **KYC Self-Access** | ✅ DECIDED: User can view/download own docs | Staff-only access | User data ownership, transparency | ADR-UP-007 |

**KYC Self-Access Policy (LOCKED DECISION):**
- Users CAN view their own KYC documents (transparency, data ownership)
- Users CAN download their own documents (data portability, GDPR right to access)
- Users CANNOT approve/reject their own KYC (requires KYC reviewer role)
- MANDATORY: Every view/download creates AuditEvent (user=self, actor=self, action=VIEW/DOWNLOAD, IP logged)
- Staff access requires `view_kyc_documents` permission + all actions logged
- Access logging requirements per UP-06 Section 3 (Access Logging Requirements)

---

## 3. PHASE CHECKLIST BY MISSION

### UP-M0: Safety Net & Inventory (2 days, P0 BLOCKING)

**Goal:** Make system safe to modify, create inventory of risks

**Checklist:**
- [ ] Grep codebase for profile access patterns (`.profile`, `select_related('profile')`)
- [ ] Document 47+ locations assuming profile exists without checking
- [ ] Categorize by risk level (direct access = high, safe access = low)
- [ ] Create `get_profile_or_create(user)` utility in apps/user_profile/utils.py
- [ ] Create `@ensure_profile_exists` decorator for views
- [ ] Implement atomic transaction wrapper with retry logic (3 attempts)
- [ ] Write safety utility tests (100% coverage, 20+ test cases)
- [ ] Create inventory report (Documents/UserProfile_CommandCenter_v1/03_Analysis/PROFILE_ACCESS_PATTERNS.md)
- [ ] Automated validation: Copilot checklist confirms all patterns documented, tests pass

**Acceptance Criteria:**
- Inventory complete: All profile access patterns documented with file paths and line numbers
- Safety utilities work: Zero profile creation failures in 1000+ test runs
- Tests pass: 100% coverage for get_profile_or_create and decorator
- Documentation: Usage examples in README
- Automated checks: CI grep audit confirms no unsafe patterns remain

**Required Tests:**
- Unit: Test profile creation when missing (success rate 100%)
- Unit: Test idempotency (no duplicate profiles on concurrent calls)
- Integration: Test decorator on views (profile exists after request)
- Race condition: Test concurrent access (10 threads, 1 profile created)

---

### UP-M1: Identity + Public ID + Privacy (5 days, P0 BLOCKING)

**Goal:** Guaranteed profile provisioning, non-PII identifier, privacy defaults

**Checklist:**
- [ ] Add public_id field to UserProfile (CharField, unique, indexed, max_length=15)
- [ ] Create PublicIDCounter model (year IntegerField, counter IntegerField, unique_together)
- [ ] Implement PublicIDGenerator service (DC-YY-NNNNNN format, atomic F() increment)
- [ ] Refactor create_user_profile signal to generate public_id atomically
- [ ] Create data migration to backfill existing users (sorted by created_at)
- [ ] Add get_by_public_id() QuerySet method
- [ ] Update profile URLs to use public_id (not username or PK)
- [ ] Create PrivacySettings model (OneToOne, 6 boolean fields + visibility_level)
- [ ] Set privacy defaults (all PII toggles False, visibility public)
- [ ] Create PrivacyAwareProfileSerializer base class
- [ ] Implement template tags ({% privacy_filter profile viewer 'email' %})
- [ ] Run privacy grep audit (fail CI on {{ profile.email }} patterns)
- [ ] Update 47+ locations to use safety accessor (from M0 inventory)

**Acceptance Criteria:**
- Public ID: All users have unique DC-YY-NNNNNN identifiers
- Invariant: Zero UserProfile.DoesNotExist errors in logs for 48h post-deploy
- Privacy: All PII fields default to hidden, users must opt-in
- Grep audit: Zero direct PII access patterns in codebase
- URLs: All profile links use public_id (/profile/DC-25-000042/)

**Required Tests:**
- Unit: Public ID generation (format validation, uniqueness, year rollover)
- Unit: Concurrency test (10 simultaneous profile creations, no duplicate IDs)
- Unit: Privacy serializer filters email when show_email=False
- Unit: Template tag blocks email when viewer != owner
- Integration: Signal creates profile with public_id on User creation
- Integration: Privacy settings respect visibility_level enum
- E2E: Grep audit passes (no PII leak patterns)

---

### UP-M2: OAuth Integration (3 days, P1 HIGH)

**Goal:** External auth providers create profiles correctly

**Checklist:**
- [ ] Audit OAuth callback handlers (Google, Discord, etc.)
- [ ] Ensure all callbacks create UserProfile atomically
- [ ] Add retry logic to OAuth flows (3 attempts on profile creation failure)
- [ ] Test OAuth with privacy defaults (PrivacySettings created)
- [ ] Log OAuth profile creation failures (Sentry + Slack alert)

**Acceptance Criteria:**
- OAuth success rate: 100% profile creation (0% failure rate)
- Privacy defaults: All OAuth users have PrivacySettings created
- Error handling: OAuth failures logged and alerted

**Required Tests:**
- Integration: Google OAuth creates User + UserProfile + PrivacySettings atomically
- Integration: Discord OAuth retry logic works (simulate transient DB error)
- E2E: New user via OAuth can immediately view profile page

---

### UP-M3: Economy Sync (3 days, P0 BLOCKING)

**Goal:** Profile balance always matches ledger

**Checklist:**
- [ ] Add signal handler (transaction_completed → update profile balance)
- [ ] Implement atomic F() updates (prevent race conditions)
- [ ] Update profile.deltacoin_balance on award transactions (+=)
- [ ] Update profile.deltacoin_balance on spend transactions (-=)
- [ ] Update profile.lifetime_earnings on award/refund (+=)
- [ ] Create reconciliation command (recompute from ledger, detect drift)
- [ ] Schedule nightly reconciliation (3 AM UTC cron job)
- [ ] Implement drift handling (auto-repair <5%, alert ≥5%)
- [ ] Add EconomyReconciliationLog model (track drift events)

**Acceptance Criteria:**
- Correctness guarantee: Every transaction creates audit record + updates caches atomically (no partial updates)
- Signal latency: Balance updates within same database transaction as ledger entry (synchronous, not async)
- Drift rate: <1% after 7 days of nightly reconciliation
- Invariants: profile.deltacoin_balance == wallet.cached_balance == SUM(ledger WHERE status=COMPLETED)
- Alerts: Slack notification on drift ≥5%
- Performance: Balance read queries <50ms (cached field, no joins)

**Required Tests:**
- Unit: Signal handler updates balance on transaction (±amount correct)
- Unit: Lifetime earnings increases on award (not spend)
- Unit: Reconciliation detects 1 DC drift
- Integration: Concurrent transactions don't create negative balance
- Integration: Nightly reconciliation repairs drift

---

### UP-M4: Stats + History (4 days, P1 HIGH)

**Goal:** Track tournaments, matches, activity accurately

**Checklist:**
- [ ] Create TournamentParticipation model (user, tournament, team, status)
- [ ] Extend TournamentResult model (add user field for individual tracking)
- [ ] Populate Match model on game completion (signal from games app)
- [ ] Create UserActivity model (activity_type, metadata JSON, visibility)
- [ ] Add signal handlers (tournament end → update profile stats)
- [ ] Update profile cached counters (tournaments_participated, matches_won, etc.)
- [ ] Implement stats service (get_match_history, get_tournament_breakdown)
- [ ] Activity timeline respects privacy (filter by visibility + viewer relationship)
- [ ] Nightly reconciliation for stats (recompute from source)

**Acceptance Criteria:**
- Stats accuracy: Cached counters match source counts (drift <1%)
- Activity timeline: Major events appear (tournament wins, achievements)
- Privacy: Match history hidden when show_match_history=False

**Required Tests:**
- Unit: Tournament end signal increments tournaments_participated
- Unit: Match completion updates matches_played and matches_won
- Unit: Activity timeline filters by visibility (PUBLIC/FOLLOWERS/PRIVATE)
- Integration: Stats reconciliation detects mismatch and repairs

---

### UP-M5: Audit + Security (3 days, P0 BLOCKING)

**Goal:** Immutable audit trail, KYC encryption, rate limiting

**Checklist:**
- [ ] Create AuditEvent model (user, actor, event_type, old_value, new_value, IP)
- [ ] Add database trigger (prevent UPDATE/DELETE on audit_events table)
- [ ] Log profile edits (email, display_name, real_name changes)
- [ ] Log privacy changes (all PrivacySettings toggles)
- [ ] Log KYC actions (upload, view, download, approve/reject)
- [ ] Log economy actions (balance adjustments, wallet freeze)
- [ ] Log admin actions (impersonation, bulk export, suspension)
- [ ] Encrypt KYC fields (real_full_name, date_of_birth, phone)
- [ ] Implement KYC access controls (view_kyc_documents permission)
- [ ] Add KYC access logging (every view/download creates AuditEvent)
- [ ] Implement rate limiting (profile endpoints, KYC endpoints)
- [ ] Add enumeration detection (sequential ID access alerts)
- [ ] Security penetration test (privacy bypass, KYC access, enumeration)

**Acceptance Criteria:**
- Audit immutability: Database trigger prevents modification
- All actions logged: Profile edits, KYC views, admin actions have audit records
- KYC encrypted: Sensitive fields unreadable in database dumps
- Rate limiting: 429 response after threshold (10 profiles/min for others)
- Pen test: Zero critical vulnerabilities, privacy enforcement verified

**Required Tests:**
- Unit: AuditEvent creation on profile edit (old→new values captured)
- Unit: Audit log UPDATE raises database error (immutability)
- Unit: KYC field encryption (plaintext not in database)
- Unit: KYC access denied for unauthorized roles
- Integration: Profile view rate limit returns 429 after 10 requests
- Security: Privacy bypass test (API manipulation fails)

---

## 4. QUALITY GATES (SHORTENED)

**Per-Commit Gates (CI Pipeline):**
- All existing tests pass (pytest exit code 0)
- Code coverage ≥75% for modified files
- Privacy grep audit passes (no {{ profile.email }} patterns)
- Bandit security linter passes
- Migrations apply cleanly on empty database

**Per-Phase Gates (Manual Review):**
- UP-M1: Zero UserProfile.DoesNotExist errors for 48h post-deploy
- UP-M2: OAuth profile creation 100% success rate
- UP-M3: Economy drift <1% after 7 days
- UP-M4: Cached stats match source counts (drift <1%)
- UP-M5: Security pen test passes (no critical vulnerabilities)

- Test pass rate drops below 95%
- Privacy grep audit fails (PII leak detected)
- P0 bug discovered in production
- Migration fails on staging
- Audit log immutability violated
- Economy drift exceeds 5%

---

## 5. DEFINITION OF DONE (TOURNAMENT PHASE 1 RESUME)
**Blocker Conditions (Stop Development):**
- Test pass rate drops below 95%
- Privacy grep audit fails (PII leak detected)
- P0 bug discovered in production
- Migration fails on staging
- Audit log immutability violated
- Economy drift exceeds 5%

---

## 5. DEFINITION OF DONE (TOURNAMENT PHASE 1 RESUME)

**Tournament Phase 1 CAN RESUME when:**

**Core Complete (Non-Negotiable):**
- [ ] UP-M1 deployed to production (invariant + public ID + privacy)
- [ ] Zero profile-related errors in logs for 48 hours
- [ ] UP-M3 deployed to production (economy sync stable)
- [ ] Drift rate <1% for 7 consecutive days

**Stats Foundation (Minimum):**
- [ ] TournamentParticipation model created and migrated
- [ ] Tournament services can record participation
- [ ] Stats update signals wired (even if UI incomplete)

**Quality Validated:**
- [ ] Test coverage ≥75% for user_profile app
- [ ] No P1+ bugs in User Profile system
- [ ] Privacy enforcement verified (grep audit passes)
- [ ] Profile page loads <300ms
- [ ] Tournament registration <500ms end-to-end

**Optional (Can Defer):**
- UP-M2 (OAuth) can be partially complete if existing OAuth works
- UP-M4 (Stats UI) can be incomplete if data model exists
- UP-M5 (Audit) can be partially complete if critical actions logged

**Decision Authority:** Engineering Manager + Product Owner

---

## 6. STOP-THE-LINE RULES (SHORT LIST)

**Development MUST PAUSE immediately if:**

1. **Test Pass Rate <95%** → Fix broken tests before continuing
2. **Privacy Grep Audit Fails** → Any {{ profile.email }} pattern found in PR
3. **P0 Production Bug** → User Profile work paused until hotfix deployed
4. **Migration Fails on Staging** → Do not proceed to next phase
5. **Audit Log Modified** → Security incident, investigate immediately
6. **Economy Drift >5%** → Halt deployment, investigate root cause
7. **Pen Test Fails** → Cannot deploy to production, fix vulnerabilities

**Escalation Path:**
- Blocker identified → notify team lead immediately (Slack alert)
- Cannot resolve in 4 hours → escalate to engineering manager
- Engineering manager decides: fix now / defer / abort phase

**Rollback Trigger:**
- User data loss → immediate rollback
- Security breach detected → immediate rollback
- Profile creation failure rate >1% → rollback and investigate

---

## TRACKER UPDATE REQUIREMENTS

**After Each Mission Completion:**

**Status Tracker:**
- Path: Documents/UserProfile_CommandCenter_v1/02_Trackers/UP_TRACKER_STATUS.md
- Update: Mark mission complete with completion date, update progress percentage, log blockers
- Frequency: Daily during active development

**Decisions Tracker:**
- Path: Documents/UserProfile_CommandCenter_v1/02_Trackers/UP_TRACKER_DECISIONS.md
- Update: Add ADR for significant design decisions (examples: "Why F() updates for counters", "Why 3 AM reconciliation")
- Frequency: Real-time as decisions are made

**Backlog:**
- Path: Documents/UserProfile_CommandCenter_v1/01_Planning/UP_BACKLOG.md
- Update: Mark completed items as DONE, add new items discovered, re-prioritize if needed
- Frequency: After each mission completion

**Mission Plan:**
- Path: Documents/UserProfile_CommandCenter_v1/01_Planning/UP_MISSION_PLAN.md
- Update: Update mission status, actual vs estimated duration, lessons learned
- Frequency: After each mission completion

**Architecture Docs (Reference Only, Do Not Edit):**
- Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_01_CORE_USER_PROFILE_ARCHITECTURE.md
- Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_02_PUBLIC_USER_ID_STRATEGY.md
- Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_03_PRIVACY_ENFORCEMENT_MODEL.md
- Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_04_PROFILE_ECONOMY_SYNC.md
- Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_05_STATS_HISTORY_ACTIVITY_MODEL.md
- Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_06_AUDIT_AND_SECURITY.md
- Documents/UserProfile_CommandCenter_v1/01_Planning/UP_07_EXECUTION_GATES_AND_ORDER.md

---

## FINAL PRE-PRODUCTION CHECKLIST

**Before Production Deploy:**
- [ ] All missions (UP-M0 through UP-M5) complete
- [ ] All quality gates passed
- [ ] Security penetration test signed off
- [ ] Staging stable for 48 hours (zero profile errors)
- [ ] Rollback plan tested
- [ ] Monitoring dashboards configured (Grafana)
- [ ] Alerts configured (drift, privacy bypass, rate limits)
- [ ] Documentation updated (README, runbooks)
- [ ] Team trained on new architecture
- [ ] Product owner approves deployment

---

**End of Checklist**
