# Phase 1 Model Field Naming - Quick Reference Card

**Critical Reference**: Always use these EXACT field names when working with Phase 1 models

---

## 🎯 TournamentSchedule

```python
# ✅ CORRECT Field Names
reg_open_at      # Registration opens (abbreviated, not registration_open_at)
reg_close_at     # Registration closes (abbreviated, not registration_close_at)
start_at         # Tournament starts
end_at           # Tournament ends

# Example Usage
schedule = TournamentSchedule.objects.create(
    tournament=tournament,
    reg_open_at=timezone.now(),
    reg_close_at=timezone.now() + timedelta(days=7),
    start_at=timezone.now() + timedelta(days=10),
    end_at=timezone.now() + timedelta(days=12)
)
```

---

## 🎯 TournamentCapacity

```python
# ✅ CORRECT Field Names
slot_size              # REQUIRED - Tournament bracket size (4, 8, 16, 32, 64)
max_teams              # Maximum teams (must be <= slot_size)
current_registrations  # Current number of registrations
waitlist_enabled       # Boolean for waitlist feature

# ❌ WRONG Names
# waitlist_count, current_teams, max_capacity

# Example Usage
capacity = TournamentCapacity.objects.create(
    tournament=tournament,
    slot_size=16,              # REQUIRED field!
    max_teams=16,
    current_registrations=8
)

# Validation Rule
# max_teams MUST be <= slot_size
# Model validation at line 142: if self.max_teams > self.slot_size:
```

---

## 🎯 TournamentFinance

```python
# ✅ CORRECT Field Names (with _bdt suffix)
entry_fee_bdt      # Entry fee in BDT (Decimal)
prize_pool_bdt     # Total prize pool in BDT (Decimal)
winner_prize_bdt   # Winner's share (Decimal)
runner_up_prize_bdt # Runner-up's share (Decimal)

# ❌ WRONG Names
# entry_fee, prize_pool (without _bdt suffix)
# total_collected, total_paid_out (don't exist)

# Example Usage
finance = TournamentFinance.objects.create(
    tournament=tournament,
    entry_fee_bdt=Decimal('1000.00'),  # Note: _bdt suffix
    prize_pool_bdt=Decimal('10000.00')
)

# Template Usage (REQUIRES {% load humanize %})
<p>Entry Fee: ৳{{ finance.entry_fee_bdt|intcomma }}</p>
```

---

## 🎯 TournamentRules

```python
# ✅ CORRECT Field Names
require_discord    # Boolean (no plural 's')
require_game_id    # Boolean (no plural 's')
general_rules      # TextField (NOT list)
eligibility_requirements  # TextField (NOT list)
match_rules        # TextField (NOT list)

# ❌ WRONG Names
# requires_discord, requires_game_id (plural form)
# requirements (list field - doesn't exist)
# min_age, region_lock, rank_restriction (don't exist)

# Example Usage
rules = TournamentRules.objects.create(
    tournament=tournament,
    general_rules='Standard tournament rules',
    eligibility_requirements='Must be 18+. Must have Discord.',
    match_rules='Best of 3',
    require_discord=True,  # No plural 's'
    require_game_id=True
)
```

---

## 🎯 TournamentArchive

```python
# ✅ CORRECT Field Names
archive_type    # CharField: 'ARCHIVED' or 'CLONED'
is_archived     # Boolean
archived_at     # DateTimeField
reason          # TextField

# ❌ WRONG Names
# status, preserve_registrations, preserve_matches (don't exist)

# Example Usage
archive = TournamentArchive.objects.create(
    tournament=tournament,
    archive_type='ARCHIVED',
    is_archived=True,
    archived_at=timezone.now(),
    reason='Tournament completed successfully'
)
```

---

## 🎯 TournamentMedia

```python
# ✅ CORRECT Field Names
banner_image      # ImageField
thumbnail_image   # ImageField
promo_video_url   # URLField

# Example Usage
media = TournamentMedia.objects.create(
    tournament=tournament,
    banner_image='banners/tournament.jpg',
    thumbnail_image='thumbnails/tournament.jpg'
)
```

---

## 🎯 Tournament (Base Model)

```python
# ✅ CORRECT Field Values
status = 'PUBLISHED'  # UPPERCASE string, not lowercase

# ❌ WRONG
# status = 'published'  # lowercase - WRONG!
# organizer (field doesn't exist)

# Example Usage
tournament = Tournament.objects.create(
    name='Test Tournament',
    slug='test-tournament',
    game='valorant',
    status='PUBLISHED',  # MUST be uppercase
)
```

---

## 🔧 Safe Access Patterns

### ✅ CORRECT: Check existence first
```python
# Method 1: hasattr
if hasattr(tournament, 'schedule'):
    reg_open = tournament.schedule.reg_open_at
else:
    reg_open = None

# Method 2: try/except
try:
    entry_fee = tournament.finance.entry_fee_bdt
except TournamentFinance.DoesNotExist:
    entry_fee = Decimal('0.00')

# Method 3: Template safe access
{% if tournament.schedule %}
  <p>Opens: {{ tournament.schedule.reg_open_at|date:"M d, Y" }}</p>
{% endif %}
```

### ❌ WRONG: Direct access
```python
# This will raise RelatedObjectDoesNotExist!
entry_fee = tournament.finance.entry_fee_bdt
```

---

## ⚡ Query Optimization

### ✅ CORRECT: Use select_related
```python
# Fetch all Phase 1 data in ONE query
tournament = Tournament.objects.select_related(
    'schedule',
    'capacity',
    'finance',
    'media',
    'rules',
    'archive'
).get(slug=slug)
```

### ❌ WRONG: N+1 query problem
```python
tournament = Tournament.objects.get(slug=slug)
# Each access below is a separate query!
print(tournament.schedule.reg_open_at)  # Query 1
print(tournament.capacity.max_teams)     # Query 2
print(tournament.finance.entry_fee_bdt)  # Query 3
```

---

## 📝 Template Requirements

### CRITICAL: Load humanize for intcomma
```django
{% load static %}
{% load humanize %}  {# REQUIRED for intcomma filter! #}

<p>Entry Fee: ৳{{ finance.entry_fee_bdt|intcomma }}</p>
<p>Prize Pool: ৳{{ finance.prize_pool_bdt|intcomma }}</p>
```

**Without {% load humanize %}**: TemplateSyntaxError: Invalid filter: 'intcomma'

---

## 🧪 Testing Patterns

### ✅ CORRECT: Complete setUp with all required fields
```python
def setUp(self):
    self.tournament = Tournament.objects.create(
        name='Test Tournament',
        slug='test-tournament',
        game='valorant',
        status='PUBLISHED',  # UPPERCASE
    )
    
    self.capacity = TournamentCapacity.objects.create(
        tournament=self.tournament,
        slot_size=16,  # REQUIRED - don't forget!
        max_teams=16,
        current_registrations=8
    )
    
    self.finance = TournamentFinance.objects.create(
        tournament=self.tournament,
        entry_fee_bdt=Decimal('1000.00'),  # _bdt suffix
        prize_pool_bdt=Decimal('10000.00')
    )
```

---

## 🚨 Common Errors & Fixes

### Error #1: TemplateSyntaxError - Invalid filter: 'intcomma'
**Fix**: Add `{% load humanize %}` after `{% load static %}`

### Error #2: RelatedObjectDoesNotExist
**Fix**: Check existence before accessing (hasattr or try/except)

### Error #3: TypeError - '>' not supported between 'int' and 'NoneType'
**Fix**: Always include `slot_size` when creating TournamentCapacity

### Error #4: AttributeError - 'TournamentSchedule' object has no attribute 'registration_open_at'
**Fix**: Use abbreviated name: `reg_open_at` not `registration_open_at`

### Error #5: Decimal has no attribute 'intcomma'
**Fix**: Use `entry_fee_bdt` not `entry_fee` (field names have _bdt suffix)

---

## 📋 Checklist: Adding Phase 1 Data to Tests

- [ ] Tournament status is 'PUBLISHED' (uppercase)
- [ ] TournamentSchedule uses `reg_open_at`, `reg_close_at`
- [ ] TournamentCapacity includes `slot_size` (REQUIRED)
- [ ] TournamentFinance fields have `_bdt` suffix
- [ ] TournamentRules uses `require_discord` (no plural)
- [ ] TournamentRules text fields are strings (not lists)
- [ ] TournamentArchive uses `archive_type`, `is_archived`
- [ ] Template includes `{% load humanize %}`
- [ ] Views use `select_related()` for optimization
- [ ] Safe access patterns used (hasattr or try/except)

---

**Quick Reference Version**: 1.0  
**Last Updated**: October 3, 2025  
**Keep this card handy when writing tests or views!**
