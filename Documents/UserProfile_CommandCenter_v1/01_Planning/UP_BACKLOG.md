# USER PROFILE MODERNIZATION BACKLOG

**Platform:** DeltaCrown Esports Tournament Platform  
**Project:** User Profile System Modernization  
**Date:** December 22, 2025  
**Status:** APPROVED FOR IMPLEMENTATION

---

## BACKLOG OVERVIEW

**Total Items:** 30  
**Priority Distribution:**
- P0 (Blocking): 12 items
- P1 (High): 13 items
- P2 (Medium): 5 items

**Phase Distribution:**
- UP-0 (Discovery): 2 items
- UP-1 (Identity + Privacy): 8 items
- UP-2 (OAuth): 3 items
- UP-3 (Economy): 5 items
- UP-4 (Stats + History): 6 items
- UP-5 (Audit + Security): 6 items

---

## PHASE UP-0: DISCOVERY & SAFETY GATES

### UP-001: Audit All Profile Access Patterns
**Priority:** P0  
**Area:** Discovery  
**Dependencies:** None

**Description:**  
Grep entire codebase for all profile access patterns (request.user.profile, User.objects.select_related('profile'), etc.). Document 47+ locations that assume profile exists without checking. Create comprehensive list of code locations requiring safety fixes.

**Definition of Done:**
- [ ] All profile access patterns documented (file path + line number)
- [ ] Categorized by risk level (direct access vs safe access)
- [ ] List of 47+ locations requiring fixes created
- [ ] Shared with team for review

**Test Expectations:**
- **Analysis:** Automated grep search produces exhaustive list
- **Validation:** Manual review confirms no false negatives

**References:**  
- User Profile Audit Part 1, Section 2.2 (Profile Creation Failures)
- Target Architecture, Section 3 (Profile Provisioning)

---

### UP-002: Create Safety Accessor Utility
**Priority:** P0  
**Area:** Identity  
**Dependencies:** UP-001

**Description:**  
Create `get_profile_or_create()` utility function that safely retrieves user profile with automatic creation fallback. Add `ensure_profile_exists()` decorator for views. Provides safety layer for all profile access.

**Definition of Done:**
- [ ] `get_profile_or_create(user)` function in apps/user_profile/utils.py
- [ ] `@ensure_profile_exists` decorator created
- [ ] Atomic transaction guarantees (user + profile created together)
- [ ] Retry logic (3 attempts on transient failures)
- [ ] Logging on profile creation (audit trail)
- [ ] Documentation with usage examples

**Test Expectations:**
- **Unit:** Test profile creation when missing (100% success rate)
- **Unit:** Test idempotency (no duplicate profiles)
- **Integration:** Test concurrent access (race condition handling)
- **Assert:** Zero profile creation failures in 1000+ test runs

**References:**  
- Target Architecture, Section 3.2 (Profile Provisioning Patterns)

---

## PHASE UP-1: IDENTITY + PUBLIC ID + PRIVACY

### UP-003: Add public_id Field to UserProfile
**Priority:** P0  
**Area:** Identity  
**Dependencies:** None

**Description:**  
Add `public_id` field to UserProfile model (CharField, unique, indexed, max_length=15, format: DC-YY-NNNNNN). Field stores human-readable, non-PII identifier for public profile access.

**Definition of Done:**
- [ ] Migration created (add field, set null=True initially)
- [ ] Field validated with regex (^DC-\d{2}-\d{6}$)
- [ ] Database index created (fast lookups)
- [ ] Admin panel displays public_id
- [ ] Field documented in model docstring

**Test Expectations:**
- **Unit:** Field accepts valid format (DC-25-000001)
- **Unit:** Field rejects invalid format (DC-2025-1, DCXX, etc.)
- **Migration:** Test runs successfully on staging data

**References:**  
- Target Architecture, Section 4.1 (Public ID Strategy)

---

### UP-004: Public ID Generator Service
**Priority:** P0  
**Area:** Identity  
**Dependencies:** UP-003

**Description:**  
Create PublicIDGenerator service with sequential allocation logic. Uses database counter table for atomicity. Generates format DC-YY-NNNNNN where YY=year, NNNNNN=sequential counter.

**Definition of Done:**
- [ ] PublicIDCounter model created (year, counter fields, unique constraint)
- [ ] `generate_public_id()` method in service class
- [ ] Atomic increment (F() expression prevents race conditions)
- [ ] Year rollover logic (resets counter Jan 1)
- [ ] Counter exhaustion detection (999,999 limit alert)
- [ ] Comprehensive test suite (concurrency, rollover, limits)

**Test Expectations:**
- **Unit:** Test sequential generation (DC-25-000001, DC-25-000002, etc.)
- **Unit:** Test year rollover (Dec 31 → Jan 1 resets counter)
- **Integration:** Test concurrent generation (100 parallel requests)
- **Assert:** Zero duplicate public_ids in 10,000 generation attempts

**References:**  
- Target Architecture, Section 4.2 (Sequential Generation Logic)

---

### UP-005: Profile Creation Signal with public_id
**Priority:** P0  
**Area:** Identity  
**Dependencies:** UP-002, UP-004

**Description:**  
Refactor `create_user_profile` signal to generate public_id during profile creation. Ensure atomic transaction, retry logic, and comprehensive error handling.

**Definition of Done:**
- [ ] Signal generates public_id on profile creation
- [ ] Atomic transaction wrapper (rollback on failure)
- [ ] Retry logic (3 attempts with exponential backoff)
- [ ] Error logging (failed profile creation audited)
- [ ] Backward compatibility (existing profiles without public_id handled)

**Test Expectations:**
- **Unit:** New user creation generates valid public_id
- **Unit:** Signal failure triggers rollback (no partial profiles)
- **Integration:** Test OAuth flow (profile + public_id created)
- **Assert:** 100% success rate in 2000+ user creation tests

**References:**  
- Target Architecture, Section 3.2 (Profile Provisioning)
- Economy & Stats Architecture, Signal Patterns

---

### UP-006: Backfill public_id for Existing Users
**Priority:** P0  
**Area:** Identity  
**Dependencies:** UP-004, UP-005

**Description:**  
Create data migration to generate public_ids for all existing users without one. Batch processing (1000 users at a time) to prevent timeout.

**Definition of Done:**
- [ ] Data migration script created
- [ ] Batch processing logic (1000 users per batch)
- [ ] Progress logging (every 1000 users)
- [ ] Dry-run mode (test before applying)
- [ ] Rollback capability (mark migration reversible)
- [ ] Verification query (confirm 100% users have public_id)

**Test Expectations:**
- **Migration:** Dry-run on staging data (validate no errors)
- **Migration:** Actual run on staging (verify 100% coverage)
- **Assert:** All UserProfile records have valid public_id after migration

**References:**  
- Execution Plan, Phase UP-1, Day 5 (Migration)

---

### UP-007: Add get_by_public_id QuerySet Method
**Priority:** P0  
**Area:** Identity  
**Dependencies:** UP-003

**Description:**  
Add custom QuerySet method for efficient public_id lookups. Enables `UserProfile.objects.get_by_public_id('DC-25-000042')` pattern throughout codebase.

**Definition of Done:**
- [ ] Custom UserProfileQuerySet class created
- [ ] `get_by_public_id(public_id)` method implemented
- [ ] Returns UserProfile or raises DoesNotExist
- [ ] Efficient lookup (uses indexed field)
- [ ] Manager attached to UserProfile model

**Test Expectations:**
- **Unit:** Test valid public_id lookup (returns correct profile)
- **Unit:** Test invalid public_id (raises DoesNotExist)
- **Performance:** Lookup completes in <10ms (indexed query)

**References:**  
- Target Architecture, Section 4.3 (Query Patterns)

---

### UP-008: PrivacySettings Model
**Priority:** P0  
**Area:** Privacy  
**Dependencies:** None

**Description:**  
Create PrivacySettings model (OneToOne with UserProfile) with granular visibility controls. Fields: show_full_name, show_email, show_stats, show_transactions, show_match_history, visibility_level.

**Definition of Done:**
- [ ] Model created with 6+ privacy fields (BooleanField)
- [ ] OneToOne relationship with UserProfile
- [ ] Default settings: all PII hidden (privacy-first)
- [ ] Signal creates PrivacySettings on profile creation
- [ ] Admin panel integration (view/edit privacy settings)

**Test Expectations:**
- **Unit:** Test default privacy settings (all PII hidden)
- **Unit:** Test signal creates settings on profile creation
- **Integration:** Test OneToOne relationship integrity

**References:**  
- Target Architecture, Section 5.2 (Privacy Model)

---

### UP-009: PrivacyAwareProfileSerializer Base Class
**Priority:** P0  
**Area:** Privacy  
**Dependencies:** UP-008

**Description:**  
Create base serializer class that filters profile fields based on viewer identity and privacy settings. All profile serializers inherit from this to enforce privacy at API layer.

**Definition of Done:**
- [ ] PrivacyAwareProfileSerializer base class created
- [ ] `filter_fields_by_privacy(viewer, profile)` method
- [ ] Handles viewer types: owner, staff, public, anonymous
- [ ] Fields removed from response if privacy disallows
- [ ] Documentation with usage examples

**Test Expectations:**
- **Unit:** Owner sees all fields (no filtering)
- **Unit:** Public sees only non-PII fields (email hidden)
- **Unit:** Staff sees all fields (audit access)
- **Integration:** Test API responses vary by viewer

**References:**  
- Target Architecture, Section 5.3 (Privacy Enforcement Layers)

---

### UP-010: Privacy Enforcement in Templates
**Priority:** P1  
**Area:** Privacy  
**Dependencies:** UP-008

**Description:**  
Create template tags and filters for privacy-aware field display. Enables `{% privacy_filter profile viewer 'email' %}` pattern in templates.

**Definition of Done:**
- [ ] `privacy_filter` template tag created
- [ ] `can_view_field` template filter created
- [ ] Updated profile templates to use privacy tags
- [ ] PII fields conditionally displayed
- [ ] Fallback display for hidden fields ("Hidden by user")

**Test Expectations:**
- **Template:** Test owner view (all fields visible)
- **Template:** Test public view (PII hidden)
- **Integration:** Test profile page renders correctly for different viewers

**References:**  
- Target Architecture, Section 5.3 (Template Layer)

---

## PHASE UP-2: GOOGLE OAUTH HARDENING

### UP-011: Atomic OAuth Profile Creation
**Priority:** P0  
**Area:** Auth  
**Dependencies:** UP-005

**Description:**  
Refactor OAuth callback handlers to guarantee profile creation. Use atomic transaction, consolidate into single `ensure_profile_from_oauth()` function.

**Definition of Done:**
- [ ] Single OAuth profile creation function (no duplicates)
- [ ] Atomic transaction wrapper (user + profile + privacy settings)
- [ ] Error logging for OAuth failures
- [ ] Retry logic (3 attempts on transient failures)
- [ ] Fallback: create profile with minimal data, prompt completion

**Test Expectations:**
- **Integration:** Test full OAuth flow (user + profile created)
- **Integration:** Test OAuth with missing email (fallback works)
- **Integration:** Test concurrent OAuth requests (no race condition)
- **Assert:** 100% profile creation success rate in OAuth tests

**References:**  
- Execution Plan, Phase UP-2 (OAuth Hardening)

---

### UP-012: OAuth Edge Case Handling
**Priority:** P1  
**Area:** Auth  
**Dependencies:** UP-011

**Description:**  
Handle OAuth edge cases: missing email from Google, duplicate email, connection timeout, API failures. Ensure graceful degradation.

**Definition of Done:**
- [ ] Missing email handled (prompt user to add email)
- [ ] Duplicate email handled (merge or error message)
- [ ] Connection timeout handled (retry + user message)
- [ ] API failure handled (clear error message, support link)
- [ ] All edge cases tested

**Test Expectations:**
- **Unit:** Test each edge case scenario (5+ tests)
- **Integration:** Mock Google API failures (timeout, 500 error)
- **Assert:** User sees actionable error message, not 500 page

**References:**  
- Execution Plan, Phase UP-2, Day 2 (Edge Cases)

---

### UP-013: OAuth Integration Test Suite
**Priority:** P1  
**Area:** Auth  
**Dependencies:** UP-011, UP-012

**Description:**  
Create comprehensive OAuth integration test suite covering success path, failures, edge cases, concurrency.

**Definition of Done:**
- [ ] 50+ test scenarios documented
- [ ] Success path tested (happy path)
- [ ] Failure modes tested (Google API down, timeout)
- [ ] Edge cases tested (missing email, duplicate user)
- [ ] Concurrency tested (100 parallel OAuth flows)
- [ ] Test coverage 95%+

**Test Expectations:**
- **Integration:** Full OAuth flow completes successfully
- **Load:** 100 concurrent OAuth requests (no failures)
- **Security:** CSRF token validation tested

**References:**  
- Execution Plan, Phase UP-2, Day 3 (Testing)

---

## PHASE UP-3: ECONOMY SYNC & RECONCILIATION

### UP-014: Transaction Creation Signal
**Priority:** P0  
**Area:** Economy  
**Dependencies:** None

**Description:**  
Create `sync_wallet_balance` signal triggered on DeltaCrownTransaction creation. Updates wallet balance atomically using F() expression.

**Definition of Done:**
- [ ] Signal connects to transaction post_save
- [ ] Wallet balance updated atomically (F() expression)
- [ ] Transaction log created (audit trail)
- [ ] Error handling (rollback on failure)
- [ ] Signal can be skipped (skip_signal flag for bulk operations)

**Test Expectations:**
- **Unit:** Transaction creation updates wallet balance
- **Unit:** Atomic update prevents race conditions (concurrent transactions)
- **Integration:** Test 100 concurrent transactions (no balance drift)
- **Assert:** Wallet balance = sum(transactions) after 1000 transactions

**References:**  
- Economy & Stats Architecture, Section 1.3 (Signal Flow)

---

### UP-015: Wallet to Profile Balance Sync
**Priority:** P0  
**Area:** Economy  
**Dependencies:** UP-014

**Description:**  
Create `sync_profile_balance` signal triggered on wallet balance update. Syncs cached balance to UserProfile.deltacoin_balance field.

**Definition of Done:**
- [ ] Signal connects to wallet post_save
- [ ] Profile balance updated (cached aggregate)
- [ ] Signal can be skipped (skip_signal flag)
- [ ] Error handling and logging

**Test Expectations:**
- **Unit:** Wallet update syncs to profile
- **Integration:** Transaction → wallet → profile sync completes
- **Assert:** Profile.deltacoin_balance matches wallet balance

**References:**  
- Economy & Stats Architecture, Section 1.3 (Cached Aggregates)

---

### UP-016: Nightly Balance Reconciliation Command
**Priority:** P1  
**Area:** Economy  
**Dependencies:** UP-014, UP-015

**Description:**  
Create management command `reconcile_balances` that compares wallet balance vs sum(transactions), and profile balance vs wallet balance. Detects and corrects drift.

**Definition of Done:**
- [ ] Management command created (python manage.py reconcile_balances)
- [ ] Compares wallet vs transaction sum (detect drift)
- [ ] Compares profile vs wallet (detect cache drift)
- [ ] Logs all mismatches (AuditEvent)
- [ ] Auto-corrects profile balance (if wallet correct)
- [ ] Alerts if wallet incorrect (manual review needed)
- [ ] Dry-run mode (--dry-run flag)

**Test Expectations:**
- **Command:** Dry-run on test data (no changes)
- **Command:** Actual run corrects profile drift
- **Assert:** Reconciliation completes in <5 minutes for 10K users

**References:**  
- Economy & Stats Architecture, Section 1.4 (Reconciliation Strategy)

---

### UP-017: Transaction History API Endpoint
**Priority:** P1  
**Area:** Economy  
**Dependencies:** UP-009 (Privacy)

**Description:**  
Create `/api/profile/<public_id>/transactions/` endpoint returning user's transaction history with pagination and filtering. Privacy-aware (only owner sees full history).

**Definition of Done:**
- [ ] API endpoint created (GET only)
- [ ] Pagination (100 transactions per page)
- [ ] Filtering (date range, transaction type)
- [ ] Privacy enforcement (only owner or staff)
- [ ] Performance optimized (select_related, prefetch_related)

**Test Expectations:**
- **API:** Test endpoint returns transactions (200 OK)
- **API:** Test privacy (non-owner gets 403)
- **API:** Test pagination and filtering
- **Performance:** Response time <500ms for 100 transactions

**References:**  
- Execution Plan, Phase UP-3, Day 4 (Transaction History)

---

### UP-018: Transaction History UI
**Priority:** P2  
**Area:** Economy  
**Dependencies:** UP-017

**Description:**  
Create transaction history page in user profile settings. Display table with search, filter, and export functionality.

**Definition of Done:**
- [ ] Template created (transaction history table)
- [ ] Tailwind styling (responsive design)
- [ ] Search and filter UI (date picker, type dropdown)
- [ ] Export button (CSV download)
- [ ] Pagination controls

**Test Expectations:**
- **Template:** Renders correctly with sample data
- **UI:** Search and filter work (JavaScript validation)
- **Accessibility:** WCAG 2.1 AA compliant

**References:**  
- Execution Plan, Phase UP-3, Day 4 (UI)

---

## PHASE UP-4: TOURNAMENT STATS & PARTICIPATION HISTORY

### UP-019: TournamentParticipation Model
**Priority:** P0  
**Area:** Stats  
**Dependencies:** None

**Description:**  
Create TournamentParticipation model storing post-tournament records. Fields: user, tournament, placement, placement_tier, matches_played, matches_won, kills, deaths, prize_amount, xp_earned.

**Definition of Done:**
- [ ] Model created with 10+ fields
- [ ] ForeignKeys to User and Tournament (indexed)
- [ ] Placement tier choices (winner, runner_up, top4, etc.)
- [ ] Timestamps (created_at, updated_at)
- [ ] Unique constraint (user, tournament)
- [ ] Admin panel integration

**Test Expectations:**
- **Unit:** Model saves correctly with all fields
- **Unit:** Unique constraint prevents duplicates
- **Migration:** Runs successfully on staging

**References:**  
- Economy & Stats Architecture, Section 2.1 (Participation Model)

---

### UP-020: Participation Creation Signal
**Priority:** P0  
**Area:** Stats  
**Dependencies:** UP-019

**Description:**  
Create signal triggered when tournament.status changes to 'completed'. Creates TournamentParticipation records for all participants with final stats.

**Definition of Done:**
- [ ] Signal connects to tournament post_save (status='completed')
- [ ] Queries tournament results (all participants)
- [ ] Creates participation record for each participant
- [ ] Calculates placement_tier from final ranking
- [ ] Stores snapshot of stats (matches, kills, etc.)
- [ ] Error handling (log failures, don't block tournament)

**Test Expectations:**
- **Unit:** Tournament completion creates participation records
- **Integration:** Test 32-player tournament (32 records created)
- **Assert:** All participants have participation record

**References:**  
- Economy & Stats Architecture, Section 2.2 (Creation Trigger)

---

### UP-021: Profile Stats Update Signal
**Priority:** P0  
**Area:** Stats  
**Dependencies:** UP-020

**Description:**  
Create signal triggered on TournamentParticipation creation. Updates cached stats in UserProfile (tournaments_played, tournaments_won, total_matches_played, etc.).

**Definition of Done:**
- [ ] Signal connects to participation post_save
- [ ] Increments profile counter fields
- [ ] Handles placement (increment tournaments_won if 1st place)
- [ ] Aggregate stats updated (total_kills, total_deaths)
- [ ] Signal can be skipped (skip_signal flag for bulk operations)

**Test Expectations:**
- **Unit:** Participation creation increments profile stats
- **Integration:** Tournament completion → participation → profile stats
- **Assert:** Profile stats match count of participation records

**References:**  
- Economy & Stats Architecture, Section 3.2 (Update Triggers)

---

### UP-022: Stats Reconciliation Command
**Priority:** P1  
**Area:** Stats  
**Dependencies:** UP-020, UP-021

**Description:**  
Create management command `reconcile_tournament_stats` that compares cached profile stats vs count of participation records. Detects and corrects drift.

**Definition of Done:**
- [ ] Management command created
- [ ] Compares cached stats vs actual participation records
- [ ] Logs all mismatches
- [ ] Auto-corrects profile stats (recalculate from participation)
- [ ] Dry-run mode (--dry-run flag)
- [ ] Performance optimized (<10 min for 10K users)

**Test Expectations:**
- **Command:** Dry-run detects drift without changes
- **Command:** Actual run corrects profile stats
- **Assert:** Profile stats match participation records after reconciliation

**References:**  
- Economy & Stats Architecture, Section 3.5 (Daily Reconciliation)

---

### UP-023: Participation History API Endpoint
**Priority:** P1  
**Area:** Stats  
**Dependencies:** UP-009, UP-019

**Description:**  
Create `/api/profile/<public_id>/tournaments/` endpoint returning user's tournament participation history with filtering and pagination.

**Definition of Done:**
- [ ] API endpoint created (GET only)
- [ ] Pagination (50 tournaments per page)
- [ ] Filtering (date range, placement tier)
- [ ] Privacy enforcement (respects visibility settings)
- [ ] Serializer includes tournament details

**Test Expectations:**
- **API:** Test endpoint returns participation records (200 OK)
- **API:** Test privacy (hidden tournaments excluded)
- **API:** Test pagination and filtering
- **Performance:** Response time <500ms for 50 tournaments

**References:**  
- Execution Plan, Phase UP-4, Day 5 (History API)

---

### UP-024: Tournament History UI
**Priority:** P2  
**Area:** Stats  
**Dependencies:** UP-023

**Description:**  
Create tournament history page displaying user's participation in timeline format with placement badges and stats.

**Definition of Done:**
- [ ] Template created (timeline/card layout)
- [ ] Tailwind styling (responsive, modern design)
- [ ] Placement badges (🥇 winner, 🥈 runner-up, etc.)
- [ ] Stats display (matches played, K/D ratio)
- [ ] Filter controls (date, placement)

**Test Expectations:**
- **Template:** Renders correctly with sample data
- **UI:** Timeline displays chronologically
- **Accessibility:** WCAG 2.1 AA compliant

**References:**  
- Execution Plan, Phase UP-4, Day 5 (History UI)

---

## PHASE UP-5: AUDIT LOG + ACTIVITY FEED + SECURITY

### UP-025: AuditEvent Model
**Priority:** P0  
**Area:** Audit  
**Dependencies:** None

**Description:**  
Create AuditEvent model for immutable audit logging. Fields: event_type, actor, target, action, changes, metadata, ip_address, signature. Append-only with HMAC signature verification.

**Definition of Done:**
- [ ] Model created with 12+ fields
- [ ] HMAC signature generation on save
- [ ] Immutability enforced (prevent UPDATE/DELETE)
- [ ] Database permissions configured (no UPDATE)
- [ ] QuerySet methods for common queries
- [ ] Admin panel (read-only view)

**Test Expectations:**
- **Unit:** Event saves with valid signature
- **Unit:** Cannot modify existing event (raises exception)
- **Unit:** Signature verification passes
- **Integration:** Test immutability at database level

**References:**  
- Audit & Security Architecture, Section 1.2 (AuditEvent Model)

---

### UP-026: Audit Logging Helper Service
**Priority:** P0  
**Area:** Audit  
**Dependencies:** UP-025

**Description:**  
Create audit logging service with helper functions for common event types. Simplifies audit logging throughout codebase.

**Definition of Done:**
- [ ] AuditLogger service class created
- [ ] Methods for common events (log_kyc_view, log_profile_edit, etc.)
- [ ] Context capture (IP address, user agent, session ID)
- [ ] Error handling (log failures, don't block action)
- [ ] Documentation with usage examples

**Test Expectations:**
- **Unit:** Test each helper method (creates audit event)
- **Integration:** Test IP capture and context

**References:**  
- Audit & Security Architecture, Section 1.5 (Query Patterns)

---

### UP-027: KYC Document Encryption
**Priority:** P0  
**Area:** Security  
**Dependencies:** None

**Description:**  
Encrypt KYC id_number field (django-cryptography) and document files (Fernet). Migrate existing plaintext data to encrypted format.

**Definition of Done:**
- [ ] django-cryptography added to dependencies
- [ ] id_number field changed to EncryptedCharField
- [ ] File encryption service created (Fernet)
- [ ] Data migration: encrypt existing records
- [ ] KYC admin panel updated (decrypt on view)
- [ ] Encryption keys in environment variables (not code)

**Test Expectations:**
- **Unit:** Encryption and decryption work correctly
- **Migration:** Existing data encrypted successfully
- **Security:** Plaintext not visible in database dump
- **Performance:** Decryption adds <50ms to KYC view

**References:**  
- Audit & Security Architecture, Section 3.2 (KYC Encryption)

---

### UP-028: KYC Access Logging
**Priority:** P0  
**Area:** Security  
**Dependencies:** UP-025, UP-026

**Description:**  
Add audit logging to all KYC document access points. Every view creates AuditEvent with actor, target user, timestamp, IP.

**Definition of Done:**
- [ ] KYC admin view logs access (AuditEvent created)
- [ ] KYC API endpoint logs access
- [ ] KYC document download logs access
- [ ] Logs include full context (who, what, when, where)
- [ ] Staff notification (optional: email on KYC access)

**Test Expectations:**
- **Integration:** KYC view creates audit event
- **Integration:** Audit event includes actor and target
- **Query:** Can retrieve "who viewed user X's KYC"

**References:**  
- Audit & Security Architecture, Section 3.2 (Access Logging)

---

### UP-029: UserActivity Model & Feed
**Priority:** P1  
**Area:** Audit  
**Dependencies:** UP-008 (Privacy)

**Description:**  
Create UserActivity model for user-facing activity timeline. Display achievements, tournament wins, badges earned. Privacy-aware visibility.

**Definition of Done:**
- [ ] Model created (activity_type, title, description, icon, visibility)
- [ ] Signal creates activities (tournament won, badge earned, etc.)
- [ ] Privacy controls (user can hide activities)
- [ ] Activity feed template (timeline view)
- [ ] API endpoint for activity feed

**Test Expectations:**
- **Unit:** Activity creation works (signal triggered)
- **Template:** Feed renders correctly
- **Privacy:** Hidden activities excluded for non-owners

**References:**  
- Audit & Security Architecture, Section 2 (Activity Feed)

---

### UP-030: Rate Limiting Implementation
**Priority:** P1  
**Area:** Security  
**Dependencies:** None

**Description:**  
Add django-ratelimit to sensitive endpoints. Prevent brute force attacks, scraping, and abuse.

**Definition of Done:**
- [ ] django-ratelimit added to dependencies
- [ ] Rate limits on login (5 attempts per 15 minutes)
- [ ] Rate limits on password reset (3 requests per hour)
- [ ] Rate limits on profile API (60 requests per minute)
- [ ] Rate limit exceeded responses (429 status)
- [ ] Staff bypass configured

**Test Expectations:**
- **Integration:** 6th login attempt blocked (429 response)
- **Integration:** Staff bypass works (unlimited attempts)
- **Security:** Automated bot blocked by rate limits

**References:**  
- Audit & Security Architecture, Section 3.4 (Rate Limiting)

---

## IMPLEMENTATION ORDER

### Critical Path (Must Complete First)
1. UP-001 → UP-002 (Safety pattern)
2. UP-003 → UP-004 → UP-005 (Public ID foundation)
3. UP-006 (Migration)
4. UP-008 → UP-009 (Privacy foundation)
5. UP-011 (OAuth guarantee)

### Parallel Tracks (Can Work Simultaneously)
**Track A (Economy):** UP-014 → UP-015 → UP-016 → UP-017 → UP-018  
**Track B (Stats):** UP-019 → UP-020 → UP-021 → UP-022 → UP-023 → UP-024  
**Track C (Security):** UP-025 → UP-026 → UP-027 → UP-028 → UP-029 → UP-030

### Final Integration
- UP-007 (QuerySet - any time)
- UP-010 (Privacy templates - after UP-009)
- UP-012, UP-013 (OAuth edge cases - after UP-011)

---

## PRIORITY BREAKDOWN

### P0 Items (Blocking Launch) - 12 Items
UP-001, UP-002, UP-003, UP-004, UP-005, UP-006, UP-007, UP-008, UP-009, UP-011, UP-014, UP-015, UP-019, UP-020, UP-021, UP-025, UP-026, UP-027, UP-028

### P1 Items (High Priority) - 13 Items
UP-010, UP-012, UP-013, UP-016, UP-017, UP-022, UP-023, UP-029, UP-030

### P2 Items (Medium Priority) - 5 Items
UP-018, UP-024

---

## AREA BREAKDOWN

**Identity:** UP-002, UP-003, UP-004, UP-005, UP-006, UP-007 (6 items)  
**Privacy:** UP-008, UP-009, UP-010 (3 items)  
**Auth:** UP-011, UP-012, UP-013 (3 items)  
**Economy:** UP-014, UP-015, UP-016, UP-017, UP-018 (5 items)  
**Stats:** UP-019, UP-020, UP-021, UP-022, UP-023, UP-024 (6 items)  
**Audit:** UP-025, UP-026, UP-029 (3 items)  
**Security:** UP-027, UP-028, UP-030 (3 items)  
**Discovery:** UP-001 (1 item)

---

## CROSS-APP TOUCHPOINTS

**Tournaments App:**
- UP-019, UP-020, UP-021 (TournamentParticipation creation)
- UP-023, UP-024 (Tournament history display)

**Economy App:**
- UP-014, UP-015, UP-016 (Transaction sync, wallet balance)
- UP-017, UP-018 (Transaction history)

**Accounts App:**
- UP-011, UP-012, UP-013 (OAuth flow, login)
- UP-030 (Rate limiting on login)

**Teams App:**
- UP-008, UP-009, UP-010 (Privacy for team member profiles)
- UP-029 (Activity: joined team)

**Tournament Ops:**
- UP-020 (Tournament completion triggers participation)
- UP-021 (Stats updates for tournament operators)

---

**END OF BACKLOG**

**Status:** Ready for Implementation  
**Total Items:** 30  
**Estimated Effort:** 6 weeks (21 person-weeks)  
**Next Step:** Begin Phase UP-0 (Discovery)

---

*Document Version: 1.0*  
*Last Updated: December 22, 2025*  
*Author: Platform Architecture Team*
