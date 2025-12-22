# UP-02: PUBLIC USER ID STRATEGY

**Platform:** DeltaCrown Esports Tournament Platform  
**Date:** December 22, 2025  
**Status:** APPROVED FOR IMPLEMENTATION

---

## 1. WHY WE NEED A PUBLIC USER ID

### Current State Problems

**Using Django Auto-Increment PK (`User.id`):**
- Exposes platform growth metrics (user 1, 2, 3... reveals total user count)
- Implementation detail leaked to URLs and APIs
- Not human-readable or memorable
- No brand identity

**Using Username:**
- Mutable (users can change username)
- Contains PII (users often use real names)
- Name squatting issues (desirable names taken by inactive users)
- GDPR risk (username may be personal data)
- Breaks bookmarks and external references when changed

### Requirements

**Public User ID must be:**
- Immutable (never changes once assigned)
- Non-PII (safe to share publicly, GDPR compliant)
- Human-readable (users can remember and share)
- Branded (reinforces DeltaCrown identity)
- URL-friendly (no special characters, no encoding needed)
- Unique (globally, forever)

**Public User ID must NOT:**
- Replace Django's auto-increment PK (keep for database efficiency)
- Be guessable in a way that enables enumeration attacks
- Contain sensitive information

---

## 2. OPTIONS CONSIDERED

### Option A: UUID (Opaque Identifier)

**Format:** `550e8400-e29b-41d4-a716-446655440000`

**Pros:**
- Globally unique (no collision risk)
- No enumeration possible (random)
- No counter management needed
- Database-friendly (indexed efficiently)

**Cons:**
- Not human-readable (impossible to remember)
- Not memorable (users can't share verbally)
- Ugly URLs (`/profile/550e8400-e29b-41d4-a716-446655440000/`)
- No brand identity
- Poor UX (users can't type or remember their ID)

**Verdict:** Rejected due to terrible user experience.

---

### Option B: Hashid (Obfuscated Auto-Increment)

**Format:** `jR3kLm` (encoded PK: 12345)

**Pros:**
- Short (6-8 characters)
- Hides actual PK value
- Reversible (decode to PK for lookups)
- URL-friendly

**Cons:**
- Not branded (no DeltaCrown identity)
- Still feels random to users
- Encoding/decoding adds complexity
- Not truly human-memorable
- Pattern recognition possible (enumeration harder but not impossible)

**Verdict:** Rejected due to lack of branding and memorability.

---

### Option C: Sequential Branded ID (RECOMMENDED)

**Format:** `DC-YY-NNNNNN`
- **DC:** Brand prefix (DeltaCrown)
- **YY:** 2-digit year (25 = 2025, 26 = 2026)
- **NNNNNN:** 6-digit sequential counter (000001-999999)

**Examples:**
- `DC-25-000001` (first user in 2025)
- `DC-25-000042` (42nd user in 2025)
- `DC-26-000001` (first user in 2026, counter resets)

**Pros:**
- Human-readable and memorable ("I'm DC-25-42")
- Branded (reinforces DeltaCrown identity)
- Shows registration cohort (users from 2025 vs 2026)
- URL-friendly: `/profile/DC-25-000042/`
- Verbally shareable ("DC twenty-five, forty-two")
- Creates sense of community (early users have lower numbers)

**Cons:**
- Sequential reveals registration order (not truly random)
- Counter management required (atomic increment)
- Year rollover logic needed (Jan 1 reset)
- Limited capacity (999,999 users per year)

**Verdict:** RECOMMENDED. Benefits outweigh risks for esports community platform.

---

## 3. RECOMMENDED OPTION: SEQUENTIAL BRANDED ID

### Decision

**Adopt format: DC-YY-NNNNNN**

### Rationale

**User Experience:**
- Early adopters get lower numbers (status symbol in gaming communities)
- Users can remember and share their ID
- Creates conversation starters ("I'm a DC-25 user!")

**Brand Identity:**
- Every profile URL reinforces DeltaCrown brand
- External links (social media, Discord) advertise platform

**Technical:**
- Simple implementation (database counter)
- Efficient lookups (indexed CharField)
- No encoding/decoding overhead

**Community Building:**
- Registration year creates cohorts ("OG 2025 users")
- Lower numbers become status symbol (gamification)
- Encourages early adoption

---

## 4. FORMAT SPECIFICATION

### Format Pattern

**Pattern:** `DC-YY-NNNNNN`

**Regex:** `^DC-\d{2}-\d{6}$`

### Components

**Prefix (DC):**
- Fixed: "DC" (DeltaCrown brand)
- Always uppercase
- Non-negotiable

**Year (YY):**
- 2-digit year: 25, 26, 27...
- Represents registration year
- Rolls over Jan 1 00:00 UTC

**Counter (NNNNNN):**
- 6-digit zero-padded: 000001-999999
- Sequential per year
- Resets to 000001 on year rollover

### Examples

**Valid:**
- `DC-25-000001` → User #1 in 2025
- `DC-25-123456` → User #123,456 in 2025
- `DC-26-000001` → User #1 in 2026

**Invalid:**
- `dc-25-000001` → Wrong case
- `DC-2025-1` → Wrong year format
- `DC-25-1` → Missing zero-padding

---

## 5. GENERATION STRATEGY

### Counter Management

**Database Model: PublicIDCounter**
- Fields: `year` (IntegerField), `counter` (IntegerField)
- Unique constraint on `year`
- Single row per year

**Atomic Increment:**
- Use Django F() expression for atomic increment
- Prevents race conditions (concurrent profile creations)
- Transaction isolation: read counter → increment → commit

**Process:**
1. Profile creation triggered (new User registered)
2. Query current year (2025 → 25)
3. Get or create PublicIDCounter row for year
4. Atomic increment: `counter = F('counter') + 1`
5. Read back new counter value
6. Format: `DC-{year}-{counter:06d}`
7. Assign to `UserProfile.public_id`

### Year Rollover

**Timing:** Jan 1 00:00:00 UTC

**Logic:**
- First profile creation in new year detects year change
- Creates new PublicIDCounter row (year=26, counter=0)
- Subsequent profiles use new year counter

**No manual intervention required.**

---

## 6. MIGRATION AND BACKFILL

### Current State

**No production users yet:**
- Platform in development/staging only
- Test users exist but not production-critical
- Safe to backfill without production risk

### Migration Strategy

**Step 1: Add Field**
- Add `public_id` CharField to UserProfile
- Nullable initially (null=True, blank=True)
- Unique constraint
- Database index for fast lookups

**Step 2: Create Counter Model**
- Create PublicIDCounter model
- Initialize for current year (year=25, counter=0)

**Step 3: Backfill Existing Users**
- Data migration: assign public_id to all existing profiles
- Sequential assignment (respect creation order)
- Example: 100 test users → DC-25-000001 through DC-25-000100

**Step 4: Make Field Required**
- Change `public_id` to non-nullable (null=False)
- Add validation in model save

**Step 5: Update Views/URLs**
- Change profile URLs from `/profile/<username>/` to `/profile/<public_id>/`
- Add redirects for old URLs (backward compatibility)

### Backfill Ordering

**Sort by:** `UserProfile.created_at ASC`
- Earliest users get lowest numbers
- Preserves temporal registration order
- Fair to early adopters

---

## 7. RISKS AND MITIGATIONS

### Risk: Counter Exhaustion

**Scenario:** More than 999,999 users register in one year.

**Likelihood:** Low (1M users/year = 2,740 users/day average)

**Mitigation:**
- Monitor counter value (alert at 900,000 → 90% capacity)
- If approaching limit: extend format to 7 digits (DC-25-0000001)
- Or switch to alphanumeric (DC-25-A00001) for additional capacity

---

### Risk: Enumeration Attacks

**Scenario:** Attacker iterates DC-25-000001, DC-25-000002... to scrape profiles.

**Likelihood:** High (sequential IDs are predictable)

**Mitigation:**
- Rate limiting on profile view endpoint (100 requests/hour)
- Privacy settings (default: hide email, stats from public)
- Monitoring: alert on suspicious sequential access patterns
- CAPTCHA on bulk profile views

**Acceptance:** Enumeration risk acceptable for UX benefits. Privacy enforcement prevents PII leakage.

---

### Risk: Year Rollover Bugs

**Scenario:** Year transition at midnight causes duplicate IDs or counter skips.

**Likelihood:** Low (tested in staging)

**Mitigation:**
- Atomic transaction ensures rollover consistency
- Integration test: simulate year boundary (Dec 31 23:59 → Jan 1 00:01)
- Monitoring: alert on duplicate public_id constraint violations

---

### Risk: Race Conditions (Concurrent Registration)

**Scenario:** Two users register simultaneously, both get same counter value.

**Likelihood:** Medium (high traffic during tournaments)

**Mitigation:**
- F() expression provides database-level atomicity
- Unique constraint on `public_id` prevents duplicates (retry on collision)
- Transaction isolation (READ COMMITTED or higher)
- Load testing: 100 concurrent registrations (verify no duplicates)

---

### Risk: Counter Desync (Data Corruption)

**Scenario:** Counter value drifts from actual assigned IDs.

**Likelihood:** Low (atomic operations prevent drift)

**Mitigation:**
- Nightly reconciliation: compare max assigned ID vs counter value
- Alert if mismatch detected
- Auto-correction: reset counter to max(assigned_ids) + 1

---

## IMPLEMENTATION CHECKLIST

**Phase 1: Database Schema**
- [ ] Add `public_id` CharField to UserProfile (nullable)
- [ ] Create PublicIDCounter model (year, counter)
- [ ] Add unique constraint on `public_id`
- [ ] Add database index on `public_id`

**Phase 2: Generation Logic**
- [ ] Create PublicIDGenerator service
- [ ] Implement atomic increment with F()
- [ ] Add year rollover logic
- [ ] Write unit tests (sequential generation, concurrency, rollover)

**Phase 3: Signal Integration**
- [ ] Update `create_user_profile` signal to call generator
- [ ] Add retry logic (3 attempts on collision)
- [ ] Add error logging

**Phase 4: Backfill**
- [ ] Create data migration (assign public_id to existing users)
- [ ] Test on staging data
- [ ] Execute backfill (100% coverage verification)

**Phase 5: URL Migration**
- [ ] Update views to accept public_id
- [ ] Change URLs from username to public_id
- [ ] Add redirects for old URLs
- [ ] Update all internal links

**Phase 6: Validation**
- [ ] Load test: 100 concurrent profile creations
- [ ] Year rollover test (simulate Jan 1 transition)
- [ ] Verify no duplicates in 10,000 test generations

---

**END OF PUBLIC USER ID STRATEGY**

*Document Version: 1.0*  
*Last Updated: December 22, 2025*  
*Lines: ~145*
