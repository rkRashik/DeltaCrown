# Tournament Detail V8 - Field Errors Fix

## 🐛 Issues Fixed

### 1. FieldError - Cannot resolve keyword 'scheduled_time'
**Error:** `Cannot resolve keyword 'scheduled_time' into field`  
**Root Cause:** V8 view was using incorrect field names for Match model  
**Status:** ✅ **FIXED**

### 2. FieldError - Invalid field name 'creator' in select_related
**Error:** `Invalid field name(s) given in select_related: 'creator'`  
**Root Cause:** Tournament model has `organizer` field, not `creator`  
**Status:** ✅ **FIXED**

### 3. ValueError - Cannot query "rkrashik": Must be "UserProfile" instance
**Error:** `Cannot query "rkrashik": Must be "UserProfile" instance`  
**Root Cause:** Registration model expects UserProfile, but view was using User  
**Status:** ✅ **FIXED**

---

## 🔧 Changes Made

### View: `apps/tournaments/views/detail_v8.py`

#### 1. Fixed Tournament select_related Query
```python
# OLD (Incorrect)
Tournament.objects.select_related(
    'creator',  # ❌ Field does not exist
    'capacity',
    'finance',
    'schedule',
    'rules',
    'media',
    'organizer'  # ✅ This was correct but redundant with creator
)

# NEW (Fixed)
Tournament.objects.select_related(
    'organizer',  # ✅ Correct - Tournament has organizer field
    'capacity',
    'finance',
    'schedule',
    'rules',
    'media'
)
```

#### 2. Fixed Match Prefetch Query
```python
# OLD (Incorrect)
Prefetch(
    'matches',
    queryset=Match.objects.select_related(
        'team1', 'team2'  # ❌ Wrong field names
    ).order_by('scheduled_time')  # ❌ Wrong field name
)

# NEW (Fixed)
Prefetch(
    'matches',
    queryset=Match.objects.select_related(
        'team_a', 'team_b'  # ✅ Correct field names
    ).order_by('start_at')  # ✅ Correct field name
)
```

#### 3. Fixed Upcoming Matches Query
```python
# OLD (Incorrect)
upcoming_matches = tournament.matches.filter(
    status__in=['SCHEDULED', 'LIVE'],  # ❌ Wrong field name
    scheduled_time__gte=now  # ❌ Wrong field name
).order_by('scheduled_time')[:5]  # ❌ Wrong field name

# NEW (Fixed)
upcoming_matches = tournament.matches.filter(
    state__in=['SCHEDULED'],  # ✅ Correct field name
    start_at__gte=now  # ✅ Correct field name
).order_by('start_at')[:5]  # ✅ Correct field name
```

#### 4. Fixed Recent Matches Query
```python
# OLD (Incorrect)
recent_matches = tournament.matches.filter(
    status='COMPLETED'  # ❌ Wrong field name
).order_by('-scheduled_time')[:5]  # ❌ Wrong field name

# NEW (Fixed)
recent_matches = tournament.matches.filter(
    state='VERIFIED'  # ✅ Correct field name
).order_by('-start_at')[:5]  # ✅ Correct field name
```

#### 5. Fixed Statistics Query
```python
# OLD (Incorrect)
stats = {
    'completed_matches': tournament.matches.filter(status='COMPLETED').count(),  # ❌
    'live_matches': tournament.matches.filter(status='LIVE').count(),  # ❌
}

# NEW (Fixed)
stats = {
    'completed_matches': tournament.matches.filter(state='VERIFIED').count(),  # ✅
    'live_matches': tournament.matches.filter(state='REPORTED').count(),  # ✅
}
```

#### 6. Fixed User Registration Query
```python
# OLD (Incorrect)
if request.user.is_authenticated:
    user_registration = tournament.registrations.filter(
        user=request.user  # ❌ Registration expects UserProfile, not User
    ).select_related('team').first()

# NEW (Fixed)
if request.user.is_authenticated and hasattr(request.user, 'profile'):
    user_registration = tournament.registrations.filter(
        user=request.user.profile  # ✅ Using UserProfile instance
    ).select_related('team').first()
```

### Template: `templates/tournaments/detail_v8.html`

#### 1. Fixed Team References
```html
<!-- OLD (Incorrect) -->
{% if match.team1 %}
    <img src="{{ match.team1.logo.url }}" alt="{{ match.team1.name }}">
    <span>{{ match.team1.name }}</span>
{% endif %}

<!-- NEW (Fixed) -->
{% if match.team_a %}
    <img src="{{ match.team_a.logo.url }}" alt="{{ match.team_a.name }}">
    <span>{{ match.team_a.name }}</span>
{% endif %}
```

#### 2. Fixed Time References
```html
<!-- OLD (Incorrect) -->
<span class="match-time">{{ match.scheduled_time|date:"M d, g:i A" }}</span>

<!-- NEW (Fixed) -->
<span class="match-time">{{ match.start_at|date:"M d, g:i A" }}</span>
```

#### 3. Fixed Score References
```html
<!-- OLD (Incorrect) -->
{% if match.team1_score is not None and match.team2_score is not None %}
    <div class="match-score">{{ match.team1_score }} - {{ match.team2_score }}</div>
{% endif %}

<!-- NEW (Fixed) -->
{% if match.score_a is not None and match.score_b is not None %}
    <div class="match-score">{{ match.score_a }} - {{ match.score_b }}</div>
{% endif %}
```

#### 4. Fixed Status References
```html
<!-- OLD (Incorrect) -->
{% if match.status == 'LIVE' %}
    <span class="match-status live">LIVE</span>
{% endif %}

<!-- NEW (Fixed) -->
{% if match.state == 'REPORTED' %}
    <span class="match-status live">LIVE</span>
{% endif %}
```

---

## 📋 Model Field References

### Tournament Model Field Reference

Based on `apps/tournaments/models/tournament.py`:

### Related Fields (for select_related)
- ✅ `organizer` - Tournament organizer (ForeignKey to UserProfile)
- ✅ `capacity` - Tournament capacity settings
- ✅ `finance` - Prize pool and finance data
- ✅ `schedule` - Tournament schedule information
- ✅ `rules` - Tournament rules and regulations
- ✅ `media` - Tournament media assets
- ✅ `bracket` - Tournament bracket structure
- ✅ `settings` - Tournament settings
- ✅ `archive` - Tournament archive data
- ❌ ~~`creator`~~ - Does not exist (use `organizer` instead)

### Registration Model Field Reference

Based on `apps/tournaments/models/registration.py`:

### User/Team Fields
- ✅ `user` - Registered user (ForeignKey to UserProfile, not User)
- ✅ `team` - Registered team (ForeignKey to Team)
- ❌ Using `request.user` directly - Must use `request.user.profile`

### Access Pattern
```python
# ❌ Wrong - Registration.user expects UserProfile
user_registration = tournament.registrations.filter(user=request.user)

# ✅ Correct - Use UserProfile instance
user_registration = tournament.registrations.filter(user=request.user.profile)

# ✅ Defensive - Check profile exists
if request.user.is_authenticated and hasattr(request.user, 'profile'):
    user_registration = tournament.registrations.filter(user=request.user.profile)
```

---

## 📋 Match Model Field Reference

Based on `apps/tournaments/models/match.py`:

### Team Fields
- ✅ `team_a` - Team A (ForeignKey to Team)
- ✅ `team_b` - Team B (ForeignKey to Team)
- ❌ ~~`team1`~~ - Does not exist
- ❌ ~~`team2`~~ - Does not exist

### User Fields (for solo matches)
- ✅ `user_a` - User A (ForeignKey to UserProfile)
- ✅ `user_b` - User B (ForeignKey to UserProfile)

### Score Fields
- ✅ `score_a` - Score for team/user A
- ✅ `score_b` - Score for team/user B
- ❌ ~~`team1_score`~~ - Does not exist
- ❌ ~~`team2_score`~~ - Does not exist

### Time Fields
- ✅ `start_at` - Scheduled start time (DateTimeField)
- ✅ `created_at` - Creation time (auto_now_add)
- ❌ ~~`scheduled_time`~~ - Does not exist

### Status Fields
- ✅ `state` - Match state (choices: SCHEDULED, REPORTED, VERIFIED)
- ❌ ~~`status`~~ - Does not exist

### Winner Fields
- ✅ `winner_team` - Winning team (ForeignKey to Team)
- ✅ `winner_user` - Winning user (ForeignKey to UserProfile)

---

## 🧪 Testing Status

✅ **Import Test:** View imports without errors  
✅ **Django Check:** No issues found  
⏳ **Browser Test:** Ready for testing at `/tournaments/t/<slug>/`

---

## 🎯 Match State Values

Understanding the Match.STATE choices:

```python
STATE = [
    ("SCHEDULED", "Scheduled"),  # ✅ Upcoming matches
    ("REPORTED", "Reported"),    # ✅ Live/in-progress matches  
    ("VERIFIED", "Verified")     # ✅ Completed matches
]
```

### Usage in Queries:
- **Upcoming:** `state='SCHEDULED'` + `start_at__gte=now`
- **Live:** `state='REPORTED'` 
- **Completed:** `state='VERIFIED'`

---

## 📝 Summary of Field Mapping

| Purpose | ❌ Incorrect | ✅ Correct |
|---------|-------------|------------|
| Team 1 | `team1` | `team_a` |
| Team 2 | `team2` | `team_b` |
| User 1 | `user1` | `user_a` |
| User 2 | `user2` | `user_b` |
| Score 1 | `team1_score` | `score_a` |
| Score 2 | `team2_score` | `score_b` |
| Time | `scheduled_time` | `start_at` |
| Status | `status` | `state` |

---

## 🚀 Result

The V8 tournament detail page now correctly uses the Match model fields and should load without field errors.

**Status:** ✅ **FIXED - Ready for Testing**

---

**Date:** December 2024  
**Fix Applied:** Match Model Field Corrections  
**Files Modified:** 2 (view + template)