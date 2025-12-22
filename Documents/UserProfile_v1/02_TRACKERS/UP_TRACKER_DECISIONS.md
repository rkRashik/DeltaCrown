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

**END OF DECISION LOG**

**Status:** Active  
**Total ADRs:** 7 approved, 0 proposed, 0 superseded  
**Last Updated:** December 22, 2025

---

*Document Version: 1.0*  
*Maintained by: Architecture Team*
