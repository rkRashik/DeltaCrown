# Model Cleanup Plan - Tournament Model

**Date**: October 4, 2025  
**Status**: In Progress  
**Estimated Time**: 4-6 hours  
**Goal**: Clean up redundant fields, add professional features, improve data structure

---

## Executive Summary

The Tournament model currently has redundant fields that duplicate functionality in Phase 1 models (TournamentSchedule, TournamentFinance). We'll deprecate these fields with clear guidance, add professional fields, and improve the prize_distribution structure.

---

## Current State Analysis

### Tournament Model (323 lines)

**Location**: `apps/tournaments/models/tournament.py`

**Redundant Fields** (overlap with Phase 1 models):
```python
# REDUNDANT - duplicates TournamentSchedule
slot_size = models.PositiveIntegerField(null=True, blank=True)
reg_open_at = models.DateTimeField(blank=True, null=True)
reg_close_at = models.DateTimeField(blank=True, null=True)
start_at = models.DateTimeField(blank=True, null=True)
end_at = models.DateTimeField(blank=True, null=True)

# REDUNDANT - duplicates TournamentFinance
entry_fee_bdt = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
prize_pool_bdt = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
```

**Issues**:
1. **Data Duplication**: Same information stored in 2 places (Tournament + Phase 1 models)
2. **Confusion**: Developers don't know which field to use
3. **Maintenance**: Changes must be synced between models
4. **API Inconsistency**: Some endpoints use Tournament fields, others use Phase 1 models

### Phase 1 Models (Replacements)

**TournamentSchedule** (replaces date fields):
```python
registration_start  # replaces reg_open_at
registration_end    # replaces reg_close_at  
tournament_start    # replaces start_at
tournament_end      # replaces end_at
# PLUS: checkin dates, early bird, timezone, auto-close settings
```

**TournamentCapacity** (replaces slot_size):
```python
max_teams          # replaces slot_size
current_teams      # live count
min_teams          # minimum requirement
waitlist_capacity  # waitlist support
# PLUS: player limits, status tracking, capacity management
```

**TournamentFinance** (replaces money fields):
```python
entry_fee          # replaces entry_fee_bdt
prize_pool         # replaces prize_pool_bdt
currency           # flexible currency support
# PLUS: early bird fees, late fees, revenue tracking, profit calculation
```

---

## Cleanup Strategy

### Approach: Deprecation (NOT Deletion)

**Why Not Delete?**
- Breaks existing code
- Loses historical data
- Risky for production

**Deprecation Benefits**:
- ✅ Backward compatible
- ✅ Data preserved
- ✅ Clear migration path
- ✅ Gradual transition
- ✅ No breaking changes

### Phase-by-Phase Cleanup

#### Phase 1: Add Deprecation Warnings (1 hour)

**Action**: Add deprecation notices to redundant fields

**Fields to Deprecate**:
```python
# apps/tournaments/models/tournament.py

# ----- DEPRECATED FIELDS (use Phase 1 models instead) -----
slot_size = models.PositiveIntegerField(
    null=True, 
    blank=True,
    help_text="⚠️ DEPRECATED: Use TournamentCapacity.max_teams instead. "
              "This field is kept for backward compatibility but will be removed in v2.0."
)

reg_open_at = models.DateTimeField(
    blank=True, 
    null=True,
    help_text="⚠️ DEPRECATED: Use TournamentSchedule.registration_start instead. "
              "This field is kept for backward compatibility but will be removed in v2.0."
)

reg_close_at = models.DateTimeField(
    blank=True, 
    null=True,
    help_text="⚠️ DEPRECATED: Use TournamentSchedule.registration_end instead. "
              "This field is kept for backward compatibility but will be removed in v2.0."
)

start_at = models.DateTimeField(
    blank=True, 
    null=True,
    help_text="⚠️ DEPRECATED: Use TournamentSchedule.tournament_start instead. "
              "This field is kept for backward compatibility but will be removed in v2.0."
)

end_at = models.DateTimeField(
    blank=True, 
    null=True,
    help_text="⚠️ DEPRECATED: Use TournamentSchedule.tournament_end instead. "
              "This field is kept for backward compatibility but will be removed in v2.0."
)

entry_fee_bdt = models.DecimalField(
    max_digits=10, 
    decimal_places=2, 
    null=True, 
    blank=True,
    help_text="⚠️ DEPRECATED: Use TournamentFinance.entry_fee + currency instead. "
              "This field is kept for backward compatibility but will be removed in v2.0."
)

prize_pool_bdt = models.DecimalField(
    max_digits=12, 
    decimal_places=2, 
    null=True, 
    blank=True,
    help_text="⚠️ DEPRECATED: Use TournamentFinance.prize_pool + prize_currency instead. "
              "This field is kept for backward compatibility but will be removed in v2.0."
)
```

**Result**: Clear warnings in admin, API docs, and code

---

#### Phase 2: Add Professional Fields (2 hours)

**Action**: Add missing fields for professional tournament management

**New Fields to Add**:
```python
# ----- Professional Fields -----
tournament_type = models.CharField(
    max_length=32,
    choices=[
        ('SOLO', 'Solo'),
        ('TEAM', 'Team'),
        ('MIXED', 'Mixed (Solo & Team)'),
    ],
    default='TEAM',
    help_text="Type of tournament: Solo, Team, or Mixed"
)

format = models.CharField(
    max_length=32,
    choices=[
        ('SINGLE_ELIM', 'Single Elimination'),
        ('DOUBLE_ELIM', 'Double Elimination'),
        ('ROUND_ROBIN', 'Round Robin'),
        ('SWISS', 'Swiss System'),
        ('GROUP_STAGE', 'Group Stage'),
        ('HYBRID', 'Hybrid (Groups + Bracket)'),
    ],
    blank=True,
    help_text="Tournament format/structure"
)

platform = models.CharField(
    max_length=32,
    choices=[
        ('ONLINE', 'Online'),
        ('OFFLINE', 'Offline/LAN'),
        ('HYBRID', 'Hybrid'),
    ],
    default='ONLINE',
    help_text="Where the tournament takes place"
)

region = models.CharField(
    max_length=64,
    blank=True,
    help_text="Geographic region (e.g., 'Bangladesh', 'South Asia', 'Global')"
)

language = models.CharField(
    max_length=8,
    choices=[
        ('en', 'English'),
        ('bn', 'বাংলা (Bengali)'),
        ('hi', 'हिन्दी (Hindi)'),
        ('multi', 'Multilingual'),
    ],
    default='en',
    help_text="Primary language for tournament communication"
)

organizer = models.ForeignKey(
    'user_profile.UserProfile',  # or Organization model if exists
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='organized_tournaments',
    help_text="User or organization running this tournament"
)

description = CKEditor5Field(
    "Full Description",
    config_name="extends",
    blank=True,
    null=True,
    help_text="Detailed tournament description (supports rich text)"
)

# Rename short_description for clarity
# short_description → tagline
tagline = CKEditor5Field(
    "Tagline",
    config_name="default",
    blank=True,
    null=True,
    help_text="Short catchy tagline (1-2 sentences)"
)
```

**Benefits**:
- Clear tournament categorization
- Better search/filtering
- Improved UX (users know what to expect)
- Professional metadata

---

#### Phase 3: Improve Prize Distribution (1 hour)

**Current State**:
```python
# TournamentFinance model
prize_distribution = models.TextField(
    blank=True,
    help_text="Prize distribution details (1st: X, 2nd: Y, etc.)"
)
```

**Problem**: Text field, no structure, hard to parse

**Solution**: Convert to JSONField with validation

**New Implementation**:
```python
# apps/tournaments/models/tournament_finance.py

prize_distribution = models.JSONField(
    default=dict,
    blank=True,
    help_text="Prize distribution structure. Example: "
              '{"1": {"amount": 50000, "percentage": 50}, '
              '"2": {"amount": 30000, "percentage": 30}, '
              '"3": {"amount": 20000, "percentage": 20}}'
)

def get_prize_distribution_display(self):
    """Format prize distribution for display"""
    if not self.prize_distribution:
        return ""
    
    lines = []
    for position, details in sorted(self.prize_distribution.items(), key=lambda x: int(x[0])):
        amount = details.get('amount', 0)
        percentage = details.get('percentage', 0)
        
        # Format position (1st, 2nd, 3rd, etc.)
        pos_suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(int(position), 'th')
        pos_text = f"{position}{pos_suffix} Place"
        
        # Format amount with currency
        currency = self.prize_currency or 'BDT'
        amount_text = f"{currency} {amount:,.2f}"
        
        # Add percentage if available
        if percentage:
            amount_text += f" ({percentage}%)"
        
        lines.append(f"{pos_text}: {amount_text}")
    
    return "\n".join(lines)

def validate_prize_distribution(self):
    """Validate prize distribution structure"""
    from django.core.exceptions import ValidationError
    
    if not isinstance(self.prize_distribution, dict):
        raise ValidationError("Prize distribution must be a dictionary")
    
    total_percentage = 0
    total_amount = 0
    
    for position, details in self.prize_distribution.items():
        # Validate position is numeric
        try:
            int(position)
        except ValueError:
            raise ValidationError(f"Position '{position}' must be a number")
        
        # Validate details structure
        if not isinstance(details, dict):
            raise ValidationError(f"Position {position} details must be a dictionary")
        
        amount = details.get('amount', 0)
        percentage = details.get('percentage', 0)
        
        if amount < 0:
            raise ValidationError(f"Position {position} amount cannot be negative")
        
        if percentage < 0 or percentage > 100:
            raise ValidationError(f"Position {position} percentage must be between 0-100")
        
        total_amount += amount
        total_percentage += percentage
    
    # Warn if total doesn't match prize pool
    if self.prize_pool and total_amount > self.prize_pool:
        raise ValidationError(
            f"Total prize distribution ({total_amount}) exceeds prize pool ({self.prize_pool})"
        )
    
    # Warn if percentages don't add to 100
    if total_percentage > 0 and abs(total_percentage - 100) > 0.01:
        raise ValidationError(
            f"Prize percentages should add up to 100% (currently {total_percentage}%)"
        )
```

**Benefits**:
- Structured data
- Easy to parse in templates
- Validation ensures correctness
- Can calculate totals/percentages
- API-friendly

---

#### Phase 4: Create Data Migration (30 minutes)

**Action**: Migrate existing data from old fields to Phase 1 models

**Migration Script**:
```python
# migrations/XXXX_migrate_deprecated_fields.py

from django.db import migrations

def migrate_schedule_data(apps, schema_editor):
    """Migrate date fields to TournamentSchedule"""
    Tournament = apps.get_model('tournaments', 'Tournament')
    TournamentSchedule = apps.get_model('tournaments', 'TournamentSchedule')
    
    for tournament in Tournament.objects.all():
        # Skip if schedule already exists
        if hasattr(tournament, 'schedule'):
            continue
        
        # Create schedule from deprecated fields
        if tournament.reg_open_at or tournament.start_at:
            TournamentSchedule.objects.create(
                tournament=tournament,
                registration_start=tournament.reg_open_at,
                registration_end=tournament.reg_close_at,
                tournament_start=tournament.start_at,
                tournament_end=tournament.end_at,
                timezone='Asia/Dhaka'  # default
            )

def migrate_capacity_data(apps, schema_editor):
    """Migrate slot_size to TournamentCapacity"""
    Tournament = apps.get_model('tournaments', 'Tournament')
    TournamentCapacity = apps.get_model('tournaments', 'TournamentCapacity')
    
    for tournament in Tournament.objects.all():
        if hasattr(tournament, 'capacity'):
            continue
        
        if tournament.slot_size:
            TournamentCapacity.objects.create(
                tournament=tournament,
                max_teams=tournament.slot_size,
                min_teams=2,  # sensible default
                min_players_per_team=1,
                max_players_per_team=5,
            )

def migrate_finance_data(apps, schema_editor):
    """Migrate entry_fee/prize_pool to TournamentFinance"""
    Tournament = apps.get_model('tournaments', 'Tournament')
    TournamentFinance = apps.get_model('tournaments', 'TournamentFinance')
    
    for tournament in Tournament.objects.all():
        if hasattr(tournament, 'finance'):
            continue
        
        if tournament.entry_fee_bdt or tournament.prize_pool_bdt:
            TournamentFinance.objects.create(
                tournament=tournament,
                entry_fee=tournament.entry_fee_bdt or 0,
                currency='BDT',
                prize_pool=tournament.prize_pool_bdt or 0,
                prize_currency='BDT',
            )

class Migration(migrations.Migration):
    dependencies = [
        ('tournaments', 'XXXX_previous_migration'),
    ]
    
    operations = [
        migrations.RunPython(
            migrate_schedule_data,
            reverse_code=migrations.RunPython.noop
        ),
        migrations.RunPython(
            migrate_capacity_data,
            reverse_code=migrations.RunPython.noop
        ),
        migrations.RunPython(
            migrate_finance_data,
            reverse_code=migrations.RunPython.noop
        ),
    ]
```

**Benefits**:
- Existing data preserved
- Phase 1 models populated
- No data loss
- Automatic migration on deploy

---

#### Phase 5: Update Property Methods (1 hour)

**Action**: Update @property methods to use Phase 1 models

**Current** (uses deprecated fields):
```python
@property
def registration_open(self) -> bool:
    # Uses reg_open_at, reg_close_at
    return self.reg_open_at <= now <= self.reg_close_at
```

**Updated** (uses Phase 1 models):
```python
@property
def registration_open(self) -> bool:
    """Check if registration is currently open"""
    # Prefer Phase 1 model
    if hasattr(self, 'schedule') and self.schedule:
        return self.schedule.is_registration_open()
    
    # Fallback to deprecated fields for backward compatibility
    from django.utils import timezone
    now = timezone.now()
    if self.reg_open_at and self.reg_close_at:
        return self.reg_open_at <= now <= self.reg_close_at
    
    return False

@property
def is_live(self) -> bool:
    """Check if tournament is currently running"""
    # Prefer Phase 1 model
    if hasattr(self, 'schedule') and self.schedule:
        return self.schedule.is_in_progress()
    
    # Fallback to deprecated fields
    from django.utils import timezone
    now = timezone.now()
    if self.start_at and self.end_at:
        return self.start_at <= now <= self.end_at
    
    return False

@property
def slots_total(self):
    """Total number of slots/teams"""
    # Prefer Phase 1 model
    if hasattr(self, 'capacity') and self.capacity:
        return self.capacity.max_teams
    
    # Fallback to deprecated field
    return self.slot_size

@property
def slots_taken(self):
    """Number of slots/teams currently filled"""
    # Prefer Phase 1 model (live count)
    if hasattr(self, 'capacity') and self.capacity:
        return self.capacity.current_teams
    
    # Fallback to registration count
    try:
        return self.registrations.filter(status="CONFIRMED").count()
    except Exception:
        return 0

@property
def entry_fee(self):
    """Entry fee amount"""
    # Prefer Phase 1 model
    if hasattr(self, 'finance') and self.finance:
        return self.finance.entry_fee
    
    # Fallback to deprecated field
    return self.entry_fee_bdt

@property
def prize_pool(self):
    """Prize pool amount"""
    # Prefer Phase 1 model
    if hasattr(self, 'finance') and self.finance:
        return self.finance.prize_pool
    
    # Fallback to deprecated field
    return self.prize_pool_bdt
```

**Benefits**:
- Uses Phase 1 models first
- Falls back to deprecated fields
- No breaking changes
- Gradual migration

---

## Implementation Timeline

### Week 1: Deprecation & New Fields (3 hours)
- [ ] Add deprecation warnings to redundant fields (1 hour)
- [ ] Add professional fields (tournament_type, format, platform, region, language, organizer) (2 hours)
- [ ] Create migration for new fields
- [ ] Update admin interface to show warnings
- [ ] Test in development

### Week 2: Prize Distribution & Data Migration (2 hours)
- [ ] Convert prize_distribution to JSONField (30 minutes)
- [ ] Add validation methods (30 minutes)
- [ ] Create data migration script (30 minutes)
- [ ] Test migration on sample data (30 minutes)

### Week 3: Property Updates & Testing (1 hour)
- [ ] Update @property methods to use Phase 1 models (30 minutes)
- [ ] Update tests (15 minutes)
- [ ] Run full test suite (15 minutes)

**Total**: 4-6 hours (spread over 3 weeks for safety)

---

## Migration Path for Developers

### Old Way (Deprecated) ❌
```python
# Accessing schedule
tournament.reg_open_at
tournament.reg_close_at
tournament.start_at
tournament.end_at

# Accessing capacity
tournament.slot_size

# Accessing finance
tournament.entry_fee_bdt
tournament.prize_pool_bdt
```

### New Way (Recommended) ✅
```python
# Accessing schedule
tournament.schedule.registration_start
tournament.schedule.registration_end
tournament.schedule.tournament_start
tournament.schedule.tournament_end

# Accessing capacity
tournament.capacity.max_teams
tournament.capacity.current_teams

# Accessing finance
tournament.finance.entry_fee
tournament.finance.prize_pool
tournament.finance.currency
```

### Backward Compatible Properties ✅
```python
# These work and automatically use Phase 1 models
tournament.registration_open  # Uses schedule model
tournament.is_live           # Uses schedule model
tournament.slots_total       # Uses capacity model
tournament.slots_taken       # Uses capacity model
tournament.entry_fee         # Uses finance model
tournament.prize_pool        # Uses finance model
```

---

## Benefits Summary

### Code Quality
- ✅ Single source of truth (Phase 1 models)
- ✅ No data duplication
- ✅ Clear deprecation path
- ✅ Backward compatible

### Data Integrity
- ✅ Validated prize distribution
- ✅ Structured data (JSONField)
- ✅ No data loss during migration
- ✅ Historical data preserved

### Professional Features
- ✅ Tournament type classification
- ✅ Format specification
- ✅ Platform indication
- ✅ Region/language support
- ✅ Organizer tracking

### Developer Experience
- ✅ Clear warnings in admin
- ✅ Deprecation notices in code
- ✅ Migration guides
- ✅ No breaking changes

---

## Success Criteria

- [ ] Deprecation warnings added to all redundant fields
- [ ] Professional fields added with migrations
- [ ] Prize distribution converted to JSONField
- [ ] Data migration script created and tested
- [ ] Property methods updated to use Phase 1 models
- [ ] Admin interface shows deprecation notices
- [ ] Tests pass (18/18 integration tests)
- [ ] Django system check clean (0 issues)
- [ ] Documentation updated

---

## Next Steps After Completion

1. ✅ Model Cleanup **[CURRENT]**
2. ⏳ UI/UX Improvements (4-6 hours)
3. ⏳ Test Admin Interface (30 minutes)
4. ⏳ Deployment (1 hour)

---

**Status**: Ready to implement  
**Priority**: High (user-requested improvement)  
**Risk**: LOW (backward compatible, gradual migration)  
**Time**: 4-6 hours (spread over 3 weeks recommended)
