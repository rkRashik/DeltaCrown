# UP-03: PRIVACY ENFORCEMENT MODEL

**Platform:** DeltaCrown Esports Tournament Platform  
**Date:** December 22, 2025  
**Status:** MANDATORY FOR LAUNCH

---

## 1. DEFAULT PRIVACY STANCE

### Privacy-First Principle

**All PII is hidden by default. Users must explicitly opt-in to share.**

### Public by Default (No Permission Required)

- Username (public identifier, not PII)
- Public ID (DC-25-000042 format)
- Display name (if set, otherwise username)
- Avatar image
- Banner image
- Country (flag only, not city/region)
- Profile bio/tagline
- Registration date (year only, not full date)
- Verified status badge (checkmark, yes/no)

### Hidden by Default (Requires Opt-In)

- Email address
- Full name (real name)
- Date of birth (shows age only if visible)
- Phone number
- Tournament statistics (win rate, placement history)
- Match history details
- Transaction history (earnings, spending)
- Team history (past teams)
- Current online status
- Last seen timestamp

### Never Public (Staff Only)

- KYC documents (ID scans, selfies)
- ID numbers (national ID, passport number)
- Admin notes
- Audit logs
- IP addresses
- Session tokens
- Internal flags (is_flagged_for_review, risk_score)

---

## 2. PRIVACYSETTINGS RESPONSIBILITIES

### Model Purpose

**PrivacySettings is a OneToOne with UserProfile defining visibility rules.**

### Core Fields

**Boolean Toggles (True = Visible, False = Hidden):**
- `show_full_name` → Default: False
- `show_email` → Default: False
- `show_tournament_stats` → Default: True (anonymized stats okay)
- `show_match_history` → Default: True (public competition records)
- `show_transaction_history` → Default: False (financial privacy)
- `show_teams_history` → Default: True (esports career visibility)

**Visibility Level (Overall Profile):**
- `visibility_level` → Choices: "public", "authenticated", "private"
- Default: "public" (profile visible to all, but PII still hidden)

### Visibility Level Meanings

**public:**
- Profile page accessible to anonymous visitors
- Public fields visible (username, avatar, bio)
- Hidden fields respect individual toggles

**authenticated:**
- Profile page requires login to view
- Authenticated users see public fields + opted-in fields
- Anonymous visitors see "Profile is private"

**private:**
- Profile page visible only to self and staff
- Other users see "This profile is private"
- Used for low-profile accounts or post-ban transparency

### Defaults on Creation

**Signal creates PrivacySettings with:**
- All PII toggles = False (maximum privacy)
- `visibility_level` = "public" (profile exists but PII hidden)
- User must explicitly enable PII sharing via settings page

---

## 3. ENFORCEMENT LAYERS

### Layer 1: Django Templates

**Responsibility:** Conditionally render PII fields based on viewer and settings.

**Mechanism:**
- Template tags: `{% privacy_filter profile viewer 'email' %}`
- Template filters: `{{ profile.email|privacy_check:viewer }}`
- Conditional blocks: `{% if can_view_email %}`

**Enforcement:**
- All profile templates use privacy tags
- Direct field access forbidden (e.g., `{{ profile.email }}` → lint error)
- Fallback display: "Hidden by user" or "—" for hidden fields

### Layer 2: API Serializers (DRF)

**Responsibility:** Remove PII fields from API responses based on viewer and settings.

**Mechanism:**
- Base class: `PrivacyAwareProfileSerializer`
- Override `to_representation()` to filter fields
- Remove keys from response dict (not just hide values)

**Enforcement:**
- All profile serializers inherit from privacy-aware base
- No raw model serialization (ModelSerializer must use privacy base)
- Staff bypass: `request.user.is_staff` sees all fields (audit purpose)

### Layer 3: Services

**Responsibility:** Central policy checks before exposing profile data.

**Mechanism:**
- Service methods accept `viewer` parameter
- Example: `ProfileService.get_display_data(profile, viewer)`
- Returns privacy-filtered dict

**Enforcement:**
- Views call service methods (not direct model access)
- Service layer is single source of truth for visibility logic
- Reusable across templates, APIs, background tasks

### Layer 4: Querysets/Managers (Recommended)

**Responsibility:** Filter profiles at database level based on visibility.

**Mechanism:**
- QuerySet method: `UserProfile.objects.visible_to(viewer)`
- Excludes private profiles from public lists
- Example: leaderboards only show "public" profiles

**Enforcement:**
- Profile listing views use `visible_to(viewer)`
- Search results respect visibility
- Admin panel bypasses filter (staff sees all)

---

## 4. VISIBILITY RULES BY VIEWER TYPE

### Anonymous (Not Logged In)

**Can See:**
- Public fields only (username, avatar, bio)
- Public profiles (`visibility_level="public"`)

**Cannot See:**
- PII fields (email, full name)
- Authenticated-only profiles
- Private profiles

### Authenticated (Logged In User)

**Can See:**
- Public fields on all public profiles
- Public profiles (`visibility_level="public"` or "authenticated")
- Opted-in fields on public profiles (if toggle enabled)

**Cannot See:**
- Private profiles (unless self or staff)
- PII fields unless opted-in by profile owner

### Self (Profile Owner)

**Can See:**
- All own fields (no restrictions)
- Own private settings
- Own KYC status (but not raw documents)

**Cannot See:**
- Other users' hidden fields

### Teammate (Same Team Member)

**Can See:**
- Same as authenticated user
- Future: team-specific visibility tier (if implemented)

**Cannot See:**
- PII unless opted-in
- Transaction history of teammates

### Staff (is_staff=True)

**Can See:**
- All fields on all profiles (audit/support purpose)
- KYC documents
- Admin notes, audit logs

**Cannot See:**
- Nothing restricted (full access for moderation)

---

## 5. "NEVER BYPASS" RULES

### Anti-Footgun Rules

**Rule 1: Never Access Fields Directly in Templates**
- ❌ Forbidden: `{{ profile.email }}`
- ✅ Required: `{% privacy_filter profile viewer 'email' %}`

**Rule 2: Never Serialize Without Privacy Base**
- ❌ Forbidden: `class ProfileSerializer(serializers.ModelSerializer)`
- ✅ Required: `class ProfileSerializer(PrivacyAwareProfileSerializer)`

**Rule 3: Never Log PII in Debug/Info Logs**
- ❌ Forbidden: `logger.info(f"User email: {profile.email}")`
- ✅ Required: `logger.info(f"User ID: {profile.user_id}")`

**Rule 4: Never Return Raw Profile Dictionaries**
- ❌ Forbidden: `return model_to_dict(profile)`
- ✅ Required: `return ProfileService.get_display_data(profile, viewer)`

**Rule 5: Staff Bypass Must Be Explicit**
- ❌ Forbidden: Auto-bypass without audit trail
- ✅ Required: Check `is_staff` AND log access in AuditEvent

**Rule 6: Never Cache PII Without Viewer Context**
- ❌ Forbidden: `cache.set('profile_123', profile_dict)`
- ✅ Required: Cache must include viewer_id in key OR only cache public fields

---

## 6. PRIVACY LEAK CHECKLIST

### Grep Patterns to Search

**Direct Field Access in Templates:**
```
Search: {{ profile.email }}
Search: {{ profile.full_name }}
Search: {{ user.email }}
Risk: PII exposed without privacy check
```

**Debug Logging:**
```
Search: logger.debug.*email
Search: logger.info.*email
Search: print(.*profile\.
Risk: PII logged in plaintext logs
```

**Raw Serialization:**
```
Search: model_to_dict(profile
Search: ProfileSerializer(serializers.ModelSerializer):
Risk: Serializer bypasses privacy layer
```

**Direct Database Queries:**
```
Search: UserProfile.objects.all()
Search: User.objects.filter(.*).values(
Risk: Query returns all profiles including private
```

**Cache Keys Without Viewer:**
```
Search: cache.set('profile_
Risk: Cached PII visible to wrong viewers
```

**API Endpoints Without Privacy Check:**
```
Search: def.*profile.*request
Check: Does endpoint use PrivacyAwareSerializer?
Risk: API leaks PII
```

---

## 7. ACCEPTANCE CRITERIA FOR "PRIVACY ENFORCEMENT COMPLETE"

### Template Layer

- [ ] All profile templates use `{% privacy_filter %}` tags
- [ ] Zero instances of `{{ profile.email }}` or `{{ profile.full_name }}`
- [ ] All PII fields show fallback text when hidden ("—" or "Hidden by user")
- [ ] Manual test: public viewer cannot see email/full_name

### API Layer

- [ ] All profile serializers inherit from `PrivacyAwareProfileSerializer`
- [ ] API responses tested with anonymous, authenticated, self, staff viewers
- [ ] PII fields removed from response (not present in JSON) when hidden
- [ ] Staff endpoints return all fields (audit purpose)

### Service Layer

- [ ] ProfileService exists with `get_display_data(profile, viewer)` method
- [ ] Service enforces privacy rules (not views/templates)
- [ ] Views call service methods (not direct model access)

### QuerySet Layer

- [ ] `UserProfile.objects.visible_to(viewer)` method exists
- [ ] Profile lists (leaderboards, search) use `visible_to(viewer)`
- [ ] Private profiles excluded from public lists
- [ ] Staff sees all profiles (no filter applied for is_staff=True)

### Logging & Debugging

- [ ] Grep for `logger.*email` returns zero PII logging
- [ ] Grep for `print(.*profile` returns zero debug prints
- [ ] All logs use non-PII identifiers (user_id, public_id)

### Testing

- [ ] Unit tests: privacy rules enforced for each viewer type
- [ ] Integration tests: API endpoints respect privacy
- [ ] Manual test: create profile, set private, verify anonymous cannot see
- [ ] Load test: privacy checks add <50ms overhead per request

### Documentation

- [ ] Privacy enforcement guide exists (this document)
- [ ] Developer onboarding includes privacy checklist
- [ ] Code review checklist includes privacy checks

---

**END OF PRIVACY ENFORCEMENT MODEL**

*Document Version: 1.0*  
*Last Updated: December 22, 2025*  
*Lines: ~147*
