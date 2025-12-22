# USER PROFILE TARGET ARCHITECTURE

**Platform:** DeltaCrown Esports Tournament Platform  
**Version:** 1.0 (Post-Audit Redesign)  
**Date:** December 22, 2025  
**Status:** APPROVED FOR IMPLEMENTATION

---

## 1. PURPOSE & PRINCIPLES

### 1.1 Core Purpose

The User Profile system serves as the **central identity and memory layer** for DeltaCrown users. It provides:

- **Single source of truth** for user identity and preferences
- **Materialized view** of user activity across tournaments, economy, teams
- **Privacy control layer** for all user data exposure
- **Audit foundation** for compliance and fraud prevention

### 1.2 Architectural Principles

#### Principle 1: Source of Truth vs Derived Data

**Source of Truth (Store in Profile):**
- ✅ Identity: name, email, DOB, nationality
- ✅ Preferences: privacy settings, notification preferences
- ✅ KYC status: verification state (verified/pending/rejected)
- ✅ Public identifiers: UUID, slug, profile number

**Derived Data (Calculate from Other Systems):**
- ✅ Wallet balance → Query `DeltaCrownWallet.cached_balance`
- ✅ Tournament count → Query `TournamentParticipation.objects.filter(user=X).count()`
- ✅ Win rate → Calculate from `MatchParticipation` records
- ✅ Team memberships → Query `TeamMembership` active records

**Cached Aggregates (Denormalized for Performance):**
- ✅ `tournaments_played_count` (updated via signal when participation recorded)
- ✅ `lifetime_earnings` (updated via signal when transaction credited)
- ✅ `last_active_at` (updated on any user action)

**Why This Matters:**
- Prevents data drift (single source = single truth)
- Simplifies updates (change in one place)
- Enables audit (can recalculate cached fields from source)

---

#### Principle 2: Auditability First

**Every sensitive action MUST be logged:**

| Action Type | Log Destination | Required Fields |
|-------------|-----------------|-----------------|
| Profile edit | `AuditEvent` | who, what_changed, old_value, new_value, when |
| Privacy change | `AuditEvent` | user, field, old_setting, new_setting, when |
| KYC document view | `AuditEvent` | admin_user, document_type, user_profile, ip_address, when |
| KYC approval/rejection | `AuditEvent` | reviewer, decision, reason, timestamp |
| Balance adjustment | `DeltaCrownTransaction` | admin, amount, reason, timestamp |
| Admin impersonation | `AuditEvent` | admin, target_user, start_time, end_time |

**Audit Retention:**
- Profile changes: 7 years (financial compliance)
- KYC access logs: Indefinite (legal requirement)
- Login attempts: 1 year
- General activity: 3 years

---

#### Principle 3: Privacy by Default

**Default Privacy Stance:**
- ❌ Real name: HIDDEN by default (`show_real_name=False`)
- ❌ Email: HIDDEN by default (`show_email=False`)
- ❌ Phone: HIDDEN by default (`show_phone=False`)
- ❌ Address: HIDDEN by default (`show_address=False`)
- ✅ Display name: PUBLIC (required for gameplay)
- ✅ Avatar: PUBLIC (required for recognition)
- ✅ Game IDs: PUBLIC by default (`show_game_ids=True`)
- ✅ Match history: PUBLIC by default (`show_match_history=True`)

**Privacy Enforcement Layers:**

```
Layer 1: Template Level (User-facing web)
  - Check privacy settings before rendering
  - Show placeholder if field hidden
  
Layer 2: Serializer Level (APIs)
  - PrivacyAwareSerializer base class
  - Remove fields based on viewer permissions
  
Layer 3: Service Level (Cross-app queries)
  - Services use privacy helper methods
  - Cannot bypass privacy checks
  
Layer 4: Database Level (QuerySets)
  - Custom managers filter private profiles
  - Staff bypass via explicit flag
```

**Who Can See What:**

| Viewer Type | Can See |
|-------------|---------|
| **Self** | Everything (own data) |
| **Staff** | Everything (admin override) |
| **Teammate** | Game IDs, contact info IF `show_teams=True` |
| **Tournament Organizer** | Emergency contact IF registered for tournament |
| **Public** | Only fields with `show_X=True` |
| **Anonymous** | Public profiles only (no sensitive data) |

---

#### Principle 4: Scalability for Esports Data

**Design for Growth:**
- User profiles: 100K users (Year 1) → 1M users (Year 3)
- Match history: 50 matches/user → 500 matches/user
- Transactions: 10 tx/user → 100 tx/user
- Audit events: 100 events/user → 1000 events/user

**Performance Patterns:**

1. **Indexed Foreign Keys:**
   - All `user` ForeignKeys indexed
   - All `created_at` fields indexed for time-based queries
   - Composite indexes on (user, created_at) for pagination

2. **Aggregate Caching:**
   - Store computed stats in profile (don't recalculate on every page load)
   - Update via signals (async where possible)
   - Background job reconciliation (nightly)

3. **Pagination Everything:**
   - Match history: 25 per page
   - Transaction history: 25 per page
   - Audit log: 50 per page
   - Use cursor-based pagination for infinite scroll

4. **Selective Prefetching:**
   - Profile list: `select_related('user')` only
   - Profile detail: `prefetch_related('matches', 'transactions', 'badges')`
   - Avoid N+1 queries in serializers

---

## 2. IDENTITY & PROFILE MODEL

### 2.1 User vs UserProfile Responsibilities

#### User Model (Django AbstractUser)

**Purpose:** Authentication and authorization only

**Responsibilities:**
- ✅ Email-based login
- ✅ Password management
- ✅ Email verification state
- ✅ Staff/superuser flags
- ✅ Last login tracking

**Fields:**
```
- id (PK)
- username (unique, alphanumeric)
- email (unique, required)
- password (hashed)
- is_active
- is_staff
- is_superuser
- is_verified (email verified)
- email_verified_at
- date_joined
- last_login
```

**What User Does NOT Store:**
- ❌ Profile data (name, bio, avatar) → UserProfile
- ❌ Privacy settings → PrivacySettings
- ❌ Game IDs → UserProfile.game_profiles
- ❌ Wallet balance → DeltaCrownWallet

---

#### UserProfile Model

**Purpose:** User's public identity and platform activity

**Responsibilities:**
- ✅ Public identity (display name, avatar, bio)
- ✅ Demographic data (real name, DOB, nationality)
- ✅ Game profiles (Valorant ID, MLBB ID, etc.)
- ✅ Cached activity metrics (matches played, tournaments won)
- ✅ Platform gamification (level, XP, badges)

**Core Fields:**

| Category | Fields | Notes |
|----------|--------|-------|
| **Identity** | uuid, slug, display_name, avatar | Public identifiers |
| **Legal** | real_full_name, date_of_birth, nationality | KYC data |
| **Contact** | phone, address, emergency_contact_* | Hidden by default |
| **Gaming** | game_profiles (JSON), preferred_games | Multi-game support |
| **Stats** | level, xp, reputation_score | Cached aggregates |
| **Economy** | (removed - use wallet) | Deprecated fields deleted |
| **Privacy** | (removed - use PrivacySettings) | Migrated to separate model |
| **Metadata** | created_at, updated_at, last_active_at | Timestamps |

**Relationship to User:**
```
UserProfile.user → User (OneToOne, CASCADE)
User.profile → UserProfile (reverse)
```

**Profile Creation Guarantee:**
- MUST exist for every User (created via signal)
- Signal wrapped in transaction.atomic
- Retry logic for race conditions
- Admin command to backfill missing profiles

---

### 2.2 Related Models

#### PrivacySettings (OneToOne with UserProfile)

**Purpose:** Granular control over data visibility

**Fields:**
```
Visibility Toggles (Boolean):
- show_real_name (default=False)
- show_email (default=False)
- show_phone (default=False)
- show_address (default=False)
- show_age (default=True)
- show_gender (default=False)
- show_country (default=True)
- show_game_ids (default=True)
- show_match_history (default=True)
- show_teams (default=True)
- show_achievements (default=True)
- show_inventory_value (default=False)
- show_level_xp (default=True)
- show_social_links (default=True)

Interaction Permissions (Boolean):
- allow_team_invites (default=True)
- allow_friend_requests (default=True)
- allow_direct_messages (default=True)
```

**Helper Method:**
```python
def allows_viewing(viewer, field_name):
    """
    Returns True if viewer can see field.
    Owner and staff always see everything.
    """
```

---

#### VerificationRecord (OneToOne with UserProfile)

**Purpose:** KYC document storage and verification tracking

**Fields:**
```
Status:
- status (unverified/pending/verified/rejected)

Documents (Encrypted at rest):
- id_document_front (ImageField)
- id_document_back (ImageField)
- selfie_with_id (ImageField)

Extracted Data:
- verified_name
- verified_dob
- verified_nationality
- id_number (ENCRYPTED CharField)

Audit:
- submitted_at
- reviewed_at
- reviewed_by (ForeignKey to User)
- rejection_reason
```

**Security Requirements:**
- ✅ id_number field MUST be encrypted (use django-cryptography)
- ✅ Document access MUST be logged (KYCAccessLog model)
- ✅ Files stored outside web root (media/kyc_documents/)
- ✅ File permissions: 600 (owner read/write only)

---

#### AuditEvent (Generic Logging)

**Purpose:** Immutable log of all sensitive actions

**Fields:**
```
- event_type (profile_edit, kyc_view, kyc_approve, balance_adjust, etc.)
- actor (ForeignKey to User - who did it)
- target_user (ForeignKey to User - affected user)
- object_type (profile, wallet, kyc, etc.)
- object_id
- action (view, create, update, delete, approve, reject)
- changes (JSONField - old/new values)
- ip_address
- user_agent
- timestamp
```

**Usage:**
```python
AuditEvent.objects.create(
    event_type='profile_edit',
    actor=request.user,
    target_user=profile.user,
    object_type='userprofile',
    object_id=profile.id,
    action='update',
    changes={'real_full_name': {'old': 'John Doe', 'new': 'Jane Doe'}},
    ip_address=get_client_ip(request),
    timestamp=timezone.now()
)
```

---

### 2.3 Relationship to Other Apps

#### Teams App
```
UserProfile → TeamMembership (ForeignKey)
  - profile field references UserProfile
  - captain field references UserProfile
  
Integration:
  - Teams query profile.get_game_id(game) for registration
  - Teams respect privacy_settings.show_teams
  - Team invites check privacy_settings.allow_team_invites
```

#### Tournaments App
```
User → Registration (ForeignKey)
  - user field references User (NOT profile)
  
UserProfile → TournamentParticipation (NEW - ForeignKey)
  - Records actual participation after tournament completes
  - Syncs from Registration when status=completed
  
Integration:
  - Registration pulls emergency_contact from profile (if registered)
  - TournamentResult creates TournamentParticipation record
  - Profile shows participation count via cached aggregate
```

#### Economy App
```
UserProfile → DeltaCrownWallet (OneToOne)
  - wallet.profile references UserProfile
  
DeltaCrownWallet → DeltaCrownTransaction (ForeignKey)
  - Immutable ledger of all balance changes
  
Integration:
  - Profile displays wallet.cached_balance (read-only property)
  - Profile displays lifetime_earnings (cached, updated via signal)
  - Transactions update profile.lifetime_earnings when credited
```

#### Games App
```
UserProfile.game_profiles (JSONField)
  - Stores game IDs/ranks for all games
  - Format: [{"game": "valorant", "ign": "User#1234", "rank": "Immortal"}]
  
Alternatively (if GameProfile model exists):
UserProfile → GameProfile (ForeignKey)
  - Separate record per game
  - Better for complex game-specific stats
```

---

## 3. PUBLIC USER ID STRATEGY

### 3.1 Current State Assessment

**Existing Identifiers:**
1. **User.id** (Integer PK) - Internal database ID, should NEVER be public
2. **User.username** (String) - User-chosen, changeable, not unique after change
3. **UserProfile.uuid** (UUID4) - Globally unique, opaque, hard to remember
4. **UserProfile.slug** (SlugField) - URL-friendly, human-readable, can collide

**Problems:**
- Username changes break old links
- UUID is not human-friendly
- Slug collisions possible (handled with counter suffix)
- No single "share-friendly" ID

---

### 3.2 Requirements for Public ID

**Must Have:**
1. ✅ **Permanent:** Never changes (even if username changes)
2. ✅ **Unique:** No collisions, globally unique
3. ✅ **Short:** Easy to type/share (< 20 characters)
4. ✅ **URL-safe:** Works in URLs without encoding

**Nice to Have:**
1. ⚠️ **Human-memorable:** Easier to share verbally
2. ⚠️ **Sequential:** Shows platform growth (user #1000 vs #500000)
3. ⚠️ **Branded:** Includes "DC" or "DeltaCrown" prefix
4. ⚠️ **Obfuscated:** Doesn't reveal total user count

---

### 3.3 Option Analysis

#### Option 1: Sequential Profile Number (DC-25-000001)

**Format:** `DC-YY-NNNNNN`
- DC = DeltaCrown
- YY = Year joined (25 = 2025)
- NNNNNN = Sequential number (000001, 000002, ...)

**Example:** User #5 who joined in 2025 = `DC-25-000005`

**Pros:**
- ✅ Human-readable and memorable
- ✅ Short (12 characters)
- ✅ Shows platform growth/history
- ✅ Branded (includes DC)
- ✅ Sortable (can rank by age)

**Cons:**
- ❌ Reveals total user count (competitive intel)
- ❌ Requires database sequence (auto-increment)
- ❌ Year prefix needs logic (what timezone?)
- ⚠️ May feel "impersonal" (just a number)

**Implementation:**
```python
profile_number = models.CharField(max_length=15, unique=True, editable=False)

def generate_profile_number(joined_year):
    # Get next number for this year
    last_profile = UserProfile.objects.filter(
        profile_number__startswith=f'DC-{joined_year}-'
    ).order_by('-profile_number').first()
    
    if last_profile:
        last_num = int(last_profile.profile_number.split('-')[-1])
        next_num = last_num + 1
    else:
        next_num = 1
    
    return f'DC-{joined_year}-{next_num:06d}'
```

---

#### Option 2: Base62 Encoded UUID (Opaque)

**Format:** `dcXXXXXXXXXX` (dc prefix + 10-char base62)

**Example:** User with UUID `a1b2c3d4...` → `dcA3k9Bx2M`

**Pros:**
- ✅ Opaque (doesn't reveal user count)
- ✅ Short (12 characters)
- ✅ Globally unique (derived from UUID)
- ✅ URL-safe (base62 = alphanumeric)
- ✅ No database sequence needed

**Cons:**
- ❌ Not human-memorable
- ❌ Random-looking (less professional?)
- ❌ Requires encoding/decoding logic

**Implementation:**
```python
import base62

public_id = models.CharField(max_length=15, unique=True, editable=False)

def generate_public_id(uuid_obj):
    # Convert UUID to integer, encode as base62
    uuid_int = uuid_obj.int
    encoded = base62.encode(uuid_int)
    return f'dc{encoded[:10]}'  # Truncate to 10 chars
```

---

#### Option 3: Hybrid (Slug + Sequential)

**Format:** `username-1234` or `username#1234`

**Example:** User "ProGamer" with sequence 5432 = `progamer#5432`

**Pros:**
- ✅ Human-memorable (includes username)
- ✅ Short (username + 5 digits)
- ✅ Discord-style (familiar pattern)

**Cons:**
- ❌ Username in URL (username changes break links)
- ❌ Exposes some sequence (less opaque)
- ❌ Longer if username is long

---

### 3.4 FINAL RECOMMENDATION

**DECISION: Option 1 - Sequential Profile Number (DC-YY-NNNNNN)**

**Rationale:**
1. **User Experience Priority:** Esports users share profiles frequently (in Discord, social media)
2. **Brand Building:** "DC-25-000001" is memorable and reinforces DeltaCrown brand
3. **Platform Psychology:** Early users feel special ("I'm DC-25-00042!"), creates FOMO
4. **Technical Simplicity:** No encoding/decoding logic, just auto-increment
5. **Competitive Intel Acceptable:** Other platforms (Riot, Steam) show IDs - not a real secret

**Mitigation for User Count Exposure:**
- Start sequence at 100000 (instead of 000001) to obfuscate early growth
- Optionally skip numbers randomly (100000, 100003, 100007...) to hide exact count

**Implementation Notes:**
- Store in `UserProfile.public_id` (CharField, max_length=15, unique, indexed)
- Generate on profile creation (via signal)
- Use `DC-{year}-{sequential}` format
- Never allow changes (immutable)
- Use in all public URLs: `/u/DC-25-000042/` instead of `/u/username/`

**URL Pattern:**
```
Current:  /u/progamer/
New:      /u/DC-25-000042/
          /users/DC-25-000042/profile/
```

**Backwards Compatibility:**
- Keep slug-based URLs working (301 redirect to public_id URL)
- Support both formats: `/u/progamer/` → 301 → `/u/DC-25-000042/`

---

### 3.5 Public ID Implementation Checklist

**Phase 1: Add Field**
- [ ] Add `public_id` CharField to UserProfile model
- [ ] Create migration (nullable initially)
- [ ] Create management command to backfill existing users

**Phase 2: Generate on Creation**
- [ ] Update profile creation signal to generate public_id
- [ ] Add tests for uniqueness, format, race conditions

**Phase 3: Update Views**
- [ ] Update URL patterns to accept public_id
- [ ] Update views to lookup by public_id
- [ ] Add slug → public_id redirect view

**Phase 4: Update Templates**
- [ ] Replace profile URLs with public_id
- [ ] Update "Share Profile" buttons to use public_id
- [ ] Add "Your ID: DC-25-000042" to profile settings

**Phase 5: API Updates**
- [ ] Add public_id to serializers
- [ ] Support lookup by public_id in APIs
- [ ] Deprecate user.id exposure in APIs (security)

---

## 4. PRIVACY MODEL

### 4.1 PrivacySettings Model

**Schema:**

| Field Category | Fields | Default | Notes |
|----------------|--------|---------|-------|
| **Profile Visibility** | | | What shows on public profile |
| | show_real_name | False | Legal name |
| | show_email | False | Email address |
| | show_phone | False | Phone number |
| | show_address | False | Physical address |
| | show_age | True | Calculated from DOB (not DOB itself) |
| | show_gender | False | Gender identity |
| | show_country | True | Country of residence |
| **Gaming & Activity** | | | Competitive history |
| | show_game_ids | True | Valorant ID, Steam ID, etc. |
| | show_match_history | True | Past tournament matches |
| | show_teams | True | Team memberships |
| | show_achievements | True | Badges and trophies |
| **Economy & Inventory** | | | Financial data |
| | show_inventory_value | False | Cosmetics worth |
| | show_level_xp | True | Platform level/XP |
| **Social** | | | Social media links |
| | show_social_links | True | Twitter, Twitch, Discord |
| **Interaction** | | | Who can contact user |
| | allow_team_invites | True | Can receive team invites |
| | allow_friend_requests | True | Can receive friend requests |
| | allow_direct_messages | True | Can receive DMs |

**Special Profile States:**

1. **Private Profile** (`profile.is_private = True`)
   - Shows minimal card: avatar, display_name, "This profile is private"
   - Overrides all other privacy settings (nuclear option)
   - Only owner and staff can see full profile

2. **Verified Profile** (KYC verified)
   - Shows verified badge
   - Some fields locked (real_full_name, date_of_birth cannot change)

3. **Suspended Profile** (moderation)
   - Shows "Account suspended" message
   - No data visible except to staff

---

### 4.2 Privacy Enforcement Rules

#### Rule 1: Template-Level Enforcement (Web Views)

**Pattern:**
```django
{# Check privacy before rendering #}
{% if profile.privacy_settings.show_email or is_own_profile or request.user.is_staff %}
    <div class="email">{{ profile.user.email }}</div>
{% else %}
    <div class="email text-gray-400">Hidden</div>
{% endif %}
```

**Helper Template Tag:**
```django
{% load profile_privacy %}
{% if profile|allows_field:request.user:'show_real_name' %}
    {{ profile.real_full_name }}
{% endif %}
```

---

#### Rule 2: API-Level Enforcement (Serializers)

**PrivacyAwareProfileSerializer:**
```python
class PrivacyAwareProfileSerializer(serializers.ModelSerializer):
    """
    Base serializer that respects privacy settings.
    Subclass this for all profile-related serializers.
    """
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        viewer = self.context.get('request').user if self.context.get('request') else None
        privacy = instance.privacy_settings
        
        # Owner and staff see everything
        if viewer and (viewer == instance.user or viewer.is_staff):
            return data
        
        # Remove hidden fields
        privacy_map = {
            'email': 'show_email',
            'phone': 'show_phone',
            'real_full_name': 'show_real_name',
            'address': 'show_address',
            'date_of_birth': 'show_age',  # Return age only if show_age=True
            'gender': 'show_gender',
            'game_profiles': 'show_game_ids',
            'match_history': 'show_match_history',
            'team_memberships': 'show_teams',
        }
        
        for field, setting in privacy_map.items():
            if field in data and not getattr(privacy, setting, False):
                data.pop(field)
        
        return data
```

**Usage:**
```python
class UserProfileSerializer(PrivacyAwareProfileSerializer):
    class Meta:
        model = UserProfile
        fields = ['public_id', 'display_name', 'avatar', 'email', 'phone', ...]
        # Privacy filtering happens automatically in to_representation
```

---

#### Rule 3: Service-Level Enforcement (Cross-App)

**Pattern:**
```python
# teams/services.py
def get_team_member_contact_info(team, member_profile):
    """
    Get contact info for team member (respects privacy).
    Only returns data if privacy allows.
    """
    privacy = member_profile.privacy_settings
    
    contact = {
        'display_name': member_profile.display_name,
        'avatar': member_profile.avatar.url if member_profile.avatar else None,
    }
    
    # Only show if privacy allows AND they're teammates
    if privacy.show_teams and privacy.show_email:
        contact['email'] = member_profile.user.email
    
    if privacy.show_teams and privacy.show_phone:
        contact['phone'] = member_profile.phone
    
    return contact
```

**Never Bypass:**
```python
# ❌ BAD: Direct access bypasses privacy
team_member.profile.user.email

# ✅ GOOD: Use service that checks privacy
contact_info = get_team_member_contact_info(team, team_member.profile)
```

---

#### Rule 4: QuerySet-Level Enforcement (Optional)

**Custom Manager:**
```python
class UserProfileQuerySet(models.QuerySet):
    def visible_to(self, viewer):
        """
        Filter profiles visible to viewer.
        Staff see everything, others see public only.
        """
        if viewer and viewer.is_staff:
            return self  # Staff sees all
        
        # Public profiles only
        return self.filter(is_private=False)

class UserProfileManager(models.Manager):
    def get_queryset(self):
        return UserProfileQuerySet(self.model, using=self._db)
    
    def visible_to(self, viewer):
        return self.get_queryset().visible_to(viewer)
```

**Usage:**
```python
# Automatically filters private profiles
profiles = UserProfile.objects.visible_to(request.user).all()
```

---

### 4.3 Visibility Levels

#### Level 1: Public (Anonymous Viewer)

**Can See:**
- Public identifiers (public_id, display_name, avatar)
- Country (if `show_country=True`)
- Game IDs (if `show_game_ids=True`)
- Match history (if `show_match_history=True`)
- Achievements (if `show_achievements=True`)
- Level/XP (if `show_level_xp=True`)

**Cannot See:**
- Email, phone, address
- Real name (unless `show_real_name=True`)
- Age/DOB
- Team memberships (unless `show_teams=True`)
- Wallet balance
- Transaction history

---

#### Level 2: Authenticated User (Logged In)

**Additional Access:**
- Can send team invite (if `allow_team_invites=True`)
- Can send friend request (if `allow_friend_requests=True`)
- Can send DM (if `allow_direct_messages=True`)

**Still Respects Privacy Toggles:**
- Cannot see hidden fields
- Cannot bypass `is_private` flag

---

#### Level 3: Teammate (Same Team)

**Additional Access:**
- May see email/phone for coordination (if `show_teams=True`)
- Context: "We're on the same team, need to communicate"

**Implementation:**
```python
def is_teammate(viewer, profile):
    if not viewer or not viewer.is_authenticated:
        return False
    
    viewer_teams = set(viewer.profile.get_active_teams())
    target_teams = set(profile.get_active_teams())
    
    return bool(viewer_teams & target_teams)  # Any shared teams
```

---

#### Level 4: Tournament Organizer (User Registered)

**Additional Access:**
- Emergency contact (if registered for organizer's tournament)
- Context: "User registered for my tournament, need contact for event"

**Restrictions:**
- Only for tournaments user registered for
- Only emergency contact (not full profile)
- Logged in audit trail

---

#### Level 5: Staff (Platform Admin)

**Full Access:**
- See everything (override all privacy)
- Edit everything (admin panel)
- Access KYC documents

**Audit Requirement:**
- Every staff view MUST be logged
- Staff impersonation MUST be logged
- KYC document access MUST be logged

---

#### Level 6: Self (Profile Owner)

**Full Access:**
- See everything (own data)
- Edit everything (except locked fields)
- Export data (GDPR right to access)
- Delete account (GDPR right to erasure)

**Locked Fields (After KYC):**
- real_full_name (verified)
- date_of_birth (verified)
- nationality (verified)

---

### 4.4 Privacy Enforcement Checklist

**Pre-Launch:**
- [ ] PrivacySettings model created and migrated
- [ ] Default privacy settings created for all users (management command)
- [ ] PrivacyAwareProfileSerializer implemented
- [ ] All profile APIs use privacy-aware serializer
- [ ] Template tags for privacy checks implemented
- [ ] All profile templates updated with privacy checks
- [ ] Cross-app services updated (teams, tournaments, economy)
- [ ] Staff privacy override tested
- [ ] Audit logging for privacy-sensitive actions

**Testing:**
- [ ] Test: Public viewer cannot see hidden fields
- [ ] Test: Owner can see all own fields
- [ ] Test: Staff can see all fields
- [ ] Test: API respects privacy (via serializer)
- [ ] Test: Teammate sees conditional fields
- [ ] Test: Tournament organizer sees emergency contact only
- [ ] Test: is_private flag hides entire profile
- [ ] Test: Privacy changes logged in audit trail

---

## APPENDIX: IMPLEMENTATION SEQUENCE

### Phase Dependencies

```
UP-1: Identity/Public ID + Profile Provisioning + Privacy
  ↓ (enables)
UP-2: Google Login
  ↓ (requires)
UP-3: Economy Sync + Reconciliation
  ↓ (requires)
UP-4: Tournament Stats/History
  ↓ (enables)
UP-5: Audit Log + Activity Feed + Security Sweep
```

**Rationale:**
1. Identity foundation first (public_id, privacy settings)
2. Login hardening (OAuth must create profiles)
3. Economy integration (wallet balance sync)
4. Tournament integration (participation tracking)
5. Security hardening (audit logs, encryption)

---

**END OF TARGET ARCHITECTURE**

**Status:** Ready for UP-1 Planning  
**Next Step:** Create UP_EXECUTION_PLAN.md with detailed phases

---

*Document Version: 1.0*  
*Last Updated: December 22, 2025*  
*Author: Platform Architecture Team*  
*Review Status: Approved*
