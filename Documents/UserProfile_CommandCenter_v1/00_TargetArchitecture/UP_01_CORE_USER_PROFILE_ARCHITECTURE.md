# UP-01: CORE USER PROFILE ARCHITECTURE

**Platform:** DeltaCrown Esports Tournament Platform  
**Date:** December 22, 2025  
**Status:** FOUNDATIONAL ARCHITECTURE

---

## 1. PURPOSE OF USER PROFILE IN DELTACROWN

### What User Profile Represents

**UserProfile is the platform's memory layer for a player's identity and persistent state.**

- Extends Django's built-in User model with esports-specific attributes
- Serves as the canonical reference point for all player-related data across apps
- Acts as the "player record" that tournaments, teams, and economy reference
- Provides the stable identity that persists across sessions, tournaments, and time

### Core Responsibilities

**Identity:**
- Public-facing identifier (username, display name, avatar)
- Biographical data (country, bio, date of birth)
- Verification status (KYC, email confirmation)

**Aggregates & Caches:**
- Computed totals from other apps (total tournaments played, lifetime earnings)
- Performance optimization (avoid expensive joins on every page load)
- Display-ready data (profile page can render without querying 5 apps)

**Settings & Preferences:**
- Privacy controls (who can see email, stats, match history)
- Notification preferences
- Theme/display preferences

### What UserProfile Is NOT

**UserProfile does NOT own:**
- Tournament results (owned by tournaments app)
- Team memberships (owned by teams app)
- Transaction records (owned by economy app)
- Match history (owned by tournaments/games apps)

**UserProfile caches aggregates derived from these, but is not the source of truth.**

---

## 2. RELATIONSHIP BETWEEN USER, USERPROFILE, AND OTHER APPS

### Django User (accounts app)

**Purpose:**
- Authentication and authorization only
- Provided by django.contrib.auth
- Fields: username, email, password, is_staff, is_active

**DeltaCrown does NOT modify Django User directly:**
- No custom fields added to User model
- No swapping User model (keeps compatibility with django-allauth, admin)
- All extensions via UserProfile (OneToOne relationship)

### UserProfile (user_profile app)

**Purpose:**
- Extends User with esports platform attributes
- OneToOne relationship: User.profile → UserProfile
- Every User has exactly one UserProfile (invariant enforced)

**Key Fields (Current/Target):**
- Public identifier: username (current), public_id (target: DC-YY-NNNNNN)
- Display: display_name, avatar, banner, bio
- Identity: country, date_of_birth, verified_status
- Cached aggregates: deltacoin_balance, level, xp, reputation_score
- Stats: tournaments_played, tournaments_won, matches_played, matches_won

### Relationship to Other Apps

**Tournaments App:**
- References UserProfile as participant (ForeignKey to User, implies profile via invariant)
- Creates TournamentParticipation records (post-tournament)
- UserProfile caches aggregates: tournaments_played = count(participations)

**Teams App:**
- References UserProfile as team member (ForeignKey to User)
- UserProfile displays current_team (cached, updated via signal)
- TeamMembership is source of truth, profile mirrors for display

**Economy App:**
- References UserProfile for wallet ownership (ForeignKey to User)
- UserProfile.deltacoin_balance is cached from EconomyWallet.balance
- DeltaCrownTransaction is source of truth, profile mirrors for display

**Games App:**
- References UserProfile for game-specific profiles (e.g., ValorantProfile)
- Game profiles are separate models (ForeignKey to User)
- UserProfile aggregates stats across all games

**Accounts App:**
- Owns User model (authentication)
- OAuth callbacks trigger UserProfile creation
- UserProfile extends User (no direct dependency back)

---

## 3. PROFILE CREATION INVARIANT

### The Invariant

**Every User MUST have exactly one UserProfile.**

**Mathematical expression:**
- `User.objects.count() == UserProfile.objects.count()` at all times
- No User exists without UserProfile
- No UserProfile exists without User

### Why This Matters

**Current Problem (Audit Finding):**
- 47+ code locations assume profile exists without checking
- 1.3% of OAuth flows fail to create profile
- Results in DoesNotExist exceptions and 500 errors

**Solution:**
- Enforce invariant via atomic signal (User + UserProfile created together)
- Add safety accessor: `get_profile_or_create(user)` for defensive access
- Add decorator: `@ensure_profile_exists` for views requiring profile

### Enforcement Strategy

**Creation (Signal-based):**
- `post_save` signal on User model
- Atomic transaction: User and UserProfile created together or both rolled back
- Retry logic (3 attempts) for transient failures
- Default values: privacy settings, initial level/xp, empty stats

**Access (Safety Pattern):**
- Views use `@ensure_profile_exists` decorator
- Services use `get_profile_or_create(user)` helper
- Templates access via `user.profile` (signal guarantees existence)

**Validation (Health Check):**
- Periodic check: `User.objects.count() == UserProfile.objects.count()`
- Alert if mismatch detected (SLO: 99.99% match rate)
- Reconciliation script repairs mismatches (creates missing profiles)

### Edge Cases

**Bulk User Creation:**
- Admin bulk import bypasses signals (performance)
- Must explicitly create profiles in same transaction
- Or run reconciliation script after bulk operation

**User Deletion:**
- Cascade delete: User deleted → UserProfile deleted (OneToOne relationship)
- Soft delete preferred: User.is_active = False (preserve audit trail)

**Profile Deletion:**
- Forbidden: Cannot delete UserProfile without deleting User
- Prevents invariant violation

---

## 4. HIGH-LEVEL DATA OWNERSHIP RULES

### Ownership Principle

**Each app owns its domain data. UserProfile caches aggregates for display.**

**Source of Truth:**
- App that creates/modifies data OWNS it
- Other apps query via API or reference via ForeignKey
- Caching is permitted but must be reconcilable

### Data Ownership Map

**UserProfile App Owns:**
- Identity attributes: display_name, avatar, bio, country, date_of_birth
- Privacy settings: show_email, show_stats, visibility_level
- Verification records: KYC documents, verification status
- Public identifier: public_id (DC-YY-NNNNNN)

**UserProfile App Caches (Derived):**
- deltacoin_balance (source: economy.EconomyWallet.balance)
- tournaments_played (source: count of TournamentParticipation)
- tournaments_won (source: count of TournamentParticipation, placement=1)
- matches_played (source: sum of TournamentParticipation.matches_played)
- matches_won (source: sum of TournamentParticipation.matches_won)
- level, xp, reputation_score (source: calculated from activities)

**Tournaments App Owns:**
- Tournament definitions, brackets, results
- TournamentParticipation records (post-tournament snapshot)
- Match results, scores, placements

**Economy App Owns:**
- DeltaCrownTransaction (immutable ledger)
- EconomyWallet.balance (derived from transactions)
- Prize distributions, refunds, adjustments

**Teams App Owns:**
- Team definitions, rosters
- TeamMembership records (join date, role, status)
- Team ownership, transfer history

**Games App Owns:**
- Game-specific profiles (ValorantProfile, CS2Profile)
- Game-specific stats (K/D, rank, match history per game)
- Game account linkage (Riot ID, Steam ID)

### Sync Strategy

**Cached aggregates updated via signals:**
- Transaction created → update wallet balance → update profile cache
- Tournament completed → create participation → update profile stats
- Team membership changed → update profile.current_team

**Nightly reconciliation:**
- Compare cached values vs source of truth
- Detect drift (signal failures, data corruption)
- Auto-correct profile caches from source data
- Log mismatches for investigation

**Query pattern:**
- Display profile: use cached aggregates (fast, no joins)
- Detailed view: query source of truth (accurate, slower)
- Reports: query source of truth (avoid stale cache)

### What Happens When Source Changes

**Tournament result disputed:**
- Update TournamentParticipation record (soft delete + recreate)
- Signal fires → decrement old stats, increment new stats
- Profile stats corrected automatically

**Balance adjustment (refund):**
- Create DeltaCrownTransaction (reversal)
- Signal fires → update wallet → update profile cache
- Profile balance corrected automatically

**Team membership revoked:**
- Update TeamMembership.status = 'inactive'
- Signal fires → update profile.current_team = None
- Profile displays "No team" automatically

---

## SUMMARY

**User Profile is the platform's identity and aggregation layer:**

1. **Identity:** Stable reference point for player across all apps
2. **Invariant:** Every User has exactly one UserProfile (enforced atomically)
3. **Ownership:** Profile owns identity, caches aggregates from other apps
4. **Sync:** Signals provide real-time updates, reconciliation detects drift
5. **Purpose:** Fast profile display without expensive joins

**Next steps in architecture suite:**
- Public ID strategy (DC-YY-NNNNNN format)
- Privacy enforcement (4-layer model)
- Economy sync (ledger-first pattern)
- Stats tracking (TournamentParticipation)
- Audit logging (immutable events)

---

**END OF CORE ARCHITECTURE**

*Document Version: 1.0*  
*Last Updated: December 22, 2025*  
*Lines: ~145*
