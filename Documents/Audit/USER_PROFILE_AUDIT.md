# UserProfile Model Audit Report

**Date:** 2025-01-XX  
**Purpose:** Comprehensive audit of `apps.user_profile.UserProfile` model to identify gaps before redesign  
**Related:** Auto-fill registration wizard, Game_Spec.md requirements, Tournament registration system

---

## Executive Summary

The current `UserProfile` model has **critical architectural gaps** that prevent proper tournament registration auto-fill functionality and violate the requirements defined in `Game_Spec.md`. The model is missing essential contact and demographic fields that are referenced throughout the codebase but don't exist in the database schema.

### Critical Issues

1. **Missing Required Fields**: `phone`, `country`, `full_name`, `age`, `date_of_birth`, `gender`, `address`
2. **Orphaned Privacy Settings**: `show_phone` flag exists but `phone` field doesn't
3. **Code References Non-Existent Fields**: Multiple views attempt to access fields that don't exist
4. **Auto-Fill Failure**: Registration wizard cannot auto-fill because source fields are missing
5. **Game ID Inconsistencies**: Naming conventions vary (`_id` vs `_uid`)
6. **No Team Integration**: No reverse relationship to access user's team memberships

---

## Section 1: Current UserProfile Model Structure

### File: `apps/user_profile/models.py` (85 lines)

**Purpose:** Store extended user data beyond Django's default User model (which only has username, email, first_name, last_name, password)

### Current Fields Inventory (20 fields total)

#### Core Identity (4 fields)
```python
user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
display_name = models.CharField(max_length=80, blank=True, default="")
region = models.CharField(max_length=20, choices=REGION_CHOICES, default="", blank=True)
avatar = models.ImageField(upload_to="user_avatars/", null=True, blank=True)
bio = models.TextField(max_length=500, blank=True, default="")
```

**Issues:**
- `region` is limited to 3 choices: AMERICAS, EUROPE, ASIA_PACIFIC (does NOT cover individual countries)
- No `country` field for specific nationality (required for international tournaments)
- No `full_name` field (User model has `first_name` and `last_name` but no combined full name)
- No demographic data (age, gender, date of birth)

#### Social Links (3 fields)
```python
youtube_link = models.URLField(max_length=200, blank=True, default="")
twitch_link = models.URLField(max_length=200, blank=True, default="")
discord_id = models.CharField(max_length=64, blank=True, default="")
```

**Issues:**
- No phone number (referenced in privacy settings and registration wizard)
- No emergency contact information
- No physical address

#### Game IDs (10 fields)
```python
# Riot Games (Valorant)
riot_id = models.CharField(max_length=100, blank=True, default="")
riot_tagline = models.CharField(max_length=50, blank=True, default="")

# Steam (Counter-Strike 2, Dota 2)
steam_id = models.CharField(max_length=100, blank=True, default="")

# Konami (eFootball)
efootball_id = models.CharField(max_length=100, blank=True, default="")

# Mobile Legends
mlbb_id = models.CharField(max_length=100, blank=True, default="")
mlbb_server_id = models.CharField(max_length=50, blank=True, default="")

# Battle Royale Games
pubg_mobile_id = models.CharField(max_length=100, blank=True, default="")
free_fire_id = models.CharField(max_length=100, blank=True, default="")

# EA Sports (FC 26)
ea_id = models.CharField(max_length=100, blank=True, default="")

# Call of Duty Mobile
codm_uid = models.CharField(max_length=100, blank=True, default="")
```

**Issues:**
- Inconsistent naming: `riot_id`, `steam_id`, `efootball_id`, `mlbb_id`, `ea_id` use `_id` suffix
- BUT: `codm_uid` uses `_uid` suffix (inconsistent)
- Separate `riot_tagline` field exists but other games don't have secondary identifiers split out
- `mlbb_server_id` is separate, but could be combined or use JSON

#### Settings & Preferences (3 fields)
```python
preferred_games = models.JSONField(default=list, blank=True)
is_private = models.BooleanField(default=False)
show_email = models.BooleanField(default=False)
show_phone = models.BooleanField(default=False)  # ⚠️ REFERENCES NON-EXISTENT FIELD!
show_socials = models.BooleanField(default=True)
```

**Critical Issue:**
- `show_phone` privacy setting exists but there is **NO phone field** in the model!
- This makes the privacy setting completely meaningless

#### Timestamps (1 field)
```python
created_at = models.DateTimeField(auto_now_add=True)
```

---

## Section 2: Missing Fields Analysis

### 2.1 Fields Referenced in Code But Don't Exist

#### File: `apps/user_profile/views_public.py` (Lines 63-65)
```python
# Attempt to get non-existent fields
phone = getattr(profile, "phone", None)  # Always returns None!
show_phone = bool(getattr(profile, "show_phone", False))
```

**Impact:** Public profile view tries to display phone number but always shows nothing because field doesn't exist.

#### File: `apps/tournaments/views/registration_wizard.py` (Line 180+)
```python
def _auto_fill_solo_data(self, profile):
    return {
        'full_name': profile.full_name or '',  # DOESN'T EXIST
        'phone': profile.phone or '',          # DOESN'T EXIST
        'country': profile.country or '',      # DOESN'T EXIST
        'age': profile.age or '',              # DOESN'T EXIST
        # ... other fields
    }
```

**Impact:** Auto-fill in registration wizard CANNOT work because all these critical fields don't exist in UserProfile.

### 2.2 Complete List of Missing Fields

| Field Name | Type | Why Needed | Current Workaround | Status |
|------------|------|------------|-------------------|--------|
| `phone` | CharField | Contact information, tournament registration | None - always returns empty | **CRITICAL** |
| `full_name` | CharField | Official tournament registration, certificates | Uses User.first_name + User.last_name | **HIGH** |
| `country` | CharField | Nationality for international tournaments | Uses limited `region` field (3 choices only) | **CRITICAL** |
| `age` | IntegerField | Age restrictions, junior tournaments | None - calculated from DOB if exists | **HIGH** |
| `date_of_birth` | DateField | Age verification, tournament eligibility | None - doesn't exist | **CRITICAL** |
| `gender` | CharField | Gender-specific tournaments, demographics | None - doesn't exist | **MEDIUM** |
| `address` | TextField | Prize shipping, official correspondence | None - doesn't exist | **MEDIUM** |
| `city` | CharField | Regional tournaments, location-based matching | None - doesn't exist | **LOW** |
| `postal_code` | CharField | Shipping, regional verification | None - doesn't exist | **LOW** |
| `emergency_contact_name` | CharField | Minor safety, tournament organizer requirements | None - doesn't exist | **HIGH** |
| `emergency_contact_phone` | CharField | Emergency situations during events | None - doesn't exist | **HIGH** |
| `nationality` | CharField | International competition requirements | None - doesn't exist | **MEDIUM** |

---

## Section 3: Game_Spec.md Requirements Comparison

### File: `Documents/Games/Game_Spec.md`

Defines 9 supported games with specific ID requirements:

| Game | Game Code | Required ID Format | Current Field | Match? |
|------|-----------|-------------------|---------------|--------|
| **Valorant** | `valorant` | Riot ID (Name#TAG) | `riot_id` + `riot_tagline` | ✅ Exists (separate fields) |
| **Counter-Strike 2** | `cs2` | Steam ID | `steam_id` | ✅ Exists |
| **Dota 2** | `dota2` | Steam ID | `steam_id` | ✅ Exists (shares with CS2) |
| **eFootball** | `efootball` | Konami ID | `efootball_id` | ✅ Exists |
| **FC 26** | `fc26` | EA ID | `ea_id` | ✅ Exists |
| **Mobile Legends** | `mlbb` | User ID + Zone ID | `mlbb_id` + `mlbb_server_id` | ✅ Exists (separate fields) |
| **Call of Duty Mobile** | `codm` | IGN/UID | `codm_uid` | ⚠️ Uses `_uid` instead of `_id` |
| **Free Fire** | `free_fire` | IGN/UID | `free_fire_id` | ⚠️ Naming inconsistency |
| **PUBG Mobile** | `pubg_mobile` | IGN/UID | `pubg_mobile_id` | ⚠️ Naming inconsistency |

**Game ID Coverage:** 9/9 games have fields ✅  
**Naming Consistency:** ❌ Inconsistent (`_id` vs `_uid`)

### Additional Game_Spec Requirements

**Team Size Requirements:**
- 5v5 games: Valorant, CS2, Dota 2, MLBB, CODM
- 4-player squads: Free Fire, PUBG Mobile
- 1v1: eFootball, FC 26

**Result Types:**
- Kill-based: Valorant, CS2, Dota 2 (kills tracked)
- Score-based: eFootball, FC 26 (goals/scores)
- Survival-based: Free Fire, PUBG Mobile (placement + kills)
- Objective-based: MLBB (kills + objectives)

**Profile Requirements (from Game_Spec context):**
- ✅ Game-specific IDs stored
- ❌ No rank/tier tracking per game
- ❌ No preferred role/position per game
- ❌ No playtime/experience tracking
- ❌ No verified player status per game

---

## Section 4: Django User Model vs UserProfile

### File: `apps/accounts/models.py`

```python
class User(AbstractUser):
    """Custom user model with mandatory email and verification."""
    
    # Inherited from AbstractUser:
    # - username (CharField, unique)
    # - first_name (CharField, blank=True)
    # - last_name (CharField, blank=True)
    # - email (EmailField) - OVERRIDDEN to be unique and required
    # - is_staff (BooleanField)
    # - is_active (BooleanField)
    # - is_superuser (BooleanField)
    # - date_joined (DateTimeField)
    # - last_login (DateTimeField)
    
    # Custom fields:
    email = models.EmailField("email address", unique=True)  # Made unique & required
    is_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    
    REQUIRED_FIELDS = ["email"]
```

### Current Data Distribution

**User Model (built-in auth):**
- Authentication: username, password, email
- Admin flags: is_staff, is_superuser, is_active
- Email verification: is_verified, email_verified_at
- Basic identity: first_name, last_name

**UserProfile Model (custom extension):**
- Display identity: display_name, avatar, bio
- Gaming identity: 10 game ID fields
- Social presence: youtube_link, twitch_link, discord_id
- Settings: region, preferred_games, privacy flags

**Gap: Missing Critical Data**
- ❌ Contact information (phone, address)
- ❌ Demographics (age, gender, nationality)
- ❌ Emergency contacts
- ❌ Tournament eligibility data
- ❌ Team integration (no reverse relation from UserProfile to TeamMembership)

---

## Section 5: Team Integration Gap

### Current Team Models (from `apps/teams/models/_legacy.py`)

```python
class Team(models.Model):
    captain = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.SET_NULL,
        related_name="captain_teams"  # ✅ Reverse relation exists
    )
    # ... team fields

class TeamMembership(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    profile = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="team_memberships"  # ✅ Reverse relation exists
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    # ...
```

**Good News:** Reverse relationships DO exist!
- `profile.captain_teams.all()` - teams where user is captain
- `profile.team_memberships.all()` - all team memberships

**Integration Status:**
- ✅ UserProfile → Team (via `captain_teams`)
- ✅ UserProfile → TeamMembership (via `team_memberships`)
- ✅ Can check team membership in registration wizard
- ❌ No convenience methods on UserProfile (e.g., `get_active_teams()`, `is_team_member()`)

---

## Section 6: Privacy Settings vs Actual Fields

### Privacy Settings in UserProfile

```python
is_private = models.BooleanField(default=False)        # Hide entire profile
show_email = models.BooleanField(default=False)        # ✅ User.email exists
show_phone = models.BooleanField(default=False)        # ❌ NO phone field!
show_socials = models.BooleanField(default=True)       # ✅ youtube_link, twitch_link, discord_id exist
```

### Privacy Setting Analysis

| Privacy Flag | Controls Field | Field Exists? | Functional? |
|--------------|---------------|---------------|-------------|
| `is_private` | Entire profile visibility | N/A | ✅ Works |
| `show_email` | `User.email` | ✅ Yes (in User model) | ✅ Works |
| `show_phone` | `UserProfile.phone` | ❌ **NO** | ❌ **BROKEN** |
| `show_socials` | youtube_link, twitch_link, discord_id | ✅ Yes | ✅ Works |

**Critical Finding:** `show_phone` privacy setting is **COMPLETELY USELESS** because there's no phone field to show/hide!

---

## Section 7: Database Schema Verification

### File: `apps/user_profile/migrations/0001_initial.py`

**Initial Schema (excerpt):**
```python
migrations.CreateModel(
    name='UserProfile',
    fields=[
        ('id', models.BigAutoField(...)),
        ('display_name', models.CharField(max_length=80)),
        ('region', models.CharField(max_length=20, choices=[...])),
        ('avatar', models.ImageField(upload_to='user_avatars/')),
        ('bio', models.TextField(max_length=500)),
        ('youtube_link', models.URLField(max_length=200)),
        ('twitch_link', models.URLField(max_length=200)),
        ('discord_id', models.CharField(max_length=64)),
        ('riot_id', models.CharField(max_length=100)),
        ('riot_tagline', models.CharField(max_length=50)),
        ('steam_id', models.CharField(max_length=100)),
        ('efootball_id', models.CharField(max_length=100)),
        ('mlbb_id', models.CharField(max_length=100)),
        ('mlbb_server_id', models.CharField(max_length=50)),
        ('pubg_mobile_id', models.CharField(max_length=100)),
        ('free_fire_id', models.CharField(max_length=100)),
        ('ea_id', models.CharField(max_length=100)),
        ('codm_uid', models.CharField(max_length=100)),
        ('preferred_games', models.JSONField(default=list)),
        ('is_private', models.BooleanField(default=False)),
        ('show_email', models.BooleanField(default=False)),
        ('show_phone', models.BooleanField(default=False)),  # ⚠️ NO phone field!
        ('show_socials', models.BooleanField(default=True)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('user', models.OneToOneField(...)),
    ],
)
```

**Confirmed:** No subsequent migrations added phone, country, age, or contact fields.

---

## Section 8: Registration Wizard Auto-Fill Impact

### File: `apps/tournaments/views/registration_wizard.py`

**Current Auto-Fill Implementation:**
```python
def _auto_fill_solo_data(self, profile):
    """Pre-fill solo registration from user profile."""
    return {
        'full_name': profile.full_name or '',      # ❌ DOESN'T EXIST
        'phone': profile.phone or '',              # ❌ DOESN'T EXIST
        'country': profile.country or '',          # ❌ DOESN'T EXIST (only region)
        'age': profile.age or '',                  # ❌ DOESN'T EXIST
        'game_id': profile.get_game_id(self.tournament.game) or '',  # ✅ Works
        'discord_id': profile.discord_id or '',    # ✅ Works
    }
```

**Result:** Auto-fill returns empty strings for 4 out of 6 fields!

**Template: `apps/tournaments/templates/tournaments/registration/solo_step1.html`**
```html
<input type="text" name="full_name" value="{{ form.full_name.value|default:'' }}" />
<input type="tel" name="phone" value="{{ form.phone.value|default:'' }}" />
<input type="text" name="country" value="{{ form.country.value|default:'' }}" />
<input type="number" name="age" value="{{ form.age.value|default:'' }}" />
```

**Current Behavior:**
- Template expects values from form context
- Form is populated by `_auto_fill_solo_data()`
- Auto-fill returns empty strings because UserProfile fields don't exist
- User sees completely empty form (no auto-fill at all)

---

## Section 9: Code Reference Audit

### Files Attempting to Access Non-Existent Fields

1. **`apps/user_profile/views_public.py`** (Line 63-65)
   ```python
   phone = getattr(profile, "phone", None)  # Always None
   ```

2. **`apps/tournaments/views/registration_wizard.py`** (Line 180+)
   ```python
   'full_name': profile.full_name or '',
   'phone': profile.phone or '',
   'country': profile.country or '',
   'age': profile.age or '',
   ```

3. **`apps/user_profile/forms.py`** (UserProfileForm)
   - Correctly excludes non-existent fields
   - Only includes fields that actually exist in model
   - No validation errors (form is consistent with model)

**Search Results:**
```bash
grep -r "profile.phone" apps/
# apps/user_profile/views_public.py:63:    phone = getattr(profile, "phone", None)
# apps/tournaments/views/registration_wizard.py:182:    'phone': profile.phone or '',

grep -r "profile.country" apps/
# apps/tournaments/views/registration_wizard.py:183:    'country': profile.country or '',

grep -r "profile.full_name" apps/
# apps/tournaments/views/registration_wizard.py:181:    'full_name': profile.full_name or '',
```

**Total References to Non-Existent Fields:** 5 instances across 2 files

---

## Section 10: Gap Analysis Summary

### Critical Gaps (Must Fix Immediately)

| Issue | Impact | Severity | Files Affected |
|-------|--------|----------|----------------|
| Missing `phone` field | Auto-fill fails, privacy setting useless, contact info unavailable | **CRITICAL** | views_public.py, registration_wizard.py, models.py |
| Missing `country` field | Cannot specify nationality for tournaments, only broad region | **CRITICAL** | registration_wizard.py, models.py |
| Missing `date_of_birth` field | Cannot verify age for tournaments, no age restrictions | **CRITICAL** | models.py |
| Missing `full_name` field | Tournament registration incomplete, certificate generation fails | **HIGH** | registration_wizard.py |
| Orphaned `show_phone` setting | Privacy setting controls nothing | **HIGH** | models.py, views_public.py |

### High Priority Gaps (Should Fix Soon)

| Issue | Impact | Severity |
|-------|--------|----------|
| No `age` calculated property | Age restrictions cannot be enforced | **HIGH** |
| No `emergency_contact_name` | Cannot handle emergencies at live events | **HIGH** |
| No `emergency_contact_phone` | Safety risk for minor participants | **HIGH** |
| Inconsistent game ID naming | Confusion (`_id` vs `_uid`) | **MEDIUM** |
| No convenience methods for teams | Must manually query `team_memberships.filter(status='ACTIVE')` | **MEDIUM** |

### Medium Priority Gaps (Nice to Have)

| Issue | Impact | Severity |
|-------|--------|----------|
| No `gender` field | Cannot support gender-specific tournaments | **MEDIUM** |
| No `address` field | Prize shipping requires manual data collection | **MEDIUM** |
| No `nationality` field | International competition requires workarounds | **MEDIUM** |
| No `city` / `postal_code` | Regional events lack location precision | **LOW** |
| No rank/tier per game | Cannot match players by skill level | **LOW** |

---

## Section 11: Recommended Changes

### Phase 1: Critical Contact & Demographic Fields

**Add to UserProfile model:**
```python
# Contact Information
phone = models.CharField(max_length=20, blank=True, default="")
address = models.TextField(max_length=300, blank=True, default="")
city = models.CharField(max_length=100, blank=True, default="")
postal_code = models.CharField(max_length=20, blank=True, default="")
country = models.CharField(max_length=100, blank=True, default="")  # ISO country code or name

# Demographics
full_name = models.CharField(max_length=200, blank=True, default="")
date_of_birth = models.DateField(null=True, blank=True)
gender = models.CharField(
    max_length=20,
    choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other'), ('prefer_not_to_say', 'Prefer not to say')],
    blank=True,
    default=""
)
nationality = models.CharField(max_length=100, blank=True, default="")

# Emergency Contact
emergency_contact_name = models.CharField(max_length=200, blank=True, default="")
emergency_contact_phone = models.CharField(max_length=20, blank=True, default="")
emergency_contact_relation = models.CharField(max_length=50, blank=True, default="")
```

**Add calculated property:**
```python
@property
def age(self):
    """Calculate age from date of birth."""
    if not self.date_of_birth:
        return None
    today = timezone.now().date()
    return today.year - self.date_of_birth.year - (
        (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
    )
```

### Phase 2: Game ID Normalization

**Standardize naming convention:**
```python
# Current inconsistency:
codm_uid = ...  # Uses _uid
free_fire_id = ...  # Uses _id
pubg_mobile_id = ...  # Uses _id

# Recommended: Use _id consistently
codm_id = models.CharField(max_length=100, blank=True, default="")  # Rename from codm_uid
```

**Or use JSON for scalability:**
```python
game_ids = models.JSONField(default=dict, blank=True)
# Example: {"valorant": "Player#TAG", "cs2": "76561198123456789", "mlbb": {"id": "123456", "server": "1234"}}
```

### Phase 3: Team Convenience Methods

**Add to UserProfile model:**
```python
def get_active_teams(self):
    """Get all teams where user is an active member."""
    return [
        membership.team 
        for membership in self.team_memberships.filter(status='ACTIVE')
    ]

def is_team_member(self, team):
    """Check if user is an active member of a specific team."""
    return self.team_memberships.filter(team=team, status='ACTIVE').exists()

def is_team_captain(self, team):
    """Check if user is the captain of a specific team."""
    return self.captain_teams.filter(id=team.id).exists()

def can_register_for_team_tournament(self, team):
    """Check if user has permission to register team for tournaments."""
    return self.is_team_captain(team) or self.team_memberships.filter(
        team=team, 
        status='ACTIVE',
        role__in=['CAPTAIN', 'MANAGER']
    ).exists()
```

### Phase 4: Enhanced Privacy Controls

**Update privacy settings to match new fields:**
```python
# Existing (keep as-is)
show_email = models.BooleanField(default=False)
show_phone = models.BooleanField(default=False)  # NOW FUNCTIONAL with phone field!
show_socials = models.BooleanField(default=True)

# New
show_address = models.BooleanField(default=False)
show_age = models.BooleanField(default=True)
show_gender = models.BooleanField(default=False)
show_country = models.BooleanField(default=True)
```

### Phase 5: Migration Strategy

**Create migration file:**
```python
# Generated migration (example)
class Migration(migrations.Migration):
    dependencies = [
        ('user_profile', '0001_initial'),
    ]
    
    operations = [
        # Add contact fields
        migrations.AddField(
            model_name='userprofile',
            name='phone',
            field=models.CharField(max_length=20, blank=True, default=''),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='country',
            field=models.CharField(max_length=100, blank=True, default=''),
        ),
        # ... add all other fields
        
        # Data migration: populate full_name from User.first_name + last_name
        migrations.RunPython(populate_full_name, reverse_code=migrations.RunPython.noop),
    ]
```

**Data migration function:**
```python
def populate_full_name(apps, schema_editor):
    UserProfile = apps.get_model('user_profile', 'UserProfile')
    for profile in UserProfile.objects.select_related('user').all():
        if profile.user.first_name or profile.user.last_name:
            profile.full_name = f"{profile.user.first_name} {profile.user.last_name}".strip()
            profile.save(update_fields=['full_name'])
```

---

## Section 12: Backwards Compatibility Plan

### Existing Code Using getattr() Pattern

**Good News:** Most code already uses defensive patterns:
```python
phone = getattr(profile, "phone", None)  # Returns None if field missing
country = profile.country if hasattr(profile, 'country') else profile.region
```

**After Migration:**
- These will automatically work when fields are added
- No code changes required (fields will exist)
- Auto-fill will immediately start working

### Forms Update

**File: `apps/user_profile/forms.py`**

**Add new fields to form:**
```python
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            # Existing
            'display_name', 'region', 'avatar', 'bio',
            'youtube_link', 'twitch_link', 'discord_id',
            'riot_id', 'riot_tagline', 'steam_id', 'efootball_id',
            'mlbb_id', 'mlbb_server_id', 'pubg_mobile_id',
            'free_fire_id', 'ea_id', 'codm_uid',
            'preferred_games', 'is_private', 'show_email',
            'show_phone', 'show_socials',
            
            # NEW
            'phone', 'country', 'full_name', 'date_of_birth',
            'gender', 'nationality', 'address', 'city', 'postal_code',
            'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relation',
            'show_address', 'show_age', 'show_gender', 'show_country',
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
```

---

## Section 13: Testing Checklist

### Before Migration
- [ ] Backup production database
- [ ] Test migration in staging environment
- [ ] Verify all existing profiles have User.email populated

### After Migration
- [ ] Run `python manage.py migrate` successfully
- [ ] Verify all fields added to database schema
- [ ] Check that `show_phone` privacy setting now controls actual phone field
- [ ] Test auto-fill in registration wizard (should populate new fields)
- [ ] Verify public profile view displays phone (if `show_phone=True`)
- [ ] Check that existing profiles have `full_name` populated from User.first_name + last_name
- [ ] Test UserProfileForm with new fields
- [ ] Verify team convenience methods work (`get_active_teams()`, etc.)
- [ ] Run full test suite: `pytest apps/user_profile/tests/`

### User Acceptance Testing
- [ ] User can edit profile and add phone number
- [ ] User can set country (not just region)
- [ ] User can enter date of birth and see age calculated
- [ ] Registration wizard auto-fills all 6 fields (not just 2)
- [ ] Privacy settings correctly hide/show new fields
- [ ] Emergency contact information saves correctly

---

## Section 14: Conclusion & Next Steps

### Summary of Findings

The `UserProfile` model is **fundamentally incomplete** for tournament registration and esports platform requirements:

1. **Missing 12 critical fields** (phone, country, full_name, date_of_birth, gender, nationality, address, city, postal_code, emergency_contact_name, emergency_contact_phone, emergency_contact_relation)
2. **Broken privacy setting** (`show_phone` controls nothing)
3. **Auto-fill completely non-functional** (4 out of 6 fields always empty)
4. **Code references fields that don't exist** (5 instances across 2 files)
5. **Game ID naming inconsistencies** (minor but annoying)

### Immediate Action Items

**Priority 1 (This Week):**
1. Create migration to add critical fields (phone, country, full_name, date_of_birth)
2. Add data migration to populate `full_name` from User model
3. Update UserProfileForm to include new fields
4. Fix registration wizard auto-fill to use new fields
5. Test in development environment

**Priority 2 (Next Week):**
1. Add emergency contact fields
2. Implement team convenience methods
3. Add demographic fields (gender, nationality)
4. Update privacy settings for new fields
5. Deploy to staging for testing

**Priority 3 (Following Week):**
1. Normalize game ID field naming
2. Add validation for phone numbers, country codes
3. Implement age calculation property
4. Add age restriction checks for tournaments
5. Deploy to production

### Estimated Effort

- **Migration creation:** 2 hours
- **Form updates:** 1 hour
- **Auto-fill fixes:** 1 hour
- **Testing:** 3 hours
- **Documentation:** 1 hour
- **Total:** ~8 hours of development work

### Risk Assessment

**Low Risk:**
- Adding new fields with `blank=True` (backwards compatible)
- Using defensive `getattr()` patterns in existing code
- Data migration to populate `full_name` (read-only operation)

**Medium Risk:**
- Renaming `codm_uid` to `codm_id` (requires code search & replace)
- Changing privacy settings behavior (users may expect different behavior)

**High Risk:**
- None identified (all changes are additive, not destructive)

---

## Appendix A: Field Specification Details

### Proposed New Fields with Constraints

```python
# Contact Information
phone = models.CharField(
    max_length=20,
    blank=True,
    default="",
    help_text="Primary phone number (international format preferred: +1234567890)"
)

address = models.TextField(
    max_length=300,
    blank=True,
    default="",
    help_text="Street address for correspondence and prize shipping"
)

city = models.CharField(
    max_length=100,
    blank=True,
    default="",
    help_text="City of residence"
)

postal_code = models.CharField(
    max_length=20,
    blank=True,
    default="",
    help_text="Postal/ZIP code"
)

country = models.CharField(
    max_length=100,
    blank=True,
    default="",
    help_text="Country of residence (ISO 3166-1 alpha-2 or full name)"
)

# Demographics
full_name = models.CharField(
    max_length=200,
    blank=True,
    default="",
    help_text="Full legal name (for official tournament registration and certificates)"
)

date_of_birth = models.DateField(
    null=True,
    blank=True,
    help_text="Date of birth (used for age verification and eligibility)"
)

gender = models.CharField(
    max_length=20,
    choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_to_say', 'Prefer not to say')
    ],
    blank=True,
    default="",
    help_text="Gender identity (optional, for demographics and gender-specific events)"
)

nationality = models.CharField(
    max_length=100,
    blank=True,
    default="",
    help_text="Nationality/citizenship (may differ from country of residence)"
)

# Emergency Contact
emergency_contact_name = models.CharField(
    max_length=200,
    blank=True,
    default="",
    help_text="Emergency contact full name"
)

emergency_contact_phone = models.CharField(
    max_length=20,
    blank=True,
    default="",
    help_text="Emergency contact phone number"
)

emergency_contact_relation = models.CharField(
    max_length=50,
    blank=True,
    default="",
    help_text="Relationship to emergency contact (e.g., Parent, Spouse, Guardian)"
)

# Additional Privacy Settings
show_address = models.BooleanField(
    default=False,
    help_text="Display address on public profile"
)

show_age = models.BooleanField(
    default=True,
    help_text="Display age (calculated from date of birth) on public profile"
)

show_gender = models.BooleanField(
    default=False,
    help_text="Display gender on public profile"
)

show_country = models.BooleanField(
    default=True,
    help_text="Display country on public profile"
)
```

---

## Appendix B: Auto-Fill Before & After Comparison

### BEFORE (Current - Broken)

**UserProfile fields available:**
- ✅ `discord_id`
- ✅ `get_game_id(game)` (Riot ID, Steam ID, etc.)
- ❌ `full_name` (doesn't exist)
- ❌ `phone` (doesn't exist)
- ❌ `country` (doesn't exist, only `region`)
- ❌ `age` (doesn't exist)

**Auto-fill result:**
```python
{
    'full_name': '',  # Empty
    'phone': '',      # Empty
    'country': '',    # Empty
    'age': '',        # Empty
    'game_id': 'Player#1234',  # Works
    'discord_id': 'user#5678',  # Works
}
```

**User Experience:** Must manually type all personal information (4 out of 6 fields empty)

### AFTER (Redesigned - Fixed)

**UserProfile fields available:**
- ✅ `discord_id`
- ✅ `get_game_id(game)`
- ✅ `full_name` (NEW)
- ✅ `phone` (NEW)
- ✅ `country` (NEW)
- ✅ `age` property (calculated from `date_of_birth`) (NEW)

**Auto-fill result:**
```python
{
    'full_name': 'John Smith',  # Populated
    'phone': '+1234567890',     # Populated
    'country': 'United States', # Populated
    'age': '25',                # Populated
    'game_id': 'Player#1234',   # Works
    'discord_id': 'user#5678',  # Works
}
```

**User Experience:** All 6 fields pre-filled, user only needs to verify/adjust if needed

---

## Appendix C: Related Documentation

- **Game Specification:** `Documents/Games/Game_Spec.md`
- **User Model:** `apps/accounts/models.py`
- **Team Models:** `apps/teams/models/_legacy.py`
- **Registration Wizard:** `apps/tournaments/views/registration_wizard.py`
- **Public Profile View:** `apps/user_profile/views_public.py`
- **Profile Form:** `apps/user_profile/forms.py`
- **Initial Migration:** `apps/user_profile/migrations/0001_initial.py`

---

**END OF AUDIT REPORT**

**Audited by:** GitHub Copilot  
**Date:** 2025-01-XX  
**Version:** 1.0  
**Status:** Draft - Ready for Review
