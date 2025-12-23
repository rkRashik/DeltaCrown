# USER PROFILE MODERNIZATION DECISION LOG (ADRs)

**Platform:** DeltaCrown Esports Tournament Platform  
**Project:** User Profile System Modernization  
**Date:** December 22, 2025  
**Status:** ACTIVE

---

## ABOUT THIS DOCUMENT

This document records all significant architectural decisions made during User Profile modernization. Each decision follows the ADR (Architecture Decision Record) format to ensure rationale is preserved for future reference.

**Purpose:**
- Document why decisions were made (not just what)
- Preserve context for future team members
- Enable informed re-evaluation if requirements change
- Prevent repeating past discussions

**ADR Lifecycle:**
- **PROPOSED:** Under discussion, not yet approved
- **APPROVED:** Accepted and ready for implementation
- **IMPLEMENTED:** Code deployed to production
- **SUPERSEDED:** Replaced by newer decision (link to replacement)
- **DEPRECATED:** No longer valid, avoid using

---

## ADR TEMPLATE

```markdown
# ADR-UP-XXX: [Title]

**Status:** [PROPOSED | APPROVED | IMPLEMENTED | SUPERSEDED | DEPRECATED]  
**Date:** YYYY-MM-DD  
**Author:** [Name]  
**Related ADRs:** [Links to related decisions]

## Context

[What is the issue we're trying to solve? What constraints exist? What are the requirements?]

## Decision

[What is the change we're proposing or have agreed to?]

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Drawback 1]
- [Drawback 2]

### Neutral
- [Trade-off 1]

## Alternatives Considered

### Alternative 1: [Name]
**Pros:** [List]  
**Cons:** [List]  
**Why rejected:** [Reason]

### Alternative 2: [Name]
**Pros:** [List]  
**Cons:** [List]  
**Why rejected:** [Reason]

## Implementation Notes

[Any specific guidance for implementation, references to docs, etc.]

## References

- [Link to architecture doc]
- [Link to audit finding]
```

---

## APPROVED ADRS

### ADR-UP-009: Public ID Format (DC-YY-NNNNNN)

**Status:** ✅ APPROVED → 🟢 IMPLEMENTING (UP-M1)  
**Date:** December 23, 2025  
**Author:** Architecture Team  
**Related ADRs:** ADR-UP-002 (Profile Provisioning Invariant)

#### Context

Current UserProfile identification uses Django auto-increment PK and username. Both have issues:
- **PK:** Exposes user count (security), not human-readable, implementation detail leaked to URLs
- **Username:** Mutable (users can change), contains PII (often real names), not branded
- **UUID:** Exists but not memorable, ugly URLs (`/profile/550e8400-e29b.../`)

**Requirements:**
- Human-readable and memorable
- Branded with DeltaCrown identity
- Immutable (never changes once assigned)
- Non-PII (GDPR compliant)
- URL-friendly (no special characters)
- Unique (globally, forever)

#### Decision

**Format:** DC-YY-NNNNNN  
- DC: DeltaCrown brand prefix (fixed)
- YY: Year (2025 → 25, supports 2000-2099)
- NNNNNN: Sequential counter (000001 to 999999, 6 digits per year)

**Example:** DC-25-000042 (42nd user in 2025)

**Implementation:**
- PublicIDCounter model: year-based counter with atomic F() increment
- select_for_update() locking prevents race conditions
- Unique constraint enforced at database level
- Auto-assigned by profile creation signal
- Retry logic handles concurrent allocation (max 3 attempts)

#### Consequences

**Positive:**
- Human-readable: Users can remember "DC-25-000042"
- Branded: Reinforces DeltaCrown identity in URLs (/u/DC-25-000042/)
- Immutable: Never changes, safe for bookmarks and external references
- Non-PII: No personal information, GDPR compliant
- Capacity: 999,999 users per year (sufficient for growth)
- Year-partitioned: Easy to audit user growth by year

**Negative:**
- Sequential reveals timing: Can infer signup order within year
- Counter overflow: Max 999,999 users per year (manual intervention if exceeded)
- Migration cost: All existing profiles need backfill

**Neutral:**
- Not globally unique without year component (but year+counter is unique)
- Does not replace Django PK (both coexist, PK for internal use)

#### Alternatives Considered

**Alternative 1: UUID (Opaque)**  
**Pros:** Globally unique, no collision risk, no counter management  
**Cons:** Not human-readable, not memorable, ugly URLs  
**Why rejected:** Terrible user experience, defeats purpose of public ID

**Alternative 2: Hashid (Obfuscated PK)**  
**Pros:** Short (6-8 chars), hides actual PK, reversible  
**Cons:** Not branded, still feels random, not truly memorable  
**Why rejected:** No DeltaCrown brand identity

**Alternative 3: Username-based slug**  
**Pros:** User-chosen, completely customizable  
**Cons:** Mutable, PII risk, name squatting, breaks references  
**Why rejected:** Already have slug field (separate from immutable ID)

#### Implementation Notes

**Code Changes:**
- Added `public_id` field to UserProfile (CharField, max_length=15, unique, db_index, null=True)
- Created PublicIDCounter model with year + counter fields
- Created PublicIDGenerator service (apps/user_profile/services/public_id.py)
- Updated ensure_profile() signal to auto-assign public_id
- Model validation: clean() method checks format with regex ^DC-\d{2}-\d{6}$

**Migration Plan:**
1. Add public_id field (nullable)
2. Create PublicIDCounter model
3. Backfill missing profiles
4. Backfill public_id for all profiles
5. Make public_id non-null

**Test Coverage:**
- 8 unit tests planned (format, concurrency, year rollover, overflow)
- Race condition test: 10 threads generating IDs simultaneously

#### References

- UP-02: Public User ID Strategy (target architecture)
- UP-M1 Implementation Plan: Phase 2 (Public ID Generator Service)
- Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_02_PUBLIC_USER_ID_STRATEGY.md

---

### ADR-UP-010: Privacy Enforcement Baseline

**Status:** ✅ APPROVED → 🟢 IMPLEMENTING (UP-M1)  
**Date:** December 23, 2025  
**Author:** Architecture Team  
**Related ADRs:** ADR-UP-006 (Privacy Enforcement in 4 Layers - from UP-0 architecture docs)

#### Context

User Profile contains sensitive PII (email, phone, address, date_of_birth, etc.). Current system has no centralized privacy enforcement:
- Templates access fields directly (`{{ profile.email }}`)
- Views pass full profile dict to templates
- APIs return all fields regardless of viewer
- No role-based visibility (owner vs public vs staff)
- Risk of accidental PII leaks

**Requirements:**
- Centralized privacy policy (single source of truth)
- Role-based field filtering (owner, public, staff)
- Prevent accidental PII exposure
- Extensible for GDPR compliance (UP-M5)
- Testable and auditable

#### Decision

**Created ProfileVisibilityPolicy service** (apps/user_profile/services/privacy_policy.py)

**Field Visibility Rules:**

| Viewer Role | Visible Fields | Example Fields |
|-------------|----------------|----------------|
| Owner (viewer == profile.user) | All fields (57+ fields) | email, phone, address, balance, PII |
| Public (anonymous or non-owner) | PUBLIC_FIELDS only (42 fields) | display_name, avatar, bio, stats |
| Staff (is_staff=True) | All fields + admin metadata | All fields + internal_notes, moderation_flags |

**PII Fields (Hidden by Default - 14 fields):**
- email, phone
- city, postal_code, address
- real_full_name, date_of_birth, nationality, gender
- emergency_contact_* (3 fields)
- deltacoin_balance, lifetime_earnings
- kyc_status, kyc_verified_at

**Methods:**
- `can_view_profile(viewer, profile) -> bool` - Check if viewer can see profile at all
- `get_visible_fields(viewer, profile) -> Set[str]` - Get field names visible to viewer
- `filter_profile_data(viewer, profile, data: dict) -> dict` - Filter dict by visibility
- `is_pii_field(field_name) -> bool` - Check if field is PII
- `redact_pii_for_logs(data: dict) -> dict` - Safe logging helper

#### Consequences

**Positive:**
- Single source of truth for privacy logic (no scattered checks)
- Prevents accidental PII leaks (centralized enforcement)
- Role-based access control (owner/public/staff)
- Testable (12 unit tests planned)
- Extensible for GDPR (UP-M5 will add PrivacySettings toggles)
- Performance: <1ms filtering (in-memory dict operation)

**Negative:**
- Not yet enforced in templates/APIs (UP-M1 baseline only, enforcement in UP-M5)
- Requires code changes to use policy (not automatic)
- May break existing features expecting full profile data

**Neutral:**
- Currently in "audit mode" (policy exists but not enforced)
- Migration path: Phase 1 (implement), Phase 2 (API enforcement), Phase 3 (template enforcement)

#### Alternatives Considered

**Alternative 1: Field-level permissions in model**  
**Pros:** Django-native, integrated with admin  
**Cons:** Inflexible, hard to test, couples model with presentation  
**Why rejected:** Too rigid, doesn't support dynamic rules

**Alternative 2: View-level filtering only**  
**Pros:** Simple, no new services  
**Cons:** Scattered logic, easy to bypass, not reusable  
**Why rejected:** No single source of truth, hard to audit

**Alternative 3: Django Guardian (object-level permissions)**  
**Pros:** Battle-tested, feature-rich  
**Cons:** Overkill for simple visibility rules, adds dependency  
**Why rejected:** Too heavy for our use case

#### Implementation Notes

**Code Changes:**
- Created ProfileVisibilityPolicy service (245 lines)
- Defined field sets: PUBLIC_FIELDS, OWNER_ONLY_FIELDS, STAFF_ONLY_FIELDS
- Helper function: get_profile_context_for_template() for views
- No template/API changes yet (UP-M5 will enforce)

**Usage Example:**
```python
from apps.user_profile.services.privacy_policy import ProfileVisibilityPolicy

# Get visible fields
visible_fields = ProfileVisibilityPolicy.get_visible_fields(request.user, profile)

# Filter profile dict
from django.forms.models import model_to_dict
profile_data = model_to_dict(profile)
filtered = ProfileVisibilityPolicy.filter_profile_data(request.user, profile, profile_data)

# Check if field is PII
if ProfileVisibilityPolicy.is_pii_field('email'):
    # Handle PII field
```

**Test Coverage:**
- 12 unit tests planned (owner/public/staff scenarios, PII hiding, performance)

#### References

- UP-03: Privacy Enforcement Model (target architecture)
- UP-M1 Implementation Plan: Phase 4 (Privacy Enforcement Baseline)
- Documents/UserProfile_CommandCenter_v1/00_TargetArchitecture/UP_03_PRIVACY_ENFORCEMENT_MODEL.md

---

### ADR-UP-008: Safety Accessor Pattern (get_or_create_user_profile)

**Status:** ✅ APPROVED → ✅ IMPLEMENTED  
**Date:** December 23, 2025 (UP-M0)  
**Author:** Developer Agent  
**Related ADRs:** ADR-UP-002 (Profile Provisioning Invariant)

#### Context

Audit revealed 94 locations with `.profile` access patterns. 22 locations (23%) have CRITICAL risk:
- Direct `user.profile` access without existence check
- Will crash with `RelatedObjectDoesNotExist` if profile missing
- Current signal-based provisioning has 1.3% failure rate (OAuth bypass)

**Requirements:**
- Atomic profile creation with race condition handling
- Retry logic for IntegrityError (concurrent creation scenarios)
- No PII exposure in logs (GDPR compliance)
- 100% success rate guarantee (fail fast if provisioning impossible)
- Idempotent (multiple calls return same profile)

**Architecture Reference:**
- UP-01 Section 1: "Invariant: Every User MUST have exactly one UserProfile"
- UP-M0 Audit: 22 CRITICAL locations require safety net

#### Decision

**Created safety accessor utility:** `get_or_create_user_profile(user, max_retries=3)`

**Implementation:**
- Uses `select_for_update()` to lock User row (prevent race conditions)
- Atomic transaction wrapper (all-or-nothing profile creation)
- Retry logic with exponential backoff (0.1s, 0.2s, 0.3s) on IntegrityError
- Returns `(profile, created)` tuple (Django get_or_create pattern)
- Raises `ValueError` for unsaved users (pk=None)
- Raises `RuntimeError` if provisioning fails after max_retries
- Logs creation events with user_id + username only (no PII)

**Also created:**
- `get_user_profile_safe(user)` - Convenience wrapper (profile only, no created flag)
- `@ensure_profile_exists` - View decorator guaranteeing profile exists before execution

#### Consequences

**Positive:**
- 100% profile provisioning guarantee (or explicit failure)
- No more `RelatedObjectDoesNotExist` crashes in production
- Race condition safe (tested with 10 concurrent threads)
- Clear error messages for debugging (fail fast pattern)
- Drop-in replacement for unsafe `user.profile` access
- Monitoring-friendly (log warnings if profile was missing)

**Negative:**
- Extra database query if profile exists (1 SELECT + 1 LOCK)
- Slightly slower than direct access (~5ms overhead)
- Requires code changes in 22 CRITICAL locations (manual migration)

**Neutral:**
- Does not fix root cause (OAuth bypass) - UP-M4 will fix signal gaps
- Temporary solution until 100% signal coverage achieved
- Must be used consistently (cannot enforce at framework level)

#### Alternatives Considered

**Alternative 1: Fix signal coverage only (no safety accessor)**  
**Pros:** Zero runtime overhead, no code changes  
**Cons:** Cannot guarantee 100% (OAuth/SSO edge cases), no retroactive fix for existing missing profiles  
**Why rejected:** Risk too high, leaves 1.3% failure rate

**Alternative 2: Middleware-based profile creation**  
**Pros:** Automatic for all requests, no per-view changes  
**Cons:** Runs on every request (performance), hard to test, no API/CLI coverage  
**Why rejected:** Performance impact, incomplete coverage

**Alternative 3: Database constraint + trigger**  
**Pros:** Enforced at DB level, cannot be bypassed  
**Cons:** PostgreSQL-specific, complex rollback, hard to test  
**Why rejected:** Framework agnostic solution preferred

#### Implementation Notes

**Usage Examples:**

```python
# Before (UNSAFE - will crash if profile missing)
profile = request.user.profile

# After (SAFE - guaranteed to work)
from apps.user_profile.utils import get_user_profile_safe
profile = get_user_profile_safe(request.user)

# Or use decorator
from apps.user_profile.decorators import ensure_profile_exists

@login_required
@ensure_profile_exists
def my_view(request):
    profile = request.user.profile  # Guaranteed to exist
```

**Test Coverage:** 25 tests, 100% line coverage  
**Files Created:**
- `apps/user_profile/utils.py` (145 lines)
- `apps/user_profile/decorators.py` (72 lines)
- `tests/test_profile_safety.py` (290 lines)

#### References

- UP-01: Core User Profile Architecture
- UP-M0 Audit Report: Table 4 (22 CRITICAL locations)
- Documents/UserProfile_CommandCenter_v1/04_Audit/UP_M0_AUDIT_REPORT.md

---

### ADR-UP-001: Public User ID Strategy

**Status:** ✅ APPROVED  
**Date:** December 22, 2025  
**Author:** Architecture Team  
**Related ADRs:** None

#### Context

Current UserProfile uses Django auto-increment PK and username for identification. Both have issues:
- **PK:** Exposes user count (security), not human-readable, implementation detail leaked to URLs
- **Username:** Mutable (users can change), contains PII (often real names), not branded

**Requirements:**
- Human-readable identifier for public profile URLs
- Immutable (never changes once assigned)
- Non-PII (GDPR compliance)
- Branded (DeltaCrown identity)
- Not easily enumerable (prevents scraping)

#### Decision

Implement **sequential public ID** with format `DC-YY-NNNNNN`:
- **DC:** Brand prefix (DeltaCrown)
- **YY:** 2-digit year (25 = 2025)
- **NNNNNN:** 6-digit sequential counter (000001-999999)
- **DO NOT change Django PK** (keep auto-increment, add public_id as separate field)

**Example:** `DC-25-000042` (42nd user registered in 2025)

**Implementation:**
- Add `public_id` CharField to UserProfile (unique, indexed, max_length=15)
- Create PublicIDCounter model (year, counter, unique constraint)
- Generate on profile creation via signal
- Use in URLs: `/profile/DC-25-000042/` (not `/profile/42/`)

#### Consequences

**Positive:**
- Human-memorable: Users can remember their ID ("I'm DC-25-42")
- Branded: Reinforces platform identity
- Non-PII: Safe to share publicly, GDPR compliant
- Immutable: Never changes, safe for URLs and references
- URL-friendly: No special characters, no encoding needed

**Negative:**
- Sequential reveals registration order (not truly random)
- Counter management adds complexity (atomic increment required)
- Year rollover needs handling (Jan 1 reset logic)
- Potential exhaustion (999,999 users per year limit)

**Neutral:**
- Requires database migration (backfill existing users)
- Requires URL routing updates (all profile links)

#### Alternatives Considered

**Alternative 1: UUID (Opaque)**
- Format: `550e8400-e29b-41d4-a716-446655440000`
- **Pros:** Globally unique, no enumeration, no counter management
- **Cons:** Not human-readable, not memorable, not branded, ugly URLs
- **Why rejected:** Terrible UX, users can't remember their ID

**Alternative 2: Hashid (Obfuscated PK)**
- Format: `jR3kLm` (encoded auto-increment ID)
- **Pros:** Short, unique, hides PK
- **Cons:** Not branded, not memorable, encoding adds complexity
- **Why rejected:** No branding, still feels random to users

**Alternative 3: Username as Identifier**
- Format: Current system (`/profile/john_doe/`)
- **Pros:** Already implemented, human-readable
- **Cons:** Mutable (users change username), often contains PII, name squatting issues
- **Why rejected:** Mutability breaks bookmarks and references

**Alternative 4: Sequential with Random Offset**
- Format: `DC-25-847362` (sequential + randomized)
- **Pros:** Hides exact registration order
- **Cons:** Loses "human-memorable" benefit (random numbers hard to remember)
- **Why rejected:** Defeats purpose of sequential IDs

#### Implementation Notes

- Counter stored in PublicIDCounter model (not Redis) for durability
- Use F() expression for atomic increment (prevent race conditions)
- Log counter value daily (detect anomalies, plan capacity)
- Alert at 900,000 users per year (90% capacity warning)
- Year rollover: Jan 1 00:00 UTC creates new counter row (year=2026, counter=0)

#### References

- [Target Architecture, Section 4](../00_TARGET_ARCHITECTURE/USER_PROFILE_TARGET_ARCHITECTURE.md)
- [User Profile Audit Part 1, Section 1.3](../../Audit/UserProfile/USER_PROFILE_AUDIT_PART_1_IDENTITY_AND_AUTH.md)

---

### ADR-UP-002: Profile Provisioning Invariant

**Status:** ✅ APPROVED  
**Date:** December 22, 2025  
**Author:** Architecture Team  
**Related ADRs:** ADR-UP-001

#### Context

**Critical Bug:** Current system allows User to exist without UserProfile due to signal race condition. Audit found 47+ code locations assume profile exists without checking, causing crashes.

**Failure Scenarios:**
- OAuth callback creates User but signal fails (transient DB error)
- Concurrent requests create User before signal fires
- Manual User creation in admin (signal doesn't fire)
- Bulk user import (signals skipped for performance)

**Impact:** 1.3% of OAuth flows result in profile creation failure, users see 500 errors when accessing profile.

#### Decision

Establish **profile provisioning invariant:** Every User MUST have exactly one UserProfile.

**Enforcement Strategy:**
1. **Refactor signal:** Atomic transaction (User + UserProfile created together or both rolled back)
2. **Add retry logic:** 3 attempts with exponential backoff on transient failures
3. **Create safety accessor:** `get_profile_or_create(user)` utility function
4. **Add decorator:** `@ensure_profile_exists` for views requiring profile
5. **Backfill existing:** Data migration ensures all existing Users have profiles

**Invariant:** `User.objects.count() == UserProfile.objects.count()` ALWAYS

#### Consequences

**Positive:**
- Zero profile creation failures (100% guarantee)
- 47+ code locations safe (no more DoesNotExist exceptions)
- Simplified code (no need for if profile exists checks everywhere)
- Better user experience (OAuth flows never crash)

**Negative:**
- Signal complexity increases (atomic transaction, retry logic)
- Performance overhead (atomic transaction lock)
- Migration required (backfill existing users)

**Neutral:**
- Requires code audit (replace direct profile access with safety accessor)
- Requires documentation (onboarding guide for new engineers)

#### Alternatives Considered

**Alternative 1: Lazy Profile Creation**
- Create profile on first access (implicit creation)
- **Pros:** No signal, simpler
- **Cons:** Race conditions (concurrent first access), unclear ownership
- **Why rejected:** Doesn't solve race condition, just moves it

**Alternative 2: OneToOne with User (Merge Models)**
- Add profile fields directly to User model
- **Pros:** No signal, no join, no race condition
- **Cons:** Violates Django best practice (don't modify User), breaks allauth, migration nightmare
- **Why rejected:** Too invasive, breaks third-party integrations

**Alternative 3: Database-Level Constraint**
- Add CHECK constraint (User → Profile FK required)
- **Pros:** Enforced at DB level, impossible to violate
- **Cons:** Django doesn't support this constraint type, PostgreSQL-specific
- **Why rejected:** Not portable, Django ORM doesn't handle gracefully

#### Implementation Notes

- Use `transaction.atomic()` with `select_for_update()` to prevent race conditions
- Log profile creation attempts (success/failure) to AuditEvent
- Add `profile_exists` health check (monitors User vs UserProfile count)
- Alert if count mismatch detected (SLO: 99.99% match rate)

#### References

- [Target Architecture, Section 3.2](../00_TARGET_ARCHITECTURE/USER_PROFILE_TARGET_ARCHITECTURE.md)
- [User Profile Audit Part 1, Section 2.2](../../Audit/UserProfile/USER_PROFILE_AUDIT_PART_1_IDENTITY_AND_AUTH.md)

---

### ADR-UP-003: Ledger-First Economy with Derived Aggregates

**Status:** ✅ APPROVED  
**Date:** December 22, 2025  
**Author:** Architecture Team  
**Related ADRs:** None

#### Context

Current system has **duplicate balance tracking**:
- `DeltaCrownTransaction` model (economy app) - transaction log
- `EconomyWallet.balance` (economy app) - wallet balance
- `UserProfile.deltacoin_balance` (user_profile app) - cached balance

**Problems:**
- No sync mechanism between fields (profile balance never updated)
- Unclear which is source of truth
- Race conditions (concurrent transactions corrupt balance)
- No audit trail (balance changes not logged)

**Requirements:**
- Single source of truth (immutable transaction log)
- Real-time balance updates (users see current balance)
- Fraud detection (audit trail for all changes)
- Performance (balance displayed on every page)

#### Decision

Implement **ledger-first economy** with derived aggregates:

**Source of Truth:** `DeltaCrownTransaction` (immutable ledger)
- All financial actions create transaction record
- Transactions NEVER modified or deleted (append-only)
- Balance = `sum(transactions)` (always queryable)

**Derived Aggregates (Cached):**
- `EconomyWallet.balance` - updated via signal (real-time sync)
- `UserProfile.deltacoin_balance` - updated via signal (display cache)

**Sync Flow:**
1. Transaction created (DeltaCrownTransaction)
2. Signal fires → update EconomyWallet.balance (atomic, F() expression)
3. Signal fires → update UserProfile.deltacoin_balance (cached for templates)
4. Nightly reconciliation: compare cached vs actual, detect drift

#### Consequences

**Positive:**
- Single source of truth (DeltaCrownTransaction = ledger)
- Audit trail complete (all transactions logged)
- Fraud detectable (investigate transaction history)
- Balance always computable (even if cache corrupted)
- Real-time updates (signals fire immediately)

**Negative:**
- Signal cascade complexity (transaction → wallet → profile)
- Potential performance impact (signal overhead)
- Drift possible (if signal fails, cache out of sync)
- Requires reconciliation job (nightly maintenance)

**Neutral:**
- Cached aggregates improve read performance (no sum() on every request)
- Reconciliation adds operational burden (monitoring, alerting)

#### Alternatives Considered

**Alternative 1: Wallet as Source of Truth**
- Store balance only in EconomyWallet, no transaction log
- **Pros:** Simple, fast
- **Cons:** No audit trail, fraud undetectable, disputed transactions unprovable
- **Why rejected:** Legally insufficient, regulatory non-compliant

**Alternative 2: Profile as Source of Truth**
- Store balance only in UserProfile, no wallet
- **Pros:** One less model, simpler
- **Cons:** No separation of concerns (profile shouldn't own economy)
- **Why rejected:** Violates separation of concerns, breaks modularity

**Alternative 3: No Caching (Always Query Ledger)**
- Calculate balance on every request: `sum(transactions)`
- **Pros:** No sync issues, always accurate
- **Cons:** Performance disaster (N+1 queries, slow aggregation)
- **Why rejected:** Unacceptable performance (100ms+ per profile view)

**Alternative 4: Redis Cache**
- Store balance in Redis (fast read)
- **Pros:** Very fast, low latency
- **Cons:** Cache invalidation complexity, Redis failure = balance unavailable
- **Why rejected:** Adds infrastructure dependency, cache invalidation hard

#### Implementation Notes

- Use atomic transactions (transaction creation + wallet update together)
- Use F() expression for balance updates (prevent race conditions)
- Add `skip_signal` flag for bulk operations (prevent signal spam)
- Reconciliation runs nightly at 3 AM UTC (low-traffic period)
- Alert if drift >1% of users (investigate signal failures)

#### References

- [Economy & Stats Architecture, Section 1](../00_TARGET_ARCHITECTURE/USER_PROFILE_ECONOMY_AND_STATS_ARCHITECTURE.md)
- [User Profile Audit Part 2, Section 1](../../Audit/UserProfile/USER_PROFILE_AUDIT_PART_2_ECONOMY_AND_STATS.md)

---

### ADR-UP-004: Stats Snapshot Strategy with Reconciliation

**Status:** ✅ APPROVED  
**Date:** December 22, 2025  
**Author:** Architecture Team  
**Related ADRs:** ADR-UP-003

#### Context

Current system has **no tournament participation tracking**:
- `UserProfile.get_tournament_participation()` returns empty queryset (placeholder)
- Profile displays "Tournaments: 0" for all users (even winners)
- No match history, no placement records, no stats

**Problems:**
- Cannot display tournament history (users want to see achievements)
- Cannot implement achievements (no data to check conditions)
- Cannot generate leaderboards (no placement data)
- Cannot verify prize eligibility (no proof of participation)

**Requirements:**
- Complete tournament history (all participations)
- Fast profile display (no N+1 queries)
- Accurate stats (match participation count)
- Achievement support (query eligibility)

#### Decision

Implement **stats snapshot strategy** with reconciliation:

**Source of Truth:** `TournamentParticipation` model
- Created when tournament completes (status='completed')
- Stores snapshot: placement, placement_tier, matches_played, kills, deaths, prize_amount, xp_earned
- Immutable (disputes handled via soft delete + recreate)

**Cached Aggregates (Profile):**
- `tournaments_played` = count(participations)
- `tournaments_won` = count(participations, placement=1)
- `total_matches_played` = sum(participations.matches_played)
- Updated via signal (participation created → profile stats increment)

**Sync Flow:**
1. Tournament completes (status='completed')
2. Signal fires → create TournamentParticipation records (all participants)
3. Signal fires → update UserProfile stats (increment counters)
4. Nightly reconciliation: compare cached vs actual, detect drift

**Why Snapshot (Not Live Query):**
- Performance: Profile displays stats on every page (can't query 100+ participations each time)
- Scaling: 10K users × 50 tournaments = 500K records (aggregate queries slow)
- Consistency: Stats frozen at tournament end (disputes don't retroactively change leaderboard)

#### Consequences

**Positive:**
- Complete tournament history (queryable, exportable)
- Fast profile display (cached counters, no aggregation)
- Achievement support (query participation records)
- Dispute handling (soft delete + recalculate, preserves audit trail)

**Negative:**
- Snapshot creates delay (participation not visible until tournament completes)
- Signal cascade complexity (tournament → participation → profile)
- Drift possible (if signal fails, stats out of sync)
- Requires reconciliation job (nightly maintenance)

**Neutral:**
- Storage cost (500K records for 10K users, negligible)
- Reconciliation adds operational burden (monitoring, alerting)

#### Alternatives Considered

**Alternative 1: Live Query (No Caching)**
- Query TournamentParticipation on every profile view
- **Pros:** Always accurate, no sync issues
- **Cons:** Performance disaster (N+1 queries, slow aggregation)
- **Why rejected:** Unacceptable performance (500ms+ per profile view)

**Alternative 2: Event Sourcing**
- Store all tournament events (match start, match end, kill, death)
- **Pros:** Complete audit trail, replay capability
- **Cons:** Massive data volume (1M+ events per tournament), query complexity
- **Why rejected:** Over-engineering, premature optimization

**Alternative 3: Materialized View (Database)**
- Use PostgreSQL materialized view for aggregates
- **Pros:** Database-level optimization, fast queries
- **Cons:** PostgreSQL-specific (not portable), refresh timing issues
- **Why rejected:** Tight coupling to database, limits future flexibility

#### Implementation Notes

- TournamentParticipation created in async task (don't block tournament completion)
- Soft delete disputes: `is_deleted=True` (preserve history)
- Recalculation: delete old → create new → recalculate stats (atomic)
- Reconciliation compares: `profile.tournaments_played` vs `count(participations)`
- Alert if drift >5% of users (investigate signal failures)

#### References

- [Economy & Stats Architecture, Section 2-3](../00_TARGET_ARCHITECTURE/USER_PROFILE_ECONOMY_AND_STATS_ARCHITECTURE.md)
- [User Profile Audit Part 2, Section 2](../../Audit/UserProfile/USER_PROFILE_AUDIT_PART_2_ECONOMY_AND_STATS.md)

---

### ADR-UP-005: Audit Log vs User Activity Feed Separation

**Status:** ✅ APPROVED  
**Date:** December 22, 2025  
**Author:** Architecture Team  
**Related ADRs:** None

#### Context

Need to track two distinct types of events:
1. **Audit events:** Staff actions, security events, compliance (legal requirement)
2. **User activities:** Achievements, milestones, social feed (UX feature)

**Problems if mixed:**
- Audit log polluted with non-security events (harder to investigate fraud)
- User feed exposes security-sensitive events (creepy: "Admin viewed your profile")
- Different retention requirements (audit: 7 years, activity: 90 days)
- Different audiences (audit: staff/regulators, activity: users/public)

**Requirements:**
- Audit log: immutable, comprehensive, staff-only, long retention
- Activity feed: user-facing, filterable by user, short retention, privacy-aware

#### Decision

Implement **two separate models:**

**AuditEvent (Security & Compliance):**
- Purpose: Legal defense, fraud investigation, compliance
- Audience: Staff, regulators, investigators
- Retention: 1-7 years (by event type)
- Immutability: REQUIRED (append-only, HMAC-signed)
- Content: ALL actions (even sensitive: KYC views, balance adjustments)
- Examples: "Admin john@dc.com viewed KYC for user 123 from IP 192.168.1.1"

**UserActivity (UX & Social):**
- Purpose: User timeline, achievements, social proof
- Audience: Profile owner, public (if allowed)
- Retention: 90 days (rolling window)
- Immutability: NOT REQUIRED (user can hide activities)
- Content: Filtered, user-friendly (only public-safe events)
- Examples: "🏆 Won Tournament: Valorant Open 2025"

**No overlap:** Events belong to ONE model, never both.

#### Consequences

**Positive:**
- Clear separation of concerns (security vs UX)
- Appropriate retention (audit: years, activity: months)
- Correct audience (audit: staff, activity: users)
- Better performance (activity queries small dataset)
- Privacy compliant (users don't see audit trails)

**Negative:**
- Two models to maintain (more code)
- Potential confusion (which model for event X?)
- Some events might feel like both (need clear guidelines)

**Neutral:**
- Storage cost negligible (audit: large but sparse, activity: small and dense)

#### Alternatives Considered

**Alternative 1: Single Unified Model**
- One "Event" model with type field (audit vs activity)
- **Pros:** Single model, simpler
- **Cons:** Mixed concerns, complex queries, retention conflicts
- **Why rejected:** Violates single responsibility principle

**Alternative 2: Audit Log Only**
- Only AuditEvent, expose filtered view to users
- **Pros:** Single source of truth
- **Cons:** Immutability conflicts (users can't hide activities), privacy risk (expose audit trails)
- **Why rejected:** Security risk, UX poor

**Alternative 3: Activity Feed Only**
- Only UserActivity, hope it's enough for compliance
- **Pros:** Simpler, one model
- **Cons:** Not legally defensible (users can delete, no immutability)
- **Why rejected:** Legally insufficient, regulatory non-compliant

#### Implementation Notes

**Decision Matrix (Which model?):**

| Event Type | Model | Rationale |
|------------|-------|-----------|
| KYC document viewed | AuditEvent | Security, staff action |
| Profile PII edited | AuditEvent | Fraud detection, compliance |
| Balance adjusted | AuditEvent | Financial audit |
| Tournament won | UserActivity | Achievement, social |
| Badge earned | UserActivity | Achievement, social |
| Level up | UserActivity | Milestone, social |
| Team joined | UserActivity | Social, public-safe |
| Login (successful) | Neither | Handled by auth system |
| Login (failed) | AuditEvent | Security, brute force detection |

**General Rule:** If staff/regulator needs to know → AuditEvent. If user wants to show off → UserActivity.

#### References

- [Audit & Security Architecture, Section 1-2](../00_TARGET_ARCHITECTURE/USER_PROFILE_AUDIT_AND_SECURITY_ARCHITECTURE.md)
- [User Profile Audit Part 3, Section 4](../../Audit/UserProfile/USER_PROFILE_AUDIT_PART_3_SECURITY_AND_RISKS.md)

---

### ADR-UP-006: Privacy Enforcement in 4 Layers

**Status:** ✅ APPROVED  
**Date:** December 22, 2025  
**Author:** Architecture Team  
**Related ADRs:** None

#### Context

**Critical Security Gap:** Privacy toggles work on web templates but 12 API endpoints bypass privacy checks, exposing PII (email, full name, DOB).

**Current State:**
- Template layer: Privacy checks implemented (conditional display)
- API layer: NO privacy checks (returns all fields to anyone)
- Service layer: NO privacy checks (functions return raw data)
- QuerySet layer: NO privacy checks (queries return all users)

**Impact:** Users believe privacy settings work (toggle UI says "hidden") but API leaks data to anyone with endpoint URL.

#### Decision

Implement **4-layer privacy enforcement:**

**Layer 1: Template (Django Templates)**
- Use `{% privacy_filter %}` template tag
- Conditionally render PII fields based on viewer
- Fallback display: "Hidden by user"

**Layer 2: Serializer (DRF)**
- All profile serializers inherit from `PrivacyAwareProfileSerializer`
- Base class filters fields based on viewer identity
- Fields removed from response (not just hidden)

**Layer 3: Service (Business Logic)**
- Service functions accept `viewer` parameter
- Return privacy-filtered data
- Example: `get_profile_data(user, viewer)`

**Layer 4: QuerySet (Database)**
- QuerySet methods: `with_privacy_for(viewer)`
- Apply privacy filters at query level
- Example: `UserProfile.objects.with_privacy_for(request.user)`

**Enforcement Order:** QuerySet → Service → Serializer → Template (defense in depth)

**Privacy Settings (6 Toggles):**
- `show_full_name` (default: False)
- `show_email` (default: False)
- `show_stats` (default: True)
- `show_transactions` (default: False)
- `show_match_history` (default: True)
- `visibility_level` (public/followers/private)

#### Consequences

**Positive:**
- Comprehensive enforcement (4 layers, no bypass)
- API privacy guaranteed (serializer filters fields)
- Defense in depth (multiple checkpoints)
- User trust (privacy actually works)
- GDPR compliant (PII hidden by default)

**Negative:**
- Complexity (4 layers to maintain)
- Performance overhead (privacy checks on every request)
- Refactor required (12 API endpoints need updates)
- Testing burden (test each layer + combinations)

**Neutral:**
- Staff bypass (staff always see all fields for audit)
- Caching complexity (cache varies by viewer)

#### Alternatives Considered

**Alternative 1: Template-Only Enforcement**
- Only check privacy in templates
- **Pros:** Simple, already partially implemented
- **Cons:** APIs bypass completely (current bug)
- **Why rejected:** Insufficient, security vulnerability

**Alternative 2: Middleware Enforcement**
- Single middleware strips PII from all responses
- **Pros:** Centralized, one place to maintain
- **Cons:** Too coarse (can't differentiate endpoints), performance overhead on all requests
- **Why rejected:** Not granular enough, affects non-profile endpoints

**Alternative 3: Database Row-Level Security**
- PostgreSQL RLS policies enforce privacy
- **Pros:** Database-level guarantee, impossible to bypass
- **Cons:** PostgreSQL-specific, Django ORM doesn't integrate well, complex policies
- **Why rejected:** Not portable, Django ecosystem doesn't support

#### Implementation Notes

- Create `PrivacySettings` model (OneToOne with UserProfile)
- Default all PII hidden (privacy-first)
- Staff always bypass (for audit/support)
- Anonymous users see minimal fields (public_id, username, avatar only)
- Cache privacy settings (avoid N+1 queries)

**Serializer Example:**
```python
class PrivacyAwareProfileSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        viewer = self.context.get('request').user
        
        if not can_view_email(viewer, instance):
            data.pop('email', None)
        if not can_view_full_name(viewer, instance):
            data.pop('full_name', None)
        
        return data
```

#### References

- [Target Architecture, Section 5](../00_TARGET_ARCHITECTURE/USER_PROFILE_TARGET_ARCHITECTURE.md)
- [User Profile Audit Part 3, Section 2](../../Audit/UserProfile/USER_PROFILE_AUDIT_PART_3_SECURITY_AND_RISKS.md)

---

### ADR-UP-007: KYC Field Encryption + Access Logging

**Status:** ✅ APPROVED  
**Date:** December 22, 2025  
**Author:** Architecture Team  
**Related ADRs:** ADR-UP-005

#### Context

**Critical Compliance Violation:** KYC documents stored in plaintext:
- `id_number` field (CharField) - national ID numbers unencrypted
- Document files (JPEG) - uploaded to media/ folder readable by web server
- Access not logged - no record of who viewed KYC documents

**Regulatory Requirements:**
- GDPR Article 32: Encryption of personal data (REQUIRED)
- Bangladesh DPA: Secure storage of identity documents (REQUIRED)
- Financial compliance: Audit trail for KYC access (REQUIRED)

**Impact:** Platform unlaunchable due to regulatory non-compliance, potential fines €20M+ (GDPR) if breached.

#### Decision

Implement **KYC encryption + access logging:**

**Field Encryption:**
- Use `django-cryptography` package
- Change `id_number` to `EncryptedCharField`
- Encryption key in environment variable (not code)
- Key rotation supported (re-encrypt on demand)

**File Encryption:**
- Use Fernet cipher (symmetric encryption)
- Encrypt files on upload (before saving to disk)
- Store files as `.enc` (cannot open without decryption)
- Encryption key per document (stored in VerificationRecord)

**Access Logging:**
- Every KYC view creates AuditEvent
- Log: actor_id, target_user_id, ip_address, timestamp
- Log includes document type (front, back, selfie)
- Immutable audit trail (cannot be deleted)

**Access Control:**
- Only staff can view KYC documents (permission check)
- Document URLs expire after 5 minutes (signed URLs)
- No direct file access (files stored outside web root)

#### Consequences

**Positive:**
- Regulatory compliant (GDPR, Bangladesh DPA)
- Audit trail complete (every access logged)
- Insider fraud detectable (log shows who viewed documents)
- Data breach mitigated (encrypted files useless without keys)

**Negative:**
- Performance overhead (encrypt/decrypt on access)
- Key management complexity (secure storage, rotation)
- Migration required (encrypt existing plaintext data)
- Admin UX slower (decrypt on view adds latency)

**Neutral:**
- Storage cost negligible (encrypted files same size)
- Backup complexity (must backup encryption keys separately)

#### Alternatives Considered

**Alternative 1: Filesystem Encryption (LUKS)**
- Encrypt entire disk/volume
- **Pros:** OS-level, transparent
- **Cons:** All-or-nothing (can't rotate keys per document), requires root access
- **Why rejected:** Not granular, key rotation impossible

**Alternative 2: Database Encryption (TDE)**
- PostgreSQL Transparent Data Encryption
- **Pros:** Database-level, no app changes
- **Cons:** Encrypts all columns (not selective), PostgreSQL 15+ only
- **Why rejected:** Too coarse, not portable

**Alternative 3: HSM (Hardware Security Module)**
- Store encryption keys in HSM (Thales, AWS CloudHSM)
- **Pros:** Maximum security, key never leaves hardware
- **Cons:** Expensive ($1000/month), complex setup, vendor lock-in
- **Why rejected:** Over-engineering for MVP, consider for scale

**Alternative 4: No Encryption (Risk Acceptance)**
- Store plaintext, rely on perimeter security
- **Pros:** Simple, fast
- **Cons:** Regulatory non-compliant, illegal in EU/Bangladesh
- **Why rejected:** Platform unlaunchable, fines exceed revenue

#### Implementation Notes

- Use django-cryptography `EncryptedCharField` for `id_number`
- Fernet encryption for files (symmetric, fast)
- Key hierarchy: master key (env var) → document keys (database)
- Access logging via AuditEvent model (immutable)
- Key rotation: re-encrypt all documents with new key (management command)
- Decryption only when explicitly accessed (lazy loading)
- Admin panel: decrypt on view, show for 5 minutes, re-encrypt on save

**Encryption Flow:**
```
Upload → Encrypt (Fernet) → Save to disk (.enc) → Store key in DB
View → Retrieve key → Decrypt → Display (5 min timeout) → Discard decrypted data
```

#### References

- [Audit & Security Architecture, Section 3.2](../00_TARGET_ARCHITECTURE/USER_PROFILE_AUDIT_AND_SECURITY_ARCHITECTURE.md)
- [User Profile Audit Part 3, Section 3](../../Audit/UserProfile/USER_PROFILE_AUDIT_PART_3_SECURITY_AND_RISKS.md)

---

## DECISION PIPELINE (Proposed ADRs)

**No proposed ADRs at this time.**

When new architectural questions arise during implementation, create proposed ADR here for team discussion.

---

## SUPERSEDED ADRS

**No superseded ADRs yet.**

When decisions are replaced, move them here with link to replacement.

---

## USAGE GUIDELINES

**When to Create ADR:**
- Choosing between multiple architectural approaches
- Making trade-offs (performance vs simplicity)
- Establishing patterns (privacy enforcement, sync strategy)
- Rejecting obvious alternatives (document why NOT chosen)

**When NOT to Create ADR:**
- Implementation details (variable names, file structure)
- Temporary decisions (can change without impact)
- Obvious choices (no alternatives considered)

**ADR Review Process:**
1. Engineer creates ADR (status: PROPOSED)
2. Team reviews (async comments, sync discussion)
3. Consensus reached (approved by 2+ senior engineers)
4. Status changed to APPROVED
5. Implementation proceeds
6. Status changed to IMPLEMENTED after deployment

---

## ADR-UP-011: Event-Sourced User Activity Pattern

**Date:** 2025-12-23  
**Status:** ✅ IMPLEMENTED  
**Context:** UP-M2 (Stats + History)  
**Decision Owner:** Platform Architecture

**Problem:**
UserProfile stats (tournaments_played, matches_won, lifetime_earnings) are manually mutated throughout the codebase, leading to:
1. **No audit trail:** Cannot answer "what did user do 6 months ago?"
2. **Desynchronization risk:** Stats incremented manually (tournaments_played++), can drift from reality
3. **No authoritative source:** TournamentResult stores winner, but no User→Tournament→Outcome link
4. **Stats not recomputable:** If corrupted, cannot rebuild from historical data

**Options Considered:**

**Option 1: Immutable Event Log (CHOSEN)**
- Create UserActivity model (append-only event log)
- Event types: TOURNAMENT_JOINED, MATCH_WON, COINS_EARNED, etc.
- Stats derived from events (recomputable)
- Pros: Infinite audit trail, stats always recomputable, scalable (append-only)
- Cons: Requires backfill migration, more storage (events never deleted)

**Option 2: Manual Stats Updates with Soft Delete**
- Keep current approach, add soft delete to stats
- Pros: Minimal code changes
- Cons: Still no audit trail, stats not recomputable, desync risk remains

**Option 3: Stats Snapshots (Daily/Monthly)**
- Store UserProfileStats snapshots at regular intervals
- Pros: Point-in-time history
- Cons: Coarse granularity, still no event-level detail, complex rollup logic

**Decision:**
Implement **Option 1: Event-Sourced Activity Log** with 3-tier data hierarchy:
- **Tier 1: Events (Source of Truth)** - UserActivity (immutable, append-only)
- **Tier 2: Stats (Derived Projection)** - UserProfileStats (recomputed from events)
- **Tier 3: Profile (Display Cache)** - UserProfile (updated from stats)

**Implementation:**
```python
# Immutable event log (ACTUAL DB SCHEMA)
class UserActivity(models.Model):
    event_type = models.CharField(choices=EventType.choices)
    user = models.ForeignKey(User)
    timestamp = models.DateTimeField(auto_now_add=True)
    source_model = models.CharField()  # tournament/match/economy
    source_id = models.IntegerField()
    metadata = models.JSONField()  # Flexible metadata
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['source_model', 'source_id', 'event_type', 'user'],
                name='unique_source_event'  # Idempotency guarantee
            )
        ]

# Derived stats (recomputable from events)
class UserProfileStats(models.Model):
    user_profile = models.OneToOneField(UserProfile)
    tournaments_played = models.IntegerField()  # COUNT(events WHERE type=TOURNAMENT_JOINED)
    matches_won = models.IntegerField()  # COUNT(events WHERE type=MATCH_WON)
    computed_at = models.DateTimeField()  # Staleness detection
    
    @classmethod
    def recompute_from_events(cls, user_id):
        # Rebuild stats from scratch by aggregating UserActivity events
```

**Consequences:**
- **Positive:**
  - Infinite audit trail (can answer "what happened 2 years ago?")
  - Stats always accurate (recompute from events if desync suspected)
  - Scalable (append-only writes, partitionable by timestamp)
  - Compliance-friendly (immutable audit log for GDPR/finance regulations)
- **Negative:**
  - Storage cost (events never deleted, 1M+ events/year expected)
  - Backfill complexity (must generate events from historical Registration/Match records)
  - Read complexity (queries must aggregate events, requires indexed queries)

**Rollback Strategy:**
- Event log append-only (safe to keep even if feature disabled)
- Stats calculator can be toggled off (revert to manual updates)
- Profile sync can be disabled via feature flag

**Monitoring:**
- Alert if UserActivity table grows >1GB/month (partition if needed)
- Alert if stats recomputation takes >5 seconds (optimize aggregation queries)
- Alert if event creation fails (signal handlers must be idempotent)

**Related Decisions:**
- UP-M3 will use UserActivity events for economy sync (COINS_EARNED/SPENT tracking)
- UP-M5 audit logs will reference UserActivity for compliance

---

## ADR-UP-012: Idempotency Key Strategy for User Activity Events

**Date:** 2025-12-23  
**Status:** ✅ IMPLEMENTED  
**Context:** UP-M2 (Stats + History)  
**Decision Owner:** Platform Architecture

**Problem:**
Event recording can be triggered multiple times due to:
1. **Signal retries:** Django signals may fire multiple times for same object (transaction rollback/retry)
2. **Backfill re-runs:** Management command must be safe to run multiple times
3. **Race conditions:** Multiple workers processing same Match completion concurrently

Without idempotency, duplicate events would:
- Inflate stats (tournaments_played = 2 for same tournament)
- Break audit trail integrity (cannot trust event count)
- Complicate analytics (must deduplicate before queries)

**Options Considered:**

**Option 1: Composite Unique Constraint (CHOSEN)**
- Database-enforced unique constraint on (source_model, source_id, event_type, user)
- Example: Only 1 TOURNAMENT_JOINED event per (user, tournament_id)
- Pros: Atomic, database-guaranteed, works across processes
- Cons: Requires get_or_create() pattern (2 queries for new events)

**Option 2: UUID Per Event**
- Assign UUID to each event, caller must generate UUID
- Pros: Explicit deduplication control
- Cons: Caller must remember UUID (stateful), no protection if UUID forgotten

**Option 3: Timestamp-Based Deduplication**
- Only allow 1 event per (user, type, minute)
- Pros: Simple
- Cons: Not reliable (user can join 2 tournaments in same minute), time zones

**Decision:**
Implement **Option 1: Composite Unique Constraint** with get_or_create() pattern.

**Implementation:**
```python
# Database constraint (enforced at DB level)
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['source_model', 'source_id', 'event_type', 'user'],
            name='unique_source_event'
        )
    ]

# Service layer (safe for re-runs)
def record_event(self, event_type, user_id, source_model, source_id, metadata):
    event, created = UserActivity.objects.get_or_create(
        event_type=event_type,
        user_id=user_id,
        source_model=source_model,
        source_id=source_id,
        defaults={'metadata': metadata, 'timestamp': now()}
    )
    return event  # Returns existing event if duplicate
```

**Consequences:**
- **Positive:**
  - Mathematically guaranteed (database enforces uniqueness)
  - Safe for retries (backfill command can run 10 times, only creates once)
  - Works across processes (multiple workers can't create duplicates)
  - Explicit semantics (get_or_create makes idempotency obvious in code)
- **Negative:**
  - Requires 2 queries for new events (SELECT + INSERT vs just INSERT)
  - Constraint violation exceptions must be handled (IntegrityError → get existing)
  - Cannot distinguish "retry" from "legitimate second event" (but that's correct behavior)

**Verification:**
Backfill command dry-run tested (ran twice, second run showed 0 new events created).

**Related Decisions:**
- ADR-UP-011: Event-Sourced pattern (provides source_model/source_id for constraint)
- UP-M3: Economy sync will rely on same idempotency pattern

---

## ADR-UP-013: Stats Derived Projection Rules

**Date:** 2025-12-23  
**Status:** ✅ IMPLEMENTED  
**Context:** UP-M2 (Stats + History)  
**Decision Owner:** Platform Architecture

**Problem:**
UserProfileStats contains computed values (tournaments_played, matches_won, total_earnings). If stats can be manually edited, they become unreliable:
1. **Desync risk:** Manual update bypasses event log (stats no longer match events)
2. **No rollback:** If bad data entered, cannot restore (no event log to recompute from)
3. **Compliance issue:** Audit trail broken (cannot prove stats accuracy)

**Options Considered:**

**Option 1: Block All Manual Updates (CHOSEN)**
- UserProfileStats.save() only allowed for initial creation
- Updates MUST use recompute_from_events() (rebuilds from UserActivity)
- Pros: Stats always match events, disaster recovery trivial (just recompute)
- Cons: Cannot hotfix stats (must fix event log instead)

**Option 2: Allow Manual Updates with Audit Log**
- Record all stat changes in separate audit table
- Pros: Flexible (can override stats if needed)
- Cons: Two sources of truth (events vs manual edits), unclear which is correct

**Option 3: Versioned Stats (Copy-On-Write)**
- Create new stats record on each update (immutable history)
- Pros: Full history of stat changes
- Cons: Complex queries (must find latest version), storage overhead

**Decision:**
Implement **Option 1: Block Manual Updates** with escape hatch for admin operations.

**Implementation:**
```python
class UserProfileStats(models.Model):
    # ... fields ...
    
    def save(self, *args, **kwargs):
        # Block updates (only allow creation)
        if self.pk and not kwargs.pop('_allow_direct_save', False):
            raise ValueError(
                "UserProfileStats cannot be updated directly. "
                "Use StatsUpdateService.recompute_stats_for_user() instead."
            )
        super().save(*args, **kwargs)
    
    @classmethod
    def recompute_from_events(cls, user_id):
        # Aggregate UserActivity events → stats
        stats = cls.objects.get(user_profile__user_id=user_id)
        stats.tournaments_played = UserActivity.objects.filter(
            user_id=user_id, event_type='TOURNAMENT_JOINED'
        ).count()
        # ... aggregate other stats ...
        stats.save(_allow_direct_save=True)  # Bypass protection
```

**Consequences:**
- **Positive:**
  - Stats always recomputable (disaster recovery: just rerun recompute_from_events())
  - Single source of truth (event log is authoritative)
  - Prevents accidental corruption (save() will raise error)
  - Compliance-friendly (stats proven to match audit log)
- **Negative:**
  - Cannot hotfix stats (must fix event log first, then recompute)
  - Admin operations need _allow_direct_save=True (escape hatch)
  - Recomputation may be slow for users with 1M+ events (requires optimization)

**Verification:**
Test suite confirms save() raises ValueError for updates (test_stats_service.py).

**Related Decisions:**
- ADR-UP-011: Event-Sourced pattern (provides events to aggregate)
- ADR-UP-012: Idempotency (ensures event counts are accurate)

---

### ADR-UP-016: Signal Timing for Economy Sync

**Status:** ✅ IMPLEMENTED  
**Date:** December 23, 2025  
**Author:** Platform Architecture Team  
**Related ADRs:** ADR-UP-014 (Signal Integration for Economy Sync)

#### Context

Economy sync signal (`on_economy_transaction`) was failing to sync profile balance correctly:
- Signal fires on `DeltaCrownTransaction.post_save` 
- Transaction model's `save()` method calls `wallet.recalc_and_save()` at END of save
- Django's `post_save` signal fires immediately after `super().save()` but BEFORE remaining code in save method
- Result: Signal saw stale `wallet.cached_balance=0` instead of updated balance

**Requirements:**
- Profile must sync immediately when transaction created
- Wallet balance must be current (not stale)
- Signal must be idempotent (safe to call multiple times)
- No race conditions or double-sync issues

#### Decision

Signal handler explicitly calls `wallet.recalc_and_save()` BEFORE calling `sync_wallet_to_profile()`:

```python
@receiver(post_save, sender='economy.DeltaCrownTransaction')
def on_economy_transaction(sender, instance, created, **kwargs):
    if not created:
        return
    
    # Ensure wallet.cached_balance is current
    instance.wallet.recalc_and_save()
    
    # Now sync to profile with up-to-date balance
    sync_wallet_to_profile(instance.wallet_id)
```

**Guards:**
- Only act on `created=True` (new transactions only)
- Signal catches all exceptions (non-critical, won't block transaction creation)
- Sync service is idempotent (calling twice is safe)

#### Consequences

**Positive:**
- Profile balance syncs correctly on every transaction
- No stale data issues
- Signal is simple and explicit (no hidden timing dependencies)

**Negative:**
- Wallet recalc happens twice: once in signal, once at end of transaction.save()
- Minor performance impact (extra SELECT FOR UPDATE + ledger sum)

**Neutral:**
- Signal assumes wallet.recalc_and_save() is fast (it locks one row, sums ledger)
- Alternative (transaction.on_commit()) would be cleaner but requires Django 3.2+ patterns

#### Alternatives Considered

**Alternative 1: Move wallet.recalc_and_save() BEFORE super().save() in transaction model**
- **Pros:** Signal would see correct balance, no double-recalc
- **Cons:** Breaks transaction immutability pattern (recalc should happen AFTER ledger write)
- **Why rejected:** Architectural violation (transaction must be saved before wallet updates)

**Alternative 2: Use transaction.on_commit() hook instead of post_save**
- **Pros:** Guaranteed to run after ALL save logic completes
- **Cons:** Requires refactoring signal registration, more complex testing
- **Why rejected:** Overkill for this issue, post_save is standard pattern

**Alternative 3: Remove wallet.recalc_and_save() from transaction.save(), only rely on signal**
- **Pros:** No double-recalc, cleaner separation of concerns
- **Cons:** Breaks existing code that creates transactions without signals enabled
- **Why rejected:** Too risky, signals can be disabled/fail

#### Implementation Notes

**Files Modified:**
- `apps/user_profile/signals/activity_signals.py` (lines 173-177)

**Future Improvement:**
- Consider `transaction.on_commit()` pattern for cleaner timing control
- Monitor performance impact of double-recalc (likely negligible, but profile if needed)
- Add metrics: signal execution time, sync success rate

**Testing:**
- Test: `test_transaction_create_triggers_sync` - verifies signal syncs profile correctly
- Test: `test_sync_updates_profile_balance` - verifies sync service works independently
- Test: `test_sync_is_idempotent` - verifies calling sync twice is safe

#### References

- [Django Signals Documentation](https://docs.djangoproject.com/en/5.0/topics/signals/)
- [Django transaction.on_commit()](https://docs.djangoproject.com/en/5.0/topics/db/transactions/#django.db.transaction.on_commit)
- UP-FIX-05 debug session (wallet.cached_balance timing issue)

---

**END OF DECISION LOG**

**Status:** Active  
**Total ADRs:** 14 approved, 0 proposed, 0 superseded  
**Last Updated:** December 23, 2025

---

*Document Version: 1.2*  
*Maintained by: Architecture Team*
